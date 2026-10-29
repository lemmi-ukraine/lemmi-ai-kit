"""The consolidator family's text says what it must, and the scans that say so can see.

Three skills form one drain: `learning-consolidator` (its SKILL.md, its reference and the
`drain_audit.py` script), `consolidation-critic` and `hypothesis-validator`. They were
written by different sessions and nothing pinned their text, so each of these shipped:

* a printed command that rendered `python python`, and a step that said "adjudicate every
  flagged row" twice in one sentence;
* three steps that printed a shell line naming the learnings buffer (the previous drain's
  heading count, the snapshot copy, the critic's recovery read). A project's own rules may
  keep that name off session shell lines, a stricter line than the kit's guard draws (it
  matches only shapes that rewrite or delete the buffer), so the byte copies are an
  operator step;
* a critic check (C1) that ran the landing audit without the base ref its reference calls
  mandatory, and so measured the wrong thing;
* a hypothesis validator named only AFTER the plan's approval stop, so its verdicts could
  never be part of the plan the operator approves, and a meta-synthesis step that said
  "update" a marker line that does not exist until somebody adds it, without saying what
  the ledger lint reads from that line or does when it is missing or wrong;
* a gate record that the guard requires (a dated file of at least 200 characters) and no
  skill documented, and a recommendation lifecycle that read a report the retrospective
  declares gitignored scratch.

Every rule below is a function over a string, so `test_every_rule_sees_its_planted_positive`
can fire it at text that carries the defect before its silence on the real files is
trusted, and `test_the_scan_covers_the_three_skills` states the scan surface in numbers.
The tests that assert a fact about the text each fail on the text they replaced.

The command-form rule checks the printed FORM only. Parsing every printed command with the
support CLI's own parser is a separate test, written once the packs are merged.
"""

import ast
import re
import shlex
from pathlib import Path

from lemmi_ai_kit import checks

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _REPO_ROOT / "plugins" / "core" / "skills"
_CONSOLIDATOR = _SKILLS / "learning-consolidator"
_CRITIC = _SKILLS / "consolidation-critic"
_VALIDATOR = _SKILLS / "hypothesis-validator"
_DIRS = (_CONSOLIDATOR, _CRITIC, _VALIDATOR)

_SKILL = _CONSOLIDATOR / "SKILL.md"
_REFERENCE = _CONSOLIDATOR / "references" / "consolidation-actions.md"
_SCRIPT = _CONSOLIDATOR / "scripts" / "drain_audit.py"

# Every suffix a text file of these skills has. Another suffix fails the surface test, so a
# new kind of file is a decision made here and not a silent gap in what is read.
_TEXT_SUFFIXES: frozenset[str] = frozenset({".md", ".py"})

# Named so the scan cannot quietly stop covering the files that carried the defects.
_MUST_BE_SCANNED: tuple[str, ...] = (
    "learning-consolidator/SKILL.md",
    "learning-consolidator/references/consolidation-actions.md",
    "learning-consolidator/scripts/drain_audit.py",
    "consolidation-critic/SKILL.md",
    "hypothesis-validator/SKILL.md",
)

_STOP = re.compile(r"\*\*STOP and wait for user approval")
_HEADING = re.compile(r"^(#{1,6})\s+\S")


def _files() -> list[Path]:
    return sorted(
        path
        for directory in _DIRS
        for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _markdown_files() -> list[Path]:
    return [path for path in _files() if path.suffix == ".md"]


def _relative(path: Path) -> str:
    return path.relative_to(_SKILLS).as_posix()


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collapsed(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the shell script it holds, not a heading.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    return "\n".join(found)


def _paragraph(text: str, lead: str) -> str:
    """The blank-line-delimited paragraph that starts with `lead`, or an empty string."""
    for block in re.split(r"\n\s*\n", text):
        if block.lstrip().startswith(lead):
            return block
    return ""


def _list_item(text: str, lead: str) -> str:
    """A list item: its first line starts with `lead`, and it runs through the indented lines
    and blank lines that follow, to the next line that starts in column 0."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(lead):
            item = [line]
            for follow in lines[index + 1 :]:
                if follow.strip() and not follow.startswith((" ", "\t")):
                    break
                item.append(follow)
            return "\n".join(item)
    return ""


def _fenced_blocks(text: str) -> list[tuple[str, list[str]]]:
    """(info string, lines) for every fenced block, the fence lines themselves left out."""
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    info = ""
    for line in text.split("\n"):
        if _is_fence(line):
            if current is None:
                current = []
                info = line.lstrip()[3:].strip().lower()
            else:
                blocks.append((info, current))
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def _fenced_lines(text: str) -> list[str]:
    return [line for _, lines in _fenced_blocks(text) for line in lines]


def _prose(text: str) -> str:
    """The text with fenced blocks blanked, so only prose and its inline code remains."""
    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
            out.append("")
        else:
            out.append("" if in_fence else line)
    return "\n".join(out)


def _inline_spans(text: str) -> list[str]:
    """Inline code spans of the prose; a span that wraps a line is joined into one.

    Spans are paired within a blank-line-delimited block, so one stray backtick cannot
    misalign every span after it.
    """
    spans: list[str] = []
    for block in re.split(r"\n\s*\n", _prose(text)):
        spans += [_collapsed(s).strip() for s in re.findall(r"`([^`]+)`", block)]
    return spans


# --- rule: a word said twice in a row ------------------------------------------------

_DOUBLED_WORD = re.compile(r"\b([A-Za-z][A-Za-z']*) \1\b", re.IGNORECASE)


def _doubled_words(text: str) -> list[str]:
    return [m.group(0) for m in _DOUBLED_WORD.finditer(_collapsed(text))]


# --- rule: a phrase said twice in one breath -----------------------------------------


def _said_twice_in_one_breath(text: str, phrase: str, within_words: int = 30) -> bool:
    flat = _collapsed(text).lower()
    starts = [m.start() for m in re.finditer(re.escape(phrase.lower()), flat)]
    return any(
        len(flat[first + len(phrase) : second].split()) < within_words
        for first, second in zip(starts, starts[1:], strict=False)
    )


# --- rule: no printed shell line names the buffer ------------------------------------

# The buffer as a command names it: the whole file name, in any case. The snapshot
# (`learnings-pre-drain-<date>.md`) is another file, and a table cell that names a cursor
# rule of the same name is never a command.
_BUFFER = re.compile(r"(?<![\w.\-])learnings\.md(?![\w.\-~])", re.IGNORECASE)

_SHELL_WORDS: frozenset[str] = frozenset(
    {
        "cp",
        "cmp",
        "git",
        "grep",
        "cat",
        "sed",
        "awk",
        "mv",
        "rm",
        "head",
        "tail",
        "wc",
        "diff",
        "tee",
        "xargs",
        "echo",
        "printf",
        "python",
        "python3",
        "uv",
    }
)
_SHELL_FENCES: frozenset[str] = frozenset(
    {"bash", "sh", "shell", "zsh", "console", "powershell", "pwsh"}
)

# The two shapes the request named. They are a sharper net than the rule above (they also
# fire in prose), so a reworded step cannot put them back.
_NAMED_SHAPES: tuple[str, ...] = ("cp .ai/learnings.md", ":.ai/learnings.md")


def _first_command_word(line: str) -> str:
    for word in line.split():
        if not re.fullmatch(r"[A-Za-z_]\w*=\S*", word):
            return word
    return ""


def _printed_shell_lines(text: str) -> list[str]:
    """Lines of a shell fence, command-shaped lines of any other bare fence, and inline code
    that opens with a shell command word. A `markdown` fence is a template, not a command."""
    lines: list[str] = []
    for info, block in _fenced_blocks(text):
        for line in (raw.strip() for raw in block):
            if not line or line.startswith("#"):
                continue
            if info in _SHELL_FENCES or (
                not info and _first_command_word(line) in _SHELL_WORDS
            ):
                lines.append(line)
    lines += [s for s in _inline_spans(text) if _first_command_word(s) in _SHELL_WORDS]
    return lines


def _buffer_on_a_shell_line(text: str) -> list[str]:
    hits = [line for line in _printed_shell_lines(text) if _BUFFER.search(line)]
    hits += [shape for shape in _NAMED_SHAPES if shape in text]
    return hits


# --- rule: every printed audit command passes a base ref -----------------------------


def _audit_invocations(text: str) -> list[list[str]]:
    """Each printed `drain_audit.py` command with operands, as its tokens after the script."""
    logical: list[str] = []
    pending = ""
    for line in _fenced_lines(text):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
            continue
        logical.append(pending + stripped)
        pending = ""
    logical += _inline_spans(text)
    invocations: list[list[str]] = []
    for command in logical:
        if "drain_audit.py" not in command:
            continue
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        for index, token in enumerate(tokens):
            if token.endswith("drain_audit.py"):
                operands = tokens[index + 1 :]
                if operands:  # a bare mention of the script is not a command
                    invocations.append(operands)
                break
    return invocations


def _without_a_ref(operands: list[str]) -> bool:
    positional = [token for token in operands if not token.startswith("-")]
    if "--current-contents" in operands:
        return len(positional) < 1
    return len(positional) < 2


def _audit_commands_missing_a_ref(text: str) -> list[list[str]]:
    return [ops for ops in _audit_invocations(text) if _without_a_ref(ops)]


# --- rule: the validator is named before the Phase 3 stop ----------------------------

_STEPS_1_TO_4 = re.compile(r"Steps?\s+1\s*(?:-|–|to)\s*4")
_STEPS_6_AND_8 = re.compile(r"Steps?\s+6\s+and\s+8")


def _hypothesis_flow_gaps(skill: str) -> list[str]:
    stop = _STOP.search(skill)
    if stop is None:
        return ["the Phase 3 STOP line is gone, so the order cannot be read"]
    gaps: list[str] = []
    phase_2 = _section(skill, "### Phase 2")
    plan = _section(skill, "### Phase 3")
    phase_65 = _collapsed(_section(skill, "### Phase 6.5"))
    if "hypothesis-validator" not in phase_2:
        gaps.append("Phase 2 does not name hypothesis-validator")
    first = skill.find("hypothesis-validator")
    if first == -1 or first > stop.start():
        gaps.append("hypothesis-validator is first named after the Phase 3 STOP")
    if not _STEPS_1_TO_4.search(phase_2):
        gaps.append("Phase 2 does not say the validator's Steps 1 to 4 run there")
    if not re.search(r"Step\s+7", phase_2):
        gaps.append("Phase 2 does not say the validator's Step 7 line runs there")
    if not re.search(r"(?i)\bwriting\s+nothing\b|\bnothing\s+is\s+written\b", phase_2):
        gaps.append("Phase 2 does not say the validator writes nothing before the gate")
    if "#hypothesis-lifecycle-in-the-plan" not in phase_2:
        gaps.append("Phase 2 does not point at where a due meta-synthesis is found")
    if not re.search(r"(?i)hypothesis\s+verdicts?", plan):
        gaps.append("the Phase 3 plan has no hypothesis verdict table")
    if not _STEPS_6_AND_8.search(phase_65):
        gaps.append("Phase 6.5 does not say it keeps the validator's Steps 6 and 8")
    if "Fold its proposed status changes into the consolidation plan" in phase_65:
        gaps.append("Phase 6.5 still folds the proposals into a plan already approved")
    return gaps


def _validator_split_gaps(validator: str) -> list[str]:
    """The split must be said where the instruction is read: the frontmatter description
    also names the steps, and would satisfy this rule with the body paragraph deleted."""
    section = _section(validator, "## When This Skill Activates")
    if not section:
        return ["the 'When This Skill Activates' section is gone"]
    flat = _collapsed(section)
    gaps: list[str] = []
    if not _STEPS_1_TO_4.search(flat):
        gaps.append("does not say Steps 1 to 4 run in the consolidator's Phase 2")
    if not re.search(r"(?i)end of (?:its |the consolidator's )?Phase 2", flat):
        gaps.append("does not say those steps run at the end of Phase 2")
    if not _STEPS_6_AND_8.search(flat):
        gaps.append("does not say Phase 6.5 keeps Steps 6 and 8")
    if not re.search(r"(?i)\bnothing\s+is\s+written\b", flat):
        gaps.append("does not say nothing is written before the gate")
    if not re.search(r"\bDORMANT\b", flat):
        gaps.append("does not say where Step 2's DORMANT marks wait for the approval")
    return gaps


def _integration_row_gaps(validator: str) -> list[str]:
    """The consolidator's row of the Integration Points table names both of its calls."""
    section = _section(validator, "## Integration Points")
    row = next(
        (
            line
            for line in section.split("\n")
            if line.startswith("| `learning-consolidator`")
        ),
        "",
    )
    if not row:
        return ["the Integration Points table has no learning-consolidator row"]
    gaps: list[str] = []
    if not re.search(r"Phase\s+2\b", row):
        gaps.append("the row does not name the call at the end of Phase 2")
    if not re.search(r"Phase\s+6\.5\b", row):
        gaps.append("the row does not name the call in Phase 6.5")
    return gaps


# --- rule: meta-synthesis item 5 adds a marker that may not exist --------------------


def _item_5_gaps(validator: str) -> list[str]:
    section = _section(validator, "## Meta-Synthesis")
    match = re.search(r"(?ms)^5\.\s+(.*?)(?=^\S|\Z)", section)
    if match is None:
        return ["the Meta-Synthesis section has no item 5"]
    item = _collapsed(match.group(1))
    gaps: list[str] = []
    if not re.search(r"(?i)\badd\b", item):
        gaps.append("item 5 does not say to ADD the marker line")
    if not re.search(r"(?i)\bhas none\b", item):
        gaps.append("item 5 does not say when to add it (the header has none)")
    if not re.search(r"(?i)\bupdate\b", item):
        gaps.append("item 5 no longer says to update a marker that exists")
    return gaps


# --- rule: the marker line is the one the ledger lint reads ----------------------------

# The ledger lint's reader of the marker, mirrored while the support CLI in this tree has
# none: the first line outside a fence that opens with the bold label (a blockquote `>`
# before it is allowed), with its count taken from `N terminal verdicts covered` after the
# label. Once `checks.read_meta_synthesis_marker` exists the lint's own reader is asked
# instead, so the text is held to the code and not to this copy of it.
_MARKER_MIRROR = re.compile(r"^\s*(?:>\s*)?\*\*Last meta-synthesis:?\*\*:?(.*)$")
_COVERED_MIRROR = re.compile(r"(\d+)\s+terminal\s+verdicts?\s+covered")

# What the lint does with a marker that is missing, unreadable or ahead of the ledger: each
# case is a NOTE, and the validator must say which.
_MARKER_CASES: dict[str, re.Pattern[str]] = {
    "what a missing marker counts as (0 covered)": re.compile(
        r"(?i)\bmissing\b[^.]{0,80}\b0\s+covered\b"
    ),
    "what an unreadable marker does (the due check does not run)": re.compile(
        r"(?i)\bunreadable\b[^.]{0,160}\bdue\s+check\b"
    ),
    "what a marker above the count is (ahead of the ledger)": re.compile(
        r"(?i)\babove\s+the\s+count\b[^.]{0,160}\bahead\s+of\s+the\s+ledger\b"
    ),
    "that every marker NOTE is never a finding": re.compile(
        r"(?i)\bnever\s+a\s+finding\b"
    ),
}


def _lint_reads_marker(line: str) -> int | None:
    """The covered count the ledger lint reads from `line`, or None when it reads none."""
    reader = getattr(checks, "read_meta_synthesis_marker", None)
    if callable(reader):
        covered = getattr(reader(line + "\n"), "covered", None)
        return covered if isinstance(covered, int) else None
    match = _MARKER_MIRROR.match(line)
    if match is None:
        return None
    count = _COVERED_MIRROR.search(match.group(1))
    return int(count.group(1)) if count else None


def _filled(template: str, covered: int) -> str:
    """A marker template with `{N}` set to `covered` and every other placeholder filled."""
    return re.sub(r"\{[^}]*\}", "x", template.replace("{N}", str(covered)))


def _marker_gaps(validator: str) -> list[str]:
    section = _section(validator, "## Meta-Synthesis")
    if not section:
        return ["the Meta-Synthesis section is gone"]
    match = re.search(r"(?ms)^5\.\s+(.*?)(?=^\S|\Z)", section)
    item = match.group(1) if match else ""
    examples = [span for span in _inline_spans(item) if "Last meta-synthesis" in span]
    gaps: list[str] = []
    if not examples:
        gaps.append("item 5 gives no marker line")
    unread = [span for span in examples if _lint_reads_marker(_filled(span, 12)) != 12]
    if unread:
        gaps.append(
            f"the ledger lint reads no count from item 5's marker line: {unread}"
        )
    flat = _collapsed(section)
    gaps += [
        f"does not say {case}"
        for case, pattern in _MARKER_CASES.items()
        if not pattern.search(flat)
    ]
    return gaps


# --- rule: the recommendation lifecycle reads the changelog entry --------------------


def _lifecycle_gaps(skill: str) -> list[str]:
    paragraph = _collapsed(_paragraph(skill, "**Recommendation lifecycle**"))
    if not paragraph:
        return ["the Recommendation lifecycle paragraph is gone"]
    gaps: list[str] = []
    if not re.search(r"(?i)changelog\s+entry", paragraph):
        gaps.append("does not name the retrospective's changelog entry")
    if not re.search(r"(?i)gitignored|not durable|absent|lost", paragraph):
        gaps.append("does not say when the report is not durable or is absent")
    if not re.search(r"(?i)\bnot\s+durable\b", paragraph):
        gaps.append(
            "falls back only when the report is absent, not when it is not durable"
        )
    if not re.search(r"(?i)\bproposals?\b", paragraph):
        gaps.append("does not say the recommendations are kept as proposals")
    return gaps


# --- rule: the gate record is documented with its day and length rules ---------------

_GATE_FACTS: dict[str, re.Pattern[str]] = {
    "the record path": re.compile(
        r"\.ai/consolidation-gates/<YYYY-MM-DD>-plan-approved\.md"
    ),
    "the local calendar day": re.compile(r"(?i)\blocal\s+calendar\s+day\b"),
    # The day rule's negative half. Without it, "an earlier day also counts" passed.
    "an earlier day does not count": re.compile(
        r"(?i)\bearlier\s+day\s+does\s+not\s+count\b"
    ),
    "the same-day consequence": re.compile(r"(?i)\bsame\s+calendar\s+day\b"),
    "the 200-character floor": re.compile(r"\b200\s+characters\b"),
    "characters, not bytes": re.compile(r"(?i)\bnot\s+bytes\b"),
    "the plan itself, not a stub": re.compile(r"(?i)\bnot\s+a\s+stub\b"),
    "written only after approval": re.compile(
        r"(?i)\bonly\s+after\s+the\s+operator['’]s\s+approval\b"
    ),
    "appends never blocked": re.compile(r"(?i)\bappends?\b[^.]{0,80}never\s+blocked"),
    "forgeable": re.compile(r"(?i)\bforgeable\b"),
    "a written claim, not enforcement": re.compile(r"(?i)\bwritten\s+claim\b"),
}


def _gate_record_gaps(section: str) -> list[str]:
    flat = _collapsed(section)
    return [name for name, pattern in _GATE_FACTS.items() if not pattern.search(flat)]


# --- rule: every printed support-CLI command has the one canonical form --------------

_CANONICAL = re.compile(
    r'^uv run --no-project --directory "\$\{CLAUDE_PLUGIN_ROOT\}/src" '
    r"python -B -m lemmi_ai_kit "
    r'(?:lint|audit-skills)\b.*--project "<project root>"$'
)
_ENV_PREFIX = re.compile(r"\b(?:PYTHONPATH|PYTHONDONTWRITEBYTECODE)=")


def _kit_command_problems(text: str) -> list[str]:
    problems: list[str] = []
    candidates = [line.strip() for line in _fenced_lines(text)] + _inline_spans(text)
    for command in candidates:
        if "-m lemmi_ai_kit" in command and not _CANONICAL.match(command):
            problems.append(command)
    problems += [m.group(0) for m in _ENV_PREFIX.finditer(text)]
    return problems


# --- rule: exit 1 is said to mean rows to adjudicate ---------------------------------

_EXIT_ONE = re.compile(r"(?i)exit\s+1\s+means\s+rows\s+to\s+adjudicate")

# Exit 0 of the current-contents scan is an upper bound: a gate that reads it as clean
# reads the unsound scan as the sound one.
_UNSOUND_ZERO = re.compile(
    r"(?i)under\s+--current-contents,?\s+(?:an\s+)?exit\s+0\s+is\s+an\s+upper\s+bound"
)


# --- the tests -----------------------------------------------------------------------


def test_the_scan_covers_the_three_skills() -> None:
    """The scan surface in numbers: every file of the three skills is read, none skipped."""
    everything = _files()
    unread = [_relative(p) for p in everything if p.suffix not in _TEXT_SUFFIXES]
    assert not unread, (
        f"{len(unread)} of {len(everything)} files of the three skills have a suffix this "
        f"test does not read: {unread}. Add the suffix to _TEXT_SUFFIXES if it is text."
    )
    names = {_relative(p) for p in everything}
    missing = [name for name in _MUST_BE_SCANNED if name not in names]
    assert not missing, f"the scan of {len(names)} files does not contain {missing}"
    for directory in _DIRS:
        assert (directory / "SKILL.md").is_file(), f"{directory.name} has no SKILL.md"
    assert len(_markdown_files()) < len(everything), (
        "no non-markdown file is in the scan"
    )


def test_no_file_of_the_three_skills_says_a_word_twice_in_a_row() -> None:
    """Red before the fix: the cadence guard printed `python python -m ...`."""
    offenders = {
        _relative(p): hits for p in _files() if (hits := _doubled_words(_text(p)))
    }
    assert not offenders, f"doubled words: {offenders}"


def test_the_landing_step_does_not_say_adjudicate_every_flagged_row_twice() -> None:
    """Red before the fix: Phase 5 step 6 said it twice, the second time after an `and`."""
    step_6 = _list_item(_text(_SKILL), "6. **Verify LANDING")
    assert step_6, "Phase 5 step 6 (Verify LANDING) is gone from the consolidator"
    assert "adjudicate every flagged row" in _collapsed(step_6), (
        "step 6 no longer tells the reader to adjudicate every flagged row"
    )
    assert not _said_twice_in_one_breath(step_6, "adjudicate every flagged row")


def test_no_printed_shell_line_names_the_buffer() -> None:
    """Red before the fix: the previous-drain count, the snapshot copy and the critic's
    recovery read each printed a shell line that named the buffer."""
    offenders = {
        _relative(p): hits
        for p in _markdown_files()
        if (hits := _buffer_on_a_shell_line(_text(p)))
    }
    assert not offenders, (
        "printed shell lines that name the learnings buffer (the operator makes these "
        f"copies and reads in their own terminal):\n{offenders}"
    )


def test_the_buffer_steps_are_still_described_as_operator_steps() -> None:
    """Positive control for the absence check above: deleting the three steps would also
    leave no shell line that names the buffer. The text must still say who does them, and
    which routes a session may use on the buffer instead."""
    section = _collapsed(_section(_text(_REFERENCE), "## Operator Steps"))
    assert section, "the reference has no 'Operator Steps' section"
    for name, pattern in {
        "the operator's own terminal": r"(?i)operator.{0,200}own terminal",
        "Grep in count mode": r"Grep in count mode",
        "Read with offset and limit": r"Read with offset and limit",
        "Edit appending after the last entry": r"Edit.{0,40}appending",
    }.items():
        assert re.search(pattern, section), f"Operator Steps does not name {name}"
    phase_5 = _collapsed(_section(_text(_SKILL), "### Phase 5"))
    assert re.search(r"(?i)operator.{0,200}own terminal", phase_5), (
        "Phase 5 no longer makes the snapshot an operator step"
    )
    c1 = _collapsed(_section(_text(_CRITIC / "SKILL.md"), "### C1"))
    assert re.search(r"(?i)operator.{0,200}own terminal", c1), (
        "C1 no longer makes the recovery read an operator step"
    )


def test_the_operator_route_is_stated_for_every_project() -> None:
    """Red before the fix: Operator Steps made the route conditional ("Where the project's own
    rules ... keep the buffer path off session shell lines, the operator makes each copy"),
    while Phase 1, Phase 5, the snapshot section and C1 state it with no condition, and a
    project without such a rule was described nowhere."""
    section = _collapsed(_section(_text(_REFERENCE), "## Operator Steps"))
    assert section, "the reference has no 'Operator Steps' section"
    gaps = [
        name
        for name, pattern in {
            "that the route holds in every project": r"(?i)\bin every project\b",
            "that a project without such a rule takes the same route": (
                r"(?i)\bwithout such a rule\b[^.]{0,80}\bsame route\b"
            ),
        }.items()
        if not re.search(pattern, section)
    ]
    assert not gaps, f"Operator Steps does not say {gaps}"
    conditional = re.search(
        r"(?i)\bwhere the project's own rules\b[^.]{0,200}\bthe operator makes\b",
        section,
    )
    assert conditional is None, (
        f"Operator Steps still makes the operator route conditional: {conditional}"
    )


def test_every_printed_landing_audit_command_passes_a_base_ref() -> None:
    """Red before the fix: C1 of the critic passed the snapshot alone."""
    offenders = {
        _relative(p): ops
        for p in _markdown_files()
        if (ops := _audit_commands_missing_a_ref(_text(p)))
    }
    assert not offenders, (
        f"printed drain_audit.py commands with no base ref: {offenders}"
    )


def test_c1_prints_the_landing_audit_with_both_ref_cases() -> None:
    """Red before the fix. C1 takes the reference's two ref cases, and says what exit 1 is."""
    c1 = _section(_text(_CRITIC / "SKILL.md"), "### C1")
    assert c1, "C1 is gone from the critic"
    invocations = _audit_invocations(c1)
    assert len(invocations) >= 2, (
        f"C1 prints {len(invocations)} audit commands; it must print one for each of the "
        "two ref cases (promotions uncommitted: HEAD; committed: the commit before them)"
    )
    refs = {ops[-1] for ops in invocations}
    assert "HEAD" in refs and any(ref.endswith("~1") for ref in refs), refs
    assert _EXIT_ONE.search(_collapsed(c1)), "C1 does not say what exit 1 means"


def test_exit_one_is_said_to_mean_rows_to_adjudicate_where_the_audit_is_run() -> None:
    """Red before the fix: nothing said what the new exit code 1 is."""
    where = {
        "SKILL.md Phase 5 step 6": _list_item(_text(_SKILL), "6. **Verify LANDING"),
        "the reference's Drain Landing Audit": _section(
            _text(_REFERENCE), "## Drain Landing Audit"
        ),
    }
    missing = [
        name for name, text in where.items() if not _EXIT_ONE.search(_collapsed(text))
    ]
    assert not missing, f"'exit 1 means rows to adjudicate' is missing from {missing}"


def test_the_script_docstring_states_the_flag_and_the_exit_code_contract() -> None:
    """Red before the fix: the docstring had no flag and no exit-code contract."""
    docstring = ast.get_docstring(ast.parse(_text(_SCRIPT))) or ""
    flat = _collapsed(docstring)
    assert "--current-contents" in flat, "the module docstring does not name the flag"
    assert re.search(r"(?i)exit codes", flat), "the module docstring has no exit codes"
    assert _EXIT_ONE.search(flat), "the module docstring does not say what exit 1 means"
    assert _UNSOUND_ZERO.search(flat), (
        "the module docstring reads exit 0 of the current-contents scan as clean"
    )


def test_the_validator_runs_before_the_phase_3_stop() -> None:
    """Red before the fix: it was first named in Phase 6.5, after the approval stop."""
    gaps = _hypothesis_flow_gaps(_text(_SKILL))
    assert not gaps, f"learning-consolidator SKILL.md: {gaps}"


def test_the_validator_text_says_it_is_split_around_the_approval_gate() -> None:
    """Red before the fix: it said it was invoked from Phase 6.5 and nothing else."""
    gaps = _validator_split_gaps(_text(_VALIDATOR / "SKILL.md"))
    assert not gaps, f"hypothesis-validator SKILL.md: {gaps}"


def test_meta_synthesis_item_5_adds_the_marker_line() -> None:
    """Red before the fix: item 5 said "Update the header marker" of a line nobody added."""
    gaps = _item_5_gaps(_text(_VALIDATOR / "SKILL.md"))
    assert not gaps, f"hypothesis-validator Meta-Synthesis: {gaps}"


def test_meta_synthesis_gives_the_marker_line_the_lint_reads_and_its_notes() -> None:
    """Red before the fix: the section named the marker but not what the lint does when the
    line is missing, unreadable or ahead of the ledger. The marker line item 5 gives must
    yield its count to the ledger lint's reader once its placeholders are filled."""
    gaps = _marker_gaps(_text(_VALIDATOR / "SKILL.md"))
    assert not gaps, f"hypothesis-validator Meta-Synthesis: {gaps}"


def test_the_validator_integration_row_names_both_of_its_calls() -> None:
    """Red before the fix: the consolidator's row still said Phase 6.5 alone."""
    gaps = _integration_row_gaps(_text(_VALIDATOR / "SKILL.md"))
    assert not gaps, f"hypothesis-validator Integration Points: {gaps}"


def test_phase_6_5_step_6_writes_every_row_the_plan_approved() -> None:
    """Red before the fix: Phase 6.5 named only the verdicts and their Resolution line, while
    the validator's Step 6 also writes the interim `Validation notes:` and DORMANT marks that
    Phase 2 held back, so a reader of the consolidator's list dropped them."""
    phase_65 = _section(_text(_SKILL), "### Phase 6.5")
    step_6 = _collapsed(_list_item(phase_65, "1. **Step 6**"))
    assert step_6, "Phase 6.5 has no Step 6 item"
    missing = [
        name
        for name, pattern in {
            "only the approved rows": r"(?i)\bonly the approved\b",
            "the verdicts' Resolution line": r"\bResolution\b",
            "the interim Validation notes": r"\bValidation notes\b",
            "the DORMANT marks": r"\bDORMANT\b",
        }.items()
        if not re.search(pattern, step_6)
    ]
    assert not missing, f"Phase 6.5's Step 6 does not write {missing}"


def test_the_recommendation_lifecycle_falls_back_to_the_changelog_entry() -> None:
    """Red before the fix: it read a report the retrospective declares gitignored scratch."""
    gaps = _lifecycle_gaps(_text(_SKILL))
    assert not gaps, f"learning-consolidator Recommendation lifecycle: {gaps}"


def test_the_gate_record_is_documented_once_with_its_day_and_length_rules() -> None:
    """Red before the fix: no skill said what the learnings guard requires before a drain."""
    section = _section(_text(_REFERENCE), "## Gate Record")
    assert section, "the reference has no 'Gate Record' section"
    gaps = _gate_record_gaps(section)
    assert not gaps, f"the Gate Record section does not state: {gaps}"

    elsewhere = [
        _relative(p)
        for p in _markdown_files()
        if p != _REFERENCE
        and _GATE_FACTS["the 200-character floor"].search(_collapsed(_text(p)))
    ]
    assert not elsewhere, (
        f"the length rule is restated outside its one home: {elsewhere}"
    )


def test_phase_3_points_at_the_gate_record_after_its_stop() -> None:
    """Red before the fix: Phase 3 ended at the STOP and recorded nothing."""
    plan = _section(_text(_SKILL), "### Phase 3")
    stop = _STOP.search(plan)
    assert stop is not None, "Phase 3 has no STOP line"
    after = _collapsed(plan[stop.end() :])
    assert re.search(r"(?i)gate record", after), (
        "nothing after the STOP names the gate record"
    )
    assert "references/consolidation-actions.md" in after, "the pointer has no link"


def test_a_dry_run_stops_before_the_gate_record_is_written() -> None:
    """Red before the fix: the gate-record write came first and the dry-run stop after it,
    so an approved dry run wrote `.ai/consolidation-gates/<date>-plan-approved.md`, against
    `--dry-run` ("do not modify any files") and the validator's "a dry run ... writes none"."""
    plan = _section(_text(_SKILL), "### Phase 3")
    stop = _STOP.search(plan)
    assert stop is not None, "Phase 3 has no STOP line"
    after = _collapsed(plan[stop.end() :])
    dry_run = re.search(r"(?i)`--dry-run` was specified, stop here", after)
    record = re.search(r"(?i)\bgate record\b", after)
    assert dry_run is not None, "nothing after the STOP stops a dry run"
    assert record is not None, "nothing after the STOP names the gate record"
    assert dry_run.start() < record.start(), (
        "a dry run reaches the gate-record write before its stop"
    )


def test_the_critic_reads_the_gate_record_the_reference_says_it_audits() -> None:
    """Red before the fix: the reference said the critic audits the record, and no input or
    check of the critic read it."""
    record = _section(_text(_REFERENCE), "## Gate Record")
    assert "consolidation-critic" in record, (
        "the Gate Record no longer names its auditor"
    )
    critic = _text(_CRITIC / "SKILL.md")
    inputs = _section(critic, "## Inputs")
    assert ".ai/consolidation-gates/" in inputs, (
        "the critic's inputs omit the gate record"
    )
    c1 = _collapsed(_section(critic, "### C1"))
    assert re.search(r"(?i)\bgate\s+record\b", c1), "C1 does not check the gate record"


def test_every_printed_support_cli_command_has_the_one_canonical_form() -> None:
    """Red before the fix: four commands carried an environment assignment, two were the
    bare module form, and none passed `--project` (which `uv --directory` makes mandatory).
    This pins the printed FORM; parsing each with the CLI's own parser is a later test."""
    offenders = {
        _relative(p): problems
        for p in _markdown_files()
        if (problems := _kit_command_problems(_text(p)))
    }
    assert not offenders, f"support-CLI commands off the canonical form: {offenders}"


def test_every_rule_sees_its_planted_positive() -> None:
    """A guard never shown to fail has not been shown to work.

    Each rule is fired at text that carries its defect (taken from the text it replaced,
    including a wrapped line) and at text that does not, so the clean results on the real
    files cannot be a probe that sees nothing.
    """
    assert _doubled_words("wraps as (`python\n   python -m lemmi_ai_kit x`)")
    assert not _doubled_words("run `python -m lemmi_ai_kit x` and then python")

    twice = "then adjudicate every flagged row\nand adjudicate every flagged row: [x]"
    assert _said_twice_in_one_breath(twice, "adjudicate every flagged row")
    far = (
        "adjudicate every flagged row " + "word " * 40 + "adjudicate every flagged row"
    )
    assert not _said_twice_in_one_breath(far, "adjudicate every flagged row")
    once = "adjudicate every flagged row"
    assert not _said_twice_in_one_breath(once, "adjudicate every flagged row")

    item = "5. a\n6. **Verify LANDING** run it\n   and adjudicate\n7. next\n"
    assert _list_item(item, "6. **Verify LANDING").endswith("and adjudicate")

    for positive in (
        "```bash\ncp .ai/learnings.md .ai/learnings-pre-drain-x.md\n```",
        "```\ngit show HEAD:.ai/learnings.md | grep -c x\n```",
        "settle it: `git show <sha>:.ai/learnings.md | grep -c '^### '` first",
        "reconstruct (`git show\n   HEAD:.ai/learnings.md > x.md`) now",
        "the old line was cp .ai/learnings.md x",
    ):
        assert _buffer_on_a_shell_line(positive), f"missed: {positive!r}"
    for clean in (
        "Read `.ai/learnings.md` in full.",
        "| `.cursor/rules/learnings.md` | yes | updated |",
        "```bash\npython x.py .ai/learnings-pre-drain-x.md HEAD\n```",
        "```markdown\n| `.ai/learnings.md` | Removed {N} entries |\n```",
        "the `.ai/learnings.md` intake buffer",
        "reconstruct (`git show HEAD:`)",
    ):
        assert not _buffer_on_a_shell_line(clean), f"flagged clean text: {clean!r}"

    old_c1 = (
        '```bash\npython "${CLAUDE_PLUGIN_ROOT}/skills/x/scripts/drain_audit.py" \\\n'
        "  .ai/learnings-pre-drain-<date>.md\n```"
    )
    assert _audit_commands_missing_a_ref(old_c1)
    assert _audit_commands_missing_a_ref("run `drain_audit.py snap.md` now")
    for ok in (
        '```bash\npython "${X}/drain_audit.py" snap.md HEAD\n```',
        '```bash\npython "${X}/drain_audit.py" --current-contents snap.md\n```',
        "run `drain_audit.py <snapshot> <base-ref>` and then adjudicate",
        "the critic ships `drain_audit.py`",
    ):
        assert not _audit_commands_missing_a_ref(ok), f"flagged clean text: {ok!r}"

    old_flow = (
        "### Phase 2: A\n\ntext\n\n### Phase 3: Plan\n\n```\n### Promotions\n```\n\n"
        "**STOP and wait for user approval before proceeding.**\n\n"
        "### Phase 6.5: Validation (via `hypothesis-validator`)\n\n"
        "2. Fold its proposed status changes into the consolidation plan (Phase 3's gate\n"
    )
    assert len(_hypothesis_flow_gaps(old_flow)) >= 5
    new_flow = (
        "### Phase 2: A\n\n**Verdicts (via `hypothesis-validator`)** run its Steps 1 to 4 "
        "and its Step 7 line here, writing nothing\n([due?](r.md#hypothesis-lifecycle-in-the-plan))."
        "\n\n### Phase 3: Plan\n\n```\n### Hypothesis verdicts\n```\n\n"
        "**STOP and wait for user approval before proceeding.**\n\n"
        "### Phase 6.5: Validation\n\nIt keeps Steps 6 and 8.\n"
    )
    assert _hypothesis_flow_gaps(new_flow) == []
    assert len(_hypothesis_flow_gaps(new_flow.replace(", writing nothing", ""))) == 1
    unlinked = new_flow.replace("#hypothesis-lifecycle-in-the-plan", "#elsewhere")
    assert len(_hypothesis_flow_gaps(unlinked)) == 1

    body = (
        "## When This Skill Activates\n\nInvoked from Phase 6.5 only.\n\n## Process\n"
    )
    assert len(_validator_split_gaps(body)) == 5
    elsewhere = "---\ndescription: Steps 1 to 4 at the end of its Phase 2; Steps 6 and 8.\n---\n"
    assert _validator_split_gaps(elsewhere + body), "the frontmatter must not count"
    split = (
        "## When This Skill Activates\n\nSteps 1 to 4 run at the end of its Phase 2; "
        "Phase 6.5 keeps Steps 6 and 8. Before the gate nothing is written: DORMANT\n"
        "marks wait for Step 6.\n"
    )
    assert not _validator_split_gaps(split)
    assert len(_validator_split_gaps(split.replace("nothing is written", "x"))) == 1

    old_row = (
        "## Integration Points\n\n| Caller | When |\n|---|---|\n"
        "| `learning-consolidator` | Phase 6.5, ~weekly |\n"
    )
    assert len(_integration_row_gaps(old_row)) == 1
    both = old_row.replace("Phase 6.5,", "End of Phase 2 and Phase 6.5,")
    assert _integration_row_gaps(both) == []
    assert _integration_row_gaps("## Integration Points\n\n| a | b |\n")

    old_item = "## Meta-Synthesis (x)\n\n1. a\n5. Update the header marker (`m`) and record it.\n"
    assert _item_5_gaps(old_item)
    new_item = (
        "## Meta-Synthesis (x)\n\n1. a\n5. **Add** the marker line `m` when the header "
        "has none,\n   and update it when it has one.\n\nCalibration.\n"
    )
    assert _item_5_gaps(new_item) == []

    old_meta = (
        "## Meta-Synthesis (x)\n\nTrigger: the lint prints `NOTE: meta-synthesis due`.\n\n"
        "3. What made it undecidable (missing instrument?)\n"
        "5. Update the header marker (`**Last meta-synthesis:** {date} — {N} terminal "
        "verdicts covered`) and record it.\n\nCalibration.\n"
    )
    old_gaps = _marker_gaps(old_meta)
    assert len(old_gaps) == len(_MARKER_CASES), (
        old_gaps
    )  # the old line itself is readable
    unreadable = old_meta.replace(
        "**Last meta-synthesis:** {date} — {N} terminal verdicts covered",
        "Last meta-synthesis: {date}, {N} covered",
    )
    assert any("reads no count" in gap for gap in _marker_gaps(unreadable))
    new_meta = (
        "## Meta-Synthesis (x)\n\nA missing marker counts as 0 covered. An unreadable one "
        "gets a NOTE and the due check does not run. One above the count is a NOTE that it "
        "is ahead of the ledger. Each is a NOTE, never a finding.\n\n"
        "5. **Add** `> **Last meta-synthesis:** {YYYY-MM-DD} — {N} terminal verdicts "
        "covered` when the header has none, and update it.\n\nCalibration.\n"
    )
    assert _marker_gaps(new_meta) == []
    assert (
        _lint_reads_marker(
            "> **Last meta-synthesis:** none — 0 terminal verdicts covered"
        )
        == 0
    )
    assert _lint_reads_marker("**Last meta-synthesis:** x — 3 verdicts") is None

    assert _lifecycle_gaps(
        "**Recommendation lifecycle** - read the latest retro report.\n"
    )
    new_lifecycle = (
        "**Recommendation lifecycle** - read the report; when it is not durable or absent, "
        "read the retrospective's changelog entry, where a project that keeps P1/P2 as "
        "proposals registers them.\n"
    )
    assert _lifecycle_gaps(new_lifecycle) == []
    assert len(_lifecycle_gaps(new_lifecycle.replace("not durable or ", ""))) == 1

    assert len(_gate_record_gaps("says nothing about the record")) == len(_GATE_FACTS)
    assert "the 200-character floor" in _gate_record_gaps(
        "At .ai/consolidation-gates/<YYYY-MM-DD>-plan-approved.md, the local calendar day."
    )

    for old in (
        'PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint',
        "`python -m lemmi_ai_kit lint learnings`",
        "(`python\n   python -m lemmi_ai_kit lint learnings --list-entries`)",
    ):
        assert _kit_command_problems(old), f"missed an old command form: {old!r}"
    canonical = (
        '`uv run --no-project --directory "${CLAUDE_PLUGIN_ROOT}/src" python -B -m '
        'lemmi_ai_kit lint learnings --list-entries --project "<project root>"`'
    )
    assert _kit_command_problems(canonical) == []
    assert _kit_command_problems(canonical.replace(' --project "<project root>"', ""))
    assert _kit_command_problems("a fresh run of the `audit-skills` subcommand") == []

    assert _EXIT_ONE.search("so exit 1 means\n rows to adjudicate")
    assert not _EXIT_ONE.search("exit 1 means failure")

    assert _UNSOUND_ZERO.search(
        "under --current-contents an exit 0 is an upper\n bound"
    )
    assert not _UNSOUND_ZERO.search(
        "0  clean: every entry landed in at least one target"
    )
