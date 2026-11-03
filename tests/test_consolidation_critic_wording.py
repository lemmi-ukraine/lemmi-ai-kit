"""The consolidation critic bounds its readers, ranks a fidelity defect and names the audit snapshot.

Three places of the critic's SKILL.md were silent or stale:

* C6 sent ONE fresh reader through every promoted paragraph, while the cap on a reader's brief
  (section 2 of the fix-rounds reference of `post-task-review`) is four real claims, plus the
  planted one. C6 now quotes that cap and spawns one fresh reader per four promoted paragraphs.
  Both numbers are read back from that section, so a cap that changes turns this file red.
* The Severity table gave a fidelity defect (a promoted paragraph that says more or less than its
  source entry) no row. The Major row now lists it beside overstated confidence, and the table
  keeps its three columns and its three rows.
* The Inputs row for the pre-drain snapshot, the two printed audit commands and the note on a
  reconstruction described the old drain: a snapshot file at a path that was committed with it.
  The consolidator now commits the buffer at a restore point and keeps a byte copy and the gate
  record local, and the audit script takes a FILE, so the snapshot is a scratch file written from
  the buffer at the restore-point commit. The three places now say so, and the old shapes are gone.
  The note also says what the byte copy is, since nothing else in the critic does.

THE SURFACE, in numbers the tests assert: 4 places in 1 file (the C6, Severity and Resolution,
Inputs and C1 sections of the critic's SKILL.md), 7 checks, 10 phrases the checks read and 3 old
shapes they refuse, plus the shape of the Severity table (a header, a separator and 3 rows of 3
cells), which the old text already had and the real text must keep. Each check is fired at the
text its place carried before (`old`, unedited excerpts) and at a fixture that fixes only that
place; each phrase is removed from the real text one at a time and must be the only thing
reported; each old shape is planted into the real text and must be the only thing reported; the
structural checks (the cap, the Severity table, the printed commands) are fired at near-misses of
the shape they read. A heading or a lead that is not found fails loudly, with the heading named.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"
_CRITIC_MD = _SKILLS / "consolidation-critic" / "SKILL.md"
_FIX_ROUNDS = _SKILLS / "post-task-review" / "references" / "fix-rounds.md"

_HEADING = re.compile(r"^(#{1,6})\s")
_SEPARATOR_CELL = re.compile(r":?-{3,}:?")

_EM = chr(0x2014)
_GE = chr(0x2265)

_NUMBERS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

# What C6 says about the count, and what the cap's own section says (both read on plain text).
_PER = re.compile(r"\bone fresh reader per (\w+) promoted paragraphs\b")
_CAP = re.compile(r"\bat most (\w+) real claims\b")

_PRINTED_AUDIT_COMMANDS = 2
_OLD_OPERAND = ".ai/learnings-pre-drain-<date>.md"
_NEW_OPERAND = "<pre-drain-snapshot>.md"

_ITEM = "a fidelity defect (a promoted paragraph that says more or less than its source entry)"
_COUNT = (
    "A reader's brief carries at most four real claims, plus the planted one, so spawn one fresh "
    "reader per four promoted paragraphs."
)


# --- slicers over a string -------------------------------------------------------------------


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same.
    A missing file is its own loud failure, never an empty match."""
    if not path.is_file():
        raise AssertionError(f"{path.name} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _chars(text: str) -> str:
    """A fixture with the two non-ASCII characters it was written with, put back."""
    return text.replace("<EM>", _EM).replace("<GE>", _GE)


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return " ".join(re.sub(r"[*`]", "", text).split())


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or
    a higher level. A `#` line inside a fenced block is not a heading (C1 prints shell comments).
    A missing heading fails loudly, with the heading named."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = _is_fence(line)
        found = None if in_fence or fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
        elif found is not None and len(found[1]) <= level:
            break
        else:
            body.append(line)
        if fence:
            in_fence = not in_fence
    if not body:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


def _block(text: str, lead: str, where: str) -> str:
    """The blank-line-delimited block whose first line starts with `lead`; missing fails loudly."""
    for block in re.split(r"\n\s*\n", text):
        if block.lstrip().startswith(lead):
            return block
    raise AssertionError(f"{where}: no block starts with {lead!r}")


def _table_rows(text: str) -> list[list[str]]:
    """Every table row of the text as its cells, the outer pipes dropped."""
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in text.split("\n")
        if line.strip().startswith("|")
    ]


def _data_rows(text: str) -> list[list[str]]:
    """The table rows that are neither the header (the first row) nor the separator."""
    return [
        row
        for row in _table_rows(text)[1:]
        if not all(_SEPARATOR_CELL.fullmatch(cell) for cell in row)
    ]


def _items(cell: str) -> list[str]:
    """The comma-separated items of a cell; a comma inside parentheses stays in its item."""
    items: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(cell):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            items.append(cell[start:index].strip())
            start = index + 1
    items.append(cell[start:].strip())
    return items


def _number(word: str) -> int | None:
    return _NUMBERS.get(word.lower(), int(word) if word.isdigit() else None)


# --- the cuts: the place a check reads inside its section ------------------------------------


def _c6(text: str) -> str:
    return _section(text, "### C6", "SKILL.md")


def _severity(text: str) -> str:
    return _section(text, "## Severity and Resolution", "SKILL.md")


def _inputs(text: str) -> str:
    return _section(text, "## Inputs", "SKILL.md")


def _c1(text: str) -> str:
    return _section(text, "### C1", "SKILL.md")


def _whole(region: str) -> str:
    return region


def _snapshot_row(inputs: str) -> str:
    for line in inputs.split("\n"):
        if line.startswith("| The pre-drain snapshot"):
            return line
    raise AssertionError("Inputs: no table row starts with '| The pre-drain snapshot'")


def _lead(c1: str) -> str:
    return _block(c1, "Removal verification proves", "C1")


def _note(c1: str) -> str:
    return _block(c1, "**If no snapshot exists**", "C1")


# --- the structural checks ---------------------------------------------------------------------


def _cap_of(fix_rounds: str) -> int:
    """The number of real claims a fresh reader's brief carries at most, as section 2 of the
    fix-rounds reference states it."""
    section = _section(fix_rounds, "## 2.", "fix-rounds.md")
    found = _CAP.search(_plain(section))
    if found is None:
        raise AssertionError("section 2 of fix-rounds.md states no cap on real claims")
    cap = _number(found[1])
    if cap is None:
        raise AssertionError(
            f"section 2 of fix-rounds.md caps real claims at {found[1]!r}"
        )
    return cap


def _cap() -> int:
    return _cap_of(_read(_FIX_ROUNDS))


def _spawns_one_reader_per(cap: int, text: str) -> bool:
    found = _PER.search(_plain(text))
    return found is not None and _number(found[1]) == cap


def _quotes_the_cap(cap: int, text: str) -> bool:
    found = _CAP.search(_plain(text))
    return found is not None and _number(found[1]) == cap


def _spawns_per_the_section_cap(text: str) -> bool:
    return _spawns_one_reader_per(_cap(), text)


def _quotes_the_section_cap(text: str) -> bool:
    return _quotes_the_cap(_cap(), text)


def _major_names_the_fidelity_defect(table: str) -> bool:
    """The Major row lists a fidelity defect right beside overstated confidence, with its gloss,
    and no other row names one."""
    rows = {_plain(row[0]): row for row in _data_rows(table)}
    major = rows.get("Major")
    if major is None or len(major) < 2:
        return False
    items = [_plain(item) for item in _items(major[1])]
    confidence = [
        k for k, item in enumerate(items) if item.startswith("overstated confidence")
    ]
    defect = [k for k, item in enumerate(items) if item.startswith("a fidelity defect")]
    elsewhere = any(
        "fidelity defect" in _plain(" ".join(row[1:]))
        for name, row in rows.items()
        if name != "Major"
    )
    return (
        len(confidence) == 1
        and len(defect) == 1
        and abs(confidence[0] - defect[0]) == 1
        and "says more or less than its source entry" in items[defect[0]]
        and not elsewhere
    )


def _severity_table_keeps_its_shape(table: str) -> bool:
    """A header, a separator and the three rows Blocker, Major, Minor, each of three cells."""
    rows = _table_rows(table)
    names = [_plain(row[0]) for row in _data_rows(table)]
    return (
        len(rows) == 5
        and all(len(row) == 3 for row in rows)
        and names == ["Blocker", "Major", "Minor"]
    )


def _printed_audit_operands(text: str) -> list[list[str]]:
    """The operands (options left out) of each `drain_audit.py` command printed in a fenced block
    of the text. A command continues over a line that ends in a backslash."""
    commands: list[str] = []
    pending = ""
    in_fence = False
    for line in text.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
            continue
        stripped = line.strip()
        if not in_fence or not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
            continue
        commands.append(pending + stripped)
        pending = ""
    operands: list[list[str]] = []
    for command in commands:
        tokens = command.split()
        for index, token in enumerate(tokens):
            if token.strip('"').endswith("drain_audit.py"):
                operands.append(
                    [t for t in tokens[index + 1 :] if not t.startswith("-")]
                )
                break
    return operands


def _audit_commands_take_the_scratch_snapshot(region: str) -> bool:
    """Two printed commands, and neither names the byte copy's path as its snapshot. A scan that
    found no command at all is not a pass."""
    operands = _printed_audit_operands(region)
    return len(operands) == _PRINTED_AUDIT_COMMANDS and all(
        bool(ops) and "learnings-pre-drain" not in ops[0] for ops in operands
    )


def _says(
    needs: tuple[str, ...], refuses: tuple[re.Pattern[str], ...] = ()
) -> Callable[[str], bool]:
    """Holds when every phrase of `needs` is in the text and no old shape of `refuses` is."""

    def holds(text: str) -> bool:
        plain = _plain(text)
        return all(need in plain for need in needs) and not any(
            old.search(plain) for old in refuses
        )

    return holds


# --- the places and their checks ---------------------------------------------------------------


class _Check(NamedTuple):
    label: str
    cut: Callable[[str], str]
    holds: Callable[[str], bool]
    removable: tuple[re.Pattern[str], ...] = ()
    refuses: tuple[tuple[re.Pattern[str], str], ...] = ()


class _Place(NamedTuple):
    name: str
    locate: Callable[[str], str]
    checks: tuple[_Check, ...]
    old: str
    fix: Callable[[str], str]


def _phrase_check(
    label: str,
    cut: Callable[[str], str],
    needs: tuple[str, ...],
    refuses: tuple[tuple[re.Pattern[str], str], ...] = (),
) -> _Check:
    return _Check(
        label,
        cut,
        _says(needs, tuple(pattern for pattern, _ in refuses)),
        tuple(re.compile(re.escape(need)) for need in needs),
        refuses,
    )


def _swap(text: str, pattern: str, replacement: str) -> str:
    """`text` with every match of `pattern` replaced; a pattern that matches nothing fails."""
    fixed, count = re.subn(pattern, lambda _: replacement, text)
    if count == 0:
        raise AssertionError(f"the excerpt has no {pattern!r} to fix")
    return fixed


_OLD_C6 = _chars("""### C6 <EM> Epistemic audit

**Fidelity read.** The checks above test where an entry landed, what its passage cites and whether
its hedge survived; none reads the rewritten paragraph beside the entry it came from, so a
paraphrase that changes the claim passes them all. A fresh reader carries the read, not you: the
author of a paraphrase reads it as faithful. You spawn it, as `post-task-review` describes one for
a fix round (section 2 of its fix-rounds reference, the planted false claim included), and brief it
to read each promoted paragraph beside its source entry in the pre-drain snapshot and list every
place it changes the claim: a narrative inverted, two techniques fused into one, a sentence
addressed to the promoter left in committed text, a dropped qualifier such as "not run" or "only".
A promotion passes only when the read lists none. The read does not replace C1 to C8.
""")

_OLD_SEVERITY = _chars("""## Severity and Resolution

| Severity | Definition | Action |
|---|---|---|
| **Blocker** | Deleted knowledge (C1), or a false claim already shipped into a rule (C2) | Fix before the consolidation may be reported complete |
| **Major** | Wrong altitude, <GE>3-way duplication, self-contradiction, overstated confidence, prose where a seam belongs | Resolve by revising; if it needs a decision only the user can make, surface it as `[UNRESOLVED]` |
| **Minor** | Wording, formatting, a redundant clause | Fix silently |
""")

_OLD_INPUTS = _chars("""## Inputs

| Input | Why it is needed |
|---|---|
| The pre-drain snapshot (`.ai/learnings-pre-drain-<date>.md`) | C1 cannot run without it |
| `git diff HEAD` over the promotion targets | The actual change under review <EM> not your memory of it |
| The consolidation plan (`.ai/consolidation-plan-*.md`) | Promotions the plan promised but the drain never made |
| The gate record (`.ai/consolidation-gates/<date>-plan-approved.md`) | The plan as recorded approved before any removal: a written claim C1 checks against the plan the operator saw |
""")

_OLD_C1 = _chars(
    """### C1 <EM> Landing audit (mechanical, non-negotiable)

Removal verification proves entries left the buffer. It is **structurally blind** to the opposite
failure: an entry removed whose knowledge reached no home. Run the audit that fits the state of the
promotions, with the same `--surface` values as the consolidator's Phase 5 audit (`--surface <glob>`
adds a home); the base ref is mandatory (no ref exits 2):

"""
    + r"""```bash
# Promotions still UNCOMMITTED: HEAD is the pre-promotion state.
python "${CLAUDE_PLUGIN_ROOT}/skills/learning-consolidator/scripts/drain_audit.py" \
  .ai/learnings-pre-drain-<date>.md HEAD

# Promotions ALREADY COMMITTED: the commit before the promotion commit, never HEAD.
python "${CLAUDE_PLUGIN_ROOT}/skills/learning-consolidator/scripts/drain_audit.py" \
  .ai/learnings-pre-drain-<date>.md <promo-commit>~1
```

"""
    + """**If no snapshot exists** (a drain that predates the Phase-5 snapshot requirement), reconstruct one
from git into scratch: the operator writes the buffer's last committed contents to a scratch path in
their own terminal (a session never names the buffer on a shell line), deliberately NOT the
committed snapshot path, because a reconstruction is not evidence <EM> and say so in the report: a
snapshot rebuilt from the last commit misses anything appended since, so C1's coverage is partial
and must be stated as partial, not clean.
"""
)


def _fix_c6(old: str) -> str:
    """The old C6 with the count sentence added before the promotion rule."""
    return _swap(old, r"A promotion passes only", f"{_COUNT} A promotion passes only")


def _fix_severity(old: str) -> str:
    return _swap(
        old, r"overstated confidence, prose", f"overstated confidence, {_ITEM}, prose"
    )


def _fix_inputs(old: str) -> str:
    return _swap(
        old,
        r"The pre-drain snapshot \(`[^`]*`\)",
        "The pre-drain snapshot: a scratch file written from the buffer at the restore-point "
        "commit",
    )


def _fix_c1(old: str) -> str:
    lead = _swap(
        old,
        r"adds a home\); the base ref is mandatory \(no ref exits 2\):",
        "adds a home). It takes the pre-drain snapshot, a scratch file written from the buffer "
        "at the restore-point commit, and a base ref, which is mandatory (no ref exits 2):",
    )
    commands = _swap(lead, re.escape(_OLD_OPERAND), _NEW_OPERAND)
    reason = _swap(
        commands,
        r"the Phase-5 snapshot requirement",
        "the Phase-5 restore point",
    )
    return _swap(
        reason,
        r"NOT the\s+committed snapshot path, because a reconstruction is not evidence "
        + _EM
        + r" and say so",
        "NOT the byte copy's path (the operator's local, never-committed copy of the buffer "
        "from Phase 5), so it cannot pass for that copy, and say so",
    )


_PLACES: tuple[_Place, ...] = (
    _Place(
        "c6-reader-count",
        _c6,
        (
            _Check(
                "C6 spawns one fresh reader per as many promoted paragraphs as the cap allows "
                "real claims",
                _whole,
                _spawns_per_the_section_cap,
                (_PER,),
            ),
            _Check(
                "C6 quotes the cap on a reader's real claims in the cap's own words",
                _whole,
                _quotes_the_section_cap,
                (_CAP,),
            ),
        ),
        _OLD_C6,
        _fix_c6,
    ),
    _Place(
        "severity-table",
        _severity,
        (
            _Check(
                "the Severity table ranks a fidelity defect Major, beside overstated confidence",
                _whole,
                _major_names_the_fidelity_defect,
            ),
        ),
        _OLD_SEVERITY,
        _fix_severity,
    ),
    _Place(
        "inputs-snapshot-row",
        _inputs,
        (
            _phrase_check(
                "the Inputs row for the pre-drain snapshot names the restore-point commit and a "
                "scratch file, not the byte copy's path",
                _snapshot_row,
                ("restore-point commit", "scratch file"),
                (
                    (
                        re.compile(r"learnings-pre-drain"),
                        "The pre-drain snapshot (.ai/learnings-pre-drain-<date>.md)",
                    ),
                ),
            ),
        ),
        _OLD_INPUTS,
        _fix_inputs,
    ),
    _Place(
        "c1-snapshot-lines",
        _c1,
        (
            _phrase_check(
                "the C1 lead hands the audit the pre-drain snapshot as a scratch file written "
                "from the buffer at the restore-point commit",
                _lead,
                ("pre-drain snapshot", "scratch file", "restore-point commit"),
            ),
            _Check(
                "the two printed audit commands pass a snapshot operand that is not the byte "
                "copy's path",
                _whole,
                _audit_commands_take_the_scratch_snapshot,
            ),
            _phrase_check(
                "the C1 note on a reconstruction keeps it off the byte copy's path, says what "
                "that copy is and names the restore point",
                _note,
                (
                    "NOT the byte copy's path",
                    "the operator's local, never-committed copy of the buffer",
                    "the Phase-5 restore point",
                ),
                (
                    (
                        re.compile(r"committed snapshot"),
                        "deliberately NOT the committed snapshot path",
                    ),
                    (
                        re.compile(r"snapshot requirement"),
                        "a drain that predates the Phase-5 snapshot requirement",
                    ),
                ),
            ),
        ),
        _OLD_C1,
        _fix_c1,
    ),
)

_ALL_CHECKS = tuple(check for place in _PLACES for check in place.checks)
_REMOVALS = [
    (place, check, pattern)
    for place in _PLACES
    for check in place.checks
    for pattern in check.removable
]
_REFUSALS = [
    (place, check, pattern, example)
    for place in _PLACES
    for check in place.checks
    for pattern, example in check.refuses
]


def _gaps(checks: tuple[_Check, ...], region: str) -> list[str]:
    return [c.label for c in checks if not c.holds(c.cut(region))]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def _skill() -> str:
    return _read(_CRITIC_MD)


# --- the tests ---------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    """4 places in 1 file, 7 checks, 10 phrases the checks read and 3 old shapes they refuse."""
    assert len(_PLACES) == 4, f"{len(_PLACES)} places, not the 4 stated"
    assert len(_ALL_CHECKS) == 7, f"{len(_ALL_CHECKS)} checks, not the 7 stated"
    assert len(_REMOVALS) == 10, f"{len(_REMOVALS)} phrases, not the 10 stated"
    assert len(_REFUSALS) == 3, f"{len(_REFUSALS)} old shapes, not the 3 stated"
    assert len({c.label for c in _ALL_CHECKS}) == len(_ALL_CHECKS), (
        "two checks share a label"
    )
    assert len({p.name for p in _PLACES}) == len(_PLACES), "two places share a name"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_carries_its_rule(place: _Place) -> None:
    gaps = _gaps(place.checks, place.locate(_skill()))
    assert not gaps, f"SKILL.md ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The known positive: the excerpt each place carried before names no cap, ranks no fidelity
    defect and describes the old snapshot, so every check must say so."""
    reported = _gaps(place.checks, place.locate(place.old))
    assert reported == [c.label for c in place.checks], (
        f"{place.name}: blind to the old text: "
        f"{[c.label for c in place.checks if c.label not in reported]}"
    )


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_fixture_that_fixes_only_one_place_passes_that_places_checks(
    place: _Place,
) -> None:
    """The known positive of the other polarity: the old excerpt with only this place fixed."""
    fixed = place.fix(place.old)
    assert fixed != place.old
    assert not _gaps(place.checks, place.locate(fixed)), place.name


@pytest.mark.parametrize(
    ("place", "check", "pattern"),
    _REMOVALS,
    ids=[f"{p.name}-{_slug(r.pattern)}" for p, _, r in _REMOVALS],
)
def test_each_phrase_removed_alone_is_the_only_gap(
    place: _Place, check: _Check, pattern: re.Pattern[str]
) -> None:
    """A near-miss of the real text: one phrase gone, the rest intact. Only the check that needs
    the phrase may report it, so no check leans on another's words."""
    scope = _plain(check.cut(place.locate(_skill())))
    assert pattern.search(scope), f"{place.name} does not say {pattern.pattern!r}"
    mutated = pattern.sub(" ", scope)
    sharing = [c for c in place.checks if c.cut is check.cut]
    assert [c.label for c in sharing if not c.holds(mutated)] == [check.label]


@pytest.mark.parametrize(
    ("place", "check", "pattern", "example"),
    _REFUSALS,
    ids=[f"{p.name}-{_slug(r.pattern)}" for p, _, r, _ in _REFUSALS],
)
def test_each_old_shape_planted_alone_is_the_only_gap(
    place: _Place, check: _Check, pattern: re.Pattern[str], example: str
) -> None:
    """The old shape added to the real text, which says everything else: only the check that
    refuses it may report it. The example is checked against the pattern first, so a pattern
    that never fires cannot hide behind the phrases the old text also lacked."""
    assert pattern.search(example), f"{example!r} is not the shape {pattern.pattern!r}"
    scope = _plain(check.cut(place.locate(_skill())))
    assert check.holds(scope), f"{place.name}: the real text already fails this check"
    planted = f"{scope} {example}"
    sharing = [c for c in place.checks if c.cut is check.cut]
    assert [c.label for c in sharing if not c.holds(planted)] == [check.label]


def test_the_reader_count_checks_see_their_near_misses() -> None:
    """Fired at the old paragraph, a different number in either statement, a different unit, a
    cap that moved, and the sentence under another heading; the fixed paragraph, and the same
    paragraph filled again, hold."""
    fixed = _fix_c6(_OLD_C6)
    assert _spawns_one_reader_per(4, fixed) and _quotes_the_cap(4, fixed)
    assert not _spawns_one_reader_per(4, _OLD_C6) and not _quotes_the_cap(4, _OLD_C6)
    wrong_per = fixed.replace("per four", "per five")
    assert not _spawns_one_reader_per(4, wrong_per) and _quotes_the_cap(4, wrong_per)
    wrong_cap = fixed.replace("at most four", "at most three")
    assert not _quotes_the_cap(4, wrong_cap) and _spawns_one_reader_per(4, wrong_cap)
    wrong_unit = fixed.replace("promoted paragraphs", "promoted claims")
    assert wrong_unit != fixed and not _spawns_one_reader_per(4, wrong_unit)
    assert not _spawns_one_reader_per(3, fixed) and not _quotes_the_cap(3, fixed)
    in_place = f"### C6 {_EM} Epistemic audit\n\n{_COUNT}\n\n### C7 {_EM} Enforcement check\n\nx\n"
    moved = f"### C6 {_EM} Epistemic audit\n\nx\n\n### C7 {_EM} Enforcement check\n\n{_COUNT}\n"
    assert _spawns_one_reader_per(4, _c6(in_place))
    assert not _spawns_one_reader_per(4, _c6(moved))
    refilled = textwrap.fill(
        fixed, width=33, break_long_words=False, break_on_hyphens=False
    )
    assert _spawns_one_reader_per(4, refilled) and _quotes_the_cap(4, refilled)


def test_the_cap_is_read_from_its_section_and_a_missing_cap_fails_loudly() -> None:
    assert (
        _cap_of("## 2. A fresh reader\n\nIt carries at most three real claims.\n") == 3
    )
    with pytest.raises(AssertionError, match="states no cap"):
        _cap_of("## 2. A fresh reader\n\nIt carries a few claims.\n")
    with pytest.raises(AssertionError, match="caps real claims at 'several'"):
        _cap_of("## 2. A fresh reader\n\nIt carries at most several real claims.\n")
    with pytest.raises(AssertionError, match="no heading"):
        _cap_of("## 3. Another section\n\nat most four real claims\n")
    assert _cap() >= 1


def test_the_shipped_severity_table_keeps_its_three_columns_and_three_rows() -> None:
    """Green before the change and after it: the row adds an item to a cell, never a column or a
    row. The shape check is fired at broken tables below; this one reads the real text."""
    assert _severity_table_keeps_its_shape(_severity(_skill()))


def test_the_severity_checks_see_their_near_misses() -> None:
    """Fired at the old table, the item in the Minor row, in the Blocker row, in the Major row
    but away from overstated confidence, only in prose below the table, and in the Minor row as
    well as in the Major row; the item on either side of overstated confidence holds, and so
    does a gloss with a comma inside its parentheses. The shape check reads the same table: a
    fourth column, a fourth row and a short separator each fail it, and the old table and the
    fixed one pass."""
    fixed = _fix_severity(_OLD_SEVERITY)
    assert _major_names_the_fidelity_defect(fixed)
    before = _swap(
        _OLD_SEVERITY,
        r"self-contradiction, overstated confidence",
        f"self-contradiction, {_ITEM}, overstated confidence",
    )
    assert _major_names_the_fidelity_defect(before)
    commaed = _swap(
        fixed, r"a promoted paragraph that says", "a promoted paragraph, which says"
    )
    assert _major_names_the_fidelity_defect(commaed)
    planted = {
        "absent": _OLD_SEVERITY,
        "in the Minor row": _swap(
            _OLD_SEVERITY, r"a redundant clause", f"a redundant clause, {_ITEM}"
        ),
        "in the Blocker row": _swap(
            _OLD_SEVERITY,
            r"shipped into a rule \(C2\)",
            f"shipped into a rule (C2), {_ITEM}",
        ),
        "in the Major row, away from overstated confidence": _swap(
            _OLD_SEVERITY, r"seam belongs", f"seam belongs, {_ITEM}"
        ),
        "in prose below the table": f"{_OLD_SEVERITY}\nA fidelity defect is Major: {_ITEM}.\n",
        "without its gloss": _swap(
            fixed, r"\(a promoted paragraph[^)]*\)", "(a changed claim)"
        ),
        "also in the Minor row": _swap(
            fixed, r"a redundant clause", f"a redundant clause, {_ITEM}"
        ),
    }
    for name, table in planted.items():
        assert not _major_names_the_fidelity_defect(table), name
    assert _severity_table_keeps_its_shape(_OLD_SEVERITY)
    assert _severity_table_keeps_its_shape(fixed)
    broken = {
        "a fourth column": _swap(fixed, r"\| Action \|", "| Action | Owner |"),
        "a fourth row": f"{fixed}| **Note** | a fidelity row | none |\n",
        "a short separator": _swap(fixed, r"\|---\|---\|---\|", "|---|---|"),
        "a row dropped": _swap(fixed, r"\| \*\*Minor\*\*[^\n]*\n", ""),
    }
    for name, table in broken.items():
        assert not _severity_table_keeps_its_shape(table), name


def test_the_audit_command_check_sees_its_near_misses() -> None:
    """Fired at the old operand in both commands and in one, a block with no command, commands
    with no fence, and a third command; the fixed block holds, and so does the old path named in
    prose, which is no command."""
    fixed = _fix_c1(_OLD_C1)
    assert _audit_commands_take_the_scratch_snapshot(fixed)
    assert fixed.count(_NEW_OPERAND) == _PRINTED_AUDIT_COMMANDS
    third = f"{fixed}\n```bash\npython drain_audit.py {_NEW_OPERAND} HEAD --surface notes\n```\n"
    planted = {
        "the old operand in both commands": fixed.replace(_NEW_OPERAND, _OLD_OPERAND),
        "the old operand in one command": fixed.replace(_NEW_OPERAND, _OLD_OPERAND, 1),
        "the old block": _OLD_C1,
        "no command printed": fixed.replace("drain_audit.py", "audit.py"),
        "commands outside a fence": fixed.replace("```bash\n", "").replace("```\n", ""),
        "a third command": third,
    }
    for name, region in planted.items():
        assert region != fixed, name
        assert not _audit_commands_take_the_scratch_snapshot(region), name
    prose = (
        f"{fixed}\nThe byte copy is {_OLD_OPERAND} and is never the audit's input.\n"
    )
    assert _audit_commands_take_the_scratch_snapshot(prose)
    assert _printed_audit_operands(_OLD_C1)[0][0] == _OLD_OPERAND


def test_a_rewrap_of_the_shipped_paragraphs_passes_every_check() -> None:
    """The checks fold whitespace, so a paragraph filled again at another width is the same text:
    the three paragraphs of the critic that carry the rewritten wording are refilled at a width
    that moves every line break, with no break at a hyphen, and every place still holds."""
    text = _skill()
    for lead in (
        "**Fidelity read.**",
        "Removal verification proves",
        "**If no snapshot exists**",
    ):
        block = _block(text, lead, "SKILL.md")
        refilled = textwrap.fill(
            " ".join(block.split()),
            width=37,
            break_long_words=False,
            break_on_hyphens=False,
        )
        assert refilled != block, lead
        text = text.replace(block, refilled)
    for place in _PLACES:
        assert not _gaps(place.checks, place.locate(text)), place.name


def test_a_missing_heading_row_or_lead_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="no heading"):
        _section("## Other\ntext\n", "### C6", "planted")
    planted = "## A\nfirst\n```bash\n# a shell comment\n```\nafter the fence\n### A.1\ndeeper\n## B\nnext\n"
    section = _section(planted, "## A", "planted")
    assert (
        "after the fence" in section and "deeper" in section and "next" not in section
    )
    with pytest.raises(AssertionError, match="no block starts"):
        _block("text\n\nmore text\n", "lead", "planted")
    with pytest.raises(AssertionError, match="no table row starts"):
        _snapshot_row("| Input | Why |\n|---|---|\n| other | row |")
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-skill.md"))
