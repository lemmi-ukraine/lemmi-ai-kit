"""Typed access to the bundled asset manifest (assets/manifest.toml)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Literal, cast

Invocation = Literal["user", "auto", "internal"]
Pack = Literal["core", "python"]

PROFILES: tuple[str, ...] = (
    "core",
    "skill-authoring",
    "research",
    "orchestration",
    "python",
)

# Profiles still describe skill families for the support CLI. Pack boundaries are
# enforced by plugin layout, so language-specific profiles are explicit opt-ins here.
DEFAULT_PROFILES: tuple[str, ...] = (
    "core",
    "skill-authoring",
    "research",
    "orchestration",
)

_INVOCATIONS: tuple[Invocation, ...] = ("user", "auto", "internal")
PACKS: tuple[Pack, ...] = ("core", "python")
PACK_PLUGIN_NAMES: dict[Pack, str] = {
    "core": "lemmi-ai-kit-core",
    "python": "lemmi-ai-kit-python",
}


class ManifestError(ValueError):
    """Raised when the bundled manifest is malformed or inconsistent."""


@dataclass(frozen=True)
class SkillEntry:
    """One skill shipped by the kit."""

    name: str
    profile: str
    invocation: Invocation
    summary: str
    pack: Pack

    @property
    def plugin_name(self) -> str:
        """Codex/Claude plugin name that exposes this skill."""
        return PACK_PLUGIN_NAMES[self.pack]


@dataclass(frozen=True)
class Manifest:
    """The full set of skills shipped by the kit."""

    skills: tuple[SkillEntry, ...]

    def for_profiles(self, profiles: tuple[str, ...]) -> tuple[SkillEntry, ...]:
        return tuple(s for s in self.skills if s.profile in profiles)


def assets_root() -> Path:
    """Filesystem path of the bundled assets directory."""
    root = resources.files("lemmi_ai_kit") / "assets"
    return Path(str(root))


def repository_root() -> Path:
    """Checkout/plugin root when running from this repo layout."""
    root = assets_root()
    candidates = (root, *root.parents)
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "plugins"
        ).is_dir():
            return candidate
    for candidate in candidates:
        if (
            candidate.joinpath(".codex-plugin", "plugin.json").is_file()
            or candidate.joinpath(".claude-plugin", "plugin.json").is_file()
        ):
            return candidate
    return root


def plugin_root(pack: Pack) -> Path:
    """Root directory for one plugin pack in a checkout or inside one plugin payload."""
    root = repository_root()
    checkout_pack = root / "plugins" / pack
    if checkout_pack.is_dir():
        return checkout_pack
    if pack == "core" and (root / "skills").is_dir():
        return root
    return checkout_pack


def available_packs() -> tuple[Pack, ...]:
    """Packs whose skill roots are present in this filesystem view."""
    return tuple(pack for pack in PACKS if skills_root(pack).is_dir())


def pack_for_profile(profile: str) -> Pack:
    """Map manifest profiles to the plugin pack that ships them."""
    return "python" if profile == "python" else "core"


def skills_root(pack: Pack) -> Path:
    """Directory containing one pack's skill directories."""
    return plugin_root(pack) / "skills"


def skill_dir(entry: SkillEntry) -> Path:
    """Directory for one shipped skill."""
    return skills_root(entry.pack) / entry.name


def shipped_skill_dirs() -> dict[str, Path]:
    """All skill directories physically shipped by every pack."""
    shipped: dict[str, Path] = {}
    for pack in PACKS:
        root = skills_root(pack)
        if not root.is_dir():
            continue
        for path in sorted(p for p in root.iterdir() if p.is_dir()):
            if path.name in shipped:
                raise ManifestError(
                    f"skill directory shipped by multiple packs: {path.name}"
                )
            shipped[path.name] = path
    return shipped


def normalize_profiles(raw: list[str], *, include_all: bool = False) -> tuple[str, ...]:
    """Expand comma-separated profile args, validate names, apply defaults."""
    if include_all:
        return PROFILES
    names = [p.strip() for chunk in raw for p in chunk.split(",") if p.strip()]
    if not names:
        return DEFAULT_PROFILES
    unknown = sorted(set(names) - set(PROFILES))
    if unknown:
        known = ", ".join(PROFILES)
        raise ManifestError(
            f"unknown profile(s): {', '.join(unknown)} (known: {known})"
        )
    # preserve manifest ordering, drop duplicates
    return tuple(p for p in PROFILES if p in names)


def load_manifest() -> Manifest:
    """Load and validate assets/manifest.toml against the shipped skill dirs."""
    root = assets_root()
    manifest_path = root / "manifest.toml"
    with manifest_path.open("rb") as fh:
        data = tomllib.load(fh)

    raw_skills = data.get("skills")
    if not isinstance(raw_skills, list) or not raw_skills:
        raise ManifestError("manifest.toml must contain a non-empty [[skills]] list")

    present_packs = set(available_packs())
    if not present_packs:
        raise ManifestError("no plugin skill roots found")

    entries: list[SkillEntry] = []
    for raw in cast(list[dict[str, object]], raw_skills):
        name = raw.get("name")
        profile = raw.get("profile")
        invocation = raw.get("invocation")
        summary = raw.get("summary")
        if not isinstance(name, str) or not name:
            raise ManifestError(f"skill entry without a valid name: {raw!r}")
        if profile not in PROFILES:
            raise ManifestError(f"skill {name}: unknown profile {profile!r}")
        if invocation not in _INVOCATIONS:
            raise ManifestError(f"skill {name}: unknown invocation {invocation!r}")
        if not isinstance(summary, str) or not summary:
            raise ManifestError(f"skill {name}: missing summary")
        pack = pack_for_profile(cast(str, profile))
        entry = SkillEntry(
            name=name,
            profile=cast(str, profile),
            invocation=invocation,
            summary=summary,
            pack=pack,
        )
        if pack in present_packs:
            entries.append(entry)

    names = [e.name for e in entries]
    if len(names) != len(set(names)):
        raise ManifestError("duplicate skill names in manifest.toml")

    shipped = set(shipped_skill_dirs())
    listed = set(names)
    if shipped != listed:
        missing = ", ".join(sorted(shipped - listed)) or "-"
        stale = ", ".join(sorted(listed - shipped)) or "-"
        raise ManifestError(
            f"manifest.toml out of sync with plugin skill dirs: unlisted dirs [{missing}], stale entries [{stale}]"
        )

    return Manifest(skills=tuple(entries))
