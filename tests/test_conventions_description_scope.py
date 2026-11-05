"""The Python test-conventions skill says Python where it says when to use it.

Its description opened "Testing conventions for the Python backend", but the sentence that tells
a reader when to pick the skill up said only "Use when writing, reviewing, or scaffolding test
files", which fits a test file in any language, so the skill was offered in a repository whose
tests are written in another one.

The description now names Python in that sentence. A check of the whole description cannot guard
this, because the first sentence already holds the word and the old text passes it. The check here
cuts the description at "Use when" and reads only what follows.

THE SURFACE, in numbers the tests assert: 1 file, 1 description, cut at the 1 place that says
"Use when", read for 1 word. The description is parsed with the kit's own frontmatter parser, the
one the skill audit uses, so a block scalar of either style and a quoted line read the same.

What each test asserts:

* `test_the_use_when_part_of_the_description_names_python` reads the real file as it is.
* `test_the_frontmatter_still_parses_with_the_keys_that_follow_the_description` shows the edit
  left the frontmatter intact: the keys after the description are still keys, not description text.
* The instrument tests fire the check at the description as it stood, in each of three YAML
  styles, which it must flag, and at the new sentence, which it must not; show that a whole
  description check passes the old text (the trap the cut avoids); show that a word which only
  contains "Python" is not the word; and show that a description with no "Use when", two of them,
  no frontmatter or no description fails loudly.
"""

import re
from pathlib import Path

import pytest

from lemmi_ai_kit.checks import parse_frontmatter

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "python"
    / "skills"
    / "test-conventions"
    / "SKILL.md"
)

# The description is cut here, and only what follows is read.
_CUT = "Use when"
_PYTHON = re.compile(r"\bPython\b")
_GAP = f"the description after {_CUT!r} does not name Python"

_STYLES = ("folded", "literal", "quoted")

# The description as it stood: the first sentence already names the language.
_FIRST_SENTENCES = (
    "Testing conventions for the Python backend. Integration-first philosophy, DI-based "
    "mocking, timeout decorators, base class rules, factory usage, and banned patterns. "
)
_OLD_USE_WHEN = "Use when writing, reviewing, or scaffolding test files."
_NEW_USE_WHEN = "Use when writing, reviewing, or scaffolding Python test files."


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
    return [] if _PYTHON.search(after) else [_GAP]


def _document(description: str, style: str) -> str:
    """A SKILL.md head that carries `description` as a folded block, a literal block or one
    quoted line, followed by the keys that come after it in the real file."""
    if style == "quoted":
        entry = f'description: "{description}"\n'
    else:
        marker = ">" if style == "folded" else "|"
        words = description.split()
        lines = ["  " + " ".join(words[at : at + 8]) for at in range(0, len(words), 8)]
        entry = f"description: {marker}\n" + "\n".join(lines) + "\n"
    return f"---\nname: test-conventions\n{entry}user-invocable: false\n---\n\n# Body\n"


# --- the change ---------------------------------------------------------------------------


def test_the_use_when_part_of_the_description_names_python() -> None:
    gaps = _gaps(_read(_SKILL), _SKILL.name)
    assert not gaps, f"test-conventions {_SKILL.name}: {gaps}"


def test_the_frontmatter_still_parses_with_the_keys_that_follow_the_description() -> (
    None
):
    fields, error = parse_frontmatter(_read(_SKILL))
    assert error is None and fields is not None, error
    assert fields.get("name") == "test-conventions"
    assert fields.get("user-invocable") == "false"


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_the_one_description() -> None:
    assert _SKILL.is_file(), f"{_SKILL} is not a file"
    description = _description(_read(_SKILL), _SKILL.name)
    assert len(description) > 100, "the description is shorter than any real one"
    assert description.count(_CUT) == 1, (
        f"{description.count(_CUT)} places say {_CUT!r}"
    )


@pytest.mark.parametrize("style", _STYLES)
def test_the_check_flags_the_old_description_and_passes_the_new_one(style: str) -> None:
    old = _document(_FIRST_SENTENCES + _OLD_USE_WHEN, style)
    new = _document(_FIRST_SENTENCES + _NEW_USE_WHEN, style)
    assert _gaps(old, "planted old") == [_GAP]
    assert _gaps(new, "planted new") == []


def test_a_check_of_the_whole_description_passes_the_old_text() -> None:
    """The trap the cut avoids: the first sentence holds the word, so a check that looks at
    the whole description reads the old text as scoped."""
    old = _document(_FIRST_SENTENCES + _OLD_USE_WHEN, "folded")
    assert _PYTHON.search(_description(old, "planted old")) is not None
    assert _gaps(old, "planted old") == [_GAP]


def test_a_word_that_only_contains_python_is_not_the_word() -> None:
    near = _document(
        _FIRST_SENTENCES
        + "Use when writing, reviewing, or scaffolding Pythonic tests.",
        "folded",
    )
    assert _gaps(near, "planted near miss") == [_GAP]


def test_a_description_the_cut_cannot_read_fails_loudly() -> None:
    without = _document("Testing conventions for the Python backend.", "folded")
    with pytest.raises(AssertionError, match="0 places say"):
        _gaps(without, "planted")
    twice = _document(_FIRST_SENTENCES + _NEW_USE_WHEN + " " + _NEW_USE_WHEN, "folded")
    with pytest.raises(AssertionError, match="2 places say"):
        _gaps(twice, "planted")
    with pytest.raises(AssertionError, match="does not parse"):
        _gaps("# no frontmatter\n", "planted")
    with pytest.raises(AssertionError, match="no description"):
        _gaps("---\nname: planted\n---\n", "planted")
