"""plan-critic reviews QUANTIFIED claims: a count or a per-record field is enumerated and executed.

A plan stated that every caller without a retry took one path, in words copied from a reviewer's
report into several documents; enumerating the call sites showed it held for half of them. The
check is a seventh dimension in `references/review-dimensions.md`, scoped to quantified claims only
(executing scenarios is costly), with one list line in SKILL.md. This test pins that the line
resolves to a real dimension and that each part of the check is stated.
"""

import re
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills" / "plan-critic"
)
_REFERENCE = _SKILL / "references" / "review-dimensions.md"

# (claim, the phrases that must all be present; lower-cased, whitespace collapsed)
_CLAIMS: list[tuple[str, tuple[str, ...]]] = [
    (
        "the dimension applies only to a plan that states attempts, retries, charges or a field per record",
        ("only when a plan or spec states attempts, retries, charges",),
    ),
    (
        "the callers come from a full listing that was run",
        ("taken from a full listing",),
    ),
    (
        "one scenario is executed per distinct row, with controls from the pinned tests",
        (
            "one executed scenario for each distinct row",
            "controls taken from the pinned tests",
        ),
    ),
    ("a derived column is marked as derived", ("derived rather than executed",)),
    ("a field is stated per event type", ("per event type, not per group name",)),
    (
        "a sentence copied from a reviewer's report is the author's claim",
        ("copied from a reviewer's report", "the author's claim"),
    ),
]


def _words(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_dimension_7_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    text = _words(_REFERENCE)
    assert "## dimension 7 — quantified claims" in text, "no Dimension 7 heading"
    section = text[text.index("## dimension 7 ") :]
    missing = [phrase for phrase in phrases if phrase not in section]
    assert not missing, f"{claim}: not stated in Dimension 7, missing {missing}"


def test_skill_md_lists_dimension_7_next_to_the_other_dimensions() -> None:
    skill = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    listed = re.findall(r"^(\d)\. ([^\n]+)", skill, flags=re.MULTILINE)
    seventh = [title for number, title in listed if number == "7"]
    assert len(seventh) == 1 and seventh[0].lower().startswith("quantified claims"), (
        listed
    )
    assert "references/review-dimensions.md" in skill
    assert _REFERENCE.is_file()
