# Flow — Cross-flow validator sibling fixture (CS)

> **SCHEMA FIXTURE — not runtime documentation.** Minimal sibling for the cross-document id
> resolution check (`--check crossflow`). Cited by `conformant.md` (as the negative case) and
> by two `probe-crossflow-*` fixtures (as the positive cases); only the two sections the
> loader reads are present.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| CS-01 | main | conformant.md's watchdog evaluation continues on the sibling side | `IdlePolicy.evaluate` | PASS | `code: scripts/fixtures/flow_map/conformant.md supplies the structural fixture path` |

## Cross-flow scenarios

| scenario | owning flow | this document's contribution |
|---|---|---|
| CF-01 | `scripts/fixtures/flow_map/conformant.md` | CS-01 is the sibling side of CF-01's eligible-session evaluation |
