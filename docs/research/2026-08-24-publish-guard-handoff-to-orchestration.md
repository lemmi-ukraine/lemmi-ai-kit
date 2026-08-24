# Session handoff — S-3 step 2 delivered, steps 3 and 4 still open. Read this first.

**Date:** 2026-08-24 · **Executed:** S-3 step 2 (the pre-publish guard) — complete and committed.
**Paths held:** `plugins/core/src/lemmi_ai_kit/publish.py`, `plugins/core/src/lemmi_ai_kit/cli.py`,
`tests/test_publish.py`, and the two documents from this session. Nothing else was written.
`assets/templates/AGENTS.md` and every pre-existing file under `docs/research/` were left alone.

**One-line state:** the guard exists, is certified, and currently **refuses to publish** — correctly.
S-3 steps 1 and 4 can now be *run* rather than reasoned about; step 3 remains impossible while the
repo is private.

**What orchestration needs from this document, in priority order:**

1. **Do not wire `publish-check` into CI** (§4). One line, and the reason matters more than the rule.
2. **Correct the commit-pathspec rule in the kickoff** — as written it fails on new files (§5).
3. Decide who runs S-3 step 4's F1/F2/F3 re-check; this session did not (§3).

Companion document: [2026-08-24-publish-guard-completion-review.md](2026-08-24-publish-guard-completion-review.md)
— adversarial review. **It found two defects in shipped behaviour after the suite was green; read it
before quoting any count the guard prints.**

---

## 1. What was asked, and what was delivered

**Asked:** the operator pasted S-3's four-step block with no instruction.

**Delivered:** step 2 only, which is the only step that was executable.

- **Step 1** is an assertion, not work. Run at session start it failed on all three probes
  (10 dirty entries, 2 untracked and 6 ignored under `plugins/`) — V-1's leak reproduced exactly.
- **Step 2** was explicitly "pulled forward deliberately" and gated on nothing. Built.
- **Step 3** (F8) cannot run: the repo is private, so the advertised `owner/repo` form is
  untestable, and there is no `claude` or `codex` binary on this machine's `PATH`.
- **Step 4** not done — see §3.

The drill as a whole was not runnable: S-3 states it runs *after* S-1 and S-2, and S-2 was still
under decision when this session started.

## 2. The deliverable

`uv run python -m lemmi_ai_kit publish-check [--repo DIR]` — committed in `c88d152`
(875 insertions across three files), plus an uncommitted fix round from the review.

**Exit 0 clean · 1 blocked · 2 could-not-measure.** Gate on `!= 0`. A script testing `== 1` reads
"I could not measure" as a pass, which is the failure the third exit code exists to prevent.

Five decisions, each argued in the module docstring so they survive a reader who never sees this file:

| Decision | Why it is not the obvious alternative |
|---|---|
| No escape-hatch flag | An excuse-a-path flag restores the judgement call the guard removes — made by whoever is publishing, about their own mess, under time pressure |
| Cannot-measure is exit 2, never 0 | A gate that scans nothing reports green forever, and a green detector nobody can fail is worse than none because it gets trusted |
| Payload read from both marketplace manifests, unioned | A third pack comes under the guard by being *listed*. Hardcoding `plugins/` would have let it escape silently |
| Every refusal names its remedy, and runs none | Refusing without saying what to run is the pressure that produces a `--force`. Running the fix would make "the tree is clean" a side effect of asking rather than a fact someone established |
| `__pycache__` is **not** exempted | The six `.pyc` under `plugins/core/src/` *are* V-1's finding. Exempting the directory is the attractive wrong fix — see §4 |

**The remedy text carries one thing no reviewer asked for and every reader needs:** adding an
untracked payload file to `.gitignore` does **not** stop it shipping. It moves the file from the
second probe to the third. That is the fix a reader invents unprompted, and it fails *silently in
the direction of shipping*.

### Certified, not asserted

Two `probe_checker` stamps, both `CAN-SEE` (review §3). The load-bearing one uses a positive
fixture whose `git status --porcelain` is **empty** while a `.pyc` sits under the payload — V-1's
leak rebuilt from scratch, caught by the guard, invisible to `status`.

## 3. State of S-3, as of this writing

**The tree is live — several sessions are writing it, and any count below is a timestamp, not a
property.** Run the command; do not quote this table.

| Step | State |
|---|---|
| 1 — assert the tree is clean | **Runnable now.** Failing, correctly: `__pycache__` is always regenerating, and peers hold uncommitted work |
| 2 — the guard | **Done.** `c88d152` + the review's fix round |
| 3 — F8, the public path | **Blocked, and will stay blocked until the flip.** No `claude`/`codex` binary here either, so even the local half cannot be re-run from this session |
| 4 — re-check F1/F2/F3 + README count | **Half done, and I am saying which half.** The README-count claim holds — `test_readme_counts.py` derives the number from the manifest rather than asserting a literal, and the suite is green. **F1/F2/F3 were not re-checked.** I would have been guessing at program rows I had not read, and a re-check nobody performed is worse recorded as done than as open |

**The critical path I escalated mid-session has since resolved on its own terms.** At the time of
my first report `assets/templates/AGENTS.md` was the only dirty path in the repository and was
frozen pending OQ-5. It landed as `d317027` while this session was working. That escalation is
moot; `lemmi-ai-kit-90`'s handoff carries the live version of that thread, including OQ-5's
unconsumed answer.

## 4. Do not put `publish-check` in CI

CI's own `pytest` run imports the package, which writes
`plugins/core/src/lemmi_ai_kit/__pycache__/*.pyc` under the payload. The guard would therefore be
**red on every green build**.

**The reason to record is not the rule but what the rule invites.** Faced with a permanently red
gate, the fix anyone reaches for is exempting `__pycache__` — and that exemption blinds the guard
to the exact six files that were V-1's finding. A guard that cannot see the thing it was built for
still reports green, which is how this program's §7 instruments failed.

It is a *pre-publish* gate: run deliberately, once, on a tree cleaned for publishing. Its tests are
built the same way — throwaway checkouts in `tmp_path`, and the single test that touches this
checkout asserts only that the guard can **measure** it, never that the answer is clean.

## 5. Correction to a standing rule in the kickoff

The pathspec-commit rule now in the kickoff is right in intent and **fails as written**:

```
git commit -- plugins/core/src/lemmi_ai_kit/publish.py
error: pathspec '…/publish.py' did not match any file(s) known to git
```

A partial commit can only name paths git already tracks, so a **new** file needs `git add` first —
and the pathspec has to be on *both* commands, or the `add` is the unprotected step:

```
git add    -- <paths>
git commit -- <paths> -m ...
```

This matters because the rule exists precisely for sessions adding new files. Both commits from
this session used the two-step form, with the index checked empty beforehand rather than assumed.

## 6. Open, and explicitly not mine

- **The guard's premise is inherited, not re-measured.** Every probe measures *git state*. That git
  state equals what an install copies is V-1's finding; no binary on this machine could re-verify
  it. Attested is not the same as re-measured, and F8 is where that gets closed.
- **Not probed:** symlinks under a pack, case-only collisions, the `./` payload form end to end,
  and performance on a large tree. Review §5 lists why each is a plausible route to a wrong answer.
- **S-3 step 2 has no companion documentation outside the code.** `README`, `CONTRIBUTING` and the
  kickoff are other initiatives' files; the guard is documented in its own docstring and here.

## 7. Durable anchors

```
c88d152                                          the guard
d317027                                          AGENTS.md landed; the freeze I escalated is over
plugins/core/src/lemmi_ai_kit/publish.py         353 lines, five decisions in the docstring
tests/test_publish.py                            27 tests, 515 lines
plugins/core/skills/post-task-review/scripts/probe_checker.py    the instrument that caught my own blind probe
docs/research/2026-08-23-v1-restructure-review.md                V-1 §2, the finding this implements
docs/research/2026-08-24-s2-closed-oq5-answered-handoff-to-orchestration.md   the live OQ-5 thread
```

Full suite at handoff: **223 passed, 6 skipped**. `ruff check .` clean repo-wide, `ruff format
--check` clean, `basedpyright` 0 errors.
