"""The checks of the instrument lessons wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_claims_reference_keeps_the_counts_its_pointer_states`: Four numbered headings and four shorter-case bullets: what the SKILL.md pointer says and `test_pointer_lines_wording.py` derives. Unlike the rows above, it holds on the old text too.
"""

import re
from pathlib import Path

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"

_CLAIM_BOUNDARIES = "post-task-review/references/claim-boundaries.md"

_NUMBERED = re.compile(r"^## (\d+)\. ")


def _read(reference: str) -> str:
    """The reference as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_SKILLS / reference).read_text(encoding="utf-8").replace("\r\n", "\n")


def _headings(text: str) -> list[str]:
    """The `##` heading lines in order, skipping any `#` line inside a fenced block."""
    found: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            found.append(line)
    return found


def _numbers(headings: list[str]) -> list[int]:
    """The numbers of the numbered headings, in order."""
    return [int(m[1]) for heading in headings if (m := _NUMBERED.match(heading))]


def _shorter_case_bullets(text: str) -> list[str]:
    """The top-level bullets under the first `##` heading that holds "shorter cases", up to the
    next `##` heading: the same cut `test_pointer_lines_wording.py` makes to count them."""
    inside = False
    bullets: list[str] = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if inside:
                break
            inside = "shorter cases" in line.lower()
        elif inside and line.startswith("- "):
            bullets.append(line)
    assert inside, "no '##' heading that contains 'shorter cases'"
    return bullets


def test_the_claims_reference_keeps_the_counts_its_pointer_states() -> None:
    """Four numbered headings and four shorter-case bullets: what the SKILL.md pointer says and
    `test_pointer_lines_wording.py` derives. Unlike the rows above, it holds on the old text too."""
    text = _read(_CLAIM_BOUNDARIES)
    numbered = _numbers(_headings(text))
    bullets = _shorter_case_bullets(text)
    assert len(numbered) == 4, (
        f"numbered headings read {numbered}, the pointer says four"
    )
    assert len(bullets) == 4, (
        f"{len(bullets)} shorter-case bullets, the pointer says four"
    )
