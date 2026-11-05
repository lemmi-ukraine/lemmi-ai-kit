"""A delegated session claims its hand-off path with a stub before any precondition, and the pack says so.

A cross-session delegate is a session nobody can block on, and a path checked absent an hour earlier
can be a peer's by the time it is written. Nothing had the delegate write its hand-off first, so two
runs of one brief could both pass their preconditions and both do the work, and a peer looking for a
sign that the work was claimed found nothing until the first run ended.

What the text says now, in two places of the Orchestration pack and one new file:

* the cross-session list of `agent-delegate/SKILL.md` opens with the hand-off stub, ahead of the
  preconditions: the brief has the delegate create the hand-off path it names as a stub the hand-off
  lint accepts, with an operation that fails if the path exists (or read the write tool's
  created-or-replaced answer); an existing path or a reported replace is a stop (write nothing more
  and report it); a failed precondition sets the stub's Status to `blocked`. The item links the stub
  and says how much evidence it rests on: a small sample, not calibrated;
* `agent-delegate/assets/handoff-stub.md` is that stub: line 1 is the label of the newest contract
  version, the headings the lint requires follow in order, one command stands under each of
  Preconditions and Verification, and Status is `in-progress - not started`. It passes the lint, and
  it is smaller than the seeded template, which stays the full shape;
* section 6 of the dispatch gates says the stub a cross-session delegate writes first is the claim
  file, the liveness check that section asks for.

The two places that order a delegate's first step, the first-step bullet of `orchestrate` section 2b
and the Paste line section of the brief template, say the stub is that first write and the done
check, and the live-peer check follows it; they are read in `test_peer_brief_first_step.py`.

THE SURFACE, in numbers the tests assert: 2 places of text (the first item of the cross-session
list, and section 6 of the dispatch gates), judged by 7 requirements and 2 links; 1 stub file, judged
by 5 rules (the label on line 1, the lint, the headings, the Status line, one command each), among 9
planted defects, and each rule is the only one to report at least one of them. The order of the
cross-session list (the stub item first, the preconditions item second) is read by one helper and
fired at planted lists. A check holds when its text is in the place (lower-cased, whitespace
collapsed), and each requirement is removed from the real text one at a time and must be the only
thing reported; the wording that has to stay is fired at a section that lost it. Every label,
heading and section name of the stub is read from `checks`, never typed, so a new contract version
turns the stub's tests red. The stub's own checks are fired at a known-good stub that this file
carries, so that they are shown to see a defect whatever the shipped file holds, and the shipped
file is then held to them.

Known limit, stated and not fixed: the lint asks for non-empty sections, so a stub copied and left
with its example values passes. The brief tells the delegate to replace them.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

from lemmi_ai_kit import checks
from lemmi_ai_kit.manifest import assets_root

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_ITEM = re.compile(r"^\d+\. ")

_SKILLS = "plugins/orchestration/skills"
_DELEGATE = f"{_SKILLS}/agent-delegate/SKILL.md"
_STUB = f"{_SKILLS}/agent-delegate/assets/handoff-stub.md"
_GATES = f"{_SKILLS}/orchestrate/references/dispatch-gates.md"
_SEEDED = assets_root() / "ai" / "templates" / "handoff.md"

_CROSS_SESSION = "## Cross-session mode"
_DISPATCH_ITEM = "2. **Dispatch"
_STUB_LEAD = "- **The hand-off stub, before any precondition**"
_PRECONDITIONS_LEAD = "- **Preconditions as command + expected-result pairs**"
_STATUS_LINE = "**Status:** in-progress - not started"
_ARROW = chr(0x2192)
_DASH = chr(0x2014)
_SECT = chr(0xA7)


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
    # The place must link this file (a path relative to the repository root), or nothing.
    links_to: str = ""
    # Wording that has to stay: it is on the old text too, and must still be on the new.
    kept: tuple[_Check, ...] = ()


class _Rule(NamedTuple):
    """One rule a stub is held to: its name and the faults it finds in a text, one line each."""

    name: str
    problems: Callable[[str], list[str]]


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space, so a re-wrapped
    line or a re-emphasised word is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _has(flat: str, needle: str) -> bool:
    return needle.lower() in flat.lower()


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


def _cross_session_bullets(text: str) -> list[str]:
    """The bullets of the list under item 2 of the cross-session section, in order: a bullet
    starts at three spaces and a dash, and the lines that run on under it (five spaces) are part
    of it. The list ends at the next numbered item. Empty when the section or the item is not
    there, which the callers report by name."""
    inside = False
    bullets: list[str] = []
    for line in _section(text, _CROSS_SESSION).split("\n"):
        if line.startswith(_DISPATCH_ITEM):
            inside = True
        elif inside and _ITEM.match(line):
            break
        elif inside and line.startswith("   - "):
            bullets.append(line.strip())
        elif inside and bullets and line.startswith("     ") and line.strip():
            bullets[-1] = f"{bullets[-1]} {line.strip()}"
    return bullets


def _first_bullet(text: str) -> str:
    bullets = _cross_session_bullets(text)
    return bullets[0] if bullets else ""


def _gates_section_6(text: str) -> str:
    return _section(text, "## 6.")


def _links_to(region: str, path: str, target: str) -> bool:
    """Whether a prose link of `region` points at `target`, resolved from the file at `path`."""
    base = (_REPO_ROOT / path).parent
    wanted = (_REPO_ROOT / target).resolve()
    for link in _LINK.findall(region):
        name = link.split("#", 1)[0]
        if name and "://" not in name and (base / name).resolve() == wanted:
            return True
    return False


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


def _problems(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    flat = _folded(region)
    problems = [
        f"missing: {c.label}" for c in place.required if not _has(flat, c.needle)
    ]
    problems += [
        f"missing (kept): {c.label}" for c in place.kept if not _has(flat, c.needle)
    ]
    if place.links_to and not _links_to(region, place.path, place.links_to):
        problems.append(f"missing: a link to {place.links_to}")
    return problems


def _order_problems(text: str) -> list[str]:
    """Where the stub item stands in the list: first, with the preconditions item right after
    it. One line per fault; empty when it stands right."""
    bullets = _cross_session_bullets(text)
    if not bullets:
        return [f"no list under item 2 of {_CROSS_SESSION!r}"]
    problems: list[str] = []
    if not bullets[0].startswith(_STUB_LEAD):
        problems.append("the stub item is not the first item of the list")
    if len(bullets) < 2 or not bullets[1].startswith(_PRECONDITIONS_LEAD):
        problems.append("the preconditions item does not follow the stub item")
    return problems


# --- the stub file --------------------------------------------------------------------------------


def _newest() -> int:
    return max(checks.HANDOFF_SECTIONS_BY_VERSION)


def _label() -> str:
    return f"<!-- handoff-contract: v{_newest()} -->"


def _required() -> tuple[str, ...]:
    return (
        *checks.HANDOFF_REQUIRED_SECTIONS,
        *checks.HANDOFF_SECTIONS_BY_VERSION[_newest()],
    )


def _outside_comments(text: str) -> str:
    return _COMMENT.sub("", text)


def _headings(text: str) -> list[str]:
    return re.findall(r"^## (.+?)\s*$", _outside_comments(text), re.MULTILINE)


def _body(text: str, name: str) -> str:
    """The lines under `## name`, up to the next `## ` heading, comments removed, folded."""
    lines = _outside_comments(text).split("\n")
    start = next((i for i, line in enumerate(lines) if line == f"## {name}"), None)
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return " ".join(" ".join(body).split())


def _entries(text: str, name: str) -> int:
    """How many bullets stand under `## name`, outside comments."""
    lines = _outside_comments(text).split("\n")
    start = next((i for i, line in enumerate(lines) if line == f"## {name}"), None)
    if start is None:
        return 0
    count = 0
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            count += 1
    return count


def _label_problems(text: str) -> list[str]:
    """Line 1 is the label. It is checked here and not left to the lint: a note with no label is
    read as the older version, which asks for fewer sections, so the lint passes it."""
    lines = text.splitlines()
    first = lines[0].rstrip() if lines else ""
    if first == _label():
        return []
    return [f"line 1 is {first!r}, not the label {_label()!r}"]


def _lint_problems(text: str) -> list[str]:
    return [
        f"lint: {finding.message}"
        for finding in checks.lint_handoff(text, "handoff-stub.md")
    ]


def _heading_problems(text: str) -> list[str]:
    """The headings are the required sections, no more and in order: the lint asks only that
    each is there."""
    headings = _headings(text)
    if tuple(headings) == _required():
        return []
    return [f"headings are {headings}, not {list(_required())}"]


def _status_problems(text: str) -> list[str]:
    """The Status body is the not-started line exactly: the lint accepts any of its three words."""
    status = _body(text, "Status")
    if status == _STATUS_LINE:
        return []
    return [f"the Status section reads {status!r}, not {_STATUS_LINE!r}"]


def _command_problems(text: str) -> list[str]:
    problems: list[str] = []
    for name in checks.HANDOFF_COMMAND_SECTIONS:
        held = _entries(text, name)
        if held != 1:
            problems.append(f"'## {name}' holds {held} entries, not 1")
    return problems


_STUB_RULES: tuple[_Rule, ...] = (
    _Rule("label", _label_problems),
    _Rule("lint", _lint_problems),
    _Rule("headings", _heading_problems),
    _Rule("status", _status_problems),
    _Rule("commands", _command_problems),
)


def _stub_problems(text: str) -> list[str]:
    """Why `text` is not a hand-off stub, from every rule in turn; empty when it is."""
    return [problem for rule in _STUB_RULES for problem in rule.problems(text)]


# A stub at its smallest, carried here so that every check above is shown to see a defect whatever
# the shipped file holds: the label, the headings in order, one command each, Status not started.
_GOOD_STUB = f"""{_label()}
# Hand-off: {{slug}}

<!--
A comment is blanked by the lint: `## Status` here is not a section.
-->

## Scope
- **In (may change):** the slice the brief names

## Durable anchors
- Branch and commit: `chore/example-branch` at `abc1234`

## Preconditions
- `git rev-parse --abbrev-ref HEAD` -> `chore/example-branch`

## Verification
- `<the brief's definition-of-done command>` -> <its expected result>

## Status
{_STATUS_LINE}

## Continue
Not started. A new session reads the brief that named this path and begins there.

## Orchestrator summary
Not started: this file only holds the path for the session that wrote it.
"""


def _without_section(text: str, name: str) -> str:
    return re.sub(
        rf"^## {re.escape(name)}\n.*?(?=^## |\Z)",
        "",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )


def _with_body(text: str, name: str, body: str) -> str:
    out, hits = re.subn(
        rf"^(## {re.escape(name)}\n).*?(?=^## |\Z)",
        lambda m: m.group(1) + body + "\n\n",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert hits == 1, f"the text has no '## {name}' section"
    return out


def _swapped_sections(text: str, first: str, second: str) -> str:
    """`text` with the sections `## first` and `## second` exchanged. They must be the last two
    of the text, `first` right before `second`; anything else fails here."""
    head, found, rest = text.partition(f"## {first}\n")
    body_first, middle, body_second = rest.partition(f"## {second}\n")
    assert found and middle, f"no '## {first}' followed by '## {second}' in the text"
    assert "\n## " not in body_second, f"'## {second}' is not the last section"
    return f"{head}## {second}\n{body_second.rstrip()}\n\n## {first}\n{body_first.rstrip()}\n"


def _planted_stubs() -> dict[str, tuple[str, str]]:
    """Nine defects planted in the known-good stub, each with the words its report must hold.
    Three of them (an extra section, two sections exchanged, a Status word with no
    not-started clause) pass the lint, so only the stub's own rules can see them."""
    good = _GOOD_STUB
    return {
        "Status says not started with no status word": (
            _with_body(good, "Status", "**Status:** not started"),
            "'## Status' must state one of",
        ),
        "Status says done, a word outside the three": (
            _with_body(good, "Status", "**Status:** done - not started"),
            "must state one of",
        ),
        "no Continue section": (
            _without_section(good, "Continue"),
            "missing required section '## Continue'",
        ),
        "no label on line 1": (
            good.split("\n", 1)[1],
            "line 1 is",
        ),
        "Verification turned into prose": (
            _with_body(good, "Verification", "- the build is green"),
            "prose, not a runnable command",
        ),
        "two commands under Preconditions": (
            _with_body(
                good,
                "Preconditions",
                "- `git status --porcelain` -> empty\n- `git log -1` -> one line",
            ),
            "'## Preconditions' holds 2 entries, not 1",
        ),
        "an extra section after the last one": (
            f"{good}\n## Notes\n- anything\n",
            "headings are",
        ),
        "the last two sections exchanged": (
            _swapped_sections(good, "Continue", "Orchestrator summary"),
            "headings are",
        ),
        "Status says in-progress with no not-started clause": (
            _with_body(good, "Status", "**Status:** in-progress"),
            "the Status section reads",
        ),
    }


# --- the text each place carried before -----------------------------------------------------------

_OLD_DELEGATE = f"""## Cross-session mode

`cross-session` is the one worker you **cannot spawn and cannot block on**.

The Process above changes in three places:

2. **Dispatch {_ARROW} emit, don't call.** Write a dispatch brief the user carries to the other session.
   On top of the normal brief contract it must carry:
   - **Preconditions as command + expected-result pairs**, never prose. `git rev-parse --verify
     <ref>` {_ARROW} resolves. `git status --porcelain` {_ARROW} empty. A prose precondition you author is the
     same defect as trusting one you receive, and it has already shipped false.
   - **The return path**: `.ai/handoffs/{{YYYY-MM-DD}}-{{slug}}.md`, and the instruction to write the
     hand-off there per the contract in `parallel-session-safety` {_SECT}9. Never ask for a paste-back.
3. **Verify {_ARROW} run the hand-off's own commands.**
"""

_OLD_GATES_6 = f"""## 6. Designing the gates that guard a dispatch {_DASH} three measured failure shapes

- **A deliverable-path gate detects DONE and is structurally blind to IN-FLIGHT.** Every gate tests
  either an input being ready or an output being absent, and that pair is exactly the signature of a
  session already mid-flight. A complete gate set is not a sufficient one; add a liveness check (claim file,
  recent mtime, the peer's own register row) before dispatching into a cleared blocker.
- **A gate written as a literal count decays into a false STOP the moment its directory legitimately
  grows.**

## 7. A changed decision reaches only the prompts someone sweeps
"""

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="agent-delegate-first-item",
        path=_DELEGATE,
        where="the first item of the cross-session list",
        locate=_first_bullet,
        required=(
            _Check(
                "the item is the hand-off stub, ahead of any precondition",
                "The hand-off stub, before any precondition",
            ),
            _Check(
                "the delegate creates the hand-off path as a stub the lint accepts",
                "create the hand-off path it names as a stub the hand-off lint accepts",
            ),
            _Check(
                "by an operation that fails if the path exists, or by reading the answer",
                "with an operation that fails if the path exists (or read the write "
                "tool's created-or-replaced answer)",
            ),
            _Check(
                "an existing path or a reported replace is a stop",
                "An existing path or a reported replace is a stop: write nothing more "
                "and report it",
            ),
            _Check(
                "a failed precondition sets the stub's Status to blocked",
                "A failed precondition sets the stub's Status to `blocked`",
            ),
            _Check(
                "the evidence level: a small sample, not calibrated",
                "a small sample, not calibrated",
            ),
        ),
        old=_OLD_DELEGATE,
        links_to=_STUB,
    ),
    _Place(
        name="dispatch-gates-section-6",
        path=_GATES,
        where="section 6 of the dispatch gates",
        locate=_gates_section_6,
        required=(
            _Check(
                "the stub a cross-session delegate writes first is the claim file",
                "The stub a cross-session delegate writes first is the claim file",
            ),
        ),
        old=_OLD_GATES_6,
        links_to=_DELEGATE,
        kept=(
            _Check(
                "the liveness check names a claim file, a recent mtime and a register row",
                "add a liveness check (claim file, recent mtime, the peer's own register "
                "row) before dispatching into a cleared blocker",
            ),
        ),
    ),
)


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Two places in two files, 7 requirements and 2 links among them, a stub judged by 5 rules
    and fired at 9 planted defects; every file present and non-empty."""
    required = [check for place in _PLACES for check in place.required]
    links = [place.links_to for place in _PLACES if place.links_to]
    assert (len(_PLACES), len(required), len(links)) == (2, 7, 2)
    paths = {place.path for place in _PLACES}
    assert len(paths) == 2, f"{len(paths)} files, not 2: {sorted(paths)}"
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"
    rules = [rule.name for rule in _STUB_RULES]
    assert len(rules) == 5, f"{len(rules)} rules, not the 5 stated: {rules}"
    assert len(set(rules)) == len(rules), "two rules share a name"
    assert len(_planted_stubs()) == 9
    assert len(_headings(_GOOD_STUB)) == len(_required())


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_states_the_stub_rule(place: _Place) -> None:
    """Red before the change: no place said a delegate writes a stub first."""
    problems = _problems(place, _read(place.path))
    assert not problems, f"{place.path} ({place.name}): {problems}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_fails_on_the_text_it_replaced(place: _Place) -> None:
    """Fired at the old text: every requirement and every link reports it, and what has to stay
    is still there."""
    reported = _problems(place, place.old)
    expected = [f"missing: {c.label}" for c in place.required]
    if place.links_to:
        expected.append(f"missing: a link to {place.links_to}")
    assert reported == expected, (
        f"{place.name}: on the old text the checks reported {reported}"
    )


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_requirement_is_load_bearing(place: _Place) -> None:
    """Removing one requirement from the real text reports that one and no other."""
    assert place.required, f"{place.name} has no requirement to remove"
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


def test_a_gates_section_that_lost_its_liveness_phrase_is_reported() -> None:
    """The wording that had to stay is shown to be checked: the real section passes, and the same
    section with the liveness sentence cut out reports that one requirement and no other. Green on
    the old text too: the phrase stood there before the stub was added."""
    place = _PLACES[1]
    text = _read(place.path)
    assert _problems(place, text) == [], (
        "the real text must pass before it can be planted on"
    )
    assert len(place.kept) == 1, f"{len(place.kept)} kept phrases, not 1"
    kept = place.kept[0]
    planted = _plant(text, kept.needle, "")
    assert _problems(place, planted) == [f"missing (kept): {kept.label}"]


def test_the_stub_item_is_first_and_the_preconditions_item_follows_it() -> None:
    """Red before the change: the preconditions item was the first of the list, and `before any
    precondition` in the lead of the stub item is a claim about the order."""
    assert _order_problems(_read(_DELEGATE)) == []


def test_the_order_check_reports_each_way_the_list_can_stand_wrong() -> None:
    """Fired at planted lists: the old list (no stub item), the stub item second, the stub item
    last with the preconditions item first, and no list at all."""
    stub = f"   {_STUB_LEAD}: the stub.\n"
    preconditions = f"   {_PRECONDITIONS_LEAD}, never prose.\n"
    other = "   - **The return path**: a path.\n"
    head = f"{_CROSS_SESSION}\n\nIntro.\n\n{_DISPATCH_ITEM} emit.**\n   On top of it:\n"
    tail = "3. **Verify.**\n"
    assert _order_problems(f"{head}{stub}{preconditions}{other}{tail}") == []
    not_first = "the stub item is not the first item of the list"
    not_followed = "the preconditions item does not follow the stub item"
    assert _order_problems(f"{head}{preconditions}{other}{tail}") == [
        not_first,
        not_followed,
    ]
    assert _order_problems(f"{head}{preconditions}{stub}{tail}") == [
        not_first,
        not_followed,
    ]
    assert _order_problems(f"{head}{stub}{other}{preconditions}{tail}") == [
        not_followed
    ]
    assert _order_problems(f"{head}{tail}") == [
        f"no list under item 2 of {_CROSS_SESSION!r}"
    ]
    assert _order_problems("no section here\n") == [
        f"no list under item 2 of {_CROSS_SESSION!r}"
    ]


def test_the_item_links_the_stub_file() -> None:
    """Red before the change for the text itself: no item linked a stub. A link to another file
    is a stub the delegate cannot copy."""
    assert _links_to(_first_bullet(_read(_DELEGATE)), _DELEGATE, _STUB)


def test_the_stub_file_exists() -> None:
    """Red before the change only for want of the file (a weak red, named as one); a dead link
    fails the audit, so the file the item links must be there."""
    assert (_REPO_ROOT / _STUB).is_file(), f"{_STUB} does not exist"


def test_a_link_to_a_missing_file_or_another_file_is_not_a_link_to_the_stub() -> None:
    """The link check can fail: a real link is found; a link to a missing file and a link to
    another file that exists are not."""
    assert _links_to("[x](assets/handoff-stub.md)", _DELEGATE, _STUB)
    for text in (
        "[x](assets/no-such-file.md)",
        "[x](assets/worker-preamble.md)",
        "[x](https://example.invalid/assets/handoff-stub.md)",
    ):
        assert not _links_to(text, _DELEGATE, _STUB), text


# --- the stub file --------------------------------------------------------------------------------


def _stub() -> str:
    path = _REPO_ROOT / _STUB
    if not path.is_file():
        pytest.fail(f"the hand-off stub {_STUB} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_the_shipped_stub_meets_every_rule_of_a_stub() -> None:
    """Red before the change for want of the file; the rules it is held to are shown to see a
    defect by the planted tests below."""
    problems = _stub_problems(_stub())
    assert not problems, problems


def test_the_stub_rules_pass_the_known_good_stub() -> None:
    assert _stub_problems(_GOOD_STUB) == []


@pytest.mark.parametrize("name", sorted(_planted_stubs()))
def test_each_defect_planted_in_a_stub_is_reported(name: str) -> None:
    planted, words = _planted_stubs()[name]
    assert planted != _GOOD_STUB, f"{name}: the planted defect changed nothing"
    problems = _stub_problems(planted)
    assert any(words in problem for problem in problems), (
        f"{name}: expected a report holding {words!r}, got {problems}"
    )


def test_every_rule_of_a_stub_is_the_only_reporter_of_a_planted_defect() -> None:
    """A rule that every planted defect also trips another rule on has not been shown to see
    anything: take it out and every planted test stays green. Each rule reports at least one
    planted defect that no other rule reports."""
    alone: dict[str, list[str]] = {rule.name: [] for rule in _STUB_RULES}
    for name, (planted, _words) in _planted_stubs().items():
        reporting = [rule.name for rule in _STUB_RULES if rule.problems(planted)]
        if len(reporting) == 1:
            alone[reporting[0]].append(name)
    never = sorted(rule for rule, names in alone.items() if not names)
    assert not never, f"rules never fired alone at a planted defect: {never}"


def test_a_stub_with_no_label_passes_the_lint_alone() -> None:
    """Why the label is a rule of its own: with line 1 gone the lint reads the note as the older
    version, which does not ask for the added sections, and says nothing."""
    unlabelled = _GOOD_STUB.split("\n", 1)[1]
    assert checks.lint_handoff(unlabelled, "handoff-stub.md") == []
    assert any(p.startswith("line 1 is") for p in _stub_problems(unlabelled))


def test_the_stub_is_smaller_than_the_seeded_template_and_has_its_headings() -> None:
    """At its smallest: fewer lines than the template, the same headings in the same order."""
    template = _SEEDED.read_text(encoding="utf-8")
    stub = _stub()
    assert len(stub.splitlines()) < len(template.splitlines())
    assert _headings(stub) == _headings(template)
    assert stub.splitlines()[0] == template.splitlines()[0]


def test_the_section_readers_see_a_heading_inside_a_comment_as_no_section() -> None:
    """Fired at the known-good stub, whose comment holds a `## Status` line: the reader does not
    take it for a section, so the real Status section is the one read."""
    assert _headings(_GOOD_STUB).count("Status") == 1
    assert _body(_GOOD_STUB, "Status") == _STATUS_LINE
    assert _entries(_GOOD_STUB, "Preconditions") == 1
    assert _entries(_GOOD_STUB, "No such section") == 0
    assert _body(_GOOD_STUB, "No such section") == ""


def test_a_list_is_cut_at_the_next_item_and_a_missing_one_is_empty() -> None:
    """The bullet finder keeps the lines that run on under a bullet, stops at the next numbered
    item, and finds nothing where the section or the item is absent."""
    text = (
        f"{_CROSS_SESSION}\n\n{_DISPATCH_ITEM} emit.**\n   On top of it:\n"
        "   - **One**: a line\n     that runs on.\n"
        "   - **Two**: another.\n"
        "3. **Verify.**\n   - **Not this one**: after the item.\n"
    )
    assert _cross_session_bullets(text) == [
        "- **One**: a line that runs on.",
        "- **Two**: another.",
    ]
    assert _cross_session_bullets("## Another section\n") == []
    assert _cross_session_bullets(f"{_CROSS_SESSION}\n\nNo item here.\n") == []
    assert _first_bullet("") == ""
