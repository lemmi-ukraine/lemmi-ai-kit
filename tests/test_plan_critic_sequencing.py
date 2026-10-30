"""`plan-critic` has a sequencing step, and the planner sends its plans through it.

`plan-critic` read one document: its cross-document checks stayed inside one spec
(`design.md` against `requirements.md`, a verification plan against both), and its framing
question said so. A plan that orders work across initiatives, branches or pull requests
fails in a different place: a step runs before a precondition that another document states
(a clean tree, a pin against the trunk, a file deleted only after its work ships). Reading
the plan against itself cannot see that, so the step reads the documents its steps depend on.

These tests assert that the step and its trigger are in `plan-critic`'s SKILL.md, that its
Step 1 and its framing question agree with it, and that `initiative-planner`'s "Before
presenting" names it. Each assertion reads one named place, and the helpers are functions
over a string, so `test_the_slicers_see_planted_text_and_fail_loudly` fires them at planted
text before their silence on the real files is trusted.
"""

import re
from collections.abc import Iterable
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_CRITIC = shipped_skill_dirs()["plan-critic"] / "SKILL.md"
_PLANNER = shipped_skill_dirs()["initiative-planner"] / "SKILL.md"
_SURFACE: tuple[Path, ...] = (_CRITIC, _PLANNER)

_HEADING = re.compile(r"^(#{1,6})\s+\S")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text with blockquote markers dropped and every run of whitespace as one space."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>+ ?", "", text)).strip()


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the code it holds, not a heading. A missing heading fails with the
    heading named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _list_item(text: str, lead: str, where: str) -> str:
    """A list item: its first line starts with `lead`, and it runs through the indented
    lines and blank lines that follow, to the next line that starts in column 0."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(lead):
            item = [line]
            for follow in lines[index + 1 :]:
                if follow.strip() and not follow.startswith((" ", "\t")):
                    break
                item.append(follow)
            return "\n".join(item)
    raise AssertionError(f"{where}: no list item starting {lead!r}")


def _assert_carries(where: str, folded: str, clauses: Iterable[str]) -> None:
    missing = [clause for clause in clauses if clause not in folded]
    assert not missing, f"{where} does not carry: {missing}"


def _sequencing_step() -> str:
    return _section(_text(_CRITIC), "### Step 2.7", "plan-critic SKILL.md")


# --- the step and its trigger ------------------------------------------------------------


def test_plan_critic_has_a_sequencing_step_between_the_citation_check_and_step_three() -> (
    None
):
    text = _text(_CRITIC)
    headings = [
        line for line in text.split("\n") if re.match(r"^### Step (2\.6|2\.7|3) ", line)
    ]
    assert len(headings) == 3, f"plan-critic SKILL.md: found step headings {headings}"
    assert headings[0].startswith("### Step 2.6")
    assert headings[1].startswith("### Step 2.7")
    assert "Sequencing" in headings[1], (
        f"Step 2.7 is not the sequencing check: {headings[1]}"
    )
    assert headings[2].startswith("### Step 3")


def test_the_sequencing_step_states_its_trigger_and_its_skip() -> None:
    _assert_carries(
        "plan-critic SKILL.md, Step 2.7 trigger",
        _fold(_sequencing_step()),
        (
            "orders work across initiatives, branches or pull requests",
            "Skip this step for a single-slice spec",
        ),
    )


def test_the_sequencing_step_reads_the_documents_its_steps_depend_on() -> None:
    _assert_carries(
        "plan-critic SKILL.md, Step 2.7 method",
        _fold(_sequencing_step()),
        (
            "the documents its steps depend on, not only the plan",
            "each initiative's plans and prompts",
            "the topology",
            "the project's rules",
            "List the preconditions they state",
            "a clean tree",
            "a pin or settle check against the trunk",
            "a file deleted only after its work ships",
            "a file with one editor",
            "a trigger that expires",
            "Test each step, in plan order, against them at the point where it runs",
        ),
    )


def test_the_sequencing_step_sets_the_two_severities() -> None:
    folded = _fold(_sequencing_step())
    _assert_carries(
        "plan-critic SKILL.md, Step 2.7 severities",
        folded,
        (
            "runs before its precondition can hold is Major",
            "loses work or breaks another initiative's gate is a Blocker",
        ),
    )


# --- the rest of the file agrees ---------------------------------------------------------


def test_step_one_points_at_the_sequencing_step() -> None:
    step_one = _section(_text(_CRITIC), "### Step 1", "plan-critic SKILL.md")
    _assert_carries(
        "plan-critic SKILL.md, Step 1",
        _fold(step_one),
        ("Read the document end to end", "Step 2.7"),
    )


def test_the_framing_question_no_longer_says_the_skill_reads_only_the_plan() -> None:
    step_three = _section(_text(_CRITIC), "### Step 3", "plan-critic SKILL.md")
    question = _fold(
        _list_item(
            step_three, "5. **Inherited framing**", "plan-critic SKILL.md Step 3"
        )
    )
    _assert_carries(
        "plan-critic SKILL.md, Step 3 question 5",
        question,
        ("cross-document checks (Steps 2.5 to 2.7)",),
    )
    assert "This skill reads the plan against itself" not in question, (
        "question 5 still says, without a qualifier, that the skill reads only the plan, "
        "which the sequencing step no longer allows"
    )


def test_the_planner_before_presenting_names_the_sequencing_step() -> None:
    section = _section(
        _text(_PLANNER), "## Before presenting", "initiative-planner SKILL.md"
    )
    item = _fold(
        _list_item(
            section, "1. Run **`plan-critic`**", "initiative-planner Before presenting"
        )
    )
    _assert_carries(
        "initiative-planner SKILL.md, 'Before presenting' item 1",
        item,
        ("Step 2.7", "sequencing"),
    )


# --- the instruments ---------------------------------------------------------------------


def test_the_scan_surface_is_two_distinct_files() -> None:
    assert len(_SURFACE) == 2
    assert len({path.resolve() for path in _SURFACE}) == 2
    for path in _SURFACE:
        assert path.is_file(), f"{path} is not a file"
        assert _text(path).strip(), f"{path} is empty"


def test_the_slicers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "### Step 1 — Orient",
            "Read it.",
            "```bash",
            "# a comment inside a fence is not a heading",
            "```",
            "after the fence",
            "",
            "### Step 2 — Dimensions",
            "1. **First** question",
            "   with an indented tail",
            "",
            "   and a second paragraph",
            "2. **Second** question",
        ]
    )
    one = _section(planted, "### Step 1", "planted")
    assert "after the fence" in one and "Dimensions" not in one
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### Step 9", "planted")

    item = _list_item(planted, "1. **First**", "planted")
    assert "second paragraph" in item and "Second" not in item
    with pytest.raises(AssertionError, match="no list item"):
        _list_item(planted, "7. **None**", "planted")

    assert _fold("> a\n> b\n\n  c") == "a b c"
    with pytest.raises(AssertionError, match="does not carry"):
        _assert_carries("planted", "alpha", ("alpha", "gamma"))
