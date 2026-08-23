---
name: analyze-logs
description: >
  Analyze application logs to find root causes and propose solutions. Works with structured JSON,
  container logs, plain text service logs, and event streams; GCP exports, Docker compose output,
  and realtime session events are worked examples rather than prerequisites. Includes parallel
  analysis for large files, session or request lifecycle reconstruction, codebase evidence checks,
  and a structured findings report with task files.
  Use when the user says "analyze logs", "check these logs", "what's wrong in the logs", "debug this",
  or provides a log file. Do NOT trigger for logging configuration, adding log statements, or
  log infrastructure changes.
argument-hint: "<log-file-path>"
metadata:
  type: task
---

# Analyze Logs — Root Cause Analysis from Application Logs

ultrathink

## When This Skill Activates

- User provides a structured JSON log file, container logs, service logs, or an event stream
- User asks to analyze logs, debug from logs, or find root causes
- User pastes log excerpts and asks what's wrong

## Ground Rules

1. **Read-only by default.** Never modify application code unless the user explicitly asks.
2. **Evidence-based.** Every root cause claim must reference specific code locations found via codebase search. If evidence is insufficient, say so and ask clarifying questions.
3. **Separate issues.** Logs often contain multiple unrelated problems. Investigate and report each one independently.
4. **Ask when unsure.** If a log entry is ambiguous, the context is unclear, or multiple root causes are plausible, ask the user rather than guess.
5. **No speculation without labeling.** If you form a hypothesis without hard evidence, explicitly mark it as `[HYPOTHESIS]` and explain what evidence would confirm or refute it.
6. **Never quote a raw `grep -c` as a frequency.** One job failure writes the same error string into several fields of each entry (`error_message`, `message`, `stack_trace`) *and* across more than one entry (the job-execution wrapper plus the feature-level handler). A `grep -c` returning 6 and an earlier review's "exactly 3 times" both traced to a **single** job — neither was an incident count, and both had already been quoted as frequency evidence in a task doc. Extract the correlating id first and count DISTINCT ids:

   ```bash
   grep -B4 -A12 "<error string>" <file> | grep -E '"(job_id|session_id)"' | sort -u
   ```

   State the ids next to the count so the next reader can tell an incident count from a hit count.
7. **Never collapse buckets a source document deliberately separated.** Merging two categories that
   an upstream doc kept apart inflated one finding **5×**. Before writing any aggregate, check
   whether the source defined its own buckets — if it did, report in those buckets and state
   explicitly when you are combining them and why.
8. **Census the identity key before normalizing.** One entity's identity can travel under more than
   one field name in the same corpus (a session appearing under two different key names), so a
   join on a single field silently drops or double-counts records. Enumerate the candidate identity
   fields across the whole corpus first, then pick the resolution order and say what it is.

## Analysis Pipeline

### Step 0: Load Known Issues

Before analyzing logs, read `.ai/learnings.md` to load accumulated project knowledge.
Known bug patterns, past root causes, and architectural pitfalls recorded there can
shortcut investigation and avoid re-discovering known issues.

### Step 1: Ingest and Detect Format

Read the log file: `$ARGUMENTS`

If `$ARGUMENTS` is empty or missing, ask the user for the file path.

**Auto-detect the log format** by examining the first few lines:

| Format | Detection Signal | Parser |
|--------|-----------------|--------|
| **Structured JSON logs** | Array/NDJSON objects with timestamp/severity/message fields | Infer field names first; for GCP exports, use [references/gcp-log-fields.md](references/gcp-log-fields.md) and [references/gcp-query-templates.md](references/gcp-query-templates.md) as examples |
| **Container logs** | Lines prefixed with a container/service name, often around a `|` separator | Split by service/container first; Docker compose examples live in [references/docker-log-format.md](references/docker-log-format.md) |
| **Plain application logs** | Text lines with level/module/message, web-server access lines, or framework output | Parse timestamp, level, component, and message; infer missing fields from nearby lines |
| **Event streams** | Repeated event names or lifecycle fields (`event_type`, `type`, `session_id`, request IDs) | Group by the strongest session/request identity key before timing analysis |

**Event-stream and session logs:** If entries carry lifecycle event names such as
`session_started`, `request_started`, `speech_started`, `turn_started`, or `response_created`, load
[references/session-event-streams.md](references/session-event-streams.md) for the vocabulary
census, timing analysis, and lifecycle-reconstruction method. Its worked example is a realtime voice
session; substitute the event names your own system emits — the method does not change.

**Actions:**
1. Read the file using the Read tool. For large files (>2000 lines), read the first 100 lines to detect format, then proceed with chunked reading.
2. Identify the time range covered by the logs (earliest → latest timestamp).
3. Count total entries and break down by severity level.
4. Report the overview to the user before diving in:
   ```
   Log file: {filename}
   Format: {structured JSON | container logs | plain application logs | event stream | mixed}
   Time range: {start} — {end} ({duration})
   Total entries: {count}
   Breakdown: {N} ERROR, {N} WARNING, {N} INFO, ...
   ```

### Step 1a: Map Platform Fields to Roles

Log platforms disagree about field *names*, not about what the fields *mean*. Write the mapping
down once, before analysing; everything downstream refers to the ROLE, never to one platform's
spelling of it.

| Role | What the analysis needs it for | GCP export | Container output | Yours |
|------|-------------------------------|-----------|------------------|-------|
| Timestamp | Timeline reconstruction, gap measurement | `timestamp` | leading `YYYY-MM-DD HH:MM:SS.mmm` | |
| Severity | Triage and priority ordering | `severity` | inferred from an `ERROR:` / `WARNING:` prefix | |
| Message | Error text, signature matching | `jsonPayload.message` or `textPayload` | everything after the service prefix | |
| Service identity | Grouping issues by emitter | `resource.labels.service_name` | the container-name prefix | |
| Correlation id | Tying one request or session together | `trace`, `spanId` | `request_id=` inside the message text | |
| Latency | Slow-path detection | `httpRequest.latency` | access-log duration, when present | |
| Event name | Lifecycle and event-stream analysis | `jsonPayload.event_type` | an app-defined key in the message | |

Fill the **Yours** column from the first 100 lines of the actual file, and **state which roles are
absent** rather than assuming a default. A missing correlation id changes the grouping strategy in
Step 2; a missing severity field means severity has to be inferred from message text; a missing
event name rules out Step 1c entirely.

The files under `references/` are **worked examples of two platforms, not the supported set.**
CloudWatch, Loki, ELK, Datadog, journald, or a plain text file all work the same way: fill in the
table above and the rest of the pipeline is unchanged.

### Step 1b: Parallel Deep Analysis (Large Files)

For log files with >500 entries or spanning >1 hour, launch **3 parallel Agent subprocesses** to maximize coverage and speed:

| Agent | Focus | What to Extract |
|-------|-------|-----------------|
| **Errors & Warnings** | All ERROR/WARNING entries, exceptions, tracebacks | Categorized issue list with counts, timestamps, stack traces |
| **Lifecycle** | Request/session start/end, connection lifecycle, cleanup | Per-identity timeline, anomalies, incomplete flows |
| **Behavioral Patterns** | Timing analysis, event ordering, cross-session/request patterns | Interruptions, false starts, timing gaps, race candidates |

Each agent reads the **entire** file in chunks and returns structured findings. After all agents complete, merge their findings into the unified issue list (Step 2).

**When to use agents vs. direct analysis:**
- <500 entries, single session: analyze directly (no agents needed)
- 500-2000 entries, 2-5 sessions/requests: launch 2 agents (errors + lifecycle)
- 2000+ entries or user reports a specific behavioral issue: launch all 3 agents

### Step 1c: Session Reconstruction

If the logs contain lifecycle or event streams (see [references/session-event-streams.md](references/session-event-streams.md) for the method and one worked example):

1. **Identify distinct sessions** by grouping on `trace` ID or `session_id` / feature-scoped ID fields
2. **Build a timeline** for each session: setup → active conversation → teardown → post-session processing → cleanup
3. **Flag anomalies**: missing phases, >60s gaps between expected events, premature termination
4. **Present session summary table** before diving into issues:
   ```
   | # | Session ID | User | Duration | Turns | Status | Anomalies |
   ```

### Step 2: Identify Distinct Issues

Group log entries into distinct issues. An "issue" is a unique problem, not a unique log line.

**Grouping strategy:**
1. **By error signature** — same exception class + message pattern (ignore variable parts like IDs, timestamps).
2. **By trace/span/request flow** - correlate via trace IDs, request IDs, session-scoped IDs, or temporal proximity within the same service/container.
3. **By temporal proximity** — errors within 1-2 seconds of each other from the same service are likely related.
4. **By causal chain** — an upstream error causing downstream errors is ONE issue, not multiple.

**Deduplication rules:**
- Same exception thrown N times = 1 issue with "occurred N times" note.
- A warning followed by an error in the same trace/request = 1 issue (the error, with warning as context).
- Different exceptions from the same root cause = 1 issue.

**Output a numbered issue list** before investigating:
```
Found {N} distinct issues:
1. [ERROR] {short description} — {count} occurrences
2. [WARNING] {short description} — {count} occurrences
...
```

### Step 3: Investigate Each Issue

For EACH issue, follow this investigation sequence:

#### 3a. Extract Context
- Full error message and exception type
- Stack trace (if present — in whichever field carries message text: `textPayload` or
  `jsonPayload.message` in a GCP export, inline in the line itself in container output)
- Request context: HTTP method, path, user ID, session ID
- Preceding log entries in the same trace/request (the "story" leading to the error)

#### 3b. Locate Code
- Extract file paths and line numbers from stack traces.
- Use Grep/Glob to find the relevant source files in the codebase.
- If no stack trace: search for the error message string, exception class name, or the endpoint path in the code.
- Read the relevant code sections to understand the execution flow.

#### 3c. Determine Root Cause
- Trace the code path from the entry point (route handler → service → storage/external call).
- Identify WHERE the error originates vs. where it surfaces (they're often different).
- Cross-reference with `.ai/learnings.md` — if this pattern was seen before, note it.
- Check for known patterns:
  - Missing null/None checks
  - Race conditions in async code
  - External service failures (e.g., AI provider, cloud storage, internal APIs)
  - Database constraint violations
  - Configuration issues (missing env vars, wrong settings)
  - Session/state management bugs (especially in WebSocket flows)
  - Middleware exception handling gaps
  - Container or orchestrator startup/shutdown issues (dependency ordering, health-check
    failures, restart loops)

#### 3d. Timing Analysis (Event Streams)

If the issue involves an event stream — a request lifecycle, a session, a state machine, a
streaming connection — perform the timing analysis described in
[references/session-event-streams.md](references/session-event-streams.md):

1. **Measure the gap between each adjacent event pair**, not just the total duration
2. **Build an event sequence table** showing timestamps in milliseconds with per-step deltas
3. **Compare each gap against its normal range** — derive the range from healthy instances in the
   same file when no documented baseline exists
4. **Flag near-zero gaps** (sub-10ms between events that should be causally ordered) as evidence of
   concurrency rather than sequence: a race, a duplicate handler, or a threshold that never fired
5. **Cross-check magnitudes that ought to agree** — a payload far smaller than the duration that
   produced it means something was truncated or fragmented upstream

Present timing evidence as a table:
```
| Time | Event | Key Detail | Delta from Previous |
```

#### 3e. Assess Impact
- **Frequency**: one-off vs. recurring (check occurrence count)
- **User-facing**: does this break the user experience or is it internal?
- **Data impact**: could this cause data loss or corruption?
- **Blast radius**: one user, one feature, or system-wide?

#### 3f. Propose Solution
- Describe the fix conceptually (what needs to change, not the code diff).
- Reference the specific file(s) and function(s) that need modification.
- If multiple approaches exist, list pros/cons briefly.
- Flag if the fix requires a migration, config change, or external service update.

### Step 4: Compile Findings Report

Present findings in this format:

```markdown
# Log Analysis Report

**File:** {filename}
**Format:** {structured JSON | container logs | plain application logs | event stream | mixed}
**Time range:** {start} — {end}
**Analyzed:** {date}

## Overview
{summary paragraph — how many issues found, overall health assessment}

---

## Issue 1: {Title}

**Severity:** CRITICAL | HIGH | MEDIUM | LOW
**Occurrences:** {count}
**Affected component:** {feature/service name}

### Symptoms
{What the logs show — error messages, HTTP status codes, timing}

### Root Cause
{Evidence-based explanation with code references}

### Evidence
- `{file_path}:{line}` — {what this code does wrong}
- Log entry: `{relevant log excerpt}`

### Proposed Fix
{Conceptual solution — what to change and why}

### Task File
Created: `tasks/{PREFIX}-{slug}.md`

---

## Issue 2: {Title}
...
```

**Severity classification:**
- **CRITICAL** — data loss, security issue, or complete feature breakage
- **HIGH** — feature partially broken, user-facing errors, recurring failures
- **MEDIUM** — degraded experience, intermittent errors, non-critical warnings
- **LOW** — cosmetic issues, noisy logs, minor inefficiencies

### Step 4b: Challenge Review (Mandatory)

**Before presenting the findings report to the user**, run a self-review challenge pass inspired by
the `plan-critic` skill. This step catches assumption errors,
contradictory guidance, and missed issues.

For each reported issue, challenge:

1. **Evidence grounding**: Is the root cause verified against current code, or assumed from stack traces alone?
   Files may have changed since the log was produced.
2. **Fix correctness**: Does the proposed fix contradict any convention in AGENTS.md or `.ai/learnings.md`?
   Cross-check fix patterns against both sources — they can conflict.
3. **Issue grouping**: Are any "separate" issues actually symptoms of the same root cause? Would fixing
   one resolve another?
4. **Completeness**: Are there log patterns (zombie sessions, resource leaks, timing anomalies) that
   were noted but not tracked as issues? If they have MEDIUM+ severity, they need a task file.
5. **Hypothesis labeling**: Is every unverified claim marked `[HYPOTHESIS]`? Are there claims presented
   as facts that lack code-level evidence?

**Actions:**
- Fix any issues found (update report text, correct proposed fixes, add missing task files).
- Note significant changes made during the challenge pass in the report footer.
- If the challenge reveals a contradiction in project conventions (e.g., AGENTS.md vs learnings.md),
  flag it as a separate finding for the user.

### Step 5: Create Task Files

For each issue with severity MEDIUM or above, create a task file in `tasks/`.

**Prefix rules** (from project conventions):
- `BUG-` — confirmed bugs with clear reproduction path
- `PROD-` — production/runtime issues (performance, resource leaks, flaky behavior)
- `TECH-` — design issues that need refactoring
- `FEATURE-` — missing functionality that caused the error

See [references/task-file-template.md](references/task-file-template.md) for the template.

For LOW severity issues, mention them in the report but skip task file creation unless the user asks.

### Step 6: Ask About Unknowns

After presenting the report, if any issues were marked `[HYPOTHESIS]` or had insufficient evidence:
1. List the open questions explicitly.
2. Suggest what additional information would help (more logs, specific time ranges, reproduction steps).
3. Offer to investigate further if the user can provide more context.

## Handling Edge Cases

- **Massive log files (>5000 lines):** Read in chunks. Start with ERROR/CRITICAL entries, then pull surrounding context by trace ID or timestamp. Don't try to read the entire file at once.
- **No errors found:** Report this clearly. Look for WARNING-level patterns that might indicate brewing problems. Check for unusual latency patterns in whichever field carries request duration (`httpRequest.latency` in a GCP export, access-log durations in container output).
- **Logs from multiple services:** Group issues by the service-identity role from Step 1a (`resource.labels.service_name` in a GCP export, the container-name prefix in container output). Note cross-service issues when correlation ids span services.
- **Truncated stack traces:** Search for the exception class in the codebase and trace likely code paths manually.
- **Repeated known issues:** If an issue matches a known pattern from `.ai/learnings.md`, reference the existing learning and check if the previous fix was applied.
- **Mixed log formats:** If a file contains both structured JSON and plain text (e.g., container startup messages before the app initializes structured logging), parse each section with the appropriate format.
- **Multi-service log dumps:** When one file interleaves several emitters (for example `docker compose logs` across all containers), split by the service-identity field before analysis. Issues in different services are separate unless causally linked.

## Analysis Quality — Good vs. Bad Examples

See [references/analysis-examples.md](references/analysis-examples.md) for calibration examples showing:
- Evidence-based root cause vs. surface-level description
- Proper hypothesis labeling vs. unfounded speculation
- Correct issue grouping vs. over-splitting

## What NOT to Do

- Do NOT modify source code unless explicitly asked.
- Do NOT create PRs, commits, or branches.
- Do NOT dismiss warnings without investigation — they often precede errors.
- Do NOT assume correlation is causation — verify causal chains in code.
- Do NOT group unrelated errors just because they happen close in time.
- Do NOT skip codebase verification — "I think the code does X" is not evidence.

## Querying the Log Platform Directly

When the user needs to search the platform rather than a downloaded file, the method is the same on
every backend:

1. **Start with the narrowest service/resource filter** the platform offers
2. **Add explicit time bounds** — an unbounded scan is slow, and on a hosted platform it is billable
3. **Search the field that matches the target**: the structured payload for application fields, the
   raw-text field for startup output and uncaught exceptions
4. **Validate the query against a downloaded sample first** when one exists, so that a zero-result
   query can be told apart from a wrong-field query

[references/gcp-query-templates.md](references/gcp-query-templates.md) works this through in GCP
Cloud Logging's query dialect — a worked example to translate, not the required backend.
