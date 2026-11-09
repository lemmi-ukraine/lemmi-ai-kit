"""The v3 hand-off ledger: six lines that tie a note to its task and to the sessions behind it.

A v3 note (`<!-- handoff-contract: v3 -->` on line 1) carries one line each of `Task:`,
`Sessions:`, `Written:`, `Lessons:`, `Delegation:` and `Safe to close:` in its header block: above
the first `## ` heading, outside comments and fences. The lint checks that each line is there once
and has its form, that the writer is one of the listed sessions, and, when it can read the
project's learnings buffer and changelog, that every lesson title the note names is in the buffer.
That last check is strict only for a note written after the last drain: a drain removes titles,
and the consolidator lints every note after each drain, so an older note gets a note-level message
naming the drain instead of an error.

The `Task:` line holds the task's slug, 2 to 5 words and at most 40 characters, and a v3 note
linted as a file must be named for it: `<YYYY-MM-DD>-<slug>.md`, or `<YYYY-MM-DD>-<slug>--<part>.md`
for a second note of the task that day. A text has no name, so linting text applies no name rule;
the same text linted as a misnamed file is told, which shows the rule runs.

WHAT KEEPS IT HONEST. Every rule fires on a planted defect beside a near miss that must stay
quiet, and each planted note is asserted to differ from the good one, so a plant that changed
nothing cannot pass for a quiet rule. An unlabelled, a v1 and a v2 note pass as they always did
(guards, green before v3 existed), and the same v2 note relabelled v3 draws exactly the six
missing-line findings, which shows the checks ran rather than that they were never reached. The
drain rule is pinned by its boundary pair (written on the drain day, written the day after), by a
drain of 0 entries that must not count, and by the consolidation sequence the consolidator runs.
A missing lesson title is dated unlike every drain and note date, so a date found in a message
can only have come from the drain. The session ids are made-up UUID shapes.
"""

import time
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from lemmi_ai_kit import checks
from lemmi_ai_kit.cli import main

_KEYS = ("Task", "Sessions", "Written", "Lessons", "Delegation", "Safe to close")

# Made up in the shape of a session id; never a real one.
_EARLIER = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
_WRITER = "11111111-2222-4333-8444-555555555555"
_STRANGER = "99999999-8888-4777-8666-555555555555"

_GOOD: dict[str, str] = {
    "Task": "example-task",
    "Sessions": f"{_EARLIER}, {_WRITER}",
    "Written": f"2026-11-10 14:05 by {_WRITER}",
    "Lessons": "none",
    "Delegation": "none, because judgment is the work",
    "Safe to close": "no - pytest still running",
}

_SECTIONS = """## Scope
The one slice. Not the rest.

## Durable anchors
- branch `feature/thing`

## Preconditions
- `git status --short` -> clean tree

## Verification
- `pytest -q` -> 0 failed

## Status
in-progress. The second half is not done.

## Continue
Paste into a new session: `Read the note and follow it.`
Next step: one sentence.

## Orchestrator summary
Done: one thing. Open: one thing.
"""

_TITLE_LINE = "# Hand-off: example-task\n\n"
_SCOPE_BODY = "The one slice. Not the rest.\n"


def _label(version: int) -> str:
    return f"<!-- handoff-contract: v{version} -->"


def _note(
    changed: Mapping[str, str | None] | None = None,
    *,
    version: int = 3,
    extra: str = "",
    sections: str = _SECTIONS,
) -> str:
    """A note at `version`: the good ledger with `changed` applied (None drops a line), then
    `extra`, in the header block above `sections`."""
    values: dict[str, str | None] = dict(_GOOD)
    if changed is not None:
        values.update(changed)
    header = "".join(
        f"{key}: {value}\n" for key, value in values.items() if value is not None
    )
    return f"{_label(version)}\n{_TITLE_LINE}{header}{extra}\n{sections}"


_UNLABELLED = f"{_TITLE_LINE}{_SECTIONS}"
_V1 = f"{_label(1)}\n{_TITLE_LINE}{_SECTIONS}"
_V2 = f"{_label(2)}\n{_TITLE_LINE}{_SECTIONS}"


def _findings(text: str) -> list[checks.LintFinding]:
    return checks.lint_handoff(text, "h.md")


def _messages(text: str) -> list[str]:
    return [finding.message for finding in _findings(text)]


def _line_of(text: str, key: str) -> int:
    return next(
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if line.startswith(f"{key}:")
    )


# --- the table ---------------------------------------------------------------------------------


def test_v3_asks_for_the_v2_sections_and_the_six_ledger_lines_in_order() -> None:
    assert checks.HANDOFF_SECTIONS_BY_VERSION[3] == ("Continue", "Orchestrator summary")
    assert checks.HANDOFF_LINES_BY_VERSION == {3: _KEYS}


# --- a filled note, and one line missing -------------------------------------------------------


def test_a_filled_v3_note_passes() -> None:
    assert _findings(_note()) == []


@pytest.mark.parametrize("key", _KEYS)
def test_a_v3_note_without_one_ledger_line_draws_one_finding_naming_it(
    key: str,
) -> None:
    text = _note({key: None})
    assert text != _note()

    messages = _messages(text)

    assert len(messages) == 1, messages
    assert f"'{key}:'" in messages[0]


# --- the writer --------------------------------------------------------------------------------


def test_a_writer_sessions_does_not_list_is_one_finding_naming_it() -> None:
    text = _note({"Written": f"2026-11-10 14:05 by {_STRANGER}"})

    found = _findings(text)

    assert len(found) == 1, found
    assert _STRANGER in found[0].message
    assert "'Sessions:'" in found[0].message
    assert found[0].line == _line_of(text, "Written")


# --- each value by its form --------------------------------------------------------------------

_VALUES: tuple[tuple[str, str, bool], ...] = (
    ("Task", "example-task", True),
    ("Task", "Example Task", False),
    ("Task", "", False),
    # The writer stays listed, so only the Sessions line itself is judged.
    ("Sessions", _WRITER, True),
    ("Sessions", f"{_EARLIER}, {_WRITER}", True),
    ("Sessions", "", False),
    ("Sessions", f"abcdefg, {_WRITER}", False),
    ("Sessions", f"abcdefgh, {_WRITER}", True),
    ("Sessions", f"{_EARLIER}, , {_WRITER}", False),
    ("Written", f"2026-11-10 14:05 by {_WRITER}", True),
    ("Written", f"by {_WRITER}", False),
    ("Written", f"2026-02-30 14:05 by {_WRITER}", False),
    ("Written", f"2026-11-10 24:05 by {_WRITER}", False),
    ("Safe to close", "yes", True),
    ("Safe to close", "yes - all committed", True),
    ("Safe to close", "no - pytest still running", True),
    ("Safe to close", "no", False),
    ("Safe to close", "no - ", False),
    ("Safe to close", "maybe", False),
    ("Delegation", "none, because judgment is the work", True),
    ("Delegation", "the pin census; the extractor fixture", True),
    ("Delegation", "the pin census", True),
    ("Delegation", "none", False),
    ("Delegation", "", False),
    ("Delegation", "none, because", False),
    ("Delegation", "the pin census;; the extractor fixture", False),
    ("Lessons", "none", True),
    ("Lessons", "not run - drafted for the receiving session", True),
    ("Lessons", "[2026-11-09] a title; [2026-11-10] another; title", True),
    ("Lessons", "not run", False),
    ("Lessons", "[2026-11-09]", False),
    ("Lessons", "[2026-11-09] a title; [2026-11-10]", False),
    ("Lessons", "[2026-02-30] a title", False),
    ("Lessons", "a title [2026-11-09]", False),
)


@pytest.mark.parametrize(
    ("key", "value", "passes"),
    _VALUES,
    ids=[f"{key}={value!r}" for key, value, _ in _VALUES],
)
def test_each_ledger_value_is_judged_by_its_form(
    key: str, value: str, passes: bool
) -> None:
    text = _note({key: value})

    found = _findings(text)

    if passes:
        assert found == []
        return
    assert text != _note(), "the planted value is the good one"
    assert len(found) == 1, found
    assert f"'{key}:'" in found[0].message
    assert not found[0].note
    assert found[0].line == _line_of(text, key)


def test_a_session_listed_twice_is_a_note_and_never_an_error() -> None:
    text = _note({"Sessions": f"{_EARLIER}, {_WRITER}, {_EARLIER}"})

    found = _findings(text)

    assert len(found) == 1, found
    assert found[0].note
    assert _EARLIER in found[0].message


def test_without_the_ledgers_a_lesson_title_is_judged_by_its_form_only() -> None:
    assert _findings(_note({"Lessons": "[2026-11-01] not in any buffer"})) == []


# --- the task's slug ---------------------------------------------------------------------------

# Three words and 40 characters: the longest slug. One letter more is one too many.
_FORTY = f"{'a' * 12}-{'b' * 13}-{'c' * 13}"
_SLUGS: tuple[tuple[str, str, bool], ...] = (
    ("one word", "task", False),
    ("two words", "example-task", True),
    ("five words", "one-two-three-four-five", True),
    ("six words", "one-two-three-four-five-six", False),
    ("40 characters", _FORTY, True),
    ("41 characters", f"{_FORTY}c", False),
    ("upper case", "Example-Task", False),
)


@pytest.mark.parametrize(
    ("slug", "passes"),
    [(slug, passes) for _, slug, passes in _SLUGS],
    ids=[name for name, _, _ in _SLUGS],
)
def test_the_task_line_holds_a_slug_of_two_to_five_words_and_at_most_40_characters(
    slug: str, passes: bool
) -> None:
    assert len(_FORTY) == 40
    text = _note({"Task": slug})

    found = _findings(text)

    if passes:
        assert found == []
        return
    assert len(found) == 1, found
    assert "'Task:'" in found[0].message
    assert not found[0].note
    assert found[0].line == _line_of(text, "Task")
    # The finding states the rule's numbers, whatever its words: the word counts and the limit.
    assert all(number in found[0].message for number in ("2", "5", "40")), found[0]


def test_a_task_value_of_many_characters_is_judged_in_linear_time() -> None:
    """The slug's pattern runs on the whole value before the length is compared, so these values
    time the pattern itself: a run of 40,000 spaces between two words, a word of 40,000 letters
    that ends in a character no slug holds, and 20,000 words."""
    spaces = " " * 40_000
    values = (f"one{spaces}two", f"{'a' * 40_000}!", "-".join(["a"] * 20_000))
    texts = [_note({"Task": value}) for value in values]

    started = time.perf_counter()
    found = [_findings(text) for text in texts]
    took = time.perf_counter() - started

    assert [[f.line for f in each] for each in found] == [
        [_line_of(text, "Task")] for text in texts
    ]
    assert took < 1.0, f"{took:.1f} s for three task values of about 40,000 characters"


# --- older notes -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text", [_UNLABELLED, _V1, _V2], ids=["unlabelled", "v1", "v2"]
)
def test_an_older_note_without_ledger_lines_passes_as_it_always_did(text: str) -> None:
    assert _findings(text) == []


def test_ledger_lines_in_a_v2_note_are_never_judged() -> None:
    text = _note({"Task": "Example Task", "Safe to close": "maybe"}, version=2)

    assert _findings(text) == []


def test_the_same_v2_note_relabelled_v3_draws_the_six_missing_line_findings() -> None:
    relabelled = _V2.replace(_label(2), _label(3), 1)
    assert relabelled != _V2

    messages = _messages(relabelled)

    assert len(messages) == len(_KEYS), messages
    for key in _KEYS:
        assert sum(f"'{key}:'" in message for message in messages) == 1, key


# --- a line counts once, and only in the header block ------------------------------------------

_PLACEMENTS: dict[str, Callable[[str], str]] = {
    "twice": lambda key: _note(extra=f"{key}: {_GOOD[key]}\n"),
    "below the first heading": lambda key: _note(
        {key: None},
        sections=_SECTIONS.replace(_SCOPE_BODY, f"{_SCOPE_BODY}{key}: {_GOOD[key]}\n"),
    ),
    "inside a comment": lambda key: _note(
        {key: None}, extra=f"<!--\n{key}: {_GOOD[key]}\n-->\n"
    ),
    "inside a fence": lambda key: _note(
        {key: None}, extra=f"```\n{key}: {_GOOD[key]}\n```\n"
    ),
}


@pytest.mark.parametrize("placement", sorted(_PLACEMENTS))
@pytest.mark.parametrize("key", _KEYS)
def test_a_line_repeated_or_outside_the_header_block_is_one_finding_for_it(
    key: str, placement: str
) -> None:
    text = _PLACEMENTS[placement](key)
    assert text != _note()
    assert f"{key}: {_GOOD[key]}" in text, "the line was planted nowhere"

    messages = _messages(text)

    assert len(messages) == 1, messages
    assert f"'{key}:'" in messages[0]


# --- the parse function ------------------------------------------------------------------------


def test_the_parse_function_returns_the_six_values_in_the_order_of_the_table() -> None:
    parsed = checks.parse_handoff_ledger(_note())

    assert parsed == _GOOD
    assert tuple(parsed) == _KEYS


@pytest.mark.parametrize("placement", sorted(_PLACEMENTS))
@pytest.mark.parametrize("key", _KEYS)
def test_the_parse_function_has_no_value_for_a_line_outside_the_header_block_or_repeated(
    key: str, placement: str
) -> None:
    expected: dict[str, str | None] = dict(_GOOD)
    expected[key] = None

    assert checks.parse_handoff_ledger(_PLACEMENTS[placement](key)) == expected


def test_the_parse_function_has_no_value_for_an_absent_line() -> None:
    parsed = checks.parse_handoff_ledger(_V2)

    assert parsed == dict.fromkeys(_KEYS)


def test_the_session_ids_are_read_in_order_each_once() -> None:
    listed = f"{_EARLIER}, {_WRITER}, {_EARLIER}"

    assert checks.handoff_session_ids(listed) == (_EARLIER, _WRITER)
    assert checks.handoff_session_ids(None) == ()


def test_header_lines_of_many_spaces_are_read_in_linear_time() -> None:
    """A pattern with a lazy group before `\\s*$` took about 10 seconds on one line of 40,000
    spaces (the drain-nudge hook's test records it); these lines are read with `startswith`,
    `strip` and patterns that cannot backtrack over a run of spaces."""
    spaces = " " * 40_000
    pathological = (
        f"Task:{spaces}x\n"
        f"{spaces}\n"
        f"Sessions:{spaces},{spaces}x\n"
        f"Written: 2026-11-10{spaces}14:05 by{spaces}x y\n"
        f"Lessons: [2026-11-10]{spaces}x;{spaces}\n"
        f"Delegation: none{spaces}x\n"
        f"Safe to close: no -{spaces}\n"
    )
    text = f"{_label(3)}\n{_TITLE_LINE}{pathological}\n{_SECTIONS}"

    started = time.perf_counter()
    parsed = checks.parse_handoff_ledger(text)
    found = checks.lint_handoff(text, "h.md")
    took = time.perf_counter() - started

    assert parsed["Task"] == "x"
    assert {key for key in _KEYS if any(f"'{key}:'" in f.message for f in found)} == {
        "Task",
        "Sessions",
        "Written",
        "Delegation",
        "Safe to close",
    }
    assert took < 1.0, f"{took:.1f} s for seven header lines of 40,000 spaces"


# --- lesson titles against the buffer and the last drain ---------------------------------------

_HELD = "[2026-11-10] t"
# Dated unlike every drain and note date below, so a date in a message comes from the drain.
_GONE = "[2026-11-01] gone"

_BUFFER_HEAD = "# Project Learnings\n\n## Common Pitfalls\n"


def _buffer(title: str) -> str:
    return (
        f"{_BUFFER_HEAD}\n### {title}\n- **Context**: c\n- **Finding**: f\n"
        "- **Impact**: i\n- **Category**: pitfall\n"
    )


_CHANGELOG_HEAD = "# AI Infrastructure Changelog\n"


def _drain(day: str, drained: str) -> str:
    return (
        f"\n## {day}\n\n### CONSOLIDATION: a drain\n- **What:** w\n"
        f"- **Drained:** {drained}\n- **Why:** y\n- **Files:** f\n"
        "- **Affected workflows:** none\n"
    )


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def _project(
    tmp_path: Path,
    *,
    buffer: str | None = None,
    changelog: str | None = _CHANGELOG_HEAD + _drain("2026-11-09", "1 entries"),
) -> Path:
    """A project whose buffer holds `_HELD` and whose last drain was on 2026-11-09, unless told
    otherwise; None leaves a file out."""
    (tmp_path / ".ai").mkdir()
    _write(
        tmp_path / ".ai" / "learnings.md", _buffer(_HELD) if buffer is None else buffer
    )
    if changelog is not None:
        _write(tmp_path / ".ai" / "ai-changelog.md", changelog)
    return tmp_path


def _hand_off(root: Path, written: str, lessons: str) -> Path:
    text = _note({"Written": f"{written} 14:05 by {_WRITER}", "Lessons": lessons})
    return _write(root / ".ai" / "handoffs" / f"{written}-example-task.md", text)


def test_a_title_the_buffer_holds_passes(tmp_path: Path) -> None:
    root = _project(tmp_path)

    assert checks.lint_handoff_file(_hand_off(root, "2026-11-10", _HELD), root) == []


def test_a_title_the_buffer_lacks_fails_a_note_written_after_the_last_drain(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)

    found = checks.lint_handoff_file(_hand_off(root, "2026-11-10", _GONE), root)

    assert len(found) == 1, found
    assert not found[0].note
    assert _GONE in found[0].message


@pytest.mark.parametrize("written", ["2026-11-09", "2026-11-08"])
def test_a_title_the_buffer_lacks_is_a_note_naming_the_drain_for_an_older_note(
    tmp_path: Path, written: str
) -> None:
    root = _project(tmp_path)

    found = checks.lint_handoff_file(_hand_off(root, written, _GONE), root)

    assert len(found) == 1, found
    assert found[0].note
    assert _GONE in found[0].message
    assert "2026-11-09" in found[0].message


@pytest.mark.parametrize(
    "changelog",
    [None, _CHANGELOG_HEAD + _drain("2026-11-09", "0 entries")],
    ids=["no changelog", "only a drain of 0 entries"],
)
def test_with_no_drain_recorded_a_title_the_buffer_lacks_is_an_error(
    tmp_path: Path, changelog: str | None
) -> None:
    # Written before the day of the drain of 0, so reading that entry as a drain would make
    # this a note: the error shows it was not read as one.
    root = _project(tmp_path, changelog=changelog)

    found = checks.lint_handoff_file(_hand_off(root, "2026-11-08", _GONE), root)

    assert len(found) == 1, found
    assert not found[0].note
    assert _GONE in found[0].message


@pytest.mark.parametrize("kind", ["missing", "a directory"])
def test_a_title_list_with_an_unreadable_buffer_is_one_error_that_says_so(
    tmp_path: Path, kind: str
) -> None:
    root = _project(tmp_path)
    buffer = root / ".ai" / "learnings.md"
    buffer.unlink()
    if kind == "a directory":
        buffer.mkdir()

    lessons = f"{_HELD}; {_GONE}"
    found = checks.lint_handoff_file(_hand_off(root, "2026-11-10", lessons), root)

    assert len(found) == 1, found
    assert not found[0].note
    assert "cannot be read" in found[0].message
    assert _GONE not in found[0].message, "worded as a title the buffer lacks"


def test_an_unreadable_buffer_is_no_finding_for_a_note_that_names_no_title(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    (root / ".ai" / "learnings.md").unlink()

    assert checks.lint_handoff_file(_hand_off(root, "2026-11-10", "none"), root) == []


def test_the_named_file_run_and_the_folder_run_report_the_title_alike(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)
    where = _hand_off(root, "2026-11-10", _GONE).relative_to(root).as_posix()

    assert main(["lint", "handoffs", where, "--project", str(root)]) == 1
    named = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(where + ":")
    ]
    assert main(["lint", "handoffs", "--project", str(root)]) == 1
    folder = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(where + ":")
    ]

    assert len(named) == 1, named
    assert _GONE in named[0]
    assert named == folder


def test_the_consolidation_sequence_keeps_an_older_note_green_and_fails_a_later_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The consolidator drains the buffer, then lints every target."""
    drained = "[2026-11-08] t"
    root = _project(tmp_path, buffer=_buffer(drained), changelog=_CHANGELOG_HEAD)
    first = _hand_off(root, "2026-11-08", drained).relative_to(root).as_posix()

    # 1. The title is in the buffer and nothing was drained: everything passes.
    assert main(["lint", "--project", str(root)]) == 0
    capsys.readouterr()

    # 2. A drain on 2026-11-09 moves the title out: the note is told, and does not fail.
    _write(root / ".ai" / "learnings.md", _BUFFER_HEAD)
    _write(
        root / ".ai" / "ai-changelog.md",
        _CHANGELOG_HEAD + _drain("2026-11-09", "1 entries"),
    )
    assert main(["lint", "--project", str(root)]) == 0
    told = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(first + ":")
    ]
    assert len(told) == 1, told
    assert ": ERROR " not in told[0]
    assert "2026-11-09" in told[0]

    # 3. A note written after the drain names the drained title: that note fails, alone.
    second = _hand_off(root, "2026-11-10", drained).relative_to(root).as_posix()
    assert main(["lint", "--project", str(root)]) == 1
    errors = [
        line for line in capsys.readouterr().out.splitlines() if ": ERROR " in line
    ]
    assert errors
    assert all(line.startswith(second + ":") for line in errors), errors


# --- the file name -----------------------------------------------------------------------------

_DAY = "2026-11-10"
# The longest part of a name; one letter more is one too many.
_PART = "abcdefghijkl"
_NAMES: tuple[tuple[str, str, bool], ...] = (
    ("the date and the slug", f"{_DAY}-example-task.md", True),
    ("a part", f"{_DAY}-example-task--return.md", True),
    ("a part of 12 characters", f"{_DAY}-example-task--{_PART}.md", True),
    ("a part of 13 characters", f"{_DAY}-example-task--{_PART}m.md", False),
    ("a part in upper case", f"{_DAY}-example-task--Return.md", False),
    ("another slug", f"{_DAY}-other-task.md", False),
    ("no date", "example-task.md", False),
    ("not a calendar date", "2026-02-30-example-task.md", False),
)


def _named(root: Path, name: str, text: str) -> Path:
    return _write(root / ".ai" / "handoffs" / name, text)


@pytest.mark.parametrize(
    ("name", "passes"),
    [(name, passes) for _, name, passes in _NAMES],
    ids=[label for label, _, _ in _NAMES],
)
def test_a_v3_note_linted_as_a_file_is_named_for_the_slug_on_its_task_line(
    tmp_path: Path, name: str, passes: bool
) -> None:
    assert len(_PART) == 12
    root = _project(tmp_path)

    found = checks.lint_handoff_file(_named(root, name, _note()), root)

    if passes:
        assert found == []
        return
    assert len(found) == 1, found
    assert not found[0].note
    assert found[0].line == _line_of(_note(), "Task")
    day = _DAY if name.startswith(_DAY) else "<YYYY-MM-DD>"
    assert f"'{day}-example-task.md'" in found[0].message, (
        "the expected name is not named"
    )


@pytest.mark.parametrize(
    "text", [_UNLABELLED, _V1, _V2], ids=["unlabelled", "v1", "v2"]
)
def test_an_older_note_is_not_judged_by_its_file_name(
    tmp_path: Path, text: str
) -> None:
    root = _project(tmp_path)

    assert checks.lint_handoff_file(_named(root, "notes.md", text), root) == []


def test_a_text_is_not_judged_by_a_name_and_the_same_text_as_a_misnamed_file_is(
    tmp_path: Path,
) -> None:
    """The shipped template and stub are linted as text, under names no slug fits."""
    root = _project(tmp_path)

    as_text = checks.lint_handoff(_note(), "notes.md")
    as_file = checks.lint_handoff_file(_named(root, "notes.md", _note()), root)

    assert as_text == []
    assert len(as_file) == 1, as_file
    assert "'<YYYY-MM-DD>-example-task.md'" in as_file[0].message


_FAILING_TASK_LINES: dict[str, str] = {
    "missing": _note({"Task": None}),
    "malformed": _note({"Task": "Example Task"}),
    "twice": _note(extra=f"Task: {_GOOD['Task']}\n"),
}


@pytest.mark.parametrize("kind", sorted(_FAILING_TASK_LINES))
def test_a_note_whose_task_line_fails_gets_no_second_finding_for_its_name(
    tmp_path: Path, kind: str
) -> None:
    root = _project(tmp_path)
    name = f"{_DAY}-other-task.md"

    found = checks.lint_handoff_file(
        _named(root, name, _FAILING_TASK_LINES[kind]), root
    )
    # The twin: a sound Task line in a file of the same name is told about the name.
    twin = checks.lint_handoff_file(_named(root, name, _note()), root)

    assert len(found) == 1, found
    assert "'Task:'" in found[0].message
    assert ".md'" not in found[0].message, "the name was judged against a failing line"
    assert len(twin) == 1, twin
    assert f"'{_DAY}-example-task.md'" in twin[0].message
