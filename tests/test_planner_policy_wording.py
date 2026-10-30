"""The planner family's policy sentences say what the operator decided, and the scans can see.

Three rules are stated in `initiative-planner` and its two templates. Each is stated in
several places that different sessions wrote, and nothing pinned the places together:

* the post-task review fires at every completion event, and a hand-off written while it has
  not run says so in its `## Status`;
* the usage window is a gate by default, and a project that says it is not one gets a switch,
  with the effect on the concurrency derivation stated;
* a plan that bars workers from the `.ai/` ledgers names, in the session register's `Owns`,
  who writes each entry.

Every test reads ONE place and names it, so a sentence that drifts back fails in the place it
drifted from. A place keeps its own wording, written for its neighbouring text: these tests
pin the clauses a place must carry, not one sentence copied into five places.

The usage-window switch is stated in four places, and each must name where the switch is read
from and carry the caveat that a reading may not exist. A count per file
(`test_the_usage_window_switch_is_stated_only_in_the_pinned_places`) fails when a fifth place
appears without its own pin.

The helpers are functions over a string, so `test_the_slicers_see_planted_text_and_fail_loudly`
can fire them at planted text before their silence on the real files is trusted, and
`test_the_scan_surface_is_three_distinct_files` states the surface in numbers.
"""

import re
from collections.abc import Iterable
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_PLANNER = shipped_skill_dirs()["initiative-planner"]
_SKILL = _PLANNER / "SKILL.md"
_ROADMAP = _PLANNER / "references" / "roadmap-template.md"
_EXECUTION_PLAN = _PLANNER / "references" / "execution-plan-template.md"
_SURFACE: tuple[Path, ...] = (_SKILL, _ROADMAP, _EXECUTION_PLAN)

# The events at which the review fires. One list, so no place can name a shorter one.
_COMPLETION_EVENTS: tuple[str, ...] = (
    "a finished task of any size",
    "a precondition stop",
    "a gate report",
    "a hand-off",
)

# What a place that states the usage-window switch must carry, whatever its other words.
# Each clause is contiguous on purpose. The first ties the source of the switch to the
# condition it reads, so a place that names another source fails. The second ties the caveat
# ", if one exists," to the reading it qualifies, so a place that drops it fails. As loose
# clauses, either could be replaced or deleted in one place and no test would notice.
_SWITCH_CONDITION = "the usage window is not a gate"
_SWITCH_CLAUSES: tuple[str, ...] = (
    f"the project's AGENTS.md or its override documents say {_SWITCH_CONDITION}",
    "report the reading and its age, if one exists, "
    "and never defer, shrink or skip verification on a wave because of it",
)
# Where the switch is stated, by file. The count is asserted, so a place cannot be added
# without a pin: each place has its own test below, and this table ties the two together.
_SWITCH_STATEMENTS: tuple[tuple[Path, int], ...] = (
    (_SKILL, 2),  # Step 4 derivation 3, and the Step 8 usage-floor trigger
    (_ROADMAP, 1),  # §2 Constraints in force
    (_EXECUTION_PLAN, 1),  # §6 Re-plan triggers, the usage-floor row
)
_STALE_READING = "older than a few minutes is stale during a fan-out"
_OPT_OUT_DISPLAY = "not applied: project opt-out"
_MINIMUM_OF_OTHER_TWO = "minimum of the other two"
_USAGE_FLOOR_ROW = "| A wave would start below the usage floor"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_ANY_HEADING = re.compile(r"^#{1,6}\s")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


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


def _raw_block(text: str, start: str, where: str) -> str:
    """From the first line that starts with `start` to the next heading-looking line.

    Fences are ignored on purpose: a template's skeleton sits inside one fenced block.
    """
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(start):
            block = [line]
            for follow in lines[index + 1 :]:
                if _ANY_HEADING.match(follow):
                    break
                block.append(follow)
            return "\n".join(block)
    raise AssertionError(f"{where}: no line starting {start!r}")


def _list_item(text: str, start: str, where: str) -> str:
    """The one list item whose first line starts with `start`, wrapped lines included.

    It runs from that line to the next blank line or heading-looking line, so a template that
    wraps a long item at a different column is a change of layout and never of meaning.
    Fences are ignored on purpose, as in `_raw_block`. No line or several lines starting with
    `start` fail with the count named, so a renamed or duplicated item is a loud failure.
    """
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(start)]
    if len(starts) != 1:
        raise AssertionError(
            f"{where}: expected one line starting {start!r}, found {len(starts)}"
        )
    block = [lines[starts[0]]]
    for follow in lines[starts[0] + 1 :]:
        if not follow.strip() or _ANY_HEADING.match(follow):
            break
        block.append(follow)
    return "\n".join(block)


def _row(text: str, first_cell: str, where: str) -> str:
    """The one table line that starts with `first_cell`, folded."""
    rows = [line for line in text.split("\n") if line.startswith(first_cell)]
    if len(rows) != 1:
        raise AssertionError(
            f"{where}: expected one table row starting {first_cell!r}, found {len(rows)}"
        )
    return _fold(rows[0])


def _switch_statements(text: str) -> int:
    """How many times `text` states the usage-window condition, wrapped across lines or not."""
    return _fold(text).count(_SWITCH_CONDITION)


def _missing(folded: str, clauses: Iterable[str]) -> list[str]:
    return [clause for clause in clauses if clause not in folded]


def _assert_carries(where: str, folded: str, clauses: Iterable[str]) -> None:
    missing = _missing(folded, clauses)
    assert not missing, f"{where} does not carry: {missing}"


def _continuation_sentence(text: str, where: str) -> str:
    """The one sentence that says what a hand-off written before the review has not run says."""
    marker = "post-task-review not run"
    sentences = [s for s in _SENTENCE_BOUNDARY.split(_fold(text)) if marker in s]
    if len(sentences) != 1:
        raise AssertionError(
            f"{where}: expected one sentence naming {marker!r}, found {len(sentences)}"
        )
    return sentences[0]


def _derivation_three(skill_text: str) -> str:
    step = _section(skill_text, "## Step 4", "initiative-planner SKILL.md")
    lead = "**3. The usage window.**"
    start = step.find(lead)
    if start < 0:
        raise AssertionError(f"initiative-planner SKILL.md Step 4: no {lead!r}")
    return step[start:]


# --- the review fires at every completion event ------------------------------------------


def test_the_planner_ends_every_session_at_every_completion_event() -> None:
    where = "initiative-planner SKILL.md, 'Every session ends the same way'"
    section = _section(
        _text(_SKILL),
        "### Every session ends the same way",
        "initiative-planner SKILL.md",
    )
    _assert_carries(where, _fold(section), _COMPLETION_EVENTS)


def test_the_roadmap_delegation_contract_names_every_completion_event() -> None:
    where = "roadmap-template.md, '§5 Delegation contract'"
    section = _section(
        _text(_ROADMAP), "### §5 Delegation contract", "roadmap-template.md"
    )
    _assert_carries(where, _fold(section), _COMPLETION_EVENTS)


@pytest.mark.parametrize(
    ("path", "where"),
    [(_SKILL, "initiative-planner SKILL.md"), (_ROADMAP, "roadmap-template.md")],
    ids=["skill", "roadmap-template"],
)
def test_a_handoff_written_before_the_review_says_so_in_its_status(
    path: Path, where: str
) -> None:
    sentence = _continuation_sentence(_text(path), where)
    _assert_carries(
        f"{where}, continuation sentence",
        sentence,
        ("`## Status`", "`parallel-session-safety` §9", "`in-progress"),
    )


# --- the usage window is a gate unless the project says it is not ------------------------


def test_the_planner_usage_window_derivation_carries_the_project_switch() -> None:
    folded = _fold(_derivation_three(_text(_SKILL)))
    _assert_carries(
        "initiative-planner SKILL.md, Step 4 derivation 3",
        folded,
        (
            # the default stays: the preflight and the checkpoint
            "Preflight the usage guard",
            "do not start the wave",
            "checkpoint continuation notes",
            # the switch
            *_SWITCH_CLAUSES,
            _STALE_READING,
            _OPT_OUT_DISPLAY,
            f"the cap stays the {_MINIMUM_OF_OTHER_TWO}",
            "accepts the risk the gate protects against",
        ),
    )


def test_the_planner_cap_sentence_names_all_three_derivations() -> None:
    folded = _fold(_section(_text(_SKILL), "## Step 4", "initiative-planner SKILL.md"))
    sentences = [
        s for s in _SENTENCE_BOUNDARY.split(folded) if s.startswith("Write the cap")
    ]
    assert len(sentences) == 1, (
        "initiative-planner SKILL.md Step 4: expected one sentence starting 'Write the cap', "
        f"found {len(sentences)}"
    )
    _assert_carries(
        "initiative-planner SKILL.md, Step 4 closing sentence",
        sentences[0],
        (
            "Write the cap with all three derivations (1, 2 and 3) visible",
            "is ignored the first time it is inconvenient",
        ),
    )


def test_the_planner_usage_floor_trigger_carries_the_project_switch() -> None:
    step = _section(_text(_SKILL), "## Step 8", "initiative-planner SKILL.md")
    row = _row(step, _USAGE_FLOOR_ROW, "initiative-planner SKILL.md Step 8")
    _assert_carries(
        "initiative-planner SKILL.md, Step 8 usage-floor trigger",
        row,
        ("do not start the wave", *_SWITCH_CLAUSES),
    )


def test_the_execution_plan_usage_window_placeholder_shows_the_opt_out() -> None:
    item = _list_item(
        _text(_EXECUTION_PLAN), "3. {", "execution-plan-template.md, derivation list"
    )
    _assert_carries(
        "execution-plan-template.md, derivation-3 placeholder",
        _fold(item),
        (
            "the usage window",
            _OPT_OUT_DISPLAY,
            "when the project says it is not a gate",
            _MINIMUM_OF_OTHER_TWO,
        ),
    )


def test_the_execution_plan_usage_floor_row_carries_the_project_switch() -> None:
    row = _row(_text(_EXECUTION_PLAN), _USAGE_FLOOR_ROW, "execution-plan-template.md")
    _assert_carries(
        "execution-plan-template.md, usage-floor row",
        row,
        ("do not start the wave", *_SWITCH_CLAUSES, _STALE_READING, _OPT_OUT_DISPLAY),
    )


def test_the_roadmap_usage_window_constraint_carries_the_project_switch() -> None:
    section = _section(
        _text(_ROADMAP), "### §2 Constraints in force", "roadmap-template.md"
    )
    _assert_carries(
        "roadmap-template.md, '§2 Constraints in force'",
        _fold(section),
        (*_SWITCH_CLAUSES, "accepts the risk the gate protects against"),
    )


@pytest.mark.parametrize(
    ("path", "pinned"),
    _SWITCH_STATEMENTS,
    ids=["skill", "roadmap-template", "execution-plan-template"],
)
def test_the_usage_window_switch_is_stated_only_in_the_pinned_places(
    path: Path, pinned: int
) -> None:
    found = _switch_statements(_text(path))
    assert found == pinned, (
        f"{path.name} states {_SWITCH_CONDITION!r} {found} times and {pinned} places are "
        "pinned in this file: give the new place its own test, then update _SWITCH_STATEMENTS"
    )


# --- a plan that bars workers from the ledgers names the writer --------------------------


def test_the_session_register_owns_names_the_ledger_writer() -> None:
    block = _raw_block(
        _text(_EXECUTION_PLAN), "## 3. Session register", "execution-plan-template.md"
    )
    _assert_carries(
        "execution-plan-template.md, '3. Session register'",
        _fold(block),
        (
            "`Owns`",
            "bars workers from the ledgers",
            "`.ai/ai-changelog.md`",
            "`.ai/improvement-hypotheses.md`",
            "`.ai/learnings.md`",
            "names the writer of each",
            "the next consolidation",
        ),
    )


# --- the instruments ---------------------------------------------------------------------


def test_the_scan_surface_is_three_distinct_files() -> None:
    assert len(_SURFACE) == 3
    assert len({path.resolve() for path in _SURFACE}) == 3
    for path in _SURFACE:
        assert path.is_file(), f"{path} is not a file"
        assert _text(path).strip(), f"{path} is empty"


def test_the_usage_window_switch_surface_is_four_places_in_three_files() -> None:
    assert sum(count for _, count in _SWITCH_STATEMENTS) == 4
    assert [path for path, _ in _SWITCH_STATEMENTS] == list(_SURFACE)
    assert [count for _, count in _SWITCH_STATEMENTS] == [2, 1, 1]


def test_the_switch_count_sees_a_statement_that_wraps_across_lines() -> None:
    wrapped = "if it says the usage\nwindow is not a gate, report it; the usage window is not a gate."
    assert _switch_statements(wrapped) == 2
    assert _switch_statements("the usage window is a gate") == 0


def test_the_list_item_slicer_keeps_wrapped_lines_and_fails_loudly() -> None:
    planted = "\n".join(
        [
            "1. {first}",
            '3. {third, wrapped after "is not a gate;"',
            "   the continuation line}",
            "",
            "outside the item",
        ]
    )
    item = _list_item(planted, "3. {", "planted")
    assert "the continuation line}" in item and "outside the item" not in item
    assert (
        _fold(item)
        == '3. {third, wrapped after "is not a gate;" the continuation line}'
    )
    with pytest.raises(AssertionError, match="expected one line"):
        _list_item(planted, "4. {", "planted")
    with pytest.raises(AssertionError, match="expected one line"):
        _list_item(planted + "\n3. {again}", "3. {", "planted")


def test_the_slicers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "# Title",
            "",
            "## Alpha",
            "> quoted line one",
            "> continues here",
            "```bash",
            "# a comment inside a fence is not a heading",
            "```",
            "tail of alpha",
            "",
            "## Beta",
            "text of beta",
            "| row one | a |",
            "| row two | b |",
            "",
            "A first sentence. A second one about post-task-review not run, here.",
        ]
    )
    alpha = _section(planted, "## Alpha", "planted")
    assert "tail of alpha" in alpha and "text of beta" not in alpha
    assert _fold(alpha).startswith("## Alpha quoted line one continues here")
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "## Gamma", "planted")

    assert "text of beta" in _raw_block(planted, "## Beta", "planted")
    assert "text of beta" not in _raw_block(planted, "## Alpha", "planted")
    with pytest.raises(AssertionError, match="no line starting"):
        _raw_block(planted, "## Gamma", "planted")

    assert _row(planted, "| row one", "planted") == "| row one | a |"
    with pytest.raises(AssertionError, match="expected one table row"):
        _row(planted, "| row", "planted")

    assert _continuation_sentence(planted, "planted").startswith("A second one")
    with pytest.raises(AssertionError, match="expected one sentence"):
        _continuation_sentence("nothing relevant here.", "planted")
    assert _missing("alpha beta", ("alpha", "gamma")) == ["gamma"]
