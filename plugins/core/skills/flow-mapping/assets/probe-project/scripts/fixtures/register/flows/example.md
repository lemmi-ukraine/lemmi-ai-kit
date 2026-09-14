# Flow: example (fixture, not a real flow document)

Fixture sibling flow document for `scripts/validate_register.py`. Used only so the
`Observed:` resolution check and the corpus join can run self-contained, without ever
reading the real `docs/flows/` during probes.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| EX-01 | main | `external: fixture trigger` | `JobSession.finish` | PASS | `code: fixture only, not a real claim` |
| EX-02 | edge | `external: fixture trigger` | `JobSession.finish` | FAIL | `code: fixture only, not a real claim` |
| EX-03 | edge | `external: fixture trigger` | `JobSession.finish` | UNKNOWN | `code: fixture only, not a real claim` |
