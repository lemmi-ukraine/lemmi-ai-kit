"""The checks of the stacked pr planner portability wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_class_counters_are_the_classes_of_the_table`: the class counters are the classes of the table
"""

import re
from pathlib import Path

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "stacked-pr-planner"
    / "SKILL.md"
)
_WHERE = "stacked-pr-planner SKILL.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_COUNTER = re.compile(r"^([A-Z]{3,})=\$\(", re.MULTILINE)

# The classes of the risk-class table as they stood before the change.
_CLASSES: frozenset[str] = frozenset({"MIGRATION", "BACKEND", "TOOLING", "DOCS"})


def _text() -> str:
    return _SKILL.read_text(encoding="utf-8")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the code it holds, not a heading. A missing heading fails with the
    heading named, so a renamed section is a loud failure and never an empty match.
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


def _step(heading: str) -> str:
    return _section(_text(), heading, _WHERE)


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


def _classifier_block(section: str, where: str) -> list[str]:
    """The lines of the one fenced block of `section` that holds the class counters."""
    holding = [
        block
        for block in _fenced_blocks(section)
        if any("MIGRATION=$(" in line for line in block)
    ]
    if len(holding) != 1:
        raise AssertionError(
            f"{where}: {len(holding)} fenced blocks hold the class counters, expected 1"
        )
    return holding[0]


def _counter_names(block: list[str]) -> set[str]:
    return set(_COUNTER.findall("\n".join(block)))


# --- the change ---------------------------------------------------------------------------


def test_the_class_counters_are_the_classes_of_the_table() -> None:
    block = _classifier_block(_step("## Step 6 "), _WHERE)
    assert _counter_names(block) == _CLASSES, (
        f"the sample classifier counts {sorted(_counter_names(block))}, the class table "
        f"lists {sorted(_CLASSES)}"
    )


# --- the instruments ----------------------------------------------------------------------
