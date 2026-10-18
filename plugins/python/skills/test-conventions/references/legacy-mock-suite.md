# Maintaining a Legacy Mock-Based Suite

**This is not a licence to write mocks.** New tests follow [SKILL.md](../SKILL.md): real
dependencies in containers, fakes only at sanctioned seams. This file keeps the traps of the
model that SKILL.md replaced, for a project that still carries a suite built on
`unittest.mock`, `monkeypatch` or framework dependency overrides and has to keep it green while
it migrates.

Each entry was paid for in such a suite. Under the integration model most of them cannot
occur, which is the strongest argument for migrating: a test that drives the real seam has no
patch target to get wrong and no double to drift from the real contract.

Migration order that has worked: write the integration test for the behaviour, see it fail
for the right reason, make it pass, then delete the mock-based test it replaces in the same
change. Do not grow the legacy suite's fixtures while doing so.

## Monkeypatch targeting

- **Hoisting a function-local import to module scope breaks
  `monkeypatch.setattr("source.module.Name")`** — the consumer now holds its OWN binding, so
  patches of the SOURCE silently stop intercepting (no error, wrong behavior). After hoisting
  any import, grep tests for `setattr("<source>.<Name>"` and re-target to the importing
  module; run the module's tests, not just ruff/import-smoke.
- **A package `__init__` binding an instance that shadows a same-named submodule breaks
  string-target monkeypatching** (`AttributeError` naming the *instance* type). Get the real
  module via `importlib.import_module("<package>.<module>")` and use the
  object-form `monkeypatch.setattr(module, "name", fake)`.
- **`patch()` targets the import site, not the definition.** Patch where the name is *used*
  (imported), not where it is defined or re-exported, or the mock silently doesn't apply. After
  a bulk file move, run a dedicated grep for `patch("app.<old_path>` across `tests/` — string
  targets raise no import error and fail silently — and include underscore-prefixed helpers
  (`_get_*`), which public-API grep patterns miss.

## Doubles must track the real contract

- **`MagicMock(wraps=obj)` does NOT delegate attribute access** — `wraps` covers CALLS only;
  every unset attr returns a fresh MagicMock that explodes in comparisons/arithmetic. For
  Settings/config doubles use a REAL instance with overridden fields; if a mock is
  unavoidable, grep the SUT for `self.config.` and set every read attribute.
- **Adding a read of `collaborator.attr` to a class is a contract change for every existing
  test that `Mock()`s that collaborator** — the pre-existing tests' bare Mocks now feed
  non-iterable/wrong-typed values. Grep the class's test files for bare doubles of that
  collaborator and set the new attr in the same change (batched test runs surface this
  phases later otherwise).
  **`spec=` does not save you, and the failure is silent rather than loud.** `spec=` constrains
  attribute *names* only — an unset attribute returns a truthy child MagicMock. So a new nullable
  entity column consumed behind an `if x:` guard silently activates the new branch in every
  pre-existing spec'd-mock test: they keep **passing** while exercising the wrong path (adding
  `Order.user_background` made the no-CV prompt fallback inject a mock repr into the prompt in
  the missing-resume test). Same shape for defensive probes: a new
  `getattr(obj, "attr", None)` sees an auto-created truthy Mock and takes the wrong branch — a
  guaranteed-sender `application_state` reachability probe read every mocked websocket as DEAD,
  which would have silently fast-failed `order.ended` delivery across 6 pre-existing harnesses
  until each pinned `application_state.value = WS_STATE_OPEN`. Whenever production grows a NEW
  attribute read on a mocked object — spec'd or not, `getattr` included — sweep every double of
  that object and pin the attribute explicitly (usually `None`) in the same change.
- **Never rely on an `AsyncMock` default for a boolean or optional-token result in an ordered
  state machine** — awaiting an unset `AsyncMock` returns another mock, which is truthy. Job
  acquisition tries initial → abandoned-pending → stale-processing → failed-retry CAS branches in
  order; fixtures that configured only the branch under test left the earlier ones unset, so the
  service treated an unconfigured earlier branch as an acquired attempt and the tests exercised the
  wrong transition while still passing. **Set every branch mock to `None` first, then override
  exactly the one that should win** — control flow must match the scenario name.
- **A new required collaborator is worth the test churn — keep it required.** A defaulted `None`
  keeps every existing construction site compiling and is a silent hole: any future site that
  forgets it gets the protection quietly absent with nothing failing. Making
  `OverrideGuard` required surfaced all 6 construction sites across 4 unrelated test
  files at type-check time — **the compile error IS the audit of who constructs the class**. Those
  suites test other axes and only need a pass-through, so put the inert double in one shared
  factory module rather than hand-rolling it per file — one definition to update when the
  collaborator's shape changes.
- **Asserting structured log fields: read them off `record.__dict__`.** When a logging helper
  forwards structured fields as stdlib `extra`, every field lands as an attribute on the captured
  `LogRecord` and caplog can assert exact values. Both obvious access forms are blocked:
  `record.close_code` fails basedpyright (unknown LogRecord attribute) and
  `getattr(record, "close_code")` trips ruff B009. `record.__dict__["close_code"]` passes both. Use
  `caplog.at_level(level, logger=<name>)`, and where the code takes a `logger` first arg, inject a
  test-named logger instead of depending on module-logger propagation.
- **Shared builders for many-parameter services.** When several test files construct the same
  many-parameter service inline from mocks, add one shared keyword-override builder so a future
  signature change lands in one place, not in every test that names it.

## Doubles hide fixture bugs

- **Removing a catch-all `@handle_errors` decorator surfaces latent fixture bugs.** A defensive
  decorator silently absorbs `TypeError`/`AttributeError` from under-specified mocks, so "passing"
  tests were buggy. Expect a wave of failures; fix the fixtures (prefer explicit
  `AsyncMock(return_value=...)` over attribute auto-creation) — do not reinstate the decorator.
- **Converting an attribute to a `@property` breaks stubs built via `object.__new__`.** Those stubs
  assign the attribute directly and now hit "property has no setter". Set the underlying state
  (`_shutdown_state = …`), not the derived alias; grep tests for write-sites when adding a property.
- **A `model_validator`-decorated method is not callable from a test.** basedpyright rejects
  `config.require_resolved_voice()` with *"Object of type PydanticDescriptorProxy… is not callable"*:
  the decorator leaves a descriptor proxy as the *static* type even though Pydantic swaps in the
  unwrapped function at class-build time, so the call works at runtime and fails the gate. Don't
  reach for `# type: ignore`. Put the check in a plain property/method that the validator *calls*
  (`_ = self.voice_value`) — one raise site, ordinary Python that both the type checker and the test
  can address — and reach the branch with `model_construct`, which skips validation by design. When
  introducing a nullable field, also test that a *sibling* missing required field still reports
  itself: a new guard can otherwise hijack the error and report a symptom as the cause.

## In-memory transports

These are the reasons the integration model runs the real application on a real socket.

- **`ASGITransport` does not run the application lifespan.** Any registry or DI singleton needed
  during *request resolution* must be populated by the application factory itself — lifespan may
  rebuild or refresh it for runtime startup, but cannot be its only writer. When adding lifespan
  wiring, ask whether request handlers need the state, and test the factory **without**
  lifespan before considering the wiring complete.
- **An in-memory transport cannot finish an infinite stream.** `ASGITransport` waits for the
  response body to finish, so a never-ending `StreamingResponse` hangs before a test can inspect
  frames. Suites stuck on it exercised the service's async iterator directly and kept HTTP tests
  for *terminating* outcomes. Never weaken a production stream just to make an in-memory
  transport finish — a real socket reads the stream incrementally and closes it.
- **A decorator-gated endpoint (quota, entitlement, rate limit) was tested by overriding the
  gating service's DI factory with a mock that raises**, so the decorator's real error-shaping
  ran. Patching the decorator or its check helper instead asserts your own mock's behaviour —
  the test keeps passing even if the real decorator stops shaping the response. Under the
  integration model the same principle needs no override: make the dependency fail at its
  sanctioned seam (the mock server answers "not available") and let the decorator run.
