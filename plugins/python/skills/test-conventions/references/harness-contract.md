# The Harness Contract

What a Testcontainers integration harness provides, and therefore what a test may rely on and
must not re-implement. SKILL.md is the working procedure; this is the contract underneath it.

Read the project's own harness README first — it names the real fixtures, profiles, flags and
artifact paths. Where this file and the project's README disagree, the README describes what
the project actually built. Examples labelled *reference adopter* are one FastAPI service's
names; they illustrate a slot, they are not required names.

## Division of labour

| Component | Owns | The project supplies |
|---|---|---|
| Testcontainers | Container provisioning, readiness wait strategies, the resource reaper | Pinned image versions |
| Environment provider | Profiles, dynamic endpoints, ownership records of everything started | Which dependencies each profile starts |
| Application adapter | Starting the app with its real lifespan, migrations, readiness, graceful stop | Start command or in-process server, migration command |
| Fixture manager | Named datasets returning references, scoped caches, reset | Dataset loaders and per-dependency reset procedures |
| Scenario runner | Strictly validated declarative scenarios, captures, bounded polling | Registered actions and authentication providers |
| Diagnostics collector | Per-test failure artifacts, redaction, size caps | App-specific evidence worth collecting |

A test that starts a container, opens its own database engine to the app's database, or spawns
the app by hand is re-implementing one of these rows — and will leak the resource the harness
would have recorded and cleaned up.

## Lifecycle

```text
collect and filter tests          (node ids, -k, -m, profile flag: all before provisioning)
  → resolve the union of profiles the selected tests need; reject unknown profiles
  → provision those dependencies in parallel; bounded readiness waits
  → run the production migrations (or the documented equivalent)
  → start the application with its real lifespan; verify readiness
  → per test: load fixtures → run → collect evidence on failure → quiesce → reset
  → stop the application, remove every owned resource
```

- Filtering happens before anything starts, so a database-only selection never starts the app.
- Cleanup is always attempted: after success, failure, cancellation and partial startup failure.
  A cleanup failure after passing tests fails the run; after a failing test it is reported
  alongside, never instead.
- Infrastructure readiness (container is up) is separate from business-outcome polling (the job
  finished). The first belongs to the harness, the second to the test's bounded wait.
- Startup, each operation, each scenario and teardown are bounded independently, and cleanup gets
  a fresh bounded context after a cancellation. A per-test hard timeout is the last resort, not the
  wait strategy. *Reference adopter:* step 30 s, scenario 120 s, quiesce 15 s, `pytest-timeout`
  300 s.

## Isolation boundaries

| Boundary | Guarantee |
|---|---|
| Execution | Each run, and each parallel worker, gets its own containers, dynamic ports and labels; concurrent runs on one machine share no writable state |
| Test | Owned async work is quiesced, then every mutable dependency is reset — tables truncated, mock-server expectations and history cleared, buckets emptied, fakes and in-process registries reset |
| Fixture | Caches are keyed by the isolation scope and dropped on reset; a partial load rolls back |
| Async work | Producers and consumers a test started are stopped or awaited before the data they touch is removed |

Transaction rollback is a valid reset only when every write the test causes goes through that
one transaction. Requests served by the app's own connection pool and background workers do not,
so a harness for a real application truncates instead. Fixed id ranges reserved per test are not
an isolation strategy: they collide the moment two workers or two runs share a database.

## Declarative scenarios

Where the harness offers a declarative format (YAML in the reference adopter), its rules are
what make a scenario trustworthy:

- Versioned documents, strictly validated **before** provisioning: unknown fields, duplicate
  names, unresolved references and unsupported capabilities are errors, not warnings.
- One operation per step: an HTTP request, a read-only query, a parameterised mutation, an
  assertion over values already in hand, a bounded `eventually` over a read-only observation, a
  registered native action, or an include of a reusable setup with explicit inputs and outputs.
- References keep their type when used whole; text interpolation only inside strings; a missing
  reference fails rather than becoming an empty string.
- SQL binds values through parameters; substitution never builds query text or identifiers.
- Exact equality and subset matching are distinct; missing, null, zero and empty stay distinct;
  multi-row exact comparisons need deterministic ordering.
- Only read-only observations are polled. Mutations and actions are never retried implicitly.
- No shell, no evaluated code. Domain behaviour that needs code is a registered native action
  with a declared contract — and control flow (loops, concurrency, fault scripting) is a native
  test, not a longer scenario.

## Process configuration captured at import or startup

A per-test settings override reaches only values the app reads at use time. Values validated at
import, objects built once by the application factory or lifespan, crash hooks and signal
handling are fixed for the life of the process. For those, the harness boots a **separate app
process** from the production entrypoint with the test's environment, against the same execution's
containers, with the provider-leaf fakes installed inside it and the network guard active. It is
stopped (signal, drain, bounded wait, kill) and recorded like any other owned resource. Boots cost
seconds, so tests share a child per configuration.

*Reference adopter:* `child_apps.get(name, db, env)` (module pool) and
`async with child_app(name, **env)`; scripted with `child.script({...})`, read with
`child.calls("chat")`.

## Diagnostics and debug retention

- On failure — including a test whose body passed and whose teardown or isolation check failed —
  the harness writes a per-test artifact directory: outcome, failing step, expected and actual,
  duration, redacted HTTP exchanges, the app log, container logs and the mock server's request
  history. Startup and interrupted runs get their own evidence directory. Logs are collected
  before resources are destroyed.
- Credentials, tokens and configured secret fields are redacted; payloads are size-capped.
- A local-only keep-failed flag stops at the first failure, skips its reset, keeps the containers
  and prints the execution id, safe connection details and the clean-up command. It is refused
  in CI. Ordinary runs are always ephemeral.
- Clean-up of a retained run removes only resources recorded as owned by that execution.

*Reference adopter:* `test-artifacts/<execution-id>/<test>/failure.json`,
`--harness-keep-failed -x`, `python -m tests.integration.harness clean <execution-id>`.

## Order and repetition independence

A harness should be able to prove that a test's result does not depend on what ran before it:
run a representative test alone, inside the suite, in reverse order and twice in a row, and
compare. *Reference adopter:* `--harness-repeat 2`, `--harness-reverse`.
