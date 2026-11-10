"""The Step 0 command `task-learnings` prints measures a whole task when its hand-off part is filled.

At the close of a task, Step 0 runs the extractor once. The command it prints carries an optional
part in square brackets, the hand-off the closing session received, so that one digest covers
every session that note lists, together with the session that runs the command. Left out, the
command is the one-session measurement it always was, and
`tests/test_session_retrospective_text.py` already runs that form from a fake project root.

This test reads the command out of the skill's Step 0 section, fills its placeholders, keeps the
optional hand-off part, and runs it from the root of a fake project under a fake home. The
project's session folder holds a chain of three sessions (the hand-off lists the first two, the
third runs the command) and one session of another task that ran beside them. The run must exit
0 and write one digest that holds a measured section for every session of the chain and none for
the other task's session.

WHAT KEEPS IT HONEST. The command is read from the skill, never retyped here, so what runs is
what the skill prints. The filler refuses a placeholder it has no value for, so a renamed
placeholder fails here instead of running with a literal `<...>` in it. The other task's session
is the negative control that tells a measurement of the chain from one of the whole folder. The
digest's header lists every id the run was given, measured or not, so it cannot show that a
session was read: only a session's own section can, and the test counts those. A run that
measures nothing leaves the header and no section, so it fails here (checked by planting that
change in the extractor). The section reader, the command reader and the filler are each fired
at planted text.
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
_SKILLS = _REPO_ROOT / "plugins" / "core" / "skills"
_TASK_LEARNINGS = _SKILLS / "task-learnings" / "SKILL.md"
_EXTRACTOR = _SKILLS / "session-retrospective" / "scripts" / "extract_sessions.py"
_STEP_0 = "### Step 0"
_HEADING = re.compile(r"^(#{1,6})\s")
_OPTIONAL = re.compile(r"\[([^\[\]]*)\]")
_VARIABLE = re.compile(r"\$\{([A-Za-z_]+)\}")
_PLACEHOLDER = re.compile(r"<([^<>]+)>")
_HAND_OFF = "HAND-OFF"

# Made-up ids in the shape a session id has. None is a real session: the kit is public.
_FIRST = "e0000001-0000-0000-0000-000000000001"
# The second session wrote the hand-off the closing session received.
_SECOND = "e0000002-0000-0000-0000-000000000002"
# The closing session runs the printed command.
_CLOSING = "e0000003-0000-0000-0000-000000000003"
# A session of another task, run beside the chain in the same session folder.
_OTHER_TASK = "f0000001-0000-0000-0000-000000000001"
_CHAIN = (_FIRST, _SECOND, _CLOSING)
_NOTE_NAME = "2026-11-10-example-task.md"


def _section(text: str, heading: str) -> str:
    """The lines from the heading that starts with `heading` to the next heading of the same or
    a higher level. A `#` line inside a fenced block is not a heading. A missing heading fails
    with its name, so a renamed step is a loud failure and never an empty section."""
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


def _step_0_command(text: str) -> str:
    """The one fenced extractor command of the Step 0 section, continuation lines joined."""
    commands = [
        element.text
        for element in _printed_elements(_section(text, _STEP_0))
        if element.fenced and "extract_sessions.py" in element.text
    ]
    assert len(commands) == 1, (
        f"expected one printed extractor command under {_STEP_0!r}, found {len(commands)}"
    )
    return commands[0]


def _filled(command: str, values: dict[str, str]) -> str:
    """The command with the optional part that names the hand-off kept, any other optional part
    dropped, and every `${VAR}` and `<NAME>` filled. A placeholder with no value fails."""

    def optional(match: re.Match[str]) -> str:
        return f" {match[1]} " if f"<{_HAND_OFF}>" in match[1] else " "

    def fill(match: re.Match[str]) -> str:
        assert match[1] in values, f"no stand-in for the placeholder {match[0]}"
        return values[match[1]]

    command = _OPTIONAL.sub(optional, command)
    command = _VARIABLE.sub(fill, command)
    return _PLACEHOLDER.sub(fill, command)


@pytest.fixture
def short_tmp() -> Iterator[Path]:
    """A short folder: the session store names a folder after the project's whole path, so a
    path in this test is about twice as long as the folder it hangs from, and under a deep
    `tmp_path` it passes the Windows limit."""
    folder = Path(tempfile.mkdtemp(prefix="k")).resolve()
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


class _Store(NamedTuple):
    home: Path
    project: Path
    plugin_root: Path


def _store(root: Path) -> _Store:
    """A fake home holding the project's session folder, one transcript per session, and an
    installed copy of the extractor. The folder is named by the extractor's own helper."""
    extractor = _load(_EXTRACTOR, "extract_sessions_task_command")
    home = root / "home"
    project = root / "work" / "proj"
    project.mkdir(parents=True)
    encoded = str(extractor._encode_repo_path(project))  # pyright: ignore[reportPrivateUsage]
    folder = home / ".claude" / "projects" / encoded
    folder.mkdir(parents=True)
    for day, session in enumerate((*_CHAIN, _OTHER_TASK), 10):
        row = {
            "type": "user",
            "timestamp": f"2026-11-{day}T09:00:00Z",
            "gitBranch": "main",
            "message": {"content": [{"type": "text", "text": f"work for day {day}"}]},
        }
        (folder / f"{session}.jsonl").write_text(
            json.dumps(row) + "\n", encoding="utf-8", newline="\n"
        )
    plugin_root = home / ".claude" / "plugins" / "cache" / "kit"
    scripts = plugin_root / "skills" / "session-retrospective" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copyfile(_EXTRACTOR, scripts / "extract_sessions.py")
    return _Store(home, project, plugin_root)


def _hand_off(project: Path) -> Path:
    """The note the closing session received: it lists the two sessions before it."""
    note = project / ".ai" / "handoffs" / _NOTE_NAME
    note.parent.mkdir(parents=True)
    note.write_text(
        "\n".join(
            [
                "<!-- handoff-contract: v3 -->",
                "# Hand-off: example task",
                "",
                "Task: example-task",
                f"Sessions: {_FIRST}, {_SECOND}",
                f"Written: 2026-11-11 17:00 by {_SECOND}",
                "Lessons: none",
                "Delegation: none, because judgment is the work",
                "Safe to close: yes",
                "",
                "## Continue",
                "",
                "Close the task.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    return note


def _run(command: str, store: _Store) -> subprocess.CompletedProcess[str]:
    """The filled command, run with this interpreter from the project root under the fake
    home."""
    words = shlex.split(command)
    assert words[0] == "python" and words[1].endswith("extract_sessions.py"), words[:2]
    return subprocess.run(
        [sys.executable, "-B", *words[1:]],
        cwd=store.project,
        env={**os.environ, "HOME": str(store.home), "USERPROFILE": str(store.home)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )


def test_the_printed_step_0_command_measures_the_chain_its_hand_off_lists(
    short_tmp: Path,
) -> None:
    store = _store(short_tmp)
    note = _hand_off(store.project)
    command = _filled(
        _step_0_command(_TASK_LEARNINGS.read_text(encoding="utf-8")),
        {
            "CLAUDE_PLUGIN_ROOT": store.plugin_root.as_posix(),
            "SESSION-ID": _CLOSING,
            _HAND_OFF: note.relative_to(store.project).as_posix(),
        },
    )

    run = _run(command, store)

    assert run.returncode == 0, (command, run.returncode, run.stderr)
    digests = sorted(store.project.rglob("interaction-digest.md"))
    assert len(digests) == 1, f"expected one digest under the project, found {digests}"
    digest = digests[0].read_text(encoding="utf-8")
    sections = sorted(re.findall(r"^## Session (\S+)$", digest, re.MULTILINE))
    expected = sorted(session[:8] for session in _CHAIN)
    assert sections == expected, (
        f"the digest has a measured section for {sections}, not for each session of the chain "
        f"{expected}. The command run was: {command}"
    )
    assert _OTHER_TASK not in digest, "the digest names a session of another task"


# --- the instruments ----------------------------------------------------------------------


def test_the_filler_keeps_the_hand_off_part_and_refuses_unknowns() -> None:
    """Of two optional parts, only the one naming the hand-off is kept; a placeholder with no
    stand-in fails instead of reaching the shell as literal text."""
    values = {"CLAUDE_PLUGIN_ROOT": "ROOT", "SESSION-ID": "S1", _HAND_OFF: "note.md"}
    printed = (
        'python "${CLAUDE_PLUGIN_ROOT}/x/extract_sessions.py" out/<SESSION-ID>/ '
        "--session <SESSION-ID> [--sessions-from <HAND-OFF>] [--since <DATE>] --digest"
    )
    assert shlex.split(_filled(printed, values)) == [
        "python",
        "ROOT/x/extract_sessions.py",
        "out/S1/",
        "--session",
        "S1",
        "--sessions-from",
        "note.md",
        "--digest",
    ]
    with pytest.raises(AssertionError, match="no stand-in for the placeholder <TASK>"):
        _filled("python extract_sessions.py --task <TASK>", values)


_ONE = "```bash\npython a/extract_sessions.py out/\n```"


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("### Step 0: x\n\nNo command here.\n\n### Step 1: y\n" + _ONE + "\n", 0),
        ("### Step 0: x\n\n" + _ONE + "\n\n" + _ONE + "\n", 2),
    ],
    ids=["none in the section, one after it", "two in the section"],
)
def test_the_command_reader_fails_unless_step_0_prints_exactly_one(
    text: str, count: int
) -> None:
    with pytest.raises(AssertionError, match=f"found {count}"):
        _step_0_command(text)


def test_the_section_reader_stops_at_the_next_step_and_fails_on_a_missing_one() -> None:
    planted = "\n".join(
        [
            "### Step 0: x",
            "```bash",
            "# a comment line inside a fence is not a heading",
            "python a/extract_sessions.py out/",
            "```",
            "### Step 1: y",
            "```bash",
            "python b/extract_sessions.py out/",
            "```",
        ]
    )
    assert _step_0_command(planted) == "python a/extract_sessions.py out/"
    with pytest.raises(AssertionError, match="no heading starts with"):
        _section(planted, "### Step 9")
