"""The checks of the test style wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_both_copies_of_a_template_are_the_same_text`: both copies of a template are the same text
* `test_the_twin_check_sees_a_planted_difference`: the twin check sees a planted difference
"""

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SEEDED = (
    _REPO / "plugins" / "core" / "src" / "lemmi_ai_kit" / "assets" / "ai" / "templates"
)
_OWN = _REPO / ".ai" / "templates"

_CASES = "test-cases.md"
_PLAN = "test-plan.md"


def _twin_problem(seeded: bytes, own: bytes) -> str | None:
    """Why two copies of a template differ, or None when they are the same text."""
    left, right = seeded.replace(b"\r\n", b"\n"), own.replace(b"\r\n", b"\n")
    if left == right:
        return None
    at = next(
        (i for i, (a, b) in enumerate(zip(left, right, strict=False)) if a != b),
        min(len(left), len(right)),
    )
    return f"the copies differ at byte {at} ({len(left)} against {len(right)} bytes)"


# --- the change ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", (_CASES, _PLAN))
def test_both_copies_of_a_template_are_the_same_text(name: str) -> None:
    problem = _twin_problem((_SEEDED / name).read_bytes(), (_OWN / name).read_bytes())
    assert problem is None, f"{name}: {problem}"


# --- the instruments ----------------------------------------------------------------------


def test_the_twin_check_sees_a_planted_difference() -> None:
    same = b"line one\nline two\n"
    assert _twin_problem(same, same) is None
    assert _twin_problem(same, b"line one\r\nline two\r\n") is None
    drift = _twin_problem(same, b"line one\nline twp\n")
    assert drift is not None and "byte 16" in drift
    assert _twin_problem(same, same + b"x") is not None
    assert _twin_problem(same, same[:-1]) is not None
