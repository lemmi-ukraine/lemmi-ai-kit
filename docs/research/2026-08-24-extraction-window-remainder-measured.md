# The extraction-window remainder, measured — 92 lines to adjudicate, not 7 skills to review

**Dated:** 2026-08-24. **Scope:** the 7 skills left `unreviewed` in `docs/upstream-sync.toml`'s
`[extraction_window]` block after the W-window paid 7 of the 16 affected and 2 more stopped shipping.

**This record measures. It recovers nothing** — no skill file was modified. Its purpose is to turn
"7 skills need a per-skill read" into a bounded, line-level worklist so the recovery is adjudication
rather than exploration.

## Method, and why it needs no per-skill base

The window is the upstream range `3dd2496d..c05bf72d` — from the true `extraction_base` to the base
the 2026-08-23 refresh actually used, four days inside the extraction window. Every line **added** to
a skill's files in that range was, by the refresh's own classification rule
(*"present at base, absent in ours, present in theirs" → deliberate kit deletion, keep it deleted*),
eligible to be dropped silently.

So the measurement is range-based and does not need each skill's own base: for every window-added
line, is that line present **anywhere in the shipped skill directory**? Per-skill bases matter for
the *merge*; they do not change what the window added.

Presence is checked against the whole shipped directory, not just `SKILL.md`, so content that moved
between files is not counted as lost. Files are read as bytes and decoded explicitly as UTF-8 —
locale decoding has produced false results in this repo before.

**Scan surface, printed rather than assumed:** 3 commits in the window · 31 files touched ·
16 skill directories touched. A zero here would have meant a broken probe, not a clean result.

## The table

| Skill (shipped path) | Window lines | Present | Absent | Carriage |
|---|---:|---:|---:|---:|
| `core/ai-docs-lookup` | 2 | 2 | **0** | **100%** |
| `core/session-retrospective` | 598 | 589 | 9 | 98% |
| `core/hypothesis-validator` | 115 | 104 | 11 | 90% |
| `core/task-learnings` | 56 | 37 | 19 | **66%** |
| **`python/test-conventions`** | 21 | 5 | 16 | **24%** |
| **`core/skill-content-reviewer`** | 18 | 0 | 18 | **0%** |
| **`core/skill-researcher`** | 19 | 0 | 19 | **0%** |
| **TOTAL** | **829** | **737** | **92** | **89%** |

### Two recorded claims confirmed exactly

- **`skill-researcher`: 19 window lines, none present.** The debt record's proof case reproduces to
  the line. And it still reports zero drift against the pin, because drift counts upstream commits
  since the base and the base is wrong.
- **`task-learnings`: 66%.** The open stray's figure is exact — 37 of 56.

### Two findings that were not on the list

- **`skill-content-reviewer`: 18 lines, 0% carriage.** Not previously recorded anywhere. Same shape
  as `skill-researcher`, and it had no proof case attached to make anyone look.
- **`test-conventions` ships in the PYTHON pack**, `plugins/python/skills/test-conventions`, not core.
  Two orchestration briefs stated `plugins/core/skills/test-conventions`; the correspondence map in
  `upstream-sync.toml` is the authority and says otherwise. A brief written from a remembered path,
  which is the same defect as checking a gate against the wrong tree.

## What the absent lines actually are — a first pass, not a verdict

Read, not inferred. **Every line still needs an explicit RECOVER / CORRECTLY-ABSENT call with a rule
cited; this section only says where the judgement will be easy and where it will not.**

**Likely CORRECTLY ABSENT — `session-retrospective` (9) and `hypothesis-validator` (11).** These
cluster on things the kit deliberately does not ship: `python .claude/skills/<name>/scripts/ai_files_lint.py`
and `audit_skills.py` (the two linters the kit **substitutes its own CLI** for), hard-coded
`.claude/skills/<name>/scripts/` paths (banned — `${CLAUDE_SKILL_DIR}` instead), the
`interview-transcript-analysis` skill (ruled out of the port by OP-5), and machine-specific rules —
one of which names the developer OS and forbids a particular runner on it. (Quoting that line
verbatim here would itself trip the hygiene guard, which is the point of the rule.) Their 98% and 90%
carriage is consistent with a refresh that worked and stripped what it was supposed to.

**Likely RECOVER — `skill-content-reviewer` (18) and `skill-researcher` (19), the two at 0%.** The
absent content is generic reviewer craft with no source-project coupling. From
`skill-content-reviewer`: that a Research Brief *"is itself a sub-agent CLAIM, not ground truth"*, and
that a skill's top load-bearing claims must be verified independently *"even when the brief agrees —
agreement between the skill and the brief is not verification; an error in the brief propagates
otherwise."* That is exactly the discipline this program has spent days relearning, and it was
sitting in an upstream commit the refresh classified as a deliberate deletion.

**Genuinely hard — `test-conventions` (16).** Generic technique in domain-specific clothing: testing
a 402 quota-exhausted path by overriding a DI factory with a mock that raises, *"with no internal
patching"*. The technique is portable and good; the illustration names `FeatureUsageGatingService`,
`InterviewSession` and `ERROR_CODE_USAGE_EXHAUSTED`, which are source-project internals. Recovering
the lesson without the coupling is a rewrite, not a merge — which is precisely why the debt record
insists on a per-skill read rather than a bulk re-merge.

## What this does not do

- **It recovers nothing.** `status` stays `"unreviewed"` and must stay there until the 92 lines are
  adjudicated and the RECOVER set is carried.
- **It does not use each skill's own extraction base**, because the measurement does not need one.
  The recovery does — see `2026-08-23-per-skill-extraction-base.md`. A single base is wrong for
  **29 of 29** extraction-era skills.
- **It ignores pure-whitespace additions** and counts a line present on exact substring match, so a
  line reworded on the kit side reads as absent. That biases the absent count **upward**, which is
  the safe direction for a worklist but means 92 is a ceiling, not a total.
- **It reads only the 7 unreviewed skills.** The other 9 affected are taken as settled on the
  W-window record's evidence, not re-measured here.

---

## Appendix — a byte-size screen across all 38 shipped skills, and why its worst numbers are noise

Run 2026-08-24 on request, with a caveat stated up front: **a two-way kit-vs-upstream size gap is the
metric handoff §8 forbids as a refresh measure**, because it cannot separate (a) upstream content the
kit is missing, from (b) content the kit strips on purpose, from (c) portability prose extraction
*added*. 7 of 26 "behind" skills once needed nothing. So this is a **screen** — it says where to look,
never whether something is wrong.

Mapping came from the correspondence map in `upstream-sync.toml`, **not from directory names**: three
skills were renamed on extraction and `test-conventions` ships in the **python** pack.

**Scan surface:** 38 map rows · 38 shipped dirs found by `SKILL.md` presence · 43 upstream dirs.

### The four lowest ratios, and what each one actually is

| Skill | kit/up | The gap, in full |
|---|---:|---|
| `learning-consolidator` | **0.18** | `scripts/ai_files_lint.py` (46KB) + its test (25KB) — **the linter the kit substitutes its own CLI for** — plus **247KB of upstream committed `__pycache__/*.pyc`** |
| `session-retrospective` | **0.45** | **197KB of upstream committed `.pyc`, and nothing else.** `extract_sessions.py` itself ships |
| `test-conventions` | **0.70** | `references/docker-runner-gotchas.md` (9.4KB) + `README.md` (596B) |
| `skill-reviewer` | **0.71** | `scripts/audit_skills.py` (13KB) — the other linter the kit replaces |

**Upstream's skills tree carries 9 committed `.pyc` files totalling 737,318 bytes.** In a byte
comparison that is pure noise, and it produces the two most alarming ratios in the table. A reader who
took 0.18 at face value would conclude `learning-consolidator` lost 82% of its content; it lost none.

### The one gap that needed a judgement, and it is correctly absent

`docker-runner-gotchas.md` is titled **"Docker Test-Runner Gotchas (this host)"**. It documents
`docker-compose.test.yaml` runners by name (`test-runner-parallel`, `test-runner-fast`), cites
`.ai/learnings.md` with a date, and points at the source project's `AGENTS.md` gate-output rule —
machine-specific and project-specific infrastructure the extraction contract strips.

**And the pointer went with it.** Upstream's `SKILL.md:318` links to that reference; the kit's
`SKILL.md` links only to `references/test-doubles-gotchas.md`, which it ships. **No orphaned
reference** — the file and its link were dropped together, which is what a correct deliberate drop
looks like and is exactly what §8 warns is indistinguishable from loss by a size metric alone.

### Set completeness, independently confirmed

**8 upstream directories map to no shipped skill, and all 8 are accounted for by recorded rulings:**
`feedback-audit` and `interview-transcript-analysis` (out, OP-5) · `usage-guard` (deferred, §5d) ·
`openai-realtime-quirks` (dropped, OQ-2) · the four prompt skills (removed, D1). **3 shipped skills
have no upstream counterpart** and are `kit-origin` by the map: `kit-setup`, `scout-review`,
`test-planner`.

**6 skills are LARGER than upstream** — `plan-critic` 1.29, `analyze-logs` 1.22, `spec-driven-dev`
1.05 among them. That is genericization and portability prose the kit added, plus the verification
stage wired in at `eefaa23`. Larger is the expected direction for a skill the kit has worked on.

### Verdict

**The screen surfaced no content-loss defect beyond the 92 window lines measured above.** Every ratio
below 0.75 resolves to committed bytecode, a deliberately substituted linter, or a correctly stripped
host-specific reference. That is a reassuring result — and it is now evidence rather than assertion,
which is the only reason it is worth writing down.

---

## Progress — the two 0% skills are recovered (2026-08-24, orchestration, inline)

Seven consecutive subagent dispatches died on API 529s, so the two highest-value items were done
inline rather than delegated. Both pushed. Every failed agent died clean — the 7 skill directories
were verified untouched after each.

| Skill | Carriage before | After | Commit |
|---|---:|---:|---|
| `skill-researcher` | **0%** | **74%** | `ac19b23` |
| `skill-content-reviewer` | **0%** | **94%** | `8fb2316` |

**The residual absences in both are deliberate, not omissions:** a `(project rules)` header framing,
a parenthetical crediting the source project's own review loop, a site-crawlability note scoped to
"this environment" (recovered in generalised form instead), and one dated internal citation.

**The pair had to move together.** Upstream added them in the same commit and they form one contract:
`skill-researcher` emits inline source markers and states that its own brief is a claim;
`skill-content-reviewer` independently verifies the top load-bearing claims rather than trusting
skill-brief agreement. Recovering either alone leaves the contract half-wired.

**One of these was worse than missing content.** `skill-content-reviewer` shipped
*"DO verify claims against the Research Brief as ground truth"* — a rule upstream had already
corrected. The kit was not merely behind; it was shipping a superseded instruction that told
reviewers to trust exactly the artifact this program keeps getting burned by. That is the sharpest
argument in the record for paying the rest of this debt: a wrong-and-live rule looks identical to a
current one until someone reads the window.

## The remaining worklist, adjudicated where the diff has been read

**`task-learnings` (19 absent) — diff read in full, NOT executed.** It spans `SKILL.md` and
`references/learnings-format.md` and needs generalisation, not a merge, which is why it was not
rushed inline:

- **RECOVER:** the dedup-check-first step · *"NEVER append at the file end or under whatever section
  happens to be last — a chronological catch-all misleads the consolidator's clustering"* · verify
  placement **structurally**, not by eyeballing · the canonical-category set as a single source of
  truth shared with `learning-consolidator`, with `SKILL.md` linking rather than restating it · the
  intake-buffer-drains-to-homes lifecycle model · and the Step 6 row *"invariant a future edit could
  silently break → co-located code comment at the exact site"*, which is fully generic.
- **REPOINT, do not drop:** the placement self-check calls the unshipped `ai_files_lint.py` by a
  hard-coded skill-script path. The kit substitutes its own CLI — recover the instruction pointed at
  `lemmi_ai_kit lint`.
- **CORRECTLY ABSENT:** the `backend/app/core/<module>/README.md` and
  `backend/app/features/<feature>/README.md` layout, the `docs/onboarding/` sync rule, the named
  legacy section headers, one machine-specific runner rule, and two dated internal citations. The
  *idea* behind the subsystem row — a gotcha scoped to one module belongs in that module's README
  rather than the global rules — is generic and should be recovered without the paths.

**`hypothesis-validator` (11), `session-retrospective` (9), `python/test-conventions` (16) — not yet
adjudicated.** The first two are expected to be mostly correctly-absent on the evidence sampled
above, but expected is not measured and neither has had every line read. `test-conventions` remains
the hard one: portable technique wearing source-project internals, a rewrite rather than a merge.

**`status` stays `"unreviewed"`.** 36 of 92 lines are now resolved.
