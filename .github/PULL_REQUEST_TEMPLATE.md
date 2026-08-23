## What this changes

<!-- One or two sentences. If it adds or changes a skill, name it. -->

## Why

<!-- Link the issue if there is one. If there isn't, say what prompted this. -->

---

## Checklist

Run `uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run pytest`
before ticking these. CI runs the same four on every PR regardless of base branch.

- [ ] All four checks pass locally
- [ ] No absolute paths — no `/Users/…`, `/home/…`, or drive-letter paths in **any** file you touched, not only under `plugins/core/src/lemmi_ai_kit/assets/`
- [ ] No reference to a private source project or to dated history that does not ship

**If this adds or renames a skill:**

- [ ] `SKILL.md` opens with YAML frontmatter whose `name:` matches the directory exactly
- [ ] Frontmatter has a `description:`
- [ ] Registered in `plugins/core/src/lemmi_ai_kit/assets/manifest.toml` with `name`, `profile`, `invocation`, `summary`
- [ ] `profile` is a value that exists in `PROFILES` in `plugins/core/src/lemmi_ai_kit/manifest.py`
- [ ] Every `references/…` link in the `SKILL.md` points at a file that ships
- [ ] No hand-written skill count added anywhere — counts come from the manifest

**If this changes what an adopter receives** (`assets/templates/**`, `kit-setup`):

- [ ] Scaffolded into a throwaway directory and the output inspected, not just read from the template

## Anything a reviewer should know

<!-- Tradeoffs you made, alternatives you rejected, parts you are unsure about.
     "I wasn't sure about X" is genuinely useful and will not count against the PR. -->

---

<sub>By opening this PR you agree your contribution is licensed under the
[MIT License](https://github.com/lemmi-ukraine/lemmi-ai-kit/blob/main/LICENSE) — inbound equals outbound. No CLA, no sign-off
trailer.</sub>
