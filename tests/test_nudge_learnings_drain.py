"""The drain-due nudge prints one line when the learnings buffer is due, and otherwise nothing.

`plugins/core/hooks/nudge_learnings_drain.py` runs when a session opens. It is off until a project
holds `.ai/drain-nudge-hook.json` with `{"enabled": true}`. Switched on, it counts the entries of
`.ai/learnings.md`, dates the last drain from `.ai/ai-changelog.md`, and prints one line when the
buffer holds more than 25 entries, or holds any and the last drain is 7 or more days old.

The hook is registered for every adopter of Core, so what these tests pin is mostly silence: no
switch file, a switch that says false, input it cannot read, files it cannot read, a changelog that
records no drain. Each silent case sits beside the same project made due and switched on, which
prints, so the probe is shown able to see what it reports as absent.

Two instruments agree wherever the hook reuses a measure the kit already has: the entry count
against what `lint learnings --list-entries` prints, and the last drain against the lint's own
changelog parser. The two numbers the hook acts on are read from the skills that state them, and the
reader that reads them is fired at a planted copy that states other numbers.
"""

import ast
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast
from unittest import mock

import pytest

from lemmi_ai_kit import checks

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / "plugins" / "core" / "hooks" / "nudge_learnings_drain.py"
_SKILLS = _REPO_ROOT / "plugins" / "core" / "skills"
_TASK_LEARNINGS = _SKILLS / "task-learnings" / "SKILL.md"
_CONSOLIDATOR = _SKILLS / "learning-consolidator" / "SKILL.md"
_README = _REPO_ROOT / "plugins" / "core" / "README.md"

# The day every in-process run is made on. A run in a separate process cannot be told the day, so
# those runs build their fixtures from the real one and accept a day of slack.
_TODAY = date(2026, 3, 31)
_SWITCH_NAME = "drain-nudge-hook.json"
_ON = '{"enabled": true}'
_ROUTE = "run /lemmi-ai-kit-core:learning-consolidator"
_AT_LEAST = chr(0x2265)


@cache
def _hook() -> ModuleType:
    """The hook, loaded once from its file (it is a script, not a package)."""
    assert _HOOK.is_file(), f"the hook script does not exist: {_HOOK}"
    spec = importlib.util.spec_from_file_location("nudge_learnings_drain", _HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------------------ the fixtures


def _buffer(entries: int) -> str:
    """A learnings buffer holding `entries` entries, each in the format the lint reads."""
    body = "".join(
        f"### [2026-03-01] Entry {number}\n- **Context**: c\n- **Finding**: f\n"
        "- **Impact**: i\n- **Category**: pattern\n\n"
        for number in range(entries)
    )
    return f"# Learnings\n\n## Pattern Discoveries\n\n{body}"


def _entry(kind: str, title: str, drained: str | None = None) -> str:
    """One changelog entry that passes every other check; `drained` follows `- **Drained:**`."""
    marker = [] if drained is None else [f"- **Drained:** {drained}".rstrip()]
    lines = [f"### {kind}: {title}", "- **What:** w", *marker, "- **Why:** y"]
    return "\n".join([*lines, "- **Files:** f", "- **Affected workflows:** none", ""])


def _ledger(*days: tuple[str, str]) -> str:
    """A changelog with one `## <date>` section per `(date, entries)` pair, as given."""
    return "# AI Infrastructure Changelog\n" + "".join(
        f"\n## {day}\n\n{entries}" for day, entries in days
    )


def _ago(days: int, today: date = _TODAY) -> str:
    return (today - timedelta(days=days)).isoformat()


def _drained(days: int, count: str = "4 entries", today: date = _TODAY) -> str:
    """A changelog whose one drain was `days` days before `today`."""
    return _ledger((_ago(days, today), _entry("CONSOLIDATION", "a drain", count)))


def _project(
    root: Path,
    *,
    entries: int = 100,
    ledger: str | None = None,
    switch: str | bytes | None = _ON,
) -> Path:
    """A project folder: the buffer, and optionally a changelog and a switch file."""
    ai = root / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    (ai / "learnings.md").write_text(_buffer(entries), encoding="utf-8", newline="\n")
    if ledger is not None:
        (ai / "ai-changelog.md").write_text(ledger, encoding="utf-8", newline="\n")
    if switch is not None:
        data = switch if isinstance(switch, bytes) else switch.encode("utf-8")
        (ai / _SWITCH_NAME).write_bytes(data)
    return root


def _payload(project: Path) -> bytes:
    """What the harness hands a SessionStart hook on stdin."""
    return json.dumps(
        {
            "hook_event_name": "SessionStart",
            "source": "startup",
            "session_id": "s",
            "cwd": str(project),
        }
    ).encode("utf-8")


def _decide(
    project: Path,
    raw: bytes | None = None,
    *,
    environ: dict[str, str] | None = None,
    today: date = _TODAY,
) -> str:
    """What the hook prints, called in this process the way `main` calls it."""
    decide = cast(Callable[..., str], _hook().decide)
    env = {"CLAUDE_PROJECT_DIR": str(project)} if environ is None else environ
    return decide(_payload(project) if raw is None else raw, env, today=today)


def _reply(out: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(out))


def _line(out: str) -> str:
    """The one line a nudge puts into the session, from a SessionStart reply and nothing else."""
    reply = _reply(out)
    assert set(reply) == {"hookSpecificOutput"}, reply
    inner = cast(dict[str, Any], reply["hookSpecificOutput"])
    assert set(inner) == {"hookEventName", "additionalContext"}, inner
    assert inner["hookEventName"] == "SessionStart"
    return str(inner["additionalContext"])


def _expected(entries: int, days: int) -> str:
    return f"intake at {entries} entries, last drain {days} days ago -> {_ROUTE}"


def _run_as_script(
    stdin: bytes, project: Path | None
) -> "subprocess.CompletedProcess[bytes]":
    """The real contract, as the harness runs it: a process that reads stdin and prints JSON."""
    env = {
        key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        [sys.executable, "-B", str(_HOOK)],
        input=stdin,
        capture_output=True,
        env=env,
        cwd=project,
        timeout=60,
        check=False,
    )


# ------------------------------------------------------------- silent until a project turns it on


@pytest.mark.parametrize(
    "switch",
    [None, "{}", '{"enabled": false}'],
    ids=["no switch file", "an empty object", "enabled is false"],
)
def test_a_project_that_has_not_switched_it_on_is_silent_even_when_everything_is_due(
    switch: str | None, tmp_path: Path
) -> None:
    project = _project(tmp_path, entries=100, ledger=_drained(30), switch=switch)

    assert _decide(project) == ""

    # The control: the same project, switched on, is due and says so.
    (project / ".ai" / _SWITCH_NAME).write_text(_ON, encoding="utf-8")
    assert _line(_decide(project)) == _expected(100, 30)


_NOT_ASCII = chr(0x442) + chr(0x430)

# (id, the switch file's bytes or text, what the one warning must say about it)
_UNUSABLE: list[tuple[str, str | bytes, str]] = [
    ("not JSON", '{"enabled": tru', "not valid JSON"),
    ("an empty file", "", "not valid JSON"),
    ("not UTF-8", b"\xff\xfe\xfd\x00garbage", "not UTF-8"),
    ("a list", "[true]", "must be a JSON object"),
    ("a string", '"yes"', "must be a JSON object"),
    ("a bare true", "true", "must be a JSON object"),
    (
        "an unknown key",
        '{"enabled": true, "threshold": 5}',
        "unknown key(s): threshold",
    ),
    ("a string for enabled", '{"enabled": "true"}', "enabled must be true or false"),
    ("a number for enabled", '{"enabled": 1}', "enabled must be true or false"),
    ("null for enabled", '{"enabled": null}', "enabled must be true or false"),
    (
        "text that is not ASCII",
        '{"enabled": "' + _NOT_ASCII + '"}',
        "enabled must be true or false",
    ),
    (
        "a key that is not ASCII",
        '{"enabled": true, "' + _NOT_ASCII + '": 1}',
        "unknown key(s)",
    ),
    ("nested too deeply", "[" * 100000, "nested too deeply"),
]


@pytest.mark.parametrize(
    ("content", "reason"),
    [(content, reason) for _, content, reason in _UNUSABLE],
    ids=[name for name, _, _ in _UNUSABLE],
)
def test_an_unusable_switch_gives_one_warning_and_no_context(
    content: str | bytes, reason: str, tmp_path: Path
) -> None:
    project = _project(tmp_path, entries=100, ledger=_drained(30), switch=content)

    out = _decide(project)

    reply = _reply(out)
    assert set(reply) == {"systemMessage"}, reply
    message = str(reply["systemMessage"])
    assert ".ai/drain-nudge-hook.json" in message and reason in message, message
    out.encode("ascii")  # a reply that is not ASCII raises here

    # The control: the project is due, so a usable switch makes it say so.
    (project / ".ai" / _SWITCH_NAME).write_text(_ON, encoding="utf-8")
    assert _line(_decide(project)) == _expected(100, 30)


def test_a_switch_path_that_is_a_folder_is_unusable_and_not_off(tmp_path: Path) -> None:
    project = _project(tmp_path, entries=100, ledger=_drained(30), switch=None)
    (project / ".ai" / _SWITCH_NAME).mkdir()

    reply = _reply(_decide(project))

    assert set(reply) == {"systemMessage"}, reply
    assert "cannot be read" in str(reply["systemMessage"])


@pytest.mark.parametrize(
    ("error", "unusable"),
    [
        (FileNotFoundError(), False),
        (NotADirectoryError(), False),
        (PermissionError(), True),
        (IsADirectoryError(), True),
        (OSError(5, "input/output error"), True),
    ],
    ids=[
        "no file",
        "a parent that is a file",
        "no permission",
        "a folder",
        "another error",
    ],
)
def test_only_a_path_that_is_not_there_means_off_and_any_other_failure_is_unusable(
    error: OSError, unusable: bool
) -> None:
    """Which error a missing switch raises depends on the platform (a parent that is a file raises
    `NotADirectoryError` on POSIX), so the answer is pinned for each error and not for the platform."""
    load_switch = cast(Callable[[str], tuple[bool, list[str]]], _hook().load_switch)

    with mock.patch.object(_hook(), "open", side_effect=error, create=True):
        enabled, problems = load_switch("anywhere")

    assert enabled is False
    assert bool(problems) is unusable, problems
    if unusable:
        assert type(error).__name__ in problems[0]


def test_a_switch_file_with_a_byte_order_mark_switches_the_hook_on(
    tmp_path: Path,
) -> None:
    """An editor on Windows writes one, and the lint's own reader drops it, so the switch must too."""
    switch = b"\xef\xbb\xbf" + _ON.encode("utf-8")
    project = _project(tmp_path, entries=100, ledger=_drained(30), switch=switch)

    assert _line(_decide(project)) == _expected(100, 30)


# ----------------------------------------------------------------------- when it speaks


@pytest.mark.parametrize(("entries", "speaks"), [(25, False), (26, True)])
def test_more_than_25_entries_speak_and_25_do_not(
    entries: int, speaks: bool, tmp_path: Path
) -> None:
    """The pressure arm alone: the last drain is a day old, so the age arm cannot be speaking."""
    project = _project(tmp_path, entries=entries, ledger=_drained(1))

    out = _decide(project)

    assert (out != "") is speaks
    if speaks:
        assert _line(out) == _expected(entries, 1)


@pytest.mark.parametrize(
    ("days", "speaks"), [(0, False), (6, False), (7, True), (8, True), (30, True)]
)
def test_a_last_drain_7_days_old_or_older_speaks_when_the_buffer_holds_anything(
    days: int, speaks: bool, tmp_path: Path
) -> None:
    """The age arm alone: three entries are far from the pressure arm."""
    project = _project(tmp_path, entries=3, ledger=_drained(days))

    out = _decide(project)

    assert (out != "") is speaks
    if speaks:
        assert _line(out) == _expected(3, days)


def test_an_empty_buffer_is_silent_however_old_the_last_drain(tmp_path: Path) -> None:
    empty = _project(tmp_path / "empty", entries=0, ledger=_drained(30))
    one = _project(tmp_path / "one", entries=1, ledger=_drained(30))

    assert _decide(empty) == ""
    # The control: one entry and the same drain.
    assert _line(_decide(one)) == _expected(1, 30)


def test_a_buffer_that_was_never_drained_is_silent_on_the_age_arm(
    tmp_path: Path,
) -> None:
    other = _ledger((_ago(30), _entry("INFRA-MODIFIED", "something else", "5 entries")))
    for name, ledger in (("none", None), ("blank", ""), ("other types", other)):
        project = _project(tmp_path / name, entries=3, ledger=ledger)
        assert _decide(project) == "", name

    control = _project(tmp_path / "drained", entries=3, ledger=_drained(30))
    assert _line(_decide(control)) == _expected(3, 30)


def test_a_fat_buffer_with_no_drain_recorded_still_speaks_and_says_so(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, entries=30, ledger=None)

    assert (
        _line(_decide(project))
        == f"intake at 30 entries, no drain recorded -> {_ROUTE}"
    )


def test_a_drain_dated_in_the_future_never_prints_a_negative_age(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, entries=30, ledger=_drained(-3))

    assert _line(_decide(project)) == _expected(30, 0)


# ------------------------------------------------------------ dating the last drain

_REMOVED_NOTHING = _entry("CONSOLIDATION", "promoted only", "0 entries")
_A_DRAIN = _entry("CONSOLIDATION", "a drain", "4 entries")
_UNMARKED = _entry("CONSOLIDATION", "written before the marker")
_FENCED_EXAMPLE = (
    f"```markdown\n## {_ago(1)}\n\n### CONSOLIDATION: an example\n"
    "- **Drained:** 9 entries\n```\n"
)
_UNFENCED_EXAMPLE = _FENCED_EXAMPLE.replace("```markdown\n", "").replace("```\n", "")
# Headings in the shapes where a regex and a string test can part: a heading of two spaces, and a
# title that opens with a space, which is no type tag. Neither dates a drain.
_ODD_HEADINGS = (
    "\n##  \n\n###  CONSOLIDATION: a title that opens with a space\n"
    "- **Drained:** 5 entries\n"
    f"\n## {_ago(3)}\n\n###  CONSOLIDATION: another\n- **Drained:** 5 entries\n"
)


def _unreadable_count_ledger(value: str) -> str:
    return _ledger(
        (_ago(10), _entry("CONSOLIDATION", "no readable count", value)),
        (_ago(40), _A_DRAIN),
    )


def _newer_than_a_drain(count: str) -> str:
    """A changelog whose newest entry, two days old, states `count`, above an older drain."""
    return _ledger(
        (_ago(2), _entry("CONSOLIDATION", "newer", count)), (_ago(30), _A_DRAIN)
    )


# (id, the changelog, how many days before today the last drain is, or None for none)
_LEDGERS: list[tuple[str, str, int | None]] = [
    ("one drain", _ledger((_ago(30), _A_DRAIN)), 30),
    (
        "a newer drain that removed nothing is skipped",
        _ledger((_ago(2), _REMOVED_NOTHING), (_ago(30), _A_DRAIN)),
        30,
    ),
    (
        "a newer entry without the line counts as drained",
        _ledger((_ago(10), _UNMARKED), (_ago(40), _A_DRAIN)),
        10,
    ),
    (
        "only drains that removed nothing",
        _ledger((_ago(2), _REMOVED_NOTHING), (_ago(9), _REMOVED_NOTHING)),
        None,
    ),
    ("no changelog entries at all", "# AI Infrastructure Changelog\n", None),
    (
        "the newest date wins whatever order the sections are in",
        _ledger((_ago(30), _A_DRAIN), (_ago(5), _A_DRAIN)),
        5,
    ),
    (
        "two entries on one day, the second removed nothing",
        _ledger((_ago(5), _A_DRAIN + "\n" + _REMOVED_NOTHING)),
        5,
    ),
    (
        "an entry under a heading that is not a date",
        "# AI Infrastructure Changelog\n\n## Notes\n\n" + _A_DRAIN,
        None,
    ),
    (
        "an entry under a date that is not a real day",
        _ledger(("2026-02-30", _A_DRAIN)),
        None,
    ),
    (
        "an entry above the first heading",
        "# AI Infrastructure Changelog\n\n" + _A_DRAIN,
        None,
    ),
    (
        "an undated drain beside a dated one",
        _ledger((_ago(30), _A_DRAIN)) + "\n## Notes\n\n" + _A_DRAIN,
        30,
    ),
    (
        "a fenced example is neither a section nor an entry",
        _ledger((_ago(30), _REMOVED_NOTHING + _FENCED_EXAMPLE)),
        None,
    ),
    (
        "the same example without its fence is a drain, so the probe can see",
        _ledger((_ago(30), _REMOVED_NOTHING + _UNFENCED_EXAMPLE)),
        1,
    ),
    (
        "a heading of two spaces and a title that opens with a space",
        _ledger((_ago(30), _A_DRAIN)) + _ODD_HEADINGS,
        30,
    ),
]


def _oracle(text: str) -> date | None:
    """The same question asked of the lint's own parser: the second instrument."""
    found: list[date] = []
    for block in checks.parse_blocks(text):
        day = block.heading_date()
        for entry in block.entries:
            tag = checks.TYPE_TAG_RE.match(entry.title)
            if day is None or tag is None or tag.group(1) != checks.DRAIN_ENTRY_TYPE:
                continue
            value = checks.fields_of(entry.body).get(checks.DRAINED_FIELD)
            if (
                value is None
                or checks.DRAINED_COUNT_RE.match(value.strip()) is None
                or int(value.split()[0]) > 0
            ):
                found.append(day)
    return max(found, default=None)


def _last_drain(text: str) -> date | None:
    return cast(Callable[[str], date | None], _hook().last_drain)(text)


@pytest.mark.parametrize(
    ("text", "days"),
    [(text, days) for _, text, days in _LEDGERS],
    ids=[name for name, _, _ in _LEDGERS],
)
def test_the_last_drain_is_the_newest_entry_that_counts_as_one(
    text: str, days: int | None
) -> None:
    expected = None if days is None else _TODAY - timedelta(days=days)

    assert _last_drain(text) == expected
    assert _oracle(text) == expected  # the lint's parser, asked the same question


@pytest.mark.parametrize(
    "value", ["", "some entries", "-3 entries", "1.5 entries", "none"]
)
def test_a_drained_line_with_no_readable_count_counts_as_drained(value: str) -> None:
    text = _unreadable_count_ledger(value)

    assert _last_drain(text) == _TODAY - timedelta(days=10)
    assert _oracle(text) == _TODAY - timedelta(days=10)


@pytest.mark.parametrize("value", ["1 entry", "360 entries", "007 entries"])
def test_a_count_above_zero_dates_the_drain_and_zero_does_not(value: str) -> None:
    assert _last_drain(_newer_than_a_drain(value)) == _TODAY - timedelta(days=2)
    assert _last_drain(_newer_than_a_drain("0 entries")) == _TODAY - timedelta(days=30)


@pytest.mark.parametrize("kind", sorted(checks.CHANGELOG_TYPES - {"CONSOLIDATION"}))
def test_an_entry_of_another_type_never_dates_a_drain(kind: str) -> None:
    text = _ledger(
        (_ago(2), _entry(kind, "another type", "5 entries")), (_ago(30), _A_DRAIN)
    )

    assert _last_drain(text) == _TODAY - timedelta(days=30)


def test_a_line_of_many_spaces_is_judged_in_linear_time() -> None:
    """The lint's pattern for a heading, `^## (.+?)\\s*$`, took about 10 seconds on a heading line
    that holds 40,000 spaces (measured once, on one machine): the whole timeout of this hook. The
    hook tests headings with `startswith`, so the same lines cost nothing."""
    spaces = " " * 40_000
    pathological = f"## {spaces}x\n### {spaces}x\n- **{spaces}\n{spaces}x\n"
    text = _ledger((_ago(30), _A_DRAIN + pathological))

    started = time.perf_counter()
    found = _last_drain(text)
    took = time.perf_counter() - started

    assert found == _TODAY - timedelta(days=30)
    assert took < 1.0, f"{took:.1f} s for four lines of 40,000 spaces"


def test_a_changelog_with_windows_line_endings_and_a_byte_order_mark_reads_the_same(
    tmp_path: Path,
) -> None:
    # The date heading is the first line, so a byte order mark left in front of it would hide it.
    text = f"## {_ago(30)}\n\n{_A_DRAIN}"
    crlf = text.replace("\n", "\r\n")
    project = _project(tmp_path, entries=3)
    path = project / ".ai" / "ai-changelog.md"
    path.write_bytes(b"\xef\xbb\xbf" + crlf.encode("utf-8"))

    assert _last_drain(crlf) == _TODAY - timedelta(days=30)
    assert _oracle(checks.read_text(path)) == _TODAY - timedelta(days=30)
    assert _line(_decide(project)) == _expected(3, 30)


# ------------------------------------------------------------- counting the buffer

# (id, the buffer, the entries it holds). Every shape is one the lint's count and the hook's
# count could disagree on, so the number is asserted as well as the agreement.
_BUFFERS: list[tuple[str, str, int]] = [
    (
        "plain",
        "# L\n\n## P\n\n### [2026-03-01] a\nbody\n\n### [2026-03-02] b\nbody\n",
        2,
    ),
    (
        "a heading inside a fence counts, as list-entries counts it",
        "### a\n```\n### b\n```\n### c\n",
        3,
    ),
    ("deeper, indented and glued headings do not", "### a\n#### b\n  ### c\n###d\n", 1),
    ("windows line endings", "### a\r\nbody\r\n### b\r\n", 2),
    ("no newline at the end", "### a\n### b", 2),
    ("an empty file", "", 0),
    ("a heading with nothing after the marker", "### \n### x\n", 2),
]


@pytest.mark.parametrize(
    ("text", "entries"),
    [(text, entries) for _, text, entries in _BUFFERS],
    ids=[name for name, _, _ in _BUFFERS],
)
def test_the_entry_count_equals_what_list_entries_prints(
    text: str, entries: int
) -> None:
    first = checks.inventory(text, "buffer")[0]
    match = re.search(r"entries=(\d+)", first)
    assert match is not None, first

    assert int(match.group(1)) == entries  # the lint's instrument
    assert cast(Callable[[str], int], _hook().count_entries)(text) == entries


_FILES: dict[str, bytes] = {
    "a byte order mark and windows line endings": b"\xef\xbb\xbf"
    + b"".join(b"### [2026-03-01] e%d\r\nbody\r\n" % n for n in range(30)),
    "a byte that is not UTF-8": b"".join(
        b"### [2026-03-01] e%d \xff\nbody\n" % n for n in range(30)
    ),
}


@pytest.mark.parametrize("name", sorted(_FILES))
def test_a_buffer_file_is_decoded_as_the_lint_decodes_it(
    name: str, tmp_path: Path
) -> None:
    project = _project(tmp_path, ledger=_drained(1))
    path = project / ".ai" / "learnings.md"
    path.write_bytes(_FILES[name])
    counted = cast(Callable[[str], int], _hook().count_entries)(checks.read_text(path))

    assert counted == 30
    assert _line(_decide(project)) == _expected(30, 1)


# ----------------------------------------------------------------------- the two numbers


def _item(text: str, lead: str) -> str:
    """The list item whose first line starts with `lead`, folded: it runs to the next line in
    column 0. A lead that is not found, or found twice, fails: a clause that moved is a test to
    update, never a clause to stop reading."""
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(lead)]
    assert len(starts) == 1, f"{len(starts)} lines start with {lead!r}"
    item = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        item.append(line)
    return " ".join("\n".join(item).split())


def _stated(item: str, pattern: str, where: str, *, required: bool = True) -> list[int]:
    found = re.findall(pattern, item)
    assert len(found) <= 1, f"{where} states {pattern!r} {len(found)} times"
    assert found or not required, f"{where} does not state {pattern!r}"
    return [int(number) for number in found]


def _thresholds(task_learnings: str, consolidator: str) -> dict[str, list[int]]:
    """Every place the two skills state the numbers: the entry count and the days."""
    check = _item(task_learnings, "4. **Buffer-pressure check")
    cadence = _item(consolidator, "0. **Cadence guard**")
    return {
        "entries": _stated(
            check, r"holds \*\*> (\d+) entries\*\*", "the buffer-pressure check"
        )
        + _stated(cadence, r"the >(\d+) NOTE", "the cadence guard", required=False),
        "days": _stated(
            check,
            r"\*\*" + _AT_LEAST + r" (\d+) days old\*\*",
            "the buffer-pressure check",
        )
        + _stated(
            cadence,
            "the last drain is " + _AT_LEAST + r"(\d+) days old",
            "the cadence guard",
        ),
    }


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _readme_thresholds(readme: str) -> dict[str, list[int]]:
    """The numbers the README's section on this hook states, folded, from its heading to the next."""
    lines = readme.split("\n")
    heading = "### The drain-nudge hook"
    assert heading in lines, f"the README has no {heading!r} section"
    found: list[str] = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith(("## ", "### ")):
            break
        found.append(line)
    section = " ".join("\n".join(found).split())
    where = "the README's section on the hook"
    return {
        "entries": _stated(section, r"more than (\d+) entries", where),
        "days": _stated(section, r"(\d+) or more days old", where),
    }


def test_the_thresholds_equal_the_numbers_the_skills_and_the_readme_state() -> None:
    stated = _thresholds(_read(_TASK_LEARNINGS), _read(_CONSOLIDATOR))
    in_readme = _readme_thresholds(_read(_README))
    hook = _hook()

    assert {name: set(numbers) for name, numbers in stated.items()} == {
        "entries": {cast(int, hook.PRESSURE_ABOVE)},
        "days": {cast(int, hook.DUE_AFTER_DAYS)},
    }
    assert in_readme == {
        "entries": [cast(int, hook.PRESSURE_ABOVE)],
        "days": [cast(int, hook.DUE_AFTER_DAYS)],
    }
    # The surface, in numbers: the days are stated in both skills, the entry count at least once.
    assert len(stated["days"]) == 2 and len(stated["entries"]) >= 1, stated


_PLANTED_CHECK = f"""\
4. **Buffer-pressure check (REQUIRED, mechanical):** the same lint prints the entry count.
   If the buffer holds **> 30 entries** OR the last drain is
   **{_AT_LEAST} 14 days old** (the newest `CONSOLIDATION` entry), surface one line.
"""
_PLANTED_CADENCE = f"""\
0. **Cadence guard** - count intake entries. Proceed when intake > 0 AND the last drain
   is {_AT_LEAST}14 days old. Cadence: so the >30 NOTE fires in ~5 days.
"""


_PLANTED_README = """\
## Hooks

### The drain-nudge hook

It prints when the buffer holds more than 30 entries, or holds any and the last drain
is 14 or more days old.

### Registration
"""


def test_the_threshold_reader_sees_a_planted_copy_that_states_other_numbers() -> None:
    planted = _thresholds(_PLANTED_CHECK, _PLANTED_CADENCE)

    assert planted == {"entries": [30, 30], "days": [14, 14]}
    assert _readme_thresholds(_PLANTED_README) == {"entries": [30], "days": [14]}
    # A hook still holding 25 and 7 would disagree with this copy: the guard has something to flag.
    assert {name: set(numbers) for name, numbers in planted.items()} != {
        "entries": {25},
        "days": {7},
    }


def test_the_threshold_reader_fails_loudly_when_a_clause_stops_stating_a_number() -> (
    None
):
    near_miss = _PLANTED_CHECK.replace("**> 30 entries**", "**more than 30 entries**")

    with pytest.raises(AssertionError, match="does not state"):
        _thresholds(near_miss, _PLANTED_CADENCE)
    with pytest.raises(AssertionError, match="lines start with"):
        _thresholds("no such item\n", _PLANTED_CADENCE)
    with pytest.raises(AssertionError, match="does not state"):
        _readme_thresholds(_PLANTED_README.replace("more than 30", "over 30"))
    with pytest.raises(AssertionError, match="no '### The drain-nudge hook' section"):
        _readme_thresholds("## Hooks\n")


# ------------------------------------------------------- the line, as the hook and the README quote it

# Numbers the printed line holds once each, so that a quoted copy of the line can be read back
# from the printed one by swapping them for the placeholders the copy uses.
_ENTRIES_MARK = 777
_DAYS_MARK = 888


def _printed_line() -> str:
    """The line the hook prints for a buffer that is due, from the hook's own function."""
    nudge_line = cast(
        Callable[[int, date | None, date], str | None], _hook().nudge_line
    )
    line = nudge_line(_ENTRIES_MARK, _TODAY - timedelta(days=_DAYS_MARK), _TODAY)
    assert line is not None, "a buffer this large is due, so the hook must speak"
    for mark in (_ENTRIES_MARK, _DAYS_MARK):
        assert line.count(str(mark)) == 1, f"{mark} is not in the line once: {line!r}"
    return line


def _quoted_form(entries: str, days: str) -> str:
    """The printed line with its two numbers replaced by the placeholders a copy of it uses."""
    return (
        _printed_line()
        .replace(str(_ENTRIES_MARK), entries)
        .replace(str(_DAYS_MARK), days)
    )


def _quotes(text: str, form: str) -> bool:
    """Whether `text` holds `form` exactly once as a whole phrase, whitespace folded (a quoted
    line may wrap). A longer name that starts with it, a renamed command, is not a quote."""
    folded = " ".join(text.split())
    whole = r"(?<![\w-])" + re.escape(" ".join(form.split())) + r"(?![\w-])"
    return len(re.findall(whole, folded)) == 1


def test_the_line_the_hook_and_the_readme_quote_is_the_line_it_prints() -> None:
    """Every test that compares the reply with `_ROUTE` pins the printed line. The hook's
    docstring and the README each quote that line with placeholders: they are read back from
    the printed line, so a command renamed in the code and not in the prose is reported."""
    assert _quotes(_read(_README), _quoted_form("N", "D"))
    docstring = _hook().__doc__
    assert docstring is not None, "the hook has no docstring"
    assert _quotes(docstring, _quoted_form("{N}", "{D}"))


def test_the_quoted_form_is_read_from_the_printed_line_and_flags_a_planted_copy() -> (
    None
):
    printed = _printed_line()
    assert printed == (
        f"intake at {_ENTRIES_MARK} entries, last drain {_DAYS_MARK} days ago -> {_ROUTE}"
    )
    form = _quoted_form("N", "D")
    assert form == f"intake at N entries, last drain D days ago -> {_ROUTE}"
    # Planted: a copy that names another skill, another wording, or no line at all.
    assert not _quotes(
        f"`{form.replace('learning-consolidator', 'consolidator')}`", form
    )
    assert not _quotes(form.replace("last drain", "last drained"), form)
    assert not _quotes("no such line", form)
    # Planted: a rename that keeps the start of the command is a longer name, not the line.
    assert not _quotes(f"`{form}r`", form)
    assert not _quotes(f"`{form}-v2`", form)
    # Near-misses: a wrapped copy is the same line, and so is one inside a longer paragraph.
    assert _quotes(form.replace(" -> ", "\n-> "), form)
    assert _quotes(f"before `{form}`. after", form)
    # A copy that stands twice is a clause that moved, not one quote.
    assert not _quotes(f"{form} and again {form}", form)


# What the hook reads out of the files is read the way the lint reads them: the patterns it holds
# are the lint's own, and a pattern the hook adds is listed here as its own.
_COPIED_FROM_THE_LINT = (
    "FENCE_RE",
    "DATE_HEADING_RE",
    "TYPE_TAG_RE",
    "FIELD_RE",
    "DRAINED_COUNT_RE",
)
_THE_HOOKS_OWN = ("ENTRY_RE",)


def _drifted(hook: object, lint: object, names: tuple[str, ...]) -> list[str]:
    def pattern(owner: object, name: str) -> str:
        return cast(re.Pattern[str], getattr(owner, name)).pattern

    return [name for name in names if pattern(hook, name) != pattern(lint, name)]


def test_the_patterns_copied_from_the_lint_equal_the_lints() -> None:
    hook = _hook()
    held = sorted(
        name for name, value in vars(hook).items() if isinstance(value, re.Pattern)
    )

    assert set(_COPIED_FROM_THE_LINT).isdisjoint(
        _THE_HOOKS_OWN
    )  # two surfaces, one owner each
    assert held == sorted((*_COPIED_FROM_THE_LINT, *_THE_HOOKS_OWN)), held
    assert _drifted(hook, checks, _COPIED_FROM_THE_LINT) == []
    assert hook.DRAIN_ENTRY_TYPE == checks.DRAIN_ENTRY_TYPE
    assert hook.DRAINED_FIELD == checks.DRAINED_FIELD


def test_the_drift_check_flags_a_planted_pattern_and_spares_an_identical_one() -> None:
    same = SimpleNamespace(**{name: re.compile("x") for name in _COPIED_FROM_THE_LINT})
    other = SimpleNamespace(**{name: re.compile("x") for name in _COPIED_FROM_THE_LINT})
    other.TYPE_TAG_RE = re.compile("y")

    assert _drifted(same, same, _COPIED_FROM_THE_LINT) == []
    assert _drifted(other, same, _COPIED_FROM_THE_LINT) == ["TYPE_TAG_RE"]


# ------------------------------------------------------------- input and files it cannot use

_UNREADABLE_INPUT: dict[str, bytes] = {
    "empty stdin": b"",
    "not JSON": b"not json at all",
    "bytes that are not UTF-8": b"\xff\xfe\xfd\x00garbage",
    "truncated JSON": b'{"hook_event_name": "SessionStart", "cwd": "/x"',
    "a list": b"[]",
    "a string": b'"text"',
    "null": b"null",
    "nested too deeply": b"[" * 100000,
}


@pytest.mark.parametrize("name", sorted(_UNREADABLE_INPUT))
def test_input_the_hook_cannot_read_is_silence_and_not_an_error(
    name: str, tmp_path: Path
) -> None:
    project = _project(tmp_path, ledger=_drained(30))

    # The control comes first: the project is due and switched on, and the environment names it,
    # so the only thing left to make this silent is the payload.
    assert _line(_decide(project)) == _expected(100, 30)
    assert _decide(project, _UNREADABLE_INPUT[name]) == ""


@pytest.mark.parametrize(
    "cwd",
    [None, "", 123, ["x"], "a" + chr(0) + "b"],
    ids=["no cwd", "an empty cwd", "a number", "a list", "a NUL in the path"],
)
def test_a_payload_without_a_usable_working_directory_is_silent(
    cwd: object, tmp_path: Path
) -> None:
    project = _project(tmp_path, ledger=_drained(30))
    body: dict[str, Any] = {"hook_event_name": "SessionStart"}
    if cwd is not None:
        body["cwd"] = cwd

    assert _decide(project, json.dumps(body).encode("utf-8"), environ={}) == ""
    # The control: the same call with the project's own folder as the working directory.
    assert _line(_decide(project, _payload(project), environ={})) == _expected(100, 30)


def test_the_environment_names_the_project_before_the_payload_does(
    tmp_path: Path,
) -> None:
    due = _project(tmp_path / "due", ledger=_drained(30))
    quiet = _project(tmp_path / "quiet", entries=3, ledger=_drained(1))

    assert _decide(due, _payload(quiet), environ={"CLAUDE_PROJECT_DIR": str(due)}) != ""
    assert (
        _decide(quiet, _payload(due), environ={"CLAUDE_PROJECT_DIR": str(quiet)}) == ""
    )


def test_a_buffer_that_is_missing_or_a_folder_is_silent(tmp_path: Path) -> None:
    missing = _project(tmp_path / "missing", ledger=_drained(30))
    (missing / ".ai" / "learnings.md").unlink()
    folder = _project(tmp_path / "folder", ledger=_drained(30))
    (folder / ".ai" / "learnings.md").unlink()
    (folder / ".ai" / "learnings.md").mkdir()
    fine = _project(tmp_path / "fine", ledger=_drained(30))

    assert _decide(missing) == ""
    assert _decide(folder) == ""
    assert _line(_decide(fine)) == _expected(100, 30)  # the control


@pytest.mark.parametrize("how", ["missing", "a folder"])
def test_a_changelog_that_cannot_be_read_leaves_only_the_pressure_arm(
    how: str, tmp_path: Path
) -> None:
    small = _project(tmp_path / "small", entries=3)
    big = _project(tmp_path / "big", entries=30)
    if how == "a folder":
        for project in (small, big):
            (project / ".ai" / "ai-changelog.md").mkdir()

    assert _decide(small) == ""
    assert _line(_decide(big)) == f"intake at 30 entries, no drain recorded -> {_ROUTE}"


def _main_out(raw: bytes, project: Path) -> str:
    """What `main` prints for `raw` on stdin, run in this process."""
    out = io.StringIO()
    with (
        mock.patch.object(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw))),
        mock.patch.object(sys, "stdout", out),
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project)}),
    ):
        cast(Callable[[], None], _hook().main)()
    return out.getvalue()


def test_a_bug_in_the_scan_is_silence_and_not_a_crash(tmp_path: Path) -> None:
    project = _project(tmp_path, ledger=_drained(30))
    raw = _payload(project)

    assert _line(_main_out(raw, project)) != ""  # the control: main prints the reply
    with mock.patch.object(_hook(), "decide", side_effect=RuntimeError("planted")):
        assert _main_out(raw, project) == ""


# ------------------------------------------------------------------- as the harness runs it


def test_the_reply_is_one_ascii_json_object_with_no_blocking_key_and_exit_zero(
    tmp_path: Path,
) -> None:
    today = date.today()
    project = _project(tmp_path, ledger=_drained(30, today=today))

    done = _run_as_script(_payload(project), project)

    assert (done.returncode, done.stderr) == (0, b"")
    reply = _reply(done.stdout.decode("ascii"))  # non-ASCII output raises here
    assert set(reply) == {"hookSpecificOutput"}
    inner = cast(dict[str, Any], reply["hookSpecificOutput"])
    assert set(inner) == {"hookEventName", "additionalContext"}
    assert inner["hookEventName"] == "SessionStart"
    assert inner["additionalContext"] in {
        _expected(100, 30),
        _expected(100, 31),  # the day turned over between the fixture and the run
    }


@pytest.mark.parametrize(
    "name", ["empty stdin", "bytes that are not UTF-8", "truncated JSON"]
)
def test_input_the_hook_cannot_read_exits_zero_and_prints_nothing_as_a_script(
    name: str, tmp_path: Path
) -> None:
    project = _project(tmp_path, ledger=_drained(30, today=date.today()))

    done = _run_as_script(_UNREADABLE_INPUT[name], project)

    assert (done.returncode, done.stdout, done.stderr) == (0, b"", b"")


def test_a_project_that_has_not_switched_it_on_prints_nothing_as_a_script(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, ledger=_drained(30, today=date.today()), switch=None)

    done = _run_as_script(_payload(project), project)

    assert (done.returncode, done.stdout, done.stderr) == (0, b"", b"")


_EXIT_NAMES = frozenset({"exit", "quit", "_exit"})


def _called(node: ast.expr) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _exit_requests(source: str) -> list[str]:
    """Where a source ends the process on purpose: a call to `exit`, `quit`, `sys.exit` or
    `os._exit`, or a `raise SystemExit`. A script that never does cannot exit 2."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and _called(node.func) in _EXIT_NAMES:
            found.append(f"line {node.lineno}: a call to {_called(node.func)}")
        elif isinstance(node, ast.Raise) and node.exc is not None:
            raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if _called(raised) == "SystemExit":
                found.append(f"line {node.lineno}: raise SystemExit")
    return found


def test_no_path_of_the_script_asks_for_an_exit_code() -> None:
    assert _exit_requests(_HOOK.read_text(encoding="utf-8")) == []


def test_the_exit_scan_flags_planted_exits_and_spares_near_misses() -> None:
    planted = (
        "import os, sys\nsys.exit(2)\nexit(0)\nos._exit(1)\n"
        "raise SystemExit(2)\nraise SystemExit\n"
    )
    near_miss = (
        '"""sys.exit(2) in a docstring."""\nexit_code = 0\n'
        "def exit_code_text():\n    return 'sys.exit(2)'\n# raise SystemExit\n"
    )

    assert len(_exit_requests(planted)) == 5
    assert _exit_requests(near_miss) == []
