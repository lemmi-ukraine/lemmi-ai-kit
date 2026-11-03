"""Twelve lessons about the review's own instruments are written down in two references, and pinned here.

Each is a way a probe, a sweep or a count passed while what it was taken to cover was wrong, and each
was seen once, in a project that uses the kit. The fixture-design reference gains four numbered
sections: a probe that certified the matcher and not the region it scans; a checker keyed on text
that cannot tell a mention from a use; a probe that tested detection and not normalisation; and two
sweeps that cannot see what they certify, a line sweep blind to a phrase the markdown wrap splits and
a token sweep blind to numbers. The claim-boundaries reference gains one section whose heading has no
number: a number typed from a printout, presence claims probed less hard than absence claims, a
document's own summary left stale by per-entry edits, a corpus narrower than the project's own list,
a write set read as the files its citations name, and a count with no command beside it. They are
references only: no SKILL.md gains a line, and both references are reached through links their
SKILL.md already has.

The heading with no number is deliberate. `test_pointer_lines_wording.py` derives the pointer's "four
measured cases" from the numbered headings of the claim-boundaries reference and its "four shorter
cases" from the bullets under the heading that holds those words, so a numbered heading or one more
bullet there turns that test red and asks for an edit of a SKILL.md line that has no room.

What each test asserts:

* `test_the_reference_states_the_claim` cuts the one section the row names, by its heading, and looks
  for the row's phrases in it (lower-cased, emphasis and code marks dropped, whitespace folded, so a
  phrase the markdown wrap splits is still found). A heading that is not there fails loudly.
* `test_every_phrase_is_found_once_and_reported_when_it_goes` plants a removal of each phrase in turn
  in the real section: the phrase is there exactly once, and its removal is the one gap reported.
* `test_the_fixture_reference_numbers_its_sections_one_to_fifteen_once_each` reads the numbered
  headings, so a block applied twice or a section renumbered turns it red.
* The two tests on the claims reference keep the counts its pointer states (four numbered headings,
  four shorter-case bullets) and keep the new heading unnumbered, outside the shorter cases, last,
  and there once. The first holds on the old text as well; the readers they use are fired at a
  planted extra bullet and a planted numbered heading.
* `test_the_opening_no_longer_says_every_failure_was_measured_in_this_repo` reads the opening of the
  fixture reference, which said all of its cases were measured here until sections were added that
  were not.
* The instrument tests fire the cutter, the scope and the readers at planted text, so their silence
  on the real files means something.

THE SURFACE, in numbers the tests assert: 12 claims and 32 phrases in 5 sections of 2 references (20
phrases in 4 sections of the fixture reference, 12 in 1 section of the claims reference), the opening
of the fixture reference (2 phrases that must be there and 1 that must be gone), and 15 numbered
sections in the fixture reference against 4 numbered headings and 4 shorter-case bullets in the claims
reference.
"""

import re
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"

_FIXTURE_DESIGN = "post-task-review/references/fixture-design.md"
_CLAIM_BOUNDARIES = "post-task-review/references/claim-boundaries.md"
_SKILL_MD = "post-task-review/SKILL.md"

_NEW_SECTION = "## More ways"
_HEADING = re.compile(r"^(#{1,6})\s")
_NUMBERED = re.compile(r"^## (\d+)\. ")


class _Claim(NamedTuple):
    claim: str
    reference: str
    heading: str
    phrases: tuple[str, ...]


# (claim, reference under plugins/core/skills, the start of the heading of the one section that holds
# the claim, the phrases that must all be in that section). Every phrase is written as `_plain` leaves
# the text: lower-case, no emphasis or code marks, whitespace folded.
_CLAIMS: tuple[_Claim, ...] = (
    _Claim(
        "a probe certifies the matcher, never the region it scans",
        _FIXTURE_DESIGN,
        "## 12.",
        (
            "a probe certifies the matcher, never the region",
            "only the correct region can see",
            "end a scan region on a token the defect cannot move",
            "whose defect sits at the boundary of the region",
        ),
    ),
    _Claim(
        "a broken-reference checker cannot tell a live pointer from a documented absence",
        _FIXTURE_DESIGN,
        "## 13.",
        (
            "cannot tell a live pointer from a documented absence",
            "read the citation's context before counting a hit",
        ),
    ),
    _Claim(
        "a checker keyed on a command's text flags the comment that documents it",
        _FIXTURE_DESIGN,
        "## 13.",
        (
            "flags the comment that documents the command",
            "put a benign mention in the negative fixture",
            "one offending insertion that must be flagged and one benign mention that must not",
            "prefer a structural rule",
        ),
    ),
    _Claim(
        "a probe tests detection, not normalisation",
        _FIXTURE_DESIGN,
        "## 14.",
        (
            "a probe tests detection, not normalisation",
            "classify a sample of its findings by hand",
            "draw one fixture from the corpus itself",
        ),
    ),
    _Claim(
        "a line-at-a-time sweep cannot see a phrase the markdown wrap splits",
        _FIXTURE_DESIGN,
        "## 15.",
        (
            "cannot see a phrase the markdown wrap splits",
            "sweep paragraphs as well as lines",
            "over the pre-fix copy of the text first",
        ),
    ),
    _Claim(
        "a presence-only sweep of tokens cannot check numbers",
        _FIXTURE_DESIGN,
        "## 15.",
        (
            "cannot check numbers",
            "under three digits",
            '"n checkable, n carried"',
            'never "all resolve"',
        ),
    ),
    _Claim(
        "a number worked out from a printout is a typed number",
        _CLAIM_BOUNDARIES,
        _NEW_SECTION,
        (
            "is a typed number",
            "print the one value you will quote, with its label",
        ),
    ),
    _Claim(
        "claims that something is there are probed as hard as claims that it is absent",
        _CLAIM_BOUNDARIES,
        _NEW_SECTION,
        (
            "as hard as the claims that something is absent",
            "say which population each probe covered",
        ),
    ),
    _Claim(
        "editing the entries stales a document's own summary",
        _CLAIM_BOUNDARIES,
        _NEW_SECTION,
        (
            "stales a document's own summary",
            "re-derive every count and status above the entries",
        ),
    ),
    _Claim(
        "a claim about what was already documented needs a stated corpus",
        _CLAIM_BOUNDARIES,
        _NEW_SECTION,
        (
            "only as good as its stated corpus",
            "print the corpus size beside any share or novelty claim",
        ),
    ),
    _Claim(
        "every file the citations point at is not every file in the write set",
        _CLAIM_BOUNDARIES,
        _NEW_SECTION,
        (
            'is not "every file in the write set"',
            "list it once near the end",
        ),
    ),
    _Claim(
        "a count with no command beside it cannot be reproduced",
        _CLAIM_BOUNDARIES,
        _NEW_SECTION,
        (
            "a count with no command beside it cannot be reproduced",
            "under -e a . matches any character",
        ),
    ),
)

# The opening of the fixture reference said "all of them were measured in this repo". Four sections
# were measured in another project, so it now says each was measured on a real instrument and which
# sections were seen once.
_OPENING_PRESENT = (
    "each was measured on a real instrument",
    "sections 12 to 15 once each, in a project that uses the kit",
)
_OPENING_GONE = ("all of them were measured in this repo",)

# The opening paragraphs and the heading after them as the reference held them before: an unedited
# excerpt, less its title line.
_OLD_OPENING = """`probe_checker.py` answers one question: *given these two fixtures, can the checker see?* It cannot
tell you whether the fixtures model anything real. Every failure below produced a **green probe** on
a **wrong instrument**, and all of them were measured in this repo.

Read this at the moment you write a checker, not at the gate that has already been driven by its
output.

---

## 1. A negative fixture must RESEMBLE the target and still pass
"""


def _read(reference: str) -> str:
    """The reference as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_SKILLS / reference).read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped, whitespace folded to one space, lower-cased."""
    return " ".join(text.replace("*", "").replace("`", "").split()).lower()


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or a
    higher level; a `#` line inside a fenced block is not a heading. A missing heading fails
    loudly, with the heading named."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        found = None if in_fence or fence else _HEADING.match(line)
        if fence:
            in_fence = not in_fence
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


def _headings(text: str) -> list[str]:
    """The `##` heading lines in order, skipping any `#` line inside a fenced block."""
    found: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            found.append(line)
    return found


def _numbers(headings: list[str]) -> list[int]:
    """The numbers of the numbered headings, in order."""
    return [int(m[1]) for heading in headings if (m := _NUMBERED.match(heading))]


def _shorter_case_bullets(text: str) -> list[str]:
    """The top-level bullets under the first `##` heading that holds "shorter cases", up to the
    next `##` heading: the same cut `test_pointer_lines_wording.py` makes to count them."""
    inside = False
    bullets: list[str] = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if inside:
                break
            inside = "shorter cases" in line.lower()
        elif inside and line.startswith("- "):
            bullets.append(line)
    assert inside, "no '##' heading that contains 'shorter cases'"
    return bullets


def _plant_a_bullet(text: str) -> str:
    """The text with one more bullet at the end of the section that holds "shorter cases"."""
    lines = text.split("\n")
    heads = [i for i, line in enumerate(lines) if line.startswith("## ")]
    start = next((i for i in heads if "shorter cases" in lines[i].lower()), None)
    assert start is not None, "no '##' heading that contains 'shorter cases'"
    end = next((i for i in heads if i > start), len(lines))
    return "\n".join([*lines[:end], "- a planted bullet", *lines[end:]])


def _missing(section: str, phrases: tuple[str, ...]) -> list[str]:
    plain = _plain(section)
    return [phrase for phrase in phrases if phrase not in plain]


def _problems(row: _Claim, text: str) -> list[str]:
    """What the section the row names does not hold in `text`; all of it when the section is gone."""
    try:
        section = _section(text, row.heading, row.reference)
    except AssertionError as gone:
        return [str(gone), *(f"missing: {phrase}" for phrase in row.phrases)]
    return [f"missing: {phrase}" for phrase in _missing(section, row.phrases)]


def _opening(text: str) -> str:
    """The text before the first `##` heading."""
    first = re.search(r"^## ", text, re.MULTILINE)
    assert first is not None, "no '##' heading in the text"
    return text[: first.start()]


def _opening_problems(text: str) -> list[str]:
    opening = _plain(_opening(text))
    gaps = [
        f"missing: {phrase}" for phrase in _OPENING_PRESENT if phrase not in opening
    ]
    old = [
        f"old wording present: {phrase}"
        for phrase in _OPENING_GONE
        if phrase in opening
    ]
    return gaps + old


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for row in _CLAIMS for phrase in row.phrases]
    sections = {(row.reference, row.heading) for row in _CLAIMS}
    references = {row.reference for row in _CLAIMS}
    assert (len(_CLAIMS), len(phrases), len(sections), len(references)) == (
        12,
        32,
        5,
        2,
    )
    assert len({row.claim for row in _CLAIMS}) == len(_CLAIMS), (
        "two claims share a name"
    )
    assert len(set(phrases)) == len(phrases), "a phrase is listed twice"
    held = {
        reference: sum(
            len(row.phrases) for row in _CLAIMS if row.reference == reference
        )
        for reference in references
    }
    assert held == {_FIXTURE_DESIGN: 20, _CLAIM_BOUNDARIES: 12}
    assert (len(_OPENING_PRESENT), len(_OPENING_GONE)) == (2, 1)
    not_plain = [
        p for p in (*phrases, *_OPENING_PRESENT, *_OPENING_GONE) if p != _plain(p)
    ]
    assert not not_plain, (
        f"phrases the reader's folding could never leave as written: {not_plain}"
    )
    unreadable = [name for name in sorted(references) if not (_SKILLS / name).is_file()]
    assert not unreadable, (
        f"{len(unreadable)} of {len(references)} references: {unreadable}"
    )


@pytest.mark.parametrize("row", _CLAIMS, ids=[row.claim for row in _CLAIMS])
def test_the_reference_states_the_claim(row: _Claim) -> None:
    problems = _problems(row, _read(row.reference))
    assert not problems, f"{row.reference} does not state {row.claim!r}: {problems}"


def test_every_phrase_is_found_once_and_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section in turn is the one gap reported, and
    an empty text lacks every phrase of a row. A phrase the check cannot see go would let a section
    lose its claim and stay green; one found twice in its section would be a paragraph pasted twice."""
    for row in _CLAIMS:
        text = _read(row.reference)
        assert not _problems(row, text), f"{row.claim!r} does not hold at the start"
        section = _plain(_section(text, row.heading, row.reference))
        for phrase in row.phrases:
            assert section.count(phrase) == 1, (
                row.claim,
                phrase,
                section.count(phrase),
            )
            assert _missing(section.replace(phrase, ""), row.phrases) == [phrase], (
                row.claim,
                phrase,
            )
        assert _missing("", row.phrases) == list(row.phrases), row.claim


def test_the_fixture_reference_numbers_its_sections_one_to_fifteen_once_each() -> None:
    numbers = _numbers(_headings(_read(_FIXTURE_DESIGN)))
    assert numbers == list(range(1, 16)), f"numbered sections read {numbers}"


def test_the_claims_reference_keeps_the_counts_its_pointer_states() -> None:
    """Four numbered headings and four shorter-case bullets: what the SKILL.md pointer says and
    `test_pointer_lines_wording.py` derives. Unlike the rows above, it holds on the old text too."""
    text = _read(_CLAIM_BOUNDARIES)
    numbered = _numbers(_headings(text))
    bullets = _shorter_case_bullets(text)
    assert len(numbered) == 4, (
        f"numbered headings read {numbered}, the pointer says four"
    )
    assert len(bullets) == 4, (
        f"{len(bullets)} shorter-case bullets, the pointer says four"
    )


def test_the_new_section_of_the_claims_reference_has_no_number_and_is_not_a_shorter_case() -> (
    None
):
    headings = _headings(_read(_CLAIM_BOUNDARIES))
    new = [heading for heading in headings if heading.startswith(_NEW_SECTION)]
    assert len(new) == 1, f"{len(new)} headings start {_NEW_SECTION!r}: {headings}"
    assert headings[-1] == new[0], "the new section is not the closing one"
    assert not _NUMBERED.match(new[0]), "the new heading carries a number"
    shorter = [heading for heading in headings if "shorter cases" in heading.lower()]
    assert len(shorter) == 1 and shorter[0] != new[0], shorter


@pytest.mark.parametrize("reference", [_FIXTURE_DESIGN, _CLAIM_BOUNDARIES])
def test_the_skill_already_links_the_reference(reference: str) -> None:
    """A reference no SKILL.md links is not read, and the links exist, so no SKILL.md grows."""
    link = reference.partition("/")[2]
    assert link in _read(_SKILL_MD), f"{_SKILL_MD} does not link {link}"


def test_the_opening_no_longer_says_every_failure_was_measured_in_this_repo() -> None:
    problems = _opening_problems(_read(_FIXTURE_DESIGN))
    assert not problems, f"{_FIXTURE_DESIGN}, its opening: {problems}"


def test_the_opening_check_reports_the_old_wording_and_passes_the_new_one() -> None:
    """Known positive and near misses for the check on the opening: the paragraph as it was is
    reported on all three counts, the new wording passes when the wrap splits a phrase, and the old
    wording returned beside the new is the one return."""
    assert "all of them were measured in this repo" in _OLD_OPENING, (
        "the plant lost the old text"
    )
    assert _opening_problems(_OLD_OPENING) == [
        f"missing: {_OPENING_PRESENT[0]}",
        f"missing: {_OPENING_PRESENT[1]}",
        f"old wording present: {_OPENING_GONE[0]}",
    ]
    new = _OLD_OPENING.replace(
        "and all of them were measured in this repo.",
        "and each was measured on a real instrument (sections 12 to 15 once each, in\n"
        "a project that uses the kit).",
    )
    assert new != _OLD_OPENING, "the new plant is the old text"
    assert _opening_problems(new) == []
    returned = new.replace(
        "Read this", "all of them were measured in this repo. Read this"
    )
    assert _opening_problems(returned) == [f"old wording present: {_OPENING_GONE[0]}"]
    with pytest.raises(AssertionError, match="no '##' heading"):
        _opening("a text with no heading\n")


def test_the_section_cutter_and_the_scope_see_planted_text() -> None:
    """Known positives and near misses for the cutter. A section ends at the next heading, a `#`
    line inside a fenced block is not one, a missing heading fails loudly, a phrase in another
    section is reported missing from this one, and a phrase the wrap splits or the marks interrupt
    is found."""
    planted = (
        "# Title\n\n## 12. First\nalpha beta\n\n```bash\n# a comment, not a heading\n```\n\n"
        "still the first\n\n## 13. Second\ngamma\n"
    )
    first = _section(planted, "## 12.", "planted")
    assert first.startswith("## 12. First")
    assert "still the first" in first, "a `#` line in a fence ended the section"
    assert "gamma" not in first, "the section ran past the next heading"
    with pytest.raises(AssertionError, match="no heading starting '## 14.'"):
        _section(planted, "## 14.", "planted")
    row = _Claim("planted", _FIXTURE_DESIGN, "## 13.", ("alpha beta",))
    assert _problems(row, planted) == ["missing: alpha beta"], (
        "scope leaked from another section"
    )
    assert (
        _problems(
            _Claim("planted", _FIXTURE_DESIGN, "## 12.", ("alpha beta",)), planted
        )
        == []
    )
    gone = _problems(_Claim("planted", _FIXTURE_DESIGN, "## 14.", ("alpha",)), planted)
    assert gone == [
        f"{_FIXTURE_DESIGN}: no heading starting '## 14.'",
        "missing: alpha",
    ]
    wrapped = "## 13. x\nthe **flags** the `comment that\ndocuments` the command\n"
    assert _missing(wrapped, ("flags the comment that documents the command",)) == []


def test_the_structure_readers_see_planted_text() -> None:
    """Known positives and near misses for the heading and bullet readers, and the planted extra
    bullet and numbered heading that the two counts must notice."""
    sections = "## 1. a\n## 2. b\n## Not numbered\n```\n## 9. inside a fence\n```\n## 2. b again\n"
    assert _numbers(_headings(sections)) == [1, 2, 2]
    claims = (
        "## 1. a\n\n## 2. b\n\n## Four shorter cases: x\n\n- one\n  wrapped\n- two\n\n"
        "## More ways\n\n- not counted\n"
    )
    assert _shorter_case_bullets(claims) == ["- one", "- two"]
    with pytest.raises(AssertionError, match="shorter cases"):
        _shorter_case_bullets("## One\n- a\n")
    real = _read(_CLAIM_BOUNDARIES)
    assert len(_shorter_case_bullets(real)) == 4
    assert len(_shorter_case_bullets(_plant_a_bullet(real))) == 5
    assert len(_numbers(_headings(real))) == 4
    assert len(_numbers(_headings(real + "\n## 5. a numbered one\n"))) == 5
