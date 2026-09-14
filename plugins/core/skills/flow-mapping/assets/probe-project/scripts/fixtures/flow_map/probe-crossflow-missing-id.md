# Flow — Cross-document id resolution probe: missing id (PM)

> **SCHEMA FIXTURE — targeted checker fixture.** One planted defect: the cross-flow row
> below cites a scenario id absent from its named owning flow. `--check crossflow` must
> report exactly one finding.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| PM-01 | main | an ineligible session is evaluated | `IdlePolicy.evaluate` | PASS | `code: src/policy.py resets state when eligibility fails` |

## Cross-flow scenarios

| scenario | owning flow | this document's contribution |
|---|---|---|
| ZZ-99 | `scripts/fixtures/flow_map/crossflow_sibling.md` | the planted defect: ZZ-99 does not exist in the cited sibling |
