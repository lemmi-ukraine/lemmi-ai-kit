"""A peer brief's first step finds work already done or already running, and its paste line says where.

Section 2 of `orchestrate` guards the dispatcher with `ListAgents` before it writes a brief, and
section 2b asked for preconditions as commands, a named return path and isolated peers. All of
that guards the dispatcher at the moment it dispatches. Nothing asked the delegate's own first
step to look for a return note or a live peer, which is the check that stops a window the user
opens later from a stale or repeated paste line, and nothing asked the paste line to say which
repository folder the session belongs in.

What the text says now:

* section 2b has a bullet for the delegate's first step. The first write is the hand-off stub at the
  return path, made only if the path is absent, and that is the done check (the return note exists;
  `git log -1` on its own paths). A live-peer check (the host's live-session list, else files
  changed in 30 minutes at its target paths) follows it. The delegate stops on either, and a live
  peer sets the stub `blocked`. The bullet says the paste line carries the state, the repository
  folder and the branch, and links the brief template;
* section 2b's lead-in no longer counts its rules ("Three rules make that survivable"), since a
  count written by hand is wrong the day a bullet is added;
* the brief template has a "Paste line" section: the line carries the state (not started, running
  in a named window, or done), the repository folder and the branch, each compared with what the
  delegate finds; a line that disagrees, or that holds a placeholder, is a stop that writes nothing
  more. Its lead-in names the items without counting them ("carries three things" is retired, for
  the reason the lead-in of section 2b lost its count). The section ends with the order of the
  first step: the stub is the first write and that write is the done check, the live-peer check
  follows it, and a live peer sets the stub `blocked`.

Both places once put the done check and the live-peer check before any write, which is the opposite
of a stub written first. That wording is retired, and each place is fired at the text that held it.

Every check is fired at the text its place carried before (`old`), and each requirement is removed
from the real text one at a time and must be the only thing reported. A bullet, a section or a link
that goes missing fails with a message that names it, not with an empty pass. The plant that turns
the bullet's last clause into its opposite goes through a whitespace-tolerant pattern, so a
re-wrapped clause is planted on and read like the same clause. The three helpers that find a
section or a bullet and fold its lines have a test of their own, since every check reads the text
through them.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_FENCED = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_DASH = chr(0x2014)
_SECT = chr(0xA7)

_SKILLS = "plugins/orchestration/skills"
_ORCHESTRATE = f"{_SKILLS}/orchestrate/SKILL.md"
_TEMPLATE = f"{_SKILLS}/orchestrate/references/brief-template.md"
_BULLET_LEAD = "- **The first step finds a duplicate.**"
_STOPS = "stops on either"
# The lead-in of the Paste line section as it first stood, and as it reads now.
_FIRST_LEAD_IN = (
    "The line carries three things, so that the delegate's first precondition can compare "
    "each with what it finds:"
)
_LEAD_IN = (
    "The line carries the items below, so that one of the delegate's preconditions can "
    "compare each with what it finds:"
)


class _Check(NamedTuple):
    label: str
    needle: str


class _Place(NamedTuple):
    name: str
    path: str
    where: str
    locate: Callable[[str], str]
    required: tuple[_Check, ...]
    old: str
    retired: tuple[_Check, ...] = ()
    # A link from the place to this file is required (a path relative to the repository root).
    links_to: str = ""


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


def _list_item(text: str, lead: str) -> str:
    """The first line that starts with `lead` and the lines that belong to it: every line after
    it up to the next heading, up to the next list marker at the same or a shallower indent, and,
    after a blank line, up to the next line that is not indented. A continuation line stays in
    whether it is indented or sits in column 0, so a re-wrapped item is read whole. Empty when no
    line starts with `lead`."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if not line.startswith(lead):
            continue
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
    return ""


def _section_of(heading: str) -> Callable[[str], str]:
    return lambda text: _section(text, heading)


def _item_of(lead: str) -> Callable[[str], str]:
    return lambda text: _list_item(text, lead)


def _has(flat: str, needle: str) -> bool:
    return needle.lower() in flat.lower()


def _plant(text: str, phrase: str, replacement: str) -> str:
    """`text` with the one place `phrase` stands replaced, wherever a re-wrap put its line breaks.
    A phrase that stands nowhere, or more than once, fails here, so a plant that changed nothing
    cannot stand in for a check that fired."""
    pattern = r"\s+".join(re.escape(word) for word in phrase.split())
    spots = list(re.finditer(pattern, text))
    assert len(spots) == 1, (
        f"{phrase!r} stands {len(spots)} times in the text, not once"
    )
    return text[: spots[0].start()] + replacement + text[spots[0].end() :]


def _links_to(region: str, path: str, target: str) -> bool:
    """Whether a prose link of `region` points at the file `target`, resolved from `path`."""
    base = (_REPO_ROOT / path).parent
    wanted = (_REPO_ROOT / target).resolve()
    for link in _LINK.findall(_FENCED.sub("", region)):
        name = link.split("#", 1)[0]
        if name and "://" not in name and (base / name).resolve() == wanted:
            return True
    return False


def _problems(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    flat = _folded(region)
    problems = [
        f"missing: {c.label}" for c in place.required if not _has(flat, c.needle)
    ]
    problems += [
        f"retired wording still there: {c.label}"
        for c in place.retired
        if _has(flat, c.needle)
    ]
    if place.links_to and not _links_to(region, place.path, place.links_to):
        problems.append(f"missing: a link to {place.links_to}")
    return problems


# --- the text each place carried before -----------------------------------------------------------

_OLD_ORCHESTRATE_2B = f"""### 2b. Dispatching to a peer session (cross-session)
A peer session is not a tool call: you emit a brief, the user carries it, and the result comes back
as a file. Three rules make that survivable {_DASH} the full contract is in `agent-delegate`
(dispatch-brief shape) and `parallel-session-safety` (handoff artifact schema):

- **Preconditions are commands, not prose.** Write every state claim as something the delegate
  runs (`git rev-parse --verify <ref>`, `git status --porcelain`), with its expected result.
- **Name the return path** in the brief: `.ai/handoffs/{{YYYY-MM-DD}}-{{slug}}.md`. Never ask the user
  to paste results back by hand; that is the ritual this replaces.
- **Stack layers are pinned; surgery is boundary-only.** A brief dispatching a stacked-PR layer
  names the branch and its base.

### 3. Review before merging {_DASH} results are claims
"""

_OLD_TEMPLATE_TAIL = """- **The report is for a decision, not a story.** If the orchestrator can't accept/reject the
  result from the report in under a minute, ask for less prose and more evidence.
"""

# The two places as they stood after the stub was written first elsewhere in the pack and before they
# said so: both put the done check and the live-peer check ahead of any write.
_BULLET_AHEAD_OF_THE_STUB = """- **The first step finds a duplicate.** Before any write the delegate runs a done check (the return note
  exists; `git log -1` on its own paths) and a live-peer check (the host's live-session list, else files
  changed in 30 minutes at its target paths) and stops on either; the
  [paste line](references/brief-template.md) carries state, repository folder and branch.
"""

_PASTE_LINE_AHEAD_OF_THE_STUB = f"""## Paste line

A peer session the user drives starts from one pasted line, and the brief is the file it points at.
The line carries the items below, so that one of the delegate's preconditions can compare each with
what it finds:

- the state: not started, running in a named window, or done;
- the repository folder, compared with `git rev-parse --show-toplevel`;
- the branch, compared with `git rev-parse --abbrev-ref HEAD`.

A line that disagrees with what the delegate finds, or that holds a placeholder, is a stop: the
delegate writes nothing and says so in one sentence. The delegate's first step, before any write, is
a done check (the return note at the named return path exists) and a live-peer check, as `SKILL.md`
{_SECT} 2b says: copy both into the brief's preconditions.
"""


# --- the places -----------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="orchestrate-2b-first-step",
        path=_ORCHESTRATE,
        where="the first-step bullet of section 2b of orchestrate",
        locate=_item_of(_BULLET_LEAD),
        required=(
            _Check(
                "the first step finds a duplicate", "The first step finds a duplicate"
            ),
            _Check(
                "the first write is the hand-off stub, made only if the path is absent",
                "The first write is the hand-off stub at the return path, made only if "
                "the path is absent",
            ),
            _Check("the stub is the done check", "that is the done check"),
            _Check("the done check reads the return note", "the return note exists"),
            _Check(
                "the done check reads the log of its own paths",
                "`git log -1` on its own paths",
            ),
            _Check(
                "a live-peer check follows the stub", "a live-peer check follows it"
            ),
            _Check(
                "the host's live-session list, else files changed in 30 minutes",
                "the host's live-session list, else files changed in 30 minutes at its "
                "target paths",
            ),
            _Check("it stops on either", "stops on either"),
            _Check(
                "a live peer sets the stub to blocked",
                "a live peer sets the stub `blocked`",
            ),
            _Check(
                "the paste line carries state, repository folder and branch",
                "[paste line](references/brief-template.md) carries state, repository folder "
                "and branch",
            ),
        ),
        old=_OLD_ORCHESTRATE_2B,
        retired=(
            _Check(
                "both checks ran before any write",
                "Before any write the delegate runs a done check",
            ),
        ),
        links_to=_TEMPLATE,
    ),
    _Place(
        name="orchestrate-2b-lead-in",
        path=_ORCHESTRATE,
        where="section 2b of orchestrate",
        locate=_section_of("### 2b."),
        required=(
            _Check("the rules are not counted", "These rules make that survivable"),
        ),
        old=_OLD_ORCHESTRATE_2B,
        retired=(
            _Check(
                "the rules were counted by hand", "Three rules make that survivable"
            ),
        ),
    ),
    _Place(
        name="brief-template-paste-line",
        path=_TEMPLATE,
        where="the Paste line section of the brief template",
        locate=_section_of("## Paste line"),
        required=(
            _Check(
                "a peer session starts from one pasted line",
                "A peer session the user drives starts from one pasted line",
            ),
            _Check(
                "the lead-in names the items below without counting them",
                "The line carries the items below",
            ),
            _Check(
                "the state: not started, running in a named window, or done",
                "the state: not started, running in a named window, or done",
            ),
            _Check(
                "the repository folder, compared with the top-level folder",
                "the repository folder, compared with `git rev-parse --show-toplevel`",
            ),
            _Check(
                "the branch, compared with the current branch",
                "the branch, compared with `git rev-parse --abbrev-ref HEAD`",
            ),
            _Check(
                "a line that disagrees with what the delegate finds is a stop",
                "disagrees with what the delegate finds",
            ),
            _Check(
                "a placeholder in the line is a stop", "holds a placeholder, is a stop"
            ),
            _Check(
                "a stop sets the stub to blocked and writes nothing more",
                "the delegate sets the hand-off stub's Status to `blocked` and writes "
                "nothing more, and says so in one sentence",
            ),
            _Check(
                "the first write is the hand-off stub",
                "The delegate's first write is the hand-off stub",
            ),
            _Check(
                "the done check reads the return note",
                "the return note at the named return path",
            ),
            _Check("the stub is the done check", "that write is the done check"),
            _Check(
                "the live-peer check follows the stub", "The live-peer check follows it"
            ),
            _Check(
                "a live peer sets the stub to blocked",
                "a live peer sets the stub `blocked`",
            ),
        ),
        old=_OLD_TEMPLATE_TAIL,
        retired=(
            _Check(
                "the lead-in counted its list by hand", "The line carries three things"
            ),
            _Check(
                "both checks ran before any write",
                "The delegate's first step, before any write, is a done check",
            ),
            _Check(
                "both checks were copied into the preconditions",
                "copy both into the brief's preconditions",
            ),
        ),
    ),
)


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Three places in two files of one pack, each present and non-empty."""
    assert len(_PLACES) == 3, f"{len(_PLACES)} places, not the 3 stated"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 2, f"{len(paths)} files, not 2: {sorted(paths)}"
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_peer_brief_has_a_first_step_and_a_paste_line(place: _Place) -> None:
    """Red before the change: 'first step' and 'paste line' had no hit in the pack."""
    problems = _problems(place, _read(place.path))
    assert not problems, f"{place.path} ({place.name}): {problems}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_fails_on_the_text_a_place_carried_before(place: _Place) -> None:
    """Fired at the old text. The bullet and the paste line section did not exist, so the place
    itself is what is reported missing; the lead-in reports its new wording and its retired one."""
    reported = _problems(place, place.old)
    if place.name == "orchestrate-2b-lead-in":
        expected = [f"missing: {c.label}" for c in place.required]
        expected += [f"retired wording still there: {c.label}" for c in place.retired]
        assert reported == expected
    else:
        assert reported == [f"{place.where} is missing from {place.path}"]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_requirement_is_load_bearing(place: _Place) -> None:
    """Removing one requirement from the real text reports that one and no other."""
    region = place.locate(_read(place.path))
    assert region.strip(), f"{place.where} is missing from {place.path}"
    flat = _folded(region)
    for check in place.required:
        start = flat.lower().find(check.needle.lower())
        assert start >= 0, f"{place.name}: {check.label!r} is not in the real text"
        stripped = flat[:start] + flat[start + len(check.needle) :]
        gaps = [c.label for c in place.required if not _has(stripped, c.needle)]
        assert gaps == [check.label], (
            f"{place.name}: removing {check.label!r} reported {gaps}"
        )


def test_a_bullet_that_proceeds_on_a_return_note_is_reported() -> None:
    """A first step that proceeds when the return note exists is the opposite of this rule. The
    real bullet passes; the same bullet with 'stops on either' replaced by that is reported."""
    place = _PLACES[0]
    text = _read(place.path)
    assert _problems(place, text) == [], (
        "the real bullet must pass before it can be planted on"
    )
    assert "proceed" not in _folded(place.locate(text)).lower()
    planted = _plant(text, _STOPS, "proceeds when the return note exists")
    assert _problems(place, planted) == ["missing: it stops on either"]


def test_a_rewrapped_clause_is_read_and_planted_on_like_the_same_clause() -> None:
    """'stops on either' broken across two lines, as a re-wrap leaves it, passes the checks and
    is still found by the plant."""
    place = _PLACES[0]
    rewrapped = _plant(_read(place.path), _STOPS, "stops on\n  either")
    assert _problems(place, rewrapped) == [], "a re-wrap is not a different clause"
    planted = _plant(rewrapped, _STOPS, "proceeds when the return note exists")
    assert _problems(place, planted) == ["missing: it stops on either"]


def test_a_plant_finds_its_phrase_wherever_a_rewrap_broke_the_line() -> None:
    """The plant itself can fail: it replaces a phrase split across lines, and it refuses a
    phrase that stands nowhere or more than once."""
    assert _plant("it stops on\n  either; the", _STOPS, "x") == "it x; the"
    for text in ("nothing of the kind here", f"{_STOPS} and {_STOPS}"):
        with pytest.raises(AssertionError, match="not once"):
            _plant(text, _STOPS, "x")


def test_a_paste_line_lead_in_that_counts_its_items_is_reported() -> None:
    """The section as first written said the line carries three things. Its list can grow, and
    a count written by hand is wrong the day an item is added: the real section with that lead-in
    put back reports the retired lead-in and the new one missing, and nothing else."""
    place = _PLACES[2]
    planted = _plant(_read(place.path), _LEAD_IN, _FIRST_LEAD_IN)
    assert _problems(place, planted) == [
        "missing: the lead-in names the items below without counting them",
        "retired wording still there: the lead-in counted its list by hand",
    ]


@pytest.mark.parametrize(
    ("index", "old", "expected"),
    (
        (
            0,
            _BULLET_AHEAD_OF_THE_STUB,
            [
                "missing: the first write is the hand-off stub, made only if the path is absent",
                "missing: the stub is the done check",
                "missing: a live-peer check follows the stub",
                "missing: a live peer sets the stub to blocked",
                "retired wording still there: both checks ran before any write",
            ],
        ),
        (
            2,
            _PASTE_LINE_AHEAD_OF_THE_STUB,
            [
                "missing: a stop sets the stub to blocked and writes nothing more",
                "missing: the first write is the hand-off stub",
                "missing: the stub is the done check",
                "missing: the live-peer check follows the stub",
                "missing: a live peer sets the stub to blocked",
                "retired wording still there: both checks ran before any write",
                "retired wording still there: both checks were copied into the preconditions",
            ],
        ),
    ),
    ids=["orchestrate-2b-first-step", "brief-template-paste-line"],
)
def test_the_wording_that_ran_both_checks_before_any_write_is_reported(
    index: int, old: str, expected: list[str]
) -> None:
    """Fired at the text each place carried before it said the stub is written first: the new
    requirements are missing, the retired sentence is there, and what stood before (the return note,
    the log of its own paths, the host's list, the stop, the link) still reads as it did."""
    assert _problems(_PLACES[index], old) == expected


@pytest.mark.parametrize(
    ("index", "phrase", "label"),
    (
        (0, "A live-peer check follows it", "a live-peer check follows the stub"),
        (2, "The live-peer check follows it", "the live-peer check follows the stub"),
    ),
    ids=["orchestrate-2b-first-step", "brief-template-paste-line"],
)
def test_a_live_peer_check_that_comes_before_the_stub_is_reported(
    index: int, phrase: str, label: str
) -> None:
    """The order is the claim: the real text passes, and the same text with only the verb changed,
    so that the live-peer check comes first, reports that requirement and no other. The words
    before the verb stay, so a check that stopped at them would not see the change."""
    place = _PLACES[index]
    text = _read(place.path)
    assert _problems(place, text) == [], (
        "the real text must pass before it can be planted on"
    )
    flipped = phrase.replace("follows it", "comes first")
    assert flipped != phrase, "the plant changed nothing"
    planted = _plant(text, phrase, flipped)
    assert _problems(place, planted) == [f"missing: {label}"]


def test_the_fold_joins_a_rewrapped_sentence_and_drops_bold_marks() -> None:
    """Every check reads the text through the fold: lines join, a run of spaces is one space,
    bold marks go, the ends are trimmed."""
    assert _folded("  a **bold**  word\n     and a second\nline  \n") == (
        "a bold word and a second line"
    )


_SECTIONS = "\n".join(
    [
        "#### 2b. A look-alike that only contains the wanted prefix",
        "### 2b. First",
        "first body",
        "#### 2b.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "```",
        "### 3. Second",
        "second body",
        "## 4. Higher",
        "higher body",
        "",
    ]
)


def test_a_section_runs_to_the_next_heading_of_its_level_or_a_higher_one() -> None:
    """The section finder starts at the heading that begins with its text, keeps a deeper heading
    and a `#` line inside a fence, stops at a heading of its own level or a higher one, and
    finds nothing for a heading that is not there."""
    first = _section(_SECTIONS, "### 2b.")
    assert first.startswith("### 2b. First"), first
    for kept in ("first body", "deeper body", "a comment in a fence"):
        assert kept in first, first
    assert "second body" not in first, first
    second = _section(_SECTIONS, "### 3.")
    assert "second body" in second and "higher body" not in second, second
    assert _section(_SECTIONS, "### 9.") == ""


_TWO_ITEMS = "\n".join(
    [
        "- **First.** one",
        "  wrapped and indented",
        "wrapped in column zero",
        "  - nested stays inside",
        "- **Second.** two",
        "",
        "Not part of any item.",
        "",
    ]
)


def test_a_list_item_runs_to_the_next_item_and_keeps_its_wrapped_lines() -> None:
    """The bullet finder keeps an indented and a column-zero continuation and a nested bullet,
    stops at the next bullet of its own level, at a heading, and after a blank line at the first
    line that is not indented, and finds nothing for a lead that is not there."""
    first = _list_item(_TWO_ITEMS, "- **First.**")
    for kept in (
        "wrapped and indented",
        "wrapped in column zero",
        "nested stays inside",
    ):
        assert kept in first, first
    assert "two" not in first, first
    second = _list_item(_TWO_ITEMS, "- **Second.**")
    assert "two" in second and "Not part of any item" not in second, second
    assert "heading" not in _list_item(
        "- **Only.** one\n### A heading\n", "- **Only.**"
    )
    assert _list_item(_TWO_ITEMS, "- **Third.**") == ""


def test_a_link_to_a_missing_file_is_not_a_link_to_the_template() -> None:
    """The link check can fail: a real link is found; a link to a missing file, a link to
    another file that exists and a link inside a fenced block are not."""
    linked = "See [brief template](references/brief-template.md)."
    assert _links_to(linked, _ORCHESTRATE, _TEMPLATE)
    for text in (
        "See [brief template](references/no-such-file.md).",
        "See [brief template](references/dispatch-gates.md).",
        "```\n[brief template](references/brief-template.md)\n```",
    ):
        assert not _links_to(text, _ORCHESTRATE, _TEMPLATE), text


def test_a_missing_place_is_a_failure_with_a_name() -> None:
    """A bullet or a section that goes missing must not read as a pass."""
    for place in _PLACES:
        assert _problems(place, "### Another section\n\nText.\n") == [
            f"{place.where} is missing from {place.path}"
        ]
