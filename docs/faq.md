# FAQ

Short answers. Where an answer needs more than a paragraph it links to the
[adoption guide](adoption-guide.md), which is the long-form version.

Every answer here is either checkable in this repository or marked as unverified.
Where the kit has no answer yet, this page says so rather than inventing one.

---

## What is an "agent skill"?

A markdown document your AI coding agent loads when it becomes relevant. It is not
code, it does not run on its own, and it is not a library your project depends on.
`commit-message`, for example, is a document telling the agent how to read a diff
and write a conventional commit message.

Skills come in three kinds: **user-invocable** ones you type as a slash command,
**auto-loaded** ones the agent pulls in as background knowledge when the topic comes
up, and **internal** ones another skill calls in a pipeline. Only the first kind
appears in your `/` menu, so that menu is always shorter than the catalog.

## How is this different from a folder of prompts I copy into my repo?

Three differences that matter in practice.

**Nothing is copied.** The plugin owns the skills and updates them. A prompt folder
is a fork of someone else's text that you re-merge by hand every time it changes.

**The skills hand off to each other.** A spec gates the code, the post-task review
feeds `.ai/learnings.md`, and a consolidator promotes the durable observations into
your `AGENTS.md`, where every later task reads them. A prompt starts from nothing
and ends where it ends.

**Your conventions are not in competition with the kit's.** They attach at a
documented seam in a file you own, and they come last, so they win. That is the
reason nobody needs to fork this.

## Does it work with Codex?

Yes. Both packs carry a Codex manifest alongside the Claude Code one, and the same
skills install from the same catalog.

Be aware of how far that has been proven, because the two hosts are not equally
exercised. Adding a **local clone** as a marketplace and installing from it has been
run end to end on both hosts. The `owner/repo` marketplace shorthand has **not** been
exercised against this repository on either host — it could not be tested while the
repository was private. If the shorthand does not resolve, the
[install section](adoption-guide.md#3-install) of the adoption guide has the verified
fallback and the exact spelling each client accepts. They differ, and the difference
is not cosmetic.

## Does it work with Cursor, Copilot, or some other agent?

The skills do not — they install through the plugin systems of Claude Code and
Codex, and no other host is supported today.

Your project conventions do carry over, though, and that is most of the value.
`kit-setup` writes [`AGENTS.md`](https://agents.md/), a cross-tool convention
stewarded by the Agentic AI Foundation under the Linux Foundation and read by 20+
agents and platforms. Another agent opening your repository will find and follow
that file. It simply will not have the workflow skills that maintain it.

## Do I have to be a Python project?

No. The core pack is language-agnostic, and that is enforced rather than promised:
no core skill references a Python-pack skill, and where a core skill needs language
conventions it refers to them by role — "the installed coding conventions skill" —
never by name. `tests/test_pack_boundaries.py` fails if that stops being true.

Install core on its own and skip the Python pack entirely.

## My language has no pack. Can I still use this?

Yes, and you probably do not want a pack anyway. Install core, then put your Go,
Rust, TypeScript or C# conventions in the `### Project rules` section of your
`AGENTS.md`. Every core skill works unchanged, and none of them will point you at a
Python skill.

Author a pack only when a *second repository* needs the same conventions — one repo
is a section in a file, several repos is a pack. See
[the adoption guide's walkthrough](adoption-guide.md#c-your-language-has-no-pack).

## Do I have to fork it to add my own rules?

No, and this is the design decision the rest follows from. The `AGENTS.md` that
`kit-setup` writes ends with a `### Project rules` section that exists purely for
you. It sits last in the file, so where your rules and the kit's disagree, yours
take precedence — with nothing to register and no schema to satisfy.

The [seam section](adoption-guide.md#5-the-seam--where-your-conventions-attach) of
the adoption guide covers it, including what to do when you already have conventions
written down somewhere else.

## What does it actually put in my repository?

Four things, and you own all of them: `AGENTS.md`, `CLAUDE.md`, an `.ai/` directory
of intake and log files the workflow writes to, and `.ai/templates/` for the spec
documents. Nothing else, ever — it does not touch your source code.

## Will it overwrite my existing `AGENTS.md`?

No. The deterministic helper underneath refuses to overwrite `AGENTS.md` outright
rather than risk a bad merge, and the `kit-setup` skill is instructed to read what
you already have, mine your existing conventions into the generated blocks, show you
a diff, and fold in rather than delete.

**One honest caveat, worth knowing before you rely on it.** The generated blocks are
delimited by HTML-comment markers, but the mechanism that respects them is
*instructions to an agent, not a deterministic transform* — no code parses the
markers and mechanically splices content. In practice that means: keep `AGENTS.md`
in version control, and read the diff `kit-setup` shows you before approving it.
Then a bad refresh is one `git diff` away from being spotted.

## Does installing it add a dependency to my project?

No. There is nothing to `pip install`, no entry in your lockfile, and no change to
how you build, test, or deploy. The Python package in this repository is not an
installer — it is the helper `kit-setup` shells out to for the deterministic part of
scaffolding, and it runs from the plugin's own cache.

## How many skills are there?

Ask your client rather than a document, because the answer depends on which packs
you installed:

```sh
claude plugin details lemmi-ai-kit-core
```

That prints the inventory by name, which is the only count that describes the
machine you are on. `codex plugin list` is the equivalent starting point on the other
host. From a clone of this repository:

```sh
PYTHONPATH=plugins/core/src python3 -m lemmi_ai_kit list
```

The README states exact totals because a test in this repository checks them against
the manifest on every run. This page states none, because nothing would check them
here — and a hand-written count in a document is wrong the first time the catalog
changes.

## How do skills get updated?

Through your host's plugin interface — `/plugin` in Claude Code, the plugin directory
in Codex. This page deliberately prints no update subcommand: the spelling varies by
host and version, and no update command has been exercised against this repository.
Check your client's `plugin --help`.

Your `AGENTS.md`, `CLAUDE.md` and `.ai/` files are yours and are never updated behind
you. There is no separate release channel either — the marketplaces serve this
repository directly, so the published state of `main` is the release.

## My `/lemmi-ai-kit:...` commands stopped working. What happened?

The kit used to install as one plugin called `lemmi-ai-kit`. It now installs as
packs, so the prefix you type is `/lemmi-ai-kit-core:<name>`, and the install
command changed with it. The old plugin id is gone from both marketplace catalogs:
it cannot be reinstalled and will never be updated again.

**The version number will not tell you which one you have** — both declare `0.1.0`,
because pushing to `main` is the release and the string did not move across the
split. The plugin *name* in `plugin list` is the discriminator.

**And your own repository does not fix itself.** The `CLAUDE.md` in your project
still carries the old prefixes, and re-running scaffolding will not touch it: seed
files are never overwritten, so it reports the file kept and changes nothing. Do
**not** reach for `--reseed` to force it — that resets seed files to their
templates, and it will take a customized `AGENTS.md` and a non-empty `.ai/` log with
it. A find-and-replace is the fix.

[Migrating from 0.1.0](migrating-from-0.1.0.md) has the whole path, including the
four skills that were renamed and the one that was dropped.

## What happens if I run setup again later?

`/lemmi-ai-kit-core:kit-setup refresh` re-runs project detection and compares each
generated block against what detection would produce now. Where a block has been
hand-edited it says so and asks you, per block, whether to keep, replace, or merge.
Content outside every marked block is not touched.

Run it after you change package manager, add CI, or rename your test command.

## Can a skill run commands on my machine?

Yes, and you should decide about this on purpose rather than by default.

A skill is instructions an agent follows. Several skills in this pack instruct the
agent to run commands — `git`, `ruff`, `pytest`, a script over your session logs —
and some ship scripts of their own. An agent following a malicious skill would run
whatever that skill told it to, with whatever permissions your agent has, in your
repository. There is no sandbox between a skill and your working tree.

That is the premise of the tool rather than a defect in it, but it is the reason
[SECURITY.md](../SECURITY.md) exists and is worth reading before you install. It
states what is in scope for a report and how to send one privately.

## What is "spec-driven development" here, exactly?

Writing the specification before the code, as artifacts the agent produces and you
approve: **requirements**, then **design**, then a **task breakdown**, with a gate at
each step and a critic pass over the result. The kit scaffolds templates for all
three plus test cases and a test plan.

The term was popularized by [GitHub Spec Kit](https://github.com/github/spec-kit);
this particular triad matches [Kiro's spec artifacts](https://kiro.dev/docs/specs/).
The kit's version is smaller than either and is designed to sit inside a normal task
rather than replace your process.

## Can I use it in a monorepo?

Partly, and the untested part is worth knowing. Scaffolding per package works — run
the helper once per package directory and each gets its own `AGENTS.md`. Whether
your agent host actually *reads* a nested `AGENTS.md` when working inside that
package is **untested here**;
[situation D](adoption-guide.md#d-two-frameworks-over-one-core) in the adoption guide
shows how to check it against your own host in about two minutes.

## Is this free? What is the license?

MIT — see [LICENSE](../LICENSE). Contributions are inbound-equals-outbound: opening a
pull request licenses your contribution under the same terms. There is no CLA to
sign and no `Signed-off-by` trailer to remember.

## Can I contribute a skill, or a pack?

Yes. [CONTRIBUTING.md](../CONTRIBUTING.md) covers reporting an issue, setting up the
development environment, the four checks CI runs, the hygiene contract that can fail
a documentation-only pull request, adding a skill, and contributing a language or
domain pack.

If you are here because your language has no pack, the most useful thing you can send
is an issue naming that language and framework — it is the signal that decides which
pack gets built next.

## Who maintains this, and where do I report a problem?

Lemmi maintains it, with one reviewer, so expect days rather than hours.

- **A bug, or a skill that misbehaves** — open one of the
  [issue forms](../.github/ISSUE_TEMPLATE).
- **A security problem** — email **support@lemmi.io**, and do not open a public
  issue. [SECURITY.md](../SECURITY.md) has the scope and the response expectations.
- **A code-of-conduct concern** — the same address; see
  [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).

## What is not built yet?

The adoption guide keeps that list, collected in one place and updated as things
land: [What is not built yet, and what is not verified](adoption-guide.md#what-is-not-built-yet-and-what-is-not-verified).
It is worth a minute before you plan around a capability — a guide that quietly
routes around its own gaps wastes your afternoon.
