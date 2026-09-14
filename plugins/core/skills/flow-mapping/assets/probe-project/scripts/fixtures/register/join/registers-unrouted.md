# Risk register — join probe fixture (unrouted case)

Only EX-02 (FAIL) is mentioned below; EX-03 (UNKNOWN, from
`scripts/fixtures/register/flows/example.md`) is mentioned nowhere in this file, so the
corpus join over this pair must report exactly one unrouted id. Used as the join check's
positive fixture.

### R-example-join-unrouted-01 · fixture entry that mentions only one non-PASS scenario
- **Class:** risk
- **Severity:** Low
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** scenario `EX-02` in `docs/flows/example.md`.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**
