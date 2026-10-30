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

The check reads that one bullet, found by its section heading and its lead, whole: a re-wrapped
bullet keeps its continuation lines. A heading or a lead that goes missing fails with a message
that names it, not with an empty pass. `test_the_check_fails_on_the_bullet_it_replaced` fires it
at the old bullet, and `test_each_requirement_is_load_bearing` removes one requirement at a time
from the real bullet and expects exactly that requirement to be reported.
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATE = "plugins/orchestration/skills/orchestrate/SKILL.md"
_HEADING = re.compile(r"^(#{1,6})\s")
_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")

_SECTION_HEADING = "### 1b. Context and usage budget"
_LEAD = "- **Preflight the usage window before every wave.**"

# (label, the sentence or clause that must be in the folded bullet). The clauses do not overlap,
# so that removing one reports that one and no other.
_REQUIRED: tuple[tuple[str, str], ...] = (
    (
        "the default stays: past the warn threshold, do not start the wave",
        "Past the warn threshold: do not start the wave",
    ),
    ("the default stays: checkpoint first", "checkpoint first"),
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
    the next heading or the next list marker at the same or a shallower indent, and, after a
    blank line, up to the next line that is not indented. A continuation line stays in whether
    it is indented or sits in column 0, so a re-wrapped bullet is read whole."""
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


def _problems(text: str) -> list[str]:
    """What the preflight bullet of `text` lacks; an empty list is a pass."""
    section = _section(text, _SECTION_HEADING)
    if not section:
        return [f"no heading starts with {_SECTION_HEADING!r}"]
    bullet = _first_bullet(section)
    if not bullet.startswith(_LEAD):
        return [f"the first bullet of the section does not start with {_LEAD!r}"]
    return [f"missing: {label}" for label in _missing(_folded(bullet))]


def _orchestrate() -> str:
    """The skill as text with LF line ends, so a checkout that stores CRLF reads the same."""
    text = (_REPO_ROOT / _ORCHESTRATE).read_text(encoding="utf-8")
    return text.replace("\r\n", "\n")


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
    """The real bullet is re-wrapped so that every continuation sits in column 0, and every
    requirement is still found: the reader does not stop at the first line that is not
    indented. Its first line alone satisfies none of the later requirements."""
    section = _section(_orchestrate(), _SECTION_HEADING)
    first, *rest = _first_bullet(section).split("\n")
    words = " ".join(part.strip() for part in rest).split(" ")
    wrapped = "\n".join(" ".join(words[i : i + 7]) for i in range(0, len(words), 7))
    text = f"{_SECTION_HEADING}\n\n{first}\n{wrapped}\n- **Epic slices leave the session.**\n"
    assert _problems(text) == []
    assert len(_missing(_folded(first))) > len(_REQUIRED) // 2, (
        "the planted wrap hides nothing: the first line already carries the requirements"
    )


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
