# Analysis Quality Examples

All feature names, file paths, platform field names, and log excerpts below are **illustrative
examples**. They are calibration samples for what "evidence-based" looks like — the contrast between
each BAD and GOOD pair is the content, not the stack they happen to be written in.

## Good vs. Bad Root Cause Analysis

### Example 1: Database Connection Error

**Log excerpt:**
```
ERROR: app.features.chat.storage.transcript_repository: Failed to save transcript
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) server closed the connection unexpectedly
```

**BAD analysis (surface-level):**
> Root Cause: The database connection was closed. The fix is to add retry logic.

Why this is bad: describes the symptom, not the cause. Doesn't explain WHY the connection was closed or reference any code.

**GOOD analysis (evidence-based):**
> Root Cause: The `TranscriptRepository.save_transcript()` at `backend/app/features/chat/storage/transcript_repository.py:87` uses a long-running session that spans the entire chat WebSocket lifecycle. When a session exceeds the PostgreSQL `idle_in_transaction_session_timeout` (default: 30 minutes in the project's Docker Compose config), the server drops the connection. The repository acquires a session in `__init__` but only commits at session end, leaving the transaction idle during the entire audio exchange.
>
> Evidence:
> - `transcript_repository.py:23` — session injected via `__init__`, not per-operation
> - `docker-compose.local.yaml:45` — PostgreSQL `idle_in_transaction_session_timeout=1800000`
> - Log timing: error occurs ~31 minutes after session start (10:15:23 start, 10:46:45 error)

---

### Example 2: Hypothesis Labeling

**Log excerpt:**
```
WARNING: app.features.voice_session.services.voice_session: Audio buffer overflow, dropping 3 chunks
WARNING: app.features.voice_session.services.voice_session: Audio buffer overflow, dropping 5 chunks
ERROR:   app.features.voice_session.services.voice_session: Session terminated unexpectedly
```

**BAD analysis (unfounded speculation):**
> Root Cause: The audio processing is too slow and can't keep up with the input stream, probably because the upstream API is rate-limiting us.

Why this is bad: "probably" hides a guess as a conclusion. No code reference, no evidence for rate limiting.

**GOOD analysis (properly labeled hypothesis):**
> Root Cause: The `VoiceSession._process_audio_queue()` at `backend/app/features/voice_session/services/voice_session.py:134` drops chunks when the internal buffer exceeds `MAX_BUFFER_SIZE=50`. After dropping 8+ chunks (logged warnings), the session receives an incomplete audio segment that causes the upstream speech API to return an error, triggering session termination at line 201.
>
> Evidence:
> - `voice_session.py:134` — buffer overflow threshold and drop logic confirmed
> - `voice_session.py:201` — termination on API error confirmed
> - Log sequence: 2 buffer overflow warnings precede the termination error by <1 second
>
> [HYPOTHESIS] The buffer overflow itself may be caused by either: (a) network latency spikes to the upstream provider slowing the consumer, or (b) the client sending audio faster than real-time. Evidence needed: check whether the request-latency field for those upstream calls (`httpRequest.latency` in a GCP export) spikes before the overflow warnings, or compare audio chunk timestamps against wall-clock time.

---

### Example 3: Issue Grouping

**Log entries (within 2 seconds):**
```
10:15:23.100 ERROR: app.features.report.services.report_generator: Failed to generate report for session abc-123
10:15:23.150 ERROR: app.core.api.middleware.unified: Unhandled exception in POST /api/v1/sessions/abc-123/report
10:15:24.200 ERROR: app.features.report.services.report_generator: Failed to generate report for session def-456
10:15:24.250 ERROR: app.core.api.middleware.unified: Unhandled exception in POST /api/v1/sessions/def-456/report
```

**BAD grouping (over-split):**
> Issue 1: Report generation failed for session abc-123
> Issue 2: Unhandled exception in middleware for abc-123
> Issue 3: Report generation failed for session def-456
> Issue 4: Unhandled exception in middleware for def-456

Why this is bad: 4 "issues" that are really 1. The middleware errors are just the service error bubbling up. Both sessions hit the same bug.

**GOOD grouping:**
> Issue 1: Report generation failure — 2 occurrences (abc-123, def-456)
>
> The middleware errors are the service exception propagating through the error handling chain, not a separate problem. Both sessions fail with the same exception in `report_generator.py`, indicating a systematic issue (not session-specific).
