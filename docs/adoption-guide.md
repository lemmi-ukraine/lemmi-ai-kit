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

The kit ships two plugins ("packs"). How many skills you end up with depends on
which of them you install, so this guide quotes no total — ask your client for the
inventory instead, as **Check that it worked** below shows.

| Pack | Plugin name | What is in it |
|---|---|---|
| Core | `lemmi-ai-kit-core` | Everything language-agnostic: project setup, spec-driven development, post-task review, the learnings loop, orchestration, research, code review, commit messages, branch handling |
| Python | `lemmi-ai-kit-python` | `python-conventions` and `test-conventions` — both auto-loaded, neither ever typed |

**Core is genuinely language-agnostic, and that is enforced rather than
promised.** No core skill names a Python-pack skill; where a core skill needs to
reach for language conventions it refers to them by role ("the installed coding
conventions skill"), not by name. A test in this repository
(`tests/test_pack_boundaries.py`) fails if that ever stops being true.

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
third, separate, entirely optional step — and it is not documented yet (see
[What is not built yet](#what-is-not-built-yet-and-what-is-not-verified)).

---

## 3. Install

Skills are managed by the plugin and update with it. Nothing is copied into your
project by installing.

### Claude Code

```
/plugin marketplace add lemmi-ukraine/lemmi-ai-kit
/plugin install lemmi-ai-kit-core@lemmi
```

Python projects only — skip it otherwise:

```
/plugin install lemmi-ai-kit-python@lemmi
```

### Codex

```sh
codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit
codex plugin add lemmi-ai-kit-core@lemmi
```

Python projects only:

```sh
codex plugin add lemmi-ai-kit-python@lemmi
```

You can also add the marketplace and then install from Codex's plugin directory
UI by selecting the **Lemmi** marketplace.

### If the `owner/repo` shorthand does not resolve

Clone the repository and add it as a local marketplace. **This is the path that
has actually been executed end-to-end** (see the honesty note below):

```sh
git clone https://github.com/lemmi-ukraine/lemmi-ai-kit
cd lemmi-ai-kit
```

Then, in Codex:

```sh
codex plugin marketplace add .
codex plugin add lemmi-ai-kit-core@lemmi
```

Or in Claude Code:

```sh
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
```

**The two clients do not spell "here" the same way, and the difference is not
cosmetic.** Codex was verified with `.`; Claude Code rejects `.` outright with
`Invalid marketplace source format` and was verified with `./`. Each form above
is the one actually run against that client — neither spelling has been shown to
work on the other, so use the line matching your client rather than assuming the
trailing slash is optional.

### How verified each of these is

Be aware of what has and has not been proven, because the two install paths are
not equally exercised:

- **Codex, from a local clone — verified.** Run on 2026-08-23 with codex-cli
  0.149.0 against an isolated `CODEX_HOME`. Both packs installed and enabled,
  and every skill file the manifest listed that day physically materialized. A
  core-only install was separately confirmed to carry the core skills and **no**
  Python skills.
- **Claude Code, from a local clone — verified.** Run on 2026-08-23:
  `claude plugin marketplace add ./`, then `claude plugin install
  lemmi-ai-kit-core@lemmi`, then `claude plugin details lemmi-ai-kit-core`,
  which listed the installed core skills by name. The `.` form of
  `marketplace add` was rejected by this client; see above.
- **The `owner/repo` shorthand — not yet exercised** against this repository on
  either host. If it fails, use the clone-and-add-local fallback above.

### Check that it worked

```sh
codex plugin list      # Codex
claude plugin list     # Claude Code
```

You should see `lemmi-ai-kit-core@lemmi` installed and enabled.

That only tells you the install did not error, which is weaker evidence than it
looks: an earlier probe of this kit showed a client will report a plugin as
installed when it carries no manifest at all. So ask for the inventory by name:

```sh
claude plugin details lemmi-ai-kit-core
```

It prints `Skills (N)` followed by every skill name. Read the names. That is the
step that separates a real install from a green message, and it is also the only
count worth trusting — it is the one your machine actually has.

**Most of these do appear in your `/` menu — but not all of them, and that is
correct.** The user-invocable ones show up; the rest are auto-loaded or internal by
design, so the menu is always the shorter list. `plugin details` prints the full
inventory by name, and the `invocation` column in the catalog tells you which is which —
that is the answer for your install, rather than a number this page would have to keep
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
| `.ai/templates/design.md`, `requirements.md`, `tasks.md` | Spec templates used by `spec-driven-dev` | kit-managed — refreshed on update |
| `.ai/git-stacked-pr-workflow.md` | Reference doc for the stacked-PR workflow | kit-managed |

Nine files, all additive. Nothing else in your repository is touched.

### Running it without an agent

`kit-setup` shells out to a small Python helper for the deterministic part. You
can run that yourself from a clone — useful in CI, or if you just want to see
the output before letting an agent near your repo:

```sh
# from a clone of lemmi-ai-kit
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit scaffold /path/to/your/project --dry-run
```

`--dry-run` writes nothing. Drop it to actually place the files. The helper
places files and applies seed semantics; it does **not** do the detection —
filling in your real commands and conventions is the agent's half of the job.

> **Needs Python 3.11 or newer** (it reads TOML with `tomllib`). If your `python3`
> is older you will get a `ModuleNotFoundError: tomllib` — name a newer
> interpreter explicitly, e.g. `python3.12` in place of `python3`. You do not need
> this when running through `kit-setup`; the skill picks a working interpreter
> itself.

---

## 5. The seam — where your conventions attach

This is the part that makes forking unnecessary, and it is the reason the rest of
the guide is short.

### `### Project rules`

The `AGENTS.md` that `kit-setup` writes ends with a section that exists purely
for you:

```markdown
### Project rules
> TODO(project): add project-specific do-nots here as they are discovered
> (the `task-learnings` → `/learning-consolidator` loop will promote them).
```

Replace that stub with your own rules. It sits directly beneath the kit's own
rule sections, so your agent reads the kit's conventions and yours as one
document — and yours come last, so they win where they disagree.

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
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit scaffold /path/to/your/project --dry-run
```

Against a project that already has an `AGENTS.md`, that prints:

```text
[dry-run] lemmi-ai-kit 0.1.0 scaffold -> /path/to/your/project
[dry-run] written: 4  seeded: 4  overwritten: 0  unchanged: 0

[dry-run] kept 1 project-owned seed file(s) (use --reseed to overwrite):
  - AGENTS.md
```

`overwritten: 0`, and your file named explicitly under "kept". Nothing was
written — `--dry-run` only reports.

> **The one destructive flag:** `--reseed` *does* overwrite `AGENTS.md`,
> `CLAUDE.md` and your `.ai/` state logs with fresh templates. There is no reason
> to pass it during adoption. (`--force` is milder — it refreshes the kit-managed
> `.ai/templates/` only.)

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
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit scaffold . --dry-run

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

```
/plugin marketplace add lemmi-ukraine/lemmi-ai-kit
/plugin install lemmi-ai-kit-core@lemmi
```

If you are a Python project, add the Python pack:

```
/plugin install lemmi-ai-kit-python@lemmi
```

Then, in the project directory:

```
/lemmi-ai-kit-core:kit-setup
```

Answer its questions, let it write the nine files, and commit them:

```sh
git add AGENTS.md CLAUDE.md .ai/
git commit -m "Adopt lemmi-ai-kit"
```

You are done. `### Project rules` starts as a stub and fills in over time — as
you work, `task-learnings` writes observations to `.ai/learnings.md`, and running
`/lemmi-ai-kit-core:learning-consolidator` every week or so promotes the durable
ones into `AGENTS.md`. You do not have to seed it up front.

If you are **not** on Python, install core only and read [C](#c-your-language-has-no-pack)
— it is two paragraphs and it is the answer to "where do my language's rules go".

---

### C. Your language has no pack

You write Go. Or Rust, or TypeScript, or C#. The kit ships packs for core and
Python, and nothing for you.

**You do not need one.** Install core alone:

```
/plugin install lemmi-ai-kit-core@lemmi
```

Every skill in the core pack works unchanged on a Go repository. Commit messages,
spec-driven development, post-task review, the learnings loop, branch handling,
code review, research — none of it is language-specific, and none of it will
point you at a Python skill. That is the enforced boundary from
[section 1](#what-you-get), not an aspiration.

Then put your Go conventions in `### Project rules`, exactly as in
[section 5](#5-the-seam--where-your-conventions-attach). That is the entire path.
No fork, no pack, nothing published, and you keep receiving core updates.

#### When to author a pack instead

Author one when **a second repository needs the same conventions**. One repo is a
`### Project rules` section; five repos is a pack, because otherwise you are
maintaining the same rules in five places by hand.

The kit's packs are split on **one axis: language.** A `-go` pack would carry Go
conventions, and nothing else would justify a new pack — not a framework, not a
team, not a domain. (A framework axis gets added only if a language pack ever
actually splits under its own weight, and none has.)

**Authoring is not documented yet.** There is no pack template, no scaffolding
command, and no `docs/authoring-a-pack.md` in this repository today. Until there
is, stay in `### Project rules` — it costs you nothing to move the rules later,
since a pack skill is the same markdown in a different file.

---

### D. Two frameworks over one core

An Angular team and a Vue team, sharing an organisation and wanting shared
workflow without carrying each other's framework rules.

Both teams install core:

```
/plugin install lemmi-ai-kit-core@lemmi
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
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit scaffold /path/to/monorepo/apps/angular
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit scaffold /path/to/monorepo/apps/vue
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

Update through your host's plugin interface — `/plugin` in Claude Code, the
plugin directory in Codex. This guide deliberately does not print an update
subcommand: the exact spelling varies by host and version, and no update command
has been exercised against this repository. Check `codex plugin --help` for
yours.

After an update that changed detection or templates, optionally re-run:

```
/lemmi-ai-kit-core:kit-setup refresh
```

which touches only marked blocks and asks before changing any block you have
hand-edited.

Because the marketplaces serve this repository directly, there is no separate
release channel — the published state of `main` is the release.

---

## What is not built yet, and what is not verified

Collected honestly, because a guide that quietly routes around its own gaps
wastes your afternoon.

### Not built

| Gap | What it means for you |
|---|---|
| **No pack template, no scaffolding command, no `docs/authoring-a-pack.md`** | You cannot follow a documented path to author a pack today. Stay in `### Project rules`; moving rules into a pack later is a copy-paste, not a migration |
| **No documented private-pack path** | Serving a pack from your own private marketplace should work — both hosts support it — but it has not been tested here and this guide will not walk you through an unverified path |
| **No packs beyond core and Python** | Go, TypeScript, Rust and the rest have no pack. See [C](#c-your-language-has-no-pack) |
| **No pre-merge review of contributed packs** | The path itself is now documented — see [CONTRIBUTING.md](../CONTRIBUTING.md) for where a pack goes, how first-party packs are named, and what to do about a merged pack that turns out to be harmful. What does **not** exist is a review bar: **merged does not mean vetted.** Since a skill is instructions an agent follows — and can direct shell commands inside whoever installs it — read a third-party pack before you install it, exactly as you would a dependency |
| **No guided onboarding interview** | `kit-setup` does the *detection* half well — it reads your manifests, lockfiles and CI. It does not yet do the *interview* half: asking you about your project, your existing conventions, and your architecture, then producing a project map and derived conventions from your actual code. Today you get detection plus whatever you write into `### Project rules` yourself |

### Not verified

| Gap | What it means for you |
|---|---|
| **Both local install paths are verified; neither remote one is** | The Claude Code local-marketplace path was executed end to end against this repository on 2026-08-23 and asserted on the materialized inventory **by name**, not on a green "installed" message. The Codex local path was exercised on 2026-08-22 against isolated fixtures. What neither host has done is the `owner/repo` shorthand — see the row below |
| **The `owner/repo` marketplace shorthand has not been exercised** | If it fails on either host, use the clone-and-add-local fallback in [section 3](#if-the-ownerrepo-shorthand-does-not-resolve), which is verified |
| **Nested `AGENTS.md` pickup in a monorepo** | Scaffolding per-package works. Whether your host reads the nested file is untested — see [D](#one-monorepo--works-with-a-caveat-you-should-know-about) for how to check it in two minutes |

If you hit one of these, an issue naming your language or framework is the most
useful thing you can send — it is the signal that decides which pack gets built
next.
