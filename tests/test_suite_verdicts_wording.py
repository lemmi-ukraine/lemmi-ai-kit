"""parallel-session-safety says a suite verdict is void when child processes failed to start.

Section 6 of the skill voids a verdict that was taken over a tree other sessions were editing, and
says nothing of the machine. A suite run beside a loop of verifiers or other suites lost many tests
to child processes that failed to start, none of them reached an assertion, and the run took
several times its usual time: the tree stood still and the verdict still measured the machine. The
skill is at its line cap, so the rule lives in a new reference,
`parallel-session-safety/references/suite-verdicts.md`, with four bullets (no verdict from a run
whose child processes failed to start; read a run's time before its count; rerun on a quiet
machine, with a wait bound labelled uncalibrated after which the verdict stays UNKNOWN; cap the
concurrent gate runs, with a starting value that is labelled uncalibrated). The pointer from the
skill is the release owner's: this file does not look for it.

A cold read found that the quiet-machine rule could not be followed to its end: it defined quiet as
no other suite, gate run, verifier loop or mutation loop, then told the agent to start the rerun
only when no other interpreter process ran, and an editor's language server or a tool server is an
interpreter process that never exits, so a literal agent waited for good. The start condition now
names the same four kinds as the definition, the wait is bounded (starting value, uncalibrated), and
the term "gate runner", which the kit defines nowhere, is "gate run" in both places it was used.

THE SURFACE, in numbers the tests assert: 1 place in 1 new file, 16 sentences in 4 bullets and an
opening paragraph, each held whole (lower-cased, bold marks dropped, whitespace collapsed) so that
a clause cannot be dropped while the rest of its sentence still matches. Each sentence occurs once
and is fired at a planted removal and a planted cut of its last clause; the reference is fired at
text that says nothing; the section it names resolves; it does not repeat what section 6 says; it
prints no command; and it is scanned for an id, a path and a commit id, with a planted control for
each. A project's or a company's own name is not scanned for here: it has no generic shape, and
naming one in a test would publish it, so that part stays a reading check.
"""

import re
import textwrap
from pathlib import Path

import pytest

_SKILL_DIR = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "parallel-session-safety"
)
_SKILL_MD = _SKILL_DIR / "SKILL.md"
_REFERENCE = _SKILL_DIR / "references" / "suite-verdicts.md"
_HEADING = re.compile(r"^(#{1,6})\s")


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


_TITLE = "# A suite verdict is void when child processes failed to start"

# The sentences, whole, in order: lower-cased, bold marks dropped, whitespace collapsed. A bold
# lead that opens a bullet is a sentence of its own.
_SENTENCES: tuple[str, ...] = (
    "read this before you report a test-suite or gate verdict from a machine that other work "
    "was also loading, and whenever a run's failures name a process that did not start.",
    "section 6 of the skill covers a verdict taken over a tree that others were editing.",
    "this is its twin for the machine: the tree can stand still and the verdict can still be "
    "wrong.",
    "a run in which child processes failed to start has no verdict.",
    "a test that never reached its assertion measured the machine, not the code.",
    "count start errors apart from assertion failures and report the run as unknown: it is "
    "neither a pass nor a regression (observed once: a suite lost many tests to start errors, "
    "and none of them reached an assertion).",
    "read the run's time before its count.",
    "a suite that takes several times its usual time was competing for the machine (observed "
    "once: a full run took several times as long, with the processor saturated by dozens of "
    "interpreter processes).",
    "rerun on a quiet machine.",
    "quiet means no other gate run, suite, verifier loop or mutation loop is running.",
    "list the running interpreter processes with the platform's process lister before the "
    "rerun, and start it only when none of them is another gate run, suite, verifier loop or "
    "mutation loop.",
    "if such a process still runs after 30 minutes (starting value, uncalibrated), start no "
    "rerun, report the verdict unknown with the list of those processes, and stop waiting.",
    "otherwise report both runs: the void one with its cause, and the rerun.",
    "cap the concurrent gate runs.",
    "starting value, uncalibrated: one gate run on the machine at a time.",
    "run gates between waves of workers, not inside one, because a wave of verifiers and a "
    "suite compete for the same processes.",
)
_LEADS = (
    "a run in which child processes failed to start has no verdict.",
    "read the run's time before its count.",
    "rerun on a quiet machine.",
    "cap the concurrent gate runs.",
)

# A reference that exists and says nothing: its title, one line, one bullet.
_STUB_REFERENCE = f"{_TITLE}\n\nRead this.\n\n- **A rule.** Be careful.\n"


def _gaps_in(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _gaps(text: str) -> list[str]:
    if not text.strip():
        raise AssertionError("suite-verdicts.md is empty")
    return _gaps_in(_flat(text), _SENTENCES)


def _has_clause(sentence: str) -> bool:
    return re.search(r"[,:] ", sentence) is not None


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    """1 place, 16 sentences and 4 bullets; no sentence stands twice or inside another; the four
    leads are four of the sentences."""
    assert len(_SENTENCES) == 16
    assert len(set(_SENTENCES)) == len(_SENTENCES)
    for sentence in _SENTENCES:
        others = [s for s in _SENTENCES if s != sentence]
        assert not any(sentence in other for other in others), sentence
    assert all(s == s.lower() for s in _SENTENCES)
    assert len(_LEADS) == 4 and all(lead in _SENTENCES for lead in _LEADS)


def test_the_reference_states_its_sentences() -> None:
    """Red before the change: the reference did not exist."""
    assert _gaps(_read(_REFERENCE)) == []


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of the real reference is the one gap reported, and
    an empty text lacks every sentence. A sentence that occurred twice would let a clause go and
    stay green."""
    flat = _flat(_read(_REFERENCE))
    assert _gaps_in(flat, _SENTENCES) == []
    for sentence in _SENTENCES:
        assert flat.count(sentence) == 1, (
            f"{sentence!r} occurs {flat.count(sentence)} times"
        )
        assert _gaps_in(flat.replace(sentence, ""), _SENTENCES) == [sentence]
    assert _gaps_in("", _SENTENCES) == list(_SENTENCES)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the words after the last comma or colon of a sentence are cut out
    of the real reference, and it then reports exactly that sentence. A check on a fragment of
    the sentence would stay green."""
    flat = _flat(_read(_REFERENCE))
    cut = 0
    for sentence in _SENTENCES:
        if not _has_clause(sentence):
            continue
        tail = re.split(r"[,:] ", sentence)[-1]
        cut += 1
        assert flat.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
        assert _gaps_in(flat.replace(tail, ""), _SENTENCES) == [sentence], sentence
    assert cut == sum(_has_clause(s) for s in _SENTENCES) > 0


def test_the_reference_as_it_would_be_without_the_rule_reports_every_sentence() -> None:
    """Known positive: a reference that exists and says nothing lacks every sentence, so a red on
    it is a red for the text and not for a broken helper."""
    assert _gaps(_STUB_REFERENCE) == list(_SENTENCES)


def test_a_missing_or_empty_reference_fails_loudly() -> None:
    """A reference that is not there and one that is empty are each reported by name and never
    read as an empty pass."""
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-reference.md"))
    with pytest.raises(AssertionError, match="is empty"):
        _gaps("  \n")


@pytest.mark.parametrize("width", [40, 72, 100])
def test_a_rewrapped_and_reemphasised_reference_still_holds_its_claims(
    width: int,
) -> None:
    """Near-miss that must NOT be reported: the real reference filled again at `width` columns,
    with bold marks around one more word, is the same text."""
    filled = textwrap.fill(
        " ".join(_read(_REFERENCE).split()),
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    reshaped = filled.replace(" a ", " **a** ", 1)
    assert "**a**" in reshaped, "the planted emphasis changed nothing"
    assert _gaps(reshaped) == []


# --- where the text sits -----------------------------------------------------------------------


def test_the_reference_opens_with_when_to_read_it_and_holds_four_bullets_in_order() -> (
    None
):
    """A new reference opens with one line saying when to read it, then holds the four rules in
    order. Each of the two starting values (the wait bound of the third rule and the cap of the
    fourth) is labelled once, and the two observed facts are tagged once each."""
    text = _read(_REFERENCE)
    assert text.split("\n")[0] == _TITLE
    assert _flat(text.split("\n\n")[1]).startswith("read this before you ")
    bullets = _bullets(text)
    assert len(bullets) == len(_LEADS), len(bullets)
    for bullet, lead in zip(bullets, _LEADS, strict=True):
        assert bullet.startswith(lead), (lead, bullet[:60])
    assert [b.count("(observed once") for b in bullets] == [1, 1, 0, 0]
    assert [b.count("starting value, uncalibrated") for b in bullets] == [0, 0, 1, 1]


def test_the_section_it_names_is_the_torn_tree_section_and_is_not_repeated() -> None:
    """The reference names "section 6" of the skill: that heading exists and is about the verdict
    over a contended tree. The reference extends it, so section 6 does not already say it: it has
    no word about child processes."""
    section = _section(_read(_SKILL_MD), "## 6.", "SKILL.md")
    lines = section.split("\n")
    assert "suite verdict" in _flat(lines[0]), lines[0]
    # A line that points at the reference may name the cause in its own words; it is not a repeat.
    body = [line for line in lines if "suite-verdicts.md" not in line]
    assert "child process" not in _flat("\n".join(body)), "section 6 already says it"


def test_the_reference_prints_no_command() -> None:
    """No command was run for this text, so it prints none: no fenced block and no code span. A
    command added later has to be run first, and has to change this test on purpose."""
    text = _read(_REFERENCE)
    assert "`" not in text
    for planted in ("```bash\nls\n```", "run `ls` first"):
        assert "`" in planted


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


def test_the_reference_names_no_id_path_or_commit() -> None:
    """The kit is public. The reference carries none of the shapes."""
    assert _leaks(_read(_REFERENCE)) == []


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
        "section 6 of the skill, and a run that took several times as long",
        "a defaced page, an effaced line and the word accede",
        "the 3 suites and 12 lines it names",
    ):
        assert _leaks(clean) == [], clean


def test_the_section_and_item_finders_keep_their_edges() -> None:
    """The finders keep a deeper heading and a `#` line inside a fence, stop at the next heading of
    their level, take no line inside a fence for a list item, and find nothing for an absent
    heading."""
    planted = "\n".join(
        [
            "## 6. First",
            "first body",
            "### deeper",
            "deeper body",
            "```bash",
            "## not a heading inside a fence",
            "- not an item inside a fence",
            "```",
            "## 7. Second",
            "second body",
            "",
        ]
    )
    first = _section(planted, "## 6.", "planted")
    assert "deeper body" in first and "not a heading" in first
    assert "second body" not in first
    with pytest.raises(AssertionError, match="no heading starting"):
        _section(planted, "## 8.", "planted")
    assert [len(i) for i in _item_lines(planted)] == []
    assert len(_item_lines("lead\n- one\n  more\n```\n- fenced\n```\n- two\n")) == 2
