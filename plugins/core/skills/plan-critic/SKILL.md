---
name: plan-critic
user-invocable: false
metadata:
  type: review
description: >
  Implementation Plan Critic & Challenger. Performs a rigorous AI self-review of spec
  documents (requirements.md, design.md, tasks.md, spec.md, test-cases.md, test-plan.md) before
  they are presented to the user. Catches security gaps, overengineering, missing failure
  handling, breaking changes, incomplete acceptance criteria, and ungrounded or duplicated
  test coverage. Use as a silent pre-presentation step inside the spec-driven-dev pipeline.
---

# Implementation Plan Critic & Challenger

## Role

You are an AI Platform Architect performing a self-review of a plan you just wrote.

**How you reason:**
- **Adversarially**: "What breaks? What fails at 2am? What does an attacker try? What does the AI model return when it shouldn't?"
- **Verification-first**: "Can I prove this claim from evidence in the document, or am I assuming?"
- **Pipeline-aware**: "Does every stage in the flow have an input contract, an output contract, and a failure contract?"

**Your domain:** AI-integrated backend systems — LLM integration, real-time streaming, prompt safety, async job processing. You know AI services fail in ways traditional services don't — hallucination, latency variance, rate limits, model drift, partial responses.

**Your constraint:** Approval must be earned through evidence. Vague criticism is as useless as blind approval. When you reject something, propose a concrete alternative.

## When This Skill Activates

Run this skill **before presenting any plan document to the user**:

- After writing `spec.md` for a medium task — full review
- After writing `design.md` for a large task — full review
- After writing `tasks.md` for a large task — completeness-only pass (dimensions 4–5)
- After writing any implementation plan — full review

Do NOT run this skill after implementation. The post-task-review skill covers that.

**Self-challenge is per-ARTIFACT, not per-task.** A second proposal written after the first one was
challenged needs its own pass — the earlier challenge does not cover it, and treating one
per-session run as satisfying the gate is how an unreviewed plan reaches the operator. The same
applies to a revision, with a cap: **at most two runs per document**. **Re-run this skill once on
the revised document**, because a fix pass introduces defects at roughly the rate it resolves
them. Measured on a churn-forensics plan — the second pass found three errors and *all three were
introduced by the first pass's own correction* — so Step 4's resolution loop must re-derive every
figure a fix touched rather than carrying the pre-fix number forward. That re-run is the second
and last run, because further runs mostly add churn: a later run edits only for a factual error,
a contradiction, a missing item or an unsafe statement — not for wording, order or taste. The
full re-read of the document belongs to that same run, not to an extra one, and a fresh-reader
re-review counts as the second run, within the limits the post-task-review skill sets for a
fresh reader.

---

## Review Process

### Step 1 — Orient and Run DoR Pre-Flight

Read the document end to end. For a plan that orders work across initiatives, branches or pull
requests, Step 2.7 also sends you to the documents its steps depend on. Identify:
- The stated problem being solved
- The affected layers (API / Service / Storage / Frontend / Infra)
- New vs. modified components
- Any external dependencies (DB, AI provider APIs, streaming channels, auth providers, Cloud services)

Then run the DoR pre-flight from [references/dor-tables.md](references/dor-tables.md).

### Step 2 — Run the Seven Dimensions

**Load and WALK the reference files — never review from a mental summary of them.** For
high-blast-radius plans (production-wide behavior, shared contracts, data), an inline from-memory
pass converges on generic checks (security, rollback, scope) and systematically misses the
table-driven ones; a measured instance found 1 Major inline vs 4 more Majors (line-budget
contradiction, detection-latency gap, under-scoped sweep, missing AI-failure contract) when the
tables were actually walked. The reference files ARE the skill; this SKILL.md is just its index.

Work through each dimension from [references/review-dimensions.md](references/review-dimensions.md):
1. Security
2. Overengineering
3. Stability & Resilience
4. Impact & Affected Areas
5. Plan Completeness
6. Verification Coverage — **only when reviewing `test-cases.md` or `test-plan.md`**; skip it for
   every other document. Dimension 5's testing bullets are about the *implementation's* tests and
   do not substitute for this pass, so a verification plan reviewed without Dimension 6 has been
   checked against nothing that applies to it.
7. Quantified Claims — **only when a plan states attempts, retries, charges or a per-record field**.

For every issue found, record it using the finding format from [references/finding-format.md](references/finding-format.md).

### Step 2.5 — Cross-Document Consistency Check (design.md reviews only)

When reviewing `design.md`, verify consistency against `requirements.md`:

1. For every quantitative value (timeout, threshold, retry count, SLA) that appears in both
   documents, confirm they match. Flag contradictions as Major.
2. For every component responsibility described in requirements, confirm the design assigns
   it to the same component. Flag ownership changes as Major if undocumented.
3. For every acceptance scenario in requirements, confirm the design provides a path to
   satisfy it. Flag gaps as Major Completeness.

Skip this step when reviewing `spec.md` (medium tasks) or `tasks.md`.

### Step 2.6 — Citation Check (verification document reviews only)

When reviewing `test-cases.md` or `test-plan.md`, verify the citations **mechanically**. Reading
cannot do this job: a fabricated id and a real one are indistinguishable on the page, and a plausible
citation is exactly what survives a reading pass.

1. Extract every cited id from the verification document (`AC-`, `UC-`, `NFR-`) — the **bare**
   form. In `requirements.md` a scenario id appears as the Gherkin tag `@AC-01`; the `@` is tag
   syntax, not part of the id, so grep the bare form (it matches the tagged occurrence too).
2. Grep `requirements.md` for each one. Any id with no match is a **fabricated citation — Blocker**.
3. Grep the other direction: every id defined in `requirements.md` should appear either in the
   traceability matrix or in the Non-Coverage table. An id in neither is untraced — flag as Major.
4. Confirm no Given/When/Then text was copied across rather than cited. Flag as Major.

Skip this step for every other document type.

### Step 2.7 — Sequencing Check (plans that order work across initiatives, branches or pull requests)

When reviewing a plan that orders work across initiatives, branches or pull requests, read the
documents its steps depend on, not only the plan: each initiative's plans and prompts, the topology,
the project's rules. List the preconditions they state: a clean tree, a pin or settle check against
the trunk, a file deleted only after its work ships, a file with one editor, a trigger that expires.
Test each step, in plan order, against them at the point where it runs. A step that runs before its
precondition can hold is Major; one that loses work or breaks another initiative's gate is a Blocker.

Skip this step for a single-slice spec.

### Step 3 — Apply the Universal Challenge Questions

After the dimensions, answer these six questions regardless of scope.
Each question must produce either a confident answer or a finding:

1. **Simplicity**: What is the simplest version of this that solves the stated problem?
   If the plan is more complex than this answer, justify why — or flag it as Major Overengineering.
   - At a scope/plan gate, surface the MINIMAL-viable design as an explicit option with its trade-offs
     and let the user choose UP from minimal — don't present only already-elaborate options (approving
     "two vs one" approves a COUNT, not proportionality).
   - A completeness question ("does it have X, like the original?") is NOT a request to make X a
     default. Two tools can share a capability without sharing its default cost profile — default to
     *available + documented*, not *on*.

2. **Failure at 2am**: What happens when this fails in production with no one available?
   If the answer is "unknown" or "system goes down," that is a Blocker unless failure handling is already covered.

3. **Rollback**: What is the rollback plan if this deploys with a bug?
   If none is stated and this touches DB schema, API contracts, or message and event formats, flag as Major Impact.

4. **Problem evidence**: Does the document state — in operator-plain language, before any solution —
   WHAT problem it solves, HOW OFTEN it occurs (a measured figure with its window and source), and
   why now? If "how often" is unanswerable from the document, flag as Major. Measured failure
   (2026-08-03, two spec sessions in one day): the operator had to interrogate the spec author —
   "why do we nede these changes, what problems we want to solve, how often tthey occure" and
   "i still don't get why do we need this fdeature" / "explain me like for non tech person" — because
   the motivation lived in a board row the document assumed the reader had. A spec that cannot answer
   this question in its own text is asking the operator to approve on trust.

5. **Inherited framing**: which claims did this plan **inherit rather than measure**? This is the
   one question the other four cannot reach, because a premise every section shares reads as
   coherence, not as a defect — and coherence is what the dimensions check. Measured failure
   (2026-08-15): this skill ran on an initiative plan and passed it, and the operator then found
   **three** scope gaps it had missed — prior shipped work, a substance-vs-delivery mis-framing, and
   an already-fixed row — each an unexamined inheritance rather than an inconsistency. One of them
   was a single sentence carried in from the source document ("behavioural feedback genuinely goes
   deep") that had narrowed a whole-rubric defect to a 12.7%-of-rows defect across **five**
   downstream sections; one measurement refuted it, 48/48 versus 0/48.
   - List the claims that **scope** the plan — what is in, what is out, how big the problem is — and
     require each to be marked `measured (window, n)` or `inherited — unverified`. An inherited
     claim is not wrong; it is untested, and it is doing structural work either way.
   - Ask separately: **what has already shipped against this problem, and was its effect measured?**
     Answered from `git log`/`git grep`, never from a status column — a board row was measured still
     reading `TODO` a month after its work shipped. Unmeasured prior work is its own deliverable, usually the
     cheapest one, and sometimes it makes the rest unnecessary.
   - **Grep `tasks/` and `.specs/` for prior work on the same defect, by the defect's own symbols.**
     A hypothesis the *operator* supplied survived an entire analysis unchallenged because nobody
     searched for prior work on it — it had already been investigated and disproven weeks earlier.
     An inherited claim from the operator gets the same provenance mark as any other; being handed
     the frame by a human is not measurement.
   - Flag as **Major Completeness** when a scoping claim carries no provenance. This is the plan-time
     twin of question 6 below: 6 asks who chose the sample, this asks who chose the frame.
   - **A review pass cannot audit its own framing.** Apart from the cross-document checks (Steps 2.5
     to 2.7), this skill reads the plan against itself, so a premise the plan and its source document
     share is invisible to every question above except this one — which is why the checks here are
     phrased as "produce the provenance list", not "does it look consistent". Where a plan overrode
     an inherited claim, make it record what it overrode.

6. **Evidence provenance**: for every load-bearing "all N instances have property P" claim, ask
   **who chose the N**. When the population came from a detector, scan, or grep the author also
   built, the claim is circular — the instances the detector misses are exactly the counter-examples,
   so its output can never contradict it. This is not hypothetical: an I6 scan of 875 turns found 30
   narration instances and measured 30 of 30 carried no question, and that number became the
   load-bearing safety argument of an **approved** spec ("cancelling a guarded turn cannot destroy
   question content, because there is none"). A concurrently-built second detector found the one
   instance that falsified it — a narration preface fused to a real question in one spoken turn.
   Both passes were individually careful and the failure was invisible from inside either.
   Flag as Major unless the document does one of: (a) tests P over the **whole population** rather
   than the detector's output, or (b) reconciles a second, independently-built detector as a union,
   treating disagreements as findings. Pair every "N of N share P" with **P's base rate** — 9 of 9
   flagged cases lacking a property looked decisive until the base rate showed 85% of the population
   lacks it (p ≈ 0.23).

**Does the better fix live in a repo you cannot see?** When a capability spans two repos and
only one is checked out here, the accessible repo's solution reads as the *obvious* plan — not
because it is technically better, but because it is the only one directly investigable. Measured:
a request to simulate a dropped connection and reconnect defaulted to a new standalone script in the
backend — the only repo checked out — without weighing that the frontend already owned the reconnect
path. Ask explicitly, before proposing where new cross-repo capability should live: *does the other
repo already have a working implementation this would duplicate or diverge from?* If you cannot
check, say so and name who can — do not let "the repo I can read" become "the repo it belongs in".

**Did every item in a source enumeration become a claim?** A consistency review cannot see an
**omission** — it checks that the claims present agree with each other and with their sources, which
is a different question from whether a source's list of N items produced N claims. Measured: a source
row enumerating N items became N−1 claims and **two self-review passes missed it**, because question 5
asks
which claims were inherited rather than measured, and never which items never became claims at all.
Take each enumerating source, count its items, count the claims derived from it, and reconcile the
two numbers explicitly.

**Does a supporting FIGURE survive re-derivation, even where the conclusion is right?** A number
attached to a correct decision is the least-challenged claim in the chain — the decision's
correctness is what protects it. Measured: a refusal handed down as settled cited a figure **no
command reproduces** (the candidate widenings yield 320 / 376 / 426; the quoted 364 is none of them),
and a two-option framing had hidden the correct third option. Re-derive the number and re-enumerate
the options, and say so explicitly when you agree with the conclusion anyway.

### Step 4 — Resolve What You Can

For each finding:
- **Minor**: fix silently in the document.
- **Question**: keep it; surface to the user.
- **Major**: attempt to resolve by revising the document. If resolution requires information only the user has, mark `[UNRESOLVED]`.
- **Blocker**: apply the Self-Refine loop:
  1. Propose a specific fix to the document
  2. Apply the fix
  3. Re-evaluate: does this fix fully resolve the Blocker?
     - Yes → mark resolved, note what changed
     - No → revise the fix, re-apply, re-evaluate (one more iteration)
  4. If the fix requires information only the user has after 2 iterations: mark `[UNRESOLVED]`

In a later run (the run cap in When This Skill Activates), resolve only the classes the run cap
names; drop every other finding, a Minor included, without fixing or surfacing it.

After the last fix pass, diff the document against its version before the first fix pass: every
changed line must be a fix you made on purpose, and any other change is reverted.

### Step 5 — Determine Output

- If **any Blockers or Questions remain `[UNRESOLVED]`**: the document is **NOT APPROVED**.
  Present the document with all unresolved findings listed prominently at the top.
- If **all Blockers and Questions are resolved**: the document is **APPROVED**.
  Present it normally. Mention resolved findings only if they changed the document significantly.
- **Minor findings** are never surfaced to the user: they are fixed silently, or dropped in a later run (Step 4).

See [references/finding-format.md](references/finding-format.md) for severity definitions and output format.

---

## Project-Specific Context

Read the project's own architecture, conventions and Do-not sections (its AGENTS.md) and review the plan against what they state; a convention the project does not state is not a finding. Two AI checks hold in every project:

- **AI failure modes**: any plan involving AI provider API calls must address rate limits, timeouts, and unexpected response formats. Missing failure contracts are a Major finding.
- **AI model facts must be doc-verified**: any plan that states a model ID, event name, session parameter, audio format, or capability limit must have that fact verified against the official docs via `WebFetch` (see the `ai-docs-lookup` skill). Unverified AI provider facts are a Major finding — in-memory knowledge is unreliable for these facts.
