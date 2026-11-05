"""The dispatch gates say what follows when the operator's reply picks no option.

Section 8 of `orchestrate/references/dispatch-gates.md` says that a bare "proceed" after a stop at
an action only the operator can take is unresolved, and that the session asks ONE question with
explicit options. It said nothing about the reply to that question, so a session that got another
non-answer could ask a second time and a third; and it said nothing about a question that got no
reply at all, so one session waited and another chose for itself.

Two bullets now follow the bare-"proceed" bullet in the same section:

* An answer that picks no option is a deferral. The one question a bare "proceed" draws is asked
  once; a reply that picks none of its options leaves it open; the deferral is recorded with the
  path each option would take, and the same question is not asked again unless the operator gives
  a clear yes. That is how the bullet fits the one before it: that one sets the number of asks at
  one, this one says what the one ask leaves behind when it draws no choice.
* When a default was offered and no answer arrives, take exactly the default and say so. A tighter
  option the session would have preferred goes into the report as a suggestion, not into the work.

THE SURFACE, in numbers the tests assert: 2 claims and 5 sentences in one file, all inside section
8, each sentence inside the bullet its claim names. A claim holds when its bullet holds every one
of its sentences whole (lower-cased, bold marks dropped, whitespace collapsed), so a clause cannot
be dropped while the rest of its sentence still matches. Each sentence occurs once in the section
and is fired at a planted removal. The older bullets of the section, its title and the opening
paragraph of the file are held by other tests and are not asserted here, except that the bullet
these two read beside must still be there.
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
_SECTION_8 = "## 8."
_HEADING = re.compile(r"^(#{1,6})\s")

# The older bullet these two read beside: the first sentence of its bold lead.
_BARE_PROCEED_LEAD = 'a bare "proceed" after such a stop is unresolved.'

# (claim id, the sentences of its bullet, whole, in order; lower-cased, bold marks dropped,
# whitespace collapsed). The first sentence of a claim is the bold lead that opens its bullet.
# The claims, in order: an answer that picks no option is a deferral (the lead, how it fits the
# one question a bare "proceed" draws, what is recorded and that the question is not asked
# again); a default that was offered and not answered is taken exactly, and a tighter option is
# a suggestion.
_CLAIMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "deferral",
        (
            "an answer that picks no option is a deferral.",
            'the one question a bare "proceed" draws is asked once: a reply that picks none of '
            'its options (a remark, a rule, another bare "proceed") leaves it open.',
            "record the deferral, with the path each option would take, and do not ask the same "
            "question again unless the operator gives a clear yes.",
        ),
    ),
    (
        "default",
        (
            "when a default was offered and no answer arrives, take exactly the default and say "
            "so.",
            "a tighter option you would have preferred goes into the report as a suggestion, "
            "not into the work.",
        ),
    ),
)
_SENTENCES = tuple(sentence for _, sentences in _CLAIMS for sentence in sentences)
_LEADS = tuple(sentences[0] for _, sentences in _CLAIMS)

# Section 8 as it stood before the two bullets were added: the known positive the checks must see
# the gap in.
_OLD_SECTION_8 = """\
## 8. A report to the operator opens with the answer, or with the action only the operator can take

Evidence level: observed in one project's notes, not yet repeated; defaults to adopt and
re-measure, not calibrated rules.

- **A long deliverable carries the short answer.** Put the two- or three-line answer to the question
  the operator literally asked before the evidence, so nobody has to ask for the restatement; for an
  initiative plan that is the goal, the session count by type and the pull-request stack.
- **A stop at an action only the operator can take opens with that action and its owner.** When the
  work is blocked on something only the operator can do (a credential, a push, a release, a
  decision), the report's first lines say what the action is, who does it and what stays blocked
  until then, before any state.
- **A bare "proceed" after such a stop is unresolved.** It does not name the action: re-check the
  gate with the command that reads it, and while it is closed ask ONE question with explicit
  options; never read the word as consent to bypass the gate. A "proceed" that answers a presented
  spec at its approval stop is the approval that stop asked for; this rule is about a stop at an
  action the operator has to take.
"""


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


def _item_lines(text: str) -> tuple[list[str], list[list[str]]]:
    """The lines before the first list item, and the lines of every item. An item starts at a
    line that begins with "- " outside a fenced block and runs to the next such line, so a line
    that continues it is part of it whether it is indented or sits in column 0."""
    head: list[str] = []
    items: list[list[str]] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("- "):
            items.append([line])
        elif items:
            items[-1].append(line)
        else:
            head.append(line)
    return head, items


def _bullet(text: str, lead: str) -> str:
    """The flat text of the first list item that opens with `lead`; empty when none does. An
    item that merely contains the lead further on is not that item."""
    for lines in _item_lines(text)[1]:
        flat = _flat("\n".join(lines)[2:])
        if flat.startswith(lead):
            return flat
    return ""


def _gaps(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _rewrap(text: str, width: int) -> str:
    """The list items of `text` re-wrapped at `width` columns, a continuation line indented by two
    spaces, whatever the file's own wrap was: a bold lead can break over two lines. Any other
    line is kept as it is."""
    head, items = _item_lines(text)
    out = list(head)
    for lines in items:
        words = " ".join(lines)[2:].split()
        row = "-"
        for word in words:
            if len(row) + 1 + len(word) > width and row.strip("- "):
                out.append(row)
                row = " "
            row = f"{row} {word}"
        out.append(row)
    return "\n".join(out) + "\n"


def _section_8() -> str:
    section = _section(_read(), _SECTION_8)
    assert section.strip(), "section 8 is missing from dispatch-gates.md"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_CLAIMS), len(_SENTENCES)) == (2, 5)
    assert len(set(_SENTENCES)) == len(_SENTENCES), "a sentence is listed twice"
    for sentence in _SENTENCES:
        others = [other for other in _SENTENCES if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    assert _GATES.is_file(), f"{_GATES} is not a file"
    assert _read().strip(), "dispatch-gates.md is empty"


def test_section_8_keeps_the_bullet_these_two_read_beside() -> None:
    """Passes before and after: the new text points at the one question a bare "proceed" draws,
    so the bullet that says so must still be there. It also shows the finder sees the section
    that did not yet hold the new bullets."""
    assert _bullet(_section_8(), _BARE_PROCEED_LEAD), (
        "section 8 has lost the bare-proceed bullet the new bullets read beside"
    )
    assert _bullet(_OLD_SECTION_8, _BARE_PROCEED_LEAD)


@pytest.mark.parametrize(("claim", "sentences"), _CLAIMS, ids=[c[0] for c in _CLAIMS])
def test_section_8_states_the_claim(claim: str, sentences: tuple[str, ...]) -> None:
    """Red before the change: section 8 had three bullets and neither of these."""
    bullet = _bullet(_section_8(), sentences[0])
    assert bullet, f"no bullet of section 8 opens with {sentences[0]!r}"
    missing = _gaps(bullet, sentences)
    assert not missing, f"the {claim!r} bullet does not state: {missing}"


# --- the checks can fail -----------------------------------------------------------------------


def test_the_old_section_8_lacks_both_claims() -> None:
    """Known positive: the section as it stood has neither bullet, and the finder says so for
    each claim; a sentence of either is in no part of it."""
    for lead in _LEADS:
        assert _bullet(_OLD_SECTION_8, lead) == "", lead
    assert _gaps(_flat(_OLD_SECTION_8), _SENTENCES) == list(_SENTENCES)


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of the real section is the one gap reported, and an
    empty section lacks every sentence. A sentence that occurs twice would let a clause go and
    stay green."""
    flat = _flat(_section_8())
    assert _gaps(flat, _SENTENCES) == [], "a sentence is missing at the start"
    for sentence in _SENTENCES:
        assert flat.count(sentence) == 1, (
            f"{sentence!r} occurs {flat.count(sentence)} times"
        )
        assert _gaps(flat.replace(sentence, ""), _SENTENCES) == [sentence], sentence
    assert _gaps("", _SENTENCES) == list(_SENTENCES)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal, one per sentence: the words after the last comma or colon of a
    sentence are cut out of the real bullet, and the claim then reports exactly that sentence.
    A check on a fragment of the sentence would stay green."""
    section = _section_8()
    for claim, sentences in _CLAIMS:
        bullet = _bullet(section, sentences[0])
        assert bullet, f"no bullet of section 8 opens with {sentences[0]!r}"
        assert not _gaps(bullet, sentences), claim
        for sentence in sentences[1:]:
            tail = re.split(r"[,:] ", sentence)[-1]
            assert tail != sentence, f"no clause to cut from {sentence!r}"
            assert bullet.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
            assert _gaps(bullet.replace(tail, ""), sentences) == [sentence], (
                claim,
                sentence,
            )


@pytest.mark.parametrize("width", [40, 72, 100])
def test_a_rewrapped_and_reemphasised_section_still_holds_every_claim(
    width: int,
) -> None:
    """Near-miss that must NOT be reported: the real section with its list items re-wrapped at
    `width` columns, so that a bold lead breaks over two lines, and bold marks around one more
    word is the same text."""
    real = _section_8()
    assert _gaps(_flat(real), _SENTENCES) == [], (
        "section 8 lacks a sentence at the start"
    )
    reshaped = _rewrap(real, width).replace("suggestion", "**suggestion**", 1)
    assert reshaped != real
    assert "**suggestion**" in reshaped, "the planted emphasis changed nothing"
    for claim, sentences in _CLAIMS:
        bullet = _bullet(reshaped, sentences[0])
        assert bullet, f"{claim}: the re-wrapped bullet was not found"
        assert _gaps(bullet, sentences) == [], claim


def test_the_claims_are_judged_inside_section_8_only() -> None:
    """Planted move: the two bullets cut out of section 8 and put into the section before it are
    a section 8 that lacks both claims and exactly them. A search of the whole file would still
    find every sentence and pass, which is why each claim is read from section 8 alone."""
    section = _section_8()
    head, items = _item_lines(section)
    moved = [lines for lines in items if _flat("\n".join(lines)[2:]).startswith(_LEADS)]
    kept = [lines for lines in items if lines not in moved]
    assert len(moved) == len(_LEADS), "the bullets to move are not in section 8"
    text = (
        "## 7. Elsewhere\n\n"
        + "\n".join(line for lines in moved for line in lines)
        + "\n\n"
        + "\n".join([*head, *(line for lines in kept for line in lines)])
        + "\n"
    )
    after = _section(text, _SECTION_8)
    assert after.strip(), "the planted text has no section 8"
    for lead in _LEADS:
        assert _bullet(after, lead) == "", lead
    assert _gaps(_flat(after), _SENTENCES) == list(_SENTENCES)
    assert _gaps(_flat(text), _SENTENCES) == [], "a whole-file search would have passed"


_SECTIONS = "\n".join(
    [
        "#### 8. A look-alike that only contains the wanted prefix",
        "## 8. First",
        "first body",
        "### 8.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "## 9. nor is this one",
        "```",
        "## 9. Second",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, runs to the end of the text
    when none follows, and finds nothing for a heading that is not there, so an absent section is
    reported and not read as an empty pass."""
    first = _section(_SECTIONS, "## 8.")
    assert first.startswith("## 8. First"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert "second body" in _section(_SECTIONS, "## 9. Second")
    assert _section(_SECTIONS, "## 99.") == ""
    assert _gaps(_flat(_section(_SECTIONS, "## 99.")), _SENTENCES) == list(_SENTENCES)


_ITEMS = "\n".join(
    [
        "Evidence line before the list.",
        "",
        "- **The first lead is",
        "  broken over two lines.** Its body says the second lead is not here.",
        "- **The second lead.** A body that quotes the first lead is",
        "the first lead is broken over two lines. again, in column 0.",
        "```text",
        "- **A fenced lead.** It is not an item.",
        "```",
        "- **The third lead.** Last body.",
        "",
    ]
)


def test_the_bullet_finder_keeps_its_edges() -> None:
    """The finder reads an item whole whether its lead is bold or broken over two lines and
    whether its continuation lines are indented or in column 0, stops at the next item, does not
    take a line inside a fence for an item, does not take an item that only contains the lead
    for the one that opens with it, and finds nothing for a lead that is absent."""
    first = _bullet(_ITEMS, "the first lead is broken over two lines.")
    assert first.startswith("the first lead is broken over two lines. its body"), first
    assert "the second lead" in first and "a body that quotes" not in first, first
    second = _bullet(_ITEMS, "the second lead.")
    assert "in column 0" in second and "fenced lead" in second, second
    assert "last body" not in second, second
    assert _bullet(_ITEMS, "a fenced lead.") == ""
    assert _bullet(_ITEMS, "its body says") == ""
    assert _bullet(_ITEMS, "the third lead.").endswith("last body.")
    assert _bullet(_ITEMS, "an absent lead.") == ""
    assert _bullet("", "an absent lead.") == ""
    head, items = _item_lines(_ITEMS)
    assert head == ["Evidence line before the list.", ""]
    assert len(items) == 3, [lines[0] for lines in items]
