# Consolidation Actions — Decision Criteria

## Action Types

### PROMOTE_TO_RULE

Add the entry's knowledge as a convention or anti-pattern rule in project configuration.

**Criteria (ALL must be true):**
- The entry describes a repeatable pattern, convention, or anti-pattern
- The entry has been validated by at least one real task (not theoretical)
- The knowledge applies across features, not just one specific file
- The entry is not already covered in AGENTS.md or skill files
- The entry's Impact, taken as advice, breaks no standing policy of the project (its AGENTS.md
  rules and recorded rulings): advice a policy forbids is not promoted, and only its measured
  figures are kept, as data

**Target selection** (a sample; the homes the project's own AGENTS.md names replace it):

| Entry describes... | Target location |
|-------------------|-----------------|
| Something to never do (universally) | `AGENTS.md` → "Do not" section |
| How to structure code | `AGENTS.md` → relevant Conventions subsection |
| A language-specific pattern with code example | Installed language-conventions skill |
| An architecture pattern with directory structure | Installed architecture-patterns skill |
| A testing convention | `AGENTS.md` → Testing subsection |
| An external API behavior to remember | `AGENTS.md` → relevant Backend subsection |
| A prompt engineering principle | Evaluate for `PROMOTE_TO_SKILL` instead |
| A subsystem-specific gotcha (one module/feature) | Use `PROMOTE_TO_README` instead |
| An invariant guard at one code site | Use `PROMOTE_TO_COMMENT` instead |

**Scope test before promoting to AGENTS.md:** would every future session, in any feature,
benefit from this rule? If it only bites inside one subsystem or one code site, promoting it to
the always-loaded surface is bloat — route it to the README/comment homes instead.

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
2. Create using `/lemmi-ai-kit-skill-authoring:skill-creator` methodology (5-phase pipeline)
3. Validate using `/lemmi-ai-kit-skill-authoring:skill-reviewer` checklist
4. Register in CLAUDE.md
5. Create thin cursor rule reference

**When NOT to create a skill:**
- Fewer than 3 related entries — use PROMOTE_TO_RULE instead
- Entry describes a one-time process — not a skill
- Entry is about a specific bug fix — not a skill
- Knowledge fits naturally as an extension to an existing skill — use UPDATE_SKILL

**Execution.**

This is the most complex action. Follow this process:

It requires enabled `lemmi-ai-kit-skill-authoring`. If unavailable, keep these entries
in the buffer and report the native plugin prerequisite; do not bypass creation or
review. Resolve each named skill through the host's installed catalog and read its
resources relative to that skill, not the current core plugin.

> **Nesting rule:** apply the `skill-creator` and `skill-reviewer` *methodology inline* (read their
> SKILL.md files and follow the steps directly). Do NOT invoke the `skill-creation-workflow`
> workflow skill from here — a workflow invoking another workflow violates the max-1-level nesting
> rule (AGENTS.md "Do not").

1. **Present the skill concept** to the user with:
   - Proposed name (kebab-case)
   - Proposed type (Task, Reference, Review, Workflow)
   - Source entries that will be consolidated
   - One-paragraph summary of what the skill will contain
2. **Wait for user approval.**
3. **Create the skill following the `skill-creator` pipeline**
   (see the `skill-creator` skill for the full 5-phase process):
   - Phase 1 (Discovery): answers come from the clustered learnings
   - Phase 2 (Classification): use the skill taxonomy from `lemmi-ai-kit-skill-authoring:skill-reviewer (references/skill-taxonomy.md)`
   - Phase 3 (Build): create SKILL.md, references/ files as needed
   - Phase 4 (Validation): run the structural compliance checklist
   - Phase 5 (Registration): add to CLAUDE.md
4. **Validate quality using the `skill-reviewer` checklist**
   (see `lemmi-ai-kit-skill-authoring:skill-reviewer (references/review-checklist.md)`):
   - Run through all structural, description, invocation, and instruction checks
   - Fix any Blocker or Major findings before presenting
   - Report Minor findings to user
5. **Cross-reference update** — Create corresponding entries in:
   - `.cursor/rules/{skill-name}.md` (thin reference pointing to the skill)
   - Update `.kiro/steering/development-conventions.md` if the skill affects conventions
   - Update `AGENTS.md` workflow documentation if the skill changes the pipeline


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

### PROMOTE_TO_README

Route a subsystem-specific convention or gotcha to that subsystem's code-adjacent README —
the home the 2026-06-23 redistribution used for 46 of the 177 drained entries.

**Criteria (ALL must be true):**
- The knowledge is scoped to ONE module or feature (`backend/app/core/<module>/`,
  `backend/app/features/<feature>/`) — it doesn't generalize across features
- A session working in that subsystem needs it; sessions elsewhere don't
- It is guidance/context, not a single-site invariant (that's `PROMOTE_TO_COMMENT`)

**Target selection** (a sample; the homes the project's own AGENTS.md names replace it):

| Entry describes... | Target |
|-------------------|--------|
| A core-module behavior/constraint | `backend/app/core/<module>/README.md` |
| A feature-slice convention/gotcha | `backend/app/features/<feature>/README.md` |

**Rules:**
- Create the README if absent — short purpose header + the guidance (precedent:
  `backend/app/core/jobs/README.md`, created by the redistribution)
- Match the README's existing style; one concise bullet per lesson (constraint + why)
- Where the project's AGENTS.md pairs READMEs with docs (the sample pairs feature READMEs with
  `docs/onboarding/` feature docs), keep each pair in sync

### PROMOTE_TO_COMMENT

Plant an invariant-guard comment at the exact code site a future edit could silently break —
the home the redistribution used for 14 entries.

**Criteria (ALL must be true):**
- The knowledge guards ONE specific code site (ordering requirement, hidden coupling,
  value that must stay in sync with something elsewhere)
- The danger is a future *edit to that site* — not general subsystem work (that's README)
- The constraint is invisible from the code itself (otherwise no comment is needed)

**Rules:**
- Verify the site still exists first (moved/vanished → re-run the Actuality Check; likely `STALE`)
- State the constraint the code can't show — the "why", terse and durable
- Never reference the learnings entry, the consolidation, or dates — the comment must read as
  native code documentation

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

**Dwell limit (lean-buffer invariant):** an entry may be KEPT for at most **2 consolidation
runs**. To check: compare the entry's date against the two most recent `CONSOLIDATION` entries
in `.ai/ai-changelog.md` whose `**Drained:**` count is above 0 (one without the line counts as
drained) — if the entry predates both, KEEP is no longer available; this run must promote it to
a home (`RULE`/`SKILL`/`README`/`COMMENT`) or `ARCHIVE` it. An entry that keeps dwelling is
silent re-accumulation — the failure mode the intake-buffer model exists to prevent. Note
"highly specific and valuable" entries usually have a home: README or comment.

**Default action:** When in doubt (and within the dwell limit), KEEP. False negatives (keeping
something that should be promoted) are low-cost. False positives (promoting something
prematurely) create rule bloat.

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

> **Legacy sections (tolerated until drained).** The two strategies below cover
> pre-redistribution section names that are NOT part of the canonical set (see
> `../../task-learnings/references/learnings-format.md` § Canonical Categories).
> Use them only if such a section still exists in `.ai/learnings.md`; drain those entries to
> canonical homes and never create new entries under these names.

### Specification Engineering (legacy)
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
│ Subsystem-scoped │───────────▶│ PROMOTE_TO   │
│ (one module /    │            │ _README      │
│ feature)?        │            └──────────────┘
└────────┬────────┘
         │ NO
         ▼
┌─────────────────┐     YES    ┌──────────────┐
│ Invariant guard  │───────────▶│ PROMOTE_TO   │
│ at one code site?│            │ _COMMENT     │
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

Run it against the pre-drain snapshot: the buffer at the restore-point commit (Phase 5 requires
that commit before any removal), written to a scratch file by the operator. **The second argument,
the base ref, is mandatory, and which ref is correct depends on whether the promotions are
committed yet — this is the step's sharpest edge:**

```bash
# Promotions still UNCOMMITTED (drain and promote in one session): HEAD is the pre-promotion state.
python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <pre-drain-snapshot>.md HEAD

# Promotions ALREADY COMMITTED (the mandated promote -> commit -> delete order, or a later
# session finishing the drain): pass the commit BEFORE the promotion commit, never HEAD.
python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <pre-drain-snapshot>.md <promo-commit>~1

# Either case, with a home outside the ten default globs: one quoted --surface per glob.
python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <pre-drain-snapshot>.md HEAD --surface 'notes/**/*.md'
```

Passing `HEAD` after the promotions are committed makes the haystack ("lines ADDED since ref")
nearly empty, so every entry reads as a loss. Omitting the ref is the opposite and more dangerous
failure, so the script refuses it: with no ref it exits 2 and names the one flag that asks for the
other scan, `--current-contents`. That scan greps each target's CURRENT contents, where a token
that predates the drain counts as a landing. Measured on one buffer — `landed 96 / LOSS 7` with
the current-contents scan versus `landed 78 / LOSS 25` in sound mode, hiding **18** candidate losses
behind pre-existing tokens. Only the sound-mode figure may be quoted.

**Exit codes.** 0 is clean: every entry landed (under `--current-contents` an exit 0 is an upper
bound, never a clean audit). 1 is rows to adjudicate — a `[LOSS?]` row or a no-probe row remains —
and **exit 1 means rows to adjudicate**: it is neither a crash nor a pass, and a caller that gates
on the code must read it as "a human has work to do". 2 is a usage error or a run that could not
measure (no ref, an unreadable snapshot or one with no entry, a diff that could not be taken):
never read it as clean.

**Reconcile the report's coverage before trusting it.** The entry splitter matches only
`### [`-prefixed headings, so entries headed `### YYYY-MM-DD — Title` are invisible and nothing
reports the gap — the script prints its own parsed count as though it were the file's, and the
`lint` subcommand does not check the heading form either. On one drain that was **6 of 115** entries,
three of them dispositioned KEEP. Always check `entries scanned` against
`grep -c '^### ' <snapshot>` and hand-adjudicate the difference.

For each entry the script extracts its most distinctive backticked identifiers and greps every
promotion surface: its ten default globs (AGENTS.md, CLAUDE.md, `docs/`, skills, cursor rules, kiro
steering, task docs, and the READMEs and Python files under `src/`), plus each `--surface <glob>`
the run adds. Neither scan counts a file that holds or quotes the entries themselves, whatever the
globs match: the buffer (any `learnings.md`), the snapshot under audit (the path the run is given,
whatever its name), every byte copy (`learnings-pre-drain-*.md`; an older one still holds the KEEP
entries of earlier drains) and the two ledgers that quote what a drain removed (any
`ai-changelog.md`, any `improvement-hypotheses.md`), so a surface that reaches `.ai/` cannot land
an entry in its own copy or in the record of its removal. Zero hits ⇒ `[LOSS?]`.

**Adjudicate every flagged row by hand and record the verdict.** Two row classes are expected-clean:

| Row class | Why it is fine |
|---|---|
| ARCHIVED entries | Already covered elsewhere, stale, or superseded — by design they have no new home |
| Entries whose only probe tokens are incidental | e.g. a file path mentioned once in the anecdote; the lesson landed under different wording |

Anything else is knowledge deleted without a home: **recover it from the snapshot and promote it
before proceeding.** Do not delete the byte copy until the audit is clean.

The `no probe tokens` list needs the same treatment — those entries carry no backticked identifiers
at all, so the script cannot speak to them and a human must confirm each one landed.

> The ten defaults are `TARGET_GLOBS` in the script; keep the list above in sync with it. A home
> outside them (the project's own AGENTS.md names its homes) needs one `--surface <glob>` on every
> run: the option repeats, and it adds a glob without replacing a default. A missing glob produces
> false `[LOSS?]` rows, which trains readers to skim the output — the same noisy-check-gets-ignored
> failure the entry-integrity lint was tightened to avoid. Each glob, a default or a surface,
> reaches git as a `:(glob)` pathspec and the current-contents scan as the same glob, so `**/`
> matches zero or more directories and `*` never crosses `/`: `docs/**/*.md` includes `docs/x.md`,
> and `tasks/*.md` is that folder's own files only. A surface the two scans are known to read
> differently exits 2: an absolute path, a `..`, a backslash, or a directory (a trailing `/` or
> `**`, or a bare folder name; `notes/**/*` names its files). Three differences still pass, so write
> a plain glob in the tree's own case: letter case on a case-insensitive file system, a `[^...]`
> class, and a `**` inside a name on Python 3.11.

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

**Commit the buffer as it stands BEFORE the first removal, in its own commit.** That commit is the
**restore point**: the recovery path if the drain goes wrong, the input of Step 6, and what the
changelog entry cites, by commit id. The **pre-drain snapshot** (the term the consolidation critic and
the audit script's help use) is the buffer as committed at the restore point, read through a scratch
file.

**The commit and the copies are operator steps** ([§ Operator Steps](#operator-steps)): in their own
terminal the operator commits the buffer, makes a byte copy and confirms it is byte-identical, and
writes the buffer as it stands at the restore point to a scratch file outside the buffer's folder
(`git show <commit>:<path>` redirected to that file). The session never names the buffer on a shell
line. The audit script takes a file, not a commit, so the scratch file is what Step 6 is given, and it
can be rebuilt from the commit id whenever the audit has to be re-run. You then confirm with Grep in
count mode that the byte copy and the buffer hold the same number of entries, and cite the commit id
in the changelog entry.

**The byte copy is a local safety net and is never committed.** Keep it, for example at
`.ai/learnings-pre-drain-<date>.md`, until Step 6's audit is clean. It may live in an ignored folder
such as `.ai/tmp/`, because the restore point is the evidence and the copy is not.

**Why the snapshot is a commit and not a file in the drain.** A snapshot file committed with the drain
has to be removed before the merge, and removing a file breaks every citation that named its path
(observed once: one change had to rewrite eight). A commit is not removed before the merge, so citing
its id does not break the way citing a path does. Evidence that sits in a swept folder fails the
other way: one drain named a snapshot
under `.ai/tmp/` as its evidence; the file no longer exists, and the run's two published tallies of
the same audit disagree (the changelog says 5 archived-as-covered / 2 not-drained / 5 probe-token
artifacts, the hypotheses ledger says 4 / 2 / 3) with nothing left to re-run and settle it. A landing
audit whose input cannot be rebuilt cannot support a "zero entries deleted without a home" claim: it is
an assertion, not evidence, and an input rebuilt from the restore point is evidence.

**Confirm with a command that the byte copy IS ignored, and that the project's ignore file lists it and
the gate-record folder (`.ai/consolidation-gates/`), so neither can be staged by mistake:**

```bash
git check-ignore -v <byte-copy-path>;  echo "rc=$? (0 = ignored, good; 1 = NOT ignored, list it first)"
```

A copy or a record that is not ignored can be staged by a broad `git add`, and a committed copy is the
file this section rejects.

### Removing an entry stops at the next SECTION HEADER, not the next entry

When you delete a promoted entry, the span you remove runs from its `### ` heading to **whichever
comes first: the next `### ` entry or the next `## ` section header.** The naive "delete up to the
next `### `" span is correct for every entry except the **last one in its section** — there, it
swallows the following `## ` header, and every entry in the *next* section is silently re-filed
into the previous one. Nothing fails: the file stays valid markdown, the entry count is right, and
the corruption is only visible as a section whose contents no longer match its name.

This is the specific shape of the general rule that **an unprobed mutator is worse than an unprobed
checker** — a blind checker reports a wrong number, a blind edit script writes damage. One
self-written edit script left **79 entries misfiled and two section headers gone**, recovered only
from the pre-drain snapshot. So: assert the section-header count is unchanged before and after any
bulk removal, and re-run the structural lint.

## The handoff lint's dead-anchor check is an ON-DISK existence test, so it certifies UNTRACKED paths as durable

`_git_anchor_resolves` returns `True` for any path-shaped token that merely **exists on disk** (by
design — an untracked path still anchors a hand-off usefully). It therefore cannot distinguish a
durable, committed anchor from a gitignored scratch file — which is the one distinction a durability
claim needs.

Measured, with both controls:

| anchor | lint says | actually |
|---|---|---|
| `.ai/tmp/<scratch-report>.md` | resolves | **gitignored** |
| `tasks/<untracked-task-doc>.md` | resolves | **untracked** (`git ls-files --error-unmatch` exit 1) |
| `docs/this-file-does-not-exist-xyz.md` | dead | absent (true negative) |
| `deadbee` | dead | not a SHA (true negative) |

So a clean anchor line is evidence the path *exists here, now* — never that a future reader will find
it. When the durability of an anchor is what a promotion rests on, run the real check yourself:

```
git ls-files --error-unmatch <path>     # exit 0 = tracked
git show HEAD:<path> | wc -l            # non-zero = the CONTENT is committed, not just the path
```

Pair them: tracked-but-uncommitted passes the first and fails the second (see the `initiative-cleanup`
skill's `references/settle-lessons.md` § the third state).

## Section-Placement Audit

**Beware time-bucket catch-all sections.** `task-learnings`/manual appends tend to drop new entries
under the file's *last* `## ` header regardless of topic, so a section silently becomes a
chronological catch-all that misleads cluster detection (and your per-section counts). Verify
section boundaries by parsing the structure (count `### [` entries per `## ` section), not by
eyeballing — and re-file mis-placed entries.

**Check `Interaction & Workflow Friction` first — it is the file's LAST `## ` header AND its name
reads broad, so it is doubly exposed to catch-all drift.** Audit its entries against the
`interaction` vs `pitfall` test in `learnings-format.md` (does the finding turn on the CODE, or on
how the work was conducted?), not on the assumption that placement was deliberate. For any mass archive/re-file in later phases, use a
**dry-run script** that asserts each kill/move pattern matches **exactly once** and reports
the before/after entry-count delta; back up the file first. Botched edits to an append-log are silent
(entries vanish or malform with nothing failing).

## Buffer Copies and Parked Lessons

The cadence guard and Phase 1 read the checked-out buffer, and a drain that starts from that file
alone misses an entry only another copy holds: the entry stays out of every plan until that copy is
merged or popped. Before reading the buffer, list its other copies and fold each entry only a copy
holds into the one intake, so the plan covers it. A dry run lists the copies and appends nothing.

- **Stashes.** `git stash list` names them. Each stash holds its own copy of the buffer: read it
  and count its entries.
- **Branches ahead of the trunk.** `git branch --no-merged <trunk>` names the branches that carry
  commits the trunk lacks, and any of them can carry another buffer: read it and count its entries.
- **Backups and snapshots.** Any other copy the project keeps, an earlier drain's byte copy among
  them. The byte copy stays the operator's ([§ Pre-Drain Snapshot](#pre-drain-snapshot-phase-5)):
  this section reads copies and never makes or moves one.

```
git stash list
git branch --no-merged <trunk>
git show '<ref>:<path>' > <scratch file>
```

Reading a copy's bytes is an operator step, by the route of [§ Operator Steps](#operator-steps): in
their own terminal the operator writes the copy to a scratch file outside the buffer's folder, one
file per copy (`<ref>` is `stash@{N}` or a branch, `<path>` the buffer's path), and the session
never names the buffer on a shell line. The session reads each scratch file, compares its `### `
heading lines with the buffer's own, and appends each entry only the copy holds with Edit under its
own `## ` category section (the placement rule of `task-learnings`), never at the file end; an
entry both hold is never added twice. A copy made before the last drain also holds entries that
drain removed: Phase 2's Steps 1 and 2 archive them again (stale or superseded in Step 1, already
covered in Step 2), so they cost a plan row and no promotion.

**Record the drain on the branch that merges.** Write the run's `CONSOLIDATION` entry in
`.ai/ai-changelog.md` on the branch that will merge. The cadence guard (Phase 1, step 0) reads the
checked-out changelog, so a drain recorded on a branch that never merges reads as no drain, and the
next session finds the buffer overdue again.

**Parked lessons.** If the project's hand-off format has a section for lessons not yet recorded as
intake, read that section of the project's hand-off notes in Phase 1 and list each lesson in the
inventory as an intake candidate. The kit's hand-off contract requires no such section, so this
applies only where the project's format has one. A candidate is analysed like an entry, and none is
copied into the buffer before the operator approves the plan.

## Verifying Parked Patterns

**Parked patterns rot mechanism-first**: a grep proves a pattern still EXISTS, but any claim about
CHECKER/TOOL behavior (basedpyright inference, a lint rule firing, a version-tied mechanism) needs a
~10-line probe against the pinned toolchain before it ships into a rule — a prior promotion pass
found 2 of 9 parked patterns fully dead by grep and 2 MORE with stale mechanism rationales only the
probe caught. Phrase promoted bullets at the principle/boundary level and anchor each to a live
file path so the next pass can re-verify cheaply. **And grep every code symbol the promoted text
cites against the CURRENT branch** — entries written on another branch carry that branch's names
One drain shipped a symbol name into a README that the target branch had already renamed;
only a post-promotion symbol sweep caught it.

## Generated Triage Table (Phase 3)

The triage table holds one row per intake entry and the decision on it. Its columns that copy the
buffer are generated, never typed, so a column cannot differ from the buffer and a row dropped or
repeated by hand is a computed difference, not something to spot in a long table. `buffer_table.py`
reads the buffer under the project root and prints one row per entry: `line` (the entry's heading
line), `date` and `age` in days (from the `[YYYY-MM-DD]` title and `--today`, which defaults to the
machine's calendar day), `home` (the `Home:` field), `anchor` (the `Verify-at:` field), `committed`
and the title.

```bash
python "${CLAUDE_SKILL_DIR}/scripts/buffer_table.py" --project "<absolute project root>"
python "${CLAUDE_SKILL_DIR}/scripts/buffer_table.py" --project "<absolute project root>" --decisions <decisions file>
```

The decisions are the only typed part: a scratch file with one JSON object per line, holding the
entry's `line`, an `action` from the table of Phase 2's Step 3 and optionally a `target` and a
`rationale`, and no other key (a copied column in the file is refused). The run joins each object to
its entry on the line number and reports the set difference both ways: an entry with no row, a row
whose line is no entry, and a line with two rows. Line numbers move with every edit of the buffer, so
regenerate the table after the last edit: a decisions file typed against an older buffer shows up as
that same difference.

**Committed.** `yes` when every non-blank line of the entry is in a commit (read with
`git blame --porcelain` on the buffer as it stands in the working tree), `no` when one is not (an
entry not yet committed, or an edit to one), `unknown` when git could not answer. The plan states
the entry count and, beside it, how many entries are not yet in a commit, read from the `committed`
column, so deleting an entry that exists in no commit is visible before the first removal.

**Exit codes.** 0 is a complete table (with `--decisions`, a complete join). 1 is rows to
adjudicate: a set difference, an entry whose `committed` is `unknown`, or a code fence that never
closes and so hides every heading after it. 2 is input the run could not read: no buffer, a buffer
with no entry or one that is not UTF-8, a decisions file that is unreadable or holds a row it cannot
use; never read it as clean. A heading inside a code fence is example text, not an entry, and the
run lists each one it skipped, so the table's entry count can be reconciled with the
`--list-entries` count of Phase 1 step 0.

The command names the project root and never the buffer. Like `lint learnings`, the run only reads:
it makes no commit and no copy, so it does none of the steps of [§ Operator Steps](#operator-steps).

## Operator Steps

Four steps need bytes of the buffer that no Grep, Read or Edit call delivers: the previous drain's
heading count at its commit (Phase 1), every other copy of the buffer (Phase 1), the restore-point
commit and the local byte copy (Phase 5)
and the critic's recovery read of the buffer's last committed contents (check C1 of
`consolidation-critic`). No kit script makes these commits, copies or reads (the `lint learnings`
subcommand reads the buffer to check it, and copies nothing). **In every project the operator makes
each commit, copy or read in their own terminal** and the session never names the buffer on a shell
line: Phase 1, Phase 5 and C1 describe this one route. A project whose own rules (AGENTS.md or its
override document) keep the buffer path
off session shell lines requires exactly this; a project without such a rule takes the same route,
because these skills print no shell line that names the buffer and a session's routes on it are
the three below. Either way the route is stricter than the kit's guard, which judges a shell line
by the shape of its text, best-effort, and matches only shapes that can rewrite or delete the
buffer: a plain read or copy passes it, while an inline script that reads the buffer and writes
another file is a known false positive.

The routes a session may use on the buffer are the three the guard names when it denies a line:
**Grep in count mode** (pattern `^### \[`) to count entries, **Read with offset and limit** to read
them, and **Edit appending after the last entry** to add one.

| Step | The operator, in their own terminal | The session, afterwards |
|---|---|---|
| Previous drain's count (Phase 1, step 0) | reads the buffer's `### ` heading count at the drain's commit | compares it with the post-drain count the drain reported |
| Copies of the buffer (Phase 1, step 1) | writes each copy to its own scratch file outside the buffer's folder, with the command in [§ Buffer Copies and Parked Lessons](#buffer-copies-and-parked-lessons) | reads each scratch file, then appends the entries only the copy holds under their own category sections |
| Restore point and byte copy (Phase 5) | commits the buffer as it stands in its own commit, copies it to the byte copy's path, confirms the copy is byte-identical, and writes the buffer at that commit to a scratch file for Step 6 | confirms with Grep in count mode that the byte copy and the buffer hold the same number of entries, then cites the commit id |
| Recovery read (C1, no snapshot exists) | writes the buffer's last committed contents to a scratch path that is NOT the byte copy's path | audits against it and states the coverage as partial: a reconstruction is not evidence |

## Gate Record

Phase 3 ends in a STOP, and a prose stop was skipped once: a drain removed 263 entries without ever
presenting its plan. The learnings guard, a PreToolUse hook the core pack ships, now denies a call
it sees removing entries from the buffer unless a **gate record** exists:
`.ai/consolidation-gates/<YYYY-MM-DD>-plan-approved.md` under the project root. It sees an Edit or
Write exactly, by counting entries; a shell call it judges by the shape of the command text,
best-effort and with known gaps.

- **Day rule.** `<YYYY-MM-DD>` is today's LOCAL calendar day, as the machine running the hook reads
  it. A record dated an earlier day does not count: approval and drain must happen on the same
  calendar day, so a plan approved yesterday needs a fresh record today.
- **Length rule.** The file must hold at least 200 characters once surrounding whitespace is
  stripped (characters, not bytes). Write the approved Phase 3 plan itself, not a stub: an absent,
  empty or short record denies the removal, and the denial names the path it needs.
- **When.** Write the record only AFTER the operator's approval of the plan, never before it.
- **What it gates.** Removals only. Appends to the buffer are never blocked, so intake stays
  frictionless.
- **What it is.** A written claim, not enforcement. The record is forgeable: nothing proves a human
  approved the plan, and a session can write the file itself. It turns skipping the gate from an
  invisible omission into a dated written claim that `consolidation-critic` and the changelog entry
  audit against what the operator actually approved. The drain session has no exemption from the
  guard.
- **Local.** The record is never committed: it is read here by the learnings guard and by
  `consolidation-critic`, and the project lists its folder (`.ai/consolidation-gates/`) in its ignore
  file so it cannot be staged by mistake.

## Hypothesis Lifecycle in the Plan

The validator splits around the Phase 3 approval gate (its Steps 1 to 4 and its Step 7 ledger-state
line at the end of Phase 2; its Steps 6 and 8 in Phase 6.5), because a verdict the operator never
saw in the plan is a status change nobody approved.

- **Its lifecycle actions are plan items, never post-approval side effects.** There is no archive
  and no rotation: terminal entries stay in `.ai/improvement-hypotheses.md` permanently, so do not
  plan a rotation and do not create an archive file. What still **writes** is the Meta-Synthesis, so
  it is *discovered* during Phases 1–2 and carried into the Phase 3 plan with its target named —
  whether the lint's synthesis-due NOTE is currently firing. To know before the gate, run the lint
  the validator's Step 8 names at the end of Phase 2 as well (it only reads) and carry any NOTE it
  prints into the plan. Approval then covers it exactly as it covers the verdicts.
- **The ledger-state line** the validator's Step 7 produces (`N PENDING · M terminal · last verdict
  <date>`) goes into the plan: a plan that never mentions the ledger is how a stalled ledger stays
  invisible.
- **Late discovery.** Phase 6.5 runs after the gate, so anything it discovers for the first time
  there has not been approved: if the NOTE only starts firing once this run's own verdicts land, do
  not execute the synthesis silently — present it as a one-line delta for a second approval, or
  carry it to the next run with a dated note. Discovery may happen late; writing may not.
