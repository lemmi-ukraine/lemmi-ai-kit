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

Exit codes, as in the lint:

    0  clean: every entry landed in at least one target. Under --current-contents an exit 0
       is an upper bound, never a clean audit.
    1  rows to adjudicate: a [LOSS?] row or a no-probe row remains. Exit 1 means rows to
       adjudicate; it is not an error, and it is not a verdict either.
    2  usage or error: no ref (and no --current-contents), a snapshot that is missing, unreadable
       or holds no entry, or a diff that could not be taken. A run that could not measure never
       exits 0.

For each entry in the snapshot it extracts the most distinctive backticked identifiers and greps
every promotion target. Zero hits => CANDIDATE LOSS. This is a review list, not a verdict: an
ARCHIVED entry legitimately has no new home, and an entry whose only tokens are incidental paths
from its anecdote can false-positive. Adjudicate each by hand; the point is that nothing is
dropped silently.

Forces UTF-8 stdout so the output is readable on consoles that default to a legacy codepage.
"""

import argparse
import contextlib
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# Every surface a promotion can land on. Keep in sync with consolidation-actions.md.
TARGET_GLOBS = (
    "AGENTS.md",
    "CLAUDE.md",
    "docs/**/*.md",
    ".claude/skills/**/*.md",
    ".cursor/**/*.md",
    ".cursor/**/*.mdc",
    ".kiro/steering/*.md",
    "tasks/*.md",
    # Source-tree surfaces: adjust these two to the project's own layout. A promotion
    # that lands in code lands in a module README or a docstring, and this script can
    # only see the trees it is told about -- a missing glob reports a false [LOSS?].
    "src/**/README.md",
    "src/**/*.py",
)

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


def load_targets(root: Path) -> str:
    """FALLBACK haystack: the full CURRENT text of every target file.

    Unsound on its own and reachable only through --current-contents. It cannot tell
    "this drain promoted the entry" from "this token already appeared somewhere
    in 30k lines of docs", so a token like `settings` or a path the entry merely
    mentions marks it landed. That is not hypothetical: it is how five harness
    entries were deleted with no promotion in the 2026-07-31 drain, the very
    failure this script exists to catch.

    Prefer :func:`load_added_targets`.
    """
    blob = []
    for g in TARGET_GLOBS:
        for f in root.glob(g):
            # The buffer itself is not a landing site.
            if f.is_file() and f.name != "learnings.md":
                with contextlib.suppress(OSError):
                    blob.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(blob)


def load_added_targets(root: Path, base_ref: str) -> str | None:
    """Haystack of ONLY the lines this drain ADDED to target files.

    The sound version of :func:`load_targets`. A promotion is an addition, so the
    evidence that an entry landed is new text — matching against pre-existing
    content proves nothing.

    Each pathspec carries the `:(glob)` magic. A plain pathspec lets `*` cross `/` and gives
    `**/` no meaning, so `docs/**/*.md` skipped `docs/x.md` and `tasks/*.md` matched
    `tasks/a/b.md`. With the magic a pathspec means here what the same pattern means to
    `Path.glob` in the fallback: `**/` matches zero or more directories, `*` never crosses `/`.

    Returns ``None`` (not an empty string) when the diff cannot be taken, so the
    caller can distinguish "no additions" from "could not check" and refuse to
    report a clean audit on the strength of a failed command.
    """
    cmd = [
        "git",
        "-C",
        str(root),
        "diff",
        "--unified=0",
        "--no-color",
        base_ref,
        "--",
        *(f":(glob){glob}" for glob in TARGET_GLOBS),
    ]
    try:
        proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
            cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    # '+' lines only, minus the '+++' file headers.
    return "\n".join(
        line[1:]
        for line in proc.stdout.split("\n")
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
    if args.current_contents:
        hay = load_targets(root)
        print(CURRENT_CONTENTS_WARNING)
    else:
        hay = load_added_targets(root, args.base_ref)
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
