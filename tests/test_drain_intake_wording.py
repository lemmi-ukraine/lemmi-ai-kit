"""The checks of the drain intake wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_printed_commands_never_name_the_buffer`: the printed commands never name the buffer
* `test_the_guard_lets_every_printed_read_form_through`: the guard lets every printed read form through
* `test_the_printed_commands_find_the_stash_and_the_branch_and_count_their_entries`: the printed commands find the stash and the branch and count their entries
"""

import importlib.util
import re
import shlex
import subprocess
from collections.abc import Callable
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "learning-consolidator"
_REFERENCE = _SKILL_DIR / "references" / "consolidation-actions.md"
_GUARD = _REPO_ROOT / "plugins" / "core" / "hooks" / "gate_learnings_drain.py"


_HEADING = re.compile(r"^(#{1,6})\s+\S")

_REFERENCE_NAME = "learning-consolidator references/consolidation-actions.md"

_COPIES_HEADING = "## Buffer Copies and Parked Lessons"


# --- slicers over a string -----------------------------------------------------------------


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced block
    is a comment of the code it holds, not a heading. A missing heading fails with the heading
    named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


# --- what the new text must say ------------------------------------------------------------


# --- one check per place the rows name; each takes a whole file's text ----------------------


def _copies_section(reference: str) -> str:
    return _section(reference, _COPIES_HEADING, _REFERENCE_NAME)


# --- the printed commands ------------------------------------------------------------------

_PLACEHOLDERS = ("<trunk>", "<ref>", "<path>", "<scratch file>")

_VALUES = {
    "<trunk>": "main",
    "<ref>": "stash@{0}",
    "<path>": ".ai/learnings.md",
    "<scratch file>": "scratch-copy.txt",
}


def _printed_commands(section: str) -> list[str]:
    """The non-blank, non-comment lines of the fenced blocks of a section."""
    commands: list[str] = []
    in_fence = False
    for line in section.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
        elif in_fence and line.strip() and not line.strip().startswith("#"):
            commands.append(line.strip())
    return commands


def _substituted(command: str, values: dict[str, str]) -> str:
    for placeholder, value in values.items():
        command = command.replace(placeholder, value)
    return command


# --- the tests -----------------------------------------------------------------------------


def test_the_printed_commands_never_name_the_buffer() -> None:
    section = _copies_section(_text(_REFERENCE))
    commands = _printed_commands(section)
    assert commands, "the section prints no command"
    for command in commands:
        assert "learnings.md" not in command, (
            f"a printed line names the buffer: {command}"
        )
    assert ":.ai/learnings.md" not in section
    assert "cp .ai/learnings.md" not in section
    assert [c for c in commands if re.match(r"[A-Za-z_]\w*=", c)] == []
    # The placeholders are the whole vocabulary: a stray one is a command nobody can run.
    used = {p for command in commands for p in re.findall(r"<[^>]+>", command)}
    assert used <= set(_PLACEHOLDERS), (
        f"unknown placeholders: {used - set(_PLACEHOLDERS)}"
    )


@cache
def _guard() -> ModuleType:
    """The guard, loaded once from its file (the hook is a script, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "gate_learnings_drain_for_intake", _GUARD
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shape(command: str, tool: str) -> str | None:
    judge = cast(Callable[[str, str], str | None], _guard()._shell_shape)  # pyright: ignore[reportPrivateUsage]
    return judge(command, tool)


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_the_guard_lets_every_printed_read_form_through(tool: str) -> None:
    commands = [
        _substituted(command, _VALUES)
        for command in _printed_commands(_copies_section(_text(_REFERENCE)))
    ]
    # The judge is shown to see: it flags a removal, a redirect into the buffer and an
    # in-place edit, so a None for the read forms below means it looked and found no rewrite.
    for positive in (
        "rm .ai/learnings.md",
        "git show 'stash@{0}:.ai/learnings.md' > .ai/learnings.md",
        "sed -i '/^### /d' .ai/learnings.md",
    ):
        assert _shape(positive, tool) is not None, f"the judge missed {positive!r}"
    assert any(".ai/learnings.md" in command for command in commands), (
        "no printed form names the buffer once filled in, so the judge has nothing to judge"
    )
    for command in commands:
        assert _shape(command, tool) is None, f"the guard would block {command!r}"


# --- the positive control: a repository with one stash and one branch ahead -----------------

_TIMEOUT_SECONDS = 60


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
    return done.stdout


def _entry(day: str, title: str) -> str:
    return f"### [{day}] {title}\n- **Finding:** a finding\n- **Impact:** an impact\n\n"


def _entry_headings(buffer: str) -> list[str]:
    return [line for line in buffer.split("\n") if line.startswith("### ")]


def _only_in_copy(buffer: str, copy: str) -> list[str]:
    """The entry headings a copy holds and the checked-out buffer does not."""
    have = set(_entry_headings(buffer))
    return [heading for heading in _entry_headings(copy) if heading not in have]


def _make_repo(parent: Path) -> tuple[Path, str]:
    """A trunk with a two-entry buffer, a branch ahead of it with a third entry, and a stash on
    the trunk that holds a different third entry. Returns the repository and the trunk's buffer."""
    root = parent / "project"
    (root / ".ai").mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "core.autocrlf", "false")
    buffer = root / ".ai" / "learnings.md"
    trunk = _entry("2026-01-01", "Entry A") + _entry("2026-01-02", "Entry B")
    buffer.write_text(trunk, encoding="utf-8", newline="\n")
    _git(root, "add", "--", ".ai")
    _git(root, "commit", "-q", "-m", "a buffer of two entries")
    _git(root, "checkout", "-q", "-b", "side")
    buffer.write_text(
        trunk + _entry("2026-01-03", "Entry C"), encoding="utf-8", newline="\n"
    )
    _git(root, "commit", "-q", "-am", "a third entry on a branch")
    _git(root, "checkout", "-q", "main")
    buffer.write_text(
        trunk + _entry("2026-01-04", "Entry D"), encoding="utf-8", newline="\n"
    )
    _git(root, "stash", "push", "-q")
    assert buffer.read_text(encoding="utf-8") == trunk
    return root, trunk


def _run_printed(command: str, root: Path, values: dict[str, str]) -> str:
    """Run one printed line as written, a `>` redirect included, without a shell."""
    tokens = shlex.split(_substituted(command, values), comments=True)
    target = None
    if ">" in tokens:
        target = tokens[tokens.index(">") + 1]
        tokens = tokens[: tokens.index(">")]
    done = subprocess.run(
        tokens,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert done.returncode == 0, f"{command!r} failed: {done.stderr}"
    if target is not None:
        (root / target).write_text(done.stdout, encoding="utf-8", newline="\n")
    return done.stdout


def test_the_printed_commands_find_the_stash_and_the_branch_and_count_their_entries(
    tmp_path: Path,
) -> None:
    root, trunk = _make_repo(tmp_path)
    commands = _printed_commands(_copies_section(_text(_REFERENCE)))
    assert len(commands) == 3
    stash_list, branches, read_copy = commands

    listed = _run_printed(stash_list, root, _VALUES)
    assert len(listed.strip().split("\n")) == 1 and listed.startswith("stash@{0}:"), (
        listed
    )
    assert _run_printed(branches, root, _VALUES).strip() == "side"

    _run_printed(read_copy, root, _VALUES)
    from_stash = (root / "scratch-copy.txt").read_text(encoding="utf-8")
    assert len(_entry_headings(from_stash)) == 3
    assert _only_in_copy(trunk, from_stash) == ["### [2026-01-04] Entry D"]

    _run_printed(read_copy, root, {**_VALUES, "<ref>": "side"})
    from_branch = (root / "scratch-copy.txt").read_text(encoding="utf-8")
    assert len(_entry_headings(from_branch)) == 3
    assert _only_in_copy(trunk, from_branch) == ["### [2026-01-03] Entry C"]
    # Neither copy is the checked-out buffer, which the commands never touched.
    assert (root / ".ai" / "learnings.md").read_text(encoding="utf-8") == trunk


# --- the instruments -----------------------------------------------------------------------
