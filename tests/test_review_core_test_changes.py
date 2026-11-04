"""`review_core` prints a seventh section on the change's tests, so a weakened test is seen.

A change can pass its own tests because one of them was edited to pass: an assertion removed, or
replaced by a weaker one, or a whole file deleted, in the same diff that changes the code. The
section prints a census of the changed test paths, the plan comparison over test paths only, and
one row for each hunk that removes or changes an assertion in an edited test or shared test helper
(REMOVED, CHANGED, MOVED? or DELETED), with the cells for what covers it now and for a broken
version that passes the old test and fails the new one printed as UNKNOWN. Each test builds a scratch
repository in which one fact is planted, runs the script as a process the way a session does, and
checks that the planted fact is printed. A control beside each shows the plain form does not see it
or that a near-miss prints nothing, so a fixture is a real positive and a zero means something.

Every check is a function that returns its problems for a section's lines, and is used three ways:
on the real script (no problems), on a section that prints only its header (a problem for every
case, so no case passes by default) and on a copy of the script with one mutation applied (the case
named for that mutation must report it). The mutation runner holds, in the same run, an unmutated
control that must pass and the header-only stub, which stands for the text the change replaced and
must fail every case.

THE SURFACE, in numbers the tests assert: 10 cases over the planted repository and 1 more for the
cap (read from a run with `--max-rows 1`), 8 mutations, 1 stub and 1 control. The census case
compares the printed figures with figures derived from git.

THE BOUNDARY CASES, in numbers the same test asserts: 4 git settings that must not hide a removed
assertion, 1 (a text conversion that prints nothing) that leaves a changed test file NOT CHECKED, in
2 kinds of file (modified, deleted); 9 token lines over 3 files and 4 comment lines over 2 files;
and one case each for the places where the reader could lose a row without a word.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "plugins" / "core" / "skills" / "post-task-review"
_SCRIPT = _SKILL / "scripts" / "review_core.py"
_MATRIX = _SKILL / "references" / "doc-impact-matrix.md"
_CHECKLIST = _SKILL / "references" / "review-checklist.md"
_SKILL_MD = _SKILL / "SKILL.md"

_KINDS = ("REMOVED", "CHANGED", "MOVED?", "DELETED")
_UNKNOWN = "UNKNOWN"

# ---------------------------------------------------------------------------------------------
# The planted facts. Each file is a text, and every expected number below is derived from the texts
# (a line number from the line's place in the text, a count from git), never typed beside them.
# ---------------------------------------------------------------------------------------------
_REMOVED_LINE = "    assert value is not None"
_CHANGED_OLD = "    assert out == EXPECTED"
_CHANGED_NEW = '    assert "x" in str(out)'
_COMMENT_LINE = "    # assert out == 3 is covered elsewhere"
_DATA_LINE = '    NEEDLES = ("one", "two")'
_MOVED_LINE = "    assert alpha(7) == 7"
_HELPER_LINE = "    assert value == 1.0"
_NON_TEST_LINE = "    assert x > 0"

_ALPHA_BASE = (
    "from app import alpha\n"
    "\n"
    "EXPECTED = 1\n"
    "\n"
    "\n"
    "def test_removed():\n"
    "    value = alpha(1)\n"
    "    assert value == 1\n"
    f"{_REMOVED_LINE}\n"
    "\n"
    "\n"
    "def test_changed():\n"
    "    out = alpha(1)\n"
    f"{_CHANGED_OLD}\n"
    "\n"
    "\n"
    "def test_other_lines():\n"
    f"{_COMMENT_LINE}\n"
    f"{_DATA_LINE}\n"
    "    return len(NEEDLES)\n"
)
_ALPHA_TASK = (
    _ALPHA_BASE.replace(f"{_REMOVED_LINE}\n", "")
    .replace(f"{_CHANGED_OLD}\n", f"{_CHANGED_NEW}\n")
    .replace(f"{_COMMENT_LINE}\n", "")
    .replace(f"{_DATA_LINE}\n", "")
)
_MOVED_FROM_BASE = (
    "from app import alpha\n\n\ndef test_moved():\n"
    f"{_MOVED_LINE}\n"
    "    assert alpha(8) == 8\n"
)
_MOVED_FROM_TASK = _MOVED_FROM_BASE.replace(f"{_MOVED_LINE}\n", "")
_MOVED_TO_BASE = (
    "from app import alpha\n\n\ndef test_elsewhere():\n    assert alpha(1) == 1\n"
)
_MOVED_TO_TASK = _MOVED_TO_BASE + f"{_MOVED_LINE}\n"
_GONE = (
    "from app import alpha\n\n\ndef test_gone_one():\n"
    "    assert alpha(2) == 2\n    assert alpha(3) == 3\n    assert alpha(4) == 4\n"
)
_RENAMED = (
    "from app import alpha\n\n\ndef test_renamed():\n"
    "    assert alpha(5) == 5\n    assert alpha(6) == 6\n"
)
_HELPERS_BASE = f"def check_twice(value):\n    assert value == 1\n{_HELPER_LINE}\n    return value\n"
_HELPERS_TASK = _HELPERS_BASE.replace(f"{_HELPER_LINE}\n", "")
_CHECKS_BASE = f"def check(x):\n    assert x\n{_NON_TEST_LINE}\n    return x\n"
_CHECKS_TASK = _CHECKS_BASE.replace(f"{_NON_TEST_LINE}\n", "")
_UNTOUCHED = "def test_untouched():\n    assert True\n"

_AGENTS = (
    "# Agents\n\n## Commands\n\n```bash\nuv run ruff check .\nuv run pytest -q\n```\n"
)


def _line_of(text: str, wanted: str) -> int:
    """The 1-based line of `wanted` in `text`, which must hold it exactly once."""
    lines = text.split("\n")
    assert lines.count(wanted) == 1, (
        f"{wanted!r} is not in the planted text exactly once"
    )
    return lines.index(wanted) + 1


class _Facts(NamedTuple):
    repo: Path
    removed_line: int
    changed_line: int
    moved_from_line: int
    moved_to_line: int
    helper_line: int


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _init(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    for key, value in (
        ("user.name", "t"),
        ("user.email", "t@example.com"),
        ("commit.gpgsign", "false"),
        ("core.autocrlf", "false"),
    ):
        _git(repo, "config", key, value)
    _write(repo / "AGENTS.md", _AGENTS)


def _commit(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")


def _planted_repo(repo: Path) -> _Facts:
    """The base commit, then the task: a removed assert, a replaced assert, a removed comment and a
    removed data line, an assertion moved to another test file, two deleted test files (one of them
    reappearing as an untracked test file), a shared helper that lost an assertion, and the same
    removal in a non-test file."""
    _init(repo)
    _write(repo / "src" / "app.py", "def alpha(x):\n    return x\n")
    _write(repo / "src" / "checks.py", _CHECKS_BASE)
    _write(repo / "tests" / "test_alpha.py", _ALPHA_BASE)
    _write(repo / "tests" / "test_moved_from.py", _MOVED_FROM_BASE)
    _write(repo / "tests" / "test_moved_to.py", _MOVED_TO_BASE)
    _write(repo / "tests" / "test_gone.py", _GONE)
    _write(repo / "tests" / "test_renamed_old.py", _RENAMED)
    _write(repo / "tests" / "helpers.py", _HELPERS_BASE)
    _write(repo / "tests" / "test_untouched.py", _UNTOUCHED)
    _commit(repo)
    _write(repo / "src" / "checks.py", _CHECKS_TASK)
    _write(repo / "tests" / "test_alpha.py", _ALPHA_TASK)
    _write(repo / "tests" / "test_moved_from.py", _MOVED_FROM_TASK)
    _write(repo / "tests" / "test_moved_to.py", _MOVED_TO_TASK)
    _write(repo / "tests" / "helpers.py", _HELPERS_TASK)
    (repo / "tests" / "test_gone.py").unlink()
    (repo / "tests" / "test_renamed_old.py").unlink()
    _write(repo / "tests" / "test_renamed_new.py", _RENAMED)
    return _Facts(
        repo=repo,
        removed_line=_line_of(_ALPHA_BASE, _REMOVED_LINE),
        changed_line=_line_of(_ALPHA_BASE, _CHANGED_OLD),
        moved_from_line=_line_of(_MOVED_FROM_BASE, _MOVED_LINE),
        moved_to_line=_line_of(_MOVED_TO_TASK, _MOVED_LINE),
        helper_line=_line_of(_HELPERS_BASE, _HELPER_LINE),
    )


class _Run(NamedTuple):
    repo: Path
    result: "subprocess.CompletedProcess[str]"

    @property
    def lines(self) -> list[str]:
        return self.result.stdout.splitlines()


def _run_script(script: Path, cwd: Path, *args: str) -> _Run:
    result = subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env=dict(os.environ),
    )
    return _Run(cwd, result)


def _run(repo: Path, *args: str) -> _Run:
    return _run_script(_SCRIPT, repo, *args)


def _section(run: _Run, number: int) -> list[str]:
    inside = False
    kept: list[str] = []
    for line in run.lines:
        if line.startswith("== "):
            inside = line.startswith(f"== {number}. ")
        elif inside:
            kept.append(line)
    return kept


class _Row(NamedTuple):
    kind: str
    where: str
    what: str
    covers: str
    broken: str
    detail: list[str]


def _rows(lines: list[str]) -> list[_Row]:
    rows: list[_Row] = []
    for line in lines:
        cells = line.split("\t")
        if len(cells) == 5 and cells[0] in _KINDS:
            rows.append(_Row(cells[0], cells[1], cells[2], cells[3], cells[4], []))
        elif line.startswith("  ") and rows:
            rows[-1].detail.append(line)
    return rows


def _find(lines: list[str], kind: str, where: str) -> _Row | None:
    found = [r for r in _rows(lines) if r.kind == kind and r.where == where]
    return found[0] if len(found) == 1 else None


def _starting(lines: list[str], prefix: str) -> list[str]:
    return [line for line in lines if line.startswith(prefix)]


# ---------------------------------------------------------------------------------------------
# The cases. Each returns the problems it finds in a section's lines; an empty list is a pass.
# ---------------------------------------------------------------------------------------------
def _case_removed(lines: list[str], facts: _Facts) -> list[str]:
    """(i) A removed assert in a modified test file prints REMOVED with the path and the old line."""
    where = f"tests/test_alpha.py:{facts.removed_line}"
    row = _find(lines, "REMOVED", where)
    if row is None:
        return [f"no single REMOVED row at {where}"]
    problems: list[str] = []
    if row.detail != [f"  - {_REMOVED_LINE.strip()}"]:
        problems.append(f"REMOVED detail is {row.detail}")
    if row.what != "1 assertion line(s) removed, nothing added":
        problems.append(f"REMOVED says {row.what!r}")
    helper = _find(lines, "REMOVED", f"tests/helpers.py:{facts.helper_line}")
    if helper is None:
        problems.append("no REMOVED row for the shared test helper")
    return problems


def _case_changed(lines: list[str], facts: _Facts) -> list[str]:
    """(ii) A replaced assertion prints CHANGED with both lines, the removed one and the added one."""
    where = f"tests/test_alpha.py:{facts.changed_line}"
    row = _find(lines, "CHANGED", where)
    if row is None:
        return [f"no single CHANGED row at {where}"]
    expected = [f"  - {_CHANGED_OLD.strip()}", f"  + {_CHANGED_NEW.strip()}"]
    problems: list[str] = []
    if row.detail != expected:
        problems.append(f"CHANGED detail is {row.detail}, not {expected}")
    if row.what != "1 assertion line(s) removed, 1 line(s) added":
        problems.append(f"CHANGED says {row.what!r}")
    return problems


def _case_deleted(lines: list[str], facts: _Facts) -> list[str]:
    """(iii) A deleted test file prints DELETED with the count of its assertion lines, and a file
    that reappears under another name reads N of N."""
    del facts
    gone = _find(lines, "DELETED", "tests/test_gone.py")
    renamed = _find(lines, "DELETED", "tests/test_renamed_old.py")
    problems: list[str] = []
    if gone is None:
        problems.append("no DELETED row for tests/test_gone.py")
    elif (
        gone.what
        != "3 assertion line(s) in the deleted file, 0 of 3 added again as identical text"
    ):
        problems.append(f"DELETED says {gone.what!r}")
    if renamed is None:
        problems.append("no DELETED row for tests/test_renamed_old.py")
    elif (
        renamed.what
        != "2 assertion line(s) in the deleted file, 2 of 2 added again as identical text"
    ):
        problems.append(f"the rename says {renamed.what!r}")
    return problems


def _case_moved(lines: list[str], facts: _Facts) -> list[str]:
    """(iv) An identical assertion line added to another test file prints MOVED? with the place, and
    the row is still counted in the totals."""
    where = f"tests/test_moved_from.py:{facts.moved_from_line}"
    row = _find(lines, "MOVED?", where)
    if row is None:
        return [f"no single MOVED? row at {where}"]
    problems: list[str] = []
    place = f"tests/test_moved_to.py:{facts.moved_to_line}"
    if row.what != f"1 assertion line(s) removed, identical text added at {place}":
        problems.append(f"MOVED? says {row.what!r}")
    if row.detail != [f"  - {_MOVED_LINE.strip()}"]:
        problems.append(f"MOVED? detail is {row.detail}")
    totals = _starting(lines, "rows: ")
    if len(totals) != 1 or "MOVED? 1" not in totals[0]:
        problems.append(f"the totals do not count the MOVED? row: {totals}")
    return problems


def _case_controls(lines: list[str], facts: _Facts) -> list[str]:
    """(v) The same removed assertion in a non-test path prints no row; a removed comment and a
    removed data line print no row but raise the per-file count of other removed lines."""
    del facts
    problems: list[str] = []
    if any("checks.py" in line or "x > 0" in line for line in lines):
        problems.append("the non-test path or its assertion is in the section")
    if any(
        _COMMENT_LINE.strip() in line or _DATA_LINE.strip() in line for line in lines
    ):
        problems.append("a comment or a data line was printed as a row")
    others = _starting(lines, "other removed lines: ")
    if others != ["other removed lines: tests/test_alpha.py\t2"]:
        problems.append(f"the other-lines count is {others}")
    if len(_rows(lines)) != 6:
        problems.append(f"{len(_rows(lines))} rows, not the 6 planted")
    return problems


_CENSUS = re.compile(
    r"^census: (\d+) of (\d+) changed path\(s\) are test paths "
    r"\((\d+) added, (\d+) modified, (\d+) deleted; \+(\d+) -(\d+) lines\); "
    r"the repository holds (\d+) test path\(s\)$"
)


def _derived_census(repo: Path) -> tuple[int, ...]:
    """The figures the census must print, from git commands over the repository."""
    status = [
        line.split("\t")
        for line in _git(
            repo, "diff", "--no-renames", "--name-status", "HEAD"
        ).splitlines()
    ]
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    changed = sorted({p for _, p in status} | set(untracked))
    is_test = [p for p in changed if p.startswith("tests/")]
    added = sum(1 for p in untracked if p in is_test) + sum(
        1 for s, p in status if p in is_test and s == "A"
    )
    deleted = sum(1 for s, p in status if p in is_test and s == "D")
    modified = len(is_test) - added - deleted
    plus = minus = 0
    for row in _git(repo, "diff", "--no-renames", "--numstat", "HEAD").splitlines():
        a, d, p = row.split("\t")
        if p in is_test:
            plus, minus = plus + int(a), minus + int(d)
    for p in untracked:
        if p in is_test:
            plus += len((repo / p).read_text(encoding="utf-8").splitlines())
    held = [
        p
        for p in _git(repo, "ls-files", "-c", "-o", "--exclude-standard").splitlines()
        if p.startswith("tests/") and (repo / p).is_file()
    ]
    return (
        len(is_test),
        len(changed),
        added,
        modified,
        deleted,
        plus,
        minus,
        len(held),
    )


def _case_census(lines: list[str], facts: _Facts) -> list[str]:
    """(vi) The census numbers (changed, added, modified, deleted, lines, repository total) equal
    the figures derived from git."""
    printed = _starting(lines, "census: ")
    if len(printed) != 1:
        return [f"{len(printed)} census lines"]
    found = _CENSUS.match(printed[0])
    if found is None:
        return [f"the census line has another shape: {printed[0]!r}"]
    got = tuple(int(g) for g in found.groups())
    want = _derived_census(facts.repo)
    return [] if got == want else [f"census {got}, git says {want}"]


def _case_rule_line(lines: list[str], facts: _Facts) -> list[str]:
    """The printed rule names the forms the census counted by."""
    del facts
    rule = _starting(lines, "test paths: ")
    if len(rule) != 1:
        return [f"{len(rule)} rule lines"]
    missing = [
        n
        for n in (
            "test, tests or __tests__",
            "test_*.py",
            "*_test.py",
            "*_test.go",
            "*.test.js",
            "*.spec.ts",
        )
        if n not in rule[0]
    ]
    return [f"the rule line does not name {missing}"] if missing else []


def _case_summary(lines: list[str], facts: _Facts) -> list[str]:
    """The totals and the denominators printed beside the rows."""
    del facts
    want_totals = (
        "rows: 6 (REMOVED 2, CHANGED 1, MOVED? 1, DELETED 2) "
        "over 4 modified and 2 deleted test file(s) read"
    )
    problems: list[str] = []
    if want_totals not in lines:
        problems.append(f"no totals line {want_totals!r}")
    if (
        "read: 7 of 7 changed test path(s) have a code extension; 0 not read"
        not in lines
    ):
        problems.append("no read line with its denominator")
    if not any(line.startswith("LIMIT: ") for line in lines):
        problems.append("the section does not end with its limit")
    return problems


def _case_limits(lines: list[str], facts: _Facts) -> list[str]:
    """The limit line names what the instrument cannot see."""
    del facts
    limit = " ".join(_starting(lines, "LIMIT: ")).lower()
    needed = (
        "token",
        "stronger or weaker is not judged",
        "skip and xfail markers are not read",
        "built by a helper",
        "case-sensitive",
        "--assertion assert.",
        "myapp.tests/",
    )
    missing = [n for n in needed if n not in limit]
    return [f"the limit does not say {missing}"] if missing else []


def _case_unknown_cells(lines: list[str], facts: _Facts) -> list[str]:
    """Every row prints the two cells for the review to fill in as UNKNOWN."""
    del facts
    rows = _rows(lines)
    if not rows:
        return ["no rows"]
    bad = [r.where for r in rows if (r.covers, r.broken) != (_UNKNOWN, _UNKNOWN)]
    return [f"cells not UNKNOWN in {bad}"] if bad else []


_CAP_ARGS = ("--max-rows", "1")


def _case_cap(lines: list[str], facts: _Facts) -> list[str]:
    """(ix) With --max-rows 1 one row is listed, the other five are NOT CHECKED and named, and the
    totals still count all six. Read from a run made with `_CAP_ARGS`."""
    del facts
    problems: list[str] = []
    if len(_rows(lines)) != 1:
        problems.append(f"{len(_rows(lines))} rows listed, not 1")
    note = "NOT CHECKED: test changes: 5 more row(s) not listed (--max-rows 1)"
    if note not in lines:
        problems.append(f"no {note!r}")
    if not any(line.startswith("rows: 6 (") for line in lines):
        problems.append("the totals do not count every row")
    return problems


_PLANTED_CASES: dict[str, Callable[[list[str], _Facts], list[str]]] = {
    "removed": _case_removed,
    "changed": _case_changed,
    "deleted": _case_deleted,
    "moved": _case_moved,
    "controls": _case_controls,
    "census": _case_census,
    "rule_line": _case_rule_line,
    "summary": _case_summary,
    "limits": _case_limits,
    "unknown_cells": _case_unknown_cells,
}


@pytest.fixture(scope="module")
def planted(tmp_path_factory: pytest.TempPathFactory) -> _Facts:
    return _planted_repo(tmp_path_factory.mktemp("planted") / "repo")


@pytest.fixture(scope="module")
def planted_run(planted: _Facts) -> _Run:
    return _run(planted.repo)


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_PLANTED_CASES) == 10, f"{len(_PLANTED_CASES)} cases, not the 10 stated"
    assert len(_MUTATIONS) == 8, f"{len(_MUTATIONS)} mutations, not the 8 stated"
    assert len({m.name for m in _MUTATIONS}) == len(_MUTATIONS), (
        "two mutations share a name"
    )
    assert (len(_SEEN_SHAPES), len(_UNREAD_KINDS)) == (4, 2), "the git settings differ"
    assert sorted(len(lines) for lines in _TOKEN_FILES.values()) == [3, 3, 3]
    assert sorted(len(lines) for lines in _COMMENT_FILES.values()) == [1, 3]


def test_control_the_plain_diff_misses_the_untracked_test_the_rename_ends_in(
    planted: _Facts,
) -> None:
    """The plain forms miss what the section is for: the removed assertion is a deletion git
    reports only as a changed file, and the renamed file is untracked, so a changed-files list
    holds neither a removed assertion nor a moved one."""
    names = _git(planted.repo, "diff", "--name-only", "HEAD").splitlines()
    assert "tests/test_alpha.py" in names
    assert "tests/test_renamed_new.py" not in names, (
        "control: the untracked file is invisible to diff"
    )
    assert (planted.repo / "tests" / "test_renamed_new.py").is_file()


@pytest.mark.parametrize("name", sorted(_PLANTED_CASES))
def test_each_case_holds_on_the_real_script(
    name: str, planted: _Facts, planted_run: _Run
) -> None:
    problems = _PLANTED_CASES[name](_section(planted_run, 7), planted)
    assert not problems, f"{name}: {problems}"


@pytest.mark.parametrize("name", sorted(_PLANTED_CASES))
def test_a_section_that_prints_only_its_header_fails_every_case(
    name: str, planted: _Facts
) -> None:
    """The stub: no case passes by default. Each case is fired at an empty section, which is what a
    script that opens section 7 and prints nothing leaves, and must report a problem."""
    problems = _PLANTED_CASES[name]([], planted)
    assert problems, f"{name} passed on a section that printed nothing"


def test_the_cap_case_fails_on_a_section_that_printed_nothing(planted: _Facts) -> None:
    assert _case_cap([], planted), (
        "the cap case passed on a section that printed nothing"
    )


def test_the_section_is_the_seventh_and_the_summary_counts_seven(
    planted_run: _Run,
) -> None:
    headers = [line for line in planted_run.lines if line.startswith("== ")]
    numbers = [
        re.match(r"== (\d+)\. ", h) for h in headers if not h.startswith("== Summary")
    ]
    assert [m[1] if m else "?" for m in numbers] == ["1", "2", "3", "4", "5", "6", "7"]
    assert headers[6] == "== 7. Test changes =="
    assert headers[-1] == "== Summary =="
    assert planted_run.result.returncode == 0, planted_run.result.stdout
    assert planted_run.lines[-1].startswith(
        "review_core: 8 changed file(s); 7 of 7 sections ran;"
    )


def test_the_plan_comparison_runs_over_test_paths_only_in_both_directions(
    planted: _Facts, tmp_path: Path
) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text(
        "tests/test_alpha.py\n- `tests/test_moved_from.py` the moved assertion\n"
        "tests/test_never_touched.py\nsrc/checks.py\nsrc/other.py\ndocs/\n",
        encoding="utf-8",
    )
    run = _run(planted.repo, "--plan", str(plan))
    lines = _section(run, 7)
    assert "plan: 3 of 6 plan path(s) are test paths" in lines
    assert (
        "changed test paths not in plan (5): tests/helpers.py, tests/test_gone.py, "
        "tests/test_moved_to.py, tests/test_renamed_new.py, tests/test_renamed_old.py"
    ) in lines
    assert "planned test paths not changed (1): tests/test_never_touched.py" in lines
    text = "\n".join(lines)
    assert (
        "src/checks.py" not in text
        and "src/other.py" not in text
        and "docs/" not in text
    ), "a non-test path, in or out of the plan, is not this section's business"
    assert any(x.startswith("changed, not in plan") for x in _section(run, 2)), (
        "section 2 still compares every path"
    )


def test_without_a_plan_the_section_says_so_and_does_not_count_a_second_skip(
    planted_run: _Run,
) -> None:
    lines = _section(planted_run, 7)
    assert any(
        line.startswith("plan: comparison over test paths not run (no --plan given")
        for line in lines
    )
    assert planted_run.lines[-1].endswith("0 NOT CHECKED; 1 skipped (not asked)")


def test_an_unreadable_plan_is_reported_once_in_section_2(
    planted: _Facts, tmp_path: Path
) -> None:
    run = _run(planted.repo, "--plan", str(tmp_path / "missing.txt"))
    assert run.result.returncode == 2
    assert sum(1 for line in run.lines if line.startswith("NOT CHECKED: ")) == 1
    assert any(
        line.startswith(
            "plan: comparison over test paths not run (the plan was unreadable"
        )
        for line in _section(run, 7)
    )


def test_tests_replaces_the_rule_with_the_projects_own(planted: _Facts) -> None:
    only = _section(_run(planted.repo, "--tests", "tests/test_alpha.py"), 7)
    assert "test paths: --tests entries only: tests/test_alpha.py" in only
    census = _CENSUS.match(_starting(only, "census: ")[0])
    assert census is not None and census.group(1) == "1" and census.group(2) == "8"
    assert {r.where.split(":")[0] for r in _rows(only)} == {"tests/test_alpha.py"}
    outside = _section(_run(planted.repo, "--tests", "src/*"), 7)
    rows = _rows(outside)
    assert [(r.kind, r.where) for r in rows] == [
        ("REMOVED", f"src/checks.py:{_line_of(_CHECKS_BASE, _NON_TEST_LINE)}")
    ], (
        "with the rule replaced a non-test path is read and the default test paths are not"
    )


def test_assertion_adds_the_projects_own_token(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init(repo)
    base = "def test_custom():\n    out = 4\n    verify_that(out, 4)\n    return out\n"
    _write(repo / "tests" / "test_custom.py", base)
    _commit(repo)
    _write(
        repo / "tests" / "test_custom.py", base.replace("    verify_that(out, 4)\n", "")
    )
    plain = _section(_run(repo), 7)
    assert (
        _rows(plain) == [] and "other removed lines: tests/test_custom.py\t1" in plain
    )
    added = _section(_run(repo, "--assertion", "verify_that("), 7)
    assert [(r.kind, r.where) for r in _rows(added)] == [
        ("REMOVED", "tests/test_custom.py:3")
    ]
    refused = _run(repo, "--assertion", "")
    assert refused.result.returncode == 2, (
        "an empty token would make every removed line an assertion"
    )


def test_max_rows_lists_up_to_the_cap_and_the_rest_are_not_checked(
    planted: _Facts,
) -> None:
    run = _run(planted.repo, *_CAP_ARGS)
    assert run.result.returncode == 2
    assert _case_cap(_section(run, 7), planted) == []
    assert run.lines[-1].startswith(
        "review_core: 8 changed file(s); 6 of 7 sections ran; 1 NOT CHECKED"
    )


def test_the_default_cap_is_forty_rows(tmp_path: Path) -> None:
    """45 separate hunks, each removing one assertion: 40 rows are listed, the other 5 are NOT
    CHECKED and named, and the totals still count all 45."""
    repo = tmp_path / "repo"
    _init(repo)
    base = "".join(
        f"def test_{n}():\n    value = {n}\n    assert value == {n}\n    return value\n\n\n"
        for n in range(45)
    )
    _write(repo / "tests" / "test_many.py", base)
    _commit(repo)
    _write(
        repo / "tests" / "test_many.py", re.sub(r"    assert value == \d+\n", "", base)
    )
    run = _run(repo)
    lines = _section(run, 7)
    assert run.result.returncode == 2
    assert len(_rows(lines)) == 40
    assert (
        "NOT CHECKED: test changes: 5 more row(s) not listed (--max-rows 40)" in lines
    )
    assert any(x.startswith("rows: 45 (REMOVED 45, ") for x in lines)


def test_no_test_path_changed_prints_the_census_and_no_rows(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init(repo)
    _write(repo / "src" / "app.py", "def alpha(x):\n    return x\n")
    _write(repo / "tests" / "test_a.py", "def test_a():\n    assert True\n")
    _commit(repo)
    _write(repo / "src" / "app.py", "def alpha(x):\n    return x + 1\n")
    run = _run(repo)
    lines = _section(run, 7)
    assert run.result.returncode == 0
    assert (
        "census: 0 of 1 changed path(s) are test paths (0 added, 0 modified, 0 deleted; +0 -0 lines); "
        "the repository holds 1 test path(s)"
    ) in lines
    assert "no rows: no test path changed" in lines
    assert _rows(lines) == []


def test_a_clean_tree_prints_a_census_of_nothing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init(repo)
    _write(repo / "tests" / "test_a.py", "def test_a():\n    assert True\n")
    _commit(repo)
    run = _run(repo)
    assert run.result.returncode == 0
    assert any(
        line.startswith("census: 0 of 0 changed path(s)") for line in _section(run, 7)
    )


def test_the_rule_counts_directories_and_file_names_and_not_their_near_misses(
    tmp_path: Path,
) -> None:
    """The classes of shape: a directory named test, tests or __tests__ at any depth and in any
    case, and file names by language; with near-miss names that must not count."""
    repo = tmp_path / "repo"
    _init(repo)
    _write(repo / "README.md", "base\n")
    _commit(repo)
    positives = (
        "tests/a.py",
        "pkg/tests/b.py",
        "test/c.rb",
        "web/__tests__/d.js",
        "src/Tests/Case.cs",
        "lib/test_core.py",
        "lib/core_test.py",
        "pkg/foo_test.go",
        "web/app.test.js",
        "web/app.test.tsx",
        "web/app.spec.ts",
        "web/app.spec.mjs",
        "lib/models_spec.rb",
        "lib/models_test.rb",
        "src/FooTest.java",
        "src/FooTests.java",
        "src/FooTest.kt",
        "src/FooTests.kt",
        "src/FooTest.cs",
        "src/FooTests.cs",
    )
    near_misses = (
        "src/contest.py",
        "src/latest.py",
        "src/Contest.java",
        "src/testing/util.py",
        "src/attest_helper.py",
        "src/protest.go",
        "src/app_test_data.json",
        "docs/testing.md",
        "src/app.test.json",
        "src/spec.ts",
        "docs/tests",
    )
    for path in (*positives, *near_misses):
        _write(repo / path, "x\n")
    lines = _section(_run(repo), 7)
    census = _CENSUS.match(_starting(lines, "census: ")[0])
    assert census is not None
    assert census.group(1) == str(len(positives)), (
        f"{census.group(1)} counted, {len(positives)} planted as test paths"
    )
    assert census.group(2) == str(len(positives) + len(near_misses))


def test_a_git_failure_in_the_diff_read_is_not_checked_and_exits_two(
    planted: _Facts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """White-box on purpose, and one of two such tests (the other reads the call's arguments): no
    black-box input makes git fail on this one call and not on the earlier ones, so the script is
    imported and its git runner is made to fail for the section's own diff read (the one call that
    pins the a/ and b/ prefixes)."""
    module = _load_script()
    real_git = module._git  # pyright: ignore[reportPrivateUsage]

    def failing(root: Path | None, *args: str, **kwargs: tuple[int, ...]) -> bytes:
        if "--src-prefix=a/" in args:
            raise module._GitError("planted failure")  # pyright: ignore[reportPrivateUsage]
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(module, "_git", failing)
    monkeypatch.chdir(planted.repo)
    code = module.main([])
    printed = capsys.readouterr().out.splitlines()
    assert code == 2
    assert (
        "NOT CHECKED: test changes: the diff could not be read (planted failure)"
        in printed
    )
    assert printed[-1].startswith(
        "review_core: 8 changed file(s); 6 of 7 sections ran; 1 NOT CHECKED"
    )
    assert any(line.startswith("census: ") for line in printed), (
        "the census does not need the diff"
    )


# ---------------------------------------------------------------------------------------------
# What git prints for the section's own diff read. A git setting that makes `git diff` print
# anything but unified hunks must not turn a removed assertion into "no rows", and a changed test
# file that git printed no hunk for is NOT CHECKED, never read as clean.
# ---------------------------------------------------------------------------------------------
_SHAPED_PATH = "tests/test_shaped.py"
_OTHER_PATH = "src/shaped.py"
_SHAPED_LINE = "    assert value > 0"
_SHAPED_BASE = f"def test_shaped():\n    value = 1\n{_SHAPED_LINE}\n    return value\n"
_SHAPED_TASK = _SHAPED_BASE.replace(f"{_SHAPED_LINE}\n", "")


class _Shape(NamedTuple):
    name: str
    attributes: str
    config: tuple[tuple[str, str], ...]
    env: tuple[tuple[str, str], ...]


# Each setting alone left the old section with no unified hunk to read (or with a file git called
# binary) while the stat still counted the removed line. `echo` stands for any external viewer.
_SEEN_SHAPES = (
    _Shape("an external diff in the config", "", (("diff.external", "echo"),), ()),
    _Shape(
        "an external diff in the environment", "", (), (("GIT_EXTERNAL_DIFF", "echo"),)
    ),
    _Shape(
        "an external diff driver chosen by an attribute",
        "*.py diff=viewer\n",
        (("diff.viewer.command", "echo"),),
        (),
    ),
    _Shape("a -diff attribute", "*.py -diff\n", (), ()),
)
# The setting that stays unread: a text conversion that prints nothing leaves no hunk at all, and
# the stat (which does not convert) still counts the removed line.
_BLANK = _Shape(
    "a text conversion that prints nothing",
    "*.py diff=blank\n",
    (("diff.blank.textconv", "true"),),
    (),
)
_UNREAD_KINDS = ("modified", "deleted")


def _shaped_repo(repo: Path, shape: _Shape) -> None:
    """The base commit, under `shape`: the test and a non-test file with the same assertion."""
    _init(repo)
    if shape.attributes:
        _write(repo / ".gitattributes", shape.attributes)
    _write(repo / _SHAPED_PATH, _SHAPED_BASE)
    _write(repo / _OTHER_PATH, _SHAPED_BASE)
    for key, value in shape.config:
        _git(repo, "config", key, value)
    _commit(repo)


@pytest.mark.parametrize("shape", _SEEN_SHAPES, ids=[s.name for s in _SEEN_SHAPES])
def test_a_git_setting_that_replaces_the_diff_does_not_hide_a_removed_assertion(
    shape: _Shape, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The old call took whatever `git diff` printed: with an external viewer or a `-diff`
    attribute there was no unified hunk, and the section said "no rows" beside a census that
    counted the removed line. The call now asks for the text form itself, and the row is printed."""
    repo = tmp_path / "repo"
    _shaped_repo(repo, shape)
    _write(repo / _SHAPED_PATH, _SHAPED_TASK)
    for key, value in shape.env:
        monkeypatch.setenv(key, value)
    run = _run(repo)
    lines = _section(run, 7)
    want = [("REMOVED", f"{_SHAPED_PATH}:{_line_of(_SHAPED_BASE, _SHAPED_LINE)}")]
    assert [(r.kind, r.where) for r in _rows(lines)] == want, lines
    assert run.result.returncode == 0, run.result.stdout


@pytest.mark.parametrize("kind", _UNREAD_KINDS)
def test_a_changed_test_file_git_printed_no_hunk_for_is_not_checked_and_exits_two(
    kind: str, tmp_path: Path
) -> None:
    """The stat says the file lost lines and git printed nothing to read them from. The section
    names the file as NOT CHECKED and exits 2; it does not count the file as read and prints no
    row for it."""
    repo = tmp_path / "repo"
    _shaped_repo(repo, _BLANK)
    if kind == "deleted":
        (repo / _SHAPED_PATH).unlink()
    else:
        _write(repo / _SHAPED_PATH, _SHAPED_TASK)
    run = _run(repo)
    lines = _section(run, 7)
    notes = _starting(lines, "NOT CHECKED: test changes: ")
    assert len(notes) == 1 and _SHAPED_PATH in notes[0], lines
    assert _rows(lines) == [] and not _starting(lines, "rows: "), lines
    assert "no rows: 0 modified and 0 deleted test file(s) read" in "\n".join(lines)
    assert run.result.returncode == 2, run.result.stdout
    assert run.lines[-1].startswith(
        "review_core: 1 changed file(s); 6 of 7 sections ran; 1 NOT CHECKED"
    )


@pytest.mark.parametrize(
    "case", ("a line is only added", "the removal is not in a test file")
)
def test_the_unread_file_check_is_quiet_when_no_test_file_lost_a_line(
    case: str, tmp_path: Path
) -> None:
    """The near-misses, under the same text conversion: a stat with nothing removed in a test
    file is not a gap, and a removed line in a file that is not a test path is not this section's."""
    repo = tmp_path / "repo"
    _shaped_repo(repo, _BLANK)
    if case == "a line is only added":
        _write(repo / _SHAPED_PATH, f"{_SHAPED_BASE}    return 0\n")
    else:
        _write(repo / _OTHER_PATH, _SHAPED_TASK)
    run = _run(repo)
    assert run.result.returncode == 0, run.result.stdout
    assert not _starting(run.lines, "NOT CHECKED: "), run.lines


def test_the_text_form_is_asked_for_code_files_only(
    planted: _Facts, monkeypatch: pytest.MonkeyPatch
) -> None:
    """White-box, with the one before it: `--text` makes git print every file as text, so the
    section's diff names the code extensions it reads, one case-blind pathspec for each, and never
    asks for an image or an archive. (A black-box run cannot see the difference.)"""
    module = _load_script()
    real_git = module._git  # pyright: ignore[reportPrivateUsage]
    calls: list[tuple[str, ...]] = []

    def spy(root: Path | None, *args: str, **kwargs: tuple[int, ...]) -> bytes:
        if "--src-prefix=a/" in args:
            calls.append(args)
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(module, "_git", spy)
    monkeypatch.chdir(planted.repo)
    assert module.main([]) == 0
    assert len(calls) == 1, "the section reads its diff with one call"
    args = calls[0]
    assert "--no-ext-diff" in args and "--text" in args
    specs = args[args.index("--") + 1 :]
    assert specs, "--text with no pathspec would diff an image or an archive as text"
    assert all(spec.startswith(":(icase)*.") for spec in specs), specs
    extensions = module._CODE_EXTENSIONS  # pyright: ignore[reportPrivateUsage]
    assert {spec.removeprefix(":(icase)*") for spec in specs} == set(extensions)


# ---------------------------------------------------------------------------------------------
# The .NET form: the built-in tokens are case-sensitive and a project directory is a test path only
# through --tests. The floor is stated in the limit line and the usage, and the stated form works.
# ---------------------------------------------------------------------------------------------
_DOTNET_TEST = "tests/FooTests.cs"
_DOTNET_PROJECT = "MyApp.Tests/Cases.cs"
_DOTNET_LINE = "        Assert.Equal(1, value);"
_DOTNET_BASE = (
    "public class Cases\n{\n    public void Adds()\n    {\n        var value = 1;\n"
    f"{_DOTNET_LINE}\n    }}\n}}\n"
)
_DOTNET_TASK = _DOTNET_BASE.replace(f"{_DOTNET_LINE}\n", "")


def test_the_dotnet_form_needs_the_two_flags_the_section_names(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init(repo)
    for path in (_DOTNET_TEST, _DOTNET_PROJECT):
        _write(repo / path, _DOTNET_BASE)
    _commit(repo)
    for path in (_DOTNET_TEST, _DOTNET_PROJECT):
        _write(repo / path, _DOTNET_TASK)
    line = _line_of(_DOTNET_BASE, _DOTNET_LINE)
    plain = _section(_run(repo), 7)
    census = _CENSUS.match(_starting(plain, "census: ")[0])
    assert census is not None
    assert (census.group(1), census.group(2)) == ("1", "2"), (
        "the project directory is not a test path by default"
    )
    assert _rows(plain) == [], "the capitalised token is not an assertion by default"
    assert f"other removed lines: {_DOTNET_TEST}\t1" in plain, plain
    token = _section(_run(repo, "--assertion", "Assert."), 7)
    assert [(r.kind, r.where) for r in _rows(token)] == [
        ("REMOVED", f"{_DOTNET_TEST}:{line}")
    ]
    both = _section(_run(repo, "--tests", "MyApp.Tests/", "--assertion", "Assert."), 7)
    assert [(r.kind, r.where) for r in _rows(both)] == [
        ("REMOVED", f"{_DOTNET_PROJECT}:{line}")
    ]


def test_the_usage_names_the_dotnet_form() -> None:
    """Red on the usage as it stood, which did not say that a capitalised assertion or a project
    directory needs a flag. The limit line says it too, and `_case_limits` holds that one."""
    text = _SCRIPT.read_text(encoding="utf-8")
    usage = _plain(_between(text, "USAGE (from anywhere", "OUTPUT: a header"))
    for needle in ("case-sensitive", "--assertion Assert.", "MyApp.Tests/"):
        assert needle in usage, f"the usage does not say {needle!r}"


# ---------------------------------------------------------------------------------------------
# The reader's entries and boundaries: what counts as an assertion line, and the places the hunk
# reader and the row printer could lose a row without a word. Each case is a black-box run over a
# scratch repository, with the line numbers and counts derived from the planted texts.
# ---------------------------------------------------------------------------------------------
def _task_repo(repo: Path, base: dict[str, str], task: dict[str, str | None]) -> Path:
    """A base commit holding `base`, then the task: each path of `task` rewritten, or deleted when
    its text is None."""
    _init(repo)
    for path, text in base.items():
        _write(repo / path, text)
    _commit(repo)
    for path, text in task.items():
        if text is None:
            (repo / path).unlink()
        else:
            _write(repo / path, text)
    return repo


def _where(row: _Row) -> tuple[str, int]:
    path, _, number = row.where.rpartition(":")
    return path, int(number)


# One removed line for each entry of the token floor, each alone in its own hunk: the line is an
# assertion by that entry only, so an entry that drops out of the pattern loses its row.
_TOKEN_FILES = {
    "tests/test_tokens.py": (
        "    assert value == 1",
        "    self.assertEqual(value, 1)",
        "    with pytest.raises(ValueError):",
    ),
    "web/app.test.js": (
        "    expect(value);",
        "    value.should.equal(1);",
        "    check(value).toBeTruthy();",
    ),
    "pkg/foo_test.go": (
        '    t.Errorf("got %v", value)',
        '    t.Fatalf("got %v", value)',
        "    t.Fail()",
    ),
}
# One removed comment in each comment style: never an assertion, however it reads, and counted.
_COMMENT_FILES = {
    "tests/test_comments.py": ("    # assert value == 1",),
    "web/comments.test.js": (
        "    // expect(value);",
        "    /* expect(value); */",
        "     * expect(value);",
    ),
}


def _block(number: int, line: str | None) -> str:
    return (
        f"def case_{number}():\n"
        + (f"{line}\n" if line else "")
        + f"    return {number}\n\n"
    )


def test_every_token_of_the_floor_makes_a_removed_line_an_assertion(
    tmp_path: Path,
) -> None:
    base: dict[str, str] = {}
    task: dict[str, str | None] = {}
    want: set[tuple[str, int]] = set()
    for path, lines in _TOKEN_FILES.items():
        text = "".join(_block(n, line) for n, line in enumerate(lines))
        base[path] = text
        task[path] = "".join(_block(n, None) for n in range(len(lines)))
        want |= {(path, _line_of(text, line)) for line in lines}
    rows = _rows(_section(_run(_task_repo(tmp_path / "repo", base, task)), 7))
    assert {_where(r) for r in rows} == want, [r.where for r in rows]
    assert {r.kind for r in rows} == {"REMOVED"}


def test_a_removed_comment_is_never_an_assertion_in_any_comment_style(
    tmp_path: Path,
) -> None:
    base: dict[str, str] = {}
    task: dict[str, str | None] = {}
    for path, lines in _COMMENT_FILES.items():
        base[path] = "".join(_block(n, line) for n, line in enumerate(lines))
        task[path] = "".join(_block(n, None) for n in range(len(lines)))
    lines = _section(_run(_task_repo(tmp_path / "repo", base, task)), 7)
    assert _rows(lines) == [], "a comment line was read as an assertion"
    for path, comments in _COMMENT_FILES.items():
        assert f"other removed lines: {path}\t{len(comments)}" in lines, path


@pytest.mark.parametrize(
    ("case", "removed", "added"),
    (
        (
            "one added line answers one of two identical removed lines",
            ("    assert alpha(7) == 7", "    assert alpha(7) == 7"),
            ("    assert alpha(7) == 7",),
        ),
        (
            "only one of two removed lines is added elsewhere",
            ("    assert alpha(1) == 1", "    assert alpha(2) == 2"),
            ("    assert alpha(1) == 1",),
        ),
    ),
    ids=("identical lines", "one of two"),
)
def test_a_row_is_moved_only_when_every_removed_line_has_its_own_added_line(
    case: str, removed: tuple[str, ...], added: tuple[str, ...], tmp_path: Path
) -> None:
    """A row never reads MOVED? while a removed line is left without an added line of its own: a
    line added once answers one removed line, and one matched line is not all of them."""
    gone = (
        "def test_gone():\n"
        + "".join(f"{line}\n" for line in removed)
        + "    return 1\n"
    )
    away = "def test_away():\n    return 2\n"
    away_task = away + "".join(f"{line}\n" for line in added)
    repo = _task_repo(
        tmp_path / "repo",
        {"tests/test_gone.py": gone, "tests/test_away.py": away},
        {
            "tests/test_gone.py": "def test_gone():\n    return 1\n",
            "tests/test_away.py": away_task,
        },
    )
    rows = _rows(_section(_run(repo), 7))
    assert [(r.kind, r.where) for r in rows] == [
        ("REMOVED", f"tests/test_gone.py:{gone.splitlines().index(removed[0]) + 1}")
    ], case
    answered = [d for d in rows[0].detail if "identical text added at" in d]
    assert len(answered) == len(added), (case, rows[0].detail)
    place = f"tests/test_away.py:{_line_of(away_task, added[0])}"
    assert place in answered[0], (case, answered)


def test_a_removed_blank_line_is_not_counted_among_the_other_removed_lines(
    tmp_path: Path,
) -> None:
    base = "def test_blank():\n    value = 1\n\n    return value\n"
    repo = _task_repo(
        tmp_path / "repo",
        {"tests/test_blank.py": base},
        {"tests/test_blank.py": base.replace("\n\n", "\n")},
    )
    lines = _section(_run(repo), 7)
    assert _rows(lines) == []
    assert "other removed lines: none in 1 modified test file(s) read" in lines, lines


def test_a_removed_line_that_starts_with_two_dashes_is_not_read_as_a_file_header(
    tmp_path: Path,
) -> None:
    """In a diff the removed line `-- drop` is printed `--- drop`, which is also how a file header
    starts. Read as a header it renames the file for every later hunk, and the row is lost."""
    dash = "-- drop the table"
    assertion = "    assert value == 1"
    base = f'SQL = """\n{dash}\n"""\n\n\ndef test_dashed():\n    value = 1\n{assertion}\n    return value\n'
    task = base.replace(f"{dash}\n", "").replace(f"{assertion}\n", "")
    repo = _task_repo(
        tmp_path / "repo",
        {"tests/test_dashed.py": base},
        {"tests/test_dashed.py": task},
    )
    lines = _section(_run(repo), 7)
    assert [(r.kind, r.where) for r in _rows(lines)] == [
        ("REMOVED", f"tests/test_dashed.py:{_line_of(base, assertion)}")
    ], lines
    assert "other removed lines: tests/test_dashed.py\t1" in lines, lines


def test_a_test_file_with_a_space_in_its_name_is_read(tmp_path: Path) -> None:
    """For a path with a space git ends its header lines with a tab; the tab is not the name."""
    path = "tests/test spaced.py"
    line = "    assert value == 1"
    base = f"def test_spaced():\n    value = 1\n{line}\n    return value\n"
    repo = _task_repo(
        tmp_path / "repo", {path: base}, {path: base.replace(f"{line}\n", "")}
    )
    rows = _rows(_section(_run(repo), 7))
    assert [(r.kind, r.where) for r in rows] == [
        ("REMOVED", f"{path}:{_line_of(base, line)}")
    ]


def test_a_staged_rename_with_an_edit_is_a_deleted_file_and_its_lines_are_counted(
    tmp_path: Path,
) -> None:
    """With rename detection the hunks of the old file are printed under the new name, and the old
    one is then a deleted file with nothing in it. The section's diff keeps the two apart."""
    lines = tuple(f"    assert alpha({n}) == {n}" for n in range(1, 5))
    old = (
        "def test_four():\n" + "".join(f"{line}\n" for line in lines) + "    return 1\n"
    )
    repo = tmp_path / "repo"
    _init(repo)
    _write(repo / "tests" / "test_old.py", old)
    _commit(repo)
    _git(repo, "mv", "tests/test_old.py", "tests/test_new.py")
    _write(repo / "tests" / "test_new.py", old.replace(f"{lines[-1]}\n", ""))
    _git(repo, "add", "-A")
    rows = _rows(_section(_run(repo), 7))
    assert [(r.kind, r.where, r.what) for r in rows] == [
        (
            "DELETED",
            "tests/test_old.py",
            f"{len(lines)} assertion line(s) in the deleted file, "
            f"{len(lines) - 1} of {len(lines)} added again as identical text",
        )
    ]


def test_a_row_lists_five_removed_lines_and_counts_the_rest(tmp_path: Path) -> None:
    count = 8
    lines = tuple(f"    assert alpha({n}) == {n}" for n in range(count))
    base = (
        "def test_many():\n" + "".join(f"{line}\n" for line in lines) + "    return 1\n"
    )
    repo = _task_repo(
        tmp_path / "repo",
        {"tests/test_many.py": base},
        {"tests/test_many.py": "def test_many():\n    return 1\n"},
    )
    rows = _rows(_section(_run(repo), 7))
    assert [r.what for r in rows] == [
        f"{count} assertion line(s) removed, nothing added"
    ]
    assert rows[0].detail == [f"  - {line.strip()}" for line in lines[:5]] + [
        f"  ... and {count - 5} more removed assertion line(s)"
    ]


def test_a_long_removed_line_is_clipped_to_the_row_width(tmp_path: Path) -> None:
    long_line = "    assert alpha(1) == " + "x" * 200
    base = f"def test_long():\n{long_line}\n    return 1\n"
    repo = _task_repo(
        tmp_path / "repo",
        {"tests/test_long.py": base},
        {"tests/test_long.py": "def test_long():\n    return 1\n"},
    )
    rows = _rows(_section(_run(repo), 7))
    assert [d.strip() for d in rows[0].detail] == [
        "- " + long_line.strip()[:117] + "..."
    ]
    assert len(rows[0].detail[0].strip()) == 2 + 120


def test_a_changed_test_path_without_a_code_extension_is_counted_and_not_read(
    tmp_path: Path,
) -> None:
    note = '  "note": "assert value == 1",'
    data = f'{{\n{note}\n  "other": 2\n}}\n'
    code = "def test_c():\n    value = 1\n    assert value == 1\n    return value\n"
    repo = _task_repo(
        tmp_path / "repo",
        {"tests/data.json": data, "tests/test_c.py": code},
        {
            "tests/data.json": data.replace(f"{note}\n", ""),
            "tests/test_c.py": code.replace("    assert value == 1\n", ""),
        },
    )
    lines = _section(_run(repo), 7)
    assert (
        "read: 1 of 2 changed test path(s) have a code extension; 1 not read" in lines
    )
    assert [(r.kind, _where(r)[0]) for r in _rows(lines)] == [
        ("REMOVED", "tests/test_c.py")
    ]


@pytest.mark.parametrize("entry", ("./tests/test_alpha.py", "tests\\test_alpha.py"))
def test_tests_entries_are_read_with_a_leading_dot_slash_and_with_backslashes(
    entry: str, planted: _Facts
) -> None:
    only = _section(_run(planted.repo, "--tests", entry), 7)
    assert "test paths: --tests entries only: tests/test_alpha.py" in only
    census = _CENSUS.match(_starting(only, "census: ")[0])
    assert census is not None and census.group(1) == "1"
    assert {_where(r)[0] for r in _rows(only)} == {"tests/test_alpha.py"}


def test_a_negative_max_rows_lists_nothing_and_counts_every_row(
    planted: _Facts,
) -> None:
    run = _run(planted.repo, "--max-rows", "-1")
    lines = _section(run, 7)
    total = int(_starting(lines, "rows: ")[0].split()[1])
    assert _rows(lines) == []
    assert (
        f"NOT CHECKED: test changes: {total} more row(s) not listed (--max-rows -1)"
        in lines
    )
    assert run.result.returncode == 2


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("review_core_under_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------------------------
# The skill's own text: the script pointer names the section and the checklist has the rows.
# ---------------------------------------------------------------------------------------------
def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _marker_at(text: str, marker: str, after: int = 0) -> int:
    """The offset of `marker` at or after `after`, or -1. A line break may stand for any run of
    whitespace inside the marker, so a paragraph that is re-wrapped is still found."""
    words = [re.escape(word) for word in marker.split()]
    found = re.compile(r"\s+".join(words)).search(text, after)
    return -1 if found is None else found.start()


def _between(text: str, start: str, end: str) -> str:
    begin = _marker_at(text, start)
    assert begin >= 0, f"no marker {start!r}"
    stop = _marker_at(text, end, begin)
    assert stop >= 0, f"no marker {end!r} after {start!r}"
    return text[begin:stop]


_POINTER_OLD = "the diff stat, line endings, lint scope and Step 7b's matrix lookups"
_POINTER_NEW = (
    "the diff stat, the test changes (Steps 1 and 2), line endings, lint scope and "
    "Step 7b's matrix lookups"
)


_PARAGRAPH_START = "Step 9 is the close self-challenge"


def _opening_paragraph(text: str) -> str:
    return _plain(_between(text, _PARAGRAPH_START, "### Step 0:"))


def test_the_skill_pointer_names_the_seventh_section() -> None:
    text = _SKILL_MD.read_text(encoding="utf-8")
    paragraph = _opening_paragraph(text)
    assert _POINTER_NEW in paragraph
    assert _POINTER_OLD not in paragraph, "the old pointer is still there"
    assert len(text.splitlines()) <= 499, "the edit must be line-neutral"


def test_the_pointer_markers_survive_a_re_wrapped_paragraph() -> None:
    """The planted positive: re-wrapped at 30 columns the paragraph splits its first sentence, so
    a plain search for the marker fails (the control) and the folded paragraph is unchanged."""
    text = _SKILL_MD.read_text(encoding="utf-8")
    region = _between(text, _PARAGRAPH_START, "### Step 0:")
    paragraph = textwrap.fill(
        " ".join(region.split()),
        width=30,
        break_long_words=False,
        break_on_hyphens=False,
    )
    wrapped = text.replace(region, paragraph + "\n\n")
    assert wrapped != text and wrapped.find(_PARAGRAPH_START) < 0, (
        "the planted wrap must split the marker, or this tests nothing"
    )
    assert _opening_paragraph(wrapped) == _opening_paragraph(text)


_STEP_1_ROW = (
    "- [ ] The tests that already exist for the touched area and for two neighbouring areas are "
    "listed before the change's own tests are judged (the script's test-changes section prints how "
    "many test paths changed and how many the repository holds)"
)
_STEP_2_ROWS = (
    "- [ ] Every removed or changed assertion in an edited test or shared test helper (the script's "
    "test-changes section lists them) has what covers it now and a broken version that passes the "
    'old test and fails the new one, or the word "none"; a "none" is a finding (see '
    "`claim-boundaries.md`, the paragraph on a mutant that survives)",
    "- [ ] The test files that changed match the plan's list of test files that may change: each "
    "changed test path the plan does not list, and each listed one left alone, is explained",
)


def _checklist_step(number: int) -> str:
    text = _CHECKLIST.read_text(encoding="utf-8")
    start = text.index(f"### Step {number}:")
    stop = text.index("###", start + 5)
    return text[start:stop]


def test_the_checklist_gains_the_census_row_in_step_1_and_two_rows_in_step_2() -> None:
    step_1 = _plain(_checklist_step(1))
    step_2 = _plain(_checklist_step(2))
    assert _plain(_STEP_1_ROW) in step_1
    for row in _STEP_2_ROWS:
        assert _plain(row) in step_2, row[:60]
    assert _plain(_STEP_1_ROW) not in step_2, "the census row is a Step 1 row"
    assert _plain(_STEP_2_ROWS[0]) not in step_1, "the assertion row is a Step 2 row"
    assert "check by check" not in step_2, (
        "the row names a reading that the paragraph it points at does not carry"
    )
    boundaries = _plain(
        (_SKILL / "references" / "claim-boundaries.md").read_text(encoding="utf-8")
    )
    assert "A mutant that survives may be equivalent." in boundaries, (
        "the paragraph the row points at is gone"
    )


def test_the_old_checklist_steps_lack_the_rows() -> None:
    """Fired at the steps as they stood: five and seven rows, none about tests."""
    old_step_1 = "### Step 1: High-Level Conceptual Review\n- [ ] Solution aligns with original requirements\n"
    old_step_2 = "### Step 2: Detailed File-by-File Review\n- [ ] Every function reviewed for correctness\n"
    assert _plain(_STEP_1_ROW) not in _plain(old_step_1)
    assert not any(_plain(row) in _plain(old_step_2) for row in _STEP_2_ROWS)


# ---------------------------------------------------------------------------------------------
# The mutation runner: an unmutated control, the header-only stub, and one mutation per case. Each
# mutation is applied once (its anchor must occur exactly once in the script) to a copy of the
# script, which runs over the planted repository, and the case that names it must report it.
# ---------------------------------------------------------------------------------------------
class _Mutation(NamedTuple):
    name: str
    anchor: str
    replacement: str
    args: tuple[str, ...]
    case: Callable[[list[str], _Facts], list[str]]


_MUTATIONS = (
    _Mutation(
        "tokens are read on the added side",
        "enumerate(hunk.removed)",
        "enumerate(hunk.added)",
        (),
        _case_removed,
    ),
    _Mutation(
        "comment skipping is removed",
        "if not line or line.startswith(_COMMENT_STARTS):",
        "if not line:",
        (),
        _case_controls,
    ),
    _Mutation(
        "the test-path rule matches every path",
        'directory = path.endswith("/")',
        'directory = path.endswith("/")\n    return True',
        (),
        _case_controls,
    ),
    _Mutation(
        "MOVED? is never set",
        "places = [_take(pool, text) for _, text in gone]",
        "places = [None for _, text in gone]",
        (),
        _case_moved,
    ),
    _Mutation(
        "the cap is dropped silently",
        "if len(rows) > len(listed):",
        "if False:",
        _CAP_ARGS,
        _case_cap,
    ),
    _Mutation(
        "deleted files are not listed",
        "rows.append(_deleted_row(path, mine, pool, tokens))",
        "pass",
        (),
        _case_deleted,
    ),
    _Mutation(
        "deleted files are not counted in the census",
        'deleted = sum(1 for path in changed if letters.get(path) == "D")',
        "deleted = 0",
        (),
        _case_census,
    ),
    _Mutation(
        "REMOVED and CHANGED are swapped",
        "elif hunk.added:",
        "elif not hunk.added:",
        (),
        _case_removed,
    ),
)
_STUB_ANCHOR = "_test_changes(report, root, args, tracked, untracked, counts)"


def _copy_with(tmp_path: Path, anchor: str | None, replacement: str) -> Path:
    """The script copied next to the references it reads, with one mutation applied once."""
    source = _SCRIPT.read_text(encoding="utf-8")
    if anchor is not None:
        assert source.count(anchor) == 1, (
            f"anchor {anchor!r} occurs {source.count(anchor)} times"
        )
        mutated = source.replace(anchor, replacement)
        assert mutated != source, "the mutation changed nothing"
    else:
        mutated = source
    (tmp_path / "skill" / "references").mkdir(parents=True)
    (tmp_path / "skill" / "scripts").mkdir(parents=True)
    shutil.copy(_MATRIX, tmp_path / "skill" / "references" / _MATRIX.name)
    target = tmp_path / "skill" / "scripts" / "review_core.py"
    target.write_text(mutated, encoding="utf-8", newline="\n")
    return target


def test_the_unmutated_copy_is_the_control_and_passes_every_case(
    tmp_path: Path, planted: _Facts
) -> None:
    """The control: a copy with no mutation, run the same way, passes every case, so a mutant that
    fails one fails it for its mutation and not for the copy."""
    lines = _section(_run_script(_copy_with(tmp_path, None, ""), planted.repo), 7)
    for name, case in _PLANTED_CASES.items():
        assert case(lines, planted) == [], name
    capped = _section(
        _run_script(_copy_with(tmp_path / "again", None, ""), planted.repo, *_CAP_ARGS),
        7,
    )
    assert _case_cap(capped, planted) == []


def test_the_header_only_stub_fails_every_case(tmp_path: Path, planted: _Facts) -> None:
    """The text the change replaced: a script that opens section 7 and prints nothing. It must fail
    every case, run end to end as a process."""
    stub = _copy_with(tmp_path, _STUB_ANCHOR, "pass")
    lines = _section(_run_script(stub, planted.repo), 7)
    assert lines == [], lines
    for name, case in _PLANTED_CASES.items():
        assert case(lines, planted), f"{name} passed on the stub"


@pytest.mark.parametrize("mutation", _MUTATIONS, ids=[m.name for m in _MUTATIONS])
def test_each_mutation_is_killed_by_the_case_that_names_it(
    mutation: _Mutation, tmp_path: Path, planted: _Facts
) -> None:
    copy = _copy_with(tmp_path, mutation.anchor, mutation.replacement)
    lines = _section(_run_script(copy, planted.repo, *mutation.args), 7)
    problems = mutation.case(lines, planted)
    assert problems, f"the mutant {mutation.name!r} survived {mutation.case.__name__}"


def test_a_missing_marker_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="no marker"):
        _between("text", "absent", "other")
    with pytest.raises(AssertionError, match="exactly once"):
        _line_of("a\nb\n", "c")
