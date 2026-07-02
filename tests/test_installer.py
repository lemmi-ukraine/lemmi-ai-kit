"""Installer behavior: placement, idempotency, force/reseed semantics, diff."""

from pathlib import Path

import pytest

from lemmi_ai_kit import installer
from lemmi_ai_kit.manifest import DEFAULT_PROFILES, PROFILES, Manifest, load_manifest


@pytest.fixture(scope="module")
def manifest() -> Manifest:
    return load_manifest()


def test_install_default_profiles(tmp_path: Path, manifest: Manifest) -> None:
    report = installer.install(tmp_path, manifest, DEFAULT_PROFILES)

    assert (tmp_path / ".claude/skills/task-learnings/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/lemmi-python-conventions/SKILL.md").is_file()
    assert (tmp_path / ".ai/learnings.md").is_file()
    assert (tmp_path / ".ai/templates/requirements.md").is_file()
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()
    # extras are opt-in
    assert not (tmp_path / ".claude/skills/analyze-logs").exists()
    assert not (tmp_path / ".claude/skills/openai-realtime-quirks").exists()

    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "`/commit-message`" in claude
    assert "analyze-logs" not in claude
    assert "{{" not in claude  # all placeholders substituted

    assert report.count("skipped-exists", "skipped-seed") == 0


def test_install_all_includes_extras(tmp_path: Path, manifest: Manifest) -> None:
    installer.install(tmp_path, manifest, PROFILES)
    assert (tmp_path / ".claude/skills/analyze-logs/SKILL.md").is_file()
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "`/analyze-logs`" in claude
    assert "openai-realtime-quirks" in claude


def test_reinstall_is_idempotent(tmp_path: Path, manifest: Manifest) -> None:
    installer.install(tmp_path, manifest, DEFAULT_PROFILES)
    report = installer.install(tmp_path, manifest, DEFAULT_PROFILES)
    assert report.count("unchanged") == len(report.results)


def test_modified_managed_file_requires_force(
    tmp_path: Path, manifest: Manifest
) -> None:
    installer.install(tmp_path, manifest, DEFAULT_PROFILES)
    victim = tmp_path / ".claude/skills/task-learnings/SKILL.md"
    victim.write_text("locally customized", encoding="utf-8")

    report = installer.install(tmp_path, manifest, DEFAULT_PROFILES)
    assert report.by_action("skipped-exists") == [
        ".claude/skills/task-learnings/SKILL.md"
    ]
    assert victim.read_text(encoding="utf-8") == "locally customized"

    report = installer.install(tmp_path, manifest, DEFAULT_PROFILES, force=True)
    assert report.by_action("overwritten") == [".claude/skills/task-learnings/SKILL.md"]
    assert victim.read_text(encoding="utf-8") != "locally customized"


def test_seeds_survive_force_but_not_reseed(tmp_path: Path, manifest: Manifest) -> None:
    installer.install(tmp_path, manifest, DEFAULT_PROFILES)
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# project-customized", encoding="utf-8")
    learnings = tmp_path / ".ai/learnings.md"
    learnings.write_text("# accumulated project history", encoding="utf-8")

    report = installer.install(tmp_path, manifest, DEFAULT_PROFILES, force=True)
    assert set(report.by_action("skipped-seed")) == {"AGENTS.md", ".ai/learnings.md"}
    assert agents.read_text(encoding="utf-8") == "# project-customized"
    assert learnings.read_text(encoding="utf-8") == "# accumulated project history"

    report = installer.install(tmp_path, manifest, DEFAULT_PROFILES, reseed=True)
    assert set(report.by_action("seeded")) == {"AGENTS.md", ".ai/learnings.md"}
    assert agents.read_text(encoding="utf-8") != "# project-customized"


def test_dry_run_writes_nothing(tmp_path: Path, manifest: Manifest) -> None:
    report = installer.install(tmp_path, manifest, DEFAULT_PROFILES, dry_run=True)
    assert report.count("written", "seeded") == len(report.results)
    assert list(tmp_path.iterdir()) == []


def test_profile_subset_only_installs_selected_skills(
    tmp_path: Path, manifest: Manifest
) -> None:
    installer.install(tmp_path, manifest, ("research",))
    installed = {p.name for p in (tmp_path / ".claude/skills").iterdir()}
    assert installed == {
        "research-source-planner",
        "research-source-claim",
        "parallel-deep-research",
    }
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "`/parallel-deep-research`" in claude
    assert "(none installed)" in claude  # no auto-loaded skills in the research profile


def test_diff_reports_drift(tmp_path: Path, manifest: Manifest) -> None:
    entries = installer.diff(tmp_path, manifest, DEFAULT_PROFILES)
    assert all(e.state == "missing" for e in entries)

    installer.install(tmp_path, manifest, DEFAULT_PROFILES)
    entries = installer.diff(tmp_path, manifest, DEFAULT_PROFILES)
    assert all(e.state == "unchanged" for e in entries)

    (tmp_path / ".claude/skills/plan-critic/SKILL.md").write_text(
        "drift", encoding="utf-8"
    )
    entries = installer.diff(tmp_path, manifest, DEFAULT_PROFILES)
    modified = [e.relative for e in entries if e.state == "modified"]
    assert modified == [".claude/skills/plan-critic/SKILL.md"]


def test_render_claude_md_groups_by_invocation(manifest: Manifest) -> None:
    text = installer.render_claude_md(manifest, PROFILES)
    user_section = text.split("### User-Invocable")[1].split("###")[0]
    auto_section = text.split("### Auto-Loaded")[1].split("###")[0]
    internal_section = text.split("### Internal Pipeline Skills")[1]
    assert "`/spec-driven-dev`" in user_section
    assert "lemmi-vertical-slice" in auto_section
    assert "plan-critic" in internal_section
    assert "{{" not in text
