"""Unit tests for the behavioral session extractor.

Pure stdlib, no DB / service / migration dependencies, so this does NOT require the project's
Docker/CI test harness. Run with:

    uv run python -m pytest "${CLAUDE_SKILL_DIR}/scripts/test_extract_sessions.py"
"""

import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
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


# --- hex exemption: citation anchors survive, secrets do not --------------------------------
def test_redaction_preserves_git_sha_and_sha256_citation_anchors():
    """Exactly-40 (git SHA-1) and exactly-64 (sha256) hex are provenance, not secrets.

    The exemption shipped untested. Blanket hex redaction destroyed 104 of these across the 25
    most recent sessions of one corpus (80 SHA-1 + 24 sha256) -- the anchors a retrospective
    cites by. All 15 distinct 40-hex tokens in that sample resolved as real git objects.
    """
    sha1 = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"  # exactly 40
    sha256 = "0" * 64  # exactly 64
    assert len(sha1) == 40 and len(sha256) == 64, "fixture lengths must be exact"
    out = ex.redact(f"commit {sha1} digest {sha256}")
    assert sha1 in out, "git SHA-1 anchor was redacted"
    assert sha256 in out, "sha256 anchor was redacted"


def test_redaction_still_masks_hex_of_other_lengths():
    """The NEGATIVE half: the exemption is length-exact, so off-by-one hex stays redacted.

    Without this, the exemption could be widened to never-redact-hex and every other test here
    would still pass -- a redaction bug in the leaking direction. Verified by mutation: with the
    rule neutered, this is the test that fails.
    """
    for n in (32, 39, 41, 63, 65, 80):
        tok = "f" * n
        out = ex.redact(f"value {tok} end")
        assert tok not in out, f"{n}-char hex must still be redacted, got: {out}"
        assert "[REDACTED_HEX]" in out, f"{n}-char hex produced no redaction marker"


def test_labelled_secrets_are_masked_even_at_exempt_lengths():
    """Defence in depth: a 40/64-hex SECRET is caught by the labelled patterns regardless.

    This is what makes the length exemption safe -- legacy 40-hex tokens in the shapes that
    actually occur (KEY=/TOKEN=/Bearer) are matched by rules above the hex rule and never
    reach it. The residual risk is a BARE, unlabelled, exactly-40/64 secret.
    """
    forty = "b" * 40
    assert forty not in ex.redact(f"GITHUB_TOKEN={forty}")
    assert forty not in ex.redact(f"Authorization: Bearer {forty}")
    assert forty not in ex.redact(f"API_SECRET: {forty}")


# --- Stripe key shapes ------------------------------------------------------------------------
# A secret or restricted API key (sk_ or rk_, then test or live) and a webhook signing secret
# (whsec_), each followed by a run of letters and digits, are redacted, and the leak gate that
# --self-check runs looks for the same shapes in what the extractor wrote, so a miss in the
# redaction is not silent. The left-boundary guard is the one the sk- patterns carry: without it the
# tail of an ordinary word that ends in the prefix ("task_test_...", "work_live_...") is redacted,
# and the redaction silently rewrites real identifiers. The keys are joined from fragments at run
# time: the repository never holds a contiguous one, only the code that makes one.
_STRIPE_SHAPES = {
    "secret-test": ("sk", "test"),
    "secret-live": ("sk", "live"),
    "restricted-test": ("rk", "test"),
    "restricted-live": ("rk", "live"),
    "webhook-secret": ("whsec",),
}
# the start of an ordinary word that ends in each prefix, so that the prefix sits inside a word
_STRIPE_WORD_LEADS = {"sk": "ta", "rk": "wo", "whsec": "x"}
_STRIPE_CONTEXTS = (
    "{key}",
    "token {key} end",
    'cfg "{key}"',
    "KEY_{key}",
    "line\n{key}\nnext",
)


def _stripe_key(shape, body="q" * 24):
    return "_".join(_STRIPE_SHAPES[shape]) + "_" + body


def test_the_stripe_shapes_are_the_ones_the_tests_state():
    """The surface in numbers: five shapes, and each prefix has a word it can hide in."""
    assert len(_STRIPE_SHAPES) == 5
    assert {parts[0] for parts in _STRIPE_SHAPES.values()} == set(_STRIPE_WORD_LEADS)


@pytest.mark.parametrize("shape", sorted(_STRIPE_SHAPES))
@pytest.mark.parametrize("context", _STRIPE_CONTEXTS)
def test_a_stripe_key_is_redacted(shape, context):
    out = ex.redact(context.format(key=_stripe_key(shape)))
    assert "qqqqqqqq" not in out
    assert "[REDACTED_KEY]" in out


@pytest.mark.parametrize("shape", sorted(_STRIPE_SHAPES))
@pytest.mark.parametrize("lead", ["letter", "digit"])
def test_an_ordinary_word_that_contains_the_prefix_is_not_redacted(shape, lead):
    """The tail of "task_test_..." is part of a word: a letter or a digit before the prefix means
    it is not the start of a key."""
    before = _STRIPE_WORD_LEADS[_STRIPE_SHAPES[shape][0]] if lead == "letter" else "7"
    text = f"see {before}{_stripe_key(shape)} here"
    assert ex.redact(text) == text


@pytest.mark.parametrize("shape", sorted(_STRIPE_SHAPES))
@pytest.mark.parametrize(
    "body",
    ["q" * 8, "checkout_flag_enabled_in_prod"],
    ids=["short-body", "words-with-underscores"],
)
def test_a_prefix_with_no_key_after_it_is_not_redacted(shape, body):
    text = f"set {_stripe_key(shape, body)} now"
    assert ex.redact(text) == text


@pytest.mark.parametrize("shape", sorted(_STRIPE_SHAPES))
def test_redacting_a_stripe_key_twice_changes_nothing(shape):
    once = ex.redact(f"x {_stripe_key(shape)} y")
    assert "[REDACTED_KEY]" in once
    assert ex.redact(once) == once


@pytest.mark.parametrize("shape", sorted(_STRIPE_SHAPES))
def test_the_leak_gate_sees_each_stripe_shape_and_the_redacted_text_is_clean(
    shape, tmp_path
):
    key = _stripe_key(shape)
    path = tmp_path / "digest.md"
    path.write_text(f"USER: pasted {key} here", encoding="utf-8")
    assert ex.check_file(path), "the leak gate does not see the shape"
    path.write_text("USER: " + ex.redact(f"pasted {key} here"), encoding="utf-8")
    assert ex.check_file(path) == []
    word = _STRIPE_WORD_LEADS[_STRIPE_SHAPES[shape][0]] + key
    path.write_text(f"USER: see {word} here", encoding="utf-8")
    assert ex.check_file(path) == [], "the leak gate flagged an ordinary word"


def _stripe_session(sdir, shape):
    sdir.mkdir()
    _write_rows(
        sdir / "aaaa1111-0000-0000-0000-000000000000.jsonl",
        [_human(f"pasted {_stripe_key(shape)} here", source="typed")],
    )


@pytest.mark.parametrize("shape", sorted(_STRIPE_SHAPES))
def test_a_stripe_key_in_an_operator_turn_never_reaches_the_digests(
    shape, tmp_path, monkeypatch
):
    _stripe_session(tmp_path / "src", shape)
    out = tmp_path / "out"
    agg = _run(tmp_path / "src", out, monkeypatch)  # --self-check: a leak would exit 3
    digest = next((out / "sessions").glob("*.md")).read_bytes().decode("utf-8")
    assert "[REDACTED_KEY]" in digest
    assert "qqqqqqqq" not in digest + json.dumps(agg)


@pytest.mark.parametrize("shape", sorted(_STRIPE_SHAPES))
def test_self_check_stops_the_run_when_the_redaction_misses_a_stripe_key(
    shape, tmp_path, monkeypatch
):
    """Known positive for the test above: with the redactions emptied the key reaches the digest,
    and the leak gate stops the run with exit status 3, so a miss in the redaction is not silent."""
    monkeypatch.setattr(ex, "REDACTIONS", [])
    _stripe_session(tmp_path / "src", shape)
    with pytest.raises(SystemExit) as stopped:
        _run(tmp_path / "src", tmp_path / "out", monkeypatch)
    assert stopped.value.code == 3


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


# --- the session dir is derived from the working directory ----------------------------------
# A plugin install places the extractor under the home directory's .claude/ folder, so the old walk
# up from the script to the first parent that holds a .claude/ folder ended at the HOME directory:
# the run either found no folder, or, when a session folder for the home directory happened to
# exist, analysed that corpus and not the project's. The derivation now starts from the working
# directory, which must be the project root with a session folder of its own, and refuses anything
# else. The fake home below is built in a temporary folder, so no test touches the real one, and
# the folder is a short one on purpose: the store names a session folder after the project's whole
# path, so a path in these tests is about twice as long as the folder it hangs from, and under a
# deep tmp_path (the wrapper test runs this file below its own) it passes the Windows limit.
_SESSION_ROW = {
    "type": "user",
    "message": {"content": [{"type": "text", "text": "hi"}]},
}


@pytest.fixture
def short_tmp():
    folder = Path(tempfile.mkdtemp(prefix="k")).resolve()
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _fake_store(home, *directories):
    """A fake home whose ~/.claude/projects holds one session folder, with a transcript in it,
    named (by the extractor's own encoding) for each directory given: {directory: its folder}."""
    projects = home / ".claude" / "projects"
    projects.mkdir(parents=True)
    folders = {}
    for directory in directories:
        folder = projects / ex._encode_repo_path(directory)
        folder.mkdir()
        _write_rows(
            folder / "s0000001-0000-0000-0000-000000000000.jsonl", [_SESSION_ROW]
        )
        folders[directory] = folder
    return folders


def test_the_session_dir_is_the_one_of_the_working_directory(short_tmp):
    home = short_tmp / "home"
    project = short_tmp / "work" / "proj"
    project.mkdir(parents=True)
    folders = _fake_store(home, home, project)  # the home directory has a folder too
    found = ex._derive_session_dir(cwd=project, home=home)
    assert found.samefile(folders[project])
    assert not found.samefile(folders[home])


def test_the_home_directory_is_never_used_silently(short_tmp):
    home = short_tmp / "home"
    _fake_store(home, home)  # its session folder exists, and is still not used
    with pytest.raises(SystemExit) as refused:
        ex._derive_session_dir(cwd=home, home=home)
    message = str(refused.value)
    assert str(home) in message and "home directory" in message
    assert "first argument" in message


def test_a_directory_with_no_session_folder_of_its_own_is_refused(short_tmp):
    """Below the project root, or beside it under a name that shares its start: the project's
    folder is there, and is not borrowed."""
    home = short_tmp / "home"
    project = short_tmp / "work" / "proj"
    below = project / "src" / "pkg"
    beside = short_tmp / "work" / "proj-two"
    for directory in (below, beside):
        directory.mkdir(parents=True)
    _fake_store(home, project)
    for directory in (below, beside):
        with pytest.raises(SystemExit) as refused:
            ex._derive_session_dir(cwd=directory, home=home)
        message = str(refused.value)
        assert str(directory) in message and "no session folder" in message
        assert "first argument" in message


# Every test above puts the project BESIDE the fake home, and most real projects sit BELOW the home
# directory (it holds the folders the repositories are cloned into). The layout needs tests of its
# own, because in none of the tests above is the home an ancestor of the working directory. Without
# them, a rule that reads any directory under the home as the home passes all of the above while it
# refuses every real project, and a fallback that hands a directory below the home the home's own
# folder passes all of it as well.
def test_a_project_below_the_home_directory_is_derived(short_tmp):
    home = short_tmp / "home"
    project = home / "work" / "proj"
    project.mkdir(parents=True)
    folders = _fake_store(home, home, project)  # the home directory has a folder too
    found = ex._derive_session_dir(cwd=project, home=home)
    assert found.samefile(folders[project])
    assert not found.samefile(folders[home])


def test_a_directory_below_the_home_with_no_folder_of_its_own_is_refused(short_tmp):
    """The home's folder is there, and is not borrowed for a directory below the home."""
    home = short_tmp / "home"
    below = home / "work" / "proj"
    below.mkdir(parents=True)
    _fake_store(home, home)
    with pytest.raises(SystemExit) as refused:
        ex._derive_session_dir(cwd=below, home=home)
    message = str(refused.value)
    assert str(below) in message and "no session folder" in message
    assert "first argument" in message


# The home directory is recognised by identity and not by how it is spelled, and a path that is not
# there cannot be asked for its identity. In every test above the working directory is either the
# home, spelled as the home is spelled, or another directory, and every path exists, so a home test
# that compares the two as written passes them all, and so does one that raises on a missing path.
# The first lets the home under another spelling use the home's own folder silently (another
# letter case on a case-insensitive file system would, as the folder lookup ignores case); the
# second turns a home that is not there into a crash, where the contract is a refusal that asks
# for the session dir. A `..` step stands for the other spelling: it differs from the home as a
# path on every system, which a letter case does not on Windows, and it needs no privilege to
# build, which a link may.
def test_another_spelling_of_the_same_directory_is_the_same_directory(short_tmp):
    (short_tmp / "a").mkdir()
    spelled = short_tmp / "a" / ".."
    assert spelled != short_tmp, "the premise: the two spellings differ as paths"
    assert ex._is_same_dir(spelled, short_tmp)
    assert ex._is_same_dir(short_tmp, spelled)
    assert not ex._is_same_dir(short_tmp / "a", short_tmp), "a child is not its parent"


def test_a_path_that_is_not_there_is_compared_as_written(short_tmp):
    assert ex._is_same_dir(short_tmp / "nope", short_tmp / "nope")
    assert not ex._is_same_dir(short_tmp / "nope", short_tmp / "other")
    assert not ex._is_same_dir(short_tmp / "nope", short_tmp)


def test_the_home_directory_spelled_another_way_is_never_used_silently(short_tmp):
    home = short_tmp / "home"
    _fake_store(home, home)  # its session folder exists, and is still not used
    (home / "work").mkdir()
    spelled = home / "work" / ".."
    with pytest.raises(SystemExit) as refused:
        ex._derive_session_dir(cwd=spelled, home=home)
    message = str(refused.value)
    assert str(spelled) in message and "home directory" in message
    assert "first argument" in message


def test_a_home_that_is_not_there_is_a_refusal_and_not_a_crash(short_tmp):
    project = short_tmp / "work" / "proj"
    project.mkdir(parents=True)
    with pytest.raises(SystemExit) as refused:
        ex._derive_session_dir(cwd=project, home=short_tmp / "no-home")
    message = str(refused.value)
    assert str(project) in message and "no session folder" in message
    assert "first argument" in message


def test_an_explicit_session_dir_never_calls_the_derivation(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("an explicit session dir must not start the derivation")

    monkeypatch.setattr(ex, "_derive_session_dir", forbidden)
    sdir = tmp_path / "src"
    sdir.mkdir()
    _write_rows(sdir / "aaaa1111-0000-0000-0000-000000000000.jsonl", [_SESSION_ROW])
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    assert agg["generatedFor"]["sessionDir"] == str(sdir)


def _run_installed_copy(home, cwd, *args):
    """The extractor as an installed plugin runs it: a copy of the script under the home
    directory's plugin cache, started in `cwd`, with `home` as the home directory."""
    cache = home / ".claude" / "plugins" / "cache" / "kit" / "scripts"
    cache.mkdir(parents=True, exist_ok=True)
    script = cache / "extract_sessions.py"
    shutil.copyfile(ex.__file__, script)
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


def _fake_home_and_project(short_tmp):
    """The paths of a fake home and a project root beside it, both created."""
    home = short_tmp / "home"
    project = short_tmp / "work" / "proj"
    home.mkdir()
    project.mkdir(parents=True)
    return home, project


@pytest.mark.parametrize(
    "home_has_a_folder", [False, True], ids=["no-folder-for-home", "folder-for-home"]
)
def test_an_installed_copy_derives_the_folder_of_the_project_it_runs_in(
    home_has_a_folder, short_tmp
):
    home, project = _fake_home_and_project(short_tmp)
    folders = _fake_store(home, project, *([home] if home_has_a_folder else []))
    done = _run_installed_copy(home, project, "out")
    assert done.returncode == 0, done.stderr
    agg = json.loads((project / "out" / "aggregate.json").read_text(encoding="utf-8"))
    assert Path(agg["generatedFor"]["sessionDir"]).samefile(folders[project])
    assert agg["stats"]["totalSessions"] == 1


@pytest.mark.parametrize(
    "home_has_a_folder", [False, True], ids=["no-folder-for-home", "folder-for-home"]
)
def test_an_installed_copy_derives_the_folder_of_a_project_below_the_home_directory(
    home_has_a_folder, short_tmp
):
    """The layout of a real install: the plugin cache and the project are both below the home."""
    home = short_tmp / "home"
    project = home / "work" / "proj"
    project.mkdir(parents=True)
    folders = _fake_store(home, project, *([home] if home_has_a_folder else []))
    done = _run_installed_copy(home, project, "out")
    assert done.returncode == 0, done.stderr
    agg = json.loads((project / "out" / "aggregate.json").read_text(encoding="utf-8"))
    assert Path(agg["generatedFor"]["sessionDir"]).samefile(folders[project])
    assert agg["stats"]["totalSessions"] == 1


@pytest.mark.parametrize("where", ["home", "below-the-root", "no-folder"])
def test_an_installed_copy_refuses_and_asks_for_the_session_dir(where, short_tmp):
    home, project = _fake_home_and_project(short_tmp)
    below = project / "src"
    elsewhere = short_tmp / "elsewhere"
    below.mkdir()
    elsewhere.mkdir()
    _fake_store(home, home, project)
    cwd = {"home": home, "below-the-root": below, "no-folder": elsewhere}[where]
    done = _run_installed_copy(home, cwd, "out")
    assert done.returncode == 1, (done.returncode, done.stderr)
    assert "first argument" in done.stderr and str(cwd) in done.stderr
    assert not (cwd / "out").exists(), "nothing is written when the run is refused"


def test_the_help_and_the_docstring_say_the_working_directory_decides(
    monkeypatch, capsys
):
    monkeypatch.setattr(sys, "argv", ["extract_sessions.py", "--help"])
    with pytest.raises(SystemExit):
        ex.main()
    helptext = " ".join(capsys.readouterr().out.split())
    doc = " ".join((ex.__doc__ or "").split())
    assert "working directory" in helptext and "working directory" in doc
    assert "auto-derived from the repo root" not in helptext
    assert "auto-derived from this script's location" not in doc


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


# --- user-rejected: the harness's own denial sentence, anchored at the START of the result ---
# Synthetic fixtures that follow the shapes real transcripts carry. Multi-line texts are joined
# from fragments, so no ":" sits directly in front of a backslash escape in this source.
_DENIAL_OPENING = "The user doesn't want to proceed with this tool use."
_DENIAL_EXPLAINED = (
    _DENIAL_OPENING
    + " The tool use was rejected (eg. if it was a file edit, the new_string was NOT written "
    "to the file)."
)
_DENIAL_STOP = (
    " STOP what you are doing and wait for the user to tell you how to proceed."
)
_DENIAL_FORMS = {
    "plain": _DENIAL_EXPLAINED + _DENIAL_STOP,
    "with-trailing-note": "\n\n".join(
        [
            _DENIAL_EXPLAINED + _DENIAL_STOP,
            "Note: The user's next message may contain a correction or preference.",
        ]
    ),
    "with-feedback": "\n".join(
        [
            _DENIAL_EXPLAINED + " To tell you how to proceed, the user said:",
            "use the other file instead",
        ]
    ),
    "older-reason": _DENIAL_EXPLAINED
    + " The user provided the following reason for the rejection:  split this up",
}
_RIPGREP_USAGE_HEAD = "Search failed — ripgrep rejected the pattern, glob, or file type without searching:"
_RIPGREP_ERRORS = {
    "regex-parse": "\n".join(
        [
            _RIPGREP_USAGE_HEAD,
            "rg: regex parse error:",
            "    (?:foo(?!bar))",
            "         ^^^",
            "error: look-around, including look-ahead and look-behind, is not supported",
        ]
    ),
    "glob-parse": "\n".join(
        [
            _RIPGREP_USAGE_HEAD,
            "rg: error parsing glob '{a/**/*.{py,md},b/*.txt}': nested alternate groups "
            "are not allowed",
        ]
    ),
    "file-type": "\n".join([_RIPGREP_USAGE_HEAD, "rg: unrecognized file type: pyy"]),
}


def test_user_rejection_is_separate_bucket():
    assert ex.classify_error("Bash", True, _DENIAL_FORMS["plain"]) == "user-rejected"
    assert (
        ex.classify_error("Edit", True, _DENIAL_FORMS["with-feedback"])
        == "user-rejected"
    )


@pytest.mark.parametrize("form", sorted(_DENIAL_FORMS))
@pytest.mark.parametrize("origin", ["Bash", "Read", "Write", "AskUserQuestion"])
def test_every_harness_denial_form_is_user_rejected(origin, form):
    """The follow-on text after the opening sentence differs by harness build (a trailing note,
    the user's own feedback, an older 'reason' form); the opening sentence is the anchor."""
    assert ex.classify_error(origin, True, _DENIAL_FORMS[form]) == "user-rejected"


def test_a_denial_arriving_as_content_blocks_is_still_user_rejected():
    blocks = [{"type": "text", "text": _DENIAL_FORMS["plain"]}]
    assert ex.classify_error("Bash", True, ex.result_text(blocks)) == "user-rejected"
    # an empty first block leaves a newline in front once the blocks are joined
    padded = ex.result_text([{"type": "text", "text": ""}, *blocks])
    assert padded.startswith("\n")
    assert ex.classify_error("Bash", True, padded) == "user-rejected"


@pytest.mark.parametrize("kind", sorted(_RIPGREP_ERRORS))
def test_ripgrep_usage_errors_are_ordinary_tool_errors(kind):
    """Grep's own usage error says "ripgrep rejected the pattern". Nobody refused anything: the
    tool failed, so it belongs with the other tool errors and not in the permission bucket."""
    assert ex.classify_error("Grep", True, _RIPGREP_ERRORS[kind]) == "tool-error"


@pytest.mark.parametrize(
    ("origin", "text", "category"),
    [
        (
            "Bash",
            "Exit code 1\nerror: the remote rejected the push because the branch is protected",
            "runtime-exit",
        ),
        ("WebFetch", "The server rejected the request with status 403", "tool-error"),
        (
            "Bash",
            "Exit code 1\nerror: user rejected the credential prompt",
            "runtime-exit",
        ),
        ("Edit", "user rejected the edit", "tool-error"),
        (
            "Bash",
            "Exit code 2\nnote: the user has chosen not to continue",
            "runtime-exit",
        ),
        ("Read", "user doesn't want this file", "tool-error"),
        (
            "Bash",
            "Exit code 1\nlog line: " + _DENIAL_FORMS["plain"],
            "runtime-exit",
        ),
        # The harness stamps this sentence as a cancellation, not a denial.
        (
            "Bash",
            "The user doesn't want to take this action right now." + _DENIAL_STOP,
            "runtime-exit",
        ),
    ],
    ids=[
        "remote-rejected-the-push",
        "server-rejected-the-request",
        "quotes-user-rejected",
        "quotes-user-rejected-edit",
        "quotes-user-has-chosen-not-to",
        "quotes-user-doesnt-want",
        "denial-sentence-quoted-mid-text",
        "cancel-sentence",
    ],
)
def test_text_that_only_quotes_a_denial_phrase_is_not_a_denial(origin, text, category):
    """A phrase match anywhere in the text misfiles any error that merely quotes the phrase;
    only the harness's own sentence at the start of the result is a denial."""
    assert ex.classify_error(origin, True, text) == category


def test_hook_denials_stay_out_of_the_user_rejected_bucket():
    """A hook block is a denial but not the user's refusal, so it keeps its ordinary category."""
    hook = "PreToolUse:Bash hook error: Blocked by project policy; use the wrapper instead."
    assert ex.classify_error("Bash", True, hook) == "runtime-exit"


def test_a_denial_sentence_in_a_result_that_is_not_an_error_is_data():
    assert ex.classify_error("Read", False, _DENIAL_FORMS["plain"]) is None


def test_exit_code_zero_is_not_an_error():
    assert ex.classify_error("Bash", False, "done\nExit code 0") is None


# --- .NET build output is a build error -----------------------------------------------------
# MSBuild stamps a failed build "Build FAILED." and the C# compiler writes "error CS" and four
# digits, so a generic "failed" rule files a .NET build as a test failure and a bare compiler line
# as a plain non-zero exit. The samples keep their bytes exactly (the runs of spaces in the dotnet
# test summary are part of its shape), each multi-line text joined from its lines. The dotnet
# test, ruff, pytest, ripgrep and refusal samples are known positives that keep their class.
_DOTNET_BUILD_FAILED = "\n".join(
    [
        "Build FAILED.",
        "  Program.cs(12,5): error CS1002: ; expected [App.csproj]",
        "    1 Error(s)",
    ]
)
_COMPILER_ERROR_LINE = "Program.cs(12,5): error CS1002: ; expected"
_DOTNET_TEST_SUMMARY = (
    "Failed!  - Failed:     1, Passed:    41, Skipped:     0, Total:    42"
)
_RUFF_ERRORS_FOUND = "ruff check: 3 errors found"
_PYTEST_SESSION = "\n".join(["=== test session starts ===", "1 failed, 3 passed"])
_RIPGREP_OPTION_ERROR = (
    "Search failed "
    + chr(0x2014)
    + " ripgrep rejected the pattern, glob, or option: regex parse error"
)
_HARNESS_REFUSAL = _DENIAL_OPENING + " (tool use was rejected)"


@pytest.mark.parametrize(
    ("origin", "text", "category"),
    [
        ("Bash", _DOTNET_BUILD_FAILED, "build-compile"),
        ("Bash", _COMPILER_ERROR_LINE, "build-compile"),
        ("Bash", _DOTNET_TEST_SUMMARY, "test-failure"),
        ("Bash", _RUFF_ERRORS_FOUND, "build-compile"),
        ("Bash", _PYTEST_SESSION, "test-failure"),
        ("Grep", _RIPGREP_OPTION_ERROR, "tool-error"),
        ("Bash", _HARNESS_REFUSAL, "user-rejected"),
    ],
    ids=[
        "dotnet-build-failed",
        "compiler-error-line",
        "dotnet-test-summary",
        "ruff-errors-found",
        "pytest-session",
        "ripgrep-option-error",
        "harness-refusal",
    ],
)
def test_a_dotnet_build_failure_is_a_build_error_and_the_other_classes_hold(
    origin, text, category
):
    assert ex.classify_error(origin, True, text) == category


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("Build FAILED.", "build-compile"),
        ("MSBUILD : error MSB1009: Project file does not exist.", "build-compile"),
        ("error CS1002: ; expected", "build-compile"),
        (
            "Program.cs(3,7): warning CS0168: The variable 'e' is declared but never used",
            "runtime-exit",
        ),
        (
            "warning MSB3277: Found conflicts between different versions.",
            "runtime-exit",
        ),
    ],
    ids=[
        "build-failed-stamp",
        "msbuild-error",
        "compiler-error-without-file-prefix",
        "compiler-warning",
        "msbuild-warning",
    ],
)
def test_each_dotnet_build_signature_is_a_build_error_on_its_own(text, category):
    """No signature rides on another one in the same text. The same codes as warnings are near
    misses: a warning is no build error, so those texts stay a plain non-zero exit."""
    assert ex.classify_error("Bash", True, text) == category


def test_the_dotnet_build_signatures_are_read_before_the_generic_failed_rule():
    """MSBuild's own stamp holds the word the generic test rule keys on, so only the ORDER of the
    two rules decides a text that holds both. The generic half alone is a test failure; joined
    to the stamp, before it or after it, the build class must win."""
    stamp = "Build FAILED."
    generic = "1 failed, 3 passed"
    assert ex.classify_error("Bash", True, generic) == "test-failure"
    for text in (stamp, "\n".join([stamp, generic]), "\n".join([generic, stamp])):
        assert ex.classify_error("Bash", True, text) == "build-compile", text


# --- end-to-end -----------------------------------------------------------------------------
def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _relative_out(monkeypatch, out_dir):
    """Return `out_dir` as a path RELATIVE to a working directory the test moves into.

    main() refuses an output dir that starts with /tmp (it asks for a repo-relative one), and
    pytest's tmp_path lives under /tmp on Linux, so an absolute `tmp_path / "out"` is accepted
    on Windows and refused on the CI runner. A relative path carries no such prefix anywhere.
    """
    monkeypatch.chdir(out_dir.parent)
    return out_dir.name


def _run(session_dir, out_dir, monkeypatch, self_check=True):
    argv = [
        "extract_sessions.py",
        str(session_dir),
        _relative_out(monkeypatch, out_dir),
    ]
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
        sys,
        "argv",
        ["extract_sessions.py", _relative_out(monkeypatch, out_dir), "--self-check"],
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
    leaks, scanned = ex.self_check(tmp_path)
    assert leaks, "self_check must flag an unredacted sk- key"
    assert scanned == 1, f"expected 1 file scanned, got {scanned}"


def test_self_check_scans_emitted_subagent_transcripts(tmp_path):
    # a leak inside an emitted sub-agent transcript must also be caught (rglob coverage)
    sub = tmp_path / "sessions" / "sub" / "sid"
    sub.mkdir(parents=True)
    (tmp_path / "aggregate.json").write_text("{}", encoding="utf-8")
    (sub / "agent-1.md").write_text(
        "ASSISTANT: leaked sk-abcdefghij1234567890SECRET", encoding="utf-8"
    )
    leaks, scanned = ex.self_check(tmp_path)
    assert leaks, (
        "self_check must scan sessions/sub/**/*.md, not just top-level transcripts"
    )
    assert scanned == 2, f"expected aggregate.json + the sub transcript, got {scanned}"


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
    leaks, scanned = ex.self_check(out_dir)
    assert not leaks, "no leaks expected after redaction"
    assert scanned, "a clean result over ZERO scanned files is not a pass"


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
        {
            "command": "session-retrospective",
            "args": "--since 2026-06-01",
            "by": "operator",
        }
    ]
    assert s["counts"]["userMsgs"] == 1, "command pseudo-message must NOT count as a userMsg"
    assert "session-retrospective" in agg["stats"]["skillsUsed"]
    assert agg["stats"]["skillInvocationModes"]["session-retrospective"] == {
        "user": 1,
        "model": 0,
        "harness": 0,
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


def _tool_error_rows(results):
    """Assistant tool_use + user tool_result(is_error) row pairs for (tool, result text) pairs."""
    rows = []
    for i, (name, text) in enumerate(results):
        tid = f"toolu_{i}"
        rows.append(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "id": tid, "name": name, "input": {}}
                    ]
                },
            }
        )
        rows.append(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "is_error": True,
                            "content": text,
                        }
                    ]
                },
            }
        )
    return rows


def test_user_rejected_count_is_every_hit_not_the_capped_sample_list(
    tmp_path, monkeypatch
):
    """The per-session sample list is capped at SAMPLES_PER_CATEGORY, and the aggregate count
    used to add up the list lengths, so a session with more hits than the cap was undercounted."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    many = ex.SAMPLES_PER_CATEGORY + 2
    few = 2
    denial = ("Bash", _DENIAL_FORMS["plain"])
    _write_jsonl(
        sdir / "aaaa1111-0000-0000-0000-000000000000.jsonl",
        _minimal_session_rows(extra=_tool_error_rows([denial] * many)),
    )
    _write_jsonl(
        sdir / "bbbb2222-0000-0000-0000-000000000000.jsonl",
        _minimal_session_rows(
            ts="2026-06-21T10:00:00Z", extra=_tool_error_rows([denial] * few)
        ),
    )
    agg = _run(sdir, tmp_path / "out", monkeypatch)

    tax = agg["errorTaxonomy"]["userRejected"]
    assert tax["count"] == many + few
    assert sorted(tax["sessions"]) == ["aaaa1111", "bbbb2222"]
    # the samples stay a capped subset, and the bucket keeps its shape
    assert len(tax["samples"]) < tax["count"]
    assert set(tax) == {"count", "sessions", "samples"}
    # the true number is also carried on each session; the bucket stays out of the categories
    hits = {s["sessionId"][:8]: s["userRejected"] for s in agg["sessions"]}
    assert hits == {"aaaa1111": many, "bbbb2222": few}
    assert all("user-rejected" not in s["errorsByCategory"] for s in agg["sessions"])


def test_a_subagent_with_only_a_ripgrep_error_is_error_bearing(tmp_path, monkeypatch):
    """Dropped from the permission bucket, a ripgrep usage error is an ordinary tool error: the
    sub-agent that hit it is now error-bearing, which also decides which digests get emitted."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "cccc3333-0000-0000-0000-000000000000"
    _write_jsonl(sdir / f"{sid}.jsonl", _minimal_session_rows())
    subdir = sdir / sid / "subagents"
    subdir.mkdir(parents=True)
    _write_jsonl(
        subdir / "agent-rg.jsonl",
        [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "search"}]},
            },
            *_tool_error_rows([("Grep", _RIPGREP_ERRORS["regex-parse"])]),
        ],
    )
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    sub = agg["sessions"][0]["subAgents"]
    assert sub["errorsByCategory"] == {"tool-error": 1}
    assert sub["agentsWithErrors"] == 1
    assert agg["subAgentErrorTaxonomy"]["byCategory"]["tool-error"]["count"] == 1


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


# --- per-parent limit on the sub-agent deep-dive picks -----------------------------------------
# One parent that fans out widely used to take almost every slot, so the picks said little
# about the other parents. A parent's later candidates now wait while any other candidate
# remains, and a slot still free after that pass is filled from those that waited.
def _pick_session(parent, rows):
    """A session that carries emitted high-signal sub-agents, as select_subagent_deep_dive reads
    them. Each row is (file, errorCount, bytes)."""
    return {
        "sessionId": parent,
        "subAgents": {
            "highSignal": [
                {
                    "file": name,
                    "transcriptPath": f"/abs/{parent}/{name}",
                    "errorsByCategory": {"tool-error": errors},
                    "bytes": size,
                    "emittedBytes": size // 40,
                }
                for name, errors, size in rows
            ]
        },
    }


def _pick_ids(entries):
    return [(e["parentSessionId"], e["file"]) for e in entries]


# pA holds the five best candidates; pB and pC hold three each, ranked between them and below
# them. Every error count differs, so the ranking needs no tie-break.
_PICK_ROWS = {
    "pA": [(f"a{i}.md", 20 - i, 1000) for i in range(5)],
    "pB": [("b0.md", 15, 1000), ("b1.md", 13, 1000), ("b2.md", 11, 1000)],
    "pC": [("c0.md", 14, 1000), ("c1.md", 12, 1000), ("c2.md", 10, 1000)],
}


def _picks_fixture():
    return [_pick_session(parent, rows) for parent, rows in _PICK_ROWS.items()]


def test_the_pick_fixtures_assume_a_limit_of_four_of_six():
    """The fixtures below spell out who is picked, so they are written for these two numbers:
    retuning either one starts here."""
    assert ex.SUBAGENT_DEEPDIVE_PER_PARENT_CAP == 4
    assert ex.SUBAGENT_DEEPDIVE_CAP == 6
    assert ex.SUBAGENT_DEEPDIVE_PER_PARENT_CAP < ex.SUBAGENT_DEEPDIVE_CAP


def test_a_parents_later_picks_give_their_slots_to_other_parents():
    """pA holds the five best candidates: its fifth waits while others remain, so pB and pC
    each take a slot. The old ranking gave pA five of the six."""
    result = ex.select_subagent_deep_dive(_picks_fixture())
    assert _pick_ids(result["selected"]) == [
        ("pA", "a0.md"),
        ("pA", "a1.md"),
        ("pA", "a2.md"),
        ("pA", "a3.md"),
        ("pB", "b0.md"),
        ("pC", "c0.md"),
    ]
    assert _pick_ids(result["overCap"]) == [
        ("pA", "a4.md"),
        ("pB", "b1.md"),
        ("pC", "c1.md"),
        ("pB", "b2.md"),
        ("pC", "c2.md"),
    ]


def test_a_free_slot_is_filled_from_the_waiting_picks_in_rank_order():
    """pA has six candidates and pB one: after the pass one slot is still free, and the best
    waiting pick of pA takes it, not the worst. The old ranking left pB out."""
    sessions = [
        _pick_session("pA", [(f"a{i}.md", 20 - i, 1000) for i in range(6)]),
        _pick_session("pB", [("b0.md", 10, 1000)]),
    ]
    result = ex.select_subagent_deep_dive(sessions)
    assert _pick_ids(result["selected"]) == [
        ("pA", "a0.md"),
        ("pA", "a1.md"),
        ("pA", "a2.md"),
        ("pA", "a3.md"),
        ("pA", "a4.md"),
        ("pB", "b0.md"),
    ]
    assert _pick_ids(result["overCap"]) == [("pA", "a5.md")]


def test_one_busy_parent_alone_still_fills_every_slot():
    """The control for the fill pass: with no other candidate nothing may wait and leave a slot
    empty. A limit with no fill would pick four here, not six, so this holds on the old
    ranking and on the new one."""
    sessions = [_pick_session("pA", [(f"a{i}.md", 20 - i, 1000) for i in range(8)])]
    result = ex.select_subagent_deep_dive(sessions)
    assert _pick_ids(result["selected"]) == [("pA", f"a{i}.md") for i in range(6)]
    assert _pick_ids(result["overCap"]) == [("pA", "a6.md"), ("pA", "a7.md")]


def test_the_pick_lists_keep_their_shape_and_lose_nobody():
    """Both lists keep rank order and their keys, together they hold every candidate once, and
    the order the sessions arrive in changes nothing."""
    sessions = _picks_fixture()
    result = ex.select_subagent_deep_dive(sessions)
    total = sum(len(rows) for rows in _PICK_ROWS.values())
    every = _pick_ids(result["selected"]) + _pick_ids(result["overCap"])
    assert len(every) == len(set(every)) == total, "a candidate was lost or repeated"
    selected_keys = {
        "parentSessionId",
        "file",
        "transcriptPath",
        "errorCount",
        "bytes",
        "emittedBytes",
    }
    over_keys = {"parentSessionId", "file", "errorCount"}
    assert all(set(e) == selected_keys for e in result["selected"])
    assert all(set(e) == over_keys for e in result["overCap"])
    for name in ("selected", "overCap"):
        errors = [e["errorCount"] for e in result[name]]
        assert errors == sorted(errors, reverse=True), f"{name} left rank order"
    assert ex.select_subagent_deep_dive(sessions[::-1]) == result
    assert ex.select_subagent_deep_dive(sessions[1:] + sessions[:1]) == result


def test_the_selection_rule_names_the_limit_per_parent():
    empty = ex.select_subagent_deep_dive([])
    assert empty["selected"] == [] and empty["overCap"] == []
    rule = empty["selectionRule"]
    assert "per parent session while others remain" in rule
    limit = ex.SUBAGENT_DEEPDIVE_PER_PARENT_CAP
    assert f"at most {limit} per parent session while others remain" in rule
    assert f"top {ex.SUBAGENT_DEEPDIVE_CAP}" in rule


def _write_error_agents(subdir, count, pad_base):
    """`count` sub-agents that each hit one error. The error count is 1 for all, so the bytes
    rank them: agent i carries `pad_base + 10 * i` more characters than the bare error."""
    subdir.mkdir(parents=True)
    for i in range(count):
        read = {
            "type": "tool_use",
            "id": "r1",
            "name": "Read",
            "input": {"file_path": f"/repo/missing-{i}.md"},
        }
        failed = {
            "type": "tool_result",
            "tool_use_id": "r1",
            "content": "File does not exist." + "x" * (pad_base + 10 * i),
            "is_error": True,
        }
        _write_jsonl(
            subdir / f"agent-{i:02d}.jsonl",
            [
                {"type": "assistant", "message": {"content": [read]}},
                {"type": "user", "message": {"content": [failed]}},
            ],
        )


def test_the_extractor_limits_one_parents_share_of_the_sub_agent_picks(
    tmp_path, monkeypatch
):
    """End to end, through the emitter: every sub-agent of `big` is larger than any of `small`,
    so the old ranking gave `big` all six slots. It keeps four and `small` gets two."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    big = "aaaa1111-0000-0000-0000-000000000000"
    small = "bbbb2222-0000-0000-0000-000000000000"
    for sid, count, pad_base in ((big, 8, 400), (small, 3, 0)):
        _write_jsonl(sdir / f"{sid}.jsonl", _minimal_session_rows())
        _write_error_agents(sdir / sid / "subagents", count, pad_base)
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    emitted = sorted(s["subAgents"]["transcriptsEmitted"] for s in agg["sessions"])
    assert emitted == [3, 8], "the fixture no longer emits every sub-agent"
    cands = agg["subAgentDeepDiveCandidates"]
    assert _pick_ids(cands["selected"]) == [
        (big, "agent-07.md"),
        (big, "agent-06.md"),
        (big, "agent-05.md"),
        (big, "agent-04.md"),
        (small, "agent-02.md"),
        (small, "agent-01.md"),
    ]
    assert len(cands["overCap"]) == 11 - len(cands["selected"])
    assert "per parent session while others remain" in cands["selectionRule"]
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
        [
            "extract_sessions.py",
            str(sdir),
            _relative_out(monkeypatch, out_dir),
            "--since",
            "2026-06-01",
        ],
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


# The four harness-injected user events: real first lines, synthetic bodies. Each body carries a
# word the corrections sweep looks for, so an un-skipped one would surface as a "correction".
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


@pytest.mark.parametrize("kind", sorted(_INJECTED_TURNS))
def test_harness_injected_turns_are_not_human_turns(kind):
    text = _INJECTED_TURNS[kind]
    assert not ex._is_human_turn(text)
    # SYSTEM_PREFIXES must not move: these still arrive as user-channel messages for
    # counts.userMsgs (see the test below), which the deep-dive selection reads.
    assert ex.is_real_user_text(text)


def test_digest_lists_only_the_operator_among_injected_turns(tmp_path):
    jf = _user_session(
        tmp_path,
        "gggg7777-0000-0000-0000-000000000000",
        ["real ask one", *_INJECTED_TURNS.values(), "real ask two"],
    )
    out = tmp_path / "out"
    out.mkdir()
    ex.write_interaction_digest(out, _fake_sess(), jf, ex.DEFAULT_REREADS_MIN)
    text = (out / "interaction-digest.md").read_text(encoding="utf-8")
    assert "real ask one" in text
    assert "real ask two" in text
    assert "User-message sequence (2 total" in text
    for injected in _INJECTED_TURNS.values():
        assert injected.split("\n")[0] not in text


def test_injected_turns_still_count_as_user_messages(tmp_path, monkeypatch):
    """counts.userMsgs picks the deep-dive sessions (see the comment above
    HARNESS_USER_PREFIXES), so skipping these belongs to the digest layer only."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    _user_session(
        sdir,
        "hhhh8888-0000-0000-0000-000000000000",
        ["real ask", *_INJECTED_TURNS.values()],
    )
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    assert agg["sessions"][0]["counts"]["userMsgs"] == 1 + len(_INJECTED_TURNS)


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
    leaks, scanned = ex.self_check(out)
    assert leaks, "a secret in the digest must be caught by self_check"
    assert scanned == 1, f"expected the digest to be scanned, got {scanned}"


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
            _relative_out(monkeypatch, out),
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


# --- digest text is LF only, on every OS ----------------------------------------------------
# A CRLF inside a message reached the digest as it was, and a Windows text-mode write then turned
# every LF into CRLF on top of that, so a CRLF inside a message became CR CR LF and a reader that
# counts lines differently from Grep and the Read tool cited the wrong line (see the sweep tests).
# The invariant is that no file the extractor writes holds a carriage return at all. It is checked
# as this OS writes and again through an emulation of Windows text mode, so that a regression in
# the writing half is caught on a host whose text mode translates nothing.
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
    """Known positive for the emulation: a write with no newline argument gets CR LF, a write that
    names its newline does not, so a green result below is the writer's doing."""
    _emulate_windows_text_mode(monkeypatch)
    plain = tmp_path / "plain.txt"
    plain.write_text("a\nb", encoding="utf-8")
    exact = tmp_path / "exact.txt"
    exact.write_text("a\nb", encoding="utf-8", newline="\n")
    assert plain.read_bytes() == b"a\r\nb"
    assert exact.read_bytes() == b"a\nb"


def _bytes_jsonl(path, rows):
    """Write rows as bytes, so the fixture itself is the same on every OS."""
    path.write_bytes(("\n".join(json.dumps(r) for r in rows) + "\n").encode("utf-8"))


def _tool_call(call_id, name, command):
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": call_id,
                    "name": name,
                    "input": {"command": command},
                }
            ]
        },
    }


def _tool_result(call_id, text, is_error=False):
    block = {"type": "tool_result", "tool_use_id": call_id, "content": text}
    if is_error:
        block["is_error"] = True
    return {"type": "user", "message": {"content": [block]}}


# Every place a carriage return can enter: a command with a lone CR (the summary used to replace
# only LF), an error result with CRLF (its first characters land on the status line), a skill body
# written with CRLF line endings, and a sub-agent whose brief and error carry CRLF as well.
_CR_COMMAND = "echo a\rb"
_CR_ERROR = "Exit code 1\r\nboom line two\r\nsecond failing line"
_CR_SKILL_BODY = (
    "Base directory for this skill: skills/demo\r\n\r\n# Demo skill\r\nsteps"
)


def _carriage_return_corpus(tmp_path):
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "cr000001-0000-0000-0000-000000000000"
    _bytes_jsonl(
        sdir / f"{sid}.jsonl",
        [
            {
                "type": "user",
                "timestamp": "2026-06-20T10:00:00Z",
                "message": {
                    "content": [{"type": "text", "text": "please fix the build"}]
                },
            },
            # the same command twice: it is a repeated command, so the interaction digest lists it
            _tool_call("c1", "Bash", _CR_COMMAND),
            _tool_result("c1", _CR_ERROR, is_error=True),
            _tool_call("c2", "Bash", _CR_COMMAND),
            _tool_result("c2", "ok"),
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": _CR_SKILL_BODY}]},
                "isMeta": True,
            },
        ],
    )
    subdir = sdir / sid / "subagents"
    subdir.mkdir(parents=True)
    _bytes_jsonl(
        subdir / "agent-cr.jsonl",
        [
            {
                "type": "user",
                "message": {
                    "content": [{"type": "text", "text": "brief one\r\nbrief two"}]
                },
            },
            _tool_call("s1", "Bash", "make"),
            _tool_result("s1", _CR_ERROR, is_error=True),
        ],
    )
    return sdir, sid


@pytest.mark.parametrize(
    "windows_text_mode", [False, True], ids=["this-os", "windows-text-mode"]
)
def test_no_file_the_extractor_writes_holds_a_carriage_return(
    windows_text_mode, tmp_path, monkeypatch
):
    sdir, sid = _carriage_return_corpus(tmp_path)
    if windows_text_mode:
        _emulate_windows_text_mode(monkeypatch)
    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_sessions.py",
            str(sdir),
            _relative_out(monkeypatch, out),
            "--session",
            sid[:8],
            "--digest",
            "--self-check",
        ],
    )
    ex.main()

    written = [
        out / "aggregate.json",
        out / "interaction-digest.md",
        out / "sessions" / f"{sid}.md",
        *sorted((out / "sessions" / "sub").rglob("*.md")),
    ]
    # the surface in numbers: the aggregate, the interaction digest, the session digest and the
    # one emitted sub-agent digest
    assert len(written) == 4 and all(p.is_file() for p in written), written
    dirty = [p.name for p in written if b"\r" in p.read_bytes()]
    assert not dirty, f"carriage returns written to {dirty}"

    # the sizes the aggregate records are the bytes on disk, not the size before a translation
    agg = json.loads((out / "aggregate.json").read_text(encoding="utf-8"))
    s = agg["sessions"][0]
    assert s["transcriptBytes"] == written[2].stat().st_size
    assert s["subAgents"]["highSignal"][0]["emittedBytes"] == written[3].stat().st_size


def test_the_digests_carry_the_text_of_the_carriage_return_fixtures(tmp_path):
    """Known positive for the test above: each fixture's text reaches the digest (the first three
    checks hold before the fix too), and its line breaks are LF, so a result with no carriage
    return in it is not a digest with nothing in it."""
    sdir, sid = _carriage_return_corpus(tmp_path)
    sessions = tmp_path / "out" / "sessions"
    sessions.mkdir(parents=True)
    sess = ex.process_session(sdir / f"{sid}.jsonl", sessions)[0]
    digest = Path(sess["transcriptPath"]).read_bytes().decode("utf-8")
    assert "boom line two" in digest and "second failing line" in digest
    assert "Demo skill" in digest and "steps" in digest
    assert "echo a" in digest
    assert "Exit code 1\nboom line two\nsecond" in digest
    assert "Demo skill\nsteps" in digest


def test_a_command_summary_is_one_line_whatever_line_break_it_holds():
    assert ex.tool_input_summary("Bash", {"command": "a\r\nb\rc\nd"}) == "a b c d"


def test_a_subagent_digest_is_lf_only(tmp_path):
    sdir, sid = _carriage_return_corpus(tmp_path)
    text, _, _, _ = ex.render_subagent(sdir / sid / "subagents" / "agent-cr.jsonl")
    assert "brief one\nbrief two" in text
    assert "\r" not in text


# --- operator turns -------------------------------------------------------------------------
# The operator's own words reach a transcript by three carriers: a user record the operator typed,
# an attachment record for a message typed while the model was working, and the answer the question
# tool returns. ONE predicate, `operator_turn_text`, says which records are such a turn, and it
# feeds both the section of operator turns after the byte cap and the interaction digest's list and
# header. The fixtures are synthetic and carry the keys that decide the verdict in real
# transcripts; each text holds a unique marker (fxNN, qqNN for a question) so that a test can ask
# where it ended up.
def _text(text):
    return {"type": "text", "text": text}


def _human(content, source="sdk", **extra):
    record = {
        "type": "user",
        "message": {"role": "user", "content": content},
        "origin": {"kind": "human"},
        "turnOrigin": "human",
        "promptSource": source,
    }
    record.update(extra)
    return record


def _injected(content, **flags):
    """Text the harness put on the user channel: a record without a human origin."""
    return {"type": "user", "message": {"role": "user", "content": content}, **flags}


def _midturn(text, **overrides):
    attachment = {
        "type": "queued_command",
        "prompt": [_text(text)],
        "commandMode": "prompt",
        "origin": {"kind": "human"},
        "humanTurn": True,
    }
    attachment.update(overrides)
    return {"type": "attachment", "attachment": attachment}


def _question(call_id, question, tool="AskUserQuestion"):
    return _tool_call_with_input(
        call_id,
        tool,
        {
            "questions": [
                {
                    "question": question,
                    "header": "Q",
                    "multiSelect": False,
                    "options": [
                        {"label": "A", "description": "a"},
                        {"label": "B", "description": "b"},
                    ],
                }
            ]
        },
    )


def _tool_call_with_input(call_id, name, tool_input):
    return {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}
            ]
        },
    }


# The question tool's result is written in two wordings by different harness builds, with the same
# structure: the record-level toolUseResult carries the answers.
_ANSWER_WORDINGS = {
    "first": 'Your questions have been answered: "{q}"="{a}". You can now continue with these answers in mind.',
    "second": 'The user answered: "{q}"="{a}". Read the answers carefully before you go on.',
}


def _answered(call_id, question, answer, wording="first", tool_result=None):
    block = {
        "type": "tool_result",
        "tool_use_id": call_id,
        "content": _ANSWER_WORDINGS[wording].format(q=question, a=answer),
    }
    block.update(tool_result or {})
    return {
        "type": "user",
        "message": {"role": "user", "content": [block]},
        "toolUseResult": {
            "questions": [{"question": question}],
            "answers": {question: answer},
        },
        "sourceToolAssistantUUID": "a",
    }


def _result_record(call_id, text, tool_use_result, **block_extra):
    block = {"type": "tool_result", "tool_use_id": call_id, "content": text}
    block.update(block_extra)
    return {
        "type": "user",
        "message": {"role": "user", "content": [block]},
        "toolUseResult": tool_use_result,
    }


_IDE_NOTE = "<ide_opened_file>The user opened a file in the IDE.</ide_opened_file>"
_IDE_SELECTION = "<ide_selection>The user selected lines in the IDE.</ide_selection>"
_PEER = {"origin": {"kind": "peer"}, "turnOrigin": "peer", "promptSource": "system"}
_PEER_LEAD = "Another Claude session sent a message:"

# name -> (carrier, records, marker): the turns an operator typed or answered by, as real
# transcripts carry them (how many is asserted by the test that states the groups, not here).
# One slash command is NOT here: it stays with sessions[].slashCommands.
_OPERATOR_TURNS = {
    "typed-in-the-editor": (
        "user-record",
        [_human([_text("fx01 typed in the editor, this is wrong")])],
        "fx01",
    ),
    "typed-in-a-terminal": (
        "user-record",
        [_human("fx02 typed in a terminal, this is wrong", source="typed")],
        "fx02",
    ),
    "ide-note-then-typed": (
        "user-record",
        [
            _human(
                [_text(_IDE_NOTE), _text("fx03 typed after an ide note, this is wrong")]
            )
        ],
        "fx03",
    ),
    "pasted-only": (
        "user-record",
        [
            _human(
                [
                    _text(
                        '<pasted_content id="1">fx04 pasted body, this is wrong</pasted_content>'
                    )
                ]
            )
        ],
        "fx04",
    ),
    "ide-note-then-pasted": (
        "user-record",
        [
            _human(
                [
                    _text(_IDE_SELECTION),
                    _text(
                        '<pasted_content id="2">fx05 pasted after a selection, this is wrong</pasted_content>'
                    ),
                ]
            )
        ],
        "fx05",
    ),
    "queued-then-delivered-as-a-user-record": (
        "user-record",
        [
            _human(
                "fx06 queued then delivered as a user record, this is wrong",
                source="queued",
            )
        ],
        "fx06",
    ),
    "image-then-typed": (
        "user-record",
        [
            _human(
                [
                    {"type": "image", "source": {"type": "base64", "data": "AAAA"}},
                    _text("fx07 typed under an image, this is wrong"),
                ]
            )
        ],
        "fx07",
    ),
    "mid-turn-message": (
        "mid-turn",
        [_midturn("fx08 typed while the model was working, this is wrong")],
        "fx08",
    ),
    "answer-in-the-first-wording": (
        "answer",
        [
            _question("qa", "qq09 which option, is this wrong?"),
            _answered("qa", "qq09 which option, is this wrong?", "fx09 A is wrong"),
        ],
        "fx09",
    ),
    "answer-in-the-second-wording": (
        "answer",
        [
            _question("qb", "qq10 which option, is this wrong?"),
            _answered(
                "qb",
                "qq10 which option, is this wrong?",
                "fx10 free text, wrong",
                "second",
            ),
        ],
        "fx10",
    ),
}

# name -> (records, marker): text and records that are NOT the operator speaking.
_NOT_OPERATOR_TURNS = {
    # the operator did type this one; it is captured by sessions[].slashCommands
    "typed-slash-command": (
        [
            _human(
                [
                    _text(
                        "<command-message>demo</command-message>\n<command-name>/demo</command-name>\n"
                        "<command-args>fx21 args typed by the operator, this is wrong</command-args>"
                    )
                ]
            )
        ],
        "fx21",
    ),
    "queue-operation-copy": (
        [
            {
                "type": "queue-operation",
                "operation": "remove",
                "content": "fx22 typed mid-turn, this is wrong",
                "reason": "absorbed_mid_turn",
            }
        ],
        "fx22",
    ),
    "question-refused": (
        [
            _question("qr", "qq23 which option?"),
            _result_record(
                "qr",
                "The user doesn't want to proceed with this tool use. fx23 refused",
                "User rejected tool use",
                is_error=True,
            ),
            _injected([_text("[Request interrupted by user for tool use]")]),
        ],
        "fx23",
    ),
    "question-interrupted": (
        [
            _question("qi", "qq24 which option?"),
            _result_record(
                "qi",
                "[Tool call interrupted: the session ended before this call's result was recorded, fx24]",
                "[Tool call interrupted]",
                is_error=True,
            ),
        ],
        "fx24",
    ),
    "skill-body": (
        [
            _injected(
                [
                    _text(
                        "Base directory for this skill: skills/demo\n\n# Demo skill\nfx25 steps, never skip a check, this is wrong"
                    )
                ],
                isMeta=True,
                turnCompanion=True,
                sourceToolUseID="t1",
            )
        ],
        "fx25",
    ),
    "skill-invocation-wrapper": (
        [
            _injected(
                [
                    _text(
                        "<command-message>demo</command-message>\n<command-name>/demo</command-name>\n"
                        "<skill-format>true</skill-format> fx26 wrong"
                    )
                ],
                isMeta=True,
            )
        ],
        "fx26",
    ),
    "task-notification": (
        [
            _injected(
                "<task-notification>\n<task-id>t1</task-id>\n<summary>fx27 build wrong</summary>\n</task-notification>",
                origin={"kind": "task-notification"},
                turnOrigin="task_notification",
                promptSource="system",
            )
        ],
        "fx27",
    ),
    "hand-back": (
        [
            _injected(
                f"{_PEER_LEAD}\n\n<agent-message>fx28 report from a helper, wrong</agent-message>",
                isMeta=True,
                **_PEER,
            )
        ],
        "fx28",
    ),
    "peer-session-message": (
        [
            _injected(
                f"{_PEER_LEAD}\n\n<cross-session-message>fx29 from another session, wrong</cross-session-message>",
                isMeta=True,
                **_PEER,
            )
        ],
        "fx29",
    ),
    "compaction-summary": (
        [
            _injected(
                "This session is being continued from a previous conversation that ran out of context. fx30 summary: do not revert, wrong",
                isCompactSummary=True,
                isVisibleInTranscriptOnly=True,
                turnOrigin="human",
            )
        ],
        "fx30",
    ),
    "resume-nudge": (
        [
            _injected(
                [_text("Continue from where you left off. fx31 wrong")],
                isMeta=True,
                turnOrigin="system",
                promptSource="system",
            )
        ],
        "fx31",
    ),
    "idle-notice": (
        [
            _injected(
                '[Cross-session idle notice] "worker" is idle now. fx32 wrong',
                isMeta=True,
                turnOrigin="system",
                promptSource="system",
            )
        ],
        "fx32",
    ),
    "classifier-stop-notice": (
        [
            _injected(
                "Your response above was stopped by a safety classifier. fx33 do not repeat it, wrong",
                isMeta=True,
                turnCompanion=True,
            )
        ],
        "fx33",
    ),
    "skill-reinvocation-note": (
        [
            _injected(
                "(Re-invocation of /demo: the skill instructions are unchanged.) fx34 wrong",
                isMeta=True,
                turnCompanion=True,
                sourceToolUseID="t2",
            )
        ],
        "fx34",
    ),
    "image-note": (
        [
            _injected(
                "[Image: original 100x100, displayed at 50x50.] fx35 wrong",
                isMeta=True,
                turnCompanion=True,
            )
        ],
        "fx35",
    ),
    "prompt-sent-by-a-script": (
        [
            _injected(
                "fx36 prompt sent by a script, this is wrong",
                turnOrigin="sdk",
                promptSource="sdk",
            )
        ],
        "fx36",
    ),
    "scheduled-prompt": (
        [
            _injected(
                "fx37 scheduled run, this is wrong",
                isMeta=True,
                turnOrigin="scheduled",
                promptSource="system",
            )
        ],
        "fx37",
    ),
    "interrupt-marker": (
        [_injected([_text("[Request interrupted by user]")])],
        "Request interrupted",
    ),
    "local-command-caveat": (
        [
            _injected(
                "<local-command-caveat>Caveat: the messages below were generated while running local commands. fx39 wrong</local-command-caveat>",
                isMeta=True,
            )
        ],
        "fx39",
    ),
    "local-command-output": (
        [
            _injected(
                "<local-command-stdout>fx40 output of a local command, wrong</local-command-stdout>"
            )
        ],
        "fx40",
    ),
    "slash-command-without-origin": (
        [
            _injected(
                "<command-name>/demo</command-name>\n<command-message>demo</command-message>\n<command-args>fx41 args, this is wrong</command-args>"
            )
        ],
        "fx41",
    ),
    "system-reminder-block": (
        [
            _injected(
                [_text("<system-reminder>fx42 reminder text, wrong</system-reminder>")],
                isMeta=True,
            )
        ],
        "fx42",
    ),
    "queued-task-notification": (
        [
            _midturn(
                "<task-notification>fx43 wrong</task-notification>",
                prompt="<task-notification>fx43 wrong</task-notification>",
                commandMode="task-notification",
                origin={"kind": "task-notification"},
            )
        ],
        "fx43",
    ),
    "queued-peer-message": (
        [
            _midturn(
                "x",
                prompt="<agent-message>fx44 wrong</agent-message>",
                origin={"kind": "peer"},
                isMeta=True,
            )
        ],
        "fx44",
    ),
    "answers-key-on-another-tool": (
        [
            _tool_call_with_input("tx", "Bash", {"command": "echo hi"}),
            _result_record(
                "tx",
                "hello",
                {
                    "questions": [{"question": "q"}],
                    "answers": {"q": "fx45 planted answer"},
                },
            ),
        ],
        "fx45",
    ),
    "ordinary-tool-result": (
        [
            _tool_call_with_input("ty", "Bash", {"command": "echo hello"}),
            _result_record("ty", "hello fx46", {"stdout": "hello", "stderr": ""}),
        ],
        "fx46",
    ),
}


def _write_rows(path, rows):
    _bytes_jsonl(path, rows)
    return path


def _operator_turns_of(tmp_path, records):
    path = _write_rows(tmp_path / "one.jsonl", records)
    return list(ex.iter_operator_turns(path))


def test_the_operator_turn_fixtures_are_the_groups_the_tests_state():
    """The surface in numbers: ten turns (seven carried by a user record, one by an attachment,
    two by the question tool) and twenty-six records that are not one."""
    assert len(_OPERATOR_TURNS) == 10
    carriers = [carrier for carrier, _, _ in _OPERATOR_TURNS.values()]
    assert {c: carriers.count(c) for c in set(carriers)} == {
        "user-record": 7,
        "mid-turn": 1,
        "answer": 2,
    }
    assert len(_NOT_OPERATOR_TURNS) == 26
    markers = [m for _, _, m in _OPERATOR_TURNS.values()] + [
        m for _, m in _NOT_OPERATOR_TURNS.values()
    ]
    assert len(set(markers)) == len(markers), (
        "a marker shared by two fixtures proves nothing"
    )


@pytest.mark.parametrize("name", sorted(_OPERATOR_TURNS))
def test_the_predicate_admits_each_operator_turn(name, tmp_path):
    _, records, marker = _OPERATOR_TURNS[name]
    turns = _operator_turns_of(tmp_path, records)
    assert len(turns) == 1, turns
    assert marker in turns[0]
    assert "qq" not in turns[0], "the question text is not the operator's answer"
    assert "You can now continue" not in turns[0]
    assert "Read the answers carefully" not in turns[0]


@pytest.mark.parametrize("name", sorted(_NOT_OPERATOR_TURNS))
def test_the_predicate_refuses_everything_that_is_not_an_operator_turn(name, tmp_path):
    records, _ = _NOT_OPERATOR_TURNS[name]
    assert _operator_turns_of(tmp_path, records) == []


def test_the_text_blocks_of_one_user_record_are_one_turn(tmp_path):
    turns = _operator_turns_of(tmp_path, _OPERATOR_TURNS["ide-note-then-pasted"][1])
    assert turns == [
        '<pasted_content id="2">fx05 pasted after a selection, this is wrong</pasted_content>'
    ]
    two_blocks = _human([_text("fx51 first block"), _text("fx52 second block")])
    assert _operator_turns_of(tmp_path, [two_blocks]) == [
        "fx51 first block\nfx52 second block"
    ]


@pytest.mark.parametrize(
    ("flags", "admitted"),
    [
        ({}, True),
        ({"turnOrigin": "human"}, True),
        ({"isMeta": True}, False),
        ({"isCompactSummary": True}, False),
        ({"turnOrigin": "sdk"}, False),
        ({"turnOrigin": "system"}, False),
        ({"turnOrigin": "peer"}, False),
        ({"turnOrigin": "task_notification"}, False),
        ({"turnOrigin": "scheduled"}, False),
        ({"origin": {"kind": "coordinator"}}, False),
        ({"origin": {}}, False),
        ({"origin": "human"}, False),
        ({"origin": {"kind": "human"}}, True),
    ],
    ids=[
        "no-stamp-no-marker",
        "turn-origin-human",
        "meta",
        "compaction-summary",
        "sdk",
        "system",
        "peer",
        "task-notification",
        "scheduled",
        "other-origin-kind",
        "origin-without-kind",
        "origin-that-is-not-a-dict",
        "human-origin",
    ],
)
def test_the_stamp_decides_and_a_record_without_one_is_judged_by_its_markers(
    flags, admitted
):
    record = {
        "type": "user",
        "message": {"content": "please look at the build"},
        **flags,
    }
    assert bool(ex.operator_turn_text(record, {})) is admitted


def test_a_record_without_a_stamp_still_needs_to_pass_the_injected_text_prefixes():
    skill = {"type": "user", "message": {"content": "Base directory for this skill: x"}}
    assert ex.operator_turn_text(skill, {}) == ""


def test_an_answer_needs_the_question_tool_a_clean_result_and_an_answers_dict():
    answered = _answered("q1", "which?", "B")
    assert ex.operator_turn_text(answered, {"q1": "AskUserQuestion"}) == "B"
    assert ex.operator_turn_text(answered, {"q1": "Bash"}) == ""
    assert ex.operator_turn_text(answered, {}) == ""
    failed = _answered("q1", "which?", "B", tool_result={"is_error": True})
    assert ex.operator_turn_text(failed, {"q1": "AskUserQuestion"}) == ""
    no_dict = _answered("q1", "which?", "B")
    no_dict["toolUseResult"] = {"answers": ["B"]}
    assert ex.operator_turn_text(no_dict, {"q1": "AskUserQuestion"}) == ""


def test_several_answers_are_one_turn_in_question_order():
    record = _answered("q1", "first?", "B")
    record["toolUseResult"]["answers"] = {"first?": "B", "second?": "A, C", "third?": 3}
    assert ex.operator_turn_text(record, {"q1": "AskUserQuestion"}) == "B | A, C"


def test_a_mid_turn_prompt_may_be_a_plain_string():
    record = _midturn("x", prompt="fx53 typed while the model was working")
    assert ex.operator_turn_text(record, {}) == "fx53 typed while the model was working"


def test_the_text_of_an_operator_turn_is_redacted():
    key = "sk" + "-" + "k" * 24
    record = _human(f"my key is {key} please keep it out")
    text = ex.operator_turn_text(record, {})
    assert "kkkkkkkk" not in text and "[REDACTED_KEY]" in text


def test_a_record_that_mixes_an_answer_with_typed_text_is_read_for_the_answer_alone():
    """The stated limit of operator_turn_text: a record that holds a tool_result block is read for
    that block alone, so typed text beside an answer is not an operator turn. The transcripts
    measured never mix the two; this pins the limit so that changing it is a decision, not drift."""
    record = _answered("q1", "which?", "B")
    record["message"]["content"].append(_text("fx62 typed beside the answer"))
    assert ex.operator_turn_text(record, {"q1": "AskUserQuestion"}) == "B"


# A record of an unexpected shape must not stop the run. iter_operator_turns feeds the interaction
# digest and the session identity, and main() calls both outside its per-file guard, so a record
# that raised there would abort the whole run instead of skipping one session. These are shapes the
# harness is not known to write: a message that is not a dict, content that is not a list, an id
# that cannot be a dict key. Each is read as "not an operator turn", and the typed turn behind it is
# still found.
_TYPED_BEHIND_THE_ODD_RECORD = "fx61 typed behind the odd record"
_ODD_RECORDS = {
    "assistant-message-is-a-string": {"type": "assistant", "message": "a plain string"},
    "assistant-message-is-a-list": {"type": "assistant", "message": ["a", "list"]},
    "assistant-message-is-null": {"type": "assistant", "message": None},
    "assistant-without-a-message": {"type": "assistant"},
    "assistant-content-is-a-string": {
        "type": "assistant",
        "message": {"content": "not a list"},
    },
    "assistant-content-holds-non-dicts": {
        "type": "assistant",
        "message": {"content": [None, "x", 3, [], {"type": "tool_use"}]},
    },
    "tool-use-id-is-a-list": _tool_call_with_input(
        ["unhashable"], "AskUserQuestion", {}
    ),
    "tool-use-id-is-a-dict": _tool_call_with_input({"a": 1}, "AskUserQuestion", {}),
    "user-message-is-a-string": {
        "type": "user",
        "message": "a plain string",
        "origin": {"kind": "human"},
    },
    "user-message-is-a-list": {
        "type": "user",
        "message": ["a"],
        "origin": {"kind": "human"},
    },
    "result-id-is-a-list": {
        "type": "user",
        "message": {
            "content": [{"type": "tool_result", "tool_use_id": ["x"], "content": "y"}]
        },
        "toolUseResult": {"answers": {"q": "a"}},
    },
    "typed-text-is-a-number": _human([{"type": "text", "text": 5}]),
    "attachment-is-a-string": {"type": "attachment", "attachment": "a string"},
    "attachment-prompt-is-a-number": {
        "type": "attachment",
        "attachment": {
            "type": "queued_command",
            "commandMode": "prompt",
            "origin": {"kind": "human"},
            "prompt": 5,
        },
    },
}


def test_the_odd_records_are_the_shapes_the_test_states():
    """The surface in numbers: fourteen shapes, eight of an assistant record, four of a user
    record and two of an attachment."""
    types = [record["type"] for record in _ODD_RECORDS.values()]
    assert len(types) == 14
    assert {t: types.count(t) for t in set(types)} == {
        "assistant": 8,
        "user": 4,
        "attachment": 2,
    }


@pytest.mark.parametrize("name", sorted(_ODD_RECORDS))
def test_a_record_of_an_unexpected_shape_does_not_stop_the_operator_turns(
    name, tmp_path
):
    path = _write_rows(
        tmp_path / "odd.jsonl",
        [_ODD_RECORDS[name], _human(_TYPED_BEHIND_THE_ODD_RECORD)],
    )
    assert list(ex.iter_operator_turns(path)) == [_TYPED_BEHIND_THE_ODD_RECORD]
    assert (
        ex._session_identity(path)["firstUserMessage"] == _TYPED_BEHIND_THE_ODD_RECORD
    )


# The fixtures as one session, each followed by an assistant message, in a fixed order.
# counts.userMsgs of that session as the extractor reported it BEFORE operator turns were
# introduced (it counts every user record with a text block that is not system-prefixed, injected
# text included): the test below fails if answers or mid-turn messages ever move it.
_FIXTURE_SESSION_USER_MSGS = 19


def _fixture_session_rows():
    everything = {name: records for name, (_, records, _) in _OPERATOR_TURNS.items()}
    everything.update(
        {name: records for name, (records, _) in _NOT_OPERATOR_TURNS.items()}
    )
    rows = []
    for name in sorted(everything):
        rows.extend(everything[name])
        rows.append({"type": "assistant", "message": {"content": [_text("ok")]}})
    return rows


def _run_fixture_session(tmp_path, monkeypatch):
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "fix00000-0000-0000-0000-000000000000"
    _write_rows(sdir / f"{sid}.jsonl", _fixture_session_rows())
    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_sessions.py",
            str(sdir),
            _relative_out(monkeypatch, out),
            "--session",
            sid[:8],
            "--digest",
            "--self-check",
        ],
    )
    ex.main()
    agg = json.loads((out / "aggregate.json").read_text(encoding="utf-8"))
    return out, agg["sessions"][0]


def _listed(digest):
    """The numbered entries under the interaction digest's user-message heading."""
    lines = digest.split("\n")
    start = next(
        i for i, ln in enumerate(lines) if ln.startswith("## User-message sequence")
    )
    items = []
    for ln in lines[start + 1 :]:
        if ln.startswith("## "):
            break
        head, _, rest = ln.partition(". ")
        if head.isdigit():
            items.append(rest)
    return items


def test_the_interaction_digest_lists_each_operator_turn_and_nothing_else(
    tmp_path, monkeypatch
):
    out, _ = _run_fixture_session(tmp_path, monkeypatch)
    digest = (out / "interaction-digest.md").read_text(encoding="utf-8")
    listed = _listed(digest)
    expected = sorted(_OPERATOR_TURNS)
    assert len(listed) == len(expected) == 10
    for entry, name in zip(listed, expected, strict=True):
        assert _OPERATOR_TURNS[name][2] in entry, f"{name} is not where it should be"
    for name, (_, marker) in _NOT_OPERATOR_TURNS.items():
        assert marker not in digest, f"{name} reached the interaction digest"
    for _, _, marker in _OPERATOR_TURNS.values():
        assert digest.count(marker) == 1
    assert "qq" not in digest and "You can now continue" not in digest


def test_the_header_counts_the_operator_turns_it_lists(tmp_path, monkeypatch):
    out, sess = _run_fixture_session(tmp_path, monkeypatch)
    digest = (out / "interaction-digest.md").read_text(encoding="utf-8")
    assert "- Volume: 10 operator turns," in digest
    assert "User-message sequence (10 total" in digest
    # the user-channel record count survives, labelled as what it is
    assert (
        f"- User-channel records: {sess['counts']['userMsgs']} (counts.userMsgs;"
        in digest
    )
    assert "not a count of operator turns" in digest
    assert "user msgs" not in digest, (
        "the old label said user msgs for the record count"
    )


def test_counts_user_msgs_does_not_move(tmp_path, monkeypatch):
    """counts.userMsgs picks the deep-dive sessions, so counting answers and mid-turn messages as
    operator turns must not change it: neither a mid-turn attachment nor a tool result is a user
    message. The number is what the extractor reported for this session before the change."""
    _, sess = _run_fixture_session(tmp_path, monkeypatch)
    assert sess["counts"]["userMsgs"] == _FIXTURE_SESSION_USER_MSGS


# --- operator turns after the byte cap ----------------------------------------------------------
# A digest stops at TRANSCRIPT_BYTE_CAP and drops the tail, and the operator's last turns are in
# that tail. They go into a section of their own after the capped transcript, outside the cap, in
# the same "USER: " format the corrections sweep reads. Turns before the cut stay where they are.
_FILLER_RECORDS = 80  # 80 x 1.9 KB is well past the 120 KB cap


def _filler(i):
    return {
        "type": "assistant",
        "message": {"content": [_text("x" * 1900 + f" filler {i}")]},
    }


def _cap_crossing_rows(after_cap_turns=None):
    return [
        _human("first typed message", source="typed"),
        _midturn("first mid turn message"),
        _question("c1", "question 1"),
        _answered("c1", "question 1", "A"),
        _human("second typed message", source="typed"),
        *[_filler(i) for i in range(_FILLER_RECORDS)],
        *(
            after_cap_turns
            or [
                _human("third typed message after the cap", source="typed"),
                _midturn("second mid turn message after the cap"),
                _question("c2", "question 2"),
                _answered("c2", "question 2", "A"),
                _human("fourth typed message after the cap", source="typed"),
            ]
        ),
    ]


def _digest_lines_of(tmp_path, rows):
    path = _write_rows(tmp_path / "cap-session.jsonl", rows)
    sessions = tmp_path / "sessions"
    sessions.mkdir(exist_ok=True)
    sess = ex.process_session(path, sessions)[0]
    return sess, Path(sess["transcriptPath"]).read_bytes().decode("utf-8").split("\n")


def _section_start(lines):
    """The line that opens the operator section: it starts with a rule, which the corrections
    sweep treats as the end of the block before it."""
    return next(i for i, ln in enumerate(lines) if ln.startswith("---"))


def test_an_operator_turn_after_the_byte_cap_is_in_the_session_digest(tmp_path):
    sess, lines = _digest_lines_of(tmp_path, _cap_crossing_rows())
    kept = [ln for ln in lines if ln.startswith("ASSISTANT: x")]
    assert 0 < len(kept) < _FILLER_RECORDS, (
        "the cap must bite for this test to mean anything"
    )
    assert any("truncated at 120 KB" in ln for ln in lines)
    # every operator turn is in the digest exactly once, in order: the four before the cut stay
    # where they happened, the four after it follow in the section
    assert [ln for ln in lines if ln.startswith("USER: ")] == [
        "USER: first typed message",
        "USER: first mid turn message",
        "USER: A",
        "USER: second typed message",
        "USER: third typed message after the cap",
        "USER: second mid turn message after the cap",
        "USER: A",
        "USER: fourth typed message after the cap",
    ]
    assert sess["counts"]["userMsgs"] == 4, (
        "mid-turn messages and answers are not user messages"
    )


def test_the_operator_section_follows_the_capped_transcript_and_says_how_many(tmp_path):
    _, lines = _digest_lines_of(tmp_path, _cap_crossing_rows())
    start = _section_start(lines)
    assert "(4)" in lines[start]
    assert lines[start - 1] == "", (
        "a blank line sets the section apart from the truncation marker above it"
    )
    assert all(ln.startswith("USER: ") for ln in lines[start + 1 :])
    assert len(lines[start + 1 :]) == 4
    # nothing but the capped transcript precedes it, and the capped transcript ends at its marker
    assert any("truncated at 120 KB" in ln for ln in lines[:start])
    assert not any(ln.startswith("---") for ln in lines[start + 1 :])
    assert sum(1 for ln in lines if ln.startswith("---")) == 1


def test_a_session_under_the_cap_has_no_operator_section(tmp_path):
    rows = [
        _human("one typed message", source="typed"),
        _filler(0),
        _midturn("a mid turn message"),
    ]
    _, lines = _digest_lines_of(tmp_path, rows)
    assert not any(ln.startswith("---") for ln in lines)
    assert [ln for ln in lines if ln.startswith("USER: ")] == [
        "USER: one typed message",
        "USER: a mid turn message",
    ]


def test_each_turn_in_the_operator_section_is_clipped_at_the_per_message_cap(tmp_path):
    rows = _cap_crossing_rows([_human("w" * 5000, source="typed")])
    _, lines = _digest_lines_of(tmp_path, rows)
    tail = lines[_section_start(lines) + 1 :]
    assert tail == ["USER: " + "w" * ex.PER_MESSAGE_TEXT_CAP]


def test_the_operator_section_is_outside_the_byte_cap(tmp_path):
    """Operator turns after the cut add up to more than the cap, and none of them is dropped."""
    turns = [_human(f"turn {i} " + "t" * 1800, source="typed") for i in range(100)]
    _, lines = _digest_lines_of(tmp_path, _cap_crossing_rows(turns))
    tail = lines[_section_start(lines) + 1 :]
    assert len(tail) == 100
    assert sum(len(ln.encode("utf-8")) for ln in tail) > ex.TRANSCRIPT_BYTE_CAP
    assert [ln.split(" ")[2] for ln in tail] == [str(i) for i in range(100)]


def test_the_turn_that_crosses_the_cap_goes_to_the_section_and_not_to_the_floor(
    tmp_path, monkeypatch
):
    """The line the cap cuts at is itself an operator turn here: it is neither lost nor listed
    twice."""
    monkeypatch.setattr(ex, "TRANSCRIPT_BYTE_CAP", 120)
    rows = [
        _human("kept before the cut", source="typed"),
        _human("this one crosses the cap " + "z" * 200, source="typed"),
        _human("and this one follows it", source="typed"),
    ]
    _, lines = _digest_lines_of(tmp_path, rows)
    assert [ln for ln in lines if ln.startswith("USER: ")] == [
        "USER: kept before the cut",
        "USER: this one crosses the cap " + "z" * 200,
        "USER: and this one follows it",
    ]
    assert "(2)" in lines[_section_start(lines)]


def test_operator_turns_after_the_cap_are_redacted(tmp_path):
    key = "sk" + "-" + "k" * 24
    rows = _cap_crossing_rows([_human(f"key {key} after the cap", source="typed")])
    _, lines = _digest_lines_of(tmp_path, rows)
    tail = lines[_section_start(lines) + 1 :]
    assert tail == ["USER: key [REDACTED_KEY] after the cap"]


# The tests above use plain text after the cut. A real store also holds turns that start with a tag
# (a pasted body, an IDE note in front of the typed text), and a section that judged a turn by its
# first characters would drop exactly those while every test above stayed green.
@pytest.mark.parametrize("name", sorted(_OPERATOR_TURNS))
def test_each_kind_of_operator_turn_is_kept_after_the_cap(name, tmp_path):
    _, records, marker = _OPERATOR_TURNS[name]
    _, lines = _digest_lines_of(tmp_path, _cap_crossing_rows(records))
    assert any("truncated at 120 KB" in ln for ln in lines), "the cap must bite"
    tail = lines[_section_start(lines) + 1 :]
    assert len(tail) == 1 and marker in tail[0], tail
    assert sum(marker in ln for ln in lines) == 1, "in the digest once: in the section"


def test_the_section_is_the_list_the_interaction_digest_builds(tmp_path):
    """Every fixture comes after the cut. The ten operator turns are all in the section, in order,
    none of the twenty-six records that are not one is, and the section is the interaction digest's
    list turn for turn (each clipped as the section clips it): one predicate, two readers."""
    rows = [*[_filler(i) for i in range(_FILLER_RECORDS)], *_fixture_session_rows()]
    path = _write_rows(tmp_path / "all-after-the-cap.jsonl", rows)
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    sess = ex.process_session(path, sessions)[0]
    lines = Path(sess["transcriptPath"]).read_bytes().decode("utf-8").split("\n")
    start = _section_start(lines)
    assert not any(ln.startswith("USER: ") for ln in lines[:start])
    tail = lines[start + 1 :]
    listed = list(ex.iter_operator_turns(path))
    assert len(tail) == len(listed) == len(_OPERATOR_TURNS) == 10
    assert tail == [f"USER: {turn[: ex.PER_MESSAGE_TEXT_CAP]}" for turn in listed]
    for line, name in zip(tail, sorted(_OPERATOR_TURNS), strict=True):
        assert _OPERATOR_TURNS[name][2] in line, f"{name} is not where it should be"
    section = "\n".join(tail)
    for name, (_, marker) in _NOT_OPERATOR_TURNS.items():
        assert marker not in section, f"{name} reached the section"


# --- a key in an operator turn, whichever way it arrived ------------------------------------------
# Each carrier takes the operator's words out of a record and redacts them, so a carrier that
# forgot to would put a key into the session digest, into the section after the cut and into the
# interaction digest. The keys are built from fragments: the repository never holds a contiguous one.
def _key(fill):
    return "sk" + "-" + fill * 24


# name -> (the character the key is filled with, a function from the key and an id for the question
# call to the records that carry it). The three carriers and the record with no origin stamp.
_KEY_CARRIERS = {
    "typed-record": (
        "k",
        lambda key, _call: [_human(f"typed {key} typed", source="typed")],
    ),
    "record-without-an-origin-stamp": (
        "p",
        lambda key, _call: [
            {"type": "user", "message": {"content": f"typed {key} typed"}}
        ],
    ),
    "mid-turn-message": (
        "m",
        lambda key, _call: [_midturn(f"queued {key} queued")],
    ),
    "answer": (
        "n",
        lambda key, call: [
            _question(call, "which one?"),
            _answered(call, "which one?", f"picked {key} picked"),
        ],
    ),
}


def _run_key_session(tmp_path, monkeypatch, name):
    """One session that carries the key before the byte cap and again after it, run through the
    CLI. Returns a run of eight of the key's filler (what a leak is looked for by), the session
    digest, the interaction digest and the aggregate, each as text."""
    fill, records = _KEY_CARRIERS[name]
    key = _key(fill)
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "rd000001-0000-0000-0000-000000000000"
    rows = [
        _human("begin", source="typed"),
        *records(key, "before"),
        *[_filler(i) for i in range(_FILLER_RECORDS)],
        *records(key, "after"),
    ]
    _write_rows(sdir / f"{sid}.jsonl", rows)
    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_sessions.py",
            str(sdir),
            _relative_out(monkeypatch, out),
            "--session",
            sid[:8],
            "--digest",
        ],
    )
    ex.main()
    return (
        fill * 8,
        (out / "sessions" / f"{sid}.md").read_bytes().decode("utf-8"),
        (out / "interaction-digest.md").read_text(encoding="utf-8"),
        (out / "aggregate.json").read_text(encoding="utf-8"),
    )


def test_the_key_carriers_are_the_ways_the_predicate_reads_an_operator_turn():
    """The surface in numbers: the predicate redacts the text it returns once per way it reads a
    record, and there is one fixture for each. A way added or dropped there moves one of the two
    numbers, and the test below would otherwise claim more than it covers."""
    assert len(_KEY_CARRIERS) == 4
    assert inspect.getsource(ex.operator_turn_text).count("redact(") == 4


@pytest.mark.parametrize("name", sorted(_KEY_CARRIERS))
def test_a_key_in_an_operator_turn_is_redacted_whichever_way_it_arrived(
    name, tmp_path, monkeypatch
):
    fragment, digest, interaction, aggregate = _run_key_session(
        tmp_path, monkeypatch, name
    )
    for where, text in (
        ("the session digest", digest),
        ("the interaction digest", interaction),
        ("the aggregate", aggregate),
    ):
        assert fragment not in text, f"a key reached {where}"
    lines = digest.split("\n")
    tail = lines[_section_start(lines) + 1 :]
    assert len(tail) == 1 and "[REDACTED_KEY]" in tail[0], tail
    marked = [ln for ln in lines if ln.startswith("USER: ") and "[REDACTED_KEY]" in ln]
    assert len(marked) == 2, "one before the cut and one in the section after it"
    assert sum("[REDACTED_KEY]" in entry for entry in _listed(interaction)) == 2


@pytest.mark.parametrize("name", sorted(_KEY_CARRIERS))
def test_the_key_reaches_both_digests_when_nothing_redacts(name, tmp_path, monkeypatch):
    """Known positive for the test above: with the redactions emptied the same session carries the
    key into the session digest (before the cut and in the section) and into the interaction
    digest, so the absence asserted there is the redaction's doing and not a key that never got
    there."""
    monkeypatch.setattr(ex, "REDACTIONS", [])
    fragment, digest, interaction, _ = _run_key_session(tmp_path, monkeypatch, name)
    user_lines = [ln for ln in digest.split("\n") if ln.startswith("USER: ")]
    assert sum(fragment in ln for ln in user_lines) == 2
    assert sum(fragment in entry for entry in _listed(interaction)) == 2


def test_a_subagent_digest_has_no_operator_section(tmp_path):
    """No operator exists in a helper's transcript: its user channel is the lead agent. The shared
    predicate serves main-session digests only."""
    path = tmp_path / "agent-big.jsonl"
    _write_rows(
        path,
        [
            {"type": "user", "message": {"content": [_text("brief")]}},
            *[_filler(i) for i in range(_FILLER_RECORDS)],
            {"type": "user", "message": {"content": [_text("a later brief")]}},
        ],
    )
    text, _, _, _ = ex.render_subagent(path)
    assert "truncated at 120 KB" in text
    assert not any(ln.startswith("---") for ln in text.split("\n"))
    assert "a later brief" not in text


# --- hook denials ---------------------------------------------------------------------------
# A hook that blocks a tool call comes back as an error result whose text starts with the harness's
# own prefix, "PreToolUse:<Tool> hook error: ", followed by what the hook wrote. The count is made
# while the whole transcript is walked, so it does not depend on what the capped digest kept, and
# the result keeps the category it always had: this count sits beside the categories.
_HOOK_REASON = "Blocked by project policy; use the wrapper script instead."
_HOOK_DENIAL = f"PreToolUse:Bash hook error: {_HOOK_REASON}"


def _hook_session_rows(*calls):
    """A user turn, then one call per (tool, result text, is_error) triple."""
    rows = [_human("run the checks", source="typed")]
    for i, (tool, text, is_error) in enumerate(calls):
        rows.append(_tool_call(f"h{i}", tool, "make check"))
        rows.append(_tool_result(f"h{i}", text, is_error=is_error))
    return rows


def test_hook_denials_are_counted_whatever_the_tool_and_keep_their_category(tmp_path):
    rows = _hook_session_rows(
        ("Bash", _HOOK_DENIAL, True),
        ("Edit", "PreToolUse:Edit hook error: Blocked by project policy.", True),
        ("Write", "PreToolUse:Write hook error: [hook-script]: crashed", True),
    )
    sess, _lines = _digest_lines_of(tmp_path, rows)
    assert sess["hookDenials"] == 3
    # the categories are what they were before this count existed: the shell result is a runtime
    # exit and the other two tools' errors are tool errors, and none is a user refusal
    assert sess["errorsByCategory"] == {"runtime-exit": 1, "tool-error": 2}
    assert sess["userRejected"] == 0


def test_text_that_only_resembles_a_hook_denial_is_not_counted(tmp_path):
    rows = _hook_session_rows(
        # output that quotes a denial is data, and so is an error that quotes one mid-text
        ("Bash", f"build log: {_HOOK_DENIAL}", False),
        ("Bash", f"Exit code 1\n12:  -> ERROR(runtime-exit): {_HOOK_DENIAL}", True),
        # a file whose content starts with the prefix is data unless the tool itself failed
        ("Read", _HOOK_DENIAL, False),
        # a hook that never answered is a timeout, not a denial
        (
            "Read",
            "PreToolUse hook did not respond before its timeout (host client may be unreachable).",
            True,
        ),
        ("Bash", "PostToolUse:Bash hook error: not a block", True),
    )
    assert _digest_lines_of(tmp_path, rows)[0]["hookDenials"] == 0
    # known positive: the same session with one real denial added counts exactly that one
    real = _hook_session_rows(("Bash", _HOOK_DENIAL, True))
    (tmp_path / "again").mkdir()
    assert _digest_lines_of(tmp_path / "again", real)[0]["hookDenials"] == 1


def test_a_hook_reason_that_carries_no_prefix_is_not_counted(tmp_path):
    """The KNOWN LOSS. A hook that denies by JSON returns only its own reason as the result text:
    no prefix, no harness sentence. In a real store the only marker is the harness's
    toolDenialKind stamp ("permission-rule"), which a don't-ask mode, a built-in safety check and a
    protected path also carry, so a count by the stamp would add those. No marker names a hook, so
    this form is not counted and the aggregate says so in its documentation."""
    rows = _hook_session_rows(("Bash", _HOOK_REASON, True))
    rows[-1]["toolDenialKind"] = "permission-rule"
    assert _digest_lines_of(tmp_path, rows)[0]["hookDenials"] == 0


def test_a_hook_denial_after_the_byte_cap_is_still_counted(tmp_path):
    """The count is made over the whole transcript, not over the digest the cap cut short."""
    rows = [
        _human("run the checks", source="typed"),
        *[_filler(i) for i in range(_FILLER_RECORDS)],
        _tool_call("late", "Bash", "make check"),
        _tool_result("late", _HOOK_DENIAL, is_error=True),
    ]
    sess, lines = _digest_lines_of(tmp_path, rows)
    assert any("truncated at 120 KB" in ln for ln in lines)
    assert not any("PreToolUse" in ln for ln in lines), "the digest must have lost it"
    assert sess["hookDenials"] == 1


def test_hook_denials_inside_subagents_are_not_in_the_session_count(
    tmp_path, monkeypatch
):
    """The count is the main thread's. A helper's denial stays where it always was, in the
    sub-agent error taxonomy under its ordinary category."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "hk000001-0000-0000-0000-000000000000"
    _write_rows(sdir / f"{sid}.jsonl", _hook_session_rows(("Bash", _HOOK_DENIAL, True)))
    subdir = sdir / sid / "subagents"
    subdir.mkdir(parents=True)
    _write_rows(
        subdir / "agent-h.jsonl", _hook_session_rows(("Bash", _HOOK_DENIAL, True))
    )
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    s = agg["sessions"][0]
    assert s["hookDenials"] == 1
    assert s["subAgents"]["errorsByCategory"] == {"runtime-exit": 1}


def test_the_aggregate_rolls_hook_denials_up(tmp_path, monkeypatch, capsys):
    sdir = tmp_path / "src"
    sdir.mkdir()
    _write_rows(
        sdir / "aaaa1111-0000-0000-0000-000000000000.jsonl",
        _hook_session_rows(("Bash", _HOOK_DENIAL, True), ("Bash", _HOOK_DENIAL, True)),
    )
    _write_rows(
        sdir / "bbbb2222-0000-0000-0000-000000000000.jsonl",
        _hook_session_rows(("Bash", _HOOK_DENIAL, True)),
    )
    _write_rows(
        sdir / "cccc3333-0000-0000-0000-000000000000.jsonl",
        _hook_session_rows(("Bash", "ok", False)),
    )
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    assert "hookDenials" in ex.SCHEMA_KEYS["session"]
    per_session = {s["sessionId"][:8]: s["hookDenials"] for s in agg["sessions"]}
    assert per_session == {"aaaa1111": 2, "bbbb2222": 1, "cccc3333": 0}
    bucket = agg["errorTaxonomy"]["hookDenials"]
    assert set(bucket) == {"count", "sessions", "samples"}
    assert bucket["count"] == 3
    assert sorted(bucket["sessions"]) == ["aaaa1111", "bbbb2222"]
    assert 0 < len(bucket["samples"]) <= 8
    assert all(smp.endswith(_HOOK_DENIAL) for smp in bucket["samples"])
    # the categories stay the categories: three runtime exits, and the user-refusal bucket is empty
    assert agg["errorTaxonomy"]["byCategory"]["runtime-exit"]["count"] == 3
    assert agg["errorTaxonomy"]["userRejected"]["count"] == 0
    assert "hook-denials=3" in capsys.readouterr().err


def test_hook_denials_are_counted_beyond_the_sample_caps(tmp_path, monkeypatch, capsys):
    """The samples are capped and the count is not. A session keeps SAMPLES_PER_CATEGORY samples
    and the roll-up keeps eight in all; these four sessions go past both, so a count taken while
    the samples still fit, or taken from them, comes out lower than the number of denials."""
    denials = {"aaaa1111": 7, "bbbb2222": 4, "cccc3333": 2, "dddd4444": 5}
    kept = sum(min(n, ex.SAMPLES_PER_CATEGORY) for n in denials.values())
    total = sum(denials.values())
    assert (ex.SAMPLES_PER_CATEGORY, kept, total) == (3, 11, 18), (
        "the fixture must go past the per-session cap (3 + 3 + 2 + 3 kept of 18) and the "
        "roll-up's cap of eight"
    )
    sdir = tmp_path / "src"
    sdir.mkdir()
    for sid8, n in denials.items():
        _write_rows(
            sdir / f"{sid8}-0000-0000-0000-000000000000.jsonl",
            _hook_session_rows(*[("Bash", _HOOK_DENIAL, True)] * n),
        )
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    assert {s["sessionId"][:8]: s["hookDenials"] for s in agg["sessions"]} == denials
    bucket = agg["errorTaxonomy"]["hookDenials"]
    assert bucket["count"] == total
    assert len(bucket["samples"]) == 8 < kept, "the samples are the capped part"
    assert f"hook-denials={total}" in capsys.readouterr().err


# A hook's own words are in the sample, and the hook's author wrote them: a key in them must not
# reach the aggregate. The sample is redacted on its own line, apart from the category samples.
def _run_hook_key_session(tmp_path, monkeypatch):
    key = _key("h")
    denial = f"PreToolUse:Bash hook error: blocked, token {key}, ask the owner"
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "hk000002-0000-0000-0000-000000000000"
    _write_rows(sdir / f"{sid}.jsonl", _hook_session_rows(("Bash", denial, True)))
    agg = _run(sdir, tmp_path / "out", monkeypatch, self_check=False)
    digest = (tmp_path / "out" / "sessions" / f"{sid}.md").read_bytes().decode("utf-8")
    return "h" * 8, agg["errorTaxonomy"]["hookDenials"]["samples"], digest, agg


def test_a_key_in_a_hook_denial_is_redacted_in_the_samples(tmp_path, monkeypatch):
    fragment, samples, digest, agg = _run_hook_key_session(tmp_path, monkeypatch)
    assert len(samples) == 1 and "[REDACTED_KEY]" in samples[0], samples
    assert fragment not in json.dumps(agg) and fragment not in digest


def test_the_hook_sample_carries_the_key_when_nothing_redacts(tmp_path, monkeypatch):
    """Known positive for the test above: with the redactions emptied the sample holds the key, so
    its absence there is the redaction's doing and not a key that never reached the sample."""
    monkeypatch.setattr(ex, "REDACTIONS", [])
    fragment, samples, _, _ = _run_hook_key_session(tmp_path, monkeypatch)
    assert len(samples) == 1 and fragment in samples[0], samples


# --- what a helper's digest can show --------------------------------------------------------
# A sub-agent digest keeps the helper's messages and tool calls. A tool call's return is cut to
# "ok" or an error line, and a plain-text final report to PER_MESSAGE_TEXT_CAP characters, so a
# structured returned result (the payload of a structured-output call, the content of a tool
# result) is not in it. The report template says so, because an analyst who reads only the digest
# cannot otherwise tell "the helper returned nothing" from "the digest cannot show it".
_REPORT_TEMPLATE = (
    Path(__file__).resolve().parent.parent / "references" / "report-template.md"
)


def test_a_subagent_digest_cannot_show_a_structured_returned_result(tmp_path):
    long_report = "REPORT " + "r" * 2990
    path = tmp_path / "agent-h.jsonl"
    _write_rows(
        path,
        [
            {"type": "user", "message": {"content": [_text("do the task")]}},
            _tool_call_with_input(
                "so1", "StructuredOutput", {"parts": [{"part": "STRUCTUREDPAYLOAD"}]}
            ),
            _result_record("so1", "STRUCTUREDRETURN accepted", {"ok": True}),
            {"type": "assistant", "message": {"content": [_text(long_report)]}},
        ],
    )
    text, _, _, _ = ex.render_subagent(path)
    lines = text.split("\n")
    assert "STRUCTUREDPAYLOAD" not in text and "STRUCTUREDRETURN" not in text
    assert "  [StructuredOutput] " in lines and "    -> ok" in lines
    report = next(ln for ln in lines if ln.startswith("ASSISTANT: REPORT"))
    assert (
        len(report) == len("ASSISTANT: ") + ex.PER_MESSAGE_TEXT_CAP < len(long_report)
    )


def test_the_report_template_says_a_helper_digest_cannot_show_a_structured_result():
    flat = " ".join(_REPORT_TEMPLATE.read_text(encoding="utf-8").split())
    section = flat.split("### Sub-Agent Deep-Dive")[1].split("## ")[0]
    assert "sub-agent digest cannot show a structured returned result" in section
    assert "PER_MESSAGE_TEXT_CAP" in section


def test_the_report_template_says_dotnet_build_failures_moved_to_the_build_class():
    """A report made before .NET build output counted as a build error filed it as a test failure
    or a plain non-zero exit, so error counts set against that report's window move."""
    flat = " ".join(_REPORT_TEMPLATE.read_text(encoding="utf-8").split())
    assert flat.count("## Pipeline Health") == 1, "the Pipeline Health heading is gone"
    assert "## Recommendations" in flat, "the heading after Pipeline Health is gone"
    section = flat.split("## Pipeline Health")[1].split("## Recommendations")[0]
    for phrase in (
        ".NET build failures",
        "`build-compile`",
        "`test-failure`",
        "`runtime-exit`",
        "report made before",
        "counts move",
    ):
        assert phrase in section, phrase


# --- replayed events ------------------------------------------------------------------------
# A session that was resumed or compacted can write earlier events into its transcript a second
# time. A repeat has the same top-level uuid, message, parent and timestamp as the original and a
# re-stamped slug, so it is not the same line byte for byte, and counted as written every tool call
# in the replayed span counts twice. iter_jsonl keys on the uuid alone, keeps the first occurrence
# and lets a line with no usable uuid through. The fixture has the shape of a real replay (the
# whole earlier span once more, in order, after the events that followed it) and the traps a wrong
# key falls into: two lines that share a message id (one API message is written as several lines,
# each with its own uuid), two turns with the same text and different uuids, a request blob that
# re-carries a tool call, and state lines that carry no uuid at all.
def _event(row, uuid, parent, message_id=None, **extra):
    event = {**row, "uuid": uuid, "parentUuid": parent, **extra}
    if message_id:
        event["message"] = {**row["message"], "id": message_id}
    return event


_REPLAYED_SPAN = [
    _event({"type": "user", "message": {"content": "run"}}, "u1", None),
    _event(_tool_call("t1", "Bash", "pytest"), "a1", "u1", "m1"),
    _event(_tool_result("t1", "Exit code 1 FAILED", is_error=True), "u2", "a1"),
]
_THINKING_TURN = {
    "type": "assistant",
    "message": {"content": [{"type": "thinking", "thinking": "x"}]},
}
_REQUEST_BLOB = {
    "type": "api-request-blob",
    "hash": "h",
    "message": {
        "content": [{"type": "tool_use", "id": "t2", "name": "Read", "input": {}}]
    },
}
_YES = {"type": "user", "message": {"content": "yes"}}


def _replay_rows():
    """Twelve rows: a state line, the span, four more events and a request blob, the span again."""
    return [
        {"type": "ai-title", "aiTitle": "t"},
        *_REPLAYED_SPAN,
        _event(_THINKING_TURN, "a2", "u2", "m2"),
        _event(
            _tool_call_with_input("t2", "Read", {"file_path": "a.py"}), "a3", "a2", "m2"
        ),
        _REQUEST_BLOB,
        _event(_YES, "u3", "a3"),
        _event(_YES, "u4", "u3"),
        *[{**row, "slug": "s"} for row in _REPLAYED_SPAN],
    ]


def _stamped(rows):
    """`rows` with a timestamp on each event, in file order. A repeat keeps the stamp of the event
    it repeats, as real replays do, so the stamps run backwards where the replay begins."""
    stamps = {}
    stamped = []
    for i, row in enumerate(rows):
        if "uuid" not in row:
            stamped.append(row)
            continue
        stamp = stamps.setdefault(row["uuid"], f"2026-06-20T10:00:{i:02d}Z")
        stamped.append({**row, "timestamp": stamp})
    return stamped


def _process(tmp_path, rows, name="replay", replays=None):
    """process_session over `rows`, written as <name>.jsonl; the session it returns."""
    path = _write_rows(tmp_path / f"{name}.jsonl", rows)
    sessions = tmp_path / "sessions"
    sessions.mkdir(exist_ok=True)
    args = () if replays is None else (replays,)
    return ex.process_session(path, sessions, *args)[0]


def test_the_replay_fixture_is_the_shape_the_tests_state():
    """The surface in numbers: twelve rows, ten of them events with a uuid, seven distinct uuids
    (so three repeats), and two rows with none: the state line and the request blob."""
    rows = _replay_rows()
    uuids = [row["uuid"] for row in rows if "uuid" in row]
    assert (len(rows), len(uuids), len(set(uuids))) == (12, 10, 7)
    without = [row["type"] for row in rows if "uuid" not in row]
    assert without == ["ai-title", "api-request-blob"]
    assert [row["slug"] for row in rows if "slug" in row] == ["s"] * 3


def test_a_replayed_span_counts_each_tool_call_once(tmp_path):
    sess = _process(tmp_path, _replay_rows())
    # the replayed "run" is not a fourth user message, and the second "yes" is a third
    assert sess["counts"] == {
        "userMsgs": 3,
        "assistantMsgs": 3,
        "toolUse": 2,
        "toolResult": 1,
        "thinking": 1,
    }
    assert sess["toolsUsed"] == {"Bash": 1, "Read": 1}
    assert sess["errorsByCategory"] == {"test-failure": 1}
    assert sess["behavior"]["repeatedCommands"] == []
    assert sess["behavior"]["buildTestLoops"] == []


def test_two_turns_with_the_same_text_and_different_uuids_are_both_kept(tmp_path):
    """A key on the message text would fold the second "yes" into the first. Real transcripts hold
    many such pairs, and here the replay of the first one is the only repeat."""
    rows = [
        _event(_YES, "u3", None),
        _event(_YES, "u4", "u3"),
        _event(_YES, "u3", None, slug="s"),
    ]
    assert _process(tmp_path, rows)["counts"]["userMsgs"] == 2


def test_events_that_share_a_message_id_are_each_kept(tmp_path):
    """One API message is written as several lines, each with its own uuid. A key on the message id
    would keep the first and lose the tool call the second one carries."""
    call = _tool_call_with_input("t2", "Read", {"file_path": "a.py"})
    rows = [
        _event(_THINKING_TURN, "a2", None, "m2"),
        _event(call, "a3", "a2", "m2"),
        _event(_THINKING_TURN, "a2", None, "m2", slug="s"),
    ]
    counts = _process(tmp_path, rows)["counts"]
    assert (counts["assistantMsgs"], counts["thinking"], counts["toolUse"]) == (2, 1, 1)


@pytest.mark.parametrize(
    "unusable",
    [
        {},
        {"uuid": None},
        {"uuid": ""},
        {"uuid": 7},
        {"uuid": ["x"]},
        {"uuid": {"k": 1}},
    ],
    ids=["absent", "null", "empty", "number", "list", "object"],
)
def test_lines_without_a_usable_uuid_are_each_kept(unusable, tmp_path):
    """State lines carry no uuid, and neither do the rows of an older transcript. Two such lines
    that read alike are two events, never folded into one, and an id that cannot be a dict key (a
    list) must not stop the run."""
    row = {**_tool_call("t9", "Bash", "make"), **unusable}
    sess = _process(
        tmp_path, [row, row, {"type": "user", "message": {"content": "go"}}]
    )
    assert sess["counts"]["toolUse"] == 2


def test_iter_jsonl_yields_each_event_once_and_keeps_the_first_occurrence(tmp_path):
    path = _write_rows(
        tmp_path / "t.jsonl",
        [
            {"type": "user", "uuid": "u1", "cwd": "first"},
            {"type": "user", "uuid": "u2"},
            {"type": "user", "uuid": "u1", "cwd": "second", "slug": "s"},
        ],
    )
    events = list(ex.iter_jsonl(path))
    assert [e["uuid"] for e in events] == ["u1", "u2"]
    assert events[0]["cwd"] == "first"


def test_iter_jsonl_reports_the_uuid_of_each_repeat_it_leaves_out(tmp_path):
    path = _write_rows(tmp_path / "t.jsonl", _replay_rows())
    left_out = []
    assert len(list(ex.iter_jsonl(path, left_out))) == 9
    assert left_out == ["u1", "a1", "u2"]
    # each call remembers only its own file: the same read again finds the same nine
    assert len(list(ex.iter_jsonl(path))) == 9


def test_a_replayed_operator_turn_is_listed_once(tmp_path):
    rows = [
        _human("first typed message", source="typed", uuid="u1"),
        _human("first typed message", source="typed", uuid="u2"),
        _human("first typed message", source="typed", uuid="u1", slug="s"),
    ]
    assert _operator_turns_of(tmp_path, rows) == ["first typed message"] * 2


def test_a_replayed_session_digest_holds_each_turn_and_call_once(tmp_path):
    _, lines = _digest_lines_of(tmp_path, _replay_rows())
    users = [ln for ln in lines if ln.startswith("USER: ")]
    assert users == ["USER: run", "USER: yes", "USER: yes"]
    assert lines.count("  [Bash] pytest") == 1


def test_a_replay_in_a_subagent_transcript_is_counted_once(tmp_path):
    path = _write_rows(tmp_path / "agent-r.jsonl", _replay_rows())
    text, msgs, errs, _ = ex.render_subagent(path)
    assert msgs == 7  # u1 a1 u2 a2 a3 u3 u4, once each
    assert errs == {"test-failure": 1}
    assert text.split("\n").count("  [Bash] pytest") == 1


def test_process_session_reports_the_repeats_it_left_out_by_session(tmp_path):
    replays = {}
    _process(tmp_path, _replay_rows(), replays=replays)
    assert replays == {"replay": 3}
    # a session with no repeat leaves no entry
    _process(tmp_path, _replay_rows()[:9], name="plain", replays=replays)
    assert replays == {"replay": 3}
    # a helper's repeats join the entry of the session that ran it
    helpers = tmp_path / "replay" / "subagents"
    helpers.mkdir(parents=True)
    _write_rows(helpers / "agent-r.jsonl", _replay_rows())
    replays.clear()
    _process(tmp_path, _replay_rows(), replays=replays)
    assert replays == {"replay": 6}


def test_a_replay_only_in_a_helper_transcript_is_reported_for_its_session(tmp_path):
    """The test above gives the main transcript a replay as well as the helper's. Here only the
    helper's replays, so an entry made only when the main transcript repeats, or one counted
    before the helpers are read, never sees the session."""
    helpers = tmp_path / "replay" / "subagents"
    helpers.mkdir(parents=True)
    helper = _write_rows(helpers / "agent-r.jsonl", _replay_rows()[:9])
    replays = {}
    _process(tmp_path, _replay_rows()[:9], replays=replays)
    assert replays == {}  # known negative: the helper repeats nothing either
    _write_rows(helper, _replay_rows())
    _process(tmp_path, _replay_rows()[:9], replays=replays)
    assert replays == {"replay": 3}


def _replay_lines(captured):
    return [ln for ln in captured.err.splitlines() if ln.startswith("Replayed events")]


def test_the_replays_left_out_are_reported_once_on_stderr(
    tmp_path, monkeypatch, capsys
):
    sdir = tmp_path / "src"
    sdir.mkdir()
    replayed, other, plain = (
        f"{head}-0000-0000-0000-000000000000"
        for head in ("aaaa1111", "bbbb2222", "cccc3333")
    )
    _write_rows(sdir / f"{replayed}.jsonl", _replay_rows())
    helpers = sdir / replayed / "subagents"
    helpers.mkdir(parents=True)
    _write_rows(helpers / "agent-r.jsonl", _replay_rows())
    _write_rows(sdir / f"{other}.jsonl", _replay_rows())
    _write_rows(sdir / f"{plain}.jsonl", _replay_rows()[:9])
    _run(sdir, tmp_path / "out", monkeypatch)
    lines = _replay_lines(capsys.readouterr())
    # three in the main transcript and three in the helper's, all in one session, and three in another
    assert len(lines) == 1, lines
    assert "9 repeated event(s)" in lines[0] and "2 session(s)" in lines[0], lines[0]


def test_a_replay_only_in_a_helper_transcript_is_reported_on_stderr(
    tmp_path, monkeypatch, capsys
):
    """The line is for the repeats of a whole session. A session whose own transcript repeats
    nothing is still reported when a helper's does, and not otherwise."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "aaaa1111-0000-0000-0000-000000000000"
    _write_rows(sdir / f"{sid}.jsonl", _replay_rows()[:9])
    helper = sdir / sid / "subagents" / "agent-r.jsonl"
    helper.parent.mkdir(parents=True)
    _write_rows(helper, _replay_rows()[:9])
    _run(sdir, tmp_path / "out", monkeypatch)
    # known negative: nothing repeats anywhere, so nothing is reported
    assert _replay_lines(capsys.readouterr()) == []
    _write_rows(helper, _replay_rows())
    _run(sdir, tmp_path / "again", monkeypatch)
    lines = _replay_lines(capsys.readouterr())
    assert len(lines) == 1, lines
    assert "3 repeated event(s)" in lines[0] and "1 session(s)" in lines[0], lines[0]


def test_nothing_is_reported_when_nothing_was_replayed(tmp_path, monkeypatch, capsys):
    sdir = tmp_path / "src"
    sdir.mkdir()
    transcript = sdir / "aaaa1111-0000-0000-0000-000000000000.jsonl"
    _write_rows(transcript, _replay_rows()[:9])
    _run(sdir, tmp_path / "out", monkeypatch)
    assert _replay_lines(capsys.readouterr()) == []
    # known positive: the same session with the replay put back is reported
    _write_rows(transcript, _replay_rows())
    _run(sdir, tmp_path / "again", monkeypatch)
    assert len(_replay_lines(capsys.readouterr())) == 1


def test_a_replay_in_a_session_the_aggregate_leaves_out_is_not_reported(
    tmp_path, monkeypatch, capsys
):
    """The line sits beside the aggregate's counts and explains them, so it counts the sessions
    that reached the aggregate: this one has no real user message and is dropped."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    dropped = [
        _event(_THINKING_TURN, "a2", None, "m2"),
        _event(_THINKING_TURN, "a2", None, "m2", slug="s"),
    ]
    _write_rows(sdir / "aaaa1111-0000-0000-0000-000000000000.jsonl", dropped)
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    assert agg["sessions"] == []
    assert _replay_lines(capsys.readouterr()) == []


def test_the_aggregate_has_no_key_for_replays(tmp_path, monkeypatch):
    """The number is for stderr: a key in the aggregate would change the schema for a count that a
    run reports once. The same session without its replay shows the same keys."""
    name = "aaaa1111-0000-0000-0000-000000000000.jsonl"
    keys = {}
    for label, rows in (("with", _replay_rows()), ("without", _replay_rows()[:9])):
        sdir = tmp_path / f"src-{label}"
        sdir.mkdir()
        _write_rows(sdir / name, rows)
        keys[label] = _run(sdir, tmp_path / f"out-{label}", monkeypatch)
    agg = keys["with"]
    assert set(agg) == set(ex.SCHEMA_KEYS["top"])
    assert [set(s) for s in agg["sessions"]] == [set(ex.SCHEMA_KEYS["session"])]
    for part in ("stats", "errorTaxonomy", "subAgentErrorTaxonomy"):
        assert set(agg[part]) == set(keys["without"][part]), part
    assert "replay" not in json.dumps(agg).lower()


def test_the_prescan_still_reads_a_replayed_transcript(tmp_path, monkeypatch, capsys):
    """The pre-scan reads timestamps off the raw lines and never goes through iter_jsonl, and a
    repeat carries the original's timestamp: a window around the session keeps it, counted once,
    and a window after it skips it before it is parsed, so nothing is reported for it."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    _write_rows(
        sdir / "aaaa1111-0000-0000-0000-000000000000.jsonl", _stamped(_replay_rows())
    )

    def run(label, *window):
        out = tmp_path / label
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "extract_sessions.py",
                str(sdir),
                _relative_out(monkeypatch, out),
                *window,
            ],
        )
        ex.main()
        agg = json.loads((out / "aggregate.json").read_text(encoding="utf-8"))
        return agg, capsys.readouterr()

    agg, captured = run("inside", "--since", "2026-06-20", "--until", "2026-06-20")
    assert [s["counts"]["toolUse"] for s in agg["sessions"]] == [2]
    assert len(_replay_lines(captured)) == 1
    assert "Pre-scan skipped 0" in captured.err

    agg, captured = run("after", "--since", "2026-06-25")
    assert agg["sessions"] == []
    assert "Pre-scan skipped 1" in captured.err
    assert _replay_lines(captured) == []


def test_the_interaction_digest_counts_a_replayed_turn_once(tmp_path, monkeypatch):
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "rp000001-0000-0000-0000-000000000000"
    _write_rows(sdir / f"{sid}.jsonl", _replay_rows())
    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_sessions.py",
            str(sdir),
            _relative_out(monkeypatch, out),
            "--session",
            sid[:8],
            "--digest",
        ],
    )
    ex.main()
    digest = (out / "interaction-digest.md").read_text(encoding="utf-8")
    assert _listed(digest) == ["run", "yes", "yes"]
    assert "- Volume: 3 operator turns," in digest


# --- sub-agent files ------------------------------------------------------------------------
# A session folder has three siblings: subagents/, workflows/ and tool-results/, and every .jsonl
# file of the folder lives under subagents/. A helper's transcript is agent-<id>.jsonl, directly
# under it or under workflows/wf_<run>/. Each workflow run also leaves one journal.jsonl beside
# its agents: the run's event log (no message, no uuid), which is not a transcript, so counting it
# made every workflow run one helper too many. A sidecar (agent-<id>.meta.json) is not a filter
# either: real agent transcripts exist without one.
_SUBAGENT_SIDECARS = {  # path under subagents/ -> the sidecar's agentType, None for no sidecar
    "agent-a1.jsonl": "general-purpose",
    "agent-a2.jsonl": None,
    "workflows/wf_r1/agent-a3.jsonl": "workflow-subagent",
    "workflows/wf_r1/agent-a4.jsonl": "workflow-subagent",
    "workflows/wf_r2/agent-a5.jsonl": "workflow-subagent",
}
_JOURNALS = ("workflows/wf_r1/journal.jsonl", "workflows/wf_r2/journal.jsonl")
# the siblings of subagents/ that hold no transcript at all (paths under the session folder)
_RUN_FILES = (
    "workflows/wf_r1.json",
    "workflows/scripts/demo-wf_r1.js",
    "tool-results/toolu_1.txt",
)


def _journal_rows():
    """A run's event log, longer than any agent transcript here: launched, started, then results."""
    return [
        {"event": "launched", "run": "r1"},
        {"event": "started", "agentId": "a3"},
        *({"event": "result", "agentId": "a3", "step": i} for i in range(40)),
    ]


def _subagent_layout(tmp_path):
    """One session that ran two plain helpers and two workflow runs, laid out as the harness does.
    Returns the source dir, the session id and the paths of the five agent transcripts."""
    sdir = tmp_path / "src"
    sdir.mkdir()
    sid = "sa000001-0000-0000-0000-000000000000"
    _write_rows(sdir / f"{sid}.jsonl", _minimal_session_rows())
    root = sdir / sid
    agents = []
    for rel, agent_type in _SUBAGENT_SIDECARS.items():
        path = root / "subagents" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_rows(
            path,
            [
                {"type": "user", "message": {"content": [_text("do the task")]}},
                {"type": "assistant", "message": {"content": [_text("done")]}},
            ],
        )
        if agent_type:
            path.with_suffix(".meta.json").write_text(
                json.dumps({"agentType": agent_type, "description": "a helper"}),
                encoding="utf-8",
            )
        agents.append(path)
    for rel in _JOURNALS:
        _write_rows(root / "subagents" / rel, _journal_rows())
    for rel in _RUN_FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    return sdir, sid, agents


def test_only_agent_transcripts_are_sub_agents(tmp_path, monkeypatch):
    sdir, sid, agents = _subagent_layout(tmp_path)
    journals = [sdir / sid / "subagents" / rel for rel in _JOURNALS]
    assert min(j.stat().st_size for j in journals) > max(
        a.stat().st_size for a in agents
    ), "the journals must be the largest files, or a count that took them would hide it"
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    sub = agg["sessions"][0]["subAgents"]
    assert sub["count"] == len(_SUBAGENT_SIDECARS) == 5
    assert sub["bytes"] == sum(a.stat().st_size for a in agents)
    assert sub["msgs"] == 10  # a user turn and an assistant turn in each of the five
    # the agent with no sidecar is still an agent, typed "?"
    assert sorted(a["type"] for a in sub["agents"]) == [
        "?",
        "general-purpose",
        "workflow-subagent",
        "workflow-subagent",
        "workflow-subagent",
    ]
    assert agg["stats"]["subAgent"]["files"] == 5
    assert agg["subAgentErrorTaxonomy"]["totalAgents"] == 5
    # a journal among the largest files would also have been emitted as a high-signal digest
    assert sub["highSignal"] and all(
        "journal" not in h["file"] for h in sub["highSignal"]
    )


def _write_rows_deep(path, rows):
    """_write_rows for a path whose folders do not exist yet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return _write_rows(path, rows)


def test_a_run_folder_with_only_a_journal_counts_no_sub_agent(tmp_path):
    sid = "sa000002-0000-0000-0000-000000000000"
    _write_rows(tmp_path / f"{sid}.jsonl", _minimal_session_rows())
    _write_rows_deep(
        tmp_path / sid / "subagents" / "workflows" / "wf_r1" / "journal.jsonl",
        _journal_rows(),
    )
    (tmp_path / "sessions").mkdir()
    sess = ex.process_session(tmp_path / f"{sid}.jsonl", tmp_path / "sessions")[0]
    sub = sess["subAgents"]
    assert (sub["count"], sub["bytes"], sub["msgs"]) == (0, 0, 0)
    assert sub["agents"] == [] and sub["highSignal"] == []
    assert not (tmp_path / "sessions" / "sub").exists()


@pytest.mark.parametrize(
    ("name", "counted"),
    [
        ("agent-x.jsonl", True),
        ("agent-1.jsonl", True),
        ("agent-07.jsonl", True),
        ("agent-a0123456789abcdef.jsonl", True),
        ("journal.jsonl", False),
        ("notes.jsonl", False),
        ("agent.jsonl", False),
        ("agents.jsonl", False),
        ("agent-x.meta.json", False),
        ("agent-x.jsonl.bak", False),
    ],
)
def test_the_file_name_decides_what_a_sub_agent_is(name, counted, tmp_path):
    sid = "sa000003-0000-0000-0000-000000000000"
    _write_rows(tmp_path / f"{sid}.jsonl", _minimal_session_rows())
    _write_rows_deep(
        tmp_path / sid / "subagents" / name,
        [{"type": "user", "message": {"content": [_text("do the task")]}}],
    )
    (tmp_path / "sessions").mkdir()
    sess = ex.process_session(tmp_path / f"{sid}.jsonl", tmp_path / "sessions")[0]
    assert sess["subAgents"]["count"] == (1 if counted else 0)


_SCHEMA_REFERENCE = (
    Path(__file__).resolve().parent.parent / "references" / "extractor-output-schema.md"
)


def test_the_docstring_and_the_schema_reference_describe_the_sub_agent_file_pattern():
    flat = " ".join(_SCHEMA_REFERENCE.read_text(encoding="utf-8").split())
    assert "<id>/subagents/**/*.jsonl" not in flat, (
        "the reference still says every .jsonl"
    )
    assert f"`<id>/subagents/**/{ex.SUBAGENT_GLOB}`" in flat
    assert "journal.jsonl" in flat
    doc = " ".join(inspect.getdoc(ex.walk_subagents).split())
    assert ex.SUBAGENT_GLOB in doc and "journal.jsonl" in doc


# --- .NET commands in the build-and-test loop detector ----------------------------------------
# buildTestLoops is the part of repeatedCommands that TEST_BUILD_RE matches. The pattern knew the
# Python and JavaScript tools and no .NET command, so a .NET session showed none of its
# build-and-test loops. Each case below runs one command twice through process_session, the real
# detector. The positives are the listed commands in the shapes they are typed: with arguments,
# chained after another command, with ".exe", in any case, with extra blanks, by path. The near
# misses repeat just the same, so that each one is SEEN as a repeat and is left out by the
# pattern alone: a near miss that never repeated would pass without testing anything.
_DOTNET_RUNS = {
    "dotnet-build": "dotnet build",
    "dotnet-test": "dotnet test --no-build --filter Category=Unit",
    "dotnet-restore": "dotnet restore",
    "dotnet-publish": "dotnet publish -c Release -o out",
    "dotnet-msbuild": "dotnet msbuild App.sln -t:Rebuild",
    "msbuild": "msbuild App.sln /m",
    "nuget-restore": "nuget restore App.sln",
    "dotnet-format": "dotnet format --verify-no-changes",
    "chained": "cd src && dotnet build --no-restore && dotnet test",
    "exe-and-case": "MSBuild.exe App.sln /p:Configuration=Release",
    "exe-with-a-verb": "nuget.exe restore App.sln",
    "extra-blanks": "dotnet  build",
    "tab-between-the-words": "dotnet\tbuild",
    "by-path": "/usr/share/dotnet/dotnet test",
}
_DOTNET_NEAR_MISSES = {
    "dotnet-info": "dotnet --info",
    "dotnet-new": "dotnet new console",
    "dotnet-run": "dotnet run",
    "build-server": "dotnet build-server shutdown",
    "another-nuget-verb": "nuget sources list",
    "file-named-like-msbuild": "cat msbuild.log",
    "folder-named-like-msbuild": "ls tools/msbuild/bin",
    "file-named-like-nuget": "cat nuget.config",
    "file-named-like-a-verb": "cat dotnet-build.log",
    "script-named-after-the-program": "./scripts/run-msbuild App.sln",
    "name-ending-in-the-program": "my_msbuild App.sln",
    "extension-named-like-the-program": "cat foo.msbuild",
    "name-starting-with-the-program": "msbuildx App.sln",
    "windows-folder-named-like-msbuild": r"dir tools\msbuild\bin",
    "verb-on-the-next-line": "export PATH=$PATH:/opt/dotnet\ntest -d src",
    "not-dotnet-at-all": "git status",
}
# what the pattern matched before the .NET commands were added: it must keep every one
_COMMANDS_THE_PATTERN_ALWAYS_KNEW = {
    "pytest": "pytest -q",
    "uv-run": "uv run pytest",
    "npm-test": "npm test",
    "ruff": "ruff check .",
    "mypy": "mypy src",
    "basedpyright": "basedpyright",
    "alembic": "alembic upgrade head",
    "compose-test": "docker compose run --rm api test",
}


def _behavior_of_a_command_run_twice(tmp_path, command, tool="Bash"):
    """The behavior block of a session in which `tool` runs `command` two times."""
    rows = [{"type": "user", "message": {"content": "get it building"}}]
    for n in (1, 2):
        rows += [_tool_call(f"x{n}", tool, command), _tool_result(f"x{n}", "ok")]
    return _process(tmp_path, rows, name="loops")["behavior"]


@pytest.mark.parametrize("name", sorted(_DOTNET_RUNS))
def test_a_repeated_dotnet_build_or_test_command_is_a_loop(name, tmp_path):
    command = _DOTNET_RUNS[name]
    behavior = _behavior_of_a_command_run_twice(tmp_path, command)
    assert behavior["buildTestLoops"] == [{"cmd": command, "count": 2}]


@pytest.mark.parametrize("name", sorted(_DOTNET_NEAR_MISSES))
def test_a_repeated_command_that_only_looks_like_a_dotnet_run_is_not_a_loop(
    name, tmp_path
):
    command = _DOTNET_NEAR_MISSES[name]
    behavior = _behavior_of_a_command_run_twice(tmp_path, command)
    assert behavior["repeatedCommands"] == [{"cmd": command, "count": 2}], "not seen"
    assert behavior["buildTestLoops"] == []


@pytest.mark.parametrize("name", sorted(_COMMANDS_THE_PATTERN_ALWAYS_KNEW))
def test_a_command_the_pattern_matched_before_is_still_a_loop(name, tmp_path):
    command = _COMMANDS_THE_PATTERN_ALWAYS_KNEW[name]
    behavior = _behavior_of_a_command_run_twice(tmp_path, command)
    assert behavior["buildTestLoops"] == [{"cmd": command, "count": 2}]


def test_the_powershell_tool_runs_dotnet_loops_too(tmp_path):
    behavior = _behavior_of_a_command_run_twice(tmp_path, "dotnet test", "PowerShell")
    assert behavior["buildTestLoops"] == [{"cmd": "dotnet test", "count": 2}]


def _dotnet_build_ending_at(length):
    """`cd <filler> && dotnet build`, made `length` characters long."""
    filler = "x" * (length - len("cd  && dotnet build"))
    return f"cd {filler} && dotnet build"


def _characters_of_a_command_the_detector_reads(tmp_path):
    """The stored text of a very long command is as long as what the detector reads of it."""
    folder = tmp_path / "long"
    folder.mkdir()
    command = _dotnet_build_ending_at(500)
    behavior = _behavior_of_a_command_run_twice(folder, command)
    kept = behavior["repeatedCommands"][0]["cmd"]
    assert len(kept) < len(command), "the command was kept whole"
    return len(kept)


@pytest.mark.parametrize(
    ("past_the_limit", "is_a_loop"),
    [(0, True), (1, False)],
    ids=["ends-at-the-limit", "one-past-the-limit"],
)
def test_a_dotnet_command_counts_only_inside_the_characters_the_detector_reads(
    past_the_limit, is_a_loop, tmp_path
):
    limit = _characters_of_a_command_the_detector_reads(tmp_path)
    command = _dotnet_build_ending_at(limit + past_the_limit)
    behavior = _behavior_of_a_command_run_twice(tmp_path, command)
    assert len(behavior["repeatedCommands"]) == 1, "not seen"
    assert bool(behavior["buildTestLoops"]) is is_a_loop


def test_the_listed_dotnet_commands_are_the_ones_the_tests_state():
    """The surface in numbers: eight commands, none twice, each led by one of three programs."""
    commands = ex.DOTNET_BUILD_TEST_COMMANDS
    assert len(commands) == 8 and len(set(commands)) == 8
    programs = {command.split()[0] for command in commands}
    assert programs == {"dotnet", "msbuild", "nuget"}


@pytest.mark.parametrize("tail", ["", " App.sln"], ids=["bare", "with-an-argument"])
def test_the_pattern_matches_every_listed_dotnet_command(tail):
    assert ex.TEST_BUILD_RE.search("dotnet test"), "the pattern knows no .NET command"
    commands = ex.DOTNET_BUILD_TEST_COMMANDS
    missed = [c for c in commands if not ex.TEST_BUILD_RE.search(c + tail)]
    assert missed == []


def _commands_left_out(text, commands):
    """The commands that `text` does not name as a code span of their own."""
    return [command for command in commands if f"`{command}`" not in text]


def _dotnet_words_beyond_the_list(pattern):
    """What .NET the pattern holds once the listed commands' own patterns are taken out of it."""
    for command in ex.DOTNET_BUILD_TEST_COMMANDS:
        pattern = pattern.replace(ex._command_pattern(command), "")
    return [word for word in ("dotnet", "msbuild", "nuget") if word in pattern.lower()]


def _top_level_alternatives(pattern):
    """`pattern` cut at the `|` that stand outside every group, so a group keeps its own."""
    parts, depth, start, escaped = [], 0, 0, False
    for i, char in enumerate(pattern):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "|" and depth == 0:
            parts.append(pattern[start:i])
            start = i + 1
    return [*parts, pattern[start:]]


def _alternatives_beyond_the_list(pattern):
    """The alternatives after the first, the group of the tools the pattern always knew, that are
    not the pattern of a listed command: whatever was written into the pattern by hand."""
    listed = [ex._command_pattern(command) for command in ex.DOTNET_BUILD_TEST_COMMANDS]
    return [part for part in _top_level_alternatives(pattern)[1:] if part not in listed]


def test_the_checks_on_the_list_flag_a_planted_miss_and_pass_a_near_miss():
    """Each check is fired at a known positive before its clean result means anything. A text
    that names one command of two, the old sentence, and a longer command are all flagged; a
    pattern with a command written into it by hand is flagged, for each program the list holds
    and for a runner that is none of them, at the end of the pattern and in the middle of it;
    the pattern as it is is not."""
    pair = ("dotnet build", "dotnet test")
    assert _commands_left_out("`dotnet build` and `dotnet test`", pair) == []
    assert _commands_left_out("`dotnet build` only", pair) == ["dotnet test"]
    assert _commands_left_out("`dotnet build-server`, `dotnet test`", pair) == [pair[0]]
    old_sentence = "subset of repeatedCommands matching test/build"
    assert _commands_left_out(old_sentence, pair) == list(pair)
    pattern = ex.TEST_BUILD_RE.pattern
    planted = pattern + "|dotnet ef|msbuild /t:x|nuget pack"
    assert _dotnet_words_beyond_the_list(planted) == ["dotnet", "msbuild", "nuget"]
    assert _dotnet_words_beyond_the_list(pattern) == []
    runner = r"vstest\.console"
    first = ex._command_pattern(ex.DOTNET_BUILD_TEST_COMMANDS[0])
    at_the_end = pattern + "|" + runner
    in_the_middle = pattern.replace("|" + first, "|" + runner + "|" + first, 1)
    assert in_the_middle != pattern, "the plant did not land"
    assert _alternatives_beyond_the_list(at_the_end) == [runner]
    assert _alternatives_beyond_the_list(in_the_middle) == [runner]
    assert _alternatives_beyond_the_list(pattern) == []


def test_the_pattern_holds_no_dotnet_command_the_list_leaves_out():
    """The reference is held to the list, so a command written into the pattern by hand would
    reach neither the reference nor this test: it has to come through the list. The pattern is
    the group of the old tools and one alternative for each listed command, and holds no .NET
    word beside those."""
    pattern = ex.TEST_BUILD_RE.pattern
    assert "dotnet" in pattern.lower(), "the pattern names no .NET command"
    assert _dotnet_words_beyond_the_list(pattern) == []
    commands = ex.DOTNET_BUILD_TEST_COMMANDS
    parts = _top_level_alternatives(pattern)
    assert len(parts) == 1 + len(commands), "the pattern was cut wrong"
    assert _alternatives_beyond_the_list(pattern) == []


def test_the_docstring_of_the_command_pattern_says_a_backslash_ends_a_program():
    doc = " ".join(inspect.getdoc(ex._command_pattern).split())
    assert "a slash or a backslash after it" in doc


def test_the_schema_reference_names_each_dotnet_command_the_loop_detector_matches(
    tmp_path,
):
    """Where the reference says what buildTestLoops holds, it names the pattern, every .NET
    command in the list the pattern is built from, how much of a command is read, and that a
    backslash ends a program as a slash does. The list and the number are read from the
    extractor."""
    flat = " ".join(_SCHEMA_REFERENCE.read_text(encoding="utf-8").split())
    first, last = "### `sessions[]`", "## Redaction & privacy"
    assert flat.count(first) == 1, "the sessions[] heading is gone"
    assert flat.count(last) == 1, "the heading after sessions[] is gone"
    section = flat.split(first)[1].split(last)[0]
    assert "`TEST_BUILD_RE`" in section, "the reference does not name the pattern"
    assert ".NET commands" in section, "the reference does not say .NET commands"
    assert _commands_left_out(section, ex.DOTNET_BUILD_TEST_COMMANDS) == []
    limit = _characters_of_a_command_the_detector_reads(tmp_path)
    window = f"first {limit} characters of the command"
    assert window in section, "the reference does not give the reading limit"
    assert "slash or backslash" in section, "the reference leaves out the backslash"


# --- the per-parent pick limit, as the skill and the schema reference say it -------------------
_SKILL_DOC = Path(__file__).resolve().parent.parent / "SKILL.md"


def _between_headings(flat, first, last):
    """The text between two headings of a whitespace-folded document. A heading that is not
    found, or the first one found twice, fails loudly, so a renamed heading cannot turn a
    check into a pass."""
    assert flat.count(first) == 1, f"{first!r} is not found exactly once"
    rest = flat.split(first)[1]
    assert last in rest, f"{last!r} does not follow {first!r}"
    return rest.split(last)[0]


def test_the_heading_cut_fails_loudly_when_a_heading_is_missing_or_repeated():
    doc = "# top ## one alpha ## two beta ## one gamma"
    assert _between_headings(doc, "## two", "## one") == " beta "
    for first, last in (
        ("## nope", "## one"),
        ("## one", "## two"),
        ("## two", "## nope"),
    ):
        with pytest.raises(AssertionError):
            _between_headings(doc, first, last)


def test_the_skill_says_the_pick_limit_per_parent_is_built_and_the_downweight_is_not():
    flat = " ".join(_SKILL_DOC.read_text(encoding="utf-8").split())
    heading = f"### Phase 3 {chr(0x2014)} Deep-Dive the Substantial Sessions"
    section = _between_headings(flat, heading, "### Phase 3b")
    assert "Two standing extractor improvements" not in section
    assert "cap sub-agent picks per parent session for diversity" not in section
    limit = ex.SUBAGENT_DEEPDIVE_PER_PARENT_CAP
    built = f"caps sub-agent picks at {limit} per parent session while others remain"
    assert built in section
    assert "(an uncalibrated default)" in section
    assert (
        "One standing extractor improvement is a candidate, not yet built: "
        "downweight sessions the prior report already deep-dived"
    ) in section


def test_the_schema_reference_example_rule_is_the_one_the_extractor_emits():
    flat = " ".join(_SCHEMA_REFERENCE.read_text(encoding="utf-8").split())
    first = "### `deepDiveCandidates` / `subAgentDeepDiveCandidates` (v4)"
    section = _between_headings(flat, first, "### `stats`")
    assert "per parent session while others remain" in section
    rule = ex.select_subagent_deep_dive([])["selectionRule"]
    assert f'"selectionRule": "{rule}"' in section


# --- environment: refused or stopped by the harness or a hook (schema v5) ---------------------
# Three shapes, each named by text the harness or the kit's own hook writes and anchored where that
# text opens an error record. The fixtures follow the shapes real transcripts carry: the harness
# wraps a refused sleep in its own error tag, a usage limit stops a turn with an assistant record
# the harness marks as an API error, and the kit's shell-prefix gate denies with its own text as the
# whole reason. The commands, times and zones in them are made up. The gate's text is read from the
# hook itself, loaded by path, so no copy of it lives in this file.
_SLEEP_ADVICE = (
    ". To wait for a condition, use Monitor with an until-loop (e.g. `until <check>; do sleep 2; "
    "done`). To wait for a command you started, use run_in_background: true."
)
_SLEEP_DENIAL = (
    "<tool_use_error>Blocked: sleep 30 followed by: uv run pytest -q"
    + _SLEEP_ADVICE
    + "</tool_use_error>"
)
_START_SLEEP_DENIAL = (
    "<tool_use_error>Blocked: Start-Sleep 30 followed by: Get-ChildItem"
    + _SLEEP_ADVICE
    + "</tool_use_error>"
)
_LIMIT_SENTENCE = "You've hit your 5-hour limit · resets 2:30pm (UTC)"
_SESSION_LIMIT_SENTENCE = "You've hit your session limit · resets 4am (UTC)"
_GATE_HOOK = Path(__file__).resolve().parents[3] / "hooks" / "gate_shell_prefix.py"
_MOVE = "<MOVE>"  # stands for the gate's MOVE text in a table; filled in by _filled


def _gate_texts():
    """(the gate's MOVE text, its other texts), from the hook loaded by path. Bytecode is not
    written, because the hook sits inside the plugin payload."""
    assert _GATE_HOOK.is_file(), f"the kit gate is not where it was: {_GATE_HOOK}"
    spec = importlib.util.spec_from_file_location(
        "gate_shell_prefix_for_extractor_tests", _GATE_HOOK
    )
    assert spec is not None and spec.loader is not None
    gate = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(gate)
    finally:
        sys.dont_write_bytecode = previous
    texts = dict(gate._TEXTS)
    move = texts.pop(gate.MOVE)
    return move, list(texts.values())


def _filled(text):
    return text.replace(_MOVE, _gate_texts()[0])


def _opens(anchor, text):
    """True when `anchor` is a non-empty opening of `text` that ends where a word ends."""
    if not anchor or not text.startswith(anchor):
        return False
    return len(text) == len(anchor) or not text[len(anchor)].isalnum()


def _limit_stop(text=_LIMIT_SENTENCE, **overrides):
    """The record a usage limit leaves: an assistant record the harness marks as an API error,
    a synthetic model, and the limit sentence as its one text block."""
    record = {
        "type": "assistant",
        "isApiErrorMessage": True,
        "error": "rate_limit",
        "apiErrorStatus": 429,
        "apiError": "usage_limit_reached",
        "message": {
            "role": "assistant",
            "model": "<synthetic>",
            "content": [_text(text)],
        },
    }
    record.update(overrides)
    return record


_A_TASK = {"type": "user", "message": {"content": [_text("do the task")]}}


def test_environment_sits_before_the_reserved_bucket():
    assert ex.ERROR_CATEGORIES[-2:] == ["environment", "other"]


@pytest.mark.parametrize(
    ("origin", "text"),
    [
        ("Bash", "Blocked: sleep 30 followed by <cmd>"),
        ("Bash", _SLEEP_DENIAL),
        ("Bash", "\n" + _SLEEP_DENIAL),
        ("PowerShell", _START_SLEEP_DENIAL),
    ],
    ids=[
        "the-bare-refusal",
        "in-the-harness-wrapper",
        "after-an-empty-first-block",
        "the-powershell-spelling",
    ],
)
def test_the_harness_sleep_refusal_is_an_environment_result(origin, text):
    """The command in the wrapped form runs pytest, so the behavioural rules filed this refusal
    as a test failure: it is the harness's refusal, not a test that failed."""
    assert ex.classify_error(origin, True, text) == "environment"
    assert ex.environment_shape(origin, True, text) == "sleep-denial"


@pytest.mark.parametrize("origin", ["Agent", "Bash", "Read"])
@pytest.mark.parametrize(
    "text",
    [
        _LIMIT_SENTENCE,
        _SESSION_LIMIT_SENTENCE,
        "<tool_use_error>" + _LIMIT_SENTENCE + "</tool_use_error>",
    ],
    ids=["five-hour", "session", "in-the-harness-wrapper"],
)
def test_an_error_result_opening_with_the_usage_limit_sentence_is_an_environment_result(
    origin, text
):
    assert ex.classify_error(origin, True, text) == "environment"
    assert ex.environment_shape(origin, True, text) == "usage-limit"


@pytest.mark.parametrize("origin", ["Bash", "PowerShell"])
def test_an_error_shell_result_opening_with_the_gates_move_text_is_a_cd_denial(origin):
    move = _gate_texts()[0]
    assert ex.classify_error(origin, True, move) == "environment"
    assert ex.environment_shape(origin, True, move) == "cd-denial"


def test_the_cd_denial_anchor_opens_the_gates_move_text_and_no_other():
    move, others = _gate_texts()
    assert _opens(ex.CD_DENIAL_ANCHOR, move)
    # the comparison can fail: a reworded opening, a cut inside a word, the gate's other texts
    assert not _opens(ex.CD_DENIAL_ANCHOR, move.replace("move", "change", 1))
    assert not _opens(ex.CD_DENIAL_ANCHOR[:-1], move)
    assert others and not any(_opens(ex.CD_DENIAL_ANCHOR, text) for text in others)


# (origin, is_error, text, the class it keeps): the three texts quoted inside other records, the
# same texts in results that are not errors, and near misses of each anchor.
_NOT_ENVIRONMENT = {
    # the quoted command runs pytest, so the behavioural rules decide it as they always did
    "sleep-refusal-quoted-in-a-failed-command": (
        "Bash",
        True,
        "Exit code 1\nlog: " + _SLEEP_DENIAL,
        "test-failure",
    ),
    "limit-sentence-quoted-in-a-failed-command": (
        "Bash",
        True,
        "Exit code 1\nlast line: " + _LIMIT_SENTENCE,
        "runtime-exit",
    ),
    "move-text-quoted-in-a-failed-command": (
        "Bash",
        True,
        "Exit code 1\nthe hook said: " + _MOVE,
        "runtime-exit",
    ),
    "limit-sentence-in-a-workflow-failure-list": (
        "Workflow",
        True,
        "<failures>[step-1] failed: " + _LIMIT_SENTENCE + "</failures>",
        "tool-error",
    ),
    "a-failed-command-that-mentions-sleep": (
        "Bash",
        True,
        "Exit code 1\nsleep: invalid time interval 'abc'",
        "runtime-exit",
    ),
    "the-same-words-behind-a-hook-error-prefix": (
        "Bash",
        True,
        "PreToolUse:Bash hook error: Blocked: sleep 30 followed by: ls",
        "runtime-exit",
    ),
    "sleep-refusal-text-from-a-tool-that-is-no-shell": (
        "Read",
        True,
        _SLEEP_DENIAL,
        "tool-error",
    ),
    "move-text-from-a-tool-that-is-no-shell": ("Edit", True, _MOVE, "tool-error"),
    "sleep-refusal-text-in-a-result-that-is-no-error": (
        "Bash",
        False,
        _SLEEP_DENIAL,
        None,
    ),
    "limit-sentence-in-a-result-that-is-no-error": (
        "Agent",
        False,
        _LIMIT_SENTENCE,
        None,
    ),
    "move-text-in-a-result-that-is-no-error": ("Bash", False, _MOVE, None),
}


@pytest.mark.parametrize("name", sorted(_NOT_ENVIRONMENT))
def test_a_text_that_does_not_open_an_error_record_keeps_its_class(name):
    origin, is_error, text, category = _NOT_ENVIRONMENT[name]
    text = _filled(text)
    assert ex.environment_shape(origin, is_error, text) is None
    assert ex.classify_error(origin, is_error, text) == category


# Failing shell calls all open with "Exit code N", the opening the census normaliser kept, so
# that opening says nothing about who failed: each keeps the class its body earns.
_FAILING_SHELL_CALLS = {
    "broken-quoting": (
        "\n".join(
            [
                "Exit code 2",
                "/usr/bin/bash: -c: line 1: unexpected EOF while looking for matching `\"'",
                "/usr/bin/bash: -c: line 2: syntax error: unexpected end of file",
            ]
        ),
        "runtime-exit",
    ),
    "a-failing-test": (
        "Exit code 1\nFAILED tests/test_x.py::test_y - AssertionError: boom",
        "test-failure",
    ),
    "a-lint-error": (
        "Exit code 1\nruff check found 1 error: x.py:1:8: F401 `os` imported but unused",
        "build-compile",
    ),
    "a-traceback": (
        "\n".join(
            [
                "Exit code 1",
                "Traceback (most recent call last):",
                '  File "x.py", line 3, in <module>',
                "ValueError: boom",
            ]
        ),
        "runtime-exit",
    ),
}


@pytest.mark.parametrize("is_error", [True, False])
@pytest.mark.parametrize("name", sorted(_FAILING_SHELL_CALLS))
def test_a_failing_shell_call_keeps_its_behavioural_class(name, is_error):
    text, category = _FAILING_SHELL_CALLS[name]
    assert ex.environment_shape("Bash", is_error, text) is None
    assert ex.classify_error("Bash", is_error, text) == category


@pytest.mark.parametrize(
    ("record", "counted"),
    [
        (_limit_stop(), True),
        (_limit_stop(_SESSION_LIMIT_SENTENCE), True),
        (_limit_stop("API Error: Connection lost mid-response."), False),
        (_limit_stop(isApiErrorMessage=False), False),
        (
            {"type": "assistant", "message": {"content": [_text(_LIMIT_SENTENCE)]}},
            False,
        ),
        (_limit_stop("The run stopped here. " + _LIMIT_SENTENCE), False),
    ],
    ids=[
        "five-hour-stop",
        "session-stop",
        "an-api-error-of-another-kind",
        "the-sentence-on-an-unmarked-record",
        "the-agent-quoting-the-sentence",
        "the-sentence-mid-text",
    ],
)
def test_only_a_marked_record_that_opens_with_the_sentence_is_a_usage_limit_stop(
    record, counted, tmp_path
):
    sess = _process(tmp_path, _minimal_session_rows(extra=[record]), name="stop")
    assert sess["errorsByCategory"].get("environment", 0) == (1 if counted else 0)
    assert sess["environmentShapes"] == ({"usage-limit": 1} if counted else {})


def test_a_usage_limit_stop_counts_once_in_the_main_walk_and_once_in_the_sub_agent_roll_up(
    tmp_path,
):
    sid = "env00001-0000-0000-0000-000000000000"
    _write_rows(tmp_path / f"{sid}.jsonl", _minimal_session_rows(extra=[_limit_stop()]))
    _write_rows_deep(
        tmp_path / sid / "subagents" / "agent-a1.jsonl",
        [_A_TASK, _limit_stop(_SESSION_LIMIT_SENTENCE)],
    )
    (tmp_path / "sessions").mkdir()
    sess = ex.process_session(tmp_path / f"{sid}.jsonl", tmp_path / "sessions")[0]
    assert sess["errorsByCategory"] == {"environment": 1}
    assert sess["environmentShapes"] == {"usage-limit": 1}
    sub = sess["subAgents"]
    assert sub["errorsByCategory"] == {"environment": 1}
    assert sub["environmentShapes"] == {"usage-limit": 1}
    assert sub["agentsWithErrors"] == 1


def test_the_aggregate_rolls_environment_up_by_shape_for_sessions_and_sub_agents(
    tmp_path, monkeypatch
):
    """Two sleep refusals, a usage-limit stop and a gate denial in the main thread; two sleep
    refusals in a Workflow agent. The refusals ran pytest, so before the class existed they were
    filed as test failures."""
    sdir = tmp_path / "src"
    sid = "env00002-0000-0000-0000-000000000000"
    main_rows = [
        *_tool_error_rows(
            [
                ("Bash", _SLEEP_DENIAL),
                ("Bash", _SLEEP_DENIAL),
                ("PowerShell", _gate_texts()[0]),
            ]
        ),
        _limit_stop(),
    ]
    _write_rows_deep(sdir / f"{sid}.jsonl", _minimal_session_rows(extra=main_rows))
    _write_rows_deep(
        sdir / sid / "subagents" / "workflows" / "wf_r1" / "agent-w1.jsonl",
        [_A_TASK, *_tool_error_rows([("Bash", _SLEEP_DENIAL)] * 2)],
    )
    agg = _run(sdir, tmp_path / "out", monkeypatch)

    assert agg["schemaVersion"] >= 5
    s = agg["sessions"][0]
    assert s["errorsByCategory"] == {"environment": 4}
    assert s["environmentShapes"] == {
        "sleep-denial": 2,
        "usage-limit": 1,
        "cd-denial": 1,
    }
    assert s["subAgents"]["errorsByCategory"] == {"environment": 2}
    assert s["subAgents"]["environmentShapes"] == {"sleep-denial": 2}

    tax = agg["errorTaxonomy"]
    assert tax["byCategory"]["environment"]["count"] == 4
    assert tax["byCategory"]["test-failure"]["count"] == 0
    assert tax["environmentShapes"] == {
        "sleep-denial": 2,
        "usage-limit": 1,
        "cd-denial": 1,
    }
    sub_tax = agg["subAgentErrorTaxonomy"]
    assert sub_tax["byCategory"]["environment"]["count"] == 2
    assert sub_tax["environmentShapes"] == {
        "sleep-denial": 2,
        "usage-limit": 0,
        "cd-denial": 0,
    }
    assert list(tax["byCategory"]) == ex.ERROR_CATEGORIES


# --- slash commands: the operator's or the harness's ------------------------------------------
def _command(name, **stamps):
    """A slash-command record: the harness's command wrapper on the user channel."""
    body = "\n".join(
        [
            f"<command-name>{name}</command-name>",
            f"<command-message>{name.lstrip('/')}</command-message>",
            "<command-args></command-args>",
        ]
    )
    return {
        "type": "user",
        "message": {"role": "user", "content": [_text(body)]},
        **stamps,
    }


def test_a_command_the_harness_typed_is_told_apart_from_the_operators(
    tmp_path, monkeypatch
):
    sdir = tmp_path / "src"
    sdir.mkdir()
    rows = _minimal_session_rows(
        extra=[
            _command("/compact", origin={"kind": "human"}),
            _command("workflow-authoring", origin={"kind": "coordinator"}),
            _command("meta-command", isMeta=True),
            _command("/model"),
        ]
    )
    _write_jsonl(sdir / "cmd00001-0000-0000-0000-000000000000.jsonl", rows)
    agg = _run(sdir, tmp_path / "out", monkeypatch)
    by = [c["by"] for c in agg["sessions"][0]["slashCommands"]]
    assert by == ["operator", "harness", "harness", "operator"]
    modes = agg["stats"]["skillInvocationModes"]
    assert modes["workflow-authoring"] == {"user": 0, "model": 0, "harness": 1}
    assert modes["compact"] == {"user": 1, "model": 0, "harness": 0}


# The stamps that decide an operator turn; the same stamps on a typed message say whose it is.
_STAMP_CASES = (
    {},
    {"turnOrigin": "human"},
    {"isMeta": True},
    {"isCompactSummary": True},
    {"turnOrigin": "sdk"},
    {"turnOrigin": "system"},
    {"turnOrigin": "peer"},
    {"turnOrigin": "task_notification"},
    {"turnOrigin": "scheduled"},
    {"origin": {"kind": "coordinator"}},
    {"origin": {}},
    {"origin": "human"},
    {"origin": {"kind": "human"}},
)


def test_a_command_is_the_operators_exactly_when_a_typed_turn_with_its_stamps_is(
    tmp_path,
):
    verdicts = []
    for i, stamps in enumerate(_STAMP_CASES):
        typed = {"type": "user", "message": {"content": "please look at the build"}}
        admitted = bool(ex.operator_turn_text({**typed, **stamps}, {}))
        rows = _minimal_session_rows(extra=[_command("/compact", **stamps)])
        sess = _process(tmp_path, rows, name=f"stamps{i}")
        by = [c["by"] for c in sess["slashCommands"]]
        assert by == ["operator" if admitted else "harness"], (stamps, by)
        verdicts.append(admitted)
    assert True in verdicts and False in verdicts, (
        "one verdict alone shows no agreement"
    )
