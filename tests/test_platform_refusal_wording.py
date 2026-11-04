"""agent-delegate says what to do when the platform refuses a sub-agent in the middle of its run.

A read-only sub-agent was refused part-way through by an organization-policy error (an HTTP 403
whose text says the organization had disabled the access it used) while its parent session kept
working, and the same route answered again later. The last section of agent-delegate's SKILL.md,
"Resuming a worker", had two bullets, a usage limit and a session near its window, and said
nothing about a refusal that is a decision of the platform and not a fault of the worker. The third
bullet is judged here, and only it: the first two belong to
`test_delegated_session_rules_wording.py`.

THE SURFACE, in numbers the tests assert: 7 claims and 11 phrases, all inside one bullet of one
section of one file. A claim holds when every one of its phrases is in the bullet (lower-cased, bold
marks dropped, whitespace collapsed, because the file wraps its lines). Each phrase is fired at a
planted removal, so a phrase the check could not see go is not in the table. The helpers that cut
the section and the bullet out of the file are fired at planted text with a decoy that only a wrong
cut would pick up, and the old section, as it stood before the bullet, must be flagged by name.
The bullet must also say the refusal in words: the error code of one provider is volatile, and a
count of hours is a figure that goes stale.

CLASSES OF SHAPE covered: a phrase dropped, the bullet dropped, the bullet hollowed out (its lead
kept), a re-wrap that breaks a phrase over two lines, a bold lead that wraps, a bullet that moves
out of its section, and a volatile figure in place of words. Shapes not covered are a later round.
"""

import re
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL = "plugins/orchestration/skills/agent-delegate/SKILL.md"
_HEADING = "## Resuming a worker"
_LEAD = "After a refusal by the platform."
# The two bullets that came first. The delegated-session test judges them and this file does not.
_OLD_LEADS = ("After a usage limit.", "Near the context window.")
_HEADING_LINE = re.compile(r"^(#{1,6})\s")
_BOLD_LEAD = re.compile(r"^-\s+\*\*(.+?)\*\*")

# (id, claim, the phrases that must all be in the bullet; lower-cased, bold marks dropped, folded)
_CLAIMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "permission-decision",
        "a refusal by the platform is a permission decision, and no route around it is taken",
        (
            "a permission decision, not a tool failure",
            "do not route around it",
        ),
    ),
    (
        "quoted-verbatim",
        "the refusal is quoted verbatim in the report",
        ("quote the refusal verbatim in the report",),
    ),
    (
        "partial-report-new-name",
        "the partial report is kept under a new name, so the return-note rule does not stop a rerun",
        (
            "under a new name",
            "an existing return note stops a second run",
        ),
    ),
    (
        "retry-once-later",
        "the route is retried at most once, at a later gate",
        ("at most once, at a later gate",),
    ),
    (
        "pasteable-session-prompt",
        "a second refusal hands the operator the brief as a pasteable session prompt",
        (
            "hand the operator the brief as a pasteable session prompt",
            "the `cross-session` worker",
        ),
    ),
    (
        "independent-read-missing",
        "the report says which independent read is missing, and the decision passes to the operator",
        (
            "which independent read is missing",
            "passes to the operator",
        ),
    ),
    (
        "evidence-tag",
        "the evidence level is stated: observed more than once",
        ("observed more than once",),
    ),
)
_PHRASES = tuple(phrase for _, _, phrases in _CLAIMS for phrase in phrases)

# What the bullet must not carry. Each alternative has a planted shape of its own, and the
# error code is built from fragments so that this file does not hold it either.
_CODE = "oauth" + "_org_" + "not_allowed"
_VOLATILE = re.compile(rf"{_CODE}|\bhours\b", re.IGNORECASE)
_VOLATILE_PLANTED = (f"the error was {_CODE}", "the route answered again 3 hours later")
_VOLATILE_NEAR_MISS = (
    "an HTTP 403 whose text says the organization has disabled the access it used; "
    "the same route answered again later"
)


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
    """What the skill lacks of the bullet, one entry per gap; empty when it carries it all."""
    bullet = _bullet(_section(text, _HEADING), _LEAD)
    if not bullet:
        return [f"the place is missing from {_SKILL}: no bullet opens with {_LEAD!r}"]
    return [
        f"{claim}: missing {phrase!r}"
        for _, claim, phrases in _CLAIMS
        for phrase in _missing(bullet, phrases)
    ]


def _shipped_bullet() -> str:
    bullet = _bullet(_section(_read(), _HEADING), _LEAD)
    assert bullet, f"the place is missing from {_SKILL}: no bullet opens with {_LEAD!r}"
    return bullet


# --- fixtures for the helpers ---------------------------------------------------------------------

# The section as it stood before the bullet: two bullets, the bullet this file judges absent.
_OLD_SKILL = f"""# Delegate

## Second-opinion mode

Run the worker read-only on the question.

{_HEADING}

- **After a usage limit.** A sub-agent that a usage limit stopped can be resumed with `SendMessage`
  once requests are accepted again. Say what you measured and what is left.
- **Near the context window.** Do not resume a session that ended near its window: the resume
  compacts almost at once.
"""
_HOLLOW_SKILL = (
    f"{_OLD_SKILL}- **{_LEAD}** A sub-agent can fail in the middle of its run.\n"
)


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
    assert (len(_CLAIMS), len(_PHRASES)) == (7, 11)
    assert len(set(_PHRASES)) == len(_PHRASES), "a phrase stands twice in the table"
    assert all(phrase == phrase.lower() for phrase in _PHRASES), (
        "a phrase is not lower-cased"
    )
    assert (_REPO_ROOT / _SKILL).read_text(encoding="utf-8").strip(), _SKILL
    assert _read().split("\n").count(_HEADING) == 1, f"{_HEADING!r} is not one heading"


def test_the_section_holds_the_bullet_after_the_two_it_had() -> None:
    """Red before the change: the section had two bullets. The count is derived from the leads
    the other test judges plus the one this file judges, and the new bullet comes last."""
    items = _items(_section(_read(), _HEADING))
    assert len(items) == len(_OLD_LEADS) + 1, (
        f"{len(items)} bullets: {[_bold_lead(i) for i in items]}"
    )
    assert [_bold_lead(item) for item in items] == [*_OLD_LEADS, _LEAD]


def test_the_two_scan_surfaces_are_disjoint() -> None:
    """The bullets the delegated-session test judges and the one this file judges share no lead and
    no phrase: a bullet judged by a rule that does not apply to it would read as better covered."""
    assert _LEAD not in _OLD_LEADS
    section = _section(_read(), _HEADING)
    mine = _shipped_bullet()
    others = [item for item in _items(section) if item != mine]
    assert len(others) == len(_OLD_LEADS), [_bold_lead(item) for item in others]
    assert not [lead for lead in _OLD_LEADS if _opens_with(mine, lead)]
    other_text = _folded(" ".join(others))
    shared = [phrase for phrase in _PHRASES if phrase in other_text]
    assert not shared, (
        f"phrases of this file that the other bullets also hold: {shared}"
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


def test_the_whole_skill_carries_the_bullet() -> None:
    assert _gaps(_read()) == []


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real bullet in turn is the one gap reported,
    and an empty bullet lacks every phrase of a claim. A phrase the check cannot see go would let
    the skill lose its claim and stay green."""
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


def test_the_bullet_says_the_refusal_in_words() -> None:
    """The shipped bullet names no provider error code and no count of hours."""
    hits = [m[0] for m in _VOLATILE.finditer(_shipped_bullet())]
    assert not hits, f"a volatile figure stands in the bullet: {hits}"


# --- the checks, fired at known positives and near-misses -----------------------------------------


def test_the_old_section_is_flagged_by_name() -> None:
    """Known positive: the skill as it stood before the bullet reports the place as missing, and
    only that, so a red on the old text is a red for the text and not for a broken helper."""
    gaps = _gaps(_OLD_SKILL)
    assert len(gaps) == 1 and gaps[0].startswith("the place is missing from"), gaps
    assert _LEAD in gaps[0]


def test_a_hollow_bullet_is_flagged_for_every_phrase() -> None:
    """Near-miss: the lead kept and the content gone. Every phrase is reported, none twice."""
    gaps = _gaps(_HOLLOW_SKILL)
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
    """A heading that only mentions the wanted one is not it; a `#` line and a list line inside a
    fenced block neither end the section nor open an item; a bold lead that wraps over two lines
    is still the lead; and an item after the next heading is not in the section."""
    planted = "\n".join(
        [
            f"### An aside on {_HEADING}",
            "decoy body",
            _HEADING,
            "- **First.** One,",
            "  wrapped over two lines.",
            "- **Fenced.** Two:",
            "  ```",
            "  # a comment inside a fence is not a heading",
            "  - a list line inside a fence is not an item",
            "  ```",
            "- **After a refusal",
            "  by the platform.** Three, whose bold lead wraps.",
            "## Next",
            f"- **{_LEAD}** A decoy after the next heading.",
        ]
    )
    section = _section(planted, _HEADING)
    assert section.startswith(f"{_HEADING}\n- **First.**"), section
    assert "a comment inside a fence" in section and "decoy after" not in section
    items = _items(section)
    assert [_bold_lead(i)[:6] for i in items] == ["First.", "Fenced", "After "], items
    found = _bullet(section, _LEAD)
    assert "Three, whose bold lead wraps." in found and "decoy" not in found, found
    assert _bullet(section, "An absent lead.") == ""
    assert _section(planted, "## Absent") == ""


def test_the_volatile_check_flags_each_planted_shape_and_spares_the_near_miss() -> None:
    for shape in _VOLATILE_PLANTED:
        assert _VOLATILE.search(shape), f"not flagged: {shape!r}"
    assert not _VOLATILE.search(_VOLATILE_NEAR_MISS)
    alternatives = [re.compile(a, re.IGNORECASE) for a in (_CODE, r"\bhours\b")]
    hit = [
        [i for i, a in enumerate(alternatives) if a.search(s)]
        for s in _VOLATILE_PLANTED
    ]
    assert hit == [[0], [1]], (
        f"each planted shape must be hit by its own alternative alone: {hit}"
    )
