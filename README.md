# lemmi-ai-kit

**A development process your AI coding agent follows — installed as a plugin, not
copied into your repository.**

[![CI](https://github.com/lemmi-ukraine/lemmi-ai-kit/actions/workflows/ci.yaml/badge.svg)](https://github.com/lemmi-ukraine/lemmi-ai-kit/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Coding agents are good at writing code and weak at the process around it: agreeing
what to build before building it, reviewing what came out, and remembering what went
wrong last time. This kit offers that process as native plugins for **Claude Code**
and **Codex**. Across five optional packs it carries 39 skills — a
*skill* being a markdown document your agent loads when it becomes relevant, not code
your project depends on — plus the files that hold your team's own conventions.

Your project receives no copied kit skills. Your conventions stay yours, in files
you own, and they take precedence over the kit's.

## Who it is for

- Teams that have an AI coding agent and no agreed process around it — every task
  starts from a blank prompt and ends wherever it ends.
- Teams that already wrote conventions into `AGENTS.md` and want a workflow on top
  **without** giving up those rules or maintaining a fork.
- Anyone who wants the same process on more than one agent host, without writing it
  twice.

## What you get

The kit ships 39 skills in five packs. **Core** carries 19 language-agnostic
skills for project setup, specs, review, and learnings. **Research** adds source
planning and parallel research. **Orchestration** adds delegation, initiative
coordination, and stacked-work review. **Skill Authoring** covers creating and
reviewing reusable skills. **Python** adds 2 Python-specific skills for coding
and testing conventions, both loaded automatically.

Install one pack, several, or all five through your host's plugin manager.
Research and Python stand alone. Orchestration and Skill Authoring require
Core 0.2.0 or newer. Fresh Claude installs of either dependent pack install Core
automatically; upgrade an existing Core first. On Codex, add or refresh Core
before either dependent pack.
Core is also the pack to install if you want `kit-setup` and the shared
project rules and `.ai/` files.

Core bundles the FFF file-search MCP for both hosts, with no separate FFF installation.
It uses the kit's existing uv runtime; see [Core setup](plugins/core/README.md#fff-file-search).

Depending on which packs you install, your agent can:

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

You receive installed skills through their plugins. There is nothing in your
repository to re-sync when a plugin changes.

## Install

Installation is an **agent task**. Open your project in Claude Code or Codex and
paste the prompt below. You need an authenticated client with plugin support,
Git and uv available. The agent may need the client's normal permission approval
to install plugins or edit project settings.

### Paste this prompt

<!-- agent-install-prompt:begin -->
```text
Install and set up Lemmi AI Kit in the project open in this session.
Source: https://github.com/lemmi-ukraine/lemmi-ai-kit. Use a checkout or ref I
provide; otherwise use the repository's default branch. Read its README and
the installed kit-setup instructions before changing project files.

Use this client's native plugin manager. Install and enable Core, plus the
Python pack only if the project actually uses Python. In an empty project,
start with Core only; do not choose a framework or create application code.
Install other optional packs only if I request them. Reuse an existing matching
marketplace; do not replace a different source or remove other plugins.
Keep any kit checkout and plugin cache outside this project.

I authorize the selected plugin installs, missing AI configuration files, and
clearly marked additive kit sections in existing instructions. Preserve all
existing rules, settings, source files and .ai history. Never use --reseed or
copy kit skills into .claude/skills or .agents/skills. Use uv for Python.

Run kit-setup from the installed Core plugin against this project. If newly
installed skills are not available in this session yet, locate and read the
installed SKILL.md and follow it directly. Fill project commands and conventions
from real files; leave unknowns explicit instead of inventing them. Proceed with
these defaults without another planning confirmation. Ask only if a prerequisite,
permission, conflicting configuration or destructive change needs my decision.

Verify the selected plugins and versions through the native client, inspect the
project changes, and confirm the existing content was preserved. Report what was
installed, files created/updated, unresolved facts, and any restart needed to load
new tools. Do not commit, push or deploy.
```
<!-- agent-install-prompt:end -->

For all capabilities, append: **"Install all five kit packs."** For a smaller set,
name which optional packs to add, such as Research or Orchestration; the agent
should honor their Core prerequisites. No new configuration format is needed.

**Reviewing the unreleased 0.2.0 PR?** Also provide the PR checkout or append
`Use ref codex/native-plugin-packs.` The default branch will provide these packs
after the PR merges; a default-branch install before then uses the older catalog.

### New project

1. Create an empty project folder (and a Git repository if you want version control),
   then open an agent session in that folder.
2. Paste the prompt. Core can be installed before you choose a language or framework.
   If the stack is already decided, say so; otherwise unknown commands stay explicit.
3. Review the generated instructions and `.ai/` files, then start a fresh session
   when the client needs it to load the installed skills and MCP tools.

### Existing project

1. Open the existing repository in the agent. Its manifests, CI, commands and current
   instructions are the evidence for setup.
2. Paste the same prompt. Existing `AGENTS.md`, `CLAUDE.md`, client settings and `.ai/`
   history must be preserved; only missing files and marked additions are authorized.
3. Review the diff before committing. Installing plugins does not remove legacy skill
   copies automatically; resolve any migration separately instead of overwriting them.

The [setup file table](#set-up-a-project) explains ownership. The commands below are
the manual equivalent and are useful when diagnosing an agent installation.

**Measured trials:** four agent sessions completed installation and setup in
2m 50s–7m 12s on an authenticated warm host. File and plugin checks passed in all
four; manual review found one minor error in generated project notes. See the
[test conditions, exact results and limits](docs/research/2026-09-14-agent-installation.md)
before treating these times as an expectation for your project.

### Claude Code

From a clone of this repository, add the local marketplace, then install the
packs you want:

```sh
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
claude plugin install lemmi-ai-kit-research@lemmi
claude plugin install lemmi-ai-kit-orchestration@lemmi
claude plugin install lemmi-ai-kit-skill-authoring@lemmi
claude plugin install lemmi-ai-kit-python@lemmi
```

Each install line is optional according to the dependency rules above. For
example, you can install Research alone, or Core with Orchestration. Use your
host's native plugin controls to enable, disable, or update a pack.

Core skills are then invoked as `/lemmi-ai-kit-core:<name>` — for example
`/lemmi-ai-kit-core:commit-message`. Some never appear in your `/` menu, which is
correct: those are loaded automatically or called by another skill in a pipeline.

**Already on 0.1.x?** [Migrating to 0.2.0](docs/migrating-to-0.2.0.md)
explains how to retain skills that moved out of Core. If you still have the
original single `lemmi-ai-kit` plugin, first read
[Migrating from 0.1.0](docs/migrating-from-0.1.0.md).

### Codex

The five packs ship Codex manifests in the same catalog. From a local clone:

```sh
codex plugin marketplace add .
codex plugin add lemmi-ai-kit-core@lemmi
codex plugin add lemmi-ai-kit-research@lemmi
codex plugin add lemmi-ai-kit-orchestration@lemmi
codex plugin add lemmi-ai-kit-skill-authoring@lemmi
codex plugin add lemmi-ai-kit-python@lemmi
```

Install only the packs you need. If you choose Orchestration or Skill Authoring,
add or refresh Core to 0.2.0 or newer first; Codex does not automatically
install that dependency. You can also select packs from the **Lemmi**
marketplace in Codex's plugin directory.

### How far these have been proven

The local marketplace commands above were exercised with all five packs on
Claude Code 2.1.266 and Codex 0.154.0 on 2026-09-14. Installed payloads matched
the source bytes; fresh Claude installs also resolved dependent packs to Core.
The source changes are not yet published, and the `owner/repo` marketplace
shorthand remains untested. See the [adoption guide](docs/adoption-guide.md#3-install)
for the verification record.

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
| The claims are prose | The claims are tests. Pack boundaries, the path and portability contract, and the skill counts on this page are checked in CI |

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
| Your rules attach at the `### Project rules` seam; `kit-setup refresh` rewrites only its own marked blocks and never yours | the open/closed principle — open for extension, closed for modification, applied to config files rather than to classes | Coined by Bertrand Meyer in *Object-Oriented Software Construction* (1988); [Robert C. Martin's restatement](https://blog.cleancoder.com/uncle-bob/2014/05/12/TheOpenClosedPrinciple.html) |
| Technical charters are written as Context → Decision → Consequences under a status header | Architecture Decision Record | [Michael Nygard, *Documenting Architecture Decisions*, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html) |
| `initiative-planner` makes every charter name its falsifiers and the verdict each one forces, and the first deliverable is the one that could kill the initiative | falsifiability as a planning gate — the criterion is Popper's; applying it to project charters is not | [Karl Popper, *falsifiability* (Stanford Encyclopedia of Philosophy)](https://plato.stanford.edu/entries/popper/) |
| Charters and specs carry an explicit definition of done, and a delegated brief is invalid without a self-checkable one | Definition of Done | [The Scrum Guide](https://scrumguides.org/scrum-guide.html) |
| `orchestrate` and `agent-delegate` break a task down, delegate the pieces, and synthesize the results | orchestrator-workers | [Anthropic, *Building Effective AI Agents*](https://www.anthropic.com/engineering/building-effective-agents) |
| Every skill is a small `SKILL.md` with `references/` behind it | progressive disclosure applied to agent context — the term itself is far older, from information architecture | [Anthropic, *Agent Skills*](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) |
| `vertical-slice` organizes features end to end rather than by layer | vertical slice architecture | [Jimmy Bogard](https://www.jimmybogard.com/vertical-slice-architecture/) |
| `python-conventions` and the design guide require one class per file, with the file named for the class | the single-responsibility principle, applied at file granularity rather than to class design | [Robert C. Martin, *The Single Responsibility Principle*](https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html) |
| `test-conventions` bans patching concrete clients in tests, requiring protocol-based overrides injected at the boundary | dependency injection / inversion of control | [Martin Fowler, *Inversion of Control Containers and the Dependency Injection Pattern*](https://martinfowler.com/articles/injection.html) |
| `test-conventions` makes integration tests the primary quality gate, and `test-planner` gives every case exactly one owning level | integration-first weighting — the testing trophy rather than the testing pyramid | [Kent C. Dodds, *The Testing Trophy*](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications) |
| `plan-critic` challenges every abstraction and bundled "nice to have" before a plan ships, and the seeded `AGENTS.md` forbids building scope the task did not ask for | YAGNI | Coined by Ron Jeffries in Extreme Programming; canonical write-up [Martin Fowler, *Yagni*](https://martinfowler.com/bliki/Yagni.html) |
| `research-source-planner` challenges a source before it is used | the SIFT method | [Mike Caulfield, *SIFT (The Four Moves)*](https://hapgood.us/2019/06/19/sift-the-four-moves/) |
| `commit-message` writes `type(scope): description` with a `BREAKING CHANGE:` footer | Conventional Commits v1.0.0 | [conventionalcommits.org](https://www.conventionalcommits.org/en/v1.0.0/) |
| `stacked-pr-planner` sequences dependent branches so each pull request is reviewable alone | stacked pull requests | The lineage from Phabricator's Differential and Gerrit, described in [Graphite's guide](https://graphite.com/guides/stacked-diffs) |
| `session-retrospective` reads a session's history for friction, blaming the process rather than the author | the blameless stance, from incident review | [Google SRE, *Postmortem Culture*](https://sre.google/sre-book/postmortem-culture/) |

## Documentation

| If you want to | Read |
|---|---|
| Put this into a repository, especially one that already has conventions | [Adoption guide](docs/adoption-guide.md) — install, the seam, four worked situations, and an explicit list of what is not built yet |
| A short answer to one question | [FAQ](docs/faq.md) |
| Move an existing install off the older single `lemmi-ai-kit` plugin | [Migrating from 0.1.0](docs/migrating-from-0.1.0.md) — the renamed prefixes, and the files in your own repository that do not fix themselves |
| Upgrade 0.1.x packs to the optional families | [Migrating to 0.2.0](docs/migrating-to-0.2.0.md) — preserve moved skills and update their namespaces |
| Report a bug, propose a skill, or open a pull request | [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Work on the kit itself rather than use it | [Working on the kit](docs/working-on-the-kit.md) — the repository layout, the support CLI, and what a version bump has to touch |
| Report a vulnerability, or understand what a skill can do on your machine | [SECURITY.md](SECURITY.md) |

**Read the threat model before you install.** A skill is instructions an agent
follows, and some of them run shell commands in your repository with your agent's
permissions. There is no sandbox between a skill and your working tree. That is the
premise of the tool rather than a defect in it, but it should be a decision you made
on purpose.

## License

MIT — see [LICENSE](LICENSE).
