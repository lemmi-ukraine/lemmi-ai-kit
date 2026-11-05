"""The dispatch gates say a report to the operator opens with the answer or with the operator's action.

Nothing in the pack said what a report to the operator opens with. Section 8 of
`orchestrate/references/dispatch-gates.md` now holds three bullets. A long deliverable carries the
two- or three-line answer to the question the operator literally asked before the evidence. A stop
at an action only the operator can take opens with that action and its owner. A bare "proceed"
after such a stop is unresolved: it names no action, so the gate is re-checked with the command
that reads it, one question with explicit options is asked while the gate is closed, and the word
is never consent to bypass the gate.

The same word at the approval stop of a presented spec is the approval that stop asked for, and
the spec pipeline of the core pack reads it that way. A rule about operator actions that did not
say so would contradict it, so the exception is a sentence of the section and is judged inside
section 8 only: a copy of it in another section does not count.

THE SURFACE, in numbers the tests assert: 5 claims and 15 phrases in one file, all inside section
8. A claim holds when every one of its phrases is in section 8 (lower-cased, bold marks dropped,
whitespace collapsed). Each phrase occurs once there and is fired at a planted removal. The title,
the opening paragraph and the section numbers of the same file are held by the test of section 7,
which reads the file apart from this section.
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

_EXCEPTION = (
    'a "proceed" that answers a presented spec at its approval stop is the approval that stop asked for',
    "this rule is about a stop at an action the operator has to take",
)

# (claim id, the phrases that must all be present in section 8; lower-cased, bold marks dropped,
# whitespace collapsed). The claims, in order: the evidence level; a long deliverable carries the
# short answer; a stop at an operator-only action opens with it; a bare "proceed" after such a stop
# is unresolved; the exception for a spec's approval stop.
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "evidence-level",
        (
            "evidence level: observed in one project's notes, not yet repeated",
            "defaults to adopt and re-measure, not calibrated rules",
        ),
    ),
    (
        "short-answer-first",
        (
            "a long deliverable carries the short answer",
            "the two- or three-line answer to the question the operator literally asked before the evidence",
            "nobody has to ask for the restatement",
            "the goal, the session count by type and the pull-request stack",
        ),
    ),
    (
        "operator-action-first",
        (
            "a stop at an action only the operator can take opens with that action and its owner",
            "a credential, a push, a release, a decision",
            "what stays blocked until then, before any state",
        ),
    ),
    (
        "bare-proceed-is-unresolved",
        (
            'a bare "proceed" after such a stop is unresolved',
            "re-check the gate with the command that reads it",
            "ask one question with explicit options",
            "never read the word as consent to bypass the gate",
        ),
    ),
    ("approval-stop-exception", _EXCEPTION),
)
_PHRASES = tuple(phrase for _, phrases in _ROWS for phrase in phrases)


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


def _section_8() -> str:
    section = _section(_read(), _SECTION_8)
    assert section.strip(), "section 8 is missing from dispatch-gates.md"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_ROWS), len(_PHRASES)) == (5, 15)
    assert len(set(_PHRASES)) == len(_PHRASES), "a phrase is listed twice"
    assert _GATES.is_file(), f"{_GATES} is not a file"
    assert _read().strip(), "dispatch-gates.md is empty"


def test_section_8_is_present() -> None:
    """Red before the change: the file stopped at section 6."""
    section = _section_8()
    assert section.startswith(
        "## 8. A report to the operator opens with the answer, or with the action only the operator can take"
    )


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[row[0] for row in _ROWS])
def test_section_8_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _gaps(_flat(_section_8()), phrases)
    assert not missing, f"section 8 does not state {claim!r}: missing {missing}"


# --- the checks can fail -----------------------------------------------------------------------


def test_every_phrase_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section is the one gap reported, and an
    empty section lacks every phrase. A phrase that occurs twice, or that overlaps another, would
    let a claim lose its wording and stay green."""
    flat = _flat(_section_8())
    assert _gaps(flat, _PHRASES) == [], "a phrase is missing at the start"
    for phrase in _PHRASES:
        assert flat.count(phrase) == 1, f"{phrase!r} occurs {flat.count(phrase)} times"
        assert _gaps(flat.replace(phrase, ""), _PHRASES) == [phrase], phrase
    assert _gaps("", _PHRASES) == list(_PHRASES)


def test_a_rewrapped_and_reemphasised_section_still_holds_every_claim() -> None:
    """Near-miss that must NOT be reported: the real section with a line break and an indent at
    every space and bold marks around one word is the same text."""
    real = _section_8()
    reshaped = real.replace(" ", "\n    ").replace("proceed", "**proceed**")
    assert reshaped != real
    assert _gaps(_flat(reshaped), _PHRASES) == []


def test_the_approval_stop_exception_is_judged_inside_section_8_only() -> None:
    """Planted move: the exception cut out of section 8 and put into a section before it is a
    section 8 that lacks it, and exactly it. A search of the whole file would still find the
    sentence and pass, which is why the claim is read from section 8 alone."""
    body = _flat("\n".join(_section_8().split("\n")[1:]))
    start = body.index(_EXCEPTION[0])
    end = body.index(_EXCEPTION[1]) + len(_EXCEPTION[1])
    moved = (
        f"## 7. Elsewhere\n\n{body[start:end]}.\n\n"
        f"{_SECTION_8} Report\n\n{body[:start]}{body[end:]}\n"
    )
    assert _gaps(_flat(_section(moved, _SECTION_8)), _PHRASES) == list(_EXCEPTION)
    assert _gaps(_flat(moved), _PHRASES) == [], "a whole-file search would have passed"


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
    assert _gaps(_flat(_section(_SECTIONS, "## 99.")), _PHRASES) == list(_PHRASES)
