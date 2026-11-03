"""The two adopter docs say which `.ai/` files the kit manages, and what overwrites them.

`docs/faq.md` and `docs/adoption-guide.md` each promised that an adopter's `AGENTS.md`,
`CLAUDE.md` and `.ai/` files "are yours and are never updated behind you". That holds for
the state logs, and for `AGENTS.md` and `CLAUDE.md` outside a marked block. It does not hold
for the rest of what the scaffold places under `.ai/`: a plain run skips such a file once
the adopter has edited it, and `--force` overwrites it with the kit's copy (measured with
the real helper in a throwaway target: edit, plain run, `--dry-run --force`, `--force`).
The guide said the same thing three more times in other words: "you own all of them" and
"a small set of project-owned files", each describing a set that a table marks partly
kit-managed, and "refreshed on update", for a refresh that only `--force` performs.

Three rules share one scan surface. The ABSENCE rule reads each document whole, one
sentence at a time, for the four shapes above. The PRESENCE rule reads four named sections
(one in the FAQ, three in the guide) and requires each to state the exception in its own
text, not in another section's. The ROW rule reads the guide's ownership table and requires
every kit-managed row to say what overwrites it, because a clause on one row reads as
true of that row alone.
`test_the_scan_surface_is_what_the_name_claims` asserts those numbers, so a heading that
moves or a document that shrinks fails there instead of narrowing the scan in silence.

Not covered, on purpose: a fourth wording of the same promise ("everything under `.ai/` is
yours", "the `.ai/` directory never changes") is not a shape here. Whitespace is folded
before every match, because the documents wrap their lines.
"""

import textwrap
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_FAQ = "docs/faq.md"
_GUIDE = "docs/adoption-guide.md"
_DOCS = (_FAQ, _GUIDE)

_WHOLE_SET = "the whole .ai/ set is yours or never updated"
_OWN_ALL = "the reader owns everything the kit places"
_REFRESH = "a refresh with no condition on it"
_SET_OWNED = "the set the helper writes is called project-owned as a whole"

# (shape, the phrase that carries it, and the phrases of which one must share its sentence;
# empty means the carrying phrase is the whole claim)
_OLD_SHAPES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (_WHOLE_SET, "`.ai/` files", ("are yours", "never updated")),
    (_OWN_ALL, "you own all of them", ()),
    (_REFRESH, "refreshed on update", ()),
    (_SET_OWNED, "project-owned", ("set of",)),
)

# What an update section must state: who is never touched, what is kit-managed, what
# overwrites it, and how to see the plan first.
_EXCEPTION = (
    "outside their marked blocks",
    "kit-managed",
    "`skipped N locally modified managed file(s)`",
    "`--force` overwrites",
    "`--dry-run` shows the plan first",
)

# The guide's ownership table, and what each kit-managed row of it must say.
_TABLE = "### What it writes, and who owns it"
_OVERWRITE = "refreshed with `--force`"

# document -> (heading of a section it must state the exception in, the phrases it needs)
_REQUIRED: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    _FAQ: (("## How do skills get updated?", ("`.ai/` intake and logs", *_EXCEPTION)),),
    _GUIDE: (
        (
            "### What the kit does not do",
            ("which of them you own and which the kit manages",),
        ),
        (_TABLE, (_OVERWRITE,)),
        ("## 7. Staying up to date", ("`.ai/` state logs", *_EXCEPTION)),
    ),
}


def _read(doc: str) -> str:
    return (_ROOT / doc).read_text(encoding="utf-8")


def _sentences(text: str) -> list[str]:
    """Sentences of the folded text; a table row is a sentence of its own."""
    folded = " ".join(text.split())
    for end in ("? ", "! ", " | | "):
        folded = folded.replace(end, ". ")
    return folded.split(". ")


def _section_lines(text: str, heading: str) -> list[str]:
    """The lines under `heading`, up to the next heading at the same or a shallower level.

    A `#` line inside a fenced block is a shell comment, not a heading. A heading that is not
    found raises: a guard that cannot find its section would be passing on nothing.
    """
    depth = len(heading) - len(heading.lstrip("#"))
    body: list[str] = []
    found = False
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        level = len(line) - len(line.lstrip("#"))
        is_heading = not fenced and 0 < level <= 6 and line[level : level + 1] == " "
        if found and is_heading and level <= depth:
            break
        if found:
            body.append(line)
        elif is_heading and line.rstrip() == heading:
            found = True
    if not found:
        raise AssertionError(f"heading not found: {heading!r}")
    return body


def _section(text: str, heading: str) -> str:
    """The folded body under `heading`."""
    return " ".join(" ".join(_section_lines(text, heading)).split())


def _kit_managed_rows(text: str, heading: str) -> list[str]:
    """The folded table rows under `heading` that call a file kit-managed."""
    return [
        " ".join(line.split())
        for line in _section_lines(text, heading)
        if line.startswith("|") and "kit-managed" in line.lower()
    ]


def _bare_kit_managed_rows(text: str) -> list[str]:
    """Every kit-managed row of the ownership table that does not say what overwrites it."""
    return [row for row in _kit_managed_rows(text, _TABLE) if _OVERWRITE not in row]


def _blanket_claims(text: str) -> list[str]:
    """Every sentence that carries one of the three old shapes, named by shape.

    Matched case-insensitively, so a re-capitalised copy of the old sentence is still one.
    """
    return [
        f"{name}: {sentence}"
        for sentence in _sentences(text)
        for name, phrase, claims in _OLD_SHAPES
        if phrase in sentence.lower()
        and (not claims or any(c in sentence.lower() for c in claims))
    ]


def _missing(doc: str, text: str) -> list[str]:
    """Every phrase a named section of `doc` should state and does not."""
    missing: list[str] = []
    for heading, phrases in _REQUIRED[doc]:
        section = _section(text, heading)
        missing += [
            f"{heading!r} does not state {p!r}" for p in phrases if p not in section
        ]
    return missing


def _rewrap(text: str, width: int) -> str:
    """Re-flow every plain paragraph at `width`; headings, tables, lists and fences stay put."""
    return "\n\n".join(
        textwrap.fill(
            " ".join(block.split()),
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if block[:1].isalpha() and "```" not in block
        else block
        for block in text.split("\n\n")
    )


def _good_fixture(doc: str) -> str:
    """A document whose named sections state every phrase the presence rule wants."""
    parts: list[str] = []
    for heading, phrases in _REQUIRED[doc]:
        parts += [heading, "", "Fixture: " + " and ".join(phrases) + ".", ""]
    return "\n".join(parts)


@pytest.mark.parametrize("doc", _DOCS)
def test_no_blanket_claim_survives(doc: str) -> None:
    claims = _blanket_claims(_read(doc))
    assert not claims, (
        f"{doc} still promises more than the scaffold does:\n" + "\n".join(claims)
    )


@pytest.mark.parametrize("doc", _DOCS)
def test_the_kit_managed_exception_is_stated(doc: str) -> None:
    missing = _missing(doc, _read(doc))
    assert not missing, f"{doc} does not state the exception:\n" + "\n".join(missing)


@pytest.mark.parametrize("doc", _DOCS)
@pytest.mark.parametrize("width", [37, 61])
def test_a_rewrapped_document_still_passes(doc: str, width: int) -> None:
    rewrapped = _rewrap(_read(doc), width)
    assert rewrapped != _read(doc), "the re-wrap changed nothing, so it proves nothing"
    assert _blanket_claims(rewrapped) == []
    assert _missing(doc, rewrapped) == []


def test_every_kit_managed_row_says_what_overwrites_it() -> None:
    bare = _bare_kit_managed_rows(_read(_GUIDE))
    assert not bare, (
        f"{_GUIDE} has kit-managed rows that do not say what overwrites them:\n"
        + "\n".join(bare)
    )


# ---- controls: the checks above are fired at known positives and at near misses ----

# The old sentences at the wrap each document gave them, then the other two shapes.
_PLANTED: tuple[tuple[str, str], ...] = (
    (
        _WHOLE_SET,
        "Your `AGENTS.md`, `CLAUDE.md` and `.ai/` files are yours and are never updated behind\n"
        "you. There is no separate release channel either.",
    ),
    (
        _WHOLE_SET,
        "updates. Your `AGENTS.md`, `CLAUDE.md` and `.ai/` files are yours and are never\n"
        "updated behind you.",
    ),
    # The same promise with a word added, with "never updated" alone, and re-capitalised.
    (_WHOLE_SET, "Your `AGENTS.md`, `CLAUDE.md` and the `.ai/` files are yours."),
    (_WHOLE_SET, "The `.ai/` files are never updated by the kit."),
    (_WHOLE_SET, "Your `.ai/` Files Are Yours And Are Never Updated Behind You."),
    (_OWN_ALL, "listed in\n[section 4](#4-set-up-a-project), and you own all of them."),
    (
        _REFRESH,
        "| `.ai/templates/tasks.md` | Spec templates | kit-managed - refreshed on update |",
    ),
    # The introduction of the table, at the wrap it had, then re-capitalised.
    (
        _SET_OWNED,
        "and your CI workflows, and writes a small set of **project-owned** files, with\n"
        "the placeholders filled from what it found.",
    ),
    (_SET_OWNED, "It writes a small set of\n**Project-Owned** files."),
)

# True sentences that sit close to the old shapes and must not be flagged.
_NEAR_MISSES: tuple[str, ...] = (
    "Your `AGENTS.md` and `CLAUDE.md` outside their marked blocks, and your `.ai/` state logs, "
    "are yours and are never updated behind you.",
    "The kit-managed `.ai/` files are overwritten by `--force`.",
    "| `.ai/learnings.md` | Empty intake file | **yours** - never overwritten |",
    "Put your rules in a file you own.",
    "A template is kit-managed - refreshed with `--force`.",
    "The retired plugin id will never be updated again.",
    "The helper kept 1 project-owned seed file(s) (use --reseed to overwrite).",
    "It writes a small set of files, each marked below as **yours** or kit-managed.",
)


@pytest.mark.parametrize("doc", _DOCS)
@pytest.mark.parametrize(("shape", "planted"), _PLANTED)
def test_a_planted_old_sentence_is_flagged(doc: str, shape: str, planted: str) -> None:
    text = _read(doc)
    before = _blanket_claims(text)
    after = _blanket_claims(f"{text}\n\n{planted}\n")
    assert len(after) == len(before) + 1, (shape, after[len(before) :])
    assert after[-1].startswith(shape), after[-1]


@pytest.mark.parametrize("sentence", _NEAR_MISSES)
def test_a_true_near_miss_is_not_flagged(sentence: str) -> None:
    assert _blanket_claims(sentence) == []


@pytest.mark.parametrize("doc", _DOCS)
def test_the_presence_rule_passes_a_good_section_and_fails_a_gutted_one(
    doc: str,
) -> None:
    good = _good_fixture(doc)
    phrases = [p for _, group in _REQUIRED[doc] for p in group]
    assert _missing(doc, good) == []
    for width in (37, 61):
        rewrapped = _rewrap(good, width)
        assert any(p not in rewrapped for p in phrases), "the re-wrap split no phrase"
        assert _missing(doc, rewrapped) == []
    for phrase in phrases:
        assert _missing(doc, good.replace(phrase, "")), (
            f"deleting {phrase!r} went unseen"
        )


@pytest.mark.parametrize("doc", _DOCS)
def test_the_presence_rule_does_not_borrow_a_phrase_from_another_section(
    doc: str,
) -> None:
    good = _good_fixture(doc)
    for phrase in [p for _, group in _REQUIRED[doc] for p in group]:
        moved = good.replace(phrase, "") + f"\n## Elsewhere\n\nFixture: {phrase}.\n"
        assert phrase in _section(moved, "## Elsewhere")
        owners = [h for h, group in _REQUIRED[doc] if phrase in group]
        assert _missing(doc, moved) == [
            f"{h!r} does not state {phrase!r}" for h in owners
        ], f"{phrase!r} was read from a section that does not own it"


_BARE_ROW = "| `.ai/git-stacked-pr-workflow.md` | Reference doc | kit-managed |"
_CLAUSE_ROW = "| `.ai/templates/tasks.md` | Spec templates | kit-managed - refreshed with `--force` |"
_YOURS_ROW = (
    "| `.ai/learnings.md` | Empty intake file | **yours** - never overwritten |"
)


def _table_fixture(*rows: str) -> str:
    """The ownership table's heading and header row over `rows`."""
    header = ("| File | What it is | Ownership |", "|---|---|---|")
    return "\n".join((_TABLE, "", *header, *rows, ""))


def test_the_row_rule_flags_a_bare_row_and_passes_the_others() -> None:
    assert _bare_kit_managed_rows(_table_fixture(_CLAUSE_ROW, _YOURS_ROW)) == []
    assert _bare_kit_managed_rows(
        _table_fixture(_CLAUSE_ROW, _BARE_ROW, _YOURS_ROW)
    ) == [_BARE_ROW]
    capitalised = _BARE_ROW.replace("kit-managed", "Kit-managed")
    assert _bare_kit_managed_rows(_table_fixture(capitalised)) == [capitalised]


def test_the_row_rule_reads_the_ownership_table_rows_only() -> None:
    other_row = "| `.ai/other.md` | Other | kit-managed |"
    assert _bare_kit_managed_rows(_table_fixture(other_row)) == [other_row]
    prose = "A kit-managed file says in its row what overwrites it."
    table = _table_fixture(_CLAUSE_ROW, _YOURS_ROW)
    elsewhere = f"## Elsewhere\n\n{other_row}\n"
    assert _bare_kit_managed_rows(f"{table}\n{prose}\n\n{elsewhere}") == []


# Two table rows fold into one line, so they read as one sentence unless the cutter splits
# them: a promise in each row is two claims, and a phrase in one row beside a promise in
# the next is none.
_ADJACENT_ROWS: tuple[tuple[str, int], ...] = (
    (
        "| `.ai/templates/a.md` | A | kit-managed - refreshed on update |\n"
        "| `.ai/templates/b.md` | B | kit-managed - refreshed on update |\n",
        2,
    ),
    (
        "| `.ai/` files | Scratch | kit-managed |\n"
        "| `.ai/learnings.md` | Intake | yours - never updated |\n",
        0,
    ),
)


@pytest.mark.parametrize(
    ("table", "claims"),
    _ADJACENT_ROWS,
    ids=["a promise in each row", "the phrase and the promise in different rows"],
)
def test_adjacent_table_rows_are_judged_one_at_a_time(table: str, claims: int) -> None:
    assert len(_blanket_claims(table)) == claims


_SYNTHETIC = "\n".join(
    (
        "# Title",
        "",
        "## Alpha",
        "",
        "alpha text",
        "",
        "```sh",
        "# a shell comment is not a heading",
        "```",
        "",
        "still alpha",
        "",
        "### Inner",
        "",
        "inner text",
        "",
        "## Beta",
        "",
        "beta text",
        "",
    )
)


def test_the_section_cutter_ignores_fences_and_fails_loudly() -> None:
    alpha = _section(_SYNTHETIC, "## Alpha")
    assert "still alpha" in alpha, "a shell comment in a fence ended the section early"
    assert "inner text" in alpha, "a deeper heading ended the section"
    assert "beta text" not in alpha, "the section ran past the next same-level heading"
    assert _section(_SYNTHETIC, "### Inner") == "inner text"
    with pytest.raises(AssertionError, match="heading not found"):
        _section(_SYNTHETIC, "## Gamma")


def test_the_scan_surface_is_what_the_name_claims() -> None:
    assert _DOCS == ("docs/faq.md", "docs/adoption-guide.md")
    assert len(_OLD_SHAPES) == 4
    assert sum(len(_REQUIRED[doc]) for doc in _DOCS) == 4
    # One row per group of managed files: the templates, the stacked-PR note, the ignore files.
    assert len(_kit_managed_rows(_read(_GUIDE), _TABLE)) == 3
    for doc, floor in ((_FAQ, 100), (_GUIDE, 180)):
        assert len(_sentences(_read(doc))) >= floor, f"{doc} reads as a stub"
    for doc in _DOCS:
        for heading, _ in _REQUIRED[doc]:
            assert len(_section(_read(doc), heading)) >= 150, (doc, heading)
