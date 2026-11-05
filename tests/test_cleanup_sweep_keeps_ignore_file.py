"""initiative-cleanup's sweep table never sweeps a local-only folder's own ignore file.

kit-setup seeds a self-ignoring `.gitignore` in each local-only folder, and the folder stays
out of git through that file. The `.ai/tmp/` row of Step 4b's table said so ("Never the
folder's own `.gitignore`: kit-setup manages it"); the `.ai/handoffs/` row said only "Go", so a
sweep that followed it deleted the seeded file and every hand-off then showed in git.

These tests slice Step 4b by its heading, cut the hand-offs row by its leading text (no row, or
two, fails loudly) and assert that THAT row forbids sweeping the folder's own `.gitignore` and
names kit-setup as its owner; the clause on the `.ai/tmp/` row does not count for it. The cell
is edited in place because SKILL.md sits at the audit's line cap, so a second test holds the
file to the audit's own count. The helpers are functions over a string, so
`test_the_slicers_see_planted_text_and_fail_loudly` and
`test_the_clause_check_sees_planted_rows` fire them at planted text before their silence on the
real file is trusted.
"""

import re
from pathlib import Path

import pytest

from lemmi_ai_kit import checks
from lemmi_ai_kit.manifest import shipped_skill_dirs

_SKILL = shipped_skill_dirs()["initiative-cleanup"]
_HEADING = re.compile(r"^(#{1,6})\s+\S")

# The row is cut by its leading text. The clause is the two phrases the `.ai/tmp/` row already
# carries, matched after folding case and whitespace: the prohibition together with what it
# protects, and the reason.
_HAND_OFFS_ROW = "| Hand-offs in"
_CLAUSE_PHRASES = ("never the folder's own `.gitignore`", "kit-setup manages it")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text, lower-cased, with whitespace runs as one space, so a re-wrap changes no match."""
    return " ".join(text.split()).lower()


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the code it holds, not a heading. A missing heading fails with the
    heading named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
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


def _row(section: str, leading: str) -> str:
    """The one table row of `section` whose first line starts with `leading`.

    A row runs to the line before the next row (a line that starts with a pipe) or the first
    blank line, so a row re-wrapped onto a second line is still one row. No row, or two, fails
    with the leading text named, so a renamed row is a loud failure and never an empty match.
    """
    lines = section.split("\n")
    starts = [n for n, line in enumerate(lines) if line.startswith(leading)]
    if len(starts) != 1:
        raise AssertionError(
            f"the section has {len(starts)} rows starting {leading!r}; expected exactly one"
        )
    row = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if not line.strip() or line.startswith("|"):
            break
        row.append(line)
    return "\n".join(row)


def _missing_from(row: str) -> list[str]:
    """The phrases of the clause that the row does not carry; empty is a pass."""
    folded = _fold(row)
    return [phrase for phrase in _CLAUSE_PHRASES if phrase not in folded]


def _audit_line_count(text: str) -> int:
    """The count the skill audit takes of a file: one more than `wc -l` for a file that
    ends in a newline."""
    return text.count("\n") + 1


def _step_4b() -> str:
    return _section(
        _text(_SKILL / "SKILL.md"), "### 4b.", "initiative-cleanup SKILL.md"
    )


def test_the_hand_offs_row_never_sweeps_the_folders_own_ignore_file() -> None:
    row = _row(_step_4b(), _HAND_OFFS_ROW)
    missing = _missing_from(row)
    assert not missing, (
        f"the hand-offs row of Step 4b does not carry {missing}: {_fold(row)!r}"
    )


def test_the_skill_file_stays_within_the_audits_line_cap() -> None:
    count = _audit_line_count(_text(_SKILL / "SKILL.md"))
    assert count <= checks.MAX_SKILL_LINES, (
        f"SKILL.md is {count} lines by the audit's count and the cap is "
        f"{checks.MAX_SKILL_LINES}: the clause has to fit inside the table cell"
    )


# Planted rows. The old cell is what the hand-offs row said before the clause; the clause is
# what the `.ai/tmp/` row says.
_CLAUSE = "Never the folder's own `.gitignore`: kit-setup manages it"
_OLD_ROW = (
    "| Hand-offs in `.ai/handoffs/` | Go. They are pointers by contract; the durable fact "
    "is elsewhere in git |"
)
_NEW_ROW = (
    "| Hand-offs in `.ai/handoffs/` | Go. They are pointers by contract; the durable fact "
    f"is elsewhere in git. {_CLAUSE} |"
)
_TMP_ROW = f"| Genuine scratch under `.ai/tmp/` | Go. Gate captures and one-off scripts. {_CLAUSE} |"


def _planted_section(*rows: str) -> str:
    return "\n".join(
        [
            "### 4b. A planted section",
            "",
            "| Artifact | Disposition |",
            "|---|---|",
            *rows,
            "",
            "### 4c. After the section",
            "after the section",
        ]
    )


def test_the_slicers_see_planted_text_and_fail_loudly() -> None:
    wrapped_row = (
        "| Hand-offs in `.ai/handoffs/` | Go. They are pointers by contract;\n"
        "  the durable fact is elsewhere in git |"
    )
    planted = _planted_section(
        _TMP_ROW, wrapped_row, "| Next row | after the hand-offs |"
    )
    section = _section(planted, "### 4b.", "planted")
    assert "after the section" not in section
    row = _row(section, _HAND_OFFS_ROW)
    assert "the durable fact is elsewhere in git" in row, (
        "a re-wrapped row was cut short"
    )
    assert "Next row" not in row, "the row swallowed the one after it"
    assert "Genuine scratch" not in row, "the row took text from the one before it"
    assert "kit-setup" not in row, "the other row's clause leaked into this row"
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### 9z.", "planted")
    with pytest.raises(AssertionError, match="0 rows"):
        _row(section, "| Hand-offs of")
    with pytest.raises(AssertionError, match="2 rows"):
        _row(section + "\n" + _OLD_ROW, _HAND_OFFS_ROW)


def test_the_clause_check_sees_planted_rows() -> None:
    every_phrase = list(_CLAUSE_PHRASES)
    # The old cell says only "Go": every phrase of the clause is missing.
    assert _missing_from(_OLD_ROW) == every_phrase
    # The clause on the `.ai/tmp/` row does not count for the hand-offs row. Cut from the same
    # table, the hand-offs row still fails while the tmp row passes, so a failure is the row's
    # and never the check's.
    only_tmp = _planted_section(_TMP_ROW, _OLD_ROW)
    assert _missing_from(_row(only_tmp, _HAND_OFFS_ROW)) == every_phrase
    assert _missing_from(_row(only_tmp, "| Genuine scratch")) == []
    # A row that keeps half of the clause fails and names the half it lacks.
    mention = (
        "| Hand-offs in `.ai/handoffs/` | Go. The folder's own `.gitignore` is kept by "
        "kit-setup |"
    )
    no_owner = (
        "| Hand-offs in `.ai/handoffs/` | Go. Never the folder's own `.gitignore` |"
    )
    assert _missing_from(mention) == every_phrase
    assert _missing_from(no_owner) == ["kit-setup manages it"]
    # The clause kept passes: appended to the old cell, with the rest of the cell reworded, or
    # re-wrapped across lines.
    reworded = (
        "| Hand-offs in `.ai/handoffs/` | Go: each is a pointer by contract and the durable "
        "fact lives in git. Never the folder's own `.gitignore`; kit-setup manages it. |"
    )
    rewrapped = _planted_section(
        "| Hand-offs in `.ai/handoffs/` | Go. They are pointers by contract. Never the folder's",
        "  own `.gitignore`:   kit-setup",
        "manages it |",
        "| Next row | after |",
    )
    assert _missing_from(_NEW_ROW) == []
    assert _missing_from(reworded) == []
    assert _missing_from(_row(rewrapped, _HAND_OFFS_ROW)) == []
