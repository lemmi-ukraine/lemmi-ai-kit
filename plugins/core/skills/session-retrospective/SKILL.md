---
name: session-retrospective
description: >
  Analyze Claude Code session history for a time period and produce a BEHAVIORAL retrospective:
  recurring-mistake taxonomy, tool thrash, workflow friction, repetitive questions, uncaptured
  feedback, and convention gaps — grounded in real agent behavior, not just "what we worked on".
  Use when the user says "session retrospective", "analyze sessions", "review past sessions",
  or "what patterns emerged".
argument-hint: "[--since YYYY-MM-DD] [--until YYYY-MM-DD]"
metadata:
  type: task
---

# Session Retrospective — Behavioral Pattern Analysis

ultrathink

## Role

You are a Retrospective Analyst. You find **how the agent actually behaved** across sessions —
recurring mistakes, wasted effort, friction, repetitive questions — plus uncaptured user feedback
and convention gaps. You produce a structured report with an actionable, evidence-backed plan.
Every claim is grounded in extractor data or a verifiable transcript quote. A pattern requires
**≥2 occurrences**. You never fabricate and you never report a single event as a pattern.

## When This Skill Activates

- User says "session retrospective", "analyze sessions", "review past sessions"
- User wants to know what behavioral patterns emerged across recent AI sessions
- User invokes `/session-retrospective`

## Input

Optional date range: `--since YYYY-MM-DD --until YYYY-MM-DD`. Default: last 14 days.

---

## Pipeline

### Phase 0 — Cadence Guard

Check the newest `.ai/retrospectives/*.md` date. If it is **<7 days old** AND the user did not
explicitly ask for a retrospective, report "last retrospective is {date} ({N} days ago) —
fresh; skipping" and stop (offer to run anyway). This keeps the proactive-run permission
(AGENTS.md standing exception) from firing too eagerly. An explicit user ask always runs.

**Event-trigger exception to the 7-day floor.** The calendar guard is blind to a bad window: in
2026-08-01→07 the damage landed on days 1–3 (≥20 workers dead on usage limits, a worktree removed
under a live session) and the retro that measured it ran on day 6 — only because the user asked.
Between the weekly retro and the weekly drain there is **no event-triggered signal path**, and a
risk clause written into the hypothesis ledger is read only at validation time, days after the
event it predicted. So when any of these high-cost shapes is observed, the floor does not apply and
a retrospective may be OFFERED early (a suggestion, never an auto-run):

- N workers dead on usage limits inside one session,
- any `git worktree` mutation after the 2026-08-07 ban,
- a hook or gate that blocked both shells.

Say which trigger fired and how many days early; the user decides.

> **Report durability (decided 2026-08-07, operator).** `.ai/retrospectives/` is **gitignored** —
> reports are local scratch, and `.ai/ai-changelog.md` is the **sole** reconciliation source of
> record. This settles a policy that three prose reminders failed to move (0 of 3 reports ever
> committed). Two consequences: do NOT offer to stage the report or describe it as durable, and
> treat the prior-report load in Phase 2 as best-effort — when the file is absent, reconstruct the
> P1–P5 baseline from the changelog, which is the sanctioned path, not a degraded one. Anything a
> future run must be able to reconcile against therefore belongs in the **changelog entry**, not
> only in the report.

### Phase 1 — Extract Session Data

Run the behavioral extractor. It emits an aggregate JSON **and** per-session readable transcripts,
all redacted, into a gitignored temp dir.

```bash
python "${CLAUDE_SKILL_DIR}/scripts/extract_sessions.py" \
  ".ai/tmp/retro/" [--since YYYY-MM-DD] [--until YYYY-MM-DD] --self-check
```

- **`<session-dir>` is auto-derived — omit it (as above).** The extractor walks up from its own
  location to the repo root and finds THIS repo's dir under `~/.claude/projects/<encoded>`. Claude
  Code names that dir after the repo's absolute path with every `/`, `\`, `:` replaced by `-`, so it
  is machine-specific (drive letter, username, and clone location differ per engineer) — **never
  hardcode one engineer's session dir.** Pass an explicit first positional ONLY to override (e.g. a
  personal-scope install where this skill is not inside the project's `.claude/`):
  `… extract_sessions.py "<session-dir>" ".ai/tmp/retro/" …`. The run prints `Using session dir: …`
  to stderr — confirm it points at this repo.
- `<output-dir>` is ALWAYS repo-relative (`.ai/tmp/retro/`) — never the system `/tmp`.
- The extractor is pure stdlib. Use the project `.venv` python or system `python`; do NOT use
  `uv run` (it may trigger an environment sync that rebuilds project deps this stdlib script
  doesn't need). On Windows the venv python is `.venv/Scripts/python.exe`.
- **Porting this script elsewhere** — it pins Python **3.11+**, redacts SECRET shapes only (no
  email/PII patterns), and detects the repo root differently from the kit's `lint` command:
  [references/extractor-output-schema.md](references/extractor-output-schema.md) § Porting.
- **Date default:** the extractor has NO built-in default — with no `--since/--until` it processes
  ALL history. To honor the 14-day default, THIS skill computes `--since` (today − 14 days) and
  passes it unless the user gave a range. `--since/--until` filter on date *overlap*, not strict
  containment.

**Verify the run** from stderr: it prints `Using session dir: …` (confirm it points at THIS repo —
that is the auto-derivation target), the session count, the error-by-category line, a
**`Sub-agents:`** line (total agents, agents-with-errors, transcripts emitted), and
`SELF-CHECK PASSED`. If self-check fails (exit 3), STOP — a secret shape leaked; do not proceed.
If no sessions match the range, inform the user and stop.

The output schema is documented in [references/extractor-output-schema.md](references/extractor-output-schema.md).

### Phase 2 — Load Context

1. **`.ai/tmp/retro/aggregate.json`** — the primary data (taxonomy + per-session behavior).
2. **`.ai/learnings.md`** — to avoid re-discovering known findings AND to date-check "recurred
   despite a rule" claims later (Phase 5).
3. **`AGENTS.md`** — to identify convention gaps (rules the user enforces that aren't captured, or
   rules the AI violated).
4. **available skills** — project `.claude/skills/` (if present) plus the lemmi-ai-kit plugin catalog (effectiveness analysis).
5. The most recent prior report in `.ai/retrospectives/` (if any) — don't repeat its findings,
   AND extract its **Recommendations** (P1–P5) for the Phase-4h reconciliation.
6. **`.ai/improvement-hypotheses.md`** — the `PENDING` hypotheses whose Signal window overlaps
   this period (feeds 4g).
7. **Deferred pipeline work** — `tasks/TECH-deferred-consolidation-*.md` and the most recent
   `.ai/consolidation-plan-*.md` open items: surface still-open deferred work in the report
   rather than letting it stay orphaned.
8. **The auto-memory index (`MEMORY.md`)** — already loaded in your context each session
   (per-machine, not in the repo). Needed for the 4e/4f "already captured?" checks: a
   preference may live in memory rather than AGENTS.md/skills.

### Phase 3 — Deep-Dive the Substantial Sessions (parallel sub-agents)

The aggregate JSON gives cross-session metrics; the per-session transcripts give the *narrative* of
what went wrong. Read the narratives for the substantial sessions in parallel.

1. **Select** substantial sessions by CONSUMING `aggregate.json`'s `deepDiveCandidates`
   (schema v4): `selected[]` is the deep-dive set (the extractor already applied the rule —
   toolUse ≥ 15 OR userMsgs ≥ 6; ranked by toolUse desc, transcriptBytes desc, sessionId;
   top 8). Do NOT re-rank or re-derive by hand — LLM arithmetic/sorting is a known error
   class; the list is deterministic. Log every `overCap[]` entry as "analyzed via JSON only"
   (do not silently drop them).
2. **Spawn one sub-agent per selected session, in parallel** (multiple Task calls in one message).
   Pass each the **ABSOLUTE** `transcriptPath` from the session object (a relative path would
   reproduce the path-not-found mistake this skill is meant to catch). Sub-agent prompt:

   > You are a session-behavior analyst. Read ONLY this transcript (absolute path): `<transcriptPath>`.
   > It is a redacted, size-capped record of ONE Claude Code session. Return STRUCTURED findings
   > (≤1.5 KB total), citing evidence (a tool line or a ≤15-word quote) for each:
   > 1. **Goal & outcome** — what the user wanted; outcome = completed | continued | abandoned.
   > 2. **Corrections** — each time the user told the agent it was wrong/off-track: quote the user +
   >    how the agent responded.
   > 3. **Recurring mistakes** — the same error/wrong approach ≥2× in this session.
   > 4. **Wasted effort / thrash** — re-reads, stale-read edit retries, repeated commands,
   >    visible backtracking.
   > 5. **Friction** — blocked skills, repeated questions, permission denials, confusion.
   > 6. **Ideal agent** — what a well-calibrated agent would have done differently.
   > If a category has nothing, write "none observed". Do NOT invent; quote only what is in the file.

3. **Fallback:** if a sub-agent fails or returns nothing, fall back to the JSON metrics for that
   session and note it. **Never block the whole retrospective on one sub-agent.**

4. **When the user named FOCUS AREAS, three compensations are MANDATORY technique, not
   improvisation.** Keep the ranking deterministic (LLM re-ranking is a known error class), but
   recognise what it optimises: generic substantialness, *not* question-relevance. In the 08-07 run
   it left the second-most-relevant session (56 sub-agents, one of only two `/orchestrate`
   invocations) in the JSON-only `overCap` pool, put 5 of 6 sub-agent picks inside ONE parent
   session, and spent 2 of 8 slots on boundary sessions the prior report had already deep-dived.
   All three of the run's decisive findings came from these compensations:
   - **(a)** Before spawning anyone, run main-thread targeted greps for the focus-signal tokens
     across **all** transcripts, not just the selected ones.
   - **(b)** Thread the focus areas into every analyst prompt as numbered FOCUS questions — the
     analysts' focus answers carried the report.
   - **(c)** Tell boundary-session analysts which findings the prior report already owns, so their
     slots return only NEW material.

   Two standing extractor improvements this implies (candidates, not yet built): downweight sessions
   the prior report already deep-dived (its ids are in the report), and cap sub-agent picks per
   parent session for diversity.

### Phase 3b — Sub-Agent Behavioral Scan (REQUIRED)

Orchestration-heavy work runs largely *inside* sub-agents — a single session can fan out dozens.
Their internals are otherwise invisible to the retrospective. The extractor (1) runs the SAME error
taxonomy over every sub-agent transcript → `subAgentErrorTaxonomy` in `aggregate.json`, and (2)
emits **redacted** transcripts for the high-signal ones (any error, or the largest few) under
`.ai/tmp/retro/sessions/sub/<sessionId>/`, each absolute path recorded in that session's
`subAgents.highSignal[].transcriptPath`. This step is **not optional** — always do both parts:

1. **Always — report the aggregate sub-agent taxonomy.** Read `subAgentErrorTaxonomy.byCategory`
   (counts + sessions + redacted `[id/sub]` samples) and the totals (`totalAgents`,
   `agentsWithErrors`, `transcriptsEmitted`). A sub-agent error class that recurs across sessions is
   a finding exactly like a main-thread one — cite it with its `[id/sub]` provenance.

   **Decompose the headline by SHAPE before comparing windows.** The ORIGIN-tool classifier is
   content-blind by design (that is what fixed the substring false-positive class), so
   harness-generated failures land in behavioral buckets and inflate the rate. "112 of 264 agents
   with errors (42%) vs 3 of 29 (10%)" reads as a 4× agent-quality regression; hand-decomposition
   showed the growth was dominated by **deny-cd hook denials** (enforcement working as designed),
   **usage-limit kills** mid-wave ("You've hit your session limit"), and **permission-stream
   aborts** when the parent paused at the usage-guard floor ("Tool permission stream closed before
   response received"; "The permission handler returned updatedInput … failed schema validation")
   — the last two landing in `test-failure`/`tool-error`. Without that split, every
   orchestration-heavy window reads as an agent regression and cross-window comparisons are
   apples-to-oranges. Never quote the headline rate without its composition. *Extractor improvement
   candidate:* classify the known harness shapes into an `environment` category — `SCHEMA_KEYS` +
   `references/extractor-output-schema.md` + tests move together per the schema doc's own rule.
2. **Bounded deep-dive of high-signal sub-agents.** CONSUME `aggregate.json`'s
   `subAgentDeepDiveCandidates` (schema v4): `selected[]` is the ≤6 deep-dive set (already
   ranked by error count desc, then bytes — do not re-rank by hand). Spawn one analyst
   sub-agent per pick **in parallel**, passing the **ABSOLUTE** `transcriptPath`. When you state
   the file size in the prompt, quote **`emittedBytes`** (the digest on disk), never `bytes` (the
   raw source, ~40× larger and only the rank key) — under the old bare-`bytes` label 4 of 6
   analysts in the 2026-08-01 run planned reads for a 400–700 KB file that was 10–13 KB, and each
   burned a turn correcting course. Log every
   `overCap[]` entry PLUS each session's `subAgents.errorAgentsNotEmitted` count as "scanned
   via taxonomy only" (no silent drop — those error-bearing agents have no emitted transcript
   at all). Use the Phase-3 analyst prompt plus: "This is a SUB-AGENT transcript — focus on
   errors it hit, any wrong/fabricated result it returned to its orchestrator, and internal
   thrash."
3. **If there are no sub-agents / none high-signal,** say so explicitly ("no sub-agent activity in
   window" / "sub-agents ran clean") — that is itself a reportable result, not a skipped step.

Sub-agents **fabricate precise-looking facts** their orchestrator must hand-verify — watch for that
specifically. Quotes from these transcripts are verified in Phase 5 against the emitted
`sessions/sub/<id>/*.md`, exactly like session quotes.

### Phase 4 — Analyze (behavioral first)

Synthesize across the aggregate JSON + the deep-dive returns. Build these, each with ≥2-occurrence
evidence (session id + redacted quote/metric):

#### 4a. Recurring-Mistake Taxonomy
Cluster `errorTaxonomy.byCategory` + deep-dive "recurring mistakes" across sessions. For each
recurring class: category, count, which sessions, a deduped redacted sample, and whether a
rule/learning already covers it. The highest-value finding is a mistake that **recurs across
multiple sessions** (e.g. `edit-stale-read` in N sessions → the agent isn't re-reading hot files).

**Effect join (the improvement metric):** for every taxonomy row already covered by a promoted
rule/skill/README bullet, date the promotion (changelog/`git log -S`) and report the row as
"covered since {date} — {N} occurrences AFTER {date}". Post-promotion occurrence count is the
ONLY honest measure of whether the promotion worked — promotions are counted as relocations at
drain time, never as improvements. A trap recurring post-promotion at similar volume = the prose
failed → the recommendation is an `Enforce-via:` escalation (lint/test/template/script at the
failure seam), not a re-worded rule. This is what turns "93 promoted" into "which of the 93
changed anything".

#### 4b. Thrash / Wasted Effort
From `behavior` (reReads ≥3×, repeatedCommands, buildTestLoops, staleReadEdits) + deep-dive thrash.
Quantify: e.g. "learnings.md re-read 7× in 2 sessions — agent loses its place in a large file."

#### 4c. Workflow Friction
`stats.skillsBlocked` (skills the agent tried to invoke but couldn't), repeated AskUserQuestion
themes, permission denials (`userRejected`). Blocked-skill friction often means a workflow expects a
skill the agent can't call directly.

**Also report permission ECONOMY, not just denials.** `userRejected` captures what the user
refused; it says nothing about what they had to *approve*, which is the larger and more annoying
tax. Cluster the window's Bash/PowerShell commands by leading token (`stats.allToolsUsed` gives
volume; the per-session transcripts give the commands), drop everything Claude Code already
auto-allows and everything already in `.claude/settings*.json`, and report the top read-only
patterns worth allow-listing — or hand the analysis to `fewer-permission-prompts`. Never propose
a wildcard on an interpreter, shell, or package runner (`python *`, `npx *`): that is arbitrary
code execution. **The 2026-08-01 run missed this entirely** — it measured 577 `cd`-prefixed calls
and correctly identified that the prefix *defeats prefix-anchored allow rules*, yet never asked
the adjacent question of which commands were being approved over and over. The user did.

#### 4d. Repetitive Questions
Cluster `askUserQuestions` across sessions. The same question asked in ≥2 sessions = a missing
default, config, or rule the agent should know without asking.

#### 4e. Uncaptured Feedback (corrections / preferences / redirections)
From deep-dive "corrections" + a **REQUIRED full-corpus sweep of user messages across ALL emitted
transcripts** — not only the deep-dived ones. Run
`python "${CLAUDE_SKILL_DIR}/scripts/sweep_user_corrections.py" <output-dir>`
(defaults to `.ai/tmp/retro`; writes `user_corrections_sweep.txt`; the marker regex and
machinery-block skip-list live in the script), then classify the hits BY HAND with this section's
false-positive filters. **The deep-dives do not substitute for this sweep**:
the 2026-08-07 run substituted its 8 deep-dives for the corpus scan, and the user then found four
≥2-occurrence correction patterns sitting in the 39 unscanned sessions (completion-review demands
×5, unintelligible operator questions ×5, missing problem-frequency justification ×2,
already-done-work recommendations). Categorize:
- **Corrections** — "wrong", "no,", "that's not right", "undo", "revert", "not what I asked".
- **Preferences** — "always", "never", "prefer", "instead of X do Y".
- **Redirections** — "actually", "wait", "let's try a different way".

**False-positive filters:** "no" in a compound ("no need for X") is a design decision, not a
correction; technical terms ("error handling") aren't feedback; questions are clarifications.
Calibration: a ~2-week / ~15-session period typically yields ~3–5 strong corrections and ~8–10
preferences. Significantly more → re-check for false positives.

#### 4f. Skill Effectiveness & Convention Coverage
- Which skills were invoked (`stats.skillsUsed` — since v4 this includes user-typed `/slash`
  runs, previously invisible; `stats.skillInvocationModes` breaks down user vs model per skill),
  how often; which exist but went unused; tasks done manually that a skill could have handled.
  Cross-check user-mode names against `ls .claude/skills/` — they may include built-in commands.
- **Diagnose every zero-invocation skill — do not just list it.** For each skill that exists,
  never fired in the window, AND whose job the window contains evidence of being done by hand,
  you MUST report a *cause*, not an inventory line. Check, in order: (a) does its **name** carry
  a qualifier that reads as "not for you" — a model name, a tool name, a role — and does
  `stats.models` show most sessions outside that qualifier? (b) do its description's trigger
  phrases match how the user actually phrased the work this window? (c) is it blocked, or
  buried under the listing budget (`PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit audit-skills` reports the fleet total)?
  **Worked example — this check exists because the 2026-08-01 run failed it.** That report wrote
  "`a87a6289` orchestrated 5 delegated sessions by hand while `agent-delegate` and
  `fable-orchestrate` went unused", filed it as a Notable aside, and concluded "P3: none — the
  deficit is enforcement, not coverage." The cause was one join away in its own data:
  `fable-orchestrate` was model-agnostic in content but model-named, and Fable was 36% of the
  window's model usage — so the name said "not for you" to 64% of sessions. The user found it,
  not the retrospective. An unused skill next to manual work is a FINDING with a cause, and
  "already covered by a skill" is not a conclusion until you have checked whether that skill can
  actually fire.
- For each feedback/mistake: already in `AGENTS.md`? → AI violated an existing rule (needs
  strengthening). In a skill? → skill may not be triggering. In the **auto-memory** (MEMORY.md)?
  → route by audience: a personal/user-specific preference is ALREADY correctly homed (do NOT
  promote it); a team-general rule captured only in memory is a promotion candidate — memory is
  per-machine, so team-relevant guidance must never live only there. Nowhere? → candidate
  rule/learning.

#### 4g. Hypothesis Evidence (report-only)
Read `.ai/improvement-hypotheses.md`: for each `PENDING` hypothesis whose Signal window
overlaps this retrospective period, note observed evidence FOR or AGAINST in the report
(session ids/metrics). Do NOT edit statuses — status changes belong to the
`hypothesis-validator` skill (normally invoked via learning-consolidator Phase 6.5); this
section is its evidence feed. If this period's data decisively settles a signal whose window
has elapsed, say so in the ending and offer to run `hypothesis-validator` now.

#### 4h. Prior-Report Reconciliation (REQUIRED when a prior report exists)
For EACH recommendation in the most recent prior report (every P1–P5 item), classify its
status NOW and produce the report's reconciliation table (finding → status now → check
performed):
- **applied** — cite the rule/skill/file that changed (grep/read it; don't trust memory);
- **superseded** — say by what;
- **still open** — carry it into THIS report's recommendations explicitly instead of
  re-deriving it (still-open P1/P2 items are the top candidates).
Calibration example: the 2026-06-22 report's "What Changed Since the 2026-06-21 Report"
table. Recommendations not applied in-session silently evaporate — this step is what makes
them a lifecycle instead of a wish list.

#### 4i. The Absence Sweep (REQUIRED — the dog that didn't bark)

Everything above this line is built from things that **happened**: errors raised, commands
repeated, files re-read, questions asked. The extractor cannot emit an event for a thing that
never occurred, so the pipeline is structurally blind to absence — and absence is where the
2026-08-01 run lost both of its biggest findings (a skill that never fired, and permission
prompts that never needed to happen). Neither was a hard inference; nothing asked the question.

Before writing the report, answer each explicitly. "Nothing found" is a valid answer; silence
is not:

| Ask | Where to look |
|---|---|
| Which skills never fired while their job was done by hand? | §4f diagnostic — report a *cause*, not a list |
| Which quality gate was never run in a window that shipped code? | `stats.allToolsUsed`, session titles |
| What did the user approve repeatedly that never needed approving? | §4c permission economy |
| Which recommendation from the last report produced no evidence either way? | §4h — that is INCONCLUSIVE, not "applied" |
| What did the user have to ask for that the pipeline should have offered? | Scan user messages for requests that duplicate an existing skill's job |

The last row is the highest-yield and the most uncomfortable: **when the user supplies a finding
the data already contained, that is a pipeline defect, and it belongs in the report as one.**
Both 2026-08-01 misses surfaced that way.

### Phase 5 — Adversarial Self-Check (before writing the report)

Sub-agent output is **untrusted**. Apply BOTH checks; drop anything that fails:

1. **Existence** — every quote you are about to put in the report must be grep-verifiable in the
   corresponding `.ai/tmp/retro/sessions/<id>.md` (for sub-agent quotes: the emitted
   `.ai/tmp/retro/sessions/sub/<id>/*.md`), and every finding must cite a session id present in
   `aggregate.json`. If you cannot locate a quote, drop the finding (a sub-agent may have paraphrased
   or hallucinated it).
2. **Causation / dates** — before claiming a mistake "recurred **despite** an existing rule or
   learning", verify that the rule/learning's **date predates** the occurrences. If the rule was
   added *after* (or between) the occurrences, it is NOT false causation — reframe as "now covered"
   rather than "the rule failed". Quote the rule's date.

3. **Dispatched == returned.** Reconcile every fan-out worker BEFORE writing; one returning after the report is written is dropped in silence. State `dispatched N == returned M + dropped K`.
4. **The report-completeness gate, mechanical, last thing before presenting.** Run `python "${CLAUDE_SKILL_DIR}/scripts/check_report.py" --report .ai/retrospectives/{date}-retrospective.md`:
   0 = complete, 1 = findings over `sections`/`workers`/`durability`, 2 = could-not-measure. **Never claim completion under anything but 0.** [references/report-gate.md](references/report-gate.md).

### Phase 6 — Generate Report

Use [references/report-template.md](references/report-template.md). Write to
`.ai/retrospectives/{YYYY-MM-DD}-retrospective.md` (create the dir if needed).

**The report must survive the session — `git add` it.** `.ai/retrospectives/` is NOT gitignored but
has never been committed: **zero retrospectives exist in any tracked tree**, so each run's baseline
is lost and the next run must reconstruct the prior P1–P5 set from `.ai/ai-changelog.md` (the
2026-08-01 run did exactly this). The 2026-07-31 hypothesis-validator pass already REFUTED the
proactive-run hypothesis partly on this evidence ("zero retrospectives ever committed").

**SETTLED 2026-08-07 (operator decision) — do not re-litigate this per run.** `.ai/retrospectives/`
is **gitignored**; the report is local scratch and is *expected* to be lost. Three runs offered to
stage and three reports went uncommitted, so the offer was removed rather than repeated a fourth
time. Consequences for this phase: do **not** `git add` the report, do **not** offer to, and do
**not** describe it as durable. Instead, put everything a later run must reconcile against into the
**`.ai/ai-changelog.md` entry**, which is now the sole reconciliation source of record — that entry,
not the report, is what Phase 4h reads next time. Do not treat the chat summary as a substitute
either: chat is not a reconciliation source.

**Report rules:**
- Behavioral findings lead; "what we worked on" is context, not a finding.
- Every finding: session id(s) + redacted quote/metric + ≥2 occurrences + whether already captured.
- Every recommendation is specific and actionable ("add rule to AGENTS.md: re-read hot files —
  e.g., frequently-edited prompt templates — immediately before editing" — not "improve editing").
- Prioritized: P1 convention gaps, P2 skill updates, P3 new skills, P4 learnings, P5 workflow.
- **Required section:** include "Sub-Agent Behavioral Findings" (Phase 3b) — the sub-agent error
  taxonomy + any deep-dive findings, or an explicit "sub-agents ran clean" if none. Never omit it.
- **Required section:** "Prior-Report Reconciliation" (Phase 4h) whenever a prior report exists —
  one row per prior recommendation with its status now + the check performed.
- **Required section:** "Pipeline Health" — the fixed small trend table (see the template): sessions
  analyzed, per-window error counts by category (main + sub-agent), learnings intake added/drained
  since the last window, hypotheses opened/validated. Data sources: `aggregate.json`, git history of
  the `.ai/` data files, and
  `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint learnings --list-entries` for intake counts. One markdown table — not a dashboard, and not a new JSON artifact.
  **Caveat the error counts** — inflated by gates whose known-GOOD state is a non-zero exit (`ruff`
  with findings, `grep` finding nothing); name it beside the number. And when crediting a rule for a
  behaviour change, count **"carried the rule and violated it anyway"** separately (a sub-agent whose
  prompt held the deny-`cd` rule verbatim still issued one) — it separates a reach failure (fix
  routing) from an adherence failure (build a seam).
- **Conditional section:** "Hypothesis Evidence" (4g) — include only when at least one PENDING
  hypothesis's window overlaps the period and the data actually speaks; no forced section.
- **Privacy:** the committed report contains ONLY synthesized findings + redacted snippets. NEVER
  paste raw transcript dumps or `transcriptPath` values. Before saving, gate the draft with the
  extractor's leak scanner (same code path as the artifact `--self-check`):
  `python "${CLAUDE_SKILL_DIR}/scripts/extract_sessions.py" --check-file <draft-path>` — exit 3
  means a secret shape leaked; redact and re-run until it passes.
- Be conservative — 5 high-confidence findings beat 20 speculative ones. 1 occurrence is not a
  pattern.

### Phase 7 — Present Summary & Apply the Default

```
## Session Retrospective: {date_range}
Sessions analyzed: {count}  (deep-dived: {n}, JSON-only: {m})
Sub-agents: {totalAgents} ({agentsWithErrors} with errors, {subDeepDived} deep-dived)

### Top Behavioral Findings
1. {recurring mistake / thrash / friction — with count}
2. …

### Recommended Actions
- [ ] {P1 action}
- [ ] …

Full report: .ai/retrospectives/{date}-retrospective.md
```

Then COMMIT to the default — do not end on an open ask-menu (the 06-22 retro flagged exactly
that behavior as friction; default approved 2026-07-02, D-3):

1. **Apply the P1/P2 recommendations in-session now.** They are visible, reviewable edits
   (AGENTS.md rules, skill updates); the momentum to land them is lost once the session ends.
   **Then route them through the same completion gates as feature work** — an `ai-changelog`
   entry, a companion improvement hypothesis, and a regression test for anything mechanical
   (hook/lint/script). Meta-work self-exempts: applying P1/P2 feels like *finishing the
   retrospective*, not *shipping an infrastructure change*, so the completion machinery that fires
   automatically for feature work never engages — the 2026-08-02 session's highest-impact changes
   (a hook + two always-loaded rules) shipped with no changelog entry, no hypothesis, and no test
   until an explicit end-of-session audit caught all three.
   **Writing the entry is not landing it** — an uncommitted append is one `git checkout` from invisibility; assert reachability with `check_report.py --check durability`.

2. **Auto-append the P4 items to `.ai/learnings.md`** following the `task-learnings` placement
   rules (non-destructive intake; feeds `/learning-consolidator`). Behavioral P4s take
   `Category: interaction` under `## Interaction & Workflow Friction` so the consolidator can
   cluster them instead of losing them among codebase pitfalls. **Dedup that section first** —
   `task-learnings` Step 0 measures each session at completion and may already hold the in-session
   form; yours is the CROSS-session claim (say how many sessions), so merge, don't near-duplicate.
3. **Surface the sibling cadence** (the inverse of this skill's Phase-0 guard): count intake
   entries (`PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint learnings
   --list-entries`) and read the newest `CONSOLIDATION` date in `.ai/ai-changelog.md`; if intake > 0
   and the last drain is ≥7 days old, state "intake has {N} entries, last drain {D} days ago →
   run `/learning-consolidator`".
4. **If 4g settled a window-elapsed signal,** offer to run `hypothesis-validator` now.
5. Only then offer discussion of findings and the P3/P5 items.

On autonomous (model-initiated) runs, steps 1–4 ARE the behavior — no ask-menu.

## Anti-Patterns to Avoid

1. **Substring error matching** — never re-introduce "content contains 'Error:' → error". Errors are
   classified by ORIGIN tool in the extractor; trust `errorTaxonomy`, not raw text scanning.
2. **Relative paths to sub-agents** — always pass the ABSOLUTE `transcriptPath`. A relative path
   fails because the sub-agent's cwd is not guaranteed.
3. **Trusting sub-agent quotes blindly** — verify existence (Phase 5) before quoting in the report.
4. **False causation** — don't claim a rule "failed" if it post-dates the mistakes (Phase 5).
5. **Reading raw `.jsonl`** — never (it is unredacted). Use the extractor; the readable forms are the
   per-session `sessions/<id>.md` AND the emitted sub-agent `sessions/sub/<id>/*.md`.
6. **Over-extraction** — "user asked X, AI did X" is not a finding. Only report actionable patterns.
7. **Single-occurrence "patterns"** — an event is not a pattern; require ≥2 occurrences.
8. **Stale findings** — check `.ai/learnings.md` / `AGENTS.md` before reporting something as new.

## Troubleshooting

- **No sessions for range:** check the session dir exists; timestamps are UTC — widen the range.
- **Self-check failed (exit 3):** a secret shape reached the output. Do not proceed; inspect the
  reported match and strengthen redaction in the extractor before re-running.
- **`uv run` fails syncing/building native deps:** expected — don't use `uv run` for this stdlib
  script. Call the venv/system python directly.
- **Output too large:** narrow the date range, or rely on the aggregate + fewer deep-dives.
- **A deep-dive sub-agent fails:** that session falls back to JSON-only; the run continues.
- **`transcriptsEmitted: 0` for a session:** it had no sub-agents, or none were high-signal (no
  errors and not among the largest). Rely on `subAgentErrorTaxonomy` + the JSON metrics; do NOT read
  raw `.jsonl` to compensate.
