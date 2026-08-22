# I3 Part B — handoff

**Written:** 2026-08-22, after Part A landed and its checks were run.
**Status:** Part A complete. Part B **not started, deliberately.**
**Branch:** `i3a-contribution-surface`, 4 commits off `main` (`f03ce20`).

`initiative-planner` Step 0 on Part A's scope answers **yes / no / no** — more than
one deliverable, but the work does not outlive the session and no approval gate
remained once OQ-2 and OQ-3 closed. So no `.specs/` decomposition was produced *for
Part A*. One already exists for I3 as a whole, written by a parallel session at
`.specs/i3-oss-discoverability/`, and Part A was built against its layer stack rather
than re-planned. **I3 as a whole does clear Step 0** (Part B outlives this session and
has four open operator gates), which is why this handoff exists and a pro-forma
roadmap does not.

## What landed

| Commit | Layer | Content |
|---|---|---|
| `1d61cae` | L1 | `LICENSE` — MIT, alone in its own commit |
| `b4a8204` | L2 | `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, 3 issue forms + `config.yml`, PR template |
| `fd6d8fb` | L3 | License-drift test across 3 sources; `pyproject.toml` license + `license-files` |
| `0f82e5f` | S1 | `docs/research/` — D9 reachability, D10 anchor terms, D11 dogfood verdict |

**Definition of done, I3a — all five verified as commands:**

| # | Check | Result |
|---|---|---|
| 1 | LICENSE matches both manifests, verified by a test | **pass**, widened to 3 sources; test verified by deliberate breakage |
| 2 | CONTRIBUTING / CoC / SECURITY exist, each naming a real contact and process | **pass** — `support@lemmi.io` |
| 3 | 3 issue forms + PR template | **pass** — 4 forms; all validated against the GitHub issue-forms schema |
| 4 | Community-standards checklist complete | **pass** by file presence (GitHub's own checklist is not readable while private) |
| 5 | Clone → four checks passing using only CONTRIBUTING.md | **pass** — executed literally in a fresh clone at `fd6d8fb` |

Full CI gate green at every commit: `ruff check`, `ruff format --check`,
`basedpyright` (strict, 0 errors), `pytest` (33 passed).

## Stated deviations — not passes

1. **One branch, not three.** The topology assigns L1/L2/L3 separate branches so a
   legal reviewer sees `LICENSE` alone in one PR. Commit-level isolation was
   preserved and the L1→L2→L3 order holds, but one branch is one PR. **Reason:** four
   sessions share one working tree and one `.git` (`git worktree list` shows a single
   entry). Every branch switch yanks the tree out from under whoever is mid-write.
   Forfeiting one-PR-per-layer was judged cheaper than risking lost work.
2. **Risk classes are mixed on this branch.** The topology's own counters fire:
   PACKAGE 0, TOOLING 6, DOCS 7, other 1. Its trigger says re-split the same day.
   Not done, for the same reason as (1).
3. **S1 is not a Lane J sibling.** The research documents landed on the same branch
   rather than off `main`. Same reason.

## Part B — what remains, and what changed under it

Everything below is Wave 4, gated behind I4's Gate D because it names plugin names,
skill names, or install commands that I4 changes.

**Findings from Part A that Part B must consume:**

- **The triad's attribution splits across two projects — preventive, not a fix.** The
  charter *asks* which project popularized `requirements → design → tasks`; it does
  not answer it, and no attribution exists in the repo today. Do not go looking for a
  charter error. The answer: Spec Kit popularized the *term* (its phases are
  `constitution/specify/plan/tasks/implement/converge`), while the *triad* is **AWS
  Kiro's** exactly. Anchor the term on Spec Kit, the triad on Kiro.
- **`llms.txt` is dropped** — ~10% adoption, no standards-body recognition, no
  governance body. Do not present it as a standard.
- **"blameless retrospective" needs rewording.** The SRE term is blameless
  *postmortem*; `session-retrospective` is an Agile-sense retrospective.
- **GitHub shipped native stacked PRs on 2026-07-31.** Three weeks old. Do not
  position `stacked-pr-planner` against "GitHub does not support this".
- **The kit's two strongest anchors** are `AGENTS.md` (Linux Foundation stewardship,
  60k+ projects) and generative engine optimization (peer-reviewed, KDD 2024).
- **The GEO paper's own finding** — verifiable statistics, credible quotations, cited
  sources produce the largest visibility gains — means honesty and reach point the
  same direction here.
- **`README.md:56` describes a mechanism that does not ship.** The marker/refresh
  claim is unbacked by the CLI, the templates, or any test. Fix the sentence or ship
  the mechanism.
- **Two dogfooding inconsistencies** to resolve before the README claims either: the
  kit prescribes Conventional Commits and this repo's history does not follow it; and
  the scaffolded `AGENTS.md` tells you to replace commands that are already correct.

**Still open, unchanged:** OQ-5 (docs site), OQ-6 (public `.ai/learnings.md` as a
curated asset), OQ-7 (Codex parity in the README). All Wave 4, all operator.

## The pre-flip gate — the concept the program plan lacks

The operator intends to publish in ~1 week (≈2026-08-29). The wave plan puts I3b in
Wave 4, behind multi-session I2 and large I4. **Neither fits in seven days.** So the
plan has no state in which the repo is publication-ready on the stated date, and no
gate that asks whether it is.

Four items must be true before the flip, and none of them is Part B's README rewrite:

1. **Four stale public-facing counts.** `README.md:3` and `README.md:108` say
   "33 skills"; `.claude-plugin/marketplace.json:9` and `.codex-plugin/plugin.json:24`
   say "30+ skills". Truth after I1 is **29** — and "30+" is false too, not merely
   imprecise. The README pair is correct on `main` today and goes wrong the moment I1
   merges; the manifest pair is already wrong. The manifest pair matters most, because
   that is what a marketplace listing surfaces.
2. **The private source project's name — and this is two questions, not one.**
   `lemmi-ai-api` is an **explicitly banned pattern** in `tests/test_assets.py:19`,
   labelled "source-project reference". But that test scans `assets_root()` only.

   - **The hygiene question** is `tasks/` alone: **13 occurrences across 4 files**
     (`00-KICKOFF` 3, `00-PROGRAM` 4, `I1` 2, `I2` 4; `.specs/` has zero). Untracked
     today, so it **resolves for free by staying untracked** or being gitignored.
   - **The disclosure question is already answered**, and separating it matters.
     **Three tracked files already name it** and go public regardless of what happens
     to `tasks/`: `tests/test_assets.py:19` (the rule), `CONTRIBUTING.md:73` (a table
     row describing it as "a reference to the private source project nobody else can
     read"), and this document. All three fall under the contract's own
     *teaches-or-implements-the-rule* exemption — the same principle as its
     `_ALLOWLIST` — so none is a defect. But answering only the hygiene question
     leaves the operator believing the name is out when it is not.

   **Standing gap either way:** `test_assets.py` scans `assets_root()`, so every
   top-level tree added since — `tasks/`, `.specs/`, and now `docs/research/`, which
   *is* tracked and flip-bound — is unguarded. Either widen the scan to the tracked
   tree with an explicit rule-teaching allowlist, or state in `CONTRIBUTING.md` that
   the contract covers shipped assets only. Silence is what let a banned pattern reach
   a committed path.
3. **The traffic baseline is a 14-day window.** It must be captured **on** the flip
   date. Nobody owns this.
4. **The install path.** Reachability clears itself at the flip; the Codex
   `"path": "./"` bug does not, and I4's Gate C has never been tested against this
   repository — only against vendor docs.

## The decision this handoff cannot make

Publishing before I4 **invalidates the program's own justification for its wave
order.** `00-PROGRAM-oss-launch.md:116`:

> The breaking rename happens at 0.1.0 with no publish pipeline (pushing `main` *is*
> the release). It is cheap now and expensive once the SEO push lands and people have
> installed. That is the reason I4 precedes I3b rather than the reverse.

OP-3 was accepted on the premise that "breakage is near-zero now". A private repo is
the strongest possible form of that premise, and 2026-08-29 ends it. After the flip,
I4's rename stops being free and becomes a breaking change against real installs.

Two coherent options, and this is an operator call:

- **Flip on 2026-08-29 and re-decide OP-3**, accepting that I4's rename will break
  real installs — or dropping the rename.
- **Hold the flip until I4's Gate D**, keeping the rename free and letting I3b land
  against final names.

Flagged by three independent sessions. It should be decided before the date, not
discovered after.
