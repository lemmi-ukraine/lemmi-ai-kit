"""Exercise installed flow tools against independent consumer projects."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import load_manifest, skill_dir


@pytest.fixture
def installation(tmp_path: Path) -> tuple[Path, Path]:
    entry = next(s for s in load_manifest().skills if s.name == "flow-mapping")
    source = skill_dir(entry)
    installed = tmp_path / "plugin cache/core/skills/flow-mapping"
    shutil.copytree(source, installed)
    checker = source.parent / "post-task-review/scripts/probe_checker.py"
    destination = installed.parent / "post-task-review/scripts/probe_checker.py"
    destination.parent.mkdir(parents=True)
    shutil.copy2(checker, destination)
    project = tmp_path / "separate consumer"
    shutil.copytree(installed / "assets/probe-project", project)
    return installed, project


def run(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=cwd,
        env={
            key: value
            for key, value in os.environ.items()
            if key != "PYTHONDONTWRITEBYTECODE"
        },
        capture_output=True,
        text=True,
        timeout=45,
    )


def hashes(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("tool", ["validate_flow_map", "validate_register"])
def test_installed_probe_pairs_need_no_source_repository(
    installation: tuple[Path, Path], tool: str
) -> None:
    installed, project = installation
    before = hashes(installed.parent)
    result = run(installed / f"scripts/{tool}.py", project, "--probe-stamps")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "exact probe pairs)" in result.stdout
    assert "verdict=CAN-SEE" in result.stdout
    assert hashes(installed.parent) == before


@pytest.mark.parametrize("source_root", ["src", "lib"])
def test_consumer_resolution_corrupt_and_missing_inputs(
    installation: tuple[Path, Path],
    source_root: str,
) -> None:
    installed, project = installation
    tool = installed / "scripts/validate_flow_map.py"
    if source_root != "src":
        (project / "src").rename(project / source_root)
        for path in (project / "scripts/fixtures").rglob("*.md"):
            path.write_text(path.read_text().replace("src/", f"{source_root}/"))
    nested = project / "nested"
    nested.mkdir()
    fixture = "scripts/fixtures/flow_map/conformant.md"
    args = ("--project-root", str(project), "--code-root", source_root, fixture)
    valid = run(tool, nested, *args)
    assert (valid.returncode, valid.stdout) == (0, ""), valid.stderr
    doc = project / fixture
    text = doc.read_text()
    assert "IdlePolicy.evaluate" in text
    doc.write_text(text.replace("IdlePolicy.evaluate", "IdlePolicy.nonexistent"))
    invalid = run(tool, nested, *args)
    assert invalid.returncode == 1 and "does not resolve" in invalid.stdout
    doc.unlink()
    missing = run(tool, nested, *args)
    assert missing.returncode == 2 and "not found" in missing.stderr
    absent = run(tool, nested, "--project-root", str(project / "missing"), fixture)
    assert absent.returncode == 2 and "project root not found" in absent.stderr


def test_projection_certification_and_authorship_refusal(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/generate_flow_projections.py"
    prefix = ("--project-root", str(project), "--code-root", "src")
    good = run(
        tool,
        project,
        *prefix,
        "scripts/fixtures/flow_projection/conformant.md",
        "--certify",
    )
    assert good.returncode == 0, good.stdout + good.stderr
    bad = run(
        tool,
        project,
        *prefix,
        "scripts/fixtures/flow_projection/wrong-row.md",
        "--certify",
    )
    assert bad.returncode == 1, bad.stdout + bad.stderr
    unread = run(
        tool, project, *prefix, "scripts/fixtures/flow_projection/unread-file.md"
    )
    assert unread.returncode == 2, unread.stdout + unread.stderr


def test_seam_candidates_and_unreadable_corpus(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/find_absent_cross_flow_seams.py"
    result = run(
        tool,
        project,
        "--project-root",
        str(project),
        "--root",
        "scripts/fixtures/flow_map/seam_probe",
        "--list-residue",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = [line for line in result.stdout.splitlines() if line.startswith("RESIDUE  ")]
    assert any("ProbeAbsentSeam.sweep_only" in line for line in rows)
    assert not any("ProbeNamedInProse.cell_names_me" in line for line in rows)
    bad = run(tool, project, "--root", str(project / "missing"))
    assert bad.returncode != 0


def test_comment_checker_detects_executable_change_and_missing_file(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/verify_no_code_change.py"
    module = project / "mod.py"
    original = '"""Module docs."""\n\ndef f():\n    """Function docs."""\n    "original".upper()\n    return 1\n'
    module.write_text(original)
    for args in (
        ["init", "-q"],
        ["add", "--", "mod.py"],
        [
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Fixture",
        ],
    ):
        subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
    module.write_text(original.replace("Function docs.", "New documentation."))
    assert run(tool, project, "HEAD", "mod.py").returncode == 0
    module.write_text(original.replace("return 1", "return 2"))
    changed = run(tool, project, "HEAD", "mod.py")
    assert changed.returncode == 1 and "CODE-CHANGED" in changed.stdout
    module.write_text(original.replace('"original"', '"different"'))
    expression = run(tool, project, "HEAD", "mod.py")
    assert expression.returncode == 1 and "CODE-CHANGED" in expression.stdout
    missing = run(tool, project, "HEAD", "absent.py")
    assert missing.returncode == 1 and "MISSING-AT-REF" in missing.stdout


def test_register_join_refuses_missing_population(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/validate_register.py"
    result = run(
        tool, project, "--project-root", str(project), "--join", "absent", "tasks"
    )
    assert result.returncode == 2 and "missing or empty" in result.stderr
