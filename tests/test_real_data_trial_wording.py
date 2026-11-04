"""A feature that reads files its authors did not write gets a real-data trial before verification.

Verifiers read what the builder built, and the builder's fixtures are shaped like the builder's own
files. A trial on real files that the authors did not write found in minutes what hundreds of
tests and a round of independent verifiers had not, and a lint that passed every hand-made fixture
failed a share of the real notes it was meant to read. The planning skills said nothing about it.

`spec-driven-dev` now carries one checklist item in its Verification group, and `test-planner`
carries one row in the technique table of its Step 2 (the input shape "files its authors did not
write"), each on one line. Both name the trial, say it runs before any independent verifier and say
its bar is set before the run; the checklist item points at "`test-planner`, Step 2", and the row
says that hand-made fixtures cannot replace the run. Both skills belong to the core pack, so
neither line uses the vocabulary of the orchestration pack.

THE SURFACE, in numbers the tests assert: 2 places in 2 files and 2 lines, each held whole
(lower-cased, bold marks dropped, whitespace collapsed); 3 phrases shared by both lines; 5
words of the orchestration pack that neither line may use. Each line occurs once in its place and
is fired at a planted removal and a planted cut of its last clause; each place is fired at the text
it replaced; a planted move shows a line is judged inside its own group or section; the table row
is held to the three cells of its table; and the added lines are scanned for an id, a path and a
commit id, with a planted control for each. A project's or a company's own name is not scanned for
here: it has no generic shape, and naming one in a test would publish it, so that part stays a
reading check.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"
_SPEC = _SKILLS / "spec-driven-dev" / "SKILL.md"
_PLANNER = _SKILLS / "test-planner" / "SKILL.md"
_HEADING = re.compile(r"^(#{1,6})\s")
_EM = chr(0x2014)

_GROUP_START = "**Verification**"
_GROUP_END = "**Requirements Output Contract**"


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same.
    A missing file is its own loud failure, never an empty match."""
    if not path.is_file():
        raise AssertionError(f"{path.name} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _flat(text: str) -> str:
    """Bold marks dropped, every run of whitespace one space, lower-cased: a re-wrapped line or
    a re-emphasised word is not a different sentence."""
    return " ".join(text.replace("**", "").split()).lower()


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or
    a higher level; a `#` line inside a fenced block is not a heading. A missing heading fails
    loudly, with the heading named."""
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
    if not body:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


def _verification_group(text: str, where: str) -> str:
    """The lines from the Verification group's bold title to the title of the next group."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith(_GROUP_START)]
    if len(starts) != 1:
        raise AssertionError(f"{where}: {len(starts)} lines start {_GROUP_START!r}")
    ends = [
        i
        for i, line in enumerate(lines)
        if i > starts[0] and line.startswith(_GROUP_END)
    ]
    if not ends:
        raise AssertionError(f"{where}: no line starts {_GROUP_END!r} after the group")
    return "\n".join(lines[starts[0] : ends[0]])


def _step_2(text: str, where: str) -> str:
    return _section(text, "## Step 2", where)


_CHECKLIST_LINE = (
    "- [ ] a feature that reads files its authors did not write has a real-data trial planned "
    "before any independent verifier runs, its bar set before the run (`test-planner`, step 2)"
)
_TABLE_ROW = (
    "| files its authors did not write | real-data trial before the independent verifiers; "
    "the bar (for example, no file newly failing) is set before the run | 1 run over a real "
    "sample, which hand-made fixtures cannot replace |"
)
_SHARED_PHRASES = ("files its authors did not write", "real-data trial", " bar ")
# Words of the orchestration pack: a Core-only project has no such pack to read them in.
_PACK_WORDS = ("wave", "orchestrat", "sub-agent", "worker", "builder")

# The checklist's Verification group as it stood: the lines are unedited.
_OLD_GROUP = f"""\
**Verification** *(Medium and Large tasks whose design touches executable code)*
- [ ] A verification plan exists {_EM} `test-plan.md`, plus `test-cases.md` for Large
- [ ] Every condition cites a source id, and no Given/When/Then text is copied from requirements
- [ ] Every condition names the design technique used to expand it into cases
- [ ] Every case has exactly one owning level; upward moves carry a written reason and exclusions are stated
- [ ] Every expected result cites the id it derives from {_EM} zero cases marked `[UNGROUNDED]`
- [ ] Every NFR has a verification method, and no category the project's testing conventions ban is assigned `automated`
- [ ] Deliberate non-coverage is stated with risk bands and rationale
- [ ] Reconciliation with `tasks.md` is complete in both directions, or explicitly marked pending

**Requirements Output Contract** {_EM} a requirements document is READY when ALL of the following are true:
"""

# Step 2 of the planner as it stood: its heading and its table of five rows, unedited.
_OLD_STEP_2 = f"""\
## Step 2 {_EM} Expand conditions into cases, with a named technique

| Input shape | Technique | Typical case count |
|---|---|---|
| A numeric or ordered range | Equivalence Partitioning + Boundary Value Analysis | 1 per partition + 2 per boundary |
| A set of business rules that combine | Decision table | 1 per reachable rule combination |
| Behaviour that depends on prior events | State transition | 1 per valid transition + key invalid ones |
| Many independent parameters | Pairwise | 1 per covering pair, not the full cross-product |
| Unordered sets, booleans, enums | Decision table {_EM} **never** BVA | 1 per value or rule |

## Step 3 {_EM} Assign exactly one owning level
"""


class _Place(NamedTuple):
    name: str
    path: Path
    locate: Callable[[str, str], str]
    line: str
    old: str


_PLACES: tuple[_Place, ...] = (
    _Place("checklist-item", _SPEC, _verification_group, _CHECKLIST_LINE, _OLD_GROUP),
    _Place("table-row", _PLANNER, _step_2, _TABLE_ROW, _OLD_STEP_2),
)


def _gap(place: _Place, text: str) -> list[str]:
    """The line of the place when its region does not hold it whole, else nothing."""
    flat = _flat(place.locate(text, place.path.name))
    return [] if place.line in flat else [place.line]


def _real(place: _Place) -> str:
    return _read(place.path)


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    """2 places in 2 files and 2 lines, 3 shared phrases and 5 pack words; each line is lower-case
    and holds the phrases both lines share."""
    assert len(_PLACES) == 2
    assert len({p.path for p in _PLACES}) == 2
    assert len({p.line for p in _PLACES}) == 2
    assert len(_SHARED_PHRASES) == 3 and len(_PACK_WORDS) == 5
    for place in _PLACES:
        assert place.line == place.line.lower(), place.name
        for phrase in _SHARED_PHRASES:
            assert phrase in place.line, (place.name, phrase)


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_states_its_line(place: _Place) -> None:
    """Red before the change: neither line existed."""
    assert _gap(place, _real(place)) == []


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_line_occurs_once_and_is_reported_when_it_goes(place: _Place) -> None:
    """Planted removal: the line cut out of the real place is the gap reported, and an empty
    region lacks it. A line that occurred twice would let one copy go and stay green."""
    flat = _flat(place.locate(_real(place), place.path.name))
    assert flat.count(place.line) == 1, (
        f"the line occurs {flat.count(place.line)} times"
    )
    assert place.line not in flat.replace(place.line, "")
    assert place.line not in ""


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_clause_cut_from_its_line_is_reported(place: _Place) -> None:
    """Planted clause removal: the words after the last comma of the line are cut out of the real
    place, and the place then lacks the line. A check on a fragment would stay green."""
    flat = _flat(place.locate(_real(place), place.path.name))
    tail = re.split(r", ", place.line)[-1]
    assert tail != place.line, "no clause to cut"
    assert flat.count(tail) == 1, f"{tail!r} is not a clause of one line"
    assert place.line not in flat.replace(tail, "")


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_place_reports_the_text_it_replaced(place: _Place) -> None:
    """Known positive: the group and the section as they stood lack the line, so a red on the old
    text is a red for the text and not for a broken helper."""
    assert _gap(place, place.old) == [place.line]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_re_emphasised_line_is_the_same_line(place: _Place) -> None:
    """Near-miss that must NOT be reported: bold marks around the trial's name and a doubled space
    are the same text."""
    text = _real(place)
    region = place.locate(text, place.path.name)
    start = region.lower().index("real-data trial")
    end = start + len("real-data trial")
    reshaped = f"{region[:start]}**{region[start:end]}**{region[end:]}".replace(
        "authors did not", "authors  did not", 1
    )
    assert reshaped.count("**") == region.count("**") + 2, (
        "the planted emphasis changed nothing"
    )
    assert "authors  did not" in reshaped, "the planted double space changed nothing"
    assert reshaped != region
    # The reshaped region goes back into the whole file, where the finders locate it again.
    assert text.count(region) == 1, "the region is not in the file exactly once"
    assert _gap(place, text.replace(region, reshaped, 1)) == []


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_line_is_judged_inside_its_own_place_only(place: _Place) -> None:
    """Planted move: the line cut out of its group or section and put after the last line of the
    file is a place that lacks it. A search of the whole file would still find it and pass."""
    text = _real(place)
    original = next(
        line
        for line in place.locate(text, place.path.name).split("\n")
        if place.line in _flat(line)
    )
    moved = text.replace(original + "\n", "", 1) + original + "\n"
    assert moved != text
    assert _gap(place, moved) == [place.line]
    assert place.line in _flat(moved), "a whole-file search would have failed"


def test_a_missing_group_or_section_fails_loudly() -> None:
    """A skill without the group, with the group's title twice or without the next title, and one
    without Step 2 are each reported by name and never read as an empty pass."""
    with pytest.raises(AssertionError, match="0 lines start"):
        _verification_group("# Skill\n\ntext\n", "SKILL.md")
    with pytest.raises(AssertionError, match="2 lines start"):
        _verification_group(
            f"{_GROUP_START} a\n{_GROUP_START} b\n{_GROUP_END}\n", "SKILL.md"
        )
    with pytest.raises(AssertionError, match="no line starts"):
        _verification_group(f"{_GROUP_START} a\n- [ ] x\n", "SKILL.md")
    with pytest.raises(AssertionError, match="no heading starting"):
        _step_2("## Step 1\n\ntext\n", "SKILL.md")
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-skill.md"))


# --- where the text sits -----------------------------------------------------------------------


def _cells(row: str) -> int:
    return len(row.strip().strip("|").split("|"))


def test_the_row_keeps_the_three_cells_of_its_table_and_comes_last() -> None:
    """A row with a stray pipe would break the table. The table of Step 2 keeps its header, its
    separator and the five rows it had, and the new row is the sixth, with three cells."""
    table = [
        line
        for line in _step_2(_read(_PLANNER), "SKILL.md").split("\n")
        if line.startswith("|")
    ]
    old = [line for line in _OLD_STEP_2.split("\n") if line.startswith("|")]
    assert len(table) == len(old) + 1, (len(table), len(old))
    assert {_cells(line) for line in table} == {3}, [_cells(line) for line in table]
    assert table[: len(old)] == old, "an old row was changed or moved"
    assert _flat(table[-1]) == _TABLE_ROW


def test_the_checklist_item_sits_in_the_group_among_checkboxes_and_points_at_step_2() -> (
    None
):
    """The item is a checkbox of the Verification group, after the item about the method of every
    NFR, and the step it names ("`test-planner`, Step 2") is the heading that holds the row."""
    group = _verification_group(_read(_SPEC), "SKILL.md").split("\n")
    boxes = [line for line in group if line.startswith("- [ ] ")]
    assert len(boxes) == len(group) - 2, "a line of the group is not a checkbox"
    position = [i for i, line in enumerate(boxes) if _flat(line) == _CHECKLIST_LINE]
    assert len(position) == 1, position
    assert "every nfr has a verification method" in _flat(boxes[position[0] - 1])
    planner = _read(_PLANNER)
    assert planner.count("\n## Step 2 ") == 1
    assert _TABLE_ROW in _flat(_step_2(planner, "SKILL.md"))


def test_both_lines_say_the_same_things_in_the_same_words() -> None:
    """The three phrases the lines share are in each, and each says when the trial runs: before
    an independent verifier. One edit that changes only one line turns this red."""
    for place in _PLACES:
        assert re.search(r"before (?:any|the) independent verifier", place.line), (
            place.name
        )
        assert "set before the run" in place.line, place.name


# --- the added lines are neutral ---------------------------------------------------------------

# The shapes are generic, so the scan names no project.
_LEAKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a request id", re.compile(r"\b[A-Z]{1,4}-\d{1,3}\b")),
    # One group for the home paths: the publication-hygiene test forbids the spelled-out
    # literal in every tracked file, this one included.
    ("an absolute local path", re.compile(r"(?:\b[A-Za-z]:[\\/]|/(?:Users|home)/)")),
    ("a commit-id-like token", re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")),
)


def _leaks(text: str) -> list[str]:
    """The shapes of a leak in `text`, and each word of the orchestration pack, by name."""
    shapes = [label for label, pattern in _LEAKS if pattern.search(text)]
    flat = _flat(text)
    return shapes + [f"pack word {word!r}" for word in _PACK_WORDS if word in flat]


def test_the_added_lines_name_no_id_path_commit_or_pack_word() -> None:
    """The kit is public and both skills are Core's. The two lines carry none of the shapes."""
    for place in _PLACES:
        assert _leaks(place.line) == [], place.name
        original = next(
            line
            for line in place.locate(_real(place), place.path.name).split("\n")
            if place.line in _flat(line)
        )
        assert _leaks(original) == [], place.name


def test_the_leak_scan_sees_each_shape_and_spares_the_near_misses() -> None:
    """Known positives, one per shape and one for a pack word, and near-misses that stay clean."""
    planted = {
        "a request id": "see " + "K" + "-8 for the reason",
        "an absolute local path": "read " + "C:" + "/Us" + "ers/someone/notes.md",
        "a commit-id-like token": "as of commit " + "0a1b2c3d4e",
        "pack word 'wave'": "a trial before the verifier wave",
    }
    shapes = {label for label, _ in _LEAKS} | {"pack word 'wave'"}
    assert set(planted) == shapes
    for label, text in planted.items():
        assert _leaks(text) == [label], (label, _leaks(text))
    for word in _PACK_WORDS:
        assert _leaks(f"a {word} here") == [f"pack word {word!r}"], word
    for clean in (
        "a real-data trial before any independent verifier runs, its bar set first",
        "see `test-planner`, Step 2, for the 3 files and 12 lines it names",
        "a defaced page and an effaced line",
    ):
        assert _leaks(clean) == [], clean
