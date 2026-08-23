"""CLI surface: exit codes and human-readable output."""

from pathlib import Path

import pytest

from lemmi_ai_kit import cli
from lemmi_ai_kit.cli import main
from lemmi_ai_kit.manifest import load_manifest


def test_list_prints_full_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "commit-message" in out
    assert "analyze-logs" in out
    assert "kit-setup" in out
    # Derived, not literal: the CLI's own count must agree with the manifest it renders.
    expected = len(load_manifest().skills)
    assert f"{expected} skill(s)" in out


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


# --- audit-skills: the gate must never pass by scanning nothing --------------------
#
# This repo has no `.claude/skills/`, so `audit-skills --fail-on major` used to print
# "nothing to audit" and exit 0 -- a gate that cannot fail, which is worse than no gate
# because it gets trusted. The three tests below pin both directions of the fallback.

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NOTHING_TO_AUDIT = "nothing to audit"


def test_audit_skills_falls_back_to_the_bundled_fleet(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no .claude/skills/, auditing this repo must still scan the shipped fleet."""
    exit_code = main(["audit-skills", "--project", str(_REPO_ROOT)])
    out = capsys.readouterr().out

    assert _NOTHING_TO_AUDIT not in out, (
        "the audit scanned nothing, so --fail-on cannot fail:\n" + out
    )
    # Derived, not literal: adding or dropping a skill must not need an edit here.
    manifest = load_manifest()
    for pack in ("core", "python"):
        expected = sum(1 for entry in manifest.skills if entry.pack == pack)
        assert f"{expected} skills;" in out
    assert exit_code == 0


def test_audit_skills_does_not_hijack_an_adopter_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An adopter with only plugin skills keeps the note -- we must not audit OUR fleet."""
    exit_code = main(["audit-skills", "--project", str(tmp_path)])
    out = capsys.readouterr().out

    assert _NOTHING_TO_AUDIT in out
    # The fleet's own INFO line would appear if we had silently changed target.
    assert "skills; description+when_to_use" not in out
    assert exit_code == 0


def test_audit_skills_without_the_fallback_would_scan_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The regression this guards: disable the fallback and the gate goes vacuous again."""

    def no_bundled_tree(_root: Path) -> tuple[Path, ...]:
        return ()

    monkeypatch.setattr(cli, "_bundled_skills_dirs", no_bundled_tree)

    exit_code = main(
        ["audit-skills", "--project", str(_REPO_ROOT), "--fail-on", "major"]
    )
    out = capsys.readouterr().out

    assert _NOTHING_TO_AUDIT in out
    assert exit_code == 0, "a vacuous scan exits 0 -- which is exactly the defect"
