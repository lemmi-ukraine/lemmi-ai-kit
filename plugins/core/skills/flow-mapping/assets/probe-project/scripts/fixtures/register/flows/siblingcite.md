# Flow — SIBLING-CITE fixture (QC)

> **SCHEMA FIXTURE — not runtime documentation.** The flows side of
> `BUG-register-flow-siblingcite.md`, whose single entry cites the sibling register entry
> `R-QC-05` and nothing else. The scenario id `QC-05` below is the whole point of this file: it
> makes the collision REAL, so that before the fix the `observed` rule extracted `QC-05` out of
> `R-QC-05` and resolved it here, staying silent on an entry that cites no scenario at all. A
> fixture without a colliding id would prove nothing — the rule would have reported the entry for
> the ordinary reason (an id that resolves nowhere) and the probe would pass either way.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| QC-05 | main | the id whose digits a sibling entry id `R-QC-05` reproduces | `JobSession.finish` | PASS | `code: scripts/fixtures/register/BUG-register-flow-siblingcite.md cites R-QC-05, not this row` |
| QC-06 | edge | a second row, so the table is not a single-row degenerate case | `JobSession.finish` | PASS | `code: scripts/fixtures/register/flows/siblingcite.md fixture padding, not a real claim` |

## Symbol index

| symbol | file | scenarios | called by | invariants |
|---|---|---|---|---|
| `JobSession.finish` | `src/session.py` | QC-05, QC-06 | _none_ | _none_ |
