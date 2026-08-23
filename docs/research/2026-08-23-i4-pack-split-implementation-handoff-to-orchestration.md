# I4 pack split implementation handoff to orchestration

**Dated:** 2026-08-23, after implementation verification.
**Status:** split is implemented in the current worktree and verified. No commit was made.
**Scope of this session:** finish and verify the Codex/Claude plugin split for
`lemmi-ai-kit`; do not redesign the layout; do not touch unrelated untracked files.

This record supersedes the packaging-layout uncertainty from the earlier I4 planning handoff:
Codex was tested with a fresh isolated `CODEX_HOME`, and both subdirectory plugins installed
with their skills physically materialized.

## Human summary

The current tree has the desired two-pack shape:

| Pack | Plugin root | Skills | Support code |
|---|---|---:|---|
| core | `plugins/core` | 35 | `plugins/core/src/lemmi_ai_kit` |
| python | `plugins/python` | 2 | none |

Root plugin manifests are intentionally gone:

- `.codex-plugin/plugin.json` - absent
- `.claude-plugin/plugin.json` - absent

Marketplace files remain at the repo root and list exactly two plugins:

- `lemmi-ai-kit-core`, source path `./plugins/core`
- `lemmi-ai-kit-python`, source path `./plugins/python`

The old `src/lemmi_ai_kit` tree has been moved under `plugins/core/src/lemmi_ai_kit`.
`pyproject.toml` now points Hatch, Ruff, and basedpyright at `plugins/core/src`.

## Split behavior verified

Two direct manifest probes passed:

| View | Result |
|---|---|
| Full checkout | `load_manifest()` sees 37 skills across `core,python` |
| Isolated copied core payload | `load_manifest()` sees 35 skills, `core` only, and no Python skills |

Rendered invocation names are pack namespaced:

- user-invocable core skills render as `/lemmi-ai-kit-core:<skill>`
- user-invocable Python skills render as `/lemmi-ai-kit-python:<skill>` when applicable

The CLI audit fallback audits bundled pack roots in this checkout:

- `plugins/core/skills`
- `plugins/python/skills`

## Codex install probe

Fresh isolated home used:

```text
%TEMP%\codex-home-lemmi-split-d22f5d99bef44525a03c8bdc915150dd
```

Codex version:

```text
codex-cli 0.149.0-alpha.4.1
```

Commands run under that isolated `CODEX_HOME`:

```powershell
codex --version
codex plugin marketplace add . --json
codex plugin list --available --json
codex plugin add lemmi-ai-kit-core@lemmi --json
codex plugin add lemmi-ai-kit-python@lemmi --json
codex plugin list --json
Get-ChildItem -LiteralPath $codexHome -Recurse -Filter SKILL.md
Get-ChildItem -LiteralPath $codexHome -Recurse -Directory |
  Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
  ForEach-Object { $_.Name } |
  Sort-Object
```

Result:

- `lemmi-ai-kit-core@lemmi` installed and enabled
- `lemmi-ai-kit-python@lemmi` installed and enabled
- 37 `SKILL.md` files materialized
- Required example skills present:
  - `kit-setup`
  - `analyze-logs`
  - `plan-critic`
  - `initiative-planner`
  - `python-conventions`
  - `test-conventions`

Codex emitted a non-failing warning about refusing to create PATH aliases under a temporary
`CODEX_HOME`. Plugin installation and skill materialization still succeeded.

## Verification gates

All requested gates passed:

```text
uv run ruff format --check .       -> 18 files already formatted
uv run ruff check .                -> All checks passed!
uv run basedpyright                -> 0 errors, 0 warnings, 0 notes
uv run pytest --basetemp <temp>    -> 190 passed, 5 skipped
uv run python -m lemmi_ai_kit audit-skills --fail-on major
                                    -> 0 finding(s)
```

Pytest basetemp used:

```text
%TEMP%\lemmi-ai-kit-pytest-a6a5b9d214b24c53898c496ac61d427f
```

Pytest emitted one non-failing warning: `.pytest_cache` could not be written because access
was denied. The requested external `--basetemp` was used, and the suite passed.

The skill audit reported both bundled pack roots:

```text
skill fleet audit: plugins/core/skills, plugins/python/skills
0 finding(s). Findings are review input, not failures.
```

## Stale-reference sweep

Sweep targets requested by the operator all returned no matches:

- old root invocation: `/lemmi-ai-kit:`
- old install name: `lemmi-ai-kit@lemmi`
- old skills tree: `src/lemmi_ai_kit/assets/skills`
- manifest/source references pointing to `./src`

No intentional historical references needed to be preserved for those exact patterns.

## Cleanup performed

Removed generated artifacts from verification:

- `.uv-cache`
- isolated Codex home:
  `%TEMP%\codex-home-lemmi-split-d22f5d99bef44525a03c8bdc915150dd`
- pytest basetemp:
  `%TEMP%\lemmi-ai-kit-pytest-a6a5b9d214b24c53898c496ac61d427f`
- discovered `__pycache__` directories

While removing `__pycache__`, PowerShell hit access denial traversing `.pytest_cache`. That
directory was not part of the requested cleanup target except as the source of the pytest
warning above.

## Worktree and untouched files

No commit was made.

The worktree already contained the split implementation when verification started. This
handoff file is an additional untracked artifact unless the operator chooses to add it.

Deliberately left untouched:

- `docs/research/2026-08-23-w-window-paid.md` - unrelated untracked file from another session
- unrelated dirty files already present in the split worktree

The final `git status --short` still showed the expected broad restructure:

- modified marketplace files, docs, tests, and `pyproject.toml`
- deleted root manifests and old `src/lemmi_ai_kit/...` paths
- untracked `plugins/`
- untracked `tests/test_pack_boundaries.py`
- untracked `docs/research/2026-08-23-w-window-paid.md`

## Recommendation to orchestration

Next orchestration session should not re-plan the layout. The layout has crossed the important
payload/materialization uncertainty and the requested verification gates are green.

Recommended sequence:

1. Review the final diff with rename detection, especially `pyproject.toml`, marketplace files,
   `plugins/core`, `plugins/python`, `README.md`, and tests.
2. Keep `docs/research/2026-08-23-w-window-paid.md` out of the split commit unless the operator
   explicitly says it belongs.
3. Decide whether to include this handoff in the commit. It is useful evidence, but it is a
   process artifact rather than code required by the split.
4. Commit the split as one coherent change. Suggested message:
   `Split lemmi-ai-kit into core and python plugin packs`
5. After commit, optionally run one clean-clone install probe before push. The isolated Codex
   probe in this session already verified the payload behavior that mattered most.

