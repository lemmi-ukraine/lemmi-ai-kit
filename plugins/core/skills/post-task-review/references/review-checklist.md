# Post-Task Review Checklist

Quick-reference checklist for the review process, Step 0 through Step 9. Use this to verify
completeness. **It is the whole pipeline or it is not a review** — this checklist previously
listed only Steps 1–8, so the blast-radius step and the mandatory CLOSE self-challenge were
invisible to anyone working from it.

## Step 0: Dependency & Blast Radius

- [ ] Ran BEFORE steps 1–6 (ideally before the change itself)
- [ ] Produced a LIST of affected callers/callees/tests — not an opinion
- [ ] Every item in that list either reviewed or explicitly excluded with a reason
- [ ] Every sweep for readers of a symbol, a claim or an old name counted untracked files (`git grep -n --untracked`, with `git ls-files --others --exclude-standard` for new files) and says which form ran next to its count

## Steps 1–6: Code Review

### Step 1: High-Level Conceptual Review
- [ ] Solution aligns with original requirements
- [ ] Architecture is appropriate for the problem
- [ ] No obvious design flaws or anti-patterns
- [ ] Integrates well with existing system components
- [ ] No missing pieces that prevent end-to-end functionality
- [ ] The tests that already exist for the touched area and for two neighbouring areas are listed before the change's own tests are judged (the script's test-changes section prints how many test paths changed and how many the repository holds)

### Step 2: Detailed File-by-File Review
- [ ] Every function reviewed for correctness
- [ ] Input validation and error handling verified
- [ ] Return types and edge cases checked
- [ ] No potential null/None reference issues
- [ ] Proper resource cleanup (connections, files, sessions)
- [ ] No potential memory leaks or performance issues
- [ ] Async/await usage correct (no missing awaits)
- [ ] Every removed or changed assertion in an edited test or shared test helper (the script's test-changes section lists them) has what covers it now and a broken version that passes the old test and fails the new one, or the word "none"; a "none" is a finding (see `claim-boundaries.md`, the paragraph on a mutant that survives)
- [ ] The test files that changed match the plan's list of test files that may change: each changed test path the plan does not list, and each listed one left alone, is explained

### Step 3: Convention Compliance
- [ ] Imports: global at top, proper grouping, no unused
- [ ] One class per file with matching snake_case name
- [ ] Feature structure: correct placement in api/, services/, storage/
- [ ] Logging: `setup_logger(__name__)`, proper levels, structured `extra={}`
- [ ] HTTP clients: correct base class, proper error handling
- [ ] Error handling: shared exceptions, not HTTPException for standard errors
- [ ] Feature exceptions converted to shared exceptions in routes
- [ ] Tests fake external dependencies only at sanctioned seams, and wait with bounded polling, not fixed sleeps

### Step 4: Self-Challenge
- [ ] "What could go wrong here?"
- [ ] "What if input is empty/null/malformed?"
- [ ] "Is there a race condition possible?"
- [ ] "What if the external service is unavailable?"
- [ ] "Did I handle all error cases?"
- [ ] "Am I using shared exceptions correctly?"
- [ ] "Is this the simplest solution that works?"

### Step 5: Fixes
- [ ] All identified issues fixed or explicitly justified
- [ ] Each fix has clear reasoning documented

### Step 6: Linting
- [ ] `read_lints` run on ALL modified files
- [ ] The project's lint command (AGENTS.md § Commands) run on all changed files
- [ ] All remaining issues resolved

## Step 7: Documentation Impact

- [ ] All modified files listed
- [ ] Doc impact matrix consulted for each modified path
- [ ] Each potentially affected doc read and evaluated
- [ ] Stale information corrected
- [ ] Missing information added
- [ ] Broken references fixed
- [ ] New feature has README.md if applicable
- [ ] Results reported (updated / no change needed)

### 7c-extra: checks 4 and 5

Checks 4 and 5 of the prompt cross-reference sweep (SKILL.md, step 7c-extra, run when prompt files
were modified). Checks 1 to 3 are in SKILL.md and cover a feature removed or added.

4. When a rule is added or strengthened, re-read its own exceptions and every example that speaks its phrasing: sharpening a rule can turn a tolerated exception into a contradiction, and examples outweigh instructions.
5. A pointer from one prompt part to another must contain the rule it names, not only resolve to a heading.

## Step 8: Learnings Extraction

- [ ] Task reviewed for discoveries and surprises
- [ ] Review findings (steps 1–7) also considered as learnings
- [ ] Findings classified (project-level vs task-specific)
- [ ] Project-level findings appended to `.ai/learnings.md`
- [ ] Rules updated if convention gaps found
- [ ] AI-infrastructure files modified: changelog entry appended to `.ai/ai-changelog.md`
- [ ] Changelog entry written: hypothesis evaluated, and appended to `.ai/improvement-hypotheses.md` if warranted (appends only; a Status or marker edit stays with the validator's run)
- [ ] A drafted changelog line marks each file it names as tracked, untracked or ignored (`git ls-files --error-unmatch <path>` exits 0 only for a tracked file, `git check-ignore -q <path>` exits 0 for an ignored one) and gives the tracked part of each count ("6 files, 4 tracked")
- [ ] Brief names another writer for these entries: the learnings entry, the changelog entry and the hypothesis drafted in the return, that writer named, each listed as not done, none appended
- [ ] Results reported (count + summary)

## Step 9: Close Self-Challenge (MANDATORY — runs LAST)

- [ ] Run AFTER steps 0–8, and NOT instead of step 4's self-challenge — different passes
- [ ] Asked: is it detailed enough? what was missed? what would a reviewer object to?
- [ ] Stated what the challenge CHANGED, including "nothing" — silence is not a result
- [ ] Ran BEFORE the handoff is written, never after
- [ ] Finished artifact read end to end: the document, plan or report as it now stands, after the last edit (not its diff, not a checker's verdict); yes or no, with what was read

## Common Mistakes Caught in Past Reviews

These are recurring issues found during reviews — watch for them:

- Missing `await` on async repository calls (causes silent data loss)
- Using `HTTPException` instead of shared exceptions for 400/401/404
- Multiple classes in a single file (especially DTOs/schemas)
- Inline/local imports inside functions
- Missing error handling for external API calls (e.g., AI provider, cloud storage)
- Tests that patch application code (`unittest.mock.patch`, `monkeypatch.setattr`, `dependency_overrides`) instead of faking at a sanctioned seam
- Feature-specific exceptions not converted to shared exceptions in routes
- Logging without structured `extra={}` context
