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

SCHEMA_VERSION = 4

# --- schema contract (machine source of truth; mirrored in extractor-output-schema.md) ---
# v4 is ADDITIVE-ONLY over v3: existing keys/shapes unchanged (other consumers — the SKILL.md
# phases and any downstream analysis skill — keep working); new keys listed at the end.
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
TEST_BUILD_RE = re.compile(
    r"(pytest|docker compose.*test|ruff|basedpyright|mypy|alembic|npm test|uv run)",
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

# Deep-dive candidate selection (v4, C-1): the Phase-3/3b ranking used to be done by the model
# (LLM arithmetic/sorting is a known error class; the 06-22 run hand-wrote an ad-hoc script for
# it). The extractor now emits the selections deterministically; the SKILL consumes the lists.
DEEP_DIVE_TOOLUSE_MIN = 15
DEEP_DIVE_USERMSGS_MIN = 6
DEEP_DIVE_CAP = 8
SUBAGENT_DEEPDIVE_CAP = 6

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
    origin = obj.get("origin")
    if origin is not None:
        return redact(_typed_text(blocks)) if _is_human_origin(origin) else ""
    # No origin stamp: the record is the operator's unless something marks it as machine text, and
    # the injected-text prefixes still apply (they are all that tells such records apart).
    if (
        obj.get("isMeta")
        or obj.get("isCompactSummary")
        or str(obj.get("turnOrigin")) in MACHINE_TURN_ORIGINS
    ):
        return ""
    text = _typed_text(blocks)
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


def classify_error(origin, is_error, text):
    """Return an error category, 'user-rejected', or None. Classifies by ORIGIN tool.

    Content tools are never errors unless is_error is set. Shell tools may also error via a
    non-zero exit code surfaced in the result body. 'user-rejected' is USER_REJECTED_SENTENCE at
    the start of an is_error result and nothing looser; leading whitespace is tolerated because
    a list-of-blocks result joins an empty first block into a leading newline.
    """
    if is_error and text.lstrip().startswith(USER_REJECTED_SENTENCE):
        return "user-rejected"

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
        },
        "transcriptPath": None,
        "backtrackingMarkers": 0,
        "slashCommands": [],
        "models": defaultdict(int),
        "compactions": 0,
        "userRejected": 0,  # every user-rejected result; `user_rejected` below is a capped sample
        "hookDenials": 0,  # every hook-blocked result; `hook_denials` below is a capped sample
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
                        sess["slashCommands"].append(
                            {"command": cm.group(1), "args": args}
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


def render_subagent(jf, left_out=None):
    """Parse one sub-agent transcript .jsonl → (redacted_text, msgs, errorsByCategory, samples).

    Mirrors process_session's message walk but lighter: no behavior metrics, just the readable
    redacted narrative + an error taxonomy (same classify_error, by ORIGIN tool). `samples` is a
    list of (category, redacted_sample) tuples. Errors inside sub-agents were previously invisible.
    `left_out` is the list iter_jsonl appends the uuid of each repeated event to.
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
    for jf in sorted(sub_root.rglob(SUBAGENT_GLOB)):
        sess["subAgents"]["count"] += 1
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
        text, msgs, errs, samples = render_subagent(jf, left_out)
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

    # select high-signal transcripts to emit: every error-bearing agent + the top-N by bytes,
    # de-duplicated and capped (bounded so a huge fan-out can't explode the output).
    top_bytes = sorted(parsed, key=lambda p: -p["bytes"])[:SUBAGENT_TOP_BYTES_EMIT]
    candidates = [p for p in parsed if p["errs"]] + [
        p for p in top_bytes if not p["errs"]
    ]
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
    """Deterministic Phase-3b selection over emitted high-signal sub-agent transcripts."""
    pool = []
    for s in sessions:
        for hs in s["subAgents"].get("highSignal", []):
            pool.append(
                {
                    "parentSessionId": s["sessionId"],
                    "file": hs["file"],
                    "transcriptPath": hs["transcriptPath"],
                    "errorCount": sum(hs.get("errorsByCategory", {}).values()),
                    # `bytes` = raw source size (also the rank key, unchanged);
                    # `emittedBytes` = what the analyst will actually read. Both are carried
                    # so a Phase-3b spawn prompt can state the real read budget.
                    "bytes": hs.get("bytes", 0),
                    "emittedBytes": hs.get("emittedBytes", 0),
                }
            )
    ranked = sorted(pool, key=lambda p: (-p["errorCount"], -p["bytes"], p["file"]))
    return {
        "selectionRule": (
            f"all emitted high-signal sub-agents; rank errorCount desc, bytes desc, file; "
            f"top {SUBAGENT_DEEPDIVE_CAP}"
        ),
        "selected": ranked[:SUBAGENT_DEEPDIVE_CAP],
        "overCap": [
            {k: p[k] for k in ("parentSessionId", "file", "errorCount")}
            for p in ranked[SUBAGENT_DEEPDIVE_CAP:]
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


def write_interaction_digest(output_dir, sess, jsonl_path, rereads_min):
    """Write the per-task interaction digest that `task-learnings` Step 0 reads.

    Counted signals are computed here. RE-ASKS ARE DELIBERATELY NOT DETECTED: a re-ask is the
    same request restated in different words, and unlike a correction (which has lexical markers
    — "wrong", "no,", "actually" — that sweep_user_corrections.py greps) it has no marker at all.
    A token-overlap similarity score both false-positives on shared domain vocabulary and misses
    terse restatements. So this emits the user-message SEQUENCE and the reader classifies by
    reading it — judgment where judgment belongs.
    """
    b = sess.get("behavior") or {}
    rereads = [r for r in (b.get("reReads") or []) if r.get("count", 0) >= rereads_min]
    cmds = [
        c
        for c in (b.get("repeatedCommands") or [])
        if c.get("count", 0) >= DIGEST_MIN_OCCURRENCES
    ]
    loops = list(b.get("buildTestLoops") or [])
    stale = b.get("staleReadEdits") or 0
    errors = {
        cat: n
        for cat, n in (sess.get("errorsByCategory") or {}).items()
        if n >= DIGEST_MIN_OCCURRENCES
    }
    msgs = list(iter_operator_turns(jsonl_path))

    signal_count = (
        len(rereads)
        + len(cmds)
        + len(loops)
        + (1 if stale >= DIGEST_MIN_OCCURRENCES else 0)
    )
    ident = _session_identity(jsonl_path)

    L = []
    L.append(f"# Interaction digest — session {ident['sessionId'][:8]}")
    L.append("")
    L.append(f"- Session: `{ident['sessionId']}`")
    L.append(f"- Last activity: {ident['lastActivity']}")
    L.append(f"- Branch: {sess.get('gitBranch') or 'unknown'}")
    L.append(
        f"- Volume: {len(msgs)} operator turns, "
        f"{sess['counts']['toolUse']} tool calls, {sess.get('compactions', 0)} compaction(s)"
    )
    # counts.userMsgs is every user-channel record that carries text, injected text included, so it
    # is not the number of operator turns above; it stays, labelled, because it drives selection.
    L.append(
        f"- User-channel records: {sess['counts']['userMsgs']} (counts.userMsgs; includes skill, "
        "hand-back and compaction text, so it is not a count of operator turns)"
    )
    L.append(
        f"- Re-read threshold applied: >={rereads_min} (see DEFAULT_REREADS_MIN provenance)"
    )
    L.append(f"- Gate: {'SIGNAL' if signal_count or errors else 'NO SIGNAL'}")
    L.append("")
    L.append("## Counted repetition signals")
    L.append("")
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
    L.append("## Agent error classes (>=2 in this session)")
    L.append("")
    if errors:
        L.extend(
            f"- {cat}: {n}" for cat, n in sorted(errors.items(), key=lambda kv: -kv[1])
        )
        L.append("")
        L.append(
            "> Classified by ORIGIN TOOL, which is content-blind by design. Harness-generated "
            "failures (hook denials, usage-limit kills, permission-stream aborts) land in "
            "behavioral buckets and inflate these counts — decompose before treating any of "
            "this as an agent-quality finding."
        )
    else:
        L.append("_None with 2+ occurrences._")
    L.append("")
    L.append(
        f"## User-message sequence ({len(msgs)} total, first {DIGEST_USER_MSG_CAP} shown)"
    )
    L.append("")
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
        f"Wrote {path} — gate={'SIGNAL' if signal_count or errors else 'NO SIGNAL'}, "
        f"{signal_count} repetition signal(s), {len(errors)} error class(es), {len(msgs)} operator turns",
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
        help="scope to ONE session: a session id (or unique prefix), or 'current' for the "
        "most-recently-written transcript. 'current' exits 4 if two transcripts were written "
        "close together, rather than guessing between parallel sessions.",
    )
    ap.add_argument(
        "--digest",
        action="store_true",
        help="also write interaction-digest.md (requires --session); consumed by task-learnings",
    )
    ap.add_argument(
        "--rereads-min",
        type=int,
        default=DEFAULT_REREADS_MIN,
        help=f"minimum re-read count treated as a signal (default {DEFAULT_REREADS_MIN}; "
        "measured range 4-8 — see DEFAULT_REREADS_MIN provenance comment)",
    )
    args = ap.parse_args()

    if args.digest and not args.session:
        print("ERROR: --digest requires --session <id|current>", file=sys.stderr)
        sys.exit(2)

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
    # --since would silently drop it and yield an empty digest that reads as "no signal".
    since = None if args.session else args.since
    until = None if args.session else args.until

    if args.session:
        scoped = resolve_session_scope(session_dir, args.session)
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
    replays = {}  # session id -> repeated events left out of it: for stderr, not the aggregate

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
        except Exception as exc:  # never abort the whole run on one file
            print(f"  ! error processing {f.name}: {exc}", file=sys.stderr)
            continue
        if sess["counts"]["userMsgs"] == 0:
            continue
        # date overlap filter
        if since and sess["endTime"] and sess["endTime"][:10] < since:
            continue
        if until and sess["startTime"] and sess["startTime"][:10] > until:
            continue
        sessions.append(sess)
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

    if args.digest:
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
    for s in sessions:
        sa = s["subAgents"]
        sub_totals["totalAgents"] += sa.get("count", 0)
        sub_totals["agentsWithErrors"] += sa.get("agentsWithErrors", 0)
        sub_totals["transcriptsEmitted"] += sa.get("transcriptsEmitted", 0)
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
        },
        "subAgentErrorTaxonomy": {"byCategory": sub_tax, **sub_totals},
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


def _merge_tools(sessions):
    merged = defaultdict(int)
    for s in sessions:
        for t, n in s["toolsUsed"].items():
            merged[t] += n
    return dict(sorted(merged.items(), key=lambda x: -x[1]))


def _invocation_modes(sessions):
    """Per-skill invocation counts by mode (v4, C-2): user = /slash, model = Skill tool."""
    modes = defaultdict(lambda: {"user": 0, "model": 0})
    for s in sessions:
        for si in s["skillInvocations"]:
            modes[si["skill"]]["model"] += 1
        for sc in s["slashCommands"]:
            modes[sc["command"]]["user"] += 1
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
