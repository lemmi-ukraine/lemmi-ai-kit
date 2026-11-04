"""learning-consolidator lists every copy of the buffer before a drain and reads parked lessons.

The cadence guard and Phase 1 read the checked-out buffer, so a drain that starts from that file
alone misses an entry only another copy holds (a stash, a branch ahead of the trunk, a backup), and
a drain whose changelog entry sits on a branch that never merges reads as no drain. The skill also
had no step for lessons a project parks in its hand-off notes, and nothing asked whether an entry's
Impact advises what the project's standing policies forbid. Phase 1 step 1 now points at a
reference section that lists the copies, folds in what only a copy holds, puts the drain's
changelog entry on the branch that merges and reads parked lessons (conditionally, because the
kit's hand-off contract requires no lessons section); the PROMOTE_TO_RULE criteria gain a
standing-policy check on the Impact. A folded entry goes under its own category section, the
placement rule of `task-learnings`, and never at the file end; the section names the Steps of
Phase 2 that archive an entry a drain removed; and Operator Steps counts the read of a copy as a
step with a row of its own, its stated count compared with the rows of its table.

Each assertion reads one named file, section or list, and a missing heading fails loudly. The
checks are functions over a string, so `test_every_check_sees_its_planted_positive` fires them at
the old text and at half-edits before their silence on the real files is trusted, and
`test_each_phrase_deleted_in_turn_is_reported` deletes every phrase of the shipped text in turn.
The printed commands are run in a throwaway repository with one stash and one branch ahead, so
they are shown to print what the text says they print, and the learnings guard's shape judge is
asked about each read form (it names the buffer after a colon) beside known positives.
Every non-ASCII character in a fixture is built from `chr()`.

THE SURFACE, in numbers the tests assert: 2 files, 4 places (Phase 1 step 1, the new section, the
PROMOTE_TO_RULE criteria, Operator Steps), 3 + 24 + 4 phrases and 2 + 2 + 1 more for Operator
Steps, 3 old shapes, 3 printed commands.
"""

import importlib.util
import re
import shlex
import subprocess
import textwrap
from collections.abc import Callable
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "learning-consolidator"
_SKILL = _SKILL_DIR / "SKILL.md"
_REFERENCE = _SKILL_DIR / "references" / "consolidation-actions.md"
_GUARD = _REPO_ROOT / "plugins" / "core" / "hooks" / "gate_learnings_drain.py"
_SURFACE: tuple[Path, ...] = (_SKILL, _REFERENCE)

# The skill audit fails a SKILL.md at 500 lines and counts one more than the newline count.
_LINE_CAP = 499

_HEADING = re.compile(r"^(#{1,6})\s+\S")

_SKILL_NAME = "learning-consolidator SKILL.md"
_REFERENCE_NAME = "learning-consolidator references/consolidation-actions.md"

_COPIES_HEADING = "## Buffer Copies and Parked Lessons"
_BEFORE_HEADING = "## Section-Placement Audit"
_AFTER_HEADING = "## Verifying Parked Patterns"
_PHASE_1_HEADING = "### Phase 1: Inventory"
_RULE_HEADING = "### PROMOTE_TO_RULE"
_CRITERIA_LEAD = "**Criteria (ALL must be true):**"
_POLICY_WORDS = "standing polic"
_OPERATOR_HEADING = "## Operator Steps"
_COPIES_ROW_LEAD = "| Copies of the buffer (Phase 1, step 1) |"

_RULE_UNDER_HEADER = re.compile(r"\|[\s|:-]+\|")
_NUMBER_WORDS = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
}
_STATED_COUNT = re.compile(r"\b([A-Za-z]+) steps need bytes of the buffer\b")

_OLD_STEP_1 = "1. Read `.ai/learnings.md` in full."
_OLD_STEP_PROBLEM = "still the one-line step that reads the buffer"


# --- slicers over a string -----------------------------------------------------------------


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _view(text: str) -> str:
    """The text with every run of whitespace as one space and bold markers dropped."""
    return " ".join(text.split()).replace("**", "")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced block
    is a comment of the code it holds, not a heading. A missing heading fails with the heading
    named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _headings(text: str) -> list[str]:
    """Every heading line outside a fenced block, in order."""
    in_fence = False
    found: list[str] = []
    for line in text.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
        elif not in_fence and _HEADING.match(line):
            found.append(line)
    return found


def _slug(heading: str) -> str:
    """The anchor a renderer gives a heading: lower case, punctuation dropped, spaces as hyphens."""
    lowered = heading.lstrip("#").strip().lower()
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", lowered))


def _list_item(section: str, lead: str, where: str) -> str:
    """The list item whose first line starts with `lead`, with the indented lines that follow."""
    lines = section.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(lead)]
    if len(starts) != 1:
        raise AssertionError(f"{where}: {len(starts)} lines start with {lead!r}")
    item = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        item.append(line)
    return "\n".join(item).rstrip()


def _paragraph_starting(text: str, lead: str) -> str:
    """The blank-line-delimited paragraph that starts with `lead`; exactly one must."""
    found = [block for block in text.split("\n\n") if block.lstrip().startswith(lead)]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} paragraphs start with {lead!r}")
    return found[0]


def _missing(view: str, facts: dict[str, str]) -> list[str]:
    """The names of the facts whose pattern is not found in `view`."""
    return [
        name
        for name, pattern in facts.items()
        if not re.search(pattern, view, re.IGNORECASE)
    ]


# --- what the new text must say ------------------------------------------------------------

_POINTER_FACTS: dict[str, str] = {
    "the step lists every other copy of the buffer": (
        r"\bList every other copy of the buffer\b"
    ),
    "and then reads the buffer in full": r"\bthen read `\.ai/learnings\.md` in full\b",
    "the link to the new section": re.escape(
        "(references/consolidation-actions.md#buffer-copies-and-parked-lessons)"
    ),
}

_COPY_FACTS: dict[str, str] = {
    "the checked-out buffer alone misses an entry only another copy holds": (
        r"\bmisses an entry only another copy holds\b"
    ),
    "the entry stays out of every plan until the copy is merged or popped": (
        r"\bthe entry stays out of every plan until that copy is merged or popped\b"
    ),
    "the copies are listed before the buffer is read": (
        r"\bbefore reading the buffer, list its other copies\b"
    ),
    "each entry only a copy holds is folded into the one intake": (
        r"\bfold each entry only a copy holds into the one intake\b"
    ),
    "a dry run lists the copies and appends nothing": (
        r"\ba dry run lists the copies and appends nothing\b"
    ),
    "stashes are listed with git stash list and each holds a copy": (
        r"`git stash list`.{0,40}\bEach stash holds its own copy of the buffer\b"
    ),
    "branches ahead of the trunk are listed with git branch --no-merged": (
        r"\bBranches ahead of the trunk\b.{0,40}`git branch --no-merged <trunk>`"
    ),
    "backups and snapshots, an earlier byte copy among them": (
        r"\bBackups and snapshots\b.{0,120}\bbyte copy\b"
    ),
    "the byte copy stays the operator's": r"\bThe byte copy stays the operator's\b",
    "reading a copy's bytes is an operator step in their own terminal": (
        r"\bReading a copy's bytes is an operator step\b.{0,160}\bown terminal\b"
    ),
    "the copy goes to a scratch file outside the buffer's folder": (
        r"\bscratch file outside the buffer's folder\b"
    ),
    "the session never names the buffer on a shell line": (
        r"\bthe session never names the buffer on a shell line\b"
    ),
    "entries are compared by heading line": (
        r"\bcompares its `### ` heading lines with the buffer's own\b"
    ),
    "a folded entry goes under its own category section, never at the file end": (
        r"\bwith Edit under its own `## ` category section \(the placement rule of "
        r"`task-learnings`\), never at the file end\b"
    ),
    "an entry both hold is never added twice": (
        r"\ban entry both hold is never added twice\b"
    ),
    "a copy made before the last drain holds entries that drain removed": (
        r"\bA copy made before the last drain also holds entries that drain removed\b"
    ),
    "Phase 2's Steps 1 and 2 archive them again, and they cost no promotion": (
        r"\bPhase 2's Steps 1 and 2 archive them again \(stale or superseded in Step 1, "
        r"already covered in Step 2\), so they cost a plan row and no promotion\b"
    ),
}

_BRANCH_FACTS: dict[str, str] = {
    "the drain's changelog entry goes on the branch that merges": (
        r"\bWrite the run's `CONSOLIDATION` entry in `\.ai/ai-changelog\.md` on the "
        r"branch that will merge\b"
    ),
    "the cadence guard reads the checked-out changelog": (
        r"\bcadence guard \(Phase 1, step 0\) reads the checked-out changelog\b"
    ),
    "a drain on a branch that never merges reads as no drain": (
        r"\ba drain recorded on a branch that never merges reads as no drain\b"
    ),
}

_LESSON_FACTS: dict[str, str] = {
    "conditional on the project's hand-off format having a lessons section": (
        r"\bIf the project's hand-off format has a section for lessons\b"
    ),
    "the section is read in Phase 1 and each lesson listed as an intake candidate": (
        r"\bread that section of the project's hand-off notes in Phase 1\b.{0,120}"
        r"\bintake candidate\b"
    ),
    "the kit's hand-off contract requires no such section": (
        r"\bkit's hand-off contract requires no such section\b"
    ),
    "none is copied into the buffer before the plan is approved": (
        r"\bnone is copied into the buffer before the operator approves the plan\b"
    ),
}

_SECTION_FACTS: dict[str, str] = {**_COPY_FACTS, **_BRANCH_FACTS, **_LESSON_FACTS}

_CRITERIA_FACTS: dict[str, str] = {
    "an Impact taken as advice breaks no standing policy": (
        r"\bImpact, taken as advice, breaks no standing policy of the project\b"
    ),
    "the policies are the AGENTS.md rules and the recorded rulings": (
        r"\bits AGENTS\.md rules and recorded rulings\b"
    ),
    "advice a policy forbids is not promoted": (
        r"\badvice a policy forbids is not promoted\b"
    ),
    "only its measured figures are kept, as data": (
        r"\bonly its measured figures are kept, as data\b"
    ),
}

# Operator Steps: the intro counts the steps and lists the copies as one, and the table holds a row
# for them, whose operator cell writes each copy to a scratch file and whose session cell folds it.
_OPERATOR_FACTS: dict[str, str] = {
    "the intro counts four steps": r"\bFour steps need bytes of the buffer\b",
    "the intro lists every other copy of the buffer as a step": (
        r"\bheading count at its commit \(Phase 1\), every other copy of the buffer "
        r"\(Phase 1\), the restore-point commit\b"
    ),
}

_OPERATOR_CELL_FACTS: dict[str, str] = {
    "the operator writes each copy to its own scratch file outside the buffer's folder": (
        r"\bwrites each copy to its own scratch file outside the buffer's folder\b"
    ),
    "by the command of the copies section": re.escape(f"(#{_slug(_COPIES_HEADING)})"),
}

_SESSION_CELL_FACTS: dict[str, str] = {
    "the session reads each scratch file and appends the entries only the copy holds": (
        r"\breads each scratch file, then appends the entries only the copy holds under "
        r"their own category sections\b"
    ),
}

# The old shapes of the folding paragraph, as the classes they came in: slug -> (pattern, what the
# old text did). The first and third are found in the old sentences below, the second in the alias.
_OLD_SHAPES: dict[str, tuple[str, str]] = {
    "append-after-the-last-entry": (
        r"\bafter the (?:buffer's )?last entry\b",
        "tells the session to append a folded entry after the last entry, the file end that the "
        "placement rule of the intake skill forbids",
    ),
    "append-at-the-end-of-the-file": (
        r"(?<!never )\b(?:at|to) the (?:end of the (?:file|buffer)|file end)\b",
        "says the same in other words",
    ),
    "the-coverage-check-alone-archives-them": (
        r"\bcoverage check archives them again\b",
        "names Step 2 alone for entries a drain also removed as stale or superseded, which Step 1 "
        "archives",
    ),
}

# The old sentences, verbatim, and the same instruction in other words.
_OLD_FOLDING = (
    "heading lines with the buffer's own, and appends each entry only the copy holds with Edit, "
    "after\nthe buffer's last entry; an entry both hold is never added twice. A copy made before "
    "the last drain\nalso holds entries that drain removed: Phase 2's coverage check archives "
    "them again, so they cost\na plan row and no promotion.\n"
)
_OLD_FOLDING_ALIAS = "Append each entry only the copy holds at the end of the buffer.\n"


# --- one check per place the rows name; each takes a whole file's text ----------------------


def _phase_1_step_1(skill: str) -> str:
    section = _section(skill, _PHASE_1_HEADING, _SKILL_NAME)
    return _list_item(section, "1. ", f"{_SKILL_NAME}, Phase 1")


def _pointer_gaps(skill: str) -> list[str]:
    return _missing(_view(_phase_1_step_1(skill)), _POINTER_FACTS)


def _old_step_problems(skill: str) -> list[str]:
    """Step 1 of the old text was one sentence that read the buffer and named no copy."""
    return [_OLD_STEP_PROBLEM] if _view(_phase_1_step_1(skill)) == _OLD_STEP_1 else []


def _copies_section(reference: str) -> str:
    return _section(reference, _COPIES_HEADING, _REFERENCE_NAME)


def _section_gaps(reference: str) -> list[str]:
    return _missing(_view(_copies_section(reference)), _SECTION_FACTS)


def _dead_anchors(section: str, reference: str) -> list[str]:
    """The in-page links of `section` whose anchor is no heading of `reference`."""
    slugs = {_slug(heading) for heading in _headings(reference)}
    return [a for a in re.findall(r"\]\(#([^)\s]+)\)", section) if a not in slugs]


def _criteria(reference: str) -> list[str]:
    """The items of the PROMOTE_TO_RULE criteria list, each folded."""
    section = _section(reference, _RULE_HEADING, _REFERENCE_NAME)
    lines = section.split("\n")
    if _CRITERIA_LEAD not in lines:
        raise AssertionError(f"{_REFERENCE_NAME}: no line {_CRITERIA_LEAD!r}")
    items: list[list[str]] = []
    for line in lines[lines.index(_CRITERIA_LEAD) + 1 :]:
        if not line.strip():
            break
        if line.startswith("- "):
            items.append([line])
        elif items:
            items[-1].append(line)
    return [_view("\n".join(item)) for item in items]


def _policy_item(items: list[str]) -> str:
    """The one criteria item that names a standing policy, or an empty string."""
    holders = [item for item in items if _POLICY_WORDS in item.lower()]
    return holders[0] if len(holders) == 1 else ""


def _criteria_gaps(reference: str) -> list[str]:
    items = _criteria(reference)
    gaps = _missing(_policy_item(items), _CRITERIA_FACTS)
    holders = sum(_POLICY_WORDS in item.lower() for item in items)
    if holders != 1:
        gaps.append(f"{holders} criteria items name a standing policy, not 1")
    if len(items) < 5:
        gaps.append(f"the list holds {len(items)} items, not 5 or more")
    return gaps


def _old_shapes(text: str) -> list[str]:
    """The slugs of the old shapes found in `text`."""
    view = _view(text)
    return [
        slug
        for slug, (pattern, _why) in _OLD_SHAPES.items()
        if re.search(pattern, view, re.IGNORECASE)
    ]


def _old_shape_problems(reference: str) -> list[str]:
    """The old shapes found in the copies section, and in no other section."""
    return [f"still says: {slug}" for slug in _old_shapes(_copies_section(reference))]


def _operator_section(reference: str) -> str:
    return _section(reference, _OPERATOR_HEADING, _REFERENCE_NAME)


def _table_rows(section: str) -> list[str]:
    """The data rows of the section's table: its bar lines after the header and the rule."""
    bars = [line for line in section.split("\n") if line.startswith("|")]
    if len(bars) < 3 or not _RULE_UNDER_HEADER.fullmatch(bars[1]):
        raise AssertionError(f"{_REFERENCE_NAME}: no table with a header and a rule")
    return bars[2:]


def _copies_row_cells(section: str) -> list[str]:
    """The three cells of the copies row; a missing row or another cell count fails loudly."""
    rows = [row for row in _table_rows(section) if row.startswith(_COPIES_ROW_LEAD)]
    if len(rows) != 1:
        raise AssertionError(
            f"{_REFERENCE_NAME}: {len(rows)} table rows start {_COPIES_ROW_LEAD!r}"
        )
    cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
    if len(cells) != 3:
        raise AssertionError(
            f"{_REFERENCE_NAME}: the copies row has {len(cells)} cells"
        )
    return cells


def _operator_gaps(reference: str) -> list[str]:
    """What Operator Steps lacks. The count the intro states is compared with the rows of the
    table, so the count and the rows cannot drift apart again."""
    section = _operator_section(reference)
    view = _view(section)
    gaps = _missing(view, _OPERATOR_FACTS)
    said = _STATED_COUNT.search(view)
    word = said.group(1).lower() if said else ""
    rows = _table_rows(section)
    if word not in _NUMBER_WORDS:
        gaps.append(f"the intro states no count of steps this test knows: {word!r}")
    elif _NUMBER_WORDS[word] != len(rows):
        gaps.append(f"the intro says {word} steps and the table holds {len(rows)} rows")
    try:
        _, operator, session = _copies_row_cells(section)
    except AssertionError as error:
        return [*gaps, str(error)]
    gaps += [
        f"operator cell: {n}" for n in _missing(_view(operator), _OPERATOR_CELL_FACTS)
    ]
    gaps += [
        f"session cell: {n}" for n in _missing(_view(session), _SESSION_CELL_FACTS)
    ]
    return gaps


def _reported(name: str, check: Callable[[str], list[str]], text: str) -> list[str]:
    """The problems of one check, a missing heading included, each led by `name`."""
    try:
        return [f"{name}: {problem}" for problem in check(text)]
    except AssertionError as error:
        return [f"{name}: {error}"]


def _problems(skill: str, reference: str) -> list[str]:
    """Every check over one SKILL.md text and one reference text, as a flat list."""

    def dead(text: str) -> list[str]:
        return _dead_anchors(_copies_section(text), text)

    def dead_operator(text: str) -> list[str]:
        return _dead_anchors(_operator_section(text), text)

    return [
        *_reported("phase 1 step 1", _pointer_gaps, skill),
        *_reported("phase 1 step 1", _old_step_problems, skill),
        *_reported("copies section", _section_gaps, reference),
        *_reported("copies section", _old_shape_problems, reference),
        *_reported("copies section anchors", dead, reference),
        *_reported("operator steps", _operator_gaps, reference),
        *_reported("operator steps anchors", dead_operator, reference),
        *_reported("promote-to-rule criteria", _criteria_gaps, reference),
    ]


# --- the printed commands ------------------------------------------------------------------

_PLACEHOLDERS = ("<trunk>", "<ref>", "<path>", "<scratch file>")

_VALUES = {
    "<trunk>": "main",
    "<ref>": "stash@{0}",
    "<path>": ".ai/learnings.md",
    "<scratch file>": "scratch-copy.txt",
}


def _printed_commands(section: str) -> list[str]:
    """The non-blank, non-comment lines of the fenced blocks of a section."""
    commands: list[str] = []
    in_fence = False
    for line in section.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
        elif in_fence and line.strip() and not line.strip().startswith("#"):
            commands.append(line.strip())
    return commands


def _substituted(command: str, values: dict[str, str]) -> str:
    for placeholder, value in values.items():
        command = command.replace(placeholder, value)
    return command


# --- the tests -----------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    assert len({path.resolve() for path in _SURFACE}) == 2, (
        "the two files must be distinct"
    )
    for path in _SURFACE:
        assert path.is_file(), f"{path.name} is not a file"
        assert _text(path).strip(), f"{path.name} is empty"
    _phase_1_step_1(_text(_SKILL))
    reference = _text(_REFERENCE)
    _criteria(reference)
    assert len(_POINTER_FACTS) == 3
    assert (len(_COPY_FACTS), len(_BRANCH_FACTS), len(_LESSON_FACTS)) == (17, 3, 4)
    assert len(_SECTION_FACTS) == 24, "a phrase is in two groups"
    assert len(_CRITERIA_FACTS) == 4
    cells = (len(_OPERATOR_FACTS), len(_OPERATOR_CELL_FACTS), len(_SESSION_CELL_FACTS))
    assert cells == (2, 2, 1)
    assert len(_OLD_SHAPES) == 3
    copies, operator = _copies_section(reference), _operator_section(reference)
    assert len(_printed_commands(copies)) == 3
    # The two sections the checks read share no line, so no line is judged by two rules.
    shared = {line for line in copies.split("\n") if line.strip()} & set(
        operator.split("\n")
    )
    assert not shared, f"the copies section and Operator Steps share lines: {shared}"


def test_phase_1_step_1_lists_the_copies_before_it_reads_the_buffer() -> None:
    skill = _text(_SKILL)
    assert _old_step_problems(skill) == [], "step 1 is still the old one-line step"
    gaps = _pointer_gaps(skill)
    assert not gaps, f"{_SKILL_NAME}, Phase 1 step 1, does not say: {gaps}"


def test_the_pointer_resolves_to_the_heading_of_the_new_section() -> None:
    step = _view(_phase_1_step_1(_text(_SKILL)))
    links = re.findall(r"\]\((references/consolidation-actions\.md)#([^)\s]+)\)", step)
    assert len(links) == 1, f"step 1 holds {len(links)} links to the reference, not 1"
    relative, anchor = links[0]
    assert (_SKILL_DIR / relative).is_file(), (
        f"{relative} does not resolve from the skill"
    )
    slugs = [_slug(heading) for heading in _headings(_text(_REFERENCE))]
    assert slugs.count(anchor) == 1, (
        f"the anchor #{anchor} names {slugs.count(anchor)} headings"
    )
    assert anchor == _slug(_COPIES_HEADING)


def test_every_in_page_link_of_the_section_resolves() -> None:
    reference = _text(_REFERENCE)
    section = _copies_section(reference)
    assert len(re.findall(r"\]\(#[^)\s]+\)", section)) == 2, (
        "the section links two sections"
    )
    assert _dead_anchors(section, reference) == []


def test_the_section_is_filed_between_the_two_headings_the_row_names() -> None:
    headings = [h for h in _headings(_text(_REFERENCE)) if h.startswith("## ")]
    assert headings.count(_COPIES_HEADING) == 1
    position = headings.index(_COPIES_HEADING)
    assert headings[position - 1] == _BEFORE_HEADING
    assert headings[position + 1] == _AFTER_HEADING


def test_the_section_lists_the_three_kinds_of_copy_and_how_to_fold_them() -> None:
    view = _view(_copies_section(_text(_REFERENCE)))
    gaps = _missing(view, _COPY_FACTS)
    assert not gaps, f"{_REFERENCE_NAME}, {_COPIES_HEADING}, does not say: {gaps}"


def test_the_section_puts_the_drain_entry_on_the_branch_that_merges() -> None:
    view = _view(_copies_section(_text(_REFERENCE)))
    gaps = _missing(view, _BRANCH_FACTS)
    assert not gaps, f"{_REFERENCE_NAME}, {_COPIES_HEADING}, does not say: {gaps}"


def test_the_section_reads_parked_lessons_only_where_the_project_has_them() -> None:
    section = _copies_section(_text(_REFERENCE))
    gaps = _missing(_view(section), _LESSON_FACTS)
    assert not gaps, f"{_REFERENCE_NAME}, {_COPIES_HEADING}, does not say: {gaps}"
    # The wording names no section of a hand-off note: no inline code span in that paragraph
    # is a heading, because the kit's contract has no such section to name.
    paragraph = _paragraph_starting(section, "**Parked lessons.**")
    named = [s for s in re.findall(r"`([^`]+)`", paragraph) if _HEADING.match(s)]
    assert named == [], f"the lessons rule names a section: {named}"


def test_the_promote_to_rule_criteria_check_the_standing_policies() -> None:
    gaps = _criteria_gaps(_text(_REFERENCE))
    assert not gaps, f"{_REFERENCE_NAME}, PROMOTE_TO_RULE criteria, do not say: {gaps}"


@pytest.mark.parametrize("slug", list(_OLD_SHAPES))
def test_the_old_folding_phrases_are_gone(slug: str) -> None:
    pattern, why = _OLD_SHAPES[slug]
    view = _view(_copies_section(_text(_REFERENCE)))
    assert not re.search(pattern, view, re.IGNORECASE), f"{_COPIES_HEADING} still {why}"


def test_operator_steps_count_the_copy_read_as_a_step_with_a_row() -> None:
    gaps = _operator_gaps(_text(_REFERENCE))
    assert not gaps, f"{_REFERENCE_NAME}, Operator Steps, does not say: {gaps}"


def test_the_one_in_page_link_of_operator_steps_resolves() -> None:
    reference = _text(_REFERENCE)
    section = _operator_section(reference)
    assert len(re.findall(r"\]\(#[^)\s]+\)", section)) == 1, (
        "Operator Steps links one section"
    )
    assert _dead_anchors(section, reference) == []


def test_skill_md_stays_within_the_line_cap() -> None:
    lines = _text(_SKILL).count("\n")
    assert lines <= _LINE_CAP, (
        f"SKILL.md has {lines} lines; the audit cap leaves {_LINE_CAP}"
    )


def test_the_printed_commands_never_name_the_buffer() -> None:
    section = _copies_section(_text(_REFERENCE))
    commands = _printed_commands(section)
    assert commands, "the section prints no command"
    for command in commands:
        assert "learnings.md" not in command, (
            f"a printed line names the buffer: {command}"
        )
    assert ":.ai/learnings.md" not in section
    assert "cp .ai/learnings.md" not in section
    assert [c for c in commands if re.match(r"[A-Za-z_]\w*=", c)] == []
    # The placeholders are the whole vocabulary: a stray one is a command nobody can run.
    used = {p for command in commands for p in re.findall(r"<[^>]+>", command)}
    assert used <= set(_PLACEHOLDERS), (
        f"unknown placeholders: {used - set(_PLACEHOLDERS)}"
    )


@cache
def _guard() -> ModuleType:
    """The guard, loaded once from its file (the hook is a script, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "gate_learnings_drain_for_intake", _GUARD
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shape(command: str, tool: str) -> str | None:
    judge = cast(Callable[[str, str], str | None], _guard()._shell_shape)  # pyright: ignore[reportPrivateUsage]
    return judge(command, tool)


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_the_guard_lets_every_printed_read_form_through(tool: str) -> None:
    commands = [
        _substituted(command, _VALUES)
        for command in _printed_commands(_copies_section(_text(_REFERENCE)))
    ]
    # The judge is shown to see: it flags a removal, a redirect into the buffer and an
    # in-place edit, so a None for the read forms below means it looked and found no rewrite.
    for positive in (
        "rm .ai/learnings.md",
        "git show 'stash@{0}:.ai/learnings.md' > .ai/learnings.md",
        "sed -i '/^### /d' .ai/learnings.md",
    ):
        assert _shape(positive, tool) is not None, f"the judge missed {positive!r}"
    assert any(".ai/learnings.md" in command for command in commands), (
        "no printed form names the buffer once filled in, so the judge has nothing to judge"
    )
    for command in commands:
        assert _shape(command, tool) is None, f"the guard would block {command!r}"


# --- the positive control: a repository with one stash and one branch ahead -----------------

_TIMEOUT_SECONDS = 60


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert done.returncode == 0, f"git {' '.join(args)} failed: {done.stderr}"
    return done.stdout


def _entry(day: str, title: str) -> str:
    return f"### [{day}] {title}\n- **Finding:** a finding\n- **Impact:** an impact\n\n"


def _entry_headings(buffer: str) -> list[str]:
    return [line for line in buffer.split("\n") if line.startswith("### ")]


def _only_in_copy(buffer: str, copy: str) -> list[str]:
    """The entry headings a copy holds and the checked-out buffer does not."""
    have = set(_entry_headings(buffer))
    return [heading for heading in _entry_headings(copy) if heading not in have]


def _make_repo(parent: Path) -> tuple[Path, str]:
    """A trunk with a two-entry buffer, a branch ahead of it with a third entry, and a stash on
    the trunk that holds a different third entry. Returns the repository and the trunk's buffer."""
    root = parent / "project"
    (root / ".ai").mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "core.autocrlf", "false")
    buffer = root / ".ai" / "learnings.md"
    trunk = _entry("2026-01-01", "Entry A") + _entry("2026-01-02", "Entry B")
    buffer.write_text(trunk, encoding="utf-8", newline="\n")
    _git(root, "add", "--", ".ai")
    _git(root, "commit", "-q", "-m", "a buffer of two entries")
    _git(root, "checkout", "-q", "-b", "side")
    buffer.write_text(
        trunk + _entry("2026-01-03", "Entry C"), encoding="utf-8", newline="\n"
    )
    _git(root, "commit", "-q", "-am", "a third entry on a branch")
    _git(root, "checkout", "-q", "main")
    buffer.write_text(
        trunk + _entry("2026-01-04", "Entry D"), encoding="utf-8", newline="\n"
    )
    _git(root, "stash", "push", "-q")
    assert buffer.read_text(encoding="utf-8") == trunk
    return root, trunk


def _run_printed(command: str, root: Path, values: dict[str, str]) -> str:
    """Run one printed line as written, a `>` redirect included, without a shell."""
    tokens = shlex.split(_substituted(command, values), comments=True)
    target = None
    if ">" in tokens:
        target = tokens[tokens.index(">") + 1]
        tokens = tokens[: tokens.index(">")]
    done = subprocess.run(
        tokens,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert done.returncode == 0, f"{command!r} failed: {done.stderr}"
    if target is not None:
        (root / target).write_text(done.stdout, encoding="utf-8", newline="\n")
    return done.stdout


def test_the_printed_commands_find_the_stash_and_the_branch_and_count_their_entries(
    tmp_path: Path,
) -> None:
    root, trunk = _make_repo(tmp_path)
    commands = _printed_commands(_copies_section(_text(_REFERENCE)))
    assert len(commands) == 3
    stash_list, branches, read_copy = commands

    listed = _run_printed(stash_list, root, _VALUES)
    assert len(listed.strip().split("\n")) == 1 and listed.startswith("stash@{0}:"), (
        listed
    )
    assert _run_printed(branches, root, _VALUES).strip() == "side"

    _run_printed(read_copy, root, _VALUES)
    from_stash = (root / "scratch-copy.txt").read_text(encoding="utf-8")
    assert len(_entry_headings(from_stash)) == 3
    assert _only_in_copy(trunk, from_stash) == ["### [2026-01-04] Entry D"]

    _run_printed(read_copy, root, {**_VALUES, "<ref>": "side"})
    from_branch = (root / "scratch-copy.txt").read_text(encoding="utf-8")
    assert len(_entry_headings(from_branch)) == 3
    assert _only_in_copy(trunk, from_branch) == ["### [2026-01-03] Entry C"]
    # Neither copy is the checked-out buffer, which the commands never touched.
    assert (root / ".ai" / "learnings.md").read_text(encoding="utf-8") == trunk


# --- the instruments -----------------------------------------------------------------------


def _mutated(text: str, old: str, new: str) -> str:
    """`text` with `old` replaced by `new`; an `old` that is not there fails loudly."""
    assert old and old in text, f"the mutation target is not in the text: {old!r}"
    return text.replace(old, new, 1)


def _criteria_item_lines(reference: str) -> str:
    """The raw lines of the criteria item that names the standing policy, with its newline."""
    lines = _section(reference, _RULE_HEADING, _REFERENCE_NAME).split("\n")
    start = next(i for i, line in enumerate(lines) if _POLICY_WORDS in line)
    while not lines[start].startswith("- "):
        start -= 1
    end = start + 1
    while lines[end].strip() and not lines[end].startswith("- "):
        end += 1
    return "\n".join(lines[start:end]) + "\n"


def _rewrap(text: str, width: int) -> str:
    """Every prose paragraph re-flowed to `width`; headings, list items, table rows, blockquotes
    and fenced blocks are kept as they are."""
    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lead = block.lstrip()
        if (
            lead.startswith(("#", "|", ">", "```"))
            or "```" in block
            or re.search(r"(?m)^\s*(?:\d+\.|[-*])\s", block)
        ):
            blocks.append(block)
            continue
        lines = textwrap.wrap(
            " ".join(block.split()),
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def test_every_check_sees_its_planted_positive() -> None:
    """A guard never shown to fail has not been shown to work."""
    skill, reference = _text(_SKILL), _text(_REFERENCE)

    # The old step 1 is the one-line step and every pointer phrase is reported; a Phase 1 with
    # no step 1, and a text with no Phase 1, fail loudly.
    old_skill = _mutated(skill, _phase_1_step_1(skill), _OLD_STEP_1)
    assert _old_step_problems(old_skill) == [_OLD_STEP_PROBLEM]
    assert _pointer_gaps(old_skill) == list(_POINTER_FACTS)
    assert any(
        "Phase 1" in p for p in _reported("x", _pointer_gaps, _PHASE_1_HEADING + "\n")
    )
    assert any("no heading" in p for p in _reported("x", _pointer_gaps, "text\n"))

    # The reference before the edit: the section is gone, and the criteria list holds four items
    # with no policy among them.
    section = _copies_section(reference)
    assert any(
        "no heading" in p
        for p in _reported("x", _section_gaps, reference.replace(section, ""))
    )
    four = _mutated(reference, _criteria_item_lines(reference), "")
    assert _criteria_gaps(four) == [
        *_CRITERIA_FACTS,
        "0 criteria items name a standing policy, not 1",
        "the list holds 4 items, not 5 or more",
    ]

    # A half-edit: the branch rule is cut out of the section, and exactly its phrases are reported.
    half = _mutated(reference, _paragraph_starting(section, "**Record the drain"), "")
    assert _section_gaps(half) == list(_BRANCH_FACTS)

    # The words in the wrong section do not count: the whole section filed under another heading.
    renamed = _mutated(reference, _COPIES_HEADING, "## Elsewhere")
    assert any("no heading" in p for p in _reported("x", _section_gaps, renamed))

    # A dead in-page anchor is reported, and a live one is not.
    dead_section = _mutated(section, "(#operator-steps)", "(#operator-step)")
    assert _dead_anchors(dead_section, reference) == ["operator-step"]
    assert _dead_anchors(section, reference) == []

    # The anchor a heading gets, for the three shapes the file's headings use.
    assert _slug(_COPIES_HEADING) == "buffer-copies-and-parked-lessons"
    assert _slug(_RULE_HEADING) == "promote_to_rule"
    assert _slug("## Pre-Drain Snapshot (Phase 5)") == "pre-drain-snapshot-phase-5"

    # The commands: a line that names the buffer, and one with an unknown placeholder, are the
    # shapes the printed-command test exists to catch.
    named = "```\ngit show 'main:.ai/learnings.md'\n```\n"
    assert any("learnings.md" in c for c in _printed_commands(named))
    stray = "```\ngit show '<commit>:<path>'\n```\n"
    assert {
        p for c in _printed_commands(stray) for p in re.findall(r"<[^>]+>", c)
    } - set(_PLACEHOLDERS) == {"<commit>"}

    # The old folding sentences hold the old shapes, each shape is found, and the words that name
    # the rule in the new text are near-misses, not old shapes.
    assert _old_shapes(_OLD_FOLDING + _OLD_FOLDING_ALIAS) == list(_OLD_SHAPES)
    for near in (
        "appends each entry with Edit under its own `## ` category section, never at the file end;",
        "Phase 2's Steps 1 and 2 archive them again (stale or superseded in Step 1).",
        "Edit appending after the entry's own category header.",
    ):
        assert _old_shapes(near) == [], f"flagged a near-miss: {near!r}"

    # The old-shape scan reads the copies section and no other: the old words under another
    # heading are not found, and the same words inside the section are.
    elsewhere = (
        reference
        + "\n## Elsewhere\n\nEdit appending after the last entry to add one.\n"
    )
    assert _old_shape_problems(elsewhere) == []
    inside = _mutated(reference, section, section + "\n" + _OLD_FOLDING)
    assert _old_shape_problems(inside) == [
        "still says: append-after-the-last-entry",
        "still says: the-coverage-check-alone-archives-them",
    ]

    # Operator Steps: a count that was not updated, a row that was not added, and no table at all.
    stale = _mutated(reference, "Four steps need bytes", "Three steps need bytes")
    assert "the intro says three steps and the table holds 4 rows" in _operator_gaps(
        stale
    )
    assert "the intro counts four steps" in _operator_gaps(stale)
    operator = _operator_section(reference)
    row_line = next(r for r in operator.split("\n") if r.startswith(_COPIES_ROW_LEAD))
    unrowed = _operator_gaps(_mutated(reference, row_line + "\n", ""))
    assert "the intro says four steps and the table holds 3 rows" in unrowed
    assert any(f"0 table rows start {_COPIES_ROW_LEAD!r}" in gap for gap in unrowed)
    bare = _mutated(
        reference, operator, "## Operator Steps\n\nFour steps need bytes of it.\n\n"
    )
    assert any("no table" in p for p in _reported("x", _operator_gaps, bare))


def _deleted_in_turn(view: str, facts: dict[str, str]) -> None:
    """Delete every phrase of `facts` from `view` in turn; the reader must name that phrase."""
    assert _missing(view, facts) == [], (
        "the shipped text must pass before a deletion means anything"
    )
    for name, pattern in facts.items():
        match = re.search(pattern, view, re.IGNORECASE)
        assert match is not None, (
            f"{name}: the pattern does not match the text it guards"
        )
        mutated = view[: match.start()] + view[match.end() :]
        assert name in _missing(mutated, facts), name


def test_each_phrase_deleted_in_turn_is_reported() -> None:
    """One mutation round over the real text: each deleted phrase is the one reported."""
    skill, reference = _text(_SKILL), _text(_REFERENCE)
    _deleted_in_turn(_view(_phase_1_step_1(skill)), _POINTER_FACTS)
    _deleted_in_turn(_view(_copies_section(reference)), _SECTION_FACTS)
    _deleted_in_turn(_policy_item(_criteria(reference)), _CRITERIA_FACTS)
    operator = _operator_section(reference)
    _, operator_cell, session_cell = _copies_row_cells(operator)
    _deleted_in_turn(_view(operator), _OPERATOR_FACTS)
    _deleted_in_turn(_view(operator_cell), _OPERATOR_CELL_FACTS)
    _deleted_in_turn(_view(session_cell), _SESSION_CELL_FACTS)


def test_the_old_folding_sentences_put_back_are_caught() -> None:
    skill, reference = _text(_SKILL), _text(_REFERENCE)
    assert not _problems(skill, reference), (
        "the shipped text must pass before a put-back means anything"
    )
    section = _copies_section(reference)
    for old in (_OLD_FOLDING, _OLD_FOLDING_ALIAS):
        problems = _problems(skill, _mutated(reference, section, section + "\n" + old))
        assert any(p.startswith("copies section: still says: ") for p in problems), (
            problems
        )


def test_the_shipped_text_has_no_problem_in_any_check() -> None:
    problems = _problems(_text(_SKILL), _text(_REFERENCE))
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("width", [48, 72, 130])
def test_a_rewrap_of_the_shipped_text_passes_every_check(width: int) -> None:
    skill, reference = _text(_SKILL), _text(_REFERENCE)
    assert not _problems(skill, reference), (
        "the shipped text must pass before a re-wrap"
    )
    assert _rewrap(reference, width) != reference, (
        "the re-wrap changed nothing, so it proves nothing"
    )
    assert _problems(_rewrap(skill, width), _rewrap(reference, width)) == []
