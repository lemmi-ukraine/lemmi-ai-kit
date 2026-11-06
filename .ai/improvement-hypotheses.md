# AI Infrastructure Improvement Hypotheses

> Testable predictions about expected value from AI infrastructure changes.
> Each hypothesis is linked to a changelog entry and will be validated by a future
> periodic review skill.
>
> **How entries are added:** Automatically by AI workflows after writing a changelog entry,
> via the `ai-improvement-tracker` skill.
>
> **Format:** Each entry follows the structured format defined in
> the `ai-improvement-tracker` skill.
>
> **Status lifecycle:** PENDING → CONFIRMED | REFUTED | INCONCLUSIVE | SUPERSEDED
> (status changes are made by the future validation skill, not this file's authors)

---

## 2026-11-06

### [INFRA-MODIFIED] Wording that a reviewer accepts no longer turns the suite red, and no text that a removed pin held comes back unseen
- **Category:** Quality
- **Hypothesis:** By removing the 83 sentence-pin test files and keeping the tests that run code, the internal-id contract and the 4-row rulings file, we expect the next pull requests that reword a skill, a reference or a template to merge with no red test that names no defect, and no text that a removed pin held to come back in its ruled-out form unseen, because the tests that remain fail only on behaviour, on a forbidden class of text or on one of 4 ruled texts, and a reviewer judges the rest.
- **Signal:** After the next 10 merged pull requests that change a skill, a reference or a template, or by 2026-12-31, whichever comes first, restore the removed and the trimmed test files from `906622e` into a scratch checkout of main (the 83 removed files are listed by `git diff --name-only --diff-filter=D 906622e HEAD -- tests`, run in a checkout of the commit that adds section 22 of the decision record; the 24 trimmed files are the files that `--diff-filter=M` lists there, except `tests/test_assets.py`, `tests/test_content_safety.py` and `tests/test_shared_tree_recipes.py`) and run them against main; read every failure: confirm if each failure is a reviewed rewording and none is a defect (a ruled-out text back, a stated count that no longer matches its list, a pointer to a section that is gone) that no reviewer, remaining test or row caught; refute if at least one failure names such a defect; inconclusive with fewer than 10 such pull requests.
- **Risk:** The reading of each failure is a judgement, and the restored files will fail in numbers for plain old-wording reasons, which makes a real defect easy to miss among them; a pin that has not yet fired cannot show that it was never needed; and 10 pull requests is an uncalibrated starting value for a repository with this few contributors.
- **Status:** PENDING
- **Changelog ref:** 2026-11-06 — Remove the sentence-pin tests that PR #19 added, keep the tests that run code, and add one internal-id contract and a four-row rulings file

## 2026-11-04

### [SKILL-MODIFIED] A worker or session stopped by a usage limit or a crash is resumed from a checkpoint, not re-run from the start
- **Category:** Quality
- **Hypothesis:** By shipping the checkpoint rule in the worker preamble, the brief template and the seeded `AGENTS.md`, we expect workers and sessions that may write files and that a usage limit, a network error or a crash stops in a project on this version to be resumed from a checkpoint written in the hour before the stop more often than re-run from the start, because the brief names the checkpoint file and the cadence and the preamble says what a checkpoint holds and how a resume re-checks it.
- **Signal:** Over the next 5 workers or sessions that may write files and that a usage limit, a network error or a crash stops in a project on this version, or by 2026-12-28, whichever comes first, read the checkpoint file or hand-off that each one's brief named and the transcript of its resume: confirm if at least 4 of the 5 left a checkpoint dated within the hour before the stop and were resumed from it; refute if fewer than 3 of the 5 left one; inconclusive with fewer than 5 stops.
- **Risk:** The rule is prose that a worker must choose to follow, the mechanism that the tracker skill says all refuted verdicts so far share; the hour is an uncalibrated starting value; a checkpoint's time is what the worker wrote, which can be guessed and not read from the clock.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Ship the checkpoint rule to adopters: a Checkpoints group in the worker preamble, a checkpoint line in the brief template and a bullet in both AGENTS.md files

### [SKILL-MODIFIED] Work built in a scratch clone leaves a patch that outlives the clone
- **Category:** Quality
- **Hypothesis:** By putting durable-state lines in the worker preamble and a line for the patch folder and the disk floor in the brief template, we expect the verified commits of the next waves that write in scratch clones to leave a patch in the git-excluded folder their brief named, because the brief names the folder and the preamble ties the patch to each verified commit.
- **Signal:** Over the next 3 waves with 3 or more workers that write in scratch clones or exports, or by 2026-12-28, whichever comes first, list each wave's verified commits from the workers' return notes and the patches in the folder each brief named: confirm if every verified commit of at least 2 of the 3 waves has a patch there; refute if fewer than half of the verified commits of the 3 waves do; inconclusive with fewer than 3 such waves.
- **Risk:** Each line relies on a worker choosing to act, and the folder and the floor are left to the brief, so a brief can leave them empty; a check at clone time can date a loss and cannot stop one.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Give the worker preamble durable-state lines and the brief template a line that names the patch folder and the disk floor

### [SKILL-MODIFIED] A session stopped by a usage limit restarts when its bucket reopens, not when someone types
- **Category:** Speed
- **Hypothesis:** By shipping the limit-recovery reference (write the checkpoint's next wake condition before the wait, arm a background waiter at the printed reset time, probe each model with a one-word agent), we expect an orchestrating session that a usage limit stops to make its next tool call within 15 minutes of the printed reset time more often than a session that waits for a message, because the waiter's completion notice restarts the session and the probe tells it whether the bucket is open.
- **Signal:** Over the next 3 usage-limit stops of an orchestrating session that print a reset time, or by 2026-12-28, whichever comes first, compare the printed reset time with the time of the session's next tool call in its transcript: confirm if at least 2 of the 3 resumed within 15 minutes of that time with no operator message before it; refute if at least 2 of the 3 waited for an operator message; inconclusive with fewer than 3 stops.
- **Risk:** The waiter restarts a session only on a host that re-invokes the session when a background job ends; the reference states that as a fact, names no host or version, and says that a sub-agent is not restarted by a notice. One of its figures (about 4 M sub-agent tokens per 5-hour window per account) is a starting value, uncalibrated, and so is the 15 minutes here.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Add a limit-recovery reference to orchestrate: size a wave in tokens, probe each model, wait out a printed reset with a tested waiter, and name the model of every sub-agent

### [SKILL-MODIFIED] A tree landed in a shared checkout is the tree its READY line recorded
- **Category:** Quality
- **Hypothesis:** By shipping the landing-queue reference and a read-only gate that exits 0 only when every check measured and passed, we expect the landings of the next initiatives that put several sessions in one tree to show a gate exit 0 on every READY line and a landed tree equal to the tree that line recorded, because the gate compares HEAD, the status, the index, the replayed tree and the working tree's copy of each changed path before each commit and prints the landing commands only on exit 0.
- **Signal:** Over the next 2 initiatives with two or more sessions landing into one tree under a queue file, or by 2026-12-28, whichever comes first, read each queue file and the commit history: confirm if every READY line records a gate exit 0 and every LANDED line's tree (`git rev-parse HEAD^{tree}` at that commit) equals the tree its READY line recorded; refute if one landing's tree differs from its READY line or a landing has no READY line with a gate result; inconclusive with fewer than 2 initiatives or fewer than 5 landings.
- **Risk:** The gate applies, stages and commits nothing, so the protocol rests on sessions running it before each commit and writing the lines, a step someone must remember; it sees the tree at the moment it runs, not a peer's write between the run and the commit.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Add a landing-queue reference and a read-only landing gate to parallel-session-safety

### [SKILL-MODIFIED] Orchestrating sessions start their independent background jobs before they ask the operator a question
- **Category:** Speed
- **Hypothesis:** By telling the orchestrator to start every background job that does not depend on the answer first and to ask last, one question per turn, we expect the next orchestrating sessions that ask the operator in the middle of the work to have started every independent background job before the first question, because a question holds the session's turn until it is answered.
- **Signal:** Over the next 5 orchestrating sessions that ask the operator a question in the middle of the work, or by 2026-12-28, whichever comes first, read each session's transcript up to its first question: confirm if at least 4 of the 5 had already started every background job that did not depend on the answer; refute if at least 3 of the 5 started such a job only after the question was answered; inconclusive with fewer than 5 such sessions.
- **Risk:** The reference's one measured case is a single session; which jobs depend on the answer is the reader's call, and the rule is prose that a session must remember when it is about to ask.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Add an operator-questions reference to orchestrate: ask last, one question per turn, and keep the independent work running

### [SKILL-MODIFIED] An initiative planned with the new charter template has its standing operator rulings recorded at the first gate
- **Category:** Quality
- **Hypothesis:** By asking for the operator's standing rules in a charter table and by listing the five rulings that arrive piecemeal (the publication invariants, the push policy, the hand-off standard, the usage guard's owner and account, and the owner of the release queue) to be taken in one gate, we expect the next initiatives planned with these templates to record most of those five rulings at or before their first gate, because the planner now asks for them at the charter and the first gate settles how the run is operated.
- **Signal:** Over the next 2 initiatives planned with the charter template, or by 2026-12-28, whichever comes first, read each charter's "Operator rules in force" table and the initiative's decision log: confirm if in both at least 4 of the five rulings are dated at or before the first gate; refute if in either initiative at least 3 of the five arrive after the first gate; inconclusive with fewer than 2 initiatives.
- **Risk:** The operating rules say that a ruling asked for one at a time during the run reopens work done under the opposite assumption, and cite one observed case in which all five arrived as separate rulings; the rulings are the operator's to give, so a late one may be the operator's choice and not a miss of the planner's; the first-gate date is read from the initiative's own records; two initiatives are few; and the forecast log and the operating rules beyond those five rulings are not measured here.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Add operating rules to the initiative planner, an Operator rules in force table to its charter template and a Forecast log to its roadmap template

### [SKILL-MODIFIED] A fix round closed clean by a fresh reader leaves no stale copy of a changed claim in a file it did not edit
- **Category:** Quality
- **Hypothesis:** By making the fresh reader's brief sweep the files the change did not edit, check that every pointer carries a section number or a stable heading name, and end its return with what it did not check, we expect the fix rounds closed clean after this change to leave no stale copy of a changed claim in a file they did not edit, because the reader greps the old claim in every skill, reference and README that cites the changed place.
- **Signal:** Over the next 3 fix rounds that rewrite claims others will act on and are re-reviewed by a fresh reader, or by 2026-12-28, whichever comes first, run the old claim's phrase over the whole tree after each round closes: confirm if none of the 3 leaves a stale copy of a changed claim in a file the round did not edit; refute if one does; inconclusive with fewer than 3 rounds.
- **Risk:** The sweep is a step that the reader's brief must carry and the reader must perform; the old claim's phrase is chosen by whoever runs the check, so two readers can pick different phrases; the real-data trial lines of this change are not measured here, because their event (a feature that reads files its authors did not write) may not occur in the window.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Add a fresh reader's sweep past the diff to fix-round review, and a real-data trial to the spec-driven-dev and test-planner checklists

### [SKILL-MODIFIED] A suite verdict taken on a machine that failed to start child processes is reported UNKNOWN with a rerun, not as a pass or a regression
- **Category:** Quality
- **Hypothesis:** By adding the suite-verdicts reference (no verdict from a run in which child processes failed to start, a run's time read before its count, a rerun on a quiet machine, one gate run at a time), we expect the next suite or gate reports from a loaded machine to call a run with start errors UNKNOWN and to report the rerun beside it, or the processes that kept a quiet machine from coming back within 30 minutes, because the reference says to count start errors apart from assertion failures and to report both runs.
- **Signal:** Over the next 3 suite or gate runs in which any child process failed to start, or by 2026-12-28, whichever comes first, read each report: confirm if each calls the run UNKNOWN and reports a rerun on a quiet machine or the processes that kept one from starting; refute if one reports such a run as a pass or as a regression; inconclusive with fewer than 3 such runs.
- **Risk:** The starting values of one gate run at a time and of the 30-minute wait are uncalibrated; it costs time when waves queue behind a suite, runs with start errors may not occur in the window, and the runtime hazards of the same entry are not measured here, because their events (a message to a running workflow agent, a stage handed over by id) may not occur in the window.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Add the runtime hazards of a scripted run to agent-delegate and a void-verdict rule for a loaded machine to parallel-session-safety

### [SKILL-MODIFIED] A rule changed while sessions run reaches each running session as a message, and each brief names the revision it was written against
- **Category:** Quality
- **Hypothesis:** By adding a revision line to the brief skeleton and a rule that a changed rule is sent to each running session or worker as a message, we expect the next rule changes made while two or more sessions or workers run to reach each of them in the turn in which the change is made, and every brief written after the change to name its revision, because the skeleton asks for the line and the rules section says a changed rule is sent as a message.
- **Signal:** Over the next 3 rule changes made while two or more sessions or workers run, or by 2026-12-28, whichever comes first, read the orchestrator's transcript and that of each running session: confirm if in at least 2 of the 3 changes every running session received the change as a message before its next action and every brief written after it names a revision; refute if in at least 2 of the 3 a running session learned of the change only by re-reading a file; inconclusive with fewer than 3 such changes.
- **Risk:** The rule is prose that the orchestrator must remember at the moment it changes a rule, and the revision line is only as good as the clock and the commit that the brief's writer reads; the read-budget line, the two publish-check runs and the wave sentence of the same entry are not measured here, because their events (a brief that names a read budget, a publish-check run in a fresh clone or in the real checkout, a wave sized in tokens) may not occur in the window.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Add a revision line, a read-budget line and a changed-rule message rule to the brief template, and say in the kit's AGENTS.md what each publish-check run answers and how wide a wave is

### [SKILL-MODIFIED] New hand-offs carry a version label and pass the lint at v2
- **Category:** Consistency
- **Hypothesis:** By shipping the version label, the lint rule and the seeded template together, we expect the hand-offs written in an adopter's `.ai/handoffs/` after the update to pass `lint handoffs` at v2 (both new sections present and non-empty) more often than notes written from the five-section contract alone, because the compliance the standard was chosen for came from the template, the label and the lint together (quoted from a consumer, uncalibrated, not re-measured here).
- **Signal:** Over the next 5 hand-offs written in a project that updated to this version, or by 2026-12-28, whichever comes first, run `lint handoffs` over them: confirm if at least 4 of the 5 carry the v2 label on line 1 and pass with both new sections present; refute if fewer than 3 of the 5 carry the label; inconclusive with fewer than 5 hand-offs in the window.
- **Risk:** The label is optional by design, so a project can ignore it and still pass at five sections; the compliance figure is quoted and was not re-measured; the thresholds are uncalibrated defaults; the lint checks that the two sections are non-empty, not that they are useful.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Apply the third session of change requests: 21 verified packages across the review, planning, orchestration, drain and hand-off skills

### [SKILL-MODIFIED] A project that switches the drain-due nudge on drains its learnings buffer sooner
- **Category:** Knowledge Retention
- **Hypothesis:** By shipping a default-off SessionStart nudge that prints the buffer-pressure line when a session opens, we expect a project that switches it on to drain its learnings buffer within 7 days of the line first appearing more often than on the prose nudges alone, because the task-learnings and session-retrospective skills speak only when they run and the hook speaks at every session start.
- **Signal:** Over the next 3 drain-due episodes in a project that switched the hook on, or by 2026-12-28, whichever comes first, compare the date the line first appeared with the date of the drain commit: confirm if at least 2 of the 3 drains came within 7 days; refute if fewer than 1 of 3 did, or if the hook ran in an enabled project and the session never mentioned the line; inconclusive if no project switched it on or fewer than 3 episodes occurred.
- **Risk:** The line reaches the session only if the harness shows hook output to the model, which was not tried live; the 7 days is an uncalibrated default; a project that switches the hook on may already care about draining.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Apply the third session of change requests: 21 verified packages across the review, planning, orchestration, drain and hand-off skills

### [SKILL-MODIFIED] A plan row for a session the operator did not drive is launched, not pasted
- **Category:** Speed
- **Hypothesis:** By giving the orchestrator one command that prints or runs the headless launch, and letting a plan row say `pasted` with no reason when the operator will drive that session, we expect plans written after this change to show fewer `pasted` rows for sessions the operator did not drive than plans written before it, because the background start now costs about one command, as pasting does.
- **Signal:** Over the next 3 initiative plans written after this change, or by 2026-12-28, whichever comes first, count each plan's `pasted` rows in its Dispatch table and ask the operator which of those sessions they drove: confirm if the share of `pasted` rows the operator did not drive is lower than in the last 3 plans written before the change in at least 2 of the 3 new plans; refute if it is not lower in 2 of 3; inconclusive with fewer than 3 new plans.
- **Risk:** The older plans were written by a different planner and are read from their tables; the operator's recollection of which sessions they drove is the instrument; three plans are few.
- **Status:** PENDING
- **Changelog ref:** 2026-11-04 — Apply the third session of change requests: 21 verified packages across the review, planning, orchestration, drain and hand-off skills

## 2026-11-03

### [SKILL-MODIFIED] A brief built from the template points a worker at the project's host-rules file
- **Category:** Quality
- **Hypothesis:** By naming the project's own host-rules file in section 0 of the worker preamble and carrying a line for it in the brief template's Standing rules, we expect the next 5 briefs written from the template in a project that keeps such a file to name it, and the workers that receive them to apply a rule only that file states, because the template now carries the line and the preamble tells a worker to read the file its brief names.
- **Signal:** Over the next 5 briefs written from the template in a project that keeps a host-rules file, or by 2026-12-28, whichever comes first, read each brief and its worker's first messages, count the briefs that name the file (N), and call a worker tested when its brief named the file and it met a rule that only that file states. Inconclusive if fewer than 5 such briefs exist by that date. Otherwise refute if N is under 3 or if a tested worker did not follow the rule; otherwise inconclusive if no worker was tested or N is 3; otherwise confirm (N is at least 4 and every tested worker followed the rule).
- **Risk:** The line is a placeholder that the writer must fill, and a wrong path passes the placeholder rule; the preamble says a brief that names none means there are no host rules, which is wider than the template's line, because a host rule can apply to a worker without any brief naming it; the template's heading still says read this file.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Name the host-rules file generically, make the drain landing audit paragraph say what the script refuses, and correct seven older statements

### [SKILL-MODIFIED] Dispatched prompts stop quoting a superseded decision, and a bare proceed is not read as consent to bypass a closed gate
- **Category:** Quality
- **Hypothesis:** By adding the amendment sweep and the operator-first report rules to the dispatch gates, we expect fewer dispatched prompts that still quote a superseded decision, and fewer bare proceed replies taken as consent to bypass a closed gate, in the next two multi-session initiatives, because each check is a command or a comparison and the stop report names the owner of the action.
- **Signal:** Over the next 2 multi-session initiatives that use the dispatch gates, or by 2026-12-28, whichever comes first, read each initiative's dispatch files and operator reports: confirm if no dispatched prompt quotes a decision its register has since superseded and every stop report opens with the answer or the operator-only action; refute if a prompt still quotes a superseded decision after its sweep was due, or a bare proceed is taken as consent to bypass a closed gate; inconclusive with fewer than 2 initiatives.
- **Risk:** A sweep is a step a session must remember to run; the rule that a bare proceed after a stop is unresolved has one stated exception (a spec's approval stop) and the reader decides whether a stop is one; two initiatives are few.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Add instrument lessons to post-task-review, add a style column to test planning, add an amendment sweep to the dispatch gates and test commands that open with an assignment

### [SKILL-MODIFIED] A plan in a two-form project places its scenarios in the form already used there
- **Category:** Quality
- **Hypothesis:** By asking for a census of tests by form and a Style column, and for the critic to check each acceptance scenario's owner in the project's own form, we expect a plan in a project with two test forms to place its scenarios in the form already used there, because the counts are taken before the cases are written.
- **Signal:** Over the next 3 plans written for a project with two test forms, or by 2026-12-28, whichever comes first, read each plan's census and Style column: confirm if every plan carries a census and no scenario is placed in a form the census shows the area does not use; refute if a two-form plan passes review with no census; inconclusive with fewer than 3 such plans.
- **Risk:** The census is taken from a feature and two sibling areas, which can mislead in a young project; a project with one test form never meets the rule.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Add instrument lessons to post-task-review, add a style column to test planning, add an amendment sweep to the dispatch gates and test commands that open with an assignment

### [SKILL-MODIFIED] No new shipped line opens a command with an assignment
- **Category:** Consistency
- **Hypothesis:** By adding the assignment-led test with an allowlist of the six occurrences that existed (five distinct commands), we expect no new shipped line to open a command with an assignment before 2026-12-28 and the allowlist to only shrink, because the shipped hook's own judge decides the rule and any new line fails by file and line.
- **Signal:** By 2026-12-28, read the allowlist in tests/test_assignment_led_commands.py and the history of shipped text: confirm if no entry was added and no shipped line opens with an assignment while the suite is green; refute if a new such line ships with the suite green or an entry is added without a fix; inconclusive if the test was removed.
- **Risk:** The test judges a command the way the hook does and nothing else: a command that is not in a fenced shell block or an inline code span is not seen.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Add instrument lessons to post-task-review, add a style column to test planning, add an amendment sweep to the dispatch gates and test commands that open with an assignment

### [SKILL-MODIFIED] A drain meets one backup instruction, and its landing audit lands nothing through a ledger
- **Category:** Knowledge Retention
- **Hypothesis:** By making the drain audit refuse the changelog and hypotheses ledgers by file name and print its scan surface, and by making the consolidation critic and the safety rule describe the backup as the committed restore point, we expect the next two drains to commit no second backup of the buffer and to report no entry as landed whose only hit is in a ledger, because the three texts a drain loads now say what the drain procedure says, and the ledgers that quote drained entries are refused by name.
- **Signal:** Over the next 2 drains in a project that runs the consolidator, or by 2026-12-28, whichever comes first, read each drain's commits and its audit output: confirm if neither drain commits a byte copy or a snapshot file beside its restore-point commit, and each audit prints its scan surface line with no landing whose only hit is a ledger; refute if a drain commits such a file, or an audit lands an entry through a ledger; inconclusive with fewer than 2 drains.
- **Risk:** The reference's landing-audit paragraph called the byte copies pre-drain snapshots and named no ledger until 441ac8d rewrote it, so a session that reads an older copy may describe the refusal wrongly; a refusal by file name also refuses a real home that happens to share a ledger's name; two drains are few.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Align the drain audit, the consolidation critic and the safety rule with the restore-point drain, read .NET commands as build-and-test loops, point plan-critic's callers at its run cap, and fix the smaller claims the last review found

### [SKILL-MODIFIED] A document reviewed through spec-driven-dev or initiative-planner gets no third plan-critic run
- **Category:** Speed
- **Hypothesis:** By having the six callers of plan-critic say that the review runs within its own run cap, instead of telling the reader to resolve all findings (or Blockers and Majors) before continuing, we expect no document reviewed through spec-driven-dev or initiative-planner to get a third critic run, because the cap now has one home and no caller contradicts it.
- **Signal:** Over the next 5 documents reviewed by plan-critic from either skill, or by 2026-12-28, whichever comes first, count the critic runs per document in each session's transcript: confirm if none has more than two runs and every second run edits only for a factual error, a contradiction, a missing item or an unsafe statement; refute if any document gets a third run; inconclusive with fewer than 5 such documents.
- **Risk:** The seeded AGENTS.md template and the kit's own AGENTS.md still restate the old rule, so a session that reads them first may loop anyway; whether a second run's edit is one of the four kinds is the reader's call.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Align the drain audit, the consolidation critic and the safety rule with the restore-point drain, read .NET commands as build-and-test loops, point plan-critic's callers at its run cap, and fix the smaller claims the last review found

### [SKILL-MODIFIED] A .NET project's retrospective digest lists its build-and-test loops
- **Category:** Quality
- **Hypothesis:** By building the loop detector's pattern from eight .NET commands beside the old tools, we expect the next retrospective digest over a .NET project to list its repeated build and test commands under buildTestLoops, because the pattern no longer sees only the tools of Python and JavaScript projects.
- **Signal:** At the next session-retrospective run over a .NET project, or by 2026-12-28, whichever comes first: confirm if a session that repeated a dotnet or msbuild command lists it under buildTestLoops; refute if a repeated `dotnet build` or `dotnet test` is absent from it; inconclusive if no session in the window repeated one.
- **Risk:** The detector reads only the first 120 characters of a command, so a .NET command after a long `cd` is missed; a quoted program path before the verb, and `dotnet watch`, `ef`, `pack` and `clean`, are not covered; the only evidence so far is a planted digest.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Align the drain audit, the consolidation critic and the safety rule with the restore-point drain, read .NET commands as build-and-test loops, point plan-critic's callers at its run cap, and fix the smaller claims the last review found

### [RULE-ADDED] A session with splittable pieces hands them to sub-agents that never write in the shared tree
- **Category:** Speed
- **Hypothesis:** By stating in AGENTS.md that crisp pieces go to sub-agents with their own context, working only in an export and delivering patches, we expect the next sessions in this repository that find nothing they can build themselves to hand pieces to sub-agents instead of ending at "waiting on the operator", and no worker to write in the shared tree, because the rule names the safe shape and says who commits.
- **Signal:** Over the next five sessions that read this rule, or by 2026-12-28, whichever comes first, read each session's return note and the tree's `git status` before and after its workers ran: confirm if at least three sessions that had splittable pieces used sub-agents and no worker's path appears in the tree's status; refute if a worker wrote in the tree, or a session with splittable pieces stopped at "waiting on the operator" without trying; inconclusive if fewer than three sessions had splittable pieces.
- **Risk:** Two of the three workers in the session that prompted the rule died to usage-limit and access errors mid-wave; a rule that encourages waves can multiply that on a limited window, and its own guards (read the usage window first; save a checkpoint at each milestone) depend on a usage feed that was stale and on workers that remember to write the checkpoint.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Sub-agents with their own context work only in a copy of the tree, and only the main session commits what they deliver

### [SKILL-MODIFIED] A drain's recovery point is a commit that is never removed, so the landing audit's input is cited by commit id
- **Category:** Knowledge Retention
- **Hypothesis:** By having the operator commit the learnings buffer in its own commit before a drain's first removal, and by keeping the byte copy and the gate record local and ignored, we expect the changelog entries of the next two drains to cite that commit's id as the landing audit's input and none to cite a snapshot file path, because a commit is not removed before the merge the way a committed snapshot file was, so no citation of it breaks.
- **Signal:** Over the next 2 drains in a project that runs this skill, or by 2026-12-28, whichever comes first, read each drain's changelog entry and the audit command it cites: confirm if both cite a restore-point commit id and neither cites a snapshot file path or commits the byte copy or the gate record; refute if either cites a path, cites no commit, or commits the copy or the record; inconclusive with fewer than 2 drains in the window.
- **Risk:** The consolidation critic's Inputs row and printed audit lines, and the audit script's closing line, named the snapshot file until the polish chain (39cf685, a5f71e3) rewrote them, so a session that reads an older copy may cite a path anyway; kit-setup seeds neither ignore entry, so a project without them may commit the copy or the record; the eight citations rewritten after a committed snapshot was removed are one observation.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Delete the PR-review skill's bare-decorator bullet, commit the learnings buffer as a drain's restore point, give the brief template a blocker line and a problem and value line, send the preamble's host rules to the project's own file, and add a SQL hand-off trap and two prompt-sweep checks

### [SKILL-MODIFIED] A brief written from the template names what only the operator can clear and what the work is for
- **Category:** Quality
- **Hypothesis:** By opening the brief template with an operator-only blocker line and giving the goal a Problem line and a Value line that says a volume target is not value, we expect the next 10 briefs written from the template to begin with the blocker line and to state a value that names who is better off, not a count of items processed, because the first line and the two goal lines are the places a brief is filled in, and the template says what each must hold.
- **Signal:** Over the next 10 briefs written from the template, or by 2026-12-28, whichever comes first, read each brief's first line and its Goal: confirm if at least 9 of the 10 begin with the blocker line and hold a Value line that names an outcome for someone and no bare volume target; refute if fewer than 5 do; inconclusive in between, or with fewer than 10 such briefs (both thresholds are uncalibrated).
- **Risk:** A brief written from memory skips the template; whether a value line names an outcome is the reader's call, so two readers may differ; a writer may fill the blocker line with "no operator-only blocker" by habit.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Delete the PR-review skill's bare-decorator bullet, commit the learnings buffer as a drain's restore point, give the brief template a blocker line and a problem and value line, send the preamble's host rules to the project's own file, and add a SQL hand-off trap and two prompt-sweep checks

### [SKILL-MODIFIED] The worker preamble no longer invites an edit that an update overwrites
- **Category:** Consistency
- **Hypothesis:** By sending the project's own host rules to the project's host-rules file and telling every brief to point at it beside the preamble, we expect no installed copy of the worker preamble to differ from the shipped one at the next update review of a project that dispatches workers with it, because section 0 no longer tells an adopter to replace a block of the installed copy, which the next update overwrites.
- **Signal:** By 2026-12-28 (calendar backstop), at the next update review of each project that dispatches workers with the preamble, compare its installed assets/worker-preamble.md with the shipped file and read its host-rules file: confirm if no installed copy differs and each project keeps its host rules in its own file; refute if an installed copy holds project rules, or a brief points a worker at the preamble alone for them; inconclusive if no project is reviewed in the window.
- **Risk:** A project that already replaced the block keeps its edit until an update overwrites it, which is the loss the change avoids; the file's conventional path is a convention and is not enforced; the comparison needs read access to an adopter's installed copy.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Delete the PR-review skill's bare-decorator bullet, commit the learnings buffer as a drain's restore point, give the brief template a blocker line and a problem and value line, send the preamble's host rules to the project's own file, and add a SQL hand-off trap and two prompt-sweep checks

### [SKILL-MODIFIED] A delegated session sizes its work, stops at its stop line and closes with the review and the lessons, and opens no session unasked
- **Category:** Consistency
- **Hypothesis:** By pointing every delegated worker at section 5 of the worker preamble and pasting one five-step Close block in every brief, we expect the next 10 delegated sessions whose brief carries them to run the completion review through the Skill tool, to end with a summary that says the session may be closed and to open no session of their own, because the rules sit in the one file a worker is told to read, and the Close block now names the review skill and the lessons step that the older four-step copies left implicit.
- **Signal:** Over the next 10 delegated sessions whose brief carries the Close block, or by 2026-12-28, whichever comes first, read each session's transcript and return note: confirm if at least 9 of the 10 ran the completion review through the Skill tool, ended by saying the session may be closed and opened no session; refute if fewer than 5 did, or if a session that reached its stop line carried on through a compaction notice; inconclusive in between, or with fewer than 10 such sessions (both thresholds are uncalibrated).
- **Risk:** A worker run by an external agent CLI has no Skill tool, so steps 2 and 3 of the Close block cannot run as written there; the 5 MB and 250 tool-call stop lines are uncalibrated and from one source; "sessions are the operator's to open" exempts sub-agents only.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Give delegated sessions size, stop and close rules and one five-step Close block, ask plan-critic for each fix as replacement text, keep the cleanup sweep off the hand-offs ignore file, and give the stacked-PR document its shared-checkout recipes

### [SKILL-MODIFIED] A plan-critic run leaves no change that none of its fixes made on purpose
- **Category:** Quality
- **Hypothesis:** By asking for each fix as exact replacement text and diffing the document after the last fix pass, we expect the next documents that plan-critic fixes to carry no edit that a fix pass made by accident, because every changed line is held against a fix the critic meant to make, and replacement text can be checked line by line where a described change could not.
- **Signal:** Over the next 5 plan-critic runs that fix a document, or by 2026-12-28, whichever comes first, diff each document against its version before the first fix pass and read the run's findings: confirm if every changed line is one a Resolution field quotes and no Resolution field describes a change instead of quoting one; refute if a run leaves a changed line that no finding names, or a Resolution field that describes a change; inconclusive with fewer than 5 such runs.
- **Risk:** The diff check named no source for the pre-fix-pass copy until the polish chain (43b9a6f) added one (copy the document before the first fix pass; git stands in only when git holds that version), so a run that kept no copy still cannot do it; whether a critic follows the clause is unmeasured; the run cap is a separate rule and unchanged.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Give delegated sessions size, stop and close rules and one five-step Close block, ask plan-critic for each fix as replacement text, keep the cleanup sweep off the hand-offs ignore file, and give the stacked-PR document its shared-checkout recipes

### [SKILL-MODIFIED] An agent delivering from a shared checkout creates its refs with a create-only guard and cites a delivery proof
- **Category:** Coverage
- **Hypothesis:** By putting the shared-checkout recipes, each with the sentence that names its trap, in the document the stacked-PR planner and the comment resolver point at, we expect an agent that delivers branches from a checkout another session writes to create its refs with a create-only guard and to cite a delivery proof instead of switching the checkout, because the recipe now sits where it reads.
- **Signal:** By 2026-12-28 (calendar backstop), read the transcripts of up to 3 sessions, in projects seeded or refreshed after this change, that stacked or delivered branches from a checkout another session was writing: confirm if each created its refs without moving the checkout's HEAD or index (a create-only `update-ref`, or `git replay`) and cited a delivery proof; refute if one switched the checkout to deliver, or created a ref with no guard; inconclusive if no such session ran in the window.
- **Risk:** A project seeded before this change keeps its old copy until kit-setup refreshes it; the recipes were run on one host (Windows PowerShell 5.1, git 2.55), so another host or git version may differ; the CI-build count and the pair-check statistic are the source project's own measurements and were not verified here.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Give delegated sessions size, stop and close rules and one five-step Close block, ask plan-critic for each fix as replacement text, keep the cleanup sweep off the hand-offs ignore file, and give the stacked-PR document its shared-checkout recipes

### [SKILL-MODIFIED] A GitHub token is redacted wherever it sits in a session digest, and the leak gate looks for the same shape
- **Category:** Quality
- **Hypothesis:** By matching a GitHub token by its shape in both the redaction list and the leak gate, we expect the digests of the next retrospectives to carry no GitHub token and the gate to flag none, because a token after a command-line flag or in an Authorization header, which the KEY/TOKEN pattern never matched, now becomes `[REDACTED_GITHUB_TOKEN]` before the digest is written.
- **Signal:** Over the next five retrospective runs, or by 2026-12-28, whichever comes first, read each run's digests and its `--check-file` result: confirm if no digest holds a GitHub token shape (grep `gh[pousr]_` and `github_pat_` followed by 36 or more letters and digits, with a planted control) and at least one digest holds a `[REDACTED_GITHUB_TOKEN]` mark; refute if a token shape survives in a digest or the gate flags text that was redacted; inconclusive if no digest meets a token in the window, which leaves no mark to count.
- **Risk:** A token prefix GitHub adds later passes until a pattern for it is added; an identifier of 36 or more letters and digits after one of the prefixes, with no `_`, `-` or `.`, is masked as a token.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Redact a GitHub token by shape in the session extractor, and make pointer and lint-gate lines say what the reference holds and name the project's own command

### [SKILL-MODIFIED] A drain that removes nothing no longer silences the cadence nudges, and the audit lands a promotion in a home the project names
- **Category:** Observability
- **Hypothesis:** By marking each `CONSOLIDATION` entry with its Drained count and letting the drain audit take the project's own homes with `--surface`, we expect the next drain in each consumer to write a Drained line that the cadence nudges then date the last drain by, and to report no `[LOSS?]` row for a promotion that landed in a home named with `--surface`, because Phase 7a writes the line (0 included), every reader skips an entry whose count is 0, and both scans read a plain added glob in the tree's case alike.
- **Signal:** Over the next drain in each consumer, or by 2026-12-28, whichever comes first, read its changelog entry, the next task-learnings or session-retrospective nudge, and its audit output: confirm if the entry carries a Drained line, a nudge after a run that drained nothing still dates the last drain by the earlier entry, and no `[LOSS?]` row names a promotion that landed under a `--surface` glob; refute if an entry lacks the line, a run that drained nothing silences a nudge, or such a row appears; inconclusive if no drain runs in the window.
- **Risk:** A surface that reaches `.ai/` still lets a ledger that quotes an entry land it, an open question for the operator; a consumer that names no home with `--surface` tests only the marker half.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Date the last drain by a marked count, let the drain audit take a project's own homes, read each promoted paragraph beside its source entry, file .NET build failures as build errors, and seed a self-ignoring .gitignore in each local-only folder

### [SKILL-MODIFIED] The consolidation critic's fidelity read catches a promoted paraphrase that changed its entry's claim
- **Category:** Quality
- **Hypothesis:** By having a fresh reader read each promoted paragraph beside its source entry in C6, we expect the next two consolidations' critic reports to list at least one changed claim that the other checks would have passed, corrected before the drain lands, because paraphrases that changed a claim passed every presence, anchor and hedge check before.
- **Signal:** Over the next two consolidation runs in either consumer, or by 2026-12-28, whichever comes first, read each critic report's Fidelity read line: confirm if at least one run lists a changed claim that was corrected before the drain landed and its reader rejected the planted claim; refute if both runs list none while a later read finds a changed claim in a promoted paragraph; inconclusive with fewer than two runs.
- **Risk:** A fresh reader's brief is capped at four real claims, so a large drain needs several readers and C6 does not say so; a reader that rejects the plant can still miss a subtle change.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Date the last drain by a marked count, let the drain audit take a project's own homes, read each promoted paragraph beside its source entry, file .NET build failures as build errors, and seed a self-ignoring .gitignore in each local-only folder

### [SKILL-MODIFIED] A retrospective over a .NET project files its build failures as build errors
- **Category:** Observability
- **Hypothesis:** By filing .NET build output as build-compile, we expect the next retrospective over the .NET consumer to show at least one build-compile result from a dotnet or MSBuild call and no dotnet test summary filed build-compile, because the table matches the build stamp and the coded errors, not the test summary's `Failed!`.
- **Signal:** In the next session-retrospective run over the .NET consumer, or by 2026-12-28, whichever comes first: confirm if at least one build-compile result comes from a dotnet or MSBuild call and no dotnet test summary is filed build-compile; refute if a failing dotnet build is still filed test-failure or runtime-exit, or a test summary is filed build-compile; inconclusive if the window holds no failing .NET build (none of the 23 local .NET error results moved class when the change was measured).
- **Risk:** A failing dotnet test that also prints the build stamp files build-compile; terminal-logger output with no coded line, and NU, NETSDK, CA, IDE, FS and BC codes, are not read as build errors.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Date the last drain by a marked count, let the drain audit take a project's own homes, read each promoted paragraph beside its source entry, file .NET build failures as build errors, and seed a self-ignoring .gitignore in each local-only folder

### [SKILL-MODIFIED] A project scaffolded after the seed commits nothing under its local-only folders but their ignore files
- **Category:** Quality
- **Hypothesis:** By seeding a self-ignoring `.gitignore` in `.ai/tmp/`, `.ai/handoffs/` and `.ai/retrospectives/`, we expect a project scaffolded or refreshed after this change to add no file under those folders to git except the three ignore files, because a plain `git add` there is now refused and the skills' gitignored claims hold without the adopter acting.
- **Signal:** By 2026-12-28 (calendar backstop), list the files added to git under the three folders, after the seed, in each project scaffolded or refreshed after this change: confirm if no file under the three folders other than their `.gitignore` files was added; refute if any other file was; inconclusive if no project was scaffolded or refreshed in the window, or if the window holds only projects whose root rules already ignore the folders. Only a fresh adopter (no root rule over those folders) can move this signal.
- **Risk:** Notes committed before the seed stay tracked, since an ignore rule never untracks a file; a root rule that covers a folder only partly is overridden by the seeded `*`.
- **Status:** PENDING
- **Changelog ref:** 2026-11-03 — Date the last drain by a marked count, let the drain audit take a project's own homes, read each promoted paragraph beside its source entry, file .NET build failures as build errors, and seed a self-ignoring .gitignore in each local-only folder

## 2026-11-02

### [SKILL-MODIFIED] Skill creation and review cite no decision an adopter cannot read and name only commit-message as user-only
- **Category:** Quality
- **Hypothesis:** By rewording six opaque or dated policy citations as the kit's own recommendation and naming commit-message as the one kit skill a model may not invoke, we expect skill-creator and skill-reviewer runs in an adopter repository to cite no decision label or dated project policy and to call no kit skill but commit-message user-only, because the shipped text now states only what the kit can show.
- **Signal:** Over the next 5 skill-creator or skill-reviewer runs in a consumer repository, or by 2026-12-28, whichever comes first, read each run's output in the transcript: confirm if none cites a decision label or a dated project policy and none says a session may not invoke branch-switch; refute if one does either; inconclusive with fewer than 5 runs.
- **Risk:** The two skills run rarely in a consumer, so the window may close empty; the example names commit-message alone, so it goes stale if another kit skill takes the flag.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Make fifteen shipped skills read as written in any consumer: the project's own conventions and names, labelled one-repository examples, and no false claim about which skill a model may not invoke

### [SKILL-MODIFIED] A plan in a repository the language pack does not cover uses its own level names with no finding for skipping the pack
- **Category:** Quality
- **Hypothesis:** By putting the project's own testing conventions before a pack's table and scoping two Python-only descriptions to Python, we expect plans written in a repository the pack does not cover to use that repository's own level names with no plan-critic finding for ignoring the pack, and the two skills to stop loading on non-Python test and backend-feature work, because the old texts called the table authoritative everywhere and the two Use-when clauses matched any test or backend feature.
- **Signal:** Over the next 3 test plans that plan-critic reviews in a non-Python repository, or by 2026-12-28, whichever comes first: confirm if none gets a finding for not using a pack's level names and neither Python convention skill loads in those sessions; refute if one plan gets such a finding or one of the two skills loads on non-Python work; inconclusive with fewer than 3 such plans.
- **Risk:** The host decides loading from the description, which only a transcript shows; a repository that states no testing conventions now falls back to the generic levels, which can read as a weaker plan.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Make fifteen shipped skills read as written in any consumer: the project's own conventions and names, labelled one-repository examples, and no false claim about which skill a model may not invoke

### [SKILL-MODIFIED] Log analysis in a repository with its own task prefixes and id names files no task under a reserved prefix and counts distinct ids
- **Category:** Coverage
- **Hypothesis:** By making the task prefix, the correlation field, the pin location and the brief sources project-supplied, we expect an analyze-logs run in a repository that reserves the new-work prefix and spells its ids differently to file no task under the reserved prefix and to count distinct ids with a grep that matches lines, because the skills no longer name one project's prefix or ids.
- **Signal:** Over the next 3 analyze-logs runs in a repository whose AGENTS.md names its own task prefixes or id fields, or by 2026-12-28, whichever comes first: confirm if no task file uses a prefix the project does not name and every distinct-id count comes from a grep that matched lines; refute if one does either; inconclusive with fewer than 3 runs.
- **Risk:** A project that names neither prefixes nor a correlation id row gets no default, so a run may file nothing where it filed something before; renaming the Step 1a row the grep points at leaves every test green.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Make fifteen shipped skills read as written in any consumer: the project's own conventions and names, labelled one-repository examples, and no false claim about which skill a model may not invoke

### [SKILL-MODIFIED] Adopters in another stack stop copying one repository's idiom, source root or CI job from the planners and reviews
- **Category:** Consistency
- **Hypothesis:** By labelling the stack-specific samples as one repository's examples, taking `<source-roots>` in the chokepoint search and swapping the learnings example for a language-neutral one, we expect adopters in another stack to stop copying a try/except routing layer, a `backend/` root or a lint, typecheck and pytest CI job into their own learnings entries, plans and reviews, because the text no longer reads as their project's rule.
- **Signal:** By 2026-12-28 (calendar backstop), sample the learnings entries, planner tables and review outputs both consumers wrote after this change: confirm if none carries the try/except routing idiom, a `backend/` pathspec or a three-gate CI job that the consumer's own stack lacks; refute if one does; inconclusive if fewer than 5 such artifacts exist by then.
- **Risk:** learnings-format Examples 2 to 4 and several worked examples still name one repository's stack, so a copy can still come from there, and a sample of 5 says little.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Make fifteen shipped skills read as written in any consumer: the project's own conventions and names, labelled one-repository examples, and no false claim about which skill a model may not invoke

### [SKILL-MODIFIED] Plan reviews cite no one stack's rules and stop at the second run
- **Category:** Quality
- **Hypothesis:** By replacing eight project-specific rules with a read of the project's own conventions and capping a document at two runs, we expect plan reviews in a repository whose AGENTS.md states none of those rules to raise no finding that cites one and to end at the second run, because the skill no longer carries the rules and its per-artifact paragraph makes the re-run the second and last.
- **Signal:** Over the next five plan-critic runs in such a repository, or by 2026-12-28, whichever comes first, read each run's findings and its document's run count in the transcript: confirm if none cites a feature layout, a file rule, a migration tool, an auth client, a config module, a prompt step or a test decorator, and no document gets a third run; refute if one does either; inconclusive with fewer than five runs.
- **Risk:** A project that relied on the old bullets without stating them stops getting those checks, and the cap relies on the session electing to stop, so it can also end a review before a real defect is found; neither shows unless transcripts are read.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Make plan-critic read the project's own conventions and stop at two runs, have an opted-out project state its own agent cap, and add an opt-in shell-prefix hook with registrations that fail open

### [SKILL-MODIFIED] Plans for an opted-out project name the project's own agent cap
- **Category:** Coverage
- **Hypothesis:** By adding a placeholder under the execution-plan template's derivation 3 and a sentence to the roadmap template's constraints section that say an opted-out project still states its own cap on simultaneous agents, we expect the plans written for such a project to name that cap instead of showing "not applied: project opt-out" alone, because a planner fills the slots its template hands it and before this change no slot asked for a cap.
- **Signal:** In the next 3 `execution-plan.md` or `roadmap.md` files the planner writes under `.specs/` for a project that opts out, or by 2026-12-28, whichever comes first: confirm if each names the project's own cap in derivation 3 or the constraints row (a number from its AGENTS.md, or an explicit "none stated"); refute if one shows only "not applied: project opt-out" or the placeholder left unfilled; inconclusive with fewer than 3 such files.
- **Risk:** It relies on a planner electing to fill the placeholder; a project that states no cap leaves only "none stated" to read; the planner SKILL.md does not carry the cap sentence, so a plan written without the templates is not covered.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Make plan-critic read the project's own conventions and stop at two runs, have an opted-out project state its own agent cap, and add an opt-in shell-prefix hook with registrations that fail open

### [INFRA-MODIFIED] A project that switches the shell-prefix hook on retries a denied call in a working form, with no false denial
- **Category:** Consistency
- **Hypothesis:** By refusing, in a project that sets `enabled` in `.ai/shell-prefix-hook.json`, a shell call that moves the persistent working directory, shadows `cd` or starts with an assignment, each with a message that names remedies that work, we expect that project's sessions to retry a denied call in one of the named forms rather than in a disguise, and no ordinary command to be denied, because each denial names a form to retry with and the switch file is read on every call.
- **Signal:** Over the next 20 session transcripts of the first project that switches the hook on, or by 2026-12-28, whichever comes first: count the hook's denials and read each; confirm if none is a false positive and no session retries a denied shape in a disguise more than once; refute if one denial is a false positive or one session retries a disguise twice or more; inconclusive if no project has switched the hook on by then or fewer than 5 sessions ran with it on.
- **Risk:** The hook is off by default, so the window may close with no project switched on; a session can route around it through a wrapper the docstring lists as a limit (a path to `env`, `command export`), which a denial count reads as compliance; and while off it still starts a process per shell call for every Core user.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Make plan-critic read the project's own conventions and stop at two runs, have an opted-out project state its own agent cap, and add an opt-in shell-prefix hook with registrations that fail open

### [INFRA-MODIFIED] A completion review starts from a printed list of its mechanical checks
- **Category:** Coverage
- **Hypothesis:** By giving the post-task review a script that prints the changed files (untracked ones included), the raw diff stat against the plan, Step 0's dependents with the count of files searched, line endings, lint scope and the matrix lookups, we expect the next completion reviews to carry a dependents list with every reader marked and a comparison of the changed files against the plan even when the session is near its context line, because those lists no longer have to be recalled and retyped from commands with known blind spots.
- **Signal:** In the next 5 completion reviews, or by 2026-12-28, whichever comes first: confirm if at least 4 of 5 review reports carry the script's summary line or an equivalent list, name each dependent as checked or UNKNOWN, and state the diff-against-plan result; refute if 2 of the 5 skip Step 0's list or the plan comparison with the script available, or if one reads a zero or a capped list from the script as complete; inconclusive with fewer than 5 reviews.
- **Risk:** The script names symbols only from definition lines of code files, finds readers by name and not by call, and caps its lists, so a review may read its output as the whole blast radius; a session short of context may run it and skip the judgment steps, which is the shrinkage this change is meant to prevent, now with a tool's authority behind it.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Give the post-task review a script that prints its mechanical checks

### [INFRA-MODIFIED] A kickoff's paste line is printed, filled and obeyed before the first write
- **Category:** Quality
- **Hypothesis:** By putting six rules in a section of the brief template (a printed paste line, a stop on any `<...>` placeholder, the return note as the first write, a standing decision over a session default, preconditions as commands with expected results, and a stated meaning for a plain affirmative), we expect the next dispatch briefs written from it to ship no paste line with an unfilled placeholder and no kickoff that says "any other reply is a no" without saying what "yes" permits, because the template now names each rule and its reason.
- **Signal:** In the next 3 dispatch briefs or kickoffs written from the template, or by 2026-12-28, whichever comes first: confirm if each paste line was printed by a command and holds no `<...>` or `$(...)`, each brief names its return note as its first write, and each kickoff that says "any other reply is a no" says what a plain affirmative permits; refute if one ships an unfilled placeholder in its paste line or leaves a plain affirmative undefined; inconclusive with fewer than 3 such briefs.
- **Risk:** The section adds 28 lines to a template a worker reads in full, and a brief that restates the rules inline would crowd out its task-specific text; a delegate whose tools offer no create-if-absent operation cannot follow the first-write rule as written.
- **Status:** PENDING
- **Changelog ref:** 2026-11-02 — Put six dispatch-brief rules in the brief template, and add two short lessons about background runs and peers

## 2026-11-01

### [SKILL-MODIFIED] A review's reader sweep names a file the task created and has not added
- **Category:** Coverage
- **Hypothesis:** By running `git ls-files --others --exclude-standard` and `git grep --untracked` in Step 0 and telling a brief's file-set sweep to count untracked files, we expect the dependents lists of the next reviews and dispatches to include the task's new files that are not yet added, because plain `git grep` and `git diff HEAD` read tracked files only.
- **Signal:** In the next 3 reviews of tasks that add a file a test or a doc reads, or by 2026-12-27, whichever comes first: confirm if each review's dependents list names the new file and says which form of the sweep ran; refute if one omits the file or names no form; inconclusive with fewer than 3 such reviews.
- **Risk:** Step 0 lists more files (a peer's new files, unignored scratch) that must be sorted by owner, and `git grep --untracked` still skips ignored files.
- **Status:** PENDING
- **Changelog ref:** 2026-11-01 — Count untracked files in every sweep, give verifiers controls, make the cleanup audit and the seam check refuse a guess, and keep the spec text project-neutral

### [SKILL-MODIFIED] A return that confirmed a planted control is not used as verified
- **Category:** Quality
- **Hypothesis:** By telling the dispatcher to give each verifier and each fresh reader one to three controls (real claims with one fact changed) and to trust a return's confirmations only if it rejected every control, we expect no return that confirmed a control, or gave no verdict on one, to be used as verified, because a pass never shown a false claim cannot be told from one that confirms every claim, and the rule makes such a return unverified instead of merged.
- **Signal:** In the next 5 verifier or fresh-reader returns whose brief carried at least one control, or by 2026-12-27, whichever comes first: confirm if each such return either rejected every control it was given or was treated as unverified, its confirmations re-run before anything they covered was merged; refute if a return that confirmed a control, or gave no verdict on one, was used as verified; inconclusive under 3 such returns.
- **Risk:** It relies on a dispatcher electing to plant the controls, each costs one more claim per pass, and a control's verdict applied to the artifact would edit a claim it never held, which is why the key stays out of it.
- **Status:** PENDING
- **Changelog ref:** 2026-11-01 — Count untracked files in every sweep, give verifiers controls, make the cleanup audit and the seam check refuse a guess, and keep the spec text project-neutral

## 2026-10-30

### [SKILL-MODIFIED] A continuation hand-off written under the planner passes the hand-off lint
- **Category:** Quality
- **Hypothesis:** By rewording the planner's usage-wall hand-off so its `## Status` reads `in-progress — post-task-review not run`, we expect the continuation hand-offs written under it to pass `lint handoffs` on the Status vocabulary, because the retired `Status: incomplete` wording failed that check in a measured probe.
- **Signal:** Over the next 3 continuation hand-offs written under the reworded planner, or by 2026-12-30, whichever comes first, run `lint handoffs` on each: confirm if none reports a Status error; refute if one that follows the planner's sentence still fails the Status check; inconclusive with fewer than 3 such hand-offs.
- **Risk:** Plans copied into other projects keep the old wording until they are refreshed, and a reader that keys on the status word sees only `in-progress`.
- **Status:** PENDING
- **Changelog ref:** 2026-10-30 — Review at every completion event, a project switch for the usage gate, a named writer for ledger entries, a sequencing check, a re-plan sweep and a fetch-summary rule

### [SKILL-MODIFIED] The completion review runs at the close of a task of any size
- **Category:** Coverage
- **Hypothesis:** By naming every completion event in the review's description, its activation list, the seeded checklist and orchestrate's brief line, we expect the operator to have to ask for the review or the self-challenge by hand in fewer sessions, because a size limit of 3 or more files stood in all four places.
- **Signal:** In the first retrospective that covers sessions run under this text, or by 2026-12-30, whichever comes first, count the sessions in which the operator typed a request for the review or the self-challenge: confirm if the share is under half of the 23 of 66 sessions (a floor) the earlier retrospective counted; refute if it is the same or higher.
- **Risk:** More review runs on small tasks for every consumer, because the description decides when the model calls the skill; a project whose own AGENTS.md keeps the size limit is not reached by this change.
- **Status:** PENDING
- **Changelog ref:** 2026-10-30 — Review at every completion event, a project switch for the usage gate, a named writer for ledger entries, a sequencing check, a re-plan sweep and a fetch-summary rule

### [INFRA-MODIFIED] A proceed is classified before it is counted as feedback
- **Category:** Quality
- **Hypothesis:** By telling a retrospective to classify the assistant message above a "proceed" before counting it as feedback, we expect the next retrospective reports to stop listing restarts after a limit or a guard wait among corrections, preferences and redirections, because the schema reference now names that kind, gives its share (about 90% in the one corpus measured) and says what a bare "proceed" after a completion report means.
- **Signal:** Over the next 2 retrospective runs whose session store holds at least one message that opens with "proceed", or by 2026-12-30, whichever comes first: confirm if neither report lists such a message after a platform stop or a guard wait as a correction, preference or redirection, and every "proceed" a report does list names the message above it; refute if a report lists a restart as feedback or lists a "proceed" without naming what preceded it; inconclusive if fewer than 2 such runs happen.
- **Risk:** The share comes from one corpus and may not hold in another; a reader who files every "proceed" as a restart would hide a real premature-completion finding, which is why the paragraph names that kind too.
- **Status:** PENDING
- **Changelog ref:** 2026-10-30 — Say how to read a message that opens with proceed, and add six short evidence lessons to existing skills

### [INFRA-MODIFIED] A branch switch starts from a backup that exists
- **Category:** Quality
- **Hypothesis:** By making the pre-switch backup one command that starts with `python`, writes under the git directory and exits non-zero on any failed step, we expect every model-initiated branch switch to be preceded by a complete six-file backup folder and a quoted path, because the old block's assignment-led first line, its unignored folder and its same-day overwrite no longer exist.
- **Signal:** Over the next 3 model-initiated branch switches, or by 2026-12-30, whichever comes first: confirm if each is preceded by a folder under the git directory's `pre-switch-backups` holding all 6 files, the session reports its path before switching, and no run of the backup command is denied by a shell guard; refute if a switch happens with no such folder or the command is denied; inconclusive if fewer than 3 switches happen.
- **Risk:** A machine whose `python` is not on the path under that name fails the command, and by design the switch then waits; a repository with an unwritable git directory does the same.
- **Status:** PENDING
- **Changelog ref:** 2026-10-30 — Back a branch switch up with a script, make the projection certifier say what it did not check, and add four short lessons to existing skills

## 2026-10-29

### [SKILL-MODIFIED] Put the hypothesis verdicts in the plan the operator approves
- **Category:** Observability
- **Hypothesis:** By running the validator's Steps 1 to 4 before the Phase 3 gate and putting its verdict table and ledger-state line in the plan, we expect consolidation runs to stop skipping `hypothesis-validator`, because the plan the operator approves now shows an empty section without it.
- **Signal:** Over the next 2 consolidation runs, or by 2026-12-23, whichever comes first: confirm if each run's changelog entry or gate record carries the line `N PENDING · M terminal · last verdict <date>`; refute if either run has none; inconclusive if fewer than 2 runs happen.
- **Risk:** The validator's reads now happen before approval, so a run that stops at the gate pays for them; its writes still wait for Phase 6.5.
- **Status:** PENDING
- **Changelog ref:** 2026-10-29 — Make the landing audit refuse to guess, give the lint a ledger-growth note and a one-file hand-off mode, and print every CLI command in one runnable form

### [INFRA-MODIFIED] The lint prints the meta-synthesis note the validator waits for
- **Category:** Observability
- **Hypothesis:** By printing `NOTE: meta-synthesis due` at 10 terminal verdicts not yet covered by a synthesis, we expect the next ledger that reaches 10 to get its meta-synthesis in the following consolidation pass, because the note fires for whoever runs the lint and nobody has to remember the count.
- **Signal:** In the first ledger that reaches 10 uncovered terminal verdicts after this ships, or by 2026-12-23, whichever comes first, read its `Last meta-synthesis` marker: confirm if the marker moved within two consolidation runs of the note first printing, refute if the note printed in both runs and the marker did not move, inconclusive if no ledger reaches 10.
- **Risk:** A ledger whose marker is never updated keeps printing the note; it is a note, so no gate fails on it.
- **Status:** PENDING
- **Changelog ref:** 2026-10-29 — Make the landing audit refuse to guess, give the lint a ledger-growth note and a one-file hand-off mode, and print every CLI command in one runnable form

### [SKILL-MODIFIED] Print every support-CLI command in one form that runs where it is read, and name the retrospective's proposals seam
- **Category:** Quality
- **Hypothesis:** By printing each support-CLI command in the one form measured to run from an installed plugin copy, with the project named and a CI test that parses every printed line, we expect a session that follows a printed lint or audit line to get its project's verdict instead of an import error or a pass over the plugin's own directory, because the line now sets nothing first and carries an absolute `--project`.
- **Signal:** Over the next 2 retrospectives or by 2026-12-23, whichever comes first, Grep the emitted digests for `No module named lemmi_ai_kit` and for a printed lint or audit run without `--project`: confirm at 0 in both, refute if either shows one, inconclusive if no session ran a printed command.
- **Risk:** It helps only a session that runs the printed line; one that retypes a shorter command still passes `lint all` without `--project`, because the CLI does not fail closed.
- **Status:** PENDING
- **Changelog ref:** 2026-10-29 — Make the landing audit refuse to guess, give the lint a ledger-growth note and a one-file hand-off mode, and print every CLI command in one runnable form

### [INFRA-MODIFIED] Read a checker's one-number output, run a checker script without a shell, and find a citation's file from a scratch export
- **Category:** Quality
- **Hypothesis:** By reading a bare-integer checker output as its count and offering a shell-free `--script` mode, we expect sessions to certify a sound checker as CAN-SEE on the first run, because the two causes of a false UNUSABLE verdict (a lone "0" counted as a line, a pattern mangled by the platform shell) no longer arise.
- **Signal:** Inspect the next two sessions that quote a `probe_checker` verdict, or look by 2026-11-29, whichever comes first, counting verdicts that read UNUSABLE for a checker later shown sound and invocation errors that needed a second attempt. Confirm if both counts are zero; refute if either recurs with the new default.
- **Risk:** A checker that deliberately prints one line holding only a number is now read as that number, so an exact-count expectation can shift; `--count-mode lines` restores the old reading.
- **Status:** PENDING
- **Changelog ref:** 2026-10-29 — Read a checker's one-number output, run a checker script without a shell, and find a citation's file from a scratch export

## 2026-10-28

### [SKILL-MODIFIED] Keep every operator turn in the session digests, cite the lines Grep shows and count each event once
- **Category:** Observability
- **Hypothesis:** By keeping the operator turns the 120 KB cap cut off, reading mid-turn messages and question answers as operator turns, and numbering the sweep's citations by LF alone, we expect the next retrospective to find the operator's closing words in every capped digest and to cite lines that Grep and Read confirm, because one structural predicate now decides what an operator turn is for every digest and the sweep no longer reads through universal newlines.
- **Signal:** In the next retrospective run over at least 10 sessions after the installed Core plugin carries this change, or by 2026-12-09, whichever comes first, check with Grep and Read on the raw transcripts and the digests, not with the extractor. For each digest that carries the line `[...transcript truncated at 120 KB...]`, find the last human-origin record of its transcript (`origin.kind` human, typed or mid-turn) and confirm its words are in the digest; for 30 citations of `user_corrections_sweep.txt` (all if fewer), Read the cited line and confirm it is the `USER:` line that starts the quoted text. Confirm if every check agrees; refute if one capped digest lacks its last operator turn or one citation names another line. Fewer than 3 capped digests or fewer than 10 citations leaves it inconclusive. The same checks fail on the previous scripts: over 206 real sessions 84 of 136 citations named another line, and 29 of 31 capped digests had operator turns after the cut that the digest did not hold.
- **Risk:** The operator section sits outside the 120 KB cap, so the longest digests grow (over those 206 sessions the largest went from 125,638 to 129,356 bytes, the largest section being 6,290 bytes) and a deep read costs a little more context. The structural rule decides only for records that carry an origin stamp: 1,104 of the 2,692 user records without a tool result in that sample carry none, and for those the prefix list still decides. Nothing resolves this unless a session runs a retrospective and does the checks by hand.
- **Status:** PENDING
- **Changelog ref:** 2026-10-28 — Keep every operator turn in the session digests, cite the lines Grep shows and count each event once

## 2026-10-27

### [INFRA-MODIFIED] Collect the skill tests in CI, rebuild the learnings guard's shell arm and fix the extractor's rejection count
- **Category:** Quality
- **Hypothesis:** By judging a shell command the way a shell reads it, we expect the learnings drain guard to deny far fewer reads and appends, because about nine in ten of the 96 denials the old guard gave in a replay of recorded commands were read-only inspections, appends or writes to other files.
- **Signal:** Over the next 30 days of recorded sessions, or the next 40 denials of this guard, whichever comes first, classify each denial of a shell command by reading the command. Confirm if fewer than 10% are plain reads or appends; refute if more than a quarter are. A python script that reads the file and writes another is a known false positive and is counted separately, not here. Fewer than 20 denials leaves the hypothesis inconclusive.
- **Risk:** A guard that denies less can let a rewrite through; the python-on-stdin shape is now denied, but the known gaps listed in its docstring remain open.
- **Status:** PENDING
- **Changelog ref:** 2026-10-27 — Collect the skill tests in CI, rebuild the learnings guard's shell arm and fix the extractor's rejection count

## 2026-09-14

### [SKILL-ADDED] Share portable flow mapping through Core
- **Category:** Coverage
- **Hypothesis:** By shipping the flow tools with explicit consumer roots and independent fixtures, we expect new projects to produce accepted flow maps without manual path repairs because validation no longer depends on the source checkout.
- **Signal:** Inspect the next two submitted flow-map changes outside the source project, or by 2026-11-09, whichever comes first, using their git diffs and review comments. Confirm if both are accepted without a manual tool-path repair; refute if either requires one. No qualifying submissions leaves the hypothesis inconclusive.
- **Risk:** Agents can over-read a structural pass as a truth claim; evidence review remains manual.
- **Status:** PENDING
- **Changelog ref:** 2026-09-14 — Share portable flow mapping through Core
