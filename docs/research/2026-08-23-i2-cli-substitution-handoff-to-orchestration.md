# Session handoff to orchestration — I2 Gate B option (c) is done

**Dated:** 2026-08-23, at session close.
**Executed:** the **(c)-substitute** half of Gate B decision D2 — complete.
**Not touched:** the (a)-ship half, W2.2 refreshes, W2.3, W2.4.
**Nothing is committed. Nothing is pushed.** Four new files, one modified.

This is the orchestration-side handoff: what moved, what it unblocks, what decisions are
now owed, and what a re-planner must not assume. The execution detail is in the companion.

| Document | For |
|---|---|
| [2026-08-23-i2-cli-substitution-handoff.md](2026-08-23-i2-cli-substitution-handoff.md) | **Session D** — §3 is the call-site rewrite table |
| [2026-08-23-i2-cli-substitution-completion-review.md](2026-08-23-i2-cli-substitution-completion-review.md) | whoever reviews this work — 8 findings against my own implementation, all fixed |
| this file | orchestration |

---

## 1. Status in one table

| Gate B decision | Half | State |
|---|---|---|
| **D2 (c) substitute** — cross-skill calls become CLI subcommands | `lint`, `audit-skills` | **DONE**, tested, gate green |
| **D2 (a) ship** — skill-owned scripts arrive with their skills; 14 same-skill sites rewritten to `${CLAUDE_SKILL_DIR}` | — | **not started** — Session D's, and none of it blocked on me |
| **D1** — ship the stacked-PR document | — | landed independently (`assets/ai/git-stacked-pr-workflow.md` is on disk) |
| D3 (no hooks story), D4 (defer `usage-guard`), D5 (correspondence map), D6 (refresh order) | — | untouched by this session |

**Deliverables:** `src/lemmi_ai_kit/checks.py` (1,440 lines), `tests/test_checks.py`
(1,333 lines, 104 functions / 109 cases), `src/lemmi_ai_kit/cli.py` (+216/−2), plus the
three documents above.

## 2. What this unblocks, and for whom

**Session D, immediately.** Ten cross-skill call sites across eight skills can now be
rewritten to a shipped command instead of stripped or left dangling — the table is the
companion's §3. Three of those are **already dangling in the shipped tree**:
`parallel-session-safety` landed mid-session citing `ai_files_lint.py` three times, and two
of those are executable forms that DoD item 4 forbids. `lint handoffs` exists specifically
so they can be rewritten rather than stripped.

**DoD item 4 moves from blocked to achievable.** The charter's durable guarantee — *"zero
references to infrastructure the kit does not ship"*, enforced by extending the hygiene
contract with the `ai_files_lint` and `audit_skills` patterns — could not be written while
those were the only names for the behaviour. There is now a shipped command to point at, so
the pattern can be added once the rewrites land. **I did not add it**: `tests/test_assets.py`
is Session D's file this whole session, and adding the pattern before the rewrites would red
the gate on their in-flight work.

**DoD item 5's CI report has something real to gate on.** `--fail-on` exists because
upstream's audit always exits 0, which makes the existing self-review gate that cites
"`audit_skills.py` exit 0" vacuous. W2.4 can wire `audit-skills --fail-on major` as a
non-blocking report and promote it later, which is the charter's prescribed shape.

## 3. Decisions now owed — none of them mine

**OD-1 — the audit reports 5 findings against the kit's own pack. Fix or drop?**

```
MAJOR  ai-docs-lookup      metadata.type missing
MAJOR  kit-setup           metadata.type missing
MAJOR  initiative-cleanup  SKILL.md 556 lines > 500
MINOR  ai-docs-lookup      README.md in the skill directory
MINOR  test-conventions    README.md in the skill directory
```

All true positives, verified by hand. Two skills carry no `metadata.type` while 34 do — so
either it is a kit requirement and those two are defects, or it is not and the check is
permanent noise that should come out. `initiative-cleanup` arrived this session already over
the 500-line cap its sibling skills teach. **Nothing is gated on this** (`--fail-on` defaults
to `none`), so it is not urgent — but it decides whether W2.4 can promote the audit to a
gate at all. **The count moved once while I worked** (`test-conventions` gained a type mid-session):
re-run the command, do not quote the block.

**OD-2 — the vocabulary pinning will fire during W2.2, by design.** Five tests assert that
the lint's taxonomies match what `ai-changelog`, `task-learnings`, `ai-improvement-tracker`,
the hypotheses seed and `parallel-session-safety` document — **in both directions**. All four
skills are in the refresh set, and upstream has already added a 12th changelog type and a
seventh learnings category. **When a refresh lands, these tests fail and that is correct
behaviour**: they name the constant and the file, and the fix is a one-line edit to
`checks.py`. Brief whoever does W2.2 that a red pinning test is the drift alarm working, not
a broken test to route around. This is the closest thing in the initiative to a working
drift detector, and it arrived early and by accident of scope.

**OD-3 — `handoffs` as a lint target expands D2's scope slightly.** The triage counted 15
cross-skill sites and did not count `parallel-session-safety`, whose references are bare
mentions rather than hard-coded paths. Supporting `handoffs` was my call, made because the
skill shipped mid-session with dangling references and stripping them was the one option the
decision rules out. If orchestration disagrees, the target is removable — but the three
references then need another answer.

## 4. What a re-planner must not assume

- **The charter's "15 cross-skill sites" and the triage's "9 of 14" are both slightly off.**
  The executable count for these two scripts is **10**, not 9: `session-retrospective` has
  two sites, not one. Neither figure changes any decision; both will mislead a count.
- **`lint` does not cover everything upstream's script does.** Out of scope by design, with
  reasons in the companion §5: `check <patterns.txt>` (a same-skill call, so (a) not (c)),
  `lint plans` (`.specs/` execution plans — no shipped contract yet), the hypotheses archive
  lint, and the buffer/synthesis pressure notes. `drain_audit.py`,
  `test_ai_files_lint.py` and `validate_realtime_export.py` remain unaddressed, exactly as
  the triage's own "9 of 14" implies.
- **`--since` replaces upstream's hardcoded cutoff *and* `--all-entries`.** Any plan that
  says "port the policy cutoff" is describing something deliberately not shipped.
- **Three upstream rules were dropped as project policy, not portable rules** (companion
  §4). A future sync will show those as diffs. They are correct diffs.

## 5. Verification, and where it stops

**Four checks at close:** `ruff check` clean · `ruff format --check` clean · `basedpyright`
0 errors · `pytest` **147 passed, 1 failed**.

**The one failure is not mine and is worth reading as a result rather than noise.**
`test_assets_have_no_contamination` fails on `skills/branch-switch/SKILL.md:46`, on the
pattern the contract labels *source-project backup reference*, which Session D's refresh of
that skill re-imported from upstream.
**The hygiene contract caught an upstream refresh re-importing a banned pattern, live.**
That is the mechanism this whole initiative is built to install, firing on its first real
refresh. It is Session D's line to fix. My 109 tests and the other 38 all pass.

**This session's own numbers moved four times under me.** The pack went 33 → 36 skills and
the manifest was out of sync for most of the session, which red-gated every manifest-reading
test until Session D synced it. Nothing I built depends on the manifest — the audit treats an
unreadable catalogue as *unknown*, not empty — but any figure in these documents is a
close-of-session snapshot on a moving tree.

**Where verification stops, stated plainly:**

1. **macOS and Linux are unrun.** The cross-platform work (BOM, CRLF, case-exact `SKILL.md`,
   ASCII output) is designed and unit-tested, on Windows only. Same limitation W2.1 recorded.
   CI settles it on the first PR.
2. **No mature `.ai/` corpus was available.** The lint runs against the shipped seeds and
   against the format shapes the skills document. It has never seen months of real entries.
   The completion review names this as where the next false positives live.
3. **The completion review found 8 defects in my own work after the suite was green** — three
   false-positive classes, one false negative, four quality issues. All fixed and tested. The
   generalisable lesson is in that document's §1, and it is worth carrying to any other
   checker this program builds: **fixtures written by the checker's author are the weakest
   possible corpus, because the author writes conforming inputs.**

## 6. Sequencing recommendation

Per the charter's own note, this is **reviewed code, not journal-class content** — it belongs
in its own commit layer, not folded into Session D's skill-content commits. Concretely:

1. **This layer first, alone:** `checks.py`, `test_checks.py`, `cli.py`, the three documents.
   It is additive — no shipped asset changes, so it cannot conflict with the refreshes.
2. **Then Session D's rewrites**, which depend on this being present to point at.
3. **Then the DoD item 4 hygiene pattern**, once no dangling reference remains — adding it
   earlier reds the gate on work in flight.

Two loose ends I left rather than take, both in files another session held all day:
`README.md:114`'s module list omits `checks.py`, and `CONTRIBUTING.md:66` still says "Nine
patterns" against a contract that carries ten. Neither is covered by a test; both are
one-line edits for whoever owns those files next.
