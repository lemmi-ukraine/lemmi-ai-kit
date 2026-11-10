"""The checks of the orchestrate operator questions wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_prose_count_equals_the_number_of_bullets`: the prose count equals the number of bullets
* `test_a_planted_fourth_bullet_or_a_wrong_number_word_is_reported`: a planted fourth bullet or a wrong number word is reported
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL = (
    _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate" / "SKILL.md"
)

_ITEM_LEAD = "9. **The close block"
_PROSE_COUNT = re.compile(r"\bPlus (\w+) operator-interface rules\b")
_NEXT_ITEM = re.compile(r"^\d+\. ")
_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _item_9(text: str) -> str:
    """The line that starts item 9 and every line after it up to the next top-level item. Fails
    loudly when no line, or more than one, starts it."""
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(_ITEM_LEAD)]
    assert len(starts) == 1, f"{_ITEM_LEAD!r} starts {len(starts)} lines, not 1"
    item = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if _NEXT_ITEM.match(line):
            break
        item.append(line)
    return "\n".join(item)


def _operator_region(item: str) -> str:
    """The prose line that says how many operator-interface rules there are, and everything
    after it in the item. Fails loudly when no line, or more than one, says it."""
    lines = item.split("\n")
    starts = [index for index, line in enumerate(lines) if _PROSE_COUNT.search(line)]
    assert len(starts) == 1, (
        f"{len(starts)} lines say how many operator-interface rules there are, not 1"
    )
    return "\n".join(lines[starts[0] :])


def _bullets(region: str) -> list[str]:
    """The bullets of a region, each as one line of folded whitespace. A bullet starts at three
    spaces and a dash and runs over the more deeply indented lines under it; a quoted list item
    (`>` first) and a wrapped line are not bullets."""
    bullets: list[str] = []
    for line in region.split("\n"):
        if line.startswith("   - "):
            bullets.append(line.strip())
        elif bullets and line.startswith("     ") and line.strip():
            bullets[-1] = f"{bullets[-1]} {line.strip()}"
    return [" ".join(bullet.split()) for bullet in bullets]


def _count_problem(region: str) -> str | None:
    """Why the number word in the prose disagrees with the bullets under it; None when they
    agree. Fails loudly when the word is not one the table knows."""
    found = _PROSE_COUNT.search(region)
    assert found is not None, "the region carries no prose count"
    word = found[1].lower()
    assert word in _NUMBER_WORDS, f"the prose count {word!r} is not in the number table"
    held = len(_bullets(region))
    if _NUMBER_WORDS[word] == held:
        return None
    return f"the prose says {word} rules and the region holds {held} bullets"


def _real_region() -> str:
    return _operator_region(_item_9(_read(_SKILL)))


def test_the_prose_count_equals_the_number_of_bullets() -> None:
    assert _count_problem(_real_region()) is None


def test_a_planted_fourth_bullet_or_a_wrong_number_word_is_reported() -> None:
    region = _real_region()
    assert _count_problem(region) is None
    fourth = f"{region}\n   - **A fourth rule.** Which the prose does not count.\n"
    assert _count_problem(fourth) == (
        "the prose says three rules and the region holds 4 bullets"
    )
    assert _count_problem(region.replace("Plus three", "Plus four")) == (
        "the prose says four rules and the region holds 3 bullets"
    )
    with pytest.raises(AssertionError, match="number table"):
        _count_problem(region.replace("Plus three", "Plus several"))
