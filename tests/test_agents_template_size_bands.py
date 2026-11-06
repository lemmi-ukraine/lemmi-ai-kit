"""The checks of the agents template size bands tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_each_size_bullet_names_the_skills_score_band_and_no_file_count`: each size bullet names the skills score band and no file count
* `test_the_two_files_say_the_same_thing_for_the_same_bullets`: the two files say the same thing for the same bullets
* `test_a_band_that_differs_from_the_skills_is_reported`: Planted: bullets whose Medium band is the skill's old file range, and a skill whose Small band moved. Both must be reported, and the matching text must not be.
"""

import re
from pathlib import Path
from typing import NamedTuple

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_KIT = "AGENTS.md"
_TEMPLATE = "plugins/core/src/lemmi_ai_kit/assets/templates/AGENTS.md"
_FILES = (_KIT, _TEMPLATE)
_SKILL = "plugins/core/skills/spec-driven-dev/SKILL.md"
_SECTION = "### Spec-driven development"
_HEADING = re.compile(r"^(#{1,6})\s")
_LIST_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")

# The old bullets held these characters; they are built from their code points, so an assertion
# written with an ASCII hyphen could never fail on text that has the en dash.
_EN = chr(0x2013)
_ARROW = chr(0x2192)
_SIZES = ("Small", "Medium", "Large")


class _Band(NamedTuple):
    size: str
    low: int
    high: int | None

    def words(self) -> str:
        """The band as the AGENTS.md bullets spell it."""
        return (
            f"{self.low} to {self.high}"
            if self.high is not None
            else f"{self.low} or more"
        )


# What the old bullets said, and what no bullet may say again.
_OLD_COUNTS = (f"1{_EN}3 files", f"4{_EN}10 files", "10+ files")


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _section(text: str, heading: str) -> str:
    """From the first line that starts with `heading` to the next heading of the same or a higher
    level. A missing heading fails loudly, with the heading named."""
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
        raise AssertionError(f"no heading starting {heading!r}")
    return "\n".join(body)


def _bullets(section: str) -> list[str]:
    """Each list item of the section, read whole: the lines after it, indented or in column 0,
    belong to it until the next list marker, a heading or a blank line. Each is returned folded,
    so a line end put anywhere in a bullet does not make it a different bullet."""
    items: list[list[str]] = []
    open_item = False
    for line in section.split("\n"):
        if _LIST_MARKER.match(line):
            items.append([line])
            open_item = True
        elif not line.strip() or _HEADING.match(line):
            open_item = False
        elif open_item:
            items[-1].append(line)
    return [_plain(" ".join(parts)) for parts in items]


def _size_bullets(text: str) -> dict[str, str]:
    """The `- <Size> tasks (...)` bullets of the section, by size, each read whole."""
    items = _bullets(text)
    bullets: dict[str, str] = {}
    for size in _SIZES:
        lead = f"- {size} tasks ("
        found = [item for item in items if item.startswith(lead)]
        if len(found) != 1:
            raise AssertionError(
                f"expected one bullet starting {lead!r}, found {len(found)}"
            )
        bullets[size] = found[0]
    return bullets


def _skill_bands(skill_text: str) -> list[_Band]:
    """The bands from the skill's `Total score ... -> **Size**` lines, read from the folded text so
    a line end at any space of a line is the same line. Fewer than three fail loudly, so a reworded
    classification cannot leave the comparison with nothing to compare."""
    pattern = re.compile(
        rf"Total score (\d+)(?:[{_EN}-](\d+)|\+) {_ARROW} \*\*(Small|Medium|Large)\*\*"
    )
    bands = [
        _Band(m[3], int(m[1]), int(m[2]) if m[2] else None)
        for m in pattern.finditer(re.sub(r"\s+", " ", skill_text))
    ]
    if [b.size for b in bands] != list(_SIZES):
        raise AssertionError(
            f"the skill's classification lines read {bands}, not three bands"
        )
    return bands


def _band_gaps(agents_text: str, bands: list[_Band]) -> list[str]:
    """What the section lacks or still carries about the bands, in `agents_text`; an empty list is
    a pass."""
    section = _section(agents_text, _SECTION)
    bullets = _size_bullets(section)
    gaps = [
        f"{b.size}: the band '{b.words()}' is not in '{bullets[b.size]}'"
        for b in bands
        if f"{b.size} tasks (score {b.words()}," not in bullets[b.size]
    ]
    flat = _plain(section)
    gaps += [
        f"retired file count still there: {old}" for old in _OLD_COUNTS if old in flat
    ]
    return gaps


@pytest.mark.parametrize("path", _FILES)
def test_each_size_bullet_names_the_skills_score_band_and_no_file_count(
    path: str,
) -> None:
    gaps = _band_gaps(_read(path), _skill_bands(_read(_SKILL)))
    assert not gaps, f"{path}: {gaps}"


def test_the_two_files_say_the_same_thing_for_the_same_bullets() -> None:
    kit = _size_bullets(_section(_read(_KIT), _SECTION))
    template = _size_bullets(_section(_read(_TEMPLATE), _SECTION))
    assert kit == template, f"the files disagree: {kit} versus {template}"


def test_a_band_that_differs_from_the_skills_is_reported() -> None:
    """Planted: bullets whose Medium band is the skill's old file range, and a skill whose Small
    band moved. Both must be reported, and the matching text must not be."""
    skill = (
        f"- Total score 0{_EN}3 {_ARROW} **Small** {_ARROW} x\n"
        f"- Total score 4{_EN}6 {_ARROW} **Medium** {_ARROW} x\n"
        f"- Total score 7+ {_ARROW} **Large** {_ARROW} x\n"
    )
    bands = _skill_bands(skill)
    assert [b.words() for b in bands] == ["0 to 3", "4 to 6", "7 or more"]
    matching = (
        f"{_SECTION}\n- Small tasks (score 0 to 3, single concern): a.\n"
        "- Medium tasks (score 4 to 6, new components): b.\n"
        "- Large tasks (score 7 or more, multi-feature): c.\n"
    )
    assert _band_gaps(matching, bands) == []
    assert len(_band_gaps(matching, _skill_bands(_read(_SKILL)))) == 2
