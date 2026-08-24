"""Pack-boundary checks: a core-shipped asset must not name a language-pack skill.

Two things this file has had to learn the hard way.

**Its scope is the post-restructure trees.** An earlier docstring said "pre-restructure
skill catalog", which was stale prose over correct code -- `skill_dir()` resolves through
the manifest to `plugins/<pack>/skills/`.

**Its failure message must be repo-relative.** Violations are reported against
`repository_root()`, not `assets_root()`. The guard's *main* case is a skill directory,
which lives outside the asset tree -- so anchoring on `assets_root()` sent every real
violation down a `ValueError` fallback that printed an absolute machine path. Found by
firing the guard at a planted violation rather than by reading it: a passing guard shows
you nothing about what it says when it fails.
"""

from pathlib import Path

from lemmi_ai_kit.manifest import (
    assets_root,
    load_manifest,
    repository_root,
    skill_dir,
)


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
                # Anchored on the repository root, not the asset tree: a violation in
                # `plugins/<pack>/skills/` is the common case and is not under
                # `assets_root()`, so anchoring there printed an absolute machine path.
                try:
                    rel = path.relative_to(repository_root()).as_posix()
                except ValueError:  # pragma: no cover - outside the checkout entirely
                    rel = path.name
                line = text.count("\n", 0, text.index(skill_name)) + 1
                violations.append(f"{rel}:{line}: hardcodes `{skill_name}`")

    assert not violations, "core assets name python-pack skills:\n" + "\n".join(
        violations
    )


def test_every_search_root_is_inside_the_repository() -> None:
    """The invariant that keeps a violation message repo-relative.

    The guard above only prints paths when it FAILS, so a passing run says nothing about
    whether its output is portable -- and it was not: skill directories fell through
    `relative_to()` and printed an absolute machine path. This pins the property directly
    instead of waiting for the next failure to reveal it, and it is the reason the
    anchor is `repository_root()` rather than `assets_root()`.
    """
    checkout = repository_root().resolve()
    manifest = load_manifest()
    assets = assets_root()
    search_roots = (
        *(skill_dir(entry) for entry in manifest.skills),
        assets / "templates",
        assets / "ai",
    )
    assert search_roots, "no search roots resolved, so this check is vacuous"

    escapees = [
        root.as_posix()
        for root in search_roots
        if not root.resolve().is_relative_to(checkout)
    ]
    assert not escapees, (
        "search roots outside the repository root -- a violation under these would "
        "print an absolute machine path:\n" + "\n".join(escapees)
    )
