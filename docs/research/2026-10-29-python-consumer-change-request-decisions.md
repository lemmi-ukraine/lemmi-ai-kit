# Change requests A1 to A28 from a Python consumer project's consolidation: a verdict for each, argued from the kit at a9d059a

**Dated:** 2026-10-29. **Scope:** 28 candidate kit changes (A1 to A10 filed earlier, A11 to A28 added) reviewed against branch `consolidation/2026-10-27-kit-change-requests` at `a9d059a`, working tree clean at the start. Catalogue: 308 lines, 52,777 bytes, sha256 prefix `468160bda087a5cd`. One kit session (a3f38ff8), no sub-agents. Nothing in the kit changed except this record.

**Status:** DECISION RECORD. The operator replied "so proceed", read as yes with permission to commit each pass after its gates pass. Pass 1 is applied in the commit that adds this file, with a changed scope: section 11 supersedes the pass column for A1 and A14. It cites the other consumer's request ids (K27 to K66) and recorded decisions (DEC-...) as labels only; their sources are private and are not reproduced here.

## 1. Where this record's verification stops

- Every "decided by" cell was re-derived at `a9d059a` by a command: greps over 134 skill and reference markdown files and 12 asset text files (each pattern was first fired at a planted positive; every probe printed CAN-SEE), file reads, the real learnings guard run the way the harness runs it, the CLI, and the suite.
- NOT re-measured: the catalogue's transcript counts (denials, sessions, tokens). Grades A and B are taken as stated, as floors from one repository. NOT verified from documentation: that a hook exit code 2 blocks the tool call (quoted from the catalogue; the exit code itself was measured), and that the skill-listing budget is 1% of the window (quoted from the audit's own message).
- NOT applied: the other lane's unlanded patches. Their file lists were read; they were not run.
- Buffer entries behind A4(h), A11a, A12a, A14, A15 and A17 were found under the headings the catalogue names; only A11a, A14 and A17 were read in full.
- `post-task-review` was not run: no code or skill changed in this phase.

## 2. Baseline, before any change (tip `a9d059a`, tree clean before and after)

| Gate | Exact command | Result |
|---|---|---|
| sync | `uv sync --dev` | exit 0, "Checked 10 packages" |
| lint | `uv run ruff check .` | exit 0, "All checks passed!" |
| format | `uv run ruff format --check .` | exit 0, "116 files already formatted" |
| types | `uv run basedpyright` | exit 0, "0 errors, 0 warnings, 0 notes" |
| tests, form 1 | `uv run pytest -q --basetemp <scratchpad path, 157 characters>` | exit 1, **9 failed, 576 passed, 6 skipped, 8 errors**: every trace ends in a file-not-found on a long path; an artifact of the deep basetemp (the other lane recorded the same trap), not a kit finding |
| tests, form 2 | the AGENTS.md form: `T=$(mktemp -d); uv run pytest -q --basetemp "$T"` (path length 19) | exit 0, **593 passed, 6 skipped** in 482.58 s |
| audit | `uv run python -B -m lemmi_ai_kit audit-skills --fail-on major` | exit 0, "0 finding(s)" |
| publish | `uv run python -B -m lemmi_ai_kit publish-check` | exit 0, "PUBLISH CHECK PASSED (the payload is exactly the git tree)" |
| drift report (non-blocking in CI) | `uv run python tests/upstream_sync.py` | exit 0, output not read |

Every command ran with `PYTHONDONTWRITEBYTECODE=1`. `git status --porcelain` was empty before the first gate and after the last. The baseline is green; form 1's red is recorded so nobody reads it as a kit defect.

## 3. Verdicts

28 ids. At the id level: **ALREADY-DONE 1, APPLY 3, APPLY-MODIFIED 11, DEFER 11, REJECT 1, NEEDS-OPERATOR 1.** Parts of six ids carry their own verdicts (section 4).

Reading guide: "carried by Kn" means the other lane already owns the same change in its pass; this lane builds nothing for it. "Pass" for this lane is 1 to 4; K-2 to K-5 are the other lane's. A pass is built only after the operator's reply.

| id | verdict | reason | decided by (at a9d059a) | pass | named test | size line |
|---|---|---|---|---|---|---|
| A1 | ALREADY-DONE | the fix landed as K32 (`06e38fb`); only two regression rows are missing | `grep '_BASH_MUTATES = '` on the hook: 0 hits. The real guard on 8 shapes (4 controls): 0 differ at the tip, 3 differ on its parent `0919d58` (read-only awk, awk with `=>` in its output, grep for `=>` are denied there) | 1 (pin rows) | 2 ALLOW rows and 1 DENY control in `tests/test_gate_learnings_drain.py`, red on `0919d58`'s guard, green at the tip | 0 skill lines |
| A2 | APPLY (carried by K28) | orchestrate still gates; the seam is the operator's own ruling (DEC-D09/C1: default kept, project switch added) | orchestrate SKILL.md has "Preflight the usage window" and "warn threshold" once each; "not a gate" as a seam: 0 hits in 146 files | K-3 | K28's seam test | orchestrate: 43 lines of headroom; initiative-planner: at the cap (499 by `wc -l`) |
| A3 | APPLY (carried by K54) | all three gaps are present; accepted as DEC-D09/C8 | "EARLY and INCREMENTALLY": 4 hits in 3 files; a leading `NAME=value` warning: 0 hits in 29 orchestration files; brief template (58 lines): no budget line | K-3 | K54's wording test | with K54 |
| A4 | APPLY-MODIFIED | five of eight parts are already landed; (d) is K58; (f) stays deferred; (h) is new | section 4a | 3 for (h) | a wording test for (h) | (h): one reference paragraph; retrospective SKILL.md has 7 lines of headroom, so none goes there |
| A5 | APPLY-MODIFIED | split three ways exactly as the other lane split it: lint file argument = K61 (ready), trigger wording = K27, contract sections = held (DEC-D09/C12) | `cli.py` lint takes a target name only; `## Continue` and `Orchestrator summary`: 0 hits in 154 files | K-2, K-3; contract: DEFER | K61's tests | none here |
| A6 | APPLY-MODIFIED (carried by K62) | the other lane already decided the switch: off by default, carrying the project's allowed forms (DEC-D09/C3, DEC-D05). New: the kit's own registration has no fail-open tail | hooks folder holds 2 files; registration: 0 hits for a fail-open tail; its command with a missing script exits **2** | K-5 | K62's table plus a registration test: run the registered command with a missing root, expect exit 0 | a new hook and its test; `hooks.json` +1 tail |
| A7 | DEFER | DEC-D12: A7 to A10 wait for a second kit round. Also evidence D | `grep -w lane`: 48 hits in 12 skill files (the catalogue's 12 reproduced); "execution lane": 0 | second round | n/a | initiative-planner at the cap |
| A8 | DEFER | DEC-D12. Conditional, so a reference only | the eight style words over test-planner, plan-critic and the 5 seeded templates: 1 unrelated hit | second round | n/a | n/a |
| A9 | DEFER | DEC-D12; depends on A18's scripted core; K38 edits the same file | census, removed assertion, weaken: 1 hit (a byte census in fixture-design) | second round | n/a | post-task-review: 17 lines of headroom |
| A10 | DEFER | DEC-D12; K48 and K50 rewrite the same shared-index reference first | `git archive`, "one session owns": 0 hits in parallel-session-safety | second round, after K-4 | n/a | parallel-session-safety: 17 lines |
| A11 | APPLY-MODIFIED | 11a is a bug, reproduced by reading; 11b is a blind check; 11c to 11e are single incidents | section 4b | 1 (11a), 2 (11b to 11e) | section 4b | `validate_register.py` only in pass 1; no SKILL.md growth |
| A12 | APPLY-MODIFIED | 12a and 12b as a reference; 12c and 12d are single incidents | section 4c | 2 | wording test | one new reference (about 20 lines) and one pointer line in a 112-line SKILL.md |
| A13 | APPLY | measured in a throwaway repository (evidence A); no text says it | five phrasings of "a journal branch removes files on switch" in stacked-pr-planner: 0 hits (the same file has 12 hits for neighbouring terms) | 2 | `tests/test_stacked_pr_planner_journal_wording.py` | +8 lines in a 420-line file; K52 adds about 10 |
| A14 | APPLY-MODIFIED | all four defects are real. The Change line's location is forbidden by the hygiene test, so the backup moves under the git directory and ships as a Python script | block line 46 is `D=".ai/pre-switch-backups/$(date +%Y-%m-%d)-<target-branch>"`; that folder name appears nowhere else in 163 files; the hygiene test rejects the `.ai/` plus `backups/` form | 1 | `tests/test_branch_switch_backup.py`: second run in the same second refuses to overwrite; the printed block has no leading assignment; the script names what it does not save | SKILL.md 230 lines, net 0 to -5; one new script |
| A15 | APPLY-MODIFIED | evidence A; limited to quantified per-caller and per-record claims, as the catalogue's own Case against asks | plan-critic: 4 hits for call sites, enumerat, executed; all are the source-enumeration check, none is about executed counts | 2 | `tests/test_plan_critic_executed_claims.py` | a review dimension in `references/review-dimensions.md` (+14) and one pointer line; SKILL.md has 250 lines |
| A16 | DEFER | three single incidents (grade C); the catalogue itself says the entry was identified by inference; consumers carry such rules in their own host rules | plain-word, term of art, define each term: 0 hits in orchestrate (4 files) | trigger: a second incident | n/a | n/a |
| A17 | APPLY-MODIFIED | merged with K40 (same defect). Code half here: bare-integer auto-detect, `--script`, the error names the shell. Not the catalogue's "split to an argument list" | docstring says "counted by lines unless --count-mode"; `shell=True` at the call; "Command as run:" already prints; no `tests/test_probe_checker.py` | 1 | `tests/test_probe_checker.py`: a bare-integer checker reads CAN-SEE without `--count-mode`; a `--script` checker whose pattern holds a quote, a pipe, a caret and a parenthesis reads CAN-SEE; a missing script exits 2 | `probe_checker.py` 270 lines, about +45; no SKILL.md change in this pass |
| A18 | APPLY-MODIFIED | scripted core only; the light mode waits for a measurement | SKILL.md 483 lines; no "light" or "scripted core" text | 4 (after K-4) | `tests/test_review_core.py` | a pointer of at most 3 lines; the script carries the weight |
| A19 | DEFER | held by DEC-D09/C12: one hand-off standard, decided by the other lane's research session | section names: 10 hits in 5 files; **no seeded hand-off template exists**; orchestrate carries no copy | trigger: that decision | n/a | n/a |
| A20 | DEFER | DEC-D09/C5: no Stop hook in the kit this round; the other consumer's own re-evaluation is 2026-11-20 | `hooks.json` registers no Stop event | trigger: that date, and A19 | n/a | n/a |
| A21 | APPLY-MODIFIED | sections in the existing `references/brief-template.md`, no new template file; rules 1, 2, 3, 4 and 6 only | orchestrate folder: SKILL.md and 3 references; the 5 seeded templates include no dispatch brief | 3 (after K-3 lands its brief edits) | `tests/test_brief_template_rules.py` | brief-template 58 to about 80 lines |
| A22 | DEFER | the census half is K45's `--list-commands` (ready, unlanded); the runner has no tested kit-side source | orchestrate has no scripts folder | trigger: K45 landed and the standard decided | n/a | n/a |
| A23 | DEFER | the context trigger is owned by the quota-guard plugin (DEC-D09/C6 and C7); a kit script would be a third implementation | `context_tokens`, `cache_read_input_tokens`: 0 hits in 27 Python files | trigger: the guard deployed and a consumer without it asks | n/a | n/a |
| A24 | DEFER | the premise "the test starts green" is false: section 7, catalogue correction 8 | `_FORBIDDEN` holds no assignment rule; a scan of 146 files finds 21 fenced and 4 inline candidates in 15 files | trigger: K58 landed and an attribution count of denials to kit text | n/a | n/a |
| A25 | NEEDS-OPERATOR | may skill ids move or merge? Recommendation: no. Parts in section 4d | `audit-skills`: 20, 5, 3, 10, 2 skills = 40; 9,997 + 2,153 + 1,888 + 7,466 + 690 = 22,194 characters (reproduced) | none | none | none |
| A26 | REJECT | failed the bootstrap check: a prompt that cannot name the cache folder cannot run the command that prints it | `list` prints name, pack, invocation and summary for 40 skills; no folder, no version | none | n/a | n/a |
| A27 | APPLY-MODIFIED | a, b, c, e, f, h (two of four sentences) and j as reference paragraphs; g goes through K-4; d, i, k, l, m deferred | section 4e | 3 (after K-2 and K-4) | wording test per file | about 40 lines across references; 0 SKILL.md lines |
| A28 | DEFER | already decided: the guard stays owned by the consumer's plugin (DEC-D09/C7); the sync record already says "DEFERRED, not rejected" | the quota-guard row in `docs/upstream-sync.toml` | trigger: the live-delivery check passes and a cross-platform task exists | n/a | n/a |

## 4. Parts of the composite ids

### 4a. A4 (the extractor)

| part | verdict | decided by |
|---|---|---|
| (a) skip prefixes | ALREADY-DONE `081f733` (K55) | `SKIP_PREFIX` and `HARNESS_USER_PREFIXES` hold the four notices |
| (b) rejection classes | ALREADY-DONE `081f733` (K30) | the same commit |
| (c) replayed events once | ALREADY-DONE `cb65265` (K56) | `test_a_replayed_span_counts_each_tool_call_once` exists in the extractor's tests; those tests passed in the baseline (form 2) |
| (d) printed lint command with a leading assignment | APPLY, carried by K58 (K-2, its third work package was lost and is to be rebuilt) | 11 such lines in 6 skills plus 1 report template, which is K58's own count |
| (e) operator turns, complete-transcript counts | ALREADY-DONE `fbbe97e` (K31) | `TRANSCRIPT_BYTE_CAP` is unchanged at 120 KiB; `test_an_operator_turn_after_the_byte_cap_is_in_the_session_digest` exists and passed in the baseline (form 2) |
| (f) mechanical-fix rule, per-parent cap | DEFER (K59: five gaps, none closed by the catalogue) | "per parent": 0 hits; trigger: a request text that closes the five gaps |
| (g) journal files counted as helpers | ALREADY-DONE `cb65265` (K57) | `SUBAGENT_GLOB = "agent-*.jsonl"`; `test_only_agent_transcripts_are_sub_agents` exists and passed in the baseline (form 2); the catalogue's UNVERIFIED is closed |
| (h) "proceed" method note | APPLY-MODIFIED, a reference paragraph, pass 3 | the only "proceed" hits are the harness refusal sentence and an unrelated stop; evidence B |

### 4b. A11 (flow-mapping)

- **11a, APPLY, pass 1.** `validate_register.py` calls `git ls-tree -r --name-only HEAD -- <path>` with `cwd=REPO_ROOT` and no `--full-tree`. A scratch export inside another repository therefore resolves every path relative to itself. Fix: accept a citation as tracked if git finds it relative to the project root OR, failing that, with `--full-tree`. The catalogue's single `--full-tree` would break a project root that is a subdirectory of a larger repository, so the test has three cases. Named test: `tests/test_validate_register_tracking.py` (new file, so it cannot collide with the other lane's edits to `tests/test_flow_mapping.py`): a scratch export inside a repository with tracked paths reports nothing; a subdirectory project root still reports a path that is untracked under it; a genuinely untracked path is reported. Carry cost: flow-mapping is upstream-origin with a per-skill base override; the edit is one function.
- **11b, APPLY-MODIFIED, pass 2, first step a red fixture.** `--certify` compares declared rows only (the code says the Symbol index rows are authored), so it cannot see a missing row. The fix is a printed "NOT CHECKED: <columns>" line, so that cannot-measure is not read as a pass. Verified by reading, not yet reproduced: if no fixture goes red, the item is dropped.
- **11c to 11e, APPLY-MODIFIED, pass 2.** Single incidents (grade C): one new reference with three short paragraphs and a one-line pointer, not SKILL.md text.

### 4c. A12 (agent-delegate)

12a (save every hand-back report verbatim at once; extract from the parent transcript when the per-agent file is empty) and 12b (write "done" or "re-stamped" only after the action; take the clock reading last) go into one new reference with a pointer line. The command that compares stamps does not exist and is not built (scope). 12c (HTTP 403 as a platform stop) and 12d (state commands before the host-rules step) are single incidents whose entries were not read: DEFER.

### 4d. A25 (listing budget)

(1) a usage census: REJECT as kit code, because the extractor already records `skillsUsed` per session, so the census is a tally the operator can run on a corpus; (2) a description-length target: DEFER, and only as audit input, never a gate (the average today is 555 characters per skill); (3) move `vertical-slice` to the Python pack: REJECT now, a move changes its id and consumers' prompts name it; (4) merge the ledger skills: DEFER until the census exists.

### 4e. A27 (thirteen additions)

APPLY-MODIFIED, pass 3, references only: a, b (post-task-review claim boundaries), c (mutants), e (metric-validity-check), f (analyze-logs), h (the completion notice carries the last command's exit code; a plain affirmative needs an instruction), j (kit wording: the kit's own lint prints `--- handoffs: N finding(s), M file(s) ---`; see section 7 for the zero-file result). g goes to K-4's shared-index visit (two sub-points K48 to K50 do not cover: session ids are not stable names; never print a peer's first message). DEFER: d, i, k, l, m, each a single incident specific to one tool or one project's register. All 13 are absent at the tip (11 probes returned 0, one returned an unrelated hit, one returned an anecdote).

## 5. Overlap map (one verdict, recorded under both ids)

| A | K | the other lane's pass and state (its board of 2026-10-29 18:58) |
|---|---|---|
| A1 | K32 | K-1 landed (`06e38fb`) |
| A2 | K28 | K-3 open |
| A3 | K54 | K-3 open |
| A4 a, b, c, e, g | K55, K30, K56, K31, K57 | K-1 landed (`081f733`, `cb65265`, `fbbe97e`) |
| A4 d | K58 (+K10, K25) | K-2; its third package was built and lost with a deleted temp folder; to be rebuilt |
| A4 f | K59 | K-2 deferred, five gaps |
| A5 | K61, K27, K60 | K61 ready in an unlanded patch; K27 in K-3; K60 held (DEC-D09/C12) |
| A6 | K62 | K-5 open, default off |
| A7, A8, A9, A10 | K63 to K66 | reserved, not merged (DEC-D12) |
| A17 | K40 | K-4; its code half moves to this lane's pass 1 |
| A15, A13 | K42, K52 | K-3, same skills; this lane's additions are separate hunks |
| A19 | K45, K47, K60 | K45 ready; K47 in K-3; K60 held |
| A22 | K45 | the census half is `--list-commands` |
| A10, A27 g | K48, K50 | K-4 |

The other lane's unlanded patches touch `consolidation-critic`, `hypothesis-validator`, `learning-consolidator` (and its reference and `drain_audit.py`), `checks.py`, `cli.py`, `parallel-session-safety` and four tests. Pass 1 touches none of them.

## 6. Questions for the operator (recommendation first)

1. **Sequencing with the other lane.** Recommend: the other lane lands its two ready patches first; then this lane's pass 1 (disjoint files); this lane's passes 2 and 3 follow the other lane's K-3 and K-4; the second round (A7 to A10 and the rest of the DEFER list) follows K-5 and the push. If pass 1 goes first instead, the other lane's whole-tree equality check must compare per-package diffs. The ledger files (`.ai/ai-changelog.md`, `.ai/improvement-hypotheses.md`, the buffer) are append points for both lanes: land one ledger commit before the other is cut.
2. **The hand-off contract (A5 contract part, A19, A20).** Recommend: give the Python consumer's contract (marker line, one status word, a continue section, a short orchestrator summary, a one-file lint) to the other lane's hand-off research as input, and build nothing until it ends in one standard.
3. **Skill ids (A25).** Recommend: no moves or merges now; ids appear in consumers' prompts, no new skills this round (DEC-D14), and the other lane is editing these skills.

Companion lines for the other lane's briefs (generic wording, nothing project-specific): K28, a reading older than a few minutes is stale during a fan-out, and the same change in the planner's two templates; K54, the three A3 items; K58, 11 lines at the tip; K61, an explicit missing or unreadable file must not pass; K62, the five skeleton lessons (absolute path variable, fail-open tail, decide by a JSON reply, UTF-8 stdin, a denial message that names working remedies) and the fail-open tail on the kit's own registration; K40, take the text half only.

## 7. New findings, and what the catalogue got wrong

New, measured at `a9d059a`:

- The kit's own registered hook command exits **2** when its script is missing; the harness treats exit 2 as a block, per the catalogue. With the matcher covering Edit, Write, Bash and PowerShell, a moved plugin folder would block every such call. Belongs in K62's visit.
- `lint handoffs` prints `LINT PASSED (0 finding(s))`, exit 0, over an empty folder and over a project with no `.ai/` at all; only the `0 file(s)` in its summary line tells. A directory run may legitimately be empty; an explicit file argument (K61) must not behave this way.
- This record and the return note are untracked files that the publication-hygiene scan reads (it lists untracked, unignored files). Both were written to pass it.

Catalogue claims corrected:

1. A1 to A6 are not unowned: all six were merged into K27 to K62 before the catalogue was written (see section 5). The catalogue's "overlap: K19" for A2 and "K18, K45 to K47" for A5 name the wrong or partial ids.
2. A4(g) is "UNVERIFIED" in the catalogue; it is ALREADY-DONE (`cb65265`).
3. A4(d): the catalogue places `PYTHONPATH=` in the consolidator skill; at the tip it is in session-retrospective (3 lines in SKILL.md, 1 in the report template) and 6 other lines in 5 other skills. The consolidator has none until the other lane's unlanded patch.
4. A5 and A27(j) assume a marker line and a `[N/N file(s) under contract]` summary. The kit's lint has neither: it prints `--- handoffs: N finding(s), M file(s) ---` and `LINT PASSED` or `LINT FAILED (N finding(s))`. Transplanting the Python consumer's marker contract would be a second standard.
5. A19: no seeded hand-off template exists in the kit (the five seeded templates are design, requirements, tasks, test-cases, test-plan), and orchestrate does not carry the section names; they live in agent-delegate (1), parallel-session-safety (2), `checks.py` (5), `cli.py` (1) and `tests/test_checks.py` (1).
6. A14: the Change line names the `.ai/` plus `backups/` folder, which `tests/test_assets.py` rejects.
7. A17: "print the exact invocation" already exists (`Command as run:` in the invocation error). Dropping `shell=True` would break the flow-mapping validators' `--cmd` strings and the `_SHELL_TRUE_ALLOWED` pin (the other lane's K40 note says the same).
8. A24: the test would not start green. After K58 and A14, 11 fenced assignment-led lines remain in 6 skills and 1 workflow note (stacked-pr-planner 5, initiative-cleanup 2, vertical-slice 1, pr-comment-resolver 1 inline, the stacked-PR workflow note 1, branch-switch 1 before A14); the heuristic also produced 2 false positives (`confidence=PLAUSIBLE.`, `logger=logger, ...`). The catalogue's evidence (denials) traces to project text, not to these lines.
9. A26: `list` prints no folder and no version, and the CLI lives in one pack's cache, so it cannot locate another pack's skills. The harness already announces a skill's base directory on invocation (the extractor's skip list carries that notice).
10. A28: the sync record already holds the answer ("DEFERRED, not rejected").
11. Reproduced exactly: A25's 40 skills and 22,194 characters; A7's 12 files; A9's single census hit; A1's 1,384 test lines.

## 8. The six arguments the brief asked for

- **A5's 38 of 58.** An association between a close block in the brief and an unprompted review. Delegated sessions that carry a close block also carry other orchestrator habits; there is no control. It supports putting a close block in a brief, not two new contract sections. The lint part (grade A, a five-minute directory run) is sound and is K61. Evidence that would change the verdict: the next 30 delegated sessions split by whether the section exists, or the hand-off research finding that delegated sessions lack a continue section.
- **A6's maintenance against a small core.** The lexer for two shells is a standing cost; three rounds still found shapes by guessing. Three rules (leading assignment, absolute or home-anchored `cd`, shadowing `cd`) behind a switch that is off by default is bounded, and the full lexer stays with the consumer. Would change the verdict: the differential test against the shell's own parser proving the small core complete, or a second consumer's switch settings contradicting the first's.
- **A7's untested mechanics.** Grade D: no run of a development lane and a test lane with the red-then-green join gate exists, and the proposal says it does not replace an independent mutation pass. Would change it: one orchestrated feature with the join executed on an exported pre-feature tree and a count of defects the test lane caught that same-agent tests missed.
- **A18's escape hatch.** A light mode that the session chooses for itself becomes the default. K27 (review at every completion event) makes the weight problem sharper, so the scripted core goes first. Any light mode must be defined by a mechanical predicate over the diff (documentation-only paths), computed by the script. Would change it: before and after counts of full reviews.
- **A25's moves and merges.** A skill id is part of consumers' prompts; a move breaks them silently, and no new skills are allowed this round. The measurement to run first already exists in the extractor (`skillsUsed`).
- **A27's text growth.** About 40 lines across references and none in any SKILL.md; five of thirteen are deferred as single-incident or tool-specific. Would change it: a reviewer judging any of the eight as project-specific.

## 9. Passes and size lines

| pass | session | items | files | SKILL.md lines added | listing-budget impact |
|---|---|---|---|---|---|
| 1 (A17 and A11a only: section 11) | KIT-1 | A1 pins, A11a, A14, A17 code half | `tests/test_gate_learnings_drain.py`; `validate_register.py` and a new test; branch-switch SKILL.md, a new script, a new test; `probe_checker.py` and a new test; ledgers; sync-record notes for the three upstream-origin skills | 0 to -5 | 0 (no description changes) |
| 2 (`cefdb41` and its review corrections `299b284`, section 12) | KIT-2 | A11b to A11e, A12a and b, A13, A15, plus the A1 pins and A14 moved from pass 1 | flow-mapping, agent-delegate, stacked-pr-planner, plan-critic references; one pointer line each | at most 3 | 0 |
| 3a (`3bc856e`, section 13) | KIT-3 | A4(h), A27 a, b, c, e, f, j | references only (session-retrospective, post-task-review, metric-validity-check, analyze-logs), one new test file and one extended | 0 | 0 |
| 3b (`7de80be`, section 14) | KIT-2 of 2026-11-02, the sixth KIT session | A21, A27 g and h | `brief-template.md`, `external-agents.md`, `shared-index-protocol.md` (one pointer line extended in the safety SKILL.md); two new test files; a sync note | 0 | 0 |
| 4 | a later session, after K-4 | A18 scripted core | a new script, a test, one pointer | at most 3 | 0 |

Second round, after K-5 and the push: A7 to A10, the A18 light mode, A24, A22, A23, and A19 and A20 if a standard is decided.

## 10. Counts check

ALREADY-DONE 1 (A1); APPLY 3 (A2, A3, A13); APPLY-MODIFIED 11 (A4, A5, A6, A11, A12, A14, A15, A17, A18, A21, A27); DEFER 11 (A7, A8, A9, A10, A16, A19, A20, A22, A23, A24, A28); REJECT 1 (A26); NEEDS-OPERATOR 1 (A25). 1 + 3 + 11 + 11 + 1 + 1 = 28.

## 11. Pass 1 as applied, and what changed at the new tip

- **Plan change.** Pass 1 applied A17 (code half) and A11a. The A1 pin rows and A14 moved to the next session's pass 2: the session crossed its 550,000-token context line while pass 1 was under way (571,497 at call 125), and A14 is the only SKILL.md edit, which the skill-authoring workflow requires.
- **The other lane landed first.** Its first two K-2 packages are on the branch (`78fa5ab`, `c02f235`, 12 files, none of this pass's paths), the order recommended in section 6. Baseline at `c02f235`: ruff, format, types, audit exit 0; pytest 663 passed, 6 skipped. `publish-check` read BLOCKED, and only because this lane's two untracked session files were in the tree (the working-tree probe; the untracked-in-payload and gitignored-in-payload probes were ok).
- **Re-derived at `c02f235`.** A5's lint file argument is now ALREADY-DONE (K61: the CLI's hand-off lint lines went from 3 to 16); the contract sections are unchanged (5 hits). A4(d): 7 assignment-led lines remain, all in K58's unfinished package (the consolidator family is done). A24's scan: 18 fenced and 3 inline candidates in 13 files. A19: 11 hits in 5 files. A22's census half exists (K45). The zero-file `lint` finding of section 7 was NOT re-measured at the new tip: UNKNOWN there.
- **Evidence for the two applied items.** A17: 8 new process-level tests, 6 red on the unmodified script (a lone "0" read as over-matching; `--script` unknown; no shell note), 2 green pins (the names other repositories load the file by, and exactly one shell call). A11a: 3 tests, 1 red (`assert False is True` from a scratch export inside a repository), 2 green controls (a project root below the repository top; a path tracked nowhere). My first A11a red run was invalid, all three failing in my own loader (a dataclass needs its module registered); it was fixed and re-run before the change. All 11 plus the content-safety shell pin pass after (21).
- **Carry.** Both edited skills are upstream-origin: local overrides for the next sync. No SKILL.md text changed.

## 12. Pass 2 as applied (KIT-2, 2026-10-30, started at `cf22252`)

- **Baseline at `cf22252`** (the kickoff's gate script): ruff, format (124 files), types and audit (0 findings) exit 0; pytest 718 passed, 6 skipped; `publish-check` BLOCKED on 1 of 3 probes, the working tree, only because the session notes in `.ai/handoffs/` were untracked. The other lane's board read K-3 in flight in scratch clones, so passes 3b and 4 stay blocked.
- **Every new check was seen red against the previous code for its stated reason, then green; the control cases (the DENY row, the detector on the old block shape, the wrong-derived-cell run) gave their expected result on the previous code too.** Mutation checks (each needle matched exactly once, an unmutated control in the same pass): 4 mutants of the backup script and 4 of the certifier each turned the intended tests red.

| item | result | named test | measured |
|---|---|---|---|
| 2.1 A1 pins | three rows (two read-only commands holding `=>` allowed, a redirect after `=>` in a string denied) at the END of `_PARSER_SHAPES`, not after `remove: rm file`: `test_the_table_holds_the_27_probe_shapes_and_both_controls` pins `_PROBE_SHAPES` at 27 rows | `tests/test_gate_learnings_drain.py` (CRLF kept: 1,384 to 1,402 lines, CR count equal) | on the pre-fix guard `0919d58` the two ALLOW rows fail ("required ALLOW, got DENY") and the DENY control passes; at the tip 3 of 3 pass and the whole file passes (200) |
| 2.2 A14 | `scripts/pre_switch_backup.py` plus one printed command; both diffs are taken with `--binary`, because without it a changed binary file is saved as the words "Binary files differ" | `tests/test_branch_switch_backup.py`, 7 tests | red with no script (5) and no printed block (1), the detector control green; 7 green. SKILL.md 230 to 227 |
| 2.3 A11b | REPRODUCED, well inside the allowance of about 20 calls: a Symbol index row deleted, or an authored `invariants` cell blanked, reads exit 0 and total 0 (control: a wrong derived cell reads exit 1). One `NOT CHECKED` line on every run; exit code and the bare total unchanged | `tests/test_certify_blind_columns.py`, 7 tests (5 at the pass commit, 2 after the completion review) | 5 of 5 red on the previous generator ("0 NOT CHECKED lines"), 5 green; of the 2 added after review, 1 red against the committed wording and 1 control |
| 2.4 A11c to e | `references/register-and-validator-pitfalls.md`, 25 lines, one pointer | `tests/test_flow_mapping_pitfalls_wording.py`, 7 | 7 red, 7 green. SKILL.md 178 to 179 |
| 2.5 A12a, b | `references/hand-back-and-stamps.md`, 16 lines, a new folder; the stamp-comparing command is named and NOT built | `tests/test_agent_delegate_hand_back_wording.py`, 7 | 7 red, 7 green. SKILL.md 117 to 118 |
| 2.6 A13 | one Step 2 paragraph. Experiment, git 2.55.0, once per `core.autocrlf` value: 2 files present before the commit and on the branch, 0 after switching back; `git restore --source` returned different bytes with the setting on, identical bytes off | `tests/test_stacked_pr_planner_journal_wording.py`, 4 | 4 red, 4 green. SKILL.md 420 to 428 |
| 2.7 A15 | Dimension 7 for quantified claims in `references/review-dimensions.md`, 186 to 205 lines (+19, the estimate was +14), one list line | `tests/test_plan_critic_executed_claims.py`, 7 | 7 red, 7 green. SKILL.md 250 to 251 |

- **Deviations and findings.** (a) The A1 rows' place, above. (b) Pass 1 wrote no `docs/upstream-sync.toml` notes for its two upstream-origin edits; this pass writes them with the five for its own, one line per skill row (`agent-delegate` is kit-origin: none). (c) The catalogue's A11b says two new invariants were missing from the Symbol index; what it measured is an authored cell, which `--certify` cannot see. A missing ROW is a second blind spot of the same kind, and both read zero. (d) plan-critic's headings still say "Five Dimensions" while its list now holds seven (6 and 7 are conditional); left alone, because the other lane's K42 edits that skill. (e) The completion review (run once over `931275d` and `cefdb41`) found the `NOT CHECKED` line overclaimed: `--certify` refuses a cited file that has no Coverage row or no note (exit 2), so the unseen case is a file no scenario cites. The line now says so, with two tests (the refusal as a control, and the blind case); the backup script's first docstring line no longer calls an inventory of untracked names a restorable snapshot. (f) The same review found `references/fixture-design.md` section 8 stale after pass 1: it says `grep -c` always probes as 1 and needs a flag, while the default now reads a lone bare integer as the count. K40, in the other lane's K-4, owns that text, so it was not edited here. (g) Pass 1 changed the probe's default counting mode, so an adopter's recorded probe stamps for a lone-integer checker will read differently on the first run after an upgrade; how many exist is UNKNOWN.
- **Commits.** Pass 1 `931275d`; pass 2 `cefdb41`; the review corrections are `299b284`. Pass 3a is not built in this session: context stood at 432,364 tokens at call 157, and 3a plus the mandatory close would not fit under the 550,000 line.

## 13. Pass 3a as applied (KIT-3, 2026-10-30, started at `299b284`)

- **Baseline at `299b284`** (the kickoff's gate script): ruff, format (131 files), types and audit (0 findings) exit 0; pytest 760 passed, 6 skipped; `publish-check` BLOCKED on 1 of 3 probes, the working tree, only because the two session notes in `.ai/handoffs/` were untracked. The other lane's board read K-3 BUILT and VERIFIED, not landed (it lands only on the operator's word), and K-4 and K-5 open, so passes 3b and 4 stay blocked.
- **Every new check was seen red against the previous text for its stated reason, then green.** Of 22 new cases, 15 were red on the previous text because the claim or the paragraph was absent, and 6 were green controls (the three links, the surface numbers, the lint over zero files, the retrospective SKILL.md's link to the schema). A seventh control, which reads the lint's summary line, was red for a wrong reason in my own test: it assumed the summary prints first, and with findings present it prints after them. It was corrected before the texts were written. Every phrase is also fired at a planted removal inside the suite.

| item | result | named test | measured |
|---|---|---|---|
| 3a.1 A4(h) | one paragraph in `references/extractor-output-schema.md`, beside the one on re-asks, inside the digest section that lists the operator's turns | `tests/test_session_retrospective_text.py`, 4 new cases | 3 red (no paragraph, not in the section, the planted check), 1 control green (SKILL.md links the schema); all 4 green after. Schema 341 to 351 lines |
| 3a.2 A27 a, b, c, j | a closing section of four short cases in `references/claim-boundaries.md` | `tests/test_evidence_discipline_wording.py` (new, 18 cases over 11 claims and 25 phrases) | 6 claim cases red, 1 planted-removal case red; green after. 119 to 145 lines. The zero-file pass of j was re-measured at the tip, and a test runs the lint to pin it |
| 3a.3 A27 e, f | a section on counting recorded commands in `references/join-diagnostics.md` (163 to 181), Example 4 in `references/analysis-examples.md` (79 to 93) | the same file | 5 claim cases red, green after |

- **Deviations and findings.** (a) A27 j is written as output lines and prose, not as a printed command: the printed-commands scan parses any span that opens with a subcommand. (b) The zero-file result at the tip: pointed at an empty project folder, and at a folder holding an empty `.ai/handoffs`, the hand-off lint prints `--- handoffs: 0 finding(s), 0 file(s) ---` then `LINT PASSED (0 finding(s))` and exits 0, which closes section 11's UNKNOWN for that line. Only the hand-off lint prints a file count: the three ledger lints take one file, print none and refuse a missing one with an error, so the kickoff's general wording (the kit's lint prints a file count) was narrowed to the hand-off lint in the text. (c) Example 4 uses illustrative figures, as its file's header says every example does; the catalogue's own figures were not carried. (d) Three SKILL.md lines now describe a reference incompletely, and were left alone because the pass is references-only: `analyze-logs` lists three kinds of example and not Example 4, the `post-task-review` pointer describes `claim-boundaries.md` as the completeness check although the file now also holds four shorter cases, and the `metric-validity-check` pointer calls `join-diagnostics.md` linkage detail and the write-up format although it now also counts recorded commands. Each is an in-place wording change, one of them a line longer, and is left to the operator. (e) The about-90% share in the retrospective paragraph is the catalogue's, from one corpus, and was not re-measured (section 1). (f) `claim-boundaries.md` and `analysis-examples.md` are CRLF in the working copy and LF in the blob (`.gitattributes` pins LF); they were edited with a script that kept CRLF and checked that the CR count equals the line count. (g) Four sync-record notes, one per upstream-origin skill, were written in this pass. (h) The completion review, run once and inline over this pass's diff, found four defects of mine in the texts, fixed before the commit: "the other kind" implied that two kinds exhaust the cases although about 8% of such messages were decisions (now "another kind"); "an old-wording control" was bare jargon (now glossed as the text the change replaced, which cost one line); one sentence guessed a mechanism (that the half of a split command that runs can exit 0 on nothing) and now says only that the pipe splits the command; and Example 4's halves contradicted each other (the join matched 0 of 2,000 rows, then 1,874), so the better analysis now says the trace was reduced to the bare id between them. An earlier read of the printed output had caught a fifth: only the hand-off lint prints a file count (see b).
- **Commits.** Pass 3a `3bc856e`. The pass cell in section 9 and this line were completed in the next commit, which carries no other change.

## 14. Pass 3b as applied (KIT-2 of 2026-11-02, the sixth KIT session, started at `84d12c3`)

- **Baseline at `84d12c3`** (the kickoff's gate script, tree `0f7744dd`): ruff, format (164 files), types and audit (0 findings) exit 0; pytest 1343 passed, 6 skipped; `publish-check` BLOCKED on 1 of 3 probes, the working tree, only because six session notes in `.ai/handoffs/` were untracked. The K-3 and K-4 trigger commands read landed (2 of 2 test files tracked; 1 of 1) and the other lane's board reads both LANDED, so passes 3b and 4 were unblocked; K-5's reads 0 commits on `hooks.json` and `pyproject.toml` (control 2), so K-5 is not landed. Passes 2 and 3a had been committed by earlier sessions (sections 12 and 13), so 3b was the first unfinished pass.
- **Every new check was seen red against the previous text for its stated reason, then green.** Of 20 new cases, 15 were red (the section, the subsection, the sentence or the pointer's `12l` was absent: the failure text names the missing phrases) and 5 were green controls (the two surface counts and the three existing SKILL.md links). The pointer helper was shown able to see by the same run: its failure printed the real section 12 pointer. Each phrase is also fired at a planted removal inside the suite.

| item | result | named test | measured |
|---|---|---|---|
| 3b.1 A21 rules 1, 2, 3, 4, 6 | a section `Rules a dispatch brief carries` after the Paste line section, which is not edited: a paste line printed by a command and carrying no substitution; stop on any `<...>` placeholder; the return note is the first write, made so that it fails if it exists (links 12k); a project's standing decision beats a session default; preconditions are commands with expected results (points at section 2b) | `tests/test_brief_template_rules.py`, 11 cases | 9 red, 2 green controls; 11 green after. `brief-template.md` 89 to 117 lines (+28; the estimate was +22 on a base of 58, and the base had grown to 89 under K-3 and K-4) |
| 3b.2 A27 h | the template's section also holds the sentence about a kickoff that says "any other reply is a no" (it must say what a plain affirmative permits); `external-agents.md` holds the completion-notice sentence beside its background-run sentence | `tests/test_brief_template_rules.py` (the kickoff sentence) and `tests/test_orchestration_lessons_wording.py`, 9 cases (the notice sentence) | the notice claim red, then green; measured in this pass: a background chain of seven gates ended in an `echo`, its notice read exit code 0, and one gate's own result file read 1. `external-agents.md` 77 to 80 |
| 3b.3 A27 g | `shared-index-protocol.md` 12l: a session's name belongs to its process and can be reused, so a peer is named by the host's session id copied from a command's output; never print the first message of a peer's transcript; liveness is read from facts about the transcript, which print no text. The section 12 pointer lists `12l` | `tests/test_orchestration_lessons_wording.py` | 3 claim cases and the pointer case red, green after. Reference 228 to 241; the safety SKILL.md 498 to 498 |

- **Deviations and findings.** (a) A27 g sits in the shared-index reference although it is about naming peers, not the index: the safety SKILL.md counts 499 lines against the audit's cap of 500 (one line of headroom) and the skill has no other reference, so a new file would have used that last line for its pointer, while 12l reuses the lettered-subsection pointer that already stands there. (b) The request's rules 5 and 7 stay unbuilt, as sections 3 and 4c rule: 5 belongs to A23 and the guard's owner, 7 to A12d, a single incident. (c) The Paste line section is pinned by `test_peer_brief_first_step.py` and was not edited; the new section does not depend on it, though the board lists "keep or cut" that section as an open question for the operator (cut, and the new section's term "paste line" loses its definition and keeps its meaning). (d) The two one-line defects KIT-5 named are fixed in this commit: `299b284` is named in section 12 and in section 9's pass 2 cell, and the A24 row points at section 7, catalogue correction 8. (e) The kit-origin skill `orchestrate` needs no sync note; the upstream-origin `parallel-session-safety` row gained one sentence. (f) K-3's and K-4's open decisions are not touched here: the hand-off standard (A19, A20, A22), K49 part 2, and the three SKILL.md lines that describe their reference incompletely (section 13 (d)). (g) The completion review (run once, inline, over `7de80be` and `06503e9`) found four defects of mine, corrected in the next commit: the new section's intro said the brief restates every rule that binds the delegate, against the template's own measured advice to point at standing rules, and said the delegate obeys each rule before its first write, which is false for two of them (it now says the rules are for whoever writes the brief); a test docstring and a table cell said a pointer was re-wrapped when one line gained a phrase; this section said both trigger commands read landed while listing three; and (a) said the safety SKILL.md cannot take a pointer line when the audit allows one more.
- **Commits.** Pass 3b `7de80be`. The pass cell in section 9 and this line were completed in `06503e9`, which carries no other change. The review corrections are the one commit whose parent is `06503e9`.
