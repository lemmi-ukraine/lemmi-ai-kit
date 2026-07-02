"""Typed access to the bundled asset manifest (assets/manifest.toml)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Literal, cast

Invocation = Literal["user", "auto", "internal"]

PROFILES: tuple[str, ...] = (
    "core",
    "skill-authoring",
    "prompts",
    "research",
    "python",
    "extras",
)

# Everything that is generic or applies to Lemmi Python projects; `extras`
# (project-flavored skills) stays opt-in.
DEFAULT_PROFILES: tuple[str, ...] = (
    "core",
    "skill-authoring",
    "prompts",
    "research",
    "python",
)

_INVOCATIONS: tuple[Invocation, ...] = ("user", "auto", "internal")


class ManifestError(ValueError):
    """Raised when the bundled manifest is malformed or inconsistent."""


@dataclass(frozen=True)
class SkillEntry:
    """One skill shipped by the kit."""

    name: str
    profile: str
    invocation: Invocation
    summary: str


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
        entries.append(
            SkillEntry(
                name=name,
                profile=cast(str, profile),
                invocation=invocation,
                summary=summary,
            )
        )

    names = [e.name for e in entries]
    if len(names) != len(set(names)):
        raise ManifestError("duplicate skill names in manifest.toml")

    shipped = {p.name for p in (root / "skills").iterdir() if p.is_dir()}
    listed = set(names)
    if shipped != listed:
        missing = ", ".join(sorted(shipped - listed)) or "-"
        stale = ", ".join(sorted(listed - shipped)) or "-"
        raise ManifestError(
            f"manifest.toml out of sync with assets/skills: unlisted dirs [{missing}], stale entries [{stale}]"
        )

    return Manifest(skills=tuple(entries))
