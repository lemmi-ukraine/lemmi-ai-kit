# Extractor Output Schema (`extract_sessions.py`)

This documents what `scripts/extract_sessions.py` emits. The **machine source of truth** is the
`SCHEMA_KEYS` constant inside the extractor; the extractor's `--self-check` and the pytest assert
that the emitted `aggregate.json` matches `SCHEMA_KEYS`. **When you change the extractor's output,
update `SCHEMA_KEYS` AND this doc together** — the content-reviewer cross-checks this doc against the
constant and the SKILL.md.

`schemaVersion`: **4** (v4 is ADDITIVE-ONLY: deterministic deep-dive candidate lists,
slash-command capture, per-session models + compaction counts, `errorAgentsNotEmitted`,
`skillInvocationModes`, plus non-schema behaviors — date pre-scan, stale-output clearing,
`--check-file`; existing v3 keys/shapes unchanged, so v3 consumers — the SKILL phases and any
downstream analysis skill — keep working. v3 added the sub-agent error taxonomy + emitted
redacted sub-agent transcripts; v2 added per-session transcripts + sub-agent counts; v1 was the
legacy Node.js flat summary).

## Artifacts

The extractor writes into `<output-dir>` (always repo-relative, e.g. `.ai/tmp/retro/`, gitignored):

| File | Purpose |
|------|---------|
| `aggregate.json` | Cross-session error taxonomy + per-session behavioral metrics + stats |
| `sessions/<id>.md` | Per-session readable transcript, size-capped (120 KB), fully redacted — for deep reading by sub-agents |
| `sessions/sub/<id>/<agent>.md` | Redacted, size-capped transcript of a HIGH-SIGNAL sub-agent (any error, or the largest few) under parent session `<id>` — for the Phase-3b sub-agent deep-dive |

## `aggregate.json` top-level keys

```jsonc
{
  "schemaVersion": 4,
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
  "selectionRule": "all emitted high-signal sub-agents; rank errorCount desc, bytes desc, file; top 6",
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
  "skillsUsed": ["…"],                                  // v4: union of model-invoked (Skill tool) AND user-typed (/slash) names — same list shape; user-mode entries may include built-in commands (cross-check against `ls .claude/skills/`)
  "skillInvocationModes": { "session-retrospective": { "user": 2, "model": 0 }, … },  // v4 — per-skill counts by invocation mode
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
    "other":           { "count": 0,  "sessions": [], "samples": [] }
  },
  "userRejected": { "count": 1, "sessions": ["0f65932c"], "samples": ["[id/Bash] The user doesn't want to proceed…"] }
}
```
- **`userRejected` is a SEPARATE bucket** — permission denials are *friction*, not agent mistakes.
- Category definitions:
  | Category | Meaning |
  |---|---|
  | `path-not-found` | Read/Edit/Write on a missing file (`does not exist` / `no such file`) |
  | `edit-stale-read` | Edit/Write rejected: file modified since read / not read yet |
  | `build-compile` | Shell non-zero exit with ruff/basedpyright/mypy/syntax signature |
  | `test-failure` | Shell non-zero exit with pytest/test/assertion signature |
  | `skill-blocked` | Skill tool result errored (e.g. `disable-model-invocation`) |
  | `runtime-exit` | Shell non-zero exit, other |
  | `tool-error` | Any other non-shell tool with `is_error` — the non-shell catch-all |
  | `other` | Reserved/forward-compat bucket — always emitted, currently always 0; `classify_error()` never returns it (catch-alls are `tool-error` for non-shell, `runtime-exit` for shell) |

  Shell errors are tested `build-compile` **before** `test-failure` (a result matching both
  signatures classifies as `build-compile`).

### `subAgentErrorTaxonomy`
Same shape and ORIGIN-tool classifier as `errorTaxonomy`, but computed over **sub-agent** transcripts
(`<id>/subagents/**/*.jsonl` nested under each session, including workflow agents). Sub-agent errors
were invisible before v3.

```jsonc
{
  "byCategory": {
    "path-not-found":  { "count": 4, "sessions": ["fffa4e1b", …], "samples": ["[id/sub] Read: File does not exist…"] },
    "edit-stale-read": { "count": 2, "sessions": […], "samples": […] },
    // … all ERROR_CATEGORIES, same as errorTaxonomy
  },
  "totalAgents": 246,         // total sub-agents seen across all sessions
  "agentsWithErrors": 12,     // sub-agents with >=1 classified error
  "transcriptsEmitted": 31    // redacted sub-agent transcripts written under sessions/sub/
}
```
Samples carry an `[id/sub]` provenance tag so a sub-agent finding traces to its parent session.

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
  "behavior": {
    "reReads": [ { "file": "~/…/learnings.md", "count": 7 } ],   // file read >=3x
    "repeatedCommands": [ { "cmd": "git diff --staged", "count": 2 } ],   // identical cmd >=2x
    "buildTestLoops": [ … ],     // subset of repeatedCommands matching test/build
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
    "highSignal": [ { "file": "agent-x.md", "type": "general-purpose", "goal": "…", "bytes": 9001, "emittedBytes": 4200, "msgs": 40, "errorsByCategory": {…}, "transcriptPath": "<ABSOLUTE path to sessions/sub/<id>/agent-x.md>" } ]  // bytes = raw source; emittedBytes (v4) = the digest on disk
  },
  "transcriptPath": "<ABSOLUTE path to sessions/<id>.md>",   // functional; pass to deep-dive sub-agents (null only for 0-user sessions, which are filtered out before selection)
  "backtrackingMarkers": 7,      // thinking "wait/actually/reconsider" count — TARGETING HEURISTIC ONLY, never a finding
  "slashCommands": [ { "command": "session-retrospective", "args": "--since 2026-06-01" } ],  // v4 — user-typed /skill invocations (<command-name> pseudo-user messages; redacted, capped at 40; not counted as userMsgs)
  "models": { "claude-fable-5": 42 },  // v4 — assistant model id -> message count (segment findings by model)
  "compactions": 1               // v4 — context-compaction boundaries ({"type":"system","subtype":"compact_boundary"}) — a friction signal
}
```

## Redaction & privacy

- Every emitted **content** string is redacted: `sk-`/`sk-ant-` keys, JWTs, `Authorization: Bearer`,
  GCP `private_key`/service-account JSON, PEM blocks, Google/AWS key prefixes, generic
  `*(KEY|TOKEN|SECRET|PASSWORD|PWD|CRED)* = value`, long hex/base64, and home-dir paths → `~`.
- `transcriptPath` is the one intentionally **unredacted absolute path** (sub-agents need it). It
  lives only in `aggregate.json` under the gitignored temp dir and never enters the committed report.
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
# <session-dir> is auto-derived from the repo root + ~/.claude/projects/ — omit it (pass it only to
# override, e.g. a personal-scope install). `generatedFor.sessionDir` records which dir was used.
python scripts/extract_sessions.py \  # path relative to this skill's directory
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
  ".ai/tmp/task-learnings/" --session <SESSION-ID|current> --digest --self-check
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
≥2 occurrences, and the session's **human turns** — harness noise (skill payloads,
task-notifications, command wrappers) filtered by `HARNESS_USER_PREFIXES`, which is deliberately
separate from `SYSTEM_PREFIXES` because that tuple feeds `counts.userMsgs` and therefore
`deepDiveCandidates` selection for the whole retrospective.

**Re-asks are deliberately NOT detected.** Corrections have lexical markers that
`sweep_user_corrections.py` can grep; a re-ask is the same request restated in different words and
has none, so a similarity score would false-positive on shared domain vocabulary and miss terse
restatements. The digest emits the sequence and the reader classifies.

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

## Porting the extractor to another repo

- **Porting this script elsewhere** — three facts none of the docs state, each verified from code:
  (a) `from datetime import UTC` pins the extractor to **Python 3.11+**; a consumer repo on 3.10
  fails at import, so any distribution must state the floor from code evidence, not assumption.
  (b) The redaction is **SECRET-shapes only** (keys/JWTs/bearer/PEM/hex/home-paths) — there are **no
  email or PII patterns**. For transcripts carrying customer or research content, re-evaluate that
  scope and state it honestly rather than claiming "redacted" generically. (c) Root detection
  differs per script: this extractor walks up to the dir containing `.claude/`, while
  the kit's `lint` command looks for `.ai` + `.git` — so an install must create `.ai/` **before** the
  first lint run, and a repo never opened in Claude Code has no `~/.claude/projects/<encoded>` dir
  for the extractor to find at all.
