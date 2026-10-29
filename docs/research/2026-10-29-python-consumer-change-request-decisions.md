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
| A24 | DEFER | the premise "the test starts green" is false: section 6 item 9 | `_FORBIDDEN` holds no assignment rule; a scan of 146 files finds 21 fenced and 4 inline candidates in 15 files | trigger: K58 landed and an attribution count of denials to kit text | n/a | n/a |
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
| 1 | KIT-1 | A1 pins, A11a, A14, A17 code half | `tests/test_gate_learnings_drain.py`; `validate_register.py` and a new test; branch-switch SKILL.md, a new script, a new test; `probe_checker.py` and a new test; ledgers; sync-record notes for the three upstream-origin skills | 0 to -5 | 0 (no description changes) |
| 2 | KIT-2 | A11b to A11e, A12a and b, A13, A15 | flow-mapping, agent-delegate, stacked-pr-planner, plan-critic references; one pointer line each | at most 3 | 0 |
| 3 | KIT-2, after K-3 and K-4 | A4(h), A21, A27 | references only | 0 | 0 |
| 4 | KIT-3, after K-4 | A18 scripted core | a new script, a test, one pointer | at most 3 | 0 |

Second round, after K-5 and the push: A7 to A10, the A18 light mode, A24, A22, A23, and A19 and A20 if a standard is decided.

## 10. Counts check

ALREADY-DONE 1 (A1); APPLY 3 (A2, A3, A13); APPLY-MODIFIED 11 (A4, A5, A6, A11, A12, A14, A15, A17, A18, A21, A27); DEFER 11 (A7, A8, A9, A10, A16, A19, A20, A22, A23, A24, A28); REJECT 1 (A26); NEEDS-OPERATOR 1 (A25). 1 + 3 + 11 + 11 + 1 + 1 = 28.

## 11. Pass 1 as applied, and what changed at the new tip

- **Plan change.** Pass 1 applied A17 (code half) and A11a. The A1 pin rows and A14 moved to the next session's pass 2: the session crossed its 550,000-token context line while pass 1 was under way (571,497 at call 125), and A14 is the only SKILL.md edit, which the skill-authoring workflow requires.
- **The other lane landed first.** Its first two K-2 packages are on the branch (`78fa5ab`, `c02f235`, 12 files, none of this pass's paths), the order recommended in section 6. Baseline at `c02f235`: ruff, format, types, audit exit 0; pytest 663 passed, 6 skipped. `publish-check` read BLOCKED, and only because this lane's two untracked session files were in the tree (the working-tree probe; the untracked-in-payload and gitignored-in-payload probes were ok).
- **Re-derived at `c02f235`.** A5's lint file argument is now ALREADY-DONE (K61: the CLI's hand-off lint lines went from 3 to 16); the contract sections are unchanged (5 hits). A4(d): 7 assignment-led lines remain, all in K58's unfinished package (the consolidator family is done). A24's scan: 18 fenced and 3 inline candidates in 13 files. A19: 11 hits in 5 files. A22's census half exists (K45). The zero-file `lint` finding of section 7 was NOT re-measured at the new tip: UNKNOWN there.
- **Evidence for the two applied items.** A17: 8 new process-level tests, 6 red on the unmodified script (a lone "0" read as over-matching; `--script` unknown; no shell note), 2 green pins (the names other repositories load the file by, and exactly one shell call). A11a: 3 tests, 1 red (`assert False is True` from a scratch export inside a repository), 2 green controls (a project root below the repository top; a path tracked nowhere). My first A11a red run was invalid, all three failing in my own loader (a dataclass needs its module registered); it was fixed and re-run before the change. All 11 plus the content-safety shell pin pass after (21).
- **Carry.** Both edited skills are upstream-origin: local overrides for the next sync. No SKILL.md text changed.
