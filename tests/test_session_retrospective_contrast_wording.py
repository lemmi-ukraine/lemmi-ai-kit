"""session-retrospective says to compare like with like before a with-and-without contrast is an effect.

A contrast between sessions that had a thing (a skill, a hook, a rule) and sessions that did not is
a difference between two groups. The groups can also differ in model, size and kind of work, so the
schema reference, which documents the per-session fields a retrospective groups and matches on,
ends its per-session section with one sentence: compare like with like first, matching on those
fields. It is a reference only: SKILL.md gains no line, and the reference is reached through the
link SKILL.md already has.

THE SURFACE, in numbers the tests assert: 1 file, 1 section (the per-session section, cut by its
heading, a missing or doubled heading fails loudly), 3 claims over 4 phrases, and 4 per-session
fields the sentence names, each of which has to be a key of the schema block in that section. A
claim holds when every one of its phrases is in the section (lower-cased, whitespace collapsed,
bold marks dropped). Each phrase is fired at a planted removal, and the phrases placed under the
next heading must not count.
"""

import re
from pathlib import Path

import pytest

_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "session-retrospective"
    / "references"
    / "extractor-output-schema.md"
)
_SESSIONS = "### `sessions[]`"
_FENCE = "```"
_ANCHOR = (
    "compare like with like before reading a with-and-without contrast as an effect"
)

# (claim, the phrases that must all be present in the per-session section)
_CLAIMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "a with-and-without contrast is compared like with like before it is read as an effect",
        (_ANCHOR,),
    ),
    (
        "the contrast named is sessions that used a skill against sessions that did not",
        ("sessions that used a skill, set against sessions that did not",),
    ),
    (
        "the groups can differ in model, size and kind of work, so they are matched first",
        ("can also differ in model", "so match the two groups on those fields first"),
    ),
)
_FIELDS = {"models", "counts", "transcriptBytes", "toolsUsed"}


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
    return _section(_REFERENCE.read_text(encoding="utf-8"), _SESSIONS)


def _paragraph_with(section: str, anchor: str) -> str:
    """The blank-line-delimited paragraph of the raw section whose folded text holds `anchor`."""
    found = [p for p in section.split("\n\n") if anchor in _fold(p)]
    assert len(found) == 1, f"{len(found)} paragraphs hold {anchor!r}, expected 1"
    return found[0]


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases]
    assert (len(_CLAIMS), len(phrases), len(_FIELDS)) == (3, 4, 4)
    assert _REFERENCE.is_file(), "the reference is not where the test looks"
    assert len(_fold(_raw_section())) > 0, "the per-session section is empty"


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_the_per_session_section_states_the_claim(
    claim: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_fold(_raw_section()), phrases)
    assert not missing, (
        f"{claim}: not stated in the per-session section, missing {missing}"
    )


def test_every_field_the_sentence_names_is_a_key_of_the_schema_block() -> None:
    section = _raw_section()
    paragraph = _paragraph_with(section, _ANCHOR)
    named = set(re.findall(r"`([A-Za-z]+)`", paragraph))
    assert named == _FIELDS, (
        f"the sentence names {sorted(named)}, expected {sorted(_FIELDS)}"
    )
    absent = [name for name in sorted(named) if f'"{name}":' not in section]
    assert not absent, f"named in the sentence, not a key of the schema block: {absent}"


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


def test_the_phrases_under_the_next_heading_do_not_count() -> None:
    """Near-miss: the same phrases under `## Redaction & privacy` leave the per-session section
    without them, and under the right heading the same document holds them."""
    phrases = tuple(phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases)
    heading = f"{_SESSIONS} (one object per session)"
    wrong = (
        f"{heading}\n\nnothing here.\n\n## Redaction & privacy\n\n{' '.join(phrases)}\n"
    )
    right = (
        f"{heading}\n\n{' '.join(phrases)}\n\n## Redaction & privacy\n\nnothing here.\n"
    )
    assert _missing(_fold(_section(wrong, _SESSIONS)), phrases) == list(phrases)
    assert _missing(_fold(_section(right, _SESSIONS)), phrases) == []
