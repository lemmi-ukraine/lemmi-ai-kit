---
name: initiative-planner
user-invocable: true
argument-hint: "[initiative name, or the problem it is meant to solve]"
when_to_use: >
  "plan this initiative", "plan this epic", "how many sessions will this take", "can any of these
  run in parallel", "how do we split this across sessions", "who has to unblock this", "what is
  the plan for the whole thing", or any body of work with more than one deliverable that will
  outlive the session currently planning it.
metadata:
  type: task
description: >
  Plan a multi-session initiative BEFORE any work starts. Establishes the level-1 charter — a PDR
  for product-shaped work, an ADR for technical — then decomposes the initiative into typed
  sessions, DERIVES how many may run concurrently instead of asserting a number, routes each
  session to a capability tier, and names the external blockers only the operator can clear. Emits
  durable artifacts under .specs/{initiative}/ that outlive every session reading them. Scope is
  the whole initiative; for one session's task use orchestrate instead.
---

# Initiative Planner — decide the shape of the whole initiative before any of it runs

## When this skill activates

- Work spans **more than one deliverable** and will **outlive the session planning it**
- The operator asks how many sessions, what runs in parallel, who unblocks what
- `orchestrate` reaches a task it cannot finish in one session
- A charter exists (`tasks/TECH-*.md`, `tasks/FEATURE-*.md`) and nobody has decided how it gets built

**Do not** activate for a single task inside one session (`orchestrate`), for one slice's
requirements/design (`spec-driven-dev`), or for the branch table alone (`stacked-pr-planner`).

## The seam: plan time vs run time

| | `initiative-planner` (this) | `orchestrate` |
|---|---|---|
| Runs | **once, before any work** | **inside one session**, every time |
| Horizon | the whole initiative | this session's task |
| Output | **durable artifacts that outlive the session** | briefs, verifications, a synthesis |
| Owns | charter → sessions → concurrency → gates → operator critical path | decompose · route to workers · verify · merge |

The distinction is **not scale**. `orchestrate` already dispatches across sessions. The test is
whether the artifact survives the session that wrote it.

## Why this exists — measured, do not soften

On **2026-08-15** a session planned an epic using `orchestrate` → `stacked-pr-planner` →
`plan-critic`. Between them those three produced a complete answer to *what ships and in which
branch*, and **no answer at all** to how many sessions the work decomposes into, which may run
concurrently, what caps that, or which blockers no session can resolve. The operator had to ask for
it after being shown a plan both skills considered complete, and the session invented the missing
layer on the spot.

The same defect one stage later is already recorded in `orchestrate` §1b: an inline-by-default epic
had **≥20 workers killed mid-wave by the usage limit across 3 sessions**, and in **2 of 3** observed
cases the *operator* initiated the move to a fresh session. Session boundaries decided reactively,
at the wall, instead of at plan time.

## What this skill emits — and the three levels it must not confuse

Three levels of document exist, and `.specs/` is **not** where the top one lives. Conflating them
is how an initiative's goals end up buried inside one slice's design doc.

| Level | Document | Where | Owner |
|---|---|---|---|
| **1 · Initiative / epic** — why this exists at all | **PDR** (product requirements) *or* **ADR** (architecture decision) — one per initiative, never both | `tasks/FEATURE-{slug}.md` (PDR) · `tasks/TECH-{slug}.md` (ADR) | step 1 below |
| **2 · Decomposition** — how the initiative is cut up | `topology.md` (what ships in which branch) | `.specs/{initiative}/` | **`stacked-pr-planner`** — do not restate its rules |
| | `roadmap.md` (phases, gates, operator critical path, risks, undecided) | `.specs/{initiative}/` | this skill, steps 6–7 · [template](references/roadmap-template.md) |
| | `execution-plan.md` (session tree, register, concurrency, routing, triggers) | `.specs/{initiative}/` | this skill, steps 3–5, 8 · [template](references/execution-plan-template.md) |
| **3 · Slice** — how one piece is built | `requirements.md` · `design.md` · `tasks.md` | `.specs/{slice}/` — **a sibling directory, never inside the initiative's** | `spec-driven-dev`, run by a Spec session |

> **Level 3 never lands in the level-2 directory.** `.specs/{initiative}/` holds only the three plan
> artifacts (plus `cleanup.md` / `forward-plan.md` from `initiative-cleanup` at the end). Each
> decomposed slice gets its **own** `.specs/{slice}/`. Four skills write into this namespace —
> `stacked-pr-planner`, this one, `spec-driven-dev`, `initiative-cleanup` — and only the directory
> name keeps their levels apart.

**Commit all four documents.** Writing under `.specs/` does not track a file — it is untracked until
staged, and an untracked single copy is the artifact this repo has lost before. Verify with
`git ls-files --error-unmatch .specs/{initiative}/roadmap.md` → exit 0. Staging is the operator's
call; say the files are ready, do not stage unasked.

## Step 0 — Is this an initiative at all?

Three questions. **All three must be yes**, or stop and hand to the cheaper skill:

1. More than one deliverable, by `stacked-pr-planner`'s test (*rejection would change what ships*)?
2. Will the work outlive the session planning it?
3. Is there at least one operator approval gate between now and done?

One "no" → `orchestrate` (one session), `spec-driven-dev` (one slice), or just do the work.
Planning overhead on work that fits in one session is pure cost.

## Step 1 — The charter: a PDR **or** an ADR

**An initiative with no falsifiable claim is a wish list with branch names.** Before decomposing
anything there must be a level-1 document stating what is believed, what it is worth, and what would
prove it wrong. **Not every initiative is product-shaped**, and starting a technical one from a
product requirements document forces it to argue in a vocabulary it does not have.

**First classify the initiative.** The test is what a *rejection* would be about:

| | **PDR** — product requirements | **ADR** — architecture decision |
|---|---|---|
| Rejection argues about | what users get, and whether it is worth building | how the system is built, and whether the trade is right |
| Typical trigger | a user-visible gap, a metric, a complaint | coupling, a failure class, cost, an unshippable constraint |
| Lands in | `tasks/FEATURE-{slug}.md` | `tasks/TECH-{slug}.md` |
| Written by | **`/product-brief`** — it owns this shape end to end | **this step**, from the template |

Pick **one**. An initiative with both has not decided what it is, and its gates will contradict each
other. If it genuinely has both faces, the product face is the initiative and the architecture
decision is a slice inside it — write the ADR at level 3, not level 1.

**Does a level-1 document already exist?**

- **Yes, under ~1 week old** → use it; fill any missing charter field from the template.
- **Yes, older than ~1 week** → **re-verify before planning on it.** These docs age in a specific
  direction: severity inflates (written at peak alarm, never re-measured) while mechanism claims go
  stale under refactors. Re-anchor every claim **by symbol** (`grep -n` the symbol now, never a line
  number the doc recorded), re-measure every frequency claim against fresh data and **state the
  window**, and record which conclusions were falsified so the next reader does not re-trust them.
  One 2026-07-30 audit of a doc in this state found **4 load-bearing conclusions false**, including
  a prescribed fix that crashes on a unique constraint; measuring inverted the priority.
- **No** → write it: [references/charter-template.md](references/charter-template.md) carries the
  shared fields plus the PDR-only and ADR-only blocks.

**Both shapes carry the same four load-bearing fields**, and `/product-brief`'s output does **not**
include three of them — its template runs Problem · Behavior · UX Content · Out of Scope ·
Implementation Notes. So on the PDR path, run `/product-brief` first, then **add the charter block**
from the template:

- **Goal** — what is true for a user when this is done. Not what gets built.
- **Hypothesis** — the causal claim, with the number it predicts moving and in which direction.
- **Expected value** — who benefits, how many, how often. A number with its source and window.
- **Falsifiers** — see step 7. The first deliverable should be able to kill the initiative.

The bar for either shape is `/product-brief`'s **Dimension 1 (Problem Strength)**: *falsifiable,
arguable, and carrying at least one concrete number*. Cite that test; do not restate it here.

**An ADR carries two more fields, and they are not decoration.** *Alternatives considered, with why
each was rejected* — an architecture decision with no rejected alternative was not a decision. And
*Consequences, split by reversibility* — what this makes easier, what it makes harder, and what
becomes **hard to undo**. That last field feeds step 5 directly: irreversibility is the first
discriminator in the tier table, so an ADR that names its one-way doors has already routed its own
riskiest sessions.

### 1.1 Reconcile prior work BEFORE decomposing anything

Two questions, asked of the problem and not of the document:

1. **What has already shipped against this problem?**
2. **Was its effect ever measured?**

Ask them with `git log`/`git grep` against the *problem's* symbols, not by reading the charter's
status column — a board row is a claim, and one in this repo read `TODO` a full month after its work
had shipped. The single largest finding of the 2026-08-15 initiative was **16 content fixes deployed
2026-07-27 that were never validated**; the plan had been written without them and had to be
reordered around them after the fact.

A plan that does not know what already shipped will re-solve it, and the re-solution will look like
progress. **"Already shipped but never measured" is its own deliverable** — usually the cheapest one,
and often the one that makes the rest unnecessary.

### 1.2 Hunt inherited framing in the source document

A charter inherits its parent's categories **silently**. One sentence carried in from an earlier doc
can narrow the whole initiative before anyone examines it.

The 2026-08-15 case: the source document asserted that behavioural feedback *"genuinely goes deep."*
That single clause had narrowed a whole-rubric defect into a defect affecting 12.7% of rows, and it
propagated through **five downstream sections**. One measurement refuted it — **48/48 versus 0/48**
on substance vocabulary.

So, for every load-bearing categorical claim in the source: **is it measured, or inherited?** List
the claims that scope the initiative, and mark each `measured (window, n)` or `inherited — unverified`.
An inherited claim is not wrong; it is *untested*, and it is doing structural work either way.

## Step 2 — Deliverables and the branch table → `stacked-pr-planner`

Run it. **Do not restate risk classes, review lanes, the layer table, or the rule that a migration
goes alone at the bottom** — that skill owns all of it, and duplicating it here creates two tables
that will disagree. Come back with `topology.md` written.

Two of its outputs are inputs here: the **deliverable list** (step 3 partitions it into sessions)
and the **layer table** (step 4 reads its file sets for overlap).

## Step 3 — Decompose into sessions

> **Layers are not sessions.** A layer is a *review surface* — one branch, one PR. A session is a
> unit of *context and approval*. One session may produce two consecutive layers; **one layer never
> spans two sessions.**

Six default types. A name alone is useless, so each carries what it consumes and emits, the shape
of its done, and whether it writes to the tree — the last of which decides whether it can run
concurrently at all.

| Type | Consumes → emits | Done when | Writes tree? | Skill |
|---|---|---|---|---|
| **Research** | a question + a corpus → a claim with evidence in `.ai/handoffs/` | the claim is stated with its window and sample size; **UNKNOWN is a valid result** | no | — / `parallel-deep-research` |
| **Spec** | an approved charter row + research claims → `.specs/{slice}/` | the **operator approved at the gate**; `plan-critic` ran first | `.specs/` only | `spec-driven-dev` |
| **Implementation** | an approved spec + one topology row → one branch | the layer's gate passes **and** the AGENTS.md task-completion checklist ran | its declared set | — |
| **Review** | committed work + a base ref → findings with owners | **every finding has an owner and a verdict**; "found nothing" is a valid result | no | `branch-diff-review` (no PR yet) · `pr-review-concise` (PR exists) |
| **Resolve** | review findings → fixes in the branch that **owns** the code | every comment has a verdict with evidence; the cascade is handed back to the operator | the owning branch | `pr-comment-resolver` |
| **Clean Up** | the settled board → forward plan, retired specs | every row settled by `git grep`, deletions partitioned tracked vs untracked | broad | `initiative-cleanup` |

### Every session ends the same way: post-task-review, **then** the handoff

Whatever its type, a session's last two acts are fixed and **ordered**:

1. **`post-task-review`** — the AGENTS.md task-completion checklist (code/artifact review, doc
   impact, learnings extraction).
2. **Then** write `.ai/handoffs/{date}-{slug}.md`.

**The order is the whole point.** The handoff is the only thing the next session reads, so a handoff
written first carries whatever the review would have corrected — and the next session inherits it as
fact. Measured on 2026-08-15 in the session that built this skill: the result handoff was written
before the review, shipped a false gate claim ("two review phases ran" when the gate had covered 2 of
4 artifacts and emitted no report) and two stale counts, and both had to be patched afterwards. The
review had found them; the handoff was simply already written.

A session that runs out of usage window mid-task is the one exception, and it inverts deliberately:
write a **continuation** handoff immediately, marked `Status: incomplete — post-task-review not run`,
so the next session knows the claims inside it are unreviewed.

> **Research sessions: reading your own side of a contract cannot establish what the other side
> populates.** A pass-through model proves the *keys* flow; it never proves the *values* are there.
> On 2026-08-15 the claim "the resume already carries seniority into the prompt" was asserted twice
> from this repo's own pass-through model — and written to memory — before the owning codebase
> refuted it: the field is `null` on every parsed record. A Research session's definition of done
> must name **which side of the boundary** its evidence came from, and a claim about what an upstream
> system *sends* is UNKNOWN until it is read from that system's data or its code.

**Resolve is a session type because a plan that omits it silently assumes reviews find nothing.**
The 2026-08-15 worked plan ran three Review sessions plus a re-measurement and a Clean Up, and **no
row owned fixing what the reviews found** — while `orchestrate` §3 names `pr-comment-resolver`
non-optional. Budget it explicitly; findings with no owning session are findings that die in a
report.

**Review before Clean Up, never after.** Clean Up settles the board and retires specs; running it
before findings are resolved retires the specs that document what still needs fixing.

**Escape hatch — do not deform the work to fit the taxonomy.** If a session does not fit a type,
**name it and say why in one line.** Two shapes recur: a session labelled Review that is really a
measurement (it produces numbers, not findings), and a Review that is mostly Research (it must first
establish what "correct" means). Both are legitimate; a taxonomy that forces them into the wrong box
loses the reason they were scheduled.

**When a session must work a branch it does not have checked out, the brief names `/branch-switch`
— never a raw checkout.** That skill is model-invocable and carries a mandatory pre-switch backup
gate; a raw `git checkout` across a contended tree is where work disappears.

## Step 4 — Derive the concurrency cap. Never assert it.

**A concurrency number with no derivation is a guess wearing a table.** Three independent
constraints produce it, and the cap is the *minimum* of the three:

**1. Declared disjoint file sets.** Parallel sessions need file sets that do not overlap — **never a
new git worktree** (standing operator rule; `parallel-session-safety` §11). Overlap means
*sequential*, not "be careful". Read the file sets straight out of `topology.md`.

**2. Chokepoint analysis — the step no other skill performs.** Find the single file or resource
several workstreams must edit. It reshapes the schedule more than any other input.

```bash
# Existing history: which file do most commits touch?
git log --format= --name-only <base>..<tip> | sort | uniq -c | sort -rn | head

# Planned work: does one file host the symbols two workstreams both need?
git grep -n "<symbolA>\|<symbolB>" -- backend/
```

In the 2026-08-15 plan, one 608-line prompt builder hosted **both** stage builders that two separate
stacks needed. That single fact forbade the two stacks from running concurrently — and once seen, the
schedule was reordered to run the second stack *during the spec phase*, when the file was free. The
payoff was a full serial stack saved and the conflict made **impossible rather than managed**. Look
for this before writing any number.

**3. The usage window.** Preflight the usage guard before any wave of ≥3 sessions. Past the warn
threshold, do not start the wave: checkpoint continuation notes first. A wave that dies at the wall
costs re-dispatch **plus duplicate-dispatch races** — every resume message must state who else is on
the item.

Write the cap with all three derivations visible. If a reader cannot see *why* the number is 3, the
number will be ignored the first time it is inconvenient.

## Step 5 — Route each session: tier first, then where it runs

**Tier, not model name.** Two reasons, stated here so the next reader does not re-add model names
per row:

- **A cross-session peer inherits the operator's session model.** This skill can *recommend*; it
  cannot set. Only native subagents accept an override (`Agent` tool `model:`). In the 2026-08-15
  plan that was **3 of 23 rows** — so a per-row model column would have been advisory on 20 of them.
- **Model names rot.** A skill naming today's models needs an edit at every release.

> ### The tier table — the ONE place to edit when a model ships
>
> | Tier | `Agent` alias | Today | Choose it when |
> |---|---|---|---|
> | `judgment` | `opus` | Opus 5 | the output is a **verdict** someone acts on; irreversible; security- or data-relevant; the spec left a decision open |
> | `mechanical` | `sonnet` | Sonnet 5 | **a gate the session runs itself** catches a wrong answer — pytest, ruff, basedpyright, a coverage gate |
> | `breadth` | `haiku` | Haiku 4.5 | the output is an **enumeration** — a file list, call sites, an inventory — not a verdict |

**The discriminator, applied in order:** *Is the output a list or a verdict?* List → `breadth`.
*Would a gate the session runs itself catch it wrong?* Yes → `mechanical`. Otherwise → `judgment`.

**Effort is a second dial, independent of tier.** `low · medium · high · xhigh · max`, verified in
`--help` on CLI 2.1.224. Tier picks *which model*; effort picks *how hard it thinks*, and the two do
not move together — a `judgment` session doing a routine review is `high`, while a session whose
entire job is to **refute** a claim earns `max` regardless of how small it is. Record it per row.

> **Set effort with the `--effort` flag.** It is a first-class CLI flag with a validated enum. A
> plan that routes effort through a `/effort` slash command inside the prompt string is working
> around a limitation that does not exist on this version — the slash-command route survives only
> because the **`Agent` tool** has no effort parameter, so it remains the fallback for *native
> subagents*, not for spawned CLI sessions.

Two corrections this encodes, both against the obvious mapping:

- **"Read-only" is not a tier.** Research sessions are read-only *and* can be the highest-judgment
  work in the initiative — the 2026-08-15 plan's cheapest read-only session was the one that could
  **redirect the entire initiative**. The axis is the output's shape, not the session's write access.
- **"Implementation of an approved spec → mechanical" is only true when the spec closed every
  decision.** Where a spec records constraints as *"hard constraints, not design options"*, it is
  saying an implementer would otherwise get them wrong — that is `judgment`, approved spec or not.

**Then decide where it runs.** Probe availability once per session (`command -v codex cursor-agent
grok`) and route only to what exists. The roster, the brief contract, and dispatch mechanics belong
to `orchestrate` and `agent-delegate` — cite them, do not restate. Record per row only: **tier**,
**effort**, **execution mode**, **worker class**, and the **declared file set**.

### 5.1 Four dispatch decisions — detail in [references/dispatch-economics.md](references/dispatch-economics.md)

1. **Execution mode: unattended or operator-driven.** The dividing line is **write access to the
   shared tree** — *not* judgement density and *not* whether the output gets reviewed. A one-line
   edit to a shared file needs no review and is still unsafe unattended; a judgement-heavy read-only
   analysis is safe unattended and still gets fully checked. Anything that must stop at a gate is
   operator-driven by definition — there is nobody there to approve.
2. **Enforce constraints by tool grant, not instruction.** A withheld tool cannot be used; an
   instruction can be forgotten (measured base rate: **5 of 6** audited sub-agents violated a stated
   rule in one window). Withhold `Agent` from anything that should not fan out, and withhold
   `Bash(git commit|push|checkout|stash *)` from every unattended session.
3. **Nesting only where fan-out earns it.** The binding limit is **verification distance**, not the
   platform's 3 layers / 20 concurrent: a summary of a summary cannot be checked against its sources.
4. **Per-launch context cost is a planning input.** A spawned session pays its whole startup context
   before doing any work — **82,966 tokens / $0.50** at full context on this repo, against **62,684 /
   $0.19** for a reduced-context launch (measured 2026-08-15, CLI 2.1.224). Startup differs by model
   and cost does not track context: opus loads 13.7% *less* and costs 43% *more*. **Budget the
   fan-out before approving it, and re-measure rather than citing the table** — it grows with every
   skill added.

## Step 6 — The operator critical path

External blockers **no session can resolve**: a data export, prod access, a credential, a
third-party answer. Distinct from a dependency between deliverables — that belongs in `topology.md`.

**Order by leverage, not by phase.** In the 2026-08-15 plan the highest-value entry in the whole
document was a single dev data export, because it could collapse the largest lane from a cross-team
project to a typed-contract change. It was not first in any phase.

Each entry states three things, and the third is the one usually skipped:

1. **The ask, in operator-plain language.** Self-contained — the operator must be able to answer it
   without holding the whole board in their head. The measured failure is questions "written for a
   reader who already had the whole board in their head", answered with *"i do not understand"* in
   ≥5 sessions.
2. **What it unblocks.**
3. **What becomes UNKNOWN without it** — *not* what we would assume instead. An assumption recorded
   in place of a blocker is how a missing fact becomes load-bearing in nine documents.

## Step 7 — Phases, gates, risks, and the minimal initiative → `roadmap.md`

**A gate is a decision the operator makes on evidence, not a checkpoint the planner clears.** Name
what is presented at each gate and what decision it forces.

**Falsifier-first.** The first deliverable should be able to **kill the initiative**. State each
falsifier with the verdict it forces if it holds — including "re-file this against another backlog".
An initiative whose own first measurement cannot change its direction is not being measured.

**Present the minimal viable initiative as a first-class option**, so the operator chooses **UP**
from the smallest scope that plausibly moves the metric rather than **DOWN** from the elaborate plan.
Name which deliverables are elective, and make the gate approve them explicitly rather than inherit
them. This is `plan-critic`'s minimal-viable rule applied at initiative scale.

**Risk register:** one row per risk, with severity and the mitigation that is already in the plan.
A risk whose mitigation is "be careful" is not mitigated.

**Record what is NOT decided.** A plan that hides its open questions gets them decided by whoever
commits first.

## Step 7b — Two ways an initiative's own documents mislead the session reading them

Both measured inside one initiative, and neither is a documentation-quality problem you can fix by
writing more carefully — they are properties of a doc *set* that has been revised.

**A layer's dispatch brief is silent on cross-layer sequencing, and silence is not clearance.** A
brief for validating one layer treated *"push and deploy"* as a next step gated only on the
operator's say-so. A same-day orchestration doc — written by a different, orchestration-level
session — showed that layer was one of a sequential chain merging as **one bottom-up train**
after the remaining layer, review and resolve were all done: *"must not be left half-run."* The layer
brief was internally correct and complete about its own scope, and simply had no reason to restate
sequencing that lives elsewhere.

> Before treating "deploy this branch" as ready in a multi-layer initiative, open
> `.specs/{initiative}/topology.md` or the orchestration session's own wave handoff and confirm the
> sibling layers plus review and resolve are also done.

**A short label (B1, L2, I-6) means different things in different documents of the same set.**
One document's board used "B1" for one branch while another's own row **locally reused** "B1"/"B4"
for a completely different pair — resolvable only from that row's plain-English text and an
independent grouping on the board. A superseded plan marked *"never executed"* added a **third**
numbering on top. A bare `grep` for "B1" surfaces every referent with nothing to disambiguate them.

> Never trust a short label in isolation across a `.specs/{initiative}/` set that has been through
> multiple planning revisions. Cross-check against a status board carrying **concrete branch names**,
> or a plain-English restatement. Treat a label reused *locally* within one row or table as a
> distinct scope from the same label on an outer board. Superseded plans are a live source of stale
> colliding labels — consult them **last**, not first-found-by-grep.

## Step 8 — Re-plan triggers and status re-verification

**A 23-row session register nobody re-opens is fiction by wave 3.** Two rules, both mirroring
`stacked-pr-planner` steps 6–7 rather than re-deriving them:

- **Triggers are commands with expected results, run at every wave boundary** — not prose to be
  re-read. A risk noticed once and not escalated is functionally unnoticed, and a trigger that must
  be re-read to fire has the same failure mode.
- **Status cells are claims with dates.** "Did this land?" asks **content, not ancestry**:
  `git grep -l <symbol> origin/dev`. Ancestry answers a different question after a squash-merge and
  produced **three consecutive false "nothing is merged" verdicts** in this repo.

Session-plan triggers worth carrying in every initiative:

| Trigger | Fires when | Response |
|---|---|---|
| A falsifier held | the killing measurement came back | Re-open the charter *that day*; the session count is now wrong |
| Two sessions report editing the same file | any overlap outside a declared set | Stop the later one and re-partition. Do not "merge carefully" |
| A new deliverable appeared | anything not in `topology.md` | Re-run `stacked-pr-planner`, then re-derive the cap (step 4) |
| A wave would start below the usage floor | preflight fails | Checkpoint continuation notes; do not start the wave |
| A blocker in step 6 went unanswered a full wave | check the dates | Re-state what is UNKNOWN because of it; do not silently assume |

**After a re-plan, mark the superseded sections explicitly — in the same edit.** A plan that
contradicts itself in git is worse than either version of it, because a later reader cannot tell
which half is live and will pick by proximity. Two re-plans in one day on 2026-08-15 left §1.1 and §4
contradicting §§3.1–3.3 until banners were added. Write the banner into the superseded section
itself (`> **SUPERSEDED 2026-08-15 by §N** — kept for the reasoning, not the plan`), never only into
the new one: the reader who lands on the stale section is exactly the one who will not see a note
filed elsewhere. Deleting is also allowed; leaving both unmarked is not.

> **State this in the plan, verbatim: session counts are a decomposition, not an estimate.** They
> say how the work partitions into contexts and approvals. They say **nothing** about duration, and
> a reader who takes them as a schedule will be wrong in both directions.

## Before presenting

1. Run **`plan-critic`** over the artifacts (AGENTS.md requires it before *any* plan is presented).
   Resolve Blockers and Majors silently; surface anything needing operator input at the top.
   **Then run the inheritance check yourself, because `plan-critic` does not.** On 2026-08-15 it ran
   and missed all three scope gaps the operator later found — prior work, substance-vs-delivery, and
   an already-fixed row — because each was an *unexamined inheritance* rather than an internal
   inconsistency, and a consistency checker cannot see a premise every section shares. Ask directly:
   **which claims did this plan inherit rather than measure** (step 1.2), and **what already shipped
   against this problem** (step 1.1)? A plan can be perfectly self-consistent and scoped by a
   sentence nobody checked.
2. Confirm every deliverable from step 2 appears in exactly one session row.
3. Confirm the concurrency cap shows its three derivations.
4. Say the artifacts are ready to commit. **Do not stage them** — staging is the operator's call,
   and this tree is routinely multi-session.

## Related — cited, never restated

- `stacked-pr-planner` — deliverables, risk classes, lanes, the layer table, re-plan triggers
- `orchestrate` — the run-time half: worker roster, brief contract, dispatch, verification, synthesis
- `agent-delegate` — the dispatch-brief contract for one delegated task
- `parallel-session-safety` §9–§11 — handoff schema, boundary operations, the no-worktree rule
- `spec-driven-dev` — how a Spec session authors its documents
- `branch-diff-review` · `pr-review-concise` · `pr-comment-resolver` — Review and Resolve sessions
- `initiative-cleanup` — the Clean Up session
- `product-brief` — product-shaped charters, and the Problem-Strength test step 1 borrows
- `.ai/git-stacked-pr-workflow.md` — every branch mechanic this skill deliberately omits
