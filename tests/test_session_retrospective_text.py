"""The session-retrospective skill cannot contradict itself about where its report lives.

Phase 6 told the reader to `git add` the report because `.ai/retrospectives/` is "NOT
gitignored", and the paragraph right after it said the folder IS gitignored, that the report
is local scratch, and that nobody should stage it. Both arrived in one commit, so no edit ever
chose between them and the reader got opposite instructions from adjacent paragraphs. Three
more lines still spoke of a committed report. The settled decision is local scratch, never
staged.

The scan reads every text file of the skill, not only `SKILL.md`: the stale claim also lived
in a reference and in an extractor comment, and a scan of one file would have passed.
`test_the_scan_covers_every_file_of_the_skill` states that surface in numbers, and
`test_the_stale_phrase_scan_flags_what_it_is_meant_to_flag` fires the scan at planted
positives before its silence on the real files is trusted.
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "session-retrospective"

# Every suffix a text file of the skill has today. A file with any other suffix fails
# `test_the_scan_covers_every_file_of_the_skill`, so a new kind of file is a decision made
# here rather than a silent gap in what is read.
_TEXT_SUFFIXES: frozenset[str] = frozenset({".md", ".py"})

# The files that held the stale claim. The scan must contain them by name, or it is not
# measuring the thing it is named for.
_FILES_THAT_HELD_THE_CLAIM: tuple[str, ...] = (
    "SKILL.md",
    "references/extractor-output-schema.md",
    "scripts/extract_sessions.py",
)

# Matched against whitespace-collapsed text, so a phrase that wraps across a line is still seen.
_STALE_PHRASES: dict[str, re.Pattern[str]] = {
    "says the report folder is not gitignored": re.compile(
        r"\bnot gitignored\b", re.IGNORECASE
    ),
    "tells the reader to stage the report": re.compile(
        r"`git add` it\b", re.IGNORECASE
    ),
    "speaks of a committed report": re.compile(
        r"(?<![A-Za-z])committed report\b", re.IGNORECASE
    ),
}

# The one claim that must stay: the folder is gitignored. `\s+` spans the line the source wraps.
_GITIGNORED_CLAIM = re.compile(r"`\.ai/retrospectives/`\s+is\s+\*\*gitignored\*\*")


def _skill_files() -> list[Path]:
    return sorted(
        path
        for path in _SKILL_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _relative(path: Path) -> str:
    return path.relative_to(_SKILL_DIR).as_posix()


def _collapsed(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _stale_hits(text: str) -> list[str]:
    """The rule itself, over a string, so it can be exercised on input the skill lacks."""
    flat = _collapsed(text)
    return [name for name, pattern in _STALE_PHRASES.items() if pattern.search(flat)]


def test_the_scan_covers_every_file_of_the_skill() -> None:
    """The scan surface in numbers: every file the skill ships is read, none is skipped."""
    everything = _skill_files()
    unread = [
        _relative(path) for path in everything if path.suffix not in _TEXT_SUFFIXES
    ]
    assert not unread, (
        f"{len(unread)} of {len(everything)} files of the skill have a suffix this test "
        f"does not read: {unread}. Add the suffix to _TEXT_SUFFIXES if the file is text."
    )
    names = {_relative(path) for path in everything}
    missing = [name for name in _FILES_THAT_HELD_THE_CLAIM if name not in names]
    assert not missing, f"the scan of {len(names)} files does not contain {missing}"


def test_no_file_of_the_skill_says_the_report_is_committed_or_not_ignored() -> None:
    offenders = {
        _relative(path): hits
        for path in _skill_files()
        if (hits := _stale_hits(path.read_text(encoding="utf-8")))
    }
    assert not offenders, (
        "the skill contradicts its settled decision (the report folder is gitignored "
        "local scratch that nobody stages):\n"
        + "\n".join(f"  {name}: {', '.join(hits)}" for name, hits in offenders.items())
    )


def test_the_skill_still_says_the_report_folder_is_gitignored() -> None:
    """Positive control: the decision the stale lines contradicted is still stated."""
    text = _collapsed((_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"))
    assert _GITIGNORED_CLAIM.search(text), (
        "SKILL.md no longer says that `.ai/retrospectives/` is **gitignored**; the "
        "absence checks above would then pass for the wrong reason"
    )


def test_the_stale_phrase_scan_flags_what_it_is_meant_to_flag() -> None:
    """Fire the scan at planted positives (including one that wraps a line) and negatives."""
    planted_positives = [
        "`.ai/retrospectives/` is NOT gitignored but has never been committed",
        "The report must survive the session - `git add` it.",
        "the committed report contains only findings",
        "the folder is NOT\ngitignored",
    ]
    for text in planted_positives:
        assert _stale_hits(text), f"the scan missed a planted positive: {text!r}"

    clean = [
        "`.ai/retrospectives/` is **gitignored** and the report is local scratch",
        "do **not** `git add` the report",
        "three reports went uncommitted",
        "an uncommitted report is lost with the session",
    ]
    for text in clean:
        assert _stale_hits(text) == [], f"the scan flagged clean text: {text!r}"
