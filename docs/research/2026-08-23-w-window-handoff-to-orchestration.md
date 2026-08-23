# Session handoff to orchestration — W-window is paid, and the pin blind spot is closed

**Dated:** 2026-08-23, at session close.
**Executed:** program doc §5f **W-1** (six funded skills), **W-2** (the vocabulary-pin blind
spot), **W-3** (`EXPERIMENT-REGISTERED`).
**Nothing is committed.** Four checks green at 19:56 on the shared tree, both with and without an
upstream checkout configured.

Companion documents:

| Document | For |
|---|---|
| [2026-08-23-w-window-paid.md](2026-08-23-w-window-paid.md) | the measurement and the per-skill result |
| [2026-08-23-w-window-completion-review.md](2026-08-23-w-window-completion-review.md) | the adversarial self-review, including the four claims that did not survive it |
| [2026-08-23-extraction-window-debt-measured.md](2026-08-23-extraction-window-debt-measured.md) | the debt this pays; its denominators reconcile exactly |
| [2026-08-23-per-skill-extraction-base.md](2026-08-23-per-skill-extraction-base.md) | the bases used — **its method has a flaw named in §4 below** |
| this file | orchestration |

---

## 1. Status in one table

| Deliverable | State |
|---|---|
| W-1 — six funded skills re-merged | **Done.** 13 files across `skill-creator`, `learning-consolidator`, `skill-reviewer`, `python-conventions`, `skill-creation-workflow`, `ai-improvement-tracker` |
| W-3 — `EXPERIMENT-REGISTERED` | **Done.** Shipped table, `checks.CHANGELOG_TYPES`, and the pairing rule in `ai-improvement-tracker`; the false "deliberately dropped" note in `checks.py` corrected in place |
| W-2 — upstream fidelity | **Done.** `read_upstream_file` in `tests/upstream_sync.py`, five tests in `tests/test_checks.py`, all five mutation-proven |
| Carriage across the funded seven | **8% → 82%** on substantive lines; 11% → 84% on all non-blank lines |
| Residual 96 absent lines | **All classified.** 52 reworded, 30 deliberate strips, 14 continuations of those. **Zero accidental losses** |
| Four-check gate | Green: `ruff` · `ruff format` · `basedpyright` 0/0/0 · `pytest` **196 passed** (190 + 6 skipped without upstream) |
| `audit-skills --fail-on major` | exit 0 for both packs, invoked with an explicit `--skills-dir` |

## 2. What a re-planner must not assume

**W-window is closed for the funded six. Do not re-fund it.** The remaining seven exposed skills
hold 91 lines between them and that ruling stands. `ai-changelog` was pulled in as W-3 and is done
too, so the funded set was effectively seven.

**The vocabulary pins now have three operands, and they are the only automated guard on upstream
fidelity in the repo.** Before W-2, all five pins compared the kit to itself, so a member dropped
from a shipped document *and* from `checks.py` stayed green — measured, not hypothesised. That hole
is the reason this debt stayed invisible, and it is now closed for **all five** members of the
family: changelog types, hypothesis categories, learnings sections, the hand-off contract, and
hypothesis statuses.

**One of those five nearly shipped as owed work on a false premise.** An earlier draft of this
hand-off filed `HYPOTHESIS_STATUSES` as deferred, reasoning that upstream's counterpart is a live
data file with no clean parse. Checking it rather than asserting it: upstream's
`.ai/improvement-hypotheses.md` carries the same `Status lifecycle:` line the shipped seed does,
so the same two patterns read both sides and the detector took minutes. **A plausible reason for
not doing something is not a measurement.**

**The W-gate criterion from the measuring session's review is satisfied.** Its §2 said promoting
either gate while this hole was open would promote a suite that is green on a measured content
loss. It no longer is.

## 3. Owed, and who it belongs to

| # | Item | Why it is not done | Owner |
|---|---|---|---|
| 1 | `[extraction_window] status` in `docs/upstream-sync.toml` off `"unreviewed"`, pointing at the paid record | That file sits in another session's declared path set and was already dirty there. Editing it meant a conflict, not a record | whoever lands the I-1/I-2 cluster |
| 2 | `subagent-preamble.md`, ~12 portable lines of 25 | Out of scope by the measuring session's decision; porting it is a new file, not a merge. **It now has a live caller** — `skill-creation-workflow` Phases 2 and 6 both want it, and I dropped the two paste instructions rather than point at a file that does not ship | a follow-up, sized at well under a session |
| 3 | `docs/research/README.md` row for the new records | That file is deliberately prose with **no per-file index**, so the measuring session's owed item #2 has nothing to add a row to. Naming it rather than inventing a table | a decision, not a task |
| 4 | `task-learnings` at 66% carriage | Outside the funded six. Still unexplained: it is exposed, yet carried 37 of 56 window lines where its peers carried near zero, and the measuring session's pinning-test explanation was tested and refuted | open question, not a deliverable |

## 4. Two method corrections that outlive this wave

**The per-skill base document's probe has a tie ambiguity, and it can make a *trusted* row look
wrong.** Its Reproduce section says to diff the shipped copy against every upstream revision of the
path and take the minimum. But `git log -- <path>` lists only commits that *touched* the path, so a
file unchanged across a range scores distance 0 at **every** revision in that range and the winner
is whichever SHA the sort returns. Probing `skill-creator/references/skill-patterns.md` that way
returns `f8ffbab6` at distance 0 with the runner-up 64 lines away — which looks far stronger than
the `3dd2496d` the document records, and is not a disagreement at all. **What a three-way merge
consumes is base *content*, and `git show <rev>:<path>` resolves for any revision whether or not it
touched the file.** Measure content at the candidate. This is distinct from the five rows flagged
on weak separation.

**A lint or type-check exclusion is written against a path, so every tree move silently changes
what is checked.** The I-2 restructure briefly pulled four shipped skill scripts into ruff's
surface, where the repo's own formatter would have rewritten pack content meant to ship as
authored. Raised, and fixed by that session with `extend-exclude` plus a matching `basedpyright`
`exclude`; re-verified at 19:56, `ruff check --show-files` returns 19 files, none under a skills
tree. The instance is closed; the class is not — it can as easily push real source *out* of the
gate as pull assets in.

## 5. The restructure landed mid-session, and the sequencing ruling is now measured

W-1 ordered W-window **before** the restructure on the grounds that *"content edits survive a path
move cleanly."* The restructure ran anyway, in another session, at ~19:29 for the skills tree and
again shortly after for the Python package. All merges had landed first.

**Verified by hash, not by inspection:** SHA-256 of all 13 merged skill files, pre-move copies
against the post-move tree — **13 identical, 0 changed**. `checks.py` likewise identical after its
own later move to `plugins/core/src/lemmi_ai_kit/`. A move and a move-plus-rewrite look the same in
this tree, so they were hashed.

**So the ruling was right, and the cost of the overlap landed on tests rather than on content.**
Three vocabulary pins broke on `assets_root() / "skills"`; they are repointed at
`manifest.shipped_skill_dirs()`, which resolves by name and survives the next move. The new
fidelity tests never broke, because their kit-side operand is a constant rather than a path.

## 6. Current locations, because they changed twice

| What | Path at session close |
|---|---|
| Six merged core skills + `ai-changelog` | `plugins/core/skills/<name>/` |
| `python-conventions` | `plugins/python/skills/python-conventions/` |
| `checks.py` (W-3 constant, corrected comment) | `plugins/core/src/lemmi_ai_kit/checks.py` |
| W-2 tests | `tests/test_checks.py` (fidelity section at the file's end) |
| W-2 upstream reader | `tests/upstream_sync.py`, `read_upstream_file` |
| Records | `docs/research/2026-08-23-w-window-{paid,completion-review,handoff-to-orchestration}.md` |

**Nothing here is committed, and the entire skills tree is untracked** as of this writing. Two
consequences that changed during the session and that anyone touching this tree needs: `git clean
-fd` now deletes all 37 skills and needs no `-x`, and **`git diff HEAD > patch` backs up none of
it** — a patch contains no untracked files. Only file copies or a tarball cover it. All 17 of this
session's deliverables are copied outside the repo.

## 7. Shared-tree notes worth carrying to the next session

- **Five writers shared this checkout**, four Claude sessions plus a Codex session that
  `ListAgents` cannot see. The Codex session ran `git restore` on paths it did not own, including
  two of the six funded skills, before this work began.
- **A peer's "I have written zero bytes" is true for one instant.** Mine was accurate when sent and
  false three minutes later, and a peer had to learn it from a file mtime. The fix is for the writer
  to re-announce on state change, not for the asker to poll harder.
- **Two measuring faults produced confident, wrong numbers** and both are recorded: the CRLF/LF
  asymmetry between the working tree and `git show`, and a `$'\r$'` pattern that is correct bare and
  degrades to match-everything inside a quoted `printf` argument. A peer correctly challenged my
  explanation of the second — the conclusion held, the mechanism I gave for it did not.

## Status

**ready-for-review.** W-1, W-2 and W-3 are complete and gated; four items are owed and itemised in
§3, none of them blocking; nothing is committed.
