"""Five small rule texts: a brief's revision line, a rule change sent as a message, a read budget,
the two runs of the publish check, and how wide a wave is.

A rule lives in a file a session reads once, so a rule changed mid-run reached only the sessions
that happened to read it again, and no brief said which version it was written against. A brief
named no read budget, so orientation was read whole. One publish-check run answered two questions,
whether an install from this checkout is safe and whether a push is. And a project rule said a wave
is as wide as the disk and the machine allow, beside a reference that sizes a wave in tokens
against the usage window.

What the text says now, in five places of two files:

* the skeleton of `orchestrate/references/brief-template.md` (its first fenced block) opens with
  its blocker line and then a revision line: when the brief was written, read from the machine
  clock, and the commit it was written against;
* the template's "Rules a dispatch brief carries" section holds one bullet: a rule changed while
  sessions or workers run is sent to each running one as a message, because a session reads its
  brief and the files the brief names once, and the revision line says which version each one read;
* the skeleton's "Context" section has a read-budget line: the files read whole, and the ones read
  only by grep or by their headings;
* in the kit's own `AGENTS.md`, the comment directly above the `publish-check` command in the
  "Commands" block says that a run in a fresh clone of the tip is the push gate and sees only what
  git holds, and that a run in the real checkout is the install gate and also sees the untracked,
  ignored and modified files in the payload, because an install copies the working tree;
* the checkpoint bullet of the kit's "Sub-agents with their own context" rules ends with one
  sentence: a wave has no fixed width, is sized in tokens against the usage window first and then
  held to what the disk and the machine allow, and `references/limit-recovery.md` says how. The
  words of the sentence it replaced, which named the disk and the machine as the only limit, are in
  no part of the file.

THE SURFACE, in numbers the tests assert: 5 places in 2 files, 3 in the template and 2 in
`AGENTS.md`, disjoint by line within each file; 5 claims and 8 sentences, and 1 retired wording
read in the whole of `AGENTS.md`. A claim holds when the block it names (a list item, a
bold-labelled line or the run of comment lines above a command, read whole) holds every one of its
sentences whole (lower-cased, bold and comment marks dropped, whitespace collapsed), so a clause
cannot be dropped while the rest of its sentence still matches. Each sentence occurs once in its
file and in its block and is fired at a planted removal and at a planted cut of its last clause;
each claim is fired at a planted move out of its place, and each block at a re-wrap that must not
be reported. The clock rule in `limit-recovery.md` is held by `test_limit_recovery_wording.py`,
and the other lines of these sections by their own tests; neither is asserted here.
"""

import re
from collections.abc import Callable
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = (
    _ROOT
    / "plugins"
    / "orchestration"
    / "skills"
    / "orchestrate"
    / "references"
    / "brief-template.md"
)
_AGENTS = _ROOT / "AGENTS.md"

_STANDING = "## Standing rules"
_CONTEXT = "## Context"
_DONE = "## Definition of done"
_RULES = "## Rules a dispatch brief carries"
_RULES_OF_THUMB = "Rules of thumb:"
_COMMANDS = "## Commands"
_SUB_AGENTS = "#### Sub-agents with their own context"
_DOCUMENTS = "#### Documents"
_PUBLISH_CHECK = "uv run python -B -m lemmi_ai_kit publish-check"
_AUDIT = "uv run python -B -m lemmi_ai_kit audit-skills --fail-on major"
_BLOCKER_LABEL = "operator-only blocker:"
_REVISION_LABEL = "revision:"
_READ_BUDGET_LABEL = "read budget:"
_EM_DASH = chr(0x2014)
_HEADING = re.compile(r"^(#{1,6})\s")
_LABEL = re.compile(r"^\*\*[^*]+:\*\*")  # a bold label, as the blocker line opens with

Claim = tuple[str, tuple[str, ...]]
Finder = Callable[[str], list[str]]

# (claim id, the sentences of its block, whole, in order; lower-cased, bold and comment marks
# dropped, whitespace collapsed)
_REVISION: Claim = (
    "revision line",
    (
        "revision: <when this brief was written, read from the machine clock, and the commit it "
        "was written against>",
    ),
)
_BROADCAST: Claim = (
    "rule change sent",
    (
        "a rule changed while sessions or workers run is sent to each running one as a message.",
        "a session reads its brief and the files the brief names once, so a change that is only "
        "written to a file reaches only the sessions that happen to read it again.",
        "the revision line under the blocker line says which version each one read.",
    ),
)
_READ_BUDGET: Claim = (
    "read budget",
    (
        "read budget: <the files read whole, and the ones read only by grep or by their "
        "headings; reading everything whole can cost more context than the work>",
    ),
)
_GATES: Claim = (
    "two gates",
    (
        "run in a fresh clone of the tip, it is the push gate: it sees only what git holds.",
        "run in the real checkout, it is the install gate: an install copies the working tree, "
        "so this run also sees untracked, ignored and modified files in the payload.",
    ),
)
_WAVE: Claim = (
    "wave width",
    (
        "a wave has no fixed width: it is sized in tokens against the usage window first, then "
        "held to what the disk and the machine allow (see `references/limit-recovery.md` in the "
        "`orchestrate` skill).",
    ),
)
_CLAIMS: tuple[Claim, ...] = (_REVISION, _BROADCAST, _READ_BUDGET, _GATES, _WAVE)
_SENTENCES = tuple(s for _, sentences in _CLAIMS for s in sentences)

# The words of the replaced sentence that contradicted the reference: they named the disk and the
# machine as the only limit on a wave.
_RETIRED: tuple[str, ...] = ("as wide as the disk and the machine allow",)

# The lead of the checkpoint bullet that holds the wave sentence; the lead is not this change's.
_WAVE_LEAD = (
    "read the usage window before a wave, and have every worker and session save a checkpoint "
    "to a file at each milestone and at the latest every hour."
)

# The opening, the comment and the bullet as they stood before: the known positives.
_OLD_OPENING = (
    "```markdown\n"
    '**Operator-only blocker:** <the one thing only the operator can clear, or the words "no '
    'operator-only blocker">\n'
    "\n"
    "## Standing rules\n"
    "```\n"
)
_OLD_COMMANDS = f"""\
# Before publishing or installing anything an adopter will consume, and as a CI gate.
# -B is not optional: this package lives inside the plugin payload, so without it
# the import writes .pyc into the tree being measured and the check blocks on
# files it created itself. Exit 0 clean, 1 blocked, 2 could-not-measure {_EM_DASH} gate on
# `!= 0`, because 2 means the answer is unknown, not good.
uv run python -B -m lemmi_ai_kit publish-check
"""
_OLD_WAVE_BULLET = """\
- **Read the usage window before a wave, and have every worker and session save a checkpoint to a
  file at each milestone and at the latest every hour.** A checkpoint says what is done, what is
  left and where the results are (commit ids, report files), so a worker or session stopped by a
  usage limit is resumed from its latest checkpoint and loses only the work since. Two of three
  workers died to usage-limit and access errors mid-wave, and a worker that dies returns exactly
  what one that found nothing returns. A wave is as wide as the disk and the machine allow.
"""


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _flat(text: str) -> str:
    """Bold marks dropped, every run of whitespace one space, lower-cased: a re-wrapped line or
    a re-emphasised word is not a different sentence."""
    return " ".join(text.replace("**", "").split()).lower()


def _flat_block(lines: list[str]) -> str:
    """A block's lines as one flat text: a list item's "- " and each comment line's "#" dropped."""
    if lines and all(line.startswith("#") for line in lines):
        lines = [line[1:] for line in lines]
    text = "\n".join(lines)
    return _flat(text[2:] if text.startswith("- ") else text)


def _flat_file(text: str) -> str:
    """A whole file as one flat text, the `#` marks that open a line dropped, so a sentence held
    in a run of comment lines reads as it does in its block."""
    return _flat("\n".join(line.lstrip("#") for line in text.split("\n")))


def _section_span(lines: list[str], heading: str) -> tuple[int, int]:
    """The line range from the first heading line that starts with `heading` to the next heading
    of the same or a higher level; a `#` line inside a fenced block is not a heading. (0, 0) when
    there is none."""
    start = level = 0
    opened = in_fence = False
    for at, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING.match(line)
        if not opened:
            if found is not None and line.startswith(heading):
                start, level, opened = at, len(found[1]), True
            continue
        if found is not None and len(found[1]) <= level:
            return start, at
    return (start, len(lines)) if opened else (0, 0)


def _section(text: str, heading: str) -> str:
    lines = text.split("\n")
    start, end = _section_span(lines, heading)
    return "\n".join(lines[start:end])


def _fence_span(lines: list[str]) -> tuple[int, int]:
    """The line range inside the first fenced block, its fence lines left out; (0, 0) when there
    is none or it is never closed."""
    opened: int | None = None
    for at, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            if opened is not None:
                return opened + 1, at
            opened = at
    return 0, 0


def _fence(text: str) -> str:
    lines = text.split("\n")
    start, end = _fence_span(lines)
    return "\n".join(lines[start:end])


def _opening(skeleton: str) -> str:
    """The skeleton's lines above its first heading: the lines every brief opens with."""
    lines = skeleton.split("\n")
    end = next(
        (at for at, line in enumerate(lines) if _HEADING.match(line)), len(lines)
    )
    return "\n".join(lines[:end])


def _items(text: str) -> list[list[str]]:
    """The list items of `text` outside fenced blocks. An item opens at a line that begins with
    "- " and runs to the next such line, a blank line or a heading; a line that continues it may be
    indented or sit in column 0."""
    items: list[list[str]] = []
    current: list[str] | None = None
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            current = None
        elif in_fence or not line.strip() or _HEADING.match(line):
            current = None
        elif line.startswith("- "):
            current = [line]
            items.append(current)
        elif current is not None:
            current.append(line)
    return items


def _labelled(text: str) -> list[list[str]]:
    """The bold-labelled lines of `text`, each with the lines that wrap it: one opens at a line
    that starts with a bold label and runs to a blank line, a heading or the next label."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if _LABEL.match(line):
            current = [line]
            blocks.append(current)
        elif current is not None and line.strip() and not _HEADING.match(line):
            current.append(line)
        else:
            current = None
    return blocks


def _item(text: str, lead: str) -> list[str]:
    """The lines of the first list item whose flat text opens with `lead`; empty when none does.
    An item that only contains the lead further on is not that item."""
    for lines in _items(text):
        if _flat("\n".join(lines)[2:]).startswith(lead):
            return lines
    return []


def _comment_run(fence: str, command: str) -> list[str]:
    """The run of comment lines directly above the first line that is `command`; empty when the
    command is absent or the line above it is no comment."""
    lines = fence.split("\n")
    at = next((n for n, line in enumerate(lines) if line.strip() == command), None)
    if at is None:
        return []
    start = at
    while start > 0 and lines[start - 1].startswith("#"):
        start -= 1
    return lines[start:at]


# --- the five places: each finder returns the lines of its block, or nothing ---------------------


def _revision_lines(template: str) -> list[str]:
    """The second bold-labelled line of the skeleton's opening, the first being the blocker line,
    when it carries the revision label."""
    blocks = _labelled(_opening(_fence(template)))
    if len(blocks) < 2 or not _flat(blocks[0][0]).startswith(_BLOCKER_LABEL):
        return []
    return blocks[1] if _flat(blocks[1][0]).startswith(_REVISION_LABEL) else []


def _broadcast_lines(template: str) -> list[str]:
    return _item(_section(template, _RULES), _BROADCAST[1][0])


def _read_budget_lines(template: str) -> list[str]:
    return _item(_section(_fence(template), _CONTEXT), _READ_BUDGET_LABEL)


def _gates_lines(agents: str) -> list[str]:
    return _comment_run(_fence(_section(agents, _COMMANDS)), _PUBLISH_CHECK)


def _wave_lines(agents: str) -> list[str]:
    return _item(_section(agents, _SUB_AGENTS), _WAVE_LEAD)


# (claim, the file it is read from, the finder of its block in that file's text)
_PLACES: tuple[tuple[Claim, Path, Finder], ...] = (
    (_REVISION, _TEMPLATE, _revision_lines),
    (_BROADCAST, _TEMPLATE, _broadcast_lines),
    (_READ_BUDGET, _TEMPLATE, _read_budget_lines),
    (_GATES, _AGENTS, _gates_lines),
    (_WAVE, _AGENTS, _wave_lines),
)
_IDS = [claim[0] for claim, _, _ in _PLACES]

# Each claim's planted move: the line its block is moved next to, outside its place, and whether
# the block goes after that line (True) or before it.
_MOVES: dict[str, tuple[str, bool]] = {
    "revision line": (_STANDING, True),
    "rule change sent": (_RULES_OF_THUMB, True),
    "read budget": (_DONE, True),
    "two gates": (_AUDIT, False),
    "wave width": (_DOCUMENTS, True),
}

# One word of each block, put in bold marks by the re-wrap near-miss.
_EMPHASIS: dict[str, str] = {
    "revision line": "machine",
    "rule change sent": "message",
    "read budget": "headings",
    "two gates": "push",
    "wave width": "tokens",
}


def _gaps(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _tail(sentence: str) -> str:
    """The last clause of a sentence: the words after its last comma, colon or semicolon, or its
    last three words when it has none."""
    parts = re.split(r"[,:;] ", sentence)
    return parts[-1] if len(parts) > 1 else " ".join(sentence.split()[-3:])


def _replaced(text: str, lines: list[str], new: list[str]) -> str:
    """`text` with the first run of rows equal to `lines` replaced by `new`."""
    rows = text.split("\n")
    at = next(n for n in range(len(rows)) if rows[n : n + len(lines)] == lines)
    return "\n".join(rows[:at] + new + rows[at + len(lines) :])


def _moved(text: str, lines: list[str], anchor: str, *, after: bool) -> str:
    """`text` with the block `lines` cut out and put back next to the first row that starts with
    `anchor`."""
    rows = _replaced(text, lines, []).split("\n")
    target = next(n for n, row in enumerate(rows) if row.startswith(anchor))
    where = target + 1 if after else target
    return "\n".join(rows[:where] + lines + rows[where:])


def _rewrap(lines: list[str], width: int) -> list[str]:
    """A block re-wrapped at `width` columns, whatever the file's own wrap: a list item keeps its
    "- " and indents the rest by two spaces, a comment run starts every row with "#", and a
    bold-labelled line indents the rest by two spaces."""
    comment = all(line.startswith("#") for line in lines)
    words = " ".join(line.lstrip("#") if comment else line for line in lines).split()
    if comment:
        first, rest = "#", "#"
    elif lines[0].startswith("- "):
        first, rest, words = "-", " ", words[1:]
    else:
        first, rest = "", " "
    rows: list[str] = []
    row = first
    for word in words:
        if row.strip("-# ") and len(row) + 1 + len(word) > width:
            rows.append(row)
            row = rest
        row = f"{row} {word}" if row else word
    rows.append(row)
    return rows


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_CLAIMS), len(_SENTENCES), len(_RETIRED)) == (5, 8, 1)
    assert len(_PLACES) == 5 and [place[0] for place in _PLACES] == list(_CLAIMS)
    files = [path for _, path, _ in _PLACES]
    assert (len(set(files)), files.count(_TEMPLATE), files.count(_AGENTS)) == (2, 3, 2)
    assert sorted(_MOVES) == sorted(_IDS) and sorted(_EMPHASIS) == sorted(_IDS)
    assert len(set(_SENTENCES)) == len(_SENTENCES), "a sentence is listed twice"
    for sentence in _SENTENCES:
        others = [other for other in _SENTENCES if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
        assert not any(retired in sentence for retired in _RETIRED), sentence
    for path in (_TEMPLATE, _AGENTS):
        assert path.is_file(), f"{path} is not a file"
        assert _read(path).strip(), f"{path.name} is empty"


def test_the_places_are_disjoint_by_line() -> None:
    """Two surfaces in each file, asserted disjoint: in the template the opening and the Context
    section lie inside the skeleton, one after the other, and the rules section comes after the
    skeleton's closing fence; in AGENTS.md the Commands section ends before the sub-agents section
    starts. A line in two places would be judged by a rule that does not apply to it."""
    lines = _read(_TEMPLATE).split("\n")
    fence_start, fence_end = _fence_span(lines)
    assert fence_start < fence_end, "the template has no closed skeleton"
    skeleton = lines[fence_start:fence_end]
    opening_end = next(n for n, line in enumerate(skeleton) if _HEADING.match(line))
    context_start, context_end = _section_span(skeleton, _CONTEXT)
    assert 0 < opening_end <= context_start < context_end
    rules_start, rules_end = _section_span(lines, _RULES)
    assert fence_end < rules_start < rules_end
    agents = _read(_AGENTS).split("\n")
    commands_start, commands_end = _section_span(agents, _COMMANDS)
    sub_agents_start, sub_agents_end = _section_span(agents, _SUB_AGENTS)
    assert commands_start < commands_end <= sub_agents_start < sub_agents_end


# --- the claims --------------------------------------------------------------------------------


@pytest.mark.parametrize(("claim", "path", "finder"), _PLACES, ids=_IDS)
def test_the_claim_holds_in_its_place(claim: Claim, path: Path, finder: Finder) -> None:
    """Red before the change: no block said this."""
    name, sentences = claim
    lines = finder(_read(path))
    assert lines, f"{name}: {path.name} has no block in the place the claim belongs"
    missing = _gaps(_flat_block(lines), sentences)
    assert not missing, f"{name}: the block does not state {missing}"


def test_the_wave_sentence_closes_its_bullet_and_the_old_words_are_gone() -> None:
    """Red before the change: the bullet ended with the sentence that named only the disk and the
    machine. ONE sentence in the same place: the new sentence is the bullet's last, and the retired
    words are in no part of the file."""
    agents = _read(_AGENTS)
    bullet = _flat_block(_wave_lines(agents))
    assert bullet, "the checkpoint bullet is missing from its section"
    assert bullet.endswith(_WAVE[1][0]), (
        "the checkpoint bullet does not end with the sentence"
    )
    for retired in _RETIRED:
        assert retired not in _flat_file(agents), f"AGENTS.md still says {retired!r}"


def test_every_sentence_has_one_home_in_its_file() -> None:
    """Each sentence occurs once in the whole of its file, so no second copy can drift from it."""
    for (name, sentences), path, _ in _PLACES:
        flat = _flat_file(_read(path))
        for sentence in sentences:
            assert flat.count(sentence) == 1, (
                f"{name}: {sentence!r} occurs {flat.count(sentence)} times in {path.name}"
            )


# --- the checks can fail -----------------------------------------------------------------------


@pytest.mark.parametrize(("claim", "path", "finder"), _PLACES, ids=_IDS)
def test_every_sentence_occurs_once_and_is_reported_when_it_goes(
    claim: Claim, path: Path, finder: Finder
) -> None:
    """Planted removal: each sentence cut out of its real block is the one gap reported, and an
    empty block lacks every sentence."""
    name, sentences = claim
    block = _flat_block(finder(_read(path)))
    assert _gaps(block, sentences) == [], f"{name}: a sentence is missing at the start"
    for sentence in sentences:
        assert block.count(sentence) == 1, (
            f"{name}: {sentence!r} occurs {block.count(sentence)} times"
        )
        assert _gaps(block.replace(sentence, ""), sentences) == [sentence], sentence
    assert _gaps("", sentences) == list(sentences)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the last clause of each sentence (after its last comma, colon or
    semicolon, or its last three words) is cut out of the real block, and the claim then reports
    exactly that sentence. A check on a fragment of the sentence would stay green."""
    cut = 0
    for (name, sentences), path, finder in _PLACES:
        block = _flat_block(finder(_read(path)))
        assert not _gaps(block, sentences), (
            f"{name}: a sentence is missing at the start"
        )
        for sentence in sentences:
            tail = _tail(sentence)
            assert tail != sentence, f"no clause to cut from {sentence!r}"
            assert block.count(tail) == 1, (
                f"{name}: {tail!r} is not a clause of one sentence"
            )
            assert _gaps(block.replace(tail, ""), sentences) == [sentence], (
                name,
                sentence,
            )
            cut += 1
    assert cut == len(_SENTENCES)


@pytest.mark.parametrize(("claim", "path", "finder"), _PLACES, ids=_IDS)
def test_the_claim_is_judged_in_its_own_place(
    claim: Claim, path: Path, finder: Finder
) -> None:
    """Planted move: the block cut out of its place and put next to a line outside it leaves a
    place without the block, while a search of the whole file still finds every sentence. That
    search would have passed, which is why each claim is read from its own place."""
    name, sentences = claim
    text = _read(path)
    lines = finder(text)
    assert lines, f"{name}: the block to move is not in its place"
    anchor, after = _MOVES[name]
    moved = _moved(text, lines, anchor, after=after)
    assert moved != text, f"{name}: the planted move changed nothing"
    assert finder(moved) == [], f"{name}: the block was still found in its place"
    assert _gaps(_flat_file(moved), sentences) == [], (
        f"{name}: the planted text lost a sentence, so the move proves nothing"
    )


def test_the_old_text_fails_every_pin() -> None:
    """Known positives: the opening, the comment and the bullet as they stood before, and the real
    file with the retired sentence planted back. Each is reported."""
    assert _revision_lines(_OLD_OPENING) == []
    planted = _OLD_OPENING.replace(
        "\n\n## Standing",
        f"\n**Revision:** {_REVISION[1][0].split(': ', 1)[1]}\n\n## Standing",
    )
    assert _flat_block(_revision_lines(planted)) == _REVISION[1][0], planted
    gates = _comment_run(_OLD_COMMANDS, _PUBLISH_CHECK)
    assert len(gates) == 5, gates
    assert _gaps(_flat_block(gates), _GATES[1]) == list(_GATES[1])
    old = _item(_OLD_WAVE_BULLET, _WAVE_LEAD)
    assert old, "the finder does not see the old bullet"
    flat = _flat_block(old)
    assert _gaps(flat, _WAVE[1]) == list(_WAVE[1]) and not flat.endswith(_WAVE[1][0])
    assert all(retired in flat for retired in _RETIRED)
    agents = _read(_AGENTS)
    lines = _wave_lines(agents)
    assert lines, "the checkpoint bullet is missing from its section"
    again = [*lines, "  A wave is as wide as the disk and the machine allow."]
    restored = _flat_file(_replaced(agents, lines, again))
    assert all(retired in restored for retired in _RETIRED)


@pytest.mark.parametrize("width", [40, 72, 100])
@pytest.mark.parametrize(("claim", "path", "finder"), _PLACES, ids=_IDS)
def test_a_rewrapped_and_reemphasised_block_still_holds_its_claim(
    claim: Claim, path: Path, finder: Finder, width: int
) -> None:
    """Near-miss that must NOT be reported: the real block re-wrapped at `width` columns, so that
    a sentence breaks over other lines, and one word of it put in bold marks, is the same text."""
    name, sentences = claim
    text = _read(path)
    lines = finder(text)
    assert lines, f"{name}: the block is not in its place"
    assert not _gaps(_flat_block(lines), sentences), f"{name}: a sentence is missing"
    word = _EMPHASIS[name]
    wrapped = [row.replace(word, f"**{word}**", 1) for row in _rewrap(lines, width)]
    assert any(f"**{word}**" in row for row in wrapped), (
        f"{name}: no word was emphasised"
    )
    reshaped = _replaced(text, lines, wrapped)
    assert reshaped != text, f"{name}: the re-wrap changed nothing"
    assert not _gaps(_flat_block(finder(reshaped)), sentences), (name, width)


# --- the finders --------------------------------------------------------------------------------


_FIXTURE = "\n".join(
    [
        "# Title",
        "",
        "**First label:** one",
        "**Second label:** two",
        "  wrapped two",
        "",
        "## Commands",
        "",
        "```bash",
        "# a comment that is no heading",
        "# its second line",
        "run a",
        "",
        "run b",
        "```",
        "",
        "- **An item.** One",
        "  wrapped in.",
        "- Another item",
        "",
        "Not an item.",
        "",
        "## Next",
        "after",
        "",
    ]
)


def test_the_finders_keep_their_edges() -> None:
    """A section stops at the next heading of its level and keeps a `#` line inside a fence; a
    comment run is the comment lines right above a command, and nothing for a command with a blank
    line above it or for one that is absent; a labelled line runs to a blank line or the next
    label; an item runs to the next item or a blank line; and an absent heading, fence or lead
    finds nothing, so a missing place is reported and never read as an empty pass."""
    commands = _section(_FIXTURE, "## Commands")
    assert commands.startswith("## Commands") and "# its second line" in commands
    assert "Not an item." in commands and "after" not in commands
    fence = _fence(commands)
    assert _comment_run(fence, "run a") == [
        "# a comment that is no heading",
        "# its second line",
    ]
    assert _comment_run(fence, "run b") == []
    assert _comment_run(fence, "run c") == []
    assert _labelled(_FIXTURE) == [
        ["**First label:** one"],
        ["**Second label:** two", "  wrapped two"],
    ]
    assert _item(commands, "an item.") == ["- **An item.** One", "  wrapped in."]
    assert _item(commands, "another item") == ["- Another item"]
    assert _item(commands, "not an item.") == []
    assert _item(commands, "wrapped in.") == []
    assert _section(_FIXTURE, "## Absent") == "" and _fence("no fence\n") == ""
    assert _opening("**A:** b\n\n## Heading\nbody") == "**A:** b\n"
    assert _flat_block(["# a", "# b"]) == "a b"
    assert _flat_block(["- **A** b", "  c"]) == "a b c"
