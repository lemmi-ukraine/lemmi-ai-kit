# `plugins/_template` — the pack skeleton, not a pack

This directory is the input to `new-pack`. It is **not installable and never
ships**: the two marketplace manifests decide what a plugin install copies, and
neither lists `_template`. That is also why the underscore is in the name — the
directory sorts away from the real packs and reads as "not one of them" to a
human scanning `plugins/`.

Nothing in the test suite mistakes it for a pack either, and that is by
construction rather than by luck. Every enumeration of packs in this repo —
`shipped_skill_dirs()`, `available_packs()`, `test_plugin.py`, `test_assets.py`,
the `audit-skills` fallback — iterates the `PACKS` tuple in `manifest.py`, a
literal. None of them globs `plugins/*`. A skill directory here is therefore
invisible to `load_manifest()`, which would otherwise raise on an unlisted skill
dir and redden the whole suite.

## Using it

```bash
uv run python -m lemmi_ai_kit new-pack <pack> --skill <skill-name>
```

That copies this tree to `plugins/<pack>/`, substitutes the placeholders below,
renames `skills/example-skill/` to the skill name you gave, and prints the
registration steps it deliberately does not perform. See
[docs/authoring-a-pack.md](../../docs/authoring-a-pack.md) for the whole path
from empty directory to green suite.

This file is the only one `new-pack` does not copy: it documents the template,
not the pack.

## Placeholders

`{{NAME}}` anywhere in a text file is substituted. Every key must resolve —
`new-pack` refuses to write a file that still contains `{{`, so a typo fails
loudly instead of shipping a literal brace into a marketplace listing.

| Placeholder | Source | Example |
|---|---|---|
| `{{PACK}}` | the `new-pack` argument | `rust` |
| `{{SKILL_NAME}}` | `--skill`, default `<pack>-conventions` | `rust-conventions` |
| `{{PLUGIN_NAME}}` | `--plugin-name`, default `lemmi-ai-kit-<pack>` | `lemmi-ai-kit-rust` |
| `{{DISPLAY_NAME}}` | `--display-name`, default derived from the plugin name | `Lemmi AI Kit Rust` |
| `{{DESCRIPTION}}` | `--description` | `Rust conventions for projects using Lemmi AI Kit Core.` |
| `{{VERSION}}` | `pyproject.toml` `project.version` | `0.1.0` |
| `{{REPOSITORY}}` | `pyproject.toml` `project.urls.Repository` | — |
| `{{LICENSE}}` | `pyproject.toml` `project.license` | `MIT` |
| `{{AUTHOR_NAME}}` | `pyproject.toml` `project.authors[0].name` | — |
| `{{AUTHOR_URL}}` | `{{REPOSITORY}}` with its last path segment dropped | — |

The last five are **derived, not asked**. `test_plugin.py` asserts every pack's
version and repository against `pyproject.toml`, and `test_license.py` asserts
its license against the `LICENSE` file — so a hand-typed value here would be a
test failure waiting on the next release bump, and the generated pack is correct
in a fork without anyone editing this template.

## Editing the template

Changes here reach every pack authored afterwards and none authored before.
Verify with a round trip rather than by reading:

```bash
uv run pytest tests/test_cli.py -q
```

`tests/test_cli.py` generates a pack from **this** directory — not from a fixture
copy — and asserts the result against the same contract `test_plugin.py` applies
to `core` and `python`, plus a clean `audit-skills` run. Break the template and
that test goes red before any pack is authored from it.
