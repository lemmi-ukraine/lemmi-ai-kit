"""Check, read-only, whether one patch may land in a shared working tree now.

A session that lands work in a tree other sessions also write runs this immediately before it
commits (see ../references/landing-queue.md). It reads the repository and the files it is given,
and it applies, stages and commits nothing: when every check passes it PRINTS the commands that
land the patch, for the session to run itself, under the lock.

    python landing_gate.py check --repo PATH --parent ID --patch FILE --tree ID
                                 [--allow "STATUS LINE"]... [--paths FILE]

--parent and --tree are full object ids (40 or 64 hex characters); a ref name moves, so it is
refused. An --allow value is one line exactly as `git status --porcelain --untracked-files=all`
prints it: a path with a space in it is printed in double quotes. --paths names a text file with
one repository path per line. A --repo inside a working tree is checked at the tree's top.

It prints one line per check, in this order, each PASS, FAIL or NOT MEASURED with what it saw:
  (a) head    HEAD is the --parent commit
  (b) status  `git status --porcelain --untracked-files=all` prints exactly the --allow lines; a
              line that is not allowed, and an allowed line that is absent, are each named
  (c) staged  nothing is staged: `git diff-index --cached HEAD` names no path
  (d) replay  the patch, applied to the parent's tree in a private index (GIT_INDEX_FILE in a
              temporary folder, never the real index), writes the --tree tree
  (e) paths   with --paths: the paths the replayed tree changes against the parent are exactly
              the listed ones, a rename counting as two; NOT ASKED without --paths

Exit 0 only when every check measured and passed: it then prints the landing commands, with an
explicit pathspec on both `git add --` and `git commit --` and quoted for a POSIX shell, and
never runs them. Exit 1 when a check failed. Exit 2 when any check could not measure (git failed
or is missing, an input is missing or unreadable, the patch does not apply to the parent), even
if another check failed: cannot-measure is never a pass. No landing command is printed unless
it exits 0.

Every git call runs with --no-optional-locks, so `git status` does not rewrite the index. It
writes nothing in the working tree, the real index or any ref. The replay leaves unreferenced
blob and tree objects in the object store, which git's garbage collection removes, and it
deletes its temporary folder.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

NOTICE = "landing gate: read-only; it checks, and prints the landing commands without running them."
PASS = "PASS"
FAIL = "FAIL"
NOT_MEASURED = "NOT MEASURED"
NOT_ASKED = "NOT ASKED"
FULL_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
# Each would point git at another repository, index or object store than the one checked.
REDIRECTS = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
    }
)
TIMEOUT_SECONDS = 300
CHECKS = (
    ("a", "head"),
    ("b", "status"),
    ("c", "staged"),
    ("d", "replay"),
    ("e", "paths"),
)


class Unmeasured(Exception):
    """A check could not see its subject: git failed, or an input is missing or unreadable."""


@dataclass(frozen=True)
class Result:
    """One check's verdict, what it saw, and the lines it names."""

    state: str
    seen: str
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class Replay:
    """The tree the patch writes on the parent's tree, and the paths that differ."""

    tree: str
    changed: tuple[str, ...]


def git(repo: Path, *args: str, index: Path | None = None) -> str:
    """Standard output of one git call in `repo`; Unmeasured when it fails or cannot start."""
    env = {name: value for name, value in os.environ.items() if name not in REDIRECTS}
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    try:
        done = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo), *args],
            capture_output=True,
            env=env,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Unmeasured(f"git {args[0]} did not run: {error}") from error
    if done.returncode != 0:
        said = done.stderr.decode("utf-8", "replace").strip().splitlines()
        last = said[-1] if said else "no message"
        raise Unmeasured(f"git {args[0]} exit {done.returncode}: {last}")
    try:
        return done.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Unmeasured(
            f"git {args[0]} printed bytes that are not utf-8 text"
        ) from error


def lines_of(text: str) -> list[str]:
    """Non-empty lines split on newline only, so a quoted path is never cut."""
    return [line.rstrip("\r") for line in text.split("\n") if line.rstrip("\r")]


def full_id(value: str, flag: str) -> str:
    """The value as a full lower-case object id; Unmeasured for a ref name or a short id."""
    lowered = value.strip().lower()
    if FULL_ID.fullmatch(lowered) is None:
        raise Unmeasured(
            f"{flag} {value!r} is not a full object id (40 or 64 hex characters)"
        )
    return lowered


def check_head(repo: Path, parent: str) -> Result:
    head = git(repo, "rev-parse", "--verify", "HEAD").strip()
    if head != parent:
        return Result(FAIL, f"HEAD is {head}, not the --parent {parent}")
    return Result(PASS, f"HEAD is {head}, the --parent")


def check_status(repo: Path, allowed: Sequence[str]) -> Result:
    seen = lines_of(git(repo, "status", "--porcelain", "--untracked-files=all"))
    extra = sorted(set(seen).difference(allowed))
    absent = sorted(set(allowed).difference(seen))
    details = tuple(f"not allowed: {line!r}" for line in extra) + tuple(
        f"allowed but absent: {line!r}" for line in absent
    )
    counted = f"{len(seen)} status line(s), {len(set(allowed))} allowed"
    if details:
        return Result(
            FAIL, f"{counted}: {len(extra)} not allowed, {len(absent)} absent", details
        )
    return Result(PASS, f"{counted}, the same lines")


def check_staged(repo: Path) -> Result:
    out = git(repo, "diff-index", "--cached", "--name-only", "-z", "HEAD")
    staged = [name for name in out.split("\0") if name]
    if staged:
        named = tuple(f"staged: {name!r}" for name in staged)
        return Result(FAIL, f"{len(staged)} path(s) staged", named)
    return Result(PASS, "0 paths staged")


def replay(repo: Path, parent: str, patch: Path) -> Replay:
    """Apply the patch to the parent's tree in a private index and write the tree."""
    try:
        with patch.open("rb") as handle:
            first = handle.read(1)
    except OSError as error:
        reason = error.strerror or type(error).__name__
        raise Unmeasured(
            f"cannot read the patch {patch.as_posix()}: {reason}"
        ) from error
    if not first:
        raise Unmeasured(f"the patch {patch.as_posix()} is empty")
    with tempfile.TemporaryDirectory(
        prefix="landing-gate-", ignore_cleanup_errors=True
    ) as folder:
        index = Path(folder) / "index"
        git(repo, "read-tree", parent, index=index)
        git(repo, "apply", "--cached", str(patch), index=index)
        tree = git(repo, "write-tree", index=index).strip()
    out = git(
        repo, "diff-tree", "-r", "--no-renames", "--name-only", "-z", parent, tree
    )
    return Replay(tree, tuple(sorted(name for name in out.split("\0") if name)))


def check_replay(replayed: Replay, tree: str) -> Result:
    if replayed.tree != tree:
        return Result(
            FAIL,
            f"the patch on the parent writes {replayed.tree}, not the --tree {tree}",
        )
    return Result(PASS, f"the patch on the parent writes {replayed.tree}, the --tree")


def read_paths(listed: Path) -> list[str]:
    try:
        text = listed.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise Unmeasured(
            f"cannot read the --paths file {listed.as_posix()}: {error}"
        ) from error
    return lines_of(text)


def check_paths(changed: Sequence[str], listed: Sequence[str]) -> Result:
    extra = sorted(set(changed).difference(listed))
    missing = sorted(set(listed).difference(changed))
    details = tuple(f"changed, not listed: {path!r}" for path in extra) + tuple(
        f"listed, not changed: {path!r}" for path in missing
    )
    counted = (
        f"the patch changes {len(changed)} path(s), "
        f"the --paths file lists {len(set(listed))}"
    )
    if details:
        return Result(FAIL, counted, details)
    return Result(PASS, f"{counted}, the same paths")


def measure(action: Callable[[], Result]) -> Result:
    try:
        return action()
    except Unmeasured as error:
        return Result(NOT_MEASURED, str(error))


def landing_commands(
    repo: Path, patch: Path, paths: Sequence[str], tree: str
) -> list[str]:
    where = shlex.quote(repo.as_posix())
    named = " ".join(shlex.quote(path) for path in paths)
    return [
        f"git -C {where} apply {shlex.quote(patch.as_posix())}",
        f"git -C {where} add -- {named}",
        f"git -C {where} commit -F <message-file> -- {named}",
        f"git -C {where} rev-parse 'HEAD^{{tree}}'    # must print {tree}",
    ]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=NOTICE)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser(
        "check", help="check one patch before its landing commit"
    )
    check.add_argument(
        "--repo", type=Path, required=True, help="the shared working tree"
    )
    check.add_argument(
        "--parent", required=True, help="the full id of the chain's parent"
    )
    check.add_argument("--patch", type=Path, required=True, help="the patch to land")
    check.add_argument(
        "--tree", required=True, help="the full tree id the patch must write"
    )
    check.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="STATUS_LINE",
        help="a status line that may be there; repeat it for each line",
    )
    check.add_argument(
        "--paths", type=Path, help="a file listing the paths, one per line"
    )
    return parser


def run_checks(
    repo: Path,
    parent_value: str,
    tree_value: str,
    patch: Path,
    allowed: Sequence[str],
    listed: Path | None,
) -> tuple[list[Result], Replay | None]:
    """The five results in check order, and the replay when one was written."""
    results = [
        measure(lambda: check_head(repo, full_id(parent_value, "--parent"))),
        measure(lambda: check_status(repo, allowed)),
        measure(lambda: check_staged(repo)),
    ]
    replayed: Replay | None = None
    try:
        replayed = replay(repo, full_id(parent_value, "--parent"), patch)
    except Unmeasured as error:
        results.append(Result(NOT_MEASURED, str(error)))
    else:
        written = replayed
        results.append(
            measure(lambda: check_replay(written, full_id(tree_value, "--tree")))
        )
    if listed is None:
        results.append(Result(NOT_ASKED, "no --paths file given"))
    elif replayed is None:
        results.append(
            Result(NOT_MEASURED, "it needs the replayed tree, which (d) did not write")
        )
    else:
        changed, paths_file = replayed.changed, listed
        results.append(measure(lambda: check_paths(changed, read_paths(paths_file))))
    return results, replayed


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    given = cast("Path", args.repo)
    patch = cast("Path", args.patch).resolve()
    allowed = cast("list[str]", args.allow)
    listed = cast("Path | None", args.paths)
    parent_value = cast("str", args.parent)
    tree_value = cast("str", args.tree)
    print(NOTICE)
    replayed: Replay | None = None
    try:
        repo = Path(git(given.resolve(), "rev-parse", "--show-toplevel").strip())
    except Unmeasured as error:
        repo = given
        unreached = Result(
            NOT_MEASURED, f"no working tree at {given.as_posix()}: {error}"
        )
        results = [unreached] * len(CHECKS)
    else:
        print(f"repository: {repo.as_posix()}")
        results, replayed = run_checks(
            repo, parent_value, tree_value, patch, allowed, listed
        )
    for (letter, name), result in zip(CHECKS, results, strict=True):
        print(f"{result.state} ({letter}) {name}: {result.seen}")
        for detail in result.details:
            print(f"    {detail}")
    states = [result.state for result in results]
    if NOT_MEASURED in states:
        print(
            f"verdict: {states.count(NOT_MEASURED)} check(s) could not measure, which is"
            " never a pass (exit 2); no landing command is printed"
        )
        return 2
    if FAIL in states:
        print(
            f"verdict: {states.count(FAIL)} check(s) failed (exit 1); no landing command"
            " is printed"
        )
        return 1
    # (d) passed, so a tree was written: its absence here is a defect, never a pass.
    if replayed is None:
        print(
            "verdict: the replay left no tree (exit 2); no landing command is printed"
        )
        return 2
    print("verdict: every check measured and passed (exit 0)")
    print(
        "landing commands, printed and NOT run: run each in its own call, under the lock"
    )
    for command in landing_commands(repo, patch, replayed.changed, replayed.tree):
        print(f"  {command}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
