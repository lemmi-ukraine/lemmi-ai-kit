# Session handoff to orchestration — W-window is sized, and a guard the plan relies on cannot fire

**Dated:** 2026-08-23, at session close.
**Executed:** the read-only W-window measurement, per the operator's ruling *"I4 next; measure
W-window beside it"*, plus its adversarial completion review.
**Nothing is committed** — the operator's standing choice, unchanged this session. Four checks green:
`ruff check` · `ruff format --check` · `pytest` (184 passed, 1 skipped).
**Footprint:** two files added under `docs/research/`. No skill, test, pin, manifest or workflow was
touched.

Companion documents:

| Document | For |
|---|---|
| [2026-08-23-extraction-window-debt-measured.md](2026-08-23-extraction-window-debt-measured.md) | the measurement, the per-skill work list, the instrument |
| [2026-08-23-extraction-window-debt-completion-review.md](2026-08-23-extraction-window-debt-completion-review.md) | the self-challenge — **three of my published results were wrong before they were right** |
| [2026-08-23-i2-w2-4-handoff-to-orchestration.md](2026-08-23-i2-w2-4-handoff-to-orchestration.md) | W2.4, which opened this debt as `status = "unreviewed"` |
| this file | orchestration |

---

## 1. Status in one table

| Item | State |
|---|---|
| **W-window measurement** | **done.** Read-only, ran beside I4's tree without touching it |
| Debt size | **13 exposed skills, 599 lines absent (85% of their window content)** |
| Scope concentration | **3 skills recover 60%, 6 recover 84%.** Two of the 15 need nothing |
| `[extraction_window] status` in the pin | **still `"unreviewed"`** — deliberately not edited, see §5 |
| New finding, not in any charter | **the vocabulary pins cannot detect upstream loss**, with a measured instance |
| Blocker on I4 | **unchanged** — G's six files still uncommitted in `assets/skills/` |

## 2. What a re-planner must not carry forward from my own first draft

**Do not use "1,644 lines across 15 skills" or "44% loss."** Both are mine, both were published
earlier today, and both are wrong in the direction of sounding milder.

Two of the 15 skills were never exposed to the wrong base, and they hold **half the population**:
`hypothesis-validator` was a **fresh W2.3 port** (first in the kit 2026-08-23, never merged against
any base) and `session-retrospective` was merged against the **true** base. Together: 713 of 1,417
lines at a 3% loss rate, averaged in with skills that lost nearly everything.

| | Skills | Window lines | Absent | Loss |
|---|---:|---:|---:|---:|
| **Exposed — plan against this** | **13** | **704** | **599** | **85%** |
| As first published | 15 | 1,417 | 623 | 44% |

**The debt is narrower in scope and roughly twice as severe inside it.** And 85% is a floor: the
"carried" figure is built from positive matches on short strings, 254 of which are one- or two-token
lines that match anywhere. Every weakness in it makes the debt larger.

**A trap on the same check.** `python-conventions` and `test-conventions` also report a 2026-08-22
first appearance and look identical to fresh ports. They are **renames**, traced to the `002dadd`
initial release, and they are exposed. `--diff-filter=A` on a path answers "when did this path
appear", not "when did this skill appear" — misreading it moves 68 genuinely-lost lines into the
safe bucket.

## 3. Decisions now owed — none of them mine

| # | Decision | Why it is not a session call |
|---|---|---|
| **W-window** | **Now sized: fund 3 skills, 6, or none.** `skill-creator` (119), `learning-consolidator` (114), `skill-reviewer` (102) recover 60%; adding `python-conventions` (52), `skill-creation-workflow` (45), `ai-improvement-tracker` (37) reaches 84%. The remaining 7 exposed skills hold 91 lines between them | Scoping and funding. The measurement is done; what to buy with it is not a session call |
| **W-gate** | **A fourth blocker exists that W2.4's criteria do not name:** no check in this repo compares a taxonomy to upstream, and one is measurably wrong right now (§4). Promoting the drift check would promote a suite that is green over a known content loss | The criteria list is the operator's, and this adds to it |
| **W-taxonomy** | **Restore `EXPERIMENT-REGISTERED` now, or fold it into W-window?** It is a content fix in `assets/skills/` plus `checks.py`, so it is serial against I4's restructure either way | It is a scope call with an ordering consequence, and it collides with the initiative in flight |
| **The commits** | G + its two coupled edits, then F. **Still the only thing blocking I4** | Left uncommitted by explicit operator choice today; I did not revisit it |

## 4. The finding worth propagating to other sessions

**A pin whose two operands both come from your own tree measures consistency, not fidelity.**

Every vocabulary pin in `tests/test_checks.py` asserts *shipped doc == kit constant*. None consults
upstream. So a refresh that drops a taxonomy member from **both** sides leaves every pin green.

Measured, not hypothesised:

| | Count |
|---|---:|
| Change types in upstream's table at the pin `a78ee5af` | **12** |
| Rows in the shipped `ai-changelog` table | **11** |
| Members of `checks.CHANGELOG_TYPES` | **11** |
| Occurrences of `EXPERIMENT-REGISTERED` in `src/lemmi_ai_kit/` | **0** |
| Test suite | **184 passed — green** |

`test_changelog_types_match_the_shipped_skill` is the test whose job this is, and it passes because
both operands lost the member together. It is one of five pins sharing that design.

This matters beyond the one taxonomy. **OD-2 ruled these pins must not be routed around, and two
handoffs treat them as the drift alarm for taxonomies — they cannot raise this class of alarm at
all.** They are still worth keeping for the doc-vs-code drift they were built for. The gap is cheap
to close: the pin tests already parse the shipped side, so a third operand read from an upstream
checkout is a small addition, gated the same way W2.4's drift check is when upstream is absent.

Second, smaller, and the same family: **an outlier that contradicts your mechanism is either a
refutation or a second population — find out which before averaging it in.** `hypothesis-validator`
carried 89% against a story that predicted near-total loss. Treated as noise it would have stayed in
the denominator and halved the headline. It was the control group.

## 5. Cross-session notes

**I edited nothing outside `docs/research/`.** Two files added; `git status` is otherwise byte-for-byte
what it was at session start (18 entries → 20).

**Two edits owed, both deliberately not made:**

1. `[extraction_window] status` in `docs/upstream-sync.toml` should move off `"unreviewed"` and point
   at the measurement. That file is part of W2.4's **uncommitted** work and the operator has left it
   uncommitted; editing it would entangle my result with a work set someone else still owns.
2. A row in `docs/research/README.md` for each of my two documents. Same reason — that index is
   also uncommitted W2.4 work.

**Input to I4's plan, since it will be written against `assets/skills/`.** Three separate bodies of
content work now queue behind the restructure, and the I4 kickoff's own rule — *anything touching
`assets/skills/` is serial against the restructure* — applies to all three:

- Session D's **five audit findings** (four are content fixes; F re-measured all five still open)
- **W-window**, 599 lines across 13 skills, of which 3 skills carry 60%
- **`EXPERIMENT-REGISTERED`**, one taxonomy member across two skills plus `checks.py`

None of them blocks I4. All of them are serial against it, and the restructure moves every path they
touch — so whoever plans I4 should decide whether these land before the move or after it, not
discover the collision mid-wave.

## 6. Verification, and where it stops

**Done:** both of W2.4's arithmetic anchors reproduced exactly (numstat 2,668; the three unshipped
scripts 453+229+342 = 1,024); its single spot-check reproduced independently (`skill-researcher`
19 added, 19 absent); the absent count re-derived under four matching rules (623 / 623 / 615 / 580)
and again directory-wide (623, **0** relocated); my own punctuation hypothesis tested and **refuted**
(0 of 623 recovered); the exposure split established from kit git history rather than assumed; the
two renamed skills traced to the initial release rather than misclassified; the taxonomy loss
confirmed by three independent counts plus a zero-hit package grep; the pin family enumerated from
source; four checks green.

**Where it stops, stated plainly:**

- **The portable / correctly-stripped split is unmeasured.** 599 is an upper bound on recoverable
  content, not a work estimate. Mechanical markers explain only 34 of it. `learning-consolidator`'s
  reference files are heavily `backend/app/`-bound and will shed far more; `skill-creator` and
  `python-conventions` will shed close to nothing. **Nobody has read them.**
- **`task-learnings` is unexplained.** Exposed, yet carried 66% where its exposed peers carried near
  zero. My pinning-test explanation was tested and is wrong. It is the one row that weakens the
  mechanism and I did not chase it further.
- **Line-level, not semantic.** A rewritten-but-equivalent paragraph counts absent below the fuzzy
  threshold, and that pass recovered only 35 lines.
- **It measures the working tree**, which holds two uncommitted sessions — which is why
  `session-retrospective` reads reconciled here while the pin records it behind.
- **No test guards any of these numbers.** They live in a document. W2.4's report re-derives the
  affected *list* but neither the exposure nor the loss.
- **I did not read the 38 skills.** Only the 16 window directories, and only their window lines.

## 7. Sequencing recommendation

1. **Commit G with its two coupled edits, then F.** Unchanged from both prior handoffs, and still
   the only thing standing between the tree and I4. It gets more confusing with age, and my
   measurement now depends on the working-tree state to read correctly.
2. **I4 next**, per today's ruling. Give its planner §5's three-item collision list as an input.
3. **Close the pin-vs-upstream gap before promoting either gate.** It is small, it is in `tests/`
   (nobody's contended path once F commits), and until it exists the suite is green over a measured
   loss.
4. **Fund W-window at three skills, not fifteen**, and do it as a three-way re-merge against
   `3dd2496d` rather than a hand-restore — `session-retrospective` reached 98% carriage that way and
   is the evidence the method works.
5. `usage-guard` stays deferred. Unchanged.
