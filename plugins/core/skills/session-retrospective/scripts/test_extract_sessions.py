"""Unit tests for the behavioral session extractor.

Pure stdlib, no DB / service / migration dependencies, so this does NOT require the project's
Docker/CI test harness. Run with:

    uv run python -m pytest "${CLAUDE_SKILL_DIR}/scripts/test_extract_sessions.py"
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import extract_sessions as ex  # noqa: E402


# --- redaction ------------------------------------------------------------------------------
def test_redaction_masks_secret_shapes():
    raw = (
        "key sk-ant-abcdefghij1234567890XYZ token "
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY.SflKxwRJSMeKKF2QT4 "
        "Authorization: Bearer abcdef1234567890ghij "
        'config "private_key": "-----BEGIN PRIVATE KEY-----MIIabc-----END PRIVATE KEY-----" '
        "OPENAI_API_KEY=supersecretvalue123 "
        "google AIzaSyA1234567890abcdefghij1234567890 path C:\\Users\\someuser\\Documents\\x "
        "mangled c:UsersomeuserDocumentsProjectsexample-project"
    )
    out = ex.redact(raw)
    assert "sk-ant-" not in out
    assert "eyJhbGci" not in out
    assert "supersecretvalue123" not in out
    assert "AIzaSy" not in out
    assert "-----BEGIN PRIVATE KEY-----" not in out
    assert (
        "someuser" not in out
    )  # home dir masked (generic placeholder, not a real username)
    assert "REDACTED" in out


def test_redaction_is_idempotent():
    raw = "OPENAI_API_KEY=secretsecret123 sk-abcdefghij1234567890"
    assert ex.redact(ex.redact(raw)) == ex.redact(raw)


# --- session-dir auto-derivation (portability) ----------------------------------------------
def test_encode_repo_path_replaces_separators():
    # "/", "\" and ":" all collapse to "-" — mirrors how Claude Code names ~/.claude/projects/<dir>.
    # Path normalizes "/"->"\" on Windows and keeps "/" on POSIX; replacing BOTH makes it stable.
    assert (
        ex._encode_repo_path(Path("/home/alice/example-project"))
        == "-home-alice-example-project"
    )
    enc = ex._encode_repo_path(Path("C:/Users/x/proj"))
    assert not any(c in enc for c in "/\\:")
    assert enc.casefold() == "c--users-x-proj"


def test_find_session_dir_exact_and_case_insensitive(tmp_path):
    base = tmp_path / "projects"
    base.mkdir()
    # on-disk dir uses a lowercase drive ("c--…"); Path.resolve() may yield an uppercase "C:" — the
    # case-insensitive fallback must still resolve it to the dir that actually exists.
    target = base / "c--Users-x-proj"
    target.mkdir()
    found = ex._find_session_dir(Path("C:/Users/x/proj"), base)
    assert found is not None
    # Compare filesystem identity, not resolved-path strings: on a case-insensitive filesystem
    # (macOS APFS, Windows) the exact-match branch may return the queried casing rather than the
    # on-disk casing, and resolve() does not normalize case.
    assert found.samefile(target)


def test_find_session_dir_returns_none_when_absent(tmp_path):
    base = tmp_path / "projects"
    base.mkdir()
    assert ex._find_session_dir(Path("/no/such/repo"), base) is None


# --- error classification by ORIGIN tool ----------------------------------------------------
def test_content_tool_with_error_word_is_not_an_error():
    # The core false-positive fix: Read returning file content containing "Error:" is DATA.
    assert (
        ex.classify_error("Read", False, "line 1\nraise ValueError: boom\nFAILED test")
        is None
    )
    assert ex.classify_error("Grep", False, "match: Error: handling here") is None
    assert (
        ex.classify_error("WebFetch", False, "the page says Exit code 1 somewhere")
        is None
    )


def test_genuine_errors_get_correct_category():
    assert ex.classify_error("Read", True, "File does not exist.") == "path-not-found"
    assert (
        ex.classify_error("Edit", True, "File has been modified since read")
        == "edit-stale-read"
    )
    assert (
        ex.classify_error("Write", True, "File has not been read yet")
        == "edit-stale-read"
    )
    assert (
        ex.classify_error("Bash", False, "Exit code 1\nruff check failed")
        == "build-compile"
    )
    assert (
        ex.classify_error("Bash", False, "Exit code 1\npytest: 1 failed")
        == "test-failure"
    )
    assert ex.classify_error("Skill", True, "skill is disabled") == "skill-blocked"
    assert (
        ex.classify_error("Bash", False, "Exit code 127\ncommand not found")
        == "runtime-exit"
    )
    assert ex.classify_error("TodoWrite", True, "boom") == "tool-error"


def test_user_rejection_is_separate_bucket():
    assert (
        ex.classify_error(
            "Bash", True, "The user doesn't want to proceed with this tool use"
        )
        == "user-rejected"
    )
    assert ex.classify_error("Edit", True, "user rejected the edit") == "user-rejected"


def test_exit_code_zero_is_not_an_error():
    assert ex.classify_error("Bash", False, "done\nExit code 0") is None


# --- end-to-end -----------------------------------------------------------------------------
def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _run(session_dir, out_dir, monkeypatch, self_check=True):
    argv = ["extract_sessions.py", str(session_dir), str(out_dir)]
    if self_check:
        argv.append("--self-check")
    monkeypatch.setattr(sys, "argv", argv)
    ex.main()
    return json.loads((out_dir / "aggregate.json").read_text(encoding="utf-8"))


def test_end_to_end(tmp_path, monkeypatch):
    sdir = tmp_path / "sessions_src"
    sdir.mkdir()
    sid = "aaaaaaaa-1111-2222-3333-444444444444"

    rows = [
        {"type": "ai-title", "aiTitle": "Test session"},
        {
            "type": "user",
            "timestamp": "2026-06-20T10:00:00Z",
            "gitBranch": "main",
            "message": {"content": [{"type": "text", "text": "please fix the bug"}]},
        },
        {
            "type": "assistant",
            "timestamp": "2026-06-20T10:00:01Z",
            "message": {
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "let me reconsider, actually wait",
                    },
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Read",
                        "input": {"file_path": "/repo/a.py"},
                    },
                ]
            },
        },
        # content tool returns text containing "Error:" with is_error false -> NOT an error
        {
            "type": "user",
            "timestamp": "2026-06-20T10:00:02Z",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": "def f():\n  raise ValueError: nope\nError: sample",
                        "is_error": False,
                    }
                ]
            },
        },
        {
            "type": "assistant",
            "timestamp": "2026-06-20T10:00:03Z",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t2",
                        "name": "Edit",
                        "input": {"file_path": "/repo/a.py"},
                    }
                ]
            },
        },
        # genuine stale-read error
        {
            "type": "user",
            "timestamp": "2026-06-20T10:00:04Z",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t2",
                        "content": "File has been modified since read",
                        "is_error": True,
                    }
                ]
            },
        },
        # blocked skill
        {
            "type": "assistant",
            "timestamp": "2026-06-20T10:00:05Z",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t3",
                        "name": "Skill",
                        "input": {"skill": "plan-critic"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "timestamp": "2026-06-20T10:00:06Z",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t3",
                        "content": "disabled",
                        "is_error": True,
                    }
                ]
            },
        },
        # AskUserQuestion capture
        {
            "type": "assistant",
            "timestamp": "2026-06-20T10:00:07Z",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t4",
                        "name": "AskUserQuestion",
                        "input": {
                            "questions": [{"question": "Which approach do you prefer?"}]
                        },
                    }
                ]
            },
        },
        "a bare JSON string line (valid JSON, non-object) must be skipped",
    ]
    _write_jsonl(sdir / f"{sid}.jsonl", rows)
    # append a TRULY malformed (non-JSON) line — must be skipped without dropping the session
    with open(sdir / f"{sid}.jsonl", "a", encoding="utf-8") as fh:
        fh.write("THIS IS NOT JSON {{{\n")

    # session with zero real user messages -> must be skipped
    _write_jsonl(
        sdir / "bbbbbbbb-0000.jsonl",
        [
            {
                "type": "assistant",
                "timestamp": "2026-06-20T09:00:00Z",
                "message": {"content": [{"type": "text", "text": "hi"}]},
            },
        ],
    )

    # nested sub-agent transcript + meta sidecar
    subdir = sdir / sid / "subagents"
    subdir.mkdir(parents=True)
    _write_jsonl(
        subdir / "agent-x.jsonl",
        [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "sub goal"}]},
            },
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "sub work"}]},
            },
        ],
    )
    (subdir / "agent-x.meta.json").write_text(
        json.dumps({"agentType": "Explore", "description": "find files"}),
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    agg = _run(sdir, out_dir, monkeypatch)

    # schema contract
    for k in ex.SCHEMA_KEYS["top"]:
        assert k in agg
    assert agg["schemaVersion"] == ex.SCHEMA_VERSION
    assert len(agg["sessions"]) == 1, "0-user session must be skipped"
    s = agg["sessions"][0]
    for k in ex.SCHEMA_KEYS["session"]:
        assert k in s

    # false positive eliminated: the Read content with 'Error:' is NOT counted
    assert agg["errorTaxonomy"]["byCategory"]["tool-error"]["count"] == 0
    assert agg["errorTaxonomy"]["byCategory"]["edit-stale-read"]["count"] == 1
    assert s["errorsByCategory"].get("edit-stale-read") == 1
    assert s["behavior"]["staleReadEdits"] == 1

    # captures
    assert s["counts"]["userMsgs"] == 1
    assert "Which approach do you prefer?" in s["askUserQuestions"]
    assert any(
        si["skill"] == "plan-critic" and si["blocked"] for si in s["skillInvocations"]
    )
    assert s["backtrackingMarkers"] >= 2  # "let me reconsider", "actually", "wait"

    # sub-agent walk + meta sidecar
    assert s["subAgents"]["count"] == 1
    assert s["subAgents"]["agents"][0]["type"] == "Explore"
    assert agg["stats"]["subAgent"]["files"] == 1
    # a no-error sub-agent is still emitted as a top-by-bytes high-signal transcript
    assert s["subAgents"]["errorsByCategory"] == {}
    assert s["subAgents"]["transcriptsEmitted"] == 1
    hs = s["subAgents"]["highSignal"][0]
    assert Path(hs["transcriptPath"]).is_file()

    # `bytes` is the RAW source size; `emittedBytes` is the redacted digest actually on disk.
    # Regression guard: the 2026-08-01 retro found 4 of 6 analysts budgeting reads from `bytes`
    # (400-700 KB) for files that were 10-13 KB, because only `bytes` was reported. Assert both
    # exist AND that emittedBytes tracks the real file — not a copy of `bytes`.
    # Exact file size is the strong guard: a field that merely copied `bytes` could not satisfy
    # it. NOTE: `emittedBytes < bytes` is deliberately NOT asserted — it is not an invariant.
    # The emitted file carries a ~150-byte header, so for a small transcript the digest is
    # LARGER than its source (this fixture: 195 emitted vs 169 raw). The size cap only bites on
    # real transcripts, where the ratio runs 1.6-2.6%.
    assert hs["emittedBytes"] == Path(hs["transcriptPath"]).stat().st_size
    assert hs["emittedBytes"] > 0
    sel = agg["subAgentDeepDiveCandidates"]["selected"]
    assert sel and all("emittedBytes" in c and "bytes" in c for c in sel)

    # transcript artifact written + absolute path
    assert Path(s["transcriptPath"]).is_file()
    assert (out_dir / "sessions").glob("*.md")


def test_output_dir_rejects_system_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["extract_sessions.py", str(tmp_path), "/tmp/retro"]
    )
    with pytest.raises(SystemExit):
        ex.main()


def test_main_omitting_session_dir_uses_autoderivation(tmp_path, monkeypatch):
    # When the session_dir positional is OMITTED, main() must call _derive_session_dir() — not treat
    # output_dir as the session dir. Monkeypatch the derivation to a controlled fixture so the test
    # is deterministic (no dependency on the real ~/.claude/projects/ layout).
    sdir = tmp_path / "derived_src"
    sdir.mkdir()
    _write_jsonl(
        sdir / "dddddddd-1111-2222-3333-666666666666.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2026-06-20T10:00:00Z",
                "gitBranch": "main",
                "message": {"content": [{"type": "text", "text": "hello"}]},
            }
        ],
    )
    monkeypatch.setattr(ex, "_derive_session_dir", lambda: sdir)
    out_dir = tmp_path / "out"
    # ONE positional only (output_dir) — the omitted session_dir forces the derivation branch.
    monkeypatch.setattr(
        sys, "argv", ["extract_sessions.py", str(out_dir), "--self-check"]
    )
    ex.main()
    agg = json.loads((out_dir / "aggregate.json").read_text(encoding="utf-8"))
    assert agg["stats"]["totalSessions"] == 1
    assert agg["generatedFor"]["sessionDir"] == str(sdir)


def test_self_check_detects_a_leak(tmp_path):
    # write an artifact with an unredacted secret and confirm the leak gate catches it
    (tmp_path / "sessions").mkdir()
    (tmp_path / "aggregate.json").write_text(
        '{"x":"sk-abcdefghij1234567890leak"}', encoding="utf-8"
    )
    leaks = ex.self_check(tmp_path)
    assert leaks, "self_check must flag an unredacted sk- key"


def test_self_check_scans_emitted_subagent_transcripts(tmp_path):
    # a leak inside an emitted sub-agent transcript must also be caught (rglob coverage)
    sub = tmp_path / "sessions" / "sub" / "sid"
    sub.mkdir(parents=True)
    (tmp_path / "aggregate.json").write_text("{}", encoding="utf-8")
    (sub / "agent-1.md").write_text(
        "ASSISTANT: leaked sk-abcdefghij1234567890SECRET", encoding="utf-8"
    )
    leaks = ex.self_check(tmp_path)
    assert leaks, (
        "self_check must scan sessions/sub/**/*.md, not just top-level transcripts"
    )


def test_subagent_taxonomy_emission_and_redaction(tmp_path, monkeypatch):
    """Sub-agent internals: errors are classified + counted, a redacted transcript is emitted for
    high-signal agents, the emitted transcript is redacted, and --self-check covers it."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "cccccccc-1111-2222-3333-555555555555"
    _write_jsonl(
        sdir / f"{sid}.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2026-06-20T10:00:00Z",
                "gitBranch": "main",
                "message": {"content": [{"type": "text", "text": "do research"}]},
            },
            {
                "type": "assistant",
                "timestamp": "2026-06-20T10:00:01Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "a1",
                            "name": "Agent",
                            "input": {"description": "verify sources"},
                        }
                    ]
                },
            },
        ],
    )
    # sub-agent transcript: a path-not-found error + a SECRET in the tool output
    subdir = sdir / sid / "subagents"
    subdir.mkdir(parents=True)
    _write_jsonl(
        subdir / "agent-1.jsonl",
        [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "verify sources"}]},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "r1",
                            "name": "Read",
                            "input": {"file_path": "/repo/missing.md"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "r1",
                            "content": "File does not exist. token sk-abcdefghij1234567890SECRET",
                            "is_error": True,
                        }
                    ]
                },
            },
        ],
    )
    (subdir / "agent-1.meta.json").write_text(
        json.dumps({"agentType": "general-purpose", "description": "verify sources"}),
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    # _run passes --self-check → main() sys.exit(3) if the emitted sub-agent transcript leaks
    agg = _run(sdir, out_dir, monkeypatch)

    # taxonomy rolled up to the aggregate
    assert agg["subAgentErrorTaxonomy"]["byCategory"]["path-not-found"]["count"] == 1
    assert agg["subAgentErrorTaxonomy"]["totalAgents"] == 1
    assert agg["subAgentErrorTaxonomy"]["agentsWithErrors"] == 1
    assert agg["subAgentErrorTaxonomy"]["transcriptsEmitted"] == 1

    s = agg["sessions"][0]
    assert s["subAgents"]["errorsByCategory"].get("path-not-found") == 1
    assert s["subAgents"]["agentsWithErrors"] == 1
    assert s["subAgents"]["transcriptsEmitted"] == 1

    # emitted transcript exists at an absolute path AND is redacted
    hs = s["subAgents"]["highSignal"]
    assert len(hs) == 1
    sub_md = Path(hs[0]["transcriptPath"])
    assert sub_md.is_file()
    body = sub_md.read_text(encoding="utf-8")
    assert "sk-abcdefghij" not in body, (
        "secret must be redacted in emitted sub-agent transcript"
    )
    assert "ERROR(path-not-found)" in body
    assert not ex.self_check(out_dir), "no leaks expected after redaction"


# --- schema v4 additions ----------------------------------------------------------------------
def _minimal_session_rows(ts="2026-06-20T10:00:00Z", extra=None):
    rows = [
        {
            "type": "user",
            "timestamp": ts,
            "gitBranch": "main",
            "message": {"content": [{"type": "text", "text": "hello agent"}]},
        },
    ]
    rows.extend(extra or [])
    return rows


def test_slash_commands_captured_and_merged(tmp_path, monkeypatch):
    """v4 (C-2): user-typed /skill runs (<command-name> pseudo-user messages) are captured per
    session and merged into stats.skillsUsed with an invocation-mode breakdown."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    cmd_text = (
        "<command-name>/session-retrospective</command-name>\n"
        "<command-message>session-retrospective</command-message>\n"
        "<command-args>--since 2026-06-01</command-args>"
    )
    rows = _minimal_session_rows(
        extra=[
            {
                "type": "user",
                "timestamp": "2026-06-20T10:00:05Z",
                "message": {"content": [{"type": "text", "text": cmd_text}]},
            },
        ]
    )
    _write_jsonl(sdir / "eeeeeeee-1111-2222-3333-777777777777.jsonl", rows)
    agg = _run(sdir, tmp_path / "out", monkeypatch)

    s = agg["sessions"][0]
    assert s["slashCommands"] == [
        {"command": "session-retrospective", "args": "--since 2026-06-01"}
    ]
    assert s["counts"]["userMsgs"] == 1, "command pseudo-message must NOT count as a userMsg"
    assert "session-retrospective" in agg["stats"]["skillsUsed"]
    assert agg["stats"]["skillInvocationModes"]["session-retrospective"] == {
        "user": 1,
        "model": 0,
    }


def test_models_and_compactions_captured(tmp_path, monkeypatch):
    """v4 (C-4): per-session assistant model ids and compact_boundary count."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    rows = _minimal_session_rows(
        extra=[
            {
                "type": "assistant",
                "timestamp": "2026-06-20T10:00:01Z",
                "message": {
                    "model": "claude-fable-5",
                    "content": [{"type": "text", "text": "working on it"}],
                },
            },
            {"type": "system", "subtype": "compact_boundary", "compactMetadata": {}},
            {"type": "system", "subtype": "compact_boundary", "compactMetadata": {}},
        ]
    )
    _write_jsonl(sdir / "ffffffff-1111-2222-3333-888888888888.jsonl", rows)
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    s = agg["sessions"][0]
    assert s["models"] == {"claude-fable-5": 1}
    assert s["compactions"] == 2


def test_deep_dive_candidate_selection_rule():
    """v4 (C-1): deterministic Phase-3 selection — qualify, rank, cap, no silent drop."""

    def fake(sid, tool_use, user_msgs=0, tbytes=0):
        return {
            "sessionId": sid,
            "transcriptPath": f"/abs/{sid}.md",
            "counts": {"toolUse": tool_use, "userMsgs": user_msgs},
            "transcriptBytes": tbytes,
        }

    sessions = [fake(f"s{i:02d}", 100 - i) for i in range(9)]  # 9 qualifiers by toolUse
    sessions.append(fake("s-low", 3, user_msgs=1))  # does not qualify
    sessions.append(fake("s-msgs", 3, user_msgs=6))  # qualifies via userMsgs
    result = ex.select_deep_dive(sessions)
    assert len(result["selected"]) == ex.DEEP_DIVE_CAP
    assert [c["sessionId"] for c in result["selected"]] == [f"s{i:02d}" for i in range(8)]
    over = {c["sessionId"] for c in result["overCap"]}
    assert over == {"s08", "s-msgs"}, "qualifiers beyond the cap must be listed, not dropped"
    assert "toolUse" in result["selectionRule"]
    # tie-break: equal toolUse -> larger transcriptBytes first
    tied = [fake("a", 50, tbytes=10), fake("b", 50, tbytes=99)]
    sel = ex.select_deep_dive(tied)["selected"]
    assert [c["sessionId"] for c in sel] == ["b", "a"]


def test_subagent_deep_dive_and_error_agents_not_emitted(tmp_path, monkeypatch):
    """v4 (C-8 + C-1): with more error-bearing sub-agents than the emission cap, the overflow
    count is recorded per session, and the aggregate emits a ranked, capped candidate list."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "99999999-1111-2222-3333-000000000000"
    _write_jsonl(sdir / f"{sid}.jsonl", _minimal_session_rows())
    subdir = sdir / sid / "subagents"
    subdir.mkdir(parents=True)
    n_agents = 10
    for i in range(n_agents):
        _write_jsonl(
            subdir / f"agent-{i:02d}.jsonl",
            [
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "r1",
                                "name": "Read",
                                "input": {"file_path": f"/repo/missing-{i}.md"},
                            }
                        ]
                    },
                },
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "r1",
                                "content": "File does not exist." + "x" * (i * 10),
                                "is_error": True,
                            }
                        ]
                    },
                },
            ],
        )
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    s = agg["sessions"][0]
    assert s["subAgents"]["agentsWithErrors"] == n_agents
    assert s["subAgents"]["transcriptsEmitted"] == ex.MAX_SUBAGENT_EMIT_PER_SESSION
    assert (
        s["subAgents"]["errorAgentsNotEmitted"]
        == n_agents - ex.MAX_SUBAGENT_EMIT_PER_SESSION
    )
    cands = agg["subAgentDeepDiveCandidates"]
    assert len(cands["selected"]) == ex.SUBAGENT_DEEPDIVE_CAP
    assert (
        len(cands["overCap"])
        == ex.MAX_SUBAGENT_EMIT_PER_SESSION - ex.SUBAGENT_DEEPDIVE_CAP
    )
    assert all(Path(c["transcriptPath"]).is_file() for c in cands["selected"])


def test_check_file_gate(tmp_path, monkeypatch):
    """v4 (C-7): --check-file runs the leak patterns over one file (report-privacy gate)."""
    leaky = tmp_path / "draft.md"
    leaky.write_text("finding cites sk-abcdefghij1234567890LEAK", encoding="utf-8")
    clean = tmp_path / "clean.md"
    clean.write_text("all findings redacted", encoding="utf-8")

    assert ex.check_file(leaky), "leak must be detected"
    assert ex.check_file(clean) == []
    assert ex.check_file(tmp_path / "missing.md"), "unreadable target fails closed"

    monkeypatch.setattr(sys, "argv", ["extract_sessions.py", "--check-file", str(leaky)])
    with pytest.raises(SystemExit) as exc:
        ex.main()
    assert exc.value.code == 3
    monkeypatch.setattr(sys, "argv", ["extract_sessions.py", "--check-file", str(clean)])
    ex.main()  # returns without SystemExit


def test_prescan_skips_out_of_range_and_falls_back(tmp_path, monkeypatch):
    """v4 (C-3): clearly out-of-range sessions are skipped BEFORE processing (no transcript
    written); sessions with undeterminable dates are still fully parsed (never silently skipped)."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    _write_jsonl(
        sdir / "old00000-1111-2222-3333-111111111111.jsonl",
        _minimal_session_rows(ts="2026-01-05T10:00:00Z"),
    )
    _write_jsonl(
        sdir / "new00000-1111-2222-3333-222222222222.jsonl",
        _minimal_session_rows(ts="2026-06-20T10:00:00Z"),
    )
    # no timestamps at all -> prescan undeterminable -> full parse -> included
    _write_jsonl(
        sdir / "nots0000-1111-2222-3333-333333333333.jsonl",
        [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "hi there"}]},
            }
        ],
    )
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        ["extract_sessions.py", str(sdir), str(out_dir), "--since", "2026-06-01"],
    )
    ex.main()
    agg = json.loads((out_dir / "aggregate.json").read_text(encoding="utf-8"))
    ids = {s["sessionId"][:8] for s in agg["sessions"]}
    assert ids == {"new00000", "nots0000"}
    written = {p.stem[:8] for p in (out_dir / "sessions").glob("*.md")}
    assert "old00000" not in written, "out-of-range session must be skipped pre-parse"


def test_stale_transcripts_cleared_between_runs(tmp_path, monkeypatch):
    """v4 (C-3): leftover transcripts from a previous run are cleared (with a notice), so
    Phase-5 grep verification can't hit stale files."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    _write_jsonl(
        sdir / "aaaa0000-1111-2222-3333-444444444444.jsonl", _minimal_session_rows()
    )
    out_dir = tmp_path / "out"
    _run(sdir, out_dir, monkeypatch)
    stale = out_dir / "sessions" / "stale-leftover.md"
    stale.write_text("from an old run", encoding="utf-8")
    _run(sdir, out_dir, monkeypatch)
    assert not stale.exists()
    assert list((out_dir / "sessions").glob("*.md")), "fresh transcripts still written"


# --- session scoping + interaction digest ---------------------------------------------------
def _user_session(dirpath, sid, texts, mtime=None):
    """Minimal one-session transcript of user turns; optionally pin mtime for scope tests."""
    p = dirpath / f"{sid}.jsonl"
    _write_jsonl(
        p,
        [
            {
                "type": "user",
                "timestamp": "2026-08-14T00:00:00Z",
                "gitBranch": "test-branch",
                "message": {"content": [{"type": "text", "text": t}]},
            }
            for t in texts
        ],
    )
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def _fake_sess(rereads=(), cmds=(), errors=None):
    return {
        "sessionId": "aaaa1111-0000-0000-0000-000000000000",
        "gitBranch": "test-branch",
        "counts": {
            "userMsgs": 4,
            "assistantMsgs": 4,
            "toolUse": 30,
            "toolResult": 30,
            "thinking": 2,
        },
        "compactions": 0,
        "errorsByCategory": dict(errors or {}),
        "behavior": {
            "reReads": [{"file": f, "count": c} for f, c in rereads],
            "repeatedCommands": [{"cmd": c, "count": n} for c, n in cmds],
            "buildTestLoops": [],
            "staleReadEdits": 0,
        },
    }


def test_resolve_session_scope_exact_and_unique_prefix(tmp_path):
    _user_session(tmp_path, "aaaa1111-0000-0000-0000-000000000000", ["a"], mtime=1000)
    _user_session(tmp_path, "bbbb2222-0000-0000-0000-000000000000", ["b"], mtime=2000)
    exact = ex.resolve_session_scope(tmp_path, "aaaa1111-0000-0000-0000-000000000000")
    assert exact.stem.startswith("aaaa1111")
    assert ex.resolve_session_scope(tmp_path, "bbbb2222").stem.startswith("bbbb2222")


def test_resolve_session_scope_unknown_id_exits(tmp_path):
    _user_session(tmp_path, "aaaa1111-0000-0000-0000-000000000000", ["a"], mtime=1000)
    with pytest.raises(SystemExit) as e:
        ex.resolve_session_scope(tmp_path, "does-not-exist")
    assert e.value.code == 2


def test_resolve_session_scope_ambiguous_prefix_exits(tmp_path):
    _user_session(tmp_path, "dupe-aaaa", ["a"], mtime=1000)
    _user_session(tmp_path, "dupe-bbbb", ["b"], mtime=2000)
    with pytest.raises(SystemExit) as e:
        ex.resolve_session_scope(tmp_path, "dupe")
    assert e.value.code == 2


def test_resolve_session_current_fails_closed_when_ambiguous(tmp_path):
    """The load-bearing safety property.

    Parallel sessions are routine in this checkout — verified live on 2026-08-14, where FOUR
    transcripts had been written within 180s and newest-mtime pointed at an unrelated session.
    Guessing would produce a learnings entry confidently describing work this session never did,
    so ambiguity must fail closed rather than pick.
    """
    now = 1_700_000_000
    _user_session(tmp_path, "aaaa1111-mine", ["mine"], mtime=now)
    _user_session(tmp_path, "bbbb2222-theirs", ["theirs"], mtime=now - 5)
    with pytest.raises(SystemExit) as e:
        ex.resolve_session_scope(tmp_path, "current")
    assert e.value.code == 4, "ambiguous 'current' must exit 4, not silently pick the newest"


def test_resolve_session_current_picks_newest_when_unambiguous(tmp_path):
    now = 1_700_000_000
    _user_session(
        tmp_path, "aaaa1111-old", ["old"], mtime=now - ex.CURRENT_AMBIGUITY_WINDOW_S - 60
    )
    newest = _user_session(tmp_path, "bbbb2222-new", ["new"], mtime=now)
    assert ex.resolve_session_scope(tmp_path, "current") == newest


def test_is_human_turn_filters_injected_machinery():
    # Measured on a live session: 4 of 10 user-channel messages were these shapes, enough to
    # make the re-ask read useless (a reader would be scanning skill prose, not human asks).
    assert ex._is_human_turn("please fix the failing test")
    assert not ex._is_human_turn("Base directory for this skill: /x/y\n# Some Skill")
    assert not ex._is_human_turn("<task-notification>done</task-notification>")
    assert not ex._is_human_turn("ARGUMENTS: --since 2026-01-01")
    assert not ex._is_human_turn("")


def test_digest_applies_the_reread_threshold(tmp_path):
    jf = _user_session(tmp_path, "aaaa1111-0000-0000-0000-000000000000", ["do the thing"])
    out = tmp_path / "out"
    out.mkdir()
    ex.write_interaction_digest(
        out,
        _fake_sess(rereads=[("kept.py", 6), ("dropped.py", 3)]),
        jf,
        ex.DEFAULT_REREADS_MIN,
    )
    text = (out / "interaction-digest.md").read_text(encoding="utf-8")
    assert "kept.py" in text
    # A count of exactly 3 is the MODE (63 of 137 measured) and is most likely the
    # AGENTS.md-mandated read->edit->re-read cycle: compliance, not thrash.
    assert "dropped.py" not in text


def test_digest_reread_threshold_is_a_parameter(tmp_path):
    """The measured data localizes the cut to 4-8 without picking one value inside it, so the
    threshold must be caller-supplied — a constant would freeze an unproven choice."""
    jf = _user_session(tmp_path, "cccc3333-0000-0000-0000-000000000000", ["go"])
    out = tmp_path / "out"
    out.mkdir()
    sess = _fake_sess(rereads=[("borderline.py", 5)])
    ex.write_interaction_digest(out, sess, jf, 4)
    assert "borderline.py" in (out / "interaction-digest.md").read_text(encoding="utf-8")
    ex.write_interaction_digest(out, sess, jf, 8)
    assert "borderline.py" not in (out / "interaction-digest.md").read_text(encoding="utf-8")


def test_digest_excludes_harness_noise_and_carries_evidence_rules(tmp_path):
    jf = _user_session(
        tmp_path,
        "dddd4444-0000-0000-0000-000000000000",
        [
            "real ask one",
            "Base directory for this skill: /x\n# Skill body",
            "<task-notification>x</task-notification>",
            "real ask two",
        ],
    )
    out = tmp_path / "out"
    out.mkdir()
    ex.write_interaction_digest(out, _fake_sess(), jf, ex.DEFAULT_REREADS_MIN)
    text = (out / "interaction-digest.md").read_text(encoding="utf-8")
    assert "real ask one" in text
    assert "real ask two" in text
    assert "Base directory for this skill" not in text
    assert "task-notification" not in text
    assert "User-message sequence (2 total" in text
    # These rules are the only thing standing between the digest and an unverifiable entry.
    assert "must be locatable in this file" in text
    assert "At most 2 entries per task" in text


def test_digest_error_classes_require_two_occurrences(tmp_path):
    jf = _user_session(tmp_path, "eeee5555-0000-0000-0000-000000000000", ["x"])
    out = tmp_path / "out"
    out.mkdir()
    ex.write_interaction_digest(
        out,
        _fake_sess(errors={"edit-stale-read": 3, "path-not-found": 1}),
        jf,
        ex.DEFAULT_REREADS_MIN,
    )
    text = (out / "interaction-digest.md").read_text(encoding="utf-8")
    assert "edit-stale-read: 3" in text
    assert "path-not-found" not in text
    # The origin-tool classifier is content-blind, so the digest must warn before these counts
    # get read as agent quality (hook denials / usage kills land in behavioral buckets).
    assert "content-blind" in text


def test_self_check_covers_the_interaction_digest(tmp_path):
    """The digest quotes user messages verbatim, making it the highest-risk emitted artifact.
    Omitting it from the leak gate would be SILENT — the run would still print PASSED."""
    out = tmp_path / "out"
    out.mkdir()
    (out / "interaction-digest.md").write_text(
        "1. my key is sk-ant-abcdefghij1234567890XYZ\n", encoding="utf-8"
    )
    assert ex.self_check(out), "a secret in the digest must be caught by self_check"


def test_cli_digest_requires_session(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["extract_sessions.py", str(tmp_path / "out"), "--digest"]
    )
    with pytest.raises(SystemExit) as e:
        ex.main()
    assert e.value.code == 2


def test_cli_session_scope_writes_digest_and_overrides_date_filter(tmp_path, monkeypatch):
    """--session overrides --since: the caller named the session, so a stale date window must
    not silently drop it and yield an empty digest that reads as 'no signal'."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    _user_session(sdir, "ffff6666-0000-0000-0000-000000000000", ["the only ask"])
    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_sessions.py",
            str(sdir),
            str(out),
            "--session",
            "ffff6666",
            "--digest",
            "--since",
            "2030-01-01",
            "--self-check",
        ],
    )
    ex.main()
    text = (out / "interaction-digest.md").read_text(encoding="utf-8")
    assert "the only ask" in text
    assert "ffff6666" in text
