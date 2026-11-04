"""flow-mapping carries a reference on four ways a register or flow-document edit looks finished.

The four claims are single-incident lessons, so they live in one reference with a one-line pointer
in SKILL.md rather than in SKILL.md itself. This test pins that the pointer resolves and that each
claim is stated, in words that survive a reflow of the lines.

The checks are fired at planted text so their silence on the real file means something: each
phrase deleted from a copy is reported, the reference as it stood before the fourth way was added
(its paragraph cut, its opening count back at three) is reported for exactly the two rows that
paragraph and that count carry, and a copy wrapped one word to a line is not reported.

THE SURFACE, in numbers the tests assert: 8 rows and 14 phrases in one reference.
"""

import re
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills" / "flow-mapping"
)
_REFERENCE = _SKILL / "references" / "register-and-validator-pitfalls.md"
_OPENING_COUNT = "the reference opens by counting four ways"
_FOURTH_WAY = (
    "a count quoted in prose is not checked, so a changed class re-runs the derivation"
)
_FOURTH_LEAD = "**A number in prose is not checked.**"

# (claim, the phrases that must all be present; lower-cased, whitespace collapsed)
_CLAIMS: list[tuple[str, tuple[str, ...]]] = [
    (
        "an edit that drops a call edge deletes the callee's symbol row in the same edit",
        ("delete the callee's symbol index row in the same edit",),
    ),
    (
        "an evidence cell cites only files that have a coverage row",
        ("cite in an evidence cell only files that already have a coverage row",),
    ),
    (
        "the validator is probed with a deliberately broken copy before its zero is quoted",
        ("deliberately broken copy of the document", "before quoting its zero"),
    ),
    (
        "a cell that is one backtick span cannot take backticked names",
        (
            "a cell that is itself one backtick span cannot take backticked names",
            "write the names without backticks",
        ),
    ),
    (
        "coverage-note counts are pinned records, re-measured beside the old figure",
        ("pinned records", "re-measured at layer x", "beside the old figure"),
    ),
    (
        "changed rows are named by diffing two scratch exports, with a control that must differ",
        ("base export and from its changed export", "control that must differ"),
    ),
    (
        _OPENING_COUNT,
        ("four ways a flow-document edit looks finished",),
    ),
    (
        _FOURTH_WAY,
        (
            "not that a count an invariant quotes still holds",
            "re-run each derivation the claim quotes",
        ),
    ),
]


def _fold(text: str) -> str:
    return " ".join(text.split()).lower()


def _words(path: Path) -> str:
    return _fold(path.read_text(encoding="utf-8"))


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _unstated(text: str) -> list[str]:
    """The claims whose phrases are not all in `text` (lower-cased, whitespace collapsed)."""
    return [claim for claim, phrases in _CLAIMS if _missing(text, phrases)]


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_the_reference_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_words(_REFERENCE), phrases)
    assert not missing, f"{claim}: not stated, missing {missing}"


def test_a_phrase_deleted_from_a_copy_of_the_reference_is_reported() -> None:
    text = _words(_REFERENCE)
    fired = 0
    for claim, phrases in _CLAIMS:
        for phrase in phrases:
            planted = text.replace(phrase, "")
            assert _missing(planted, phrases) == [phrase], (
                f"{claim}: deleting {phrase!r} went unreported"
            )
            fired += 1
    assert (len(_CLAIMS), fired) == (8, 14), (len(_CLAIMS), fired)


def test_the_text_before_the_fourth_way_is_reported_for_its_rows() -> None:
    raw = _REFERENCE.read_text(encoding="utf-8")
    assert raw.count(_FOURTH_LEAD) == 1, (
        "the fourth paragraph opens with its bold lead, once"
    )
    assert raw.count("Four ways") == 1, "the opening line counts four ways, once"
    before = raw.split(_FOURTH_LEAD)[0].replace("Four ways", "Three ways")
    assert _unstated(_fold(before)) == [_OPENING_COUNT, _FOURTH_WAY]


def test_a_copy_wrapped_one_word_to_a_line_is_not_reported() -> None:
    raw = _REFERENCE.read_text(encoding="utf-8")
    narrow = "\n".join(raw.split())
    assert len(narrow.splitlines()) == len(raw.split()), (
        "the copy has one word to a line"
    )
    assert _unstated(_fold(narrow)) == []


def test_skill_md_points_at_the_reference_and_the_pointer_resolves() -> None:
    skill = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\((references/[^)#]+)", skill)
    assert "references/register-and-validator-pitfalls.md" in links, links
    assert _REFERENCE.is_file()
