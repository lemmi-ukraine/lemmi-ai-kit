"""Every command that subsection 12m of the shared-index reference prints is run, in a scratch
repository, and does what the subsection says.

The wording of 12m is pinned in `test_shared_tree_rules_wording.py`. This file runs the commands
under it, so that a recipe that reads well and does not work cannot stand. Each test builds its
own repository with no ambient git config and `core.autocrlf` off, runs the printed commands with
their placeholders filled, and carries a control that could fail:

* a tree stamp takes `index.lock` and rewrites `.git/index` when a `git add` left the tree cache
  invalid (the control: a second stamp changes nothing), with or without `--no-optional-locks`,
  and a peer's lock stops it with exit 128;
* `git archive -o <file> <tree>` holds the staged content and not a later unstaged edit, and an
  export has no repository;
* `git diff --name-only <tree-a> <tree-b>` names exactly the path I re-staged and the path a peer
  staged (the control: a tree against itself prints nothing);
* after a commit with no pathspec `HEAD^{tree}` equals the stamp, after one with a pathspec while
  a peer staged another file it does not, and `git diff <tree> HEAD -- <paths>` still prints
  nothing for the paths committed (the control: an edit made after the stamp is printed);
* a private copy of the index file builds HEAD plus my paths and leaves `.git/index` byte-equal,
  works while a peer holds `index.lock`, and, left set, redirects a later `git add` (the control:
  without the variable the same add changes the shared index);
* the three guard commands print other values once a peer has switched branch and committed, the
  reflog shows it, and switching straight back removes the peer's committed file (the control: no
  peer, the same three values);
* a peer's `git add` of an untracked file changes `git diff HEAD` with no byte moving (the
  control: before the add it printed nothing).

THE SURFACE, in numbers the tests assert: 12 printed commands, each of which must be an inline
code span of subsection 12m (an exact span, so a command that is only the start of a longer one
does not count), and each of which is run by at least one recipe test below. A printed command
that goes from the subsection, or a recipe that stops running one, is reported by name.

These tests need `git` on the path: a machine without it fails them by name instead of passing,
because a recipe that was not run proves nothing.
"""

import ast
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REFERENCE = (
    _REPO_ROOT
    / "plugins"
    / "orchestration"
    / "skills"
    / "parallel-session-safety"
    / "references"
    / "shared-index-protocol.md"
)
_HEADING = "### 12m."
_MD_HEADING = re.compile(r"^(#{1,6})\s")
_SPAN = re.compile(r"`([^`\n]+)`")

# The commands as the subsection prints them, by the name the recipes use for them.
_PRINTED: dict[str, str] = {
    "branch": "git rev-parse --abbrev-ref HEAD",
    "commit": "git rev-parse HEAD",
    "staged": "git diff --cached --name-only",
    "reflog": "git reflog --date=iso -n 20",
    "archive": "git archive -o <file> <id>",
    "stamp": "git write-tree",
    "names": "git diff --name-only <tested-tree> <tree-now>",
    "tree": "git rev-parse HEAD^{tree}",
    "paths": "git diff <tested-tree> HEAD -- <paths>",
    "read": "git read-tree HEAD",
    "add": "git add -- <your paths>",
    "snapshot": "git diff HEAD",
}


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _MD_HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _printed_spans(section: str) -> set[str]:
    """The inline code spans of a section, read after its lines are joined (a span may wrap),
    each with its whitespace folded."""
    folded = " ".join(section.split())
    return {" ".join(span.split()) for span in _SPAN.findall(folded)}


def _unprinted(section: str) -> list[str]:
    spans = _printed_spans(section)
    return [command for command in _PRINTED.values() if command not in spans]


def _keys_run(source: str) -> set[str]:
    """The names of the printed commands that a source file runs: the first argument of every
    call of `_argv` that is a string constant."""
    return {
        node.args[0].value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_argv"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }


# --- the scratch repository ----------------------------------------------------------------------


def _environment(root: Path) -> dict[str, str]:
    """The ambient environment with every git variable dropped (a hook that runs this suite sets
    `GIT_INDEX_FILE`), no global or system config, and an identity to commit with."""
    empty = root / "gitconfig-empty"
    if not empty.exists():
        empty.write_bytes(b"")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        {
            "GIT_CONFIG_GLOBAL": str(empty),
            "GIT_CONFIG_SYSTEM": str(empty),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
    )
    return env


def _run(
    repo: Path, argv: list[str], extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    env = _environment(repo.parent)
    if extra:
        env.update(extra)
    try:
        return subprocess.run(
            argv, cwd=repo, env=env, capture_output=True, check=False, timeout=60
        )
    except OSError as exc:  # pragma: no cover - git absent
        pytest.fail(f"git is not available, so the recipe was not run: {exc}")


def _ok(repo: Path, argv: list[str], extra: dict[str, str] | None = None) -> str:
    """The stdout of a command that must succeed, decoded and stripped."""
    done = _run(repo, argv, extra)
    assert done.returncode == 0, (
        f"{' '.join(argv)} exited {done.returncode}: {done.stderr.decode('utf-8', 'replace')}"
    )
    return done.stdout.decode("utf-8").strip()


def _argv(key: str, values: dict[str, str] | None = None) -> list[str]:
    """A printed command with its placeholders filled; none may be left, so no recipe runs a
    placeholder as if it were a path."""
    template = _PRINTED[key]
    for placeholder, value in (values or {}).items():
        template = template.replace(f"<{placeholder}>", value)
    argv = shlex.split(template)
    assert not any("<" in word for word in argv), f"a placeholder is left in {argv}"
    return argv


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def _scratch(tmp_path: Path) -> Path:
    """A repository with a base commit of a.txt and b.txt, on a branch called main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _ok(repo, ["git", "init", "-q", "-b", "main"])
    _ok(repo, ["git", "config", "core.autocrlf", "false"])
    _write(repo / "a.txt", "one\n")
    _write(repo / "b.txt", "base\n")
    _ok(repo, ["git", "add", "--", "a.txt", "b.txt"])
    _ok(repo, ["git", "commit", "-q", "-m", "base"])
    return repo


def _stage(repo: Path, name: str, text: str) -> None:
    _write(repo / name, text)
    _ok(repo, ["git", "add", "--", name])


def _index_hash(repo: Path) -> str:
    return hashlib.sha256((repo / ".git" / "index").read_bytes()).hexdigest()


# --- the commands as printed ---------------------------------------------------------------------


def test_the_printed_commands_are_the_spans_of_the_subsection() -> None:
    """Red before the change: there was no subsection to print them."""
    section = _section(_REFERENCE.read_text(encoding="utf-8"), _HEADING)
    assert section.strip(), f"{_HEADING} is not in {_REFERENCE.name}"
    assert len(_PRINTED) == 12
    assert _unprinted(section) == [], _unprinted(section)


def test_a_command_that_goes_from_the_subsection_is_reported_by_name() -> None:
    """Planted removal of each printed span in turn, and the near miss: a command that is only
    the start of a longer span (`git rev-parse HEAD` inside the `HEAD^{tree}` span) is not it."""
    section = _section(_REFERENCE.read_text(encoding="utf-8"), _HEADING)
    assert section.strip(), f"{_HEADING} is not in {_REFERENCE.name}"
    for command in _PRINTED.values():
        span = f"`{command}`"
        assert span in section, f"{command!r} is not printed as its own span"
        assert _unprinted(section.replace(span, "")) == [command], command
    only_the_start = "Compare `git rev-parse HEAD^{tree}` here."
    assert "git rev-parse HEAD" not in _printed_spans(only_the_start)
    assert "git rev-parse HEAD^{tree}" in _printed_spans(only_the_start)
    assert _unprinted("") == list(_PRINTED.values())


def test_every_printed_command_is_run_by_a_recipe() -> None:
    """Each name in the table of printed commands is the first argument of an `_argv` call in
    this file, so a recipe that stops running a command is reported by its name."""
    source = Path(__file__).read_text(encoding="utf-8")
    assert set(_PRINTED) - _keys_run(source) == set(), set(_PRINTED) - _keys_run(source)
    # planted: a source that runs two of them, a name that is not a constant, another function
    planted = "\n".join(
        ["_argv('stamp')", "_argv(key)", "other('read')", "x = _argv('names', {})", ""]
    )
    assert _keys_run(planted) == {"stamp", "names"}
    assert set(_PRINTED) - _keys_run(planted) == set(_PRINTED) - {"stamp", "names"}


# --- the recipes ---------------------------------------------------------------------------------


def test_a_tree_stamp_takes_the_index_lock_and_rewrites_the_index(
    tmp_path: Path,
) -> None:
    repo = _scratch(tmp_path)
    _stage(repo, "a.txt", "two\n")
    before = _index_hash(repo)
    first = _ok(repo, _argv("stamp"))
    after = _index_hash(repo)
    assert after != before, "the stamp left the index bytes as they were"
    # control: with the tree cache valid again, a second stamp writes nothing
    assert _ok(repo, _argv("stamp")) == first
    assert _index_hash(repo) == after
    # the flag that suppresses optional locks does not make a stamp read-only
    _stage(repo, "a.txt", "three\n")
    before = _index_hash(repo)
    _ok(repo, ["git", "--no-optional-locks", "write-tree"])
    assert _index_hash(repo) != before
    # a peer's lock stops it, and nothing else does
    stamped = _ok(repo, _argv("stamp"))
    lock = repo / ".git" / "index.lock"
    lock.write_bytes(b"")
    blocked = _run(repo, _argv("stamp"))
    assert blocked.returncode == 128, blocked.returncode
    assert b"index.lock" in blocked.stderr, blocked.stderr
    lock.unlink()
    assert _ok(repo, _argv("stamp")) == stamped


def test_an_export_of_the_stamped_tree_holds_the_staged_content(tmp_path: Path) -> None:
    repo = _scratch(tmp_path)
    _stage(repo, "a.txt", "two\n")
    tree = _ok(repo, _argv("stamp"))
    _write(repo / "a.txt", "three\n")
    assert (repo / "a.txt").read_bytes() == b"three\n", "no unstaged edit to compare to"
    tarball = tmp_path / "export.tar"
    # The printed command writes the tar to its own file: nothing goes through a pipe.
    written = _run(
        repo, _argv("archive", {"file": shlex.quote(tarball.as_posix()), "id": tree})
    )
    assert written.returncode == 0, written.stderr
    assert written.stdout == b"", "the archive went to standard output"
    assert tarball.is_file(), "the printed command wrote no file"
    export = tmp_path / "export"
    with tarfile.open(tarball) as tar:
        for member in tar.getmembers():
            if member.isfile():
                handle = tar.extractfile(member)
                assert handle is not None, member.name
                _write(export / member.name, handle.read().decode("utf-8"))
    assert (export / "a.txt").read_bytes() == b"two\n"
    assert (export / "b.txt").read_bytes() == b"base\n"
    assert not (export / ".git").exists()
    ceiling = {"GIT_CEILING_DIRECTORIES": str(tmp_path)}
    no_repository = _run(export, ["git", "rev-parse", "--git-dir"], ceiling)
    assert no_repository.returncode != 0, "an export is a repository"


def test_two_stamps_differ_by_the_paths_staged_in_between(tmp_path: Path) -> None:
    repo = _scratch(tmp_path)
    _stage(repo, "a.txt", "two\n")
    tested = _ok(repo, _argv("stamp"))
    same = _argv("names", {"tested-tree": tested, "tree-now": tested})
    assert _ok(repo, same) == "", "a tree against itself printed a path"
    _stage(repo, "a.txt", "three\n")
    _stage(repo, "peer.txt", "peer\n")
    now = _ok(repo, _argv("stamp"))
    names = _argv("names", {"tested-tree": tested, "tree-now": now})
    assert _ok(repo, names).splitlines() == ["a.txt", "peer.txt"]
    again = _argv("names", {"tested-tree": now, "tree-now": _ok(repo, _argv("stamp"))})
    assert _ok(repo, again) == "", (
        "nothing was staged in between and a path was printed"
    )


def test_the_tree_after_a_commit_equals_the_stamp_only_without_a_pathspec(
    tmp_path: Path,
) -> None:
    repo = _scratch(tmp_path)
    _stage(repo, "a.txt", "two\n")
    tested = _ok(repo, _argv("stamp"))
    _ok(repo, ["git", "commit", "-q", "-m", "no pathspec"])
    assert _ok(repo, _argv("tree")) == tested
    _stage(repo, "a.txt", "three\n")
    _stage(repo, "peer.txt", "peer\n")
    tested = _ok(repo, _argv("stamp"))
    _ok(repo, ["git", "commit", "-q", "-m", "with a pathspec", "--", "a.txt"])
    assert _ok(repo, _argv("tree")) != tested, "a pathspec commit held the peer's file"
    held = _argv("paths", {"tested-tree": tested, "paths": "a.txt"})
    assert _ok(repo, held) == ""
    # control: an edit made after the stamp is what the same comparison exists to print
    _stage(repo, "a.txt", "four\n")
    tested = _ok(repo, _argv("stamp"))
    _write(repo / "a.txt", "five\n")
    _ok(repo, ["git", "commit", "-q", "-m", "an edit after the stamp", "--", "a.txt"])
    printed = _ok(repo, _argv("paths", {"tested-tree": tested, "paths": "a.txt"}))
    assert "+five" in printed, printed


def test_a_private_copy_of_the_index_builds_head_plus_my_paths(tmp_path: Path) -> None:
    repo = _scratch(tmp_path)
    _stage(repo, "peer.txt", "peer\n")
    _write(repo / "mine.txt", "mine\n")
    shared = _index_hash(repo)
    assert _ok(repo, _argv("staged")) == "peer.txt"
    private = tmp_path / "private-index"
    shutil.copyfile(repo / ".git" / "index", private)
    mine = {"GIT_INDEX_FILE": str(private)}
    _ok(repo, _argv("read"), mine)
    _ok(repo, _argv("add", {"your paths": "mine.txt"}), mine)
    tree = _ok(repo, _argv("stamp"), mine)
    listed = _ok(repo, ["git", "ls-tree", "-r", "--name-only", tree]).splitlines()
    assert listed == ["a.txt", "b.txt", "mine.txt"], "the peer's staged file is in it"
    assert _index_hash(repo) == shared, "the shared index changed"
    assert _ok(repo, _argv("staged")) == "peer.txt"
    # a peer's lock does not stop the private route, and does stop the shared one
    lock = repo / ".git" / "index.lock"
    lock.write_bytes(b"")
    assert _ok(repo, _argv("stamp"), mine) == tree
    assert _run(repo, _argv("stamp")).returncode == 128
    lock.unlink()
    # left set, the variable redirects a later add into the private file
    _write(repo / "other.txt", "other\n")
    _ok(repo, ["git", "add", "--", "other.txt"], mine)
    assert _index_hash(repo) == shared
    assert "other.txt" in _ok(repo, ["git", "ls-files"], mine).splitlines()
    # control: without the variable the same add changes the shared index
    _ok(repo, ["git", "add", "--", "other.txt"])
    assert _index_hash(repo) != shared
    assert "other.txt" in _ok(repo, _argv("staged")).splitlines()


def test_the_guard_commands_and_the_reflog_see_a_peer_who_moved_head(
    tmp_path: Path,
) -> None:
    repo = _scratch(tmp_path)
    _stage(repo, "mine.txt", "mine\n")

    def guard() -> tuple[str, str, str]:
        return (
            _ok(repo, _argv("branch")),
            _ok(repo, _argv("commit")),
            _ok(repo, _argv("staged")),
        )

    recorded = guard()
    assert recorded[0] == "main" and recorded[2] == "mine.txt"
    assert guard() == recorded, "control: with no peer the three values moved"
    _ok(repo, ["git", "switch", "-q", "-c", "peer-branch"])
    _stage(repo, "peerfile.txt", "peerfile\n")
    _ok(repo, ["git", "commit", "-q", "-m", "peer commit", "--", "peerfile.txt"])
    _stage(repo, "peerstaged.txt", "staged\n")
    now = guard()
    assert [now[i] != recorded[i] for i in range(3)] == [True, True, True], now
    log = _ok(repo, _argv("reflog"))
    assert "checkout: moving from main to peer-branch" in log, log
    assert "commit: peer commit" in log, log
    assert (repo / "peerfile.txt").exists()
    _ok(repo, ["git", "switch", "-q", "main"])
    assert not (repo / "peerfile.txt").exists(), "switching back kept the peer's file"


def test_a_peer_add_of_an_untracked_file_changes_the_diff_without_moving_a_byte(
    tmp_path: Path,
) -> None:
    repo = _scratch(tmp_path)
    _write(repo / "u.txt", "untracked\n")
    hash_before = hashlib.sha256((repo / "u.txt").read_bytes()).hexdigest()
    before = _ok(repo, _argv("snapshot"))
    assert before == "", "control: an untracked file is not in git diff HEAD"
    _ok(repo, ["git", "add", "--", "u.txt"])
    after = _ok(repo, _argv("snapshot"))
    assert after != before and "untracked" in after, after
    assert hashlib.sha256((repo / "u.txt").read_bytes()).hexdigest() == hash_before
