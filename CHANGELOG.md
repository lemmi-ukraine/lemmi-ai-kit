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

- `metric-validity-check` — a new core skill: does a metric, score or judge actually track a
  user-visible outcome, tested BEFORE its number drives a decision. Joins the label to the artifact
  (a nearest-match join when there is no foreign key, with seven mandatory linkage diagnostics), runs
  a known-groups test over every metric in the suite, and returns one of four verdicts —
  SEPARATES / DOES NOT SEPARATE / UNDERPOWERED / SUSPECT — each stating what it licenses. It was an
  `[[unported]]` row (declined 2026-08-31 because, as written, its boundary pointed at a skill the
  kit does not ship); the carried copy strips those pointers and cites its source audit as evidence
  the kit does not carry. The record row says so.
- `python-conventions/references/comment-discipline.md` — the four things a code comment may carry
  (an ordering constraint, a counter-intuitive invariant, a non-obvious external behaviour, a one-line
  why-not), the security-prose KEEP default, why a comment the code contradicts is corrected rather
  than trimmed, and the symbol-not-line citation rule. `SKILL.md` gains a pointer section.
- `orchestrate/references/dispatch-gates.md` — six measured dispatch-time failure shapes: brief rules
  need the same suspicion as brief lists; a takeover is a dispatch; the forward plan is a wave-boundary
  deliverable; intersect a fix against peers' staging intent; one dispatch channel per kickoff block;
  and the three gate shapes that read DONE while a peer is in flight. `SKILL.md` points at it twice.
- `initiative-cleanup/references/settle-lessons.md` — six measured Step 1–3 lessons, including the
  tracked-but-uncommitted third state that both durability checks call durable.
- `test-conventions/references/test-doubles-gotchas.md` — four new sections: a `MagicMock()` logger
  makes negative `caplog` assertions vacuous; subclassing a test class re-runs its tests; a return
  value compared only against its broken-case value is untested; a filter with no test that REJECTS
  something is untested however many acceptance tests it has.
- `python-conventions/references/coding-patterns.md` — catching an optional database read's failure
  does not restore the caller's transaction (`InFailedSQLTransactionError`); use a `SAVEPOINT`, and
  inject a DATABASE error in the guard test, not a Python one.
- `post-task-review/references/fixture-design.md` §8–§11 — the probe counts output LINES (so
  `grep -c` probes as over-matching while correct), fixtures must model the real confounder, a
  pattern the shell tool cannot parse exits 2 and reads as "no match", and a scripted replacement
  spliced into a CRLF file silently makes it mixed-ending.
- `parallel-session-safety` — disjoint file sets are a guarantee about bytes, not meaning; a
  start-of-session ownership snapshot is a one-shot test; `git diff HEAD --stat` is blind to untracked
  files; measure-then-fix hand-off counts expire by design; landing a layer on a sibling branch
  removes its files from every peer's tree. §6 and §9 no longer recommend a `git worktree`, which §11
  already forbade — the skill contradicted itself.
- `scout-review` — an Adjudication section: two reviewers need adjudication, not aggregation; verify
  a finding's premise separately from its conclusion; sweep for the concept, not the cited location;
  a gate's product is a `(hash, verdict)` pair; withhold prior findings from a re-review pair.
- Smaller additions carried from the source project's 2026-09-13 consolidation: `ai-changelog` (a
  misfiled entry hides its own defects), `plan-critic` (did every enumerated item become a claim; does
  a supporting figure survive re-derivation), `pr-review-concise` (criterion 4 bounds EXISTING
  instances only), `agent-delegate` (boilerplate rules travel, their measurements do not),
  `hypothesis-validator` (the designated caller is the one that failed — run the steps, do not
  improvise), `task-learnings` (a native sub-agent must skip Step 0; a mandated preflight is
  compliance, not thrash), `learnings-format` (the bracketed heading is what enrols an entry in every
  check), `skill-reviewer` (a clean audit certifies the skills tree and nothing else),
  `initiative-planner` (a pre-settled consumer design destroys a usage probe),
  `consolidation-actions` (the handoff lint's anchor check is an on-disk existence test).
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

- The kit's own `CLAUDE.md` index no longer says "8-step post-task review" (the count `4f550b5`
  set out to retire and missed in this one place) or "archive rotation" for `hypothesis-validator`;
  both lines now match the manifest summaries.
- `ai-improvement-tracker`'s ledger section is titled "Ledger growth" rather than "File Size
  Management", matching the body it already carried (there is no archive; growth is expected).
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
