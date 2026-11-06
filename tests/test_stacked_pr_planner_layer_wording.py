"""The checks of the stacked pr planner layer wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_printed_commands_run_in_a_throwaway_repository`: the printed commands run in a throwaway repository
* `test_the_command_scan_sees_planted_lines`: the command scan sees planted lines
* `test_a_missing_shell_fails_and_the_one_beside_git_is_found`: a missing shell fails and the one beside git is found
"""

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _ROOT / "plugins" / "orchestration" / "skills" / "stacked-pr-planner"

_TRIGGERS = "layer-triggers.md"
_MECHANICS = "layer-mechanics.md"


_PLACEHOLDER = re.compile(r"<[^<>\n]+>")
_ASSIGNMENT_LED = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=")
_COMMAND_LINES = 6


# --- reading ------------------------------------------------------------------------------


def _reference(name: str) -> Path:
    return _SKILL_DIR / "references" / name


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(_ROOT).as_posix()} does not exist")
    return path.read_text(encoding="utf-8")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _fenced_blocks(section: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in section.split("\n"):
        if _is_fence(line):
            if in_fence:
                blocks.append(current)
                current = []
            in_fence = not in_fence
        elif in_fence:
            current.append(line)
    return blocks


# --- the claims ---------------------------------------------------------------------------


# --- the pointer --------------------------------------------------------------------------


# --- the printed commands run -------------------------------------------------------------


def _fenced_lines(text: str) -> list[str]:
    """The non-blank lines inside fenced blocks, indentation dropped, in file order."""
    return [
        line.strip() for block in _fenced_blocks(text) for line in block if line.strip()
    ]


def _git_lines(text: str) -> list[str]:
    """Every line that starts with `git ` once its indentation is dropped."""
    return [
        line.strip() for line in text.split("\n") if line.lstrip().startswith("git ")
    ]


def _surface_problems(*texts: str) -> list[str]:
    """What the two instruments, a fence walk and a count of `git ` lines, make of the texts."""
    fenced = [line for text in texts for line in _fenced_lines(text)]
    started = [line for text in texts for line in _git_lines(text)]
    problems: list[str] = []
    if len(fenced) != _COMMAND_LINES:
        problems.append(
            f"{len(fenced)} fenced command lines, expected {_COMMAND_LINES}"
        )
    if len(started) != _COMMAND_LINES:
        problems.append(f"{len(started)} lines start `git `, expected {_COMMAND_LINES}")
    if fenced != started:
        problems.append(
            "the fence walk and the count of `git ` lines read different lines"
        )
    problems.extend(
        f"an assignment-led command line: {line!r}"
        for line in fenced
        if _ASSIGNMENT_LED.match(line)
    )
    return problems


def _the_line(lines: Sequence[str], start: str) -> str:
    hits = [line for line in lines if line.startswith(start)]
    if len(hits) != 1:
        raise AssertionError(f"{len(hits)} command lines start {start!r}, expected 1")
    return hits[0]


def _fill(command: str, values: dict[str, str]) -> str:
    """The command with each `<name>` replaced; a placeholder left over fails loudly."""
    filled = command
    for name, value in values.items():
        filled = filled.replace(f"<{name}>", value)
    left = _PLACEHOLDER.findall(filled)
    if left:
        raise AssertionError(f"placeholders {left} left unfilled in {command!r}")
    return filled


def _shell() -> str:
    """A POSIX shell: `sh` from PATH, else the one that ships with git. Never a skip."""
    found = shutil.which("sh")
    if found:
        return found
    git = shutil.which("git")
    if git:
        for parent in Path(git).resolve().parents:
            bundled = parent / "usr" / "bin" / "sh.exe"
            if bundled.is_file():
                return str(bundled)
    raise AssertionError(
        "no POSIX shell: `sh` is not on PATH and none ships beside git"
    )


def _run(repo: Path, command: str) -> tuple[int, str]:
    """The exit code and standard output of `command` through `sh -c`, run inside `repo`."""
    shell = _shell()
    path = os.pathsep.join([str(Path(shell).parent), os.environ.get("PATH", "")])
    done = subprocess.run(
        [shell, "-c", command],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PATH": path},
        timeout=60,
        check=False,
    )
    return done.returncode, done.stdout


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=True,
    )
    return done.stdout


def _repo(path: Path) -> Path:
    """An empty repository on branch `main`, with the identity a commit needs."""
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    for key, value in (
        ("user.name", "tester"),
        ("user.email", "tester@example.invalid"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
    ):
        _git(path, "config", key, value)
    return path


def _commit(repo: Path, message: str, files: dict[str, str | None]) -> str:
    """Write (or, for None, delete) each file, commit them all and return the commit."""
    for relative, body in files.items():
        target = repo / relative
        if body is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _guard_problems(tmp: Path, command: str) -> list[str]:
    head, tail = command.rsplit(" | ", 1)
    if "ai-changelog" not in tail or "ai-changelog" in head:
        return [f"the last stage of the guard is not the exemption: {tail!r}"]
    values = {"base": "main", "layer": "layer", "declared files regex": "^src/"}
    repo = _repo(tmp / "guard")
    _commit(repo, "base", {"src/code.py": "one\n", "docs/guide.md": "one\n"})
    _git(repo, "checkout", "-q", "-b", "layer")
    _commit(
        repo,
        "a compliant layer: its code and the two logs of the checklist",
        {
            "src/code.py": "two\n",
            ".ai/learnings.md": "x\n",
            ".ai/ai-changelog.md": "x\n",
        },
    )
    problems: list[str] = []
    _, compliant = _run(repo, _fill(command, values))
    if compliant.split():
        problems.append(f"the guard fires on a compliant layer: {compliant.split()}")
    _, without = _run(repo, _fill(head, values))
    if sorted(without.split()) != [".ai/ai-changelog.md", ".ai/learnings.md"]:
        problems.append(
            f"the guard without its exemption stage prints {without.split()}, "
            "expected the two logs"
        )
    _commit(repo, "a stray path", {"docs/other.md": "x\n"})
    _, stray = _run(repo, _fill(command, values))
    if stray.split() != ["docs/other.md"]:
        problems.append(f"a stray path prints {stray.split()}, expected docs/other.md")
    return problems


def _conditional_problems(tmp: Path, command: str) -> list[str]:
    repo = _repo(tmp / "conditional")
    _commit(repo, "base", {"src/present.py": "one\n"})
    problems: list[str] = []
    code, out = _run(
        repo, _fill(command, {"base-tip": "main", "file": "src/present.py"})
    )
    if code != 0 or out.split() != ["src/present.py"]:
        problems.append(f"a file the base holds prints {out.split()} (exit {code})")
    code, out = _run(
        repo, _fill(command, {"base-tip": "main", "file": "src/absent.py"})
    )
    if code != 0 or out != "":
        problems.append(
            f"a file the base lacks prints {out!r} (exit {code}), not nothing"
        )
    return problems


def _delta_problems(tmp: Path, rows_command: str, rules_command: str) -> list[str]:
    repo = _repo(tmp / "delta")
    pin = _commit(
        repo,
        "the trunk at the pin",
        {
            "src/a.py": "one\n",
            "src/b.py": "one\n",
            "src/c.py": "one\n",
            "AGENTS.md": "rule one\n",
            "other.txt": "one\n",
        },
    )
    _git(repo, "checkout", "-q", "-b", "layer")
    _commit(repo, "a layer", {"src/a.py": "layer\n", "src/b.py": "layer\n"})
    _git(repo, "branch", "layer-empty", "main")
    _git(repo, "checkout", "-q", "-b", "target-work", "main")
    moved = _commit(
        repo,
        "the target moves: one layer file changed, one deleted, the rules file changed",
        {
            "src/a.py": "target\n",
            "src/b.py": None,
            "AGENTS.md": "rule two\n",
            "other.txt": "t\n",
        },
    )
    _git(repo, "update-ref", "refs/remotes/origin/main", moved)
    values = {
        "pin": pin,
        "target": "main",
        "base": "main",
        "layer": "layer",
        "rules file": "AGENTS.md",
    }
    problems: list[str] = []
    _, rows = _run(repo, _fill(rows_command, values))
    if rows.splitlines() != ["M\tsrc/a.py", "D\tsrc/b.py"]:
        problems.append(
            f"the layer's rows are {rows.splitlines()}, expected its M and D rows only"
        )
    _, rules = _run(repo, _fill(rules_command, values))
    if "-rule one" not in rules or "+rule two" not in rules or "other.txt" in rules:
        problems.append(
            f"the rules-file diff is {rules!r}, expected that file's change alone"
        )
    _, whole = _run(repo, _fill(rows_command, {**values, "layer": "layer-empty"}))
    if len(whole.splitlines()) != 4 or "other.txt" not in whole:
        problems.append(
            f"a layer with no path prints {whole.splitlines()}, expected the whole delta"
        )
    return problems


def _fork_problems(tmp: Path, log_command: str, diff_command: str) -> list[str]:
    repo = _repo(tmp / "fork")
    _commit(repo, "the trunk", {"shared.txt": "one\n", "keep.txt": "one\n"})
    _git(repo, "checkout", "-q", "-b", "chain")
    # The two new files differ throughout, so rename detection cannot pair an A with a D.
    _commit(repo, "one unmerged commit", {"chain.txt": "chain one\nchain two\n"})
    _git(repo, "checkout", "-q", "main")
    moved = _commit(
        repo,
        "the trunk moves",
        {"shared.txt": "two\n", "trunk-only.txt": "trunk one\ntrunk two\n"},
    )
    _git(repo, "update-ref", "refs/remotes/origin/main", moved)
    values = {"trunk": "main"}
    problems: list[str] = []
    _git(repo, "checkout", "-q", "chain")
    _, unmerged = _run(repo, _fill(log_command, values))
    if len(unmerged.splitlines()) != 1:
        problems.append(
            f"HEAD on a chain prints {unmerged.splitlines()}, expected one line"
        )
    _, rows = _run(repo, _fill(diff_command, values))
    if sorted(rows.splitlines()) != [
        "A\tchain.txt",
        "D\ttrunk-only.txt",
        "M\tshared.txt",
    ]:
        problems.append(f"the side-effect rows are {sorted(rows.splitlines())}")
    _git(repo, "checkout", "-q", "main")
    _, none = _run(repo, _fill(log_command, values))
    if none != "":
        problems.append(f"HEAD on the trunk prints {none!r}, expected nothing")
    return problems


def test_the_printed_commands_run_in_a_throwaway_repository(tmp_path: Path) -> None:
    triggers = _read(_reference(_TRIGGERS))
    mechanics = _read(_reference(_MECHANICS))
    surface = _surface_problems(triggers, mechanics)
    assert not surface, "the scan surface is not what the test claims: " + "; ".join(
        surface
    )

    lines = [*_fenced_lines(triggers), *_fenced_lines(mechanics)]
    problems = [
        *_guard_problems(
            tmp_path, _the_line(lines, "git diff --name-only <base>...<layer> |")
        ),
        *_conditional_problems(tmp_path, _the_line(lines, "git ls-tree")),
        *_delta_problems(
            tmp_path,
            _the_line(lines, "git diff --name-status <pin>"),
            _the_line(lines, "git diff <pin>"),
        ),
        *_fork_problems(
            tmp_path,
            _the_line(lines, "git log --oneline origin/<trunk>"),
            _the_line(lines, "git diff --name-status origin/<trunk>"),
        ),
    ]
    assert not problems, "\n".join(problems)


def test_the_command_scan_sees_planted_lines() -> None:
    planted = "\n".join(
        [
            "Prose that mentions (`git status`) inline and is not a command line.",
            "```bash",
            "git log --oneline origin/<trunk>..HEAD",
            "",
            "  git diff --name-status origin/<trunk> HEAD",
            "```",
            "git stash list",
            "```bash",
            "TRUNK=main git fetch",
            "```",
        ]
    )
    assert _fenced_lines(planted) == [
        "git log --oneline origin/<trunk>..HEAD",
        "git diff --name-status origin/<trunk> HEAD",
        "TRUNK=main git fetch",
    ]
    assert _git_lines(planted) == [
        "git log --oneline origin/<trunk>..HEAD",
        "git diff --name-status origin/<trunk> HEAD",
        "git stash list",
    ]
    problems = _surface_problems(planted)
    assert any("assignment-led" in problem for problem in problems), problems
    assert any("read different lines" in problem for problem in problems), problems
    assert any("fenced command lines" in problem for problem in problems), problems

    clean = (
        "```bash\n"
        + "\n".join(f"git log -{n}" for n in range(_COMMAND_LINES))
        + "\n```\n"
    )
    assert _surface_problems(clean) == [], "the control is not clean"
    with pytest.raises(AssertionError, match="placeholders"):
        _fill("git log <trunk>..<other>", {"trunk": "main"})
    with pytest.raises(AssertionError, match="expected 1"):
        _the_line(["git log -1", "git log -2"], "git log")


def _which_only(found: dict[str, str]) -> Callable[[str], str | None]:
    """A stand-in for `shutil.which` that knows only the programs in `found`."""

    def which(name: str) -> str | None:
        return found.get(name)

    return which


def test_a_missing_shell_fails_and_the_one_beside_git_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    git_home = tmp_path / "Git"
    bundled = git_home / "usr" / "bin" / "sh.exe"
    fake_git = git_home / "cmd" / "git.exe"
    for stand_in in (bundled, fake_git):
        stand_in.parent.mkdir(parents=True)
        stand_in.write_text("", encoding="utf-8")

    monkeypatch.setattr(shutil, "which", _which_only({"sh": "/opt/bin/sh"}))
    assert _shell() == "/opt/bin/sh", "a shell on PATH must be the one used"
    monkeypatch.setattr(shutil, "which", _which_only({"git": str(fake_git)}))
    assert Path(_shell()) == bundled.resolve(), "the shell beside git was not found"
    monkeypatch.setattr(shutil, "which", _which_only({}))
    with pytest.raises(AssertionError, match="no POSIX shell"):
        _shell()


# --- the sample counters ------------------------------------------------------------------


# --- the request ids ----------------------------------------------------------------------
