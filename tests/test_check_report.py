"""`check_report.py --proposals-only`: a retrospective that registered P1/P2 and applied none.

The durability check asserts two things about a retrospective's Phase 7 output: the date's
changelog entry is reachable from HEAD, and a companion hypothesis exists for the same date,
"for the P1/P2 changes applied". A project that keeps P1/P2 as proposals applies none, so it
has no prediction to make, and the default gate made it write a baseline hypothesis anyway.

`--proposals-only` drops that one requirement and nothing else. The changelog entry is the only
durable record of the proposals a later consolidation will read, so it is still required and
still has to be reachable from HEAD; a flag that skipped the whole check would leave a
proposals-only run with no durable record and a clean exit. The tests fire the flag at each
state that must still be refused, and at the default, which must not change.

Every repository is built under `tmp_path` with a local identity and signing off, so the
tests touch no configuration of the machine they run on.
"""

import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Literal

import pytest
from test_printed_commands import (
    _printed_elements,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _REPO_ROOT / "plugins" / "core" / "skills" / "session-retrospective"
_SCRIPT = _SKILL / "scripts" / "check_report.py"
_COMPLETE_REPORT = _SKILL / "scripts" / "fixtures" / "report_complete.md"
_DATE = "2031-02-20"

_Entry = Literal["committed", "disk-only", "none"]


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _entry(heading: str) -> str:
    return f"{heading}\n\n### [SKILL-MODIFIED] a retrospective's proposals\n"


def _repo(tmp_path: Path, *, entry: _Entry, hypothesis: bool) -> Path:
    """A repository whose HEAD holds (or lacks) the date's changelog entry and hypothesis.

    `disk-only` commits a changelog without the entry and then appends it, so the entry is
    on disk and not reachable from HEAD.
    """
    root = tmp_path / "repo"
    ledger = root / ".ai"
    ledger.mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    heading = f"## {_DATE}"
    changelog = ledger / "ai-changelog.md"
    changelog.write_text(
        "# AI changelog\n\n" + (_entry(heading) if entry == "committed" else ""),
        encoding="utf-8",
        newline="\n",
    )
    (ledger / "improvement-hypotheses.md").write_text(
        "# Improvement hypotheses\n\n" + (_entry(heading) if hypothesis else ""),
        encoding="utf-8",
        newline="\n",
    )
    _git(root, "add", "--", ".ai")
    _git(root, "commit", "-q", "-m", "baseline", "--", ".ai")
    if entry == "disk-only":
        with changelog.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_entry(heading))
    reports = ledger / "retrospectives"
    reports.mkdir()
    (reports / f"{_DATE}-retrospective.md").write_text(
        _COMPLETE_REPORT.read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
    )
    return root


def _run(root: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    report = root / ".ai" / "retrospectives" / f"{_DATE}-retrospective.md"
    return subprocess.run(
        [sys.executable, "-B", str(_SCRIPT), "--report", str(report), *flags],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )


_NO_HYPOTHESIS = f"NO hypothesis dated {_DATE}"
_NO_ENTRY = f"NO entry dated {_DATE}"
_NOT_REACHABLE = "NOT reachable from HEAD"
_SKIP_NOTICE = "proposals only: no companion hypothesis required"


@pytest.mark.parametrize("check", ["durability", "all"])
def test_a_proposals_only_run_with_a_committed_entry_and_no_hypothesis_passes(
    check: str, tmp_path: Path
) -> None:
    root = _repo(tmp_path, entry="committed", hypothesis=False)
    done = _run(root, "--check", check, "--proposals-only")
    assert (done.returncode, done.stdout) == (0, ""), (done.stdout, done.stderr)
    assert "0 finding(s)" in done.stderr


@pytest.mark.parametrize("check", ["durability", "all"])
def test_without_the_flag_the_missing_hypothesis_is_still_a_finding(
    check: str, tmp_path: Path
) -> None:
    """The default is unchanged: same repository as the passing run, no flag."""
    root = _repo(tmp_path, entry="committed", hypothesis=False)
    done = _run(root, "--check", check)
    assert done.returncode == 1, (done.stdout, done.stderr)
    assert _NO_HYPOTHESIS in done.stdout
    assert _SKIP_NOTICE not in done.stderr


@pytest.mark.parametrize("check", ["durability", "all"])
def test_the_flag_still_requires_the_changelog_entry(
    check: str, tmp_path: Path
) -> None:
    root = _repo(tmp_path, entry="none", hypothesis=False)
    done = _run(root, "--check", check, "--proposals-only")
    assert done.returncode == 1, (done.stdout, done.stderr)
    assert _NO_ENTRY in done.stdout
    assert _NO_HYPOTHESIS not in done.stdout, (
        "the flag drops the hypothesis finding only"
    )


@pytest.mark.parametrize("check", ["durability", "all"])
def test_the_flag_still_requires_the_entry_to_be_reachable_from_head(
    check: str, tmp_path: Path
) -> None:
    """An entry written and never committed is the only durable record, and it is not one."""
    root = _repo(tmp_path, entry="disk-only", hypothesis=False)
    done = _run(root, "--check", check, "--proposals-only")
    assert done.returncode == 1, (done.stdout, done.stderr)
    assert _NOT_REACHABLE in done.stdout
    assert _NO_ENTRY not in done.stdout, "the entry is on disk; only HEAD lacks it"
    assert _NO_HYPOTHESIS not in done.stdout


@pytest.mark.parametrize("flags", [[], ["--proposals-only"]], ids=["default", "flag"])
def test_a_hypothesis_that_exists_is_never_a_finding(
    flags: list[str], tmp_path: Path
) -> None:
    root = _repo(tmp_path, entry="committed", hypothesis=True)
    done = _run(root, "--check", "durability", *flags)
    assert (done.returncode, done.stdout) == (0, ""), (done.stdout, done.stderr)


def test_the_summary_says_when_the_hypothesis_was_not_required(
    tmp_path: Path,
) -> None:
    """A skipped requirement is never silent, and never claimed when nothing was skipped."""
    root = _repo(tmp_path, entry="committed", hypothesis=False)
    for check in ("durability", "all"):
        assert _SKIP_NOTICE in _run(root, "--check", check, "--proposals-only").stderr
        assert _SKIP_NOTICE not in _run(root, "--check", check).stderr
    sections = _run(root, "--check", "sections", "--proposals-only")
    assert sections.returncode == 0, (sections.stdout, sections.stderr)
    assert _SKIP_NOTICE not in sections.stderr, "the sections check skipped nothing"


def _help_text() -> str:
    """The script's own `--help` output, which argparse writes from its docstring and options."""
    done = subprocess.run(
        [sys.executable, "-B", str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def _usage_options() -> set[str]:
    """The options the script's own `--help` lists in its usage line, written by argparse."""
    usage = _help_text().split("\n\n", 1)[0]
    assert usage.startswith("usage:"), usage
    return set(re.findall(r"--[a-z][a-z-]*", usage))


def _options_after_the_gate(command: str) -> set[str]:
    """The options that follow `check_report.py` as the program of a printed command.

    A command that merely carries the gate's text inside a quoted argument (the probe line
    passes it to `probe_checker.py` in `--cmd '...'`) has no such word, and the options after
    it are the probe's own.
    """
    try:
        words = shlex.split(command)
    except ValueError:
        return set()
    for index, word in enumerate(words):
        if word.endswith("check_report.py"):
            return set(re.findall(r"--[a-z][a-z-]*", " ".join(words[index + 1 :])))
    return set()


def _options_printed_beside_the_gate(relative: str) -> set[str]:
    """Every `--option` a code span or fenced line passes to `check_report.py`."""
    text = (_SKILL / relative).read_text(encoding="utf-8")
    return {
        option
        for element in _printed_elements(text)
        for option in _options_after_the_gate(element.text)
    }


def test_the_option_reader_takes_the_gates_options_and_not_the_probes() -> None:
    """Planted: the probe line carries the gate in a quoted argument, and its own options."""
    probe = (
        "python x/probe_checker.py --cmd 'python y/check_report.py --check sections "
        "--report {file}' --positive a.md --negative b.md"
    )
    assert _options_after_the_gate(probe) == set()
    gate = 'python "x/check_report.py" --report r.md [--check sections|workers|all]'
    assert _options_after_the_gate(gate) == {"--report", "--check"}
    short = "check_report.py --check durability --proposals-only"
    assert _options_after_the_gate(short) == {"--check", "--proposals-only"}
    assert _options_after_the_gate("python run.py --proposals-only") == set()


def test_every_option_the_skill_prints_for_the_gate_is_one_it_takes() -> None:
    """The text and the script cannot disagree about a flag in either direction."""
    takes = _usage_options()
    assert {"--report", "--check", "--date", "--proposals-only"} <= takes, takes
    printed = _options_printed_beside_the_gate(
        "SKILL.md"
    ) | _options_printed_beside_the_gate("references/report-gate.md")
    assert printed, "the scan read no option out of the text that prints the gate"
    assert "--proposals-only" in printed, (
        "no printed gate command carries --proposals-only, so a proposals-only run is "
        "never told the flag exists"
    )
    unknown = sorted(printed - takes)
    assert not unknown, f"the text prints options the script does not take: {unknown}"


# --- `--help` says the entry is still required --------------------------------------------------
#
# The flag drops one requirement, and a reader meets it in `--help` before any skill text: the
# script's docstring is the description and the option has a help line of its own. Both must say
# the changelog entry stays required, or a reader is told the flag skips the whole check.

_OPTIONS_HEADING = re.compile(r"^(?:options|optional arguments):$", re.MULTILINE)


def _help_parts(text: str) -> tuple[str, str]:
    """The description and the option list of an argparse help text, each with its whitespace
    collapsed, because argparse wraps the option help at the width of the terminal."""
    parts = _OPTIONS_HEADING.split(text, maxsplit=1)
    assert len(parts) == 2, f"the help text has no options heading\n{text}"
    return " ".join(parts[0].split()), " ".join(parts[1].split())


def _flag_help(options: str) -> str:
    """The help of `--proposals-only` alone: from its name to the next option, if any."""
    _, found, tail = options.partition("--proposals-only")
    return re.split(r"\s--[a-z]", tail, maxsplit=1)[0] if found else ""


def _help_gaps(description: str, options: str) -> list[str]:
    """What `--help` must say about the flag; each name is a fact it does not state."""
    flag = _flag_help(options)
    stated = {
        "the description says the changelog entry is STILL required": (
            "STILL required" in description
        ),
        "the description says the entry must be reachable from HEAD": (
            "reachable from HEAD" in description
        ),
        "the option's help says the entry is still required": "still required" in flag,
        "the option's help says the entry must be reachable from HEAD": (
            "reachable from HEAD" in flag
        ),
    }
    return [name for name, ok in stated.items() if not ok]


def test_the_help_says_the_flag_leaves_the_changelog_entry_required() -> None:
    description, options = _help_parts(_help_text())
    assert _help_gaps(description, options) == []


def test_the_help_check_fails_on_the_wording_it_guards() -> None:
    """Planted: the real help text with one claim reversed at a time, each in the part of the
    help that carries it. Each plant must produce exactly the gap it targets."""
    description, options = _help_parts(_help_text())
    assert _flag_help(options), "the option list holds no --proposals-only entry"
    plants = {
        "the description says the changelog entry is STILL required": (
            True,
            "STILL required",
            "NOT required",
        ),
        "the description says the entry must be reachable from HEAD": (
            True,
            "reachable from HEAD",
            "present on disk",
        ),
        "the option's help says the entry is still required": (
            False,
            "still required",
            "not required",
        ),
        "the option's help says the entry must be reachable from HEAD": (
            False,
            "reachable from HEAD",
            "present on disk",
        ),
    }
    for expected, (in_description, before, after) in plants.items():
        assert before in (description if in_description else _flag_help(options)), (
            f"the {'description' if in_description else 'option help'} no longer holds "
            f"{before!r}"
        )
        planted = (
            (description.replace(before, after, 1), options)
            if in_description
            else (description, options.replace(before, after, 1))
        )
        assert _help_gaps(*planted) == [expected], expected
