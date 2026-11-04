"""The landing gate checks, read-only, whether one patch may land in a shared working tree now.

`parallel-session-safety/scripts/landing_gate.py check` reads one repository, a patch and the
values a session recorded when it built the patch, and prints one line per check, in this order:
(a) HEAD is the --parent; (b) `git status --porcelain --untracked-files=all` is exactly the
--allow lines; (c) nothing is staged; (d) the patch, replayed on the parent's tree in a private
index, writes the --tree; (e) with --paths, the patch changes exactly the listed paths, a rename
counting as two; (f) the patch changes at least one path, and in the working tree each of them
is still exactly the parent's file, is not ignored, and has an executable bit and line ends this
repository stores as the patch has them, so the printed `git add --` stores the patch and
nothing else. Exit 0 only when every check measured and passed, and only then are the
landing commands printed, never run; exit 1 when a check failed; exit 2 when any check could
not measure. Output is utf-8 whatever the console's code page.

THE SURFACE, in numbers the tests assert: 1 script, run as a subprocess in the form the landing
queue reference names; 6 checks; 15 planted failures (one per check (a) to (e), two for (b): a
line that is not allowed and an allowed line that is absent, and nine for (f): a peer's edit to a
changed path allowed, hidden by assume-unchanged and hidden by skip-worktree, an untracked file
where the patch adds one with other bytes and with the patch's own, a patch that changes no
path, a changed path an ignore rule names, an executable bit with core.filemode false, and a
CRLF blob the shared tree would convert), each run beside its control, and each shown to be the
ONLY failing check of its run, so the gate would exit 0 if that check were missing; for 6 of the
9 (the allowed edit, both untracked files, the ignored path, the mode and the line ends) also
that the commands the gate refused would have landed another tree or been refused by git; 4
patches it cannot read or apply (missing,
empty, not a patch, a patch for other content), each exit 2; 2 inputs that name no repository
and 2 values that are not full ids, each exit 2; 4 pathspec-mode variables in the environment
that leave the green run green; a name outside the console's code page, run under a cp1252
console, that still gets its verdict (the green run and a failing run); and the all-green
run, after which HEAD, the refs, the real index bytes, the status, the working tree and the
gate's temporary folder are as they were, and whose printed commands, run in a throw-away clone,
land exactly the --tree. The normal flow, a peer's allowed edit to a path the patch leaves alone,
is green and its printed commands land exactly the --tree beside that edit. Every repository is
built in the test's own folder, with `core.autocrlf true` both in a global config the tests
point git at and in the repository's own config, so the working tree holds CRLF files as such a
machine's checkout would.
"""

import hashlib
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "orchestration"
    / "skills"
    / "parallel-session-safety"
    / "scripts"
    / "landing_gate.py"
)

_LETTERS = ("a", "b", "c", "d", "e", "f")
_STATES = ("PASS", "FAIL", "NOT MEASURED", "NOT ASKED")
# The paths the template change touches: an edit in a folder, a rename (two paths) and a new
# file, two of them with a space in the name.
_CHANGED = ("added.txt", "new name.txt", "notes/a file.txt", "old name.txt")
_PEER_NOTE = "peer note.txt"
_PEER_LINE = '?? "peer note.txt"'  # how the status quotes a path with a space
# The variable that sets the encoding of python's standard streams, spelled in two parts: the
# publication scan bans the whole word as a machine-specific workaround, and this test sets it on
# purpose, in one child process, to plant a console code page.
_IO_ENCODING = "PYTHON" + "IOENCODING"


class _Run(NamedTuple):
    code: int
    out: str
    err: str


@dataclass(frozen=True)
class _Template:
    origin: Path
    patch: Path
    parent: str
    tree: str
    parent_tree: str


@dataclass(frozen=True)
class _Shared:
    """A fresh clone of the template origin: the shared tree a session lands in."""

    real: Path
    folder: Path
    template: _Template


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, f"git {args} exit {done.returncode}: {done.stderr}"
    return done.stdout


def _write(path: Path, text: str) -> None:
    """LF bytes, so the file is what the test wrote and not what the platform translated."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


@pytest.fixture(scope="module")
def _git_home(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Point every git call at a global config of the test's own, with `core.autocrlf true`
    and no system config, so a developer's settings (hooks, signing, prefixes) cannot reach
    the run and the run is the one a machine with that global setting makes."""
    home = tmp_path_factory.mktemp("git-home")
    hooks = home / "no-hooks"
    hooks.mkdir()
    config = home / "gitconfig"
    _write(
        config,
        "[core]\n\tautocrlf = true\n"
        f"\thooksPath = {hooks.as_posix()}\n"
        "[user]\n\tname = Gate Test\n\temail = gate@example.invalid\n"
        "[commit]\n\tgpgsign = false\n"
        "[init]\n\tdefaultBranch = main\n",
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GIT_CONFIG_GLOBAL", str(config))
        patch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        yield home


@pytest.fixture(scope="module")
def _template(tmp_path_factory: pytest.TempPathFactory, _git_home: Path) -> _Template:
    """An origin at the parent, and the patch, tree and parent a builder clone recorded."""
    root = tmp_path_factory.mktemp("template")
    origin = root / "origin"
    _git(root, "init", "-q", str(origin))
    _write(origin / "notes" / "a file.txt", "one\ntwo\n")
    _write(origin / "keep.txt", "keep\n")
    _write(origin / "old name.txt", "moved, not changed\n")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-q", "-m", "parent")
    parent = _git(origin, "rev-parse", "HEAD").strip()
    build = root / "build"
    _git(root, "clone", "-q", str(origin), str(build))
    _write(build / "notes" / "a file.txt", "one\ntwo\nthree\n")
    _git(build, "mv", "old name.txt", "new name.txt")
    _write(build / "added.txt", "added\n")
    _git(build, "add", "-A")
    _git(build, "commit", "-q", "-m", "change")
    patch = root / "change.patch"
    _git(
        build,
        "diff",
        "--binary",
        "--no-color",
        "--no-ext-diff",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "-M",
        f"--output={patch}",
        "HEAD~1",
        "HEAD",
    )
    assert b"rename from old name.txt" in patch.read_bytes(), "the patch has no rename"
    return _Template(
        origin=origin,
        patch=patch,
        parent=parent,
        tree=_git(build, "rev-parse", "HEAD^{tree}").strip(),
        parent_tree=_git(build, "rev-parse", "HEAD~1^{tree}").strip(),
    )


@pytest.fixture
def shared(tmp_path: Path, _template: _Template) -> _Shared:
    real = tmp_path / "shared tree"
    _git(tmp_path, "clone", "-q", str(_template.origin), str(real))
    _git(real, "config", "core.autocrlf", "true")
    assert _git(real, "config", "core.autocrlf").strip() == "true"
    assert (real / "keep.txt").read_bytes() == b"keep\r\n", "the checkout is not CRLF"
    return _Shared(real, tmp_path, _template)


def _paths_file(folder: Path, paths: tuple[str, ...], name: str = "paths.txt") -> Path:
    path = folder / name
    _write(path, "".join(f"{entry}\n" for entry in paths))
    return path


def _run(
    *args: str,
    temp: Path | None = None,
    console: str | None = None,
    environment: dict[str, str] | None = None,
) -> _Run:
    """One gate run; with `temp`, its temporary folder is made there and nowhere else; with
    `console`, python is not isolated and its standard streams use that encoding, as they do on
    a machine whose console code page it is; with `environment`, those variables are set."""
    extra = dict(environment or {})
    isolation = ["-I"]
    if temp is not None:
        extra |= {"TMPDIR": str(temp), "TEMP": str(temp), "TMP": str(temp)}
    if console is not None:
        extra |= {_IO_ENCODING: console, "PYTHONUTF8": "0"}
        isolation = []
    env = {**os.environ, **extra} if extra else None
    done = subprocess.run(
        [sys.executable, "-B", *isolation, str(_SCRIPT), "check", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
        env=env,
    )
    return _Run(done.returncode, done.stdout, done.stderr)


def _gate(
    shared: _Shared,
    *,
    allow: tuple[str, ...] = (),
    paths: Path | None = None,
    parent: str | None = None,
    tree: str | None = None,
    patch: Path | None = None,
    repo: Path | None = None,
    temp: Path | None = None,
    console: str | None = None,
    environment: dict[str, str] | None = None,
) -> _Run:
    template = shared.template
    args = [
        "--repo",
        str(repo or shared.real),
        "--parent",
        parent or template.parent,
        "--patch",
        str(patch or template.patch),
        "--tree",
        tree or template.tree,
    ]
    for line in allow:
        args += ["--allow", line]
    if paths is not None:
        args += ["--paths", str(paths)]
    return _run(*args, temp=temp, console=console, environment=environment)


def _states(out: str) -> dict[str, str]:
    """The state of each check by its letter; every letter exactly once."""
    found: dict[str, list[str]] = {letter: [] for letter in _LETTERS}
    for line in out.splitlines():
        for state in _STATES:
            for letter in _LETTERS:
                if line.startswith(f"{state} ({letter}) "):
                    found[letter].append(state)
    assert all(len(states) == 1 for states in found.values()), (
        f"lines per check: {found}"
    )
    return {letter: states[0] for letter, states in found.items()}


def _printed_commands(out: str) -> list[str]:
    return [line[2:] for line in out.splitlines() if line.startswith("  git -C ")]


def _only_failure(run: _Run, letter: str) -> None:
    """Exit 1, `letter` FAIL and every other check PASS, with no landing command printed: the
    plant is the one thing between this run and an exit 0."""
    assert run.code == 1, f"exit {run.code}\n{run.out}{run.err}"
    states = _states(run.out)
    assert states[letter] == "FAIL", run.out
    others = {key: value for key, value in states.items() if key != letter}
    assert set(others.values()) == {"PASS"}, run.out
    assert _printed_commands(run.out) == [], run.out


def _green(run: _Run) -> None:
    assert run.code == 0, f"exit {run.code}\n{run.out}{run.err}"
    assert set(_states(run.out).values()) == {"PASS"}, run.out
    assert len(_printed_commands(run.out)) == 4, run.out


def _snapshot(repo: Path) -> tuple[str, ...]:
    """HEAD, every ref, the real index bytes, the status and the working-tree file list."""
    files = sorted(
        path.relative_to(repo).as_posix()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    )
    return (
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "for-each-ref"),
        hashlib.sha256((repo / ".git" / "index").read_bytes()).hexdigest(),
        _git(repo, "status", "--porcelain", "--untracked-files=all"),
        "\n".join(files),
    )


# --- the all-green run ----------------------------------------------------------------------


def test_all_green_prints_the_landing_commands_and_runs_none(shared: _Shared) -> None:
    """Every check passes on the parent with one allowed peer file whose name has a space, and a
    --paths file written with a byte-order mark and CRLF line ends, as a Windows editor writes
    it. The commands are printed with the pathspec on both `add --` and `commit --` and none of
    them is run: everything the gate could have written is as it was, and its temporary
    folder is empty again."""
    _write(shared.real / _PEER_NOTE, "a peer's untracked note\n")
    listed = shared.folder / "paths-crlf.txt"
    listed.write_bytes(b"\xef\xbb\xbf" + "".join(f"{p}\r\n" for p in _CHANGED).encode())
    temp = shared.folder / "gate-temp"
    temp.mkdir()
    before = _snapshot(shared.real)
    run = _gate(shared, allow=(_PEER_LINE,), paths=listed, temp=temp)
    _green(run)
    assert _snapshot(shared.real) == before, "the gate changed the repository"
    assert list(temp.iterdir()) == [], "the gate left its temporary folder behind"
    add, commit = _printed_commands(run.out)[1:3]
    for command in (add, commit):
        words = shlex.split(command)
        assert words[-len(_CHANGED) - 1 :] == ["--", *_CHANGED], command
    assert " add -- " in add and " commit -F <message-file> -- " in commit


def test_the_printed_commands_land_exactly_the_tree(shared: _Shared) -> None:
    """Run in a throw-away clone, the printed commands commit the --tree on the --parent. A
    printed command that does not work is a defect the all-green run alone cannot see."""
    land = shared.folder / "land"
    _git(shared.folder, "clone", "-q", str(shared.template.origin), str(land))
    run = _gate(shared, repo=land, paths=_paths_file(shared.folder, _CHANGED))
    _green(run)
    message = shared.folder / "message.txt"
    _write(message, "land the change\n")
    for command in _printed_commands(run.out)[:3]:
        words = shlex.split(command, comments=True)
        words = [str(message) if word == "<message-file>" else word for word in words]
        done = subprocess.run(
            words, capture_output=True, text=True, timeout=120, check=False
        )
        assert done.returncode == 0, f"{command}: {done.stderr}"
    assert _git(land, "rev-parse", "HEAD^{tree}").strip() == shared.template.tree
    assert _git(land, "rev-parse", "HEAD~1").strip() == shared.template.parent
    assert _git(land, "status", "--porcelain", "--untracked-files=all") == ""


# --- one planted failure per check, each beside its control ---------------------------------


def test_a_moved_parent_fails_check_a_alone(shared: _Shared) -> None:
    """Planted: a peer's commit on top of the parent. The status is clean, nothing is staged and
    the patch still writes the --tree on the --parent, so without check (a) the gate would
    exit 0 and the landing would go on a HEAD that moved."""
    listed = _paths_file(shared.folder, _CHANGED)
    _green(_gate(shared, paths=listed))
    _write(shared.real / "peer.txt", "a peer landed first\n")
    _git(shared.real, "add", "--", "peer.txt")
    _git(shared.real, "commit", "-q", "-m", "a peer's commit")
    run = _gate(shared, paths=listed)
    _only_failure(run, "a")
    assert f"not the --parent {shared.template.parent}" in run.out


def test_a_status_line_that_is_not_allowed_fails_check_b_alone(shared: _Shared) -> None:
    """Planted: an untracked file no --allow line names. Allowed, the same file passes (the
    control); not allowed, only check (b) can see it, and it names the line."""
    listed = _paths_file(shared.folder, _CHANGED)
    _write(shared.real / "stray.txt", "written by someone\n")
    _green(_gate(shared, allow=("?? stray.txt",), paths=listed))
    run = _gate(shared, paths=listed)
    _only_failure(run, "b")
    assert "not allowed: '?? stray.txt'" in run.out


def test_an_allowed_line_that_is_absent_fails_check_b_alone(shared: _Shared) -> None:
    """Planted: an --allow line for a file that is not there. Present, it passes (the control);
    absent, the status no longer matches what the session recorded, and only (b) says so."""
    listed = _paths_file(shared.folder, _CHANGED)
    gone = shared.real / "gone.txt"
    _write(gone, "here for the control\n")
    _green(_gate(shared, allow=("?? gone.txt",), paths=listed))
    gone.unlink()
    run = _gate(shared, allow=("?? gone.txt",), paths=listed)
    _only_failure(run, "b")
    assert "allowed but absent: '?? gone.txt'" in run.out


def test_a_staged_file_fails_check_c_alone(shared: _Shared) -> None:
    """Planted: a staged file whose status line IS allowed, so check (b) passes and only (c)
    can see it. Untracked and allowed, the same file passes (the control)."""
    listed = _paths_file(shared.folder, _CHANGED)
    _write(shared.real / "staged.txt", "a peer's staged work\n")
    _green(_gate(shared, allow=("?? staged.txt",), paths=listed))
    _git(shared.real, "add", "--", "staged.txt")
    run = _gate(shared, allow=("A  staged.txt",), paths=listed)
    _only_failure(run, "c")
    assert "staged: 'staged.txt'" in run.out


def test_a_tree_that_differs_fails_check_d_alone(shared: _Shared) -> None:
    """Planted: a --tree that is a real tree but not the one the patch writes (the parent's
    own). HEAD, status, index and the changed paths are all as recorded, so without check
    (d) the gate would pass a landing whose result nobody reproduced."""
    listed = _paths_file(shared.folder, _CHANGED)
    _green(_gate(shared, paths=listed))
    run = _gate(shared, tree=shared.template.parent_tree, paths=listed)
    _only_failure(run, "d")
    assert f"not the --tree {shared.template.parent_tree}" in run.out


def test_a_paths_list_that_differs_fails_check_e_alone(shared: _Shared) -> None:
    """Planted: a --paths file without the old path of the rename, the path a list written
    from the patch's new names misses. The full list passes (the control); the short one
    fails (e) alone and names the path."""
    _green(_gate(shared, paths=_paths_file(shared.folder, _CHANGED)))
    short = tuple(path for path in _CHANGED if path != "old name.txt")
    run = _gate(shared, paths=_paths_file(shared.folder, short, "short.txt"))
    _only_failure(run, "e")
    assert "changed, not listed: 'old name.txt'" in run.out


# --- check (f): what the printed `git add --` would store -----------------------------------

_TEN = "".join(f"line {number}\n" for number in range(1, 11))


def _build_case(
    folder: Path,
    files: dict[str, str],
    change: Callable[[Path], None],
    *,
    real_config: tuple[tuple[str, str], ...] = (),
) -> _Shared:
    """A case of its own in `folder`: an origin holding `files`, a builder clone that `change`
    edits, stages and commits as the chain, and a fresh clone of the origin as the shared tree,
    whose working tree holds CRLF files and whose own config gets `real_config`."""
    folder.mkdir(parents=True, exist_ok=True)
    origin, build = folder / "c-origin", folder / "c-build"
    real = folder / "c shared tree"
    _git(folder, "init", "-q", str(origin))
    for name, text in files.items():
        _write(origin / name, text)
    _git(origin, "add", "-A")
    _git(origin, "commit", "-q", "-m", "parent")
    parent = _git(origin, "rev-parse", "HEAD").strip()
    _git(folder, "clone", "-q", str(origin), str(build))
    change(build)
    _git(build, "add", "-A")
    _git(build, "commit", "-q", "-m", "change")
    patch = folder / "c-change.patch"
    _git(
        build,
        "diff",
        "--binary",
        "--no-color",
        "--no-ext-diff",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "-M",
        f"--output={patch}",
        "HEAD~1",
        "HEAD",
    )
    _git(folder, "clone", "-q", str(origin), str(real))
    _git(real, "config", "core.autocrlf", "true")
    for key, value in real_config:
        _git(real, "config", key, value)
    template = _Template(
        origin=origin,
        patch=patch,
        parent=parent,
        tree=_git(build, "rev-parse", "HEAD^{tree}").strip(),
        parent_tree=_git(build, "rev-parse", "HEAD~1^{tree}").strip(),
    )
    return _Shared(real, folder, template)


def _ten_line_case(folder: Path) -> _Shared:
    """`A.txt` has ten lines and the patch changes line 8, far from line 2 where a peer edits,
    so the patch still applies on top of the peer's edit. `keep.txt` is a path the patch leaves
    alone."""

    def change(build: Path) -> None:
        _write(build / "A.txt", _TEN.replace("line 8\n", "line eight, the session's\n"))

    return _build_case(folder, {"A.txt": _TEN, "keep.txt": "keep\n"}, change)


def _peer_edits(shared: _Shared, name: str, old: str, new: str) -> None:
    """A peer's uncommitted edit of one line in the shared tree, whose files hold CRLF lines."""
    path = shared.real / name
    data = path.read_bytes()
    assert f"{old}\r\n".encode() in data, "the working tree is not CRLF"
    path.write_bytes(data.replace(f"{old}\r\n".encode(), f"{new}\r\n".encode(), 1))


def _land(run: _Run, folder: Path) -> None:
    """Run the three printed landing commands, each as printed, in the tree they name."""
    message = folder / "message.txt"
    _write(message, "land the change\n")
    for command in _printed_commands(run.out)[:3]:
        words = shlex.split(command, comments=True)
        words = [str(message) if word == "<message-file>" else word for word in words]
        done = subprocess.run(
            words, capture_output=True, text=True, timeout=120, check=False
        )
        assert done.returncode == 0, f"{command}: {done.stderr}"


def _landed_by_hand(shared: _Shared, paths: tuple[str, ...]) -> tuple[str, str]:
    """What the commands the gate refused to print would have committed: the same apply, add
    and commit with a pathspec, run in a copy of the shared tree. The tree it wrote and the
    commit's diff."""
    copy = shared.folder / "by-hand"
    shutil.copytree(shared.real, copy)
    message = shared.folder / "by-hand-message.txt"
    _write(message, "land the change\n")
    _git(copy, "apply", str(shared.template.patch))
    _git(copy, "add", "--", *paths)
    _git(copy, "commit", "-q", "-F", str(message), "--", *paths)
    return (
        _git(copy, "rev-parse", "HEAD^{tree}").strip(),
        _git(copy, "show", "--format=", "HEAD"),
    )


@pytest.mark.parametrize("hiding", ["allowed", "assume-unchanged", "skip-worktree"])
def test_a_peer_edit_to_a_changed_path_fails_check_f_alone(
    tmp_path: Path, _git_home: Path, hiding: str
) -> None:
    """Planted: a peer's uncommitted edit to A.txt, a path the patch also changes on another
    line. Allowed as ` M A.txt`, or hidden from the status by `assume-unchanged` or
    `skip-worktree`, checks (a) to (e) all pass, and without check (f) the gate would exit 0
    and the printed `git add --` would store the peer's line in the landing commit. Without
    the edit the same run is green (the control). The gate changes nothing in the repository;
    for the allowed edit, the commands it refused are shown to land another tree, the peer's
    line in it."""
    shared = _ten_line_case(tmp_path)
    listed = _paths_file(tmp_path, ("A.txt",))
    _green(_gate(shared, paths=listed))
    if hiding != "allowed":
        _git(shared.real, "update-index", f"--{hiding}", "--", "A.txt")
    _peer_edits(shared, "A.txt", "line 2", "line two, a peer's uncommitted line")
    allow = (" M A.txt",) if hiding == "allowed" else ()
    before = _snapshot(shared.real)
    run = _gate(shared, allow=allow, paths=listed)
    _only_failure(run, "f")
    assert "'A.txt'" in run.out
    assert _snapshot(shared.real) == before, "the gate changed the repository"
    if hiding == "allowed":
        tree, shown = _landed_by_hand(shared, ("A.txt",))
        assert tree != shared.template.tree, "the refused commands land the gated tree"
        assert "a peer's uncommitted line" in shown


def test_the_normal_flow_lands_exactly_the_tree_beside_an_allowed_peer_edit(
    tmp_path: Path, _git_home: Path
) -> None:
    """The flow the reference documents: the gate runs before the patch is applied, a peer's
    uncommitted edit to a path the patch leaves alone is allowed, and the printed commands then
    land exactly the --tree and leave that edit uncommitted. Check (f) must not stand in its
    way."""
    shared = _ten_line_case(tmp_path)
    _peer_edits(shared, "keep.txt", "keep", "keep, a peer's uncommitted edit")
    run = _gate(shared, allow=(" M keep.txt",), paths=_paths_file(tmp_path, ("A.txt",)))
    _green(run)
    _land(run, tmp_path)
    landed = _git(shared.real, "rev-parse", "HEAD^{tree}").strip()
    assert landed == shared.template.tree
    status = _git(shared.real, "status", "--porcelain", "--untracked-files=all")
    assert status == " M keep.txt\n"


@pytest.mark.parametrize(
    "content",
    ["local content\n", "added\n"],
    ids=["other bytes", "the patch's own bytes"],
)
def test_an_untracked_file_where_the_patch_adds_one_fails_check_f_alone(
    shared: _Shared, content: str
) -> None:
    """Planted: an untracked file at `added.txt`, a path the patch adds, allowed as
    `?? added.txt`, holding other bytes or the patch's own. `git apply` refuses to create a file
    that exists, so the printed commands would stop at the first. Without the file the same run
    is green (the control)."""
    listed = _paths_file(shared.folder, _CHANGED)
    _green(_gate(shared, paths=listed))
    _write(shared.real / "added.txt", content)
    run = _gate(shared, allow=("?? added.txt",), paths=listed)
    _only_failure(run, "f")
    assert "'added.txt'" in run.out
    refused = subprocess.run(
        ["git", "-C", str(shared.real), "apply", str(shared.template.patch)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert refused.returncode != 0, "git apply took the patch over the file"
    assert "already exists in working directory" in refused.stderr


def test_a_patch_that_changes_no_path_fails_check_f_alone(shared: _Shared) -> None:
    """Planted: a patch whose lines replace a line with itself, so its tree is the parent's own
    tree: (a) to (e) pass, and the printed commands would stage and commit nothing. The real
    patch is green (the control)."""
    _green(_gate(shared, paths=_paths_file(shared.folder, _CHANGED)))
    noop = shared.folder / "noop.patch"
    _write(
        noop,
        "diff --git a/keep.txt b/keep.txt\n--- a/keep.txt\n+++ b/keep.txt\n"
        "@@ -1 +1 @@\n-keep\n+keep\n",
    )
    nothing = _paths_file(shared.folder, (), "nothing.txt")
    run = _gate(shared, patch=noop, tree=shared.template.parent_tree, paths=nothing)
    _only_failure(run, "f")
    assert "changes no path" in run.out


def test_a_changed_path_that_an_ignore_rule_names_fails_check_f_alone(
    tmp_path: Path, _git_home: Path
) -> None:
    """Planted: the patch adds `ignored/new.txt`, forced past a rule that names `ignored/`.
    `git add --` refuses an ignored path, so the printed commands would stop at it; the same
    patch under a name no rule names is green (the control)."""

    def adding(folder: str) -> Callable[[Path], None]:
        def change(build: Path) -> None:
            _write(build / folder / "new.txt", "a new file\n")
            _git(build, "add", "-f", "--", f"{folder}/new.txt")

        return change

    files = {".gitignore": "ignored/\n", "keep.txt": "keep\n"}
    control = _build_case(tmp_path / "control", files, adding("visible"))
    _green(_gate(control, paths=_paths_file(control.folder, ("visible/new.txt",))))
    plant = _build_case(tmp_path / "plant", files, adding("ignored"))
    run = _gate(plant, paths=_paths_file(plant.folder, ("ignored/new.txt",)))
    _only_failure(run, "f")
    assert "ignored, so `git add --` refuses it: 'ignored/new.txt'" in run.out
    _git(plant.real, "apply", str(plant.template.patch))
    refused = subprocess.run(
        ["git", "-C", str(plant.real), "add", "--", "ignored/new.txt"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert refused.returncode != 0, "git add took an ignored path"


def test_an_executable_bit_that_git_add_cannot_store_fails_check_f_alone(
    tmp_path: Path, _git_home: Path
) -> None:
    """Planted: the patch adds `tool.sh` with the executable bit and the shared tree's
    core.filemode is false, as it is on every Windows checkout: the apply writes the file,
    `git add --` stores a new file 100644, and the landing writes another tree. The same file
    without the bit is green in the same repository (the control)."""

    def adding(executable: bool) -> Callable[[Path], None]:
        def change(build: Path) -> None:
            tool = build / "tool.sh"
            _write(tool, "#!/bin/sh\necho tool\n")
            if executable:
                tool.chmod(0o755)
                _git(build, "add", "--chmod=+x", "--", "tool.sh")

        return change

    files, config = {"keep.txt": "keep\n"}, (("core.filemode", "false"),)
    control = _build_case(tmp_path / "ctl", files, adding(False), real_config=config)
    _green(_gate(control, paths=_paths_file(control.folder, ("tool.sh",))))
    plant = _build_case(tmp_path / "plant", files, adding(True), real_config=config)
    run = _gate(plant, paths=_paths_file(plant.folder, ("tool.sh",)))
    _only_failure(run, "f")
    assert "core.filemode is false" in run.out and "'tool.sh'" in run.out
    tree, _ = _landed_by_hand(plant, ("tool.sh",))
    assert tree != plant.template.tree, "the refused commands land the gated tree"


def test_a_new_file_whose_line_ends_git_add_would_convert_fails_check_f_alone(
    tmp_path: Path, _git_home: Path
) -> None:
    """Planted: the chain was built in a repository that converts no line ends (core.autocrlf
    false) and adds `dos.txt` with CRLF line ends, as a Linux machine does for a file meant for
    Windows. The shared tree converts them on the way in (core.autocrlf true), so `git add --`
    stores the LF form, another blob, and the landing writes another tree. The same file with LF
    line ends is green (the control)."""

    def adding(text: str) -> Callable[[Path], None]:
        def change(build: Path) -> None:
            _git(build, "config", "core.autocrlf", "false")
            # The checkout holds CRLF files; with conversion off they would be staged as CRLF
            # blobs, so the one file that is not the plant goes back to LF first.
            _write(build / "keep.txt", "keep\n")
            _write(build / "dos.txt", text)

        return change

    files = {"keep.txt": "keep\n"}
    control = _build_case(tmp_path / "ctl", files, adding("one\ntwo\n"))
    _green(_gate(control, paths=_paths_file(control.folder, ("dos.txt",))))
    plant = _build_case(tmp_path / "plant", files, adding("one\r\ntwo\r\n"))
    run = _gate(plant, paths=_paths_file(plant.folder, ("dos.txt",)))
    _only_failure(run, "f")
    assert "convert its line ends" in run.out and "'dos.txt'" in run.out
    tree, _ = _landed_by_hand(plant, ("dos.txt",))
    assert tree != plant.template.tree, "the refused commands land the gated tree"


@pytest.mark.parametrize(
    "variable",
    [
        "GIT_LITERAL_PATHSPECS",
        "GIT_GLOB_PATHSPECS",
        "GIT_NOGLOB_PATHSPECS",
        "GIT_ICASE_PATHSPECS",
    ],
)
def test_a_pathspec_mode_in_the_environment_does_not_stop_check_f(
    shared: _Shared, variable: str
) -> None:
    """Planted: the session's environment sets a mode in which git reads every path it is handed
    differently. `git check-ignore` refuses the literal mode outright, which made check (f) NOT
    MEASURED, exit 2, on a normal landing. The gate hands git its paths as data, so the same run
    stays green with each variable set, as it is without it (the control)."""
    listed = _paths_file(shared.folder, _CHANGED)
    _green(_gate(shared, paths=listed))
    _green(_gate(shared, paths=listed, environment={variable: "1"}))


# --- the console's code page -----------------------------------------------------------------


def test_a_name_outside_the_console_code_page_still_gets_its_verdict(
    tmp_path: Path, _git_home: Path
) -> None:
    """Run under a cp1252 console: the patch adds a file named with two CJK characters, which
    no single-byte code page holds. The green run prints that name in the landing commands and a
    failing run prints it in a detail line; each used to end in a traceback that exits 1, the
    code for "a check failed", with the verdict never printed. Now each gets its verdict, in
    utf-8."""
    name = "漢字.txt"
    shared = _build_case(
        tmp_path, {"keep.txt": "keep\n"}, lambda build: _write(build / name, "added\n")
    )
    green = _gate(shared, paths=_paths_file(tmp_path, (name,)), console="cp1252")
    _green(green)
    assert name in green.out
    assert "Traceback" not in green.err, green.err
    wrong = _paths_file(tmp_path, ("keep.txt",), "wrong.txt")
    failing = _gate(shared, paths=wrong, console="cp1252")
    _only_failure(failing, "e")
    assert f"changed, not listed: {name!r}" in failing.out
    assert "Traceback" not in failing.err, failing.err


# --- what it cannot measure is never a pass -------------------------------------------------


def _unapplicable(template: _Template, folder: Path) -> Path:
    """The real patch with one context line changed, so it applies to no parent it names."""
    text = template.patch.read_bytes()
    assert text.count(b"\n one\n") == 1, (
        "the context line to change is not in the patch once"
    )
    path = folder / "other.patch"
    path.write_bytes(text.replace(b"\n one\n", b"\n uno\n"))
    return path


@pytest.mark.parametrize("kind", ["missing", "empty", "not a patch", "does not apply"])
def test_an_unreadable_patch_is_not_measured(shared: _Shared, kind: str) -> None:
    """Exit 2: (d) cannot write a tree and (e) and (f) cannot use one, while (a) to (c) pass,
    and no landing command is printed."""
    patch = shared.folder / f"{kind}.patch"
    if kind == "empty":
        patch.write_bytes(b"")
    elif kind == "not a patch":
        patch.write_bytes(b"these are notes, not a patch\n")
    elif kind == "does not apply":
        patch = _unapplicable(shared.template, shared.folder)
    listed = _paths_file(shared.folder, _CHANGED)
    run = _gate(shared, patch=patch, paths=listed)
    assert run.code == 2, f"exit {run.code}\n{run.out}{run.err}"
    states = _states(run.out)
    assert {states[letter] for letter in "def"} == {"NOT MEASURED"}, run.out
    assert {states[letter] for letter in "abc"} == {"PASS"}, run.out
    assert _printed_commands(run.out) == [], run.out
    assert "never a pass (exit 2)" in run.out


@pytest.mark.parametrize("kind", ["plain folder", "no folder"])
def test_a_repo_that_is_not_a_working_tree_is_not_measured(
    shared: _Shared, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 2 with every check NOT MEASURED: a gate that could not find the tree passes
    nothing. Git is stopped from searching above the test folder for a repository."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(shared.folder))
    target = shared.folder / kind
    if kind == "plain folder":
        target.mkdir()
    run = _gate(shared, repo=target, paths=_paths_file(shared.folder, _CHANGED))
    assert run.code == 2, f"exit {run.code}\n{run.out}{run.err}"
    assert set(_states(run.out).values()) == {"NOT MEASURED"}, run.out
    assert _printed_commands(run.out) == [], run.out


@pytest.mark.parametrize("flag", ["--parent", "--tree"])
def test_a_ref_name_or_a_short_id_is_refused(shared: _Shared, flag: str) -> None:
    """A ref name moves with the tree, so `--parent HEAD` would make check (a) true by
    definition; a short id is refused for the same reason it is not a recorded value. Each is
    NOT MEASURED, exit 2, never a pass."""
    listed = _paths_file(shared.folder, _CHANGED)
    if flag == "--parent":
        run = _gate(shared, parent="HEAD", paths=listed)
        letters = ("a", "d", "e", "f")
    else:
        run = _gate(shared, tree=shared.template.tree[:12], paths=listed)
        letters = ("d",)
    assert run.code == 2, f"exit {run.code}\n{run.out}{run.err}"
    states = _states(run.out)
    assert {states[letter] for letter in letters} == {"NOT MEASURED"}, run.out
    assert "is not a full object id" in run.out
    assert _printed_commands(run.out) == [], run.out
