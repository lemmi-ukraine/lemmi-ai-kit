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
`interview-transcript-analysis` skill (ruled out of the port by OP-5), and machine-specific rules
("never `uv run` on this Windows host"). Their 98% and 90% carriage is consistent with a refresh that
worked and stripped what it was supposed to.

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
