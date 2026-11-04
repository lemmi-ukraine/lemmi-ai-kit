# Delegation brief template

Use this shape for every worker dispatch — native subagent or external CLI. Fill every section;
a section you can't fill crisply is a sign the subtask isn't ready to delegate.

```markdown
**Operator-only blocker:** <the one thing only the operator can clear, or the words "no operator-only blocker">

## Standing rules (read this FILE — only two harness limits are restated below)
Read `<absolute path to the installed agent-delegate skill's assets/worker-preamble.md>` in full before your first
shell call: evidence discipline, working-tree discipline, how to return a result,
and the size, stop and close rules.
Read the project's host-rules file too, if it keeps one: `<host-rules file, or "none">`. A brief
that names none means the project has none.
- Shell hook: a leading `NAME=value` assignment before a command can be denied. Put the value inline,
  write multi-step logic to a script file, or use the interpreter's UTF-8 mode flag instead of an
  environment variable.
- Report file: a harness may refuse a sub-agent's write of a report file. If yours does, return your
  findings as text; "write your report early" applies only if you are allowed to write.

## Goal (one concern)
<single outcome this worker owns>
**Problem:** <what is wrong or missing today>
**Value:** <what is better, for whom, once this is done; a volume target such as "N items processed" is not value>

## Context (so you don't re-explore the repo)
- Files: <paths the work touches, with one-line roles> — a STARTING SET, not a boundary
- Constraints/conventions: <the TASK-SPECIFIC rules — inline them, don't cite them>
- Known facts: <what the orchestrator already verified; state these as COMMANDS that regenerate
  the figure, not as figures — a brief's measured premise is the most common thing to go stale>
- Out of scope: <adjacent things this brief must NOT touch>
- Budget: <how many sessions this work needs and how it splits, written before phase 1>
- Ledgers: `.ai/learnings.md`, `.ai/ai-changelog.md` and, for appends only,
  `.ai/improvement-hypotheses.md` stay open to your appends whatever the file set says (a Status or
  marker edit stays with the validator's run, not with you). <Where the project or the plan bars
  workers from these files, replace that sentence with the writer rule: the brief names one writer
  for each entry (the worker in its own branch, the session that receives the return, or the next
  consolidation) and adds the files to that writer's set; any other worker returns its drafts and
  lists each as not done, with the writer's name, under `## Status` in a hand-off.>

## Definition of done (self-checkable)
- <command that must pass / observable behavior / artifact that must exist>

## Report back (keep it short)
1. What you did (≤5 bullets)
2. Definition-of-done result (command output / evidence)
3. Anything surprising or off-brief you noticed (do not fix it)
4. Files changed (exact paths) — if any
5. Your own error history — killed commands, crashed scripts, broken checkers, reversed conclusions

If you may write files, write this report file EARLY and INCREMENTALLY, not at the end: workers are
killed mid-run by usage limits often enough that a report written only at the end is often never
written at all.

## Close (run in this order, do not wait to be asked)
1. Self-challenge: is it detailed enough? Have you missed something? Say what it changed,
   including "nothing".
2. Then the completion review: run `lemmi-ai-kit-core:post-task-review` through the Skill tool,
   whatever the size of the task (a hand-written review does not replace it), if you have not
   already run it. Both run BEFORE the handoff. A worker without the Skill tool reads the skill's
   steps and says so in its closing message.
3. Lessons: run `lemmi-ai-kit-core:task-learnings`. If your brief bars the learnings buffer, put
   the lesson drafts in your handoff and say so in your closing message.
4. Save everything into the handoff (the report file or return note your brief names).
5. Then write a short summary for whoever reads it next: bullets, at most 10 lines, plain
   language, no internal ids, with the review's step list and the lessons result in it, and say
   in plain words that the session may be closed.
```

Rules of thumb:

- **Workers don't invent the plan.** If the worker would need to make an architectural choice,
  the brief is under-specified — decide it yourself first (or make that decision the brief, routed
  to a reasoning worker).
- **Inline the TASK-SPECIFIC source of truth; POINT at the standing rules.** These pull in opposite
  directions and the split is deliberate. Paste the convention or spec text that governs *this*
  change — it is small, task-scoped, and a stale reference is the real risk. But give the **standing**
  rules (evidence discipline, tree discipline, how to return, size, stop and close) as a path to
  `../../agent-delegate/assets/worker-preamble.md`: that content is identical across every dispatch,
  and restating it inline was measured to change nothing (violated at 32/32 when restated vs 25/27
  when not, with the only clean transcripts being the ones pointed at a file). Inlining it also
  crowds out the task-specific text that inlining is *for*. The one exception is the two harness
  limits restated at the top of the template (a denied leading `NAME=value` assignment, a refused
  report file): a worker meets them on its first command and its last write.
- **Definition of done must be checkable by the worker alone** — and re-checkable by you at merge
  time. "Looks good" is not a definition of done.
- **The report is for a decision, not a story.** If the orchestrator can't accept/reject the
  result from the report in under a minute, ask for less prose and more evidence.

## Paste line

A peer session the user drives starts from one pasted line, and the brief is the file it points at.
The line carries the items below, so that one of the delegate's preconditions can compare each with
what it finds:

- the state: not started, running in a named window, or done;
- the repository folder, compared with `git rev-parse --show-toplevel`;
- the branch, compared with `git rev-parse --abbrev-ref HEAD`.

A line that disagrees with what the delegate finds, or that holds a placeholder, is a stop: the
delegate writes nothing and says so in one sentence. The delegate's first step, before any write, is
a done check (the return note at the named return path exists) and a live-peer check, as `SKILL.md`
§ 2b says: copy both into the brief's preconditions.

## Rules a dispatch brief carries

Each rule was added after a session stopped, or ran twice, without it. They are for whoever writes
the brief: apply each one to the brief you are about to send.

- **A paste line is printed by a command, never typed.** A commit id, branch or date typed into the
  line can be left unfilled. The session that writes the brief runs a command that prints the line
  and gives the operator that output. The line carries no substitution of its own: a `$(...)` in a
  pasted line has arrived unexpanded.
- **Stop on ANY `<...>` placeholder.** A delegate told to stop on two named spellings walks past the
  third. A `<...>` in a command template means "fill it from the command that names it", and one the
  delegate cannot fill is a stop: nothing is written, and its one-sentence report names the
  placeholder.
- **The return note is the first write.** The note and the session's scratch folder come before any
  other file, each made by an operation that fails if it exists (the create collision,
  [12k](../../parallel-session-safety/references/shared-index-protocol.md)). One that exists means
  another run holds this page: the delegate stops and reads it, and a second run of the same brief
  finds the first run's note instead of repeating its work.
- **A project's standing decision beats a session default.** A session starts with defaults it did
  not choose, such as an injected reference that says to fan work out to sub-agents. Where the
  project has ruled otherwise, the brief states the ruling and the default it overrides: a loaded
  reference describes an action and does not authorize it.
- **Preconditions are commands with expected results**, as `SKILL.md` § 2b says. The expected result
  is a literal the delegate compares, and a surprise is a stop to re-derive, never a judgment call.
- **The brief's first lines say what to read before the first command.** A brief that lists its
  state commands or preconditions above the line that points at the standing rules puts the
  delegate's first shell call ahead of that read, and the first call is where a leading assignment
  or a `cd` goes wrong. Keep the pointer to the worker preamble, and to the project's own host-rules
  file when it keeps one, above every command, and word it as "read these, then run the first
  command". The done check and the live-peer check are commands too. The skeleton above already puts
  its standing rules first; a kickoff with a section order of its own must do the same, because a
  rule inside a document the session reads in the same step as its state commands is read after
  them.
- **A kickoff that says "any other reply is a no" says what a plain affirmative means.** "Yes" is the
  likeliest reply. The brief lists what it permits (commits by explicit pathspec, say) and what stays
  the operator's (push, tag, release), so the delegate neither does everything nor stalls.
- **A brief filled in at launch ends with a marker block, and one of its preconditions searches for
  the marker.** The placeholder line is one word, `ADDENDUM-` followed by `PENDING`, written
  without brackets. The precondition searches for it as a regular expression with one character
  in a class, `ADDENDUM-PEN[D]ING`, which does not match its own text. A match means the launch
  addendum is missing: the delegate stops and says so. Certify the check before the brief ships:
  it prints True for a file holding the placeholder, and False for a file without it and for a
  file holding only the check line.
- **A brief never tells an agent to run a user-only skill.** For example `commit-message`: when the
  operator asks for a commit, the agent writes the message from the change itself and says the
  skill is the operator's to run.
- **A brief that lists acceptance criteria names who ticks the boxes and who writes the Status
  line.** A worker that is not named edits no task file; the worker preamble says how it returns
  the criteria.
- **An implementation brief for an approved slice starts from the gate's approval record.** One of
  its preconditions greps that record for every operator-question id the slice's tasks cite,
  expecting each to be found with an answer or "default accepted"; a count of 0 is a stop, never a
  reason to assume the default. Evidence level: observed in one project's notes, not yet repeated;
  an uncalibrated default.
