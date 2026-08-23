# Session handoff to orchestration — `session-retrospective` is merged; D-retro is closed

**Dated:** 2026-08-23, at session close.
**Executed:** the D-retro reconciliation from
[2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md](2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md) §5.
**Not committed. Nothing pushed.**

Companion documents:

| Document | For |
|---|---|
| [2026-08-23-session-retrospective-reconciliation.md](2026-08-23-session-retrospective-reconciliation.md) | the measurement and the merge |
| [2026-08-23-session-retrospective-completion-review.md](2026-08-23-session-retrospective-completion-review.md) | the self-challenge — **three of my own results were wrong before they were right** |
| this file | orchestration |

---

## 1. Status in one table

| Item | State |
|---|---|
| **D-retro — `session-retrospective` reconciliation** | **done.** Schema v3 → v4, merged three-way against the true base |
| The "~1,100-word uncharacterized removal" | **refuted.** It never happened — artifact of a base four days too new |
| §5's "the mechanical merge is proven insufficient" | **refuted.** Against the right base the extractor merges with **0 conflicts** |
| `sweep_user_corrections.py` (the §7 loose end) | **read for portability and ported**, one edit |
| W2.4 pin correction | **already adopted by that session** — see §4 |

**Measured:** the skill is 9,025 → **18,120 words**, 5 → **6 files**. Pack unchanged at **38 skills**,
~158,900 words. Four checks green on the full tree — `ruff` · `ruff format` · `basedpyright` ·
`pytest` **183 passed, 1 skipped** — plus the skill's own **35 passed** (v3 baseline was 15).

## 2. What this unblocks

- **The last deferred skill is no longer deferred.** W2.2 is 26 of 26. The pack ships upstream's
  v4 retrospective pipeline: deterministic deep-dive selection (replacing model-side arithmetic),
  slash-command capture, per-session model and compaction counts, the `--check-file` privacy gate,
  and the date pre-scan.
- **W2.4's correspondence map has its hardest row settled**, with a `base` that is measured rather
  than assumed, and a method for finding the others (§3).
- **The §5 blocker is gone as a scheduling item.** Nothing about this file is expensive; it was
  expensive to *believe*.

## 3. The finding a re-planner must carry — `extraction_base` is a default, not the base

The refresh used one base for every skill, `c05bf72d` (2026-07-06). That commit sits **inside** the
extraction window (kit commits 2026-07-02..07-09), so for any skill extracted before it, it is too
new — and a too-new base renders genuine upstream advances as kit deletions.

For this skill: the kit extracted on **2026-07-02**; upstream added schema v4 on **2026-07-05**.
Diffing from `c05bf72d` therefore showed the entire v4 feature set as ~1,100 removed words. It was
never removed. The kit's real edit set against its true base (`3dd2496d`, 2026-06-25) is **four
hunks, ~13 words** — three dated-citation scrubs and one platform generalisation.

That single wrong operand produced, in order: a failed merge, a revert, a "this file is
non-mechanical" conclusion, a scheduled reconciliation task, a paragraph in a handoff, and a row in
the W2.4 pin. **None of it was a content problem.**

**The mechanical fix, which needs no judgment:** for each skill, diff the shipped file against
*every* upstream revision of that path and take the minimum-distance commit.

```bash
for c in $(git -C <upstream> log --reverse --format=%h -- "$P"); do
  echo "$c $(git -C <upstream> show "$c:$P" | diff - <shipped> | grep -c '^[<>]')"
done
```

Here it returned 9 diff-lines at `3dd2496d` against 271 at the next-closest, and agreed
independently across all five files. Run it for every skill before trusting a `base`.

This is §4 of the prior handoff — *a two-way diff cannot separate an upstream advance from a
deliberate kit removal* — recurring one level down, in the choice of base itself. §4 predicted two
per-skill overrides; this is a third, and it was misdiagnosed as a content problem for a session.

## 4. Cross-session note — the W2.4 pin, and a coupling before commit

W2.4 landed in the shared checkout while I worked. **That session has already adopted this
finding**: `docs/upstream-sync.toml` now records
`base = "3dd2496d874552d6acaac3de6095abc4ec68c2b0"` for this skill with a corrected note. I did not
edit their file.

**The coupling whoever commits must honour:** their row says *"A reconciliation of this skill was in
flight when this record was written — when it lands, drop this row's `base` override and its
`divergent-both` direction."* That is now true. My merge brings the skill to upstream `a78ee5af`
modulo the kit's portability edits, so after it commits the row is stale in two ways — the override
has served its purpose, and the direction is no longer divergent.

**Commit these together, or the pin describes a state that no longer exists.**

## 5. The defect worth propagating

**A reachability test with no failing control is not a test.** I rewrote five call sites to the
plugin-reachable CLI form and verified them by running the commands. They passed — from the
development venv, where the package is installed and the console script is on `PATH`. That
environment satisfies *every* form of the invocation, **including the unreachable console-script
form the prior session had just deleted from 16 call sites**. The test could not have failed.

Re-run on a clean interpreter with two controls (package not importable; console script absent),
both forms are genuinely reachable — but the first result was worth nothing.

This is the prior handoff's §6 rule — *check a named command against the install path the adopter
actually uses, not the one the developer has* — violated while checking a named command. **Being
documented did not prevent it**, because the defect is a property of the default `PATH`, not of
attention. If W2.4's drift check ever verifies invocations, it must run them somewhere the package
is absent, or it will certify the same defect green.

Two further self-inflicted measurement errors — a shell pattern that collapsed to empty, and a
`subprocess(text=True)` diff that mangled em-dashes and reported **176** dropped lines where **14**
were real — are in the completion review §2. Both were caught by the number's shape, not by
inspecting the tool.

## 6. Verification, and where it stops

**Done:** three-way merge against the measured base (extractor, tests, and schema doc at 0
conflicts; 3 prose conflicts hand-resolved keeping both sides); a carry audit showing **99.0% of
upstream's 1,336 added lines carried verbatim, 14 rewritten, 0 dropped** — all 14 my own
substitutions; 27 of 29 kit-side edits verbatim with both exceptions accounted; upstream's and the
final file's `SKILL.md` heading sets identical; the DoD-4 guards re-run **by importing** the
compiled patterns with the real allowlist (all 6 merge-introduced hits fixed, 5 residual are
pre-existing allowlisted fixtures); an **end-to-end run over 15 real transcripts** with every v4 key
populated and `SELF-CHECK PASSED`; the `--check-file` gate exercised in both directions (exit 3 on
an in-gate shape); the wheel built and all six files confirmed inside it.

**Where it stops, stated plainly:**

- **I did not human-read `SKILL.md` end to end** (493 lines). Confidence is mechanical. A prose
  regression that is portable and syntactically clean would not have been caught.
- **The vocabulary-pinning tests were never the alarm here.** They pin `ai-changelog` and
  `task-learnings`, not this skill. Green is not evidence its taxonomy is unchanged — that was
  verified separately by import (`ERROR_CATEGORIES` identical across v3, final, and upstream).
  **If this skill's taxonomy deserves a pin like the other three have, it does not have one, and I
  did not add it.**
- **`sweep_user_corrections.py` has no tests.** Upstream ships none either — inherited, not
  introduced. Smoke-run only.
- **The Python 3.11+ floor is asserted from code, not tested.** Runs happened on 3.11 and 3.13; no
  3.10 run proves the failure.
- **Prose generalisation remains unmeasured**, as every prior report in this initiative has said.

## 7. Sequencing recommendation

1. **Commit this together with the W2.4 pin row edit** (§4). They are coupled; separately, one of
   them lies.
2. **Run the minimum-distance base check across all 38 skills** (§3) before W2.4's drift report is
   trusted. It is cheap, mechanical, and this session is the proof that a wrong `base` is not a
   cosmetic error — it cost a session and produced a fictitious finding that reached two documents.
3. **F9, then the push**, unchanged from the prior handoff — still the only irreversible decision
   on the board, and now with three more `docs/research/` files in scope for it.
4. `usage-guard` stays deferred.
