---
name: ai-changelog
user-invocable: false
description: >
  Append structured entries to the AI infrastructure changelog (.ai/ai-changelog.md).
  Tracks skill creation, skill modification, convention changes, rule additions,
  and workflow modifications. Called automatically by other
  skills (skill-creator, learning-consolidator, post-task-review, task-learnings)
  or invoked directly for manual changelog entries. Use when AI infrastructure
  files are created, modified, or removed.
metadata:
  type: task
---

# AI Changelog — Record AI Infrastructure Changes

## When This Skill Activates

Append a changelog entry whenever any of these occur:

- A new skill is created (via skill-creator or skill-creation-workflow)
- An existing skill's SKILL.md or references are modified
- A convention is added or changed in AGENTS.md
- A rule is added to the "Do not" section of AGENTS.md
- A workflow pipeline is changed (new phase, removed phase, reordered)
- CLAUDE.md skill listings are updated
- Learnings are consolidated and promoted to rules or skills
- AI infrastructure files are deleted or deprecated

## Entry Format

Each entry follows this structure. Append under the current date heading in
`.ai/ai-changelog.md`:

```markdown
### {CHANGE-TYPE}: {Short descriptive title}
- **What:** {Concise description of the change}
- **Why:** {Motivation — what problem does this solve or what value does it add}
- **Files:** {Comma-separated list of files created, modified, or deleted}
- **Affected workflows:** {Which workflows or skills are impacted, if any}
```

### Change Type Taxonomy

| Prefix | When to use |
|--------|-------------|
| `SKILL-ADDED` | New skill directory and SKILL.md created |
| `SKILL-MODIFIED` | Existing skill instructions, references, or frontmatter changed |
| `SKILL-REMOVED` | Skill directory deleted or deprecated |
| `CONV-ADDED` | New convention added to AGENTS.md or convention skills |
| `CONV-MODIFIED` | Existing convention changed or clarified |
| `RULE-ADDED` | New entry in AGENTS.md "Do not" section |
| `RULE-MODIFIED` | Existing "Do not" rule changed |
| `WORKFLOW-MODIFIED` | Pipeline phase added, removed, or reordered in a workflow skill |
| `INFRA-ADDED` | New AI infrastructure file (changelog, templates, learnings structure) |
| `INFRA-MODIFIED` | Changes to AI infrastructure files or CLAUDE.md listings |
| `CONSOLIDATION` | Learnings promoted to rules/skills during consolidation |
| `EXPERIMENT-REGISTERED` | A measurement experiment is registered: instrument/baseline built and a prediction staked. MUST pair with a dated, falsifiable `.ai/improvement-hypotheses.md` entry that includes a re-eval date |

## How to Append an Entry

### Step 1: Determine the date heading

Read the first ~30 lines of `.ai/ai-changelog.md` (after the header block) to check
if today's date heading (`## YYYY-MM-DD`) already exists at the top of the entries.

- If it exists: insert the new entry DIRECTLY UNDER the date heading — newest-first *within* the
  day, matching the file's reverse-chronological contract. Do NOT append under the day's last
  entry: a same-day append once landed between a drain entry and the self-review that reviews it,
  and the lint (`check_date_headings`) cannot catch this — it checks heading order, not entry
  order within a heading.
  After inserting, re-read the day's entry titles top-to-bottom and confirm they read newest →
  oldest.
- If it does not exist: add a new date heading immediately after the `---` separator,
  before any existing date headings, then add the entry under it.

**Ordering invariant:** date headings are strictly reverse-chronological — a new/target date
heading must sort ABOVE the current top heading. NEVER append a new heading below existing
headings or at the file end. Appending at the end is how heading disorder and misfiled
entries arise, and unwinding it costs a full-file cleanup pass.

### Step 2: Write the entry

Use the entry format above. Rules:

- **Be specific** — name the skill, rule, or file that changed; don't say "updated a skill"
- **Include motivation** — the "Why" field is mandatory; it's what makes the changelog useful for learning
- **List all files** — every file created, modified, or deleted in this change
- **Link affected workflows** — if this change affects how other skills or workflows behave, name them
- **One entry per logical change** — if a single task creates a skill AND updates CLAUDE.md, that's one entry with both files listed. If a consolidation promotes 3 different learnings to 3 different rules, that's 3 entries.

### Step 3: Verify (structural, not eyeballed)

After appending, run the data-file lint:

```
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint changelog
```

It checks date-heading order, the 12-type taxonomy, and required fields. Fix any
finding before moving on.
Fallback only if the lint cannot run: manually verify the entry is under the correct date
heading, headings are reverse-chronological, no fields are missing, and no duplicate exists.

## Integration Points

This skill is called by other skills at their completion phase. Each caller provides
the change details; this skill only handles formatting and appending.

| Caller | When called | Expected input |
|--------|-------------|----------------|
| `skill-creator` | Phase 5 (Registration) | Skill name, type, location, files created |
| `skill-creation-workflow` | Phase 9 (Present Results) | Skill name, research summary, files created |
| `learning-consolidator` | Phase 7 (Summary Report) | List of all promotions, new skills, rule additions |
| `post-task-review` | Step 8 (Learnings) | Any convention/rule updates made during review |
| `task-learnings` | Step 6 (Update Rules) | Any rule file modifications |

## Grouping Under Consolidation

When `learning-consolidator` triggers multiple changes (e.g., 3 rules promoted, 1 skill
created), group them under a single `CONSOLIDATION` entry with sub-items:

```markdown
### CONSOLIDATION: Weekly learning consolidation (N entries processed)
- **What:**
  - Promoted 3 learnings to AGENTS.md rules (enum handling, async patterns, prompt sanitization)
  - Created `openai-realtime-quirks` reference skill from 4 clustered entries
  - Archived 5 stale entries
- **Why:** Weekly cadence consolidation to keep learnings lean and promote actionable knowledge
- **Files:** AGENTS.md, .claude/skills/openai-realtime-quirks/SKILL.md, .ai/learnings.md, CLAUDE.md
- **Affected workflows:** None
```

## Calibration Examples

### Good: Single skill creation (SKILL-ADDED)

```markdown
### SKILL-ADDED: ai-changelog internal pipeline skill
- **What:** Created `.claude/skills/ai-changelog/` to track all AI infrastructure changes in a structured changelog
- **Why:** Enable historical tracking and learning from how the AI infrastructure evolves over time
- **Files:** `.claude/skills/ai-changelog/SKILL.md`, `.ai/ai-changelog.md`, `CLAUDE.md`
- **Affected workflows:** skill-creator, skill-creation-workflow, learning-consolidator, post-task-review, task-learnings
```

### Good: Convention change (CONV-MODIFIED)

```markdown
### CONV-MODIFIED: Clarified enum handling for AI-parsed fields
- **What:** Added guidance to use `str(field)` instead of `.value` for enum-typed fields in AI responses
- **Why:** Python 3.11 changed str/Enum behavior; AI may return raw strings that bypass Pydantic coercion
- **Files:** `AGENTS.md`
- **Affected workflows:** None
```

### Bad: What NOT to log

- Fixing a typo in a skill's SKILL.md (too minor — not a behavioral change)
- Appending a routine learnings entry to `.ai/learnings.md` (that's task-learnings output, not an infrastructure change)
- Reading or reviewing files without modifying them
- Adding a code feature that doesn't touch AI infrastructure files

## Type Taxonomy Lock

The 12 change types above are a closed set (11 original plus `EXPERIMENT-REGISTERED`, which
carries the pairing rule stated in its table row). Do NOT introduce new prefixes — they cover
all AI infrastructure changes in this project. If a change does not fit any existing type,
it likely should not be logged. If you genuinely believe a new type is needed, flag it to
the user for approval before using it.

## File Size Management

The changelog is append-only and will grow over time. At the expected rate of ~10-20
entries per month, the file will reach ~200-500 lines in the first year. This is manageable.

When the file exceeds **500 entries**, archive older entries:
1. Move all entries older than 12 months to `.ai/ai-changelog-archive-YYYY.md`
2. Keep the header and last 12 months of entries in `.ai/ai-changelog.md`
3. Add a note at the bottom: `> Older entries archived in ai-changelog-archive-YYYY.md`

Do not prune or rotate before 500 entries — premature archival reduces the changelog's
value as a learning resource.

## Anti-Patterns

- Do NOT log routine task completions — only AI infrastructure changes
- Do NOT log code changes (bug fixes, features) unless they modify AI infrastructure files
- Do NOT create entries for reading or reviewing files without modifying them
- Do NOT duplicate information already in git commit messages — the changelog captures the "why" and impact, not the diff
- Do NOT backfill historical entries — start tracking from the date the changelog was created
- Do NOT log changes to product prompt content (e.g., files under `prompts/**`) — those are AI *product*
  content, not AI *development* infrastructure. A prompt change's record is its `.specs/<task>/`
  research + spec; it does NOT belong in `.ai/ai-changelog.md` or `.ai/improvement-hypotheses.md`.
