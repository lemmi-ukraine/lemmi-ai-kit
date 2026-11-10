"""The session extractor reads a hand-off's ledger as the lint does.

`--sessions-from <hand-off>` makes the extractor read a note's `Task:` and `Sessions:` lines and
measure exactly the sessions listed there. The extractor runs stand-alone and imports nothing of
the kit, so it carries its own reader of the header block; the lint's is
`checks.parse_handoff_ledger` with `checks.handoff_session_ids`. If the two drifted, a note the lint
passes could be measured from other sessions than it lists, or from none. This file gives both
readers the same notes and holds every value the extractor reads equal to the lint's, and the ids
both split from the `Sessions:` value.

WHAT KEEPS IT HONEST. Agreement alone would pass two readers that are wrong in the same way, so
each note also carries the answer both must give: a filled note names its task and its ids, a
line inside a comment, inside a fence, below the first heading or written twice gives no value,
and an id listed twice is read once. The note of many spaces is timed per reader. The session ids
are made-up UUID shapes.
"""

import importlib.util
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from lemmi_ai_kit import checks

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = (
    _REPO_ROOT / "plugins" / "core" / "skills" / "session-retrospective" / "scripts"
)
_EXTRACTOR = _SCRIPTS / "extract_sessions.py"


def _load(script: Path, name: str) -> ModuleType:
    """Import a script by path, without leaving bytecode inside the pack payload."""
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


_EXTRACT = _load(_EXTRACTOR, "extract_sessions_ledger_agreement")
_read_ledger = cast(
    Callable[[str], dict[str, str | None]], _EXTRACT.read_handoff_ledger
)
_ledger_ids = cast(Callable[[str | None], tuple[str, ...]], _EXTRACT.ledger_session_ids)

# Made up in the shape of a session id; never a real one.
_A = "a1a1a1a1-0000-4000-8000-000000000001"
_C = "c2c2c2c2-0000-4000-8000-000000000002"
_HEAD = "<!-- handoff-contract: v3 -->\n# Hand-off: example-task\n\n"
_FILLED = (
    f"{_HEAD}Task: example-task\nSessions: {_A}, {_C}\n"
    f"Written: 2026-11-10 14:05 by {_C}\n\n## Scope\n"
)

# A note, the `Task:` value both readers must give, and the ids both must split from `Sessions:`.
_NOTES: dict[str, tuple[str, str | None, tuple[str, ...]]] = {
    "a filled note": (_FILLED, "example-task", (_A, _C)),
    "the lines inside a comment": (
        f"{_HEAD}<!--\nTask: example-task\nSessions: {_A}\n-->\n## Scope\n",
        None,
        (),
    ),
    "the lines inside a backtick fence": (
        f"{_HEAD}```\nTask: example-task\nSessions: {_A}\n```\n## Scope\n",
        None,
        (),
    ),
    "the lines inside a tilde fence": (
        f"{_HEAD}~~~\nTask: example-task\nSessions: {_A}\n~~~\n## Scope\n",
        None,
        (),
    ),
    "the lines below the first heading": (
        f"{_HEAD}## Scope\nTask: example-task\nSessions: {_A}\n",
        None,
        (),
    ),
    "each line written twice": (
        f"{_HEAD}Task: one-task\nTask: two-task\nSessions: {_A}\nSessions: {_C}\n",
        None,
        (),
    ),
    "an id listed twice": (f"{_HEAD}Sessions: {_A}, {_C}, {_A}\n", None, (_A, _C)),
    "empty items between the ids": (
        f"{_HEAD}Sessions: , {_A},, {_C} ,\n",
        None,
        (_A, _C),
    ),
    "empty values": (f"{_HEAD}Task:" + "\n" + "Sessions:" + "\n", "", ()),
    "no space after the colon": (
        f"{_HEAD}Task:example-task\nSessions:{_A}\n",
        "example-task",
        (_A,),
    ),
    "indented keys": (f"{_HEAD} Task: x\n\tSessions: {_A}\n", None, ()),
    "lower-case keys": (f"{_HEAD}task: x\nsessions: {_A}\n", None, ()),
    "a space before the colon": (f"{_HEAD}Task : x\nSessions : {_A}\n", None, ()),
    "a heading inside a comment or a fence ends nothing": (
        f"{_HEAD}<!--\n## c\n-->\n```\n## f\n```\nTask: k\nSessions: {_A}\n## Scope\n",
        "k",
        (_A,),
    ),
    "a comment never closed": (
        f"{_HEAD}<!-- open\nTask: k\nSessions: {_A}\n## Scope\n",
        "k",
        (_A,),
    ),
    "a fence never closed": (
        f"{_HEAD}```\nTask: k\nSessions: {_A}\n## Scope\n",
        None,
        (),
    ),
    "windows line endings": (
        f"{_HEAD}Task: k\nSessions: {_A}\n## Scope\n".replace("\n", "\r\n"),
        "k",
        (_A,),
    ),
    "no label": (f"Task: k\nSessions: {_A}\n", "k", (_A,)),
    "a heading with no text": (f"{_HEAD}## \nTask: k\nSessions: {_A}\n", "k", (_A,)),
    "a level-3 heading": (
        f"{_HEAD}### Sub\nTask: k\nSessions: {_A}\n## Scope\n",
        "k",
        (_A,),
    ),
    "a comment inside a line": (
        f"{_HEAD}Task: k <!-- note --> tail\nSessions: {_A} <!--\nmore -->\n",
        "k  tail",
        (_A,),
    ),
    "a unicode line separator": (f"{_HEAD}Task: k\u2028Sessions: {_A}\n", "k", (_A,)),
}


def _both(text: str) -> tuple[dict[str, str | None], dict[str, str | None]]:
    return checks.parse_handoff_ledger(text), _read_ledger(text)


@pytest.mark.parametrize("name", list(_NOTES))
def test_the_extractor_reads_a_note_as_the_lint_does(name: str) -> None:
    text, task, ids = _NOTES[name]

    lint, extractor = _both(text)

    assert {"Task", "Sessions"} <= set(extractor)
    assert {key: lint[key] for key in extractor} == extractor
    assert _ledger_ids(extractor["Sessions"]) == checks.handoff_session_ids(
        lint["Sessions"]
    )
    assert (lint["Task"], checks.handoff_session_ids(lint["Sessions"])) == (task, ids)


def test_a_note_of_many_spaces_is_read_alike_and_in_linear_time() -> None:
    """A pattern with a lazy group before `\\s*$` took about 10 seconds on one line of 40,000
    spaces (the drain-nudge hook's test records it). Here two ledger lines, a blank line, a
    comment and the first heading each hold 40,000 spaces, and each reader is timed alone."""
    spaces = " " * 40_000
    text = (
        f"{_HEAD}Task:{spaces}x\n{spaces}\n<!--{spaces}-->\n"
        f"Sessions:{spaces},{spaces}{_A}\n## {spaces}x\nTask: below-the-heading\n"
    )
    took: dict[str, float] = {}

    started = time.perf_counter()
    lint = checks.parse_handoff_ledger(text)
    lint_ids = checks.handoff_session_ids(lint["Sessions"])
    took["the lint"] = time.perf_counter() - started
    started = time.perf_counter()
    extractor = _read_ledger(text)
    extractor_ids = _ledger_ids(extractor["Sessions"])
    took["the extractor"] = time.perf_counter() - started

    assert {key: lint[key] for key in extractor} == extractor
    assert extractor_ids == lint_ids
    assert (extractor["Task"], extractor_ids) == ("x", (_A,))
    assert all(seconds < 1.0 for seconds in took.values()), took
