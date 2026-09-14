# Risk register — flow SIBLING-CITE (fixture, not a real flow)

Positive fixture for roadmap item 35: the `observed` rule must NOT accept a scenario id that
occurs only inside a **sibling register entry id**. The entry below cites `R-QC-05` and no
scenario, and its flows document (`scripts/fixtures/register/flows/siblingcite.md`) really does
carry `QC-05` — so before the fix `SCENARIO_ID_SEARCH_RE` pulled `QC-05` out of `R-QC-05`,
resolved it, and reported nothing. Expected after the fix: exactly one `observed` finding, and
nothing else. Every other bullet here is deliberately conformant so the count stays 1.

### R-siblingcite-01 · Observed cites a sibling entry id and no scenario
- **Class:** risk
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** covered by `R-QC-05`, which is a sibling REGISTER ENTRY id, not a scenario id. Nothing here names a scenario row, and the entry deliberately omits the literal escape hatch, so the rule must fire.
- **Verdict:** confirmed.
- **Reconciled against:** `tasks/BUG-register-flow-related.md` — cited only to keep a TRACKED path in the bullet, as the conformant fixture does.
- **Provenance:** confirmed (author)
- **No fix proposed.**
