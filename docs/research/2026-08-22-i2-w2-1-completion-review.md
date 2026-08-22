# I2 W2.1 — self-challenge and completion review

**Dated:** 2026-08-22, at the end of the session that executed I2 W2.1 (portability triage).
**Reviews:** [2026-08-22-i2-portability-triage.md](2026-08-22-i2-portability-triage.md)
**Method:** adversarial. Every derived figure re-derived from the trees, not re-read from
my own output. The point is to find what is wrong with the work, not to certify it.
Findings are stated against my own report, and the corrections are already applied to it.

---

## 1. The structural failure: measured values were scripted, derived values were typed

**Four numeric errors reached the report. Every one is a figure I computed in my head
from correct measurements, and none is a measurement.** The upstream/kit scans all held
on re-derivation — whole-directory word counts, the 27-skill gap ranking, the 29
hard-coded call sites, the 100,916-word candidate total, the 2,711-word document, the
31,867-word dependent set. What broke was the arithmetic *on top* of them: sums,
percentages, and cross-section consistency.

That is the same defect the program document diagnoses in F3 and prescribes the fix
for: *"The durable fix is to stop hand-writing the number."* I hand-wrote my own
derived counts while writing a report whose §12 criticises the charter for exactly
that. The verification script I ran during the work re-derived the inputs and never
re-derived the outputs.

**Carry forward:** any report whose conclusions turn on sums or percentages should emit
them from the same script that measured the inputs. For this session that would have
cost one extra function and caught all four.

## 2. The four corrections

| # | Section | Claimed | Actual | Consequence |
|---|---|---|---|---|
| 1 | §1 table + prose ×2, §12 | charter Table A sums to **~39,900**; understatement **2.5x** | **38,807**; **2.6x** | cosmetic — the finding (Table A used the forbidden metric) is unaffected |
| 2 | §4 | 12 candidate violations across **5 skills** | **6 skills** | cosmetic — contradicted my own §7 table, which listed six |
| 3 | §8 | kit removed **20** hard-coded paths, **7** in `learning-consolidator` | **19** invocations, **6** in `learning-consolidator` | cosmetic. 20 counts a bare `scripts/` directory mention alongside 19 real invocations; the report now states both |
| 4 | **§11 D1** | doc not shipped → **7 of 12 (58%)** | **5 of 12 (42%) to 8 of 12 (67%)** | **substantive — see §3** |

Findings 1–3 are slips. Finding 4 is a reasoning error and it is the one worth reading.

## 3. The one that mattered: a judgment call presented as a measurement

§11 D1 is the report's dominant recommendation — ship the 2,711-word stacked-PR
document — and its force came from a single number: *without it, 58% of candidates are
non-portable, so the charter's 40% falsifier fires.*

**58% was not measured. It was derived from a mis-assignment I never checked.** Five of
the twelve candidates reference the document. I asserted that four were load-bearing
and one was a fallback, giving 3 + 4 = 7 of 12. When I finally read all thirteen
references in context — at review time, not during the work — the split was different:

| Grade | Skills | Evidence |
|---|---|---|
| Load-bearing | `stacked-pr-planner`, `pr-comment-resolver` | both disclaim owning the mechanics outright: *"Do not restate any of them here"*, *"Read it there; do not re-derive it"*, and one *"run § X in full"* |
| Degraded | `parallel-session-safety`, `orchestrate` (a refresh, not a candidate) | lose command mapping and manual fallback; retain their own substance |
| Cosmetic | `initiative-planner`, `pr-review-concise` | a see-also entry and a parenthetical supporting an inline rule |

So the honest answer is a range, not a point: **42% counting only the two load-bearing
skills, 67% counting all five that reference the document.**

**The conclusion survives and gets stronger.** The falsifier threshold is 40%, and the
*most generous* counting rule still clears it. There is no defensible way to decline the
document and keep the initiative at full scope — which is a more robust claim than the
single 58% I originally offered. But I reached the right recommendation through a number
I had not verified, and that is luck, not method.

**Carry forward:** when a percentage depends on classifying evidence, read the evidence
before publishing the percentage, and publish the range with the classification rule
attached.

## 4. What I checked at review time and found sound

Re-derived from the trees, independent of the report's own text:

```
candidate whole-dir total .......... 100,916   OK
27 refresh skills, top-10 gap ...... +42,397   OK
27 refresh skills, all positive .... +48,249   OK
stacked-PR doc ..................... 2,711 words, 13 refs, 6 skills   OK
those 6 skills ..................... 31,867 words   OK
hard-coded call sites .............. 14 same-skill + 15 cross-skill = 29   OK
hygiene, post-I1 refresh ........... 31 violations / 9 of 27 skills   OK
hygiene, 12 candidates ............. 12 violations / 6 skills   (report corrected)
```

The three provenance findings also re-checked clean: upstream has never contained
`scout-review`, the kit has never had the `analyge-logs` typo, and upstream made zero
commits to its skills tree since 2026-08-22.

## 5. A gate I ran but should not have trusted alone

I verified my report against `test_publication_hygiene.py` by importing its patterns and
scanning the file — 0 violations — and separately ran the full suite, 37 passed. Both
are real, but the first is the weaker check it looks like: it confirms the file does not
*contain* a banned pattern. It says nothing about whether the file's **markdown links
resolve**, and the i3a review already recorded that this repo has no link checker and
shipped two dead links through fifteen commits because of it.

My report contains one internal link (to itself, in the review header) and cites two
private planning paths using the established *"not committed to this repository"*
wording. That is the convention the F6 fix introduced, so it is consistent — but I
verified it by pattern, not by resolution, and the repo still cannot check the
difference.

## 6. Scope discipline — what I declined to do

- **I did not widen the hygiene contract** to cover `.ps1`/`.sh`/`.ts`, despite §7 identifying that gap. It is a W2.4 item and editing `tests/test_assets.py` mid-triage would have modified a contended file for a finding that is currently unexercised.
- **I did not fix `audit_skills.py`'s hard-coded path depth.** It is upstream's file; the triage records the defect and the fix pattern for whoever ports it.
- **I did not correct the charter or program documents.** §12 lists ten claims to correct; they are private planning artifacts owned by the operator, and the brief said touch no existing file.

## 7. Limits that remain, and are not resolvable from this session

Restating §13 of the report because a handoff reader needs them in one place:

- **Cross-platform is unverified.** `ai_files_lint.py` and `extract_sessions.py` ship tests; whether they pass on macOS or Linux is unmeasured. This platform was the only one available, and the charter's "must work on Windows, macOS and Linux" consequence stands open.
- **The skill-directory variable's runtime resolution is assumed, not proven.** The whole (a)/(c) split in §6 rests on it resolving to the calling skill's directory. Both the kit and upstream already rely on it, so this is a reasonable assumption — but nothing in this session executed a skill to confirm it, and if it is wrong the same-skill/cross-skill line moves.
- **Prose generalization is unmeasurable by pattern.** §8's 31-scrub figure is a floor on intentional divergence, not a total. Edits that reworded without touching a forbidden pattern cannot be counted this way, and `extract_sessions.py`'s +598/−21 shows the volume involved.

## 8. Did W2.1 meet its Definition of Done?

The brief's four criteria, assessed rather than asserted:

| # | Criterion | Verdict |
|---|---|---|
| 1 | One report at `docs/research/` | **pass** — one file; this review and the handoff are the two artifacts requested afterwards |
| 2 | Per-skill port verdict | **pass** — §7 for all 12 candidates with verdict and blockers; §3 for all 27 refresh skills |
| 3 | Gate B recommendation with real numbers | **pass, after correction** — D1–D6. It would have been *fail* on the numbers as first published: the dominant recommendation carried an unverified percentage |
| 4 | No other file in the tree modified | **pass** — verified by `git status`; the other entries are two sibling sessions' work |

The charter's W2.1 asks — dependency count by class, hygiene count from the real test
run against a raw upstream copy, and the intentional-divergence check (OQ-4) — are all
answered, and the wave's stated purpose ("this wave can kill the initiative") was
exercised honestly: the kill-switch was tested and did not fire, but §11 D1 identifies
the one decision that would make it fire.

**Net:** the triage's findings hold. Its arithmetic did not, until this review.
