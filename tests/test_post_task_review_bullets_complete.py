"""The AGENTS.md review bullets cover the whole review, and the README row names its events.

`post-task-review` is Step 0 (dependency and blast radius) through Step 9 (the close
self-challenge), and runs at every completion event. The "Post-task review" section that
`kit-setup` seeds, and the kit's own, listed Steps 1 to 8 only, so a reader of AGENTS.md alone never
met the step that asks what a change breaks or the step that is run last and cannot be folded into
the review; the README row for the review still said "A completed implementation".

What the text says now: the section carries a Step 0 bullet before the code-review bullet and a
Step 9 bullet after Step 8, in the same words in both files, and the README row opens with the
completion events the skill names. The documentation item of the task completion checklist points
at the project's own code-to-docs matrix first and at the skill's sample only when there is none,
since the reference it used to name outright is now a labelled sample of one backend's layout. Only
projects seeded after this change get the bullets and the item; a project that already ran the kit
setup keeps its old section until a refresh.

THE SURFACE, in numbers the tests assert: 2 AGENTS.md files with 6 bullets each in the section, the
2 new bullets read whole, the 1 documentation item read whole in each, and 1 README row among the 1
that links the skill.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_KIT = "AGENTS.md"
_TEMPLATE = "plugins/core/src/lemmi_ai_kit/assets/templates/AGENTS.md"
_FILES = (_KIT, _TEMPLATE)
_README = "README.md"
_SECTION = "### Post-task review"
_CHECKLIST = "### Task completion checklist"
_DOCS_LEAD = "3. **Documentation updates**"
_HEADING = re.compile(r"^(#{1,6})\s")
_LIST_ITEM = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")

# The text carries these characters; they are built from their code points so that a retyped
# hyphen or dot in an old excerpt cannot make a check that sees nothing look as if it works.
_EN = chr(0x2013)
_EM = chr(0x2014)
_DOT = chr(0xB7)

_EVENTS = (
    "a finished task of any size",
    "a precondition stop",
    "a gate report",
    "a hand-off",
)
_TRIGGER = f"every completion event: {', '.join(_EVENTS)}"

_STEP_0 = (
    f"- Step 0: dependency and blast radius {_EM} list the dependents of every changed symbol "
    "and mark each checked or unknown, before the code review "
    "(see the `post-task-review` skill)."
)
_STEP_9 = (
    f"- Step 9: close self-challenge {_EM} run last, before any hand-off or report; ask what the "
    "work did not look at and state the findings, or none (see the `post-task-review` skill)."
)
# The leads of the bullets, in the order the section reads.
_LEADS = (
    "- Run the full post-task review at every completion event",
    "- Step 0:",
    f"- Steps 1{_EN}6:",
    "- Step 7:",
    "- Step 8:",
    "- Step 9:",
)

_OLD_SECTION = f"""### Post-task review
Uses: post-task-review (workflow), task-learnings (task), commit-message (task)
- Run the full post-task review at {_TRIGGER}. A close with no changed files still runs every step, reading the report's claims where there is no diff, and always Step 9. Inside a workflow skill, run it as its own top-level step after that workflow ends (a workflow skill is never invoked from inside another).
- Steps 1{_EN}6: code review and convention compliance (see the `post-task-review` skill).
- Step 7: documentation impact analysis {_EM} check and update affected docs.
- Step 8: learnings extraction {_EM} capture and record project knowledge.
"""

_DOCS_ITEM = (
    f"3. **Documentation updates** {_EM} If any modified files affect docs (per the project's own "
    "code-to-docs matrix, else the sample in `references/doc-impact-matrix.md` in the "
    "`post-task-review` skill), update the affected documentation."
)
# What the item said while the reference it names was one backend's matrix and nothing else.
_OLD_DOCS_ITEM = "(per references/doc-impact-matrix.md in the post-task-review skill)"
_OLD_CHECKLIST = f"""### Task completion checklist (mandatory)
When a task is complete, ALWAYS perform these steps before considering it done:
2. **Learnings extraction** (all tasks) {_EM} Extract project-level findings and append to `.ai/learnings.md`.
3. **Documentation updates** {_EM} If any modified files affect docs (per `references/doc-impact-matrix.md` in the `post-task-review` skill), update the affected documentation.
4. **Rebuild/restart** {_EM} not needed.
"""

_OLD_README_ROW = (
    f"| A completed implementation | Core {_DOT} "
    "[post-task-review](plugins/core/skills/post-task-review/SKILL.md) | Code and "
    "convention review, documentation impact and captured learnings |"
)


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space, so a re-wrapped
    bullet is the same bullet."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _section(text: str, heading: str) -> str:
    """From the first line that starts with `heading` to the next heading of the same or a higher
    level. A missing heading fails loudly, with the heading named."""
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
        raise AssertionError(f"no heading starting {heading!r}")
    return "\n".join(body)


def _list_items(section: str) -> list[str]:
    """Each list item of the section, bulleted or numbered, read whole and folded: the lines after
    it, indented or in column 0, belong to it until the next list item, a heading or a blank line.
    A line end put anywhere in an item, inside its lead included, does not change what it says."""
    items: list[list[str]] = []
    open_item = False
    for line in section.split("\n"):
        if _LIST_ITEM.match(line):
            items.append([line])
            open_item = True
        elif not line.strip() or _HEADING.match(line):
            open_item = False
        elif open_item:
            items[-1].append(line)
    return [_plain(" ".join(parts)) for parts in items]


def _numbered_item(section: str, lead: str) -> str:
    """The one list item that starts with `lead`, read whole and folded. None or several fail
    loudly, with the count named."""
    wanted = _plain(lead)
    found = [item for item in _list_items(section) if item.startswith(wanted)]
    if len(found) != 1:
        raise AssertionError(
            f"expected one checklist item starting {lead!r}, found {len(found)}"
        )
    return found[0]


def _docs_item_gaps(agents_text: str) -> list[str]:
    """What the documentation item lacks or still says, in `agents_text`; empty is a pass."""
    item = _numbered_item(_section(agents_text, _CHECKLIST), _DOCS_LEAD)
    gaps: list[str] = []
    if _plain(_DOCS_ITEM) not in item:
        gaps.append(
            "the item does not point at the project's own matrix, else the sample"
        )
    if _plain(_OLD_DOCS_ITEM) in item:
        gaps.append("the item still names the sample as the matrix")
    return gaps


def _bullets(section: str) -> list[str]:
    """Each `- ` bullet of the section, read whole: a continuation line belongs to the bullet
    above it until the next bullet or a blank line, and every bullet is returned folded."""
    bullets: list[list[str]] = []
    open_bullet = False
    for line in section.split("\n")[1:]:
        if line.startswith("- "):
            bullets.append([line])
            open_bullet = True
        elif not line.strip():
            open_bullet = False
        elif open_bullet:
            bullets[-1].append(line)
    return [_plain(" ".join(parts)) for parts in bullets]


def _gaps(agents_text: str) -> list[str]:
    """What the section lacks, in `agents_text`; an empty list is a pass."""
    bullets = _bullets(_section(agents_text, _SECTION))
    gaps: list[str] = []
    for want in (_STEP_0, _STEP_9):
        if _plain(want) not in bullets:
            gaps.append(f"missing bullet: {want[:40]}")
    leads = [
        next((b for b in bullets if b.startswith(_plain(lead))), None)
        for lead in _LEADS
    ]
    absent = [lead for lead, found in zip(_LEADS, leads, strict=True) if found is None]
    gaps += [f"no bullet starts: {lead}" for lead in absent]
    if not absent:
        positions = [bullets.index(found) for found in leads if found is not None]
        if positions != sorted(positions):
            gaps.append(f"the bullets are out of order: {positions}")
    return gaps


def _readme_row(text: str) -> str:
    """The one table row that links the skill. None or several fail loudly, with the count."""
    rows = [
        line
        for line in text.split("\n")
        if line.startswith("|")
        and "plugins/core/skills/post-task-review/SKILL.md" in line
    ]
    if len(rows) != 1:
        raise AssertionError(
            f"expected one README row linking the skill, found {len(rows)}"
        )
    return rows[0]


def _first_cell(row: str) -> str:
    return _plain(row.strip().strip("|").split("|")[0])


def _row_gaps(row: str) -> list[str]:
    cell = _first_cell(row)
    gaps = [
        f"the first cell does not name: {event}"
        for event in _EVENTS
        if event not in cell
    ]
    if "completion event" not in cell:
        gaps.append("the first cell does not say completion event")
    if "A completed implementation" in cell:
        gaps.append("the first cell is still 'A completed implementation'")
    return gaps


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_FILES) == 2 and len(set(_FILES)) == 2
    for path in _FILES:
        bullets = _bullets(_section(_read(path), _SECTION))
        assert len(bullets) == 6, f"{path}: {len(bullets)} bullets, not the 6 stated"
    assert len(_LEADS) == 6
    assert _readme_row(_read(_README)).startswith("|")


@pytest.mark.parametrize("path", _FILES)
def test_the_review_section_has_a_step_0_and_a_step_9_bullet(path: str) -> None:
    gaps = _gaps(_read(path))
    assert not gaps, f"{path}: {gaps}"


def test_the_two_files_carry_the_same_bullets() -> None:
    kit = _bullets(_section(_read(_KIT), _SECTION))
    template = _bullets(_section(_read(_TEMPLATE), _SECTION))
    assert kit == template, f"the files disagree: {kit} versus {template}"


@pytest.mark.parametrize("path", _FILES)
def test_the_documentation_item_points_at_the_projects_own_matrix_first(
    path: str,
) -> None:
    gaps = _docs_item_gaps(_read(path))
    assert not gaps, f"{path}: {gaps}"


def test_the_documentation_item_reads_the_same_in_both_files() -> None:
    kit = _numbered_item(_section(_read(_KIT), _CHECKLIST), _DOCS_LEAD)
    template = _numbered_item(_section(_read(_TEMPLATE), _CHECKLIST), _DOCS_LEAD)
    assert kit == template, f"the files disagree: {kit} versus {template}"


def test_the_readme_row_names_the_completion_events() -> None:
    gaps = _row_gaps(_readme_row(_read(_README)))
    assert not gaps, gaps


def test_the_documentation_checks_report_the_text_they_replaced() -> None:
    """Fired at the old checklist item, both checks report it; fired at the new item re-wrapped at
    every space, neither does. A missing item or heading fails loudly instead of passing."""
    assert _docs_item_gaps(_OLD_CHECKLIST) == [
        "the item does not point at the project's own matrix, else the sample",
        "the item still names the sample as the matrix",
    ]
    new = f"{_CHECKLIST} (mandatory)\n1. x\n{_DOCS_ITEM}\n4. y\n"
    assert _docs_item_gaps(new) == []
    words = _DOCS_ITEM.split(" ")
    for at in range(2, len(words)):
        wrapped = " ".join(words[:at]) + "\n  " + " ".join(words[at:])
        assert _docs_item_gaps(new.replace(_DOCS_ITEM, wrapped)) == [], wrapped
    with pytest.raises(AssertionError, match="found 0"):
        _docs_item_gaps(f"{_CHECKLIST}\n1. x\n")
    with pytest.raises(AssertionError, match="found 2"):
        _docs_item_gaps(f"{_CHECKLIST}\n{_DOCS_ITEM}\n{_DOCS_ITEM}\n")
    with pytest.raises(AssertionError, match="no heading"):
        _docs_item_gaps("### Other\n3. **Documentation updates** x\n")
    taken = _numbered_item(
        "### H\n3. **Documentation updates** a\n   b\n4. c\n", _DOCS_LEAD
    )
    assert taken == "3. Documentation updates a b"


def test_the_checks_report_the_text_they_replaced() -> None:
    """A guard never shown to fail has not been shown to work: fired at the old section, both new
    bullets and the order are reported, and the old README row fails on its first cell."""
    old_gaps = _gaps(_OLD_SECTION)
    assert len([g for g in old_gaps if g.startswith("missing bullet")]) == 2, old_gaps
    assert len([g for g in old_gaps if g.startswith("no bullet starts")]) == 2, old_gaps
    old_row = _row_gaps(_OLD_README_ROW)
    assert len(old_row) == len(_EVENTS) + 2, old_row
    assert _first_cell(_OLD_README_ROW) == "A completed implementation"


def _planted(*bullets: str) -> str:
    return "\n".join((_SECTION, "Uses: x", *bullets))


def test_the_checks_see_planted_sections_and_rows() -> None:
    opening = f"- Run the full post-task review at {_TRIGGER}. More words."
    review = f"- Steps 1{_EN}6: review."
    full = _planted(
        opening, _STEP_0, review, "- Step 7: docs.", "- Step 8: learnings.", _STEP_9
    )
    assert _gaps(full) == []
    swapped = _planted(
        opening, _STEP_0, review, "- Step 7: docs.", _STEP_9, "- Step 8: learnings."
    )
    assert any("out of order" in gap for gap in _gaps(swapped)), _gaps(swapped)
    wrapped = full.replace(_STEP_9, _STEP_9.replace("; ask", ";\n  ask"))
    assert _gaps(wrapped) == [], "a re-wrapped bullet must read the same"
    shortened = full.replace(" (see the `post-task-review` skill).", ".")
    assert any(gap.startswith("missing bullet") for gap in _gaps(shortened))
    good_row = (
        f"| Work at {_TRIGGER} | Core {_DOT} [post-task-review]"
        "(plugins/core/skills/post-task-review/SKILL.md) | x |"
    )
    assert _row_gaps(good_row) == []
    partial = good_row.replace(", a hand-off", "")
    assert _row_gaps(partial) == [f"the first cell does not name: {_EVENTS[3]}"]


def test_the_readers_fail_loudly_on_a_missing_heading_or_row() -> None:
    with pytest.raises(AssertionError, match="no heading"):
        _section("### Other\n- a\n", _SECTION)
    with pytest.raises(AssertionError, match="found 0"):
        _readme_row("| a | b |\n")
    twice = "| a | plugins/core/skills/post-task-review/SKILL.md |\n" * 2
    with pytest.raises(AssertionError, match="found 2"):
        _readme_row(twice)
    section = _section("### A\n- x\n### B\n- y\n", "### A")
    assert "- x" in section and "- y" not in section
