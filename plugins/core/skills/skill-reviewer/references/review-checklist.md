# Skill Review Checklist — Quick Reference

Sources: Agent Skills spec (agentskills.io/specification), Claude Code docs (code.claude.com/docs/en/skills)
Facts verified 2026-07-02 — re-fetch both sources before editing numbers or field semantics here.
Mechanical rows are automated by `python -m lemmi_ai_kit audit-skills`.

## Structural Compliance (Blockers)

- [ ] File is named exactly `SKILL.md` (case-sensitive)
- [ ] Folder name: lowercase letters, numbers, hyphens only
- [ ] Name does not start or end with a hyphen
- [ ] Name does not contain consecutive hyphens (`--`)
- [ ] `name` field matches parent directory name (if set)
- [ ] `name` field is 1-64 characters (if set)
- [ ] YAML frontmatter has `---` delimiters on both sides

## Structural Compliance (Major — portability risk)

- [ ] `name` field exists (spec: required; Claude Code: optional, falls back to directory name)
- [ ] `description` field exists, 1-1024 characters (spec: required; Claude Code: recommended, falls back to first paragraph)

## Structural Compliance (Minor)

- [ ] No `README.md` in the skill directory (avoids entrypoint confusion)
- [ ] Description includes keywords / trigger phrases for agent matching

## Description Quality

- [ ] First sentence: WHAT the skill does (Agent Skills spec)
- [ ] Second sentence: WHEN to use it (Agent Skills spec)
- [ ] Includes specific keywords that help agents identify relevant tasks (Agent Skills spec)
- [ ] Includes trigger phrases users would say, in quotes (project convention)
- [ ] Specific enough to avoid false triggers
- [ ] Name is qualifier-free: no model/tool/vendor term unless functionally required — a
      name-level qualifier gates invocation before the body is read (measured: zero invocations
      across 47 sessions for a model-named skill whose content was model-agnostic)
- [ ] Mentions relevant file types if applicable
- [ ] `description` + `when_to_use` combined under 1,536 chars (listing cap); fleet fits the
      listing budget (default 1% of context window; diagnose with `/doctor`)

## Invocation Model

- [ ] Only OUTWARD/DESTRUCTIVE timing-critical skills have `disable-model-invocation: true`
      (in this pack: commit-message + branch-switch); repo-internal writers and workflows stay
      model-invocable — the AGENTS.md "don't auto-invoke" rule governs behavior, not the flag
- [ ] Background knowledge skills have `user-invocable: false`
- [ ] Internal pipeline skills have `user-invocable: false` only (NOT both flags — combining them makes the skill unreachable)
- [ ] Both flags are NEVER set simultaneously on the same skill
- [ ] `allowed-tools` grants are minimal — it PRE-APPROVES tools, it does NOT restrict the pool;
      restriction intent uses `disallowed-tools` (allowed-tools is experimental in the spec)
- [ ] If `user-invocable: false`, understand it only hides from menu (not from Skill tool)
- [ ] No name collision with skills at higher precedence scopes (enterprise > personal > project)

## Progressive Disclosure

- [ ] SKILL.md is under 500 lines (<5000 tokens recommended by spec)
- [ ] Detailed tables >50 lines are in `references/`
- [ ] Templates and examples are in supporting files
- [ ] References are explicitly linked from SKILL.md
- [ ] If `context: fork`, skill has explicit task instructions (not just guidelines)

## Instruction Quality

- [ ] Steps are specific and actionable
- [ ] Error handling for common failures
- [ ] Good/bad examples as calibration anchors
- [ ] Critical instructions at the top, not buried
- [ ] Uses headings, numbered steps, tables (not prose)
- [ ] No IDE-specific references unless justified

## Claude Code Features (informational)

- [ ] Uses `$ARGUMENTS` / `$N` if skill accepts parameters
- [ ] Uses `argument-hint` for discoverability
- [ ] Considers `!`command`` for dynamic context injection
- [ ] Considers `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PROJECT_DIR}` for bundled script paths
- [ ] Considers `ultrathink` keyword for complex reasoning skills
- [ ] `hooks` field documented if lifecycle events are relevant
- [ ] Considers `when_to_use` for trigger phrases (preferred for new skills)
- [ ] Considers `paths` globs for subsystem-scoped reference skills
- [ ] Considers `disallowed-tools` where a tool must be hard-blocked (prose bans don't enforce)

## Composability

- [ ] Doesn't assume it's the only active skill
- [ ] No content overlap with other skills
- [ ] No trigger overlap with other skills
- [ ] No name collision across scopes (enterprise > personal > project)
- [ ] Accounts for nested directory discovery in monorepos
- [ ] Doesn't duplicate CLAUDE.md or AGENTS.md content
- [ ] If pipeline skill: connections to other skills are documented
- [ ] Agent-spawn templates restate host-env + read-only/git rules (sub-agents don't inherit AGENTS.md)
- [ ] Cross-references CONTAIN the cited rule (open the target; a resolving header is not verification)

## Common Issues (from past reviews)

1. No invocation control set (causes over/under-triggering)
2. Both `user-invocable: false` AND `disable-model-invocation: true` set (makes skill unreachable)
3. Description too vague ("helps with projects")
4. SKILL.md too long (>500 lines without references/)
5. Duplicate conventions across skills and AGENTS.md
6. IDE-specific tool references limiting portability
7. No good/bad examples for calibration
8. Overbroad `allowed-tools` grants (it pre-approves tools; it does not restrict the pool)
9. `context: fork` on guidelines-only skill (returns empty output)
10. Name collision with skill at higher precedence scope
