# Operator questions: ask last, one at a time, and keep the independent work running

Read this before you ask the operator anything in the middle of the work, and before you write a
hand-off that waits on an answer. It adds to the operator-interface rules in item 9 of the brief
contract in `SKILL.md` and does not repeat them.

## Before you ask

- **Start every background job that does not depend on the answer first, and ask last.** A question
  holds your turn until it is answered: one question dialog held a session's turn for about an hour
  while its three background jobs, which took about half an hour, had long finished, and the three
  questions after it took seconds (observed, 2026-11-04).
- **Ask nothing that a command can answer or that the brief already ruled.** Run the command or
  quote the ruling instead, and keep the operator's attention for what only the operator decides.

## How to ask

- **Ask one question per turn, in one call, and make it stand alone.** The operator may see only the
  dialog, so name the items and say what you found instead of pointing at earlier text.
- **Mark the recommended option, which item 9 already puts first.** Offer two to four options, each
  with its consequence, so the operator chooses between outcomes, not between labels.
- **A bare "proceed" is not an answer to a question.** Handle it by the rule in section 8 of the
  [dispatch gates](dispatch-gates.md); a worker finds the same rule in its
  [worker preamble](../../agent-delegate/assets/worker-preamble.md).

## When no answer can arrive

- **A session that cannot ask writes the question under "Blocked on" in its hand-off, with the
  default it takes.** It stops the work that depends on the answer and lets the independent work go
  on.
- **Record in your checkpoint which default you took for an absent operator.** Section 8 of the
  dispatch gates says to take exactly the default you offered; the record lets the next reader see
  that a default, not an answer, decided it.

## After the answer

- **An answer that says it did something ("done", "merged", "rotated") is a claim.** Re-read the
  state by command before you rely on it.
