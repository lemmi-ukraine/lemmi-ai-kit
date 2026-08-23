---
name: ai-improvement-tracker
user-invocable: false
description: >
  Record testable improvement hypotheses for AI infrastructure changes in
  .ai/improvement-hypotheses.md. Companions each ai-changelog entry with a
  falsifiable prediction about expected value, categorized by improvement type.
  Called automatically by workflows after writing a changelog entry. Use when
  an AI infrastructure change is expected to produce a measurable improvement.
metadata:
  type: task
---

# AI Improvement Tracker — Record Testable Hypotheses

## When This Skill Activates

After the `ai-changelog` skill appends a changelog entry, evaluate whether the
change warrants an improvement hypothesis. Not every change does — see the
Decision Gate below.

## Decision Gate

The gate is **behavioral vs administrative** — judged by what the change DOES, not by its
type prefix. An `INFRA-*` change that alters how sessions behave (a new script agents run, a
restructured knowledge home) deserves a hypothesis; a `SKILL-MODIFIED` that only fixes a
listing does not.

**Record a hypothesis when the change is behavioral** (typical types):
- `SKILL-ADDED` / `SKILL-MODIFIED` — new or changed skill behavior
- `CONV-ADDED` / `CONV-MODIFIED` — new or changed convention
- `RULE-ADDED` / `RULE-MODIFIED` — new or changed rule
- `WORKFLOW-MODIFIED` — pipeline phase added, removed, or reordered
- `CONSOLIDATION` — learnings promoted to permanent infrastructure
- `EXPERIMENT-REGISTERED` — ALWAYS: this type's entry rule requires a paired dated,
  falsifiable hypothesis with a re-eval date
- `INFRA-ADDED` / `INFRA-MODIFIED` — when the infrastructure change is behavioral

**Skip hypothesis recording when the change is administrative — regardless of prefix:**
- Purely structural (renaming, reformatting, file reorganization, listings sync)
- A removal with no replacement (`SKILL-REMOVED` without successor)
- The changelog entry's "Why" is purely administrative ("keeping listings in sync")

When in doubt, skip — a missing hypothesis is better than a vague one.

## Improvement Category Taxonomy

Every hypothesis must target exactly one category. These 7 categories are derived
from the SPACE framework (ACM Queue / Microsoft Research), DX Core 4, and the
METR study, adapted for AI development infrastructure.

| Category | What it measures | Example signal |
|----------|-----------------|----------------|
| **Consistency** | Reduced variance in AI output quality | Fewer off-convention outputs, less human correction |
| **Speed** | Time from task start to acceptable completion | Fewer review cycles, faster first-pass generation |
| **Quality** | Correctness, compliance, fewer regressions | Fewer post-task-review findings, reduced rework |
| **Cognitive Load** | Reduced mental effort for humans | Fewer redirections, simpler prompts produce correct output |
| **Knowledge Retention** | Institutional knowledge persists and is reused | Learnings consulted before tasks, gaps caught earlier |
| **Coverage** | Breadth of scenarios the AI handles correctly | New edge cases handled, more features covered by skills |
| **Observability** | Ability to understand what happened and why | Better post-mortem data, easier root cause analysis |

This taxonomy is a closed set. Do not introduce new categories — if a hypothesis
does not fit, reconsider whether it is specific enough.

**One PRIMARY category per entry.** Never write compound categories ("Quality /
Observability") — pick the primary improvement; the secondary angle goes in the Hypothesis
prose. Map common synonyms to the closed set instead of inventing near-duplicates:

| You are tempted to write... | Use instead |
|-----------------------------|-------------|
| Reliability | Quality |
| Maintainability | Quality |
| Efficiency (incl. "hot-path efficiency") | Speed |
| Reusability / Effectiveness | Coverage |

(`python -m lemmi_ai_kit lint hypotheses` flags any new violation.)

## Entry Format

Append under the current date heading in `.ai/improvement-hypotheses.md`:

```markdown
### [{CHANGE-TYPE}] {Title from changelog entry}
- **Category:** {Exactly one of: Consistency | Speed | Quality | Cognitive Load | Knowledge Retention | Coverage | Observability}
- **Hypothesis:** By {what the change does}, we expect {specific expected improvement} because {causal mechanism}.
- **Signal:** {What observable evidence would confirm or refute this?}
- **Risk:** {Potential negative side-effect to watch for, or "None anticipated"}
- **Status:** PENDING
- **Changelog ref:** {YYYY-MM-DD — title of the companion changelog entry}
```

### Field Rules

- **Category** — mandatory, single-valued. Forces specificity.
- **Hypothesis** — must use the "By X, we expect Y because Z" structure. The "because"
  clause is what makes it useful; without a causal mechanism, the hypothesis is a wish.
- **Signal** — mandatory. The falsifiability test: if you cannot describe what you would
  observe, the hypothesis is not worth recording. Four signal-design rules from the
  2026-08-02 meta-synthesis (n=22 — these patterns decided whether an entry could ever
  resolve):
  1. Name only measuring instruments that EXIST at write time — Glob/`git log` the file,
     report, or script before citing it (4 of 6 INCONCLUSIVE verdicts named instruments
     that did not exist, e.g. retrospectives that were never committed).
  2. Prefer ≤2 decidable clauses. A ≥3-clause conjunction resolves INCONCLUSIVE on partial
     hits — split into two hypotheses (different categories) or drop the weakest clause.
  3. Give event-keyed windows a calendar backstop ("the next 2 runs or 8 weeks, whichever
     first") — rare events strand PENDINGs; the validator parks them DORMANT at 8 weeks.
  4. Never write a signal the system's own operation satisfies (a skill's hypothesis
     confirmed by the skill merely running is a cheap CONFIRMED that measures nothing).
- **Risk** — optional but encouraged. Presence is a quality marker. If the change relies
  on a session *electing to act* (a permission, a prose cadence guard, a step someone must
  remember), say so here — all 3 REFUTED verdicts to date share exactly that mechanism.
- **Status** — always starts as `PENDING` and its value is EXACTLY one of `PENDING`,
  `CONFIRMED`, `REFUTED`, `INCONCLUSIVE`, `SUPERSEDED`. Only the `hypothesis-validator`
  skill (invoked from learning-consolidator Phase 6.5, approval-gated; offered by
  session-retrospective when its data settles a signal) changes it; session-retrospective
  §4g reports evidence but never edits statuses.
- **Validation notes** — optional sub-field placed directly above Status. Partial or
  interim evidence (e.g. "1 supporting run") goes HERE while Status stays `PENDING` —
  never inline annotations on the Status value itself. Written by `hypothesis-validator`
  (or a human); dated.
- **Changelog ref** — creates the link to the companion changelog entry. Never modify
  the changelog to link back (keeps the changelog format stable).

### Multiple Hypotheses Per Entry

A single changelog entry may produce up to **2 hypotheses** — one primary improvement
and one risk-focused prediction — but each must target a **different category**. This
prevents compound predictions while acknowledging dual effects.

## How to Append an Entry

### Step 1: Check the decision gate

Read the changelog entry that was just written. Does it pass the decision gate above?
If not, skip — do not record a hypothesis.

### Step 2: Determine the date heading

Read the first ~30 lines of `.ai/improvement-hypotheses.md` (after the header) to
check if today's date heading (`## YYYY-MM-DD`) already exists.

- If it exists: insert the new entry DIRECTLY UNDER the date heading — newest-first *within*
  the day, matching the file's reverse-chronological contract (same rule as `ai-changelog`
  Step 1; a same-day append-at-end once separated a changelog entry from the review that
  reviews it).
- If it does not: add a new date heading after the `---` separator, before existing
  date headings.

**Ordering invariant:** date headings are strictly reverse-chronological — a new/target
date heading must sort ABOVE the current top heading. NEVER append an entry at the file
end or under whatever heading happens to be last. Misfiling an entry under a stale heading
corrupts every window-based validation that reads it.

### Step 3: Draft the hypothesis

1. Identify the **category** — which of the 7 does this change primarily improve?
2. Write the **hypothesis** using "By X, we expect Y because Z"
3. Write the **signal** — what would you observe in the next 2-4 weeks if the
   hypothesis is true? What would you observe if it's false?
4. Consider the **risk** — could this change have a negative side-effect?

### Step 4: Quality check

Before writing, verify:
- [ ] Hypothesis is NOT a restatement of the changelog "Why" field
- [ ] Hypothesis names a specific causal mechanism (the "because" clause)
- [ ] Signal describes something observable, not aspirational
- [ ] Signal cites only instruments that exist right now (verified with Glob/git, not assumed)
- [ ] Category is a single value from the taxonomy
- [ ] If 2 hypotheses, they target different categories

### Step 5: Write and verify (structural, not eyeballed)

Append the entry, then run the data-file lint:

```
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint hypotheses
```

It checks heading order, heading-vs-`Changelog ref` date consistency, the category and
status vocabularies, and required fields for new entries. Fix any finding before moving on.

## Integration Points

Called by the same workflows as `ai-changelog`, immediately after the changelog step:

| Caller | When called | Trigger |
|--------|-------------|---------|
| `skill-creator` | Phase 5 (Registration) | After changelog entry |
| `skill-creation-workflow` | Phase 9 (Present Results) | After changelog entry |
| `learning-consolidator` | Phase 7 (Summary Report) | After changelog entry |
| `post-task-review` | Step 8 (Learnings) | After changelog entry, if infra files modified |
| `task-learnings` | Step 7 (Changelog) | After changelog entry, if rules updated |

## Calibration Examples

### Good: New skill with specific signal

```markdown
### [SKILL-ADDED] openai-realtime-quirks reference skill
- **Category:** Consistency
- **Hypothesis:** By codifying OpenAI Realtime API quirks into a reference skill, we expect fewer external-service-related bugs in realtime voice features because developers will consult known quirks before implementation rather than rediscovering them.
- **Signal:** Fewer learnings entries about OpenAI Realtime surprises in the 4 weeks following skill creation.
- **Risk:** The skill may become stale as OpenAI updates their API, creating false confidence in outdated quirks.
- **Status:** PENDING
- **Changelog ref:** 2026-04-01 — SKILL-ADDED: openai-realtime-quirks reference skill
```

### Good: Convention change with risk

```markdown
### [CONV-ADDED] Explicit enum handling for AI-parsed fields
- **Category:** Quality
- **Hypothesis:** By adding explicit enum handling guidance to AGENTS.md, we expect fewer runtime AttributeError crashes in AI-parsed responses because the convention eliminates the ambiguity between .value and str().
- **Signal:** Zero enum-related crashes in production logs for the 2 weeks following the convention addition.
- **Risk:** Developers may over-apply str() to fields that are already strings in use_enum_values=True models, creating redundant wrapping.
- **Status:** PENDING
- **Changelog ref:** 2026-03-15 — CONV-ADDED: Explicit enum handling for AI-parsed fields
```

### Bad: Restates the "Why" (circular)

```markdown
### [INFRA-ADDED] AI Infrastructure Changelog system
- **Category:** Observability
- **Hypothesis:** By creating a changelog, we expect to have a historical record of changes.
```

Why bad: The hypothesis just restates the changelog's "Why" field. There is no causal
mechanism, no specific expected improvement beyond the obvious purpose of the change.

### Bad: Compound and unmeasurable

```markdown
### [SKILL-ADDED] Some new skill
- **Category:** Quality
- **Hypothesis:** This will improve quality, speed, and developer experience across all workflows.
```

Why bad: Three categories in one, no mechanism, no signal, no specificity.

### Skip decision: Administrative change

Changelog entry: `INFRA-MODIFIED: Updated CLAUDE.md skill listings`

Decision: **Skip** — purely administrative sync, no behavioral change expected.

## File Size Management

Hypotheses with `PENDING` status must persist until validated — never archive or delete
them; they are the backlog for validation.

Terminal entries do NOT accumulate in the hot file: `hypothesis-validator`'s archive-rotation step rotates
every entry resolved before the latest pass to `.ai/improvement-hypotheses-archive.md`,
and the lint's `meta-synthesis due` NOTE (≥10 unsynthesized terminal verdicts, computed
from the hot-file header's `Last meta-synthesis` marker) triggers the aggregate read that
turns verdicts into design rules.

## Anti-Patterns

- Do NOT record hypotheses for every changelog entry — use the decision gate
- Do NOT restate the changelog "Why" as the hypothesis — add causal reasoning
- Do NOT write compound hypotheses covering multiple categories — split them
- Do NOT record retroactive hypotheses for past changes — hindsight bias corrupts predictions
- Do NOT modify hypothesis Status — that is reserved for the `hypothesis-validator` skill
  (invoked via learning-consolidator Phase 6.5); interim evidence goes in `Validation notes:`
- Do NOT modify the changelog to link back to hypotheses — keep the formats independent
- Do NOT selectively interpret signals to confirm a hypothesis — record disconfirming evidence with equal weight (confirmation bias)
