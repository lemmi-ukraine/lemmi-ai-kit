"""The triage table's copied columns, generated from the learnings buffer, with the decisions joined on them.

Phase 3 of the consolidator builds a table with one row per intake entry and the decision on it. The
columns that merely copy the buffer are generated here and never typed, and the decisions, which are
typed, are joined to the entries on the line number. "One row per entry" then becomes a set
difference this script reports, instead of something to spot by eye in a table of a hundred rows.

Usage:

    python "${CLAUDE_SKILL_DIR}/scripts/buffer_table.py" --project "<absolute project root>"
    python "${CLAUDE_SKILL_DIR}/scripts/buffer_table.py" --project "<absolute project root>" \\
        --today <YYYY-MM-DD> --decisions <decisions file>

The command names the project root and never the buffer: the buffer is `.ai/learnings.md` under it,
the file `lint learnings` reads, so a session may run it under the rule that a session never names
the buffer on a shell line. The run only reads. It makes no commit and no copy and writes no file.

The table has one row per entry, an entry being a `### ` heading outside a fenced code block (the
lint's reading of a fence, which the inventory of `lint learnings --list-entries` does not apply: a
heading inside a fence is example text, so the run lists each one it skips, and the two counts can
be reconciled). Its columns:

    line       the heading's line, the key of the join (git's line, and the inventory's)
    date       the `[YYYY-MM-DD]` the title starts with, or `-`
    age        the days from --today (default: the machine's calendar day) to that date, or `-`
    home       the entry's `Home:` field, the first one, or `-`
    anchor     the entry's `Verify-at:` field, the first one, or `-`
    committed  `yes` when every non-blank line of the entry is in a commit, `no` when one is not
               (a new entry, or an edit to one), `unknown` when git could not answer, read from
               `git blame --porcelain` on the buffer as it stands in the working tree
    title      the heading's text

`--decisions` names a JSON Lines file, one object per entry with `line`, `action` (one of the
actions of Phase 2's Step 3) and optionally `target` and `rationale`, and no other key: the copied
columns are generated, so one typed into the file is refused. The decisions are joined to the entries
on `line`, three columns are added, and the set difference is reported both ways: an entry with no
decision row, a decision row whose line is no entry, and a line with more than one decision row.
Line numbers move with every edit of the buffer, so run it again after the last one.

Exit codes, as in `drain_audit.py`:

    0  a complete table, and with --decisions a complete join
    1  rows to adjudicate: a set difference, an entry whose `committed` is `unknown`, or a code
       fence that never closes (it hides every heading after it). It is not an error, and it is
       not a clean table either
    2  input the run could not read: no buffer, a buffer with no entry or that is not UTF-8, a
       decisions file that is unreadable or holds a row it cannot use, or a bad option. A run that
       could not measure never exits 0

Forces UTF-8 stdout so the output is readable on consoles that default to a legacy codepage.
"""

import argparse
import contextlib
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

# The buffer's path under the project root: the one file `lint learnings` reads.
BUFFER = ".ai/learnings.md"

# The actions of the table under Step 3 of Phase 2 in SKILL.md; a test holds the two in step.
ACTIONS = (
    "PROMOTE_TO_RULE",
    "PROMOTE_TO_SKILL",
    "UPDATE_SKILL",
    "PROMOTE_TO_README",
    "PROMOTE_TO_COMMENT",
    "MERGE_ENTRIES",
    "KEEP",
    "ARCHIVE",
)
DECISION_KEYS = ("line", "action", "target", "rationale")

GIT_TIMEOUT_SECONDS = 120

# The shapes `lint learnings` reads: an entry heading (as its inventory counts one), a section
# heading, a fence marker, an entry's `**Field**: value` bullet and a title's leading date.
ENTRY_RE = re.compile(r"^### (.*)$")
SECTION_RE = re.compile(r"^## ")
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
FIELD_RE = re.compile(r"^- \*\*(.+?):?\*\*:?\s*(.*)$")
TITLE_DATE_RE = re.compile(r"^\[(\d{4})-(\d{2})-(\d{2})\]")
ISO_DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# One line of `git blame --porcelain` that starts a line's block: the commit, the line it came
# from, the line it is now, and (for the first line of a group) the group's size.
BLAME_HEADER_RE = re.compile(r"^([0-9a-f]{40,64}) \d+ (\d+)(?: \d+)?$")


@dataclass(frozen=True)
class Entry:
    line: int
    title: str
    day: date | None
    home: str
    anchor: str
    # The lines of the entry that are not blank, its heading's included: what `committed` judges.
    content: tuple[int, ...]


@dataclass(frozen=True)
class Scan:
    entries: tuple[Entry, ...]
    # The lines of headings inside a code fence: example text, skipped and listed, not entries.
    fenced: tuple[int, ...]
    # The line of the fence marker that never closes, which hides every heading after it.
    unclosed: int | None


@dataclass(frozen=True)
class Decision:
    # The line of the decisions file this row came from; `line` is the entry's line it names.
    source: int
    line: int
    action: str
    target: str
    rationale: str


@dataclass(frozen=True)
class Join:
    by_line: dict[int, list[Decision]]
    missing: tuple[Entry, ...]
    extra: tuple[Decision, ...]
    duplicated: tuple[tuple[Entry, list[Decision]], ...]

    def problems(self) -> list[str]:
        lines = [
            f"entry without a decision row: line {entry.line}, {entry.title}"
            for entry in self.missing
        ]
        lines += [
            f"decision row without an entry: line {row.line} (decisions file line {row.source})"
            for row in self.extra
        ]
        lines += [
            f"line with more than one decision row: line {entry.line} holds {len(rows)} rows "
            f"(decisions file lines {', '.join(str(row.source) for row in rows)})"
            for entry, rows in self.duplicated
        ]
        return lines


def fence_mask(lines: Sequence[str]) -> list[bool]:
    """True for every line inside a fenced code block, the fence markers included.

    The definition of `lint learnings` (`checks._fence_mask`), copied because this script runs
    from a plugin install and imports nothing of the kit; a test holds the two in step.
    """
    mask: list[bool] = []
    inside = False
    for line in lines:
        if FENCE_RE.match(line) is not None:
            mask.append(True)
            inside = not inside
            continue
        mask.append(inside)
    return mask


def read_lines(path: Path) -> list[str]:
    """The file's lines, split on the newline alone (git's lines), without a BOM or a CR.

    `str.splitlines` also breaks on a form feed, a Unicode line separator and others, which would
    put every later line number off from git's and the inventory's.
    """
    text = path.read_bytes().decode("utf-8-sig")
    return [line.removesuffix("\r") for line in text.split("\n")]


def title_day(title: str) -> date | None:
    match = TITLE_DATE_RE.match(title)
    if match is None:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def scan(lines: Sequence[str]) -> Scan:
    """The entries of a buffer, the headings a fence hides, and a fence that never closes."""
    mask = fence_mask(lines)
    closers = [
        index
        for index, line in enumerate(lines)
        if not mask[index] and (ENTRY_RE.match(line) or SECTION_RE.match(line))
    ]
    entries: list[Entry] = []
    for position, start in enumerate(closers):
        heading = ENTRY_RE.match(lines[start])
        if heading is None:
            continue
        end = closers[position + 1] if position + 1 < len(closers) else len(lines)
        fields: dict[str, str] = {}
        for index in range(start + 1, end):
            field = None if mask[index] else FIELD_RE.match(lines[index].strip())
            if field is not None:
                fields.setdefault(field.group(1).rstrip(":"), field.group(2))
        title = heading.group(1).strip()
        entries.append(
            Entry(
                line=start + 1,
                title=title,
                day=title_day(title),
                home=fields.get("Home", ""),
                anchor=fields.get("Verify-at", ""),
                content=tuple(i + 1 for i in range(start, end) if lines[i].strip()),
            )
        )
    fenced = tuple(
        index + 1
        for index, line in enumerate(lines)
        if mask[index] and ENTRY_RE.match(line)
    )
    markers = [index for index, line in enumerate(lines) if FENCE_RE.match(line)]
    unclosed = markers[-1] + 1 if len(markers) % 2 else None
    return Scan(tuple(entries), fenced, unclosed)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _first_line(text: str) -> str:
    return next(
        (line.strip() for line in text.split("\n") if line.strip()), "no message"
    )


def committed_lines(root: Path) -> tuple[frozenset[int] | None, str]:
    """The lines of the buffer that are in a commit, or None and the reason when git cannot say.

    `git blame --porcelain` of the working-tree file names, for every line, the commit it came
    from, and gives a line no commit holds (a new line, an edit, a staged one) the all-zero id.
    A buffer that is not in HEAD has no line in a commit, which is an answer; a directory that is
    no work tree, or a git that cannot run, is not one.
    """
    blamed = _git(root, "blame", "--porcelain", "--", BUFFER)
    if blamed is None:
        return None, "git could not be run"
    if blamed.returncode == 0:
        committed: set[int] = set()
        for line in blamed.stdout.split("\n"):
            header = BLAME_HEADER_RE.match(line)
            if header is not None and set(header.group(1)) != {"0"}:
                committed.add(int(header.group(2)))
        return frozenset(committed), ""
    reason = _first_line(blamed.stderr)
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != "true":
        return None, reason
    in_head = _git(root, "cat-file", "-e", f"HEAD:{BUFFER}")
    if in_head is not None and in_head.returncode != 0:
        return frozenset(), ""
    return None, reason


def committed_state(entry: Entry, committed: frozenset[int] | None) -> str:
    if committed is None:
        return "unknown"
    return "yes" if all(number in committed for number in entry.content) else "no"


def _decision(number: int, raw: str) -> Decision | str:
    """One decisions line as a decision, or the reason it cannot be used."""
    where = f"decisions file line {number}"
    try:
        value: object = json.loads(raw)
    except json.JSONDecodeError as error:
        return f"{where}: not valid JSON ({error.msg})"
    if not isinstance(value, dict):
        return f"{where}: not a JSON object"
    row = cast("dict[str, object]", value)
    unknown = [key for key in row if key not in DECISION_KEYS]
    if unknown:
        return (
            f"{where}: unknown key `{unknown[0]}` (the copied columns are generated; "
            f"type only {', '.join(f'`{key}`' for key in DECISION_KEYS)})"
        )
    if "line" not in row:
        return f"{where}: missing key `line`"
    line = row["line"]
    if not isinstance(line, int) or isinstance(line, bool) or line < 1:
        return f"{where}: `line` must be a whole number of 1 or more"
    if "action" not in row:
        return f"{where}: missing key `action`"
    action = row["action"]
    if not isinstance(action, str) or action not in ACTIONS:
        return f"{where}: `action` must be one of {', '.join(ACTIONS)}"
    text: dict[str, str] = {}
    for key in ("target", "rationale"):
        item = row.get(key, "")
        if not isinstance(item, str):
            return f"{where}: `{key}` must be a string"
        text[key] = item
    return Decision(number, line, action, text["target"], text["rationale"])


def read_decisions(path: Path) -> tuple[list[Decision], list[str]]:
    """The decisions of a JSON Lines file, and one reason for each line that cannot be used."""
    decisions: list[Decision] = []
    problems: list[str] = []
    for number, raw in enumerate(
        path.read_bytes().decode("utf-8-sig").split("\n"), start=1
    ):
        if not raw.strip():
            continue
        parsed = _decision(number, raw.strip())
        if isinstance(parsed, Decision):
            decisions.append(parsed)
        else:
            problems.append(parsed)
    return decisions, problems


def join_decisions(entries: Sequence[Entry], decisions: Sequence[Decision]) -> Join:
    by_line: dict[int, list[Decision]] = {}
    for decision in decisions:
        by_line.setdefault(decision.line, []).append(decision)
    on_entry = {entry.line for entry in entries}
    return Join(
        by_line=by_line,
        missing=tuple(entry for entry in entries if entry.line not in by_line),
        extra=tuple(row for row in decisions if row.line not in on_entry),
        duplicated=tuple(
            (entry, by_line[entry.line])
            for entry in entries
            if len(by_line.get(entry.line, [])) > 1
        ),
    )


def cell(value: str) -> str:
    """A markdown table cell: one line, a pipe escaped, `-` when empty."""
    return " ".join(value.split()).replace("|", "\\|") or "-"


def render(
    entries: Sequence[Entry], states: Sequence[str], today: date, joined: Join | None
) -> list[str]:
    columns = ["line", "date", "age", "home", "anchor", "committed", "title"]
    if joined is not None:
        columns += ["action", "target", "rationale"]
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for entry, state in zip(entries, states, strict=True):
        cells = [
            str(entry.line),
            entry.day.isoformat() if entry.day else "-",
            str((today - entry.day).days) if entry.day else "-",
            cell(entry.home),
            cell(entry.anchor),
            state,
            cell(entry.title),
        ]
        if joined is not None:
            rows = joined.by_line.get(entry.line, [])
            if len(rows) == 1:
                cells += [rows[0].action, cell(rows[0].target), cell(rows[0].rationale)]
            else:
                cells += ["(duplicate)" if rows else "(no row)", "-", "-"]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def iso_day(value: str) -> date:
    if ISO_DAY_RE.fullmatch(value) is None:
        raise argparse.ArgumentTypeError(f"{value!r} is not a date written YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{value!r} is not a date: {error}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buffer_table.py",
        description=(
            "Print the triage table's copied columns for the learnings buffer, one row per "
            "entry, and join the typed decisions on the line number. Reads only."
        ),
        epilog=(
            "exit codes: 0 a complete table (with --decisions, a complete join); "
            "1 rows to adjudicate (a set difference, a committed that is unknown, a code fence "
            "that never closes), which is not an error; 2 input the run could not read"
        ),
    )
    parser.add_argument(
        "--project",
        default=".",
        metavar="DIR",
        help=f"the project root, whose {BUFFER} is read (default: the working directory)",
    )
    parser.add_argument(
        "--today",
        type=iso_day,
        metavar="YYYY-MM-DD",
        help="the day each age is counted to (default: the machine's calendar day)",
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        metavar="FILE",
        help=(
            "a JSON Lines file with one object per entry: line, action (one of "
            f"{', '.join(ACTIONS)}) and optionally target and rationale; joined on the line "
            "number, with the set difference reported both ways"
        ),
    )
    return parser


def _force_utf8_stdout() -> None:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def main(argv: Sequence[str] | None = None) -> int:
    _force_utf8_stdout()
    args = build_parser().parse_args(argv)
    root = Path(args.project).resolve()
    buffer = root / BUFFER
    if not buffer.is_file():
        print(f"ERROR: no buffer: {buffer} is not a file, so nothing was measured.")
        return 2
    try:
        found = scan(read_lines(buffer))
    except (OSError, UnicodeDecodeError) as error:
        print(f"ERROR: could not read the buffer {buffer}: {error}")
        return 2
    if not found.entries:
        print(
            f"ERROR: no entry in {buffer} (an entry heading starts with '### ' outside a code "
            f"fence; {len(found.fenced)} heading(s) inside a fence were skipped), so nothing was "
            "measured. A run that cannot see its subject must not report a clean table."
        )
        return 2
    decisions: list[Decision] | None = None
    if args.decisions is not None:
        try:
            decisions, unusable = read_decisions(args.decisions)
        except (OSError, UnicodeDecodeError) as error:
            print(f"ERROR: could not read the decisions file {args.decisions}: {error}")
            return 2
        if unusable:
            print(
                f"ERROR: the decisions file is not usable, so nothing was joined "
                f"({len(unusable)} problems):"
            )
            for problem in unusable:
                print(f"  {problem}")
            return 2
    committed, reason = committed_lines(root)
    states = [committed_state(entry, committed) for entry in found.entries]
    today = args.today or date.today()
    joined = None if decisions is None else join_decisions(found.entries, decisions)

    print(f"buffer: {BUFFER}")
    print(f"entries: {len(found.entries)}")
    print(
        f"today: {today.isoformat()} ({'from --today' if args.today else 'from the machine clock'})"
    )
    print(
        f"committed: {states.count('yes')} yes, {states.count('no')} no, "
        f"{states.count('unknown')} unknown"
    )
    flagged = False
    if committed is None:
        flagged = True
        print(f"committed could not be read: {reason}")
    if found.fenced:
        print(
            f"fenced headings skipped: {len(found.fenced)} [{', '.join(map(str, found.fenced))}]"
        )
    if found.unclosed is not None:
        flagged = True
        print(
            f"code fence that never closes: opened at line {found.unclosed}, so every heading "
            "after it was skipped"
        )
    if joined is not None and decisions is not None:
        print(f"decision rows: {len(decisions)}")
        for problem in joined.problems():
            flagged = True
            print(problem)
    print()
    for line in render(found.entries, states, today, joined):
        print(line)
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
