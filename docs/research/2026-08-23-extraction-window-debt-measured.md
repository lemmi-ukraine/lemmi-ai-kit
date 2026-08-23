# W-window measured — 13 skills exposed, 85% of their window content gone, and 84% of the loss in six of them

**Dated:** 2026-08-23.
**Measures:** the debt opened by
[2026-08-23-i2-w2-4-handoff-to-orchestration.md](2026-08-23-i2-w2-4-handoff-to-orchestration.md) §2
and recorded as `[extraction_window] status = "unreviewed"` in
[upstream-sync.toml](../upstream-sync.toml).
**Scope:** read-only. No skill, test, pin or manifest was edited. Deliberately runs beside I4,
which needs `assets/skills/` quiet.

W2.4 established that 1,644 insertions were **eligible** to be misclassified as deliberate kit
deletions, and spot-checked one skill. This measures how many are **actually** absent from the
shipped pack, per skill, so the debt can be scoped instead of estimated.

---

## 1. The answer

| Population | Lines |
|---|---|
| Window insertions across the skills tree, `git diff --numstat` | **2,668** |
| — in the three scripts the kit deliberately does not ship | **1,024** |
| — remainder, W2.4's "skill content" figure | **1,644** |
| Same remainder counted as non-blank content lines, in files the kit ships | **1,417** |
| **Carried after all** | **794** (56%) — but see the exposure split below, and §5 on what "carried" counts |
| **Absent — exact match** | **623** (44%) |
| **Absent — under the loosest matching rule tried** | **580** (41%) |
| Of the 623, explained by a known portability rule | **39** |

### 1a. The rate above is diluted — half the population was never at risk

Two of the 15 skills were never exposed to the wrong base, and between them they hold **713 of the
1,417 lines**. Leaving them in the denominator halves the apparent loss rate.

| | Skills | Window lines | Absent (exact) | Loss rate |
|---|---:|---:|---:|---:|
| **Never exposed** — `hypothesis-validator` (fresh W2.3 port, first in the kit 2026-08-23, never three-way merged) and `session-retrospective` (merged against the *true* base) | 2 | 713 | 24 | **3%** |
| **Exposed** — extraction-era, refreshed against `c05bf72d` | 13 | **704** | **599** | **85%** |
| All 15 as published above | 15 | 1,417 | 623 | 44% |

**The honest headline is 85%, not 44%** — among the skills that actually ran the defective merge,
between **80% and 85%** of the window content is gone (85% exact, 80% under the loosest fuzzy rule).
The debt is smaller in scope than 15 skills and far more severe inside that scope.

`lemmi-python-conventions` and `lemmi-test-conventions` are in the exposed group: both trace to the
`002dadd` initial release and were only *renamed* on 2026-08-22, which a naive
`--diff-filter=A` on the new path misreports as a fresh port.

**Both reconciliations with W2.4 are exact**, which is why the rest is trustworthy: numstat returns
2,668, and the three unshipped scripts are 453 + 229 + 342 = **1,024**. The 2,668 → 2,318 difference
against this run is 350 blank lines; W2.4 counted insertions including blanks, this counts content.

A further **901** non-blank window lines sit in files the kit ships no version of at all: the two
linters and their tests (875), `skill-creation-workflow/references/subagent-preamble.md` (25), and
one line in `prompt-engineering-conventions`, which I1 removed. Those are out of scope by decision,
not by oversight.

## 2. The work list, ordered

Absent under the strictest and loosest rules, per skill. Use the last column to scope; use the gap
between the two to see how much is wording drift rather than loss.

| Upstream skill | Ships as | Exposed? | Window lines | Carried | Absent (exact) | Absent (fuzzy) | Rule-explained |
|---|---|---|---:|---:|---:|---:|---:|
| `skill-creator` | same | yes | 124 | 1 | 123 | **119** | 5 |
| `learning-consolidator` | same | yes | 170 | 40 | 130 | **114** | 15 |
| `skill-reviewer` | same | yes | 110 | 3 | 107 | **102** | 4 |
| `lemmi-python-conventions` | `python-conventions` | yes | 58 | 6 | 52 | **52** | 0 |
| `skill-creation-workflow` | same | yes | 49 | 0 | 49 | **45** | 5 |
| `ai-improvement-tracker` | same | yes | 53 | 11 | 42 | **37** | 2 |
| `ai-changelog` | same | yes | 23 | 2 | 21 | **20** | 1 |
| `skill-researcher` | same | yes | 19 | 0 | 19 | **19** | 0 |
| `skill-content-reviewer` | same | yes | 18 | 0 | 18 | **18** | 0 |
| `lemmi-test-conventions` | `test-conventions` | yes | 21 | 5 | 16 | **16** | 0 |
| `task-learnings` | same | yes | 56 | 37 | 19 | **15** | 2 |
| `ai-docs-lookup` | same | yes | 2 | 0 | 2 | **2** | 0 |
| `openai-realtime-quirks` | same | yes | 1 | 0 | 1 | **1** | 0 |
| `hypothesis-validator` | same | **no** — fresh W2.3 port | 115 | 102 | 13 | **12** | 2 |
| `session-retrospective` | same | **no** — correct-base merge | 598 | 587 | 11 | **8** | 3 |
| **Total, exposed only** | | | **704** | **105** | **599** | **560** | **34** |
| **Total, all 15** | | | **1,417** | **794** | **623** | **580** | **39** |

**All six heaviest rows are exposed skills. Top three are 335 lines — 60% of the 560. Top six are
469 — 84%.** This is not a flat 15-skill sweep; it is three skills, then three more, then a tail
where four skills have 2 lines or fewer between them.

**Five of the top six are the meta/authoring skills** — `skill-creator`, `skill-reviewer`,
`skill-creation-workflow`, `learning-consolidator`, plus `skill-researcher` and
`skill-content-reviewer` just below. The window happens to be when upstream did its skill-authoring
work, and that is precisely the cluster this pack exists to ship.

## 3. Two controls say the base is the cause, and the fix works

Every tracked skill is synced to the **same** target upstream — the pin `a78ee5af` — and
`session-retrospective` is the only row carrying a `base` override. So across these 15 skills the
target is held constant and the *base* is the only variable. That is what makes the comparison a
control rather than an anecdote.

| Skill | How it reached the pin | Window lines carried |
|---|---|---|
| `session-retrospective` | three-way merge against the **true** base `3dd2496d` | **587 of 598** (98%) |
| `hypothesis-validator` | **fresh port** from current upstream — no merge, no base | **102 of 115** (89%) |
| `skill-creator` | three-way merge against the **wrong** base `c05bf72d` | **1 of 124** (1%) |

Same content, same window, same instrument, same destination. The two paths that never consulted
`c05bf72d` carried nearly everything; the path that did carried almost nothing. This debt is an
artifact of the base, not a set of judgement calls someone already made — and §1a's 85% is the
size of it.

`session-retrospective`'s 11 exact-absent lines are accounted for by its own session as its 14
deliberate portability substitutions.

**Correction to an earlier draft of this document:** it claimed *"every other skill on the list was
refreshed against the base four days too new."* That is false — `hypothesis-validator` was ported
fresh on 2026-08-23 and never merged against any base. Leaving it in the exposed group is what
diluted the published loss rate from 85% to 44%.

## 4. What the absent content actually is

Mechanical markers explain only 39 of 623, so the character matters more than the count. Both kinds
are present and a per-skill read has to separate them.

**Portable, and the pack is worse without it:**

- `skill-creator` — the *"Is a skill the right artifact?"* routing table (hook vs custom agent vs
  AGENTS.md line vs memory vs skill) and the extend-vs-create check. Domain-agnostic skill-authoring
  guidance, and 74 of its 75 `SKILL.md` window lines are gone.
- `python-conventions` — aliased Pydantic construction under `basedpyright` (construct with the
  alias, not the field name), the double-cast partial-DI test-double idiom, positive partitioning of
  `asyncio.gather(return_exceptions=True)`. Real Python guidance with no Lemmi in it.
- `ai-changelog` / `ai-improvement-tracker` — the closed 12-type taxonomy and its pairing rule, the
  strict reverse-chronological ordering invariant, the behavioral-vs-administrative gate, and the
  synonym-mapping table that stops near-duplicate categories.
- `learning-consolidator` — the `PROMOTE_TO_RULE` / `_README` / `_COMMENT` / `KEEP` action taxonomy
  and its scope test, plus the recommendation-lifecycle loop.

**A named, behavioural instance — and the guards do not see it.** Upstream's change-type table at
the pin has **12** members. The shipped table has **11**, `checks.CHANGELOG_TYPES` has **11**, and
`EXPERIMENT-REGISTERED` returns **0 hits across the whole package** — the member is gone from the
doc, the constant, and `ai-improvement-tracker`, which carried its pairing rule (such an entry
*always* requires a dated, falsifiable hypothesis with a re-eval date). This is not a line count; it
is a taxonomy member the pack no longer offers.

**And the full test suite is green.** `test_changelog_types_match_the_shipped_skill` asserts
*shipped doc == kit constant*, and both operands lost the member together. It is one of five pins
sharing that design, and none consults upstream. The vocabulary pins guard **internal** drift, not
upstream fidelity — see the completion review §2 for what that implies for promoting either gate.

**Correctly absent, and must not be restored:**

- `backend/app/core/<module>/README.md` and `backend/app/features/<feature>/` promotion targets
  throughout `learning-consolidator`'s reference files.
- `python .claude/skills/learning-consolidator/scripts/ai_files_lint.py …` invocations of the
  linters the kit replaced with its CLI.
- Machine-specific rules — *"use the project venv python or plain `python`, never `uv run` on this
  Windows host"*.
- Dated probe citations and named source-project test files.

The mechanical 39 is a floor, not the split. `learning-consolidator`'s reference files are heavily
path-bound and will shed far more than their 15; `skill-creator` and `python-conventions` will shed
close to nothing.

## 5. The instrument, and the hypothesis it refuted

Three prior measurements in this initiative returned confident nonsense, so the controls are stated.

- **git output is decoded UTF-8 explicitly**, never `subprocess(text=True)`. That exact defect
  turned 14 rewritten lines into 176 phantom dropped ones in the `session-retrospective` review.
- **Added lines come from `difflib` opcodes**, not from parsing diff text; paths arrive `-z`.
- **The record is read through W2.4's own loader**, not re-parsed.
- **A control that could have failed:** W2.4 independently measured
  `skill-researcher/SKILL.md` at 19 window-added lines, all absent. This run returns **19 and 19**.
- **A hypothesis of my own, refuted:** the pack has an ASCII-only rule and upstream uses em-dashes,
  so exact matching should have called carried-but-repunctuated lines absent. Normalising em-dashes,
  en-dashes, curly quotes, ellipses and NBSP recovered **exactly 0** of 623. The lines are not
  there in any form. Aggressive alphanumeric normalisation recovered 8; fuzzy matching at 0.90
  recovered a further 35. **The count is not an artifact of the matching rule** — that was the one
  way this whole result could have been wrong, and it was tested rather than argued.

### 5a. Where "carried" is weaker than "absent"

The absent count survived every challenge. The **carried** count did not, and it is the softer of
the two figures. Of the 794 lines counted as carried:

| | Lines |
|---|---:|
| Substantive (>25 chars, not pure structure) | **540** |
| Short, <=25 chars — `try:`, `sys,`, `},`, `{` | 232 |
| Pure structure — table separators, fence markers, `"""`, `---` | 22 |
| Duplicated within the carried set | 122 |

A one- or two-character line matches somewhere in almost any file, so those 254 short and structural
matches are coincidence as often as carriage. Treating every one of them as a false carry puts the
all-15 absent count as high as **877 of 1,417 (62%)** rather than 623 (44%).

**Direction of the bias: this makes the debt bigger, never smaller.** The published absent counts are
the conservative end of the range, and §1a's 85% exposed-loss rate is a floor.

## 6. What this does not establish

- **It does not say what to restore.** 580 is an upper bound on recoverable content. The
  portable/correctly-stripped split needs a human read per skill; §4 is a characterisation from
  samples, not a classification of all 580.
- **Presence is line-membership in the shipped file.** A line counted as carried could be present
  for an unrelated reason — quantified in §5a, and it pushes the absent count *down*, so the
  published figures are conservative.
- **Matching was per-file, and an earlier draft of this section had the consequence backwards.** It
  claimed a line relocated to another file inside the same skill "still counts as carried". It would
  have counted **absent** — the check compared upstream `<skill>/X` against kit `<skill>/X` only.
  Re-run against every file in the skill directory: **623 absent either way, 0 lines relocated.**
  The claim was wrong; the number it applied to was not.
- **It measures the working tree**, which currently holds two uncommitted sessions. That is why
  `session-retrospective` reads as reconciled here while `upstream-sync.toml` still records it
  behind — deliberately, per that record's note.
- **Nothing here re-reads the 38 skills.** Only the 16 window directories were touched, and only
  their window lines.

## 7. Owed, if this is acted on

1. `[extraction_window] status` in [upstream-sync.toml](../upstream-sync.toml) moves from
   `"unreviewed"` to measured, pointing here. **Not done: that file belongs to the uncommitted W2.4
   work and the operator has left it uncommitted.**
2. A row in [README.md](README.md) for this document.
3. If W-window is funded, scope it as **three skills, not fifteen** — `skill-creator`,
   `learning-consolidator`, `skill-reviewer` recover 60% of it, and six recover 84%. Two of the 15
   need nothing at all (§1a), and the four with two lines or fewer are not worth a session between
   them.
4. Re-merge rather than hand-restore: §3 is evidence that a three-way merge against
   `3dd2496d` recovers this content, which is how `session-retrospective` got to 8.
