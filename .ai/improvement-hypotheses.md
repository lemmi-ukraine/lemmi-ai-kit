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
