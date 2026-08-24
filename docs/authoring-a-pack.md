# Authoring a pack

A **pack** is a plugin: its own directory under `plugins/`, its own manifest for
each host, its own `skills/` tree. `core` and `python` are both packs, so a third
follows a shape that already exists.

This document is the **mechanics** — the command, the files, the verification.
Two policy questions are settled elsewhere and are not restated here, because a
rule written down twice drifts:

- **Should this be a pack at all?** Almost always no.
  [You probably do not need to author a pack](adoption-guide.md#2-you-probably-do-not-need-to-author-a-pack).
  Most people reaching for one want a `### Project rules` section in their own
  repository, which costs nothing and ships nothing.
- **Naming, authorship, and what a merge does and does not certify.**
  [CONTRIBUTING.md, Contributing a pack](../CONTRIBUTING.md#contributing-a-pack).
  Open a pack-contribution issue before writing one.

## 1. Scaffold it

```sh
uv run python -m lemmi_ai_kit new-pack rust --skill rust-conventions
```

Three files, in `plugins/rust/`:

```
plugins/rust/.claude-plugin/plugin.json
plugins/rust/.codex-plugin/plugin.json
plugins/rust/skills/rust-conventions/SKILL.md
```

Add `--dry-run` to see that list without writing it. `--help` shows the rest;
the two that matter are `--plugin-name` and `--author`, and **a pack this
repository's owner did not write needs both** — the plugin name and the `author`
field are the only provenance an adopter has, per CONTRIBUTING.md.

Everything else is derived from `pyproject.toml`: version, repository, license,
and the author when you do not override it. Those are derived rather than asked
for because the suite asserts each of them against `pyproject.toml` or `LICENSE`,
so a value typed into the template would be a test failure waiting on the next
release bump. The full placeholder table is in
[`plugins/_template/README.md`](../plugins/_template/README.md).

## 2. Register it — seven edits `new-pack` does not make

The command prints this list and performs none of it. That is deliberate: adding
a plugin to a published marketplace listing is a decision somebody reviews, not a
side effect of scaffolding. **A pack is not real until all seven are done**; until
then it is a directory the tooling cannot see.

| # | File | What to add |
|---|---|---|
| 1 | `.claude-plugin/marketplace.json` | an entry with `"source": "./plugins/<pack>"` — a bare string |
| 2 | `.agents/plugins/marketplace.json` | the same pack with `"source": {"source": "local", "path": "./plugins/<pack>"}`, plus `policy` and `category` |
| 3 | `plugins/core/src/lemmi_ai_kit/manifest.py` | the pack name in `Pack`, `PACKS` and `PACK_PLUGIN_NAMES`; the pack's **profile** in `PROFILES`; and that profile mapped in `pack_for_profile()` |
| 4 | `plugins/core/src/lemmi_ai_kit/assets/manifest.toml` | one `[[skills]]` entry per skill, with the profile from step 3 |
| 5 | `docs/upstream-sync.toml` | one row per skill, **sorted by name**, each with an explicit `upstream` (`""` when there is no counterpart) |
| 6 | `README.md` | the skill counts |
| 7 | `tests/test_upstream_sync.py` | only for a `kit-origin` skill: one line in the pinned set |

Three of these have a trap that costs a debugging cycle if you meet it cold, and
each was met while writing this document rather than imagined:

- **Step 3 is five edits, not four.** `PROFILES` is separate from `PACKS`, and a
  profile missing from it makes `load_manifest()` reject the skill entry you just
  added in step 4 — with an error about the profile, not about the pack.
- **Step 5's rows must be sorted**, and `upstream` is required rather than
  optional. The record refuses an unsorted table on the grounds that it makes
  every future diff unreviewable, and refuses a missing `upstream` because an
  absent field cannot be told from an unanswered question.
- **Step 7 is a chokepoint by design, not an oversight.** The `kit-origin` set is
  pinned as a literal so that a future edit quietly flipping a direction has to
  argue with a test. A genuinely new kit-origin skill costs one deliberate line.

The registration files are the reason there is no `--register` flag. Each is a
place a reviewer looks; automating them would move the decision to the moment
somebody was scaffolding rather than the moment somebody was reviewing.

## 3. Verify it

```sh
uv run pytest
uv run python -m lemmi_ai_kit audit-skills --fail-on major
uv run python -B -m lemmi_ai_kit publish-check
```

`pytest` is the check that matters — it is what tells you the pack is real rather
than merely present. `audit-skills` holds the new skills to the fleet's rules
(frontmatter, the 500-line cap, resolvable links). `publish-check` refuses while
the payload carries anything git does not track, and your new pack is now part of
that payload; the `-B` is load-bearing, since without it the command writes
bytecode into the very tree it is measuring.

### Two tests fail for every third pack, for reasons unrelated to your pack

Measured 2026-08-24 by generating `plugins/rust` and registering it in a
throwaway clone. **Both are hardcoded pack enumerations, and both fail by
construction — no correct pack can satisfy either.** They are recorded here
rather than fixed because they belong to another owner; fix them in the same pull
request as the third pack, and the fix is derivation in both cases.

**`tests/test_plugin.py:54`**

```python
assert (root / "kit-setup").is_dir() or (root / "python-conventions").is_dir()
```

One sentinel skill per existing pack. A third pack ships neither. What it is
actually asserting is that the skills path is not an empty directory, which is
derivable: any pack must ship at least one subdirectory holding a `SKILL.md`.

**`tests/test_publish.py:522`**

```python
assert report.payload == ("plugins/core", "plugins/python")
```

The pair written out. The very next test in the same file already derives that
set as `tuple(sorted(f"plugins/{pack}" for pack in PACKS))`, and says in its own
docstring that adding a pack must not need an edit there — so the hardcoded copy
above it adds no coverage and costs every future pack a red suite.

With those two derived, a generated-and-registered third pack takes the suite to
**249 passed / 6 skipped**, `tests/test_plugin.py` 7 of 7.

A third instance of the same shape survives in `tests/test_readme_counts.py:78`,
which hand-enumerates six manifest paths. It does not fail a new pack — it does
something quieter, which is to stop checking one. `tests/test_license.py` had the
identical defect and now derives its set from
`publish.payload_roots()`; that is the pattern to copy.

## 4. What goes in the pack

The template's example skill is a skeleton with `TODO` markers, and the skeleton
encodes one rule worth repeating: **a core skill must never name a skill in your
pack.** Core routes by role — "the installed coding-conventions skill" — so a
project that installs a different language pack still resolves. This is enforced;
`tests/test_pack_boundaries.py` fails a core asset that hardcodes a pack skill's
name.

The reverse direction is fine. A pack skill may name core skills freely.

Keep the axis to **language, and only language** — not a framework, not a team,
not a domain. That is CONTRIBUTING.md's rule and it is the question to settle in
the issue, before any of the above.
