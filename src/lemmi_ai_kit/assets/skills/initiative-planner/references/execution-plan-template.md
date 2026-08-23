# Execution plan template — `.specs/{initiative}/execution-plan.md`

**The document that answers: how many sessions, of what type, and which can run at the same time.**
Companion to `topology.md` (what ships, in which branch) and `roadmap.md` (phases, gates,
operator asks).

> **Layers are not sessions.** A layer is a review surface — one branch, one PR. A session is a unit
> of context and approval. One session may produce two consecutive layers; **one layer never spans
> two sessions.**

---

## Skeleton — copy this

```markdown
# Execution plan — sessions, types, and parallelism

## 1. Headline numbers

| | Full initiative | Minimal initiative (roadmap §1.1) |
|---|---|---|
| Research | | |
| Spec | | |
| Implementation | | |
| Review | | |
| Resolve | | |
| Clean Up | | |
| **Total** | | |
| **Max concurrent** | | |

**Max concurrency is {N}, and it is a correctness limit, not a resource limit.** Record it as
**`derived {N} / dispatched {M}`** and, when `M < N`, name the contended file that forced the
serialization — concurrency is otherwise re-derived per session and collapses to serial under
uncertainty, which is invisible unless the plan carries both numbers. Derived from:
1. {disjoint-file-set constraint}
2. {the chokepoint}
3. {the usage window}

## 2. The session tree

{ASCII tree: waves, what is parallel inside each, gates as full-width bars between them.
Mark the cheapest unblocked session START HERE and the highest-value one.}

## 3. Session register

`Owns` is the **declared disjoint file set** — the parallel-safety contract. A session touching a
path outside its set is a collision, not initiative.

### {Type} — {count}

| ID | Does / question it answers | Owns | Tier | Where | Dispatch | Blocked by |
|---|---|---|---|---|---|---|

**`Dispatch` is REQUIRED and its vocabulary is closed: `auto` | `headless` | `pasted`.**
It is the one field that makes two measured failures countable instead of archaeological:
**56 of 129 sessions (43%) opened with a hand-pasted brief**, and a headless-launch capability
that one orchestrator used 7 times was used 0 times by the next because it lived only in that
session's context. Recovering those numbers took a 129-session transcript sweep; with this
column a plan states its own dispatch profile up front and
`grep -c 'pasted' execution-plan.md` re-measures it in one command.

- `pasted` is the **fallback**, not the default — justify each one in the row's `Blocked by`
  cell ("needs the operator's own approval loop"), because an unjustified `pasted` row is the
  43% reproducing itself.
- `headless` requires the launcher in `orchestrate` §2a; if you invent a dispatch mechanism
  mid-initiative, write it into that skill **before** the orchestrator handoff or it dies there.

## 4. Why the schedule is ordered this way

{Only the non-obvious reorderings, with the naive schedule beside the planned one.}

## 5. Where sessions run

| Session class | Where | Why |
|---|---|---|

## 6. Re-plan triggers for THIS document

| Trigger | Check (a command) | Fires when | Response |
|---|---|---|---|

## 7. Honest limits of this plan
```

---

## Structure description

### §1 Headline numbers
Both columns — full and minimal — or the operator cannot choose UP from the minimal scope. The
minimal column is not a smaller version of the plan; it is a **different decomposition**, usually
with whole session types missing.

**Every number is a decomposition, not an estimate.** Say so in this section, verbatim: they describe
how work partitions into contexts and approvals, and say nothing about duration. Readers take
counts as schedules unless told not to.

### §2 The session tree
The tree is the artifact people actually read. Make it carry four things text tables cannot:

- **Waves** — what may start at the same time.
- **Gates** — full-width bars, so it is visually impossible to read past one.
- **Blockers** — annotate each session with what it waits on (`needs OP-2`, `needs Gate A`).
- **Entry points** — mark the cheapest unblocked session (`← START HERE`) and the one with the most
  leverage (`← HIGHEST VALUE`). They are rarely the same session, and the difference is a decision.

### §3 Session register
One row per session. **`Owns` is a contract, not a description** — it is what makes concurrent
sessions safe, and it is checkable after the fact. A session whose `Owns` cell says "the feedback
feature" cannot be verified against; one that names files can.

The six types and what each row means are in `SKILL.md` step 3. Group rows by type — it makes an
absent type obvious, which is how a missing **Resolve** session gets caught at plan time instead of
after three reviews have produced findings nobody owns.

Add a one-line `>` note under any row that is **deliberately not parallel** with its sibling, with
the reason. Without it, a later reader "optimises" the schedule by running them together, and the
reason the split existed is not recoverable from the table.

Where a session does not fit a type, **name it and say why in one line.** Do not deform the work to
fit the taxonomy.

### §4 Why the schedule is ordered this way
Only the reorderings a reader would otherwise undo. Show the naive schedule next to the planned one
and name what the difference buys:

```
NAIVE                          PLANNED
spec everything                spec A ∥ spec B ∥ implement C   ← C's file is free NOW
then implement everything      then implement A                ← the conflict never happens
  ↑ both stacks contend
    on the same file
```

A chokepoint discovered at plan time is **designed around**; discovered at dispatch time it is
**managed**, which costs a serial stack and a merge conflict in every layer.

### §5 Where sessions run
Per class, not per row. What belongs here:

- **Native subagent** — read-only, bounded, needs no approval loop of its own. Accepts a model
  override, so its tier is real rather than advisory.
- **Cross-session peer** — owns a branch, or needs its own context window and its own approval loop.
  **It is not a tool call:** a brief goes out, the result returns as `.ai/handoffs/{date}-{slug}.md`.
  It cannot be spawned and cannot be awaited. It **inherits the operator's session model**, so the
  tier column is a recommendation.
- **External CLI worker** — only if `command -v` found it this session. Probe, do not assume.

State once here what every brief carries (the delegation contract lives in `roadmap.md` §5), and
that a session needing a branch it does not have checked out uses `/branch-switch` with its
pre-switch backup — never a raw checkout in a contended tree.

### §6 Re-plan triggers
**Commands with expected results, run at every wave boundary** — not prose to be re-read. A trigger
that must be remembered has already failed. `topology.md` carries the branch-shaped triggers; these
are the session-shaped ones:

| Trigger | Check | Response |
|---|---|---|
| A falsifier held | the measuring deliverable reported | Re-open the charter that day; the session count is now wrong |
| Two sessions editing the same file | either reports a path outside its `Owns` | Stop the later one; re-partition. Not "merge carefully" |
| A new deliverable appeared | `topology.md` has no row for it | Re-run `stacked-pr-planner`, then re-derive §1's cap |
| A wave would start below the usage floor | preflight the usage guard | Checkpoint continuation notes; do not start the wave |
| A blocker went a full wave unanswered | dates in `roadmap.md` §3 | Re-state what is UNKNOWN because of it; do not silently assume |
| Status claim needs settling | `git grep -l <symbol> origin/dev` | Content, **never** ancestry — ancestry answers a different question after a squash-merge |

### §7 Honest limits
Three things to state plainly, because a plan that hides them gets over-trusted:

1. **Counts are a decomposition, not an estimate.**
2. **Late waves are planned against specs that do not exist yet.** Say which parts are expected to
   change (the layer contents) and which should survive (the shape — how many stacks, where the
   chokepoint is, which trees are disjoint).
3. **What still blocks dispatch**, with the gate that clears it.
