"""The usage-window preflight of `orchestrate` keeps its default and gains the project's switch.

The first bullet of "1b. Context and usage budget" told the orchestrator to check the usage
window before a fan-out and, past the warn threshold, not to start the wave. That is a sound
default, and a project that does not treat the window as a gate had no way to say so: the text
gave it nothing to point at, a reading that was minutes old read as current, and nothing said
what to report when the client exposes no reading at all (the kit ships no usage guard).

What the bullet says now: the default stays (past the warn threshold, do not start the wave,
checkpoint first); the age of the reading is noted, and a reading older than a few minutes is
stale during a fan-out, since every other live session draws on the same window; and if the
project's AGENTS.md or its override documents say the window is not a gate, the orchestrator
reports the reading and its age, if one exists, and never defers, shrinks or skips verification
on a wave because of it. The kit ships no usage guard, so no reading is ever presumed to exist,
and a project that opts out accepts the risk the gate protects against: waves killed at the
limit and duplicate dispatch after a re-run.

The default also tells the orchestrator what to checkpoint, and a cold read found that the old
wording ("continuation notes + workflow `resumeFromRunId` lines") contradicted the runtime-hazards
reference of `agent-delegate`: a resume id works only in the session that ran the workflow, so a
successor session handed those lines had nothing to resume. The bullet now writes a resume line
only for a resume in this session and a standalone stage script for a hand-off to another one,
and points at the reference. The skill is at its line cap, so the clause replaces words of the
two lines that carried the old one and adds no line.

That project still states its own cap on simultaneous agents and counts every live session on
the account toward it. The kit sets no number and no default cap, so the sentence names none.
The check is a tripwire for a default, not a proof that none is there: it reads digits and the
count words of `_NUMBER` in the one sentence that carries the cap, so a vague quantity ("a
handful") passes and the pronoun "one" is read as a count. `test_a_number_in_the_cap_sentence_is_a_failure`
fires it at planted defaults, and
`test_the_number_check_does_not_depend_on_how_the_bullet_is_laid_out` shows that how the file
wraps or spaces the bullet moves no verdict.

The check reads that one bullet, found by its section heading and its lead, whole: a re-wrapped
bullet keeps its continuation lines wherever the wrap breaks them, which
`test_a_re_wrapped_bullet_is_read_whole` shows by laying its words out at every chunk size. A
heading or a lead that goes missing fails with a message that names it, not with an empty pass.
`test_the_check_fails_on_the_bullet_it_replaced` fires it at the old bullet, and
`test_each_requirement_is_load_bearing` removes one requirement at a time from the real bullet
and expects exactly that requirement to be reported.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATE = "plugins/orchestration/skills/orchestrate/SKILL.md"
_HEADING = re.compile(r"^(#{1,6})\s")
# A line opens the next list item the way the skill opens its own: "- " or a number and a
# period. It never opens one with "+" or "*", so a line that a word of the bullet opens, as a
# re-wrap could do with the "+" of the old bullet's "notes + workflow", stays part of the bullet.
_MARKER = re.compile(r"\s*(?:-|\d+\.)\s")

_SECTION_HEADING = "### 1b. Context and usage budget"
_LEAD = "- **Preflight the usage window before every wave.**"

# The cap sentence is found by its first clause. It names no number: the project supplies one.
_CAP_MARKER = "still states its own cap on simultaneous agents"
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
# A number in the cap sentence is a default the kit would be setting, so the check reads digits
# and these count words. It is a tripwire, not a proof: a vague quantity ("a handful") passes,
# and the pronoun "one" is read as a count, which is the safe direction for a guard on a default.
_COUNT_WORDS = (
    "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    "fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    "eighty|ninety|hundred|thousand|dozen|couple|pair|single"
)
_NUMBER = re.compile(rf"\d+|\b(?:{_COUNT_WORDS})\b", re.IGNORECASE)
# The period of these ends no sentence, so a number after one stays in the sentence it sits in.
_ABBREVIATION = re.compile(r"\b(?:e\.g|i\.e|cf|vs)\.", re.IGNORECASE)

# The three clauses of the cap sentence, which must share ONE sentence of the bullet.
_CAP_REQUIRED: tuple[tuple[str, str], ...] = (
    (
        "an opted-out project still states its own cap on simultaneous agents",
        _CAP_MARKER,
    ),
    (
        "every live session on the account counts toward that cap",
        "counts every live session on the account toward it",
    ),
    (
        "the kit sets no number and no default cap",
        "the kit sets no number and no default cap",
    ),
)

# (label, the sentence or clause that must be in the folded bullet). The clauses do not overlap,
# so that removing one reports that one and no other.
_REQUIRED: tuple[tuple[str, str], ...] = (
    (
        "the default stays: past the warn threshold, do not start the wave",
        "Past the warn threshold: do not start the wave",
    ),
    ("the default stays: checkpoint first", "checkpoint first"),
    (
        "a resume line is for a resume in this session, a standalone script for a hand-off",
        "continuation notes; a workflow `resumeFromRunId` line only for a resume in this "
        "session, a standalone stage script for a hand-off to another session; see [runtime "
        "hazards](../agent-delegate/references/runtime-hazards.md)",
    ),
    ("the age of the reading is noted", "note how old the reading is"),
    (
        "a reading older than a few minutes is stale during a fan-out",
        "a reading older than a few minutes is stale during a fan-out",
    ),
    (
        "every other live session draws on the same window",
        "every other live session draws on the same window",
    ),
    (
        "the switch names where a project says the window is not a gate",
        "If the project's AGENTS.md or its override documents say the usage window is "
        "not a gate",
    ),
    (
        "the reading and its age are reported, if one exists",
        "report the reading and its age, if one exists",
    ),
    (
        "never defer, shrink or skip verification because of the window",
        "never defer, shrink or skip verification on a wave because of it",
    ),
    ("the kit ships no usage guard", "The kit ships no usage guard"),
    ("a reading is never presumed to exist", "never presume a reading exists"),
    (
        "a project that opts out accepts the risk the gate protects against",
        "a project that opts out accepts the risk the gate protects against",
    ),
    (
        "the risk is waves killed at the limit and duplicate dispatch after a re-run",
        "(waves killed at the limit, duplicate dispatch after a re-run)",
    ),
    *_CAP_REQUIRED,
)

_OLD_BULLET = """### 1b. Context and usage budget

The measured failure mode is inline-by-default.

- **Preflight the usage window before every wave.** Check the remaining usage window (whatever
  your client exposes — a statusline rate-limit feed, or the provider's console) before any
  fan-out of ≥3 workers. Past the warn threshold: do not start the
  wave — checkpoint first (continuation notes + workflow `resumeFromRunId` lines), then wait or hand
  off. A wave that dies at the wall costs re-dispatch AND duplicate-dispatch races: every resume
  message must state who else is on the item ("two workers ran this assignment" was found by the
  worker, not the orchestrator).
- **Epic implementation slices leave the session by default** — the plan-time rule.
"""


def _folded(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space, so a re-wrapped
    line is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


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


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _first_bullet(section: str) -> str:
    """The first list item of the section: its line and every line that belongs to it, up to
    the next heading or the next list marker (`_MARKER`) at the same or a shallower indent, and,
    after a blank line, up to the next line that is not indented. A continuation line stays in
    whether it is indented or sits in column 0, so a re-wrapped bullet is read whole. A list
    item opened with "+" or "*", which the skill does not use, would be read as part of it."""
    lines = section.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("- ")), -1)
    if start < 0:
        return ""
    bullet = [lines[start]]
    after_blank = False
    for follow in lines[start + 1 :]:
        if not follow.strip():
            bullet.append(follow)
            after_blank = True
            continue
        shallow = _indent(follow) <= _indent(lines[start])
        if _HEADING.match(follow) or (
            shallow and (_MARKER.match(follow) is not None or after_blank)
        ):
            break
        bullet.append(follow)
        after_blank = False
    return "\n".join(bullet)


def _missing(flat: str) -> list[str]:
    """The labels of the requirements the folded bullet does not satisfy."""
    return [label for label, clause in _REQUIRED if clause not in flat]


def _sentences(flat: str) -> list[str]:
    """The sentences of the folded bullet. The period of an abbreviation ends none, so a number
    after "e.g." stays in the sentence it sits in."""
    unabbreviated = _ABBREVIATION.sub(lambda m: m.group(0).rstrip("."), flat)
    return _SENTENCE_BOUNDARY.split(unabbreviated)


def _numbers_in_cap_sentence(flat: str) -> list[str]:
    """Every digit or count word in the folded sentence that carries the cap marker.
    A bullet with no such sentence yields none: the missing requirement reports that."""
    sentences = [s for s in _sentences(flat) if _CAP_MARKER in s]
    return [m.group(0) for sentence in sentences for m in _NUMBER.finditer(sentence)]


def _problems(text: str) -> list[str]:
    """What the preflight bullet of `text` lacks; an empty list is a pass."""
    section = _section(text, _SECTION_HEADING)
    if not section:
        return [f"no heading starts with {_SECTION_HEADING!r}"]
    bullet = _first_bullet(section)
    if not bullet.startswith(_LEAD):
        return [f"the first bullet of the section does not start with {_LEAD!r}"]
    flat = _folded(bullet)
    return [f"missing: {label}" for label in _missing(flat)] + [
        f"the cap sentence names a number: {number!r}"
        for number in _numbers_in_cap_sentence(flat)
    ]


def _orchestrate() -> str:
    """The skill as text with LF line ends, so a checkout that stores CRLF reads the same."""
    text = (_REPO_ROOT / _ORCHESTRATE).read_text(encoding="utf-8")
    return text.replace("\r\n", "\n")


def _on_one_line(bullet: str) -> str:
    """The bullet as one line: its lead as written, the rest folded. How the real bullet is
    wrapped or spaced is gone, and the cap sentence is in one piece."""
    flat = _folded(bullet)
    rest = flat.removeprefix(_folded(_LEAD))
    assert rest != flat, "the folded bullet does not open with the folded lead"
    return f"{_LEAD}{rest}"


def _planted(line: str, planted: str) -> str:
    """`line` with `planted` added to the end of its cap sentence."""
    tail = _CAP_REQUIRED[-1][1]
    assert tail in line, (
        "the planted default has nowhere to go: the cap sentence is absent"
    )
    return line.replace(tail, f"{tail} ({planted})", 1)


def _in_section(bullet: str) -> str:
    return f"{_SECTION_HEADING}\n\n{bullet}\n"


# The same words laid out three ways. A layout that moves no word must not turn a verdict.
_LAYOUTS: dict[str, Callable[[str], str]] = {
    "one line": lambda line: line,
    "every gap doubled": lambda line: (
        _LEAD + line.removeprefix(_LEAD).replace(" ", "  ")
    ),
    "wrapped at 60 columns": lambda line: textwrap.fill(
        line,
        width=60,
        subsequent_indent="  ",
        break_long_words=False,
        break_on_hyphens=False,
    ),
}


def test_the_preflight_keeps_its_default_and_gains_the_project_switch() -> None:
    """Red before the change: the bullet had the default and none of the switch."""
    text = _orchestrate()
    problems = _problems(text)
    assert not problems, f"{_ORCHESTRATE}: {problems}"


def test_the_check_fails_on_the_bullet_it_replaced() -> None:
    """The old bullet carries the default and nothing else, so the check must report every
    requirement but the two that say the default stays."""
    problems = _problems(_OLD_BULLET)
    expected = {label for label, _ in _REQUIRED[2:]}
    assert {p.removeprefix("missing: ") for p in problems} == expected, problems
    for label, clause in _REQUIRED[:2]:
        assert clause in _folded(_OLD_BULLET), f"the old bullet lacks {label!r}"


def test_each_requirement_is_load_bearing() -> None:
    """Removing one clause from the real bullet reports that clause and no other."""
    text = _orchestrate()
    flat = _folded(_first_bullet(_section(text, _SECTION_HEADING)))
    assert flat, "the preflight bullet was not found"
    assert _missing(flat) == [], "the real bullet must satisfy every requirement first"
    for label, clause in _REQUIRED:
        assert _missing(flat.replace(clause, "")) == [label], label


def test_a_re_wrapped_bullet_is_read_whole() -> None:
    """The real bullet's words after its lead are laid out again with every continuation in
    column 0, in chunks of every size from one word to all of them, and every requirement is
    still found in each layout: the reader does not stop at the first line that is not
    indented, nor at a line that a word of the bullet opens, such as the "+" of the old
    bullet's "notes + workflow", and it stops at the next list item. The layouts are built from the bullet's
    words, not its lines, so how the file wraps the bullet decides nothing, and the lead alone
    satisfies none of the requirements."""
    section = _section(_orchestrate(), _SECTION_HEADING)
    flat = " ".join(_first_bullet(section).split())
    assert flat.startswith(_LEAD), f"the first bullet does not open with {_LEAD!r}"
    words = flat.removeprefix(_LEAD).split()
    assert _missing(_folded(_LEAD)) == [label for label, _ in _REQUIRED], (
        "the planted wrap hides nothing: the lead already carries a requirement"
    )
    for size in range(1, len(words) + 1):
        wrapped = "\n".join(
            " ".join(words[i : i + size]) for i in range(0, len(words), size)
        )
        text = (
            f"{_SECTION_HEADING}\n\n{_LEAD}\n{wrapped}\n"
            "- **Epic slices leave the session.**\n"
        )
        read = _first_bullet(_section(text, _SECTION_HEADING))
        assert read == f"{_LEAD}\n{wrapped}", (
            f"the words laid out {size} to a line: the bullet is cut short or runs into "
            "the next item"
        )
        assert _problems(text) == [], f"the words laid out {size} to a line"


def test_a_missing_heading_or_lead_is_a_failure_with_a_name() -> None:
    """A section or a lead that goes missing must not read as a pass."""
    no_heading = (
        "## Protocol\n\n- **Preflight the usage window before every wave.** Check.\n"
    )
    assert _problems(no_heading) == [f"no heading starts with {_SECTION_HEADING!r}"]
    other_lead = (
        f"{_SECTION_HEADING}\n\n- **Epic slices leave the session.** Plan-time.\n"
    )
    assert _problems(other_lead) == [
        f"the first bullet of the section does not start with {_LEAD!r}"
    ]


def test_the_cap_clauses_share_one_sentence_and_it_names_no_number() -> None:
    """The three cap clauses are one sentence of the real bullet, and that sentence sets no
    number. Exactly one sentence must carry the marker, or the number check reads nothing."""
    flat = _folded(_first_bullet(_section(_orchestrate(), _SECTION_HEADING)))
    sentences = [s for s in _sentences(flat) if _CAP_MARKER in s]
    assert len(sentences) == 1, (
        f"expected one sentence carrying {_CAP_MARKER!r}, found {len(sentences)}"
    )
    for label, clause in _CAP_REQUIRED:
        assert clause in sentences[0], f"the cap sentence lacks: {label}"
    assert _numbers_in_cap_sentence(flat) == []


def test_a_number_in_the_cap_sentence_is_a_failure() -> None:
    """Fired at planted text: a default cap given in words, as a digit, past twelve, as a dozen
    and after an abbreviation is each reported by `_problems` and by nothing else, so the number
    check is not silent. The default is planted into the folded real bullet, so how the file wraps
    or spaces it cannot decide whether the plant lands."""
    line = _on_one_line(_first_bullet(_section(_orchestrate(), _SECTION_HEADING)))
    assert _problems(_in_section(line)) == []
    for planted, found in (
        ("a default cap of two agents", "two"),
        ("6 is typical", "6"),
        ("cap twenty", "twenty"),
        ("a dozen agents", "dozen"),
        ("e.g. 20 agents", "20"),
    ):
        problems = _problems(_in_section(_planted(line, planted)))
        assert problems == [f"the cap sentence names a number: {found!r}"], planted


def test_the_number_check_does_not_depend_on_how_the_bullet_is_laid_out() -> None:
    """The real bullet's words, laid out three ways: a clean bullet passes in each and a planted
    default is reported in each. A layout change that moves no word is not a defect, so it must
    not turn a verdict either way."""
    line = _on_one_line(_first_bullet(_section(_orchestrate(), _SECTION_HEADING)))
    for layout, lay_out in _LAYOUTS.items():
        laid_out = lay_out(line)
        assert layout == "one line" or laid_out != line, (
            f"{layout}: the layout changed nothing"
        )
        assert _problems(_in_section(laid_out)) == [], layout
        problems = _problems(_in_section(lay_out(_planted(line, "cap twenty"))))
        assert problems == ["the cap sentence names a number: 'twenty'"], layout
