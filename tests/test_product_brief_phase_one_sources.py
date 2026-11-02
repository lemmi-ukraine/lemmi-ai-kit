"""`product-brief` Phase 1 reads the documents the project names, not a set of onboarding docs.

Step 1 of Phase 1, the codebase research that comes before any discussion, told the author to
read "the onboarding docs and backend services" a feature touches. A project has onboarding
docs only if it keeps them, so in a project without them the author went looking for a folder
that does not exist. The project's own AGENTS.md names the architecture and flow documents it
does keep. Phase 1 now points the author at those.

The tests read Phase 1 only, from its heading to the Phase 2 heading, with line breaks folded:
the new words must be inside it, and the old words must not. Both headings are found by their
text and a missing one fails loudly, so a renamed phase is a failure and never an empty match.
`test_the_phase_reader_sees_planted_text_and_fails_loudly` fires the reader and the two checks
at planted text that holds the old shape, wrapped over a line break, and at near misses (the new
words in Phase 2 only, the old words in a later phase only) before their silence on the real
file is trusted.

THE SURFACE, in numbers the tests assert: 1 file, 1 section of it (Phase 1), 2 checks (the new
words present, the old words absent).
"""

import re
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "product-brief"
    / "SKILL.md"
)
_HEADING = re.compile(r"^(#{1,6})\s+\S")
_PHASE_ONE = "### Phase 1"
_PHASE_TWO = "### Phase 2"

_NEW = "the architecture and flow documents named in AGENTS.md"
# The words on one side of the dash that precedes them in the file, so the string has no dash.
_OLD = "read the onboarding docs and backend services"
_EM = chr(0x2014)


def _fold(text: str) -> str:
    """The text with every run of whitespace, line breaks included, as one space."""
    return " ".join(text.split())


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _between(text: str, start: str, end: str, where: str) -> str:
    """From the heading line that starts with `start` up to, not including, the next heading
    line that starts with `end`. A `#` line inside a fenced block is not a heading. A heading
    that is not found fails loudly with its text named."""
    lines = text.split("\n")
    in_fence = False
    first: int | None = None
    last: int | None = None
    for index, line in enumerate(lines):
        if _is_fence(line):
            in_fence = not in_fence
        elif not in_fence and _HEADING.match(line) is not None:
            if first is None:
                if line.startswith(start):
                    first = index
            elif line.startswith(end):
                last = index
                break
    if first is None:
        raise AssertionError(f"{where}: no heading starting {start!r}")
    if last is None:
        raise AssertionError(f"{where}: no heading starting {end!r} after {start!r}")
    return "\n".join(lines[first:last])


def _phase_one(text: str) -> str:
    return _fold(_between(text, _PHASE_ONE, _PHASE_TWO, "product-brief SKILL.md"))


def _problems(phase_one: str) -> list[str]:
    """What is wrong with the folded Phase 1 text: the new words missing, the old ones kept."""
    problems: list[str] = []
    if _NEW not in phase_one:
        problems.append(f"does not carry {_NEW!r}")
    if _OLD in phase_one:
        problems.append(f"still carries {_OLD!r}")
    return problems


# --- the change ---------------------------------------------------------------------------


def test_phase_one_points_at_the_documents_agents_md_names() -> None:
    problems = _problems(_phase_one(_SKILL.read_text(encoding="utf-8")))
    assert not problems, "product-brief SKILL.md, Phase 1: " + "; ".join(problems)


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_one_section_of_one_file() -> None:
    assert _SKILL.is_file()
    text = _SKILL.read_text(encoding="utf-8")
    assert len(text.split("\n")) > 100, "SKILL.md is shorter than any real version"
    phase = _between(text, _PHASE_ONE, _PHASE_TWO, "product-brief SKILL.md")
    assert 5 < len(phase.split("\n")) < 40, "Phase 1 is not the section it should be"
    assert "Find the affected user flow" in phase, "Phase 1 lost its first step"


def test_the_phase_reader_sees_planted_text_and_fails_loudly() -> None:
    old = "\n".join(
        [
            "### Phase 1: Codebase Research (mandatory, silent)",
            "",
            f"1. **Find the affected user flow** {_EM} read the onboarding docs and",
            "   backend services that the feature touches.",
            "",
            "### Phase 2: Assumption Challenge",
            f"Read {_NEW} here.",
            "",
            "### Phase 3: Write the Brief",
            "In a later phase, read the onboarding docs and backend services again.",
        ]
    )
    # The old shape, wrapped over a line break, is reported and its absence of the new words too.
    assert _problems(_phase_one(old)) == [
        f"does not carry {_NEW!r}",
        f"still carries {_OLD!r}",
    ]
    # The near misses: the new words in Phase 2 only do not count for Phase 1, and the old words
    # in Phase 3 only are not Phase 1's.
    assert "Phase 2" not in _phase_one(old) and "later phase" not in _phase_one(old)
    new = old.replace(
        "read the onboarding docs and\n   backend services that the feature touches.",
        f"read {_NEW},\n   then the backend services that the feature touches.",
    )
    assert new != old, "the planted change found nothing to change"
    assert _problems(_phase_one(new)) == []
    with pytest.raises(AssertionError, match="no heading starting '### Phase 9'"):
        _between(old, "### Phase 9", _PHASE_TWO, "planted")
    with pytest.raises(AssertionError, match="no heading starting '### Phase 7' after"):
        _between(old, _PHASE_ONE, "### Phase 7", "planted")
    fenced = (
        "### Phase 1\n```\n### Phase 2 inside a fence\n```\nbody\n### Phase 2\nafter\n"
    )
    assert "body" in _between(fenced, _PHASE_ONE, _PHASE_TWO, "planted")
    assert "after" not in _between(fenced, _PHASE_ONE, _PHASE_TWO, "planted")
