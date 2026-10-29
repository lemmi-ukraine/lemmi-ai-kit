"""The drain landing audit's exit codes and its sound mode, run the way the harness runs it.

`plugins/core/skills/learning-consolidator/scripts/drain_audit.py` answers the question
the removal check of Phase 5 cannot: did every entry that left the learnings buffer land in
a promotion target. Four defects were fixed together, and the tests below that name them
are red without their fix:

* `main` read `sys.argv` by hand, so `-h` became the snapshot path and exited 2.
* It ended in `return 0` even after listing `[LOSS?]` rows, so a caller that gates on the
  exit code read a drain that had lost entries as clean. Now 0 is clean, 1 is rows to
  adjudicate, and 2 is a usage error or a run that could not measure.
* With no base ref it silently scanned the CURRENT contents of the targets, where a token
  that predates the drain counts as a landing. The ref is now mandatory and that scan is
  the explicit `--current-contents` flag.
* Sound mode handed the target globs to `git diff` as plain pathspecs. A plain
  `docs/**/*.md` matches only files inside a subfolder of `docs/` (`**/` is not special and
  `*` crosses `/`), so a promotion written to `docs/x.md` read as lost, while `tasks/*.md`
  matched `tasks/a/b.md`, which the fallback's `Path.glob` never does.

The script finds its project from its OWN file (`repo_root` walks up looking for `.ai/`
beside `.git`), so every test copies it into a throwaway repository: run in place it would
audit the kit checkout, run as a copy it audits the temporary one. It runs as a subprocess
from another working directory, so a crash, a stray line or a wrong exit code is seen as the
caller sees it. Nothing here imports the script from its place in the plugin tree: an import
would write bytecode into the payload, and `publish-check` refuses a payload that holds any.

Tests that were green before the fix are controls, and say so: they stop a fix that works by
making every run exit 1, or by breaking a path that already worked.
"""

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = (
    _REPO_ROOT
    / "plugins"
    / "core"
    / "skills"
    / "learning-consolidator"
    / "scripts"
    / "drain_audit.py"
)

# The one token the throwaway repository holds BEFORE any promotion. An entry whose only
# probe token is this one was not promoted by the drain, whatever the target files say.
_PREEXISTING_TOKEN = "preexisting_token"

_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class _Repo:
    root: Path
    script: Path
    base: str  # the commit before any promotion


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert done.returncode == 0, f"git {' '.join(args)} failed: {done.stderr}"
    return done.stdout.strip()


def _make_repo(parent: Path) -> _Repo:
    """A repository with one commit, `.ai/` beside `.git`, and a COPY of the script in it."""
    root = parent / "project"
    (root / ".ai").mkdir(parents=True)
    (root / "scripts").mkdir()
    script = root / "scripts" / "drain_audit.py"
    shutil.copyfile(_SCRIPT, script)
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "core.autocrlf", "false")
    (root / "AGENTS.md").write_text(
        f"# Rules\n\nAn old rule that mentions `{_PREEXISTING_TOKEN}`.\n",
        encoding="utf-8",
    )
    _git(root, "add", "AGENTS.md")
    _git(root, "commit", "-q", "-m", "base")
    return _Repo(root=root, script=script, base=_git(root, "rev-parse", "HEAD"))


@pytest.fixture
def repo(tmp_path: Path) -> _Repo:
    return _make_repo(tmp_path)


def _run(repo: _Repo, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the copied script from a DIFFERENT working directory, as a subprocess."""
    return subprocess.run(
        [sys.executable, "-B", str(repo.script), *args],
        cwd=repo.root.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )


def _title(name: str) -> str:
    """The title the script derives from a heading: everything after `### `."""
    return f"[{name}] Entry {name}"


def _entry(name: str, body: str) -> str:
    """One snapshot entry, headed the way the script's splitter reads (`### [`)."""
    return f"### {_title(name)}\n- Finding: {body}\n- Impact: none.\n"


def _snapshot(repo: _Repo, *entries: str) -> Path:
    path = repo.root / ".ai" / "snapshot.md"
    path.write_text("# Buffer\n\n" + "\n".join(entries), encoding="utf-8")
    return path


def _stage(repo: _Repo, relative: str, text: str) -> None:
    """Write `text` to a path (appending when it exists) and stage it, as a session would."""
    target = repo.root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(existing + text, encoding="utf-8")
    _git(repo.root, "add", relative)


def _counts(output: str) -> dict[str, int]:
    """The four numbers the script prints, parsed rather than substring-matched."""
    counts: dict[str, int] = {}
    for label in (
        "entries scanned",
        "landed (>=1 tok)",
        "no probe tokens",
        "CANDIDATE LOSS",
    ):
        match = re.search(rf"^{re.escape(label)}\s*:\s*(\d+)\s*$", output, re.MULTILINE)
        assert match is not None, f"the report has no {label!r} line:\n{output}"
        counts[label] = int(match.group(1))
    return counts


def _lost_titles(output: str) -> set[str]:
    return {
        match.group(1).strip()
        for match in re.finditer(r"^\s*\[LOSS\?\]\s+(.*)$", output, re.MULTILINE)
    }


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_help_exits_zero_and_documents_the_flag_and_the_exit_codes(repo: _Repo) -> None:
    """Red before the fix: `-h` was read as the snapshot path, which does not exist, exit 2."""
    done = _run(repo, "-h")
    assert done.returncode == 0, done.stdout + done.stderr
    flat = _flat(done.stdout)
    for needle in (
        "--current-contents",
        "exit 1 means rows to adjudicate",
        "under --current-contents an exit 0 is an upper bound",
    ):
        assert needle in flat, f"--help does not say {needle!r}:\n{done.stdout}"


def test_no_ref_exits_two_and_names_the_flag_that_asks_for_the_other_scan(
    repo: _Repo,
) -> None:
    """Red before the fix: no ref fell back to the unsound scan and exited 0."""
    snapshot = _snapshot(repo, _entry("a", "about `alpha_token`"))
    done = _run(repo, str(snapshot))
    assert done.returncode == 2, done.stdout + done.stderr
    assert "--current-contents" in done.stdout + done.stderr


def test_a_ref_and_the_current_contents_flag_together_exit_two(repo: _Repo) -> None:
    """The two asks contradict (a scan of added lines, a scan of current contents)."""
    snapshot = _snapshot(repo, _entry("a", "about `alpha_token`"))
    done = _run(repo, str(snapshot), repo.base, "--current-contents")
    assert done.returncode == 2, done.stdout + done.stderr
    assert "contradict" in done.stdout + done.stderr


def test_a_token_added_only_to_a_top_level_docs_file_lands(repo: _Repo) -> None:
    """Red before the fix: plain pathspec `docs/**/*.md` skipped `docs/x.md`, a false loss."""
    _stage(repo, "docs/x.md", "The new rule names `zeta_widget_token` once.\n")
    snapshot = _snapshot(
        repo, _entry("zeta", "the lesson is about `zeta_widget_token`")
    )
    done = _run(repo, str(snapshot), repo.base)
    assert done.returncode == 0, done.stdout + done.stderr
    counts = _counts(done.stdout)
    assert counts["landed (>=1 tok)"] == 1, done.stdout
    assert counts["CANDIDATE LOSS"] == 0, done.stdout


# (path, whether the audit sees it), one unique token per path. The expectations are the
# meaning of each target glob to `Path.glob`, which the fallback uses: `**/` matches zero or
# more directories, and `*` never crosses `/`.
_PATHS: tuple[tuple[str, bool], ...] = (
    ("AGENTS.md", True),
    ("CLAUDE.md", True),
    ("docs/x.md", True),
    ("docs/a/y.md", True),
    ("docs/a/b/z.md", True),
    (".claude/skills/s/SKILL.md", True),
    (".cursor/rules/r.md", True),
    (".cursor/rules/r.mdc", True),
    (".kiro/steering/k.md", True),
    (".kiro/steering/sub/k.md", False),
    ("tasks/t.md", True),
    ("tasks/sub/u.md", False),
    ("src/top.py", True),
    ("src/pkg/m.py", True),
    ("src/pkg/README.md", True),
    ("notes/n.md", False),
    ("README.md", False),
)


def _landed_paths(
    repo: _Repo, *, before: tuple[str, ...], after: tuple[str, ...]
) -> set[str]:
    """Which of `_PATHS` the audit reports as landed, read off the entries it lists as lost."""
    for index, (path, _) in enumerate(_PATHS):
        _stage(repo, path, f"A promotion that names `tok_{index}_here` for {path}.\n")
    entries = [
        _entry(f"p{index}", f"the lesson is about `tok_{index}_here` ({path})")
        for index, (path, _) in enumerate(_PATHS)
    ]
    snapshot = _snapshot(repo, *entries)
    done = _run(repo, *before, str(snapshot), *after)
    assert done.returncode in (0, 1), done.stdout + done.stderr
    assert _counts(done.stdout)["entries scanned"] == len(_PATHS), done.stdout
    lost = _lost_titles(done.stdout)
    return {
        path
        for index, (path, _) in enumerate(_PATHS)
        if _title(f"p{index}") not in lost
    }


def test_sound_mode_and_the_current_contents_scan_agree_on_what_a_target_is(
    tmp_path: Path,
) -> None:
    """Two instruments, one table: a pathspec must mean in `git diff` what a glob means in
    `Path.glob`. Red before the fix on `docs/x.md`, `src/top.py` and `tasks/sub/u.md`."""
    expected = {path for path, seen in _PATHS if seen}

    sound_repo = _make_repo(tmp_path / "sound")
    sound = _landed_paths(sound_repo, before=(), after=(sound_repo.base,))
    assert sound == expected, (
        f"sound mode saw {sorted(sound)}; the table says {sorted(expected)}"
    )

    fallback_repo = _make_repo(tmp_path / "fallback")
    fallback = _landed_paths(fallback_repo, before=("--current-contents",), after=())
    assert fallback == expected, (
        f"the current-contents scan saw {sorted(fallback)}; the table says {sorted(expected)}"
    )


def test_a_loss_row_exits_one_and_says_what_one_means(repo: _Repo) -> None:
    """Red before the fix: the script returned 0 after listing a `[LOSS?]` row."""
    snapshot = _snapshot(repo, _entry("lost", "the lesson is about `nowhere_token`"))
    done = _run(repo, str(snapshot), repo.base)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "[LOSS?]" in done.stdout, done.stdout
    assert "exit 1 means rows to adjudicate" in _flat(done.stdout), done.stdout


def test_a_row_with_no_probe_tokens_exits_one(repo: _Repo) -> None:
    """Red before the fix. A row the script cannot speak to is not a clean row."""
    snapshot = _snapshot(repo, _entry("bare", "a lesson that names no identifier"))
    done = _run(repo, str(snapshot), repo.base)
    assert done.returncode == 1, done.stdout + done.stderr
    assert _counts(done.stdout)["no probe tokens"] == 1, done.stdout


def test_a_mixed_snapshot_counts_each_class_once_and_exits_one(repo: _Repo) -> None:
    """Red before the fix (it exited 0). One landed, one lost and one no-probe entry."""
    _stage(repo, "docs/sub/y.md", "The rule names `landed_token`.\n")
    snapshot = _snapshot(
        repo,
        _entry("hit", "about `landed_token`"),
        _entry("miss", "about `absent_token`"),
        _entry("bare", "names nothing"),
    )
    done = _run(repo, str(snapshot), repo.base)
    assert done.returncode == 1, done.stdout + done.stderr
    assert _counts(done.stdout) == {
        "entries scanned": 3,
        "landed (>=1 tok)": 1,
        "no probe tokens": 1,
        "CANDIDATE LOSS": 1,
    }


def test_a_token_that_predates_the_drain_lands_only_in_the_unsound_scan(
    repo: _Repo,
) -> None:
    """The reason the ref is mandatory, as a known-positive. `AGENTS.md` held the token
    before any promotion: sound mode reads the entry as lost, the current-contents scan
    reads it as landed and says out loud that its answer is an upper bound."""
    snapshot = _snapshot(
        repo, _entry("old", f"the lesson is about `{_PREEXISTING_TOKEN}`")
    )
    sound = _run(repo, str(snapshot), repo.base)
    assert sound.returncode == 1, sound.stdout + sound.stderr
    assert _counts(sound.stdout)["CANDIDATE LOSS"] == 1, sound.stdout

    unsound = _run(repo, "--current-contents", str(snapshot))
    assert unsound.returncode == 0, unsound.stdout + unsound.stderr
    assert _counts(unsound.stdout)["landed (>=1 tok)"] == 1, unsound.stdout
    assert "UPPER BOUND" in unsound.stdout, unsound.stdout


def test_both_ref_cases_of_the_reference_work_and_head_after_a_commit_reads_as_a_loss(
    repo: _Repo,
) -> None:
    """Control (the loss half is red before the fix, the landing half is green).

    Uncommitted promotions: HEAD is the pre-promotion state. Committed promotions: the
    commit before the promotion commit, never HEAD, which would leave nothing added.
    """
    _stage(repo, "docs/sub/y.md", "The rule names `committed_token`.\n")
    snapshot = _snapshot(repo, _entry("c", "about `committed_token`"))

    uncommitted = _run(repo, str(snapshot), "HEAD")
    assert uncommitted.returncode == 0, uncommitted.stdout + uncommitted.stderr

    _git(repo.root, "commit", "-q", "-m", "promote")
    committed = _run(repo, str(snapshot), "HEAD~1")
    assert committed.returncode == 0, committed.stdout + committed.stderr

    wrong = _run(repo, str(snapshot), "HEAD")
    assert wrong.returncode == 1, wrong.stdout + wrong.stderr
    assert _counts(wrong.stdout)["CANDIDATE LOSS"] == 1, wrong.stdout


def test_errors_exit_two_never_one(repo: _Repo) -> None:
    """Control for the contract's other half: a run that could not measure is not 'rows'."""
    missing = _run(repo, str(repo.root / ".ai" / "no-such-snapshot.md"), repo.base)
    assert missing.returncode == 2, missing.stdout + missing.stderr

    snapshot = _snapshot(repo, _entry("a", "about `alpha_token`"))
    bad_ref = _run(repo, str(snapshot), "no-such-ref-anywhere")
    assert bad_ref.returncode == 2, bad_ref.stdout + bad_ref.stderr


def test_a_snapshot_with_no_entries_exits_two(repo: _Repo) -> None:
    """Red before the fix. Cannot-measure is never a pass: a file with no `### [` heading
    holds nothing to audit, and 'entries scanned: 0' with exit 0 would read as clean."""
    snapshot = repo.root / ".ai" / "snapshot.md"
    snapshot.write_text(
        "# Buffer\n\n### 2026-01-01 An entry in a heading form the splitter cannot see\n",
        encoding="utf-8",
    )
    done = _run(repo, str(snapshot), repo.base)
    assert done.returncode == 2, done.stdout + done.stderr


def test_a_snapshot_that_is_not_utf8_exits_two_and_says_so(repo: _Repo) -> None:
    """Red before the fix, and red against a `main` that catches `OSError` alone: the decode
    error then escapes as a traceback with exit 1, the code reserved for rows to adjudicate.
    A copy written as UTF-16 opens with the bytes ff fe, which UTF-8 rejects, so the run
    could not read its subject and must exit 2."""
    snapshot = repo.root / ".ai" / "snapshot.md"
    text = "# Buffer\n\n" + _entry("u", "about `utf16_token`")
    snapshot.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    done = _run(repo, str(snapshot), repo.base)
    assert done.returncode == 2, done.stdout + done.stderr
    assert "could not read the snapshot" in done.stdout, done.stdout
    assert "Traceback" not in done.stderr, done.stderr


def _load(script: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("drain_audit_under_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_parser_can_be_built_and_enforces_the_ref_rule(
    repo: _Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red before the fix: there was no `build_parser`. A later test parses every printed
    command line with it, so the parser itself must refuse a line that names no ref."""
    parser = cast(argparse.ArgumentParser, _load(repo.script).build_parser())

    for argv in (["snap.md", "HEAD"], ["snap.md", "abc1234~1"]):
        parsed = vars(parser.parse_args(argv))
        assert parsed["base_ref"] == argv[1]
        assert parsed["current_contents"] is False

    flagged = vars(parser.parse_args(["--current-contents", "snap.md"]))
    assert flagged["current_contents"] is True
    assert flagged["base_ref"] is None

    with pytest.raises(SystemExit) as no_ref:
        parser.parse_args(["snap.md"])
    assert no_ref.value.code == 2
    assert "--current-contents" in capsys.readouterr().err

    with pytest.raises(SystemExit) as helped:
        parser.parse_args(["-h"])
    assert helped.value.code == 0
