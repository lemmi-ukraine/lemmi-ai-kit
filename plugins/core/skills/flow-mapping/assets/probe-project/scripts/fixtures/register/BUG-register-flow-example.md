# Risk register — flow EXAMPLE (fixture, not a real flow)

Conformant fixture for `scripts/validate_register.py` — the shared negative fixture for
every probe pair. Slug `example` resolves against `scripts/fixtures/register/flows/example.md`.

### R-example-01 · a fixture symptom used as the conformant baseline
- **Class:** risk
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** scenario `EX-02` in `docs/flows/example.md`. `code:` fixture only, not a real claim.
- **Verdict:** confirmed.
- **Reconciled against:** `tasks/BUG-register-flow-related.md` documents an unrelated mechanism; cited here only to prove a TRACKED path does not fire the citation check.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-02 · a second fixture symptom, no covering row
- **Class:** bug
- **Severity:** High (fixture rationale)
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** UNKNOWN.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-03 · a Symbol bullet that quotes a WRONG name as its evidence
- **Class:** risk
- **Severity:** Low (fixture rationale)
- **Symbol:** `JobSession.finish` in `src/session.py`, cited in that module's own docstring as `JobSession._finish_phantom`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**
