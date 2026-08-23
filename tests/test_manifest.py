"""Manifest loading and profile normalization."""

import pytest

from lemmi_ai_kit.manifest import (
    DEFAULT_PROFILES,
    PACKS,
    PROFILES,
    ManifestError,
    assets_root,
    load_manifest,
    normalize_profiles,
    skills_root,
)


def test_manifest_loads_and_matches_asset_dirs() -> None:
    # load_manifest() itself enforces the bijection between [[skills]] entries
    # and plugins/*/skills/* directories, so loading successfully is the assertion.
    manifest = load_manifest()
    # No literal here on purpose. This test already asserts manifest <-> asset-dir
    # equality below, and a hard-coded total rots on every legitimate catalog change --
    # whoever adds a skill bumps it mechanically, which defeats the guard while looking
    # like maintenance. The catalog size is pinned where a human can see it drift:
    # README.md, enforced against this manifest by tests/test_readme_counts.py.
    assert manifest.skills, "manifest ships no skills"
    names = {s.name for s in manifest.skills}
    assert "task-learnings" in names
    assert "openai-realtime-quirks" not in names


def test_every_profile_is_used() -> None:
    manifest = load_manifest()
    used = {s.profile for s in manifest.skills}
    assert used == set(PROFILES)


def test_for_profiles_filters() -> None:
    manifest = load_manifest()
    python_only = manifest.for_profiles(("python",))
    assert {s.name for s in python_only} == {
        "python-conventions",
        "test-conventions",
    }


def test_normalize_profiles_defaults() -> None:
    assert normalize_profiles([]) == DEFAULT_PROFILES
    assert "python" not in DEFAULT_PROFILES


def test_normalize_profiles_all() -> None:
    assert normalize_profiles([], include_all=True) == PROFILES


def test_normalize_profiles_comma_and_repeat() -> None:
    assert normalize_profiles(["python,core", "python"]) == ("core", "python")


def test_normalize_profiles_unknown_raises() -> None:
    with pytest.raises(ManifestError, match="unknown profile"):
        normalize_profiles(["nope"])


def test_assets_root_exists() -> None:
    root = assets_root()
    assert (root / "manifest.toml").is_file()
    assert (root / "templates" / "AGENTS.md").is_file()
    assert (root / "templates" / "CLAUDE.md").is_file()
    assert (root / "ai" / "learnings.md").is_file()


def test_pack_skill_roots_exist() -> None:
    for pack in PACKS:
        assert skills_root(pack).is_dir()
