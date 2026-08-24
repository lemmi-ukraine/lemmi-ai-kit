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

**Prefix every one of them with `PYTHONDONTWRITEBYTECODE=1`, or export it once for
the session.** All four import the package, and each import writes `__pycache__/*.pyc`
under `plugins/core/src/` — inside the pack payload. `publish-check` refuses to publish
while the payload carries anything git does not track, so running the checks is enough
to block a publish afterwards, with a failure naming files you never wrote:

```bash
export PYTHONDONTWRITEBYTECODE=1        # once per shell, then run the four as above
```

**Run all four, not just `pytest`.** They are separate CI steps, so a green suite says
nothing about the other three — a formatting failure sat on `main` for five commits
because the sessions touching it ran only the tests.

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

## Contributing a pack

A **pack** is a plugin: its own directory under `plugins/`, its own per-host
manifests, its own `skills/` tree. The repo already serves two that way — `core`
and `python` — so a third means following a shape that exists rather than
inventing one.

Read [You probably do not need to author a
pack](docs/adoption-guide.md#2-you-probably-do-not-need-to-author-a-pack) first.
Most people who reach for a pack want a `### Project rules` section in their own
repository, which costs nothing, ships nothing, and stays private.

If you do want one contributed back here, **open a pack-contribution issue before
you write it.** The axis question below is much cheaper to settle in an issue
than in a pull request.

### Where it goes

| | |
|---|---|
| Directory | `plugins/<pack>/`, a sibling of `core` and `python` |
| Skills | `plugins/<pack>/skills/<name>/SKILL.md` — same frontmatter rules as any other skill |
| Registration | the manifest in the **core** pack registers the skills of *every* pack, so [Adding a skill](#adding-a-skill) above applies unchanged |
| Catalogs | both marketplace manifests, `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`, list every pack |
| Axis | **language, and only language** — not a framework, not a team, not a domain. See [when to author a pack instead](docs/adoption-guide.md#when-to-author-a-pack-instead) |

The mechanics — the two `plugin.json` files, the marketplace entries, the
skeleton to copy — are the subject of
[`docs/authoring-a-pack.md`](docs/authoring-a-pack.md) and the template in
[`plugins/_template/`](plugins/_template/). This section does not restate them on
purpose: a layout written down twice drifts, and the copy in the contributing
guide is the one nobody re-runs. **If those two paths are not in your checkout,
they have not landed yet** — they arrive with the pack-mechanism work. Until they
do, `plugins/python/` is the worked example, and it is small enough to read end
to end.

### Naming, so a reader can tell who wrote a pack

**Every pack Lemmi authors is named `lemmi-ai-kit-<something>` and declares
`"author": {"name": "lemmi-ukraine", ...}` in both of its `plugin.json` files. A
pack Lemmi did not author does neither** — it carries its author's own name in
the plugin name and its author's own identity in the `author` field. The plugin
name is the signal a person reads at a glance; the `author` field is the one a
script can read.

That is a labelling rule, not a quality judgement, and a pull request that takes
the `lemmi-ai-kit-` prefix for a pack Lemmi did not write will be asked to
rename. The reason is the next section: **nothing in this repo certifies a pack**,
so the name is the only provenance an adopter has, and a borrowed prefix destroys
it.

To check what you are looking at: in the repo, read `author` in the pack's
`plugins/<pack>/.claude-plugin/plugin.json`. On an installed pack, the plugin
name you installed is the name that carries the claim.

### What this repo checks, and what it does not

**There is no pre-merge review bar for a contributed pack, and merged does not
mean vetted.** That is a decision rather than an oversight, and it should be read
literally: a pack being in this repository is not evidence that anyone has
audited it.

[Review expectations](#review-expectations) below describes what the maintainer
actually reads on a pull request, and a pack contribution gets that reading like
anything else. It is one person's attention, not a gate: no named standard a pack
must clear, no sign-off, no audit. Nothing in that section entitles a reader to
treat a merged pack as checked.

What does run on every pull request is [the four checks](#the-four-checks), and
what they enforce is **shape, not substance**:

- the manifest and the skill directories agree in both directions, so nothing
  ships unregistered and nothing is registered that does not ship;
- every `SKILL.md` opens with valid frontmatter whose `name` matches its
  directory;
- every relative reference inside a skill resolves to a file that ships;
- nothing carries an absolute path, a machine-specific workaround, or a pointer
  at a repository the reader cannot open — the [hygiene
  contract](#the-hygiene-contract--why-a-prose-only-pr-can-fail-ci);
- the version agrees across every manifest, and every pack's declared source path
  resolves to a directory that exists;
- no core skill names a pack skill.

Not one of those reads what a skill tells an agent to *do*. **The checks cannot
tell whether a skill's advice is correct, whether the commands it instructs are
safe to follow, or whether it does what its own description says.** A green pull
request is a well-formed pack. That is the whole of what it certifies.

So, for anyone installing rather than contributing:

> **A skill is instructions an agent executes in your repository, with your
> agent's permissions, and there is no sandbox between the two.** Read a pack
> before you install it — `SKILL.md` is plain markdown, and reading it is the
> entire audit. [SECURITY.md](SECURITY.md#threat-model--read-this-part) sets out
> why, and it says the same about first-party packs.

### If a merged pack turns out to be harmful

"No review bar" describes what happens **before** a merge. It says nothing about
after one, and after one there is a route.

**Email support@lemmi.io, and do not open a public issue.**
[SECURITY.md](SECURITY.md#reporting-a-vulnerability) is the procedure, and it
covers a merged community pack exactly as it covers a first-party skill: the same
address, the same acknowledgement window, and the same commitment to either a fix
or a stated decision not to fix. A rough report of a real problem is worth
sending; it does not have to be a polished one.

Two things specific to packs:

- **Removal at the source is a commit.** The marketplaces serve this repository
  directly and there is no publish pipeline, so dropping a pack from the catalogs
  takes effect as soon as it is pushed. What that does to a copy already
  installed on a machine is your client's behaviour rather than this repo's — so
  if you are the one exposed, remove it locally too instead of waiting for an
  update to reach you.
- **Tell the pack's author as well.** The `author` field names them, which is the
  second reason the naming rule above earns its keep.

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
