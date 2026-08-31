#!/usr/bin/env python3
"""Certify an ad-hoc checker can actually see before its verdict is quoted.

WHY THIS EXISTS
---------------
A leading cause of reversed conclusions is an in-session verifier whose zero meant
"my pattern never matched", not "the defect is absent". Measured: >=9 recurrences
across >=3 sessions AFTER the rule against it was promoted into three separate prose
surfaces. Prose asked sessions to probe their checkers; nothing made them. This script is the seam: it FAILS (exit 1) when the
checker cannot see, so a clean run is evidence rather than an assertion.

Real instances this would have caught:
  * a `"$` anchor that never matched under CRLF -> "TOTAL OVER CAP: 0" believed for a
    whole session until an unrelated crash exposed the loop had never run
  * `fluen` false-matching "influence" (false POSITIVE - the negative fixture catches it)
  * a marker-gated linter returning zero findings for a file it never opened
  * a checker blind to the very region its rule covered

USAGE
-----
    python probe_checker.py --cmd '<shell command with {file}>' \
        --positive <file-that-MUST-match> \
        --negative <file-that-MUST-NOT-match> \
        [--expect-positive N] [--label "what this checks"]

`{file}` in --cmd is substituted with each fixture path. The checker's own output is
counted by lines unless --count-mode is `grep-c` (parse a bare integer on stdout).

EXIT CODES
    0  checker demonstrated sight: positive matched, negative did not
    1  checker is BLIND or over-matching - its verdict must not be quoted
    2  bad invocation

Self-test (this script obeys the rule it enforces):
    python probe_checker.py --self-test
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# A stamp the caller pastes next to the number the checker produced, so a reader can
# tell a probed verdict from an unprobed one without re-running anything.
STAMP = "probe_checker: positive={pos} negative={neg} verdict={verdict}"


class ProbeError(RuntimeError):
    """Invocation problem - distinct from a checker that ran and proved blind."""


def _normalise_exe_path(cmd: str) -> str:
    """On Windows, backslash the leading executable token if it is a real file.

    `shell=True` is cmd.exe there, and cmd.exe does not accept a forward-slash path for
    the command ITSELF -- it reads `/Scripts` as a switch. The result is no stdout, no
    usable error, and a probe reporting `BLIND ... verdict=UNUSABLE` for a checker that
    works perfectly. A false BLIND is the exact mirror of the false-clean this script
    exists to catch, and it sends the reader hunting a defect in a sound instrument.

    Only the FIRST token is touched, and only when it resolves to a file that exists, so
    a `grep a/b` pattern or a `--flag=x/y` argument is never rewritten.
    """
    if os.name != "nt":
        return cmd
    stripped = cmd.lstrip()
    if not stripped or stripped[0] in ("'", '"'):
        return cmd  # already quoted - the author took control of it
    head, sep, tail = stripped.partition(" ")
    if "/" not in head:
        return cmd
    if not Path(head).is_file():
        return cmd
    return head.replace("/", "\\") + sep + tail


def _run(cmd: str, fixture: Path) -> tuple[int, str]:
    """Run the checker against one fixture. Returns (exit_code, stdout)."""
    if "{file}" not in cmd:
        raise ProbeError("--cmd must contain the {file} placeholder")
    filled = _normalise_exe_path(cmd.replace("{file}", str(fixture)))
    # shell=True: the checkers this wraps are ad-hoc grep/rg/python one-liners.
    proc = subprocess.run(  # noqa: S602 - deliberate, see above
        filled,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # When the ONLY thing the command produced was an error message, it did not run --
    # and counting that as "0 matches" is how a broken invocation becomes a BLIND verdict
    # against an innocent checker. Such a case looks like "no output and no visible
    # error" precisely BECAUSE this function captured stderr and discarded it. Surface it.
    #
    # KNOWN LIMIT, stated so a zero is read correctly: a command that fails SILENTLY --
    # nonzero exit, nothing on either channel -- is deliberately NOT caught here, because
    # that is also exactly how `rg` reports a legitimate no-match, which is the expected
    # result for a negative fixture. Distinguishing them needs the caller's knowledge of
    # the tool, not a heuristic here.
    if proc.returncode != 0 and not proc.stdout.strip() and proc.stderr.strip():
        raise ProbeError(
            f"checker exited {proc.returncode} on {fixture.name} having written nothing "
            f"to stdout and this to stderr: {proc.stderr.strip()!r}\n"
            f"Command as run: {filled!r}\n"
            f"That is an INVOCATION failure, not a blind checker -- fix the command "
            f"before concluding anything about what the checker can see."
        )
    return proc.returncode, proc.stdout


def count_matches(cmd: str, fixture: Path, count_mode: str) -> int:
    """How many matches did the checker report for this fixture?

    `grep-c` mode reads a bare integer off stdout (what `grep -c` prints). Any other
    mode counts non-empty stdout lines. A checker that CRASHES counts as zero matches
    AND is reported by the caller - a traceback with "timeouts: 0" above it is exactly
    the shape that has fooled this repo before.
    """
    code, out = _run(cmd, fixture)
    if count_mode == "grep-c":
        nums = re.findall(r"^\s*(\d+)\s*$", out, flags=re.MULTILINE)
        if not nums:
            # grep -c prints nothing only when the command failed to run at all.
            if code not in (0, 1):
                raise ProbeError(
                    f"checker failed on {fixture.name} (exit {code}); stdout was {out!r}"
                )
            return 0
        return sum(int(n) for n in nums)
    return len([ln for ln in out.splitlines() if ln.strip()])


def probe(
    cmd: str,
    positive: Path,
    negative: Path,
    expect_positive: int = 1,
    count_mode: str = "lines",
    label: str = "",
) -> tuple[bool, str]:
    """Return (ok, human-readable report). ok=False means DO NOT QUOTE the verdict."""
    for p in (positive, negative):
        if not p.is_file():
            raise ProbeError(f"fixture does not exist: {p}")

    pos = count_matches(cmd, positive, count_mode)
    neg = count_matches(cmd, negative, count_mode)

    problems: list[str] = []
    if pos < expect_positive:
        problems.append(
            f"BLIND: positive fixture yielded {pos} match(es), expected >= {expect_positive}. "
            "A zero here means the pattern never matched - it does NOT mean the defect is absent."
        )
    if neg != 0:
        problems.append(
            f"OVER-MATCHING: negative fixture yielded {neg} match(es), expected 0. "
            "The checker fires on content it should ignore, so its findings are inflated."
        )

    verdict = "CAN-SEE" if not problems else "UNUSABLE"
    lines = [
        f"probe_checker {'PASS' if not problems else 'FAIL'}"
        + (f" - {label}" if label else ""),
        f"  cmd            : {cmd}",
        f"  positive ({positive.name}): {pos} match(es)  [need >= {expect_positive}]",
        f"  negative ({negative.name}): {neg} match(es)  [need 0]",
    ]
    lines += [f"  ! {p}" for p in problems]
    lines.append("  " + STAMP.format(pos=pos, neg=neg, verdict=verdict))
    return (not problems), "\n".join(lines)


def _self_test() -> int:
    """Prove this script can itself see - one known-positive, one known-negative.

    The script that enforces "probe your checker" would be self-refuting if it shipped
    without probing itself. Both directions are asserted: a working checker must PASS,
    and each of the two failure shapes (blind, over-matching) must FAIL.
    """
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        pos = d / "has_needle.txt"
        neg = d / "no_needle.txt"
        pos.write_text("alpha\nNEEDLE here\nomega\n", encoding="utf-8")
        neg.write_text("alpha\nomega\n", encoding="utf-8")

        cases: list[tuple[str, str, bool]] = [
            ("a checker that works", "grep -c NEEDLE {file} || true", True),
            # Blind: pattern can never match either fixture.
            ("a blind checker", "grep -c ZZZ_NEVER {file} || true", False),
            # Over-matching: matches every line, so the negative fixture is non-zero.
            ("an over-matching checker", "grep -c '' {file} || true", False),
        ]

        failures = 0
        for name, cmd, expect_ok in cases:
            ok, report = probe(
                cmd, pos, neg, expect_positive=1, count_mode="grep-c", label=name
            )
            status = "ok" if ok == expect_ok else "SELF-TEST FAILURE"
            if ok != expect_ok:
                failures += 1
            print(f"[{status}] {name}: probe returned ok={ok}, expected {expect_ok}")
            print(report)
            print()

        print(
            f"self-test: {len(cases) - failures}/{len(cases)} cases behaved as specified"
        )
        return 1 if failures else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Prove an ad-hoc checker can see before quoting its verdict."
    )
    ap.add_argument("--cmd", help="checker command; must contain {file}")
    ap.add_argument("--positive", help="fixture the checker MUST match")
    ap.add_argument("--negative", help="fixture the checker must NOT match")
    ap.add_argument("--expect-positive", type=int, default=1)
    ap.add_argument("--count-mode", choices=("lines", "grep-c"), default="lines")
    ap.add_argument("--label", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not (args.cmd and args.positive and args.negative):
        ap.error("--cmd, --positive and --negative are required (or use --self-test)")

    try:
        ok, report = probe(
            args.cmd,
            Path(args.positive),
            Path(args.negative),
            expect_positive=args.expect_positive,
            count_mode=args.count_mode,
            label=args.label,
        )
    except ProbeError as exc:
        print(f"probe_checker: invocation error - {exc}", file=sys.stderr)
        return 2

    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
