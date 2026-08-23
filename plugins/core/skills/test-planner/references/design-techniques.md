# Test Design Techniques — turning one condition into the right cases

A condition says what must be proven. A technique says how many cases that takes and which ones.
Without a named technique the case count is arbitrary, and arbitrary coverage is the failure mode
that looks most like success — a tidy table of plausible cases that misses the branch that breaks.

Name the technique on every condition. If you cannot name one, you have not analysed the input.

## Selection

Work down this list and stop at the first match.

| Ask | If yes | Technique |
|---|---|---|
| Does the response depend on what happened *before* this input? | State transition | Cases per transition |
| Do several conditions combine into rules with different outcomes? | Decision table | Cases per reachable combination |
| Is the input an ordered range (numeric, date, length, size)? | EP + BVA | Cases per partition and boundary |
| Are there many independent parameters with small value sets? | Pairwise | Cases per covering pair |
| Is it a fixed set of unordered values (enum, boolean, flag)? | Decision table | One per value or rule |

The first question is deliberately first. Event-history dependence is the property people miss,
because a stateful condition reads exactly like a stateless one in a requirements document.

---

## Equivalence Partitioning + Boundary Value Analysis

**Use when** the input has a natural order: a numeric range, a string length, a date window, a
page size, a retry count.

Split the domain into classes that the system should treat identically, then probe the edges —
defects cluster where the comparison operator lives.

**Worked example.** Condition: *"upload size must be between 1 byte and 10 MB"* (cites `AC-05`).

| Partition | Representative | Boundaries |
|---|---|---|
| Below valid | 0 bytes | 0, 1 |
| Valid | 4 MB | 1, 10 485 760 |
| Above valid | 12 MB | 10 485 760, 10 485 761 |

Six cases, and every one is derivable — not chosen. Note the boundary values are the exact
integers, not "about 10 MB": a case that cannot distinguish `<=` from `<` tests nothing.

**Trap.** Applying BVA to something with no order. See below.

---

## Decision Table

**Use when** two or more conditions combine and the outcome depends on the combination — most
permission rules, pricing rules, eligibility rules, and validation cascades.

**Worked example.** Condition: *"only the owner may delete, and only while the record is
unlocked"* (cites `AC-11`).

| # | Is owner | Is locked | Expected |
|---|---|---|---|
| 1 | yes | no | Deleted (`AC-11`) |
| 2 | yes | yes | Rejected, locked (`AC-11`) |
| 3 | no | no | Rejected, forbidden (`AC-12`) |
| 4 | no | yes | Rejected, forbidden (`AC-12`) |

Four rows because two booleans give four combinations. Rows 3 and 4 collapse to one case **only
if** the spec says authorization is checked before lock state — and if it does not say, that is a
requirements gap worth raising, not a judgement call to make silently. The order of the two checks
is observable behaviour.

**Trap.** Collapsing rows to shorten the table hides exactly this kind of ordering question.

---

## State Transition

**Use when** the response to an event depends on prior events. Connection lifecycles, retry and
backoff, session state, upload resumption, anything with an explicit status field.

**Worked example.** Condition: *"a dropped connection resumes without losing buffered events"*
(cites `AC-08`, the resilience answer from the adversarial five).

Enumerate transitions, not states:

| From | Event | To | Case |
|---|---|---|---|
| connected | drop | reconnecting | Buffer retained (`AC-08`) |
| reconnecting | success | connected | Buffered events flushed in order (`AC-08`) |
| reconnecting | timeout | failed | Buffer released, error surfaced (`AC-09`) |
| connected | drop during flush | reconnecting | No duplicate delivery (`AC-08`) |

The last row is the one a case-per-state approach never generates, and it is usually where the
defect is. **Cover the invalid transitions too** — the ones the state machine should refuse. A
state machine that silently accepts an illegal transition fails in production, not in the diagram.

---

## Pairwise

**Use when** several independent parameters each have a small set of values, and the full
cross-product is impractical.

Four parameters with 3 values each is 81 combinations; pairwise covers every *pair* of values in
roughly 9–12 cases. Most combinatorial defects involve two interacting parameters, so this buys
the majority of the value for an eighth of the cases.

**Use it only for genuinely independent parameters.** If the parameters interact through business
rules, the interaction *is* the thing under test — that is a decision table.

---

## Traps

**BVA on unordered input.** Booleans, enums, categorical values and unordered sets have no
boundaries. "The boundary of an enum" is not a concept, and cases built on it are noise that
displaces the rule combinations that matter. Use a decision table.

**One case per requirement.** A requirement is a condition, not a case. A condition that expands
to exactly one case is possible but uncommon; a *document* where every condition expands to
exactly one case means no technique was applied at all.

**Cases that differ only in data.** If three cases share every step and differ only in an input
value, they are one parameterized case. Collapse them and list the values — the requirements
template's own `Scenario Outline` guidance follows the same rule.

**The happy path counted five ways.** Enumerate the valid partitions once. Extra happy-path cases
inflate the count and the perceived coverage without adding a single new assertion.

**Technique named but not applied.** Writing "Decision table" above a list of three ad-hoc cases
is worse than naming nothing, because it claims a rigour the cases do not have. The table has to
be present and its rows have to be the cases.
