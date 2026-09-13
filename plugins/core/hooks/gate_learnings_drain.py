"""PreToolUse guard: a learnings DRAIN may not run without its approved plan.

Why this exists (measured, not theoretical): `learning-consolidator` Phase 3 ends with
"**STOP and wait for user approval before proceeding.**" — prose. The 2026-09-13 drain
removed **263** entries from `.ai/learnings.md` without ever presenting that plan. Prose
already said to; prose is what failed, so the rule is enforced here instead.

WHAT IT BLOCKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
Only **removal** of entries from `.ai/learnings.md` is gated. Appends are the intake path —
`task-learnings` writes to this file constantly and must stay frictionless — so a call that
adds entries, or leaves the entry count unchanged, is never blocked. The gate fires on the
one irreversible act: deleting entries that a promotion is supposed to have re-homed.

THE GATE RECORD
---------------
`.ai/consolidation-gates/<YYYY-MM-DD>-plan-approved.md`, containing the Phase 3 plan the
operator approved. Absent or empty -> the drain is denied with the path it needs.

HONEST LIMITS — read these before trusting the guard
----------------------------------------------------
1. **The record is forgeable.** Nothing here proves a human approved anything; a model can
   Write that file itself. What the guard changes is the SHAPE of the failure: skipping the
   gate stops being an omission (invisible, deniable, what happened on 2026-09-13) and
   becomes a conspicuous written claim in a dated file, which `consolidation-critic` and the
   changelog can be audited against afterwards. That is a real improvement and it is not
   enforcement. Closing it properly needs the stamp to come from a `UserPromptSubmit` hook —
   which sees the operator's own message and the model never gets to author — carrying a
   nonce this guard verifies. Sketched, deliberately not built: it is a bigger change than
   the defect warrants today.
2. **The Bash arm is best-effort.** It matches mutating shapes (`sed -i`, `>` redirect, a
   `python -c` touching the file). A guard that matches a token is routinely reached by a
   rephrasing — `python drain.py` with the path inside the script is invisible here. The
   Edit/Write arms are exact because they see the content; the Bash arm is a speed bump.
3. **Hook config snapshots at session start**, so registering this engages next session.
4. It fails **open** on any malformed payload. A guard that crashes must not block unrelated
   work.

Contract: reads the PreToolUse payload on stdin, prints a deny decision as JSON when the call
would remove entries without an approved plan, prints nothing otherwise. Never raises.
"""

import datetime
import json
import os
import re
import sys

LEARNINGS_SUFFIX = os.path.join(".ai", "learnings.md")
ENTRY_RE = re.compile(r"^### ", re.MULTILINE)

# Bash shapes that plausibly rewrite a file in place. Best-effort by construction (see limit 2).
_BASH_MUTATES = re.compile(
    r"(?:\bsed\b[^|;]*-i)|(?:>\s*[^|;>]*learnings\.md)|(?:\brm\b[^|;]*learnings\.md)"
    r"|(?:\bpython\b[^|;]*-c\b)|(?:\btee\b[^|;]*learnings\.md)",
    re.IGNORECASE,
)


def _targets_learnings(path):
    return isinstance(path, str) and path.replace("/", os.sep).endswith(
        LEARNINGS_SUFFIX
    )


def _count(text):
    return len(ENTRY_RE.findall(text or ""))


def _gate_record_exists(project_dir):
    """A non-trivial gate record dated today. Empty or missing -> no gate."""
    today = datetime.date.today().isoformat()
    path = os.path.join(
        project_dir, ".ai", "consolidation-gates", f"{today}-plan-approved.md"
    )
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return len(fh.read().strip()) >= 200, path
    except OSError:
        return False, path


def _reason(path, removed):
    return (
        f"BLOCKED: this call would remove {removed} entr"
        + ("y" if removed == 1 else "ies")
        + " from .ai/learnings.md, and no approved consolidation plan exists for today.\n\n"
        "A drain removes the only copy of knowledge that promotions are supposed to have "
        "re-homed. learning-consolidator Phase 3 requires the plan to be presented and "
        "APPROVED first; the 2026-09-13 drain removed 263 entries without one.\n\n"
        "To proceed:\n"
        "  1. Present the Phase 3 consolidation plan to the operator and WAIT.\n"
        f"  2. On approval, record it at: {path}\n"
        "  3. Re-run this edit.\n\n"
        "Appending to learnings.md is never blocked - only removal is."
    )


def main():
    try:
        payload = json.load(sys.stdin)
        tool = payload.get("tool_name", "")
        ti = payload.get("tool_input", {}) or {}
    except Exception:
        return  # fail open

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    removed = 0

    try:
        if tool in ("Edit", "MultiEdit"):
            if not _targets_learnings(ti.get("file_path")):
                return
            edits = ti.get("edits") or [ti]
            for e in edits:
                removed += max(
                    0, _count(e.get("old_string")) - _count(e.get("new_string"))
                )

        elif tool == "Write":
            if not _targets_learnings(ti.get("file_path")):
                return
            try:
                with open(ti["file_path"], encoding="utf-8", errors="replace") as fh:
                    current = _count(fh.read())
            except OSError:
                return  # new file: cannot be a removal
            removed = max(0, current - _count(ti.get("content")))

        elif tool in ("Bash", "PowerShell"):
            cmd = ti.get("command", "")
            if not isinstance(cmd, str) or "learnings.md" not in cmd:
                return
            if not _BASH_MUTATES.search(cmd):
                return
            removed = -1  # unknown magnitude; treat as a potential drain

        else:
            return
    except Exception:
        return  # fail open

    if removed == 0:
        return

    ok, path = _gate_record_exists(project_dir)
    if ok:
        return

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": _reason(
                    path, removed if removed > 0 else "an unknown number of"
                ),
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
