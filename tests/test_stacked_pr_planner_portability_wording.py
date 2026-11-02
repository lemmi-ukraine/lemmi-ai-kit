"""`stacked-pr-planner` names no one repository's tools, pipeline or layout without saying so.

Three places in the planner read as one repository's own. The risk-class table described its
migration class as one migration tool's files. Two notes on what a docs-only pull request costs
named the three gates of one pipeline, where another repository's pipeline runs other gates. And
the sample classifier in Step 6 sorts changed files by one project's paths, in a shell block and
in a trigger-table check, with no word saying that the paths are that project's. The change is
three labels, not a rewrite: the migration row names a second tool, the two notes say "the full
CI job", and the sample carries one line that says its paths are one project's layout. The
table's method does not change, so the set of classes stays what it was.

What each test asserts:

* `test_the_migration_row_names_both_migration_tools` reads the migration row of the class
  table in Step 2.
* `test_the_ci_advice_names_no_one_pipeline` reads the whole file for the old three-gate phrase
  in any wording or wrap, and reads Step 2 and Step 4 (where the two notes sit) for the new one.
* `test_the_sample_classifier_carries_its_label` reads the one fenced block in Step 6 that holds
  the class counters, for a comment that says its paths are one project's layout and sends the
  reader to the project's AGENTS.md. The comment may be one line or several consecutive comment
  lines, so a re-wrap does not fail it, and it need not point at any table: the row names none.
* `test_the_class_table_lists_the_same_four_classes` and
  `test_the_class_counters_are_the_classes_of_the_table` are NOT red on the old file: the classes
  were the same four. They guard the change against growing into a new taxonomy, and they hold
  the two places that name the classes (the table and the counters) to one set.
* The instrument tests fire the readers and the scans at planted text, so their silence on the
  real file means something. Every old shape is planted beside near misses that share words
  with it and must not be flagged.
"""

import re
from collections.abc import Callable
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "stacked-pr-planner"
    / "SKILL.md"
)
_WHERE = "stacked-pr-planner SKILL.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+\|?\s*$")
_COUNTER = re.compile(r"^([A-Z]{3,})=\$\(", re.MULTILINE)

# The classes of the risk-class table as they stood before the change.
_CLASSES: frozenset[str] = frozenset({"MIGRATION", "BACKEND", "TOOLING", "DOCS"})
_CLASS_COUNT = 4

_CI_PHRASE = "the full CI job"
# Where the two CI notes sit.
_CI_STEPS: tuple[str, ...] = ("## Step 2 ", "## Step 4 ")

# The old phrase named three gates joined by a plus, a comma, a slash, an ampersand or "and".
_JOIN = r"(?:\s*[+,/&]\s*(?:and\s+)?|\s+and\s+)"
_THREE_GATES = re.compile(
    rf"\blint\b{_JOIN}type-?check\b{_JOIN}pytest\b", re.IGNORECASE
)

# The words of the sample's label, each of which must be in one comment: one comment line, or
# consecutive comment lines that read as one.
_LABEL_PHRASES: tuple[str, ...] = (
    "one project's layout",
    "AGENTS.md",
)


def _text() -> str:
    return _SKILL.read_text(encoding="utf-8")


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


def _step(heading: str) -> str:
    return _section(_text(), heading, _WHERE)


def _class_rows(section: str, where: str) -> list[tuple[str, str]]:
    """(class, contents) for each data row of the table whose header cell is `Class`.

    The class is the backticked token of the first cell; a first cell that is not one stays as
    written, so a malformed row shows up as a class and is never skipped. The table ends at
    the first line that does not start with a pipe. A missing table fails loudly.
    """
    lines = section.split("\n")
    start = next(
        (at for at, line in enumerate(lines) if re.match(r"^\|\s*Class\s*\|", line)),
        None,
    )
    if start is None:
        raise AssertionError(f"{where}: no table whose header cell is 'Class'")
    rows: list[tuple[str, str]] = []
    for line in lines[start + 1 :]:
        if not line.startswith("|"):
            break
        if _SEPARATOR_ROW.match(line):
            continue
        cells = [
            cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
        ]
        named = re.fullmatch(r"`([A-Z][A-Z-]*)`", cells[0])
        rows.append((named.group(1) if named else cells[0], " ".join(cells[1:])))
    return rows


def _class_problems(section: str) -> list[str]:
    """What is wrong with the class table against the four classes it listed before."""
    names = [name for name, _ in _class_rows(section, _WHERE)]
    listed = set(names)
    problems: list[str] = []
    extra = sorted(listed - _CLASSES)
    if extra and len(listed) > _CLASS_COUNT:
        problems.append(f"the class table now lists a fifth class: {extra}")
    elif extra:
        problems.append(f"the class table lists a class it did not before: {extra}")
    missing = sorted(_CLASSES - listed)
    if missing:
        problems.append(f"the class table lost {missing}")
    if len(names) != len(listed):
        problems.append(f"a class is listed twice: {names}")
    return problems


def _migration_row(section: str) -> str:
    rows = [
        contents
        for name, contents in _class_rows(section, _WHERE)
        if name == "MIGRATION"
    ]
    if len(rows) != 1:
        raise AssertionError(
            f"{_WHERE}: {len(rows)} rows for the MIGRATION class, expected 1"
        )
    return _fold(rows[0])


def _migration_problems(row: str) -> list[str]:
    folded = _fold(row)
    problems: list[str] = []
    if "schema migrations (alembic, ef core)" not in folded.lower():
        problems.append("the row does not name 'schema migrations (Alembic, EF Core)'")
    if "EF Core" not in folded:
        problems.append("the row does not name EF Core")
    if folded.lower().startswith("alembic migrations"):
        problems.append("the row still opens on one tool's migrations")
    for kept in ("destructive data operations", "anything with a deploy hazard"):
        if kept not in folded:
            problems.append(f"the row lost {kept!r}")
    return problems


def _ci_problems(text: str) -> list[str]:
    """Each place `text` names the three gates of one pipeline, after folding line breaks."""
    return [
        f"names three gates of one pipeline: {match.group(0)!r}"
        for match in _THREE_GATES.finditer(_fold(text))
    ]


def _fenced_blocks(section: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in section.split("\n"):
        if _is_fence(line):
            if in_fence:
                blocks.append(current)
                current = []
            in_fence = not in_fence
        elif in_fence:
            current.append(line)
    return blocks


def _classifier_block(section: str, where: str) -> list[str]:
    """The lines of the one fenced block of `section` that holds the class counters."""
    holding = [
        block
        for block in _fenced_blocks(section)
        if any("MIGRATION=$(" in line for line in block)
    ]
    if len(holding) != 1:
        raise AssertionError(
            f"{where}: {len(holding)} fenced blocks hold the class counters, expected 1"
        )
    return holding[0]


def _comment_runs(block: list[str]) -> list[str]:
    """Each run of consecutive comment lines of `block` as one string, the `#` markers dropped.

    A label may be wrapped over several comment lines, so a run is read as one comment. Any
    other line ends the run, so two comments that code separates are never read as one.
    """
    runs: list[list[str]] = []
    in_run = False
    for line in block:
        if line.lstrip().startswith("#"):
            if not in_run:
                runs.append([])
            runs[-1].append(line.lstrip().lstrip("#"))
            in_run = True
        else:
            in_run = False
    return [_fold(" ".join(run)) for run in runs]


def _label_problems(block: list[str]) -> list[str]:
    """What is missing from the classifier block's label: one comment holding every phrase."""
    runs = _comment_runs(block)
    for run in runs:
        if all(phrase.lower() in run.lower() for phrase in _LABEL_PHRASES):
            return []
    return [
        f"no comment in the sample classifier says {list(_LABEL_PHRASES)}; "
        f"its comments are {runs}"
    ]


def _counter_names(block: list[str]) -> set[str]:
    return set(_COUNTER.findall("\n".join(block)))


# --- the change ---------------------------------------------------------------------------


def test_the_migration_row_names_both_migration_tools() -> None:
    problems = _migration_problems(_migration_row(_step("## Step 2 ")))
    assert not problems, f"{_WHERE}, Step 2 class table: " + "; ".join(problems)


def test_the_ci_advice_names_no_one_pipeline() -> None:
    problems = _ci_problems(_text())
    assert not problems, f"{_WHERE}: " + "; ".join(problems)
    for heading in _CI_STEPS:
        step = _fold(_step(heading))
        assert _CI_PHRASE in step, f"{_WHERE}, {heading.strip()}: no {_CI_PHRASE!r}"


def test_the_sample_classifier_carries_its_label() -> None:
    block = _classifier_block(_step("## Step 6 "), _WHERE)
    problems = _label_problems(block)
    assert not problems, f"{_WHERE}, Step 6: " + "; ".join(problems)


def test_the_class_table_lists_the_same_four_classes() -> None:
    problems = _class_problems(_step("## Step 2 "))
    assert not problems, f"{_WHERE}, Step 2: " + "; ".join(problems)


def test_the_class_counters_are_the_classes_of_the_table() -> None:
    block = _classifier_block(_step("## Step 6 "), _WHERE)
    assert _counter_names(block) == _CLASSES, (
        f"the sample classifier counts {sorted(_counter_names(block))}, the class table "
        f"lists {sorted(_CLASSES)}"
    )


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_what_it_claims() -> None:
    text = _text()
    assert (
        len(_class_rows(_step("## Step 2 "), _WHERE)) == _CLASS_COUNT == len(_CLASSES)
    )
    for heading in (*_CI_STEPS, "## Step 6 "):
        assert _step(heading).count("\n") > 5, f"{heading.strip()} is nearly empty"
    assert len(_classifier_block(_step("## Step 6 "), _WHERE)) >= 5
    assert text.count("\n") > 100


_OLD_ROW = (
    "Alembic migrations, destructive data operations, anything with a deploy hazard"
)
_NEW_ROW = (
    "Schema migrations (Alembic, EF Core), destructive data operations, anything "
    "with a deploy hazard"
)


def test_the_migration_check_sees_the_old_row_and_accepts_the_new_one() -> None:
    assert _migration_problems(_NEW_ROW) == [], "the control row is not clean"
    assert _migration_problems(_OLD_ROW), "the check missed the old row"
    wrapped = _NEW_ROW.replace("(Alembic, ", "(Alembic,\n  ")
    assert _migration_problems(wrapped) == [], "a re-wrap changed the verdict"
    for planted in (
        _NEW_ROW.replace("EF Core", "Flyway"),
        _NEW_ROW.replace(", destructive data operations", ""),
        _NEW_ROW.replace("Schema migrations", "Alembic migrations"),
    ):
        assert _migration_problems(planted), f"missed a planted row: {planted!r}"


def test_the_migration_reader_fails_loudly() -> None:
    planted = "## Step 2\n| Class | Contents |\n|---|---|\n| `DOCS` | prose |\n"
    with pytest.raises(AssertionError, match="0 rows for the MIGRATION class"):
        _migration_row(planted)
    with pytest.raises(AssertionError, match="no table whose header cell is 'Class'"):
        _class_rows("## Step 2\nno table here\n", "planted")


_THREE_GATE_FORMS: tuple[str, ...] = (
    "the full lint + typecheck + pytest job",
    "the whole lint + typecheck + pytest job",
    "the full lint, typecheck and pytest job",
    "the full lint, typecheck, and pytest job",
    "the full lint/typecheck/pytest job",
    "the full lint + type-check + pytest job",
    "the full lint and typecheck and pytest job",
    "it runs the whole lint +\n> typecheck +\n> pytest job",
)

_NOT_THREE_GATES: tuple[str, ...] = (
    "the full CI job",
    "the lint rules, a typecheck pass and a pytest plugin are different things",
    "lint + format + docs",
    "every gate the project's CI runs",
)


@pytest.mark.parametrize("form", _THREE_GATE_FORMS)
def test_the_ci_scan_sees_each_planted_form(form: str) -> None:
    assert _ci_problems(f"A docs-only PR still runs {form}, which is a reason."), form


@pytest.mark.parametrize("sentence", _NOT_THREE_GATES)
def test_the_ci_scan_is_silent_on_near_misses(sentence: str) -> None:
    assert _ci_problems(sentence) == []


_CLASSIFIER = (
    "F=$(git diff --name-only <base>...<layer>)",
    "MIGRATION=$(printf '%s\\n' \"$F\" | grep -cE '^db/migrations/')",
    "BACKEND=$(printf   '%s\\n' \"$F\" | grep -cE '^src/')",
    "DOCS=$(printf      '%s\\n' \"$F\" | grep -cE '^(docs|tasks)/')",
    "TOOLING=$(printf   '%s\\n' \"$F\" | grep -cE '^(scripts|tests)/')",
    "# exactly one of these four may be non-zero",
)
_LABEL = (
    "# One project's layout, as in the table above: replace these paths from the "
    "project's AGENTS.md."
)


def test_the_label_check_sees_a_missing_label_and_accepts_a_present_one() -> None:
    assert _label_problems([_LABEL, *_CLASSIFIER]) == [], "the control is not clean"
    assert _label_problems(list(_CLASSIFIER)), "the check missed the unlabelled sample"
    for planted in (
        # A comment about something else.
        ["# written for portability: no grep -P", *_CLASSIFIER],
        # The two phrases in comments that a code line separates are not one label.
        [
            "# one project's layout",
            _CLASSIFIER[0],
            "# AGENTS.md",
            *_CLASSIFIER[1:],
        ],
        # The label as code, not as a comment.
        [f'echo "{_LABEL[2:]}"', *_CLASSIFIER],
        # One phrase short, each way.
        [
            _LABEL.replace("the project's AGENTS.md", "the project's config"),
            *_CLASSIFIER,
        ],
        [_LABEL.replace("One project's layout", "These paths"), *_CLASSIFIER],
    ):
        assert _label_problems(planted), f"missed a planted shape: {planted[0]!r}"


def test_the_label_check_ignores_a_re_wrap_and_asks_for_no_pointer() -> None:
    for label in (
        # No pointer to a table: the row names none.
        ["# One project's layout: replace these paths from the project's AGENTS.md."],
        # Wrapped over two comment lines, at a clause and inside a phrase.
        [
            "# One project's layout: replace these paths",
            "# from the project's AGENTS.md.",
        ],
        [
            "# One project's",
            "# layout: replace these paths from the project's AGENTS.md.",
        ],
        # Wrapped over three lines, the later ones indented.
        [
            "# One project's layout:",
            "  # replace these paths from",
            "  # the project's AGENTS.md.",
        ],
    ):
        assert _label_problems([*label, *_CLASSIFIER]) == [], f"flagged {label!r}"


def test_the_classifier_reader_finds_one_block_and_fails_loudly() -> None:
    one = (
        "## Step 6\n\n```bash\n"
        + "\n".join(_CLASSIFIER)
        + "\n```\n\n```text\nother\n```\n"
    )
    assert _classifier_block(one, "planted") == list(_CLASSIFIER)
    assert _counter_names(list(_CLASSIFIER)) == _CLASSES
    with pytest.raises(AssertionError, match="0 fenced blocks hold the class counters"):
        _classifier_block("## Step 6\n\n```text\nother\n```\n", "planted")
    with pytest.raises(AssertionError, match="2 fenced blocks hold the class counters"):
        _classifier_block(one + "\n```bash\nMIGRATION=$(true)\n```\n", "planted")


def _real_table() -> str:
    return _step("## Step 2 ")


def _insert_row_after(row_start: str, new_row: str) -> Callable[[str], str]:
    def edit(section: str) -> str:
        lines = section.split("\n")
        at = next(i for i, line in enumerate(lines) if line.startswith(row_start))
        return "\n".join([*lines[: at + 1], new_row, *lines[at + 1 :]])

    return edit


def _drop_row(row_start: str) -> Callable[[str], str]:
    def edit(section: str) -> str:
        lines = section.split("\n")
        kept = [line for line in lines if not line.startswith(row_start)]
        assert len(kept) < len(lines), f"no row starts {row_start!r}"
        return "\n".join(kept)

    return edit


_PLANTED_TABLES: dict[str, Callable[[str], str]] = {
    "a fifth class": _insert_row_after(
        "| `DOCS` |", "| `DATA` | Seed data and fixtures |"
    ),
    "a class dropped": _drop_row("| `TOOLING` |"),
    "a class renamed": lambda s: s.replace("| `BACKEND` |", "| `RUNTIME` |", 1),
    "a class listed twice": _insert_row_after("| `DOCS` |", "| `DOCS` | More prose |"),
}


@pytest.mark.parametrize("form", list(_PLANTED_TABLES))
def test_the_class_check_sees_a_planted_change(form: str) -> None:
    section = _real_table()
    assert _class_problems(section) == [], "the control is not clean"
    planted = _PLANTED_TABLES[form](section)
    assert planted != section, f"{form}: the planted change changed nothing"
    assert _class_problems(planted), f"the check missed {form}"


def test_a_fifth_class_is_reported_as_the_table_listing_one() -> None:
    planted = _PLANTED_TABLES["a fifth class"](_real_table())
    problems = _class_problems(planted)
    assert any(
        problem.startswith("the class table now lists a fifth class")
        and "DATA" in problem
        for problem in problems
    ), problems


def test_the_class_check_is_silent_when_only_the_descriptions_change() -> None:
    section = _real_table()
    reworded = re.sub(
        r"^(\| `[A-Z]+` \|)[^|\n]*\|", r"\1 reworded |", section, flags=re.MULTILINE
    )
    assert reworded != section, "the planted rewording changed nothing"
    assert _class_problems(reworded) == []


def test_the_section_reader_fails_loudly_and_ignores_a_comment_in_a_fence() -> None:
    planted = "\n".join(
        [
            "## Step 6 - alpha",
            "```bash",
            "# a comment inside a fence is not a heading",
            "```",
            "after the fence",
            "### Sub",
            "sub body",
            "## Step 7 - beta",
            "beta body",
        ]
    )
    found = _section(planted, "## Step 6 ", "planted")
    assert "after the fence" in found and "sub body" in found
    assert "beta body" not in found
    with pytest.raises(AssertionError, match="no heading starting"):
        _section(planted, "## Step 9 ", "planted")


def test_the_fold_drops_blockquote_markers_so_a_wrapped_note_reads_as_one_line() -> (
    None
):
    assert _fold("> a +\n> b") == "a + b"
    assert _ci_problems("> it runs the whole lint +\n> typecheck + pytest job")
