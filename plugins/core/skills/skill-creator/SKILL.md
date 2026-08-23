---
name: skill-creator
description: >
  Interactive guide for creating new Claude Code skills. Walks through use case definition,
  frontmatter generation, instruction writing, supporting file creation, and validation.
  Enforces the Agent Skills open standard and Claude Code extensions: progressive disclosure,
  proper invocation control, kebab-case naming. Use when the user says "create a skill",
  "new skill", "build a skill", or "I want to teach Claude to..."
argument-hint: "[skill-name or description]"
metadata:
  type: task
---

# Skill Creator — Interactive Skill Building Guide

## Role

You are a Skill Architect helping the user create a well-structured Claude Code skill.
You know the Agent Skills open standard (agentskills.io/specification), Claude Code's
skill extensions (code.claude.com/docs/en/skills), and the patterns that make skills
effective in production.

## When This Skill Activates

- User wants to create a new skill from scratch
- User wants to convert an existing workflow into a skill
- User says "create a skill", "new skill", "build a skill", "teach Claude to..."

**NOTE**: If a Research Brief is provided as input, use it as source material for the
skill content (Phase 3, Step 3). This happens when invoked by the `skill-creation-workflow`.

## Creation Pipeline

### Phase 1: Discovery (Gather Requirements)

**Is a skill the right artifact?** Route first:

| Signal | Right artifact |
|--------|----------------|
| "Whenever/every time X happens, do Y" (must fire deterministically) | Hook (settings.json — the harness enforces it; a skill cannot) |
| Reusable persona + toolset for delegated work | Custom agent (`.claude/agents/*.md`) |
| A fact or rule, not a procedure | AGENTS.md / CLAUDE.md line |
| Personal, machine- or user-specific context | Memory, not a shared skill |
| A procedure Claude should run on demand | Skill — continue below |

**Extend-vs-create check:** glob `.claude/skills/*/SKILL.md` and scan descriptions — if an
existing skill already covers this ground, extending it beats creating an overlapping sibling.
Heuristic: a skill is warranted when instructions keep getting re-pasted, or when a CLAUDE.md
section has grown into a PROCEDURE rather than a fact.

Then ask the user these questions (skip any the user already answered in their request):

1. **What task should this skill handle?** Get 2-3 concrete use cases.
2. **Who invokes it?**
   - User-only (side effects like deploy, commit, send messages)
   - Claude-only (background knowledge like conventions, style guides)
   - Both (default — task + reference hybrid)
   - Internal-only (called by other skills in a pipeline, never directly)
3. **What tools does it need?** (Read, Write, Edit, Bash, Grep, Glob, WebFetch, etc.)
4. **Should it run in isolation?** (`context: fork` for research/review skills)
   - WARNING: `context: fork` only works for skills with explicit task instructions.
     Guidelines-only skills (like conventions) get no actionable prompt and return empty.
5. **Where should it live?**
   - Project: `.claude/skills/` (this project only)
   - Personal: `~/.claude/skills/` (all your projects)
   - Plugin: `<plugin>/skills/` (where plugin is enabled, uses `plugin-name:skill-name` namespace)
   - Nested: `packages/<pkg>/.claude/skills/` (auto-discovered in monorepos when editing files in that subtree)
   - Enterprise: managed settings (all users in org)
   - Note: precedence is enterprise > personal > project. Same-name skills at higher scopes win.

### Phase 2: Classification

Based on discovery, classify the skill using these two dimensions:

**Content type** (from Claude Code docs):

| Type | Pattern | Key Techniques |
|------|---------|----------------|
| **Reference content** | Background knowledge Claude applies contextually | Conventions, patterns, domain expertise |
| **Task content** | Step-by-step instructions for a specific action | Templates, validation gates, iterative refinement |

**Project taxonomy** (this project's internal classification):

| Type | Definition | Invocation |
|------|-----------|------------|
| **Task** | Bounded action with clear input/output | User or pipeline |
| **Reference** | Background knowledge loaded automatically | Claude only |
| **Review** | Analyzes artifacts, produces findings | Pipeline only |
| **Workflow** | Orchestrates other skills with gates | User only |

### Phase 3: Build the Skill

#### Step 1: Create the directory structure

```
.claude/skills/{skill-name}/
├── SKILL.md                    # Required — main instructions
├── references/                 # Optional — detailed docs loaded on demand
│   └── {reference-name}.md
├── scripts/                    # Optional — executable code
│   └── {script-name}.py
└── assets/                     # Optional — templates, etc.
    └── {asset-name}.md
```

CRITICAL rules (from Agent Skills spec):
- Folder name: lowercase letters, numbers, and hyphens only
- Must not start or end with a hyphen, no consecutive hyphens (`--`)
- MUST be exactly `SKILL.md` (case-sensitive)
- Folder name must match the `name` field in frontmatter
- Avoid README.md in skill directories — SKILL.md is the only recognized entrypoint

Team-shareable pipelines package as ONE self-contained skill folder — never a parent folder of
multiple skills. Multi-skill bundles break on partial copies (cross-skill relative paths) and can't
upload to claude.ai as a unit. Write the multi-stage pipeline as non-skippable SKILL.md steps, the
"critic" as a checklist reference file, and use section-marked assets (`SECTION: name` … `END:
name`) so generated outputs inline only the sections they use.

When the deliverable is a **copy-installable kit** (a whole loop another workspace installs, not one
skill), four conventions make it safe and maintainable:

1. Inside the kit, skills live under `skills/<name>/` — **never** a nested `.claude/skills/`, or the
   host repo's Claude discovers duplicate skill names and one silently shadows the other.
2. Ship the scaffold as a **mirrored tree** (`scaffold/.ai/…`) copy-able in one step. Root-anchored
   `.gitignore` patterns with an internal slash (`.ai/tmp/`) don't match nested copies, so it commits
   cleanly; give the scaffold's own ignore file the self-ignoring `*` + `!.gitignore` idiom.
3. Keep ported scripts **byte-verbatim except deltas**, each commented `kit delta` AND listed in a
   README "Deltas from upstream" table — that table doubles as the future manual-sync merge guide.
4. Open the README install checklist with a **name-collision check** against the target repo's
   existing skills.

Verify the empty-state tooling passes on the scaffold (a fake-repo install exercise) before
shipping, and remember the fleet audit does not reach the kit path — see the `skill-reviewer` note
on out-of-tree skills.

#### Step 2: Write the frontmatter

Generate YAML frontmatter following these rules:

```yaml
---
# === Agent Skills spec fields (portable across tools) ===
name: {kebab-case-name}              # Spec: required. Claude Code: optional (falls back to
                                     # directory name). Recommended for portability.
                                     # 1-64 chars, lowercase + numbers + hyphens.
                                     # No start/end hyphens, no consecutive hyphens (--).
                                     # Must match folder name if set.
description: >                        # Spec: required. Claude Code: recommended (falls back
  {What it does}. {When to use it}.   # to first paragraph). Max 1024 chars.
  Use when the user says "{trigger}", # Include keywords that help agents identify tasks.
  "{trigger}", or "{trigger}".        # WHAT + WHEN + keywords (spec) + trigger phrases (project).
license: {license-name}              # Optional. License name or reference to LICENSE file.
compatibility: {requirements}        # Optional. Max 500 chars. Environment requirements.
metadata:                            # Optional. Arbitrary key-value pairs (string→string).
  type: {task|reference|review|workflow}
  author: {name}

# === Claude Code extension fields ===
# (facts verified 2026-07-02 against code.claude.com/docs/en/skills — re-fetch before editing)
disable-model-invocation: {true|false} # true → only user can invoke. Removes the description
                                       # from context entirely (also a budget saver for RARE
                                       # user-only utilities), blocks programmatic invocation,
                                       # blocks subagent preloading + scheduled-task prompts
user-invocable: {true|false}           # false → hidden from / menu (Claude can still invoke
                                       # via Skill tool — this is correct for pipeline skills)
when_to_use: {trigger context}         # Trigger phrases / example requests; appended to the
                                       # description in the skill listing and truncated after it
                                       # (trigger lists degrade gracefully). Project policy (D1):
                                       # NEW skills put trigger phrases here; existing skills
                                       # migrate when a task touches them
allowed-tools: {tool list}             # PRE-APPROVAL: listed tools run without permission
                                       # prompts while the skill is active. Does NOT restrict
                                       # the tool pool. Permission-rule syntax: Bash(git add *)
disallowed-tools: {tool list}          # Restriction: tools REMOVED from the pool while active
                                       # (clears on the next user message)
paths: {globs}                         # Auto-load only when working with matching files
                                       # (e.g. backend/**/*.py) — precision loading for references
context: {fork}                        # fork → runs in isolated subagent
agent: {Explore|Plan|general-purpose}  # Only when context: fork (Explore/Plan skip CLAUDE.md)
arguments: {names}                     # Named positional args enabling $name substitution
argument-hint: "{hint}"                # Shown during autocomplete
model: {model-name}                    # Model override while the skill is active (rest of turn)
effort: {low|medium|high|xhigh|max}    # Effort override while the skill is active
shell: {bash|powershell}               # Shell for !`command` injection (powershell requires
                                       # CLAUDE_CODE_USE_POWERSHELL_TOOL=1)
hooks: {...}                           # Hooks scoped to skill lifecycle events
                                       # (see code.claude.com/docs/en/hooks)
---
```

**Important invocation nuances** (from Claude Code docs):
- `user-invocable: false` only controls `/` menu visibility, NOT Skill tool access.
  This is the correct setting for internal pipeline skills — Claude can still invoke them.
- `disable-model-invocation: true` fully blocks programmatic invocation AND removes
  the description from context. Use for side-effect skills only.
- **Never combine both flags** — this makes the skill unreachable by anyone.

**Invocation model decision tree (project policy 2026-06-21 — AGENTS.md governs auto-invocation behavior):**
```
Is the action OUTWARD or DESTRUCTIVE and timing-critical?
(commit, push, deploy, branch mutation, external sends)
  YES → disable-model-invocation: true
        (fleet: only commit-message + branch-switch. Side effect: the description
        leaves context — also right for RARE user-only utilities.)
  NO ↓

Writes only inside the repo (learnings, changelog, reports) or orchestrates other skills?
  → keep model-invocable (defaults). The AGENTS.md "don't auto-invoke side-effect
    skills without an explicit user request" rule governs BEHAVIOR; the flag stays
    off so workflows and the user can both invoke it.
  ↓

Is it background knowledge? (conventions, patterns, domain expertise)
  YES → user-invocable: false
  NO ↓

Is it only called by other skills? (internal pipeline step)
  YES → user-invocable: false  (hides from menu; Claude can still invoke via Skill tool)
  NOTE: Do NOT also set disable-model-invocation: true — that blocks
  programmatic invocation and makes the skill unreachable by anyone.
  NO → keep defaults (both true)
```

#### String substitutions (Claude Code feature)

Skills support dynamic placeholders in the markdown body:

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking the skill |
| `$ARGUMENTS[N]` or `$N` | Access a specific argument by 0-based index |
| `$name` | Named argument declared via the `arguments` frontmatter field |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing the skill's SKILL.md |
| `${CLAUDE_PROJECT_DIR}` | Project root — also valid inside `allowed-tools` rules |
| `${CLAUDE_EFFORT}` | Active effort level (low/medium/high/xhigh/max) |

If `$ARGUMENTS` is not present in the content, arguments are appended as `ARGUMENTS: <value>`.

#### Extended thinking (Claude Code feature)

Include the word `ultrathink` anywhere in skill content to enable extended thinking
mode. Useful for skills that involve complex reasoning, multi-step analysis, or
nuanced decision-making.

#### Dynamic context injection (Claude Code feature)

The `!`command`` syntax runs shell commands before the skill content is sent to Claude:

```yaml
## Current branch context
- Branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -5`
```

The command output replaces the placeholder — Claude only sees the result, not the command.
For multi-line commands, use a fenced block opened with ```` ```! ```` instead of the inline form.
Inline `!` is only recognized at line start or after whitespace. Commands run in bash by default;
set `shell: powershell` in frontmatter for PowerShell (requires `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`).

#### Step 3: Write the instructions body

Follow this structure (adapt based on category):

```markdown
# {Skill Name} — {One-line purpose}

## When This Skill Activates
{Bullet list of activation conditions}

## Instructions / Process / Pipeline
{Numbered steps with clear actions}

## Examples
{Good/bad examples showing expected behavior}

## Troubleshooting (optional)
{Common errors and solutions}
```

**When a Research Brief is provided** (from `skill-researcher` via the workflow):

1. **Translate research findings into actionable instructions** — don't just copy
   the brief; transform knowledge into guidance Claude can follow
2. **Include anti-patterns from the research** — these prevent concrete harm
3. **Add calibrating examples** — use the examples identified in the Research Brief
4. **Respect the depth recommendation** — don't go deeper or shallower than research suggests
5. **Acknowledge trade-offs** — don't present one approach as universally correct
   when the research shows trade-offs exist

**Instruction quality rules:**
- Be specific and actionable (commands, not vague guidance)
- Include error handling for common failure modes
- Use progressive disclosure — keep SKILL.md under 500 lines
- Move detailed reference material to `references/`
- Reference supporting files explicitly so Claude knows when to load them
- Include good/bad examples as calibration anchors — **critical** for any skill that defines a
  writing style or subjective quality bar (tone, copy, formatting): output drifts across invocations
  without concrete good-vs-bad pairs ("spartan" means nothing until you show what it is and isn't)
- Skill bodies persist in context UN-RE-READ for the whole session — write standing instructions,
  not one-time steps, and put load-bearing rules EARLY: after auto-compaction only the first
  ~5,000 tokens per skill are re-attached (25,000-token combined budget, most-recent-first)
- Workflow-type skills must externalize phase state to files (`.specs/{task}/` pattern) so an
  interrupted or compacted run can resume; re-invoke a load-bearing skill after compaction

#### Step 4: Create supporting files (if needed)

Move detailed content to supporting files when:
- A reference section exceeds 50 lines
- A template is needed for consistent output
- A script handles validation or generation

Reference them from SKILL.md:
```markdown
## Additional Resources
- For detailed API patterns, see [references/api-patterns.md](references/api-patterns.md)
- For output templates, see [assets/template.md](assets/template.md)
```

### Phase 4: Validation

Run this checklist before presenting the skill to the user:

**Structure (Agent Skills spec):**
- [ ] Folder name: lowercase letters, numbers, hyphens only
- [ ] No start/end hyphens, no consecutive hyphens (`--`)
- [ ] SKILL.md exists (exact spelling, case-sensitive)
- [ ] YAML frontmatter has `---` delimiters
- [ ] `name` field matches folder name, 1-64 chars (spec: required; Claude Code: optional)
- [ ] No README.md in the skill directory (avoid entrypoint confusion)

**Description:**
- [ ] Includes WHAT and WHEN (Agent Skills spec)
- [ ] Includes keywords for agent matching (Agent Skills spec)
- [ ] Includes trigger phrases in quotes (project convention)
- [ ] Under 1024 characters (Agent Skills spec); `description` + `when_to_use` combined under
      1,536 chars (Claude Code listing cap)
- [ ] Fits within the fleet's listing budget (default 1% of context window; overflow silently drops
      LEAST-INVOKED skills' descriptions; diagnose with `/doctor`, raise via `skillListingBudgetFraction`)

**Instructions:**
- [ ] Clear, actionable steps
- [ ] Error handling included
- [ ] Examples provided (good/bad)
- [ ] SKILL.md under 500 lines
- [ ] References clearly linked

**Invocation:**
- [ ] Correct `disable-model-invocation` setting for skill type
- [ ] Correct `user-invocable` setting for skill type
- [ ] Both flags are NOT set simultaneously (makes skill unreachable)
- [ ] `allowed-tools` follows principle of least privilege — but note it is **experimental**: Claude Code's SKILL.md parser may not recognize it (an IDE diagnostic can flag it as unsupported), so treat it as informational, not a load-bearing tool restriction
- [ ] No name collision with skills at higher precedence scopes

**Composability:**
- [ ] Works alongside existing skills without conflict
- [ ] Doesn't duplicate content from CLAUDE.md or AGENTS.md
- [ ] If it's part of a pipeline, the pipeline connections are documented

### Phase 5: Registration

After creating the skill files:

1. If it's a project skill, add it to the project's `CLAUDE.md` skills listing
1b. **Registration is not reachability — wire the CALLER in the same task.** `python -m lemmi_ai_kit audit-skills`
   verifies a skill is *listed*, never that any workflow *calls* it, so a skill nothing invokes
   passes every gate and still only runs if a human remembers it exists. That is the same defect as
   a rule with no detector, one level up: four stacked-PR skills shipped with
   `stacked-pr-planner` asserting "`orchestrate`'s plan step calls this skill" — which was **false**;
   nothing in `orchestrate`, `AGENTS.md` or the workflow doc referenced any of the four, and the
   operator caught it, not the build. For any skill meant to be a pipeline step, the definition of
   done includes the caller edit (the invoking skill's phase, the workflow doc's pointer, the
   AGENTS.md pipeline diagram) **and the reverse pointer being true in both directions**. Check it
   directly: grep the tracked tree for the skill's name outside its own directory and the ledgers —
   zero non-listing hits means it is unreachable. "Wire it later" ships a skill whose own text lies
   about how it is reached.
2. **Append a changelog entry** — invoke the `ai-changelog` skill (read
   `.claude/skills/ai-changelog/SKILL.md`) with a `SKILL-ADDED` entry containing:
   the skill name, type, files created, and which workflows are affected
3. **Record improvement hypothesis** — read the `ai-improvement-tracker` skill
   and evaluate whether the changelog entry warrants a testable hypothesis about expected value
4. Test listing: ask "What skills are available?" to verify the skill loads. (Malformed
   frontmatter YAML loads the body with EMPTY metadata — `/skill-name` still works but
   description matching dies; run `claude --debug` to see the parse error)
5. Test triggering: in a FRESH session (leftover authoring context masks description gaps),
   phrase a realistic request matching the description and verify the skill fires
6. Test non-triggering: verify it doesn't activate on unrelated queries
7. **Persist the trigger tests** — save the should/shouldn't-trigger phrases from the Output
   Format as 2-3 cases in `{skill}/evals/evals.json` (plain JSON, zero tooling:
   `{"skill_name": "...", "evals": [{"id": 1, "prompt": "...", "expected_output": "..."}]}`)
   so later description tuning has a re-runnable fixture
8. **Modification rule (standing):** any later non-trivial SKILL.md edit (steps, invocation
   flags, description) re-runs the mechanical audit
   (`python -m lemmi_ai_kit audit-skills`) plus the relevant
   skill-reviewer steps — pipeline skills included, and keep the CLAUDE.md listing in sync

## Output Format

Present the created skill to the user with:

```
## Skill Created: {name}

**Location:** .claude/skills/{name}/
**Type:** {Task | Reference | Review | Workflow}
**Invocation:** {User-only | Claude-only | Both | Internal-only}

### Files Created:
- SKILL.md ({line count} lines)
- references/{name}.md (if created)
- scripts/{name}.py (if created)

### Test Suggestions:
Should trigger:
- "{test query 1}"
- "{test query 2}"

Should NOT trigger:
- "{negative test 1}"
- "{negative test 2}"
```

## Common Patterns Reference

For detailed examples of skill patterns from this project, see:
- [references/skill-patterns.md](references/skill-patterns.md) — common patterns and quick references
