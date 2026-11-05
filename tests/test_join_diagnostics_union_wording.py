"""metric-validity-check says a sum of two presence counts is not their union.

The section on counting recorded commands lists four ways a count goes wrong. It now ends with a
paragraph about the figures those counts feed: two counts of the sessions in which something is
present (a tool used, a path touched) are added to get "either", and a session that has both is
counted twice. The paragraph says to take the union from the per-session records, or to subtract the
overlap and report it, and gives one worked example whose arithmetic a test recomputes. It is a
paragraph, not a fifth bullet, so the section's own "four ways" stays true, and a control checks the
stated number against the bullets it counts.

THE SURFACE, in numbers the tests assert: 1 file, 1 section (the counting section, cut by its
heading to the end of the file, a missing or doubled heading fails loudly), 4 claims over 5 phrases,
1 worked example, 4 bullets. A claim holds when every one of its phrases is in that section
(lower-cased, whitespace collapsed, bold marks dropped). Each phrase is fired at a planted removal,
and phrases placed under another heading, above the section or after it, must not count. The two
controls (the example, the bullets) hold on the old text as well: they guard what the paragraph
must not disturb.
"""

import re
from pathlib import Path

import pytest

_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "metric-validity-check"
    / "references"
    / "join-diagnostics.md"
)
_COUNTING = "## Counting recorded commands"
_FENCE = "```"
_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}

# (claim, the phrases that must all be present in the counting section)
_CLAIMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "a sum of two presence counts is not their union",
        ("a sum of two presence counts is not their union",),
    ),
    (
        "a session that has both is counted twice",
        ("counts a session that used both twice",),
    ),
    (
        "the union is taken from the per-session records, or the overlap is subtracted and shown",
        (
            "counting a session once when either is present",
            "subtract the overlap and report it beside the figure",
        ),
    ),
    (
        "it holds for any per-entity presence count",
        ("any per-entity presence count",),
    ),
)
_EXAMPLE = re.compile(
    r"say (\d+) sessions used a, (\d+) used b and (\d+) used both, "
    r"and the sum is (\d+) where the union is (\d+)"
)
_STATED_WAYS = re.compile(r"goes wrong in (\w+) ways")


def _outside_fences(lines: list[str]) -> list[tuple[int, str]]:
    """(index, line) for every line that is neither a fence line nor inside a fenced block."""
    kept: list[tuple[int, str]] = []
    fenced = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith(_FENCE):
            fenced = not fenced
        elif not fenced:
            kept.append((index, line))
    return kept


def _level(line: str) -> int:
    hashes = len(line) - len(line.lstrip("#"))
    return hashes if hashes and line[hashes : hashes + 1] == " " else 0


def _section(text: str, prefix: str) -> str:
    """The lines from the one heading that starts with `prefix` to the next heading of its level
    or a higher one. A `#` line inside a fence is not a heading."""
    lines = text.splitlines()
    starts = [i for i, line in _outside_fences(lines) if line.startswith(prefix)]
    assert len(starts) == 1, f"{len(starts)} headings start with {prefix!r}, expected 1"
    start = starts[0]
    level = _level(lines[start])
    end = next(
        (
            i
            for i, line in _outside_fences(lines)
            if i > start and 0 < _level(line) <= level
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def _fold(text: str) -> str:
    return " ".join(text.replace("**", "").split()).lower()


def _missing(folded: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in folded]


def _raw_section() -> str:
    return _section(_REFERENCE.read_text(encoding="utf-8"), _COUNTING)


def _bullets(section: str) -> list[str]:
    return [
        line
        for _, line in _outside_fences(section.splitlines())
        if line.startswith("- **")
    ]


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases]
    assert (len(_CLAIMS), len(phrases)) == (4, 5)
    assert _REFERENCE.is_file(), "the reference is not where the test looks"
    section = _raw_section()
    assert len(_fold(section)) > 0, "the counting section is empty"
    assert len(_bullets(section)) == 4, (
        "the counting section no longer has its four bullets"
    )


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_the_counting_section_states_the_claim(
    claim: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_fold(_raw_section()), phrases)
    assert not missing, (
        f"{claim}: not stated in the counting section, missing {missing}"
    )


def test_the_worked_example_adds_up() -> None:
    """The one example holds numbers, and a number written by hand is recomputed: the sum is the
    two counts added, the union is that sum less the sessions that have both."""
    found = _EXAMPLE.findall(_fold(_raw_section()))
    assert len(found) == 1, f"{len(found)} worked examples, expected 1"
    first, second, both, total, union = (int(number) for number in found[0])
    assert total == first + second, found
    assert union == first + second - both, found
    assert union < total, "an example whose union equals its sum shows nothing"


def test_the_stated_number_of_ways_is_the_number_of_bullets() -> None:
    """Control, green on the old text too: the paragraph is not a fifth bullet, so the intro's
    word and the bullets it counts still agree."""
    section = _raw_section()
    stated = _STATED_WAYS.findall(_fold(section))
    assert len(stated) == 1, (
        f"{len(stated)} statements of the number of ways, expected 1"
    )
    assert _NUMBER_WORDS[stated[0]] == len(_bullets(section)), (
        stated,
        _bullets(section),
    )


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section is the one gap reported, and an
    empty section lacks every phrase of a claim."""
    section = _fold(_raw_section())
    for claim, phrases in _CLAIMS:
        assert not _missing(section, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(section.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_phrases_under_another_heading_do_not_count() -> None:
    """Near-miss: the same phrases under a heading above the counting section leave that section
    without them, and under the right heading the same document holds them."""
    phrases = tuple(phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases)
    heading = f"{_COUNTING}, and reading a zero"
    wrong = f"## Elsewhere\n\n{' '.join(phrases)}\n\n{heading}\n\nnothing here.\n"
    right = f"## Elsewhere\n\nnothing here.\n\n{heading}\n\n{' '.join(phrases)}\n"
    assert _missing(_fold(_section(wrong, _COUNTING)), phrases) == list(phrases)
    assert _missing(_fold(_section(right, _COUNTING)), phrases) == []


def test_the_phrases_under_a_later_heading_do_not_count() -> None:
    """Near-miss: the same phrases under a heading AFTER the counting section are not in it, and
    before that heading the same document holds them. The section ends at the next heading."""
    phrases = tuple(phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases)
    heading = f"{_COUNTING}, and reading a zero"
    wrong = f"{heading}\n\nnothing here.\n\n## After\n\n{' '.join(phrases)}\n"
    right = f"{heading}\n\n{' '.join(phrases)}\n\n## After\n\nnothing here.\n"
    assert _missing(_fold(_section(wrong, _COUNTING)), phrases) == list(phrases)
    assert _missing(_fold(_section(right, _COUNTING)), phrases) == []
