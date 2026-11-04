"""python-conventions says how an event deadline is written, what `asyncio.wait` leaves running, and when a name is grepped.

Three pieces of text, each from a behaviour reproduced with the standard library alone, nothing
installed, on the three interpreters that exist on one machine (3.11, 3.12 and 3.13):

- `asyncio.wait_for(event.wait(), timeout)` swallowed an accepted `cancel()` of the awaiting task on
  3.11 when the event was set in the loop iterations before the cancel, and did not on 3.12 or 3.13,
  where `wait_for` is built on `asyncio.timeout`; `async with asyncio.timeout(...)` swallowed none of
  them on any of the three. The text is about a lost cancellation and not about bounding a response:
  both forms answer only after the cancelled work has finished unwinding.
- A caller cancelled during `await asyncio.wait({task}, timeout=...)` leaves `task` running to its end
  on all three, where `gather` and `wait_for` cancelled it, so the reference's own bounded-response
  shape never reaches its `task.cancel()` in that case.
- A name bound twice at module level is rebound without a word, so grepping the name first is the
  check that sees it.

What the text says now: the reference's timeouts section keeps its body as it was and gains two
subsections after it, one per behaviour, and the skill's constants section gains one bullet at the
end of its list.

THE SURFACE, in numbers the tests assert: 2 files are read (the reference and the skill), 3 places
are read in them (two subsections and the bullet), 15 phrases are asserted in all, 1 fenced block is
parsed as Python, and 4 anchors of the timeouts section's own body are kept. Each helper is fired at
the pre-edit text, at a near miss (the phrases under the wrong heading) and at planted text that
holds the new shape, so a silence on the real files is a silence about the files. The section reader
is also fired at a `#` line inside a fenced block, which is a comment and never a heading.
"""

import ast
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO / "plugins" / "python" / "skills" / "python-conventions"
_SKILL = _SKILL_DIR / "SKILL.md"
_REFERENCE = _SKILL_DIR / "references" / "coding-patterns.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")

_TIMEOUTS = "## Timeouts That Must Bound a Response"
_FOLLOWING = "## Client Free Text at Logging Boundaries"
_DEADLINE = "### A deadline on an event or future"
_OUTLIVE = "### Tasks awaited with `asyncio.wait` outlive a cancelled caller"
_CONSTANTS = "### Constants Over Magic Strings"
_LIST = "Where to put constants:"

_EM = chr(0x2014)

# What each place says: the label the test id carries, the file, the heading whose section holds
# the words, a marker inside that section after which the words must sit ("" for none), and the
# phrases that must all be there once whitespace is folded.
_PLACES: tuple[tuple[str, Path, str, str, tuple[str, ...]], ...] = (
    (
        "deadline",
        _REFERENCE,
        _DEADLINE,
        "",
        (
            "On Python 3.11, `asyncio.wait_for(event.wait(), timeout)` can swallow a cancellation"
            " of the task that awaits it",
            "`wait_for` returns the result and the `CancelledError` is lost",
            "From 3.12 `wait_for` is built on `asyncio.timeout`",
            "in code that may run on 3.11, use the context manager",
            "This is about not losing a cancellation, not about bounding a response",
            "a timeout that must bound the response still takes the `asyncio.wait` shape at the"
            " top of this section",
            "reproduce it with the standard library alone under the interpreter that runs in"
            " production",
        ),
    ),
    (
        "outlive",
        _REFERENCE,
        _OUTLIVE,
        "",
        (
            "`asyncio.wait(tasks, timeout=...)` cancels none of the tasks it awaits when the"
            " coroutine awaiting it is itself cancelled",
            "leaves `task` running, neither cancelled nor observed, if its caller is cancelled"
            " during the wait",
            "cancels or signals them when it is itself cancelled (`try`/`finally`, or"
            " `except asyncio.CancelledError`)",
            "or says that the work continues after the caller gave up",
            '"The teardown timed out" does not mean "nothing is running"',
        ),
    ),
    (
        "constant",
        _SKILL,
        _CONSTANTS,
        _LIST,
        (
            "Before adding a module-level constant to an existing module, run"
            " `grep -n '^<NAME>' <file>`",
            "Python rebinds a name silently, so the new constant can replace an older one that"
            " another check still reads",
            "A probe of the new check shows that it can see; only the suite shows that nothing"
            " else broke",
        ),
    ),
)

# The timeouts section's own body, which the change leaves as it was: two code lines, the sentence
# that gives the measured figure, and the sentence that ends the section.
_BODY_ANCHORS = (
    "result = await asyncio.wait_for(probe(), timeout=2.0)",
    "done, _pending = await asyncio.wait({task}, timeout=2.0)",
    "hung past 20 s under a 2 s `wait_for`",
    "exactly the case `wait_for` silently fails.",
)

# The text of both places before the change, as `git show` printed it at the start commit.
_OLD_TIMEOUTS = f"""\
## Timeouts That Must Bound a Response

`asyncio.wait_for` cancels the inner coroutine and then **awaits that cancellation to complete**.
Closing a SQLAlchemy session whose server has gone away issues *more* network I/O on the same
unresponsive socket, so the cleanup blocks and the timeout bounds nothing {_EM} `/health` hung past
20 s under a 2 s `wait_for`.

```python
# BAD: cleanup talks to the dead peer, so the timeout is not a bound
result = await asyncio.wait_for(probe(), timeout=2.0)

# GOOD: does not await cancellation {_EM} cancel, leave it to be reaped, answer now
done, _pending = await asyncio.wait({{task}}, timeout=2.0)
if not done:
    task.cancel()          # fire-and-forget
    return unhealthy()
```

Use this shape whenever the timeout must bound the *response* {_EM} health/liveness/readiness probes,
anything a load balancer or an on-call human reads. And **test the timeout by making the dependency
unreachable** (`docker pause`), never merely slow: a paused peer is exactly the case where cleanup
itself blocks, and exactly the case `wait_for` silently fails.

{_FOLLOWING}
"""

_OLD_CONSTANTS = """\
### Constants Over Magic Strings

```python
# GOOD: constants at module level or in constants file
STAGE_PARSE_SOURCE = "parse_source"

# BAD: inline string literals
progress.update(stage="parse_source", detail="fetching")
```

Where to put constants:
- Feature-scoped: `features/{feature}/constants.py`
- Core-scoped: `core/{module}/constants/{name}.py` (e.g. `core/jobs/constants/timing.py`)
- Module-level in the consuming file is acceptable for single-consumer constants

## basedpyright Compliance Patterns
"""

_OLD = {_REFERENCE: _OLD_TIMEOUTS, _SKILL: _OLD_CONSTANTS}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text with every run of whitespace, line breaks included, as one space."""
    return " ".join(text.split())


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str, *, head_only: bool = False) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level, or, with `head_only`, to the next
    heading of any level. A `#` line inside a fenced block is a comment of the code it holds, not
    a heading. A missing heading fails with the heading named, so a renamed section is a loud
    failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and (head_only or len(match.group(1)) <= level):
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _fenced_blocks(text: str) -> list[list[str]]:
    """The lines inside each fenced block, without its fence lines."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if _is_fence(line):
            if current is not None:
                blocks.append(current)
            current = [] if current is None else None
        elif current is not None:
            current.append(line)
    return blocks


def _missing(
    text: str, heading: str, after: str, phrases: tuple[str, ...], where: str
) -> list[str]:
    """The phrases that the section under `heading` lacks, or lacks after the marker `after`.

    A heading or a marker that is not found raises, and the message names the phrases the whole
    file lacks as well, so a renamed heading and a text that is gone read differently.
    """
    try:
        section = _section(text, heading, where)
        if after:
            if after not in section:
                raise AssertionError(f"{where}: {heading!r} has no {after!r}")
            section = section.split(after, 1)[1]
    except AssertionError as error:
        gone = [phrase for phrase in phrases if phrase not in _fold(text)]
        raise AssertionError(
            f"{error}; phrases found nowhere in the file: {gone}"
        ) from error
    folded = _fold(section)
    return [phrase for phrase in phrases if phrase not in folded]


# --- the change ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "heading", "after", "phrases"),
    [row[1:] for row in _PLACES],
    ids=[row[0] for row in _PLACES],
)
def test_the_place_states_its_claim(
    path: Path, heading: str, after: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_read(path), heading, after, phrases, path.name)
    assert not missing, f"{path.name}, {heading!r} does not carry {missing}"


def test_the_two_subsections_sit_inside_the_timeouts_section_in_order() -> None:
    text = _read(_REFERENCE)
    section = _section(text, _TIMEOUTS, _REFERENCE.name)
    _section(text, _FOLLOWING, _REFERENCE.name)
    positions = [section.find(heading) for heading in (_DEADLINE, _OUTLIVE)]
    assert -1 not in positions, f"not both inside the timeouts section: {positions}"
    assert positions == sorted(positions), f"not in order: {positions}"


def test_the_timeouts_section_keeps_its_own_body() -> None:
    head = _fold(
        _section(_read(_REFERENCE), _TIMEOUTS, _REFERENCE.name, head_only=True)
    )
    lost = [anchor for anchor in _BODY_ANCHORS if anchor not in head]
    assert not lost, f"the section's body lost {lost}"


def test_the_deadline_fence_is_the_context_manager_and_parses() -> None:
    section = _section(_read(_REFERENCE), _DEADLINE, _REFERENCE.name)
    blocks = _fenced_blocks(section)
    assert blocks == [["async with asyncio.timeout(5.0):", "    await event.wait()"]], (
        blocks
    )
    ast.parse(
        "async def deadline(event):\n" + "\n".join("    " + line for line in blocks[0])
    )


# --- the instruments ----------------------------------------------------------------------

_PLANTED = "\n".join(
    [
        "## Before",
        "",
        "text before",
        "",
        _TIMEOUTS,
        "",
        "The body.",
        "",
        "```python",
        "# a comment line inside a fenced block is not a heading",
        "x = 1",
        "```",
        "",
        _DEADLINE,
        "",
        "On Python 3.11 the planted",
        "claim runs over a line break.",
        "",
        _FOLLOWING,
        "",
        "after",
    ]
)


def test_the_section_reader_sees_planted_text_and_fails_loudly() -> None:
    whole = _section(_PLANTED, _TIMEOUTS, "planted")
    assert "The body." in whole and _DEADLINE in whole and "claim runs over" in whole
    assert "after" not in whole and "text before" not in whole
    head = _section(_PLANTED, _TIMEOUTS, "planted", head_only=True)
    assert "The body." in head and "# a comment line inside" in head
    assert _DEADLINE not in head
    with pytest.raises(AssertionError, match="no heading"):
        _section(_PLANTED, "# a comment line", "planted")
    with pytest.raises(AssertionError, match="no heading"):
        _section(_PLANTED, "### Nothing like this", "planted")
    assert "claim runs over a line break" in _fold(whole)


def test_the_claim_check_flags_the_pre_edit_text() -> None:
    for label, path, heading, after, phrases in _PLACES:
        old = _OLD[path]
        if label == "constant":
            assert _missing(old, heading, after, phrases, label) == list(phrases)
        else:
            with pytest.raises(AssertionError, match="no heading.*found nowhere"):
                _missing(old, heading, after, phrases, label)
    with pytest.raises(AssertionError, match="has no 'Where to put constants:'"):
        _missing(
            "### Constants Over Magic Strings\n\nx\n", _CONSTANTS, _LIST, ("x",), "p"
        )


def test_phrases_under_the_wrong_heading_do_not_satisfy_the_check() -> None:
    for label, _path, heading, after, phrases in _PLACES:
        said = " ".join(phrases)
        sibling = "### A sibling" if heading.startswith("###") else "## A sibling"
        before = f"{after}\n\n- an earlier item\n\n" if after else ""
        near_miss = f"{heading}\n\n{before}nothing here\n\n{sibling}\n\n{said}\n"
        assert _missing(near_miss, heading, after, phrases, label) == list(phrases)
        elsewhere = f"{sibling}\n\n{said}\n"
        with pytest.raises(AssertionError, match="no heading"):
            _missing(elsewhere, heading, after, phrases, label)
    marker_first = (
        f"{_CONSTANTS}\n\nBefore adding a module-level constant\n\n{_LIST}\n- x\n"
    )
    found = _missing(
        marker_first, _CONSTANTS, _LIST, ("Before adding a module-level constant",), "p"
    )
    assert found == ["Before adding a module-level constant"]


def test_the_claim_check_passes_planted_text_with_the_new_shape() -> None:
    for label, _path, heading, after, phrases in _PLACES:
        wrapped = "\n".join(f"  {part}" for part in " ".join(phrases).split(" "))
        lead = f"{after}\n- an earlier item\n" if after else ""
        planted = f"{heading}\n\n{lead}{wrapped}\n\n## Next\n"
        assert _missing(planted, heading, after, phrases, label) == []


def test_the_fence_parse_flags_a_broken_fence() -> None:
    broken = ["async with asyncio.timeout(5.0)", "    await event.wait()"]
    with pytest.raises(SyntaxError):
        ast.parse(
            "async def deadline(event):\n" + "\n".join("    " + line for line in broken)
        )


def test_the_body_check_flags_a_body_that_lost_an_anchor() -> None:
    old = _fold(_section(_OLD_TIMEOUTS, _TIMEOUTS, "old", head_only=True))
    assert [anchor for anchor in _BODY_ANCHORS if anchor not in old] == []
    edited = old.replace("hung past 20 s", "hung past 25 s")
    assert [anchor for anchor in _BODY_ANCHORS if anchor not in edited] == [
        _BODY_ANCHORS[2]
    ]


def test_the_scan_surface_is_stated_in_numbers() -> None:
    assert len({path for _, path, _, _, _ in _PLACES}) == 2, "not the 2 files stated"
    assert len(_PLACES) == 3, f"{len(_PLACES)} places, not the 3 stated"
    assert sum(len(places[4]) for places in _PLACES) == 15, "not the 15 phrases stated"
    assert len(_BODY_ANCHORS) == 4, "not the 4 body anchors stated"
    assert set(_OLD) == {path for _, path, _, _, _ in _PLACES}, (
        "an excerpt has no place"
    )
    for path in (_REFERENCE, _SKILL):
        assert path.is_file(), f"{path} is not a file"
    assert len(_read(_REFERENCE).split("\n")) > 300, (
        "the reference is shorter than any real one"
    )
    assert len(_read(_SKILL).split("\n")) > 400, (
        "the skill is shorter than any real one"
    )
    head = _fold(
        _section(_read(_REFERENCE), _TIMEOUTS, _REFERENCE.name, head_only=True)
    )
    said = [
        p for _, path, _, _, phrases in _PLACES if path == _REFERENCE for p in phrases
    ]
    assert len(said) == 12, "not the 12 reference phrases stated"
    assert [phrase for phrase in said if phrase in head] == [], (
        "a phrase of a subsection is in the section's own body, so the two scans overlap"
    )
