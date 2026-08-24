# Session handoff — the guard is in and the publish path is GREEN. Read this first.

**Date:** 2026-08-24, at session close · **Executed:** S-3 step 2 (the pre-publish guard), complete.
**Paths held:** `plugins/core/src/lemmi_ai_kit/publish.py`, `plugins/core/src/lemmi_ai_kit/cli.py`,
`tests/test_publish.py`, this file, and the companion review. Nothing else was written.
`assets/templates/AGENTS.md` and every pre-existing file under `docs/research/` were left alone.

**One-line state:** run as `python -B …`, the guard reports **`PUBLISH CHECK PASSED`, exit 0**, on
this checkout. S-3 step 1 passes for the first time in this program.

```
porcelain 0 · untracked under plugins/ 0 · ignored under plugins/ 0
PUBLISH CHECK PASSED (the payload is exactly the git tree)
```

**What orchestration must act on, in priority order:**

1. **The drill's invocation is `python -B -m lemmi_ai_kit publish-check`** (§2). Without `-B` the
   gate cannot pass on this repo *even from a clean tree*. This is the single most important line
   in this document.
2. **Do not wire `publish-check` into CI** (§5). The reason matters more than the rule.
3. **The kickoff's pathspec-commit rule fails as written on a new file** (§6).
4. **S-3 step 4's F1/F2/F3 re-check is unassigned** (§4). This session did not do it and says so.

> This file was refreshed at session close and **supersedes the mid-session version**, which had
> accumulated two correction blocks. Nothing is lost: the companion
> [completion review](2026-08-24-publish-guard-completion-review.md) holds the full audit trail,
> including both corrections and the finding that arrived after the review closed. **Read it
> before quoting any count the guard prints.**

---

## 1. What was asked, and what was delivered

**Asked:** the operator pasted S-3's four-step block with no instruction.

**Delivered:** step 2, which was the only step executable when the session started — S-3 runs after
S-1 and S-2, and S-2 was still under decision. Five commits:

```
c88d152  the guard
34360e2  fix: it undercounted what it said would ship
5757c96  the completion review and the first version of this handoff
8c01f2e  correct the collapse bound: unbounded, not six to one
68139d5  fix: it blocked on bytecode it wrote itself
```

## 2. The invocation is part of the control

```
uv run python -B -m lemmi_ai_kit publish-check     # require exit 0
```

**`-B` is not optional and not a preference.** The package lives inside the payload, so importing
it writes seven `.pyc` there *before* the git probe runs — the guard then blocks on files it
created itself. Measured on a clean clone: from zero `.pyc`, a plain run reports
`gitignored in the payload (7)` and exits 1 having made all seven; the same invocation under `-B`
exits 0. `git clean -Xdf` followed by a plain re-run is a loop.

Also measured, because it is the fix anyone would try first and it does **not** work: setting
`sys.dont_write_bytecode` at the top of `__init__.py` takes seven to **one**, never zero. CPython
writes a module's cache entry before the module body executes, so `__init__.pyc` lands regardless.
The flag has to be on the interpreter.

The guard now detects the condition and prints the `-B` command beside the `git clean` — but only
when it actually caused the findings. Verified: on this checkout under `-B`, with pre-existing
`.pyc` from other sessions' test runs, it printed the `git clean` remedy and *not* the `-B` advice,
because clean alone was sufficient there.

**Gate on `!= 0`, never on `== 1`.** Exit 2 means *could not measure* — no git, not a work tree, no
marketplace manifest, or a payload pathspec matching nothing tracked. A script testing `== 1` reads
"I could not measure" as a pass, which is the failure the third exit code exists to prevent.

## 3. What the guard is, and the five decisions behind it

Three probes — `git status --porcelain -uall`, `ls-files --others`, `ls-files --others --ignored`
— the last two scoped to the payload. Each is argued in the module docstring, so a reader who
never sees this file still gets the reasoning.

| Decision | Why not the obvious alternative |
|---|---|
| No escape-hatch flag | An excuse-a-path flag restores the judgement call the guard removes — made by whoever is publishing, about their own mess, under time pressure |
| Could-not-measure is exit 2, never 0 | A gate that scans nothing reports green forever, and a green detector nobody can fail is worse than none because it gets trusted |
| Payload read from **both** marketplace manifests, unioned | A third pack comes under the guard by being *listed*. Hardcoding `plugins/` would let it escape silently |
| Every refusal names its remedy, and runs none | Refusing without saying what to run is the pressure that produces a `--force`. Running the fix would make "the tree is clean" a side effect of asking rather than a fact someone established |
| `__pycache__` is **not** exempted | Those `.pyc` *are* V-1's finding. Exempting them is the attractive wrong fix — see §5 |

**Three probes, but two independent detections.** With `-uall`, probe 2 is a strict subset of
probe 1 and can never fire when probe 1 is silent; it earns its place by scoping and by supplying
the "would copy N files" arithmetic. The genuinely independent one is the ignored-file probe, and
it is **certified**: `probe_checker` reports `CAN-SEE` against a fixture whose
`git status --porcelain` is empty while a `.pyc` sits under the payload — V-1's leak rebuilt from
scratch, caught, invisible to `status`.

**One remedy is worth repeating here** because a reader invents it unprompted and it fails
*silently in the direction of shipping*: adding an untracked payload file to `.gitignore` does not
stop it shipping. It moves the file from the second probe to the third.

## 4. State of S-3

| Step | State |
|---|---|
| 1 — assert the tree is clean | **PASSES**, under `-B`. First time. It is a timestamp, not a property — several sessions write this tree; re-run it, do not quote it |
| 2 — the guard | **Done**, five commits |
| 3 — F8, the public path | **Blocked until the flip.** The repo is private, so the advertised `owner/repo` form is untestable, and there is no `claude` or `codex` binary on this machine — the local half could not be re-run either |
| 4 — re-check F1/F2/F3 + README count | **Half done, and this says which half.** The README-count claim holds: `test_readme_counts.py` derives the number from the manifest rather than asserting a literal, and the suite is green. **F1/F2/F3 were not re-checked** — that would have been guessing at program rows this session had not read, and a re-check nobody performed is worse recorded as done than as open |

## 5. Do not put `publish-check` in CI

CI's own `pytest` imports the package, writing `.pyc` under the payload, so the guard would be
**red on every green build**.

**Record the consequence, not just the rule.** Faced with a permanently red gate the fix anyone
reaches for is exempting `__pycache__` — and that exemption blinds the guard to the exact files
that were V-1's finding. This is not hypothetical: the guard shipped *unpassable* for two commits,
which is the strongest possible version of that pressure, and it was built by the same session
that wrote the warning against it.

It is a pre-publish gate: run deliberately, once, on a tree cleaned for publishing, with `-B`.

## 6. Correction to a standing rule in the kickoff

The pathspec-commit rule is right in intent and **fails as written**:

```
git commit -- plugins/core/src/lemmi_ai_kit/publish.py
error: pathspec '…/publish.py' did not match any file(s) known to git
```

A partial commit can only name paths git already tracks, so a **new** file needs `git add` first —
and the pathspec must be on *both* commands, or the `add` is the unprotected step:

```
git add    -- <paths>
git commit -- <paths> -m ...
```

This matters precisely because the rule exists for sessions adding new files. All five commits here
used the two-step form, with the index checked empty beforehand rather than assumed.

## 7. Open, unverified, and explicitly not mine

- **The guard's premise is inherited, not re-measured.** Every probe measures *git state*. That git
  state equals what an install copies is V-1's measurement; no binary on this machine could
  re-verify it. **F8 is where that closes** — until then the guard is precise about git, and
  trusting-by-proxy about publishing.
- **Not probed:** symlinks under a pack; case-only collisions; the `./` payload form end to end
  (unit-tested only); performance on a large tree.
- **A known limit, disclosed rather than hidden:** a nested git repository is one entry in every
  probe — git will not look inside another repo. It still *blocks*; it cannot be *counted*, so the
  arithmetic prints "at least" and the entry is marked.
- **Nothing is pushed.** `origin/main` is far behind, and that backlog long predates this session.
  Consistent with every handoff in this directory; flagged so it is not assumed otherwise.

## 8. What the review found, and why it matters to the next reviewer

Three defects in shipped behaviour, all **after** a green suite, none found by adding tests:

1. the working-tree probe collapsed an untracked subtree to one entry at its topmost untracked
   ancestor — an undercount of *unbounded* ratio, in the direction of looking clean;
2. a nested repo cannot be counted, and the total was printing a floor as if exact;
3. the guard blocked on bytecode it wrote itself, making the gate unpassable by construction.

The first two came from ten minutes of `mktemp -d` characterising what git actually does. The third
came from `lemmi-ai-kit-c2` running it from a clean state — a state this session never had, because
its own tooling had dirtied the tree before its first probe.

**Carry-forward for whoever builds the next gate: a check that runs inside its own subject must be
measured from that subject's clean state, by something that is not the check.**

## 9. Durable anchors

```
c88d152 34360e2 5757c96 8c01f2e 68139d5    this session's five commits
plugins/core/src/lemmi_ai_kit/publish.py   the five decisions, in the module docstring
tests/test_publish.py                      30 tests at 68139d5
plugins/core/skills/post-task-review/scripts/probe_checker.py   caught this session's own blind probe
docs/research/2026-08-24-publish-guard-completion-review.md      the audit trail
docs/research/2026-08-23-v1-restructure-review.md                V-1 §2, the finding this implements
```

At close: **227 passed, 6 skipped**; `ruff check .` clean repo-wide; `ruff format --check` clean;
`basedpyright` 0 errors; `git status --porcelain` empty.
