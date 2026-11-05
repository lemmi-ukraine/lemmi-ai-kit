"""The planner's charter and roadmap templates hold the operator's rules and the plan's forecasts.

An initiative learned two things at its end that its planner could have asked at its start. The
operator's rules arrived one at a time during the run, the last of them after every gate was green,
and no gate measured a rule it did not encode. And the plan's forecasts (how long a session would take,
when a landing would happen, how many sessions were left) missed in both directions with no record of
what had been said, because the planner's one sentence on the subject says that session counts are a
decomposition, not an estimate, and gives a forecast no home.

What the two templates now say:

* `references/charter-template.md` gains "Operator rules in force", a field of the shared charter
  block, in two places: a row of the skeleton (a table of the rule, whether it was stated or is
  expected, the command that measures it, what enforces it and who counts the slips) and three
  paragraphs of the structure description. The first says what a stated and an expected rule are and
  that the expected ones are asked for at the charter. The second says a green gate says nothing about
  a rule it does not encode, so each row names the command that measures the rule on every landing,
  fired at a planted line first, and those commands are run before a push is asked for. The third
  says a rule that only a brief states gets broken, so each row names what enforces it, a hook is
  switched on for the initiative, and each row names who counts the slips.
* `references/roadmap-template.md` gains section 8, "Forecast log", in two places: a table of the
  skeleton (date, claim, basis, observed) and one paragraph of the structure description. A row per
  forecast, written when it is made; the observed cell filled at each session close; and the planner's
  sentence on decomposition left as it is, because a count is not a forecast.

THE SURFACE, in numbers the tests assert: 4 claims and 17 sentences in 2 files, each claim held by one
paragraph of one section, and 2 skeleton tables. A claim holds when its paragraph holds every one of
its sentences whole (lower-cased, bold marks dropped, whitespace collapsed), so a clause cannot be
dropped while the rest of its sentence still matches. Each sentence occurs once in its section and is
fired at a planted removal; 10 of them carry a clause that is cut out in turn. A third file, the
planner's SKILL.md, is read for the one sentence it must keep. The charter's skeleton and the
roadmap's are read for the heading, its place between its neighbours and the table's first two rows.

Green on the old text by construction, and said so where they are: the surface (a count), the kept
sentence, and the finders fired at planted text. Every other check is red on the old text, because
the section, the heading and the table were not there.

CLASSES OF SHAPE covered: a sentence dropped; a clause dropped; a section emptied; a claim moved to
another section of the same file, where a whole-file search would still find it; a re-wrap and a
re-emphasis, which are the same text; a heading renamed or missing, which fails loudly and never
passes on an empty section; a table whose heading is missing or out of place, or that lacks a column
or its rule row. Shapes not covered are the order of the paragraphs inside a section and any sentence
outside the claims.
"""

import re
from pathlib import Path
from typing import NamedTuple

import pytest

_PLANNER = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "initiative-planner"
)
_FILES: dict[str, Path] = {
    "charter": _PLANNER / "references" / "charter-template.md",
    "roadmap": _PLANNER / "references" / "roadmap-template.md",
}
_SKILL = _PLANNER / "SKILL.md"
_SIGN = chr(0xA7)  # the section sign in the roadmap's headings
_HEADING = re.compile(r"^(#{1,6})\s")
_FENCE = "```"
_CLAUSE = re.compile(r"[,:] ")

_RULES = "### Operator rules in force"
_FORECAST = f"### {_SIGN}8 Forecast log"

# The planner's own sentence on counts, which the log must leave where it is: it is in SKILL.md and
# is held whole, once.
_KEPT = "state this in the plan, verbatim: session counts are a decomposition, not an estimate."

# (claim id, file key, the heading of the ONE section that must hold it, the sentences of its
# paragraph, whole, in order; lower-cased, bold marks dropped, whitespace collapsed). The first
# sentence of a claim is the lead that opens its paragraph. The claims, in order: what a stated and
# an expected rule are, and that the expected ones are asked for at the charter; a green gate says
# nothing about a rule it does not encode, so each row has its own measuring command, fired at a
# planted line, and run before a push is asked for; what enforces the rule, the hook switched on
# for the initiative, and who counts the slips; the forecast log's rows, its observed cell at each
# session close, and the planner's sentence on counts left as it is.
_CLAIMS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "rules-stated-and-expected",
        "charter",
        _RULES,
        (
            "the rules the operator has stated about how this initiative may run, and the "
            "rules the operator would state if asked.",
            "a stated rule is one the operator has already said.",
            "an expected rule follows from a fact about the work: a public repository means "
            "nothing private may reach anything pushed, a shared tree means disjoint file "
            "sets, a consumer that installs the work means it must run from a fresh copy.",
            "ask for the expected ones at the charter, because a rule that arrives after "
            "the gates are green meets gates that cannot see it (observed, 2026-11-03: the "
            "operator ruled that a repository was public, and must carry no project "
            "information, on the eighth day of an initiative, with every gate green and the "
            "forbidden content already tracked).",
        ),
    ),
    (
        "measure-the-rule-itself",
        "charter",
        _RULES,
        (
            "measure the rule itself.",
            "a green gate says nothing about a rule it does not encode.",
            "each row names the command that measures its rule on every landing, and that "
            "command is fired at a planted line before its zero is trusted.",
            "a public repository, for example, means a forbidden-content scan on every "
            "landing, built with a planted control.",
            "run each row's command before asking the operator for a push; the gates that "
            "ran are not evidence for it.",
        ),
    ),
    (
        "hook-and-slips",
        "charter",
        _RULES,
        (
            "name what enforces the rule, and who counts the slips.",
            "a rule that only a brief states gets broken "
            "([dispatch-economics.md](dispatch-economics.md) section 2 gives the measured "
            "rate), so each row names the hook, tool grant or gate that enforces it for "
            "this initiative.",
            "where that is a hook, switch it on before the first wave: core's shell-prefix "
            'hook does nothing until `.ai/shell-prefix-hook.json` says `{"enabled": true}`, '
            "and the switch is flipped while no peer session is mid-task.",
            "each row also names who counts a break of the rule, and where the count is "
            "kept, so a slip is a number and not a memory.",
        ),
    ),
    (
        "forecast-log",
        "roadmap",
        _FORECAST,
        (
            "one row per forecast the plan makes, written when it is made: the date and "
            "time read from the clock, the claim (a duration, a landing time, the context a "
            "session will use, how many sessions remain) and the basis it rests on, or the "
            'word "none".',
            "at each session close, fill in observed for every row that session settled, "
            "with how far the result was from the claim, so the next forecast starts from "
            "what the last one missed by.",
            "the plan's sentence that session counts are a decomposition, not an estimate "
            "(`skill.md` step 8) stays as it is: the counts partition the work and say "
            "nothing about duration, so a forecast of how long or how many is a separate "
            "claim, and this log holds it.",
            "estimates of a session's context, of landing times and of the sessions "
            "remaining missed in both directions, and none was logged against its outcome "
            "(observed, 2026-10-30 to 2026-11-03).",
        ),
    ),
)
_SENTENCES = tuple(sentence for _, _, _, sentences in _CLAIMS for sentence in sentences)
_CUTTABLE = 10  # the sentences after a claim's lead that carry a comma or colon


class _Skeleton(NamedTuple):
    """A skeleton's new heading, the neighbours it sits between, and its table's first two rows."""

    key: str
    marker: str
    before: str
    heading: str
    after: str | None
    header: str
    rule_row: str


_SKELETONS: tuple[_Skeleton, ...] = (
    _Skeleton(
        "charter",
        "## Goal",
        "## Non-goals",
        "## Operator rules in force",
        "## Open questions",
        "| Rule | Stated or expected | Measured by | Enforced by | Slips counted by |",
        "|---|---|---|---|---|",
    ),
    _Skeleton(
        "roadmap",
        "## 1. Goal, falsifiers, definition of done",
        "## 7. What has NOT been decided",
        "## 8. Forecast log",
        None,
        "| Date | Claim | Basis | Observed |",
        "|---|---|---|---|",
    ),
)

# The two places as they stood before the change, shortened to lines that carry no character
# outside ASCII: the known positives the checks must see the gaps in.
_OLD: dict[str, str] = {
    "charter": """\
### Non-goals
Every initiative has boundaries. The useful ones are the boundaries someone **will** try to cross
during implementation.

### Alternatives considered (ADR)
"Do nothing" is always an alternative and always listed.

```markdown
## Goal

{What is true for a USER when this is done.}

## Non-goals

{What this deliberately excludes, and why. An empty section is a failure.}

## Open questions

{Each names its gate and its decider.}
```
""",
    "roadmap": """\
### §7 What has NOT been decided
Every open question with the gate that closes it.
Give each question an id the gate's approval record can cite (§4).

```markdown
## 1. Goal, falsifiers, definition of done

{One paragraph from the charter.}

## 7. What has NOT been decided

{Each with the gate that decides it.}
```
""",
}


def _read(path: Path) -> str:
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


def _block(text: str, marker: str) -> str:
    """The first fenced block of `text` that holds `marker`: a template's skeleton. Empty when
    none does."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if line.lstrip().startswith(_FENCE):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line)
    for lines in blocks:
        joined = "\n".join(lines)
        if marker in joined:
            return joined
    return ""


def _table_problems(block: str, spec: _Skeleton) -> list[str]:
    """What is wrong with a skeleton block: a heading line that is missing, the headings out of
    order, or a table whose header row and rule row are not the two lines the spec names, which
    follow the heading after one blank line."""
    lines = block.split("\n")
    names = [spec.before, spec.heading, *([spec.after] if spec.after else [])]
    missing = [f"no line {name!r}" for name in names if name not in lines]
    if missing:
        return missing
    positions = [lines.index(name) for name in names]
    problems: list[str] = []
    if positions != sorted(positions):
        problems.append("the headings are out of order")
    at = positions[1]
    if lines[at + 2 : at + 4] != [spec.header, spec.rule_row]:
        problems.append("the header row or the rule row is not the one named")
    return problems


def _held(key: str, heading: str) -> str:
    """The section of the real file, and a loud failure naming it when it is missing."""
    section = _section(_read(_FILES[key]), heading)
    assert section.strip(), f"{_FILES[key].name}: no section {heading!r}"
    return section


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    sections = {(key, heading) for _, key, heading, _ in _CLAIMS}
    assert (len(_CLAIMS), len(_SENTENCES), len(sections), len(_FILES)) == (
        4,
        17,
        2,
        2,
    )
    assert len(_SKELETONS) == 2
    assert len(set(_SENTENCES)) == len(_SENTENCES), "a sentence is listed twice"
    for sentence in _SENTENCES:
        others = [other for other in _SENTENCES if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    cuttable = [
        sentence
        for _, _, _, sentences in _CLAIMS
        for sentence in sentences[1:]
        if _CLAUSE.search(sentence)
    ]
    assert len(cuttable) == _CUTTABLE
    assert len({path.resolve() for path in _FILES.values()}) == len(_FILES)
    for path in (*_FILES.values(), _SKILL):
        assert path.is_file(), f"{path} is not a file"
        assert _read(path).strip(), f"{path.name} is empty"


def test_the_planners_sentence_on_counts_is_kept() -> None:
    """Passes before and after: the log is added beside the planner's sentence that session counts
    are a decomposition, not an estimate, and leaves it where it is, once."""
    count = _flat(_read(_SKILL)).count(_KEPT)
    assert count == 1, f"SKILL.md holds the sentence {count} times"


@pytest.mark.parametrize(
    ("claim", "key", "heading", "sentences"), _CLAIMS, ids=[c[0] for c in _CLAIMS]
)
def test_the_section_states_the_claim(
    claim: str, key: str, heading: str, sentences: tuple[str, ...]
) -> None:
    """Red before the change: neither template had the section."""
    unit = _unit(_held(key, heading), sentences[0])
    assert unit, f"{key}: no paragraph of {heading!r} opens with {sentences[0]!r}"
    missing = _gaps(unit, sentences)
    assert not missing, f"the {claim!r} paragraph does not state: {missing}"


def test_each_claim_has_one_home() -> None:
    """One paragraph per claim: the lead sentence of every claim occurs once in its file, so the
    rule has no second copy to drift from the first."""
    for claim, key, _, sentences in _CLAIMS:
        count = _flat(_read(_FILES[key])).count(sentences[0])
        assert count == 1, f"{claim}: the lead occurs {count} times in {key}"


@pytest.mark.parametrize("spec", _SKELETONS, ids=[spec.key for spec in _SKELETONS])
def test_the_skeleton_carries_the_new_heading_and_its_table(spec: _Skeleton) -> None:
    """Red before the change: neither skeleton had the heading or the table."""
    block = _block(_read(_FILES[spec.key]), spec.marker)
    assert block, f"{spec.key}: no fenced block holds {spec.marker!r}"
    assert _table_problems(block, spec) == []


# --- the checks can fail -----------------------------------------------------------------------


def test_the_old_text_lacks_every_claim_and_both_tables() -> None:
    """Known positive: the places as they stood have none of the sections, and the finders say so
    for every claim; a sentence of any claim is in no part of the old text of its file; and each
    skeleton block is reported for the one heading it lacks."""
    for claim, key, heading, sentences in _CLAIMS:
        assert _section(_OLD[key], heading) == "", claim
        assert _unit(_OLD[key], sentences[0]) == "", claim
        assert _gaps(_flat(_OLD[key]), sentences) == list(sentences), claim
    for spec in _SKELETONS:
        block = _block(_OLD[spec.key], spec.marker)
        assert block, f"the old {spec.key} excerpt has no skeleton"
        assert _table_problems(block, spec) == [f"no line {spec.heading!r}"]


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of the real section is the one gap reported, and an
    empty section lacks every sentence of the claim. A sentence that occurs twice would let a
    clause go and stay green."""
    for claim, key, heading, sentences in _CLAIMS:
        flat = _flat(_held(key, heading))
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
    of the real paragraph, and the claim then reports exactly that sentence. A check on a fragment
    of the sentence would stay green."""
    cut = 0
    for claim, key, heading, sentences in _CLAIMS:
        unit = _unit(_held(key, heading), sentences[0])
        assert unit, f"{claim}: no paragraph opens with {sentences[0]!r}"
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
    """Near-miss that must NOT be reported: the real section with every paragraph re-wrapped at
    `width` columns and bold marks around every `the` is the same text."""
    for claim, key, heading, sentences in _CLAIMS:
        real = _held(key, heading)
        reshaped = _rewrap(real, width).replace(" the ", " **the** ")
        assert reshaped != real, claim
        assert "**the**" in reshaped, f"{claim}: the planted emphasis changed nothing"
        unit = _unit(reshaped, sentences[0])
        assert unit, f"{claim}: the re-wrapped paragraph was not found"
        assert _gaps(unit, sentences) == [], claim


def test_a_claim_is_judged_in_its_own_section_only() -> None:
    """Planted move: the section's body put under another heading of the same file is a section
    that lacks every sentence of its claims. A search of the whole file would still find them and
    pass, which is why each claim is read from its section alone."""
    for claim, key, heading, sentences in _CLAIMS:
        text = _read(_FILES[key])
        section = _held(key, heading)
        head, _, body = section.partition("\n")
        moved = text.replace(
            section, f"{head}\n\n(a stub)\n\n## Elsewhere\n\n{body}\n", 1
        )
        assert moved != text, f"{claim}: the planted move changed nothing"
        after = _section(moved, heading)
        assert after.strip(), f"{claim}: the planted text has no section"
        assert _unit(after, sentences[0]) == "", claim
        assert _gaps(_flat(after), sentences) == list(sentences), claim
        assert _gaps(_flat(moved), sentences) == [], (
            f"{claim}: a whole-file search would fail"
        )


def test_the_table_check_sees_planted_defects() -> None:
    """Each defect is planted in the real skeleton in turn: the new heading gone, a column gone
    from the header row, the rule row gone, and the heading swapped with its next neighbour. The
    first three are the one problem reported; the swap is reported as out of order. The unplanted
    block reports nothing."""
    one_problem = ["the header row or the rule row is not the one named"]
    for spec in _SKELETONS:
        block = _block(_read(_FILES[spec.key]), spec.marker)
        assert _table_problems(block, spec) == [], spec.key
        lines = block.split("\n")
        at = lines.index(spec.heading)
        gone = "\n".join(lines[:at] + lines[at + 1 :])
        assert _table_problems(gone, spec) == [f"no line {spec.heading!r}"], spec.key
        # The table under the new heading is hit by line, because the skeletons hold other
        # tables whose rule rows look the same.
        narrow = [
            *lines[: at + 2],
            spec.header.rsplit("|", 2)[0] + "|",
            *lines[at + 3 :],
        ]
        assert narrow[at + 2] != lines[at + 2], spec.key
        assert _table_problems("\n".join(narrow), spec) == one_problem, spec.key
        ruleless = [*lines[: at + 3], *lines[at + 4 :]]
        assert len(ruleless) == len(lines) - 1, spec.key
        assert _table_problems("\n".join(ruleless), spec) == one_problem, spec.key
    charter = _SKELETONS[0]
    lines = _block(_read(_FILES["charter"]), charter.marker).split("\n")
    at = lines.index(charter.heading)
    after = lines.index(charter.after or "")
    lines[at], lines[after] = lines[after], lines[at]
    assert "the headings are out of order" in _table_problems("\n".join(lines), charter)


_SECTIONS = "\n".join(
    [
        "#### 8. A look-alike that only contains the wanted prefix",
        "### 8. First",
        "first body",
        "#### 8.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "### 9. nor is this one",
        "```",
        "### 9. Second",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, runs to the end of the text
    when none follows, and finds nothing for a heading that is not there, so an absent section is
    reported and not read as an empty pass."""
    first = _section(_SECTIONS, "### 8.")
    assert first.startswith("### 8. First"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert "second body" in _section(_SECTIONS, "### 9. Second")
    assert _section(_SECTIONS, "### 99.") == ""
    assert _gaps(_flat(_section(_SECTIONS, "### 99.")), _SENTENCES) == list(_SENTENCES)


_UNITS = "\n".join(
    [
        "### Heading is dropped",
        "The first paragraph is",
        "  broken over two lines.",
        "",
        "- **A lead.** An item that quotes the first paragraph is",
        "the first paragraph is broken over two lines. again, in column 0.",
        "- **A second lead.** Last item.",
        "",
        "```text",
        "- **A fenced lead.** It is not an item.",
        "### Nor is this a heading",
        "```",
        "",
        "Closing paragraph.",
        "",
    ]
)


def test_the_unit_finder_keeps_its_edges() -> None:
    """The finder drops a heading, reads a paragraph whole across a line break, reads an item whole
    whether its continuation lines are indented or in column 0, stops at the next item, takes
    nothing inside a fence for an item or a heading, takes an item that only contains the lead for
    the one that opens with it never, and finds nothing for a lead that is absent."""
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


_FENCED = "\n".join(
    [
        "## Outside",
        "```markdown",
        "## Inside one",
        "```",
        "text between",
        "```markdown",
        "## Inside two",
        "| a | b |",
        "```",
        "",
    ]
)


def test_the_block_finder_keeps_its_edges() -> None:
    """The finder returns the first fenced block that holds the marker, takes none for a marker
    only the text outside a fence holds, and finds nothing for an absent marker."""
    assert _block(_FENCED, "## Inside").startswith("## Inside one")
    assert _block(_FENCED, "## Inside two").startswith("## Inside two")
    assert "| a | b |" in _block(_FENCED, "| a | b |")
    assert _block(_FENCED, "text between") == ""
    assert _block(_FENCED, "## Outside") == ""
    assert _block(_FENCED, "an absent marker") == ""
    assert _block("", "an absent marker") == ""
