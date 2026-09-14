# Lemmi AI Kit Skill Authoring

Research, create and review reusable agent skills. Requires core.

Install `lemmi-ai-kit-skill-authoring@lemmi` with the host plugin manager. Skills are
canonical under this pack's `skills/`; do not copy them into a consuming project.

## Core prerequisite and shared checks

Claude declares core as a native plugin dependency. On Codex, install and enable
`lemmi-ai-kit-core@lemmi` before this pack. No custom dependency resolver runs.
Check the host inventory before a core-dependent workflow; if core is missing,
report the prerequisite rather than skipping its required steps.

Resolve a namespaced skill through the host catalog, then read any named resource
relative to that installed skill. Do not use a sibling path across plugin roots.
For the core support CLI, locate core through its installed `kit-setup` skill and
set `KIT_CORE_PLUGIN_ROOT` to that plugin root. Keep `KIT_PROJECT_ROOT` as the
absolute consuming-project directory and `KIT_SKILLS_DIR` as the skill tree under review:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --directory "${KIT_CORE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit audit-skills --project "${KIT_PROJECT_ROOT}" --skills-dir "${KIT_SKILLS_DIR}" --fail-on major
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --directory "${KIT_CORE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint all --project "${KIT_PROJECT_ROOT}"
```

The source checkout can also run the same commands through `uv run python -m
lemmi_ai_kit`. Installing a plugin does not install a Python package into the
consumer's environment. Never assume the current plugin root contains core's `src/`.
