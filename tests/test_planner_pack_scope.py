"""The test-planning texts put the project's own testing conventions first.

The planner told its reader that a language pack's test-type decision table "is authoritative"
and to defer to it rather than invent a competing taxonomy. The same order stood in five places:
Step 3 of the planner, its level-assignment reference, the comment in the test-plan template every
project is seeded with, the same comment in the kit's own copy of that template, and the plan
critic's level-assignment question, which called a plan wrong for not using the table's level
names. A pack's table is written for one language and one test runner, so in a project written in
another language that order made a plan wrong for following the project's own conventions.

What the five texts say now: the project's own testing conventions come first, and a language
pack's reference applies only where it matches the code under test, so one written for another
language never overrides them. The routing stays by role, never by a pack skill's name, and the
plan critic asks whether the plan lets the conventions come first and calls a plan wrong only when
it invents level names that they already define.

THE SURFACE, in numbers the tests assert: 5 files, each read in the one section that holds its
paragraph, 19 checks for an old shape (read in the whole file) and 15 checks for the new phrases
(read in that section only). A text is read with emphasis marks dropped, whitespace folded and
the case lowered, so a re-wrap or a re-emphasis is the same sentence.

What each test asserts:

* `test_the_pack_table_is_not_authoritative_and_the_projects_conventions_come_first` reads each
  file as it is: no old shape, the three new phrases in its section.
* The instrument tests fire the check at the text each file carried before (`_OLD`, excerpts of
  the files as they stood), which it must flag with exactly the old shapes that text held and
  every missing phrase, at the wording the rewrite first had (`_FIRST_WORDING`), which it must
  flag for the shapes that wording held, and at text that uses the same words in another sense,
  which it must not flag. They show that a sentence which only looks like a new phrase ("tests
  come first", a scope with no match, a criterion that names another purpose) does not stand in for
  it, that the new phrases count only inside the section, that a line break or an emphasis mark
  inside an old claim does not hide it, and that a missing heading fails loudly.
"""

import re
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PLANNER = _REPO / "plugins" / "core" / "skills" / "test-planner"
_CRITIC = _REPO / "plugins" / "core" / "skills" / "plan-critic"
_SEEDED = (
    _REPO / "plugins" / "core" / "src" / "lemmi_ai_kit" / "assets" / "ai" / "templates"
)
_OWN = _REPO / ".ai" / "templates"

# The dash the old text used, spelled as a code point so a retyped hyphen cannot make an
# excerpt below look the same while matching nothing.
_EM = chr(0x2014)

_HEADING = re.compile(r"^(#{1,6})\s+\S")

# What no rewritten file may say again. The first three stood in the text before the rewrite,
# the rest in the wording the rewrite first had.
_AUTHORITY = "that table is authoritative"
_DEFER = "defer to it rather than inventing a competing taxonomy"
_CRITIC_QUESTION = "does the plan use that table's level names"
# A scope that covers only the pack's table, while the pack's whole reference is read.
_NARROW_SCOPE = "table applies only where"
# A mismatch criterion that names a test runner where the other texts name a language.
_UNEVEN_CRITERION = "another language or test runner"
# A fallback keyed to the old precondition: with a table that does not match, it licensed nothing.
_OLD_FALLBACK = "provides no such table"
# A critic question whose subject is the conventions, where its sibling questions ask about the plan.
_CRITIC_CONVENTIONS_AS_SUBJECT = "do the project's own testing conventions come first"
_EVERYWHERE = (_AUTHORITY, _NARROW_SCOPE, _UNEVEN_CRITERION)

# What each rewritten file must say, inside the section that holds its paragraph: whose
# conventions come first (a bare "come first" is true of any sentence that says something does),
# the scope a pack's reference is held to, and the one criterion by which it stops applying.
_CONVENTIONS_FIRST = "project's own testing conventions come first"
_SCOPE = "applies only where it matches the code"
_CRITERION = "written for another language"
_NEW_PHRASES = (_CONVENTIONS_FIRST, _SCOPE, _CRITERION)

# The word that ties a section to the paragraph this guard is about.
_ANCHOR = "language pack"


class _Surface(NamedTuple):
    name: str
    path: Path
    heading: str
    old_shapes: tuple[str, ...]


_SURFACES: tuple[_Surface, ...] = (
    _Surface(
        "planner-step-3",
        _PLANNER / "SKILL.md",
        "## Step 3",
        (*_EVERYWHERE, _DEFER),
    ),
    _Surface(
        "planner-level-names",
        _PLANNER / "references" / "level-assignment.md",
        "## Level names",
        (*_EVERYWHERE, _OLD_FALLBACK),
    ),
    _Surface(
        "seeded-test-plan-template",
        _SEEDED / "test-plan.md",
        "## Test Levels",
        _EVERYWHERE,
    ),
    _Surface(
        "plan-critic-dimension-6",
        _CRITIC / "references" / "review-dimensions.md",
        "## Dimension 6",
        (*_EVERYWHERE, _CRITIC_QUESTION, _CRITIC_CONVENTIONS_AS_SUBJECT),
    ),
    _Surface(
        "kit-own-test-plan-template",
        _OWN / "test-plan.md",
        "## Test Levels",
        _EVERYWHERE,
    ),
)
_BY_NAME = {surface.name: surface for surface in _SURFACES}

# The comment both template copies carried before, word for word.
_OLD_TEMPLATE: tuple[str, tuple[str, ...]] = (
    "<!-- Use the project's own level names. Where a language pack ships a test-type "
    "decision table,\n"
    f"     that table is authoritative {_EM} read the pack's testing conventions "
    "reference and use its\n"
    "     names verbatim, so the plan and the suite agree. -->\n",
    (_AUTHORITY,),
)

# The paragraph each surface carried before, word for word, with the old shapes it held.
_OLD: dict[str, tuple[str, tuple[str, ...]]] = {
    "planner-step-3": (
        "**Where the project ships a language pack with its own test-type decision table, "
        "that table is\n"
        f"authoritative {_EM} defer to it rather than inventing a competing taxonomy.** "
        "Read the pack's\n"
        "testing conventions reference for the project's own level names, its base-class "
        "rules, and its\n"
        "required timeout decorators, and use those names in the plan. Do not hardcode any "
        "pack skill's\n"
        "name here; route by role, so the plan stays correct in a project with a different "
        "language pack\n"
        "or none at all.\n",
        (_AUTHORITY, _DEFER),
    ),
    "planner-level-names": (
        "Use the names the project already uses. Where the project ships a language pack "
        "with its own\n"
        "test-type decision table, **that table is authoritative** "
        f"{_EM} read it for the project's level names,\n"
        "its base-class rules, and any required timeout or marker decorators, then use "
        "those names in the\n"
        "plan verbatim so the plan and the suite agree.\n",
        (_AUTHORITY,),
    ),
    "seeded-test-plan-template": _OLD_TEMPLATE,
    "plan-critic-dimension-6": (
        "- Where the project ships a language pack with its own test-type table, does the "
        "plan use that\n"
        f"  table's level names {_EM} or has it invented a competing taxonomy? Major.\n",
        (_CRITIC_QUESTION,),
    ),
    "kit-own-test-plan-template": _OLD_TEMPLATE,
}

# The wording the rewrite first had, word for word, with the old shapes it held and the new
# phrases it lacked. It scoped only the pack's table, named a test runner at one site where the
# others name a language, kept a fallback keyed to the old precondition, asked a critic question
# about the conventions where its sibling questions ask about the plan, and left the criterion
# out of the template. The kit's own template copy was not rewritten then, so it has no entry.
_FIRST_WORDING: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "planner-step-3": (
        "**The project's own testing conventions come first.** Use its level names, its base-class rules\n"
        "and its required timeout decorators in the plan, so the plan and the suite agree. Where the\n"
        "project ships a language pack with its own test-type decision table, read the pack's testing\n"
        "conventions reference as well, but its table applies only where it matches the code under test: a\n"
        "table written for another language never overrides the project's own conventions. Do not\n"
        "hardcode any pack skill's name here; route by role, so the plan stays correct in a project with a\n"
        "different language pack or none at all.\n",
        (_NARROW_SCOPE,),
        (),
    ),
    "planner-level-names": (
        "The project's own testing conventions come first: use the level names the project already uses,\n"
        "with its base-class rules and any required timeout or marker decorators, verbatim, so the plan\n"
        "and the suite agree. Where the project ships a language pack with its own test-type decision\n"
        "table, read it as well, but the table applies only where it matches the code under test: one\n"
        "written for another language or test runner never overrides the project's own conventions.\n"
        "\n"
        "Where the project provides no such table, these generic levels are a safe default:\n",
        (_NARROW_SCOPE, _UNEVEN_CRITERION, _OLD_FALLBACK),
        (),
    ),
    "seeded-test-plan-template": (
        "<!-- The project's own testing conventions come first: use its level names verbatim, so the plan\n"
        "     and the suite agree. Where a language pack ships a test-type decision table, read the pack's\n"
        "     testing conventions reference too; its table applies only where it matches the code under\n"
        "     test. -->\n",
        (_NARROW_SCOPE,),
        (_CRITERION,),
    ),
    "plan-critic-dimension-6": (
        "- Do the project's own testing conventions come first for the level names? A language pack's\n"
        "  test-type table applies only where it matches the code under test, so a plan is not wrong for\n"
        "  skipping a table written for another language; it is wrong when it invents level names that the\n"
        "  conventions, or a matching table, already define. Major.\n",
        (_NARROW_SCOPE, _CRITIC_CONVENTIONS_AS_SUBJECT),
        (),
    ),
}

# Text that says the new thing, and that uses two of the old words in another sense: a
# failing test can be "authoritative", and "competing taxonomy" can be something to avoid.
_NEW_SHAPE = (
    "The project's own testing conventions come first. A language pack's reference applies "
    "only where it matches the code under test: one written for another language never "
    "overrides them. Which failing test is authoritative when they disagree is settled by "
    "the owning level, and the plan invents no competing taxonomy for a language pack."
)

# The new sentence in three clauses. Each clause is swapped for a look-alike that says something
# else in nearly the same words, and the check must then report that clause's phrase, and only
# that one, as missing.
_FIRST_CLAUSE = "The project's own testing conventions come first."
_SCOPE_CLAUSE = "it applies only where it matches the code under test"
_CRITERION_CLAUSE = "one written for another language never overrides them"
_GOOD = (
    f"{_FIRST_CLAUSE} Where a language pack ships a test-type decision table, read the pack's "
    f"testing conventions reference too; {_SCOPE_CLAUSE}: {_CRITERION_CLAUSE}."
)
_LOOKALIKES: tuple[tuple[str, str, str, str], ...] = (
    # (id, the clause swapped out, the look-alike swapped in, the phrase that must then be missing)
    ("tests-come-first", _FIRST_CLAUSE, "Tests come first.", _CONVENTIONS_FIRST),
    (
        "pack-tables-come-first",
        _FIRST_CLAUSE,
        "Pack tables come first.",
        _CONVENTIONS_FIRST,
    ),
    (
        "the-packs-own-conventions-come-first",
        _FIRST_CLAUSE,
        "The pack's own testing conventions come first.",
        _CONVENTIONS_FIRST,
    ),
    (
        "a-scope-with-no-match",
        _SCOPE_CLAUSE,
        "it applies wherever the project uses the language",
        _SCOPE,
    ),
    (
        "a-criterion-naming-another-purpose",
        _CRITERION_CLAUSE,
        "one written for another purpose never overrides them",
        _CRITERION,
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """The text lower-cased, emphasis and code marks dropped, every run of whitespace one space.

    A sentence re-wrapped across lines, or re-emphasised, reads the same.
    """
    return " ".join(re.sub(r"[*`]", "", text).split()).lower()


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


def _problems(text: str, surface: _Surface) -> list[str]:
    """What a file still says or no longer says; an empty list means nothing.

    An old shape is looked for in the whole file. A new phrase is looked for in the section
    that holds the paragraph, so text elsewhere in the file cannot stand in for it.
    """
    whole = _plain(text)
    section = _plain(_section(text, surface.heading, surface.name))
    problems = [
        f"still says {old!r}" for old in surface.old_shapes if old.lower() in whole
    ]
    problems += [
        f"section {surface.heading!r} does not say {new!r}"
        for new in _NEW_PHRASES
        if new not in section
    ]
    return problems


def _planted(surface: _Surface, body: str) -> str:
    """A small document with `body` under the surface's heading and a section after it."""
    return (
        f"# Planted\n\n{surface.heading} planted\n\n{body}\n\n## After\n\nelsewhere\n"
    )


_IDS = [surface.name for surface in _SURFACES]


# --- the change ---------------------------------------------------------------------------


@pytest.mark.parametrize("surface", _SURFACES, ids=_IDS)
def test_the_pack_table_is_not_authoritative_and_the_projects_conventions_come_first(
    surface: _Surface,
) -> None:
    problems = _problems(_read(surface.path), surface)
    assert not problems, f"{surface.name} ({surface.path.name}): " + "; ".join(problems)


# --- the instruments ----------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_SURFACES) == 5, f"{len(_SURFACES)} surfaces, not the 5 stated"
    assert len({surface.path for surface in _SURFACES}) == 5, (
        "two surfaces share a file"
    )
    assert len(set(_IDS)) == 5, "two surfaces share a name"
    assert set(_OLD) == set(_IDS), (
        "an old excerpt has no surface, or a surface has none"
    )
    assert set(_FIRST_WORDING) <= set(_IDS), "a first-wording excerpt has no surface"
    assert len(_FIRST_WORDING) == 4, (
        f"{len(_FIRST_WORDING)} first wordings, not the 4 stated"
    )
    old_checks = sum(len(surface.old_shapes) for surface in _SURFACES)
    assert old_checks == 19, f"{old_checks} old-shape checks, not the 19 stated"
    new_checks = len(_SURFACES) * len(_NEW_PHRASES)
    assert new_checks == 15, f"{new_checks} new-phrase checks, not the 15 stated"
    for surface in _SURFACES:
        text = _read(surface.path)
        assert text.strip(), f"{surface.name}: the file is empty"
        section = _plain(_section(text, surface.heading, surface.name))
        assert _ANCHOR in section, (
            f"{surface.name}: section {surface.heading!r} no longer holds the paragraph "
            f"about a {_ANCHOR}, so the new phrases would be read in the wrong place"
        )


@pytest.mark.parametrize("surface", _SURFACES, ids=_IDS)
def test_the_check_flags_the_old_text_of_every_surface(surface: _Surface) -> None:
    excerpt, held = _OLD[surface.name]
    problems = _problems(_planted(surface, excerpt), surface)
    for old in held:
        assert f"still says {old!r}" in problems, (
            f"{surface.name}: the check missed the old shape {old!r}; it reported {problems}"
        )
    assert len(problems) == len(held) + len(_NEW_PHRASES), (
        f"{surface.name}: expected the old shapes {held} and every missing phrase, "
        f"got {problems}"
    )


@pytest.mark.parametrize("name", list(_FIRST_WORDING), ids=list(_FIRST_WORDING))
def test_the_check_flags_the_first_wording_of_every_rewritten_surface(
    name: str,
) -> None:
    surface = _BY_NAME[name]
    excerpt, held, lacking = _FIRST_WORDING[name]
    expected = [f"still says {old!r}" for old in held] + [
        f"section {surface.heading!r} does not say {new!r}" for new in lacking
    ]
    assert expected, f"{name}: the planted wording holds nothing the check should flag"
    assert sorted(_problems(_planted(surface, excerpt), surface)) == sorted(expected)


@pytest.mark.parametrize("surface", _SURFACES, ids=_IDS)
def test_the_check_is_silent_on_text_that_uses_the_words_in_another_sense(
    surface: _Surface,
) -> None:
    assert _problems(_planted(surface, _NEW_SHAPE), surface) == []


@pytest.mark.parametrize(
    ("clause", "lookalike", "phrase"),
    [(clause, lookalike, phrase) for _, clause, lookalike, phrase in _LOOKALIKES],
    ids=[name for name, *_ in _LOOKALIKES],
)
def test_a_look_alike_of_a_new_phrase_does_not_stand_in_for_it(
    clause: str, lookalike: str, phrase: str
) -> None:
    surface = _SURFACES[0]
    assert _problems(_planted(surface, _GOOD), surface) == [], (
        "the good text is not silent"
    )
    body = _GOOD.replace(clause, lookalike)
    assert body != _GOOD, "the planted look-alike replaced nothing"
    expected = [f"section {surface.heading!r} does not say {phrase!r}"]
    assert _problems(_planted(surface, body), surface) == expected


def test_the_new_phrases_count_only_inside_the_section() -> None:
    surface = _SURFACES[0]
    elsewhere = (
        f"# Planted\n\n{surface.heading} planted\n\nnothing about the matter here.\n\n"
        f"## After\n\n{_NEW_SHAPE}\n"
    )
    assert len(_problems(elsewhere, surface)) == len(_NEW_PHRASES)


def test_a_line_break_or_an_emphasis_mark_does_not_hide_an_old_claim() -> None:
    surface = _SURFACES[0]
    excerpt, held = _OLD[surface.name]
    spaces = [at for at, char in enumerate(excerpt) if char == " "]
    assert len(spaces) > 50, "the excerpt is too short to break at every space"
    for at in spaces:
        for pad in ("\n", "\n    "):
            variant = excerpt[:at] + pad + excerpt[at + 1 :]
            problems = _problems(_planted(surface, variant), surface)
            for old in held:
                assert f"still says {old!r}" in problems, (
                    f"a break at {at} hid {old!r} in {variant!r}"
                )
    marked = excerpt.replace("that table is", "that **table** is")
    assert marked != excerpt, "the planted emphasis found nothing to mark"
    assert f"still says {_AUTHORITY!r}" in _problems(_planted(surface, marked), surface)


def test_a_missing_heading_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="no heading"):
        _problems("# Only a title\n\nsome text\n", _SURFACES[0])


def test_the_section_reader_sees_planted_text() -> None:
    planted = "\n".join(
        [
            "## Alpha",
            "first body",
            "```bash",
            "# a comment inside a fence is not a heading",
            "```",
            "after the fence",
            "### Alpha child",
            "child body",
            "## Beta",
            "second body",
        ]
    )
    alpha = _section(planted, "## Alpha", "planted")
    assert "after the fence" in alpha and "child body" in alpha
    assert "second body" not in alpha
