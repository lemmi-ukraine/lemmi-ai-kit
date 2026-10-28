"""Unit tests for the user-corrections sweep and for its link to the extractor's skip list.

The sweep reads the `USER:` blocks the extractor writes into sessions/<id>.md. Two lists decide
which of those blocks are injected machinery rather than the operator speaking:
HARNESS_USER_PREFIXES in extract_sessions.py (the interaction digest) and SKIP_PREFIX in
sweep_user_corrections.py (the sweep). They are duplicated, because the scripts run as
stand-alone files and cannot import each other, and the comment above HARNESS_USER_PREFIXES says
they must move together. The parity test below is what enforces that.

Pure stdlib, no network. Run with:

    uv run python -m pytest "${CLAUDE_SKILL_DIR}/scripts/test_sweep_user_corrections.py"
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent


def _load(name):
    """Import a sibling script BY PATH, so the two scripts never have to import each other."""
    spec = importlib.util.spec_from_file_location(
        f"{name}_under_test", _SCRIPTS / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ex = _load("extract_sessions")
sweep = _load("sweep_user_corrections")

# The machinery prefixes both lists carried before the four below were added.
_ORIGINAL_PREFIXES = (
    "<",
    "Base directory for this skill",
    "ARGUMENTS:",
    "[Request interrupted",
    "Caveat:",
)
# The four harness-injected user events, as the first line a real transcript carries.
_INJECTED_PREFIXES = (
    "# Workflow authoring reference",
    "This session is being continued from a previous conversation",
    "Another Claude session sent a message",
    "Your response above was stopped by a safety classifier",
)
# Synthetic full turns that begin with each of them. Every body carries a word the sweep looks
# for, so a turn that is not skipped surfaces as a correction candidate.
_INJECTED_TURNS = {
    "workflow-authoring header": "\n\n".join(
        [
            "# Workflow authoring reference",
            "Read this before you change a script. Never rely on memory; fix gaps instead.",
        ]
    ),
    "session-continuation notice": "\n\n".join(
        [
            "This session is being continued from a previous conversation that ran out "
            "of context.",
            "Summary: fix the build, do not revert the migration.",
        ]
    ),
    "peer-message notice": "\n\n".join(
        [
            "Another Claude session sent a message:",
            "please do not change the schema, fix the test again",
        ]
    ),
    "safety-classifier stop notice": (
        "Your response above was stopped by a safety classifier — this is not a tool or "
        "API error. Do not produce that content again, even reworded."
    ),
}


def _unshared(first, second):
    """The prefixes that sit in exactly one of two skip lists."""
    return set(first) ^ set(second)


def test_the_two_skip_lists_are_equal_as_sets():
    both = (ex.HARNESS_USER_PREFIXES, sweep.SKIP_PREFIX)
    assert all(both), "two empty lists would compare equal and prove nothing"
    unshared = _unshared(*both)
    assert not unshared, (
        f"only one of HARNESS_USER_PREFIXES / SKIP_PREFIX has {sorted(unshared)}: "
        "the two lists must move together"
    )
    for skip_list in both:
        assert len(set(skip_list)) == len(skip_list), (
            "a duplicate entry is a stale copy"
        )


@pytest.mark.parametrize("lacking", ["extractor", "sweep"])
def test_the_parity_check_names_a_prefix_missing_from_either_list(lacking, monkeypatch):
    """Known positive: remove one prefix from one list and the comparison must name it."""
    dropped = "Caveat:"
    module, name = {
        "extractor": (ex, "HARNESS_USER_PREFIXES"),
        "sweep": (sweep, "SKIP_PREFIX"),
    }[lacking]
    assert dropped in getattr(module, name)
    monkeypatch.setattr(
        module, name, tuple(p for p in getattr(module, name) if p != dropped)
    )
    assert dropped in _unshared(ex.HARNESS_USER_PREFIXES, sweep.SKIP_PREFIX)


@pytest.mark.parametrize("prefix", [*_ORIGINAL_PREFIXES, *_INJECTED_PREFIXES])
def test_each_known_prefix_is_in_both_skip_lists(prefix):
    assert prefix in ex.HARNESS_USER_PREFIXES
    assert prefix in sweep.SKIP_PREFIX


def _sweep(tmp_path, turns):
    """Run the real sweep over one transcript whose USER blocks are `turns`."""
    sessions = tmp_path / "retro" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    lines = []
    for turn in turns:
        lines.append(f"USER: {turn}")
        lines.append("ASSISTANT: ok")
    # Bytes, so the file is the same on every OS: write_text would translate each newline.
    (sessions / "abcd1234-0000.md").write_bytes(
        ("\n".join(lines) + "\n").encode("utf-8")
    )
    return sweep.sweep(tmp_path / "retro")


@pytest.mark.parametrize("kind", sorted(_INJECTED_TURNS))
def test_the_sweep_skips_each_harness_injected_turn(kind, tmp_path):
    assert _sweep(tmp_path, [_INJECTED_TURNS[kind]]) == []


def test_the_sweep_flags_an_operator_correction_between_injected_turns(tmp_path):
    """Known positive for the skip tests: the sweep does see a correction, and the skip is by
    what a block starts with, not by where it sits."""
    turns = [*_INJECTED_TURNS.values(), "no, that is wrong, fix it again"]
    hits = _sweep(tmp_path, turns)
    assert len(hits) == 1
    assert hits[0].startswith("[abcd1234:")
    assert "that is wrong" in hits[0]


def test_without_the_four_prefixes_the_sweep_flags_every_injected_turn(
    tmp_path, monkeypatch
):
    """Known positive: with the list as it was before the four were added, each injected turn
    IS a candidate. So an empty result above is the skip working, not a sweep that cannot see
    these turns."""
    before = tuple(p for p in sweep.SKIP_PREFIX if p not in _INJECTED_PREFIXES)
    monkeypatch.setattr(sweep, "SKIP_PREFIX", before)
    hits = _sweep(tmp_path, list(_INJECTED_TURNS.values()))
    assert len(hits) == len(_INJECTED_TURNS)
