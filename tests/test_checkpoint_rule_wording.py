"""Every session and worker checkpoints the same way, and the rule reaches the kit's adopters.

The kit's own AGENTS.md told every worker and session to save a checkpoint at each milestone and at
the latest every hour, but an adopter gets the plugin files and an AGENTS.md seeded from the kit's
template, and neither said so. The worker preamble had a worker write its report early (section 3)
and a continuation prompt at its stop line (section 5), with no cadence, no contents and no resume
rule, so a worker or a session that a usage limit, a network error or a crash stopped lost what it
held in memory.

What the text says now, in four places of four files:

* section 3 of the worker preamble holds a "Checkpoints" group ahead of the paragraph that closes
  the section ("Publish before extras."): a lead paragraph that tells a checkpoint apart from the
  report and from the continuation prompt of section 5 and binds the orchestrating session as much
  as every worker, then five bullets: the cadence (each milestone and at the latest every hour, an
  uncalibrated starting value, and what counts as a milestone); what a checkpoint says (done, left,
  where the results are, anything shared that is held); its next wake condition, with the command
  that reads it; where it is written (the hand-off file's Status, "Not done" and Continue sections,
  or the checkpoint file the brief names, newest block first); and the resume rule (from the latest
  checkpoint, re-read and re-checked by command, losing only the work since);
* the "Report back" section of the brief template's skeleton has the dispatcher name the checkpoint
  file and the cadence, and points at section 3 of the preamble;
* the "Orchestration and delegation" section of the kit's own AGENTS.md and of the template the
  scaffold seeds hold one checkpoint bullet of at most four lines, in the same words.

Where each place reaches. The preamble and the brief template ship in the Orchestration plugin, so
every adopter gets them with the plugin. AGENTS.md is a seed: the scaffold writes it once and
`kit-setup refresh` rewrites only its marked blocks, and this section holds none, so only a project
seeded after this change gets the bullet; one seeded before gets the rule from the plugin files.

THE SURFACE, in numbers the tests assert: 4 places in 4 files; 6 claims and 13 sentences in section
3 of the preamble, 1 claim and 2 sentences in the skeleton's "Report back" section, and 1 claim and
2 sentences in the "Orchestration and delegation" section of each AGENTS.md. A claim holds when the
block it names (a paragraph or a list item, read whole) holds every one of its sentences whole
(lower-cased, bold marks dropped, whitespace collapsed), so a clause cannot be dropped while the
rest of its sentence still matches. Each sentence occurs once in its place and is fired at a planted
removal; each sentence of more than one word is also fired at a planted cut of its last clause. The
rest of each file is held by other tests and is not asserted here.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATION_SKILLS = _ROOT / "plugins" / "orchestration" / "skills"
_PREAMBLE = _ORCHESTRATION_SKILLS / "agent-delegate" / "assets" / "worker-preamble.md"
_TEMPLATE = _ORCHESTRATION_SKILLS / "orchestrate" / "references" / "brief-template.md"
_KIT_AGENTS = _ROOT / "AGENTS.md"
_SEEDED_AGENTS = (
    _ROOT
    / "plugins"
    / "core"
    / "src"
    / "lemmi_ai_kit"
    / "assets"
    / "templates"
    / "AGENTS.md"
)
_AGENTS_FILES = (_KIT_AGENTS, _SEEDED_AGENTS)

_DOT = chr(0xB7)  # the middle dot in the preamble's numbered headings
_EM = chr(0x2014)  # the em dash the old text carried
_SECTION_2 = f"## 2 {_DOT}"
_SECTION_3 = f"## 3 {_DOT}"
_REPORT_BACK = "## Report back"
_ORCHESTRATION = "### Orchestration and delegation"
_HEADING = re.compile(r"^(#{1,6})\s")
_RULE = re.compile(r"^-{3,}\s*$")  # the `---` line that ends each numbered section
_PUBLISH_LEAD = "publish before extras."
_AGENTS_MAX_LINES = 4

Claim = tuple[str, tuple[str, ...]]

# (claim id, the sentences of its block, whole, in order; lower-cased, bold marks dropped,
# whitespace collapsed). The first sentence is the lead that opens the block.
_PREAMBLE_CLAIMS: tuple[Claim, ...] = (
    (
        "lead",
        (
            "checkpoints.",
            "the report holds what you found; a checkpoint holds where the work stands, so a "
            "successor can pick it up if you are stopped before the report or the continuation "
            "prompt of section 5 is written.",
            "these rules bind the orchestrating session as much as every worker it starts.",
        ),
    ),
    (
        "cadence",
        (
            "write a checkpoint at each milestone and at the latest every hour (starting value, "
            "uncalibrated).",
            "a milestone is a verified step, a commit, a finished sub-task or a hand-off to "
            "another worker.",
        ),
    ),
    (
        "contents",
        (
            "a checkpoint says what is done, what is left and where the results are.",
            "name the commit ids, the report files and paths, and the state of anything shared "
            "that you hold, such as a lock.",
        ),
    ),
    (
        "wake",
        (
            "a checkpoint names its next wake condition: the event or the time that resumes the "
            "work, with the command that reads it.",
            "a successor that cannot tell what you were waiting for starts over.",
        ),
    ),
    (
        "where",
        (
            "write it where your brief says.",
            'that is the hand-off file it names, in its status, "not done" and continue '
            "sections, or the checkpoint file it names, with the newest block first.",
        ),
    ),
    (
        "resume",
        (
            "a worker or session stopped by a usage limit, a network error or a crash is resumed "
            "from its latest checkpoint.",
            "the resumer re-reads it and re-checks each claim in it by command before acting, "
            "and only the work since that checkpoint is lost.",
        ),
    ),
)
_PREAMBLE_SENTENCES = tuple(s for _, sentences in _PREAMBLE_CLAIMS for s in sentences)
_PREAMBLE_LEADS = tuple(sentences[0] for _, sentences in _PREAMBLE_CLAIMS)

_TEMPLATE_CLAIM: Claim = (
    "report back",
    (
        "checkpoint: write one to `<the hand-off file or a checkpoint file>` at each milestone "
        "and at the latest every `<cadence>`;",
        "section 3 of the worker preamble says what it holds and how a stopped worker is "
        "resumed from it.",
    ),
)

_AGENTS_CLAIM: Claim = (
    "agents",
    (
        "every session and worker writes a checkpoint to a file at each milestone and at the "
        "latest every hour (starting value, uncalibrated): what is done, what is left, where the "
        "results are, and the next wake condition.",
        "one stopped by a usage limit, a network error or a crash resumes from its latest "
        "checkpoint, re-checked by command, and loses only the work since (`agent-delegate` "
        "worker preamble, section 3).",
    ),
)

# The places as they stood before the change, shortened to lines of ASCII text (the em dash is
# built from its code point): the known positives the checks must see the gap in.
_OLD_SECTION_3 = f"""\
{_SECTION_3} Write your report file EARLY and INCREMENTALLY

In the one recorded controlled contrast, a worker told to write its report early and incrementally
survived the same usage window that killed its sibling, and delivered. One occurrence {_EM} so this
is a practice with a named test (re-measure the no-return rate after adopting it), not a law.

**Publish before extras.** Write the result (or create the branch or ref your brief names) before
any optional verification, and keep the evidence on disk: a session limit stops every agent at
once, and a resume starts from that state.
"""

_OLD_REPORT_BACK = """\
## Report back (keep it short)
2. Definition-of-done result (command output / evidence)
3. Anything surprising or off-brief you noticed (do not fix it)

If you may write files, write this report file EARLY and INCREMENTALLY, not at the end: workers are
killed mid-run by usage limits often enough that a report written only at the end is often never
written at all.
"""

_OLD_ORCHESTRATION = f"""\
{_ORCHESTRATION}
Uses: orchestrate (workflow), agent-delegate (task)
- Delegation through that plugin uses its brief contract (one concern, inlined context, self-checkable
  definition of done, short report) {_EM} see `references/brief-template.md` in the `orchestrate` skill.
- A worker's summary is a claim: verify the actual output against the definition of done before
  merging. For high-stakes decisions, task independent workers in parallel without showing them
  each other's answers, then synthesize.
- Keep single-agent when judgment is the work or the subtasks can't be crisply named.
"""


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


def _skeleton(text: str) -> str:
    """The lines inside the first ```markdown fence, without the fence lines: the brief skeleton
    the template asks a dispatcher to fill. Empty when there is no such fence."""
    body: list[str] = []
    inside = False
    for line in text.split("\n"):
        if not inside:
            inside = line.startswith("```markdown")
            continue
        if line.strip() == "```":
            return "\n".join(body)
        body.append(line)
    return ""


def _blocks(text: str) -> list[list[str]]:
    """The blocks of `text` outside fenced code: a heading line; a list item, from a line that
    begins with "- " to a blank line or the next item, its other lines indented or in column 0;
    or a paragraph, up to a blank line or the next item. A fenced line and a `---` rule belong to
    no block."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            current = None
            continue
        if in_fence or not line.strip() or _RULE.match(line):
            current = None
            continue
        if _HEADING.match(line):
            blocks.append([line])
            current = None
            continue
        if current is None or line.startswith("- "):
            current = [line]
            blocks.append(current)
        else:
            current.append(line)
    return blocks


def _joined(lines: list[str]) -> str:
    """A block's lines as one text, a list item's "- " dropped."""
    text = "\n".join(lines)
    return text[2:] if text.startswith("- ") else text


def _block_lines(text: str, lead: str) -> list[str]:
    """The lines of the first block whose flat text opens with `lead`; empty when none does. A
    block that merely contains the lead further on is not that block."""
    for lines in _blocks(text):
        if _flat(_joined(lines)).startswith(lead):
            return lines
    return []


def _block(text: str, lead: str) -> str:
    """The flat text of the first block that opens with `lead`; empty when none does."""
    lines = _block_lines(text, lead)
    return _flat(_joined(lines)) if lines else ""


def _gaps(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _tail(sentence: str) -> str:
    """The last clause of a sentence: the words after its last comma, colon or semicolon, or its
    last three words when it has none."""
    parts = re.split(r"[,:;] ", sentence)
    return parts[-1] if len(parts) > 1 else " ".join(sentence.split()[-3:])


def _rewrap(text: str, width: int) -> str:
    """Every paragraph and list item of `text` re-wrapped at `width` columns, a list item's
    continuation lines indented by two spaces, whatever the file's own wrap was: a bold lead can
    break over two lines. Headings are kept, and one blank line follows every block."""
    out: list[str] = []
    for lines in _blocks(text):
        if _HEADING.match(lines[0]):
            out.extend([lines[0], ""])
            continue
        item = lines[0].startswith("- ")
        words = " ".join(lines).split()[1 if item else 0 :]
        rows: list[str] = []
        row = "-" if item else ""
        for word in words:
            if row.strip("- ") and len(row) + 1 + len(word) > width:
                rows.append(row)
                row = " " if item else ""
            row = f"{row} {word}" if row else word
        rows.append(row)
        out.extend([*rows, ""])
    return "\n".join(out)


def _section_3() -> str:
    section = _section(_read(_PREAMBLE), _SECTION_3)
    assert section.strip(), "section 3 is missing from worker-preamble.md"
    return section


def _report_back() -> str:
    skeleton = _skeleton(_read(_TEMPLATE))
    assert skeleton.strip(), "brief-template.md has no fenced skeleton"
    section = _section(skeleton, _REPORT_BACK)
    assert section.strip(), "the skeleton has no Report back section"
    return section


def _orchestration(path: Path) -> str:
    section = _section(_read(path), _ORCHESTRATION)
    assert section.strip(), f"{path.name} has no {_ORCHESTRATION!r} section"
    return section


def _places() -> list[tuple[str, str, tuple[Claim, ...]]]:
    """Each place as (name, its text, its claims)."""
    return [
        ("preamble section 3", _section_3(), _PREAMBLE_CLAIMS),
        ("skeleton report back", _report_back(), (_TEMPLATE_CLAIM,)),
        *(
            (
                f"{path.name} at {path.parent.name}",
                _orchestration(path),
                (_AGENTS_CLAIM,),
            )
            for path in _AGENTS_FILES
        ),
    ]


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_PREAMBLE_CLAIMS), len(_PREAMBLE_SENTENCES)) == (6, 13)
    assert len(_TEMPLATE_CLAIM[1]) == 2 and len(_AGENTS_CLAIM[1]) == 2
    every = [*_PREAMBLE_SENTENCES, *_TEMPLATE_CLAIM[1], *_AGENTS_CLAIM[1]]
    assert len(set(every)) == len(every), "a sentence is listed twice"
    for sentence in every:
        others = [other for other in every if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    files = {_PREAMBLE, _TEMPLATE, *_AGENTS_FILES}
    assert len(files) == 4
    for path in files:
        assert path.is_file(), f"{path} is not a file"
    assert len(_places()) == 4
    found = [lead for lead in _PREAMBLE_LEADS if _block(_section_3(), lead)]
    assert len(found) == 6, f"{len(found)} of 6 claim blocks are in section 3: {found}"


# --- each place states its claims ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("claim", "sentences"), _PREAMBLE_CLAIMS, ids=[c[0] for c in _PREAMBLE_CLAIMS]
)
def test_section_3_states_the_claim(claim: str, sentences: tuple[str, ...]) -> None:
    """Red before the change: section 3 had four paragraphs and no checkpoint rule."""
    block = _block(_section_3(), sentences[0])
    assert block, f"no block of section 3 opens with {sentences[0]!r}"
    missing = _gaps(block, sentences)
    assert not missing, f"the {claim!r} block does not state: {missing}"


def test_the_group_sits_directly_before_the_closing_paragraph() -> None:
    """The lead paragraph and the five bullets are one run of blocks in this order, and the
    paragraph that closes section 3 ("Publish before extras.") follows the run directly."""
    flats = [_flat(_joined(lines)) for lines in _blocks(_section_3())]
    order = [
        next((at for at, flat in enumerate(flats) if flat.startswith(lead)), -1)
        for lead in _PREAMBLE_LEADS
    ]
    assert -1 not in order, f"a block of the group is missing: {order}"
    assert order == list(range(order[0], order[0] + len(order))), (
        f"the group is not one run of blocks in order: {order}"
    )
    assert flats[-1].startswith(_PUBLISH_LEAD), (
        "section 3 no longer closes with that paragraph"
    )
    assert order[-1] == len(flats) - 2, (
        "the group does not end directly before that paragraph"
    )


def test_each_claim_of_the_preamble_has_one_home() -> None:
    """ONE block per claim: exactly one block of the whole preamble opens with each lead, and each
    sentence occurs once in the file, so the rule has no second copy to drift from the first."""
    text = _read(_PREAMBLE)
    flat = _flat(text)
    for claim, sentences in _PREAMBLE_CLAIMS:
        openers = [
            lines
            for lines in _blocks(text)
            if _flat(_joined(lines)).startswith(sentences[0])
        ]
        assert len(openers) == 1, (
            f"{claim}: {len(openers)} blocks open with {sentences[0]!r}"
        )
        for sentence in sentences:
            assert flat.count(sentence) == 1, (
                f"{claim}: {sentence!r} occurs {flat.count(sentence)} times in the file"
            )


def test_the_skeleton_names_the_checkpoint_in_report_back() -> None:
    """Red before the change: the Report back section said to write the report early and named no
    checkpoint. The line sits in the skeleton, so the dispatcher fills its two placeholders."""
    sentences = _TEMPLATE_CLAIM[1]
    block = _block(_report_back(), sentences[0])
    assert block, f"no block of the Report back section opens with {sentences[0]!r}"
    assert not _gaps(block, sentences), _gaps(block, sentences)
    assert _flat(_read(_TEMPLATE)).count(sentences[0]) == 1, (
        "the line occurs more than once"
    )


@pytest.mark.parametrize("path", _AGENTS_FILES, ids=["kit", "seeded"])
def test_each_agents_file_states_the_bullet(path: Path) -> None:
    """Red before the change: neither section said anything about checkpoints."""
    section = _orchestration(path)
    sentences = _AGENTS_CLAIM[1]
    lines = _block_lines(section, sentences[0])
    assert lines, f"{path.name}: no bullet opens with {sentences[0]!r}"
    assert lines[0].startswith("- "), f"{path.name}: the block is not a list item"
    assert len(lines) <= _AGENTS_MAX_LINES, (
        f"{path.name}: the bullet has {len(lines)} lines, more than {_AGENTS_MAX_LINES}"
    )
    assert not _gaps(_block(section, sentences[0]), sentences)


def test_the_two_agents_files_say_the_same_bullet() -> None:
    lead = _AGENTS_CLAIM[1][0]
    kit = _block(_orchestration(_KIT_AGENTS), lead)
    seeded = _block(_orchestration(_SEEDED_AGENTS), lead)
    assert kit, "the kit's AGENTS.md has no checkpoint bullet"
    assert kit == seeded, f"the files disagree: {kit!r} versus {seeded!r}"


# --- the checks can fail ------------------------------------------------------------------------


def test_the_old_text_lacks_every_claim() -> None:
    """Known positive: each place as it stood has no such block, and the finder says so; no
    sentence is in any part of it. The blocks that stayed are still found, so the finder sees."""
    for lead in _PREAMBLE_LEADS:
        assert _block(_OLD_SECTION_3, lead) == "", lead
    assert _gaps(_flat(_OLD_SECTION_3), _PREAMBLE_SENTENCES) == list(
        _PREAMBLE_SENTENCES
    )
    assert _block(_OLD_SECTION_3, _PUBLISH_LEAD)
    assert _block(_OLD_REPORT_BACK, _TEMPLATE_CLAIM[1][0]) == ""
    assert _gaps(_flat(_OLD_REPORT_BACK), _TEMPLATE_CLAIM[1]) == list(
        _TEMPLATE_CLAIM[1]
    )
    assert _block(_OLD_REPORT_BACK, "if you may write files")
    assert _block(_OLD_ORCHESTRATION, _AGENTS_CLAIM[1][0]) == ""
    assert _gaps(_flat(_OLD_ORCHESTRATION), _AGENTS_CLAIM[1]) == list(_AGENTS_CLAIM[1])
    assert _block(_OLD_ORCHESTRATION, "keep single-agent when judgment is the work")


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of the real place is the one gap reported, and an
    empty place lacks every sentence. A sentence that occurs twice would let a clause go and stay
    green."""
    for name, text, claims in _places():
        sentences = tuple(s for _, group in claims for s in group)
        flat = _flat(text)
        assert _gaps(flat, sentences) == [], (
            f"{name}: a sentence is missing at the start"
        )
        for sentence in sentences:
            assert flat.count(sentence) == 1, (
                f"{name}: {sentence!r} occurs {flat.count(sentence)} times"
            )
            assert _gaps(flat.replace(sentence, ""), sentences) == [sentence], sentence
        assert _gaps("", sentences) == list(sentences)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the last clause of each sentence (after its last comma, colon or
    semicolon, or its last three words) is cut out of the real block, and the claim then reports
    exactly that sentence. A one-word lead has no clause to cut and is fired at by the planted
    removal above; every other sentence is fired at here, and the count says so."""
    cut = 0
    for name, text, claims in _places():
        for claim, sentences in claims:
            block = _block(text, sentences[0])
            assert block, f"{name}: no block opens with {sentences[0]!r}"
            assert not _gaps(block, sentences), f"{name}: {claim}"
            for sentence in sentences:
                tail = _tail(sentence)
                if tail == sentence:
                    assert len(sentence.split()) == 1, (
                        f"no clause to cut from {sentence!r}"
                    )
                    continue
                assert block.count(tail) == 1, (
                    f"{tail!r} is not a clause of one sentence"
                )
                assert _gaps(block.replace(tail, ""), sentences) == [sentence], (
                    name,
                    sentence,
                )
                cut += 1
    every = (
        len(_PREAMBLE_SENTENCES) + len(_TEMPLATE_CLAIM[1]) + 2 * len(_AGENTS_CLAIM[1])
    )
    assert cut == every - 1, (
        f"{cut} clauses cut of {every} sentences, one of them a one-word lead"
    )


@pytest.mark.parametrize("width", [40, 72, 100])
def test_a_rewrapped_and_reemphasised_place_still_holds_its_claims(width: int) -> None:
    """Near-miss that must NOT be reported: each real place with its paragraphs and list items
    re-wrapped at `width` columns, so that a bold lead breaks over two lines, and bold marks
    around one more word, is the same text."""
    for name, text, claims in _places():
        reshaped = _rewrap(text, width).replace("checkpoint", "**checkpoint**", 1)
        assert "**checkpoint**" in reshaped, (
            f"{name}: the planted emphasis changed nothing"
        )
        for claim, sentences in claims:
            block = _block(reshaped, sentences[0])
            assert block, f"{name}: the re-wrapped {claim!r} block was not found"
            assert _gaps(block, sentences) == [], (name, claim)


def test_the_claims_are_judged_inside_section_3_only() -> None:
    """Planted move: the group cut out of section 3 and put into the section before it is a
    section 3 that lacks every claim and exactly them. A search of the whole file would still find
    every sentence and pass, which is why each claim is read from section 3 alone."""
    blocks = _blocks(_section_3())
    moved = [
        lines for lines in blocks if _flat(_joined(lines)).startswith(_PREAMBLE_LEADS)
    ]
    kept = [lines for lines in blocks if lines not in moved]
    assert len(moved) == len(_PREAMBLE_LEADS), "the group to move is not in section 3"
    text = "\n\n".join(
        [f"{_SECTION_2} Elsewhere", *("\n".join(lines) for lines in [*moved, *kept])]
    )
    after = _section(text, _SECTION_3)
    assert after.strip(), "the planted text has no section 3"
    for lead in _PREAMBLE_LEADS:
        assert _block(after, lead) == "", lead
    assert _gaps(_flat(after), _PREAMBLE_SENTENCES) == list(_PREAMBLE_SENTENCES)
    assert _gaps(_flat(text), _PREAMBLE_SENTENCES) == [], (
        "a whole-file search would have passed"
    )


_SECTIONS = "\n".join(
    [
        "#### 3. A look-alike that only contains the wanted prefix",
        "## 3. First",
        "first body",
        "### 3.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "## 4. nor is this one",
        "```",
        "## 4. Second",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, runs to the end of the text
    when none follows, and finds nothing for a heading that is not there, so an absent section is
    reported and not read as an empty pass."""
    first = _section(_SECTIONS, "## 3.")
    assert first.startswith("## 3. First"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert "second body" in _section(_SECTIONS, "## 4. Second")
    assert _section(_SECTIONS, "## 99.") == ""


_BLOCKS = "\n".join(
    [
        "Evidence line before the list.",
        "- **The first lead is",
        "  broken over two lines.** Its body says the second lead is not here.",
        "- **The second lead.** A body that quotes the first lead is",
        "the first lead is broken over two lines. again, in column 0.",
        "```text",
        "- **A fenced lead.** It is not an item.",
        "```",
        "",
        "**A paragraph lead.** Its body ends at the blank line.",
        "",
        "- **The third lead.** Last body.",
        "",
        "**After the list.** A paragraph after a blank line is not part of the item before it.",
        "",
    ]
)


def test_the_block_finder_keeps_its_edges() -> None:
    """The finder reads a list item whole whether its lead is bold or broken over two lines and
    whether its other lines are indented or in column 0, ends it at the next item, a fence or a
    blank line, reads a paragraph as a block of its own, takes no fenced line for a block, does not
    take a block that only contains the lead for the one that opens with it, and finds nothing for
    a lead that is absent."""
    first = _block(_BLOCKS, "the first lead is broken over two lines.")
    assert first.startswith("the first lead is broken over two lines. its body"), first
    assert "a body that quotes" not in first, first
    second = _block(_BLOCKS, "the second lead.")
    assert second.endswith("again, in column 0."), second
    assert _block(_BLOCKS, "a fenced lead.") == ""
    assert _block(_BLOCKS, "its body says") == ""
    assert _block(_BLOCKS, "a paragraph lead.") == (
        "a paragraph lead. its body ends at the blank line."
    )
    assert _block(_BLOCKS, "the third lead.") == "the third lead. last body."
    assert _block(_BLOCKS, "after the list.").endswith("the item before it.")
    assert (
        _block(_BLOCKS, "evidence line before the list.")
        == "evidence line before the list."
    )
    assert _block(_BLOCKS, "an absent lead.") == ""
    assert _block("", "an absent lead.") == ""
    assert len(_block_lines(_BLOCKS, "the first lead is broken over two lines.")) == 2


def test_the_skeleton_finder_keeps_its_edges() -> None:
    """The finder returns the lines inside the first ```markdown fence, skips a fence of another
    language before it and the text after it, and returns nothing when there is no such fence."""
    text = "\n".join(
        [
            "intro",
            "```bash",
            "## Report back (a decoy in another fence)",
            "```",
            "```markdown",
            "## Report back",
            "inside",
            "```",
            "## Report back",
            "outside",
        ]
    )
    skeleton = _skeleton(text)
    assert skeleton == "## Report back\ninside", skeleton
    assert "outside" not in _section(skeleton, _REPORT_BACK)
    assert _skeleton("no fence here") == ""
    assert _skeleton("```markdown\nnever closed") == ""
