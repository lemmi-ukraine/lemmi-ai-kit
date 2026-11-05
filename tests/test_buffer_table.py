"""The generated triage table: the copied columns of Phase 3 come from the buffer, the decisions join on it.

A drain's triage table has one row per intake entry. Its columns that merely copy the buffer (the
heading line, the date, the age, the entry's `Home:` and `Verify-at:` fields, whether the entry is
in a commit) were typed by hand, and a table of a hundred rows hides a row dropped or repeated.
`scripts/buffer_table.py` of `learning-consolidator` generates those columns and joins the typed
decisions on the line number, so "one row per entry" is a set difference the run reports. The same
change puts one sentence in the reference: the plan states how many entries are not yet in a commit.

What each group asserts:

* The script, run as a subprocess from a COPY in a throwaway repository, as the harness runs it:
  one row per entry with the generated columns; the rows equal what `lint learnings
  --list-entries` prints for the same file (two instruments); `committed` for a new entry, an edit,
  a staged entry, a buffer never committed and a directory that is no repository; CRLF, a byte-order
  mark, a missing final newline and the Unicode line separators that `str.splitlines` would count;
  a fenced heading and a fence that never closes; cells with a pipe; the join, with a missing, an
  extra, a duplicate and a stale row; a decisions file the run cannot use; input it cannot read; and
  that the run only reads. Nothing imports the script from its place in the plugin tree: an import
  would write bytecode into the payload, and `publish-check` refuses a payload that holds any.
* Three drift guards for what the script copies from elsewhere: its action list against the table
  of Phase 2's Step 3, its fence mask against the lint's, its buffer path against the lint's.
* The wording: the reference's new section, the count sentence beside the entry count (its own
  test), the pointer in SKILL.md and its cap, and the printed commands, parsed by the script's own
  parser and never naming the buffer. Each check is a function over a string, so
  `test_every_check_sees_its_planted_positive` fires it at the old text and at half-edits, and
  `test_each_phrase_deleted_in_turn_is_reported` deletes every phrase of the shipped text in turn.

Every non-ASCII character in a fixture is built from `chr()`.

THE SURFACE, in numbers the tests assert: 3 files (the script, the reference, SKILL.md), 7 generated
columns plus 3 decision columns, 8 committed scenarios, 8 actions, 11 shapes of an unusable decision
row, 3 set-difference classes and 2 printed commands.
"""

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from lemmi_ai_kit import checks

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "learning-consolidator"
_SKILL = _SKILL_DIR / "SKILL.md"
_REFERENCE = _SKILL_DIR / "references" / "consolidation-actions.md"
_SCRIPT = _SKILL_DIR / "scripts" / "buffer_table.py"
_GUARD = _REPO_ROOT / "plugins" / "core" / "hooks" / "gate_learnings_drain.py"
_SURFACE: tuple[Path, ...] = (_SCRIPT, _REFERENCE, _SKILL)

_SKILL_NAME = "learning-consolidator SKILL.md"
_REFERENCE_NAME = "learning-consolidator references/consolidation-actions.md"

# The skill audit fails a SKILL.md at 500 lines and counts one more than the newline count.
_LINE_CAP = 499
_TIMEOUT_SECONDS = 120

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_SECTION_HEADING = "## Generated Triage Table (Phase 3)"
_PHASE_3_HEADING = "### Phase 3: Consolidation Plan"
_STEP_3_HEADING = "#### Step 3: Promotion Classification"
_POINTER_LEAD = "Before making any changes, present a consolidation plan to the user"

_GENERATED = ["line", "date", "age", "home", "anchor", "committed", "title"]
_DECIDED = ["action", "target", "rationale"]
_BUFFER = ".ai/learnings.md"

# --- slicers over a string -----------------------------------------------------------------


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _view(text: str) -> str:
    """The text with every run of whitespace as one space and bold markers dropped."""
    return " ".join(text.split()).replace("**", "")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced block
    is a comment of the code it holds, not a heading. A missing heading fails with the heading
    named, so a renamed section is a loud failure and never an empty match.
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


def _headings(text: str) -> list[str]:
    """Every heading line outside a fenced block, in order."""
    in_fence = False
    found: list[str] = []
    for line in text.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
        elif not in_fence and _HEADING.match(line):
            found.append(line)
    return found


def _slug(heading: str) -> str:
    """The anchor a renderer gives a heading: lower case, punctuation dropped, spaces as hyphens."""
    lowered = heading.lstrip("#").strip().lower()
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", lowered))


def _missing(view: str, facts: dict[str, str]) -> list[str]:
    """The names of the facts whose pattern is not found in `view`."""
    return [
        name
        for name, pattern in facts.items()
        if not re.search(pattern, view, re.IGNORECASE)
    ]


def _deleted(view: str, pattern: str) -> str:
    """`view` with the first match of `pattern` cut out; a pattern that matches nothing fails."""
    match = re.search(pattern, view, re.IGNORECASE)
    assert match is not None, (
        f"the pattern matches nothing, so it cannot be cut: {pattern}"
    )
    return view[: match.start()] + view[match.end() :]


def _reported(name: str, check: Callable[[str], list[str]], text: str) -> list[str]:
    """The problems of one check, a missing heading included, each led by `name`."""
    try:
        return [f"{name}: {problem}" for problem in check(text)]
    except AssertionError as error:
        return [f"{name}: {error}"]


# --- the fixtures: a buffer, a throwaway repository and a copy of the script ----------------


def _entry(
    day: str, title: str, *, home: str | None = None, anchor: str | None = None
) -> str:
    lines = [
        f"### [{day}] {title}",
        "- **Context**: where it came from",
        "- **Finding**: what was found",
        "- **Impact**: what to do",
    ]
    if home is not None:
        lines.append(f"- **Home**: {home}")
    if anchor is not None:
        lines.append(f"- **Verify-at**: {anchor}")
    return "\n".join(lines) + "\n\n"


_HEADER = "# Project Learnings\n\nA lean intake buffer.\n\n## Common Pitfalls\n\n"
_THREE = (
    _entry("2026-01-01", "First title", home="agents-rule", anchor="src/a.py::f"),
    _entry("2026-01-11", "Second title"),
    _entry("2026-01-21", "Third title", home="skill:example"),
)
_ALL = _HEADER + "".join(_THREE)
_NEW = _entry("2026-01-30", "A new entry")
_UNDATED = "### Undated title\n- **Finding**: no date in the heading\n\n"


def _heading_lines(text: str) -> list[int]:
    """The 1-based line of every `### ` heading, split on the newline alone (git's lines)."""
    return [
        number
        for number, line in enumerate(text.split("\n"), start=1)
        if line.startswith("### ")
    ]


@dataclass(frozen=True)
class _Project:
    root: Path
    buffer: Path
    script: Path
    cwd: Path


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert done.returncode == 0, f"git {' '.join(args)} failed: {done.stderr}"
    return done.stdout


def _project(
    parent: Path,
    *,
    repo: bool = True,
    committed: str | None = None,
    working: str | None = None,
    stage: bool = False,
    other_commit: bool = False,
) -> _Project:
    """A project with `.ai/` and a COPY of the script outside it, both under `parent`.

    `committed` is written and committed, then `working` replaces it uncommitted (staged when
    `stage`). A `committed` of None leaves the buffer untracked; `other_commit` gives the
    repository a commit that does not hold the buffer. Text is written as given, byte for byte.
    """
    root = parent / "project"
    (root / ".ai").mkdir(parents=True)
    tool = parent / "tool"
    tool.mkdir()
    script = tool / "buffer_table.py"
    shutil.copyfile(_SCRIPT, script)
    buffer = root / ".ai" / "learnings.md"
    if repo:
        _git(root, "init", "-q")
        _git(root, "config", "user.name", "fixture")
        _git(root, "config", "user.email", "fixture@example.invalid")
        _git(root, "config", "core.autocrlf", "false")
    if other_commit:
        (root / "README.md").write_text("a readme\n", encoding="utf-8")
        _git(root, "add", "--", "README.md")
        _git(root, "commit", "-q", "-m", "a commit without the buffer")
    if committed is not None:
        buffer.write_bytes(committed.encode("utf-8"))
        if repo:
            _git(root, "add", "--", ".ai/learnings.md")
            _git(root, "commit", "-q", "-m", "the buffer")
    if working is not None:
        buffer.write_bytes(working.encode("utf-8"))
        if repo and stage:
            _git(root, "add", "--", ".ai/learnings.md")
    return _Project(root=root, buffer=buffer, script=script, cwd=parent)


def _run(
    project: _Project,
    *args: str,
    with_project: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the copied script as a subprocess, by default from another working directory.

    Git is told not to look above the parent folder, so a temporary folder that happens to sit
    inside some checkout cannot turn "no repository" into an answer about that checkout.
    """
    argv = [sys.executable, "-B", str(project.script)]
    if with_project:
        argv += ["--project", str(project.root)]
    return subprocess.run(
        [*argv, *args],
        cwd=cwd or project.cwd,
        env={**os.environ, "GIT_CEILING_DIRECTORIES": str(project.cwd)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )


def _today(project: _Project, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(project, "--today", "2026-01-31", *args)


def _output(done: subprocess.CompletedProcess[str]) -> str:
    return done.stdout + done.stderr


_CELL = re.compile(r"(?<!\\)\|")


def _table(stdout: str) -> tuple[list[str], list[dict[str, str]]]:
    """The printed table: its header cells and one dict per row, an escaped pipe read back."""
    rows = [line for line in stdout.split("\n") if line.startswith("|")]
    assert len(rows) >= 2, f"no table in the output:\n{stdout}"
    header = [cell.strip() for cell in _CELL.split(rows[0])[1:-1]]
    body: list[dict[str, str]] = []
    for row in rows[2:]:
        cells = [cell.strip().replace("\\|", "|") for cell in _CELL.split(row)[1:-1]]
        assert len(cells) == len(header), f"a row with {len(cells)} cells: {row}"
        body.append(dict(zip(header, cells, strict=True)))
    return header, body


def _rows(done: subprocess.CompletedProcess[str]) -> list[dict[str, str]]:
    return _table(done.stdout)[1]


def _inventory_pairs(path: Path) -> list[tuple[int, str]]:
    """What `lint learnings --list-entries` prints for the file: its `line<TAB>title` rows."""
    lines = checks.inventory(checks.read_text(path), _BUFFER)
    start = lines.index("--- ENTRIES ---") + 1
    pairs: list[tuple[int, str]] = []
    for line in lines[start:]:
        number, title = line.split("\t", 1)
        pairs.append((int(number), title))
    return pairs


def _decisions(path: Path, rows: Sequence[dict[str, object] | str]) -> Path:
    """A decisions file: one JSON object per line, or a raw string written as it is."""
    lines = [row if isinstance(row, str) else json.dumps(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _decisions_for(text: str, *, skip: int | None = None) -> list[dict[str, object]]:
    """One typed decision per entry of `text`, none for the entry at index `skip`."""
    actions = ["ARCHIVE", "KEEP", "PROMOTE_TO_RULE"]
    rows: list[dict[str, object]] = []
    for index, number in enumerate(_heading_lines(text)):
        if index == skip:
            continue
        row: dict[str, object] = {"line": number, "action": actions[index % 3]}
        if actions[index % 3] == "PROMOTE_TO_RULE":
            row["target"] = "AGENTS.md"
            row["rationale"] = "universal | applies everywhere"
        rows.append(row)
    return rows


def _load(script: Path, name: str = "buffer_table_under_test") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script_module(tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    """The script loaded from a copy, so no bytecode lands in the plugin tree."""
    target = tmp_path_factory.mktemp("buffer-table-module") / "buffer_table.py"
    shutil.copyfile(_SCRIPT, target)
    return _load(target)


# --- the script: the columns ---------------------------------------------------------------


def test_the_script_ships_in_the_skills_scripts_folder() -> None:
    assert _SCRIPT.is_file(), f"{_SCRIPT} is not a file"
    assert _SCRIPT.parent == _SKILL_DIR / "scripts"
    assert (_SKILL_DIR / "scripts" / "drain_audit.py").is_file(), "the neighbour moved"


def test_one_row_per_entry_with_the_generated_columns(tmp_path: Path) -> None:
    text = _ALL + _UNDATED
    done = _today(_project(tmp_path, committed=text))
    assert done.returncode == 0, _output(done)
    header, rows = _table(done.stdout)
    assert header == _GENERATED
    lines = _heading_lines(text)
    assert len(lines) == 4
    assert rows == [
        {
            "line": str(lines[0]),
            "date": "2026-01-01",
            "age": "30",
            "home": "agents-rule",
            "anchor": "src/a.py::f",
            "committed": "yes",
            "title": "[2026-01-01] First title",
        },
        {
            "line": str(lines[1]),
            "date": "2026-01-11",
            "age": "20",
            "home": "-",
            "anchor": "-",
            "committed": "yes",
            "title": "[2026-01-11] Second title",
        },
        {
            "line": str(lines[2]),
            "date": "2026-01-21",
            "age": "10",
            "home": "skill:example",
            "anchor": "-",
            "committed": "yes",
            "title": "[2026-01-21] Third title",
        },
        {
            "line": str(lines[3]),
            "date": "-",
            "age": "-",
            "home": "-",
            "anchor": "-",
            "committed": "yes",
            "title": "Undated title",
        },
    ]
    assert "entries: 4" in done.stdout
    assert "committed: 4 yes, 0 no, 0 unknown" in done.stdout
    assert "today: 2026-01-31 (from --today)" in done.stdout


def test_the_rows_equal_what_list_entries_prints(tmp_path: Path) -> None:
    """Two instruments, one file: the table's (line, title) pairs are the inventory's."""
    project = _project(tmp_path, committed=_ALL + _UNDATED)
    done = _today(project)
    assert done.returncode == 0, _output(done)
    pairs = [(int(row["line"]), row["title"]) for row in _rows(done)]
    assert pairs == _inventory_pairs(project.buffer)
    assert len(pairs) == 4


@pytest.mark.parametrize(
    ("source", "expect"),
    [
        ("2026-01-01", "30"),
        ("2025-12-31", "31"),
        ("2026-01-31", "0"),
        ("2026-02-01", "-1"),
        ("2026-13-45", "-"),
    ],
)
def test_age_counts_days_from_today_and_an_impossible_date_reads_as_none(
    tmp_path: Path, source: str, expect: str
) -> None:
    done = _today(_project(tmp_path, committed=_HEADER + _entry(source, "Dated")))
    assert done.returncode == 0, _output(done)
    (row,) = _rows(done)
    assert row["age"] == expect
    assert row["date"] == (source if expect != "-" else "-")


def test_today_defaults_to_the_machine_day_and_a_bad_value_is_refused(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, committed=_HEADER + _entry("2026-01-01", "Dated"))
    before = date.today()
    done = _run(project)
    after = date.today()
    assert done.returncode == 0, _output(done)
    (row,) = _rows(done)
    day = date(2026, 1, 1)
    assert int(row["age"]) in {(before - day).days, (after - day).days}
    assert "(from the machine clock)" in done.stdout
    bad = _run(project, "--today", "2026-02-30")
    assert bad.returncode == 2, _output(bad)
    assert "Traceback" not in bad.stderr, bad.stderr


def test_both_bullet_spellings_are_read_the_first_value_wins_and_a_pipe_is_escaped(
    tmp_path: Path,
) -> None:
    text = (
        _HEADER
        + "### [2026-01-01] Spellings\n"
        + "- **Home:** first-home\n"
        + "- **Home**: second-home\n"
        + "- **Verify-at:** a|b\n\n"
        + "### [2026-01-02] Pipe | in the title\n- **Home**: x|y\n\n"
    )
    done = _today(_project(tmp_path, committed=text))
    assert done.returncode == 0, _output(done)
    rows = _rows(done)
    assert rows[0]["home"] == "first-home"
    assert rows[0]["anchor"] == "a|b"
    assert rows[1]["title"] == "[2026-01-02] Pipe | in the title"
    assert rows[1]["home"] == "x|y"
    assert "a\\|b" in done.stdout, (
        "a pipe in a cell must be escaped in the markdown table"
    )


@pytest.mark.parametrize("shape", ["lf", "crlf", "bom", "no-final-newline"])
def test_the_same_rows_whatever_the_encoding_shape_of_the_buffer(
    tmp_path: Path, shape: str
) -> None:
    """The buffer opens on an entry heading at line 1, where a byte-order mark would hide it."""
    text = "".join(_THREE)
    expected = _rows(_today(_project(tmp_path / "expected", committed=text)))
    assert [row["line"] for row in expected] == [str(n) for n in _heading_lines(text)]
    assert expected[0]["line"] == "1"
    written = {
        "lf": text,
        "crlf": text.replace("\n", "\r\n"),
        "bom": chr(0xFEFF) + text,
        "no-final-newline": text.rstrip("\n"),
    }[shape]
    done = _today(_project(tmp_path / shape, committed=written))
    assert done.returncode == 0, _output(done)
    assert _rows(done) == expected
    assert "\r" not in done.stdout


def test_unicode_line_separators_do_not_shift_a_later_line(tmp_path: Path) -> None:
    """`str.splitlines` also breaks on these, so a later entry would sit three lines early."""
    separators = chr(0x0C) + chr(0x2028) + chr(0x85)
    first = _entry("2026-01-01", "First").replace(
        "where it came from", f"where it{separators}came from"
    )
    text = _HEADER + first + _entry("2026-01-02", "Second")
    assert len(text.splitlines()) == text.count("\n") + len(separators), (
        "no separator planted"
    )
    project = _project(tmp_path, committed=text)
    done = _today(project)
    assert done.returncode == 0, _output(done)
    lines = [int(row["line"]) for row in _rows(done)]
    assert lines == _heading_lines(text)
    assert lines == [number for number, _ in _inventory_pairs(project.buffer)]


def test_the_run_only_reads(tmp_path: Path) -> None:
    """No commit, no copy, no write: the buffer, the status and the log are what they were."""
    project = _project(tmp_path, committed=_ALL, working=_ALL + _NEW)
    path = _decisions(tmp_path / "decisions.jsonl", _decisions_for(_ALL + _NEW))
    before = (
        project.buffer.read_bytes(),
        _git(project.root, "status", "--porcelain"),
        _git(project.root, "log", "--format=%H"),
        sorted(p.name for p in project.root.rglob("*") if ".git" not in p.parts),
    )
    for extra in ([], ["--decisions", str(path)]):
        done = _today(project, *extra)
        assert done.returncode == 0, _output(done)
    after = (
        project.buffer.read_bytes(),
        _git(project.root, "status", "--porcelain"),
        _git(project.root, "log", "--format=%H"),
        sorted(p.name for p in project.root.rglob("*") if ".git" not in p.parts),
    )
    assert after == before
    assert "learnings.md" in before[1], "the fixture holds no uncommitted change"


# --- the script: committed, from git blame -------------------------------------------------


@dataclass(frozen=True)
class _Scenario:
    states: list[str]
    exit_code: int
    committed: str | None
    working: str | None = None
    repo: bool = True
    stage: bool = False
    other_commit: bool = False


_SCENARIOS: dict[str, _Scenario] = {
    "committed and clean": _Scenario(["yes"] * 3, 0, committed=_ALL),
    "an appended entry is not committed": _Scenario(
        ["yes", "yes", "yes", "no"], 0, committed=_ALL, working=_ALL + _NEW
    ),
    "the blank line before a new entry does not flip the entry above it": _Scenario(
        ["yes", "yes", "yes", "no"],
        0,
        committed=_ALL.rstrip("\n") + "\n",
        working=_ALL.rstrip("\n") + "\n\n" + _NEW,
    ),
    "an edit to a committed entry makes that entry not committed": _Scenario(
        ["yes", "no", "yes"],
        0,
        committed=_ALL,
        working=_ALL.replace(
            "### [2026-01-11] Second title\n- **Context**: where it came from",
            "### [2026-01-11] Second title\n- **Context**: where it came from, edited",
        ),
    ),
    "a staged entry is not committed": _Scenario(
        ["yes", "yes", "yes", "no"], 0, committed=_ALL, working=_ALL + _NEW, stage=True
    ),
    "a buffer never committed, in a repository with a commit": _Scenario(
        ["no"] * 3, 0, committed=None, working=_ALL, other_commit=True
    ),
    "a buffer in a repository with no commit at all": _Scenario(
        ["no"] * 3, 0, committed=None, working=_ALL
    ),
    "a directory that is no repository: unknown, and never a pass": _Scenario(
        ["unknown"] * 3, 1, committed=None, working=_ALL, repo=False
    ),
}


@pytest.mark.parametrize("name", list(_SCENARIOS))
def test_committed_is_read_from_git_blame(tmp_path: Path, name: str) -> None:
    scenario = _SCENARIOS[name]
    project = _project(
        tmp_path,
        repo=scenario.repo,
        committed=scenario.committed,
        working=scenario.working,
        stage=scenario.stage,
        other_commit=scenario.other_commit,
    )
    done = _today(project)
    assert done.returncode == scenario.exit_code, _output(done)
    assert [row["committed"] for row in _rows(done)] == scenario.states
    counts = {state: scenario.states.count(state) for state in ("yes", "no", "unknown")}
    summary = f"committed: {counts['yes']} yes, {counts['no']} no, {counts['unknown']} unknown"
    assert summary in done.stdout, done.stdout


def test_a_crlf_working_tree_under_autocrlf_still_reads_as_committed(
    tmp_path: Path,
) -> None:
    """A Windows checkout writes CRLF where the commit holds LF; blame compares as git does."""
    project = _project(tmp_path, committed=_ALL)
    _git(project.root, "config", "core.autocrlf", "true")
    project.buffer.write_bytes(_ALL.replace("\n", "\r\n").encode("utf-8"))
    done = _today(project)
    assert done.returncode == 0, _output(done)
    assert [row["committed"] for row in _rows(done)] == ["yes"] * 3
    project.buffer.write_bytes((_ALL + _NEW).replace("\n", "\r\n").encode("utf-8"))
    states = [row["committed"] for row in _rows(_today(project))]
    assert states == ["yes", "yes", "yes", "no"]


# --- the script: a fence, and the lint's reading of one ------------------------------------

_FENCED = (
    _HEADER
    + "### [2026-01-01] Entry one\n"
    + "- **Finding**: shows the format:\n\n"
    + "```markdown\n"
    + "### [2026-02-02] A heading inside a fence\n"
    + "- **Home**: skill:inside-the-fence\n"
    + "```\n\n"
    + "- **Impact**: i\n\n"
    + _entry("2026-01-03", "Entry two")
)


def test_a_fenced_heading_is_listed_as_skipped_and_never_as_a_row(
    tmp_path: Path,
) -> None:
    done = _today(_project(tmp_path, committed=_FENCED))
    assert done.returncode == 0, _output(done)
    rows = _rows(done)
    assert [row["title"] for row in rows] == [
        "[2026-01-01] Entry one",
        "[2026-01-03] Entry two",
    ]
    assert rows[0]["home"] == "-", (
        "a field inside a fence is example text, not the entry's"
    )
    listed = {int(row["line"]) for row in rows}
    skipped = [number for number in _heading_lines(_FENCED) if number not in listed]
    assert len(skipped) == 1
    assert f"fenced headings skipped: 1 [{skipped[0]}]" in done.stdout, done.stdout


def test_the_table_follows_the_lints_structure_and_not_its_inventory(
    tmp_path: Path,
) -> None:
    """Three readers of one file: the lint's parser and the table agree, the inventory counts more."""
    project = _project(tmp_path, committed=_FENCED)
    done = _today(project)
    table = [int(row["line"]) for row in _rows(done)]
    parsed = [
        entry.line
        for block in checks.parse_blocks(checks.read_text(project.buffer))
        for entry in block.entries
    ]
    assert table == parsed
    inventory = [number for number, _ in _inventory_pairs(project.buffer)]
    assert len(inventory) == len(table) + 1
    assert set(table) < set(inventory)


def test_a_code_fence_that_never_closes_exits_1_and_says_what_it_hid(
    tmp_path: Path,
) -> None:
    text = (
        _HEADER
        + _entry("2026-01-01", "Before the fence")
        + "### [2026-01-02] Opens a fence\n- **Finding**: an example\n\n```text\nnever closed\n\n"
        + _entry("2026-01-03", "Hidden one")
        + _entry("2026-01-04", "Hidden two")
    )
    done = _today(_project(tmp_path, committed=text))
    assert done.returncode == 1, _output(done)
    assert [row["title"] for row in _rows(done)] == [
        "[2026-01-01] Before the fence",
        "[2026-01-02] Opens a fence",
    ]
    opened = text.split("\n").index("```text") + 1
    assert re.search(rf"never closes.*line {opened}\b", done.stdout), done.stdout
    assert "fenced headings skipped: 2" in done.stdout, done.stdout


def test_the_fence_mask_is_the_lints_on_a_corpus(script_module: ModuleType) -> None:
    lines = [
        "plain",
        "```",
        "### in a fence",
        "```",
        "~~~",
        "- **Home**: x",
        "   ```bash",
        "still inside",
        "```",
        "### outside again",
        "   ~~~",
    ]
    mask = cast(Callable[[list[str]], list[bool]], script_module.fence_mask)
    expected = checks._fence_mask(lines)  # pyright: ignore[reportPrivateUsage]
    assert mask(lines) == expected
    assert any(expected) and not all(expected), (
        "the corpus must hold both kinds of line"
    )


# --- the script: the join ------------------------------------------------------------------


def test_a_complete_join_exits_0_and_adds_the_decision_columns(tmp_path: Path) -> None:
    project = _project(tmp_path, committed=_ALL)
    # Written in reverse: the join is on the line number, not on the order of the rows.
    path = _decisions(tmp_path / "decisions.jsonl", _decisions_for(_ALL)[::-1])
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 0, _output(done)
    header, rows = _table(done.stdout)
    assert header == _GENERATED + _DECIDED
    assert [(row["action"], row["target"], row["rationale"]) for row in rows] == [
        ("ARCHIVE", "-", "-"),
        ("KEEP", "-", "-"),
        ("PROMOTE_TO_RULE", "AGENTS.md", "universal | applies everywhere"),
    ]
    assert "decision rows: 3" in done.stdout


def test_without_decisions_the_table_has_no_decision_columns(tmp_path: Path) -> None:
    done = _today(_project(tmp_path, committed=_ALL))
    assert _table(done.stdout)[0] == _GENERATED
    assert "decision rows:" not in done.stdout


def _join_problems(output: str) -> dict[str, list[str]]:
    """The reported set-difference lines, by class."""
    classes = {
        "missing": "entry without a decision row",
        "extra": "decision row without an entry",
        "duplicate": "line with more than one decision row",
    }
    return {
        key: [line for line in output.split("\n") if line.startswith(label)]
        for key, label in classes.items()
    }


def test_a_missing_row_is_reported_with_the_entry_it_names(tmp_path: Path) -> None:
    project = _project(tmp_path, committed=_ALL)
    path = _decisions(tmp_path / "decisions.jsonl", _decisions_for(_ALL, skip=1))
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 1, _output(done)
    problems = _join_problems(done.stdout)
    assert len(problems["missing"]) == 1
    assert f"line {_heading_lines(_ALL)[1]}" in problems["missing"][0]
    assert "Second title" in problems["missing"][0]
    assert problems["extra"] == [] and problems["duplicate"] == []
    assert [row["action"] for row in _rows(done)][1] == "(no row)"


def test_an_extra_row_is_reported_with_its_line_in_the_decisions_file(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, committed=_ALL)
    rows = _decisions_for(_ALL)
    rows.append({"line": 999, "action": "ARCHIVE"})
    path = _decisions(tmp_path / "decisions.jsonl", rows)
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 1, _output(done)
    problems = _join_problems(done.stdout)
    assert len(problems["extra"]) == 1
    assert "line 999" in problems["extra"][0]
    assert "decisions file line 4" in problems["extra"][0]
    assert problems["missing"] == [] and problems["duplicate"] == []


def test_a_duplicate_row_is_reported_and_its_cell_says_so(tmp_path: Path) -> None:
    project = _project(tmp_path, committed=_ALL)
    rows = _decisions_for(_ALL)
    rows.append({"line": rows[1]["line"], "action": "ARCHIVE"})
    path = _decisions(tmp_path / "decisions.jsonl", rows)
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 1, _output(done)
    problems = _join_problems(done.stdout)
    assert len(problems["duplicate"]) == 1
    assert f"line {rows[1]['line']}" in problems["duplicate"][0]
    assert "2 rows" in problems["duplicate"][0]
    assert "decisions file lines 2, 4" in problems["duplicate"][0]
    assert [row["action"] for row in _rows(done)][1] == "(duplicate)"
    assert problems["missing"] == [] and problems["extra"] == []


def test_all_three_classes_are_reported_in_one_run(tmp_path: Path) -> None:
    project = _project(tmp_path, committed=_ALL)
    rows = _decisions_for(_ALL, skip=0)
    rows.append({"line": 999, "action": "KEEP"})
    rows.append(dict(rows[1]))
    path = _decisions(tmp_path / "decisions.jsonl", rows)
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 1, _output(done)
    problems = _join_problems(done.stdout)
    assert [len(problems[key]) for key in ("missing", "extra", "duplicate")] == [
        1,
        1,
        1,
    ]


def test_a_decisions_file_typed_against_an_older_buffer_shows_as_a_difference(
    tmp_path: Path,
) -> None:
    """An entry added above shifts every line number: the join sees exactly that, both ways."""
    rows = _decisions_for(_ALL)
    newer = _HEADER + _entry("2025-12-01", "Added above") + "".join(_THREE)
    project = _project(tmp_path, committed=newer)
    path = _decisions(tmp_path / "decisions.jsonl", rows)
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 1, _output(done)
    problems = _join_problems(done.stdout)
    assert problems["missing"], "an entry at its new line has no row"
    assert problems["extra"] == [] or "decision row" in problems["extra"][0]
    shifted = _heading_lines(newer)
    assert any(f"line {n}" in " ".join(problems["missing"]) for n in shifted)


def test_an_empty_decisions_file_leaves_every_entry_without_a_row(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, committed=_ALL)
    path = tmp_path / "decisions.jsonl"
    path.write_text("\n\n", encoding="utf-8")
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 1, _output(done)
    assert len(_join_problems(done.stdout)["missing"]) == 3


def test_a_decisions_file_with_a_byte_order_mark_and_crlf_is_read(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, committed=_ALL)
    body = "\r\n".join(json.dumps(row) for row in _decisions_for(_ALL)) + "\r\n"
    path = tmp_path / "decisions.jsonl"
    path.write_bytes((chr(0xFEFF) + body).encode("utf-8"))
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 0, _output(done)


_UNUSABLE: dict[str, tuple[str, str]] = {
    "not json": ('{"line": 7,', "not valid JSON"),
    "not an object": ("[1, 2]", "not a JSON object"),
    "line is a string": ('{"line": "7", "action": "KEEP"}', "`line`"),
    "line is a bool": ('{"line": true, "action": "KEEP"}', "`line`"),
    "line below one": ('{"line": 0, "action": "KEEP"}', "`line`"),
    "no line": ('{"action": "KEEP"}', "`line`"),
    "no action": ('{"line": 7}', "`action`"),
    "unknown action": ('{"line": 7, "action": "DROP"}', "`action`"),
    "lower case action": ('{"line": 7, "action": "keep"}', "`action`"),
    "a copied column": (
        '{"line": 7, "action": "KEEP", "date": "2026-01-01"}',
        "`date`",
    ),
    "target is a number": ('{"line": 7, "action": "KEEP", "target": 3}', "`target`"),
}


@pytest.mark.parametrize("name", list(_UNUSABLE))
def test_a_decisions_row_the_run_cannot_use_exits_2_naming_its_line(
    tmp_path: Path, name: str
) -> None:
    raw, mentions = _UNUSABLE[name]
    project = _project(tmp_path, committed=_ALL)
    path = _decisions(
        tmp_path / "decisions.jsonl", ['{"line": 7, "action": "KEEP"}', raw]
    )
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 2, _output(done)
    assert "decisions file line 2" in done.stdout, done.stdout
    assert mentions in done.stdout, done.stdout
    assert "| line |" not in done.stdout, "nothing is joined, so no table is printed"
    assert "Traceback" not in done.stderr, done.stderr


def test_every_unusable_row_is_listed_in_one_run(tmp_path: Path) -> None:
    project = _project(tmp_path, committed=_ALL)
    path = _decisions(
        tmp_path / "decisions.jsonl",
        ["not json", '{"line": 7, "action": "KEEP"}', '{"line": 8, "action": "DROP"}'],
    )
    done = _today(project, "--decisions", str(path))
    assert done.returncode == 2, _output(done)
    assert "decisions file line 1" in done.stdout
    assert "decisions file line 3" in done.stdout
    assert "decisions file line 2" not in done.stdout


# --- the script: input it cannot read ------------------------------------------------------


def _unreadable(name: str, parent: Path) -> tuple[_Project, list[str]]:
    """A project the run cannot read in the way `name` says, and the extra arguments to run it."""
    if name == "no buffer":
        return _project(parent), []
    if name == "no entry in the buffer":
        return _project(
            parent, committed="# Project Learnings\n\n## Common Pitfalls\n"
        ), []
    if name == "a buffer that is not UTF-8":
        project = _project(parent)
        project.buffer.write_bytes(b"### [2026-01-01] Title \xff\xfe\n")
        return project, []
    return _project(parent, committed=_ALL), [
        "--decisions",
        str(parent / "nowhere.jsonl"),
    ]


@pytest.mark.parametrize(
    "name",
    [
        "no buffer",
        "no entry in the buffer",
        "a buffer that is not UTF-8",
        "a decisions file that is missing",
    ],
)
def test_input_the_run_cannot_read_exits_2_and_says_why(
    tmp_path: Path, name: str
) -> None:
    """A run that cannot see its subject never reports a clean table."""
    project, extra = _unreadable(name, tmp_path)
    done = _today(project, *extra)
    assert done.returncode == 2, _output(done)
    assert "ERROR" in done.stdout, _output(done)
    assert "Traceback" not in done.stderr, done.stderr
    assert "| line |" not in done.stdout


def test_a_project_directory_that_does_not_exist_exits_2(tmp_path: Path) -> None:
    project = _project(tmp_path, committed=_ALL)
    done = _run(project, "--project", str(tmp_path / "nowhere"), with_project=False)
    assert done.returncode == 2, _output(done)
    assert "ERROR" in done.stdout, _output(done)


def test_the_project_defaults_to_the_working_directory(tmp_path: Path) -> None:
    project = _project(tmp_path, committed=_ALL)
    done = _run(project, "--today", "2026-01-31", with_project=False, cwd=project.root)
    assert done.returncode == 0, _output(done)
    assert len(_rows(done)) == 3
    elsewhere = _run(project, "--today", "2026-01-31", with_project=False)
    assert elsewhere.returncode == 2, (
        "from a folder without a buffer there is nothing to read"
    )


def test_a_git_that_cannot_run_reads_as_unknown_and_exits_1(tmp_path: Path) -> None:
    """With nothing on the search path the run still lists the entries, and never says `yes`."""
    project = _project(tmp_path, committed=_ALL)
    nothing = tmp_path / "nothing-on-the-path"
    nothing.mkdir()
    done = subprocess.run(
        [sys.executable, "-B", str(project.script), "--project", str(project.root)],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(nothing)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert done.returncode == 1, _output(done)
    assert [row["committed"] for row in _rows(done)] == ["unknown"] * 3
    assert "committed could not be read: git could not be run" in done.stdout


def test_help_names_the_options_and_exits_0(tmp_path: Path) -> None:
    done = _run(_project(tmp_path, committed=_ALL), "--help", with_project=False)
    assert done.returncode == 0, _output(done)
    for option in ("--project", "--today", "--decisions"):
        assert option in done.stdout, f"{option} is not described by --help"


# --- drift guards: what the script copies from elsewhere ------------------------------------


def _step_3_actions(skill: str) -> list[str]:
    """The actions of the table under Step 3: the backticked first cell of each row."""
    section = _section(skill, _STEP_3_HEADING, _SKILL_NAME)
    return re.findall(r"^\| `([A-Z_]+)` \|", section, flags=re.MULTILINE)


def test_the_action_list_is_the_step_3_table(script_module: ModuleType) -> None:
    actions = list(cast(tuple[str, ...], script_module.ACTIONS))
    table = _step_3_actions(_text(_SKILL))
    assert len(table) == 8 and len(actions) == 8
    assert sorted(actions) == sorted(table)
    planted = _text(_SKILL).replace("| `MERGE_ENTRIES` |", "| `MERGED_ENTRIES` |")
    assert "MERGE_ENTRIES" not in _step_3_actions(planted), (
        "the reader must see a rename"
    )


def test_the_buffer_path_is_the_one_the_lint_reads(
    script_module: ModuleType, tmp_path: Path
) -> None:
    lint = checks.target_path("learnings", tmp_path).relative_to(tmp_path).as_posix()
    assert str(script_module.BUFFER) == lint == _BUFFER


# --- the wording of the reference and of SKILL.md -------------------------------------------

_SECTION_FACTS: dict[str, str] = {
    "the copied columns are generated, never typed": (
        r"\bcolumns that copy the buffer are generated, never typed\b"
    ),
    "a dropped or repeated row is a computed difference": (
        r"\ba row dropped or repeated by hand is a computed difference\b"
    ),
    "the script prints one row per entry from the buffer under the project root": (
        r"`buffer_table\.py` reads the buffer under the project root and prints one row "
        r"per entry\b"
    ),
    "line is the entry's heading line": r"`line` \(the entry's heading line\)",
    "date and age come from the title and --today, which defaults to the machine's day": (
        r"`date` and `age` in days \(from the `\[YYYY-MM-DD\]` title and `--today`, "
        r"which defaults to the machine's calendar day\)"
    ),
    "home is the Home: field": r"`home` \(the `Home:` field\)",
    "anchor is the Verify-at: field": r"`anchor` \(the `Verify-at:` field\)",
    "committed and the title close the list": r"`committed` and the title\.",
    "the decisions are the only typed part": r"\bThe decisions are the only typed part\b",
    "one JSON object per line, with line, action, target and rationale": (
        r"\bone JSON object per line, holding the entry's `line`, an `action` from the "
        r"table of Phase 2's Step 3 and optionally a `target` and a `rationale`"
    ),
    "no other key, a copied column is refused": (
        r"\band no other key \(a copied column in the file is refused\)"
    ),
    "the decisions join the entries on the line number": (
        r"\bjoins each object to its entry on the line number\b"
    ),
    "the set difference is reported both ways, in three classes": (
        r"\breports the set difference both ways: an entry with no row, a row whose line "
        r"is no entry, and a line with two rows\b"
    ),
    "line numbers move with every edit, so the table is regenerated after the last one": (
        r"\bLine numbers move with every edit of the buffer, so regenerate the table "
        r"after the last edit\b"
    ),
    "an older decisions file shows up as that same difference": (
        r"\ba decisions file typed against an older buffer shows up as that same "
        r"difference\b"
    ),
    "committed yes means every non-blank line is in a commit": (
        r"`yes` when every non-blank line of the entry is in a commit\b"
    ),
    "committed is read with git blame --porcelain on the working tree": (
        r"`git blame --porcelain` on the buffer as it stands in the working tree"
    ),
    "committed no means a line is not": (
        r"`no` when one is not \(an entry not yet committed, or an edit to one\)"
    ),
    "committed unknown means git could not answer": r"`unknown` when git could not answer",
    "exit 0 is a complete table, with decisions a complete join": (
        r"\b0 is a complete table \(with `--decisions`, a complete join\)"
    ),
    "exit 1 is rows to adjudicate: a difference, an unknown, a fence that never closes": (
        r"\b1 is rows to adjudicate: a set difference, an entry whose `committed` is "
        r"`unknown`, or a code fence that never closes\b"
    ),
    "exit 2 is input the run could not read, never clean": (
        r"\b2 is input the run could not read\b.{0,260}\bnever read it as clean\b"
    ),
    "a heading inside a fence is example text and each one skipped is listed": (
        r"\bA heading inside a code fence is example text, not an entry, and the run "
        r"lists each one it skipped\b"
    ),
    "the skipped count reconciles with the list-entries count of Phase 1": (
        r"\bcan be reconciled with the `--list-entries` count of Phase 1 step 0\b"
    ),
    "the command names the project root and never the buffer": (
        r"\bThe command names the project root and never the buffer\b"
    ),
    "like the lint, the run only reads: no commit and no copy": (
        r"\bLike `lint learnings`, the run only reads: it makes no commit and no copy\b"
    ),
    "so it does none of the steps of Operator Steps": (
        r"\bso it does none of the steps of \[\xa7 Operator Steps\]\(#operator-steps\)"
    ),
}

# The sentence that puts the count beside the entry count. It has its own facts and its own test.
_COUNT_SENTENCE = (
    r"The plan states the entry count and, beside it, how many entries are not yet in a "
    r"commit, read from the `committed` column, so deleting an entry that exists in no "
    r"commit is visible before the first removal\."
)
_COUNT_FACTS: dict[str, str] = {
    "the plan states the entry count and, beside it, the entries not yet in a commit": (
        r"\bThe plan states the entry count and, beside it, how many entries are not yet "
        r"in a commit\b"
    ),
    "the number is read from the committed column": r"\bread from the `committed` column\b",
    "so deleting an entry in no commit is visible before the first removal": (
        r"\bso deleting an entry that exists in no commit is visible before the first "
        r"removal\b"
    ),
}


def _section_view(reference: str) -> str:
    return _view(_section(reference, _SECTION_HEADING, _REFERENCE_NAME))


def _section_gaps(reference: str) -> list[str]:
    return _missing(_section_view(reference), _SECTION_FACTS)


def _count_sentence_gaps(reference: str) -> list[str]:
    view = _section_view(reference)
    gaps = _missing(view, _COUNT_FACTS)
    found = re.findall(_COUNT_SENTENCE, view)
    if len(found) != 1:
        gaps.append(f"the whole sentence appears {len(found)} times in the section")
    return gaps


def _pointer_gaps(skill: str, reference: str) -> list[str]:
    """What is wrong with the pointer in Phase 3 and the heading it names, as a list."""
    gaps: list[str] = []
    phase = _section(skill, _PHASE_3_HEADING, _SKILL_NAME)
    anchor = _slug(_SECTION_HEADING)
    links = re.findall(r"\]\(references/consolidation-actions\.md#([^)\s]+)\)", phase)
    if links.count(anchor) != 1:
        gaps.append(f"Phase 3 links {links}, not once #{anchor}")
    lines = [line for line in phase.split("\n") if f"#{anchor}" in line]
    if not lines or not lines[0].startswith(_POINTER_LEAD):
        gaps.append("the link is not on the line that opens Phase 3's plan")
    elif "triage table" not in lines[0]:
        gaps.append("the pointer line does not name the triage table")
    slugs = [_slug(heading) for heading in _headings(reference)]
    if slugs.count(anchor) != 1:
        gaps.append(f"the anchor #{anchor} names {slugs.count(anchor)} headings")
    return gaps


def test_the_reference_section_says_what_the_run_does() -> None:
    gaps = _section_gaps(_text(_REFERENCE))
    assert not gaps, f"{_REFERENCE_NAME}, {_SECTION_HEADING}, does not say: {gaps}"


def test_the_count_sentence_puts_the_uncommitted_count_beside_the_entry_count() -> None:
    reference = _text(_REFERENCE)
    gaps = _count_sentence_gaps(reference)
    assert not gaps, f"{_SECTION_HEADING} does not say: {gaps}"
    assert len(re.findall(r"The plan states the entry count", _view(reference))) == 1, (
        "the sentence appears outside its section, or twice"
    )
    assert "not yet in a commit" not in _view(_text(_SKILL)), (
        "SKILL.md has no room for it"
    )


def test_the_section_is_filed_once_as_a_level_two_heading() -> None:
    headings = _headings(_text(_REFERENCE))
    assert headings.count(_SECTION_HEADING) == 1
    assert [h for h in headings if h.startswith("## Generated")] == [_SECTION_HEADING]


def test_the_pointer_in_skill_md_resolves_to_the_section() -> None:
    gaps = _pointer_gaps(_text(_SKILL), _text(_REFERENCE))
    assert not gaps, f"{_SKILL_NAME}: {gaps}"
    assert _slug(_SECTION_HEADING) == "generated-triage-table-phase-3"


def test_skill_md_stays_within_the_line_cap() -> None:
    lines = _text(_SKILL).count("\n")
    assert lines <= _LINE_CAP, (
        f"SKILL.md has {lines} lines; the audit cap leaves {_LINE_CAP}"
    )


def _printed_commands(section: str) -> list[str]:
    """The lines of the section's fenced blocks that run the script."""
    in_fence = False
    found: list[str] = []
    for line in section.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
        elif in_fence and "buffer_table.py" in line:
            found.append(line.strip())
    return found


_PLACEHOLDERS = {
    "<absolute project root>": "/project",
    "<YYYY-MM-DD>": "2026-01-31",
    "<decisions file>": "decisions.jsonl",
}


def _filled(command: str) -> str:
    """The printed command with each placeholder filled in."""
    for placeholder, value in _PLACEHOLDERS.items():
        command = command.replace(placeholder, value)
    return command


def _argv(command: str) -> list[str]:
    """The tokens after the script, with each placeholder filled in."""
    words = shlex.split(_filled(command))
    index = next(i for i, word in enumerate(words) if word.endswith("buffer_table.py"))
    return words[index + 1 :]


def test_the_printed_commands_parse_and_never_name_the_buffer(
    script_module: ModuleType,
) -> None:
    section = _section(_text(_REFERENCE), _SECTION_HEADING, _REFERENCE_NAME)
    commands = _printed_commands(section)
    assert len(commands) == 2, commands
    parser = cast(argparse.ArgumentParser, script_module.build_parser())
    for command in commands:
        assert "learnings.md" not in command, (
            f"a printed line names the buffer: {command}"
        )
        assert not re.match(r"[A-Za-z_]\w*=", command), (
            f"a leading assignment: {command}"
        )
        assert command.startswith(
            'python "${CLAUDE_SKILL_DIR}/scripts/buffer_table.py"'
        )
        assert vars(parser.parse_args(_argv(command)))["project"] == "/project"
    assert (
        str(vars(parser.parse_args(_argv(commands[1])))["decisions"])
        == "decisions.jsonl"
    )
    used = {p for command in commands for p in re.findall(r"<[^>]+>", command)}
    assert used <= set(_PLACEHOLDERS), (
        f"unknown placeholders: {used - set(_PLACEHOLDERS)}"
    )
    assert ":.ai/learnings.md" not in section
    assert "cp .ai/learnings.md" not in section


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_the_learnings_guard_lets_the_printed_commands_through(
    tmp_path: Path, tool: str
) -> None:
    """The guard judges a shell line by its text, so a line that names the project and never the
    buffer is not one it denies. The judge is shown to see: it flags a removal, a redirect into the
    buffer and an in-place edit, so a None for the printed lines means it looked and found none."""
    copy = tmp_path / "gate_learnings_drain.py"
    shutil.copyfile(_GUARD, copy)
    module = _load(copy, "gate_learnings_drain_for_buffer_table")
    judge = cast(Callable[[str, str], str | None], module._shell_shape)  # pyright: ignore[reportPrivateUsage]
    for positive in (
        "rm .ai/learnings.md",
        "git show 'stash@{0}:.ai/learnings.md' > .ai/learnings.md",
        "sed -i '/^### /d' .ai/learnings.md",
    ):
        assert judge(positive, tool) is not None, f"the judge missed {positive!r}"
    section = _section(_text(_REFERENCE), _SECTION_HEADING, _REFERENCE_NAME)
    commands = _printed_commands(section)
    assert len(commands) == 2
    for command in commands:
        assert judge(_filled(command), tool) is None, (
            f"the guard would block {command!r}"
        )


def test_the_surface_in_numbers() -> None:
    assert len(_SURFACE) == 3 and all(path.is_file() for path in _SURFACE)
    assert len(_GENERATED) == 7 and len(_DECIDED) == 3
    assert len(_SCENARIOS) == 8 and len(_UNUSABLE) == 11


# --- the checks, fired at planted text -------------------------------------------------------


def test_every_check_sees_its_planted_positive() -> None:
    """A check that is silent on the real files means something only if it speaks on bad ones."""
    reference = _text(_REFERENCE)
    skill = _text(_SKILL)
    section = _section(reference, _SECTION_HEADING, _REFERENCE_NAME)
    old = reference.replace(section, "", 1)
    assert _SECTION_HEADING not in old
    for name, check in (
        ("section facts", _section_gaps),
        ("count sentence", _count_sentence_gaps),
    ):
        assert _reported(name, check, old), (
            f"{name}: silent on the text without the section"
        )
    # A half-edit: the count sentence cut out of the section, everything else kept.
    cut = reference.replace(
        section, re.sub(_COUNT_SENTENCE, "", " ".join(section.split())), 1
    )
    assert len(_count_sentence_gaps(cut)) == len(_COUNT_FACTS) + 1
    assert _section_gaps(cut) == [], (
        "the sentence belongs to its own check, not the section's"
    )
    # The whole sentence twice: a copy elsewhere in the section cannot pass for the original.
    found = re.search(_COUNT_SENTENCE, " ".join(section.split()))
    assert found is not None
    twice = reference.replace(section, section + "\n\n" + found.group(0), 1)
    assert any("2 times" in gap for gap in _count_sentence_gaps(twice))
    # The pointer: a Phase 3 without the link, a link on another line, and a renamed heading.
    link = "(references/consolidation-actions.md#generated-triage-table-phase-3)"
    assert link in skill and _pointer_gaps(skill, reference) == []
    assert _pointer_gaps(
        skill.replace(link, "(references/consolidation-actions.md)"), reference
    )
    assert _pointer_gaps(
        skill.replace(_POINTER_LEAD, f"Note: {_POINTER_LEAD}", 1), reference
    )
    assert _pointer_gaps(
        skill.replace("the generated triage table", "the generated list", 1), reference
    )
    renamed = reference.replace(_SECTION_HEADING, "## Elsewhere (Phase 3)")
    assert _pointer_gaps(skill, renamed)


def test_each_phrase_deleted_in_turn_is_reported() -> None:
    view = _section_view(_text(_REFERENCE))
    for name, pattern in _SECTION_FACTS.items():
        assert name in _missing(_deleted(view, pattern), _SECTION_FACTS), (
            f"deleting the phrase of {name!r} went unreported"
        )
    for name, pattern in _COUNT_FACTS.items():
        assert name in _missing(_deleted(view, pattern), _COUNT_FACTS), (
            f"deleting the phrase of {name!r} went unreported"
        )
    assert len(re.findall(_COUNT_SENTENCE, _deleted(view, _COUNT_SENTENCE))) == 0
