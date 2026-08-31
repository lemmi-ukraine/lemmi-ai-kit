# The report completeness gate — what it checks and why each check exists

`scripts/check_report.py` is the mechanical half of Phases 5–7. Every check below encodes a failure
**measured on the 2026-08-29 run of this skill**, where all three requirements were already written
in `SKILL.md` and all three were violated by the session that had just read them.

```
python ${CLAUDE_SKILL_DIR}/scripts/check_report.py \
  --report .ai/retrospectives/{date}-retrospective.md [--check sections|workers|durability|all]
```

Exit 0 = complete. Exit 1 prints one finding per line (stdout), summary to stderr. Exit 2 = bad
invocation. Never present a report, or claim the retrospective is finished, under exit 1.

## `--check sections`

Asserts every Phase-6 required section is present, matched against **heading lines only**.

*Why:* the 2026-08-29 report shipped without "Pipeline Health" — which Phase 6 names a Required
section — and without the template's User Feedback Analysis (4e) and Repetitive Questions (4d).
Three required analyses absent with no signal, because **a missing section reads exactly like a
section with nothing to report**. Unlike every other gate in this repo, it fails by looking finished.

*Why headings only:* the negative fixture (`fixtures/report_complete.md`'s sibling,
`report_missing_sections.md`) deliberately names "pipeline health" and "repetitive questions" in
prose. A whole-file substring checker scores it clean and cannot pass the probe.

## `--check workers`

Fails when any `.ai/dispatch/logs/*.out` has an mtime later than the report's.

*Why:* W2 — the Phase-4e operator-correction sweep, which classified all 366 candidate messages into
24 CORRECTION / 18 PREFERENCE / 23 REDIRECTION with a grep-verified capture join per theme — was
dispatched at 16:47 and returned at **17:17**. The report was written at 17:04 and never mentions
it. No error, no timeout, no visible gap. Three of its seven themes were captured **nowhere** and one
was **contradicted** by `spec-driven-dev/SKILL.md:373`; all of it was lost until a later pass looked.

The general form matters beyond this skill: any workflow that fans out and synthesizes owes a
`dispatched N == returned M + dropped-with-reason K` reconciliation before the synthesis is written.
Otherwise the moment the writing starts silently decides the corpus.

## `--check durability`

Asserts the date's `.ai/ai-changelog.md` entry is reachable from `HEAD` — not merely present on
disk — and that a companion hypothesis exists for the same date.

*Why:* on 2026-08-29 the changelog entry and 15 learnings existed **only inside a stash**.
`git show HEAD:.ai/ai-changelog.md | grep -c '## 2026-08-29'` returned **0**, while the report's own
header stated that this file "is what the next run's Phase 4h reads" and §7 pointed at that entry as
its durable record. Both statements were true about a file that did not contain it. "Wrote the
entry" and "the next run can read the entry" are different claims; the skill only ever checked the
first, by not checking at all.

The hypothesis half exists because that run wrote none — while its own P1-2 recommended giving
`ai-improvement-tracker` a firing seam *because* it has zero invocations across 191 sessions.

### When a peer holds the tree

Do not append to a reverted baseline. If HEAD is detached, paths are unmerged, `.git/rebase-merge`
exists, or a peer has just stashed your files, stage the ledger blocks under
`.ai/handoffs/{date}-retro-finalization/` with an explicit apply order and record that in the report's
completion-state section. Note that this check asserts *reachability*, not correct branch placement —
committing the ledger onto whichever branch happens to be checked out satisfies it and is still wrong.

## Probing the gate

The probe caught this checker **blind on first write**: a date guard made `--check sections` exit 2
with empty stdout, which a caller reads as "no findings". Re-probe after any change to
`REQUIRED_SECTIONS`:

```
python ${CLAUDE_PLUGIN_ROOT}/skills/post-task-review/scripts/probe_checker.py \
  --cmd 'python ${CLAUDE_SKILL_DIR}/scripts/check_report.py --check sections --report {file}' \
  --positive ${CLAUDE_SKILL_DIR}/scripts/fixtures/report_missing_sections.md \
  --negative ${CLAUDE_SKILL_DIR}/scripts/fixtures/report_complete.md
```

Recorded verdict: `probe_checker: positive=4 negative=0 verdict=CAN-SEE`.

**Known residual.** `REQUIRED_SECTIONS` duplicates `references/report-template.md` instead of
deriving from it. If the template gains a section the gate does not, the gate returns a clean zero
for an incomplete report — the exact defect it was built to catch, one level up. Deriving the list
from the template is the right fix and is not yet done.
