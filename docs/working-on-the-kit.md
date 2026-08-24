# Working on the kit

For people changing the kit rather than using it. If you arrived here to install
it, start at the [README](../README.md) or the [adoption guide](adoption-guide.md)
instead.

Two procedures are settled elsewhere and are deliberately not repeated here,
because a procedure written down twice drifts and the copy nobody re-runs is the
one that rots:

| Question | Where it is answered |
|---|---|
| How do I report an issue, set up the development environment, run the four checks CI runs, or add a skill? | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| How do I author a pack — the scaffold command, and the registration edits it does not make? | [Authoring a pack](authoring-a-pack.md) |

What is below is the mechanics both of those stand on: where things live, what the
support CLI is for, and what a version bump has to touch.

## Repository layout

| Path | What it is |
|---|---|
| `.claude-plugin/marketplace.json` | Claude Code marketplace catalog for the packs in `plugins/*` |
| `.agents/plugins/marketplace.json` | Codex marketplace catalog for the same packs |
| `plugins/core/`, `plugins/python/` | the two packs — per-host manifests plus the skill directories under `skills/` |
| `plugins/_template/` | the skeleton `new-pack` copies; its placeholders are filled from `pyproject.toml` at scaffold time |
| `plugins/core/src/lemmi_ai_kit/` | the support package behind the CLI: scaffolding, the manifest reader, the `.ai/` and skill checks, and the publish guard |
| `plugins/core/src/lemmi_ai_kit/assets/manifest.toml` | the skill registry — one `[[skills]]` entry per skill, carrying `name`, `profile`, `invocation` and `summary` |
| `plugins/core/src/lemmi_ai_kit/assets/templates/` | the `AGENTS.md` and `CLAUDE.md` seeds `scaffold` writes |
| `plugins/core/src/lemmi_ai_kit/assets/ai/` | the `.ai/` payload — the empty state logs, the stacked-PR workflow note, and the spec templates |
| `.vscode/` | editor settings and extension recommendations, shared rather than personal |

Two things about that table are worth stating rather than leaving to be inferred.

**The registry lives in the core pack and registers the skills of every pack.**
There is no per-pack manifest. `list` and the rendered `CLAUDE.md` index both read
from it, and the suite enforces a bijection between its entries and the directories
under `plugins/*/skills/` — so a skill directory with no row, or a row with no
directory, makes `load_manifest()` raise and takes a large part of the suite down
at once rather than pointing at the thing you just did.

**`profile` is not `pack`.** The registry records a *profile*; the pack is derived
from it. That is why adding a pack means registering its profile as well as its
name — the trap is written up in
[Authoring a pack](authoring-a-pack.md#2-register-it--seven-edits-new-pack-does-not-make).

## The support CLI

The Python package is **not an installer**. It is the deterministic helper the
`kit-setup` skill shells out to, and a development tool for this repository.
Installing the kit does not require it, and nothing in an adopter's project depends
on it.

```sh
uv run python -B -m lemmi_ai_kit list
uv run python -B -m lemmi_ai_kit scaffold <target> --dry-run
```

| Subcommand | What it does |
|---|---|
| `scaffold` | place the project-owned files — `AGENTS.md`, `CLAUDE.md`, `.ai/` — into a project |
| `list` | print the skill catalog from the manifest |
| `lint` | validate a project's `.ai/` pipeline data files |
| `audit-skills` | audit a project's skills directory against the review checklist |
| `publish-check` | refuse to publish while the payload carries untracked or ignored files |
| `new-pack` | scaffold a new pack from `plugins/_template` — see [Authoring a pack](authoring-a-pack.md) |

`--help` on the command or any subcommand is the authority; the table above is a
map, not a contract. Python 3.11 or newer is required, since the manifest is read
with `tomllib`.

**Pass `-B`** on every command that imports this package. Any import writes
`__pycache__/*.pyc` inside the payload — bytecode git does not track, which
`publish-check` then refuses on, with a failure that names files you never wrote.
A test run imports it too and takes no `-B` of its own, so
`PYTHONDONTWRITEBYTECODE=1` in the environment is the form that covers everything:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest
```

[Authoring a pack, step 3](authoring-a-pack.md#3-verify-it) has the measurement
behind this.

### What `scaffold` will and will not overwrite

It never copies skills and never overwrites an existing seed file, which is what
makes re-running it safe.

| Flag | Effect |
|---|---|
| *(none)* | writes what is missing and keeps every seed file that already exists |
| `--dry-run` | reports what would change and writes nothing |
| `--force` | updates the kit-managed `.ai/templates/` |
| `--reseed` | resets seed files to their templates — it will discard a customized `AGENTS.md` or a non-empty `.ai/` log |

`--reseed` is the blunt one and it is **not** an upgrade path.
[Migrating from 0.1.0](migrating-from-0.1.0.md) has what to do instead.

### How the skill reaches the helper

`kit-setup` runs it straight from the plugin cache, by putting the plugin root's
`src/` on `PYTHONPATH`. Claude Code supplies `CLAUDE_PLUGIN_ROOT`; Codex supplies
`PLUGIN_ROOT` and sets `CLAUDE_PLUGIN_ROOT` too, for compatibility. No `pip
install` is involved anywhere on that path, which is also why the same call works
from a clone with `plugins/core/src` on `PYTHONPATH` instead.

## Versioning and releasing

There is no publish pipeline. The marketplaces serve this repository directly, so
**pushing to `main` is the release**, and CI gates code quality only.

A version bump touches `pyproject.toml` and both manifests of every pack:

- `pyproject.toml` — `project.version`, the source the others are checked against
- `plugins/<pack>/.claude-plugin/plugin.json`
- `plugins/<pack>/.codex-plugin/plugin.json`

`plugins/_template/` is the exception. It carries a `{{VERSION}}` placeholder that
`new-pack` fills from `pyproject.toml`, so writing a real version into it would
break the template rather than release it. The two marketplace catalogs carry no
version at all.

`tests/test_plugin.py` holds every pack manifest against `pyproject.toml` on both
hosts, so a half-finished bump fails the suite instead of shipping.

## Syncing from upstream

The skills were extracted from another repository and still move in both
directions. [Syncing from upstream](syncing-from-upstream.md) is the procedure,
together with the drift measurement it depends on and the debt it has recorded so
far.
