# Delegation brief template

Use this shape for every worker dispatch — native subagent or external CLI. Fill every section;
a section you can't fill crisply is a sign the subtask isn't ready to delegate.

```markdown
## Standing rules (read this FILE — only two harness limits are restated below)
Read `<absolute path to the installed agent-delegate skill's assets/worker-preamble.md>` in full before your first
shell call: evidence discipline, working-tree discipline, and how to return a result.
- Shell hook: a leading `NAME=value` assignment before a command can be denied. Put the value inline,
  write multi-step logic to a script file, or use the interpreter's UTF-8 mode flag instead of an
  environment variable.
- Report file: a harness may refuse a sub-agent's write of a report file. If yours does, return your
  findings as text; "write your report early" applies only if you are allowed to write.

## Goal (one concern)
<single outcome this worker owns>

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
2. Then the task-completion review, if not already run. Both run BEFORE the handoff.
3. Save everything into the handoff.
4. Then a short human-facing summary: bullets, ≤10 lines, plain language, no internal ids.
```

Rules of thumb:

- **Workers don't invent the plan.** If the worker would need to make an architectural choice,
  the brief is under-specified — decide it yourself first (or make that decision the brief, routed
  to a reasoning worker).
- **Inline the TASK-SPECIFIC source of truth; POINT at the standing rules.** These pull in opposite
  directions and the split is deliberate. Paste the convention or spec text that governs *this*
  change — it is small, task-scoped, and a stale reference is the real risk. But give the **standing**
  rules (evidence discipline, tree discipline, how to return) as a path to
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
