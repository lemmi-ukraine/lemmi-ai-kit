#!/usr/bin/env python3
"""Behavioral extractor for Claude Code JSONL session transcripts.

Reads a project's Claude session directory and emits TWO artifacts into <output-dir>:

  aggregate.json    cross-session error taxonomy + per-session behavioral metrics
  sessions/<id>.md  per-session readable, size-capped, redacted transcript (for deep reading); the
                    operator's turns the cap cut off follow it in a section of their own

Design (see references/extractor-output-schema.md):
  * tool_result is paired to its originating tool_use by id; errors are classified by ORIGIN
    tool. Content-producing tools (Read/Grep/Glob/WebFetch/WebSearch/ToolSearch/NotebookRead)
    are DATA, never errors, unless the tool itself set is_error. This is what kills the
    substring-on-content false-positive class — do NOT reintroduce substring matching on it.
  * Secret redaction is applied to every emitted string; --self-check greps outputs with the
    same high-confidence patterns to prove nothing leaked.
  * Each event is counted once: a resumed or compacted session can write earlier events into its
    transcript again, and iter_jsonl keeps the first occurrence of each uuid (a run that left any
    out says how many on stderr).
  * Robust: streams line by line, guards malformed lines / huge files / unknown types, skips
    sessions with zero real user messages, never aborts the whole run on one bad file.

Usage:
  python extract_sessions.py [<session-dir>] <output-dir> [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--self-check]
  python extract_sessions.py [<session-dir>] <output-dir> --session <id|current> [--digest] [--self-check]
  python extract_sessions.py [<session-dir>] <output-dir> [--session <id> ...] [--sessions-from <hand-off> ...] [--digest] [--self-check]

The last form is task mode (two or more --session, or any --sessions-from): it measures exactly
the sessions a task's hand-offs list, and their helpers, and exits 5 when one of them could not be
measured (see the task-mode comment above read_handoff_ledger, and the Session scoping section of
extractor-output-schema.md).

<session-dir> is OPTIONAL — when omitted it is derived from the working directory plus
~/.claude/projects/ (see _derive_session_dir), so the skill works for any engineer on any machine
without a hardcoded path. The working directory must be the project root, the directory Claude
Code was launched in, and that project must have a session folder of its own. The script's own
location says nothing about the project (an installed plugin sits under the home directory's
.claude/), so it is not used. From anywhere else (a subdirectory, the home directory, a folder
Claude Code never ran in) the run is refused and <session-dir> is required as the first argument:
no corpus is ever guessed. <output-dir> MUST be repo-relative
(e.g. .ai/tmp/retro/), never the system /tmp (shells and platforms resolve /tmp inconsistently).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 5

# --- schema contract (machine source of truth; mirrored in extractor-output-schema.md) ---
# v4 is ADDITIVE-ONLY over v3: existing keys/shapes unchanged (other consumers — the SKILL.md
# phases and any downstream analysis skill — keep working); new keys listed at the end.
# v5 renames and removes no key, but it MOVES counts: the `environment` category takes the results
# the harness or a hook refused or stopped out of the behavioural categories (see
# environment_shape), and a slash command the harness typed counts under `harness`, not `user`.
SCHEMA_KEYS = {
    "top": [
        "schemaVersion",
        "generatedFor",
        "stats",
        "errorTaxonomy",
        "subAgentErrorTaxonomy",
        "sessions",
        "deepDiveCandidates",  # v4 (C-1): deterministic Phase-3 selection
        "subAgentDeepDiveCandidates",  # v4 (C-1): deterministic Phase-3b selection
    ],
    "session": [
        "sessionId",
        "title",
        "gitBranch",
        "startTime",
        "endTime",
        "counts",
        "transcriptBytes",
        "toolsUsed",
        "errorsByCategory",
        "behavior",
        "skillInvocations",
        "askUserQuestions",
        "subAgents",
        "transcriptPath",
        "backtrackingMarkers",
        "slashCommands",  # v4 (C-2): user-typed /skill invocations
        "models",  # v4 (C-4a): assistant model ids seen -> msg count
        "compactions",  # v4 (C-4b): context-compaction boundary count
        "userRejected",  # v4 (additive): TRUE count of user-rejected results (samples are capped)
        "hookDenials",  # v4 (additive): TRUE count of results a PreToolUse hook blocked, main thread
        "environmentShapes",  # v5: environment shape -> count, main thread
    ],
}

ERROR_CATEGORIES = [
    "path-not-found",
    "edit-stale-read",
    "build-compile",
    "test-failure",
    "skill-blocked",
    "runtime-exit",
    "tool-error",
    "environment",
    "other",
]

# Tools whose tool_result is content (data), never an error unless is_error is set.
CONTENT_TOOLS = {
    "Read",
    "Grep",
    "Glob",
    "WebFetch",
    "WebSearch",
    "ToolSearch",
    "NotebookRead",
}
SHELL_TOOLS = {"Bash", "PowerShell"}
# The .NET commands that count as a build or a test run, with the restore, publish and format runs
# around them, beside the tools TEST_BUILD_RE already listed. This list builds the .NET half of
# the pattern, and extractor-output-schema.md names the same commands where it says what
# buildTestLoops holds, so a command is added here and in that sentence together. What else the
# program does (run, new, tool, pack, clean, --info) is no build or test run and stays out.
DOTNET_BUILD_TEST_COMMANDS = (
    "dotnet build",
    "dotnet test",
    "dotnet restore",
    "dotnet publish",
    "dotnet msbuild",
    "msbuild",
    "nuget restore",
    "dotnet format",
)


def _command_pattern(command):
    """The pattern for one command as it is typed, never as a word inside another name.

    The program may carry ".exe", its words are apart by blanks on ONE line (a newline ends a
    command), and no word character, dot or hyphen sits before it, nor one of those, a slash or
    a backslash after it. So "msbuild.log", "nuget.config", "tools/msbuild/bin" and
    "dotnet build-server" are no runs, while "MSBuild.exe", "nuget.exe restore" and
    "/usr/share/dotnet/dotnet test" are.
    """
    program, *words = command.split()
    return (
        r"(?<![\w.-])"
        + re.escape(program)
        + r"(?:\.exe)?"
        + "".join(r"[ \t]+" + re.escape(word) for word in words)
        + r"(?![\w.\\/-])"
    )


TEST_BUILD_RE = re.compile(
    "|".join(
        [
            r"(pytest|docker compose.*test|ruff|basedpyright|mypy|alembic|npm test|uv run)",
            *map(_command_pattern, DOTNET_BUILD_TEST_COMMANDS),
        ]
    ),
    re.I,
)

# Text that marks an IDE/system-injected pseudo-user message (not real user input).
SYSTEM_PREFIXES = (
    "<ide_",
    "<system-reminder>",
    "<command-name>",
    "<command-message>",
    "<local-command",
    "The user opened the file",
    "Caveat:",
    "[Request interrupted",
)

PER_MESSAGE_TEXT_CAP = 2000
TRANSCRIPT_BYTE_CAP = 120 * 1024
# Opens the section of operator turns a session digest keeps after the byte cap (outside it). It
# starts with a rule on purpose: sweep_user_corrections.py ends a USER block at a line that begins
# with "---", so the block before the section does not absorb the heading.
OPERATOR_SECTION_RULE = "--- Operator turns after the cut ({n}): outside the byte cap, in transcript order ---"
SAMPLES_PER_CATEGORY = 3
RE_READ_THRESHOLD = 3
REPEAT_CMD_THRESHOLD = 2
# Sub-agent transcript emission: emit only the HIGH-SIGNAL ones (any error, or the largest few) so a
# retrospective can deep-read them without ever touching raw .jsonl. Bounded so a large fan-out
# can't explode the output; emitted-vs-total is logged (no silent truncation).
SUBAGENT_TOP_BYTES_EMIT = 2
MAX_SUBAGENT_EMIT_PER_SESSION = 8
# A helper's transcript is agent-<id>.jsonl, directly under <session>/subagents/ or under
# <session>/subagents/workflows/wf_<run>/. Nothing else under subagents/ is one: each workflow run
# leaves a journal.jsonl there too, the run's event log (no message, no uuid). The sidecar
# agent-<id>.meta.json is NOT part of the test, because real agent transcripts exist without one.
SUBAGENT_GLOB = "agent-*.jsonl"
# The folder under subagents/ that holds the Workflow runs; a helper anywhere else is native.
SUBAGENT_WORKFLOWS_DIR = "workflows"

# Deep-dive candidate selection (v4, C-1): the Phase-3/3b ranking used to be done by the model
# (LLM arithmetic/sorting is a known error class; the 06-22 run hand-wrote an ad-hoc script for
# it). The extractor now emits the selections deterministically; the SKILL consumes the lists.
DEEP_DIVE_TOOLUSE_MIN = 15
DEEP_DIVE_USERMSGS_MIN = 6
DEEP_DIVE_CAP = 8
SUBAGENT_DEEPDIVE_CAP = 6
# A soft limit on one parent session's share of those sub-agent picks: its later candidates wait
# while any other candidate remains, and a slot still free after that pass is filled from the
# ones that waited, so one busy parent still fills every slot. A starting value, not calibrated.
SUBAGENT_DEEPDIVE_PER_PARENT_CAP = 4

# Slash-command capture (v4, C-2): user-typed "/skill" runs surface as <command-name> pseudo-user
# messages, which SYSTEM_PREFIXES filters out of user text — previously making the primary
# invocation path of user-invocable skills invisible to the skill-effectiveness analysis.
COMMAND_NAME_RE = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
COMMAND_ARGS_RE = re.compile(r"<command-args>([\s\S]*?)</command-args>")
SLASH_COMMANDS_CAP = 40

# Date pre-scan (v4, C-3): bytes read from each end of a .jsonl to find first/last timestamps
# before committing to a full parse (sub-agent walks make full parses expensive).
PRESCAN_HEAD_LINES = 50
PRESCAN_TAIL_BYTES = 64 * 1024
TIMESTAMP_RE = re.compile(r'"timestamp"\s*:\s*"(\d{4}-\d{2}-\d{2}[^"]*)"')

# --- redaction -------------------------------------------------------------------------------
# GitHub tokens are matched by SHAPE. The KEY/TOKEN assignment pattern below masks a token only
# right after such a name and "=" or ":", so one after a flag ("-p <token>") or in an
# "Authorization: token <token>" header was emitted as it was, and the leak gate could not see it
# either. REDACTIONS and LEAK_PATTERNS hold the same compiled pattern, so the gate looks for
# exactly what the redaction masks. Shapes: "GitHub's token formats" in "About authentication to
# GitHub" (docs.github.com), and "Behind GitHub's new authentication token formats" (github.blog).
#   * ghp_ gho_ ghu_ ghs_ ghr_: base62, 30 random characters plus a 6-character checksum. The
#     bound is 36 or more with no maximum, because GitHub says lengths will likely grow. The class
#     holds no "_", "-" or ".", so "ghs_installation_token" and "fix/ghp_rotation-fix" are not
#     tokens.
#   * github_pat_: GitHub states no length. "_" is in its alphabet, so a snake_case name that
#     starts with the prefix would pass; the lookahead demands an uppercase letter, which such a
#     name never has and a random 36-character base62 body lacks about 3 times in a billion.
#   * The stateless ghs_ token (a ghs_-prefixed JWT) needs no pattern: the JWT pattern runs before
#     these and masks it.
# Same left-boundary guard as the sk- patterns below: a letter or digit before the prefix means
# the tail of a word.
GITHUB_PREFIXED_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36,}")
GITHUB_FINE_GRAINED_PAT_RE = re.compile(
    r"(?<![A-Za-z0-9])github_pat_(?=[A-Za-z0-9_]*[A-Z])[A-Za-z0-9_]{36,}"
)

REDACTIONS = [
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
        ),
        "[REDACTED_PEM]",
    ),
    (re.compile(r'"private_key"\s*:\s*"[^"]*"'), '"private_key":"[REDACTED]"'),
    (re.compile(r'"type"\s*:\s*"service_account"'), '"type":"[REDACTED_SA]"'),
    # The `sk-` patterns are guarded on the LEFT against a preceding alphanumeric. Unguarded, they
    # match the tail of any ordinary hyphenated word ending in "sk" — "ta|sk-generation",
    # "subta|sk-audit" — and the redaction then silently rewrites real paths. Measured on one
    # corpus: all 28 substitutions were false positives (20 preceded by "ta", 1 by "subta", 6 by
    # "a"), and ZERO were real keys.
    #
    # Why `(?<![A-Za-z0-9])` and not a plain `\b` — measured, not reasoned: `\b` also rejects the
    # "task-" case, but it rejects a REAL key prefixed by an underscore too ("KEY_sk-<key>" ->
    # no match), because `_` is a word character. The explicit class refuses letters and digits
    # while still redacting after `_`, `=`, `"` and friends. Fixtures for both live in
    # test_extract_sessions.py; keep the underscore-prefixed positive case if this is ever retuned.
    #
    # NOTE: neither form can fix a key-SHAPED string sitting in ordinary prose (preceded by a
    # space) — e.g. documentation quoting an example. That class is handled by DOC_EXAMPLE_ALLOWLIST
    # below, deliberately as an exact-literal allow-list rather than a further regex relaxation.
    (re.compile(r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_\-]{12,}"), "[REDACTED_KEY]"),
    (re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}"), "[REDACTED_KEY]"),
    # Stripe: secret and restricted API keys (sk_ or rk_, then test or live) and webhook signing
    # secrets (whsec_), then a run of letters and digits. Stripe keys hold nothing else, so the
    # class is narrower than the sk- one: with `_` in it, an identifier such as
    # `sk_live_flag_enabled_in_checkout` would be redacted whole. Same left-boundary guard as the
    # sk- patterns, for the same reason: "ta|sk_test_..." is the tail of a word, not a key.
    (
        re.compile(r"(?<![A-Za-z0-9])(?:[sr]k_(?:test|live)|whsec)_[A-Za-z0-9]{16,}"),
        "[REDACTED_KEY]",
    ),
    (
        re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}"),
        "[REDACTED_JWT]",
    ),
    (
        re.compile(r"(?i)authorization:\s*bearer\s+\S+"),
        "Authorization: Bearer [REDACTED]",
    ),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.]{12,}"), "Bearer [REDACTED]"),
    (re.compile(r"AIza[A-Za-z0-9_\-]{20,}"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"AKIA[A-Z0-9]{12,}"), "[REDACTED_AWS_KEY]"),
    (GITHUB_PREFIXED_TOKEN_RE, "[REDACTED_GITHUB_TOKEN]"),
    (GITHUB_FINE_GRAINED_PAT_RE, "[REDACTED_GITHUB_TOKEN]"),
    (
        re.compile(
            r"(?i)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PWD|CRED)[A-Z0-9_]*)\s*[=:]\s*([^\s,;\"']{4,})"
        ),
        r"\1=[REDACTED]",
    ),
    # Long hex runs are redacted EXCEPT exactly-40 and exactly-64, which are git SHA-1 and
    # sha256 digests. Those are citation anchors, not secrets, and blanket redaction destroys the
    # provenance the report exists to carry — one measured run lost 70 anchors. The exemption is
    # deliberately length-exact: a 39- or 41-char run is still redacted, so a real secret has to
    # land on one of two exact lengths to slip through, and hex of exactly those lengths is
    # overwhelmingly a digest in this corpus.
    (
        re.compile(r"\b(?![A-Fa-f0-9]{40}\b)(?![A-Fa-f0-9]{64}\b)[A-Fa-f0-9]{32,}\b"),
        "[REDACTED_HEX]",
    ),
    (re.compile(r"(?i)[a-z]:\\users\\[^\\/\s]+"), "~"),
    (re.compile(r"(?i)/(?:c/)?users/[^\\/\s]+"), "~"),
    (re.compile(r"/home/[^\\/\s]+"), "~"),
    # Separator-stripped Windows home path: when the Bash tool eats the backslashes a path collapses
    # to e.g. "c:UsersjdoeDocuments…" — the patterns above need separators and miss it, leaking the
    # username. Drive-letter-anchored so it won't match mid-word "…s:users…".
    (re.compile(r"(?i)\b[a-z]:users[a-z0-9._\-]+"), "~"),
]
# High-confidence shapes whose presence in OUTPUT means a redaction miss (used by --self-check).
LEAK_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])(?:[sr]k_(?:test|live)|whsec)_[A-Za-z0-9]{16,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{12,}"),
    GITHUB_PREFIXED_TOKEN_RE,
    GITHUB_FINE_GRAINED_PAT_RE,
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r'"private_key"\s*:\s*"[^"\]]{8,}"'),
]

# Exact literals that LOOK like secrets but are documentation examples — typically this project's
# own write-ups of a past false positive, which then become new false positives when the gate runs
# over a draft report. Measured: one such string tripped the gate 7x across a repo's `.ai/` files.
#
# This is an ALLOW-LIST, not a regex relaxation, and that distinction is the point: every entry is
# an exact full-match string, so adding one cannot silently widen what the gate accepts. A regex
# broad enough to excuse these would also excuse real keys, because the only thing distinguishing
# them is *which literal it is* — no amount of context-matching recovers that.
#
# Rules for adding an entry: it must be a string that is safe to publish, it must be quoted here in
# full (never a prefix or a pattern), and it should carry a one-line note saying where it comes
# from. If you cannot state why the literal is not a credential, it does not belong here.
DOC_EXAMPLE_ALLOWLIST = frozenset(
    {
        # A skills/docs slug quoted in write-ups of the original `sk-` false-positive bug. It is a
        # directory name, not a key; it trips the gate because it sits in prose after a space,
        # where no left-boundary guard can help.
        "sk-content-reduction-spec",
    }
)
# Note: home-dir paths are masked in all emitted CONTENT via REDACTIONS (home -> ~). The only
# unredacted absolute path is the functional `transcriptPath` field in the gitignored
# aggregate.json (sub-agents need it); it is never part of the report, so the leak gate
# below targets true secret shapes only, not the home username.


def redact(text):
    """Mask secrets/PII in any string before it is emitted. Safe on non-strings."""
    if not isinstance(text, str):
        text = str(text)
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


# --- line endings ----------------------------------------------------------------------------
# Every file this script writes holds LF line endings and no carriage return at all. Text mode
# turns each LF into CR LF on Windows, and a CR LF already inside a message then reached the file
# as CR CR LF, so a reader that numbers lines as ripgrep and the Read tool do (LF only) and one
# that does not (universal newlines) cited different lines. Normalise the text, and write it with
# newline="\n" so that nothing translates it back.
_CR_LF_RE = re.compile(r"\r\n?")
_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")


def _lf(text):
    """`text` with every CR LF and every lone CR turned into LF."""
    return _CR_LF_RE.sub("\n", text)


def _write_lf(path, text):
    """Write `text` to `path` as UTF-8 with LF line endings, on every OS."""
    Path(path).write_text(_lf(text), encoding="utf-8", newline="\n")


# --- helpers ---------------------------------------------------------------------------------
def is_real_user_text(text):
    if not text or not text.strip():
        return False
    stripped = text.lstrip()
    return not any(stripped.startswith(p) for p in SYSTEM_PREFIXES)


def clean_user_text(text):
    text = re.sub(r"<system-reminder>[\s\S]*?</system-reminder>", "", text)
    text = re.sub(r"<ide_[^>]*>[\s\S]*?</ide_[^>]*>", "", text)
    return text.strip()


def result_text(content):
    """Flatten a tool_result content (string or list of blocks) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if (
                isinstance(b, dict)
                and b.get("type") == "text"
                and isinstance(b.get("text"), str)
            ):
                parts.append(b["text"])
        return "\n".join(parts)
    return ""


# --- operator turns --------------------------------------------------------------------------
# The operator's own words reach a main-session transcript by three carriers, and only structure
# tells them from the text the harness injects on the same channel (skill bodies, task
# notifications, hand-backs, compaction summaries, resume nudges). This is the ONE definition of an
# operator turn: the section of operator turns after the byte cap and the interaction digest's list
# and header all read it, so the three cannot disagree.
#   * a user record the operator typed: origin.kind is "human" and no block is a tool_result;
#   * an attachment record of type queued_command, for a message typed while the model was working
#     (commandMode "prompt", origin.kind "human"). The text is attachment.prompt, never the
#     `rendered` copy of it, which sits in a system-reminder frame;
#   * the question tool's answer: a tool_result whose call was AskUserQuestion, with no is_error and
#     a record-level toolUseResult holding a dict `answers`. The result's own sentence repeats
#     every question, so the answer values are the operator's words and that sentence is not.
# Not carriers: queue-operation and last-prompt records, which only copy text one of the above
# already holds. Not operator flags: promptSource (a prompt a program sent carries it too),
# turnOrigin "human" (compaction summaries carry it) and the wording of an answer (it comes in two
# forms).
# A slash command the operator typed stays with sessions[].slashCommands: its wrapper is dropped
# with the other system-prefixed blocks.
ASK_TOOL = "AskUserQuestion"
ANSWER_SEPARATOR = " | "
# turnOrigin values of prompts a program or the harness sent. Consulted only for a record with no
# origin stamp, which is how a transcript written before the harness stamped one looks.
MACHINE_TURN_ORIGINS = frozenset(
    {"sdk", "system", "peer", "task_notification", "scheduled"}
)


def _record_blocks(content):
    """The blocks of a message content: a list as it is, a plain string as one text block."""
    if isinstance(content, list):
        return content
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return []


def _message_content(obj):
    """The content of a record's message, or None when there is no message or it is not a dict."""
    message = obj.get("message")
    return message.get("content") if isinstance(message, dict) else None


def _typed_text(blocks):
    """The operator's words in a record's text blocks: each block cleaned, a block that is only an
    IDE note dropped, pasted bodies kept, the blocks joined with a newline. Not yet redacted."""
    parts = []
    for b in blocks:
        if (
            isinstance(b, dict)
            and b.get("type") == "text"
            and isinstance(b.get("text"), str)
            and is_real_user_text(b["text"])
        ):
            cleaned = clean_user_text(b["text"])
            if cleaned:
                parts.append(cleaned)
    return "\n".join(parts)


def _is_human_origin(origin):
    return isinstance(origin, dict) and origin.get("kind") == "human"


def _sent_by_operator(obj):
    """What a record's stamps say about who sent it: True for an origin stamp of kind human, or
    for no origin stamp and none of the machine markers (isMeta, isCompactSummary, a turnOrigin
    of a program or the harness). The one stamp rule: operator_turn_text reads it for a user
    record and process_session for a slash command (sessions[].slashCommands[].by), so the two
    cannot disagree. What a caller adds on top (the injected-text prefixes) stays its own."""
    origin = obj.get("origin")
    if origin is not None:
        return _is_human_origin(origin)
    return not (
        obj.get("isMeta")
        or obj.get("isCompactSummary")
        or str(obj.get("turnOrigin")) in MACHINE_TURN_ORIGINS
    )


def _answer_text(obj, blocks, id_to_tool):
    """The answers the operator gave the question tool, or '' for any other tool result. The call
    must have been the question tool AND the record must carry the answers: structure alone would
    admit any tool whose result happens to hold an `answers` dict."""
    result = obj.get("toolUseResult")
    answers = result.get("answers") if isinstance(result, dict) else None
    if not isinstance(answers, dict):
        return ""
    for b in blocks:
        if (
            isinstance(b, dict)
            and b.get("type") == "tool_result"
            and b.get("is_error") is not True
            and isinstance(b.get("tool_use_id"), str)
            and id_to_tool.get(b.get("tool_use_id")) == ASK_TOOL
        ):
            values = [v.strip() for v in answers.values() if isinstance(v, str)]
            return ANSWER_SEPARATOR.join(v for v in values if v)
    return ""


def operator_turn_text(obj, id_to_tool):
    """The operator's own words carried by ONE transcript record, redacted, or '' when the record
    is not an operator turn. `id_to_tool` maps tool_use ids seen so far to their tool names (it
    pairs an answer with its question call). The text is not clipped: callers clip.

    A record that holds a tool_result block is read for that block alone: typed text beside an
    answer in the same record is not an operator turn, and process_session leaves it out of the
    digest as well. No transcript measured so far mixes the two, so this is a stated limit and not
    a handled case."""
    otype = obj.get("type")
    if otype == "attachment":
        att = obj.get("attachment")
        if (
            isinstance(att, dict)
            and att.get("type") == "queued_command"
            and att.get("commandMode") == "prompt"
            and _is_human_origin(att.get("origin"))
        ):
            return redact(_typed_text(_record_blocks(att.get("prompt"))))
        return ""
    if otype != "user":
        return ""
    blocks = _record_blocks(_message_content(obj))
    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks):
        return redact(_answer_text(obj, blocks, id_to_tool))
    if not _sent_by_operator(obj):
        return ""
    text = _typed_text(blocks)
    if obj.get("origin") is not None:
        return redact(text)
    # No origin stamp and no machine marker: the injected-text prefixes still apply (they are all
    # that tells such records apart).
    return redact(text) if _is_human_turn(text) else ""


def iter_operator_turns(jsonl_path):
    """Yield the text of every operator turn of one main-session transcript, in file order.

    The interaction digest and the session identity call this outside main()'s per-file guard, so a
    record of an unexpected shape is read as "not an operator turn" and never raised on. A tool_use
    id is taken only when it is a string: it becomes a dict key, and an id of any other type must
    not stop the run."""
    id_to_tool = {}
    for obj in iter_jsonl(jsonl_path):
        if obj.get("type") == "assistant":
            content = _message_content(obj)
            for b in content if isinstance(content, list) else []:
                if (
                    isinstance(b, dict)
                    and b.get("type") == "tool_use"
                    and isinstance(b.get("id"), str)
                    and b["id"]
                    and b.get("name")
                ):
                    id_to_tool[b["id"]] = b["name"]
            continue
        text = operator_turn_text(obj, id_to_tool)
        if text:
            yield text


# The harness's own sentence when the user refuses a tool call, written at the START of the
# tool_result. What follows it differs by build (a trailing note, "To tell you how to proceed,
# the user said:", an older "provided the following reason"), so only the opening sentence is
# the anchor. It is anchored, never a substring: ripgrep's own usage errors say "rejected the
# pattern, glob, or file type", and any error that merely QUOTES a denial phrase (a log line, a
# commit message) carries it mid-text — a substring match filed both as a permission denial.
# The cancellation sentence ("... doesn't want to take this action right now") is the harness's
# stamp for a cancelled call, not a denial, and is deliberately not matched.
USER_REJECTED_SENTENCE = "The user doesn't want to proceed with this tool use."

# .NET build output counts as a build error, the class a ruff or mypy failure gets: MSBuild's
# "Build FAILED." stamp, its own errors ("error MSB" and four digits) and the C# compiler's
# ("error CS" and four digits, with or without the "file(line,col): " prefix in front). They are
# matched case-sensitively on the raw text and read BEFORE the generic "failed" rule, because the
# stamp itself holds the word "failed": read after it, a failed build that prints the stamp would
# file as a test failure. The dotnet test summary line ("Failed!  - Failed: ...") matches none of
# them and stays a test failure.
DOTNET_BUILD_SIGNATURES = (
    re.compile(r"\bBuild FAILED\."),
    re.compile(r"\berror MSB\d{4}\b"),
    re.compile(r"\berror CS\d{4}\b"),
)

# The `environment` category: a call the harness or a hook refused or stopped, which is no measure
# of the agent: give the rule a home, not an agent-quality count. Three shapes, each named by text
# the harness or the kit's own hook writes, and only where that text OPENS an error record (after
# leading whitespace and the harness's own <tool_use_error> tag): the same words quoted inside a
# failed command, a log or a workflow's failure list keep their ordinary class, and a result that
# is not an error is data. Nothing else moves: a failed shell call opens with "Exit code N"
# whoever failed, so that opening names no shape. Measured on one transcript store (2026-11-09):
#   * sleep-denial: the harness refuses a long sleep put in front of a command, "Blocked: sleep N
#     followed by: <command>" for Bash and "Blocked: Start-Sleep N followed by: ..." for
#     PowerShell, in the tag, and a long sleep with nothing after it, "Blocked: standalone sleep
#     N." and "Blocked: standalone Start-Sleep N." (the store held none of these; the shape is
#     from a live refusal, 2026-11-09). One guard and one remedy, so one shape: two shapes would
#     split one habit's count, and the digest's twice-or-more bar counts per shape. A short sleep
#     runs, so the refusal is matched and never the word.
#   * usage-limit: the harness's limit sentence ("You've hit your 5-hour limit", "... session
#     limit"). It stops a turn as an assistant record marked isApiErrorMessage (is_usage_limit_stop),
#     and it is the shape too when it opens an error tool result.
#   * cd-denial: the kit shell-prefix gate (hooks/gate_shell_prefix.py) denies a move by returning
#     its MOVE text as the whole reason. CD_DENIAL_ANCHOR is that text's opening, and a test loads
#     the hook by path and holds the two equal. Another hook's wording is not encoded here.
ENVIRONMENT_SHAPES = ("sleep-denial", "usage-limit", "cd-denial")
TOOL_USE_ERROR_TAG = "<tool_use_error>"
SLEEP_DENIAL_RE = re.compile(
    r"Blocked: (?:(?:sleep|Start-Sleep) \S+ followed by\b"
    r"|standalone (?:sleep|Start-Sleep) \S+\.)"
)
USAGE_LIMIT_RE = re.compile(r"You['\u2019]ve hit your (?:[\w-]+ ){0,2}limit\b")
CD_DENIAL_ANCHOR = "Do not move the shell's working directory"
# The label a usage-limit stop's sample carries where a tool result's carries its tool.
API_ERROR_SOURCE = "api-error"


def _opening(text):
    """The text an anchor is read against: leading whitespace and the harness's tag dropped."""
    head = text.lstrip()
    if head.startswith(TOOL_USE_ERROR_TAG):
        head = head[len(TOOL_USE_ERROR_TAG) :].lstrip()
    return head


def environment_shape(origin, is_error, text):
    """The environment shape of one tool result ('sleep-denial', 'usage-limit', 'cd-denial'),
    or None. Only an error result has one; the sleep and cd shapes only from a shell tool."""
    if not is_error:
        return None
    head = _opening(text)
    if USAGE_LIMIT_RE.match(head):
        return "usage-limit"
    if origin in SHELL_TOOLS:
        if SLEEP_DENIAL_RE.match(head):
            return "sleep-denial"
        if head.startswith(CD_DENIAL_ANCHOR):
            return "cd-denial"
    return None


def is_usage_limit_stop(obj):
    """True for the record a usage limit leaves: an assistant record the harness marks as an API
    error (isApiErrorMessage) whose text opens with the limit sentence. The agent's own prose that
    quotes the sentence carries no mark, and another API error carries another text."""
    if obj.get("type") != "assistant" or obj.get("isApiErrorMessage") is not True:
        return False
    return USAGE_LIMIT_RE.match(result_text(_message_content(obj)).lstrip()) is not None


def _errors_outside_environment(errors):
    """How many of `errors` (category -> count) are the agent's own: every class but
    `environment`, which a stop or a refusal by the harness or a hook fills."""
    return sum(n for category, n in errors.items() if category != "environment")


def _count_shape(shapes, shape):
    shapes[shape] = shapes.get(shape, 0) + 1


def _shapes_in_order(shapes):
    """A shape count as a plain dict in ENVIRONMENT_SHAPES order, the shapes never seen left out."""
    return {s: shapes[s] for s in ENVIRONMENT_SHAPES if shapes.get(s)}


def classify_error(origin, is_error, text):
    """Return an error category, 'user-rejected', or None. Classifies by ORIGIN tool.

    Content tools are never errors unless is_error is set. Shell tools may also error via a
    non-zero exit code surfaced in the result body. 'user-rejected' is USER_REJECTED_SENTENCE at
    the start of an is_error result and nothing looser; leading whitespace is tolerated because
    a list-of-blocks result joins an empty first block into a leading newline. 'environment' is
    an is_error result that opens with one of the shapes environment_shape names, read before
    every behavioural rule: a refused sleep put in front of a test run is no test failure.
    """
    if is_error and text.lstrip().startswith(USER_REJECTED_SENTENCE):
        return "user-rejected"
    if environment_shape(origin, is_error, text):
        return "environment"

    low = text.lower()
    is_shell = origin in SHELL_TOOLS
    nonzero_exit = bool(re.search(r"exit code:?\s*[1-9]", low))
    if not (is_error or (is_shell and nonzero_exit)):
        return None

    if origin in {"Read", "Edit", "Write"} and (
        "does not exist" in low or "no such file" in low
    ):
        return "path-not-found"
    if origin in {"Edit", "Write"} and (
        "modified since" in low or "not been read" in low or "has been modified" in low
    ):
        return "edit-stale-read"
    if is_shell:
        if (
            re.search(r"\b(ruff|basedpyright|mypy|pyright|syntaxerror)\b", low)
            or "compileerror" in low
            or any(signature.search(text) for signature in DOTNET_BUILD_SIGNATURES)
        ):
            return "build-compile"
        if re.search(r"\b(pytest|test session starts|failed|assertionerror)\b", low):
            return "test-failure"
        return "runtime-exit"
    if origin == "Skill":
        return "skill-blocked"
    # Non-shell catch-all. ("other" in ERROR_CATEGORIES is a reserved/forward-compat bucket and is
    # never produced here — tool-error and runtime-exit are the real catch-alls.)
    return "tool-error"


# A hook that blocks a tool call comes back as an error result that starts with the harness's own
# prefix, "PreToolUse:<Tool> hook error: ", and then whatever the hook wrote. It is anchored at
# the start and counted only on an error result: shell output, a log line or a quoted message
# carries the same words mid-text, and a hook that never answered says "did not respond" instead.
# The count sits BESIDE the error categories (the result keeps its category). A hook that denies by
# JSON returns only its own reason, with no prefix, and nothing else in the record names a hook:
# the harness's denial stamp is shared with don't-ask mode, built-in safety checks and protected
# paths, so that form is deliberately not counted. extractor-output-schema.md says so too.
# (Two literals, so that no colon sits right before a backslash: the asset hygiene scan reads
# letter-colon-backslash-letter as a drive path.)
HOOK_DENIAL_RE = re.compile("PreToolUse:" r"\S+ hook error: ")


def is_hook_denial(is_error, text):
    """True for an error result carrying the harness's hook-error prefix at its start."""
    return bool(is_error) and HOOK_DENIAL_RE.match(text.lstrip()) is not None


def tool_input_summary(name, inp):
    """One-line, redacted summary of a tool_use input for the readable transcript."""
    if not isinstance(inp, dict):
        return ""
    if name in {"Read", "Edit", "Write", "NotebookEdit"}:
        s = inp.get("file_path", "")
    elif name in SHELL_TOOLS:
        s = inp.get("command", "")
    elif name in {"Grep", "Glob"}:
        s = inp.get("pattern", "")
    elif name == "Skill":
        s = inp.get("skill", "")
    elif name == "Task" or name == "Agent":
        s = inp.get("description", "")
    elif name == "TodoWrite":
        s = f"{len(inp.get('todos', []))} todos"
    else:
        s = inp.get("description") or inp.get("prompt") or inp.get("query") or ""
    return redact(_LINE_BREAK_RE.sub(" ", str(s)))[:100]


# --- per-session processing ------------------------------------------------------------------
def iter_jsonl(path, left_out=None):
    """Yield parsed objects from a JSONL file; skip malformed lines without aborting.

    Each event is yielded once. A session that was resumed or compacted can write earlier events
    into its transcript a second time: the repeat has the same top-level `uuid` (and the same
    message, parent and timestamp) as the original but a re-stamped slug and, usually, a shorter
    toolUseResult, so it is not the same line byte for byte, and counted as written every tool call
    in the replayed span counts twice. The key is the `uuid` alone, remembered per call, and the
    FIRST occurrence is the one kept. Other keys fail on measured transcripts: one API message is
    written as several lines that each carry a uuid of their own (a message-id key loses events),
    two real turns can read alike (a text key folds them), and a whole-line key never matches a
    repeat while it folds the state lines that have no uuid. A line whose uuid is absent, empty or
    not a string is always yielded: state lines and the rows of an older transcript carry none.
    When `left_out` is a list, the uuid of each repeat that was left out is appended to it, so that
    the caller can say that it happened."""
    seen = set()
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, json.JSONDecodeError):
                    continue
                if not isinstance(obj, dict):
                    continue  # valid-but-non-object lines (bare strings/numbers)
                uid = obj.get("uuid")
                if isinstance(uid, str) and uid:
                    if uid in seen:
                        if left_out is not None:
                            left_out.append(uid)
                        continue
                    seen.add(uid)
                yield obj
    except OSError as exc:
        print(f"  ! cannot read {path}: {exc}", file=sys.stderr)


def process_session(jsonl_path, sessions_dir, replays=None):
    """Walk one main-session transcript and the transcripts of its helpers.

    `replays`, when given, is a dict that receives {session id: number of repeated events left out}
    for a session that had any (see iter_jsonl; a helper's repeats count for the session that ran
    it). The caller reports the number: it is not part of the returned session."""
    sid = jsonl_path.stem
    sess = {
        "sessionId": sid,
        "title": None,
        "gitBranch": None,
        "startTime": None,
        "endTime": None,
        "counts": {
            "userMsgs": 0,
            "assistantMsgs": 0,
            "toolUse": 0,
            "toolResult": 0,
            "thinking": 0,
        },
        "transcriptBytes": 0,
        "toolsUsed": defaultdict(int),
        "errorsByCategory": defaultdict(int),
        "behavior": {
            "reReads": [],
            "repeatedCommands": [],
            "buildTestLoops": [],
            "staleReadEdits": 0,
        },
        "skillInvocations": [],
        "askUserQuestions": [],
        "subAgents": {
            "count": 0,
            "bytes": 0,
            "msgs": 0,
            "agents": [],
            "errorsByCategory": {},
            "agentsWithErrors": 0,
            "errorSamples": {},
            "transcriptsEmitted": 0,
            "errorAgentsNotEmitted": 0,
            "highSignal": [],
            "environmentShapes": {},  # v5: environment shape -> count, over the helpers
            "workflowAgents": 0,  # v5: of `count`, the helpers a Workflow run started
        },
        "transcriptPath": None,
        "backtrackingMarkers": 0,
        "slashCommands": [],
        "models": defaultdict(int),
        "compactions": 0,
        "userRejected": 0,  # every user-rejected result; `user_rejected` below is a capped sample
        "hookDenials": 0,  # every hook-blocked result; `hook_denials` below is a capped sample
        "environmentShapes": {},  # v5: environment shape -> count; the category holds the total
    }
    # cross-session error samples collected by the caller; here we collect locally then return
    local_errors = defaultdict(list)  # category -> [redacted sample]
    user_rejected = []  # [redacted sample], capped at SAMPLES_PER_CATEGORY — NOT the count
    hook_denials = []  # [redacted sample], capped at SAMPLES_PER_CATEGORY — NOT the count

    id_to_tool = {}
    skill_ids = {}  # tool_use_id -> skill name
    reads = defaultdict(int)
    cmds = defaultdict(int)
    transcript = []
    transcript_bytes = 0
    truncated = False
    operator_tail = []  # operator turns the byte cap cut off: kept outside it, in a section
    left_out = []  # uuids of the repeated events iter_jsonl dropped, here and in the helpers

    def emit(line):
        """Add a line to the capped transcript; False when the cap kept it out."""
        nonlocal transcript_bytes, truncated
        if truncated:
            return False
        line = _lf(line)
        b = len(line.encode("utf-8", "replace")) + 1
        if transcript_bytes + b > TRANSCRIPT_BYTE_CAP:
            transcript.append("\n[...transcript truncated at 120 KB...]")
            truncated = True
            return False
        transcript.append(line)
        transcript_bytes += b
        return True

    def emit_operator(text):
        """An operator turn goes where it happened; one the cap has already cut off is kept in
        `operator_tail` instead, so the byte cap never costs the operator's own words."""
        line = f"USER: {text[:PER_MESSAGE_TEXT_CAP]}"
        if not emit(line):
            operator_tail.append(_lf(line))

    for obj in iter_jsonl(jsonl_path, left_out):
        otype = obj.get("type")
        ts = obj.get("timestamp")
        if ts:
            if not sess["startTime"] or ts < sess["startTime"]:
                sess["startTime"] = ts
            if not sess["endTime"] or ts > sess["endTime"]:
                sess["endTime"] = ts
        if obj.get("gitBranch") and not sess["gitBranch"]:
            sess["gitBranch"] = obj["gitBranch"]
        if otype == "ai-title":
            sess["title"] = obj.get("aiTitle")
            continue
        if otype == "system" and obj.get("subtype") == "compact_boundary":
            # context compaction event ({"type":"system","subtype":"compact_boundary",
            # "compactMetadata":…}) — a friction signal (v4, C-4b)
            sess["compactions"] += 1
            emit("  [context compacted]")
            continue

        msg = obj.get("message") or {}
        content = msg.get("content")

        if otype == "assistant":
            if not isinstance(content, list):
                continue
            sess["counts"]["assistantMsgs"] += 1
            if isinstance(msg.get("model"), str) and msg["model"]:
                sess["models"][msg["model"]] += 1
            if is_usage_limit_stop(obj):
                sess["errorsByCategory"]["environment"] += 1
                _count_shape(sess["environmentShapes"], "usage-limit")
                if len(local_errors["environment"]) < SAMPLES_PER_CATEGORY:
                    local_errors["environment"].append(
                        f"[{sid[:8]}/{API_ERROR_SOURCE}] {redact(result_text(content))[:160]}"
                    )
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and b.get("text", "").strip():
                    emit(
                        f"ASSISTANT: {redact(b['text'].strip())[:PER_MESSAGE_TEXT_CAP]}"
                    )
                elif bt == "thinking":
                    think = b.get("thinking", "") or ""
                    sess["counts"]["thinking"] += 1
                    sess["backtrackingMarkers"] += len(
                        re.findall(
                            r"\b(wait|actually|let me reconsider|on second thought)\b",
                            think,
                            re.I,
                        )
                    )
                    emit(f"  [thinking {len(think)} chars]")
                elif bt == "tool_use":
                    name = b.get("name", "?")
                    sess["counts"]["toolUse"] += 1
                    sess["toolsUsed"][name] += 1
                    tid = b.get("id")
                    if tid and name:
                        id_to_tool[tid] = name
                    inp = b.get("input") or {}
                    if name == "Read" and inp.get("file_path"):
                        reads[inp["file_path"]] += 1
                    elif name in SHELL_TOOLS and inp.get("command"):
                        cmds[inp["command"].strip()] += 1
                    elif name == "Skill" and tid:
                        skill_ids[tid] = inp.get("skill", "?")
                    elif name == "AskUserQuestion":
                        for q in inp.get("questions") or []:
                            if isinstance(q, dict) and q.get("question"):
                                sess["askUserQuestions"].append(
                                    redact(q["question"])[:300]
                                )
                    emit(f"  [{name}] {tool_input_summary(name, inp)}")
            continue

        if otype == "user":
            # user entries carry EITHER real user text OR tool_result blocks (or both).
            blocks = (
                content
                if isinstance(content, list)
                else (
                    [{"type": "text", "text": content}]
                    if isinstance(content, str)
                    else []
                )
            )
            operator = operator_turn_text(obj, id_to_tool)
            had_user_text = False
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and is_real_user_text(b.get("text", "")):
                    cleaned = clean_user_text(b["text"])
                    if cleaned:
                        had_user_text = True
                        if not operator:  # injected text rides along as it always did
                            emit(f"USER: {redact(cleaned)[:PER_MESSAGE_TEXT_CAP]}")
                elif bt == "text":
                    # v4 (C-2): user-typed slash invocations surface as <command-name>
                    # pseudo-user messages (filtered from user text; still not a userMsg).
                    cm = COMMAND_NAME_RE.search(b.get("text", ""))
                    if cm and len(sess["slashCommands"]) < SLASH_COMMANDS_CAP:
                        am = COMMAND_ARGS_RE.search(b.get("text", ""))
                        args = redact(am.group(1).strip())[:200] if am else ""
                        # v5: who typed it, by the stamps an operator turn is judged by
                        by = "operator" if _sent_by_operator(obj) else "harness"
                        sess["slashCommands"].append(
                            {"command": cm.group(1), "args": args, "by": by}
                        )
                        emit(f"  [slash] /{cm.group(1)} {args}".rstrip())
                elif bt == "tool_result":
                    sess["counts"]["toolResult"] += 1
                    origin = id_to_tool.get(b.get("tool_use_id"), "<unknown>")
                    is_err = b.get("is_error") is True
                    txt = result_text(b.get("content"))
                    cat = classify_error(origin, is_err, txt)
                    if is_hook_denial(is_err, txt):
                        sess["hookDenials"] += 1
                        if len(hook_denials) < SAMPLES_PER_CATEGORY:
                            hook_denials.append(
                                f"[{sid[:8]}/{origin}] {redact(txt)[:160]}"
                            )
                    if cat == "user-rejected":
                        sess["userRejected"] += 1
                        if len(user_rejected) < SAMPLES_PER_CATEGORY:
                            user_rejected.append(
                                f"[{sid[:8]}/{origin}] {redact(txt)[:160]}"
                            )
                    elif cat:
                        sess["errorsByCategory"][cat] += 1
                        if cat == "environment":
                            _count_shape(
                                sess["environmentShapes"],
                                environment_shape(origin, is_err, txt),
                            )
                        if len(local_errors[cat]) < SAMPLES_PER_CATEGORY:
                            local_errors[cat].append(
                                f"[{sid[:8]}/{origin}] {redact(txt)[:160]}"
                            )
                        if cat == "edit-stale-read":
                            sess["behavior"]["staleReadEdits"] += 1
                    # blocked skill: a Skill result with is_error
                    if b.get("tool_use_id") in skill_ids:
                        sess["skillInvocations"].append(
                            {"skill": skill_ids[b["tool_use_id"]], "blocked": is_err}
                        )
                    status = "ok" if not cat else f"ERROR({cat}): {redact(txt)[:120]}"
                    emit(f"    -> {status}")
            if operator:
                emit_operator(operator)
            if had_user_text:
                sess["counts"]["userMsgs"] += 1
            continue

        if otype == "attachment":
            # a message the operator typed while the model was working: not a user record, so
            # not a userMsg either, but the operator's words all the same
            operator = operator_turn_text(obj, id_to_tool)
            if operator:
                emit_operator(operator)
            continue
        # other entry types (last-prompt, queue-operation, file-history-snapshot, mode) are
        # intentionally ignored for behavioral analysis.

    # behavioral aggregates
    sess["behavior"]["reReads"] = [
        {"file": redact(f), "count": n}
        for f, n in sorted(reads.items(), key=lambda x: -x[1])
        if n >= RE_READ_THRESHOLD
    ]
    rep = [
        {"cmd": redact(c)[:120], "count": n}
        for c, n in sorted(cmds.items(), key=lambda x: -x[1])
        if n >= REPEAT_CMD_THRESHOLD
    ]
    sess["behavior"]["repeatedCommands"] = rep
    sess["behavior"]["buildTestLoops"] = [
        r for r in rep if TEST_BUILD_RE.search(r["cmd"])
    ]

    # sub-agents (nested per parent session): aggregate metrics + an error taxonomy, and emit
    # redacted transcripts for the high-signal ones so they can be deep-dived without raw .jsonl.
    walk_subagents(jsonl_path.parent / sid, sess, sessions_dir, left_out)
    if replays is not None and left_out:
        replays[sid] = len(left_out)

    # finalize types
    sess["toolsUsed"] = dict(sess["toolsUsed"])
    sess["errorsByCategory"] = dict(sess["errorsByCategory"])
    sess["models"] = dict(sess["models"])
    sess["environmentShapes"] = _shapes_in_order(sess["environmentShapes"])

    # write per-session transcript
    if sess["counts"]["userMsgs"] > 0:
        header = f"# Session {sid}\nTitle: {redact(sess['title'] or '(none)')}\nBranch: {sess['gitBranch']}\n{sess['startTime']} -> {sess['endTime']}\n\n"
        body = header + "\n".join(transcript)
        if operator_tail:
            # The rule line ends the USER block before it for the corrections sweep, which would
            # otherwise absorb the section's title line into that candidate. A blank line precedes
            # the rule so the section reads apart from the truncation marker above it.
            body += (
                "\n\n"
                + OPERATOR_SECTION_RULE.format(n=len(operator_tail))
                + "\n"
                + "\n".join(operator_tail)
            )
        body = _lf(body)
        out = sessions_dir / f"{sid}.md"
        _write_lf(out, body)
        sess["transcriptPath"] = str(out.resolve())
        sess["transcriptBytes"] = len(body.encode("utf-8", "replace"))

    return sess, local_errors, user_rejected, hook_denials


def render_subagent(jf, left_out=None, shapes=None):
    """Parse one sub-agent transcript .jsonl → (redacted_text, msgs, errorsByCategory, samples).

    Mirrors process_session's message walk but lighter: no behavior metrics, just the readable
    redacted narrative + an error taxonomy (same classify_error, by ORIGIN tool, and a usage-limit
    stop counted as `environment` as the main walk counts it). `samples` is a list of (category,
    redacted_sample) tuples. Errors inside sub-agents were previously invisible.
    `left_out` is the list iter_jsonl appends the uuid of each repeated event to. `shapes`, when
    given, is a dict that receives {environment shape: count} for this transcript.
    """
    id_to_tool = {}
    lines = []
    nbytes = 0
    truncated = False
    msgs = 0
    errs = defaultdict(int)
    samples = []

    def emit(line):
        nonlocal nbytes, truncated
        if truncated:
            return
        line = _lf(line)
        b = len(line.encode("utf-8", "replace")) + 1
        if nbytes + b > TRANSCRIPT_BYTE_CAP:
            lines.append("\n[...sub-agent transcript truncated at 120 KB...]")
            truncated = True
            return
        lines.append(line)
        nbytes += b

    for obj in iter_jsonl(jf, left_out):
        otype = obj.get("type")
        if otype in ("user", "assistant"):
            msgs += 1
        content = (obj.get("message") or {}).get("content")
        if otype == "assistant":
            if not isinstance(content, list):
                continue
            if is_usage_limit_stop(obj):
                errs["environment"] += 1
                if shapes is not None:
                    _count_shape(shapes, "usage-limit")
                if len(samples) < SAMPLES_PER_CATEGORY * 2:
                    samples.append(
                        (
                            "environment",
                            f"{API_ERROR_SOURCE}: {redact(result_text(content))[:140]}",
                        )
                    )
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and b.get("text", "").strip():
                    emit(
                        f"ASSISTANT: {redact(b['text'].strip())[:PER_MESSAGE_TEXT_CAP]}"
                    )
                elif bt == "thinking":
                    emit("  [thinking]")
                elif bt == "tool_use":
                    name = b.get("name", "?")
                    tid = b.get("id")
                    if tid and name:
                        id_to_tool[tid] = name
                    emit(f"  [{name}] {tool_input_summary(name, b.get('input') or {})}")
        elif otype == "user":
            blocks = (
                content
                if isinstance(content, list)
                else (
                    [{"type": "text", "text": content}]
                    if isinstance(content, str)
                    else []
                )
            )
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and is_real_user_text(b.get("text", "")):
                    cleaned = clean_user_text(b["text"])
                    if cleaned:
                        emit(f"USER: {redact(cleaned)[:PER_MESSAGE_TEXT_CAP]}")
                elif bt == "tool_result":
                    origin = id_to_tool.get(b.get("tool_use_id"), "<unknown>")
                    is_err = b.get("is_error") is True
                    txt = result_text(b.get("content"))
                    cat = classify_error(origin, is_err, txt)
                    if cat and cat != "user-rejected":
                        errs[cat] += 1
                        if cat == "environment" and shapes is not None:
                            _count_shape(shapes, environment_shape(origin, is_err, txt))
                        if len(samples) < SAMPLES_PER_CATEGORY * 2:
                            samples.append((cat, f"{origin}: {redact(txt)[:140]}"))
                    status = "ok" if not cat else f"ERROR({cat}): {redact(txt)[:120]}"
                    emit(f"    -> {status}")
    return "\n".join(lines), msgs, dict(errs), samples


def walk_subagents(session_dir, sess, sessions_dir, left_out=None):
    """Aggregate nested sub-agent transcripts (<id>/subagents/agent-*.jsonl and
    .../workflows/wf_*/agent-*.jsonl: see SUBAGENT_GLOB), build a per-session sub-agent error
    taxonomy, and emit redacted transcripts for the HIGH-SIGNAL ones (any error, or the largest
    few) so they can be deep-dived without ever reading raw .jsonl. A workflow run's journal.jsonl
    is an event log, not a transcript, and is not counted. Uses agent-*.meta.json sidecars for
    type/goal (an agent without one is typed "?"). Mutates `sess`. `left_out` collects the repeated
    events the transcripts held (see iter_jsonl)."""
    sub_root = session_dir / "subagents"
    if not sub_root.is_dir():
        return
    sid8 = sess["sessionId"][:8]
    parsed = []
    shapes = {}  # environment shape -> count, over every helper of the session
    for jf in sorted(sub_root.rglob(SUBAGENT_GLOB)):
        sess["subAgents"]["count"] += 1
        if jf.relative_to(sub_root).parts[0] == SUBAGENT_WORKFLOWS_DIR:
            sess["subAgents"]["workflowAgents"] += 1
        size = 0
        with contextlib.suppress(OSError):
            size = jf.stat().st_size
        sess["subAgents"]["bytes"] += size
        meta = jf.with_suffix(".meta.json")  # agent-X.jsonl -> agent-X.meta.json
        atype, goal = None, None
        if meta.is_file():  # sidecar is authoritative for agentType + description
            with contextlib.suppress(OSError, ValueError):
                m = json.loads(meta.read_text(encoding="utf-8", errors="replace"))
                atype = m.get("agentType")
                goal = m.get("description")
        text, msgs, errs, samples = render_subagent(jf, left_out, shapes)
        sess["subAgents"]["msgs"] += msgs
        if len(sess["subAgents"]["agents"]) < 30:
            sess["subAgents"]["agents"].append(
                {"type": atype or "?", "goal": redact(goal or "?")[:120]}
            )
        parsed.append(
            {
                "rel": str(jf.relative_to(sub_root)),
                "type": atype or "?",
                "goal": redact(goal or "?")[:120],
                "bytes": size,
                "msgs": msgs,
                "errs": errs,
                "samples": samples,
                "text": text,
            }
        )

    # roll up the session-level sub-agent error taxonomy
    agg_errs = defaultdict(int)
    sample_by_cat = defaultdict(list)
    agents_with_errors = 0
    for p in parsed:
        if p["errs"]:
            agents_with_errors += 1
            for c, n in p["errs"].items():
                agg_errs[c] += n
            for c, txt in p["samples"]:
                if len(sample_by_cat[c]) < SAMPLES_PER_CATEGORY:
                    sample_by_cat[c].append(f"[{sid8}/sub] {txt}")
    sess["subAgents"]["errorsByCategory"] = dict(agg_errs)
    sess["subAgents"]["agentsWithErrors"] = agents_with_errors
    sess["subAgents"]["errorSamples"] = dict(sample_by_cat)
    sess["subAgents"]["environmentShapes"] = _shapes_in_order(shapes)

    # select high-signal transcripts to emit: every error-bearing agent + the top-N by bytes,
    # de-duplicated and capped (bounded so a huge fan-out can't explode the output). An agent
    # with an error outside `environment` goes before one whose only errors are stops and
    # refusals, which are no measure of the agent: a wave the usage limit ended would fill the
    # cap with the agents it stopped, in path order, and leave out the one that failed.
    top_bytes = sorted(parsed, key=lambda p: -p["bytes"])[:SUBAGENT_TOP_BYTES_EMIT]
    own = [p for p in parsed if _errors_outside_environment(p["errs"])]
    stopped = [
        p for p in parsed if p["errs"] and not _errors_outside_environment(p["errs"])
    ]
    candidates = own + stopped + [p for p in top_bytes if not p["errs"]]
    seen, ordered = set(), []
    for p in candidates:
        if p["rel"] in seen:
            continue
        seen.add(p["rel"])
        ordered.append(p)
    ordered = ordered[:MAX_SUBAGENT_EMIT_PER_SESSION]
    # v4 (C-8): error-bearing agents beyond the emission cap are taxonomy-only; record how many,
    # so "scanned via taxonomy only" is reportable (not derivable from agentsWithErrors −
    # transcriptsEmitted, since emitted also includes top-by-bytes non-error agents).
    emitted_rels = {p["rel"] for p in ordered}
    sess["subAgents"]["errorAgentsNotEmitted"] = sum(
        1 for p in parsed if p["errs"] and p["rel"] not in emitted_rels
    )
    if ordered:
        sub_dir = sessions_dir / "sub" / sess["sessionId"]
        sub_dir.mkdir(parents=True, exist_ok=True)
        for p in ordered:
            safe = (
                re.sub(r"\.jsonl$", "", p["rel"]).replace("\\", "__").replace("/", "__")
                + ".md"
            )
            # `bytes` is the RAW source transcript size; what lands on disk here is a
            # redacted, size-capped digest — routinely ~2% of it. Both numbers are stated
            # explicitly because the old header showed only the raw one under the bare label
            # "bytes", and 4 of 6 analysts in the 2026-08-01 retro budgeted their reads for a
            # 400-700 KB file that was actually 10-13 KB.
            body_bytes = len(p["text"].encode("utf-8", "replace"))
            header = (
                f"# Sub-agent {redact(safe)} (parent {sid8})\n"
                f"Type: {p['type']}\nGoal: {p['goal']}\n"
                f"raw source bytes: {p['bytes']}  |  THIS FILE (redacted digest): ~{body_bytes}"
                f"  msgs: {p['msgs']}  errors: {p['errs'] or 'none'}\n\n"
            )
            outp = sub_dir / safe
            _write_lf(outp, header + p["text"])
            sess["subAgents"]["highSignal"].append(
                {
                    "file": safe,
                    "type": p["type"],
                    "goal": p["goal"],
                    "bytes": p["bytes"],
                    "emittedBytes": outp.stat().st_size,
                    "msgs": p["msgs"],
                    "errorsByCategory": p["errs"],
                    "transcriptPath": str(outp.resolve()),
                }
            )
    sess["subAgents"]["transcriptsEmitted"] = len(sess["subAgents"]["highSignal"])


# --- session-dir derivation -------------------------------------------------------------------
# Claude Code stores a project's sessions under ~/.claude/projects/<encoded>, where <encoded> is the
# project's ABSOLUTE path with every "/", "\" and ":" replaced by "-". That name is machine-specific
# (drive letter, username, clone location all differ per engineer), so it MUST be derived at runtime,
# never hardcoded — a hardcoded path is portable to exactly one person.
# Not measured: whether Claude Code replaces other characters too (a dot, an underscore, a space).
# If it does, a working directory whose path holds one is not found by this encoding, and the
# derivation refuses and asks for the session dir, as it does for every directory it cannot match.
def _encode_repo_path(root):
    """Encode an absolute repo path the way Claude Code names its ~/.claude/projects/<dir>."""
    return re.sub(r"[/\\:]", "-", str(root))


def _find_session_dir(repo_root, projects_base):
    """Return the projects/<encoded> dir for repo_root, or None.

    Tries an exact match first, then a case-insensitive scan so a Windows drive-letter casing diff
    (Path.resolve() yields 'C:\\…' but the on-disk dir is 'c--…') still resolves.
    """
    enc = _encode_repo_path(repo_root)
    cand = projects_base / enc
    if cand.is_dir():
        return cand
    if projects_base.is_dir():
        for d in projects_base.iterdir():
            if d.is_dir() and d.name.casefold() == enc.casefold():
                return d
    return None


def _is_same_dir(a, b):
    """True when two paths name the same directory (case, links and short names aside)."""
    try:
        return a.samefile(b)
    except OSError:  # one of them does not exist: compare the paths as written
        return a == b


def _derive_session_dir(cwd=None, home=None):
    """Derive the Claude session dir of the project this run was started in, from the WORKING
    DIRECTORY.

    The working directory must be the project root (the directory Claude Code was launched in) and
    must have a session folder of its own under ~/.claude/projects/, found by _find_session_dir:
    the folder is the proof that Claude Code ran there. The script's own location is not used. An
    installed plugin sits under the home directory's .claude/, so a walk up from it ends at the home
    directory and either finds no folder or finds the home directory's, which holds everything ever
    started there and is not one project's corpus. Refused, with exit status 1 and a message that
    asks for the session dir as the first argument, and never guessed:
      * the home directory, even when a session folder for it exists;
      * a directory with no folder of its own: below the project root, beside it, a launch
        directory that is not the project root, or a folder Claude Code never ran in.
    CLAUDE_PROJECT_DIR is not set in tool calls, so it cannot stand in for the working directory.
    `cwd` and `home` default to the process's own; they exist so that a test patches neither.
    """
    cwd = Path.cwd() if cwd is None else Path(cwd)
    home = Path.home() if home is None else Path(home)
    projects_base = home / ".claude" / "projects"
    is_home = _is_same_dir(cwd, home)
    found = None if is_home else _find_session_dir(cwd, projects_base)
    if found is None:
        avail = (
            sorted(p.name for p in projects_base.iterdir() if p.is_dir())
            if projects_base.is_dir()
            else []
        )
        why = (
            "it is the home directory, and a session folder for the home directory is never "
            "used silently"
            if is_home
            else "no session folder is named for it (looked for "
            f"{projects_base / _encode_repo_path(cwd)}); it must be the project root, the "
            "directory Claude Code was launched in"
        )
        raise SystemExit(
            "ERROR: could not derive the Claude session dir.\n"
            f"  working dir: {cwd}\n"
            f"  why:         {why}\n"
            f"  available:   {avail or '(none)'}\n"
            "  Pass the session dir explicitly as the first argument."
        )
    return found


# --- date pre-scan (v4, C-3) ------------------------------------------------------------------
def prescan_date_range(jsonl_path):
    """Cheaply estimate a session's (first_ts, last_ts) without a full parse.

    Reads the first PRESCAN_HEAD_LINES lines and the last PRESCAN_TAIL_BYTES bytes, extracting
    ISO timestamps by regex. Returns (first, last) — either may be None when undeterminable
    (the caller must then FULL-PARSE the session; never silently skip). JSONL lines are appended
    chronologically, but to be safe we take min(head matches) and max(tail matches).
    """
    head_ts, tail_ts = [], []
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as fh:
            for _ in range(PRESCAN_HEAD_LINES):
                line = fh.readline()
                if not line:
                    break
                head_ts.extend(TIMESTAMP_RE.findall(line))
                if head_ts:
                    break
        size = jsonl_path.stat().st_size
        with open(jsonl_path, "rb") as fh:
            fh.seek(max(0, size - PRESCAN_TAIL_BYTES))
            tail = fh.read().decode("utf-8", errors="replace")
        tail_ts = TIMESTAMP_RE.findall(tail)
    except OSError:
        return None, None
    return (min(head_ts) if head_ts else None), (max(tail_ts) if tail_ts else None)


# --- deep-dive candidate selection (v4, C-1) ---------------------------------------------------
def select_deep_dive(sessions):
    """Deterministic Phase-3 selection: qualify by toolUse/userMsgs, rank, cap at DEEP_DIVE_CAP."""
    qualifiers = [
        s
        for s in sessions
        if s["counts"]["toolUse"] >= DEEP_DIVE_TOOLUSE_MIN
        or s["counts"]["userMsgs"] >= DEEP_DIVE_USERMSGS_MIN
    ]
    ranked = sorted(
        qualifiers,
        key=lambda s: (-s["counts"]["toolUse"], -s["transcriptBytes"], s["sessionId"]),
    )
    selected = [
        {
            "sessionId": s["sessionId"],
            "transcriptPath": s["transcriptPath"],
            "toolUse": s["counts"]["toolUse"],
            "userMsgs": s["counts"]["userMsgs"],
            "transcriptBytes": s["transcriptBytes"],
        }
        for s in ranked[:DEEP_DIVE_CAP]
    ]
    over_cap = [
        {"sessionId": s["sessionId"], "toolUse": s["counts"]["toolUse"]}
        for s in ranked[DEEP_DIVE_CAP:]
    ]
    return {
        "selectionRule": (
            f"toolUse>={DEEP_DIVE_TOOLUSE_MIN} OR userMsgs>={DEEP_DIVE_USERMSGS_MIN}; "
            f"rank toolUse desc, transcriptBytes desc, sessionId; top {DEEP_DIVE_CAP}"
        ),
        "selected": selected,
        "overCap": over_cap,
    }


def select_subagent_deep_dive(sessions):
    """Deterministic Phase-3b selection over emitted high-signal sub-agent transcripts.

    The rank reads the errors outside `environment` first, so an agent the harness stopped or
    refused, however often, follows one with an error of its own; then errorCount (every class),
    bytes and file, which is the whole rank when no agent has an `environment` error.
    Candidates are taken in rank order with a soft limit per parent session: a parent's
    candidates past SUBAGENT_DEEPDIVE_PER_PARENT_CAP wait while any other candidate remains, and
    a slot still free after that pass is filled from the ones that waited, in rank order. Both
    lists come out in rank order, so the limit decides who is picked, not how the lists read.
    """
    pool, own = [], []  # each candidate, and its count of errors outside `environment`
    for s in sessions:
        for hs in s["subAgents"].get("highSignal", []):
            errors = hs.get("errorsByCategory", {})
            own.append(_errors_outside_environment(errors))
            pool.append(
                {
                    "parentSessionId": s["sessionId"],
                    "file": hs["file"],
                    "transcriptPath": hs["transcriptPath"],
                    "errorCount": sum(errors.values()),
                    # `bytes` = raw source size (also the rank key, unchanged);
                    # `emittedBytes` = what the analyst will actually read. Both are carried
                    # so a Phase-3b spawn prompt can state the real read budget.
                    "bytes": hs.get("bytes", 0),
                    "emittedBytes": hs.get("emittedBytes", 0),
                }
            )
    order = sorted(
        range(len(pool)),
        key=lambda i: (
            -own[i],
            -pool[i]["errorCount"],
            -pool[i]["bytes"],
            pool[i]["file"],
        ),
    )
    ranked = [pool[i] for i in order]
    taken_per_parent = defaultdict(int)
    picked, waiting = [], []  # positions in `ranked`
    for position, p in enumerate(ranked):
        if len(picked) == SUBAGENT_DEEPDIVE_CAP:
            break
        parent = p["parentSessionId"]
        if taken_per_parent[parent] >= SUBAGENT_DEEPDIVE_PER_PARENT_CAP:
            waiting.append(position)
        else:
            taken_per_parent[parent] += 1
            picked.append(position)
    picked += waiting[: SUBAGENT_DEEPDIVE_CAP - len(picked)]
    chosen = set(picked)
    return {
        "selectionRule": (
            f"all emitted high-signal sub-agents; rank errors outside environment desc, "
            f"errorCount desc, bytes desc, file; "
            f"top {SUBAGENT_DEEPDIVE_CAP}; at most {SUBAGENT_DEEPDIVE_PER_PARENT_CAP} per "
            f"parent session while others remain"
        ),
        "selected": [p for position, p in enumerate(ranked) if position in chosen],
        "overCap": [
            {k: p[k] for k in ("parentSessionId", "file", "errorCount")}
            for position, p in enumerate(ranked)
            if position not in chosen
        ],
    }


# --- main ------------------------------------------------------------------------------------
def check_file(path, unreadable_is_leak=True):
    """Run LEAK_PATTERNS over one file (v4, C-7 — the Phase-6 report-privacy gate).

    Same code path as the --self-check artifact gate. Returns a list of leak descriptions.
    The CLI gate treats an unreadable target as a failure (fail-closed); self_check keeps its
    historical skip-on-OSError behavior via unreadable_is_leak=False.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"{path}: unreadable ({exc})"] if unreadable_is_leak else []
    leaks = []
    for pat in LEAK_PATTERNS:
        # finditer, not search: `search` stops at the first hit, so a single allow-listed
        # documentation example at the top of a file would mask a real key further down.
        for m in pat.finditer(text):
            hit = m.group(0)
            if hit in DOC_EXAMPLE_ALLOWLIST:
                continue
            leaks.append(
                f"{Path(path).name}: matched /{pat.pattern[:40]}/ -> {hit[:30]}"
            )
            break  # one finding per pattern is enough to fail the gate
    return leaks


def self_check(output_dir):
    """Grep emitted artifacts for high-confidence secret shapes.

    Returns `(leaks, files_scanned)`. The count is not decoration: a bare "0 leaks" cannot be
    distinguished from a gate that scanned nothing — an empty output dir, a `sessions/` tree that
    never materialised, or a path list that silently missed every emitted file all print exactly
    the same clean result. Callers must report the denominator beside the zero.
    """
    leaks = []
    scanned = 0
    for path in [
        output_dir / "aggregate.json",
        # The interaction digest quotes USER MESSAGES verbatim, so it is the highest-risk
        # artifact this script emits and must never be outside the gate. Any new emitted file
        # belongs in this list — omission here is silent (the run still prints PASSED).
        output_dir / "interaction-digest.md",
        *(
            (output_dir / "sessions").rglob(
                "*.md"
            )  # rglob → also scans emitted sub-agent dirs
            if (output_dir / "sessions").is_dir()
            else []
        ),
    ]:
        if path.is_file():
            scanned += 1
            leaks.extend(check_file(path, unreadable_is_leak=False))
    return leaks, scanned


# --- session-scoped interaction digest -------------------------------------------------------
# `task-learnings` fires once per task and needs ONE session measured, not the 14-day corpus the
# retrospective walks. Two rules live HERE rather than in the calling skill, because prose in a
# SKILL.md cannot enforce them:
#
#   * Ambiguous "current session" FAILS CLOSED (exit 4). This checkout routinely runs parallel
#     sessions, so newest-mtime alone can silently select somebody ELSE's transcript — and the
#     resulting learnings entry would be confidently about work this session never did.
#   * The re-read threshold is a PARAMETER with a measured default, not a magic number.
#
# Threshold provenance (measured 2026-08-14, 90 sessions / 85 substantial): a re-read count of
# exactly 3 is the MODE (63 of 137 occurrences, 46%) and is most likely AGENTS.md-mandated
# read->edit->re-read COMPLIANCE, not thrash — the extractor never records a count below 3, so a
# ">=2 occurrences" filter is vacuous here. Session yield by threshold: 73% @>=3, 54% @>=4,
# 42% @>=5, 31% @>=6, 18% @>=8, 8% @>=10. The data localizes the honest cut to 4-8 and does not
# pick one value inside it, which is exactly why this is tunable rather than hardcoded.
DEFAULT_REREADS_MIN = 6
CURRENT_AMBIGUITY_WINDOW_S = 180
DIGEST_USER_MSG_CAP = 40
DIGEST_USER_MSG_CHARS = 220
DIGEST_MIN_OCCURRENCES = 2

# Injected machinery that arrives on the USER channel but is not the human speaking: skill
# bodies, task notifications, command wrappers, plain-text harness notices. Measured on a live
# session, 4 of 10 "user messages" were this noise (two skill payloads, one task-notification,
# one more skill payload) — enough to make the re-ask read useless, since a reader would be
# scanning skill prose.
#
# Deliberately SEPARATE from SYSTEM_PREFIXES rather than widening it: that tuple feeds
# is_real_user_text(), which drives counts.userMsgs and therefore deepDiveCandidates selection
# for the WHOLE retrospective — widening it would silently shift every session's metrics and
# change which sessions get deep-dived. This layer applies to the digest only.
#
# Which records are the operator is decided by operator_turn_text: a record with an origin stamp is
# told apart by the stamp, because a prefix cannot do it (the blanket "<" below also matches a
# pasted block the operator sent). This list still decides for a record with no stamp, and the
# sweep reads the same prefixes off the digest it is given.
#
# Mirrors SKIP_PREFIX in the sibling sweep_user_corrections.py (same skill, same noise class).
# The two lists must move together; they are duplicated because the scripts are invoked as
# stand-alone files from the repo root and cannot import each other without path juggling.
# test_sweep_user_corrections.py imports both by path and fails when they differ as sets.
HARNESS_USER_PREFIXES = (
    "<",
    "Base directory for this skill",
    "ARGUMENTS:",
    "[Request interrupted",
    "Caveat:",
    # Plain-text events the harness injects on the user channel. In real transcripts each is
    # machine-marked (isMeta, isCompactSummary or a non-human origin), never operator typing:
    # the workflow-authoring reference header, the notice that a compacted session continues,
    # a message relayed from a peer session, and the stop notice a safety classifier leaves.
    "# Workflow authoring reference",
    "This session is being continued from a previous conversation",
    "Another Claude session sent a message",
    "Your response above was stopped by a safety classifier",
)


def _is_human_turn(text):
    """True if this user-channel text is the human speaking, not injected machinery."""
    return bool(text) and not text.lstrip().startswith(HARNESS_USER_PREFIXES)


def _session_identity(path):
    """Identity fields a CALLER CAN FALSIFY — not just an opaque id.

    The point is that a wrong pick is detectable: an operator who sees a first-message they
    never sent knows immediately that the wrong session was measured.
    """
    mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    first = next(iter_operator_turns(path), "")
    return {
        "sessionId": path.stem,
        "lastActivity": mtime.isoformat(timespec="seconds"),
        "firstUserMessage": first[:120],
    }


def resolve_session_scope(session_dir, selector):
    """Resolve --session <id|current> to exactly ONE transcript, or exit non-zero."""
    files = sorted(session_dir.glob("*.jsonl"))
    if not files:
        print(f"ERROR: no session transcripts under {session_dir}", file=sys.stderr)
        sys.exit(2)

    if selector != "current":
        matches = [f for f in files if f.stem == selector]
        if not matches:
            matches = [f for f in files if f.stem.startswith(selector)]
        if not matches:
            print(f"ERROR: no session matching id '{selector}'", file=sys.stderr)
            sys.exit(2)
        if len(matches) > 1:
            print(
                f"ERROR: id prefix '{selector}' matches {len(matches)} sessions:",
                file=sys.stderr,
            )
            for f in matches:
                print(f"    {f.stem}", file=sys.stderr)
            sys.exit(2)
        return matches[0]

    newest = max(files, key=lambda p: p.stat().st_mtime)
    newest_mtime = newest.stat().st_mtime
    rivals = [
        f
        for f in files
        if f != newest
        and newest_mtime - f.stat().st_mtime <= CURRENT_AMBIGUITY_WINDOW_S
    ]
    if rivals:
        print(
            f"ERROR: cannot identify the CURRENT session — {len(rivals) + 1} transcripts were "
            f"written within {CURRENT_AMBIGUITY_WINDOW_S}s of each other.",
            file=sys.stderr,
        )
        print(
            "  Parallel sessions are routine in this checkout, so picking the newest here could "
            "measure another session's work. Re-run with an explicit --session <id>:",
            file=sys.stderr,
        )
        for f in [newest, *rivals]:
            ident = _session_identity(f)
            print(
                f"    {ident['sessionId']}  last={ident['lastActivity']}  "
                f"first={ident['firstUserMessage'][:60]!r}",
                file=sys.stderr,
            )
        sys.exit(4)
    return newest


def _repetition_signals(sess, rereads_min):
    """(re-reads, repeated commands, build/test loops, stale-read retries) of one session, each
    at the digest's threshold."""
    b = sess.get("behavior") or {}
    rereads = [r for r in (b.get("reReads") or []) if r.get("count", 0) >= rereads_min]
    cmds = [
        c
        for c in (b.get("repeatedCommands") or [])
        if c.get("count", 0) >= DIGEST_MIN_OCCURRENCES
    ]
    loops = list(b.get("buildTestLoops") or [])
    stale = b.get("staleReadEdits") or 0
    return rereads, cmds, loops, stale


def _signal_count(signals):
    rereads, cmds, loops, stale = signals
    return (
        len(rereads)
        + len(cmds)
        + len(loops)
        + (1 if stale >= DIGEST_MIN_OCCURRENCES else 0)
    )


def _session_header_lines(sess, ident, msgs):
    """The lines that say which session this is and how much happened in it."""
    return [
        f"- Session: `{ident['sessionId']}`",
        f"- Last activity: {ident['lastActivity']}",
        f"- Branch: {sess.get('gitBranch') or 'unknown'}",
        f"- Volume: {len(msgs)} operator turns, "
        f"{sess['counts']['toolUse']} tool calls, {sess.get('compactions', 0)} compaction(s)",
        # counts.userMsgs is every user-channel record that carries text, injected text included,
        # so it is not the number of operator turns above; it stays, labelled, because it drives
        # selection.
        f"- User-channel records: {sess['counts']['userMsgs']} (counts.userMsgs; includes skill, "
        "hand-back and compaction text, so it is not a count of operator turns)",
    ]


def _signal_lines(heading, signals, rereads_min):
    rereads, cmds, loops, stale = signals
    L = [heading, ""]
    if rereads or cmds or loops or stale >= DIGEST_MIN_OCCURRENCES:
        for r in rereads:
            L.append(f"- re-read x{r['count']}: `{r.get('file', '?')}`")
        for c in cmds:
            L.append(f"- repeated command x{c['count']}: `{c.get('cmd', '?')}`")
        for lp in loops:
            L.append(f"- build/test loop: `{lp}`")
        if stale >= DIGEST_MIN_OCCURRENCES:
            L.append(f"- stale-read edit retries: {stale}")
    else:
        L.append(
            f"_None at or above the thresholds (re-read >={rereads_min}, others >={DIGEST_MIN_OCCURRENCES})._"
        )
    L.append("")
    return L


def _error_class_lines(heading, classes, none_line):
    """The main thread's error classes that qualify, most frequent first, and the note on how
    they were classified."""
    L = [heading, ""]
    if classes:
        L.extend(
            f"- {cat}: {n}" for cat, n in sorted(classes.items(), key=lambda kv: -kv[1])
        )
        L.append("")
        L.append(
            "> Classified by ORIGIN TOOL, which is content-blind by design. `environment` is "
            "the exception: calls the harness or a hook refused or stopped (by shape in "
            "aggregate.json `environmentShapes`), so give the rule a home, not an agent-quality "
            "count. Other harness-generated failures (hook denials, permission-stream aborts) "
            "still land in behavioral buckets and inflate these counts — decompose before "
            "treating any of this as an agent-quality finding."
        )
    else:
        L.append(none_line)
    L.append("")
    return L


def _subagent_lines(heading, sub, classes):
    """The sub-agent block of one session: the helpers walked (native and Workflow), how many
    failed, their environment refusals by shape, and each error class that qualifies with up to
    SUBAGENT_DIGEST_SAMPLES of its redacted samples. `sub` is the session's `subAgents`."""
    L = [heading, ""]
    count = sub.get("count", 0)
    if not count:
        L.append("_No sub-agent transcript under this session, native or Workflow._")
        L.append("")
        return L
    workflow = sub.get("workflowAgents", 0)
    L.append(
        f"- Walked: {count} ({count - workflow} native, {workflow} in Workflow runs), "
        f"{sub.get('agentsWithErrors', 0)} with errors"
    )
    shapes = sub.get("environmentShapes") or {}
    if shapes:
        L.append(
            "- Environment by shape: "
            + ", ".join(f"{shape}: {n}" for shape, n in shapes.items())
        )
    if not classes:
        L.append(f"- Error classes with {DIGEST_MIN_OCCURRENCES}+ occurrences: none")
        L.append("")
        return L
    samples = sub.get("errorSamples") or {}
    for cat, n in sorted(classes.items(), key=lambda kv: -kv[1]):
        L.append(f"- {cat}: {n}")
        for sample in (samples.get(cat) or [])[:SUBAGENT_DIGEST_SAMPLES]:
            flat = " ".join(str(sample).split())[:DIGEST_USER_MSG_CHARS]
            L.append(f"  - sample: {flat}")
    L.append("")
    L.append(
        "> The helpers' own results, classified as the main thread's are (by ORIGIN TOOL, "
        "content-blind; `environment` is a refusal or stop by the harness or a hook). The "
        "session that started a helper is the one that writes its lessons."
    )
    L.append("")
    return L


def _operator_turn_lines(heading, msgs, explain):
    L = [heading, ""]
    if explain:
        L.append(
            "Read these for RE-ASKS: the same request restated because the first attempt did not "
            "land. A re-ask needs >=2 occurrences to qualify, and paraphrase counts — no lexical "
            "marker exists, which is why this is a sequence to read and not a detector's output."
        )
        L.append("")
        L.append(
            "Operator turns only: typed messages, messages typed while the model was working, and "
            "the answers given to the question tool. Skill bodies, task notifications, hand-backs "
            "and compaction text are not listed."
        )
        L.append("")
    for i, t in enumerate(msgs[:DIGEST_USER_MSG_CAP], 1):
        flat = " ".join(t.split())[:DIGEST_USER_MSG_CHARS]
        L.append(f"{i}. {flat}")
    if len(msgs) > DIGEST_USER_MSG_CAP:
        L.append(f"…and {len(msgs) - DIGEST_USER_MSG_CAP} more (not shown).")
    L.append("")
    return L


def _qualifying(counts, shapes, minimum=DIGEST_MIN_OCCURRENCES):
    """The classes in `counts` seen `minimum` times or more. `environment` adds up unrelated
    rules (a refused sleep, a usage-limit stop, a gate denial), so it qualifies only when one
    of its shapes, counted in `shapes`, does: one of each is no pattern."""
    classes = {cat: n for cat, n in (counts or {}).items() if n >= minimum}
    if not any(n >= minimum for n in (shapes or {}).values()):
        classes.pop("environment", None)
    return classes


def write_interaction_digest(output_dir, sess, jsonl_path, rereads_min):
    """Write the per-task interaction digest that `task-learnings` Step 0 reads.

    Counted signals are computed here. RE-ASKS ARE DELIBERATELY NOT DETECTED: a re-ask is the
    same request restated in different words, and unlike a correction (which has lexical markers
    — "wrong", "no,", "actually" — that sweep_user_corrections.py greps) it has no marker at all.
    A token-overlap similarity score both false-positives on shared domain vocabulary and misses
    terse restatements. So this emits the user-message SEQUENCE and the reader classifies by
    reading it — judgment where judgment belongs.

    The sub-agent block carries what the session's helpers did, native and Workflow alike: the
    lessons of work a session handed off are this session's to write, and before the block they
    reached aggregate.json only, which this step never reads.
    """
    signals = _repetition_signals(sess, rereads_min)
    rereads, cmds, loops, stale = signals
    errors = _qualifying(sess.get("errorsByCategory"), sess.get("environmentShapes"))
    sub = sess.get("subAgents") or {}
    sub_errors = _qualifying(sub.get("errorsByCategory"), sub.get("environmentShapes"))
    msgs = list(iter_operator_turns(jsonl_path))

    signal_count = _signal_count(signals)
    gate = "SIGNAL" if signal_count or errors or sub_errors else "NO SIGNAL"
    ident = _session_identity(jsonl_path)

    L = []
    L.append(f"# Interaction digest — session {ident['sessionId'][:8]}")
    L.append("")
    L.extend(_session_header_lines(sess, ident, msgs))
    L.append(
        f"- Re-read threshold applied: >={rereads_min} (see DEFAULT_REREADS_MIN provenance)"
    )
    L.append(f"- Gate: {gate}")
    L.append("")
    L.extend(_signal_lines("## Counted repetition signals", signals, rereads_min))
    L.extend(
        _error_class_lines(
            "## Agent error classes (>=2 in this session)",
            errors,
            "_None with 2+ occurrences._",
        )
    )
    L.extend(_subagent_lines("## Sub-agents (>=2 in this session)", sub, sub_errors))
    L.extend(
        _operator_turn_lines(
            f"## User-message sequence ({len(msgs)} total, first {DIGEST_USER_MSG_CAP} shown)",
            msgs,
            explain=True,
        )
    )
    L.append("## Rules for anything written from this digest")
    L.append("")
    L.append(
        f"1. A candidate needs **>={DIGEST_MIN_OCCURRENCES} occurrences in THIS session**. One event is not a pattern."
    )
    L.append("2. **At most 2 entries per task.** Rank and drop the rest.")
    L.append(
        "3. Every count and quote you write **must be locatable in this file**. If it is not here, discard the claim — do not soften it."
    )
    L.append(
        "4. Cross-SESSION patterns are `session-retrospective`'s job, not this one. Report only what this session proves."
    )
    L.append("")

    path = Path(output_dir) / "interaction-digest.md"
    _write_lf(path, "\n".join(L))
    print(
        f"Wrote {path} — gate={gate}, "
        f"{signal_count} repetition signal(s), {len(errors)} error class(es), "
        f"{len(sub_errors)} sub-agent error class(es), {len(msgs)} operator turns",
        file=sys.stderr,
    )
    return path


# --- task mode: every session of one task, and nothing else ------------------------------------
# A task carried across a hand-off chain is measured as one: the sessions its hand-offs list on
# their `Sessions:` line, with every helper those sessions started (native and Workflow), and not a
# session of any other task, even one that ran beside it. The ids are the evidence set, so nothing
# here guesses one: `current` is refused, an id is matched by the exact name of a transcript in the
# ONE session folder this run reads (never by prefix, never in another project's folder on an id's
# say-so), and an id that cannot be measured is reported with its reason and never dropped. A
# listed session with no operator turn is measured all the same: its helpers did work.
#
# A hand-off is read as the kit's lint reads it (lemmi_ai_kit.checks: parse_handoff_ledger and
# handoff_session_ids): the header block is every line above the first `## ` heading, HTML
# comments blanked with their newlines kept, fenced lines skipped; a line is a ledger line when it
# starts with its key and a colon, its value is the rest of the line stripped, and a line written
# twice has no value. This file runs stand-alone and imports nothing of the kit, so the rule is
# restated here, and tests/test_handoff_ledger_agreement.py holds the two readers equal on the same
# notes. Each pattern below reads a line of many spaces in linear time: the lines are another
# session's text.
HANDOFF_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
HANDOFF_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
HANDOFF_SECTION_RE = re.compile(r"^## (.+)$")
HANDOFF_LEDGER_KEYS = ("Task", "Sessions")
# The selector that picks a session by file time: a guess, so task mode refuses it.
CURRENT_SELECTOR = "current"
# Exit status of a run in which a listed session could not be measured; the digest is kept.
EXIT_UNMEASURED = 5
UNMEASURED_NO_TRANSCRIPT = "no transcript in this project's session folder"
UNMEASURED_UNREADABLE = "transcript unreadable"
UNMEASURED_PROCESSING_ERROR = "processing error"
# How many redacted samples the sub-agent block quotes for one class (the session carries 3).
SUBAGENT_DIGEST_SAMPLES = 2


def read_handoff_ledger(text):
    """{'Task': value or None, 'Sessions': value or None} from a hand-off's header block, read
    as the kit's lint reads it (see the comment above). None: no such line, or two."""
    text = HANDOFF_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    found = {key: [] for key in HANDOFF_LEDGER_KEYS}
    fenced = False
    for line in text.splitlines():
        if HANDOFF_FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if HANDOFF_SECTION_RE.match(line):
            break
        for key in HANDOFF_LEDGER_KEYS:
            if line.startswith(f"{key}:"):
                found[key].append(line[len(key) + 1 :].strip())
                break
    return {key: (v[0] if len(v) == 1 else None) for key, v in found.items()}


def ledger_session_ids(sessions):
    """The ids a `Sessions:` value lists, in order and each once; () for None. The ids are
    separated by commas and stripped, and an empty item is skipped."""
    if sessions is None:
        return ()
    return tuple(
        dict.fromkeys(item.strip() for item in sessions.split(",") if item.strip())
    )


def _refusal(message):
    """The exit of a refused task-mode run, for the caller to raise: a task's evidence set is
    named, never guessed, so a run that cannot name it says why, measures nothing and writes
    nothing (exit 2)."""
    print(
        f"ERROR: {message} No session was measured and nothing was written.",
        file=sys.stderr,
    )
    return SystemExit(2)


def resolve_task_scope(selectors, notes):
    """The evidence set of a task-mode run: {'task': slug or None, 'ids': (...), 'notes': [...]}.

    The ids are the --session values in the order given, then each hand-off's Sessions ids, each
    id once. Exits 2 before anything is written on `current`, on a hand-off that does not exist
    or cannot be read, on one with no single Sessions line or no id on it, and on hand-offs that
    name different tasks: one run measures one task."""
    if CURRENT_SELECTOR in selectors:
        raise _refusal(
            f"`--session {CURRENT_SELECTOR}` is refused in task mode: it picks a session by file "
            "time, and a task's sessions are named by id."
        )
    ids = list(selectors)
    tasks = []
    for note in notes:
        path = Path(note)
        if not path.exists():
            raise _refusal(f"the hand-off {note} does not exist.")
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:
            raise _refusal(
                f"the hand-off {note} cannot be read ({type(exc).__name__})."
            ) from None
        ledger = read_handoff_ledger(text)
        if ledger["Sessions"] is None:
            raise _refusal(
                f"the hand-off {note} has no Sessions line in its header block (above the first "
                "`## ` heading, outside comments and fences), or has two; a v3 hand-off lists "
                "every session of its task there, and none is guessed in its place."
            )
        listed = ledger_session_ids(ledger["Sessions"])
        if not listed:
            raise _refusal(
                f"the Sessions line of the hand-off {note} lists no session id."
            )
        ids.extend(listed)
        if ledger["Task"] is not None and ledger["Task"] not in tasks:
            tasks.append(ledger["Task"])
    if len(tasks) > 1:
        raise _refusal(
            f"the hand-offs name {len(tasks)} tasks ({', '.join(tasks)}); one run measures one "
            "task."
        )
    ids = list(dict.fromkeys(ids))
    if CURRENT_SELECTOR in ids:
        raise _refusal(
            f"a hand-off lists `{CURRENT_SELECTOR}`, which is no session id."
        )
    return {
        "task": tasks[0] if tasks else None,
        "ids": tuple(ids),
        "notes": list(notes),
    }


def resolve_task_sessions(session_dir, ids):
    """([transcript], [(id, reason)]): each listed id's transcript, found by its exact file name
    in the listing of `session_dir` and nowhere else, or the reason it has none."""
    by_name = {f.stem: f for f in session_dir.glob("*.jsonl")}
    found, missing = [], []
    for sid in ids:
        path = by_name.get(sid)
        if path is None:
            missing.append((sid, UNMEASURED_NO_TRANSCRIPT))
            continue
        try:
            with open(path, "rb"):
                pass
        except OSError:
            missing.append((sid, UNMEASURED_UNREADABLE))
            continue
        found.append(path)
    return found, missing


def _drop_outputs(sessions_dir, sid):
    """Remove what process_session wrote for `sid` before it failed, so that an unmeasured
    session leaves nothing in the outputs."""
    with contextlib.suppress(OSError):
        (sessions_dir / f"{sid}.md").unlink(missing_ok=True)
    shutil.rmtree(sessions_dir / "sub" / sid, ignore_errors=True)


def _shape_text(shapes):
    return ", ".join(f"{shape}: {n}" for shape, n in shapes.items() if n) or "none"


def _class_total_lines(label, totals, by_session):
    """One totals line for the classes that qualify across the task, each with its split by
    session, so that a count written from it can be found again in the sections below."""
    if not totals:
        return [f"- {label}: none"]
    L = [f"- {label}:"]
    for cat, n in sorted(totals.items(), key=lambda kv: -kv[1]):
        split = ", ".join(f"{sid8}: {k}" for sid8, k in by_session[cat])
        L.append(f"  - {cat}: {n} ({split})")
    return L


def write_task_digest(output_dir, task, sessions, inputs, unmeasured, rereads_min):
    """Write the task digest: one interaction digest for every session a task's hand-offs list.

    The header names the task and the listed ids; then come the totals over the measured
    sessions, the ids that were not measured with their reasons, and one section per measured
    session, oldest first, holding what a one-session digest holds, sub-agent block included. A
    class qualifies when it occurs twice or more across the task's sessions, the main threads and
    the helpers counted apart (`environment` when one of its shapes does), and each section lists
    its own session's count of it. `inputs`
    maps a session id to (identity, operator turns), read inside the run's per-file guard."""
    main_totals, sub_totals = defaultdict(int), defaultdict(int)
    main_by, sub_by = defaultdict(list), defaultdict(list)
    main_env = dict.fromkeys(ENVIRONMENT_SHAPES, 0)
    sub_env = dict.fromkeys(ENVIRONMENT_SHAPES, 0)
    turns = tools = compactions = walked = workflow = with_errors = 0
    for s in sessions:
        sid8 = s["sessionId"][:8]
        sub = s.get("subAgents") or {}
        for cat, n in (s.get("errorsByCategory") or {}).items():
            main_totals[cat] += n
            main_by[cat].append((sid8, n))
        for cat, n in (sub.get("errorsByCategory") or {}).items():
            sub_totals[cat] += n
            sub_by[cat].append((sid8, n))
        for shape, n in (s.get("environmentShapes") or {}).items():
            main_env[shape] = main_env.get(shape, 0) + n
        for shape, n in (sub.get("environmentShapes") or {}).items():
            sub_env[shape] = sub_env.get(shape, 0) + n
        turns += len(inputs[s["sessionId"]][1])
        tools += s["counts"]["toolUse"]
        compactions += s.get("compactions", 0)
        walked += sub.get("count", 0)
        workflow += sub.get("workflowAgents", 0)
        with_errors += sub.get("agentsWithErrors", 0)
    main_classes = _qualifying(main_totals, main_env)
    sub_classes = _qualifying(sub_totals, sub_env)
    signal_count = sum(
        _signal_count(_repetition_signals(s, rereads_min)) for s in sessions
    )
    gate = "SIGNAL" if signal_count or main_classes or sub_classes else "NO SIGNAL"
    slug = task["task"]

    L = [f"# Interaction digest — task {slug or '(not named)'}", ""]
    if slug:
        named_in = ", ".join(f"`{Path(note).name}`" for note in task["notes"])
        L.append(f"- Task: `{slug}`, from the `Task:` line of {named_in}")
    elif task["notes"]:
        L.append("- Task: not named: no hand-off given has a single `Task:` line")
    else:
        L.append("- Task: not named: the sessions were given by id, with no hand-off")
    L.append(
        f"- Sessions listed: {len(task['ids'])}: "
        + ", ".join(f"`{sid}`" for sid in task["ids"])
    )
    L.append(
        f"- Measured: {len(sessions)}, one section each below, oldest first; "
        f"unmeasured: {len(unmeasured)}"
        + (" (nothing in this file is about them)" if unmeasured else "")
    )
    L.append(
        f"- Re-read threshold applied: >={rereads_min} (see DEFAULT_REREADS_MIN provenance)"
    )
    L.append(f"- Gate: {gate}")
    L.append(
        "- Each user-message sequence lists operator turns only (typed messages, messages typed "
        "while the model was working, answers given to the question tool). Read them for "
        "RE-ASKS: the same request restated because the first attempt did not land; paraphrase "
        "counts, and no detector does this for you."
    )
    L.append("")
    L.append("## Totals across the measured sessions")
    L.append("")
    L.append(
        f"- Volume: {turns} operator turns, {tools} tool calls, {compactions} compaction(s)"
    )
    L.append(
        f"- Sub-agents: {walked} walked ({walked - workflow} native, {workflow} in Workflow "
        f"runs), {with_errors} with errors"
    )
    L.extend(
        _class_total_lines(
            "Agent error classes (>=2 across this task's sessions)",
            main_classes,
            main_by,
        )
    )
    L.extend(
        _class_total_lines(
            "Sub-agent error classes (>=2 across this task's sessions)",
            sub_classes,
            sub_by,
        )
    )
    L.append(
        f"- Environment by shape: main threads {_shape_text(main_env)}; "
        f"sub-agents {_shape_text(sub_env)}"
    )
    L.append("")
    L.append(f"## Unmeasured sessions ({len(unmeasured)})")
    L.append("")
    if unmeasured:
        L.extend(f"- `{sid}`: {reason}" for sid, reason in unmeasured)
        L.append("")
        L.append(
            "> Not read, so nothing here is about them and nothing written from this file may "
            "be. A session that ran in another project's folder is measured by a run of its own "
            "with that folder as the first argument."
        )
    else:
        L.append("_None: every listed session was measured._")
    L.append("")
    for s in sessions:
        ident, msgs = inputs[s["sessionId"]]
        sub = s.get("subAgents") or {}
        L.append(f"## Session {s['sessionId'][:8]}")
        L.append("")
        L.extend(_session_header_lines(s, ident, msgs))
        L.append("")
        L.extend(
            _signal_lines(
                "### Counted repetition signals",
                _repetition_signals(s, rereads_min),
                rereads_min,
            )
        )
        L.extend(
            _error_class_lines(
                "### Agent error classes (>=2 across this task's sessions)",
                {
                    cat: n
                    for cat, n in (s.get("errorsByCategory") or {}).items()
                    if cat in main_classes
                },
                "_None of the classes seen 2+ times across this task._",
            )
        )
        L.extend(
            _subagent_lines(
                "### Sub-agents (>=2 across this task's sessions)",
                sub,
                {
                    cat: n
                    for cat, n in (sub.get("errorsByCategory") or {}).items()
                    if cat in sub_classes
                },
            )
        )
        L.extend(
            _operator_turn_lines(
                f"### User-message sequence ({len(msgs)} total, first {DIGEST_USER_MSG_CAP} shown)",
                msgs,
                explain=False,
            )
        )
    L.append("## Rules for anything written from this digest")
    L.append("")
    L.append(
        f"1. A candidate needs **>={DIGEST_MIN_OCCURRENCES} occurrences across this task's sessions**. One event is not a pattern."
    )
    L.append("2. **At most 2 entries per task.** Rank and drop the rest.")
    L.append(
        "3. Every count and quote you write **must be locatable in this file**. If it is not here, discard the claim — do not soften it."
    )
    L.append(
        "4. **Write nothing about an unmeasured session**: it was not read. Cross-TASK patterns are `session-retrospective`'s job, not this one. Report only what this task's sessions prove."
    )
    L.append("")

    path = Path(output_dir) / "interaction-digest.md"
    _write_lf(path, "\n".join(L))
    print(
        f"Wrote {path} — task {slug or '(not named)'}, gate={gate}, {len(sessions)} of "
        f"{len(task['ids'])} listed session(s) measured, {len(unmeasured)} unmeasured, "
        f"{len(main_classes)} error class(es), {len(sub_classes)} sub-agent error class(es)",
        file=sys.stderr,
    )
    return path


def main():
    # v4 (C-7): single-file leak gate — same LEAK_PATTERNS code path as --self-check; used by
    # the SKILL's Phase-6 report-privacy check on the draft report. Handled before argparse so
    # the extraction positionals are not required in this mode.
    if "--check-file" in sys.argv[1:]:
        i = sys.argv.index("--check-file")
        if i + 1 >= len(sys.argv):
            print("usage: extract_sessions.py --check-file <path>", file=sys.stderr)
            sys.exit(2)
        leaks = check_file(sys.argv[i + 1])
        if leaks:
            print("CHECK-FILE FAILED — possible secret leak:", file=sys.stderr)
            for lk in leaks:
                print("  " + lk, file=sys.stderr)
            sys.exit(3)
        print("CHECK-FILE PASSED — no secret shapes found", file=sys.stderr)
        return

    ap = argparse.ArgumentParser(
        description="Behavioral extractor for Claude Code sessions"
    )
    ap.add_argument(
        "session_dir",
        nargs="?",
        help="Claude session dir under ~/.claude/projects/. When omitted it is derived from the "
        "working directory, which must be the project root (the directory Claude Code was "
        "launched in) with a session folder of its own; anywhere else the run is refused and "
        "this argument is required",
    )
    ap.add_argument(
        "output_dir", help="repo-relative output dir (e.g. .ai/tmp/retro/), never /tmp"
    )
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument(
        "--session",
        action="append",
        help="scope to ONE session: a session id (or unique prefix), or 'current' for the "
        "most-recently-written transcript. 'current' exits 4 if two transcripts were written "
        "close together, rather than guessing between parallel sessions. Given twice or more, "
        "or beside --sessions-from, it is task mode: each id must be the exact name of a "
        "transcript in the session dir, and 'current' is refused (exit 2).",
    )
    ap.add_argument(
        "--sessions-from",
        action="append",
        metavar="HAND-OFF",
        help="task mode: measure every session a v3 hand-off lists on its Sessions line, with "
        "their sub-agents, and nothing else (repeatable: one per note of the task received). "
        "A hand-off that does not exist or has no Sessions line exits 2; a listed session that "
        "cannot be measured is reported unmeasured with its reason, and the run exits 5 with "
        "the digest kept.",
    )
    ap.add_argument(
        "--digest",
        action="store_true",
        help="also write interaction-digest.md (requires --session or --sessions-from); "
        "consumed by task-learnings",
    )
    ap.add_argument(
        "--rereads-min",
        type=int,
        default=DEFAULT_REREADS_MIN,
        help=f"minimum re-read count treated as a signal (default {DEFAULT_REREADS_MIN}; "
        "measured range 4-8 — see DEFAULT_REREADS_MIN provenance comment)",
    )
    args = ap.parse_args()

    selectors = args.session or []
    notes = args.sessions_from or []
    # Task mode: the sessions of one task, named by id or by its hand-offs (see the comment
    # above read_handoff_ledger). One --session alone is the one-session mode it always was.
    task_mode = bool(notes) or len(selectors) > 1

    if args.digest and not (selectors or notes):
        print(
            "ERROR: --digest requires --session <id|current> or --sessions-from <hand-off>",
            file=sys.stderr,
        )
        sys.exit(2)
    # Read and checked before anything is written, so a refusal leaves no output behind.
    task = resolve_task_scope(selectors, notes) if task_mode else None

    session_dir = Path(args.session_dir) if args.session_dir else _derive_session_dir()
    print(f"Using session dir: {session_dir}", file=sys.stderr)
    output_dir = Path(args.output_dir)
    if str(output_dir).replace("\\", "/").lower().startswith("/tmp"):
        print(
            "ERROR: output-dir must be repo-relative (e.g. .ai/tmp/retro/), never the system /tmp",
            file=sys.stderr,
        )
        sys.exit(2)
    sessions_dir = output_dir / "sessions"
    # v4 (C-3): output hygiene — out-of-range/stale transcripts from previous runs otherwise
    # accumulate forever and become a Phase-5 grep-verification foot-gun. Never clear silently
    # (a parallel session could be reading): always print what was removed.
    if sessions_dir.is_dir():
        stale = list(sessions_dir.rglob("*.md"))
        if stale:
            print(
                f"Clearing {len(stale)} stale transcript file(s) from a previous run "
                f"under {sessions_dir}",
                file=sys.stderr,
            )
            shutil.rmtree(sessions_dir, ignore_errors=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # An explicit --session overrides date filtering: the caller named the session, so a stale
    # --since would silently drop it and yield an empty digest that reads as "no signal". A
    # task's hand-offs name its sessions too.
    since = None if selectors or notes else args.since
    until = None if selectors or notes else args.until

    unmeasured = []  # task mode: (session id, reason) for each listed id that was not measured
    if task is not None:
        files, unmeasured = resolve_task_sessions(session_dir, task["ids"])
        print(
            f"Task mode: {task['task'] or '(task not named)'}, {len(task['ids'])} listed "
            f"session(s), {len(files)} transcript(s) found by exact name",
            file=sys.stderr,
        )
    elif selectors:
        scoped = resolve_session_scope(session_dir, selectors[0])
        ident = _session_identity(scoped)
        print(
            f"Scoped to ONE session: {ident['sessionId']}\n"
            f"  last activity     : {ident['lastActivity']}\n"
            f"  first user message: {ident['firstUserMessage']!r}",
            file=sys.stderr,
        )
        files = [scoped]
    else:
        files = sorted(p for p in session_dir.glob("*.jsonl"))
        print(f"Found {len(files)} top-level session files", file=sys.stderr)

    sessions = []
    tax = {c: {"count": 0, "sessions": [], "samples": []} for c in ERROR_CATEGORIES}
    user_rejected = {"count": 0, "sessions": [], "samples": []}
    hook_denials = {"count": 0, "sessions": [], "samples": []}
    # v5: the `environment` category by shape, every shape listed as byCategory lists every class
    env_shapes = dict.fromkeys(ENVIRONMENT_SHAPES, 0)
    replays = {}  # session id -> repeated events left out of it: for stderr, not the aggregate
    # task mode: session id -> (identity, operator turns), read inside the per-file guard below so
    # that a transcript the digest cannot read makes its session unmeasured, never a crash
    digest_inputs = {}

    prescan_skipped = 0
    for f in files:
        # v4 (C-3): timestamp pre-scan — skip clearly out-of-range sessions BEFORE the full
        # parse (the sub-agent walk is the expensive part; cost otherwise grows with project
        # age). Undeterminable dates → full parse; the exact overlap filter below still runs.
        if since or until:
            first_ts, last_ts = prescan_date_range(f)
            if (since and last_ts and last_ts[:10] < since) or (
                until and first_ts and first_ts[:10] > until
            ):
                prescan_skipped += 1
                continue
        try:
            sess, local_errors, rejected, hooked = process_session(
                f, sessions_dir, replays
            )
            if task is not None and args.digest:
                digest_inputs[sess["sessionId"]] = (
                    _session_identity(f),
                    list(iter_operator_turns(f)),
                )
        except Exception as exc:  # never abort the whole run on one file
            print(f"  ! error processing {f.name}: {exc}", file=sys.stderr)
            if task is not None:  # a listed session is never dropped: it is unmeasured
                unmeasured.append(
                    (f.stem, f"{UNMEASURED_PROCESSING_ERROR} ({type(exc).__name__})")
                )
                _drop_outputs(sessions_dir, f.stem)
            continue
        # A listed session is measured whatever it holds: one with no operator turn may still
        # have started the helpers that did the task's work.
        if sess["counts"]["userMsgs"] == 0 and task is None:
            continue
        # date overlap filter
        if since and sess["endTime"] and sess["endTime"][:10] < since:
            continue
        if until and sess["startTime"] and sess["startTime"][:10] > until:
            continue
        sessions.append(sess)
        for shape, n in sess["environmentShapes"].items():
            env_shapes[shape] += n
        for cat, samples in local_errors.items():
            tax[cat]["count"] += sess["errorsByCategory"].get(cat, 0)
            if sess["errorsByCategory"].get(cat):
                tax[cat]["sessions"].append(sess["sessionId"][:8])
            for s in samples:
                if len(tax[cat]["samples"]) < 8:
                    tax[cat]["samples"].append(s)
        if sess["userRejected"]:
            # the TRUE number: `rejected` is a capped sample list, so its length undercounts
            user_rejected["count"] += sess["userRejected"]
            user_rejected["sessions"].append(sess["sessionId"][:8])
            for s in rejected:
                if len(user_rejected["samples"]) < 8:
                    user_rejected["samples"].append(s)
        if sess["hookDenials"]:
            # the TRUE number again: `hooked` is a capped sample list
            hook_denials["count"] += sess["hookDenials"]
            hook_denials["sessions"].append(sess["sessionId"][:8])
            for s in hooked:
                if len(hook_denials["samples"]) < 8:
                    hook_denials["samples"].append(s)

    sessions.sort(key=lambda s: s["startTime"] or "")

    if task is not None:
        listed_at = {sid: i for i, sid in enumerate(task["ids"])}
        unmeasured.sort(key=lambda u: listed_at.get(u[0], len(listed_at)))
        for sid, reason in unmeasured:
            print(f"  ! unmeasured {sid}: {reason}", file=sys.stderr)
        if args.digest:
            write_task_digest(
                output_dir, task, sessions, digest_inputs, unmeasured, args.rereads_min
            )
    elif args.digest:
        if not sessions:
            print(
                "ERROR: the scoped session yielded no analyzable content (0 real user messages) — "
                "no digest written. Do NOT fall back to writing entries from recollection.",
                file=sys.stderr,
            )
            sys.exit(2)
        write_interaction_digest(output_dir, sessions[0], files[0], args.rereads_min)

    # cross-session sub-agent error taxonomy (rolled up from each session's walk_subagents pass)
    sub_tax = {c: {"count": 0, "sessions": [], "samples": []} for c in ERROR_CATEGORIES}
    sub_totals = {"totalAgents": 0, "agentsWithErrors": 0, "transcriptsEmitted": 0}
    sub_env_shapes = dict.fromkeys(ENVIRONMENT_SHAPES, 0)
    for s in sessions:
        sa = s["subAgents"]
        sub_totals["totalAgents"] += sa.get("count", 0)
        sub_totals["agentsWithErrors"] += sa.get("agentsWithErrors", 0)
        sub_totals["transcriptsEmitted"] += sa.get("transcriptsEmitted", 0)
        for shape, n in sa.get("environmentShapes", {}).items():
            sub_env_shapes[shape] += n
        for c, n in sa.get("errorsByCategory", {}).items():
            sub_tax[c]["count"] += n
            sub_tax[c]["sessions"].append(s["sessionId"][:8])
        for c, lst in sa.get("errorSamples", {}).items():
            for smp in lst:
                if len(sub_tax[c]["samples"]) < 8:
                    sub_tax[c]["samples"].append(smp)

    stats = {
        "totalSessions": len(sessions),
        "dateRange": {
            "from": sessions[0]["startTime"] if sessions else None,
            "to": sessions[-1]["endTime"] if sessions else None,
        },
        "totalUserMessages": sum(s["counts"]["userMsgs"] for s in sessions),
        "totalToolCalls": sum(s["counts"]["toolUse"] for s in sessions),
        "totalThinkingBlocks": sum(s["counts"]["thinking"] for s in sessions),
        "subAgent": {
            "files": sum(s["subAgents"]["count"] for s in sessions),
            "bytes": sum(s["subAgents"]["bytes"] for s in sessions),
            "msgs": sum(s["subAgents"]["msgs"] for s in sessions),
        },
        "branchesWorkedOn": sorted(
            {s["gitBranch"] for s in sessions if s["gitBranch"]}
        ),
        # v4 (C-2): union of model-invoked (Skill tool) and user-typed (/slash) names — same
        # list-of-names shape as v3; user-mode entries may include built-in commands (the
        # consumer cross-checks against `ls .claude/skills/`).
        "skillsUsed": sorted(
            {si["skill"] for s in sessions for si in s["skillInvocations"]}
            | {sc["command"] for s in sessions for sc in s["slashCommands"]}
        ),
        "skillInvocationModes": _invocation_modes(sessions),
        "skillsBlocked": sorted(
            {
                si["skill"]
                for s in sessions
                for si in s["skillInvocations"]
                if si["blocked"]
            }
        ),
        "allToolsUsed": _merge_tools(sessions),
    }

    deep_dive = select_deep_dive(sessions)
    sub_deep_dive = select_subagent_deep_dive(sessions)

    out = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedFor": {
            "sessionDir": str(session_dir),
            "since": since,
            "until": until,
            "generatedAt": datetime.now(UTC).isoformat(),
        },
        "stats": stats,
        "errorTaxonomy": {
            "byCategory": tax,
            "userRejected": user_rejected,
            "hookDenials": hook_denials,
            "environmentShapes": env_shapes,  # v5
        },
        "subAgentErrorTaxonomy": {
            "byCategory": sub_tax,
            **sub_totals,
            "environmentShapes": sub_env_shapes,  # v5
        },
        "deepDiveCandidates": deep_dive,
        "subAgentDeepDiveCandidates": sub_deep_dive,
        "sessions": sessions,
    }

    # validate schema contract before writing
    _validate_schema(out)

    _write_lf(output_dir / "aggregate.json", json.dumps(out, indent=2))
    print(
        f"Wrote aggregate.json ({len(sessions)} sessions) + {len(list(sessions_dir.glob('*.md')))} transcripts to {output_dir}",
        file=sys.stderr,
    )
    print(
        "Errors by category: "
        + ", ".join(
            f"{c}={tax[c]['count']}" for c in ERROR_CATEGORIES if tax[c]["count"]
        )
        + f" | user-rejected={user_rejected['count']} | hook-denials={hook_denials['count']}",
        file=sys.stderr,
    )
    sub_cat = ", ".join(
        f"{c}={sub_tax[c]['count']}" for c in ERROR_CATEGORIES if sub_tax[c]["count"]
    )
    print(
        f"Sub-agents: {sub_totals['totalAgents']} agents, "
        f"{sub_totals['agentsWithErrors']} with errors, "
        f"{sub_totals['transcriptsEmitted']} transcripts emitted"
        + (f" | {sub_cat}" if sub_cat else ""),
        file=sys.stderr,
    )
    # Never silent: the counts above read each replayed event once, so a run over a replayed
    # transcript reads lower than one built before the extractor dropped repeats. Only the
    # sessions that reached the aggregate are counted, and only when there is something to say.
    kept = {s["sessionId"] for s in sessions}
    replayed = {sid: n for sid, n in replays.items() if sid in kept}
    if replayed:
        print(
            f"Replayed events: skipped {sum(replayed.values())} repeated event(s) in "
            f"{len(replayed)} session(s); each event is counted once, by its uuid",
            file=sys.stderr,
        )
    if since or until:
        print(
            f"Pre-scan skipped {prescan_skipped} out-of-range session file(s) before parsing",
            file=sys.stderr,
        )
    print(
        f"Deep-dive candidates: {len(deep_dive['selected'])} sessions "
        f"(+{len(deep_dive['overCap'])} over cap), "
        f"{len(sub_deep_dive['selected'])} sub-agents "
        f"(+{len(sub_deep_dive['overCap'])} over cap)",
        file=sys.stderr,
    )

    if args.self_check:
        leaks, scanned = self_check(output_dir)
        if leaks:
            print("SELF-CHECK FAILED — possible secret leak:", file=sys.stderr)
            for lk in leaks:
                print("  " + lk, file=sys.stderr)
            # The digest is a CONSUMED artifact: a caller that ignores the exit code would still
            # find it on disk and write learnings from leaked content. Removing it makes the
            # failure unmissable — a suppressed output cannot be read by accident.
            digest = output_dir / "interaction-digest.md"
            if digest.is_file():
                digest.unlink()
                print(
                    f"  Removed {digest} — a leaking digest must not remain readable.",
                    file=sys.stderr,
                )
            sys.exit(3)
        # Print the denominator: "no secret shapes found" over an empty file list is a gate that
        # never ran, and without the count it is indistinguishable from a real pass.
        print(
            f"SELF-CHECK PASSED — no secret shapes found across {scanned} emitted file(s)",
            file=sys.stderr,
        )
        if not scanned:
            print(
                "  WARNING: zero files scanned — this is NOT a clean result.",
                file=sys.stderr,
            )

    # Task mode, last, so that a leak (exit 3, digest deleted) wins: a listed session that was
    # not measured is never silent. The digest is kept, and it names each such id with its reason.
    if task is not None and unmeasured:
        print(
            f"UNMEASURED: {len(unmeasured)} of {len(task['ids'])} listed session(s) could not "
            f"be measured ({', '.join(sid for sid, _ in unmeasured)}); exit {EXIT_UNMEASURED}. "
            "Write nothing about them.",
            file=sys.stderr,
        )
        sys.exit(EXIT_UNMEASURED)


def _merge_tools(sessions):
    merged = defaultdict(int)
    for s in sessions:
        for t, n in s["toolsUsed"].items():
            merged[t] += n
    return dict(sorted(merged.items(), key=lambda x: -x[1]))


def _invocation_modes(sessions):
    """Per-skill invocation counts by mode (v4, C-2; harness v5): user = a /slash command the
    operator typed, harness = one the harness typed (slashCommands[].by), model = Skill tool."""
    modes = defaultdict(lambda: {"user": 0, "model": 0, "harness": 0})
    for s in sessions:
        for si in s["skillInvocations"]:
            modes[si["skill"]]["model"] += 1
        for sc in s["slashCommands"]:
            modes[sc["command"]]["user" if sc["by"] == "operator" else "harness"] += 1
    return {k: dict(v) for k, v in sorted(modes.items())}


def _validate_schema(out):
    missing = [k for k in SCHEMA_KEYS["top"] if k not in out]
    if missing:
        raise ValueError(f"aggregate missing top-level keys: {missing}")
    for s in out["sessions"]:
        miss = [k for k in SCHEMA_KEYS["session"] if k not in s]
        if miss:
            raise ValueError(f"session {s.get('sessionId')} missing keys: {miss}")


if __name__ == "__main__":
    main()
