"""The checks of the ai docs lookup wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_step_two_call_names_the_table_realtime_guide_url`: the step two call names the table realtime guide url
"""

import re
from urllib.parse import urlparse

from lemmi_ai_kit.manifest import shipped_skill_dirs

_SKILL = shipped_skill_dirs()["ai-docs-lookup"] / "SKILL.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_REALTIME_ROW = re.compile(r"\|\s*Realtime API guide\s*\|\s*`(https?://[^`\s]+)`")
_CALL_URL = re.compile(r'WebFetch\(.*?url="([^"]+)"', re.DOTALL)


def _text() -> str:
    return _SKILL.read_text(encoding="utf-8")


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the code it holds, not a heading. A missing heading fails with the
    heading named, so a renamed section is a loud failure and never an empty match.
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
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _step(number: int) -> str:
    return _section(_text(), f"### Step {number}", "ai-docs-lookup SKILL.md")


def _step_two_call() -> str:
    """The fenced block of Step 2 that holds the `WebFetch(` call."""
    blocks = re.findall(r"```[^\n]*\n(.*?)```", _step(2), re.DOTALL)
    calls = [block for block in blocks if "WebFetch(" in block]
    if len(calls) != 1:
        raise AssertionError(
            f"ai-docs-lookup SKILL.md Step 2: expected one WebFetch call block, found {len(calls)}"
        )
    return calls[0]


# --- a fetch answer can be a summary -----------------------------------------------------


# --- the Step 2 call ---------------------------------------------------------------------


def test_the_step_two_call_names_the_table_realtime_guide_url() -> None:
    row = _REALTIME_ROW.search(_text())
    assert row is not None, (
        "the sources table has no 'Realtime API guide' row with a URL"
    )
    table_url = row.group(1)
    found = _CALL_URL.search(_step_two_call())
    assert found is not None, "the Step 2 call names no url="
    call_url = found.group(1)
    assert urlparse(call_url).netloc == urlparse(table_url).netloc, (
        f"the Step 2 call names host {urlparse(call_url).netloc!r}, the table row "
        f"{urlparse(table_url).netloc!r}"
    )
    assert call_url == table_url, (
        f"the Step 2 call fetches {call_url}, the table row {table_url}"
    )


# --- the file agrees ---------------------------------------------------------------------


# --- the instruments ---------------------------------------------------------------------
