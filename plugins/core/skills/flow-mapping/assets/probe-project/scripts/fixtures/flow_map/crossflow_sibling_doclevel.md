# Flow — Cross-flow validator doc-level sibling fixture (CD)

> **SCHEMA FIXTURE — not runtime documentation.** Minimal sibling demonstrating the KNOWN
> LIMIT recorded in a comment beside `PROBE_CASES` in `validate_flow_map.py`: a doc-level
> back-pointer (this document's own row below names PD-01, but describes a scenario
> unrelated to the one that cites CD-01) is indistinguishable from a correct one at the
> existence level.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| CD-01 | main | an unrelated boundary condition on the sibling side | `IdlePolicy.evaluate` | PASS | `code: scripts/fixtures/flow_map/probe-crossflow-wrong-id-doclevel.md supplies the structural fixture path` |

## Cross-flow scenarios

| scenario | owning flow | this document's contribution |
|---|---|---|
| PD-01 | `scripts/fixtures/flow_map/probe-crossflow-wrong-id-doclevel.md` | a back-pointer that exists but names a different row than the one that cites CD-01 |
