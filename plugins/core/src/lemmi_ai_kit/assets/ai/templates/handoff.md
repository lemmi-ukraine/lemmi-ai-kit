<!-- handoff-contract: v2 -->
# Hand-off: {slug}

<!--
HOW TO USE (delete this comment and every instruction line before you hand over)
- Copy to `.ai/handoffs/{YYYY-MM-DD}-{slug}.md`: the date is the day you write it. Keep line 1, the version label, as it is.
- This folder is gitignored and never committed: a hand-off is a POINTER. A fact that must outlive it goes to git (a task file,
  a doc, a code comment), the learnings buffer or a memory note, and is only NAMED here. Never paste a credential or token.
- Write a figure with the time you measured it; the receiver re-derives it. Preconditions and Verification are commands with
  `-> expected result`, never prose.
- Status is one of `in-progress`, `blocked` or `ready-for-review`, then text after a dash. A note nobody has started reads
  `in-progress - not started`; work stays `ready-for-review` until the reader has run Verification, never "done".
- Check it before you hand over: run the support CLI's hand-off lint (`lint handoffs <this file>`) on this one file -> LINT PASSED.
- Optional sections go after the last required one: Error history and Files changed (see the end).
-->

Written: {YYYY-MM-DD HH:MM local} by {session id or window name}

## Scope
- **In (may change):** {the one slice, and the files or folders it may touch}
- **Not in (must not change):** {what this does not cover: files, repositories, decisions that stay untouched}
- **Rules:** {path of the shared rules file for this work, if any; reference it, do not copy it}

## Durable anchors
- Branch and commit: `chore/example-branch` at `abc1234`
- Read first, in this order: `docs/example.md`, `.ai/handoffs/2026-01-01-example.md`
- Where the results live: `docs/example-results.md`

## Preconditions
- `git rev-parse --abbrev-ref HEAD` -> `chore/example-branch`
- `git status --porcelain` -> save it as the start snapshot; lines already there belong to someone else

## Verification
- `<command that proves one claim of this hand-off>` -> <the expected result, with its exit code>
- `<second command>` -> <result>

## Status
**Status:** in-progress

- Gates, one line each, including the ones not run: `<gate>` done, evidence `<path or command>` | NOT run, because <reason>
- **Not done:** <every item left over, with its owner; a commit, the lessons, the review or the close left to the next reader is listed here by name, never implied>
- Blocked on: <a decision or an event, if any>

## Continue
Paste into a NEW session opened in `<folder>`: `Read <absolute path of this file> and follow it.`
Next step: <one sentence>. Stop at <where the receiver stops and reports, by reference to the one file that holds that rule>.

## Orchestrator summary
<At most 10 plain lines for the reader who will not open the rest: what was done, what was found, what is open, what the reader decides. No table, no ids, no jargon.>

<!--
OPTIONAL SECTIONS (copy the ones you need above this comment)

## Error history
- <what went wrong, what it cost, what fixed it; one line each>

## Files changed
- `<path>` <time> <what changed>
-->
