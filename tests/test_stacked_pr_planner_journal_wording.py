"""stacked-pr-planner says a journal branch is a deletion event for the untracked files it tracks.

Measured in a throwaway repository: two untracked documents committed on a branch were present on
it and gone after switching back to a base that lacks them, and `git restore --source` returned
different bytes under `core.autocrlf` (identical bytes without it). The planner's Lane J section
had no sentence about either. The paragraph has to sit in Step 2, where Lane J is defined, so a
reader choosing a lane meets it.
"""

from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "stacked-pr-planner"
    / "SKILL.md"
)

# (claim, the phrases that must all be present; lower-cased, whitespace collapsed)
_CLAIMS: list[tuple[str, tuple[str, ...]]] = [
    (
        "a journal branch is a deletion event for the untracked files it tracks",
        ("a deletion event for the untracked files it tracks",),
    ),
    ("the switch removes the files from disk", ("makes git delete them from disk",)),
    (
        "byte-exact copies are taken first, hashes compared again after the switch",
        (
            "byte-exact copies first",
            "commit last",
            "compare hashes again after the switch",
        ),
    ),
    (
        "git restore is not relied on to return the files unchanged",
        (
            "do not rely on `git restore --source=<branch>` to return them unchanged",
            "core.autocrlf",
        ),
    ),
]


def _step_2() -> str:
    text = " ".join(_SKILL.read_text(encoding="utf-8").split()).lower()
    start = text.index("## step 2 ")
    return text[start : text.index("## step 3 ", start)]


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_step_2_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    section = _step_2()
    missing = [phrase for phrase in phrases if phrase not in section]
    assert not missing, f"{claim}: not stated in Step 2, missing {missing}"
