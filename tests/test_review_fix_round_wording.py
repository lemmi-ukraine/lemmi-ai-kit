"""A fix round is re-reviewed in an order, and by a fresh reader when it rewrote claims.

Step 5 of `post-task-review` said to "re-run the review over the diff the fixes produced", and named
neither the order nor the reader. Two rules were measured to matter. The defects of a fix round sit
where one pass applied several findings at once, because each new clause is general enough for the
rest of the document to contradict it; and a reader that did the fix-up reads its own wording as
correct, so a round that rewrote claims others will act on needs a new agent that re-derives each
claim from the pinned source and is given one planted false claim to reject. That reader is one more
agent run, so its brief is capped: at most four real claims, plus the planted one, which the cap
does not count (a Core-only project reads this reference with no other statement of a cap).

The text sits in `references/fix-rounds.md`, and Step 5 carries one link to it on the line that
already closes the item, so the SKILL.md grows by no line. The tests slice the Step 5 item of the
skill and the two sections of the reference by their markers and headings (a missing one fails
loudly), assert each rule where it belongs, and fire every check at the text it replaced: the Step 5
item as it stood (`_OLD_STEP_5`, an unedited excerpt) and a reference that has the two headings and
neither rule (`_STUB_REFERENCE`).

THE SURFACE, in numbers the tests assert: 3 places in 2 files (the Step 5 item of SKILL.md, and
sections 1 and 2 of the reference) and 5 checks: 1 for the link and 4 for the rules in their two
sections. The planted-text tests fire each check at text that lacks it.
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
_SKILL_MD = _SKILL / "SKILL.md"
_REFERENCE = _SKILL / "references" / "fix-rounds.md"
_HEADING = re.compile(r"^(#{1,6})\s")

_STEP_5_START = "5. **Document Findings and Implement Fixes**"
_STEP_5_END = "6. **Run Linting and Diagnostics**"
_LINK = "(references/fix-rounds.md)"


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same.
    A missing file is its own loud failure, never an empty match."""
    if not path.is_file():
        raise AssertionError(f"{path.name} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _between(text: str, start: str, end: str, where: str) -> str:
    begin = text.find(start)
    if begin < 0:
        raise AssertionError(f"{where}: no marker {start!r}")
    stop = text.find(end, begin)
    if stop < 0:
        raise AssertionError(f"{where}: no marker {end!r} after {start!r}")
    return text[begin:stop]


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


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


class _Place(NamedTuple):
    name: str
    path: Path
    checks: tuple[_Check, ...]
    locate: Callable[[str, str], str]
    old: str


def _links(region: str) -> bool:
    return _LINK in region


def _says(*needles: str) -> Callable[[str], bool]:
    return lambda region: all(n in _plain(region) for n in needles)


_ORDER = (
    "Review first, and whole, any row or section where one pass applied several findings, "
    "and check each new clause against claims elsewhere in the document"
)
_FRESH_READER = (
    "When a fix round rewrote claims others will act on, a fresh reader runs the re-review: "
    "a new agent that re-derives each claim from the pinned source, not from the artifact's "
    "own citations, and is given one planted false claim to reject"
)
_CAP = "at most four real claims, plus the planted one"
_CAP_LABEL = "section 2 caps the fresh reader's brief at four real claims, the planted one outside the cap"

_OLD_STEP_5 = r"""5. **Document Findings and Implement Fixes** — Fix each issue found with clear reasoning.
   **The fix pass is not safer than the original work, and the review that produced the fixes does
   not certify them.** Measured three times independently: a stacked-PR research round where *each*
   verification pass found defects introduced by the previous pass's fixes (2026-08-04); a prompt
   review whose fixes "introduced defects at roughly the rate they resolved them" (2026-08-19, RG1);
   and a plan revision whose second pass found three errors, **all three introduced by the first
   pass's own correction** (2026-08-19). So: re-run the review over the diff the fixes produced, not
   over the original artifact, and **re-derive every figure a fix touched** rather than carrying the
   pre-fix number forward. A correction carries more authority than the claim it replaces, which is
   what makes an unreviewed fix round expensive.
6. **Run Linting and Diagnostics** — `ruff check --fix` on all modified files, `read_lints` on all modified files.
"""

# The two headings and none of the rules: a reference that exists but says nothing.
_STUB_REFERENCE = """# Reviewing a fix round

## 1. Order: the dense spots first

Review the diff.

## 2. A fresh reader, given a planted false claim

Ask someone.
"""


def _step_5(text: str, where: str) -> str:
    return _between(text, _STEP_5_START, _STEP_5_END, where)


def _section_1(text: str, where: str) -> str:
    return _section(text, "## 1.", where)


def _section_2(text: str, where: str) -> str:
    return _section(text, "## 2.", where)


_PLACES: tuple[_Place, ...] = (
    _Place(
        "skill-step-5",
        _SKILL_MD,
        (_Check("Step 5 links references/fix-rounds.md", _links),),
        _step_5,
        _OLD_STEP_5,
    ),
    _Place(
        "reference-section-1",
        _REFERENCE,
        (_Check("section 1 states the order and the cross-check", _says(_ORDER)),),
        _section_1,
        _STUB_REFERENCE,
    ),
    _Place(
        "reference-section-2",
        _REFERENCE,
        (
            _Check("section 2 states the fresh reader", _says(_FRESH_READER)),
            _Check(
                "section 2 says the planted claim is a control to trust only if rejected",
                _says(
                    "trust the reader's confirmations only if it rejected the planted claim"
                ),
            ),
            _Check(_CAP_LABEL, _says(_CAP)),
        ),
        _section_2,
        _STUB_REFERENCE,
    ),
)


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text, place.path.name)
    return [c.label for c in place.checks if not c.holds(region)]


def test_the_surface_is_stated_in_numbers() -> None:
    """3 places over 2 files and 5 checks, the Step 5 link included."""
    assert len(_PLACES) == 3, f"{len(_PLACES)} places, not the 3 stated"
    assert len({p.path for p in _PLACES}) == 2, "the places are not in 2 distinct files"
    checks = [c for p in _PLACES for c in p.checks]
    assert len(checks) == 5, f"{len(checks)} checks, not the 5 stated"
    assert len({c.label for c in checks}) == len(checks), "two checks share a label"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_carries_its_rule(place: _Place) -> None:
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path.name} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The old Step 5 item has no link and the stub has no rule, so every check must say so."""
    reported = _gaps(place, place.old)
    assert len(reported) == len(place.checks), (
        f"{place.name}: {len(reported)} of {len(place.checks)} checks saw the old text; "
        f"blind: {[c.label for c in place.checks if c.label not in reported]}"
    )


def test_the_link_is_on_the_step_5_item_and_the_target_is_a_reference_of_the_skill() -> (
    None
):
    """The link has to be inside the item (not after it), and the file it names has to exist."""
    text = _read(_SKILL_MD)
    item = _between(text, _STEP_5_START, _STEP_5_END, "SKILL.md")
    assert item.count(_LINK) == 1
    assert (_SKILL / "references" / "fix-rounds.md").is_file()
    assert text.count(_LINK) == 1, "the link appears outside Step 5 as well"


def test_a_missing_marker_heading_or_file_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="no marker"):
        _between("text without the item", _STEP_5_START, _STEP_5_END, "planted")
    with pytest.raises(AssertionError, match="no heading"):
        _section("## 1. Only one\ntext\n", "## 2.", "planted")
    planted = "## 1. A\nOrder text\n### 1.1 sub\nmore\n## 2. B\nOther\n"
    assert "more" in _section(planted, "## 1.", "planted")
    assert "Other" not in _section(planted, "## 1.", "planted")
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-reference.md"))


def test_the_cap_check_needs_the_planted_claim_outside_the_four() -> None:
    """Fired at planted sentences: a cap that never says "real", one that counts the planted claim
    among the four, one with no planted claim and the cap whole. The cap of the Orchestration pack
    does not say whether its controls count; here the planted claim is outside the four."""
    check = next(c for p in _PLACES for c in p.checks if c.label == _CAP_LABEL)
    assert check.holds(
        "Its brief carries at most four real claims, plus the planted one."
    )
    for text in (
        "Its brief carries at most four claims per pass.",
        "Its brief carries at most four real claims.",
        "Its brief carries at most four claims, the planted one included.",
        "Its brief carries four real claims, plus the planted one.",
    ):
        assert not check.holds(text), text


def test_the_needle_helper_needs_every_needle_it_is_given() -> None:
    """`_says` holds only when every needle is there. Every check here passes one needle, so the
    join is fired at a region that holds one of two: a helper that settled for any needle would
    pass it."""
    region = "alpha and beta, not gamma"
    assert _says("alpha", "beta")(region)
    assert not _says("alpha", "delta")(region)
