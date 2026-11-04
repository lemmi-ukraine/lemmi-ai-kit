"""python-conventions says a declared Optional keeps its declared type when it is assigned an `Any`.

The Narrowing section teaches that an annotated assignment does not narrow an `Any` (the validator
case, where only `cast` clears the report). The same mechanism has a second shape: after
`limit: int | None = payload["limit"]` basedpyright still reads `limit` as `int | None`, so a later
`limit > 0` is reported although the value is an integer at run time. Measured with the checker the
pack teaches: the comparison is reported as `reportOptionalOperand`, and a separate local annotated
`int` is not. The section gains one paragraph and a three-line example after its last paragraph, and
the validator paragraph before it stays as it was. The paragraph says why an annotation is the way
out here although it is not in the validator case: the variable keeps the type declared for it.

THE SURFACE, in numbers the tests assert: 1 file, 1 section (the Narrowing section, cut by its
heading, a missing or doubled heading fails loudly), 3 claims over 6 phrases, 2 python examples in
the section, each of which has to parse. A claim holds when every one of its phrases is in that
section (lower-cased, whitespace collapsed). Each phrase is fired at a planted removal, and phrases
placed under the next heading must not count. The control on the validator paragraph holds on the
old text as well: it guards what the new paragraph must not disturb.
"""

import ast
from pathlib import Path

import pytest

_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "python"
    / "skills"
    / "python-conventions"
    / "references"
    / "coding-patterns.md"
)
_NARROWING = "## Narrowing `Any`"
_NEXT = "## New Parameters, and Validators Called By Their Own Caller"
_FENCE = "```"
_LAST_OLD_SENTENCE = "a different operation in the opposite direction."
_NEW_START = "a declared optional behaves the same way"

# (claim, the phrases that must all be present in the Narrowing section)
_CLAIMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "a declared Optional behaves the same way when the assigned value is `Any`",
        ("a declared optional behaves the same way when the assigned value is `any`",),
    ),
    (
        "the checker keeps the declared type, so the later comparison is reported",
        ("basedpyright still reads `limit` as `int | none`", "`reportoptionaloperand`"),
    ),
    (
        "the variable keeps its declared type, so the way out is a separate typed local, or a "
        "check on a value that can be missing",
        (
            "the variable keeps the type you declared for it",
            "separate local whose annotation is the type you mean",
            "check it first and narrow on that",
        ),
    ),
)
_VALIDATOR_PARAGRAPH = (
    "burning a basedpyright cycle",
    "payload = cast(dict[str, any], data)",
    _LAST_OLD_SENTENCE,
)


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
    return _section(_REFERENCE.read_text(encoding="utf-8"), _NARROWING)


def _python_fences(section: str) -> list[str]:
    fences: list[str] = []
    current: list[str] | None = None
    for line in section.splitlines():
        stripped = line.strip()
        if current is None:
            if stripped.startswith(f"{_FENCE}python"):
                current = []
        elif stripped.startswith(_FENCE):
            fences.append("\n".join(current))
            current = None
        else:
            current.append(line)
    return fences


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases]
    assert (len(_CLAIMS), len(phrases)) == (3, 6)
    assert _REFERENCE.is_file(), "the reference is not where the test looks"
    section = _raw_section()
    assert len(_fold(section)) > 0, "the Narrowing section is empty"
    assert len(_python_fences(section)) == 2, (
        "the Narrowing section no longer has 2 examples"
    )


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_the_narrowing_section_states_the_claim(
    claim: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_fold(_raw_section()), phrases)
    assert not missing, (
        f"{claim}: not stated in the Narrowing section, missing {missing}"
    )


def test_the_example_shows_the_separate_local_and_every_example_parses() -> None:
    fences = _python_fences(_raw_section())
    for source in fences:
        ast.parse(source)
    shown = [
        source for source in fences if 'raw_limit: int = payload["limit"]' in source
    ]
    assert len(shown) == 1, f"{len(shown)} examples show the separate local, expected 1"
    assert "if raw_limit > 0:" in shown[0], (
        "the example does not compare the separate local"
    )


def test_the_new_paragraph_follows_the_validator_paragraph() -> None:
    section = _fold(_raw_section())
    assert _LAST_OLD_SENTENCE in section and _NEW_START in section
    assert section.index(_LAST_OLD_SENTENCE) < section.index(_NEW_START), (
        "the new paragraph is not after the last paragraph of the section"
    )


def test_the_validator_paragraph_is_untouched() -> None:
    """Control, green on the old text too: the new paragraph is added, nothing before it moves."""
    assert _missing(_fold(_raw_section()), _VALIDATOR_PARAGRAPH) == []


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
    """Near-miss: the same phrases under the next section leave the Narrowing section without
    them, and under the right heading the same document holds them."""
    phrases = tuple(phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases)
    heading = f"{_NARROWING} in a Pydantic before-validator"
    wrong = f"{heading}\n\nnothing here.\n\n{_NEXT}\n\n{' '.join(phrases)}\n"
    right = f"{heading}\n\n{' '.join(phrases)}\n\n{_NEXT}\n\nnothing here.\n"
    assert _missing(_fold(_section(wrong, _NARROWING)), phrases) == list(phrases)
    assert _missing(_fold(_section(right, _NARROWING)), phrases) == []
