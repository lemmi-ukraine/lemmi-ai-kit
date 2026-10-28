"""Unit tests for the user-corrections sweep and for its link to the extractor's skip list.

The sweep reads the `USER:` blocks the extractor writes into sessions/<id>.md. Two lists decide
which of those blocks are injected machinery rather than the operator speaking:
HARNESS_USER_PREFIXES in extract_sessions.py (the interaction digest) and SKIP_PREFIX in
sweep_user_corrections.py (the sweep). They are duplicated, because the scripts run as
stand-alone files and cannot import each other, and the comment above HARNESS_USER_PREFIXES says
they must move together. The parity test below is what enforces that.

Pure stdlib, no network. Run with:

    uv run python -m pytest "${CLAUDE_SKILL_DIR}/scripts/test_sweep_user_corrections.py"
"""

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent


def _load(name):
    """Import a sibling script BY PATH, so the two scripts never have to import each other."""
    spec = importlib.util.spec_from_file_location(
        f"{name}_under_test", _SCRIPTS / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ex = _load("extract_sessions")
sweep = _load("sweep_user_corrections")

# The machinery prefixes both lists carried before the four below were added.
_ORIGINAL_PREFIXES = (
    "<",
    "Base directory for this skill",
    "ARGUMENTS:",
    "[Request interrupted",
    "Caveat:",
)
# The four harness-injected user events, as the first line a real transcript carries.
_INJECTED_PREFIXES = (
    "# Workflow authoring reference",
    "This session is being continued from a previous conversation",
    "Another Claude session sent a message",
    "Your response above was stopped by a safety classifier",
)
# Synthetic full turns that begin with each of them. Every body carries a word the sweep looks
# for, so a turn that is not skipped surfaces as a correction candidate.
_INJECTED_TURNS = {
    "workflow-authoring header": "\n\n".join(
        [
            "# Workflow authoring reference",
            "Read this before you change a script. Never rely on memory; fix gaps instead.",
        ]
    ),
    "session-continuation notice": "\n\n".join(
        [
            "This session is being continued from a previous conversation that ran out "
            "of context.",
            "Summary: fix the build, do not revert the migration.",
        ]
    ),
    "peer-message notice": "\n\n".join(
        [
            "Another Claude session sent a message:",
            "please do not change the schema, fix the test again",
        ]
    ),
    "safety-classifier stop notice": (
        "Your response above was stopped by a safety classifier — this is not a tool or "
        "API error. Do not produce that content again, even reworded."
    ),
}


def _unshared(first, second):
    """The prefixes that sit in exactly one of two skip lists."""
    return set(first) ^ set(second)


def test_the_two_skip_lists_are_equal_as_sets():
    both = (ex.HARNESS_USER_PREFIXES, sweep.SKIP_PREFIX)
    assert all(both), "two empty lists would compare equal and prove nothing"
    unshared = _unshared(*both)
    assert not unshared, (
        f"only one of HARNESS_USER_PREFIXES / SKIP_PREFIX has {sorted(unshared)}: "
        "the two lists must move together"
    )
    for skip_list in both:
        assert len(set(skip_list)) == len(skip_list), (
            "a duplicate entry is a stale copy"
        )


@pytest.mark.parametrize("lacking", ["extractor", "sweep"])
def test_the_parity_check_names_a_prefix_missing_from_either_list(lacking, monkeypatch):
    """Known positive: remove one prefix from one list and the comparison must name it."""
    dropped = "Caveat:"
    module, name = {
        "extractor": (ex, "HARNESS_USER_PREFIXES"),
        "sweep": (sweep, "SKIP_PREFIX"),
    }[lacking]
    assert dropped in getattr(module, name)
    monkeypatch.setattr(
        module, name, tuple(p for p in getattr(module, name) if p != dropped)
    )
    assert dropped in _unshared(ex.HARNESS_USER_PREFIXES, sweep.SKIP_PREFIX)


@pytest.mark.parametrize("prefix", [*_ORIGINAL_PREFIXES, *_INJECTED_PREFIXES])
def test_each_known_prefix_is_in_both_skip_lists(prefix):
    assert prefix in ex.HARNESS_USER_PREFIXES
    assert prefix in sweep.SKIP_PREFIX


def _sweep(tmp_path, turns):
    """Run the real sweep over one transcript whose USER blocks are `turns`."""
    sessions = tmp_path / "retro" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    lines = []
    for turn in turns:
        lines.append(f"USER: {turn}")
        lines.append("ASSISTANT: ok")
    # Bytes, so the file is the same on every OS: write_text would translate each newline.
    (sessions / "abcd1234-0000.md").write_bytes(
        ("\n".join(lines) + "\n").encode("utf-8")
    )
    return sweep.sweep(tmp_path / "retro")


@pytest.mark.parametrize("kind", sorted(_INJECTED_TURNS))
def test_the_sweep_skips_each_harness_injected_turn(kind, tmp_path):
    assert _sweep(tmp_path, [_INJECTED_TURNS[kind]]) == []


def test_the_sweep_flags_an_operator_correction_between_injected_turns(tmp_path):
    """Known positive for the skip tests: the sweep does see a correction, and the skip is by
    what a block starts with, not by where it sits."""
    turns = [*_INJECTED_TURNS.values(), "no, that is wrong, fix it again"]
    hits = _sweep(tmp_path, turns)
    assert len(hits) == 1
    assert hits[0].startswith("[abcd1234:")
    assert "that is wrong" in hits[0]


def test_without_the_four_prefixes_the_sweep_flags_every_injected_turn(
    tmp_path, monkeypatch
):
    """Known positive: with the list as it was before the four were added, each injected turn
    IS a candidate. So an empty result above is the skip working, not a sweep that cannot see
    these turns."""
    before = tuple(p for p in sweep.SKIP_PREFIX if p not in _INJECTED_PREFIXES)
    monkeypatch.setattr(sweep, "SKIP_PREFIX", before)
    hits = _sweep(tmp_path, list(_INJECTED_TURNS.values()))
    assert len(hits) == len(_INJECTED_TURNS)


# --- line numbers: the sweep must agree with ripgrep and the Read tool ----------------------
# A candidate is cited as [session:line], and the reader then opens that line with Grep or the
# Read tool. Both count the line feed character and nothing else. `Path.read_text` does not: it
# reads with universal newlines, so a carriage return in front of a line feed adds a line end of
# its own and a lone one is a line end by itself. The digest writer used to turn a CRLF inside a
# message into CR CR LF on Windows, so every block after one was cited too high (the same on every
# OS once such a digest exists, because universal newlines is not OS-specific).
_DIGEST_HEAD = b"# Session abcdefgh\nTitle: t\nBranch: b\nstart -> end\n\n"
_REPORTED_BLOCK = b"USER: this is wrong and must be reported\n"
_LINE_NUMBER_DIGESTS = {
    "control": _DIGEST_HEAD
    + b"USER: first message\ncontinues on the next line\nASSISTANT: ok\n"
    + _REPORTED_BLOCK,
    "cr-cr-lf": _DIGEST_HEAD
    + b"USER: first message line\r\r\nsecond physical line of the first block\n"
    + b"ASSISTANT: ok\n"
    + _REPORTED_BLOCK,
    "lone-cr": _DIGEST_HEAD
    + b"USER: first message\rcontinues after a lone carriage return\nASSISTANT: ok\n"
    + _REPORTED_BLOCK,
    "form-feed": _DIGEST_HEAD
    + b"USER: first message\x0ccontinues after a form feed\nASSISTANT: ok\n"
    + _REPORTED_BLOCK,
    # What an older extractor wrote on Windows: every line feed a CR LF, and a CR LF inside a
    # message a CR CR LF.
    "older-windows-digest": b"# Session abcdefgh\r\nTitle: t\r\nBranch: b\r\n"
    + b"start -> end\r\n\r\n"
    + b"USER: first message line\r\r\nsecond physical line\r\nASSISTANT: ok\r\n"
    + _REPORTED_BLOCK.replace(b"\n", b"\r\n"),
}
# The kinds on which a reader that is not LF-only gives another number than ripgrep does.
_KINDS_THAT_DRIFT = sorted(set(_LINE_NUMBER_DIGESTS) - {"control"})


def _true_line(data):
    """The line of the reported block as ripgrep and the Read tool number it: LF only."""
    marker = b"USER: this is wrong"
    return next(i for i, ln in enumerate(data.split(b"\n"), 1) if ln.startswith(marker))


def _sweep_digest(tmp_path, data, name="abcdefgh-0000.md"):
    """Run the real sweep over one digest written as bytes, so no OS translates anything."""
    sessions = tmp_path / "retro" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / name).write_bytes(data)
    return sweep.sweep(tmp_path / "retro")


def _cited_line(hit):
    return int(hit[1:].split("]")[0].split(":")[1])


def test_the_line_number_fixtures_have_the_line_numbers_they_claim():
    """Pin the surface in numbers: five digests, four of which move a number-by-reader."""
    assert len(_LINE_NUMBER_DIGESTS) == 5
    assert len(_KINDS_THAT_DRIFT) == 4
    assert {kind: _true_line(data) for kind, data in _LINE_NUMBER_DIGESTS.items()} == {
        "control": 9,
        "cr-cr-lf": 9,
        "lone-cr": 8,
        "form-feed": 8,
        "older-windows-digest": 9,
    }


@pytest.mark.parametrize("kind", _KINDS_THAT_DRIFT)
def test_the_fixtures_separate_a_reader_that_miscounts_from_one_that_does_not(
    kind, tmp_path
):
    """Known positive for the line-number test below: the reader the sweep used to have (read with
    universal newlines, split with splitlines) cites another line on every fixture except the
    control, so a test that passes on all five is not a test that cannot see the drift."""
    data = _LINE_NUMBER_DIGESTS[kind]
    path = tmp_path / "digest.md"
    path.write_bytes(data)
    old_reader = path.read_text(encoding="utf-8").splitlines()
    old_number = next(
        i for i, ln in enumerate(old_reader, 1) if ln.startswith("USER: this is wrong")
    )
    assert old_number != _true_line(data), f"{kind}: the old reader numbered it right"
    control = _LINE_NUMBER_DIGESTS["control"]
    path.write_bytes(control)
    control_lines = path.read_text(encoding="utf-8").splitlines()
    assert next(
        i
        for i, ln in enumerate(control_lines, 1)
        if ln.startswith("USER: this is wrong")
    ) == _true_line(control)


@pytest.mark.parametrize("kind", sorted(_LINE_NUMBER_DIGESTS))
def test_the_sweep_cites_the_line_that_grep_and_the_read_tool_show(kind, tmp_path):
    data = _LINE_NUMBER_DIGESTS[kind]
    hits = _sweep_digest(tmp_path, data)
    assert len(hits) == 1, hits
    assert _cited_line(hits[0]) == _true_line(data)
    assert "\r" not in hits[0], (
        "a carriage return in a candidate breaks the one-line citation"
    )


# The sweep's result file holds LF only. A text-mode write turns each LF into CR LF on Windows, so
# the file is written as bytes. The invariant is "no carriage return in the file", checked as this
# OS writes and again through an emulation of Windows text mode: a writer that went back to text
# mode would otherwise pass on a host whose text mode translates nothing, and CI runs on one.
def _emulate_windows_text_mode(monkeypatch):
    original = Path.write_text

    def write_text(self, data, encoding=None, errors=None, newline=None):
        if newline is None:  # text mode with no newline argument: LF becomes CR LF
            data = data.replace("\n", "\r\n")
        return original(
            self,
            data,
            encoding=encoding,
            errors=errors,
            newline="" if newline is None else newline,
        )

    monkeypatch.setattr(Path, "write_text", write_text)


def test_the_text_mode_emulation_does_translate_line_feeds(tmp_path, monkeypatch):
    """Known positive for the emulation: a text write with no newline argument gets CR LF, one that
    names its newline does not, and a write of bytes is untouched, so a green result below is the
    sweep's writer and not an emulation that changes nothing."""
    _emulate_windows_text_mode(monkeypatch)
    plain = tmp_path / "plain.txt"
    plain.write_text("a\nb", encoding="utf-8")
    exact = tmp_path / "exact.txt"
    exact.write_text("a\nb", encoding="utf-8", newline="\n")
    raw = tmp_path / "raw.txt"
    raw.write_bytes(b"a\nb")
    assert plain.read_bytes() == b"a\r\nb"
    assert exact.read_bytes() == b"a\nb"
    assert raw.read_bytes() == b"a\nb"


@pytest.mark.parametrize(
    "windows_text_mode", [False, True], ids=["this-os", "windows-text-mode"]
)
def test_the_sweep_output_file_carries_no_carriage_return(
    windows_text_mode, tmp_path, monkeypatch
):
    """Two candidates, so the file holds a line break of its own, and one digest whose message has
    a lone carriage return inside it: neither may reach the file, on any OS."""
    if windows_text_mode:
        _emulate_windows_text_mode(monkeypatch)
    _sweep_digest(tmp_path, _LINE_NUMBER_DIGESTS["lone-cr"], "abcdefgh-0001.md")
    _sweep_digest(
        tmp_path, _LINE_NUMBER_DIGESTS["older-windows-digest"], "ijklmnop-0002.md"
    )
    assert sweep.main(["sweep_user_corrections.py", str(tmp_path / "retro")]) == 0
    written = (tmp_path / "retro" / "user_corrections_sweep.txt").read_bytes()
    assert written.count(b"[") == 2, "expected one candidate per digest"
    assert b"\r" not in written
    assert written.count(b"\n") == 1, "two candidates are separated by exactly one LF"


# --- the operator section after the extractor's byte cap ------------------------------------
def _operator_record(text):
    return {
        "type": "user",
        "message": {"role": "user", "content": text},
        "origin": {"kind": "human"},
        "promptSource": "typed",
    }


def test_the_sweep_reads_the_operator_section_after_the_cap(tmp_path, monkeypatch):
    """A correction the operator typed after the cap is a candidate, cited at the line grep shows,
    and the USER block that ends the capped transcript is closed at the section's rule instead of
    absorbing the section's heading."""
    monkeypatch.setattr(ex, "TRANSCRIPT_BYTE_CAP", 160)
    rows = [
        _operator_record("no, that is wrong, first"),
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "x" * 400}]},
        },
        _operator_record("no, that is wrong, second, typed after the cut"),
    ]
    source = tmp_path / "abcdefgh-0000.jsonl"
    source.write_bytes(("\n".join(json.dumps(r) for r in rows) + "\n").encode("utf-8"))
    sessions = tmp_path / "retro" / "sessions"
    sessions.mkdir(parents=True)
    sess = ex.process_session(source, sessions)[0]
    digest = Path(sess["transcriptPath"]).read_bytes()
    assert b"truncated at 120 KB" in digest, (
        "the cap must bite for this test to mean anything"
    )

    hits = sweep.sweep(tmp_path / "retro")
    assert len(hits) == 2, hits
    first, second = hits
    assert "typed after the cut" not in first
    assert "Operator turns" not in first and "Operator turns" not in second
    lines = digest.split(b"\n")
    for hit, marker in (
        (first, b"USER: no, that is wrong, first"),
        (second, b"USER: no, that is wrong, second"),
    ):
        true_line = next(i for i, ln in enumerate(lines, 1) if ln.startswith(marker))
        assert _cited_line(hit) == true_line
