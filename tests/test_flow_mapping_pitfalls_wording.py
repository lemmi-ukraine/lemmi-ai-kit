"""flow-mapping carries a reference on three ways a register or flow-document edit looks finished.

The three claims are single-incident lessons, so they live in one reference with a one-line pointer
in SKILL.md rather than in SKILL.md itself. This test pins that the pointer resolves and that each
claim is stated, in words that survive a reflow of the lines.
"""

import re
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills" / "flow-mapping"
)
_REFERENCE = _SKILL / "references" / "register-and-validator-pitfalls.md"

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
    assert "references/register-and-validator-pitfalls.md" in links, links
    assert _REFERENCE.is_file()
