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

A later gap needed an option: the ten default globs are one layout's homes, so a promotion
that lands outside all of them (a `notes/` or `lib/` file) read as a false `[LOSS?]`, and
nothing could add the home. `--surface` adds a glob and never replaces a default, one parse
hands the same globs to both scans, so the two-instruments table runs with it too, and a
value in a shape the two scans are known to read differently is refused with exit 2.

A surface may reach `.ai/`, where the snapshot lives, and the snapshot holds every entry's
tokens: with `--surface '.ai/*.md'` two entries that landed nowhere read as landed, exit 0, in
either scan. Only the fallback left anything out (a file named `learnings.md`). Now one rule,
applied by both scans, says no file that holds the entries is a landing site: the buffer, the
snapshot under audit whatever its name, and every byte copy (`learnings-pre-drain-*.md`).

A drain also leaves records. The changelog's CONSOLIDATION entry and the hypotheses ledger quote
the entries a drain removed, so a surface that reached `.ai/` landed an entry in the record of
its own removal. Both ledgers are now left out by name, as the buffer is. The report prints the
globs it scanned beside the counts, so a home outside them shows before a `[LOSS?]` row is read as
lost. And the docstring and `--help` describe the pre-drain snapshot the way the drain procedure
now does: the buffer as committed at the restore point, read through a scratch file, with the
operator's byte copy kept until the audit is clean. The files named `learnings-pre-drain-*.md`
are those byte copies, and the script's own texts call them that and not snapshots.

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
import ast
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
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


# The `--surface` globs the table also runs with, both outside the ten defaults: one that
# leans on `**/` and one on `*`, given as two options to show that the option repeats.
_SURFACES: tuple[str, ...] = ("notes/**/*.md", "lib/*.py")

# (path, seen by the ten defaults, seen with `_SURFACES` added), one unique token per path.
# The expectations are the meaning of each glob to `Path.glob`, which the fallback uses:
# `**/` matches zero or more directories, and `*` never crosses `/`. A surface adds a glob
# and never replaces one, so every path the defaults see stays seen with the surfaces.
_PATHS: tuple[tuple[str, bool, bool], ...] = (
    ("AGENTS.md", True, True),
    ("CLAUDE.md", True, True),
    ("docs/x.md", True, True),
    ("docs/a/y.md", True, True),
    ("docs/a/b/z.md", True, True),
    (".claude/skills/s/SKILL.md", True, True),
    (".cursor/rules/r.md", True, True),
    (".cursor/rules/r.mdc", True, True),
    (".kiro/steering/k.md", True, True),
    (".kiro/steering/sub/k.md", False, False),
    ("tasks/t.md", True, True),
    ("tasks/sub/u.md", False, False),
    ("src/top.py", True, True),
    ("src/pkg/m.py", True, True),
    ("src/pkg/README.md", True, True),
    ("notes/n.md", False, True),
    ("notes/a/m.md", False, True),
    ("notes/n.txt", False, False),
    ("lib/l.py", False, True),
    ("lib/sub/k.py", False, False),
    ("README.md", False, False),
)


def _audit_table(
    repo: _Repo, *, before: tuple[str, ...], after: tuple[str, ...]
) -> tuple[set[str], str]:
    """Which of `_PATHS` the audit reports as landed, read off the entries it lists as lost,
    and the report it printed."""
    for index, (path, *_) in enumerate(_PATHS):
        _stage(repo, path, f"A promotion that names `tok_{index}_here` for {path}.\n")
    entries = [
        _entry(f"p{index}", f"the lesson is about `tok_{index}_here` ({path})")
        for index, (path, *_) in enumerate(_PATHS)
    ]
    snapshot = _snapshot(repo, *entries)
    done = _run(repo, *before, str(snapshot), *after)
    assert done.returncode in (0, 1), done.stdout + done.stderr
    assert _counts(done.stdout)["entries scanned"] == len(_PATHS), done.stdout
    lost = _lost_titles(done.stdout)
    landed = {
        path
        for index, (path, *_) in enumerate(_PATHS)
        if _title(f"p{index}") not in lost
    }
    return landed, done.stdout


def _landed_paths(
    repo: _Repo, *, before: tuple[str, ...], after: tuple[str, ...]
) -> set[str]:
    """Which of `_PATHS` the audit reports as landed."""
    return _audit_table(repo, before=before, after=after)[0]


@pytest.mark.parametrize(
    "surfaces", [(), _SURFACES], ids=["the-ten-defaults", "with-two-surfaces"]
)
def test_sound_mode_and_the_current_contents_scan_agree_on_what_a_target_is(
    tmp_path: Path, surfaces: tuple[str, ...]
) -> None:
    """Two instruments, one table: a pathspec must mean in `git diff` what a glob means in
    `Path.glob`. Red before the fix on `docs/x.md`, `src/top.py` and `tasks/sub/u.md`.

    With `--surface` the same must hold for the globs a run adds, which reach both scans
    through one parse. That case was red before the option existed (exit 2), and it is red
    if git reads a surface as a plain pathspec (`notes/n.md` lost, `lib/sub/k.py` seen), if
    one scan never receives the surfaces, or if a surface replaces the defaults."""
    expected = {
        path
        for path, by_default, with_surfaces in _PATHS
        if (with_surfaces if surfaces else by_default)
    }
    options = tuple(word for glob in surfaces for word in ("--surface", glob))

    sound_repo = _make_repo(tmp_path / "sound")
    sound = _landed_paths(sound_repo, before=options, after=(sound_repo.base,))
    assert sound == expected, (
        f"sound mode saw {sorted(sound)}; the table says {sorted(expected)}"
    )

    fallback_repo = _make_repo(tmp_path / "fallback")
    fallback = _landed_paths(
        fallback_repo, before=("--current-contents", *options), after=()
    )
    assert fallback == expected, (
        f"the current-contents scan saw {sorted(fallback)}; the table says {sorted(expected)}"
    )


# The two scans: the arguments before and after the snapshot that select each one.
_MODES = ("sound", "current-contents")


def _scan(repo: _Repo, mode: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if mode == "current-contents":
        return ("--current-contents",), ()
    return (), (repo.base,)


def _promoted_outside_the_defaults(repo: _Repo) -> Path:
    """A promotion written only to `notes/n.md`, outside all ten default globs (the table
    above marks it not seen), and the snapshot entry it promotes."""
    _stage(repo, "notes/n.md", "The new rule names `eta_widget_token` once.\n")
    return _snapshot(repo, _entry("eta", "the lesson is about `eta_widget_token`"))


@pytest.mark.parametrize("mode", _MODES)
def test_a_token_added_only_outside_the_ten_default_globs_reads_as_a_loss(
    repo: _Repo, mode: str
) -> None:
    """The known positive, green before the option and after it: with no `--surface` the
    home is invisible, so its promotion reads as lost and the run exits 1."""
    snapshot = _promoted_outside_the_defaults(repo)
    before, after = _scan(repo, mode)
    done = _run(repo, *before, str(snapshot), *after)
    assert done.returncode == 1, done.stdout + done.stderr
    assert _lost_titles(done.stdout) == {_title("eta")}, done.stdout


@pytest.mark.parametrize("mode", _MODES)
def test_a_surface_naming_that_glob_lands_the_promotion_and_exits_zero(
    repo: _Repo, mode: str
) -> None:
    """Red before the option existed (exit 2, an unrecognized argument): the same fixture
    with `--surface notes/*.md` lands in either scan."""
    snapshot = _promoted_outside_the_defaults(repo)
    before, after = _scan(repo, mode)
    done = _run(repo, *before, "--surface", "notes/*.md", str(snapshot), *after)
    assert done.returncode == 0, done.stdout + done.stderr
    counts = _counts(done.stdout)
    assert counts["landed (>=1 tok)"] == 1, done.stdout
    assert counts["CANDIDATE LOSS"] == 0, done.stdout


def test_help_names_the_surface_option_and_says_it_only_adds(repo: _Repo) -> None:
    """Red before the option existed: `--help` named no way to add a surface."""
    done = _run(repo, "-h")
    assert done.returncode == 0, done.stdout + done.stderr
    flat = _flat(done.stdout)
    for needle in (
        "--surface GLOB",
        "never replaces a default",
        "in the tree's own letter case",
    ):
        assert needle in flat, f"--help does not say {needle!r}:\n{done.stdout}"


# Values git and the current-contents scan would read differently, each with words of the
# reason the parse gives. Each was measured: git reads '' as the whole tree where `Path.glob`
# raises (a traceback, exit 1), an absolute path or a `..` leaves the project, a backslash
# escapes to git and separates on Windows, `:(...)` is pathspec magic `Path.glob` reads as
# a name, and a trailing `/` or `**` takes every file below to git and none to `Path.glob`.
# The backslash and the drive are built from fragments: each is an argument value under
# test, not a path this test reads, and it runs the same on every platform.
_REFUSED: tuple[tuple[str, str, str], ...] = (
    ("empty", "", "is empty"),
    ("backslash", "notes" + chr(0x5C) + "*.md", "backslash"),
    ("absolute", "/notes/*.md", "not a glob relative to the project root"),
    ("drive", "C" + ":/notes/*.md", "not a glob relative to the project root"),
    ("pathspec-magic", ":(glob)notes/*.md", "not a glob relative to the project root"),
    ("parent", "../notes/*.md", "climbs out of the project"),
    ("trailing-slash", "notes/", "names a directory"),
    ("trailing-double-star", "notes/**", "names a directory"),
)


@pytest.mark.parametrize(
    ("value", "reason"),
    [(value, reason) for _, value, reason in _REFUSED],
    ids=[name for name, _, _ in _REFUSED],
)
@pytest.mark.parametrize("mode", _MODES)
def test_a_surface_the_two_scans_would_read_differently_exits_two(
    repo: _Repo, mode: str, value: str, reason: str
) -> None:
    """Red before the option existed: argparse refused the unknown option, never the value.
    Exit 2 is a run that could not measure; it must never be exit 1, which means rows."""
    snapshot = _promoted_outside_the_defaults(repo)
    before, after = _scan(repo, mode)
    done = _run(repo, *before, "--surface", value, str(snapshot), *after)
    assert done.returncode == 2, done.stdout + done.stderr
    flat = _flat(done.stderr)
    assert reason in flat and "would not read it alike" in flat, done.stderr
    assert "Traceback" not in done.stderr, done.stderr


@pytest.mark.parametrize("mode", _MODES)
def test_a_surface_naming_a_directory_exits_two_and_one_naming_a_file_lands(
    repo: _Repo, mode: str
) -> None:
    """Red before the option existed. Git reads a wildcard-free directory as every file below
    it and `Path.glob` as no file at all, so `notes` is refused; `notes/n.md` names a file,
    which both read alike, and it lands (the near-miss)."""
    snapshot = _promoted_outside_the_defaults(repo)
    before, after = _scan(repo, mode)
    folder = _run(repo, *before, "--surface", "notes", str(snapshot), *after)
    assert folder.returncode == 2, folder.stdout + folder.stderr
    assert "names a directory" in _flat(folder.stdout), folder.stdout
    file = _run(repo, *before, "--surface", "notes/n.md", str(snapshot), *after)
    assert file.returncode == 0, file.stdout + file.stderr


# Two entries whose tokens no promotion carries: only a file that holds the entries can land
# them. Phase 5 commits the snapshot with the drain, so each file below is STAGED, and its
# lines are lines added since the base: sound mode sees them as well as the fallback.
_NEVER_LANDED: tuple[tuple[str, str], ...] = (
    ("lost1", "lost_one_token"),
    ("lost2", "lost_two_token"),
)


def _stage_the_entries(repo: _Repo, relative: str) -> Path:
    """Write the two entries to `relative` as a snapshot or buffer holds them, and stage it."""
    entries = (
        _entry(name, f"the lesson is about `{token}`") for name, token in _NEVER_LANDED
    )
    _stage(repo, relative, "# Buffer\n\n" + "\n".join(entries))
    return repo.root / relative


def _a_loss_row_each(done: subprocess.CompletedProcess[str]) -> None:
    assert done.returncode == 1, done.stdout + done.stderr
    assert _lost_titles(done.stdout) == {_title(name) for name, _ in _NEVER_LANDED}, (
        done.stdout
    )


@pytest.mark.parametrize(
    "snapshot_path",
    [".ai/learnings-pre-drain-2026-01-02.md", ".ai/snapshot.md"],
    ids=["phase-5-name", "any-name"],
)
@pytest.mark.parametrize("mode", _MODES)
def test_a_surface_over_the_snapshot_s_folder_lands_none_of_its_entries(
    repo: _Repo, mode: str, snapshot_path: str
) -> None:
    """Red before the fix: `--surface '.ai/*.md'` reached the snapshot itself, so two entries
    that landed nowhere read as `landed 2`, exit 0, in either scan. The snapshot under audit is
    left out by its path, whatever its name: `any-name` is one no name rule covers."""
    snapshot = _stage_the_entries(repo, snapshot_path)
    before, after = _scan(repo, mode)
    _a_loss_row_each(
        _run(repo, *before, "--surface", ".ai/*.md", str(snapshot), *after)
    )


@pytest.mark.parametrize(
    "holder",
    [".ai/learnings-pre-drain-2025-12-01.md", ".ai/learnings.md"],
    ids=["older-snapshot", "buffer"],
)
@pytest.mark.parametrize("mode", _MODES)
def test_an_older_snapshot_or_the_buffer_lands_none_of_the_entries_it_holds(
    repo: _Repo, mode: str, holder: str
) -> None:
    """The twin: the snapshot under audit sits outside the surface, so only `holder` can land
    the entries. Red before the fix for an older snapshot (it still holds the KEEP entries that
    dwelt through earlier drains) in either scan, and for the buffer in sound mode. The buffer
    under the current-contents scan was green before the fix, the one case the old rule (a
    file named `learnings.md`, skipped by the fallback alone) covered."""
    _stage_the_entries(repo, holder)
    snapshot = _stage_the_entries(repo, "scratch/snapshot.md")
    before, after = _scan(repo, mode)
    _a_loss_row_each(
        _run(repo, *before, "--surface", ".ai/*.md", str(snapshot), *after)
    )


@pytest.mark.parametrize("mode", _MODES)
def test_a_home_under_the_ai_folder_still_lands_beside_the_snapshot(
    repo: _Repo, mode: str
) -> None:
    """Control, green before the fix and after: the rule leaves out files that hold the
    entries, not a folder and not a name prefix. A promotion written to
    `.ai/templates/learnings-format.md` (its name starts like the buffer's) lands under the
    same surface, with the snapshot that holds its entry beside it."""
    _stage(
        repo,
        ".ai/templates/learnings-format.md",
        "The new rule names `theta_widget_token` once.\n",
    )
    _stage(
        repo,
        ".ai/learnings-pre-drain-2026-01-02.md",
        "# Buffer\n\n" + _entry("theta", "the lesson is about `theta_widget_token`"),
    )
    snapshot = repo.root / ".ai" / "learnings-pre-drain-2026-01-02.md"
    before, after = _scan(repo, mode)
    done = _run(
        repo,
        *before,
        "--surface",
        ".ai/*.md",
        "--surface",
        ".ai/templates/*.md",
        str(snapshot),
        *after,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    counts = _counts(done.stdout)
    assert counts["landed (>=1 tok)"] == 1, done.stdout
    assert counts["CANDIDATE LOSS"] == 0, done.stdout


def test_help_names_the_files_that_are_never_a_landing_site(repo: _Repo) -> None:
    """Red before the fix: `--help` named no file the scans leave out, so nothing told a
    reader that a surface over `.ai/` cannot land an entry in its own copy."""
    done = _run(repo, "-h")
    assert done.returncode == 0, done.stdout + done.stderr
    flat = _flat(done.stdout)
    for needle in (
        "never a landing site, in either scan",
        "the buffer (any learnings.md)",
        "the snapshot under audit (whatever its name)",
        "every byte copy (learnings-pre-drain-*.md)",
    ):
        assert needle in flat, f"--help does not say {needle!r}:\n{done.stdout}"


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


# --- ledgers are never a landing site -------------------------------------------------------

# The two ledgers a drain writes. The changelog's CONSOLIDATION entry names what the drain
# removed and a hypothesis may quote the entry it grew from, so each holds the tokens of entries
# that landed nowhere: a token found in one proves nothing, as in the buffer.
_LEDGERS: tuple[str, ...] = (".ai/ai-changelog.md", ".ai/improvement-hypotheses.md")
_LEDGER_IDS = ["changelog", "hypotheses"]

_QUOTED = " and ".join(f"`{token}`" for _, token in _NEVER_LANDED)


def _quote_the_entries(repo: _Repo, relative: str) -> None:
    """Stage `relative` holding a record that quotes the tokens of `_NEVER_LANDED`."""
    _stage(repo, relative, f"## 2026-01-02 CONSOLIDATION\n- Drained: {_QUOTED}\n")


# (id, the ledger, the surface that reaches it): the ledger by its literal path and by its
# folder's glob, and a file of the same name in another folder, which the by-name rule refuses
# as it refuses any `learnings.md`.
_LEDGER_ONLY: tuple[tuple[str, str, str], ...] = (
    ("changelog-by-path", ".ai/ai-changelog.md", ".ai/ai-changelog.md"),
    ("changelog-by-folder", ".ai/ai-changelog.md", ".ai/*.md"),
    (
        "hypotheses-by-path",
        ".ai/improvement-hypotheses.md",
        ".ai/improvement-hypotheses.md",
    ),
    ("hypotheses-by-folder", ".ai/improvement-hypotheses.md", ".ai/*.md"),
    ("same-name-elsewhere", "notes/ai-changelog.md", "notes/*.md"),
)


@pytest.mark.parametrize(
    ("ledger", "surface"),
    [(ledger, surface) for _, ledger, surface in _LEDGER_ONLY],
    ids=[name for name, _, _ in _LEDGER_ONLY],
)
@pytest.mark.parametrize("mode", _MODES)
def test_a_surface_holding_only_a_ledger_lands_none_of_the_entries_it_quotes(
    repo: _Repo, mode: str, ledger: str, surface: str
) -> None:
    """Red before the fix: the ledger quotes both tokens and nothing else holds them, yet each
    entry read as landed (exit 0, either scan). The snapshot under audit sits outside the
    surface, so the ledger is the only file that can land anything."""
    _quote_the_entries(repo, ledger)
    snapshot = _stage_the_entries(repo, "scratch/snapshot.md")
    before, after = _scan(repo, mode)
    _a_loss_row_each(_run(repo, *before, "--surface", surface, str(snapshot), *after))


@pytest.mark.parametrize("ledger", _LEDGERS, ids=_LEDGER_IDS)
@pytest.mark.parametrize("mode", _MODES)
def test_a_real_home_lands_the_entries_a_ledger_also_quotes(
    repo: _Repo, mode: str, ledger: str
) -> None:
    """Control, green before the fix and after: the rule leaves out the ledger, not the surface
    around it. `notes/n.md` is a home that holds both tokens, so both entries land beside the
    ledger that quotes them and the run is clean."""
    _quote_the_entries(repo, ledger)
    _stage(repo, "notes/n.md", f"The new rule names {_QUOTED}.\n")
    snapshot = _stage_the_entries(repo, "scratch/snapshot.md")
    before, after = _scan(repo, mode)
    surfaces = ("--surface", ".ai/*.md", "--surface", "notes/*.md")
    done = _run(repo, *before, *surfaces, str(snapshot), *after)
    assert done.returncode == 0, done.stdout + done.stderr
    counts = _counts(done.stdout)
    assert counts["landed (>=1 tok)"] == len(_NEVER_LANDED), done.stdout
    assert counts["CANDIDATE LOSS"] == 0, done.stdout


@pytest.mark.parametrize("ledger", _LEDGERS, ids=_LEDGER_IDS)
@pytest.mark.parametrize("mode", _MODES)
def test_a_ledger_lands_nothing_the_real_home_left_out(
    repo: _Repo, mode: str, ledger: str
) -> None:
    """Red before the fix: the ledger quotes both tokens and the home holds only the second, so
    the first entry read as landed through the ledger (exit 0). The rule is per entry: the one
    the home carries lands, the one only the ledger quotes is a loss row."""
    (first, _), (_, second_token) = _NEVER_LANDED
    _quote_the_entries(repo, ledger)
    _stage(repo, "notes/n.md", f"The new rule names `{second_token}`.\n")
    snapshot = _stage_the_entries(repo, "scratch/snapshot.md")
    before, after = _scan(repo, mode)
    surfaces = ("--surface", ".ai/*.md", "--surface", "notes/*.md")
    done = _run(repo, *before, *surfaces, str(snapshot), *after)
    assert done.returncode == 1, done.stdout + done.stderr
    assert _lost_titles(done.stdout) == {_title(first)}, done.stdout
    landed = _counts(done.stdout)["landed (>=1 tok)"]
    assert landed == len(_NEVER_LANDED) - 1, done.stdout


# Names near a ledger's that are not a ledger's. The rule is the whole file name, not a prefix,
# a suffix or a family of names, for either ledger, and each of these holds a real promotion
# that must still land.
_NEAR_MISSES: tuple[tuple[str, str], ...] = (
    ("suffix", "docs/ai-changelog-guide.md"),
    ("prefix", "docs/my-ai-changelog.md"),
    ("family", "docs/changelog.md"),
    ("other-ledger-suffix", "docs/improvement-hypotheses-guide.md"),
    ("other-ledger-prefix", "docs/my-improvement-hypotheses.md"),
    ("other-ledger-family", "docs/hypotheses.md"),
    ("under-the-ledger-folder", ".ai/templates/ai-changelog-format.md"),
)


@pytest.mark.parametrize(
    "home",
    [home for _, home in _NEAR_MISSES],
    ids=[name for name, _ in _NEAR_MISSES],
)
@pytest.mark.parametrize("mode", _MODES)
def test_a_file_with_a_name_near_a_ledger_s_still_lands_the_entry(
    repo: _Repo, mode: str, home: str
) -> None:
    """Control, green before the fix and after: a refusal that matched a prefix, a suffix or a
    part of the name would send these real homes to the loss list."""
    _stage(repo, home, "The new rule names `iota_widget_token` once.\n")
    snapshot = _snapshot(
        repo, _entry("iota", "the lesson is about `iota_widget_token`")
    )
    before, after = _scan(repo, mode)
    done = _run(repo, *before, "--surface", ".ai/templates/*.md", str(snapshot), *after)
    assert done.returncode == 0, done.stdout + done.stderr
    counts = _counts(done.stdout)
    assert counts["landed (>=1 tok)"] == 1, done.stdout
    assert counts["CANDIDATE LOSS"] == 0, done.stdout


# --- the report prints the globs it scanned, beside the counts ------------------------------


@dataclass(frozen=True)
class _PrintedSurface:
    total: int
    default: int
    added: int
    globs: list[str]


_SURFACE_LINE = re.compile(
    r"^scan surface\s*:\s*(\d+) globs \((\d+) default \+ (\d+) --surface\): (.+)$",
    re.MULTILINE,
)


def _printed_surface(output: str) -> _PrintedSurface:
    """The `scan surface` line parsed; a report with no such line fails with the report shown."""
    match = _SURFACE_LINE.search(output)
    assert match is not None, f"the report has no 'scan surface' line:\n{output}"
    return _PrintedSurface(
        total=int(match.group(1)),
        default=int(match.group(2)),
        added=int(match.group(3)),
        globs=match.group(4).split(", "),
    )


def _surface_gaps(
    printed: _PrintedSurface, scanned: Sequence[str], added: int
) -> list[str]:
    """How the printed surface differs from `scanned`, the globs the run was handed in order."""
    gaps: list[str] = []
    if printed.globs != list(scanned):
        gaps.append(f"globs: printed {printed.globs}, scanned {list(scanned)}")
    if printed.total != len(scanned):
        gaps.append(f"total: printed {printed.total}, scanned {len(scanned)}")
    if printed.added != added:
        gaps.append(f"--surface count: printed {printed.added}, given {added}")
    if printed.default != len(scanned) - added:
        gaps.append(
            f"default count: printed {printed.default}, scanned {len(scanned) - added}"
        )
    return gaps


def _options(surfaces: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(word for glob in surfaces for word in ("--surface", glob))


def _reached_by(root: Path, globs: Sequence[str]) -> set[str]:
    """The files under `root` that `Path.glob` reaches with any of `globs`, as relative paths."""
    return {
        found.relative_to(root).as_posix()
        for glob in globs
        for found in root.glob(glob)
        if found.is_file()
    }


@pytest.mark.parametrize(
    "surfaces",
    [(), ("notes/*.md",), _SURFACES],
    ids=["no-surface", "one-surface", "two-surfaces"],
)
@pytest.mark.parametrize("mode", _MODES)
def test_the_report_prints_the_globs_it_scanned_beside_the_counts(
    repo: _Repo, mode: str, surfaces: tuple[str, ...]
) -> None:
    """Red before the fix: the report said how many entries matched and not what they were
    matched against. The expected globs come from the script's own `TARGET_GLOBS` and from the
    options this test passed, so no count or glob is retyped here."""
    snapshot = _snapshot(repo, _entry("a", "about `alpha_token`"))
    before, after = _scan(repo, mode)
    done = _run(repo, *before, *_options(surfaces), str(snapshot), *after)
    assert done.returncode == 1, done.stdout + done.stderr
    _counts(done.stdout)
    defaults = cast(tuple[str, ...], _load(repo.script).TARGET_GLOBS)
    printed = _printed_surface(done.stdout)
    assert _surface_gaps(printed, (*defaults, *surfaces), len(surfaces)) == []
    lines = done.stdout.splitlines()
    last_count = next(
        index for index, line in enumerate(lines) if line.startswith("CANDIDATE LOSS")
    )
    assert lines[last_count + 1].startswith("scan surface"), (
        f"the surface line is not beside the counts:\n{done.stdout}"
    )


@pytest.mark.parametrize(
    "surfaces",
    [(), _SURFACES],
    ids=["the-ten-defaults", "with-two-surfaces"],
)
@pytest.mark.parametrize("mode", _MODES)
def test_the_printed_globs_reach_exactly_the_files_the_audit_landed(
    tmp_path: Path, mode: str, surfaces: tuple[str, ...]
) -> None:
    """Two instruments for one surface: the files the PRINTED globs reach under `Path.glob`, and
    the files the audit really treated as homes (the table of `_PATHS`). They must agree, so a
    printed line that drifts from what the scans received is red. Red before the fix: there were
    no printed globs to read."""
    repo = _make_repo(tmp_path)
    before, after = _scan(repo, mode)
    landed, output = _audit_table(
        repo, before=(*before, *_options(surfaces)), after=after
    )
    printed = _printed_surface(output)
    staged = {path for path, *_ in _PATHS}
    assert landed, "the table landed nothing, so the comparison would prove nothing"
    assert staged & _reached_by(repo.root, printed.globs) == landed


def test_the_surface_checks_see_their_planted_positives() -> None:
    """A guard never shown to fail has not been shown to work: the parse and the comparison are
    fired at the old report, at four planted defects and at a near-miss that must pass."""
    stand_in = ("AGENTS.md", "docs/**/*.md", "src/**/*.py")
    scanned = (*stand_in, "notes/*.md")
    report = (
        "CANDIDATE LOSS   : 0\n"
        "scan surface     : 4 globs (3 default + 1 --surface): "
        "AGENTS.md, docs/**/*.md, src/**/*.py, notes/*.md\n\n"
    )
    assert _surface_gaps(_printed_surface(report), scanned, 1) == []

    with pytest.raises(AssertionError, match="no 'scan surface' line"):
        _printed_surface("entries scanned  : 1\nCANDIDATE LOSS   : 0\n\n")

    planted = {
        "a surface left out of the line": report.replace(", notes/*.md", "").replace(
            "4 globs (3 default + 1", "3 globs (3 default + 0"
        ),
        "a glob that differs by one character": report.replace(
            "docs/**/*.md", "docs/*/*.md"
        ),
        "a total that is not the count": report.replace("4 globs", "5 globs"),
        "a default miscounted as a surface": report.replace(
            "(3 default + 1", "(2 default + 2"
        ),
    }
    for name, variant in planted.items():
        gaps = _surface_gaps(_printed_surface(variant), scanned, 1)
        assert gaps, f"the comparison missed {name}"

    # Each defect above breaks a glob or two counts at once, so deleting one count comparison
    # would still be seen. These break one count only: the line is caught by that comparison
    # alone, and the gap says which.
    one_count = {
        "a --surface count that is not the number given": (
            "(3 default + 2",
            "--surface count",
        ),
        "a default count that is not the number of defaults": (
            "(2 default + 1",
            "default count",
        ),
    }
    for name, (wrong, label) in one_count.items():
        variant = report.replace("(3 default + 1", wrong)
        gaps = _surface_gaps(_printed_surface(variant), scanned, 1)
        assert [gap.split(":")[0] for gap in gaps] == [label], (
            f"the comparison missed {name}: {gaps}"
        )

    spaced = report.replace("scan surface     :", "scan surface:")
    assert _surface_gaps(_printed_surface(spaced), scanned, 1) == [], (
        "the padding after the label is not part of the surface"
    )


# --- the docstring and --help say what the drain procedure now says -------------------------

_SNAPSHOT_DEFINITION = (
    "the buffer as committed at the restore point, read through a scratch file"
)

# One clause each, matched in the whitespace-folded text of the docstring and of `--help`.
_RESTORE_POINT_CLAUSES: tuple[str, ...] = (
    _SNAPSHOT_DEFINITION,
    "takes a file, not a commit",
    "byte copy",
    "never committed",
    "until the audit is clean",
)

# What the old docstring, the old help and the old closing line of the report said.
_OLD_WORDING: dict[str, str] = {
    "before deleting the snapshot": (
        r"\bbefore\s+deleting\s+the\s+(?:pre-drain\s+)?snapshot\b"
    ),
    "a copy made before any deletion": r"\ba\s+copy\s+made\s+before\s+any\s+deletion\b",
}


def _old_wording(text: str) -> list[str]:
    """The labels of the old phrases found in `text`."""
    return [
        label
        for label, pattern in _OLD_WORDING.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]


def _docstring() -> str:
    """The module docstring of the script, read from the source so nothing is imported."""
    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    return _flat(ast.get_docstring(tree) or "")


def _help_flat(repo: _Repo) -> str:
    """`--help` whitespace-folded. It runs wide: argparse breaks a hyphenated word at a line end
    when it wraps, and the clauses below hold such words."""
    done = subprocess.run(
        [sys.executable, "-B", str(repo.script), "-h"],
        cwd=repo.root.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
        env={**os.environ, "COLUMNS": "400"},
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return _flat(done.stdout)


def _between(text: str, start: str, end: str) -> str:
    assert start in text and end in text, (
        f"the help has no {start!r} or {end!r}:\n{text}"
    )
    return text.split(start, 1)[1].split(end, 1)[0]


def test_the_docstring_describes_the_snapshot_the_way_the_drain_procedure_does() -> (
    None
):
    """Red before the fix: the docstring said to run BEFORE deleting the pre-drain snapshot,
    which the drain procedure no longer deletes, and named neither the restore point, the
    scratch file nor the byte copy."""
    docstring = _docstring()
    missing = [clause for clause in _RESTORE_POINT_CLAUSES if clause not in docstring]
    assert not missing, f"the module docstring does not say {missing}"
    assert _old_wording(docstring) == [], "the module docstring keeps the old wording"


def test_help_describes_the_snapshot_the_way_the_drain_procedure_does(
    repo: _Repo,
) -> None:
    """Red before the fix: the snapshot argument was described as a copy made before any
    deletion, and `--help` named neither the restore point, the scratch file nor the byte copy."""
    helped = _help_flat(repo)
    missing = [clause for clause in _RESTORE_POINT_CLAUSES if clause not in helped]
    assert not missing, f"--help does not say {missing}"
    positional = _between(helped, "positional arguments:", "options:")
    assert _SNAPSHOT_DEFINITION in positional, (
        f"the snapshot argument is not described as {_SNAPSHOT_DEFINITION!r}: {positional}"
    )
    assert _old_wording(helped) == [], "--help keeps the old wording"


def test_the_closing_line_of_a_report_with_rows_names_the_byte_copy(
    repo: _Repo,
) -> None:
    """Red before the fix: it said to adjudicate before deleting the snapshot, which is now a
    scratch file that is rebuilt from the restore point; the file to keep is the byte copy."""
    snapshot = _snapshot(repo, _entry("lost", "the lesson is about `nowhere_token`"))
    done = _run(repo, str(snapshot), repo.base)
    assert done.returncode == 1, done.stdout + done.stderr
    report = _flat(done.stdout)
    assert "Adjudicate every row above before deleting the byte copy." in report, report
    assert _old_wording(report) == [], "the closing line keeps the old wording"


def test_the_old_wording_check_sees_its_planted_positives() -> None:
    """The three old sentences, as they stood, are found; wording close to them is not."""
    for old in (
        "Usage (run BEFORE deleting the pre-drain snapshot):",
        "the pre-drain snapshot of the buffer: a copy made before any deletion",
        "Adjudicate every row above before deleting the snapshot. Expected-clean rows:",
    ):
        assert _old_wording(_flat(old)), f"the check missed {old!r}"
    for near in (
        "Adjudicate every row above before deleting the byte copy.",
        "keep the byte copy until the audit is clean",
        "a copy of the buffer that is never committed",
        "before any deletion the operator commits the buffer",
    ):
        assert _old_wording(near) == [], f"the check flagged {near!r}"


def test_the_docstring_and_help_name_every_file_name_the_audit_refuses(
    repo: _Repo,
) -> None:
    """The refusal list is data in the script (`NEVER_A_LANDING_SITE`). Both texts list each
    name, so a name added to the data and not to the text is red, and the two ledgers the row
    names are asserted to be in the data. Red before the fix for those two names."""
    refused = cast(tuple[str, ...], _load(repo.script).NEVER_A_LANDING_SITE)
    ledger_names = {Path(ledger).name for ledger in _LEDGERS}
    assert ledger_names <= set(refused), (
        f"{ledger_names - set(refused)} are not refused"
    )
    docstring, helped = _docstring(), _help_flat(repo)
    for name in refused:
        assert name in docstring, f"the module docstring does not name {name!r}"
        assert name in helped, f"--help does not name {name!r}"


# The clause both texts use for the report line that prints the globs: the docstring says "on
# the `scan surface` line beside them" and `--help` says "on its `scan surface` line, beside
# the counts".
_SCAN_SURFACE_CLAUSES: tuple[str, ...] = ("`scan surface` line",)


def test_the_docstring_and_help_document_the_scan_surface_line(repo: _Repo) -> None:
    """Pins prose the report line came with and no test held: green on the tree it was written
    against, red when the docstring paragraph or the `--help` line that tells a reader the
    report prints the globs it scanned is deleted."""
    for where, text in (
        ("the module docstring", _docstring()),
        ("--help", _help_flat(repo)),
    ):
        missing = [clause for clause in _SCAN_SURFACE_CLAUSES if clause not in text]
        assert not missing, f"{where} does not say {missing}"


# --- the files named learnings-pre-drain-*.md are byte copies, not snapshots -----------------

# The pre-drain snapshot is now the scratch file read from the restore point, and the copy the
# operator keeps is a byte copy. The files named `learnings-pre-drain-*.md` are those copies, so
# a text that calls them snapshots contradicts the definition it gives two paragraphs earlier.
_STALE_SNAPSHOT_NAMES: dict[str, str] = {
    "every (other) pre-drain snapshot": r"\bevery\s+(?:other\s+)?pre-drain\s+snapshot\b",
    "pre-drain snapshots": r"\bpre-drain\s+snapshots\b",
}

# The new shape: the file-name pattern introduced as a byte copy, in `--help` and the docstring.
_BYTE_COPY_NAMES = re.compile(
    r"\bbyte cop(?:y|ies)\b[^.()]{0,40}\(`?learnings-pre-drain-\*\.md`?\)"
)


def _stale_snapshot_names(text: str) -> list[str]:
    """The labels of the stale shapes found in `text`."""
    return [
        label
        for label, pattern in _STALE_SNAPSHOT_NAMES.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]


def test_the_pre_drain_file_names_are_called_byte_copies_not_snapshots(
    repo: _Repo,
) -> None:
    """Red before the fix: the module docstring, `--help`, a comment and a function docstring
    called the files named `learnings-pre-drain-*.md` pre-drain snapshots, in the same texts that
    define the pre-drain snapshot as the scratch file and call the copy kept until the audit is
    clean a byte copy. The scan reads the whole script, comments included, with `#` folded away,
    and the second half asserts the new shape is present, so a scan that sees nothing is red."""
    source = _flat(_SCRIPT.read_text(encoding="utf-8").replace("#", " "))
    assert _stale_snapshot_names(source) == [], (
        "the script still calls the byte copies snapshots"
    )
    for where, text in (
        ("the module docstring", _docstring()),
        ("--help", _help_flat(repo)),
    ):
        assert _BYTE_COPY_NAMES.search(text), (
            f"{where} does not introduce learnings-pre-drain-*.md as a byte copy"
        )


def test_the_stale_snapshot_name_check_sees_its_planted_positives() -> None:
    """The shapes the stale wording took (the docstring and `--help` sentence, the comment, the
    function docstring) and a plural variant are found, wording close to it is not, and the
    byte-copy shape is accepted only when the file-name pattern follows the term."""
    for stale in (
        "under audit (the path given), every other pre-drain snapshot (`learnings-pre-drain-*.md`) and",
        "# proves nothing: the buffer, every pre-drain snapshot (an older one still holds the KEEP",
        "is found: the buffer, every pre-drain snapshot and the ledgers, by name",
        "older pre-drain snapshots keep the entries that dwelt through earlier drains",
    ):
        flat = _flat(stale.replace("#", " "))
        assert _stale_snapshot_names(flat), f"the check missed {stale!r}"
    for near in (
        "The pre-drain snapshot is the buffer as committed at the restore point",
        "did every entry of the pre-drain snapshot land in a promotion target",
        "every byte copy (`learnings-pre-drain-*.md`) and the ledgers",
        "pre-drain snapshot (first argument): the buffer as committed at the restore point",
    ):
        assert _stale_snapshot_names(_flat(near)) == [], f"the check flagged {near!r}"
    for shaped in (
        "every byte copy (`learnings-pre-drain-*.md`) and the ledgers",
        "every byte copy (learnings-pre-drain-*.md) and the ledgers",
        "every byte copy of the buffer (`learnings-pre-drain-*.md`)",
    ):
        assert _BYTE_COPY_NAMES.search(shaped), f"the shape check missed {shaped!r}"
    for unshaped in (
        "every other pre-drain snapshot (`learnings-pre-drain-*.md`) and the ledgers",
        "keep the byte copy until the audit is clean",
    ):
        assert not _BYTE_COPY_NAMES.search(unshaped), (
            f"the shape check took {unshaped!r}"
        )
