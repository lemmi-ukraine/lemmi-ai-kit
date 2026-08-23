# Consolidation Actions — Decision Criteria

## Action Types

### PROMOTE_TO_RULE

Add the entry's knowledge as a convention or anti-pattern rule in project configuration.

**Criteria (ALL must be true):**
- The entry describes a repeatable pattern, convention, or anti-pattern
- The entry has been validated by at least one real task (not theoretical)
- The knowledge applies across features, not just one specific file
- The entry is not already covered in AGENTS.md or skill files

**Target selection:**

| Entry describes... | Target location |
|-------------------|-----------------|
| Something to never do | `AGENTS.md` → "Do not" section |
| How to structure code | `AGENTS.md` → relevant Conventions subsection |
| A Python-specific pattern with code example | `python-conventions` skill |
| An architecture pattern with directory structure | `vertical-slice` skill |
| A testing convention | `AGENTS.md` → Testing subsection |
| An external API behavior to remember | `AGENTS.md` → relevant Backend subsection |
| A prompt engineering principle | Evaluate for `PROMOTE_TO_SKILL` instead |

**Writing style:**
- Match the imperative, concise style of existing rules in the target
- One bullet point per rule in AGENTS.md (no sub-bullets)
- Include the "why" only if the rule is non-obvious

**Retrospective-backed priority (strongest promote signal):**
If the latest `.ai/retrospectives/` report shows this learning maps to a recurring-mistake
taxonomy row with ≥2 sessions, it is top-priority for PROMOTE_TO_RULE — real sessions prove the
current guidance is insufficient. Date-check first (per the retrospective's causation rule):
- Rule/learning **predates** the recurrences → existing guidance is too weak: strengthen the rule
  or add a worked example (do NOT archive as "already covered").
- Rule/learning **postdates** (or there is none) → straightforward PROMOTE_TO_RULE.
Cite the retrospective (date + category + session count) in the consolidation plan's rationale.

### PROMOTE_TO_SKILL

Create a new skill or major skill component based on a cluster of related entries.

**Criteria (ALL must be true):**
- A cluster of 3+ related entries forms a coherent body of knowledge
- The knowledge would benefit from structured guidance (not just a bullet in AGENTS.md)
- The knowledge is used frequently enough to justify a dedicated skill
- A single AGENTS.md rule cannot adequately capture the nuance

**Skill type selection:**

| Cluster pattern | Skill type | Example |
|----------------|------------|---------|
| Domain knowledge with principles and examples | Reference | prompt-engineering conventions |
| Debugging/operational runbook | Task | debug-openai-realtime |
| Repeated multi-step process | Workflow | (rare — most workflows already exist) |
| Review criteria for a specific artifact type | Review | (rare — extends existing reviewers) |

**Process:**
1. Present the skill concept for user approval
2. Create using `/skill-creator` methodology (5-phase pipeline)
3. Validate using `/skill-reviewer` checklist
4. Register in CLAUDE.md
5. Create thin cursor rule reference

**When NOT to create a skill:**
- Fewer than 3 related entries — use PROMOTE_TO_RULE instead
- Entry describes a one-time process — not a skill
- Entry is about a specific bug fix — not a skill
- Knowledge fits naturally as an extension to an existing skill — use UPDATE_SKILL

### UPDATE_SKILL

Extend or refine an existing skill's instructions or references.

**Criteria (ANY is sufficient):**
- The entry reveals a gap in an existing skill's coverage
- The entry provides a better example or pattern for an existing skill step
- The entry describes a failure mode that an existing skill should warn about

**Process:**
1. Identify the most relevant existing skill
2. Determine if the update goes in SKILL.md or a reference file
3. Keep the update concise — add a bullet, a row in a table, or a short paragraph
4. If SKILL.md would exceed 500 lines, use a reference file
5. Verify the update doesn't contradict existing content

### MERGE_ENTRIES

Combine multiple entries that describe the same underlying insight.

**Criteria (ALL must be true):**
- Entries describe the same root cause or pattern
- Entries were discovered in different contexts (proving the pattern is general)
- A single merged entry would be more useful than the individual entries

**Merge rules:**
- Use the most recent date
- Combine contexts into a single Context field (list the situations)
- Write a unified Finding that captures the generalized insight
- Write an Impact that covers all the action items from source entries
- Use the most fitting category

### KEEP

Leave the entry in learnings.md for future reference.

**Criteria (ANY is sufficient):**
- Entry is less than 2 weeks old (needs more validation time)
- Entry is highly specific and valuable but doesn't generalize to a rule
- Entry provides important context that would be lost if reduced to a rule
- Unclear whether the entry is still relevant — needs investigation
- Entry is about an external service quirk that may change

**Default action:** When in doubt, KEEP. False negatives (keeping something that should be promoted) are low-cost. False positives (promoting something prematurely) create rule bloat.

### ARCHIVE

Remove the entry from learnings.md entirely.

**Criteria (ANY is sufficient):**
- The code/module/API the entry references no longer exists
- A newer entry explicitly supersedes this one
- The entry's knowledge is fully captured in AGENTS.md or a skill file
- The entry describes a one-time bug fix with no generalizable lesson

**Archive protocol:**
- Stale entries: delete entirely (no tombstone)
- Superseded entries: delete entirely (the newer entry remains)
- Fully covered entries: delete entirely (the rule/skill is the authoritative source)
- Git history preserves the original entry for audit purposes

## Category-Specific Verification Strategies

Each learnings category requires different verification approaches during the Actuality Check.

### Architecture Decisions
**Verify by:** checking that the module, pattern, or structural convention still exists.
- Glob for the files/directories mentioned in the entry
- Grep for the class or pattern name in current code
- If the entry mentions a migration or restructuring, verify it was completed

### Common Pitfalls
**Verify by:** confirming the problematic code path or API is still in use.
- Grep for the function/class name mentioned in the entry
- Check if the pitfall was fixed by a subsequent change (git log the file)
- If it's a test pitfall, verify the test file still exists and uses the pattern

### External Service Quirks
**Verify by:** checking SDK version and API behavior.
- Read `pyproject.toml` for the SDK version (e.g., `openai` package version)
- If the quirk is version-specific, check if we've upgraded past it
- If the quirk describes API behavior, assume CURRENT unless SDK major version changed

### Performance Insights
**Verify by:** confirming the optimization is still in place.
- Grep for the optimization technique (e.g., batching, caching)
- Verify the configuration values mentioned are still current
- If the entry mentions specific latency numbers, they may be outdated but the principle may hold

### Pattern Discoveries
**Verify by:** confirming the pattern is still the recommended approach.
- Check if the pattern is still used in the codebase
- Verify no newer pattern has replaced it
- Cross-reference with any related entries that might supersede

### Convention Clarifications
**Verify by:** checking that the convention is still followed in current code.
- Grep for the convention pattern in recent code
- Check if AGENTS.md or a skill already codifies this convention
- If the convention was clarified due to confusion, verify the confusion source is still present

> **Legacy sections (tolerated until drained).** The three strategies below cover
> pre-redistribution section names that are NOT part of the canonical set (see
> `../task-learnings/references/learnings-format.md` § Canonical Categories).
> Use them only if such a section still exists in `.ai/learnings.md`; drain those entries to
> canonical homes and never create new entries under these names.

### Prompt Engineering for AI Skills (legacy)
**Verify by:** checking against current prompt files and skill definitions.
- Read the relevant prompt template files to verify the technique is still in use
- Check if the skill mentioned still uses the described approach
- Cross-reference with other prompt engineering entries for contradictions

### Specification Engineering
**Verify by:** checking spec templates and guides.
- Read the templates in `.ai/templates/` to verify they match the entry's guidance
- Check if `spec-driven-dev` skill has incorporated this guidance
- Verify the spec pipeline steps still align

### Feature-Specific AI Pipelines
**Verify by:** checking against the feature's current service code (e.g., a category tracking a feedback-generation pipeline).
- Read the feature's service models and prompt builders
- Verify the Pydantic model field ordering is as described
- Check if the prompt structure still uses the described pattern

## Cluster Detection Criteria

A cluster is a group of entries that together form a coherent body of knowledge.

### Identifying clusters

1. **Keyword overlap** — 3+ entries share domain-specific keywords (e.g., "prompt", "VAD", "structured output")
2. **Cross-category coherence** — Entries from different categories that describe the same system or domain
3. **Progressive depth** — Entries that build on each other (entry A describes the problem, entry B the pattern, entry C the anti-pattern)
4. **Practitioner knowledge** — Entries that together would form useful guidance for someone new to the domain

### Cluster → Skill suitability

A cluster is suitable for skill promotion when:
- It contains 3+ entries (hard minimum)
- The combined knowledge exceeds what a single AGENTS.md rule can capture
- The entries describe principles, patterns, AND anti-patterns (not just facts)
- The knowledge would be useful across multiple future tasks

A cluster is NOT suitable when:
- All entries are about the same specific bug or incident
- The entries are just factual observations with no actionable guidance
- The knowledge is already well-documented in external sources (SDK docs, etc.)

## Decision Flowchart

```
Entry Analysis Start
       │
       ▼
┌─────────────────┐      NO    ┌──────────┐
│ Still accurate?  │───────────▶│ ARCHIVE  │
│ (use category-   │            │ (STALE)  │
│  specific check) │            └──────────┘
└────────┬────────┘
         │ YES
         ▼
┌─────────────────┐     YES    ┌──────────┐
│ Superseded by    │───────────▶│ ARCHIVE  │
│ newer entry?     │            │(SUPERSEDED)
└────────┬────────┘            └──────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌──────────┐
│ Fully covered    │───────────▶│ ARCHIVE  │
│ in rules/skills? │            │(COVERED) │
└────────┬────────┘            └──────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌──────────┐
│ Partially        │───────────▶│ UPDATE   │
│ covered?         │            │ _SKILL   │
└────────┬────────┘            └──────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌──────────────┐
│ Generalizable    │───────────▶│ PROMOTE_TO   │
│ rule/convention? │            │ _RULE        │
└────────┬────────┘            └──────────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌──────────────┐
│ Part of a        │───────────▶│ Check: 3+    │
│ detected cluster?│            │ in cluster?  │
└────────┬────────┘            │  YES→SKILL   │
         │ NO                  │  NO →KEEP    │
         ▼                     └──────────────┘
┌─────────────────┐     YES    ┌──────────────┐
│ Mergeable with   │───────────▶│ MERGE        │
│ similar entries? │            │ _ENTRIES     │
└────────┬────────┘            └──────────────┘
         │ NO
         ▼
      ┌──────┐
      │ KEEP │
      └──────┘
```

## Drain Landing Audit

Phase 5's removal check and this landing check are **different failures**. Removal verification
proves entries left the buffer. It is structurally blind to the opposite failure: an entry removed
whose knowledge reached no home — deleted, not promoted.

Hand-counting does not catch this at drain scale. The 2026-07-31 drain's manual accounting reported
~60 entries promoted and read as complete; this audit found **6 of 87 (7%) had landed nowhere**,
including a rule the same consolidation then cross-referenced from a skill as if it existed —
a dangling pointer to knowledge it had just deleted.

Run it against the pre-drain snapshot (Phase 5 requires taking one before any deletion):

```bash
python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <pre-drain-snapshot>.md HEAD
```

For each entry the script extracts its most distinctive backticked identifiers and greps every
promotion surface (AGENTS.md, CLAUDE.md, `docs/`, skills, cursor rules, kiro steering, module and
feature READMEs, backend source, task docs). Zero hits ⇒ `[LOSS?]`.

**Adjudicate every flagged row by hand and record the verdict.** Two row classes are expected-clean:

| Row class | Why it is fine |
|---|---|
| ARCHIVED entries | Already covered elsewhere, stale, or superseded — by design they have no new home |
| Entries whose only probe tokens are incidental | e.g. a file path mentioned once in the anecdote; the lesson landed under different wording |

Anything else is knowledge deleted without a home: **recover it from the snapshot and promote it
before proceeding.** Do not delete the snapshot until the audit is clean.

The `no probe tokens` list needs the same treatment — those entries carry no backticked identifiers
at all, so the script cannot speak to them and a human must confirm each one landed.

> Keep `TARGET_GLOBS` in the script in sync with the promotion surfaces above. A missing glob
> produces false `[LOSS?]` rows, which trains readers to skim the output — the same
> noisy-check-gets-ignored failure the entry-integrity lint was tightened to avoid.

## Calibration Examples

### Good: Entry that should be PROMOTE_TO_RULE

```
### [2026-03-04] Shared exceptions over HTTPException for standard errors
- Finding: Using HTTPException directly in routes bypasses the middleware error shaping pipeline.
- Impact: Always use shared exceptions in routes. Only use HTTPException for non-standard status codes.
```

Why PROMOTE_TO_RULE: describes a mandatory convention, validated in production, applies across all features,
expressible as a single imperative rule in AGENTS.md's "Do not" section.

### Good: Entry that should be KEEP

```
### [2026-03-14] OpenAI response.audio.delta events arrive out of order under high load
- Finding: Under sustained load, audio delta events occasionally arrive with sequence numbers
  that skip ahead, causing playback gaps.
- Impact: May need client-side reordering buffer.
```

Why KEEP: only 1 day old, observed once, needs more validation before becoming a rule.
Could be a transient API issue.

### Bad: Premature PROMOTE_TO_SKILL

An entry about a single debugging technique (e.g., "log timeline analysis for OpenAI Realtime")
should NOT become a skill on its own — it's one technique, not a coherent body of knowledge.
It should be PROMOTE_TO_RULE or KEEP until 2+ related entries form a cluster.

## Pre-Drain Snapshot (Phase 5)

**Snapshot the buffer FIRST** — copy it to `.ai/learnings-pre-drain-<date>.md` before
any deletion. Step 6 requires it, and it is the only recovery path if the drain goes wrong.

**Do NOT put it in `.ai/tmp/`.** That directory is gitignored, so a snapshot
there can never be committed, never reaches a reviewer, and is routinely swept. One drain
named a snapshot under `.ai/tmp/` as its evidence; the file no longer
exists, and the run's two published tallies of the same audit disagree (the changelog says
5 archived-as-covered / 2 not-drained / 5 probe-token artifacts, the hypotheses ledger says
4 / 2 / 3) with nothing left to re-run and settle it. A landing audit whose input is
unreproducible cannot support a "zero entries deleted without a home" claim — it is an
assertion, not evidence.

Commit the snapshot alongside the drain, and cite it by path in the changelog entry. Delete it
only after Step 6's audit is clean AND the drain has been merged.
