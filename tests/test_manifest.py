"""Manifest loading and profile normalization."""

import pytest

from lemmi_ai_kit.manifest import (
    DEFAULT_PROFILES,
    PROFILES,
    ManifestError,
    assets_root,
    load_manifest,
    normalize_profiles,
)


def test_manifest_loads_and_matches_asset_dirs() -> None:
    # load_manifest() itself enforces the bijection between [[skills]] entries
    # and assets/skills/* directories, so loading successfully is the assertion.
    manifest = load_manifest()
    assert len(manifest.skills) == 33
    names = {s.name for s in manifest.skills}
    assert "task-learnings" in names
    assert "openai-realtime-quirks" in names


def test_every_profile_is_used() -> None:
    manifest = load_manifest()
    used = {s.profile for s in manifest.skills}
    assert used == set(PROFILES)


def test_for_profiles_filters() -> None:
    manifest = load_manifest()
    python_only = manifest.for_profiles(("python",))
    assert {s.name for s in python_only} == {
        "lemmi-python-conventions",
        "lemmi-vertical-slice",
        "lemmi-test-conventions",
    }


def test_normalize_profiles_defaults() -> None:
    assert normalize_profiles([]) == DEFAULT_PROFILES
    assert "extras" not in DEFAULT_PROFILES


def test_normalize_profiles_all() -> None:
    assert normalize_profiles([], include_all=True) == PROFILES


def test_normalize_profiles_comma_and_repeat() -> None:
    assert normalize_profiles(["python,core", "extras"]) == ("core", "python", "extras")


def test_normalize_profiles_unknown_raises() -> None:
    with pytest.raises(ManifestError, match="unknown profile"):
        normalize_profiles(["nope"])


def test_assets_root_exists() -> None:
    root = assets_root()
    assert (root / "manifest.toml").is_file()
    assert (root / "templates" / "AGENTS.md").is_file()
    assert (root / "templates" / "CLAUDE.md").is_file()
    assert (root / "ai" / "learnings.md").is_file()
