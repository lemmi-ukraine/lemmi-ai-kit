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

An opted-out project still states its own cap on simultaneous agents and counts every live
session on the account toward it; the kit sets no number and no default cap. That sentence is
in the two templates only. `_CAP_STATEMENTS` pins how often each of the three scanned files says
it (0 in the planner SKILL.md, once in each template), as `_SWITCH_STATEMENTS` does for the
switch, and each template has its own test from one table, `_CAP_PLACES`, which the surface test
counts. The cap clauses (`_OPT_OUT_CAP_CLAUSES`) are never part of `_SWITCH_CLAUSES`, which the
planner SKILL.md must carry too. The no-number check is a tripwire for a default, not a proof
that none is there: it reads digits and the count words of `_NUMBER` in the one sentence or
placeholder that carries the cap, so a vague quantity ("a handful") passes and the pronoun "one"
is read as a count. Derivation 3's placeholder in the execution-plan template names where the
opt-out is read, as the other places do; its old condition is replaced, not extended, and a
planted fixture that still holds the old condition is flagged
(`test_the_placeholder_check_flags_the_old_condition_and_passes_the_new`). The cap checks are
fired at planted text in `test_the_cap_checks_see_planted_text_and_fail_loudly`, and
`test_the_cap_surface_is_two_templates_of_the_three_scanned_files` states their surface in
numbers.

The helpers are functions over a string, so `test_the_slicers_see_planted_text_and_fail_loudly`
can fire them at planted text before their silence on the real files is trusted, and
`test_the_scan_surface_is_three_distinct_files` states the surface in numbers.
"""

import re
from collections.abc import Callable, Iterable
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
# The clause that bars a size threshold from every brief. No test pinned it: deleting it left the
# whole suite green, so it is asserted whole, beside the events it qualifies.
_NO_SIZE_THRESHOLD = (
    "Every brief states this explicitly, naming the events and never a size threshold."
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

# Derivation 3's placeholder names where the opt-out is read, as the other places do. It keeps
# the pronoun ("say it is not a gate"): repeating _SWITCH_CONDITION whole would raise the count
# pinned in _SWITCH_STATEMENTS. The condition it replaced named no place, so the old text is
# checked absent, not merely the new text present.
_PLACEHOLDER_CONDITION = (
    "when the project's AGENTS.md or its override documents say it is not a gate"
)
_PLACEHOLDER_OLD_CONDITION = "when the project says it is not a gate"
_PLACEHOLDER_CLAUSES: tuple[str, ...] = (
    "the usage window",
    _OPT_OUT_DISPLAY,
    _PLACEHOLDER_CONDITION,
    _MINIMUM_OF_OTHER_TWO,
)

# What the two templates (and no other place) say an opted-out project still does. The three
# clauses are contiguous and share one sentence or one placeholder. They are NOT part of
# _SWITCH_CLAUSES: the planner SKILL.md carries the switch and must carry every switch clause,
# and says none of these (_CAP_STATEMENTS pins that at 0).
_OPT_OUT_CAP_CLAUSES: tuple[str, ...] = (
    "still states its own cap on simultaneous agents",
    "counts every live session on the account toward it",
    "the kit sets no number and no default cap",
)
_CAP_MARKER = _OPT_OUT_CAP_CLAUSES[0]
# Where the cap is stated, by file, as _SWITCH_STATEMENTS does for the switch: each clause of the
# sentence appears this many times in the file. The planner SKILL.md is scanned and pinned at 0,
# so a cap sentence added there needs its own test and its own row before this passes.
_CAP_STATEMENTS: tuple[tuple[Path, int], ...] = (
    (_SKILL, 0),
    (_ROADMAP, 1),  # §2 Constraints in force
    (_EXECUTION_PLAN, 1),  # §1 Headline numbers, under derivation 3
)
# The kit names no number: the project supplies its own cap. A number in the cap sentence is a
# default the kit would be setting, so the check reads digits and these count words. It is a
# tripwire, not a proof: a vague quantity ("a handful") passes, and the pronoun "one" is read
# as a count, which is the safe direction for a guard on a default.
_COUNT_WORDS = (
    "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    "fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    "eighty|ninety|hundred|thousand|dozen|couple|pair|single"
)
_NUMBER = re.compile(rf"\d+|\b(?:{_COUNT_WORDS})\b", re.IGNORECASE)
# The period of these ends no sentence, so a number after one stays in the sentence it sits in.
_ABBREVIATION = re.compile(r"\b(?:e\.g|i\.e|cf|vs)\.", re.IGNORECASE)

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_ANY_HEADING = re.compile(r"^#{1,6}\s")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")


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


def _placeholder_problems(item: str) -> list[str]:
    """What derivation 3's placeholder lacks, and the old condition if it still carries it."""
    folded = _fold(item)
    problems = [
        f"does not carry: {clause!r}"
        for clause in _missing(folded, _PLACEHOLDER_CLAUSES)
    ]
    if _PLACEHOLDER_OLD_CONDITION in folded:
        problems.append(
            f"still carries {_PLACEHOLDER_OLD_CONDITION!r}, which names no place"
        )
    return problems


def _only_unit(units: Iterable[str], where: str, kind: str) -> str:
    """The one unit that carries the cap marker; none or several fail with the count named."""
    found = [unit for unit in units if _CAP_MARKER in unit]
    if len(found) != 1:
        raise AssertionError(
            f"{where}: expected one {kind} naming {_CAP_MARKER!r}, found {len(found)}"
        )
    return found[0]


def _cap_sentences(text: str) -> list[str]:
    """The sentences of `text`, folded, with its headings dropped: a digit in a heading is not
    part of the sentence below it. The period of an abbreviation ends no sentence."""
    prose = "\n".join(line for line in text.split("\n") if not _ANY_HEADING.match(line))
    unabbreviated = _ABBREVIATION.sub(lambda m: m.group(0).rstrip("."), _fold(prose))
    return _SENTENCE_BOUNDARY.split(unabbreviated)


def _cap_sentence(text: str, where: str) -> str:
    """The one sentence of `text` that says an opted-out project states its own cap."""
    return _only_unit(_cap_sentences(text), where, "sentence")


def _cap_placeholder(text: str, where: str) -> str:
    """The one `{...}` placeholder of `text` that says an opted-out project states its cap."""
    return _only_unit(_PLACEHOLDER.findall(_fold(text)), where, "placeholder")


def _cap_problems(unit: str) -> list[str]:
    """The cap clauses a sentence or placeholder lacks, and every number it names."""
    return [
        f"does not carry: {clause!r}" for clause in _missing(unit, _OPT_OUT_CAP_CLAUSES)
    ] + [f"names a number: {match.group(0)!r}" for match in _NUMBER.finditer(unit)]


def _overlapping(first: Iterable[str], second: Iterable[str]) -> list[tuple[str, str]]:
    """The pairs, one from each list, where one clause contains the other."""
    seconds = tuple(second)
    return [(a, b) for a in first for b in seconds if a in b or b in a]


def _roadmap_cap_unit(text: str) -> str:
    where = "roadmap-template.md, '§2 Constraints in force'"
    section = _section(text, "### §2 Constraints in force", "roadmap-template.md")
    return _cap_sentence(section, where)


def _execution_plan_cap_unit(text: str) -> str:
    where = "execution-plan-template.md, '1. Headline numbers' skeleton"
    block = _raw_block(text, "## 1. Headline numbers", "execution-plan-template.md")
    return _cap_placeholder(block, where)


# The templates that carry the cap sentence, each with the reader that finds its one sentence or
# placeholder. The cap tests read this table and nothing else, so a template cannot be tested
# without a row here or have a row without a test, and the surface test counts the rows.
_CAP_PLACES: tuple[tuple[Path, Callable[[str], str]], ...] = (
    (_ROADMAP, _roadmap_cap_unit),
    (_EXECUTION_PLAN, _execution_plan_cap_unit),
)
_CAP_SURFACE: tuple[Path, ...] = tuple(path for path, _ in _CAP_PLACES)


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
    _assert_carries(where, _fold(section), (*_COMPLETION_EVENTS, _NO_SIZE_THRESHOLD))


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
    problems = _placeholder_problems(item)
    assert not problems, (
        f"execution-plan-template.md, derivation-3 placeholder: {problems}"
    )


def test_the_placeholder_check_flags_the_old_condition_and_passes_the_new() -> None:
    """Fired at planted placeholders: the one that holds the old condition is flagged twice,
    for the new condition it lacks and for the old one it keeps, and the one that holds the new
    condition passes. The new condition does not contain the old one, so neither can hide in
    the other."""
    old = (
        '3. {the usage window - or "not applied: project opt-out" '
        "when the project says it is not a gate; "
        "the cap is then the minimum of the other two}"
    )
    new = old.replace(_PLACEHOLDER_OLD_CONDITION, _PLACEHOLDER_CONDITION, 1)
    assert new != old, "the planted replacement changed nothing"
    assert _PLACEHOLDER_OLD_CONDITION not in _PLACEHOLDER_CONDITION
    assert _placeholder_problems(new) == []
    assert _placeholder_problems(old) == [
        f"does not carry: {_PLACEHOLDER_CONDITION!r}",
        f"still carries {_PLACEHOLDER_OLD_CONDITION!r}, which names no place",
    ]


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


# --- an opted-out project still states its own cap on simultaneous agents -----------------


@pytest.mark.parametrize(
    ("path", "unit_of"),
    _CAP_PLACES,
    ids=["roadmap-template", "execution-plan-template"],
)
def test_a_template_tells_an_opted_out_project_to_state_its_own_cap(
    path: Path, unit_of: Callable[[str], str]
) -> None:
    problems = _cap_problems(unit_of(_text(path)))
    assert not problems, f"{path.name}, opt-out cap: {problems}"


@pytest.mark.parametrize(
    ("path", "pinned"),
    _CAP_STATEMENTS,
    ids=["skill", "roadmap-template", "execution-plan-template"],
)
def test_the_cap_sentence_is_stated_only_in_the_pinned_places(
    path: Path, pinned: int
) -> None:
    folded = _fold(_text(path))
    found = {clause: folded.count(clause) for clause in _OPT_OUT_CAP_CLAUSES}
    assert found == dict.fromkeys(_OPT_OUT_CAP_CLAUSES, pinned), (
        f"{path.name} carries the cap clauses {found} times and {pinned} of each are pinned "
        "in this file: give the new place its own row in _CAP_PLACES and its own count in "
        "_CAP_STATEMENTS"
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


def test_the_size_threshold_clause_is_seen_deleted_inverted_or_weakened() -> None:
    """The clause is fired at its own section with each defect planted in turn: deleted, turned
    into a threshold, and weakened to a permission. Each plant must change the text, and a
    re-wrap of the same words must not read as one."""
    raw = _section(_text(_ROADMAP), "### §5 Delegation contract", "roadmap-template.md")
    section = _fold(raw)
    assert _missing(section, (_NO_SIZE_THRESHOLD,)) == []
    planted = {
        "deleted": section.replace(
            ", naming the events and never a size threshold", ""
        ),
        "inverted": section.replace(
            "never a size threshold", "a size threshold of three files"
        ),
        "weakened": section.replace(
            "Every brief states this explicitly", "A brief may state this"
        ),
    }
    for defect, text in planted.items():
        assert text != section, f"the {defect} plant changed nothing"
        assert _missing(text, (_NO_SIZE_THRESHOLD,)) == [_NO_SIZE_THRESHOLD], defect
    wrapped = raw.replace("explicitly, naming", "explicitly,\n    naming")
    assert wrapped != raw, "the re-wrap plant changed nothing"
    assert _missing(_fold(wrapped), (_NO_SIZE_THRESHOLD,)) == []


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


def test_the_cap_checks_see_planted_text_and_fail_loudly() -> None:
    sentence = (
        "The project still states its own cap on simultaneous agents and counts every live "
        "session on the account toward it; the kit sets no number and no default cap."
    )
    wrapped = sentence.replace("every live", "every\nlive").replace(
        "the kit sets", "the\nkit sets"
    )
    section = f"## Alpha\nAn earlier sentence. {wrapped} A later one.\n"
    assert _cap_sentence(section, "planted") == sentence
    assert _cap_problems(sentence) == []
    with pytest.raises(AssertionError, match="found 0"):
        _cap_sentence("## Alpha\nNothing about caps here.\n", "planted")
    with pytest.raises(AssertionError, match="found 2"):
        _cap_sentence(f"{sentence} {sentence}", "planted")

    placeholder = (
        "{when opted out, the project still states its own cap on simultaneous agents and "
        "counts every live session on the account toward it; the kit sets no number and no "
        "default cap}"
    )
    block = f"3. {{the usage window}}\n   {placeholder}\n"
    assert _cap_placeholder(block, "planted") == placeholder
    assert _cap_problems(placeholder) == []
    with pytest.raises(AssertionError, match="found 0"):
        _cap_placeholder("3. {the usage window}\n", "planted")
    with pytest.raises(AssertionError, match="found 2"):
        _cap_placeholder(f"{placeholder}\n{placeholder}\n", "planted")

    without_tail = sentence.replace("; the kit sets no number and no default cap", "")
    assert _cap_problems(without_tail) == [
        f"does not carry: {_OPT_OUT_CAP_CLAUSES[2]!r}"
    ]
    # Each default is planted at the end of the sentence and read back through the slicer, as
    # the real file is. The last one sits after an abbreviation: its period ends no sentence.
    for planted, found in (
        ("a default cap of two agents", "two"),
        ("6 at once", "6"),
        ("Twelve is typical", "Twelve"),
        ("cap twenty", "twenty"),
        ("a dozen agents", "dozen"),
        ("e.g. 20 agents", "20"),
    ):
        with_default = f"{sentence[:-1]} ({planted}). A later one."
        problems = _cap_problems(_cap_sentence(with_default, "planted"))
        assert problems == [f"names a number: {found!r}"], planted
    # A digit in the heading above the sentence is not a number the sentence names.
    heading_first = f"## Section 2\n{sentence} A later one.\n"
    assert _cap_problems(_cap_sentence(heading_first, "planted")) == []


def test_the_cap_surface_is_two_templates_of_the_three_scanned_files() -> None:
    """Three files are counted, the same three the other checks scan, and the two with a count
    above zero are the two the cap tests read: the planner SKILL.md is counted at 0 and is not one
    of them. The numbers are asserted, so a third place cannot join silently. What no check in this
    file can see, here or for the switch table, is the whole cap test being renamed out of
    collection: that diff is for review."""
    assert [path for path, _ in _CAP_STATEMENTS] == list(_SURFACE)
    assert [count for _, count in _CAP_STATEMENTS] == [0, 1, 1]
    assert [path for path, count in _CAP_STATEMENTS if count] == list(_CAP_SURFACE)
    assert len(_CAP_SURFACE) == 2
    assert len({path.resolve() for path in _CAP_SURFACE}) == 2
    assert _SKILL not in _CAP_SURFACE


def test_the_cap_clauses_are_template_only() -> None:
    """No cap clause may be, or sit inside, a switch clause: the planner SKILL.md must carry
    every switch clause, and `_CAP_STATEMENTS` holds it to no cap clause. Fired at a planted
    overlap first."""
    assert _overlapping(("alpha beta",), ("beta", "gamma")) == [("alpha beta", "beta")]
    assert _overlapping(("alpha",), ("gamma",)) == []
    assert (len(_OPT_OUT_CAP_CLAUSES), len(_SWITCH_CLAUSES)) == (3, 2), (
        "the overlap check compares 3 cap clauses with 2 switch clauses: a clause added to "
        "either tuple changes that surface, so state the new numbers here"
    )
    assert _overlapping(_OPT_OUT_CAP_CLAUSES, _SWITCH_CLAUSES) == []
