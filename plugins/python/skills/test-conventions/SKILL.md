---
name: test-conventions
description: >
  Testing conventions for Python services: every behaviour test is a Testcontainers
  integration test that drives the real application against real dependencies in containers,
  fakes external systems only at sanctioned seams (provider leaf, mock-server base URL,
  emulator), and is written first and proven red then green. Use when writing, changing,
  running, debugging, reviewing or planning tests, and before implementing a feature or fix.
  Not for static checks over repository files (manifests, prompts, import boundaries).
when_to_use: >
  "write a test", "add tests", "fix this bug", "TDD", "testcontainers", "integration test",
  "fake the provider", "mock this service", "flaky test", "why is this test failing",
  "review these tests"
user-invocable: false
metadata:
  type: reference
---

# Test Conventions — Testcontainers Integration Testing

**The model in one sentence:** a test proves behaviour by driving the real application through
its real entry points, against real dependencies that a harness starts in disposable containers,
with external systems faked only at sanctioned seams — and it is written, and seen to fail,
before the code that makes it pass.

Examples labelled *reference adopter* come from one FastAPI service that runs its whole suite
this way (Postgres, a cloud-storage emulator, an HTTP mock server for a sibling API, LLM and
speech providers faked at the provider leaf). Its names illustrate a slot; they are not required
names. The project's own harness README names the real fixtures, flags and paths — read it once
per session. The contract underneath: [references/harness-contract.md](references/harness-contract.md).

## Scope and precedence

- **Governs every test of application behaviour** — anything that crosses a process boundary:
  database, HTTP, storage, queues, sockets, provider SDKs.
- **Pure contract tests** — a parser, a comparison, a reference resolver: no I/O at all — may run
  without containers. The harness contract allows them; some projects ban them outright. Whether
  the project allows them is a decision its `AGENTS.md` records. Where allowed they still follow every
  rule below except provisioning: no mocks, assertions on outputs.
- **The project's `AGENTS.md` wins where it disagrees** — a project still running a mock-based
  suite, or a library with no external dependency at all. Say which rule you followed.

## Non-negotiables

1. **Real dependencies in containers.** Databases, caches, queues and storage run as real
   services (or their official emulators) in containers the harness starts, with the production
   migrations applied. Nothing is started by hand; no shared or developer database. A dependency
   that needs no container — a temporary directory, a local subprocess — is simply used for real.
2. **Fakes only at sanctioned seams** (table below). Never `unittest.mock.patch` / `MagicMock`
   doubles of application objects, `monkeypatch.setattr` on application or SDK code, framework
   `dependency_overrides`, or patching SDK internals. Any non-local network connection fails the
   test.
3. **Test first, red then green.** Write the test → run it → it fails **on the new assertion**
   (not an import error, a provisioning error or a typo) → implement → the same command passes.
   Report both runs with their exact commands and summary lines. A bug fix starts with a test
   that reproduces the bug.
4. **Explicit, minimal profile.** Every test declares the narrowest profile that can prove it; a
   test without one is rejected at collection.
5. **Observable outcomes only:** HTTP status and body, WebSocket messages, database rows, stored
   objects, requests the mock server received, calls the fakes received, log records and metrics
   read through the harness. Never private attributes.
6. **Generated identifiers.** Every id comes from the harness's scope or a fixture loader. Never a
   hard-coded id another test or worker could also use, never a reserved numeric range.
7. **Bounded waits; nothing left running.** Poll asynchronous outcomes with a deadline — never a
   fixed `sleep`. Close every socket and stream you open and let every job reach a terminal state:
   the harness quiesces after each test and fails the one that leaked work.
8. **No performance or load tests.** A latency or throughput requirement is verified by
   observability, not by a test.

## The loop

```bash
<runner> <tests>/native/<feature>/test_<surface>.py::test_<outcome> -x   # red, then green
<runner> <tests>/scenarios/<feature>/<name>.yaml                          # one declarative scenario
<runner> --<profile-flag> <profile> -n auto                               # the affected profile
<runner> -n auto                                                          # everything
```

*Reference adopter:* `uv run pytest …`, `--harness-profile app`, `--harness-validate-only`
(scenario validation, no containers).

- **Judge a run by its exit code and summary line, captured to a file** — never through a
  `| tail` or `| grep`, which hands you the filter's exit code instead of the runner's.
- A red run that died on an import or provisioning error is not red. Fix it and run again until
  the failure is the assertion about the new behaviour.
- The first run of a profile pays for provisioning (seconds); later tests in the same run pay
  milliseconds. Narrow the selection, not the rules.
- **If CI cannot run the container suite**, the merge gate is a full local run on the exact
  pushed commit, recorded against that commit (a commit status, for example). A result belongs to
  one commit; re-run after every push or rebase.

## Choosing the profile and the style

| Behaviour | Profile | Style |
|---|---|---|
| Repository, migration, constraint, raw SQL | database only | native |
| Request → response → persisted or external effect | full app | declarative scenario if linear; native if it needs loops, concurrency or fault scripting |
| Background job outcome | full app | scenario `eventually`, or native bounded wait |
| WebSocket or streaming conversation | full app | native |
| Provider failure, retry, fallback | full app | native, scripting the fake or the mock server |
| Configuration read once at import or startup, crash hooks, signal drain | a separate app process | native |

*Reference adopter:* profiles `db` and `app`, selected with `@pytest.mark.profile("db")` natively
or `environment: app` in YAML; files under `native/<feature>/test_<surface>.py`,
`scenarios/<feature>/<name>.yaml`, shared datasets in `fixtures/<domain>.py`, reusable actions in
`actions/<domain>.py`.

Declarative scenarios carry linear request/response/database flows; anything with control flow is
a native test. The scenario rules that keep them honest are in
[references/harness-contract.md](references/harness-contract.md#declarative-scenarios).

## Seams — what to use instead of a mock

| Dependency | Sanctioned seam | *Reference adopter* |
|---|---|---|
| Database, cache, queue the app owns | The real service in a container, real migrations | Postgres + Alembic `upgrade head` |
| Managed service that ships an emulator | The emulator container, at the endpoint variable the SDK already honours | fake-gcs-server via `STORAGE_EMULATOR_HOST` |
| Another HTTP service the app calls | A mock-server container at the **base URL the app reads from config**; tests script expectations and read the requests it received | Smocker at the sibling API's base URL; unmatched requests answer `666` |
| SDK with no emulator (LLM, speech, payments) | A fake at the **provider leaf** — the one factory that constructs the SDK client — installed through an app-owned override hook | an override registry the client factories consult; `fakes.chat.respond(...)`, `fakes.chat.calls` |
| Anything else on the network | Refused: a guard fails the test on any non-local connection | a socket-level network guard |

Rules that make a seam trustworthy:

- **Everything above the leaf stays real** — routing, retries, fallback, logging, metrics,
  persistence of provider calls. A fake installed higher up deletes exactly the code most likely
  to be wrong.
- **Configuration for one test** goes through the harness's per-test override, restored after the
  test (*reference adopter:* `app.override_settings(target, **fields)`). A value the app copied at
  import or startup cannot be reached that way: boot a separate app process with that environment,
  or change the app to read the value at use time. A test that stays red only because the value
  was copied is telling you which. Environment that every test shares is pinned once in the root
  `conftest.py`, with the developer's `.env` not loaded — pin there only what all tests need.
- **Faults and timing are injected at the seam**: the fake fails its next call, the mock server
  answers an error, a hold or gate primitive parks a request so a race can be positioned. A fault
  no real client can produce (a send failing on an open socket) comes from a transport-fault layer
  between the server and the app, not from patching the handler. Never
  sleep to win a race, and never wait out a production duration — shrink it with an override.
- **When the app runs in-process on its own event loop**, run app-side code through the harness's
  helper for that loop (*reference adopter:* `await app.run(lambda: coro())`); never use the app's
  engine or client factories from the test's loop.
- **A fake is a claim about the real dependency.** Build fake payloads from the real response
  model, and derive mock-server routes from the client's own constants — a hand-copied path that
  404s degrades to a quiet fallback, not a failure.
- **No seam fits?** Add one to the application in the same change — a factory leaf, a
  settings-driven URL, an override hook — and say so. A behaviour that "can only be unit tested"
  needs a seam, not a mock.

## Run the real application

The app starts through its production factory with its real lifespan, served on a real socket on
a dynamic port. In-memory transports (`ASGITransport`, `TestClient`) skip or reshape the lifespan
and cannot finish an infinite stream — over a real socket a test reads a stream incrementally and
closes it. Everything the app would do in production at startup, it does in the test.

## Writing a native test

```python
# Fixture names (api, auth, harness, db) follow the reference adopter;
# wait_until stands for the harness's bounded-polling helper.
import pytest

pytestmark = pytest.mark.profile("app")


async def test_submitted_order_completes_and_is_readable_by_its_owner(api, auth, harness, db):
    owner = await harness.fixtures.load("user")  # generated id, unique to this test's scope
    headers = auth.headers(owner["user_id"])

    created = await api.post("/api/v1/orders", json={"sku": "A-1"}, headers=headers)
    assert created.status_code == 202
    order_id = created.json()["id"]

    await wait_until(
        lambda: db.scalar("SELECT status FROM orders WHERE id = :id", {"id": order_id}),
        until=lambda status: status == "completed",
        timeout_s=15,
        describe=f"order {order_id} completed",
    )
    read = await api.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert read.json()["status"] == "completed"
```

- **One behaviour per test, named after the outcome**: `test_expired_token_is_rejected_with_401`.
  Where a condition is what distinguishes it, `test_<what>_when_<condition>_<outcome>`.
- **Data comes from named fixture loaders** that return references, shared by native tests and
  scenarios. A raw mutation is an explicit, parameterised preparation step — never string-built SQL.
- **Verify persisted state after every write**, not only the response that claims it happened.
- **Use a fresh principal per test** where the app enforces real per-user caps.
- **Keep a test under ~20 s.** Long waits mean a production timeout is being waited out — override
  it.

## Isolation

Each run and each parallel worker gets its own containers and ports. After every test the harness
quiesces the work the test started, then resets every mutable dependency — truncates tables,
clears the mock server's expectations and history, empties buckets, resets fakes and in-process
registries. A test therefore assumes an empty world and builds what it needs. Transaction rollback
is not a substitute: requests served by the app's own pool and background jobs never join the
test's transaction. Boundaries in full: [references/harness-contract.md](references/harness-contract.md#isolation-boundaries).

## When a test fails

1. **Read the failure artifacts before re-running**: failing step, expected and actual, redacted
   HTTP exchanges, the app log, the mock server's request history (*reference adopter:*
   `test-artifacts/<execution-id>/<test>/`).
2. **A teardown failure is a failure** — usually leaked work (an open socket, an unfinished job).
   Fix the test, not the quiesce.
3. **An unmatched-request answer from the mock server** means the app called a route no test
   expected — compare the request history with the client's constants.
4. **A refused non-local connection** means the app reached a real provider. Route it through a
   seam; never allow-list it.
5. **Flaky?** Run the test alone, in reverse order and twice in a row. A test that passes in only
   one order shares state through an identifier or a leaked job.
6. **Debug with retained state** through the harness's local-only keep-failed flag, which prints
   the connection details and the clean-up command (*reference adopter:*
   `--harness-keep-failed -x <target>`).

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| `unittest.mock.patch(...)`, `monkeypatch.setattr` on app or SDK code, `dependency_overrides` | Fake at the sanctioned seam; add a seam if none fits |
| A unit test written because "this can't be integration tested" | Add the missing seam to the app |
| Implementing first, writing the test after | Red on the new assertion first, then green |
| Fixed `sleep` before an assertion | Bounded polling with a deadline and a description |
| Hard-coded ids or reserved id ranges | Harness-generated ids, fixture references |
| Asserting on private attributes or internal calls | Assert what a client, the database or the mock server observes |
| A fake installed above the provider leaf | Fake the leaf; keep routing, retries and logging real |
| Waiting out a production timeout | Override the setting for the test |
| A test with no profile, or the full-app profile for a SQL question | The narrowest profile that proves it |
| Performance or load tests | Observability with a named metric |

## Legacy mock-based suites

A project that still carries a suite built on mocks follows this skill for every new test, and
does not grow the old suite's fixtures. Replace a mock-based test in the same change that adds the
integration test covering its behaviour. While the old suite still runs, its traps are in
[references/legacy-mock-suite.md](references/legacy-mock-suite.md).

## Tests that pass for the wrong reason

An integration test can be vacuous too: an expected falsy result with two possible causes, a frozen
token expiry, a skipped gate read as green, a negative log assertion over a capture nothing writes
to, a bound assertion whose load was removed, a filter no test ever sees reject anything, a fake
whose error path cannot fire. Consult
[references/vacuous-coverage.md](references/vacuous-coverage.md) whenever a test passes
suspiciously easily, a fake feeds a comparison, or a change alters who writes to a structure
some test bounds.

## Review checklist

- [ ] Red run recorded — failing on the new assertion — and green run recorded, with commands.
- [ ] Profile present and minimal (database-only when no app is needed).
- [ ] No `unittest.mock`, no `monkeypatch` of app or SDK code, no `dependency_overrides`, no fixed
      `sleep`.
- [ ] Every external dependency reached through a sanctioned seam; any new seam named in the change.
- [ ] Assertions on observable outcomes, including persisted state after each write.
- [ ] Identifiers generated; nothing left running; runs in ≲20 s.
- [ ] Each negative assertion paired with a positive one on the same capture.
- [ ] No performance or load test.
- [ ] Where CI does not run the container suite: the merge gate ran on the pushed head.
