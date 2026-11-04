"""`review_core` prints the review's mechanical checks, so a session reads them instead of retyping them.

The review's Step 0 list, its stat, its line-ending check, its lint scope and its documentation lookup
were each a command a session had to remember and get right. A plain `git grep` and `git diff HEAD`
cannot see a file the task created, `--stat` rescales its bars, and a zero printed with no count of what
was searched reads as clean. Each test builds a scratch repository in which one fact is planted (a
reader that exists only as an untracked file, a file whose endings changed, a symbol whose signature
changed), runs the script as a process the way a session does, and checks that the planted fact is
printed. A control beside each one shows that the plain command misses it, so the fixture is a real
positive and not a case every instrument passes.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "plugins" / "core" / "skills" / "post-task-review"
_SCRIPT = _SKILL / "scripts" / "review_core.py"

# The reader of `alpha` that exists only as an untracked file, with a class and two names the
# derivation must skip by rule (a dunder method and a test function).
_NEW_FEATURE = (
    "from app import alpha\n"
    "\n"
    "RESULT = alpha(2, 3)\n"
    "\n"
    "\n"
    "class Widget:\n"
    "    def __repr__(self):\n"
    '        return "w"\n'
    "\n"
    "\n"
    "def test_new_thing():\n"
    "    return alpha(0, 0)\n"
)

_MATRIX = (
    "| Code Path Changed | Check These Docs |\n"
    "|---|---|\n"
    "| `src/{pkg}.py` (any file) | `docs/guide.md` |\n"
    "| `.ai/` | `AGENTS.md` |\n"
    "| New feature created | create a README |\n"
)


class _Run(NamedTuple):
    repo: Path
    result: "subprocess.CompletedProcess[str]"

    @property
    def lines(self) -> list[str]:
        return self.result.stdout.splitlines()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _base_repo(repo: Path) -> Path:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    for key, value in (
        ("user.name", "t"),
        ("user.email", "t@example.com"),
        ("commit.gpgsign", "false"),
        ("core.autocrlf", "false"),
    ):
        _git(repo, "config", key, value)
    _write(repo / ".gitignore", "ignored.txt\n")
    _write(
        repo / "AGENTS.md",
        "# Agents\n\n## Commands\n\n```bash\nuv run ruff check .\nuv run pytest -q\n```\n",
    )
    _write(
        repo / "src" / "app.py",
        "def alpha(x):\n    return x\n\n\ndef beta():\n    return 1\n",
    )
    # `gamma` is read here before the task adds it, and `alphabet` is not a reader of `alpha`.
    _write(
        repo / "src" / "user.py",
        "from app import alpha, gamma\n\nVALUE = alpha(1)\nalphabet = 2\n",
    )
    _write(repo / "docs" / "guide.md", "# Guide\n\nCall alpha first.\n")
    for name in ("keep.cfg", "legacy.cfg", "mixed.txt"):
        (repo / name).write_bytes(b"one\r\ntwo\r\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _do_task(repo: Path) -> None:
    _write(
        repo / "src" / "app.py",
        "def alpha(x, y):\n    return x + y\n\n\ndef gamma():\n    return 2\n",
    )
    _write(repo / "src" / "new_feature.py", _NEW_FEATURE)
    _write(repo / "ignored.txt", "alpha\n")
    (repo / "keep.cfg").write_bytes(b"one\r\ntwo\r\nthree\r\n")
    (repo / "legacy.cfg").write_bytes(b"one\ntwo\n")
    (repo / "mixed.txt").write_bytes(b"one\r\ntwo\r\nthree\n")
    (repo / "blob.bin").write_bytes(b"\x00\x01\x02")


def _run(cwd: Path, *args: str, ceiling: Path | None = None) -> _Run:
    env = dict(os.environ)
    if ceiling is not None:
        env["GIT_CEILING_DIRECTORIES"] = str(ceiling)
    result = subprocess.run(
        [sys.executable, "-B", str(_SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env=env,
    )
    return _Run(cwd, result)


def _section(run: _Run, number: int) -> list[str]:
    inside = False
    kept: list[str] = []
    for line in run.lines:
        if line.startswith("== "):
            inside = line.startswith(f"== {number}. ")
        elif inside:
            kept.append(line)
    return kept


@pytest.fixture(scope="module")
def tasked(tmp_path_factory: pytest.TempPathFactory) -> _Run:
    repo = _base_repo(tmp_path_factory.mktemp("core") / "repo")
    _do_task(repo)
    return _run(repo)


def test_untracked_files_are_listed_and_ignored_files_are_not(tasked: _Run) -> None:
    assert "src/new_feature.py" not in _git(
        tasked.repo, "diff", "--name-only", "HEAD"
    ), (
        "control: the plain form must miss the untracked file, or this fixture proves nothing"
    )
    lines = _section(tasked, 1)
    assert "?\tsrc/new_feature.py" in lines
    assert "?\tblob.bin" in lines
    assert "M\tsrc/app.py" in lines
    assert not any("ignored.txt" in line for line in tasked.lines)
    assert (
        "changed: 6 (4 tracked, 2 untracked) of 8 tracked and 2 untracked files"
        in lines
    )


def test_a_clean_tree_prints_its_denominator_and_points_at_base(tmp_path: Path) -> None:
    run = _run(_base_repo(tmp_path / "repo"))
    lines = _section(run, 1)
    assert (
        "changed: 0 (0 tracked, 0 untracked) of 8 tracked and 0 untracked files"
        in lines
    )
    assert any("--base" in line for line in lines)
    assert run.result.returncode == 0


def test_numstat_counts_match_git_and_untracked_files_count_their_lines(
    tasked: _Run,
) -> None:
    printed = {
        line.split("\t")[1]: line.split("\t")[0]
        for line in _section(tasked, 2)
        if "\t" in line
    }
    for row in _git(tasked.repo, "diff", "--numstat", "HEAD").splitlines():
        added, deleted, path = row.split("\t")
        assert printed[path] == f"+{added} -{deleted}", path
    assert printed["src/new_feature.py"] == f"+{len(_NEW_FEATURE.splitlines())} -0"
    assert printed["blob.bin"] == "binary"


def test_plan_comparison_reports_both_directions(tasked: _Run, tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text(
        "# files\n- `src/app.py` change alpha\nsrc/user.py\ndocs/\n", encoding="utf-8"
    )
    run = _run(tasked.repo, "--plan", str(plan))
    lines = _section(run, 2)
    assert "plan: 3 path(s) in plan.txt" in lines
    assert (
        "changed, not in plan (5): blob.bin, keep.cfg, legacy.cfg, mixed.txt, src/new_feature.py"
        in lines
    )
    assert "in plan, not changed (2): docs/, src/user.py" in lines
    assert run.result.returncode == 0


def test_no_plan_is_skipped_and_an_unreadable_plan_is_not_checked(
    tasked: _Run, tmp_path: Path
) -> None:
    assert any(
        line.startswith("SKIPPED (not asked): plan comparison")
        for line in _section(tasked, 2)
    )
    run = _run(tasked.repo, "--plan", str(tmp_path / "missing.txt"))
    assert run.result.returncode == 2
    assert any(line.startswith("NOT CHECKED: plan") for line in run.lines)
    assert any(line.startswith("== 4. ") for line in run.lines), (
        "the other sections still ran"
    )


def test_derived_symbols_are_labelled_and_skipped_names_are_counted(
    tasked: _Run,
) -> None:
    text = "\n".join(_section(tasked, 3))
    assert re.search(r"^alpha \(signature changed\): ", text, re.MULTILINE)
    assert re.search(r"^beta \(removed\): ", text, re.MULTILINE)
    assert re.search(r"^gamma \(added\): ", text, re.MULTILINE)
    assert re.search(r"^Widget \(added\): ", text, re.MULTILINE)
    assert "__repr__" not in text
    assert "test_new_thing" not in text
    assert "skipped by rule: 2" in text


def test_dependents_list_every_reader_including_untracked_and_never_ignored(
    tasked: _Run,
) -> None:
    expected = 0
    for path in (p for p in tasked.repo.rglob("*.py") if p.is_file()):
        relative = path.relative_to(tasked.repo).as_posix()
        if relative.startswith(".git/"):
            continue
        expected += sum(
            1
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if re.search(r"\balpha\b", line)
        )
    tracked_only = _git(tasked.repo, "grep", "-n", "-w", "alpha", "--", "*.py").count(
        "\n"
    )
    assert expected - tracked_only == _NEW_FEATURE.count("alpha"), (
        "control: the plain form misses exactly the untracked file's hits"
    )
    lines = _section(tasked, 3)
    header = next(line for line in lines if line.startswith("alpha ("))
    assert f": {expected} hits in 3 files; 1 outside the changed set" in header
    assert not any("new_feature" in line for line in lines), (
        "files already in the diff are not listed"
    )
    assert any(
        re.fullmatch(r"\s+UNKNOWN\s+src/user\.py\s+2 hit\(s\)", x) for x in lines
    )
    assert not any("guide.md" in line for line in lines), (
        "a derived name is searched in code files only; the guide is Step 7's question"
    )


def test_given_symbols_print_the_surface_beside_a_zero(tasked: _Run) -> None:
    run = _run(
        tasked.repo,
        *("--symbol", "VALUE", "--symbol", "zzz_absent_symbol", "--symbol", "alpha"),
    )
    in_scope = len(
        _git(tasked.repo, "ls-files", "-c", "-o", "--exclude-standard").splitlines()
    )
    code_scope = len(
        _git(
            tasked.repo, "ls-files", "-c", "-o", "--exclude-standard", "--", "*.py"
        ).splitlines()
    )
    lines = _section(run, 3)
    assert (
        "alpha (signature changed): 8 hits in 4 files; 2 outside the changed set"
        in lines
    ), (
        "a given name is a fixed string in every file: it reaches the guide and counts `alphabet`"
    )
    assert any(
        re.fullmatch(r"\s+UNKNOWN\s+docs/guide\.md\s+1 hit\(s\)", x) for x in lines
    )
    assert "beta (removed): 0 hits in 0 files; 0 outside the changed set" in lines
    assert f"  none found over {code_scope} files in scope" in lines
    assert "VALUE (given): 1 hits in 1 files; 1 outside the changed set" in lines
    assert (
        "zzz_absent_symbol (given): 0 hits in 0 files; 0 outside the changed set"
        in lines
    )
    assert f"  none found over {in_scope} files in scope" in lines


def test_roots_limit_both_the_search_and_the_scan_surface_it_prints(
    tasked: _Run,
) -> None:
    run = _run(tasked.repo, "--roots", "docs", "--symbol", "alpha")
    in_docs = _git(
        tasked.repo, "ls-files", "-c", "-o", "--exclude-standard", "--", "docs"
    )
    lines = _section(run, 3)
    assert (
        "scan: git grep -n --untracked -I -F; derived names over 0 code files, "
        f"given names over {len(in_docs.splitlines())} files (roots: docs)"
    ) in lines
    assert (
        "alpha (signature changed): 1 hits in 1 files; 1 outside the changed set"
        in lines
    )
    assert any(
        re.fullmatch(r"\s+UNKNOWN\s+docs/guide\.md\s+1 hit\(s\)", x) for x in lines
    )
    assert not any("src/" in x for x in lines), (
        "readers outside the roots are not searched"
    )


def test_an_added_name_prints_counts_only_and_a_given_one_lists_its_readers(
    tasked: _Run,
) -> None:
    lines = _section(tasked, 3)
    at = next(i for i, x in enumerate(lines) if x.startswith("gamma (added): "))
    assert lines[at] == "gamma (added): 2 hits in 2 files; 1 outside the changed set"
    assert not lines[at + 1].startswith("  UNKNOWN"), (
        "nothing written earlier can have read an added name, so its outside hits are not listed"
    )
    listed = _section(_run(tasked.repo, "--symbol", "gamma"), 3)
    assert any(
        re.fullmatch(r"\s+UNKNOWN\s+src/user\.py\s+1 hit\(s\)", x) for x in listed
    ), "--symbol lists the readers of an added name on request"


def test_symbols_beyond_the_cap_are_not_checked_and_named(tasked: _Run) -> None:
    run = _run(tasked.repo, "--max-symbols", "1")
    assert run.result.returncode == 2
    assert any(
        line.startswith("NOT CHECKED: ") and "not searched" in line
        for line in run.lines
    ), run.result.stdout


def test_readers_beyond_the_file_cap_are_counted_not_dropped(tasked: _Run) -> None:
    run = _run(tasked.repo, "--max-files", "1", "--symbol", "alpha")
    assert run.result.returncode == 2
    lines = _section(run, 3)
    assert (
        sum(1 for x in lines if re.fullmatch(r"\s+UNKNOWN\s+\S+\s+\d+ hit\(s\)", x))
        >= 1
    )
    assert (
        "NOT CHECKED: dependents: alpha: 1 more outside file(s) not listed (--max-files 1)"
        in lines
    )


def test_line_endings_flag_mixed_and_converted_files_and_skip_binary(
    tasked: _Run,
) -> None:
    rows = {
        line.split("\t")[0]: line.split("\t")[1:]
        for line in _section(tasked, 4)
        if "\t" in line
    }
    assert rows["src/app.py"] == ["lf"]
    assert rows["keep.cfg"] == ["crlf"], (
        "control: a CRLF file edited in CRLF is not flagged"
    )
    assert rows["mixed.txt"][0] == "mixed (lf=1 crlf=2)"
    assert rows["mixed.txt"][1] == "MIXED"
    assert rows["legacy.cfg"][0] == "lf"
    assert rows["legacy.cfg"][1].startswith("CHANGED stored crlf, now lf")
    assert rows["blob.bin"] == ["binary (skipped)"]
    assert "endings: lf 3, crlf 1, mixed 1, binary 1; flagged 2 of 6" in _section(
        tasked, 4
    )


def test_lint_scope_names_the_tool_and_lists_what_nothing_covers(tasked: _Run) -> None:
    rows = {
        line.split("\t")[0]: line.split("\t")[1:]
        for line in _section(tasked, 5)
        if "\t" in line
    }
    assert rows[".py"] == ["2 file(s)", "ruff"]
    assert rows[".cfg"] == ["2 file(s)", "NO TOOL named in the commands covers it"]
    assert rows[".bin"][1].startswith("NO TOOL")
    assert (
        "lint scope: 2 of 6 changed file(s) have a named tool; 4 have none"
        in _section(tasked, 5)
    )


def test_lint_scope_without_a_commands_section_is_not_checked(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path / "repo")
    (repo / "AGENTS.md").unlink()
    run = _run(repo)
    assert run.result.returncode == 2
    assert any(line.startswith("NOT CHECKED: lint scope") for line in _section(run, 5))


def test_matrix_rows_match_paths_and_an_unmatched_file_reads_unknown(
    tasked: _Run, tmp_path: Path
) -> None:
    matrix = tmp_path / "matrix.md"
    matrix.write_text(_MATRIX, encoding="utf-8")
    lines = _section(_run(tasked.repo, "--matrix", str(matrix)), 6)
    assert "matrix: matrix.md (2 path row(s), 1 event row(s) judged by hand)" in lines
    assert any(x.startswith("src/app.py\t") and "docs/guide.md" in x for x in lines)
    assert any(
        x.startswith("src/new_feature.py\t") and "docs/guide.md" in x for x in lines
    )
    assert any(x.startswith("legacy.cfg\tNO MATRIX ROW") for x in lines)
    assert "matrix: 2 of 6 changed file(s) matched a row; 4 have no row" in lines


def test_the_default_matrix_is_the_labelled_sample_and_a_missing_one_is_not_checked(
    tasked: _Run, tmp_path: Path
) -> None:
    assert any(line.startswith("matrix: SAMPLE ") for line in _section(tasked, 6))
    run = _run(tasked.repo, "--matrix", str(tmp_path / "missing.md"))
    assert run.result.returncode == 2
    assert any(
        line.startswith("NOT CHECKED: documentation matrix") for line in run.lines
    )


def test_base_reviews_committed_work_and_without_it_nothing_differs(
    tmp_path: Path,
) -> None:
    repo = _base_repo(tmp_path / "repo")
    _do_task(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "task")
    assert "changed: 0 (0 tracked, 0 untracked)" in "\n".join(_section(_run(repo), 1))
    run = _run(repo, "--base", "HEAD~1")
    lines = _section(run, 1)
    assert "A\tsrc/new_feature.py" in lines
    assert "M\tsrc/app.py" in lines
    assert (
        "changed: 6 (6 tracked, 0 untracked) of 10 tracked and 0 untracked files"
        in lines
    )
    assert run.lines[0].startswith("review_core: base=HEAD~1 (")


def test_an_unresolvable_base_and_a_non_repository_are_not_checked(
    tasked: _Run, tmp_path: Path
) -> None:
    bad = _run(tasked.repo, "--base", "no-such-ref")
    assert bad.result.returncode == 2
    assert any("no-such-ref" in x and x.startswith("NOT CHECKED:") for x in bad.lines)
    plain = tmp_path / "plain"
    plain.mkdir()
    outside = _run(plain, ceiling=tmp_path)
    assert outside.result.returncode == 2
    assert any(
        x.startswith("NOT CHECKED: not inside a git work tree") for x in outside.lines
    )


def test_the_summary_line_counts_sections_not_checked_and_skipped(tasked: _Run) -> None:
    assert tasked.result.returncode == 0, tasked.result.stderr
    assert tasked.lines[0].startswith("review_core: base=HEAD (")
    assert tasked.lines[-1] == (
        "review_core: 6 changed file(s); 7 of 7 sections ran; 0 NOT CHECKED; 1 skipped (not asked)"
    )


def test_the_skill_points_at_the_script_in_at_most_three_added_lines() -> None:
    lines = (_SKILL / "SKILL.md").read_text(encoding="utf-8").splitlines()
    pointer = [
        line for line in lines if "${CLAUDE_SKILL_DIR}/scripts/review_core.py" in line
    ]
    assert pointer, "SKILL.md must name the script by its skill-relative path"
    assert _SCRIPT.is_file()
    assert len(lines) <= 499, (
        "499 lines is the most the audit allows: it counts one more"
    )
