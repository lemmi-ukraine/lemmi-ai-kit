# Adoption guide

How to put this kit into your own repository, keep your own conventions, and never fork.

This guide assumes you have installed nothing and that you have never used an
"agent skill" before. Every command is copy-pasteable from a clean checkout of
your own project. Where the kit has no good answer yet, this guide says so
instead of inventing one — those places are collected in
[What is not built yet](#what-is-not-built-yet-and-what-is-not-verified) at the end.

---

## Contents

1. [What the kit actually is](#1-what-the-kit-actually-is)
2. [You probably do not need to author a pack](#2-you-probably-do-not-need-to-author-a-pack)
3. [Install](#3-install)
4. [Set up a project](#4-set-up-a-project)
5. [The seam — where your conventions attach](#5-the-seam--where-your-conventions-attach)
6. [Four situations](#6-four-situations) — start here if you already have an `AGENTS.md`
7. [Staying up to date](#7-staying-up-to-date)
8. [What is not built yet](#what-is-not-built-yet-and-what-is-not-verified)

---

## 1. What the kit actually is

### What a skill is

A **skill** is a markdown file of instructions that your AI coding agent loads
when it is relevant. It is not code, it does not run on its own, and it is not a
library your project depends on. `commit-message`, for example, is a document
that tells the agent how to read a diff and write a conventional commit message.

Skills come in three kinds, and the difference matters for what you will see:

| Kind | How it is used | Example |
|---|---|---|
| **User-invocable** | you type it as a slash command | `/lemmi-ai-kit-core:commit-message` |
| **Auto-loaded** | the agent pulls it in as background knowledge when the topic comes up; you never type its name | `python-conventions` |
| **Internal** | invoked by another skill in a pipeline; hidden from your `/` menu | `plan-critic` |

### What you get

The kit ships five native plugins ("packs"). Install one, several, or all of
them with your host's plugin manager. How many skills you end up with depends
on that choice; ask your client for its installed inventory as
**Check that it worked** below shows.

| Pack | Plugin name | What is in it |
|---|---|---|
| Core | `lemmi-ai-kit-core` | Project setup, specs, post-task review, learnings, code review, commit messages and branch handling |
| Research | `lemmi-ai-kit-research` | Source planning, ownership and parallel research; stands alone |
| Orchestration | `lemmi-ai-kit-orchestration` | Delegation, initiative coordination and stacked-work review; requires Core |
| Skill Authoring | `lemmi-ai-kit-skill-authoring` | Create, research and review reusable skills; requires Core |
| Python | `lemmi-ai-kit-python` | `python-conventions` and `test-conventions`; both auto-loaded and the pack stands alone |

Core has no dependency on another family. Where a core skill needs language
conventions it refers to the installed convention by role. The manifest and
pack-boundary tests check which native plugin owns each skill. Claude manifests
declare Core 0.2.0 or newer as a dependency of Orchestration and Skill
Authoring. Install or upgrade Core before either dependent pack on both hosts.
Fresh Claude installation of either dependent pack was verified to install Core
automatically. Update an existing Core to 0.2.0 first; Codex uses the explicit
Core-first installation commands.

### What the kit does not do

- It does not touch your source code.
- It adds no runtime dependency to your project — nothing to `pip install`, no
  entry in your lockfile.
- It does not require you to change how you build, test, or deploy.

The only files it ever puts in your repository are the ones listed in
[section 4](#4-set-up-a-project), and you own all of them.

---

## 2. You probably do not need to author a pack

Read this before anything else, because it saves most readers the rest of the
document.

Most adopters want one thing: **their own conventions sitting alongside the
kit's, in their own repository, visible to nobody else.** That needs no pack, no
fork, and nothing published. It is a section in one file, and it is described in
[section 5](#5-the-seam--where-your-conventions-attach).

The test for when you need more:

> **One repository → write your rules into `### Project rules`.**
> **Several repositories that need the same rules → then think about a pack.**

That is the whole decision. Authoring a pack earns its cost only when you would
otherwise be copying the same conventions into a second `AGENTS.md` by hand.

Contributing a pack *back* to this repository so other companies get it is a
third, separate, entirely optional step. It **is** documented now: [CONTRIBUTING.md](../CONTRIBUTING.md)
for where a pack goes and what this repo does and does not check, and
[docs/authoring-a-pack.md](authoring-a-pack.md) for the mechanics.

---

## 3. Install

Skills are managed by the plugin and update with it. Nothing is copied into your
project by installing.

### Claude Code

From a clone of the kit repository:

```sh
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
claude plugin install lemmi-ai-kit-research@lemmi
claude plugin install lemmi-ai-kit-orchestration@lemmi
claude plugin install lemmi-ai-kit-skill-authoring@lemmi
claude plugin install lemmi-ai-kit-python@lemmi
```

The five install lines show every choice; run only those you want. Research and
Python can be installed alone. Install Core when you want project setup or the
shared learnings workflow. Install or upgrade Core to 0.2.0 or newer before
Orchestration or Skill Authoring. Their Claude manifests declare that minimum
version; fresh Claude installs of either pack automatically installed Core in the
2026-09-14 check. For an existing Core install, use `claude plugin update
lemmi-ai-kit-core@lemmi` with its original scope before installing the new packs.

### Codex

```sh
codex plugin marketplace add .
codex plugin add lemmi-ai-kit-core@lemmi
codex plugin add lemmi-ai-kit-research@lemmi
codex plugin add lemmi-ai-kit-orchestration@lemmi
codex plugin add lemmi-ai-kit-skill-authoring@lemmi
codex plugin add lemmi-ai-kit-python@lemmi
```

Run only the install lines you want. For Orchestration or Skill Authoring,
install or upgrade Core to 0.2.0 or newer first; Codex does not automatically
install dependencies. Research
and Python can be installed alone.

You can also add the marketplace and then install from Codex's plugin directory
UI by selecting the **Lemmi** marketplace.

### If the `owner/repo` shorthand does not resolve

Clone the repository and add it as a local marketplace:

```sh
git clone https://github.com/lemmi-ukraine/lemmi-ai-kit
cd lemmi-ai-kit
```

The Codex and Claude commands above add that clone. If you want just one pack,
for example Research, run only its install line after the marketplace command.
In Codex:

```sh
codex plugin marketplace add .
codex plugin add lemmi-ai-kit-research@lemmi
```

Or in Claude Code:

```sh
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-research@lemmi
```

**The two clients do not spell "here" the same way, and the difference is not
cosmetic.** Claude Code rejects a bare `.` outright with `Invalid marketplace
source format`; the run that installed it used `./`, and that is the form above.
The Codex run used a local directory path, but the record of it does not pin
which spelling was typed, so treat the Codex line as the documented form rather
than as a transcript. Either way, use the line matching your client and do not
assume the trailing slash is optional — on one of these clients it is the
difference between an install and an error.

### How verified each of these is

Be aware of what has and has not been proven:

- **Codex, from a local clone — older two-pack baseline verified.** Run on
  2026-08-22 with codex-cli 0.149.0 against an isolated `CODEX_HOME`. Core and
  Python installed and enabled, and their then-listed skills materialized.
- **Claude Code, from a local clone — older Core baseline verified.** Run on 2026-08-23:
  `claude plugin marketplace add ./`, then `claude plugin install
  lemmi-ai-kit-core@lemmi`, then `claude plugin details lemmi-ai-kit-core`,
  which listed the installed core skills by name. The `.` form of
  `marketplace add` was rejected by this client; see above.
- **The `owner/repo` shorthand — not yet exercised** against this repository on
  either host. Use the clone-and-add-local path above.
- **Five-pack 0.2.0 local install — verified on 2026-09-14.** Claude Code 2.1.266
  and Codex 0.154.0 installed all five payloads; installed bytes matched source.
  Fresh Claude configurations installed Research and Python independently, and
  Orchestration and Skill Authoring with their declared Core dependency. A native
  Codex configuration override selected Research alone without changing the saved
  enabled set. The Git-based release still requires publishing the source changes.

### Check that it worked

```sh
codex plugin list      # Codex
claude plugin list     # Claude Code
```

You should see each pack you selected installed and enabled.

That only tells you the install did not error, which is weaker evidence than it
looks: an earlier probe of this kit showed a client will report a plugin as
installed when it carries no manifest at all. So ask for the inventory by name:

```sh
claude plugin details lemmi-ai-kit-core
claude plugin details lemmi-ai-kit-research
```

Ask for the details of each pack you installed; the two lines above are examples.
Claude prints `Skills (N)` followed by every skill name. Read the names. That is the
step that separates a real install from a green message, and it is also the only
count worth trusting — it is the one your machine actually has.

**Most of these do appear in your `/` menu — but not all of them, and that is
correct.** The user-invocable ones show up; the rest are auto-loaded or internal by
design, so the menu is always the shorter list. `plugin details` prints the full
inventory by name, and the `CLAUDE.md` that [section 4](#4-set-up-a-project) writes
sorts that same inventory under three headings — User-Invocable, Auto-Loaded, and
Internal Pipeline Skills — so you can see which is which. That is the answer for your
install, rather than a number this page would have to keep
true. The Python pack is the clean illustration: both of its skills are auto-loaded, so
it adds **no** new menu entries — a `/` menu that does not change after installing it is
a successful install, not a failed one.

---

## 4. Set up a project

Open the project you want to configure and run:

```
/lemmi-ai-kit-core:kit-setup
```

(In Codex, invoke the `kit-setup` skill.)

`kit-setup` reads your project — manifests, lockfiles, `Makefile`/`justfile`,
and your CI workflows — and writes a small set of **project-owned** files, with
the placeholders filled from what it found. It is told to establish every fact
from a real file and to leave an honest `TODO(project)` stub where it cannot,
rather than guessing.

### What it writes, and who owns it

| File | What it is | Ownership |
|---|---|---|
| `AGENTS.md` | Your AI workflow rules. Commands, conventions, restart steps and project rules detected from the project | **yours** — edit freely |
| `CLAUDE.md` | `@AGENTS.md` plus the skill index, pre-rendered | **yours** — edit freely |
| `.ai/learnings.md`, `.ai/ai-changelog.md`, `.ai/improvement-hypotheses.md` | Empty intake and log files the learnings loop appends to | **yours** — never overwritten |
| `.ai/templates/design.md`, `requirements.md`, `tasks.md`, `test-cases.md`, `test-plan.md` | Spec and verification templates used by `spec-driven-dev` and `test-planner` | kit-managed — refreshed on update |
| `.ai/git-stacked-pr-workflow.md` | Reference doc for the stacked-PR workflow | kit-managed |

Every file in that table, all additive. Nothing else in your repository is
touched, and this page prints no total for the same reason it prints no skill
count: the set is whatever the scaffold reports when you run it.

### Running it without an agent

`kit-setup` shells out to a small Python helper for the deterministic part. You
can run that yourself from a clone — useful in CI, or if you just want to see
the output before letting an agent near your repo:

```sh
# from a clone of lemmi-ai-kit
PYTHONPATH=plugins/core/src PYTHONDONTWRITEBYTECODE=1 uv run --no-project python -m lemmi_ai_kit scaffold /path/to/your/project --dry-run
```

`--dry-run` writes nothing. Drop it to actually place the files. The helper
places files and applies seed semantics; it does **not** do the detection —
filling in your real commands and conventions is the agent's half of the job.

> **Needs Python 3.11 or newer** (it reads TOML with `tomllib`). The `uv run`
> command above selects a Python interpreter. You do not need to run the helper
> yourself when using `kit-setup`; the skill selects a working interpreter.

---

## 5. The seam — where your conventions attach

This is the part that makes forking unnecessary, and it is the reason the rest of
the guide is short.

### `### Project rules`

The `AGENTS.md` that `kit-setup` writes ends with a section that exists purely
for you. It is not a `TODO` stub: it explains what belongs there, and then states
its own empty state and stops.

```markdown
*None recorded yet. That is a legitimate state: it means none have been
established, which is not the same as nobody having looked.*
```

Write your rules under that heading, and replace that italic line once you have a
real one. The section sits directly beneath the kit's own rule sections, so your
agent reads the kit's conventions and yours as one document — and yours come
last, so they win where they disagree.

There is nothing to register and no schema to satisfy. It is a markdown section
in a file you own.

```markdown
### Project rules
- Never call the payments client directly from a handler — go through
  `PaymentsService` so retries and idempotency keys are applied.
- Do not add a new top-level package without an ADR in `docs/adr/`.
- Integration tests talk to the real database via testcontainers; unit tests
  never touch I/O.
```

`AGENTS.md` is also where the kit's own learnings loop deposits rules over time:
`task-learnings` collects observations into `.ai/learnings.md`, and
`/lemmi-ai-kit-core:learning-consolidator` periodically promotes the durable ones
into this section. So the section fills itself as you work, whether or not you
seed it by hand.

### The marker blocks

Sections that `kit-setup` *generates* are wrapped in HTML comments:

```markdown
<!-- lemmi-ai-kit:begin commands (generated from project detection — edit freely; kit-setup refresh updates this block) -->
...generated content...
<!-- lemmi-ai-kit:end commands -->
```

Five block ids are used: `commands`, `conventions`, `restart`, `project-rules`,
and `skills-index`.

The markers exist so that re-running setup can find a generated block and update
*it* without disturbing anything else in the file. Content inside a block is
still plain markdown you may edit; content **outside** every block is never
touched at all.

To re-run detection later — you changed package manager, added CI, renamed your
test command:

```
/lemmi-ai-kit-core:kit-setup refresh
```

Refresh compares each marked block against what detection would produce now, and
where a block has been hand-edited it says so and asks you per block whether to
keep, replace, or merge.

### An honest note on how the seam is enforced

Worth knowing before you rely on it: **the marker mechanism is instructions to
the agent, not a deterministic transform.** `kit-setup` is a skill — a document
telling the agent to write marked blocks, to show a diff before applying, to fold
in rather than delete, and to never touch anything outside markers. There is no
code that parses markers and mechanically splices content.

In practice this means the seam is as reliable as the agent following the skill,
which is good but is not the same as a guarantee. Two things follow:

- **Review the diff `kit-setup` shows you** before approving it. It is instructed
  to show one.
- **Keep `AGENTS.md` in version control.** Then a bad refresh is a `git diff`
  away from being spotted and a `git checkout` away from being undone.

The Python helper underneath is deterministic and is conservative in the other
direction: it will refuse to overwrite `AGENTS.md` entirely rather than risk
merging (see the next section).

---

## 6. Four situations

Find yourself in this table and read that section. They are ordered by how common
they are, not by how simple they are.

| You are | Go to |
|---|---|
| A team that already has `AGENTS.md` / `CLAUDE.md` and conventions written down | [A](#a-you-already-have-agentsmd-and-written-conventions) |
| A single-language team starting fresh | [B](#b-single-language-team-starting-fresh) |
| A team on a language the kit ships no pack for — Go, Rust, TypeScript | [C](#c-your-language-has-no-pack) |
| A frontend org running two frameworks over one core | [D](#d-two-frameworks-over-one-core) |

---

### A. You already have `AGENTS.md` and written conventions

**This is the most common case and the one most likely to be skipped, so it is
first.** You are not a greenfield adopter. You have accumulated conventions, they
are written down, and your reasonable fear is that installing something called a
"setup skill" will flatten them.

**It will not, and this is mechanical rather than a promise.**

#### What actually happens to your existing files

The scaffold classifies `AGENTS.md`, `CLAUDE.md` and the `.ai/` state logs as
*seed* files: it writes them **only if they do not already exist**. If yours
exists and differs from the template, it is left byte-for-byte alone and reported
as kept.

Verify that on your own repository before letting anything write, with `--dry-run`:

```sh
# from a clone of lemmi-ai-kit
PYTHONPATH=plugins/core/src PYTHONDONTWRITEBYTECODE=1 uv run --no-project python -m lemmi_ai_kit scaffold /path/to/your/project --dry-run
```

Against a project that already has an `AGENTS.md`, that prints:

```text
[dry-run] lemmi-ai-kit 0.2.0 scaffold -> /path/to/your/project
[dry-run] written: 6  seeded: 4  overwritten: 0  unchanged: 0

[dry-run] kept 1 project-owned seed file(s) (use --reseed to overwrite):
  - AGENTS.md
```

`overwritten: 0`, and your file named explicitly under "kept". Nothing was
written — `--dry-run` only reports.

> **The one destructive flag:** `--reseed` *does* overwrite `AGENTS.md`,
> `CLAUDE.md` and your `.ai/` state logs with fresh templates. There is no reason
> to pass it during adoption. (`--force` is milder — it touches only the
> kit-managed files, which are `.ai/templates/` and `.ai/git-stacked-pr-workflow.md`,
> and never a seed file.)

#### So how do you get the kit's content into a file it refuses to write?

That is `kit-setup`'s job, and it is the reason the skill exists on top of the
helper. It is instructed to:

1. Read what you already have — `README.md`, `CONTRIBUTING.md`, your existing
   `AGENTS.md` / `CLAUDE.md` / `.cursorrules` — and treat it as source material.
2. Mine your existing conventions into the `project-rules` block rather than
   discarding them.
3. Show you which blocks it would add or change **as a diff**, and apply only
   what you approve.
4. Fold in, never delete. Your content is not dropped to make room.

For an existing `CLAUDE.md`, it offers to insert the kit's skill index as a
marked `skills-index` block rather than replacing your file.

#### The recommended order for this case

```sh
# 1. See exactly what would be touched. Writes nothing.
PYTHONPATH=plugins/core/src PYTHONDONTWRITEBYTECODE=1 uv run --no-project python -m lemmi_ai_kit scaffold . --dry-run

# 2. Make sure your existing files are committed, so any change is reviewable.
git add -A && git commit -m "checkpoint before lemmi-ai-kit adoption"
```

Then, in your agent:

```
/lemmi-ai-kit-core:kit-setup
```

Review the diff it proposes. Approve the blocks you want. `git diff` afterwards
is the real check — and because you committed first, `git checkout -- AGENTS.md`
undoes the whole thing.

#### Where your existing conventions end up

You have a choice, and it is worth making deliberately:

| Your existing rule | Put it in |
|---|---|
| Specific to this repository | `### Project rules` |
| A language-wide rule your whole org follows | still `### Project rules` for now — until a second repo needs it, at which point see [C](#c-your-language-has-no-pack) |
| Contradicts something the kit says | `### Project rules`. It comes last in the file, so it wins |

That last row is the important one. You do not need to edit or fork the kit's
rules to disagree with them. State your version in `### Project rules` and it
takes precedence.

---

### B. Single-language team, starting fresh

The straightforward path.

```sh
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
```

If you are a Python project, add the Python pack:

```sh
claude plugin install lemmi-ai-kit-python@lemmi
```

Then, in the project directory:

```
/lemmi-ai-kit-core:kit-setup
```

Answer its questions, let it write the files from
[section 4](#what-it-writes-and-who-owns-it), and commit them:

```sh
git add AGENTS.md CLAUDE.md .ai/
git commit -m "Adopt lemmi-ai-kit"
```

You are done. `### Project rules` starts as a stub and fills in over time — as
you work, `task-learnings` writes observations to `.ai/learnings.md`, and running
`/lemmi-ai-kit-core:learning-consolidator` every week or so promotes the durable
ones into `AGENTS.md`. You do not have to seed it up front.

If you are **not** on Python, omit the Python pack and read [C](#c-your-language-has-no-pack)
— it is short, and it is the answer to "where do my language's rules go".

---

### C. Your language has no pack

You write Go. Or Rust, or TypeScript, or C#. The kit ships no conventions pack
for your language.

**You do not need one.** For the shared project workflow, install Core:

```sh
claude plugin install lemmi-ai-kit-core@lemmi
```

Core works on a Go repository: commit messages, specs, post-task review, the
learnings loop, branch handling and code review are language-neutral. Add the
Research pack if you want source planning or parallel research. That is the boundary from
[section 1](#what-you-get), not an aspiration.

Then put your Go conventions in `### Project rules`, exactly as in
[section 5](#5-the-seam--where-your-conventions-attach). That is the entire path.
No fork, no pack, nothing published, and you keep receiving core updates.

One rough edge to expect, because it is easier to delete than to be surprised by:
the `AGENTS.md` template is the same for every language, so the file you are
seeded with carries a `### Python rules (Python projects)` block whatever your
project is written in. No core skill depends on it. Delete the block; it sits
outside every marker, so `kit-setup refresh` will not put it back, and the
scaffold will not either unless you pass `--reseed`.

#### When to author a pack instead

Author one when **a second repository needs the same conventions**. One repo is a
`### Project rules` section; five repos is a pack, because otherwise you are
maintaining the same rules in five places by hand.

The kit has two kinds of optional families: shared workflow packs (Research,
Orchestration and Skill Authoring) and language conventions packs (currently
Python). A `-go` pack would carry reusable Go conventions, while framework or
team rules normally stay in each project's `### Project rules` section.

**Authoring is documented, and it assumes you have cloned this repository.** There is a
pack template (`plugins/_template/`), a scaffolding command (`new-pack`), and
[docs/authoring-a-pack.md](authoring-a-pack.md). What that document does not do is state
the contents of the files it tells you to create — it points at the template and at the
existing packs — so it works as a checklist beside a clone and not as a specification on
its own. The assumption is enforced rather than merely implied: run `new-pack` outside a
git checkout and it exits non-zero with `not inside a git checkout`, and no prose in the
document recovers you from there.

None of which you need. **If you are not sure you want a pack, stay in `### Project rules`**
— it costs you nothing to move the rules later, since a pack skill is the same markdown in
a different file.

---

### D. Two frameworks over one core

An Angular team and a Vue team, sharing an organisation and wanting shared
workflow without carrying each other's framework rules.

Both teams install Core:

```sh
claude plugin install lemmi-ai-kit-core@lemmi
```

Then the answer depends on one thing: **do the two apps live in separate
repositories, or one?**

#### Separate repositories — solved

Each repository gets its own `AGENTS.md`, so each team's `### Project rules`
is private to it by construction. The Angular team writes Angular rules; the Vue
team writes Vue rules; neither sees the other's. Nothing further is needed.

If the two teams share TypeScript conventions that are true for both, those are a
candidate for a single `-typescript` pack later — one pack on the language axis,
with the framework differences staying in each repository's `### Project rules`.
There is no `-angular` and no `-vue` pack, and there is not meant to be: the axis
is language.

#### One monorepo — works, with a caveat you should know about

`kit-setup` and the scaffold operate on a **target directory**, not on a
repository, so you can set up each package independently:

```sh
# from a clone of lemmi-ai-kit
PYTHONPATH=plugins/core/src PYTHONDONTWRITEBYTECODE=1 uv run --no-project python -m lemmi_ai_kit scaffold /path/to/monorepo/apps/angular
PYTHONPATH=plugins/core/src PYTHONDONTWRITEBYTECODE=1 uv run --no-project python -m lemmi_ai_kit scaffold /path/to/monorepo/apps/vue
```

That produces two independent `AGENTS.md` files with two independent
`### Project rules` sections — verified to work. Two caveats, both real:

- **Each target also gets its own `.ai/` tree** — two `learnings.md`, two
  changelogs. The learnings loop is per-directory, so the two teams accumulate
  rules separately. That is usually what you want here, but it is a duplication
  to be aware of rather than a surprise to discover.
- **Whether your agent actually picks up the nested `AGENTS.md`** when working
  inside `apps/angular/` is behaviour of your host (Claude Code, Codex), not of
  this kit, and **it has not been tested here.** Check it before relying on it:
  put a distinctive rule in `apps/angular/AGENTS.md`, start a session in that
  directory, and ask the agent to state the project rules it can see.

If nested pickup does not work on your host, the fallback is a single
repository-root `AGENTS.md` whose `### Project rules` section is subdivided by
package with plain markdown subheadings. Both teams then see both sets of rules.
That is worse, and this guide will not pretend otherwise.

---

## 7. Staying up to date

Skills live in the plugin, not in your repository, so they update when the plugin
updates. Your `AGENTS.md`, `CLAUDE.md` and `.ai/` files are yours and are never
updated behind you.

Enable, disable and update each installed pack through your host's plugin
interface. Research and Python remain usable by themselves; if you disable
Core, Orchestration and Skill Authoring lose their required dependency. For an
existing project-scoped Claude install, `claude plugin update
lemmi-ai-kit-core@lemmi --scope project` refreshed Core in the 2026-09-14
check. Use the original installation scope; `claude plugin install` alone
reported that the existing pack was already installed. On Codex,
`codex plugin add lemmi-ai-kit-core@lemmi` refreshes Core. Native plugin
controls also manage each pack's enabled state.

After an update that changed detection or templates, optionally re-run:

```
/lemmi-ai-kit-core:kit-setup refresh
```

which touches only marked blocks and asks before changing any block you have
hand-edited.

Because the marketplaces serve this repository directly, there is no separate
release channel — the published state of `main` is the release.

If you installed Core before 0.2.0, read [Migrating to 0.2.0](migrating-to-0.2.0.md):
Research, Orchestration and Skill Authoring moved out of Core, so install those
three packs to keep all formerly bundled capabilities. Existing project rules
and `.ai/` data stay in your repository.

---

## What is not built yet, and what is not verified

Collected honestly, because a guide that quietly routes around its own gaps
wastes your afternoon.

### Not built

| Gap | What it means for you |
|---|---|
| **Pack authoring assumes a clone** | The template, the `new-pack` command and [the authoring document](authoring-a-pack.md) all exist. What the document does not carry is the contents of the files it asks you to create, so it reads as a checklist next to a checkout rather than a standalone spec. The assumption is hard: `new-pack` exits non-zero outside a git checkout. Fine if you are working from a clone; a wall if you are not |
| **No documented private-pack path** | Serving a pack from your own private marketplace should work — both hosts support it — but it has not been tested here and this guide will not walk you through an unverified path |
| **No Go, TypeScript or Rust conventions pack** | Those languages use project rules or a contributed language pack. See [C](#c-your-language-has-no-pack) |
| **No pre-merge review of contributed packs** | The path itself is now documented — see [CONTRIBUTING.md](../CONTRIBUTING.md) for where a pack goes, how first-party packs are named, and what to do about a merged pack that turns out to be harmful. What does **not** exist is a review bar: **merged does not mean vetted.** Since a skill is instructions an agent follows — and can direct shell commands inside whoever installs it — read a third-party pack before you install it, exactly as you would a dependency |
| **No guided onboarding interview** | `kit-setup` does the *detection* half well — it reads your manifests, lockfiles and CI. It does not yet do the *interview* half: asking you about your project, your existing conventions, and your architecture, then producing a project map and derived conventions from your actual code. Today you get detection plus whatever you write into `### Project rules` yourself |

### Not verified

| Gap | What it means for you |
|---|---|
| **The 0.2.0 Git-based release has not been published** | All five packs were installed from a local checkout on both hosts; teammates need the source changes published before installing the new packs from Git |
| **The `owner/repo` marketplace shorthand has not been exercised** | Use the [local clone path](#if-the-ownerrepo-shorthand-does-not-resolve), which is the documented route here |
| **Nested `AGENTS.md` pickup in a monorepo** | Scaffolding per-package works. Whether your host reads the nested file is untested — see [D](#one-monorepo--works-with-a-caveat-you-should-know-about) for how to check it in two minutes |

If you hit one of these, an issue naming your language or framework is the most
useful thing you can send — it is the signal that decides which pack gets built
next.
