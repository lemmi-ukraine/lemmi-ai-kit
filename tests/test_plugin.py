"""Plugin packaging for Claude Code and Codex: manifests valid, paths resolve, versions in sync."""

import json
import re
import tomllib
from pathlib import Path
from typing import Any, cast

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative: str) -> dict[str, Any]:
    path = _REPO_ROOT / relative
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _claude_plugin_json() -> dict[str, Any]:
    return _load_json(".claude-plugin/plugin.json")


def _codex_plugin_json() -> dict[str, Any]:
    return _load_json(".codex-plugin/plugin.json")


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _assert_plugin_identity(data: dict[str, Any]) -> None:
    name = cast(str, data["name"])
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", name)
    project = cast(dict[str, Any], _pyproject()["project"])
    assert data["version"] == project["version"]
    assert data["repository"] == project["urls"]["Repository"]


def test_claude_plugin_json_paths_resolve() -> None:
    data = _claude_plugin_json()
    _assert_plugin_identity(data)
    skill_dirs = cast(list[str], data["skills"])
    assert isinstance(skill_dirs, list) and skill_dirs
    for rel in skill_dirs:
        assert rel.startswith("./")
        assert (_REPO_ROOT / rel).is_dir(), f"plugin skills path missing: {rel}"


def test_codex_plugin_json_paths_resolve() -> None:
    data = _codex_plugin_json()
    _assert_plugin_identity(data)
    skills = cast(str, data["skills"])
    assert isinstance(skills, str) and skills.startswith("./")
    assert (_REPO_ROOT / skills).is_dir(), f"codex skills path missing: {skills}"
    interface = cast(dict[str, Any], data["interface"])
    assert interface["displayName"]
    assert interface["category"]


def test_claude_and_codex_plugins_share_identity_and_skills() -> None:
    claude = _claude_plugin_json()
    codex = _codex_plugin_json()
    assert claude["name"] == codex["name"]
    assert claude["version"] == codex["version"]
    assert claude["repository"] == codex["repository"]
    claude_skills = cast(list[str], claude["skills"])
    codex_skills = cast(str, codex["skills"])
    assert codex_skills in claude_skills or claude_skills == [codex_skills]


def test_claude_marketplace_lists_the_plugin_at_repo_root() -> None:
    market = _load_json(".claude-plugin/marketplace.json")
    owner = cast(dict[str, Any], market["owner"])
    assert owner["name"]
    plugins = cast(list[dict[str, Any]], market["plugins"])
    entries = {p["name"]: p for p in plugins}
    plugin = entries[_claude_plugin_json()["name"]]
    assert plugin["source"] == "./"


def test_codex_marketplace_lists_the_plugin_at_repo_root() -> None:
    market = _load_json(".agents/plugins/marketplace.json")
    assert market["name"]
    interface = cast(dict[str, Any], market["interface"])
    assert interface["displayName"]
    plugins = cast(list[dict[str, Any]], market["plugins"])
    entries = {p["name"]: p for p in plugins}
    plugin = entries[_codex_plugin_json()["name"]]
    source = cast(dict[str, Any], plugin["source"])
    assert source["source"] == "local"
    assert source["path"] == "./"
    policy = cast(dict[str, Any], plugin["policy"])
    assert policy["installation"]
    assert policy["authentication"]
    assert plugin["category"]


def test_kit_setup_skill_ships_with_plugin() -> None:
    text = (_REPO_ROOT / "src/lemmi_ai_kit/assets/skills/kit-setup/SKILL.md").read_text(
        encoding="utf-8"
    )
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "kit-setup SKILL.md missing frontmatter"
    assert re.search(r"^description:", match.group(1), re.MULTILINE)
    # skill must resolve plugin root on Claude (CLAUDE_PLUGIN_ROOT) and Codex
    # (PLUGIN_ROOT; Codex also sets CLAUDE_PLUGIN_ROOT for compatibility)
    assert "CLAUDE_PLUGIN_ROOT" in text or "PLUGIN_ROOT" in text
