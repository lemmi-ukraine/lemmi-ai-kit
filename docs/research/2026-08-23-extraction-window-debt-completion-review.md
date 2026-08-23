# W-window measurement — self-challenge and completion review

**Dated:** 2026-08-23, at the end of the session that measured the extraction-window debt.
**Reviews:** [2026-08-23-extraction-window-debt-measured.md](2026-08-23-extraction-window-debt-measured.md).
**Method:** adversarial. Every published figure re-derived by a second method or against a
second population. Three claims did not survive; all three are corrected in the document
rather than noted here only.

---

## 1. The correction that changes what the number means: half my denominator was never at risk

I published **"623 absent of 1,417 — 44%"** and treated it as the loss rate. It is not.

Two of the 15 window skills never ran the defective merge:

| Skill | How it reached the pin | Window lines | Carried |
|---|---|---:|---:|
| `session-retrospective` | three-way merge against the **true** base | 598 | 587 (98%) |
| `hypothesis-validator` | **fresh port** from current upstream, first in the kit 2026-08-23 | 115 | 102 (89%) |

Between them that is **713 of 1,417 lines — half the population — with a 3% loss rate**, averaged in
with skills that lost nearly everything. Removing them:

| | Skills | Window lines | Absent | Loss |
|---|---:|---:|---:|---:|
| Exposed | **13** | **704** | **599** | **85%** |
| As published | 15 | 1,417 | 623 | 44% |

**The finding is worse and narrower than I reported it.** Narrower because two skills need nothing;
worse because among skills that were actually exposed, 85% of the window content is gone, not 44%.

**How I caught it:** `hypothesis-validator` carried 102 of 115 lines, which contradicted the causal
story I had just written. Instead of recording it as noise I asked why, and `git log --diff-filter=A`
put its first appearance at 2026-08-23 — one of W2.3's nine fresh ports, never merged against any
base. The outlier was not noise; it was the control group.

**Carry forward: an outlier that contradicts your mechanism is either a refutation or a second
population. Find out which before averaging it in.** A single number over a mixed population hid
both facts at once — that some skills were fine and that the rest were far worse.

**A trap I nearly fell into on the same check.** `python-conventions` and `test-conventions` also
report a 2026-08-22 first appearance, which looks identical to a fresh port. They are **renames** of
extraction-era skills, verified back to the `002dadd` initial release. Had I classified them the same
way I would have moved 68 genuinely-lost lines into the "never at risk" bucket and understated the
debt again. `--diff-filter=A` on a path answers "when did this path appear", not "when did this skill
appear".

## 2. The finding that outgrew the task: the vocabulary pins cannot see this loss

Chasing the one row that contradicted my mechanism (§8) led somewhere more important than the row.

`task-learnings` carried 66% of its window content where its exposed peers carried near zero, and
its category table is guarded by `test_learnings_sections_and_slugs_match_the_shipped_skill`. The
obvious explanation — *a test forced the content to stay* — is **wrong**, and testing it exposed a
gap in the guard set:

**Every vocabulary pin asserts `shipped doc == kit constant`. None consults upstream.**

So a refresh that drops a taxonomy member from *both* the shipped document and `checks.py` leaves
every pin green. Not hypothetically — measured:

| | Count |
|---|---:|
| Change types in upstream's table at the pin `a78ee5af` | **12** |
| Rows in the shipped `ai-changelog` table | **11** |
| Members of the kit's `checks.CHANGELOG_TYPES` | **11** |
| Occurrences of `EXPERIMENT-REGISTERED` anywhere in `src/lemmi_ai_kit/` | **0** |
| Test suite status | **184 passed, 1 skipped — green** |

The pack silently offers an 11-member closed set where upstream defines 12. The member is gone from
all three places at once — the shipped table, the constant, and `ai-improvement-tracker`, which
carried its pairing rule (an `EXPERIMENT-REGISTERED` entry *always* requires a dated, falsifiable
hypothesis with a re-eval date). Zero hits across the whole package.

`test_changelog_types_match_the_shipped_skill` is the test whose job this is, and it passes, because
both of its operands lost the member together. It is one of **five** pins in the family
(`changelog_types`, `learnings_sections_and_slugs`, `hypothesis_categories`, `hypothesis_statuses`,
`handoff_contract_sections`) and all five share the design.

**This is the `MAP ERROR` lesson from W2.4 one level in: a check that cannot fail is not a check.**
Those pins are real and worth keeping — they catch doc-vs-code drift, which is what they were built
for. But they were being treated in the handoffs as *the* drift alarm for taxonomies, and they cannot
raise this class of alarm at all.

**Direct consequence for W-gate.** Promoting the drift check while this hole is open promotes a suite
that is green on a measured content loss. The drift check counts commits, the pins compare kit to
itself, and nothing in the repo compares a taxonomy to upstream. That is the gap to close before
either gate is promoted — and it is cheap to close, because the pin tests already parse both sides.

**Carry forward: a pin whose two operands both come from your own tree measures consistency, not
fidelity. Ask what an adversary would have to change to keep it green.**

## 3. The claim I stated backwards

The measurement document's §6 listed as a limitation that a line relocated to another file inside
the same skill "still counts as carried." That is the opposite of what the code did: matching was
`upstream <skill>/X` against `kit <skill>/X`, so a relocated line would have counted **absent** and
inflated the debt.

Re-run against every file in each skill directory: **623 absent either way, 0 lines relocated.** The
limitation was described wrongly and the number it described was right — which is the more dangerous
combination, because a reviewer checking the prose against the result finds them consistent.

**Carry forward: state a limitation as the direction it biases the result, then test that direction.**
"Presence is per-file" is a description. "Per-file matching inflates the absent count, and re-running
directory-wide moves it by zero" is a check.

## 4. The soft figure I published next to a hard one

The absent count survived every challenge. The **carried** count did not, and I gave them equal
weight.

Of the 794 lines counted carried: **540 substantive**, 232 at 25 characters or fewer, 22 pure
structure, 122 duplicated within the set. The short matches include `{`, `?`, `]`, `s`, `try:`,
`sys,` — lines that appear somewhere in almost any file of the same type. Treating every one as a
false carry puts absent as high as **877 of 1,417 (62%)**.

This does not change the direction of anything: every weakness in the carried figure makes the debt
**larger**. But publishing "56% carried" as though it were as solid as "44% absent" overstated what
I knew, and §5a now says which of the two is load-bearing.

**Carry forward: when a measurement produces a pair of complementary figures, they are not equally
strong. The one built from positive matches on short strings is the weak one.**

## 5. What I challenged and found sound

| Claim | How re-checked | Result |
|---|---|---|
| Total window insertions | `git diff --numstat`, independent of my difflib path | **2,668** — matches W2.4 exactly |
| The 1,024 unshipped-script lines | numstat per file: 453 + 229 + 342 | **1,024** — matches W2.4 exactly |
| The 2,668 vs 2,318 gap | blank-line hypothesis, tested | 350 blank lines; W2.4 counted insertions incl. blanks, I counted content |
| W2.4's one spot-check | re-derived independently | `skill-researcher/SKILL.md` **19 added, 19 absent** — reproduced |
| Absent is not a punctuation artifact | normalised em/en-dashes, curly quotes, ellipses, NBSP | recovered **exactly 0** of 623 — my own hypothesis refuted |
| Absent is not a matching-rule artifact | four rules, tightest to loosest | 623 / 623 / 615 / 580 — the result is not rule-driven |
| Absent is not a relocation artifact | re-matched directory-wide | 623, **0 relocated** |
| The control holds the target constant | read the record through W2.4's loader | all 36 tracked rows sync to pin `a78ee5af`; **one** `base` override exists |
| The outlier is a second population | `git log --diff-filter=A` in the kit | `hypothesis-validator` first appears 2026-08-23, in W2.3's nine ports |
| The two renamed skills are not ports | traced both to the initial release | `002dadd`, 2026-07-02 — exposed, correctly counted |
| Per-skill ranking is robust | re-ranked under the strictest rule | same order; top three 335, top six 469 |

The ranking surviving the strictest challenge is what matters most, because the ranking — not the
total — is what a scoping decision uses.

## 6. The instrument, and why I did not reuse W2.4's

W2.4's `_git` helper uses `subprocess(text=True)`. For its own work — commit counts and ASCII
paths — that is fine. For content comparison it is the exact defect that turned 14 rewritten lines
into 176 phantom dropped ones in the `session-retrospective` review, because Windows decodes UTF-8
through the locale codec and every em-dash becomes a difference.

So I read the record through W2.4's loader (safe: `tomllib` decodes UTF-8 itself) and wrote my own
byte-level git call for content, decoding explicitly. Added lines come from `difflib` opcodes rather
than parsed diff text; paths arrive `-z`.

One residue worth naming: the em-dashes rendered as `?` in my terminal output. That is stdout's code
page, downstream of the comparison, and it is cosmetic here — but it is the same class of artifact,
and had I been eyeballing samples to decide presence rather than comparing in Python, it would have
mattered.

**A control that could have failed, and one that did.** W2.4's 19/19 spot-check reproduced, so the
instrument has discriminating power on a known answer. My punctuation hypothesis was a real
prediction with a real mechanism — the pack has an ASCII-only rule, upstream uses em-dashes — and it
recovered zero. Both mattered: the first proves the tool measures, the second proves the result is
not an artifact of how it measures.

## 7. Scope discipline — what I declined to do

- **Did not touch `assets/skills/`.** The measurement is read-only by construction, which is what
  lets it run beside I4.
- **Did not edit `docs/upstream-sync.toml`** to move `[extraction_window] status` off `"unreviewed"`,
  and did not add a row to `docs/research/README.md`. Both belong to the uncommitted W2.4 work, and
  the operator has left it uncommitted deliberately. Named as owed instead.
- **Did not classify all 580 absent lines** as portable or correctly-stripped. Mechanical markers
  explain 39; the rest needs a human read. §4 of the document characterises from samples and says so.
- **Did not restore anything.** Scoping the debt and paying it are different decisions, and the
  second is not measured by this.
- **Did not re-read the 38 skills.** Only the 16 window directories, and only their window lines.

## 8. Limits that remain

- **The portable / correctly-stripped split is unmeasured.** 560 exposed-absent lines is an upper
  bound on recoverable content, not a work estimate. `learning-consolidator`'s reference files are
  heavily `backend/app/` path-bound and will shed far more than the 15 lines markers caught;
  `skill-creator` and `python-conventions` will shed close to nothing. Nobody has read them.
- **`task-learnings` is unexplained.** It is exposed, yet carried 37 of 56 window lines — 66%, where
  its exposed peers are near zero. Either the refresh resolved it differently or the content arrived
  by another route. I did not chase it, and it is the one row that weakens the mechanism.
- **It measures the working tree**, which holds two uncommitted sessions. `session-retrospective`
  reads as reconciled here while `upstream-sync.toml` records it behind — deliberate, per that
  record.
- **Line-level, not semantic.** A rewritten-but-equivalent paragraph counts absent at every
  threshold below the fuzzy one, and the fuzzy pass only recovered 35 lines.
- **No test guards any of this.** The numbers live in a document; nothing re-derives them on a run.
  W2.4's report re-derives the affected *list* but not the exposure or the loss.

## 9. Did the task meet what was asked?

The ask was to measure W-window read-only, beside I4, so the debt could be scoped instead of
estimated.

| | Verdict |
|---|---|
| Read-only, no collision with `assets/skills/` | **Met.** One file added; `git status` otherwise unchanged |
| Converts the debt from unbounded to scoped | **Met.** 13 exposed skills, 560–599 lines, ranked, with three skills holding 60% |
| Reconciles with the measurement it extends | **Met.** 2,668 and 1,024 both reproduce exactly |
| Survives challenge | **Partly.** The absent count and the ranking survived; the loss *rate*, the carried figure and one limitation statement did not, and are corrected |

**Net:** the deliverable stands and is more useful than when I first published it — but the version I
first published understated the severity by half and misattributed the cause for one of 15 skills.
Both errors came from the same habit: computing one number over a population I had not checked was
homogeneous. The document now separates the population before it reports a rate.
