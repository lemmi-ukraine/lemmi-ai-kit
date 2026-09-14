---
name: kit-setup
description: >
  Seed or refresh this project's AI configuration (AGENTS.md, CLAUDE.md, .ai/
  scaffolding) from the lemmi-ai-kit plugin templates, with every placeholder
  filled from the ACTUAL project — detected commands, conventions, and structure —
  instead of TODO stubs. Generated blocks are wrapped in markers so they stay
  editable and can be selectively refreshed later. Also works out which language
  packs the project needs and recommends them with the exact command for the
  detected host — it installs nothing itself. Use right after installing the
  lemmi-ai-kit plugin, when the user says "set up the kit", "kit setup",
  "initialize AI config", "which lemmi packs do I need", or asks to refresh or
  re-detect the generated sections ("kit-setup refresh").
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

## Step 0 — Establish the host, then scaffold the files

### Which host is this? Test `PLUGIN_ROOT`, not `CLAUDE_PLUGIN_ROOT`

Both hosts set a plugin-root variable, and testing them in the obvious order
gets the answer wrong: **Codex sets BOTH** `PLUGIN_ROOT` and
`CLAUDE_PLUGIN_ROOT`, the second for compatibility, so a check that looks at the
Claude variable first reports Codex as Claude. The discriminator runs the other
way round:

```bash
# PLUGIN_ROOT set -> Codex. Otherwise Claude Code. NOT the reverse: Codex sets both.
if [ -n "${PLUGIN_ROOT:-}" ]; then KIT_HOST=codex; else KIT_HOST=claude; fi
KIT_PLUGIN_ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}"
```

`KIT_PLUGIN_ROOT`, not `PLUGIN_ROOT`: assigning to `PLUGIN_ROOT` overwrites the
discriminator's own input, so every later command in that shell would read
Codex. The host matters in Step 2, where the two clients disagree about
something that is a hard error rather than a preference.

### Scaffold

The kit ships a support script that places the raw files (template AGENTS.md
with TODO stubs, CLAUDE.md with the skill index already rendered, and the `.ai/`
scaffolding), with seed semantics — existing files are never overwritten:

```bash
KIT_PROJECT_ROOT="$(pwd)"
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --directory "${KIT_PLUGIN_ROOT}/src" python -m lemmi_ai_kit scaffold "${KIT_PROJECT_ROOT}"
```

Use the project's uv/Python conventions. The explicit target prevents the core
package directory from becoming the project being scaffolded. If uv is unavailable,
report that prerequisite instead of inventing a separate installer.

Run it from the project root and read its report. It is safe to re-run; add
`--dry-run` first if the project already has some of the files and you want to
see what would happen. Do not hand-copy templates — the script also renders the
CLAUDE.md skill catalog (pack-namespaced invocations) and stamps
provenance.

If `.claude/skills/` contains copies of kit skills (from the retired pip
installer), tell the user what actually happens, which is **not** shadowing:
**both copies load.** Plugin skills are namespaced, so the project copy keeps the bare
`/name` — it already uses that name — and the plugin's is reachable only as
`/lemmi-ai-kit-core:<name>`. The user ends up with two skills per name whose descriptions
cover the same ground, and the stale project copy is the one the bare name reaches, while
it also never receives updates. From the Claude Code documentation on resolving skills
that share a name: *"A plugin skill and a skill at any of the locations above -> Both load,
because plugin skills are namespaced as `/plugin-name:skill-name`"*
(<https://code.claude.com/docs/en/skills>).

So recommend deleting the project copies and relying on the plugin — but say plainly that
installing the plugin does **not** on its own retire them, and that until they are deleted
the older copy is what the bare name runs.

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

## Step 2 — Recommend the packs. Do not install them

The host plugin manager owns installation, enable/disable and updates. This skill
recommends native commands for requested capability groups; it does not create a
selection file, preset engine or dependency resolver. If the user explicitly asks
you to run installation, use those native commands and verify the resulting inventory.

### Which packs

Map what Step 1 detected. The catalogue, both clients' exact commands, and the
verification step are in
[references/packs-and-hosts.md](references/packs-and-hosts.md) — read it before
printing a command, and update it when a pack is added.

| Detected in Step 1 | Recommend | Note |
|---|---|---|
| any project at all | `lemmi-ai-kit-core` | already installed — you are running from it |
| `pyproject.toml`, `setup.cfg`, or top-level `*.py` | `lemmi-ai-kit-python` | Python coding and testing conventions |
| source planning or parallel research requested | `lemmi-ai-kit-research` | Standalone research workflows |
| delegation, initiatives or stacked work requested | `lemmi-ai-kit-orchestration` | Requires core 0.2.0 or newer |
| creating or reviewing skills requested | `lemmi-ai-kit-skill-authoring` | Requires core 0.2.0 or newer |
| any other language | nothing further | see below — this is not a gap in the setup |

**Never invent a pack name.** If the project's language has no pack, say so in
those words: the core pack is language-agnostic by construction, so a missing
language pack costs the project nothing that exists, and writing one is a
contribution rather than a bug report. Point at `docs/authoring-a-pack.md` in
the kit's repository and move on.

### Then ask, print, and stop

1. Confirm the detected languages with the user before recommending anything —
   a monorepo with one stray `pyproject.toml` is not a Python project. Ask:
   *"I found <languages>. Which of these should the kit set conventions for?"*
2. For each pack they want that is not already installed, print the two commands
   for the host detected in Step 0 — marketplace first, then install — from
   `references/packs-and-hosts.md`. Print them; do not run them.
3. Say plainly that the new skills load on the next session, not this one.
4. If the user already asked you to install, run the native commands, verify the
   inventory, and explain that a fresh session loads the changed skills.

## Step 3 — Fill the placeholders

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
| `project-rules` | nothing — it APPENDS under the existing `### Project rules` heading | Rules mined from existing docs (`CONTRIBUTING.md`, a house style, review decisions), each with its reason. That section is no longer a stub: it explains itself and states its own empty state, so leaving it untouched is a legitimate outcome. Replace the italic empty-state line only when you have a real rule to put there |

**CLAUDE.md** and **`.ai/`** need no filling — the scaffold already rendered
them. If the user had a pre-existing CLAUDE.md the scaffold kept, offer to merge
the kit's skill index into it as a marked `skills-index` block instead.

## Step 4 — Write safely

Existing file content is never discarded: show which marked blocks would be
added or changed as a diff, apply only what the user approves, and fold in —
never delete — their existing content.

## Step 5 — Refresh mode

On `refresh`: re-run detection, then for each marked block compare the freshly
generated content against what is in the file. Unchanged → skip. Changed → show
a per-block diff; where the current content differs from what generation would
have produced *and* shows signs of manual editing, say so explicitly and let the
user pick keep/replace/merge per block. Never touch anything outside markers.

## Step 6 — Report

List each file as created / updated (which blocks) / skipped, each fact that
could not be detected (left as TODO), and close with: these files are owned by
the project — edit them directly anytime; markers only matter for `refresh`.
