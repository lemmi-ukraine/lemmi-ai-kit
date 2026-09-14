# Comments — Edit-Time Invariants Only

A comment earns its place by telling whoever edits **this line** what they need in order not to break
it. Everything else has a better home, and moving it there is not optional: scenario and flow facts to
the subsystem's flow document, environment-variable provenance to the env reference, subsystem
mechanism to the module README, provider behaviour to the provider-quirks reference your project keeps.
**Write the destination first, in the same commit, then cut** — no comment is deleted while it holds
the only copy of a fact.

Exactly four things clear that bar. One shape each; the wording is the tell:

| Clears the bar | Shape of the comment |
|---|---|
| an **ordering constraint** | *"Count the attempt up-front so a failing reconfigure still advances the cap"* — the line's position relative to another line is the invariant |
| a **counter-intuitive invariant** a plausible edit would break | *"the framework pins `client_state` at CONNECTED once the peer vanishes, so a `client_state`-only check calls a dead socket OPEN for the life of the process"* — the obvious simplification is the bug |
| a **non-obvious external behaviour** | *"the faulted cohort still sent 151–531 bytes of control frames — and they refresh `last_inbound_at`, so a timestamp-only check cannot see the fault"* — a fact about the other side of a boundary that no test in this repo can reproduce |
| a **why-not** for the obvious rejected alternative, one line | *"Rebind rather than clear in place: nothing else holds a reference to the list"*. A one-line justification beside a deliberately tolerated lint suppression (`# noqa: <code> — <why>`) is this category, and is never cut |

**Security prose is KEEP by default** — anything naming auth, ownership, tenancy or data exposure
stays regardless of length or duplication, because a comment describing a data-exposure consequence
is evidence the hole is OPEN, not that it is handled. If the hazard is unfixed it also gets a
`tasks/` row; it is never a bare delete.

**A comment the code contradicts is corrected or cut — never left, never silently deleted.** A
density trim is the wrong instrument for it: wrongness and verbosity are uncorrelated, so cutting by
volume removes the accurate comments first. Replace the false clause — appending a correction beneath
it leaves the block self-contradictory — and expect the correction to **add** lines, which is the
right outcome. Measured in one seven-document documentation pass, stale comments were the largest
defect class: **23 of 130** register entries.

**Superseded-design narration is cut first** — actively misleading rather than merely verbose,
because an agent solves the old problem while the code still explains the old problem. The forms:
`previously…`, `the old version…`, `restores the pre-fix behaviour`, review-finding ids used as
justification (`(review B-F6)`), git-archaeology pointers (`recoverable from commit <sha>`). Git
already holds all of it.

**Never cite a line number from a comment; cite the symbol.** Line citations decay inside the
session that writes them: one pass wrote a register citing code by line, then ran its comment pass
over that same code and staled **14 of its own 40** citations. The worst case it found was a comment
citing `_handle_response_canceled (1504-1506)` into a file 1,082 lines long — and that comment was the
symbol's only occurrence in the whole tree, so cutting it took the last trace with it. Before cutting
a comment as a duplicate, grep its distinctive token tree-wide and require a second hit; a file whose
still-correct line citations point INTO it is a reason to skip that file, not to cut.

Running a pass over code that already exists is a different job — seven verdicts, a token-grep gate
on every cut-as-duplicate, a negative control, and a no-code-change gate (`changed=0`) as its exit
criterion: the `initiative-cleanup` skill's `references/comment-pass.md`.
