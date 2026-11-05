# Vacuous Coverage — Tests That Pass For The Wrong Reason

Extends SKILL.md. Theme: a test that would still pass with the mechanism ripped out proves
nothing. These traps are independent of how a dependency is provided, so they apply to every
integration test, every pure contract test, and every fake installed at a sanctioned seam.
The traps that only exist in mock-based suites live in
[legacy-mock-suite.md](legacy-mock-suite.md).

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
  raises). Add one test that drives the real caller through its real boundaries and asserts the
  emitted count/effect.
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

## A fake is a CLAIM about the outside world, and a wrong claim degrades to green

A fake at a sanctioned seam — a provider-leaf fake, a mock server's expectation, an emulator's
seeded state — asserts what the real dependency does. When that assertion is wrong AND the caller
**degrades gracefully**, a broken fixture becomes a vacuous pass rather than a failure.

### 0. A fake payload is built from the real schema, never hand-typed

Build a fake structured response from the response model (`Model(...).model_dump()`), never a raw
dict — when the service catches parse errors and falls back gracefully, a schema-stale raw-dict
payload silently reroutes the test onto the fallback path where weak assertions keep passing. For
any catch-and-fallback seam, also assert the INTENDED path ran (no error log emitted / output
differs from input).

### 1. A stub path must be DERIVED from the client's constants, never hand-copied

Measured: a mock-API fixture stubbed `/api/internal/<resource>/parse` while the calling service used
`/api/v1/internal/...`. The missing `/v1` meant **every** call through that client 404'd in the
containerised suite, for as long as the stub had existed — hidden because the caller degraded on
error. The tests that finally failed named an unrelated feature entirely, so nothing pointed at the
stub.

```bash
grep -oE '"/api[^"]*"' <source root> -r | sort -u   # diff against the stub paths
```

Hand-copying a route into a fixture forks it from the constant the client actually uses, and nothing
re-joins them. Derive the stub's paths from the client's own constants, or assert equality between
the two sets in a test.

### 2. Fabricated ids must sit OUTSIDE the real id band

Measured: a fixture minted ids as `md5(content) % 10000` — inside the real id band, where
production records ran 2859—3159. The double was *too realistic*, so a mock id leaking into real
data could never be spotted on sight. That is the exact property that let fabricated ids survive in
production for months. Put fabricated ids somewhere no real id can reach.

### 3. An `__init__` assignment silently kills the method it shadows

A mock response class defines `def raise_for_status(self)` that raises on `status >= 400` — and
`__init__` then assigns `self.raise_for_status = MagicMock()`, which **shadows it**. So a factory
called with `status_code=500` returns a response that does not raise: the request "succeeds" and the
body parses.

Found only because a new test asserting *"a 500 must raise"* failed against **correct** production
code. The dangerous direction is the inverse — a test asserting success under an injected 500
passes and reads as error-path coverage.

```bash
# before trusting any double's error-path behaviour:
grep -n 'self\.<method_name> = ' <the double>   # inside __init__ ⇒ the method is dead
```

### 4. A stale double becomes a silent no-op when its seam is wrapped in `except Exception`

Measured: a cleanup helper gained a call reading three new attributes off the session object; the
suite's stub session predated them. The `AttributeError` raised **inside** the `except Exception`
that exists so a failed cleanup degrades to teardown — correct production behaviour — and
converted the test failure into *"nothing happened"*. Five tests failed on assertions naming the
cleanup; **not one named the missing attribute**, and the swallowed traceback never reached pytest's
output.

```bash
git grep -l "<SeamFunction>" -- tests/   # in the SAME edit that widens what the seam reads
```

Two lessons. Grep the doubles when widening a seam, rather than waiting for a suite that will give
you a misleading failure instead of a stack trace. And when a degradation path swallows an exception,
make the swallow point **name the attribute** — a `logger.exception` was present here and the
runner never surfaced it, so the information existed and was unreachable exactly when it was needed.

> The file's own docstring already warned about this hazard **for three other attributes** and it
> recurred anyway, because the warning listed the attributes instead of stating the rule.

---

**When any of these is corrected, expect previously-passing tests to change behaviour, and read that
as signal rather than regression.** Removing a fallback that swallowed transport errors will fail
tests that look unrelated to the subsystem — the fallback was holding up everything else that went
through that call. Budget a full-suite run for it, not a targeted one.

## A docstring that weighs exactly TWO options can lock in the defect it warns about

Measured: a parser discarded an open START event when a second arrived, and a test asserted exactly
that. Its docstring justified the expectation: *"keeping the first would mint a single pair covering
two turns, which places the later turn's data at the earlier turn's offset — the exact
desynchronisation this work exists to remove."*

Every clause is true and the conclusion is still wrong, because the comparison is **binary** —
keep-the-first versus keep-the-second — and the correct answer is a third option the docstring
never names: **emit BOTH**. Discarding the first produces the *same* failure the docstring warns
about, so the test locked in the defect it was written to prevent while reading as a considered
trade-off.

- When a test docstring argues its expectation by weighing two alternatives, **treat the enumeration
  itself as the thing to check**: ask what a third option would be, and whether the stated harm also
  follows from the chosen branch.
- A docstring that reasons about a trade-off is **more** dangerous than a bare assertion — it
  reads as already-audited, so reviewers stop at the reasoning instead of the option set.
- Grep-able symptom: any invariant joining two lists **positionally** with no test asserting
  `len(a) == len(b)`.

## Two ways a test silently asserts nothing

**1. A NEGATIVE log assertion over a capture the code never writes to is vacuous.** The measured
case was an injected `MagicMock()` logger: `caplog` captures records that reach the logging
framework, and a unit under test that logs through a logger the helper *injects* never reaches it. One feature's `_build()` helper passed `logger=MagicMock()`, so
`caplog.records` was empty for that unit. A positive assertion then fails loudly (fine), but

```python
assert not any(r for r in caplog.records if ...)   # passes over zero records, forever
```

can never fail. The integration-model form of the same trap is a log assertion that reads a
capture the harness does not feed — the wrong logger prefix, a level below the capture threshold,
a child process whose lines land elsewhere. Pair every "no such record" assertion with a positive
one on the same capture in the same test, so the capture is shown able to see anything.

**2. Subclassing a test class to reuse its builders re-runs the parent's tests under the child.**
The inherited test methods execute again in the subclass's context — inflating the count, and
sometimes passing for reasons that have nothing to do with the child. Extract shared builders into a
module-level factory or a plain mixin that defines no `test_*` methods.

## A return value only ever compared against its broken-case value is untested

Every rowcount assertion for two destructive statements expected **zero**, so a method that always
returned `0` would have passed the entire suite. This is the count-the-complement rule (never phrase a
claim as all-X-were-Y when Y is in the selection pattern) arriving through a new door: a **return
value** whose only assertions are against the value it would take if it were broken.

It is easy to miss precisely because the surrounding assertions are strong — proving the ROWS are
gone does not prove the COUNT of removed rows is right. Add one case where the expected count is
non-zero, or the return value is unverified regardless of how many assertions surround it.

## A guard test that omits a production parameter eventually fails for a limit production never applies

Under-testing is the smaller half. The larger half is that the guard drifts into asserting a
constraint the real system does not have, and then **fails** — inviting a "fix" to the production
artifact to satisfy a broken instrument. One such test made "the prompt is now too big, trim it" the
tempting read; it would have driven a rewrite of freshly-reviewed prose. Two independent facts
settled it the other way: an end-to-end assembly at the REAL cap showed the sanitizer never
truncating (largest filled block 19,872 of 20,000, byte-identical every time).

When a guard test fails, first ask whether it is constructing the unit the way production does —
compare its arguments against the real call site before touching the artifact under test.

## A filter with no test that REJECTS something is untested, however many acceptance tests it has

A rejection path whose detector has **never fired** in production is a broken-instrument hypothesis
before it is evidence of health. Measured: a minimum-duration filter compared its threshold against a
provider-reported duration that carried a hard floor (configured silence window plus padding) *above*
the threshold, so the filter was arithmetically unreachable; its rejection counter had read 0 since
deployment and was cited as "no false positives". Every threshold compared against a derived quantity
needs one test that computes the quantity's floor and proves the threshold sits above it, and one test
in which the filter actually rejects — a zero from a detector nobody has seen fire is UNREAD.

## Three assertions that pass for the wrong reason

All three were live in one service's suite for months.

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
  green CI. The correct pattern already existed one file over (a token helper computing
  `datetime.now(UTC) + timedelta(...)`), so this was a hand-rolled divergence from a documented
  convention. **Never keep a captured token's absolute claims** — recompute relative to run time,
  preserving only offsets that matter. Cheap sweep:
  `grep -rn '"exp":\s*[0-9]\{9,10\}' tests/` (it found all 15 live occurrences and correctly skipped
  2 deliberately-expired negative-test literals).
- **A skipped gate reads green.** A test guarded by `is_file()` + `pytest.skip` reports success in
  CI, where the file it needs can never exist. A skip is not a pass; count skips per run.

## Rewrites, splits and live inputs

- **For a behaviour-preserving rewrite, copy the old implementation into the test as an oracle —
  never import it.** An import goes tautological the moment the original changes, and the copy keeps
  the comparison honest after the original is deleted. It also lets you *measure* behaviour instead
  of deriving it: `AudioSegment.silent()` defaults to 11025 Hz and is resampled on append, losing a
  fixed 2–3 frames per gap (1000 ms produced 47,996 bytes, not 48,000) — a deficit that is not a
  ratio and cannot be computed. Enumerate the edge branches as named scenarios, and add tests that
  fail if someone "fixes" a deliberately preserved defect, each with the reason inline.
- **Splitting one predicate into two silently unpins its equivalence test.** A test that asserts
  "SQL twin == pure filter" guards nothing after the split unless it is re-pointed at the correct
  twin AND the fixture gains a row where the two new predicates disagree — without that row it
  keeps passing no matter which predicate it pins, and its stale docstring reads as if the old
  invariant still holds. When splitting any predicate, treat every test that pins it as requiring
  re-pointing, add the distinguishing fixture row, and assert the two predicates genuinely differ
  on it; grep sibling docs/READMEs for the old pairing claim too — it was echoed stale in two.
- **A check that reads live repository state makes every test of its caller
  repository-state-dependent.** Give the read an injection seam and have synthetic-input tests pass
  it explicitly — an `archive_text=…` parameter on the check, which would otherwise let the repo's
  real archive fire a NOTE nondeterministically inside the synthetic-text tests. The failure is
  invisible at authoring time and fires later on unrelated repo activity (a quiet week → a
  drain-due NOTE → a passing test breaks). Corollary: around any check that can emit unrelated
  scheduling NOTEs, assert the **absence of the specific message** — never `notes == []`, which
  couples the test to every future note the checker learns to emit.

## Being inside a tool's `include` is not being gated

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

## Making a hook fail closed expands the caller contract

Converting an implicit fallback into a registered factory whose getter **raises when unset** is
usually right — a silently absent provider had been ending jobs with no tasks, no error and no row.
But the raise fires at every construction site, including ones no spec lists. Measured: the spec
named 7 files; the raise broke **4 tests in an 8th** that built the object directly and had no reason
to know a registration now existed — they broke purely on the hook being **consulted at all**.

- Before making a hook fail closed, take a **caller census** by grepping the call-site symbol
  tree-wide (`git grep -n '<function>('`) — never from the spec's file list, which enumerates the
  files the author thought about, and scaffolding is exactly what gets forgotten.
- Budget a registration fixture **with teardown** for each test module the census finds; a
  module-level hook leaks between tests otherwise.
