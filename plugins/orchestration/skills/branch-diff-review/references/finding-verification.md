# Per-Finding Verification Checklist

Run this against **every** finding before it reaches the report.

The items below are split into two classes, and **the split is the point**. Only Part A items produce
external output, so only Part A items may move a severity. Part B items are genuine judgment with no
oracle; they can *raise* a concern but never *settle* one.

| | Part A — tool-grounded | Part B — judgment-only |
|---|---|---|
| Produces | a command/read and its output | an argument |
| May change severity? | **yes**, citing the output | **no** — severity frozen |
| Confidence ceiling | `CONFIRMED` | `PLAUSIBLE` |

**The governing rule:** severity may change only as the mechanical consequence of a recorded output
from a Part A check. A Part A check you could not run, and every Part B item, leaves severity untouched
and caps confidence at `PLAUSIBLE`.

**Why the split exists (do not remove it).** An earlier version of this file claimed *every* item was
"an operation with an output", which was false: items B1–B3 below have no external feedback, and the
Phase 6 content review caught the contradiction. That mattered because the permission to run this pass
at all rests on the distinction between tool-grounded verification and intrinsic self-judgement (see
`SKILL.md` § "The one thing to read before running this"). A judgment item running under the
verification banner **is** the banned operation. Note the sting: **B1 is the least tool-grounded item
here and it is the one that produced the source run's top-severity finding.** Judgment is not
worthless — it is just not verification, and it must not move a number.

---

## Provenance and blind spot

**Every item comes from one review** (2026-08-13, `tasks/TECH-interview-stabilization-review.md`).

That provenance is also the limitation, and it is a documented failure mode of checklist inspection: a
checklist inherits the defect distribution it was built from, so **it is structurally blind to failure
modes that one run did not exhibit.** Hence item B3 (unclassified), and hence: when a run surfaces a
new mode, add it here with its instance and its class.

**On the 19→7 figure — do not cite it as proof.** It is one self-assessed sample: the same agent raised
the 19 and reduced them to 7. This repo measured the *opposite* architecture once —
`tasks/TECH-pr394-jobs-sse-review.md` used an independent adversarial verifier and changed **1 of 40**.
Two readings, and n=1 each cannot distinguish them: either the checklist overcame self-preference bias,
**or** the self-review over-corrected while the independent verifier rubber-stamped. Which is better
calibrated is **UNKNOWN**. What justifies this pass is the *mechanism* — Part A checks with outputs —
not the ratio. (The source doc's own decomposition does not sum: 7 held + 7 downgraded + 2 retracted +
1 escalated = 17, not 19. Two findings are unaccounted for. Recompute your own counts from the table
at write time; see A5.)

---

## Part A — tool-grounded (may move severity)

## A1. Can you construct the trigger?

Write the concrete input or state producing the wrong output, and try to build it.

- **Record:** the construction, or exactly where it fails.
- **Consequence:** not constructible → severity **unchanged**, confidence `PLAUSIBLE`, and write
  "reachability UNKNOWN, not demonstrated".
- **Instance:** a worker-death hang was called "reachable" and the path could not be built. The real
  finding was a docstring claiming a guard that does not exist.

## A2. Did you measure the before-state as rigorously as the after-state?

Any claim that a change *worsens* something needs both numbers.

- **Record:** before figure, after figure, and how each was obtained.
- **Instance:** "probable → certain" was wrong — the prior behaviour was already certain, so the change
  moved the *depth* of an overlap, not its likelihood. Mechanism survived; severity framing did not.

## A3. Read the comment next to the number

Before doing arithmetic on a configured value, read its adjacent comment and description.

- **Instance:** `--concurrency 80` became a 2.56 GB memory claim. The line above it reads "concurrency
  is purely a placement cap". The number was in the file; so was the reason not to multiply it.

## A4. Never assert an absence without searching for it

"Nothing enforces this", "no test covers this", "this is unowned" each require a search.

- **Where:** `parallel-session-safety` § 7 owns this rule and names the surfaces — including that
  `.ai/handoffs/` is **gitignored**, so no code grep or `git log` reaches it.
- **Instance:** "nothing enforces the merge-order constraint" shipped while a `ready-for-review`
  handoff owned exactly that work.

## A5. Sweep by class, not by string — and recompute every count at write time

Once you have one instance, search for its **category**, varying the phrasing. Then recompute any
number you are about to write, from the artifact rather than from memory.

- **Record:** the pattern used **and its scope/exclusions**, plus three numbers — expected, actually
  carrying it, found outside your list.
- **Instance (this task, four times):** a step-count sweep grepped `"8-step"` and reported clean while
  `"8 steps"` and `"steps 1–6"` were stale — 7 → 12 → 21 occurrences across three widening passes. Then
  a citation count went 22 → 32 → 84 across three passes, and a directory count "~70" measured 81. A
  bare number without its measurement scope is the defect; write the command beside the figure.

## A6. Is this pre-existing, or introduced by the change?

`git log -S"<symbol>"`, or read the base revision with **`git show <base>:<path>`** — never
`git stash`/`git checkout`/`git restore`, which mutate a working tree other sessions may be using.

- **Consequence:** pre-existing → keep the finding, relabel it, name the revision that introduced it.

## A7. Flip the assertion and run the test

Where a test asserts the behaviour your finding disputes, invert the assertion and run it
(`pytest -k <test>`), or run the test against the fix. Record pass/fail.

- **Why this is Part A:** the runner is the oracle. Reasoning about what a test *would* do is B2.
- **Instance:** an eviction test asserted `cleanup_calls == 1`, encoding the very finalize-on-eviction
  behaviour that became the run's top finding. It passed, and the behaviour was wrong.

---

## Part B — judgment-only (severity frozen, confidence caps at `PLAUSIBLE`)

These are where the real defects hide, and where you have no oracle. Raise them, argue them, anchor
them — but do not let them move a number, and never label their output `CONFIRMED`.

## B1. For a claim spanning two changes, trace both

The source run's top-severity finding existed in **neither** diff: it emerged from parking deferring
teardown *and* delivery rerouting by interview id. Each change was correct alone.

- **Do:** when two workstreams touched one lifecycle, enumerate the **state pairs**, not the file lists.
- **Record:** both anchors (grep-able — that part is Part A evidence) and the specific pair that
  composes badly (judgment — that part is not).
- **Escalation route:** if a pair can be turned into a constructible trigger, it becomes A1 and *then*
  may move severity. That conversion is the highest-value work in this checklist.

## B2. Does a test assert the opposite — and what would the right test look like?

A test asserting current behaviour is not evidence the behaviour is correct.

- **Ask:** what would this test look like if the opposite were correct?
- **Note:** this is the reasoning half; A7 is the executable half. If you can run it, run it and use A7.

## B3. Unclassified concern (deliberate escape hatch)

A concern matching no item above is recorded as `unclassified` with whatever evidence exists, rather
than dropped. This slot exists because A1–A7 and B1–B2 came from one run and cannot cover what that run
did not hit. An unclassified concern with a real anchor is worth more than a forced fit.

---

## What a completed verification row looks like

```
F5 — Major, CONFIRMED.
  A1 (construct trigger): drain timeout with 2 queued units; _extract_track_segments maps the
    i-th append_audio to the i-th timeline pair (audio_storage_service.py:575-576, re-grepped)
    → a dropped unit shifts every later segment. Constructed.
  A6 (pre-existing?): git log -S"turn_byte_lengths" → mapping predates this branch; the
    time-based trigger does not. Relabelled: new trigger, pre-existing failure class.
  A5 (sweep by class): grepped positional list<->list pairings in the module, scope = that file
    only → 1 more (turn_durations_ms), noted inline.
```

Three Part A checks, three outputs, a severity a later reader can re-derive. Contrast:

```
F5 — Major (seems serious).
```

Unfalsifiable, and if its severity ever moved on that basis it would be the banned re-rating.

And a Part B row, correctly capped:

```
F1 — Major, PLAUSIBLE.
  B1 (two-change trace): one change defers teardown (<OID-a>) + another reroutes delivery by
    id (<OID-b>); both anchors re-grepped. The composing pair is EVICTED-outcome x
    reroute-target. Severity NOT moved by this item — judgment only.
  A1 attempted: could not construct end-to-end without a live socket pair. Reachability
    argued, not demonstrated.
```

Note what did *not* happen: B1 did not promote F1 to Blocker. Only re-resolution against a new SHA
did — which is an A-class output (see `SKILL.md` § Step 5).
