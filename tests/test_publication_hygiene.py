"""The hygiene contract, applied to every tracked file — not just the asset tree.

`test_assets.py` rejects nine patterns, but all five of its scans start at
`assets_root()`. Every top-level tree added since — `docs/`, the community files,
anything future — was unguarded, so a banned pattern could reach a committed path
with nothing checking it. The Part B handoff's own mention of the source project is
exempt on the merits, but nothing verified it: it passed because the scan never
looked.

Two deliberate design choices:

**The patterns are imported, not restated.** Duplicating the nine regexes here would
let the two contracts drift, and a pattern guarded inside `assets/` but not outside
is exactly the gap this file exists to close. One definition, two scopes.

**Scope is tracked files only.** That is the set which becomes public, and it keeps
untracked local scratch out of scope rather than failing a developer's run for files
they never intend to commit. A tracked file is a published file, and this is the gate.
"""

import subprocess
from pathlib import Path

import pytest
from test_assets import _FORBIDDEN  # pyright: ignore[reportPrivateUsage]

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The asset tree has its own scan, with its own allowlist.
_ALREADY_COVERED = "src/lemmi_ai_kit/assets/"

# Files permitted to carry a pattern because they teach, implement, or document the
# rule that bans it — same principle and same shape as test_assets.py's _ALLOWLIST.
# Per-pattern, never blanket: a wholesale exemption hides the next real violation.
_ALLOWLIST: dict[str, tuple[str, ...]] = {
    # Defines the patterns, so its own source necessarily contains them. Only six of
    # the nine self-match: three regexes (/home/\w and the two dated citations) use
    # metacharacters where a literal would be, so they do not match their own source.
    "tests/test_assets.py": (
        "absolute macOS home path",
        "machine-specific host rule",
        "machine-specific console workaround",
        "source-project reference",
        "source-project backup reference",
        # `authorization:\s` and a Windows-normalization comment, per its own note.
        "Windows drive-letter path",
    ),
    # Explains the contract to contributors, so it must quote what it bans.
    "CONTRIBUTING.md": (
        "absolute macOS home path",
        "machine-specific host rule",
        "machine-specific console workaround",
        "source-project reference",
        "source-project backup reference",
    ),
    # The review checklist names the path shapes a reviewer rejects.
    ".github/PULL_REQUEST_TEMPLATE.md": ("absolute macOS home path",),
    # Documents the scan-scope finding that produced this test.
    "docs/research/2026-08-22-i3-part-b-handoff.md": ("source-project reference",),
    # A `"…LICENSE:\n"` assertion message: a literal backslash-n after a colon trips
    # the drive-letter pattern. Same false-positive class test_assets.py allowlists
    # for extract_sessions.py's redaction regexes.
    "tests/test_license.py": ("Windows drive-letter path",),
    # This file, for the same reason — it quotes that message in a comment.
    "tests/test_publication_hygiene.py": ("Windows drive-letter path",),
}

_TEXT_SUFFIXES = frozenset(
    {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml", ".cfg", ".ini"}
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
        raise
    if result.returncode != 0:  # pragma: no cover - not a work tree
        pytest.skip("not a git work tree, so the tracked set cannot be determined")
        raise

    return sorted(
        raw
        for raw in result.stdout.decode("utf-8").split("\0")
        if raw
        and not raw.startswith(_ALREADY_COVERED)
        and Path(raw).suffix.lower() in _TEXT_SUFFIXES
    )


def test_the_tracked_set_is_not_empty() -> None:
    """Guard the guard: an empty file list would make every check below vacuous."""
    files = _tracked_text_files()
    assert len(files) > 10, (
        f"only {len(files)} tracked text files found outside the asset tree — "
        "the enumeration is probably broken, which would make this suite pass vacuously"
    )


def test_no_tracked_file_carries_a_forbidden_pattern() -> None:
    violations: list[str] = []
    for relative in _tracked_text_files():
        allowed = _ALLOWLIST.get(relative, ())
        try:
            text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            # Never skip silently. An unreadable tracked file is precisely the
            # "passed because the scan never looked" failure this test exists for.
            violations.append(
                f"{relative}: could not be scanned ({type(exc).__name__}) — "
                "add it to _TEXT_SUFFIXES' exclusions or fix its encoding"
            )
            continue
        for pattern, why in _FORBIDDEN:
            if why in allowed:
                continue
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                violations.append(f"{relative}:{line}: {why} ({match.group(0)!r})")

    assert not violations, (
        "tracked files carrying a forbidden pattern:\n"
        + "\n".join(violations)
        + "\n\nIf the file exists to teach or document the rule, add that specific "
        "reason to its _ALLOWLIST entry with a comment saying why. Otherwise remove "
        "the reference — a tracked file is a published file."
    )


def test_the_allowlist_has_no_stale_entries() -> None:
    """A dead allowlist entry silently exempts the next real violation."""
    by_reason = {why: pattern for pattern, why in _FORBIDDEN}
    stale: list[str] = []
    for relative, reasons in sorted(_ALLOWLIST.items()):
        path = _REPO_ROOT / relative
        if not path.is_file():
            stale.append(f"{relative}: allowlisted but does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        for reason in reasons:
            pattern = by_reason.get(reason)
            if pattern is None:
                stale.append(f"{relative}: allowlists unknown reason {reason!r}")
            elif not pattern.search(text):
                stale.append(
                    f"{relative}: allowlists {reason!r} but no longer matches it"
                )
    assert not stale, "stale _ALLOWLIST entries:\n" + "\n".join(stale)
