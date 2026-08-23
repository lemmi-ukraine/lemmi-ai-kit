"""SKILL.md §4e full-corpus user-corrections sweep.

Scans every ``USER:`` block in the extractor's emitted ``sessions/*.md`` transcripts
(main sessions only — ``sessions/sub/`` holds orchestrator briefs, not the human) for
correction / change-demand markers, and writes the candidates to
``user_corrections_sweep.txt`` in the retro output dir. The analyst then classifies
the hits BY HAND, applying SKILL.md §4e's false-positive filters ("no need for X" is
a design decision, technical terms aren't feedback, questions are clarifications).

The deep-dives do NOT substitute for this sweep: in a measured run, deep-diving a
subset was substituted for it and several >=2-occurrence correction patterns sat
unread in the unscanned sessions until the user asked.

Pure stdlib, Python 3.9+. No hardcoded paths.

Usage:
    python sweep_user_corrections.py [retro-dir]    # default: .ai/tmp/retro
Exit codes: 0 ok (count printed), 2 sessions dir missing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKERS = re.compile(
    r"(wrong|incorrect|mistake|why (have|did|do|are|is|was) |you (haven|didn|did not|havent|missed|forgot|lost|broke)"
    r"|haven'?t you|have you .{0,30}(fix|chang|commit|push|answer|done|complete)"
    r"|\bfix\b|\bfixed\b|chang|revert|undo|\bredo\b|remove|delete|\bstop\b|don'?t|do not\b|\bmust\b|never|always"
    r"|instead|rather|not what|\bno[,!]|nope|properly|make sure|again\b|actually|wait\b|re-?check|re-?do"
    r"|didn'?t work|doesn'?t work|not work|still (not|the same|broken|fails)|missing|forgot"
    r"|don'?t (get|understand)|do not (get|understand)|undert?stand|rephrase|rehpase)",
    re.I,
)

# USER blocks that are injected machinery, not the human speaking.
SKIP_PREFIX = ("<", "Base directory for this skill", "[Request interrupted", "Caveat:", "ARGUMENTS:")


def sweep(retro_dir: Path) -> list[str]:
    root = retro_dir / "sessions"
    if not root.is_dir():
        raise FileNotFoundError(f"sessions dir not found: {root}")
    results: list[str] = []
    for f in sorted(root.glob("*.md")):
        sid = f.name[:8]
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        blocks: list[tuple[int, str]] = []
        cur_start, cur_buf = None, []
        for i, ln in enumerate(lines, 1):
            if ln.startswith("USER: "):
                if cur_start is not None:
                    blocks.append((cur_start, " ".join(cur_buf)))
                cur_start, cur_buf = i, [ln[6:]]
            elif cur_start is not None:
                if ln.startswith(("ASSISTANT", "  [", "---", "===")):
                    blocks.append((cur_start, " ".join(cur_buf)))
                    cur_start, cur_buf = None, []
                else:
                    cur_buf.append(ln.strip())
        if cur_start is not None:
            blocks.append((cur_start, " ".join(cur_buf)))

        for start, text in blocks:
            t = text.strip()
            if not t or t.startswith(SKIP_PREFIX):
                continue
            if MARKERS.search(t):
                results.append(f"[{sid}:{start}] {t[:260]}")
    return results


def main(argv: list[str]) -> int:
    retro_dir = Path(argv[1]) if len(argv) > 1 else Path(".ai/tmp/retro")
    try:
        results = sweep(retro_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out_path = retro_dir / "user_corrections_sweep.txt"
    out_path.write_text("\n".join(results), encoding="utf-8")
    print(f"{len(results)} candidate USER messages with correction/change markers -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
