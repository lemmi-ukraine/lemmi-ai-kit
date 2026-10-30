"""agent-delegate carries a reference on saving hand-back reports and on dated stamps.

Both are single-incident lessons, so they live in one reference with a one-line pointer in SKILL.md.
This test pins that the pointer resolves and that each claim is stated, including the one thing the
reference deliberately does NOT build: a command that compares stamps.
"""

import re
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "agent-delegate"
)
_REFERENCE = _SKILL / "references" / "hand-back-and-stamps.md"

# (claim, the phrases that must all be present; lower-cased, whitespace collapsed)
_CLAIMS: list[tuple[str, tuple[str, ...]]] = [
    (
        "a hand-back report is saved verbatim, at once, labelled as model output",
        ("save the hand-back report verbatim, at once, labelled as model output",),
    ),
    ("a digest is not a durable copy", ("a digest is not a durable copy",)),
    (
        "an empty per-agent transcript is recovered from the parent session's transcript",
        ("come back empty", "survives in the parent session's transcript"),
    ),
    (
        "done, last and re-stamped are written only after the action",
        ('write "done", "last" or "re-stamped" only after the action',),
    ),
    (
        "the clock reading is taken immediately before the stamp edit, which is the last write",
        ("immediately before the stamp edit and make that edit the last write",),
    ),
    (
        "the stamp-comparing command is named and not built",
        ("is later than the stamp", "it is not built here"),
    ),
]


def _words(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_the_reference_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    text = _words(_REFERENCE)
    missing = [phrase for phrase in phrases if phrase not in text]
    assert not missing, f"{claim}: not stated, missing {missing}"


def test_skill_md_points_at_the_reference_and_the_pointer_resolves() -> None:
    skill = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\((references/[^)#]+)", skill)
    assert "references/hand-back-and-stamps.md" in links, links
    assert _REFERENCE.is_file()
