# Session and Event-Stream Analysis

## What this file is, and why it is here

This is the **event-stream branch** of log analysis: logs where the unit of investigation is a
*lifecycle* — a request, a session, a state machine, a streaming connection — rather than an
isolated error line. Errors in this class are usually invisible line-by-line and only appear as an
**ordering** or **gap** anomaly across several entries. The method below is platform-neutral and
provider-neutral.

The worked example throughout is a **realtime voice session** (speech detection, conversational
turns, streamed model responses), because that shape exercises every part of the method: named
lifecycle events, hard timing expectations, and failures visible only in the sequence. Event names
such as `speech_started` are **that example's vocabulary, not a required schema.** Substitute the
names your own system emits; nothing in the method changes.

**Provenance — read this before extending the file.** This content arrived with a provider-specific
realtime skill that was deliberately dropped from the pack. The lifecycle-analysis *method* was kept
and generalized, because it is genuinely part of log analysis and two steps of this skill depend on
it (SKILL.md Step 1c and Step 3d). What was removed: one provider's API surface, and the originating
codebase's internal table, column, and helper names. Knowledge only its author can use does not
belong in a shared pack — that is the same test the dropped skill failed. Keep new material on the
generic side of that line.

## 1. Census the event vocabulary before analysing

Do not start from an assumed event list. Read enough of the file to enumerate what is actually
emitted, then write the table yourself:

| Column | What goes in it |
|--------|-----------------|
| Event name | The literal value in the event-name field (see SKILL.md Step 1a) |
| Meaning | What the system was doing — infer from surrounding entries, confirm in code |
| Key fields | The payload fields that carry the analysis signal for this event |
| Severity | Where it normally sits, so an off-normal severity stands out |

Two rules that come out of real misreadings:

- **A count of event names is not a count of events.** The same logical step often emits under more
  than one name across versions or code paths. Group by meaning, not by string.
- **Enumerate identity fields across the whole file first.** One entity's identity can travel under
  more than one field name in the same corpus, so a join on a single field silently drops or
  double-counts. This is SKILL.md Ground Rule 8, and event streams are where it bites hardest.

### Worked example — a realtime voice session's vocabulary

Session and connection lifecycle:

| Event name | Meaning | Key fields |
|------------|---------|------------|
| `session_started` | Session established with the speech provider | `session_id`, `model` |
| `session_configured` | Session parameters sent upstream | `turn_detection_type`, `silence_duration_ms` |
| `session_ended` | Session closed, normally or on error | `reason`, `duration_seconds` |
| `connection_established` | Client transport (WebSocket) connected | `session_id`, `user_id` |
| `connection_closed` | Client transport disconnected | `reason`, `duration_seconds` |
| `connection_quality_failed` | Health check failed | `quality`, `error_count`, `rtt_ms` |
| `ping_failed` | Single health-check failure | `error` |
| `ping_failure_cascade` | Consecutive failures forced a disconnect | `consecutive_failures` |

Conversation flow:

| Event name | Meaning | Key fields |
|------------|---------|------------|
| `speech_started` | Voice-activity detection saw speech begin | `has_active_response` (decisive for interruption analysis) |
| `speech_stopped` | Voice-activity detection saw speech end | `speech_duration_ms` |
| `turn_started` | A conversational turn began | `role`, `turn_number` |
| `turn_completed` | A turn ended | `role`, `turn_number`, `duration_seconds`, `text_length` |
| `response_created` | Model response generation started | `response_id` |
| `response_completed` | Model response generation finished | `response_id`, `response_length` |
| `barge_in_truncate_decision` | Provider-side barge-in: the user spoke over the response (WARNING) | — |
| `user_transcript` | User speech transcribed | `text`, `text_length` |

Audio streaming:

| Event name | Meaning | Key fields |
|------------|---------|------------|
| `audio_stream_started` / `audio_stream_ended` | Streaming boundaries | — |
| `audio_storage_complete` | Media persisted | `user_bytes`, `assistant_bytes` |
| `transcript_save` | Transcripts persisted | `count` |

Feature-level events sit **on top of** the transport vocabulary and are always project-specific.
Expect a start/complete pair per feature phase, and a separate pipeline vocabulary for whatever runs
after the session ends:

| Shape | Typical events | Key fields |
|-------|----------------|------------|
| Feature session | `<feature>_started`, `<feature>_completed` | feature id, user id, duration, completion percentage |
| Post-session pipeline | `<phase>_started`, `<phase>_completed`, `<phase>_error` | phase inputs and outputs, duration, error detail |
| Terminal result | `<result>_calculated`, `<result>_persisted` | the computed value |

## 2. Reconstruct the timeline

1. **Group by correlation id** — every entry sharing a trace or session id belongs to one lifecycle
2. **Order by timestamp**, and note where sub-millisecond resolution is missing, because that limits
   what step 3 can conclude
3. **Map the phases** — most lifecycles fit setup → active → teardown → post-processing → cleanup
4. **Flag structural gaps**: a phase entirely absent, or a gap far longer than the phase's normal
   duration, is an anomaly before any timing arithmetic

### Worked example — phase map for the voice session

- **Setup**: `connection_established` → `session_started` → first `turn_started`
- **Active**: repetitions of the turn chain below
- **Teardown**: `audio_stream_ended` → `transcript_save` → the feature's completion event
- **Post-session**: the pipeline's own `*_started` / `*_completed` pair
- **Cleanup**: `connection_closed`, or `ping_failure_cascade` if the connection went stale

**Write the healthy chain down before comparing anything to it.** One turn of the active phase runs:

```
speech_started → speech_stopped → user_transcript → turn_started(assistant) → response_created → response_completed → turn_completed(assistant)
```

Two readings of that chain do most of the diagnostic work, and both generalize to any
detector-gated lifecycle:

- **Normal**: `speech_stopped` occurs, and only after the configured silence window does
  `turn_started(assistant)` follow.
- **Interruption**: `response_created` is immediately followed by `speech_started` carrying
  `has_active_response=true` — the responder began while the user was still going.

An observed timeline is analysed by diffing it against this chain: a missing link, a reordered
pair, or a repeated element each point somewhere different.

## 3. Measure the gap between each adjacent pair

Build a table of event pairs, the observed gap, and the range you expect. **If no documented
baseline exists, derive one from the healthy lifecycles in the same file** and say that is what you
did — a threshold invented at analysis time and reported as a standard is a fabricated finding.

| Gap | Where the expectation comes from |
|-----|----------------------------------|
| Configured delay → the event it gates | The configured value itself: the gap should exceed it |
| Machine event → human reaction | Human reaction floors (>500 ms); anything shorter was not a reaction |
| Work start → work end | The normal duration range for that work; far below it means truncation |
| Repeat of the same event | Whether a retry, a duplicate handler, or a real second occurrence |

### Worked example — the four gaps that matter in a voice session

| Gap | Normal range | Anomaly signal |
|-----|-------------|----------------|
| `speech_stopped` → `response_created` | above `silence_duration_ms` (often 3000 ms) | Significantly shorter: the detector config in effect is not the one in code |
| `response_created` → `speech_started` | above 500 ms (human reaction) | **Below 100 ms: the user never stopped — a false end-of-turn** |
| `turn_started` → `turn_completed` (assistant) | 2–30 s | Below 1 s: the response was truncated |
| `speech_stopped` → next `speech_started` | varies | Inside `silence_duration_ms`: the user was pausing mid-thought, not finishing |

## 4. Read near-zero gaps as concurrency, not sequence

A **sub-10 ms gap between two events that should be causally ordered** is the single most useful
signal in this class of analysis. Two entries that close together were not cause and effect; they
were concurrent. That points at a race, a duplicate handler, or a threshold that never fired.

The generic corroborating patterns:

- **Two magnitudes that should agree, disagreeing** — a payload far smaller than the duration that
  produced it means the input was split or truncated upstream
- **A work unit far shorter than its normal range**, immediately followed by fresh input — the work
  was cut off, not completed
- **Consecutive same-role units with thin payloads** — one logical unit fragmented into several
- **A provider- or framework-emitted warning** in the same window naming the collision directly

### Worked example — false end-of-turn detection

- Sub-10 ms between `response_created` and `speech_started` = the user never stopped speaking
- A transcript under 20 characters from a speech duration over 5 s = the utterance was split
- `barge_in_truncate_decision` shortly after `response_created` = the provider saw the collision too
- An assistant turn under 1 s followed by long user speech = the response was cut off immediately
- Consecutive user turns with short transcripts = one utterance fragmented by the detector

## 5. Verify the configuration that was actually applied

Look for the event that records what the system *sent*, not what the code *contains*. If no such
event exists, that absence is itself a finding: report it as an **observability gap**, because
without it no claim about the running configuration can be evidence-based.

## 6. Compare across lifecycles in the same file

A single anomalous session proves little; the same anomaly across sessions localizes the cause.

- Does it cluster on one user or client? — input or environment
- Does it cluster at a position in the lifecycle (turn 6, retry 2)? — accumulation, not the trigger
- Does it cluster on one configuration value? — the setting is wrong for that workload
- Does it cluster in time regardless of user? — a deploy or an upstream provider incident

## 7. Field traps — names that lie

Before quoting any field as evidence, confirm what it actually counts. Field names in event streams
drift from their meaning more than anywhere else in a log corpus, and the failure is silent: the
number is plausible, so nothing catches it.

Three trap shapes, all observed in real analyses:

| Trap | Example shape | What it actually was |
|------|---------------|----------------------|
| A duration that measures the wrong span | `*_duration_seconds` on a completion event | The *generation* window (0.02 s bursts), not the elapsed real-world duration |
| A count derived from a container's length | `items_processed` | A list length divided by 2 — an artifact of how the rows are stored, not a count of anything |
| A `*_length` that counts rows, not content | `transcript_length` | The number of turns, not the size of the text |

The rule: for every field you plan to quote, find where it is written before quoting it. A field's
name is a claim by its author, not a measurement.

**Triangulate before reaching for expensive artifacts.** For "the stored output is thinner than the
tracker counted", the event stream usually attributes the cause without touching media files at all:
compare what the producer reported it emitted, what the consumer reported it received, the detector's
own duration measurements, and raw byte counts converted to duration. **The per-phase ratio between
them discriminates the cause**: a healthy opening that collapses to near-zero points somewhere
different from a uniform near-zero, which points somewhere different again from an upstream provider
incident visible on a status page.
