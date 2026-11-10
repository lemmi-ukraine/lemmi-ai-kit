"""The checks of the coherence followup wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_hooks_json_registers_more_than_two_scripts`: hooks json registers more than two scripts
* `test_no_hook_file_names_a_count_that_hooks_json_contradicts`: no hook file names a count that hooks json contradicts
* `test_the_count_scan_flags_the_old_sentences_and_spares_near_misses`: Planted: the three sentences as they stood are reported against three registered hooks. Near-misses: the words that replaced them, a right count, and counts of other things.
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_HOOKS_JSON = "plugins/core/hooks/hooks.json"


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Whitespace folded and lower-cased: lines wrap, and the claims are about words."""
    return " ".join(text.split()).lower()


# ------------------------------------------------------------------ the file the docstring names


# ----------------------------------------------------------- a count of hooks that hooks.json denies

_COUNT_WORDS = {"both": 2, "two": 2, "three": 3, "four": 4}
_COUNTED = re.compile(r"\b(both|two|three|four)\s+(?:hook\s+)?(?:scripts?|hooks?)\b")
_HOOK_FILES = (
    "plugins/core/hooks/gate_learnings_drain.py",
    "plugins/core/hooks/gate_shell_prefix.py",
    "plugins/core/hooks/nudge_learnings_drain.py",
    "plugins/core/README.md",
    "tests/test_hook_registration.py",
)


def _registered() -> list[str]:
    """The distinct hook scripts that hooks.json registers, by file name."""
    found = re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/hooks/(\w+\.py)", _read(_HOOKS_JSON))
    return sorted(set(found))


def _miscounts(text: str, registered: int) -> list[str]:
    """Every count word that stands before `hook(s)` or `script(s)` and is not `registered`."""
    return [
        found[0]
        for found in _COUNTED.finditer(_folded(text))
        if _COUNT_WORDS[found[1]] != registered
    ]


def test_hooks_json_registers_more_than_two_scripts() -> None:
    registered = _registered()
    assert len(registered) >= 3, registered
    for name in registered:
        assert (_REPO_ROOT / "plugins/core/hooks" / name).is_file(), name


def test_no_hook_file_names_a_count_that_hooks_json_contradicts() -> None:
    registered = len(_registered())
    assert len(_HOOK_FILES) == 5
    for path in _HOOK_FILES:
        assert _miscounts(_read(path), registered) == [], path


def test_the_count_scan_flags_the_old_sentences_and_spares_near_misses() -> None:
    """Planted: the three sentences as they stood are reported against three registered hooks.
    Near-misses: the words that replaced them, a right count, and counts of other things."""
    for old, found in (
        ("A test pins that for\n    both hook scripts.", "both hook scripts"),
        ("# the two scripts are each exercised", "two scripts"),
        ("Not a thing these two hooks do", "two hooks"),
        ("the two hook scripts", "two hook scripts"),
    ):
        assert _miscounts(old, 3) == [found], old
    for fine in (
        "A test pins that for each hook script.",
        "# the scripts are each exercised",
        "Not a thing these hooks do",
        "All three hooks may be offered",
        "both options and two projects",
    ):
        assert _miscounts(fine, 3) == [], fine
    # The same words are right when two scripts are registered: the scan reads the count.
    assert _miscounts("both hook scripts", 2) == []


# ------------------------------------------------------------- one agreed rule for a pasted row


# --------------------------------------------------------------------- deferred annotations
