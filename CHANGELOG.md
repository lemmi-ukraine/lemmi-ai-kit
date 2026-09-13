# Changelog

Notable changes to the kit, newest first. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**This file starts at the public release, not at the first commit.** Everything before
that was pre-release work on a private repository, and reconstructing it here from 130-odd
commits would produce a list nobody verified — which is the one thing this project's own
rules say not to ship. The git log is the record for that period, and
[`docs/research/`](docs/research/) carries the dated engineering notes behind the
decisions.

For what an entry means to an adopter: skills are delivered by the plugin, so a change
here reaches you on the next plugin update with nothing to re-sync in your repository.
Files the kit *seeds* into your project (`AGENTS.md`, `.ai/`) are yours once written and
are never rewritten except inside `kit-setup`'s own marked blocks.

## [Unreleased]

### Added

- `plugins/core/hooks/` — the kit's first hook surface. `gate_learnings_drain.py` is a
  `PreToolUse` guard that DENIES any Edit/Write/Bash call which would **remove** entries from
  `.ai/learnings.md` without a dated, non-trivial approved-plan record under
  `.ai/consolidation-gates/`. Appends are never blocked — intake must stay frictionless.
  `learning-consolidator` Phase 3 already said "STOP and wait for user approval"; a drain removed
  263 entries anyway, so the rule is a seam now instead of prose. Plugin hooks run automatically
  once the plugin is enabled, so this arrives with the pack rather than needing a per-project
  registration. Its limits are written into its own docstring rather than omitted: the gate record
  is forgeable by the model (it converts an invisible omission into a dated, auditable claim — an
  improvement, not enforcement), the Bash arm is a speed bump a rephrasing walks past, and hook
  config snapshots at session start. Ships with `test_gate_learnings_drain.py`, 17 cases, of which
  the ALLOW half is the important half: a guard that blocks unrelated work is worse than no guard.
- Three tests for the exactly-40/exactly-64 hex exemption in
  `session-retrospective/scripts/extract_sessions.py`, which **shipped untested**. Positive: git
  SHA-1 and sha256 citation anchors survive redaction. Negative: 32/39/41/63/65/80-char hex is
  still redacted, so the exemption cannot be widened into a leak without a test failing — verified
  by mutation, where neutering the rule fails exactly that test. Third: labelled secrets
  (`KEY=`/`TOKEN=`/`Bearer`) are masked even at the exempt lengths, which is what makes the
  exemption safe; the residual risk is a bare, unlabelled, exactly-40/64 secret.
- `--expect-positive-exact` in `post-task-review/scripts/probe_checker.py`. Its absence made
  exact-count probes unusable against the kit's copy: a checker that must match a KNOWN
  number of findings could only assert "at least N", which cannot catch over-matching.
- Brief-contract item 10 in `orchestrate` — any rule a close-time lint enforces by EXACT MATCH
  goes into the brief verbatim, never by pointing at the template that carries it. Template
  comments are read once and thereafter written from habit, and character substitution (`→` for
  `->`) is invisible until the lint runs at the end of the session.

- `tests/test_commit_message_hygiene.py` — the hygiene contract extended to commit
  messages, which no scan had ever covered. Confidentiality patterns are checked;
  portability patterns are not, and the split is asserted exhaustive and disjoint so a
  new pattern cannot land in the unscanned half.
- `tests/test_content_safety.py` — rejects instruction-injection shapes, invisible and
  bidirectional characters, network imports and data-to-code calls in shipped scripts,
  and pins the single legitimate `shell=True` site. Asserts the package declares no
  runtime dependencies.
- `publish-check` and the skill audit now run in CI, and Dependabot watches the actions
  and dev toolchain.

### Changed

- `kit-setup` no longer tells users that project-local skill copies "shadow the plugin's
  versions" — **they do not**. Per the Claude Code documentation, a plugin skill and a
  same-named project skill **both load**, because plugin skills are namespaced
  `/plugin-name:skill-name`. The practical consequence is the opposite of shadowing and worth
  stating: the adopter gets two skills per name, the stale project copy keeps the bare `/name`,
  and installing the plugin does not on its own retire anything.
- Every stale "8-step post-task-review" claim removed — the skill runs Step 0 through Step 9.
  It was wrong in five places, including `assets/templates/AGENTS.md`, which **seeds the claim
  into every project the kit scaffolds**. Replaced with count-free wording, because a hard-coded
  step count in a satellite document is precisely what went stale.
- `post-task-review/references/review-checklist.md` was not merely mislabelled, it was
  **incomplete**: it enumerated Steps 1–8, omitting Step 0 (blast radius) and Step 9 (the
  mandatory close self-challenge). Anyone working from the checklist skipped both. Both added.
- `agent-delegate` no longer says "all **9** items apply here" — the count is gone, so adding a
  contract item cannot make it stale again (adding item 10 just did).
- `vertical-slice`'s description no longer says "in this project", which means nothing to an
  adopter. (A tree-wide sweep found six other uses of that phrase; all read as "the project you
  are working in" and were deliberately left.)

- CI hardened for a public repository: least-privilege `permissions`, actions pinned to
  commit SHAs rather than mutable tags, and `PYTHONDONTWRITEBYTECODE` set job-wide so
  `publish-check` does not block on bytecode CI itself wrote.
- The pull-request template asks reviewers to read added instruction prose in full,
  rather than checking it against a pattern list alone.
- Maintainer, security, and conduct contact is a named maintainer rather than a shared
  alias that had never been verified to receive mail.

### Security

- Commit messages that named and sized the private source project were rewritten out of
  history before the repository was made public. See the security policy in
  [SECURITY.md](SECURITY.md) for how to report anything this missed.

## [0.1.0-preview.1]

First tagged preview. Two packs — `lemmi-ai-kit-core` and `lemmi-ai-kit-python` — for
Claude Code and Codex, installed as a plugin rather than vendored. See the
[README](README.md) for what ships and [docs/adoption-guide.md](docs/adoption-guide.md)
for installing it.
