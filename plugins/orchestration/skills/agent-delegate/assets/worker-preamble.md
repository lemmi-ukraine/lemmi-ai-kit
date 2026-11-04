# Worker preamble — point every delegated worker at this FILE

A delegated worker does **not** inherit your `AGENTS.md`, your `CLAUDE.md`, or your project
conventions. Everything it must obey has to reach it some other way.

**Point at this file by path. Do not paste its contents into the prompt instead.**

That instruction is not a style preference. Across a measured corpus of 59 sub-agent transcripts,
prompts that **restated** the rules inline were violated at **32 of 32 (100%)**; prompts that did
not restate them were violated at **25 of 27 (93%)** — no measurable difference. The only
transcripts with **zero** violations were the ones pointed at a rules *file* rather than given an
inline restatement. That is a single condition in a small corpus, so treat it as the current best
practice with a named test — re-measure the violation rate after adopting it — not as a law.

The practical consequence is cheap either way: a pointer costs one line, and re-stating rules
inline has no measured benefit to trade against it.

---

## 0 · Host rules (project-specific — kept in the project's host-rules file)

> The project's own host rules — shell and path rules, forbidden directories, interpreter names,
> redirection requirements — live in the project's own host-rules file, if it keeps one, not in
> this file: an edit to an installed plugin copy does not survive an update. Point every brief at
> that file as well as at this preamble, and never edit this copy. Keep that file to constraints a
> worker can *violate*, not general advice. A worker reads the host-rules file its brief names; a
> brief that names none means there are no host rules.

**Shell hooks (a kit default).** A leading `NAME=value` assignment before a command can be denied
by a shell hook. Put the value inline in the command, write multi-step logic to a script file, or
use the interpreter's UTF-8 mode flag (`python -X utf8` for Python) instead of an environment
variable.

---

## 1 · Evidence discipline — how you are allowed to make a claim

Each rule below is a measured failure mode, not a style preference. The unifying principle:

> **A claim about an act must be emitted by the act, not typed beside it.**

- **Cite by symbol, never by a recalled line number.** Run the grep at the moment you write the
  citation. Anchors drift by a line or two even when the quoted text is perfect.
- **Stamp every `file:line` citation with the revision you read** — `path:line (@ <short-sha>)`.
  In a tree where the head commit moves mid-task, anchors drift and an unstamped citation that was
  exact when written reads as fabricated afterwards.
- **Derive counts by enumerating.** Never write a count from memory. Recompute from the diff at
  write time, and write derived numbers in the *last* edit of the task — a figure that was correct
  when written goes stale if editing continues after it.
- **Print the denominator beside every zero.** `0 findings across 344 files scanned` cannot be
  confused with `0 findings because nothing was scanned`. This one line is the cheapest fix in this
  document: silence, an empty result, and a gate that never ran are otherwise indistinguishable.
- **A gate's verdict is its log — never its exit code, and never a filtered tail.** Piping a gate
  through `head`/`grep`/`tail` substitutes the *filter's* exit code for the gate's. Redirect to a
  file and read the file.
- **A verdict from an unfinished run is not a verdict.** A partially-written output file always
  yields a plausible count, and nothing signals incompleteness. Check that the run finished, and
  that it finished *after* the artifact it certifies existed.
- **Exclude yourself from your own measurement.** A sweep whose output lands inside the tree it
  sweeps will find itself. State the exclusion when you report the number. (One recorded instance
  grepped its own growing output to 34 GB and exhausted the disk.)
- **A count from a formatted-literal grep is unproven.** An exact-match pattern like
  `'"anchored":true'` returns 0 against pretty-printed `"anchored": true`. Probe one bare token
  first to learn the formatting, or parse the file.
- **Never write "verified" for anything whose tool call has no recorded output.** Silence from a
  redirected command is UNREAD, not success.
- **On conflicting sources return UNKNOWN with both quotes.** Do not silently pick one.
- **Verify a path exists before reading it.** Do not read a conventional path you assume is there.
- **Treat your brief's file list as a starting set, not a boundary.** Derive the sweep from the
  *claim*, grep tree-wide, untracked files included (`git grep --untracked` or a working-tree grep),
  and report `N named / M actually carried it / K found outside the list`.
  Over-inclusion is caught free by grepping before you edit; under-inclusion is invisible unless you
  deliberately search outside the list.

### A checker you wrote this session is the least-scrutinised instrument in the task

Its zero is what drives your edits, and the failure is symmetric: a silently blind checker's clean
pass blesses a defect exactly as readily as a false alarm invents one. **Do not hand-probe it.**
Run it against a known-positive and a known-negative fixture and report the result beside the
number. A positive control alone certifies the harness, not the pattern — you need the negative
half to catch a filter that encodes its own answer.

Three qualifications worth carrying:

- **A probe certifies the matcher, not the region.** A checker can pass its fixtures and still
  search the wrong span of the file.
- **A probe cannot see a *missing* input.** Pair every manifest or inventory check with a
  set-difference against the live tree.
- **Never phrase a claim as "all X were Y" when Y appears in your selection pattern.** That is
  tautological and fails silently in the worst direction. Count the complement separately.

### An unprobed *mutator* is worse than an unprobed checker

A blind checker reports a wrong number; a blind edit script **writes damage**. Assert that every
substitution actually matched (`assert old in text`, or check the replacement count) rather than
trusting a silent no-op, and make the script idempotent — an edit whose assertion checks only its
*anchor* will happily apply itself twice.

---

## 2 · Working tree

Assume this checkout is shared and that other sessions are writing to it right now.

- **Touch only the file set your brief declares.** A path outside it is a collision, not initiative.
- **Do not stage, commit, push, switch branches, or stash** unless your brief explicitly says to.
  Produce artifacts; branch state belongs to the operator.
- **Never create a git worktree** unless explicitly asked.
- **Never combine a check with the action it gates in one call.** The check's result is stale the
  instant the same call acts on it. Run the check, read it, then act — and scope the action by
  explicit pathspec. (One recorded commit took 74 files where 6 were intended, because the index
  was checked and committed in two separate calls while a peer staged in between.)
- **A suite or gate verdict over a tree others are editing is void.** Snapshot the changed-file
  list before and after any run you will report, and discard the result if the set changed.

**Durable state.** Work held only in a scratch clone or in your context is lost when you are
stopped. Keep it where a stop or a cleanup cannot reach it:

- **Cut a patch into a git-excluded folder after each verified commit.** A clone can be lost or
  damaged, and the patch is what the work is rebuilt from.
- **Do no overnight work in a clone under the OS temp folder.** The system can empty that folder on
  a schedule or at a restart, and the clone goes with it.
- **Run `git fsck` and back up the pack when you make a clone.** Objects can go missing from a
  clone later: the check shows it started whole, and the backup is what you restore from.
- **Create and delete a test run's temporary folder (pytest's `--basetemp`) inside one command.** A
  delete left for a later step is the one a stopped worker skips, and the folders left behind fill
  the disk.
- **Check free disk space against the floor your brief names before you start a wave.** A full disk
  stops every agent at once, in the middle of a write.

---

## 3 · Write your report file EARLY and INCREMENTALLY

Write the deliverable as you go, not at the end — **but only if you are allowed to write.** A harness
may refuse a sub-agent's write of a report file. If yours does, do not retry or route around the
refusal: return your findings as text in your final message (section 4) and say the write was refused.

Workers are killed mid-run by usage limits often enough to matter — **22% of one measured
sub-agent corpus returned nothing at all**. A worker that dies returns exactly what a worker that
found nothing returns, so the orchestrator cannot tell a missing gate from a passing one.

In the one recorded controlled contrast, a worker told to write its report early and incrementally
survived the same usage window that killed its sibling, and delivered. One occurrence — so this is
a practice with a named test (re-measure the no-return rate after adopting it), not a law.

**Checkpoints.** The report holds what you found; a checkpoint holds where the work stands, so a
successor can pick it up if you are stopped before the report or the continuation prompt of section
5 is written. These rules bind the orchestrating session as much as every worker it starts.

- **If you may write files, write a checkpoint at each milestone and at the latest every hour
  (starting value, uncalibrated).** A milestone is a verified step, a commit, a finished sub-task or
  a hand-off to another worker. A worker that may not write files writes none and returns its
  findings as text (section 4).
- **A checkpoint says what is done, what is left and where the results are.** Name the commit ids,
  the report files and paths, and the state of anything shared that you hold, such as a lock.
- **A checkpoint names its next wake condition: the event or the time that resumes the work, with
  the command that reads it.** A successor that cannot tell what you were waiting for starts over.
- **Write it where your brief says.** That is the hand-off file it names, in its Status, "Not done"
  and Continue sections, or the checkpoint file it names, with the newest block first. A brief that
  names neither asks for no checkpoint.
- **A worker or session stopped by a usage limit, a network error or a crash is resumed from its
  latest checkpoint.** The resumer re-reads it and re-checks each claim in it by command before
  acting, and only the work since that checkpoint is lost.

**Publish before extras.** Write the result (or create the branch or ref your brief names) before
any optional verification, and keep the evidence on disk: a session limit stops every agent at
once, and a resume starts from that state.

---

## 4 · Returning your result

- **Your final message *is* the return value** — data for the orchestrator, not a status report.
- **If the harness refused your report file, your final message is the report:** return the
  findings as text, in the report format your brief gave, and say the write was refused (section 3).
  Without that, the refusal reads as a worker that found nothing.
- **Results are claims.** State what you ran and what it output. If you could not verify something,
  say UNKNOWN and name what would settle it.
- **Report your own error history — it is part of the result, not noise.** Killed commands, crashed
  scripts, checkers you found broken, and conclusions you reversed mid-task all go in the return.
  A clean-looking summary over a messy run is a false report, and omitting it is the default
  behaviour you have to override: in one audited set, two of three workers concealed exactly this,
  one of them under an explicit "enumerated, not recalled" claim.
- **Run your completion checklist BEFORE writing your return, never after.** A return written first
  carries whatever the review would have corrected, and the orchestrator inherits it as fact.
- **If your brief turns out to be wrong, say so explicitly and early.** A brief premise that does
  not reproduce is the single most common defect in delegated work (measured at roughly half of
  sessions). Report the discrepancy as a finding; do not quietly work around it.
- **A stop at an action only the operator can take opens your return with that action and its
  owner.** Say what stays blocked until then, before any state or table. A bare "proceed" in reply
  to such a stop is unresolved: it names no action and is not consent to bypass the gate, so
  re-check the gate with the command that reads it and, while it is closed, ask one question with
  explicit options.
- **Return acceptance criteria as a table.** If your brief points at a task file or lists acceptance
  criteria, return them as a table before the rest of your report: one state each (met, not met,
  superseded or operator-owned) and one evidence pointer each. Your brief names who ticks the boxes
  and who writes the Status line; with no such line, edit no task file you do not own.

---

## 5 · Size, stop and close

- **Size the work first.** Size it against your context before you start. If it will not fit one
  session, say so and split it into staged sessions with a prompt each. Set a stop line in the unit
  your host shows you (transcript size, tool calls or tokens); your brief or the project's host
  rules may give it. Starting values, uncalibrated defaults and not measured limits: about 5 MB of
  transcript or about 250 tool calls.
- **Plan the close.** At the stop line, or at a compaction notice, start no new work: run the Close
  block of your brief and write a continuation prompt for what remains. Do not carry on through a
  compaction.
- **Run the Close block of your brief**, in its order, without waiting to be asked. A read-only
  sub-agent that returns text is exempt.
- **Sessions are the operator's to open.** Never start a successor or peer session yourself (a
  terminal window or a headless run of the agent CLI): propose it, name its prompt and folder, and
  ask first. A sub-agent your brief lets you launch is not one.
- **No external call by default.** Make no call to an external service (a payment provider, a cloud
  API, an AI provider) and start no local stack unless your brief names that one call as approved by
  the operator. A ban that names a few services leaves every other one callable, so allow by name
  instead. Record a check you could not run as UNKNOWN with its command.
- **If you run `lemmi-ai-kit-core:plan-critic` on a document, run it within its own run cap**,
  and no more often.
