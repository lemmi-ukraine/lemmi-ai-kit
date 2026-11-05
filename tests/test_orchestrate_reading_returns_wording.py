"""What a returned note says about itself, and what a workflow's failures mean, are checked before they are acted on.

`orchestrate` said a worker's summary is a claim, and left two things a return can carry unchecked.
A status line, a "last updated" time or a "nothing done yet" is text typed at one moment by a session
that may have kept working: it is compared with the note's file time, the newest file or commit in
the paths the note owns, and the live-session list, and a stale note is corrected in place with a
dated line. A workflow whose verifier stage did not finish returns findings without verdicts: its
failures are read before its findings, and every finding is unverified until the load-bearing ones
are verified. The wording lives in `orchestrate/references/reading-returns.md`, reached by one
pointer line in section 3 of `SKILL.md`. It carries no hand-off Status value, because the hand-off
standard owns those, and no link at all.

THE SURFACE, in numbers the tests assert: 1 reference judged by 7 claims and 12 phrases (a claim
holds when every one of its phrases is in the reference, lower-cased, whitespace collapsed); 1
pointer line in section 3, fired at 5 planted shapes (absent, dead, before the passage it follows,
in a later paragraph, twice); 1 hygiene scan reused from `test_assets.py` (its patterns, over the
reference, which must be inside that scan's file list), fired at 4 planted shapes and 2 near-misses;
1 link check (relative, inside the pack) fired at 3 planted links and 1 near-miss. Each phrase is
fired at a planted removal, so a phrase the check could not see go is not in the table. A missing
reference reads as empty text, so every claim fails by name and not by an exception.
"""

import re
from pathlib import Path

import pytest
from test_assets import (
    _FORBIDDEN as _ASSET_FORBIDDEN,  # pyright: ignore[reportPrivateUsage]
)
from test_assets import (
    _asset_text_files,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACK = _REPO_ROOT / "plugins" / "orchestration"
_ORCHESTRATE = _PACK / "skills" / "orchestrate"
_SKILL = _ORCHESTRATE / "SKILL.md"
_REFERENCE = _ORCHESTRATE / "references" / "reading-returns.md"

_TARGET = "references/reading-returns.md"
_SECTION_3 = "### 3. Review before merging"
_PASSAGE_END = "the author re-runs every finding it cites."
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
# The values of the hand-off Status section: the hand-off standard owns them, so a reference of
# this skill does not name them.
_STATUS_VALUES = ("in-progress", "ready-for-review")

# (claim, the phrases that must all be present; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "a status line, an updated time and a nothing-done-yet are claims",
        (
            'a status line, an "updated" time and a "nothing done yet" are claims',
            "may have kept working after it did",
        ),
    ),
    (
        "they are compared with the note's file time, the newest work it owns and the live sessions",
        (
            "compare the note's file time with the newest file or commit in the paths it owns",
            "and with the host's live-session list",
        ),
    ),
    (
        "a note older than the work it describes is stale and is corrected in place with a dated line",
        (
            "a note older than the work it describes is stale",
            "say so, and correct it in place with a dated line",
            "never by rewriting it",
        ),
    ),
    (
        "a workflow's failures are read before its findings",
        ("read a workflow's failures before its findings",),
    ),
    (
        "a run whose verifier stage did not finish returns findings without verdicts",
        (
            "a run whose verifier stage did not finish returns findings without verdicts",
        ),
    ),
    (
        "every finding is unverified until the load-bearing ones are verified",
        (
            "treat every finding as unverified",
            "verify the load-bearing ones before you act on them",
        ),
    ),
    (
        "the rules are labelled with their evidence level",
        ("evidence level: preventive",),
    ),
)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _words(text: str) -> str:
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _reference_words() -> str:
    """The reference folded, or empty text when it is absent, so that a missing file fails every
    claim by name instead of raising."""
    return _words(_read(_REFERENCE)) if _REFERENCE.is_file() else ""


def _section(text: str, heading: str) -> str:
    """The one heading line that starts with `heading` and the lines under it, up to the next
    heading of the same or a higher level. A `#` line inside a fence is not a heading. Fails
    loudly when no line, or more than one, starts with `heading`."""
    lines = text.split("\n")
    inside = False
    fenced: list[bool] = []
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            fenced.append(True)
        else:
            fenced.append(inside)
    starts = [
        index
        for index, line in enumerate(lines)
        if not fenced[index] and _HEADING.match(line) and line.startswith(heading)
    ]
    assert len(starts) == 1, f"{heading!r} starts {len(starts)} headings, not 1"
    opening = _HEADING.match(lines[starts[0]])
    assert opening is not None
    body = [lines[starts[0]]]
    for index in range(starts[0] + 1, len(lines)):
        found = None if fenced[index] else _HEADING.match(lines[index])
        if found is not None and len(found[1]) <= len(opening[1]):
            break
        body.append(lines[index])
    return "\n".join(body)


def _pointer_problems(skill_text: str, root: Path) -> list[str]:
    """Why section 3 does not carry the one pointer to the reference, in the paragraph of the
    verifier passage and after it, with a target that exists under `root`; empty when it does."""
    section = _section(skill_text, _SECTION_3)
    found = [target for target in _LINK.findall(section) if target == _TARGET]
    if len(found) != 1:
        return [f"section 3 links {_TARGET} {len(found)} times, not 1"]
    problems: list[str] = []
    if not (root / _TARGET).is_file():
        problems.append(f"the pointer's target {_TARGET} does not exist")
    holding = [
        _words(paragraph)
        for paragraph in section.split("\n\n")
        if _PASSAGE_END in _words(paragraph)
    ]
    if len(holding) != 1:
        return [
            *problems,
            f"{len(holding)} paragraphs of section 3 end the verifier passage",
        ]
    paragraph = holding[0]
    link = f"]({_TARGET})"
    if link not in paragraph:
        problems.append("the pointer is not in the paragraph of the verifier passage")
    elif paragraph.index(link) < paragraph.index(_PASSAGE_END):
        problems.append("the pointer comes before the verifier passage it follows")
    return problems


def _link_problems(text: str, folder: Path) -> list[str]:
    """The markdown links of `text` that are absolute or whose target, read from `folder`, is
    outside the pack."""
    problems: list[str] = []
    for target in _LINK.findall(text):
        if target.startswith(("/", "http", "~")) or re.match(r"[A-Za-z]:", target):
            problems.append(f"{target}: not a relative link")
        elif not (folder / target).resolve().is_relative_to(_PACK.resolve()):
            problems.append(f"{target}: leaves the pack")
    return problems


def _hygiene_problems(text: str) -> list[str]:
    """The reasons the shared hygiene patterns of `test_assets.py` give for `text`."""
    return [why for pattern, why in _ASSET_FORBIDDEN if pattern.search(text)]


def _status_values(text: str) -> list[str]:
    return [value for value in _STATUS_VALUES if value in text.lower()]


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (7, 12)
    assert _REFERENCE.is_file(), f"{_REFERENCE.name} does not exist"
    assert _SKILL.is_file(), _SKILL


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[claim for claim, _ in _ROWS])
def test_the_reference_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_reference_words(), phrases)
    assert not missing, f"the reference does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real text in turn is the one gap reported,
    and an empty text lacks every phrase of a row. A phrase the check cannot see go would let
    the reference lose its claim and stay green."""
    text = _reference_words()
    for claim, phrases in _ROWS:
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_section_3_points_at_the_reference_after_the_verifier_passage() -> None:
    assert _pointer_problems(_read(_SKILL), _ORCHESTRATE) == []


def test_the_pointer_check_sees_each_planted_shape(tmp_path: Path) -> None:
    """Fired at planted texts of section 3: the pointer after the passage in its paragraph is
    clean, and a missing pointer, a dead one, one before the passage, one in a later paragraph
    and a doubled one are each reported."""
    (tmp_path / "references").mkdir()
    (tmp_path / _TARGET).write_text("x\n", encoding="utf-8")
    passage = f"A worker's summary is a claim. A verifier is an instrument too. {_PASSAGE_END}"
    pointer = f"See [{_TARGET}]({_TARGET})."
    head = f"{_SECTION_3} results are claims\n"
    good = f"{head}{passage}\n{pointer}\n\nThe review loop.\n"
    assert _pointer_problems(good, tmp_path) == []
    absent = f"{head}{passage}\n\nThe review loop.\n"
    assert _pointer_problems(absent, tmp_path) == [
        f"section 3 links {_TARGET} 0 times, not 1"
    ]
    assert _pointer_problems(good, tmp_path / "elsewhere") == [
        f"the pointer's target {_TARGET} does not exist"
    ]
    before = f"{head}{pointer}\n{passage}\n\nThe review loop.\n"
    assert _pointer_problems(before, tmp_path) == [
        "the pointer comes before the verifier passage it follows"
    ]
    later = f"{head}{passage}\n\n{pointer}\n"
    assert _pointer_problems(later, tmp_path) == [
        "the pointer is not in the paragraph of the verifier passage"
    ]
    twice = f"{head}{passage}\n{pointer}\n{pointer}\n"
    assert _pointer_problems(twice, tmp_path) == [
        f"section 3 links {_TARGET} 2 times, not 1"
    ]
    with pytest.raises(AssertionError, match="starts 0 headings"):
        _pointer_problems(f"## Another section\n{passage}\n{pointer}\n", tmp_path)


def test_the_reference_is_inside_the_shared_hygiene_scan_and_clean_under_it() -> None:
    scanned = {path.resolve() for path in _asset_text_files()}
    assert _REFERENCE.resolve() in scanned, (
        f"{_REFERENCE.name} is outside the file list of the hygiene scan in test_assets.py"
    )
    assert _hygiene_problems(_read(_REFERENCE)) == []


def test_the_hygiene_patterns_see_planted_shapes_and_not_near_misses() -> None:
    """Fired at planted text: a home path, a drive-letter path, a machine-specific host rule and a
    hard-coded skill-script path are each reported; prose about paths and about hosts is not. The
    planted shapes are built from fragments, so this file holds none of them whole."""
    home = "/" + "Users/someone/notes.md"
    drive = "C" + ":" + chr(92) + "Users" + chr(92) + "someone"
    host = "Windows" + " host"
    script = ".claude/" + "skills/demo/" + "scripts/run.py"
    for planted in (home, drive, host, script):
        assert _hygiene_problems(f"see {planted} for it"), planted
    for near_miss in (
        "a note about Windows paths and about the host's file times",
        "the skills folder of the project, and a scripts folder",
    ):
        assert _hygiene_problems(near_miss) == [], near_miss


def test_the_reference_names_no_hand_off_status_value_and_holds_no_link() -> None:
    text = _read(_REFERENCE)
    assert _status_values(text) == []
    assert _link_problems(text, _REFERENCE.parent) == []
    assert _LINK.findall(text) == []


def test_the_link_and_status_checks_see_planted_shapes() -> None:
    folder = _REFERENCE.parent
    assert _status_values("the status is in-progress or Ready-For-Review") == [
        "in-progress",
        "ready-for-review",
    ]
    assert _status_values("work is blocked, and a task is in progress") == []
    assert _link_problems("[a](brief-template.md)", folder) == []
    leaving = "../../../../core/skills/x/SKILL.md"
    assert _link_problems(f"[a]({leaving})", folder) == [f"{leaving}: leaves the pack"]
    assert _link_problems("[a](/abs/path.md)", folder) == [
        "/abs/path.md: not a relative link"
    ]
    assert _link_problems("[a](https://example.test/x)", folder) == [
        "https://example.test/x: not a relative link"
    ]
