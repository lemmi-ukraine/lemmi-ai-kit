---
name: test-planner
description: >
  Derive a verification plan from an approved requirements/design pair. Harvests test
  conditions from acceptance-criteria ids, expands them into grounded test cases using an
  explicit design technique, assigns each case one owning test level and a verification
  method, states deliberate non-coverage, and reconciles the result against the task
  breakdown. Runs parallel to tasks.md in the spec-driven pipeline. Use when the user says
  "test plan", "test cases", "QA step", "verification plan", or "what should we test".
argument-hint: "[task-name]"
when_to_use: >
  "write a test plan", "create test cases", "add a QA step", "verification plan",
  "what should we test", "test scenarios"; or automatically after design.md is approved
  in the spec-driven-dev pipeline for a Medium or Large task.
metadata:
  type: task
---

# Test Planner — verification planning from an approved spec

ultrathink

## Vocabulary (read this first)

Two incompatible definitions of "test scenario" are in live industry use. This kit uses the
ISTQB one. Pin it before writing anything, or the document will be misread.

| Term | Definition used here | Not this |
|---|---|---|
| **Test condition** | An item or event that *could* be verified by one or more test cases — a function, rule, quality attribute, or boundary. Answers "what must be proven". | Not a test. It has no inputs and no expected result. |
| **Test case** | Preconditions + inputs + actions + **expected result** + postconditions, derived *from* a condition. Carries a `TC-` id. | Not a restatement of the requirement. |
| **Test scenario** | A *sequence of actions for the execution of a test* — synonymous with test script / test procedure. It sits **downstream** of the case and groups several into one runnable flow. Carries a `TS-` id. | **NOT** an umbrella above test cases. That is the colloquial vendor usage and it inverts the hierarchy. |
| **Test plan** | The management wrapper: scope, levels, environments, entry/exit criteria, risk banding, non-coverage. | Not a list of tests. |

Hierarchy: **condition → case → scenario**, with the plan wrapping all three.

## When This Skill Activates

Invoked after `design.md` is approved, running **parallel to `tasks.md`** — both derive from
the same frozen requirements/design pair.

Activate for:

- Any **Medium** or **Large** task in the spec-driven pipeline
- A direct request for a test plan, test cases, or a QA step
- A feature whose acceptance criteria have never been mapped to test levels

Do NOT activate for:

- **Small** tasks. They produce no `requirements.md` and no `design.md`, so there is nothing to
  derive from. Verification for a Small task is the change's own test, written inline.
- Documentation-only or pure-config changes where the design touches no executable code.
- Writing the tests themselves. This skill plans; it does not implement.

## Inputs and Preconditions

| Input | Required | Used for |
|---|---|---|
| `.specs/{task-name}/requirements.md` | Yes | Harvesting conditions from `AC-`/`UC-`/`NFR-` ids |
| `.specs/{task-name}/design.md` (or the design section of `spec.md`) | Yes | Component boundaries, integration points, and the Risk Assessment's Likelihood/Impact scores |
| `.specs/{task-name}/tasks.md` | No — may not exist yet | The reconciliation pass (Step 7), once it does |

**If the requirements document has no `AC-`/`NFR-` ids** — it predates the id convention —
assign them in place as a first action, report that you did, and proceed. Never invent an id
that does not exist in the source, and never cite a scenario by title alone: titles get
reworded and the citation dies silently.

## Pipeline by Size

### Medium — one document

Create `.specs/{task-name}/test-plan.md` from `.ai/templates/test-plan.md`, carrying the case
table inline. Run Steps 1–7. One STOP gate.

### Large — two documents

1. `.specs/{task-name}/test-cases.md` from `.ai/templates/test-cases.md` — Steps 1–4 and 6.
   **STOP.** Present for approval.
2. `.specs/{task-name}/test-plan.md` from `.ai/templates/test-plan.md` — Steps 5 and 7, plus
   the scenarios that group the approved cases. **STOP.** Present for approval.

## Step 1 — Harvest conditions (never restate)

The requirements document has already done the hard part. Its Gherkin `Scenario:` blocks, its
Use Case Exception Flows, and its adversarial-five answers (auth / malformed input / dependency
unavailable / concurrent race / dropped connection) **are** your test conditions.

Harvest them:

1. List every `AC-`, `UC-` and `NFR-` id in the requirements document.
2. Write each as one condition heading — a short statement of what must be proven.
3. Cite the source id on the heading. A condition with no source id is either an invention or
   a genuine requirements gap; if it is a real gap, raise it rather than quietly covering it.

**Do not copy the Given/When/Then text into this document.** A second copy of a scenario is a
second source of truth, and it diverges the first time the requirement is edited — with nothing
in the pipeline cross-checking the two. Cite the id; add only what the requirement does not
already carry.

## Step 2 — Expand conditions into cases, with a named technique

One condition becomes N cases. **N is not a matter of taste** — it falls out of the design
technique that fits the input's shape. Name the technique on every condition; a condition whose
case count has no named technique was generated by vibes.

| Input shape | Technique | Typical case count |
|---|---|---|
| A numeric or ordered range | Equivalence Partitioning + Boundary Value Analysis | 1 per partition + 2 per boundary |
| A set of business rules that combine | Decision table | 1 per reachable rule combination |
| Behaviour that depends on prior events | State transition | 1 per valid transition + key invalid ones |
| Many independent parameters | Pairwise | 1 per covering pair, not the full cross-product |
| Unordered sets, booleans, enums | Decision table — **never** BVA | 1 per value or rule |

**BVA on a boolean, an enum, or an unordered set produces meaningless cases** and leaves the
real rule combinations untested. Boundaries only exist where there is an order.

Full technique selection, worked examples, and the traps: [references/design-techniques.md](references/design-techniques.md)

## Step 3 — Assign exactly one owning level

Every case gets **one** owning level. Not two, not "all of them".

When teams do not agree the level up front, the same behaviour gets automated at every level
independently — a fat base at each tier rather than a pyramid. The result is duplicated
maintenance, slow suites, and ambiguity about which failure is authoritative. **Deciding the
level here, before any test is written, is the main reason this stage exists.**

Two rules:

1. **Default downward.** Assign the lowest level that can actually prove the assertion. Moving
   a case *up* a level requires a written reason on the case; moving it *down* never does.
2. **Exclusions are stated, not implied.** When a case plausibly belongs at more than one level,
   name the levels you excluded and why — one clause is enough. Silence reads as "nobody
   considered it" to the next reader.

**Where the project ships a language pack with its own test-type decision table, that table is
authoritative — defer to it rather than inventing a competing taxonomy.** Read the pack's
testing conventions reference for the project's own level names, its base-class rules, and its
required timeout decorators, and use those names in the plan. Do not hardcode any pack skill's
name here; route by role, so the plan stays correct in a project with a different language pack
or none at all.

Level names, the default-downward decision tree, and the exclusion phrasing:
[references/level-assignment.md](references/level-assignment.md)

## Step 4 — Ground every expected result in a cited id

**This is a hard gate, and the highest-value rule in the skill.**

Every case's expected result cites the `AC-`/`UC-`/`NFR-` id or the named design contract it
comes from. An expected result with no citation is a defect in the document, not a minor
omission.

The reason is specific to how these documents get written. A model asked for an expected value
will produce one that is plausible and specific and wrong — a latency figure, an error code, a
field name that reads exactly like the real one. Plausibility is precisely what makes it survive
review. The citation is the only cheap check that separates "derived from the spec" from
"generated to fill the column".

```
BAD   TC-04 | expected: responds within 200ms          ← invented; no id, no source
GOOD  TC-04 | expected: responds within 500ms (NFR-02) ← traceable, falsifiable
```

If a case genuinely needs a value the spec does not fix, that is a **requirements gap**. Mark
the case `[UNGROUNDED]`, state what is missing, and surface it at the STOP gate. Do not fill it.

### Can this case pass without proving anything?

Ask it of every case before the gate closes. A case that passes because its precondition was
never reachable is indistinguishable from one that passes because the behaviour is correct — and
it is the shape that survives longest, because nothing ever fails.

Three shapes to check for:

- **Empty population.** The case iterates over a set that can legitimately be empty. Add an
  assertion that the set is non-empty, and say what it is guarding.
- **A falsy expected result with more than one cause.** `None`, `False`, `[]` or "rejected" that
  two different code paths produce. Assert something that distinguishes them — an error type, a
  message, a field — or neutralize the other causes in the preconditions.
- **A precondition that cannot hold in the target environment.** The case is skipped rather than
  run. A skip is not a pass; plan to count them.

Note the guard on the case itself, so nobody later removes it as redundant.

## Step 5 — Assign a verification method, not just a level

A level says *where* a case runs. A method says *whether it is an automated test at all* — and
for a whole class of requirements, it must not be.

| Method | Use when | Produces |
|---|---|---|
| `automated` | The assertion is deterministic and cheap to observe in a test | A test case at the assigned level |
| `observability` | The assertion is about production behaviour under real load — latency percentiles, throughput, error rates | A metric, log field, or alert; no test |
| `manual` | One-off verification at release; automation cost exceeds value | A checklist item with an owner |
| `accepted-unverified` | The risk is accepted and stated | A row in Non-Coverage with its rationale |

**NFRs are where this earns its keep.** The requirements template demands numeric NFR targets
("under 500ms at p95"), and many projects — including any whose conventions ban performance and
load tests — have no automated home for them. Assigning such an NFR a test case produces a test
the project's own conventions forbid. Assign `observability` and name the metric instead.

```
BAD   NFR-01 p95 < 500ms | automated | TC-09 asserts elapsed < 500ms
      ← a latency assertion in a suite that bans performance tests; flaky, and
        the conventions require deleting it on sight
GOOD  NFR-01 p95 < 500ms | observability | metric api.request.duration, p95 alert at 500ms
      ← nothing to run in CI, and the target is actually watched where it is real
```

Check the project's testing conventions for banned test categories **before** assigning
`automated` to any performance, load, or throughput requirement.

## Step 6 — State deliberate non-coverage

What you decided not to test is an output of this document, not an omission from it.

Band each condition by risk using **the Likelihood and Impact already scored in `design.md`'s
Risk Assessment table** — do not re-derive risk, and do not invent a second scoring scheme.

| Band | Coverage |
|---|---|
| High impact × High likelihood | All applicable levels; adversarial cases mandatory |
| Medium | Owning level only |
| Low × Low | Smoke coverage, or an explicit non-coverage row |

Every non-covered condition gets a row: the condition, its band, and one sentence of rationale.
A reader must be able to disagree with the decision, which means they have to be able to see it.

## Step 7 — Reconcile against tasks.md

This stage runs **parallel** to `tasks.md`, so the two documents are written without knowledge
of each other. Left alone they never meet. Reconciliation is this stage's completion gate, and
it runs in **both** directions once `tasks.md` exists:

1. **Every `TC-` has an owner.** Either an implementing task in `tasks.md`, or a named party
   outside this spec's scope. A case owned by nobody is not planned work.
2. **Every task's `Test requirements` field cites `TC-` ids.** That field already exists in the
   task template and holds free prose by default. Back-fill it with the ids that task must
   satisfy. Prose that names no case is not a test requirement.
3. **Re-run after any amendment.** Adding a condition, case, or task after reconciliation
   silently re-opens it — the pass was valid only for the state it ran against.

The traceability matrix records **verification status**, not just the mapping. A requirement
mapped to a case that was never written or never ran is the appearance of coverage without the
substance of it — and it reads identically to real coverage at a glance, which is what makes it
worth a column rather than a convention.

If `tasks.md` does not exist yet, say so at the STOP gate and mark the reconciliation pending.
Do not report the plan complete without it.

## Output Contract

A test-planning document is READY when all of the following hold:

1. Every condition cites a source id from the requirements document.
2. Every condition names the design technique used to expand it.
3. Every case has exactly one owning level, and any upward move carries a reason.
4. Every expected result cites an id, or is marked `[UNGROUNDED]` and surfaced.
5. No case can pass vacuously — empty populations are guarded, falsy expected results distinguish
   their cause, and environment-dependent preconditions are stated.
6. Every NFR has a verification method, and no banned test category is assigned `automated`.
7. Non-coverage is stated with bands and rationale, not left implicit.
8. Reconciliation against `tasks.md` is complete, or explicitly marked pending.
9. No Given/When/Then text is copied from the requirements document.

## Anti-Patterns

| Anti-pattern | What actually happens | Instead |
|---|---|---|
| Restating requirement scenarios as cases | Two sources of truth, no cross-check; drifts on first edit | Cite the id; add inputs, level, expected value |
| A case listed at three levels | Duplicated maintenance and no authoritative failure | One owning level; state the exclusions |
| Proving behaviour mainly through end-to-end cases | Brittle, slow, and it hides which unit is broken | Default downward; justify upward moves |
| An invented expected value | Reads as specific and survives review; encodes a wrong assertion | The Step 4 citation gate |
| BVA on enums or booleans | Meaningless boundaries; real rule combinations untested | Decision table |
| A matrix maintained after the spec ships | Requirements move, cases do not, and it certifies a dead version | The document dies with the spec — see State Contract |
| An NFR with a performance test in a project that bans them | A test that conventions require deleting on sight | `observability` + a named metric |

## State Contract

- **State location:** `.specs/{task-name}/`
- **State files:** `test-cases.md` (Large only), `test-plan.md`
- **State transitions:** harvested → expanded → levelled → reconciled → approved (user)
- **Lifetime — build-time only.** These documents exist to drive test writing. Once the work
  ships, **the tests themselves are the truth** and the plan is deleted with the rest of the
  spec by `initiative-cleanup`. Do not maintain it afterwards: a traceability matrix kept past
  its purpose rots quietly under deadline pressure and then certifies coverage that no longer
  exists. If a durable artifact is warranted, relocate it into the test suite's own
  documentation before deletion, never leave a second copy behind.
- **Cleanup:** owned by `initiative-cleanup`, not by this skill.
