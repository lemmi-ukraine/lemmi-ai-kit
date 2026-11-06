"""The checks of the session retrospective text tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_schema_invocation_prints_the_command_in_the_skill_dir_form`: The block used to print `\\ # comment` after the script, which breaks the continuation in a shell, and a path relative to a directory no reader is in.
* `test_the_printed_extractor_command_runs_from_the_project_root`: The command is read out of the skill text, filled and run with `sys.executable`.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from test_printed_commands import (
    _load,  # pyright: ignore[reportPrivateUsage]
    _printed_elements,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "session-retrospective"


# --- reading a section of a skill ------------------------------------------------------------

_TASK_LEARNINGS_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "task-learnings"
_RETRO = _SKILL_DIR / "SKILL.md"
_SCHEMA = _SKILL_DIR / "references" / "extractor-output-schema.md"
_EXTRACTOR = _SKILL_DIR / "scripts" / "extract_sessions.py"
_TASK_LEARNINGS = _TASK_LEARNINGS_DIR / "SKILL.md"
_HEADING = re.compile(r"^(#{1,6})\s")


def _section(text: str, heading: str) -> str:
    """The lines from the heading that starts with `heading` to the next heading of the same
    or a higher level. A `#` line inside a fenced block is not a heading."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in re.split(r"\r?\n", text):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    assert body, f"no heading starts with {heading!r}"
    return "\n".join(body)


# --- the session folder comes from the working directory -------------------------------------


def test_the_schema_invocation_prints_the_command_in_the_skill_dir_form() -> None:
    """The block used to print `\\  # comment` after the script, which breaks the
    continuation in a shell, and a path relative to a directory no reader is in."""
    section = _section(_SCHEMA.read_text(encoding="utf-8"), "## Invocation")
    commands = [
        e
        for e in _printed_elements(section)
        if e.fenced and "extract_sessions.py" in e.text
    ]
    assert commands, "the Invocation section prints no extractor command"
    first = commands[0].text
    assert first.startswith(
        'python "${CLAUDE_SKILL_DIR}/scripts/extract_sessions.py"'
    ), first


# --- each printed extractor command, taken out of the text, runs -----------------------------


@pytest.fixture
def short_tmp() -> Iterator[Path]:
    """A short folder: the session store names a folder after the project's whole path, so
    a path in these tests is about twice as long as the folder it hangs from, and under a
    deep `tmp_path` it passes the Windows limit."""
    folder = Path(tempfile.mkdtemp(prefix="k")).resolve()
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


class _Fake(NamedTuple):
    home: Path
    project: Path
    folder: Path
    session_id: str
    plugin_root: Path
    skill_dir: Path


_SESSION_ROW = {
    "type": "user",
    "timestamp": "2026-08-14T00:00:00Z",
    "gitBranch": "main",
    "message": {"content": [{"type": "text", "text": "please fix the build"}]},
}


def _fake(root: Path) -> _Fake:
    """A fake home holding one session folder for a fake project root and an installed copy
    of the extractor. The folder is named by the extractor's own helper, not retyped."""
    extractor = _load(_EXTRACTOR, "extract_sessions_printed_commands")
    home = root / "home"
    project = root / "work" / "proj"
    project.mkdir(parents=True)
    folder = home / ".claude" / "projects" / str(extractor._encode_repo_path(project))  # pyright: ignore[reportPrivateUsage]
    folder.mkdir(parents=True)
    session_id = "s0000001-0000-0000-0000-000000000000"
    (folder / f"{session_id}.jsonl").write_text(
        json.dumps(_SESSION_ROW) + "\n", encoding="utf-8", newline="\n"
    )
    plugin_root = home / ".claude" / "plugins" / "cache" / "kit"
    skill_dir = plugin_root / "skills" / "session-retrospective"
    (skill_dir / "scripts").mkdir(parents=True)
    shutil.copyfile(_EXTRACTOR, skill_dir / "scripts" / "extract_sessions.py")
    return _Fake(home, project, folder, session_id, plugin_root, skill_dir)


def _instantiate(command: str, fake: _Fake) -> str:
    """The printed command with each placeholder filled; one this test cannot fill fails it."""
    values = {
        "CLAUDE_SKILL_DIR": fake.skill_dir.as_posix(),
        "CLAUDE_PLUGIN_ROOT": fake.plugin_root.as_posix(),
        "SESSION-ID": fake.session_id,
    }

    def fill(match: re.Match[str]) -> str:
        assert match[1] in values, f"no stand-in for the placeholder {match[0]}"
        return values[match[1]]

    command = re.sub(r"\[[^\[\]]*\]", " ", command)
    command = re.sub(r"\$\{([A-Za-z_]+)\}", fill, command)
    return re.sub(r"<([^<>]+)>", fill, command)


def _printed_extractor_command(path: Path, heading: str) -> str:
    elements = [
        e
        for e in _printed_elements(_section(path.read_text(encoding="utf-8"), heading))
        if e.fenced and "extract_sessions.py" in e.text
    ]
    assert len(elements) == 1, (
        f"expected one printed extractor command under {heading!r}, found {len(elements)}"
    )
    return elements[0].text


def _run_printed(
    command: str, fake: _Fake, cwd: Path, first_argument: Path | None = None
) -> subprocess.CompletedProcess[str]:
    words = shlex.split(_instantiate(command, fake))
    assert words[0] == "python" and words[1].endswith("extract_sessions.py"), words[:2]
    argv = [sys.executable, "-B", words[1]]
    if first_argument is not None:
        argv.append(str(first_argument))
    argv += words[2:]
    return subprocess.run(
        argv,
        cwd=cwd,
        env={**os.environ, "HOME": str(fake.home), "USERPROFILE": str(fake.home)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )


def _named_session_dir(stderr: str) -> Path:
    named = [
        line for line in stderr.splitlines() if line.startswith("Using session dir:")
    ]
    assert len(named) == 1, f"expected one `Using session dir:` line in:\n{stderr}"
    return Path(named[0].split(":", 1)[1].strip())


_PRINTED_EXTRACTOR_COMMANDS = {
    "retrospective-phase-1": (_RETRO, "### Phase 1"),
    "task-learnings-step-0": (_TASK_LEARNINGS, "### Step 0"),
}


@pytest.mark.parametrize("which", sorted(_PRINTED_EXTRACTOR_COMMANDS))
def test_the_printed_extractor_command_runs_from_the_project_root(
    which: str, short_tmp: Path
) -> None:
    """The command is read out of the skill text, filled and run with `sys.executable`.

    What this proves: the command as printed, with no session folder given, runs from the
    project root under a fake home and names that project's folder; from below the root it
    exits 1 and asks for the first argument; and the first argument is the way out. What it
    cannot prove: that a sentence around the command is true. The two printed commands
    already left the folder out before the text was corrected, so this test is green on the
    old wording too; the stale-sentence scans above carry that red, and the check that this
    test can fail is a printed command given an argument that no longer fits.
    """
    path, heading = _PRINTED_EXTRACTOR_COMMANDS[which]
    command = _printed_extractor_command(path, heading)
    fake = _fake(short_tmp)

    at_the_root = _run_printed(command, fake, fake.project)
    assert at_the_root.returncode == 0, at_the_root.stderr
    assert _named_session_dir(at_the_root.stderr).samefile(fake.folder)

    below = fake.project / "src"
    below.mkdir()
    refused = _run_printed(command, fake, below)
    assert refused.returncode == 1, (refused.returncode, refused.stderr)
    assert "first argument" in refused.stderr
    assert not (below / ".ai").exists(), "nothing is written when the run is refused"

    given = _run_printed(command, fake, below, first_argument=fake.folder)
    assert given.returncode == 0, given.stderr
    assert _named_session_dir(given.stderr).samefile(fake.folder)


# --- the proposals seam, and the gate that takes it -------------------------------------------


# --- the hypothesis validator runs in the consolidator's Phase 2 AND its Phase 6.5 -----------


# --- the gate reference says what the flag drops, and what it keeps ---------------------------


# --- a "proceed" is read against the message above it -----------------------------------------
