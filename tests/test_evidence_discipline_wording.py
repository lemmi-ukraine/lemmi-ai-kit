"""The checks of the evidence discipline wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_lint_passes_over_zero_files`: The reference says the hand-off lint prints PASSED over zero files; this is that, measured.
* `test_the_summary_line_counts_the_files_it_linted`: Control for the test above: with one note in the folder M is 1 whatever the findings are, so M is the number the reference tells the reader to compare with the files meant.
"""

import re
from pathlib import Path

import pytest

from lemmi_ai_kit.cli import main

_SUMMARY = re.compile(r"^--- handoffs: (\d+) finding\(s\), (\d+) file\(s\) ---$")


def _summary(lines: list[str]) -> tuple[str, ...]:
    """The two numbers of the one summary line, wherever it falls among the finding lines."""
    found = [match for line in lines if (match := _SUMMARY.match(line))]
    assert len(found) == 1, lines
    return found[0].groups()


def _lint_handoffs(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, list[str]]:
    code = main(["lint", "handoffs", "--project", str(project)])
    return code, capsys.readouterr().out.splitlines()


def test_the_lint_passes_over_zero_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The reference says the hand-off lint prints PASSED over zero files; this is that, measured."""
    code, lines = _lint_handoffs(tmp_path, capsys)
    assert code == 0, lines
    assert _summary(lines) == ("0", "0"), lines
    assert lines[-1].startswith("LINT PASSED"), lines


def test_the_summary_line_counts_the_files_it_linted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Control for the test above: with one note in the folder M is 1 whatever the findings
    are, so M is the number the reference tells the reader to compare with the files meant."""
    folder = tmp_path / ".ai" / "handoffs"
    folder.mkdir(parents=True)
    (folder / "2026-01-01-example-return.md").write_text(
        "# a note that holds no contract line\n", encoding="utf-8"
    )
    _, lines = _lint_handoffs(tmp_path, capsys)
    assert _summary(lines)[1] == "1", lines
