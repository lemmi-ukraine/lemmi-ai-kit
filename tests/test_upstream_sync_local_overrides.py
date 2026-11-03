"""A skill edited here whose upstream is its origin carries a `Local override` note in the sync record.

The next refresh from upstream rewrites a skill unless its row says what was changed on this side,
and a note that has been replaced loses the overrides it listed. Of the skills edited here, 23
descend from upstream, so each of those rows needs a note, and 4 of the rows that already carried
one are held to keep it whole as the start of the longer note. The other 4 are authored here
(`kit-origin`), which is why they need no override note: upstream's later edits to them are
contributions to review.

The record is parsed, never searched as text, and the sets below are checked against it, not against
each other: an edited skill with no row, a row that is not upstream's, or a skill in both sets fails.
A note carries one phrase per edit it records, in its own words; where a note was found to describe
an edit wrongly, the wrong wording is retired by name, so it cannot come back.

Two notes were found to leave edits out, and a refresh re-applies only what its note names. Each
file those skills' later edits touched, and each section of the skill file they changed, now has a
phrase in its row below, and the two notes as they read before are kept as excerpts, so the check is
shown to report every phrase they lacked.

Two more notes left out edits that had already landed. initiative-cleanup's named neither the
evidence command's fixed-string search, its exit 2 when git cannot search, the help text that says
both, nor the Related line; flow-mapping's said the validator gained a quantifiers check but not that
the check is report-only by default, so a re-apply from the note could bring back a blocking default,
and it named neither the registers folder of the documented command nor the new probe fixtures. Both
notes as they read then are kept as excerpts as well, and the check reports the phrases each lacked.

initiative-cleanup was edited twice more after both of its excerpts were taken. The phrases of those
later edits sit in a table of their own: the row's note must carry them too, while the checks fired at
the excerpts count only the phrases of the excerpts' own time, so each still reports what it lacked then.

post-task-review was edited again after its one excerpt was taken (a row on SQL handed to someone else, and two
checks of the prompt sweep): its 2 later phrases sit in the same table, so the excerpt still reports the 7
phrases it lacked then.

THE SURFACE, in numbers the tests assert: 23 edited upstream-origin rows, 4 earlier notes kept whole,
4 kit-origin rows left alone, no name in both sets, 1 retired wording, 2 incomplete notes reported
as they read, 7 missing phrases each, 2 later incomplete notes reported as they read, 5 missing
phrases each, and 2 rows edited again after their excerpts, their 5 later phrases checked apart.
"""

import re
import tomllib
from pathlib import Path
from typing import cast

import pytest

_RECORD = Path(__file__).resolve().parents[1] / "docs" / "upstream-sync.toml"
_ORIGIN = "upstream-origin"
_OVERRIDE = re.compile(r"Local overrides?\b")
_REAPPLY = "re-apply on the next sync"

# Each edited skill, and the phrases its note must carry: the edits it records, in the note's words.
_EDITED: dict[str, tuple[str, ...]] = {
    "ai-changelog": (
        "carries a `- **Drained:** N entries` line",
        "the grouping example shows the line",
        "from the oldest marked one on",
    ),
    "ai-docs-lookup": (
        "a model's summary of the page",
        "the pin is read wherever the project pins it",
    ),
    "analyze-logs": (
        "the task prefixes from the project's own task conventions",
        "a stated exception (Step 5 and Step 4b)",
        "a placeholder read from the Step 1a Correlation id row",
        "the quotes dropped for an id in message text",
    ),
    "branch-diff-review": (
        "content hashes of the dirty set",
        "labels its Gates example as one repository's",
    ),
    "consolidation-critic": (
        "the same --surface values as the consolidator's Phase 5 audit",
        "C6 gains a fidelity read",
        "a fresh reader, not the promoter, carries the read",
        "the Output Format gains a Fidelity read line",
    ),
    "flow-mapping": (
        "--registers",
        "report-only in the default run",
        "blocks only through --check quantifiers",
        "--list-residue --registers tasks",
        "probe-quantifiers.md",
        "seam_probe_registers/",
    ),
    "initiative-cleanup": (
        "--code-suffix",
        "the gates block and Steps 4a and 5.5a pass the verified ref",
        "Steps 4b and 7 get the suffix-free command",
        "the shared spec folders are taken from the spec root on disk",
        "searches the symbol as a fixed string",
        "exits 2 when the ref does not resolve or git grep fails",
        "the script's help text says both",
        "the 5.5a gates comment names exit 2",
        "the Related line names only the learnings routing",
    ),
    "initiative-planner": (
        "project opt-out",
        "states its own cap on simultaneous agents",
        "counts every live session on the account toward it",
        "no default cap",
        "derivation 3 names where the project opt-out is read",
        "chokepoint search takes <source-roots>",
    ),
    "learning-consolidator": (
        "count only CONSOLIDATION entries whose Drained count is above 0",
        "Phase 7a writes the line",
        "a home the project's own AGENTS.md names",
        "calls the skill's homes a sample",
        "a repeatable --surface glob",
        "any other pre-drain snapshot as a landing site",
        "Phase 5 has the operator commit the buffer in its own commit before the first removal",
    ),
    "parallel-session-safety": (
        "12g to 12k",
        "section 2 (the content hash decides which candidate paths changed, 12g)",
        "section 3 (create a path believed new only if absent, 12k)",
        "section 3b (hand a file back by reverting your own lines, 12j)",
        "section 6 (hash the dirty set before and after a suite run, 12g)",
        "section 12 (the verify-and-stage rule and its corollary name the recorded hashes, 12a)",
        "12b gains a sentence that a peer's staged file stops staging, not every edit (12i)",
        "its opening line no longer counts five failure modes",
    ),
    "plan-critic": (
        "Step 2.7",
        "Project-Specific Context section is one instruction",
        "examples that named one stack are neutral",
        "layering line holds only where the project requires it",
        "the DI-overrides line is gone",
        "applies to any implementation plan",
        "a two-run cap",
        "severity table in finding-format.md",
        "the plan lets the project's own testing conventions come first",
        "asks for each fix as exact replacement text",
        "diff the document against its version before the first fix pass",
    ),
    "post-task-review": (
        "references/fix-rounds.md",
        "names the config's own default",
        "a positive must resemble the target, with a matching paragraph in fixture-design.md",
        "the project's own code-to-docs matrix before the sample",
        "derives the id prefixes from the retired file",
        "review-checklist.md gains an untracked-sweep row",
        "a row for the drafted changelog line",
        "reading-gate-output.md a trap row for the untracked sweep",
    ),
    "pr-comment-resolver": (
        "a session may use branch-switch after its pre-switch backup",
    ),
    "pr-review-concise": (
        "Step 7 labels its gate examples as one repository's",
        "the bullet on a bare timeout decorator is deleted from Step 7",
    ),
    "product-brief": ("the architecture and flow documents named in AGENTS.md",),
    "session-retrospective": (
        "the closing nudge dates the last drain",
        "files .NET build output",
        "error-class counts move against older reports",
        "the output-schema reference's category table",
        "redacts a GitHub token by its shape",
    ),
    "skill-creator": (
        "the kit's own recommendation instead of one repository's decision",
        "name commit-message as the only user-only example",
        "branch mutation only without a backup gate",
    ),
    "skill-reviewer": (
        "the kit's own recommendation or convention instead of one repository's decision",
        "name commit-message as the only user-only example",
        "branch mutation only without a backup gate",
    ),
    "spec-driven-dev": (
        "three documents (spec, tasks, test plan)",
        "a Large one four (requirements, design, tasks, verification plan)",
    ),
    "stacked-pr-planner": (
        "never ordered by ancestry",
        "names Alembic and EF Core",
        "the full CI job",
        "one label line",
    ),
    "task-learnings": (
        "close of every task",
        "a language-neutral entry",
        "the buffer-pressure check dates the last drain",
    ),
    "test-conventions": ("the description's Use-when sentence says Python test files",),
    "vertical-slice": ("scoped to a Python repository laid out by feature",),
}
# Wording a note must not carry: it described an edit more broadly than the edit went (every step
# of the skill passed the ref and ran the suffix-free sweep, where each got one of the two).
_RETIRED_WORDING: dict[str, tuple[str, ...]] = {
    "initiative-cleanup": ("pass the ref and run a suffix-free sweep",),
}
# Skills edited here that this repository authored: no override note is owed.
_AUTHORED_HERE: tuple[str, ...] = (
    "agent-delegate",
    "kit-setup",
    "orchestrate",
    "test-planner",
)

# The notes four rows carried before: each stays, whole, as the start of the note that replaces it.
_KEPT: dict[str, str] = {
    "flow-mapping": (
        "Carried from the last pre-migration skill revision with portable tools and synthetic "
        "fixtures; the historical source path still resolves at this base. Project-specific "
        "provenance was replaced by executable fixture evidence. Local overrides, 2026-10-30, "
        "to re-apply on the next sync: validate_register.py accepts a citation tracked "
        "relative to the project root or from the repository top; generate_flow_projections.py "
        "--certify prints a NOT CHECKED line; references/register-and-validator-pitfalls.md "
        "and its one SKILL.md pointer line."
    ),
    "plan-critic": (
        "Local override, 2026-10-30: Dimension 7 (quantified claims) in "
        "references/review-dimensions.md plus one SKILL.md list line. Re-apply on the next sync."
    ),
    "post-task-review": (
        "Local overrides, to re-apply on the next sync: 2026-10-29, probe_checker.py reads a "
        "bare-integer checker as its count and takes --script; 2026-10-30, "
        "references/claim-boundaries.md gains a section of four shorter cases."
    ),
    "stacked-pr-planner": (
        "Local override, 2026-10-30: one Step 2 paragraph on a journal branch as a deletion "
        "event. Re-apply on the next sync."
    ),
}

# Two notes as they read while they left edits out: the later edits to the skill file and to the
# references are the phrases they lacked. Each is reported with its 7 missing phrases, by the
# same check that passes the notes as they read now.
_OLD_NOTES: dict[str, str] = {
    "post-task-review": (
        "Local overrides, to re-apply on the next sync: 2026-10-29, probe_checker.py reads a "
        "bare-integer checker as its count and takes --script; 2026-10-30, "
        "references/claim-boundaries.md gains a section of four shorter cases. Further local "
        "overrides, 2026-10-30, to re-apply on the next sync: the review runs at every "
        "completion event (description, activation list, and the phase-gate sentence saying "
        "which run counts); Step 0 counts untracked files with git grep --untracked; "
        "reading-gate-output.md compares blob ids in two forms; the probe item (j) text and "
        "fixture-design.md follow the probe; new references/fix-rounds.md; Step 6 and the "
        "checklist name the project's lint command; doc-impact-matrix.md is a labelled sample; "
        "Step 8's other-writer clause covers the learnings entry."
    ),
    "parallel-session-safety": (
        "Local override, 2026-10-30: the append-only ledgers include improvement-hypotheses.md "
        "for appends, and a project or plan that bars workers from them names one writer; "
        "references/shared-index-protocol.md gains 12g to 12k (hash the dirty set, a merge dry "
        "run, editing a held file, handing a file back, the create collision), 12a and 12e are "
        "extended, and the SKILL.md pointer lists every subsection. Re-apply on the next sync."
    ),
}
_OLD_NOTE_MISSING = 7

# Two notes as they read after the edits they lacked had landed: the phrases each lacked are the 5 it
# gained last, and the check reports those and nothing else.
_LATE_NOTES: dict[str, str] = {
    "flow-mapping": (
        _KEPT["flow-mapping"]
        + " Further local overrides, 2026-10-30, to re-apply on the next "
        "sync: the close runs post-task-review at every completion event of mapping work; "
        "find_absent_cross_flow_seams.py takes --registers and exits 1 while a candidate has no "
        "disposition bullet; validate_flow_map.py gains a quantifiers check; section B and the "
        "self-challenge state the universal-word rule; section D and the template name the "
        "ownership marker."
    ),
    "initiative-cleanup": (
        "Local override, 2026-10-30: scripts/audit_cleanup_targets.py refs opens every "
        "non-binary file, and evidence takes --ref (default HEAD) and a repeatable "
        "--code-suffix, answering NO VERDICT when its only hits are in uncounted file types; "
        "the gates block and Steps 4a and 5.5a pass the verified ref, Steps 4b and 7 get the "
        "suffix-free command, and the shared spec folders are taken from the spec root on disk; "
        "new references/retirement-sweep.md, pointed at from Step 4b. Re-apply on the next sync."
    ),
}
_LATE_NOTE_MISSING = 5

# The phrases of an edit made after a row's excerpts above were taken. The row's note must carry
# them as well; the checks fired at the excerpts leave them out, since no excerpt is from their time.
_LATER_EDITS: dict[str, tuple[str, ...]] = {
    "initiative-cleanup": (
        "no file a session puts in `.ai/tmp/` has history",
        "the sweep table never sweeps the folder's own `.gitignore`",
        "the sweep table's hand-offs row never sweeps the folder's own `.gitignore` either",
    ),
    "post-task-review": (
        "a syntax-only check of SQL that another person will run is syntax-clean, not validated",
        "Step 7c-extra gains a one-line item 4",
    ),
}


def _rows(text: str) -> dict[str, dict[str, object]]:
    """The skill rows of a record, by name. A record with no skill table fails loudly."""
    data = cast(dict[str, object], tomllib.loads(text))
    table = data.get("skills")
    if not isinstance(table, list) or not table:
        raise AssertionError("the record has no [[skills]] table")
    return {str(row["name"]): row for row in cast(list[dict[str, object]], table)}


def _problems(
    rows: dict[str, dict[str, object]],
    name: str,
    phrases: tuple[str, ...],
    kept: str | None,
    retired: tuple[str, ...] = (),
) -> list[str]:
    """What is wrong with the row of an edited upstream-origin skill; empty is a pass."""
    row = rows.get(name)
    if row is None:
        return ["no row"]
    problems: list[str] = []
    if row.get("direction") != _ORIGIN:
        problems.append(f"direction is {row.get('direction')!r}, not {_ORIGIN!r}")
    note = row.get("note")
    note = note if isinstance(note, str) else ""
    if not _OVERRIDE.search(note):
        problems.append("the note does not say Local override")
    problems += [f"the note does not carry {p!r}" for p in phrases if p not in note]
    problems += [f"the note still carries {p!r}" for p in retired if p in note]
    if _REAPPLY not in note.lower():
        problems.append("the note does not say to re-apply on the next sync")
    if kept is not None and not note.startswith(kept):
        problems.append("the earlier note is not kept whole at the start")
    return problems


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_EDITED) == 23, f"{len(_EDITED)} edited skills, not the 23 stated"
    assert len(_KEPT) == 4 and set(_KEPT) <= set(_EDITED)
    assert len(_AUTHORED_HERE) == 4
    assert len(_RETIRED_WORDING) == 1 and set(_RETIRED_WORDING) <= set(_EDITED)
    assert len(_OLD_NOTES) == 2 and set(_OLD_NOTES) <= set(_EDITED)
    assert len(_LATE_NOTES) == 2 and set(_LATE_NOTES) <= set(_EDITED)
    assert len(_LATER_EDITS) == 2 and set(_LATER_EDITS) <= set(_LATE_NOTES) | set(
        _OLD_NOTES
    )
    assert sum(len(phrases) for phrases in _LATER_EDITS.values()) == 5
    assert not set(_EDITED) & set(_AUTHORED_HERE), "a skill is in both sets"
    rows = _rows(_RECORD.read_text(encoding="utf-8"))
    unknown = [n for n in (*_EDITED, *_AUTHORED_HERE) if n not in rows]
    assert not unknown, f"no row in the record for {unknown}"


@pytest.mark.parametrize("name", sorted(_EDITED))
def test_an_edited_upstream_origin_skill_carries_an_override_note(name: str) -> None:
    rows = _rows(_RECORD.read_text(encoding="utf-8"))
    phrases = _EDITED[name] + _LATER_EDITS.get(name, ())
    problems = _problems(
        rows, name, phrases, _KEPT.get(name), _RETIRED_WORDING.get(name, ())
    )
    assert not problems, f"{name}: {problems}"


@pytest.mark.parametrize("name", _AUTHORED_HERE)
def test_a_skill_authored_here_is_not_given_an_upstream_override_note(
    name: str,
) -> None:
    """Kept apart on purpose: upstream's copy descends from these, so the record says so and a
    note that tells the next sync to re-apply an override would send the edit the wrong way."""
    rows = _rows(_RECORD.read_text(encoding="utf-8"))
    assert rows[name]["direction"] == "kit-origin", (
        f"{name} is no longer authored here: it now needs an override note and a place in _EDITED"
    )


def test_the_checks_see_planted_rows() -> None:
    """A guard never shown to fail has not been shown to work: each defect is planted in a row."""
    good = (
        '[[skills]]\nname = "x"\nupstream = "x"\ndirection = "upstream-origin"\n'
        'note = "Earlier. Local override, 2026-01-01: a thing. Re-apply on the next sync."\n'
    )
    assert _problems(_rows(good), "x", ("a thing",), "Earlier.") == []
    no_note = '[[skills]]\nname = "x"\nupstream = "x"\ndirection = "upstream-origin"\n'
    assert "the note does not say Local override" in _problems(
        _rows(no_note), "x", ("a",), None
    )
    replaced = good.replace("Earlier. ", "")
    assert _problems(_rows(replaced), "x", ("a thing",), "Earlier.") == [
        "the earlier note is not kept whole at the start"
    ]
    kit = good.replace("upstream-origin", "kit-origin")
    assert any("direction" in p for p in _problems(_rows(kit), "x", ("a thing",), None))
    no_phrase = good.replace("a thing", "another thing")
    assert any(
        "carry" in p for p in _problems(_rows(no_phrase), "x", ("a thing",), None)
    )
    one_of_two = _problems(_rows(good), "x", ("a thing", "a second thing"), None)
    assert one_of_two == ["the note does not carry 'a second thing'"]
    assert _problems(_rows(good), "x", ("a thing",), None, ("a thing",)) == [
        "the note still carries 'a thing'"
    ]
    assert _problems(_rows(good), "x", ("a thing",), None, ("another thing",)) == []
    no_reapply = good.replace(" Re-apply on the next sync.", "")
    assert any(
        "re-apply" in p for p in _problems(_rows(no_reapply), "x", ("a thing",), None)
    )
    assert _problems(_rows(good), "y", ("a thing",), None) == ["no row"]
    with pytest.raises(AssertionError, match="no .*skills"):
        _rows("title = 'no rows'\n")


def test_the_old_initiative_cleanup_note_is_reported() -> None:
    """The note as it read before it was corrected said every step passed the ref and ran the
    suffix-free sweep, and named neither where each one goes nor where the shared spec folders are
    read from: the three clauses are missing, so are the phrases the note gained after them, and the
    retired wording is there."""
    old = (
        "Local override, 2026-10-30: scripts/audit_cleanup_targets.py refs opens every "
        "non-binary file, and evidence takes --ref (default HEAD) and a repeatable "
        "--code-suffix, answering NO VERDICT when its only hits are in uncounted file types; "
        "the gates, Steps 4a, 4b, 5.5a and the Step 7 template pass the ref and run a "
        "suffix-free sweep; new references/retirement-sweep.md, pointed at from Step 4b. "
        "Re-apply on the next sync."
    )
    row = (
        '[[skills]]\nname = "initiative-cleanup"\nupstream = "initiative-cleanup"\n'
        f'direction = "upstream-origin"\nnote = "{old}"\n'
    )
    problems = _problems(
        _rows(row),
        "initiative-cleanup",
        _EDITED["initiative-cleanup"],
        None,
        _RETIRED_WORDING["initiative-cleanup"],
    )
    assert len(problems) == 4 + _LATE_NOTE_MISSING, problems
    assert sum("does not carry" in p for p in problems) == 3 + _LATE_NOTE_MISSING, (
        problems
    )
    assert sum("still carries" in p for p in problems) == 1, problems


@pytest.mark.parametrize("name", sorted(_OLD_NOTES))
def test_a_note_that_left_edits_out_is_reported_phrase_by_phrase(name: str) -> None:
    """Fired at each note as it read before, the check reports the 7 phrases it lacked and nothing
    else: the one phrase it already carried passes, it still says Local override and re-apply, and
    where the row keeps an earlier note whole, the excerpt starts with it."""
    old = _OLD_NOTES[name]
    row = (
        f'[[skills]]\nname = "{name}"\nupstream = "{name}"\n'
        f'direction = "upstream-origin"\nnote = "{old}"\n'
    )
    problems = _problems(_rows(row), name, _EDITED[name], _KEPT.get(name))
    assert len(problems) == _OLD_NOTE_MISSING, problems
    assert all("does not carry" in p for p in problems), problems
    carried = [p for p in _EDITED[name] if p in old]
    assert len(carried) == 1, f"the old note carries {carried}, expected one phrase"


@pytest.mark.parametrize("name", sorted(_LATE_NOTES))
def test_a_note_completed_later_is_reported_for_the_phrases_it_gained(
    name: str,
) -> None:
    """Fired at each note as it read before it was completed, the check reports the 5 phrases the
    note gained last and nothing else: it already said Local override and re-apply, every phrase it
    carried passes, and where the row keeps an earlier note whole, the excerpt starts with it."""
    late = _LATE_NOTES[name]
    row = (
        f'[[skills]]\nname = "{name}"\nupstream = "{name}"\n'
        f'direction = "upstream-origin"\nnote = "{late}"\n'
    )
    problems = _problems(_rows(row), name, _EDITED[name], _KEPT.get(name))
    assert len(problems) == _LATE_NOTE_MISSING, problems
    assert all("does not carry" in p for p in problems), problems
    lacked = [p for p in _EDITED[name] if p not in late]
    assert lacked == list(_EDITED[name][-_LATE_NOTE_MISSING:]), (
        f"the note lacked {lacked}, not the {_LATE_NOTE_MISSING} phrases it gained last"
    )
