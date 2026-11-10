"""The checks of the landing queue wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_command_names_the_script_and_exactly_its_flags`: The command runs the script that ships beside this file, with every flag its `check` takes and no other, so the reference and the script cannot drift apart unseen. A planted flag the script lacks is reported.
* `test_the_script_states_the_same_three_exit_codes`: The script's own docstring says what the reference's three exit bullets say.
* `test_the_links_resolve_and_the_section_they_name_exists`: the links resolve and the section they name exists
"""

import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "plugins" / "orchestration" / "skills" / "parallel-session-safety"
_FILE = _SKILL / "references" / "landing-queue.md"
_SCRIPT = _SKILL / "scripts" / "landing_gate.py"
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_FLAG = re.compile(r"(?<![\w-])--[a-z][a-z-]*")

_GATE_SECTION = "## The gate before every commit"


def _read(path: Path = _FILE) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
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
    return "\n".join(body)


def _fence(text: str, language: str) -> list[str]:
    """The lines of the first fenced block opened with ```language; empty when there is none."""
    lines = text.split("\n")
    opener = f"```{language}"
    for start, line in enumerate(lines):
        if line.strip() == opener:
            body: list[str] = []
            for inner in lines[start + 1 :]:
                if inner.strip().startswith("```"):
                    return body
                body.append(inner)
    return []


def _real_section(heading: str) -> str:
    section = _section(_read(), heading)
    assert section.strip(), f"{heading!r} is missing from landing-queue.md"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_command_names_the_script_and_exactly_its_flags() -> None:
    """The command runs the script that ships beside this file, with every flag its `check`
    takes and no other, so the reference and the script cannot drift apart unseen. A planted
    flag the script lacks is reported."""
    command = "\n".join(_fence(_real_section(_GATE_SECTION), "bash"))
    assert '"${CLAUDE_SKILL_DIR}/scripts/landing_gate.py" check ' in command, command
    assert _SCRIPT.is_file(), f"{_SCRIPT} is not a file"
    done = subprocess.run(
        [sys.executable, "-B", "-I", str(_SCRIPT), "check", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    offered = set(_FLAG.findall(done.stdout)) - {"--help"}
    used = set(_FLAG.findall(command))
    assert len(offered) == 6 and used == offered, (sorted(used), sorted(offered))
    planted = command.replace("--paths", "--paths <paths file> --message", 1)
    assert set(_FLAG.findall(planted)) - offered == {"--message"}


def test_the_script_states_the_same_three_exit_codes() -> None:
    """The script's own docstring says what the reference's three exit bullets say."""
    text = " ".join(_read(_SCRIPT).split())
    for said in (
        "Exit 0 only when every check measured and passed",
        "Exit 1 when a check failed",
        "Exit 2 when any check could not measure",
        "cannot-measure is never a pass",
    ):
        assert said in text, said


def test_the_links_resolve_and_the_section_they_name_exists() -> None:
    text = _read()
    targets = [target.split("#")[0] for target in _LINK.findall(text)]
    assert targets == ["shared-index-protocol.md", "shared-index-protocol.md"], targets
    protocol = _FILE.parent / "shared-index-protocol.md"
    assert protocol.is_file()
    assert any(line.startswith("### 12l.") for line in _read(protocol).split("\n"))


# --- the checks can fail -----------------------------------------------------------------------


# --- the finders -------------------------------------------------------------------------------


# --- hygiene of the six added files ------------------------------------------------------------
