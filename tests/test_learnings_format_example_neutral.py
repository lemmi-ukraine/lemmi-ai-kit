"""`task-learnings`' first good-entry example names no one stack's idiom.

The first example under "Good Entry Examples" taught a rule of one codebase: a route layer
wraps each service call in a try/except and converts the feature's errors into the codebase's
shared exceptions, and its anchor was a file path in that codebase's source tree. It is the one
place in the file that shows what a good entry looks like, so a reader in another stack copied
the idiom of a stack that was not theirs along with the format. The example is now an entry that
reads the same in any language, with the same fields in the same order. The category table and
the Category slug line beside it are what the learnings lint is pinned to, so the swap has to
leave them as they were.

What each test asserts:

* `test_the_first_example_names_no_one_stacks_idiom` reads the first example only (the other
  three are not its subject) and finds none of the five old shapes.
* `test_the_first_example_keeps_the_entry_shape` holds it to the format the file teaches: a
  bracketed ISO date and a title, then the same eight fields in the same order, each with a
  value, and a Category that is a canonical slug. It is NOT red on the old example, which had
  the same shape: it guards the swap and shows no change.
* `test_the_category_table_and_slug_line_are_unchanged` pins the seven (section header, slug)
  pairs and the slug line as literals. It is NOT red on the old file either, for the same
  reason.
* The instrument tests fire the readers and the scans at planted text, so their silence on the
  real file means something. The old shapes are planted one class at a time and as one whole
  old-shaped entry, beside near misses that share words with them and must not be flagged.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

_FORMAT = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "task-learnings"
    / "references"
    / "learnings-format.md"
)

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_ENTRY_HEADING = re.compile(r"^### \[\d{4}-\d{2}-\d{2}\] \S")
_FIELD = re.compile(r"^- \*\*([A-Za-z-]+)\*\*: ?(.*)$")
_TABLE_ROW = re.compile(r"^\|\s*([A-Z][^|]*?)\s*\|\s*`([a-z-]+)`\s*\|", re.MULTILINE)
_TABLE_ROW_TAIL = re.compile(
    r"^(\|\s*[A-Z][^|]*?\s*\|\s*`[a-z-]+`\s*\|)[^|\n]*\|", re.M
)
_SLUG_LINE = re.compile(r"^- \*\*Category\*\*: (.+\|.+)$", re.MULTILINE)
_EXAMPLE_HEADING = re.compile(r"^### Example \d+:", re.MULTILINE)

_FIRST_EXAMPLE = "### Example 1:"
_WHERE = "task-learnings references/learnings-format.md"

# The eight fields the first example carries, in the order it carries them: the six every entry
# needs and the four routing fields (one of which, Category, is both).
_FIELDS: tuple[str, ...] = (
    "Context",
    "Finding",
    "Impact",
    "Category",
    "Home",
    "Enforce-via",
    "Verify-at",
    "Scope",
)
_FIELD_COUNT = 8

# The category table and the slug line as they stood before the example was swapped.
_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("Architecture Decisions", "architecture"),
        ("Common Pitfalls", "pitfall"),
        ("External Service Quirks", "external-api"),
        ("Performance Insights", "performance"),
        ("Pattern Discoveries", "pattern"),
        ("Convention Clarifications", "convention"),
        ("Interaction & Workflow Friction", "interaction"),
    }
)
_PAIR_COUNT = 7
_SLUG_LINE_TEXT = (
    "architecture | pitfall | external-api | performance | pattern | convention | "
    "interaction"
)
_SLUGS = frozenset(slug for _, slug in _PAIRS)
_EXAMPLE_COUNT = 4

# Parts of the old example, spelled in fragments where the whole would name a real tree.
_OLD_TITLE = "Feature exception conversion must happen in routes, not services"
_OLD_PATH = "back" + "end/app/features/coach/api/routes.py"


def _text() -> str:
    return _FORMAT.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text with every run of whitespace, line breaks included, as one space."""
    return " ".join(text.split())


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is the entry the block shows, not a heading of this file. A missing heading fails
    with the heading named, so a renamed section is a loud failure and never an empty match.
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


def _fence_lines(section: str, where: str) -> list[str]:
    """The lines of the first fenced block of `section`, the two fence lines left out."""
    lines = section.split("\n")
    fences = [at for at, line in enumerate(lines) if _is_fence(line)]
    if len(fences) < 2:
        raise AssertionError(f"{where}: no complete fenced block")
    return lines[fences[0] + 1 : fences[1]]


@dataclass(frozen=True)
class _Shape:
    """One class of old shape: what it is called, how it is found, a sentence that holds it."""

    label: str
    pattern: re.Pattern[str]
    planted: str


_SHAPES: tuple[_Shape, ...] = (
    _Shape(
        "the old title",
        re.compile(re.escape(_OLD_TITLE), re.IGNORECASE),
        _OLD_TITLE,
    ),
    _Shape(
        "the try/except idiom",
        re.compile(r"\btry\s*/\s*except\b", re.IGNORECASE),
        "In the handlers, wrap each call with try/except and map the error.",
    ),
    _Shape(
        "a conversion to shared exceptions",
        re.compile(r"\bconvert(?:s|ed|ing)?\s+to\s+shared\s+exceptions?\b", re.I),
        "Catch the feature error and converts to shared exceptions.",
    ),
    _Shape(
        "the old exception names",
        re.compile(r"\b(?:Session)?NotFoundError\b"),
        "A SessionNotFoundError is raised for a missing record.",
    ),
    _Shape(
        "a path in the old source tree",
        re.compile(r"\b" + "back" + "end/"),
        "Verify-at: " + _OLD_PATH,
    ),
)

# Sentences that share words with the shapes and are not one of them.
_NEAR_MISSES: tuple[str, ...] = (
    "Retry once, then try again later, except when the call is not idempotent.",
    "A missing record raises a not-found error that the boundary turns into its own.",
    "The back-end team owns the scheduler, and a backend service calls it.",
    "Convert the error at the boundary, and share the conversion between handlers.",
    "Every exception that is shared between layers needs one owner.",
)


def _shapes_in(text: str) -> list[str]:
    """Every old shape `text` holds, as `label: match`, after line breaks are folded."""
    folded = _fold(text)
    return [
        f"{shape.label}: {match.group(0)!r}"
        for shape in _SHAPES
        for match in shape.pattern.finditer(folded)
    ]


def _entry_problems(lines: list[str]) -> list[str]:
    """What is wrong with one entry: its heading, its fields, their order, values and slug.

    A value may continue on indented lines. A line that is neither a field, a continuation
    nor blank is a problem of its own, so an entry cannot hide a stray line between fields.
    """
    problems: list[str] = []
    if not lines or _ENTRY_HEADING.match(lines[0]) is None:
        shown = lines[0] if lines else "nothing"
        problems.append(f"the heading is not a bracketed date and a title: {shown!r}")
    fields: list[tuple[str, str]] = []
    for line in lines[1:]:
        match = _FIELD.match(line)
        if match is not None:
            fields.append((match.group(1), match.group(2)))
        elif not line.strip():
            continue
        elif line[:1].isspace() and fields:
            name, value = fields[-1]
            fields[-1] = (name, f"{value} {line.strip()}")
        else:
            problems.append(f"a line that is not a field: {line[:60]!r}")
    names = tuple(name for name, _ in fields)
    if names != _FIELDS:
        problems.append(f"the fields are {names}, expected {_FIELDS}")
    empty = [name for name, value in fields if not value.strip()]
    if empty:
        problems.append(f"fields with no value: {empty}")
    category = dict(fields).get("Category", "").strip()
    if category not in _SLUGS:
        problems.append(f"the Category {category!r} is not a canonical slug")
    return problems


def _surface_counts(block: list[str]) -> tuple[int, int]:
    """(headings, fields) of one fenced entry block, counted by the lines that open them.

    A value wrapped onto indented lines is still one field, so a re-wrap moves neither count.
    """
    headings = sum(1 for line in block if _ENTRY_HEADING.match(line) is not None)
    fields = sum(1 for line in block if _FIELD.match(line) is not None)
    return headings, fields


def _category_problems(text: str) -> list[str]:
    """What is wrong with the category table and the slug line, against the pinned literals."""
    pairs = {(header, slug) for header, slug in _TABLE_ROW.findall(text)}
    problems: list[str] = []
    dropped = sorted(_PAIRS - pairs)
    if dropped:
        problems.append(f"the swap drops a category row: {dropped}")
    added = sorted(pairs - _PAIRS)
    if added:
        problems.append(f"the table lists a row it did not before: {added}")
    slug_lines = [line.strip() for line in _SLUG_LINE.findall(text)]
    if slug_lines != [_SLUG_LINE_TEXT]:
        problems.append(f"the Category slug line is not the pinned one: {slug_lines}")
    return problems


def _first_example() -> str:
    return _section(_text(), _FIRST_EXAMPLE, _WHERE)


# --- the change ---------------------------------------------------------------------------


def test_the_first_example_names_no_one_stacks_idiom() -> None:
    hits = _shapes_in(_first_example())
    assert not hits, (
        "the first good-entry example still teaches one stack's idiom "
        f"({len(hits)} hits): " + "; ".join(hits)
    )


def test_the_first_example_keeps_the_entry_shape() -> None:
    block = _fence_lines(_first_example(), _WHERE)
    problems = _entry_problems(block)
    assert not problems, "the first example is not a well-formed entry: " + "; ".join(
        problems
    )


def test_the_category_table_and_slug_line_are_unchanged() -> None:
    problems = _category_problems(_text())
    assert not problems, "; ".join(problems)


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_what_it_claims() -> None:
    text = _text()
    assert len(_EXAMPLE_HEADING.findall(text)) == _EXAMPLE_COUNT, (
        f"the file no longer holds {_EXAMPLE_COUNT} good-entry examples"
    )
    assert len(_TABLE_ROW.findall(text)) == _PAIR_COUNT == len(_PAIRS)
    assert len(_SLUG_LINE.findall(text)) == 1
    assert len(_FIELDS) == _FIELD_COUNT
    block = _fence_lines(_first_example(), _WHERE)
    assert _surface_counts(block) == (1, _FIELD_COUNT), (
        "the first example's block is not one heading and one opening line per field"
    )


@pytest.mark.parametrize("shape", _SHAPES, ids=[shape.label for shape in _SHAPES])
def test_the_idiom_scan_sees_each_planted_shape(shape: _Shape) -> None:
    planted = f"An opening sentence.\n{shape.planted}\nA closing sentence."
    hits = _shapes_in(planted)
    assert any(hit.startswith(shape.label) for hit in hits), (
        f"the scan missed {shape.label!r} planted in a sentence; it found {hits}"
    )


def test_the_idiom_scan_sees_a_whole_old_shaped_entry() -> None:
    old = "\n".join(
        [
            "### Example 1: Convention Clarification (with routing fields)",
            "",
            "```markdown",
            f"### [2026-02-15] {_OLD_TITLE}",
            "- **Context**: New feature implementation, a service raised a transport error",
            "- **Finding**: Feature-specific exceptions (e.g., `SessionNotFoundError`) must",
            "  be caught in API routes and converted to shared exceptions (`NotFoundError`).",
            "- **Impact**: In routes, wrap service calls with try/except that converts to",
            "  shared exceptions.",
            "- **Category**: convention",
            "- **Home**: the installed language-conventions skill",
            "- **Enforce-via**: prose",
            f"- **Verify-at**: {_OLD_PATH}",
            "- **Scope**: durable",
            "```",
        ]
    )
    found = {hit.split(":")[0] for hit in _shapes_in(old)}
    assert found == {shape.label for shape in _SHAPES}, (
        f"the scan found {sorted(found)} in the old example, expected every class"
    )


@pytest.mark.parametrize("sentence", _NEAR_MISSES)
def test_the_idiom_scan_is_silent_on_near_misses(sentence: str) -> None:
    assert _shapes_in(sentence) == []


def test_the_idiom_scan_reads_through_a_re_wrap() -> None:
    both = {"the try/except idiom", "a conversion to shared exceptions"}
    wrapped = (
        "wrap each call with try/\nexcept, and a handler that converts\n"
        "  to shared\nexceptions"
    )
    assert {hit.split(":")[0] for hit in _shapes_in(wrapped)} == both
    spaced = "wrap each call with try / except, and a handler that converts to shared exceptions"
    assert {hit.split(":")[0] for hit in _shapes_in(spaced)} == both


_GOOD_ENTRY: tuple[str, ...] = (
    "### [2026-01-02] A title that states the finding",
    "- **Context**: where it came up",
    "- **Finding**: what is true",
    "- **Impact**: do this, avoid that",
    "- **Category**: convention",
    "- **Home**: agents-rule",
    "- **Enforce-via**: test",
    "- **Verify-at**: Anchor.symbol",
    "- **Scope**: durable",
)


def _without(prefix: str) -> list[str]:
    return [line for line in _GOOD_ENTRY if not line.startswith(prefix)]


_PLANTED_ENTRIES: dict[str, list[str]] = {
    "an unbracketed heading": ["### 2026-01-02 A title", *_GOOD_ENTRY[1:]],
    "a heading with no title": ["### [2026-01-02]", *_GOOD_ENTRY[1:]],
    "a field dropped": _without("- **Impact**"),
    "a routing field dropped": _without("- **Scope**"),
    "two fields swapped": [
        *_GOOD_ENTRY[:2],
        _GOOD_ENTRY[3],
        _GOOD_ENTRY[2],
        *_GOOD_ENTRY[4:],
    ],
    "an empty value": [
        *_GOOD_ENTRY[:3],
        "- **Impact**:",
        *_GOOD_ENTRY[4:],
    ],
    "a slug that is not canonical": [
        *_GOOD_ENTRY[:4],
        "- **Category**: convention-ish",
        *_GOOD_ENTRY[5:],
    ],
    "a stray line between fields": [*_GOOD_ENTRY[:3], "not a field", *_GOOD_ENTRY[3:]],
}


def test_the_entry_check_is_clean_on_a_good_entry_and_sees_each_planted_defect() -> (
    None
):
    assert _entry_problems(list(_GOOD_ENTRY)) == [], "the control entry is not clean"
    for form, lines in _PLANTED_ENTRIES.items():
        assert lines != list(_GOOD_ENTRY), f"{form}: the planted entry changed nothing"
        assert _entry_problems(lines), f"the check missed a planted {form}"


def test_the_entry_check_reads_a_wrapped_value_as_one_field() -> None:
    wrapped = [
        *_GOOD_ENTRY[:2],
        "- **Finding**: what is true,",
        "  and the rest of it on a second line",
        *_GOOD_ENTRY[3:],
    ]
    assert _entry_problems(wrapped) == []


def test_the_surface_count_ignores_a_re_wrap_and_sees_a_change() -> None:
    assert _surface_counts(list(_GOOD_ENTRY)) == (1, _FIELD_COUNT), "the control is off"
    wrapped = [
        *_GOOD_ENTRY[:2],
        "- **Finding**: what is true,",
        "  and the rest of it on a second line",
        *_GOOD_ENTRY[3:],
    ]
    assert _surface_counts(wrapped) == (1, _FIELD_COUNT), "a re-wrap moved a count"
    assert _surface_counts(_without("- **Scope**")) == (1, _FIELD_COUNT - 1)
    assert _surface_counts([*_GOOD_ENTRY, *_GOOD_ENTRY]) == (2, 2 * _FIELD_COUNT)


def _replace_once(old: str, new: str) -> Callable[[str], str]:
    def edit(text: str) -> str:
        assert old in text, f"the planted edit's target is not in the text: {old!r}"
        return text.replace(old, new, 1)

    return edit


def _drop_lines_with(fragment: str) -> Callable[[str], str]:
    def edit(text: str) -> str:
        lines = text.split("\n")
        kept = [line for line in lines if fragment not in line]
        assert len(kept) < len(lines), f"no line holds {fragment!r}"
        return "\n".join(kept)

    return edit


def _reword_every_description(text: str) -> str:
    return _TABLE_ROW_TAIL.sub(r"\1 reworded |", text)


_PLANTED_TABLES: dict[str, Callable[[str], str]] = {
    "a category row dropped": _drop_lines_with("| Common Pitfalls |"),
    "a slug changed in its row": _replace_once("`external-api` |", "`external` |"),
    "a section header renamed": _replace_once("| Common Pitfalls |", "| Pitfalls |"),
    "a slug left out of the slug line": _replace_once(
        "convention | interaction", "convention"
    ),
}


@pytest.mark.parametrize("form", list(_PLANTED_TABLES))
def test_the_table_check_sees_a_planted_change(form: str) -> None:
    text = _text()
    assert _category_problems(text) == [], "the control is not clean"
    planted = _PLANTED_TABLES[form](text)
    assert planted != text, f"{form}: the planted change changed nothing"
    assert _category_problems(planted), f"the check missed {form}"


def test_a_dropped_row_is_reported_as_the_swap_dropping_it() -> None:
    planted = _PLANTED_TABLES["a category row dropped"](_text())
    problems = _category_problems(planted)
    assert any(
        problem.startswith("the swap drops a category row") and "pitfall" in problem
        for problem in problems
    ), problems


def test_the_table_check_is_silent_when_only_the_descriptions_change() -> None:
    text = _text()
    reworded = _reword_every_description(text)
    assert reworded != text, "the planted rewording changed nothing"
    assert len(_TABLE_ROW.findall(reworded)) == _PAIR_COUNT
    assert _category_problems(reworded) == []


def test_the_section_reader_fails_loudly_and_stops_at_the_next_example() -> None:
    planted = "\n".join(
        [
            "## Alpha",
            "### Example 1: first",
            "```markdown",
            "### [2026-01-02] an entry heading inside a fence is not a heading",
            "- **Context**: inside",
            "```",
            "after the fence",
            "### Example 2: second",
            "second body",
        ]
    )
    first = _section(planted, "### Example 1:", "planted")
    assert "after the fence" in first and "second body" not in first
    assert _fence_lines(first, "planted") == [
        "### [2026-01-02] an entry heading inside a fence is not a heading",
        "- **Context**: inside",
    ]
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### Example 9:", "planted")
    with pytest.raises(AssertionError, match="no complete fenced block"):
        _fence_lines("### Example 1: bare\nno fence here", "planted")
