# I2 (c)-substitute — self-challenge and completion review

**Dated:** 2026-08-23, at the end of the session that added `lint` and `audit-skills`.
**Reviews:** [2026-08-23-i2-cli-substitution-handoff.md](2026-08-23-i2-cli-substitution-handoff.md)
and the code it hands over — `src/lemmi_ai_kit/checks.py`, `tests/test_checks.py`,
`src/lemmi_ai_kit/cli.py`.
**Method:** adversarial, against the implementation rather than the report. Fourteen probes
of behaviour I had *not* tested, run against the built code. The point was to find what is
wrong with the work, not to certify it. **Every finding below is already fixed and has a
test; the handoff's affected figures are corrected.**

---

## 1. The structural failure: I tested my intentions, not the file format

The 98 original tests passed on the first run. I distrusted that and mutation-tested five
design choices, all of which held — so I shipped, and the handoff said so.

**That was the wrong check.** Mutation testing asks *"does my test notice if I break my
implementation?"*. It cannot ask *"did I implement the right thing?"*. Every one of my
tests was built from a fixture **I** wrote, and I write conforming entries — so the suite
proved the lint accepted my idea of a good file and rejected my idea of a bad one. It never
asked what a *real* `.ai/` file contains.

What real files contain is **documentation of their own format.** The `ai-changelog` skill's
own calibration examples are fenced entry blocks. Its guidance on `CONSOLIDATION` entries
tells authors to nest sub-items. `task-learnings` ships a `references/learnings-format.md`
whose whole content is fenced examples of entries. An author following the skills as written
produces exactly the shape my parser mishandled.

**Three false-positive classes, one root cause: the parser was not fence-aware.** And the
tell was in my own code — `_link_findings` in the skill audit toggles on ``` because
upstream taught it to, and I ported that fence-awareness into the audit while leaving it out
of the data-file parser, which is where format documentation actually lives. I had the
concept in the file and applied it to the wrong half.

**Carry forward:** for a checker, fixtures written by the author are the weakest possible
corpus. Run it against the real artifacts in the repository *and against the format examples
the docs ship* before believing a green suite. The seed-file test I did write
(`test_the_shipped_seed_files_lint_clean`) was the right instinct aimed at the wrong files —
the seeds are empty headers, so it could never have caught this.

## 2. The findings

Ranked by consequence. Rows 1–4 are defects in shipped behaviour; 5–8 are quality.

| # | Finding | Class | Consequence |
|---|---|---|---|
| **1** | A fenced `## YYYY-MM-DD` inside an entry body was parsed as a real date heading | **false positive** | Split the entry: every field below the fence was attributed to a new empty block, so a conforming entry reported 3 missing required fields — and a fenced date out of order also faked a reverse-chronological violation |
| **2** | A fenced `### TYPE: title` was parsed as a real entry | **false positive** | Same split, 4 false findings, plus a phantom entry in the count |
| **3** | Fenced field bullets read as a second copy of the field block | **false positive** | 4 false "duplicate field block — double append" findings on an entry that documents the format |
| **4** | Entries above the first `## ` heading were silently dropped | **false negative** | `parse_blocks` files entries under headings, so an entry preceding the first heading belonged to no block and was invisible to every required-field, taxonomy and date check. **A file with a broken orphan entry linted clean.** |
| 5 | `target_path` mapped any unknown target to the hand-off directory; `lint_file` fell through to the hypotheses lint | latent | Argparse `choices` guards the CLI today, so unreachable — but a target added to `LINT_TARGETS` without a path entry would silently lint the wrong file |
| 6 | `worst_severity` was dead public API, with a test certifying it | dead code | `_fails_threshold` in `cli.py` reimplemented the same severity comparison inline. The test made the function look used |
| 7 | `_flag`'s second clause was unreachable, and its sibling flag read did not use it | dead code | Only call site passed `default="false"`, making the clause constant-false; `user_blocked` used `_text_field` directly, so two ways to read one kind of field |
| 8 | `_handoff_sections` was not fence-aware either | latent false positive | A fenced `## Status` example in a hand-off would have become a phantom — and, given a real `## Status`, a **duplicate section** finding |

**Findings 1–4 are the ones worth reading.** 1–3 are the same defect wearing three faces,
and 4 is its mirror image: the fence bug reported conforming files as broken, the orphan bug
reported broken files as clean. Both are failures of the same missing question — *what does
this file actually look like when a human follows the skill that writes it?*

### Why finding 4 is worse than its rank suggests

I built a test specifically about silent under-reporting — `test_a_bom_does_not_silently_
swallow_the_whole_file` — after a first version of it passed under mutation. I understood
the failure mode well enough to write a test for it, correctly identified that an unparsed
heading orphans every entry beneath it, and then **fixed only the BOM route to that state**.
The same state reached by a bad append, or by a heading deleted out from over its entries,
stayed invisible. I fixed one cause of a class instead of checking the class.

## 3. What held

Stated because a review that only lists failures is not a measurement:

- **All five original mutations still hold**, and the two new fixes are mutation-verified
  the same way (reverting fence-awareness fails 3 tests; removing the orphan check fails 2).
- **Ten further probes found nothing.** CRLF hand-offs produce byte-identical findings and
  line numbers to LF. HTML-comment blanking keeps reported line numbers true (verified
  against the real line index, not assumed). `.ai/handoffs` existing as a *file* rather than
  a directory degrades to a no-op. A loose `README.md` inside a skills directory is ignored
  rather than audited as a skill. `display_path` on a path outside the root falls back to
  the bare filename, so no absolute path can leak. Indented fenced content was already safe.
- **The vocabulary pinning held** against all four shipped skills at session close — and it
  is the one part of this work that was verified against real artifacts from the start,
  which is exactly why it found nothing wrong.
- **No asset was touched.** Verified at close: the only files I created or modified are
  `checks.py`, `test_checks.py`, `cli.py`, and these documents.

## 4. Corrections applied to the handoff

| Section | Was | Now |
|---|---|---|
| §1 | `checks.py` 1,342 lines; tests 1,226 / 93 functions / 98 cases | **1,440**; **1,333 / 104 / 109** |
| §4 | "Five portability fixes upstream never needed" | **Six**, with fenced-content handling added as item 0 and pointed at this review |
| §6 | 4 MAJOR / 6 findings in the shipped pack | **3 MAJOR / 5**, with a note that the number moved under Session D mid-session and must be re-run rather than quoted |

## 5. Two things I did not fix, deliberately

**`--since` plus an undated entry skips every per-entry check, including "the title is
malformed".** With a cutoff set, a learnings entry whose title carries no parseable date
falls out of policy entirely — so the one finding that would tell the author *why* it has no
date is suppressed. Upstream behaves the same way. Leaving it: with a cutoff there is
genuinely no way to tell which side an undated entry falls on, and guessing "in policy"
would fail entries an adopter deliberately excluded. It is documented in `_in_policy`'s
docstring and now here. **The kit's default is no cutoff, so this affects nobody until an
adopter opts in.**

**Hand-offs are linted without an opt-in marker.** Covered in the handoff §4; restated
because it is the other place I knowingly diverged. Upstream gates on a `handoff-contract:`
marker; the kit's `parallel-session-safety` documents no marker, so requiring one would ship
a lint that silently passes everything. If Session D ports the marker language, add the gate.

## 6. The honest limits

- **macOS and Linux remain unrun.** Unchanged by this review. The fence, BOM, CRLF and
  case-sensitivity behaviour is unit-tested and meaningful on this platform, but "green on
  Linux" is unmeasured. CI settles it on the next PR.
- **The corpus is still narrow.** I now test against the shipped seed files and against the
  format shapes the skills document. I have **not** run the lint against a mature `.ai/`
  tree with months of real entries, because no such tree exists in this repository. That is
  where the next class of false positives will be found, and the first adopter to run
  `lint` on a populated pipeline is the real test.
- **One asset-tree test is red at close, and it is not mine.**
  `test_assets_have_no_contamination` fails on
  `skills/branch-switch/SKILL.md:46`, on the pattern the contract labels *source-project
  backup reference*, re-imported by Session D's refresh of that skill. Worth recording as evidence rather than noise: **the hygiene
  contract caught an upstream refresh re-importing a banned pattern, live, which is exactly
  the mechanism the initiative is building.** Everything else passes (147 of 148).
