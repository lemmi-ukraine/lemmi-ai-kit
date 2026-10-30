"""`ai-docs-lookup` does not treat a fetch answer as the page.

A `WebFetch` answer can be a model's summary of the page, not the page. A summary of a
provider's models index said a model did not appear while that model's own page existed, and
a 404 for one URL said nothing about the item. The skill told its reader to fetch and to
quote, and it never said a fetch answer may be a summary, gave the fetch a prompt, or said
what a missing item or a 404 proves.

These tests read the skill text with line breaks folded and assert that one sentence says a
fetch answer can be a summary, that the Step 2 call carries a prompt with an escape for a
missing fact and names the table's own Realtime guide URL, that Step 1 checks a model on its
own page, that Step 3 quotes only text the fetch returned verbatim, and that the access
note no longer claims the pages return full content. Each assertion fails on the text it
replaced. The helpers are functions over a string, so
`test_the_slicers_see_planted_text_and_fail_loudly` fires them at planted text before their
silence on the real file is trusted.
"""

import re
from collections.abc import Iterable
from urllib.parse import urlparse

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_SKILL = shipped_skill_dirs()["ai-docs-lookup"] / "SKILL.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_REALTIME_ROW = re.compile(r"\|\s*Realtime API guide\s*\|\s*`(https?://[^`\s]+)`")
_CALL_URL = re.compile(r'WebFetch\(.*?url="([^"]+)"', re.DOTALL)


def _text() -> str:
    return _SKILL.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text with blockquote markers dropped and every run of whitespace as one space."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>+ ?", "", text)).strip()


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


def _assert_carries(where: str, folded: str, clauses: Iterable[str]) -> None:
    missing = [clause for clause in clauses if clause not in folded]
    assert not missing, f"{where} does not carry: {missing}"


def _bullet(text: str, lead: str, where: str) -> str:
    """One list bullet, folded: its first line starts with `lead`, and it runs through the
    indented lines that follow."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(lead):
            item = [line]
            for follow in lines[index + 1 :]:
                if not follow.strip() or not follow.startswith((" ", "\t")):
                    break
                item.append(follow)
            return _fold("\n".join(item))
    raise AssertionError(f"{where}: no bullet starting {lead!r}")


def _blockquote(text: str, lead: str, where: str) -> str:
    """One blockquote, folded: its first line starts with `lead`, and it runs through the
    lines that follow while they start with `>`."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(lead):
            quote = [line]
            for follow in lines[index + 1 :]:
                if not follow.startswith(">"):
                    break
                quote.append(follow)
            return _fold("\n".join(quote))
    raise AssertionError(f"{where}: no blockquote starting {lead!r}")


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


def test_a_fetch_answer_can_be_a_summary_and_the_skill_says_so() -> None:
    folded = _fold(_step(2))
    sentences = [
        s
        for s in _SENTENCE_BOUNDARY.split(folded)
        if "`WebFetch` answer" in s and re.search(r"\bsummary\b", s)
    ]
    assert sentences, (
        "ai-docs-lookup SKILL.md, Step 2 has no sentence saying a `WebFetch` answer can be a summary"
    )
    _assert_carries(
        "ai-docs-lookup SKILL.md, Step 2 summary rule",
        folded,
        (
            "can be a model's summary of the page, not the page",
            "an index summary can say an item is missing when its own page exists",
            "a 404 speaks for that URL only",
            "Never conclude that a model, parameter or page does not exist from a summarized fetch",
            "fetch the item's own page or make a live API call",
            "else use the Step 4 template and name the URLs read",
        ),
    )


def test_the_summary_rule_follows_the_search_rule() -> None:
    folded = _fold(_step(2))
    assert "`WebSearch` result is a pointer to fetch" in folded, (
        "Step 2 lost the search rule"
    )
    assert "`WebFetch` answer can be" in folded, "Step 2 has no summary rule"
    assert folded.index("`WebSearch` result is a pointer to fetch") < folded.index(
        "`WebFetch` answer can be"
    ), "the summary rule must come after the search rule it follows"


# --- the Step 2 call ---------------------------------------------------------------------


def test_the_step_two_call_carries_a_verbatim_prompt_with_an_escape() -> None:
    call = _fold(_step_two_call())
    _assert_carries(
        "ai-docs-lookup SKILL.md, Step 2 call",
        call,
        (
            "prompt=",
            "Quote verbatim every sentence that states",
            "If there is none, answer NOT ON THE PAGE.",
        ),
    )


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


def test_step_one_checks_a_model_on_its_own_page() -> None:
    bullet = _bullet(_step(1), "- **Model facts**", "ai-docs-lookup SKILL.md, Step 1")
    _assert_carries(
        "ai-docs-lookup SKILL.md, Step 1 'Model facts' bullet",
        bullet,
        ("model's own page",),
    )


def test_step_three_quotes_only_text_the_fetch_returned_verbatim() -> None:
    _assert_carries(
        "ai-docs-lookup SKILL.md, Step 3",
        _fold(_step(3)),
        ("Quote only text the fetch returned verbatim",),
    )


def test_the_access_note_no_longer_claims_the_pages_return_full_content() -> None:
    text = _text()
    note = _blockquote(
        text, "> **Access status", "ai-docs-lookup SKILL.md, OpenAI access note"
    )
    assert "full content" not in note, (
        "the access note still says the pages return full content"
    )
    assert "all return full content" not in _fold(text), (
        "the skill still says the pages all return full content"
    )
    _assert_carries(
        "ai-docs-lookup SKILL.md, OpenAI access note",
        note,
        ("renders fine via WebFetch", "summary"),
    )


# --- the instruments ---------------------------------------------------------------------


def test_the_scan_surface_is_the_one_skill_file() -> None:
    assert _SKILL.is_file()
    assert len(_text().strip().split("\n")) > 100, (
        "SKILL.md is shorter than any real version"
    )


def test_the_slicers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "### Step 2 — Fetch",
            "> **Rule.** A `WebFetch` answer can be a summary, wrapped",
            "> over two lines. Another sentence.",
            "",
            "- **First bullet**: one line",
            "  and a wrapped tail",
            "- **Second bullet**: another",
            "```",
            "# a comment inside a fence is not a heading",
            'WebFetch(url="https://example.invalid/page", prompt="NOT ON THE PAGE")',
            "```",
            "",
            "### Step 3 — Answer",
            "after the step",
        ]
    )
    quote = _blockquote(planted, "> **Rule.**", "planted")
    assert (
        quote.endswith("over two lines. Another sentence.")
        and "First bullet" not in quote
    )
    with pytest.raises(AssertionError, match="no blockquote"):
        _blockquote(planted, "> **Absent.**", "planted")
    bullet = _bullet(planted, "- **First bullet**", "planted")
    assert bullet == "- **First bullet**: one line and a wrapped tail"
    with pytest.raises(AssertionError, match="no bullet"):
        _bullet(planted, "- **Absent**", "planted")
    two = _section(planted, "### Step 2", "planted")
    assert "after the step" not in two
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### Step 9", "planted")

    folded = _fold(two)
    assert "`WebFetch` answer can be a summary, wrapped over two lines." in folded
    blocks = re.findall(r"```[^\n]*\n(.*?)```", two, re.DOTALL)
    assert len(blocks) == 1 and _CALL_URL.search(blocks[0]) is not None
    found = _CALL_URL.search(blocks[0])
    assert found is not None and found.group(1) == "https://example.invalid/page"
    row = _REALTIME_ROW.search(
        "| Realtime API guide | `https://example.invalid/guide` | x |"
    )
    assert row is not None and row.group(1) == "https://example.invalid/guide"
    with pytest.raises(AssertionError, match="does not carry"):
        _assert_carries("planted", folded, ("Rule", "no such clause"))
