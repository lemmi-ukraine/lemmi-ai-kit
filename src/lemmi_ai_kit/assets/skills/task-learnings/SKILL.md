---
name: task-learnings
user-invocable: false
metadata:
  type: task
description: >
  Extract and record project learnings after task completion. Captures architecture
  decisions, pitfalls, patterns, and convention gaps discovered during implementation.
  Automatically updates .ai/learnings.md and relevant project rules. Use after completing
  any coding task, bug fix, refactoring, or when the AI discovers something non-obvious
  about the project.
---

# Task Learnings — Extract and Record Project Knowledge

## When This Skill Activates

Run the learnings extraction process when any of these occur:

- A coding task, bug fix, or refactoring is completed
- A surprising or non-obvious behavior is discovered in the codebase
- The human corrects the AI's approach or assumption
- An external API or service behaves unexpectedly
- A pattern is discovered that could benefit future tasks
- A convention gap or ambiguity is identified

## Learnings Extraction Process

Follow these steps in order at the end of every qualifying task:

### Step 0: Measure This Session (gated)

Steps 1–8 extract from **recollection**, which is the weakest available evidence for the agent's
*own* behavior: only findings dramatic enough to notice survive, and no count can be audited
afterwards. This step measures instead, for the one class of finding recollection is worst at —
how the human and the agent actually interacted.

**Gate — skip Step 0 entirely when ALL of these hold** (costs nothing, no script run):

- the session ran fewer than ~15 tool calls, AND
- no command or file was visibly worked more than once, AND
- the user did not restate a request or correct you

Then say "no interaction signal — skipping the measurement" and go to Step 1. **A clean session is
a valid result, not a skipped step.**

> **Do not read the gate off the extractor's first-user-message field.** When a session opens with a
> slash command only, that field comes back **blank** — the command invocation is not captured as a
> user message — so a session that clearly had interaction signal looks like it had none. Judge the
> gate from the three conditions above (tool-call count, repeated work, restated requests), not from
> a summary field that can be empty for a reason unrelated to the session's content.

**Otherwise:**

1. **Resolve THIS session's id** — it is the last path segment of your scratchpad directory
   (`…/claude/<encoded-repo>/<SESSION-ID>/scratchpad`). Pass that id explicitly; do **not** pass
   `current`. `current` resolves by newest-mtime, and this checkout routinely runs parallel
   sessions: verified 2026-08-14, **four** transcripts had been written within 180s and
   newest-mtime pointed at an entirely unrelated session. The extractor fails closed (exit 4)
   rather than guess, but the scratchpad id avoids the ambiguity outright.

2. **Run the extractor, scoped to that session:**

   ```bash
   python "../session-retrospective/scripts/extract_sessions.py" \
     .ai/tmp/task-learnings/ --session <SESSION-ID> --digest --self-check
   ```

   Output dir is `.ai/tmp/task-learnings/` — **never `.ai/tmp/retro/`**, which a running
   retrospective owns (the extractor clears stale transcripts under its own output dir).

3. **Verify the pick before trusting the digest.** stderr prints the resolved id and the session's
   `first user message`. If that message is not one YOU received, you measured someone else's
   session — stop and re-run with the correct id.

4. **Exit codes:** `0` digest written · `4` ambiguous `current` (re-run with the explicit id) ·
   `3` leak gate tripped and the digest was deleted → write **no** interaction entries ·
   `2` usage error or the session had no analyzable content.

5. **Any failure falls through to Steps 1–8.** A measurement failure must never block the
   learnings append — but do **not** write interaction entries from recollection to compensate.
   State that the measurement failed and move on.

6. **Read `.ai/tmp/task-learnings/interaction-digest.md`** and derive candidates from it:
   - *counted repetition signals* — already filtered to the re-read threshold (default 6, tunable
     via `--rereads-min`; the digest records why 3 is compliance rather than thrash);
   - *agent error classes with ≥2 occurrences* — decompose before calling any of it agent quality;
     the classifier is content-blind and the digest says so;
   - *the user-message sequence* — read it for **re-asks**: the same request restated because the
     first attempt did not land. Paraphrase counts. There is deliberately no detector here, so
     this is a read, not a lookup.

7. **Write at most 2 entries**, `Category: interaction`, under `## Interaction & Workflow
   Friction`, following Steps 4–5. Every count and quote **must be locatable in the digest** — if
   it is not there, discard the claim rather than softening it.

8. **Describe the signal; do not paste the transcript.** The digest lives in gitignored
   `.ai/tmp/`, but `.ai/learnings.md` is **tracked and shared**, and the extractor's redaction is
   **secret-shapes only — it has no email or PII patterns**. So an entry must characterise what was
   measured rather than quote it at length: **no verbatim user quote longer than ~15 words**, no
   transcript path, and nothing whose safety depends on redaction that was never written to catch
   it. "The same request was restated twice before it landed" is the finding; the user's two
   messages are the evidence, and they stay in the digest.

**Division of labor — do not duplicate `session-retrospective`:**

| Step 0 (here) | `session-retrospective` |
|---|---|
| ONE session, at task completion | ~14-day window, ~weekly cadence |
| ≥2 occurrences **within this session** | ≥2 occurrences **across sessions** |
| ≤2 entries into the tracked buffer | full report, gitignored |

Report only what this session proves. A pattern you suspect spans sessions belongs to the
retrospective — leave it there rather than guessing at cross-session frequency.

### Step 1: Review the Task

Recollection is the right tool for the rest — codebase findings live in the diff, not in the
transcript. Keep it to that: anything about *how the work was conducted* comes from Step 0's
digest, where it is counted, or it does not get written.

Look back at all changes made during the task:

- What files were created, modified, or deleted?
- What problems were encountered and how were they solved?
- Did the human provide any corrections or redirections?
- Were there any surprises in how the codebase behaved?
- Did any external service behave unexpectedly?

### Step 2: Identify Findings

For each potential finding, capture:

- **What happened**: The specific observation or discovery
- **Why it matters**: How it affects future work
- **What to do differently**: Actionable guidance for next time

### Step 3: Classify Each Finding

Use this decision tree to determine if a finding is project-level (worth recording) or task-specific (discard):

```
Is this finding specific to one file/function with no broader lesson?
  └─ YES → task-specific → discard
  └─ NO ↓

Would this help in a future task in a different feature?
  └─ YES → project-level → record it
  └─ NO ↓

Did the human correct the AI's approach or assumption?
  └─ YES → project-level → record it
  └─ NO ↓

Was an external API or service behavior surprising?
  └─ YES → project-level → record it
  └─ NO → task-specific → discard
```

### Step 4: Categorize Project-Level Findings

Assign each project-level finding to exactly one of the **canonical categories** defined in
[references/learnings-format.md](references/learnings-format.md) (§ Canonical Categories). That
reference is the single source of truth for the category set AND the entry format — shared with
`learning-consolidator`. Do not invent new categories or section names.

Then fill the **routing fields** (§ Routing Fields in the same reference) — you are the cheapest
classifier, at the moment of discovery:

- `Home:` — where this should live when drained. **Work-lane rule:** if the finding is a defect
  to fix or a code/pipeline change (WORK, not knowledge), set `Home: tasks:<tasks/FILE.md>` and
  create/name that task doc in the same step — learnings hold knowledge, task files hold work.
- `Enforce-via:` — name a mechanical seam (`lint`/`test`/`template`/`script`) whenever one exists;
  `prose` is the honest default, not the reflex.
- `Verify-at:` — one live path/symbol anchoring the claim (write the CURRENT branch's name for it).
- `Scope:` — `durable` unless the finding is tied to a branch, freeze, or in-flight refactor —
  then say which (`branch:<name>` / `until:<event>`).

These are hints for the consolidator's gate, not decisions — when unsure, leave a field out
rather than guessing.

### Step 5: Write Entries to `.ai/learnings.md`

1. **Dedup check first** — the intake buffer is small: scan its existing entries (titles +
   findings) and skip any finding already recorded there or already promoted to its home
   (grep the Step 6 targets for the key terms). If a near-duplicate exists in the buffer,
   extend that entry instead of appending a second one.
2. **Append under the matching `## Category` section header** (create the header if absent —
   canonical headers are listed in learnings-format.md). NEVER append at the file end or under
   whatever section happens to be last — a chronological catch-all misleads the consolidator's
   clustering.
3. **Verify placement structurally, and run the lint — it is REQUIRED, not optional.**
   The new `### [YYYY-MM-DD] title` block must sit between its section's `##` header and the next
   `## ` header. Then run, and read the verdict:

   ```bash
   lemmi-ai-kit lint learnings
   ```

   It validates section placement, entry format, and category slugs. **This call was labelled
   "optional" once, and that is exactly how three malformed entries reached the buffer**: each was
   missing **all four** required fields, and nothing at append time looked wrong. If the lint reports findings on YOUR entries, fix them before finishing; findings on
   other sessions' entries are theirs — report, do not edit.

   > **The failure mode has a specific cause: this file's format is NOT the auto-memory format.**
   > A learnings entry uses `- **Context**:` / `- **Finding**:` / `- **Impact**:` /
   > `- **Category**:` as list items. The memory files under `~/.claude/.../memory/` use
   > `**Category:** x` plus `**Why:**` and `**How to apply:**` as paragraphs — a similar-looking
   > contract with different field names and different punctuation (colon INSIDE the bold, not
   > after it). Writing one shape into the other passes every eyeball check and fails the lint.
   > If you have written to memory in this session, re-read the field list above before appending.
4. **Buffer-pressure check (REQUIRED, mechanical):** the same lint call's `list learnings` mode
   prints the entry count. If the buffer holds **> 25 entries** OR the newest `CONSOLIDATION`
   entry in `.ai/ai-changelog.md` is **≥ 7 days old**, you MUST surface one line in your
   user-facing output: `intake at {N} entries, last drain {D} days ago → run
   /learning-consolidator`. Never refuse or defer the append itself (a lost learning is worse
   than a fat buffer) — the surfaced line is the enforcement. This is the capture-side twin of
   the consolidator's cadence guard; the 06-23→07-16 lapse grew the buffer to 115 entries
   because nothing at append time said so.

Entry format (field rules, canonical slugs, and good/bad examples:
[references/learnings-format.md](references/learnings-format.md)):

```markdown
### [YYYY-MM-DD] Short descriptive title
- **Context**: What task or situation triggered this
- **Finding**: The specific insight discovered
- **Impact**: What to do differently going forward
- **Category**: <one of the canonical slugs>
```

See [references/learnings-format.md](references/learnings-format.md) for detailed format rules and examples.

### Step 6: Update Rules If Needed

If a finding reveals a gap in existing project rules:

| What Changed | Where to Update | How |
|-------------|-----------------|-----|
| New anti-pattern discovered | `AGENTS.md` "Do not" section | Append a new bullet |
| Convention ambiguity resolved | Relevant project rule files (`.claude/skills/`, AGENTS.md, or equivalent) | Add clarification |
| Skill instructions were insufficient | Relevant skill (project-local; kit skills are plugin-managed — record an upstream proposal in `.ai/learnings.md`) | Extend instructions |
| New coding pattern to enforce | `AGENTS.md` conventions section | Append to relevant subsection |

**Rules for updating rules:**
- Always explain the rationale in the learnings entry first
- Only add to rules — never modify or remove existing rules without human approval
- Keep additions concise and consistent with the surrounding style
- If unsure whether something belongs in rules, record it in learnings only

### Step 7: Changelog Entry (if rules were updated)

If Step 6 modified any AI infrastructure files (AGENTS.md rules, skill instructions, conventions),
read the `ai-changelog` skill and append the appropriate changelog entry
(e.g., `RULE-ADDED`, `CONV-MODIFIED`, `SKILL-MODIFIED`) to `.ai/ai-changelog.md`.

### Step 8: Improvement Hypothesis (if changelog entry was written)

After writing a changelog entry in Step 7, read the `ai-improvement-tracker` skill
and evaluate whether the change warrants a testable improvement hypothesis.

## Quality Gates

A good learnings entry:
- Has a specific, descriptive title (not "miscellaneous finding")
- Includes concrete context (what task, what file, what happened)
- States an actionable impact (what to do differently)
- Does not duplicate information already in AGENTS.md or existing rules
- Is scannable — no narrative prose, use structured fields

A bad learnings entry:
- Is vague ("we learned something about testing")
- Has no actionable impact ("X is interesting")
- Duplicates an existing convention without adding new insight
- Is too granular ("line 42 of file X had a typo")
