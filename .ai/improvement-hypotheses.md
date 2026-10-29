# AI Infrastructure Improvement Hypotheses

> Testable predictions about expected value from AI infrastructure changes.
> Each hypothesis is linked to a changelog entry and will be validated by a future
> periodic review skill.
>
> **How entries are added:** Automatically by AI workflows after writing a changelog entry,
> via the `ai-improvement-tracker` skill.
>
> **Format:** Each entry follows the structured format defined in
> the `ai-improvement-tracker` skill.
>
> **Status lifecycle:** PENDING → CONFIRMED | REFUTED | INCONCLUSIVE | SUPERSEDED
> (status changes are made by the future validation skill, not this file's authors)

---

## 2026-10-29

### [INFRA-MODIFIED] Read a checker's one-number output, run a checker script without a shell, and find a citation's file from a scratch export
- **Category:** Quality
- **Hypothesis:** By reading a bare-integer checker output as its count and offering a shell-free `--script` mode, we expect sessions to certify a sound checker as CAN-SEE on the first run, because the two causes of a false UNUSABLE verdict (a lone "0" counted as a line, a pattern mangled by the platform shell) no longer arise.
- **Signal:** Inspect the next two sessions that quote a `probe_checker` verdict, or look by 2026-11-29, whichever comes first, counting verdicts that read UNUSABLE for a checker later shown sound and invocation errors that needed a second attempt. Confirm if both counts are zero; refute if either recurs with the new default.
- **Risk:** A checker that deliberately prints one line holding only a number is now read as that number, so an exact-count expectation can shift; `--count-mode lines` restores the old reading.
- **Status:** PENDING
- **Changelog ref:** 2026-10-29 — Read a checker's one-number output, run a checker script without a shell, and find a citation's file from a scratch export

## 2026-10-28

### [SKILL-MODIFIED] Keep every operator turn in the session digests, cite the lines Grep shows and count each event once
- **Category:** Observability
- **Hypothesis:** By keeping the operator turns the 120 KB cap cut off, reading mid-turn messages and question answers as operator turns, and numbering the sweep's citations by LF alone, we expect the next retrospective to find the operator's closing words in every capped digest and to cite lines that Grep and Read confirm, because one structural predicate now decides what an operator turn is for every digest and the sweep no longer reads through universal newlines.
- **Signal:** In the next retrospective run over at least 10 sessions after the installed Core plugin carries this change, or by 2026-12-09, whichever comes first, check with Grep and Read on the raw transcripts and the digests, not with the extractor. For each digest that carries the line `[...transcript truncated at 120 KB...]`, find the last human-origin record of its transcript (`origin.kind` human, typed or mid-turn) and confirm its words are in the digest; for 30 citations of `user_corrections_sweep.txt` (all if fewer), Read the cited line and confirm it is the `USER:` line that starts the quoted text. Confirm if every check agrees; refute if one capped digest lacks its last operator turn or one citation names another line. Fewer than 3 capped digests or fewer than 10 citations leaves it inconclusive. The same checks fail on the previous scripts: over 206 real sessions 84 of 136 citations named another line, and 29 of 31 capped digests had operator turns after the cut that the digest did not hold.
- **Risk:** The operator section sits outside the 120 KB cap, so the longest digests grow (over those 206 sessions the largest went from 125,638 to 129,356 bytes, the largest section being 6,290 bytes) and a deep read costs a little more context. The structural rule decides only for records that carry an origin stamp: 1,104 of the 2,692 user records without a tool result in that sample carry none, and for those the prefix list still decides. Nothing resolves this unless a session runs a retrospective and does the checks by hand.
- **Status:** PENDING
- **Changelog ref:** 2026-10-28 — Keep every operator turn in the session digests, cite the lines Grep shows and count each event once

## 2026-10-27

### [INFRA-MODIFIED] Collect the skill tests in CI, rebuild the learnings guard's shell arm and fix the extractor's rejection count
- **Category:** Quality
- **Hypothesis:** By judging a shell command the way a shell reads it, we expect the learnings drain guard to deny far fewer reads and appends, because about nine in ten of the 96 denials the old guard gave in a replay of recorded commands were read-only inspections, appends or writes to other files.
- **Signal:** Over the next 30 days of recorded sessions, or the next 40 denials of this guard, whichever comes first, classify each denial of a shell command by reading the command. Confirm if fewer than 10% are plain reads or appends; refute if more than a quarter are. A python script that reads the file and writes another is a known false positive and is counted separately, not here. Fewer than 20 denials leaves the hypothesis inconclusive.
- **Risk:** A guard that denies less can let a rewrite through; the python-on-stdin shape is now denied, but the known gaps listed in its docstring remain open.
- **Status:** PENDING
- **Changelog ref:** 2026-10-27 — Collect the skill tests in CI, rebuild the learnings guard's shell arm and fix the extractor's rejection count

## 2026-09-14

### [SKILL-ADDED] Share portable flow mapping through Core
- **Category:** Coverage
- **Hypothesis:** By shipping the flow tools with explicit consumer roots and independent fixtures, we expect new projects to produce accepted flow maps without manual path repairs because validation no longer depends on the source checkout.
- **Signal:** Inspect the next two submitted flow-map changes outside the source project, or by 2026-11-09, whichever comes first, using their git diffs and review comments. Confirm if both are accepted without a manual tool-path repair; refute if either requires one. No qualifying submissions leaves the hypothesis inconclusive.
- **Risk:** Agents can over-read a structural pass as a truth claim; evidence review remains manual.
- **Status:** PENDING
- **Changelog ref:** 2026-09-14 — Share portable flow mapping through Core
