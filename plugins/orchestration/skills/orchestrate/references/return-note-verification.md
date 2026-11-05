# Verifying a returned note's Verification commands

A returned note lists commands under its Verification section, each with the result it should give.
The note's own claim that they pass is a claim, and this recipe is how to check it. It is a recipe
only. The kit ships no runner for it, and a person or an agent follows it by hand.

## 1. List the commands and give every one exactly one disposition

List the commands with the hand-off lint's `--list-commands` option (the printed form is in
`parallel-session-safety`, section 9). It lists each command with its file and line, its section,
the result expected and an UNRESOLVED mark where a placeholder is unfilled, and it runs nothing.
Give every bullet exactly one disposition:

- **run**: run it and compare the result with the expected one.
- **observe**: run it and record the output; a person judges it.
- **historical**: an event or an old state that cannot be re-run; a reason is required.
- **skip**: do not run it; a reason is required.
- **background**: it runs elsewhere (point 6) and its result is imported.

Count the bullets against the dispositions: a bullet with no disposition, or a disposition with no
bullet, is a finding.

## 2. One result file per run

Save each run's output and exit code to its own result file, so a result can be read again later
and no claim rests on memory.

## 3. The report line is computed, never typed

Compute the report line (how many commands held, failed, were observed or were skipped) from the
result files. A script that updates the records refuses to write unless the numbers its text quotes
hold in those files.

## 4. A separator that can occur inside a command breaks silently

A command can contain the separator of the table that stores it: a search for a diff hunk carries
`@@`, and a pipe is common. A row split on it gains a field and is misread without an error. Use a
format whose separator cannot occur in a command, or fail on a wrong field count.

## 5. A verifier copy takes the project root as an argument

A checking script that runs from a scratch copy must be given the project root. It must never derive
the root from its own path (`parents[N]` of the script file): the copy sits elsewhere, and the
derived root is wrong without an error.

## 6. Long checks run in the background, on copies, between two snapshots

Run a long check in the background on copies of the live bytes, so it does not touch the tree while
peers write. Take a snapshot before it starts and another after it ends (the status, the diffstat
and the content hashes of the files under test). If the two differ, the run is void: run it again.

## 7. Plant a gap before trusting a clean census

A census that finds nothing missing has not yet shown that it can see. Plant one missing
disposition in a copy and show that the checker reports it, with the probe script of
`post-task-review` (`probe_checker.py`); only then trust a clean result.

Evidence level: one project's practice over a few runs; a recipe, not a measured rule.
