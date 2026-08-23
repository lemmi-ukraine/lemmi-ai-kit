# Cross-Reference Targets — Files to Update After Promotions

When the learning-consolidator promotes entries to rules, skills, or conventions, multiple
files across the project may need corresponding updates. This reference maps each promotion
target to its dependent files.

> **Extension note:** `.cursor/rules/` may mix `.md` and `.mdc` files.
> Check the actual on-disk extension before creating/editing a cursor rule —
> assuming `.md` can create a divergent duplicate.

## When a Rule is Added to AGENTS.md

| AGENTS.md section modified | Files to check/update |
|---------------------------|----------------------|
| Conventions → Project structure | `.kiro/steering/development-conventions.md` (Key Rules) |
| Conventions → Backend (any) | `.kiro/steering/development-conventions.md` (Key Rules) |
| Conventions → Frontend | — (no thin reference exists yet) |
| Conventions → Testing | `.cursor/rules/testing.md` |
| "Do not" section | `.cursor/rules/code-quality.md` (if code quality related) |
| "Do not" section | `.cursor/rules/error-handling.md` (if error handling related) |
| "Do not" section | `.cursor/rules/feature-development.md` (if architecture related) |
| AI Development Workflows | `.cursor/rules/spec-driven-dev.md`, `.cursor/rules/post-task-review.md`, `.cursor/rules/learnings.md` |

## When a Skill is Created or Updated

| Action | Files to update |
|--------|----------------|
| New skill created | `CLAUDE.md` → appropriate Skills section |
| New skill created | `.cursor/rules.md` → Documentation Index → Skills table |
| New user-invocable skill | `.cursor/rules.md` → add to Skills table |
| New reference skill | `.kiro/steering/development-conventions.md` → Convention Sources table |
| New skill with cursor rule | `.cursor/rules/` → create thin reference `.md` file |
| Existing skill instructions changed | Corresponding `.cursor/rules/{name}.md` if it exists |
| Skill description/triggers changed | Verify no stale references in other skills' descriptions |

## When a Learning is Promoted to a README or Code Comment

| Action | Files to check/update |
|--------|----------------------|
| Feature README updated/created (`backend/app/features/<feature>/README.md`) | Matching `docs/onboarding/` feature doc — AGENTS.md requires feature READMEs and onboarding docs stay in sync |
| Core-module README updated/created (`backend/app/core/<module>/README.md`) | — (leaf home; discovered by path convention per AGENTS.md § Learnings system) |
| Code comment added | — (leaf artifact; no cross-references) |

## When a Convention is Updated

| Convention type | Files to check |
|----------------|---------------|
| Language coding convention | Installed language-conventions skill, `.cursor/rules/code-quality.md` |
| Architecture convention | Installed architecture-patterns skill, `.cursor/rules/feature-development.md` |
| Testing convention | Installed testing-conventions skill, `.cursor/rules/testing.md` |
| Error handling convention | `.cursor/rules/error-handling.md` |
| Logging convention | `.cursor/rules/logging.md` |
| Workflow convention | `.cursor/rules/spec-driven-dev.md`, `.cursor/rules/post-task-review.md` |
| Learnings lifecycle / intake-buffer model | `.cursor/rules/learnings.md`, `.kiro/steering/task-completion-review.md`, `.kiro/steering/task-completion-review-output.md` (any change to how learnings are consulted, appended, or drained must update ALL thin references — the 2026-06-23 redistribution missed the cursor one) |
| **Pipeline-skill edit** (`ai-changelog`, `ai-improvement-tracker`, `hypothesis-validator`, `learning-consolidator` and its `scripts/`, `session-retrospective`, `task-learnings`) | **The edit reaches only the skills directory it is made in.** If the project keeps copies of these skills anywhere else, nothing signals the drift. **Locate them first** (`find . -type d -name learning-consolidator`), then establish which regime each copy is in, because the two behave oppositely: a **content fork** holds its own body and must be diffed against mainline before you trust it; a **pointer shim** (~20 lines whose body says *read the canonical SKILL.md*) is drift-immune by construction and needs no action, though its frontmatter `description` and any adaptation list can still go stale when a skill's description or argument contract changes. Tell the two apart before assuming either: `head -8 <path>/SKILL.md` — a shim opens with a read instruction, a fork opens with content. Then state in the change record which copies the edit reached. |

## Cursor Rule File Format (for new rules)

When creating a new cursor rule during consolidation, follow this structure:

```markdown
# {Topic Name}

{1-2 sentence summary of what this covers.}

## Rules

- **{Rule 1}**: {concise description}
- **{Rule 2}**: {concise description}

## Full Process

See the `{skill-name}` skill for the complete process.
```

Keep cursor rules as thin references (under 30 lines). They exist so Cursor IDE users
get the key rules without needing to open the full skill. The skill is always authoritative.

## Verification Checklist

After completing all cross-reference updates:

- [ ] Every new rule in AGENTS.md has been checked against cursor rules for consistency
- [ ] Every new skill is listed in CLAUDE.md
- [ ] Every new skill with a cursor rule has a matching `.cursor/rules/{name}.md`
- [ ] `.cursor/rules.md` Documentation Index reflects any new skills or cursor rules
- [ ] `.kiro/steering/development-conventions.md` reflects any new reference skills
- [ ] No stale file paths or skill names remain in any updated file
