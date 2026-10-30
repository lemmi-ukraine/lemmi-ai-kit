"""`stacked-pr-planner`'s re-plan sweep covers the plan and its ancestry triggers.

Step 6 swept pending dispatch briefs and nothing else. After a revision that adds or
withdraws a dependency, the plan's own text kept two things that name the changed pair: a
trigger command that still ran an ancestry check on two branches that had become siblings,
and a schedule reason that still argued the withdrawn order. A search for the old wording
misses a command that names the pair, so the sweep has to name its targets.

These tests slice Step 6 by its heading (a missing heading fails loudly), assert that it
names trigger commands and rationale as sweep targets and holds one sentence that ties the
ancestry check to siblings, and assert that the execution-plan template's re-plan section
names the sweep. Each assertion fails on the text it replaced. The helpers are functions
over a string, so `test_the_slicers_see_planted_text_and_fail_loudly` fires them at planted
text before their silence on the real files is trusted.
"""

import re
from collections.abc import Iterable
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_PLANNER = shipped_skill_dirs()["stacked-pr-planner"] / "SKILL.md"
_TEMPLATE = (
    shipped_skill_dirs()["initiative-planner"]
    / "references"
    / "execution-plan-template.md"
)
_SURFACE: tuple[Path, ...] = (_PLANNER, _TEMPLATE)

_HEADING = re.compile(r"^(#{1,6})\s+\S")
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


def _sentences(folded: str) -> list[str]:
    return _SENTENCE_BOUNDARY.split(folded)


def _sentence_with(folded: str, anchor: str, where: str) -> str:
    """The one folded sentence that contains `anchor`."""
    hits = [s for s in _sentences(folded) if anchor in s]
    if len(hits) != 1:
        raise AssertionError(
            f"{where}: expected one sentence with {anchor!r}, found {len(hits)}"
        )
    return hits[0]


def _assert_carries(where: str, folded: str, clauses: Iterable[str]) -> None:
    missing = [clause for clause in clauses if clause not in folded]
    assert not missing, f"{where} does not carry: {missing}"


def _step_six() -> str:
    return _section(_text(_PLANNER), "## Step 6", "stacked-pr-planner SKILL.md")


# --- the sweep covers the plan -----------------------------------------------------------


def test_step_six_sweeps_the_plan_as_well_as_the_briefs() -> None:
    folded = _fold(_step_six())
    assert "PENDING DISPATCH BRIEFS" in folded, (
        "Step 6 lost the brief rule the sweep follows"
    )
    assert "The sweep covers the plan too" in folded, (
        "stacked-pr-planner SKILL.md, Step 6 has no rule that the sweep covers the plan"
    )
    assert folded.index("PENDING DISPATCH BRIEFS") < folded.index(
        "The sweep covers the plan too"
    )


def test_step_six_names_trigger_commands_and_rationale_as_sweep_targets() -> None:
    sentence = _sentence_with(
        _fold(_step_six()),
        "search every plan document",
        "stacked-pr-planner SKILL.md, Step 6 sweep",
    )
    _assert_carries(
        "stacked-pr-planner SKILL.md, Step 6 sweep sentence",
        sentence,
        (
            "adds or withdraws a dependency",
            "tracked or not",
            "every name of each changed pair",
            "(branch, row label, session label, item id)",
            "trigger commands",
            "`Depends on (why)` cells",
            "order rationale",
        ),
    )
    _assert_carries(
        "stacked-pr-planner SKILL.md, Step 6 sweep",
        _fold(_step_six()),
        ("A search for the old wording misses a command that names the pair",),
    )


# --- siblings are never ordered by ancestry ----------------------------------------------


def test_step_six_never_orders_siblings_by_ancestry() -> None:
    folded = _fold(_step_six())
    tying = [
        s
        for s in _sentences(folded)
        if "--is-ancestor" in s and re.search(r"\bsiblings\b", s, re.IGNORECASE)
    ]
    assert tying, (
        "stacked-pr-planner SKILL.md, Step 6 has no sentence that ties --is-ancestor to siblings"
    )
    _assert_carries(
        "stacked-pr-planner SKILL.md, Step 6 sibling rule",
        folded,
        (
            "Never order siblings by ancestry",
            "not ancestors of each other until a rebase or merge brings one into the other",
            "holds the later merge",
            "When a dependency is withdrawn, delete that check",
            "git merge-tree --write-tree <trunk> <branch>",
            "git 2.38 or later",
            "the gate on an export of the tree it prints",
            "the earlier one's work is in trunk (Step 7)",
        ),
    )


# --- the template points at the sweep ----------------------------------------------------


def test_the_execution_plan_template_replan_section_names_the_sweep() -> None:
    section = _section(
        _text(_TEMPLATE), "### §6 Re-plan triggers", "execution-plan-template.md"
    )
    _assert_carries(
        "execution-plan-template.md, '§6 Re-plan triggers'",
        _fold(section),
        (
            "added or withdrawn",
            "`stacked-pr-planner` Step 6's sweep covers these triggers and §4's reasons",
        ),
    )


# --- the instruments ---------------------------------------------------------------------


def test_the_scan_surface_is_two_distinct_files_and_step_six_holds_the_trigger_table() -> (
    None
):
    assert len(_SURFACE) == 2
    assert len({path.resolve() for path in _SURFACE}) == 2
    for path in _SURFACE:
        assert path.is_file(), f"{path} is not a file"
    step = _step_six()
    assert "## Step 7" not in step, "the Step 6 slice runs past its own end"
    table_lines = [line for line in step.split("\n") if line.startswith("|")]
    assert len(table_lines) >= 8, (
        f"the Step 6 slice holds {len(table_lines)} table lines; the trigger table has a "
        "header, a separator and at least six rows, so the slice is cutting it short"
    )


def test_the_slicers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "## Step 6 — Triggers",
            "> **Sweep.** One rule here, wrapped",
            "> over two lines.",
            "```bash",
            "# a comment inside a fence is not a heading",
            "```",
            "Siblings are not ancestors, so `--is-ancestor` fails. Another sentence.",
            "",
            "## Step 7 — Next",
            "after the section",
        ]
    )
    six = _section(planted, "## Step 6", "planted")
    assert "Siblings are not ancestors" in six and "after the section" not in six
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "## Step 9", "planted")

    folded = _fold(six)
    assert "One rule here, wrapped over two lines." in folded
    assert _sentence_with(folded, "--is-ancestor", "planted").endswith(
        "Siblings are not ancestors, so `--is-ancestor` fails."
    )
    with pytest.raises(AssertionError, match="expected one sentence"):
        _sentence_with(folded, "absent anchor", "planted")
    with pytest.raises(AssertionError, match="does not carry"):
        _assert_carries("planted", folded, ("Sweep", "no such clause"))
