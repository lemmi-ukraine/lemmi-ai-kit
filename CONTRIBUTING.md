# Contributing to lemmi-ai-kit

Thanks for considering a contribution. This kit is a plugin of skills — mostly
markdown, with a small Python support package — so most contributions are prose,
and the review bar is about accuracy and portability rather than cleverness.

- **Maintainer / reviewer:** support@lemmi.io
- **Security issues:** do not open a public issue — see [SECURITY.md](SECURITY.md)
- **Conduct concerns:** see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Licensing of contributions

This project is [MIT licensed](LICENSE). By opening a pull request you agree
that your contribution is licensed under the same terms — inbound equals
outbound. There is no CLA to sign and no `Signed-off-by` trailer to remember.

## Reporting an issue

Open one of the three forms under
[`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE):

| Use | When |
|---|---|
| **Bug report** | A skill misbehaves, `kit-setup` scaffolds something wrong, the CLI errors, an install command fails |
| **Skill request** | You want a skill the kit does not have |
| **Pack contribution** | You want to contribute a language- or domain-specific pack |

The forms ask for structured fields because "it didn't work" reports cost more
to triage than they carry. The one field that matters most is what you ran and
what you expected — a skill behaving differently from its own SKILL.md is a
much clearer bug than a skill behaving differently from your expectation.

## Setting up

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/lemmi-ukraine/lemmi-ai-kit
cd lemmi-ai-kit
uv sync --dev
```

## The four checks

CI runs exactly these four, in this order, on every pull request — there is no
`branches:` filter on the `pull_request` trigger, so your PR gets the full job
whatever it is based on. Run them locally first:

```bash
uv run ruff check .            # lint
uv run ruff format --check .   # formatting
uv run basedpyright            # types, strict mode
uv run pytest                  # tests
```

`ruff format .` (without `--check`) fixes formatting in place. `basedpyright`
runs in strict mode over `src/` and `tests/` only — the asset tree is excluded,
since it is prose, not code.

## The hygiene contract — why a prose-only PR can fail CI

`tests/test_assets.py` is the permanent enforcement of one promise: **assets must
work in a brand-new project on any machine.** It is the most common reason an
otherwise-good skill PR goes red, so it is worth knowing before you write.

**1. No contamination.** Nine patterns are rejected anywhere under
`src/lemmi_ai_kit/assets/`:

| Rejected | Why |
|---|---|
| `/Users/…`, `/home/…`, a Windows drive-letter path | An absolute path works for exactly one person |
| `Windows host`, `PYTHONIOENCODING` | Machine-specific workarounds |
| `lemmi-ai-api` | A reference to the private source project nobody else can read |
| A dated `learnings.md` or `retrospectives/` citation | Points at history that does not ship |
| `.ai/backups/` | Source-project state |

Derive paths at runtime instead: relative to the referring file, repo-root
relative, `${CLAUDE_SKILL_DIR}`, or `Path(__file__)`. There is a small
allowlist in that file for the handful of documents that *teach* the rule and so
must quote the patterns it bans — keep it that way; adding yourself to the
allowlist to get green is not a fix.

**2. Every skill needs valid frontmatter.** `SKILL.md` must open with a YAML
block whose `name:` matches the skill's directory and its manifest entry exactly,
and it must have a `description:`.

**3. Relative references must resolve.** Any `references/…`, `assets/…` or
`scripts/…` link in a `SKILL.md` must point at a file that ships. Links inside
fenced code blocks are exempt, because skills that teach skill-authoring show
illustrative examples there.

**4. `.ai/` state files ship empty.** `learnings.md`, `ai-changelog.md` and
`improvement-hypotheses.md` ship as headers with no dated entries — a new project
starts at zero.

**Scope, stated precisely.** The four checks above cover
`src/lemmi_ai_kit/assets/` — the tree that ships to your project. A **second** check
in `tests/test_publication_hygiene.py` applies the same nine patterns to every
*tracked* file outside that tree: docs, community files, config, this file. It
imports the patterns from `test_assets.py` rather than restating them, so the two
scans cannot drift apart, and it has its own small allowlist for documents that exist
to teach the rule.

So **a docs-only PR can go red**, and the message names which contract you tripped.
The rule of thumb: a tracked file is a published file, so an absolute path or a
private-project reference is a problem wherever you put it — not only under
`assets/`.

## Adding a skill

1. Create `src/lemmi_ai_kit/assets/skills/<name>/SKILL.md` with frontmatter whose
   `name:` is `<name>`. Put anything long in `references/` and link to it, rather
   than growing one file — the loader reads `SKILL.md` first and follows links
   only when needed.
2. Register it in `src/lemmi_ai_kit/assets/manifest.toml` with a `name`,
   `profile`, `invocation` and `summary`. All four are validated.
   - `profile` must be one of the values in `PROFILES` in
     [`src/lemmi_ai_kit/manifest.py`](src/lemmi_ai_kit/manifest.py) — a closed
     tuple. Read it rather than guessing; the set changes. It is validated, so a
     wrong value fails the suite — but be aware it currently has **no runtime
     effect**: `for_profiles()` has no production call site and the plugin
     packaging ships every skill regardless of profile. Treat it as a label that
     is checked for consistency, not a switch. A planned pack split will give it
     teeth.
   - `invocation` is `user` (a slash command), `auto` (loaded as background
     reference) or `internal` (called by another skill, not by a person).
3. Run `uv run pytest`. `load_manifest()` enforces a bijection between manifest
   entries and asset directories, so a skill that is registered but not shipped —
   or shipped but not registered — fails immediately, with both lists named.
4. Do not hand-write a skill count anywhere. `uv run python -m lemmi_ai_kit list`
   prints the catalog from the manifest.

## Contributing a language or domain pack

**This path is not open yet.** The repo currently ships one plugin from one
skills directory; splitting it into a core pack plus sibling language packs, and
defining how an external pack registers itself, is planned but not built. Until
it lands, open a **pack contribution** issue describing the pack you want to add
and what it would contain. That is genuinely useful now — the shape of the first
few requests is what the authoring path gets designed against.

## Review expectations

- **Reviewer:** support@lemmi.io. One maintainer, so expect days rather than
  hours.
- **What review looks for**, in this order: does it work in a fresh repo on
  another OS; does the skill's own description match what it actually does; is it
  scoped to one job; does it duplicate a skill that already exists.
- **Are the commands it tells an agent to run safe?** This is a first-class review
  criterion, not a footnote, because a skill is instructions an agent executes and
  there is no sandbox between it and your working tree — see
  [SECURITY.md](SECURITY.md#threat-model--read-this-part). Review reads every
  command a skill instructs, every script it ships, and every path it writes to,
  and asks what a careless reading of the instruction would do. Destructive
  commands, network calls the skill does not document, and writes outside a
  declared target are all rejected regardless of how good the rest is.
- **Prose gets read closely.** In a skills pack the prose *is* the product, so
  expect line-level comments on wording. That is not nitpicking — a skill is
  instructions a model follows literally.
- **Green CI is necessary, not sufficient.** The four checks catch portability
  and structure. They cannot tell whether a skill's advice is correct.
