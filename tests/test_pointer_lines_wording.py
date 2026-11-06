"""The checks of the pointer lines wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_log_analysis_pointer_lists_one_kind_per_example`: the log analysis pointer lists one kind per example
* `test_the_post_task_review_pointer_counts_both_groups_of_cases`: the post task review pointer counts both groups of cases
* `test_every_count_of_the_dimensions_is_the_number_the_reference_holds`: every count of the dimensions is the number the reference holds
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CORE = "plugins/core/skills"

_ANALYZE_LOGS = f"{_CORE}/analyze-logs/SKILL.md"
_ANALYSIS_EXAMPLES = f"{_CORE}/analyze-logs/references/analysis-examples.md"
_POST_TASK_REVIEW = f"{_CORE}/post-task-review/SKILL.md"
_CLAIM_BOUNDARIES = f"{_CORE}/post-task-review/references/claim-boundaries.md"
_PLAN_CRITIC = f"{_CORE}/plan-critic/SKILL.md"
_REVIEW_DIMENSIONS = f"{_CORE}/plan-critic/references/review-dimensions.md"


_NUMBER_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
)
_COUNT_BEFORE_DIMENSIONS = re.compile(
    rf"\b({'|'.join(_NUMBER_WORDS[1:])})\s+dimensions\b", re.IGNORECASE
)


def _raw(relative: str) -> str:
    return (_ROOT / relative).read_text(encoding="utf-8")


def _words(relative: str) -> str:
    return " ".join(_raw(relative).split()).lower()


def _count(text: str, pattern: str, what: str) -> int:
    """How many lines of `text` match `pattern`. None is an error: a renamed heading must fail."""
    found = len(re.findall(pattern, text, re.MULTILINE))
    assert found > 0, f"no {what} found by {pattern!r}"
    return found


def _word(count: int) -> str:
    assert 0 < count < len(_NUMBER_WORDS), f"no number word for {count}"
    return _NUMBER_WORDS[count]


def _section_lines(text: str, heading_containing: str) -> list[str]:
    """The lines under the first `##` heading that contains a phrase, up to the next `##` heading."""
    inside = False
    lines: list[str] = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if inside:
                break
            inside = heading_containing in line.lower()
        elif inside:
            lines.append(line)
    assert inside, f"no '##' heading that contains {heading_containing!r}"
    return lines


def _section_bullets(text: str, heading_containing: str) -> list[str]:
    """The top-level bullets under the first `##` heading that contains a phrase, up to the next."""
    return [
        line
        for line in _section_lines(text, heading_containing)
        if line.startswith("- ")
    ]


def _pointer_bullets(text: str, link: str) -> list[str]:
    """The bullet lines that follow the one line that links `link`."""
    lines = text.split("\n")
    pointers = [i for i, line in enumerate(lines) if link in line]
    assert len(pointers) == 1, (
        f"{len(pointers)} lines link {link!r}, expected one pointer line"
    )
    bullets: list[str] = []
    for line in lines[pointers[0] + 1 :]:
        if not line.startswith("- "):
            break
        bullets.append(line)
    return bullets


def test_the_log_analysis_pointer_lists_one_kind_per_example() -> None:
    examples = _count(
        _raw(_ANALYSIS_EXAMPLES), r"^### Example \d+:", "example headings"
    )
    kinds = _pointer_bullets(_raw(_ANALYZE_LOGS), "references/analysis-examples.md")
    assert len(kinds) == examples, (
        f"the reference holds {examples} examples and the pointer lists {len(kinds)} kinds: "
        f"{kinds}"
    )


def test_the_post_task_review_pointer_counts_both_groups_of_cases() -> None:
    reference = _raw(_CLAIM_BOUNDARIES)
    measured = _count(reference, r"^## \d+\. ", "numbered case headings")
    shorter = len(_section_bullets(reference, "shorter cases"))
    assert shorter > 0, "the closing section of shorter cases holds no bullet"
    pointer = _words(_POST_TASK_REVIEW)
    for count, kind in ((measured, "measured"), (shorter, "shorter")):
        phrase = f"{_word(count)} {kind} cases"
        assert phrase in pointer, (
            f"the reference holds {count} {kind} cases: no {phrase!r}"
        )


def test_every_count_of_the_dimensions_is_the_number_the_reference_holds() -> None:
    held = _count(_raw(_REVIEW_DIMENSIONS), r"^## Dimension \d+ ", "dimension headings")
    stated = [m.lower() for m in _COUNT_BEFORE_DIMENSIONS.findall(_raw(_PLAN_CRITIC))]
    heading = re.search(
        r"^### Step 2 \S+ Run the (\w+) Dimensions$", _raw(_PLAN_CRITIC), re.MULTILINE
    )
    assert heading is not None, "plan-critic lost its Step 2 heading"
    assert stated, "plan-critic states no count of dimensions"
    wrong = [word for word in stated if word != _word(held)]
    assert not wrong, (
        f"the reference holds {held} dimensions; plan-critic says {stated}"
    )
    assert heading.group(1).lower() == _word(held), (
        f"the Step 2 heading says {heading.group(1)}, the reference holds {held}"
    )
