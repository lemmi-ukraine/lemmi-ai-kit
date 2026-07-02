"""Install, diff, and render the bundled AI configuration into a target project.

Two kinds of files:

- **managed** — owned by the kit and safe to update on upgrade: everything under
  `.claude/skills/` and `.ai/templates/`. Overwritten only with `force`.
- **seeds** — written once, then owned by the project: `AGENTS.md`, `CLAUDE.md`
  and the stateful `.ai/*.md` logs (learnings, changelog, hypotheses). Never
  touched on re-install unless `reseed` is passed explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from lemmi_ai_kit.manifest import Manifest, SkillEntry, assets_root

Action = Literal[
    "written",
    "overwritten",
    "unchanged",
    "skipped-exists",
    "seeded",
    "skipped-seed",
]

Kind = Literal["managed", "seed"]

_SEED_STATE_FILES: tuple[str, ...] = (
    "learnings.md",
    "ai-changelog.md",
    "improvement-hypotheses.md",
)

_CLAUDE_PLACEHOLDERS: dict[str, Literal["user", "auto", "internal"]] = {
    "{{SKILLS_USER}}": "user",
    "{{SKILLS_AUTO}}": "auto",
    "{{SKILLS_INTERNAL}}": "internal",
}


@dataclass(frozen=True)
class PlannedFile:
    """One file the installer wants to place into the target project."""

    relative: str
    content: bytes
    kind: Kind


@dataclass(frozen=True)
class FileResult:
    relative: str
    action: Action


@dataclass
class Report:
    results: list[FileResult] = field(default_factory=list)

    def count(self, *actions: Action) -> int:
        return sum(1 for r in self.results if r.action in actions)

    def by_action(self, action: Action) -> list[str]:
        return [r.relative for r in self.results if r.action == action]


def _skill_line(entry: SkillEntry) -> str:
    if entry.invocation == "user":
        return f"- `/{entry.name}` — {entry.summary}"
    return f"- {entry.name} — {entry.summary}"


def render_claude_md(manifest: Manifest, profiles: tuple[str, ...]) -> str:
    """Render CLAUDE.md from the bundled template and the selected skills."""
    template = (assets_root() / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
    selected = manifest.for_profiles(profiles)
    for placeholder, invocation in _CLAUDE_PLACEHOLDERS.items():
        lines = [_skill_line(e) for e in selected if e.invocation == invocation]
        block = "\n".join(lines) if lines else "- (none installed)"
        template = template.replace(placeholder, block)
    return template


def _walk_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def plan(manifest: Manifest, profiles: tuple[str, ...]) -> list[PlannedFile]:
    """Compute every file an install would place, with its target-relative path."""
    root = assets_root()
    planned: list[PlannedFile] = []

    for entry in manifest.for_profiles(profiles):
        skill_root = root / "skills" / entry.name
        for path in _walk_files(skill_root):
            rel = (
                f".claude/skills/{entry.name}/{path.relative_to(skill_root).as_posix()}"
            )
            planned.append(PlannedFile(rel, path.read_bytes(), "managed"))

    ai_root = root / "ai"
    for path in _walk_files(ai_root):
        rel_inside = path.relative_to(ai_root).as_posix()
        kind: Kind = "seed" if rel_inside in _SEED_STATE_FILES else "managed"
        planned.append(PlannedFile(f".ai/{rel_inside}", path.read_bytes(), kind))

    agents = (root / "templates" / "AGENTS.md").read_bytes()
    planned.append(PlannedFile("AGENTS.md", agents, "seed"))

    claude = render_claude_md(manifest, profiles).encode("utf-8")
    planned.append(PlannedFile("CLAUDE.md", claude, "seed"))

    return planned


def _decide(target: Path, item: PlannedFile, *, force: bool, reseed: bool) -> Action:
    dest = target / item.relative
    if not dest.exists():
        return "seeded" if item.kind == "seed" else "written"
    if dest.read_bytes() == item.content:
        return "unchanged"
    if item.kind == "seed":
        return "seeded" if reseed else "skipped-seed"
    return "overwritten" if force else "skipped-exists"


def install(
    target: Path,
    manifest: Manifest,
    profiles: tuple[str, ...],
    *,
    force: bool = False,
    reseed: bool = False,
    dry_run: bool = False,
) -> Report:
    """Place the selected profiles' files into `target`. Returns a per-file report."""
    report = Report()
    for item in plan(manifest, profiles):
        action = _decide(target, item, force=force, reseed=reseed)
        if action in ("written", "overwritten", "seeded") and not dry_run:
            dest = target / item.relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(item.content)
        report.results.append(FileResult(item.relative, action))
    return report


@dataclass(frozen=True)
class DriftEntry:
    relative: str
    state: Literal["missing", "modified", "unchanged"]
    kind: Kind


def diff(
    target: Path, manifest: Manifest, profiles: tuple[str, ...]
) -> list[DriftEntry]:
    """Compare an installed project against the kit's current assets."""
    entries: list[DriftEntry] = []
    for item in plan(manifest, profiles):
        dest = target / item.relative
        if not dest.exists():
            state: Literal["missing", "modified", "unchanged"] = "missing"
        elif dest.read_bytes() != item.content:
            state = "modified"
        else:
            state = "unchanged"
        entries.append(DriftEntry(item.relative, state, item.kind))
    return entries
