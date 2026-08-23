# GCP Log Query Templates

Common GCP Cloud Logging queries for this project. Use these when the user asks to
search GCP logs or when constructing queries to help the user find specific entries.
Replace `{SERVICE_NAME}` with the project's Cloud Run service name, and
`{PROJECT_ID}` with the GCP project id of the environment you are querying.

## Base Filters

All queries should start with the service filter:

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
```

To scope to a specific environment, use `resource.labels.project_id`, not
`resource.labels.location`. **Measured: `location` does not distinguish environments** when
deployments share a region — every entry across 11 log exports spanning two environments carried
the same `location`. One project id per environment is the reliable discriminator:

```
resource.labels.configuration_name="{SERVICE_NAME}"
resource.labels.project_id="{PROJECT_ID}"
```

```
resource.labels.configuration_name="{SERVICE_NAME}"
resource.labels.project_id="{PROJECT_ID}"
```

## Common Queries

### Background Pipeline Traces for a Session

Track a session-scoped background job (e.g., a post-session report/feedback generation pipeline) from creation to completion:

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
jsonPayload.session_id="{SESSION_ID}"
(jsonPayload.message=~"{PIPELINE_KEYWORD}" OR jsonPayload.message=~"job" OR jsonPayload.message=~"generation")
severity>=DEFAULT
timestamp>="{START_TIME}"
timestamp<="{END_TIME}"
```

### Session Timeline

All events for a specific session (add feature-scoped ID fields with OR if the app logs them):

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
jsonPayload.session_id="{SESSION_ID}"
severity>=DEFAULT
timestamp>="{START_TIME}"
timestamp<="{END_TIME}"
```

### Errors Only (Last N Hours)

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
severity>=ERROR
timestamp>="{N_HOURS_AGO}"
```

### Specific Exception Type

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
(textPayload=~"{EXCEPTION_CLASS}" OR jsonPayload.message=~"{EXCEPTION_CLASS}")
severity>=ERROR
```

### Background Job Failures

This job system has no single structured `job_failed` event — a job's terminal outcome is one of
FOUR shapes (verified 2026-07-29/07-30 against `backend/app/core/jobs/service.py` AND two real
incidents' logs — do not assume the first shape found is exhaustive, as the 07-29 revision below was
missed until a second real incident produced it):

1. `jsonPayload.event_type="job_completed"` — success.
2. `jsonPayload.event_type="job_expired"` — the repository's inactivity-sweep path
   (`JOB_INACTIVITY_EXPIRATION_SECONDS`), for a row that went silent for a long time.
3. `jsonPayload.event_type="job_execution_cancelled"` (`JOB_EVENT_CANCELLED`,
   `service.py::_run_registered_job`'s `CancelledError` handler) — a **graceful** cancellation
   (e.g. `background_task_registry`'s shutdown-timeout cancel that the task's own try/except got a
   chance to observe before SIGKILL) that DOES mark the row FAILED and DOES log a structured
   `job_`-prefixed event, WARNING severity.
4. An unstructured `"Exception in {job_type}"` / `"Exception in job_execution"` ERROR message with
   NO `job_`-prefixed event_type at all — an uncaught application exception inside the handler
   (e.g. a raised `ValueError`).

A row can also show **no terminal event whatsoever** — created/dispatched/execution_started with
nothing after, forever — when the process is killed too abruptly (hard SIGKILL, e.g. OOM) for even
the `CancelledError` handler in shape 3 to run. This is the genuinely silent case and the one most
likely to be missed: two same-shaped OOM-kill incidents produced BOTH outcomes (one job silently
stuck with nothing further logged, a different job in the other incident cleanly cancelled via
shape 3) — the abruptness of the kill relative to that specific task's execution point decides
which one you get, not the failure cause.

The query below covers all four terminal shapes; a query that only matches `event_type=~"job_"` or
`message=~"job.*failed"` will silently miss shapes 3 and 4, and NONE of these queries can
distinguish "still running" from "silently stuck forever" — for that, correlate by `job_id` (see
below) and check whether enough time has passed for the job type's normal duration.

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
(jsonPayload.event_type="job_expired" OR jsonPayload.event_type="job_execution_cancelled" OR jsonPayload.message=~"^Exception in " OR jsonPayload.message=~"BackgroundJobError")
severity>=WARNING
timestamp>="{START_TIME}"
```

To reconstruct a specific job's full outcome, correlate every `event_type=~"job_"` entry by
`jsonPayload.job_id` (a JSON parse, not `grep -A`/`-B` — see the External Service Quirks entry
`[2026-07-29] GCP Cloud Logging console exports...` in `.ai/learnings.md`/its promoted home) and
treat "created/dispatched/execution_started with no completed/expired and no Exception message" as
inconclusive rather than failed — it may simply be still running or outside the captured window.

### WebSocket Connection Issues

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
(jsonPayload.message=~"websocket" OR jsonPayload.message=~"WebSocket" OR jsonPayload.message=~"connection.*closed")
severity>=WARNING
timestamp>="{START_TIME}"
```

### Slow Requests (Latency > 5s)

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
httpRequest.latency>"5s"
timestamp>="{START_TIME}"
```

### Cold Start Detection

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
(textPayload=~"Started server process" OR jsonPayload.message=~"Application startup complete")
timestamp>="{START_TIME}"
```

### Enum/Parsing Errors

Useful when AI-parsed output bypasses enum coercion (the AI returns a Python repr like `"SomeEnum.MEMBER"` instead of the value):

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
(jsonPayload.message=~"AttributeError.*value" OR jsonPayload.message=~"{ENUM_CLASS}" OR jsonPayload.message=~"enum.*parsing")
severity>=ERROR
```

### User-Specific Session Activity

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
jsonPayload.user_id="{USER_ID}"
severity>=DEFAULT
timestamp>="{START_TIME}"
timestamp<="{END_TIME}"
```

## Query Construction Tips

1. **Always include a time range** — GCP scans are expensive without time bounds
2. **Use `jsonPayload.*` for structured fields** — the app uses structured JSON logging
3. **Use `textPayload` for unstructured output** — container startup logs, uncaught exceptions
4. **Use `=~` for regex matching** — more flexible than exact match for error messages
5. **Combine with `severity>=WARNING`** to reduce noise from INFO logs
6. **Quote special characters** in values — IDs with hyphens work unquoted, but strings with spaces need quotes
7. **Check both `jsonPayload.message` and `textPayload`** — different log sources use different fields

## Field Reference

| Field | Where | Contains |
|-------|-------|----------|
| `jsonPayload.message` | App structured logs | Log message text |
| `jsonPayload.session_id` | Session-scoped logs | WebSocket session UUID |
| `jsonPayload.<feature>_id` | Feature-scoped logs | Feature session UUID (project features add their own) |
| `jsonPayload.user_id` | Auth-scoped logs | User ID string |
| `jsonPayload.job_id` | Background job logs | Job UUID |
| `jsonPayload.event_type` | Realtime events | Event name (speech_started, etc.) |
| `textPayload` | Unstructured logs | Raw text (startup, crashes) |
| `httpRequest.requestMethod` | HTTP access logs | GET, POST, etc. |
| `httpRequest.requestUrl` | HTTP access logs | Request path |
| `httpRequest.status` | HTTP access logs | HTTP status code |
| `httpRequest.latency` | HTTP access logs | Request duration (e.g., "0.234s") |
| `severity` | All logs | DEFAULT, INFO, WARNING, ERROR, CRITICAL |
| `timestamp` | All logs | ISO 8601 timestamp |
