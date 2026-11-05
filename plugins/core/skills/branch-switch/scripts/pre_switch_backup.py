"""Save the tracked changes and an inventory of the untracked files BEFORE a branch switch.

Usage:

    python -B "${CLAUDE_SKILL_DIR}/scripts/pre_switch_backup.py" <target-branch>

Writes ONE new folder, `<git dir>/pre-switch-backups/<UTC stamp>-<target-branch>/`, and prints its
absolute path as the LAST line of stdout so the caller can quote it to the user before switching.
It lives under the git directory because that is never tracked, never swept by `git clean`, and
never read by a publication scan; a folder inside the working tree is all three. The branch name
is stored with every character outside `A-Za-z0-9._-` turned into `-`, so `feature/x` is one
folder, not two.

Each file holds the output of one git command, byte for byte:

    unstaged-tracked.patch    git diff --binary
    staged-tracked.patch      git diff --cached --binary
    untracked-inventory.txt   git ls-files --others --exclude-standard
    stash-list.txt            git stash list
    head-at-backup.txt        git rev-parse HEAD
    branch-at-backup.txt      git rev-parse --abbrev-ref HEAD    (`HEAD` when detached)

`--binary` is deliberate: without it a changed binary file is backed up as the words "Binary
files differ", which restores nothing.

NOT saved, and the script says so on every run: the CONTENTS of untracked files (the inventory
holds names only; the stash a switch takes with `git stash push --include-untracked` keeps them
for a handful of files or fewer, and past that they stay in the tree) and ignored files.

The folder is made with a `mkdir` that fails when it exists, so a second run with the same stamp
can never overwrite the first backup.

Exit codes:

    0  every file written; the path is the last line of stdout
    1  a step failed (git missing, not a repository, a git command, the folder already exists, a
       write): the step is named on stderr and nothing is printed on stdout. A half-written
       folder is left in place and stderr says it is INCOMPLETE
    2  usage error (argparse)

--stamp STAMP  name the folder with STAMP instead of the current UTC time (`YYYYMMDDTHHMMSSZ`).
               It exists so a test can run the script twice inside one second.

Forces UTF-8 output so a path with non-ASCII characters prints on a legacy console codepage.
"""

import argparse
import contextlib
import re
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

BACKUP_FOLDER = "pre-switch-backups"

# (file name, the git arguments whose output it holds), in the order the files are written.
SNAPSHOTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("unstaged-tracked.patch", ("diff", "--binary")),
    ("staged-tracked.patch", ("diff", "--cached", "--binary")),
    ("untracked-inventory.txt", ("ls-files", "--others", "--exclude-standard")),
    ("stash-list.txt", ("stash", "list")),
    ("head-at-backup.txt", ("rev-parse", "HEAD")),
    ("branch-at-backup.txt", ("rev-parse", "--abbrev-ref", "HEAD")),
)


def _git(*args: str) -> bytes:
    """The stdout of `git <args>`, byte for byte. Any failure raises, naming the command."""
    try:
        done = subprocess.run(["git", *args], capture_output=True, check=False)
    except OSError as error:
        raise RuntimeError(f"could not run git: {error}") from error
    if done.returncode != 0:
        said = done.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"`git {' '.join(args)}` exited {done.returncode}: {said}")
    return done.stdout


def take_backup(target_branch: str, stamp: str) -> Path:
    """Write the snapshot folder and return it; raise `RuntimeError` at the first failed step."""
    git_dir = Path(_git("rev-parse", "--absolute-git-dir").decode("utf-8").strip())
    leaf = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{stamp}-{target_branch}").strip("-")
    folder = git_dir / BACKUP_FOLDER / leaf
    try:
        folder.mkdir(parents=True)  # exist_ok stays False: a backup is never reused
    except FileExistsError as error:
        raise RuntimeError(f"{folder} already exists and was left untouched") from error
    except OSError as error:
        raise RuntimeError(f"cannot create {folder}: {error}") from error
    try:
        for name, args in SNAPSHOTS:
            (folder / name).write_bytes(_git(*args))
    except (RuntimeError, OSError) as error:
        raise RuntimeError(f"INCOMPLETE backup left at {folder}: {error}") from error
    return folder


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "target_branch", help="the branch being switched TO; it names the folder"
    )
    parser.add_argument(
        "--stamp", help="folder stamp instead of the UTC time (YYYYMMDDTHHMMSSZ)"
    )
    args = parser.parse_args(argv)
    stamp = args.stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        folder = take_backup(args.target_branch, stamp)
    except RuntimeError as error:
        print(f"pre_switch_backup: {error}", file=sys.stderr)
        return 1
    print(
        "Saved: the unstaged and staged tracked changes (as binary-safe patches), the names of"
    )
    print("untracked files, the stash list, HEAD and the branch.")
    print(
        "NOT saved: the CONTENTS of untracked files (the stash taken with "
        "`git stash push --include-untracked` keeps them for a handful of files or fewer; "
        "past that they stay in the tree) and ignored files."
    )
    print(folder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
