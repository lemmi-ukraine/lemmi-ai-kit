"""Pack-boundary checks for the pre-restructure skill catalog."""

from pathlib import Path

from lemmi_ai_kit.manifest import assets_root, load_manifest, skill_dir


def _text_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".md", ".txt"}
    )


def test_core_assets_do_not_name_python_pack_skills() -> None:
    """Core-shipped assets must route to language conventions by role, not name."""
    manifest = load_manifest()
    python_skill_names = {
        entry.name for entry in manifest.skills if entry.profile == "python"
    }
    assert python_skill_names, "test needs at least one python-pack skill to guard"

    root = assets_root()
    python_skill_dirs = {
        skill_dir(entry)
        for entry in manifest.skills
        if entry.name in python_skill_names
    }
    search_roots = (
        *(skill_dir(entry) for entry in manifest.skills if entry.profile != "python"),
        root / "templates",
        root / "ai",
    )

    violations: list[str] = []
    for search_root in search_roots:
        for path in _text_files(search_root):
            if any(path.is_relative_to(skill_dir) for skill_dir in python_skill_dirs):
                continue
            text = path.read_text(encoding="utf-8")
            for skill_name in sorted(python_skill_names):
                if skill_name not in text:
                    continue
                try:
                    rel = path.relative_to(root).as_posix()
                except ValueError:
                    rel = path.as_posix()
                line = text.count("\n", 0, text.index(skill_name)) + 1
                violations.append(f"{rel}:{line}: hardcodes `{skill_name}`")

    assert not violations, "core assets name python-pack skills:\n" + "\n".join(
        violations
    )
