"""Exercise the drain gate across every arm. Each case states the REQUIRED decision.

Pure stdlib. Run with:  python plugins/core/hooks/test_gate_learnings_drain.py

A guard that blocks unrelated work is worse than no guard — a repo-relative hook registration
once disabled every Bash and PowerShell call here for three sessions — so the ALLOW cases matter
as much as the DENY ones. Keep both halves.
"""

import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

GATE = str(pathlib.Path(__file__).with_name("gate_learnings_drain.py"))

work = pathlib.Path(tempfile.mkdtemp(prefix="gatetest-"))
(work / ".ai").mkdir(parents=True)
LEARN = work / ".ai" / "learnings.md"
LEARN.write_text(
    "# Learnings\n\n### A\nbody\n\n### B\nbody\n\n### C\nbody\n", encoding="utf-8"
)


def run(payload):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(work)
    proc = subprocess.run(
        [sys.executable, GATE],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.stdout.strip()


def decision(out):
    if not out:
        return "ALLOW"
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"].upper()
    except (ValueError, KeyError, AttributeError):
        return "MALFORMED:" + out[:80]


CASES = [
    (
        "Edit REMOVES 2 entries, no gate",
        "DENY",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(LEARN),
                "old_string": "### A\nbody\n\n### B\nbody\n",
                "new_string": "### A\nbody\n",
            },
        },
    ),
    (
        "Edit removes 1 of 2",
        "DENY",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(LEARN),
                "old_string": "### A\n\n### B\n",
                "new_string": "### A\n",
            },
        },
    ),
    (
        "Edit APPENDS an entry (the intake path must stay free)",
        "ALLOW",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(LEARN),
                "old_string": "### C\nbody\n",
                "new_string": "### C\nbody\n\n### D\nnew\n",
            },
        },
    ),
    (
        "Edit rewords, same entry count",
        "ALLOW",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(LEARN),
                "old_string": "### A\nbody\n",
                "new_string": "### A\nreworded\n",
            },
        },
    ),
    (
        "Edit on an UNRELATED file that removes headers",
        "ALLOW",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(work / "other.md"),
                "old_string": "### A\n\n### B\n",
                "new_string": "### A\n",
            },
        },
    ),
    (
        "Write shrinks 3 entries -> 1",
        "DENY",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(LEARN),
                "content": "# Learnings\n\n### A\nbody\n",
            },
        },
    ),
    (
        "Write grows 3 -> 4",
        "ALLOW",
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(LEARN),
                "content": "# L\n\n### A\n\n### B\n\n### C\n\n### D\n",
            },
        },
    ),
    (
        "Bash sed -i on learnings.md",
        "DENY",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "sed -i '/### A/d' .ai/learnings.md"},
        },
    ),
    (
        "Bash READS learnings.md (grep)",
        "ALLOW",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "grep -c '### ' .ai/learnings.md"},
        },
    ),
    (
        "Bash unrelated",
        "ALLOW",
        {"tool_name": "Bash", "tool_input": {"command": "ls -la"}},
    ),
    (
        "Read tool (not matched)",
        "ALLOW",
        {"tool_name": "Read", "tool_input": {"file_path": str(LEARN)}},
    ),
    ("malformed payload -> fail OPEN", "ALLOW", {"garbage": True}),
]


def main():
    fails = 0
    for name, want, payload in CASES:
        got = decision(run(payload))
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL':4}  want={want:5} got={got:5}  {name}")

    # With an approved gate record present, every DENY case must flip to ALLOW.
    gates = work / ".ai" / "consolidation-gates"
    gates.mkdir(parents=True, exist_ok=True)
    record = gates / f"{datetime.date.today().isoformat()}-plan-approved.md"
    record.write_text("x" * 250, encoding="utf-8")
    print("\n-- with an approved gate record for today --")
    for name, want, payload in CASES:
        if want != "DENY":
            continue
        got = decision(run(payload))
        ok = got == "ALLOW"
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL':4}  want=ALLOW got={got:5}  {name}")

    # A stub record must NOT satisfy the gate, or the gate is satisfied by typing anything.
    record.write_text("ok\n", encoding="utf-8")
    got = decision(run(CASES[0][2]))
    ok = got == "DENY"
    fails += not ok
    print(
        f"\n{'PASS' if ok else 'FAIL':4}  want=DENY  got={got:5}  "
        "stub (too-short) gate record is rejected"
    )

    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
