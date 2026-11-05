"""How an orchestrator verifies the Verification commands of a returned note is written down as a recipe.

`orchestrate` said a worker's summary is a claim and to run the brief's definition-of-done check, and
the support CLI lists a note's commands without running them. Between the two nothing said how to
turn that list into a verified result: which commands are run, which are only observed, which
cannot be re-run and need a stated reason; where each result is kept; that the report line is
computed from those results and not typed; what breaks when a table's separator can occur inside a
command; where a checking script gets the project root; how a long check runs beside peers that
write; and that a clean census proves nothing until a planted gap has been found. The recipe lives
in `orchestrate/references/return-note-verification.md`, reached by one pointer line in section 3
of `SKILL.md`. It is a recipe only: the kit ships no runner for it.

THE SURFACE, in numbers the tests assert: 1 reference judged by 11 claims (one per numbered point
and the three around them) and 30 phrases (a claim holds when every one of its phrases is in the
reference, lower-cased, whitespace collapsed); 1 pointer line in section 3, fired at 5 planted
shapes (absent, dead, before the passage it follows, in a later paragraph, twice); 1 hygiene scan
reused from `test_assets.py` (its patterns, over the reference, which must be inside that scan's
file list), fired at 4 planted shapes and 2 near-misses; 1 link check and 1 code-span check (the
hand-off lint's printed form belongs to one place, and a code span that opens with the subcommand
would be parsed as a printed command), fired at planted spans and near-misses. Each phrase is
fired at a planted removal, so a phrase the check could not see go is not in the table. A missing
reference reads as empty text, so every claim fails by name and not by an exception.
"""

import re
from pathlib import Path

import pytest
from test_assets import (
    _FORBIDDEN as _ASSET_FORBIDDEN,  # pyright: ignore[reportPrivateUsage]
)
from test_assets import (
    _asset_text_files,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACK = _REPO_ROOT / "plugins" / "orchestration"
_ORCHESTRATE = _PACK / "skills" / "orchestrate"
_SKILL = _ORCHESTRATE / "SKILL.md"
_REFERENCE = _ORCHESTRATE / "references" / "return-note-verification.md"

_TARGET = "references/return-note-verification.md"
_SECTION_3 = "### 3. Review before merging"
_PASSAGE_END = "the author re-runs every finding it cites."
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_SPAN = re.compile(r"`([^`]+)`")
_LINT_LED = re.compile(r"^lint\s")

# (claim, the phrases that must all be present; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "it is a recipe only: the kit ships no runner for it",
        ("it is a recipe only", "the kit ships no runner for it"),
    ),
    (
        "1: the commands are listed with the lint's list option, which runs nothing",
        (
            "list the commands with the hand-off lint's `--list-commands` option",
            "`parallel-session-safety`, section 9",
            "and it runs nothing",
        ),
    ),
    (
        "1: every bullet gets exactly one of five dispositions",
        (
            "give every bullet exactly one disposition",
            "**run**: run it and compare the result with the expected one",
            "**observe**: run it and record the output; a person judges it",
            "**historical**: an event or an old state that cannot be re-run; a reason is required",
            "**skip**: do not run it; a reason is required",
            "**background**: it runs elsewhere (point 6) and its result is imported",
        ),
    ),
    (
        "1: bullets and dispositions are counted against each other",
        (
            "count the bullets against the dispositions",
            "a bullet with no disposition, or a disposition with no bullet, is a finding",
        ),
    ),
    (
        "2: each run's output and exit code go to its own result file",
        ("save each run's output and exit code to its own result file",),
    ),
    (
        "3: the report line is computed from the result files, and the updating script checks it",
        (
            "the report line is computed, never typed",
            "refuses to write unless the numbers its text quotes hold in those files",
        ),
    ),
    (
        "4: a separator that can occur inside a command breaks silently",
        (
            "a search for a diff hunk carries `@@`",
            "gains a field and is misread without an error",
            "or fail on a wrong field count",
        ),
    ),
    (
        "5: a verifier copy takes the project root as an argument",
        (
            "a verifier copy takes the project root as an argument",
            "must be given the project root",
            "never derive the root from its own path (`parents[n]` of the script file)",
        ),
    ),
    (
        "6: long checks run in the background, on copies, between two snapshots",
        (
            "run a long check in the background on copies of the live bytes",
            "take a snapshot before it starts and another after it ends",
            "the status, the diffstat and the content hashes of the files under test",
            "if the two differ, the run is void",
        ),
    ),
    (
        "7: a gap is planted before a clean census is trusted",
        (
            "a census that finds nothing missing has not yet shown that it can see",
            "plant one missing disposition in a copy and show that the checker reports it",
            "`probe_checker.py`",
        ),
    ),
    (
        "the recipe is labelled with its evidence level",
        (
            "evidence level: one project's practice over a few runs; a recipe, not a measured rule",
        ),
    ),
)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _words(text: str) -> str:
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _reference_words() -> str:
    """The reference folded, or empty text when it is absent, so that a missing file fails every
    claim by name instead of raising."""
    return _words(_read(_REFERENCE)) if _REFERENCE.is_file() else ""


def _section(text: str, heading: str) -> str:
    """The one heading line that starts with `heading` and the lines under it, up to the next
    heading of the same or a higher level. A `#` line inside a fence is not a heading. Fails
    loudly when no line, or more than one, starts with `heading`."""
    lines = text.split("\n")
    inside = False
    fenced: list[bool] = []
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            fenced.append(True)
        else:
            fenced.append(inside)
    starts = [
        index
        for index, line in enumerate(lines)
        if not fenced[index] and _HEADING.match(line) and line.startswith(heading)
    ]
    assert len(starts) == 1, f"{heading!r} starts {len(starts)} headings, not 1"
    opening = _HEADING.match(lines[starts[0]])
    assert opening is not None
    body = [lines[starts[0]]]
    for index in range(starts[0] + 1, len(lines)):
        found = None if fenced[index] else _HEADING.match(lines[index])
        if found is not None and len(found[1]) <= len(opening[1]):
            break
        body.append(lines[index])
    return "\n".join(body)


def _pointer_problems(skill_text: str, root: Path) -> list[str]:
    """Why section 3 does not carry the one pointer to the reference, in the paragraph of the
    verifier passage and after it, with a target that exists under `root`; empty when it does."""
    section = _section(skill_text, _SECTION_3)
    found = [target for target in _LINK.findall(section) if target == _TARGET]
    if len(found) != 1:
        return [f"section 3 links {_TARGET} {len(found)} times, not 1"]
    problems: list[str] = []
    if not (root / _TARGET).is_file():
        problems.append(f"the pointer's target {_TARGET} does not exist")
    holding = [
        _words(paragraph)
        for paragraph in section.split("\n\n")
        if _PASSAGE_END in _words(paragraph)
    ]
    if len(holding) != 1:
        return [
            *problems,
            f"{len(holding)} paragraphs of section 3 end the verifier passage",
        ]
    paragraph = holding[0]
    link = f"]({_TARGET})"
    if link not in paragraph:
        problems.append("the pointer is not in the paragraph of the verifier passage")
    elif paragraph.index(link) < paragraph.index(_PASSAGE_END):
        problems.append("the pointer comes before the verifier passage it follows")
    return problems


def _link_problems(text: str, folder: Path) -> list[str]:
    """The markdown links of `text` that are absolute or whose target, read from `folder`, is
    outside the pack."""
    problems: list[str] = []
    for target in _LINK.findall(text):
        if target.startswith(("/", "http", "~")) or re.match(r"[A-Za-z]:", target):
            problems.append(f"{target}: not a relative link")
        elif not (folder / target).resolve().is_relative_to(_PACK.resolve()):
            problems.append(f"{target}: leaves the pack")
    return problems


def _lint_led_spans(text: str) -> list[str]:
    """The code spans that open with the hand-off lint's subcommand: the printed-command scan
    would parse each as a command and require the one printed form, which has one home."""
    return [span for span in _SPAN.findall(text) if _LINT_LED.match(span)]


def _hygiene_problems(text: str) -> list[str]:
    """The reasons the shared hygiene patterns of `test_assets.py` give for `text`."""
    return [why for pattern, why in _ASSET_FORBIDDEN if pattern.search(text)]


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (11, 30)
    assert _REFERENCE.is_file(), f"{_REFERENCE.name} does not exist"
    assert _SKILL.is_file(), _SKILL


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[claim for claim, _ in _ROWS])
def test_the_reference_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_reference_words(), phrases)
    assert not missing, f"the reference does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real text in turn is the one gap reported,
    and an empty text lacks every phrase of a row. A phrase the check cannot see go would let
    the reference lose its claim and stay green."""
    text = _reference_words()
    for claim, phrases in _ROWS:
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_section_3_points_at_the_reference_after_the_verifier_passage() -> None:
    assert _pointer_problems(_read(_SKILL), _ORCHESTRATE) == []


def test_the_pointer_check_sees_each_planted_shape(tmp_path: Path) -> None:
    """Fired at planted texts of section 3: the pointer after the passage in its paragraph is
    clean, and a missing pointer, a dead one, one before the passage, one in a later paragraph
    and a doubled one are each reported."""
    (tmp_path / "references").mkdir()
    (tmp_path / _TARGET).write_text("x\n", encoding="utf-8")
    passage = f"A worker's summary is a claim. A verifier is an instrument too. {_PASSAGE_END}"
    pointer = f"See [{_TARGET}]({_TARGET})."
    head = f"{_SECTION_3} results are claims\n"
    good = f"{head}{passage}\n{pointer}\n\nThe review loop.\n"
    assert _pointer_problems(good, tmp_path) == []
    absent = f"{head}{passage}\n\nThe review loop.\n"
    assert _pointer_problems(absent, tmp_path) == [
        f"section 3 links {_TARGET} 0 times, not 1"
    ]
    assert _pointer_problems(good, tmp_path / "elsewhere") == [
        f"the pointer's target {_TARGET} does not exist"
    ]
    before = f"{head}{pointer}\n{passage}\n\nThe review loop.\n"
    assert _pointer_problems(before, tmp_path) == [
        "the pointer comes before the verifier passage it follows"
    ]
    later = f"{head}{passage}\n\n{pointer}\n"
    assert _pointer_problems(later, tmp_path) == [
        "the pointer is not in the paragraph of the verifier passage"
    ]
    twice = f"{head}{passage}\n{pointer}\n{pointer}\n"
    assert _pointer_problems(twice, tmp_path) == [
        f"section 3 links {_TARGET} 2 times, not 1"
    ]
    with pytest.raises(AssertionError, match="starts 0 headings"):
        _pointer_problems(f"## Another section\n{passage}\n{pointer}\n", tmp_path)


def test_the_reference_is_inside_the_shared_hygiene_scan_and_clean_under_it() -> None:
    scanned = {path.resolve() for path in _asset_text_files()}
    assert _REFERENCE.resolve() in scanned, (
        f"{_REFERENCE.name} is outside the file list of the hygiene scan in test_assets.py"
    )
    assert _hygiene_problems(_read(_REFERENCE)) == []


def test_the_hygiene_patterns_see_planted_shapes_and_not_near_misses() -> None:
    """Fired at planted text: a home path, a drive-letter path, a machine-specific host rule and a
    hard-coded skill-script path are each reported; prose about paths and about hosts is not. The
    planted shapes are built from fragments, so this file holds none of them whole."""
    home = "/" + "Users/someone/notes.md"
    drive = "C" + ":" + chr(92) + "Users" + chr(92) + "someone"
    host = "Windows" + " host"
    script = ".claude/" + "skills/demo/" + "scripts/run.py"
    for planted in (home, drive, host, script):
        assert _hygiene_problems(f"see {planted} for it"), planted
    for near_miss in (
        "a note about Windows paths and about the host's file times",
        "the skills folder of the project, and a scripts folder",
    ):
        assert _hygiene_problems(near_miss) == [], near_miss


def test_the_reference_holds_no_link_and_no_code_span_that_opens_with_the_lint() -> (
    None
):
    text = _read(_REFERENCE)
    assert _link_problems(text, _REFERENCE.parent) == []
    assert _LINK.findall(text) == []
    assert _lint_led_spans(text) == []


def test_the_link_and_code_span_checks_see_planted_shapes() -> None:
    folder = _REFERENCE.parent
    assert _link_problems("[a](brief-template.md)", folder) == []
    leaving = "../../../../core/skills/x/SKILL.md"
    assert _link_problems(f"[a]({leaving})", folder) == [f"{leaving}: leaves the pack"]
    assert _link_problems("[a](/abs/path.md)", folder) == [
        "/abs/path.md: not a relative link"
    ]
    assert _lint_led_spans("run `lint handoffs <file> --list-commands` now") == [
        "lint handoffs <file> --list-commands"
    ]
    assert _lint_led_spans("the `--list-commands` option and `probe_checker.py`") == []
    assert _lint_led_spans("the lint handoffs subcommand, named in prose") == []
