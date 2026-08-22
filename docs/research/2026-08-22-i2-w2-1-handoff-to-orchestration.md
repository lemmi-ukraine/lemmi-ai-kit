# Session handoff — I2 W2.1 complete, Gate B open. Read this first.

**Dated:** 2026-08-22, at session close. **Executed:** I2 W2.1 (portability triage) — complete.
**Not started:** Gate B (operator), W2.2, W2.3, W2.4.
**Nothing is pushed. Nothing this session produced is committed.** Three untracked files on
branch `pre-flip`. Committing them is the operator's call.

This is the execution-side handoff for I2. The deliverable it hands over is a decision
input, not code: **no skill was ported and no existing file was modified.**

Companion documents from this session:
- [2026-08-22-i2-portability-triage.md](2026-08-22-i2-portability-triage.md) — the deliverable
- [2026-08-22-i2-w2-1-completion-review.md](2026-08-22-i2-w2-1-completion-review.md) — adversarial review; **it corrects four figures in the triage, read it before quoting numbers**

---

## 1. Branch state — and the one thing that surprised me

I started on `i3a-contribution-surface`; the session ended on **`pre-flip`**, because a
sibling session created it and moved the rename work there while I was measuring.

```
main (f03ce20) ........................ 33 skills, original names
 ├── i1-decouple-prompt-skills (1b5f652)  29 skills — I1 complete
 │    └── f3-stale-counts (e6946d0) ...... 29 skills, CONTAINS i1, counts gated
 ├── i3a-contribution-surface (8e758b7) .. 33 skills, I3a complete
 │    └── pre-flip (d750097) ............. 33 skills, CONTAINS i3a, + the 4 renames
 └── readme-drop-unbacked-refresh-claim .. 33 skills, independent
```

**The two lines I2 depends on are disjoint and neither contains the other:**

| | I1 (deletes 4) | the 4 renames |
|---|---|---|
| `f3-stale-counts` | **yes** | no — still `fable-orchestrate`, `lemmi-*` |
| `pre-flip` | **no** — all 4 prompt skills present | **yes** |

Both edit `assets/manifest.toml`. That is the contended file the program document warns
about, and it is why I checked the merge rather than assuming it.

## 2. The merge is clean *and* semantically correct — verified, not assumed

Run with `git merge-tree --write-tree`, so **no shared working tree was touched** (the
technique the I1+I3a review recommends for exactly this):

```
git merge-tree --write-tree f3-stale-counts pre-flip
  → exit 0, no conflict list                          clean
merged tree 3ed70aed:
  skill dirs 29 · manifest entries 29 · zero mismatch either direction
  renames survived:  orchestrate · python-conventions · test-conventions · vertical-slice
  I1 applied:        all 4 prompt skills absent
  README "29 skills" · test_manifest 29 · test_cli "29 skill(s)"
  full suite, materialized in a scratch git repo:     39 passed
```

A clean merge is not a correct merge, so the second half matters: git resolved f3's
deletions against pre-flip's renames without producing a manifest that disagrees with
the tree. **That means I2 has a legal starting point today** — merge those two, and the
result is the post-I1, post-rename, 29-skill tree that W2.2 refreshes.

> Caveat on the 39: the scratch copy needed `git init` before
> `test_publication_hygiene.py` could run, because that test shells out to `git ls-files`
> and correctly refuses to certify a non-work-tree. Without it the run reports
> `37 passed, 2 failed` — a harness artifact, not a defect. Do not read a bare 37 as a
> regression.

## 3. Gate B — what the operator must decide, in priority order

The triage's §11 has the full reasoning. Condensed, with the one decision that dominates
first:

**D1 (dominant) — ship the stacked-PR workflow document, 2,711 words, through the
scaffolding channel?** This decides whether the initiative proceeds at full scope:

| | Non-portable candidates | Charter's 40% falsifier |
|---|---|---|
| doc ships | 3 of 12 (25%) | does not fire — full scope |
| doc does not ship | 5 of 12 (42%) … 8 of 12 (67%) | **fires under every counting rule** |

Five candidates reference it; two of them state outright that they do not own the
mechanics. The range is a classification judgment, not measurement error — the review's
§3 explains why the range is the honest form and why the conclusion holds across all of
it.

**D2 — dependency handling, revised from OP-2.** Confirm *(c) substitute*, but paired
with *(a)* and split by mechanism rather than by "linters vs docs":
- **(a) ship** the skill-owned scripts (all stdlib-only, all arrive with their skill; already the kit's pattern via the shipped session extractor). Rewrite the **14 same-skill** call sites to the skill-directory variable.
- **(c) substitute** for the **15 cross-skill** sites, where no portable idiom exists. `lint` + `audit-skills` cover 9 of the 14 in scope.
- **never (b) strip.**

**D3 — OQ-5: no hooks story needed for this port.** Zero skills require a hook; the four
references are prose case studies to genericize.

**D4 — OQ-2 / `usage-guard`: defer.** OP-5 admitted it against a 1,764-word estimate; it
is 12,509 words, 72% PowerShell, writes the user's settings file, installs a scheduled
task.

**D5 — OQ-6: explicit correspondence map, not name-derivation.** Name-keying is already
falsified — see §4.

**D6 — OQ-3 needs no decision.** The rename happened during this session, in I4's wave.

## 4. Read this before writing the drift check

**Name-based correspondence is falsified, and this session is the proof.** Four skills
were renamed between `main` and `pre-flip` while I was measuring. A name-keyed check run
against upstream today reports 8 phantom findings out of 43 — an 18% false-positive rate
on day one:

| Kit (post-rename) | Upstream | A name-keyed check would say |
|---|---|---|
| `orchestrate` | `orchestrate` | matches — but only by luck; upstream renamed it too |
| `python-conventions` | `lemmi-python-conventions` | kit-only + upstream-only |
| `test-conventions` | `lemmi-test-conventions` | kit-only + upstream-only |
| `vertical-slice` | `lemmi-vertical-slice` | kit-only + upstream-only |

Store the pairs explicitly. **Pin upstream at `a78ee5a`** (2026-08-22) — that is the
revision every number in the triage was measured against, and it has had **0 commits to
its skills tree since**.

## 5. W2.2 refresh order — use the post-rename names

Reference skills before their citers, then by absolute whole-directory word gap. Ranks
are the triage's §3.

1. **`parallel-session-safety`** — new skill, but port it *first*: it is a reference skill many others cite, 0 hygiene violations, no blockers.
2. **`consolidation-critic`** — before `learning-consolidator`, which gains a Phase 8 dependency on it. Needs D2's CLI (4 cross-skill sites, the most in the set).
3. **`learning-consolidator`** (rank 1, +12,005) — brings the linter with it; 6 same-skill call sites to rewrite.
4. **`session-retrospective`** (rank 2, +9,051) — **but see §6: the extractor is its own task.**
5. Then ranks 3–10 by gap: `test-conventions`, `post-task-review`, `orchestrate`, `task-learnings`, `python-conventions`, `skill-reviewer`, `skill-creator`, `spec-driven-dev`.
6. `hypothesis-validator` alongside `ai-improvement-tracker` (rank 15) — they close one loop.
7. Cosmetic tail (ranks 23–27, ≤61 words each) in one batch, last.

**Contention warning.** `orchestrate`, `python-conventions`, `test-conventions` and
`vertical-slice` were being written *this session*. They are ranks 5, 7, 3 and 17. Start
on the uncontended rows and confirm the rename branches have settled before touching
those four.

## 6. The single most expensive file, and it is not a skill

`session-retrospective/scripts/extract_sessions.py` — **+598 / −21 lines**, 3,453 kit
words against 6,320 upstream, and **both sides moved**:

- the kit dropped a dated learnings citation and generalized a platform-specific note (an extraction edit the hygiene contract enforces, and one of the 31 it would revert);
- upstream advanced its schema version 3 → 4 with additive fields, deterministic candidate selection replacing model-side arithmetic, and slash-command capture.

Neither side is discardable. **Plan it as its own task with its own review, not as part
of a skill refresh.** This is also the concrete answer to OQ-4: three-way merge, never
overwrite-then-clean.

## 7. One test worth adding early, not at W2.4

The kit removed **19 hard-coded script invocations across 8 skills** during extraction,
replacing them with the skill-directory variable, and **nothing tests for it**. Every
refresh in W2.2 will re-introduce them from upstream, and only human diligence stands
between that and a regression. It is a one-pattern addition to the hygiene contract and
it converts the port's most repetitive manual edit into an enforced invariant.

Add it **before** W2.2 starts, not in W2.4 — it is worth most while the refreshes are
being done, not after.

## 8. Charter claims to correct before planning

The triage's §12 lists ten. The four that will actively mislead a planner:

| Charter says | Actually |
|---|---|
| Table A's "Words" column | **SKILL.md only** — understates the candidate set 2.6x (38,807 → 100,916); `usage-guard` 7.1x, `feedback-audit` 9.3x |
| "Rows 1–10 sum to +42,155" (twice) | its own rows sum to **+39,959**; correct post-I1 top-ten is **+42,397** |
| "`analyge-logs` → `analyze-logs`" | **no such rename** — the kit never had the typo. Delete the work item |
| the spec-directory convention is unshipped | the kit **already ships it** — 20 references across 8 files, 14 in `spec-driven-dev` |

These are private planning artifacts, so I did not edit them.

## 9. What to re-derive, and what not to

**Do not re-measure** (verified twice this session, second time adversarially): the
27-skill gap ranking and its sums, the 29 hard-coded call sites split 14/15, the hygiene
counts, the three provenance findings (`scout-review` is a kit original; no
`analyge-logs` typo; 0 upstream commits since 2026-08-22).

**Do re-derive:**
- **Anything after upstream moves.** Re-run `git rev-list --count --since` against the `a78ee5a` pin first; if it is non-zero, the gap table is stale.
- **The candidate/refresh split**, if I1 or the renames land differently than §2 assumes.
- **Every figure quoted from the triage's first version.** The review corrected four; use the current file.

## 10. Open limits this session could not close

- **Cross-platform is unverified.** The shipped scripts' tests were never run on macOS or Linux — this platform was the only one available. The charter's "must work on Windows, macOS and Linux" consequence is still open, and D2's (a) is what makes it load-bearing.
- **The skill-directory variable's runtime resolution is assumed.** The whole same-skill/cross-skill split rests on it resolving to the *calling* skill's directory. Both the kit and upstream rely on it, but nothing here executed a skill to prove it. If it is wrong, D2's line moves and more sites go to (c).
- **`audit_skills.py` carries a portability defect** — a hard-coded path depth instead of discovery. Ported as-is into the asset tree it resolves to `src/lemmi_ai_kit`, which is not a repository root. Fix it on the way in, using the working-directory fallback the shipped extractor already uses.
- **The hygiene contract cannot see `.ps1`/`.sh`/`.ts`.** Unexercised today because the kit ships no such file; it becomes real the moment `usage-guard` or any shell-script skill is reconsidered.
- **Prose generalization is unmeasurable by pattern.** The 31-scrub figure is a floor on intentional divergence, not a total.

## 11. If I2 stops here

W2.1 is self-contained and leaves nothing half-done: no skill was touched, no test was
changed, `manifest.toml` is untouched by this session, and the tree is consistent on
every branch. The triage's value does not decay except through upstream drift, which is
measurable against the `a78ee5a` pin.

The charter's own minimal viable initiative is **W2.1 + W2.4 + the ten worst-diverged
skills**. W2.1 is done. If only one more thing happens, the triage argues it should be
**W2.4's drift mechanism** — the content gap is recoverable at any time, but the
6-week-to-3x decay rate is what made this port necessary in the first place, and nothing
currently prevents a repeat.
