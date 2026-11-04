# Runtime hazards of a scripted run

Read this before you message a sub-agent that a scripted run is driving, hand a stage of such a run
to another session, let a worker wait on a background run, or trust a run's final summary. A
workflow here is the harness feature that runs scripted sub-agents and keeps a journal of what each
stage returned.

- **Never message a running workflow agent.** A message to a sub-agent that a workflow was still
  running started a second live copy of it, so two writers worked at once (observed once). To change
  course, let the run return and brief again. A sub-agent that has stopped is a different case: the
  bullets of the "Resuming a worker" section of the skill cover it.
- **Hand a last stage over as a standalone script with its arguments, never a resume id.** A resume
  id works only in the session that ran the workflow, so a stage handed to another session by id has
  nothing to resume (observed once). Write the stage as a script that takes what it needs (the
  commit, the paths, the report folder) as arguments.
- **A worker stays in its turn while its background run finishes.** A worker that ended its turn to
  wait for a background run was not woken when the run finished (observed once). It waits inside its
  turn, with a command that exits when the run does, and returns after.
- **Check the journal for a stage that returned no commit id.** A verifier stage that returned no
  commit id was skipped without an error, so nothing flagged it (observed once). After every run,
  read the journal for each stage and list any that returned none, then run the missing stage as a
  standalone script, as the second bullet says.
