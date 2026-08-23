# Session handoff to orchestration — I4 is planned; it is 10 sessions, not 4, and the minimal path is 3

**Dated:** 2026-08-23, at session close.
**Executed:** `/initiative-planner` over the I4 charter, `/stacked-pr-planner` for the topology,
`/plan-critic` over all three, then `/post-task-review` over my own output.
**Planning only. No code was written, no tracked file was modified, nothing is committed or pushed.**
`ruff` clean · `pytest` 184 passed / 1 skipped at `2de7787`.

Companion documents:

| Document | For |
|---|---|
| [2026-08-22-w3-0-codex-install-verified.md](2026-08-22-w3-0-codex-install-verified.md) | **tracked.** The four-fixture Codex method this plan's first session must rebuild, and the §7 P3 payload observation the plan is built on |
| [2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md](2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md) | **tracked.** Why the pack I4 splits is 38 skills and current, not stale |
| `.specs/i4-pack-split/{roadmap,execution-plan,topology}.md` | the plan itself — **NOT durable, see §7** |

---

## 1. Status in one table

| Item | State |
|---|---|
| `roadmap.md` — goal, falsifiers, gates, operator path, risks, undecided | **written**, 378 lines |
| `execution-plan.md` — sessions, tiers, concurrency, dispatch, triggers | **written**, 342 lines |
| `topology.md` — deliverables, layers, lanes, preconditions, triggers | **written**, 235 lines |
| `plan-critic` pass | **ran.** 6 Majors, 0 Blockers, all resolved in the documents |
| `post-task-review` pass | **ran.** 9 further defects in my own artifacts, all fixed and re-verified |
| Deliverable traceability | **23 deliverables, each in exactly one session row**, verified by script |
| Implementation | **not started, and must not start** — see §3 and §5 |

**Headline: the operator's H1–H4 hypothesis was 4 sessions. The plan is 10 full / 3 minimal.** Every
addition traces to either a charter deliverable H1–H4 omitted (W3.4's proof, a Resolve session) or a
measured risk (the packaging-layout unknown, reviewing the one-way door before it merges).

## 2. What this unblocks, and for whom

- **The operator**, immediately: three gate decisions are now answerable from written evidence rather
  than from memory of the charter — the packaging layout, the flip date, and whether I4 may write two
  files that belong to I3a and I3b.
- **The first I4 session (`R-1`)**: fully specified and unblocked *except* for the dirty tree. It is
  read-only, cheap, and it is the falsifier — it can change the shape of the most expensive session.
- **Nothing else.** Every other session in the plan is behind either Gate 1, Gate 2 or Gate 3.

## 3. Decisions now owed — none of them mine

Three are new and carry dates; four are the charter's own open questions, deliberately routed to
gates rather than answered, per the planning instruction.

| # | Ask | Blocks | UNKNOWN without it |
|---|---|---|---|
| **OP-I4-1** | Does the restructure land **before the repo goes public ~2026-08-29**? And may I4 write `README.md` (I3b's) and `CONTRIBUTING.md` (I3a's), which its own DoD requires? | `I-2`, `I-5`, therefore everything after | Whether the plan has six days or six weeks, and whether the repo greets its first outside readers with an install command that fails |
| **OP-I4-2** | Put `codex` back on PATH before the one-way door ships | a real verification of `I-2` | Whether the split actually ships skills to an adopter. `codex`, `claude`, `cursor-agent`, `grok` are **all absent** today |
| **OP-I4-3** | The concurrent session's uncommitted work sits inside the tree I4 must move | **everything** | Nothing — this one is simply blocking, and it is the cheapest item on the list |
| **OQ-3 · OQ-4 · OQ-5** | private overlays · four Go teams · does `kit-setup` install or detect | `I-3`, `I-4` | routed to **Gate 4**, unanswered by design |
| **OQ-7** | the community-pack review bar — a **supply-chain** control, not a quality preference | `I-5` | routed to **Gate 5**. A missing answer blocks the community tier, not the split |

**One thing worth knowing before OQ-4 is answered:** `### Project rules` lives in `AGENTS.md`, which
`scaffold` seeds **once per project directory**. So per-team rules work cleanly if the four Go teams
have four repositories and do not if they share one. That is the discriminator, and it is
information only the operator holds — not a preference between three equally available shapes.

## 4. What a re-planner must not assume — four inherited claims, measured and refuted

Do not re-derive these from the charter or the program doc. They were measured on 2026-08-23 and the
source documents still carry the old figures.

| Standing claim | Measured |
|---|---|
| Program §5e: split is **"core 36, python 2"** | **core 35 + python 2 = 37.** 33 agnostic + `vertical-slice` + `analyze-logs` = 35. `36+2=38` is the *pre-drop* total — the ruling added the two mis-filings to core and never subtracted the dropped skill |
| Charter: a non-Python adopter carries **"~17% irrelevant surface"** | **5.4%** (2 of 37). It was 5 of 29 pre-I2; the port roughly tripled the agnostic count. **The volume argument for the split has largely evaporated** — what survives is the naming argument and the funnel argument |
| Charter Context: the restructure is **2 packs × 2 `plugin.json` + 2 marketplace files** | **It is a packaging-layout change.** Three code sites read `assets_root()/"skills"` directly — `manifest.load_manifest()`, `tests/test_upstream_sync.py:65`, `tests/test_assets.py` — plus hatchling's `packages = ["src/lemmi_ai_kit"]`, which decides whether the wheel carries skills at all, plus `docs/syncing-from-upstream.md:311` in prose |
| Charter DoD 3: `grep -rn "lemmi-python-conventions\|…" .` **→ 0 hits** | **Unsatisfiable as written, and must not be run.** `docs/upstream-sync.toml` legitimately names the *upstream* skills; `skill-reviewer` and `session-retrospective` cite `fable-orchestrate` as the case study that teaches name-neutrality. Driving this grep to zero breaks the sync map. Re-scoped in `roadmap.md` §1.5 |

**Both wrong numbers still live in `tasks/`.** They were outside this session's scope, so they were
escalated rather than edited. The next reader inherits them unless the operator fixes them at source.

## 5. The finding that reshapes the initiative — the pack payload is unverified

`2026-08-22-w3-0-codex-install-verified.md` fixture **B** proved that a `source.path` of
`./plugins/core` **installs**. It did **not** show skills materializing — that claim (§1, "33 skill
directories materialized") was measured against the **root** layout only. And §7 P3 of that same
record notes the local install copied the whole repository into the plugin cache, which implies the
payload is `<source.path>` recursively.

**If that implication holds, skills cannot stay under `src/` when the plugin root becomes
`plugins/<pack>/`** — and `assets_root()`, `load_manifest()`, `pyproject.toml`, `test_assets.py`,
`test_upstream_sync.py` and `docs/syncing-from-upstream.md` all move **inside the one commit that
cannot be partially landed**.

This is why `R-1` exists and why it runs first. It is the cheapest session in the plan and it can
change the most expensive one. **Do not let a session discover this inside `I-2`.**

**And fixture C is the trap to carry forward:** Codex accepted a plugin with **no manifest at all**
and reported it installed, version silently degraded to `"local"`. Any check that reads "install
succeeded" as "the pack is valid" is unsound — for `R-1`, for `V-1`, and for §2c F8 at the flip.

## 6. The defect worth propagating to other sessions

**A count is a claim about a quantity, and naming the wrong quantity passes every consistency check.**
`post-task-review` found **nine** defects in my own artifacts after `plan-critic` had passed them.
Every one was a number, and three are worth generalizing:

1. **"41 platform mentions"** was the count of matching *lines*, not matches (54). `grep -c` and
   `re.findall` answer different questions; the label said one and the measurement did the other.
2. **"6 README lines"** was an eyeballed subset of a truncated grep. Re-derived **by category** —
   install command, invocation prefix, skill count, structure claim — the answer is **11 lines**.
   The wrong figure had propagated into all three documents before it was caught.
3. **The worst one: I diagnosed program §5e's off-by-one in `roadmap.md` §1.3, then used the wrong
   figure as a denominator in §1.4 of the same document.** A plan can restate the error it has just
   corrected, two sections later, and read as perfectly coherent.

**The general rule, already in `post-task-review` step 4b and now confirmed a third time here:**
recompute every derived figure in the *last* edit of the task, from the artifact rather than from
working memory, and say which quantity the number describes.

**A fourth, for anyone writing preconditions in this repo:** every command in `topology.md` §5 is
POSIX shell, and this machine's primary shell is PowerShell, where `for p in …; do … done` and `$?`
are **parse errors, not failures**. A precondition run in the wrong shell returns a syntax error
instead of a verdict. Verified by running it. Say "Git Bash" in the document.

## 7. Verification, and where it stops

Commands, with expected results. Run these before trusting anything above.

```
git rev-parse HEAD                                  -> 2de7787abffe061dc0cd6cdaaa9d83cb22434f8c
git rev-list --count origin/main..main              -> 41   (nothing pushed)
uv run pytest -q                                    -> 184 passed, 1 skipped
uv run ruff check .                                 -> All checks passed!
uv run python -m lemmi_ai_kit audit-skills \
  --skills-dir src/lemmi_ai_kit/assets/skills --fail-on major
                                                    -> 3 MAJOR + 2 MINOR, exit 1
                                                       (all five OD-1 findings still open)
ls src/lemmi_ai_kit/assets/skills | wc -l           -> 38
ls .specs/i4-pack-split/                            -> roadmap.md execution-plan.md topology.md
git status --porcelain | grep -c '^ M'              -> 6   (all the concurrent session's)
```

**Where it stops — three limits, stated rather than buried:**

- **No install was performed.** `codex`, `claude`, `cursor-agent` and `grok` are absent from PATH, so
  every claim about how the split behaves at install time is doc-derived or inherited from the
  2026-08-22 fixtures. That is the reason `R-1` and `OP-I4-2` exist.
- **`git ls-files --error-unmatch .specs/i4-pack-split/roadmap.md` returns non-zero, deliberately.**
  Both planner skills mandate committing these documents; operator ruling **F5** forbids it and
  `.git/info/exclude` enforces it. The ruling wins. **The consequence is that the plan exists in one
  copy, on one machine, with no history, inside a tree `git clean -xdf` deletes silently** — and
  `docs/research/` is untracked *without* being ignored, so plain `git clean -fd` reaches this
  handoff too. If the plan matters, copy it outside the repository folder.
- **`plan-critic` ran fully on the original documents.** On the revised documents I ran targeted
  mechanical re-verification (18 checks) plus a dimension pass over the fix diff — which is what
  found the shell-portability defect — but not a second full five-dimension walk.

## 8. Cross-session note — a peer is live in the tree I4 must move

A concurrent session is working `session-retrospective` **right now**. Six tracked paths are dirty,
five of them inside `src/lemmi_ai_kit/assets/skills/session-retrospective/`, and the untracked count
moved **13 → 15 while this plan was being written**. Two of I2's W2.4 deliverables
(`tests/test_upstream_sync.py`, `docs/upstream-sync.toml`) are still untracked and assert against the
skills-tree location the restructure moves.

**I touched none of it, and neither should the next session.** This is `PRE-1` and it blocks every
row in the plan. The check, in Git Bash:

```
git diff-files --quiet; echo $?          -> want 0; it is 1 today
for p in tests/upstream_sync.py tests/test_upstream_sync.py \
         docs/upstream-sync.toml docs/syncing-from-upstream.md; do
  git ls-files --error-unmatch "$p" >/dev/null 2>&1 || echo "UNTRACKED $p"
done                                      -> want no output; all four print today
```

## 9. Sequencing recommendation

1. **Clear `PRE-1` first.** Ask the `session-retrospective` session to commit or revert. Nothing in
   I4 is safe to start before that, and it is the cheapest item on the whole board.
2. **Then dispatch `R-1` alone** — read-only, cheap, and it is the falsifier. It needs `codex`
   (OP-I4-2), so pair the two asks.
3. **`I-1` can run beside `R-1`** — disjoint file sets, and it is the entire minimal initiative.
   If the operator declines the split at Gate 1, `I-1` plus the adoption guide is the whole of I4.
4. **Do not start `I-2` until Gates 1 and 2 are both closed.** It is one commit or none, it cannot be
   checkpointed, and a stopped `I-2` is discarded rather than resumed.
5. **Read `roadmap.md` §1.1 before approving anything expensive.** Two-thirds of the charter's own
   minimal viable initiative has already shipped — Gate C passed, the rename landed. What remains of
   the minimal path is one hygiene session, one document, and a close.
