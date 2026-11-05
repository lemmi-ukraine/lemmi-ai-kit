"""Check, read-only, whether one patch may land in a shared working tree now.

A session that lands work in a tree other sessions also write runs this immediately before it
commits, and BEFORE it applies the patch (see ../references/landing-queue.md). It reads the
repository and the files it is given, and it applies, stages and commits nothing: when every
check passes it PRINTS the commands that land the patch, for the session to run itself, under
the lock.

    python landing_gate.py check --repo PATH --parent ID --patch FILE --tree ID
                                 [--allow "STATUS LINE"]... [--paths FILE]

--parent and --tree are full object ids (40 or 64 hex characters); a ref name moves, so it is
refused. An --allow value is one line exactly as `git status --porcelain --untracked-files=all`
prints it: a path with a space in it is printed in double quotes. Allow only lines for paths the
patch leaves alone: check (f) fails a changed path whatever the status says. --paths names a
text file with one repository path per line. A --repo inside a working tree is checked at the
tree's top.

It prints one line per check, in this order, each PASS, FAIL or NOT MEASURED with what it saw:
  (a) head      HEAD is the --parent commit
  (b) status    `git status --porcelain --untracked-files=all` prints exactly the --allow lines; a
                line that is not allowed, and an allowed line that is absent, are each named
  (c) staged    nothing is staged: `git diff-index --cached HEAD` names no path
  (d) replay    the patch, applied to the parent's tree in a private index (GIT_INDEX_FILE in a
                temporary folder, never the real index), writes the --tree tree
  (e) paths     with --paths: the paths the replayed tree changes against the parent are exactly
                the listed ones, a rename counting as two; NOT ASKED without --paths
  (f) landing   the printed commands store exactly the patch from this working tree: the
                replayed tree changes at least one path; in the working tree each changed path is
                still exactly the parent's file (absent where the parent has none), read with
                `git update-index` into a second private index, so the status cannot hide it (a
                peer's edit, allowed or hidden by assume-unchanged or skip-worktree, and an
                untracked file where the patch adds one, each fail); none is ignored, because
                `git add --` refuses an ignored path; none sets or clears an executable bit that
                this repository cannot store (core.filemode false); and no added or changed blob
                that holds a CR would be stored with other line ends by this repository's own
                conversion on the way in

Exit 0 only when every check measured and passed: it then prints the landing commands, with an
explicit pathspec on both `git add --` and `git commit --` and quoted for a POSIX shell, and
never runs them. Exit 1 when a check failed. Exit 2 when any check could not measure (git failed
or is missing, an input is missing or unreadable, the patch does not apply to the parent), even
if another check failed: cannot-measure is never a pass. No landing command is printed unless
it exits 0.

Every git call runs with --no-optional-locks, so `git status` does not rewrite the index. It
writes nothing in the working tree, the real index or any ref. The replay and check (f) leave
unreferenced blob and tree objects in the object store, which git's garbage collection removes,
and each deletes its temporary folder. Output is always utf-8, whatever the console's code page,
so a file name outside that code page cannot end the run in a traceback after the verdict.
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
# The modes of a raw tree diff: none (the path is absent on that side) and the two plain files.
NO_MODE = "000000"
EXEC_MODE = "100755"
FILE_MODES = frozenset({"100644", EXEC_MODE})
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
# Each changes how git reads a path it is handed, and `git check-ignore` refuses the literal one
# outright; the gate hands git every path as plain data.
PATHSPEC_MODES = frozenset(
    {
        "GIT_LITERAL_PATHSPECS",
        "GIT_GLOB_PATHSPECS",
        "GIT_NOGLOB_PATHSPECS",
        "GIT_ICASE_PATHSPECS",
    }
)
TIMEOUT_SECONDS = 300
CHECKS = (
    ("a", "head"),
    ("b", "status"),
    ("c", "staged"),
    ("d", "replay"),
    ("e", "paths"),
    ("f", "landing"),
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
class Entry:
    """One path of a raw tree diff: its mode and blob id on each side (all zeros where absent)."""

    old_mode: str
    new_mode: str
    old_id: str
    new_id: str
    path: str


@dataclass(frozen=True)
class Replay:
    """The tree the patch writes on the parent's tree, and the paths that differ."""

    tree: str
    entries: tuple[Entry, ...]

    @property
    def changed(self) -> tuple[str, ...]:
        return tuple(entry.path for entry in self.entries)


def run_git(
    repo: Path,
    *args: str,
    index: Path | None = None,
    stdin: bytes | None = None,
    ok: Sequence[int] = (0,),
) -> bytes:
    """Standard output of one git call in `repo`, with `stdin` as its input when given;
    Unmeasured when it cannot start or exits with a code that is not in `ok`."""
    dropped = REDIRECTS | PATHSPEC_MODES
    env = {name: value for name, value in os.environ.items() if name not in dropped}
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    try:
        done = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo), *args],
            capture_output=True,
            env=env,
            input=stdin,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Unmeasured(f"git {args[0]} did not run: {error}") from error
    if done.returncode not in ok:
        said = done.stderr.decode("utf-8", "replace").strip().splitlines()
        last = said[-1] if said else "no message"
        raise Unmeasured(f"git {args[0]} exit {done.returncode}: {last}")
    return done.stdout


def git(
    repo: Path,
    *args: str,
    index: Path | None = None,
    stdin: str | None = None,
    ok: Sequence[int] = (0,),
) -> str:
    """Standard output of one git call as utf-8 text; Unmeasured when it is not text."""
    out = run_git(
        repo,
        *args,
        index=index,
        stdin=None if stdin is None else stdin.encode("utf-8"),
        ok=ok,
    )
    try:
        return out.decode("utf-8")
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


def tree_entries(repo: Path, parent: str, tree: str) -> tuple[Entry, ...]:
    """Every path that differs between the parent's tree and `tree`, by path, a rename counting
    as two. The raw format with -z is `:old-mode new-mode old-id new-id status NUL path NUL`."""
    out = git(repo, "diff-tree", "-r", "--no-renames", "-z", parent, tree)
    fields = out.split("\0")
    entries: list[Entry] = []
    for header, path in zip(fields[0::2], fields[1::2], strict=False):
        parts = header.removeprefix(":").split(" ")
        if len(parts) != 5 or not path:
            raise Unmeasured(
                f"git diff-tree printed a line this gate cannot read: {header!r}"
            )
        entries.append(Entry(parts[0], parts[1], parts[2], parts[3], path))
    return tuple(sorted(entries, key=lambda entry: entry.path))


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
    return Replay(tree, tree_entries(repo, parent, tree))


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


def nul_lines(paths: Sequence[str]) -> str:
    """The paths as git reads them from standard input with -z: each ends with a NUL."""
    return "".join(f"{path}\0" for path in paths)


def staged_differences(repo: Path, parent: str, paths: Sequence[str]) -> list[str]:
    """The paths whose working-tree file is not the parent's version of that path.

    Each path is staged the way `git add` stages it (the same filters and line-end conversion)
    into a second private index that starts as the parent's tree, and that index is compared with
    the parent. The file itself is read, so an assume-unchanged or skip-worktree flag, which hides
    an edit from the status, hides nothing here; a path with no file stages as a removal.
    """
    with tempfile.TemporaryDirectory(
        prefix="landing-gate-", ignore_cleanup_errors=True
    ) as folder:
        index = Path(folder) / "index"
        git(repo, "read-tree", parent, index=index)
        git(
            repo,
            "update-index",
            "--add",
            "--remove",
            "-z",
            "--stdin",
            index=index,
            stdin=nul_lines(paths),
        )
        out = git(
            repo,
            "diff-index",
            "--cached",
            "--no-renames",
            "--name-only",
            "-z",
            parent,
            index=index,
        )
    return sorted(name for name in out.split("\0") if name)


def ignored_paths(repo: Path, paths: Sequence[str]) -> list[str]:
    """The paths an ignore rule names and the index does not track: `git add --` refuses them."""
    out = git(repo, "check-ignore", "-z", "--stdin", stdin=nul_lines(paths), ok=(0, 1))
    return sorted(name for name in out.split("\0") if name)


def git_flag(repo: Path, key: str) -> bool:
    """A boolean git setting; true when it is unset, which is git's default for core.filemode."""
    return git(repo, "config", "--bool", "--get", key, ok=(0, 1)).strip() != "false"


def mode_details(repo: Path, entries: Sequence[Entry]) -> tuple[str, ...]:
    """The paths whose executable bit `git add --` cannot store in this repository: with
    core.filemode false a new file is stored 100644 and an old one keeps its mode, so a bit that
    the patch sets or clears is lost."""
    if git_flag(repo, "core.filemode"):
        return ()
    return tuple(
        "the executable bit changes and core.filemode is false, so `git add --` cannot"
        f" store it: {entry.path!r}"
        for entry in entries
        if entry.new_mode != NO_MODE
        and (entry.old_mode == EXEC_MODE) != (entry.new_mode == EXEC_MODE)
    )


def blobs(repo: Path, ids: Sequence[str]) -> dict[str, bytes]:
    """The content of each blob, read with one `git cat-file --batch` call, which answers each id
    with `id type size NL`, the content and a NL."""
    if not ids:
        return {}
    out = run_git(
        repo, "cat-file", "--batch", stdin="".join(f"{each}\n" for each in ids).encode()
    )
    found: dict[str, bytes] = {}
    at = 0
    for wanted in ids:
        end = out.find(b"\n", at)
        header = out[at:end].split(b" ") if end >= 0 else []
        if len(header) != 3 or header[0].decode("ascii", "replace") != wanted:
            raise Unmeasured(f"git cat-file could not read the blob {wanted}")
        size = int(header[2])
        found[wanted] = out[end + 1 : end + 1 + size]
        at = end + 1 + size + 1
    return found


def converted_blobs(repo: Path, entries: Sequence[Entry]) -> tuple[str, ...]:
    """The paths whose blob `git add --` would store with other line ends than the patch wrote,
    because this repository converts a file on the way in (core.autocrlf, or an eol or text
    attribute) and the repository the chain was built in did not. Only a blob that holds a CR
    can change, and git leaves a file alone whose old blob already holds one, so those are the
    ones asked: `git hash-object --path` runs the blob through the conversion of its path."""
    files = [entry for entry in entries if entry.new_mode in FILE_MODES]
    held = blobs(repo, [entry.new_id for entry in files])
    risky = [entry for entry in files if b"\r" in held[entry.new_id]]
    old = blobs(repo, [entry.old_id for entry in risky if entry.old_mode != NO_MODE])
    named: list[str] = []
    for entry in risky:
        if b"\r" in old.get(entry.old_id, b""):
            continue
        stored = run_git(
            repo,
            "hash-object",
            f"--path={entry.path}",
            "--stdin",
            stdin=held[entry.new_id],
        )
        if stored.decode("ascii", "replace").strip() != entry.new_id:
            named.append(
                f"git would convert its line ends and store another blob: {entry.path!r}"
            )
    return tuple(named)


def check_landing(repo: Path, parent: str, replayed: Replay) -> Result:
    """The printed commands apply the patch over the working-tree file of each changed path and
    `git add --` stores that file, so each file must be the parent's, must not be ignored, and
    must be storable here exactly as the patch has it for the patch to be all that is stored."""
    changed = replayed.changed
    if not changed:
        return Result(
            FAIL, "the patch changes no path: the printed commands would land nothing"
        )
    differs = staged_differences(repo, parent, changed)
    ignored = ignored_paths(repo, changed)
    modes = mode_details(repo, replayed.entries)
    converted = converted_blobs(repo, replayed.entries)
    details = (
        tuple(
            "not the parent's file in the working tree, so the landing would store more or"
            f" less than the patch: {name!r}"
            for name in differs
        )
        + tuple(f"ignored, so `git add --` refuses it: {name!r}" for name in ignored)
        + modes
        + converted
    )
    counted = f"the patch changes {len(changed)} path(s)"
    if details:
        return Result(
            FAIL,
            f"{counted}: {len(differs)} not the parent's file in the working tree,"
            f" {len(ignored)} ignored, {len(modes)} with an executable bit git cannot store,"
            f" {len(converted)} with line ends git would convert",
            details,
        )
    return Result(
        PASS,
        f"{counted}, each the parent's file in the working tree, none ignored,"
        " each stored as the patch has it",
    )


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
    """The six results in check order, and the replay when one was written."""
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
    if replayed is None:
        results.append(
            Result(NOT_MEASURED, "it needs the replayed tree, which (d) did not write")
        )
    else:
        found, base = replayed, full_id(parent_value, "--parent")
        results.append(measure(lambda: check_landing(repo, base, found)))
    return results, replayed


def utf8_output() -> None:
    """Write utf-8 whatever the console's code page is. A name outside that code page would
    otherwise raise on the first print that holds it, after the verdict was already decided, and
    the traceback exits 1, which means "a check failed"."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    utf8_output()
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
