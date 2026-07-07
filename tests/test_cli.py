"""CLI surface: exit codes and human-readable output."""

from pathlib import Path

import pytest

from lemmi_ai_kit.cli import main


def test_list_prints_full_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "commit-message" in out
    assert "analyze-logs" in out
    assert "kit-setup" in out
    assert "33 skill(s)" in out


def test_scaffold_and_rerun_roundtrip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scaffold", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "seeded: " in out
    assert (tmp_path / "AGENTS.md").is_file()
    assert not (tmp_path / ".claude").exists()

    # a second run is a no-op, not an error
    assert main(["scaffold", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "seeded: 0" in out


def test_scaffold_rejects_missing_target(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["scaffold", "/nonexistent/definitely-not-here"]) == 2
    assert "not a directory" in capsys.readouterr().out
