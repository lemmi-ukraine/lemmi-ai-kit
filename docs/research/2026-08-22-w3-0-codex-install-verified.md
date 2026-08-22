# Session handoff — I4 W3.0: the Codex `source.path` defect is REFUTED

**Dated:** 2026-08-22, at session close. **Executed:** I4 W3.0 (the empirical check only).
**Not started:** the pack split (W3.1+), the rename. **Branch:** `pre-flip`. **Nothing is pushed.**

**Headline: `"path": "./"` installs fine. F4 and install-blocker 3 are not defects.** The claim that
the Codex plugin "does not install today" was read off vendor docs, never run. It was run. It
installs. The charter's prescribed fix, applied today, is what would break it.

---

## 1. What was run, and what it returned

`codex` was absent from this environment — the reason two prior sessions could only reason from docs.
Obtained as `codex-cli 0.149.0` (`npm install @openai/codex@0.149.0` into a scratch dir, **not**
globally, not into the repo). `CODEX_HOME` redirected to scratch for every run, so the operator's
real `~/.codex` was never written — verified after the fact: `config.toml` mtime unchanged
(2026-08-13), zero `marketplace` keys.

Marketplace source was a **local directory path**: no network, no auth, and therefore no
authentication failure to be mistaken for success. This was the instructed method and it is the right
one — it exercises the schema rather than the transport.

```
$ codex plugin marketplace add <repo>
  Added marketplace `lemmi`.  Installed marketplace root: <repo>                      exit 0
$ codex plugin add lemmi-ai-kit@lemmi
  Added plugin `lemmi-ai-kit`.  Installed plugin root: .../lemmi-ai-kit/0.1.0         exit 0
$ codex plugin list
  lemmi-ai-kit@lemmi   installed, enabled   0.1.0
```

**The install is real, not a registration stub.** 33 skill directories materialized under the
declared skills path, and version `0.1.0` was parsed out of `./.codex-plugin/plugin.json` — which is
the decisive fact: the manifest sitting at `source.path == "./"` **was discovered and read**.

## 2. The mechanism — four fixtures, because one success proves less than a matrix

| | `source.path` | manifest location | result |
|---|---|---|---|
| A | `"./"` | at root | **installs**, version `0.1.0` |
| B | `"./plugins/core"` | at `plugins/core/` | **installs**, version `0.1.0` |
| C | `"./"` | absent entirely | installs, version silently degrades to `"local"` — no error |
| D | `"./plugins/core"` | only at root | **hard error, nonzero:** `plugin source path is not a directory` |

Codex is indifferent to root-versus-subdirectory. It enforces two things: that
`<marketplace root>/<source.path>` **exists as a directory** (D), and it reads the manifest at
`<source.path>/.codex-plugin/plugin.json` (C — a missing manifest is not rejected, it just loses the
version). `"./"` satisfies both, because `.codex-plugin/plugin.json` sits at the repo root today.

Row C is worth keeping: Codex will accept a plugin with no manifest at all and report it as
installed. Any future check that treats "install succeeded" as "manifest is valid" is unsound.

## 3. Do not apply the fix the charter prescribes. It is the bug.

> Fixture **D is the prescribed fix.** "Repoint `source.path` at a concrete plugin subdirectory" —
> performed today, before any such subdirectory exists — names a path that is not there and converts
> a **working** install into a hard error.

`source.path` was therefore left at `"./"`, deliberately. The path change is correct only in the
same commit that creates `plugins/<pack>/` — i.e. inside the pack split (W3.1+), never ahead of it.
`.codex-plugin/plugin.json` needed no change either.

This is the second trap in the same neighbourhood. The prior handoff (§4, P0) had already spotted the
first: that a manifest-only fix goes red on the test and *reads* as though the fix were wrong. Correct
— and the deeper problem is that the manifest change is itself wrong until the directory exists.

## 4. What changed in the tree

One file, uncommitted: `tests/test_plugin.py`.

`test_codex_marketplace_lists_the_plugin_at_repo_root` became
`test_codex_marketplace_source_path_resolves_to_a_plugin_dir`. The `assert source["path"] == "./"` is
**gone** — it locked in a shape Codex never demanded, so CI was defending a non-bug. Deleting it
outright would have left nothing defending the constraint that *does* exist, so it was replaced with
the invariant the fixtures established: starts with `./`, contains no `..`, resolves to a real
directory, and has `.codex-plugin/plugin.json` under it.

That formulation is **split-agnostic** — true for `"./"` now and for `"./plugins/core"` after W3.1, so
it will not need revisiting when the split lands. Same shape of fix as F3's "stop hand-writing the
number": assert the derived property, never the literal.

**Verified by deliberate breakage, then restored:** with `source.path` mutated to `./plugins/core`
the new test fails at `tests/test_plugin.py:102` on `is_dir()` — catching exactly the naive fix that
the old equality assertion could never have caught. Restored byte-identical from a backup taken
outside the tree (no git operation was run against this shared checkout).

`uv run pytest` gives **37 passed** on `pre-flip`.

## 5. Scope — what this kills, and what it does not

**Dead:** install-blocker 3 (schema / `source.path`), and the schema half of §2c F4. There is nothing
to fix and nothing to drop from the README on those grounds.

**Still standing, unchanged:** install-blocker 2 (reachability). And note precisely what the README
advertises at line 29:

```
codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit
```

That is the **`owner/repo` git form** — the one transport this work could not exercise. Codex accepts
only `owner/repo`, HTTPS, or SSH as a git source; a local *bare* repo is rejected outright
(`invalid marketplace source format`), so there is no offline path to it. The schema objection to that
command is dead; the command itself remains unexercised end-to-end until the repo is public.

So F4 — *"no advertised install command that cannot work"* — is **discharged on the grounds it was
raised on**, and the residual is the ordinary reachability wait that always cleared at the flip.

**Other limits, stated rather than buried:** the result is specific to codex-cli 0.149.0 on Windows,
and row A was reproduced on the real repo plus a minimal fixture, not across versions.

## 6. Corrections owed to standing documents — none of them mine to make

Three places assert the bug as fact. All are outside this session's file ownership and were left
untouched:

| Where | Says | Should say |
|---|---|---|
| `00-PROGRAM-oss-launch.md` §2c, row F4 (private planning artifact — not committed to this repository) | "open" | refuted; schema half closed, reachability unchanged |
| same, §5b, install-blocker 3 | "Codex requires a concrete plugin subdirectory" | Codex requires the path to resolve to a directory; root qualifies |
| `I4-TECH-pack-split-adoption.md`, Context (private planning artifact — not committed to this repository) | "a live bug, not a planning question" | not a bug; the path move belongs to the split |

One stale reference: [`2026-08-22-session-handoff-to-orchestration.md`](2026-08-22-session-handoff-to-orchestration.md)
§4 cites `tests/test_plugin.py:89` for the offending assertion. That line no longer exists.

## 7. Recommended next actions

**P1 — 30 seconds, on 2026-08-29, and it retires the last of F4.** Once the repo is public, run the
README's own command verbatim — `codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit`, then
install. That closes the git transport this session could not reach. Pair it with the traffic-baseline
capture already scheduled for that date.

**P1 — carry the path change *inside* the split, not before it.** When W3.1 creates `plugins/<pack>/`,
`source.path` moves in the same commit. The test in §4 already enforces the correct invariant, so it
will pass across the move and fail if the directory is missing — which is the guard that was wanted.

**P2 — decide where this session's edit lands.** The `tests/test_plugin.py` change is uncommitted on
`pre-flip`, sharing the working tree with three unrelated modified `docs/research/` files belonging to
I3a. It is a clean single-file commit and depends on nothing else.

**P3 — the bloat argument for the split survives, on its own merits.** With `path: "./"` the plugin
payload is the whole repository: the local install copied `.git`, `.venv`, `tests/`, and the private
planning trees into the plugin cache. Untracked trees would not travel in a git-sourced install, so
this is a size-and-tidiness argument for concrete plugin subdirectories — **not** an install defect,
and it must not be re-imported as one.

## 8. Branch state, measured

`pre-flip` is **22 commits ahead of `main`, fast-forward** (`pre-flip..main` = 0), and **contains
`i3a-contribution-surface`**. It does **not** contain `i1-decouple-prompt-skills`, `f3-stale-counts`,
or `readme-drop-unbacked-refresh-claim`.

Two consequences worth having in writing:

- `pre-flip` is therefore **pre-I1**: 33 skills, and README line 3 still reads "33 skills". That is
  the F3 drift, expected on this branch, not a new defect. The 33 skill dirs the Codex install
  produced are consistent with it.
- The **37** test count above is `pre-flip`'s. The prior handoff's **39** describes the
  `f3 + i3a + readme-drop` merge result. Different trees, not a contradiction.
