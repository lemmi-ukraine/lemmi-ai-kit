# Session handoff to orchestration — I2 W2.4 is done, and the initiative's merge base was wrong

**Dated:** 2026-08-23, at session close.
**Executed:** W2.4 — the recorded upstream pin, the drift check, `docs/syncing-from-upstream.md`,
and the CI report.
**Nothing is committed.** Four checks green: `ruff` · `ruff format` · `basedpyright` ·
`pytest` (185, one of which skips without an upstream checkout).

Companion documents:

| Document | For |
|---|---|
| [2026-08-23-i2-w2-4-completion-review.md](2026-08-23-i2-w2-4-completion-review.md) | the adversarial self-review, including the one claim that did not survive it |
| [2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md](2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md) | W2.2/W2.3, which this wave measures — **its §4 base is refuted below** |
| [2026-08-23-session-retrospective-reconciliation.md](2026-08-23-session-retrospective-reconciliation.md) | the concurrent session that reached the same conclusion independently |
| this file | orchestration |

---

## 1. Status in one table

| Deliverable | State |
|---|---|
| Recorded upstream pin | **Done** — [docs/upstream-sync.toml](../upstream-sync.toml): upstream SHA at the sync point, 38-row correspondence map with the `direction` column, 7-row `[[unported]]` table |
| Drift check | **Done** — `tests/upstream_sync.py`, non-blocking, exits 0 on every path |
| Gates that do not need upstream | **Done** — `tests/test_upstream_sync.py`, 37 new tests |
| CI wiring | **Done** — non-blocking report step, `continue-on-error: true` |
| `docs/syncing-from-upstream.md` | **Done** — 9 sections, including what is deliberately not ported and the promotion criteria for both gates |
| Charter DoD 5 and 6 | **Met.** DoD 7 re-verified. DoD 1–4 untouched — no asset edited, no allowlist entry added |

First run against a real upstream checkout: **one skill behind** — the one independently
known to be deferred — with **0** map errors, **0** undeclared upstream skills and **0**
vanished rows across the other 35.

## 2. What a re-planner must not assume — the base is wrong, and it cost content

**Do not plan any further refresh against upstream `c05bf72d` (2026-07-06).** The kickoff
named it, the charter names it, W2.2/W2.3's §4 measured against it. It is four days *inside*
this repo's extraction window: the first kit commit is **2026-07-02T23:26**, and three
upstream commits land in the gap.

| Measured at review time | Value |
|---|---|
| True base — last upstream skills commit before this repo's first | **`3dd2496d`**, 2026-06-25T21:39 |
| Insertions in the gap | **2,668** across 16 skill directories (15 shipped, 1 declined) |
| Of those, the two linters + tests the kit deliberately does not ship | 1,024 |
| **Skill content the wrong base could not distinguish from this repo's own deletions** | **1,644** |

**Why this is not merely an inaccurate number.** The three-way rule reads *present at base,
absent in ours, present in theirs* as a deliberate kit deletion — **keep it deleted**. All
1,644 lines are present at the too-new base, so every one was eligible to be classified that
way and dropped with nothing objecting. The carry audit that certified W2.2 used the same
base, so it could not have caught this either. **A wrong base launders upstream content into
"our deliberate divergence."**

**Spot-checked, not asserted:** all **19** window-added lines of `skill-researcher/SKILL.md`
are absent from the shipped file, and that skill reports **zero** drift against the pin. Some
are correctly absent (they carry source-project rules) — which is why clearing this needs a
per-skill read, not a bulk re-merge.

Corroborated independently: the concurrent `session-retrospective` session reached the same
base by minimum-distance selection (9 diff-lines at the true base against 271 at the
next-closest), and found the charter's "~1,100-word uncharacterized removal" was this same
artifact — upstream added schema v4 on 2026-07-05, three days after extraction. Based
correctly, that merge yields 3 conflicts instead of 13.

The record now uses the true base and carries an `[extraction_window]` table; the report
surfaces the debt as its own finding rather than folding it into drift.

## 3. Decisions now owed — none of them mine

| # | Decision | Why it is not a session call |
|---|---|---|
| **W-window** | **New work item, not in the charter: clear the extraction-window debt.** 15 shipped skills, 1,644 insertions, per-skill portability reads. Needs an owner and a wave slot | It is a content refresh across `assets/skills/`, sized like a wave, and it exists only because W2.2's base was wrong. Whether to fund it, defer it, or accept the loss is a scoping call |
| **W-gate** | Promote the drift check from report to gate? | Three of four criteria are open (§7 of the procedure doc). One of them — *CI needs a way to reach an upstream checkout* — is infrastructure the operator controls. Promoting before that turns `NOT MEASURED` into a green pass, which is the worst available outcome |
| **W-audit** | Promote `audit-skills --fail-on major`? | Re-measured this session: **all five** findings still open (3 MAJOR, 2 MINOR), all inside `assets/skills/`. Not promotable yet, and clearing them belongs to whoever owns that tree |
| **W-retro-row** | One owed test edit when the `session-retrospective` reconciliation commits (§5) | It is a deliberate alarm, not a defect, but it lands in a file that session does not own |

## 4. The defect worth propagating to other sessions

**Building a measurement honestly can refute the premise it was told to measure against.**
The kickoff gave me the base as settled — *"Compare three-way against the extraction-point
merge base (upstream at 2026-07-06)"* — and two prior documents had already used it. I found
it wrong only because writing `extraction_base` into a validated file forced me to state what
the field *means*: "the last skills-tree state at or before the extraction window." Writing
that sentence made the date comparison unavoidable.

**Transferable rule: when you record a constant, write down the property that makes it the
right constant. A pin with a definition is checkable; a pin with a provenance story is not.**

Second, smaller, and the same shape as W2.2's `lemmi-ai-kit <sub>` finding: **a check that
cannot fail is not a check.** `git rev-list --count` over a path that does not exist returns
0, so a single typo in an `upstream` name would have reported "in sync" forever while
measuring nothing. That is why the report has a `MAP ERROR` finding, and it is the piece I
would restore first if any of this were cut.

## 5. Cross-session notes

**I edited `.github/workflows/ci.yaml`,** which was outside my declared ownership
(`tests/`, `docs/syncing-from-upstream.md`, the pin file). DoD 5 requires the check be
"wired into CI," so the deliverable could not be met without it. It is an 18-line addition
at the end of the job — one step plus its rationale. Nothing else in the file changed.

**One owed edit when the `session-retrospective` reconciliation commits.** Simulated it:
exactly one test goes red, `test_base_overrides_are_the_unsynced_skills`, and its failure
message names the fix. The edits are:

1. `docs/upstream-sync.toml` — on the `session-retrospective` row, delete the `base` line and
   change `direction` to `upstream-origin`.
2. `tests/test_upstream_sync.py` — in `test_base_overrides_are_the_unsynced_skills`, change
   the expected set from `{"session-retrospective"}` to `set()`.

Both belong in the same commit as the reconciliation. I deliberately did **not** pre-apply
them: that session's work is uncommitted, and if the record claimed the skill reconciled
while the work did not land, the check would report "in sync" for a skill ten commits behind
— a silent false negative. Claiming it behind and being wrong produces a loud false positive
instead, which somebody investigates. **Pick the error that fails loudly.**

I also found and removed two tests of my own that would have punished the fix rather than
flagged it: one required `divergent-both` to always have a member (so reconciling the last
such skill would fail a test), and one named `session-retrospective` specifically. Both are
now structural. The remaining pinned assertions are deliberate alarms, in the same spirit as
the vocabulary-pinning tests OD-2 ruled must not be routed around.

**I clobbered a concurrent memory update and restored it.** The shared memory file for the
merge base was rewritten by the other session between my read and my write; I overwrote their
body. Recovered the substance from their research document — the minimum-distance method —
and merged both findings, then credited the method in §3c of the procedure doc, which had
told a maintainer to use a per-skill base without saying how to establish one. **Re-read a
shared file immediately before writing it, not once at session start.**

## 6. Verification, and where it stops

**Done:** every SHA re-resolved with dates and ancestry; kit-origin byte-identity re-confirmed
(6,775 and 3,153 bytes); `scout-review`'s absence from all upstream refs verified rather than
assumed; the correspondence map resolved live against real upstream (0 errors across 36 rows);
the recorded window list re-derived from git independently and matched 16/16; window arithmetic
recomputed insertions-only (1,644 exactly, not "roughly" as first published); the
correspondence gate mutation-tested by deleting a row; the hygiene contract applied to all five
of my files by *importing* the compiled patterns (two violations found in my own comments,
fixed by rewriting rather than allowlisting); the CI workflow parsed and its step command run;
scaffold no-regression re-checked.

**Where it stops, stated plainly:**

- **The check cannot run in CI.** Upstream is private and absent, so the step's normal output
  is `NOT MEASURED`. That line is printed so the absence is visible rather than silent, and
  everything not needing upstream is gated instead. `NOT MEASURED` is not a pass.
- **Window exposure is measured in commits, spot-checked in one file.** How much of the 1,644
  lines is actually missing from the pack is unknown. In the one skill checked it was all of it.
- **The 82 deliberately-dropped lines from W2.2 are classified in prose but not enumerated
  anywhere machine-readable.** A maintainer wanting to revisit one has no list.
- **Drift is counted in commits, so it cannot size work.** It answers "has upstream moved",
  never "how much is this".
- **I did not read the 38 skills.** Nothing in this wave required it, and nothing in it claims
  otherwise.
- **`sweep_user_corrections.py`** still has no portability read and now exists untracked.

## 7. Sequencing recommendation

1. **Commit the `session-retrospective` reconciliation with the two edits in §5.** It is the
   only thing coupled to an uncommitted state, and the coupling gets more confusing with age.
2. **Then commit this wave.** Suggested boundaries, since the pieces are different classes:
   the pin plus the procedure document (reviewed prose), then the check plus its tests
   (reviewed code), then the CI step alone. `assets/manifest.toml` is untouched, so no commit
   here can strand the tree.
3. **Put W-window to the operator before any further refresh work.** Every skill refreshed
   against the old base is potentially carrying the same defect, and the number is measured
   now rather than estimated later.
4. **Leave both gates as reports.** The criteria are written down; three of four are open for
   the drift gate and all five findings are open for the audit gate.
5. `usage-guard` stays deferred. Unchanged this session.
