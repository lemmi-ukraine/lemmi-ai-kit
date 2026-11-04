"""The Dispatch section of `orchestrate` writes a prompt the operator asks for by name, and points writers at execution lanes.

Default 1 told the orchestrator that a brief the operator pastes into a new session is the fallback,
and to say why "the launcher" would not do before writing one. Two things were wrong with the last
sentence. It had no exception for a prompt the operator asked for by name, so restating the default
could not move the number it was written to move: a request by name is the operator measuring what
the launch costs, not a lapse to correct, and the default governs what the orchestrator chooses
unasked. And section 2a holds measured launch facts, not a launcher, so the sentence named something
the kit does not ship. The section also says parallel writers are isolated by declared disjoint
file sets; its bullet now names the optional execution lanes of `spec-driven-dev` (plain words, no
link, no path into the other pack) for a build whose tests are written apart from its code. The
rows of this file are the ones that add lines to `SKILL.md`, so its cap is asserted here as well.

THE SURFACE, in numbers the tests assert: 1 file (`SKILL.md`), 1 section (`### 2. Dispatch`) holding
1 paragraph (Default 1) and 1 bullet (the writers bullet); 7 claims and 11 phrases, each judged in
its own scope (a claim holds when every one of its phrases is in its scope, lower-cased,
whitespace collapsed, quote marks dropped). Each phrase is fired at a planted removal. The
paragraph and the bullet are fired at the text they carried before (the old closing sentence,
which must be reported for exactly the four phrases the change added, and the bullet less its
clause); the retired word, the link and path guards and the line cap are fired at planted
positives and near-misses, because they are green on the text that came before. Every helper that
cuts a section, a paragraph or a bullet out of the file fails loudly when what it looks for is
absent or doubled.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL = (
    _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate" / "SKILL.md"
)

_EM = chr(0x2014)
_SEC = chr(0xA7)
_SECTION = "### 2. Dispatch"
_DEFAULT_1 = "**Default 1"
_WRITERS_BULLET = "- External CLIs: run via Bash"
_PARAGRAPH_HEAD_END = "instead of in this file."
_OLD_TAIL = (
    'If you are about to write "paste this into a new session", first say why '
    f"{_SEC}2a's launcher will not do."
)
_CORE_PATH = "plugins/core/skills/"
_LINE_CAP = 499
_HEADING = re.compile(r"^(#{1,6})\s")

_DEFAULT = "default 1"
_DISPATCH = "dispatch section"
_WRITERS = "writers bullet"

# (scope, claim, the phrases that must all be in the scope; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        _DEFAULT,
        "the default stays: auto-dispatch, and a brief the operator pastes is the fallback",
        (
            f"default 1 {_EM} auto-dispatch ({_SEC}2a), not a brief for the operator to paste.",
            "is the *fallback*",
        ),
    ),
    (
        _DEFAULT,
        "a prompt the operator asks for by name is written, not argued",
        ("a pasteable prompt the operator asks for by name is written, not argued",),
    ),
    (
        _DEFAULT,
        "a request by name measures what the launch costs and is not a lapse to correct",
        (
            "a request by name measures what the launch costs",
            "it is not a lapse to correct",
        ),
    ),
    (
        _DEFAULT,
        "unasked, the reason the launch will not do is still given before a brief is pasted",
        (
            'unasked, if you are about to write "paste this into a new session", '
            f"first say why a {_SEC}2a launch will not do",
        ),
    ),
    (
        _DISPATCH,
        "the plan's Dispatch column is still read off before dispatching",
        ("carries a required `dispatch` column",),
    ),
    (
        _WRITERS,
        "the bullet still isolates parallel writers by declared disjoint file sets",
        ("declared disjoint file sets", "never new git worktrees"),
    ),
    (
        _WRITERS,
        "the bullet names the execution lanes and the skill whose reference describes them",
        ("execution lanes", "`spec-driven-dev` reference"),
    ),
)
# What the change added to Default 1, as the phrases the closing sentence of old lacks.
_ADDED_TO_DEFAULT = (
    "a pasteable prompt the operator asks for by name is written, not argued",
    "a request by name measures what the launch costs",
    "it is not a lapse to correct",
    'unasked, if you are about to write "paste this into a new session", '
    f"first say why a {_SEC}2a launch will not do",
)
_CLAUSE = "; execution lanes: `spec-driven-dev` reference"


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _words(text: str) -> str:
    """Quote marks dropped from the line starts, whitespace folded, lower-cased."""
    unquoted = "\n".join(re.sub(r"^\s*>\s?", "", line) for line in text.split("\n"))
    return " ".join(unquoted.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _section(text: str, heading: str) -> str:
    """The one heading line that starts with `heading` and the lines under it, up to the next
    heading of the same or a higher level. A `#` line inside a fence is not a heading. Fails
    loudly when no line, or more than one, starts with `heading`."""
    lines = text.split("\n")
    inside = False
    fenced: list[bool] = []
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            fenced.append(True)
        else:
            fenced.append(inside)
    starts = [
        index
        for index, line in enumerate(lines)
        if not fenced[index] and _HEADING.match(line) and line.startswith(heading)
    ]
    assert len(starts) == 1, f"{heading!r} starts {len(starts)} headings, not 1"
    opening = _HEADING.match(lines[starts[0]])
    assert opening is not None
    body = [lines[starts[0]]]
    for index in range(starts[0] + 1, len(lines)):
        found = None if fenced[index] else _HEADING.match(lines[index])
        if found is not None and len(found[1]) <= len(opening[1]):
            break
        body.append(lines[index])
    return "\n".join(body)


def _paragraph(section: str, lead: str) -> str:
    """The one paragraph (a run of lines up to a blank line) of `section` that starts with
    `lead`. Fails loudly when no paragraph, or more than one, starts with it."""
    found = [part for part in section.split("\n\n") if part.startswith(lead)]
    assert len(found) == 1, f"{lead!r} starts {len(found)} paragraphs, not 1"
    return found[0]


def _bullet(section: str, lead: str) -> str:
    """The one bullet of `section` that starts a line with `lead`, up to the next bullet or the
    next blank line. Fails loudly when no line, or more than one, starts with `lead`."""
    lines = section.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(lead)]
    assert len(starts) == 1, f"{lead!r} starts {len(starts)} lines, not 1"
    body = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if not line.strip() or line.startswith("- "):
            break
        body.append(line)
    return "\n".join(body)


def _scopes(text: str) -> dict[str, str]:
    """The folded text of each scope a claim is judged in."""
    section = _section(text, _SECTION)
    return {
        _DEFAULT: _words(_paragraph(section, _DEFAULT_1)),
        _DISPATCH: _words(section),
        _WRITERS: _words(_bullet(section, _WRITERS_BULLET)),
    }


def _holds_a_link(text: str) -> bool:
    return "](" in text


def _names_the_core_path(text: str) -> bool:
    return _CORE_PATH in text


def _lines_over_the_cap(text: str) -> int:
    """How many lines `wc -l` counts above the cap; zero when the file is within it."""
    return max(0, text.count("\n") - _LINE_CAP)


def _real_scopes() -> dict[str, str]:
    return _scopes(_read(_SKILL))


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (7, 11)
    assert {scope for scope, _, _ in _ROWS} == {_DEFAULT, _DISPATCH, _WRITERS}
    assert set(_real_scopes()) == {_DEFAULT, _DISPATCH, _WRITERS}
    assert all(_real_scopes().values())
    assert len(_ADDED_TO_DEFAULT) == 4


@pytest.mark.parametrize(
    ("scope", "claim", "phrases"), _ROWS, ids=[row[1] for row in _ROWS]
)
def test_the_scope_states_the_claim(
    scope: str, claim: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_real_scopes()[scope], phrases)
    assert not missing, f"the {scope} does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real text in turn is the one gap reported,
    and an empty text lacks every phrase of a row. A phrase the check cannot see go would let
    the scope lose its claim and stay green."""
    scopes = _real_scopes()
    for scope, claim, phrases in _ROWS:
        text = scopes[scope]
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_default_1_as_it_stood_is_reported_for_the_four_added_phrases() -> None:
    """The closing sentence before the change is the known positive: the head of the real
    paragraph with the old sentence after it holds the default and the retired word, and lacks
    exactly the four phrases the change added."""
    real = _paragraph(_section(_read(_SKILL), _SECTION), _DEFAULT_1)
    folded = " ".join(real.split())
    end = folded.index(_PARAGRAPH_HEAD_END) + len(_PARAGRAPH_HEAD_END)
    old = _words(f"{folded[:end]} {_OLD_TAIL}")
    reported = [
        phrase
        for scope, _, phrases in _ROWS
        if scope == _DEFAULT
        for phrase in _missing(old, phrases)
    ]
    assert reported == list(_ADDED_TO_DEFAULT), reported
    assert "launcher" in old


def test_default_1_no_longer_calls_a_launcher_real() -> None:
    """Section 2a holds launch facts and no launcher script, so the paragraph must not name
    one. Fired at the old sentence, which does."""
    assert "launcher" not in _real_scopes()[_DEFAULT]
    assert "launcher" in _words(_OLD_TAIL)
    assert "launcher" not in _words(
        f"first say why a {_SEC}2a launch will not do, and the launch facts"
    )


def test_the_writers_bullet_as_it_stood_is_reported_for_its_clause() -> None:
    """The bullet less its clause is the known positive: it still isolates writers, and it
    lacks both phrases that name the execution lanes and the skill."""
    section = _section(_read(_SKILL), _SECTION)
    real = " ".join(_bullet(section, _WRITERS_BULLET).split())
    assert _CLAUSE in real, "the clause is not in the real bullet"
    old = _words(real.replace(_CLAUSE, ""))
    for scope, claim, phrases in _ROWS:
        if scope != _WRITERS:
            continue
        reported = _missing(old, phrases)
        if "isolates" in claim:
            assert reported == [], (claim, reported)
        else:
            assert reported == list(phrases), (claim, reported)


def test_the_bullet_holds_no_link_and_the_file_names_no_path_into_the_core_pack() -> (
    None
):
    text = _read(_SKILL)
    bullet = _bullet(_section(text, _SECTION), _WRITERS_BULLET)
    assert not _holds_a_link(bullet), "the writers bullet holds a markdown link"
    assert not _names_the_core_path(text), "SKILL.md names a path into the core pack"


def test_the_link_and_path_guards_see_planted_shapes_and_not_near_misses() -> None:
    """Fired at planted text, because both guards are green on the text that came before: a
    markdown link to the reference and a path into the core pack are reported; the plain-words
    clause, a backticked skill name and a link to a file of this pack are not path shapes of
    the other pack."""
    assert _holds_a_link("see [the reference](../spec-driven-dev/references/x.md)")
    assert not _holds_a_link(f"overlap, then{_CLAUSE}")
    assert _names_the_core_path(f"see {_CORE_PATH}spec-driven-dev/references/x.md")
    assert not _names_the_core_path("see `spec-driven-dev` and the core pack")
    assert not _names_the_core_path("see plugins/orchestration/skills/orchestrate")


def test_the_line_cap_is_fired_at_the_boundary_and_holds_for_the_real_file() -> None:
    """`wc -l` of a SKILL.md is at most 499. Fired at planted texts of 499 and 500 lines."""
    assert _lines_over_the_cap(_read(_SKILL)) == 0, (
        f"SKILL.md has {_read(_SKILL).count(chr(10))} lines, over the cap of {_LINE_CAP}"
    )
    assert _lines_over_the_cap("x\n" * _LINE_CAP) == 0
    assert _lines_over_the_cap("x\n" * (_LINE_CAP + 1)) == 1


def test_a_missing_section_paragraph_or_bullet_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="starts 0 headings"):
        _section("## Another\ntext\n", _SECTION)
    with pytest.raises(AssertionError, match="starts 2 headings"):
        _section(f"{_SECTION}\na\n{_SECTION}\nb\n", _SECTION)
    with pytest.raises(AssertionError, match="starts 0 paragraphs"):
        _paragraph("a paragraph\n\nanother\n", _DEFAULT_1)
    with pytest.raises(AssertionError, match="starts 2 paragraphs"):
        _paragraph(f"{_DEFAULT_1} one\n\n{_DEFAULT_1} two\n", _DEFAULT_1)
    with pytest.raises(AssertionError, match="starts 0 lines"):
        _bullet("- Another bullet\n", _WRITERS_BULLET)
    with pytest.raises(AssertionError, match="starts 2 lines"):
        _bullet(f"{_WRITERS_BULLET} one\n{_WRITERS_BULLET} two\n", _WRITERS_BULLET)


def test_a_section_paragraph_and_bullet_are_cut_where_they_end() -> None:
    """The section ends at the next heading of its level (a deeper heading and a fenced `#`
    line do not end it), a paragraph at its blank line, a bullet at the next bullet."""
    text = "\n".join(
        [
            _SECTION,
            "",
            f"{_DEFAULT_1} one**",
            "continued",
            "",
            "- first bullet",
            "  wrapped",
            f"{_WRITERS_BULLET} two",
            "  wrapped too",
            "- last bullet",
            "```text",
            "### 2. Dispatch",
            "```",
            "#### Deeper",
            "kept",
            "### 2a. Launch",
            "left out",
            "",
        ]
    )
    section = _section(text, _SECTION)
    assert "kept" in section and "left out" not in section
    assert _paragraph(section, _DEFAULT_1) == f"{_DEFAULT_1} one**\ncontinued"
    assert _bullet(section, _WRITERS_BULLET) == f"{_WRITERS_BULLET} two\n  wrapped too"
