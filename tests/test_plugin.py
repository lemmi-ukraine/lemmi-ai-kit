"""Claude Code plugin packaging: manifests valid, paths resolve, versions in sync."""

import json
import re
import tomllib
from pathlib import Path
from typing import Any, cast

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative: str) -> dict[str, Any]:
    path = _REPO_ROOT / relative
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _plugin_json() -> dict[str, Any]:
    return _load_json(".claude-plugin/plugin.json")


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_plugin_json_paths_resolve() -> None:
    data = _plugin_json()
    name = cast(str, data["name"])
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", name)
    skill_dirs = cast(list[str], data["skills"])
    assert isinstance(skill_dirs, list) and skill_dirs
    for rel in skill_dirs:
        assert rel.startswith("./")
        assert (_REPO_ROOT / rel).is_dir(), f"plugin skills path missing: {rel}"


def test_plugin_json_in_sync_with_pyproject() -> None:
    """Version and repo URL have one source of truth each; plugin.json must match."""
    data = _plugin_json()
    project = cast(dict[str, Any], _pyproject()["project"])
    assert data["version"] == project["version"]
    assert data["repository"] == project["urls"]["Repository"]


def test_marketplace_lists_the_plugin_at_repo_root() -> None:
    market = _load_json(".claude-plugin/marketplace.json")
    owner = cast(dict[str, Any], market["owner"])
    assert owner["name"]
    plugins = cast(list[dict[str, Any]], market["plugins"])
    entries = {p["name"]: p for p in plugins}
    plugin = entries[_plugin_json()["name"]]
    assert plugin["source"] == "./"


def test_kit_setup_skill_ships_with_plugin() -> None:
    text = (_REPO_ROOT / "src/lemmi_ai_kit/assets/skills/kit-setup/SKILL.md").read_text(
        encoding="utf-8"
    )
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "kit-setup SKILL.md missing frontmatter"
    assert re.search(r"^description:", match.group(1), re.MULTILINE)
    # the skill must read templates from the plugin, not from hardcoded paths
    assert "${CLAUDE_PLUGIN_ROOT}" in text
