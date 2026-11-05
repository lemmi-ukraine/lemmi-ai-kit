"""agent-delegate carries a reference on saving hand-back reports and on dated stamps.

Both are single-incident lessons, so they live in one reference with a one-line pointer in SKILL.md.
This test pins that the pointer resolves and that each claim is stated, including the one thing the
reference deliberately does NOT build: a command that compares stamps. The clock rule is stated for
every write that carries a time, with the bound between two clock readings in place of a guess and a
script that asserts one match per replacement for the correction. Each phrase of each claim is also
fired at a planted removal, so a claim that passes is one that could have failed.
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
        "the clock rule covers every write that carries a time, not only a stamp edit",
        (
            "every write that carries a time",
            "not only a stamp edit",
            "has been seen outside stamp edits",
        ),
    ),
    (
        "a time one reading cannot pin is the bound between two clock readings, never a guess",
        (
            "the bound between two clock readings",
            "never a guessed minute or a masked label",
        ),
    ),
    (
        "a guessed stamp is corrected by a script that asserts one match per replacement",
        (
            "asserts exactly one match per replacement",
            "prints how many it made",
        ),
    ),
    (
        "the stamp-comparing command is named and not built",
        ("is later than the stamp", "it is not built here"),
    ),
]


def _words(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_the_reference_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_words(_REFERENCE), phrases)
    assert not missing, f"{claim}: not stated, missing {missing}"


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_removing_a_phrase_makes_the_claim_fail(
    claim: str, phrases: tuple[str, ...]
) -> None:
    """Every phrase is fired at a planted removal, so a passing claim means its words are there."""
    text = _words(_REFERENCE)
    assert not _missing(text, phrases), f"{claim}: the intact reference must state it"
    for phrase in phrases:
        assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
            f"{claim}: removing {phrase!r} was not noticed"
        )


def test_skill_md_points_at_the_reference_and_the_pointer_resolves() -> None:
    skill = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\((references/[^)#]+)", skill)
    assert "references/hand-back-and-stamps.md" in links, links
    assert _REFERENCE.is_file()
