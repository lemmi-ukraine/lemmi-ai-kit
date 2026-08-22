# I2 W2.1 — upstream portability triage, and the Gate B numbers

**Measured:** 2026-08-22 · **Deliverable:** I2 W2.1 · **Status:** triage complete, Gate B ready
**Charter:** `tasks/I2-TECH-port-upstream-skills.md` (private planning artifact — not committed to this repository)
**Program:** `tasks/00-PROGRAM-oss-launch.md` (private planning artifact — not committed to this repository)

Upstream baseline: source project at `.claude/skills`, commit `a78ee5a` (2026-08-22).
Kit baseline: this repository at `main`, frozen to a scratch copy for the duration of
the measurement — see §2 for why that was necessary.

**Bottom line.** The initiative survives. The charter's own kill-switch does not
fire: **3 of 12 new-skill candidates are non-portable (25%), against a 40%
threshold** — and two of those three were already declared non-goals. The refresh is
a port, not a rewrite: **31 hygiene violations across 9 of 27 skills**, one skill
above the ~10-site falsifier, and that one is a single find-and-replace.

**But the pre-decided strategy does not survive intact.** OP-2 chose *(c) substitute
a kit-CLI equivalent for the linters and audits*. The measurement says (c) is right
for **15 call sites** and wrong for **14 others**, and the line between them is not
"linters vs docs" — it is **cross-skill vs same-skill invocation**. §6 has the
mechanism. And the whole falsifier verdict rests on one 2,711-word document (§7).

---

## 1. Re-measurement: upstream has not moved, but two charter tables used the wrong metric

The charter's last falsifier — "upstream has changed materially since 2026-08-22" —
**does not hold**:

| Probe | Result |
|---|---|
| commits touching `.claude/skills` since 2026-08-22 | **0** |
| commits touching `.claude/skills` since the kit's last commit (2026-07-09) | **43** — the charter's figure, confirmed |
| upstream HEAD | `a78ee5a`, dated 2026-08-22 |

So the charter's numbers are still current, and I reproduced its methodology exactly
once I found the rule it actually used.

**The measurement rule, stated precisely, because two of my own passes got it wrong
before I pinned it down.** The charter's Table B counts **every file in the skill
directory except compiled-bytecode caches** — SKILL.md, `references/`, `scripts/`,
and stray files. Including bytecode inflates `learning-consolidator` by 11,000 words
and `session-retrospective` by 7,801; excluding `scripts/` deflates them by 8,662 and
9,995. With the right rule, Table B reproduces to the word: `learning-consolidator`
5,238 → 17,243 (**+12,005, 3.29x**), `session-retrospective` +9,051 (2.00x),
`test-conventions` +4,089 (**3.62x**), `post-task-review` +3,915 (2.69x),
`task-learnings` +2,720 (2.76x). The operator's two rules hold and Table B is sound.

**Table A is not.** The charter's upstream-only inventory was measured **SKILL.md
only** — the metric its own Context section forbids. It understates the new-skill
volume by 2.6x in aggregate and by up to 9.3x per skill:

| Skill | Charter's "Words" | Whole directory | Understated by |
|---|---|---|---|
| `usage-guard` | 1,764 | **12,509** | 7.1x — 9,049 words of it PowerShell |
| `initiative-cleanup` | 5,738 | **15,311** | 2.7x |
| `initiative-planner` | ~2,400 | **9,502** | 4.0x — the charter's own row says "Refs dir 4" |
| `interview-transcript-analysis` | 2,349 | 6,598 | 2.8x |
| `branch-diff-review` | 2,440 | 5,384 | 2.2x |
| `feedback-audit` | 3,296 | **30,792** | 9.3x |
| the other six | correct | correct | — (single-file skills) |
| **all 12 candidates** | **38,807** | **100,916** | **2.6x** |

This matters for planning, not for the decision: the port is 2.6x larger on the
new-skill side than the charter's table implies, and the two largest entries in it are
both non-goals.

**One arithmetic correction.** The charter says twice that its Table B rows 1–10 sum
to **+42,155**. They sum to **+39,959**. The correct post-I1 top-ten figure is
**+42,397**, which differs from both because the rename (§2) promotes `orchestrate`
into 5th place at +3,350 and I1 removes `prompt-engineering-conventions` (+3,116) from
the table. The full 27-skill refresh set is **+48,249**.

## 2. The baseline moved under this session, and it answers two open questions

Mid-measurement, a concurrent session committed `e52e4e2` — *"Drop the Lemmi brand
from the three convention skill names"* — and staged `fable-orchestrate` →
`orchestrate`. My first three measurement passes ran before it, the next two after,
which is how I caught it: a skill count silently changed from 30 shared to 27. I
re-ran everything against a frozen `git archive` of `main` in a scratch directory.
`e52e4e2` changed 16 lines across 11 files, all cross-reference text, so **content
gaps are unaffected**; only names moved.

Two consequences the charter cannot have anticipated:

**OQ-3 is answered by fact, not by decision.** The charter asks whether the
`fable-orchestrate` → `orchestrate` rename happens in I2 or I4's rename wave. It is
happening now, in I4's wave, pulled ahead of the flip. So `orchestrate` is **no longer
a new skill to add** — it is a shared skill to refresh, at 1,770 → 5,120 (**+3,350,
2.89x**), and it belongs in the refresh table at rank 5. That also drops the
upstream-only count from 13 to 12 and makes the charter's "12 candidates + 1 rename"
arithmetic resolve to a clean 12.

**OQ-6 is answered too, and the answer is "not by name".** The charter asks what the
correspondence key for the drift check should be, noting that name-based mapping
"breaks on renames (which just happened once)". It has now happened **four more times
in one commit-pair**. A name-keyed check run today would report `python-conventions`,
`test-conventions`, `vertical-slice` and `orchestrate` as kit-only, and their four
upstream counterparts as upstream-only — **8 phantom findings out of 43**, an 18%
false-positive rate on day one. A drift check needs an **explicit stored
correspondence map** (kit name → upstream name), reviewed when it changes; content
hashing cannot recover a rename either. This is not a preference: name-keying is
already falsified.

## 3. The refresh set — 27 skills, ranked by absolute whole-directory word gap

Post-I1, post-rename. `hyg` is the violation count from the kit's own hygiene contract
run against a raw upstream copy (§4). Dependency classes are §5's.

| # | Skill | Kit | Upstream | Gap | Ratio | hyg | Blocking deps |
|---|---|---|---|---|---|---|---|
| 1 | `learning-consolidator` | 5,238 | 17,243 | **+12,005** | 3.29x | 4 | owns the linter; 7 same-skill call sites |
| 2 | `session-retrospective` | 9,026 | 18,077 | +9,051 | 2.00x | 6 | 5 same-skill call sites; **619-line script merge** |
| 3 | `test-conventions` | 1,559 | 5,648 | +4,089 | **3.62x** | 0 | none |
| 4 | `post-task-review` | 2,313 | 6,228 | +3,915 | 2.69x | 0 | 1 same-skill call site |
| 5 | `orchestrate` *(was `fable-orchestrate`)* | 1,770 | 5,120 | +3,350 | 2.89x | 0 | stacked-PR doc |
| 6 | `task-learnings` | 1,549 | 4,269 | +2,720 | 2.76x | 2 | 2 cross-skill call sites |
| 7 | `python-conventions` | 2,173 | 4,533 | +2,360 | 2.09x | 0 | none |
| 8 | `skill-reviewer` | 3,743 | 6,017 | +2,274 | 1.61x | 1 | owns the audit script; 2 same-skill sites |
| 9 | `skill-creator` | 2,881 | 4,506 | +1,625 | 1.56x | 0 | 1 cross-skill call site |
| 10 | `spec-driven-dev` | 8,773 | 9,781 | +1,008 | 1.11x | 0 | none |
| 11 | `plan-critic` | 2,890 | 3,802 | +912 | 1.32x | 0 | none |
| 12 | `openai-realtime-quirks` | 1,137 | 1,922 | +785 | 1.69x | 0 | none |
| 13 | `analyze-logs` | 5,687 | 6,379 | +692 | 1.12x | **14** | none — 14x one string |
| 14 | `skill-creation-workflow` | 1,367 | 1,988 | +621 | 1.45x | 1 | none |
| 15 | `ai-improvement-tracker` | 1,469 | 2,047 | +578 | 1.39x | 1 | 1 cross-skill call site |
| 16 | `agent-delegate` | 435 | 921 | +486 | 2.12x | 0 | none |
| 17 | `vertical-slice` | 1,296 | 1,781 | +485 | 1.37x | 0 | none |
| 18 | `branch-switch` | 831 | 1,219 | +388 | 1.47x | 1 | none |
| 19 | `ai-changelog` | 1,240 | 1,502 | +262 | 1.21x | 1 | 1 cross-skill call site |
| 20 | `skill-researcher` | 1,341 | 1,531 | +190 | 1.14x | 0 | none |
| 21 | `ai-docs-lookup` | 1,142 | 1,321 | +179 | 1.16x | 0 | none |
| 22 | `skill-content-reviewer` | 1,325 | 1,490 | +165 | 1.12x | 0 | none |
| 23 | `product-brief` | 2,811 | 2,872 | +61 | 1.02x | 0 | none |
| 24 | `research-source-planner` | 5,362 | 5,407 | +45 | 1.01x | 0 | none |
| 25 | `research-source-claim` | 2,225 | 2,227 | +2 | 1.00x | 0 | none |
| 26 | `commit-message` | 766 | 767 | +1 | 1.00x | 0 | none |
| 27 | `parallel-deep-research` | 2,259 | 2,259 | 0 | 1.00x | 0 | none |

Rows 1–10: **+42,397**. All 27: **+48,249**. Rows 23–27 are the cosmetic tail.

**One spurious work item removed.** The charter's row 12 reads "`analyge-logs` →
`analyze-logs`", presenting a typo rename as part of the refresh. **The kit has never
had that typo.** `main`'s tree holds `analyze-logs`, and no commit in kit history
touches any path matching the misspelling. There is no rename to do.

## 4. Hygiene: the "refresh is a rewrite" falsifier does not hold

I ran the real contract, not a reimplementation: staged a copy of the package from
`main` into a scratch directory, replaced all 31 shared skill directories with raw
upstream copies, and ran `pytest tests/test_assets.py` against it. Counts below are
from the test's own code path, with its existing allowlist applied.

| Result | Value |
|---|---|
| Violations, all 31 overwritten skills | 32 |
| Violations, post-I1 (27 skills) | **31, across 9 skills** |
| Worst single skill | `analyze-logs`, **14** |
| Skills above the charter's ~10-site threshold | **1 of 27 (3.7%)** |
| `test_skill_relative_references_resolve` | **passes** |
| `test_ai_state_files_ship_empty` | **passes** |
| `test_every_skill_has_valid_frontmatter` | fails on exactly 1 skill — the rename, expected |

By pattern: 17 source-project references, 4 backup-path references, 4
machine-specific host rules, 3 dated learnings citations, 1 console-encoding
workaround, 1 macOS home path, 1 drive-letter path.

**The one skill over the threshold is the cheapest fix in the set.** All 14 of
`analyze-logs`'s violations are the *same string* — the source project's name — in two
reference files, 13 of them in `references/gcp-query-templates.md`. That is a
find-and-replace, not an authoring session. `session-retrospective`'s 6 are all in
`scripts/`, and 5 of its 11 raw hits are **already allowlisted** by the shipped
contract.

**Verdict: falsifier #2 does not hold.** No skill needs re-authoring from source
material. Budget the refresh as a port with a cleaning pass.

For the 12 new candidates the picture is the same: **12 violations across 6 skills**,
worst 6 (`initiative-cleanup`), and both the frontmatter and reference-resolution
tests pass for all 12 — every `references/` link in every candidate resolves as
shipped.

## 5. The dependency table is two classes, and collapsing them is what makes the port look impossible

This is the finding that changes Gate B. The charter's context table lists eight
dependency rows with a single "Kit ships it?" column, almost all "no". Measured, they
divide into two classes with opposite costs.

**Class 1 — self-describing conventions. Cost to port: zero.** The three-level spec
directory convention (86 refs in SKILL.md files, 115 whole-tree) and the
`tasks/{TECH,FEATURE,…}-*` charter naming (20 / 38) are directories **the skill
instructs the adopter to create in their own project**. Nothing has to ship for them
to work.

And the kit **already ships this convention**: `main` carries **20 spec-directory
references across 8 shipped files**, 14 of them in `spec-driven-dev` — the kit's
third-largest skill — plus 8 charter-path references in 3 files. The convention has
been published since extraction. The charter's headline "86 refs, kit ships it: no" is
measuring a convention as though it were an artifact.

**Class 2 — executable infrastructure. Cost to port: real, and lower than the charter
assumes.** Five scripts and one document. The charter's table renders the scripts as
repo-level infrastructure (`scripts/ai_files_lint.py`). They are not:

| Script | Actually lives at | Words | Third-party imports |
|---|---|---|---|
| `ai_files_lint.py` | `.claude/skills/learning-consolidator/scripts/` | 4,960 | **none** |
| `audit_cleanup_targets.py` | `.claude/skills/initiative-cleanup/scripts/` | 4,481 | **none** |
| `audit_skills.py` | `.claude/skills/skill-reviewer/scripts/` | 1,258 | **none** |
| `drain_audit.py` | `.claude/skills/learning-consolidator/scripts/` | 920 | **none** |
| `extract_sessions.py` | `.claude/skills/session-retrospective/scripts/` | 6,320 | **none** — *kit already ships it* |

Every one is **skill-owned and stdlib-only**. Porting `learning-consolidator` brings
its linter along by construction; porting `skill-reviewer` brings the audit script;
porting `initiative-cleanup` brings its own. No `assets/scripts/` tree is needed, and
the kit already proves the pattern works — it ships `extract_sessions.py` inside
`session-retrospective`, with its own tests and two allowlist entries.

**The one genuine document dependency is small and high-leverage.** The stacked-PR
workflow document is **2,711 words** and is referenced 13 times, and those references
are *delegations*, not citations — "every command, cascade form and verification rule
lives in", "read it there", "run § X in full". Six skills reference it —
`stacked-pr-planner`, `pr-comment-resolver`, `pr-review-concise`,
`parallel-session-safety`, `initiative-planner`, `orchestrate`, together **31,867
words of skill content** — and two of them state outright that they do not own the
mechanics. §11 D1 grades the six by how load-bearing the reference actually is; the
distinction matters, because it is what decides the falsifier. The kit already ships
documents through `assets/templates/` and `assets/ai/templates/`, so the channel
exists.

**One 2,711-word document unblocks 31,867 words of skills. It is the single
highest-leverage item at Gate B.**

**Two dependency classes in the charter turn out not to be dependencies at all.** The
cd-prefix hook (OQ-5) and the settings file: **zero candidate skills require either.**
The four refs live in `pr-review-concise` and `pr-comment-resolver` and are *worked
examples* — a narrated incident about a specific numbered PR where a hook was added
and its registration landed in the wrong layer. Nothing breaks without the hook; the
skill just reads as written for another repository. These need **genericizing, not
shipping**. OQ-5's premise — "porting rules whose enforcement is a hook without the
hook ships the rule as a suggestion" — is sound in general but **matches no skill in
this port**.

## 6. Where the CLI substitution actually earns its keep — and where it does not

OP-2 pre-decided *(c) substitute* for the linters and audits. The measurement supports
(c), but for a different reason and over a different scope, and the correct split falls
on a line the charter never draws.

Upstream invokes skill-owned scripts **two ways**. The portable idiom is the
runtime-provided skill-directory variable; the non-portable one hard-codes
`.claude/skills/<skill>/scripts/X.py`, a project-relative path that only resolves if
the adopter has vendored the skills into their own `.claude/skills/` — which plugin
distribution never does. **The kit already uses the portable idiom exclusively: zero
hard-coded invocations in the shipped tree.** Upstream uses it in 6 files and
hard-codes 29 other sites, so this is upstream inconsistency, not design.

Those 29 sites split cleanly, and the split is the decision:

| | Sites | Fix | Cost |
|---|---|---|---|
| **Same-skill** — the script ships inside the calling skill | **14** | rewrite to the skill-directory variable | mechanical; the idiom the kit already uses |
| **Cross-skill** — the script lives in a *different* skill | **15** | **no portable idiom exists** | this is the real question |

The skill-directory variable resolves to the *calling* skill's directory, so it cannot
address a sibling skill's script. That is why cross-skill calls need substitution — a
mechanism, not a preference. The 15 cross-skill sites target 6 scripts:

| Target | Called by | Sites |
|---|---|---|
| `learning-consolidator/ai_files_lint.py` | `ai-changelog`, `ai-improvement-tracker`, `consolidation-critic`, `hypothesis-validator`, `session-retrospective`, `task-learnings` | 6 |
| `skill-reviewer/audit_skills.py` | `consolidation-critic`, `hypothesis-validator`, `skill-creator` | 3 |
| `session-retrospective/extract_sessions.py` | `interview-transcript-analysis`, `task-learnings` | 2 |
| `learning-consolidator/drain_audit.py` | `consolidation-critic` | 1 |
| `learning-consolidator/test_ai_files_lint.py` | `consolidation-critic` | 1 |
| `feedback-audit/validate_realtime_export.py` | `interview-transcript-analysis` | 1 — both skills are non-goals |

**So: (a) for same-skill, (c) for cross-skill.** Two CLI subcommands — `lint` and
`audit-skills` — cover **9 of the 14 in-scope cross-skill sites**, which is what OP-2
recommended; the mechanism just narrows it from "the linters and audits" to "the
linters and audits *when called from another skill*". Doing (c) wholesale would mean
rewriting three working, tested, stdlib-only scripts as CLI subcommands, editing 29
call sites instead of 14, and re-translating every future upstream change to those
scripts — which directly damages W2.4, the deliverable the charter calls durable.

**One concrete portability defect to fix on the way in.** `audit_skills.py` derives its
root as a **hard-coded path depth** (`parents[4]`) rather than by discovery, plus a
`.claude/skills` join beneath it. Correct upstream; ported into this kit's asset tree
the same expression resolves to `src/lemmi_ai_kit`, which is not a repository root and
holds no skills directory. The other three scripts walk up looking for marker
directories, and the kit's shipped `extract_sessions.py` already uses the right
pattern — walk up for a marker, **fall back to the working directory**. That fallback
is what makes it work from a plugin install, where no ancestor of the script is inside
the adopter's repository at all. Apply that pattern to all four.

## 7. Per-skill port verdict — the 12 candidates

| Skill | Whole-dir | hyg | Verdict | What it needs |
|---|---|---|---|---|
| `initiative-planner` | 9,502 | **0** | **PORT** | stacked-PR doc (1 ref); 15 spec + 9 charter refs are Class 1 — free |
| `stacked-pr-planner` | 4,594 | **0** | **PORT** | stacked-PR doc (4 refs) — its mechanics are *delegated* there |
| `pr-comment-resolver` | 4,743 | **0** | **PORT** | stacked-PR doc (5 refs); genericize 2 hook + 2 settings anecdotes |
| `pr-review-concise` | 4,110 | **0** | **PORT** | genericize the numbered-PR case study; 1 doc ref |
| `parallel-session-safety` | 3,798 | **0** | **PORT FIRST** | 1 doc ref; its 3 linter refs are prose. **Reference skill — port before its citers** |
| `branch-diff-review` | 5,384 | 1 | **PORT** | 1 backup-path reference; 8 charter refs are Class 1 |
| `initiative-cleanup` | 15,311 | 6 | **PORT** | brings its own script; 4 same-skill sites to rewrite; 6 backup-path refs |
| `consolidation-critic` | 1,955 | 1 | **PORT — needs CLI** | 4 cross-skill sites, the most in the set. Gate on `lint` + `audit-skills` |
| `hypothesis-validator` | 1,620 | 1 | **PORT — needs CLI** | 4 cross-skill sites; pairs with `ai-improvement-tracker` (row 15) |
| `usage-guard` | 12,509 | 0* | **DEFER** | see below |
| `feedback-audit` | 30,792 | 1 | **OUT** | charter non-goal, OP-5 confirmed |
| `interview-transcript-analysis` | 6,598 | 2 | **OUT** | charter non-goal, OP-5 confirmed |

**Portable: 9 of 12 (75%). Non-portable: 3 of 12 (25%).** Excluding the two
already-declared non-goals from the denominator: **9 of 10 (90%) portable**.

**`usage-guard`: the zero is not a pass.** OP-5 admitted it "with a portability pass
and the limitation documented". The pass is larger than the charter's 1,764-word row
suggests. Its hygiene score of 0 is **an artifact of the contract not looking**: the
scan covers seven text suffixes, and **9,049 of its 12,509 words are in 12 PowerShell
files** that no suffix matches. I scanned them anyway — they contain zero violations
of the nine patterns, so nothing is hidden. But the patterns do not describe its actual
coupling, which is a class the contract has no rule for: **10 writes to the user's
Claude settings file** in the installer, scheduled-task registration in 4 scripts,
Windows-only environment and CIM calls in 7, an OAuth polling loop, and 61 references
to a statusline rate-limit feed. This is not a skill with portability defects; it is a
Windows service with a skill attached. **Defer it, or ship it explicitly
quarantined.** Either way it should not be counted as ported.

**A standing gap this exposes.** Any future skill shipping `.ps1`, `.sh`, `.ts` or
`.js` is invisible to the hygiene contract — both the asset scan and the tracked-tree
scan filter on the same text suffixes. Widening them is a W2.4 item; today it is
unexercised because the kit ships no such file.

## 8. OQ-4 — intentional divergence is real, and a blind overwrite loses it

The charter suspected this; it is measurable. **11 of 27 refresh skills carry
extraction edits that a raw overwrite would revert**, and the count is exactly the
hygiene number from §4 — **31 scrubs** — because the extraction edits *are* what the
contract encodes. But the tests catch only some of them:

| Edit class | Sites | Caught by the tests? |
|---|---|---|
| Hygiene-pattern scrubs (source-project names, dated citations, machine notes, backup paths) | 31 | **yes** — this is what the contract is for |
| Hard-coded path → skill-directory-variable invocation rewrites | **19 across 8 skills** | **no** — nothing tests for it |
| Prose generalization with no forbidden pattern | unbounded | **no** |

The middle row is the dangerous one: the kit removed 19 hard-coded script invocations
(6 in `learning-consolidator`, 5 in `session-retrospective`, 2 each in `skill-reviewer`
and `task-learnings`, 1 each in four more — 20 if you also count a bare `scripts/`
directory mention) and no test would notice them coming back.
**W2.4 should add that pattern to the contract** — it is a one-line addition and it
converts the port's most repetitive manual edit into an enforced invariant.

**Answer to OQ-4: three-way merge, not overwrite-then-clean** — and the single most
expensive file in the whole initiative is
`session-retrospective/scripts/extract_sessions.py`: **+598 / −21 lines**, 3,453 kit
words against 6,320 upstream. Both sides moved. The kit rewrote a comment to drop a
dated learnings citation and generalize a platform-specific note; upstream advanced its
schema version 3 → 4 with additive fields, deterministic candidate selection replacing
model-side arithmetic, and slash-command capture. Neither side's changes are
discardable. Plan this file as its own task, not as part of a skill refresh.

## 9. `scout-review` — kit original, and the kit is ahead in three ways

The charter's falsifier asks whether `scout-review` is upstream's ancestor. **It is
not. It is a kit original.** Upstream has never had it: no path in any commit, no
commit touching the name, and the string does not appear anywhere at upstream HEAD. The
kit added it in `e14ea23` — *"Rework distribution as a Claude Code plugin; add
scout-review and kit-setup skills"* — alongside `kit-setup`, which the charter already
labels kit-original.

**But the falsifier's underlying worry is correct**, by three other routes:

1. **Two skills where the kit is textually ahead** — `prompt-eng-reviewer` (−7 words)
   and `prompt-domain-reviewer` (−14). I1 deletes both, so the evidence is about to be
   discarded; record it before it goes.
2. **A capability upstream lacks** — `scout-review` (1,818 words) and `kit-setup`
   (937). A genuine reverse-port candidate, and the charter's "Two-way sync" non-goal
   correctly says that is a note for the operator, not a push.
3. **The portability idiom itself** — the kit's exclusive use of the skill-directory
   variable against upstream's 29 hard-coded paths, and `extract_sessions.py`'s
   working-directory fallback. **The kit is ahead of upstream on portability
   engineering**, which is the one axis this initiative cares most about. Every future
   sync should pull content and *keep* the kit's invocation idiom.

**So: stop assuming upstream is always newer.** Not because `scout-review` is an
ancestor, but because on portability the direction of travel is the other way.

## 10. Falsifier scoreboard

| Falsifier | Verdict | Evidence |
|---|---|---|
| >40% of candidates non-portable | **DOES NOT HOLD** | 25% (3/12); 10% excluding declared non-goals — **conditional on §11** |
| Refresh is a rewrite (>~10 hygiene sites/skill) | **DOES NOT HOLD** | 31 violations / 9 of 27 skills; 1 skill over, and it is one find-and-replace |
| No automatable drift correspondence | **PARTIALLY HOLDS** | name-keying is already falsified — 4 renames, 8 phantom findings. An explicit stored map is automatable; derive-by-name is not |
| `scout-review` is upstream's ancestor | **DOES NOT HOLD** — but the concern does | kit original; the kit is ahead on portability idiom (§9) |
| Upstream changed since 2026-08-22 | **DOES NOT HOLD** | 0 commits to `.claude/skills` |

## 11. Gate B recommendation

**Proceed with the full initiative.** Then one decision dominates everything else:

**D1 — ship the stacked-PR workflow document (2,711 words) through the scaffolding
channel.** This is the decision the falsifier verdict rests on, and it can flip it:

| If the doc… | Non-portable candidates | Falsifier |
|---|---|---|
| **ships** | 3 of 12 (**25%**) | does not hold — full initiative proceeds |
| **does not ship** — counting only the two skills that disclaim owning the mechanics | 5 of 12 (**42%**) | **HOLDS** — narrows to "refresh the 26 + sync mechanism" |
| **does not ship** — counting all five candidates that reference it | 8 of 12 (**67%**) | **HOLDS** |

Five of the 12 candidates reference the document, and they do not depend on it equally
— so this is a judgment call about where the line falls, not a single measured number:

- **Load-bearing.** `stacked-pr-planner` and `pr-comment-resolver` each state outright that they do not own the mechanics — *"This skill decides. It does not execute. Every command, cascade, force-push and verification lives in [the document]… Do not restate any of them here"* and *"Read it there; do not re-derive it"*, plus one instruction to run a named section of it **in full**. Without the document these are decision procedures pointing at nothing.
- **Degraded.** `parallel-session-safety` loses its command mapping, retained verification rules and manual fallback, but keeps its own 3,798 words of substance. `orchestrate` is the same shape — and it is a refresh, not a candidate.
- **Cosmetic.** `initiative-planner` cites it in a see-also list ("every branch mechanic this skill deliberately omits") and `pr-review-concise` in a parenthetical supporting a routing rule stated inline. Both read fine without it.

**The falsifier holds under every counting rule that treats a dangling delegation as
non-portable — 42% at the most generous, 67% at the strictest.** That is a stronger
result than a single percentage: there is no defensible way to decline the document
*and* keep the initiative at full scope. 2,711 words is the cheapest 31,867 words of
capability in this program.

**D2 — dependency handling, revised from OP-2.** Confirm *(c) substitute* — narrowed
by mechanism, and paired with (a):

- **(a) ship** the skill-owned scripts. They arrive with their skills, are stdlib-only, and this is already the kit's pattern. Rewrite the **14 same-skill** call sites to the skill-directory variable.
- **(c) substitute** for the **15 cross-skill** sites, where no portable idiom exists. Two subcommands (`lint`, `audit-skills`) cover 9 of the 14 in scope.
- **(a) ship** the stacked-PR document per D1, and the Class 1 conventions need nothing — the kit already publishes them in 8 files.
- **never (b) strip** — unchanged, and now better supported: stripping the delegations is what would make those six skills prose.
- Fix `audit_skills.py`'s hard-coded path depth before shipping (§6).

**D3 — OQ-5 needs no hooks story for this port.** Zero skills require a hook.
Genericize the two narrated incidents in `pr-review-concise` and `pr-comment-resolver`
instead. A hooks story may be worth having; it is not on I2's critical path, and
deciding it here would block the port on an unrelated question.

**D4 — OQ-2 / `usage-guard`: defer.** OP-5's "port with a documented limitation" was
decided against a 1,764-word estimate. It is 12,509 words, 72% PowerShell, writes the
user's settings file, and installs a scheduled task. Revisit as its own initiative.

**D5 — OQ-6: an explicit correspondence map.** Name-derivation is falsified (§2).
Store kit↔upstream name pairs, pin the upstream commit, report drift as commits-since
per skill.

**D6 — refresh order.** `parallel-session-safety` first (reference skill, 0 violations,
no blockers), then `consolidation-critic` before `learning-consolidator`'s Phase 8,
then rows 1–10 by gap. `extract_sessions.py` gets its own task (§8).

**Sequencing note.** The renames are landing right now on a shared tree. `orchestrate`,
`python-conventions`, `test-conventions` and `vertical-slice` are contended directories
today — four of the refresh set, including ranks 3, 5 and 7. Start the refresh on the
uncontended rows.

## 12. Corrections to the charter, for whoever plans W2.2

| Charter claim | Measured |
|---|---|
| Table A "Words" column | **SKILL.md only** — understates the candidate set 2.6x in aggregate (38,807 → 100,916), 7.1x for `usage-guard`, 9.3x for `feedback-audit` |
| "Rows 1–10 sum to +42,155" (twice) | Its own rows sum to **+39,959**; correct post-I1 top-ten is **+42,397** |
| "`analyge-logs` → `analyze-logs`" | **No such rename.** The kit never had the typo |
| spec-directory convention "Kit ships it? no" | The kit ships **20 references across 8 files**, 14 in `spec-driven-dev` |
| `scripts/ai_files_lint.py` etc. as repo infrastructure | **Skill-owned**, ships with its skill, stdlib-only |
| `audit_skills.py` 5 refs · `audit_cleanup_targets.py` 5 | **9** and **5** in SKILL.md files; 12 and 6 whole-tree |
| `extract_sessions.py` 4 refs | **5** in SKILL.md files, 23 whole-tree |
| 13 upstream-only = 12 candidates + 1 rename | **12** — the rename landed during this session |
| OQ-3 (rename here or in I4?) | **Answered by fact** — happening now, in I4's wave |
| cd-prefix hook as a dependency | **Not a dependency of any skill.** 4 refs, all prose anecdote |

## 13. What this triage did not do

- **No port.** Read-only apart from this file. The staged overwrites were built and tested in a scratch directory outside the repository.
- **Did not run the candidates' own test suites.** `ai_files_lint.py` and `extract_sessions.py` ship tests; whether they pass on macOS or Linux is unmeasured, and the charter's "must work on Windows, macOS and Linux" consequence stands unverified. This platform was the only one available.
- **Did not verify the skill-directory variable's resolution at runtime.** It is treated as sound because both the kit and upstream already rely on it; nothing here executed a skill to confirm it.
- **Did not design the drift check.** §11 D5 states the key; the format is W2.4's.
- **Prose generalization is unmeasured.** §8's third row is unbounded by construction: edits that changed wording without touching a forbidden pattern cannot be counted by pattern-matching. The 31-scrub figure is a **floor** on intentional divergence, not a total.
