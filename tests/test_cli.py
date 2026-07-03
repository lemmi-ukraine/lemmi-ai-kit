"""CLI surface: exit codes and human-readable output."""

from pathlib import Path

import pytest

from lemmi_ai_kit.cli import main


def test_list_prints_skills(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--all"]) == 0
    out = capsys.readouterr().out
    assert "commit-message" in out
    assert "analyze-logs" in out
    assert "31 skill(s)" in out


def test_list_default_excludes_extras(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "analyze-logs" not in out


def test_install_and_diff_roundtrip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "seeded: " in out

    assert main(["diff", str(tmp_path)]) == 0
    assert "in sync" in capsys.readouterr().out

    (tmp_path / "AGENTS.md").write_text("customized", encoding="utf-8")
    assert main(["diff", str(tmp_path)]) == 1
    assert "modified" in capsys.readouterr().out


def test_install_dry_run_touches_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", str(tmp_path), "--dry-run", "--all"]) == 0
    assert "[dry-run]" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_unknown_profile_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--profile", "bogus"]) == 2
    assert "unknown profile" in capsys.readouterr().out


def test_install_into_missing_dir_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", str(tmp_path / "does-not-exist")]) == 2
    assert "not a directory" in capsys.readouterr().out
