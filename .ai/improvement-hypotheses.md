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
