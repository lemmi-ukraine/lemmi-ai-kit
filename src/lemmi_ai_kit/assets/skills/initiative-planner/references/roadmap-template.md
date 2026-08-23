# Roadmap template — `.specs/{initiative}/roadmap.md`

Phases, gates, the operator's critical path, risks, and what is not decided. **Companion to
`topology.md`** (what ships in which branch, owned by `stacked-pr-planner`) and
`execution-plan.md` (how many sessions, which run together).

---

## Skeleton — copy this

```markdown
# Roadmap — {Initiative}

**Charter:** tasks/TECH-{slug}.md    **Topology:** topology.md    **Sessions:** execution-plan.md
**Planned:** {YYYY-MM-DD}, before the first commit.   **Trunk:** {dev}

## 1. Goal, falsifiers, definition of done

{One paragraph from the charter — do not re-derive it. Link, then state the falsifier table
and the numbered definition of done so a gate can be run from this file alone.}

### 1.1 The minimal viable initiative — choose UP from this

{The smallest subset that plausibly moves the metric. Name the elective deliverables.}

### 1.2 Measurement methodology

{Only if the initiative builds the instrument that later certifies it. See "Circular evidence".}

## 2. Constraints in force

| Constraint | Consequence for this plan |
|---|---|

## 3. Operator critical path — ordered by LEVERAGE, not by phase

### OP-{n} — {ask in plain language}  ⚠ blocks {what}

**Ask:** {self-contained, answerable without holding the board in your head}
**Unblocks:** {which deliverables}
**UNKNOWN without it:** {what stays unknowable — NOT what we would assume instead}

## 4. Phases and gates

### Phase {n} — {name}

| Work | Row | Routing | Blocked by |
|---|---|---|---|

**Gate {X}.** Present: {evidence}. Operator decides: {the actual choices}.

## 5. Delegation contract

{What every brief in this initiative carries. Cite agent-delegate / orchestrate; do not restate.}

## 5.1 Testing and rollback — per risk class

{Per risk class from topology.md. Rows with no test suite need an explicit rollback path.}

## 6. Risk register

| Risk | Severity | Mitigation |
|---|---|---|

## 7. What has NOT been decided

{Each with the gate that decides it.}
```

---

## Structure description

### §2 Constraints in force
Facts about the environment that change the plan — not general good practice. A constraint belongs
here only if removing it would change a decision in this document. Each row states the
**consequence**, because a constraint with no consequence is trivia.

Recurring ones in this repo: a shared multi-session checkout (declared disjoint file sets, never a
new worktree); untracked deployment artifacts that never appear in a diff (no PR lane, no automatic
regression catch); external CLI workers absent from PATH; the usage window.

### §3 Operator critical path
**External blockers no session can resolve.** A dependency between two deliverables is not one —
that lives in `topology.md`.

**Order by leverage.** The highest-value ask is frequently not in the first phase: it is the one that
could collapse a lane from a cross-team project to a typed-contract change, and it should be asked
first regardless of when its phase runs.

Each entry's third field is the one usually skipped: **what becomes UNKNOWN without it.** Not what we
would assume instead. An assumption written where a blocker belongs reframes a *retrievable* fact as
a property of the world, and every later pass then spends its care on the inference instead of on
retrieving the fact — one such claim became load-bearing in nine documents before one API call
settled it.

Write the ask so the operator can answer it cold. The measured failure is questions written for a
reader who already had the whole board in their head, answered with *"i do not understand"*.

### §4 Phases and gates
> **A gate is a decision the operator makes on evidence, not a checkpoint the planner clears.**

Each gate names: what is **presented**, and what the operator actually **decides** — as choices, not
as "approve/reject". A gate whose only options are proceed or stop is a status update.

Put the falsifying measurement in the first phase. If the earliest gate cannot change the
initiative's direction, the phases are ordered for comfort rather than for information.

### §5 Delegation contract
State what every brief carries; **cite** `agent-delegate` and `orchestrate` for the contract itself.
The two lines worth repeating per initiative, because they are initiative-specific:

- **Preconditions are commands with expected results, never prose.** A prose state claim in a brief
  you author is the same defect as trusting one you receive — and has already shipped false.
- **Results are claims.** Read the returned diff and run the definition-of-done check yourself. Where
  a returned finding contradicts a recorded learning, the learning wins until the contradiction is
  reproduced in the shape this codebase actually uses.
- **The completion checklist runs BEFORE the handoff is written.** Every brief states this
  explicitly. A handoff written first carries whatever the review would have corrected, and it is
  the only artifact the next session reads — so the error propagates as fact rather than as a
  claim. A session stopped by the usage wall inverts this on purpose: continuation handoff first,
  marked `Status: incomplete — post-task-review not run`.

### §5.1 Testing and rollback
Per risk class. The class that matters most is the one with **no test suite and no code review** —
deployment artifacts, prompt trees, anything not in a diff. Those need their rollback path written
**before** the first upload: capture the current state somewhere durable (not a temp directory that
has been deleted mid-initiative, not a single gitignored copy), state what a rollback restores to,
and ship one deployable unit at a time so a regression stays bisectable.

### §6 Risk register
Severity plus a mitigation **already present in the plan**. "Be careful" is not a mitigation; "the
coverage gate blocks the merge" is. If a risk's mitigation does not correspond to a deliverable or a
gate, either add the deliverable or accept the risk explicitly.

Two risk classes this repo keeps rediscovering:

- **Circular evidence** — the initiative builds the instrument that later certifies its own success.
  Instances the instrument misses can never contradict it. Mitigate with a paired base rate, a second
  independently-built detector reconciled as a union, and instrument-vs-judge agreement established
  **at baseline**, not first attempted at the end.
- **A sequencing trap** — shipping A before B makes some users strictly worse off. Enforce it
  mechanically with a gate, never by remembering.

### §7 What has NOT been decided
Every open question with the gate that closes it. Include conflicts between the plan and a standing
rule or a stated non-goal — **record the violation, do not hide it.** A plan that only permits clean
answers gets abandoned at the first messy one.
