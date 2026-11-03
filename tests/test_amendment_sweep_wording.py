"""The dispatch gates say a changed decision reaches only the prompts someone sweeps.

A dispatched prompt quotes the decision, spec or plan it was written under and keeps that wording
after the source moves. The planner skill sweeps pending briefs when the branch topology is
revised; nothing swept the prompts when a decision changed, a spec came back or a plan was
revised, and nothing said to look for a running session before rewriting its dispatch file.
Section 7 of `orchestrate/references/dispatch-gates.md` now holds those checks, one bullet each:
sweep every dispatched and pending prompt on the change; date the plan a session follows; check
each row a prompt names against the register text; compare a foreign prompt's edit list with its
rows' homes before pasting it; look for a live session before rewriting a dispatch file.

Three things about the file as a whole are held here, because adding the section put them at risk.
The title said "six" and counted the sections by hand, so it now counts nothing. The opening
paragraph said every shape was measured, which a section that states a lower evidence level
cannot honour, so it now says "unless a section states a lower evidence level". And the sections
stay numbered without a gap, because `SKILL.md` cites them by number.

THE SURFACE, in numbers the tests assert: 7 claims and 25 phrases in one file, all inside section
7; the title, the opening paragraph and the section numbers are read apart from it. A claim holds
when every one of its phrases is in section 7 (lower-cased, bold marks dropped, whitespace
collapsed). Each phrase occurs once there and is fired at a planted removal. Every helper is fired
at a planted fixture it must flag and a near-miss it must not.
"""

import re
from pathlib import Path

import pytest

_GATES = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "orchestrate"
    / "references"
    / "dispatch-gates.md"
)
_SECTION_7 = "## 7."
_HEADING = re.compile(r"^(#{1,6})\s")
_NUMBERED = re.compile(r"^## (\d+)\.")
_WORD = re.compile(r"[a-z0-9]+")
_DASH = chr(0x2014)

# (claim id, the phrases that must all be present in section 7; lower-cased, bold marks
# dropped, whitespace collapsed). The claims, in order: the gap (only a topology change had a
# sweep); the evidence level; sweep on the change; date the plan a session follows; check
# each row against the register text; compare a foreign prompt's edit list with its rows'
# homes; look for a live session before rewriting a dispatch file.
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "gap",
        (
            "keeps that wording after the source moves",
            "`stacked-pr-planner` step 6 sweeps pending briefs when the branch topology is revised",
            "a decision, a returned spec or a revised plan has no such trigger",
        ),
    ),
    (
        "evidence-level",
        (
            "evidence level: observed in one cluster of hand-off notes, not yet repeated",
            "defaults to adopt and re-measure, not calibrated rules",
        ),
    ),
    (
        "sweep-on-the-change",
        (
            "in the same edit session, grep every dispatched and pending prompt for the old wording",
            "for the name of each row or file the change touches",
            "a prompt that names the row by id only",
            'a "conflicts with the spec" pass',
        ),
    ),
    (
        "date-the-plan",
        (
            "record the modification time of each plan file when a session starts and again before it hands back",
            "which plan version its work follows",
            "a plan that changed in between is reconciled before the hand-back is accepted",
        ),
    ),
    (
        "register-text",
        (
            "check every row a prompt names against the register text",
            "not as the prompt paraphrases it",
            "when two prompts share a fix, check the row in both",
            'an "or" between alternatives is read as a split',
            "the row then closes in neither",
        ),
    ),
    (
        "foreign-prompt",
        (
            "compare a foreign prompt's edit list with its rows' homes before pasting it",
            "lists the files its author saw",
            "add what the rows require before the prompt goes out",
        ),
    ),
    (
        "live-session",
        (
            "look for a live session before rewriting a dispatch file",
            "`git reflog -3`",
            "the host's live-session list",
            "an addendum keyed to its state",
            "a board line that session itself checks",
        ),
    ),
)
_PHRASES = tuple(phrase for _, phrases in _ROWS for phrase in phrases)

# Number words that would hand-write a count in a title.
_NUMBER_WORDS = frozenset(
    {
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "dozen",
    }
)

# What the file said before: the title and the opening sentence.
_OLD_TITLE = f"# Dispatch gates {_DASH} six measured failure shapes at the moment a brief goes out"
_OLD_OPENING_SENTENCE = (
    "Every shape below was\nmeasured in a multi-session initiative; the numbers are corpus "
    "measurements, not targets."
)
_QUALIFIED = (
    "unless a section states a lower evidence level, every shape below was measured"
)


def _read() -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return _GATES.read_text(encoding="utf-8").replace("\r\n", "\n")


def _flat(text: str) -> str:
    """Bold marks dropped, every run of whitespace one space, lower-cased: a re-wrapped line or
    a re-emphasised word is not a different sentence."""
    return " ".join(text.replace("**", "").split()).lower()


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


def _gaps(flat: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in flat]


def _title(text: str) -> str:
    return text.split("\n", 1)[0]


def _counts_in(title: str) -> list[str]:
    """The whole words of a title that are a digit string or a number word."""
    return [
        word
        for word in _WORD.findall(title.lower())
        if word.isdigit() or word in _NUMBER_WORDS
    ]


def _opening(text: str) -> str:
    """The text between the title line and the first `## ` heading, flattened."""
    body: list[str] = []
    for line in text.split("\n")[1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return _flat("\n".join(body))


def _numbers(text: str) -> list[int]:
    """The N of every `## N.` heading outside a fenced block, in file order."""
    found: list[int] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else _NUMBERED.match(line)
        if match is not None:
            found.append(int(match[1]))
    return found


def _without_gaps(numbers: list[int]) -> bool:
    return numbers == list(range(1, len(numbers) + 1))


def _section_7() -> str:
    section = _section(_read(), _SECTION_7)
    assert section.strip(), "section 7 is missing from dispatch-gates.md"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_ROWS), len(_PHRASES)) == (7, 25)
    assert len(set(_PHRASES)) == len(_PHRASES), "a phrase is listed twice"
    assert _GATES.is_file(), f"{_GATES} is not a file"
    assert _read().strip(), "dispatch-gates.md is empty"


def test_section_7_is_present() -> None:
    """Red before the change: the file stopped at section 6."""
    section = _section_7()
    assert section.startswith(
        "## 7. A changed decision reaches only the prompts someone sweeps"
    )


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[row[0] for row in _ROWS])
def test_section_7_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _gaps(_flat(_section_7()), phrases)
    assert not missing, f"section 7 does not state {claim!r}: missing {missing}"


# --- the checks can fail -----------------------------------------------------------------------


def test_every_phrase_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section is the one gap reported, and an
    empty section lacks every phrase. A phrase that occurs twice, or that overlaps another, would
    let a claim lose its wording and stay green."""
    flat = _flat(_section_7())
    assert _gaps(flat, _PHRASES) == [], "a phrase is missing at the start"
    for phrase in _PHRASES:
        assert flat.count(phrase) == 1, f"{phrase!r} occurs {flat.count(phrase)} times"
        assert _gaps(flat.replace(phrase, ""), _PHRASES) == [phrase], phrase
    assert _gaps("", _PHRASES) == list(_PHRASES)


def test_a_rewrapped_and_reemphasised_section_still_holds_every_claim() -> None:
    """Near-miss that must NOT be reported: the real section with a line break and an indent at
    every space and bold marks around one word is the same text."""
    real = _section_7()
    reshaped = real.replace(" ", "\n    ").replace("sweep", "**sweep**")
    assert reshaped != real
    assert _gaps(_flat(reshaped), _PHRASES) == []


def test_a_sweep_of_pending_prompts_only_is_reported_for_that_phrase_alone() -> None:
    """Near-miss that MUST be reported: dropping the dispatched half of the sweep, the part a
    pending-only search misses, loses that one phrase and no other."""
    reduced = _section_7().replace("dispatched and pending", "pending")
    gaps = _gaps(_flat(reduced), _PHRASES)
    assert gaps == [
        "in the same edit session, grep every dispatched and pending prompt for the old wording"
    ], gaps


_SECTIONS = "\n".join(
    [
        "#### 7. A look-alike that only contains the wanted prefix",
        "## 7. First",
        "first body",
        "### 7.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "## 9. nor is this one",
        "```",
        "## 8. Second",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, and finds nothing for a
    heading that is not there, so an absent section is reported and not read as an empty pass."""
    first = _section(_SECTIONS, "## 7.")
    assert first.startswith("## 7. First"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert _section(_SECTIONS, "## 99.") == ""
    assert _gaps(_flat(_section(_SECTIONS, "## 99.")), _PHRASES) == list(_PHRASES)


# --- the file as a whole -----------------------------------------------------------------------


def test_the_title_hand_writes_no_count() -> None:
    """Red before the change: the title said six, and the file has more sections than that."""
    title = _title(_read())
    assert title.startswith("# Dispatch gates"), title
    assert _counts_in(title) == [], (
        f"the title hand-writes a count: {_counts_in(title)}"
    )


def test_the_title_check_flags_a_count_and_not_a_word_that_holds_one() -> None:
    """Fired at the title the file had (it must flag it), at a digit and at another number word,
    and at a near-miss of words that only contain a number word (it must not)."""
    assert _counts_in(_OLD_TITLE) == ["six"]
    assert _counts_in("# Dispatch gates: 8 failure shapes") == ["8"]
    assert _counts_in("# Dispatch gates: twelve failure shapes") == ["twelve"]
    near_miss = (
        "# Dispatch gates: someone, none, often, the tone of a listener on stone"
    )
    assert _counts_in(near_miss) == []


def test_the_opening_does_not_claim_every_shape_was_measured() -> None:
    """Red before the change: the opening paragraph said every shape was measured in a
    multi-session initiative, which section 7 does not claim for itself."""
    assert _QUALIFIED in _opening(_read())


def test_the_opening_check_flags_the_old_sentence() -> None:
    old = f"# Title\n\nCompanion to a skill. {_OLD_OPENING_SENTENCE}\n\n## 1. First\nbody\n"
    assert _QUALIFIED not in _opening(old)
    qualified = old.replace(
        "Every shape", "Unless a section states a lower evidence level, every shape"
    )
    assert _QUALIFIED in _opening(qualified)
    assert "unless a section" not in _opening("# Title\n## 1. First\nUnless a section")


def test_the_sections_are_numbered_without_a_gap_up_to_section_8() -> None:
    """`SKILL.md` cites the sections by number, so 7 and 8 exist and nothing is skipped."""
    numbers = _numbers(_read())
    assert _without_gaps(numbers), numbers
    assert {7, 8} <= set(numbers), numbers


def test_the_numbering_check_flags_a_gap_a_repeat_and_ignores_a_fence() -> None:
    assert _without_gaps(_numbers("## 1. a\n## 2. b\n## 3. c\n"))
    assert not _without_gaps(_numbers("## 1. a\n## 2. b\n## 4. d\n"))
    assert not _without_gaps(_numbers("## 1. a\n## 2. b\n## 2. b again\n"))
    assert _numbers("## 1. a\n```\n## 2. in a fence\n```\n## 2. b\n") == [1, 2]
    assert _numbers("### 1. deeper\n") == []
