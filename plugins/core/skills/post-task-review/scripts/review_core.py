#!/usr/bin/env python3
"""Print the post-task review's mechanical checks in one run, so the judgment steps start from facts.

WHY THIS EXISTS
---------------
The review's mechanical half was a list of commands a session had to remember at the end of a long
task, which is when context is scarcest: the dependents grep (Step 0), the diff stat against the
plan's file list, the line-ending check, the lint and format scope (Step 6) and the documentation
lookup (Step 7b). Under that pressure the review was skipped or shrunk, and the commands that did run
had known blind spots: plain `git grep` and `git diff HEAD` cannot see a file the task created,
`--stat` rescales its bars and abbreviates paths, and a zero printed without a count of what was
searched reads as clean. This script runs the commands in the forms the skill's references prescribe,
prints a denominator beside every zero, and ends each section with what it did not check. It prints
facts for the review to read. It judges nothing and edits nothing.

USAGE (from anywhere inside the repository)
    python -B review_core.py [--base REF] [--plan FILE] [--symbol NAME ...] [--roots PATH ...]
                             [--matrix FILE] [--max-symbols N] [--tests PATH ...]
                             [--assertion TOKEN ...] [--max-rows N]

    --base REF       compare the working tree with REF instead of HEAD, to review committed work
    --plan FILE      the plan's file list, one path per line: a trailing `/` covers a directory, a
                     bullet, backticks and text after the path are ignored, `#` starts a comment
    --symbol NAME    add a name to the dependents search (a flag, a key, a message: anything the
                     definition patterns cannot derive); repeatable, matched as a fixed string in every
                     file, and the way to list the readers of a name the diff adds
    --roots PATH     limit the dependents search to these paths (default: the whole repository)
    --matrix FILE    the project's own code-to-docs matrix (markdown tables); default: the sample
    --max-symbols N  search at most N names (default 30); the rest are printed as NOT CHECKED
    --max-files N    list at most N readers outside the diff per name (default 15); the rest are
                     counted as NOT CHECKED, so a long list is never silently cut
    --tests PATH     replace the printed rule for test paths with the project's own entries, written
                     as in --plan (a trailing `/` covers a directory, `*?[` makes a pattern); a
                     project directory such as MyApp.Tests/ is a test path only this way
    --assertion TOKEN  also count a line that holds this fixed string as an assertion; repeatable.
                     The built-in tokens are case-sensitive: a capitalised form such as C#'s
                     Assert.Equal( needs `--assertion Assert.`
    --max-rows N     list at most N removed or changed assertion rows (default 40); the rest are
                     counted as NOT CHECKED

OUTPUT: a header, seven numbered sections (changed files, diff stat, dependents, line endings, lint
and format scope, documentation matrix, test changes), then one summary line. Each section ends
with the limit of its own instrument.

EXIT CODES
    0  every section ran; what it found is printed for the review to judge
    2  something could not be measured (a NOT CHECKED line says what): not a git work tree, an
       unresolvable base, an unreadable plan or matrix, no Commands section to read, a changed
       test file that git printed no hunk for, or more names or rows than a cap allows.
       Cannot-measure is never a pass, so gate on `!= 0`.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import NamedTuple

_SECTIONS = 7

# Definition syntax is read only in files with one of these extensions, so a markdown line that
# happens to start with "type" or "class" does not become a symbol.
_CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".cs",
    }
    | {".rb", ".php", ".swift"}
)
_MODIFIERS = r"(?:(?:export|default|async|public|private|protected|static|final|abstract|pub|unsafe)\s+|pub\([^)]*\)\s+)*"
_DEFINITION = re.compile(
    rf"^\s*{_MODIFIERS}(?:def|class|function|func|fn|struct|enum|trait|interface|type)\s+"
    r"(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"
)
_SKIP_RULE = "dunder, test_/Test, under 3 characters"

# Tool -> the extensions it checks by default. A tool the commands name but this table lacks reads as
# "no tool", which sends the reviewer to look, not to assume.
_TOOLS: dict[str, frozenset[str]] = {
    "ruff": frozenset({".py", ".pyi"}),
    "black": frozenset({".py", ".pyi"}),
    "flake8": frozenset({".py"}),
    "pylint": frozenset({".py"}),
    "isort": frozenset({".py"}),
    "basedpyright": frozenset({".py", ".pyi"}),
    "pyright": frozenset({".py", ".pyi"}),
    "mypy": frozenset({".py", ".pyi"}),
    "eslint": frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}),
    "prettier": frozenset(
        {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".html", ".md", ".yaml", ".yml"}
    ),
    "tsc": frozenset({".ts", ".tsx"}),
    "biome": frozenset({".js", ".jsx", ".ts", ".tsx", ".json"}),
    "markdownlint": frozenset({".md"}),
    "shellcheck": frozenset({".sh", ".bash"}),
    "gofmt": frozenset({".go"}),
    "golangci-lint": frozenset({".go"}),
    "rustfmt": frozenset({".rs"}),
    "clippy": frozenset({".rs"}),
    "yamllint": frozenset({".yml", ".yaml"}),
    "taplo": frozenset({".toml"}),
    "rubocop": frozenset({".rb"}),
    "ktlint": frozenset({".kt"}),
}

_STYLE_ORDER = ("lf", "crlf", "mixed", "binary", "none", "empty")

# A test path has a directory named test, tests or __tests__ (any case) or a file name matching one
# of these; --tests replaces the rule with the project's own entries.
_TEST_DIRS = ("test", "tests", "__tests__")
_SCRIPT_EXTENSIONS = ("js", "jsx", "mjs", "cjs", "ts", "tsx")
_TEST_NAMES = (
    "test_*.py",
    "*_test.py",
    "*_test.go",
    "*_test.rb",
    "*_spec.rb",
    *(f"*.{kind}.{ext}" for kind in ("test", "spec") for ext in _SCRIPT_EXTENSIONS),
    "*Test.java",
    "*Tests.java",
    "*Test.kt",
    "*Tests.kt",
    "*Test.cs",
    "*Tests.cs",
)
_TEST_RULE = (
    f"a directory named {', '.join(_TEST_DIRS[:-1])} or {_TEST_DIRS[-1]}, "
    f"or a file named {', '.join(_TEST_NAMES)}"
)

# A line is an assertion when it holds one of these tokens (or a --assertion token) and is not a
# comment. The token floor sees an assertion by its first line only.
_ASSERTION = re.compile(
    r"\bassert\w*|\bexpect\w*|\bshould\b|\.to[A-Z]\w*\(|\bt\.(?:Error|Fatal|Fail)\w*|\braises\b"
)
_COMMENT_STARTS = ("#", "//", "/*", "*")
_ROW_KINDS = ("REMOVED", "CHANGED", "MOVED?", "DELETED")
_ROW_LINES = 5
_ROW_WIDTH = 120
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
# The section's diff is asked for code files only, matched without regard to case as the extension
# test is, so that --text (which makes git print hunks for a file an attribute marks `-diff`) is
# never applied to an image or an archive.
_CODE_DIFF_PATHSPECS = tuple(
    f":(icase)*{extension}" for extension in sorted(_CODE_EXTENSIONS)
)


class _GitError(Exception):
    pass


def _git(root: Path | None, *args: str, ok: tuple[int, ...] = (0,)) -> bytes:
    command = ["git", "--no-optional-locks", "-c", "core.quotePath=false", *args]
    try:
        proc = subprocess.run(command, cwd=root, capture_output=True, check=False)
    except OSError as exc:
        raise _GitError(f"git cannot run ({exc.strerror})") from exc
    if proc.returncode not in ok:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise _GitError(detail or f"git {args[0]} exited {proc.returncode}")
    return proc.stdout


def _split_nul(raw: bytes) -> list[str]:
    return [piece.decode("utf-8", "replace") for piece in raw.split(b"\0") if piece]


class _Report:
    """Prints the section frames and counts what could not be measured or was not asked for."""

    def __init__(self) -> None:
        self.section = 0
        self.failed: set[int] = set()
        self.not_checked = 0
        self.skipped = 0

    def open(self, number: int, title: str) -> None:
        self.section = number
        print(f"== {number}. {title} ==")

    def fail(self, message: str) -> None:
        print(f"NOT CHECKED: {message}")
        self.not_checked += 1
        self.failed.add(self.section)

    def skip(self, message: str) -> None:
        print(f"SKIPPED (not asked): {message}")
        self.skipped += 1

    def finish(self, changed: int, ran: int) -> int:
        print("== Summary ==")
        print(
            f"review_core: {changed} changed file(s); {ran} of {_SECTIONS} sections ran; "
            f"{self.not_checked} NOT CHECKED; {self.skipped} skipped (not asked)"
        )
        return 2 if self.not_checked else 0


def _style(data: bytes) -> tuple[str, int, int]:
    if b"\0" in data[:8000]:
        return "binary", 0, 0
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    if not lf and not crlf:
        return ("none" if data else "empty"), 0, 0
    if lf and crlf:
        return "mixed", lf, crlf
    return ("crlf" if crlf else "lf"), lf, crlf


def _read_plan(path: Path) -> list[str]:
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^[-*+]\s+", "", line)
        ticked = re.search(r"`([^`]+)`", line)
        token = ticked.group(1) if ticked else line.split()[0]
        entries.append(token.replace("\\", "/").removeprefix("./"))
    return list(dict.fromkeys(entries))


def _covers(entry: str, path: str) -> bool:
    if entry.endswith("/"):
        return path.startswith(entry)
    if any(char in entry for char in "*?["):
        return fnmatch.fnmatchcase(path, entry)
    return path == entry


def _definition(text: str, path: str) -> str | None:
    if Path(path).suffix.lower() not in _CODE_EXTENSIONS:
        return None
    found = _DEFINITION.match(text)
    return found.group(1) if found else None


def _derive_symbols(
    root: Path, base: str, untracked: list[str]
) -> tuple[dict[str, set[str]], set[str]]:
    """Names a definition line adds or removes, and the names the skip rule dropped."""
    seen: dict[str, set[str]] = {}
    skipped: set[str] = set()

    def note(name: str, side: str) -> None:
        if (
            len(name) < 3
            or (name.startswith("__") and name.endswith("__"))
            or name.startswith(("test_", "Test"))
        ):
            skipped.add(name)
        else:
            seen.setdefault(name, set()).add(side)

    diff = _git(root, "diff", "--no-renames", "-U0", "--no-color", base, "--").decode(
        "utf-8", "replace"
    )
    current, in_header = "", False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            current, in_header = "", True
        elif in_header and line.startswith(("--- ", "+++ ")):
            target = line[4:].removeprefix("a/").removeprefix("b/")
            current = target if target != "/dev/null" else current
        elif line.startswith("@@"):
            in_header = False
        elif not in_header and line[:1] in ("+", "-"):
            name = _definition(line[1:], current)
            if name:
                note(name, "added" if line[0] == "+" else "removed")
    for path in untracked:
        file = root / path
        if Path(path).suffix.lower() in _CODE_EXTENSIONS and file.is_file():
            for line in file.read_text(encoding="utf-8", errors="replace").splitlines():
                name = _definition(line, path)
                if name:
                    note(name, "added")
    return seen, skipped


def _search(
    root: Path, name: str, roots: list[str], whole_word: bool
) -> dict[str, list[int]]:
    command = [
        "grep",
        "-n",
        "--untracked",
        "-I",
        "-F",
        *(["-w"] if whole_word else []),
        "-e",
        name,
        "--",
        *roots,
    ]
    hits: dict[str, list[int]] = {}
    for line in _git(root, *command, ok=(0, 1)).decode("utf-8", "replace").splitlines():
        path, _, rest = line.partition(":")
        number = rest.partition(":")[0]
        if number.isdigit():
            hits.setdefault(path, []).append(int(number))
    return hits


def _code_pathspecs(roots: list[str]) -> list[str]:
    """Pathspecs that keep a search to code files under the roots (one glob per extension)."""
    return [
        f"*{extension}" if root in (".", "") else f"{root.rstrip('/')}/*{extension}"
        for root in roots
        for extension in sorted(_CODE_EXTENSIONS)
    ]


def _scope(root: Path, pathspecs: list[str]) -> int:
    listed = _git(
        root, "ls-files", "-z", "-c", "-o", "--exclude-standard", "--", *pathspecs
    )
    return len(_split_nul(listed))


def _commands(root: Path) -> tuple[str, list[str]] | None:
    for name in ("AGENTS.md", "CLAUDE.md"):
        file = root / name
        if not file.is_file():
            continue
        lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
        level = 0
        fenced = False
        found: list[str] = []
        for line in lines:
            heading = re.match(r"^(#{1,6})\s+(.*)$", line) if not fenced else None
            if heading and level == 0 and re.match(r"Commands\b", heading.group(2)):
                level = len(heading.group(1))
            elif heading and level and len(heading.group(1)) <= level:
                break
            elif level and line.lstrip().startswith("```"):
                fenced = not fenced
            elif level and fenced and line.strip() and not line.strip().startswith("#"):
                found.append(line.strip())
        if found:
            return name, found
    return None


def _matrix_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if (
            len(cells) < 2
            or not cells[0]
            or set(cells[0]) <= set("-: ")
            or cells[0].lower().startswith("code path")
        ):
            continue
        rows.append((cells[0], cells[1]))
    return rows


def _path_regex(token: str) -> re.Pattern[str]:
    body = "[^/]+".join(re.escape(part) for part in re.split(r"\{[^}]*\}", token))
    return re.compile(f"^{body}.*" if token.endswith("/") else f"^{body}$")


def _is_test_path(path: str, entries: list[str] | None) -> bool:
    """The printed rule, or the project's own --tests entries when given (an entry ending in `/`
    covers a directory, one with `*?[` is a pattern, as in --plan)."""
    if entries is not None:
        return any(_covers(entry, path) for entry in entries)
    parts = path.rstrip("/").split("/")
    directory = path.endswith("/")
    if any(part.lower() in _TEST_DIRS for part in (parts if directory else parts[:-1])):
        return True
    return not directory and any(
        fnmatch.fnmatchcase(parts[-1], name) for name in _TEST_NAMES
    )


def _is_assertion(text: str, tokens: list[str]) -> bool:
    line = text.strip()
    if not line or line.startswith(_COMMENT_STARTS):
        return False
    return bool(_ASSERTION.search(line)) or any(token in line for token in tokens)


class _Hunk(NamedTuple):
    """One `-U0` hunk: where it starts in the base and in the work tree, and its changed lines."""

    path: str
    old_line: int
    new_line: int
    removed: list[str]
    added: list[str]


class _Row(NamedTuple):
    """One printed row of section 7: kind, `path:line` in the base, what changed, detail lines."""

    kind: str
    where: str
    what: str
    lines: list[str]


def _read_hunks(diff: str) -> list[_Hunk]:
    """The hunks of a `-U0` diff made with fixed a/ and b/ prefixes, in the diff's own order."""
    hunks: list[_Hunk] = []
    path, in_header = "", False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            path, in_header = "", True
        elif in_header and line.startswith(("--- ", "+++ ")):
            name = line[4:].split("\t")[0]
            path = name[2:] if name != "/dev/null" else path
        elif line.startswith("@@"):
            in_header = False
            found = _HUNK_HEADER.match(line)
            if found is None:
                raise _GitError(f"unreadable hunk header {line[:40]!r}")
            hunks.append(_Hunk(path, int(found[1]), int(found[2]), [], []))
        elif not in_header and hunks and line[:1] in ("-", "+"):
            (hunks[-1].removed if line[0] == "-" else hunks[-1].added).append(line[1:])
    return hunks


def _added_text(
    hunks: list[_Hunk], root: Path, untracked: list[str], rule: list[str] | None
) -> dict[str, deque[tuple[str, int]]]:
    """Every line the diff adds to a code file and every line of an untracked test file, by its
    stripped text, with the place it was added at."""
    pool: dict[str, deque[tuple[str, int]]] = defaultdict(deque)
    for hunk in hunks:
        if Path(hunk.path).suffix.lower() in _CODE_EXTENSIONS:
            for offset, text in enumerate(hunk.added):
                if text.strip():
                    pool[text.strip()].append((hunk.path, hunk.new_line + offset))
    for path in untracked:
        file = root / path
        if (
            Path(path).suffix.lower() in _CODE_EXTENSIONS
            and _is_test_path(path, rule)
            and file.is_file()
        ):
            data = file.read_bytes()
            if b"\0" in data[:8000]:
                continue
            for number, text in enumerate(
                data.decode("utf-8", "replace").splitlines(), start=1
            ):
                if text.strip():
                    pool[text.strip()].append((path, number))
    return pool


def _take(pool: dict[str, deque[tuple[str, int]]], text: str) -> str | None:
    """The place an identical line was added at, used up so that one added line answers one
    removed line."""
    places = pool.get(text.strip())
    if not places:
        return None
    path, number = places.popleft()
    return f"{path}:{number}"


def _clip(text: str) -> str:
    return text if len(text) <= _ROW_WIDTH else text[: _ROW_WIDTH - 3] + "..."


def _hunk_rows(
    path: str,
    hunks: list[_Hunk],
    pool: dict[str, deque[tuple[str, int]]],
    tokens: list[str],
) -> tuple[list[_Row], int]:
    """One row per hunk that removes an assertion line, and the count of the other removed lines."""
    rows: list[_Row] = []
    other = 0
    for hunk in hunks:
        gone = [
            (hunk.old_line + index, text.strip())
            for index, text in enumerate(hunk.removed)
            if _is_assertion(text, tokens)
        ]
        other += sum(
            1
            for text in hunk.removed
            if text.strip() and not _is_assertion(text, tokens)
        )
        if not gone:
            continue
        places = [_take(pool, text) for _, text in gone]
        unmatched = places.count(None)
        if not unmatched:
            kind = "MOVED?"
            where = ", ".join(place for place in places[:3] if place)
            more = f" and {len(places) - 3} more" if len(places) > 3 else ""
            what = f"{len(gone)} assertion line(s) removed, identical text added at {where}{more}"
        elif hunk.added:
            kind = "CHANGED"
            what = f"{len(gone)} assertion line(s) removed, {len(hunk.added)} line(s) added"
        else:
            kind = "REMOVED"
            what = f"{len(gone)} assertion line(s) removed, nothing added"
        shown = [
            f"- {_clip(text)}"
            + (f" (identical text added at {place})" if place and unmatched else "")
            for (_, text), place in zip(gone, places, strict=True)
        ]
        lines = shown[:_ROW_LINES]
        if len(shown) > _ROW_LINES:
            lines.append(
                f"... and {len(shown) - _ROW_LINES} more removed assertion line(s)"
            )
        if kind == "CHANGED":
            lines += [f"+ {_clip(text.strip())}" for text in hunk.added[:3]]
            if len(hunk.added) > 3:
                lines.append(f"... and {len(hunk.added) - 3} more added line(s)")
        rows.append(_Row(kind, f"{path}:{gone[0][0]}", what, lines))
    return rows, other


def _deleted_row(
    path: str,
    hunks: list[_Hunk],
    pool: dict[str, deque[tuple[str, int]]],
    tokens: list[str],
) -> _Row:
    gone = [
        text for hunk in hunks for text in hunk.removed if _is_assertion(text, tokens)
    ]
    again = sum(1 for text in gone if _take(pool, text) is not None)
    what = f"{len(gone)} assertion line(s) in the deleted file, {again} of {len(gone)} added again as identical text"
    return _Row("DELETED", path, what, [])


def _lost_lines(count: tuple[str, str] | None) -> bool:
    """True unless the diff stat says a path lost no line (`-` is a file git counted as binary)."""
    return count is not None and count[1] != "0"


def _held_tests(root: Path, rule: list[str] | None) -> int:
    listed = _split_nul(_git(root, "ls-files", "-z", "-c", "-o", "--exclude-standard"))
    return sum(
        1 for path in listed if _is_test_path(path, rule) and (root / path).is_file()
    )


def _test_changes(
    report: _Report,
    root: Path,
    args: argparse.Namespace,
    tracked: list[tuple[str, str]],
    untracked: list[str],
    counts: dict[str, tuple[str, str]],
) -> None:
    """Section 7: the census of changed test paths, the plan over test paths only, and one row for
    each hunk that removes or changes an assertion in an edited test or a shared test helper."""
    rule: list[str] | None = (
        None
        if args.tests is None
        else [entry.replace("\\", "/").removeprefix("./") for entry in args.tests]
    )
    tokens: list[str] = args.assertion
    print(
        "test paths: "
        + (f"--tests entries only: {', '.join(rule)}" if rule else _TEST_RULE)
    )
    letters = {path: letter for letter, path in tracked}
    every = sorted(set(letters) | set(untracked))
    changed = [path for path in every if _is_test_path(path, rule)]
    added = sum(1 for path in changed if letters.get(path, "?") in ("A", "?"))
    deleted = sum(1 for path in changed if letters.get(path) == "D")
    plus = minus = binary = 0
    for path in changed:
        more, fewer = counts.get(path, ("0", "0"))
        if more == "-":
            binary += 1
        else:
            plus, minus = plus + int(more), minus + int(fewer)
    try:
        held = str(_held_tests(root, rule))
    except _GitError as exc:
        report.fail(f"test changes: the test paths could not be listed ({exc})")
        held = "an unknown number of"
    print(
        f"census: {len(changed)} of {len(every)} changed path(s) are test paths "
        f"({added} added, {len(changed) - added - deleted} modified, {deleted} deleted; "
        f"+{plus} -{minus} lines{f', {binary} binary' if binary else ''}); "
        f"the repository holds {held} test path(s)"
    )
    readable = [p for p in changed if Path(p).suffix.lower() in _CODE_EXTENSIONS]
    print(
        f"read: {len(readable)} of {len(changed)} changed test path(s) have a code extension; "
        f"{len(changed) - len(readable)} not read"
    )

    if args.plan is None:
        print(
            "plan: comparison over test paths not run (no --plan given; counted once, in section 2)"
        )
    else:
        try:
            entries = _read_plan(Path(args.plan))
        except OSError:
            print(
                "plan: comparison over test paths not run (the plan was unreadable, see section 2)"
            )
        else:
            planned = [entry for entry in entries if _is_test_path(entry, rule)]
            outside = [
                path
                for path in changed
                if not any(_covers(entry, path) for entry in entries)
            ]
            idle = [
                entry
                for entry in planned
                if not any(_covers(entry, path) for path in changed)
            ]
            print(f"plan: {len(planned)} of {len(entries)} plan path(s) are test paths")
            print(
                f"changed test paths not in plan ({len(outside)}): {', '.join(outside) or 'none'}"
            )
            print(
                f"planned test paths not changed ({len(idle)}): {', '.join(sorted(idle)) or 'none'}"
            )

    try:
        diff = _git(
            root,
            "diff",
            "--no-renames",
            "--no-ext-diff",
            "--text",
            "-U0",
            "--no-color",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            args.base,
            "--",
            *_CODE_DIFF_PATHSPECS,
        ).decode("utf-8", "replace")
        hunks = _read_hunks(diff)
    except _GitError as exc:
        report.fail(f"test changes: the diff could not be read ({exc})")
        hunks = None
    if hunks is not None:
        pool = _added_text(hunks, root, untracked, rule)
        rows: list[_Row] = []
        other: dict[str, int] = {}
        unread: list[str] = []
        modified_read = deleted_read = 0
        for path in readable:
            letter = letters.get(path, "?")
            if letter in ("A", "?"):
                continue
            mine = [hunk for hunk in hunks if hunk.path == path]
            if not mine and _lost_lines(counts.get(path)):
                unread.append(path)
                continue
            if letter == "D":
                deleted_read += 1
                rows.append(_deleted_row(path, mine, pool, tokens))
            else:
                modified_read += 1
                found, other[path] = _hunk_rows(path, mine, pool, tokens)
                rows += found
        listed = rows[: max(args.max_rows, 0)]
        if rows:
            print(
                "columns: kind, where (path:line in the base), what changed, what covers it now, "
                'a broken version that passes the old test and fails the new one (or "none")'
            )
        for row in listed:
            print(f"{row.kind}\t{row.where}\t{row.what}\tUNKNOWN\tUNKNOWN")
            for line in row.lines:
                print(f"  {line}")
        if rows:
            kinds = ", ".join(
                f"{kind} {sum(1 for row in rows if row.kind == kind)}"
                for kind in _ROW_KINDS
            )
            print(
                f"rows: {len(rows)} ({kinds}) over {modified_read} modified and "
                f"{deleted_read} deleted test file(s) read"
            )
        elif changed:
            print(
                f"no rows: {modified_read} modified and {deleted_read} deleted test file(s) read, "
                "none removes or changes an assertion line"
            )
        else:
            print("no rows: no test path changed")
        if len(rows) > len(listed):
            report.fail(
                f"test changes: {len(rows) - len(listed)} more row(s) not listed "
                f"(--max-rows {args.max_rows})"
            )
        if unread:
            more = f" and {len(unread) - 5} more" if len(unread) > 5 else ""
            report.fail(
                f"test changes: {len(unread)} changed test file(s) lost lines in the diff stat but "
                f"git printed no hunk for them, so they were not read (a diff driver or a text "
                f"conversion may be in the way): {', '.join(unread[:5])}{more}"
            )
        counted = sorted((path, count) for path, count in other.items() if count)
        for path, count in counted:
            print(f"other removed lines: {path}\t{count}")
        if not counted:
            print(
                f"other removed lines: none in {modified_read} modified test file(s) read"
            )
    print(
        "LIMIT: a line is an assertion when it holds a token (assert*, expect*, should, .toX(, "
        "t.Error or t.Fatal calls, raises, all matched case-sensitively, plus each --assertion: "
        "a capitalised form such as Assert.Equal( needs --assertion Assert., and a project "
        "directory such as MyApp.Tests/ is a test path only through --tests) and is not a "
        "comment, so a "
        "data-driven pin, an assertion built by a helper and the later lines of a multi-line "
        "assertion are seen by their token lines only (a needle table shows in the other removed "
        "lines count: open it by hand); stronger or weaker is not judged; skip and xfail markers "
        "are not read; MOVED? means identical text was added elsewhere, not that it still guards "
        "the same thing; what covers it now and the broken version are for the review to fill in "
        "and stay UNKNOWN until read."
    )


def _token(value: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError("an assertion token cannot be empty")
    return value


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the post-task review's mechanical checks."
    )
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--plan")
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--roots", nargs="+", default=["."])
    parser.add_argument("--matrix")
    parser.add_argument("--max-symbols", type=int, default=30)
    parser.add_argument("--max-files", type=int, default=15)
    parser.add_argument("--tests", nargs="+")
    parser.add_argument("--assertion", action="append", default=[], type=_token)
    parser.add_argument("--max-rows", type=int, default=40)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    report = _Report()
    try:
        root = Path(_git(None, "rev-parse", "--show-toplevel").decode("utf-8").strip())
    except _GitError as exc:
        report.fail(f"not inside a git work tree ({exc})")
        return report.finish(0, 0)
    try:
        sha = (
            _git(root, "rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
            .decode()
            .strip()
        )
        status = _split_nul(
            _git(root, "diff", "--no-renames", "--name-status", "-z", args.base, "--")
        )
        numstat = _split_nul(
            _git(root, "diff", "--no-renames", "--numstat", "-z", args.base, "--")
        )
        untracked = _split_nul(
            _git(root, "ls-files", "-z", "--others", "--exclude-standard")
        )
        tracked_total = len(_split_nul(_git(root, "ls-files", "-z")))
    except _GitError as exc:
        report.fail(
            f"base ref '{args.base}' does not resolve to a commit, or git failed ({exc}); pass --base <ref>"
        )
        return report.finish(0, 0)
    print(f"review_core: base={args.base} ({sha[:7]})")

    tracked = [(status[i], status[i + 1]) for i in range(0, len(status) - 1, 2)]
    changed = sorted({path for _, path in tracked} | set(untracked))
    changed_set = set(changed)
    deleted = {path for letter, path in tracked if letter == "D"}
    present = [path for path in changed if path not in deleted]

    report.open(1, "Changed files")
    for letter, path in sorted(tracked, key=lambda item: item[1]):
        print(f"{letter}\t{path}")
    for path in sorted(untracked):
        print(f"?\t{path}")
    print(
        f"changed: {len(changed)} ({len(tracked)} tracked, {len(untracked)} untracked) "
        f"of {tracked_total} tracked and {len(untracked)} untracked files"
    )
    if not changed:
        print(
            f"NOTE: nothing differs from {args.base}; if the work is already committed, pass --base <ref>"
        )

    report.open(2, "Diff stat (raw counts; untracked files counted by lines)")
    counts: dict[str, tuple[str, str]] = {}
    for record in numstat:
        added, deleted_count, path = record.split("\t", 2)
        counts[path] = (added, deleted_count)
    added_total = deleted_total = binary = 0
    for path in changed:
        if path in untracked:
            data = (root / path).read_bytes()
            if _style(data)[0] == "binary":
                counts[path] = ("-", "-")
            else:
                counts[path] = (
                    str(
                        data.count(b"\n")
                        + (1 if data and not data.endswith(b"\n") else 0)
                    ),
                    "0",
                )
        added, removed = counts.get(path, ("0", "0"))
        if added == "-":
            binary += 1
            print(f"binary\t{path}")
        else:
            added_total, deleted_total = (
                added_total + int(added),
                deleted_total + int(removed),
            )
            print(f"+{added} -{removed}\t{path}")
    print(
        f"total: +{added_total} -{deleted_total} in {len(changed)} file(s)"
        + (f" ({binary} binary)" if binary else "")
    )
    if args.plan is None:
        report.skip("plan comparison (no --plan given)")
    else:
        try:
            entries = _read_plan(Path(args.plan))
        except OSError as exc:
            report.fail(f"plan {Path(args.plan).name} unreadable ({exc.strerror})")
        else:
            outside = [
                path
                for path in changed
                if not any(_covers(entry, path) for entry in entries)
            ]
            idle = [
                entry
                for entry in entries
                if not any(_covers(entry, path) for path in changed)
            ]
            print(f"plan: {len(entries)} path(s) in {Path(args.plan).name}")
            print(
                f"changed, not in plan ({len(outside)}): {', '.join(sorted(outside)) or 'none'}"
            )
            print(
                f"in plan, not changed ({len(idle)}): {', '.join(sorted(idle)) or 'none'}"
            )

    report.open(3, "Dependents of changed and given names")
    derived: dict[str, set[str]] = {}
    skipped: set[str] = set()
    try:
        derived, skipped = _derive_symbols(root, args.base, untracked)
    except _GitError as exc:
        report.fail(f"dependents: the diff could not be read ({exc})")
    labels = {
        name: "signature changed" if sides == {"added", "removed"} else sorted(sides)[0]
        for name, sides in derived.items()
    }
    given = [name for name in dict.fromkeys(args.symbol) if name not in labels]
    names = sorted(labels) + given
    code_specs = _code_pathspecs(args.roots)
    scope_all = _scope(root, args.roots)
    scope_code = _scope(root, code_specs)
    print(
        f"scan: git grep -n --untracked -I -F; derived names over {scope_code} code files, "
        f"given names over {scope_all} files (roots: {' '.join(args.roots)})"
    )
    print(
        f"symbols: {len(labels)} derived from definition lines, {len(given)} given; "
        f"skipped by rule: {len(skipped)} ({_SKIP_RULE})"
    )
    for name in names[: max(args.max_symbols, 0)]:
        label = labels.get(name, "given")
        everywhere = name in args.symbol
        try:
            hits = _search(
                root,
                name,
                args.roots if everywhere else code_specs,
                whole_word=name in labels and not everywhere,
            )
        except _GitError as exc:
            report.fail(f"dependents: the search for {name} failed ({exc})")
            continue
        outside_diff = sorted(path for path in hits if path not in changed_set)
        print(
            f"{name} ({label}): {sum(map(len, hits.values()))} hits in {len(hits)} files; "
            f"{len(outside_diff)} outside the changed set"
        )
        if label != "added" or everywhere:
            for path in outside_diff[: max(args.max_files, 0)]:
                print(f"  UNKNOWN\t{path}\t{len(hits[path])} hit(s)")
            if len(outside_diff) > args.max_files:
                report.fail(
                    f"dependents: {name}: {len(outside_diff) - args.max_files} more outside file(s) "
                    f"not listed (--max-files {args.max_files})"
                )
        if not hits:
            surface = scope_all if everywhere else scope_code
            print(f"  none found over {surface} files in scope")
    rest = names[max(args.max_symbols, 0) :]
    if rest:
        report.fail(
            f"dependents: {len(rest)} symbol(s) not searched (over --max-symbols {args.max_symbols}): {', '.join(rest[:8])}"
        )
    print(
        "LIMIT: a caller list from grep is a floor (dynamic dispatch, reflection, string-keyed lookup and "
        "config-driven wiring are invisible to it) and a common name over-counts. Derived names come only from "
        "definition lines and are searched only in code files; a name given with --symbol is searched in every "
        "file as a fixed string, so add a flag, a key or a message that way. An added name prints counts only: "
        "nothing written earlier can have read a name that did not exist, so its outside hits are collisions "
        "(list them with --symbol NAME). Record each UNKNOWN as checked and unaffected, checked and updated, "
        "or leave it UNKNOWN."
    )

    report.open(4, "Line endings (worktree against the base's stored form)")
    tally: dict[str, int] = dict.fromkeys(_STYLE_ORDER, 0)
    flagged = 0
    status_of = {path: letter for letter, path in tracked}
    for path in present:
        style, lf, crlf = _style((root / path).read_bytes())
        tally[style] += 1
        if style == "binary":
            print(f"{path}\tbinary (skipped)")
        elif style == "mixed":
            flagged += 1
            print(f"{path}\tmixed (lf={lf} crlf={crlf})\tMIXED")
        else:
            stored = ""
            if status_of.get(path, "A") not in ("A", "?"):
                blob = _git(root, "cat-file", "blob", f"{sha}:{path}", ok=(0, 128))
                stored = _style(blob)[0]
            if stored in ("lf", "crlf") and style in ("lf", "crlf") and stored != style:
                flagged += 1
                eol = re.search(
                    r"i/(\S+)\s+w/(\S+)",
                    _git(root, "ls-files", "--eol", "--", path).decode(
                        "utf-8", "replace"
                    ),
                )
                print(
                    f"{path}\t{style}\tCHANGED stored {stored}, now {style} [i/{eol.group(1) if eol else '?'} w/{eol.group(2) if eol else '?'}]"
                )
            else:
                print(f"{path}\t{style}")
    kinds = ", ".join(f"{kind} {tally[kind]}" for kind in _STYLE_ORDER if tally[kind])
    print(f"endings: {kinds or 'no files'}; flagged {flagged} of {len(present)}")
    print(
        "LIMIT: 'stored' is the blob at the base; core.autocrlf or .gitattributes can explain a CHANGED row."
    )

    report.open(5, "Lint and format scope")
    commands = _commands(root)
    if commands is None:
        report.fail(
            "lint scope (no AGENTS.md or CLAUDE.md with a Commands section at the repository root)"
        )
    else:
        source, lines = commands
        text = "\n".join(lines)
        named = {
            tool: ext
            for tool, ext in _TOOLS.items()
            if re.search(rf"(?<![\w-]){re.escape(tool)}(?![\w-])", text)
        }
        print(
            f'commands: {source} section "Commands" ({len(lines)} line(s)); tools named: {", ".join(sorted(named)) or "none"}'
        )
        by_extension: dict[str, list[str]] = {}
        for path in present:
            by_extension.setdefault(Path(path).suffix.lower() or "(none)", []).append(
                path
            )
        covered = 0
        for extension in sorted(by_extension):
            tools = sorted(tool for tool, exts in named.items() if extension in exts)
            covered += len(by_extension[extension]) if tools else 0
            print(
                f"{extension}\t{len(by_extension[extension])} file(s)\t{', '.join(tools) or 'NO TOOL named in the commands covers it'}"
            )
        print(
            f"lint scope: {covered} of {len(present)} changed file(s) have a named tool; {len(present) - covered} have none"
        )
        print(
            "LIMIT: scope is read from the commands' text and a built-in table of each tool's default "
            "extensions (a newer default missing from it reads as NO TOOL); no linter was run and no "
            "tool config was read, so a file a tool excludes still reads as covered."
        )

    report.open(6, "Documentation matrix")
    sample = (
        Path(__file__).resolve().parent.parent / "references" / "doc-impact-matrix.md"
    )
    matrix = Path(args.matrix) if args.matrix else sample
    try:
        rows = _matrix_rows(matrix.read_text(encoding="utf-8"))
    except OSError as exc:
        report.fail(f"documentation matrix {matrix.name} unreadable ({exc.strerror})")
    else:
        path_rows = [
            (cell, docs, [_path_regex(t) for t in re.findall(r"`([^`]+)`", cell)])
            for cell, docs in rows
        ]
        event_rows = sum(1 for _, _, patterns in path_rows if not patterns)
        label = (
            "SAMPLE (the skill's reference, one backend's layout; pass --matrix with the project's own)"
            if not args.matrix
            else matrix.name
        )
        print(
            f"matrix: {label} ({len(rows) - event_rows} path row(s), {event_rows} event row(s) judged by hand)"
        )
        matched = 0
        for path in changed:
            hit = [
                (cell, docs)
                for cell, docs, patterns in path_rows
                if any(p.match(path) for p in patterns)
            ]
            matched += 1 if hit else 0
            for cell, docs in hit:
                print(f"{path}\t-> {docs}\t(row: {cell})")
            if not hit:
                print(f'{path}\tNO MATRIX ROW (UNKNOWN, not "no doc affected")')
        print(
            f"matrix: {matched} of {len(changed)} changed file(s) matched a row; {len(changed) - matched} have no row"
        )
        print(
            "LIMIT: a match names the docs to open, not whether they are stale; event rows are judged by hand."
        )

    report.open(7, "Test changes")
    _test_changes(report, root, args, tracked, untracked, counts)

    return report.finish(len(changed), _SECTIONS - len(report.failed))


if __name__ == "__main__":
    sys.exit(main())
