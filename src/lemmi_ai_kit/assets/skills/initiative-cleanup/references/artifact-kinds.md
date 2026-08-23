# The artifact-kind axis — Step 3b detail

Read this when running Step 3b. SKILL.md carries the kind table and the commands; this file carries
the reasoning, the two sub-gates in full, and the measured cases behind them.

## Why a second axis was needed at all

The skill shipped with **one** question: *is the work this file describes implemented?* (Step 4a).
That question is right for a spec and **structurally unanswerable** for session scaffolding — a
dispatch brief describes no code, so no symbol exists to prove, so 4a can never be satisfied, so
every brief is permanently undeletable.

Measured on `.specs/feedback-relevance-and-realism` at HEAD `c88eefa7` (2026-08-19): **51 briefs +
85 capture files = 136 of 157 tracked files** sat outside the only gate the skill had. The run
passed every gate it ran and retired nothing. Full incident, including the two instrument
blindnesses that let it read as success: [self-review-gate.md](self-review-gate.md).

The rule was right. The axis was missing.

## Disposition = kind ∧ life-ending condition

**A kind is never an authorisation.** This is the part that fails silently, because the naive
taxonomy reads perfectly well on its own: *"measurement scripts never needed to be in git — archive
them."* Applied to that initiative it would have moved **26 instruments, every one load-bearing.**

| Instrument | Why it is not spent | Evidence |
|---|---|---|
| `enumerate.py`, `contested.py` | Invoked by repo-root-relative path from a brief headed *"DO NOT RUN THIS YET … scheduled ~2 weeks after the prompt upload"* | the brief's own header |
| `dg1_classification_baseline.py` | Named `Instrument`, invoked under *"How to re-read this after deploy"*. The deploy has not happened | the measurement doc's "how to re-read" section |
| 8 × `measurement/*.py` | A blanket *"every script behind the numbers above, rerunnable from the repo root"* — a promise that is **repo-root-relative**, and an off-repo move falsifies it | a findings doc's blanket rerunnability promise |
| `apply_fixes.py`, `apply_edits.py` | An **open, unresolved** sequencing question: *"The §5 edit must be sequenced against those"* | an open spec's sequencing note |
| `apply_p4_final.py` | *"Replay of the shipped state"* — for an upload that has not shipped | the post-upload verification doc |
| `apply_unblock_fixes.py` | Kept explicitly as a **rollback point** | the change log |

Their kind said *measurement*. Their condition said *pending*. **Pending wins**, and a taxonomy that
cannot express that is a licence to delete.

The same trap in the other direction: **rollback anchors under an un-shipped change are the entire
revert path.** Where `git ls-files <dir> | wc -l` → **0** the tree is untracked
deployment artifact — so byte captures under a capture directory are the *only* copy of any prompt
bytes in version control. They are archivable the day the upload is validated, and not before.

## The extraction check — before ANY scaffolding is archived

```bash
python $S extraction --target <the brief>      # exit 1 = NOT SPENT, it stays
```

**"The session returned" is not the test.** A returned session whose traps were never written down
anywhere else leaves its brief as the sole copy of that reasoning. The test is whether the reasoning
has **another home**. Two independent failure modes, either of which keeps the file:

1. **The file's own text says its work has not happened.** `DO NOT RUN THIS YET`, `must be
   sequenced`, `after deploy`, `scheduled for`. Scaffolding for a session that has not run is not
   spent — and this is not hypothetical: one brief in that initiative is a *future* session's
   instructions that invokes two scripts by path.
2. **No decision record cites it.** Then archiving removes the only copy from the repo. Extract the
   reasoning into a decision record *first*, or keep the file.

**Measured case worth internalising:** `briefs/AR1-archive-review-records.md` describes an archiving
operation that **is finished** — the intuitive case for archiving the brief. `extraction` returns
**NOT SPENT**, because zero decision records carry its reasoning. Finished work and spent scaffolding
are different properties.

What counts as a decision record is configurable (`--records`); the default set is
`topology.md`, `roadmap.md`, `execution-plan.md`, `forward-plan.md`, `*changelog*.md`, `*DECISION*.md`.

## The functional-dependency guard — derived vs load-bearing

```bash
python $S fundep --target <path you are about to move>   # exit 1 = STOP
```

A path inside a shell array or a python literal is an **argument to a running program**, not a
reference in prose. The two fail differently and only one is repairable after the fact:

| | Goes stale | Repaired by |
|---|---|---|
| **Citation** in a doc | silently — nothing fails a build | an edit, any time |
| **Functional dependency** in an executable | the program *breaks* | nothing; re-annotation does not help |

Live instance: `regenerate-prompt-packet.sh` holds **9** capture paths in a `FILES=()` array. A sweep
that treats those like citations has silently become a code change. If `fundep` flags a path, either
repoint the executable **in the same commit** or do not move the file.

Comment lines are excluded deliberately — a `#` line naming the path is a citation, not a dependency.

## Declaring kinds for an initiative

Defaults cover unambiguous shapes only; **everything else is UNCLASSIFIED and fails the gate.** That
is the point — a default bucket is how 136 files got a disposition nobody chose. An initiative
declares its own kinds in a committed manifest:

```
# .specs/{initiative}/cleanup-kinds.txt      lines are `kind: glob`, # comments ignored
decision-record: post-upload-verification-*.md
scaffolding:     share/*
rollback-anchor: <capture-dir>/prompts/**
```

Valid kinds: `decision-record` · `slice-spec` · `scaffolding` · `rollback-anchor` · `instrument` ·
`result`. The manifest is a **committed artifact**, not a convenience: which kind an artifact belongs
to is a decision, and a decision that lives only in a session's head is what this gate exists to stop.

**Doc-shaped rules are pinned to doc extensions on purpose.** While building this gate an unpinned
`*changelog*` claimed `pending-edits/apply_changelog_ub_row.py` as a decision-record, hiding a script
from the instrument checks. A name pattern must never outrank what the file actually is.
