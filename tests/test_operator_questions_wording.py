"""The orchestrator's operator-questions reference says how to ask without blocking the work.

`orchestrate/references/operator-questions.md` is new. It adds to the operator-interface rules in
item 9 of the brief contract in `orchestrate/SKILL.md` (answer your own question first, expand
every id, put the recommendation first) without repeating them. It says: start every background
job that does not depend on the answer first and ask last, citing one observed figure; ask
nothing a command can answer or the brief already ruled; ask one question per turn, in one call,
standing alone; mark the recommended option, which item 9 already puts first, among two to four
options with their consequences; handle a bare "proceed" by the rule in section 8 of the dispatch
gates, which it links and does not restate; a session that cannot ask writes the question under
"Blocked on" with the default it takes and lets the independent work go on; the default taken for
an absent operator is recorded in the checkpoint; and an answer that says it did something is a
claim to re-read by command.

THE SURFACE, in numbers the tests assert: 1 file, 2 opening sentences, 4 sections, 8 claims and
16 sentences, every claim one bullet in its own section and every sentence held whole
(lower-cased, bold marks dropped, whitespace collapsed), occurring once and fired at a planted
removal; 11 of the 16 sentences, leads included, have a clause that is also cut; 1 observed
figure, cited once; 3 rules it points at, each checked in its target: item 9 of `SKILL.md` still
puts the recommendation first, and section 8 of the dispatch gates and the worker preamble still
hold the bare-"proceed" rule; 2 links, each resolving. Which SKILL.md line points at this file is
the release owner's edit and is not asserted here.
"""

import re
from pathlib import Path

import pytest

_REFERENCES = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "orchestrate"
    / "references"
)
_FILE = _REFERENCES / "operator-questions.md"
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_CLAUSE = re.compile(r"[,:;] ")

_OPENING = (
    "read this before you ask the operator anything in the middle of the work, and before you "
    "write a hand-off that waits on an answer.",
    "it adds to the operator-interface rules in item 9 of the brief contract in `skill.md` and "
    "does not repeat them.",
)
_OBSERVED = "(observed, 2026-11-04)"

# (section heading, ((claim id, the sentences of its bullet, whole, in order), ...)). The first
# sentence of a claim is the bold lead that opens its bullet; lower-cased, bold marks dropped.
_SECTIONS: tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    (
        "## Before you ask",
        (
            (
                "ask last",
                (
                    "start every background job that does not depend on the answer first, "
                    "and ask last.",
                    "a question holds your turn until it is answered: one question dialog held "
                    "a session's turn for about an hour while its three background jobs, which "
                    "took about half an hour, had long finished, and the three questions after "
                    "it took seconds (observed, 2026-11-04).",
                ),
            ),
            (
                "nothing a command answers",
                (
                    "ask nothing that a command can answer or that the brief already ruled.",
                    "run the command or quote the ruling instead, and keep the operator's "
                    "attention for what only the operator decides.",
                ),
            ),
        ),
    ),
    (
        "## How to ask",
        (
            (
                "one question",
                (
                    "ask one question per turn, in one call, and make it stand alone.",
                    "the operator may see only the dialog, so name the items and say what you "
                    "found instead of pointing at earlier text.",
                ),
            ),
            (
                "options",
                (
                    "mark the recommended option, which item 9 already puts first.",
                    "offer two to four options, each with its consequence, so the operator "
                    "chooses between outcomes, not between labels.",
                ),
            ),
            (
                "bare proceed",
                (
                    'a bare "proceed" is not an answer to a question.',
                    "handle it by the rule in section 8 of the [dispatch "
                    "gates](dispatch-gates.md); a worker finds the same rule in its [worker "
                    "preamble](../../agent-delegate/assets/worker-preamble.md).",
                ),
            ),
        ),
    ),
    (
        "## When no answer can arrive",
        (
            (
                "blocked on",
                (
                    'a session that cannot ask writes the question under "blocked on" in its '
                    "hand-off, with the default it takes.",
                    "it stops the work that depends on the answer and lets the independent "
                    "work go on.",
                ),
            ),
            (
                "default recorded",
                (
                    "record in your checkpoint which default you took for an absent operator.",
                    "section 8 of the dispatch gates says to take exactly the default you "
                    "offered; the record lets the next reader see that a default, not an "
                    "answer, decided it.",
                ),
            ),
        ),
    ),
    (
        "## After the answer",
        (
            (
                "answers are claims",
                (
                    'an answer that says it did something ("done", "merged", "rotated") is a '
                    "claim.",
                    "re-read the state by command before you rely on it.",
                ),
            ),
        ),
    ),
)
_CLAIMS = tuple(
    (heading, claim, sentences)
    for heading, claims in _SECTIONS
    for claim, sentences in claims
)
_SENTENCES = tuple(sentence for _, _, sentences in _CLAIMS for sentence in sentences)
_LEADS = tuple(sentences[0] for _, _, sentences in _CLAIMS)
_WITH_CLAUSE = tuple(sentence for sentence in _SENTENCES if _CLAUSE.search(sentence))

# The rules this file points at, as their targets state them (lower-cased, bold marks dropped).
_PROCEED_IN_GATES = 'a bare "proceed" after such a stop is unresolved.'
_PROCEED_IN_PREAMBLE = 'a bare "proceed" in reply to such a stop is unresolved'
_ITEM_9 = "9. **The close block"
_ITEM_9_RULES = (
    "plus three operator-interface rules",
    "answer your own question first.",
    "a decision question states your recommendation first, then the options",
)


def _read(path: Path = _FILE) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
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
    return "\n".join(body)


def _item_lines(text: str) -> tuple[list[str], list[list[str]]]:
    """The lines before the first list item, and the lines of every item. An item starts at a
    line that begins with "- " outside a fenced block and runs to the next such line, so a line
    that continues it is part of it whether it is indented or sits in column 0."""
    head: list[str] = []
    items: list[list[str]] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("- "):
            items.append([line])
        elif items:
            items[-1].append(line)
        else:
            head.append(line)
    return head, items


def _bullet(text: str, lead: str) -> str:
    """The flat text of the first list item that opens with `lead`; empty when none does. An
    item that merely contains the lead further on is not that item."""
    for lines in _item_lines(text)[1]:
        flat = _flat("\n".join(lines)[2:])
        if flat.startswith(lead):
            return flat
    return ""


def _gaps(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _rewrap(text: str, width: int) -> str:
    """The list items of `text` re-wrapped at `width` columns, a continuation line indented by two
    spaces, whatever the file's own wrap was: a bold lead can break over two lines. Any other
    line is kept as it is."""
    head, items = _item_lines(text)
    out = list(head)
    for lines in items:
        words = " ".join(lines)[2:].split()
        row = "-"
        for word in words:
            if len(row) + 1 + len(word) > width and row.strip("- "):
                out.append(row)
                row = " "
            row = f"{row} {word}"
        out.append(row)
    return "\n".join(out) + "\n"


def _real_section(heading: str) -> str:
    section = _section(_read(), heading)
    assert section.strip(), f"{heading!r} is missing from operator-questions.md"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    counts = (len(_OPENING), len(_SECTIONS), len(_CLAIMS), len(_SENTENCES))
    assert counts == (2, 4, 8, 16), counts
    assert len(_WITH_CLAUSE) == 11, len(_WITH_CLAUSE)
    every = (*_OPENING, *_SENTENCES)
    assert len(set(every)) == len(every), "a sentence is listed twice"
    for sentence in every:
        others = [other for other in every if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    assert _FILE.is_file(), f"{_FILE} is not a file"
    headings = [line for line in _read().split("\n") if line.startswith("## ")]
    assert headings == [heading for heading, _ in _SECTIONS], headings


def test_the_file_opens_by_saying_when_to_read_it_and_what_it_adds_to() -> None:
    """The opening paragraph, before the first section, says when to read the file and that it
    adds to item 9 of the brief contract without repeating it; a planted removal is reported."""
    text = _read()
    opening = _flat(text.split("\n## ", 1)[0])
    assert text.startswith("# "), "the file does not open with its title"
    assert _gaps(opening, _OPENING) == [], "the opening lost a sentence"
    for sentence in _OPENING:
        assert _gaps(opening.replace(sentence, ""), _OPENING) == [sentence]


@pytest.mark.parametrize(
    ("heading", "claim", "sentences"), _CLAIMS, ids=[c[1] for c in _CLAIMS]
)
def test_each_section_states_its_claim(
    heading: str, claim: str, sentences: tuple[str, ...]
) -> None:
    bullet = _bullet(_real_section(heading), sentences[0])
    assert bullet, f"no bullet of {heading!r} opens with {sentences[0]!r}"
    missing = _gaps(bullet, sentences)
    assert not missing, f"the {claim!r} bullet does not state: {missing}"


def test_every_claim_is_one_bullet_with_one_home() -> None:
    """Exactly one list item of the whole file opens with each lead, and each lead occurs once
    in the file, so no rule has a second copy to drift from the first."""
    text = _read()
    for lead in _LEADS:
        openers = [
            lines
            for lines in _item_lines(text)[1]
            if _flat("\n".join(lines)[2:]).startswith(lead)
        ]
        assert len(openers) == 1, f"{len(openers)} list items open with {lead!r}"
        assert _flat(text).count(lead) == 1, f"{lead!r} occurs more than once"


def test_the_observed_figure_is_cited_once() -> None:
    """One measured figure, labelled with its date, and nowhere repeated."""
    flat = _flat(_read())
    assert flat.count(_OBSERVED) == 1, (
        f"{_OBSERVED!r} occurs {flat.count(_OBSERVED)} times"
    )
    assert flat.count("about an hour") == 1 and flat.count("about half an hour") == 1


# --- the checks can fail -----------------------------------------------------------------------


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of its real section is the one gap reported, and
    an empty section lacks every sentence. A sentence that occurs twice would let a clause go
    and stay green."""
    for heading, claims in _SECTIONS:
        flat = _flat(_real_section(heading))
        sentences = tuple(s for _, group in claims for s in group)
        assert _gaps(flat, sentences) == [], f"{heading}: a sentence is missing"
        for sentence in sentences:
            assert flat.count(sentence) == 1, (
                f"{sentence!r} occurs {flat.count(sentence)} times"
            )
            assert _gaps(flat.replace(sentence, ""), sentences) == [sentence], sentence
        assert _gaps("", sentences) == list(sentences)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the words after the last comma, colon or semicolon of every
    sentence that has one, leads included, are cut out of the real bullet, and the claim then
    reports exactly that sentence. A check on a fragment of the sentence would stay green."""
    fired = 0
    for heading, claim, sentences in _CLAIMS:
        bullet = _bullet(_real_section(heading), sentences[0])
        assert bullet, f"no bullet of {heading!r} opens with {sentences[0]!r}"
        for sentence in sentences:
            tail = _CLAUSE.split(sentence)[-1]
            if tail == sentence:
                continue
            assert bullet.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
            assert _gaps(bullet.replace(tail, ""), sentences) == [sentence], (
                claim,
                sentence,
            )
            fired += 1
    assert fired == len(_WITH_CLAUSE)


@pytest.mark.parametrize("width", [40, 72, 100])
def test_a_rewrapped_and_reemphasised_file_still_holds_every_claim(width: int) -> None:
    """Near-miss that must NOT be reported: each real section with its list items re-wrapped at
    `width` columns, so that a bold lead breaks over two lines, and bold marks around one more
    word of a bullet (no heading holds " it ") is the same text."""
    for heading, claim, sentences in _CLAIMS:
        real = _real_section(heading)
        reshaped = _rewrap(real, width).replace(" it ", " **it** ", 1)
        assert "**it**" in reshaped, f"{heading}: the planted emphasis changed nothing"
        bullet = _bullet(reshaped, sentences[0])
        assert bullet, f"{claim}: the re-wrapped bullet was not found"
        assert _gaps(bullet, sentences) == [], claim


def test_the_claims_are_judged_inside_their_section_only() -> None:
    """Planted move: the bullets of "How to ask" put under "Before you ask" leave a "How to
    ask" that lacks its claims and exactly them. A search of the whole file would still find
    every sentence and pass, which is why each claim is read from its own section."""
    text = _read()
    moving = _real_section("## How to ask")
    head, items = _item_lines(moving)
    moved = "\n".join(line for lines in items for line in lines)
    planted = text.replace(moving, "\n".join(head)).replace(
        "## Before you ask\n", f"## Before you ask\n\n{moved}\n", 1
    )
    assert planted != text and moved in planted
    after = _section(planted, "## How to ask")
    assert after.strip(), "the planted text has no How to ask section"
    sentences = tuple(
        s for h, _, group in _CLAIMS if h == "## How to ask" for s in group
    )
    assert _gaps(_flat(after), sentences) == list(sentences)
    assert _gaps(_flat(planted), sentences) == [], (
        "a whole-file search would have passed"
    )


# --- the links point at the rule they are cited for --------------------------------------------


def _missing_targets(text: str, base: Path) -> list[str]:
    targets = [target.split("#")[0] for target in _LINK.findall(text)]
    return [target for target in targets if not (base / target).is_file()]


def test_every_link_resolves_from_this_file() -> None:
    """Both links resolve against the folder of this file; a planted broken one is reported."""
    text = _read()
    assert len(_LINK.findall(text)) == 2, _LINK.findall(text)
    assert _missing_targets(text, _FILE.parent) == []
    planted = text.replace("(dispatch-gates.md)", "(dispatch-gate.md)", 1)
    assert _missing_targets(planted, _FILE.parent) == ["dispatch-gate.md"]


def _item_9(skill: str) -> str:
    """Item 9 of the brief contract: from its numbered line to the next numbered item."""
    lines = skill.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(_ITEM_9)]
    assert len(starts) == 1, f"{len(starts)} lines open item 9"
    body = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if re.match(r"^\d+\. ", line):
            break
        body.append(line)
    return _flat("\n".join(body))


def test_item_9_still_holds_the_rules_this_file_adds_to() -> None:
    """The rules the opening says this file does not repeat are still in item 9 of
    `SKILL.md`; the planted item 9 without the recommendation-first clause is reported."""
    item = _item_9(_read(_REFERENCES.parent / "SKILL.md"))
    assert _gaps(item, _ITEM_9_RULES) == [], "item 9 lost a rule this file builds on"
    planted = item.replace(_ITEM_9_RULES[2], "")
    assert _gaps(planted, _ITEM_9_RULES) == [_ITEM_9_RULES[2]]
    assert _flat(_read()).count("item 9") == 2, "the pointer to item 9 moved"


def test_the_linked_files_hold_the_rule_they_are_cited_for() -> None:
    """Section 8 of the dispatch gates and the worker preamble each still hold the bare
    "proceed" rule this file sends the reader to, so a renumbered or rewritten target is
    reported here and not found later by a reader who followed a dead pointer. The planted
    section 8 without that bullet is reported."""
    gates = _read(_REFERENCES / "dispatch-gates.md")
    preamble = _read(
        _REFERENCES.parents[1] / "agent-delegate" / "assets" / "worker-preamble.md"
    )
    section_8 = _section(gates, "## 8.")
    assert _bullet(section_8, _PROCEED_IN_GATES), "section 8 lost the bare-proceed rule"
    assert _PROCEED_IN_PREAMBLE in _flat(preamble), "the preamble lost the rule"
    head, items = _item_lines(section_8)
    kept = [
        lines
        for lines in items
        if not _flat("\n".join(lines)[2:]).startswith(_PROCEED_IN_GATES)
    ]
    assert len(kept) == len(items) - 1
    planted = "\n".join([*head, *(line for lines in kept for line in lines)])
    assert _bullet(planted, _PROCEED_IN_GATES) == ""
    assert _flat(_read()).count("section 8 of the") == 2, (
        "the pointer to section 8 moved"
    )


# --- the finders -------------------------------------------------------------------------------


_FIXTURE_SECTIONS = "\n".join(
    [
        "#### How to ask, a look-alike that only contains the wanted prefix",
        "## How to ask",
        "first body",
        "### Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "## nor is this one",
        "```",
        "## After the answer",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, finds nothing for a heading
    that is not there, and finds every section of the real file."""
    first = _section(_FIXTURE_SECTIONS, "## How to ask")
    assert first.startswith("## How to ask"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert "second body" in _section(_FIXTURE_SECTIONS, "## After the answer")
    assert _section(_FIXTURE_SECTIONS, "## Absent") == ""
    for heading, _ in _SECTIONS:
        assert _section(_read(), heading).strip(), heading


_ITEMS = "\n".join(
    [
        "Evidence line before the list.",
        "",
        "- **The first lead is",
        "  broken over two lines.** Its body says the second lead is not here.",
        "- **The second lead.** A body that quotes the first lead is",
        "the first lead is broken over two lines. again, in column 0.",
        "```text",
        "- **A fenced lead.** It is not an item.",
        "```",
        "- **The third lead.** Last body.",
        "",
    ]
)


def test_the_bullet_finder_keeps_its_edges() -> None:
    """The finder reads an item whole whether its lead is bold or broken over two lines and
    whether its continuation lines are indented or in column 0, stops at the next item, does not
    take a line inside a fence for an item or an item that only contains the lead for the one
    that opens with it, finds nothing for an absent lead, and finds every real lead."""
    first = _bullet(_ITEMS, "the first lead is broken over two lines.")
    assert first.startswith("the first lead is broken over two lines. its body"), first
    second = _bullet(_ITEMS, "the second lead.")
    assert "in column 0" in second and "fenced lead" in second, second
    assert "last body" not in second, second
    assert _bullet(_ITEMS, "a fenced lead.") == ""
    assert _bullet(_ITEMS, "its body says") == ""
    assert _bullet(_ITEMS, "an absent lead.") == ""
    head, items = _item_lines(_ITEMS)
    assert head == ["Evidence line before the list.", ""]
    assert len(items) == 3, [lines[0] for lines in items]
    assert all(_bullet(_read(), lead) for lead in _LEADS)
