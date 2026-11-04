<!-- handoff-contract: v2 -->
# Hand-off: {slug}

<!--
STUB, the first write of a delegated session: create this file at the hand-off path the brief names,
before any precondition, with an operation that fails if the path exists. Keep line 1. Replace each
example value from the brief. A failed precondition sets Status to `blocked`, with the reason after a
dash. The seeded hand-off template shows every section in full.
-->

## Scope
- **In (may change):** the slice the brief names

## Durable anchors
- Branch and commit: `chore/example-branch` at `abc1234`

## Preconditions
- `git rev-parse --abbrev-ref HEAD` -> `chore/example-branch`

## Verification
- `<the brief's definition-of-done command>` -> <its expected result>

## Status
**Status:** in-progress - not started

## Continue
Not started. A new session reads the brief that named this path and begins there.

## Orchestrator summary
Not started: this file only holds the path for the session that wrote it.
