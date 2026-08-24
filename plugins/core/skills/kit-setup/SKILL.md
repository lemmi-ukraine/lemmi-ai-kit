---
name: kit-setup
description: >
  Seed or refresh this project's AI configuration (AGENTS.md, CLAUDE.md, .ai/
  scaffolding) from the lemmi-ai-kit plugin templates, with every placeholder
  filled from the ACTUAL project — detected commands, conventions, and structure —
  instead of TODO stubs. Generated blocks are wrapped in markers so they stay
  editable and can be selectively refreshed later. Use right after installing the
  lemmi-ai-kit plugin, when the user says "set up the kit", "kit setup",
  "initialize AI config", or asks to refresh/re-detect the generated sections
  ("kit-setup refresh").
metadata:
  type: workflow
---

# Kit Setup — fill placeholders from the project, keep them editable

Seeds the project-owned files the kit's skills rely on. The plugin is the only
way the kit is installed: skills load from the plugin cache and are never copied
into the project; this skill places only the files the project owns and edits.

Two modes:

- `/lemmi-ai-kit-core:kit-setup` — first-time seed (or complete missing files).
- `/lemmi-ai-kit-core:kit-setup refresh` — re-detect and update ONLY the marked
  generated blocks in existing files, leaving everything else untouched.

## Step 0 — Scaffold the files (deterministic, via the support CLI)

The kit ships a support script that places the raw files (template AGENTS.md
with TODO stubs, CLAUDE.md with the skill index already rendered, and the `.ai/`
scaffolding), with seed semantics — existing files are never overwritten:

```bash
# needs Python >= 3.11 (tomllib); system python3 may be older — pick one that works:
# Claude sets CLAUDE_PLUGIN_ROOT; Codex sets PLUGIN_ROOT (and CLAUDE_PLUGIN_ROOT for compat).
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT}}"
PY=$(command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3)
PYTHONPATH="${PLUGIN_ROOT}/src" "$PY" -m lemmi_ai_kit scaffold .
```

If no Python ≥ 3.11 exists on the machine, use uv if available
(`uv run --no-project --python 3.12 python -m lemmi_ai_kit scaffold .` with the
same `PYTHONPATH`); as a last resort, replicate the scaffold by hand: copy
`templates/AGENTS.md`, `ai/*` from `${PLUGIN_ROOT}/src/lemmi_ai_kit/assets/`
(only files that don't exist), and render CLAUDE.md's `{{SKILLS_*}}` placeholders
from `${PLUGIN_ROOT}/src/lemmi_ai_kit/assets/manifest.toml` (user-invocable
entries use their pack namespace, such as `/lemmi-ai-kit-core:<name>`).

Run it from the project root and read its report. It is safe to re-run; add
`--dry-run` first if the project already has some of the files and you want to
see what would happen. Do not hand-copy templates — the script also renders the
CLAUDE.md skill catalog (pack-namespaced invocations) and stamps
provenance.

If `.claude/skills/` contains copies of kit skills (from the retired pip
installer), tell the user: project-local copies shadow the plugin's versions and
will not receive updates — recommend deleting them and relying on the plugin.

## Step 1 — Detect the project (read, never guess)

The scaffolded AGENTS.md still has `TODO(project)` stubs. Establish each fact
from real files; if a fact cannot be established, leave the TODO in place rather
than inventing content:

- **Name + language(s):** `pyproject.toml`, `package.json`, `Cargo.toml`,
  `go.mod`, `*.csproj`, `pom.xml`/`build.gradle*` — else the directory name.
- **Commands** (dependency sync, lint, format, type-check, test, run): read the
  project's own definitions — `pyproject.toml` tool sections + lockfile flavor
  (uv/poetry/pip), `package.json` scripts + package manager from the lockfile,
  `Makefile`/`justfile`/`Taskfile.yml`, and `.github/workflows/*` (CI is the
  ground truth for what actually runs). Commands must be copy-pasteable from the
  repo root. Verify the cheap ones actually work before writing them down (e.g.
  run the lint command with `--help` or on a single file) — never publish a
  command you haven't seen succeed or found verbatim in CI.
- **Structure + conventions:** top-level layout (src/tests/apps/packages),
  monorepo or single package, existing docs (`README.md`, `CONTRIBUTING.md`,
  existing `AGENTS.md`/`CLAUDE.md`/`.cursorrules`) worth folding in.
- **Long-lived services:** anything needing rebuild/restart after code changes
  (docker compose, dev servers) for the task-completion checklist.

## Step 2 — Fill the placeholders

Every generated section is wrapped in markers. The block is plain markdown the
user may edit freely; the markers only exist so `refresh` can find and update it
later:

```
<!-- lemmi-ai-kit:begin commands (generated from project detection — edit freely; kit-setup refresh updates this block) -->
...content...
<!-- lemmi-ai-kit:end commands -->
```

In **AGENTS.md**, replace each `> TODO(project)` stub with a marked block,
keeping all other content verbatim:

| Block id | Replaces | Content |
|---|---|---|
| `commands` | Commands TODO + example block | The detected, verified commands |
| `conventions` | Conventions TODO | Detected structure + conventions specific to THIS project |
| `restart` | checklist item 4 TODO | Rebuild/restart command, or "not needed — no long-lived services" |
| `project-rules` | Project rules TODO | Rules mined from existing docs, or the intake note that the learnings loop will populate this |

**CLAUDE.md** and **`.ai/`** need no filling — the scaffold already rendered
them. If the user had a pre-existing CLAUDE.md the scaffold kept, offer to merge
the kit's skill index into it as a marked `skills-index` block instead.

## Step 3 — Write safely

Existing file content is never discarded: show which marked blocks would be
added or changed as a diff, apply only what the user approves, and fold in —
never delete — their existing content.

## Step 4 — Refresh mode

On `refresh`: re-run detection, then for each marked block compare the freshly
generated content against what is in the file. Unchanged → skip. Changed → show
a per-block diff; where the current content differs from what generation would
have produced *and* shows signs of manual editing, say so explicitly and let the
user pick keep/replace/merge per block. Never touch anything outside markers.

## Step 5 — Report

List each file as created / updated (which blocks) / skipped, each fact that
could not be detected (left as TODO), and close with: these files are owned by
the project — edit them directly anytime; markers only matter for `refresh`.
