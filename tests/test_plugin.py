"""Plugin packaging for Claude Code and Codex: manifests valid, paths resolve, versions in sync."""

import json
import re
import tomllib
from pathlib import Path
from typing import Any, cast

from lemmi_ai_kit.manifest import (
    PACK_PLUGIN_NAMES,
    PACKS,
    Pack,
    load_manifest,
    skill_dir,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative: str) -> dict[str, Any]:
    path = _REPO_ROOT / relative
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _claude_plugin_json(pack: Pack) -> dict[str, Any]:
    return _load_json(f"plugins/{pack}/.claude-plugin/plugin.json")


def _codex_plugin_json(pack: Pack) -> dict[str, Any]:
    return _load_json(f"plugins/{pack}/.codex-plugin/plugin.json")


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _assert_plugin_identity(data: dict[str, Any], expected_name: str) -> None:
    name = cast(str, data["name"])
    assert name == expected_name
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", name)
    project = cast(dict[str, Any], _pyproject()["project"])
    assert data["version"] == project["version"]
    assert data["repository"] == project["urls"]["Repository"]


def _assert_skills_path_resolves(plugin_root: Path, skills: str | list[str]) -> None:
    rels = [skills] if isinstance(skills, str) else skills
    assert rels
    for rel in rels:
        assert rel.startswith("./")
        assert ".." not in rel
        root = plugin_root / rel
        assert root.is_dir(), f"plugin skills path missing: {plugin_root / rel}"
        # Derived, not enumerated: the point is that the declared path actually ships
        # skills, not that it ships one particular skill. Naming a sentinel per pack
        # fails every pack added later, which `new-pack` now makes routine.
        assert any((d / "SKILL.md").is_file() for d in root.iterdir() if d.is_dir()), (
            f"{plugin_root / rel} declares a skills path that ships no skill"
        )


def test_no_root_plugin_manifest_remains() -> None:
    """The repo root is now the marketplace root, not a plugin payload."""
    assert not (_REPO_ROOT / ".codex-plugin" / "plugin.json").exists()
    assert not (_REPO_ROOT / ".claude-plugin" / "plugin.json").exists()


def test_pack_plugin_json_paths_resolve() -> None:
    for pack in PACKS:
        plugin_root = _REPO_ROOT / "plugins" / pack
        expected_name = PACK_PLUGIN_NAMES[pack]

        claude = _claude_plugin_json(pack)
        _assert_plugin_identity(claude, expected_name)
        _assert_skills_path_resolves(plugin_root, cast(list[str], claude["skills"]))

        codex = _codex_plugin_json(pack)
        _assert_plugin_identity(codex, expected_name)
        _assert_skills_path_resolves(plugin_root, cast(str, codex["skills"]))
        interface = cast(dict[str, Any], codex["interface"])
        assert interface["displayName"]
        assert interface["category"]


def test_claude_and_codex_pack_manifests_share_identity_and_skills() -> None:
    for pack in PACKS:
        claude = _claude_plugin_json(pack)
        codex = _codex_plugin_json(pack)
        assert claude["name"] == codex["name"]
        assert claude["version"] == codex["version"]
        assert claude["repository"] == codex["repository"]
        assert cast(list[str], claude["skills"]) == [codex["skills"]]


def test_pack_skill_dirs_match_the_asset_manifest() -> None:
    manifest = load_manifest()
    for pack in PACKS:
        expected = {entry.name for entry in manifest.skills if entry.pack == pack}
        root = _REPO_ROOT / "plugins" / pack / "skills"
        shipped = {path.name for path in root.iterdir() if path.is_dir()}
        assert shipped == expected


def test_claude_marketplace_lists_every_pack() -> None:
    market = _load_json(".claude-plugin/marketplace.json")
    owner = cast(dict[str, Any], market["owner"])
    assert owner["name"]
    plugins = cast(list[dict[str, Any]], market["plugins"])
    entries = {p["name"]: p for p in plugins}
    assert set(entries) == {PACK_PLUGIN_NAMES[pack] for pack in PACKS}
    for pack in PACKS:
        plugin = entries[PACK_PLUGIN_NAMES[pack]]
        assert plugin["source"] == f"./plugins/{pack}"


def test_codex_marketplace_source_paths_resolve_to_plugin_dirs() -> None:
    # Codex reports some malformed local plugins as installed, so this test asserts
    # the actual payload roots and manifests that installation must consume.
    market = _load_json(".agents/plugins/marketplace.json")
    assert market["name"]
    interface = cast(dict[str, Any], market["interface"])
    assert interface["displayName"]
    plugins = cast(list[dict[str, Any]], market["plugins"])
    entries = {p["name"]: p for p in plugins}
    assert set(entries) == {PACK_PLUGIN_NAMES[pack] for pack in PACKS}

    for pack in PACKS:
        plugin = entries[PACK_PLUGIN_NAMES[pack]]
        source = cast(dict[str, Any], plugin["source"])
        assert source["source"] == "local"
        rel = cast(str, source["path"])
        assert rel == f"./plugins/{pack}"
        plugin_root = _REPO_ROOT / rel
        assert plugin_root.is_dir(), (
            f"codex plugin source path is not a directory: {rel}"
        )
        manifest = plugin_root / ".codex-plugin" / "plugin.json"
        assert manifest.is_file(), (
            f"no .codex-plugin/plugin.json under source.path: {rel}"
        )
        policy = cast(dict[str, Any], plugin["policy"])
        assert policy["installation"]
        assert policy["authentication"]
        assert plugin["category"]


def test_kit_setup_skill_ships_with_core_plugin() -> None:
    entry = next(s for s in load_manifest().skills if s.name == "kit-setup")
    text = (skill_dir(entry) / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "kit-setup SKILL.md missing frontmatter"
    assert re.search(r"^description:", match.group(1), re.MULTILINE)
    # skill must resolve plugin root on Claude (CLAUDE_PLUGIN_ROOT) and Codex
    # (PLUGIN_ROOT; Codex also sets CLAUDE_PLUGIN_ROOT for compatibility)
    assert "CLAUDE_PLUGIN_ROOT" in text or "PLUGIN_ROOT" in text
