---
name: hypothesis-validator
user-invocable: false
description: >
  Validate PENDING improvement hypotheses in .ai/improvement-hypotheses.md against observed
  evidence and propose status changes (CONFIRMED | REFUTED | INCONCLUSIVE | SUPERSEDED) —
  the validation step the ai-improvement-tracker reserves status edits for. Also owns the
  ledger lifecycle: rotates terminal entries to .ai/improvement-hypotheses-archive.md,
  marks event-starved windows DORMANT, and runs the meta-synthesis when the lint's
  synthesis-due NOTE fires (~every 10 verdicts). Invoked from learning-consolidator
  Phase 6.5 (~weekly, approval-gated) and offered by session-retrospective when its data
  settles a signal. Use when the user says "validate hypotheses", "check pending
  hypotheses", or "close the hypothesis loop".
metadata:
  type: task
---

# Hypothesis Validator — Close the Hypothesis→Validation Loop

## Role

You are the single owner of hypothesis **Status** changes in `.ai/improvement-hypotheses.md`.
Every other skill (including the tracker that writes hypotheses) is forbidden from editing
statuses; the retrospective only feeds you evidence (§4g "Hypothesis Evidence", report-only).
One owner, multiple callers — the ai-changelog / ai-improvement-tracker precedent.

## When This Skill Activates

- `learning-consolidator` Phase 6.5 invokes it on the ~weekly consolidation run
- `session-retrospective` offers it at its ending when §4g evidence settles a signal mid-window
- The user asks directly ("validate hypotheses", "close the hypothesis loop")

## Process

### Step 1: Enumerate candidates

Read `.ai/improvement-hypotheses.md` in full (the HOT file only — the archive,
`.ai/improvement-hypotheses-archive.md`, is read during Meta-Synthesis, never during a
normal pass). Candidates = every entry with `Status: PENDING`, except entries whose latest
`Validation notes:` carry a `DORMANT until <event>` mark — skip those unless this pass has
evidence the named event has since occurred. For each candidate, extract: Category, Signal,
Changelog ref date, any existing `Validation notes:`.

### Step 2: Window check (hard guardrail)

Determine each hypothesis's **signal window** from its own Signal text (typical: "next 2-4
weeks", "next 2 runs"); date it from the **Changelog ref date**. Then:

- **Window not yet elapsed** → NO status change, even if evidence looks decisive. Record
  interim evidence as a dated `Validation notes:` sub-field (Status stays `PENDING`).
- **Window elapsed** → proceed to Step 3.
- A signal counted in runs/events (e.g. "the next 2 consolidator runs") elapses when that
  many qualifying events occurred, regardless of calendar time.
- **Event-dormancy:** if an event-keyed window's qualifying event has not occurred within
  **8 weeks** of the Changelog ref (or since the last qualifying event), add a dated
  `- **Validation notes ({today}):** DORMANT until <the named event> — none since
  {last-event date}` line and skip the entry in subsequent passes. Dormancy is a scheduling mark, not
  a verdict: Status stays PENDING, and any session that observes the event removes the
  mark (or simply evaluates) at the next pass. Never resolve an entry INCONCLUSIVE merely
  because its event has not happened.

Never retro-fit a window: if the Signal names none, use 4 weeks from the Changelog ref.

### Step 3: Gather evidence per elapsed hypothesis

Evaluate the Signal — as written, no reinterpretation (the tracker's hindsight rules apply) —
against:

- The latest `.ai/retrospectives/*.md` report(s): its "Hypothesis Evidence" (§4g) section and
  pipeline-health table when present, plus the recurring-mistake taxonomy for "fewer X
  occurrences" signals
- `.ai/learnings.md` intake (did the predicted entries stop/continue appearing?)
- `.ai/ai-changelog.md` history (was the artifact since replaced? → SUPERSEDED candidate)
- Where the signal is a fleet property: a fresh
  `python -m lemmi_ai_kit audit-skills` run (if available)
- Session evidence the caller supplies (the consolidator's current-run analysis)

**Record disconfirming evidence with equal weight — never confirm by default.** If you find
yourself searching only for supporting instances, stop and search for counter-instances.

### Step 4: Propose verdicts (closed vocabulary)

| Verdict | When |
|---------|------|
| `CONFIRMED` | The Signal's predicted observation occurred; no material counter-evidence |
| `REFUTED` | The predicted observation did not occur, or the named refutation condition did |
| `INCONCLUSIVE` | Window elapsed but evidence is ambiguous/absent (say what WOULD settle it) |
| `SUPERSEDED` | The changed artifact was since replaced/removed — the prediction is moot |

Partial-but-promising evidence on an elapsed window is `INCONCLUSIVE` with a
`Validation notes:` line — not a soft "supported" status; those out-of-vocabulary statuses
are exactly the drift this skill exists to prevent.

### Step 5: Approval gate (mandatory)

Present the proposal as a table — hypothesis title, current window state, evidence summary
(for AND against), proposed verdict — and **wait for user approval before editing anything**.
When invoked from `learning-consolidator`, fold the proposals into the consolidation plan's
existing approval gate instead of a second prompt.

### Step 6: Execute approved changes

For each approved verdict:

1. Update the entry's `- **Status:**` line to the exact verdict word.
2. Append directly under it: `- **Resolution ({YYYY-MM-DD}):** {1-3 line evidence summary,
   citing the retro/changelog/data source}`.
3. For interim (non-flip) evidence: add/extend the dated `- **Validation notes:**` sub-field
   above Status; Status stays `PENDING`.

**REFUTED requires a follow-up action** — a refuted hypothesis means the infrastructure
change did not deliver; the loop is only closed when one of these is recorded:
- Adjust or revert the underlying rule/skill change (do it, or open a `tasks/` doc for it),
  and note the action in the Resolution line; or
- Record in the Resolution line WHY the change stays despite the refuted prediction
  (e.g. value shifted, prediction was too aggressive).

### Step 7: Archive rotation (every pass)

Rotate the ledger so the hot file holds only the live backlog: MOVE — verbatim, never
rewritten — every entry whose Status is terminal (CONFIRMED | REFUTED | INCONCLUSIVE |
SUPERSEDED) AND whose Resolution predates the current pass to
`.ai/improvement-hypotheses-archive.md`, under its original date heading (create headings
as needed; keep both files reverse-chronological). Entries resolved AT the current pass
STAY in the hot file until the next pass — session-retrospective §4g reconciles against
them. Delete date headings the move leaves empty. PENDING entries never move. Report the
rotation ("rotated N, kept M hot") in the pass summary — a pass that proposes verdicts but
skips rotation is incomplete.

### Step 8: Verify

Run the data-file lint:

```
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint hypotheses
```

Zero findings required (statuses must be exactly in-vocabulary; heading structure intact).
The lint may also print `NOTE: meta-synthesis due` — a NOTE is not a finding; it schedules
the Meta-Synthesis below (run it this pass or explicitly carry it to the next).

## Meta-Synthesis (~every 10 terminal verdicts)

Individual verdicts close single loops; the synthesis is where they compound into design
rules for future changes. Trigger: `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint hypotheses` prints
`NOTE: meta-synthesis due` — computed by comparing the terminal-verdict count (hot +
archive) against the hot-file header's `**Last meta-synthesis:**` marker, so it fires for
whoever runs the lint, with no memory required.

1. Read every terminal entry (hot + archive) resolved since the last synthesis.
2. Cluster by MECHANISM (prose rule / mechanical check / skill / doc-home / permission),
   not by Category — 7 categories over ~10 verdicts is too thin per cell to signal.
3. Ask three questions: what do the REFUTED share? what made the INCONCLUSIVE undecidable
   (missing instrument? conjunctive signal? event never occurred)? which CONFIRMED were
   satisfied by the system's own operation (cheap confirms that measure nothing)?
4. Promote the lessons through normal channels behind the same approval gate as verdicts —
   tracker signal-design rules, consolidator routing guidance, AGENTS.md.
5. Update the header marker (`**Last meta-synthesis:** {date} — {N} terminal verdicts
   covered`) and record the findings in the run's changelog entry.

Calibration — run #1 (2026-08-02, n=22: 13 CONFIRMED / 3 REFUTED / 6 INCONCLUSIVE): all
3 REFUTED shared one mechanism — the change relied on a session *electing to act*
(a permission, a prose cadence guard); 4 of 6 INCONCLUSIVE were undecidable because the
signal named a measuring instrument that did not exist at write time (uncommitted
retrospectives) or stacked ≥3 conjunctive clauses; the cleanest CONFIRMED were
precise-trigger rules and mechanical checkers. Lessons landed as the tracker's
signal-design rules.

## Guardrails

- NEVER change a Status without user approval (Step 5 gate)
- NEVER validate a hypothesis younger than its own window (Step 2)
- NEVER invent statuses outside `CONFIRMED | REFUTED | INCONCLUSIVE | SUPERSEDED`
- NEVER rewrite a hypothesis's prediction to fit the observed outcome (hindsight bias);
  evidence goes in Resolution/Validation notes, the original text stays
- NEVER delete PENDING entries — they are the validation backlog; rotation (Step 7) MOVES
  only terminal entries, verbatim, and archived entries are never edited or re-armed
- DORMANT is a Validation-notes mark, not a status — never resolve an entry INCONCLUSIVE
  merely because its qualifying event has not occurred
- INCONCLUSIVE is terminal for that window — do NOT silently re-arm the same entry. If the
  signal deserves another observation window, say so in the Resolution line and record a
  fresh follow-up hypothesis via `ai-improvement-tracker` (new entry, new window)

## Calibration

**Good resolution (in-vocabulary, evidence-cited, dated):**

```markdown
- **Status:** CONFIRMED
- **Resolution (2026-07-15):** 2026-07-14 retro §4g: 0 edit-stale-read occurrences across
  12 sessions in the window (was 20 across 4 sessions pre-rule); no counter-evidence found.
```

**Bad (the historical anti-pattern this skill exists to prevent):**

```markdown
- **Status:** ✅ SUPPORTED (1 run) — looks promising...
```

Why bad: invented status outside the closed vocabulary, no approval gate, partial evidence
overwriting the lifecycle field. Correct form: Status stays `PENDING`, the evidence goes in
`- **Validation notes:** (2026-06-24) 1 supporting run — …`.

## Integration Points

| Caller | When | What the caller provides |
|--------|------|--------------------------|
| `learning-consolidator` | Phase 6.5, ~weekly | Current-run learnings analysis; folds proposals into its plan approval gate |
| `session-retrospective` | Ending, when §4g settles a signal | The retro report's evidence (§4g + health table); offers the run to the user |
| User direct | On request | — |
