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

## 2026-09-14

### [SKILL-ADDED] Share portable flow mapping through Core
- **Category:** Coverage
- **Hypothesis:** By shipping the flow tools with explicit consumer roots and independent fixtures, we expect new projects to produce accepted flow maps without manual path repairs because validation no longer depends on the source checkout.
- **Signal:** Inspect the next two submitted flow-map changes outside the source project, or by 2026-11-09, whichever comes first, using their git diffs and review comments. Confirm if both are accepted without a manual tool-path repair; refute if either requires one. No qualifying submissions leaves the hypothesis inconclusive.
- **Risk:** Agents can over-read a structural pass as a truth claim; evidence review remains manual.
- **Status:** PENDING
- **Changelog ref:** 2026-09-14 — Share portable flow mapping through Core
