"""The drain marker: each `CONSOLIDATION` entry says how many entries it drained.

A consolidation can promote now and drain later, or never. The cadence readers took the date
of the newest `CONSOLIDATION` entry in the changelog as the last drain, so a run that drained
nothing silenced every nudge while the buffer grew. Each `CONSOLIDATION` entry now carries
`- **Drained:** N entries` (the entries that run removed from the buffer, 0 allowed); a reader
takes the newest entry whose N is above 0, and an entry without the line counts as drained,
so a ledger written before the marker keeps working.

Two halves are pinned here, each red on the text or code it replaced:

* the changelog lint: once a ledger holds one entry with a `Drained` line, every
  `CONSOLIDATION` entry dated on or after the oldest such entry must carry the line, with a
  count. The cut-off is that entry, never a date in the code (the kit dropped hard-coded
  cut-offs for the adopter's `--since`), and the rule passes the same `--since` gate as the
  other per-entry checks;
* the places that read or write the marker: each reader names it, the "above 0" reading and
  the unmarked rule in the clause that does the reading, the changelog skill's example
  shows the line in a shape the lint reads, and its verify step names the check.
"""

import re
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from lemmi_ai_kit import checks

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"
_TASK_LEARNINGS = _SKILLS / "task-learnings" / "SKILL.md"
_RETROSPECTIVE = _SKILLS / "session-retrospective" / "SKILL.md"
_CONSOLIDATOR = _SKILLS / "learning-consolidator" / "SKILL.md"
_ACTIONS = _SKILLS / "learning-consolidator" / "references" / "consolidation-actions.md"
_CHANGELOG_SKILL = _SKILLS / "ai-changelog" / "SKILL.md"

_AT_LEAST = chr(0x2265)
_EM_DASH = chr(0x2014)

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


def _fold(text: str) -> str:
    return " ".join(text.split())


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _list_item(path: Path, lead: str, stop: str | None = None) -> str:
    """The list item whose first line starts with `lead`, folded.

    It runs through the indented and blank lines below that line, to the next line in column
    0, or to `stop` when one is given. A lead or a stop that is not found fails: a clause
    that moved is a test to update, never a clause to stop checking.
    """
    lines = _read(path).split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(lead)]
    assert len(starts) == 1, f"{path.name}: {len(starts)} lines start with {lead!r}"
    item = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        item.append(line)
    flat = _fold("\n".join(item))
    if stop is not None:
        assert stop in flat, f"{path.name}: {stop!r} is not in the item {lead!r}"
        flat = flat[: flat.index(stop)]
    return flat


def _paragraph(path: Path, lead: str) -> str:
    """The blank-line-delimited paragraph that starts with `lead`, folded."""
    blocks = re.split(r"\n\s*\n", _read(path))
    found = [block for block in blocks if block.lstrip().startswith(lead)]
    assert len(found) == 1, f"{path.name}: {len(found)} paragraphs start with {lead!r}"
    return _fold(found[0])


def _table_row(path: Path, lead: str) -> str:
    rows = [line for line in _read(path).split("\n") if line.startswith(lead)]
    assert len(rows) == 1, f"{path.name}: {len(rows)} rows start with {lead!r}"
    return _fold(rows[0])


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


# Each place: the clause that reads the marker, and the old reading it replaced, which must
# be gone from that clause.
_PLACES: dict[str, tuple[Callable[[], str], str]] = {
    "task-learnings-buffer-pressure-check": (
        lambda: _list_item(_TASK_LEARNINGS, "4. **Buffer-pressure check"),
        "OR the newest `CONSOLIDATION` entry in `.ai/ai-changelog.md` is **"
        + _AT_LEAST
        + " 7 days old**",
    ),
    "retrospective-closing-nudge": (
        lambda: _list_item(_RETROSPECTIVE, "3. **Surface the sibling cadence**"),
        "read the newest `CONSOLIDATION` date in `.ai/ai-changelog.md`",
    ),
    "consolidator-cadence-guard": (
        lambda: _list_item(
            _CONSOLIDATOR, "0. **Cadence guard**", stop="Cadence: measured"
        ),
        "read the newest `CONSOLIDATION` entry date in `.ai/ai-changelog.md`",
    ),
    "consolidator-keep-dwell-limit": (
        lambda: _list_item(_CONSOLIDATOR, "4. **Keep entries**"),
        "check its date against the two most recent `CONSOLIDATION` entries in "
        "`.ai/ai-changelog.md`)",
    ),
    "actions-dwell-limit": (
        lambda: _paragraph(_ACTIONS, "**Dwell limit (lean-buffer invariant):**"),
        "the two most recent `CONSOLIDATION` entries in `.ai/ai-changelog.md` "
        + _EM_DASH
        + " if the entry predates both",
    ),
    "changelog-type-row": (
        lambda: _table_row(_CHANGELOG_SKILL, "| `CONSOLIDATION` |"),
        "| `CONSOLIDATION` | Learnings promoted to rules/skills during consolidation |",
    ),
}


@pytest.mark.parametrize("place", sorted(_PLACES))
def test_each_place_reads_the_last_drain_by_its_marker(place: str) -> None:
    scope, old = _PLACES[place]
    clause = scope()

    assert _marker_gaps(clause) == [], f"{place} does not say: {_marker_gaps(clause)}"
    assert old not in clause, f"{place} still states the reading it replaced"


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


def test_the_verify_step_names_the_marker_check_and_its_fallback() -> None:
    """What Step 3 says the lint checks, and its fallback for when the lint cannot run, each
    name the marker; the sentence it replaced named neither."""
    paragraph = _paragraph(_CHANGELOG_SKILL, "It checks date-heading order")
    fallback_lead = "Fallback only if the lint cannot run"
    assert fallback_lead in paragraph, f"Step 3 has no {fallback_lead!r} clause"
    lint, fallback = paragraph.split(fallback_lead, 1)

    gaps = [p for p in ("Drained", "`CONSOLIDATION`", "oldest") if p not in lint]
    gaps += [
        f"fallback: {p}" for p in ("Drained", "`CONSOLIDATION`") if p not in fallback
    ]
    assert gaps == [], f"Step 3 does not say {gaps}"
    assert "the 12-type taxonomy, and required fields." not in lint


def test_the_consolidator_writes_the_marker_into_its_changelog_entry() -> None:
    """The writer must know the line and that a run which removed nothing writes 0: an entry
    without the line counts as drained, so leaving it out is the defect itself."""
    step = _paragraph(_CONSOLIDATOR, "**7a. Append changelog entry**")

    assert re.search(r"Drained.{0,120}\b0\b", step), step
