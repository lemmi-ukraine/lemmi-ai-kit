"""Drain completeness audit — did every drained learnings entry actually LAND somewhere?

Phase 5's existing verification confirms entries were REMOVED from the buffer. It cannot see the
opposite failure: an entry removed without its knowledge reaching any home. That gap is real — the
2026-07-31 drain lost 6 of 87 entries (7%) that way, including a rule the consolidation then
cross-referenced as if it existed, and manual accounting did not catch any of them.

Usage (run BEFORE deleting the pre-drain snapshot):

    python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <pre-drain-snapshot.md> [pre-drain-commit]

Pass the pre-drain commit as the second argument. Without it the audit matches against the
CURRENT contents of every target file, which cannot distinguish a promotion this drain made from
a token that already happened to appear somewhere — so it silently over-reports 'landed'.

For each entry in the snapshot it extracts the most distinctive backticked identifiers and greps
every promotion target. Zero hits => CANDIDATE LOSS. This is a review list, not a verdict: an
ARCHIVED entry legitimately has no new home, and an entry whose only tokens are incidental paths
from its anecdote can false-positive. Adjudicate each by hand; the point is that nothing is
dropped silently.

Forces UTF-8 stdout so the output is readable on consoles that default to a legacy codepage.
"""

import contextlib
import re
import subprocess
import sys
from pathlib import Path

with contextlib.suppress(Exception):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

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

    Unsound on its own and kept only for the no-baseline case. It cannot tell
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
        *TARGET_GLOBS,
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


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    snapshot = Path(argv[1])
    if not snapshot.is_file():
        print(f"snapshot not found: {snapshot}")
        return 2

    root = repo_root()
    base_ref = argv[2] if len(argv) > 2 else None
    if base_ref:
        hay = load_added_targets(root, base_ref)
        if hay is None:
            print(
                f"ERROR: could not diff against '{base_ref}'. Refusing to fall back to "
                "the whole-file scan — it would report a clean audit it cannot support."
            )
            return 2
        print(f"haystack: lines ADDED since {base_ref} (sound mode)\n")
    else:
        hay = load_targets(root)
        print(
            "WARNING: no base ref given, scanning CURRENT file contents. Any "
            "pre-existing occurrence of a token counts as a landing, so 'landed' is "
            "an UPPER BOUND and losses can hide behind it. Pass the pre-drain commit "
            "as the second argument for a sound audit.\n"
        )
    lost: list[tuple[str, list[str]]] = []
    weak: list[str] = []
    landed = 0

    for chunk in ENTRY_SPLIT_RE.split(snapshot.read_text(encoding="utf-8"))[1:]:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
