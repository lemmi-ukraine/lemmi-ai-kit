# Operating rules — how the run itself is operated

Read this at the first gate of an initiative, before any session of the plan starts, and again at each release boundary.

One rule per section, the rule first and its reason after. A release is the work that is pushed
together. A number is a starting value, uncalibrated, unless it is marked observed, with its date.
The charter records the answers, in its "Operator rules in force" section
([charter-template.md](charter-template.md)).

## 1. Take the piecemeal rulings in one gate, before any session starts

**Take the rulings that arrive piecemeal in one gate, before any session starts:** the publication
invariants (what must never reach anything pushed), the push policy (section 6), the hand-off
standard (the one set of sections every hand-off carries), the usage guard's owner and account (who
keeps it, and whose usage it reads), and the owner of the release queue (the one session that lands
finished work). Asked one at a time during the run, each answer reopens work done under the
opposite assumption (observed, 2026-11-03 to 2026-11-04: all five arrived as separate rulings mid-run,
and the push policy and the queue owner were still open when the last batch of commits was ready to
land).

## 2. Keep open decisions to a budget

**Keep at most about 10 open decision rows per release (starting value, uncalibrated), each with an
owner and a trigger, and when a session adds a row it says which row it replaces.** An open decision
row is a question for the operator that no gate has closed, such as an entry of the roadmap's "What
has NOT been decided" list. Sessions that append decisions with a recommendation and no owner,
trigger or deadline outgrow any triage (observed, 2026-11-03: one decision file held 68 numbered
rows).

## 3. Put a stop condition in every kickoff

**End every kickoff with the case where nothing happened: "if no trigger fired, write five lines and
stop".** The triggers are commands with expected results (`SKILL.md` step 8), so a session prints
whether one fired and does not judge it. A kickoff that re-read a large state and found no trigger
fired cost about 0.9 M tokens of context, for nothing (observed once, 2026-11-03, over three
sessions).

## 4. Check the environment before each wave

**Before a wave starts, check these four things:**

- **Free disk.** Start no wave below a floor of 3 GB free (starting value, uncalibrated), and name the
  wave's janitor: the one session that deletes its scratch folders and test temp folders. A full
  system drive stopped the container engine, and two commits went without their Linux gate (observed,
  2026-11-02).
- **Markdown lint.** Limit a markdown-lint hook to the changed lines, or switch it off under scratch
  folders. It returned 14K to 18K tokens of diagnostics for one edit of a long ledger (observed,
  2026-10-30).
- **Usage reading.** Where one is taken (`SKILL.md` step 4), take it for the account the sessions
  actually run under, and say its age. A reading for another account says nothing about the window
  being spent.
- **Shell hook.** Switch Core's shell-prefix hook on for the initiative, as the charter's rule table
  says. It does nothing until the project switches it on.

## 5. Mirror the initiative's folder outside the checkout

**At each release boundary, mirror the initiative's folder outside the checkout, and at each session
close turn each ledger line that has a proposed home into an intake entry.** A folder the repository
ignores is in no commit, so a lost checkout loses it (observed, 2026-11-04: none of several thousand
hand-off and planning files of four workstreams was tracked), and a lesson left only in the
initiative's own ledger never reaches the consolidation that drains the intake buffer.

## 6. Decide the push policy at the gate

**Decide at the first gate, and write it in the charter: one push at the end, or a private fork or a
draft pull request that gives CI feedback before the end.** One push at the end spares consumers a
half-finished state and also withholds the integration signal until the whole release is one merge
(observed, 2026-11-04: about a hundred commits and a week of work had met neither CI nor a reviewer).
