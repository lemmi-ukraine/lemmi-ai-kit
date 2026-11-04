"""A dispatch brief says what to read before its first command, and the template already does.

Sessions have run a first shell call, a state command, before they had read the playbook line
that says to read the host rules and the worker preamble first. Each call was harmless. The brief
that sent them listed its state block above the line that points at the standing rules. The
template's skeleton already puts its standing rules above its goal and its context, so what was
missing is a RULE that says so to whoever writes a brief with a section order of their own. The
rule is one bullet of the rules section, directly after the bullet on preconditions, and that
bullet is judged here.

THE SURFACE, in numbers the tests assert: 5 claims and 6 phrases in one bullet of one section of
one reference, and the rules section holds 9 bullets before the new one, 10 or more after. A claim
holds when every one of its phrases is in the bullet (lower-cased, bold marks dropped, whitespace
collapsed, because the file wraps its lines). Each phrase is fired at a planted removal.

TWO SCAN SURFACES, asserted disjoint. The bullet is judged in the rules section after the fenced
skeleton, and the skeleton's section order is judged inside the fence: the fence closes before the
rules heading, and no line is in both. The bullet repeats nothing that the paste-line section or
the precondition bullet says in so many words, so each stays said once.

THE SKELETON CHECK IS GREEN ON THE OLD TEMPLATE. The skeleton already complied, so this check
cannot be shown red on the old text, and a check that is never red has not been shown to work. It
is fired at a planted skeleton in which a section that carries commands is moved above the
standing rules, once for each section, and it must name that section and no other.

CLASSES OF SHAPE covered: a phrase dropped, the bullet dropped, the bullet hollowed out (its lead
kept), a re-wrap that breaks a phrase over two lines, a section order broken, a heading missing, and
a sentence repeated that another test pins. Shapes not covered are a later round.
"""

import re
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = "plugins/orchestration/skills/orchestrate/references/brief-template.md"
_HEADING = "## Rules a dispatch brief carries"
_LEAD = "The brief's first lines say what to read before the first command."
_ANCHOR = "Preconditions are commands with expected results"
_BULLETS_BEFORE = 9
_HEADING_LINE = re.compile(r"^(#{1,6})\s")
_BOLD_LEAD = re.compile(r"^-\s+\*\*(.+?)\*\*")

# (id, claim, the phrases that must all be in the bullet; lower-cased, bold marks dropped, folded)
_CLAIMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "pointer-above-every-command",
        "the pointer to the worker preamble and to the host rules sits above every command",
        ("above every command", "host-rules file"),
    ),
    (
        "worded-as-an-order",
        "the pointer is worded as an order: read these, then run the first command",
        ("read these, then run the first command",),
    ),
    (
        "done-check-is-a-command",
        "the done check and the live-peer check count as commands",
        ("the done check and the live-peer check are commands too",),
    ),
    (
        "own-section-order",
        "a kickoff with a section order of its own does the same",
        ("a kickoff with a section order of its own must do the same",),
    ),
    (
        "first-call-ahead-of-the-read",
        "a state block above the pointer puts the first shell call ahead of the read",
        ("puts the delegate's first shell call ahead of that read",),
    ),
)
_PHRASES = tuple(phrase for _, _, phrases in _CLAIMS for phrase in phrases)

# Sentences another test pins in so many words. The bullet does not say them again.
_NOT_REPEATED = (
    "the delegate's first write is the hand-off stub",
    "preconditions are commands",
)

# The skeleton: the heading that must come first, and the headings of the sections that carry
# commands, which must come after it.
_FIRST = "## Standing rules"
_AFTER = ("## Goal", "## Context", "## Definition of done")


def _read() -> str:
    """The template as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / _TEMPLATE).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped, whitespace folded, capitals ignored: a re-wrapped line is the same line."""
    return " ".join(text.replace("**", "").split()).lower()


def _section(text: str, heading: str) -> str:
    """From the heading line to the next heading of the same or a higher level. A `#` line inside
    a fenced block is not a heading, so the skeleton's own headings never end or start a section.
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


def _items(section: str) -> list[str]:
    """The list items of the section. An item opens at a line that starts with `- ` in column 0,
    outside a fenced block, and runs to the next such line or to the end of the section."""
    items: list[list[str]] = []
    in_fence = False
    for line in section.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("- "):
            items.append([line])
        elif items:
            items[-1].append(line)
    return ["\n".join(item).rstrip() for item in items]


def _opens_with(item: str, lead: str) -> bool:
    """Whether the item, past its list marker and bold marks, begins with `lead`. The item is
    read folded, so a lead that wraps over two lines is still found."""
    return _folded(item).removeprefix("- ").startswith(lead.lower())


def _bullet(section: str, lead: str) -> str:
    """The first item that opens with `lead`; empty when none does."""
    return next((item for item in _items(section) if _opens_with(item, lead)), "")


def _bold_lead(item: str) -> str:
    found = _BOLD_LEAD.match(" ".join(item.split()))
    return found[1] if found else ""


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    folded = _folded(text)
    return [phrase for phrase in phrases if phrase not in folded]


def _gaps(text: str) -> list[str]:
    """What the template lacks of the bullet, one entry per gap; empty when it carries it all."""
    bullet = _bullet(_section(text, _HEADING), _LEAD)
    if not bullet:
        return [
            f"the place is missing from {_TEMPLATE}: no bullet opens with {_LEAD!r}"
        ]
    return [
        f"{claim}: missing {phrase!r}"
        for _, claim, phrases in _CLAIMS
        for phrase in _missing(bullet, phrases)
    ]


def _shipped_bullet() -> str:
    bullet = _bullet(_section(_read(), _HEADING), _LEAD)
    assert bullet, (
        f"the place is missing from {_TEMPLATE}: no bullet opens with {_LEAD!r}"
    )
    return bullet


def _fence(text: str) -> list[str]:
    """The lines between the first pair of code fences, the skeleton an orchestrator copies.
    Empty when there is none or it is never closed, so a check on it fails loudly."""
    inside: list[str] = []
    opened = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if opened:
                return inside
            opened = True
        elif opened:
            inside.append(line)
    return []


def _order_gaps(skeleton: list[str]) -> list[str]:
    """Why the skeleton does not put its standing rules first: one entry for each section that
    carries commands and sits above them, and one for each heading that is missing."""

    def at(prefix: str) -> int | None:
        return next(
            (n for n, line in enumerate(skeleton) if line.startswith(prefix)), None
        )

    first = at(_FIRST)
    if first is None:
        return [f"no line opens with {_FIRST!r}"]
    gaps: list[str] = []
    for heading in _AFTER:
        found = at(heading)
        if found is None:
            gaps.append(f"no line opens with {heading!r}")
        elif found < first:
            gaps.append(f"{heading!r} sits above the standing rules")
    return gaps


def _moved_above_the_rules(skeleton: list[str], heading: str) -> list[str]:
    """The skeleton with the section that opens at `heading` cut out and put back above the
    standing rules: the known positive for `_order_gaps`."""
    start = next(n for n, line in enumerate(skeleton) if line.startswith(heading))
    end = next(
        (n for n in range(start + 1, len(skeleton)) if skeleton[n].startswith("## ")),
        len(skeleton),
    )
    block, rest = skeleton[start:end], skeleton[:start] + skeleton[end:]
    first = next(n for n, line in enumerate(rest) if line.startswith(_FIRST))
    return [*rest[:first], *block, *rest[first:]]


# --- fixtures for the helpers ---------------------------------------------------------------------

# The rules section as it stood before the bullet: nine bullets, each cut to its lead and a stub.
_OLD_RULES = f"""{_HEADING}

Each rule was added after a session stopped, or ran twice, without it.

- **A paste line is printed by a command, never typed.** Stub.
- **Stop on ANY `<...>` placeholder.** Stub.
- **The return note is the first write.** Stub.
- **A project's standing decision beats a session default.** Stub.
- **{_ANCHOR}**, as the skill says. Stub.
- **A kickoff that says "any other reply is a no" says what a plain affirmative means.** Stub.
- **A brief filled in at launch ends with a marker block, and one of its preconditions
  searches for the marker.** Stub.
- **A brief never tells an agent to run a user-only skill.** Stub.
- **A brief that lists acceptance criteria names who ticks the boxes and who writes the Status
  line.** Stub.
"""
_OLD_TEMPLATE = (
    f"# Delegation brief template\n\n```markdown\n{_FIRST}\nStub.\n```\n\n{_OLD_RULES}"
)
_HOLLOW_TEMPLATE = f"{_OLD_TEMPLATE}- **{_LEAD}** A brief can list its commands.\n"


def _rewrapped(text: str, width: int) -> str:
    """The text with the bullet filled again at `width` columns, a break falling wherever it falls."""
    bullet = _bullet(_section(text, _HEADING), _LEAD)
    assert bullet, "no bullet to re-wrap"
    filled = textwrap.fill(
        " ".join(bullet.split()),
        width=width,
        subsequent_indent="  ",
        break_long_words=False,
        break_on_hyphens=False,
    )
    assert text.count(bullet) == 1, "the bullet is not in the text exactly once"
    return text.replace(bullet, filled)


# --- the tests on the shipped text ----------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_CLAIMS), len(_PHRASES)) == (5, 6)
    assert len(set(_PHRASES)) == len(_PHRASES), "a phrase stands twice in the table"
    assert all(phrase == phrase.lower() for phrase in _PHRASES), (
        "a phrase is not lower-cased"
    )
    assert _read().split("\n").count(_HEADING) == 1, f"{_HEADING!r} is not one heading"


def test_the_rules_section_gains_one_bullet_directly_after_the_precondition_bullet() -> (
    None
):
    """Red before the change: the section held nine bullets and this one was not among them."""
    items = _items(_section(_read(), _HEADING))
    leads = [_bold_lead(item) for item in items]
    assert len(items) >= _BULLETS_BEFORE + 1, f"{len(items)} bullets: {leads}"
    assert _LEAD in leads, f"no bullet leads with {_LEAD!r}: {leads}"
    at = leads.index(_LEAD)
    assert _opens_with(items[at - 1], _ANCHOR), (
        f"the bullet before it is {leads[at - 1]!r}"
    )


@pytest.mark.parametrize(
    ("claim", "phrases"),
    [(claim, phrases) for _, claim, phrases in _CLAIMS],
    ids=[slug for slug, _, _ in _CLAIMS],
)
def test_the_bullet_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    """Red before the change: the bullet did not exist."""
    missing = _missing(_shipped_bullet(), phrases)
    assert not missing, f"the bullet does not state {claim!r}: missing {missing}"


def test_the_whole_template_carries_the_bullet() -> None:
    assert _gaps(_read()) == []


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real bullet in turn is the one gap reported,
    and an empty bullet lacks every phrase of a claim. A phrase the check cannot see go would let
    the template lose its rule and stay green."""
    folded = _folded(_shipped_bullet())
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


def _repeated(bullet: str) -> list[str]:
    """The sentences another test pins that the bullet says again."""
    folded = _folded(bullet)
    return [phrase for phrase in _NOT_REPEATED if phrase in folded]


def test_the_bullet_repeats_no_sentence_that_another_test_pins() -> None:
    """The bullet names the preconditions and the first step without saying either sentence again.
    The sentences are real, so the check is not vacuous: each stands in the template, and a bullet
    that says one again is flagged, and only that one."""
    whole = _folded(_read())
    assert all(phrase in whole for phrase in _NOT_REPEATED), "a pinned sentence is gone"
    bullet = _shipped_bullet()
    assert _repeated(bullet) == []
    for phrase in _NOT_REPEATED:
        assert _repeated(f"{bullet} {phrase.capitalize()}, said again.") == [phrase]


def test_the_two_scan_surfaces_are_disjoint() -> None:
    """The bullet is judged after the fence, the skeleton's order inside it: the fence closes before
    the rules heading, so no line is in both. No phrase of this file is in another bullet of the
    section either, which is judged by another test."""
    lines = _read().split("\n")
    fences = [n for n, line in enumerate(lines) if line.lstrip().startswith("```")]
    assert len(fences) >= 2, f"{len(fences)} fence lines, not a closed fence"
    assert fences[1] < lines.index(_HEADING), (
        "the skeleton's fence does not close before the rules"
    )
    mine = _shipped_bullet()
    others = [item for item in _items(_section(_read(), _HEADING)) if item != mine]
    assert len(others) >= _BULLETS_BEFORE, f"{len(others)} other bullets"
    other_text = _folded(" ".join(others))
    shared = [phrase for phrase in _PHRASES if phrase in other_text]
    assert not shared, (
        f"phrases of this file that the other bullets also hold: {shared}"
    )


def test_the_skeleton_puts_its_standing_rules_first() -> None:
    """Green on the old template and on the new: the skeleton already complied. It is not a red
    proof, so the planted tests below fire it at a skeleton that does not."""
    skeleton = _fence(_read())
    assert skeleton, "the template has no closed code fence"
    assert _order_gaps(skeleton) == []


# --- the checks, fired at known positives and near-misses -----------------------------------------


@pytest.mark.parametrize("heading", _AFTER)
def test_a_skeleton_with_a_section_moved_above_the_rules_is_flagged(
    heading: str,
) -> None:
    """Known positive, one per section that carries commands: that section is moved above the
    standing rules, and it is the one gap reported."""
    skeleton = _fence(_read())
    planted = _moved_above_the_rules(skeleton, heading)
    assert planted != skeleton, "the planted move changed nothing"
    assert _order_gaps(planted) == [f"{heading!r} sits above the standing rules"]


def test_a_skeleton_that_lost_a_heading_is_flagged_and_an_empty_one_too() -> None:
    skeleton = _fence(_read())
    no_rules = [line for line in skeleton if not line.startswith(_FIRST)]
    assert _order_gaps(no_rules) == [f"no line opens with {_FIRST!r}"]
    no_goal = [line for line in skeleton if not line.startswith("## Goal")]
    assert _order_gaps(no_goal) == [f"no line opens with {'## Goal'!r}"]
    assert _order_gaps(_fence("no fence at all")) == [f"no line opens with {_FIRST!r}"]
    assert _fence("```\nnever closed\n") == []


def test_a_reworded_standing_rules_heading_still_passes() -> None:
    """Near-miss: the heading's own text changed, its place did not."""
    skeleton = [
        line.replace(_FIRST, f"{_FIRST} (read the files named here)")
        for line in _fence(_read())
    ]
    assert any(line.startswith(f"{_FIRST} (read the files") for line in skeleton)
    assert _order_gaps(skeleton) == []


def test_the_old_template_is_flagged_by_name_and_holds_nine_bullets() -> None:
    """Known positive: the template as it stood before the bullet reports the place as missing,
    and only that, and the counter sees the nine bullets it had."""
    gaps = _gaps(_OLD_TEMPLATE)
    assert len(gaps) == 1 and gaps[0].startswith("the place is missing from"), gaps
    assert len(_items(_section(_OLD_TEMPLATE, _HEADING))) == _BULLETS_BEFORE


def test_the_counter_sees_ten_bullets_once_the_shipped_bullet_is_in() -> None:
    """The shipped bullet put after the precondition bullet of the old section: ten, in order."""
    items = _items(_section(_OLD_TEMPLATE, _HEADING))
    at = next(n for n, item in enumerate(items) if _opens_with(item, _ANCHOR))
    items.insert(at + 1, _shipped_bullet())
    assert len(items) == _BULLETS_BEFORE + 1
    assert _opens_with(items[at], _ANCHOR) and _opens_with(items[at + 1], _LEAD)


def test_a_hollow_bullet_is_flagged_for_every_phrase() -> None:
    """Near-miss: the lead kept and the content gone. Every phrase is reported, none twice."""
    gaps = _gaps(_HOLLOW_TEMPLATE)
    assert len(gaps) == len(_PHRASES), gaps
    assert all(f"missing {phrase!r}" in " ".join(gaps) for phrase in _PHRASES)


@pytest.mark.parametrize("width", [40, 72])
def test_a_re_wrapped_bullet_passes(width: int) -> None:
    """A re-wrap changes no claim, so it must not change a verdict, a phrase broken over two lines
    included. The control: at 40 columns the wrap hides a phrase from a raw read."""
    text = _read()
    wrapped = _rewrapped(text, width)
    assert wrapped != text, "the planted re-wrap changed nothing"
    assert _gaps(wrapped) == []
    if width == 40:
        raw = wrapped.lower()
        assert any(phrase not in raw for phrase in _PHRASES), "the wrap hides no phrase"


def test_the_helpers_see_planted_text() -> None:
    """A heading that only mentions the wanted one is not it; a heading-looking line and a list
    line inside a fenced block neither end the section nor open an item; a bold lead that wraps
    over two lines is still the lead; and an item after the next heading is not in the section."""
    planted = "\n".join(
        [
            f"### An aside on {_HEADING}",
            "decoy body",
            _HEADING,
            "- **First.** One,",
            "  wrapped over two lines.",
            "- **Fenced.** Two:",
            "  ```",
            "  ## a heading inside a fence does not end the section",
            "  - a list line inside a fence is not an item",
            "  ```",
            "- **The brief's first lines say",
            "  what to read before the first command.** Three, whose bold lead wraps.",
            "## Next",
            f"- **{_LEAD}** A decoy after the next heading.",
        ]
    )
    section = _section(planted, _HEADING)
    assert section.startswith(f"{_HEADING}\n- **First.**"), section
    assert "a heading inside a fence" in section and "decoy after" not in section
    items = _items(section)
    assert [_bold_lead(i)[:6] for i in items] == ["First.", "Fenced", "The br"], items
    found = _bullet(section, _LEAD)
    assert "Three, whose bold lead wraps." in found and "decoy" not in found, found
    assert _bullet(section, "An absent lead.") == ""
    assert _section(planted, "## Absent") == ""
