---
name: learning-consolidator
description: >
  Deep-analyze .ai/learnings.md entries for relevance and actuality, then promote findings
  into AI skills, conventions, rules, or AGENTS.md updates. Use to convert accumulated
  learnings into permanent project rules and skills (~weekly cadence). Use when the user
  says "consolidate learnings", "review learnings", "process learnings", "clean up
  learnings", or "weekly learning review".
argument-hint: "[--dry-run | --category <name>]"
metadata:
  type: workflow
---

# Learning Consolidator — Weekly Knowledge Promotion Pipeline

## Role

You are a Knowledge Architect performing a deep, systematic review of accumulated project
learnings. Your goal is to extract maximum value from each entry by promoting actionable
knowledge into the project's AI infrastructure (skills, conventions, rules) and then
cleaning up processed entries so the file stays lean and useful.

How you reason: evidence-based, consolidation-first, skeptical of stale knowledge.
You verify each entry against the current codebase before deciding its fate.

## When This Skill Activates

- User wants to consolidate accumulated learnings (~weekly cadence)
- ANY entries have accumulated in the `.ai/learnings.md` intake buffer — it is a lean intake
  buffer (post-2026-06-23 model), not a store; do NOT wait for it to grow large
- User says "consolidate learnings", "review learnings", "process learnings"
- User wants to clean up the learnings file after extracting value

## Arguments

**Received:** $ARGUMENTS

- `--dry-run` — Analyze and report but do not modify any files. Produces the analysis report only.
- `--category <name>` — Process only entries in the specified category. Matching is a case-insensitive substring of the section title (e.g. `pitfall` → "Common Pitfalls", `architecture` → "Architecture Decisions").

## Pipeline

### Phase 1: Inventory & Cluster Detection

0. **Cadence guard** — count intake entries (`python
   python -m lemmi_ai_kit lint learnings --list-entries`) and read the
   newest `CONSOLIDATION` entry date in `.ai/ai-changelog.md`. Proceed when intake > 0 AND the
   last consolidation is ≥7 days old — or whenever the user explicitly asked. Otherwise report
   why not ("buffer empty" / "last drain {D} days ago — fresh") and stop. This is the pair of
   `session-retrospective` Phase 0; that skill's ending also nudges THIS one when it is overdue.
   Cadence: measured **~5 entries/day** (REFUTED twice — draining does not slow intake, do not
   re-predict it), so the >25 NOTE fires in ~5 days and weekly is the FLOOR; if volume is the
   concern the lever is capture-side selectivity at `task-learnings`, not more drains.
   **Then verify the PREVIOUS drain landed — its plan is a claims sheet.**
   `.ai/consolidation-plan-2026-08-03.md` is headed "EXECUTED" and lost **18 of its 37** promotions:
   uncommitted edits in a tree several sessions were stashing through, and the only symptom was the
   buffer failing to shrink (work looked pending AND done, so neither artifact contradicted the
   other). Run `git log --oneline --all --grep=CONSOLIDATION -- AGENTS.md`; with no commit naming
   that drain, re-verify each promotion at its **named target** and treat still-present entries as
   un-drained rather than duplicates.
1. Read `.ai/learnings.md` in full.
2. **Deferred-work pickup** — check `tasks/TECH-deferred-consolidation-*.md` and the most
   recent `.ai/consolidation-plan-*.md` for open/deferred items. Carry each still-open item
   into this run's consolidation plan (re-verify it against the live skill/codebase first —
   coverage may have shifted since it was deferred). Deferred ≠ dropped only if something
   re-surfaces it; this step is that something.
3. Count entries per category. The canonical category set is defined in
   `../task-learnings/references/learnings-format.md` (§ Canonical Categories) —
   the single source of truth shared with the producer (`task-learnings`). Report the inventory:
   ```
   Learnings Inventory:
   - Architecture Decisions: N
   - Common Pitfalls: N
   - External Service Quirks: N
   - Performance Insights: N
   - Pattern Discoveries: N
   - Convention Clarifications: N
   - Interaction & Workflow Friction: N
   - <each legacy/transitional section found, verbatim>: N
   - Total: N
   ```
   Legacy or transitional section names (pre-redistribution categories such as "Prompt
   Engineering for AI Skills", carried-over intake sections) may still exist — inventory each
   verbatim and drain its entries to canonical homes; never create new non-canonical sections.
4. If `--category` was specified, filter to only that category's entries for subsequent phases.

> **Section placement is not evidence of intent.** Time-bucket catch-all drift, and how to
> audit for it, is in [references/consolidation-actions.md](references/consolidation-actions.md)
> § Section-Placement Audit. Read it before trusting per-section counts.

5. **Cluster detection** — Scan for groups of 3+ entries that share a common theme or domain
   across categories. Clusters are candidates for PROMOTE_TO_SKILL (reference skill).

   Clustering signals:
   - Same domain keywords appearing across entries (e.g., "prompt", "VAD", "WebSocket")
   - Entries from different dates/contexts that describe the same system or pattern
   - A category with 5+ entries where most share a root concern

   Report detected clusters:
   ```
   Detected Clusters:
   - "Prompt Engineering" (8 entries across Prompt Engineering, Specification Engineering)
     → Reference skill candidate
   - "OpenAI Realtime" (4 entries across External Service Quirks, Common Pitfalls)
     → Reference skill candidate or AGENTS.md section
   ```

### Phase 1.5: Near-Duplicate Detection & Retrospective Cross-Link

**Near-duplicates** — scan for PAIRS of entries that describe the SAME underlying insight (not just
the same domain). Signals: near-identical titles, the same root cause stated twice, or one entry's
Impact restating another's Finding. Flag each pair as a `MERGE_ENTRIES` candidate. This is distinct
from a 3+-entry cluster (a skill candidate): two entries on one insight is a merge, not a skill.

```
Near-duplicate candidates:
- "[date] Patch targets must point to where used" ≈ "[date] patch() string targets" → MERGE
```

**Retrospective cross-link** — if `.ai/retrospectives/` contains reports, read the most recent one's
**Recurring-Mistake Taxonomy** and **Convention Gap** sections. For each learning, check whether it
maps to a behavior the agent **repeatedly got wrong in real sessions** (a taxonomy row with ≥2
sessions). Record the cross-link on the entry — it raises that entry's promotion priority in Phase 2
(see PROMOTE_TO_RULE "Retrospective-backed priority" in
[references/consolidation-actions.md](references/consolidation-actions.md)). A learning the
retrospective proves is *still being violated* is the strongest promote-to-rule signal there is.

```
Retrospective cross-links (from .ai/retrospectives/{date}-retrospective.md):
- "[date] re-read hot prompt files before editing" ↔ recurring "edit-stale-read" in 4 sessions
  → HIGH-PRIORITY PROMOTE_TO_RULE (rule predates the recurrences → existing guidance is too weak)
```

**Recommendation lifecycle** — also read the latest retro report's **Recommendations** section
(all P1–P5 items) and — cross-checking its own "Prior-Report Reconciliation" table if present —
classify each item: **applied** (verify by grep/read, not memory) | **superseded** | **still
open**. Still-open items enter this run's consolidation plan: P1/P2 as promotion/update
candidates, P4 as expected intake entries (flag if the intake buffer never received them).
Recommendations with no tracked lifecycle silently evaporate — this closes that loop from the
consumer side.

### Phase 2: Entry-by-Entry Analysis

For **each** entry, perform this analysis using category-specific verification strategies.

#### Step 1: Actuality Check

Verify the entry is still accurate against the current codebase. Each category has a
specific verification approach — consult the "Category-Specific Verification Strategies"
section in [references/consolidation-actions.md](references/consolidation-actions.md).

The core question: does the file, module, class, API, or pattern described in the entry
still exist and behave as described?

Use the entry's routing fields when present: `Verify-at:` names the anchor to grep first;
a `Scope: branch:<x>` / `Scope: until:<event>` whose boundary has passed makes the entry an
ARCHIVE candidate (expired) without further analysis — confirm the boundary passed, don't
re-litigate the content.

Parked patterns rot mechanism-first, and a grep alone does not prove one is still true -- see
[references/consolidation-actions.md](references/consolidation-actions.md) § Verifying Parked Patterns.

**Decision:** `CURRENT` | `STALE` | `SUPERSEDED`

If `STALE` or `SUPERSEDED`: mark for archival with reason.

#### Step 2: Coverage Check

Determine if the entry's knowledge is already captured elsewhere:

| Check against | How |
|---------------|-----|
| `AGENTS.md` | Grep for key terms from the entry's Finding/Impact |
| `.claude/skills/*/SKILL.md` | Grep for the pattern or rule described |
| `.cursor/rules/*.md` | Grep for matching guidance |
| `.kiro/steering/*.md` | Grep for matching guidance |

**Decision:** `NOT_COVERED` | `PARTIALLY_COVERED` | `FULLY_COVERED`

If `FULLY_COVERED`: mark for archival — "Already in {file}".
If `PARTIALLY_COVERED`: mark for promotion to fill the gap.

#### Step 3: Promotion Classification

For entries that are `CURRENT` and `NOT_COVERED` or `PARTIALLY_COVERED`, classify the
promotion action. Use the decision criteria in
[references/consolidation-actions.md](references/consolidation-actions.md):

| Action | When to use |
|--------|-------------|
| `PROMOTE_TO_RULE` | Entry describes a **universal** convention, anti-pattern, or mandatory practice (applies across features) |
| `PROMOTE_TO_SKILL` | Cluster of 3+ related entries reveals a repeatable body of knowledge worth capturing as a skill |
| `UPDATE_SKILL` | Entry refines or extends an existing skill's instructions |
| `PROMOTE_TO_README` | **Subsystem-specific** convention or gotcha → that module/feature `README.md`, not the always-loaded surface |
| `PROMOTE_TO_COMMENT` | **Invariant guard** a future edit could silently break → co-located code comment at the exact site |
| `MERGE_ENTRIES` | Multiple entries describe the same insight from different angles |
| `KEEP` | Entry is valuable context but not yet promotable (too specific, too recent). **Max dwell: 2 consolidations** — then promote it to a home or drop it |
| `ARCHIVE` | Entry is stale, superseded, or fully covered |

Record the classification and target (which file to update or create) for each entry.

**Routing-field hints (when the entry carries them):** `Home:` seeds the action/target
(`tasks:<file>` → the work lane: verify the named task doc exists or create it, then the entry
archives once the task carries the work; `agents-rule`/`skill:<name>`/`readme:<path>`/`comment:`
map to the actions above). `Enforce-via:` biases the promotion: when it names `lint`/`test`/
`template`/`script`, prefer landing the guidance at that mechanical seam over prose — the
measured record is that mechanical seams change behavior and prose only raises probability.
Hints are VERIFIED, never followed blindly: a wrong `Home:` or a renamed `Verify-at:` symbol is
expected (entries can be written on another branch — grep every promoted symbol against the
current branch).

**Retrospective priority boost:** any entry that Phase 1.5 cross-linked to a recurring real-session
mistake jumps to the top of the `PROMOTE_TO_RULE` queue — the retrospective is evidence the current
guidance is insufficient. If a rule already exists but the mistake still recurs *after* the rule's
date, the action is "strengthen the rule / add a worked example", not "already covered → archive".

### Phase 3: Consolidation Plan

Before making any changes, present a consolidation plan to the user:

```
## Consolidation Plan

### Promotions (N entries)
| # | Entry Title | Action | Target | Rationale |
|---|-------------|--------|--------|-----------|
| 1 | [title]     | PROMOTE_TO_RULE | AGENTS.md "Do not" section | [why] |
| 2 | [title]     | UPDATE_SKILL | task-learnings SKILL.md | [why] |
| ...

### New Skills (N proposed)
| Skill Name | Type | Source Entries | Rationale |
|------------|------|---------------|-----------|
| [name]     | reference | [entry1], [entry2], [entry3] | [why this cluster is a skill] |

### Merges (N entries → M merged)
| Entries to merge | Merged title | Target |
|-----------------|--------------|--------|
| [entry1], [entry2] | [new title] | [where] |

### Archives (N entries)
| # | Entry Title | Reason |
|---|-------------|--------|
| 1 | [title]     | Stale — code removed in commit abc123 |
| 2 | [title]     | Fully covered in AGENTS.md line 42 |

### Keep (N entries)
| # | Entry Title | Reason to keep |
|---|-------------|----------------|
| 1 | [title]     | Too recent — needs more validation |
```

**STOP and wait for user approval before proceeding.**

If `--dry-run` was specified, stop here. Present the report and exit.

### Phase 4: Execute Promotions

For each approved promotion, execute the action:

#### PROMOTE_TO_RULE
1. Identify the correct target section in `AGENTS.md` (Conventions, "Do not", or specific subsection).
2. Draft the rule text — concise, imperative, consistent with surrounding style. If the rule
   governs how work is *performed* (evidence standards, citation discipline, verification
   thresholds), ask whether a **sub-agent** will ever do that work — if yes, route the operative
   text into the AGENTS.md spawn-preamble clause (the restate-in-every-spawn-prompt list), not only
   a main-thread bullet: rules outside the spawn prompt do not reach sub-agents (5 of 6 audited
   sub-agents violated a 2-week-old main-thread rule), while the preamble mechanism measured 0
   re-hits in 300 agents.
3. Add the rule to `AGENTS.md` at the identified location.
4. If the rule also needs a code example, check whether the installed language-conventions or architecture-patterns skill covers it. Add an example there only if the pattern is non-obvious.
5. **Cross-reference update** — Check [references/cross-reference-targets.md](references/cross-reference-targets.md) for files that must be updated when a rule is added to the target section. Update each one.

#### UPDATE_SKILL
1. Read the target skill's `SKILL.md` and any relevant `references/` files.
2. Identify the exact section to update.
3. Add the new guidance — keep it concise and consistent with existing style.
4. If the SKILL.md is approaching 500 lines, move detailed content to a reference file.
5. **Post-update validation** — After updating a skill, run a quick structural check:
   - SKILL.md still under 500 lines
   - No content duplicated from AGENTS.md
   - References still linked correctly

#### PROMOTE_TO_README
1. Identify the owning subsystem: `backend/app/core/<module>/README.md` or
   `backend/app/features/<feature>/README.md`.
2. If the README does not exist, create it with a short purpose header plus the new guidance
   (precedent: the 2026-06-23 redistribution created `backend/app/core/jobs/README.md`).
3. Add the guidance as a concise bullet in the README's conventions/gotchas section — match the
   file's existing style; state the constraint and the "why" in 1–3 lines.
4. Feature READMEs must stay in sync with `docs/onboarding/` (AGENTS.md rule) — check whether
   the matching onboarding doc needs the same note.

#### PROMOTE_TO_COMMENT
1. Locate the exact code site the invariant guards (file + line) — re-verify it still exists
   (if it moved or vanished, the entry may be `STALE`, not promotable).
2. Add a short co-located comment stating the constraint the code itself can't show (ordering
   requirement, hidden coupling, value that must stay in sync) — the "why", not the "what".
3. Keep it terse and durable; do not reference the learnings entry or this consolidation.

#### PROMOTE_TO_SKILL
The full procedure -- concept presentation, the approval gate, the `skill-creator` pass, the
`skill-reviewer` gate and the cross-reference updates -- is in
[references/consolidation-actions.md](references/consolidation-actions.md) § PROMOTE_TO_SKILL
(Execution). It is the longest of the actions and the one least often taken; read it there.

#### MERGE_ENTRIES
1. Write a single merged entry that combines the insights from all source entries.
2. Use the most recent date and the most comprehensive Finding/Impact.
3. The merged entry replaces all source entries.

### Phase 5: Clean Up learnings.md

After all promotions are executed:

> **Snapshot the buffer FIRST** — `cp .ai/learnings.md .ai/learnings-pre-drain-<date>.md`
> before any deletion, `cmp`-verify it, and **commit it alongside the drain**. Step 6's landing
> audit takes it as input, so an uncommitted or gitignored snapshot makes "zero entries deleted
> without a home" an assertion rather than evidence. Never `.ai/tmp/` (gitignored — the 2026-08-02
> drain's evidence is simply gone, and its two published tallies still disagree with nothing left
> to settle it). Full rationale: [references/consolidation-actions.md](references/consolidation-actions.md)
> § Pre-Drain Snapshot.

1. **Remove archived entries** — entries marked `ARCHIVE` are deleted entirely.
2. **Remove promoted entries** — entries whose knowledge is now fully captured in
   rules/skills are deleted entirely. No tombstones — the rule/skill is the authoritative
   source now, and the git history preserves the original entry.
3. **Replace merged entries** — remove source entries, insert the merged entry.
4. **Keep entries** — leave unchanged, but enforce the dwell limit: if an entry already
   survived the TWO previous consolidation runs as KEEP (check its date against the two most
   recent `CONSOLIDATION` entries in `.ai/ai-changelog.md`), KEEP is no longer available —
   promote it to a home or drop it. A lean buffer must not silently re-accumulate.
5. **Verify removal (structural, not eyeballed)** — run
   `python -m lemmi_ai_kit lint learnings`
   (zero findings required), then re-read `.ai/learnings.md` and confirm:
   - All promoted entries are removed
   - All archived entries are removed
   - Remaining entries are properly formatted
   - Category sections with no entries are removed (avoid empty sections)
   - File header and instructions are preserved
6. **Verify LANDING — mandatory, and NOT step 5's check.** Step 5 proves entries left the buffer; it
   is blind to an entry removed whose knowledge reached no home. Run `drain_audit.py` on the snapshot
   and adjudicate every flagged row: [§ Drain Landing Audit](references/consolidation-actions.md#drain-landing-audit).

### Phase 6: Cross-Reference Verification

After all changes are made, verify consistency across the project's AI infrastructure:

1. **Rule consistency** — For each new rule in AGENTS.md:
   - Grep all skill files for contradicting guidance
   - Grep cursor rules for stale references
   - Verify the rule doesn't duplicate an existing rule (different wording, same meaning)

2. **Skill consistency** — For each new or updated skill:
   - Verify it's listed in CLAUDE.md
   - Verify no content overlap with other skills
   - Verify references are linked and accessible

3. **Emit the per-row verification table** — "verify consistency" without a deterministic
   checklist produces silent misses (the 2026-06-23 redistribution updated `code-quality.md` +
   kiro but missed `.cursor/rules/learnings.md` even though the mapping file listed it). For
   EVERY row of [references/cross-reference-targets.md](references/cross-reference-targets.md)
   whose trigger fired this run, output:

   | Cross-reference target | Checked? | Result |
   |------------------------|----------|--------|
   | `.cursor/rules/learnings.md` | yes | updated / no-change-needed |
   | … one row per mapped target … | | |

   A target with no row is a miss — the table is the completion evidence, not a courtesy.

4. **Report any inconsistencies** found — these must be resolved before the consolidation
   is considered complete.

### Phase 6.5: Hypothesis Validation (via `hypothesis-validator`)

Close the feedback loop on `.ai/improvement-hypotheses.md`. The validation logic lives in
the dedicated internal task skill — read `../hypothesis-validator/SKILL.md` and
run its process here (one owner, multiple callers):

1. It enumerates `Status: PENDING` hypotheses, applies the **window guardrail** (never
   validate younger than the signal's window; interim evidence → dated `Validation notes:`,
   Status untouched), gathers evidence FOR and AGAINST (this run's analysis, retro §4g,
   changelog, fleet audits), and proposes `CONFIRMED | REFUTED | INCONCLUSIVE | SUPERSEDED`.
2. Fold its proposed status changes into the consolidation plan (Phase 3's approval gate
   covers them — no second prompt); execute only after approval, appending the
   `- **Resolution ({date}):** …` line per its Step 6.
3. `REFUTED` verdicts carry its mandatory follow-up action (adjust/revert the change, or
   record why it stays) — a refuted-with-no-action row is an incomplete plan item.
4. **Its lifecycle actions are plan items, never post-approval side effects.** Archive
   rotation and the Meta-Synthesis both **write** (`.ai/improvement-hypotheses.md` and the
   archive file), so they are *discovered* during Phases 1–2 and carried into the Phase 3
   plan with their targets named — which entries rotate, and whether the lint's synthesis-due
   NOTE is currently firing. Approval then covers them exactly as item 2's status changes.
   **This step runs after the gate, so anything it discovers for the first time here has not
   been approved:** if the NOTE only starts firing once this run's own verdicts land, do not
   execute it silently — present it as a one-line delta for a second approval, or carry it to
   the next run with a dated note. Discovery may happen late; writing may not.

### Phase 7: Changelog & Summary Report

**7a. Append changelog entry** — Read the `ai-changelog` skill and append a
`CONSOLIDATION` entry to `.ai/ai-changelog.md` summarizing all promotions, new skills,
rule additions, and archives from this consolidation run. Use the grouped format documented
in the ai-changelog skill.

**7b. Record improvement hypothesis** — Read the `ai-improvement-tracker` skill
and evaluate whether the consolidation warrants improvement hypotheses (e.g., promoted rules
expected to reduce specific error classes, new skills expected to improve consistency).

**7c. Draft the summary** — using the template in
[references/analysis-report-template.md](references/analysis-report-template.md), including a
section listing every file modified during the consolidation. **Do not present it yet** — Phase 8
routinely changes what it says.

### Phase 8: Consolidation Critic (MANDATORY — via `consolidation-critic`)

Read `../consolidation-critic/SKILL.md` and run its eight checks over this run's own
output, then present the reviewed summary. It is a `review`-type skill, so invoking it from this
workflow does not violate the max-1-level nesting rule (same relationship as
`spec-driven-dev` → `plan-critic`).

This is not a formality and not optional. The 2026-07-31 drain was believed complete when Phase 7
was drafted; the critic found **6 of 87 entries (7%) deleted without a home** — one of them
cross-referenced from a skill as if it existed — plus **4 false claims already written into
always-loaded rules**, an auto-loaded skill contradicting itself, and a provider claim promoted from
a single unverifiable forum post as fact.

Resolve every **Blocker** (deleted knowledge, a false claim already shipped) before reporting the
consolidation complete, and fold the critic's corrections into the Phase 7 changelog entry and
summary — including any headline figure the fixes invalidated. If a Blocker needs a decision only
the user can make, surface it at the top of the summary rather than reporting a clean run.

## Quality Gates

### Before promotion
- Every rule added to AGENTS.md must be grep-verified as not already present
- Every skill update must be read-verified against current SKILL.md content
- New skills must pass the skill-reviewer structural compliance checklist
- New rules must follow the imperative style of existing rules in the target section

### Before cleanup
- User has approved the consolidation plan
- All promotions have been executed successfully
- No entry is both promoted AND kept (mutually exclusive)

### After cleanup
- `.ai/learnings.md` is valid markdown with no broken formatting
- No empty category sections remain
- Entry count is reported (before → after)
- Cross-reference verification passed

## Error Handling

| Error | Recovery |
|-------|----------|
| Entry references deleted file/class | Mark as `STALE`, verify with `git log` if needed |
| Unclear if entry is covered | Default to `KEEP` — false negatives are safer than false positives |
| AGENTS.md section not found | Ask user where the rule should go |
| Skill update would exceed 500 lines | Move content to references/ instead |
| User rejects a promotion | Mark as `KEEP` and move on |
| Skill-reviewer finds Blockers in new skill | Fix before proceeding — do not skip validation |
| Cross-reference inconsistency found | Resolve before completing consolidation |

## Calibration Examples

Worked promote-vs-keep judgements (a good PROMOTE_TO_RULE, a good KEEP, and a premature
PROMOTE_TO_SKILL): [references/consolidation-actions.md § Calibration Examples](references/consolidation-actions.md#calibration-examples).

## Anti-patterns

- Do NOT promote entries that are too specific to one task or one-time fix
- Do NOT create new skills for single-use patterns — only for repeatable workflows or coherent knowledge bodies (3+ related entries)
- Do NOT merge entries that describe genuinely different insights even if in the same category
- Do NOT delete entries without user approval (the consolidation plan is the approval gate)
- Do NOT promote to both AGENTS.md AND a skill for the same rule — pick the authoritative home
- Do NOT route subsystem-specific gotchas or single-site invariants into AGENTS.md or skills —
  that re-bloats the always-loaded surface; use `PROMOTE_TO_README` / `PROMOTE_TO_COMMENT`
- Do NOT leave tombstone entries ("Promoted to: X") — delete promoted entries cleanly
- Do NOT skip skill-reviewer validation when creating new skills during consolidation
- Do NOT create cursor rules or kiro steering docs without checking existing ones for overlap
