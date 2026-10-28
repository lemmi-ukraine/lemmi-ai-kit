"""Run the test files that ship beside a skill's scripts, which CI never collects.

`pyproject.toml` sets `testpaths = ["tests"]`, so a bare `pytest` -- which is what CI
runs -- collects `tests/` and nothing else. A `test_*.py` that lives next to the script
it tests, inside a skill, is therefore invisible to CI: it can go red and the job stays
green. This module closes that gap without widening `testpaths`: it discovers every such
file and runs each one in a `python -B -m pytest` process of its own.

**One process per file, not a wider `testpaths`.** A skill's test file puts its own
directory on `sys.path` and imports a sibling script by bare name, so collecting two of
them into one process lets their module names collide. A process of its own is also how
a skill documents running its tests. `-B` and `-p no:cacheprovider` keep the run from
writing bytecode or a cache into the plugin payload, which `publish-check` would then
refuse.

**The set is discovered, never listed**, so a skill test added later is covered by
existing. An empty set would make the parametrized test vanish -- pytest skips an empty
parameter set -- so non-emptiness is asserted on its own. The controls show that the
discovery sees a nested file and ignores a non-test one, that the verdict names each way
a run can fail, and that a failing test planted outside the repository turns the run red.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# A skill's tests sit beside its scripts, but nothing requires that depth, hence `**`.
_SKILL_TEST_PATTERN = "plugins/*/skills/**/test_*.py"

# A limit that guards a hang, not speed: a skill's tests run in seconds.
_TIMEOUT_SECONDS = 300
_TAIL_LINES = 40

# `-q` ends a run with a line such as "38 passed in 2.97s". A run that only skipped prints
# no such count, and exits 0 all the same.
_PASSED = re.compile(r"\b[1-9]\d* passed\b")

_PLANTED_FAILURE = """\
def test_planted_failure_for_the_control() -> None:
    assert 1 + 1 == 3, "planted"
"""


@dataclass(frozen=True)
class _Run:
    returncode: int | None  # None: still running when the time limit killed it
    output: str


def _discover(repo_root: Path) -> list[Path]:
    return sorted(repo_root.glob(_SKILL_TEST_PATTERN), key=Path.as_posix)


def _label(test_file: Path) -> str:
    return test_file.relative_to(_REPO_ROOT).as_posix()


def _as_text(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    return raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")


def _tail(output: str) -> str:
    return "\n".join(output.splitlines()[-_TAIL_LINES:])


def _run(test_file: Path, workdir: Path) -> _Run:
    """Run one test file in a cold interpreter of its own, writing only under `workdir`."""
    workdir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        str(test_file),
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp",
        str(workdir / "basetemp"),
    ]
    try:
        done = subprocess.run(
            command,
            cwd=workdir,
            env=env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _Run(None, _as_text(exc.stdout) + _as_text(exc.stderr))
    return _Run(done.returncode, done.stdout + done.stderr)


def _why_not_passing(run: _Run) -> str | None:
    """Why this run does not count as a pass, or None when it does."""
    tail = _tail(run.output)
    if run.returncode is None:
        return f"was still running after {_TIMEOUT_SECONDS} s and was killed:\n{tail}"
    if run.returncode != 0:
        return f"exited {run.returncode}:\n{tail}"
    if not _PASSED.search(run.output):
        return f"exited 0 but no test passed, so nothing was shown to work:\n{tail}"
    return None


_SKILL_TESTS = _discover(_REPO_ROOT)


def test_the_skill_test_set_is_not_empty() -> None:
    """Guard the guard: an empty set would make the parametrized test below vanish."""
    assert _SKILL_TESTS, (
        f"{_SKILL_TEST_PATTERN} matched nothing under {_REPO_ROOT}; pytest skips an "
        "empty parameter set, so the run below would pass without running anything"
    )


@pytest.mark.parametrize("test_file", _SKILL_TESTS, ids=_label)
def test_each_skill_test_file_passes_in_its_own_process(
    test_file: Path, tmp_path: Path
) -> None:
    problem = _why_not_passing(_run(test_file, tmp_path))
    assert problem is None, f"{_label(test_file)} {problem}"


def test_discovery_finds_nested_test_files_and_ignores_everything_else(
    tmp_path: Path,
) -> None:
    wanted = [
        "plugins/a/skills/x/scripts/test_one.py",
        "plugins/b/skills/y/test_two.py",
        "plugins/b/skills/y/references/deep/er/test_three.py",
    ]
    ignored = [
        "plugins/a/skills/x/scripts/helper.py",
        "plugins/a/skills/x/scripts/one_test.py",
        "plugins/a/skills/x/scripts/test_notes.md",
        "plugins/a/elsewhere/test_not_under_skills.py",
        "tests/test_the_wrapper_itself.py",
    ]
    for relative in (*wanted, *ignored):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    expected = sorted((tmp_path / relative for relative in wanted), key=Path.as_posix)
    assert _discover(tmp_path) == expected


def test_the_verdict_names_every_way_a_run_can_fail() -> None:
    assert _why_not_passing(_Run(0, "38 passed in 2.97s")) is None
    assert _why_not_passing(_Run(0, "37 passed, 1 skipped in 2.90s")) is None
    assert _why_not_passing(_Run(0, "10 passed in 0.10s")) is None
    for run in (
        _Run(1, "1 failed, 37 passed in 2.9s"),
        _Run(5, "no tests ran in 0.01s"),
        _Run(None, ""),
        _Run(0, "2 skipped in 0.01s"),
        _Run(0, "0 passed in 0.01s"),
        _Run(0, ""),
    ):
        assert _why_not_passing(run) is not None, run


def test_a_planted_failing_skill_test_turns_the_run_red(tmp_path: Path) -> None:
    """Fire the runner at a known-positive: a failing test planted outside the repository."""
    root = tmp_path / "repo"
    planted = root / "plugins/demo/skills/sample/scripts/test_planted.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(_PLANTED_FAILURE, encoding="utf-8")
    assert _discover(root) == [planted]

    run = _run(planted, tmp_path / "work")

    assert run.returncode is not None and run.returncode != 0, run.output
    assert "test_planted_failure_for_the_control" in run.output, run.output
    assert _why_not_passing(run) is not None
