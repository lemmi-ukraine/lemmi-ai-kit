# lemmi-ai-kit

**A development process your AI coding agent follows — installed as a plugin, not
copied into your repository.**

[![CI](https://github.com/lemmi-ukraine/lemmi-ai-kit/actions/workflows/ci.yaml/badge.svg)](https://github.com/lemmi-ukraine/lemmi-ai-kit/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Coding agents are good at writing code and weak at the process around it: agreeing
what to build before building it, reviewing what came out, and remembering what went
wrong last time. This kit installs that process. It is a plugin for **Claude Code**,
with **Codex** support shipped in the same packs, and it carries 38 skills — a
*skill* being a markdown document your agent loads when it becomes relevant, not code
your project depends on — plus the files that hold your team's own conventions.

Nothing is vendored. Nothing is forked. Your conventions stay yours, in files you
own, and they take precedence over the kit's.

## Who it is for

- Teams that have an AI coding agent and no agreed process around it — every task
  starts from a blank prompt and ends wherever it ends.
- Teams that already wrote conventions into `AGENTS.md` and want a workflow on top
  **without** giving up those rules or maintaining a fork.
- Anyone who wants the same process on more than one agent host, without writing it
  twice.

## What you get

The kit ships 38 skills in two packs. **Core** is 36 language-agnostic skills —
project setup, spec-driven development, post-task review, the learnings loop,
orchestration, research, code review, commit messages, branch handling. **Python**
adds 2 Python-specific skills, both loaded automatically and never typed.

Concretely, once installed your agent can:

- **Turn a request into a spec before it writes code** — requirements, then design,
  then a task breakdown, with a gate at each step and a critic pass over the result.
- **Review its own work when the task ends** — code review, documentation impact,
  and an extraction step that writes down what was learned.
- **Carry those learnings forward.** Observations accumulate in `.ai/learnings.md`;
  a consolidator promotes the durable ones into `AGENTS.md`, where every later task
  reads them.
- **Split large work across sub-agents** and reassemble the results, rather than
  running one long context until it degrades.
- **Write a conventional commit message from the actual diff**, plan a stack of
  dependent pull requests, and research a question with its sources challenged
  rather than trusted.

You keep receiving these through the plugin. There is nothing in your repository to
re-sync when they change.

## Install

### Claude Code

```
/plugin marketplace add lemmi-ukraine/lemmi-ai-kit
/plugin install lemmi-ai-kit-core@lemmi
```

Python projects also want:

```
/plugin install lemmi-ai-kit-python@lemmi
```

Core skills are then invoked as `/lemmi-ai-kit-core:<name>` — for example
`/lemmi-ai-kit-core:commit-message`. Some never appear in your `/` menu, which is
correct: those are loaded automatically or called by another skill in a pipeline.

### Codex

Both packs ship a Codex manifest and install from the same catalog:

```sh
codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit
codex plugin add lemmi-ai-kit-core@lemmi
```

You can also add the marketplace and then install from Codex's plugin directory by
selecting the **Lemmi** marketplace.

### How far these have been proven

Worth knowing before you file a bug against them. The `owner/repo` shorthand used
above **has not been exercised against this repository on either host** — it could
not be tested while the repository was private. What *has* been run end-to-end, on
both hosts, is cloning the repository and adding the clone as a local marketplace. If
the shorthand does not resolve for you, that fallback and the exact spelling each
client accepts are in the [adoption guide](docs/adoption-guide.md#3-install), which
also records what each host was verified with and when.

## Set up a project

In the repository you want to configure:

```
/lemmi-ai-kit-core:kit-setup
```

It reads your project — CI workflows, manifests, lockfiles, whatever `AGENTS.md` you
already have — and writes the project-owned files, filling their placeholders from
what it found. Facts it cannot detect stay as honest `TODO(project)` stubs rather
than plausible guesses.

| File | Content | Who owns it |
|---|---|---|
| `AGENTS.md` | AI-workflow rules, with the commands / conventions / restart / project-rules sections detected from your project | you — edit freely |
| `CLAUDE.md` | `@AGENTS.md` plus the skill index, pre-rendered | you — edit freely |
| `.ai/learnings.md`, `.ai/ai-changelog.md`, `.ai/improvement-hypotheses.md` | empty intake and log files the workflow writes to | your project's state — never overwritten |
| `.ai/templates/` | spec templates (requirements, design, tasks, test cases, test plan) | kit-managed |

Your own rules go in the `### Project rules` section of `AGENTS.md`. It sits last in
the file, so where your rules and the kit's disagree, yours win. That seam is why
nobody needs to fork this — the [adoption guide](docs/adoption-guide.md#5-the-seam--where-your-conventions-attach)
walks through it, including what to do when you already have conventions written.

## How this differs from a prompt library

| A folder of prompts | This kit |
|---|---|
| You copy the text into your repository, and copy it again every time it changes | The plugin owns the skills and updates them; installing copies nothing into your project |
| Each prompt starts from nothing and ends when it ends | Skills hand off: a spec gates the code, the post-task review feeds the learnings file, the consolidator promotes durable rules into `AGENTS.md` |
| Your conventions and the library's collide, so you fork and then maintain the fork | Yours attach at a documented seam and come last, so they win without editing anything of the kit's |
| The whole text is pasted into the context window | Each skill is a short `SKILL.md`; its `references/` are loaded only when that depth is actually needed |
| The claims are prose | The claims are tests. Core carrying no dependency on the Python pack, the path and portability contract, and every count on this page are all enforced in CI |

That last row is the one to check first, because it is the cheapest to verify and it
is what the rest rests on.

## The patterns it implements

The kit is not novel and does not claim to be — it is a set of established practices
made executable by an agent. Each is named with its primary source so you can judge
the practice on its own merits rather than on ours.

| What the kit does | The pattern | Primary source |
|---|---|---|
| `spec-driven-dev` produces requirements → design → tasks before any code | spec-driven development | The term was popularized by [GitHub Spec Kit](https://github.com/github/spec-kit); this exact triad matches [Kiro's spec artifacts](https://kiro.dev/docs/specs/) |
| `kit-setup` seeds and maintains `AGENTS.md` | the `AGENTS.md` convention — stewarded by the Agentic AI Foundation under the Linux Foundation, used by 60k+ open-source projects and read by 20+ agents | [agents.md](https://agents.md/) |
| Technical charters are written as Context → Decision → Consequences under a status header | Architecture Decision Record | [Michael Nygard, *Documenting Architecture Decisions*, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html) |
| `orchestrate` and `agent-delegate` break a task down, delegate the pieces, and synthesize the results | orchestrator-workers | [Anthropic, *Building Effective AI Agents*](https://www.anthropic.com/engineering/building-effective-agents) |
| Every skill is a small `SKILL.md` with `references/` behind it | progressive disclosure applied to agent context — the term itself is far older, from information architecture | [Anthropic, *Agent Skills*](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) |
| `vertical-slice` organizes features end to end rather than by layer | vertical slice architecture | [Jimmy Bogard](https://www.jimmybogard.com/vertical-slice-architecture/) |
| `research-source-planner` challenges a source before it is used | the SIFT method | [Mike Caulfield, *SIFT (The Four Moves)*](https://hapgood.us/2019/06/19/sift-the-four-moves/) |
| `commit-message` writes `type(scope): description` with a `BREAKING CHANGE:` footer | Conventional Commits v1.0.0 | [conventionalcommits.org](https://www.conventionalcommits.org/en/v1.0.0/) |
| `stacked-pr-planner` sequences dependent branches so each pull request is reviewable alone | stacked pull requests | The lineage from Phabricator's Differential and Gerrit, described in [Graphite's guide](https://graphite.com/guides/stacked-diffs) |
| `session-retrospective` reads a session's history for friction, blaming the process rather than the author | the blameless stance, from incident review | [Google SRE, *Postmortem Culture*](https://sre.google/sre-book/postmortem-culture/) |

## Documentation

| If you want to | Read |
|---|---|
| Put this into a repository, especially one that already has conventions | [Adoption guide](docs/adoption-guide.md) — install, the seam, four worked situations, and an explicit list of what is not built yet |
| A short answer to one question | [FAQ](docs/faq.md) |
| Report a bug, propose a skill, or open a pull request | [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Report a vulnerability, or understand what a skill can do on your machine | [SECURITY.md](SECURITY.md) |

**Read the threat model before you install.** A skill is instructions an agent
follows, and some of them run shell commands in your repository with your agent's
permissions. There is no sandbox between a skill and your working tree. That is the
premise of the tool rather than a defect in it, but it should be a decision you made
on purpose.

## Working on the kit itself

Everything below this line is for people changing the kit, not people using it.

### Support CLI

The Python package is not an installer. It is the deterministic helper the
`kit-setup` skill shells out to, and a development tool for this repository:

```sh
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit list
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit scaffold <target> --dry-run
```

Subcommands are `scaffold`, `list`, `lint`, `audit-skills` and `publish-check`;
Python 3.11 or newer is required, since the manifest is read with `tomllib`.

`scaffold` never copies skills and never overwrites an existing seed file —
`--reseed` resets seeds, `--force` updates the kit-managed `.ai/templates/`, and
`--dry-run` writes nothing. The `kit-setup` skill runs it straight from the plugin
cache by putting the plugin root's `src/` on `PYTHONPATH`; Claude Code supplies
`CLAUDE_PLUGIN_ROOT` and Codex supplies `PLUGIN_ROOT`, with `CLAUDE_PLUGIN_ROOT` set
too for compatibility. No pip install is involved anywhere in that path.

### Development

```sh
uv sync --dev
uv run ruff check .
uv run ruff format .
uv run basedpyright
uv run pytest
```

Those four checks are what CI runs. [CONTRIBUTING.md](CONTRIBUTING.md) explains the
hygiene contract they enforce and why a documentation-only pull request can fail it.
VS Code settings and extension recommendations ship in `.vscode/`.

### Versioning

There is no publish pipeline — the marketplaces serve this repository directly, so
pushing to `main` is the release. CI gates code quality only. When bumping the
version, change it in `pyproject.toml` and in every pack manifest under
`plugins/*/{.claude-plugin,.codex-plugin}/plugin.json` together; a test enforces
that they agree.

### Layout

- `.claude-plugin/marketplace.json` — Claude Code marketplace catalog for the packs
  in `plugins/*`.
- `.agents/plugins/marketplace.json` — Codex marketplace catalog for the same packs.
- `plugins/core/` and `plugins/python/` — the two plugins: per-host manifests plus
  the skill directories under `skills/`.
- `plugins/core/src/lemmi_ai_kit/assets/manifest.toml` — the skill registry (name,
  pack, invocation, summary). `list` and the rendered `CLAUDE.md` index both read
  from it, and tests enforce that it stays in sync with `plugins/*/skills/*`.
- `plugins/core/src/lemmi_ai_kit/assets/templates/` — the `AGENTS.md` and `CLAUDE.md`
  seeds used by `scaffold`.
- `plugins/core/src/lemmi_ai_kit/assets/ai/` — the `.ai/` scaffolding: empty state
  logs plus the spec templates.
- `plugins/core/src/lemmi_ai_kit/{cli,scaffold,manifest}.py` — the support scripting.
- [docs/syncing-from-upstream.md](docs/syncing-from-upstream.md) — the procedure for
  refreshing the pack from the repository it was extracted from, and the drift
  measurement that procedure depends on.

## License

MIT — see [LICENSE](LICENSE).
