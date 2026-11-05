# Running the review in a fresh context

By the end of a long task a session has the least room, and that is when the review runs. This
reference changes who runs the review, never whether: every step still runs, Step 0 to Step 9, and
the report keeps the skill's Output Format. The case for a fresh reader is the fix-round one
(`fix-rounds.md`, section 2); applying it to the whole review is reasoned, not measured.

## 1. When

Use it when the session's context cannot hold the skill, the script's output and the files under
review, or when a reviewer other than the author is wanted. If the session has no way to start an
agent with its own context, run the review in the session and say so in the report.

## 2. The brief

Give the agent one inline brief, because it knows only what the brief carries:

- the base ref, as a commit id, and the plan's list of files;
- the script's real path, the path the session resolved, because the new agent does not know the
  skill's folder, and the path of the skill's SKILL.md to read if it has no Skill tool;
- at most four claims, each with the command that re-derives it, plus one planted false claim, as in
  the fix-round rule (a real claim with one fact changed, left unmarked);
- the gates already run, with their exit codes, as claims to re-run and not as results;
- the skill's Output Format, and read-only terms: the reviewer reports and does not edit, stage or
  commit anything.

Leave out the author's verdict on the work: the reviewer reaches its own.

## 3. What stays with the session

The fix pass and its re-review (Step 5), Step 8, and Step 9 over the whole close before the hand-off
stay with the session. The reviewer closes its own review with its Step 9, and runs as a top-level
run in its own context, not as a skill invoked from inside another.

## 4. Reading the return

Read the return as claims. Trust a confirmation only if the planted claim was rejected, and treat a
return that says nothing about it as unverified. The hand-off names the file that holds the
reviewer's return and the result for the planted claim.
