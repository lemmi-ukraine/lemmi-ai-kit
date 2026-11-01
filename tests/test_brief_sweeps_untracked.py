"""A brief's tree-wide sweep counts untracked files, and says which form of grep ran.

A brief's file list is a starting set, so the worker derives its sweep from the claim and greps
"tree-wide". Plain `git grep` searches tracked files only, so a file the task created and has not
added is invisible to a "tree-wide" sweep, and under-inclusion is the failure the sweep exists to
catch. `git grep --untracked` adds such a file and still skips ignored files.

What the text says now, in the two Orchestration places of that rule:

* item 7 of `orchestrate`'s brief contract, in its file-set bullet: the sweep is grepped
  tree-wide, untracked files included (`git grep --untracked` or a working-tree grep);
* the worker preamble, in the bullet that treats the brief's file list as a starting set: the
  same words, so a worker that is pointed at the preamble and never reads the contract still
  sweeps the untracked files.

The review skill's own places for this rule belong to that skill's test; this file asserts only
the two places above.

Every check is fired at the text its place carried before (`old`), and a planted plain `git grep`
must be reported, since the old text said "tree-wide" and named no form. The plant is made
through a whitespace-tolerant pattern, so a sentence re-wrapped across two lines is planted on
and read like the same sentence. A place that goes missing fails with a message that names it,
not with an empty pass. The two helpers that find a bullet and fold its lines have a test of
their own, since every other check reads the text through them.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")
_DASH = chr(0x2014)
_EN_DASH = chr(0x2013)

_SKILLS = "plugins/orchestration/skills"
_ORCHESTRATE = f"{_SKILLS}/orchestrate/SKILL.md"
_PREAMBLE = f"{_SKILLS}/agent-delegate/assets/worker-preamble.md"
_FORM = "`git grep --untracked`"


class _Check(NamedTuple):
    label: str
    needle: str


class _Place(NamedTuple):
    name: str
    path: str
    where: str
    locate: Callable[[str], str]
    old: str


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


def _has(flat: str, needle: str) -> bool:
    return needle.lower() in flat.lower()


def _plant(text: str, phrase: str, replacement: str) -> str:
    """`text` with the one place `phrase` stands replaced, wherever a re-wrap put its line breaks.
    A phrase that stands nowhere, or more than once, fails here, so a plant that changed nothing
    cannot stand in for a check that fired."""
    pattern = r"\s+".join(re.escape(word) for word in phrase.split())
    spots = list(re.finditer(pattern, text))
    assert len(spots) == 1, (
        f"{phrase!r} stands {len(spots)} times in the text, not once"
    )
    return text[: spots[0].start()] + replacement + text[spots[0].end() :]


# The clauses do not overlap, so that removing one reports that one and no other.
_REQUIRED: tuple[_Check, ...] = (
    _Check("untracked files are in the sweep", "untracked files included"),
    _Check("the form that adds them is git grep --untracked", _FORM),
    _Check("or the sweep is a working-tree grep", "or a working-tree grep"),
)
# What has to stay: the sweep is still derived from the claim and reported as three numbers.
_KEPT: tuple[_Check, ...] = (
    _Check("the sweep is tree-wide", "tree-wide"),
    _Check(
        "N named / M actually carried it / K found outside the list",
        "K found outside the list",
    ),
)


# --- the text each place carried before -----------------------------------------------------------

_OLD_ORCHESTRATE_FILE_SET = f"""   - **The file set.** A brief's declared files are a scope boundary drawn before anyone knew where
     the fix lives; the required file was the one it omitted. The worker must derive its sweep from
     the *claim* (2{_EN_DASH}3 phrasings, grepped tree-wide) and report **"N named / M actually carried it /
     K found outside the list"** {_DASH} over-inclusion is caught free by grepping before editing, but
     under-inclusion is invisible unless someone deliberately searches outside the list.
   - **The governing documents.** A brief is not a complete statement of what governs the task:
"""

_OLD_PREAMBLE_FILE_LIST = """- **Treat your brief's file list as a starting set, not a boundary.** Derive the sweep from the
  *claim*, grep tree-wide, and report `N named / M actually carried it / K found outside the list`.
  Over-inclusion is caught free by grepping before you edit; under-inclusion is invisible unless you
  deliberately search outside the list.

### A checker you wrote this session is the least-scrutinised instrument in the task
"""


# --- the places -----------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="orchestrate-file-set",
        path=_ORCHESTRATE,
        where="the file-set bullet of item 7 of orchestrate",
        locate=_item_of("   - **The file set.**"),
        old=_OLD_ORCHESTRATE_FILE_SET,
    ),
    _Place(
        name="worker-preamble-file-list",
        path=_PREAMBLE,
        where="the file-list bullet of section 1 of the worker preamble",
        locate=_item_of("- **Treat your brief's file list as a starting set"),
        old=_OLD_PREAMBLE_FILE_LIST,
    ),
)


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    flat = _folded(region)
    gaps = [f"missing: {c.label}" for c in _REQUIRED if not _has(flat, c.needle)]
    gaps += [f"missing (kept): {c.label}" for c in _KEPT if not _has(flat, c.needle)]
    return gaps


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Two places in two files of one pack, each present and non-empty."""
    assert len(_PLACES) == 2, f"{len(_PLACES)} places, not the 2 stated"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 2, f"{len(paths)} files, not 2: {sorted(paths)}"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_tree_wide_sweep_counts_untracked_files(place: _Place) -> None:
    """Red before the change: neither place said that untracked files are in a tree-wide sweep."""
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_fails_on_the_text_a_place_carried_before(place: _Place) -> None:
    """Fired at the old text: every requirement reports it, and what has to stay is still there,
    since the old text said 'tree-wide' and named no form."""
    assert _gaps(place, place.old) == [f"missing: {c.label}" for c in _REQUIRED]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_requirement_is_load_bearing(place: _Place) -> None:
    """Removing one requirement from the real text reports that one and no other."""
    region = place.locate(_read(place.path))
    assert region.strip(), f"{place.where} is missing from {place.path}"
    flat = _folded(region)
    for check in _REQUIRED:
        start = flat.lower().find(check.needle.lower())
        assert start >= 0, f"{place.name}: {check.label!r} is not in the real text"
        stripped = flat[:start] + flat[start + len(check.needle) :]
        gaps = [c.label for c in _REQUIRED if not _has(stripped, c.needle)]
        assert gaps == [check.label], (
            f"{place.name}: removing {check.label!r} reported {gaps}"
        )


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_plain_git_grep_is_not_enough(place: _Place) -> None:
    """The planted case: the real bullet with its `--untracked` form replaced by a plain
    `git grep` is reported, so a bullet that names the command but not the flag cannot pass."""
    text = _read(place.path)
    assert _gaps(place, text) == [], (
        "the real place must pass before it can be planted on"
    )
    planted = _plant(text, _FORM, "`git grep`")
    assert _gaps(place, planted) == [
        "missing: the form that adds them is git grep --untracked"
    ]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_rewrapped_sentence_is_read_and_planted_on_like_the_same_sentence(
    place: _Place,
) -> None:
    """The form broken across two lines, as a re-wrap leaves it, passes the checks and is still
    found by the plant, which then reports it as a plain `git grep` is reported."""
    text = _read(place.path)
    rewrapped = _plant(text, _FORM, "`git grep\n     --untracked`")
    assert _gaps(place, rewrapped) == [], "a re-wrap is not a different sentence"
    planted = _plant(rewrapped, _FORM, "`git grep`")
    assert _gaps(place, planted) == [
        "missing: the form that adds them is git grep --untracked"
    ]


def test_a_plant_finds_its_phrase_wherever_a_rewrap_broke_the_line() -> None:
    """The plant itself can fail: it replaces a phrase split across lines, and it refuses a
    phrase that stands nowhere or more than once."""
    assert (
        _plant("a `git grep\n     --untracked` b", _FORM, "`git grep`")
        == "a `git grep` b"
    )
    for text in ("nothing of the kind here", f"{_FORM} and {_FORM}"):
        with pytest.raises(AssertionError, match="not once"):
            _plant(text, _FORM, "x")


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
    """The bullet finder keeps an indented and a column-zero continuation and a nested bullet,
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


def test_a_missing_place_is_a_failure_with_a_name() -> None:
    """A bullet that goes missing must not read as a pass."""
    for place in _PLACES:
        assert _gaps(place, "### Another item\n\nText.\n") == [
            f"{place.where} is missing from {place.path}"
        ]
