# Container Log Format — Docker Compose Worked Example

**One container runtime's output shape, not a requirement.** The problems this file solves —
separating interleaved emitters, inferring severity when there is no severity field, correlating
requests with no trace id, and mapping in-container paths back to the repository — occur in every
container runtime's log output. The prefixes and path roots differ; `podman-compose`, `kubectl
logs`, `nerdctl` and a plain `journald` unit each need the same four things worked out. Read this as
the filled-in example and substitute your own runtime's shapes.

## Log Line Structure

### Multi-container output (`docker compose logs`)

```
container-name-1  | 2026-03-21 10:15:23.456 INFO:     uvicorn.access: 192.168.1.1:0 - "GET /api/v1/health HTTP/1.1" 200
container-name-1  | 2026-03-21 10:15:24.789 ERROR:    app.services.voice_session: Failed to process audio chunk
container-name-1  | Traceback (most recent call last):
container-name-1  |   File "/app/backend/app/services/voice_session/audio_processor.py", line 42, in process
container-name-1  |     result = await self._client.transcribe(chunk)
container-name-1  | httpx.ReadTimeout: Request timed out
```

**Parsing rules:**
- Container name prefix ends at ` | ` (pipe with surrounding spaces)
- Everything after the pipe is the actual log content
- Multi-line entries (stack traces) share the same container prefix
- Container names may have a numeric suffix (`-1`, `-2`) for scaled services

### Single-container output (`docker compose logs backend`)

Same format but all lines share one container prefix. Can also appear without prefix
if captured via `docker logs <container-id>`.

## Severity Detection

Container stdout has no structured severity field — this is the *missing severity role* case from
SKILL.md Step 1a. Infer it from the line content, and say in the report that severity was inferred
rather than read:

| Pattern | Severity | Examples |
|---------|----------|----------|
| `ERROR:` or `ERROR ` | ERROR | `ERROR:    app.core.middleware: Unhandled exception` |
| `WARNING:` or `WARNING ` | WARNING | `WARNING:  app.services.voice_session: Session timeout approaching` |
| `INFO:` or `INFO ` | INFO | `INFO:     uvicorn.access: ...` |
| `DEBUG:` or `DEBUG ` | DEBUG | `DEBUG:    app.core.logging: Request context set` |
| `CRITICAL:` | CRITICAL | `CRITICAL: app.core.config: Missing required env var` |
| `Traceback (most recent call last):` | ERROR (continuation) | Stack trace follows a preceding ERROR line |
| HTTP status 5xx in access log | ERROR | `"POST /api/v1/sessions HTTP/1.1" 500` |
| HTTP status 4xx in access log | WARNING | `"GET /api/v1/user HTTP/1.1" 401` |

## Timestamp Formats

| Source | Format | Example |
|--------|--------|---------|
| Python logging | `YYYY-MM-DD HH:MM:SS.mmm` | `2026-03-21 10:15:23.456` |
| Uvicorn access | `YYYY-MM-DD HH:MM:SS.mmm` | Same |
| Docker daemon | `YYYY-MM-DDTHH:MM:SS.nnnnnnnnnZ` | `2026-03-21T10:15:23.456789000Z` |
| Alembic/startup | May lack timestamps | `INFO  [alembic.runtime.migration] Running upgrade...` |

## Request Correlation

Container stdout has no correlation-id field either, unless the application puts one in the message
text. In descending order of reliability:

1. **Request ID** — look for `request_id=` or `X-Request-ID` in log messages
2. **Context fields** — `user_id=`, `session_id=`, plus feature-scoped session IDs, set via the app's logging-context helper (e.g., `set_logging_context()`)
3. **Temporal grouping** — entries within the same second from the same container, sharing a module path
4. **Uvicorn access log pairing** — match the request start (`INFO: ... "POST /path"`) with preceding application logs by timestamp

## Container Names (typical)

Illustrative of the naming convention (`<service>-<ordinal>`), not a set to expect:

| Container | Typical Name | What It Runs |
|-----------|-------------|--------------|
| Backend API | `backend-1` or `<project>-backend-1` | FastAPI app (uvicorn) |
| Database | `db-1` or `postgres-1` | PostgreSQL |
| Redis | `redis-1` | Redis cache |
| Test runner | `test-runner-fast-1` | Pytest in container |

## Stack Trace Parsing

A traceback in container output is identical to the same traceback in a structured export, except
that every line carries the container prefix — so strip prefixes before parsing:

```
backend-1  | Traceback (most recent call last):
backend-1  |   File "/app/backend/app/features/voice_session/services/voice_session.py", line 156, in handle_audio
backend-1  |     await self._audio_processor.process(chunk)
backend-1  |   File "/app/backend/app/features/voice_session/services/audio_processor.py", line 42, in process
backend-1  |     result = await self._client.transcribe(chunk)
backend-1  | httpx.ReadTimeout: Request timed out
```

**Path mapping:** Container paths start with `/app/` which maps to the repository root.
- `/app/backend/app/features/...` → `backend/app/features/...`
- `/app/alembic/...` → `alembic/...`

## Container Issue Patterns

Runtime-level rather than application-level, and the reason a container log is worth reading past
the application errors. The examples are from a Python/PostgreSQL stack; the categories are not.

| Pattern | What It Means |
|---------|---------------|
| `Connection refused` on startup | Container started before dependency (DB, Redis) was ready |
| `OSError: [Errno 98] Address already in use` | Port conflict — previous container didn't shut down cleanly |
| `sqlalchemy.exc.OperationalError: connection to server closed` | DB connection pool exhaustion or container restart |
| Repeated `health check` failures | App not responding — check startup errors above |
| `ModuleNotFoundError` | Missing dependency — dependency sync (e.g., `uv sync`) or Dockerfile issue |
| `alembic.util.exc.CommandError` | Migration conflict or missing migration |
