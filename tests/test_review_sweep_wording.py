"""A fresh reader of a fix round sweeps past the diff and says what it did not check.

The fix-round rules of `post-task-review` brief a fresh reader with at most four claims and one
planted false claim. Neither that brief nor the consolidation critic told the reader to look at
the files the change did not edit, so a contradiction that the change introduced into another
skill passed a round the reader called clean; a pointer that names a line number or a commit id
went stale at the next edit or squash; the reader's return said what it confirmed and not how
far it got; and a ledger commit that was reviewed on one base landed on another when a peer's
chain landed first.

`references/fix-rounds.md` now says all four, as two notes under its second rule, so it still
counts three rules (another test holds that sentence): 2a says what the reader's brief adds (a
contradiction and pointer sweep over the files the change did not edit; a pointer that carries a
section number or a stable heading name, never only a line number or a commit id; a return that
ends with what the reader did not check), and 2b says a ledger commit is re-reviewed on the new
base when a peer's chain lands first. The introduction names both notes. The critic's C5 (the
self-contradiction sweep) reaches the files the batch did not edit and points at 2a. The text
that said none of this is kept below as `_OLD_FIX_ROUNDS` and `_OLD_CRITIC_C5`, unedited excerpts.

THE SURFACE, in numbers the tests assert: 4 places in 2 files (the introduction and notes 2a and
2b of the reference, and C5 of the critic's SKILL.md) and 20 sentences, each held whole
(lower-cased, bold marks dropped, whitespace collapsed) so that a clause cannot be dropped while
the rest of its sentence still matches. Each sentence occurs once in its place and is fired at a
planted removal and a planted cut of its last clause; each place is fired at the text it
replaced; a planted move shows that a claim is judged inside its place and not in the whole file;
and the added text is scanned for an id, a path or a commit id with a planted control for each. A
project's or a company's own name is not scanned for here: it has no generic shape, and naming one
in a test would publish it, so that part stays a reading check. The cap on a reader's real claims,
the intro's three-rule count and C6's phrases belong to other tests and are not asserted here.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"
_FIX_ROUNDS = _SKILLS / "post-task-review" / "references" / "fix-rounds.md"
_CRITIC_MD = _SKILLS / "consolidation-critic" / "SKILL.md"
_HEADING = re.compile(r"^(#{1,6})\s")
_EM = chr(0x2014)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same.
    A missing file is its own loud failure, never an empty match."""
    if not path.is_file():
        raise AssertionError(f"{path.name} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _flat(text: str) -> str:
    """Bold marks dropped, every run of whitespace one space, lower-cased: a re-wrapped line or
    a re-emphasised word is not a different sentence."""
    return " ".join(text.replace("**", "").split()).lower()


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or
    a higher level; a `#` line inside a fenced block is not a heading. A missing heading fails
    loudly, with the heading named."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


def _introduction(text: str, where: str) -> str:
    """The text between the title and the first numbered heading."""
    start = text.find("\n\n")
    stop = text.find("\n## 1.")
    if start < 0 or stop < 0 or stop < start:
        raise AssertionError(
            f"{where}: no introduction before the first numbered heading"
        )
    return text[start:stop]


def _note_2a(text: str, where: str) -> str:
    return _section(text, "### 2a.", where)


def _note_2b(text: str, where: str) -> str:
    return _section(text, "### 2b.", where)


def _check_5(text: str, where: str) -> str:
    return _section(text, "### C5", where)


# The sentences of each place, whole, in order: lower-cased, bold marks dropped, whitespace
# collapsed. A bold lead that opens a bullet is a sentence of its own.
_INTRO_SENTENCES: tuple[str, ...] = (
    "two notes under it say what the reader's brief adds (2a) and when a peer's landing calls "
    "for the review again (2b).",
)
_NOTE_2A_SENTENCES: tuple[str, ...] = (
    "a fresh reader's brief asks for more than the claims.",
    "these asks are not claims, so the cap on real claims stands.",
    "a contradiction and pointer sweep over the files the change did not edit.",
    "the reader greps the old claim, not the new one, in every skill, reference, readme and "
    "rule file that cites the changed place.",
    "a fix round's contradictions sit in text the diff does not show, so a reader given only "
    "the diff cannot find them (observed once: a review found blocking contradictions in "
    "skills that the change had not edited).",
    "every pointer carries a section number or a stable heading name, never only a line "
    "number or a commit id.",
    "a line number moves with the next edit above it, and a squash merge makes a commit id "
    "unreliable.",
    "the reader checks that each pointer to a changed place carries one of the two, still "
    "resolves, and names a place that still says what the pointer claims.",
    "the return ends with what the reader did not check.",
    "step 9 of the review asks the same of its author.",
    "the reader lists the files, claims and places it did not reach and says how it knows the "
    "list is complete, or says unknown.",
    "a return with no such list does not say how far the reader got, so read it as unverified "
    "beyond what it names.",
)
_NOTE_2B_SENTENCES: tuple[str, ...] = (
    "a reader's verdict covers the base it read.",
    "when a peer's chain of commits lands first on the branch a change will land on, re-review "
    "the change's ledger commits (the commits that add dated entries to a shared changelog, "
    "board or log) on the new base before they land.",
    "their entries, the order of those entries and the counts they quote were checked against "
    "a tree that has since moved, and the peer's entries now sit beside them.",
    "a fresh reader reads the commit as rebuilt on the new base, not the commit that was "
    "reviewed before (observed more than once in one release: each rebuild called for its "
    "readers again).",
)
_CHECK_5_SENTENCES: tuple[str, ...] = (
    "the sweep reaches the files the batch did not edit: grep the old claim in every skill, "
    "reference and readme that cites a promoted rule, because a contradiction sits where the "
    "diff does not look.",
    "the fresh reader of c6 carries the same sweep and checks that each pointer in the batch "
    "names a section number or a stable heading name, never only a line number or a commit id.",
    "its return ends with what it did not check (`post-task-review`, fix-rounds reference, "
    "section 2a).",
)

# The reference as it stood: the title, the introduction and the second rule, with the lines
# that remain unedited and the text of the first and third rules shortened to their first lines.
_OLD_FIX_ROUNDS = """\
# Reviewing a fix round

Step 5 of the review says to re-run the review over the diff the fixes produced. Three rules say how,
for a round of fixes to a document, plan, rule or report that others will act on, and the third also
for the checks of any change. The first costs only reading order and the third only running order.
The second is one more agent run, so it is kept for a round that rewrote claims.

## 1. Order: the dense spots first, and every new clause against the rest of the document

Review first, and whole, any row or section where one pass applied several findings, and check each
new clause against claims elsewhere in the document.

## 2. A fresh reader, given a planted false claim

When a fix round rewrote claims others will act on, a fresh reader runs the re-review: a new agent
that re-derives each claim from the pinned source, not from the artifact's own citations, and is
given one planted false claim to reject.

## 3. Order the checks by cost: the long validation last, once, on frozen files

A fix made after a check voids that check.
"""

# The same file with both notes' headings and none of their text: a note that exists and says
# nothing.
_STUB_FIX_ROUNDS = _OLD_FIX_ROUNDS.replace(
    "## 3. Order the checks",
    "### 2a. The reader's brief reaches past the diff\n\nAsk someone.\n\n"
    "### 2b. A ledger commit is reviewed on one base\n\nLook again.\n\n"
    "## 3. Order the checks",
)

_OLD_CRITIC_C5 = f"""\
## The Checks

### C5 {_EM} Self-contradiction sweep

A promotion that corrects a fact must correct **every** statement of that fact in the same file and
its siblings. Grep the *old* claim, not the new one {_EM} the stale copy is what you are hunting.

> **Caught:** a skill whose prose was updated to "renders fine via WebFetch" while a table seven
> rows below still said "Unreliable".

### C6 {_EM} Epistemic audit
"""


class _Place(NamedTuple):
    name: str
    path: Path
    locate: Callable[[str, str], str]
    sentences: tuple[str, ...]
    old: str


_PLACES: tuple[_Place, ...] = (
    _Place(
        "reference-introduction",
        _FIX_ROUNDS,
        _introduction,
        _INTRO_SENTENCES,
        _OLD_FIX_ROUNDS,
    ),
    _Place(
        "reference-note-2a",
        _FIX_ROUNDS,
        _note_2a,
        _NOTE_2A_SENTENCES,
        _STUB_FIX_ROUNDS,
    ),
    _Place(
        "reference-note-2b",
        _FIX_ROUNDS,
        _note_2b,
        _NOTE_2B_SENTENCES,
        _STUB_FIX_ROUNDS,
    ),
    _Place("critic-c5", _CRITIC_MD, _check_5, _CHECK_5_SENTENCES, _OLD_CRITIC_C5),
)
_HEADED = tuple(p for p in _PLACES if p.name != "reference-introduction")


def _gaps_in(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _gaps(place: _Place, text: str) -> list[str]:
    return _gaps_in(_flat(place.locate(text, place.path.name)), place.sentences)


def _real(place: _Place) -> str:
    return _read(place.path)


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    """4 places in 2 files and 20 sentences; no sentence stands twice or inside another of its place."""
    assert len(_PLACES) == 4
    assert len({p.path for p in _PLACES}) == 2
    assert sum(len(p.sentences) for p in _PLACES) == 20
    for place in _PLACES:
        assert len(set(place.sentences)) == len(place.sentences), place.name
        for sentence in place.sentences:
            others = [s for s in place.sentences if s != sentence]
            assert not any(sentence in other for other in others), (
                place.name,
                sentence,
            )
        assert all(s == s.lower() for s in place.sentences), place.name


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_states_its_sentences(place: _Place) -> None:
    """Red before the change: none of these sentences, and two of the places, existed."""
    assert _gaps(place, _real(place)) == []


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_sentence_occurs_once_and_is_reported_when_it_goes(place: _Place) -> None:
    """Planted removal: each sentence cut out of the real place is the one gap reported, and an
    empty place lacks every sentence. A sentence that occurred twice would let a clause go and
    stay green."""
    flat = _flat(place.locate(_real(place), place.path.name))
    assert _gaps_in(flat, place.sentences) == []
    for sentence in place.sentences:
        assert flat.count(sentence) == 1, (
            f"{sentence!r} occurs {flat.count(sentence)} times"
        )
        assert _gaps_in(flat.replace(sentence, ""), place.sentences) == [sentence]
    assert _gaps_in("", place.sentences) == list(place.sentences)


def _has_clause(sentence: str) -> bool:
    return re.search(r"[,:] ", sentence) is not None


# The introduction's one sentence has no comma or colon, so there is no clause to cut from it:
# it stays out of this test, which would otherwise pass on it with nothing cut.
_CUTTABLE = tuple(p for p in _PLACES if any(_has_clause(s) for s in p.sentences))


@pytest.mark.parametrize("place", _CUTTABLE, ids=[p.name for p in _CUTTABLE])
def test_a_clause_cut_from_its_sentence_is_reported(place: _Place) -> None:
    """Planted clause removal: the words after the last comma or colon of a sentence are cut out
    of the real place, and the place then reports exactly that sentence. A check on a fragment of
    the sentence would stay green."""
    flat = _flat(place.locate(_real(place), place.path.name))
    cut = 0
    for sentence in place.sentences:
        if not _has_clause(sentence):
            continue
        tail = re.split(r"[,:] ", sentence)[-1]
        cut += 1
        assert flat.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
        assert _gaps_in(flat.replace(tail, ""), place.sentences) == [sentence], sentence
    assert cut == sum(_has_clause(s) for s in place.sentences) > 0, place.name


def test_the_cut_test_covers_three_places() -> None:
    """3 of the 4 places have a sentence with a clause to cut; the introduction does not."""
    assert [p.name for p in _CUTTABLE] == [
        "reference-note-2a",
        "reference-note-2b",
        "critic-c5",
    ]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_place_reports_the_text_it_replaced(place: _Place) -> None:
    """Known positive: the place as it stood, or with its heading and no text, lacks every
    sentence, so a red on the old text is a red for the text and not for a broken helper."""
    assert _gaps(place, place.old) == list(place.sentences)


@pytest.mark.parametrize("place", _HEADED, ids=[p.name for p in _HEADED])
def test_a_missing_heading_fails_loudly(place: _Place) -> None:
    """The reference as it stood has neither note, and the critic text without C5 has no such
    section: the finder says so, naming the heading, and never reads it as an empty pass."""
    stood = (
        _OLD_FIX_ROUNDS
        if place.path == _FIX_ROUNDS
        else _OLD_CRITIC_C5.replace("### C5", "### C9")
    )
    with pytest.raises(AssertionError, match="no heading starting"):
        _gaps(place, stood)


@pytest.mark.parametrize("width", [40, 72, 100])
@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_rewrapped_and_reemphasised_place_still_holds_its_claims(
    place: _Place, width: int
) -> None:
    """Near-miss that must NOT be reported: the real place filled again at `width` columns, with
    bold marks around one more word, is the same text."""
    region = place.locate(_real(place), place.path.name)
    filled = textwrap.fill(
        " ".join(region.split()),
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    reshaped = filled.replace(" the ", " **the** ", 1)
    assert "**the**" in reshaped, "the planted emphasis changed nothing"
    assert _gaps_in(_flat(reshaped), place.sentences) == []


@pytest.mark.parametrize("place", _HEADED, ids=[p.name for p in _HEADED])
def test_the_claims_are_judged_inside_their_place_only(place: _Place) -> None:
    """Planted move: the body of the place cut out and put after the last line of the file is a
    place that lacks every claim. A search of the whole file would still find them and pass, which
    is why each claim is read from its own place."""
    text = _real(place)
    region = place.locate(text, place.path.name)
    head, _, body = region.partition("\n")
    assert body.strip(), "no body to move"
    moved = text.replace(region, head + "\n\n") + "\n" + body
    assert _gaps(place, moved) == list(place.sentences)
    assert _gaps_in(_flat(moved), place.sentences) == [], (
        "a whole-file search would have passed"
    )


# --- where the text sits -----------------------------------------------------------------------


def test_the_notes_sit_under_the_second_rule_and_the_rules_stay_three() -> None:
    """2a and 2b are notes under rule 2, between it and rule 3, so the reference still counts
    three rules and every pointer to its section 2 still reaches the fresh reader."""
    lines = _read(_FIX_ROUNDS).split("\n")
    rules = [line for line in lines if re.match(r"## \d+\.", line)]
    assert len(rules) == 3, rules
    order = [m[1] for line in lines if (m := re.match(r"#{2,3} (\d+[ab]?\.)", line))]
    assert order == ["1.", "2.", "2a.", "2b.", "3."], order


_NAMED_SECTION = re.compile(r"fix-rounds reference, section (\w+)\)")


def test_the_critic_names_the_note_in_plain_text_and_the_note_exists() -> None:
    """C5 names the reference by skill and section, as C6 does and without a markdown link, and
    the section it names is the note that holds the sweep."""
    c5 = _check_5(_read(_CRITIC_MD), "SKILL.md")
    assert "](" not in c5, "C5 links to the fix-round text instead of naming it"
    named = _NAMED_SECTION.findall(_flat(c5))
    assert named == ["2a"], named
    target = _flat(_note_2a(_read(_FIX_ROUNDS), "fix-rounds.md"))
    assert (
        "a contradiction and pointer sweep over the files the change did not edit."
        in target
    )


def test_the_critic_keeps_its_eight_checks_and_adds_no_ninth() -> None:
    """The sweep sits inside C5: the checks are still C1 to C8, in order."""
    checks = _section(_read(_CRITIC_MD), "## The Checks", "SKILL.md")
    found = re.findall(r"(?m)^### (C\d+) ", checks)
    assert found == [f"C{n}" for n in range(1, 9)], found


# --- the added text is neutral -----------------------------------------------------------------

# The shapes are generic, so the scan names no project.
_LEAKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a request id", re.compile(r"\b[A-Z]{1,4}-\d{1,3}\b")),
    # One group for the home paths: the publication-hygiene test forbids the spelled-out
    # literal in every tracked file, this one included.
    ("an absolute local path", re.compile(r"(?:\b[A-Za-z]:[\\/]|/(?:Users|home)/)")),
    ("a commit-id-like token", re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")),
)


def _leaks(text: str) -> list[str]:
    return [label for label, pattern in _LEAKS if pattern.search(text)]


def test_the_added_text_names_no_id_path_or_commit() -> None:
    """The kit is public. The introduction, both notes and C5 carry none of the shapes."""
    for place in _PLACES:
        region = place.locate(_real(place), place.path.name)
        assert _leaks(region) == [], place.name


def test_the_leak_scan_sees_each_shape_and_spares_the_near_misses() -> None:
    """Known positives, one per shape, and near-misses that must stay clean."""
    planted = {
        "a request id": "see " + "K" + "-8 for the reason",
        "an absolute local path": "read " + "C:" + "/Us" + "ers/someone/notes.md",
        "a commit-id-like token": "as of commit " + "0a1b2c3d4e",
    }
    assert set(planted) == {label for label, _ in _LEAKS}
    for label, text in planted.items():
        assert _leaks(text) == [label], (label, _leaks(text))
    for clean in (
        "section 2a of the fix-rounds reference, step 9 and C5",
        "a defaced page, an effaced line and the word accede",
        "the 3 files and 12 lines it names",
    ):
        assert _leaks(clean) == [], clean


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder keeps a deeper heading and a `#` line inside a fence, stops at the next heading
    of its level, and runs to the end when none follows."""
    planted = "\n".join(
        [
            "### 2a. First",
            "first body",
            "#### deeper",
            "deeper body",
            "```bash",
            "### 2b. not a heading inside a fence",
            "```",
            "### 2b. Second",
            "second body",
            "",
        ]
    )
    first = _section(planted, "### 2a.", "planted")
    assert "deeper body" in first and "not a heading" in first
    assert "second body" not in first
    assert "second body" in _section(planted, "### 2b. Second", "planted")
