"""The Close block is one text in two places, and a dispatch brief carries three more rules.

A brief pastes the Close block verbatim, and two files hold it: the brief contract of
`orchestrate/SKILL.md` (item 9, a blockquote) and the delegation template in
`orchestrate/references/brief-template.md` (the last section of the fenced skeleton). The two
copies had drifted apart and neither named the review skill, the lessons step or the handoff's
name. Each now holds five steps in the same words, in this order: the self-challenge, the
completion review (run through the Skill tool, whatever the size of the task), the lessons (and
where the drafts go when the brief bars the learnings buffer), the handoff, and the summary that
tells the reader the session may be closed. The review's step list is not counted anywhere: a
count goes stale where the skill that owns the list changes it.

The completion review's step ends with one sentence for a worker whose harness has no Skill tool,
as the external CLI workers a brief can be sent to have none: it reads the skill's steps and says
so in its closing message. The sentence comes last, after "Both run BEFORE the handoff.", so the
older words of the step stay one run of text, which the worker-preamble test pins.

The template's list of rules a brief carries gains three in a row, after the rules it had: a brief
filled in at launch ends with a marker block that one of its preconditions searches for with a
regular expression that does not match its own text, a brief never tells an agent to run a
user-only skill, and a brief that lists acceptance criteria names who ticks the boxes. Section 2a
of `SKILL.md` no longer names one project's host-rules file; it says the project's own, if it
keeps one. No other file under `plugins/` or `tests/` holds that path whole either.

Four wordings are retired and must stay gone: no precondition is called "the first" one (the
paste-line comparison and the marker search are two of several), the user-only rule gives
`commit-message` as an example and not as the one such skill, and the step that saves into the
handoff names "the report file or return note your brief names", since a brief may name either.
The three lists of the worker preamble's topics (in the skeleton of the template, in its rule of
thumb and in item 8 of the contract) end with the size, stop and close rules; the tests read the
three lists and not the preamble.

THE SURFACE, in numbers the tests assert: 2 Close blocks (the contract's blockquote and the
template's last section) of 5 steps each, judged by 20 phrases; 3 claims and 21 phrases in one
section of the template (`## Rules a dispatch brief carries`); 4 retired wordings, each absent
from its own place; 3 lists of preamble topics, each pinned by its last words; 2 whole files (the
contract and the template) scanned for the launch placeholder and for a count of the review's
steps. Read
beside them, by name and not by count: every file under `plugins/` and `tests/` for the old
host-rules path, and the one sentence of section 2a that replaced it. A claim holds when every phrase is in its step
or section (lower-cased, whitespace collapsed), and each phrase is fired at a planted removal,
so a phrase the check could not see go is not in the table. The two scans that are green on the
text that came before (no placeholder written whole, no step count) are fired at planted texts
instead, and so is the old-path scan, which has no other proof once the old path is gone. So is
every helper that cuts a section, an item or a block out of a file: it is fired at a planted
document that holds a second section, a heading inside a fence, a heading twice, a paragraph
that trails the item it belongs to, and, placed before the real line, a decoy that only contains
the text looked for or only starts like it. A claim's phrases leave no word of its sentence
outside them and do not overlap: a word outside every phrase can be deleted with every test
still green, and two phrases that share words cannot be told apart by the planted removal.

The sentence for a worker without the Skill tool is fired at three kinds of planted change: one
word of it changed in either copy, or the sentence missing from one copy, is the one step reported;
the sentence placed in another step is found there and not in step 2, and placed after the block it
is found in no step; and each block re-wrapped at 3 widths, the narrowest splitting the sentence
over lines, reads as it did.

Each block also ends with one sentence after its five steps, set off from them by a blank line, and
the two copies hold it in the same words: write the hand-off from the seeded hand-off template, keep
the label on line 1 and the sections the newest contract version adds, and run the one-file hand-off
lint on it before the step that summarises. It is a literal the lint matches by exact text, so a
brief carries it whole and does not point at the template (item 10 of the contract). The label and
the section names are read from `checks`, the path of the template is checked against what the
scaffold plans, and the number of the step it names is read from the steps, so a new contract
version, a renamed template or a renumbered block turns the tests red. The steps end at the first
blank line, so the sentence is never a sixth line of step 5. The third operator-interface rule of
item 9 says the human-facing summary is the hand-off's own section, said again as the closing
message. THE SURFACE of this part, in numbers the tests assert: 2 blocks, each with 1 closing
sentence read in 4 runs that leave no word of it out. The summary rule is found among the bullets
of item 9 by its lead, and a lead that starts no bullet, or two, fails.
"""

import re
import textwrap
from pathlib import Path

import pytest

from lemmi_ai_kit import checks, scaffold
from lemmi_ai_kit.manifest import load_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATE = _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate"
_SKILL = _ORCHESTRATE / "SKILL.md"
_TEMPLATE = _ORCHESTRATE / "references" / "brief-template.md"

_EM = chr(0x2014)
_EN = chr(0x2013)
_SKILL_CLOSE_LEAD = f"**Close {_EM} run in this order, do not wait to be asked.**"
_TEMPLATE_CLOSE_HEADING = "## Close (run in this order, do not wait to be asked)"
_CONTRACT_ITEM = "9. **The close block"
_RULES_HEADING = "## Rules a dispatch brief carries"
_LAUNCH_HEADING = "### 2a."
_PASTE_HEADING = "## Paste line"
_STANDING_HEADING = "## Standing rules"
_ITEM_8 = "8. **Point the worker at the preamble FILE"
_RULE_OF_THUMB = "- **Inline the TASK-SPECIFIC source of truth"
_SKILL_PLACE = "SKILL.md item 9"
_TEMPLATE_PLACE = "brief-template.md Close section"
_PLACES = (_SKILL_PLACE, _TEMPLATE_PLACE)
# The files read whole, for a placeholder written out and for a count of the review's steps.
_WHOLE_FILE_SCANS = (_TEMPLATE, _SKILL)
# What the step that saves into the handoff says it is named by: a brief names a report file or
# a return note, whichever it asks for.
_SAVE_STEP_NAMES = "the report file or return note your brief names"
# The new topic of the worker preamble, which the three lists of its topics now end with.
_SIZE_STOP_CLOSE = "size, stop and close"
# What step 2 of both blocks tells a worker whose harness has no Skill tool: an external CLI worker
# has none, so "run it through the Skill tool" cannot be done as written there. It is the last
# sentence of the step; the phrase of the table is the sentence lower-cased, without its full stop.
_NO_SKILL_TOOL = "A worker without the Skill tool reads the skill's steps and says so in its closing message."
_NO_SKILL_TOOL_PHRASE = _NO_SKILL_TOOL.lower().rstrip(".")
# The widths a Close block is re-wrapped at: the narrowest splits the sentence over lines, the
# widest leaves a step shorter than it on one line (a longer step still wraps), and the middle
# one is near the width the files use.
_REWRAP_WIDTHS = (40, 90, 200)

# The sentence after the five steps. Its label and its section names are read from the lint's table,
# and the path it names is checked against what the scaffold plans; the number of the step it names
# is read from the steps. A new contract version or a renamed template turns the tests red.
_NEWEST = max(checks.HANDOFF_SECTIONS_BY_VERSION)
_LABEL = f"<!-- handoff-contract: v{_NEWEST} -->"
_ADDED_SECTIONS = checks.HANDOFF_SECTIONS_BY_VERSION[_NEWEST]
_HAND_OFF_TEMPLATE = ".ai/templates/handoff.md"
_SUMMARY_STEP = "Then write a short summary"
_SAVE_STEP = "Save everything into the handoff"
_SUMMARY_SECTION = "Orchestrator summary"
_NO_SENTENCE = "no sentence follows the five steps"
_SUMMARY_BULLET_LEAD = "- **The human-facing summary"
_LESS_OR_EQUAL = chr(0x2264)

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
_STEP_COUNT = re.compile(
    r"\bsteps?\s+0\s*(?:to|through|-|" + _EN + r")\s*(?:step\s+)?9\b", re.IGNORECASE
)

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

# (claim, the phrases that must all be in the section; lower-cased, whitespace collapsed)
_RULE_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "m: a brief filled in at launch ends with a marker block, one of its preconditions searches",
        (
            "a brief filled in at launch ends with a marker block",
            "one of its preconditions searches for the marker",
            "the placeholder line is one word",
            "`addendum-` followed by `pending`",
            "written without brackets",
            "the precondition searches for it as a regular expression with",
            "one character in a class, `addendum-pen[d]ing`",
            "which does not match its own text",
            "a match means the launch addendum is missing",
            "the delegate stops and says so",
            "certify the check before the brief ships",
            "it prints true for a file holding the placeholder, and false for a file without it "
            "and for a file holding only the check line",
        ),
    ),
    (
        "u: a brief never tells an agent to run a user-only skill",
        (
            "a brief never tells an agent to run a user-only skill",
            "for example `commit-message`:",
            "when the operator asks for a commit",
            "the agent writes the message from the change itself",
            "and says the skill is the operator's to run",
        ),
    ),
    (
        "a: a brief that lists acceptance criteria names who ticks the boxes and the status line",
        (
            "a brief that lists acceptance criteria names who ticks the boxes",
            "who writes the status line",
            "a worker that is not named edits no task file",
            "the worker preamble says how it returns the criteria",
        ),
    ),
)

# The three new rules open their bullets with these leads, in a row and in this order. Later rules
# may follow them: a rule added at the end of the section is not a break of the order.
_NEW_RULE_LEADS = (
    "- **A brief filled in at launch ends with a marker block, and one of its preconditions "
    "searches for the marker.**",
    "- **A brief never tells an agent to run a user-only skill.**",
    "- **A brief that lists acceptance criteria names who ticks the boxes and who writes the "
    "Status line.**",
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


def _top_level_item(text: str, lead: str) -> str:
    """The one list item that starts a line with `lead` and every line after it up to the next
    top-level numbered item or heading. Fails loudly when no line, or more than one, starts
    with `lead`."""
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(lead)]
    assert len(starts) == 1, f"{lead!r} starts {len(starts)} lines, not 1"
    item = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if re.match(r"\d+\. ", line) or _HEADING.match(line):
            break
        item.append(line)
    return "\n".join(item)


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


def _steps_with_the_no_skill_tool_sentence(steps: list[str]) -> list[int]:
    """The 1-based numbers of the folded steps that hold the sentence for a worker without the
    Skill tool."""
    return [number for number, step in enumerate(steps, 1) if _NO_SKILL_TOOL in step]


def _bullets(section: str) -> list[str]:
    """The bullets of a section, each as one line of folded whitespace."""
    bullets: list[str] = []
    for line in section.split("\n"):
        if line.startswith("- "):
            bullets.append(line)
        elif bullets and line.strip():
            bullets[-1] = f"{bullets[-1]} {line.strip()}"
    return [" ".join(bullet.split()) for bullet in bullets]


def _cited_step_problems(text: str) -> list[str]:
    """Why the paragraph that says which step writes a file does not cite the step that saves
    into the handoff; empty when it does."""
    steps = _steps(_skill_close_block(text))
    saved = [number for number, step in enumerate(steps, 1) if _SAVE_STEP_NAMES in step]
    if not saved:
        return ["no step of the Close block names the return note"]
    item = " ".join(_top_level_item(text, _CONTRACT_ITEM).split())
    cited = [
        int(number) for number in re.findall(r"\bStep (\d+) writes a file\b", item)
    ]
    if cited != saved:
        return [
            f"the paragraph cites step {cited} as the one that writes a file; it is {saved}"
        ]
    return []


def _planted_contract(cited: int, with_return_note: bool = True) -> str:
    saves = "Save everything into the handoff"
    saves += f" ({_SAVE_STEP_NAMES})." if with_return_note else "."
    return (
        f"9. **The close block {_EM} paste it verbatim into every brief.** A paragraph.\n\n"
        f"   > **Close {_EM} run in this order, do not wait to be asked.**\n"
        "   > 1. Self-challenge: one.\n"
        "   > 2. Then the completion review: two.\n"
        "   > 3. Lessons: three.\n"
        f"   > 4. {saves}\n"
        "   > 5. Then write a short summary: five.\n\n"
        f"   Step {cited} writes a file: a sub-agent whose harness refuses the write returns\n"
        "   the handoff content as text (item 8).\n"
        "10. **Another item.**\n"
    )


def _planted_template(step_two: str, step_three: str, after: str) -> str:
    """A cut-down template: a fenced skeleton whose Close section holds three steps, and the
    text `after` the closing fence."""
    return (
        "```markdown\n"
        f"{_TEMPLATE_CLOSE_HEADING}\n"
        "1. one\n"
        f"2. {step_two}\n"
        f"3. {step_three}\n"
        "```\n\n"
        f"{after}\n"
    )


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


def _closing_runs(step: int) -> tuple[str, ...]:
    """The sentence after the steps, in four runs that between them leave no word of it out.
    `step` is the number of the step it says the lint runs before."""
    sections = " and ".join(f"`## {name}`" for name in _ADDED_SECTIONS)
    return (
        f"Write the hand-off from `{_HAND_OFF_TEMPLATE}`:",
        f"line 1 stays `{_LABEL}`,",
        f"and {sections} stay in it;",
        f"run the one-file hand-off lint on it before step {step}.",
    )


def _numbered(steps: list[str], lead: str) -> list[int]:
    """The 1-based numbers of the folded steps that hold `lead`."""
    return [number for number, step in enumerate(steps, 1) if lead in step]


def _closing_problems(steps: list[str], tail: str) -> list[str]:
    """Why `tail`, the text after the steps, is not the closing sentence; empty when it is. The
    step the sentence names is read from `steps`: it is the one that summarises, and the one
    before it is the one that saves into the handoff, so a renumbered block is reported. Fails
    loudly when no step, or more than one, summarises."""
    if not tail:
        return [_NO_SENTENCE]
    summarising = _numbered(steps, _SUMMARY_STEP)
    assert len(summarising) == 1, f"{len(summarising)} steps summarise, not 1"
    problems: list[str] = []
    saving = _numbered(steps, _SAVE_STEP)
    if saving != [summarising[0] - 1]:
        problems.append(
            f"step(s) {saving} save into the handoff, and the lint runs before step "
            f"{summarising[0]}"
        )
    expected = " ".join(_closing_runs(summarising[0]))
    if tail != expected:
        problems.append(f"the sentence reads {tail!r}, not {expected!r}")
    return problems


def _steps_holding_the_sentence(steps: list[str]) -> list[int]:
    """The 1-based numbers of the folded steps that hold the first run of the closing sentence."""
    return _numbered(steps, _closing_runs(0)[0])


def _item_bullets(item: str) -> list[str]:
    """The bullets that stand in an item at three spaces and a dash, each as one line of folded
    whitespace; the lines that run on under one (five spaces) are part of it."""
    bullets: list[str] = []
    for line in item.split("\n"):
        if line.startswith("   - "):
            bullets.append(line.strip())
        elif bullets and line.startswith("     ") and line.strip():
            bullets[-1] = f"{bullets[-1]} {line.strip()}"
    return [" ".join(bullet.split()) for bullet in bullets]


def _summary_bullet(text: str) -> str:
    """The one bullet of item 9 that starts with the lead of the human-facing summary rule, folded.
    Fails loudly when no bullet, or more than one, starts with it."""
    bullets = _item_bullets(_top_level_item(text, _CONTRACT_ITEM))
    found = [bullet for bullet in bullets if bullet.startswith(_SUMMARY_BULLET_LEAD)]
    assert len(found) == 1, (
        f"{_SUMMARY_BULLET_LEAD!r} starts {len(found)} bullets, not 1"
    )
    return found[0]


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


def _skeleton(text: str) -> str:
    """The lines between the first pair of code fences: the brief template is that block, and
    the headings in it are headings only once the fences are gone. Fails loudly when the text
    holds no complete fenced block."""
    inside: list[str] = []
    opened = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if opened:
                return "\n".join(inside)
            opened = True
        elif opened:
            inside.append(line)
    raise AssertionError("the text holds no complete fenced block")


def _bullet_starting(text: str, lead: str) -> str:
    """The one bullet of `text` that starts with `lead`, as one line of folded whitespace. Fails
    loudly when no bullet, or more than one, starts with `lead`."""
    found = [bullet for bullet in _bullets(text) if bullet.startswith(lead)]
    assert len(found) == 1, f"{lead!r} starts {len(found)} bullets, not 1"
    return found[0]


# The wordings that are retired: each is looked for in its own place only (the key names it).
_RETIRED_KEYS = (
    "first precondition: the whole template",
    "is the one: the user-only rule",
    "return note only: step 4 of SKILL.md item 9",
    "return note only: step 4 of the template's Close section",
)

# The three lists of the worker preamble's topics, and the words each one ends with.
_TOPIC_LIST_ENDS = {
    "template skeleton": "how to return a result, and the size, stop and close rules.",
    "template rule of thumb": "how to return, size, stop and close)",
    "contract item 8": "how to return a result, and the size, stop and close rules)",
}


def _retired_wordings() -> dict[str, tuple[str, str]]:
    """For each key of `_RETIRED_KEYS`: the folded text of its place, and the wording that must
    not be in it."""
    template = _read(_TEMPLATE)
    rules = _section(template, _RULES_HEADING)
    return {
        _RETIRED_KEYS[0]: (_words(template), "first precondition"),
        _RETIRED_KEYS[1]: (
            _words(_bullet_starting(rules, _NEW_RULE_LEADS[1])),
            "is the one",
        ),
        _RETIRED_KEYS[2]: (
            _words(_close_steps(_SKILL_PLACE)[3]),
            "(the return note your brief names)",
        ),
        _RETIRED_KEYS[3]: (
            _words(_close_steps(_TEMPLATE_PLACE)[3]),
            "(the return note your brief names)",
        ),
    }


def _topic_list_places() -> dict[str, str]:
    """For each key of `_TOPIC_LIST_ENDS`: the folded text of the place that holds the list."""
    template = _read(_TEMPLATE)
    return {
        "template skeleton": _words(_section(_skeleton(template), _STANDING_HEADING)),
        "template rule of thumb": _words(_bullet_starting(template, _RULE_OF_THUMB)),
        "contract item 8": _words(_top_level_item(_read(_SKILL), _ITEM_8)),
    }


def test_the_surface_is_stated_in_numbers() -> None:
    step_phrases = [phrase for _, phrases in _STEP_ROWS for phrase in phrases]
    rule_phrases = [phrase for _, phrases in _RULE_ROWS for phrase in phrases]
    assert (len(_STEP_ROWS), len(step_phrases)) == (5, 20)
    assert (len(_RULE_ROWS), len(rule_phrases)) == (3, 21)
    assert len(_RETIRED_KEYS) == 4 and set(_retired_wordings()) == set(_RETIRED_KEYS)
    assert len(_TOPIC_LIST_ENDS) == 3
    assert set(_topic_list_places()) == set(_TOPIC_LIST_ENDS)
    assert len(_NEW_RULE_LEADS) == len(_RULE_ROWS)
    assert len(_PLACES) == 2
    assert len(_REWRAP_WIDTHS) == 3 and len(set(_REWRAP_WIDTHS)) == 3
    assert len(_WHOLE_FILE_SCANS) == 2 and len(set(_WHOLE_FILE_SCANS)) == 2
    for path in _WHOLE_FILE_SCANS:
        assert path.is_file(), path
    assert len(_closing_runs(5)) == 4 and len(_PLACES) == 2


@pytest.mark.parametrize("place", _PLACES)
def test_each_close_block_holds_the_five_steps_in_order(place: str) -> None:
    steps = _close_steps(place)
    assert len(steps) == len(_STEP_ROWS), (
        f"{place} holds {len(steps)} steps, not 5: {steps}"
    )
    for number, (step, (claim, phrases)) in enumerate(
        zip(steps, _STEP_ROWS, strict=True), 1
    ):
        assert step.startswith(f"{number}. "), (
            f"{place}: step {number} is numbered wrongly"
        )
        missing = _missing(_words(step), phrases)
        assert not missing, f"{place} does not state {claim!r}: missing {missing}"


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


def test_only_step_two_of_the_block_counts_for_the_no_skill_tool_sentence() -> None:
    """Fired at planted documents, in the contract's blockquote and in the template's last
    section: the sentence at the end of step 2 is found in step 2 and in no other step, the same
    sentence in step 3 is found in step 3 and not in step 2, and in the text after the block it is
    found in no step at all. The pin reads the block, cut by its own lead or heading, and not the
    whole file; a cut that ran on past the block would put the text after it into the last step."""
    contract = _planted_contract(cited=4)
    in_two = contract.replace(
        "2. Then the completion review: two.",
        f"2. Then the completion review: two. {_NO_SKILL_TOOL}",
    )
    in_three = contract.replace(
        "3. Lessons: three.", f"3. Lessons: three. {_NO_SKILL_TOOL}"
    )
    after_block = contract.replace(
        "   Step 4 writes a file", f"   {_NO_SKILL_TOOL}\n\n   Step 4 writes a file"
    )
    for planted in (in_two, in_three, after_block):
        assert planted != contract, "the planted placement changed nothing"
    template_in_two = _planted_template(f"two. {_NO_SKILL_TOOL}", "three", "")
    template_in_three = _planted_template("two", f"three. {_NO_SKILL_TOOL}", "")
    template_after_block = _planted_template("two", "three", _NO_SKILL_TOOL)
    cases: tuple[tuple[str, list[str], list[int]], ...] = (
        ("contract, in step 2", _skill_close_block(in_two), [2]),
        ("contract, in step 3", _skill_close_block(in_three), [3]),
        ("contract, after the block", _skill_close_block(after_block), []),
        ("template, in step 2", _template_close_block(template_in_two), [2]),
        ("template, in step 3", _template_close_block(template_in_three), [3]),
        ("template, after the block", _template_close_block(template_after_block), []),
    )
    for name, block, expected in cases:
        found = _steps_with_the_no_skill_tool_sentence(_steps(block))
        assert found == expected, f"{name}: in step(s) {found}, not {expected}"


def test_the_paragraph_after_the_block_cites_the_save_step() -> None:
    """Renumbering the Close block moves the step that writes the handoff; the sentence that
    says which step writes a file must follow it."""
    problems = _cited_step_problems(_read(_SKILL))
    assert not problems, problems


def test_the_save_step_check_sees_a_stale_number() -> None:
    assert _cited_step_problems(_planted_contract(cited=4)) == []
    stale = _cited_step_problems(_planted_contract(cited=3))
    assert len(stale) == 1 and "cites step [3]" in stale[0], stale
    unnamed = _cited_step_problems(_planted_contract(cited=4, with_return_note=False))
    assert unnamed == ["no step of the Close block names the return note"]


@pytest.mark.parametrize(
    ("claim", "phrases"), _RULE_ROWS, ids=[row[0] for row in _RULE_ROWS]
)
def test_the_rules_section_states_the_claim(
    claim: str, phrases: tuple[str, ...]
) -> None:
    section = _words(_section(_read(_TEMPLATE), _RULES_HEADING))
    missing = _missing(section, phrases)
    assert not missing, f"the section does not state {claim!r}: missing {missing}"


def test_the_new_rules_are_three_consecutive_bullets_in_order() -> None:
    bullets = _bullets(_section(_read(_TEMPLATE), _RULES_HEADING))
    starts = [
        at for at, bullet in enumerate(bullets) if bullet.startswith(_NEW_RULE_LEADS[0])
    ]
    assert len(starts) == 1, (
        f"{_NEW_RULE_LEADS[0]!r} starts {len(starts)} bullets, not 1"
    )
    run = bullets[starts[0] : starts[0] + len(_NEW_RULE_LEADS)]
    assert len(run) == len(_NEW_RULE_LEADS), bullets
    for lead, bullet in zip(_NEW_RULE_LEADS, run, strict=True):
        assert bullet.startswith(lead), (
            f"expected a bullet that opens {lead!r}, found {bullet!r}"
        )


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real text in turn is the one gap reported,
    and an empty text lacks every phrase of a row. A phrase the check cannot see go would let
    the text lose its rule and stay green."""
    section = _words(_section(_read(_TEMPLATE), _RULES_HEADING))
    rows: list[tuple[str, str, tuple[str, ...]]] = [
        ("rules section", section, phrases) for _, phrases in _RULE_ROWS
    ]
    for place in _PLACES:
        steps = _close_steps(place)
        assert len(steps) == len(_STEP_ROWS), f"{place} holds {len(steps)} steps, not 5"
        rows += [
            (place, _words(step), phrases)
            for step, (_, phrases) in zip(steps, _STEP_ROWS, strict=True)
        ]
    for where, text, phrases in rows:
        assert not _missing(text, phrases), (
            f"{where}: a claim does not hold at the start"
        )
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                where,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), where


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


def test_the_certification_reads_the_check_from_the_template_it_is_given(
    tmp_path: Path,
) -> None:
    """Fired at planted templates: one that gives the check in its rules section is certified,
    one that gives it nowhere and one that gives it only outside the rules section are refused.
    A certification run on a copy of the check typed in the test would pass on all three, and
    one that read the whole file would pass on the third."""
    gives = f"{_RULES_HEADING}\n\n- the check is `{_BRACKET_FORM}`\n"
    assert _certify(gives, tmp_path) == (True, False, False, True)
    nowhere = f"{_RULES_HEADING}\n\n- no check is given\n"
    elsewhere = (
        f"## Paste line\n\n- the check is `{_BRACKET_FORM}`\n\n"
        f"{_RULES_HEADING}\n\n- no check is given here\n"
    )
    for planted in (nowhere, elsewhere):
        with pytest.raises(AssertionError, match="0 times"):
            _certify(planted, tmp_path)


def test_section_2a_names_no_projects_host_rules_file() -> None:
    skill = _read(_SKILL)
    assert not _names_old_path(skill), (
        "SKILL.md still names one project's host-rules path"
    )
    section = " ".join(_section(skill, _LAUNCH_HEADING).split())
    assert "host-rules file" in section, "section 2a does not name the host-rules file"
    assert _SENTENCE_2A in section, f"section 2a lost the sentence {_SENTENCE_2A!r}"


def test_no_file_under_plugins_or_tests_names_the_old_host_rules_path() -> None:
    """The path is one project's, so no shipped file and no test holds it whole. The surface is
    checked by name: the worker preamble, the contract, the template and the two tests that pin
    their wording are all in it."""
    scanned, named = _files_naming_old_path(_REPO_ROOT)
    assert not named, f"{len(named)} of {len(scanned)} files hold the old path: {named}"
    relative = {path.relative_to(_REPO_ROOT).as_posix() for path in scanned}
    expected = {
        "plugins/orchestration/skills/agent-delegate/assets/worker-preamble.md",
        "plugins/orchestration/skills/orchestrate/SKILL.md",
        "plugins/orchestration/skills/orchestrate/references/brief-template.md",
        "tests/test_brief_close_block_wording.py",
        "tests/test_worker_preamble_wording.py",
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


def test_no_step_count_of_the_review_appears() -> None:
    """The review skill owns its step list, and a count written here goes stale. Preventive: the
    text that came before held none, so the scan is fired at planted shapes below."""
    for path in _WHOLE_FILE_SCANS:
        found = [match[0] for match in _STEP_COUNT.finditer(_read(path))]
        assert not found, f"{path.name} counts the review's steps: {found}"


def test_the_step_count_scan_sees_planted_shapes() -> None:
    flagged = (
        "Run it through the Skill tool, Steps 0 to 9, whatever the size of the task",
        "Step 0 through Step 9",
        "steps 0-9",
        f"Steps 0{_EN}9",
        "Steps 0 through 9",
    )
    clean = (
        "with the review's step list and the lessons result in it",
        "Step 3 writes a file",
        "Steps 3 to 9",
        "step 0 of the review",
        "Step 10",
        "Steps 0 to 90",
    )
    for text in flagged:
        assert _STEP_COUNT.search(text), f"the scan missed {text!r}"
    for text in clean:
        assert _STEP_COUNT.search(text) is None, f"the scan flagged {text!r}"


def test_a_missing_heading_fails_loudly() -> None:
    with pytest.raises(AssertionError):
        _skill_close_block("no lead here\n")
    with pytest.raises(AssertionError):
        _template_close_block("no heading here\n")
    with pytest.raises(AssertionError):
        _section("no heading here\n", _RULES_HEADING)
    with pytest.raises(AssertionError):
        _top_level_item("no item here\n", _CONTRACT_ITEM)


def test_the_old_path_scan_sees_a_planted_path_and_near_misses() -> None:
    """The scan is fired at a sentence that names the old path, spelled apart from the constant it
    looks for, and at near-misses: the sentence that took its place, and the two halves of the
    path far apart."""
    assert _names_old_path(_PLANTED_OLD_SENTENCE)
    assert _names_old_path(f"a line\n{_PLANTED_OLD_SENTENCE} More.\nand another")
    assert not _names_old_path(_SENTENCE_2A)
    assert not _names_old_path("a folder of preambles, and a file named host-rules.md")


def test_a_section_is_cut_by_level_and_fence_and_a_duplicate_fails_loudly() -> None:
    """The cut is fired at one planted document: a section ends at the next heading of its own
    level and not at a deeper one, a heading written inside a fence neither starts nor ends a
    section, and a heading that starts two sections is an error and not a pick of the first."""
    document = "\n".join(
        [
            "# Title",
            "",
            "## Rules",
            "- kept one",
            "```text",
            "## Rules",
            "# a fenced line",
            "```",
            "### Deeper",
            "- kept two",
            "",
            "## Next",
            "- left out",
            "",
        ]
    )
    section = _section(document, "## Rules")
    for kept in ("- kept one", "# a fenced line", "### Deeper", "- kept two"):
        assert kept in section, kept
    for left_out in ("## Next", "- left out"):
        assert left_out not in section, left_out
    moved = f"### 2a. Launch\nthe body\n### 2b. Peer\n{_SENTENCE_2A}\n"
    assert _SENTENCE_2A not in _section(moved, _LAUNCH_HEADING)
    with pytest.raises(AssertionError):
        _section(f"{document}\n## Rules\n- again\n", "## Rules")
    with pytest.raises(AssertionError):
        _section("```text\n## Rules\n```\n", "## Rules")


def test_an_item_ends_at_the_next_item_or_heading_and_a_duplicate_fails() -> None:
    """The item is fired at planted lists: it holds the paragraph that trails its block, it ends
    at the next numbered item, it ends at a heading when no item follows, and a lead on two lines
    is an error."""
    lead = "9. **The close block"
    followed_by_item = (
        "8. **Eight.** before\n"
        f"{lead}** a lead\n"
        "\n"
        "   > quoted\n"
        "\n"
        "   Step 4 writes a file: the paragraph that trails the block.\n"
        "10. **Ten.** belongs to the next item\n"
    )
    item = _top_level_item(followed_by_item, lead)
    for kept in ("> quoted", "Step 4 writes a file"):
        assert kept in item, kept
    for left_out in ("8. **Eight.**", "10. **Ten.**"):
        assert left_out not in item, left_out
    followed_by_heading = (
        f"{lead}** a lead\n   the body\n## A heading\n   after the heading\n"
    )
    item = _top_level_item(followed_by_heading, lead)
    assert "the body" in item
    for left_out in ("A heading", "after the heading"):
        assert left_out not in item, left_out
    with pytest.raises(AssertionError):
        _top_level_item(f"{followed_by_item}{lead}** again\n", lead)


def test_the_close_blocks_end_where_they_end_and_a_duplicate_fails_loudly() -> None:
    """The contract's block ends at the first line that is not quoted, and the template's block at
    its closing fence or at the next heading; a lead, or a heading, on two lines is an error."""
    contract = _planted_contract(cited=4)
    block = _skill_close_block(contract)
    assert len(_steps(block)) == 5
    assert "Step 4 writes a file" not in "\n".join(block)
    with pytest.raises(AssertionError):
        _skill_close_block(f"{contract}\n{contract}")
    fenced = f"```markdown\n{_TEMPLATE_CLOSE_HEADING}\n1. one\n2. two\n```\n\nRules of thumb:\n"
    assert _steps(_template_close_block(fenced)) == ["1. one", "2. two"]
    headed = f"{_TEMPLATE_CLOSE_HEADING}\n1. one\n\n## Paste line\n2. not a step of the block\n"
    assert _steps(_template_close_block(headed)) == ["1. one"]
    with pytest.raises(AssertionError):
        _template_close_block(f"{fenced}\n{fenced}")


def test_the_shipped_check_is_read_once_from_the_rules_section() -> None:
    once = f"{_RULES_HEADING}\n\n- the check is `{_BRACKET_FORM}`\n"
    assert _shipped_check(once).pattern == _BRACKET_FORM
    twice = f"{_RULES_HEADING}\n\n- `{_BRACKET_FORM}` and again `{_BRACKET_FORM}`\n"
    none = f"{_RULES_HEADING}\n\n- no check is given\n"
    outside = (
        f"## Paste line\n\n- `{_BRACKET_FORM}`\n\n{_RULES_HEADING}\n\n- no check\n"
    )
    for text in (twice, none, outside):
        with pytest.raises(AssertionError):
            _shipped_check(text)


def test_a_heading_that_only_contains_the_text_is_not_the_section_heading() -> None:
    """Placed before the real heading: a heading that holds the text in its middle is not a
    second start, and nor is a heading that begins with the first words of the real one (the
    shipped rules heading is not a prefix match for `## Rules of the road`)."""
    real = f"{_RULES_HEADING}\n\n- the rule\n"
    containing = f"### About the {_RULES_HEADING} below\n- a decoy\n\n"
    starting_alike = (
        "## Rules of the road\n- another decoy, `" + _BRACKET_FORM + "`\n\n"
    )
    for decoy in (containing, starting_alike):
        section = _section(f"{decoy}{real}", _RULES_HEADING)
        assert section == _section(real, _RULES_HEADING), decoy
        assert "decoy" not in section, decoy
        assert _shipped_check(f"{decoy}{real}- `{_BRACKET_FORM}`\n").pattern == (
            _BRACKET_FORM
        ), decoy


def test_a_line_that_only_contains_the_lead_is_not_the_item() -> None:
    """Placed before the real item: a paragraph that quotes the lead in passing and an item of
    another list that has the same number are not a second start, and the paragraph that cites
    the save step is still read from the real item."""
    item = _planted_contract(cited=4)
    quoting = f"A paragraph that quotes {_CONTRACT_ITEM}** in passing.\n\n"
    another_list = "9. **The ninth item of another list.**\n\n"
    for decoy in (quoting, another_list):
        assert _top_level_item(f"{decoy}{item}", _CONTRACT_ITEM) == _top_level_item(
            item, _CONTRACT_ITEM
        ), decoy
        assert _cited_step_problems(f"{decoy}{item}") == [], decoy


def test_a_heading_that_only_starts_like_the_close_heading_is_not_it() -> None:
    """Placed before the real heading: a longer heading that begins with the same words is not
    a second start, and its lines are not steps of the block."""
    real = f"{_TEMPLATE_CLOSE_HEADING}\n1. one\n2. two\n"
    longer = (
        f"{_TEMPLATE_CLOSE_HEADING}, second version\n1. not a step of the block\n\n"
    )
    assert _steps(_template_close_block(f"{longer}{real}")) == ["1. one", "2. two"]


def test_a_wrapped_line_that_starts_with_a_decimal_number_is_not_a_step() -> None:
    """A step that wraps onto a line starting `2.5 hours` is one step: a step starts at a
    number, a dot and a space."""
    block = [
        "1. one",
        "2. two, which runs for",
        "   2.5 hours before it stops",
        "3. three",
    ]
    assert _steps(block) == [
        "1. one",
        "2. two, which runs for 2.5 hours before it stops",
        "3. three",
    ]


def test_the_paste_line_lead_in_calls_the_compare_one_of_the_preconditions() -> None:
    """The paste line is compared by the delegate's preconditions and one of them does it: no
    precondition is the first one, which is a rank the brief does not give them."""
    section = _words(_section(_read(_TEMPLATE), _PASTE_HEADING))
    assert (
        "so that one of the delegate's preconditions can compare each with what it finds"
        in section
    ), "the paste line's lead-in does not say that one of the preconditions compares"


@pytest.mark.parametrize("key", _RETIRED_KEYS)
def test_a_retired_wording_is_gone_from_its_place(key: str) -> None:
    text, wording = _retired_wordings()[key]
    assert wording not in text, f"{key}: still says {wording!r}"


@pytest.mark.parametrize("key", sorted(_TOPIC_LIST_ENDS))
def test_a_list_of_the_preambles_topics_ends_with_the_size_stop_and_close_rules(
    key: str,
) -> None:
    """The worker preamble gained a section on size, stop and close, so each list of its topics
    names it last. Only the lists are read: the preamble is not."""
    place = _topic_list_places()[key]
    assert _SIZE_STOP_CLOSE in place, (
        f"{key}: the list does not name {_SIZE_STOP_CLOSE!r}"
    )
    assert _TOPIC_LIST_ENDS[key] in place, (
        f"{key}: the list does not end with {_TOPIC_LIST_ENDS[key]!r}"
    )


def test_a_bullet_is_cut_at_the_next_bullet_and_a_duplicate_lead_fails() -> None:
    text = "- **A lead.** one\n  wrapped on\n\n- **Another lead.** two\n"
    assert _bullet_starting(text, "- **A lead.**") == "- **A lead.** one wrapped on"
    assert _bullet_starting(text, "- **Another lead.**") == "- **Another lead.** two"
    with pytest.raises(AssertionError):
        _bullet_starting(f"{text}- **A lead.** again\n", "- **A lead.**")
    with pytest.raises(AssertionError):
        _bullet_starting(text, "- **A lead that is missing")


def test_the_skeleton_is_the_first_fenced_block_and_nothing_else() -> None:
    """Fired at a planted document: the headings inside the first block are headings of the
    skeleton, and what stands outside it or in a second block is not."""
    text = (
        "# Title\n\n```markdown\n## Standing rules\nthe list\n\n## Goal\nthe goal\n```\n\n"
        "## Standing rules\noutside the block\n\n```text\n## Standing rules\nsecond block\n```\n"
    )
    section = _section(_skeleton(text), _STANDING_HEADING)
    assert "the list" in section
    for left_out in ("the goal", "outside the block", "second block"):
        assert left_out not in section, left_out
    with pytest.raises(AssertionError):
        _skeleton("no fence here\n")
    with pytest.raises(AssertionError):
        _skeleton("```markdown\nnever closed\n")


# --- the sentence after the five steps ------------------------------------------------------------


@pytest.mark.parametrize("place", _PLACES)
def test_each_close_block_ends_with_the_hand_off_sentence(place: str) -> None:
    """Red before the change: neither block had a sentence after its five steps."""
    problems = _closing_problems(_close_steps(place), _tail(_close_block(place)))
    assert not problems, f"{place}: {problems}"


def test_the_two_closing_sentences_agree() -> None:
    skill = _tail(_close_block(_SKILL_PLACE))
    template = _tail(_close_block(_TEMPLATE_PLACE))
    assert skill and skill == template, (
        f"the closing sentences differ: SKILL.md {skill!r} against the template {template!r}"
    )


@pytest.mark.parametrize("place", _PLACES)
def test_the_closing_sentence_is_not_a_part_of_a_step(place: str) -> None:
    """Preventive: the text that came before had no such sentence, so the scan is fired at
    planted blocks in the next test."""
    assert _steps_holding_the_sentence(_close_steps(place)) == [], place


def test_the_closing_sentence_is_seen_glued_to_step_five_and_set_off_from_it() -> None:
    """Fired at planted blocks: the sentence set off by a blank line is in no step and is the
    tail; glued to step 5 with no blank line it is in step 5, the tail is empty and the sentence
    is reported missing."""
    sentence = " ".join(_closing_runs(5))
    steps = [
        "1. one",
        "2. two",
        "3. three",
        f"4. {_SAVE_STEP} (x).",
        f"5. {_SUMMARY_STEP}: five.",
    ]
    set_off = [*steps, "", sentence]
    glued = [*steps, sentence]
    assert _steps(set_off) == steps and _tail(set_off) == sentence
    assert _steps_holding_the_sentence(_steps(set_off)) == []
    assert _closing_problems(steps, _tail(set_off)) == []
    assert _steps(glued)[4] == f"{steps[4]} {sentence}"
    assert _steps_holding_the_sentence(_steps(glued)) == [5]
    assert _tail(glued) == ""
    assert _closing_problems(steps, _tail(glued)) == [_NO_SENTENCE]


def test_the_tail_is_what_follows_the_first_blank_line_after_a_step() -> None:
    """The cut is fired at planted blocks: a block with no steps and a block with no blank line
    have no tail, a lead line before the first step is not a step, and a second blank line does
    not start another tail."""
    assert _tail([]) == "" and _tail(["lead", "", "text"]) == ""
    assert _step_line_count(["lead", "", "text"]) == 3
    assert _tail(["1. one", "2. two"]) == ""
    assert _tail(["lead", "1. one", "", "", "text", "over two lines"]) == (
        "text over two lines"
    )
    assert _steps(["lead", "1. one", "wrapped", "", "text"]) == ["1. one wrapped"]


def test_every_run_of_the_closing_sentence_is_reported_when_it_goes() -> None:
    """Planted removal: each of the four runs cut out of the real sentence in turn is a fault,
    and so is an empty tail. A run the check could not see go would let the block lose it."""
    for place in _PLACES:
        steps = _close_steps(place)
        tail = _tail(_close_block(place))
        assert _closing_problems(steps, tail) == [], f"{place}: not right at the start"
        number = _numbered(steps, _SUMMARY_STEP)[0]
        for run in _closing_runs(number):
            assert run in tail, f"{place}: the run {run!r} is not in the sentence"
            cut = " ".join(tail.replace(run, "").split())
            assert _closing_problems(steps, cut) != [], (place, run)
        assert _closing_problems(steps, "") == [_NO_SENTENCE]


def test_the_step_the_sentence_names_follows_a_renumbering() -> None:
    """The step in `before step N` is the one that summarises, and the step before it saves into
    the handoff. Fired at planted steps: a sentence naming step 4 on the five steps, a sixth step
    inserted before the summary, and a block with no step that summarises."""
    steps = [
        "1. one",
        "2. two",
        "3. three",
        f"4. {_SAVE_STEP} (x).",
        f"5. {_SUMMARY_STEP}: five.",
    ]
    right = " ".join(_closing_runs(5))
    assert _closing_problems(steps, right) == []
    stale = _closing_problems(steps, " ".join(_closing_runs(4)))
    assert len(stale) == 1 and "before step 5" in stale[0], stale
    inserted = [*steps[:4], "5. A new step.", f"6. {_SUMMARY_STEP}: six."]
    assert len(_closing_problems(inserted, right)) == 2
    with pytest.raises(AssertionError):
        _closing_problems(steps[:4], right)


@pytest.mark.parametrize("place", _PLACES)
def test_a_rewrapped_closing_sentence_reads_the_same(place: str) -> None:
    """The sentence of each real block, re-wrapped at three widths and put back after the steps,
    is read as the same sentence, and the steps are still the same five. The wraps are real: the
    narrowest has more lines than the widest."""
    block = _close_block(place)
    expected = _tail(block)
    assert expected, f"{place}: the block has no sentence after its steps"
    kept = block[: _step_line_count(block)]
    rows: dict[int, list[str]] = {}
    for width in _REWRAP_WIDTHS:
        rows[width] = textwrap.wrap(
            expected, width=width, break_long_words=False, break_on_hyphens=False
        )
        planted = [*kept, "", *rows[width]]
        assert _tail(planted) == expected, f"{place} at {width}"
        assert _steps(planted) == _close_steps(place), f"{place} at {width}"
    assert len(rows[min(_REWRAP_WIDTHS)]) > len(rows[max(_REWRAP_WIDTHS)])


def test_the_template_the_sentence_names_is_one_the_kit_seeds() -> None:
    """Preventive: the sentence tells a worker to write from a file, so the scaffold must plan
    that path; a rename of the seeded template turns this red before it strands the sentence."""
    planned = {item.relative for item in scaffold.plan(load_manifest())}
    assert _HAND_OFF_TEMPLATE in planned, f"the scaffold plans no {_HAND_OFF_TEMPLATE}"


def test_the_human_facing_summary_is_the_hand_offs_own_section_said_again() -> None:
    """Red before the change: the rule called the summary a separate artifact from the handoff."""
    assert _SUMMARY_SECTION in _ADDED_SECTIONS, "the lint no longer adds that section"
    bullet = _summary_bullet(_read(_SKILL))
    lead = (
        f"{_SUMMARY_BULLET_LEAD} is the hand-off's `## {_SUMMARY_SECTION}`, said again "
        "as the closing message.**"
    )
    assert bullet.startswith(lead), bullet
    assert "separate artifact" not in bullet, "the retired wording is still there"
    assert f"{_LESS_OR_EQUAL}10 plain-language bullets" in bullet, "the cap is gone"


def test_the_summary_bullet_is_cut_from_its_own_item_and_a_duplicate_fails() -> None:
    """The cut is fired at a planted item: a bullet with a line that runs on is one folded line,
    a quoted line is not a bullet, the next item is not read, and a lead on no line or on two
    lines is an error."""
    item = (
        f"{_CONTRACT_ITEM}** paste it.\n\n"
        "   > - not a bullet\n\n"
        "   - **Answer first.** one\n"
        "     wrapped on.\n"
        f"   {_SUMMARY_BULLET_LEAD} is X.** two\n"
        "     wrapped on.\n"
        f"10. **Next.**\n   {_SUMMARY_BULLET_LEAD} is not read.** three\n"
    )
    assert _item_bullets(_top_level_item(item, _CONTRACT_ITEM)) == [
        "- **Answer first.** one wrapped on.",
        f"{_SUMMARY_BULLET_LEAD} is X.** two wrapped on.",
    ]
    assert _summary_bullet(item) == f"{_SUMMARY_BULLET_LEAD} is X.** two wrapped on."
    with pytest.raises(AssertionError):
        _summary_bullet(item.replace(_SUMMARY_BULLET_LEAD, "- **Another lead", 1))
    twice = item.replace(
        "   - **Answer first.**", f"   {_SUMMARY_BULLET_LEAD} again.**"
    )
    with pytest.raises(AssertionError):
        _summary_bullet(twice)
