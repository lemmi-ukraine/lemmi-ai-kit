# Session Retrospective Report Template

Behavioral findings lead. Every finding carries: session id(s), a redacted quote or metric, an
occurrence count (≥2 to be a pattern), and whether it's already captured in a rule/learning.

---

```markdown
# Session Retrospective: {date_range}

Generated: {current_date}
Sessions analyzed: {count}  (deep-dived: {n}, JSON-only: {m})
Sub-agents: {totalAgents} ({agentsWithErrors} with errors, {subDeepDived} deep-dived)
Period: {from_date} to {to_date}

## Executive Summary

{3-5 bullets — the highest-impact BEHAVIORAL findings, each with its occurrence count}

## Prior-Report Reconciliation

{REQUIRED when a prior report exists (Phase 4h) — one row per prior P1–P5 recommendation.
Calibration: the 2026-06-22 report's "What Changed Since the 2026-06-21 Report" table.}

| Prior recommendation | Status now | Check performed |
|----------------------|-----------|-----------------|
| {P1: rule text} | applied {date} ({file § section}) / still open / superseded by {what} | {grep/read evidence} |
{still-open P1/P2 items are carried into this report's Recommendations explicitly}

## Behavioral Findings

### Recurring-Mistake Taxonomy
{Cross-session error patterns from errorTaxonomy + deep-dives. A mistake recurring across multiple
sessions is the highest-value finding.}

| Category | Count | Sessions | Sample (redacted) | Already covered? (effect join) |
|----------|-------|----------|-------------------|------------------|
| edit-stale-read | 20 | 0f65932c, 640fb5dd, … | "File has been modified since read" | Rule since {date} — 20 occurrences AFTER → prose failing, escalate Enforce-via |
{one row per recurring class; the last column carries the 4a effect join — covered-since date +
post-date occurrence count, and the escalation verdict when the trap recurs despite coverage}

### Tool Thrash / Wasted Effort
{From behavior.reReads / repeatedCommands / buildTestLoops / staleReadEdits + deep-dive thrash.}

| Signal | Evidence (session × count) | Interpretation |
|--------|----------------------------|----------------|
| File re-read ≥3× | learnings.md 7× (0f65932c), default.txt 6× (a45a6445) | Agent loses place in large files |
{one row per thrash signal}

### Workflow Friction
{Blocked skills, repeated questions, permission denials.}

| Friction | Occurrences | Evidence | Likely cause |
|----------|-------------|----------|--------------|
| Blocked skill invocation | plan-critic, branch-switch, commit-message | stats.skillsBlocked | Agent tried to call disable-model-invocation skills directly |

### Repetitive Questions
{Same AskUserQuestion theme across ≥2 sessions → a missing default/config/rule.}

| Question theme | Sessions | Suggested default to encode |
|----------------|----------|-----------------------------|
{one row per repeated question}

## User Feedback Analysis

### Corrections (user told AI it was wrong)
| Session | Quote (redacted) | Category | Captured in Rules? |
|---------|------------------|----------|--------------------|
{each correction — existence-verified}

### Preferences (how things should be done)
| Session | Quote (redacted) | Category | Captured in Rules? |
|---------|------------------|----------|--------------------|
{each preference}

### Redirections (approach changed mid-task)
| Session | What AI was doing | What user wanted instead |
|---------|-------------------|--------------------------|
{each redirection}

## Convention Gap Analysis

### Rules Enforced by User but Not in AGENTS.md
{Conventions the user stated that aren't captured}

### Rules in AGENTS.md That AI Violated
{Cases where AI broke an existing rule. PER FINDING: verify the rule's date predates the violations
(Phase 5 causation check) — quote the rule date. If the rule post-dates, mark "now covered" instead.}

## Skill Effectiveness

### Skills Used
| Skill | Times Invoked | Blocked? | Effective? |
|-------|---------------|----------|------------|
{from stats.skillsUsed / skillsBlocked}

### Skills Never Used
{Exist but not invoked in the period}

### Missing Skills (Repeated Manual Work)
{Tasks done manually ≥2× that could be a skill}

## Sub-Agent Behavioral Findings
{REQUIRED (Phase 3b) — never omit. If clean, state "sub-agents ran clean ({totalAgents} agents, 0 with errors)".
Volume: {stats.subAgent.files} agents, {bytes}, {msgs} msgs.}

### Sub-Agent Error Taxonomy (from `subAgentErrorTaxonomy`)
| Category | Count | Sessions | Sample (redacted `[id/sub]`) |
|----------|-------|----------|------------------------------|
{one row per non-zero category — same classify-by-origin-tool rules as the main taxonomy}

### Sub-Agent Deep-Dive (top ≤6 high-signal)
{Findings from the bounded deep-dive of emitted `sessions/sub/<id>/*.md`: errors hit, any
WRONG/FABRICATED result returned to the orchestrator, internal thrash — each with the sub-agent
transcript as evidence. State how many were scanned via taxonomy only (beyond the ≤6 cap).}

## Absence Sweep (Phase 4i)

{REQUIRED — the dog that didn't bark. Everything above is built from things that HAPPENED; the
extractor cannot emit an event for a thing that never occurred. Answer each ask explicitly.
"Nothing found" is a valid answer; silence is not. The last row also feeds the Pipeline Health
table's final row.}

| Ask | Answer |
|---|---|
| Which skills never fired while their job was done by hand? | {cause, not a list} |
| Which quality gate was never run in a window that shipped code? | {n} |
| What did the user approve repeatedly that never needed approving? | {n} |
| Which recommendation from the last report produced no evidence either way? | {INCONCLUSIVE, not "applied"} |
| What did the user have to ask for that the pipeline should have offered? | {n — list them} |

## Hypothesis Evidence (feeds hypothesis-validator)

{CONDITIONAL (4g) — include only when ≥1 PENDING hypothesis's Signal window overlaps this
period AND the data speaks. Report-only: statuses are the hypothesis-validator's to change.}

| Hypothesis (title + ref date) | Window state | Evidence FOR | Evidence AGAINST |
|-------------------------------|--------------|--------------|------------------|
{session ids / metrics per cell; "none observed" is a valid cell value}

## Pipeline Health

{REQUIRED — fixed per-window trend table; consumed by hypothesis-validator and the
learning-consolidator. Data: aggregate.json, git history of `.ai/` data files,
`PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint learnings --list-entries`. One table — not a dashboard.}

| Metric | This window | Prior window |
|--------|-------------|--------------|
| Sessions analyzed (deep-dived) | {n} ({m}) | {n} ({m}) |
| Main-thread errors — top categories | {cat: n, cat: n} | {…} |
| Sub-agent errors (agents with errors / total) | {n}/{N} | {…} |
| Learnings intake: added / drained since last window | {n} / {n} | {…} |
| Hypotheses: opened / validated since last window | {n} / {n} | {…} |
| **Findings the USER supplied that this data already contained** | {n} — list them | {…} |

{The last row is the pipeline's own error rate (§4i Absence Sweep). A finding the user had to
point out, which the extractor data already supported, is a defect in THIS skill — name it and
fix the step that should have caught it. The 2026-08-01 run scored 2: a zero-invocation skill
whose cause sat one join away in its own model-distribution data, and a permission-economy
question it never asked despite measuring the friction.}

## Recommendations

### Priority 1: New/Strengthened Rules for AGENTS.md
{Specific rule text. Tie each to a recurring behavioral finding above.}

### Priority 2: Skill Updates
{Existing skills to modify, with specific changes}

### Priority 3: New Skill Candidates
{Repeated manual tasks warranting a new skill}

### Priority 4: New Learnings
{Findings to append to .ai/learnings.md — these feed /learning-consolidator}

### Priority 5: Workflow Changes
{Changes to the overall AI development workflow}

## Method note
Errors classified by origin tool (no content false positives). Deep-dive quotes existence-verified
against per-session transcripts. "Recurred despite rule" claims date-checked. Raw transcripts and
absolute paths are NOT included — only redacted synthesized findings.
```
