"""The post-task review can run in a fresh context, and its close names a finished artifact.

A session at the end of a long task holds the least room, which is when the review runs. The skill
gains `references/fresh-context-review.md`: it changes who runs the review, never whether, and it
says when to use it, what the one inline brief carries (including one planted false claim and the
read-only terms), what stays with the session and how the return is read. Two lines of SKILL.md
point at it and at the checklist, and neither adds a line to a file that stands at the audit's cap:
the opening paragraph of the review pipeline gains one sentence on its last line, and the step
inventory merges its last two rows into one and uses the freed row for a finished artifact read end
to end (the checklist's Step 9 carries the same row).

The tests slice each place by its markers or headings (a missing one fails loudly), assert each rule
where it belongs, and fire every check at the text it replaced: the opening paragraph and the
inventory as they stood (`_OLD_*`, unedited excerpts) and the Step 9 list as it stood, and a
reference that has the headings and none of the rules (`_STUB_REFERENCE`). Each rule sentence is
also removed from the real text, one at a time, to show the check that holds it reports the gap.

THE SURFACE, in numbers the tests assert: 8 places in 3 files (the reference's introduction and its
four sections, the opening paragraph of SKILL.md, its step inventory, and Step 9 of the checklist)
and 22 checks. Besides the checks: SKILL.md at most 499 lines, one link to the reference, and the
inventory at 7 data rows.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
)
_SKILL_MD = _SKILL / "SKILL.md"
_REFERENCE = _SKILL / "references" / "fresh-context-review.md"
_CHECKLIST = _SKILL / "references" / "review-checklist.md"
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = "(references/fresh-context-review.md)"

_EN = chr(0x2013)
_EM = chr(0x2014)
_ELLIPSIS = chr(0x2026)

_PIPELINE_START = "Step 9 is the close self-challenge, and it runs last."
_PIPELINE_END = "### Step 0:"
_INVENTORY_START = "### 9. Step Inventory"
_INVENTORY_END = "### 10."


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same.
    A missing file is its own loud failure, never an empty match."""
    if not path.is_file():
        raise AssertionError(f"{path.name} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _marker_at(text: str, marker: str, after: int = 0) -> int:
    """The offset of `marker` at or after `after`, or -1. A line break may stand for any run of
    whitespace inside the marker, so a paragraph that is re-wrapped is still found."""
    words = [re.escape(word) for word in marker.split()]
    found = re.compile(r"\s+".join(words)).search(text, after)
    return -1 if found is None else found.start()


def _between(text: str, start: str, end: str, where: str) -> str:
    begin = _marker_at(text, start)
    if begin < 0:
        raise AssertionError(f"{where}: no marker {start!r}")
    stop = _marker_at(text, end, begin)
    if stop < 0:
        raise AssertionError(f"{where}: no marker {end!r} after {start!r}")
    return text[begin:stop]


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or a
    higher level. A missing heading fails loudly, with the heading named."""
    body: list[str] = []
    level = 0
    for line in text.split("\n"):
        found = _HEADING.match(line)
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


def _introduction(text: str, where: str) -> str:
    """The text between the title and the first numbered heading."""
    start = text.find("\n\n")
    stop = text.find("\n## 1.")
    if start < 0 or stop < 0 or stop < start:
        raise AssertionError(
            f"{where}: no introduction before the first numbered heading"
        )
    return text[start:stop]


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


class _Place(NamedTuple):
    name: str
    path: Path
    checks: tuple[_Check, ...]
    locate: Callable[[str, str], str]
    old: str


def _says(*needles: str) -> Callable[[str], bool]:
    return lambda region: all(n in _plain(region) for n in needles)


# ---------------------------------------------------------------------------------------------
# The rules of the reference, by the words that carry them.
# ---------------------------------------------------------------------------------------------
_WHO_NOT_WHETHER = "changes who runs the review, never whether"
_EVERY_STEP = "every step still runs, Step 0 to Step 9"
_NOT_MEASURED = "reasoned, not measured"
_NO_ROOM = "cannot hold the skill, the script's output and the files under review"
_OTHER_REVIEWER = "or when a reviewer other than the author is wanted"
_NO_AGENT = (
    "no way to start an agent with its own context, run the review in the session "
    "and say so in the report"
)
_ONE_BRIEF = "Give the agent one inline brief"
_BASE_AND_PLAN = "the base ref, as a commit id, and the plan's list of files"
_SCRIPT_PATH = (
    "the script's real path, the path the session resolved, because the new agent "
    "does not know the skill's folder"
)
_SKILL_PATH = "the path of the skill's SKILL.md to read if it has no Skill tool"
_PLANTED = (
    "at most four claims, each with the command that re-derives it, "
    "plus one planted false claim"
)
_GATES = "the gates already run, with their exit codes, as claims to re-run and not as results"
_OUTPUT_FORMAT = "the skill's Output Format"
_READ_ONLY = "the reviewer reports and does not edit, stage or commit anything"
_NO_VERDICT = "Leave out the author's verdict on the work"
_STAYS = (
    "The fix pass and its re-review (Step 5), Step 8, and Step 9 over the whole close "
    "before the hand-off stay with the session"
)
_OWN_STEP_9 = "The reviewer closes its own review with its Step 9"
_TOP_LEVEL = "runs as a top-level run in its own context, not as a skill invoked from inside another"
_TRUST = "Trust a confirmation only if the planted claim was rejected"
_UNVERIFIED = "treat a return that says nothing about it as unverified"
_HAND_OFF = (
    "The hand-off names the file that holds the reviewer's return "
    "and the result for the planted claim"
)

_POINTER = (
    "A session short of context runs the review in a fresh context instead: "
    "[references/fresh-context-review.md](references/fresh-context-review.md)."
)
_CHECKLIST_ROW = (
    "- [ ] Finished artifact read end to end: the document, plan or report as it now stands, "
    "after the last edit (not its diff, not a checker's verdict); yes or no, with what was read"
)
_MERGED_ROW = (
    "| Backend restart (if backend touched), or any other gate this task triggered "
    "| yes/no/n-a | {command} |"
)
_ARTIFACT_ROW = (
    "| Finished artifact read end to end (as it now stands, after the last edit) "
    "| yes/no | {what was read, whole} |"
)

# The references as they stood: the headings and none of the rules.
_STUB_REFERENCE = """# Running the review in a fresh context

Run it somewhere else.

## 1. When

Sometimes.

## 2. The brief

Tell the agent.

## 3. What stays with the session

Some of it.

## 4. Reading the return

Read it.
"""

# The opening paragraph of the review pipeline, last lines as they stood.
_OLD_PIPELINE = (
    "Step 9 is the close self-challenge, and it runs last. Run "
    '`python -B "${CLAUDE_SKILL_DIR}/scripts/review_core.py" --base <ref> --plan <file-list>`\n'
    "first: it prints Step 0's lists, the diff stat, line endings, lint scope and Step 7b's matrix "
    "lookups, each ending with what it did not check\n"
    "(exit 2 means a check could not run, never a pass). It reads nothing for you: every UNKNOWN "
    "it prints is still yours to open.\n\n"
    "### Step 0: Dependency & Blast Radius (produces a LIST, not an opinion)\n"
)

# The step inventory as it stood: the last two rows were a backend restart and any other gate.
_OLD_INVENTORY = (
    f"### 9. Step Inventory (REQUIRED {_EM} the operator reads this first)\n"
    "| Mandated step | Ran? | Evidence / why not |\n"
    "|---|---|---|\n"
    "| Dependency & blast radius (step 0) | yes/no | {dependents found / checked / UNKNOWN} |\n"
    f"| Post-task review (steps 1{_EN}6) | yes/no | {{what was reviewed}} |\n"
    "| Documentation impact (step 7) | yes/no | {files checked} |\n"
    "| Learnings extraction (step 8) | yes/no | {entries appended} |\n"
    '| Close self-challenge (step 9) | yes/no | {findings, or the word "none"} |\n'
    "| Backend restart (if backend touched) | yes/no/n-a | {command} |\n"
    f"| {{any other gate this task triggered}} | yes/no | {{{_ELLIPSIS}}} |\n\n"
    "### 10. Close Self-Challenge Results\n"
)

# Step 9 of the checklist as it stood: two of its four rows.
_OLD_STEP_9 = (
    f"## Step 9: Close Self-Challenge (MANDATORY {_EM} runs LAST)\n\n"
    "- [ ] Asked: is it detailed enough? what was missed? what would a reviewer object to?\n"
    "- [ ] Ran BEFORE the handoff is written, never after\n\n"
    "## Common Mistakes Caught in Past Reviews\n"
)


def _introduction_of(text: str, where: str) -> str:
    return _introduction(text, where)


def _section_n(number: int) -> Callable[[str, str], str]:
    return lambda text, where: _section(text, f"## {number}.", where)


def _pipeline(text: str, where: str) -> str:
    return _between(text, _PIPELINE_START, _PIPELINE_END, where)


def _inventory(text: str, where: str) -> str:
    return _between(text, _INVENTORY_START, _INVENTORY_END, where)


def _step_9(text: str, where: str) -> str:
    return _section(text, "## Step 9", where)


_PLACES: tuple[_Place, ...] = (
    _Place(
        "reference-introduction",
        _REFERENCE,
        (
            _Check(
                "the introduction says it changes who runs the review, never whether",
                _says(_WHO_NOT_WHETHER),
            ),
            _Check("the introduction says every step still runs", _says(_EVERY_STEP)),
            _Check(
                "the introduction keeps the evidence level of the case for it",
                _says(_NOT_MEASURED),
            ),
        ),
        _introduction_of,
        _STUB_REFERENCE,
    ),
    _Place(
        "reference-section-1",
        _REFERENCE,
        (
            _Check("section 1 names a session short of room", _says(_NO_ROOM)),
            _Check(
                "section 1 names a reviewer other than the author",
                _says(_OTHER_REVIEWER),
            ),
            _Check(
                "section 1 says what to do with no agent of its own context",
                _says(_NO_AGENT),
            ),
        ),
        _section_n(1),
        _STUB_REFERENCE,
    ),
    _Place(
        "reference-section-2",
        _REFERENCE,
        (
            _Check(
                "section 2 gives one inline brief with the base and the plan",
                _says(_ONE_BRIEF, _BASE_AND_PLAN),
            ),
            _Check(
                "section 2 has the session resolve the script path",
                _says(_SCRIPT_PATH, _SKILL_PATH),
            ),
            _Check(
                "section 2 caps the claims at four and plants one false claim",
                _says(_PLANTED),
            ),
            _Check(
                "section 2 hands over the gates already run as claims to re-run",
                _says(_GATES),
            ),
            _Check(
                "section 2 carries the Output Format and the read-only terms",
                _says(_OUTPUT_FORMAT, _READ_ONLY),
            ),
            _Check("section 2 leaves out the author's verdict", _says(_NO_VERDICT)),
        ),
        _section_n(2),
        _STUB_REFERENCE,
    ),
    _Place(
        "reference-section-3",
        _REFERENCE,
        (
            _Check(
                "section 3 keeps the fix pass, Step 8 and the close Step 9 with the session",
                _says(_STAYS),
            ),
            _Check(
                "section 3 has the reviewer close its own review", _says(_OWN_STEP_9)
            ),
            _Check(
                "section 3 makes the reviewer a top-level run, not a nested skill",
                _says(_TOP_LEVEL),
            ),
        ),
        _section_n(3),
        _STUB_REFERENCE,
    ),
    _Place(
        "reference-section-4",
        _REFERENCE,
        (
            _Check(
                "section 4 trusts a confirmation only if the planted claim was rejected",
                _says(_TRUST),
            ),
            _Check(
                "section 4 treats a silent return as unverified", _says(_UNVERIFIED)
            ),
            _Check(
                "section 4 has the hand-off name the return and the planted claim's result",
                _says(_HAND_OFF),
            ),
        ),
        _section_n(4),
        _STUB_REFERENCE,
    ),
    _Place(
        "skill-pipeline-paragraph",
        _SKILL_MD,
        (
            _Check(
                "the opening paragraph points at the fresh-context reference",
                _says(_POINTER),
            ),
        ),
        _pipeline,
        _OLD_PIPELINE,
    ),
    _Place(
        "skill-step-inventory",
        _SKILL_MD,
        (
            _Check(
                "the inventory merges the backend restart and any other gate in one row",
                _says(_MERGED_ROW),
            ),
            _Check(
                "the inventory has a finished artifact read end to end row",
                _says(_ARTIFACT_ROW),
            ),
        ),
        _inventory,
        _OLD_INVENTORY,
    ),
    _Place(
        "checklist-step-9",
        _CHECKLIST,
        (_Check("Step 9 has the finished artifact row", _says(_CHECKLIST_ROW)),),
        _step_9,
        _OLD_STEP_9,
    ),
)


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text, place.path.name)
    return [c.label for c in place.checks if not c.holds(region)]


def test_the_surface_is_stated_in_numbers() -> None:
    """8 places in 3 files and 22 checks."""
    assert len(_PLACES) == 8, f"{len(_PLACES)} places, not the 8 stated"
    assert len({p.path for p in _PLACES}) == 3, "the places are not in 3 distinct files"
    checks = [c for p in _PLACES for c in p.checks]
    assert len(checks) == 22, f"{len(checks)} checks, not the 22 stated"
    assert len({c.label for c in checks}) == len(checks), "two checks share a label"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_carries_its_rule(place: _Place) -> None:
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path.name} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The old paragraph, inventory and Step 9 list lack the new sentence or row, and the stub
    reference has no rule, so every check of a place must say so."""
    reported = _gaps(place, place.old)
    assert len(reported) == len(place.checks), (
        f"{place.name}: {len(reported)} of {len(place.checks)} checks saw the old text; "
        f"blind: {[c.label for c in place.checks if c.label not in reported]}"
    )


def _needle_removal_cases() -> list[tuple[str, str, str]]:
    """One case per rule sentence: the place, the check label and the one needle to take out.
    Written as data so that a sentence moved between checks is still a case."""
    cases = [
        (
            "reference-introduction",
            "the introduction says it changes",
            _WHO_NOT_WHETHER,
        ),
        ("reference-introduction", "the introduction says every step", _EVERY_STEP),
        (
            "reference-introduction",
            "the introduction keeps the evidence",
            _NOT_MEASURED,
        ),
        ("reference-section-1", "section 1 names a session", _NO_ROOM),
        ("reference-section-1", "section 1 names a reviewer", _OTHER_REVIEWER),
        ("reference-section-1", "section 1 says what to do", _NO_AGENT),
        ("reference-section-2", "section 2 gives one inline brief", _ONE_BRIEF),
        ("reference-section-2", "section 2 gives one inline brief", _BASE_AND_PLAN),
        ("reference-section-2", "section 2 has the session resolve", _SCRIPT_PATH),
        ("reference-section-2", "section 2 has the session resolve", _SKILL_PATH),
        ("reference-section-2", "section 2 caps the claims", _PLANTED),
        ("reference-section-2", "section 2 hands over the gates", _GATES),
        ("reference-section-2", "section 2 carries the Output Format", _OUTPUT_FORMAT),
        ("reference-section-2", "section 2 carries the Output Format", _READ_ONLY),
        ("reference-section-2", "section 2 leaves out", _NO_VERDICT),
        ("reference-section-3", "section 3 keeps the fix pass", _STAYS),
        ("reference-section-3", "section 3 has the reviewer close", _OWN_STEP_9),
        ("reference-section-3", "section 3 makes the reviewer", _TOP_LEVEL),
        ("reference-section-4", "section 4 trusts a confirmation", _TRUST),
        ("reference-section-4", "section 4 treats a silent return", _UNVERIFIED),
        ("reference-section-4", "section 4 has the hand-off", _HAND_OFF),
    ]
    return cases


@pytest.mark.parametrize(
    ("place_name", "label_start", "needle"),
    _needle_removal_cases(),
    ids=[f"{c[0]}:{c[2][:32]}" for c in _needle_removal_cases()],
)
def test_removing_a_rule_sentence_is_reported_by_the_check_that_holds_it(
    place_name: str, label_start: str, needle: str
) -> None:
    place = next(p for p in _PLACES if p.name == place_name)
    check = next(c for c in place.checks if c.label.startswith(label_start))
    region = _plain(place.locate(_read(place.path), place.path.name))
    assert region.count(needle) == 1, f"{needle!r} is not in {place_name} exactly once"
    removed = region.replace(needle, "", 1)
    assert not check.holds(removed), f"removing {needle!r} went unreported"


def test_the_planted_claim_rule_and_the_read_only_rule_are_each_checked() -> None:
    """Named separately because the brief is the one place a fresh reader's rules can be dropped:
    a brief with no planted claim cannot tell a reviewer that confirms from one that read."""
    section = _plain(_section(_read(_REFERENCE), "## 2.", _REFERENCE.name))
    assert _PLANTED in section and _READ_ONLY in section
    planted = _says(_PLANTED)
    read_only = _says(_READ_ONLY)
    assert not planted(section.replace("plus one planted false claim", "plus nothing"))
    assert not read_only(
        section.replace("does not edit, stage or commit anything", "may fix")
    )
    section_4 = _plain(_section(_read(_REFERENCE), "## 4.", _REFERENCE.name))
    assert not _says(_TRUST)(
        section_4.replace("only if the planted claim was rejected", "always")
    )


def test_the_reference_has_four_numbered_sections_in_order() -> None:
    text = _read(_REFERENCE)
    numbered = re.findall(r"(?m)^## (\d+)\. ", text)
    assert numbered == ["1", "2", "3", "4"], numbered
    assert text.splitlines()[0].startswith("# "), "the reference has no title"


def test_the_link_is_on_the_opening_paragraph_once_and_the_target_exists() -> None:
    """The link has to be inside the paragraph that names the script, once in the file, and the
    file it names has to exist in the skill's own references."""
    text = _read(_SKILL_MD)
    paragraph = _pipeline(text, "SKILL.md")
    assert paragraph.count(_LINK) == 1
    assert text.count(_LINK) == 1, (
        "the link appears outside the opening paragraph as well"
    )
    assert (_SKILL / "references" / "fresh-context-review.md").is_file()
    assert "${CLAUDE_SKILL_DIR}/scripts/review_core.py" in paragraph, (
        "the pointer is not on the paragraph that names the script"
    )


def test_the_pointer_check_sees_a_target_that_is_wrong() -> None:
    """Fired at a planted paragraph whose link names a file that does not exist."""
    check = _says(_POINTER)
    good = "It is yours to open. " + _POINTER
    assert check(good)
    wrong = good.replace("fresh-context-review.md)", "fresh-context.md)")
    assert wrong != good and not check(wrong)
    bare = good.replace(
        "[references/fresh-context-review.md](references/fresh-context-review.md)", "it"
    )
    assert bare != good and not check(bare)


def test_the_two_regions_of_skill_md_are_disjoint() -> None:
    """The opening paragraph and the step inventory are two scan surfaces of one file. A line in
    both would be judged by a rule that does not apply to it, so their spans must not overlap."""
    text = _read(_SKILL_MD)
    first = _marker_at(text, _PIPELINE_START)
    first_end = _marker_at(text, _PIPELINE_END, first)
    second = _marker_at(text, _INVENTORY_START)
    second_end = _marker_at(text, _INVENTORY_END, second)
    assert 0 <= first < first_end and 0 <= second < second_end, "a region was not found"
    assert first_end <= second or second_end <= first, (
        "the two regions of SKILL.md overlap"
    )
    overlapping = text[: first_end + 1]
    assert _marker_at(overlapping, _INVENTORY_START) < 0, (
        "the inventory starts inside the paragraph"
    )


def test_a_re_wrapped_opening_paragraph_is_still_found_and_still_checked() -> None:
    """The planted positive for the markers: the paragraph re-wrapped at 40 columns splits its
    first sentence across lines, so a plain search for it fails (the control), and the places and
    the region slices still hold on the folded text."""
    text = _read(_SKILL_MD)
    region = _between(text, _PIPELINE_START, _PIPELINE_END, "SKILL.md")
    paragraph = textwrap.fill(
        " ".join(region.split()),
        width=40,
        break_long_words=False,
        break_on_hyphens=False,
    )
    wrapped = text.replace(region, paragraph + "\n\n")
    assert wrapped != text and wrapped.find(_PIPELINE_START) < 0, (
        "the planted wrap must split the marker, or this tests nothing"
    )
    place = next(p for p in _PLACES if p.name == "skill-pipeline-paragraph")
    assert _gaps(place, wrapped) == []
    assert _plain(_pipeline(wrapped, "SKILL.md")) == _plain(region)


def test_skill_md_stays_within_the_audits_cap() -> None:
    lines = _read(_SKILL_MD).splitlines()
    assert len(lines) <= 499, (
        f"SKILL.md has {len(lines)} lines; the audit counts one more"
    )


def test_the_inventory_keeps_its_seven_rows_and_its_five_step_rows() -> None:
    """The edit merges two rows into one and adds one: the data rows stay at 7, and the five rows
    for the steps themselves are as they were."""
    region = _inventory(_read(_SKILL_MD), "SKILL.md")
    rows = [line for line in region.split("\n") if line.startswith("|")]
    assert len(rows) == 9, f"{len(rows)} table lines, header and rule included, not 9"
    for lead in (
        "| Dependency & blast radius (step 0) |",
        f"| Post-task review (steps 1{_EN}6) |",
        "| Documentation impact (step 7) |",
        "| Learnings extraction (step 8) |",
        "| Close self-challenge (step 9) |",
    ):
        assert any(row.startswith(lead) for row in rows), lead
    assert _OLD_INVENTORY.count("\n| ") == 8, (
        "the old inventory excerpt is not the old table"
    )
    assert "{any other gate this task triggered} |" not in region, (
        "the old last row is still there"
    )


def test_the_reference_stays_inside_the_skill_and_names_no_machine_path() -> None:
    text = _read(_REFERENCE)
    assert "](" not in text, (
        "the reference links out; its neighbours name files in plain text"
    )
    # Built from fragments, because the hygiene tests refuse these strings in any tracked file.
    forbidden_strings = (
        "." + "claude/skills/",
        "/" + "Users" + "/",
        "/" + "home" + "/",
        ":" + "\\",
        "Windows" + " host",
    )
    for forbidden in forbidden_strings:
        assert forbidden not in text, forbidden
    assert re.search(r"\b[A-Za-z]:/", text) is None, "a drive-letter path"
    assert "${CLAUDE_SKILL_DIR}" not in text, (
        "the reference says 'the path the session resolved'; the variable means nothing to the new agent"
    )


def test_a_missing_marker_heading_or_file_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="no marker"):
        _between(
            "text without the paragraph", _PIPELINE_START, _PIPELINE_END, "planted"
        )
    with pytest.raises(AssertionError, match="no heading"):
        _section("## 1. Only one\ntext\n", "## 2.", "planted")
    with pytest.raises(AssertionError, match="no introduction"):
        _introduction("# Title only", "planted")
    planted = "## 1. A\nOrder text\n### 1.1 sub\nmore\n## 2. B\nOther\n"
    assert "more" in _section(planted, "## 1.", "planted")
    assert "Other" not in _section(planted, "## 1.", "planted")
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-reference.md"))


def test_the_needle_helper_needs_every_needle_it_is_given() -> None:
    """`_says` holds only when every needle is there: fired at a region that holds one of two."""
    region = "alpha and beta, not gamma"
    assert _says("alpha", "beta")(region)
    assert not _says("alpha", "delta")(region)
