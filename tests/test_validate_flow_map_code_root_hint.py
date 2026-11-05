"""validate_flow_map.py says once, on stderr, why a file citation may be a false finding.

Run without `--code-root`, the validator takes the project root as the code root. That widens the
pattern that picks file references out of a document to a path under any directory, so a task file
cited in an evidence cell needs a Coverage row: a clean document reports a finding that reads like
a mistake in the document and is a consequence of the missing flag. The run now prints one `hint:`
line on stderr when the flag was omitted and the run fails with findings. The exit code and stdout
are what they were (a probe that counts stdout lines reads the same count), and a run that was
given the flag, or that is clean, prints nothing on stderr.

What each test asserts, on an installed copy of the skill and a copy of its probe project, both in
`tmp_path`:

* `test_the_hint_follows_the_flag_and_the_exit_status` runs the four quadrants of flag given or
  omitted and run clean or failing. Only the omitted-and-failing one prints the hint; the other
  three, in particular the given-and-failing one, print nothing on stderr.
* `test_the_hint_leaves_stdout_and_the_exit_code_as_they_were` reads the failing run's stdout: the
  finding and nothing else, with the hint text on stderr only.
* `test_a_selection_that_prints_nothing_gets_no_hint` runs a document that fails, with a check
  selected that has no finding: the run prints nothing and exits 0, and has nothing to explain.
* `test_a_planted_copy_of_the_validator_is_caught` fires the oracle at three copies of the script,
  one with the hint line deleted, one that ignores the flag and one that prints the hint on stdout,
  so the silence of the oracle on the real script means something.

THE SURFACE, in numbers the tests assert: 1 script, 3 documents (the conformant one and two edited
copies of it), 4 quadrants run once each, 1 run with a check selected, 3 planted copies.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import load_manifest, skill_dir

_CALL_TIMEOUT_SECONDS = 45
_SCRIPT = "scripts/validate_flow_map.py"
_PLANTED_SCRIPT = "scripts/validate_flow_map_planted.py"

# The probe project's conformant document, and two edited copies of it. The citing copy also cites a
# task file in an evidence cell: no file reference with `--code-root src`, a file that needs a
# Coverage row without it. The broken copy cites a method that does not exist: it fails either way.
_CONFORMANT = "scripts/fixtures/flow_map/conformant.md"
_CITING = "scripts/fixtures/flow_map/cites-a-task-file.md"
_BROKEN = "scripts/fixtures/flow_map/cites-a-missing-method.md"
_TASK_FILE = "tasks/BUG-register-flow-related.md"
_EVIDENCE = "`code: src/policy.py resets state when eligibility fails`"
_EVIDENCE_WITH_TASK_FILE = (
    f"`code: src/policy.py resets state when eligibility fails; see {_TASK_FILE}`"
)
_METHOD = "IdlePolicy.evaluate"
_MISSING_METHOD = "IdlePolicy.nonexistent"

# What the hint must say, lower-cased and whitespace collapsed: what happened, what it costs, and
# what to do. The wording around these phrases is free.
_HINT_PHRASES = (
    "hint: --code-root was not given",
    "the project root is the code root",
    "needs a coverage row",
    "pass --code-root <dir>",
)

# The two statements of the shipped script the planted copies replace.
_PRINT = "print(CODE_ROOT_HINT, file=sys.stderr)"
_GUARD = "if failed and not code_root_given:"


@pytest.fixture
def installation(tmp_path: Path) -> tuple[Path, Path]:
    entry = next(s for s in load_manifest().skills if s.name == "flow-mapping")
    installed = tmp_path / "plugin cache/core/skills/flow-mapping"
    shutil.copytree(skill_dir(entry), installed)
    project = tmp_path / "separate consumer"
    shutil.copytree(installed / "assets/probe-project", project)
    _write_documents(project)
    return installed, project


def _write_documents(project: Path) -> None:
    text = (project / _CONFORMANT).read_text(encoding="utf-8")
    assert text.count(_EVIDENCE) == 1, (
        "the citing copy needs one evidence cell to extend"
    )
    assert text.count(_METHOD) > 0, "the broken copy needs the method it breaks"
    assert (project / _TASK_FILE).is_file(), f"the probe project has no {_TASK_FILE}"
    (project / _CITING).write_text(
        text.replace(_EVIDENCE, _EVIDENCE_WITH_TASK_FILE), encoding="utf-8"
    )
    (project / _BROKEN).write_text(
        text.replace(_METHOD, _MISSING_METHOD), encoding="utf-8"
    )


def _validate(
    installed: Path,
    project: Path,
    document: str,
    *,
    flag_given: bool,
    script: str = _SCRIPT,
    selected: str | None = None,
) -> subprocess.CompletedProcess[str]:
    args = ["--project-root", str(project)]
    if flag_given:
        args += ["--code-root", "src"]
    if selected is not None:
        args += ["--check", selected]
    return subprocess.run(
        [sys.executable, "-B", str(installed / script), *args, document],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=_CALL_TIMEOUT_SECONDS,
    )


def _folded(text: str) -> str:
    return " ".join(text.split()).lower()


def _says_the_hint(text: str) -> bool:
    return all(phrase in _folded(text) for phrase in _HINT_PHRASES)


def problems(result: subprocess.CompletedProcess[str], *, hint: bool) -> list[str]:
    """What is wrong with the two streams of a run: empty when stderr is exactly the one hint
    line (`hint`) or empty (not `hint`) and stdout does not say the hint."""
    found: list[str] = []
    lines = result.stderr.splitlines()
    if hint and not (
        len(lines) == 1 and lines[0].startswith("hint:") and _says_the_hint(lines[0])
    ):
        found.append(f"stderr is not exactly the one hint line: {result.stderr!r}")
    if not hint and lines:
        found.append(f"stderr is not empty: {result.stderr!r}")
    if _says_the_hint(result.stdout):
        found.append("the hint is on stdout")
    return found


_QUADRANTS = (
    pytest.param(False, _CITING, 1, True, id="omitted-and-the-run-fails"),
    pytest.param(True, _CITING, 0, False, id="given-and-the-document-is-clean"),
    pytest.param(False, _CONFORMANT, 0, False, id="omitted-and-the-document-is-clean"),
    pytest.param(True, _BROKEN, 1, False, id="given-and-the-run-fails"),
)


@pytest.mark.parametrize(("flag_given", "document", "exit_code", "hint"), _QUADRANTS)
def test_the_hint_follows_the_flag_and_the_exit_status(
    installation: tuple[Path, Path],
    flag_given: bool,
    document: str,
    exit_code: int,
    hint: bool,
) -> None:
    installed, project = installation
    result = _validate(installed, project, document, flag_given=flag_given)
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert bool(result.stdout) == (exit_code == 1), result.stdout
    assert problems(result, hint=hint) == [], result.stderr


def test_the_hint_leaves_stdout_and_the_exit_code_as_they_were(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    result = _validate(installed, project, _CITING, flag_given=False)
    assert result.returncode == 1, result.stdout + result.stderr
    finding = result.stdout.splitlines()
    assert len(finding) == 1, result.stdout
    assert finding[0].startswith("[symbols] ") and _TASK_FILE in finding[0], finding
    assert "missing from Coverage" in finding[0], finding
    assert not _says_the_hint(result.stdout)
    assert _says_the_hint(result.stderr)


def test_a_selection_that_prints_nothing_gets_no_hint(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    unselected = _validate(installed, project, _CITING, flag_given=False)
    assert unselected.returncode == 1, (
        "the document must fail when no check is selected"
    )
    selected = _validate(installed, project, _CITING, flag_given=False, selected="tone")
    assert (selected.returncode, selected.stdout, selected.stderr) == (0, "", "")


_PLANTED = (
    pytest.param(
        _PRINT,
        "pass",
        False,
        _CITING,
        True,
        "stderr is not exactly the one hint line",
        id="the-hint-line-is-deleted",
    ),
    pytest.param(
        _GUARD,
        "if failed:",
        True,
        _BROKEN,
        False,
        "stderr is not empty",
        id="the-hint-ignores-the-flag",
    ),
    pytest.param(
        _PRINT,
        "print(CODE_ROOT_HINT)",
        False,
        _CITING,
        True,
        "the hint is on stdout",
        id="the-hint-goes-to-stdout",
    ),
)


@pytest.mark.parametrize(
    ("old", "new", "flag_given", "document", "hint", "named"), _PLANTED
)
def test_a_planted_copy_of_the_validator_is_caught(
    installation: tuple[Path, Path],
    old: str,
    new: str,
    flag_given: bool,
    document: str,
    hint: bool,
    named: str,
) -> None:
    installed, project = installation
    source = (installed / _SCRIPT).read_text(encoding="utf-8")
    assert source.count(old) == 1, f"the planted edit needs one {old!r} in {_SCRIPT}"
    (installed / _PLANTED_SCRIPT).write_text(source.replace(old, new), encoding="utf-8")
    result = _validate(
        installed, project, document, flag_given=flag_given, script=_PLANTED_SCRIPT
    )
    assert result.returncode == 1 and result.stdout, "the copy must still run and fail"
    found = problems(result, hint=hint)
    assert any(named in problem for problem in found), found


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_QUADRANTS) == 4, f"{len(_QUADRANTS)} quadrants, not the 4 stated"
    assert len(_PLANTED) == 3, f"{len(_PLANTED)} planted copies, not the 3 stated"
    assert len({_CONFORMANT, _CITING, _BROKEN}) == 3
