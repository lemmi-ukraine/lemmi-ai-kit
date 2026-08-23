---
name: spec-driven-dev
metadata:
  type: workflow
description: >
  Spec-driven development pipeline for medium and large tasks. Auto-detects task size
  based on scope analysis, then guides creation of requirements, design, task decomposition,
  and verification-plan documents before implementation begins. Use when starting a new feature,
  significant refactoring, or any task that touches multiple files or features. Creates
  specs in .specs/{task-name}/ directory.
---

# Spec-Driven Development Pipeline

## When This Skill Activates

> **Tip:** For raw product ideas that need shaping (assumption-challenging, UX content,
> team-readable task descriptions), run `/product-brief` first. It produces a
> `tasks/FEATURE-*.md` file that feeds naturally into this pipeline.

Activate at the start of any task that involves:

- Implementing a new feature or significant functionality
- Refactoring that will touch multiple files across layers
- Adding new API endpoints with service and storage layers
- Architectural changes or new integration points
- Any request where the scope is ambiguous or large

Do NOT activate for:

- Simple bug fixes in a single file
- Adding a comment, logging, or renaming
- Documentation-only updates
- **Pure value-only configuration**: numeric threshold or timeout change in a single feature,
  no behavioral mode change (e.g., raising silence_duration_ms from 3000 to 3500, tightening
  a rate limit). These are not architectural decisions.

**Configuration changes that ARE subject to spec classification** (do not exempt these):
- Changing the *default mode* of an AI provider integration (e.g., switching VAD type,
  changing audio model, toggling a behavior flag whose description says "architectural").
- Adding a new session parameter to a shared protocol that multiple features must implement.
- Any configuration change that touches 2+ features or a shared cross-feature protocol
  (e.g., a realtime session config protocol).

## Task Size Auto-Detection

Before starting implementation, analyze the task to classify its size.

### Detection Heuristics

Evaluate each dimension and score:

| Dimension | Small (0) | Medium (1) | Large (2) |
|-----------|-----------|------------|-----------|
| **Files to create/modify** | 1–3 | 4–10 | 10+ |
| **Features involved** | 1 existing | 1 with new components | 2+ features |
| **DB migrations needed** | No | Simple add column/table | Complex schema change |
| **New API endpoints** | 0 | 1–2 | 3+ |
| **Cross-feature communication** | None | Reads from another feature | New integration |
| **Architectural decisions** | None | Minor (pattern choice) | Major (new pattern) |

**Classification:**
- Total score 0–2 → **Small** — direct implementation, no spec needed
- Total score 3–6 → **Medium** — lightweight spec (single combined document)
- Total score 7+ → **Large** — full spec (requirements + design + tasks)

See [references/size-detection.md](references/size-detection.md) for detailed examples.

### Present Classification

After detection, present the classification to the user:

```
Task size: {SMALL | MEDIUM | LARGE}
Rationale: {1-2 sentences explaining the score}
Proceeding with: {direct implementation | lightweight spec + tasks | full spec}
```

If the user disagrees, accept their override without argument.

## Step 1.5 — External Dependency Research (when applicable)

Before writing any spec document, if the task involves integrating **new external services
or AI providers**, perform upfront research:

1. For each new external provider: fetch official API docs, verify SDK method signatures
   against source, document capabilities and constraints.
2. Verify SDK parameter names against the actual SDK source — parameter names change between
   versions (e.g., `speech_model` vs `speech_models`).
3. Document findings as notes for the spec, not assumptions.
4. If multiple providers serve the same capability, force an explicit **Multi-Provider Strategy**
   decision: single active provider (config-switchable), fallback chain, A/B test, or parallel
   comparison. Default to the simplest model (single active) unless the user escalates complexity.

Skip this step if the task uses only providers already integrated in the codebase.

## Step 1.6 — Ambiguity Scan (Medium and Large tasks only)

Before writing any spec document, scan for blocking ambiguities.
Skip this step entirely for Small tasks.

Ask at most **2 clarifying questions** to the user when **any** of these triggers apply:

| Trigger | Example |
|---|---|
| Multiple architecturally distinct solutions exist | REST vs WebSocket, sync vs async |
| A requirement states a goal without specifying constraints | "improve performance" — what target or SLA? |
| An existing interface is touched and backward compatibility is unclear | "update endpoint X" — must existing consumers keep working? |
| A scope or ownership assumption is being made | placing work in feature Y without confirmation |

Cap: ask the 2 most architecture-impacting questions if more triggers apply.

Do NOT ask about: naming, code style, error messages, test structure, or anything
resolved by project convention. These are Minor plan-critic findings, not user questions.

If no triggers fire, proceed directly to the pipeline without asking anything.

## Pipeline by Size

> **File requirement**: All spec documents must be written to disk at `.specs/{task-name}/`.
> IDE-specific plan tools (if available) do not substitute for file creation.

### Small Tasks — Direct Implementation

Skip spec creation entirely. Proceed to implementation following existing project conventions.

### Medium Tasks — Lightweight Spec

Create two documents:

1. Create `.specs/{task-name}/spec.md`
2. Combine key sections from the requirements and design templates:
   - Problem Statement (from `.ai/templates/requirements.md`)
   - Actors and Acceptance Scenarios — User Stories with Gherkin OR Use Cases (from `.ai/templates/requirements.md`)
   - Technical Approach (from `.ai/templates/design.md`)
   - Files to Create/Modify (from `.ai/templates/design.md`)
   - Risk Assessment (from `.ai/templates/design.md`)
3. **If the Technical Approach or Design section exceeds ~60 lines**, move it into a separate `.specs/{task-name}/design.md` file and link to it from spec.md. Keep spec.md focused on Problem Statement + Scenarios + Risk.
4. Create `.specs/{task-name}/tasks.md` — a task breakdown derived from the spec. Use `.ai/templates/tasks.md` as the starting template. Every file-to-modify in the spec should map to at least one task. Identify parallel groups where possible.
5. Create `.specs/{task-name}/test-plan.md` — run the `test-planner` skill, which for a Medium task
   produces a single document carrying the case table inline. Use `.ai/templates/test-plan.md`.
   Author it **in parallel with step 4**, then reconcile the two: every `TC-` gets an implementing
   task, and every task's `Test requirements` field cites `TC-` ids instead of prose. Skip this step
   only when the change touches no executable code, and say so explicitly.
6. Self-review using the Spec Quality Checklist at the bottom of this file.
7. **Run the plan-critic self-review** (the `plan-critic` skill) — full review over spec.md + tasks.md + test-plan.md (+ design.md if split out). Resolve all findings before continuing. If any Blockers or Questions remain, surface them in the presentation.
8. **STOP.** Present to the user for approval. Wait for explicit approval before continuing.
9. Only proceed to implementation after approval.

### Large Tasks — Full Spec

Create four documents, with a user approval gate after each. Requirements and design are strictly
sequential. **Tasks and the verification plan are authored in parallel** — both derive from the
same approved design, and neither is an input to the other until they are reconciled at the end.

1. **Requirements**: Create `.specs/{task-name}/requirements.md`
   - Use `.ai/templates/requirements.md` as the starting template
   - Fill in all sections based on task analysis and codebase exploration
   - See [references/requirements-guide.md](references/requirements-guide.md) for Gherkin syntax, actor identification, adversarial scenario generation, and AI pipeline patterns
   - **Run the plan-critic self-review** (the `plan-critic` skill) — full review. Resolve all findings before continuing. If any Blockers or Questions remain unresolved, surface them in the presentation.
   - **STOP.** Present to user. Wait for explicit approval before continuing.

2. **Design**: Create `.specs/{task-name}/design.md` (only after requirements approved)
   - Use `.ai/templates/design.md` as the starting template
   - Reference the requirements document for acceptance criteria
   - See [references/design-guide.md](references/design-guide.md) for writing guidance
   - **Run the plan-critic self-review** (the `plan-critic` skill) — full review. Resolve all findings before continuing. If any Blockers or Questions remain unresolved, surface them in the presentation.
   - **STOP.** Present to user. Wait for explicit approval before continuing.

3. **Tasks**: Create `.specs/{task-name}/tasks.md` (only after design approved)
   - Use `.ai/templates/tasks.md` as the starting template
   - Derive tasks from the design document
   - Ensure every acceptance criterion maps to at least one task
   - Identify parallel groups and dependencies
   - **Relevance audit — for each task, state what it recovers and THROUGH WHICH MECHANISM.**
     Task-to-cause mapping is assumed at planning time and rarely re-checked, so a plan can be
     internally consistent and still leave its largest bucket unaddressed. Measured: a 41% funnel
     loss decomposed into three causes; the task written as the fix for the biggest one delivered a
     machine-readable reason on the API's event payload and error body — and **the front end
     rendered neither**, so it changed nothing user-visible. It was correctly derived from the root
     cause and still could not move it. A task whose
     mechanism terminates in another team's repo is **enablement, not a fix**: label it so and name
     who owns the other half. Run this as an explicit audit, not as trust in the
     requirements-to-task derivation.
   - **Any post-review amendment re-opens the completeness dimension.** Plan-critic's "every
     adopted item → a task" check passed *when it ran*; sections, riders and decisions adopted in
     prose afterwards silently re-open it with nobody re-running the review. Two shapes seen
     together: a rider adopted in discussion with **no implementing task**, and a measurement
     contract promising a detector **no task builds**. After adding any section, rider or decision,
     immediately tick it against `tasks.md` — a new task, or an explicit "no task because…" — and
     re-check every instrument the spec promises against a building task. Cheap form: end every
     spec-amending turn with "does each new noun have a task?"
   - **Run the plan-critic self-review** (the `plan-critic` skill) — completeness-only pass (Dimensions 4–5 only). Resolve all findings before continuing. If any Blockers or Questions remain unresolved, surface them in the presentation.
   - **STOP.** Present to user. Wait for explicit approval before implementation.

4. **Verification plan**: run the `test-planner` skill (only after design approved — **in parallel
   with step 3**, not after it)
   - Produces `.specs/{task-name}/test-cases.md`, then `.specs/{task-name}/test-plan.md`, each with
     its own STOP gate. Templates: `.ai/templates/test-cases.md`, `.ai/templates/test-plan.md`
   - Conditions are **harvested by id** from requirements (`AC-`, `UC-`, `NFR-`), never restated.
     A second copy of a Gherkin scenario is a second source of truth that drifts on the first edit,
     and nothing in this pipeline cross-checks the two
   - Every case gets exactly one owning level, and every expected result cites the id it derives
     from. An uncited expected value is a document defect, not a formatting nit — a model asked to
     fill an expected-result column produces something plausible, specific, and wrong, and
     plausibility is exactly what survives review
   - **Run the plan-critic self-review** (the `plan-critic` skill) — verification pass. Resolve all
     findings before continuing
   - **Reconcile against `tasks.md` once both exist.** Bidirectional, and it is this stage's
     completion gate: every `TC-` has an implementing task or a named out-of-scope owner, and every
     task's `Test requirements` field cites `TC-` ids instead of prose. Parallel authoring means
     the two documents are written blind to each other — without this pass they never meet
   - **STOP.** Present to user. Wait for explicit approval before implementation.

5. Proceed to implementation only after all four documents are approved.

**Skip step 4** when the design touches no executable code (documentation-only or pure-config
changes). Say so explicitly rather than silently omitting it.

## Stage Approval Protocol

Every STOP gate in the pipeline above expects one of three responses from the user:

| Response | Action |
|----------|--------|
| Explicit approval ("approved", "looks good", "proceed") | Advance to the next stage |
| Revision request ("change X", "add Y", "remove Z") | Enter the review cycle |
| Silence or ambiguous response | Ask explicitly: "Do you approve this document, or would you like changes?" |

### Review Cycle

When the user requests a change:

1. **Evaluate the change before applying it.** See the Challenge Protocol below if the change raises a concern.
2. **Apply valid changes**: update the spec file on disk, then re-present the updated document with a brief summary of what changed (e.g., "Updated: removed the Redis caching option from Alternatives; tightened AC-3 to include the 401 error case").
3. **Wait for approval again.** The cycle repeats until the user explicitly approves the document.

### Challenge Protocol

When a requested change is technically questionable — it conflicts with existing project architecture, reverses a decision approved in an earlier stage of this spec, removes the only mitigation for an identified risk, or would add implementation code to the spec — raise the concern before applying anything:

1. **State the conflict clearly**: name the specific constraint it violates (e.g., the vertical slice rule, the earlier approved decision, the risk entry in the spec).
2. **Propose an alternative** if one exists.
3. **Wait for the user to respond.** They may have context the AI lacks.
4. **After the user responds**:
   - If they provide justification: accept the change, apply it, re-present.
   - If they simply insist without new information: apply the change, note it in the spec's Deviations Log as a "user override", re-present.
5. **Never challenge the same point twice.** Once the user has responded, the discussion is closed.

### What the AI challenges

- Changes that contradict the project's vertical slice architecture rules
- Changes that reverse an earlier stage's approved decision without explanation
- Changes that remove the only mitigation for a risk already identified in the spec
- Changes that add implementation code to spec documents

### What the AI does NOT challenge

- Naming preferences, wording choices, or ordering of sections
- Scope changes within reason (the user may have new information about requirements)
- Technology choices that are a matter of preference rather than correctness

## Executing & Resuming a Spec

- **Acceptance scenarios outrank tactic prose.** Gherkin scenarios and the risk table encode
  decisions at higher fidelity than tactic sketches — an "accepted risk" row reveals which
  over-constraint the author consciously chose. Derive each edit from the scenarios first, use
  tactic prose as implementation hints, resolve any divergence in the scenario's favor, and record
  the interpretation in the spec's working notes at execution time.
- **A parenthetical "reuse X's exact type" loses to the spec's own NAMED PRECEDENT.** When a spec
  gives both an implementation detail to copy *and* a named precedent function for the same
  behavior, verify the parenthetical actually produces the required outcome before trusting it —
  the named precedent is likelier to have been chosen because it is the one that works. Measured:
  a spec said the new endpoint's ownership check should "mirror `bulk_update_statuses`'s existing
  check; reuse its exact exception type" (a bare `PermissionError`), while its own Security NFR
  anchored the endpoint to "same pattern as `GET /coach/subtasks/{id}`". `PermissionError` is a
  builtin with **no entry in `handle_coach_request`'s exception→HTTP map**, so raising it would
  have fallen through as an unhandled 500 instead of the required 403 — and the named precedent
  (`CoachTaskService.get_subtask_detail`) raises `TaskAccessDeniedError`, which IS wired to 403.
  Grep the decorator/middleware exception map before copying an exception type, and record the
  resolution in the Deviations Log with **both** readings, not only the one taken.
- **Resuming mid-pipeline: every "Done" status line in `tasks.md` is a prior session's CLAIM, and
  one entry can mix true and fabricated claims** — so neither blanket-trust nor blanket-redo is
  right. Before building on a load-bearing "Done", grep for each claim's concrete artifact (test
  symbol, fixture field, doc marker): claims whose artifacts exist stand; absent artifacts get
  re-done. Record corrections in the tracking file (supersede, don't silently overwrite history).

## Phased Execution for Large Tasks

Large tasks that affect multiple independent concerns or can reach a consistent intermediate
state may benefit from phased execution. Phasing reduces the context each AI session must
hold, introduces intermediate quality gates, and catches drift before it compounds.

### When to Phase

After writing the design for a large task, assess whether phasing would help.

**Phase when ALL of these are true:**
- The task affects 2+ independent concerns (different features, layers, or subsystems)
- At least one intermediate state exists where the system is consistent and testable
- Later phases build on earlier phases without invalidating them

**Do NOT phase when ANY of these are true:**
- The change must be atomic (e.g., a migration from one API pattern to another across all features)
- All tasks share the same files and cannot be meaningfully separated
- The task is large by file count but single-concern (e.g., adding the same field to 15 entities)

See [references/phased-execution.md](references/phased-execution.md) for decision tree and examples.

### Phase Decomposition (During Design)

When phasing is beneficial, organize tasks into phases in the `tasks.md` document:

1. Identify natural phase boundaries. Good boundaries align with:
   - **Architectural layers**: storage complete → service complete → API complete
   - **Feature slices**: feature A vertical slice → feature B vertical slice
   - **Data flow stages**: data model + repo → business logic → API + integration tests
2. Group tasks into phases (2–4 phases; more than 4 indicates the task should be split into separate specs)
3. Define for each phase: objective, entry criteria, exit criteria, quality gate level
4. Verify each phase leaves the system in a consistent, testable state
5. Present the phased plan to the user for approval

### Phase Execution

Each phase is executed as a semi-independent unit:

1. **Load context**: Re-read requirements.md, design.md, and tasks.md. Do NOT rely on conversation memory from previous phases.
2. **Check entry criteria**: Verify the previous phase's exit criteria are met.
3. **Implement**: Work through the phase's tasks in dependency order.
4. **Update tasks.md**: Mark completed tasks, log deviations.
5. **Run quality gate**: Execute the gate level assigned to this phase.
6. **Handoff**: The updated tasks.md serves as the persistent anchor for the next phase.

### Quality Gate Levels

| Level | When to Use | Steps |
|-------|-------------|-------|
| **Light** | Simple phases (2–3 tasks, single layer) | Lint + quick self-review |
| **Standard** | Default for most phases | Steps 1–6 of post-task-review |
| **Full** | Final phase, or phases with cross-feature impact | Full 8-step post-task-review |

### Context Handoff Rules

- The spec documents (requirements.md, design.md, tasks.md) are the **persistent memory** across phases
- Never depend on the AI remembering details from a previous phase's conversation
- After each phase, update tasks.md with: task completion status, deviations, and any discoveries
- If a phase reveals that the design needs changes, update the design document before proceeding

## During Implementation

When implementing from a spec (phased or non-phased):

- Work through tasks in dependency order
- Mark each task as complete in the tasks document when done
- If implementation reveals that the spec needs changes, update the spec first and note the deviation in the Deviations Log
- If scope grows beyond the original spec, stop and discuss with the user

## Closing a Spec — self-review, then retire

A spec is not finished when its last task is ticked. Two steps close it, in order:

1. **Self-review — `post-task-review`** (mandatory for Medium and Large; the 8-step pass). Its
   step 4 self-challenge and step 7 documentation-impact sweep are what catch the defects the
   implementation pass cannot see, because they check the work against the *approved scenarios* and
   against every doc that cites the changed files. Phased specs run the gate levels in
   § Quality Gate Levels; the final phase always gets the Full pass.

2. **Retire — `initiative-cleanup`** (approval-gated, destructive). Settles the board rows against
   `git grep`, writes the forward plan **before** anything is deleted, partitions every deletion
   target per file into tracked vs untracked, and runs the comment pass. **`initiative-cleanup` owns
   the disposition rules — do not decide a spec's fate here.** Its gates:
   - **What KIND of artifact is it?** The implemented/not-implemented question below reaches a
     **spec** and nothing else — a dispatch brief describes no code, so it can never satisfy it.
     Scaffolding, rollback anchors, instruments and results are each dispositioned by their own
     life-ending condition. Skipping this axis is how one run left 136 of 157 files uncategorised
     and still reported success.
   - **Implemented?** (specs only) Prove it by content (`git grep -l '<symbol>' <ref>`), never by
     ancestry — a squash-merge makes the original SHAs non-ancestors while the code is in `dev`. Not
     implemented ⇒ `parked` with a revival trigger, never deleted.
   - **References repointed?** Sweep every inbound citation and repoint it *before* removal, then
     re-sweep to zero. No build fails over a dead reference.

**For a multi-slice initiative** (several specs, several branches), the topology is decided *before*
the first commit by `stacked-pr-planner`, and `orchestrate` § "Plan first" invokes it. A spec that
will land across more than one PR names its layer there rather than discovering it at commit time.

## State Contract

- **State location:** `.specs/{task-name}/`
- **State files:** `requirements.md`, `design.md`, `tasks.md`, `spec.md`, `test-cases.md`, `test-plan.md`
- **State transitions:** draft → reviewed (plan-critic) → approved (user) → implementing → completed
- **Cleanup:** owned by `initiative-cleanup`, not by this skill. Note its rules are the **inverse** of
  the intuitive ones this line used to state: a spec whose work **shipped** is *deleted* (the code and
  its tests are the truth; relocate anything durable to the code-adjacent home and leave a changelog
  pointer, or it becomes a second source that drifts), while a spec that was **parked or abandoned**
  is *kept*, because it carries the decision **not** to build — which is what stops the next
  initiative re-deriving it. Both dispositions are gated on § Closing a Spec's two checks.

## Spec Storage Convention

- All specs live in `.specs/{task-name}/` at the project root
- `{task-name}` uses lowercase with hyphens (e.g., `voice-recording-upload`, `sse-progress-migration`)
- **Commit the spec.** Writing under `.specs/` does not track it — the directory is not gitignored,
  but a new file there stays untracked until `git add`, and an untracked spec is a single copy with
  no history. Verify: `git ls-files --error-unmatch .specs/{task-name}/spec.md` → exit 0
- **Disposition at the end is `initiative-cleanup`'s call, and it inverts the intuition:** a spec
  whose work SHIPPED gets deleted (relocate anything durable to the code-adjacent home, leave a
  changelog pointer); a spec that was ABANDONED or parked is KEPT, with its revival trigger. See
  § Closing a Spec. Never delete a spec whose work was not implemented, and never delete one without
  first repointing every inbound reference

## Spec Quality Checklist

Before presenting a spec for approval, verify:

**Structure & Architecture**
- [ ] Files-to-modify and files-NOT-to-modify are explicit
- [ ] Risk assessment identifies at least one risk
- [ ] Alternatives section is filled in (at least one alternative considered)
- [ ] Design follows existing vertical slice architecture
- [ ] No implementation code in the spec documents
- [ ] Task dependencies form a valid DAG (no circular deps)

**Acceptance Criteria & Scenarios**
- [ ] All acceptance scenarios use a valid format — Gherkin (user-facing/goal-driven) OR Use Cases (system/technical flows) — or WHEN/THEN for purely internal/subtractive changes
- [ ] Gherkin: every Feature block has at least one happy-path scenario and one error/edge-case scenario
- [ ] Gherkin: `Background` used for shared preconditions where 2+ scenarios repeat the same Given steps
- [ ] Gherkin: `Scenario Outline` used for parameterized variants instead of duplicated scenarios
- [ ] Use Cases: every Use Case has at least one Exception Flow (happy-path-only Use Cases are incomplete)
- [ ] Use Cases: Postconditions (Failure) stated, enforcing invariants (no partial writes, error logged)
- [ ] Actors identified in the Actors section for all features with user-facing or multi-agent interaction
- [ ] Adversarial coverage applied — Gherkin error Scenarios OR Use Case Exception Flows answer the 5 boundary questions (auth, validation, AI failure, race condition, resilience)
- [ ] Stable ids present — every Gherkin Scenario carries an `@AC-{nn}` tag, every Use Case a `UC-{nn}`, every NFR an `NFR-{nn}`. Downstream documents cite ids; a citation to a title dies silently when the title is reworded

**Verification** *(Medium and Large tasks whose design touches executable code)*
- [ ] A verification plan exists — `test-plan.md`, plus `test-cases.md` for Large
- [ ] Every condition cites a source id, and no Given/When/Then text is copied from requirements
- [ ] Every condition names the design technique used to expand it into cases
- [ ] Every case has exactly one owning level; upward moves carry a written reason and exclusions are stated
- [ ] Every expected result cites the id it derives from — zero cases marked `[UNGROUNDED]`
- [ ] Every NFR has a verification method, and no category the project's testing conventions ban is assigned `automated`
- [ ] Deliberate non-coverage is stated with risk bands and rationale
- [ ] Reconciliation with `tasks.md` is complete in both directions, or explicitly marked pending

**Requirements Output Contract** — a requirements document is READY when ALL of the following are true:
1. Every Gherkin Feature has at least 2 Scenarios (1 happy path, 1 error); every Use Case has a Main Success Scenario + at least 1 Exception Flow
2. Every Gherkin Scenario has exactly one `When` step (single trigger, not compound); every Use Case has a single Trigger
3. No Gherkin Scenario exceeds 7 steps; no Use Case Main Success Scenario exceeds 10 steps
4. All actors referenced in scenarios or use cases appear in the Actors section
5. NFRs have numeric or boolean targets — no adjectives without a threshold

## Spec Authoring Lessons

- **Coordinate overlapping prompt-section edits**: before editing a prompt section, grep `.specs/*/`
  for other in-flight specs targeting the same section; land them in a known order and re-verify the
  first spec's edits survived after the second.
- **Out of Scope / Future Impact**: when an excluded item will plausibly become in-scope and affects
  interfaces/data models, analyze its design impact now (a "Future Impact" note) — "out of scope for
  implementation" ≠ "out of mind for design."
- **NFRs under uncertainty**: for features with new/unknown external deps, use "target with
  uncertainty" ("Target: <10s based on the provider's documented speed; verify in impl"), not a
  fabricated hard SLA. Reserve hard SLAs for measured or contractual behavior.
- **Strategy-boundary safety nets**: when two implementations of one protocol have intentionally
  different fault-tolerance, document the deviation in BOTH module docstrings AND the spec section
  (cross-ref the spec ID) so reviewers don't "fix" the asymmetry as drift.
- **Deviations Log captures downgrades**: record implementation-time model/version/default downgrades
  from the design spec; mark any resulting unused config with a `# TODO(...)` pointing at the log
  entry so it doesn't read as a bug.
- **Multi-file mechanical edits**: prefer numbered-plan + parallel executor agents (exact insert
  texts, file allowlists, machine-checkable self-checks) + an orchestrator diff pass over one long
  sequential pass.
