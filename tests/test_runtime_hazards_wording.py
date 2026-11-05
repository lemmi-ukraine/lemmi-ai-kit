"""agent-delegate names the four ways a scripted run loses or doubles work.

The orchestration text described how to dispatch and resume a worker and said nothing about the
failure modes of a scripted run (a workflow: the harness feature that runs scripted sub-agents and
keeps a journal of what each stage returned). Each of four was learned by a loss. A message to a
sub-agent that a workflow was still running started a second live copy of it. A resume id works
only in the session that ran the workflow, so a stage handed to another session by id had nothing
to resume. A sub-agent that ended its turn to wait for a background run was not woken when the run
finished. A verifier stage that returned no commit id was skipped without an error.

A cold read found that the third bullet and the limit-recovery reference of `orchestrate` seemed
to contradict each other (one said a background run's notice wakes a turn that has ended, the other
that it did not), told apart only by "worker" and "session", and that its wait had no bound: a run
that hung held the sub-agent for good. The bullet now says "sub-agent", bounds the wait by a time
limit (the brief's, else the sub-agent's own), and has the sub-agent say which of the two ended it;
the limit-recovery reference says the waiter is a session's and points here.

`agent-delegate/references/runtime-hazards.md` now holds the four as four bullets and says what a
workflow is in one clause, in neutral words. `agent-delegate/SKILL.md` points at it from one line
directly under the heading of its last section, "Resuming a worker": the pointer is not a fourth
bullet, because the tests of that section hold it to three, and the section stays the last one.

THE SURFACE, in numbers the tests assert: 2 places in 2 files (the whole reference, and the line
under the heading of the skill's last section) and 16 sentences, each held whole (lower-cased, bold
marks dropped, whitespace collapsed) so that a clause cannot be dropped while the rest of its
sentence still matches; 4 bullets, each carrying its evidence tag once. Each sentence occurs once
in its place and is fired at a planted removal and a planted cut of its last clause; each place
is fired at the text it replaced; a planted move shows the pointer is judged under its heading and
not anywhere in the file; and the added text is scanned for an id, a path, a commit id and a tool's
own parameter name, with a planted control for each. A project's or a company's own name is not
scanned for here: it has no generic shape, and naming one in a test would publish it, so that part
stays a reading check.
"""

import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILL_DIR = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "agent-delegate"
)
_SKILL_MD = _SKILL_DIR / "SKILL.md"
_REFERENCE = _SKILL_DIR / "references" / "runtime-hazards.md"
_HEADING = re.compile(r"^(#{1,6})\s")
_RESUMING = "## Resuming a worker"
_BOLD_LEAD = re.compile(r"^-\s+\*\*(.+?)\*\*")


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


def _item_lines(text: str) -> list[list[str]]:
    """The lines of every list item: an item opens at a line that starts with "- " outside a
    fenced block and runs to the next such line or to the end."""
    items: list[list[str]] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("- "):
            items.append([line])
        elif items:
            items[-1].append(line)
    return items


def _bullets(text: str) -> list[str]:
    """The flat text of each list item, past its marker."""
    return [_flat("\n".join(lines)[2:]) for lines in _item_lines(text)]


def _whole_reference(text: str, where: str) -> str:
    if not text.strip():
        raise AssertionError(f"{where} is empty")
    return text


def _pointer_region(text: str, where: str) -> str:
    """The lines of the last section between its heading and its first bullet."""
    region: list[str] = []
    for line in _section(text, _RESUMING, where).split("\n"):
        if line.startswith("- "):
            break
        region.append(line)
    return "\n".join(region)


_REFERENCE_SENTENCES: tuple[str, ...] = (
    "read this before you message a sub-agent that a scripted run is driving, hand a stage of "
    "such a run to another session, let a worker wait on a background run, or trust a run's "
    "final summary.",
    "a workflow here is the harness feature that runs scripted sub-agents and keeps a journal "
    "of what each stage returned.",
    "never message a running workflow agent.",
    "a message to a sub-agent that a workflow was still running started a second live copy of "
    "it, so two writers worked at once (observed once).",
    "to change course, let the run return and brief again.",
    'a sub-agent that has stopped is a different case: the bullets of the "resuming a worker" '
    "section of the skill cover it.",
    "hand a last stage over as a standalone script with its arguments, never a resume id.",
    "a resume id works only in the session that ran the workflow, so a stage handed to another "
    "session by id has nothing to resume (observed once).",
    "write the stage as a script that takes what it needs (the commit, the paths, the report "
    "folder) as arguments.",
    "a sub-agent stays in its turn while its background run finishes.",
    "a sub-agent that ended its turn to wait for a background run was not woken when the run "
    "finished (observed once).",
    "it waits inside its turn, with a command that exits when the run does or at a time limit "
    "(its brief's, else its own), and returns either way, saying which.",
    "check the journal for a stage that returned no commit id.",
    "a verifier stage that returned no commit id was skipped without an error, so nothing "
    "flagged it (observed once).",
    "after every run, read the journal for each stage and list any that returned none, then "
    "run the missing stage as a standalone script, as the second bullet says.",
)
_POINTER_SENTENCES: tuple[str, ...] = (
    "a scripted run (a workflow) has hazards of its own that a stopped worker does not: read "
    "[runtime hazards](references/runtime-hazards.md) before you message, resume or trust one.",
)
_LEADS = (
    "never message a running workflow agent.",
    "hand a last stage over as a standalone script with its arguments, never a resume id.",
    "a sub-agent stays in its turn while its background run finishes.",
    "check the journal for a stage that returned no commit id.",
)
_SECTION_LEADS = (
    "After a usage limit.",
    "Near the context window.",
    "After a refusal by the platform.",
)

# The skill's last section as it stood: its heading and its three bullets, each shortened to its
# first lines. The lines that remain are unedited.
_OLD_RESUMING = """\
# Agent Delegate

## Resuming a worker

- **After a usage limit.** A sub-agent that a usage limit stopped can be resumed with `SendMessage`
  once requests are accepted again.
- **Near the context window.** Do not resume a session that ended near its window: the resume
  compacts almost at once.
- **After a refusal by the platform.** A sub-agent can be refused mid-run by an organization-policy
  error while its parent session keeps working.
"""
# A reference that exists and says nothing: its heading, one line, one bullet.
_STUB_REFERENCE = (
    "# Runtime hazards of a scripted run\n\nRead this.\n\n- **A hazard.** Be careful.\n"
)


class _Place(NamedTuple):
    name: str
    path: Path
    locate: Callable[[str, str], str]
    sentences: tuple[str, ...]
    old: str


_PLACES: tuple[_Place, ...] = (
    _Place(
        "reference",
        _REFERENCE,
        _whole_reference,
        _REFERENCE_SENTENCES,
        _STUB_REFERENCE,
    ),
    _Place(
        "skill-pointer",
        _SKILL_MD,
        _pointer_region,
        _POINTER_SENTENCES,
        _OLD_RESUMING,
    ),
)


def _gaps_in(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _gaps(place: _Place, text: str) -> list[str]:
    return _gaps_in(_flat(place.locate(text, place.path.name)), place.sentences)


def _real(place: _Place) -> str:
    return _read(place.path)


def _has_clause(sentence: str) -> bool:
    return re.search(r"[,:] ", sentence) is not None


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    """2 places in 2 files, 16 sentences and 4 bullets; no sentence stands twice or inside another."""
    assert len(_PLACES) == 2
    assert len({p.path for p in _PLACES}) == 2
    assert sum(len(p.sentences) for p in _PLACES) == 16
    assert len(_LEADS) == 4
    for place in _PLACES:
        assert len(set(place.sentences)) == len(place.sentences), place.name
        for sentence in place.sentences:
            others = [s for s in place.sentences if s != sentence]
            assert not any(sentence in other for other in others), (
                place.name,
                sentence,
            )
        assert all(s == s.lower() for s in place.sentences), place.name
    assert all(lead in _REFERENCE_SENTENCES for lead in _LEADS)


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_states_its_sentences(place: _Place) -> None:
    """Red before the change: the reference did not exist and the section had no such line."""
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


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the words after the last comma or colon of a sentence are cut out
    of the real reference, and it then reports exactly that sentence. The pointer has one colon
    and is cut the same way."""
    for place in _PLACES:
        flat = _flat(place.locate(_real(place), place.path.name))
        cut = 0
        for sentence in place.sentences:
            if not _has_clause(sentence):
                continue
            tail = re.split(r"[,:] ", sentence)[-1]
            cut += 1
            assert flat.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
            assert _gaps_in(flat.replace(tail, ""), place.sentences) == [sentence], (
                sentence
            )
        assert cut == sum(_has_clause(s) for s in place.sentences) > 0, place.name


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_place_reports_the_text_it_replaced(place: _Place) -> None:
    """Known positive: a reference that says nothing, and the section as it stood, lack every
    sentence, so a red on the old text is a red for the text and not for a broken helper."""
    assert _gaps(place, place.old) == list(place.sentences)


def test_a_missing_file_or_heading_fails_loudly() -> None:
    """A reference that is not there, an empty one and a skill without its last section are
    each reported by name and never read as an empty pass."""
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-reference.md"))
    with pytest.raises(AssertionError, match="is empty"):
        _whole_reference("  \n", "runtime-hazards.md")
    with pytest.raises(AssertionError, match="no heading starting"):
        _pointer_region("# Agent Delegate\n\n## Other\n\ntext\n", "SKILL.md")


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
    reshaped = filled.replace(" a ", " **a** ", 1)
    assert "**a**" in reshaped, "the planted emphasis changed nothing"
    assert _gaps_in(_flat(reshaped), place.sentences) == []


def test_the_pointer_is_judged_under_its_heading_only() -> None:
    """Planted move: the pointer line cut out from under the heading and put after the last line
    of the file is a section that lacks it. A search of the whole file would still find it."""
    place = _PLACES[1]
    text = _real(place)
    region = place.locate(text, place.path.name)
    line = region.strip().split("\n")
    pointer = "\n".join(line[1:]).strip()
    assert pointer, "no pointer to move"
    moved = text.replace(pointer, "", 1) + "\n" + pointer + "\n"
    assert _gaps(place, moved) == list(place.sentences)
    assert _gaps_in(_flat(moved), place.sentences) == [], (
        "a whole-file search would have passed"
    )


# --- where the text sits -----------------------------------------------------------------------


def test_the_reference_opens_with_when_to_read_it_and_holds_four_bullets_in_order() -> (
    None
):
    """A new reference opens with one line saying when to read it, defines a workflow in the same
    opening paragraph, and then holds the four hazards, each with its evidence tag once. The
    last bullet says "the second bullet", so the second bullet has to be the one about a resume id."""
    text = _read(_REFERENCE)
    lines = text.split("\n")
    assert lines[0] == "# Runtime hazards of a scripted run"
    opening = _flat(text.split("\n\n")[1])
    assert opening.startswith("read this before you "), opening
    assert "a workflow here is the harness feature" in opening
    bullets = _bullets(text)
    assert len(bullets) == len(_LEADS), len(bullets)
    for bullet, lead in zip(bullets, _LEADS, strict=True):
        assert bullet.startswith(lead), (lead, bullet[:60])
        assert bullet.count("(observed once)") == 1, lead
    assert "never a resume id" in bullets[1], (
        "the second bullet is not the resume-id one"
    )
    assert "as the second bullet says" in bullets[3]


def test_the_skill_keeps_its_three_bullets_and_its_last_heading() -> None:
    """The pointer is a line under the heading, not a fourth bullet, and "Resuming a worker" is
    still the last heading of the skill. The link resolves to the reference in the same folder."""
    text = _read(_SKILL_MD)
    section = _section(text, _RESUMING, "SKILL.md")
    leads: list[str] = []
    for lines in _item_lines(section):
        found = _BOLD_LEAD.match(" ".join(" ".join(lines).split()))
        assert found is not None, lines[0]
        leads.append(found[1])
    assert tuple(leads) == _SECTION_LEADS, leads
    headings = [line for line in text.split("\n") if _HEADING.match(line)]
    assert headings[-1] == _RESUMING, headings[-1]
    assert (_SKILL_DIR / "references" / "runtime-hazards.md").is_file()
    assert text.count("(references/runtime-hazards.md)") == 1


def test_the_bullet_that_names_the_section_names_a_real_one() -> None:
    """The first bullet sends the reader to the "Resuming a worker" section, and the skill has it."""
    assert f"\n{_RESUMING}\n" in _read(_SKILL_MD)
    assert '"resuming a worker" section of the skill' in _flat(_read(_REFERENCE))


# --- the added text is neutral -----------------------------------------------------------------

# The shapes are generic, so the scan names no project.
_LEAKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a request id", re.compile(r"\b[A-Z]{1,4}-\d{1,3}\b")),
    # One group for the home paths: the publication-hygiene test forbids the spelled-out
    # literal in every tracked file, this one included.
    ("an absolute local path", re.compile(r"(?:\b[A-Za-z]:[\\/]|/(?:Users|home)/)")),
    ("a commit-id-like token", re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")),
    ("a camelCase tool or parameter name", re.compile(r"\b[a-z]+[A-Z][A-Za-z]*\b")),
)


def _leaks(text: str) -> list[str]:
    return [label for label, pattern in _LEAKS if pattern.search(text)]


def test_the_added_text_names_no_id_path_commit_or_parameter() -> None:
    """The kit is public, and the workflow is described in neutral words. The reference and the
    pointer carry none of the shapes."""
    for place in _PLACES:
        region = place.locate(_real(place), place.path.name)
        assert _leaks(region) == [], place.name


def test_the_leak_scan_sees_each_shape_and_spares_the_near_misses() -> None:
    """Known positives, one per shape, and near-misses that must stay clean."""
    planted = {
        "a request id": "see " + "K" + "-8 for the reason",
        "an absolute local path": "read " + "C:" + "/Us" + "ers/someone/notes.md",
        "a commit-id-like token": "as of commit " + "0a1b2c3d4e",
        "a camelCase tool or parameter name": "pass " + "resume" + "From" + "RunId",
    }
    assert set(planted) == {label for label, _ in _LEAKS}
    for label, text in planted.items():
        assert _leaks(text) == [label], (label, _leaks(text))
    for clean in (
        "a stage handed over as a standalone script with its arguments, never a resume id",
        "SendMessage and the sub-agent, a defaced page and an effaced line",
        "the 3 stages and 12 lines it names",
    ):
        assert _leaks(clean) == [], clean


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder keeps a deeper heading and a `#` line inside a fence, stops at the next heading
    of its level, and finds nothing for a heading that is not there."""
    planted = "\n".join(
        [
            "## First",
            "first body",
            "### deeper",
            "deeper body",
            "```bash",
            "## not a heading inside a fence",
            "```",
            "## Second",
            "second body",
            "",
        ]
    )
    first = _section(planted, "## First", "planted")
    assert "deeper body" in first and "not a heading" in first
    assert "second body" not in first
    with pytest.raises(AssertionError, match="no heading starting"):
        _section(planted, "## Absent", "planted")
    items = _item_lines("lead\n- one\n  more\n```\n- fenced\n```\n- two\n")
    assert [len(i) for i in items] == [5, 2], items


def test_the_reference_prints_no_command() -> None:
    """No command was run for this text, so it prints none: no fenced block and no code span. A
    command added later has to be run first, and has to change this test on purpose."""
    assert "`" not in _read(_REFERENCE)
    for planted in ("```bash\nls\n```", "run `ls` first"):
        assert "`" in planted
