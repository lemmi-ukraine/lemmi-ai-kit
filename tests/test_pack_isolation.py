"""Native pack payloads work when copied away from the source checkout."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from lemmi_ai_kit.manifest import PACKS, load_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OLD_CORE_SKILL_PATH = re.compile(r"plugins/core/skills/")
_FENCE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")


def _broken_payload_links(copied: Path) -> list[str]:
    broken: list[str] = []
    for path in sorted((copied / "skills").rglob("*.md")):
        prose = _FENCE.sub("", path.read_text(encoding="utf-8"))
        for link in _MARKDOWN_LINK.findall(prose):
            target_name = link.split("#", 1)[0]
            if (
                not target_name
                or "://" in target_name
                or target_name.startswith(("mailto:", "/"))
            ):
                continue
            target = (path.parent / target_name).resolve()
            if not target.is_relative_to(copied.resolve()) or not target.exists():
                broken.append(f"{path.relative_to(copied)} -> {link}")
    return broken


def test_old_core_path_detector_has_positive_and_negative_controls() -> None:
    assert _OLD_CORE_SKILL_PATH.search(
        "Read plugins/core/skills/agent-delegate/SKILL.md"
    )
    assert not _OLD_CORE_SKILL_PATH.search(
        "Read ${CLAUDE_PLUGIN_ROOT}/skills/agent-delegate/SKILL.md"
    )
    assert not _OLD_CORE_SKILL_PATH.search("Invoke /lemmi-ai-kit-core:agent-delegate")


def test_payload_link_detector_has_positive_and_negative_controls(
    tmp_path: Path,
) -> None:
    skill = tmp_path / "skills" / "sample"
    skill.mkdir(parents=True)
    (skill / "present.md").write_text("present", encoding="utf-8")
    index = skill / "SKILL.md"
    index.write_text("[good](present.md) [bad](missing.md)", encoding="utf-8")
    assert _broken_payload_links(tmp_path) == ["skills/sample/SKILL.md -> missing.md"]
    index.write_text("[good](present.md)", encoding="utf-8")
    assert _broken_payload_links(tmp_path) == []


def test_copied_native_payloads_have_only_their_declared_skills(
    tmp_path: Path,
) -> None:
    manifest = load_manifest()
    owners = {entry.name: entry.pack for entry in manifest.skills}
    assert len(owners) == len(manifest.skills)

    for pack in PACKS:
        source = _REPO_ROOT / "plugins" / pack
        copied = tmp_path / pack
        shutil.copytree(
            source, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )

        expected = {name for name, owner in owners.items() if owner == pack}
        skills = copied / "skills"
        actual = {path.name for path in skills.iterdir() if path.is_dir()}
        assert actual == expected, pack
        assert all((skills / name / "SKILL.md").is_file() for name in expected)

        # A copied payload has no repository-level subtree that can supply a
        # missing resource or another pack's skill at runtime.
        assert not (copied / "plugins").exists()
        allowed_roots = {".claude-plugin", ".codex-plugin", "README.md", "skills"}
        if pack == "core":
            allowed_roots.update({"src", "hooks", ".mcp.json", "vendor"})
        assert {path.name for path in copied.iterdir()} == allowed_roots

        broken_links = _broken_payload_links(copied)
        assert not broken_links, f"{pack} has broken payload links: {broken_links}"

        stale: list[str] = []
        for path in sorted(skills.rglob("*.md")):
            prose = _FENCE.sub("", path.read_text(encoding="utf-8"))
            if _OLD_CORE_SKILL_PATH.search(prose):
                stale.append(path.relative_to(copied).as_posix())
        assert not stale, f"{pack} still points at old core skill paths: {stale}"


def test_copied_core_support_package_scaffolds_without_replacing_project_seeds(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "core"
    shutil.copytree(
        _REPO_ROOT / "plugins" / "core",
        copied,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    target = tmp_path / "adopter"
    target.mkdir()
    script = """
import json
import sys
from pathlib import Path

from lemmi_ai_kit import scaffold
from lemmi_ai_kit.manifest import assets_root, load_manifest, repository_root

payload = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2])
assert repository_root().resolve() == payload
assert assets_root().resolve().is_relative_to(payload)
manifest = load_manifest()
assert manifest.skills and {entry.pack for entry in manifest.skills} == {'core'}

(target / '.ai').mkdir()
owned = {
    'AGENTS.md': b'# project rules\\n',
    'CLAUDE.md': b'# project assistant\\n',
    '.ai/learnings.md': b'# project history\\n',
}
for relative, content in owned.items():
    (target / relative).write_bytes(content)
managed = target / '.ai/templates/requirements.md'
managed.parent.mkdir(parents=True)
managed.write_bytes(b'old template\\n')

report = scaffold.scaffold(target, manifest, force=True)
assert all((target / relative).read_bytes() == content for relative, content in owned.items())
assert managed.read_bytes() != b'old template\\n'
assert set(report.by_action('skipped-seed')) == set(owned)
assert report.by_action('overwritten') == ['.ai/templates/requirements.md']
assert not (target / '.claude').exists()
print(json.dumps({'module': str(assets_root()), 'skills': len(manifest.skills)}))
"""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(copied / "src")
    result = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "python",
            "-B",
            "-c",
            script,
            str(copied),
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    output = json.loads(result.stdout)
    assert Path(output["module"]).is_relative_to(copied)
    assert output["skills"] == sum(
        entry.pack == "core" for entry in load_manifest().skills
    )
