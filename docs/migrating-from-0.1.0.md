# Migrating from 0.1.0

The kit used to install as **one plugin named `lemmi-ai-kit`**. Its first split
created `lemmi-ai-kit-core` and `lemmi-ai-kit-python` at version 0.1.0.
Version 0.2.0 then moved three workflow families out of Core. This note covers
the first split; follow it with [Migrating to 0.2.0](migrating-to-0.2.0.md) to
retain the skills that later moved.

This note is for anyone who installed before the split. If you are installing for
the first time, read the [README](../README.md) or the [adoption
guide](adoption-guide.md) instead — none of this applies to you.

## The version number will not tell you which one you have

At the **first split**, both the old single plugin and the then-current Core
and Python packs declared version `0.1.0`. That historical equality made the
plugin name the only reliable discriminator. The current base release is
`0.2.0`; a local Core payload can add SemVer build metadata to that version.
Check the name and base release now.

`lemmi-ai-kit` means you still have the retired single plugin. A Core pack at
0.1.x has completed only the first split; use the 0.2.0 note next.

## What changed in the first split

| | Single plugin | First packs at 0.1.0 |
|---|---|---|
| Plugins served | one, `lemmi-ai-kit` | one per pack: `lemmi-ai-kit-core`, `lemmi-ai-kit-python` |
| Install | `lemmi-ai-kit@lemmi` | `lemmi-ai-kit-core@lemmi`, plus `lemmi-ai-kit-python@lemmi` if you write Python |
| Typing a skill | `/lemmi-ai-kit:<name>` | `/lemmi-ai-kit-core:<name>` |
| Python conventions | inside the one plugin, always installed | a **separate pack** — a core-only install does not carry them |
| Skills in the repo | inside the Python support package | `plugins/<pack>/skills/` |

The old plugin id is gone from both marketplace catalogs. It cannot be
reinstalled and will never be updated again, so an existing install is now a
stale local copy rather than an older version of something live.

**How many skills you end up with depends on which packs you install**, which is
why this note quotes no total. Ask your client for the inventory instead —
[Verify](#verify) below — and trust that number, because it is the one your
machine actually has.

## What to run

**1. See what you have.**

```
claude plugin list
```

If `lemmi-ai-kit` is listed, remove it with your client's uninstall command. This
note does not quote a spelling for that one, because it has not been run here and
an invented command in a migration document is worse than none — `claude plugin
--help` carries it.

**2. Add the marketplace and install the packs.**

```
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
```

Python projects also want `claude plugin install lemmi-ai-kit-python@lemmi`.

`./` — with the trailing slash — is the source that was verified. A bare `.` is
**rejected** as an invalid source format, so the slash is not cosmetic. These are
the local-clone commands: clone the repository and run them from inside it. The
`owner/repo` marketplace shorthand is **unverified** — it has not been
exercised against this repository on either host — so it is not the path this
note tells you to migrate on.

Codex spells "here" differently and takes a different install verb; see [the
adoption guide](adoption-guide.md#3-install), which records what each host was
verified with.

**3. Verify by name** — the next section. It is the step worth not skipping.

## Verify

```
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
claude plugin details lemmi-ai-kit-core
```

`plugin details` prints the component inventory **by name** — `Skills (N)`
followed by every skill name. Read the names.

That is the entire reason this step exists. **A green "installed" message is not
evidence.** A fixture in this project's own history showed a plugin host
accepting a plugin that carried **no manifest at all**, reporting it installed,
with the version silently degraded to `"local"`. Any check that reads "install
succeeded" as "the pack is correct" is unsound. An inventory you can read is a
check; an exit code is not.

Those three lines were executed against the then-current 0.1 packs on Claude
Code; the [adoption
guide](adoption-guide.md#how-verified-each-of-these-is) records what was run on
which host, and when.

## Then fix your own project's files

Moving the plugin touches nothing inside your repository, and that is the
problem. Your `CLAUDE.md` was rendered when you first ran `kit-setup`, and its
skill index still says `/lemmi-ai-kit:<name>` on every line you would type.

**Nothing fixes that for you.** Re-running the scaffold reports `CLAUDE.md` as
*kept* and changes nothing: it is a project-owned seed file, and seed files are
never overwritten. That is correct behaviour — it is what stops the kit eating
your edits — but it means the stale prefixes survive a re-run, silently.

**Do not reach for `--reseed`.** It does overwrite `CLAUDE.md` and it does fix the
prefixes. It also overwrites *every* seed file, and `AGENTS.md` and the `.ai/`
state logs are seed files too: run against a project with a filled-in `AGENTS.md`
and an intake file that has entries in it, `--reseed` replaces all three with
empty templates. There is no flag that means "only re-render the index".

For the first split, the find-and-replace in your own `CLAUDE.md` was:

```
/lemmi-ai-kit:   ->   /lemmi-ai-kit-core:
```

At 0.2.0, some of those Core-prefixed skills moved again. Check each moved
skill's current namespace in [Migrating to 0.2.0](migrating-to-0.2.0.md).
Only the skills you *type* carry a prefix at all. Auto-loaded and internal
skills are listed by bare name in that index and need no edit.

Then check anything else of yours that names a skill by its old prefix — the
`### Project rules` section of your `AGENTS.md`, a team README, a CI comment, a
saved prompt. The kit cannot see those files and will not warn you about them.

## Four skills were also renamed, and one was dropped

Separately from the split, and inside the same `0.1.0`:

| Old name | Now | Typed? |
|---|---|---|
| `fable-orchestrate` | `orchestrate` | **yes** — update it wherever you type it |
| `lemmi-python-conventions` | `python-conventions` | no, auto-loaded |
| `lemmi-test-conventions` | `test-conventions` | no, auto-loaded |
| `lemmi-vertical-slice` | `vertical-slice` | no, auto-loaded |

The brand and the model name came out of the names an adopter has to type; they
stay in the repository URL and the marketplace owner, where they belong.

`openai-realtime-quirks` was removed from the catalog during that first split.

The auto-loaded three need no edit for the agent to keep finding them, but if you
named one in your own `AGENTS.md` or in a prompt, that reference now points at
nothing.

## If a skill is missing after the move

Check the pack before assuming it is gone. The Python conventions moved into
`lemmi-ai-kit-python`, so a core-only install genuinely does not have them, and
that is not a bug — install the Python pack.

To see which pack a skill is in today, check the pack's inventory with
`plugin details` or the current manifest's profile-to-pack mapping. In 0.2.0,
the five approved profiles map one-to-one to their native packs.
