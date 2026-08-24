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

**`--skill` takes one name and is not repeatable.** It names the pack's *first*
skill. A multi-skill pack is one `new-pack` run plus a directory per additional
skill, each registered by hand in step 4 below — there is no repeat form, and
passing `--skill` twice keeps only the last. `--author` is a bare string
(`--author "Some Team"`), paired with `--author-url`.

### What the two manifests actually contain

You will read both files in step 1 of registration, and they do **not** share a
schema — so here they are rather than a pointer to them.

`plugins/<pack>/.claude-plugin/plugin.json` — eight keys, `skills` an **array**:

```json
{
  "name": "...", "displayName": "...", "version": "...", "description": "...",
  "author": { "name": "...", "url": "..." },
  "repository": "...", "license": "...",
  "skills": ["./skills/"]
}
```

`plugins/<pack>/.codex-plugin/plugin.json` — same identity keys, then three things
Claude's has no equivalent for: `homepage`, `keywords`, and an `interface` block.
`skills` here is a **bare string, not an array** — the one difference that will not
announce itself:

```json
{
  "name": "...", "version": "...", "description": "...",
  "author": { "name": "...", "url": "..." },
  "homepage": "...", "repository": "...", "license": "...",
  "keywords": ["skills", "<pack>", "agents-md"],
  "skills": "./skills/",
  "interface": {
    "displayName": "...", "shortDescription": "...", "longDescription": "...",
    "developerName": "...", "category": "Developer Tools",
    "capabilities": ["Interactive"], "websiteURL": "...",
    "defaultPrompt": ["...", "..."]
  }
}
```

`new-pack` fills every one of these from the template. They are written out here
because the failure mode is editing them later — by hand, from memory of the other
host's shape.

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
- **Step 7 is a chokepoint by design, not an oversight.** A **kit-origin** skill is
  one this repository wrote, as opposed to one carried in from the upstream project
  the kit was extracted from — that is what step 5's `upstream` field records, and
  `upstream = ""` is what makes a skill kit-origin. A pack you author is kit-origin
  by definition, so **step 7 applies to every skill in it.** The `kit-origin` set is
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
that payload.

**Use `-B` for every command that touches this package, not just this one.** Any
import of `lemmi_ai_kit` writes `__pycache__/*.pyc` under `plugins/core/src/` —
which is untracked bytecode inside the payload, exactly what `publish-check`
refuses on. Measured: a bare `python -c "import lemmi_ai_kit"` run from *outside*
the repository still deposited a `.pyc` inside it. So an author who follows steps 1
and 2 without `-B` poisons the check before ever reaching step 3, and the failure
names files they never wrote. `PYTHONDONTWRITEBYTECODE=1` in your shell does the
same job for a whole session.

### Three pack enumerations were hardcoded. All three are now derived.

Measured 2026-08-24 by generating `plugins/rust` and registering it in a throwaway
clone. Two of them failed **by construction** — no correct third pack could satisfy
either — and a third failed more quietly. All three were fixed in `386a507`, so
**you should not need to touch them.** They are kept here because the shape recurs
and the next one will look just like them:

| Was | Failed how |
|---|---|
| `tests/test_plugin.py` asserted a sentinel skill per existing pack | A third pack ships neither, so its author met a red suite for a reason unrelated to their work |
| `tests/test_publish.py` wrote out the payload pair | The very next test in the same file already derived it from `PACKS`, so the literal added no coverage and cost every future pack a red suite |
| `tests/test_readme_counts.py` hand-listed six manifest paths | Quieter and worse: it did not fail a new pack, it silently **stopped checking** one |

The fix in every case was derivation from `PACKS` or from what the marketplaces
declare — the pattern `tests/test_license.py` and `publish.payload_roots()` already
used. **If your pack makes a test fail for a reason that has nothing to do with your
pack, suspect a hardcoded enumeration before you suspect your work.**

With those derived, a generated-and-registered third pack leaves the suite green and
`tests/test_plugin.py` at 7 of 7. **Establish your own baseline before you start** —
run `pytest` on a clean checkout and write the number down — rather than comparing
against a figure printed here, which rots on the next test anyone adds.

## 4. What goes in the pack

The template's example skill is a skeleton with `TODO` markers, and the skeleton
encodes one rule worth repeating: **a core skill must never name a skill in your
pack.** Core routes by role — "the installed coding-conventions skill" — so a
project that installs a different language pack still resolves. This is enforced;
`tests/test_pack_boundaries.py` fails a core asset that hardcodes a pack skill's
name.

The reverse direction is fine. A pack skill may name core skills freely.

### The `SKILL.md` frontmatter contract

`audit-skills` checks these, and §3's `--fail-on major` is what turns them into a
gate. The template's skeleton already satisfies every one; this is the list so a
failure is readable rather than a surprise.

| Rule | Failure if broken |
|---|---|
| Opening **and** closing `---` delimiters | frontmatter unparseable — and the body then loads with *empty* metadata, so `/name` still works while auto-matching dies silently |
| `name` equals the skill's **directory** name | name/directory mismatch |
| `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$` | charset or length violation |
| `description` ≤ **1024** characters | over the per-skill spec cap; rejected |
| `description` + `when_to_use` ≤ **1536** | over the listing cap — silently truncated in the menu, which is why it is checked |
| `metadata.type` ∈ `reference · review · task · workflow` | missing or unknown type |
| `SKILL.md` ≤ **500** lines | past this, detail belongs in `references/` |

### A profile is not a pack, and the mapping is one-to-many

Step 3 of registration asks for a **profile**, which is easy to read as a synonym
for the pack. It is not. A profile groups skills by *what they are for*; a pack is
what ships them. `core` ships **four** profiles — `core`, `skill-authoring`,
`research`, `orchestration` — while `python` ships one.

For a new pack the practical rule is the simple case: **add one profile named
after your pack, and map it to your pack** in `pack_for_profile()`. Anything that
does not map explicitly falls through to `core`, so a profile you add without
touching that function silently files your skills under the core pack — and the
suite will not tell you, because both halves are individually consistent.

Keep the axis to **language, and only language** — not a framework, not a team,
not a domain. That is CONTRIBUTING.md's rule and it is the question to settle in
the issue, before any of the above.
