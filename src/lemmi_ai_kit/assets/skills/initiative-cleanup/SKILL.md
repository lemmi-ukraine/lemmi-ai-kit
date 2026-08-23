---
name: initiative-cleanup
description: >
  End-of-initiative cleanup workflow: settle every roadmap row against git, write the forward plan
  the next session inherits, partition deletion targets into tracked vs untracked BEFORE removing
  anything, retire specs by status transition rather than deletion, and run a comment-reduction pass
  over the code the initiative added. Destructive steps are approval-gated. Use when the user says
  "clean up the initiative", "we're done with this epic", "retire these specs", or "tidy up the
  tasks and specs".
when_to_use: >
  "clean up the initiative", "we're done with this epic", "retire these specs and tasks", "tidy up
  after this work", "settle the roadmap", "clean up the comments we added".
metadata:
  type: workflow
---

# Initiative Cleanup — settle, preserve, retire, trim

## When this skill activates

- An initiative or epic has shipped (or been parked) and its scaffolding is still on disk
- The board carries rows that no longer describe reality
- Specs, task docs and temp artifacts have accumulated across sessions
- New code from the initiative is comment-heavy and the operator has asked for a trim

**Destructive by nature — so it is gated.** The plan is presented and approved *before* anything is
removed. It never touches another session's uncommitted work.

**Two files, one per purpose — do not conflate them.** `.specs/{initiative}/cleanup.md` = **phase
state**, so an interrupted or compacted run resumes from the right step. `cleanup-plan.md` = **the
plan presented at Step 6**, the file `coverage` is pointed at, and the artifact the operator approves.


## The gates are a script, not this document

**The prose in this file has already failed in production.** The 2026-08-09 run violated *"partition
per FILE, never per directory"* — stated **four times below** — caught only by a later self-review.
Same shape as a rule written in three places, where the first
session after out-violated the whole pre-rule window. A hook fixed that one; a script fixes this.

So the decisions that determine whether a file is deleted are **executable and exit non-zero**:

```bash
S="${CLAUDE_SKILL_DIR}/scripts/audit_cleanup_targets.py"

python "$S" census     --root .specs                       # Step 3 — per-file partition + exhaustiveness
python "$S" kinds      --root .specs/<initiative>          # Step 3b — per-file ARTIFACT KIND + completeness
python "$S" evidence   --symbol <SymbolTheWorkIntroduced>  # Step 4a — CODE vs DOC-ONLY vs ABSENT
python "$S" extraction --target <scaffolding file>         # Step 4a-bis — is the reasoning elsewhere?
python "$S" fundep     --target <path being moved>         # Step 4b-bis — does a PROGRAM read this?
python "$S" refs       --target .specs/<name>              # Step 4b — inbound refs + authority guard
python "$S" coverage   --root .specs --plan <plan.md>      # Step 6 — whole population dispositioned?
```

All are read-only. **A non-zero exit is a stop, not a warning** — if `evidence` says DOC-ONLY,
the spec is not implemented, whatever its header claims. Each gate exists because it caught a real
error on 2026-08-09, in a run that had this whole document in context; measured evidence per gate:
[references/self-review-gate.md](references/self-review-gate.md).

**`coverage --root <one initiative>` must be run with `--per-file`.** Without it the gate counts
*directories*, and measured 2026-08-19 a plan containing the single string
one initiative's spec directory dispositioned all 157 files inside it and exited 0.


## Step 0 — Establish what is actually true right now

Run first, every time. Three sessions share this checkout and things move under you.

```bash
git rev-parse --short HEAD && git log --oneline -3
git status --porcelain --untracked-files=no
git stash list
git diff HEAD --stat
```

**Re-verify every target named in the initiative's own docs against the tree before planning
anything.** A task doc is a claim, and claims age.

**Then run the census before dispositioning anything** — deriving the population from whatever the
initiative's own docs happen to mention is circular:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/audit_cleanup_targets.py" census --root .specs
```

### Ask the operator two things now, not after the plan is written

Both are intent that is nowhere in the tree, and either one wrong invalidates the plan's
**structure**, not a row — a plan on the wrong branch base is re-derived, not edited.

1. **Where does the cleanup land relative to open PRs?** Before, after, or **with** them as the top
   of the stack? This decides the branch base. (2026-08-09: reasoned to "after" from conflict risk;
   the operator was merging 16 approved PRs as one cascade and wanted the cleanup inside it.)
2. **Which tiers are in scope?** Board/reference repair · spec retirement · artifact rescue ·
   scratch sweep. Very different blast radii; the operator may want only the first.

**If `gh` is unauthenticated, PR state is retrievable, not unknown** — say what would retrieve it
(`gh auth login`, `GH_TOKEN`) and ask. Never substitute `git merge-base --is-ancestor`: under
squash-merge it reports "not merged" for work that is in `dev`, and three consecutive passes in this
repo drew exactly that wrong conclusion.

> Live proof: a requirements brief named `services/conduct/` as the comment-pass target at 45 %
> comment share. By cleanup time the package was **gone** — reverted, 14 files, 1,609 deletions. A
> cleanup that trusted the doc would have planned a pass over files that no longer exist.

## Step 1 — Settle the roadmap

Every board row reaches a **terminal state**. No row is left mid-sentence.

**The board is whatever file the initiative's spec names.** For interview-realism that is
`tasks/BACKLOG-interview-realism.md`; `tasks/BACKLOG.md` is the repo-wide index that points to it.
Resolve it before step 1 and name it in the plan — do not assume.

Whatever board it is, **it already owns its status vocabulary. Do not redefine it.** The realism board
uses `open · in progress · spec ready · on a branch · parked · delegated · deployed—verify · done`.
Add only the two retirement states this workflow needs:

- `superseded (→ <pointer>)` — a later decision replaced this one; the record stays. **This one is
  ADR practice.**
- `retired (→ <where the artifact went>)` — the work is closed and the artifact was relocated. **This
  one is a local coinage, not ADR** — ADR's nearest standard state is `deprecated`.

**Adding a state changes a vocabulary two boards share** — update both in the same edit, or record
the divergence.

**Do not "fix" the difference you will notice between them.** `tasks/BACKLOG.md` lists six states and
omits `deployed—verify` and `done`; that is a documented division of labour, not drift — it prunes
done items to a *Recently shipped* section and names the initiative board as the authoritative status
home ("don't duplicate statuses across the two"). Reconciling it would be exactly the redefinition
this step forbids.

Nygard's rule for decision records is the one to follow: *"If a decision is reversed, we will keep the
old one around, but mark it as superseded. (It's still relevant to know that it* was *the decision,
but is* no longer *the decision.)"* ADR practice does not say delete.

**Every settled row cites the command that settled it.**

Two board rows once read `UNCOMMITTED` after their work was committed, and the error survived until a
later review pass. Worse, three successive passes concluded "nothing is merged" from
`git merge-base --is-ancestor` when all twelve stack PRs had merged — under squash-merge the original
SHAs are not ancestors while the content *is* in `dev`.

```bash
git fetch --prune origin                              # REQUIRED FIRST — nothing else refreshes origin/*
git rev-parse --verify origin/dev                     # the ref must resolve, or the next line lies
git grep -l '<symbol the work introduced>' origin/dev  # "did it land?" — ask content, not ancestry
```

**A status cell is a claim with a date.** Write the date next to it.

## Step 2 — Write the forward plan BEFORE deleting anything

This is what makes deletion safe. It goes in a file this step **writes and stages, then hands to the
operator to commit** — committing here would be an outward action before the workflow's only approval
gate, and a one-time "go ahead" does not generalize —
`.specs/{initiative}/forward-plan.md` — not in `.ai/handoffs/` (gitignored, single copy) and not in
`.ai/tmp/` (deleted mid-initiative once, taking both the raw exports and every derived artifact,
unrecoverable). **Writing under `.specs/` does not track it:** the directory is not ignored, but a new
file there is untracked until `git add`.

Contents:
- **Open decisions** — what was deliberately not decided, and what would decide it
- **Pending verifications, each with its date** — "deployed, verify after 2026-08-11"
- **Watch-list items** — things expected to break or drift
- **Revival triggers** for anything parked — the condition under which it comes back

Then check every path this plan cites is actually durable — **in that order, because the second
command alone proves the wrong property**:

```bash
git ls-files --error-unmatch <file>   # exit 0 = it is IN GIT. This is the durability test.
git check-ignore -q <file>; echo $?   # 0 = ignored ⇒ it can never be committed as-is
```

**Always pass a FILE, never a directory, and never a trailing slash.** Measured: for one gitignored
directory, `git check-ignore -q <dir>` → exit 1 ("durable") while `<dir>/` → exit 0 ("can never be
committed") — the same directory, opposite verdicts, decided by one character. Other pairs in the
same tree agreed, so this is not a general rule you can reason around: whether the trailing slash
flips the verdict depends on which ignore pattern matches. The file-level form is unambiguous.

`check-ignore` answers "could this ever be tracked?", not "is it tracked?". It returns "durable" for a
file that does not exist, and for an untracked single copy. Verified while writing this skill: its own
research brief passed `check-ignore` while asserting "this file is the DURABLE copy" — and
`ls-files --error-unmatch` reported it untracked. **That is F7 passing this step's own gate.**

## Step 3 — Partition before removing (the load-bearing step)

**Run this before touching anything. "Git history recovers it" is true only for the tracked half.**

**Partition per FILE, never per directory.** `git ls-files --error-unmatch` takes a *pathspec*:
handed a directory it exits 0 if **any** file under it is indexed. Verified here — a `.specs/`
subdirectory returned exit 0 ("tracked, recoverable") while a file inside it was untracked and
recoverable by nothing: the mixed set this step exists to catch, passing its own gate.

```bash
git ls-files -- <target>                              # 1. the tracked set
git ls-files --others --exclude-standard -- <target>  # 2. the untracked set
git ls-files --others --ignored --exclude-standard -- <target>  # 3. the IGNORED set
# all THREE lists must account for EVERY file on disk under <target> before anything is removed
```

**Three lists, not two — `--exclude-standard` alone hides the least recoverable population.** It
suppresses gitignored paths, so everything under a gitignored scratch root appears in *neither* of
the first two lists while sitting on disk: a partition built from those two reports complete coverage
over a set it cannot see, and that hidden set is exactly the one with **no history and no recovery
path** (§4c — corpora have been lost this way twice). Verify exhaustiveness, do not assume it:

```bash
diff <(find <target> -type f | sed 's|^\./||' | sort) \
     <(git ls-files -- <target>; \
        git ls-files --others --exclude-standard -- <target>; \
        git ls-files --others --ignored --exclude-standard -- <target>) 2>/dev/null
# any line only in the left column is a file no partition claimed — resolve it before removing anything
```

`tasks/` and `.specs/` are routinely half-untracked — docs are authored across sessions and land with
their own commits. `git rm` **refuses** on untracked paths, and a plain delete of one is permanent.

| Partition | Action | Recovery |
|---|---|---|
| Tracked | `git rm` | `git log --diff-filter=D --name-only` |
| **Untracked** | **Preserve FIRST**, then remove | see below — the copy is not enough |

Copy to a dated backup directory (`<backup-root>/<date>-<initiative>/`), then remove, and say so in
the report. **But a copy is not preservation if it lands somewhere gitignored** — that is a single
local copy with no history, which one `rm` erases. Check the destination before trusting it
(`git check-ignore -q <backup-root>/.keep; echo $?`). So preserving means: copy there **and
`git add` it on the retirement branch** — and if the destination turns out to be ignored, choose a
tracked one rather than reaching for `-f`. Otherwise *state in the report* that the artifact now has
exactly one copy and no history. If it is worth keeping, it is worth committing. **Never let a
blanket "git can recover this" cover a mixed set** — state the partition explicitly in the plan.

**Before deleting any doc, apply the doc-retirement gate** (defined in `post-task-review` step 7 —
read it there; **do not invoke it**, it is a `workflow` skill and so is this): grep the doc for fenced
code blocks and "Reproduce" / "How to find" / query sections, and relocate each **verbatim** next to
the step that needs it, never into a summary. A relocation pass captures claims and obligations and
systematically misses queries — "the checklist survived" and "the means of executing it survived" are
two separate gates.

**Never delete another session's uncommitted work.** Anything in `git status` that this initiative did
not produce is out of scope — list it, do not touch it.

## Step 3b — Classify by artifact KIND. Step 4a cannot reach most of a real initiative

**This step exists because the skill shipped with one axis and reported success on a run that
retired nothing.** Step 4a asks *is the work this file describes implemented?* — right for a spec,
**unanswerable** for session scaffolding, which describes no code and so has no symbol to prove.
Measured on one initiative's spec directory: **51 briefs + 85 capture
files = 136 of 157 tracked files** sat outside the only gate the skill had, and the run reported
completion — on its **coverage**, not its **outcome**. The rule was right; the axis was missing.

```bash
python "$S" kinds --root .specs/<initiative> --list    # exit 1 = an unclassified file remains
```

Every file gets exactly one kind, each paired with **the condition that ends its life**:

| Kind | What ends its life | Disposition while unmet |
|---|---|---|
| **decision-record** — topology, roadmap, execution/forward plan, ADR, changelog | **Nothing.** It is the durable *why* | **Keep, always.** Never a deletion candidate; status transition only |
| **slice-spec** — requirements/design/tasks/spec | Step 4a: the deliverable exists in **code** | `parked`, keeps its revival trigger |
| **scaffolding** — dispatch briefs, edit sheets, hand-off pointers | The session returned **and** its reasoning is in a decision record | Keep — run `extraction` |
| **rollback-anchor** — byte captures, `.sha256` manifests | The change it reverts is **deployed and validated** | Keep. The only revert path is not a tidiness candidate |
| **instrument** — measurement and apply scripts | **Every** documented invocation is spent | Keep |
| **result** — query dumps, JSON/measurement outputs | The claim it supports is closed | Keep |

**A kind is not a disposition** — it is the *conjunction* of kind and condition, and this is where
the naive reading fails hardest: "measurement never needed to be in git, archive it" is wrong for
**all 26** instruments in that initiative, each invoked from a brief headed *"DO NOT RUN THIS YET"*
or named as the replay point for an un-shipped upload. Kind says *measurement*; condition says
*pending*. **Pending wins.** Two sub-gates, both mandatory before anything moves:

```bash
python "$S" extraction --target <the brief>       # exit 1 = NOT SPENT, it stays
python "$S" fundep     --target <path to move>    # exit 1 = a PROGRAM reads it — STOP
```

- **`extraction`** — scaffolding is spent **only if its reasoning is already in a decision record**.
  "The session returned" is not the test. **A brief with no other home is not spent, whatever its
  session's status**; nor is one whose own text says its work has not happened.
- **`fundep`** — a path in a shell array or python literal is an argument to a running program. A
  citation goes stale silently and an edit repairs it; a dependency **breaks** and re-annotation does
  not. `regenerate-prompt-packet.sh` holds **9** capture paths in `FILES=()`.

Kind declaration (`cleanup-kinds.txt`), the measured evidence per row, and both sub-gates in full:
[references/artifact-kinds.md](references/artifact-kinds.md).

## Step 4 — Retire, don't just delete

**Three preconditions gate EVERY deletion. All must pass, in this order, or the file stays:**
**4a** it is actually implemented · **4b** every inbound reference is repointed · **4c** it is not an
irreplaceable input misfiled under a scratch path. Read 4c *before* applying the disposition table —
it is what decides whether a `.ai/tmp/` target is a deletion candidate at all.

### 4a. The work must actually be implemented — verified, not assumed

**Scope: this gate governs the `slice-spec` kind only.** It is the *implementation* axis, and it is
structurally unable to speak about scaffolding, rollback anchors, instruments or results — those are
dispositioned by their own life-ending condition in Step 3b, not here. Applying 4a to a dispatch
brief is not a strict reading; it is a category error that permanently protects every brief, and it
is exactly what made a whole cleanup run retire nothing.

A **spec or task** is deletable **only** because the thing it describes now exists in code. If it is
not implemented, it is not "done" — it is `parked` and keeps its revival trigger. Never delete a spec
to tidy up.

Prove it by **content, not by ancestry** — squash-merge makes the original SHAs non-ancestors while
the code is in `dev`:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/audit_cleanup_targets.py" evidence --symbol <Symbol>
```

**Use the script, not a bare `git grep`.** An earlier revision of this step recommended
`git grep -l '<symbol>' origin/dev` — and that command is itself the defect: unscoped, it matches
`README.md`, and on 2026-08-09 it produced **14 false "implemented" verdicts out of 34**, every one
a doc hit. The script classifies by file type and refuses to score documentation as code.

Pick the symbol from the spec's own acceptance criteria (a class, a route, a migration id, a settings
field). **No symbol you can grep for is itself the finding**: a spec whose deliverable cannot be
named in code did not ship, whatever the board says.

**Three rules the script enforces, each from a measured failure** (cases:
[references/self-review-gate.md](references/self-review-gate.md)):

1. **A `.md` hit is DOC-ONLY, never implemented.** `ConductGovernor` appears in two specs and a task
   doc and in **no** code — the package had been reverted. An unscoped grep would have
   called it shipped and deleted the record of a deliberate removal.
2. **A symbol shared across spec dirs proves nothing about any one.** `transcript_gradeability` is
   real landed code belonging to the *eligibility* work, and it also matched
   `stt-coverage-collapse-handling`, whose own header reads *"no code written"*. On SHARED: find a
   unique symbol, or **record no verdict**.
3. **A spec's self-reported status is inadmissible — in both directions.** Measured across all 55
   spec dirs, tick-counts of 6/70, 0/14 **and** 42/42 all described **shipped** work, so neither a
   high nor a low count carries information. Gate on the code, never on a checkbox or a header.

**No verdict is a valid verdict.** If no unique symbol identifies the deliverable, the spec stays.
Keeping a stale spec costs a stale file; a wrong delete costs the design.

**ABSENT is not a negative verdict — it usually means the symbol was wrong.** Try ≥3 symbols from
the spec's own acceptance criteria before concluding anything. **Two evidence sources outrank the
gate and must be recorded as overrides:** the **operator** (they know what shipped; mark the row
*operator-confirmed* and still record whether code corroborates — an uncorroborated confirmation is
the one to re-check, not to hide), and **deliverables outside this checkout** (a kit, a fork,
another repo — ABSENT there means nothing). Measured cases:
[references/self-review-gate.md](references/self-review-gate.md).

### 4b. Every inbound reference must be repointed BEFORE the file is removed

Deleting a tracked file is cheap; leaving the citations behind is what costs. **A dead reference is
silent** — no build fails over a dead pointer, and the citing doc still reads as maintained.

```bash
# find every inbound reference across the WORKING TREE, by basename AND by path
grep -rn '<basename>' --include='*.md' --include='*.py' . | grep -v '/\.ai/tmp/'
```

> **`git grep` is the wrong tool here and will report a clean sweep when it is not.** It reads the
> **index**, so it cannot see untracked files, and step 3's premise is that `tasks/` and `.specs/`
> are routinely half-untracked — measured 2026-08-04, `git grep` returned **0** where a working-tree
> `grep -rn` returned **10+**. Use `grep -rn` (or `git grep --untracked`), and re-sweep with the same
> command and scope: a narrower re-sweep proves nothing.

Repoint each hit to whichever is true:

| The content… | Repoint to |
|---|---|
| moved to a code-adjacent home | that README / test / code comment |
| survives only in history | the recovery command: `git show <deleting-commit>^:<path>` |
| is superseded | the superseding doc, by path |

Then **re-run the grep and require zero hits** outside recovery commands. Deletion is not done when
the file is gone; it is done when nothing points at a hole.

> **Measured live, 2026-08-04:** deleting one shipped-work spec created three dead references in the
> same minute and **every gate stayed green**. Only a post-task reference sweep caught it. Full case:
> [references/self-review-gate.md](references/self-review-gate.md) § *A dead reference passes every gate*.

Only once 4a and 4b both pass:

| Artifact | Disposition |
|---|---|
| Spec for work that **shipped** | **DELETE it** (tracked, so `git log --diff-filter=D` recovers it) after relocating anything durable to the **code-adjacent home** — feature README, test name, code comment — and leaving a changelog pointer to the landing commit. Once code ships, the code + tests are the truth and a retained spec is a second source that drifts. *Measured:* a shipped fold-split spec was 242 lines, of which ~10 (alternatives-rejected) were not already in the code, its 19 tests, the README or the task doc. Relocate those 10, delete the file. |
| Spec for work that was **parked** | **Keeps its revival trigger.** Deleting it destroys the decision *not* to build — exactly what stops the next initiative re-deriving it |
| Genuine scratch under `.ai/tmp/` | Go — **only after 4c below**. Gate captures, one-off scripts, intermediate JSON |
| **Anything under `.ai/tmp/` that is an INPUT, not an output** | **KEEP — never swept.** See 4c: `.ai/tmp/` is not one class |
| Hand-offs in `.ai/handoffs/` | Go. They are pointers by contract; the durable fact is elsewhere in git |
| Every other kind — decision record, scaffolding, rollback anchor, instrument, result | **Step 3b owns these.** Disposition is that kind's life-ending condition, not this table. Measurement corpora and raw exports in particular: keep, and move somewhere durable — they have been lost once with no copy anywhere |

### 4c. `.ai/tmp/` is NOT one class — classify by content, never by directory

`.ai/tmp/` is gitignored, so **nothing in it has history and nothing in it is
recoverable** — a sweep there is final. It holds two populations that look identical from the path:
**scratch** (this session made it and could remake it → sweep) and **INPUT / corpus** (production
exports, log downloads, anything a report's numbers were computed from → **never** sweep; upstream
retention rolls, so it is not regenerable). Two checks per file — the path never decides:

```bash
git grep -l '<the path or its parent dir>'   # cited by a TRACKED file? then it is not scratch
# and: could you regenerate it? production query / log export / retention-bound API call => NO
```

**Measured twice**, most recently 2026-08-09: `.ai/tmp/` was 168 MB, of which 124 MB `logs/` and
4.4 MB corpus tree are INPUT class, while **54 tracked files cited paths inside it**. An
earlier blanket delete took the raw exports and every derived artifact, unrecoverable. Full tables,
the incident, and the `.ai/corpora/` structural fix:
[references/tmp-classification.md](references/tmp-classification.md). **Until that lands, `.ai/tmp/`
is swept per file, never wholesale.**

## Step 5 — Comment-reduction pass over the code the initiative added

**Runs only if the operator asked for a trim.** Full method, scoping commands and the
KEEP/CUT/SHORTEN/RELOCATE table: [references/comment-pass.md](references/comment-pass.md).

Two things that must not be lost to a summary:

- **Scope the pathspec, or the pass edits what Step 3 just preserved.** Unscoped, the untracked arm
  returns everything: measured 2026-08-04, **30 untracked `.py` files of which 26 were under
  `.ai/`** — 22 of them backup copies made minutes earlier by Step 3.
- **There is no evidence-based comment-density target, and this skill does not invent one.** Judge
  per comment and *report the delta*; never work toward a percentage. The cut criterion is
  duplication, not length — a long comment carrying a measurement that exists nowhere else is a KEEP.

## Step 5.5 — Self-review. MANDATORY, and it runs before the operator sees anything

**This step exists because its absence was the single most expensive gap in the 2026-08-09 run.**
Every finding below was eventually found — but by the *operator*, after the plan had been presented
as finished, across four correction rounds. None of them needed a human; all were derivable from the
tree. The purpose of this step is that the operator's first read is of a plan that has already
survived its own audit.

### 5.5a — Run every gate. Each must exit 0, or the plan is not ready

```bash
S="${CLAUDE_SKILL_DIR}/scripts/audit_cleanup_targets.py"
python "$S" census   --root .specs
python "$S" kinds    --root .specs/<initiative> --list             # exit 1 = an unclassified file
python "$S" coverage --root .specs/<initiative> --per-file \
                   --plan .specs/<initiative>/cleanup-plan.md    # --per-file is NOT optional here
for name in <every deletion candidate>; do
  python "$S" refs   --target ".specs/$name"          # exit 1 = live refs or an authority cite
  python "$S" fundep --target ".specs/$name"          # exit 1 = a PROGRAM reads it — stop
done
for brief in <every scaffolding file proposed for archive>; do
  python "$S" extraction --target "$brief"            # exit 1 = NOT SPENT, it stays
done
for sym in <every 4a symbol>; do
  python "$S" evidence --symbol "$sym"                # exit 1 = DOC-ONLY, ABSENT, or SHARED
done
```

A non-zero exit is not something to explain in the plan's prose. It means a row is wrong.
**Record each gate's exit code in the plan** — a gate whose output you did not read is UNRUN, and
"it looked fine" is how the 34-verdict / 14-false-positive pass reported itself as complete.

**And a gate that passed over a population it could not see is also UNRUN.** Before quoting any
exit 0, state what that instrument cannot look at: `census` cannot see kind, `kinds` cannot see
whether a condition is met, `refs` cannot see an executable's arguments, and every one of them was
blind to something that mattered here. Establishing an instrument's blind spot is part of running it.

### 5.5b — Invoke `plan-critic`, and actually walk its reference files

`plan-critic` is a `review` skill, so a workflow may invoke it (not the forbidden
workflow-in-workflow nesting). **Read its three `references/*.md` files — do not recall them.** The
2026-08-09 run reviewed from memory and found 2 Blockers; walking the same tables afterwards found
**4 more Majors and 1 more Blocker**. **State in the plan which reference files were read** — that is
the only thing distinguishing a walked review from a remembered one.

### 5.5c — Answer S-1 … S-8 in the plan, before presenting

The eight questions, each with the failure it was derived from:
[references/self-review-gate.md](references/self-review-gate.md) § *The eight questions*. In short:
is the whole population dispositioned **per file** (S-1) and claimed by exactly one **kind** (S-6);
for anything being removed, **which life-ending condition is met and what proved it** (S-7); did
`refs` and `fundep` both run on every path (S-2, S-8); does every 4a verdict rest on CODE via a
**unique** symbol (S-3); where does this land relative to open PRs (S-4); and is any load-bearing
fact merely *unavailable* rather than false (S-5).

**S-4 is a question for the operator, not a deduction** — ask it in Step 0. Sequencing depends on
merge intent that is nowhere in the tree.

### 5.5d — Where the plan is uncertain, say so in the plan

Not in the chat message: a caveat that lives only in conversation is lost the moment anyone else
reads the plan. **No verdict is a valid verdict** — keeping a stale spec costs a stale file, a wrong
delete costs the design, and for an untracked spec it costs it permanently.

## Step 6 — Approval gate · Step 7 — Execute, then report the deltas

Present, then wait. Nothing is removed before Step 6 returns. **The plan must open with the gate exit
codes, the plan-critic reference files read, and the S-1..S-5 answers** — a plan that leads with its
deletion table is asking to be trusted rather than checked. The Step 7 report must state **what was
preserved and where**, not just what was removed; one that lists only deletions is unauditable.

Both templates: [references/output-templates.md](references/output-templates.md).

## Step 8 — Hand knowledge off; do not absorb it

- **Invoke `task-learnings`** to extract findings into the `.ai/learnings.md` intake buffer.
- **Ask the operator to run `/learning-consolidator`** — do **not** invoke it. It is a workflow, and
  a workflow skill may not invoke another workflow skill (max one level of nesting).
- AI-infrastructure changes go to `.ai/ai-changelog.md` via `ai-changelog`, with a hypothesis via
  `ai-improvement-tracker` where one is warranted.

## Anti-patterns

**Seven of these are now gated mechanically** — "git can recover it" over a mixed set (`census`),
removing a file before fixing its citations (`refs`), scoring a doc hit as implementation and
trusting a shared symbol (`evidence`), leaving a file in no category at all (`kinds`), archiving
scaffolding whose reasoning has no other home (`extraction`), and moving a path a program reads
(`fundep`). A non-zero exit stops them; prose did not.

The ones no script can catch, which is why they stay here:

| Anti-pattern | Why it seems right | What actually happens |
|---|---|---|
| **Judge every artifact on the implementation axis** | Step 4a is the skill's stated gate, and it is strict | Scaffolding describes no code, so 4a can never be satisfied — 136 of 157 files became permanently undeletable and the run reported success. **The rule was right; the axis was missing** |
| **Read a kind as a disposition** | The taxonomy says "measurement never needed to be in git" | All 26 instruments in one initiative were load-bearing: invoked by a brief marked *"DO NOT RUN THIS YET"*, or the declared replay point for an un-shipped upload. Kind ∧ condition, never kind alone |
| **Treat "the session returned" as "the brief is spent"** | The work is over, so the scaffolding is waste | A returned session whose traps were never written down leaves the brief as the *only* copy. Spent means the reasoning has another home |
| **Re-annotate a path an executable reads** | It looks like every other citation | Citations go stale silently and an edit fixes them; a `FILES=()` entry *breaks*, and no annotation repairs it |
| **Report a gate's exit 0 without stating its blind spot** | The gate passed | `census` passed on all 157 files while blind to kind. A pass over a population the instrument cannot see is coverage, not outcome |
| Delete the parked spec | The work is not happening | Destroys the decision *not* to build; the next initiative re-derives it |
| Delete a spec that was never implemented | It is stale and nobody reads it | Stale ≠ done. Unimplemented means `parked` with a revival trigger (step 4a) |
| Trust a spec's own status or checkbox count | It is the spec's own claim about itself | Fails in both directions: 6/70 and 0/14 both described **shipped** work; 42/42 also did |
| Sweep `.ai/tmp/` wholesale | It is called "tmp" and gitignored | Holds production exports that cannot be re-queried, and 54 tracked files cite paths inside it. Gitignored means no history — the sweep is final |
| Summarize a doc, then delete it | The knowledge survived | Relocation captures claims and misses repro steps and queries |
| Cite `.ai/tmp/` or `.ai/handoffs/` as the durable home | The file is right there | Both gitignored; the reference dies at the next cleanup |
| Settle the board from memory | It was accurate when written | Rows read `UNCOMMITTED` after the work was committed |
| Use `--is-ancestor` to prove work landed | It is the obvious git check | Squash-merge makes it false while the content is in `dev`; three passes got this wrong |
| Deduce the merge/branch sequencing | The conflict analysis is sound | Sequencing is operator intent, not a tree fact — ask it in Step 0 (S-4) |
| Cut comments to hit a ratio | 45 % is obviously too high | No evidence-based target exists; you delete the measurement that justified a constant |
| Clean up files another session is editing | The tree looks messy | Destroys unrelated in-flight work |
| Trust the initiative's own doc for the target list | It was written by this initiative | Targets move — one was reverted out of the tree entirely before cleanup ran |

## Cross-cutting rules

Secrets, durable-vs-ephemeral artifacts, authorization scope, branch hygiene, own-hunks staging and
gate-verdict discipline are shared across these skills — see
[stacked-pr-planner](../stacked-pr-planner/SKILL.md) § Cross-cutting rules. The one that binds
hardest here: **anything another session must act on lives in git, or is reconstructible from
something in git.**

## Related

- `scripts/audit_cleanup_targets.py` — the gates (`census` · `kinds` · `extraction` · `fundep` ·
  `evidence` · `refs` · `coverage`). `kinds`/`extraction`/`fundep` are the artifact-kind axis added
  2026-08-19; `.specs/{initiative}/cleanup-kinds.txt` is where an initiative declares its own kinds
- `references/self-review-gate.md` — Step 5.5 detail and the measured failures behind each gate
- `references/tmp-classification.md` · `references/comment-pass.md` — Step 4c and Step 5 detail
- `plan-critic` (invoke at Step 5.5b — read its `references/`, do not recall them)
- `AGENTS.md` — the deletion-sweep rule this step 3 implements; the learnings-system routing
- `post-task-review` — the doc-retirement gate and the `git check-ignore` durable-path check
- `task-learnings` (invoke) · `learning-consolidator` (ask the operator to run) · `ai-changelog`
- `stacked-pr-planner` — the topology table this settles at the end
- `parallel-session-safety` — why the tree may not be what the docs say it is
