"""learning-consolidator commits the buffer before a drain and keeps the copy and the record local.

Phase 5 told the operator to copy the buffer to a snapshot file, to "commit the snapshot
alongside the drain", to cite it by path and to delete it once the drain had merged. A file that
has to come out of the tree before the merge breaks every citation of its path (one change had to
rewrite eight), and the Gate Record section was silent on whether the record is tracked. The rule
is now: before the first removal the operator commits the buffer as it stands, in its own commit;
that commit is the restore point and the input of the landing audit, cited by commit id; the
operator's byte copy and the gate record stay local and are never committed, and the project lists
both in its ignore file. The audit script takes a FILE, so its input is the buffer at the restore
point written to a scratch file, and no text may say the script reads a commit.

Each assertion reads one named file, section or clause, and a missing heading fails loudly. The
checks are functions over a string, so `test_every_check_sees_its_planted_positive` fires them at
the old text and at near-misses before their silence on the real files is trusted, and
`test_a_rewrap_of_the_shipped_text_passes_every_check` shows a re-flowed line is the same text.
Every non-ASCII character in a fixture is built from `chr()`.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "learning-consolidator"
_SKILL = _SKILL_DIR / "SKILL.md"
_REFERENCE = _SKILL_DIR / "references" / "consolidation-actions.md"
_SURFACE: tuple[Path, ...] = (_SKILL, _REFERENCE)

# The skill audit fails a SKILL.md at 500 lines and counts one more than the newline count.
_LINE_CAP = 499
_CALLOUT_LINE_CAP = 7

_EM_DASH = chr(0x2014)
_SECTION_SIGN = chr(0xA7)

_HEADING = re.compile(r"^(#{1,6})\s+\S")

_SKILL_NAME = "learning-consolidator SKILL.md"
_REFERENCE_NAME = "learning-consolidator references/consolidation-actions.md"


# --- slicers over a string -----------------------------------------------------------------


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _relative(path: Path) -> str:
    return path.relative_to(_SKILL_DIR).as_posix()


def _fold(text: str) -> str:
    """The text with blockquote markers dropped and every run of whitespace as one space."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>+ ?", "", text)).strip()


def _view(text: str) -> str:
    """The folded text without bold markers: what every pattern below is matched against."""
    return _fold(text).replace("**", "")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


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


def _callout(skill: str) -> list[str]:
    """The blockquote lines at the top of Phase 5, before its numbered list."""
    section = _section(skill, "### Phase 5", _SKILL_NAME)
    quoted: list[str] = []
    for line in section.split("\n"):
        if line.startswith(">"):
            quoted.append(line)
        elif quoted and line.strip():
            break
    if not quoted:
        raise AssertionError(f"{_SKILL_NAME}: Phase 5 has no blockquote callout")
    return quoted


def _table_row(section: str, lead: str) -> str:
    """The table row that starts with `lead`, or an empty string when there is none."""
    return next((line for line in section.split("\n") if line.startswith(lead)), "")


def _missing(view: str, facts: dict[str, str]) -> list[str]:
    """The names of the facts whose pattern is not found in `view`."""
    return [
        name
        for name, pattern in facts.items()
        if not re.search(pattern, view, re.IGNORECASE)
    ]


# --- what the new text must say ------------------------------------------------------------

_DEFINITION = (
    "the buffer as committed at the restore point, read through a scratch file"
)

_CALLOUT_FACTS: dict[str, str] = {
    "the operator commits the buffer as it stands": (
        r"\bthe operator commits the buffer as it stands\b"
    ),
    "before any removal": r"\bbefore any removal\b",
    "in its own commit": r"\bin its own commit\b",
    "in the operator's own terminal": r"\boperator\b.{0,200}\bown terminal\b",
    "a byte copy that is never committed": r"\bbyte copy\b.{0,80}\bnever committed\b",
    "the ignore file lists the copy and the gate-record folder": (
        r"\bignore file lists it and the gate-record folder\b"
    ),
    "the landing audit takes the buffer at that commit through a scratch file": (
        r"\blanding audit takes\b.{0,160}\bat that commit\b.{0,40}\bscratch file\b"
    ),
    "the commit id is cited in the changelog entry": (
        r"\bcite the commit id in the changelog entry\b"
    ),
    "the link to the Pre-Drain Snapshot section": (
        r"references/consolidation-actions\.md#pre-drain-snapshot-phase-5"
    ),
}

_SNAPSHOT_FACTS: dict[str, str] = {
    "commit the buffer as it stands before the first removal, in its own commit": (
        r"\bcommit the buffer as it stands\b.{0,40}\bbefore the first removal\b"
        r".{0,40}\bown commit\b"
    ),
    "that commit is the restore point": r"\bthat commit is the restore point\b",
    "the changelog entry cites it by commit id": r"\bcites, by commit id\b",
    "the pre-drain snapshot is defined through the restore point": (
        r"\bpre-drain snapshot\b.{0,120}\bis " + re.escape(_DEFINITION)
    ),
    "the audit script takes a file, not a commit": (
        r"\baudit script takes a file, not a commit\b"
    ),
    "the operator writes the buffer at the restore point to a scratch file": (
        r"`git show <commit>:<path>`.{0,40}\bredirected to that file\b"
    ),
    "the scratch file lies outside the buffer's folder": (
        r"\boutside the buffer's folder\b"
    ),
    "all of it is in the operator's own terminal": (
        r"\boperator\b.{0,200}\bown terminal\b"
    ),
    "the byte copy is never committed": r"\bbyte copy\b.{0,60}\bnever committed\b",
    "the byte copy is confirmed byte-identical": r"\bbyte-identical\b",
    "the counts are confirmed with Grep in count mode": (
        r"\bGrep in count mode\b.{0,80}\bsame number of entries\b"
    ),
    "why a snapshot file in the drain was rejected": (
        r"\bbreaks every citation that named its path\b"
    ),
    "that rejection was observed once": r"\bobserved once\b",
    "the byte copy may live in an ignored folder": r"\bmay live in an ignored folder\b",
    "the byte copy must BE ignored and the ignore file lists it and the record folder": (
        r"\bbyte copy is ignored\b.{0,80}"
        r"\bignore file lists it and the gate-record folder\b"
    ),
    "the check says an ignored path exits 0": (
        r"\bgit check-ignore -v <byte-copy-path>.{0,80}\b0 = ignored\b"
    ),
}

_LANDING_FACTS: dict[str, str] = {
    "the audit runs against the buffer at the restore-point commit": (
        r"\brun it against the pre-drain snapshot\b.{0,160}\brestore-point commit\b"
    ),
    "the input is a scratch file": r"\bscratch file\b",
    "the byte copy waits for a clean audit": (
        r"\bdo not delete the byte copy until the audit is clean\b"
    ),
}

_OPERATOR_FACTS: dict[str, str] = {
    "the intro lists the restore-point commit and the byte copy": (
        r"\bthe restore-point commit and the local byte copy \(Phase 5\)"
    ),
    "every commit, copy or read is in the operator's own terminal": (
        r"\bin every project the operator makes each commit, copy or read in their own "
        r"terminal\b"
    ),
}

_OPERATOR_ROW_FACTS: dict[str, str] = {
    "the operator commits the buffer": r"\bcommits the buffer\b",
    "the operator confirms the copy is byte-identical": r"\bbyte-identical\b",
    "the operator writes the scratch file for Step 6": r"\bscratch file for Step 6\b",
    "the session confirms the counts with Grep in count mode": r"\bGrep in count mode\b",
    "the session cites the commit id": r"\bcites the commit id\b",
}

_GATE_FACTS: dict[str, str] = {
    "the record is never committed": r"\bnever committed\b",
    "the project lists its folder in its ignore file": (
        r"\blists its folder\b.{0,40}\.ai/consolidation-gates/.{0,40}\bin its ignore file\b"
    ),
}

# --- what the old text said, as the classes of shape it came in -----------------------------

# slug -> (pattern, what the old text did). Every pattern is found in the old paragraphs below.
_OLD_SHAPES: dict[str, tuple[str, str]] = {
    "commit-the-snapshot-alongside-the-drain": (
        r"\bcommit the snapshot alongside the drain\b",
        "told the operator to commit the snapshot file with the drain",
    ),
    "commits-the-snapshot": (
        r"\bcommits?\s+(?:the\s+)?snapshot\b",
        "named the snapshot, not the buffer, as the thing that is committed",
    ),
    "uncommitted-snapshot": (
        r"\buncommitted\b.{0,40}\bsnapshot\b",
        "called an uncommitted snapshot the defect",
    ),
    "cite-it-by-path": (
        r"\bcite\s+it\s+by\s+path\b",
        "cited the snapshot by a path that is removed before the merge",
    ),
    "delete-it-after-the-merge": (
        r"\bdelete\s+it\s+only\s+after\b.{0,120}\bmerged\b",
        "deleted the snapshot file after the merge",
    ),
    "do-not-delete-the-snapshot": (
        r"\bdo\s+not\s+delete\s+the\s+snapshot\b",
        "kept the snapshot file, not the byte copy, until the audit was clean",
    ),
    "location-is-not-itself-ignored": (
        r"\bnot\s+itself\s+ignored\b",
        "asked the operator to confirm the copy is NOT ignored",
    ),
    "one-is-not-ignored-good": (
        r"\b1\s*=\s*not\s+ignored,\s*good\b",
        "called exit 1 of the ignore check good",
    ),
    "git-add-f": (
        r"\bgit\s+add\s+-f\b",
        "told the operator to force-stage an ignored copy",
    ),
    "can-never-be-committed": (
        r"\bcan\s+never\s+be\s+committed\b",
        "called an ignored folder the reason a snapshot could not be committed",
    ),
    "never-ai-tmp": (
        r"\bnever\s+`\.ai/tmp/`",
        "forbade an ignored folder for the copy",
    ),
    "the-snapshot-path": (
        r"\bsnapshot\s+path\b",
        "named a snapshot path that is now the byte copy's",
    ),
}

# The old paragraphs, verbatim apart from the characters built from chr().
_OLD_CALLOUT = f"""\
> **Snapshot the buffer FIRST** {_EM_DASH} before any deletion the operator copies it to
> `.ai/learnings-pre-drain-<date>.md` in their own terminal and confirms the copy is
> byte-identical (a session never names the buffer on a shell line), and you **commit the
> snapshot alongside the drain**. Step 6's landing audit takes it as input, so an uncommitted
> or gitignored snapshot makes "zero entries deleted without a home" an assertion rather than
> evidence. Never `.ai/tmp/` (gitignored {_EM_DASH} a drain whose snapshot lived there left
> nothing to settle two tallies that disagree). Rationale:
> [{_SECTION_SIGN} Pre-Drain Snapshot](references/consolidation-actions.md#pre-drain-snapshot-phase-5).
"""

_OLD_SNAPSHOT_SECTION = """\
## Pre-Drain Snapshot (Phase 5)

**Do NOT put it in `.ai/tmp/`.** That directory is gitignored, so a snapshot
there can never be committed, never reaches a reviewer, and is routinely swept.

Commit the snapshot alongside the drain, and cite it by path in the changelog entry. Delete it
only after Step 6's audit is clean AND the drain has been merged.

**Confirm the snapshot's location is not itself ignored, with a command, before trusting it:**

```bash
git check-ignore -v <snapshot-path>;  echo "rc=$? (1 = NOT ignored, good)"
```

If the only sensible location *is* ignored, stage it explicitly with `git add -f` and say so in
the report; do not quietly skip it.
"""

_OLD_AUDIT_TAIL = (
    "Anything else is knowledge deleted without a home: **recover it from the snapshot and "
    "promote it before proceeding.** Do not delete the snapshot until the audit is clean.\n"
)

_OLD_OPERATOR_ROWS = (
    "| Snapshot (Phase 5) | copies the buffer to the snapshot path and confirms the copy is "
    "byte-identical | confirms with Grep in count mode that both files hold the same number "
    "of entries, then commits the snapshot with the drain |\n"
)

_OLD_GATE_SECTION = (
    "## Gate Record\n\n"
    "- **When.** Write the record only AFTER the operator's approval of the plan.\n"
    "- **What it gates.** Removals only.\n"
)


def _old_shapes(text: str) -> list[str]:
    """The slugs of the old shapes found in `text`."""
    view = _view(text)
    return [
        slug
        for slug, (pattern, _why) in _OLD_SHAPES.items()
        if re.search(pattern, view, re.IGNORECASE)
    ]


# --- no text says the audit script reads a commit ------------------------------------------

_COMMIT_PATH = "<commit>:<path>"
_READS_A_COMMIT = re.compile(
    r"\b(?:audit(?: script)?|script|drain_audit\.py)\s+(?:can\s+|will\s+)?"
    r"(?:reads?|takes?|accepts?)\s+(?:a\s+|the\s+)?commits?\b",
    re.IGNORECASE,
)


def _claims_the_script_reads_a_commit(text: str) -> list[str]:
    """Sentences that give the landing-audit script a commit where it takes a file.

    `<commit>:<path>` is the operator's `git show` operand that makes the scratch file, so a
    sentence that names it with `git show` is fine; one that hands it to the audit is the claim.
    """
    claims: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", _view(text)):
        lowered = sentence.lower()
        if not re.search(r"\b(?:audit|script|drain_audit\.py)\b", lowered):
            continue
        handed_over = _COMMIT_PATH in sentence and "git show" not in lowered
        if handed_over or _READS_A_COMMIT.search(sentence):
            claims.append(sentence)
    return claims


# --- one check per place the row names; each takes a whole file's text ----------------------


def _callout_gaps(skill: str) -> list[str]:
    return _missing(_view("\n".join(_callout(skill))), _CALLOUT_FACTS)


def _snapshot_gaps(reference: str) -> list[str]:
    section = _section(reference, "## Pre-Drain Snapshot (Phase 5)", _REFERENCE_NAME)
    return _missing(_view(section), _SNAPSHOT_FACTS)


def _landing_gaps(reference: str) -> list[str]:
    section = _section(reference, "## Drain Landing Audit", _REFERENCE_NAME)
    return _missing(_view(section), _LANDING_FACTS)


_RESTORE_ROW = "| Restore point and byte copy (Phase 5) |"
_RECOVERY_ROW = "| Recovery read (C1, no snapshot exists) |"


def _operator_gaps(reference: str) -> list[str]:
    section = _section(reference, "## Operator Steps", _REFERENCE_NAME)
    gaps = _missing(_view(section), _OPERATOR_FACTS)
    row = _table_row(section, _RESTORE_ROW)
    if not row:
        gaps.append(f"no table row starting {_RESTORE_ROW!r}")
    else:
        if row.count("|") != 4:
            gaps.append(f"the restore-point row is not three cells: {row}")
        gaps += [f"row: {name}" for name in _missing(_view(row), _OPERATOR_ROW_FACTS)]
    recovery = _table_row(section, _RECOVERY_ROW)
    if not recovery:
        gaps.append(f"no table row starting {_RECOVERY_ROW!r}")
    elif "NOT the byte copy's path" not in recovery:
        gaps.append(
            "the recovery read row does not point away from the byte copy's path"
        )
    return gaps


def _gate_gaps(reference: str) -> list[str]:
    section = _section(reference, "## Gate Record", _REFERENCE_NAME)
    return _missing(_view(section), _GATE_FACTS)


def _old_text_problems(text: str) -> list[str]:
    return [f"still says: {slug}" for slug in _old_shapes(text)] + [
        f"claims the audit reads a commit: {claim}"
        for claim in _claims_the_script_reads_a_commit(text)
    ]


def _reported(name: str, check: Callable[[str], list[str]], text: str) -> list[str]:
    """The problems of one check, a missing heading or row included, each led by `name`."""
    try:
        return [f"{name}: {problem}" for problem in check(text)]
    except AssertionError as error:
        return [f"{name}: {error}"]


def _problems(skill: str, reference: str) -> list[str]:
    """Every check over one SKILL.md text and one reference text, as a flat list."""
    return [
        *_reported("callout", _callout_gaps, skill),
        *_reported("snapshot section", _snapshot_gaps, reference),
        *_reported("landing audit", _landing_gaps, reference),
        *_reported("operator steps", _operator_gaps, reference),
        *_reported("gate record", _gate_gaps, reference),
        *_reported("SKILL.md", _old_text_problems, skill),
        *_reported("reference", _old_text_problems, reference),
    ]


# --- the tests -----------------------------------------------------------------------------


def test_the_scan_surface_is_the_two_files_the_row_names() -> None:
    assert len(_SURFACE) == 2
    assert len({path.resolve() for path in _SURFACE}) == 2, (
        "the two scopes must be distinct"
    )
    for path in _SURFACE:
        assert path.is_file(), f"{path.name} is not a file"
        assert _text(path).strip(), f"{path.name} is empty"
    _section(_text(_SKILL), "### Phase 5", _SKILL_NAME)
    for heading in (
        "## Pre-Drain Snapshot (Phase 5)",
        "## Drain Landing Audit",
        "## Operator Steps",
        "## Gate Record",
    ):
        _section(_text(_REFERENCE), heading, _REFERENCE_NAME)


def test_phase_5_callout_commits_the_buffer_and_keeps_the_copy_local() -> None:
    gaps = _callout_gaps(_text(_SKILL))
    assert not gaps, f"{_SKILL_NAME}, Phase 5 callout, does not say: {gaps}"


def test_the_callout_and_skill_md_stay_within_their_line_caps() -> None:
    lines = _text(_SKILL).count("\n")
    assert lines <= _LINE_CAP, (
        f"SKILL.md has {lines} lines; the audit cap leaves {_LINE_CAP}"
    )
    callout = len(_callout(_text(_SKILL)))
    assert callout <= _CALLOUT_LINE_CAP, (
        f"the Phase 5 callout is {callout} lines; at most {_CALLOUT_LINE_CAP}"
    )


@pytest.mark.parametrize("slug", list(_OLD_SHAPES))
def test_the_old_snapshot_instruction_is_gone(slug: str) -> None:
    pattern, why = _OLD_SHAPES[slug]
    still = [
        _relative(path)
        for path in _SURFACE
        if re.search(pattern, _view(_text(path)), re.IGNORECASE)
    ]
    assert not still, f"{still} still carry the old shape that {why}"


def test_the_pre_drain_snapshot_section_states_the_restore_point_rule() -> None:
    gaps = _snapshot_gaps(_text(_REFERENCE))
    assert not gaps, f"{_REFERENCE_NAME}, Pre-Drain Snapshot, does not say: {gaps}"


def test_the_pre_drain_snapshot_term_is_defined_once() -> None:
    defined = {
        _relative(path): _view(_text(path)).count(_DEFINITION) for path in _SURFACE
    }
    assert sum(defined.values()) == 1, (
        f"the term must be defined exactly once, as {_DEFINITION!r}: {defined}"
    )
    assert defined[_relative(_REFERENCE)] == 1, (
        "the one definition belongs in the reference"
    )


def test_the_landing_audit_is_given_the_buffer_at_the_restore_point() -> None:
    gaps = _landing_gaps(_text(_REFERENCE))
    assert not gaps, f"{_REFERENCE_NAME}, Drain Landing Audit, does not say: {gaps}"


def test_operator_steps_name_the_restore_point_and_the_byte_copy() -> None:
    gaps = _operator_gaps(_text(_REFERENCE))
    assert not gaps, f"{_REFERENCE_NAME}, Operator Steps, does not say: {gaps}"


def test_the_gate_record_is_local_and_never_committed() -> None:
    gaps = _gate_gaps(_text(_REFERENCE))
    assert not gaps, f"{_REFERENCE_NAME}, Gate Record, does not say: {gaps}"


def test_no_text_says_the_audit_script_reads_a_commit() -> None:
    claims = {
        _relative(path): found
        for path in _SURFACE
        if (found := _claims_the_script_reads_a_commit(_text(path)))
    }
    assert not claims, f"the audit script takes a file, not a commit: {claims}"


# --- the instruments -----------------------------------------------------------------------


def _mutated(text: str, old: str, new: str) -> str:
    """`text` with `old` replaced by `new`; an `old` that is not there fails loudly."""
    assert old in text, f"the mutation target is not in the text: {old!r}"
    return text.replace(old, new, 1)


def _rewrap(text: str, width: int) -> str:
    """Every prose paragraph re-flowed to `width`; headings, table rows and fenced blocks are
    kept, and a blockquote keeps its marker."""
    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lead = block.lstrip()
        if lead.startswith(("#", "|", "```")) or "```" in block:
            blocks.append(block)
            continue
        quote = "> " if lead.startswith(">") else ""
        lines = textwrap.wrap(
            _fold(block), width=width, break_long_words=False, break_on_hyphens=False
        )
        blocks.append("\n".join(quote + line for line in lines))
    return "\n\n".join(blocks)


def test_every_check_sees_its_planted_positive() -> None:
    """A guard never shown to fail has not been shown to work."""
    # The old paragraphs hold every old shape, so each pattern can see its target.
    old = "\n".join(
        (_OLD_CALLOUT, _OLD_SNAPSHOT_SECTION, _OLD_AUDIT_TAIL, _OLD_OPERATOR_ROWS)
    )
    unseen = sorted(set(_OLD_SHAPES) - set(_old_shapes(old)))
    assert not unseen, f"shapes the old fixtures do not show: {unseen}"

    # The old paragraphs fail the presence checks.
    assert len(_missing(_view(_OLD_CALLOUT), _CALLOUT_FACTS)) >= 6
    assert len(_missing(_view(_OLD_SNAPSHOT_SECTION), _SNAPSHOT_FACTS)) >= 10
    assert _missing(_view(_OLD_GATE_SECTION), _GATE_FACTS) == list(_GATE_FACTS)
    assert _missing(_view(_OLD_AUDIT_TAIL), _LANDING_FACTS)
    assert _missing(_view(_OLD_OPERATOR_ROWS), _OPERATOR_ROW_FACTS)
    assert _reported("gate record", _gate_gaps, _OLD_GATE_SECTION)

    # A heading or a row that is gone is reported, never an empty pass.
    assert any("no heading" in p for p in _reported("callout", _callout_gaps, "text\n"))
    assert any(
        "no heading" in p for p in _reported("gate", _gate_gaps, "## Elsewhere\n")
    )
    assert any(
        "no table row" in p
        for p in _reported(
            "operator", _operator_gaps, "## Operator Steps\n\n| a | b | c |\n"
        )
    )

    # Near-misses that carry the new rule's words are not old shapes.
    for near in (
        "A snapshot file committed with the drain has to be removed before the merge.",
        "The operator commits the buffer as it stands, in its own commit.",
        "The changelog entry cites, by commit id, the restore point.",
        "Do not delete the byte copy until the audit is clean.",
        "Delete the scratch file when the drain has merged.",
        "(0 = ignored, good; 1 = NOT ignored, list it first)",
        "The byte copy may live in an ignored folder such as `.ai/tmp/`.",
        "Step 6's landing audit takes the buffer at the restore point.",
        "`git add -- <paths>` stages exactly the files named.",
    ):
        assert _old_shapes(near) == [], f"flagged a near-miss: {near!r}"

    # The claim that the script reads a commit: the item as filed, and plain statements of it.
    filed = (
        "Pass the buffer at that commit, written to a scratch file, or let the audit script "
        f"read `{_COMMIT_PATH}`."
    )
    assert _claims_the_script_reads_a_commit(filed)
    assert _claims_the_script_reads_a_commit(
        "The audit script takes a commit and reads it."
    )
    assert _claims_the_script_reads_a_commit(
        "drain_audit.py accepts the commit directly."
    )
    for fine in (
        "The audit script takes a file, not a commit, so the scratch file is what it is given.",
        f"The operator writes the buffer to a scratch file (`git show {_COMMIT_PATH}` "
        "redirected to it), and the audit reads that file.",
        "Step 6's landing audit takes the buffer at that commit, written to a scratch file.",
    ):
        assert _claims_the_script_reads_a_commit(fine) == [], fine


def test_each_regression_of_the_shipped_text_is_caught() -> None:
    """One mutation round over the real text: each regression adds the problem it should."""
    skill, reference = _text(_SKILL), _text(_REFERENCE)
    baseline = _problems(skill, reference)
    cases = (
        (
            _mutated(skill, "commits the buffer", "copies the buffer"),
            reference,
            "callout: the operator commits the buffer as it stands",
        ),
        (
            skill,
            reference + "\nCommit the snapshot alongside the drain.\n",
            "reference: still says: commit-the-snapshot-alongside-the-drain",
        ),
        (
            skill,
            _mutated(reference, "never committed: it is read", "committed: it is read"),
            "gate record: the record is never committed",
        ),
        (
            skill,
            reference + f"\nOr let the audit script read `{_COMMIT_PATH}`.\n",
            "reference: claims the audit reads a commit",
        ),
    )
    for mutated_skill, mutated_reference, expected in cases:
        added = [
            problem
            for problem in _problems(mutated_skill, mutated_reference)
            if problem not in baseline
        ]
        assert any(problem.startswith(expected) for problem in added), (
            expected,
            added[:4],
        )


def test_the_shipped_text_has_no_problem_in_any_check() -> None:
    problems = _problems(_text(_SKILL), _text(_REFERENCE))
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("width", [48, 72, 130])
def test_a_rewrap_of_the_shipped_text_passes_every_check(width: int) -> None:
    skill, reference = _text(_SKILL), _text(_REFERENCE)
    baseline = _problems(skill, reference)
    assert not baseline, "the shipped text must pass before a re-wrap can mean anything"
    assert _rewrap(skill, width) != skill, (
        "the re-wrap changed nothing, so it proves nothing"
    )
    assert _problems(_rewrap(skill, width), _rewrap(reference, width)) == []
