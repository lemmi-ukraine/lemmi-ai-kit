"""branch-diff-review says to match the fan-out to the diff before spawning read-only lenses.

Several read-only lens agents, one per axis, were run over a small committed diff. They cost a
multiple of the diff and found nothing above Minor, and the one major finding came from the main
thread's own read of the target branch, which no lens had been asked to do. Step 3 of the skill delegates the
finding generation and had no sentence about what to run in the main thread first, which lenses are
worth a fan-out, or what to tell a lens about items accepted earlier. The new paragraph sits in
Step 3 after the paragraph on picking an effort level and before the one on confirming the diff
basis, and it is judged here.

The evidence level is part of the claim. It rests on one run with no control, so the paragraph says
that it is a calibration and not a measurement, and it gives no number for what a small diff is.

THE SURFACE, in numbers the tests assert: 6 claims and 8 phrases in one paragraph of one section of
one file. A claim holds when every one of its phrases is in the paragraph (lower-cased, bold marks
dropped, whitespace collapsed, because the file wraps its lines). Each phrase is fired at a planted
removal, and the word "lens", which the skill used nowhere else, is defined where it is first used.
The paragraph must also carry no count of tokens, minutes or files, no mention of a usage guard, and
no printed command: each class has a planted shape of its own and a near-miss.

CLASSES OF SHAPE covered: a phrase dropped, the paragraph dropped, the paragraph hollowed out (its
lead kept), a re-wrap that breaks a phrase over two lines, a paragraph that moves out of its place
between its two neighbours, an undefined word, and a figure or a command the paragraph must not
carry. Shapes not covered are a later round.
"""

import re
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL = "plugins/orchestration/skills/branch-diff-review/SKILL.md"
_EM_DASH = chr(0x2014)
_STEP_3 = f"## Step 3 {_EM_DASH} Generate findings (delegate; do not reinvent)"
_LEAD = "Match the fan-out to the diff."
_ENDS_BEFORE = "pick from blast radius, not habit."
_OPENS_AFTER = "Confirm the diff basis before trusting the findings."
_HEADING_LINE = re.compile(r"^(#{1,6})\s")
_LENS = re.compile(r"\blens", re.IGNORECASE)

# (id, claim, the phrases that must all be in the paragraph; lower-cased, bold marks dropped, folded)
_CLAIMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "lens-is-defined",
        "a lens is one read-only sub-agent per axis",
        ("read-only lenses (one sub-agent per axis)",),
    ),
    (
        "fan-out-costs-a-multiple",
        "a fan-out costs a multiple of the diff itself",
        ("costs a multiple of the diff itself",),
    ),
    (
        "main-thread-first",
        "the base drift and the gates run in the main thread before any fan-out",
        (
            "run in the main thread what needs no sub-agent",
            "the base branch's drift since the fork (step 1) and the gates",
        ),
    ),
    (
        "only-lenses-that-execute-something",
        "only the lenses that execute something are fanned out",
        ("fan out only the lenses that execute something",),
    ),
    (
        "retest-against-the-current-base",
        "each lens is told which items accepted earlier to re-test against the current base",
        (
            "which items accepted in an earlier round to re-test against the current base",
        ),
    ),
    (
        "a-calibration-from-one-sample",
        "the rule is a calibration from one sample with no control, not a measurement",
        (
            "one sample with no control",
            "a calibration, not a measurement",
        ),
    ),
)
_PHRASES = tuple(phrase for _, _, phrases in _CLAIMS for phrase in phrases)

# What the paragraph must not carry: (name, a regex, a planted shape that holds it and no other).
_FORBIDDEN: tuple[tuple[str, str, str], ...] = (
    (
        "a count of tokens, minutes or files",
        r"\b\d+(?:\.\d+)?\s*k?\s*(?:tokens?|minutes?|files?)\b",
        "the five lenses read 40 files and cost 12 minutes",
    ),
    ("a usage guard", r"\busage[- ]guard\b", "stop when the usage guard says so"),
    ("a printed command", r"`[^`]+`", "run `git diff origin/main...HEAD` first"),
)
_NEAR_MISS = "the base branch's drift since the fork (Step 1) and the gates, a multiple of the diff"


def _read() -> str:
    """The skill as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / _SKILL).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped, whitespace folded, capitals ignored: a re-wrapped line is the same line."""
    return " ".join(text.replace("**", "").split()).lower()


def _section(text: str, heading: str) -> str:
    """From the heading line to the next heading of the same or a higher level. A `#` line inside
    a fenced block is not a heading, and a heading that only mentions the wanted one is not it.
    Empty when the heading is absent."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING_LINE.match(line)
        if not body:
            if found is not None and line.rstrip() == heading:
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _blocks(section: str) -> list[str]:
    """The blank-line-separated blocks of the section, the heading line the first of them."""
    return [block for block in re.split(r"\n\s*\n", section) if block.strip()]


def _opens_with(block: str, lead: str) -> bool:
    """Whether the block, past its bold marks, begins with `lead`. The block is read folded, so a
    lead that wraps over two lines is still found."""
    return _folded(block).startswith(lead.lower())


def _paragraph(section: str, lead: str) -> str:
    """The first block that opens with `lead`; empty when none does."""
    return next((block for block in _blocks(section) if _opens_with(block, lead)), "")


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    folded = _folded(text)
    return [phrase for phrase in phrases if phrase not in folded]


def _gaps(text: str) -> list[str]:
    """What the skill lacks of the paragraph, one entry per gap; empty when it carries it all."""
    paragraph = _paragraph(_section(text, _STEP_3), _LEAD)
    if not paragraph:
        return [
            f"the place is missing from {_SKILL}: no paragraph opens with {_LEAD!r}"
        ]
    return [
        f"{claim}: missing {phrase!r}"
        for _, claim, phrases in _CLAIMS
        for phrase in _missing(paragraph, phrases)
    ]


def _shipped_paragraph() -> str:
    paragraph = _paragraph(_section(_read(), _STEP_3), _LEAD)
    assert paragraph, (
        f"the place is missing from {_SKILL}: no paragraph opens with {_LEAD!r}"
    )
    return paragraph


def _defined_where_first_used(text: str) -> bool:
    """Whether the first use of the word "lens" in the text is the definition: the word, then in
    the same clause what it means. False when the word is not in the text at all."""
    first = _LENS.search(_folded(text))
    return first is not None and _folded(text)[first.start() :].startswith(
        "lenses (one sub-agent per axis)"
    )


def _forbidden_hits(text: str) -> list[str]:
    return [
        name for name, regex, _ in _FORBIDDEN if re.search(regex, text, re.IGNORECASE)
    ]


# --- fixtures for the helpers ---------------------------------------------------------------------

# Step 3 as it stood before the paragraph: the paragraph on the effort level, then the one on the
# diff basis, and the heading of the next step to end the section.
_OLD_SKILL = f"""# Branch diff review

{_STEP_3}

Run the built-in **`/code-review`** with the branch target and an explicit effort level. Pick from
blast radius, not habit.

**Confirm the diff basis before trusting the findings.** What basis `/code-review` uses for a
branch target is **UNKNOWN** from inside this repo.

## Step 4 {_EM_DASH} The verification pass (mandatory)

Work the reference against every finding.
"""
_HOLLOW_SKILL = _OLD_SKILL.replace(
    "\n**Confirm the diff basis",
    f"\n**{_LEAD}** A review can fan out.\n\n**Confirm the diff basis",
)


def _rewrapped(text: str, width: int) -> str:
    """The text with the paragraph filled again at `width` columns, a break falling wherever it falls."""
    paragraph = _paragraph(_section(text, _STEP_3), _LEAD)
    assert paragraph, "no paragraph to re-wrap"
    filled = textwrap.fill(
        " ".join(paragraph.split()),
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    assert text.count(paragraph) == 1, "the paragraph is not in the text exactly once"
    return text.replace(paragraph, filled)


# --- the tests on the shipped text ----------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_CLAIMS), len(_PHRASES)) == (6, 8)
    assert len(set(_PHRASES)) == len(_PHRASES), "a phrase stands twice in the table"
    assert all(phrase == phrase.lower() for phrase in _PHRASES), (
        "a phrase is not lower-cased"
    )
    assert _read().split("\n").count(_STEP_3) == 1, f"{_STEP_3!r} is not one heading"


def _placement_gaps(blocks: list[str]) -> list[str]:
    """Why the paragraph is not between its two neighbours: directly after the paragraph that ends
    'pick from blast radius, not habit.' and directly before the one that opens 'Confirm the diff
    basis before trusting the findings.' One entry per gap; empty when it sits there."""
    at = next((n for n, block in enumerate(blocks) if _opens_with(block, _LEAD)), None)
    if at is None:
        return [f"no paragraph opens with {_LEAD!r}"]
    gaps: list[str] = []
    if at == 0 or not _folded(blocks[at - 1]).endswith(_ENDS_BEFORE):
        gaps.append(f"it does not follow a paragraph that ends {_ENDS_BEFORE!r}")
    if at + 1 >= len(blocks) or not _opens_with(blocks[at + 1], _OPENS_AFTER):
        gaps.append(f"it does not precede a paragraph that opens {_OPENS_AFTER!r}")
    return gaps


def test_the_paragraph_sits_between_the_effort_level_and_the_diff_basis() -> None:
    """Red before the change: Step 3 had no such paragraph. It sits inside Step 3, between the
    paragraph on the effort level and the one on the diff basis."""
    assert _placement_gaps(_blocks(_section(_read(), _STEP_3))) == []


@pytest.mark.parametrize(
    ("claim", "phrases"),
    [(claim, phrases) for _, claim, phrases in _CLAIMS],
    ids=[slug for slug, _, _ in _CLAIMS],
)
def test_the_paragraph_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    """Red before the change: the paragraph did not exist."""
    missing = _missing(_shipped_paragraph(), phrases)
    assert not missing, f"the paragraph does not state {claim!r}: missing {missing}"


def test_the_whole_skill_carries_the_paragraph() -> None:
    assert _gaps(_read()) == []


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real paragraph in turn is the one gap reported,
    and an empty paragraph lacks every phrase of a claim. A phrase the check cannot see go would
    let the skill lose its claim and stay green."""
    folded = _folded(_shipped_paragraph())
    for _, claim, phrases in _CLAIMS:
        assert not _missing(folded, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert folded.count(phrase) == 1, (
                f"{phrase!r} stands {folded.count(phrase)} times"
            )
            assert _missing(folded.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_two_scan_surfaces_are_disjoint() -> None:
    """The other paragraphs of Step 3 are judged by other tests. This file judges none of them,
    and none of its phrases is in any of them."""
    mine = _shipped_paragraph()
    others = [block for block in _blocks(_section(_read(), _STEP_3)) if block != mine]
    other_text = _folded(" ".join(others))
    shared = [phrase for phrase in _PHRASES if phrase in other_text]
    assert not shared, f"phrases of this file that other paragraphs also hold: {shared}"


def test_the_word_lens_is_defined_where_it_is_first_used() -> None:
    """The skill used the word nowhere else, so its first use is the definition."""
    assert _defined_where_first_used(_read())
    assert len(_LENS.findall(_folded(_read()))) >= 2, "the word is used only once"


def test_the_paragraph_carries_no_figure_guard_or_command_it_must_not() -> None:
    """The paragraph gives no count of tokens, minutes or files, names no usage guard and prints no
    command, so it cannot go stale with a budget, a tool or a path."""
    assert _forbidden_hits(_shipped_paragraph()) == []


# --- the checks, fired at known positives and near-misses -----------------------------------------


def test_the_old_skill_is_flagged_by_name() -> None:
    """Known positive: the skill as it stood before the paragraph reports the place as missing,
    and only that, so a red on the old text is a red for the text and not for a broken helper."""
    gaps = _gaps(_OLD_SKILL)
    assert len(gaps) == 1 and gaps[0].startswith("the place is missing from"), gaps
    assert _LEAD in gaps[0]
    assert len(_blocks(_section(_OLD_SKILL, _STEP_3))) == 3, (
        "heading and two paragraphs"
    )


def test_a_hollow_paragraph_is_flagged_for_every_phrase() -> None:
    """Near-miss: the lead kept and the content gone. Every phrase is reported, none twice."""
    assert _HOLLOW_SKILL != _OLD_SKILL, "the planted hollow paragraph changed nothing"
    gaps = _gaps(_HOLLOW_SKILL)
    assert len(gaps) == len(_PHRASES), gaps
    assert all(f"missing {phrase!r}" in " ".join(gaps) for phrase in _PHRASES)


@pytest.mark.parametrize("width", [40, 72])
def test_a_re_wrapped_paragraph_passes(width: int) -> None:
    """A re-wrap changes no claim, so it must not change a verdict, a phrase broken over two lines
    included. The control: at 40 columns the wrap hides a phrase from a raw read."""
    text = _read()
    wrapped = _rewrapped(text, width)
    assert wrapped != text, "the planted re-wrap changed nothing"
    assert _gaps(wrapped) == []
    if width == 40:
        raw = wrapped.lower()
        assert any(phrase not in raw for phrase in _PHRASES), "the wrap hides no phrase"


def test_a_paragraph_out_of_its_place_is_flagged() -> None:
    """Planted misplacement: the paragraph is whole but moved one place down, below the paragraph
    on the diff basis, and then one place up, above the paragraph on the effort level. The check
    reports both neighbours each time, and the old skeleton, which has no such paragraph, by name."""
    blocks = _blocks(_section(_read(), _STEP_3))
    assert _placement_gaps(blocks) == []
    at = next(n for n, block in enumerate(blocks) if _opens_with(block, _LEAD))
    down = [*blocks[:at], blocks[at + 1], blocks[at], *blocks[at + 2 :]]
    up = [*blocks[: at - 1], blocks[at], blocks[at - 1], *blocks[at + 1 :]]
    for moved in (down, up):
        assert moved != blocks, "the planted move changed nothing"
        assert len(_placement_gaps(moved)) == 2, _placement_gaps(moved)
    assert _placement_gaps(_blocks(_section(_OLD_SKILL, _STEP_3))) == [
        f"no paragraph opens with {_LEAD!r}"
    ]


def test_the_helpers_see_planted_text() -> None:
    """A heading that only mentions the wanted one is not it; a heading-looking line inside a
    fenced block does not end the section; a bold lead that wraps over two lines is still the
    lead; and a paragraph after the next heading is not in the section."""
    planted = "\n".join(
        [
            f"### An aside on {_STEP_3}",
            "decoy body",
            "",
            _STEP_3,
            "",
            "First paragraph.",
            "",
            "```",
            "## a heading inside a fence does not end the section",
            "```",
            "",
            "**Match the fan-out",
            "to the diff.** Second paragraph, whose bold lead wraps.",
            "",
            "## Step 4",
            "",
            f"**{_LEAD}** A decoy after the next heading.",
        ]
    )
    section = _section(planted, _STEP_3)
    assert "a heading inside a fence" in section and "decoy after" not in section
    found = _paragraph(section, _LEAD)
    assert (
        "Second paragraph, whose bold lead wraps." in found and "decoy" not in found
    ), found
    assert _paragraph(section, "An absent lead.") == ""
    assert _section(planted, "## Absent") == ""


def test_the_definition_check_flags_an_undefined_first_use_and_spares_the_definition() -> (
    None
):
    defined = "A review fans out to several read-only lenses (one sub-agent per axis). Each lens runs."
    undefined = "Each lens reports alone. Later, read-only lenses (one sub-agent per axis) are named."
    assert _defined_where_first_used(defined)
    assert not _defined_where_first_used(undefined)
    assert not _defined_where_first_used("no such word here")


@pytest.mark.parametrize(
    ("name", "regex", "planted"), _FORBIDDEN, ids=[f[0] for f in _FORBIDDEN]
)
def test_the_forbidden_check_flags_its_planted_shape_and_spares_the_near_miss(
    name: str, regex: str, planted: str
) -> None:
    assert _forbidden_hits(planted) == [name], (
        f"planted shape not flagged alone: {planted!r}"
    )
    assert _forbidden_hits(_NEAR_MISS) == []
    assert re.search(regex, planted, re.IGNORECASE), (
        "the regex does not see its own plant"
    )
