---
name: test-conventions
description: >
  Testing conventions for the Python backend. Integration-first philosophy,
  DI-based mocking, timeout decorators, base class rules, factory usage,
  and banned patterns. Use when writing, reviewing, or scaffolding test files.
user-invocable: false
metadata:
  type: reference
---

# Test Conventions — Python Backend

## When This Skill Activates

- Writing or editing any file under `tests/`
- Adding new test classes or test functions
- Choosing between unit, integration, or endpoint test types
- Setting up mocks for OpenAI, GCS, or internal HTTP APIs
- Reviewing tests for convention compliance

---

## Philosophy

**Integration tests are the primary quality gate.**
Prefer one comprehensive test class that covers all scenarios — happy path, all
error cases, validation failures, and edge cases — over many small isolated unit tests.

**Unit tests are welcome and good.** They are not the primary driver.

**All 3rd-party services are ALWAYS mocked.** OpenAI, GCS, and internal HTTP APIs must
be mocked via DI overrides at the `dependencies.py` boundary. No exceptions.
A test that makes real external calls is a bug.

**No performance tests. No load tests.** This project does not track or enforce
performance thresholds in automated tests.

---

## The 4 Non-Negotiable Rules

1. **Every test has a timeout decorator.** No exceptions. Bare async tests will hang forever on deadlocks.
2. **3rd-party services use DI overrides only.** Never call `unittest.mock.patch()` on a concrete client class.
3. **Endpoint tests inherit a base class. Service/integration tests do not.**
4. **No performance tests, no load tests, no real external API calls.**

---

## Test Type Decision Table

| What you're testing | Pattern | Base class | Timeout |
|---|---|---|---|
| HTTP endpoint (CRUD, auth, validation) | Inherit base class | `BaseCRUDTest` / `BaseAuthTest` | `@fast_test(3)` |
| Service + real DB (full integration) | Standalone class | none | `@integration_test(5)` |
| Complex service flow (multi-step) | Standalone class | none | `@integration_test(15)` |
| WebSocket connection + protocol | Standalone class | none | `@websocket_test(10)` |
| Pure logic (no I/O, no DB) | Standalone class | none | `@fast_test(3)` |
| CRUD via endpoint (data persistence) | Inherit `BaseCRUDTest` | `BaseCRUDTest` | `@fast_test(3)` |

---

## Timeout Decorators

Import from `tests.utils.timeout_decorator`:

```python
from tests.utils.timeout_decorator import fast_test, integration_test, websocket_test
```

| Decorator | Default | When to use |
|---|---|---|
| `@fast_test(3)` | 3 s | Unit tests, endpoint tests, simple logic |
| `@integration_test(5)` | 5 s | Standard DB integration |
| `@integration_test(15)` | 15 s | Multi-step service flows |
| `@integration_test(20)` | 20 s | Complex workflows with many DB ops |
| `@websocket_test(10)` | 10 s | WebSocket connection and protocol tests |

Apply the decorator **directly on the test method**, below `@pytest.mark.*`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
@integration_test(5)
async def test_create_order_stores_record(self, order_service, async_session):
    ...
```

---

## Integration Test Structure

A comprehensive integration test class covers every case in one place:

```python
class TestOrderServiceIntegration:
    """Integration tests for OrderService with real database."""

    @pytest.fixture
    def service(self, async_session, mock_openai_client):
        return OrderService(db=async_session, openai_client=mock_openai_client)

    # ── Happy path ──────────────────────────────────────────────────────────

    @pytest.mark.integration
    @pytest.mark.asyncio
    @integration_test(5)
    async def test_create_stores_record(self, service, async_session):
        result = await service.create(OrderCreate(title="Test"))
        assert result.id is not None
        # Verify DB state
        db_record = await async_session.get(Order, result.id)
        assert db_record.title == "Test"

    # ── Error cases ─────────────────────────────────────────────────────────

    @pytest.mark.integration
    @pytest.mark.asyncio
    @integration_test(5)
    async def test_create_raises_not_found_when_customer_missing(self, service):
        with pytest.raises(NotFoundError):
            await service.create(OrderCreate(customer_id=99999))

    @pytest.mark.integration
    @pytest.mark.asyncio
    @integration_test(5)
    async def test_create_raises_conflict_on_duplicate(self, service, async_session):
        existing = await OrderFactory.create_async(async_session)
        with pytest.raises(ConflictError):
            await service.create(OrderCreate(title=existing.title))

    # ── Edge cases ──────────────────────────────────────────────────────────

    @pytest.mark.integration
    @pytest.mark.asyncio
    @integration_test(5)
    async def test_list_returns_empty_for_new_user(self, service):
        result = await service.list(user_id=99999)
        assert result == []
```

Key structural rules:
- One fixture block at the top — all shared setup as `@pytest.fixture` methods
- Group tests with comments: happy path, error cases, edge cases
- Always verify DB state after writes (do not trust the service's return value alone)
- Use factories for test data — never raw `INSERT` statements

---

## Mocking External Services

### Rule
Mock at the DI boundary (`dependencies.py`). Inject the mock via the fixture.
Never use `unittest.mock.patch("app.features.xyz.SomeConcreteClient")`.

### OpenAI Client

```python
# In test class:
@pytest.fixture
def service(self, async_session, mock_openai_client):
    return OrderService(db=async_session, openai_client=mock_openai_client)

# mock_openai_client is provided by conftest.py
# Configure responses:
def test_openai_response_handling(self, service, mock_openai_client):
    mock_openai_client.some_method.return_value = expected_response
    ...
```

For endpoint tests, use the `override_openai_client` fixture (auto-applies DI override to `test_app`):

```python
class TestReportEndpoints(BaseCRUDTest):
    @pytest.fixture(autouse=True)
    def _apply_openai_override(self, override_openai_client):
        pass  # fixture side-effect wires up the DI override
```

### Cloud Storage (GCS)

```python
@pytest.fixture
def service(self, async_session, mock_cloud_storage_client):
    return DocumentService(db=async_session, storage=mock_cloud_storage_client)

# mock_cloud_storage_client is provided by conftest.py
```

### Internal HTTP APIs (HTTP Client)

```python
@pytest.fixture
def service(self, async_session, mock_http_client_factory):
    return ProfileService(db=async_session, http_factory=mock_http_client_factory)

# mock_http_client_factory is provided by conftest.py
```

### Decorator-Gated Endpoints (`@enforce_quota`)

When a decorator gates the endpoint — quota, entitlement, rate limit — test the rejection
path by overriding the gating service's DI factory with a mock that **raises**. This drives
the decorator's real error-shaping (status code + `errorCode` payload) with no internal
patching:

```python
exhausted = AsyncMock(spec=QuotaService)
exhausted.check_or_raise.side_effect = QuotaExceededError("limit reached")
test_app.dependency_overrides[get_quota_service] = lambda: exhausted

response = await async_client.post(url, json=payload, headers=auth_headers)
assert response.status_code == 402
assert response.json()["errorCode"] == ERROR_CODE_QUOTA_EXCEEDED
```

Patching the decorator or its check helper instead asserts your own mock's behaviour — the
test keeps passing even if the real decorator stops shaping the response. Same shape for any
decorator whose dependency is injected: make the dependency fail, let the decorator run.

### Available fixtures from `conftest.py`

| Fixture | Provides |
|---|---|
| `mock_openai_client` | `MockOpenAIClient` instance |
| `override_openai_client` | DI override for `get_openai_client` applied to `test_app` |
| `mock_ai_chat_provider` | `MockAIChatProvider` instance |
| `override_ai_chat_provider` | DI override for `get_ai_provider` |
| `mock_cloud_storage_client` | `MockStorageClient` instance |
| `override_cloud_storage_service` | DI override for `get_cloud_storage_service` |
| `mock_http_client_factory` | Mock HTTP factory for internal HTTP APIs |
| `override_http_client_factory` | DI override for `get_http_client_factory` |
| `profile_service_stub` | `StubProfileService` |

---

## Endpoint Tests (Base Classes)

Inherit the appropriate base class and configure three class attributes:

```python
from tests.base_tests import BaseCRUDTest, BaseAuthTest, BaseValidationTest

class TestOrderEndpoints(BaseCRUDTest, BaseAuthTest, BaseValidationTest):
    endpoint_url = "/api/v1/order"
    factory_class = OrderFactory
    response_schema = OrderResponse
    create_schema = OrderCreate
```

| Base class | What it provides |
|---|---|
| `BaseCRUDTest` | create, list, get, update, delete tests + 404 cases |
| `BaseAuthTest` | 401 on missing / invalid / expired token |
| `BaseValidationTest` | parametrized Pydantic validation error tests |

Override `_get_create_data()` to customise the payload. Override `_setup_related_data()` for FK dependencies.

---

## Factory Usage

All test data goes through async factories. Never insert rows directly.

```python
from tests.factories.order_factory import OrderFactory

# Single record
order = await OrderFactory.create_async(session)

# Batch
orders = await OrderFactory.create_batch_async(session, 5)

# With overrides
order = await OrderFactory.create_async(session, title="Custom Title", user_id=42)
```

### Shared Builders for Many-Parameter Services

When several test files construct the same many-parameter service inline — a service wired
from a dozen collaborators, rebuilt at each call site — add one shared keyword-override
builder under `tests/fixtures/` so a future signature change lands in one place, not in
every test that names it. Factories cover DB entities; builders cover service objects wired
from mocks.

## Test Naming

```
test_<what>_when_<condition>_<expected_outcome>
```

Examples:
- `test_create_order_when_customer_missing_raises_not_found`
- `test_list_orders_when_user_has_none_returns_empty`
- `test_update_order_when_not_owner_raises_unauthorized`

For positive cases, the `when_<condition>` part can be omitted:
- `test_create_order_stores_record`
- `test_list_orders_returns_paginated_response`

---

## Markers

```python
@pytest.mark.unit          # fast, no I/O (also for CRUD endpoint tests)
@pytest.mark.integration   # real DB, real service stack
@pytest.mark.slow          # > 1 second
@pytest.mark.security      # auth and access control
@pytest.mark.websocket     # WebSocket protocol tests
@pytest.mark.auth          # authentication enforcement
@pytest.mark.validation    # input validation and schema
```

---

## Anti-Patterns

| Anti-pattern | Correct approach |
|---|---|
| `unittest.mock.patch("app.features.X.ConcreteClient")` | Inject mock via constructor or DI override fixture |
| Real OpenAI / GCS / internal HTTP APIs calls in tests | Use `mock_openai_client`, `mock_cloud_storage_client`, `mock_http_client_factory` |
| Performance benchmarks / load tests | Not done in this project — delete if found |
| `@pytest.mark.external` | External services are always mocked — marker is meaningless |
| `@pytest.mark.crud` as standalone marker | CRUD tests are unit tests — use `@pytest.mark.unit` |
| Bare `async def test_*` without timeout decorator | Always add `@fast_test(3)`, `@integration_test(5)`, or `@websocket_test(10)` |
| One assertion per test class (micro-tests) | Group all related cases in one comprehensive class |
| Raw `INSERT` / SQL in tests | Use `BaseAsyncFactory` — create via `create_async()` |

---

## Test Doubles & Fixtures (gotchas)

- **`patch()` targets the import site, not the definition.** Prefer DI overrides; but when you must
  `patch()` a non-client internal, patch where it is *used* (imported), not where it is defined or
  re-exported, or the mock silently doesn't apply. After a bulk file move, run a dedicated grep for
  `patch("app.<old_path>` across `tests/` — string targets raise no import error and fail silently —
  and include underscore-prefixed helpers (`_get_*`), which public-API grep patterns miss.
- **A shared-script check that reads live repo state makes every unit test of its caller
  repo-state-dependent.** Give the read an injection seam and have synthetic-fixture tests pass it
  explicitly — an `archive_text=…` parameter on the check, which would otherwise let the repo's real
  archive fire a NOTE nondeterministically inside the synthetic-text tests. The failure is invisible at authoring time and fires later on unrelated repo
  activity (a quiet week → a drain-due NOTE → a passing test breaks). Corollary: around any check
  that can emit unrelated scheduling NOTEs, assert the **absence of the specific message** — never
  `notes == []`, which couples the test to every future note the checker learns to emit.
- **A `model_validator`-decorated method is not callable from a test.** basedpyright rejects
  `config.require_resolved_voice()` with *"Object of type PydanticDescriptorProxy… is not callable"*:
  the decorator leaves a descriptor proxy as the *static* type even though Pydantic swaps in the
  unwrapped function at class-build time, so the call works at runtime and fails the gate. Don't
  reach for `# type: ignore`. Put the check in a plain property/method that the validator *calls*
  (`_ = self.voice_value`) — one raise site, ordinary Python that both the type checker and the test
  can address — and reach the branch with `model_construct`, which skips validation by design. When
  introducing a nullable field, also test that a *sibling* missing required field still reports
  itself: a new guard can otherwise hijack the error and report a symptom as the cause.
- **For a behaviour-preserving rewrite, copy the old implementation into the test as an oracle —
  never import it.** An import goes tautological the moment the original changes, and the copy keeps
  the comparison honest after the original is deleted. It also lets you *measure* behaviour instead
  of deriving it: `AudioSegment.silent()` defaults to 11025 Hz and is resampled on append, losing a
  fixed 2–3 frames per gap (1000 ms produced 47,996 bytes, not 48,000) — a deficit that is not a
  ratio and cannot be computed. Enumerate the edge branches as named scenarios, and add tests that
  fail if someone "fixes" a deliberately preserved defect, each with the reason inline.
- **Removing a catch-all `@handle_errors` decorator surfaces latent fixture bugs.** A defensive
  decorator silently absorbs `TypeError`/`AttributeError` from under-specified mocks, so "passing"
  tests were buggy. Expect a wave of failures; fix the fixtures (prefer explicit
  `AsyncMock(return_value=...)` over attribute auto-creation) — do not reinstate the decorator.
- **Converting an attribute to a `@property` breaks stubs built via `object.__new__`.** Those stubs
  assign the attribute directly and now hit "property has no setter". Set the underlying state
  (`_shutdown_state = …`), not the derived alias; grep tests for write-sites when adding a property.
- **`ASGITransport` does not run the application lifespan.** Any registry or DI singleton needed
  during *request resolution* must be populated by `create_application()` itself — lifespan may
  rebuild or refresh it for runtime startup, but cannot be its only writer. When adding lifespan
  wiring, ask whether request handlers need the state, and test `create_application()` **without**
  lifespan before considering the wiring complete.
- **Assert infinite-stream semantics at the service generator, not over HTTP.** `ASGITransport`
  waits for the response body to finish, so a never-ending `StreamingResponse` hangs before a test
  can inspect frames. Exercise the service's managed async iterator directly for
  snapshot/replay/heartbeat/disconnect behavior, and keep HTTP tests for *terminating* outcomes —
  auth errors, 429, list/history, route shape, OpenAPI. Never weaken a production stream just to
  make an in-memory transport finish. Tests that hand-consume a stream must mirror the route
  contract: cancel, then `aclose()`, then call `release()` explicitly.
- **Splitting one predicate into two silently unpins its equivalence test.** A test that asserts
  "SQL twin == pure filter" guards nothing after the split unless it is re-pointed at the correct
  twin AND the fixture gains a row where the two new predicates disagree — without that row it
  keeps passing no matter which predicate it pins, and its stale docstring reads as if the old
  invariant still holds. When splitting any predicate, treat every test that pins it as requiring
  re-pointing, add the distinguishing fixture row, and assert the two predicates genuinely differ
  on it; grep sibling docs/READMEs for the old pairing claim too — it was echoed stale in two.
  (The live case split one row-eligibility predicate into two narrower ones, with an integration
  test still pinning the old pairing.)
- **More double/coverage traps** — monkeypatch retargeting after import hoisting, package-attr
  shadowing, model-derived AI-response fixtures, `MagicMock(wraps=)`, `spec=`-truthy children and
  `getattr` probes, unset-`AsyncMock` state-machine branches, required-collaborator doubles,
  structured-log field assertions, set-site vs honor-site flag tests,
  accept-tests-that-encode-the-hole, real-seam pass-through tests, parse-based sync tests:
  [references/test-doubles-gotchas.md](references/test-doubles-gotchas.md). Consult it whenever a
  test passes suspiciously easily or a mock feeds a comparison/arithmetic site.

## Assertions That Pass For The Wrong Reason

Three shapes where green means nothing. All three were live in this repo for months.

- **An expected falsy result with more than one legitimate cause proves nothing.**
  `validate_jwt_token` returns `None` both for a malformed/missing user-id AND for an expired token.
  While a shared fixture token was expired, `test_token_with_invalid_user_id_format` and
  `test_token_with_missing_user_id` kept passing — on expiry, never on the malformed-field logic they
  name. The intended path went untested for ~11 months and nothing signalled it. Either **isolate the
  cause** (assert a distinguishing error message or field, not the bare `None`/`False`/`[]`) or
  **neutralize the others** in the fixture. Confirmed by the fix: once expiry was corrected both
  assertions still passed — for the first time actually exercising the intended branch.
- **A frozen `exp`/`nbf`/`iat` in a pasted "real token" is a wall-clock time bomb.** Three files
  hand-rolled `jwt.encode()` around a captured production payload keeping literal
  `"nbf": 1755442078, "exp": 1786978078` — `iat + 365 days`, valid for exactly one year, then 12
  tests began failing every run once the clock crossed it. Invisible at write time; a full year of
  green CI. The correct pattern already existed one file over (`tests/fixtures/auth.py`
  `create_jwt_token()` uses `datetime.now(UTC) + timedelta(...)`), so this was a hand-rolled
  divergence from a documented convention. **Never keep a captured token's absolute claims** —
  recompute relative to run time, preserving only offsets that matter. Cheap sweep:
  `grep -rn '"exp":\s*[0-9]\{9,10\}' tests/` (it found all 15 live occurrences and correctly skipped
  2 deliberately-expired negative-test literals).
- **A skipped gate reads green.** A test guarded by `is_file()` + `pytest.skip` reports success in
  CI, where the file it needs can never exist. A skip is not a pass; count skips per run.

## Being Inside A Tool's `include` Is Not Being Gated

A type checker's `include` list in `pyproject.toml` may cover `tests/` while the **canonical gate
command** named in AGENTS.md narrows to the source package — in which case `tests/` looks
type-checked and is not. Measured on one such repo: test files using the project's own
`@pytest.fixture(autouse=True)` convention report `reportUnusedFunction`, and pre-existing files
using the same convention report the identical error, because an autouse fixture is by definition
never called by name.

So: **check what scope the gate command actually passes**, not what the config includes. When a type
error appears in a test file you just wrote, probe two pre-existing files using the same convention
*before* treating it as your regression or silencing it — a repo-wide pattern silenced in one new
file is worse than the error, because it makes that file diverge. Report the canonical scope's result
and any extra scope's result separately, naming both.

## Pre-Writing Checklist

Before writing any test:

- [ ] Have I identified the right test type (unit / integration / endpoint)?
- [ ] Is there already a test class for this component I should extend?
- [ ] Do I know which 3rd-party services this code calls? (mock them all)
- [ ] Have I included happy path + all error cases + edge cases in the same class?
- [ ] Does every test method have a timeout decorator?
- [ ] Am I using factories for all test data?
- [ ] Are DB state assertions present for every write operation?
- [ ] Are test names following `test_<what>_when_<condition>_<expected_outcome>`?
