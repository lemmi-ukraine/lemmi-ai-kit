"""initiative-cleanup's retirement sweep covers the ids a retired file defined.

Step 4b repointed references by path or basename. A path grep cannot see an id, so text
relocated out of a retired file kept saying "see REQ-12" after the file that said what REQ-12
is had gone. Step 4b now carries a one-line pointer and the method lives in a reference,
because SKILL.md sits at its line cap.

These tests slice Step 4b by its heading (a missing heading fails loudly), assert that the one
pointer line says to grep the destination for the id prefixes and to write what each id means,
and that its link resolves, and assert that the reference states the method (it calls the
step the destination grep) while SKILL.md does not restate it. The Related list's line about
AGENTS.md may claim only what both the kit's AGENTS.md and the one it seeds carry: it named a
deletion-sweep rule that neither has. Each assertion fails on the text it replaced. The
helpers are functions over a string, so
`test_the_slicer_sees_planted_text_and_fails_loudly` and
`test_the_claim_check_sees_a_planted_claim_and_fails_loudly` fire them at planted text before
their silence on the real files is trusted.
"""

import re
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_SKILL = shipped_skill_dirs()["initiative-cleanup"]
_REFERENCE_LINK = "references/retirement-sweep.md"
_HEADING = re.compile(r"^(#{1,6})\s+\S")
_CONTINUATION = re.compile(r"\\\r?\n[ \t]*")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text, lower-cased, with backslash continuations joined, blockquote markers dropped
    and whitespace runs as one space, so a re-wrap of prose or of a command changes no match."""
    joined = _CONTINUATION.sub(" ", text)
    return " ".join(re.sub(r"(?m)^\s*>+ ?", "", joined).split()).lower()


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the code it holds, not a heading. A missing heading fails with the
    heading named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _step_4b() -> str:
    return _section(
        _text(_SKILL / "SKILL.md"), "### 4b.", "initiative-cleanup SKILL.md"
    )


def test_step_4b_points_at_the_retirement_sweep_in_one_line() -> None:
    pointers = [line for line in _step_4b().split("\n") if _REFERENCE_LINK in line]
    assert len(pointers) == 1, (
        f"Step 4b has {len(pointers)} lines linking {_REFERENCE_LINK}; expected exactly one"
    )
    pointer = _fold(pointers[0])
    missing = [
        phrase
        for phrase in ("grep the destination", "id prefixes", "what each id means")
        if phrase not in pointer
    ]
    assert not missing, f"the pointer line does not carry {missing}: {pointer!r}"
    assert (_SKILL / _REFERENCE_LINK).is_file(), f"{_REFERENCE_LINK} does not resolve"


def test_the_reference_states_the_method() -> None:
    folded = _fold(_text(_SKILL / _REFERENCE_LINK))
    missing = [
        phrase
        for phrase in (
            "derive the id prefixes from the retired file",
            "destination grep",
            "git grep --untracked --no-exclude-standard",
            "what each id means where it now stands",
        )
        if phrase not in folded
    ]
    assert not missing, f"{_REFERENCE_LINK} does not state: {missing}"
    assert folded.index("derive the id prefixes") < folded.index("destination grep")
    assert folded.index("destination grep") < folded.index("what each id means")


def test_skill_md_does_not_restate_the_method() -> None:
    folded = _fold(_text(_SKILL / "SKILL.md"))
    assert "derive the id prefixes" not in folded, (
        "the method belongs in the reference; SKILL.md keeps only the pointer"
    )


# What the Related list may say AGENTS.md holds, each claim paired with the text a file must
# carry for the sentence to be true. The kit's own AGENTS.md and the one it seeds into a
# project are both read: an adopter gets the second, and a claim that only the first carries
# sends them to a rule they do not have.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_AGENTS_DOCUMENTS = (
    "AGENTS.md",
    "plugins/core/src/lemmi_ai_kit/assets/templates/AGENTS.md",
)
_AGENTS_CLAIMS = (
    ("deletion-sweep rule", "deletion-sweep"),
    ("learnings-system routing", "learnings system"),
)


def _related_agents_line() -> str:
    related = _section(
        _text(_SKILL / "SKILL.md"), "## Related", "initiative-cleanup SKILL.md"
    )
    lines = [line for line in related.split("\n") if line.startswith("- `AGENTS.md`")]
    assert len(lines) == 1, (
        f"the Related list has {len(lines)} lines about AGENTS.md; expected exactly one"
    )
    return _fold(lines[0])


def _claims_without_a_home(line: str, documents: dict[str, str]) -> list[str]:
    """Each known claim the line makes that some document does not carry.

    A line that makes none of the known claims fails loudly: a reworded line would otherwise
    slip past the table and the check would read nothing.
    """
    made = [(claim, needed) for claim, needed in _AGENTS_CLAIMS if claim in line]
    if not made:
        known = [claim for claim, _needed in _AGENTS_CLAIMS]
        raise AssertionError(f"the line makes none of the claims {known}: {line!r}")
    return [
        f"{claim!r}: {name} has no {needed!r}"
        for name, body in documents.items()
        for claim, needed in made
        if needed not in body
    ]


def test_the_related_agents_line_claims_only_what_both_agents_files_carry() -> None:
    documents = {name: _fold(_text(_REPO_ROOT / name)) for name in _AGENTS_DOCUMENTS}
    assert all(documents.values()), f"an AGENTS.md read as empty: {sorted(documents)}"
    assert _claims_without_a_home(_related_agents_line(), documents) == []


def test_the_claim_check_sees_a_planted_claim_and_fails_loudly() -> None:
    both = {"kit": "### learnings system", "seeded": "### learnings system"}
    planted = _fold(
        "- `AGENTS.md` — the deletion-sweep rule this step implements; the "
        "learnings-system routing"
    )
    assert _claims_without_a_home(planted, both) == [
        "'deletion-sweep rule': kit has no 'deletion-sweep'",
        "'deletion-sweep rule': seeded has no 'deletion-sweep'",
    ]
    one_has_it = {**both, "kit": "the deletion-sweep rule, and the learnings system"}
    assert _claims_without_a_home(planted, one_has_it) == [
        "'deletion-sweep rule': seeded has no 'deletion-sweep'"
    ]
    honest = _fold("- `AGENTS.md` — the learnings-system routing")
    assert _claims_without_a_home(honest, both) == []
    with pytest.raises(AssertionError, match="makes none of the claims"):
        _claims_without_a_home(_fold("- `AGENTS.md` — something else"), both)


def test_the_slicer_sees_planted_text_and_fails_loudly() -> None:
    planted = "\n".join(
        [
            "### 4b. Repoint",
            "> **A quoted rule,** wrapped",
            "> over two lines.",
            "```bash",
            "# a comment inside a fence is not a heading",
            "git grep --untracked \\",
            "  --no-exclude-standard -n x",
            "```",
            "A line that links references/retirement-sweep.md here.",
            "",
            "### 4c. Next",
            "after the section",
        ]
    )
    four_b = _section(planted, "### 4b.", "planted")
    assert "links references/retirement-sweep.md" in four_b
    assert "after the section" not in four_b
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### 9z.", "planted")
    folded = _fold(four_b)
    assert "**a quoted rule,** wrapped over two lines." in folded
    assert "git grep --untracked --no-exclude-standard -n x" in folded
