"""The hygiene contract, applied to every file git would publish -- not just assets.

`test_assets.py` defines the forbidden patterns, but every one of its scans starts
at `assets_root()`. Every top-level tree added since -- `docs/`, the community
files, anything future -- was unguarded, so a banned pattern could reach a
committed path with nothing checking it. The Part B handoff's own mention of the
source project is exempt on the merits, but nothing verified it: it passed because
the scan never looked.

**This docstring states no counts, deliberately.** It used to say `test_assets.py`
"rejects nine patterns" and referred to "the nine regexes"; `_FORBIDDEN` had by then
grown to ten, and the tenth -- the skill-script path rule -- was the one nobody had
counted. A hand-written number going stale inside the module whose entire subject is
a check that stopped looking is the failure describing itself. Replacing nine with
ten would only have reset the clock, so the relationship the prose used to assert is
asserted by `test_every_imported_pattern_is_carried_over` instead, where it is
recomputed on every run.

Three deliberate design choices:

**The patterns are imported, not restated.** Duplicating them would let the two
contracts drift, and a pattern guarded inside `assets/` but not outside is exactly
the gap this file exists to close. One definition, two scopes.

**Scope is everything git would publish: tracked files, plus untracked files that
are not ignored.** `--others --exclude-standard` pulls in the second group on
purpose. An untracked, unignored file is one `git add .` away from being published,
and catching it before that commit is worth more than sparing a developer a failure
on a scratch file -- which `.gitignore` already exempts, and which is where scratch
belongs. (An earlier version of this note claimed the scope was tracked files only.
It never was; the enumeration below has always passed `--others`.)

**The drive-letter pattern is narrowed rather than exempted per file.** See
`_TIGHTENED_DRIVE_LETTER` -- excusing a whole pattern for a whole file would blind
that file to real violations of it, which is the same failure this test exists to
catch.
"""

import re
import subprocess
from pathlib import Path

import pytest
from test_assets import (
    _FORBIDDEN as _ASSET_FORBIDDEN,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The asset and plugin skill trees have their own scan, with their own allowlist.
_ALREADY_COVERED = (
    "plugins/core/src/lemmi_ai_kit/assets/",
    "plugins/core/skills/",
    "plugins/python/skills/",
)

_DRIVE_LETTER_REASON = "Windows drive-letter path"

# A locally TIGHTENED drive-letter pattern, substituted for the imported one.
#
# The shared pattern is `[A-Za-z]:\\?[A-Za-z]`, which cannot tell `C:\Users` from a
# source escape like `"…LICENSE:\n"` — both are letter-colon-backslash-letter. Inside
# `assets/` that costs little: the allowlist there is three curated files. Across the
# whole tracked tree it would need an exemption for every Python file with a `:\n` in
# a string, and a per-file pattern exemption blinds that file to REAL paths — a file
# excused for `":\n"` would also be excused a genuine `C:\Users\someone`. That is the
# same "passes because the scan stopped looking" failure this file exists to catch, so
# the pattern is narrowed instead of the files being excused.
#
# The narrowing: require at least two word characters after the separator, so a real
# path segment (`\Users`) qualifies and a one-character escape (`\n"`) does not.
#
# The shared pattern in test_assets.py deserves the same treatment. Not changed here,
# because editing it would fork one contract into two — flagged for whoever owns that
# file next.
_TIGHTENED_DRIVE_LETTER = re.compile(r"[A-Za-z]:\\{1,2}[A-Za-z]\w+")

_FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (_TIGHTENED_DRIVE_LETTER if why == _DRIVE_LETTER_REASON else pattern, why)
    for pattern, why in _ASSET_FORBIDDEN
)

# Files permitted to carry a pattern because they teach, implement, or document the
# rule that bans it — same principle as test_assets.py's _ALLOWLIST. Per-pattern,
# never blanket, and kept minimal: every entry is a file it would be wrong to rewrite.
_ALLOWLIST: dict[str, tuple[str, ...]] = {
    # Defines the patterns, so its own source necessarily contains them -- but only
    # those written as literals. The rest (/home/\w, the two dated-citation regexes,
    # the skill-script path rule, and under the tightened rule above the drive-letter
    # one) use a metacharacter where a literal would be, so they do not match their
    # own source and must not be listed here. That is a rule, not a tally: it
    # classifies the next pattern too, and
    # test_the_allowlist_has_no_stale_entries fails on an entry that stops matching.
    "tests/test_assets.py": (
        "absolute macOS home path",
        "machine-specific host rule",
        "machine-specific console workaround",
        "source-project reference",
        "source-project backup reference",
    ),
    # The repo's own scaffolded AGENTS.md -- this project dogfooding its own template
    # (I3 DoD 11). It states the rule against absolute paths, so it must quote the shapes
    # it bans, exactly as `assets/templates/AGENTS.md` does.
    #
    # Worth knowing why this entry is needed at all: the source template is ALREADY
    # allowlisted for this same reason in `test_assets.py`, but that scan starts at
    # `assets_root()` and this one deliberately excludes it (`_ALREADY_COVERED`). So one
    # file's content is legitimate at its template path and a violation at its scaffolded
    # path, and only running the scaffold on this repo reveals it. Any adopter who runs
    # `kit-setup` and has a comparable scan will meet the same thing.
    "AGENTS.md": ("absolute macOS home path",),
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
    # Documents the finding that produced the skill-script pattern: its evidence table
    # records where each upstream script actually lives, which is the banned shape. The
    # table IS the finding, so redacting it would remove the evidence, not a slip.
    "docs/research/2026-08-22-i2-portability-triage.md": (
        "hard-coded skill-script path (use ${CLAUDE_SKILL_DIR})",
    ),
    # Enumerates what the extraction STRIPPED, so its evidence list necessarily quotes
    # the shapes the contract bans -- a hard-coded linter invocation and a machine-specific
    # rule. Redacting them would delete the finding, not a slip.
    "docs/research/2026-08-23-extraction-window-debt-measured.md": (
        "hard-coded skill-script path (use ${CLAUDE_SKILL_DIR})",
        "machine-specific host rule",
    ),
    # This file quotes `C:\Users\someone` in the comment explaining the narrowing.
    "tests/test_publication_hygiene.py": (_DRIVE_LETTER_REASON,),
}

_TEXT_SUFFIXES = frozenset(
    {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml", ".cfg", ".ini"}
)


def _tracked_text_files() -> list[str]:
    """Repo-relative paths of published text files outside the asset/skill trees."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=_REPO_ROOT,
            capture_output=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - git absent
        pytest.fail(
            f"git is not available, so the tracked set cannot be checked: {exc}"
        )
    if result.returncode != 0:  # pragma: no cover - not a work tree
        pytest.fail("not a git work tree, so the tracked set cannot be checked")

    return sorted(
        raw
        for raw in result.stdout.decode("utf-8").split("\0")
        if raw
        and (_REPO_ROOT / raw).is_file()
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
                "exclude its suffix from _TEXT_SUFFIXES or fix its encoding"
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


def test_the_tightened_pattern_still_catches_real_paths() -> None:
    """The narrowing must not have narrowed away the thing it is guarding against."""
    for real in (r"C:\Users\someone", r"D:\projects\thing", r"C:\\Users\\x"):
        assert _TIGHTENED_DRIVE_LETTER.search(real), f"{real!r} should be caught"
    for escape in (r'"out of sync with LICENSE:\n"', r'"authorization:\s"'):
        assert not _TIGHTENED_DRIVE_LETTER.search(escape), (
            f"{escape!r} is a source escape, not a path"
        )


def test_every_imported_pattern_is_carried_over() -> None:
    """The local set is the imported set with exactly one substitution.

    This is what the docstring used to assert as a count, moved somewhere it gets
    recomputed. A pattern added to `test_assets.py` and dropped here -- by a bad
    merge, or by someone rebuilding this tuple by hand -- would leave the whole repo
    surface unguarded against it while both files still looked maintained.
    """
    assert [why for _, why in _FORBIDDEN] == [why for _, why in _ASSET_FORBIDDEN], (
        "the local pattern set no longer mirrors test_assets.py._FORBIDDEN; it is "
        "built by comprehension over it, so a difference here means the import or "
        "the substitution below has been edited into something else"
    )

    substituted = [
        why
        for (local, why), (shared, _) in zip(_FORBIDDEN, _ASSET_FORBIDDEN, strict=True)
        if local is not shared
    ]
    assert substituted == [_DRIVE_LETTER_REASON], (
        f"expected exactly one locally substituted pattern "
        f"({_DRIVE_LETTER_REASON!r}), found {substituted!r}. Every other pattern "
        "must be the shared object itself, or the two contracts have forked."
    )
