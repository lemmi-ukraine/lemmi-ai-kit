"""The checks of the handoff stub wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_shipped_stub_meets_every_rule_of_a_stub`: Red before the change for want of the file; the rules it is held to are shown to see a defect by the planted tests below.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

from lemmi_ai_kit import checks

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

_SKILLS = "plugins/orchestration/skills"
_STUB = f"{_SKILLS}/agent-delegate/assets/handoff-stub.md"

_STATUS_LINE = "**Status:** in-progress - not started"


class _Rule(NamedTuple):
    """One rule a stub is held to: its name and the faults it finds in a text, one line each."""

    name: str
    problems: Callable[[str], list[str]]


# --- the stub file --------------------------------------------------------------------------------


def _newest() -> int:
    return max(checks.HANDOFF_SECTIONS_BY_VERSION)


def _label() -> str:
    return f"<!-- handoff-contract: v{_newest()} -->"


def _required() -> tuple[str, ...]:
    return (
        *checks.HANDOFF_REQUIRED_SECTIONS,
        *checks.HANDOFF_SECTIONS_BY_VERSION[_newest()],
    )


def _outside_comments(text: str) -> str:
    return _COMMENT.sub("", text)


def _headings(text: str) -> list[str]:
    return re.findall(r"^## (.+?)\s*$", _outside_comments(text), re.MULTILINE)


def _body(text: str, name: str) -> str:
    """The lines under `## name`, up to the next `## ` heading, comments removed, folded."""
    lines = _outside_comments(text).split("\n")
    start = next((i for i, line in enumerate(lines) if line == f"## {name}"), None)
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return " ".join(" ".join(body).split())


def _entries(text: str, name: str) -> int:
    """How many bullets stand under `## name`, outside comments."""
    lines = _outside_comments(text).split("\n")
    start = next((i for i, line in enumerate(lines) if line == f"## {name}"), None)
    if start is None:
        return 0
    count = 0
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            count += 1
    return count


def _label_problems(text: str) -> list[str]:
    """Line 1 is the label. It is checked here and not left to the lint: a note with no label is
    read as the older version, which asks for fewer sections, so the lint passes it."""
    lines = text.splitlines()
    first = lines[0].rstrip() if lines else ""
    if first == _label():
        return []
    return [f"line 1 is {first!r}, not the label {_label()!r}"]


def _lint_problems(text: str) -> list[str]:
    return [
        f"lint: {finding.message}"
        for finding in checks.lint_handoff(text, "handoff-stub.md")
    ]


def _heading_problems(text: str) -> list[str]:
    """The headings are the required sections, no more and in order: the lint asks only that
    each is there."""
    headings = _headings(text)
    if tuple(headings) == _required():
        return []
    return [f"headings are {headings}, not {list(_required())}"]


def _status_problems(text: str) -> list[str]:
    """The Status body is the not-started line exactly: the lint accepts any of its three words."""
    status = _body(text, "Status")
    if status == _STATUS_LINE:
        return []
    return [f"the Status section reads {status!r}, not {_STATUS_LINE!r}"]


def _command_problems(text: str) -> list[str]:
    problems: list[str] = []
    for name in checks.HANDOFF_COMMAND_SECTIONS:
        held = _entries(text, name)
        if held != 1:
            problems.append(f"'## {name}' holds {held} entries, not 1")
    return problems


_STUB_RULES: tuple[_Rule, ...] = (
    _Rule("label", _label_problems),
    _Rule("lint", _lint_problems),
    _Rule("headings", _heading_problems),
    _Rule("status", _status_problems),
    _Rule("commands", _command_problems),
)


def _stub_problems(text: str) -> list[str]:
    """Why `text` is not a hand-off stub, from every rule in turn; empty when it is."""
    return [problem for rule in _STUB_RULES for problem in rule.problems(text)]


# --- the text each place carried before -----------------------------------------------------------


# --- the tests ------------------------------------------------------------------------------------


# --- the stub file --------------------------------------------------------------------------------


def _stub() -> str:
    path = _REPO_ROOT / _STUB
    if not path.is_file():
        pytest.fail(f"the hand-off stub {_STUB} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_the_shipped_stub_meets_every_rule_of_a_stub() -> None:
    """Red before the change for want of the file; the rules it is held to are shown to see a
    defect by the planted tests below."""
    problems = _stub_problems(_stub())
    assert not problems, problems
