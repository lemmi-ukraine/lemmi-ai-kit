"""The brief contract's item 8 title states its own exceptions, and agent-delegate stops listing items.

Item 8 of `orchestrate`'s brief contract is titled "do not restate the rules inline, and require
the report to be written incrementally". Both halves were later given exceptions in the body of
the item: two harness limits are restated, because a worker meets them on its first command and
its last write, and "write your report early" applies only to a worker that may write. The title
still said both without a condition, beside the exceptions.

`agent-delegate`'s Process step 2 paraphrased the same title and enumerated contract items 5 to 9
by number. The contract has grown since, so any list of its items in a second file is stale the
day an item is added, and it repeated the unqualified title.

What the text says now:

* the title of item 8 qualifies both halves: the two harness limits are excepted from "do not
  restate", and the report is written incrementally if the worker may write;
* step 2 of `agent-delegate` says that every item of the contract applies here, names no item by
  number, no longer paraphrases the item 8 title, and still links the worker preamble, which
  lives in that skill, and still carries the paragraph on boilerplate host rules.

Every check is fired at the text its place carried before (`old`): each requirement reports it
and each retired phrase is seen. Each requirement is also removed from the real text one at a
time and must be the only thing reported. Step 2 of `agent-delegate` has no requirement of its
own, only retired phrases and wording that has to stay, so it is left out of that removal test.
The two helpers that find an item and fold its lines have a test of their own, since every check
reads the text through them.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_FENCED = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_DASH = chr(0x2014)
_SECT = chr(0xA7)

_SKILLS = "plugins/orchestration/skills"
_ORCHESTRATE = f"{_SKILLS}/orchestrate/SKILL.md"
_DELEGATE = f"{_SKILLS}/agent-delegate/SKILL.md"
_PREAMBLE = f"{_SKILLS}/agent-delegate/assets/worker-preamble.md"
_ITEM_8_LEAD = "8. **Point the worker at the preamble FILE"
_STEP_2_LEAD = "2. **Brief.**"


class _Check(NamedTuple):
    label: str
    needle: str


class _Place(NamedTuple):
    name: str
    path: str
    where: str
    locate: Callable[[str], str]
    required: tuple[_Check, ...]
    old: str
    retired: tuple[_Check, ...] = ()
    kept: tuple[_Check, ...] = ()
    # A link from the place to this file is required (a path relative to the repository root).
    links_to: str = ""


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space, so a re-wrapped
    line or a re-emphasised word is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _list_item(text: str, lead: str) -> str:
    """The first line that starts with `lead` and the lines that belong to it: every line after
    it up to the next heading, up to the next list marker at the same or a shallower indent, and,
    after a blank line, up to the next line that is not indented. A continuation line stays in
    whether it is indented or sits in column 0, so a re-wrapped item is read whole. Empty when no
    line starts with `lead`."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if not line.startswith(lead):
            continue
        item = [line]
        after_blank = False
        for follow in lines[index + 1 :]:
            if not follow.strip():
                item.append(follow)
                after_blank = True
                continue
            shallow = _indent(follow) <= _indent(line)
            if _HEADING.match(follow) or (
                shallow and (_MARKER.match(follow) is not None or after_blank)
            ):
                break
            item.append(follow)
            after_blank = False
        return "\n".join(item)
    return ""


def _item_of(lead: str) -> Callable[[str], str]:
    return lambda text: _list_item(text, lead)


def _title_of_item_8(text: str) -> str:
    """The title of item 8: the item up to its 'Two clauses' lead-in. Empty when the item or the
    lead-in is missing, so a title that loses its place cannot pass by being absent."""
    item = _list_item(text, _ITEM_8_LEAD)
    title, found, _ = item.partition("Two clauses")
    return title if found else ""


def _has(flat: str, needle: str) -> bool:
    return needle.lower() in flat.lower()


def _links_to(region: str, path: str, target: str) -> bool:
    """Whether a prose link of `region` points at the file `target`, resolved from `path`."""
    base = (_REPO_ROOT / path).parent
    wanted = (_REPO_ROOT / target).resolve()
    for link in _LINK.findall(_FENCED.sub("", region)):
        name = link.split("#", 1)[0]
        if name and "://" not in name and (base / name).resolve() == wanted:
            return True
    return False


def _flat_problems(place: _Place, flat: str) -> list[str]:
    problems = [
        f"missing: {c.label}" for c in place.required if not _has(flat, c.needle)
    ]
    problems += [
        f"missing (kept): {c.label}" for c in place.kept if not _has(flat, c.needle)
    ]
    problems += [
        f"retired wording still there: {c.label}"
        for c in place.retired
        if _has(flat, c.needle)
    ]
    return problems


def _problems(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    problems = _flat_problems(place, _folded(region))
    if place.links_to and not _links_to(region, place.path, place.links_to):
        problems.append(f"missing: a link to {place.links_to}")
    return problems


def _expected_on_old(place: _Place) -> list[str]:
    expected = [f"missing: {c.label}" for c in place.required]
    expected += [f"retired wording still there: {c.label}" for c in place.retired]
    return expected


# --- the text each place carried before -----------------------------------------------------------

_OLD_ITEM_8_TITLE = f"""8. **Point the worker at the preamble FILE {_DASH} do not restate the rules inline, and require the
   report to be written incrementally.** Two clauses, both measured:

   - *Point, don't paste.* Give the worker the path to the preamble.

9. **The close block {_DASH} paste it verbatim into every brief.**
"""

_OLD_STEP_2 = f"""2. **Brief.** Write the brief per the contract {_DASH} one concern, inlined context, self-checkable
   definition of done, short report format. The contract itself is
   `../orchestrate/SKILL.md` {_SECT} "The brief contract" (**every** item applies here,
   including the DoD's zero-hit-grep self-check, the discriminating-token rule for presence checks,
   item 5's "the completion checklist is ALWAYS in scope regardless of the declared file set",
   item 6's target-branch assertion before every commit, item 7's "every list in the brief is a
   starting set" {_DASH} file set, governing documents, and blockers all age {_DASH} item 8's *point the worker
   at [`assets/worker-preamble.md`](assets/worker-preamble.md) rather than restating rules inline,
   and require the report to be written incrementally*, and item 9's **close block, pasted verbatim**
   plus the three operator-interface rules);
   template: `../orchestrate/references/brief-template.md`. If the task needs decisions
   the brief can't pin down, surface that to the user instead of delegating mush.
   **Boilerplate host rules are copied; the MEASUREMENTS inside them are not transferable.** One
   brief carried the correct rule.
3. **Mode.** Opinion/analysis (`--second-opinion`, reviews, diagnosis) {_DASH} read-only mode.
"""


# --- the places -----------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="orchestrate-item-8-title",
        path=_ORCHESTRATE,
        where="the title of item 8 of the brief contract in orchestrate",
        locate=_title_of_item_8,
        required=(
            _Check(
                "the two harness limits are excepted from 'do not restate'",
                "(the two harness limits excepted)",
            ),
            _Check(
                "the report is written incrementally if the worker may write",
                "incrementally if it may write",
            ),
        ),
        old=_OLD_ITEM_8_TITLE,
        retired=(
            _Check(
                "'do not restate the rules inline' with no exception",
                "do not restate the rules inline, and require",
            ),
        ),
        kept=(
            _Check(
                "point the worker at the preamble file",
                "Point the worker at the preamble FILE",
            ),
        ),
    ),
    _Place(
        name="agent-delegate-step-2",
        path=_DELEGATE,
        where="step 2 of the Process of agent-delegate",
        locate=_item_of(_STEP_2_LEAD),
        required=(),
        old=_OLD_STEP_2,
        retired=(
            _Check("an item is named by number: item 5", "item 5's"),
            _Check("an item is named by number: item 6", "item 6's"),
            _Check("an item is named by number: item 7", "item 7's"),
            _Check("an item is named by number: item 8", "item 8's"),
            _Check("an item is named by number: item 9", "item 9's"),
            _Check("the zero-hit-grep enumeration", "zero-hit-grep self-check"),
            _Check(
                "the unqualified paraphrase of the item 8 title",
                "rather than restating rules inline, and require the report to be written "
                "incrementally",
            ),
        ),
        kept=(
            _Check(
                "every item of the contract applies here", "every item applies here"
            ),
            _Check(
                "boilerplate host rules are copied, their measurements are not",
                "Boilerplate host rules are copied",
            ),
        ),
        links_to=_PREAMBLE,
    ),
)

# The places that carry a requirement of their own. Step 2 of agent-delegate has none: it is judged
# by its retired phrases and by what has to stay, so removing a requirement from it is not a test
# that can run.
_WITH_REQUIREMENTS = tuple(place for place in _PLACES if place.required)


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Two places in two files of one pack, each present and non-empty."""
    assert len(_PLACES) == 2, f"{len(_PLACES)} places, not the 2 stated"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 2, f"{len(paths)} files, not 2: {sorted(paths)}"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"
    assert len(_WITH_REQUIREMENTS) == 1, (
        f"{len(_WITH_REQUIREMENTS)} places with a requirement of their own, not the 1 stated"
    )
    assert [p.name for p in _PLACES if not p.required] == ["agent-delegate-step-2"]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_the_brief_contract_is_pointed_at_without_restating_it(place: _Place) -> None:
    """Red before the change: the title had no exception and step 2 named items by number."""
    problems = _problems(place, _read(place.path))
    assert not problems, f"{place.path} ({place.name}): {problems}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_fails_on_the_text_it_replaced(place: _Place) -> None:
    """Fired at the old text: every requirement reports it, every retired phrase is seen, and
    what has to stay is still there."""
    reported = _problems(place, place.old)
    expected = _expected_on_old(place)
    if place.links_to:
        # The old step 2 already linked the preamble, so the link is not among the gaps.
        assert _links_to(place.locate(place.old), place.path, place.links_to)
    assert reported == expected, (
        f"{place.name}: on the old text the checks reported {reported}"
    )


@pytest.mark.parametrize(
    "place", _WITH_REQUIREMENTS, ids=[p.name for p in _WITH_REQUIREMENTS]
)
def test_each_requirement_is_load_bearing(place: _Place) -> None:
    """Removing one requirement from the real text reports that one and no other. A place with
    no requirement has nothing to remove, so it is not run through this test: a loop over an
    empty tuple would pass whatever the text said."""
    assert place.required, f"{place.name} has no requirement to remove"
    region = place.locate(_read(place.path))
    assert region.strip(), f"{place.where} is missing from {place.path}"
    flat = _folded(region)
    for check in place.required:
        start = flat.lower().find(check.needle.lower())
        assert start >= 0, f"{place.name}: {check.label!r} is not in the real text"
        stripped = flat[:start] + flat[start + len(check.needle) :]
        gaps = [c.label for c in place.required if not _has(stripped, c.needle)]
        assert gaps == [check.label], (
            f"{place.name}: removing {check.label!r} reported {gaps}"
        )


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_retired_phrase_is_seen_when_it_comes_back(place: _Place) -> None:
    """The real text passes; the same text with one retired phrase added back is reported, and
    that phrase is the only thing reported."""
    region = place.locate(_read(place.path))
    assert region.strip(), f"{place.where} is missing from {place.path}"
    flat = _folded(region)
    assert _flat_problems(place, flat) == [], (
        "the real place must pass before it can be planted on"
    )
    for check in place.retired:
        planted = f"{flat} {check.needle}"
        assert _flat_problems(place, planted) == [
            f"retired wording still there: {check.label}"
        ], check.label


def test_the_title_reader_stops_at_the_lead_in_of_the_item() -> None:
    """The title is read up to 'Two clauses' and no further: a sentence of the body does not
    stand in for the title, and an item without the lead-in is reported missing."""
    item = "\n".join(
        [
            f"{_ITEM_8_LEAD} {_DASH} do not restate.** Two clauses, both measured:",
            "",
            "   (the harness limits excepted)",
            "",
        ]
    )
    title = _title_of_item_8(item)
    assert "do not restate" in title
    assert "harness limits excepted" not in title
    assert _title_of_item_8(f"{_ITEM_8_LEAD} {_DASH} do not restate.**\n") == ""


def test_a_link_to_a_missing_file_is_not_a_link_to_the_preamble() -> None:
    """The link check can fail: a real link is found; a link to a missing file, a link to
    another file that exists and a link inside a fenced block are not."""
    linked = "See [`assets/worker-preamble.md`](assets/worker-preamble.md)."
    assert _links_to(linked, _DELEGATE, _PREAMBLE)
    for text in (
        "See [preamble](assets/no-such-file.md).",
        "See [preamble](references/hand-back-and-stamps.md).",
        "```\n[preamble](assets/worker-preamble.md)\n```",
    ):
        assert not _links_to(text, _DELEGATE, _PREAMBLE), text


def test_a_missing_place_is_a_failure_with_a_name() -> None:
    """An item that goes missing must not read as a pass."""
    for place in _PLACES:
        assert _problems(place, "### Another section\n\nText.\n") == [
            f"{place.where} is missing from {place.path}"
        ]


def test_the_fold_joins_a_rewrapped_sentence_and_drops_bold_marks() -> None:
    """Every check reads the text through the fold: lines join, a run of spaces is one space,
    bold marks go, the ends are trimmed."""
    assert _folded("  a **bold**  word\n     and a second\nline  \n") == (
        "a bold word and a second line"
    )


_TWO_ITEMS = "\n".join(
    [
        "- **First.** one",
        "  wrapped and indented",
        "wrapped in column zero",
        "  - nested stays inside",
        "- **Second.** two",
        "",
        "Not part of any item.",
        "",
    ]
)


def test_a_list_item_runs_to_the_next_item_and_keeps_its_wrapped_lines() -> None:
    """The item finder keeps an indented and a column-zero continuation and a nested bullet,
    stops at the next bullet of its own level, at a heading, and after a blank line at the first
    line that is not indented, and finds nothing for a lead that is not there."""
    first = _list_item(_TWO_ITEMS, "- **First.**")
    for kept in (
        "wrapped and indented",
        "wrapped in column zero",
        "nested stays inside",
    ):
        assert kept in first, first
    assert "two" not in first, first
    second = _list_item(_TWO_ITEMS, "- **Second.**")
    assert "two" in second and "Not part of any item" not in second, second
    assert "heading" not in _list_item(
        "- **Only.** one\n### A heading\n", "- **Only.**"
    )
    assert _list_item(_TWO_ITEMS, "- **Third.**") == ""
