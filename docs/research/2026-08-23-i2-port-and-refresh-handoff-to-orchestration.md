# Session handoff to orchestration — I2 W2.2/W2.3 are done; the pack is 38 skills

**Dated:** 2026-08-23, at session close.
**Executed:** the ports (W2.3) and the refreshes (W2.2), plus the DoD-4 guards.
**Merged to `main`** in five commits, each independently green. **Nothing is pushed.**

Companion documents:

| Document | For |
|---|---|
| [2026-08-22-i2-portability-triage.md](2026-08-22-i2-portability-triage.md) | the per-skill verdicts this session executed — §12 corrections extended below |
| [2026-08-23-i2-cli-substitution-handoff.md](2026-08-23-i2-cli-substitution-handoff.md) | the CLI half; **carries a correction added by this session — read it before using its §3 table** |
| this file | orchestration |

---

## 1. Status in one table

| Wave | State |
|---|---|
| **W2.2 — refresh the shared skills** | **25 of 26 done.** `session-retrospective` deliberately not refreshed |
| **W2.3 — add the portable new skills** | **8 ported.** The 6 planned, plus `consolidation-critic` and `hypothesis-validator` once the CLI landed mid-session |
| **W2.1b — stripped-invocation guard** | already landed before this session; extended (see §3) |
| **Gate B D2 (a) — ship skill-owned scripts** | **done**, with one deliberate departure (§4) |
| **W2.4 — drift detector, pin, sync procedure** | **not started.** Still owed: the recorded upstream revision, the CI drift report, `docs/syncing-from-upstream.md` |

**Measured:** 29 → **38 skills**, 75,296 → **149,925 words**. Four checks green (`ruff` · `ruff format` · `basedpyright` · `pytest` 148). 38 skill directories = 38 manifest entries = README's stated count.

## 2. What this unblocks, and for whom

- **I3 can advertise real capability.** The pack now ships the four skills this program runs on (`initiative-planner`, `orchestrate`, `stacked-pr-planner`, `plan-critic`) plus the PR-review chain. The charter's "the kit stays unable to host its own development" is closed.
- **I4 splits a current pack, not a stale one.** All four already-renamed skills (`orchestrate`, `python-conventions`, `test-conventions`, `vertical-slice`) are refreshed and carry no *dangling* pre-rename references. One deliberate mention remains: `skill-reviewer` cites the old `fable-orchestrate` name as the measured case study that justifies its name-neutrality rule (zero invocations across 47 sessions until renamed). That file teaches the rule, so the name stays.
- **W2.4's hardest input exists.** The correspondence problem is now concrete: the refresh set is not name-derivable (§4), and two skills travel the *other* direction.

## 3. Decisions now owed — none of them mine

| # | Decision | Why it is not a session call |
|---|---|---|
| **D-push** | Push `main`? It is **40+ commits ahead** of a remote last updated 2026-07-09 (the exact count moves with each commit; `git rev-list --count origin/main..main` is the live figure) — this repo has not been pushed since extraction | Program item **F9** (whether `docs/research/`'s internal handoffs should greet the first public visitors) is still marked *open, judgment*. Pushing settles F9 by accident. Resolve F9 first; it is the cheaper order |
| **D-retro** | Schedule the `session-retrospective` reconciliation | It is no longer a port. See §5 — the mechanical merge is proven insufficient, and the charter names the revised first step |
| **D-usage-guard** | `usage-guard` remains deferred per triage D4 | Unchanged this session |
| **D-w24** | W2.4's pin format and whether the drift check gates or reports | Charter DoD 5 says non-blocking report first. Untouched |

## 4. What a re-planner must not assume

**Do not plan the remaining refresh work from the charter's or the triage's word gaps.** Both measure kit-vs-upstream, which **cannot distinguish an upstream advance from a deliberate extraction edit** — the two are indistinguishable in a two-way diff. Measured against the real merge base (upstream at the extraction point, 2026-07-06):

| Assumption | Measured |
|---|---|
| 26 skills need refreshing | **7 of them needed nothing** — upstream never touched them since extraction, verified byte-identical. Refreshing them would have *reverted* the extraction edits |
| `skill-reviewer` is 2,275 words behind | Only **+195** is real upstream advance; the other 91% is this repo's own generalization work |
| `orchestrate` and `agent-delegate` are upstream skills the kit fell behind on | **Both originate here.** They entered this repo 2026-07-03 and upstream 2026-07-13, byte-identical. Upstream is downstream. Their merge base is this repo's own first version |
| The refresh set is name-derivable | It is not, and now for a second reason: two entries need a per-skill base override |

**Consequence for W2.4:** the correspondence map needs a **direction** field, not just kit↔upstream name pairs. For those two skills a drift check that assumes upstream-is-newer will report backwards.

**Deliberate departure from Gate B D2.** D2 reads "(a) ship skill-owned scripts for same-skill sites, (c) substitute the CLI for cross-skill sites". Applied literally that ships upstream's linter *and* the CLI — two implementations disagreeing about what is valid, since the CLI deliberately drops four upstream rules. So **same-skill sites use the CLI too**, and the kit ships neither `ai_files_lint.py` nor `audit_skills.py`. Shipped instead, each with a working-directory fallback: `drain_audit.py`, `audit_cleanup_targets.py`, `probe_checker.py`. A future sync will show these as diffs that are **correct**.

## 5. `session-retrospective` — attempted, reverted, and why that is the finding

I ran the same three-way merge that carried the other 25. It reported 13 conflicts that all resolve to "take upstream", which looks clean. It is not:

| Check | Result |
|---|---|
| Extractor after merge | **1,400 lines** against upstream's 1,547 |
| Extractor tests | **8 failed, 27 passed** (baseline before: 15 passed) |
| Absent | `check_file`, slash-command capture, `compact_boundary` counting, and the `DEEP_DIVE_*` / `PRESCAN_*` constants whose function bodies *did* land |

A partial v4 — new function bodies without their constants — is worse than either version alone. It failed loudly only because this file is well tested; a thinner file would have shipped silently broken. **Reverted to the working v3; nothing half-merged was committed.**

**Root cause, and the number the charter was missing:** the shipped extractor is 3,453 words against the extraction point's **4,584**. This repo removed ~1,100 words, not the ~40 the dated-citation scrubs account for. That uncharacterized removal is what makes the merge non-mechanical — upstream's v4 hunks target context that was deleted.

**Revised first step, before any merge of that file:** diff the extraction-point extractor against the shipped one and write down what those ~1,100 words were and why they went. Until that exists there is no way to tell a dropped upstream hunk from a deliberate removal, so no merge of it is reviewable. Budget it as a reconciliation. Also note the schema version is stated in the script **and** both reference docs, so the whole skill moves together or not at all.

## 6. The defect worth propagating to other sessions

**16 call sites across 10 skills told adopters to run a command they do not have.** `lemmi-ai-kit <sub>` is a `[project.scripts]` console script — it exists only after a pip/uv install of the distribution. This kit installs as a plugin, which places skills and never installs the package. It resolved in testing only because the development venv has the package installed.

This is the same defect class the port existed to remove: an unreachable script path was replaced with an unreachable command name, and the DoD-4 guard did not catch it because that guard bans the *old names* rather than requiring a *reachable form*.

Fixed in three places, because it had propagated: the 16 call sites, `cli.py`'s argparse `prog` (so `--help` stopped teaching it), and the companion handoff's rewrite table. **The reachable form is the one `kit-setup` already documented all along** — `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit <sub>`.

**Transferable rule: when a skill names a command, check it against the install path the adopter actually uses, not the one the developer has.**

## 7. Verification, and where it stops

**Done:** three-way merges per file against the real base; ~30 conflicts resolved by hand; the four checks green at every commit; every reference path resolved (own, sibling, cross-skill, and markdown anchors — 0 broken); scaffold into a fresh directory renders all 38 under the correct invocation heading; the three shipped scripts executed from a plugin-style path with no `.git`/`.ai` ancestor; four new hygiene patterns mutation-tested by reintroducing each violation and confirming the suite goes red.

**A line-level carry audit** over the 5,561 lines upstream added since extraction (excluding the deferred skill and the four deliberately unshipped files): **95.0% carried verbatim, 3.6% carried rewritten, 1.5% (82 lines) dropped** — all 82 classified, every one a deliberate category (banned pattern, unshipped infrastructure, unreachable pointer, source-project deploy state, machine-specific rule).

**Where it stops, stated plainly:**

- **I did not human-read all 38 skills end to end.** Confidence rests on mechanical merges plus targeted reads of the two highest-risk skills.
- **Both real defects this session came from challenging an assumption, not from more scanning.** Every pattern check added is good at what it encodes and blind to everything else. Two examples: the completeness sweep matched backticked skill names and so missed slash-command form, leaving two skills invoking a skill I1 deleted; and nothing checked whether a named command was reachable.
- **Prose generalization remains unmeasured**, as the triage's §13 said. The 82-line figure is a floor on intentional divergence, not a total.
- **`sweep_user_corrections.py`** (new upstream, 357 words) has never been read for portability. It belongs to the `session-retrospective` task, not to the merge.

## 8. Cross-session note — I edited another session's files

`src/lemmi_ai_kit/checks.py` gained a seventh learnings category, and `tests/test_checks.py` now reads the canonical reference doc instead of `SKILL.md`. Both were required: the refreshed `task-learnings` moved the category table into the reference doc (upstream made it the single source shared with `learning-consolidator`) and added an `interaction` category, so without the change the lint would reject entries the shipped skill teaches.

Those edits are in the **second** commit, not in the CLI commit. Whoever reviews the CLI work should read both.

## 9. Sequencing recommendation

1. **Resolve F9, then decide the push.** Everything else is local and reversible; the push is not.
2. **W2.4 next, not the retrospective reconciliation.** W2.4 is the charter's durable deliverable and it is now unblocked with better inputs than it would have had — including the direction problem in §4, which it must encode.
3. **Then the `session-retrospective` reconciliation**, scoped per §5 as its own task.
4. `usage-guard` stays deferred.
