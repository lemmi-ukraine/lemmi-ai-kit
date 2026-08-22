"""Nothing tracked may name the private source project, except where it teaches the rule.

`test_assets.py` enforces the same ban, but only under `assets_root()`. Every
top-level tree added since — `docs/`, the community files, and anything future —
was unguarded, so a reference could reach a committed path without anything
checking it. That is not hypothetical: the Part B handoff's own mention of the
source project is exempt on the merits, but nothing verified it. It passed because
the scan never looked.

Scope is deliberately **tracked files only**. That is the set that becomes public,
and it keeps untracked local scratch (planning notes, scratch dirs) out of scope
rather than failing a developer's run for files they never intend to commit. A
tracked file is a published file, and this test is the gate.
"""

import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The asset tree has its own, stricter contract in test_assets.py.
_ALREADY_COVERED = "src/lemmi_ai_kit/assets/"

_SOURCE_PROJECT = re.compile(r"lemmi-ai-api")

# Files permitted to name it because they teach, implement, or document the rule
# that bans it — the same principle as test_assets.py's _ALLOWLIST. Keep this
# minimal: every entry is a file that would be wrong to rewrite.
_TEACHES_THE_RULE: frozenset[str] = frozenset(
    {
        "tests/test_assets.py",  # defines the forbidden pattern
        "tests/test_publication_hygiene.py",  # this file
        "CONTRIBUTING.md",  # explains the ban to contributors
        "docs/research/2026-08-22-i3-part-b-handoff.md",  # documents this finding
    }
)

_TEXT_SUFFIXES = frozenset(
    {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml", ".cfg", ".ini", ""}
)


def _tracked_text_files() -> list[str]:
    """Repo-relative paths of tracked text files outside the asset tree."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=_REPO_ROOT,
            capture_output=True,
            check=False,
        )
    except OSError:  # pragma: no cover - git absent
        pytest.skip("git is not available, so the tracked set cannot be determined")
    if result.returncode != 0:  # pragma: no cover - not a work tree
        pytest.skip("not a git work tree, so the tracked set cannot be determined")

    paths: list[str] = []
    for raw in result.stdout.decode("utf-8").split("\0"):
        if not raw or raw.startswith(_ALREADY_COVERED):
            continue
        if Path(raw).suffix.lower() not in _TEXT_SUFFIXES:
            continue
        paths.append(raw)
    return sorted(paths)


def test_the_tracked_set_is_not_empty() -> None:
    """Guard the guard: an empty file list would make every check below vacuous."""
    files = _tracked_text_files()
    assert len(files) > 10, (
        f"only {len(files)} tracked text files found outside the asset tree — "
        "the enumeration is probably broken, which would make this suite pass vacuously"
    )


def test_no_tracked_file_names_the_private_source_project() -> None:
    violations: list[str] = []
    for relative in _tracked_text_files():
        if relative in _TEACHES_THE_RULE:
            continue
        path = _REPO_ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in _SOURCE_PROJECT.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            violations.append(f"{relative}:{line}: names the private source project")

    assert not violations, (
        "tracked files naming the private source project:\n"
        + "\n".join(violations)
        + "\n\nIf the file exists to teach or document this rule, add it to "
        "_TEACHES_THE_RULE with a comment saying why. Otherwise remove the reference — "
        "a tracked file is a published file."
    )


def test_the_allowlist_has_no_stale_entries() -> None:
    """An allowlist entry that no longer needs to be there hides a future violation."""
    stale: list[str] = []
    for relative in sorted(_TEACHES_THE_RULE):
        path = _REPO_ROOT / relative
        if not path.is_file():
            stale.append(f"{relative}: allowlisted but does not exist")
            continue
        if not _SOURCE_PROJECT.search(path.read_text(encoding="utf-8")):
            stale.append(f"{relative}: allowlisted but no longer names it")
    assert not stale, "stale _TEACHES_THE_RULE entries:\n" + "\n".join(stale)
