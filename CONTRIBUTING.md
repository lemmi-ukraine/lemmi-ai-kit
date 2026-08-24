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
runs in strict mode over `plugins/core/src/` and `tests/` only — the asset tree
and both packs' skills trees are excluded, since they are prose, not code.

## The hygiene contract — why a prose-only PR can fail CI

`tests/test_assets.py` is the permanent enforcement of one promise: **assets must
work in a brand-new project on any machine.** It is the most common reason an
otherwise-good skill PR goes red, so it is worth knowing before you write.

**1. No contamination.** These patterns are rejected anywhere under
`plugins/core/src/lemmi_ai_kit/assets/`:

| Rejected | Why |
|---|---|
| `/Users/…`, `/home/…`, a Windows drive-letter path | An absolute path works for exactly one person |
| `Windows host`, `PYTHONIOENCODING` | Machine-specific workarounds |
| `lemmi-ai-api` | A reference to the private source project nobody else can read |
| A dated `learnings.md` or `retrospectives/` citation | Points at history that does not ship |
| `.ai/backups/` | Source-project state |
| A `.claude/skills/<name>/scripts/…` path | Kit scripts ship inside the plugin, so a project-relative skills path is broken by construction — use `${CLAUDE_SKILL_DIR}/scripts/…` |

The authoritative list is `_FORBIDDEN` in `tests/test_assets.py`; the table above
is a summary of it and can fall behind. Read the tuple if you need to be certain,
and do not trust a count of it written in prose — an earlier revision of this
section said "nine patterns" for as long as there were ten.

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

**Scope, stated precisely.** The checks above cover
`plugins/core/src/lemmi_ai_kit/assets/` — the tree that ships to your project. A
**second** check in `tests/test_publication_hygiene.py` applies the same patterns
to every file outside that tree that git would publish: docs, community files,
config, this file. It imports the patterns from `test_assets.py` rather than
restating them, so the two scans cannot drift apart, and it has its own small
allowlist for documents that exist to teach the rule.

"Everything git would publish" means tracked files **plus untracked files that
are not ignored** — the scan passes `--others --exclude-standard`. That is
deliberate: an unignored scratch file is one `git add .` away from being
committed, and it is cheaper to hear about it now. Ignored files are never
scanned, so that is where scratch belongs.

A third check, `tests/test_repo_path_references.py`, fails on any reference to
the support package that is missing its `plugins/<pack>/` prefix. The pack split
moved it, and a stale path in a contributor-facing document is an instruction to
a directory that does not exist.

So **a docs-only PR can go red**, and the message names which contract you tripped.
The rule of thumb: anything git would publish is published, so an absolute path or
a private-project reference is a problem wherever you put it — not only under
`assets/`.

## Adding a skill

This is an **atomic multi-file edit**. Make all of it before running anything: a
skill directory that exists without its manifest row makes `load_manifest()`
raise, which fails a large part of the suite at once rather than pointing at what
you did.

1. Create `plugins/core/skills/<name>/SKILL.md` with frontmatter whose `name:` is
   `<name>` — or `plugins/python/skills/<name>/` if the skill is Python-specific.
   Put anything long in `references/` and link to it, rather than growing one
   file — the loader reads `SKILL.md` first and follows links only when needed.
2. Register it in `plugins/core/src/lemmi_ai_kit/assets/manifest.toml` with a
   `name`, `profile`, `invocation` and `summary`. All four are validated. The
   manifest lives in the core pack and registers the skills of **both** packs.
   - `profile` must be one of the values in `PROFILES` in
     [`plugins/core/src/lemmi_ai_kit/manifest.py`](plugins/core/src/lemmi_ai_kit/manifest.py)
     — a closed tuple. Read it rather than guessing; the set changes. It is
     validated, so a wrong value fails the suite — but be aware it currently has
     **no runtime effect**: `for_profiles()` has no production call site outside
     its own test. Treat it as a label that is checked for consistency, not a
     switch. The pack split has since landed and did *not* give it teeth:
     packaging is per **pack**, not per profile.
   - `invocation` is `user` (a slash command), `auto` (loaded as background
     reference) or `internal` (called by another skill, not by a person).
3. Add a correspondence row to `docs/upstream-sync.toml`. Nothing earlier will
   remind you: two tests in `tests/test_upstream_sync.py` bind that file to the
   shipped set in both directions, so a skill with no row fails the suite even
   though the manifest and the directory agree. For a skill written here rather
   than ported, the row is `upstream = ""` with `direction = "kit-origin"` and a
   note. A kit-origin skill *also* has to be added to the pinned set in
   `test_the_kit_origin_set_is_the_measured_one` — that constant is deliberately
   not derived from the record it checks, so a new kit-origin skill is supposed
   to argue with a test. The alarm is the design, not an obstacle.
4. Update the counts in `README.md`. Adding a core skill moves both the total and
   the per-pack number, and `tests/test_readme_counts.py` checks each claim
   against the manifest, so it will name every line that is now wrong and what it
   should say.
5. Run the suite, and believe it over this list. `load_manifest()` enforces a
   bijection between manifest entries and skill directories, so a skill that is
   registered but not shipped — or shipped but not registered — raises and takes
   a large part of the suite down at once rather than pointing at what you did.
   **Two of the steps above were found by running the suite after registering a
   skill, not by reasoning about it**, so treat the run as the authority: register
   what you know about, then let the failures name whatever else moved. A list of
   registration sites is itself a hand-maintained thing, and this one has been
   wrong before.
6. Do not add a skill count anywhere that nothing checks. `uv run python -m
   lemmi_ai_kit list` prints the catalog from the manifest. The counts in
   `README.md` are allowed to exist **because** `tests/test_readme_counts.py`
   holds each one against it — including per-pack claims, whose scoping phrase
   has to be registered in `_PACK_QUALIFIERS`. A count that test cannot resolve
   fails rather than being skipped, which is the whole point: a count it could
   not see is how "35 language-agnostic skills" stayed on the landing page,
   wrong, with the suite green.

## Contributing a language or domain pack

**Partly open.** The pack split has landed: the repo now ships a core pack and a
`python` pack from their own skills directories, so a language pack is a shape
that exists rather than a plan. What is still undefined is how an **external**
pack — one living in its own repository — registers itself with this marketplace.

So there are two answers depending on what you want:

- **You want your own conventions in your own projects.** You probably do not
  need to author a pack at all. Attach them in your own repo as an overlay; see
  [the adoption guide](docs/adoption-guide.md), which leads with exactly this.
- **You want a pack contributed back here.** Open a **pack contribution** issue
  describing the pack and what it would contain. That is genuinely useful now —
  the shape of the first few requests is what the external-pack authoring path
  gets designed against.

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
