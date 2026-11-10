"""The checks of the branch switch stash scope wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_count_reads_the_same_from_a_subdirectory`: The command Step 2 prints, run as printed, counts every untracked file of the repository from the root and from a subdirectory.
* `test_the_old_count_command_misses_the_rest_of_the_tree_from_a_subdirectory`: Planted positive: the command Step 2 printed before the pathspec counts only the directory it runs in, so the equal pair in the test above is a measurement and not a blind probe.
"""

import shlex
import subprocess
from pathlib import Path

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "branch-switch"
    / "SKILL.md"
)
_STEP_2 = "### Step 2"
_FENCE = "```"
_OLD_COUNT_COMMAND = "git ls-files --others --exclude-standard"


def _outside_fences(lines: list[str]) -> list[tuple[int, str]]:
    """(index, line) for every line that is neither a fence line nor inside a fenced block."""
    kept: list[tuple[int, str]] = []
    fenced = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith(_FENCE):
            fenced = not fenced
        elif not fenced:
            kept.append((index, line))
    return kept


def _level(line: str) -> int:
    hashes = len(line) - len(line.lstrip("#"))
    return hashes if hashes and line[hashes : hashes + 1] == " " else 0


def _section(text: str, prefix: str) -> str:
    """The lines from the one heading that starts with `prefix` to the next heading of its level
    or a higher one. A `#` line inside a fence is not a heading."""
    lines = text.splitlines()
    starts = [i for i, line in _outside_fences(lines) if line.startswith(prefix)]
    assert len(starts) == 1, f"{len(starts)} headings start with {prefix!r}, expected 1"
    start = starts[0]
    level = _level(lines[start])
    end = next(
        (
            i
            for i, line in _outside_fences(lines)
            if i > start and 0 < _level(line) <= level
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def _skill_text() -> str:
    return _SKILL.read_text(encoding="utf-8")


def _git(where: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(where), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=True,
    )


def _tree_with_untracked(tmp_path: Path) -> tuple[Path, Path]:
    """A repository with six untracked files: two at the root, two in a subdirectory, two in a new
    directory two levels down (one line in `git status --short`). Returns the root and the
    subdirectory."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for name in (
        "a.txt",
        "b.txt",
        "sub/c.txt",
        "sub/d.txt",
        "other/deep/e.txt",
        "other/deep/f.txt",
    ):
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    return repo, repo / "sub"


def _count_arguments() -> list[str]:
    """The words of the count command in Step 2: the first line inside its first fenced block,
    without the pipe to `wc -l`."""
    fenced = False
    for line in _section(_skill_text(), _STEP_2).splitlines():
        if line.lstrip().startswith(_FENCE):
            if fenced:
                break
            fenced = True
        elif fenced and line.strip():
            return shlex.split(line.strip().split(" | ")[0])
    raise AssertionError("Step 2 has no fenced command")


def _files_counted(where: Path, arguments: list[str]) -> int:
    """How many names the count command prints when it runs in `where`: what `| wc -l` counts."""
    done = _git(where, *arguments[1:])
    return len([line for line in done.stdout.splitlines() if line.strip()])


def test_the_count_reads_the_same_from_a_subdirectory(tmp_path: Path) -> None:
    """The command Step 2 prints, run as printed, counts every untracked file of the repository
    from the root and from a subdirectory."""
    repo, sub = _tree_with_untracked(tmp_path)
    arguments = _count_arguments()
    assert arguments[:2] == ["git", "ls-files"], arguments
    assert _files_counted(repo, arguments) == 6
    assert _files_counted(sub, arguments) == 6, (
        "the count depends on the directory it runs in"
    )


def test_the_old_count_command_misses_the_rest_of_the_tree_from_a_subdirectory(
    tmp_path: Path,
) -> None:
    """Planted positive: the command Step 2 printed before the pathspec counts only the directory
    it runs in, so the equal pair in the test above is a measurement and not a blind probe."""
    repo, sub = _tree_with_untracked(tmp_path)
    old = shlex.split(_OLD_COUNT_COMMAND)
    assert _files_counted(repo, old) == 6
    assert _files_counted(sub, old) == 2
