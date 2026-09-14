# Flow — Cross-document id resolution: wrong-but-existing id WITH a doc-level back-pointer (PD)

> **SCHEMA FIXTURE — demonstrates a KNOWN LIMIT, not a probe pair.** The cross-flow row
> below cites a real scenario row of its named owning flow that describes a different
> mechanism -- the same defect class as `probe-crossflow-wrong-id-no-backpointer.md` -- but
> the sibling's own Cross-flow scenarios table happens to carry a row back into this
> document (naming a different row than the one that cites CD-01). Existence passes and
> reciprocity reads doc-level, so `--check crossflow` reports ZERO findings here: this is
> the limit recorded in a comment beside `PROBE_CASES` in `validate_flow_map.py`, not a
> defect in the check. Exercised by neither `PROBE_CASES` nor `--probe-stamps`.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| PD-01 | main | an ineligible session is evaluated | `IdlePolicy.evaluate` | PASS | `code: src/policy.py resets state when eligibility fails` |

## Cross-flow scenarios

| scenario | owning flow | this document's contribution |
|---|---|---|
| CD-01 | `scripts/fixtures/flow_map/crossflow_sibling_doclevel.md` | a scenario that exists on the sibling side but describes an unrelated boundary condition |
