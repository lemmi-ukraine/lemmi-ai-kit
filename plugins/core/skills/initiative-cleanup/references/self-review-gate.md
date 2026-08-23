# Self-review gate — the detail behind SKILL.md Step 5.5

Read this when running Step 5.5. It carries the measured evidence for each gate and the full
self-review checklist; SKILL.md carries only the commands.

## Why every gate here exists

All five findings below come from the **2026-08-09** cleanup run — a run that had the whole of
SKILL.md in context and still made each error. They were caught by the *operator*, across four
correction rounds, after the plan had been presented as finished. None needed a human: all were
derivable from the tree. That gap is what Step 5.5 closes.

| Gate | What it caught | Cost if it had not fired |
|---|---|---|
| `census` | 15 spec dirs with **no git history**, 1 mixed dir | A `git rm` refusal, or a permanent delete presented to the operator as "git can recover it" |
| `evidence` | **14 of 34** "implemented" verdicts were README hits | Deleting the design for work that never shipped |
| `evidence` | `transcript_gradeability` is **shared** across specs | Scoring a spec whose own header says "no code written" as shipped |
| `refs` | `stacked-pr-skills/research-brief.md` is cited by `CLAUDE.md` | Deleting the decision record a shipped skill cites for its core policy |
| `coverage` | The plan dispositioned **19 of 55** dirs | A partial audit presenting itself as complete |

## 2026-08-19 — the missing axis. A run that retired nothing and reported success

The three gates below (`kinds`, `extraction`, `fundep`) come from a **different** failure than the
2026-08-09 set, and it is the more dangerous shape: **every gate passed.** Nothing was mis-scored;
the run simply never asked a question that could reach two-thirds of its target, then reported on its
coverage rather than its outcome.

Step 4a reads *"a spec or task is deletable **only** because the thing it describes now exists in
code."* Correct for a spec. **Structurally unanswerable for session scaffolding** — a dispatch brief
describes no code, so no symbol exists to prove, so 4a can never be satisfied, so every brief is
permanently undeletable. Measured on one initiative's spec directory:

```bash
git ls-files .specs/<initiative>/ | wc -l                    # -> 157 in the measured run
git ls-files .specs/<initiative>/briefs/ | wc -l             # ->  51
git ls-files '.specs/<initiative>/<capture-dir>-*' | wc -l   # -> 85 in the measured run
# 51 + 85 = 136 of 157 unreachable by the only gate the skill had
```

**Two instrument blindnesses, each reproduced before being fixed:**

| Instrument | Reported | Was blind to |
|---|---|---|
| `census --root <initiative>` | `PASS every file on disk is claimed by exactly one partition`, exit **0**, all 157 files in **ONE row** | Its axis is git status — *recoverability*, not kind. And its row key was the first two path components, so a `--root` already two deep collapsed the whole initiative into a single line |
| `coverage --root <initiative>` | counts **directories** | A plan containing the single string one initiative's spec directory dispositioned all 157 files at once. Hence `--per-file` |

**The generalisable lesson, and the reason S-6..S-8 exist:** a gate that exits 0 over a population it
cannot see has not passed — it has abstained. *"Before trusting any instrument, establish what it
cannot see"* is a step, not a sentiment. Six instruments in that initiative would each have certified
success by being blind, including the cleanup skill's own gates.

### Why `kind` is never a disposition

The obvious taxonomy assigns measurement scripts "archive off-repo — it never needed to be in git".
Applied to that initiative it would have moved **26 instruments, every one load-bearing**:

| Instrument | Why it is not spent | Evidence |
|---|---|---|
| `enumerate.py`, `contested.py` | Invoked by repo-root-relative path from a brief whose header reads *"DO NOT RUN THIS YET … scheduled ~2 weeks after the prompt upload"* | the brief's own header |
| `dg1_classification_baseline.py` | Named `Instrument` and invoked under *"How to re-read this after deploy"* — the deploy has not happened | the measurement doc's "how to re-read" section |
| 8 × `measurement/*.py` | Covered by a blanket *"every script behind the numbers above, rerunnable from the repo root"* — a promise that is **repo-root-relative** and falsified by an off-repo move | a findings doc's blanket rerunnability promise |
| `apply_fixes.py`, `apply_edits.py` | An **open, unresolved** sequencing question: *"The §5 edit must be sequenced against those"* | an open spec's sequencing note |
| `apply_p4_final.py` | *"Replay of the shipped state"* for an upload that has not shipped | the post-upload verification doc |
| `apply_unblock_fixes.py` | Kept as a **rollback point** | the change log |

So: disposition = **kind ∧ life-ending condition**. Their kind said "measurement"; their condition
said *pending*. Pending wins, and a taxonomy that cannot express that is a licence to delete.

### The extraction check, and why "the session returned" is the wrong test

A brief describing an archiving operation that **is finished** — the
intuitive case for archiving the brief. `extraction` returns **NOT SPENT**: zero decision records
carry its reasoning, so archiving it removes the only copy from the repo. A brief is spent when its
reasoning has another home, never merely because its session ended.

### `fundep` — the line between derived and load-bearing

`regenerate-prompt-packet.sh` holds **9** capture paths in a `FILES=()` array. Those are arguments to
a running program. A citation goes stale silently and an edit repairs it; a `FILES[]` entry *breaks*,
and re-annotation repairs nothing. Any sweep that treats the two alike has silently become a code
change.

## A dead reference passes every gate

**Measured live.** A parallel session deleted a spec plan as shipped-work cleanup. It was the
layer-table precedent cited twice by `stacked-pr-planner` and once by its research brief. All three
became dead references in the same minute, and **every gate stayed green** — no build fails over a
dead pointer, and the citing doc still reads as maintained.

Only a post-task reference sweep caught it. The fix was three edits repointing at the deleted
file's last committed revision — seconds of work *if the grep runs before the delete*, archaeology
afterwards. This is why 4b requires the working-tree sweep to return zero before
removal, not after.

## Why a spec's self-reported status is inadmissible

Nobody ticks checkboxes on the way out, and status headers are written at authoring time and never
revisited. Measured across all 55 spec directories, 2026-08-09:

| Spec | Says about itself | Reality |
|---|---|---|
| A compatibility spec | *"Draft for design approval"*, **6/70** ticked | Shipped in 3 merged commits |
| A config-mapping spec | **0/14** ticked | Its lookup table live in the service layer |
| An orchestration spec | **0/35** ticked | Its adapter shipped |
| A decoupling spec | **42/42** ticked | Also shipped — the one case where the boxes agree |

They fail in **both** directions, so neither a high nor a low tick-count carries information.
Gate deletions on code, never on a checkbox or a header.

## ABSENT means the symbol was wrong, far more often than the work is missing

Measured. A run recorded a spec as **"not implemented"** from an ABSENT result and moved it to
the keep-list. The spec had in fact shipped — as a settings module, an action handler, and a set
of websocket events. The probe had guessed two class and service names, neither of which ever
existed.

The rule ("no verdict is a valid verdict") was already written in SKILL.md and was violated in the
same session that wrote it — so the tool now prints the recovery procedure on every ABSENT and the
verdict string itself reads `ABSENT -- NO VERDICT (this is NOT 'not implemented')`.

Before recording anything from an ABSENT: try ≥3 more symbols from the spec's own acceptance
criteria, grep the spec text for identifiers (`grep -oE '[a-z_]{6,}\.py|[A-Z][A-Za-z]{6,}'`), and
ask whether the deliverable ships outside this checkout.

## Two evidence sources outrank the gate

| Source | Why it outranks | How to record it |
|---|---|---|
| **The operator** | They know what shipped; the tool sees one checkout at one moment | Mark the row *operator-confirmed*. **Still record whether code corroborates it** — on 2026-08-09 five of six operator confirmations were corroborated and one (`interview-feedback-funnel-stabilization`) was not, and that one is the row worth re-checking |
| **Out-of-repo deliverables** | A spec whose output is a kit, a fork, or another repository can never be confirmed locally | ABSENT is meaningless there. Ask where it shipped and record the answer |

An operator override is not a failure of the gate — it is the gate doing its job by surfacing a row
the tree could not settle. What must never happen is an override recorded *silently*, because then
the next reader cannot tell a verified row from an asserted one.

## Invoking plan-critic without hollowing it out

`plan-critic` is a `review` skill, so a workflow may invoke it — this is not the forbidden
workflow-in-workflow nesting. **Its reference files must be read, not recalled:**

- `.claude/skills/plan-critic/references/dor-tables.md`
- `.claude/skills/plan-critic/references/review-dimensions.md`
- `.claude/skills/plan-critic/references/finding-format.md`

The 2026-08-09 run invoked `plan-critic` and reviewed from memory. That pass found **2 Blockers**.
Walking the same tables afterwards found **4 more Majors and 1 more Blocker** — including a spec
with no git history covering a live credential exposure, and a deletion that would have repeated
this skill's own worst documented incident (`pr441-stack-split/plan.md`, 2026-08-04).

The instruction to walk the files was already in `plan-critic`. It was skipped because nothing
checked. **State in the plan which reference files were read** — that is the check.

## The eight questions, in full

S-1..S-5 were real operator corrections on 2026-08-09; S-6..S-8 come from the 2026-08-19
missing-axis run above. A plan that cannot answer one is not ready to present.

| # | Question | Origin |
|---|---|---|
| S-1 | Is the whole population dispositioned? Cite the `coverage` exit code | 19 of 55 dirs, presented as complete |
| S-2 | Is any deletion target cited by `CLAUDE.md`, `AGENTS.md` or a skill? Cite `refs` | A decision record was one step from deletion |
| S-3 | Does every 4a verdict rest on CODE, and on a symbol **unique** to that spec? | 14 doc hits + 1 shared symbol scored as shipped |
| S-4 | Where does this land relative to open PRs — before, after, or **with** them? | Assumed "after"; operator wanted "with", which changes the branch base |
| S-5 | Is any load-bearing fact *unavailable* rather than false? Name what would retrieve it | `gh` unauthenticated — retrievable with a token, not unknowable |
| S-6 | Is every file claimed by exactly one **kind**? Cite the `kinds` exit code. A plan that dispositions a *directory* has dispositioned nothing | 136 of 157 files in no category, run reported success (2026-08-19) |
| S-7 | For each kind proposed for removal, **which life-ending condition is met, and what proved it?** A kind alone is not an authorisation | "measurement → archive" would have moved 26 load-bearing instruments |
| S-8 | Did `fundep` run on every path being moved? | 9 capture paths sit in a shell `FILES=()` array — a move breaks the program |

**S-4 is a question for the operator, not a deduction.** The 2026-08-09 run reasoned its way to
"after the merge" from conflict risk. The reasoning was sound and the answer was wrong: the operator
was merging 16 approved PRs as one cascade and wanted the cleanup inside it. A plan built on the
wrong branch base is re-derived, not edited — so ask during Step 0.

## Uncertainty belongs in the plan, not the chat message

A caveat that lives only in conversation is lost the moment anyone else reads the plan. On
2026-08-09 two verdicts rested on a single weak symbol each; both were kept on the conservative bias
**and that reasoning was written into the plan**, which is what let the operator overrule it
knowingly instead of discovering it later.

The conservative bias itself: **no verdict is a valid verdict.** Keeping a stale spec costs a stale
file. A wrong delete costs the design — and for an untracked spec dir, costs it
permanently.

## 2026-08-20 drain: four preservation and instrument failures

### "The only copy in version control" is false for any TRACKED file

A run refused to archive 147 artifacts, arguing the 47 prompt byte captures were the only
version-controlled copy of bytes whose upload had not validated. **Every one of the 147 was
tracked.** Removing a tracked file from the tip does not remove it from version control:
`git log --diff-filter=D --name-only -- <path>` finds the removing commit and
`git show <sha>^:<path>` returns the bytes, permanently. The real risk window is narrow —
**between the `git rm --cached` and the commit**, history has no record yet, so in those minutes the
off-repo copy really is the only one. Closing it is just committing.

Distinguish "leaves the tip" from "leaves version control" before refusing on preservation grounds.
The genuinely irreplaceable class is **untracked** (`git ls-files --error-unmatch` exit 1), which is
exactly what the Step 3 partition isolates. Over-refusing has a cost too: the initiative's PR carried
~245 files, past the point anyone reviews it, which was the problem the archive existed to solve.

### A spec cited by production code is load-bearing, and `refs` cannot see it

The same sweep archived a 4-file spec directory; a service module and a test fixture cited its
`design.md`/`requirements.md` as the design rationale for **shipped** code, confirmed live by
`evidence --symbol <Symbol>`. Archiving it would have left production code pointing at a hole, in
trees explicitly out of scope to edit. The `refs` authority check covers `CLAUDE.md`, `AGENTS.md`
and the skills directory and says nothing about source or test trees, so it never flagged it. The
spec was restored.

**A citation from a code path is at least as strong an authority signal as one from `CLAUDE.md`** —
the code is documenting why it looks the way it does. Grep the source and test trees for a spec's
path before archiving it. Script fix (open): extend `AUTHORITY_FILES` so a citation from any code path
makes `refs` exit 1.

### Two host traps inside one file-move loop, both reading as success

Executing a 152-file archive move, both failures produced output that looked fine:

1. `git rm --cached --quiet <paths> | tail -3` reported `exit=0` while git had printed
   `fatal: pathspec ... did not match any files` and staged **zero** deletions — the pipe made `$?`
   the exit code of `tail`. This is the filtered-verdict trap AGENTS.md documents, hit while working
   in the repo that documents it. **Never pipe a mutating git command into a formatter**; check `$?`
   on the bare command.
2. The pathspec file was CRLF, because Python's `write_text(..., encoding='utf-8')` translates the
   newline on Windows unless `newline=''` is passed; git then treated the trailing CR as part of the
   filename. **Always pass `newline=''`** when writing a file another tool parses as a path list.
3. Milder: the move list came from a gate that walks **disk**, so it mixed tracked and untracked
   paths, and `git rm --cached` refuses on untracked — the Step 3 partition is not optional
   bookkeeping.

### A whole-file claim can be wrong for every file it was applied to

"Scripts are derived, byte captures are load-bearing" was applied to 23 files and was wrong for all
23. Before acting on a rule-of-thumb about a *class* of artifact, test it against two members of the
class explicitly; a class-level claim that has never been checked against an instance is an
assumption wearing a policy's grammar. (This is why Step 3b classifies per file, not per directory.)

### A grooming pass deleted the doc whose BODY carried an unexecuted obligation

A `tasks/BUG-<slug>.md` doc was deleted as part of a backlog tidy — recoverable only through
`git show <deleting-commit>^:<path>`. Its *title* read like a closed bug; its **body**
carried work nobody had done. A task doc is not just a status marker — **read the body of every
doc a grooming pass would delete, and grep it for imperative/unchecked items** (`TODO`, `- [ ]`,
"must", "still needs") before removing it. If the obligation is real, it moves to a live doc in the
same commit; the deletion is not a decision about the file, it is a decision about the work.

### A citation is not evidence of extraction, and a basename is not a file

Two failures in `audit_cleanup_targets.py`'s extraction check. (1) Finding that some other document
*cites* a target proves a pointer exists, **not** that the target's reasoning was extracted — the
citation can be a bare filename in a list. Check that the citing document reproduces the content, not
that it mentions the path. (2) Matching on a **basename** conflates distinct files across
directories, so `design.md` matches every spec's design doc; match on the repo-relative path.
Regression cases for both now live with `cmd_extraction` / `_cites_this_file` / `OPEN_STATE_MARKERS`.
