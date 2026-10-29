"""`probe_checker` reads a checker that prints one number, and runs a checker script with no shell.

Two defects made a sound checker read as broken. A checker that prints a single bare integer (what
`grep -c` prints) was counted as one line of output, so its zero on the negative fixture read as
OVER-MATCHING unless the caller knew to pass `--count-mode grep-c`. And the only way to hand the
probe a checker was `--cmd`, which runs in the platform shell: on Windows that is cmd.exe, where a
single quote is an ordinary character and `|`, `^` and parentheses are syntax, so a check whose
pattern held any of them never started and the probe said UNUSABLE for a checker that works.

Each test runs the script as a process, the way a session does. The checkers are Python files built
under `tmp_path`, so the tests mean the same thing on every OS. The signature test pins the names
that other repositories load this file by.
"""

import importlib.util
import inspect
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
    / "scripts"
    / "probe_checker.py"
)

# A needle the platform shell would mangle: a quote, a caret, parentheses and a pipe.
_NEEDLE = "'^(L[12]|x) NEEDLE"


def _run(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-B", str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def _fixtures(tmp_path: Path) -> tuple[Path, Path]:
    positive = tmp_path / "positive.txt"
    negative = tmp_path / "negative.txt"
    positive.write_text(f"alpha\n{_NEEDLE}\nomega\n", encoding="utf-8")
    negative.write_text("alpha\nomega\n", encoding="utf-8")
    return positive, negative


def _checker(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(
        "import sys\ntext = open(sys.argv[1], encoding='utf-8').read()\n" + body,
        encoding="utf-8",
    )
    return path


def _counts_the_needle(tmp_path: Path) -> Path:
    """Prints one bare integer: how many lines hold the needle."""
    body = f"print(sum(1 for line in text.splitlines() if {_NEEDLE!r} in line))\n"
    return _checker(tmp_path, "count.py", body)


def _always_zero(tmp_path: Path) -> Path:
    return _checker(tmp_path, "blind.py", "print(0)\n")


def _shell_command(script: Path) -> str:
    """A `--cmd` string that quotes with double quotes, the one form cmd.exe and sh both read."""
    return f'"{sys.executable}" "{script}" "{{file}}"'


def test_a_checker_that_prints_one_bare_integer_reads_can_see_without_count_mode(
    tmp_path: Path,
) -> None:
    positive, negative = _fixtures(tmp_path)
    result = _run(
        "--cmd",
        _shell_command(_counts_the_needle(tmp_path)),
        "--positive",
        str(positive),
        "--negative",
        str(negative),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "verdict=CAN-SEE" in result.stdout


def test_a_bare_integer_checker_that_never_matches_is_still_reported_blind(
    tmp_path: Path,
) -> None:
    positive, negative = _fixtures(tmp_path)
    result = _run(
        "--cmd",
        _shell_command(_always_zero(tmp_path)),
        "--positive",
        str(positive),
        "--negative",
        str(negative),
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BLIND" in result.stdout


def test_script_runs_a_checker_whose_pattern_the_platform_shell_would_mangle(
    tmp_path: Path,
) -> None:
    positive, negative = _fixtures(tmp_path)
    result = _run(
        "--script",
        str(_counts_the_needle(tmp_path)),
        "--positive",
        str(positive),
        "--negative",
        str(negative),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "verdict=CAN-SEE" in result.stdout


def test_script_and_cmd_cannot_be_given_together(tmp_path: Path) -> None:
    positive, negative = _fixtures(tmp_path)
    script = _counts_the_needle(tmp_path)
    result = _run(
        "--script",
        str(script),
        "--cmd",
        _shell_command(script),
        "--positive",
        str(positive),
        "--negative",
        str(negative),
    )
    assert result.returncode == 2
    assert "not allowed with" in result.stderr


def test_a_script_that_cannot_start_is_an_invocation_error_not_a_blind_verdict(
    tmp_path: Path,
) -> None:
    positive, negative = _fixtures(tmp_path)
    result = _run(
        "--script",
        str(tmp_path / "missing.py"),
        "--positive",
        str(positive),
        "--negative",
        str(negative),
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "invocation error" in result.stderr
    assert "INVOCATION failure" in result.stderr


def test_a_command_that_cannot_start_names_the_platform_shell_and_points_at_script(
    tmp_path: Path,
) -> None:
    positive, negative = _fixtures(tmp_path)
    result = _run(
        "--cmd",
        _shell_command(tmp_path / "missing.py"),
        "--positive",
        str(positive),
        "--negative",
        str(negative),
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "platform shell" in result.stderr
    assert "--script" in result.stderr


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("probe_checker_under_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_names_other_repositories_load_this_file_by_keep_their_signatures() -> None:
    module = _load()
    count_matches = cast(Callable[..., int], module.count_matches)
    assert list(inspect.signature(count_matches).parameters)[:3] == [
        "cmd",
        "fixture",
        "count_mode",
    ]
    assert callable(module.main)
    assert issubclass(cast(type, module.ProbeError), RuntimeError)
    assert isinstance(module.STAMP, str)


def test_the_file_keeps_exactly_one_shell_call() -> None:
    """The content-safety pin allows this file one shell site and cannot count a second."""
    source = _SCRIPT.read_text(encoding="utf-8")
    assert len(re.findall(r"shell\s*=\s*True\s*,", source)) == 1
