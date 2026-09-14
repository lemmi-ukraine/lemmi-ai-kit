# Risk register — flow EXAMPLE-BAD (fixture, not a real flow)

Nonconformant fixture for `scripts/validate_register.py`. Each entry violates exactly one
rule; every other field in that entry is otherwise conformant so `--check <rule>` isolates
an exact count. Slug `example-bad` (no matching flows/ fixture is needed: the one entry that
tests Observed-resolution deliberately cites an id that cannot resolve anywhere).

### R-SA-01 · wrong heading id for this file's slug
- **Class:** bug
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-02 · missing the Provenance bullet
- **Class:** bug
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **No fix proposed.**

### R-example-bad-03 · Severity bullet duplicated
- **Class:** bug
- **Severity:** Medium
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-04 · Severity value has no accepted rationale shape
- **Class:** bug
- **Severity:** High if reachable
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-05 · Class value is not one of the five
- **Class:** confirmed-bug
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-06 · Observed names an id that resolves nowhere
- **Class:** bug
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** scenario `EX-99` in `docs/flows/example-bad.md`. No such id exists anywhere in this fixture corpus.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-07 · Reconciled-against cites an untracked tasks path
- **Class:** bug
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** `tasks/BUG-does-not-exist-anywhere.md` is the nearest doc, but it is not tracked.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-08 · a path:NN citation instead of an entry id
- **Class:** bug
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** see `src/session.py:42` for context, not an entry id.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-09 · a backticked path followed by "line NN" instead of an entry id
- **Class:** bug
- **Severity:** Medium
- **Symbol:** `JobSession.finish` in `src/session.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** described in `docs/flows/turn-lifecycle.md` at line 42 of that document, not an entry id.
- **Provenance:** confirmed (author)
- **No fix proposed.**

### R-example-bad-10 · Symbol does not resolve against the code index
- **Class:** bug
- **Severity:** Medium
- **Symbol:** `FixtureExample.does_not_exist_anywhere` in `src/nonexistent_fixture_module.py`
- **Observed:** **no covering row** — fixture entry, not applicable to any scenario.
- **Verdict:** confirmed.
- **Reconciled against:** none found by symbol grep.
- **Provenance:** confirmed (author)
- **No fix proposed.**
