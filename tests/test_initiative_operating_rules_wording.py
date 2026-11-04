"""The planner's operating rules say how an initiative's own run is operated.

An initiative ran for a week before anyone wrote down how the run itself was to be operated, and each
answer then arrived late. The operator's rulings came one at a time, the last of them after every
gate was green. Decisions for the operator piled up faster than anyone triaged them. A kickoff re-read
a large state to find that nothing had happened. The drive filled, the initiative's folder was in no
commit, and one push at the end kept a week of work away from CI and from reviewers.

`references/operating-rules.md` is new. It opens with one line that says when to read it, then
holds six sections, one rule each, the rule first and its reason after: take the piecemeal rulings in
one gate before any session starts; keep open decisions to a budget; put a stop condition in every
kickoff; check the environment before each wave (free disk and a janitor, the markdown lint, the
usage reading, the shell hook); mirror the initiative's folder outside the checkout; decide the push
policy at the gate. A number is a starting value, uncalibrated, unless it is marked observed with its
date, and the tests hold every sentence that carries one.

THE SURFACE, in numbers the tests assert: 10 claims and 25 sentences in 1 file, over 6 sections (the
fourth holds five claims, a lead and four list items), a file of 50 to 80 lines, and 3 files for the
hygiene scan. A claim holds when its paragraph or list item holds every one of its sentences whole
(lower-cased, bold marks dropped, whitespace collapsed), so a clause cannot be dropped while the rest
of its sentence still matches. Each sentence occurs once in its section and is fired at a planted
removal; 13 of them carry a clause that is cut out in turn. The scan reads the three files this change
touches outside the tests, whole: the new file and the two templates it sits beside.

Green on the old text by construction, and said so where they are: the surface (a count) fails on
the old text only because the file is not there, and the finders and the two instruments are fired at
planted text. Every other check is red on the old text, which had no such file.

CLASSES OF SHAPE covered: a sentence dropped; a clause dropped; a section emptied; a claim moved to
another section, where a whole-file search would still find it; a re-wrap and a re-emphasis, which
are the same text; a number with no label; a request id, a commit id and an absolute path planted in
text, beside near-misses that must pass. Shapes not covered are the order of the sections' sentences
and any wording outside the claims; a project or company name is not scanned for here, because
naming one in a test would publish it, and the repository-wide hygiene scan owns that.
"""

import re
from pathlib import Path

import pytest

_PLANNER = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "initiative-planner"
    / "references"
)
_RULES = _PLANNER / "operating-rules.md"
_HYGIENE_FILES: tuple[Path, ...] = (
    _RULES,
    _PLANNER / "charter-template.md",
    _PLANNER / "roadmap-template.md",
)
_HEADING = re.compile(r"^(#{1,6})\s")
_FENCE = "```"
_CLAUSE = re.compile(r"[,:] ")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

_TITLE = "# Operating rules"
_WHEN = "Read this at the first gate of an initiative, before any session of the plan starts, and again at each release boundary."
_HEADINGS: tuple[str, ...] = (
    "## 1. Take the piecemeal rulings in one gate, before any session starts",
    "## 2. Keep open decisions to a budget",
    "## 3. Put a stop condition in every kickoff",
    "## 4. Check the environment before each wave",
    "## 5. Mirror the initiative's folder outside the checkout",
    "## 6. Decide the push policy at the gate",
)
_LABELS = ("(starting value, uncalibrated)", "(observed")
_REFERENCE = re.compile(r"\b(?:step|section) \d+\b")

# (claim id, the heading of the ONE section that must hold it, the sentences of its paragraph or list
# item, whole, in order; lower-cased, bold marks dropped, whitespace collapsed). The first sentence
# of a claim is the bold lead that opens its paragraph or item. The claims, in order: the five
# rulings taken in one gate; the budget of open decision rows; the stop condition of a kickoff; the
# four checks of the environment (the lead and one item each: free disk, markdown lint, usage
# reading, shell hook); the mirror and the intake entry; the push policy.
_CLAIMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "one-gate",
        _HEADINGS[0],
        (
            "take the rulings that arrive piecemeal in one gate, before any session starts: "
            "the publication invariants (what must never reach anything pushed), the push "
            "policy (section 6), the hand-off standard (the one set of sections every "
            "hand-off carries), the usage guard's owner and account (who keeps it, and "
            "whose usage it reads), and the owner of the release queue (the one session "
            "that lands finished work).",
            "asked one at a time during the run, each answer reopens work done under the "
            "opposite assumption (observed, 2026-11-03 to 2026-11-04: all five arrived as "
            "separate rulings mid-run, and the push policy and the queue owner were still "
            "open when the last batch of commits was ready to land).",
        ),
    ),
    (
        "budget",
        _HEADINGS[1],
        (
            "keep at most about 10 open decision rows per release (starting value, "
            "uncalibrated), each with an owner and a trigger, and when a session adds a row "
            "it says which row it replaces.",
            "an open decision row is a question for the operator that no gate has closed, "
            'such as an entry of the roadmap\'s "what has not been decided" list.',
            "sessions that append decisions with a recommendation and no owner, trigger or "
            "deadline outgrow any triage (observed, 2026-11-03: one decision file held 68 "
            "numbered rows).",
        ),
    ),
    (
        "stop-condition",
        _HEADINGS[2],
        (
            'end every kickoff with the case where nothing happened: "if no trigger fired, '
            'write five lines and stop".',
            "the triggers are commands with expected results (`skill.md` step 8), so a "
            "session prints whether one fired and does not judge it.",
            "a kickoff that re-read a large state and found no trigger fired cost about 0.9 "
            "m tokens of context, for nothing (observed once, 2026-11-03, over three "
            "sessions).",
        ),
    ),
    (
        "environment-lead",
        _HEADINGS[3],
        ("before a wave starts, check these four things:",),
    ),
    (
        "free-disk",
        _HEADINGS[3],
        (
            "free disk.",
            "start no wave below a floor of 3 gb free (starting value, uncalibrated), and "
            "name the wave's janitor: the one session that deletes its scratch folders and "
            "test temp folders.",
            "a full system drive stopped the container engine, and two commits went without "
            "their linux gate (observed, 2026-11-02).",
        ),
    ),
    (
        "markdown-lint",
        _HEADINGS[3],
        (
            "markdown lint.",
            "limit a markdown-lint hook to the changed lines, or switch it off under "
            "scratch folders.",
            "it returned 14k to 18k tokens of diagnostics for one edit of a long ledger "
            "(observed, 2026-10-30).",
        ),
    ),
    (
        "usage-reading",
        _HEADINGS[3],
        (
            "usage reading.",
            "where one is taken (`skill.md` step 4), take it for the account the sessions "
            "actually run under, and say its age.",
            "a reading for another account says nothing about the window being spent.",
        ),
    ),
    (
        "shell-hook",
        _HEADINGS[3],
        (
            "shell hook.",
            "switch core's shell-prefix hook on for the initiative, as the charter's rule "
            "table says.",
            "it does nothing until the project switches it on.",
        ),
    ),
    (
        "mirror",
        _HEADINGS[4],
        (
            "at each release boundary, mirror the initiative's folder outside the checkout, "
            "and at each session close turn each ledger line that has a proposed home into "
            "an intake entry.",
            "a folder the repository ignores is in no commit, so a lost checkout loses it "
            "(observed, 2026-11-04: none of several thousand hand-off and planning files of "
            "four workstreams was tracked), and a lesson left only in the initiative's own "
            "ledger never reaches the consolidation that drains the intake buffer.",
        ),
    ),
    (
        "push-policy",
        _HEADINGS[5],
        (
            "decide at the first gate, and write it in the charter: one push at the end, or "
            "a private fork or a draft pull request that gives ci feedback before the end.",
            "one push at the end spares consumers a half-finished state and also withholds "
            "the integration signal until the whole release is one merge (observed, "
            "2026-11-04: about a hundred commits and a week of work had met neither ci nor "
            "a reviewer).",
        ),
    ),
)
_SENTENCES = tuple(sentence for _, _, sentences in _CLAIMS for sentence in sentences)
_CUTTABLE = 13  # the sentences after a claim's lead that carry a comma or colon

# What no changed file may carry: a request id, a commit id and a machine path. The shapes are
# generic, so the scan names no project; a bare capital letter and digits is a request id here.
_HYGIENE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a request id", re.compile(r"\b(?:KIT|OQ)-?\d+\b|\b[A-Z]-?\d{1,3}[a-z]?\b")),
    (
        "a commit id",
        re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b"),
    ),
    ("a drive-letter path", re.compile(r"\b[A-Za-z]:[\\/][A-Za-z]")),
    ("a home path", re.compile(r"/(?:Users|home)/")),
)
# The planted positive is built from pieces, so that this file holds no path or id of its own.
_PLANTED = " ".join(
    [
        "see A42, K-7, KIT-12 and OQ-4",
        "at 0123456789ab",
        "in " + "D" + ":/" + "work",
        "or " + "/" + "home" + "/x",
        "and " + "/" + "Users" + "/y",
    ]
)
# Near-misses that must pass: dates, a section sign, a template placeholder, a size, a word made
# only of letters that happen to be hex digits, and a number made only of digits.
_NEAR_MISSES = (
    "feedback on 2026-11-03, step 8 and section 6, 10 GB free, 0.9 M tokens, 68 rows, "
    "OP-{n} and Gate A (§4), decade, deadbeef, 1234567, https://example.org/a"
)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    assert path.is_file(), f"{path.name} is not a file"
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _flat(text: str) -> str:
    """Bold marks dropped, every run of whitespace one space, lower-cased: a re-wrapped line or
    a re-emphasised word is not a different sentence."""
    return " ".join(text.replace("**", "").split()).lower()


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith(_FENCE):
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
    return "\n".join(body)


def _blocks(section: str) -> list[tuple[str, list[str]]]:
    """The section as (kind, lines) blocks, kind "heading", "paragraph" or "item". A paragraph or
    an item ends at a blank line or a heading; a line that begins with "- " starts a new item, so a
    line that continues one is part of it whether it is indented or in column 0. A fenced block
    holds no heading, item or paragraph of the section."""
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    in_fence = False
    for line in section.split("\n"):
        if line.lstrip().startswith(_FENCE):
            in_fence = not in_fence
            current = None
        elif in_fence:
            continue
        elif _HEADING.match(line):
            blocks.append(("heading", [line]))
            current = None
        elif not line.strip():
            current = None
        elif line.startswith("- "):
            current = [line[2:]]
            blocks.append(("item", current))
        elif current is None:
            current = [line]
            blocks.append(("paragraph", current))
        else:
            current.append(line)
    return blocks


def _units(section: str) -> list[str]:
    """The flat text of every paragraph and every list item of the section, headings dropped."""
    return [
        _flat("\n".join(lines)) for kind, lines in _blocks(section) if kind != "heading"
    ]


def _unit(section: str, lead: str) -> str:
    """The flat text of the first paragraph or item that opens with `lead`; empty when none does.
    A unit that merely contains the lead further on is not that unit."""
    for unit in _units(section):
        if unit.startswith(lead):
            return unit
    return ""


def _gaps(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _rewrap(section: str, width: int) -> str:
    """The section with every paragraph and item re-wrapped at `width` columns, an item's
    continuation line indented by two spaces and a blank line after each unit, whatever the file's
    own wrap was. A heading is kept as it is."""
    out: list[str] = []
    for kind, lines in _blocks(section):
        if kind == "heading":
            out.extend(lines)
            continue
        first, rest = ("- ", "  ") if kind == "item" else ("", "")
        row = first
        for word in " ".join(lines).split():
            if len(row) + len(word) + 1 > width and row.strip():
                out.append(row.rstrip())
                row = rest
            row = f"{row}{word} "
        out.extend([row.rstrip(), ""])
    return "\n".join(out) + "\n"


def _unlabelled(text: str) -> list[str]:
    """The sentences of `text` that hold a number and neither a label nor a bare reference to a
    step or a section: a number with no measurement and no mark that says so."""
    found: list[str] = []
    for unit in _units(text):
        for sentence in _SENTENCE_END.split(unit):
            if not re.search(r"\d", _REFERENCE.sub("", sentence)):
                continue
            if not any(label in sentence for label in _LABELS):
                found.append(sentence)
    return found


def _hygiene(text: str) -> list[tuple[str, str]]:
    """Every (what, token) the hygiene patterns find in `text`."""
    return [
        (name, match.group(0))
        for name, pattern in _HYGIENE
        for match in pattern.finditer(text)
    ]


def _held(heading: str) -> str:
    """The section of the real file, and a loud failure naming it when it is missing."""
    section = _section(_read(_RULES), heading)
    assert section.strip(), f"operating-rules.md: no section {heading!r}"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    sections = {heading for _, heading, _ in _CLAIMS}
    assert (len(_CLAIMS), len(_SENTENCES), len(sections), len(_HYGIENE_FILES)) == (
        10,
        25,
        6,
        3,
    )
    assert sections == set(_HEADINGS)
    assert len(set(_SENTENCES)) == len(_SENTENCES), "a sentence is listed twice"
    for sentence in _SENTENCES:
        others = [other for other in _SENTENCES if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    cuttable = [
        sentence
        for _, _, sentences in _CLAIMS
        for sentence in sentences[1:]
        if _CLAUSE.search(sentence)
    ]
    assert len(cuttable) == _CUTTABLE
    assert len({path.resolve() for path in _HYGIENE_FILES}) == len(_HYGIENE_FILES)
    lines = len(_read(_RULES).rstrip("\n").split("\n"))
    assert 50 <= lines <= 80, f"operating-rules.md has {lines} lines; it is read whole"


def test_the_file_opens_with_one_line_saying_when_to_read_it() -> None:
    """Red before the change: there was no file. The title is followed by one line that says when to
    read it, on a line of its own."""
    lines = _read(_RULES).split("\n")
    assert lines[0].startswith(_TITLE), lines[0]
    assert lines[1] == "", "the title is not followed by a blank line"
    assert lines[2] == _WHEN, lines[2]
    assert lines[3] == "", "the opening line runs on into a second line"


def test_the_file_has_six_sections_in_order() -> None:
    headings = [line for line in _read(_RULES).split("\n") if line.startswith("## ")]
    assert headings == list(_HEADINGS)


@pytest.mark.parametrize(
    ("claim", "heading", "sentences"), _CLAIMS, ids=[c[0] for c in _CLAIMS]
)
def test_the_section_states_the_claim(
    claim: str, heading: str, sentences: tuple[str, ...]
) -> None:
    """Red before the change: the file was not there."""
    unit = _unit(_held(heading), sentences[0])
    assert unit, f"no paragraph or item of {heading!r} opens with {sentences[0]!r}"
    missing = _gaps(unit, sentences)
    assert not missing, f"the {claim!r} unit does not state: {missing}"


def test_each_claim_has_one_home() -> None:
    """One unit per claim: the lead sentence of every claim occurs once in the file, so the rule
    has no second copy to drift from the first."""
    flat = _flat(_read(_RULES))
    for claim, _, sentences in _CLAIMS:
        count = flat.count(sentences[0])
        assert count == 1, f"{claim}: the lead occurs {count} times"


def test_every_number_carries_its_label() -> None:
    """The file's own rule, held over its text: a sentence with a number is a bare reference to a
    step or a section, a starting value marked uncalibrated, or a measured fact marked observed."""
    assert _unlabelled(_read(_RULES)) == []


# --- the checks can fail -----------------------------------------------------------------------


def test_the_finders_see_a_file_that_is_not_the_new_one() -> None:
    """Known positive: an empty text and a text of another file hold none of the sections, and the
    finders say so for every claim, so an absent file or section is reported and not read as an
    empty pass."""
    other = "# Another reference\n\nRead this when something else.\n\n## 1. Something else\n\nText.\n"
    for claim, heading, sentences in _CLAIMS:
        for text in ("", other):
            assert _section(text, heading) == "", claim
            assert _unit(text, sentences[0]) == "", claim
            assert _gaps(_flat(text), sentences) == list(sentences), claim


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of the real section is the one gap reported, and an
    empty section lacks every sentence of the claim. A sentence that occurs twice would let a
    clause go and stay green."""
    for claim, heading, sentences in _CLAIMS:
        flat = _flat(_held(heading))
        assert _gaps(flat, sentences) == [], (
            f"{claim}: a sentence is missing at the start"
        )
        for sentence in sentences:
            assert flat.count(sentence) == 1, (
                f"{sentence!r} occurs {flat.count(sentence)} times"
            )
            assert _gaps(flat.replace(sentence, ""), sentences) == [sentence], sentence
        assert _gaps("", sentences) == list(sentences), claim


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the words after the last comma or colon of a sentence are cut out
    of the real paragraph or item, and the claim then reports exactly that sentence. A check on a
    fragment of the sentence would stay green."""
    cut = 0
    for claim, heading, sentences in _CLAIMS:
        unit = _unit(_held(heading), sentences[0])
        assert unit, f"{claim}: no unit opens with {sentences[0]!r}"
        assert not _gaps(unit, sentences)
        for sentence in sentences[1:]:
            if not _CLAUSE.search(sentence):
                continue
            tail = _CLAUSE.split(sentence)[-1]
            assert unit.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
            assert _gaps(unit.replace(tail, ""), sentences) == [sentence], (
                claim,
                sentence,
            )
            cut += 1
    assert cut == _CUTTABLE


@pytest.mark.parametrize("width", [40, 72, 100])
def test_a_rewrapped_and_reemphasised_section_still_holds_every_claim(
    width: int,
) -> None:
    """Near-miss that must NOT be reported: the real section with every paragraph and item
    re-wrapped at `width` columns and bold marks around every `the` is the same text."""
    for claim, heading, sentences in _CLAIMS:
        real = _held(heading)
        reshaped = _rewrap(real, width).replace(" the ", " **the** ")
        assert reshaped != real, claim
        assert "**the**" in reshaped, f"{claim}: the planted emphasis changed nothing"
        unit = _unit(reshaped, sentences[0])
        assert unit, f"{claim}: the re-wrapped unit was not found"
        assert _gaps(unit, sentences) == [], claim


def test_a_claim_is_judged_in_its_own_section_only() -> None:
    """Planted move: the section's body put under another heading is a section that lacks every
    sentence of its claims. A search of the whole file would still find them and pass, which is
    why each claim is read from its section alone."""
    text = _read(_RULES)
    for heading in _HEADINGS:
        section = _held(heading)
        head, _, body = section.partition("\n")
        moved = text.replace(
            section, f"{head}\n\n(a stub)\n\n# Elsewhere\n\n{body}\n", 1
        )
        assert moved != text, f"{heading}: the planted move changed nothing"
        after = _section(moved, heading)
        assert after.strip(), f"{heading}: the planted text has no section"
        for claim, claim_heading, sentences in _CLAIMS:
            if claim_heading != heading:
                continue
            assert _unit(after, sentences[0]) == "", claim
            assert _gaps(_flat(after), sentences) == list(sentences), claim
            assert _gaps(_flat(moved), sentences) == [], (
                f"{claim}: a whole-file search fails"
            )


def test_the_number_check_sees_planted_text() -> None:
    """Known positives and near-misses for the label check: a bare number, a number in a sentence
    that only mentions another section's label, and a label on the wrong side of a sentence end
    are each reported; a labelled value, a measured fact and a bare reference pass."""
    flagged = (
        "Keep at most 10 open rows per release.",
        "Keep at most about 10 open rows. The floor is 3 GB (starting value, uncalibrated).",
        "A kickoff cost 0.9 M tokens, for nothing. (observed, 2026-11-03)",
        "- Start no wave below 3 GB free.",
    )
    for text in flagged:
        assert _unlabelled(text), text
    passed = (
        "Keep at most about 10 open rows (starting value, uncalibrated).",
        "A kickoff cost 0.9 M tokens (observed, 2026-11-03).",
        "See step 8 and section 6 for the rest.",
        "- Start no wave below 3 GB free (starting value, uncalibrated).",
        "A paragraph with no number at all.",
    )
    for text in passed:
        assert _unlabelled(text) == [], text
    assert _unlabelled(
        "Keep at most 10 open rows. The floor is 3 GB (starting value, uncalibrated)."
    ) == ["keep at most 10 open rows."]


# --- the hygiene scan --------------------------------------------------------------------------


def test_the_hygiene_scan_sees_a_planted_positive_and_passes_the_near_misses() -> None:
    """The scan is fired at a planted line first: it finds each kind once or more, and nothing in
    the near-misses, which hold a date, a section sign, a placeholder, a size, an all-letter word
    made of hex digits and an all-digit number."""
    kinds = {name for name, _ in _hygiene(_PLANTED)}
    assert kinds == {name for name, _ in _HYGIENE}, kinds
    assert {token for name, token in _hygiene(_PLANTED) if name == "a request id"} == {
        "A42",
        "K-7",
        "KIT-12",
        "OQ-4",
    }
    assert [token for name, token in _hygiene(_PLANTED) if name == "a commit id"] == [
        "0123456789ab"
    ]
    assert _hygiene(_NEAR_MISSES) == []


def test_the_changed_files_carry_no_request_id_commit_id_or_machine_path() -> None:
    """The zero is printed beside its denominator: the three files and their lines. Each file is
    read whole; a file that is not there fails, so a zero is never a scan of nothing."""
    scanned = 0
    for path in _HYGIENE_FILES:
        text = _read(path)
        lines = len(text.split("\n"))
        assert lines >= 50, f"{path.name} has {lines} lines: is it the file?"
        scanned += lines
        assert _hygiene(text) == [], f"{path.name}: {_hygiene(text)}"
    assert scanned >= 3 * 50


# --- the finders keep their edges --------------------------------------------------------------

_SECTIONS = "\n".join(
    [
        "### 8. A look-alike that only contains the wanted prefix",
        "## 8. First",
        "first body",
        "### 8.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "## 9. nor is this one",
        "```",
        "## 9. Second",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, runs to the end of the text
    when none follows, and finds nothing for a heading that is not there."""
    first = _section(_SECTIONS, "## 8.")
    assert first.startswith("## 8. First"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert "second body" in _section(_SECTIONS, "## 9. Second")
    assert _section(_SECTIONS, "## 99.") == ""


_UNITS = "\n".join(
    [
        "## Heading is dropped",
        "The first paragraph is",
        "  broken over two lines.",
        "",
        "- **A lead.** An item that quotes the first paragraph is",
        "the first paragraph is broken over two lines. again, in column 0.",
        "- **A second lead.** Last item.",
        "",
        "```text",
        "- **A fenced lead.** It is not an item.",
        "## Nor is this a heading",
        "```",
        "",
        "Closing paragraph.",
        "",
    ]
)


def test_the_unit_finder_keeps_its_edges() -> None:
    """The finder drops a heading, reads a paragraph whole across a line break, reads an item whole
    whether its continuation lines are indented or in column 0, stops at the next item, takes
    nothing inside a fence for an item or a heading, never takes an item that only contains the
    lead for the one that opens with it, and finds nothing for a lead that is absent."""
    units = _units(_UNITS)
    assert units == [
        "the first paragraph is broken over two lines.",
        "a lead. an item that quotes the first paragraph is the first paragraph is broken over "
        "two lines. again, in column 0.",
        "a second lead. last item.",
        "closing paragraph.",
    ], units
    assert [kind for kind, _ in _blocks(_UNITS)] == [
        "heading",
        "paragraph",
        "item",
        "item",
        "paragraph",
    ]
    assert _unit(_UNITS, "the first paragraph") == units[0]
    assert _unit(_UNITS, "a lead.").endswith("in column 0.")
    assert _unit(_UNITS, "a second lead.") == units[2]
    assert _unit(_UNITS, "an item that quotes") == ""
    assert _unit(_UNITS, "a fenced lead.") == ""
    assert _unit(_UNITS, "an absent lead.") == ""
    assert _unit("", "an absent lead.") == ""
