"""Drain completeness audit — did every drained learnings entry actually LAND somewhere?

Phase 5's existing verification confirms entries were REMOVED from the buffer. It cannot see the
opposite failure: an entry removed without its knowledge reaching any home. That gap is real — the
2026-07-31 drain lost 6 of 87 entries (7%) that way, including a rule the consolidation then
cross-referenced as if it existed, and manual accounting did not catch any of them.

Usage (run BEFORE deleting the pre-drain snapshot):

    python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <pre-drain-snapshot.md> <base-ref>
    python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" --current-contents <pre-drain-snapshot.md>

The base ref is mandatory: the commit that was HEAD before the promotions. Pass HEAD itself while
the promotions are still uncommitted; once they are committed pass the commit BEFORE the promotion
commit (<promotion-commit>~1), never HEAD, which would leave nothing added. The audit then matches
only the lines ADDED to the target files since that ref, so a token that already appeared
somewhere cannot pass for a promotion.

With no ref the script exits 2 and names the one flag that asks for the other scan:

    --current-contents   match against the CURRENT contents of every target file instead. Any
                         pre-existing occurrence of a token then counts as a landing, so 'landed'
                         is an UPPER BOUND and losses can hide behind it. Use it only when no
                         baseline exists at all, and never quote its figure as an audit.

The ten default globs (TARGET_GLOBS) are one layout's promotion surfaces. A home outside them,
which the project's own AGENTS.md names, is added on every run, once per glob:

    --surface GLOB       add a glob of files, relative to the project root, to the defaults; it
                         never replaces one. It reaches git as a `:(glob)` pathspec and
                         --current-contents as a `Path.glob` pattern; the shapes the two are known
                         to read differently exit 2 (see `surface_glob`), and three still pass:
                         letter case on a case-insensitive file system, a `[^...]` class, and a `**`
                         inside a name on Python 3.11. Write a plain glob in the tree's own case.

Exit codes, as in the lint:

    0  clean: every entry landed in at least one target. Under --current-contents an exit 0
       is an upper bound, never a clean audit.
    1  rows to adjudicate: a [LOSS?] row or a no-probe row remains. Exit 1 means rows to
       adjudicate; it is not an error, and it is not a verdict either.
    2  usage or error: no ref (and no --current-contents), a snapshot that is missing, unreadable
       or holds no entry, or a diff that could not be taken. A run that could not measure never
       exits 0.

For each entry in the snapshot it extracts the most distinctive backticked identifiers and greps
every promotion target. A file that holds the entries themselves is never a landing site, in
either scan and whatever the globs match: the buffer (any `learnings.md`), the snapshot under
audit (the path given, whatever its name) and every other pre-drain snapshot
(`learnings-pre-drain-*.md`), so a surface that reaches `.ai/` cannot land an entry in its own
copy. Zero hits => CANDIDATE LOSS. This is a review list, not a verdict: an
ARCHIVED entry legitimately has no new home, and an entry whose only tokens are incidental paths
from its anecdote can false-positive. Adjudicate each by hand; the point is that nothing is
dropped silently.

Forces UTF-8 stdout so the output is readable on consoles that default to a legacy codepage.
"""

import argparse
import contextlib
import fnmatch
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path, PureWindowsPath

# The default promotion surfaces, one layout's homes. Keep in sync with the Drain Landing Audit
# section of consolidation-actions.md. A home outside them (the project's own AGENTS.md names
# its homes) is added per run with --surface, which never replaces one of these.
TARGET_GLOBS = (
    "AGENTS.md",
    "CLAUDE.md",
    "docs/**/*.md",
    ".claude/skills/**/*.md",
    ".cursor/**/*.md",
    ".cursor/**/*.mdc",
    ".kiro/steering/*.md",
    "tasks/*.md",
    # Source-tree surfaces of the same layout. A promotion that lands in code lands in a
    # module README or a docstring, and this script can only see the trees it is told
    # about -- a missing glob reports a false [LOSS?], so a project whose code lives
    # elsewhere names that tree with --surface.
    "src/**/README.md",
    "src/**/*.py",
)

# The characters that make a glob more than a literal path.
GLOB_CHARS = "*?["

# The names of the files that hold the entries themselves, so a token found in one proves
# nothing: the buffer, and every pre-drain snapshot (an older one still holds the KEEP entries
# that dwelt through earlier drains). The snapshot under audit is left out by identity as well,
# whatever its name. `is_landing_site` applies the rule, and both scans call it.
NEVER_A_LANDING_SITE = ("learnings.md", "learnings-pre-drain-*.md")

# Tokens too generic to prove a landing.
STOP = {
    "true", "false", "none", "null", "if", "for", "the", "and", "not", "status",
    "test", "tests", "error", "int", "str", "bool", "list", "dict", "data", "id",
}

ENTRY_SPLIT_RE = re.compile(r"^### (?=\[)", re.M)
BACKTICK_RE = re.compile(r"`([^`\n]{4,60})`")

CURRENT_CONTENTS_WARNING = (
    "WARNING: --current-contents given, scanning CURRENT file contents. Any "
    "pre-existing occurrence of a token counts as a landing, so 'landed' is "
    "an UPPER BOUND and losses can hide behind it. Pass the pre-drain commit "
    "as the second argument for a sound audit.\n"
)

NO_REF_MESSAGE = (
    "no base ref given. The audit is sound only against the lines a drain ADDED, so pass "
    "the commit to compare with as the second argument: HEAD while the promotions are "
    "uncommitted, <promotion-commit>~1 once they are committed. To scan the CURRENT "
    "contents of the target files instead (unsound: a token that predates the drain counts "
    "as a landing), pass --current-contents."
)

BOTH_MESSAGE = (
    "a base ref and --current-contents contradict each other: the ref selects the sound "
    "scan of the lines added since it, the flag the unsound scan of current contents. "
    "Pass one."
)

EPILOG = """\
base ref (second argument): the commit BEFORE the promotions.
  promotions still uncommitted: HEAD
  promotions already committed: <promotion-commit>~1, never HEAD
  mandatory unless --current-contents is given

exit codes:
  0  clean: every entry landed in at least one target
     (under --current-contents an exit 0 is an upper bound, never a clean audit)
  1  rows to adjudicate: a [LOSS?] row or a no-probe row remains
     (exit 1 means rows to adjudicate; it is not an error)
  2  usage or error: no ref, a snapshot that is missing, unreadable or holds no entry,
     or a diff that could not be taken

never a landing site, in either scan and whatever the globs match:
  the buffer (any learnings.md), the snapshot under audit (whatever its name)
  and every other pre-drain snapshot (learnings-pre-drain-*.md)
"""


def repo_root() -> Path:
    """Nearest ancestor holding both .ai/ and .git/, else the working directory.

    A fixed parent depth cannot work from a plugin install, where no ancestor of this
    file is inside the adopter's project at all.
    """
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".ai").is_dir() and (parent / ".git").exists():
            return parent
    return Path.cwd()


def is_landing_site(path: Path, snapshot: Path) -> bool:
    """The one rule both scans apply to each file the globs match: can an entry land in it?

    Not in a file that holds the entries themselves, where every token of every entry is
    found: the buffer and every pre-drain snapshot, by name (`NEVER_A_LANDING_SITE`), and the
    snapshot under audit, by identity, whatever its name (a scratch reconstruction under audit
    is left out too). Without the rule a surface that reaches `.ai/` lands every entry.
    """
    if any(fnmatch.fnmatchcase(path.name, name) for name in NEVER_A_LANDING_SITE):
        return False
    try:
        return not path.samefile(snapshot)
    except OSError:
        return True  # a path the diff lists as deleted: it adds no line either way


def load_targets(
    root: Path, snapshot: Path, globs: Sequence[str] = TARGET_GLOBS
) -> str:
    """FALLBACK haystack: the full CURRENT text of every landing site the globs match.

    Unsound on its own and reachable only through --current-contents. It cannot tell
    "this drain promoted the entry" from "this token already appeared somewhere
    in 30k lines of docs", so a token like `settings` or a path the entry merely
    mentions marks it landed. That is not hypothetical: it is how five harness
    entries were deleted with no promotion in the 2026-07-31 drain, the very
    failure this script exists to catch.

    Prefer :func:`load_added_targets`.
    """
    blob = []
    for g in globs:
        for f in root.glob(g):
            if f.is_file() and is_landing_site(f, snapshot):
                with contextlib.suppress(OSError):
                    blob.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(blob)


def _git_diff(root: Path, *args: str) -> str | None:
    """The output of `git diff <args>` run in `root`, or None when it could not be taken."""
    try:
        proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "-C", str(root), "diff", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return None
    return proc.stdout if proc.returncode == 0 else None


def load_added_targets(
    root: Path, base_ref: str, snapshot: Path, globs: Sequence[str] = TARGET_GLOBS
) -> str | None:
    """Haystack of ONLY the lines this drain ADDED to the landing sites the globs match.

    The sound version of :func:`load_targets`. A promotion is an addition, so the
    evidence that an entry landed is new text — matching against pre-existing
    content proves nothing.

    Each pathspec carries the `:(glob)` magic. A plain pathspec lets `*` cross `/` and gives
    `**/` no meaning, so `docs/**/*.md` skipped `docs/x.md` and `tasks/*.md` matched
    `tasks/a/b.md`. With the magic a pathspec means here what the same pattern means to
    `Path.glob` in the fallback: `**/` matches zero or more directories, `*` never crosses `/`.

    The fallback's rule holds here too: the files the diff touches are listed first (NUL
    separated, never quoted, relative to `root` like the pathspecs), and each one
    :func:`is_landing_site` refuses leaves the diff as a literal exclude.

    Returns ``None`` (not an empty string) when the diff cannot be taken, so the
    caller can distinguish "no additions" from "could not check" and refuse to
    report a clean audit on the strength of a failed command.
    """
    pathspecs = [f":(glob){glob}" for glob in globs]
    listed = _git_diff(root, "--name-only", "-z", "--relative", base_ref, "--", *pathspecs)
    if listed is None:
        return None
    excluded = [
        f":(exclude,literal){name}"
        for name in listed.split("\0")
        if name and not is_landing_site(root / name, snapshot)
    ]
    diff = _git_diff(root, "--unified=0", "--no-color", base_ref, "--", *pathspecs, *excluded)
    if diff is None:
        return None
    # '+' lines only, minus the '+++' file headers.
    return "\n".join(
        line[1:]
        for line in diff.split("\n")
        if line.startswith("+") and not line.startswith("+++")
    )


def tokens_for(title: str, body: str) -> list[str]:
    """Distinctive backticked identifiers, longest first (longest = most specific)."""
    out = []
    for tok in BACKTICK_RE.findall(f"{title}\n{body[:1400]}"):
        tok = tok.strip().strip("()")
        if " " in tok and not any(c in tok for c in "/._"):
            continue  # prose in backticks, not a symbol
        if tok.lower() in STOP:
            continue
        out.append(tok)
    return sorted(set(out), key=len, reverse=True)[:6]


def surface_glob(value: str) -> str:
    """One `--surface` value, refused in the shapes git and the current-contents scan read differently.

    The value reaches git as a `:(glob)` pathspec and the current-contents scan as a
    `Path.glob` pattern, and the two agree on a relative glob of files. They part ways on the
    shapes refused here: git reads an empty value as the whole tree where `Path.glob` raises;
    an absolute path or a `..` leaves the project; a backslash escapes in git and separates on
    Windows; a leading `:` is pathspec magic that `Path.glob` reads as a name; and a value
    that ends in `/` or `**` takes every file below it in git and no file in `Path.glob`. A
    wildcard-free value that names a directory parts them the same way, which only the tree
    can tell, so `main` refuses that one. Three differences are not caught here: letter case, which
    `Path.glob` ignores on a case-insensitive file system and git does not; a `[^...]` class, which
    git negates and `Path.glob` reads as a caret; and, on Python 3.11, a `**` inside a name, where
    `Path.glob` raises.
    """
    parts = value.split("/")
    if not value:
        problem = "is empty"
    elif "\\" in value:
        problem = "holds a backslash (write '/')"
    elif value.startswith(("/", ":")) or PureWindowsPath(value).drive:
        problem = "is not a glob relative to the project root"
    elif ".." in parts:
        problem = "climbs out of the project with '..'"
    elif parts[-1] in ("", "**"):
        problem = "names a directory, not its files (end it with a file glob such as '/**/*')"
    else:
        return value
    raise argparse.ArgumentTypeError(
        f"{value!r} {problem}, so git and the current-contents scan would not read it alike"
    )


class _AuditParser(argparse.ArgumentParser):
    """A parser that refuses a line naming neither a base ref nor --current-contents.

    The rule lives in the parser, not in `main`, so anything that parses a command line with
    `build_parser()` meets it: a printed command with no ref fails to parse.
    """

    def parse_args(self, args=None, namespace=None):  # type: ignore[override]
        parsed = super().parse_args(args, namespace)
        if parsed.base_ref is None and not parsed.current_contents:
            self.error(NO_REF_MESSAGE)
        if parsed.base_ref is not None and parsed.current_contents:
            self.error(BOTH_MESSAGE)
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = _AuditParser(
        prog="drain_audit.py",
        description=(
            "Audit a learnings drain: did every entry of the pre-drain snapshot land in a "
            "promotion target? Prints a review list, not a verdict."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "snapshot",
        help="the pre-drain snapshot of the buffer: a copy made before any deletion",
    )
    parser.add_argument(
        "base_ref",
        nargs="?",
        help=(
            "the commit before the promotions (HEAD while they are uncommitted, "
            "<promotion-commit>~1 once committed); mandatory unless --current-contents"
        ),
    )
    parser.add_argument(
        "--current-contents",
        action="store_true",
        help=(
            "scan the CURRENT contents of every target file instead of the lines added "
            "since a ref. Unsound: a token that predates the drain counts as a landing, "
            "so the result is an upper bound. For when no baseline exists at all"
        ),
    )
    parser.add_argument(
        "--surface",
        action="append",
        default=[],
        type=surface_glob,
        metavar="GLOB",
        help=(
            "add a promotion surface to the ten default globs, for a home outside them; "
            "repeat it for each glob, and it never replaces a default. A glob of files "
            "relative to the project root, in the tree's own letter case: '**/' matches zero "
            "or more directories and '*' never crosses '/'"
        ),
    )
    return parser


def _force_utf8_stdout() -> None:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def main(argv: Sequence[str] | None = None) -> int:
    _force_utf8_stdout()
    args = build_parser().parse_args(argv)

    snapshot = Path(args.snapshot)
    if not snapshot.is_file():
        print(f"snapshot not found: {snapshot}")
        return 2
    try:
        text = snapshot.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: could not read the snapshot {snapshot}: {exc}")
        return 2
    chunks = ENTRY_SPLIT_RE.split(text)[1:]
    if not chunks:
        print(
            f"ERROR: no entries found in {snapshot} (an entry heading starts with "
            "'### ['), so nothing was measured. A run that cannot see its subject must "
            "not report a clean audit."
        )
        return 2

    root = repo_root()
    for glob in args.surface:
        if not any(char in glob for char in GLOB_CHARS) and (root / glob).is_dir():
            print(
                f"ERROR: --surface {glob!r} names a directory, so git and the current-contents "
                "scan would not read it alike (git takes every file below it, the scan none). "
                f"Pass '{glob}/**/*' for its files."
            )
            return 2
    # One parse feeds both scans: the same globs reach git and the current-contents scan, and
    # both leave out what `is_landing_site` refuses, the snapshot under audit among it.
    globs = (*TARGET_GLOBS, *args.surface)
    if args.current_contents:
        hay = load_targets(root, snapshot, globs)
        print(CURRENT_CONTENTS_WARNING)
    else:
        hay = load_added_targets(root, args.base_ref, snapshot, globs)
        if hay is None:
            print(
                f"ERROR: could not diff against '{args.base_ref}'. Refusing to fall back to "
                "the whole-file scan — it would report a clean audit it cannot support."
            )
            return 2
        print(f"haystack: lines ADDED since {args.base_ref} (sound mode)\n")
    lost: list[tuple[str, list[str]]] = []
    weak: list[str] = []
    landed = 0

    for chunk in chunks:
        title = chunk.split("\n", 1)[0].strip()
        toks = tokens_for(title, chunk)
        if not toks:
            weak.append(title)
        elif any(t in hay for t in toks):
            landed += 1
        else:
            lost.append((title, toks))

    total = landed + len(lost) + len(weak)
    print(f"entries scanned  : {total}")
    print(f"landed (>=1 tok) : {landed}")
    print(f"no probe tokens  : {len(weak)}")
    print(f"CANDIDATE LOSS   : {len(lost)}\n")
    for title, toks in lost:
        print(f"  [LOSS?] {title[:105]}")
        print(f"          probes: {toks}")
    if weak:
        print("\n  (no distinctive tokens — adjudicate by hand:)")
        for title in weak:
            print(f"   - {title[:105]}")
    if lost or weak:
        print("\nAdjudicate every row above before deleting the snapshot. Expected-clean rows:")
        print("  * ARCHIVED entries (already covered elsewhere / stale / superseded)")
        print("  * entries whose only tokens are incidental paths from their anecdote")
        print("\nexit 1 means rows to adjudicate (it is not an error).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
