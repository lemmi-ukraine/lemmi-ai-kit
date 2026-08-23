# W-window — self-challenge and completion review

**Dated:** 2026-08-23, at the close of the session that paid the extraction-window debt.
**Reviews:** [2026-08-23-w-window-paid.md](2026-08-23-w-window-paid.md).
**Method:** adversarial. Every published figure re-derived by a second method or against a
second population; every new detector mutation-tested. Five claims did not survive, and all
five are corrected in the record itself rather than only noted here.

---

## 1. The headline survived, but only after the test its own source document demanded

The measuring session's review closed with a warning aimed at exactly this kind of figure:

> when a measurement produces a pair of complementary figures, they are not equally strong. The
> one built from positive matches on short strings is the weak one.

**I published a carried count — the weak half — as the headline, and did not apply that test to
it.** Applying it now:

| Basis | Before | After |
|---|---:|---:|
| All non-blank window lines, as published | 63/589 (11%) | **493/589 (84%)** |
| Substantive only (>25 chars, not pure table/fence), **both sides filtered** | 45/540 (8%) | **444/540 (82%)** |
| Substantive numerator against the unfiltered denominator | — | 444/589 (75%) |

**The claim holds, two points lower.** Of the 493 carried, 444 are substantive, 42 are 25
characters or fewer, 17 are pure structure, 11 are duplicated within the set — a far cleaner
profile than the population that prompted the original warning, where 254 of 794 were short or
structural. That is the expected shape when content arrives by merge rather than by coincidence:
a three-way merge carries whole paragraphs, so its carried set is mostly prose.

**The 75% row is the trap.** It is what you get by filtering the numerator and not the
denominator, and it is the number I would have published had I done the check carelessly — a
*more* conservative-looking figure that is simply wrong, because the denominator also contains
short and structural lines. Being conservative in the wrong place is still being inaccurate.

**Carry forward: apply the previous review's stated warning to your own numbers before publishing
them, not after. And when you filter a ratio, filter both halves or neither.**

## 2. The correction that mattered most: three of the four new detectors had never failed

The whole point of W-2 is that a check which cannot fail is not a check. I mutation-tested
**one** of the four detectors I added — changelog types, the one with a known historical defect —
and shipped the other three untested. That is the same error one level in, again.

Mutating each in turn, removing a member from the kit-side constant:

| Detector | Result | Names the member |
|---|---|---|
| `test_upstream_changelog_types_are_all_carried` | RED | yes |
| `test_upstream_hypothesis_categories_are_all_carried` | RED | yes |
| `test_upstream_learnings_sections_are_all_carried` | RED | yes |
| `test_upstream_handoff_contract_is_all_carried` | RED | yes |
| `test_upstream_hypothesis_statuses_are_all_carried` (added during review, §4a) | RED | yes |

**5/5 fail on a dropped member and each names it.** The set is sound — but it was sound by luck
until it was tested, and the handoff one especially, because that is the detector I had already
had to rewrite once for being vacuous (its first version filtered upstream's candidate sections
through the kit's own constant, so it could never see an upstream addition). A detector I had
already got wrong once was the one I left untested.

**Carry forward: "I tested the detector" means every detector, and the one you already fixed once
is the one most likely to be broken twice.**

## 3. The claim I made from three samples and stated as though I had checked all of it

The record said of the 96 still-absent lines: *"Every one inspected. No accidental losses."* I had
read the list and spot-checked **three**. The conclusion was right; the warrant was not.

Classifying all 96 by best fuzzy match against the shipped skill, then reviewing the residue:

| Class | Lines |
|---|---:|
| Carried in reworded or re-wrapped form (match ≥ 0.60) | **52** |
| Deliberate strips matched to a named banned pattern or source-project marker | **30** |
| Continuation lines of blocks in that second group | **14** |
| **Accidental losses** | **0** |

The 14 exist because a marker matched a block's first line and not its tail — an artifact of the
classifier, not of the merge. Reviewing them by hand found one that inverts the question:
upstream's *"handles cleanup by changing statuses and optionally archiving resolved entries"* is
absent because **the kit says it better**, naming the archive file and the rotation step. An
absent line can mean the shipped version is more specific, and a pure line-membership test cannot
tell that from a loss.

**Carry forward: "I inspected them" and "I inspected three of them" are different claims. If a
classification is worth publishing, classify the whole population and report the residue.**

## 4. A finding I published that the tree fixed underneath me

The record's §10c reported that the restructure had moved the shipped skill scripts into ruff's
lint surface, so the repo's own formatter would rewrite pack content meant to ship as authored.
That was true when measured and I relayed it to two peer sessions. By 19:56 the restructure
session had added `extend-exclude` and a matching `basedpyright` `exclude` for both skills trees.
Re-verified: `ruff check --show-files` returns 19 files, **none under a skills tree**.

§10c is now marked RESOLVED rather than deleted, because the generalisation outlives the instance:
**a lint or type-check exclusion is written against a path, so every tree move silently changes
what is checked — in either direction.** The move first pulled 4 shipped scripts *into* the gate;
the fix could as easily have pushed real source *out* of it.

**Carry forward: a finding reported into a live tree needs re-checking before it is filed, or the
record ships a defect that no longer exists.**

## 4a. The owed item that was not owed

The hand-off's first draft deferred the fifth vocabulary detector, `HYPOTHESIS_STATUSES`, with
the reason *"upstream's counterpart is a live data file, not a template; there is no clean
parse."* That was written from memory of the shipped pin's docstring, and never checked against
upstream. Checking it took one command: upstream's `.ai/improvement-hypotheses.md` line 13
carries the identical `**Status lifecycle:** PENDING → CONFIRMED | REFUTED | INCONCLUSIVE |
SUPERSEDED` line that the shipped seed does. The detector was then written in minutes, reusing
the two hoisted patterns so both sides parse by the same rule, and mutation-tested: removing
`SUPERSEDED` turns it red and it names the member.

**Carry forward: a reason for deferring work is a claim about the world and needs the same check
as a finding. This one would have shipped a permanent gap in a guard family, justified by a
sentence nobody had tested** — and it is the same shape as the `checks.py` comment this whole
wave exists to correct: a plausible rationale written to explain an absence, which then
protects it.

## 5. What I challenged and found sound

| Claim | How re-checked | Result |
|---|---|---|
| Window-line denominators | against the measuring session's independent per-skill table | 170/110/58/53/23 **exact**; two off by one |
| Per-skill bases | distance at the candidate base vs global minimum over every touching revision, all 15 files | `at_base == global_min` everywhere, no contradictions |
| `ai-improvement-tracker`'s odd base | probed separately; it is not the default | `03a10499` confirmed, 2 vs global min 2 |
| W-3's premise | upstream commit timestamps vs the kit's first commit | type added **17h after** extraction — the "deliberate drop" note is circular |
| The 12th type is the only vocabulary gap | all five vocabularies parsed out of upstream at the pin | 12=12, 7=7, 7=7, sections and statuses all present |
| Contributor path stays green | full suite with the upstream env var unset | **190 passed, 5 skipped** |
| Merged content survived the restructure | SHA-256, pre-move copies vs post-move tree | **13/13 identical**, plus `checks.py` identical after its own later move |
| The audit is not passing vacuously | `--skills-dir` passed explicitly, both packs, post-move | core exit 0, python exit 0 |
| `drain_audit.py` was correctly skipped | kit vs upstream at the pin, by diff | kit strictly ahead; nothing to merge |
| `learning-consolidator` under the size cap | audit after moving three blocks to `references/` | 482 lines, `0 finding(s)`, exit 0 |

The base verification is the one that mattered most, because a wrong base is the defect this whole
initiative exists to correct and re-committing it while fixing it was the available irony.

## 6. The instrument, and the defect I described wrongly

Two measuring faults hit this session; one I diagnosed correctly and explained wrongly.

**Diagnosed right:** the working tree is CRLF and `git show` yields LF, so merging them directly
made every line differ by a trailing `\r` and `git merge-file` returned one whole-file conflict per
file — which reads as "these files are 100% divergent" rather than as an encoding artifact. All
seven files did it. Normalising all three operands to LF took `skill-creator/SKILL.md` from one
whole-file conflict to two real localised ones.

**Explained wrong, and a peer caught it.** I reported the shell construct `$'\r$'` as broken. It is
not: bare, it returns the correct answer. It fails only when nested inside a double-quoted `printf`
argument, where the pattern degrades to match-every-line. A peer ran the bare form, got the right
answer, and challenged the claim rather than accepting it. Both halves matter — my *conclusion*
about line endings was independently confirmed, and my *mechanism* for it was wrong, which is the
combination most likely to be believed.

**The structural tell, which is the transferable part:** the count exactly equalled `wc -l` on all
three files. A count equal to the line count is a match-everything pattern, not a measurement. On
the one all-CRLF file the broken form and the true answer agreed, and that coincidence is what sold
it to me.

## 7. Scope discipline — what I declined

- **`docs/upstream-sync.toml` untouched**, though moving `[extraction_window] status` off
  `"unreviewed"` is genuinely owed. It sits in another session's declared path set and was already
  dirty there; handed over with the exact value instead of edited into a conflict.
- **`tests/test_publication_hygiene.py` untouched.** My record tripped the repo-wide contract by
  quoting two banned literals. The precedented fix is an allowlist entry, but that file was dirty
  under another session — so I rephrased my own document instead, which is also what the contract
  prefers ("remove the reference") over growing an exemption list.
- **`task-learnings` untouched.** It is the row that contradicts the mechanism (66% carriage where
  exposed peers were near zero, with the measuring session's explanation tested and refuted). It is
  outside the funded six and remains unexplained. I did not fold it in to make the story tidier.
- **The seven remaining exposed skills untouched** — 91 lines, ~13 each, ruled not worth a session.
- **`subagent-preamble.md` not ported.** ~12 of its 25 lines are portable and it now has a live
  caller, but the measuring session put it out of scope and porting it is a new file, not a merge.
  Named and sized rather than smuggled in.
- **No taxonomy edited to turn a red test green.** The three pins that broke on the path move were
  repointed at `manifest.shipped_skill_dirs()`; the vocabularies were not touched.

## 8. Limits that remain

- **82% is carriage, not quality.** It says upstream's substantive window lines are present. No
  human has read the merged `skill-creator/SKILL.md` end to end; it grew 66 lines.
- **The classification in §3 leans on a 0.60 fuzzy threshold.** The 52 "reworded" are not
  individually verified as semantically equivalent — three were, in the record's §5.
- **Nothing guards the carriage numbers.** They live in a document. W-2's four tests guard the
  vocabularies against upstream, which is a narrower claim, and the only part of this that a future
  run re-derives.
- **`ai-changelog` at 29% substantive is the weakest row** and is expected to be: its window
  content is disproportionately the unshipped linter's invocation and dated project history. The
  taxonomy member that motivated W-3 is carried.
- **Measured against one upstream revision.** Every figure is relative to the pin `a78ee5af` as it
  stood on 2026-08-23. A base is a claim with an expiry, and so is this.
- **The tree moved four times during the work.** Skills tree moved, then the package moved. Every
  figure here is timestamped; none should be re-read as a statement about a later tree.

## 9. Did the task meet what was asked?

| Ask | Verdict |
|---|---|
| W-1: six skills, re-merge against the per-skill base, not hand-restore | **Met.** All six plus `ai-changelog`; 13 files; bases verified per file |
| W-2: close the pin blind spot by adding the upstream read | **Met, and mutation-proven 5/5** across the whole pin family. Skips cleanly for contributors |
| W-3: restore `EXPERIMENT-REGISTERED` inside W-window | **Met.** Doc, constant, and the pairing rule in `ai-improvement-tracker`; the false "deliberate drop" note corrected in place |
| Re-probe the five untrusted bases before use | **N/A, established rather than assumed.** None of the funded seven is among them; all were verified anyway |
| Run before the restructure | **Met, narrowly.** All merges landed before the tree moved; survival verified by hash, not by inspection |
| Do not assume away the unmeasured split | **Met.** All 96 residual lines classified; zero accidental losses |
| Do not assume away `task-learnings` | **Met by declining it** and saying so |
| Four-check gate every step | **Met.** Green at close both with and without an upstream checkout |

**Net:** the deliverable stands and is stronger than when first published. But four of the five
things that did not survive review were the same mistake — **publishing a claim whose warrant was
narrower than its wording**: a carried count presented as robust without the test its own source
demanded, one detector tested and four claimed, three lines inspected and 96 asserted, and a
work item deferred on a reason never checked. The
underlying work was right each time, which is precisely what makes the habit dangerous: it never
produced a wrong answer, so nothing forced it into view.
