"""Section 7 of the gate-output reference says SQL handed to someone else is validated only by running it.

Section 7 is a table of command traps: each row is a command shape that ran, exited 0 and answered
a different question. It had no row for a syntax-only check of SQL that another person will run (a
parser, an EXPLAIN that plans but never executes, a dry run). Such a check says the query is well
formed; what a pattern in it means is decided by the engine, and a PostgreSQL regular expression
reads a backslash-b as a backspace and a backslash-y as the word boundary. The row says that SQL
handed to someone else is validated only by executing it, as written and then widened, on a
throwaway database of the target's major version, with known-positive and known-negative rows.
No test here starts a database or runs SQL: the wording is pinned. The claim about the two escapes
was read from the PostgreSQL manual (the Regular Expression Escapes subsection of its
pattern-matching chapter) when the row was written.

THE SURFACE, in numbers the tests assert: 1 place (the table of section 7 of 1 file), 3 columns, 6
phrases that must all sit in ONE body row of that table, and a table of at least 17 body rows (at
least 2 of them holding an escaped pipe), every line of it counted by the one cell counter that
counts the new row. The phrases are matched inside table rows only: `known-positive` and
`known-negative` already stand in the paragraph that closes section 7, so a search of the whole
section passes 2 of the 6 on the text as it stood (`_OLD_SECTION_7`, an excerpt of it, on which the
helpers must report all 6 as missing).
"""

import re
from pathlib import Path

import pytest

_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
    / "references"
    / "reading-gate-output.md"
)
_HEADING_7 = "## 7."
_BACKSLASH = chr(92)
_COLUMNS = 3
# The table as it stood before the row was added, derived by reading it: a floor, not an equality.
_ROWS_AT_START = 17
_ESCAPED_AT_START = 2
# The wording the row must hold, all in ONE body row. Matched case-sensitively, on the row with its
# emphasis and code-span marks dropped and its whitespace folded.
_PHRASES: tuple[str, ...] = (
    "syntax-clean",
    "throwaway database",
    "known-positive",
    "known-negative",
    "backspace",
    _BACKSLASH + "y",
)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return " ".join(re.sub(r"[*`]", "", text).split())


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next `## ` heading; a `## ` line
    inside a fenced block is not a heading. A missing heading fails loudly, with the heading named."""
    body: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            if body:
                body.append(line)
            continue
        is_heading = not in_fence and line.startswith("## ")
        if not body:
            if is_heading and line.startswith(heading):
                body.append(line)
            continue
        if is_heading:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"reading-gate-output.md: no heading starting {heading!r}")
    return "\n".join(body)


def _table(section: str) -> list[str]:
    """The first run of table lines (lines that start with a pipe) in the section: the header, the
    separator, then the rows. A line that does not start with a pipe ends the run, so a row set
    apart from it by a blank line, or one that lost its leading pipe, is not in the table."""
    run: list[str] = []
    for line in section.split("\n"):
        if line.startswith("|"):
            run.append(line)
        elif run:
            break
    return run


def _cells(row: str) -> list[str]:
    """The cells of one table line, outer pipes dropped, split on a pipe that is not escaped: the
    neighbouring rows hold escaped pipes inside their code spans, which a plain split miscounts."""
    inner = row.strip().removeprefix("|").removesuffix("|")
    return [
        str(cell) for cell in re.split(r"(?<!" + re.escape(_BACKSLASH) + r")\|", inner)
    ]


def _missing(row: str) -> list[str]:
    """The phrases that one table line lacks."""
    folded = _plain(row)
    return [phrase for phrase in _PHRASES if phrase not in folded]


def _sql_rows(section: str) -> list[str]:
    """The body rows of the table that hold every phrase."""
    return [row for row in _table(section)[2:] if not _missing(row)]


def _phrase_gaps(section: str) -> list[str]:
    """The phrases the closest body row lacks: empty when one row holds them all, every phrase when
    the table has no body row."""
    return min(
        (_missing(row) for row in _table(section)[2:]),
        key=len,
        default=list(_PHRASES),
    )


def _cell_gaps(section: str) -> list[str]:
    """What is wrong with the cell count of the rows that hold the phrases: empty when each has
    exactly as many cells as the table's header."""
    rows = _sql_rows(section)
    if not rows:
        return ["no table row holds the phrases, so there is no row to count"]
    width = len(_cells(_table(section)[0]))
    counts = [len(_cells(row)) for row in rows]
    return [
        f"a row holds {n} cells, the table has {width}" for n in counts if n != width
    ]


def _gaps_of(text: str) -> list[str]:
    return _phrase_gaps(_section(text, _HEADING_7))


# The shapes the helpers are fired at. The two neighbours and the closing paragraph are the text as
# it stood; the rest are planted.
_HEADER = "| Command shape | What you think it does | What it does |"
_SEPARATOR = "|---|---|---|"
_ESCAPED_NEIGHBOUR = r"""| `grep -E 'a\|b'` | alternation | `\|` inside `-E` is a **literal pipe**; `-E` wants a bare `\|`. Four "0 files untracked" results in one sweep were silent zeros |"""
_NEIGHBOUR = r"""| a `\b` written into generated file **content** | a regex boundary | arrives at the next reader as the **BACKSPACE escape** (`0x08`), putting invisible bytes into a committed file |"""
_NEXT_NEIGHBOUR = "| an italic-span regex over markdown | italics | swallows every **bold** span too, so a citation audit can report a whole document as uncited |"
_CLOSING = (
    "The general rule underneath all of them: **run the command against a case whose answer you already",
    "know before you trust it on a case whose answer you don't.** Every row here would have been caught",
    "by a single known-positive/known-negative pair.",
)
_SQL_ROW = r"""| a syntax-only check of SQL that another person will run (a parser, an EXPLAIN that plans but never executes, a dry run) | the query is validated | it is syntax-clean, not validated: the engine decides what a pattern means. In a PostgreSQL regular expression `\b` is a backspace and `\y` is the word boundary, so a query written with `\b` parses, runs and matches nothing. SQL handed to someone else is validated only by executing it, as written and then widened, on a throwaway database of the target's major version, with known-positive and known-negative rows |"""
# The same row re-wrapped: doubled spaces, and no padding at the cell edges.
_REWRAPPED = _SQL_ROW.replace(" | ", "|").replace(" ", "  ")
# Other words, the same phrases.
_REWORDED = r"""| a parse-only pass over SQL that someone else will run | the query is checked | it is syntax-clean and no more: the engine decides what a pattern means (in PostgreSQL a `\b` is a backspace, `\y` the word boundary). Validate by running it on a throwaway database with known-positive and known-negative rows |"""
# An escaped pipe inside a cell is not a cell separator.
_ESCAPED_PIPE_ROW = _SQL_ROW.replace("a dry run", r"a dry run \| a lint")
# The six phrases are all there, but no one row holds them all.
_SPREAD = (
    r"""| a syntax-only check of SQL | the query is validated | it is syntax-clean: in a PostgreSQL regular expression `\b` is a backspace and `\y` is the word boundary |""",
    "| SQL handed to someone else | a parser validates it | validate it by running it on a throwaway database with known-positive and known-negative rows |",
)

_OLD_SECTION_7 = "\n".join(
    [
        "## 7. Concrete command traps (an excerpt of the section as it stood)",
        "",
        "Measured instances. Every row below produced a confident wrong answer that drove a decision.",
        "",
        _HEADER,
        _SEPARATOR,
        _ESCAPED_NEIGHBOUR,
        _NEIGHBOUR,
        _NEXT_NEIGHBOUR,
        "",
        *_CLOSING,
    ]
)


def _planted(*rows: str, apart: str = "", after: str = "") -> str:
    """A section 7 with the header and the neighbours, `rows` directly after the second neighbour
    (where the real row goes); `apart` follows a blank line and `after` stands under the next heading."""
    return "\n".join(
        [
            "## 7. Planted",
            "",
            _HEADER,
            _SEPARATOR,
            _ESCAPED_NEIGHBOUR,
            _NEIGHBOUR,
            *rows,
            _NEXT_NEIGHBOUR,
            "",
            apart,
            *_CLOSING,
            "## 8. After",
            after,
        ]
    )


def test_the_surface_is_stated_in_numbers() -> None:
    table = _table(_section(_read(_REFERENCE), _HEADING_7))
    assert len(_PHRASES) == 6, "the 6 phrases the docstring states"
    assert len(set(_PHRASES)) == len(_PHRASES), "two phrases are the same"
    assert len(table) - 2 >= _ROWS_AT_START, (
        f"{len(table) - 2} body rows scanned in section 7, at least {_ROWS_AT_START} expected"
    )
    assert len(_cells(table[0])) == _COLUMNS == 3, (
        f"the header holds {len(_cells(table[0]))} cells"
    )
    assert {len(_cells(line)) for line in table} == {_COLUMNS}, (
        "a line of the table does not count 3 cells"
    )
    escaped = [line for line in table if _BACKSLASH + "|" in line]
    assert len(escaped) >= _ESCAPED_AT_START, (
        f"{len(escaped)} rows hold an escaped pipe, at least {_ESCAPED_AT_START} expected"
    )


def test_section_7_holds_the_sql_row() -> None:
    section = _section(_read(_REFERENCE), _HEADING_7)
    gaps = _phrase_gaps(section)
    assert not gaps, f"no table row of section 7 of reading-gate-output.md holds {gaps}"
    assert len(_sql_rows(section)) == 1, "the row is in the table more than once"


def test_the_sql_row_sits_inside_the_table_with_the_tables_cell_count() -> None:
    gaps = _cell_gaps(_section(_read(_REFERENCE), _HEADING_7))
    assert not gaps, f"section 7 of reading-gate-output.md: {gaps}"


def test_the_cell_counter_reads_escaped_pipes_the_way_the_neighbours_do() -> None:
    """Fired at the real table: the rows that hold an escaped pipe count 3 cells here and not by a
    plain split, so the escape rule is exercised and not assumed."""
    table = _table(_section(_read(_REFERENCE), _HEADING_7))
    escaped = [line for line in table if _BACKSLASH + "|" in line]
    assert escaped, "no row of the table holds an escaped pipe: this check sees nothing"
    for line in escaped:
        plain_split = len(line.strip().strip("|").split("|"))
        assert plain_split != _COLUMNS, (
            f"a plain split already counts {line[:40]!r} right"
        )
        assert len(_cells(line)) == _COLUMNS, f"{line[:40]!r} does not count 3 cells"


def test_every_check_reports_the_text_it_replaced() -> None:
    """The text as it stood carried none of the row, so every check must say so. Two of the six
    phrases are in its closing paragraph and a third is in a neighbour in capitals: a search of the
    section, or a case-folded one, would have passed them."""
    old = _section(_OLD_SECTION_7, _HEADING_7)
    assert _phrase_gaps(old) == list(_PHRASES), "a check did not see the old text"
    assert _sql_rows(old) == []
    assert len(_cell_gaps(old)) == 1
    assert [p for p in _PHRASES if p in _plain(old)] == [
        "known-positive",
        "known-negative",
    ], "the excerpt no longer carries the trap that the row scope avoids"
    assert "backspace" in _plain(old).lower(), "the neighbour no longer says BACKSPACE"


def test_the_helpers_accept_the_row_and_its_near_misses() -> None:
    shapes = {
        "the row as it ships": _SQL_ROW,
        "re-wrapped: doubled spaces, no padding at the cell edges": _REWRAPPED,
        "reworded, the same phrases": _REWORDED,
        "an escaped pipe inside a cell": _ESCAPED_PIPE_ROW,
    }
    for label, row in shapes.items():
        section = _section(_planted(row), _HEADING_7)
        assert _phrase_gaps(section) == [], label
        assert _cell_gaps(section) == [], label
        assert len(_sql_rows(section)) == 1, label


def test_the_helpers_reject_a_section_without_the_row() -> None:
    absent = _section(_planted(), _HEADING_7)
    assert _phrase_gaps(absent) == list(_PHRASES)
    assert _sql_rows(absent) == []
    assert len(_cell_gaps(absent)) == 1
    for label, text in {
        "a row set apart from the table by a blank line": _planted(apart=_SQL_ROW),
        "a row under the next heading": _planted(after=_SQL_ROW),
        "a row that lost its leading pipe": _planted(_SQL_ROW[1:]),
    }.items():
        assert _gaps_of(text) == list(_PHRASES), label


def test_the_helpers_name_the_phrase_that_is_missing_from_the_row() -> None:
    for phrase in _PHRASES:
        mutated = _SQL_ROW.replace(phrase, "x" * 4)
        assert mutated != _SQL_ROW, f"{phrase!r} is not in the planted row"
        assert _gaps_of(_planted(mutated)) == [phrase], phrase
    spread = _section(_planted(*_SPREAD), _HEADING_7)
    assert len(_phrase_gaps(spread)) == 3, (
        "phrases spread over two rows were counted as one"
    )
    assert _sql_rows(spread) == []


def test_the_helpers_count_the_cells_of_the_row() -> None:
    shapes = {
        "a fourth cell": (_SQL_ROW + " one cell too many |", 4),
        "a missing cell": (_SQL_ROW.replace(" | the query is validated |", " |"), 2),
    }
    for label, (row, cells) in shapes.items():
        section = _section(_planted(row), _HEADING_7)
        assert _phrase_gaps(section) == [], f"{label}: the phrases are still all there"
        assert _cell_gaps(section) == [f"a row holds {cells} cells, the table has 3"], (
            label
        )


def test_a_missing_heading_fails_loudly_and_the_next_heading_ends_the_section() -> None:
    planted = _planted(_SQL_ROW)
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "## 9.")
    assert "## 8. After" not in _section(planted, _HEADING_7)
    assert _section(planted, _HEADING_7).splitlines()[0] == "## 7. Planted"
