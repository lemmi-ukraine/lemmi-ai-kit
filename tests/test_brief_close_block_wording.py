"""The checks of the brief close block wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_two_close_blocks_agree_step_by_step`: the two close blocks agree step by step
* `test_the_comparison_sees_a_changed_word_and_ignores_wrapping`: The comparison is fired at the real contract block: re-indented and re-wrapped it still agrees, one changed word is the one step reported, and a missing step is reported.
* `test_the_agreement_check_sees_a_changed_or_missing_no_skill_tool_sentence`: Fired at the sentence for a worker without the Skill tool, planted on the folded steps of the real blocks so that it holds wherever a file wraps its lines: one word of it changed in either copy, or the sentence missing from either copy, is step 2 reported and no other step.
* `test_a_rewrapped_close_block_still_reads_the_same_and_agrees`: Each block, re-wrapped at three widths, keeps the same folded steps, every phrase of every step (the sentence for a worker without the Skill tool among them) and its agreement with the other block. The planted wrap is real: the narrowest and the widest wrap are different texts, whatever width the file itself is written at, and the narrowest splits the sentence over lines.
* `test_the_launch_marker_is_given_in_bracket_form_and_never_written_whole`: The placeholder written whole in a shipped file would match the check that looks for it, in the brief a delegate copies from. The rules section gives the bracket form and describes the placeholder in two code spans.
* `test_the_placeholder_scan_sees_a_planted_placeholder`: the placeholder scan sees a planted placeholder
* `test_the_marker_check_prints_true_only_for_a_file_holding_the_placeholder`: The certification the rule asks for, run on the regular expression the template ships: True for a planted file holding the placeholder, False for a file without it and False for a file holding only the check line. The unbracketed expression is then run on a file holding only its own check line: it finds itself there, so the character class is shown to be what prevents that.
* `test_no_file_under_plugins_or_tests_names_the_old_host_rules_path`: The path is one project's, so no shipped file and no test holds it whole. The surface is checked by name: the worker preamble, the contract, the template and the two tests that pin their wording are all in it.
* `test_the_tree_scan_sees_a_planted_path_and_skips_near_misses`: Fired at a planted tree: a file under each root that holds the old path, spelled apart from the constant the scan looks for, is found; a near-miss (the two halves of the path far apart), a file outside the two roots and a compiled file under `__pycache__` are not.
* `test_the_old_path_scan_sees_a_planted_path_and_near_misses`: The scan is fired at a sentence that names the old path, spelled apart from the constant it looks for, and at near-misses: the sentence that took its place, and the two halves of the path far apart.
* `test_the_two_closing_sentences_agree`: the two closing sentences agree
"""

import re
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATE = _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate"
_SKILL = _ORCHESTRATE / "SKILL.md"
_TEMPLATE = _ORCHESTRATE / "references" / "brief-template.md"

_EM = chr(0x2014)
_SKILL_CLOSE_LEAD = f"**Close {_EM} run in this order, do not wait to be asked.**"
_TEMPLATE_CLOSE_HEADING = "## Close (run in this order, do not wait to be asked)"
_RULES_HEADING = "## Rules a dispatch brief carries"
_SKILL_PLACE = "SKILL.md item 9"
_TEMPLATE_PLACE = "brief-template.md Close section"
_PLACES = (_SKILL_PLACE, _TEMPLATE_PLACE)
# The files read whole, for a placeholder written out and for a count of the review's steps.
_WHOLE_FILE_SCANS = (_TEMPLATE, _SKILL)
# What the step that saves into the handoff says it is named by: a brief names a report file or
# a return note, whichever it asks for.
_SAVE_STEP_NAMES = "the report file or return note your brief names"
# What step 2 of both blocks tells a worker whose harness has no Skill tool: an external CLI worker
# has none, so "run it through the Skill tool" cannot be done as written there. It is the last
# sentence of the step; the phrase of the table is the sentence lower-cased, without its full stop.
_NO_SKILL_TOOL = "A worker without the Skill tool reads the skill's steps and says so in its closing message."
_NO_SKILL_TOOL_PHRASE = _NO_SKILL_TOOL.lower().rstrip(".")
# The widths a Close block is re-wrapped at: the narrowest splits the sentence over lines, the
# widest leaves a step shorter than it on one line (a longer step still wraps), and the middle
# one is near the width the files use.
_REWRAP_WIDTHS = (40, 90, 200)


# Written whole, the placeholder would match the check that looks for it, and the old path is
# one project's: both are built from fragments, so no shipped file or test holds them as one.
_PLACEHOLDER = "ADDENDUM-" + "PENDING"
_BRACKET_FORM = "ADDENDUM-PEN[D]ING"
_OLD_HOST_RULES_PATH = ".claude/" + "preambles/" + "spawned-session-" + "host-rules.md"
# A second spelling of the same path, split at other places: the planted positive of the scan is
# built from it, so a typo made in only one of the two spellings is seen and not shared.
_PLANTED_OLD_SENTENCE = (
    "Use it to inject `.claude/pre" + "ambles/spawned-session-host-" + "rules.md`."
)

_HEADING = re.compile(r"^(#{1,6})\s")
_STEP_START = re.compile(r"^\s*(\d+)\.\s")

# (step, the phrases that must all be in that step; lower-cased, whitespace collapsed)
_STEP_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1: the self-challenge",
        (
            "self-challenge: is it detailed enough?",
            "have you missed something?",
            'say what it changed, including "nothing"',
        ),
    ),
    (
        "2: the completion review is run through the skill, before the handoff, and a worker "
        "without the Skill tool reads the skill's steps and says so",
        (
            "then the completion review",
            "`lemmi-ai-kit-core:post-task-review` through the skill tool",
            "whatever the size of the task",
            "a hand-written review does not replace it",
            "if you have not already run it",
            "both run before the handoff",
            _NO_SKILL_TOOL_PHRASE,
        ),
    ),
    (
        "3: the lessons, and where the drafts go when the learnings buffer is barred",
        (
            "lessons: run `lemmi-ai-kit-core:task-learnings`",
            "if your brief bars the learnings buffer",
            "put the lesson drafts in your handoff",
            "say so in your closing message",
        ),
    ),
    (
        "4: everything is saved into the handoff, which the brief names",
        (
            "save everything into the handoff",
            f"({_SAVE_STEP_NAMES})",
        ),
    ),
    (
        "5: a plain summary that says the session may be closed",
        (
            "then write a short summary for whoever reads it next",
            "bullets, at most 10 lines, plain language, no internal ids",
            "the review's step list and the lessons result in it",
            "say in plain words that the session may be closed",
        ),
    ),
)


_SENTENCE_2A = (
    "Use it to inject the project's own host-rules file, if it keeps one "
    f"{_EM} spawned sessions do **not** inherit `AGENTS.md`."
)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _words(text: str) -> str:
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _fenced(lines: list[str]) -> list[bool]:
    """For each line, whether it is a fence line or sits in a fenced block, so that a `#` line
    in a code block is never read as a heading."""
    flags: list[bool] = []
    inside = False
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            flags.append(True)
        else:
            flags.append(inside)
    return flags


def _section(text: str, heading: str) -> str:
    """The one heading line that starts with `heading` and the lines under it, up to the next
    heading of the same or a higher level. Fails loudly when no line, or more than one, starts
    with `heading`."""
    lines = text.split("\n")
    fenced = _fenced(lines)
    starts = [
        index
        for index, line in enumerate(lines)
        if not fenced[index] and _HEADING.match(line) and line.startswith(heading)
    ]
    assert len(starts) == 1, f"{heading!r} starts {len(starts)} headings, not 1"
    opening = _HEADING.match(lines[starts[0]])
    assert opening is not None
    level = len(opening[1])
    body = [lines[starts[0]]]
    for index in range(starts[0] + 1, len(lines)):
        found = None if fenced[index] else _HEADING.match(lines[index])
        if found is not None and len(found[1]) <= level:
            break
        body.append(lines[index])
    return "\n".join(body)


def _skill_close_block(text: str) -> list[str]:
    """The blockquote of the brief contract that holds the Close lead, markers removed. Fails
    loudly when the lead is not on exactly one line."""
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if _SKILL_CLOSE_LEAD in line]
    assert len(starts) == 1, (
        f"the Close lead is on {len(starts)} lines of SKILL.md, not 1"
    )
    block: list[str] = []
    for line in lines[starts[0] :]:
        if not line.lstrip().startswith(">"):
            break
        block.append(re.sub(r"^\s*>\s?", "", line))
    return block


def _template_close_block(text: str) -> list[str]:
    """The lines under the template's Close heading, up to the closing fence of the skeleton
    or the next heading. Fails loudly when the heading is not on exactly one line."""
    lines = text.split("\n")
    starts = [
        index for index, line in enumerate(lines) if line == _TEMPLATE_CLOSE_HEADING
    ]
    assert len(starts) == 1, (
        f"the Close heading is on {len(starts)} lines of the template, not 1"
    )
    block: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if line.startswith("```") or line.startswith("## "):
            break
        block.append(line)
    return block


def _step_line_count(block: list[str]) -> int:
    """How many lines of a block hold its steps: the lines before the first blank one that
    follows a step. The whole block when no blank line follows a step."""
    seen = False
    for index, line in enumerate(block):
        if _STEP_START.match(line):
            seen = True
        elif seen and not line.strip():
            return index
    return len(block)


def _steps(block: list[str]) -> list[str]:
    """The numbered steps of a block, each as one line of folded whitespace. The steps end at the
    first blank line that follows one: what comes after it is the sentence that closes the block."""
    steps: list[str] = []
    for line in block[: _step_line_count(block)]:
        if _STEP_START.match(line):
            steps.append(line.strip())
        elif steps and line.strip():
            steps[-1] = f"{steps[-1]} {line.strip()}"
    return [" ".join(step.split()) for step in steps]


def _close_steps(place: str) -> list[str]:
    if place == _SKILL_PLACE:
        return _steps(_skill_close_block(_read(_SKILL)))
    return _steps(_template_close_block(_read(_TEMPLATE)))


def _disagreements(left: list[str], right: list[str]) -> list[int]:
    """The 1-based numbers of the steps whose folded text differs, or that one side lacks."""
    longest = max(len(left), len(right))
    left_padded = left + [""] * (longest - len(left))
    right_padded = right + [""] * (longest - len(right))
    return [
        number
        for number, (one, other) in enumerate(
            zip(left_padded, right_padded, strict=True), 1
        )
        if one != other
    ]


def _rewrapped(place: str, width: int) -> str:
    """The file that holds the Close block of `place`, with every step of that block re-wrapped at
    `width` columns (breaking at spaces only, as an editor does) and nothing else changed."""
    text = _read(_SKILL if place == _SKILL_PLACE else _TEMPLATE)
    lines = text.split("\n")
    if place == _SKILL_PLACE:
        start = next(
            index for index, line in enumerate(lines) if _SKILL_CLOSE_LEAD in line
        )
        old_count = _step_line_count(_skill_close_block(text)) - 1
        prefix = "   > "
    else:
        start = lines.index(_TEMPLATE_CLOSE_HEADING)
        old_count = _step_line_count(_template_close_block(text))
        prefix = ""
    wrapped = [
        prefix + piece
        for step in _close_steps(place)
        for piece in textwrap.wrap(
            step,
            width=width,
            subsequent_indent="   ",
            break_long_words=False,
            break_on_hyphens=False,
        )
    ]
    lines[start + 1 : start + 1 + old_count] = wrapped
    return "\n".join(lines)


def _close_block(place: str) -> list[str]:
    """The block of `place` as its own cut gives it: the steps and what follows them."""
    if place == _SKILL_PLACE:
        return _skill_close_block(_read(_SKILL))
    return _template_close_block(_read(_TEMPLATE))


def _tail(block: list[str]) -> str:
    """What follows the steps of a block, as one line of folded whitespace: everything after the
    first blank line that follows a step. Empty when nothing does."""
    return " ".join(" ".join(block[_step_line_count(block) :]).split())


def _holds_placeholder(text: str) -> bool:
    return _PLACEHOLDER in text


def _names_old_path(text: str) -> bool:
    return _OLD_HOST_RULES_PATH in text


# The roots read whole for the old host-rules path: what the kit ships and what tests it.
_OLD_PATH_ROOTS = ("plugins", "tests")


def _files_naming_old_path(root: Path) -> tuple[list[Path], list[str]]:
    """Every file under the roots of `_OLD_PATH_ROOTS` in `root`, and the paths (relative to
    `root`) of those that hold the old host-rules path whole. Bytecode is skipped: compiling a
    test joins the fragments the path is built from into one string."""
    needle = _OLD_HOST_RULES_PATH.encode()
    scanned = sorted(
        path
        for name in _OLD_PATH_ROOTS
        for path in (root / name).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    named = [
        path.relative_to(root).as_posix()
        for path in scanned
        if needle in path.read_bytes()
    ]
    return scanned, named


def _own_check_line(expression: str) -> str:
    """The text of a file that holds only the line that searches for `expression`."""
    return f"grep -E '{expression}' brief.md\n"


def _marker_check(check: re.Pattern[str], path: Path) -> bool:
    """What the precondition of a launch brief that searches for the marker prints: whether the
    file matches."""
    return check.search(path.read_text(encoding="utf-8")) is not None


def _shipped_check(template: str) -> re.Pattern[str]:
    """The regular expression the rules section of `template` gives, read from the section
    itself, so the check that is certified is the one the template ships and not a copy typed
    here. Fails loudly when the section gives it zero times or more than once."""
    section = _section(template, _RULES_HEADING)
    found = re.findall(f"`({re.escape(_BRACKET_FORM)})`", section)
    assert len(found) == 1, (
        f"the rules section gives the marker check {len(found)} times, not 1"
    )
    return re.compile(found[0])


def test_the_two_close_blocks_agree_step_by_step() -> None:
    skill = _close_steps(_SKILL_PLACE)
    template = _close_steps(_TEMPLATE_PLACE)
    differing = _disagreements(skill, template)
    assert not differing, (
        f"the two copies of the Close block differ at step(s) {differing}: "
        f"SKILL.md {[skill[n - 1] for n in differing if n <= len(skill)]} "
        f"against the template {[template[n - 1] for n in differing if n <= len(template)]}"
    )


def test_the_comparison_sees_a_changed_word_and_ignores_wrapping() -> None:
    """The comparison is fired at the real contract block: re-indented and re-wrapped it still
    agrees, one changed word is the one step reported, and a missing step is reported."""
    block = _skill_close_block(_read(_SKILL))
    steps = _steps(block)
    assert steps, "the contract's Close block holds no step"
    rewrapped = _steps([line.strip() for line in block])
    assert rewrapped == steps and _disagreements(steps, rewrapped) == []
    changed = _steps([line.replace("Self-challenge", "Self-check") for line in block])
    assert changed != steps, "the planted change changed nothing"
    assert _disagreements(steps, changed) == [1]
    assert _disagreements(steps, steps[:-1]) == [len(steps)]


def test_the_agreement_check_sees_a_changed_or_missing_no_skill_tool_sentence() -> None:
    """Fired at the sentence for a worker without the Skill tool, planted on the folded steps of
    the real blocks so that it holds wherever a file wraps its lines: one word of it changed in
    either copy, or the sentence missing from either copy, is step 2 reported and no other step."""
    skill = _close_steps(_SKILL_PLACE)
    template = _close_steps(_TEMPLATE_PLACE)
    for place, steps in ((_SKILL_PLACE, skill), (_TEMPLATE_PLACE, template)):
        assert _NO_SKILL_TOOL in steps[1], (
            f"{place}: step 2 does not hold the sentence for a worker without the Skill tool"
        )
    assert _disagreements(skill, template) == []
    skimmed = _NO_SKILL_TOOL.replace("reads", "skims")
    assert skimmed != _NO_SKILL_TOOL
    for steps, other in ((skill, template), (template, skill)):
        changed = [step.replace(_NO_SKILL_TOOL, skimmed) for step in steps]
        missing = [step.replace(f" {_NO_SKILL_TOOL}", "") for step in steps]
        for planted in (changed, missing):
            assert planted != steps, "the planted change changed nothing"
            assert _disagreements(planted, other) == [2]
            assert _disagreements(other, planted) == [2]


@pytest.mark.parametrize("place", _PLACES)
def test_a_rewrapped_close_block_still_reads_the_same_and_agrees(place: str) -> None:
    """Each block, re-wrapped at three widths, keeps the same folded steps, every phrase of every
    step (the sentence for a worker without the Skill tool among them) and its agreement with the
    other block. The planted wrap is real: the narrowest and the widest wrap are different texts,
    whatever width the file itself is written at, and the narrowest splits the sentence over
    lines."""
    cut = _skill_close_block if place == _SKILL_PLACE else _template_close_block
    other = _close_steps(_TEMPLATE_PLACE if place == _SKILL_PLACE else _SKILL_PLACE)
    expected = _close_steps(place)
    texts = {width: _rewrapped(place, width) for width in _REWRAP_WIDTHS}
    for width, text in texts.items():
        steps = _steps(cut(text))
        assert steps == expected, f"{place} re-wrapped at {width} reads differently"
        for step, (claim, phrases) in zip(steps, _STEP_ROWS, strict=True):
            missing = _missing(_words(step), phrases)
            assert not missing, (
                f"{place} at {width} does not state {claim!r}: {missing}"
            )
        assert _disagreements(steps, other) == [], f"{place} at {width} disagrees"
    narrowest, widest = min(_REWRAP_WIDTHS), max(_REWRAP_WIDTHS)
    assert texts[narrowest] != texts[widest], (
        f"the wrap at {narrowest} and the wrap at {widest} are the same text"
    )
    assert all(_NO_SKILL_TOOL not in line for line in cut(texts[narrowest])), (
        "the narrowest wrap kept the sentence on one line"
    )


def test_the_launch_marker_is_given_in_bracket_form_and_never_written_whole() -> None:
    """The placeholder written whole in a shipped file would match the check that looks for it,
    in the brief a delegate copies from. The rules section gives the bracket form and describes
    the placeholder in two code spans."""
    for path in _WHOLE_FILE_SCANS:
        assert not _holds_placeholder(_read(path)), (
            f"{path.name} writes the placeholder whole"
        )
    assert _BRACKET_FORM in _section(_read(_TEMPLATE), _RULES_HEADING)


def test_the_placeholder_scan_sees_a_planted_placeholder() -> None:
    assert _holds_placeholder(f"## Addendum\n{_PLACEHOLDER}\n")
    assert _holds_placeholder(f"x {_PLACEHOLDER} y")
    shipped_shape = (
        "The placeholder line is one word, `ADDENDUM-` followed by `PENDING`, written "
        f"without brackets, and the check is `{_BRACKET_FORM}`."
    )
    assert not _holds_placeholder(shipped_shape)


def _certify(template: str, folder: Path) -> tuple[bool, bool, bool, bool]:
    """The certification the rule asks for, run on the regular expression `template` ships.
    Four answers, in this order: for a planted file holding the placeholder, for a file without
    it, for a file holding only the check line, and, for the expression written without its
    character class, for a file holding only its own check line. Each check line is written from
    the expression it is run with. Fails loudly when `template` does not give the check once in
    its rules section."""

    def printed(expression: re.Pattern[str], name: str, text: str) -> bool:
        path = folder / name
        path.write_text(text, encoding="utf-8")
        return _marker_check(expression, path)

    check = _shipped_check(template)
    unbracketed = re.compile(_PLACEHOLDER)
    return (
        printed(check, "holding.md", f"# A brief\n\n{_PLACEHOLDER}\n"),
        printed(check, "without.md", "# A brief\n\nThe addendum was filled in.\n"),
        printed(check, "only-the-check.md", _own_check_line(check.pattern)),
        printed(
            unbracketed, "unbracketed-own-line.md", _own_check_line(unbracketed.pattern)
        ),
    )


def test_the_marker_check_prints_true_only_for_a_file_holding_the_placeholder(
    tmp_path: Path,
) -> None:
    """The certification the rule asks for, run on the regular expression the template ships:
    True for a planted file holding the placeholder, False for a file without it and False for a
    file holding only the check line. The unbracketed expression is then run on a file holding
    only its own check line: it finds itself there, so the character class is shown to be what
    prevents that."""
    holding, without, only_the_check, unbracketed_own_line = _certify(
        _read(_TEMPLATE), tmp_path
    )
    assert holding is True
    assert without is False
    assert only_the_check is False
    assert unbracketed_own_line is True


def test_no_file_under_plugins_or_tests_names_the_old_host_rules_path() -> None:
    """The path is one project's, so no shipped file and no test holds it whole. The surface is
    checked by name: the worker preamble, the contract, the template and this test are all in
    it."""
    scanned, named = _files_naming_old_path(_REPO_ROOT)
    assert not named, f"{len(named)} of {len(scanned)} files hold the old path: {named}"
    relative = {path.relative_to(_REPO_ROOT).as_posix() for path in scanned}
    expected = {
        "plugins/orchestration/skills/agent-delegate/assets/worker-preamble.md",
        "plugins/orchestration/skills/orchestrate/SKILL.md",
        "plugins/orchestration/skills/orchestrate/references/brief-template.md",
        "tests/test_brief_close_block_wording.py",
    }
    assert expected <= relative, f"the scan missed {sorted(expected - relative)}"


def test_the_tree_scan_sees_a_planted_path_and_skips_near_misses(
    tmp_path: Path,
) -> None:
    """Fired at a planted tree: a file under each root that holds the old path, spelled apart
    from the constant the scan looks for, is found; a near-miss (the two halves of the path far
    apart), a file outside the two roots and a compiled file under `__pycache__` are not."""
    planted = {
        "plugins/pack/preamble.md": _PLANTED_OLD_SENTENCE,
        "tests/test_planted.py": f'TEXT = "{_PLANTED_OLD_SENTENCE}"\n',
        "plugins/pack/near.md": "a folder of preambles, and a file named host-rules.md",
        "docs/record.md": _PLANTED_OLD_SENTENCE,
        "tests/__pycache__/test_planted.pyc": _PLANTED_OLD_SENTENCE,
    }
    for relative, text in planted.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    scanned, named = _files_naming_old_path(tmp_path)
    assert named == ["plugins/pack/preamble.md", "tests/test_planted.py"], named
    assert len(scanned) == 3, [path.name for path in scanned]


def test_the_old_path_scan_sees_a_planted_path_and_near_misses() -> None:
    """The scan is fired at a sentence that names the old path, spelled apart from the constant it
    looks for, and at near-misses: the sentence that took its place, and the two halves of the
    path far apart."""
    assert _names_old_path(_PLANTED_OLD_SENTENCE)
    assert _names_old_path(f"a line\n{_PLANTED_OLD_SENTENCE} More.\nand another")
    assert not _names_old_path(_SENTENCE_2A)
    assert not _names_old_path("a folder of preambles, and a file named host-rules.md")


# --- the sentence after the five steps ------------------------------------------------------------


def test_the_two_closing_sentences_agree() -> None:
    skill = _tail(_close_block(_SKILL_PLACE))
    template = _tail(_close_block(_TEMPLATE_PLACE))
    assert skill and skill == template, (
        f"the closing sentences differ: SKILL.md {skill!r} against the template {template!r}"
    )
