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
