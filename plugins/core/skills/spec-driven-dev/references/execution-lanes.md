# Execution Lanes (optional)

> Optional, and untried: the practice is reasoned, not run end to end on a real feature. Treat the
> steps as a starting point. Nothing else in the skill depends on it.

When the approved requirements, design and test plan are enough to write tests without seeing the
implementation, a task may run in two execution lanes. An execution lane is not a review lane: it
decides who writes what, not who checks it.

## The lanes

- **Lane field.** Every task in `tasks.md` carries a Lane field: D (development: writes the
  implementation) or T (tests: written from the requirements, design and test plan only, in new
  files).
- **Disjoint file sets.** The two lanes never edit the same file. A shared helper or fixture file
  belongs to exactly one lane.
- **Contracts first.** The T lane opens by writing each contract the two lanes share (a name, a
  signature, an error, a format) as a question, and the D lane answers every one before its first
  code edit. A practice, not a rule.

## Join gate

Run by whoever owns the plan, after both lanes report. The T lane's tests are new files, so an
export of the pre-feature commit does not hold them: copy them in. Make the export with
`git archive`, which writes a plain tree with no history, and unpack the archive in the scratch
folder (`<scratch>` below; `<start commit>` is the pre-feature commit):

```bash
git archive --format=tar --prefix=pre-feature/ --output=<scratch>/pre-feature.tar <start commit>
```

1. Run only the T lane's tests in `<scratch>/pre-feature`: every one must fail, for the reason the
   test plan gives. A test that passes there proves nothing about the feature: send it back to the
   T lane.
2. Run the same tests on the D lane's tree. Every one must pass.
3. A failure at step 2 is settled against the requirements, never by editing the test to fit the
   code. Record it in the Deviations Log.

## What the split does not do

The split changes who writes the tests, not whose list of properties they come from, so it does
not replace an independent mutation pass or the review.
