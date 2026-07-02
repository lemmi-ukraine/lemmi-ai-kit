"""Asset hygiene: valid frontmatter and no project/machine contamination.

These tests are the permanent enforcement of the porting cleanup contract:
assets must work in a brand-new project on any machine.
"""

import re
from pathlib import Path

from lemmi_ai_kit.manifest import assets_root, load_manifest

# (pattern, human explanation)
_FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"/Users/"), "absolute macOS home path"),
    (re.compile(r"/home/\w"), "absolute Linux home path"),
    (re.compile(r"[A-Za-z]:\\\\?[A-Za-z]"), "Windows drive-letter path"),
    (re.compile(r"Windows host"), "machine-specific host rule"),
    (re.compile(r"PYTHONIOENCODING"), "machine-specific console workaround"),
    (re.compile(r"lemmi-ai-api"), "source-project reference"),
    (re.compile(r"learnings\.md\s+20\d{2}-\d{2}"), "dated learnings citation"),
    (re.compile(r"retrospectives/20\d{2}"), "dated retrospective citation"),
    (re.compile(r"\.ai/backups/"), "source-project backup reference"),
)

# Files allowed to mention a pattern because they *teach or implement* the rule
# that bans it. Keep this list minimal and specific.
_ALLOWLIST: dict[str, tuple[str, ...]] = {
    # The portability rule itself names the forbidden path shapes.
    "templates/AGENTS.md": ("absolute macOS home path",),
    # The portability review check documents the patterns to grep for.
    "skills/skill-reviewer/SKILL.md": (
        "absolute macOS home path",
        "Windows drive-letter path",
    ),
    # Secret-redaction regexes (`authorization:\s`) and a comment about runtime
    # Windows path normalization trip the drive-letter pattern.
    "skills/session-retrospective/scripts/extract_sessions.py": (
        "Windows drive-letter path",
    ),
    # Path-encoding test fixtures (the rule's explicit "redaction-test fixtures" exception).
    "skills/session-retrospective/scripts/test_extract_sessions.py": (
        "absolute macOS home path",
        "absolute Linux home path",
        "Windows drive-letter path",
    ),
}


def _asset_text_files() -> list[Path]:
    root = assets_root()
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix in {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml"}
    )


def test_assets_have_no_contamination() -> None:
    root = assets_root()
    violations: list[str] = []
    for path in _asset_text_files():
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        allowed = _ALLOWLIST.get(rel, ())
        for pattern, why in _FORBIDDEN:
            if why in allowed:
                continue
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                violations.append(f"{rel}:{line}: {why} ({match.group(0)!r})")
    assert not violations, "contaminated assets:\n" + "\n".join(violations)


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def test_every_skill_has_valid_frontmatter() -> None:
    root = assets_root()
    problems: list[str] = []
    for entry in load_manifest().skills:
        skill_md = root / "skills" / entry.name / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f"{entry.name}: SKILL.md missing")
            continue
        text = skill_md.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if match is None:
            problems.append(f"{entry.name}: no YAML frontmatter block")
            continue
        block = match.group(1)
        name_match = re.search(r"^name:\s*(\S+)\s*$", block, re.MULTILINE)
        if name_match is None or name_match.group(1) != entry.name:
            problems.append(
                f"{entry.name}: frontmatter name mismatch ({name_match and name_match.group(1)})"
            )
        if re.search(r"^description:", block, re.MULTILINE) is None:
            problems.append(f"{entry.name}: frontmatter missing description")
    assert not problems, "\n".join(problems)


def test_skill_relative_references_resolve() -> None:
    """Any references/..., assets/..., scripts/... path mentioned in a SKILL.md must ship.

    Fenced code blocks are excluded: skills that teach skill authoring show
    illustrative example links there.
    """
    root = assets_root()
    link_re = re.compile(r"\((?:\./)?((?:references|assets|scripts)/[\w./-]+)\)")
    fence_re = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
    problems: list[str] = []
    for entry in load_manifest().skills:
        skill_dir = root / "skills" / entry.name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        prose = fence_re.sub("", skill_md.read_text(encoding="utf-8"))
        for match in link_re.finditer(prose):
            target = skill_dir / match.group(1)
            if not target.is_file():
                problems.append(f"{entry.name}: broken reference {match.group(1)}")
    assert not problems, "\n".join(problems)


def test_ai_state_files_ship_empty() -> None:
    """Stateful .ai logs must ship as headers only — a new project starts with zero entries."""
    root = assets_root()
    for name in ("learnings.md", "ai-changelog.md", "improvement-hypotheses.md"):
        text = (root / "ai" / name).read_text(encoding="utf-8")
        assert not re.search(r"^### \[?20\d{2}-", text, re.MULTILINE), (
            f"{name} ships with dated entries"
        )
