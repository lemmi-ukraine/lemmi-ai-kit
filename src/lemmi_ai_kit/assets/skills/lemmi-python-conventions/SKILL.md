---
name: lemmi-python-conventions
user-invocable: false
metadata:
  type: reference
description: |
  Enforce Python coding conventions for the Lemmi backend. Covers one-class-per-file,
  no local imports, no magic strings, no anonymous types, cognitive complexity limits,
  typed models over dicts, constants extraction, and feature-scoped dependencies.

  Use when: writing Python backend code, adding services/models/routes, reviewing
  Python code quality, or troubleshooting convention violations in PR reviews.
---

# Python Convention Examples — Lemmi Backend

This skill provides **code examples** for the conventions defined in AGENTS.md.
For the rules themselves, see AGENTS.md § Conventions.

## When This Skill Activates

- Writing or editing any Python file under `backend/`
- Adding new classes, enums, models, services, or routes
- Reviewing code for convention compliance

## File Organization Examples

```python
# GOOD: backend/app/features/jobs/enums/job_status.py — one class per file
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

# GOOD: backend/app/features/jobs/entities/job.py
class Job(Base):
    ...

# BAD: backend/app/features/jobs/enums.py (multiple enums in one file)
class JobStatus(str, Enum): ...
class JobType(str, Enum): ...
```

```python
# GOOD: backend/app/schemas/order_patch_accepted_response.py
class OrderPatchAcceptedResponse(BaseModel):
    job_id: str
    status: str

# BAD: Stuffed into backend/app/schemas/order.py alongside other schemas
```

When creating a new entity, enum, or model:
1. Create a dedicated file named after the class (`snake_case`)
2. Place it in the correct subdirectory (`entities/`, `enums/`, `models/`)
3. Re-export from the package `__init__.py`

## Import Examples

```python
# GOOD: module-scope, absolute, from package API
from app.features.orders.storage.entities import Order
from app.features.billing.services import BillingService
from app.core.config import settings
from app.features.billing.storage.enums import InvoiceCategory

# BAD: local import
class OrderPatchJob:
    def execute(self):
        from app.features.orders.storage.entities import Order  # NO

# BAD: relative import
from ..services import BillingService

# BAD: deep file path
from app.features.billing.storage.enums.invoice_category import InvoiceCategory
```

### No `TYPE_CHECKING` import guards

Do **not** reach for `if TYPE_CHECKING:` to silence an import cycle. Each guard
is a smell that two modules are coupled the wrong way — usually feature-layer
logic holding a concrete back-reference to its owner. Resolve the cycle
structurally instead: define a narrow `Protocol` the consumer depends on (the
owner satisfies it by duck-typing), move the shared type to a neutral module, or
invert the dependency.

```python
# BAD: a deferred import guard to dodge a cycle (tool ↔ session)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.features.realtime_chat.services.chat_session import (
        ChatSession,
    )

class EndChatTool:
    def __init__(self, session: "ChatSession") -> None:  # NO
        self._session = session

# GOOD: depend on a Protocol that captures only what is needed.
# session_end_host.py imports neither side concretely; the session satisfies it.
from app.features.realtime_chat.services.session_end_host import SessionEndHost

class SessionEndCoordinator:
    def __init__(self, host: SessionEndHost) -> None:  # no cycle, no TYPE_CHECKING
        self._host = host
```

Mirror the owner's method signatures exactly in the `Protocol` so basedpyright
strict accepts the structural match (e.g. an `end_session(final_status=None,
reason=None)` host method needs the same defaults on the protocol stub). The one
narrow exception — a package `__init__` that defers heavy re-exports purely for
import-time/perf reasons — must carry a comment explaining why, not a silent
guard.

### Import-cycle hygiene in core packages

- Lint and basedpyright never catch order-sensitive import cycles — only `import app.main` does.
  After touching imports in core packages with deep adapter chains (e.g. `core/ai/**` or
  `core/realtime/**`), run at least one test that imports `app.main`.
- Keep a package `__init__` re-export to the LOWEST layer (DTOs/value objects). Do NOT
  eager-re-export an adapter/service that imports a sibling the DTO consumers also import — it
  drags the whole chain in and creates a cycle. Import that adapter directly from its submodule at
  the one wiring site. When a leaf must reference a heavy core dep, prefer a function-local (lazy)
  import with `# noqa: PLC0415` + a comment over restructuring `__init__`.

## Type Safety Examples

### Typed Models Over Dicts

```python
# GOOD
class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: dict | None

def get_job_status(self, job_id: str) -> JobStatusResponse:
    return JobStatusResponse(job_id=job_id, status=status, progress=progress)

# BAD
def get_job_status(self, job_id: str) -> dict:
    return {"job_id": job_id, "status": status, "progress": progress}
```

### Constants Over Magic Strings

```python
# GOOD: constants at module level or in constants file
STAGE_PARSE_SOURCE = "parse_source"
STAGE_RESOLVE_RECORD = "resolve_record"
DETAIL_FETCHING = "fetching"

progress.update(stage=STAGE_PARSE_SOURCE, detail=DETAIL_FETCHING)

# BAD: inline string literals
progress.update(stage="parse_source", detail="fetching")
```

Where to put constants:
- Feature-scoped: `features/{feature}/constants.py`
- Core-scoped: `core/{module}/constants/{name}.py` (e.g. `core/jobs/constants/timing.py`)
- Module-level in the consuming file is acceptable for single-consumer constants

## basedpyright Compliance Patterns

### ORM Entity Assertions in Tests

```python
# GOOD: cast to Any for ORM entity attribute comparisons
from typing import cast, Any

entity = await repo.get_by_id(some_id)
entity_any = cast(Any, entity)
assert entity_any.status == "active"
assert entity_any.name == "expected"

# BAD: direct attribute access triggers basedpyright ColumnElement errors
assert entity.status == "active"  # reportOperatorIssue
```

### Missing-Field Validation Tests

```python
# GOOD: use model_validate with dict for missing-field tests
with pytest.raises(ValidationError):
    MyModel.model_validate({"field_a": "value"})  # field_b missing

# BAD: incomplete constructor call (basedpyright flags missing args)
with pytest.raises(ValidationError):
    MyModel(field_a="value")  # type error: missing field_b
```

### Optional Dev-Only Imports

```python
# GOOD: importlib for optional packages
import importlib

try:
    tasks_module = importlib.import_module("tasks")
except ModuleNotFoundError:
    tasks_module = None

# BAD: direct import (basedpyright flags even inside try/except)
try:
    from tasks import ns  # basedpyright still resolves this
except ImportError:
    ns = None
```

### Thin Typed Wrappers Expose Explicit Methods

A wrapper that forwards everything via `__getattr__` returning `Any` erases method signatures for
static analysis — downstream `get_session`/`send_message`/`connect` become `Unknown` and strict
basedpyright errors spread far beyond the wrapper. Declare explicit pass-through methods for the
APIs the feature actually uses; keep `__getattr__` only as a fallback, never as the primary typed
surface.

## Method Design Examples

### Cognitive Complexity — Split by Stage

```python
# GOOD: split into stages
class OrderPatchJob:
    async def execute(self):
        source = await self._parse_source()
        record = await self._resolve_record(source)
        await self._patch_order(record)

    async def _parse_source(self) -> SourceData: ...
    async def _resolve_record(self, source: SourceData) -> RecordData: ...
    async def _patch_order(self, record: RecordData) -> None: ...

# BAD: one long method with all stages inline
class OrderPatchJob:
    async def execute(self):
        # 80 lines of source parsing...
        # 60 lines of record resolving...
        # 40 lines of order patching...
```

## Dependency Injection Examples

### Feature-Scoped Dependencies

```python
# GOOD: backend/app/features/jobs/dependencies.py
def get_job_service(db: AsyncSession = Depends(get_db)) -> JobService:
    return JobService(db)

# BAD: backend/app/dependencies.py
def get_job_service(...) -> JobService:  # feature-specific, doesn't belong in global deps
    ...
```

A FastAPI DI factory is just a callable — a pass-through wrapper in `app/dependencies.py` that only
`return create_feature_X()` is dead indirection. `Depends(create_feature_X)` directly from the
route, and override the factory itself in tests (`app.dependency_overrides[create_feature_X]`). Put
something in `app/dependencies.py` only when it composes feature-crossing concerns or needs FastAPI
`Request`/`WebSocket` context.

### Protocol-Based Injection

```python
# GOOD
class StorageProtocol(Protocol):
    async def get(self, key: str) -> bytes: ...

class MyService:
    def __init__(self, storage: StorageProtocol): ...

# BAD
class MyService:
    def __init__(self):
        self.storage = GCSClient()  # hard-coded, untestable
```

## Route Handler Examples

```python
# GOOD: thin handler
@router.post("/orders/{id}/invoices")
async def generate_invoice(
    id: str,
    service: BillingService = Depends(get_billing_service),
):
    return await service.generate(id)

# BAD: business logic in handler
@router.post("/orders/{id}/invoices")
async def generate_invoice(id: str, db = Depends(get_db)):
    order = await db.execute(select(Order).where(...))
    result = process_invoice(order)
    return result
```

Use the project's shared exceptions (`NotFoundError`, `UnauthorizedError`, `BadRequestError`,
`ConflictError` from `app.services.utils.errors`) in routes — never raw `HTTPException` for standard
400/401/404/409, which bypasses the middleware error-shaping pipeline and yields inconsistent error
bodies. Reserve `HTTPException` for non-standard status codes.

## Async I/O Examples

```python
# GOOD
data = await client.fetch(url)
result = await repository.get_by_id(id)

# BAD
data = requests.get(url)           # blocking
result = repository.get_by_id(id)  # sync in async context
```

### Async Task Lifecycle & Concurrency

```python
# Always await fire-and-forget coroutines. An un-awaited coroutine emits a RuntimeWarning
# to stderr (NOT the app logger) and its work is silently dropped — static analysis won't flag it.
await progress_updater.update(...)     # GOOD
progress_updater.update(...)           # BAD: "coroutine ... was never awaited"

# Application-level fire-and-forget I/O (work that outlives the request) → BackgroundTaskRegistry,
# so it drains on graceful shutdown. Per-session infra loops with their own start/stop may stay raw.
get_background_task_registry().create_task(coro, name=f"invoice-{id}")     # GOOD (app-level I/O)
asyncio.create_task(coro)                                                  # BAD for app-level I/O

# A raw create_task body nobody awaits MUST self-guard, or a raise surfaces as a loop-level
# "Task exception was never retrieved". Use Exception (not BaseException) so CancelledError propagates.
async def _run() -> None:
    try:
        await do_work()
    except Exception:
        logger.exception("background task failed")

# Set a one-time/idempotency flag right AFTER the committing step, before any fallible awaited tail —
# else a mid-sequence raise leaves the action half-applied AND repeatable (e.g. a replayed client command).
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

## Settings Examples

```python
# GOOD
from app.core.config import settings
api_key = settings.openai_api_key

# BAD
import os
api_key = os.getenv("OPENAI_API_KEY")
```

### Settings Inheritance

To share fields across settings classes that read different env namespaces, extract a base class
with **no** `model_config`; each subclass sets its own `model_config = SettingsConfigDict(env_prefix="…")`.
Inherited fields are then read under the *subclass's* effective prefix at instantiation. Override only
the fields that actually differ.

## Linting Scope

Pass `ruff check --fix` / `ruff format` the EXACT files you edited (e.g. `git status --short | … | xargs`),
never a parent directory — directory-scoped autofix silently reformats unrelated, pre-existing files
in that tree and folds them into your changeset. At review time, `git status` every change and revert
edits to files outside the task's scope.

## Shared Helpers

When a utility function is used by a single consumer, it can stay local to that module. Extract to a shared location (`core/` or `utils/`) only when a second consumer appears.
