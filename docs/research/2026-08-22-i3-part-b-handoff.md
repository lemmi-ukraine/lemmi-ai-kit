# I3 Part B — handoff

**Written:** 2026-08-22, after Part A landed and its checks were run.
**Status:** Part A complete. Part B **not started, deliberately.**
**Branches:** `i3a-contribution-surface` (15 commits off `main`), plus two authorized
surgical exceptions — `f3-stale-counts` (4, off `i1`) and
`readme-drop-unbacked-refresh-claim` (1, off `main`).

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
| later | — | this handoff; two peer-review rounds; the tracked-tree hygiene guard; the review-criteria and dead-field fixes; two unresolvable links corrected |

**Definition of done, I3a — three pass, two cannot be signed while the repo is private.**
Corrected 2026-08-22; an earlier version of this table claimed all five, which overstated
4 and 5. See [the completion review](2026-08-22-i3a-completion-review.md).

| # | Check | Result |
|---|---|---|
| 1 | LICENSE matches both manifests, verified by a test | **PASS** — widened to 3 sources; test verified by deliberate breakage |
| 2 | CONTRIBUTING / CoC / SECURITY exist, each naming a real contact and process | **PASS** — `support@lemmi.io`, domain confirmed to accept mail (full Workspace MX + SPF); the alias itself is unverified |
| 3 | 3 issue forms + PR template | **PASS** — 4 forms, all validated against the GitHub issue-forms schema |
| 4 | Community-standards checklist complete | **UNVERIFIED — not a pass.** Every required file is present, but that is *not this check*: GitHub's checklist lives in Insights → Community Standards, which needs the web UI and is unreadable on a private repo. Signable only at the flip. |
| 5 | Clone → four checks passing using only `CONTRIBUTING.md` | **PARTIAL.** Content verified — a clone at `fd6d8fb` ran `uv sync --dev` and all four checks clean. But CONTRIBUTING's *literal* first command (`git clone https://github.com/lemmi-ukraine/lemmi-ai-kit`) fails for an outsider, so a local-path clone was substituted. The instruction is correct and not yet executable by its audience. Resolves at the flip, no code change. |

Full CI gate green at every commit: `ruff check`, `ruff format --check`,
`basedpyright` (strict, 0 errors), `pytest` — **37 on this branch, and 39 on the
merged result of all four branches**, which was verified rather than assumed. See the
completion review.

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

## Found in passing, deliberately not crossed — I2/I4 territory

`learning-consolidator` hardcodes IDE-specific paths: **29 occurrences** — 23
`.cursor/` and 6 `.kiro/` — across 26 lines in `SKILL.md` and
`references/cross-reference-targets.md`. Meanwhile `skill-reviewer/SKILL.md:153`'s
portability check reads *"No IDE-specific references (Cursor, VSCode, Kiro) unless
justified."* The kit ships one skill pointing at these paths and another forbidding
it.

The load-bearing instances are the unconditional ones — `SKILL.md:256`
(*"`.cursor/rules/{skill-name}.md`"*) and `cross-reference-targets.md:77` (a checklist
checkbox on the Kiro path). `SKILL.md:257` is conditional (*"if the skill affects
conventions"*).

**`SKILL.md:387` is not exculpatory — do not read it that way.** It sits in an
"Anti-patterns" list as *"Do NOT create cursor rules or kiro steering docs **without
checking existing ones for overlap**"*, which is a **conditional authorization**, not
a prohibition: it presumes these files get created and only requires an overlap check
first. The sibling entries confirm the reading — *"Do NOT delete entries without user
approval"* permits deletion with approval, while *"Do NOT skip skill-reviewer
validation"* is a flat ban. So :387 is weak evidence **for** this finding, not against
it: the kit instructs creating IDE-specific files, just carefully.

Two structural points for whoever owns this:

1. **Nothing mechanical catches it.** `test_assets.py`'s `_FORBIDDEN` has no
   `\.cursor/` or `\.kiro/` pattern, so `skill-reviewer:153` is enforced by human
   review only.
2. **The rule says "unless justified", so the cheap fix is probably to state the
   justification** rather than strip 29 references: these are discovery targets in
   *other people's* repos — places a consolidator looks for existing guidance — not
   this repo's own paths. That is a defensible justification; it is simply nowhere
   written down.

## The pre-flip gate — the concept the program plan lacks

The operator intends to publish in ~1 week (≈2026-08-29). The wave plan puts I3b in
Wave 4, behind multi-session I2 and large I4. **Neither fits in seven days.** So the
plan has no state in which the repo is publication-ready on the stated date, and no
gate that asks whether it is.

Four items must be true before the flip, and none of them is Part B's README rewrite:

1. **Four stale public-facing counts — one provenance, one commit, one owner.**

   | Site | Says | True today | After I1 |
   |---|---|---|---|
   | `README.md:3` | "33 skills" | ✔ (33) | ✘ |
   | `README.md:108` | "all 33 skills" | ✔ (33) | ✘ |
   | `.claude-plugin/marketplace.json:9` | "30+ skills" | ✔ (33 is 30-plus) | ✘ |
   | `.codex-plugin/plugin.json:24` | "30+ skills" | ✔ | ✘ |

   Measured: `main` 33, `i3a` 33, `i1-decouple-prompt-skills` **29**.

   **All four are true today and all four break at the same instant — the I1 merge.**
   An earlier draft of this document called `"30+"` "already false"; that was circular
   reasoning, because 29 *is* the I1 state. What actually predates I1 is only `"30+"`
   understating 33 — vague, a style wart, not a flip blocker and not worth its own
   owner.

   So the provenance of the *falsehood* is uniformly **I1**, and the fix is one commit
   on `i1-decouple-prompt-skills`. Splitting these by owner is the failure mode to
   avoid: only one pair reads as "the README", so a split ruling risks the other two
   being missed entirely.

   Note on latitude, stated rather than assumed: the Part B hard stop names
   `README.md`, so it does not literally bar the two manifest files. But its *reason*
   does — `.claude-plugin/marketplace.json:9` contains `/lemmi-ai-kit:kit-setup`, an
   invocation I4 changes, which is exactly what the stop exists to protect. The
   charter also assigns manifest `description` fields to I3b. Either way, correction
   above makes one commit on `i1` the cleaner route.
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

   ~~**Standing gap either way:**~~ **Closed** — `tests/test_publication_hygiene.py`
   now applies all nine patterns to every tracked file outside `assets/`. So both
   `tasks/` and `.specs/` fail CI the moment anyone commits them, which is the
   behaviour we want: the decision can no longer be made silently.

   ### And the string is not the problem — do not treat this as a hygiene question

   A proposal to **allowlist** the occurrences was put forward on the grounds that all
   of them "discuss the ban", which is the category both tests already exempt. Checked
   against the files: **it does not hold.** Of 17 occurrences, roughly 10 are
   substantive references *to* the private project rather than discussions of the rule
   — paths into it (`lemmi-ai-api/.claude/skills/`), a git command run against it
   (`git -C ../lemmi-ai-api log …`), its total skill count (43), and the statement that
   the kit was extracted from it. Allowlisting those would convert a working guard into
   a rubber stamp.

   **But stripping the string would not make these files safe either, and that is the
   more important point.** Even with every mention of the name removed,
   `tasks/I2-TECH-port-upstream-skills.md` still publishes:

   - a **named inventory of a private repository's skills** — 13 upstream-only
     entries, each with a word count and a dependency count
   - internal script names (`audit_cleanup_targets.py`, `ai_files_lint.py`)
   - a product-line attribution: two skills marked *"Non-portable — Lemmi interview
     product"*
   - the private repo's divergence profile against this one

   Redacting the name makes that inventory **unattributed, not safe**. A
   hygiene-contract exemption cannot resolve a disclosure question, and treating it as
   one would answer the small question while leaving the large one untouched.

   **The pressure to commit has already been removed.** The stated reason to commit
   these trees was loss risk — four charters and the plan artifacts existing as a
   single uncommitted copy. A verified byte-for-byte backup now sits outside the
   working tree, which mitigates loss without publishing anything. So the tension
   between "commit them for safekeeping" and "do not publish them" dissolves: keep
   them untracked, and the loss risk is already handled.

   **Recommendation:** do not commit `tasks/` or `.specs/` to this repository. If the
   planning record should be public, that is a rewrite — not a redaction — and it is a
   separate decision from I3. Gitignoring both trees would make the accident
   impossible, but note it may collide with the `.specs/` convention that I2 and I4
   discuss shipping, so it is not a free change.
3. **The traffic baseline is a 14-day window.** It must be captured **on** the flip
   date. Nobody owns this.
4. **The install path.** Reachability clears itself at the flip; the Codex
   `"path": "./"` bug does not, and I4's Gate C has never been tested against this
   repository — only against vendor docs.

   **For whoever owns I4 — a cheaper mitigation than an alias, with what is and
   is not verified marked.** Publishing on 2026-08-29 expires OP-3's rationale
   (program line 193: *"breakage is near-zero now and compounds weekly"* — near-zero
   was a property of being private). Three mitigations existed; the flip date and
   the README restriction remove two, leaving only a compatibility shim. On that:

   | Shape | Status |
   |---|---|
   | Host-level skill aliases | **No mechanism found.** Neither manifest has an alias table, and the `/lemmi-ai-kit:` namespace derives from the plugin *name*. Whether either host supports aliases is unresearched — likely not. |
   | A **deprecated plugin entry** beside its successors, sharing the skills path | **Format permits it** — both marketplace files already use a `plugins` **array**. Old `/lemmi-ai-kit:<skill>` invocations would keep resolving because the old plugin still exists, with nothing aliasing anything. |
   | Duplicate skill directories under old names | Works, but doubles the tree I2 just refreshed. |

   **Verified here:** the array exists in both files; and **neither marketplace test
   asserts `len(plugins) == 1`** — `test_plugin.py` builds `{p["name"]: p for p in
   plugins}` and looks up by name, so a second entry passes both tests unchanged.
   **Not verified:** whether Claude Code resolves two plugins sharing one skills
   directory, and Codex's `source.path: "./"` defect is an independent unknown on
   that path. Test the deprecated-entry shape first — it is the cheapest to falsify.

   **Two traps for whoever implements this, both measured:**

   1. **Fixing the Codex manifest alone turns the suite red.**
      `test_plugin.py:89` asserts `source["path"] == "./"` — the exact shape §5b says
      Codex rejects. So the test defends the defect. Correcting the manifest without
      the test is a manifest edit *plus* a test edit, and someone who does the manifest
      first will see a failure and may conclude their fix was wrong.
   2. **The shim would ship untested, and is one cleanup commit from vanishing.** Both
      marketplace tests look up `entries[_claude_plugin_json()["name"]]` — the plugin's
      *current* name. After a rename that resolves to the **new** name, so a deprecated
      old entry is invisible to the suite: nothing asserts it exists. A shim whose whole
      purpose is absorbing a breaking change must carry its own test — assert the old
      name is still present and still resolves — or a later tidy-up deletes what every
      pre-rename install depends on, with CI green. Same defect class as the scan-scope
      gap above, one layer up: the guard does not look there.

   **The pressure runs one way.** If every shim shape fails, this is not a balanced
   choice between accepting breakage and dropping the rename: dropping it to protect
   adopters from breakage would undermine D4, and D4's reasoning — *"nobody adopts a
   skill branded with another company's name"* — is **strengthened** by going public,
   not weakened, because outside adopters become the entire point. So "re-decide
   OP-3" reads like a live trade-off and is not one.

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

**Delaying is not uniformly safer — the pre-flip items do not all move the same way.**
Worth knowing before the date is chosen, because "hold the flip" reads like it relaxes
every blocker and it does not:

| Item | Sensitivity to a later flip |
|---|---|
| Stale counts (§1) | **Neutral.** They break when **I1 merges**, not when the repo flips. The date only decides whether they break in public. |
| Scan-scope gap (§2) | **Buys time on the exposure**, but the gap itself outlives any date — `docs/research/` stays unguarded either way. |
| Traffic baseline (§3) | **Neutral**, but the owner and the 14-day window move with the date. Re-anchor, do not forget. |
| Marketplace install (§4) | **INVERTED — a delay costs you.** A private repo is *what blocks* `plugin marketplace add`. Going public is the fix. This is a blocker on *signing I4's Gate C*, not a blocker on flipping, and holding keeps it open longer. |
| `README.md:56` refresh promise | **Buys real time.** Move the flip past I3b and build-or-retract stops being an emergency and becomes I3b's ordinary scope. |
| IDE-path references | **Independent** of the date entirely. |

Net: a later flip buys time on the count fix's public exposure, the scan gap, and the
refresh promise — and costs time on the one item that only publication can resolve.
