# Claim boundaries — four ways correct reasoning produced a wrong conclusion

Every case here was **right about everything it examined**. That is what makes the family dangerous:
re-reading the reasoning *confirms* it, so a second pass over the same material can never falsify it.
Only enumerating the thing that was never examined does.

None of these is a carelessness failure. Each was produced by a careful pass.

---

## 1. "A and B are impossible, therefore C" is only sound if A, B, C is the COMPLETE set

**Measured.** A new refusal helper needed a home. `endpoints.py` imports `reconnection.py`, so
hosting it in either creates an import cycle — **true**. The conclusion drawn was that a standalone
module was necessary, and one was written, with a docstring explaining the cycle as its
justification.

There was a third candidate that was never enumerated: `lifecycle.py` is imported by **both** routes
and imports neither, so it had no cycle at all — and "close a socket after telling the client why" is
connection lifecycle, which that class already owns. The operator caught it in review with one
question: *"why is it not part of a class?"* **The fix deleted a file rather than adding one.**

> Whenever a constraint eliminates candidates, **write the candidate list down before concluding**,
> and say how you know it is complete. For import-cycle questions the mechanical version is cheap:
> for each module both callers already import, check whether it imports either caller back.

Generalises past imports to any *"X is impossible, so I built Y"* reasoning. The sentence is only as
strong as the enumeration behind it, and **a justification that survives re-reading is not thereby a
complete one.**

## 2. Two independent derivations agreeing confirms the CLAIM, not its SCOPE

**Measured.** A layer was dispatched with a hard instruction: two reviews had
independently derived that one of the algorithm's inputs was process-local, so *"treat it as fact
and not as a question to re-open"*. Both derivations were correct. The instruction to trust them was
right.

Both examined **the value that prompted the question** and neither enumerated the algorithm's other
inputs. The consuming function takes **three** things per stream — the payload, the event anchors,
and the segment lengths — and **two** were missing, not one:

- the anchors lived on an in-memory service attribute that the handover object does not carry,
  reaching disk only at finalize — so a takeover discards the entire pre-drop timeline;
- restarting the timer re-origins the clock at the takeover instant, persisted in no column.

Those matter **more** than the segment lengths — anchors decide *where* a slice goes, lengths only
how long it is. And the second review's proposed escape hatch (*"reconstruct it from the per-item
object sizes, which is available"*) was itself unreachable: the storage protocol has **no listing
operation at all**.

> When a dispatch pins a finding as confirmed-by-two-sources, trust the finding and **still enumerate
> the consumer's full input set yourself**. The cheap mechanical version: open the function the work
> must satisfy and list its parameters *before* reading any review about it.

Independent agreement raises confidence in a proposition and says nothing about whether the
proposition is the whole question. **A review's suggested remedy is a claim too** — "available" was
asserted about a capability that does not exist.

## 3. A stated limitation that would change the conclusion must gate it, not merely accompany it

**Measured.** A cohort result was computed on an extracted numeric field present on **40%** of
records. The report stated that coverage explicitly — and still made the result its headline, and
carried it into a request document sent to **another team**.

That team's reviewer replied with exactly that objection: the field is sparse, and only **5 of 22**
records in the cohort driving the finding carried it. Re-measured with a 93%-coverage estimator, the
effect **collapsed from ~1.6 to ~0.4 and reversed direction** in the clean cohort.

The caveat was present, accurate, and adjacent to the claim — and it changed nothing about how the
claim was weighted or where it travelled. **An external reviewer applied my own stated number against
me, which is the tell that the number was decorative in my hands.**

> Writing a limitation down is cheap and feels like rigour. It is not the same as letting the
> limitation gate the confidence language, the headline position, or the decision to publish. If a
> result rests on a partially-covered field, check that field's coverage **inside the subgroup
> driving the finding** and put THAT number in the headline sentence, not the overall one.

A caveat beside a bold claim is read as a footnote by every downstream consumer — including the ones
who forward it.

## 4. A suite failure localises itself; do not generalise it onto a different surface

**Measured.** The unit suite reported a `NameError` and an `ImportError` raised by another
session's in-flight edits. The conclusion drawn was *"the checkout does not import"* — so the
mandated service restart was recorded as **blocked**, and that reason was written into the result
hand-off as a fact for the next reader.

Every one of those errors was raised while pytest **COLLECTED a test module**, and every module it
named lived under `tests/`. **Not one came from the application package.** The one-line check never
run:

```bash
python -c "import <the app's entry module>"    # exit 0, and it did
```

The restart was never blocked, and the hand-off would have told the next session *"do not restart,
the tree is broken"* — an instruction manufactured from an inference, in the exact slot the contract
reserves for **verified state**. The tell was in the output all along: pytest prints
`ERROR collecting <path>` and names the importing module, and every path it named was under `tests/`.

> Before converting suite output into a claim about a **different** surface — the app imports, the
> container will boot, the migration will run — run that surface's own one-line check. They are
> seconds each.

**And note which row this was.** *"Blocked"* in a step inventory is the state most likely to be
inferred rather than measured, **because it is the row that excuses you from doing the work.** It
needs its evidence command attached at the moment it is written.

---

## The common guard

Three of the four were produced by a pass that was internally sound. So the question that catches
this family is not *"is my reasoning correct?"* — it was, every time — but:

**"What did I not look at, and how do I know the list is complete?"**

Write the enumeration down next to the conclusion. If you cannot say how you know it is exhaustive,
the conclusion is a hypothesis wearing a conclusion's grammar.
