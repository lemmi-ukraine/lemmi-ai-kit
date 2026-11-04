"""The worker preamble says how a delegated worker reports a stop at an operator-only action.

Section 8 of the orchestrator's dispatch gates says that a stop at an action only the operator
can take opens its report with that action and its owner, and that a bare "proceed" after such a
stop is unresolved. A delegated worker is not pointed at that file: the worker preamble is the one
text it is told to read, and its section on returning a result said nothing about either. So a
worker that stopped at an action only the operator could take could lead with state, and one that
was answered with a bare "proceed" could take the word for consent to bypass the gate.

ONE bullet of section 4 of the preamble ("Returning your result") now says both: the stop opens
the return with the action and its owner, ahead of any state and ahead of the acceptance table
that the last bullet of the section asks for; and a bare "proceed" in reply to such a stop is
unresolved, names no action and is no consent to bypass the gate, so the worker re-checks the gate
with the command that reads it and, while it is closed, asks one question with explicit options.
The words "in reply to such a stop" keep the rule from reaching a "proceed" that answers a
presented spec at its approval stop.

THE SURFACE, in numbers the tests assert: 1 claim and 3 sentences in one file, all inside section
4, in one bullet. The claim holds when that bullet holds every one of its sentences whole
(lower-cased, bold marks dropped, whitespace collapsed), so a clause cannot be dropped while the
rest of its sentence still matches. Each sentence occurs once in the section and is fired at a
planted removal. Which bullet closes the section, the other sections of the preamble and the
orchestrator's own copy of the rule are held by other tests and are not asserted here.
"""

import re
from pathlib import Path

import pytest

_PREAMBLE = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "agent-delegate"
    / "assets"
    / "worker-preamble.md"
)
_DOT = chr(0xB7)  # the middle dot in the preamble's numbered headings
_SECTION_3 = f"## 3 {_DOT}"
_SECTION_4 = f"## 4 {_DOT} Returning your result"
_HEADING = re.compile(r"^(#{1,6})\s")

# The bullets of section 4 that stay: the first, and the one that returns the acceptance table.
_KEPT_LEADS = (
    "your final message *is* the return value",
    "return acceptance criteria as a table.",
)

# The sentences of the new bullet, whole, in order (lower-cased, bold marks dropped, whitespace
# collapsed). The first is the bold lead that opens the bullet.
_SENTENCES: tuple[str, ...] = (
    "a stop at an action only the operator can take opens your return with that action and its "
    "owner.",
    "say what stays blocked until then, before any state or table.",
    'a bare "proceed" in reply to such a stop is unresolved: it names no action and is not '
    "consent to bypass the gate, so re-check the gate with the command that reads it and, "
    "while it is closed, ask one question with explicit options.",
)
_LEAD = _SENTENCES[0]

# Section 4 as it stood before the bullet was added, shortened to the bullets that carry no
# character outside ASCII: the known positive the checks must see the gap in.
_OLD_SECTION_4 = f"""\
{_SECTION_4}

- **Results are claims.** State what you ran and what it output. If you could not verify
  something, say UNKNOWN and name what would settle it.
- **Run your completion checklist BEFORE writing your return, never after.** A return written
  first carries whatever the review would have corrected, and the orchestrator inherits it as
  fact.
- **If your brief turns out to be wrong, say so explicitly and early.** A brief premise that does
  not reproduce is the single most common defect in delegated work (measured at roughly half of
  sessions). Report the discrepancy as a finding; do not quietly work around it.
- **Return acceptance criteria as a table.** If your brief points at a task file or lists
  acceptance criteria, return them as a table before the rest of your report: one state each
  (met, not met, superseded or operator-owned) and one evidence pointer each. Your brief names who
  ticks the boxes and who writes the Status line; with no such line, edit no task file you do not
  own.
"""


def _read() -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return _PREAMBLE.read_text(encoding="utf-8").replace("\r\n", "\n")


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


def _section_4() -> str:
    section = _section(_read(), _SECTION_4)
    assert section.strip(), "section 4 is missing from worker-preamble.md"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_SENTENCES) == 3
    assert len(set(_SENTENCES)) == len(_SENTENCES), "a sentence is listed twice"
    for sentence in _SENTENCES:
        others = [other for other in _SENTENCES if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    assert _PREAMBLE.is_file(), f"{_PREAMBLE} is not a file"
    text = _read()
    assert text.strip(), "worker-preamble.md is empty"
    headings = [line for line in text.split("\n") if line.startswith(_SECTION_4)]
    assert len(headings) == 1, f"{len(headings)} headings start with {_SECTION_4!r}"


def test_section_4_keeps_the_bullets_around_the_new_one() -> None:
    """Passes before and after: the first bullet and the acceptance bullet are still in section 4,
    which also shows the finder sees the section that did not yet hold the new bullet."""
    section = _section_4()
    for lead in _KEPT_LEADS:
        assert _bullet(section, lead), (
            f"section 4 has lost the bullet that opens {lead!r}"
        )
    assert _bullet(_OLD_SECTION_4, _KEPT_LEADS[1])


def test_section_4_states_the_claim() -> None:
    """Red before the change: section 4 had seven bullets and none of this."""
    bullet = _bullet(_section_4(), _LEAD)
    assert bullet, f"no bullet of section 4 opens with {_LEAD!r}"
    missing = _gaps(bullet, _SENTENCES)
    assert not missing, f"the bullet does not state: {missing}"


def test_the_claim_is_one_bullet_with_one_home() -> None:
    """ONE bullet: exactly one list item of the whole preamble opens with the lead, and the lead
    sentence occurs once in the file, so the rule has no second copy to drift from the first."""
    text = _read()
    openers = [
        lines
        for lines in _item_lines(text)[1]
        if _flat("\n".join(lines)[2:]).startswith(_LEAD)
    ]
    assert len(openers) == 1, f"{len(openers)} list items open with {_LEAD!r}"
    assert _flat(text).count(_LEAD) == 1, "the lead sentence occurs more than once"


# --- the checks can fail -----------------------------------------------------------------------


def test_the_old_section_4_lacks_the_claim() -> None:
    """Known positive: the section as it stood has no such bullet, and the finder says so; a
    sentence of it is in no part of the old section."""
    assert _bullet(_OLD_SECTION_4, _LEAD) == ""
    assert _gaps(_flat(_OLD_SECTION_4), _SENTENCES) == list(_SENTENCES)


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of the real section is the one gap reported, and an
    empty section lacks every sentence. A sentence that occurs twice would let a clause go and
    stay green."""
    flat = _flat(_section_4())
    assert _gaps(flat, _SENTENCES) == [], "a sentence is missing at the start"
    for sentence in _SENTENCES:
        assert flat.count(sentence) == 1, (
            f"{sentence!r} occurs {flat.count(sentence)} times"
        )
        assert _gaps(flat.replace(sentence, ""), _SENTENCES) == [sentence], sentence
    assert _gaps("", _SENTENCES) == list(_SENTENCES)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal, one per sentence after the lead: the words after the last comma
    or colon of the sentence are cut out of the real bullet, and the bullet then reports exactly
    that sentence. A check on a fragment of the sentence would stay green."""
    bullet = _bullet(_section_4(), _LEAD)
    assert bullet, f"no bullet of section 4 opens with {_LEAD!r}"
    assert not _gaps(bullet, _SENTENCES)
    for sentence in _SENTENCES[1:]:
        tail = re.split(r"[,:] ", sentence)[-1]
        assert tail != sentence, f"no clause to cut from {sentence!r}"
        assert bullet.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
        assert _gaps(bullet.replace(tail, ""), _SENTENCES) == [sentence], sentence


@pytest.mark.parametrize("width", [40, 72, 100])
def test_a_rewrapped_and_reemphasised_section_still_holds_the_claim(width: int) -> None:
    """Near-miss that must NOT be reported: the real section with its list items re-wrapped at
    `width` columns, so that the bold lead breaks over two lines, and bold marks around one
    more word is the same text. The word is one that no wrap can split."""
    real = _section_4()
    assert _gaps(_flat(real), _SENTENCES) == [], (
        "section 4 lacks a sentence at the start"
    )
    reshaped = _rewrap(real, width).replace("blocked", "**blocked**", 1)
    assert reshaped != real
    assert "**blocked**" in reshaped, "the planted emphasis changed nothing"
    bullet = _bullet(reshaped, _LEAD)
    assert bullet, "the re-wrapped bullet was not found"
    assert _gaps(bullet, _SENTENCES) == []


def test_the_claim_is_judged_inside_section_4_only() -> None:
    """Planted move: the bullet cut out of section 4 and put into the section before it is a
    section 4 that lacks the claim and exactly it. A search of the whole file would still find
    every sentence and pass, which is why the claim is read from section 4 alone."""
    head, items = _item_lines(_section_4())
    moved = [lines for lines in items if _flat("\n".join(lines)[2:]).startswith(_LEAD)]
    kept = [lines for lines in items if lines not in moved]
    assert len(moved) == 1, "the bullet to move is not in section 4"
    text = (
        f"{_SECTION_3} Elsewhere\n\n"
        + "\n".join(moved[0])
        + "\n\n"
        + "\n".join([*head, *(line for lines in kept for line in lines)])
        + "\n"
    )
    after = _section(text, _SECTION_4)
    assert after.strip(), "the planted text has no section 4"
    assert _bullet(after, _LEAD) == ""
    assert _gaps(_flat(after), _SENTENCES) == list(_SENTENCES)
    assert _gaps(_flat(text), _SENTENCES) == [], "a whole-file search would have passed"


_SECTIONS = "\n".join(
    [
        "#### 4. A look-alike that only contains the wanted prefix",
        "## 4. First",
        "first body",
        "### 4.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "## 5. nor is this one",
        "```",
        "## 5. Second",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, runs to the end of the text
    when none follows, and finds nothing for a heading that is not there, so an absent section is
    reported and not read as an empty pass."""
    first = _section(_SECTIONS, "## 4.")
    assert first.startswith("## 4. First"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert "second body" in _section(_SECTIONS, "## 5. Second")
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
