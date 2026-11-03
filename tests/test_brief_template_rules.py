"""A dispatch brief carries six rules, each in a section of the template that is only theirs.

Each rule was added after a session stopped, or ran twice, without it: a paste line typed by hand
with a placeholder left in it, a delegate that stopped on two named spellings of a placeholder and
walked past a third, a second run that repeated a page because the first run's note did not exist
yet, an injected session default that outranked the project's own ruling, a precondition written
as prose, and a kickoff that said "any other reply is a no" without saying what "yes" permits.

THE SURFACE, in numbers the tests assert: 6 claims and 14 phrases in one reference,
`orchestrate/references/brief-template.md`, all inside one section, `## Rules a dispatch brief
carries`. The `## Paste line` section is pinned by its own test (`test_peer_brief_first_step.py`)
and is not this file's: no phrase here is judged against it. A claim holds when every one of its
phrases is in the section (lower-cased, whitespace collapsed), and each phrase is fired at a planted
removal, so a phrase the check could not see go is not in the table.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATE = _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate"
_TEMPLATE = _ORCHESTRATE / "references" / "brief-template.md"
_HEADING = "## Rules a dispatch brief carries"
_PASTE_LINE_HEADING = "## Paste line"

# (claim, the phrases that must all be in the section; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1: a paste line is printed by a command, never typed, and holds no substitution",
        (
            "a paste line is printed by a command, never typed",
            "carries no substitution",
        ),
    ),
    (
        "2: any placeholder is a stop, not only the spellings the brief names",
        (
            "stop on any `<...>` placeholder",
            "walks past the third",
            "nothing is written",
        ),
    ),
    (
        "3: the return note is the first write, made so that it fails if it exists",
        (
            "the return note is the first write",
            "fails if it exists",
            "another run holds this page",
        ),
    ),
    (
        "4: a project's standing decision beats a session default",
        (
            "a project's standing decision beats a session default",
            "does not authorize it",
        ),
    ),
    (
        "6: a precondition is a command with an expected result, and a surprise is a stop",
        (
            "preconditions are commands with expected results",
            "a surprise is a stop",
        ),
    ),
    (
        'h: a kickoff that says "any other reply is a no" says what a plain affirmative means',
        (
            "any other reply is a no",
            "says what a plain affirmative means",
        ),
    ),
)


def _template() -> str:
    """The template as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return _TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n")


def _section(text: str, heading: str) -> str:
    """The lines under `heading` up to the next level-2 heading; empty when it is absent."""
    lines = text.split("\n")
    if heading not in lines:
        return ""
    body: list[str] = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def _words(text: str) -> str:
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (6, 14)
    assert _TEMPLATE.is_file(), _TEMPLATE


def test_the_rules_have_a_section_of_their_own() -> None:
    """Once, outside the fenced skeleton, and not folded into the paste-line section."""
    text = _template()
    assert text.split("\n").count(_HEADING) == 1, f"{_HEADING!r} is not one heading"
    assert _words(_section(text, _HEADING)), "the section is empty"
    assert _HEADING not in _section(text, _PASTE_LINE_HEADING)


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[row[0] for row in _ROWS])
def test_the_section_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    section = _words(_section(_template(), _HEADING))
    missing = _missing(section, phrases)
    assert not missing, f"the section does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section in turn is the one gap reported,
    and an empty section lacks every phrase of a row. A phrase the check cannot see go would
    let the template lose its rule and stay green."""
    section = _words(_section(_template(), _HEADING))
    for claim, phrases in _ROWS:
        assert not _missing(section, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(section.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_skill_already_links_the_template() -> None:
    """A reference no SKILL.md links is not read; the link exists, so SKILL.md gains no line."""
    skill = (_ORCHESTRATE / "SKILL.md").read_text(encoding="utf-8")
    assert "references/brief-template.md" in skill


def test_the_links_in_the_section_resolve() -> None:
    """A rule that points at the create collision names a file that exists."""
    section = _section(_template(), _HEADING)
    targets = re.findall(r"\]\(([^)\s#]+)(?:#[^)\s]*)?\)", section)
    unresolved = [
        target
        for target in targets
        if not (_TEMPLATE.parent / target).resolve().is_file()
    ]
    assert not unresolved, f"links that do not resolve from the template: {unresolved}"
    assert targets, "the section links nothing; the create collision rule names 12k"


# --- the opening of the template: this file's second scan surface ---------------------------------
#
# The six rules above are judged in `## Rules a dispatch brief carries`, after the fence. The three
# lines below are judged INSIDE the template's first code fence, the brief an orchestrator copies:
# the blocker line that opens it, and the problem and value lines under its Goal heading. The two
# surfaces share no line (`test_the_two_surfaces_share_no_line`).
#
# THE SURFACE, in numbers the tests assert: 3 lines and 5 phrases in the one fence of the one
# reference. A line holds when it sits where it belongs (the blocker line is the first line of the
# fence, the other two are under the Goal heading, the problem line above the value line) and every
# one of its phrases is in it. Each line is fired at a planted removal, a planted misplacement and
# the template as it stood before, and a re-wrapped line must still pass.

_GOAL_HEADING = "## Goal (one concern)"
_CONTEXT_HEADING = "## Context (so you don't re-explore the repo)"
_STANDING_RULES = "## Standing rules"
_EM_DASH = chr(0x2014)
_BOLD_LABEL = re.compile(r"^\*\*[^*]+:\*\*")

# (name, the label that opens the line, the heading whose section holds it or "" for the first
# line of the fence, the phrases that must all be in it; lower-cased, bold marks dropped)
_OPENING: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "blocker",
        "operator-only blocker:",
        "",
        (
            "the one thing only the operator can clear",
            'the words "no operator-only blocker"',
        ),
    ),
    ("problem", "problem:", _GOAL_HEADING, ("what is wrong or missing today",)),
    (
        "value",
        "value:",
        _GOAL_HEADING,
        (
            "what is better, for whom, once this is done",
            'a volume target such as "n items processed" is not value',
        ),
    ),
)

# The template as it stood before the opening existed. The word value is in it, in the shell-hook
# rule, and is no value line.
_OLD_TEMPLATE = f"""# Delegation brief template

```markdown
{_STANDING_RULES} (read this FILE {_EM_DASH} only two harness limits are restated below)
Read `<absolute path to the installed agent-delegate skill's assets/worker-preamble.md>` in full before your first
shell call: evidence discipline, working-tree discipline, and how to return a result.
- Shell hook: a leading `NAME=value` assignment before a command can be denied. Put the value inline,
  write multi-step logic to a script file, or use the interpreter's UTF-8 mode flag instead of an
  environment variable.

{_GOAL_HEADING}
<single outcome this worker owns>

{_CONTEXT_HEADING}
- Files: <paths the work touches, with one-line roles> {_EM_DASH} a STARTING SET, not a boundary

## Definition of done (self-checkable)
- <command that must pass / observable behavior / artifact that must exist>
```
"""


def _plain(text: str) -> str:
    """Bold marks dropped, whitespace folded, capitals ignored: a re-wrapped or re-emphasised
    line is the same line."""
    return " ".join(text.replace("**", "").split()).lower()


def _fence(text: str) -> list[str]:
    """The lines between the first pair of code fences, the template an orchestrator copies.
    Empty when there is none or it is never closed, so a pin on it fails loudly."""
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


def _line_of(lines: list[str], label: str) -> int | None:
    """The index of the first line that opens with `label`; None when no line does."""
    return next(
        (index for index, line in enumerate(lines) if _plain(line).startswith(label)),
        None,
    )


def _end_of(lines: list[str], start: int) -> int:
    """One past the last line of the line that opens at `start`: its wrapped lines run up to a
    blank line, a heading or the next bold label."""
    end = start + 1
    while end < len(lines):
        follow = lines[end]
        if not follow.strip() or follow.startswith("#") or _BOLD_LABEL.match(follow):
            break
        end += 1
    return end


def _opening_gaps(text: str) -> list[str]:
    """What the opening lacks, one entry per gap, each starting with the name of its line."""
    fence = _fence(text)
    gaps: list[str] = []
    found: dict[str, int] = {}
    for name, label, under, phrases in _OPENING:
        region = _section("\n".join(fence), under).split("\n") if under else fence
        start = _line_of(region, label)
        if start is None or (not under and start != 0):
            where = f"under {under!r}" if under else "as the first line of the fence"
            gaps.append(f"{name}: no line opens with {label!r} {where}")
            continue
        found[name] = start
        line = _plain(" ".join(region[start : _end_of(region, start)]))
        gaps += [f"{name}: the line lacks {p!r}" for p in phrases if p not in line]
    if "problem" in found and "value" in found and found["value"] < found["problem"]:
        gaps.append("value: sits above the problem line")
    return gaps


def _pins_reported(text: str) -> list[str]:
    """The names of the lines `_opening_gaps` reports, in the order it reports them."""
    return [gap.split(":")[0] for gap in _opening_gaps(text)]


def _cut(text: str, label: str) -> tuple[list[str], list[str]]:
    """The lines of `text` without the line that opens with `label`, and the lines cut out."""
    lines = text.split("\n")
    start = _line_of(lines, label)
    assert start is not None, f"no line opens with {label!r}"
    end = _end_of(lines, start)
    return lines[:start] + lines[end:], lines[start:end]


def _rewrap(line: str, width: int) -> list[str]:
    """`line` broken at its spaces into rows of at most `width` characters (one long word may
    run over), the continuation rows indented by two spaces as the template's bullets are."""
    rows: list[str] = []
    current = ""
    for word in line.split():
        if current and len(current) + 1 + len(word) > width:
            rows.append(current)
            current = f"  {word}"
        else:
            current = f"{current} {word}" if current else word
    rows.append(current)
    return rows


def test_the_opening_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, _, _, line_phrases in _OPENING for phrase in line_phrases]
    assert (len(_OPENING), len(phrases)) == (3, 5)
    fence = _fence(_template())
    assert fence, "the template has no closed code fence"
    assert _GOAL_HEADING in fence, "the first fence is not the template"


def test_the_two_surfaces_share_no_line() -> None:
    """The six rules are judged after the fence and the opening inside it: a line in both would
    be judged by a rule that does not apply to it."""
    lines = _template().split("\n")
    fences = [n for n, line in enumerate(lines, 1) if line.lstrip().startswith("```")]
    rules = lines.index(_HEADING) + 1
    assert len(fences) >= 2, f"{len(fences)} fence lines, not a closed fence"
    assert fences[1] < rules, (
        f"the fence ends at line {fences[1]}, the rules at {rules}"
    )


@pytest.mark.parametrize("name", [row[0] for row in _OPENING])
def test_the_template_carries_the_opening_line(name: str) -> None:
    """Red before the change: the template opened with its standing rules, and the goal had
    no problem line and no value line under it."""
    gaps = [gap for gap in _opening_gaps(_template()) if gap.startswith(f"{name}:")]
    assert not gaps, f"the template's opening lacks its {name} line: {gaps}"


def test_the_old_template_fails_every_pin() -> None:
    """Known-positive: the template as it stood before. It says value, in the shell-hook rule
    (`NAME=value`), and that is no value line: each of the three pins reports it."""
    assert "NAME=value" in _OLD_TEMPLATE
    assert _pins_reported(_OLD_TEMPLATE) == [row[0] for row in _OPENING]


def test_every_opening_line_is_reported_when_it_goes() -> None:
    """Planted removal: each line cut out of the real template in turn is the one pin reported,
    and each phrase cut out of its line is the one gap reported. A pin that could not see its
    line go would let the template lose it and stay green."""
    text = _template()
    assert not _opening_gaps(text), (
        "the template does not carry its opening at the start"
    )
    lines = text.split("\n")
    for name, label, _, phrases in _OPENING:
        rest, _cut_lines = _cut(text, label)
        assert _pins_reported("\n".join(rest)) == [name], name
        start = _line_of(lines, label)
        assert start is not None, name
        end = _end_of(lines, start)
        item = " ".join(lines[start:end])
        for phrase in phrases:
            shorter = re.sub(re.escape(phrase), "", item, count=1, flags=re.IGNORECASE)
            assert shorter != item, f"{name}: {phrase!r} is not in the line as written"
            planted = "\n".join([*lines[:start], shorter, *lines[end:]])
            assert _opening_gaps(planted) == [f"{name}: the line lacks {phrase!r}"]


def test_a_line_in_the_wrong_place_is_reported() -> None:
    """Planted misplacement: each line is present, whole, in the wrong place, and is the one pin
    reported. The blocker line below the standing rules heading is not an opening line; the
    value line under Context is not under the goal; a value line above the problem line is out
    of order; and a goal heading that is gone leaves both lines under nothing."""
    text = _template()
    assert not _opening_gaps(text), (
        "the template does not carry its opening at the start"
    )

    rest, blocker = _cut(text, "operator-only blocker:")
    below = (
        next(i for i, line in enumerate(rest) if line.startswith(_STANDING_RULES)) + 1
    )
    planted = [*rest[:below], *blocker, *rest[below:]]
    assert _pins_reported("\n".join(planted)) == ["blocker"]

    rest, value = _cut(text, "value:")
    below = rest.index(_CONTEXT_HEADING) + 1
    planted = [*rest[:below], *value, *rest[below:]]
    assert _pins_reported("\n".join(planted)) == ["value"]

    above = _line_of(rest, "problem:")
    assert above is not None
    planted = [*rest[:above], *value, *rest[above:]]
    assert _opening_gaps("\n".join(planted)) == ["value: sits above the problem line"]

    renamed = text.replace(_GOAL_HEADING, "## Goal")
    assert renamed != text, "the planted rename changed nothing"
    assert _pins_reported(renamed) == ["problem", "value"]


def test_a_re_wrapped_opening_still_passes() -> None:
    """Near-miss: the three lines re-wrapped at 40 columns, so that a phrase runs over two rows,
    are still the same three lines. The wrap changes the text and hides a phrase from a raw read,
    and the pins read it whole."""
    text = _template()
    assert not _opening_gaps(text), (
        "the template does not carry its opening at the start"
    )
    lines = text.split("\n")
    for _, label, _, _ in _OPENING:
        start = _line_of(lines, label)
        assert start is not None, label
        end = _end_of(lines, start)
        lines[start:end] = _rewrap(" ".join(lines[start:end]), 40)
    wrapped = "\n".join(lines)
    assert wrapped != text, "the planted wrap changed nothing"
    assert any(
        phrase not in wrapped.lower()
        for _, _, _, phrases in _OPENING
        for phrase in phrases
    ), "the planted wrap hides no phrase from a raw read"
    assert _opening_gaps(wrapped) == []
