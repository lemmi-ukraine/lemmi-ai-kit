# Reviewing a fix round

Step 5 of the review says to re-run the review over the diff the fixes produced. Three rules say how,
for a round of fixes to a document, plan, rule or report that others will act on, and the third also
for the checks of any change. The first costs only reading order and the third only running order.
The second is one more agent run, so it is kept for a round that rewrote claims.

## 1. Order: the dense spots first, and every new clause against the rest of the document

Review first, and whole, any row or section where one pass applied several findings, and check each
new clause against claims elsewhere in the document.

A fix is usually a general clause, and a general clause is what the rest of the document
contradicts. Findings applied one to a row leave a small diff that is easy to check; findings
applied several at once into one row or section leave the broadest clauses, so that is where the
defects of a fix round tend to concentrate. Read that place whole, because the contradiction sits
in text the diff does not show.

## 2. A fresh reader, given a planted false claim

When a fix round rewrote claims others will act on, a fresh reader runs the re-review: a new agent
that re-derives each claim from the pinned source, not from the artifact's own citations, and is
given one planted false claim to reject.

The agent that applied the fixes reads its own new wording as correct, and a second pass in the same
context inherits that reading. A new agent has the source and the claims to check, not the author's
memory of what each clause was meant to say. Its brief carries at most four real claims, plus the
planted one, so that the extra run stays short. The planted claim (a real claim with one fact
changed, left unmarked) is the control: trust the reader's confirmations only if it rejected the
planted claim, and treat a return that says nothing about it as unverified. Keep the key, which
claim is false, out of the artifact, so that the verdict on the control cannot become an edit.

## 3. Order the checks by cost: the long validation last, once, on frozen files

A fix made after a check voids that check. So run the change's checks from the cheapest to the
dearest, and fix what each one finds before you start the next:

1. lint and format;
2. each claim in the change's documents and in its commit message, against the code, by command;
3. the documentation and count sweeps: stale names, and every number recomputed;
4. the acceptance run;
5. the long validation (the whole suite, the full probe, the whole-tree gate), last and once, on
   frozen files: files that no longer change.

A review fix made after the long validation sends you back to it, which is why the cheap checks
come first. When the validation has finished, compare each touched file's modified time with the
run's start time (`reading-gate-output.md`, section 3).
