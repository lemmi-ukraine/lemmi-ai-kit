"""A drafted changelog line marks which of the files it names are tracked.

The review checklist's Step 8 rows say to append a changelog entry. An entry drafted while its files
were still untracked or ignored names paths that no commit holds, so a tracked ledger points at
nothing for anyone who clones. Two git commands settle each file at drafting time:
`git ls-files --error-unmatch` exits 0 only for a tracked file, and `git check-ignore -q` exits 0 for
an ignored one (both were run in a scratch repository before the row was written). The row sits right
after the "Changelog entry written" row and asks for the mark and the tracked part of each count. It
does not ask the author to add the files: whether a file is committed is not the entry's call.

Only the checklist changes; no SKILL.md line is spent on it.

THE SURFACE, in numbers the tests assert: 1 place (Step 8 of the checklist), which holds 10 rows or
more, and 5 checks on the one new row (4 for what it says, 1 for what it must not say). The lookup
is fired at the Step 8 section as it stood (`_OLD_STEP_8`, an unedited excerpt, 9 rows) and reports
the row missing, each of the 5 checks is fired at a planted row, and the anchor lookup is fired at
planted rows that sit before the anchor, behind another row, or one row away from it.
"""

import re
from pathlib import Path

import pytest

_CHECKLIST = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
    / "references"
    / "review-checklist.md"
)
_HEADING = re.compile(r"^(#{1,6})\s")
_ANCHOR_ROW = "- [ ] Changelog entry written:"

_OLD_STEP_8 = r"""## Step 8: Learnings Extraction

- [ ] Task reviewed for discoveries and surprises
- [ ] Review findings (steps 1–7) also considered as learnings
- [ ] Findings classified (project-level vs task-specific)
- [ ] Project-level findings appended to `.ai/learnings.md`
- [ ] Rules updated if convention gaps found
- [ ] AI-infrastructure files modified: changelog entry appended to `.ai/ai-changelog.md`
- [ ] Changelog entry written: hypothesis evaluated, and appended to `.ai/improvement-hypotheses.md` if warranted (appends only; a Status or marker edit stays with the validator's run)
- [ ] Brief names another writer for these two entries: both drafted in the return, that writer named, each listed as not done
- [ ] Results reported (count + summary)
"""


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _section(text: str, heading: str) -> str:
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
        raise AssertionError(f"review-checklist.md: no heading starting {heading!r}")
    return "\n".join(body)


def _checklist_rows(section: str) -> list[str]:
    """Every checklist row of the section as one string: its `- [ ]` line and the lines that
    continue it, up to a blank line or the start of another block, so a row wrapped over two
    lines is the same row."""
    rows: list[str] = []
    open_row = False
    for line in section.split("\n"):
        if line.startswith("- [ ]"):
            rows.append(line)
            open_row = True
        elif not line.strip() or line.startswith(("- ", "* ", "#", "|", ">", "```")):
            open_row = False
        elif open_row:
            rows[-1] += " " + line.strip()
    return rows


def _tracking_row(section: str) -> str | None:
    """The row right after the anchor row, when that row is the tracking row."""
    rows = _checklist_rows(section)
    for row, following in zip(rows, rows[1:], strict=False):
        if row.startswith(_ANCHOR_ROW) and "--error-unmatch" in following:
            return following
    return None


def _gaps(section: str) -> list[str]:
    """What the section lacks; the empty list means the row is there and says what it must."""
    row = _tracking_row(section)
    if row is None:
        return ["no row right after the changelog row that names --error-unmatch"]
    text = _plain(row)
    needed = {
        "the row marks each file tracked, untracked or ignored": "tracked, untracked or ignored",
        "the row names git ls-files --error-unmatch": "git ls-files --error-unmatch",
        "the row names git check-ignore -q": "git check-ignore -q",
        "the row asks for the tracked part of each count": "the tracked part of each count",
    }
    gaps = [label for label, needle in needed.items() if needle not in text]
    if "git add" in text:
        gaps.append("the row tells the author to git add the files")
    return gaps


def test_the_surface_is_stated_in_numbers() -> None:
    section = _section(_read(_CHECKLIST), "## Step 8")
    rows = _checklist_rows(section)
    assert len(rows) >= 10, (
        f"Step 8 holds {len(rows)} rows; the 9 old ones and the new one"
    )
    assert sum(1 for r in rows if r.startswith(_ANCHOR_ROW)) == 1, (
        "the anchor row is not unique"
    )
    assert "## Step 9" not in section, "the Step 8 slice runs past its own end"


def test_step_8_has_the_tracking_row_right_after_the_changelog_row() -> None:
    gaps = _gaps(_section(_read(_CHECKLIST), "## Step 8"))
    assert not gaps, f"Step 8 of review-checklist.md: {gaps}"


def test_the_old_step_8_has_no_tracking_row() -> None:
    """Fired at the section as it stood: the row is missing, so the one gap the check reports is
    the row itself, which is what the new row fixes."""
    old = _section(_OLD_STEP_8, "## Step 8")
    assert sum(1 for line in old.split("\n") if line.startswith("- [ ]")) == 9
    assert _gaps(old) == [
        "no row right after the changelog row that names --error-unmatch"
    ]


def test_the_row_check_sees_planted_rows() -> None:
    """Fired at planted rows: one that asks for git add, one placed before its anchor, one with
    another row before it, one with a row between it and its anchor, one missing a command, and a
    wrapped one. The last three placements are what pin the lookup to the anchor: a lookup that
    took any row naming --error-unmatch would still find the row in them."""
    anchor = f"{_ANCHOR_ROW} hypothesis evaluated"
    good = (
        "- [ ] A drafted changelog line marks each file it names as tracked, untracked or "
        "ignored (`git ls-files --error-unmatch <path>`, `git check-ignore -q <path>`) and "
        "gives the tracked part of each count"
    )
    section = f"## Step 8\n\n{anchor}\n{good}\n- [ ] next row\n"
    assert _gaps(section) == []
    assert (
        _gaps(section.replace("untracked or ignored", "untracked or\n  ignored")) == []
    )
    assert _gaps(section.replace("tracked part", "count")) == [
        "the row asks for the tracked part of each count"
    ]
    assert _gaps(section.replace("`git check-ignore -q <path>`", "`git status`")) == [
        "the row names git check-ignore -q"
    ]
    assert _gaps(section.replace("gives", "git add the files and gives")) == [
        "the row tells the author to git add the files"
    ]
    assert _gaps(f"## Step 8\n\n- [ ] next row\n{anchor}\n") == [
        "no row right after the changelog row that names --error-unmatch"
    ]
    assert _gaps(f"## Step 8\n\n{good}\n{anchor}\n") == [
        "no row right after the changelog row that names --error-unmatch"
    ]
    assert _gaps(f"## Step 8\n\n- [ ] other row\n{good}\n{anchor}\n") == [
        "no row right after the changelog row that names --error-unmatch"
    ]
    assert _gaps(f"## Step 8\n\n{anchor}\n- [ ] other row\n{good}\n") == [
        "no row right after the changelog row that names --error-unmatch"
    ]
    with pytest.raises(AssertionError, match="no heading"):
        _section("## Step 7\n", "## Step 8")
