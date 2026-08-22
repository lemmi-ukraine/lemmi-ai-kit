# I1 + I3a — self-challenge and completion review

**Dated:** 2026-08-22, at the end of the session that executed I1 and I3 Part A.
**Method:** adversarial. Every claim re-measured; the point is to find what is wrong
with the work, not to certify it. Findings are stated against my own output.

---

## 1. The check that should have been part of "done" and was not

**I reported completion twice before verifying that the four branches integrate.**
Each was green in isolation; none had been merged with the others. "Each part passes"
is not "the whole passes", and the gap was invisible because every individual gate was
green.

Run at review time, `main` → merge all four → full gate:

```
merged i1-decouple-prompt-skills, f3-stale-counts,
       i3a-contribution-surface, readme-drop-unbacked-refresh-claim   all clean
skill dirs 29 · manifest entries 29 · README "29 skills" · refresh claim 0
ruff clean · ruff format clean · basedpyright 0 errors · pytest 39 passed
```

The result was fine. That does not retire the criticism: the check cost 90 seconds and
should have run before the first completion claim, not after a prompt. `git merge-tree
--write-tree` does the conflict half without touching a shared working tree, so there
was no cost excuse either.

**Carry forward:** for any multi-branch delivery, "done" includes the merged gate.

## 2. Two dead links shipped through 15 commits

`.github/ISSUE_TEMPLATE/bug.yml` and `.github/PULL_REQUEST_TEMPLATE.md` used
`../blob/main/<file>` — a relative path guessed from the file's position in `.github/`.
Neither renders in a context where that resolves: an issue form renders in the
issue-creation UI, a PR template in the compose view, both outside the file's own
directory.

They would have been dead for precisely the audiences they were written for: a reporter
being steered away from filing a security issue publicly, and a contributor being shown
the license they are agreeing to.

**What makes this a slip rather than an unknown:** `config.yml`, in the same directory,
already used the absolute URL correctly. The right answer was adjacent and was not
applied consistently. Fixed at review time.

**Structural cause:** nothing in this repo checks link targets. The hygiene tests check
*patterns*, `test_assets.py` checks that `references/…` links resolve *inside* the asset
tree, and no check covers markdown links in the community files. A future guard could
close it; not added here, to avoid growing scope during a review.

## 3. Two Definition-of-done rows were overstated, and are now corrected

The handoff's DoD table claimed **all five** I3a checks passed. Two did not.

| # | Claimed | Actual |
|---|---|---|
| 4 | "**pass** by file presence" | **UNVERIFIED.** File presence is not the check. GitHub's community-standards checklist lives in Insights → Community Standards, needs the web UI, and is unreadable on a private repo. |
| 5 | "**pass** — executed literally in a fresh clone" | **PARTIAL.** The content was verified, but the word *literally* was wrong: CONTRIBUTING's own first command (`git clone https://github.com/…`) fails for an outsider, so a local-path clone was substituted. |

Both resolve at the flip with no code change. Neither is a defect in the deliverable —
they are defects in how confidently it was reported, which is worse in a document whose
whole job is to be trusted by the next session. Table corrected.

## 4. A deviation I chose and did not fix — the operator may reasonably disagree

The charter is explicit that a legal reviewer should see `LICENSE` **alone** in its
diff. I put L1/L2/L3 plus the read-only research on **one branch**, which mixes three
risk classes and trips the topology's own class-counter trigger (TOOLING 7, DOCS 8,
other 1).

I traded charter compliance for shared-checkout safety: four sessions shared one
working tree and one `.git`, and every branch switch risks yanking the tree from under
a peer mid-write. Commit-level isolation and L1→L2→L3 order were preserved, so the
*dependency* property holds; what is forfeited is one-PR-per-layer.

**This is a judgment call, not a necessity.** The stack is cleanly separable at commit
boundary `1d61cae` with no history rewrite, every commit byte-identical. If the charter
instruction matters more than the concurrency risk, it is still cheap to honour. Left
open deliberately rather than resolved unilaterally.

## 5. Claims I made and then had to correct

Recorded because the pattern matters more than the individual errors: five of the seven
were caught by re-measuring my own output or by peer challenge, and two of those were
**over-corrections** — conceding a valid point and then overshooting what it implied.

| Claim | Correction | Caught by |
|---|---|---|
| "The charter attributes the triad to the wrong project" | It *asks* the question; no attribution exists in the repo. Preventive, not corrective | peer |
| "`30+ skills` is already false" | Circular — 29 *is* the I1 state, so `30+` is true at 33 today | peer |
| "Both drive-letter allowlist entries are gone" | One remains, necessarily, in the file defining the rule | peer |
| `SKILL.md:387` cited as an IDE-path violation | It is a *guard*… | me |
| …then withdrawn as "arguing against the finding" | **Over-correction.** It is a *conditional authorization* — weak evidence *for* | peer |
| "12 occurrences of the source-project name" | 13; correct when measured, changed by a peer's edits | peer |
| A peer's "the manifest↔disk check is one-directional" | Rejected — `shipped != listed` is set equality; verified by creating an unregistered skill dir (8 failed, 7 errors) | me |

**The transferable lesson:** after conceding a correction, re-derive the claim instead
of inheriting the corrector's framing. That worked in the last case — going to the
sibling entries of an "Anti-patterns" list settled the grammar dispute on evidence
rather than on either party's reading.

**And a near-miss worth more than any of the above:** twice, a regex retyped into a
shell heredoc was mangled by escaping and appeared to match `cli:main`. Both times the
next step would have been a false "your pattern is broken" report. Importing the
compiled pattern cleared it. That failure hit two sessions inside an hour, and it is
the reason the tracked-tree scan *imports* `_FORBIDDEN` rather than restating it.

## 6. Scope discipline — measured, not asserted

| Check | Result |
|---|---|
| Skill assets touched on I3 branches | **0** (`i3a`, `readme-drop`) |
| README changed on `i3a` (the Part B hard stop) | **0** |
| `tasks/` or `.specs/` ever committed | **0** on all four branches |
| README edits made | 2, **both explicitly authorized** as surgical exceptions |
| Unauthorized escalations acted on | **0** — a peer twice relayed an operator ruling; both times it was put back to the operator before acting |

Two things deliberately **not** done, each with the reason recorded rather than left as
a silent gap: `plugin marketplace add` was not run (it would modify the operator's real
plugin configuration and belongs to I4's Gate C), and `tasks/`/`.specs/` were not
gitignored (it looks free but pre-empts the `.specs/` convention I2 and I4 discuss
shipping).

## 7. What is actually complete

- **I1** — all 6 DoD checks verified as commands. 8,734 words removed, cost recorded in
  the removal commit. 12 edit sites, not the charter's 10; three charter errors
  corrected in writing.
- **I3a** — 3 of 5 DoD verified, 2 blocked on the flip (§3). Six community files, a
  license-drift test across three sources, a tracked-tree hygiene guard, and four
  research documents. Every test that guards something was verified by deliberate
  breakage and then restored.

## 8. Open, and none of it mine to close

| Item | Owner | Deadline |
|---|---|---|
| Traffic baseline capture — 14-day API retention | **unowned** | **2026-08-29, or unanswerable forever** |
| Codex install block the README advertises and nobody can verify | **unowned** | before the flip |
| Disclosure: is the planning record private, publishable after a rewrite, or publishable as-is | operator | before committing `tasks/` |
| OP-3 — its rationale expires at the flip | I4 | before 2026-08-29 |
| `support@lemmi.io` — domain accepts mail; the alias is unconfirmed | operator | one test message |
| LICENSE-alone re-split (§4) | operator | any time, cheap |

**The single highest-risk item is the first one**, because it is the only one that
becomes permanently impossible rather than merely late.
