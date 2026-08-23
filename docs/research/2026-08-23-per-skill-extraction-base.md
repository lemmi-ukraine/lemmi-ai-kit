# Per-skill extraction base — the default is wrong for all 29

**Run:** 2026-08-23, in response to ACTION 2 of the `session-retrospective` reconciliation handoff.
**Finding:** `extraction_base = c05bf72d` is wrong for **29 of 29** extraction-era skills. Not a
majority — all of them.

## Why a single default cannot work

The kit's first commit is **2026-07-02** (`002dadd`). `c05bf72d` is **2026-07-06**, four days later.
Any upstream change landing in that window renders as a phantom kit *deletion*, because the base
already contains work the kit never had. The reconciliation session measured one instance of this
precisely: schema v4 landed upstream in `0ff80065` on **2026-07-05**, three days after extraction, so
diffing against `c05bf72d` presented the entire v4 feature set as a ~1,100-word removal. It was
never removed.

That artifact then propagated into a failed merge, a revert, a "this file is non-mechanical"
conclusion, a scheduled task, a handoff paragraph, and a pin row. **One wrong operand, six
downstream conclusions.**

## Method

For each skill, the probe is its `SKILL.md` **as shipped at the extraction commit** — not at `HEAD`.
Diff that against every upstream revision of the same path; take the minimum-distance commit.

**A first attempt probed `HEAD` and produced noise** — 33 of 33 "differs" with the runner-up 1%
away. After the refreshes, the kit's files resemble *recent* upstream, so a HEAD probe measures
which revision is closest to the refresh, not which one we extracted from. That is the same
wrong-operand error this document exists to correct, committed while correcting it.

Separation is the reliability signal. Where the next-closest revision is far away the base is
certain; where it is 1.0–1.1x the probe cannot discriminate and the row is marked unreliable.

## Result

`dist` = diff lines against the winning revision · `next` = against the runner-up · `ratio` = next/dist.

| Skill | True base | Date | dist | next | ratio |
|---|---|---|---|---|---|
| parallel-deep-research | `3dd2496d` | 2026-06-25 | **0** | — | exact |
| research-source-claim | `3dd2496d` | 2026-06-25 | **0** | — | exact |
| skill-creation-workflow | `3dd2496d` | 2026-06-25 | **0** | 16 | exact |
| skill-content-reviewer | `03a10499` | 2026-03-29 | **0** | 26 | exact |
| skill-researcher | `03a10499` | 2026-03-29 | **0** | 22 | exact |
| ai-improvement-tracker | `03a10499` | 2026-03-29 | 2 | 81 | **40.5x** |
| learning-consolidator | `3dd2496d` | 2026-06-25 | 6 | 50 | 8.3x |
| post-task-review | `3dd2496d` | 2026-06-25 | 2 | 13 | 6.5x |
| task-learnings | `03a10499` | 2026-03-29 | 2 | 13 | 6.5x |
| session-retrospective | `3dd2496d` | 2026-06-25 | 26 | 139 | 5.3x |
| branch-switch | `3dd2496d` | 2026-06-25 | 5 | 18 | 3.6x |
| lemmi-vertical-slice → `vertical-slice` | `3dd2496d` | 2026-06-25 | 12 | 38 | 3.2x |
| spec-driven-dev | `3dd2496d` | 2026-06-25 | 7 | 20 | 2.9x |
| skill-creator | `3dd2496d` | 2026-06-25 | 4 | 11 | 2.8x |
| skill-reviewer | `3dd2496d` | 2026-06-25 | 14 | 33 | 2.4x |
| ai-changelog | `3dd2496d` | 2026-06-25 | 2 | 4 | 2.0x |
| plan-critic | `3dd2496d` | 2026-06-25 | 8 | 15 | 1.9x |
| lemmi-python-conventions → `python-conventions` | `3dd2496d` | 2026-06-25 | 94 | 168 | 1.8x |
| commit-message | `f8ffbab6` | 2026-03-15 | 6 | 9 | 1.5x |
| **— rows below: separation too weak to trust —** | | | | | |
| ai-docs-lookup | `3dd2496d` | 2026-06-25 | 13 | 15 | 1.2x |
| product-brief | `3dd2496d` | 2026-06-25 | 6 | 7 | 1.2x |
| analyze-logs | `3dd2496d` | 2026-06-25 | 10 | 11 | 1.1x |
| lemmi-test-conventions → `test-conventions` | `3dd2496d` | 2026-06-25 | 75 | 78 | 1.0x |
| openai-realtime-quirks | `3dd2496d` | 2026-06-25 | 33 | 34 | 1.0x |

Three prompt skills (`review-prompts`, `prompt-eng-reviewer`, `prompt-domain-reviewer`, base
`9e97fffe`) are omitted from planning use — I1 deleted them.

**Five skills are kit-origin with no upstream path at all:** `kit-setup`, `scout-review`,
`python-conventions`, `test-conventions`, `vertical-slice` (the last three under their pre-rename
names in the table above). Plus, per the port handoff, `orchestrate` and `agent-delegate` originate
here — this repo 2026-07-03, upstream 2026-07-13, byte-identical. **Upstream is downstream for those
two.**

## What W2.4 must do with this

1. **`base` is per-skill, not a default with overrides.** Two overrides was the wrong model; the
   correct count is one base per skill. Twenty-one cluster on `3dd2496d`, but that is a coincidence
   of one consolidation commit touching many paths, not a default.
2. **The five weak rows need a second probe** before their base is trusted — a different file in the
   same skill, or a hunk-level comparison. Do not record a base whose separation is 1.0x.
3. **`direction` still matters** and is unchanged: `kit-origin` for the seven above,
   `upstream-origin` for the rest, `divergent-both` where both sides moved.
4. **A base is a claim with an expiry.** Every one here was derived from upstream's history as of
   2026-08-23. Re-derive, do not inherit.

## Reproduce

The probe is four lines of shell per skill: `git show <extraction>:<kit path>` into a temp file,
then `git diff --no-index --numstat` against `git show <rev>:<upstream path>` for each revision in
`git log --format=%H -- <upstream path>`. Take the minimum. Record the runner-up too — without it
there is no way to know whether the answer means anything.
