# Project Learnings

This file is a **lean intake buffer**, not a knowledge store. New lessons are appended here by the
`task-learnings` skill, then **periodically drained** to the agent-facing home where each lesson is
actually useful — so this file normally holds only a handful of not-yet-promoted entries.

**Where the knowledge lives (consult these, not one big flat file):**
- **Universal conventions & anti-patterns** → `AGENTS.md` (always loaded).
- **Cross-cutting patterns** → the relevant skill (project-local `.claude/skills/`; kit skills are plugin-managed).
- **Subsystem conventions & gotchas** → the code-adjacent **module / feature `README.md`**.
  **When you work in a subsystem, consult that subsystem's README** — that is where its
  promoted lessons live.
- **Invariant-guarding gotchas** → a co-located code comment at the exact site it guards.

**How entries are added:** `task-learnings` appends each finding as a `### [YYYY-MM-DD] title` block
under the matching `## Category` header (create the header if absent; use a canonical category —
Architecture Decisions, Common Pitfalls, External Service Quirks, Performance Insights, Pattern
Discoveries, Convention Clarifications, Interaction & Workflow Friction). Place each entry under
its **topic** category, never at the file end (a chronological catch-all misleads the
consolidator's clustering).

**How it drains:** periodically (`/learning-consolidator`, ~weekly) each accumulated entry is routed
to its home above and removed here.

---

## Common Pitfalls

### [2026-10-29] A lint run with no --project from the plugin's own folder measures that folder and passes
- **Context**: Giving every printed support-CLI command `--project` and running the printed forms from a foreign working directory.
- **Finding**: `find_project_root` returns its starting directory when no ancestor holds a project marker, and a printed command runs under `uv --directory <plugin root>/src`, so without `--project` the working directory is the plugin's own folder. `lint all`, `lint`, `lint handoffs` and `audit-skills` then exit 0 with "LINT PASSED (0 finding(s))" over nothing, while `lint changelog` and `lint learnings` exit 2 ("no such file"). A relative `--project .` resolves inside the plugin the same way.
- **Impact**: Read a clean lint as evidence only when the run named an absolute project root, and never from a printed form that lacks one. Failing closed in the CLI (cannot measure is never a pass) is an open decision, not a built change.
- **Category**: pitfall
- **Home**: comment:plugins/core/src/lemmi_ai_kit/checks.py:find_project_root
- **Enforce-via**: test
- **Verify-at**: tests/test_printed_commands.py
- **Scope**: durable

### [2026-11-03] A rule pasted into every brief must work for every kind of worker the brief goes to
- **Context**: The Close block of the brief contract is pasted into every brief, and its step 2 told the worker to run the completion review through the Skill tool.
- **Finding**: A worker run by an external agent CLI has no Skill tool, so the step could not be done as written there, and nothing in the block said what such a worker does until one sentence was added to step 2; step 3 still names the skill the same way.
- **Impact**: Beside a rule that every brief carries, list the kinds of worker the brief goes to (a native sub-agent, each external CLI) and ask of each whether it can follow the rule as written; put the fallback in the rule itself.
- **Category**: pitfall
- **Home**: skill:orchestrate
- **Enforce-via**: test
- **Verify-at**: tests/test_brief_close_block_wording.py
- **Scope**: durable

### [2026-11-04] A shared list file that another tool rewrites on Windows can carry carriage returns, and a shell loop that reads it makes them part of every name
- **Context**: Building a chain of scratch commits from a package list that another session rewrites while the chain is being built.
- **Finding**: The list was rewritten with CRLF line endings between two runs (the file grew from 42 to 60 bytes). `read -r id` kept the carriage return, so every patch name read `<name><CR>.patch` and the build stopped with a message naming a file that exists. The Python readers of the same file split on whitespace and were not affected.
- **Impact**: Strip carriage returns at every shell read of a file another tool may rewrite (`${id//$'\r'/}` or `tr -d '\r'`), read such lists with a whitespace split in Python, and fire the loader once at a CRLF copy before trusting it.
- **Category**: pitfall
- **Home**: agents-rule
- **Enforce-via**: prose
- **Verify-at**: AGENTS.md
- **Scope**: durable

### [2026-11-04] A replace-once edit whose old text is the first words of its new text applies again on every run
- **Context**: Writing a re-runnable script that applies a review's 16 exact text replacements to a record, three ledgers and a test docstring.
- **Finding**: One item replaced a sentence with the same words plus a new sentence, so the old text was still present after the edit and the first version of the script appended the new sentence again on the second run (it printed 1 applied and 15 already applied). An item whose old text is not inside its new text does not do this, and only a second run showed it.
- **Impact**: Test whether the new text is already present before testing the old text, and run every edit script twice before it is committed, expecting it to say nothing to do the second time.
- **Category**: pitfall
- **Home**: agents-rule
- **Enforce-via**: prose
- **Verify-at**: AGENTS.md
- **Scope**: durable

### [2026-11-06] A trimmed test file keeps dead machinery when a kept test is an instrument table over removed checks
- **Context**: Trimming 24 files to their provable tests with a script that keeps the named tests and the helpers they reach.
- **Finding**: `tests/test_consolidation_text.py` still held 808 lines for 7 tests, because its kept planted-positive test fired controls at the checks of pins that were removed; 194 lines in 18 helpers were reached only by that test and applied to no real file. A detector (helpers reached only by tests whose names say planted, sees, spares or flags) found it, and removing the whole statements of the test that used those helpers brought the file to 463 lines. The same script also wrote a kept test's cooked docstring text into a generated module docstring, and a backslash in it raised a DeprecationWarning; escape backslashes and triple quotes when generated text goes back into a source literal.
- **Impact**: After a trim, list the helpers that only instrument tests reach and read each flagged file; and run the trimmed files with `-W error::DeprecationWarning`.
- **Category**: pitfall
- **Scope**: durable

### [2026-10-29] A prompt that names one note can miss a newer note of the same family written the same day
- **Context**: A session was dispatched with a prompt that named one change-request note, and that note had been superseded the same day by a second version the prompt did not name.
- **Finding**: The named note said on its third line that a newer note in the same folder, written the same day and holding 28 items against its 10, superseded it; the prompt named only the old one.
- **Impact**: Before reading a note a prompt names, glob its source folder for a newer file of the same family.
- **Category**: pitfall
- **Home**: skill:orchestrate
- **Enforce-via**: prose
- **Verify-at**: plugins/orchestration/skills/orchestrate/references/dispatch-gates.md
- **Scope**: durable

### [2026-10-30] A skill-directory variable passed in another skill's arguments is replaced by that skill's folder
- **Context**: A skill invoked another skill and passed it a path written with the skill-directory variable.
- **Finding**: The variable in the arguments was replaced with the invoked skill's own folder, not the caller's, so the path pointed into the wrong skill (one record in a return note, not re-tested).
- **Impact**: Describe such a path in words, not as a skill-directory variable in another skill's arguments.
- **Category**: pitfall
- **Home**: skill:skill-reviewer
- **Enforce-via**: prose
- **Scope**: durable

## Performance Insights

### [2026-11-06] Removing 83 wording-test files cut the test count in half and the suite time by nothing
- **Context**: The sentence-pin removal (83 files, 1,750 items) was expected to be partly a speed gain.
- **Finding**: `pytest --collect-only` went from 4,782 to 2,412 items, but the six-process split's longest process went from 171 s to 181 s (the files are dealt differently to the processes), and the 83 removed files run in 11 s serially against about 560 s of process time in all. Substring and count tests cost milliseconds; the time is in the tests that start hooks, scripts and git.
- **Impact**: Do not promise a faster suite from removing wording tests, and measure the removed files alone (`pytest <files> --durations`) before writing any time claim; the case for removal is maintenance and false reds.
- **Category**: performance
- **Scope**: durable

## Interaction & Workflow Friction

### [2026-11-08] A classifier of objective tests built from code signals misses the objective checks that live inside prose files, and only a full cold read shows how many
- **Context**: The sentence-pin removal classified 135 test files with two code-signal detectors and independent reads of the 19 flagged files; five more files were found by chance to compare a stated count with the list it counts.
- **Finding**: A cold re-read of all 83 removed files and of what was dropped from 24 trimmed files, by twelve independent readers, marked 63 of the 107 as holding at least one code-provable assertion that the tip leaves unguarded or half guarded (234 assertions: 64 covered, 52 partly, 118 not). The 24 refutations that ran refuted none (13 confirmed, 11 partly; 5 rated major). The kinds: counts against lists, forbidden-class scans, reachability of a reference from its SKILL.md, ids cited against headings, copies that must agree. A reachability probe found no orphan reference today; a table-shape probe found one malformed row (an unescaped pipe in a code span) in a shipped skill that no removed test covered either.
- **Impact**: Before a bulk deletion of tests, have someone other than the classifier read every file, and restore each recurring class as one generic check (reachability, table shape, cited-heading resolution) instead of keeping per-file pins or accepting the loss silently.
- **Category**: interaction
- **Scope**: durable

### [2026-11-08] A verdict table and the appendix that drives the script can disagree, and the script's input wins
- **Context**: Twenty-four trims were applied by a script from a per-file keep list (an appendix) while the verdict table carried a note per file.
- **Finding**: For one file the note said to keep the one test that derives the score bands from the skill; the appendix listed four other tests, and the trimmer followed the appendix. The kept set held two skill pins and the control of a helper that no kept test applies to the real files, and the one invariant that mattered was gone.
- **Impact**: Generate the script's keep list from the verdict table (one source), or assert after the run that every test a note names is present at the tip.
- **Category**: interaction
- **Scope**: durable

### [2026-11-08] A rule against a practice needs the practice's origin traced by commit and by brief, and its live carriers fixed in the same change
- **Context**: The AGENTS.md bullet against sentence-pin tests was justified by the decision record's "named test" column prescribing a wording test per row.
- **Finding**: The column names a wording test in 5 to 7 of 28 rows. Most pins came from the passes' build method (test first, red on the old text, a planted removal) and from an untracked kickoff brief that still says every wording test fires at a planted removal. Live carriers were left after the first version of the change: seven intake entries that anchor on removed tests, of which five teach wording-test craft and name `agents-rule` or `skill:test-conventions` as their home (the next drain would have promoted them; they were marked superseded in the same change, and the two general lessons among the seven stay), and a sub-agent line of AGENTS.md that expected "a new test red on the old text and green on the patch" (reworded in the same change).
- **Impact**: Before writing a rule against a practice, trace its origin by commit log and by the briefs that drove it, grep the intake buffer and the always-loaded files for the practice's own instructions, and annotate or reword each carrier in the same change.
- **Category**: interaction
- **Scope**: durable

### [2026-11-08] Broken shell quoting is the top sub-agent error shape, so run a multi-line probe from a file
- **Context**: First session retrospective, 2026-10-25 to 2026-11-08 (41 sessions, 792 sub-agents, 14 deep-dives).
- **Finding**: "unexpected EOF while looking for matching" appears in 21 of the 150 emitted sub-agent transcripts, from 12 parent sessions, the most common shape by transcripts (second by hits, 26 against 27 for never-read edits); the deep-dives add heredocs that mangled a regex, `python -c` with backslashes, backticks run inside double quotes, and nested quotes passed from PowerShell into a container. The taxonomy files all 26 emitted hits as runtime-exit, so they read as failed runs.
- **Impact**: Write a multi-line probe to a file in the scratch directory and run it by path; never pass a script or a regex through a second shell layer. The worker preamble already asks for a script file, but only for the `NAME=` hook's case; widen that line.
- **Category**: interaction
- **Home**: skill:agent-delegate
- **Enforce-via**: template
- **Verify-at**: plugins/orchestration/skills/agent-delegate/assets/worker-preamble.md
- **Scope**: durable

### [2026-11-08] The Edit tool needs a Read-tool read first, and a shell view does not count
- **Context**: First session retrospective, 2026-10-25 to 2026-11-08, sub-agent deep-dives.
- **Finding**: Two sub-agents each lost a batch of 6 edits to "File has not been read yet. Read it first before writing to it." on files they had only viewed with `cat` or `sed`. The extractor's `edit-stale-read` class (99 hits in 13 sessions) also counts "File has been modified since read"; in the 150 emitted transcripts the split is 27 never-read to 11 modified-since-read.
- **Impact**: Read each file with the Read tool before its first Edit, even after viewing it in a shell.
- **Category**: interaction
- **Home**: skill:agent-delegate
- **Enforce-via**: template
- **Verify-at**: plugins/orchestration/skills/agent-delegate/assets/worker-preamble.md
- **Scope**: durable

### [2026-11-08] Hand off at a wave boundary before the context runs out
- **Context**: First session retrospective, 2026-10-25 to 2026-11-08, session deep-dives.
- **Finding**: In 3 of the 8 deep-dived sessions the context ran out before a hand-off was written: in 2 the operator had to order the hand-over, and 1 worked to 7.58 MB past the operator's 5 MB line. The orchestrate skill already says to hand off on a leading trigger and to state the hand-off decision at every wave boundary (in the kit since 2026-08-23), but none of the 3 sessions invoked that skill.
- **Impact**: Do not add more wording to orchestrate: put the wave-boundary decision ("continuing, N waves left" or "handing off") where these sessions read it, as a line in the kickoff and hand-off templates that `lint handoffs` checks.
- **Category**: interaction
- **Home**: skill:orchestrate
- **Enforce-via**: lint
- **Verify-at**: plugins/core/src/lemmi_ai_kit/assets/ai/templates/handoff.md
- **Scope**: durable
