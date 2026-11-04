"""The stacked-PR document says to read a pull request's live body after someone else opens it.

A pull request that an agent prepared, with its body in a file, was opened by hand from the web
compare page. The page took the commit message as the body, so the prepared bodies never arrived,
and a review brief cited a merge-order note that existed only in the file. The document's section on
hand-over checks in a shared checkout is about what the operator does after an agent says "ready for
a PR", and it had nothing on the body. The new bullet is the second of three, directly after the
bullet on re-reading state before any "ready to PR" message, and that bullet is judged here.

The evidence level is part of the claim. GitHub's own pages on creating a pull request and on query
parameters do not say what the compare page pre-fills, so the bullet says what was seen and does
not name a case.

THE SURFACE, in numbers the tests assert: 5 claims and 8 phrases in one bullet of one section of
one document, and the section holds 2 bullets before the new one and 3 with it. A claim holds when
every one of its phrases is in the bullet (lower-cased, bold marks dropped, whitespace collapsed,
because the document wraps its lines at 100 columns). Each phrase is fired at a planted removal. The
other two bullets are judged by `test_stacked_pr_workflow_asset.py` and this file judges none of
them: no phrase here is in either, asserted.

CLASSES OF SHAPE covered: a phrase dropped, the bullet dropped, the bullet hollowed out (its lead
kept), a re-wrap that breaks a phrase over two lines, a bullet that moves out of its section, a
line wider than the document wraps, and a recipe the bullet must not carry. Shapes not covered are a
later round.
"""

import re
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DOC = "plugins/core/src/lemmi_ai_kit/assets/ai/git-stacked-pr-workflow.md"
_HEADING = "## Hand-over checks in a shared checkout"
_NEXT_HEADING = "## Is it merged? Is it safe to delete?"
_LEAD = "After someone else opens a PR you prepared, read its live body before you rely on it."
_FIRST_LEAD = 'Before any "ready to PR"'
_BULLETS_BEFORE = 2
_WRAP = 100  # the width at which the document wraps its prose
_HEADING_LINE = re.compile(r"^(#{1,6})\s")
_BOLD_LEAD = re.compile(r"^-\s+\*\*(.+?)\*\*")

# (id, claim, the phrases that must all be in the bullet; lower-cased, bold marks dropped, folded)
_CLAIMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "live-body-compared-with-the-file",
        "the live body is read with gh pr view and compared with the prepared file",
        (
            "gh pr view <n> --json body --jq .body",
            "with the prepared file",
        ),
    ),
    (
        "seen-to-take-the-commit-message",
        "a pull request opened by hand has been seen to take the commit message as its body",
        (
            "opened by hand from the web compare page",
            "has been seen to take the commit message as its body",
        ),
    ),
    (
        "a-note-only-in-the-file-never-arrived",
        "a note that exists only in the prepared file never reached the pull request",
        (
            "a merge order, a gate that was not run, a step before deploy",
            "never reached the pr",
        ),
    ),
    (
        "cite-the-live-body",
        "the live body is cited in any brief or review",
        ("cite the live body in any brief or review",),
    ),
    (
        "notes-go-in-the-commit-message-too",
        "those notes go in the commit message as well",
        ("put those notes in the commit message as well",),
    ),
)
_PHRASES = tuple(phrase for _, _, phrases in _CLAIMS for phrase in phrases)

# What the bullet must not carry: (name, a regex, a planted shape that holds it and no other).
_FORBIDDEN: tuple[tuple[str, str, str], ...] = (
    (
        "a create recipe",
        r"\bgh pr create\b",
        "open it with `gh pr create --body-file` instead",
    ),
    (
        "a body template",
        r"\bbody template\b",
        "start from a body template for every pull request",
    ),
)
_NEAR_MISS = "Compare `gh pr view <n> --json body --jq .body` with the prepared file."


def _read() -> str:
    """The document as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / _DOC).read_text(encoding="utf-8").replace("\r\n", "\n")


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
    """What the document lacks of the bullet, one entry per gap; empty when it carries it all."""
    bullet = _bullet(_section(text, _HEADING), _LEAD)
    if not bullet:
        return [f"the place is missing from {_DOC}: no bullet opens with {_LEAD!r}"]
    return [
        f"{claim}: missing {phrase!r}"
        for _, claim, phrases in _CLAIMS
        for phrase in _missing(bullet, phrases)
    ]


def _shipped_bullet() -> str:
    bullet = _bullet(_section(_read(), _HEADING), _LEAD)
    assert bullet, f"the place is missing from {_DOC}: no bullet opens with {_LEAD!r}"
    return bullet


def _too_wide(text: str) -> list[str]:
    """The lines of the text wider than the document wraps."""
    return [line for line in text.split("\n") if len(line) > _WRAP]


def _forbidden_hits(text: str) -> list[str]:
    return [
        name for name, regex, _ in _FORBIDDEN if re.search(regex, text, re.IGNORECASE)
    ]


# --- fixtures for the helpers ---------------------------------------------------------------------

# The section as it stood before the bullet: two bullets, the second with a fenced command in it.
_OLD_DOC = f"""# Stacked PR Workflow

{_HEADING}

The operator acts through the IDE in a shared checkout.

- **Before any "ready to PR" or "next step" message**, re-read in the same turn the head, the
  staged files and the remote tip.
- **Re-read the base after any pause and before the commit.** Write the base commit down:

  ```powershell
  ## a comment inside a fence is not a heading
  git fetch origin <trunk>
  ```

  If the base moved, compare the blobs.

{_NEXT_HEADING}

After a stack is rebased or squash-merged, no single git check answers this.
"""


def _swap(text: str, old: str, new: str) -> str:
    """A planted edit that must find its anchor exactly once, so it cannot change nothing."""
    assert text.count(old) == 1, f"planted edit: {old!r} stands {text.count(old)} times"
    return text.replace(old, new)


_LAST_LINE = "\n  If the base moved, compare the blobs.\n"
_HOLLOW_DOC = _swap(
    _OLD_DOC,
    _LAST_LINE,
    f"{_LAST_LINE}- **{_LEAD}** A body can differ from its file.\n",
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
    assert (len(_CLAIMS), len(_PHRASES)) == (5, 8)
    assert len(set(_PHRASES)) == len(_PHRASES), "a phrase stands twice in the table"
    assert all(phrase == phrase.lower() for phrase in _PHRASES), (
        "a phrase is not lower-cased"
    )
    assert _read().split("\n").count(_HEADING) == 1, f"{_HEADING!r} is not one heading"


def test_the_section_gains_one_bullet_directly_after_its_first() -> None:
    """Red before the change: the section held two bullets. The new one is the second of three,
    inside the section that ends at the next heading, with no heading of its own in between."""
    section = _section(_read(), _HEADING)
    items = _items(section)
    leads = [_bold_lead(item) for item in items]
    assert len(items) == _BULLETS_BEFORE + 1, f"{len(items)} bullets: {leads}"
    assert _opens_with(items[0], _FIRST_LEAD), f"the first bullet is {leads[0]!r}"
    assert _opens_with(items[1], _LEAD), f"the second bullet is {leads[1]!r}"
    assert not [line for line in section.split("\n")[1:] if _HEADING_LINE.match(line)]
    assert _read().split("\n").count(_NEXT_HEADING) == 1, (
        "the section no longer ends there"
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


def test_the_whole_document_carries_the_bullet() -> None:
    assert _gaps(_read()) == []


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real bullet in turn is the one gap reported,
    and an empty bullet lacks every phrase of a claim. A phrase the check cannot see go would let
    the document lose its claim and stay green."""
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


def test_the_two_scan_surfaces_are_disjoint() -> None:
    """The other bullets of the section are judged by the document's own test. This file judges
    none of them, and none of its phrases is in either."""
    mine = _shipped_bullet()
    others = [item for item in _items(_section(_read(), _HEADING)) if item != mine]
    assert len(others) == _BULLETS_BEFORE, f"{len(others)} other bullets"
    other_text = _folded(" ".join(others))
    shared = [phrase for phrase in _PHRASES if phrase in other_text]
    assert not shared, (
        f"phrases of this file that the other bullets also hold: {shared}"
    )


def test_the_bullet_wraps_at_the_width_the_document_uses() -> None:
    assert not _too_wide(_shipped_bullet()), _too_wide(_shipped_bullet())


def test_the_bullet_carries_no_recipe_it_must_not() -> None:
    """The bullet says to compare and to cite. It is no recipe for opening a pull request and no
    template for its body."""
    assert _forbidden_hits(_shipped_bullet()) == []


# --- the checks, fired at known positives and near-misses -----------------------------------------


def test_the_old_document_is_flagged_by_name_and_holds_two_bullets() -> None:
    """Known positive: the document as it stood before the bullet reports the place as missing,
    and only that, and the counter sees the two bullets the section had, the fenced command of
    the second one inside it."""
    gaps = _gaps(_OLD_DOC)
    assert len(gaps) == 1 and gaps[0].startswith("the place is missing from"), gaps
    items = _items(_section(_OLD_DOC, _HEADING))
    assert len(items) == _BULLETS_BEFORE
    assert "git fetch origin <trunk>" in items[1] and "compare the blobs" in items[1]


def test_a_hollow_bullet_is_flagged_for_every_phrase() -> None:
    """Near-miss: the lead kept and the content gone. Every phrase is reported, none twice."""
    gaps = _gaps(_HOLLOW_DOC)
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
            "- **After someone else opens a PR you prepared,",
            "  read its live body before you rely on it.** Three, whose bold lead wraps.",
            _NEXT_HEADING,
            f"- **{_LEAD}** A decoy after the next heading.",
        ]
    )
    section = _section(planted, _HEADING)
    assert section.startswith(f"{_HEADING}\n- **First.**"), section
    assert "a heading inside a fence" in section and "decoy after" not in section
    items = _items(section)
    assert [_bold_lead(i)[:6] for i in items] == ["First.", "Fenced", "After "], items
    found = _bullet(section, _LEAD)
    assert "Three, whose bold lead wraps." in found and "decoy" not in found, found
    assert _bullet(section, "An absent lead.") == ""
    assert _section(planted, "## Absent") == ""


def test_the_width_check_flags_a_wide_line_and_spares_one_at_the_limit() -> None:
    assert _too_wide("x" * (_WRAP + 1)) == ["x" * (_WRAP + 1)]
    assert _too_wide("x" * _WRAP) == []
    assert _too_wide(f"{'x' * _WRAP}\n{'y' * (_WRAP + 5)}") == ["y" * (_WRAP + 5)]


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
