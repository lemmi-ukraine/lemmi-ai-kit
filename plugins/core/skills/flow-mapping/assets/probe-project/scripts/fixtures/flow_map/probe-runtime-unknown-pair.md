# Flow — Runtime UNKNOWN-pair validator fixture (PF)

> **SCHEMA FIXTURE — not runtime documentation.** Targeted checker fixture.

## Provenance

- **Flow / session:** PF · validator fixture
- **Mapped at:** local fixture state, 2026-09-04
- **Authority:** none; this file certifies the checker only

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| PF-01 | main | an ineligible session is evaluated | `IdlePolicy.evaluate` → `IdlePolicy.is_eligible` → `IdlePolicy._reset` | PASS | `code: src/policy.py resets state when eligibility fails` |

## Cross-flow scenarios

_none_

## Runtime applicability

| profile | effective switches | reachable scenarios | unreachable scenarios | evidence |
|---|---|---|---|---|
| production without live configuration | `UNKNOWN` | UNKNOWN | PF-01 | `code: repository files do not establish this deployed profile` |

## Symbol index

| symbol | file | scenarios | called by | invariants |
|---|---|---|---|---|
| `IdlePolicy.evaluate` | `src/policy.py` | PF-01 | `external: connection-manager sweep` | INV-01 |
| `IdlePolicy.is_eligible` | `src/policy.py` | PF-01 | `IdlePolicy.evaluate` | — |
| `IdlePolicy._reset` | `src/policy.py` | PF-01 | `IdlePolicy.evaluate` | — |

## Invariants

| # | symbol | constraint | breaks if violated |
|---|---|---|---|
| INV-01 | `IdlePolicy.evaluate` | evaluation should run while the connection-manager lock protects session state | concurrent mutation can corrupt the silence decision |

## Call graph

| caller | callee | site | scenarios |
|---|---|---|---|
| `external: connection-manager sweep` | `IdlePolicy.evaluate` | `src/policy.py` | PF-01 |
| `IdlePolicy.evaluate` | `IdlePolicy.is_eligible` | `src/policy.py` | PF-01 |
| `IdlePolicy.evaluate` | `IdlePolicy._reset` | `src/policy.py` | PF-01 |

## Coverage

| file | scenarios | coverage note |
|---|---|---|
| `src/policy.py` | PF-01 | indexed symbols, call sites, and local evidence |

**Verdict distribution:** PASS 1 · UNKNOWN 0 · FAIL 0

## Diagrams

```mermaid
sequenceDiagram
    participant Sweep as Connection-manager sweep
    participant WD as IdlePolicy
    Sweep->>WD: IdlePolicy.evaluate
    WD->>WD: IdlePolicy._reset
```

### Legend — targeted sequence

| participant / node | symbol | file | scenarios |
|---|---|---|---|
| Sweep | `external: connection-manager sweep` | — | PF-01 |
| WD | `IdlePolicy.evaluate`, `IdlePolicy._reset` | `src/policy.py` | PF-01 |
