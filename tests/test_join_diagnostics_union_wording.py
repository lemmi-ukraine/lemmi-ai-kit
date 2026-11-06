"""The checks of the join diagnostics union wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_stated_number_of_ways_is_the_number_of_bullets`: Control, green on the old text too: the paragraph is not a fifth bullet, so the intro's word and the bullets it counts still agree.
"""

import re
from pathlib import Path

_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "metric-validity-check"
    / "references"
    / "join-diagnostics.md"
)
_COUNTING = "## Counting recorded commands"
_FENCE = "```"
_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}

_STATED_WAYS = re.compile(r"goes wrong in (\w+) ways")


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


def _fold(text: str) -> str:
    return " ".join(text.replace("**", "").split()).lower()


def _raw_section() -> str:
    return _section(_REFERENCE.read_text(encoding="utf-8"), _COUNTING)


def _bullets(section: str) -> list[str]:
    return [
        line
        for _, line in _outside_fences(section.splitlines())
        if line.startswith("- **")
    ]


def test_the_stated_number_of_ways_is_the_number_of_bullets() -> None:
    """Control, green on the old text too: the paragraph is not a fifth bullet, so the intro's
    word and the bullets it counts still agree."""
    section = _raw_section()
    stated = _STATED_WAYS.findall(_fold(section))
    assert len(stated) == 1, (
        f"{len(stated)} statements of the number of ways, expected 1"
    )
    assert _NUMBER_WORDS[stated[0]] == len(_bullets(section)), (
        stated,
        _bullets(section),
    )
