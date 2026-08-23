# Coding Patterns Reference — Python Backend

Detailed implementation patterns for error handling, HTTP clients, dependency injection,
authentication, and feature decorators. Read this file when implementing services that
involve cross-feature communication, external API calls, or route boilerplate reduction.

## Error Handling Architecture

The application uses **centralized error handling** via `UnifiedMiddleware`.

**Shared exceptions** (from `app.services.utils.errors`):
- `BadRequestError` (400), `UnauthorizedError` (401), `NotFoundError` (404),
  `ConflictError` (409), plus any project-specific shared exceptions
  (e.g. a 412 precondition error)

**Feature-specific exceptions** live in `features/{feature}/exceptions/` with a base class
and one exception per file. They are converted to shared exceptions at the API route boundary.

**Route exception conversion pattern:**
```python
try:
    return await service.get_resource(resource_id)
except ResourceNotFoundError as e:
    raise NotFoundError(str(e)) from e
except AccessDeniedError as e:
    raise UnauthorizedError(str(e)) from e
except YourFeatureServiceError as e:
    logger.error(f"Feature error: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e)) from e
```

**HTTPException is only acceptable** for non-standard status codes: 422, 410, 429, 500.

## Feature Route Decorators

Each feature should have a decorator in `api/decorators.py` that eliminates boilerplate:
- Exception mapping (feature → shared exceptions)
- Logging context initialization
- User ID extraction from `current_user`
- JWT token extraction (optional)

**Usage (after):**
```python
@router.get("/resources/{resource_id}")
@handle_your_feature_request(requires_auth_token=True, log_context_keys=['resource_id'])
async def get_resource(
    resource_id: UUID,
    current_user: dict = Depends(get_current_user_flexible),
    service: ResourceService = Depends(get_resource_service),
    auth_token: str = None,  # Injected by decorator
):
    return await service.get_resource(resource_id, current_user['id'], auth_token)
```

**Reference implementation:** `backend/app/features/<feature>/api/decorators.py` in any
feature that has adopted the pattern.

## HTTP Client Architecture

**Internal clients** (`BaseInternalClient`): Cross-feature communication with JWT auth.
**External clients** (`BaseExternalClient`): Third-party APIs with API key auth.
Both live in `backend/app/core/http/`.

```python
class BillingDataModifier(BaseInternalClient):
    def __init__(self, auth_token: str, logger: logging.Logger,
                 base_url: str | None = None, timeout: float = 10.0):
        super().__init__(base_url=base_url, auth_token=auth_token,
                         logger=logger, timeout=timeout)
```

**Key rules:**
- Auth token is REQUIRED (no `| None = None`)
- Logger is injected for testability
- Use enums, not magic strings
- Return Pydantic models, not raw dicts
- Use `_make_request()` and `_handle_response_status()` from base class

## Data Modifier Pattern

Data Modifiers are HTTP clients for cross-feature data updates:
- Live in the consuming feature's `services/` directory
- Non-blocking: failures should not prevent the primary operation
- Always wrap in try/except and log errors

```python
try:
    await self.billing_data_modifier.update_invoice_status(...)
except Exception as e:
    self.logger.error(f"Status update failed: {str(e)}", exc_info=True)
```

## Service Dependency Injection

Services receive dependencies through constructor injection:
- Repositories, HTTP clients, loggers, other services
- Factory functions in `features/{feature}/dependencies.py` resolve via FastAPI Depends
- Required dependencies have no default; optional use `| None = None`
- Tests mock at the DI boundary using protocol overrides

```python
async def get_order_task_service(
    request: Request,
    task_repo: OrderTaskRepository = Depends(get_order_task_repository),
) -> OrderTaskService:
    auth_token = extract_token_from_request(request)
    modifier = BillingDataModifier(auth_token=auth_token, logger=logger)
    return OrderTaskService(task_repo=task_repo, billing_data_modifier=modifier, logger=logger)
```

## Auth Token Flow

1. Extract token in route (via decorator or manual `extract_token_from_request()`)
2. Pass token to client constructor
3. Base client adds token to request headers
4. Internal endpoint validates JWT and user ownership

**Rules:** Never optional, fail fast, no token storage, secure logging (`[REDACTED]`).

## Hot Paths: GIL-bound work and bulk rewrites

**`asyncio.to_thread` does not fix pure-Python CPU work.** Plain Python bytecode holds the GIL, so a
worker thread only timeshares the same core — and dev Cloud Run is `--cpu 1`, so there is no second
core to escape to. Before reaching for `to_thread`/executors on a hot path, ask whether the work
releases the GIL. If it is plain Python over bytes, make it a **strided/bulk operation** first —
cheaper AND race-free.

A byte-at-a-time PCM interleave rewritten to four extended-slice copies measured **30–114× faster**
and byte-identical:

```python
# before: per-byte loop over the whole buffer (hundreds of ms to seconds, blocking the event loop)
# after:  four strided copies
out[0::4] = left[0::2]
out[1::4] = left[1::2]
out[2::4] = right[0::2]
out[3::4] = right[1::2]
```

Prefer stdlib extended slicing over `numpy` (pinned `1.26.4`, will not build on 3.13) and `audioop`
(removed in 3.13) — no version coupling.

**Keeping such a routine synchronous is often deliberate.** Adding an `await` inside
`StereoBatcher._create_batch` would race `_append` / `_evict_batched_audio`, which mutate the buffers
outside the dispatch lock. Note that in the same subsystem, and for the same reason.

**Guard the rewrite with the old implementation as an oracle.** An "obviously equivalent"
`b"".join(...)` rewrite was NOT byte-identical — caught only because the benchmark asserted equality
against the current implementation. The cause: `AudioSegment.silent(duration=ms)` defaults to
`frame_rate=11025`, so concatenating it onto a 24 kHz segment makes pydub `_sync()` resample the
silence and the stored gap is not `int(ms * 24000/1000)` frames. **Always pass an explicit
`frame_rate` to `AudioSegment.silent()` in this codebase.**

## Timeouts That Must Bound a Response

`asyncio.wait_for` cancels the inner coroutine and then **awaits that cancellation to complete**.
Closing a SQLAlchemy session whose server has gone away issues *more* network I/O on the same
unresponsive socket, so the cleanup blocks and the timeout bounds nothing — `/health` hung past
20 s under a 2 s `wait_for`.

```python
# BAD: cleanup talks to the dead peer, so the timeout is not a bound
result = await asyncio.wait_for(probe(), timeout=2.0)

# GOOD: does not await cancellation — cancel, leave it to be reaped, answer now
done, _pending = await asyncio.wait({task}, timeout=2.0)
if not done:
    task.cancel()          # fire-and-forget
    return unhealthy()
```

Use this shape whenever the timeout must bound the *response* — health/liveness/readiness probes,
anything a load balancer or an on-call human reads. And **test the timeout by making the dependency
unreachable** (`docker pause`), never merely slow: a paused peer is exactly the case where cleanup
itself blocks, and exactly the case `wait_for` silently fails.

## Client Free Text at Logging Boundaries

Nothing upstream bounds a hostile client string. Starlette hands a WebSocket close reason over
verbatim, so a newline inside it forges log lines and an oversized one bloats the record.

**Reuse the protocol's own size cap as the bound** where one exists — RFC 6455 §5.5.1 caps a close
reason at 123 bytes, so anything longer is a broken or hostile client and truncation loses nothing.
Then drop non-printables, in a small named helper next to the receive site:

```python
def _sanitize_close_reason(reason: str | None) -> str | None:
    if not reason:
        return None
    truncated = reason[:WS_CLOSE_REASON_MAX_BYTES]
    return "".join(ch for ch in truncated if ch.isprintable())
```

Applies to **any** new log statement carrying client-supplied free text — close reasons, headers,
message excerpts.

## Async Task Lifecycle & Concurrency

```python
# Always await fire-and-forget coroutines. An un-awaited coroutine emits a RuntimeWarning
# to stderr (NOT the app logger) and its work is silently dropped — static analysis won't flag it.
await progress_updater.update(...)     # GOOD
progress_updater.update(...)           # BAD: "coroutine ... was never awaited"

# Application-level fire-and-forget I/O (work that outlives the request) → BackgroundTaskRegistry,
# so it drains on graceful shutdown. Per-session infra loops with their own start/stop may stay raw.
get_background_task_registry().create_task(coro, name=f"feedback-{id}")   # GOOD (app-level I/O)
asyncio.create_task(coro)                                                 # BAD for app-level I/O

# A raw create_task body nobody awaits MUST self-guard, or a raise surfaces as a loop-level
# "Task exception was never retrieved". Use Exception (not BaseException) so CancelledError propagates.
async def _run() -> None:
    try:
        await do_work()
    except Exception:
        logger.exception("background task failed")

# Set a one-time/idempotency flag right AFTER the committing step, before any fallible awaited tail —
# else a mid-sequence raise leaves the action half-applied AND repeatable (e.g. a replayed "Continue").
timer.extend(...); self._extension_used = True
try:
    await reconfigure()       # fallible tail, guarded
except Exception:
    logger.exception("reconfigure failed")

# A callback that may fire as a side-effect of work done under a lock must read shared state and
# early-exit BEFORE acquiring the same lock — else the lock-holder awaiting the task deadlocks.
if self._shutdown_state is ShutdownState.SHUTTING_DOWN:
    return                    # fast path, no lock

# asyncio.Event.wait() is a GATE, not a serializer: all waiters resume at once, so a boolean
# check-then-act after it is still racy. Wrap the whole check-then-act in asyncio.Lock when idempotent.

# ContextVar payloads use default=None, never a mutable default (ruff B039) — a shared dict/list
# leaks across every context that never calls .set().
ai_meta: ContextVar[dict | None] = ContextVar("ai_meta", default=None)
```

## Narrowing `Any` in a Pydantic before-validator

A `model_validator(mode="before")` receives `data: Any` (Pydantic's own signature convention).
Under this project's basedpyright config, an annotated assignment does **not** narrow it — the
obvious `payload: dict[str, Any] = data` after an `isinstance(data, dict)` check still reports
`reportUnknownVariableType`. Only `typing.cast` clears it. Reach for `cast()` directly rather than
burning a basedpyright cycle discovering that the annotation form doesn't work.

```python
@model_validator(mode="before")
@classmethod
def resolve_persona_voice_default(cls, data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    payload = cast(dict[str, Any], data)   # NOT: payload: dict[str, Any] = data
    ...
```

This is narrowing FROM `Any` for internal use inside one function. It is **not** the cross-layer
`cast(Any, ...)` that AGENTS.md bans — that rule is about smuggling objects between layers with
different models, a different operation in the opposite direction.

## New Parameters, and Validators Called By Their Own Caller

Two defects that a reviewer reading one function cannot see — only the call site reveals them.

- **A function that grows a parameter its only caller never passes is dead code with a passing
  gate.** `check_synthesis_pressure` gained a `findings` parameter that `lint_hypotheses` never
  passed, so the corruption check it guarded (`covered > terminal` ⇒ verdicts were lost) simply never
  ran — gated behind `if findings is not None`, with its unit test failing in a suite nobody ran.
  A sibling `NameError` in the same file crashed every run and was fixed immediately; this one was
  silent for weeks. **Treat `if <new_param> is not None:` as a review flag** — it makes "nobody wired
  this" indistinguishable from "deliberately off". When a function grows a parameter, grep every call
  site in the same change and assert the argument is actually passed; where a shared script's checks
  can be disabled this way, run its test suite as part of the gate, not just the script.
- **A validator that gains a new check can start failing its own caller's in-progress state.**
  `generate()` stages output in a temp dir, calls `validate()` to recheck before the atomic rename,
  then renames. Adding "flag any abandoned staging directory" to `validate()` was correct and closed
  a real gap — and it fired on `generate()`'s **own** stage during that internal recheck, so every
  call began failing itself. Any checker invoked by its own caller mid-operation must distinguish
  *my caller's transient state, currently valid* from *the same shape, abandoned by someone else*.
  Test the self-referential call path explicitly; the fix is a caller-supplied exclusion
  (`_ignore_stage`), not a looser check.

## Never Build YAML/JSON/TOML By f-string Interpolation

`f"description: {description}\n"` is a live bug, not a style nit. A colon-space inside an unquoted
YAML scalar is a hard `ScannerError`, and **every one of the 5 real skill descriptions** the
codex-compatibility generator publishes contains a colon — while 31 synthetic tests passed because
every fixture used a placeholder with no special characters.

Use `json.dumps(value)`: its double-quoted scalar and escapes (`\"`, `\\`, `\n`) are a valid subset
of YAML's double-quoted syntax, so one stdlib call fixes both formats.

**Corollary for fixtures:** when a generator's tests use a placeholder for a free-text field
(`"d"`, `"test"`, `"x"`), add at least one fixture with real-shaped data — a colon, a quote, an
apostrophe. A placeholder that never varies cannot exercise an escaping bug, and a green suite over
unrepresentative fixtures proves nothing about the shape production data actually takes.

## Leaf Packages Must Not Import `app.core.*`

In `app/schemas/` and `app/constants/`, log with stdlib `logging.getLogger(__name__)`, **never** `log_event`.
`app/core/__init__.py:18` eagerly re-exports the whole core package, so importing
anything under `app.core.*` transitively pulls `ai.chat` -> `ai.fallback` -> `ai.stt` -> `numpy`;
one log line in `schemas/personalization.py::_optional_int` would have coupled a leaf schema to the
heaviest package in the tree. `git grep "from app\.|import app\." -- backend/app/schemas/` returns
**zero hits** today — a property worth preserving, so run it before adding the first such import.
Precedent: `app/constants/enums.py::safe_parse_enum` (stdlib logger). Rule, not gate — numpy is a
real dep so it resolves in Docker and CI; only `python -c "import app.schemas.<mod>"` in a venv
missing a transitive dep exposes it.
