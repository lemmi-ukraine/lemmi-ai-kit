# GCP Log Query Templates

Common GCP Cloud Logging queries for this project. Use these when the user asks to
search GCP logs or when constructing queries to help the user find specific entries.
Replace `{SERVICE_NAME}` with the project's Cloud Run service name.

## Base Filters

All queries should start with the service filter:

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
```

To scope to a specific environment, add the configuration name and region — e.g., if
production and dev deployments run in different regions:

```
resource.labels.configuration_name="{SERVICE_NAME}"
resource.labels.location="{REGION}"
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

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
(jsonPayload.message=~"job.*failed" OR jsonPayload.message=~"job.*error" OR jsonPayload.message=~"BackgroundJobError")
severity>=WARNING
timestamp>="{START_TIME}"
```

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
