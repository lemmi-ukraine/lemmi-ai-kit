# Evidence and closing rules

## Durable citations

- Cite tracked content at the stated revision, a pinned package, or a dated artifact
  with a hash. A tracked file can still contain uncommitted evidence: verify the
  cited content at the pin, not just `git ls-files` membership.
- `test:` needs the actual assertion and test name. Opening a test file does not
  establish which input, execution shape and outcome it checks.
- `provider-doc:` names the relevant version. Current upstream main can describe
  behavior absent from the installed dependency. Retrieve official sources for
  provider facts and distinguish inference from execution.
- `log:` states the measurement window, population and available fields. Missing
  logging cannot prove an event never happened. If a claim is retracted, sweep its
  numbers and reworded variants through every destination, including corrections.
- Resolve dotted symbols at write time. A line number recalled from an earlier
  read is not evidence. A cache key describes internal partitioning, not its
  owner's lifetime; inspect construction, retention and disposal paths separately.
- Read cross-flow target rows and their triggers, both directions. Existing IDs
  can point at the wrong scenario. Check IDs in prose as well as table cells.
- Derive counts from explicit populations. State qualifiers in the selection and
  count excluded/complement sets separately. A detector-selected population cannot
  prove absence outside that detector's coverage. Probe new checkers with known
  positives and negatives before interpreting a zero.

## What automation does not prove

The validator checks required table shapes, selected symbol/file references,
scenario joins and documented cross-flow reciprocity. It cannot prove a source
was read, a test's assertion supports the prose, every owned file has a Coverage
row, the described call is reachable at runtime, or a sibling's verdict is true.
The Python AST index does not resolve every dynamic reference. A register symbol
note is informational; inspect the actual code before deciding it is wrong.
Schema conformance is a prerequisite to review, not its substitute.

## Completeness and retirement

Compare owned files with the read inventory; defined symbols with mapped or
explicitly excluded symbols; cited files with Coverage. Treat exclusions as claims
requiring reasons. Do not require a directory or dead branch to have a scenario
just to make a count match. Respect authored row ordering.

For a trimmed document, inventory identifiers, figures, constraints and claims
from the original revision. Give each a surviving destination or a retirement
reason backed by current code. Raw string mismatch can mean a concept was
reworded, not lost. Conversely, a section link can exist while its details vanished.
Read the destination before declaring preservation. Search the whole repository
for inbound links and alternate phrasings, beyond the initial file list.

Project-specific setup remains in onboarding; runtime behavior goes to flow maps;
actionable defects go to a register; cross-cutting policy goes to its rule owner.
A short overview should route readers directly to the relevant scenario or symbol.
Do not write conflicting "read this first" sequences into multiple documents.

## Final self-challenge

1. Recheck every sentence explaining why work was omitted or unnecessary.
2. Enumerate what was not read or mapped; prove the list covers the declared scope.
3. Check the claim, not just the command that produced a plausible result.
4. Recompute figures and qualifiers against the final revision.
5. Resolve scenario and register IDs in prose and tables.
6. Verify cited content exists in the revision a new clone will receive.
7. Re-read neighboring sentences after a fix, including correction banners.
8. Reassess severity from current frequency and caller-visible consequences.
9. Require positive/negative certification for new or changed instruments.
10. Assign a reasoned disposition to every seam candidate; distinguish a missing
    link from a shared entry point that warrants no cross-flow scenario.
11. Reconcile sibling verdicts or record explicit ownership with the full symbol,
    both document names and reason. Preserve UNKNOWN where evidence is missing.

In concurrent work, declare path ownership before writing, check both peer overlap
and writes outside your allocation, and snapshot the actual gate input set. If it
changes during a run, the result describes no stable revision. Register unresolved
cross-owner findings in a durable artifact with a responsible owner; a message or
temporary handoff alone is not a destination. Distinguish existing gate failures
from regressions using a baseline with the same location and inputs.
