# A suite verdict is void when child processes failed to start

Read this before you report a test-suite or gate verdict from a machine that other work was also
loading, and whenever a run's failures name a process that did not start. Section 6 of the skill
covers a verdict taken over a tree that others were editing. This is its twin for the machine: the
tree can stand still and the verdict can still be wrong.

- **A run in which child processes failed to start has no verdict.** A test that never reached its
  assertion measured the machine, not the code. Count start errors apart from assertion failures and
  report the run as UNKNOWN: it is neither a pass nor a regression (observed once: a suite lost many
  tests to start errors, and none of them reached an assertion).
- **Read the run's time before its count.** A suite that takes several times its usual time was
  competing for the machine (observed once: a full run took several times as long, with the
  processor saturated by dozens of interpreter processes).
- **Rerun on a quiet machine.** Quiet means no other gate run, suite, verifier loop or mutation
  loop is running. List the running interpreter processes with the platform's process lister before
  the rerun, and start it only when none of them is another gate run, suite, verifier loop or
  mutation loop. If such a process still runs after 30 minutes (starting value, uncalibrated),
  start no rerun, report the verdict UNKNOWN with the list of those processes, and stop waiting.
  Otherwise report both runs: the void one with its cause, and the rerun.
- **Cap the concurrent gate runs.** Starting value, uncalibrated: one gate run on the machine at a
  time. Run gates between waves of workers, not inside one, because a wave of verifiers and a suite
  compete for the same processes.
