"""A staleness alarm is placed in a step that runs for an unrelated reason.

The tracker's "Ledger growth" section said the backlog could no longer pile up silently because the
validator's Step 7 reports the ledger state at the close of every pass. That report runs inside the
pass it watches, so when the validator stops being run nothing prints, and the lint's
`meta-synthesis due` NOTE counts terminal verdicts, so it cannot see a stop either. The text now
states the placement rule (an alarm lives in a step that runs for an unrelated reason, and each
check is asked whether it still runs when the thing it detects stops), the tracker's Step 5 reports
the ledger-state line after every recorded entry, and the validator's Step 7 says the line also
runs from there.

Each assertion reads one named section of one file, and a heading that is not found fails loudly.
The checks are functions over a string, so `test_every_check_sees_its_planted_positive` fires them
at the old text, at a half-edit and at near-misses before their silence on the real files is
trusted, and `test_each_phrase_deleted_in_turn_is_reported` deletes every phrase of the shipped
text in turn. Every non-ASCII character in a fixture is built from `chr()`.

THE SURFACE, in numbers the tests assert: 2 files, 3 sections (Ledger growth, Step 5 of the
tracker, Step 7 of the validator), 6 + 5 + 4 phrases, 1 old shape.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"
_TRACKER = _SKILLS / "ai-improvement-tracker" / "SKILL.md"
_VALIDATOR = _SKILLS / "hypothesis-validator" / "SKILL.md"
_SURFACE: tuple[Path, ...] = (_TRACKER, _VALIDATOR)

# The skill audit fails a SKILL.md at 500 lines and counts one more than the newline count.
_LINE_CAP = 499

_AT_LEAST = chr(0x2265)
_MIDDLE_DOT = chr(0xB7)
_EM_DASH = chr(0x2014)

_STATE_LINE = f"`N PENDING {_MIDDLE_DOT} M terminal {_MIDDLE_DOT} last verdict <date>`"

_HEADING = re.compile(r"^(#{1,6})\s+\S")

_TRACKER_NAME = "ai-improvement-tracker SKILL.md"
_VALIDATOR_NAME = "hypothesis-validator SKILL.md"

_GROWTH_HEADING = "## Ledger growth"
_STEP_5_HEADING = "### Step 5: Write and verify"
_STEP_7_HEADING = "### Step 7: Report the ledger state"


# --- slicers over a string -----------------------------------------------------------------


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _view(text: str) -> str:
    """The text with every run of whitespace as one space and bold markers dropped."""
    return " ".join(text.split()).replace("**", "")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced block
    is a comment of the code it holds, not a heading. A missing heading fails with the heading
    named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _missing(view: str, facts: dict[str, str]) -> list[str]:
    """The names of the facts whose pattern is not found in `view`."""
    return [
        name
        for name, pattern in facts.items()
        if not re.search(pattern, view, re.IGNORECASE)
    ]


# --- what the new text must say ------------------------------------------------------------

_GROWTH_FACTS: dict[str, str] = {
    "the NOTE and its threshold stay": (
        r"the lint's `meta-synthesis due` NOTE \("
        + _AT_LEAST
        + r"10 unsynthesized terminal verdicts"
    ),
    "an alarm inside the process it watches cannot report that process stopping": (
        r"\ban alarm that runs inside the process it watches cannot report that "
        r"process stopping\b"
    ),
    "a staleness alarm goes in a step that runs for an unrelated reason": (
        r"\bplace a staleness alarm in a step that runs for an unrelated reason\b"
    ),
    "the step that records the next entry is one such step": (
        r"\bthe step that records the next entry\b"
    ),
    "ask of each check whether the alarm still runs when its subject stops": (
        r"\bif the thing it detects stops happening, does this alarm still run\?"
    ),
    "a gate that reads a file its design removed can invert": (
        r"\ba gate that reads a file its design removed can invert instead of going "
        r"quiet\b"
    ),
}

_STEP_5_FACTS: dict[str, str] = {
    "it reports the ledger state": r"\bthen report the ledger state\b",
    "the three counts are the ones the validator's Step 7 lists": (
        r"\bthe three counts `hypothesis-validator` Step 7 lists\b"
    ),
    "in the line shape of Step 7": re.escape(_STATE_LINE),
    "after every recorded entry": r"\bafter every recorded entry\b",
    "and not only when a validation pass runs": (
        r"\bnot only when a validation pass runs\b"
    ),
}

_STEP_7_FACTS: dict[str, str] = {
    "the three counts are still reported in the line shape": (
        r"\bReport them as " + re.escape(_STATE_LINE)
    ),
    "the line also runs from the tracker's Step 5": (
        r"\bthe line also runs from `ai-improvement-tracker` Step 5\b"
    ),
    "after every recorded entry": r"\bafter every recorded entry\b",
    "an alarm inside its own pass cannot report that pass stopping": (
        r"\ban alarm inside its own pass cannot report that pass stopping\b"
    ),
}

# The old placement: the validator's Step 7 as the one place the ledger state is reported.
_OLD_SHAPES: dict[str, tuple[str, str]] = {
    "the-validator-reports-so-the-backlog-cannot-pile-up": (
        r"at the close of every pass so the backlog cannot silently accumulate again",
        "names the validator's own pass as the alarm that keeps the backlog visible",
    ),
}


def _old_shapes(text: str) -> list[str]:
    """The slugs of the old shapes found in `text`."""
    view = _view(text)
    return [
        slug
        for slug, (pattern, _why) in _OLD_SHAPES.items()
        if re.search(pattern, view, re.IGNORECASE)
    ]


# --- the text as it stood before, and two stages of the edit: fixtures for the planted positives

_NOTE_PARAGRAPH = (
    "The file is therefore expected to grow, and that is not the failure mode to guard. The real\n"
    "one is a ledger that grows while nothing closes: the lint's `meta-synthesis due` NOTE ("
    + _AT_LEAST
    + "10\nunsynthesized terminal verdicts, computed from the header's `Last meta-synthesis` "
    "marker)\ntriggers the aggregate read that turns verdicts into design rules"
)

_OLD_GROWTH = (
    "## Ledger growth\n\n"
    "`.ai/improvement-hypotheses.md` is the **single file of record**.\n\n"
    + _NOTE_PARAGRAPH
    + ", and\n"
    f"`hypothesis-validator` Step 7 reports {_STATE_LINE} at the\n"
    "close of every pass so the backlog cannot silently accumulate again.\n\n"
)

# The old sentence is gone and the rule is there, but the question every check is asked is not.
_HALF_GROWTH = (
    "## Ledger growth\n\n" + _NOTE_PARAGRAPH + ".\n\n"
    "An alarm that runs inside the process it watches cannot report that process stopping.\n"
    "Place a staleness alarm in a step that runs for an unrelated reason (a session start,\n"
    "a commit check, a CI job, the step that records the next entry). A gate that reads a file\n"
    "its design removed can invert instead of going quiet.\n\n"
)

_NEW_GROWTH = (
    "## Ledger growth\n\n" + _NOTE_PARAGRAPH + ".\n\n"
    "An alarm that runs inside the process it watches cannot report that process stopping.\n"
    "Place a staleness alarm in a step that runs for an unrelated reason (a session start,\n"
    "a commit check, a CI job, the step that records the next entry), and ask of each check:\n"
    "if the thing it detects stops happening, does this alarm still run? A gate that reads a\n"
    "file its design removed can invert instead of going quiet.\n\n"
)

_OLD_STEP_5 = (
    "### Step 5: Write and verify (structural, not eyeballed)\n\n"
    "Append the entry, then run the data-file lint:\n\n"
    '```\nuv run --no-project --directory "${CLAUDE_PLUGIN_ROOT}/src" python -B -m '
    'lemmi_ai_kit lint hypotheses --project "<absolute project root>"\n```\n\n'
    "It checks heading order, heading-vs-`Changelog ref` date consistency, the category and\n"
    "status vocabularies, and required fields for new entries. Fix any finding before moving on.\n\n"
)

_OLD_STEP_7 = (
    "### Step 7: Report the ledger state (every pass)\n\n"
    f"Report them as {_STATE_LINE}. A pass that proposes\n"
    "verdicts but does not report these three is incomplete.\n\n"
    "**Why this replaced rotation.** Rotation guarded file SIZE. The failure that actually\n"
    "occurs is a ledger that grows while nothing closes. Size was never the problem;\n"
    f"an unreported backlog was. If you adopt this skill, do not reintroduce an archive {_EM_DASH} you\n"
    "would be re-solving the wrong failure and re-hiding this one.\n\n"
)

# The shipped additions on top of the old text: Step 5 with its report paragraph, Step 7 with its
# closing sentence. Every phrase of the new rule is in them.
_NEW_STEP_5 = _OLD_STEP_5 + (
    "Then report the ledger state, the three counts `hypothesis-validator` Step 7 lists, as\n"
    f"{_STATE_LINE}, after every recorded entry and not only when a\n"
    "validation pass runs: this step runs when that one does not.\n\n"
)

_NEW_STEP_7 = _OLD_STEP_7.rstrip("\n") + (
    " The line also runs from\n"
    "`ai-improvement-tracker` Step 5, after every recorded entry: an alarm inside its own pass\n"
    "cannot report that pass stopping.\n\n"
)


def _under_the_next_heading(fixture: str, next_heading: str) -> str:
    """`fixture` with its whole body moved under `next_heading`: the section keeps its heading and
    holds no phrase, and every phrase now stands in the section that follows."""
    heading, body = fixture.split("\n\n", 1)
    return f"{heading}\n\n{next_heading}\n\n{body}"


# --- one check per place the change names; each takes a whole file's text ------------------


def _growth_gaps(tracker: str) -> list[str]:
    section = _section(tracker, _GROWTH_HEADING, _TRACKER_NAME)
    return _missing(_view(section), _GROWTH_FACTS)


def _step_5_gaps(tracker: str) -> list[str]:
    section = _section(tracker, _STEP_5_HEADING, _TRACKER_NAME)
    return _missing(_view(section), _STEP_5_FACTS)


def _step_7_gaps(validator: str) -> list[str]:
    section = _section(validator, _STEP_7_HEADING, _VALIDATOR_NAME)
    return _missing(_view(section), _STEP_7_FACTS)


def _old_text_problems(tracker: str) -> list[str]:
    return [f"still says: {slug}" for slug in _old_shapes(tracker)]


def _reported(name: str, check: Callable[[str], list[str]], text: str) -> list[str]:
    """The problems of one check, a missing heading included, each led by `name`."""
    try:
        return [f"{name}: {problem}" for problem in check(text)]
    except AssertionError as error:
        return [f"{name}: {error}"]


def _problems(tracker: str, validator: str) -> list[str]:
    """Every check over one tracker text and one validator text, as a flat list."""
    return [
        *_reported("ledger growth", _growth_gaps, tracker),
        *_reported("tracker step 5", _step_5_gaps, tracker),
        *_reported("tracker", _old_text_problems, tracker),
        *_reported("validator step 7", _step_7_gaps, validator),
    ]


# --- the tests -----------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    assert len({path.resolve() for path in _SURFACE}) == 2, (
        "the two files must be distinct"
    )
    for path in _SURFACE:
        assert path.is_file(), f"{path.name} is not a file"
        assert _text(path).strip(), f"{path.name} is empty"
    _section(_text(_TRACKER), _GROWTH_HEADING, _TRACKER_NAME)
    _section(_text(_TRACKER), _STEP_5_HEADING, _TRACKER_NAME)
    _section(_text(_VALIDATOR), _STEP_7_HEADING, _VALIDATOR_NAME)
    assert (len(_GROWTH_FACTS), len(_STEP_5_FACTS), len(_STEP_7_FACTS)) == (6, 5, 4)
    assert len(_OLD_SHAPES) == 1


def test_ledger_growth_names_the_placement_rule() -> None:
    gaps = _growth_gaps(_text(_TRACKER))
    assert not gaps, f"{_TRACKER_NAME}, Ledger growth, does not say: {gaps}"


def test_the_validator_only_placement_is_gone_from_the_tracker() -> None:
    found = _old_shapes(_text(_TRACKER))
    assert not found, f"{_TRACKER_NAME} still carries the old placement: {found}"


def test_tracker_step_5_reports_the_ledger_state_after_every_recorded_entry() -> None:
    gaps = _step_5_gaps(_text(_TRACKER))
    assert not gaps, f"{_TRACKER_NAME}, Step 5, does not say: {gaps}"


def test_validator_step_7_says_the_line_also_runs_from_the_trackers_step_5() -> None:
    gaps = _step_7_gaps(_text(_VALIDATOR))
    assert not gaps, f"{_VALIDATOR_NAME}, Step 7, does not say: {gaps}"


def test_both_skills_stay_within_the_line_cap() -> None:
    for path in _SURFACE:
        lines = _text(path).count("\n")
        assert lines <= _LINE_CAP, (
            f"{path.name}: {lines} lines; the audit cap leaves {_LINE_CAP}"
        )


# --- the instruments -----------------------------------------------------------------------


def _rewrap(text: str, width: int) -> str:
    """Every prose paragraph re-flowed to `width`; headings, list items, table rows and fenced
    blocks are kept as they are."""
    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lead = block.lstrip()
        if lead.startswith(("#", "|", "-", "```")) or "```" in block or "\n- " in block:
            blocks.append(block)
            continue
        lines = textwrap.wrap(
            " ".join(block.split()),
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def test_every_check_sees_its_planted_positive() -> None:
    """A guard never shown to fail has not been shown to work."""
    # The old text: the old shape is found and every phrase of the new rule is missing, but the
    # NOTE and its threshold, which the edit must keep, are present.
    assert _old_shapes(_OLD_GROWTH) == list(_OLD_SHAPES)
    assert set(_growth_gaps(_OLD_GROWTH)) == set(_GROWTH_FACTS) - {
        "the NOTE and its threshold stay"
    }
    assert _step_5_gaps(_OLD_STEP_5) == list(_STEP_5_FACTS)
    assert _step_7_gaps(_OLD_STEP_7) == [
        "the line also runs from the tracker's Step 5",
        "after every recorded entry",
        "an alarm inside its own pass cannot report that pass stopping",
    ]

    # A half-edit: the old sentence is gone and the rule is there, but the question each check
    # is asked is missing, so exactly that phrase is reported.
    assert _old_shapes(_HALF_GROWTH) == []
    assert _growth_gaps(_HALF_GROWTH) == [
        "ask of each check whether the alarm still runs when its subject stops"
    ]

    # The new text: nothing missing, nothing old.
    assert _growth_gaps(_NEW_GROWTH) == []
    assert _old_shapes(_NEW_GROWTH) == []

    # A heading that is gone is reported, never an empty pass.
    for name, check in (
        ("growth", _growth_gaps),
        ("step 5", _step_5_gaps),
        ("step 7", _step_7_gaps),
    ):
        assert any("no heading" in p for p in _reported(name, check, "## Elsewhere\n"))

    # The words in the wrong section do not count: a phrase of Step 5 under another heading is
    # still a gap in Step 5, and the near-misses below are not old shapes.
    elsewhere = (
        "## Anti-Patterns\n\nThen report the ledger state after every recorded entry.\n\n"
        + _OLD_STEP_5
    )
    assert "after every recorded entry" in _step_5_gaps(elsewhere)
    for near in (
        "`hypothesis-validator` Step 7 reports the ledger state at the close of every pass.",
        f"Report {_STATE_LINE} after every recorded entry, so the backlog stays visible.",
        "The NOTE counts verdicts, so the backlog cannot silently accumulate unseen.",
    ):
        assert _old_shapes(near) == [], f"flagged a near-miss: {near!r}"


def test_a_phrase_under_the_next_heading_is_not_a_phrase_of_the_section() -> None:
    """A slicer that runs past the next heading finds a phrase in the section it left and reports
    nothing, so a phrase moved after its section would pass. Every phrase of each section is moved
    under the heading that follows it, for a next heading of the same level and of a higher one."""
    for name, check, fixture, facts, next_heading in (
        ("ledger growth", _growth_gaps, _NEW_GROWTH, _GROWTH_FACTS, "## Anti-Patterns"),
        (
            "tracker step 5",
            _step_5_gaps,
            _NEW_STEP_5,
            _STEP_5_FACTS,
            "## Integration Points",
        ),
        (
            "tracker step 5",
            _step_5_gaps,
            _NEW_STEP_5,
            _STEP_5_FACTS,
            "### Step 6: Next",
        ),
        (
            "validator step 7",
            _step_7_gaps,
            _NEW_STEP_7,
            _STEP_7_FACTS,
            "### Step 8: Verify",
        ),
    ):
        assert check(fixture) == [], f"{name}: the fixture must pass before it is moved"
        moved = _under_the_next_heading(fixture, next_heading)
        assert check(moved) == list(facts), (
            f"{name}: a phrase under {next_heading!r} counted"
        )


def _deleted_in_turn(view: str, facts: dict[str, str]) -> None:
    """Delete every phrase of `facts` from `view` in turn; the reader must name that phrase."""
    assert _missing(view, facts) == [], (
        "the shipped text must pass before a deletion means anything"
    )
    for name, pattern in facts.items():
        match = re.search(pattern, view, re.IGNORECASE)
        assert match is not None, (
            f"{name}: the pattern does not match the text it guards"
        )
        mutated = view[: match.start()] + view[match.end() :]
        assert name in _missing(mutated, facts), name


def test_each_phrase_deleted_in_turn_is_reported() -> None:
    """One mutation round over the real text: each deleted phrase is the one reported."""
    tracker, validator = _text(_TRACKER), _text(_VALIDATOR)
    growth = _section(tracker, _GROWTH_HEADING, _TRACKER_NAME)
    step_5 = _section(tracker, _STEP_5_HEADING, _TRACKER_NAME)
    step_7 = _section(validator, _STEP_7_HEADING, _VALIDATOR_NAME)
    _deleted_in_turn(_view(growth), _GROWTH_FACTS)
    _deleted_in_turn(_view(step_5), _STEP_5_FACTS)
    _deleted_in_turn(_view(step_7), _STEP_7_FACTS)


def test_the_old_sentence_put_back_is_caught() -> None:
    tracker, validator = _text(_TRACKER), _text(_VALIDATOR)
    old = (
        f"`hypothesis-validator` Step 7 reports {_STATE_LINE} at the close of every pass so "
        "the backlog cannot silently accumulate again."
    )
    baseline = _problems(tracker, validator)
    added = [
        p
        for p in _problems(tracker + "\n" + old + "\n", validator)
        if p not in baseline
    ]
    assert any(p.startswith("tracker: still says: ") for p in added), added


def test_the_shipped_text_has_no_problem_in_any_check() -> None:
    problems = _problems(_text(_TRACKER), _text(_VALIDATOR))
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("width", [48, 72, 130])
def test_a_rewrap_of_the_shipped_text_passes_every_check(width: int) -> None:
    tracker, validator = _text(_TRACKER), _text(_VALIDATOR)
    assert not _problems(tracker, validator), (
        "the shipped text must pass before a re-wrap"
    )
    assert _rewrap(tracker, width) != tracker, (
        "the re-wrap changed nothing, so it proves nothing"
    )
    assert _problems(_rewrap(tracker, width), _rewrap(validator, width)) == []
