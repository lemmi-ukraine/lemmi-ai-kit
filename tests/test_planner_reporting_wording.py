"""The planner's references carry three rules about what a plan leans on, and a brief carries a fourth.

Three documents of a multi-session initiative each leaned on something that had gone stale or had
never been asked for. The charter's value estimate and falsifier leaned on past volume, which
measures the exposure that produced it: when discoverability, gating or a release is about to
change, past volume says nothing about what follows. A roadmap's cut membership was copied into the
definition of done, the assertion list and the field sets, and each copy then disagreed with the
others. A gate approved a spec slice without recording which of the operator's questions it had
answered, and the slice's tasks assumed the answers.

Each rule is a paragraph or a bullet in the one section that owns it:

* `initiative-planner/references/charter-template.md`, section "Expected value": ask whether
  exposure has changed before past volume is read as a value; section "Falsifiers": a falsifier
  built on past volume needs that check first;
* `initiative-planner/references/roadmap-template.md`, section 4 "Phases and gates": membership
  lives in one table, with the lists derived from it, ids with letter suffixes enumerated and the
  table's checker certified on a clean and a defect-injected pair; and a gate that approves a spec
  slice records the slice's operator questions in an approval record; section 7 "What has NOT been
  decided": each open question carries an id that record can cite;
* `orchestrate/references/brief-template.md`, section "Rules a dispatch brief carries": an
  implementation brief for an approved slice starts from that record, greps it for every question
  id its tasks cite, and treats a count of 0 as a stop.

The record is called an approval record. The learnings consolidator owns the other name, a file
that lets the buffer be drained, so none of the three files uses it
(`test_no_place_calls_the_record_a_gate_record`). Each place also states the evidence level,
because the rules were observed in one project's notes and are defaults to re-measure, not
calibrated rules.

THE SURFACE, in numbers the tests assert: 9 claims and 27 phrases in 3 files, over 5 sections. A
claim holds when every one of its phrases is in its section (lower-cased, bold marks dropped,
whitespace collapsed, because the files wrap their lines). Each phrase occurs once in its section
and is fired at a planted removal. The naming guard reads the same 3 files whole. Four checks are
green on the old text: the surface (a count), the section finder and the naming guard on planted
text (instruments), and the naming guard on the real files (none of the 3 held the name). The two
instruments are fired at planted text, so a zero from the guard means it can see.

CLASSES OF SHAPE covered: a phrase dropped; a section emptied; a claim moved to another section of
the same file, where a whole-file search would still find it; a heading renamed or missing, which
fails loudly and never passes on an empty section; a re-wrap and a re-emphasis, which are the same
text; the forbidden name planted, wrapped across a line, and beside two near-misses; the brief's
rule written without its list marker. Shapes not covered are a later round: the position of the
bullet in its list (other rules are added there too), and the wording of any sentence outside the
phrases.
"""

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SKILLS = _REPO / "plugins" / "orchestration" / "skills"
_FILES: dict[str, Path] = {
    "charter": _SKILLS / "initiative-planner" / "references" / "charter-template.md",
    "roadmap": _SKILLS / "initiative-planner" / "references" / "roadmap-template.md",
    "brief": _SKILLS / "orchestrate" / "references" / "brief-template.md",
}
_SIGN = chr(0xA7)
_HEADING = re.compile(r"^(#{1,6})\s")
_GATE_RECORD = re.compile(r"\bgate records?\b")

_EXPECTED_VALUE = "### Expected value"
_FALSIFIERS = "### Falsifiers"
_PHASES = f"### {_SIGN}4 Phases and gates"
_UNDECIDED = f"### {_SIGN}7 What has NOT been decided"
_RULES = "## Rules a dispatch brief carries"

_EVIDENCE = "evidence level: observed in one project's notes, not yet repeated; an uncalibrated default"
_BRIEF_LEAD = "an implementation brief for an approved slice starts from the gate's approval record."

# (claim id, file, the heading of the ONE section that must hold it, the phrases that must all be
# in it; lower-cased, bold marks dropped, whitespace collapsed). The claims, in order: the exposure
# check before past volume; its evidence level; the falsifier line; membership in one table; the
# gate's approval record of the slice's operator questions; the evidence level of those two rules;
# the ids in the list of open questions; the brief that starts from the record; its evidence level.
_ROWS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "exposure-before-past-volume",
        "charter",
        _EXPECTED_VALUE,
        (
            "past volume measures the exposure that produced it",
            "has changed or is about to",
            "past volume measures the old exposure",
            "set an absolute target, measured forward from the change",
            "release sequencing a gate decision",
            'a falsifier of "fewer than n uses in d days, park the rest"',
        ),
    ),
    ("charter-evidence-level", "charter", _EXPECTED_VALUE, (_EVIDENCE,)),
    (
        "falsifier-needs-the-exposure-check",
        "charter",
        _FALSIFIERS,
        (
            "a falsifier built on past volume needs the exposure check from expected value first",
        ),
    ),
    (
        "membership-lives-in-one-table",
        "roadmap",
        _PHASES,
        (
            "membership lives in one table",
            "written once, in the phase work tables",
            "derived from that table, never restated by hand",
            "once ids carry letter suffixes, enumerate them",
            "a range hides the suffixed ones",
            "certify the table's checker on a clean and a defect-injected pair built from one template",
            "state the exact finding counts each must print",
        ),
    ),
    (
        "gate-records-the-slices-operator-questions",
        "roadmap",
        _PHASES,
        (
            "a gate that approves a spec slice records the slice's operator questions",
            f"by its id in the open-questions list ({_SIGN}7)",
            "gets a line in the gate's approval record with its answer",
            'or the words "default accepted" when the operator took the default',
            "leaves the slice's tasks to assume answers nobody gave",
        ),
    ),
    (
        "roadmap-evidence-level",
        "roadmap",
        _PHASES,
        (
            "evidence level of this rule and the one above: observed in one project's notes, "
            "not yet repeated; an uncalibrated default",
        ),
    ),
    (
        "open-questions-carry-ids",
        "roadmap",
        _UNDECIDED,
        ("an id the gate's approval record can cite",),
    ),
    (
        "brief-starts-from-the-approval-record",
        "brief",
        _RULES,
        (
            "an implementation brief for an approved slice starts from the gate's approval record",
            "greps that record for every operator-question id the slice's tasks cite",
            'expecting each to be found with an answer or "default accepted"',
            "a count of 0 is a stop, never a reason to assume the default",
        ),
    ),
    ("brief-evidence-level", "brief", _RULES, (_EVIDENCE,)),
)
_PHRASES = tuple(phrase for *_, phrases in _ROWS for phrase in phrases)
_IDS = [row[0] for row in _ROWS]


def _read(key: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return _FILES[key].read_text(encoding="utf-8").replace("\r\n", "\n")


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


def _held_text(text: str, heading: str, where: str) -> str:
    """The section, and a loud failure naming it when it is missing or empty."""
    section = _section(text, heading)
    assert section.strip(), f"{where}: no section {heading!r}"
    return section


def _held(key: str, heading: str) -> str:
    return _held_text(_read(key), heading, _FILES[key].name)


def _gaps(flat: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in flat]


def _moved_elsewhere(text: str, heading: str) -> str:
    """`text` with the body of the section that opens at `heading` put, whole, under a heading of
    another section: the heading stays and the section under it holds a stub."""
    section = _held_text(text, heading, "the planted move")
    head, _, body = section.partition("\n")
    moved = text.replace(section, f"{head}\n\n(a stub)\n\n## Elsewhere\n\n{body}\n", 1)
    assert moved != text, "the planted move changed nothing"
    return moved


def _gate_record_hits(text: str) -> list[str]:
    """Each use of the consolidator's name for its own file, wrapped across lines or not. A word
    boundary keeps the end of a longer word ("aggregate records") from being read as the name."""
    return _GATE_RECORD.findall(_flat(text))


def _bullet_leads(section: str) -> list[str]:
    """The bold lead of each list item of the section, lower-cased: an item opens at a line that
    starts with a list marker and a bold mark."""
    return [
        line.removeprefix("- **").split("**")[0].lower()
        for line in section.split("\n")
        if line.startswith("- **")
    ]


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    sections = {(key, heading) for _, key, heading, _ in _ROWS}
    triples = {
        (key, heading, phrase)
        for _, key, heading, phrases in _ROWS
        for phrase in phrases
    }
    assert (len(_ROWS), len(_PHRASES), len(sections), len(_FILES)) == (9, 27, 5, 3)
    assert len(triples) == len(_PHRASES), "a phrase is listed twice for one section"
    assert all(phrase == phrase.lower() for phrase in _PHRASES), (
        "a phrase is not lower-cased"
    )
    assert len({path.resolve() for path in _FILES.values()}) == len(_FILES)
    for key, path in _FILES.items():
        assert path.is_file(), f"{path} is not a file"
        assert _read(key).strip(), f"{path.name} is empty"


@pytest.mark.parametrize(("claim", "key", "heading", "phrases"), _ROWS, ids=_IDS)
def test_the_section_states_the_claim(
    claim: str, key: str, heading: str, phrases: tuple[str, ...]
) -> None:
    missing = _gaps(_flat(_held(key, heading)), phrases)
    assert not missing, (
        f"{_FILES[key].name}, section {heading!r}, does not state {claim!r}: missing {missing}"
    )


def test_the_brief_rule_is_a_bullet_of_the_rules_section() -> None:
    """The rule is one bullet of the list: its lead opens a list item, once. The same sentence
    without its list marker is a paragraph, and is not counted."""
    leads = _bullet_leads(_held("brief", _RULES))
    assert leads.count(_BRIEF_LEAD) == 1, (
        f"{leads.count(_BRIEF_LEAD)} bullets lead with it: {leads}"
    )
    planted = f"- **{_BRIEF_LEAD.capitalize()}** A planted item.\n\n**{_BRIEF_LEAD}** A paragraph.\n"
    assert _bullet_leads(planted) == [_BRIEF_LEAD]


def test_no_place_calls_the_record_a_gate_record() -> None:
    """Green on the old text, by construction: none of the three files held the name. It is
    fired at planted text in `test_the_naming_guard_flags_the_name_and_passes_the_near_misses`."""
    for key, path in _FILES.items():
        assert _gate_record_hits(_read(key)) == [], (
            f"{path.name} calls the record a gate record"
        )


# --- the checks can fail -----------------------------------------------------------------------


def test_every_phrase_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section is the one gap reported, and an
    empty section lacks every phrase of the claim. A phrase that occurs twice, or that overlaps
    another, would let a claim lose its wording and stay green."""
    for claim, key, heading, phrases in _ROWS:
        flat = _flat(_held(key, heading))
        assert _gaps(flat, phrases) == [], f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert flat.count(phrase) == 1, (
                f"{phrase!r} occurs {flat.count(phrase)} times"
            )
            assert _gaps(flat.replace(phrase, ""), phrases) == [phrase], phrase
        assert _gaps("", phrases) == list(phrases), claim


def test_a_rewrapped_and_reemphasised_section_still_holds_every_claim() -> None:
    """Near-miss that must NOT be reported: the real section with bold marks around every `the`
    and a line break and an indent at every space is the same text."""
    for claim, key, heading, phrases in _ROWS:
        real = _held(key, heading)
        reshaped = real.replace(" the ", " **the** ").replace(" ", "\n    ")
        assert reshaped != real, claim
        assert _gaps(_flat(reshaped), phrases) == [], claim


def test_a_claim_is_judged_in_its_own_section_only() -> None:
    """Planted move: the section's body put under another heading of the same file is a section
    that lacks every phrase of its claims. A search of the whole file would still find them and
    pass, which is why each claim is read from its section alone."""
    for claim, key, heading, phrases in _ROWS:
        moved = _moved_elsewhere(_read(key), heading)
        assert _gaps(_flat(_section(moved, heading)), phrases) == list(phrases), claim
        assert _gaps(_flat(moved), phrases) == [], (
            f"{claim}: a whole-file search would fail"
        )


_PLANTED = "\n".join(
    [
        "#### Alpha is a look-alike that only contains the wanted prefix",
        "### Alpha",
        "alpha body",
        "#### Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "### Beta in a fence is not a heading either",
        "```",
        "### Beta",
        "beta body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, runs to the end of the text
    when none follows, and finds nothing for a heading that is not there, so an absent section
    fails loudly and is never read as an empty pass."""
    alpha = _section(_PLANTED, "### Alpha")
    assert alpha.startswith("### Alpha\n"), alpha
    for kept in (
        "alpha body",
        "deeper body",
        "a comment in a fence",
        "Beta in a fence",
    ):
        assert kept in alpha, alpha
    assert "beta body" not in alpha, alpha
    assert _section(_PLANTED, "### Beta").startswith("### Beta\nbeta body")
    assert _section(_PLANTED, "### Gamma") == ""
    with pytest.raises(AssertionError, match="no section"):
        _held_text(_PLANTED, "### Gamma", "planted")
    assert _gaps(_flat(_section(_PLANTED, "### Gamma")), _PHRASES) == list(_PHRASES)


def test_the_naming_guard_flags_the_name_and_passes_the_near_misses() -> None:
    """Known positives: the name written plainly, in the plural, in capitals and wrapped across a
    line is each found once. Near-misses that must pass: the record called by its own name, a
    longer word that ends in the same letters, and the words in another order."""
    assert _gate_record_hits("The gate record lists each answer.") == ["gate record"]
    assert _gate_record_hits("two Gate Records are kept") == ["gate records"]
    assert _gate_record_hits("the gate\n    record lists them") == ["gate record"]
    assert _gate_record_hits("the gate's approval record") == []
    assert _gate_record_hits("the aggregate records are bytes") == []
    assert _gate_record_hits("the approval record of the gate") == []
