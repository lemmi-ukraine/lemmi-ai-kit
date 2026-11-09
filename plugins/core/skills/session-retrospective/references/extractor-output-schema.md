# Extractor Output Schema (`extract_sessions.py`)

This documents what `scripts/extract_sessions.py` emits. The **machine source of truth** is the
`SCHEMA_KEYS` constant inside the extractor; the extractor's `--self-check` and the pytest assert
that the emitted `aggregate.json` matches `SCHEMA_KEYS`. **When you change the extractor's output,
update `SCHEMA_KEYS` AND this doc together** — the content-reviewer cross-checks this doc against the
constant and the SKILL.md.

`schemaVersion`: **5**. v5 renames and removes no key, but it MOVES counts, which is why the
version changed. The `environment` category (see `errorTaxonomy`) takes the results the harness or
a hook refused or stopped out of the behavioural categories (`runtime-exit`, `test-failure`,
`build-compile`, `tool-error`), and it counts the usage-limit stops that no category counted
before. A slash command the harness typed counts under `harness` in `stats.skillInvocationModes`,
no longer under `user`. The keys v5 adds: `errorTaxonomy.environmentShapes`,
`subAgentErrorTaxonomy.environmentShapes`, `sessions[].environmentShapes`,
`sessions[].subAgents.environmentShapes`, `sessions[].slashCommands[].by` and the `harness` mode.
**A report that compares a window with one built by v4 must say so:** the v4 window filed these
results in the behavioural categories, so those read higher there and `environment` reads 0; a
sub-agent whose only error is a usage-limit stop is error-bearing in v5 and was not in v4, which
can change `agentsWithErrors` and which sub-agent digests are emitted and picked; and a command the
harness typed was counted as `user`.

(v4 was ADDITIVE-ONLY: deterministic deep-dive candidate lists, slash-command capture, per-session
models + compaction counts, `errorAgentsNotEmitted`, `skillInvocationModes`, plus non-schema
behaviors — date pre-scan, stale-output clearing, `--check-file`; existing v3 keys/shapes
unchanged, so v3 consumers — the SKILL phases and any downstream analysis skill — keep working.
v3 added the sub-agent error taxonomy + emitted redacted sub-agent transcripts; v2 added
per-session transcripts + sub-agent counts; v1 was the legacy Node.js flat summary.)

## Artifacts

The extractor writes into `<output-dir>` (always repo-relative, e.g. `.ai/tmp/retro/`, gitignored):

| File | Purpose |
|------|---------|
| `aggregate.json` | Cross-session error taxonomy + per-session behavioral metrics + stats |
| `sessions/<id>.md` | Per-session readable transcript, size-capped (120 KB), fully redacted — for deep reading by sub-agents. The operator turns the cap cut off follow the capped transcript in a section of their own (see below) |
| `sessions/sub/<id>/<agent>.md` | Redacted, size-capped transcript of a HIGH-SIGNAL sub-agent (any error, or the largest few) under parent session `<id>` — for the Phase-3b sub-agent deep-dive |

**The operator section.** A session digest stops at `TRANSCRIPT_BYTE_CAP` and drops the rest, and the
operator's last turns are in that rest. They are kept: every operator turn after the cut is appended
as a `USER: ` line (each clipped at `PER_MESSAGE_TEXT_CAP`, redacted, outside the byte cap) under a
heading line that starts with `---` and says how many there are. A turn before the cut stays where it
happened, so each operator turn is in the digest exactly once. The rule line also ends the `USER:`
block before it for `sweep_user_corrections.py`. A sub-agent digest has no such section: no operator
speaks in a helper's transcript.

**Line endings.** Every file the extractor writes (`aggregate.json`, both kinds of digest,
`interaction-digest.md`) holds LF line endings and no carriage return at all, on every OS, and
`sweep_user_corrections.py` writes its own output the same way. The sweep numbers digest lines by LF
alone, as Grep and the Read tool do, so a `[session:line]` citation is the line they show — also in a
digest an older extractor wrote on Windows, where a CRLF inside a message had become CR CR LF.

## `aggregate.json` top-level keys

```jsonc
{
  "schemaVersion": 5,
  "generatedFor": { "sessionDir": "<path>", "since": "YYYY-MM-DD|null", "until": "…|null", "generatedAt": "<iso8601>" },
  "stats": { … },                  // see below
  "errorTaxonomy": { … },          // see below
  "subAgentErrorTaxonomy": { … },  // see below — same shape as errorTaxonomy, computed over sub-agent transcripts
  "deepDiveCandidates": { … },         // v4 — deterministic Phase-3 selection (see below)
  "subAgentDeepDiveCandidates": { … }, // v4 — deterministic Phase-3b selection (see below)
  "sessions": [ { … } ]            // see below
}
```

### `deepDiveCandidates` / `subAgentDeepDiveCandidates` (v4)

The Phase-3/3b ranking is now computed by the extractor (LLM arithmetic/sorting is a known
error class — the 06-22 run had to hand-write an ad-hoc script for this). The SKILL consumes
these lists as-is; qualifiers beyond the cap are listed in `overCap` (never silently dropped).

```jsonc
"deepDiveCandidates": {
  "selectionRule": "toolUse>=15 OR userMsgs>=6; rank toolUse desc, transcriptBytes desc, sessionId; top 8",
  "selected": [ { "sessionId": "…", "transcriptPath": "<ABSOLUTE>", "toolUse": 88, "userMsgs": 9, "transcriptBytes": 120034 } ],
  "overCap":  [ { "sessionId": "…", "toolUse": 21 } ]
},
"subAgentDeepDiveCandidates": {
  "selectionRule": "all emitted high-signal sub-agents; rank errorCount desc, bytes desc, file; top 6; at most 4 per parent session while others remain",
  "selected": [ { "parentSessionId": "…", "file": "agent-x.md", "transcriptPath": "<ABSOLUTE>", "errorCount": 3, "bytes": 9001, "emittedBytes": 4200 } ],
  // `bytes` = RAW source transcript size (and the rank key). `emittedBytes` (v4, additive) = the
  // redacted, size-capped digest actually on disk — measured at 1.6–2.6% of raw. Quote
  // emittedBytes, never bytes, when telling an analyst how much file to expect: under the old
  // bare-`bytes` header 4 of 6 analysts in the 2026-08-01 retro planned reads for a 400–700 KB
  // file that was 10–13 KB.
  "overCap":  [ { "parentSessionId": "…", "file": "agent-y.md", "errorCount": 1 } ]
}
```

### `stats`
```jsonc
{
  "totalSessions": 25,
  "dateRange": { "from": "<iso>", "to": "<iso>" },
  "totalUserMessages": 0,
  "totalToolCalls": 0,
  "totalThinkingBlocks": 0,
  "subAgent": { "files": 0, "bytes": 0, "msgs": 0 },   // nested sub-agent transcripts aggregated
  "branchesWorkedOn": ["…"],
  "skillsUsed": ["…"],                                  // v4: union of model-invoked (Skill tool) AND /slash names (every `slashCommands` name, whoever typed it) — same list shape; slash entries may include built-in commands (cross-check against `ls .claude/skills/`)
  "skillInvocationModes": { "session-retrospective": { "user": 2, "model": 0, "harness": 0 }, … },  // v4 — per-skill counts by invocation mode: user = a /command the operator typed, model = the Skill tool; v5 adds harness = a /command the harness typed (see `slashCommands[].by`)
  "skillsBlocked": ["…"],                               // skills invoked via the Skill tool that errored (disable-model-invocation friction)
  "allToolsUsed": { "Read": 344, "Edit": 456, … }
}
```

### `errorTaxonomy`
Errors are classified **by the ORIGIN tool** of each `tool_result` (paired via
`tool_result.tool_use_id` → `tool_use.id`). Content tools (Read/Grep/Glob/WebFetch/WebSearch/
ToolSearch/NotebookRead) are **never** errors unless the tool set `is_error` — this is why file/grep
content containing the word "Error:" is NOT counted (the false-positive fix).

```jsonc
{
  "byCategory": {
    "path-not-found":  { "count": 9,  "sessions": ["0f65932c", …], "samples": ["[id/Read] File does not exist…"] },
    "edit-stale-read": { "count": 20, "sessions": […], "samples": […] },
    "build-compile":   { "count": 0,  "sessions": [], "samples": [] },
    "test-failure":    { "count": 5,  "sessions": […], "samples": […] },
    "skill-blocked":   { "count": 5,  "sessions": […], "samples": […] },
    "runtime-exit":    { "count": 5,  "sessions": […], "samples": […] },
    "tool-error":      { "count": 5,  "sessions": […], "samples": […] },
    "environment":     { "count": 3,  "sessions": […], "samples": ["[id/Bash] <tool_use_error>Blocked: sleep 30 followed by: …", "[id/api-error] You've hit your 5-hour limit…"] },   // v5
    "other":           { "count": 0,  "sessions": [], "samples": [] }
  },
  "userRejected": { "count": 1, "sessions": ["0f65932c"], "samples": ["[id/Bash] The user doesn't want to proceed…"] },
  "hookDenials":  { "count": 2, "sessions": ["0f65932c"], "samples": ["[id/Bash] PreToolUse:Bash hook error: …"] },   // v4 (additive)
  "environmentShapes": { "sleep-denial": 2, "usage-limit": 1, "cd-denial": 0 }   // v5 — the environment count by shape, main thread; every shape listed
}
```
- **`userRejected` is a SEPARATE bucket** — permission denials are *friction*, not agent mistakes.
  A result lands here only when it is an error whose text STARTS with the harness's own denial
  sentence (`USER_REJECTED_SENTENCE`: "The user doesn't want to proceed with this tool use."; a
  trailing note or the user's own feedback after it is fine). A phrase found ANYWHERE in the text
  does not count: ripgrep's own usage errors ("ripgrep rejected the pattern, glob, or file type")
  and any error that merely quotes a denial phrase are ordinary `tool-error` / shell results.
  `count` is the TRUE number of hits (each session's own number is `sessions[].userRejected`);
  `samples` stay capped at 3 per session, so their length is not the count. **A report that
  compares with one built by an older extractor must say so:** the older run filed those usage
  errors here, so this bucket reads lower and `tool-error` higher, and a sub-agent whose only
  error was one is now error-bearing, which can change which sub-agent digests are emitted.
- **`hookDenials` is a count BESIDE the categories, not a category.** It is the number of error
  results whose text STARTS with the harness's hook prefix (`PreToolUse:<Tool> hook error: `),
  counted over the whole main-thread transcript while it is walked — not over the capped digest, so
  a denial after the cut is counted. `count` is the TRUE number (each session's own number is
  `sessions[].hookDenials`); `samples` stay capped at 3 per session. The result keeps the category
  it always had (`runtime-exit` for a shell tool, `tool-error` for most others): nothing in
  `byCategory` moved, so a hook-heavy window still inflates those buckets, and this count is how to
  take it back out. Output that quotes the prefix mid-text, a non-error result that starts with it,
  and a hook that did not answer in time are not denials. **Known loss:** a hook that denies by
  JSON returns only its own reason, with no prefix, and nothing else in the record names a hook (the
  harness's `toolDenialKind` stamp is shared with don't-ask mode, built-in safety checks and
  protected paths), so that form is NOT counted and the count is a floor. The one such hook read by
  its text is the kit's own shell-prefix gate, and it is read under `environment` (`cd-denial`),
  not here. Sub-agent transcripts are not counted here; their denials stay in the sub-agent
  taxonomy under their ordinary category.
- Category definitions:
  | Category | Meaning |
  |---|---|
  | `path-not-found` | Read/Edit/Write on a missing file (`does not exist` / `no such file`) |
  | `edit-stale-read` | Edit/Write rejected: file modified since read / not read yet |
  | `build-compile` | Shell non-zero exit with a lint, type-check or compile signature: ruff, basedpyright, mypy, pyright, `syntaxerror` or `compileerror` (any case); or a .NET build signature (exact case): MSBuild's `Build FAILED.` stamp, or `error MSB` or `error CS` plus four digits |
  | `test-failure` | Shell non-zero exit with a pytest/`test session starts`/`assertionerror`/`failed` signature (any case; the word `failed` alone is enough, so a .NET test summary's `Failed!` lands here) |
  | `skill-blocked` | Skill tool result errored (e.g. `disable-model-invocation`) |
  | `runtime-exit` | Shell non-zero exit, other |
  | `tool-error` | Any other non-shell tool with `is_error` — the non-shell catch-all |
  | `environment` | v5. Refused or stopped by the harness or a hook: give the rule a home, not an agent-quality count. An `is_error` result that OPENS (after leading whitespace and the harness's `<tool_use_error>` tag) with one of three shapes: `sleep-denial`, the harness's refusal of a long sleep put in front of a command (`Blocked: sleep N followed by`, or `Blocked: Start-Sleep N followed by` in PowerShell; shell tools only); `usage-limit`, the harness's limit sentence (`You've hit your … limit`; any tool); `cd-denial`, the kit shell-prefix gate's own MOVE text (`CD_DENIAL_ANCHOR`, which a test holds equal to the hook's text; shell tools only). Also a usage-limit stop: the assistant record the harness marks `isApiErrorMessage` whose text opens with the limit sentence, in the main thread and in sub-agents. Counted by shape in `environmentShapes` |
  | `other` | Reserved/forward-compat bucket — always emitted, currently always 0; `classify_error()` never returns it (catch-alls are `tool-error` for non-shell, `runtime-exit` for shell) |

  Shell errors are tested `build-compile` **before** `test-failure` (a result matching both
  signatures classifies as `build-compile`). Every error result is tested for the `environment`
  shapes before any of these (only the user-rejected sentence comes first), so a refused sleep put
  in front of a test run is `environment`, not `test-failure`. The same words anywhere but the
  opening of an error record (quoted in a failed command, a log or a workflow's failure list) are
  no shape, and a result that is not an error is data. A failed shell call opens with
  `Exit code N` whoever failed, so that opening names no shape and keeps its behavioural class. No
  other hook's wording is encoded (the kit is public): a project's own hook stays in its
  behavioural class.

### `subAgentErrorTaxonomy`
Same shape and ORIGIN-tool classifier as `errorTaxonomy`, but computed over **sub-agent** transcripts
(`<id>/subagents/**/agent-*.jsonl` nested under each session, including workflow agents). A workflow
run's `journal.jsonl` is its event log, not a transcript, and is not counted (an older extractor
counted it, so its sub-agent counts read one higher per workflow run). Sub-agent errors were invisible
before v3.

```jsonc
{
  "byCategory": {
    "path-not-found":  { "count": 4, "sessions": ["fffa4e1b", …], "samples": ["[id/sub] Read: File does not exist…"] },
    "edit-stale-read": { "count": 2, "sessions": […], "samples": […] },
    // … all ERROR_CATEGORIES, same as errorTaxonomy
  },
  "totalAgents": 246,         // total sub-agents seen across all sessions
  "agentsWithErrors": 12,     // sub-agents with >=1 classified error
  "transcriptsEmitted": 31,   // redacted sub-agent transcripts written under sessions/sub/
  "environmentShapes": { "sleep-denial": 4, "usage-limit": 6, "cd-denial": 0 }   // v5 — the sub-agents' environment count by shape; every shape listed
}
```
Samples carry an `[id/sub]` provenance tag so a sub-agent finding traces to its parent session. A
usage-limit stop's sample names `api-error` where a tool result's names its tool, in both
taxonomies.

### `sessions[]` (one object per session, sorted by start time)
```jsonc
{
  "sessionId": "<uuid>",
  "title": "…",                  // from ai-title, redacted
  "gitBranch": "…",
  "startTime": "<iso>", "endTime": "<iso>",
  "counts": { "userMsgs": 0, "assistantMsgs": 0, "toolUse": 0, "toolResult": 0, "thinking": 0 },
  "transcriptBytes": 0,          // size of sessions/<id>.md (use for "substantial session" ranking)
  "toolsUsed": { "Read": 12, … },
  "errorsByCategory": { "edit-stale-read": 3, … },   // per-session error counts
  "userRejected": 0,             // v4 (additive) — per-session count of user-rejected results (see `errorTaxonomy`); kept out of errorsByCategory and NOT capped like the samples
  "hookDenials": 0,              // v4 (additive) — per-session count of results a PreToolUse hook blocked (see `errorTaxonomy`); main thread, over the whole transcript, NOT capped; the result still counts in errorsByCategory
  "environmentShapes": { "sleep-denial": 2 },   // v5 — this session's errorsByCategory.environment split by shape, main thread; a shape never seen is left out
  "behavior": {
    "reReads": [ { "file": "~/…/learnings.md", "count": 7 } ],   // file read >=3x
    "repeatedCommands": [ { "cmd": "git diff --staged", "count": 2 } ],   // identical cmd >=2x
    "buildTestLoops": [ … ],     // subset of repeatedCommands matching test/build (see below)
    "staleReadEdits": 3          // == errorsByCategory["edit-stale-read"]
  },
  "skillInvocations": [ { "skill": "plan-critic", "blocked": true }, … ],
  "askUserQuestions": [ "Which approach do you prefer?", … ],   // for repetitive-question clustering
  "subAgents": {
    "count": 4, "bytes": 12345, "msgs": 120,
    "agents": [ { "type": "Explore", "goal": "find files" } ],          // metadata list, capped at 30
    "errorsByCategory": { "path-not-found": 2 },                        // sub-agent errors, this session
    "agentsWithErrors": 1,
    "errorSamples": { "path-not-found": ["[id/sub] Read: File does not exist…"] },
    "transcriptsEmitted": 3,                                            // # redacted sub-agent .md written
    "errorAgentsNotEmitted": 0,                                         // v4 — error-bearing agents beyond the emission cap (taxonomy-only; NOT derivable from agentsWithErrors − transcriptsEmitted, since emitted includes top-by-bytes non-error agents)
    "environmentShapes": { "usage-limit": 1 },                          // v5 — the sub-agents' errorsByCategory.environment split by shape; a shape never seen is left out
    "highSignal": [ { "file": "agent-x.md", "type": "general-purpose", "goal": "…", "bytes": 9001, "emittedBytes": 4200, "msgs": 40, "errorsByCategory": {…}, "transcriptPath": "<ABSOLUTE path to sessions/sub/<id>/agent-x.md>" } ]  // bytes = raw source; emittedBytes (v4) = the digest on disk
  },
  "transcriptPath": "<ABSOLUTE path to sessions/<id>.md>",   // functional; pass to deep-dive sub-agents (null only for 0-user sessions, which are filtered out before selection)
  "backtrackingMarkers": 7,      // thinking "wait/actually/reconsider" count — TARGETING HEURISTIC ONLY, never a finding
  "slashCommands": [ { "command": "session-retrospective", "args": "--since 2026-06-01", "by": "operator" } ],  // v4 — /skill invocations (<command-name> pseudo-user messages; redacted, capped at 40; not counted as userMsgs); v5 `by` = who typed it, see below
  "models": { "claude-fable-5": 42 },  // v4 — assistant model id -> message count (segment findings by model)
  "compactions": 1               // v4 — context-compaction boundaries ({"type":"system","subtype":"compact_boundary"}) — a friction signal
}
```

`slashCommands[].by` (v5) is `operator` or `harness`, decided by the record's stamps exactly as an
operator turn is (one rule, which `operator_turn_text` reads too): `operator` for an `origin` stamp
of kind `human`, or for no `origin` stamp and none of the machine markers (`isMeta`,
`isCompactSummary`, a `turnOrigin` of a program or the harness); otherwise `harness`.
`stats.skillInvocationModes` counts the two apart, as `user` and `harness`.

`behavior.buildTestLoops` is the part of `repeatedCommands` (identical text, at least twice) that
`TEST_BUILD_RE` matches anywhere in the first 120 characters of the command, in any case: the tools
the pattern already listed (`pytest`, `ruff`, `uv run` and the rest of its alternatives) and these
.NET commands, which are the list the pattern's .NET half is built from: `dotnet build`,
`dotnet test`, `dotnet restore`, `dotnet publish`, `dotnet msbuild`, `msbuild`, `nuget restore`,
`dotnet format`. A .NET command counts as typed: the program may carry `.exe`, its words are apart
by blanks on one line, and it stands alone as a command word (no name, dot or hyphen fused to it,
no slash or backslash after it), so `msbuild.log`, `run-msbuild`, `tools/msbuild/bin` and
`dotnet build-server` do not count, and neither do `dotnet run`, `dotnet new` or `dotnet --info`.
When the pattern changes, change this paragraph with it; a test holds the two together.

**Compare like with like before reading a with-and-without contrast as an effect:** sessions that
used a skill, set against sessions that did not, can also differ in model (`models`), size
(`counts`, `transcriptBytes`) and kind of work (`toolsUsed`), so match the two groups on those
fields first.

## Redaction & privacy

- Every emitted **content** string is redacted: `sk-`/`sk-ant-` keys, JWTs, `Authorization: Bearer`,
  GCP `private_key`/service-account JSON, PEM blocks, Google/AWS key prefixes, GitHub tokens
  (`ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`/`github_pat_`), generic
  `*(KEY|TOKEN|SECRET|PASSWORD|PWD|CRED)* = value`, long hex/base64, and home-dir paths → `~`.
- `transcriptPath` is the one intentionally **unredacted absolute path** (sub-agents need it). It
  lives only in `aggregate.json` under the gitignored temp dir and never enters the report.
- Emitted sub-agent transcripts (`sessions/sub/<id>/*.md`) are redacted by the SAME `redact()` and
  `--self-check` scans them too (it rglobs `sessions/`), so they cannot leak either.
- `--self-check` greps the artifacts for high-confidence secret shapes; exit code 3 on any hit.
- `interaction-digest.md` (see § Session scoping) quotes **user messages verbatim** and is therefore
  the highest-risk artifact emitted. It is listed explicitly in `self_check()`, and on a leak the
  digest is **deleted** before exit 3 — a consumed artifact must not remain readable after failing
  the gate. **Any new emitted file must be added to that list**; omission is silent, because the run
  still prints `SELF-CHECK PASSED`.
- Redaction is **secret shapes only** — there are no email or PII patterns. Anything quoting user
  text into a *tracked* file must be written knowing that.

## Invocation

```bash
# <session-dir> is derived from the working directory, which must be the project root — omit it.
# From anywhere else the run exits 1 and asks for it as the first argument.
# `generatedFor.sessionDir` records which dir was used.
python "${CLAUDE_SKILL_DIR}/scripts/extract_sessions.py" \
  ".ai/tmp/retro/" [--since YYYY-MM-DD] [--until YYYY-MM-DD] --self-check
```
Pure stdlib (no third-party deps). The project `.venv` python or system `python` both work;
`uv run` is NOT required (and may trigger an environment sync/rebuild).

`--since`/`--until` filter on date **overlap** (a session straddling a boundary is included), not
strict containment. With neither flag, ALL history is processed (the 14-day default is applied by
the calling skill, not the extractor).

### Session scoping (`--session`, `--digest`) — consumed by `task-learnings`

```bash
python "${CLAUDE_SKILL_DIR}/scripts/extract_sessions.py" \
  ".ai/tmp/task-learnings/<SESSION-ID>/" --session <SESSION-ID|current> --digest --self-check
```

`--session` restricts the run to ONE transcript and **overrides `--since`/`--until`** (the caller
named the session, so a stale window must not silently drop it and produce an empty digest that
reads as "no signal"). It accepts a full session id, a unique prefix, or `current`.

**`current` fails closed.** It resolves by newest-mtime, and if any other transcript was written
within `CURRENT_AMBIGUITY_WINDOW_S` (180 s) it exits **4** and lists every candidate with its id,
last-activity, and first user message — rather than guessing. This is not defensive theatre:
verified 2026-08-14, **four** transcripts in this checkout had been written within that window and
newest-mtime pointed at an unrelated session. Callers that know their own id (it is the last segment
of the Claude Code scratchpad path) should pass it explicitly and skip the ambiguity entirely.

Every run prints the resolved id plus the session's first user message, so a **wrong pick is
detectable by the caller** instead of silently becoming a finding about work it never did.

`--digest` requires `--session` and writes `interaction-digest.md`: counted repetition signals
(re-reads at or above `--rereads-min`, default `DEFAULT_REREADS_MIN` = 6), agent error classes with
≥2 occurrences, and the session's **operator turns**: what the operator typed, what they typed
while the model was working (a `queued_command` attachment record, which no user record
duplicates), and the answers they gave the question tool. ONE function, `operator_turn_text`,
decides which records those are, by structure and not by wording — `origin.kind` human on a user
record, a human `queued_command` prompt, an `AskUserQuestion` result that carries a dict of
answers — and the operator section of a session digest shares it with this list and its header.
Harness noise (skill payloads, task-notifications, command wrappers, hand-backs, and the plain-text
notices that continue a compacted session, nudge a resume, report a classifier stop or open a
workflow-authoring reference) is not an operator turn and is not listed; neither is a slash command
the operator typed, which `sessions[].slashCommands` captures. A record with no `origin` stamp (an
older transcript) falls back to its machine markers and to `HARNESS_USER_PREFIXES`, which is
deliberately separate from `SYSTEM_PREFIXES` because that tuple feeds `counts.userMsgs` and
therefore `deepDiveCandidates` selection for the whole retrospective. `sweep_user_corrections.py`
keeps a mirror list (`SKIP_PREFIX`); a test imports both by path and fails when the two differ.

The digest's header prints `Volume: N operator turns` (the number listed, not capped at the 40
shown) and, on a line of its own, `User-channel records: M`. `M` is `counts.userMsgs`: it counts
injected text as well, so it is not the number of operator turns, and it stays as it is because it
selects the deep-dive sessions.

**Re-asks are deliberately NOT detected.** Corrections have lexical markers that
`sweep_user_corrections.py` can grep; a re-ask is the same request restated in different words and
has none, so a similarity score would false-positive on shared domain vocabulary and miss terse
restatements. The digest emits the sequence and the reader classifies.

**A message that opens with "proceed" is read against the message above it.** Classify that
assistant message first, and do not file the "proceed" as feedback on the agent's claim until you
have. About 90% of such messages, in the one corpus where this was measured, followed a platform stop
or a guard wait (a session or weekly limit, an access or connector notice, a quota-guard pause): the
operator was restarting halted work, which is neither an approval nor a correction, and counting it
as either inflates the feedback tally. Another kind is a bare "proceed" after the agent's own
completion report: it marks a premature completion (a local milestone presented as the end of the
task) and belongs in the findings as such. If the message above is not in the digest, read it in the
transcript before classifying.

Threshold provenance (measured 2026-08-14, 90 sessions / 85 substantial): the extractor never
records a re-read below **3**, so a "≥2 occurrences" filter is vacuous; a count of exactly 3 is the
**mode** (63 of 137, 46%) and is most likely the AGENTS.md-mandated read→edit→re-read cycle, i.e.
compliance rather than thrash. Session yield: 73% @≥3, 54% @≥4, 42% @≥5, **31% @≥6**, 18% @≥8,
8% @≥10. The data localizes the honest cut to **4–8** without picking a value inside it — hence a
parameter, not a constant.

### v4 run behaviors

- **Date pre-scan:** with `--since`/`--until`, each `.jsonl` gets a cheap first/last-timestamp
  scan (head lines + tail bytes) and clearly out-of-range sessions are skipped BEFORE the full
  parse (the sub-agent walk is the expensive part). Undeterminable dates → full parse; the exact
  overlap filter still applies after parsing. Skips are counted on stderr
  (`Pre-scan skipped N …`) — never silent.
- **Output hygiene:** stale `sessions/**/*.md` transcripts from previous runs are cleared at
  startup **with a stderr notice** (never silently), so Phase-5 grep verification cannot hit
  files from an earlier window.
- **`--check-file <path>`:** standalone leak gate — runs the same `LEAK_PATTERNS` over ONE file
  (exit 3 on a hit, 0 clean). Used by the SKILL's Phase 6 to gate the draft report; no other
  arguments required in this mode.
- **Replayed events:** a session that was resumed or compacted can write earlier events into its
  transcript a second time (the same top-level `uuid` and message, a re-stamped `slug`). The
  extractor reads each `uuid` once per transcript file, the first occurrence, in the main thread and
  in sub-agent files alike; a line with no usable `uuid` (state lines, older transcripts) is always
  read. `counts`, `behavior` and both digests therefore count each event once, so a window that held
  such a session reads lower than a report built by an older extractor. The number left out is
  printed once on stderr (`Replayed events: skipped N repeated event(s) in M session(s)`), only when
  it is above zero and only for sessions in the aggregate; there is no aggregate key for it.

## Porting the extractor to another repo

- **Porting this script elsewhere** — three facts none of the docs state, each verified from code:
  (a) `from datetime import UTC` pins the extractor to **Python 3.11+**; a consumer repo on 3.10
  fails at import, so any distribution must state the floor from code evidence, not assumption.
  (b) The redaction is **SECRET-shapes only** (keys/GitHub tokens/JWTs/bearer/PEM/hex/home-paths) —
  there are **no email or PII patterns**. For transcripts carrying customer or research content,
  re-evaluate that scope and state it honestly rather than claiming "redacted" generically.
  (c) Root detection
  differs per script: this extractor reads the working directory, which must be the project root
  with a session folder of its own under `~/.claude/projects/`, while the kit's `lint` command
  looks for `.ai` + `.git` — so an install must create `.ai/` **before** the first lint run, and a
  repo never opened in Claude Code has no `~/.claude/projects/<encoded>` dir, so the extractor
  refuses it (exit 1) and asks for the session dir.
