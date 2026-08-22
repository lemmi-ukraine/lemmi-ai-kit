# lemmi-ai-kit

Lemmi's shared AI configuration as a **Claude Code and Codex plugin** — 29 skills
(spec-driven dev, post-task review, the learnings loop, orchestration, research,
code review) plus project seeding for `AGENTS.md`/`CLAUDE.md` and the `.ai/`
scaffolding.

The kit packages the AI development workflow system that grew inside a
production project, cleaned of project- and machine-specific content so it works
in a brand-new repository on any machine.

## Install (plugin — the only supported way)

Skills are managed by the plugin and update with it; nothing is copied into your
projects.

### Claude Code

```
/plugin marketplace add lemmi-ukraine/lemmi-ai-kit
/plugin install lemmi-ai-kit@lemmi
```

Invoke skills as `/lemmi-ai-kit:<name>` (e.g. `/lemmi-ai-kit:commit-message`).

### Codex

```
codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit
```

Then open the plugin directory, select the **Lemmi** marketplace, and install
**Lemmi AI Kit**. Skills ship from the same catalog; invoke them via the plugin
skill surface (e.g. `kit-setup`, `commit-message`).

## Set up a project

Inside the project you want to configure:

```
/lemmi-ai-kit:kit-setup
```

(or the Codex skill equivalent, `kit-setup`)

The setup skill scaffolds the **project-owned** files and fills their
placeholders from your actual project:

| File | Content | Ownership |
|---|---|---|
| `AGENTS.md` | AI-workflow rules; commands/conventions/restart/project-rules sections **detected from the project** (CI workflows, manifests, lockfiles) | project — edit freely |
| `CLAUDE.md` | `@AGENTS.md` + the plugin skill index, pre-rendered | project — edit freely |
| `.ai/learnings.md`, `.ai/ai-changelog.md`, `.ai/improvement-hypotheses.md` | empty intake/log files | project state — never overwritten |
| `.ai/templates/` | spec templates (requirements/design/tasks) | kit-managed |

The files are yours to edit. Facts that can't be detected stay as honest
`TODO(project)` stubs.

## Support CLI (scripting, not installation)

The Python package is no longer an installer — it is the deterministic helper
the `kit-setup` skill shells out to, and a dev tool for this repo:

```sh
python3 -m lemmi_ai_kit scaffold <target>   # place project-owned files (seed semantics)
python3 -m lemmi_ai_kit list                # print the skill catalog
```

`scaffold` never copies skills and never overwrites existing seed files
(`--reseed` to reset seeds, `--force` to update kit-managed `.ai/templates/`,
`--dry-run` to preview). The `kit-setup` skill runs it from the plugin cache via
`PYTHONPATH` on the plugin root's `src/` (Claude: `CLAUDE_PLUGIN_ROOT`; Codex:
`PLUGIN_ROOT`, with `CLAUDE_PLUGIN_ROOT` also set for compatibility) — no pip
install needed.

## Versioning

There is no publish pipeline — the plugin marketplaces serve this repo
directly, so pushing to `main` is the release. CI only gates code quality
(lint, format, types, tests). When bumping the version, change it in
`pyproject.toml`, `.claude-plugin/plugin.json`, and `.codex-plugin/plugin.json`
together (tests enforce they match).

## Development

```sh
uv sync --dev
uv run ruff check .
uv run ruff format .
uv run basedpyright
uv run pytest
```

Layout:

- `.claude-plugin/` — Claude Code `plugin.json` (points at the skills below) and
  `marketplace.json` (this repo doubles as its own Claude marketplace).
- `.codex-plugin/` — Codex `plugin.json` (same skills path + install-surface
  metadata).
- `.agents/plugins/marketplace.json` — Codex marketplace catalog (plugin at
  repo root).
- `src/lemmi_ai_kit/assets/manifest.toml` — the skill registry (name, profile,
  invocation, summary); `list` and the CLAUDE.md index render from it. Tests
  enforce that it stays in sync with `assets/skills/*`.
- `src/lemmi_ai_kit/assets/skills/` — all 29 skills, loaded by both plugins
  directly from this path. The test suite (`tests/test_assets.py`) permanently
  enforces the porting hygiene contract: no absolute machine paths, no
  source-project references, no dated history citations, no machine-specific
  rules.
- `src/lemmi_ai_kit/assets/templates/` — `AGENTS.md`/`CLAUDE.md` seeds used by
  `scaffold`.
- `src/lemmi_ai_kit/assets/ai/` — the `.ai/` scaffolding (empty state logs +
  spec templates).
- `src/lemmi_ai_kit/{cli,scaffold,manifest}.py` — the support scripting code.

VS Code: the repo ships settings and extension recommendations (ruff as
formatter, basedpyright for types) in `.vscode/`.
