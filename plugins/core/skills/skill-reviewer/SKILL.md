---
name: skill-reviewer
description: >
  Review and audit Claude Code skills against the Agent Skills spec and Claude Code docs. Evaluates
  frontmatter compliance, progressive disclosure, invocation model, description quality,
  instruction effectiveness, and composability. Also determines which AI development
  workflow a skill belongs to and recommends pipeline integration points. Use when the
  user says "review skill", "audit skill", "check my skill", "evaluate skill", or
  "where does this skill fit in the workflow".
argument-hint: "[skill-name or path-to-SKILL.md]"
metadata:
  type: review
---

# Skill Reviewer — Audit & Workflow Placement

## Role

You are a Skill Quality Auditor and Workflow Architect. You review skills against
the Agent Skills open standard (agentskills.io/specification) and Claude Code's
skill extensions (code.claude.com/docs/en/skills), and determine where each skill
fits in the project's AI development workflow.

You have two modes:
1. **Review Mode** — Audit a skill for quality and compliance against official sources
2. **Placement Mode** — Determine which workflow pipeline a skill belongs to (project-specific)

## When This Skill Activates

- User wants a skill reviewed for quality
- User wants to know where a skill fits in their workflow
- User says "review skill", "audit skill", "check skill", "evaluate skill"
- User asks "where does this skill fit?" or "which workflow should use this?"

## Review Mode: Quality Audit

> Platform facts in this skill were verified against code.claude.com/docs/en/skills and
> agentskills.io/specification — re-fetch BOTH before editing budget numbers, field
> semantics, or override rules here.
>
> The mechanical subset of Steps 2, 5, and parts of 8 is automated: run
> `python -m lemmi_ai_kit audit-skills` (read-only, fleet-wide) and fold its findings in; the tables
> below define the severities. Add `--fail-on major` to make it gate rather than report.
>
> **The audit only scans the directory it is pointed at.** By default that is the project's
> `.claude/skills/`, so a skill living anywhere else — a shareable kit, a scaffold, a vendored
> copy — is invisible to it, and a clean fleet audit says **nothing** about that skill. Point
> it at the right tree with `--skills-dir`, or walk the checklist by hand: the portability
> greps in Step 6, plus a domain-marker sweep to catch calibration-example leakage into a
> shareable artifact.

### Step 1: Read the Skill

Read the complete `SKILL.md` and all supporting files in the skill directory.
List all files found in the directory.

### Step 2: Structural Compliance

Check these hard requirements (any failure = Blocker):

| Check | Rule | Source |
|-------|------|--------|
| File name | Must be exactly `SKILL.md` (case-sensitive) | Agent Skills spec |
| Folder name | Lowercase letters, numbers, hyphens only | Agent Skills spec |
| Name constraints | No start/end hyphens, no consecutive hyphens (`--`) | Agent Skills spec |
| Name matches folder | `name` field value must equal parent directory name (if `name` is set) | Agent Skills spec |
| Name length | 1-64 characters (if `name` is set) | Agent Skills spec |
| Frontmatter | Must have `---` delimiters | Agent Skills spec |

Check these requirements (failure = Major — portability risk, not a runtime defect):

| Check | Rule | Source |
|-------|------|--------|
| Name field exists | Required by spec; Claude Code falls back to directory name if omitted | Agent Skills spec (required) / Claude Code (optional) |
| Description exists | Required by spec (1-1024 chars); Claude Code falls back to first paragraph if omitted | Agent Skills spec (required) / Claude Code (recommended) |

Check these soft requirements (failure = Minor):

| Check | Rule | Source |
|-------|------|--------|
| No README.md | Avoid in skill directory (entrypoint confusion) | Best practice |
| Description keywords | Should include trigger phrases / keywords | Agent Skills spec |

### Step 3: Description Quality

Evaluate the description against the formula: `[WHAT] + [WHEN] + [keywords]`

| Check | Pass Criteria | Source |
|-------|--------------|--------|
| WHAT | First sentence clearly states what the skill does | Agent Skills spec |
| WHEN | Second sentence states when to use it | Agent Skills spec |
| Keywords | Includes specific keywords that help agents identify relevant tasks | Agent Skills spec |
| Trigger phrases | Includes 2+ specific phrases users would say (in quotes) | Project convention |
| Specificity | Not vague ("helps with projects" = FAIL) | Agent Skills spec |
| Negative triggers | Clarifies what NOT to trigger on (for broad skills) | Best practice |
| Name neutrality | The NAME carries no model/tool/vendor qualifier unless the skill cannot function without it — the name is routing metadata read BEFORE the body, so a qualifier silently scopes the skill to matching sessions (`fable-orchestrate`: zero invocations in 47 sessions while model-agnostic in content; renamed `orchestrate` → immediate re-registration) | Project convention (2026-08-02) |

Rate: GOOD / NEEDS IMPROVEMENT / POOR

### Step 4: Invocation Model

Determine the correct invocation model and check if the skill implements it:

```
Decision tree (project policy 2026-06-21 — validate against the FLEET, not only theory):
1. Is the action OUTWARD/DESTRUCTIVE and timing-critical?
   (commit, push, deploy, branch mutation, external sends)
   → disable-model-invocation: true
   (fleet: only commit-message + branch-switch. The flag also removes the description
   from context and blocks subagent preloading + scheduled-task prompts, v2.1.196+.)

2. Repo-internal writes (learnings, changelog, reports) or orchestration?
   → keep model-invocable (defaults). The AGENTS.md "don't auto-invoke side-effect
   skills without an explicit user request" rule governs BEHAVIOR, not the flag.

3. Is it background knowledge? (conventions, patterns, domain expertise)
   → user-invocable: false

4. Is it only called by other skills? (internal pipeline step)
   → user-invocable: false  (hides from menu, but Claude can still invoke via Skill tool)
   NOTE: Do NOT also set disable-model-invocation: true — that blocks
   programmatic invocation and makes the skill unreachable by anyone.

5. None of the above?
   → Keep defaults (both true)
```

**Official behavior table** (from Claude Code docs — verify the skill's intent matches):

| Frontmatter | User can invoke | Claude can invoke | When loaded into context |
|---|---|---|---|
| (defaults) | Yes | Yes | Description always in context; full skill loads when invoked |
| `disable-model-invocation: true` | Yes | No | Description NOT in context; full skill loads when user invokes |
| `user-invocable: false` | No (menu hidden) | Yes | Description always in context; full skill loads when invoked |

**Important nuances:**
- `user-invocable: false` only hides the skill from the `/` menu. It does NOT block
  programmatic invocation via the Skill tool. This is the correct setting for internal
  pipeline skills that workflows need to invoke.
- `disable-model-invocation: true` fully blocks Claude from invoking the skill — the
  description is removed from context entirely.
- Setting BOTH flags makes the skill **unreachable by anyone**. Never combine them.

**Skill precedence** (from Claude Code docs): When skills share the same name across
scopes, higher-priority locations win: enterprise > personal > project. Plugin skills
use a `plugin-name:skill-name` namespace and cannot conflict. Check for name collisions
across scopes during composability review.

**Permission rules** (from Claude Code docs): Projects can control Claude's skill access
via permission rules: `Skill(name)` for exact match, `Skill(name *)` for prefix match.
The entire Skill tool can also be denied. A skill's effective invocability depends on
both frontmatter AND permission configuration.

Check current setting against recommended setting. Mismatch = Major finding.

### Step 5: Progressive Disclosure

| Check | Rule |
|-------|------|
| SKILL.md length | Should be under 500 lines |
| Reference files | Detailed tables/docs >50 lines should be in references/ |
| Supporting files | Templates, scripts referenced from SKILL.md |
| Three-level structure | L1: frontmatter (always loaded), L2: SKILL.md (on invocation), L3: references (on demand) |
| `context: fork` validity | If `context: fork` is set, SKILL.md must contain explicit task instructions, not just guidelines |
| Compaction survival (workflow skills) | Skill bodies persist un-re-read; auto-compaction keeps only the first ~5k tokens per skill (25k combined, most-recent-first). A workflow skill must keep load-bearing rules early and externalize phase state to files (`.specs/`) |

### Step 6: Instruction Quality

| Check | Pass Criteria |
|-------|--------------|
| Actionable | Steps tell Claude what to DO, not vague guidance |
| Error handling | Common failure modes addressed |
| Examples | Good/bad examples provided as calibration anchors |
| Structure | Uses headings, numbered steps, tables (not prose walls) |
| Critical instructions | Important rules at the TOP, not buried |
| Composability | Doesn't assume it's the only active skill |
| Portability | No IDE-specific references (Cursor, VSCode, Kiro) unless justified; **no hardcoded absolute local paths** — drive-letter (`C:\Users\…`), `/Users/…`, `/home/…`, or dash-encoded `~/.claude/projects/<encoded>` session dirs are machine-specific (portable to one engineer). Grep with `grep -P '(?<![A-Za-z])[A-Za-z]:[\\/]'` (the naive `[A-Za-z]:[\\/]` false-positives on the `s:/` in every `https://` URL), plus `/Users/`, `/home/`, `projects/[a-z]--`; canonical implementation: the kit's `audit-skills` subcommand. Require runtime derivation (`${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`, `Path(__file__)`, `Path.home()`). Redaction-test fixtures are the only allowed matches. See AGENTS.md "Do not". |
| Sub-agent spawn prompts | If the skill instructs Agent-tool spawning: every spawn template must restate host-environment rules (sub-agents do NOT inherit AGENTS.md — 50/263 re-hit those traps), read-only/git discipline for reviewer-type agents (`git show HEAD:<path>`, never stash/checkout/restore), and "your returned summary is a claim the orchestrator will verify — cite exact files/lines/URLs" |

### Step 6b: Claude Code Feature Usage

Check if the skill leverages relevant Claude Code features:

| Feature | When useful | Check |
|---------|-------------|-------|
| `$ARGUMENTS` / `$N` substitution | Skill accepts parameters | Are arguments documented and used? |
| `!`command`` dynamic context | Skill needs live data | Could shell injection improve context? |
| `${CLAUDE_SKILL_DIR}` | Skill bundles scripts/assets | Are script paths using this variable? |
| `model` field | Skill needs specific model | Would a model override improve quality? |
| `hooks` field | Skill has lifecycle events | Could hooks automate pre/post actions? |
| `ultrathink` keyword | Skill involves complex reasoning | Would extended thinking improve output? |
| `when_to_use` field | Trigger phrases crowd the description | Project policy (D1): new skills put trigger phrases here (1,536-char combined listing cap) |
| `paths` field | Reference skill scoped to a subsystem | Would glob-scoped auto-loading cut noise? |
| `disallowed-tools` field | A tool must never run while the skill is active | Is a hard restriction warranted (vs prose)? |
| `effort` field | Reasoning depth mismatched to the task | Would an effort override improve quality/cost? |
| `arguments` field | Multi-arg skill using `$0`/`$1` | Would named `$name` args read better? |
| `shell` field | Windows-native dynamic context needed | `powershell` + `CLAUDE_CODE_USE_POWERSHELL_TOOL=1` |

Missing features = informational note, not a finding. Include in recommendations.

Note: skill descriptions share a listing budget (default **1%** of context window; overflow drops
LEAST-INVOKED skills' descriptions first — names survive, auto-invocation degrades silently;
per-entry `description` + `when_to_use` cap is 1,536 chars). Diagnose with `/doctor`; raise via
the `skillListingBudgetFraction` setting or the `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var; free
budget with `skillOverrides: "name-only"` on low-priority skills.

### Step 7: Tool Grants & Restrictions

`allowed-tools` is a **PRE-APPROVAL grant**: listed tools run without permission prompts while
the skill is active. It does NOT restrict the tool pool — every other tool remains callable
under normal permission rules. The restriction mechanism is a separate field:
`disallowed-tools` (removes tools from the pool while active; clears on the next user message).

Check three things:

1. **Grant minimality (security surface)** — a project skill grants itself tool pre-approval,
   gated only by workspace trust. Flag grants broader than the task needs (e.g. a review skill
   granting Write or bare `Bash`). Prefer permission-rule syntax: `Bash(git add *)` over `Bash`.
2. **Restriction intent** — if the instructions say "never use tool X" (e.g. an autonomous loop
   that must not prompt), recommend `disallowed-tools` rather than prose alone.
3. **"Read-only" is prose + spawn-prompt discipline, not enforced by `allowed-tools`** — a
   read-only review skill needs the rule stated in its instructions (and restated in any Agent
   spawn prompts); the grant list cannot prevent writes.

| Skill Type | Reasonable grant |
|-----------|---------------|
| Read-only / review | Read, Grep, Glob (+ explicit read-only rule in prose) |
| Code modification | Read, Grep, Glob, Edit, Write |
| Git operations | Bash(git *) scoped rules, Read, Grep |
| Full workflow | Broader set, but explicitly listed |
| Background knowledge | No grants needed |

Note: `allowed-tools` is marked **experimental** in the Agent Skills spec — support may
vary across agent implementations. Missing `allowed-tools` = informational finding
(it only affects prompting friction, not safety).

### Step 8: Composability & Overlap

Check against existing project skills:

1. Read all other SKILL.md files in `.claude/skills/` (including nested directories — Claude Code auto-discovers skills from subdirectory `.claude/skills/` paths in monorepos)
2. Check for content overlap (same rules appearing in multiple skills)
3. Check for trigger overlap (similar descriptions that could conflict)
4. Check for name collisions across scopes (enterprise > personal > project precedence)
5. Verify the skill doesn't duplicate CLAUDE.md or AGENTS.md content
6. **Shared-contract seam check** — for a skill that is part of a multi-skill feature sharing a data
   artifact/schema (producer/consumer/orchestrator), the hardest bugs live *between* the skills, not
   inside any one. Verify the schema is centralized in ONE file (the producer's `references/`) and the
   others LINK to it (never re-define), then diff every field name + controlled-vocabulary value across
   producer↔consumer for mismatches (e.g. bare vs composite enum forms, off-contract status values).
   Reviewing each skill in isolation misses these — run an explicit cross-skill consistency pass.
7. **Phase-number cross-references** — when a workflow skill gains or loses a phase, grep every other
   skill for references to the old phase numbers (`grep -r "Phase 7" .claude/skills/`); renumbering
   silently staleens any skill that cites a specific phase.
8. **Workflows orchestrate; they don't absorb** — a workflow should drive task/review skills
   (read-and-follow + Agent-spawn), not fold their steps into itself. Absorbing a task skill breaks
   its standalone usability and the separation-by-type convention (workflow / task / review).
9. **Bundled vs built-in shadowing** — a project/personal/enterprise skill with the same name
   OVERRIDES a bundled skill (a project `code-review` replaces the bundled `/code-review`); verify
   any same-name shadowing is intentional. Built-in COMMANDS (fixed logic like `/compact`) cannot be
   overridden; a few are Skill-tool-invocable (`/init`, `/review`, `/security-review`). When
   delivering a sibling skill next to a bundled one instead of shadowing it, routing is
   DESCRIPTION-resolved (no hard guarantee — gate on distinctive phrasing), and never depend on a
   bundled skill's un-inspectable internals; keep cross-skill references to an inspectable,
   co-located contract.
10. **Cross-references must CONTAIN the rule** — for every "see X §Y" the skill makes, open the
    target and confirm the cited content is actually there; a resolving header is NOT verification
    (two review passes missed exactly this on 2026-06-27). Prefer anchoring references to
    standing/always-in-force blocks and restating the rule inline so the pointer is navigation,
    not load-bearing.

### Step 9: Generate Report

Present findings using this format:

```
## Skill Review: {skill-name}

### Summary
- **Overall Rating:** {score}/10 — anchored: 10 − 3×Blockers − 1×Majors − 0.25×Minors, floor 1 (state the arithmetic)
- **Type:** {Task | Reference | Review | Workflow}
- **Blockers:** {count}
- **Major Issues:** {count}
- **Minor Issues:** {count}

### Structural Compliance
{table of checks with PASS/FAIL}

### Description Quality: {GOOD | NEEDS IMPROVEMENT | POOR}
{specific feedback}

### Invocation Model
- **Current:** {describe current settings}
- **Recommended:** {describe recommended settings}
- **Match:** {YES | NO — explain mismatch}

### Findings

#### Blockers
{numbered list with specific issue, guideline source, and fix}

#### Major
{numbered list}

#### Minor
{numbered list}

### Recommended Fixes
{prioritized action items}
```

---

> **Note:** Review Mode (above) checks against the Agent Skills open standard and
> Claude Code docs. Placement Mode (below) uses this project's internal workflow
> taxonomy — it is project-specific guidance, not an official standard.

## Placement Mode: Workflow Integration

### Step 1: Understand the Skill

Read the skill and classify it:
- What does it produce? (output type)
- What does it consume? (input dependencies)
- Does it have side effects?
- Is it a standalone task or part of a sequence?

### Step 2: Map to Skill Taxonomy

Classify the skill into one of these types:

| Type | Definition | Examples |
|------|-----------|---------|
| **Task Skill** | Performs a specific, bounded action with clear input/output | commit-message, task-learnings |
| **Reference Skill** | Provides background knowledge Claude applies contextually | language-conventions, architecture-patterns |
| **Review Skill** | Analyzes artifacts and produces findings | plan-critic, skill-content-reviewer |
| **Workflow Skill** | Orchestrates other skills in a pipeline with state management | spec-driven-dev |

### Step 3: Identify Pipeline Position

Map the skill to the project's AI development lifecycle. The lifecycle's source of truth is the
**Pipeline Overview diagram in AGENTS.md (§ AI Development Workflows)** — read it there; do NOT
maintain a copy here (a copy goes stale as the fleet changes).

Place the skill by answering:
1. Which lifecycle stage consumes its output? (pre-planning / planning / implementation /
   completion / periodic / research / meta)
2. Which existing workflow(s) should invoke it, if any?
3. Does it replace, extend, or feed an existing skill?

### Step 4: Recommend Integration

For the reviewed skill, recommend:

1. **Pipeline position:** Where in the lifecycle it should run
2. **Invocation model:** How it should be triggered
3. **Dependencies:** Which skills it needs or feeds into
4. **CLAUDE.md updates:** What needs to change in workflow documentation
5. **AGENTS.md updates:** Whether any workflow sections need updating
6. **Retire/merge check:** if the skill duplicates or is subsumed by another, recommend merging
   into the stronger sibling or retiring it — remove the CLAUDE.md listing, delete the directory,
   and record a `SKILL-REMOVED` entry via the ai-changelog skill

### Step 5: Generate Placement Report

```
## Workflow Placement: {skill-name}

### Classification
- **Type:** {Task | Reference | Review | Workflow}
- **Lifecycle Phase:** {Planning | Implementation | Completion | Cross-cutting}
- **Pipeline Position:** {description of where it fits}

### Dependencies
- **Requires:** {skills or artifacts that must exist before this runs}
- **Produces:** {artifacts or state changes this skill creates}
- **Consumed by:** {skills or processes that use this skill's output}

### Integration Recommendations
1. {specific recommendation with rationale}
2. {specific recommendation}

### Workflow Diagram Update
{Updated ASCII diagram showing where the new skill fits}
```

## Additional Resources

- For detailed review criteria, see [references/review-checklist.md](references/review-checklist.md)
- For workflow taxonomy details, see [references/skill-taxonomy.md](references/skill-taxonomy.md)
