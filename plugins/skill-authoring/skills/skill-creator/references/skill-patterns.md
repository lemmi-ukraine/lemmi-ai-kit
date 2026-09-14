# Skill Patterns Reference

Patterns derived from the Agent Skills open standard (agentskills.io/specification),
the Claude Code skills documentation (code.claude.com/docs/en/skills), and project
experience.

## Pattern 1: Sequential Workflow Orchestration

**Use when:** Multi-step processes in a specific order.

Key techniques:
- Explicit step ordering with numbered steps
- Dependencies between steps (output of step N feeds step N+1)
- Validation gates at each stage
- Rollback instructions for failures
- Clear "STOP" points for user approval

Example structure:
```markdown
### Step 1: Gather Context
{Collect information needed for the workflow}

### Step 2: Validate Inputs
{Check prerequisites before proceeding}

### Step 3: Execute Core Action
{The main operation}

### Step 4: Verify Results
{Confirm the action succeeded}
```

## Pattern 2: Iterative Refinement

**Use when:** Output quality improves with iteration.

Key techniques:
- Initial draft generation
- Quality check against explicit criteria
- Refinement loop with re-validation
- Termination condition (quality threshold or max iterations)

## Pattern 3: Context-Aware Decision

**Use when:** Same outcome, different approaches based on context.

Key techniques:
- Decision tree with clear criteria
- Fallback options for edge cases
- Transparency about which path was chosen and why

## Pattern 4: Progressive Disclosure Reference

**Use when:** Background knowledge that Claude applies contextually.

Key techniques:
- SKILL.md contains overview and navigation
- Detailed rules/patterns in `references/` files
- Claude reads references only when working on relevant code
- No task steps — just knowledge and examples

## Pattern 5: Pipeline Stage

**Use when:** Skill is one step in a larger workflow (internal skill).

Key techniques:
- Clear input contract (what must exist before this skill runs)
- Clear output contract (what this skill produces)
- `user-invocable: false` since users invoke the parent workflow
- Do NOT set `disable-model-invocation: true` — Claude needs to invoke via Skill tool
- Focused scope — does one thing well
- Returns structured results for the parent to consume

## Invocation Model Quick Reference

| Skill Type | `disable-model-invocation` | `user-invocable` | Example |
|------------|---------------------------|-------------------|---------|
| Outward/destructive, timing-critical action | `true` | `true` (default) | commit-message, branch-switch, deploy |
| Repo-internal writes or orchestration | `false` (default) | `true` (default) | task-learnings, post-task-review |
| Background knowledge | `false` (default) | `false` | conventions, style-guide |
| Internal pipeline step | `false` (default) | `false` | plan-critic, skill-researcher |
| General purpose | `false` (default) | `true` (default) | explain-code, research |

**IMPORTANT:** Never set both `disable-model-invocation: true` AND `user-invocable: false`
on the same skill — this makes the skill unreachable by anyone. Internal pipeline skills
need `user-invocable: false` only so Claude can still invoke them via the Skill tool.

**Policy:** only outward/destructive, timing-critical skills are user-only — in this
pack, `commit-message` and `branch-switch`. Repo-file-writing skills and workflows stay
model-invocable; the AGENTS.md "don't auto-invoke side-effect skills without an explicit user
request" rule governs behavior, not the flag. Note `disable-model-invocation: true` also removes
the description from context (a budget saver for rare user-only utilities), blocks subagent
preloading, and blocks scheduled-task prompts (v2.1.196+).

## Description Formula

```
[What it does — 1 sentence] + [When to use it — 1 sentence] + [keywords/trigger phrases]
```

The Agent Skills spec requires: keywords that help agents identify relevant tasks.
This project also uses: quoted trigger phrases users would say.

Good: "Generate conventional commit messages from staged changes. Use when the user
says 'commit', 'create commit message', or 'finalize changes'."

Bad: "Helps with commits." (too vague, no keywords or triggers)

## Extended Thinking

Include the word `ultrathink` anywhere in skill content to enable extended thinking mode.
Best for skills involving complex reasoning, multi-step analysis, or nuanced decisions.

## Description Budget

(facts verified 2026-07-02 against code.claude.com/docs/en/skills — re-fetch before editing)

Skill descriptions share a listing budget that defaults to **1% of the model's context window**.
On overflow, descriptions of the LEAST-INVOKED skills are dropped first — names always survive,
so `/skill-name` keeps working while model-side auto-invocation degrades silently. Each entry's
combined `description` + `when_to_use` is capped at **1,536 characters**
(`skillListingMaxDescChars`). Diagnose with `/doctor` (shows shortened/dropped skills). Raise
the budget via the `skillListingBudgetFraction` setting (e.g. `0.02` = 2%) or a fixed character
count in the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable. Free budget by setting
low-priority skills to `"name-only"` in the `skillOverrides` setting (also usable to silence a
noisy skill without editing its shared SKILL.md).

## SKILL.md Size Guidelines

| Content Type | Target | Move to references/ when |
|-------------|--------|------------------------|
| Core instructions | 100-300 lines | N/A — always in SKILL.md |
| Detailed tables | Inline if <50 lines | >50 lines |
| Code examples | Inline if <5 examples | >5 detailed examples |
| Templates | Always in references/ or assets/ | Always |
| API documentation | Always in references/ | Always |

**Content lifecycle:** an invoked skill body stays in context UN-RE-READ for the whole session;
after auto-compaction each skill is re-attached keeping only its first ~5,000 tokens, under a
25,000-token combined budget (most-recent-first). Put load-bearing rules early; workflow skills
must keep phase state in files (`.specs/`), not in the skill body.

## Newer Frontmatter Fields (Claude Code)

(verified 2026-07-02 against code.claude.com/docs/en/skills — re-fetch before editing)

| Field | Semantics | When to use |
|-------|-----------|-------------|
| `when_to_use` | Appended to description in the skill listing; truncated after it; combined cap 1,536 chars | Trigger phrases / example requests. Prefer this for new skills; migrate existing ones when you touch them |
| `paths` | Comma-separated globs; the skill auto-loads only when working with matching files | Reference skills scoped to a subsystem (e.g. `src/**/*.py`) |
| `disallowed-tools` | Tools REMOVED from the pool while the skill is active; clears on next user message | A tool that must be hard-blocked (e.g. AskUserQuestion in an autonomous loop) |
| `effort` | Effort override while active (low/medium/high/xhigh/max) | Skills needing deeper or cheaper reasoning than the session default |
| `arguments` | Named positional args enabling `$name` substitution | Multi-arg skills where `$0`/`$1` reads poorly |
| `shell` | `bash` (default) or `powershell` for dynamic-context commands; powershell requires `CLAUDE_CODE_USE_POWERSHELL_TOOL=1` | Windows-native dynamic context |

`allowed-tools` is a PRE-APPROVAL grant (listed tools run without permission prompts while the
skill is active) — it does NOT restrict the tool pool; use `disallowed-tools` for restriction.
It accepts permission-rule syntax (`Bash(git add *)`) and, for project skills, is gated by
workspace trust — review grants as a security surface.

## Eval Methodology (ecosystem awareness)

agentskills.io defines an eval format for skills (verified 2026-07-02): `evals/evals.json`
holds test cases (`{id, prompt, expected_output, files, assertions}`), run with-skill vs
without-skill from a FRESH context, graded per assertion with concrete evidence, aggregated
into benchmark deltas (pass-rate gain vs token/time cost). An official `skill-creator` plugin
(claude-plugins-official) automates that loop.

**This pack's position:** this pipeline is self-contained — do NOT install the official plugin
or add `skills-ref` as a dependency. Use only the evals.json FILE FORMAT (plain JSON, zero
tooling) to persist trigger tests (skill-creator Phase 5). If the official plugin is ever
installed, add a disambiguation note to our skill-creator description (plugin skills are
namespaced `skill-creator:...`, but description-level routing can still confuse).

## Pattern 6: Parameterized Skill (Claude Code)

**Use when:** Same skill logic, different inputs each time.

Key techniques:
- `$ARGUMENTS` for the full argument string
- `$0`, `$1`, `$2` for positional access
- `argument-hint` in frontmatter for discoverability
- Graceful fallback when arguments are missing

Example:
```yaml
---
name: fix-issue
argument-hint: "[issue-number]"
---
Fix GitHub issue $0 following our coding standards.
```

## Pattern 7: Dynamic Context Skill (Claude Code)

**Use when:** Skill needs live data (git state, API status, env info) to work effectively.

Key techniques:
- `!`command`` preprocessor injects shell output before Claude sees the prompt
- Commands run once at skill invocation, not repeatedly
- Combine with `context: fork` for isolated research with fresh data

Example:
```yaml
---
name: pr-summary
context: fork
agent: Explore
---
## PR Context
- Diff: !`git diff main...HEAD --stat`
- Recent commits: !`git log main..HEAD --oneline`

Summarize what this PR changes and why.
```

## Anti-Patterns to Avoid

1. **Duplicate conventions** — Don't repeat AGENTS.md content in skills.
2. **Both invocation flags set** — Never set `disable-model-invocation: true` AND `user-invocable: false` on the same skill; this makes it unreachable by anyone.
3. **Unnecessary explicit defaults** — Only set `disable-model-invocation` or `user-invocable` when deviating from defaults. General-purpose skills work fine with defaults.
4. **Monolithic SKILL.md** — Keep under 500 lines (spec: <5000 tokens); use references/.
5. **IDE-specific references** — Use environment-agnostic alternatives.
6. **No examples** — Always include good/bad calibration examples.
7. **Vague descriptions** — Must include WHAT + WHEN + keywords (spec) and trigger phrases (project).
8. **`context: fork` with guidelines-only** — Forked skills need explicit tasks, not just reference content.
9. **Consecutive hyphens in name** — Spec forbids `--` in skill names; use single hyphens.
10. **Ignoring scope precedence** — enterprise > personal > project; same-name skills at higher scopes shadow lower ones.
