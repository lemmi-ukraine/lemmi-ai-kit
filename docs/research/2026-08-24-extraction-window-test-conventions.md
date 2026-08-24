# `test-conventions`: 16 window lines adjudicated — 7 recovered as-is, 9 rewritten, 0 unportable

**Dated:** 2026-08-24. **Skill:** upstream `lemmi-test-conventions` → shipped
`plugins/python/skills/test-conventions`. **Pack:** python, not core — the correspondence map in
`docs/upstream-sync.toml` is the authority, and two earlier briefs named the core path from memory.

This is the per-skill read the debt record demanded for the hardest item in the remainder:
**24% carriage, the lowest of any skill still shipping.** It was left for a dedicated session
because the absent content is portable technique wearing source-project internals — recovering it
is a rewrite, not a merge.

## Reproduction, before any edit

Window `3dd2496d..c05bf72d`, path `lemmi-test-conventions`. Two commits touch it, **one file**
(`SKILL.md`), **27 added lines → 21 non-whitespace**. Presence checked against the whole shipped
directory, files read as bytes and decoded explicitly as UTF-8.

**5 present, 16 absent, 24% carriage — the recorded figure reproduces exactly.**

The 16 absent lines are not scattered. They are **two contiguous blocks**, and the 5 "present"
lines are three frontmatter keys plus a pair of code fences that match elsewhere in the file. So
the real unit of judgement was two, not sixteen.

## Why every line was recoverable, and how that was decided

The decisive evidence was already in the shipped file: **the kit had genericized this exact file
before.** Upstream's `InterviewFactory` ships as `OrderFactory`, `interview_factory` as
`order_factory`, "Lemmi backend" as "Python backend". The file's DI factories are already named on
a `get_*` convention (`get_openai_client`, `get_cloud_storage_service`, `get_http_client_factory`),
and it already establishes both `tests/fixtures/` (an auth-token builder) and `AsyncMock`.

That matters because it means the rewrite **continues the file's own vocabulary rather than
inventing one**. Nothing here is a new pattern; it is upstream's mechanism with the actors renamed,
which is precisely what §4.5 of `syncing-from-upstream.md` calls replaying the rename map onto new
content. The mechanism itself — `AsyncMock(spec=…)`, a `side_effect` that raises, a
`dependency_overrides` entry, an assertion on status and payload — is stock library API, not
something this session made up.

**The hygiene guard would not have caught any of it.** `_FORBIDDEN` (imported from
`tests/test_assets.py`, not retyped — it is an annotated assignment) has ten patterns, and none
matches a source-project *class* name. The private project name, machine paths, dated citations and
hard-coded skill-script paths are all covered; domain identifiers are not. So this was a contract
judgement against the extraction rules, not a rule the tests could have made for me.

## The verdict table — all 16 lines

### Block A — feature/quota-gated endpoints (10 lines)

| # | Upstream line (abbreviated) | Verdict |
|---|---|---|
| 03 | `### Feature-Gated Endpoints (@check_feature_usage)` | **REWRITE** — decorator name is a source-project internal |
| 05 | "Test the 402 quota-exhausted path by overriding the gating-service DI factory with a mock" | **REWRITE** — reflowed and generalised past the one decorator |
| 06 | "that raises — this drives the decorator's real error-shaping (status code + `errorCode`" | **RECOVER AS-IS** — carried verbatim, only reflowed |
| 07 | "payload) with no internal patching:" | **RECOVER AS-IS** |
| 10 | `exhausted = AsyncMock(spec=FeatureUsageGatingService)` | **REWRITE** — service class |
| 11 | `exhausted.check_availability_or_raise.side_effect = FeatureNotAvailableError(...)` | **REWRITE** — method + exception |
| 12 | `test_app.dependency_overrides[create_feature_usage_gating_service] = lambda: exhausted` | **REWRITE** — DI factory name |
| 14 | `response = await async_client.post(url, json=payload, headers=self.auth_headers)` | **REWRITE** — `self.auth_headers` claims an undocumented base-class attribute |
| 15 | `assert response.status_code == 402` | **RECOVER AS-IS** — verbatim |
| 16 | `assert response.json()["errorCode"] == ERROR_CODE_USAGE_EXHAUSTED` | **REWRITE** — constant name |

### Block B — shared builders (6 lines)

| # | Upstream line (abbreviated) | Verdict |
|---|---|---|
| 19 | `### Shared Builders for Many-Parameter Services` | **RECOVER AS-IS** — verbatim heading |
| 21 | "When many test files construct a many-parameter service directly (e.g. `InterviewSession` —" | **REWRITE** — named service |
| 22 | "24 constructor params, built inline at 11 sites across 6 test files), add one shared" | **REWRITE** — a census of a codebase the adopter does not have |
| 23 | "keyword-override builder under `tests/fixtures/` so a future signature change lands in one" | **RECOVER AS-IS** |
| 24 | "place, not every call site. Factories cover DB entities; builders cover service objects" | **RECOVER AS-IS** |
| 25 | "wired from mocks." | **RECOVER AS-IS** |

**7 RECOVER AS-IS · 9 REWRITE · 0 CORRECTLY ABSENT.**

## The identifier map

| Upstream | Shipped | Why this substitute |
|---|---|---|
| `@check_feature_usage` | `@enforce_quota` | Names the gate's job, not the source project's feature-flag product |
| `FeatureUsageGatingService` | `QuotaService` | Same role, no product coupling |
| `create_feature_usage_gating_service` | `get_quota_service` | Matches the file's existing `get_*` DI-factory convention |
| `check_availability_or_raise` | `check_or_raise` | Keeps the raise-don't-return contract, drops the domain verb |
| `FeatureNotAvailableError` | `QuotaExceededError` | States the condition the mock simulates |
| `ERROR_CODE_USAGE_EXHAUSTED` | `ERROR_CODE_QUOTA_EXCEEDED` | Same envelope shape, neutral name |
| `self.auth_headers` | `auth_headers` | Reads as a fixture; the base classes the file documents never promise this attribute |
| `InterviewSession` (24 params, 11 sites, 6 files) | "the same many-parameter service … a dozen collaborators" | The trigger is duplication plus arity, not a number from another repo |

`402` and `errorCode` were **kept**. 402 is a standard status and `errorCode` is a common JSON
error-envelope key; neither is a source-project identifier, and the whole point of the technique is
that the decorator shapes *both* halves of the response.

## What was added beyond a rename, and why

Two things, both stating the *reason* the technique matters — the part the brief identified as
carrying the value:

- The block now leads with the general case ("when a decorator gates the endpoint — quota,
  entitlement, rate limit") so the lesson survives for a reader with no quota decorator.
- A closing sentence the window did not have: patching the decorator or its check helper asserts
  your own mock's behaviour, and keeps passing even if the real decorator stops shaping the
  response. That is the *why* behind "no internal patching", and it is consistent with the rule the
  skill already teaches two sections earlier (mock at the DI boundary, never `patch()` a concrete
  class) and with its own gotcha that `patch()` targets the import site.

Placement mirrors upstream — Block A inside "Mocking External Services" before the fixtures table,
Block B under "Factory Usage" before "Test Naming" — so the next three-way merge sees an aligned
section list rather than a moved hunk.

## Nothing was judged unportable, and that is the honest answer

The brief allowed for lessons that cannot survive losing their example, and warned that a rewrite
inventing a plausible-but-untested pattern is worse than an honest gap. **Neither block is such a
case.** Both teach a mechanism whose every step is stock pytest/FastAPI API; only the actors were
project-specific. A zero here is not a rubber stamp — it is what the two-block structure produced
once the blocks were read, and the file's own prior genericization is the precedent that made the
substitutions obvious rather than invented.

**`references/docker-runner-gotchas.md` is a separate matter and stays out.** It is titled for one
host, names the source project's compose runners, and its pointer was dropped with it, so nothing
is orphaned. It is **not in this window** — the window touches `SKILL.md` only — and it was already
recorded as a correct deliberate drop. Recovering it was explicitly out of scope.

## Carriage, measured both ways

| Measure | Before | After |
|---|---:|---:|
| Mechanical (whole-line substring, the recorded metric) | **24%** | **33%** |
| Load-bearing phrases carried | — | **14 / 14** |
| Lessons adjudicated and carried | — | **16 / 16** |
| Source-project identifiers leaked | — | **0** |

**The mechanical figure understates the result on purpose, and cannot do otherwise.** The
measurement counts a line present on exact substring match, so every rewritten or reflowed line
reads as absent — the same upward bias the measurement record already flagged. 33% is a floor, not
the outcome; the 14/14 phrase check and the 16/16 adjudication are the real ones. Anyone re-running
the whole-line probe will still see 14 "absent" lines here, and that is expected: they are absent
*as written upstream*, which is the point.

`SKILL.md` 420 → **449 lines**, 51 under the 500-line cap.

## Gates

- `audit-skills --fail-on major` → **0 findings**, exit 0.
- Full suite green at the recorded baseline.

## What this does not do

- **It does not touch `docs/upstream-sync.toml`.** `extraction_window.status` stays `"unreviewed"`
  — two skills in the remainder (`hypothesis-validator`, `session-retrospective`) are still
  unadjudicated, and the flag is for the whole block.
- **It does not re-derive this skill's own extraction base.** The window measurement does not need
  one, and every absent line here resolved on portability grounds rather than on merge grounds. A
  future full re-merge of this skill should still find its base by minimum distance.
- **It adds no anti-pattern rows or cross-references** beyond the two blocks. Scope was the 16
  lines.
