"""Three short lessons are written down in references their skills already link, and pinned here.

Each lesson cost a page something: a record that said a session was running when the name now
belonged to another process, a peer's transcript printed to find out whether it was alive, which
copied what an operator had pasted into the reader's own transcript, and a background gate whose
completion notice read exit 0 because the last command of the chain was an `echo`. They are
references only: no SKILL.md gains a line, and the one pointer that names the new subsection
re-wraps lines that were already there.

THE SURFACE, in numbers the tests assert: 4 claims and 11 phrases over two references. A claim holds
when every one of its phrases is in its reference (lower-cased, whitespace collapsed). Each phrase is
fired at a planted removal, so a phrase the check could not see go is not in the table. The sentence
about a kickoff that says "any other reply is a no" is the template's, and is pinned with the brief
template's other rules in `test_brief_template_rules.py`.
"""

import re
from pathlib import Path

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "orchestration" / "skills"

_SAFETY = "parallel-session-safety"
_SHARED_INDEX = f"{_SAFETY}/references/shared-index-protocol.md"
_EXTERNAL_AGENTS = "orchestrate/references/external-agents.md"

# (claim, reference under plugins/orchestration/skills, the phrases that must all be present;
# lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "g: a session's name is not its identity; a peer is named by the host's session id",
        _SHARED_INDEX,
        (
            "### 12l.",
            "a session's name is not its identity",
            "can be reused",
            "the session id the host assigned",
        ),
    ),
    (
        "g: never print the first message of a peer's transcript",
        _SHARED_INDEX,
        (
            "never print the first message of a peer's transcript",
            "copies whatever was pasted",
        ),
    ),
    (
        "g: whether a peer is live is read from facts about its transcript, not its words",
        _SHARED_INDEX,
        (
            "a count of one literal you chose",
            "prints a number and no text",
        ),
    ),
    (
        "h: a background command's completion notice carries the last command's exit code",
        _EXTERNAL_AGENTS,
        (
            "the completion notice carries the exit code of the last command of the chain",
            "end the chain with the gate",
            "write its exit code to a file",
        ),
    ),
)

_POINTER_HEADING = "## 12."


def _words(reference: str) -> str:
    return " ".join((_SKILLS / reference).read_text(encoding="utf-8").split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _blockquote_of(skill_text: str, heading_prefix: str) -> str:
    """Every quoted line of the section whose heading starts with `heading_prefix`."""
    quoted: list[str] = []
    inside = False
    for line in skill_text.replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            if inside:
                break
            inside = line.startswith(heading_prefix)
        elif inside and line.startswith(">"):
            quoted.append(line)
    return "\n".join(quoted)


def test_the_surface_is_stated_in_numbers() -> None:
    references = {reference for _, reference, _ in _ROWS}
    phrases = [phrase for _, _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(references), len(phrases)) == (4, 2, 11)
    unreadable = [name for name in sorted(references) if not (_SKILLS / name).is_file()]
    assert not unreadable, (
        f"{len(unreadable)} of {len(references)} references: {unreadable}"
    )


@pytest.mark.parametrize(
    ("claim", "reference", "phrases"), _ROWS, ids=[row[0] for row in _ROWS]
)
def test_the_reference_states_the_claim(
    claim: str, reference: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_words(reference), phrases)
    assert not missing, f"{reference} does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real text in turn is the one gap reported,
    and an empty text lacks every phrase of a row. A phrase the check cannot see go would let
    a reference lose its claim and stay green."""
    for claim, reference, phrases in _ROWS:
        text = _words(reference)
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


@pytest.mark.parametrize("reference", sorted({row[1] for row in _ROWS}))
def test_the_skill_already_links_the_reference(reference: str) -> None:
    """A reference no SKILL.md links is not read; the links exist, so no SKILL.md grows."""
    skill, _, relative = reference.partition("/")
    linked = (_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    assert relative in linked, f"{skill}/SKILL.md does not link {relative}"


def test_the_safety_skill_pointer_names_the_new_subsection() -> None:
    """The section 12 pointer lists every lettered subsection; 12l is one, so it is named there."""
    skill = (_SKILLS / _SAFETY / "SKILL.md").read_text(encoding="utf-8")
    pointer = _blockquote_of(skill, _POINTER_HEADING)
    assert "references/shared-index-protocol.md" in pointer, pointer
    assert re.search(r"\(12l\)", pointer), pointer
    assert "(12k)" in pointer, "the create collision pointer must stay"
