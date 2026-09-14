# Flow — Cross-document id resolution probe: wrong-but-existing id, no back-pointer (PW)

> **SCHEMA FIXTURE — targeted checker fixture.** One planted defect: the cross-flow row
> below cites a real scenario row of its named owning flow, but one that describes a
> different mechanism, and the sibling carries no row back into this document.
> `--check crossflow` must report exactly one finding (reciprocity: none).

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| PW-01 | main | an ineligible session is evaluated | `IdlePolicy.evaluate` | PASS | `code: src/policy.py resets state when eligibility fails` |

## Cross-flow scenarios

| scenario | owning flow | this document's contribution |
|---|---|---|
| CS-01 | `scripts/fixtures/flow_map/crossflow_sibling.md` | the planted defect: CS-01 is real but describes the conformant fixture's watchdog, unrelated to PW-01 |
