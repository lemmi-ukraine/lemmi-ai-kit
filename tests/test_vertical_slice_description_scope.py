"""The vertical-slice skill scopes the clause that decides when it loads to the layout it serves.

The skill is a reference for Python backends laid out by feature, and it loads without being
asked. Its description said so in the first sentence ("for Python backend features") and then
said "Use when: creating new backend features, adding files to existing features, reviewing
feature structure, or troubleshooting circular imports between features", a clause that fits a
backend in any language and any layout, so the skill was offered in repositories it does not fit.

The Use-when clause now says where it applies: in a Python repository laid out by feature. A
check of the whole description cannot guard this, because the first sentence could carry the
words while the clause that decides the load stayed as it was. The check here cuts the
description at "Use when" and reads only what follows.

THE SURFACE, in numbers the tests assert: 1 file, 1 description, cut at the 1 place that says
"Use when", read for 2 phrases. The description is parsed with the kit's own frontmatter parser,
the one the skill audit uses, so a block scalar of either style and a quoted line read the same.

What each test asserts:

* `test_the_use_when_clause_names_the_language_and_the_layout` reads the real file as it is.
* `test_the_frontmatter_still_parses_with_the_keys_that_precede_the_description` shows the edit
  left the frontmatter intact: the keys before the description are still keys, and the block still
  closes after it (the description is the last key, so the closing delimiter is what follows it).
* The instrument tests fire the check at the description as it stood, in each of three YAML
  styles, which it must flag for both phrases, and at the new clause, which it must not; show that
  words moved into the first sentence while the clause stays as it was are flagged although a
  whole description check passes them; show that one phrase without the other is flagged for the
  one that is missing; and show that a description with no "Use when", two of them, no
  frontmatter or no description fails loudly.
"""

from pathlib import Path

import pytest

from lemmi_ai_kit.checks import parse_frontmatter

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "vertical-slice"
    / "SKILL.md"
)

# The description is cut here, and only what follows is read.
_CUT = "Use when"
# The two phrases the clause must carry: the language, and the layout the skill serves.
_LANGUAGE = "a Python repository"
_LAYOUT = "laid out by feature"
_PHRASES = (_LANGUAGE, _LAYOUT)

_STYLES = ("folded", "literal", "quoted")

# The description as it stood: the first sentence names the language, the clause names nothing.
_FIRST_SENTENCE = "Enforce vertical slice architecture for Python backend features. "
_MIDDLE = (
    "Covers feature directory scaffolding, layer separation (API/Service/Storage), "
    "one-class-per-file convention, prompt-as-view pattern, enum placement, import rules, "
    "and anti-patterns. "
)
_LIST = (
    "creating new backend features, adding files to existing features, reviewing feature "
    "structure, or troubleshooting circular imports between features."
)
_OLD_CLAUSE = f"Use when: {_LIST}"
_NEW_CLAUSE = f"Use when, in {_LANGUAGE} {_LAYOUT}: {_LIST}"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _description(text: str, where: str) -> str:
    """The description from the frontmatter, parsed as the skill audit parses it, folded."""
    fields, error = parse_frontmatter(text)
    if fields is None:
        raise AssertionError(f"{where}: the frontmatter does not parse: {error}")
    value = fields.get("description")
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"{where}: the frontmatter has no description")
    return " ".join(value.split())


def _after_use_when(description: str, where: str) -> str:
    """What follows "Use when". Anything but exactly one such place fails loudly, with the
    count named, so a reworded clause is a loud failure and never an empty match."""
    count = description.count(_CUT)
    if count != 1:
        raise AssertionError(
            f"{where}: {count} places say {_CUT!r} in the description, expected 1"
        )
    return description.partition(_CUT)[2]


def _gaps(text: str, where: str) -> list[str]:
    """What the description lacks after "Use when"; an empty list means nothing."""
    after = _after_use_when(_description(text, where), where)
    return [
        f"the description after {_CUT!r} does not say {phrase!r}"
        for phrase in _PHRASES
        if phrase not in after
    ]


def _document(description: str, style: str) -> str:
    """A SKILL.md head that carries `description` as a folded block, a literal block or one
    quoted line, after the keys that come before it in the real file (it is the last key)."""
    if style == "quoted":
        entry = f'description: "{description}"\n'
    else:
        marker = ">" if style == "folded" else "|"
        words = description.split()
        lines = ["  " + " ".join(words[at : at + 8]) for at in range(0, len(words), 8)]
        entry = f"description: {marker}\n" + "\n".join(lines) + "\n"
    return (
        "---\nname: vertical-slice\nuser-invocable: false\nmetadata:\n  type: reference\n"
        f"{entry}---\n\n# Body\n"
    )


def _missing(*phrases: str) -> list[str]:
    return [
        f"the description after {_CUT!r} does not say {phrase!r}" for phrase in phrases
    ]


# --- the change ---------------------------------------------------------------------------


def test_the_use_when_clause_names_the_language_and_the_layout() -> None:
    gaps = _gaps(_read(_SKILL), _SKILL.name)
    assert not gaps, f"vertical-slice {_SKILL.name}: {gaps}"


def test_the_frontmatter_still_parses_with_the_keys_that_precede_the_description() -> (
    None
):
    fields, error = parse_frontmatter(_read(_SKILL))
    assert error is None and fields is not None, error
    assert fields.get("name") == "vertical-slice"
    assert fields.get("user-invocable") == "false"


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_the_one_description() -> None:
    assert _SKILL.is_file(), f"{_SKILL} is not a file"
    description = _description(_read(_SKILL), _SKILL.name)
    assert len(description) > 100, "the description is shorter than any real one"
    assert description.count(_CUT) == 1, (
        f"{description.count(_CUT)} places say {_CUT!r}"
    )
    assert len(_PHRASES) == 2 and len(set(_PHRASES)) == 2, "the two phrases are not two"


@pytest.mark.parametrize("style", _STYLES)
def test_the_check_flags_the_old_description_and_passes_the_new_one(style: str) -> None:
    old = _document(_FIRST_SENTENCE + _MIDDLE + _OLD_CLAUSE, style)
    new = _document(_FIRST_SENTENCE + _MIDDLE + _NEW_CLAUSE, style)
    assert _gaps(old, "planted old") == _missing(*_PHRASES)
    assert _gaps(new, "planted new") == []


def test_words_moved_to_the_first_sentence_do_not_scope_the_clause() -> None:
    moved = _FIRST_SENTENCE.replace(
        "for Python backend features.", f"for {_LANGUAGE} {_LAYOUT}."
    )
    assert moved != _FIRST_SENTENCE, "the planted move found nothing to move"
    text = _document(moved + _MIDDLE + _OLD_CLAUSE, "literal")
    whole = _description(text, "planted")
    assert all(phrase in whole for phrase in _PHRASES), (
        "a check of the whole description would read both phrases as present"
    )
    assert _gaps(text, "planted") == _missing(*_PHRASES)


@pytest.mark.parametrize("phrase", _PHRASES)
def test_one_phrase_without_the_other_is_flagged_for_the_one_missing(
    phrase: str,
) -> None:
    kept = next(other for other in _PHRASES if other != phrase)
    clause = f"Use when, in {kept}: {_LIST}"
    text = _document(_FIRST_SENTENCE + _MIDDLE + clause, "folded")
    assert _gaps(text, "planted half") == _missing(phrase)


def test_a_description_the_cut_cannot_read_fails_loudly() -> None:
    without = _document(_FIRST_SENTENCE + _MIDDLE, "folded")
    with pytest.raises(AssertionError, match="0 places say"):
        _gaps(without, "planted")
    twice = _document(_FIRST_SENTENCE + _NEW_CLAUSE + " " + _NEW_CLAUSE, "folded")
    with pytest.raises(AssertionError, match="2 places say"):
        _gaps(twice, "planted")
    with pytest.raises(AssertionError, match="does not parse"):
        _gaps("# no frontmatter\n", "planted")
    with pytest.raises(AssertionError, match="no description"):
        _gaps("---\nname: planted\n---\n", "planted")
