---
name: {{SKILL_NAME}}
description: >
  TODO({{PACK}}): one paragraph the model matches on. Say what this skill decides
  or produces, and name the situations that should pull it in — file types, task
  shapes, and the words a user would actually type. A description that only
  restates the skill's title is never auto-invoked.
metadata:
  type: reference
---

# {{DISPLAY_NAME}} — {{SKILL_NAME}}

TODO({{PACK}}): one or two sentences on what this skill is for, and what it is
deliberately NOT for. The boundary is the useful half.

## When this applies

- TODO({{PACK}}): the concrete trigger, not a category.
- TODO({{PACK}}): the case that looks like a trigger and is not.

## Rules

TODO({{PACK}}): write rules an agent can follow without asking a follow-up
question. Each one states the rule, then the reason it exists — a rule with no
reason gets dropped the first time it is inconvenient.

1. **Rule.** Why it exists, and what breaks without it.
2. **Rule.** Why it exists, and what breaks without it.

## Not this pack's job

Language-agnostic workflow — spec-driven development, review, learnings,
orchestration — is the core pack's. This pack carries only what is specific to
{{PACK}}. A core skill must never name a skill in this pack: it routes by role,
so a project that installs a different language pack still resolves.

## Detail

Anything past ~500 lines belongs in `references/` next to this file, linked from
here. Relative links in this file are checked and must resolve.
