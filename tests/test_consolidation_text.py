"""The checks of the consolidation text tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_scan_covers_the_three_skills`: The scan surface in numbers: every file of the three skills is read, none skipped.
* `test_no_file_of_the_three_skills_says_a_word_twice_in_a_row`: Red before the fix: the cadence guard printed `python python -m ...`.
* `test_no_printed_shell_line_names_the_buffer`: Red before the fix: the previous-drain count, the snapshot copy and the critic's recovery read each printed a shell line that named the buffer.
* `test_every_printed_landing_audit_command_passes_a_base_ref`: Red before the fix: C1 of the critic passed the snapshot alone.
* `test_c1_prints_the_landing_audit_with_both_ref_cases`: Red before the fix. C1 takes the reference's two ref cases, and says what exit 1 is.
* `test_every_printed_support_cli_command_has_the_one_canonical_form`: Red before the fix: four commands carried an environment assignment, two were the bare module form, and none passed `--project` (which `uv --directory` makes mandatory). This pins the printed FORM; `test_printed_commands.py` parses each with the CLI's own parser.
* `test_every_rule_sees_its_planted_positive`: A guard never shown to fail has not been shown to work.
"""

import re
import shlex
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _REPO_ROOT / "plugins" / "core" / "skills"
_CONSOLIDATOR = _SKILLS / "learning-consolidator"
_CRITIC = _SKILLS / "consolidation-critic"
_VALIDATOR = _SKILLS / "hypothesis-validator"
_DIRS = (_CONSOLIDATOR, _CRITIC, _VALIDATOR)


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


# --- rule: meta-synthesis item 5 adds a marker that may not exist --------------------


# --- rule: the marker line is the one the ledger lint reads ----------------------------

# The marker line is read by the ledger lint's own reader,
# `checks.read_meta_synthesis_marker`: the first line outside a fence that opens with the
# bold label (a blockquote `>` before it is allowed), with its count taken from
# `N terminal verdicts covered` after the label. Asking that reader, and not a pattern
# copied from it, holds the text to the code.


# --- rule: the recommendation lifecycle reads the changelog entry --------------------


# --- rule: the gate record is documented with its day and length rules ---------------


# --- rule: every printed support-CLI command has the one canonical form --------------

_CANONICAL = re.compile(
    r'^uv run --no-project --directory "\$\{CLAUDE_PLUGIN_ROOT\}/src" '
    r"python -B -m lemmi_ai_kit "
    r'(?:lint|audit-skills)\b.*--project "<absolute project root>"$'
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


def test_every_printed_support_cli_command_has_the_one_canonical_form() -> None:
    """Red before the fix: four commands carried an environment assignment, two were the
    bare module form, and none passed `--project` (which `uv --directory` makes mandatory).
    This pins the printed FORM; `test_printed_commands.py` parses each with the CLI's
    own parser."""
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

    for old in (
        'PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint',
        "`python -m lemmi_ai_kit lint learnings`",
        "(`python\n   python -m lemmi_ai_kit lint learnings --list-entries`)",
    ):
        assert _kit_command_problems(old), f"missed an old command form: {old!r}"
    canonical = (
        '`uv run --no-project --directory "${CLAUDE_PLUGIN_ROOT}/src" python -B -m '
        'lemmi_ai_kit lint learnings --list-entries --project "<absolute project root>"`'
    )
    assert _kit_command_problems(canonical) == []
    assert _kit_command_problems(
        canonical.replace(' --project "<absolute project root>"', "")
    )
    assert _kit_command_problems(
        canonical.replace("<absolute project root>", "<project root>")
    ), "a project root that does not say it is absolute is the old form"
    assert _kit_command_problems("a fresh run of the `audit-skills` subcommand") == []

    assert _EXIT_ONE.search("so exit 1 means\n rows to adjudicate")
    assert not _EXIT_ONE.search("exit 1 means failure")
