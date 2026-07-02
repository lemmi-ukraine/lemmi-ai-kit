# lemmi-ai-kit

Deploy Lemmi's shared AI configuration — Claude Code skills, `AGENTS.md`/`CLAUDE.md`,
and the `.ai/` learnings scaffolding — into any project with one command.

The kit packages the AI development workflow system that grew inside
`<private-source-project>`, cleaned of project- and machine-specific content so it works in a
brand-new repository on any machine.

## Install the CLI

```sh
curl -LsSf https://raw.githubusercontent.com/lemmi-ukraine/lemmi-ai-kit/main/install.sh | sh
```

or directly with uv:

```sh
uv tool install git+https://github.com/lemmi-ukraine/lemmi-ai-kit   # add @vX.Y.Z for a pinned release
```

## Use it in a project

```sh
cd your-project
lemmi-ai-kit install              # default profiles (see below)
lemmi-ai-kit install --all        # everything, including extras
lemmi-ai-kit install --profile core,python
lemmi-ai-kit list                 # what ships, per profile
lemmi-ai-kit diff                 # drift between the project and the kit (exit 1 on drift)
lemmi-ai-kit install --dry-run    # preview without writing
```

### What gets installed

| Target | Content | Ownership |
|---|---|---|
| `.claude/skills/<name>/` | the selected profiles' skills | **managed** — updated by re-install (`--force` to overwrite local edits) |
| `.ai/templates/` | spec templates (requirements/design/tasks) | **managed** |
| `.ai/learnings.md`, `.ai/ai-changelog.md`, `.ai/improvement-hypotheses.md` | empty intake/log files | **seed** — written once, never touched again (`--reseed` to reset) |
| `AGENTS.md` | generic AI-workflow rules + `TODO(project)` sections to fill in | **seed** |
| `CLAUDE.md` | `@AGENTS.md` + a skills index rendered for the installed profiles | **seed** |

### Profiles

| Profile | Skills | Default |
|---|---|---|
| `core` | commit-message, branch-switch, spec-driven-dev, post-task-review, learning-consolidator, session-retrospective, product-brief, plan-critic, task-learnings, ai-changelog, ai-improvement-tracker, ai-docs-lookup | ✅ |
| `skill-authoring` | skill-creator, skill-creation-workflow, skill-reviewer, skill-researcher, skill-content-reviewer | ✅ |
| `prompts` | prompt-engineering-conventions, review-prompts, prompt-eng-reviewer, prompt-domain-reviewer | ✅ |
| `research` | research-source-planner, research-source-claim, parallel-deep-research | ✅ |
| `python` | lemmi-python-conventions, lemmi-vertical-slice, lemmi-test-conventions | ✅ |
| `extras` | openai-realtime-quirks, analyze-logs (project-flavored: realtime voice, GCP logs) | opt-in |

After installing, fill in the `TODO(project)` sections in `AGENTS.md` (commands,
project conventions, restart steps).

## Releases

- **Preview**: every push to `main` automatically publishes a semver prerelease
  `vX.Y.Z-preview.N` (wheel version `X.Y.Z.devN`) via GitHub Actions.
- **Stable**: run `scripts/publish.sh` from an up-to-date `main`. It gates on
  lint/type/tests, tags `vX.Y.Z`, pushes, and starts the next patch cycle;
  CI then publishes the GitHub release. Use `scripts/publish.sh minor|major`
  to bump before releasing.

The version in `pyproject.toml` is always the version *under development*;
previews are prereleases of it.

## Development

```sh
uv sync --dev
uv run ruff check .
uv run ruff format .
uv run basedpyright
uv run pytest
```

Assets live in `src/lemmi_ai_kit/assets/` and are shipped inside the wheel:

- `assets/manifest.toml` — the skill registry (name, profile, invocation, summary);
  `lemmi-ai-kit list` and the `CLAUDE.md` index render from it. Tests enforce that
  it stays in sync with `assets/skills/*`.
- `assets/skills/` — the ported skills. The test suite (`tests/test_assets.py`)
  permanently enforces the porting hygiene contract: no absolute machine paths, no
  `<private-source-project>` references, no dated history citations, no machine-specific rules.
- `assets/templates/` — `AGENTS.md` and `CLAUDE.md` seeds.
- `assets/ai/` — the `.ai/` scaffolding (empty state logs + spec templates).

VS Code: the repo ships settings and extension recommendations (ruff as formatter,
basedpyright for types) in `.vscode/`.
