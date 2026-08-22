# Handoff — F7 rename executed. The merge set changed shape. Read §2 and §4 first.

**Dated:** 2026-08-22, at session close. **Executed:** F7 / I4 W3.1 (the rename, complete).
**Not started:** the pack split (W3.2+), the adoption path (W3.3+), the pack authoring path.
**Branch:** `pre-flip` — which I created, because it did not exist. **Nothing is pushed.**

This is the execution-side handoff for the rename. The adversarial review of the same
work is at [`2026-08-22-f7-rename-completion-review.md`](2026-08-22-f7-rename-completion-review.md);
where they overlap, that one is harsher and this one is shorter.

Two things in here are more urgent than the rename itself: the merge set is no longer
the three branches the earlier handoff names (§2), and **two other sessions' pre-flip
work is sitting uncommitted in this shared checkout** (§4).

---

## 1. What landed — three commits, and why three

| Commit | Change | Decision it implements |
|---|---|---|
| `e52e4e2` | `lemmi-python-conventions` → `python-conventions`, `lemmi-test-conventions` → `test-conventions`, `lemmi-vertical-slice` → `vertical-slice` | D4 |
| `de02980` | `fable-orchestrate` → `orchestrate`, plus its H1 | OQ-8 |
| `d750097` | two names the name-sweep could not see — wrapped inside ASCII box art | fixes an omission in `e52e4e2` |

Split on the decision boundary, not by convenience: the de-branding and the
orchestrate rename have different rationales and **share no edited line**, so
`git revert de02980` cleanly defers the orchestrate half to I2's port if the operator
prefers that. The reverse is not true — do not revert `e52e4e2` alone, because
`d750097` fixes sites it introduced.

19 paths: 16 content edits (the number the brief predicted) plus 3 files that moved
inside a renamed directory without their content changing.

**The finding worth carrying forward.**
[`skill-reviewer/SKILL.md`](../../src/lemmi_ai_kit/assets/skills/skill-reviewer/SKILL.md)
draws a fixed-width diagram in which two skill names are *wrapped across lines*:

```
│ lemmi-python-    │        │ lemmi-vertical-  │
│  conventions     │        │  slice           │
```

Neither name exists as a contiguous string, so a grep for the full name reports the
file clean. What found them was sweeping for the **prefix** and tokenizing:
`git grep -ohE "(lemmi|fable)-[a-z0-9_-]*" | sort | uniq -c`, which left two truncated
tokens at count 1 each. **Grep-for-the-old-name is not a completeness check for a
rename** — it cannot see a name broken by line wrapping, and fixed-width diagrams break
names by construction. W3.2's restructure will hit the same class of defect.

## 2. Merge order — still three branches, but not the same three

`pre-flip` descends from `i3a-contribution-surface`, so it **carries all of I3a**. That
changes the set the earlier handoff records. Measured, not remembered:

```
git merge-base --is-ancestor i3a-contribution-surface pre-flip   -> 0  (contained)
git merge-base --is-ancestor i1-decouple-prompt-skills f3-…       -> 0  (contained)
git merge-base --is-ancestor f3-stale-counts pre-flip             -> 1  (NOT contained)

commits over main:  pre-flip 22 · f3-stale-counts 4 · readme-drop-… 1
```

```
main
 └── pre-flip ......................... CONTAINS i3a-contribution-surface (19) + the rename (3)
main
 └── f3-stale-counts ................. CONTAINS i1 — merging this lands both
main
 └── readme-drop-unbacked-refresh-claim  independent
```

**Merge `pre-flip`, `f3-stale-counts`, and `readme-drop-unbacked-refresh-claim`, in any
order. Do not merge `i1` or `i3a-contribution-surface` separately** — both are subsumed.
Where the earlier handoff says to merge `i3a-contribution-surface`, read `pre-flip`.

**`pre-flip` does not contain F3.** Its `manifest.toml` and `test_manifest.py` still say
33 skills. That is correct for the branch and wrong for the flip, and it resolves on
merge — verified below, not assumed.

## 3. The merged flip state passes the full gate — measured

Assembled entirely in the object database and extracted to a scratch directory outside
the repo, so the shared working tree was never touched:

```
merge-tree(pre-flip, f3-stale-counts)                     clean, no conflicts
merge-tree(that, readme-drop-unbacked-refresh-claim)       clean, no conflicts

skill dirs 29 · manifest entries 29 · README "29 skills" ×2 · zero old skill names
ruff check       All checks passed!
ruff format      13 files already formatted
basedpyright     0 errors, 0 warnings, 0 notes
pytest           37 passed, 2 failed
```

**The two failures are my harness, not the tree.** Both are in
`test_publication_hygiene.py`, which resolves the tracked set with `git ls-files`; an
extracted tree has no git metadata, so it correctly refuses to pass a scan it cannot
run. The hygiene contract was therefore verified a second way — the nine patterns
**imported** from the test rather than retyped, applied to the merged tree's blobs: 36
tracked text files outside `assets/`, clean.

The operator's atomicity warning resolves here and does not need managing: F3 edits the
skill *count* (line 19) and I edited the python-profile *set* (lines 34-38) in the same
file. Line-disjoint, so git combines them, and the merged `test_manifest.py` carries
both `== 29` and the renamed set.

## 4. Three other sessions are live in this checkout, and only my work is committed

This is the operational risk in the tree right now. Over this session the dirty set grew
from four entries to six as other sessions worked around me:

| Path | Owner | State |
|---|---|---|
| `docs/research/2026-08-22-i3-part-b-handoff.md`, `-publication-reachability.md`, `-session-handoff-to-orchestration.md` | I3a | **modified, uncommitted — this is the F6 fix** |
| `tests/test_plugin.py` | Session A (W3.0) | modified, uncommitted |
| `docs/research/2026-08-22-w3-0-codex-install-verified.md` | Session A (W3.0) | **untracked** |
| `docs/research/2026-08-22-i2-portability-triage.md` | I2 | **untracked** |

Two consequences, both cheap to prevent and expensive to discover later:

1. **F6 is marked "fixed" and is not committed.** The fix is real — the dirty diff
   delinks the private-path citations exactly as F6 prescribes, e.g.
   `[../../tasks/I3-…](…)` becomes `` `tasks/I3-…` (private planning artifact — not
   committed to this repository) ``. But **if the flip merges without those three files
   being committed, the flip ships the defect F6 exists to fix.** Nothing in the merged
   state contains that fix, because it is not in any commit.
2. **Four files of other sessions' evidence exist in exactly one copy, untracked.** The
   program doc already records that the F5 enforcement makes `git clean -xdf` delete
   untracked trees silently, with no recovery. Two of the four are untracked *and* not
   ignored, so an ordinary `git clean` reaches them too.

**Nobody should switch this checkout's branch or clean it until those are committed.**
That is also why I created `pre-flip` at the existing tip rather than basing on
`f3-stale-counts`: reaching it means checking out a divergent sibling and deleting
nineteen commits' worth of files out from under three live sessions.

## 5. Program items this session changes

| Item | Was | Now |
|---|---|---|
| **F7** — rename's cheapness expires at the flip | open, time-boxed to ~2026-08-29, owner "operator" | **executed on `pre-flip`.** Closes on merge, not before |
| **OQ-8** — does `fable-orchestrate` → `orchestrate` land in I2 or I4? | open, "operator, coordinating with I2" | **settled: it rode along with the rename.** One breakage event, as W3.1 asked |
| **I4 W3.1** — rename, "3 skill names and 12+ references, 3 tests" | pending | **done, and the charter's own numbers were low**: 4 names, 16 files, 2 test files. `test_plugin.py` — the charter's third test — needed no change |
| **F4 / install-blocker 3** — Codex `source.path` | open, owner I4 W3.0 | **Session A reports it REFUTED** — see below |

**On F4, reporting someone else's finding as theirs.** Session A's untracked handoff
states that `"path": "./"` installs fine, that `codex-cli 0.149.0` was actually run
against a local marketplace directory, and that *the charter's prescribed fix is what
would break it*. I did not verify any of that and it is not my claim — but if it holds,
a pre-flip gate item is not a defect, and `tests/test_plugin.py` asserting the current
shape is correct rather than "CI defending a bug". **Do not action the charter's F4 fix
without reading that document first.**

## 6. Decisions taken here — do not re-litigate without new information

1. **The rename is 4 names, not 3.** OQ-8 was settled by the operator in the session
   brief; `orchestrate` shipped with the de-branding.
2. **`vertical-slice` stays under profile `python`.** It is architecture, not language —
   flagged, deliberately not re-filed. The pack axis is OQ-2's one-way door and re-filing
   it here would have pre-empted that decision.
3. **`manifest.toml:2`'s profile comment still omits `orchestration`.** Left alone on
   purpose: `f3-stale-counts` edits that exact line to drop `prompts`, so fixing a
   comment typo would have manufactured a merge conflict.
4. **The brand was removed from names only.** Five prose sites still say "Lemmi",
   including the frontmatter `description` of `python-conventions` and a line in
   `templates/AGENTS.md` that is seeded into every adopter project. Full list in the
   review, §2. **Operator call, and `AGENTS.md:19` is a one-word deletion independent of
   OQ-2.**

## 7. Recommended next actions, in priority order

1. **Get the other sessions' work committed** (§4). Highest value per minute in this
   tree, and it protects against a class of loss that has no recovery. The F6 fix in
   particular must be committed *before* the flip, not before the merge.
2. **Read Session A's W3.0 document and re-rule F4** (§5). It may remove a gate item and
   it contradicts the charter's prescribed fix, so acting on the charter here is the
   risk, not the caution.
3. **Merge the three branches and run the gate on the result** — the merge is verified
   clean (§3), but verify in a real work tree so the two git-dependent hygiene tests
   actually execute.
4. **Decide the five brand-in-prose sites** (review §2). Cheap now; it is I2's content
   refresh afterwards, at which point it competes with 26 other skill refreshes.
5. **Repoint I2's triage before it plans against stale names.** The untracked
   `2026-08-22-i2-portability-triage.md` names `fable-orchestrate` at lines 77, 87 and
   116; that directory no longer exists.
6. **Add the test that makes the next rename self-checking** — frontmatter `name:` must
   equal the directory name. All 33 currently agree (I checked by hand, which is the
   point). Same shape as F3's "stop hand-writing the number", and it belongs with that
   work rather than bolted onto this branch.

## 8. What I did not do, and would not without being asked

- **Did not merge anything.** Merging changes a tree three sessions are working in.
- **Did not push.** Nothing is on the remote; the repo is still private.
- **Did not touch** `.codex-plugin/`, `.agents/`, `tests/test_plugin.py`, or any of the
  six foreign dirty files. Every commit staged by explicit path; `git add -A` never run.
- **Did not use a worktree**, and never switched the shared tree.
- **Did not re-file the mis-filed skill**, fix the stale profile comment, resolve the
  duplicate `test-conventions/README.md`, or strip the brand from prose. All are in §6
  or the review's §8 with the reasoning attached.

## 9. Read these, in this order

1. This file, then [the completion review](2026-08-22-f7-rename-completion-review.md).
2. `docs/research/2026-08-22-w3-0-codex-install-verified.md` — untracked at the time of
   writing, and it may retire a flip gate item.
3. `docs/research/2026-08-22-session-handoff-to-orchestration.md` — the I1/I3a
   execution handoff. **Its §1 merge set is superseded by §2 here.**
4. The program and I4 charters, held privately as `tasks/00-PROGRAM-oss-launch.md`
   (§2c F7, §5b OP-3) and `tasks/I4-TECH-pack-split-adoption.md` (W3.1, OQ-2, OQ-8) —
   private planning artifacts, not committed to this repository.
