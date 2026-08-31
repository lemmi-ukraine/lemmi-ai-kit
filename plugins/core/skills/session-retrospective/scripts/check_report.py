#!/usr/bin/env python3
"""Gate a session-retrospective report before it is presented or called finished.

WHY THIS EXISTS
---------------
Three failure modes, all MEASURED on the 2026-08-29 run of this very skill. Each was
already prose in SKILL.md, and prose caught none of them:

  1. A required section was silently absent. Phase 6 lists "Pipeline Health" as a
     Required section; the report shipped without it and nothing said so. A missing
     section reads exactly like a section with nothing to report.

  2. A dispatched fan-out worker returned AFTER the report was written, so its whole
     result was dropped. W2 (the Phase-4e operator-correction sweep, 366 messages
     classified into 24/18/23) finished at 17:17; the report was written at 17:04.
     The report never mentions it. Nothing reconciled dispatched against returned.

  3. Phase-7 outputs were written but left unreachable from any commit. The changelog
     entry and 15 learnings existed only inside `stash@{0}` -- so the next run's
     Phase 4h, which reads `.ai/ai-changelog.md`, would have found nothing. The report
     even points at that entry as its durable record.

This script FAILS (exit 1) on each, so a clean run is evidence instead of an assertion.

USAGE
-----
    python check_report.py --report .ai/retrospectives/{date}-retrospective.md
    python check_report.py --report <path> --check sections
    python check_report.py --report <path> --check workers --date 2026-08-29

Findings go to STDOUT, one per line (so `probe_checker.py` can count them).
The summary goes to STDERR, so stdout line count == finding count.

EXIT CODES
    0  no findings
    1  findings -- the report is not finished
    2  bad invocation

PROBE THIS CHECKER BEFORE QUOTING ITS ZERO (AGENTS.md, gate-verdict clause 5):
    python ${CLAUDE_PLUGIN_ROOT}/skills/post-task-review/scripts/probe_checker.py \
      --cmd 'python ${CLAUDE_SKILL_DIR}/scripts/check_report.py --check sections --report {file}' \
      --positive ${CLAUDE_SKILL_DIR}/scripts/fixtures/report_missing_sections.md \
      --negative ${CLAUDE_SKILL_DIR}/scripts/fixtures/report_complete.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Required report sections. Each entry is (label, [alias regexes]) -- a report may use
# its own numbering and wording, so match the CONCEPT, not one literal heading. Matched
# against heading lines only (never a whole-file substring): a report that merely
# mentions "pipeline health" in prose must not score as having the section.
REQUIRED_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Prior-Report Reconciliation (Phase 4h)",
        [r"prior[- ]report", r"reconciliation", r"phase\s*4h"],
    ),
    ("Sub-Agent Behavioral Findings (Phase 3b)", [r"sub[- ]agent", r"phase\s*3b"]),
    ("Pipeline Health", [r"pipeline health"]),
    (
        "Recurring-Mistake Taxonomy (Phase 4a)",
        [r"recurring[- ]mistake", r"mistake taxonomy", r"phase\s*4a"],
    ),
    (
        "Uncaptured Feedback (Phase 4e)",
        [
            r"uncaptured feedback",
            r"user feedback",
            r"operator feedback",
            r"corrections?\s*/",
            r"phase\s*4e",
        ],
    ),
    (
        "Repetitive Questions (Phase 4d)",
        [r"repetitive question", r"missing default", r"phase\s*4d"],
    ),
    ("Absence Sweep (Phase 4i)", [r"absence sweep", r"didn'?t bark", r"phase\s*4i"]),
    ("Recommendations (P1-P5)", [r"recommendation"]),
]

HEADING_RE = re.compile(r"^#{1,4}\s+(.*\S)\s*$")
WORKER_LABEL_RE = re.compile(r"^\d{8}-\d{6}-(?P<label>.+?)\.(out|err)$")


def repo_root(start: Path) -> Path:
    """Derive the repo root at runtime -- never hardcode a machine-specific path."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return start


def read_text(path: Path) -> str:
    """CRLF-safe read: decode the bytes, never normalise.

    `.ai/` files may be pure CRLF on some checkouts and LF on others, and `splitlines()`
    handles both. Normalising here would make a line-ending difference invisible to any
    caller that compares this text against a git blob.
    """
    return path.read_bytes().decode("utf-8", errors="replace")


def headings(text: str) -> list[str]:
    return [
        m.group(1).lower()
        for line in text.splitlines()
        if (m := HEADING_RE.match(line))
    ]


def check_sections(report: Path) -> list[str]:
    found = headings(read_text(report))
    out: list[str] = []
    for label, aliases in REQUIRED_SECTIONS:
        if not any(re.search(a, h) for h in found for a in aliases):
            out.append(f"{report.name}: MISSING required section -- {label}")
    return out


def check_workers(report: Path, root: Path, date: str) -> list[str]:
    """The W2 defect: a worker that returned after the report was written.

    A fan-out result that lands after the report is invisible -- there is no error, the
    report simply never mentions it. Compare mtimes, and check the label was referenced.
    """
    logs = root / ".ai" / "dispatch" / "logs"
    if not logs.is_dir():
        return []
    stamp = date.replace("-", "")
    report_mtime = report.stat().st_mtime
    body = read_text(report).lower()
    out: list[str] = []
    for entry in sorted(logs.glob(f"{stamp}-*.out")):
        m = WORKER_LABEL_RE.match(entry.name)
        if not m or entry.stat().st_size == 0:
            continue
        label = m.group("label")
        token = label.split("-")[0]
        if entry.stat().st_mtime > report_mtime:
            delta = int((entry.stat().st_mtime - report_mtime) // 60)
            out.append(
                f"{report.name}: worker '{label}' returned {delta} min AFTER the report was "
                f"written -- its result cannot be in the report"
            )
        elif token.lower() not in body and label.lower() not in body:
            out.append(
                f"{report.name}: worker '{label}' returned but is never referenced in the report"
            )
    return out


def _git(root: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout


def check_durability(root: Path, date: str) -> list[str]:
    """Phase 7: the changelog entry is the sole reconciliation source of record.

    A working-tree-only or stash-only entry is NOT durable -- the next run reads the
    committed file. Verify the entry is reachable from HEAD, not merely present on disk.
    """
    out: list[str] = []
    heading = f"## {date}"

    changelog = root / ".ai" / "ai-changelog.md"
    if not changelog.is_file():
        return [f"ai-changelog.md: not found at {changelog}"]

    on_disk = heading in read_text(changelog)
    code, committed = _git(root, ["show", "HEAD:.ai/ai-changelog.md"])
    in_head = code == 0 and heading in committed

    if not on_disk:
        out.append(f"ai-changelog.md: NO entry dated {date} -- Phase 7 never wrote one")
    elif not in_head:
        out.append(
            f"ai-changelog.md: the {date} entry exists on disk but is NOT reachable from HEAD "
            f"-- uncommitted or stash-only, so the next run's Phase 4h will not see it"
        )

    hyp = root / ".ai" / "improvement-hypotheses.md"
    if hyp.is_file() and heading not in read_text(hyp):
        out.append(
            f"improvement-hypotheses.md: NO hypothesis dated {date} -- Phase 7 requires a "
            f"companion falsifiable prediction for the P1/P2 changes applied"
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument(
        "--check", default="all", choices=["all", "sections", "workers", "durability"]
    )
    ap.add_argument(
        "--date", help="YYYY-MM-DD; default: parsed from the report filename"
    )
    args = ap.parse_args(argv)

    report: Path = args.report
    if not report.is_file():
        print(f"check_report: report not found: {report}", file=sys.stderr)
        return 2

    # Only the worker and durability checks are date-scoped. Requiring a date for a
    # bare --check sections run made this script exit 2 with an empty stdout, which a
    # caller reads as "no findings" -- the probe caught exactly that on first write.
    needs_date = args.check in ("all", "workers", "durability")
    date = args.date
    if not date:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", report.name)
        if m:
            date = m.group(1)
        elif needs_date:
            print(
                "check_report: --date required (not derivable from filename)",
                file=sys.stderr,
            )
            return 2
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"check_report: bad --date {date!r}", file=sys.stderr)
            return 2

    root = repo_root(report.resolve().parent)
    findings: list[str] = []
    if args.check in ("all", "sections"):
        findings += check_sections(report)
    if args.check in ("all", "workers"):
        findings += check_workers(report, root, date)
    if args.check in ("all", "durability"):
        findings += check_durability(root, date)

    for f in findings:
        print(f)
    print(
        f"check_report[{args.check}]: {len(findings)} finding(s)"
        + ("" if findings else " -- report is complete"),
        file=sys.stderr,
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
