<!-- handoff-contract: v3 -->
# Hand-off: {slug}

<!--
STUB, the first write of a delegated session: create this file at the hand-off path the brief names,
before any precondition, with an operation that fails if the path exists. Keep line 1. Replace each
example value from the brief. `Task:` is the slug of that path, its file name between the date and
`.md` (or `--{part}`, when it has one). `Sessions:` copies the ids of every note of this task you were
given, then ends with your own id, the name of the folder that holds your scratchpad, which `Written:`
names too. A failed precondition sets Status to `blocked`, with the reason after a dash. The seeded
hand-off template shows every section and ledger line in full.
-->

Task: example-task
Sessions: example-session-id
Written: 2026-01-01 09:00 by example-session-id
Lessons: not run - not started
Delegation: none, because not started
Safe to close: no - not started

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
