---
name: post-task-review
metadata:
  type: workflow
description: >
  Comprehensive post-task review including code review, convention compliance, documentation
  impact analysis, and learnings extraction. Extends the existing task-completion-review
  process with two new mandatory steps. Use after completing any major task (3+ files
  modified, new feature, significant refactoring, or spec task completion).
---

# Post-Task Review — Comprehensive Completion Process

## When This Skill Activates

Run this review when any of these conditions are met:

- A new feature or significant functionality was implemented
- Refactoring touched 3 or more files
- A spec-driven development task was completed
- A bug fix revealed a systemic issue
- The human explicitly requests a review
- Any task that created or modified database migrations

## Review Pipeline

The review consists of 8 steps, executed in order. Steps 1–6 cover code review
and convention compliance. Steps 7–8 are documentation and learnings extensions.

### Steps 1–6: Code Review and Convention Compliance

1. **High-Level Conceptual Review** — Does the solution align with requirements? Any design flaws?
2. **Detailed File-by-File Review** — Check every function for correctness, edge cases, resource cleanup
3. **Project Conventions Review** — Imports, one-class-per-file, feature structure, logging, exceptions (see AGENTS.md § Conventions).
4. **Self-Challenge** — Ask adversarial questions: "What could go wrong?", "What if input is empty?"
   Three verified traps to include: (a) any claim grounded in a NAMED config/settings field is
   unverified until the field's description/usage is read — a name that pattern-matches the claim
   ("tolerance" ≈ leniency) is a false friend; (b) every COUNT written into a ledger/changelog entry
   (samples changed, files touched) must be recomputed from the diff at write time — working memory
   reliably holds an earlier edit-pass's number — and a figure CORRECT when written goes stale if
   editing continues afterwards, so write derived numbers in the LAST edit of the task, or scope
   them explicitly ("at the end of the review pass") — and when a change was applied partly by a
   script and partly by hand, **never quote the script's edit-list length as the change's size**:
   a 14-entry `EDITS` list plus 2 hand edits became "15" (neither number) in four documents in one
   pass, and every consistency check passed because the documents agreed with each other and only
   disagreed with the tree. Derive the figure from the backup→live diff, and say which quantity a
   count describes ("14 of the 16 edits are in this script"); (c) if the task appended to a shared `.ai/` data
   file, re-open the file's governing skill and re-validate your own entries against the CURRENT
   rules (a concurrent session may have tightened them mid-task; the lint enforces only a subset).
   Three more, all from reviews that *looked* thorough and were not: (d) **tracing what the logic
   does is not a correctness review** — the trace must be diffed against the FORMAL reference
   (approved Gherkin scenarios / acceptance criteria) **line by line, by name**. An accurate trace
   that is never checked against the letter of an already-approved scenario reads as diligence but
   isn't: one self-review correctly traced that a PATCH route's new fallback let `resume_id` and
   `user_background` coexist, then documented it as an "accepted trade-off" — it silently violated
   the spec's own scenario ("Patch replaces resume personalization with a background… clears
   `resume_id`"), and an external P1 review caught what the self-review missed. (e) When a fix
   touches an N-boolean interaction, **enumerate the full 2^N truth table** and confirm test
   coverage for every cell — a bug report naming 2 of 4 quadrants tempts a fix-and-test-those-2
   response that leaves the rest unverified. (f) A behavioral claim documented in one place is very
   likely echoed in a sibling doc — **grep the SAME claim across ALL docs** (feature README vs.
   spec design.md) before considering a doc correction complete. (g) If the change **relocated a
   validation gate** ahead of a charge/dispatch/side-effect point, enumerate every upstream cause
   that can now reach it and check the existing message still tells the truth for each — a gate that
   absorbs new causes inherits the duty to name them. Moving the feedback answered-questions check
   pre-dispatch correctly stopped a doomed generation from consuming quota, and simultaneously made
   it the sole speaker for STT collapse, telling a candidate who had completed a full 350 s
   interview that they lacked answered questions: a silent failure became a confidently WRONG
   explanation. Stating a symptom as the cause is a new user-facing defect, not a neutral refactor.
   (h) If the fix landed in ONE implementation of a strategy/protocol seam, enumerate the siblings
   (grep the interface method) and check each before closing — including which implementation is
   the configured DEFAULT, since that is where an unfixed copy hurts most. A review comment naming
   the shared caller is evidence the defect lives at the seam, not in the leaf you opened first
   (the stereo/mono batcher pair: the sibling left unfixed was the default). **"Production doesn't
   run that implementation" is a traffic claim, not a safety argument** — dismiss a sibling by
   MECHANISM, in terms of its own code path, because a traffic-share dismissal expires the next
   time someone flips an env var. Resolve the default from the `Field(default=…)` AND every
   compose/cloudbuild pin, which disagree here: `STT__PIPELINE_MODE` defaults to `mono` in both
   `config.py` and `docker-compose.yaml` while only the cloudbuilds set stereo. The inverse shape
   is the same finding: **a bound/guard present in one implementation and absent in its sibling is
   a half-applied fix** — `MockStorageService` already had an LRU byte cap commented as "a dev-only
   memory leak" while the production `CloudStorageService` had none, and `local_storage_enabled`
   defaults to `False`, so the *unfixed* sibling was the one running in production. On finding a
   cap or eviction policy in any protocol implementation, open every sibling; and keep siblings
   behaviourally identical on the contract itself, or a test against the mock proves something
   untrue of production. (i) **Write the source next to any derived rate (X/day, N% of Y) at the
   moment you write it** — the citation is what makes a number falsifiable, and an uncited-but-true
   figure is one review pass away from being "fixed". An uncited "34 End-presses over ~4.5 days" was
   self-reviewed into a *wrong* correction by reconstructing a provenance from the nearest plausible
   neighbour; the real window sat in a task doc one file away, and the original number was right. A
   correction carries more authority than the claim it replaces, so before correcting anyone's
   number (including your own) search the whole artifact set, not the document you happen to have
   open — and read the staged-but-uncommitted diff, which is where the last session's findings sit
   unindexed. (j) **Before acting on a checker you wrote during this task, certify it with the seam** —
   `python "${CLAUDE_SKILL_DIR}/scripts/probe_checker.py" --cmd '<check with {file}>'
   --positive <must-match> --negative <must-not-match>` (exit 1 = blind or over-matching; paste its
   stamp beside the number). An in-session verifier gets less scrutiny than the artifacts it judges,
   yet its verdicts drive the edits. Five of one session's "blocker" findings were its own parsing
   bugs (quote-stripping, a leading `-` parsed as a grep option, an unanchored whole-file substring
   check); the failure is symmetric, since a silently-broken checker's clean pass would bless a
   defect. A zero or a wall of findings from an unprobed checker is unproven either way. **This
   step ran at task END for a month while the blind instrument had already driven the edits** —
   which is why the script exists and belongs at the moment the checker is written. Two shapes the
   probe cannot see for you: a manifest check cannot flag a file that was never in the manifest
   (pair it with a set-difference against the live tree), and a self-check whose fixtures share
   provenance with the code under test measures well-formedness, not validity.
   (k) **Reading your own side of a contract cannot establish what the other side populates.**
   Two claims about a resume-resolution contract were refuted this way: the producing side was never
   opened, and the consuming side's code was consistent with several possible producer behaviours.
   When a finding depends on what another component sends, read that component — or mark the claim
   UNKNOWN with both quotes. (l) **A scoped edit can be unfixable inside its scope, and the fix for a
   scoping finding is what exposes it** — when the correct fix requires a file the task excluded, say
   so and escalate; do not ship the best edit available inside the boundary and report it as the fix.
   (m) **A commit message written before the final git state is a prediction** — re-read it after any
   rebase, amend, or restack; two claims in one were falsified by a rebase that ran after it was
   drafted. (n) **In a reply you requested, the aside can be the finding** — a cross-repo answer's
   parenthetical "do not confuse this with X" WAS the result, and was nearly missed because the reply
   was read against the question list instead of read whole. Read a delegated answer for what it
   volunteers, not only for what you asked.
5. **Document Findings and Implement Fixes** — Fix each issue found with clear reasoning.
   **The fix pass is not safer than the original work, and the review that produced the fixes does
   not certify them.** Measured three times independently: a stacked-PR research round where *each*
   verification pass found defects introduced by the previous pass's fixes (2026-08-04); a prompt
   review whose fixes "introduced defects at roughly the rate they resolved them" (2026-08-19, RG1);
   and a plan revision whose second pass found three errors, **all three introduced by the first
   pass's own correction** (2026-08-19). So: re-run the review over the diff the fixes produced, not
   over the original artifact, and **re-derive every figure a fix touched** rather than carrying the
   pre-fix number forward. A correction carries more authority than the claim it replaces, which is
   what makes an unreviewed fix round expensive.
6. **Run Linting and Diagnostics** — `ruff check --fix` on all modified files, `read_lints` on all modified files

### Step 7: Documentation Impact Analysis

After code review is complete, check whether any project documentation needs updating.

#### 7a. Identify Modified Files

List all files that were created, modified, or deleted during this task.

#### 7b. Consult the Documentation Impact Matrix

For each modified file, check [references/doc-impact-matrix.md](references/doc-impact-matrix.md) to
determine which documentation files might be affected.

#### 7c. Read and Evaluate Affected Docs

For each potentially affected documentation file:

1. Read the current content
2. Check for:
   - **Stale information** — Does the doc describe behavior that changed? A documented *platform
     limitation* is a dated fact, not a permanent one: when a provider ships a feature adjacent to a
     documented workaround, re-verify the limitation before planning around it (WebSearch/WebFetch
     the changelog). State precisely which half moved — platform-limitation claims have two
     independently-movable parts, the constraint and the workflow step it forces, and a release can
     invert either alone. GitHub's stacked-PR preview did not remove the base-lock 422; it removed
     the *need* to fight it, so calling the 422 "historical" was wrong in the opposite direction.
   - **Missing information** — Does the doc omit new functionality? For any documented state
     machine or lifecycle, also ask which real-world terminations are ABSENT — omission misleads
     without contradicting: a status lifecycle can be true for every ordinary exception while the
     path that actually kills jobs in production (OOM/SIGTERM ⇒ `CancelledError`, a
     `BaseException`) walks past every documented handler. Document the kill path beside the happy
     path; a contradiction grep finds nothing here, so omission needs its own question.
   - **Contradictions** — Does the doc contradict the current implementation?
   - **Broken references** — Do links or file paths still resolve?
   - **Stale line-number citations** — if the task INSERTED code into any file a doc cites as
     `file.py:NN`, grep the doc for `<filename>:` and re-derive EVERY cited line (grep the symbol);
     "is the new row present?" and "are the existing rows still true?" are different questions, and
     the second is the one that silently breaks. Prefer symbol-anchored refs in new docs.
     **Partition the citations by owner before touching anything** — the re-derive rule says what to
     recompute, not whose file you may edit, and the single-writer rule says you may not touch
     another session's. Three cases: **yours** → fix, and switch to symbol anchors so the next
     insertion cannot break them; **another session's living doc** → do NOT edit, report the
     re-derived numbers so its owner can apply them (one 126-line insertion staled five sibling
     docs, two belonging to a different in-flight workstream); **a dated audit/retro artifact** →
     leave it, it was true at its date and rewriting it falsifies the record. Re-derive by symbol
     (`grep -n "def <name>"`), never by arithmetic on the insertion size — the same insertion moved
     one function 314→435 and another 526→663, different deltas in the same file.
3. If no issues found, move on

#### 7c-extra. Prompt Cross-Reference Sweep (when prompt files were modified)

When a behavioral feature is removed from or added to a prompt template:

1. Grep the entire prompt file (and all injected partials/persona files) for every phrase
   that implies or enables the removed/added feature.
2. A single stale reference in a downstream partial is enough for the model to revert to
   old behavior — treat every mention as load-bearing.
3. Check newly written sample phrases against the prompt's Prohibited Language and Variety
   sections to avoid introducing contradictions.

#### 7d. Update Documentation

For each doc that needs updating:

1. Update the content in-place to match the current implementation
2. Preserve the existing style and structure of the document
3. Do not create new documentation files unless the change warrants it (new feature README, new onboarding doc)
4. If a new feature was created, ensure it has a `README.md` in its feature directory

#### 7e. Report Results

In the review output, list:
- Which docs were checked
- Which docs were updated (and what changed)
- Which docs needed no changes

If no documentation was affected, explicitly state: "No documentation updates needed."

### Step 8: Learnings Extraction & Changelog

After the full review is complete, extract and record learnings.

Invoke the `task-learnings` skill to:

1. Review the entire task for discoveries, surprises, and corrections
2. Include findings from the review itself (steps 1–7) — if the review caught issues, those are learnings too
3. Classify findings as project-level or task-specific
4. Append project-level findings to `.ai/learnings.md`
5. Update project rules if any convention gaps were found
6. **If any AI infrastructure files were modified** during steps 1–7 (convention updates,
   skill modifications, rule additions), read the `ai-changelog` skill and
   append the appropriate changelog entry to `.ai/ai-changelog.md`
7. **After writing a changelog entry**, read the `ai-improvement-tracker` skill
   and evaluate whether the change warrants a testable improvement hypothesis

## Output Format

Present the review results using this structure:

```
## Post-Task Review

### 1. High-Level Assessment
{Summary of conceptual review findings}

### 2. Detailed Review Findings
{List of issues found with file:line references}

### 3. Convention Compliance
{Any violations of project conventions}

### 4. Self-Challenge Results
{Edge cases, race conditions, or other concerns identified}

### 5. Fixes Applied
{List of fixes implemented with reasoning}

### 6. Linting Results
{Summary of ruff and diagnostic results}

### 7. Documentation Impact
- **Docs checked**: {list}
- **Docs updated**: {list with brief description of changes}
- **No updates needed**: {list}

### 8. Learnings Extracted
- **Project-level findings recorded**: {count}
- **Rules updated**: {list of files updated, or "None"}
- **Summary**: {1-2 sentence summary of key learnings}

### 9. Step Inventory (REQUIRED — the operator reads this first)
| Mandated step | Ran? | Evidence / why not |
|---|---|---|
| Post-task review (steps 1–6) | yes/no | {what was reviewed} |
| Documentation impact (step 7) | yes/no | {files checked} |
| Learnings extraction (step 8) | yes/no | {entries appended} |
| `/review-prompts` (if `prompts/` touched) | yes/no/n-a | {gate record path} |
| Backend restart (if backend touched) | yes/no/n-a | {command} |
| {any other gate this task triggered} | yes/no | {…} |
```

## Important Notes

- Do NOT skip any step, even if the implementation seems perfect
- Step 7 (docs) must read actual file content before deciding — never assume docs are up-to-date
- Step 8 (learnings) should capture findings from the review itself, not just the implementation
- **Section 9 exists because prose did not work.** Four surfaces were told on one day that this
  review is mandatory, and the operator's rate of *demanding* it did not move — 27 sessions before,
  27 after. The dominant operator interaction in the measured window was auditing whether a mandated
  step actually ran, including auditing the retrospective itself; they asked "what is outstanding"
  five times in one session and restated a question verbatim after the first answer did not land.
  A step inventory is the cheapest thing that answers that question without being asked. Three rules
  keep it honest: **a "no" row with a reason is a valid result** and far better than a missing table;
  **"attempted, could not run" is its own state** — an environmental failure is neither a pass nor
  an open finding, so record it as blocked with the error, never silently omit the row; and
  **an informal self-review is not this gate** — reporting one as though it were satisfied the gate
  in name only and the operator had to ask for the real thing.
- **A staged delivery never fires the "task complete" event these gates hang off.** When work lands
  in phases behind approval gates, no single moment looks like completion, so the checklist silently
  never runs. Treat each approved stage as a completion for gate purposes, or say in the stage report
  which gates are deferred and to when.
- Be thorough but efficient — focus on real issues, not nitpicks
- If no issues are found in a step, explicitly state "No issues found"
- Always run the linter as the final step of code review (step 6) before proceeding to docs
- **Coverage audit for research/spec-driven tasks** (step 1/4): verify that EACH adopted research or
  spec finding actually shipped in the edited files — not just that what shipped is correct. "Is it
  correct?" and "did everything that should ship, ship?" are different gates; convert a spec's
  reconciliation/finding table into a checklist and tick each row against the diff. **A green suite
  cannot close this gate** — suite verdicts answer "does what exists pass?", never "does everything
  required exist?". Two clean runs, a `--collect-only` proof and a stable-tree bracket all failed to
  detect a task whose `integration_test` requirement had no test at all; the nearest candidate
  mocked out the very collaborator it should have covered, which is the specific shape that makes an
  integration file *look* like coverage of the interaction it disables. Tick each per-task "Test
  requirements" clause against the written tests **by name**, and when a requirement is met by
  construction rather than by assertion, record it explicitly as structural coverage or the next
  reader counts it as tested. Apply this to your OWN prose too: before writing "covered by X" in a
  Deviations Log or Status line, grep for the test symbol that actually calls the code — a correct
  trace of current behavior is not evidence a regression test exists. **For a multi-part change with
  a pre-edit backup, the backup→live diff is the scope-complete instrument, not the task's status
  line**: a prompt fix shipped "✅ DEPLOYED" with review and upload both green while an
  operator-approved rider in the same files was silently dropped — `diff backup live | grep '^>'` is
  a complete inventory of what actually changed, checkable against the approved scope item by item.
  When writing multi-part briefs, list scope items as grep-able markers so that check is mechanical.
- **Lint/refactor commits can hide behavioral deletions** (step 2): diff every file with a large
  net-negative line count and read the commit body for buried notes — a "ci: lint" commit can gut a
  feature. Orchestration surfaces (job-dispatch fan-out, executor payloads) need ≥1 test asserting
  the dispatch happened, and any dangling read-side check (e.g. a 425/job-status lookup) must still
  have a writer.
- **"Standardize X across files" tasks** (step 3): after applying the listed changes, grep for ALL
  remaining instances of the OLD pattern (and adjacent variations) — task-doc file lists routinely
  miss edge cases.
- **Rename/deprecation doc sweep** (step 7): after renaming/moving a session method, settings field,
  or flow handler — or marking a module deprecated — grep ALL `.md` under `docs/` (including
  `FLOW-*` sequence docs) AND `backend/**/README.md` for the old name/classes, not just the feature's
  own README. Distinguish a code symbol (stale → update) from a wire/event constant
  (`action.confirm_ai_end` → unchanged). Do the sweep at deprecation time, not at deletion.
- **Summarizer sweep when a doc gains an authoritative section** (step 7): an always-loaded summary
  outranks the doc it summarizes in agent attention, so the moment a doc gains a new authoritative
  section, every restatement of its *superseded* claim becomes the operative (wrong) rule. Grep the
  summarizers for the doc's superseded claims and sync them in the same change — and grep by the
  **source's own path/name** as well as by topic keywords, because an index line describes a doc
  without using the topic's words (a `.cursor/rules.md` index enumerating a skill's sections omitted
  a newly-added one; the topic grep cleared the file, the name grep caught it). The summarizer class
  is wider than the always-loaded set: `.claude/skills/**` counts too — a skill section enumerating
  a ledger's series is loaded whenever that skill runs, so adding a series leaves it silently
  incomplete for precisely the session that maintains the doc. Treat a spec's "explicitly NOT
  modified" list as a hypothesis to re-verify at implementation time, not an exemption: it was
  written before the doc's new content existed.
- **Published-surface audit on approach change** (steps 1/7): any statement already posted to an
  external surface (PR reply, review comment, task doc, hand-off) is a claim with a timestamp.
  If the approach changed mid-task, grep the published set for the abandoned plan's identifiers —
  the old branch name, "is closed", "still needs" — and post corrections BEFORE reporting
  completion, preferring to edit the superseded text in place (a reader can stop at the first
  reply). A count-based check ("36/36 threads answered") passes while the content is wrong;
  content-matches-final-state is the gate, not count-of-threads-answered.
- **Untracked-dependency check** (step 7): for every file the task created, ask whether a TRACKED
  file now references it — a test asserting its existence, a rule naming its path, a doc linking
  it. If yes, tracking it (or making the reference conditional) is a completion criterion, not a
  staging preference: the pair passes every local gate and breaks on a fresh clone. Cheap check:
  `git status --porcelain` for untracked artifacts, then grep the tracked tree for each one's path.
  Two blind spots in that cheap check, each needing its own command. (1) `git status --porcelain`
  **cannot see ignored paths** — `.ai/tmp/` and `.ai/handoffs/` are gitignored, so a tracked doc
  citing a derived artifact there reads as a normal reference and fails silently and totally; run
  `git check-ignore -q <path>; echo $?` (0 = ignored ⇒ do not cite as durable) and cite the tracked
  module or the re-derivation contract instead of the scratch script that produced the number.
  (2) "not ignored" is **not** "tracked" — `.specs/` and `tasks/` are trackable but routinely left
  untracked, so `git check-ignore` reports a new file there durable while `git ls-files
  --error-unmatch` reports it untracked. The two commands answer different questions and only the
  second is the durability test. Run `git ls-files --error-unmatch` on every referenced path before
  reporting completion; a green audit over a dirty tree is scope-limited and the report must say
  so. The real question is not "is the new file present?" but "would this reference resolve in a
  clone of HEAD?"
- **Doc-retirement gate** (step 7): before deleting any doc, enumerate its EXECUTABLE artifacts
  separately from its knowledge — grep it for fenced code blocks and "Reproduce" / "How to find" /
  query sections, and relocate each VERBATIM next to the step that needs it, not into a summary.
  A relocation pass naturally captures claims and obligations and systematically misses
  queries/repro steps; "the checklist survived" and "the means of executing it survived" are two
  separate gates. Pair with the AGENTS.md deletion-sweep rule (partition targets by `git ls-files`
  first — the untracked half is unrecoverable).

See [references/review-checklist.md](references/review-checklist.md) for a quick-reference checklist.

## State Contract

- **State location:** Inline output (no persistent files created by default)
- **Side effects:** May update `.ai/learnings.md`, documentation files, project rule files
- **Idempotency:** Safe to re-run; appends to learnings, updates docs to current state
