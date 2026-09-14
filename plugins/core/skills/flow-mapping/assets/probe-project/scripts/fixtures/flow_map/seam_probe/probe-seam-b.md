# Flow — Seam-detector probe corpus, side B (QB)

> **SCHEMA FIXTURE — not runtime documentation, and not a flow map of anything real.** The sibling
> half of `probe-seam-a.md`; that document carries the `EXPECTED` table and the two invariants a
> future edit must preserve. Read it before changing a cell here.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| QB-01 | main | the fixture's absent-seam symbol runs on this side | `ProbeAbsentSeam.sweep_only` | PASS | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-a.md maps the same symbol with no row between the two` |
| QB-02 | main | the fixture's prose-linked symbol runs on this side | `ProbeNamedInProse.cell_names_me` | PASS | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-b.md names this symbol in full in the contribution cell below` |
| QB-03 | main | the fixture's row-level-linked symbol runs on this side | `ProbeRowLevelOnly.target_id_links_me` | PASS | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-a.md hosts a row targeting QB-03 without naming this symbol` |
| QB-04 | edge | the disagreeing symbol is unestablished on this side | `ProbeVerdictSplit.fail_here_unknown_there` | UNKNOWN | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-a.md records FAIL for the same symbol, which is the disagreement under test` |
| QB-05 | edge | the agreeing symbol passes on this side | `ProbeVerdictAgree.fail_here_pass_there` | PASS | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-a.md records FAIL for the same symbol; a bare PASS is deliberately not a disagreement` |

## Symbol index

| symbol | file | scenarios | called by | invariants |
|---|---|---|---|---|
| `ProbeAbsentSeam.sweep_only` | `scripts/fixtures/flow_map/seam_probe/probe-seam-b.md` | QB-01 | _none_ | _none_ |
| `ProbeNamedInProse.cell_names_me` | `scripts/fixtures/flow_map/seam_probe/probe-seam-b.md` | QB-02 | _none_ | _none_ |
| `ProbeRowLevelOnly.target_id_links_me` | `scripts/fixtures/flow_map/seam_probe/probe-seam-b.md` | QB-03 | _none_ | _none_ |
| `ProbeVerdictSplit.fail_here_unknown_there` | `scripts/fixtures/flow_map/seam_probe/probe-seam-b.md` | QB-04 | _none_ | _none_ |
| `ProbeVerdictAgree.fail_here_pass_there` | `scripts/fixtures/flow_map/seam_probe/probe-seam-b.md` | QB-05 | _none_ | _none_ |

## Cross-flow scenarios

| scenario | owning flow | this document's contribution |
|---|---|---|
| QA-05 | `scripts/fixtures/flow_map/seam_probe/probe-seam-a.md` | `ProbeNamedInProse.cell_names_me` is named here, in full dotted form, and that is the ONLY thing linking it across this pair — this row's own target id, QA-05, belongs to a different symbol on purpose, so the prose path is what the known-negative probe tests. Do not retarget this row at QA-02. |
