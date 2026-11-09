"""The seed buffer names every canonical learnings category.

`checks.LEARNINGS_SECTIONS` is the set of `## Category` headers the learnings lint accepts. A
new project's buffer starts from `assets/ai/learnings.md`, whose "How entries are added"
paragraph tells a session which categories to file an entry under. A category the lint accepts
and the seed does not name is one a new project's first sessions are never pointed at, so an
entry about it lands under a category it does not belong to, or under none.

The comparison is derived, not written: the seed's paragraph is asked for every key of the
lint's own table, so a category added to `checks.py` fails here until the seed names it, and
there is no count to keep in step.

WHAT KEEPS IT HONEST. The gap finder is fired at text built from the table itself with each
name taken out in turn, and must report that name and no other. The paragraph locator is fired
at seeds that have no such paragraph, or two, and must fail loudly instead of reading the whole
file.
"""

import re

import pytest

from lemmi_ai_kit import checks
from lemmi_ai_kit.manifest import assets_root

_SEED = assets_root() / "ai" / "learnings.md"
# The bold lead of the paragraph that lists the categories a session may file an entry under.
_LEAD = "How entries are added"


def _seed() -> str:
    """The shipped seed as text. A missing file is its own loud failure, never an empty match."""
    if not _SEED.is_file():
        raise AssertionError(f"{_SEED} does not exist")
    return _SEED.read_text(encoding="utf-8")


def _paragraph(text: str) -> str:
    """The one paragraph whose lead is `_LEAD`, with every run of whitespace folded to one space.

    A line break inside the list of names then reads as a space, so a wrapped list is found.
    Zero paragraphs or more than one fail with the count, so a renamed lead is a loud failure
    and never a search of the whole file.
    """
    found = [p for p in re.split(r"\n\s*\n", text) if _LEAD in p]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} paragraphs hold {_LEAD!r}, not 1")
    return " ".join(found[0].split())


def _gaps(paragraph: str) -> list[str]:
    """Every canonical category the paragraph does not name, in the lint's order."""
    return [name for name in checks.LEARNINGS_SECTIONS if name not in paragraph]


def test_the_seed_names_every_canonical_category() -> None:
    names = tuple(checks.LEARNINGS_SECTIONS)
    assert names, "the lint has no canonical categories, so there is nothing to compare"
    missing = _gaps(_paragraph(_seed()))
    assert not missing, (
        f"the seed's {_LEAD!r} paragraph names {len(names) - len(missing)} of "
        f"{len(names)} canonical categories; it does not name: {missing}"
    )


def test_the_gap_finder_reports_each_name_taken_out() -> None:
    """Fired at text built from the table: whole, it reports nothing, and with one name removed
    it reports that name and no other, for every name in turn."""
    names = tuple(checks.LEARNINGS_SECTIONS)
    whole = ", ".join(names)
    assert _gaps(whole) == [], "the control text is not whole"
    for name in names:
        assert _gaps(whole.replace(name, "")) == [name], name


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("# Project Learnings\n\nNothing here lists categories.\n", 0),
        (f"**{_LEAD}:** one.\n\n**{_LEAD}:** two.\n", 2),
    ],
    ids=["no paragraph", "two paragraphs"],
)
def test_the_locator_fails_loudly_unless_there_is_exactly_one_paragraph(
    text: str, count: int
) -> None:
    with pytest.raises(AssertionError, match=f"{count} paragraphs hold"):
        _paragraph(text)
