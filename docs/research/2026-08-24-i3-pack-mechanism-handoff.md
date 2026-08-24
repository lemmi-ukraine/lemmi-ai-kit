# I-3 (I4 slice): the pack-authoring mechanism — landed, with two blockers recorded

**2026-08-24.** Slice `I-3` of `.specs/i4-pack-split/execution-plan.md`, deliverables
D14–D17. Baseline `b2931d2`, 227 passed / 6 skipped. Ends at `d5cc088`,
**249 passed / 6 skipped**, `audit-skills --fail-on major` 0 findings, ruff / ruff format
/ basedpyright clean.

Five commits, all inside the declared path set:

| Commit | What |
|---|---|
| `aa574ed` | D14 `plugins/_template/` + D15 `new-pack` + 16 tests |
| `df2b173` | D16 `kit-setup` pack awareness, the `### Project rules` seam, the diagram node |
| `5a7b028` | `tests/test_license.py` derived, with a measured positive control |
| `4974232` | `new-pack --author` / `--author-url` |
| `d5cc088` | D17 `docs/authoring-a-pack.md` + two checklist corrections |

## 1. The discriminator: the round trip, and what it found

**Result: 249 passed / 6 skipped in a throwaway clone carrying a third pack,
`tests/test_plugin.py` 7 of 7.**

Method, because a round trip described is not a round trip run. `git clone` of this
checkout at `4974232`; `new-pack rust --skill rust-conventions --repo <clone>`; the
registration checklist executed **in the clone only**; then the full suite there, driven
by this repo's venv with `PYTHONPATH` aimed at the clone's package. The editable install
is a plain `.pth` path entry rather than a meta-path finder, so `PYTHONPATH` wins — verified
by printing `lemmi_ai_kit.__file__` before trusting the run.

It took four iterations, and every one of them was a real finding rather than a fixture
mistake:

| Iteration | Failure | What it actually was |
|---|---|---|
| 1 | `test_pack_plugin_json_paths_resolve` | **Blocker A** below — hardcoded sentinel skill |
| 2 | 11 × `test_upstream_sync` | `PROFILES` missing the new profile; the checklist did not say to edit it |
| 3 | `upstream` required, rows must be sorted | two sync-record rules the checklist did not say |
| 4 | `test_this_checkout_is_measurable` | **Blocker B** below — hardcoded payload pair |

Both checklist gaps are now printed by `new-pack` (`d5cc088`) and are in
`docs/authoring-a-pack.md` §2 with the error each produces.

## 2. Two tests fail every third pack by construction — NOT FIXED, not mine

Both are hardcoded pack enumerations. No correct pack can satisfy either, and neither
belongs to this slice's path set. The clone-only patches that made the suite green are
recorded here and in `docs/authoring-a-pack.md` §3; both are one-line derivations.

**Blocker A — `tests/test_plugin.py:54`**

```python
assert (root / "kit-setup").is_dir() or (root / "python-conventions").is_dir()
```

One sentinel skill per *existing* pack. The claim it is reaching for is "the skills path
is not an empty directory", which derives: any pack must ship at least one subdirectory
holding a `SKILL.md`.

**Blocker B — `tests/test_publish.py:522`**

```python
assert report.payload == ("plugins/core", "plugins/python")
```

The very next test in that file, `test_the_payload_matches_what_the_marketplaces_declare`,
already derives the identical set as `tuple(sorted(f"plugins/{pack}" for pack in PACKS))`
and its docstring says adding a pack must not need an edit there. The hardcoded copy adds
no coverage and costs every future pack a red suite.

**One deliberate chokepoint, not a defect.** `tests/test_upstream_sync.py:101` pins the
`kit-origin` set as a literal, documented as costing one line per genuinely new kit-origin
skill so that a direction flip has to argue with a test. It is the seventh registration
step in the guide, described as intended rather than filed as friction.

**A third instance of the same shape survives: `tests/test_readme_counts.py:78`** —
six manifest paths hand-enumerated. It does not fail a new pack; it does the quieter
thing and silently stops checking one. `tests/test_license.py` had the identical defect
and now derives from `publish.payload_roots()`.

## 3. Per deliverable

### D14 — `plugins/_template/`

Four files: both `plugin.json` manifests, one example skill at
`skills/example-skill/SKILL.md`, and a `README.md` that `new-pack` deliberately does not
copy.

**The trap was checked before the path was created, not after.** `load_manifest()` raises
on a skill directory under a pack with no manifest entry, and the template ships exactly
such a directory. It is safe only because every pack enumeration in the repo iterates the
`PACKS` literal instead of globbing `plugins/*` — `shipped_skill_dirs()`,
`available_packs()`, `test_plugin.py`, `test_assets.py`, and the `audit-skills` fallback,
all read before writing anything. `grep -rn "glob(\|iterdir()\|rglob(" tests/ plugins/core/src/`
returned nine sites and none of them globs `plugins/*`. `test_the_template_is_invisible_to_every_pack_enumeration`
now pins that invariant, because one `glob` anywhere would end it silently.

Two consequences worth carrying: the template is **inside** the shipped-surface scan of
`test_repo_path_references.py` (anything under `plugins/`), which is why it must use
`${...PLUGIN_ROOT}/` anchoring — accidentally the correct rule for a template whose output
lands in a payload. And it is inside `test_publication_hygiene.py`'s scan, since
`_ALREADY_COVERED` names only `assets/` and the two live skills trees. Real file suffixes
were kept rather than `.tmpl` for exactly that reason: `.tmpl` is not in `_TEXT_SUFFIXES`,
so it would have removed the template from both scans.

### D15 — `new-pack`

In `cli.py`, not a new module, to stay inside the declared path set.

Version, repository and license are derived from `pyproject.toml`; the author defaults
there and is overridable. That split is not aesthetic: `test_plugin.py` asserts version and
repository against `pyproject.toml` and `test_license.py` asserts license against `LICENSE`,
so a flag for those would only let somebody generate a pack that fails — while CONTRIBUTING.md
makes `author` a *provenance label*, so a non-overridable author would mislabel every
contributed pack on the path of least resistance (`4974232`).

Renders every file before writing any, so an unfilled placeholder fails with no pack on
disk. Refuses an existing pack, six name shapes, and a template that cannot produce a valid
pack. The registration checklist derives the marketplace pair from
`publish.MARKETPLACE_MANIFESTS` and the two package-internal paths from `Path(__file__)` and
`assets_root()` — the latter because `cli.py` ships inside a payload where a `plugins/<pack>/`
prefix resolves to nothing, so writing it as a literal is what
`test_repo_path_references.py` exists to reject.

18 tests. Three positive controls: an unfilled `{{KEY}}` refused by name with no partial
pack left behind, a template missing `.codex-plugin/plugin.json` refused as a broken
skeleton, and six invalid names refused at the argument. The leading-hyphen case needs
`--repo` before `--`, or argparse claims the name as an option and the case passes for the
wrong reason.

### D16 — `kit-setup`

Measured start: **zero** pack awareness (126 lines; of six "pack" hits, two rendered the
CLAUDE.md namespace and four were substrings of `package.json`), and zero questions asked
(`grep -c "?"` → 0, against 7 / 11 / 17 for `spec-driven-dev` / `plan-critic` /
`product-brief`). All verified before writing.

Per OQ-I4-5, ratified: **detect and recommend, never install**, with the four grounds
stated in the skill rather than cited to a document its reader cannot open.

**The host discriminator trap, and why the fix is not the line it looks like.** The old
`PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT}}"` is correct for resolving a path and
wrong as a host test, because Codex sets both variables. Step 0 now tests `PLUGIN_ROOT`
first *and* assigns the resolved root to `KIT_PLUGIN_ROOT` — the old spelling clobbered the
discriminator's own input, so anything reading it later in the same shell would have said
Codex regardless. `[A-Z_]*PLUGIN_ROOT` in the path guard's regex already admits the new
name.

New `references/packs-and-hosts.md` carries the catalogue, both clients' commands, and the
`.` versus `./` asymmetry (Claude Code rejects a bare `.` with *Invalid marketplace source
format*). It says to update its own table when a pack lands, because a pack absent there is
a pack the skill never recommends. 200 lines against the 500-line cap; two questions, both
load-bearing for the recommendation. **The rest of the missing interview half is still
missing and was not built** — it remains a roadmap candidate with no charter.

`### Project rules` in `templates/AGENTS.md` is no longer one of the four `TODO(project)`
stubs (three remain, all genuine project facts). It now states what belongs there, the three
near-misses that belong elsewhere, the rule that a rule carries its reason, both routes in,
and an explicit empty state.

The Pipeline Overview diagram gained its missing `test-planner` node. Columns were rebuilt
by arithmetic from the existing ones rather than retyped — nothing tests an ASCII diagram.

### D17 — `docs/authoring-a-pack.md`

Mechanics only. Policy is linked, not restated: the adoption guide owns "should this be a
pack at all", CONTRIBUTING.md owns naming, authorship and what a merge does not certify —
and it already links back here for exactly these mechanics. Every command in it was run once
before it was written, including the `-B` on `publish-check`, which is not decoration: the
plain form writes bytecode into the tree it measures, reproduced this session (2 `.pyc`
under the payload, cleared).

## 4. Also carried

`tests/test_license.py` hand-enumerated four pack manifest paths; `new-pack` makes a fifth
one command away. Now derived from `publish.payload_roots()`. **Measured against a throwaway
copy with a wrong-licensed `plugins/rust` added to the Claude marketplace:** two mismatches
caught and named, and `would the OLD hardcoded list have seen it? False`. Four controls,
including one asserting that a payload advertised with no readable manifest **fails** rather
than being skipped — a skipped payload renders as a pass.

## 5. Open for whoever takes this next

1. **Blockers A and B** above. Two one-line derivations, in files this slice does not own.
   They should land in the same pull request as the first third pack, or that pack's author
   meets a red suite with no idea why.
2. **`tests/test_readme_counts.py:78`** — same shape, quieter failure mode.
3. **`kit-setup`'s interview half** — still unbuilt, still uncharted.
4. **`.` versus `./` is documented from one measurement per client on one machine.** The
   asymmetry is real and recorded; the version floor under it is not known.
