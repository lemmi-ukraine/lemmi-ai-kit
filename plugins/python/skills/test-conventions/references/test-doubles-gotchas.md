# Test Doubles & Vacuous-Coverage Gotchas

Extends the SKILL.md "Test Doubles & Fixtures (gotchas)" section. Consolidated from
`.ai/learnings.md` on 2026-07-16. Theme: a test that would still pass with the mechanism
ripped out proves nothing — drive the real seam, and keep doubles coupled to the real
contract.

## Monkeypatch targeting

- **Hoisting a function-local import to module scope breaks
  `monkeypatch.setattr("source.module.Name")`** — the consumer now holds its OWN binding, so
  patches of the SOURCE silently stop intercepting (no error, wrong behavior). After hoisting
  any import, grep tests for `setattr("<source>.<Name>"` and re-target to the importing
  module; run the module's tests, not just ruff/import-smoke.
- **A package `__init__` binding an instance that shadows a same-named submodule breaks
  string-target monkeypatching** (`AttributeError` naming the *instance* type). Get the real
  module via `importlib.import_module("app.core.system.resource_manager")` and use the
  object-form `monkeypatch.setattr(module, "name", fake)`.

## Doubles must track the real contract

- **Build mocked structured-AI responses from the response model**
  (`Model(...).model_dump()`), never raw dicts — when the service catches parse errors and
  falls back gracefully, a schema-stale raw-dict fixture silently reroutes the test onto the
  fallback path where weak assertions keep passing. For any catch-and-fallback seam, also
  assert the INTENDED path ran (no error log emitted / output differs from input).
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
  suites test other axes and only need a pass-through, so put the inert double in
  `tests/factories/mock_service_factories.py` (`create_inert_override_guard()`) rather than
  hand-rolling it per file — one definition to update when the collaborator's shape changes.
- **Asserting structured log fields: read them off `record.__dict__`.** In non-GCP runs `log_event`
  forwards `additional_fields` as stdlib `extra`, so every structured field lands as an attribute on
  the captured `LogRecord` and caplog can assert exact values. Both obvious access forms are blocked:
  `record.close_code` fails basedpyright (unknown LogRecord attribute) and
  `getattr(record, "close_code")` trips ruff B009. `record.__dict__["close_code"]` passes both. Use
  `caplog.at_level(level, logger=<name>)`, and where the code takes a `logger` first arg, inject a
  test-named logger instead of depending on module-logger propagation.

## Vacuous coverage patterns

- **Tests of implicit runtime mechanisms must exercise the mechanism, not the function
  body** — `await`ing a fire-and-forget task retrieves its exception independently of the
  done-callback under test; calling a handler directly proves nothing about its
  installation. Drive the runtime trigger (GC the task, fire a real unregistered failure)
  and assert the observable effect.
- **A gate's accept-path tests are a written record of everything the gate currently lets
  through** — when adding a reject, classify each existing accept assertion: still-valid
  contract (set the new precondition) vs *encodes the hole* (changing it IS the fix
  landing). Never weaken the new guard to keep an accept-path test green.
- **Testing that a gate HONORS a flag is not testing that anything SETS it** — hand-setting
  `state.flag = True` in every test leaves the producer half untested; deleting the real
  authorization line would stay green. Enumerate the flag's SET sites and write one test per
  site plus the clear-on-failure path; a negative "flag is False after failure" assertion is
  vacuous unless paired with a positive set-site test.
- **Pass-through wiring (metrics/lint/logging enrichment) fails by silent degradation, not
  exception** — a direct-call unit test with hand-built inputs cannot catch a shape mismatch
  with the real caller's payload (`list(a_string)` shreds text into characters and never
  raises). Add one test that drives the real caller with only the DI boundary mocked and
  asserts the emitted count/effect.
- **A "keep in sync with X" comment is not a sync mechanism** — mirrored inventories (literal
  stems, enum echoes, allowlists) drift within days when a batch touches the source. Add a
  parse-based sync test in the mirror's suite (read and regex-parse the source file — works
  across importability boundaries) and put the reverse-pointer comment at the SOURCE.
- **A bound assertion goes silently vacuous when a change removes the pressure it measured** —
  `measured <= bound` cannot distinguish "the bound holds under load" from "there is no load".
  `test_cache_stays_under_byte_cap` uploaded 20 blobs against a monkeypatched 1000-byte cap; when
  `upload_bytes` was changed to invalidate rather than populate, both assertions kept passing as
  `0 <= 1000` and `0 == 0`, and the suite stayed green through the very change that hollowed them
  out — while the docstring went on advertising a regression that had been designed away. When a
  change alters *who writes* to a structure, grep the tests asserting bounds on it and re-derive
  what each now measures; a green suite is not evidence they still bite. Prefer a positive
  assertion of the actual contract (`_cache == {}`) over an inequality whenever the expected value
  is exact — the positive form fails the moment the contract changes, in either direction.
- **A factory that clamps its arguments makes a test's stated setup a fiction** —
  `CoachTaskFactory.create_with_subtasks_async` silently applies `max(2, min(5, subtask_count))`,
  so `subtask_count=1` really creates two subtasks and the untouched sibling stays `NOT_STARTED`
  forever, correctly defeating any "all subtasks passed" derivation. Any coach test needing every
  subtask in a terminal state must pre-fix `task.subtasks[1:]`, not just the one under test.
  General form: when a test failure's symptom fits a plausible SQLAlchemy-caching narrative, print
  the actual row count and objects before writing a fix for that narrative — a wrong-but-plausible
  theory yields a "fix" that is at worst a no-op, so it passes review and quality gates while the
  real (test-setup) bug survives.
