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
                             [--matrix FILE] [--max-symbols N]

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

OUTPUT: a header, six numbered sections (changed files, diff stat, dependents, line endings, lint
and format scope, documentation matrix), then one summary line. Each section ends with the limit of
its own instrument.

EXIT CODES
    0  every section ran; what it found is printed for the review to judge
    2  something could not be measured (a NOT CHECKED line says what): not a git work tree, an
       unresolvable base, an unreadable plan or matrix, no Commands section to read, or more names
       than a cap allows. Cannot-measure is never a pass, so gate on `!= 0`.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

_SECTIONS = 6

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

    return report.finish(len(changed), _SECTIONS - len(report.failed))


if __name__ == "__main__":
    sys.exit(main())
