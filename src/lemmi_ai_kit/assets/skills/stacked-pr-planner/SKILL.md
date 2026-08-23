---
name: stacked-pr-planner
description: >
  Plan the branch/PR topology BEFORE the first commit of a multi-slice initiative. Classifies each
  deliverable by risk and review lane, assigns it to exactly one layer, and emits a checkable layer
  table with re-plan triggers. Prevents mixed-risk PRs where a migration is reviewed with the same
  attention as a board-row edit. Use when the user says "plan the branches", "plan the stack",
  "branch topology", "how should we split this into PRs", or before dispatching any epic whose work
  spans production code plus docs or tooling.
when_to_use: >
  "plan the branches", "plan the stack", "branch topology", "how should we split this into PRs",
  "which PR does this go in", "split this initiative", "what base should this branch fork from",
  "create a branch for <feature>", "where does this commit belong", or the orchestrate plan step
  reaching its branch-topology line.
metadata:
  type: task
---

# Stacked PR Planner — decide the topology before the first commit

## When this skill activates

- An initiative will produce more than one deliverable and has not yet been split into branches
- `orchestrate`'s plan step reaches its branch-topology line (this skill is what that line calls into)
- `initiative-planner` reaches step 2 — for multi-session work that skill is the caller, and it
  supplies the charter this topology is built against
- A new deliverable appears mid-initiative and needs a home (**re-plan**, see step 6)
- You are about to commit and the answer to "which branch does this belong to?" is
  "whatever is checked out" — **stop and run this skill**

**This skill decides. It does not execute.** Every command, cascade, force-push and verification
lives in `.ai/git-stacked-pr-workflow.md`; session/cascade safety lives in `parallel-session-safety`
§9–§10. Fixing review comments is `pr-comment-resolver`. Do not restate any of them here.

## Why this exists (do not soften these numbers)

One layer of a real initiative accumulated **28 commits across 7 commit types in one PR** — 18
`docs(ai)`, 4 `feat(ai)`, 2 `fix(ai)`, 1 `feat(db)` **migration**, 1 `fix(transcription)`,
1 `fix(feedback)`, 1 `feat(interview)` — measured over
`feat/ai-hypothesis-ledger-lifecycle..origin/fix/stack-review-findings` **as of 2026-08-04, pinned at
`origin/fix/stack-review-findings` = `4c47f7c7`** (step 7's own rule: OIDs, not refs). (Re-run
it and you will get a larger number: the branch is live and had reached 32 commits hours later. That
drift is the point of step 7, not a contradiction — *state the window and the ref, or the figure
rots*.) The DB migration — the highest-risk artifact in the initiative, carrying an
unrecoverable-data-loss deploy hazard — sat at **position 17 of 20 within that same PR's own range** and
was reviewed with the same attention as a board-row edit. Then the coupling reversed: **one
reviewer's comment on a changelog blocked the migration and two backend fixes from merging.** Repair
cost 5 new PRs, a closed PR carrying an active review, and 7 orphaned comment threads — most of them
pointing at lines no longer in the PR's diff.

**Root cause: the decision of which branch a deliverable belongs to was made at commit time, by
whatever branch happened to be checked out — never at plan time.** Everything below exists to move
that decision earlier.

**On why this is a skill at all.** An earlier spec rejected a stacked-PR skill outright — *"fleet at
listing cap; the knowledge is workflow-doc-shaped"* — and set a rollout gate: *"the next genuinely
layered epic runs the codified workflow end-to-end."* That rejection was right for a *mechanics*
skill: `.ai/git-stacked-pr-workflow.md` genuinely owns the mechanics, and this skill adds none.
This is a *decision procedure* that runs before any mechanics exist. The gate then ran, and failed
on exactly the part no artifact owned.

## Step 0 — Probe the tree before emitting any plan that contains a rebase

Run both probes and record their exit codes. They are the ones `git rebase` calls internally:

```bash
git diff-index --quiet --cached HEAD   # 0 = nothing staged
git diff-files --quiet                 # 0 = no unstaged tracked edits
```

**If either exits non-zero, every rebase in the plan is unexecutable today.** Say so in the table
— mark those rows `NOT-EXECUTABLE (dirty tree: N paths)` rather than emitting them as if they were
runnable. `gh stack init/modify/sync` restructures branches too and is blocked by the same
condition.

Measured 2026-08-14: a plan presented **1 + 9 rebases as executable** against a tree carrying
**117 dirty paths** from parallel sessions; the session's own verdict was *"Every rebase in the
plan refuses to run today."* This checkout is routinely multi-session (`parallel-session-safety`),
so a clean tree is a fact to establish, never an assumption. The dirty paths usually belong to
**another session** — do not clean them, and do not wait on them silently: report whose they are
and let the operator sequence it.

## Step 1 — Enumerate deliverables, not commits

A **deliverable** is *something whose rejection would change what ships*.

That test is the whole classification. A board row cannot be meaningfully rejected — nobody blocks a
merge over it — so it is not a deliverable and does not get a review surface. A migration can be
rejected, and rejecting it changes what ships, so it is one.

List every deliverable the initiative will produce, before any of them exists. Include the ones that
feel too small to matter; those are the ones that historically land by accident.

## Step 2 — Classify each deliverable: risk class + lane

**Risk class** (the taxonomy comes from a retroactive split plan for the mixed-risk PR above):

| Class | Contents |
|---|---|
| `MIGRATION` | Alembic migrations, destructive data operations, anything with a deploy hazard |
| `BACKEND` | Production runtime code and the tests that gate it |
| `TOOLING` | Scripts, CI, dev-only utilities |
| `DOCS` | Prose — split by lane below |

**Lane** — the review ceremony a deliverable earns. This is the F11 decision; the reasoning and its
sources are in `.specs/stacked-pr-skills/research-brief.md` §2.

| Lane | Contents | Ceremony |
|---|---|---|
| **R** — Reviewed | Production code, migrations, their tests, **and executable prose**: `AGENTS.md`, `CLAUDE.md`, `.claude/**`, `.cursor/**`, hooks, CI config, prompt templates, runbooks | Full review; a migration is alone in its layer with a named reviewer |
| **C** — Carried | Prose documenting a specific code change: feature README, onboarding doc, migration runbook, docstrings | **No separate PR** — rides in the code PR, because it is only verifiable against that diff |
| **J** — Journal | Narrative coordination prose: `.ai/` boards and ledgers, retrospectives, `tasks/`, `.specs/` for in-flight work | **One batched PR per initiative**, merged by the **operator** without requesting review |

**Lane follows behaviour, not path — and when path and behaviour disagree, behaviour wins.** The paths
above are examples, not the rule. The rule is: *would merging this change what an agent, a build, or
an operator does?* Then it is Lane R.

- `.ai/templates/*.md` are read at runtime by `spec-driven-dev` — path says J, behaviour says **R**.
- `docs/onboarding/**` is narrative → **C** (it documents code); an operational runbook is **R**.
- Untracked deployment artifacts never appear in a diff at all, so they have no PR lane — route
  changes to them through whatever review gate owns them, and say so in the plan.

**Executable prose is Lane R, always.** It changes what every future session does and no test catches
a wrong rule — the class can include hooks that *deny tool calls*. Treating
it as narrative is also the misclassification the "Rules File Backdoor" technique depends on, though
note that attack's scope is rule files arriving from **outside** (shared repos, templates, poisoned
PRs); the local argument stands on its own without it.

**Lane J is "no review", not Apache-style commit-then-review.** CTR works where a commit-mail channel
and binding vetoes exist; this repo has no CODEOWNERS and no announcement channel, so nobody would
see a merged journal PR in time to veto it. Call it what it is: **review skipped, risk accepted,
because a board row cannot be meaningfully rejected.** Merging is an outward action — the operator
does it, not a session (`parallel-session-safety` §10). Lane J is also not free: with no `paths:`
filter on the CI workflow, a docs-only PR still runs the full lint + typecheck + pytest job, which is
a second reason to batch.

**The load-bearing rule that follows:**

> **A Lane J layer is NEVER a base in the stack.** Journal prose goes in a sibling branch off trunk,
> never underneath code.

This is structural, not disciplinary. It makes "a comment on a changelog blocks a migration"
impossible rather than discouraged.

**Lane policy is a team decision, recorded in one column.** If the operator wants prose reviewed, the
`Lane` column changes and nothing else does. Do not re-litigate it per initiative; do surface it once
if the operator has never seen it.

## Step 3 — Decide stack vs siblings, per dependency

**Only stack changes that genuinely depend on each other.** Git Town states it directly — "Only stack
changes that depend on each other. If they don't, create them as independent top-level feature
branches" — and GitHub's own rule is that a dependency must live "in the same branch or a lower one".
`orchestrate` says the same: never force independent work into the stack.

Ask per pair: *does B fail to compile, run, or make sense without A?* If no, B is a **sibling off
trunk**, not a layer above A. Coming from the same initiative is not a dependency. Stacking
independent work imports cascade cost, merge-train coupling and force-push blast radius for nothing.

Depth is a planning input, not an outcome. The deepest stack in this repo so far was 11 PRs.

## Step 4 — Order the layers by risk

The highest-risk deliverable gets **its own layer and its own named reviewer**, positioned so nothing
lower can block it — which in practice means the **bottom**. A migration is always alone. Lane J
siblings hang off trunk.

> **In this repo, CI runs only on PRs whose BASE is `main` or `dev`.** `.github/workflows/
> test-and-deploy.yml` triggers on `pull_request`/`push` with `branches: [main, dev]`, and that
> filter matches the PR's **base**, not its head — verified 2026-08-04. So the bottom layer **and
> every sibling** get the full run; **every non-bottom stacked layer gets none.** Put the
> tested-critical work at the bottom or in a sibling, or name the covering run in the PR body
> (`gh pr checks <n>`). This is a planning input, not a detail — and it is also why a Lane J docs PR
> is not free: with no `paths:` filter, it runs the whole lint + typecheck + pytest job.

Standalone-*reviewable* is the bar, not standalone-*shippable*. Google's guidance explicitly counts
"a CL they've already reviewed" as available context, so a layer may depend on a reviewed layer below
it without being independently deployable.

**Do not reduce this to a line count.** Google's own framing is "one self-contained change", with
"100 lines is usually a reasonable size … 1000 lines is usually too large, but it's up to the
judgment of your reviewer". The layer that failed here failed on **composition — 7 mixed commit
types — not size.** A line-ceiling rule would have passed it. (The widely-quoted 200–400 LOC figures
come from a vendor marketing white paper, not peer-reviewed work; cite Google if you cite anything.)

## Step 5 — Emit the layer table

Write it to `.specs/{initiative}/topology.md` **before the first commit**. Tracked file, not a
handoff — a handoff is gitignored and would be a single copy.

```markdown
| Layer | Branch | Deliverable | Risk class | Lane | PR base | Depends on (why) | Review audience | Status |
|---|---|---|---|---|---|---|---|---|
| L1 | db/drop-question-category | The migration, alone | MIGRATION | R | dev | — | backend + DBA | planned (2026-08-04) |
| L2 | fix/feedback-aggregate | Aggregation over the new schema | BACKEND | R | db/drop-question-category | reads the dropped column | backend | planned (2026-08-04) |
| B1 | fix/transcription-retry | Retry on 5xx in the STT client | BACKEND | R | dev (sibling) | — no dependency | backend | planned (2026-08-04) |
| C1 | (rides L1) | Migration runbook | DOCS | C | — carried | documents L1's diff | backend + DBA | planned (2026-08-04) |
| S1 | docs/initiative-journal | Board rows, retro, ledger updates | DOCS | J | dev (sibling) | — | none — no review | planned (2026-08-04) |
```

Rules for the table:
- **Every deliverable from step 1 appears in exactly one row.** A deliverable in no row is the F1
  failure in miniature.
- **`Depends on (why)` must be a real compile/run dependency, stated.** An empty cell means the row is
  a sibling off trunk, not a layer. This column is what stops step 3 being skipped.
- **Lane C rows have no `PR base`** — they ride a code PR. A Lane C deliverable with *no* code PR to
  ride is not Lane C: re-classify it R or J.
- `Review audience` names *who*, not just how deep — it is what makes a depth choice checkable, and
  varying depth is only legitimate if the variance is recorded.
- `Status` is a claim with a date — write the date in the cell. See step 7. Prefer the vocabulary the
  repo's boards already use (`on a branch · parked · delegated · deployed—verify · done`).
- **Commit the file.** Writing under `.specs/` does not track it — `.specs/` is not gitignored, but a
  new file there is untracked until `git add`, and an untracked single copy is exactly F7. Verify:
  `git ls-files --error-unmatch .specs/{initiative}/topology.md` → exit 0.
- **Never write an absolute local path into this table** — a drive-letter path, or one anchored at a
  user's home directory, works for exactly one engineer. Keep paths repo-relative.

**When a clean boundary is unaffordable, record the violation — do not hide it.** The model is
that split plan's "L3 caveat, stated not hidden": one tooling commit among seven
docs commits, isolating it would require a history rewrite, accepted with the reason written down. A
plan that only permits clean tables gets abandoned at the first messy history.

**Splitting existing history? Measure shared-file overlap first.** Run
`git log --format= --name-only <base>..<tip> | sort | uniq -c | sort -rn | head`. If one file is
touched by most commits (one real case: a backlog file touched by **12 of 20**), a thematic re-split
means a conflict in nearly every layer plus invalidated review anchors. Cut the existing linear
history at commit boundaries instead — every commit stays byte-identical, nothing is rewritten.

## Step 6 — Write the re-plan triggers into the table

F6's failure was not a missing trigger *concept*. The risk was flagged **once**; the migration then
landed on that same branch — the exact moment the problem became concrete — and it was never
re-raised. The split happened two days later at the cost of a closed PR and 7 orphaned threads.

**A risk noticed once and not escalated is functionally unnoticed. A trigger that must be re-read to
fire has the same failure mode — so make them commands.**

Each trigger is a command **with an expected result** — the `parallel-session-safety` §9 contract
("preconditions and verification are commands, never prose"). Escaped pipes below are markdown table
escapes; drop the backslash when running.

| Trigger | Check | Fires when |
|---|---|---|
| Risk **classes** mixed on one layer | `git diff --name-only <base>...<layer>` piped through the four class counters below | more than one count is non-zero, or a non-zero count belongs to a class this layer was not assigned |
| A migration appeared where it does not belong | `git diff --name-only <base>...<layer> \| grep -Ei 'alembic\|migrations'` | non-empty on a layer whose class is not `MIGRATION` |
| Production code landed on a docs/tooling layer | `git diff --name-only <base>...<layer> \| grep '^backend/'` | non-empty on a `DOCS` or `TOOLING` layer |
| Branch older than ~2 days | `expr $(date +%s) - $(git log --format=%at <base>..<layer> \| tail -1)` | result > 172800 (the layer's **oldest** commit, by AUTHOR date) |
| Plan and live stack disagree | `gh stack view --json` vs the **L-rows** of this table | order or branch names differ |
| A layer stopped being reviewable alone | reviewer asks for a re-split | any such request — it is a legitimate reviewer action |

**Classify by changed PATH, never by commit type.** A commit-subject probe (`git log --format=%s …
| sort -u`, "fires when more than one type appears") reads `feat:` + `test:` on one layer as mixed
risk — but a correct BACKEND layer almost always carries both, so the trigger fires on the *healthy*
case and reopens a settled topology. Risk lives in the files a layer touches, not in the words its
author chose. The four counters, written for portability — **no `grep -P`**, whose
lookbehind/lookahead dies where `LANG` is unset ("-P supports only unibyte and UTF-8 locales"):

```bash
F=$(git diff --name-only <base>...<layer>)
MIGRATION=$(printf '%s\n' "$F" | grep -cE '^backend/app/storage/migrations/')
BACKEND=$(printf   '%s\n' "$F" | grep -E '^backend/' | grep -vcE '^backend/app/storage/migrations/')
DOCS=$(printf      '%s\n' "$F" | grep -cE '^(docs|tasks|\.specs|\.ai)/')
TOOLING=$(printf   '%s\n' "$F" | grep -cE '^(\.claude|\.cursor|scripts|tests)/')
# exactly one of these four may be non-zero, and it must be the class the layer was assigned
```

> **Three-dot for `git diff`, two-dot for `git log` — they mean opposite things here.** `git diff
> A..B` compares *endpoints*, so everything trunk gained since the fork reads as a change on your
> layer: after trunk merged an unrelated migration, the two-dot form fired both the migration and the
> production-code trigger on a docs-only layer. `A...B` diffs against the merge-base and returns only
> the layer's own work. `git log A..B` is already merge-base-relative, so it stays two-dot.

> **Author date, never committer date.** `%cr`/`%cd` are rewritten by every rebase, and this skill
> mandates cascades — a branch that has been `gh stack sync`'d reads as "0 seconds ago" no matter how
> old it is, so a `%cr` age trigger can never fire. `%at`/`%ar` survive the replay. Compare a number,
> not the prose `%ar` renders, or nothing consumes the result.

> **Use `grep -E` with a real pipe, not `grep -i a\|b`.** Under basic regex `\|` is a literal, so the
> naive form silently matches nothing and reports "no migration here" on a layer that has one. That
> failure was reproduced against the very migration this skill was written about.

> **S-rows (siblings) are not in `gh stack`.** A `gh stack` chain is strictly linear — each branch is
> based on the previous one, with no fork or sibling flag. Siblings are ordinary PRs against trunk;
> check them with `gh pr list --base dev`, and scope the drift check to L-rows or it fires every time.

Run them at every dispatch round. **Any trigger firing re-opens the topology that day** — not at the
end of the initiative, when the repair costs a closed PR.

## Step 7 — Re-verify the table against git/gh at every dispatch round

Two board rows once read `UNCOMMITTED` after their work was committed, and the error survived until a
later review pass. **A status cell is a claim with a date, not a memory.**

- **"Did this land?" — ask content, not ancestry.** Under squash-merge the original SHAs are not
  ancestors while the content is in `dev`. Three successive passes wrote "nothing is merged" from
  `git merge-base --is-ancestor` when all twelve PRs had merged. Use `git grep -l <symbol> origin/dev`.
- **Pin layers by OID, not by ancestry** — `parallel-session-safety` §10 has the six-line precondition
  block; use it verbatim rather than retyping it. Ancestry alone passes on a chain someone else
  rewrote.
- Verify the remote chain link-by-link after every push, per `.ai/git-stacked-pr-workflow.md`.

## Cross-cutting rules (all four stacked-PR skills carry these)

- **Secrets:** a credential pasted into a chat transcript is already compromised. Use it **once** to
  establish stored credentials (`gh auth login`), tell the operator to rotate, and never write it to
  a file — not even a gitignored one. Repeating "please rotate" is not a mitigation.
- **Durable vs ephemeral:** anything another session must act on lives in git or is reconstructible
  from something in git. The topology table is tracked. `.ai/tmp/` has been deleted mid-initiative
  with no copy anywhere; `.ai/handoffs/` is gitignored, so every handoff is a single copy and is a
  *pointer*, never the artifact.
- **Authorization is scoped to the action it was granted for.** A one-time "go ahead and commit" does
  not generalize — it once became ~15 commits and 12 pushes across two days, none re-authorized.
  Re-ask when the scope changes: new branch, new PR, a push after a merge-train decision.
- **Branch hygiene:** never `git symbolic-ref` to switch branches — it moves HEAD without touching
  the working tree or index and leaves all three inconsistent. Use `/branch-switch`. Run
  `git status` + `git stash list` before trusting any file; three sessions share this checkout.
- **Stage only your own hunks.** With files carrying mixed edits from several sessions, build the
  index line-by-line (`git hash-object -w` + `git update-index --cacheinfo`), leaving the working
  tree byte-identical, verified by checksum before and after.
- **A gate's verdict is its log, never its exit code.** The Docker runner has returned exit 0 around
  `1 failed, 2260 passed`.
- **Verify by CLASS, not by instance.** When checking that a finding, a fix, or a redaction is
  complete, target the finding's *category* — not the one example you already saw. A privacy
  redaction in this window was verified with the pattern of its single known instance (`user 2xxx`)
  and missed a named third party plus a re-identifying research fingerprint: both were the same
  class, neither matched the instance. Derive the sweep from 2–3 phrasings of the actual proposition
  over the whole tracked tree, and report "N named, M carried it, K found outside the list" — a list
  built by matching a *string* rather than the *claim* fails in both directions.
- **Cascades and outward actions are boundary operations** (`parallel-session-safety` §10) — user
  authorized, never mid-layer.

## Worked example — the failing layer, re-planned

**Before** (what happened): one branch, 28 commits, 7 types, migration at 17/20, one PR.
A changelog comment blocked the migration and two backend fixes.

**After** (what this skill emits, before the first commit):

| Layer | Branch | Deliverable | Risk | Lane | Base | Depends on (why) | Audience |
|---|---|---|---|---|---|---|---|
| L1 | `db/drop-question-category` | **The migration, alone** | MIGRATION | R | dev | — | backend + DBA |
| L2 | `feat/interview-conduct-core` | New detection feature | BACKEND | R | L1 | reads the new schema | backend |
| B1 | `fix/transcription-retry` | STT retry fix | BACKEND | R | dev (sibling) | — none | backend |
| B2 | `fix/feedback-non-english` | Feedback language fix | BACKEND | R | dev (sibling) | — none | backend |
| B3 | `chore/ai-infra-rules` | AGENTS.md + skills + hooks | DOCS | **R** | dev (sibling) | — none | AI-infra owner |
| S1 | `docs/initiative-journal` | Board, retro, ledger, task docs | DOCS | **J** | dev (sibling) | — none | none — no review |

Four reviewer open-and-reads of zero-production-code PRs collapse to zero.

**Note what moved.** The migration is at the **bottom**, not the middle — "its own layer, positioned
so nothing lower can block it" means nothing lower *at all*, prose or code. GitHub's own stacked-PR
guidance puts "foundational changes such as shared types and database schema" in lower branches for
the same reason. And the two unrelated backend fixes became **siblings**, because an STT retry and a
feedback aggregation have no compile-or-run dependency on the migration — stacking them would let a
change-request on the STT fix block the migration, which is F1 in a different currency.

`B3` stays Lane R because a hook that denies tool calls is executable, not narrative.

## Worked example 2 — a real run, and a re-plan trigger firing

The example above is a re-plan of a known failure. This one is an **executed** run: this skill
against its own initiative (`/skill-creation-workflow` Phase 8, on a live stacked base pinned by
OID). It is the only record of the planner producing a table in anger.


| Layer | Branch | Deliverable | Risk | Lane | Base | Audience |
|---|---|---|---|---|---|---|
| L1 | `feat/ai-stacked-pr-skills` | 4 × `SKILL.md` + the `CLAUDE.md` registration block | DOCS | **R** | dev | AI-infra owner |
| S1 | `docs/stacked-pr-skills-record` | `research-brief.md` (F11 decision record) + the topology | DOCS | **J** | dev (sibling) | none — no review |
| — | (not a deliverable) | `.ai/tmp/*.txt` gate captures | — | — | — | ephemeral, never committed |

**The re-plan trigger fired, and that is the point.** *"A new deliverable appeared"* — the brief
specified three skills; a fourth (`initiative-cleanup`) was added mid-request. The topology was
**re-planned around four from the start** rather than bolting the fourth onto whatever branch
happened to be open. That is the F6 path taken correctly, and it is the behaviour Step 7 exists to
produce. The other triggers were checked and clean: no mixed commit types, `git diff --name-only |
grep -Ei 'alembic|migrations'` empty, `grep '^backend/'` empty, branch age same-day.

## Anti-patterns

| Anti-pattern | Why it seems right | What actually happens |
|---|---|---|
| Assign the branch at commit time | The branch is right there and the change is small | 28 commits / 7 types / 1 PR, migration at 17/20 |
| One layer accumulates mixed risk | Each addition was individually small | Review attention is allocated per PR, not per risk; then the changelog blocks the migration |
| Stack independent work | It all came from one initiative | Cascade cost and merge-train coupling for zero benefit |
| Flag a risk once | It was raised; someone will act | Two days, a closed PR, 7 orphaned threads |
| Fix a topology problem later | We can re-split afterwards | Shared-file density only grows; the cheap-split window closes silently |
| Maintain the table from memory | It was right when written | Rows read `UNCOMMITTED` after the work was committed |
| Put fixes in a new top PR | A cascade is expensive | A silent merge-train dependency — see `pr-comment-resolver` |

## Related

- `.ai/git-stacked-pr-workflow.md` — every command, cascade and verification rule
- `parallel-session-safety` §9 (hand-off contract), §10 (cascade = boundary operation, layer pins)
- `orchestrate` — its plan step calls this skill (single-session scope)
- `initiative-planner` — calls this skill at its step 2; owns the charter, the session
  decomposition and the concurrency derivation that sit above this table
- `pr-review-concise` — lane drives review depth; `pr-comment-resolver` — fixes go in the owning layer
- `.specs/stacked-pr-skills/research-brief.md` — the F11 decision record and its sources
