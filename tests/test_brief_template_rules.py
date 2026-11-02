"""A dispatch brief carries six rules, each in a section of the template that is only theirs.

Each rule was added after a session stopped, or ran twice, without it: a paste line typed by hand
with a placeholder left in it, a delegate that stopped on two named spellings of a placeholder and
walked past a third, a second run that repeated a page because the first run's note did not exist
yet, an injected session default that outranked the project's own ruling, a precondition written
as prose, and a kickoff that said "any other reply is a no" without saying what "yes" permits.

THE SURFACE, in numbers the tests assert: 6 claims and 14 phrases in one reference,
`orchestrate/references/brief-template.md`, all inside one section, `## Rules a dispatch brief
carries`. The `## Paste line` section is pinned by its own test (`test_peer_brief_first_step.py`)
and is not this file's: no phrase here is judged against it. A claim holds when every one of its
phrases is in the section (lower-cased, whitespace collapsed), and each phrase is fired at a planted
removal, so a phrase the check could not see go is not in the table.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATE = _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate"
_TEMPLATE = _ORCHESTRATE / "references" / "brief-template.md"
_HEADING = "## Rules a dispatch brief carries"
_PASTE_LINE_HEADING = "## Paste line"

# (claim, the phrases that must all be in the section; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1: a paste line is printed by a command, never typed, and holds no substitution",
        (
            "a paste line is printed by a command, never typed",
            "carries no substitution",
        ),
    ),
    (
        "2: any placeholder is a stop, not only the spellings the brief names",
        (
            "stop on any `<...>` placeholder",
            "walks past the third",
            "nothing is written",
        ),
    ),
    (
        "3: the return note is the first write, made so that it fails if it exists",
        (
            "the return note is the first write",
            "fails if it exists",
            "another run holds this page",
        ),
    ),
    (
        "4: a project's standing decision beats a session default",
        (
            "a project's standing decision beats a session default",
            "does not authorize it",
        ),
    ),
    (
        "6: a precondition is a command with an expected result, and a surprise is a stop",
        (
            "preconditions are commands with expected results",
            "a surprise is a stop",
        ),
    ),
    (
        'h: a kickoff that says "any other reply is a no" says what a plain affirmative means',
        (
            "any other reply is a no",
            "says what a plain affirmative means",
        ),
    ),
)


def _template() -> str:
    """The template as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return _TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n")


def _section(text: str, heading: str) -> str:
    """The lines under `heading` up to the next level-2 heading; empty when it is absent."""
    lines = text.split("\n")
    if heading not in lines:
        return ""
    body: list[str] = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def _words(text: str) -> str:
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (6, 14)
    assert _TEMPLATE.is_file(), _TEMPLATE


def test_the_rules_have_a_section_of_their_own() -> None:
    """Once, outside the fenced skeleton, and not folded into the paste-line section."""
    text = _template()
    assert text.split("\n").count(_HEADING) == 1, f"{_HEADING!r} is not one heading"
    assert _words(_section(text, _HEADING)), "the section is empty"
    assert _HEADING not in _section(text, _PASTE_LINE_HEADING)


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[row[0] for row in _ROWS])
def test_the_section_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    section = _words(_section(_template(), _HEADING))
    missing = _missing(section, phrases)
    assert not missing, f"the section does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section in turn is the one gap reported,
    and an empty section lacks every phrase of a row. A phrase the check cannot see go would
    let the template lose its rule and stay green."""
    section = _words(_section(_template(), _HEADING))
    for claim, phrases in _ROWS:
        assert not _missing(section, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(section.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_skill_already_links_the_template() -> None:
    """A reference no SKILL.md links is not read; the link exists, so SKILL.md gains no line."""
    skill = (_ORCHESTRATE / "SKILL.md").read_text(encoding="utf-8")
    assert "references/brief-template.md" in skill


def test_the_links_in_the_section_resolve() -> None:
    """A rule that points at the create collision names a file that exists."""
    section = _section(_template(), _HEADING)
    targets = re.findall(r"\]\(([^)\s#]+)(?:#[^)\s]*)?\)", section)
    unresolved = [
        target
        for target in targets
        if not (_TEMPLATE.parent / target).resolve().is_file()
    ]
    assert not unresolved, f"links that do not resolve from the template: {unresolved}"
    assert targets, "the section links nothing; the create collision rule names 12k"
