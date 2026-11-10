"""The checks of the changelog drained marker tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_a_marked_ledger_flags_a_later_unmarked_entry_not_an_earlier_one`: a marked ledger flags a later unmarked entry not an earlier one
* `test_the_rule_starts_at_the_oldest_marked_entry_not_the_newest`: A newer marked entry does not move the cut-off: an unmarked entry between two marked ones is judged, because it is dated after the oldest of them.
* `test_an_unmarked_entry_dated_on_the_first_marked_day_is_judged`: On or after: the boundary day is inside the rule, and a count of 0 is a marker.
* `test_an_unmarked_ledger_gives_no_finding`: A ledger that never wrote the marker is never judged by it; the same ledger with its oldest entry marked is the positive control that shows the rule is there to fire.
* `test_since_keeps_an_entry_dated_before_it_out_of_judgment`: Without the option both later entries are judged, so the option is what spares one. The marked entry is itself before the cutoff: adoption is read from the whole file.
* `test_an_entry_of_another_type_is_never_judged`: an entry of another type is never judged
* `test_a_drained_line_on_another_type_does_not_mark_the_ledger`: The marker is a `CONSOLIDATION` entry's line, and the readers look for it nowhere else, so the same line under another type is not the ledger adopting it. The positive control is the same ledger with the line on a `CONSOLIDATION` entry.
* `test_a_drained_line_without_a_count_is_reported`: A line with no count still marks the ledger, so the typo is reported rather than hidden; the older unmarked entry stays spared.
* `test_a_count_of_zero_or_more_is_a_marker`: The counted entry passes, and it marks the ledger: the later unmarked one is flagged.
* `test_the_marker_check_flags_the_old_reading_and_spares_the_new_one`: the marker check flags the old reading and spares the new one
* `test_the_grouping_example_shows_the_marker_in_the_shape_the_lint_reads`: the grouping example shows the marker in the shape the lint reads
"""

import re
from datetime import date
from pathlib import Path

import pytest

from lemmi_ai_kit import checks

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"
_CHANGELOG_SKILL = _SKILLS / "ai-changelog" / "SKILL.md"


_MARKER_LINE = re.compile(r"^- \*\*Drained:\*\* \d+ entries$")

# --- the lint -----------------------------------------------------------------------------


def _entry(kind: str, title: str, drained: str | None = None) -> str:
    """One entry that passes every other check; `drained` follows `- **Drained:**`."""
    marker = [] if drained is None else [f"- **Drained:** {drained}".rstrip()]
    lines = [f"### {kind}: {title}", "- **What:** w", *marker, "- **Why:** y"]
    return "\n".join([*lines, "- **Files:** f", "- **Affected workflows:** none", ""])


def _ledger(*days: tuple[str, str]) -> str:
    """A changelog with one `## <date>` section per `(date, entries)` pair, newest first."""
    return "# AI Infrastructure Changelog\n" + "".join(
        f"\n## {day}\n\n{entries}" for day, entries in days
    )


def _line_of(text: str, title: str) -> int:
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("### ") and line.endswith(f": {title}"):
            return number
    raise AssertionError(f"the fixture has no entry titled {title!r}")


def _flagged(text: str, since: date | None = None) -> list[int]:
    """The lines the lint flags. These fixtures pass every other check, so a finding that is
    not about the marker is a broken fixture, not a result."""
    findings = checks.lint_changelog(text, "x.md", since=since)
    assert all("Drained" in f.message and not f.note for f in findings), findings
    return [f.line for f in findings]


def test_a_marked_ledger_flags_a_later_unmarked_entry_not_an_earlier_one() -> None:
    text = _ledger(
        ("2026-03-01", _entry("CONSOLIDATION", "promoted, drain left for later")),
        ("2026-02-01", _entry("CONSOLIDATION", "the first marked drain", "4 entries")),
        ("2026-01-01", _entry("CONSOLIDATION", "a drain written before the marker")),
    )

    assert _flagged(text) == [_line_of(text, "promoted, drain left for later")]


def test_the_rule_starts_at_the_oldest_marked_entry_not_the_newest() -> None:
    """A newer marked entry does not move the cut-off: an unmarked entry between two marked
    ones is judged, because it is dated after the oldest of them."""
    text = _ledger(
        ("2026-04-01", _entry("CONSOLIDATION", "a later marked drain", "2 entries")),
        ("2026-03-01", _entry("CONSOLIDATION", "promoted, drain left for later")),
        ("2026-02-01", _entry("CONSOLIDATION", "the first marked drain", "4 entries")),
    )

    assert _flagged(text) == [_line_of(text, "promoted, drain left for later")]


def test_an_unmarked_entry_dated_on_the_first_marked_day_is_judged() -> None:
    """On or after: the boundary day is inside the rule, and a count of 0 is a marker."""
    same_day = _entry("CONSOLIDATION", "same day, unmarked") + "\n"
    same_day += _entry("CONSOLIDATION", "same day, drained nothing", "0 entries")
    text = _ledger(("2026-02-01", same_day))

    assert _flagged(text) == [_line_of(text, "same day, unmarked")]


def test_an_unmarked_ledger_gives_no_finding() -> None:
    """A ledger that never wrote the marker is never judged by it; the same ledger with its
    oldest entry marked is the positive control that shows the rule is there to fire."""
    later = _entry("CONSOLIDATION", "promoted, drain left for later")
    unmarked = _ledger(
        ("2026-03-01", later), ("2026-02-01", _entry("CONSOLIDATION", "a drain"))
    )
    marked = _ledger(
        ("2026-03-01", later),
        ("2026-02-01", _entry("CONSOLIDATION", "a drain", "9 entries")),
    )

    assert checks.lint_changelog(unmarked, "x.md") == []
    assert _flagged(marked) == [_line_of(marked, "promoted, drain left for later")]


def test_since_keeps_an_entry_dated_before_it_out_of_judgment() -> None:
    """Without the option both later entries are judged, so the option is what spares one.
    The marked entry is itself before the cutoff: adoption is read from the whole file."""
    text = _ledger(
        ("2026-04-01", _entry("CONSOLIDATION", "after the cutoff")),
        ("2026-03-01", _entry("CONSOLIDATION", "before the cutoff")),
        ("2026-02-01", _entry("CONSOLIDATION", "the first marked drain", "4 entries")),
    )

    assert _flagged(text) == [
        _line_of(text, "after the cutoff"),
        _line_of(text, "before the cutoff"),
    ]
    assert _flagged(text, since=date(2026, 3, 15)) == [
        _line_of(text, "after the cutoff")
    ]


@pytest.mark.parametrize("kind", sorted(checks.CHANGELOG_TYPES - {"CONSOLIDATION"}))
def test_an_entry_of_another_type_is_never_judged(kind: str) -> None:
    later = _entry(kind, "another type, no marker") + "\n"
    later += _entry("CONSOLIDATION", "promoted, drain left for later")
    text = _ledger(
        ("2026-03-01", later),
        ("2026-02-01", _entry("CONSOLIDATION", "the first marked drain", "4 entries")),
    )

    assert _flagged(text) == [_line_of(text, "promoted, drain left for later")]


def test_a_drained_line_on_another_type_does_not_mark_the_ledger() -> None:
    """The marker is a `CONSOLIDATION` entry's line, and the readers look for it nowhere else,
    so the same line under another type is not the ledger adopting it. The positive control
    is the same ledger with the line on a `CONSOLIDATION` entry."""
    later = _entry("CONSOLIDATION", "promoted, drain left for later")
    elsewhere = _ledger(
        ("2026-03-01", later),
        ("2026-02-01", _entry("INFRA-MODIFIED", "a counted note", "4 entries")),
    )
    on_a_drain = _ledger(
        ("2026-03-01", later),
        ("2026-02-01", _entry("CONSOLIDATION", "a counted note", "4 entries")),
    )

    assert checks.lint_changelog(elsewhere, "x.md") == []
    assert _flagged(on_a_drain) == [
        _line_of(on_a_drain, "promoted, drain left for later")
    ]


@pytest.mark.parametrize(
    "value", ["", "some entries", "-3 entries", "1.5 entries", "none"]
)
def test_a_drained_line_without_a_count_is_reported(value: str) -> None:
    """A line with no count still marks the ledger, so the typo is reported rather than
    hidden; the older unmarked entry stays spared."""
    text = _ledger(
        ("2026-03-01", _entry("CONSOLIDATION", "a marker with no count", value)),
        ("2026-02-01", _entry("CONSOLIDATION", "a drain written before the marker")),
    )

    assert _flagged(text) == [_line_of(text, "a marker with no count")]


@pytest.mark.parametrize("value", ["0 entries", "1 entry", "360 entries"])
def test_a_count_of_zero_or_more_is_a_marker(value: str) -> None:
    """The counted entry passes, and it marks the ledger: the later unmarked one is flagged."""
    text = _ledger(
        ("2026-03-01", _entry("CONSOLIDATION", "promoted, drain left for later")),
        ("2026-02-01", _entry("CONSOLIDATION", "a counted drain", value)),
    )

    assert _flagged(text) == [_line_of(text, "promoted, drain left for later")]


# --- the places that read or write the marker ---------------------------------------------


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(path: Path, heading: str) -> str:
    """The lines under `heading` to the next `## ` heading outside a fence."""
    lines = _read(path).split("\n")
    assert heading in lines, f"{path.name} has no heading {heading!r}"
    found: list[str] = []
    inside = False
    for line in lines[lines.index(heading) + 1 :]:
        if line.lstrip().startswith("```"):
            inside = not inside
        elif not inside and line.startswith("## "):
            break
        found.append(line)
    return "\n".join(found)


def _fenced_lines(text: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
        elif inside:
            lines.append(line)
    return lines


# What a clause that dates the last drain must say: the marker by name, the reading (a count
# above 0), and what an entry without the line counts as.
_READER_PHRASES: tuple[str, ...] = (
    "Drained",
    "above 0",
    "without the line counts as drained",
)


def _marker_gaps(clause: str) -> list[str]:
    return [phrase for phrase in _READER_PHRASES if phrase not in clause]


def test_the_marker_check_flags_the_old_reading_and_spares_the_new_one() -> None:
    old = "and read the newest `CONSOLIDATION` entry date in `.ai/ai-changelog.md`."
    partial = "the newest `CONSOLIDATION` entry that has a `**Drained:**` line"
    new = (
        "the newest `CONSOLIDATION` entry whose `**Drained:**` count is above 0 (one "
        "without the line counts as drained)"
    )

    assert _marker_gaps(old) == list(_READER_PHRASES)
    assert _marker_gaps(partial) == ["above 0", "without the line counts as drained"]
    assert _marker_gaps(new) == []


def test_the_grouping_example_shows_the_marker_in_the_shape_the_lint_reads() -> None:
    example = _fenced_lines(
        _section(_CHANGELOG_SKILL, "## Grouping Under Consolidation")
    )
    markers = [line for line in example if _MARKER_LINE.match(line)]
    assert len(markers) == 1, f"the grouping example shows {len(markers)} marker lines"

    entry = "\n".join(example) + "\n"
    first_marked = _entry("CONSOLIDATION", "the first marked drain", "4 entries")
    with_marker = _ledger(("2026-03-01", entry), ("2026-02-01", first_marked))
    without = _ledger(
        ("2026-03-01", entry.replace(markers[0] + "\n", "")),
        ("2026-02-01", first_marked),
    )

    assert checks.lint_changelog(with_marker, "x.md") == []
    assert len(_flagged(without)) == 1
