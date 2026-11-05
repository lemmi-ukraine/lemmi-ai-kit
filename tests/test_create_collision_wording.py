"""A path believed new can exist at the write: the create collision, and only that rule.

The safety skill's alarm for a collision was a failed edit on an owned file, and the dispatch gate
kept an existence check "as a STOP precondition", run once at the start. A path checked absent an
hour earlier can be a peer's by the time it is written, and a write tool that answers "replaced"
instead of "created" is the only sign. Neither pack said how to create a file only if it is absent,
or what the created-or-replaced answer means.

What the text says now, in four places of the Orchestration pack:

* subsection 12k of the shared-index reference: a path checked absent earlier can exist at the
  write; create it with an operation that fails if it exists, or read the write tool's
  created-or-replaced answer where it gives one; "replaced" on a path believed new is a
  collision: stop, do not write again, and report it so the other writer can restore its content;
* section 3 of `SKILL.md` carries one pointer line to 12k, and the section 12 pointer names the id.
  The line is a paragraph of its own after the list about a stale-read failure: the create
  collision is another alarm, so it is not an item that the lead-in about a stale read introduces;
* section 5 of the dispatch gates adds: repeat the check at the write.

This file asserts that rule and nothing else. A hand-off stub written before the preconditions is a
separate rule, pinned in tests/test_handoff_stub_wording.py, so no place of it is read here: the
agent-delegate list, the brief template and section 6 of the dispatch gates are untouched by this
file.

Every check is fired at the text its place carried before (`old`), and each requirement is removed
from the real text one at a time and must be the only thing reported. The section 12 pointer has
no wording of its own, only the id and the link, so it is left out of that removal test. The
helpers that find a section, a pointer and fold the lines have a test of their own, since every
check reads the text through them.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_FENCED = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_DASH = chr(0x2014)
_ID = "12k"
_POINTER_MARK = "can exist at the write"

_SKILLS = "plugins/orchestration/skills"
_SAFETY = f"{_SKILLS}/parallel-session-safety/SKILL.md"
_REFERENCE = f"{_SKILLS}/parallel-session-safety/references/shared-index-protocol.md"
_GATES = f"{_SKILLS}/orchestrate/references/dispatch-gates.md"


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
    # The place must name the id and link the reference file.
    linked: bool = False
    # The old text already carried a link to the reference file (the section 12 pointer).
    old_linked: bool = False
    # Wording that has to stay: it is on the old text too, and must still be on the new.
    kept: tuple[_Check, ...] = ()


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space, so a re-wrapped
    line or a re-emphasised word is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _section_of(heading: str) -> Callable[[str], str]:
    return lambda text: _section(text, heading)


def _blockquote_of(heading: str) -> Callable[[str], str]:
    """The blockquote lines of the section: the pointer to the reference."""

    def locate(text: str) -> str:
        lines = _section(text, heading).split("\n")
        return "\n".join(line for line in lines if line.startswith(">"))

    return locate


def _has(flat: str, needle: str) -> bool:
    return needle.lower() in flat.lower()


def _links_the_reference(region: str, path: str) -> bool:
    """Whether a prose link of `region` points at the reference file, resolved from `path`."""
    base = (_REPO_ROOT / path).parent
    wanted = (_REPO_ROOT / _REFERENCE).resolve()
    for link in _LINK.findall(_FENCED.sub("", region)):
        name = link.split("#", 1)[0]
        if name and "://" not in name and (base / name).resolve() == wanted:
            return True
    return False


def _problems(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    flat = _folded(region)
    problems = [
        f"missing: {c.label}" for c in place.required if not _has(flat, c.needle)
    ]
    problems += [
        f"missing (kept): {c.label}" for c in place.kept if not _has(flat, c.needle)
    ]
    if place.linked:
        if not re.search(rf"\b{_ID}\b", flat):
            problems.append(f"missing: the id {_ID}")
        if not _links_the_reference(region, place.path):
            problems.append("missing: a link to a reference file that exists")
    return problems


def _placement(region: str) -> list[str]:
    """Where the pointer stands in section 3. The section opens with a lead-in about a stale-read
    failure and a list that continues it. The create collision is another alarm, so its pointer
    is a paragraph after that list, set off by a blank line, and not an item the lead-in seems to
    introduce. One line per way it can stand wrong; empty when it stands right."""
    lines = region.split("\n")
    marked = [i for i, line in enumerate(lines) if _POINTER_MARK in line]
    if len(marked) != 1:
        return [f"the pointer is on {len(marked)} lines, not 1"]
    at = marked[0]
    items = [i for i, line in enumerate(lines) if _LIST_ITEM.match(line)]
    problems: list[str] = []
    if not items:
        problems.append("section 3 has no list for the pointer to follow")
    if at in items:
        problems.append("the pointer is an item of the list")
    if items and at < max(items):
        problems.append("the pointer stands before the last item of the list")
    if at > 0 and lines[at - 1].strip():
        problems.append("the pointer has no blank line before it")
    return problems


# --- the text each place carried before -----------------------------------------------------------

_OLD_SAFETY_3 = f"""## 3. "Modified since read" is a collision alarm, not an annoyance

Treat a stale-read failure on an **owned** file as possible pre-completion:

- **Re-read** the file.
- **Verify** current state against the spec / source-of-truth.
- If it already satisfies the target: **VERIFY-don't-reapply.** Re-applying the drafted edit
  overwrites concurrent work and can clobber a cleaner version.
- Still run the required gate and a fresh final-state grep {_DASH} the files mutated under you.
- **Report provenance honestly**: "verified, not authored".

## 3b. VERIFY-don't-reapply has a BRANCH-level twin
"""

# Section 3 with the pointer put in each way: as the last item of the list (where it first stood),
# after the list as a paragraph of its own (where it stands now), before the lead-in, and on the
# line after the last item with no blank line, which a markdown reader folds into that item.
_CREATE_POINTER = (
    "**A path believed new can exist at the write:** create it only if absent "
    "([12k](references/shared-index-protocol.md))."
)
_HEADING_3 = '## 3. "Modified since read" is a collision alarm, not an annoyance'
_LEAD_IN = "Treat a stale-read failure on an **owned** file as possible pre-completion:"
_STALE_READ_LIST = f"""- **Re-read** the file.
- **Verify** current state against the spec / source-of-truth.
- If it already satisfies the target: **VERIFY-don't-reapply.** Re-applying the drafted edit
  overwrites concurrent work and can clobber a cleaner version.
- Still run the required gate and a fresh final-state grep {_DASH} the files mutated under you.
- **Report provenance honestly**: "verified, not authored"."""
_NEXT_SECTION = "## 3b. VERIFY-don't-reapply has a BRANCH-level twin\n"

_POINTER_AS_AN_ITEM = f"{_HEADING_3}\n\n{_LEAD_IN}\n\n{_STALE_READ_LIST}\n- {_CREATE_POINTER}\n\n{_NEXT_SECTION}"
_POINTER_AFTER_THE_LIST = f"{_HEADING_3}\n\n{_LEAD_IN}\n\n{_STALE_READ_LIST}\n\n{_CREATE_POINTER}\n\n{_NEXT_SECTION}"
_POINTER_BEFORE_THE_LIST = f"{_HEADING_3}\n\n{_CREATE_POINTER}\n\n{_LEAD_IN}\n\n{_STALE_READ_LIST}\n\n{_NEXT_SECTION}"
_POINTER_RUN_ON = f"{_HEADING_3}\n\n{_LEAD_IN}\n\n{_STALE_READ_LIST}\n{_CREATE_POINTER}\n\n{_NEXT_SECTION}"

_OLD_GATES_5 = f"""## 5. One kickoff block, one dispatch CHANNEL {_DASH} name it, because nothing else records ownership

**The collision was survived only because the brief carried a deliverable-path existence
check as a STOP precondition**, so the second run wrote to scratch instead of overwriting. So: state
per block *"the orchestrator dispatches this"* or *"the operator pastes this"*, never both; keep the
deliverable-path STOP precondition in every brief; and check the escalation file and the deliverable
path before auto-dispatching.

## 6. Designing the gates that guard a dispatch
"""

_OLD_POINTER = """## 12. The index is shared

> **Five measured failure modes, with the exact commands for each, are in
> [references/shared-index-protocol.md](references/shared-index-protocol.md):** contention is
> per-LINE and defeats both standard guards (12a); a held index is a lock that blocked four
> planned sessions (12b); work done AFTER staging silently invalidates the staged set (12c);
> `git push` answering "Everything up-to-date" means you are not on that branch (12d); and how
> to back up a tree for a multi-branch history operation (12e).

## Cross-references
"""


# --- the places -----------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="reference-12k",
        path=_REFERENCE,
        where="subsection 12k of the reference",
        locate=_section_of("### 12k."),
        required=(
            _Check(
                "a path checked absent earlier can exist at the write",
                "A path checked absent earlier can exist at the write",
            ),
            _Check(
                "create it with an operation that fails if it exists",
                "Create it with an operation that fails if it exists",
            ),
            _Check(
                "or read the write tool's created-or-replaced answer where it gives one",
                "read the write tool's created-or-replaced answer where it gives one",
            ),
            _Check(
                "replaced on a path believed new is a collision",
                "Replaced on a path believed new is a collision",
            ),
            _Check(
                "stop, do not write again, and report it so the other writer can restore",
                "stop, do not write again, and report it so the other writer can restore "
                "its content",
            ),
        ),
        old="",
    ),
    _Place(
        name="safety-section-3-pointer",
        path=_SAFETY,
        where="section 3 of the safety skill",
        locate=_section_of("## 3."),
        required=(
            _Check(
                "a path believed new can exist at the write", "can exist at the write"
            ),
            _Check("create it only if absent", "create it only if absent"),
        ),
        old=_OLD_SAFETY_3,
        linked=True,
    ),
    _Place(
        name="safety-section-12-pointer",
        path=_SAFETY,
        where="the pointer of section 12 of the safety skill",
        locate=_blockquote_of("## 12."),
        required=(),
        old=_OLD_POINTER,
        linked=True,
        old_linked=True,
    ),
    _Place(
        name="dispatch-gates-section-5",
        path=_GATES,
        where="section 5 of the dispatch gates",
        locate=_section_of("## 5."),
        required=(
            _Check("repeat the check at the write", "repeat the check at the write"),
        ),
        old=_OLD_GATES_5,
        linked=True,
        kept=(
            _Check(
                "the existence check stays a STOP precondition in every brief",
                "keep the deliverable-path STOP precondition in every brief",
            ),
        ),
    ),
)

# The places that carry wording of their own. The section 12 pointer has none: it is judged by the
# id and the link alone, so removing a requirement from it is not a test that can run.
_WITH_REQUIREMENTS = tuple(place for place in _PLACES if place.required)


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Four places in three files of the Orchestration pack, each present and non-empty."""
    assert len(_PLACES) == 4, f"{len(_PLACES)} places, not the 4 stated"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 3, f"{len(paths)} files, not 3: {sorted(paths)}"
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"
    assert len(_WITH_REQUIREMENTS) == 3, (
        f"{len(_WITH_REQUIREMENTS)} places with wording of their own, not the 3 stated"
    )
    assert [p.name for p in _PLACES if not p.required] == ["safety-section-12-pointer"]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_states_the_create_collision_rule(place: _Place) -> None:
    """Red before the change: no place said a checked-absent path can exist at the write."""
    problems = _problems(place, _read(place.path))
    assert not problems, f"{place.path} ({place.name}): {problems}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_fails_on_the_text_it_replaced(place: _Place) -> None:
    """Fired at the old text: every requirement, the id and the link report it, and what has to
    stay is still there. Subsection 12k is new, so its old text is empty and the place itself is
    what is reported missing."""
    reported = _problems(place, place.old)
    if not place.old:
        assert reported == [f"{place.where} is missing from {place.path}"]
        return
    expected = [f"missing: {c.label}" for c in place.required]
    if place.linked:
        expected.append(f"missing: the id {_ID}")
        if not place.old_linked:
            expected.append("missing: a link to a reference file that exists")
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


def test_the_pointer_is_a_paragraph_after_the_stale_read_list() -> None:
    """Red before the change: the pointer was the last item of the list that the lead-in about a
    stale-read failure introduces, and it does not continue that lead-in."""
    region = _section(_read(_SAFETY), "## 3.")
    assert region.strip(), f"section 3 is missing from {_SAFETY}"
    assert _placement(region) == []


def test_a_pointer_that_stands_wrong_is_reported_for_each_way_it_can() -> None:
    """The placement check can fail, one way at a time: as an item of the list (run on from the
    item above, so with no blank line before it), before the list, run on to the last item with
    no blank line, with no list to follow and not there at all. The stand that is right is
    not reported."""
    assert _placement(_section(_POINTER_AFTER_THE_LIST, "## 3.")) == []
    assert _placement(_section(_POINTER_AS_AN_ITEM, "## 3.")) == [
        "the pointer is an item of the list",
        "the pointer has no blank line before it",
    ]
    assert _placement(_section(_POINTER_BEFORE_THE_LIST, "## 3.")) == [
        "the pointer stands before the last item of the list"
    ]
    assert _placement(_section(_POINTER_RUN_ON, "## 3.")) == [
        "the pointer has no blank line before it"
    ]
    assert _placement(f"{_HEADING_3}\n\n{_CREATE_POINTER}\n") == [
        "section 3 has no list for the pointer to follow"
    ]
    assert _placement(f"{_HEADING_3}\n\n{_STALE_READ_LIST}\n") == [
        "the pointer is on 0 lines, not 1"
    ]


def test_each_placement_rule_is_load_bearing_on_the_real_text() -> None:
    """Each wrong stand applied to the real section 3 is reported by its own rule and no other:
    the pointer made an item of the list, and the blank line before it removed."""
    lines = _section(_read(_SAFETY), "## 3.").split("\n")
    at = next(i for i, line in enumerate(lines) if _POINTER_MARK in line)
    assert not lines[at - 1].strip(), "the real pointer has no blank line before it"
    as_an_item = [*lines[:at], f"- {lines[at]}", *lines[at + 1 :]]
    run_on = [*lines[: at - 1], *lines[at:]]
    assert _placement("\n".join(as_an_item)) == ["the pointer is an item of the list"]
    assert _placement("\n".join(run_on)) == ["the pointer has no blank line before it"]


def test_a_link_to_a_missing_file_is_not_a_link_to_the_reference() -> None:
    """The link check can fail: a real link is found; a link to a missing file, a link to
    another file that exists and a link inside a fenced block are not."""
    linked = "Create it only if absent ([12k](references/shared-index-protocol.md))."
    assert _links_the_reference(linked, _SAFETY)
    for text in (
        "Create it only if absent ([12k](references/no-such-file.md)).",
        "Create it only if absent ([12k](SKILL.md)).",
        "```\n[12k](references/shared-index-protocol.md)\n```",
    ):
        assert not _links_the_reference(text, _SAFETY), text


def test_a_place_that_is_missing_says_so_by_name() -> None:
    place = _PLACES[3]
    assert _problems(place, "## 6. Another gate\n\nText.\n") == [
        f"{place.where} is missing from {place.path}"
    ]
    assert _problems(place, "") == [f"{place.where} is missing from {place.path}"]


def test_the_fold_joins_a_rewrapped_sentence_and_drops_bold_marks() -> None:
    """Every check reads the text through the fold: lines join, a run of spaces is one space,
    bold marks go, the ends are trimmed."""
    assert _folded("  a **bold**  word\n     and a second\nline  \n") == (
        "a bold word and a second line"
    )


_SECTIONS = "\n".join(
    [
        "#### 12. A look-alike that only contains the wanted prefix",
        "## 12. First",
        "first body",
        "### 12.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "```",
        "## 13. Second",
        "second body",
        "# 14. Higher",
        "higher body",
        "",
    ]
)


def test_a_section_runs_to_the_next_heading_of_its_level_or_a_higher_one() -> None:
    """The section finder starts at the heading that begins with its text, keeps a deeper heading
    and a `#` line inside a fence, stops at a heading of its own level or a higher one, and
    finds nothing for a heading that is not there."""
    first = _section(_SECTIONS, "## 12.")
    assert first.startswith("## 12. First"), first
    for kept in ("first body", "deeper body", "a comment in a fence"):
        assert kept in first, first
    assert "second body" not in first, first
    second = _section(_SECTIONS, "## 13.")
    assert "second body" in second and "higher body" not in second, second
    assert _section(_SECTIONS, "## 99.") == ""


def test_a_blockquote_pointer_is_read_from_its_own_section_only() -> None:
    """The pointer finder keeps the lines of the section that start with '>' and nothing else:
    no prose line of the section, and no blockquote of the section before or after it."""
    text = "\n".join(
        [
            "## 11. Before",
            "> not this one",
            "## 12. The pointer",
            "a prose line",
            "> the pointer line",
            "> and its second line",
            "## 13. After",
            "> nor this one",
            "",
        ]
    )
    assert _blockquote_of("## 12.")(text) == "> the pointer line\n> and its second line"
    assert _blockquote_of("## 99.")(text) == ""
