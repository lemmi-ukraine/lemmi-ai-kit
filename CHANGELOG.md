# Changelog

Notable changes to the kit, newest first. Entries are grouped under the date they landed,
strictly reverse-chronological, and each one follows the structured format the
`ai-changelog` skill defines:

```markdown
### {TYPE}: {short descriptive title}
- **What:** what changed
- **Why:** what problem it solves, with the measurement behind it where there is one
- **Files:** what was created, modified or deleted
- **Affected workflows:** which skills or workflows this reaches
```

Types are the `ai-changelog` vocabulary — `SKILL-ADDED`, `SKILL-MODIFIED`, `SKILL-REMOVED`,
`CONV-ADDED`, `CONV-MODIFIED`, `RULE-ADDED`, `RULE-MODIFIED`, `WORKFLOW-MODIFIED`,
`INFRA-ADDED`, `INFRA-MODIFIED`, `CONSOLIDATION`, `EXPERIMENT-REGISTERED` — plus `SECURITY`
and `RELEASE`, which that vocabulary has no equivalent for because it was written for an
internal log rather than a published one. Releases are marked by git tags, named in their
own `RELEASE` entry, rather than by version headings.

**This file starts at the public release, not at the first commit.** Everything before that
was pre-release work on a private repository, and reconstructing it here from 130-odd
commits would produce a list nobody verified — which is the one thing this project's own
rules say not to ship. The git log is the record for that period, and
[`docs/research/`](docs/research/) carries the dated engineering notes behind the decisions.

For what an entry means to an adopter: skills are delivered by the plugin, so a change here
reaches you on the next plugin update with nothing to re-sync in your repository. Files the
kit *seeds* into your project (`AGENTS.md`, `.ai/`) are yours once written and are never
rewritten except inside `kit-setup`'s own marked blocks.

---

## 2026-09-14

### SKILL-ADDED: Share portable flow mapping through Core
- **What:** Registered flow-mapping in Core with its schema, five reusable tools and synthetic self-certification project. Tool paths stay inside the plugin; consumer roots and code directories are explicit. Preserved authored projection columns and made missing corpus inputs fail visibly. Comment checking distinguishes docstrings from executable string expressions.
- **Why:** The formerly deferred workflow must work outside its source checkout without copied skills or validators. Independent consumer tests exercise installation paths, invalid inputs and the shared-tool contract.
- **Files:** `plugins/core/skills/flow-mapping/`, Core native manifests and README, the bundled `manifest.toml`, `docs/upstream-sync.toml`, `README.md`, `tests/test_flow_mapping.py`, `tests/test_upstream_sync.py`, `.ai/ai-changelog.md`, `.ai/learnings.md`, `.ai/improvement-hypotheses.md`, `CHANGELOG.md`.
- **Affected workflows:** Flow mapping, native Core installation, flow validation, projection generation, seam reconciliation and optional comment cleanup. This completes the deferred port described in the earlier entry.

### INFRA-MODIFIED: Describe the research workflows and flow-mapping port status

- **What:** README now explains custom parallel research, source planning and ownership,
  and the separate research-backed skill-authoring pipeline. Flow mapping is described
  with its current deferred-port status from the upstream synchronization record.
- **Why:** the workflow roles and outputs should be visible before a user chooses a pack.
- **Files:** `README.md`
- **Affected workflows:** `parallel-deep-research`, `research-source-planner`,
  `research-source-claim`, `skill-researcher`, `skill-creation-workflow`

### INFRA-MODIFIED: Guide and measure agent-led installation

- **What:** a paste-ready README prompt and new/existing-project guides, with four native
  agent trials recording wall-clock time, project preservation and content-review findings.
- **Why:** users should have one installation entry point and evidence of what it preserves.
- **Files:** `README.md`, `docs/research/2026-09-14-agent-installation.md`,
  `docs/research/2026-09-14-agent-installation-results.json`
- **Affected workflows:** native plugin installation, `kit-setup`

### INFRA-ADDED: Bundle FFF with Core

- **What:** the six official FFF v0.10.6 binaries for macOS, Linux and Windows on x64/ARM64,
  with upstream licensing and checksums. The shared MCP declaration launches the selected
  verified binary through uv, without a separate FFF installation or first-use FFF download.
- **Why:** users should receive file search with Core without per-machine FFF setup.
- **Files:** `plugins/core/vendor/fff/`, `plugins/core/.mcp.json`,
  `plugins/core/src/lemmi_ai_kit/fff.py`, both Core plugin manifests, `.gitattributes`,
  `tests/test_fff.py`, `plugins/core/README.md`
- **Affected workflows:** file search, native plugin installation

### INFRA-MODIFIED: Distribute workflow families as optional native plugins

- **What:** Research, Orchestration and Skill Authoring ship as separate optional packs;
  Core retains development and learning workflows, and Python remains optional. Moved
  skills use their owning namespace and report missing prerequisites. Authoring and
  Orchestration declare Core >=0.2.0 for Claude; Codex users install Core explicitly.
- **Why:** native plugin managers should own capability selection and updates, with one
  canonical skill source and project-owned conventions.
- **Files:** both marketplace catalogs, `plugins/`, the Core manifest/scaffold/audit helpers,
  template assets, `pyproject.toml`, `uv.lock`, current adoption/authoring/migration guides,
  and manifest/plugin/isolation/CLI/document-reference tests
- **Affected workflows:** native plugin installation, `kit-setup`, optional workflow handoffs

### SKILL-ADDED: `metric-validity-check`

- **What:** a new core skill asking whether a metric, score or judge actually tracks a
  user-visible outcome, tested BEFORE its number drives a decision. It joins the label to the
  artifact (a nearest-match join where there is no foreign key, with seven mandatory linkage
  diagnostics), runs a known-groups test over every metric in the suite, and returns one of
  four verdicts — SEPARATES / DOES NOT SEPARATE / UNDERPOWERED / SUSPECT — each stating what
  it licenses.
- **Why:** it was an `[[unported]]` row, declined 2026-08-31 because as written its boundary
  pointed at a skill the kit does not ship. The carried copy strips those pointers and cites
  its source audit as evidence the kit does not carry; the record row says so.
- **Files:** `plugins/core/skills/metric-validity-check/SKILL.md` and its `references/`,
  `plugins/core/src/lemmi_ai_kit/assets/manifest.toml`, `docs/upstream-sync.toml`
- **Affected workflows:** `metric-validity-check`

### SKILL-MODIFIED: Six reference files carried from the 2026-09-13 upstream consolidation

- **What:** `python-conventions/references/comment-discipline.md` (the four things a comment
  may carry, the security-prose KEEP default, and the symbol-not-line citation rule);
  `orchestrate/references/dispatch-gates.md` (six measured dispatch-time failure shapes);
  `initiative-cleanup/references/settle-lessons.md` (six Step 1–3 lessons, including the
  tracked-but-uncommitted third state both durability checks call durable);
  `test-conventions/references/test-doubles-gotchas.md` (a `MagicMock()` logger makes negative
  `caplog` assertions vacuous; subclassing a test class re-runs its tests; a filter with no
  rejecting test is untested however many acceptance tests it has);
  `python-conventions/references/coding-patterns.md` (catching an optional database read's
  failure does not restore the caller's transaction — `InFailedSQLTransactionError`; use a
  `SAVEPOINT`, and inject a DATABASE error in the guard test, not a Python one); and
  `post-task-review/references/fixture-design.md`
  §8–§11 (the probe counts output LINES, so `grep -c` probes as over-matching while correct; a
  pattern the shell tool cannot parse exits 2 and reads as "no match").
- **Why:** each is a measured failure shape rather than advice, and each `SKILL.md` gains a
  pointer section so the reference is reachable from the skill that needs it.
- **Files:** the six `references/` files above, plus the `SKILL.md` of each owning skill
- **Affected workflows:** `python-conventions`, `orchestrate`, `initiative-cleanup`,
  `test-conventions`, `post-task-review`

### SKILL-MODIFIED: `parallel-session-safety` and `scout-review`

- **What:** `parallel-session-safety` gains that disjoint file sets are a guarantee about bytes
  and not meaning, that a start-of-session ownership snapshot is a one-shot test, that
  `git diff HEAD --stat` is blind to untracked files, and that landing a layer on a sibling
  branch removes its files from every peer's tree. `scout-review` gains an Adjudication section:
  two reviewers need adjudication rather than aggregation, a finding's premise is verified
  separately from its conclusion, the sweep is for the concept rather than the cited location,
  a gate's product is a `(hash, verdict)` pair, and prior findings are withheld from a
  re-review pair.
- **Why:** `parallel-session-safety` §6 and §9 recommended a `git worktree` that §11 already
  forbade — the skill contradicted itself, and both now agree.
- **Files:** `plugins/core/skills/parallel-session-safety/SKILL.md`,
  `plugins/core/skills/scout-review/SKILL.md`
- **Affected workflows:** `parallel-session-safety`, `scout-review`

### CONSOLIDATION: Smaller carries across ten skills

- **What:** `ai-changelog` (a misfiled entry hides its own defects), `plan-critic` (did every
  enumerated item become a claim; does a supporting figure survive re-derivation),
  `pr-review-concise` (criterion 4 bounds EXISTING instances only), `agent-delegate`
  (boilerplate rules travel, their measurements do not), `hypothesis-validator` (the designated
  caller is the one that failed — run the steps, do not improvise), `task-learnings` (a native
  sub-agent must skip Step 0), `learnings-format` (the bracketed heading is what enrols an entry
  in every check), `skill-reviewer` (a clean audit certifies the skills tree and nothing else),
  `initiative-planner` (a pre-settled consumer design destroys a usage probe), and
  `consolidation-actions` (the handoff lint's anchor check is an on-disk existence test).
- **Why:** each was a measured finding in the source project's 2026-09-13 consolidation,
  de-branded and carried rather than restated.
- **Files:** the `SKILL.md` or `references/` file of each skill named above
- **Affected workflows:** the ten skills named above

### INFRA-MODIFIED: The kit's own `CLAUDE.md` index matches the manifest again

- **What:** the index no longer says "8-step post-task review" — the count `4f550b5` set out to
  retire and missed in this one place — nor "archive rotation" for `hypothesis-validator`.
  `ai-improvement-tracker`'s ledger section is titled "Ledger growth" rather than "File Size
  Management", matching the body it already carried.
- **Why:** both lines now match the manifest summaries, and the ledger has no archive, so a
  section named for size management described a policy the skill does not have.
- **Files:** `CLAUDE.md`, `plugins/core/skills/ai-improvement-tracker/SKILL.md`
- **Affected workflows:** `post-task-review`, `hypothesis-validator`, `ai-improvement-tracker`

## 2026-09-13

### INFRA-ADDED: The kit's first hook surface, gating learnings drains

- **What:** `plugins/core/hooks/` arrives, with `gate_learnings_drain.py` as a `PreToolUse`
  guard that DENIES any Edit/Write/Bash call which would **remove** entries from
  `.ai/learnings.md` without a dated, non-trivial approved-plan record under
  `.ai/consolidation-gates/`. Appends are never blocked — intake must stay frictionless.
  Plugin hooks are auto-discovered from `hooks/hooks.json`, so this arrives with the pack
  rather than needing a per-project registration. Ships with `test_gate_learnings_drain.py`,
  17 cases, of which the ALLOW half is the important half: a guard that blocks unrelated
  work is worse than no guard.
- **Why:** `learning-consolidator` Phase 3 already said "STOP and wait for user approval";
  a drain removed 263 entries anyway, so the rule is a seam now instead of prose. Its limits
  are written into its own docstring rather than omitted: the gate record is forgeable by the
  model (it converts an invisible omission into a dated, auditable claim — an improvement,
  not enforcement), the Bash arm is a speed bump a rephrasing walks past, and hook config
  snapshots at session start.
- **Files:** `plugins/core/hooks/gate_learnings_drain.py`, `plugins/core/hooks/hooks.json`,
  `plugins/core/hooks/test_gate_learnings_drain.py`
- **Affected workflows:** `learning-consolidator`, `task-learnings`

### SKILL-MODIFIED: The hex-redaction exemption is tested for the first time

- **What:** Three tests for the exactly-40/exactly-64 hex exemption in
  `session-retrospective/scripts/extract_sessions.py`, which **shipped untested**. Positive:
  git SHA-1 and sha256 citation anchors survive redaction. Negative: 32/39/41/63/65/80-char
  hex is still redacted — verified by mutation, where neutering the rule fails exactly that
  test. Third: labelled secrets (`KEY=`/`TOKEN=`/`Bearer`) are masked even at the exempt
  lengths.
- **Why:** the exemption could have been widened into a leak with nothing failing. The
  negative test is what makes that impossible, and the labelled-secret test is what makes
  the exemption safe at all; the residual risk is a bare, unlabelled, exactly-40/64 secret.
- **Files:** `plugins/core/skills/session-retrospective/scripts/extract_sessions.py`,
  `plugins/core/skills/session-retrospective/scripts/test_extract_sessions.py`
- **Affected workflows:** `session-retrospective`

### SKILL-MODIFIED: `probe_checker.py` gains `--expect-positive-exact`

- **What:** an exact-count assertion for probe fixtures.
- **Why:** its absence made exact-count probes unusable against the kit's own copy — a
  checker that must match a KNOWN number of findings could only assert "at least N", which
  cannot catch over-matching.
- **Files:** `plugins/core/skills/post-task-review/scripts/probe_checker.py`
- **Affected workflows:** `post-task-review`

### SKILL-MODIFIED: Brief-contract item 10, and the count that made item 9 stale

- **What:** `orchestrate` gains brief-contract item 10 — any rule a close-time lint enforces
  by EXACT MATCH goes into the brief verbatim, never by pointing at the template that carries
  it. `agent-delegate` correspondingly no longer says "all **9** items apply here".
- **Why:** template comments are read once and thereafter written from habit, and character
  substitution (`→` for `->`) is invisible until the lint runs at the end of the session. The
  count is gone rather than corrected, because adding item 10 is exactly what made "9" stale.
- **Files:** `plugins/core/skills/orchestrate/SKILL.md`,
  `plugins/core/skills/orchestrate/references/brief-template.md`,
  `plugins/core/skills/agent-delegate/SKILL.md`,
  `plugins/core/skills/agent-delegate/assets/worker-preamble.md`
- **Affected workflows:** `orchestrate`, `agent-delegate`

### SKILL-MODIFIED: `kit-setup` no longer claims project copies shadow the plugin

- **What:** the "shadow the plugin's versions" wording is gone — **they do not**. Per the
  Claude Code documentation, a plugin skill and a same-named project skill **both load**,
  because plugin skills are namespaced `/plugin-name:skill-name`.
- **Why:** the practical consequence is the opposite of shadowing and worth stating: the
  adopter gets two skills per name, the stale project copy keeps the bare `/name`, and
  installing the plugin does not on its own retire anything.
- **Files:** `plugins/core/skills/kit-setup/SKILL.md`
- **Affected workflows:** `kit-setup`

### CONSOLIDATION: Hand-written step counts retired across skills and the scaffold template

- **What:** every stale "8-step post-task-review" claim removed — the skill runs Step 0
  through Step 9. It was wrong in five places, including `assets/templates/AGENTS.md`, which
  **seeds the claim into every project the kit scaffolds**.
  `post-task-review/references/review-checklist.md` was not merely mislabelled but
  **incomplete**: it enumerated Steps 1–8, omitting Step 0 (blast radius) and Step 9 (the
  mandatory close self-challenge), so anyone working from the checklist skipped both.
  `vertical-slice`'s description no longer says "in this project", which means nothing to an
  adopter.
- **Why:** replaced with count-free wording rather than a corrected number, because a
  hard-coded step count in a satellite document is precisely what went stale. A tree-wide
  sweep found six other uses of "in this project"; all read as "the project you are working
  in" and were deliberately left.
- **Files:** `plugins/core/skills/post-task-review/SKILL.md` and its `references/`,
  `plugins/core/skills/spec-driven-dev/SKILL.md` and its `references/`,
  `plugins/core/skills/vertical-slice/SKILL.md`,
  `plugins/core/src/lemmi_ai_kit/assets/templates/AGENTS.md`,
  `plugins/core/src/lemmi_ai_kit/assets/manifest.toml`
- **Affected workflows:** `post-task-review`, `spec-driven-dev`, `vertical-slice`

---

## 2026-08-31

### INFRA-ADDED: The hygiene contract extended to commit messages

- **What:** `tests/test_commit_message_hygiene.py` — a publication surface no scan had ever
  covered. Confidentiality patterns are checked; portability patterns are not, and the split
  is asserted exhaustive and disjoint.
- **Why:** so a new pattern cannot land in the unscanned half without a test failing.
- **Files:** `tests/test_commit_message_hygiene.py`
- **Affected workflows:** contribution review, CI

### INFRA-ADDED: Content-safety gate over shipped prose and scripts

- **What:** `tests/test_content_safety.py` — rejects instruction-injection shapes, invisible
  and bidirectional characters, network imports and data-to-code calls in shipped scripts,
  and pins the single legitimate `shell=True` site. Asserts the package declares no runtime
  dependencies.
- **Why:** the payload is instructions an agent acts on in someone else's repository, so the
  shapes that are never legitimate should fail by construction rather than by review.
- **Files:** `tests/test_content_safety.py`
- **Affected workflows:** contribution review, CI

### INFRA-MODIFIED: CI hardened for a public repository that accepts contributions

- **What:** `publish-check` and the skill audit now run in CI, and Dependabot watches the
  actions and the dev toolchain. CI runs with least-privilege `permissions`, actions pinned
  to commit SHAs rather than mutable tags, and `PYTHONDONTWRITEBYTECODE` set job-wide. The
  pull-request template asks reviewers to read added instruction prose in full, rather than
  checking it against a pattern list alone. Maintainer, security and conduct contact is a
  named maintainer.
- **Why:** the four checks cannot see what the skill audit checks, mutable action tags are a
  supply-chain surface, and `publish-check` would otherwise block on bytecode CI itself
  wrote. The previous shared contact alias had never been verified to receive mail.
- **Files:** `.github/workflows/ci.yaml`, `.github/dependabot.yml`,
  `.github/PULL_REQUEST_TEMPLATE.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `README.md`
- **Affected workflows:** CI, contribution review

### SECURITY: Private-project references rewritten out of history before publication

- **What:** commit messages that named and sized the private source project were rewritten
  out of history before the repository was made public.
- **Why:** `refs/pull/<N>/head` is permanent on GitHub, so a force-push could not have
  cleaned it. See [SECURITY.md](SECURITY.md) for how to report anything this missed.
- **Files:** repository history
- **Affected workflows:** none

---

## 2026-07-03

### RELEASE: `v0.1.0-preview.1` — first tagged preview

- **What:** two packs — `lemmi-ai-kit-core` and `lemmi-ai-kit-python` — for Claude Code and
  Codex, installed as a plugin rather than vendored.
- **Why:** a plugin install updates in place; a vendored copy goes stale in every repository
  that took one.
- **Files:** see the [README](README.md) for what ships and
  [docs/adoption-guide.md](docs/adoption-guide.md) for installing it.
- **Affected workflows:** all
