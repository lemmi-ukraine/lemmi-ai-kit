"""A design that records the command re-checking a claim says how a pipe survives its table.

A table cell has to escape every pipe, so a command with a pipe in it that is stored in a cell is no
longer the command: copied raw into `grep -E`, the escaped pipe is a literal one and the pattern
finds nothing, and a copy with the backslashes dropped can be another pattern again, one whose first
branch matches every line. Neither failure is loud: a grep that finds nothing and a grep that finds
everything both look like output. The design guide of `spec-driven-dev` carried no word on it, and
the spec templates ask for a command per claim.

What the guide says now is one section of its own at the end, `## Recording a Verification Command`:
the cell escapes every pipe and so does not reproduce, the two ways the copy goes wrong, a command
with a pipe goes in a fenced block under the table and is cited by the row's id, repeated `-e`
patterns replace an alternation but not a pipe that must stay literal, and every recorded command is
re-run from the raw text of the file. The section is a heading of its own, not a list item under the
risk list, so the places that read the guide's other sections do not absorb it.

THE SURFACE, in numbers the tests assert: 6 claims and 14 phrases, all inside that one section of
one file. A claim holds when every one of its phrases is in the section (lower-cased, whitespace
collapsed, so `grep -E` is read as `grep -e`). The section is read by its heading, so a phrase
placed under another heading does not count, and a file without the heading fails loudly. Each
phrase is fired at a planted removal, the old file is the new one cut at the heading, and the
section locator is fired at planted text before its silence is trusted.
"""

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_GUIDE = (
    _REPO
    / "plugins"
    / "core"
    / "skills"
    / "spec-driven-dev"
    / "references"
    / "design-guide.md"
)
_HEADING = "## Recording a Verification Command"
_RISK_LIST_HEADING = "### Common Risks"
_ANY_HEADING = re.compile(r"^(#{1,6})\s")

# (claim, the phrases that must all be in the section; lower-cased, whitespace collapsed). The
# backslash-pipe is written as a raw string so that no shell and no escape sequence touches it.
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1: a table cell escapes every pipe, so a command stored in a cell does not reproduce",
        (
            r"a markdown table cell must escape every pipe as `\|`",
            "so a command stored in a cell does not reproduce",
        ),
    ),
    (
        "2: copied raw into grep -E, the escaped pipe is a literal one and finds nothing",
        (
            "copied raw into `grep -e`",
            r"reads `\|` as a literal pipe and finds nothing",
        ),
    ),
    (
        "3: a copy with the backslashes dropped can be another pattern, and neither fails loudly",
        (
            "a form with the backslashes dropped can be another pattern again",
            "a leading `^|` is an alternation whose first branch matches every line",
            "neither reading fails loudly",
        ),
    ),
    (
        "4: a command with a pipe goes in a fenced block under the table, cited by the row's id",
        (
            "put any command that contains a pipe in a fenced block under the table",
            "cite it by the row's id",
        ),
    ),
    (
        "5: repeated -e replaces an alternation, not a pipe that must stay literal",
        (
            "repeated `-e` patterns replace an alternation and need no pipe there",
            "a pipe that must stay literal still needs the fence",
            r"stored in a cell as `\|`, plain gnu `grep` reads it as an alternation",
        ),
    ),
    (
        "6: every recorded command is re-run from the raw text, never from the rendered view",
        (
            "re-run every recorded command from the raw text of the file",
            "never from the rendered view",
        ),
    ),
)


def _guide() -> str:
    """The guide as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return _GUIDE.read_text(encoding="utf-8").replace("\r\n", "\n")


def _section(text: str, heading: str) -> str:
    """From the line that is `heading` to the next heading of the same or a higher level; a `#`
    line inside a fenced block is not a heading. A text without the heading fails loudly."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        found = None if in_fence or fence else _ANY_HEADING.match(line)
        if fence:
            in_fence = not in_fence
        if not body:
            if found is not None and line == heading:
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"no heading {heading!r}")
    return "\n".join(body)


def _headings(text: str) -> list[str]:
    """Every heading line of the text, in order, leaving out `#` lines inside fenced blocks."""
    found: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and _ANY_HEADING.match(line):
            found.append(line)
    return found


def _words(text: str) -> str:
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (6, 14)
    assert _GUIDE.is_file(), _GUIDE
    assert _words(_section(_guide(), _HEADING)), "the section is empty"


def test_the_section_is_a_heading_of_its_own_at_the_end_of_the_guide() -> None:
    """Once, at level two, after the risk list and last: so the list items above it are not read as
    the section's, and the section is not read as one of the list's."""
    headings = _headings(_guide())
    assert headings.count(_HEADING) == 1, f"{_HEADING!r} is not one heading"
    assert headings[-1] == _HEADING, f"the last heading is {headings[-1]!r}"
    risk = [h for h in headings if h.startswith(_RISK_LIST_HEADING)]
    assert len(risk) == 1, f"{len(risk)} headings start {_RISK_LIST_HEADING!r}"
    assert headings.index(risk[0]) < headings.index(_HEADING)


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[row[0] for row in _ROWS])
def test_the_section_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    section = _words(_section(_guide(), _HEADING))
    missing = _missing(section, phrases)
    assert not missing, f"the section does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section in turn is the one gap reported,
    and an empty section lacks every phrase of a row. A phrase the check cannot see go would let
    the guide lose its rule and stay green."""
    section = _words(_section(_guide(), _HEADING))
    for claim, phrases in _ROWS:
        assert not _missing(section, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(section.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_guide_without_the_section_fails_loudly() -> None:
    """The old file is the new one cut at the heading, so the check is fired at the text the guide
    carried before: no heading, a loud failure, and not a silent pass over an empty section."""
    text = _guide()
    assert _HEADING in text, f"the guide has no {_HEADING!r} to cut at"
    before = text[: text.index(_HEADING)]
    assert _HEADING not in before and _RISK_LIST_HEADING in before
    with pytest.raises(AssertionError, match="no heading"):
        _section(before, _HEADING)
    flat = _words(before)
    gone = [claim for claim, phrases in _ROWS if _missing(flat, phrases) == [*phrases]]
    assert len(gone) == len(_ROWS), f"the old guide already held a claim: {gone}"


def test_phrases_under_another_heading_do_not_count() -> None:
    """Planted near miss: every phrase of the table is present in the file, but under another
    heading, and the section that carries the right heading is empty of them."""
    every_phrase = " ".join(p for _, claim_phrases in _ROWS for p in claim_phrases)
    planted = f"## An earlier section\n\n{every_phrase}\n\n{_HEADING}\n\nNothing about pipes.\n"
    section = _words(_section(planted, _HEADING))
    for claim, phrases in _ROWS:
        assert _missing(section, phrases) == [*phrases], claim
    # the same phrases under the right heading are found, so the check is not blind to them
    right = _words(
        _section(f"## Earlier\n\nx\n\n{_HEADING}\n\n{every_phrase}\n", _HEADING)
    )
    for claim, phrases in _ROWS:
        assert not _missing(right, phrases), claim


def test_the_section_locator_stops_at_the_next_heading_and_skips_fences() -> None:
    text = (
        f"# T\n\n## One\nkept\n\n{_HEADING}\nin\n\n### Inside\nalso in\n\n"
        "```\n# not a heading\n```\n\n## Next\nout\n"
    )
    section = _section(text, _HEADING)
    lines = section.split("\n")
    assert "in" in lines and "also in" in lines and "# not a heading" in lines
    assert "out" not in lines and "kept" not in lines
    with pytest.raises(AssertionError, match="no heading"):
        _section("# T\n\n## One\nx\n", _HEADING)
    # a heading that only starts like the wanted one is another heading
    with pytest.raises(AssertionError, match="no heading"):
        _section(f"{_HEADING} and more\nbody\n", _HEADING)
    assert _headings(text) == ["# T", "## One", _HEADING, "### Inside", "## Next"]
