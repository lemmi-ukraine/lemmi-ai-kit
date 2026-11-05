# Level Assignment — one owning level per case

## Why this is a planning decision, not an implementation one

When the level is decided at implementation time, it gets decided independently by whoever is
writing each part. The same behaviour then ends up automated at several levels at once: a fat base
at every tier instead of a pyramid. The costs are concrete — the same assertion maintained in
three places, a slow suite, and genuine ambiguity about which failing test is authoritative when
they disagree.

The fix is not more coordination later. It is deciding the level **before any test is written**,
which is what this document is for.

## Level names

The project's own testing conventions come first: use the level names the project already uses,
with the seams it allows for faking an external dependency and its rules for waits, deadlines and
required markers, verbatim, so the plan and the suite agree. Where the project ships a language
pack with its own test-type decision table, read it as well, but it applies only where it matches
the code under test: one written for another language never overrides the project's own
conventions.

A pack whose model runs every behaviour test against real dependencies in containers has no unit
level to default down to. Its **profiles** (for example a database-only profile and a full-app
profile) are the levels: default downward means the narrowest profile that can prove the
assertion, and the generic table below does not apply.

Route to the pack **by role, not by name**: "the language pack's testing conventions reference". A
core skill that hardcodes a specific pack skill's name breaks in projects using a different pack or
none, and this repo enforces that with a boundary test.

Where neither the project's conventions nor a matching table names the levels, these generic
levels are a safe default:

| Level | Proves | Cannot prove |
|---|---|---|
| **Unit** | Pure logic, one function or class, no I/O | Anything about wiring, serialization, or persistence |
| **Integration** | A component against its real collaborators — database, queue, adjacent service | Transport-layer concerns: routing, status codes, auth headers |
| **Endpoint / API** | The wire contract — routing, status codes, auth, request and response shape | Deep business-rule branches, which are cheaper one level down |
| **Protocol / streaming** | Connection lifecycle, event ordering, reconnection, cancellation | Anything not observable on the wire |
| **End-to-end** | A whole user journey across real components | Which component broke, when it fails |
| **Manual** | Judgement, look-and-feel, one-off release checks | Anything that needs to run on every change |

## The default-downward rule

Assign the **lowest** level that can actually prove the assertion.

```
Does proving it require a real collaborator (DB, queue, provider)?
  NO  → Unit.
  YES ↓

Is the assertion about the wire contract itself
(status code, auth, request/response shape, routing)?
  YES → Endpoint / API.
  NO  ↓

Is it about connection lifecycle, event ordering, or reconnection?
  YES → Protocol / streaming.
  NO  ↓

Can it be proven against one component plus its collaborators?
  YES → Integration.          ← most cases land here
  NO  ↓

Does it genuinely require the whole system end to end?
  YES → End-to-end, and write the reason on the case.
  NO  → It was Integration. Go back.
```

Moving a case **up** a level requires a written reason on the case. Moving it **down** never does.
The asymmetry is deliberate: upward drift is what produces a brittle, slow suite, and it always
happens one defensible case at a time.

## Stating exclusions

When a case plausibly belongs at more than one level, name what you excluded. One clause is
enough. Silence is indistinguishable from not having considered it.

```
GOOD  TC-07 | Integration | excluded: endpoint (contract already proven by TC-02),
                            e2e (adds no assertion, adds 40s)
BAD   TC-07 | Integration
BAD   TC-07 | Integration, endpoint, e2e     ← this is the failure mode, not thoroughness
```

The exclusion note is also the cheapest defence at review time. A reviewer who disagrees with the
level can say so, because the alternative is written down.

## Cases that legitimately appear twice

Rare, and always deliberate. Two shapes qualify:

1. **A smoke case.** One end-to-end case proving the journey is wired together, whose assertions
   are deliberately shallow because the depth lives at lower levels. Mark it `smoke` so nobody
   later "improves" it by adding detailed assertions.
2. **A contract pinned on both sides.** Where a producer and consumer are tested separately, the
   same shape may be pinned twice by design. Say so on both cases and name the counterpart id.

Anything else at two levels is duplication. If you cannot write which distinct assertion the
second one makes, it does not make one.

## Ownership

Ownership is optional and empty by default.

Fill it only where distinct parties genuinely write the tests at different levels — separate
back-end and front-end teams being the textbook example. Where one team or one agent writes all
of them, the column is ceremony: leave it out rather than filling it with the same name.

An unfilled ownership column is honest. A column filled with a party that does not exist makes the
plan look like a handoff document and invites the reader to wait for someone.

## Style within a level

Style is optional and empty by default, like ownership.

Add a `Style` column to the case table only where a level has more than one test form: plain test
functions beside scenario or feature files, or hand-written tests beside generated or snapshot
ones. A project with one form per level leaves the column and the census line out.

The plan states its placement rule in one sentence: a case goes in the form the repository already
uses for that kind of flow, read from the census, unless the case says why not. A case that departs
from the rule says why on its own row.

The census is one line for the feature and two sibling areas, each counting its tests by form. Take
the counts from a listing command run now, not from memory, and name the command beside the line.

```
Census  (functions, scenarios)  <feature>: 6, 0;  <sibling area>: 4, 11;  <sibling area>: 2, 9
        counted with: <listing command, run today>
Rule    acceptance flows go in feature files, as both siblings do; pure logic stays in functions
```

Without a census a plan labels its cases in the form its author knows, and every review written
against that plan inherits the omission: it checks that the cases are sound, not that their form is
the one CI already runs for that kind of flow. Observed once; the rule is reasoned from that case,
not measured.
