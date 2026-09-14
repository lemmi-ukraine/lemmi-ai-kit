# Risk register — join probe fixture (routed case)

Both non-PASS scenarios from `scripts/fixtures/register/flows/example.md` (EX-02 FAIL,
EX-03 UNKNOWN) are mentioned below, so the corpus join over this pair must report zero
unrouted ids. Used as the join check's negative fixture.

### R-example-join-routed-01 · fixture entry that mentions both non-PASS scenarios
- **Class:** risk
- **Severity:** Low
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** scenario `EX-02` in `docs/flows/example.md`; the related UNKNOWN case is `EX-03`.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**
