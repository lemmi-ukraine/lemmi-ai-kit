"""A change's checks run from the cheapest to the dearest, the long validation last and once.

A fix made after a check voids that check, so a change that runs its whole-suite validation before
its sweeps and its claim checks pays for the long run again after every correction the cheaper
checks find. `references/fix-rounds.md` of the `post-task-review` skill carries the order as its
third rule, and its introduction counts three rules where it counted two. The tests slice the
introduction and section 3 by their markers and headings (a missing one fails loudly), read the five
stages from the numbered list in order, and fire every check at the text it replaced: the file as it
stood with two sections (`_OLD_REFERENCE`, an excerpt of the unedited file) and a section 3 whose
long validation and acceptance run have traded places.

THE SURFACE, in numbers the tests assert: 1 file, 2 places (the introduction and section 3) and 10
checks (3 in the introduction, 7 in section 3, the stage order among them). The planted-text tests
fire each check at text that lacks it.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
)
_REFERENCE = _SKILL / "references" / "fix-rounds.md"
_GATE_OUTPUT = _SKILL / "references" / "reading-gate-output.md"
_HEADING = re.compile(r"^(#{1,6})\s")
_ITEM = re.compile(r"(?m)^(\d+)\. (.+(?:\n {2,}.+)*)")


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same.
    A missing file is its own loud failure, never an empty match."""
    if not path.is_file():
        raise AssertionError(f"{path.name} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or a
    higher level. A missing heading fails loudly, with the heading named."""
    body: list[str] = []
    level = 0
    for line in text.split("\n"):
        found = _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


def _introduction(text: str, where: str) -> str:
    """The text between the title and the first numbered heading."""
    start = text.find("\n\n")
    stop = text.find("\n## 1.")
    if start < 0 or stop < 0 or stop < start:
        raise AssertionError(
            f"{where}: no introduction before the first numbered heading"
        )
    return text[start:stop]


def _section_3(text: str, where: str) -> str:
    return _section(text, "## 3.", where)


def _stages(region: str) -> list[str]:
    """The text of each numbered item of the region, in order, folded to plain text."""
    return [_plain(item[1]) for item in _ITEM.findall(region)]


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


class _Place(NamedTuple):
    name: str
    checks: tuple[_Check, ...]
    locate: Callable[[str, str], str]


def _says(*needles: str) -> Callable[[str], bool]:
    return lambda region: all(n in _plain(region) for n in needles)


# The five stages, cheapest first, each by the words that identify it in its list item.
_STAGE_WORDS = (
    "lint and format",
    "against the code, by command",
    "count sweeps",
    "acceptance run",
    "long validation",
)


def _in_order(region: str) -> bool:
    """Five items, the nth naming the nth stage and no earlier or later one."""
    items = _stages(region)
    if len(items) != len(_STAGE_WORDS):
        return False
    for index, item in enumerate(items):
        for other, word in enumerate(_STAGE_WORDS):
            if (word in item) != (other == index):
                return False
    return True


def _last_once_frozen(region: str) -> bool:
    items = _stages(region)
    return len(items) == len(_STAGE_WORDS) and all(
        word in items[-1] for word in ("last and once", "frozen files")
    )


_PLACES: tuple[_Place, ...] = (
    _Place(
        "introduction",
        (
            _Check("the introduction counts three rules", _says("Three rules say how")),
            _Check(
                "the introduction widens its scope to the checks of any change",
                _says("the third also for the checks of any change"),
            ),
            _Check(
                "the introduction says the third costs only running order",
                _says(
                    "The first costs only reading order and the third only running order"
                ),
            ),
        ),
        _introduction,
    ),
    _Place(
        "section-3",
        (
            _Check(
                "section 3 says a fix after a check voids that check",
                _says("A fix made after a check voids that check"),
            ),
            _Check(
                "section 3 runs the checks from the cheapest to the dearest and fixes each one's findings first",
                _says(
                    "from the cheapest to the dearest",
                    "fix what each one finds before you start the next",
                ),
            ),
            _Check("section 3 lists the five stages in cost order", _in_order),
            _Check(
                "section 3 puts the long validation last, once, on frozen files",
                _last_once_frozen,
            ),
            _Check(
                "section 3 sends a review fix after the long validation back to it",
                _says(
                    "A review fix made after the long validation sends you back to it"
                ),
            ),
            _Check(
                "section 3 compares each touched file's modified time with the run's start time",
                _says(
                    "compare each touched file's modified time with the run's start time"
                ),
            ),
            _Check(
                "section 3 points at the gate-output reference by file and section number",
                _says("reading-gate-output.md, section 3"),
            ),
        ),
        _section_3,
    ),
)

# The two first paragraphs of the file as it stood at the start of the round: the introduction
# counted two rules, and the file ended with the fresh-reader section.
_OLD_REFERENCE = """# Reviewing a fix round

Step 5 of the review says to re-run the review over the diff the fixes produced. Two rules say how,
for a round of fixes to a document, plan, rule or report that others will act on. The first costs
only reading order. The second is one more agent run, so it is kept for a round that rewrote claims.

## 1. Order: the dense spots first, and every new clause against the rest of the document

Review first, and whole, any row or section where one pass applied several findings, and check each
new clause against claims elsewhere in the document.

## 2. A fresh reader, given a planted false claim

When a fix round rewrote claims others will act on, a fresh reader runs the re-review: a new agent
that re-derives each claim from the pinned source, not from the artifact's own citations, and is
given one planted false claim to reject.
"""


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text, _REFERENCE.name)
    return [c.label for c in place.checks if not c.holds(region)]


def _the_place(name: str) -> _Place:
    return next(p for p in _PLACES if p.name == name)


def _check(label_start: str) -> _Check:
    return next(c for p in _PLACES for c in p.checks if c.label.startswith(label_start))


def _swap_items(section: str, first: int, second: int) -> str:
    """The section with the bodies of two numbered items traded, numbers kept in place."""
    items = _ITEM.findall(section)
    assert len(items) > max(first, second), "the planted swap needs both items to exist"
    swapped = section
    marker = "\x00"
    swapped = swapped.replace(items[first][1], marker, 1)
    swapped = swapped.replace(items[second][1], items[first][1], 1)
    swapped = swapped.replace(marker, items[second][1], 1)
    assert swapped != section, "the planted swap changed nothing"
    return swapped


def test_the_surface_is_stated_in_numbers() -> None:
    """2 places in 1 file and 10 checks, 3 in the introduction and 7 in section 3."""
    assert len(_PLACES) == 2, f"{len(_PLACES)} places, not the 2 stated"
    checks = [c for p in _PLACES for c in p.checks]
    assert len(checks) == 10, f"{len(checks)} checks, not the 10 stated"
    assert [len(p.checks) for p in _PLACES] == [3, 7]
    assert len({c.label for c in checks}) == len(checks), "two checks share a label"
    assert len(_STAGE_WORDS) == 5


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_carries_its_rule(place: _Place) -> None:
    gaps = _gaps(place, _read(_REFERENCE))
    assert not gaps, f"{_REFERENCE.name} ({place.name}): {gaps}"


def test_the_old_introduction_fails_every_introduction_check() -> None:
    """The unedited file counted two rules and said nothing of a change's checks."""
    place = _the_place("introduction")
    reported = _gaps(place, _OLD_REFERENCE)
    assert len(reported) == len(place.checks), (
        f"{len(reported)} of {len(place.checks)} checks saw the old introduction; "
        f"blind: {[c.label for c in place.checks if c.label not in reported]}"
    )


def test_the_old_file_has_no_third_section_and_says_so_loudly() -> None:
    with pytest.raises(AssertionError, match="no heading starting '## 3.'"):
        _section_3(_OLD_REFERENCE, "old fix-rounds.md")


def test_the_order_check_reports_a_long_validation_before_the_acceptance_run() -> None:
    """The planted reorder: items 4 and 5 trade bodies, so the long validation comes before the
    acceptance run. The same swap of items 1 and 3 and a dropped item are reported too."""
    section = _section_3(_read(_REFERENCE), _REFERENCE.name)
    order = _check("section 3 lists the five stages")
    assert order.holds(section), "the real section 3 is out of order"
    assert not order.holds(_swap_items(section, 3, 4)), (
        "long validation before acceptance run"
    )
    assert not order.holds(_swap_items(section, 0, 2)), "sweeps before lint"
    dropped = re.sub(r"(?m)^2\. .*\n", "", section, count=1)
    assert dropped != section and not order.holds(dropped), "a stage is missing"


def test_the_order_check_passes_a_reworded_list_in_the_same_order() -> None:
    """The near-miss: other words around the same five stages, in the same order, still pass, so
    the check reads the order and not one fixed sentence."""
    reworded = """## 3. Anything

1. First, lint and format everything, then go on.
2. Then each claim, against the code, by command.
3. Then the count sweeps.
4. Then the acceptance run.
5. Last, the long validation, last and once, on frozen files.
"""
    assert _check("section 3 lists the five stages").holds(reworded)
    assert _check("section 3 puts the long validation last").holds(reworded)


def test_the_last_once_frozen_check_needs_each_of_its_words() -> None:
    check = _check("section 3 puts the long validation last")
    section = _section_3(_read(_REFERENCE), _REFERENCE.name)
    assert check.holds(section)
    items = _stages(section)
    for word in ("last and once", "frozen files"):
        assert items[-1].count(word) == 1, (
            f"{word!r} is not in the last item exactly once"
        )
        bare = [*items[:-1], items[-1].replace(word, "...")]
        rebuilt = "\n".join(f"{n}. {t}" for n, t in enumerate(bare, start=1))
        assert not check.holds(rebuilt), f"a section 3 without {word!r} passed"


def test_each_rule_sentence_of_section_3_is_reported_when_removed() -> None:
    """A removal check: every needle of the section's checks, taken out of the real text one at a
    time, must be reported by the check that holds it."""
    place = _the_place("section-3")
    section = _plain(_section_3(_read(_REFERENCE), _REFERENCE.name))
    needles = {
        "section 3 says a fix after a check voids that check": (
            "A fix made after a check voids that check",
        ),
        "section 3 runs the checks": (
            "from the cheapest to the dearest",
            "fix what each one finds before you start the next",
        ),
        "section 3 sends a review fix": (
            "A review fix made after the long validation sends you back to it",
        ),
        "section 3 compares each touched file's": (
            "compare each touched file's modified time with the run's start time",
        ),
        "section 3 points at the gate-output": ("reading-gate-output.md, section 3",),
    }
    for label_start, texts in needles.items():
        check = _check(label_start)
        assert check in place.checks, label_start
        for text in texts:
            assert section.count(text) == 1, (
                f"{text!r} is not in section 3 exactly once"
            )
            removed = section.replace(text, "", 1)
            assert not check.holds(removed), f"removing {text!r} went unreported"


_STEP_NUMBER = re.compile(r"(?i)\bstep \d")


def test_section_3_does_not_call_its_own_list_items_steps_of_the_review() -> None:
    """The file's first sentence says "Step 5 of the review", so a "step 5" inside section 3 reads
    as that step and not as the list's fifth item. The items are named by what they are. The
    control: the sentence as it stood is found by the same pattern."""
    section = _plain(_section_3(_read(_REFERENCE), _REFERENCE.name))
    assert _STEP_NUMBER.search(section) is None, section
    as_it_stood = "A review fix made after step 5 sends you back to step 5"
    assert _STEP_NUMBER.search(as_it_stood) is not None, "the pattern sees nothing"


def test_the_pointer_names_a_section_of_the_gate_output_reference_that_is_that_rule() -> (
    None
):
    """`reading-gate-output.md`, section 3 has to be the one about a gate that started before the
    edit it judges: a renumbered reference turns this red instead of pointing at another rule."""
    section = _section(_read(_GATE_OUTPUT), "## 3.", "reading-gate-output.md")
    heading = section.split("\n", 1)[0].lower()
    assert "predates" in heading, (
        f"section 3 of the gate-output reference is {heading!r}"
    )
    assert "started before your last edit" in _plain(section)


def test_the_first_two_sections_keep_their_numbers_and_the_third_follows() -> None:
    """The fresh-reader rule stays section 2: other references and tests name it by number."""
    text = _read(_REFERENCE)
    numbered = re.findall(r"(?m)^## (\d+)\. ", text)
    assert numbered[:3] == ["1", "2", "3"], numbered
    assert (
        "fresh reader"
        in _section(text, "## 2.", _REFERENCE.name).split("\n", 1)[0].lower()
    )


def test_a_missing_marker_heading_or_file_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="no heading"):
        _section("## 1. Only one\ntext\n", "## 3.", "planted")
    with pytest.raises(AssertionError, match="no introduction"):
        _introduction("# Title only", "planted")
    planted = "## 3. A\nOrder text\n### 3.1 sub\nmore\n## 4. B\nOther\n"
    assert "more" in _section(planted, "## 3.", "planted")
    assert "Other" not in _section(planted, "## 3.", "planted")
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-reference.md"))


def test_the_needle_helper_needs_every_needle_it_is_given() -> None:
    """`_says` holds only when every needle is there: fired at a region that holds one of two."""
    region = "alpha and beta, not gamma"
    assert _says("alpha", "beta")(region)
    assert not _says("alpha", "delta")(region)
