"""The worker preamble carries the rules of a delegated session, and agent-delegate says when to resume one.

What the text says, in eleven places of two files:

* section 3 of the preamble ends with a paragraph that has a worker write its result, or create the
  branch or ref its brief names, before any optional verification and keep the evidence on disk;
* section 4 ends with a bullet that returns acceptance criteria as a table, one of four states and
  one evidence pointer each, and names who ticks the boxes;
* section 5, the last section of the file, holds six rules: size the work first (its starting values
  carry their uncalibrated tag), plan the close, run the Close block of the brief, leave sessions to
  the operator, make no external call by default, and, if it runs the plan critic, run it within its
  own cap, with no run count stated in the preamble;
* the last section of agent-delegate's SKILL.md, "Resuming a worker", says how to resume after a
  usage limit and why not to resume a session that ended near its window, each claim with its
  evidence tag.

A guard that reads text never runs out of shapes, so this one covers classes: a rule dropped, a rule
hollowed out (its lead kept, its content gone), a section or paragraph moved out of its place, an
evidence tag or a number lost, a critic run count stated, and a re-wrap or a rewording that changes
no rule, down to a bold lead that wraps over two lines. Every check is fired at a known positive:
each check of a place is removed from the shipped text and must then be reported, a section 5 that
lacks one rule must be flagged and no other rule with it, a reworded or re-wrapped section 5 must
pass, and each helper that slices the text (a section, a list item, a paragraph) is fired at a
planted text with a decoy that only a wrong slice would pick up. The first test asserts the scan
surface in numbers.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")
_DOT = chr(0xB7)  # the middle dot in the preamble's numbered headings

_PREAMBLE = "plugins/orchestration/skills/agent-delegate/assets/worker-preamble.md"
_DELEGATE = "plugins/orchestration/skills/agent-delegate/SKILL.md"
_H3 = f"## 3 {_DOT}"
_H4 = f"## 4 {_DOT}"
_H5 = f"## 5 {_DOT} Size, stop and close"
_RESUME = "## Resuming a worker"

# The two defaults of the size rule. A number is matched whole: 15 MB, 5.5 MB, 2500 tool calls and
# 250 tools are not these defaults.
_MEGABYTES = r"(?<![\d.])5\s*MB\b"
_TOOL_CALLS = r"(?<![\d.])250\s+tool\s+calls\b"
# A number of critic runs: the cap itself is plan-critic's, so the preamble states none.
_CRITIC_COUNT = r"\b(?:twice|(?:two|2)\s+(?:runs|times|passes))\b"
# A rule that names the Close block and says it is the brief's, in either order.
_CLOSE_POINTER = re.compile(
    r"\bclose block\b[^.]{0,30}\bbrief\b|\bbrief\b[^.]{0,30}\bclose block\b",
    re.IGNORECASE,
)
# The two rules of section 5 that name the Close block, by their leads.
_CLOSE_RULES = ("Plan the close", "Run the Close block")


class _Check(NamedTuple):
    label: str
    pattern: re.Pattern[str]
    plant: str = ""  # for a forbidden check: a phrase the pattern must flag


class _Place(NamedTuple):
    name: str
    path: str
    locate: Callable[[str], str]
    required: tuple[_Check, ...]
    forbidden: tuple[_Check, ...] = ()


def _says(label: str, phrase: str) -> _Check:
    """A check for one phrase, matched on folded text with capitals ignored."""
    return _Check(label, re.compile(re.escape(phrase), re.IGNORECASE))


def _matches(label: str, regex: str, plant: str = "") -> _Check:
    return _Check(label, re.compile(regex, re.IGNORECASE), plant)


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space, so a re-wrapped
    line or a re-emphasised word is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _opens_with(item: str, lead: str) -> bool:
    """Whether the item, past its list marker and bold marks, begins with `lead`, capitals ignored.
    The item is read folded, so a lead that wraps over two lines is still found."""
    folded = _folded(item)
    marker = _MARKER.match(folded)
    bare = folded[marker.end() :] if marker else folded
    return bare.lower().startswith(lead.lower())


def _item_from(lines: list[str], index: int) -> str:
    """The line at `index` and the lines that belong to it: every line after it up to the next
    heading, up to the next list marker at the same or a shallower indent, and, after a blank line,
    up to the next line that is not indented. A continuation line stays in whether it is indented
    or sits in column 0, so a re-wrapped item is read whole."""
    line = lines[index]
    item = [line]
    after_blank = False
    for follow in lines[index + 1 :]:
        if not follow.strip():
            item.append(follow)
            after_blank = True
            continue
        shallow = _indent(follow) <= _indent(line)
        if _HEADING.match(follow) or (
            shallow and (_MARKER.match(follow) is not None or after_blank)
        ):
            break
        item.append(follow)
        after_blank = False
    return "\n".join(item)


def _list_item(text: str, lead: str) -> str:
    """The first list item whose folded text opens with `lead`, with its continuation lines. Only
    a line that carries a list marker opens an item, so a continuation line that happens to start
    with the words of a lead is never taken for one. Empty when no item opens with `lead`."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if _MARKER.match(line) is None:
            continue
        item = _item_from(lines, index)
        if _opens_with(item, lead):
            return item
    return ""


def _last_list_item(region: str) -> str:
    """The last list item of the region, with its continuation lines. Empty when it has none."""
    lines = region.split("\n")
    starts = [index for index, line in enumerate(lines) if _MARKER.match(line)]
    return _item_from(lines, starts[-1]) if starts else ""


def _paragraph(text: str, lead: str) -> str:
    """The first blank-line-separated block whose folded text opens with `lead`. Empty when none."""
    for block in re.split(r"\n\s*\n", text):
        if _folded(block).lower().startswith(lead.lower()):
            return block
    return ""


def _last_paragraph(text: str) -> str:
    """The last block of the text that is neither blank nor a `---` separator line."""
    blocks = [
        b for b in re.split(r"\n\s*\n", text.strip()) if b.strip() not in ("", "---")
    ]
    return blocks[-1] if blocks else ""


def _section_of(heading: str) -> Callable[[str], str]:
    return lambda text: _section(text, heading)


def _item_in(heading: str, lead: str) -> Callable[[str], str]:
    return lambda text: _list_item(_section(text, heading), lead)


def _paragraph_in(heading: str, lead: str) -> Callable[[str], str]:
    return lambda text: _paragraph(_section(text, heading), lead)


def _flat_gaps(place: _Place, flat: str) -> list[str]:
    gaps = [f"missing: {c.label}" for c in place.required if not c.pattern.search(flat)]
    gaps += [
        f"forbidden wording present: {c.label}"
        for c in place.forbidden
        if c.pattern.search(flat)
    ]
    return gaps


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"the place is missing from {place.path}"]
    return _flat_gaps(place, _folded(region))


def _close_pointer_gap(section_5: str, lead: str) -> str:
    """Why the rule `lead` of section 5 does not name the brief's Close block, or an empty string
    when it does."""
    item = _folded(_list_item(section_5, lead))
    if not item:
        return f"the rule {lead!r} is missing from section 5"
    if not _CLOSE_POINTER.search(item):
        return f"{lead!r} does not name the brief's Close block: {item}"
    return ""


def _close_pointer_gaps(section_5: str) -> list[str]:
    """The gaps of every Close-block rule of section 5: none when each names the brief's block."""
    return [
        gap for lead in _CLOSE_RULES if (gap := _close_pointer_gap(section_5, lead))
    ]


# --- the places -----------------------------------------------------------------------------------


def _rule(slug: str, lead: str, *checks: _Check) -> _Place:
    """One bullet of section 5, found by its lead."""
    return _Place(
        name=f"preamble-section-5-{slug}",
        path=_PREAMBLE,
        locate=_item_in(_H5, lead),
        required=(_says(f"the rule's lead, {lead!r}", lead), *checks),
    )


_PUBLISH = _Place(
    name="preamble-section-3-publish-before-extras",
    path=_PREAMBLE,
    locate=_paragraph_in(_H3, "Publish before extras"),
    required=(
        _says("the paragraph's lead", "Publish before extras"),
        _says("write the result", "write the result"),
        _says(
            "or create the branch or ref the brief names",
            "create the branch or ref your brief names",
        ),
        _says("before any optional verification", "before any optional verification"),
        _says("keep the evidence on disk", "evidence on disk"),
        _says(
            "a session limit stops every agent at once",
            "session limit stops every agent at once",
        ),
        _says("a resume starts from that state", "a resume starts from that state"),
    ),
)

_ACCEPTANCE = _Place(
    name="preamble-section-4-acceptance-table",
    path=_PREAMBLE,
    locate=_item_in(_H4, "Return acceptance criteria as a table"),
    required=(
        _says("the bullet's lead", "Return acceptance criteria as a table"),
        _says(
            "returned before the rest of the report", "before the rest of your report"
        ),
        _matches("state: met", r"(?<!not )\bmet\b"),
        _says("state: not met", "not met"),
        _says("state: superseded", "superseded"),
        _matches("state: operator-owned", r"\boperator[- ]owned\b"),
        _says("an evidence pointer each", "evidence pointer"),
        _says("the brief names who ticks the boxes", "who ticks the boxes"),
        _says("the brief names who writes the Status line", "Status line"),
        _says(
            "with no such line, edit no task file you do not own",
            "edit no task file you do not own",
        ),
    ),
)

_RULES = (
    _rule(
        "size-the-work",
        "Size the work first",
        _says("size it against the context", "against your context"),
        _says("split what will not fit into staged sessions", "staged sessions"),
        _says("set a stop line", "stop line"),
        _matches("the starting values are tagged uncalibrated", r"\buncalibrated\b"),
        _matches("transcript size, about 5 MB", _MEGABYTES),
        _matches("tool calls, about 250", _TOOL_CALLS),
    ),
    _rule(
        "plan-the-close",
        "Plan the close",
        _says("at a compaction notice", "compaction notice"),
        _says("start no new work", "no new work"),
        _says("write a continuation prompt", "continuation prompt"),
        _says("do not carry on through a compaction", "through a compaction"),
    ),
    _rule(
        "run-the-close-block",
        "Run the Close block",
        _matches("in the order the brief gives", r"\border\b"),
        _says("without waiting to be asked", "without waiting to be asked"),
        _says("a read-only sub-agent", "read-only sub-agent"),
        _says("that returns text is exempt", "exempt"),
    ),
    _rule(
        "sessions-are-the-operators",
        "Sessions are the operator",
        _says("never start a successor or peer session", "successor or peer session"),
        _says("propose it", "propose it"),
        _says("name its prompt and folder", "name its prompt and folder"),
        _says("ask first", "ask first"),
        _says(
            "a sub-agent the brief lets you launch is not one",
            "lets you launch is not one",
        ),
    ),
    _rule(
        "no-external-call",
        "No external call",
        _says("no call to an external service", "external service"),
        _says("no local stack", "local stack"),
        _says(
            "unless the brief names the call as approved", "approved by the operator"
        ),
        _says("allow by name, not ban by name", "allow by name"),
        _says("a check that could not run is UNKNOWN", "UNKNOWN"),
    ),
    _rule(
        "plan-critic",
        "If you run",
        _says("names plan-critic", "plan-critic"),
        _says("within its own run cap", "own run cap"),
        _says("and no more often", "no more often"),
    ),
)

_NO_CRITIC_COUNT = _Place(
    name="preamble-section-5-no-critic-run-count",
    path=_PREAMBLE,
    locate=_section_of(_H5),
    required=(),
    forbidden=(
        _matches("a number of critic runs", _CRITIC_COUNT, plant="Run it twice."),
        _matches(
            "a number of critic runs", _CRITIC_COUNT, plant="Run it at most two runs."
        ),
    ),
)

_RESUME_BULLETS = (
    _Place(
        name="agent-delegate-resume-after-a-limit",
        path=_DELEGATE,
        locate=_item_in(_RESUME, "After a usage limit"),
        required=(
            _says("the bullet's lead", "After a usage limit"),
            _says("resume with SendMessage", "SendMessage"),
            _says(
                "say what was measured and what is left",
                "what you measured and what is left",
            ),
            _says("re-read the state by command", "re-read the state by command"),
            _says(
                "its last words can predate its last write",
                "last words can predate its last write",
            ),
            _says("resumed after more than an hour", "more than an hour"),
            _says("a finished sub-agent re-sent its report", "re-sent its old report"),
            _matches(
                "both observations carry their tag", r"observed once.*observed once"
            ),
        ),
    ),
    _Place(
        name="agent-delegate-resume-near-the-window",
        path=_DELEGATE,
        locate=_item_in(_RESUME, "Near the context window"),
        required=(
            _says("the bullet's lead", "Near the context window"),
            _says("the resume compacts almost at once", "compacts almost at once"),
            _says("past the prompt-cache lifetime", "prompt-cache"),
            _says("the claim is reasoned, not tried", "reasoned, not tried"),
            _says("resume only well under the window", "well under its window"),
            _says("otherwise a fresh session", "fresh session"),
            _says("whose brief points at the return note", "return note"),
        ),
    ),
)

_PLACES: tuple[_Place, ...] = (
    _PUBLISH,
    _ACCEPTANCE,
    *_RULES,
    _NO_CRITIC_COUNT,
    *_RESUME_BULLETS,
)
_IDS = [p.name for p in _PLACES]
_SECTION_5_PLACES = (*_RULES, _NO_CRITIC_COUNT)


# --- fixtures for the scan helper -------------------------------------------------------------------

# Every rule reworded and present: the wording differs from the shipped text, the load-bearing
# phrases do not.
_REWORDED_SECTION_5 = f"""{_H5}

- **Size the work first.** Measure it against your context before starting. If it cannot fit one
  session, say so and break it into staged sessions, one prompt each. Pick a stop line in whatever
  unit your host shows (transcript size, tool calls, tokens). Starting values, uncalibrated and not
  measured: roughly 5MB of transcript or roughly 250 tool calls.
- **Plan the close.** On reaching the stop line, or on a compaction notice, take on no new work: run
  your brief's Close block and write a continuation prompt for the rest. Never push on through a
  compaction.
- **Run the Close block of your brief**, in order, without waiting to be asked. A read-only
  sub-agent returning text is exempt.
- **Sessions are the operator's to open.** Do not start a successor or peer session yourself: propose
  it, name its prompt and folder, and ask first. A sub-agent your brief lets you launch is not one.
- **No external call by default.** Call no external service and start no local stack unless your
  brief names that call as approved by the operator; allow by name, never ban by name. Record what
  you could not check as UNKNOWN with its command.
- **If you run `lemmi-ai-kit-core:plan-critic` on a document, run it within its own run cap**,
  and no more often.
"""


def _dedented(text: str) -> str:
    """Every continuation line moved to column 0."""
    return re.sub(r"(?m)^[ \t]+(?=\S)", "", text)


def _joined(text: str) -> str:
    """Every item on one line: an indented continuation line is joined to the line before it."""
    return re.sub(r"\n[ \t]+(?=\S)", " ", text)


def _split_inside_the_numbers(text: str) -> str:
    """A line break inside each of the two defaults, between the number and its unit."""
    return text.replace("5MB", "5\n  MB").replace(
        "250 tool calls", "250\n  tool\n  calls"
    )


def _swap(text: str, old: str, new: str) -> str:
    """A planted edit that must find its anchor exactly once, so it cannot change nothing."""
    assert text.count(old) == 1, f"planted edit: {old!r} stands {text.count(old)} times"
    return text.replace(old, new)


def _fill(block: list[str], width: int, indent: str) -> list[str]:
    """The lines of one paragraph or list item, joined and wrapped at `width`."""
    if not block:
        return []
    joined = " ".join(" ".join(block).split())
    return [
        textwrap.fill(
            joined,
            width=width,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
    ]


def _rewrapped(text: str, width: int, indent: str) -> str:
    """Every paragraph and list item of the text re-wrapped at `width`, a break falling wherever
    it falls. Headings, `---` lines, table rows, fenced blocks and blank lines stay as they are."""
    wrapped: list[str] = []
    block: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        verbatim = (
            fence
            or in_fence
            or not line.strip()
            or _HEADING.match(line) is not None
            or line.strip() == "---"
            or line.startswith("|")
        )
        if verbatim or _MARKER.match(line):
            wrapped += _fill(block, width, indent)
            block = []
        if verbatim:
            wrapped.append(line)
        else:
            block.append(line)
        if fence:
            in_fence = not in_fence
    wrapped += _fill(block, width, indent)
    return "\n".join(wrapped)


def _section_5_gaps(text: str) -> dict[str, list[str]]:
    return {place.name: _gaps(place, text) for place in _SECTION_5_PLACES}


# --- the tests on the shipped text ------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Eleven places in two files, six rules in section 5, and every bullet of section 5 is one
    of the six: a seventh bullet needs its own check before it can ship."""
    assert len(_PLACES) == 11, f"{len(_PLACES)} places, not the 11 stated"
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 2, f"{len(paths)} distinct files, not 2: {sorted(paths)}"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"
    assert len(_RULES) == 6, f"{len(_RULES)} rule places, not the 6 stated"
    bullets = [
        line
        for line in _section(_read(_PREAMBLE), _H5).split("\n")
        if line.startswith("- ")
    ]
    assert len(bullets) == len(_RULES), (
        f"section 5 has {len(bullets)} bullets, the guard checks {len(_RULES)}: {bullets}"
    )


@pytest.mark.parametrize("place", _PLACES, ids=_IDS)
def test_each_place_states_its_rule(place: _Place) -> None:
    """Red before the change: none of these places existed."""
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=_IDS)
def test_every_check_of_a_place_can_fail(place: _Place) -> None:
    """Fired at the shipped text: take out what one check looks for and that check, and not only
    the place, reports. A forbidden check is fired by planting its phrase."""
    region = place.locate(_read(place.path))
    assert region.strip(), f"the place is missing from {place.path}"
    flat = _folded(region)
    assert not _flat_gaps(place, flat), f"{place.name} has gaps before any mutation"
    blind = [
        c.label
        for c in place.required
        if f"missing: {c.label}" not in _flat_gaps(place, c.pattern.sub(" ", flat))
    ]
    blind += [
        c.label
        for c in place.forbidden
        if not c.plant
        or f"forbidden wording present: {c.label}"
        not in _flat_gaps(place, f"{flat} {c.plant}")
    ]
    assert not blind, f"{place.name}: checks that cannot fail: {blind}"


def test_section_3_closes_with_publish_before_extras() -> None:
    """The new paragraph is the last one of section 3, after the paragraphs it did not touch."""
    last = _folded(_last_paragraph(_section(_read(_PREAMBLE), _H3)))
    assert last.startswith("Publish before extras."), (
        f"the last paragraph of section 3: {last!r}"
    )


def test_section_4_closes_with_the_acceptance_bullet() -> None:
    """The new bullet is the last one of section 4, read whole whatever its wrap."""
    last = _last_list_item(_section(_read(_PREAMBLE), _H4))
    assert last, "section 4 has no list item"
    assert _opens_with(last, "Return acceptance criteria as a table."), last


def test_section_5_follows_section_4_and_closes_the_file() -> None:
    """Sections 0 to 5 in order, each once, so sections 3, 4 and 5 are disjoint; section 5 is the
    last heading of the file and follows a `---` separator line."""
    lines = _read(_PREAMBLE).split("\n")
    headings = [line for line in lines if line.startswith("## ")]
    numbered = [h for h in headings if re.match(rf"## \d {_DOT} ", h)]
    assert [h[:4] for h in numbered] == [f"## {n}" for n in range(6)], numbered
    assert headings[-1] == _H5, f"the last heading is {headings[-1]!r}, not {_H5!r}"
    before = [line for line in lines[: lines.index(_H5)] if line.strip()]
    assert before[-1] == "---", f"section 5 follows {before[-1]!r}, not a `---` line"


def test_resuming_a_worker_closes_skill_md() -> None:
    """The new section is the last one of the file, after the second-opinion mode."""
    headings = [line for line in _read(_DELEGATE).split("\n") if line.startswith("## ")]
    assert headings.count(_RESUME) == 1, (
        f"{headings.count(_RESUME)} headings {_RESUME!r}"
    )
    assert headings[-1] == _RESUME, (
        f"the last heading is {headings[-1]!r}, not {_RESUME!r}"
    )


@pytest.mark.parametrize("lead", _CLOSE_RULES)
def test_section_5_points_at_the_close_block_of_the_brief(lead: str) -> None:
    """The Close block lives in the brief. The preamble names it and does not restate it, so its
    wording is not asserted here."""
    gap = _close_pointer_gap(_section(_read(_PREAMBLE), _H5), lead)
    assert not gap, gap


# --- the scan helper, fired at known positives and near-misses --------------------------------------


@pytest.mark.parametrize(
    ("text", "names_it"),
    [
        ("run the Close block of your brief and write", True),
        ("run your brief's Close block and write", True),
        ("Run the Close block, in its order", False),
        ("run the close steps of your brief", False),
        (
            "Run the Close block, then write the return note that your brief names",
            False,
        ),
        (
            "Read your brief, and then, much later on, run the Close block",
            False,
        ),
    ],
)
def test_the_close_pointer_tells_a_pointer_from_a_bare_close(
    text: str, names_it: bool
) -> None:
    assert bool(_CLOSE_POINTER.search(text)) is names_it, text


def test_a_reworded_section_5_passes_the_scan() -> None:
    """The near-miss: every rule worded differently and still present, and the two rules that
    name the Close block still say it is the brief's."""
    gaps = {
        name: found
        for name, found in _section_5_gaps(_REWORDED_SECTION_5).items()
        if found
    }
    assert not gaps, gaps
    assert not _close_pointer_gaps(_REWORDED_SECTION_5)


@pytest.mark.parametrize(
    "variant",
    [_dedented, _joined, _split_inside_the_numbers],
    ids=[
        "continuation-lines-in-column-0",
        "one-line-per-item",
        "break-inside-each-number",
    ],
)
def test_a_re_wrapped_section_5_passes_the_scan(variant: Callable[[str], str]) -> None:
    """A re-wrap changes no rule, so it must not change a verdict, the two numbers included."""
    wrapped = variant(_REWORDED_SECTION_5)
    assert wrapped != _REWORDED_SECTION_5, "the planted re-wrap changed nothing"
    gaps = {name: found for name, found in _section_5_gaps(wrapped).items() if found}
    assert not gaps, gaps
    assert not _close_pointer_gaps(wrapped)


@pytest.mark.parametrize("rule", _RULES, ids=[r.name for r in _RULES])
def test_a_section_5_that_lacks_one_rule_is_flagged_and_no_other_rule_with_it(
    rule: _Place,
) -> None:
    """The planted fixture: the near-miss with one rule cut out, and again with only its lead left."""
    region = rule.locate(_REWORDED_SECTION_5)
    assert region.strip(), f"the fixture holds no {rule.name}"
    lead = region.split("**")[1].rstrip(".")
    cut = _section_5_gaps(_REWORDED_SECTION_5.replace(region, ""))
    assert cut[rule.name] == [f"the place is missing from {rule.path}"], cut
    assert {n: g for n, g in cut.items() if n != rule.name and g} == {}, cut
    kept = f"- **{lead}.**\n"
    hollow = _section_5_gaps(_REWORDED_SECTION_5.replace(region, kept))
    left = [
        f"missing: {c.label}"
        for c in rule.required
        if not c.pattern.search(_folded(kept))
    ]
    assert left, (
        f"the lead of {rule.name} satisfies every check, so a hollow rule would pass"
    )
    assert hollow[rule.name] == left, hollow[rule.name]
    assert {n: g for n, g in hollow.items() if n != rule.name and g} == {}, hollow


@pytest.mark.parametrize(
    ("old", "new", "lead"),
    [
        (
            "run\n  your brief's Close block and write",
            "run\n  the closing steps and write",
            "Plan the close",
        ),
        (
            "- **Run the Close block of your brief**, in order,",
            "- **Run the Close block**, in order,",
            "Run the Close block",
        ),
    ],
    ids=["plan-the-close", "run-the-close-block"],
)
def test_a_close_rule_that_loses_its_pointer_is_flagged_and_no_other_rule_with_it(
    old: str, new: str, lead: str
) -> None:
    """The near-miss with the pointer cut out of one of the two rules that carry it."""
    gaps = _close_pointer_gaps(_swap(_REWORDED_SECTION_5, old, new))
    assert len(gaps) == 1 and lead in gaps[0], gaps


@pytest.mark.parametrize(
    ("width", "indent"),
    [(40, "  "), (40, "")],
    ids=["width-40-indented", "width-40-column-0"],
)
def test_a_narrow_re_wrap_of_the_shipped_text_changes_no_verdict(
    width: int, indent: str
) -> None:
    """Both shipped files re-wrapped narrow enough that the bold lead of the acceptance bullet
    breaks over two lines: no place goes missing, and section 4 still closes with that bullet."""
    wrapped: dict[str, str] = {}
    for path in sorted({place.path for place in _PLACES}):
        wrapped[path] = _rewrapped(_read(path), width, indent)
        assert wrapped[path] != _read(path), f"the re-wrap changed nothing in {path}"
    gaps: dict[str, list[str]] = {}
    for place in _PLACES:
        found = _gaps(place, wrapped[place.path])
        if found:
            gaps[place.name] = found
    assert not gaps, gaps
    lead = "- **Return acceptance criteria as a table.**"
    assert lead not in wrapped[_PREAMBLE], "the re-wrap no longer breaks the bold lead"
    closing = _last_list_item(_section(wrapped[_PREAMBLE], _H4))
    assert _opens_with(closing, "Return acceptance criteria as a table."), closing


_ACCEPTANCE_ITEM = (
    "- **Return acceptance criteria as a table.** If your brief points at a task file, return "
    "them first: one state each and one evidence pointer each."
)


@pytest.mark.parametrize("words", range(2, 9))
def test_a_lead_that_wraps_over_two_lines_is_still_found(words: int) -> None:
    """The bullet broken after each of its first words in turn, which cuts the bold lead at every
    point and then leaves it whole: the lead is matched on the folded item, never on one line."""
    parts = _ACCEPTANCE_ITEM.split(" ")
    item = " ".join(parts[:words]) + "\n  " + " ".join(parts[words:])
    section = "\n".join(
        [f"{_H4} Returning your result", "", "- **An earlier bullet.** Its text.", item]
        + ["", "---", ""]
    )
    lead = "Return acceptance criteria as a table"
    assert _folded(_list_item(section, lead)) == _folded(_ACCEPTANCE_ITEM)
    assert _opens_with(_last_list_item(_section(section, _H4)), lead + ".")


def test_the_section_slicer_sees_planted_text() -> None:
    """A decoy heading that only mentions the heading is not the heading, a `#` line inside a
    fenced block neither ends a section nor starts one, and a heading of the same level ends it."""
    planted = "\n".join(
        [
            "### An aside on ## Alpha",
            "decoy body",
            "## Alpha",
            "first body",
            "```",
            "# a comment inside a fence is not a heading",
            "```",
            "after the fence",
            "### Alpha child",
            "child body",
            "## Beta",
            "second body",
        ]
    )
    alpha = _section(planted, "## Alpha")
    assert alpha.startswith("## Alpha\nfirst body"), alpha
    assert "after the fence" in alpha and "child body" in alpha, alpha
    assert "second body" not in alpha, alpha
    assert _section(planted, "## Gamma") == ""


def test_the_list_item_slicer_sees_planted_text() -> None:
    """A decoy that only mentions the lead mid-line is not the item, and neither is a continuation
    line that opens with the words of the lead. The item runs over its continuation lines and an
    indented paragraph after a blank line, and stops at a paragraph in column 0 after a blank
    line, at a sibling bullet and at a heading."""
    planted = "\n".join(
        [
            "- **Earlier.** A decoy that mentions the plan the close rule mid-line.",
            "- **Wrapped decoy.** A bullet whose second line opens with the words",
            "  plan the close as if it were a lead.",
            "- **Plan the close.** The first line of the item,",
            "  a continuation line,",
            "column zero too.",
            "",
            "  an indented paragraph after a blank line.",
            "",
            "A paragraph in column 0 after a blank line is not part of the item.",
            "- **Next.** The next sibling.",
            "- **Heading follows.** Text.",
            "## A heading",
            "- **After the heading.** Text.",
        ]
    )
    assert _folded(_list_item(planted, "Plan the close")) == (
        "- Plan the close. The first line of the item, a continuation line, column zero too. "
        "an indented paragraph after a blank line."
    )
    assert _folded(_list_item(planted, "Heading follows")) == "- Heading follows. Text."
    assert _list_item(planted, "A heading") == ""
    assert _list_item(planted, "An absent lead") == ""


def test_the_paragraph_slicer_sees_planted_text() -> None:
    """A block that only mentions the lead mid-text is not the paragraph that opens with it."""
    planted = (
        "A decoy block that mentions publish before extras mid-text.\n\n"
        "Publish before extras. The real block,\nwrapped over two lines.\n\nLast block."
    )
    assert _folded(_paragraph(planted, "Publish before extras")) == (
        "Publish before extras. The real block, wrapped over two lines."
    )
    assert _paragraph(planted, "An absent lead") == ""


@pytest.mark.parametrize(
    ("pattern", "text", "is_the_default"),
    [
        pytest.param(_MEGABYTES, "about 5 MB of transcript", True, id="5 MB"),
        pytest.param(_MEGABYTES, "about 5MB of transcript", True, id="5MB, no space"),
        pytest.param(
            _MEGABYTES, _folded("about 5\nMB of transcript"), True, id="5, break, MB"
        ),
        pytest.param(_MEGABYTES, "about 15 MB of transcript", False, id="15 MB"),
        pytest.param(_MEGABYTES, "about 5.5 MB of transcript", False, id="5.5 MB"),
        pytest.param(_MEGABYTES, "about 5 GB of transcript", False, id="5 GB"),
        pytest.param(_MEGABYTES, "about 5 MBit of transcript", False, id="5 MBit"),
        pytest.param(_TOOL_CALLS, "about 250 tool calls", True, id="250 tool calls"),
        pytest.param(
            _TOOL_CALLS,
            _folded("about 250\ntool\ncalls"),
            True,
            id="250, breaks, calls",
        ),
        pytest.param(_TOOL_CALLS, "about 2500 tool calls", False, id="2500 tool calls"),
        pytest.param(_TOOL_CALLS, "about 1250 tool calls", False, id="1250 tool calls"),
        pytest.param(_TOOL_CALLS, "about 250 tools", False, id="250 tools"),
        pytest.param(
            _TOOL_CALLS, "about 250 tool callsites", False, id="250 callsites"
        ),
    ],
)
def test_the_number_checks_tell_a_default_from_a_lookalike(
    pattern: str, text: str, is_the_default: bool
) -> None:
    assert bool(re.search(pattern, text, re.IGNORECASE)) is is_the_default, text


@pytest.mark.parametrize(
    ("text", "states_a_count"),
    [
        ("Run it twice.", True),
        ("at most two runs", True),
        ("2 runs, no more", True),
        ("two times", True),
        ("2 passes", True),
        ("within its own run cap, and no more often", False),
        ("about 5 MB of transcript or about 250 tool calls, in two units", False),
        ("split it into two sessions", False),
    ],
)
def test_the_critic_count_guard_tells_a_count_from_other_numbers(
    text: str, states_a_count: bool
) -> None:
    assert bool(re.search(_CRITIC_COUNT, text, re.IGNORECASE)) is states_a_count, text
