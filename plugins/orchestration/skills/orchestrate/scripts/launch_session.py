#!/usr/bin/env python
"""Print, run or check the one command that starts a headless `claude -p` session.

WHY THIS IS A SCRIPT AND NOT MORE PROSE
---------------------------------------
Section 2a of the orchestrate skill listed the measured facts of a headless launch -- `-p` and
not `--bg`, standard input cut off, repo-relative paths, the project's host-rules file injected --
and left each orchestrator to rebuild the command from them. One orchestrator launched seven
sessions that way; the next, on the same initiative, launched none and pasted prompts into new
windows instead, because the practice lived in the first one's context and not in the kit. A
command that prints the whole line makes the background start as cheap as pasting, and what a
script enforces cannot be forgotten the way a paragraph can.

Nothing here writes to the repository, and no environment variable is set: the cap on how long a
`-p` run waits for background work belongs in the settings `env`, never in front of a command.

Modes
-----
  print BRIEF   print shows the exact command and starts nothing. It is one line, quoted for a
                POSIX shell and ending in the redirect that cuts standard input off, ready for
                the Bash tool's `run_in_background`.
  run BRIEF     run starts the session only when this mode is named. It echoes the command on
                stderr, starts the CLI with standard input cut off, passes the CLI's output
                through, and exits 0 when the CLI exited 0 and 1 when it did not.
  check         check sends no prompt and costs nothing. It appends a flag no CLI knows, LAST,
                and reads what the CLI says while it parses its arguments.

BRIEF and --rules-file are paths relative to the working directory and must exist there: an
absolute path in an argument is rewritten by the Git Bash path conversion, so the CLI would read
another file. --model, --effort and --permission-mode are passed through without a list of
values: the CLI has none for models, and it only warns about an effort value it does not know.

What `check` reads
------------------
The CLI rejects an unknown flag while it parses, before any session starts, and names the first
one it meets. The sentinel goes last, so a real flag the CLI does not know is named instead of
it. The check passes only when the CLI names the sentinel in an `unknown option` error. It fails
when the CLI names another flag, refuses a flag's value, or warns that it will ignore a value
(measured on CLI 2.1.316: an unknown --effort value only warns, and the default effort runs). It
sees flag names and syntax and nothing else: a model name is not checked, and the CLI reads a
file only after it has parsed, so this script checks the brief and the rules file itself.

Exit codes: 0 = printed, the CLI exited 0, or the check passed; 1 = the CLI exited non-zero, or
the check found a flag the CLI will not take; 2 = a usage error, a refused path, or a check that
could not measure (the CLI was not found, accepted the sentinel, or answered in words this script
does not know). CANNOT MEASURE is exit 2, never a pass.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

SENTINEL = "--zzz-sentinel"
NULL_STDIN = "< /dev/null"
DEFAULT_CLI = "claude"
PROMPT = "Read {brief} and follow it: it is your whole task."

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UNKNOWN = 2

LABEL_PASS = "PASS"
LABEL_FAIL = "FAIL"
LABEL_CANNOT = "CANNOT MEASURE"

# Commander's wording, which the CLI parses its arguments with: its own errors start with a lower
# case `error:`, the CLI's messages with `Error:`, and warnings with `Warning:`.
UNKNOWN_OPTION = "error: unknown option '"
REFUSED_VALUE = "error: option "
WARNING = "Warning:"
SHOWN_LINES = 6


class Verdict(NamedTuple):
    """What a check concluded: the exit code, the label it is read by, and why."""

    code: int
    label: str
    detail: str


def refusal(path: str) -> str | None:
    """Why `path` is not a path relative to the working directory, or None when it is.

    The shape only: whether the file is there is the caller's question. A rooted path is refused
    because the Git Bash path conversion rewrites it before the CLI sees it (measured: an argument
    that named a missing file reached the CLI under the install root), so the CLI would read a
    different file and say nothing.
    """
    if not path.strip():
        return "the path is empty"
    if path.startswith(("/", "\\")):
        return f"{path!r} is rooted; pass a path relative to the working directory"
    if len(path) >= 2 and path[1] == ":" and path[0].isascii() and path[0].isalpha():
        return f"{path!r} starts with a drive letter; pass a path relative to the working directory"
    return None


def build_flags(
    model: str | None,
    effort: str | None,
    permission_mode: str | None,
    rules_file: str | None,
) -> list[str]:
    """The flags of a launch in a fixed order, so the same inputs print the same line."""
    flags = ["-p"]
    for name, value in (
        ("--model", model),
        ("--effort", effort),
        ("--permission-mode", permission_mode),
        ("--append-system-prompt-file", rules_file),
    ):
        if value is not None:
            flags += [name, value]
    return flags


def launch_args(flags: list[str], brief: str) -> list[str]:
    """The arguments of a real launch: the flags, then the one line that points at the brief."""
    return [*flags, PROMPT.format(brief=brief)]


def check_args(flags: list[str]) -> list[str]:
    """The arguments of a check: the same flags, no prompt, and the sentinel LAST, because the CLI
    names the first unknown flag it meets and a real flag it does not know must be reached first."""
    return [*flags, SENTINEL]


def render(cli: list[str], args: list[str]) -> str:
    """The command as one line for a POSIX shell, ending in the redirect that cuts stdin off."""
    return f"{shlex.join([*cli, *args])} {NULL_STDIN}"


def first_unknown_option(lines: list[str]) -> str | None:
    """The flag named by the first `error: unknown option '<flag>'` line, or None. A line that
    only mentions a flag, or a warning that says it was ignored, is not the CLI rejecting it."""
    for line in lines:
        if line.startswith(UNKNOWN_OPTION):
            rest = line[len(UNKNOWN_OPTION) :]
            end = rest.find("'")
            if end != -1:
                return rest[:end]
    return None


def classify(output: str) -> Verdict:
    """Read what the CLI said to a check. Only the sentinel named in an unknown-option error is a
    pass, and a warning beside it is not: the CLI would still ignore what it warned about."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    named = first_unknown_option(lines)
    warnings = [line for line in lines if line.startswith(WARNING)]
    refused = [line for line in lines if line.startswith(REFUSED_VALUE)]
    if named is not None and named != SENTINEL:
        return Verdict(
            EXIT_FAILED,
            LABEL_FAIL,
            f"the CLI does not know {named}, so it never reached the sentinel",
        )
    if named == SENTINEL:
        if warnings:
            return Verdict(
                EXIT_FAILED,
                LABEL_FAIL,
                f"the CLI parsed every flag but warned it will not honour one: {warnings[0]}",
            )
        return Verdict(
            EXIT_OK,
            LABEL_PASS,
            "the CLI named the sentinel in an unknown-option error, so every flag before it "
            "parsed (names and syntax only: a model name and a file are not checked)",
        )
    if refused:
        return Verdict(
            EXIT_FAILED, LABEL_FAIL, f"the CLI refused a flag's value: {refused[0]}"
        )
    said = lines[0] if lines else "(nothing)"
    return Verdict(
        EXIT_UNKNOWN,
        LABEL_CANNOT,
        "the CLI did not reject the sentinel (it accepted it, answered in words this script "
        f"does not know, or said nothing), so nothing was learned and this is not a pass; it said: {said}",
    )


def refuse(message: str) -> int:
    sys.stderr.write(f"refused: {message}\n")
    return EXIT_UNKNOWN


def invalid_input(mode: str, brief: str | None, rules_file: str | None) -> str | None:
    """Why an input cannot be used, or None. The brief and the rules file are checked here and
    not by the CLI, which reads a file only after it has parsed every flag."""
    named = [("--rules-file", rules_file)]
    if mode != "check":
        named.insert(0, ("the brief", brief))
    for label, path in named:
        if path is None:
            continue
        reason = refusal(path)
        if reason is not None:
            return f"{label}: {reason}"
        if not Path(path).is_file():
            return f"{label}: {path!r} is not a file relative to the working directory"
    return None


def run_session(cli: list[str], args: list[str]) -> int:
    """Start the session with standard input cut off, and report whether the CLI succeeded."""
    found = shutil.which(cli[0])
    if found is None:
        return refuse(f"{cli[0]!r} was not found on PATH")
    sys.stderr.write(f"launch: {render(cli, args)}\n")
    try:
        done = subprocess.run(
            [found, *cli[1:], *args], stdin=subprocess.DEVNULL, check=False
        )
    except OSError as error:
        return refuse(f"{cli[0]!r} could not be started: {error}")
    if done.returncode != 0:
        sys.stderr.write(f"the CLI exited {done.returncode}\n")
        return EXIT_FAILED
    return EXIT_OK


def check_flags(cli: list[str], args: list[str]) -> int:
    """Run the CLI with the sentinel and say what it answered. Nothing is sent to the model: there
    is no prompt, and standard input is cut off, so even a CLI that accepted the sentinel would
    have nothing to run."""
    print(f"CHECK  {shlex.join([*cli, *args])}")
    found = shutil.which(cli[0])
    if found is None:
        return report(
            Verdict(EXIT_UNKNOWN, LABEL_CANNOT, f"{cli[0]!r} was not found on PATH")
        )
    try:
        done = subprocess.run(
            [found, *cli[1:], *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        return report(
            Verdict(
                EXIT_UNKNOWN,
                LABEL_CANNOT,
                f"{cli[0]!r} could not be started: {error}",
            )
        )
    answer = done.stdout + done.stderr
    for line in [row for row in answer.splitlines() if row.strip()][:SHOWN_LINES]:
        print(f"  cli said: {line.strip()}")
    return report(classify(answer))


def report(verdict: Verdict) -> int:
    print(f"{verdict.label}  {verdict.detail}")
    return verdict.code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument(
        "--model", help="passed through; a typo in a model name is not caught"
    )
    options.add_argument(
        "--effort", help="passed through; the CLI warns about a value it does not know"
    )
    options.add_argument(
        "--permission-mode",
        dest="permission_mode",
        help="passed through; from CLI 2.1.302 a -p run with no mode denies what needs approval",
    )
    options.add_argument(
        "--rules-file",
        dest="rules_file",
        help="the project's host-rules file, passed as --append-system-prompt-file; relative",
    )
    options.add_argument(
        "--cli",
        default=DEFAULT_CLI,
        help="the CLI to start: a name or path, or a quoted command (default: %(default)s)",
    )
    modes = parser.add_subparsers(dest="mode", required=True)
    for name, text in (
        ("print", "print the exact command and start nothing"),
        ("run", "start the session; the only mode that starts one"),
    ):
        sub = modes.add_parser(name, parents=[options], help=text)
        sub.add_argument(
            "brief", help="path of the brief, relative to the working directory"
        )
    modes.add_parser(
        "check",
        parents=[options],
        help="zero-cost flag check against the installed CLI (exit 2 = could not measure)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        # The CLI's own words may hold characters this console cannot encode.
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    mode: str = args.mode
    brief: str | None = getattr(args, "brief", None)
    rules_file: str | None = args.rules_file
    try:
        cli = shlex.split(args.cli)
    except ValueError as error:
        return refuse(f"--cli is not a command string: {error}")
    if not cli:
        return refuse("--cli is empty")
    problem = invalid_input(mode, brief, rules_file)
    if problem is not None:
        return refuse(problem)
    flags = build_flags(args.model, args.effort, args.permission_mode, rules_file)
    if mode == "check":
        return check_flags(cli, check_args(flags))
    if brief is None:  # argparse requires one in the other two modes
        return refuse("no brief was given")
    if mode == "run":
        return run_session(cli, launch_args(flags, brief))
    sys.stdout.write(render(cli, launch_args(flags, brief)) + "\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
