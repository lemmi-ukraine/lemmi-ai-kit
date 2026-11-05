"""`branch-switch` backs the tree up with a script that cannot overwrite and cannot half-succeed.

The skill's mandatory backup used to be a shell block. It opened with a variable assignment (a
shell guard in front of a model session denies a command that starts that way), wrote to a folder
no ignore rule covers, and named it with the DATE only, so a second backup the same day silently
overwrote the first. It is now `scripts/pre_switch_backup.py`, which writes under the git
directory and names the folder with a UTC stamp.

Each behaviour test runs the script as a process in a throwaway repository, the way a session
does. The repository is built here with plain git and sets what it depends on locally.
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "branch-switch"
)
_SCRIPT = _SKILL / "scripts" / "pre_switch_backup.py"
_STAMP = "20261030T101500Z"
_BRANCH = "feature/x y"
_LEAF = f"{_STAMP}-feature-x-y"

# What each file must hold: the byte-for-byte output of this git command, run by the test.
_EXPECTED: dict[str, tuple[str, ...]] = {
    "unstaged-tracked.patch": ("diff", "--binary"),
    "staged-tracked.patch": ("diff", "--cached", "--binary"),
    "untracked-inventory.txt": ("ls-files", "--others", "--exclude-standard"),
    "stash-list.txt": ("stash", "list"),
    "head-at-backup.txt": ("rev-parse", "HEAD"),
    "branch-at-backup.txt": ("rev-parse", "--abbrev-ref", "HEAD"),
}


def _git(repo: Path, *args: str) -> "subprocess.CompletedProcess[bytes]":
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)


def _init(repo: Path) -> Path:
    repo.mkdir()
    _git(repo, "init", "-q")
    for key, value in (
        ("user.name", "tester"),
        ("user.email", "tester@example.invalid"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
    ):
        _git(repo, "config", key, value)
    return repo


def _working_repo(tmp_path: Path) -> Path:
    """One commit, one older stash, then one of each thing the backup has to see."""
    repo = _init(tmp_path / "repo")
    (repo / "tracked.txt").write_text("one\n", encoding="utf-8")
    (repo / "staged.txt").write_text("one\n", encoding="utf-8")
    (repo / "image.bin").write_bytes(bytes(range(256)))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / "tracked.txt").write_text("older work\n", encoding="utf-8")
    _git(repo, "stash", "push", "-q", "-m", "older work")
    (repo / "tracked.txt").write_text("one\ntwo\n", encoding="utf-8")
    (repo / "staged.txt").write_text("one\nthree\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")
    (repo / "image.bin").write_bytes(bytes(reversed(range(256))))
    (repo / "untracked.txt").write_text("loose\n", encoding="utf-8")
    (repo / ".git" / "info" / "exclude").write_text("ignored.log\n", encoding="utf-8")
    (repo / "ignored.log").write_text("noise\n", encoding="utf-8")
    return repo


def _backup(repo: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-B", str(_SCRIPT), _BRANCH, "--stamp", _STAMP],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def _folder(repo: Path) -> Path:
    return repo / ".git" / "pre-switch-backups" / _LEAF


def _hashes(folder: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.iterdir())
    }


def test_a_run_writes_every_file_under_the_git_directory_and_prints_the_folder_last(
    tmp_path: Path,
) -> None:
    repo = _working_repo(tmp_path)
    done = _backup(repo)
    assert done.returncode == 0, done.stderr
    printed = Path(done.stdout.strip().splitlines()[-1])
    assert printed.resolve() == _folder(repo).resolve()
    assert sorted(path.name for path in printed.iterdir()) == sorted(_EXPECTED)
    for name, args in _EXPECTED.items():
        assert (printed / name).read_bytes() == _git(repo, *args).stdout, name
    inventory = (printed / "untracked-inventory.txt").read_text(encoding="utf-8")
    assert "untracked.txt" in inventory and "ignored.log" not in inventory
    assert "older work" in (printed / "stash-list.txt").read_text(encoding="utf-8")


def test_a_changed_binary_file_is_saved_as_a_patch_that_can_restore_it(
    tmp_path: Path,
) -> None:
    repo = _working_repo(tmp_path)
    plain = _git(repo, "diff").stdout
    assert b"GIT binary patch" not in plain, (
        "control: a plain diff does not carry the bytes"
    )
    done = _backup(repo)
    assert done.returncode == 0, done.stderr
    patch = (_folder(repo) / "unstaged-tracked.patch").read_bytes()
    assert b"GIT binary patch" in patch


def test_a_second_run_with_the_same_stamp_refuses_and_leaves_the_first_backup_intact(
    tmp_path: Path,
) -> None:
    repo = _working_repo(tmp_path)
    assert _backup(repo).returncode == 0
    before = _hashes(_folder(repo))
    (repo / "tracked.txt").write_text(
        "changed between the two runs\n", encoding="utf-8"
    )
    second = _backup(repo)
    assert second.returncode != 0
    assert second.stdout == "", "a refused run must not print a folder to quote"
    assert "already exists" in second.stderr
    assert _hashes(_folder(repo)) == before


def test_a_failing_step_exits_non_zero_prints_no_path_and_says_the_folder_is_incomplete(
    tmp_path: Path,
) -> None:
    repo = _init(tmp_path / "unborn")  # no commit, so `git rev-parse HEAD` fails midway
    done = _backup(repo)
    assert done.returncode == 1
    assert done.stdout == ""
    assert "INCOMPLETE" in done.stderr and "rev-parse" in done.stderr
    left = _folder(repo)
    assert (left / "stash-list.txt").is_file()
    assert not (left / "head-at-backup.txt").exists()


def test_the_script_says_what_it_does_not_save_before_it_prints_the_folder(
    tmp_path: Path,
) -> None:
    done = _backup(_working_repo(tmp_path))
    assert done.returncode == 0, done.stderr
    *said, _path = done.stdout.strip().splitlines()
    not_saved = next((line for line in said if line.startswith("NOT saved")), "")
    assert "untracked" in not_saved and "--include-untracked" in not_saved
    assert "ignored" in not_saved


def _fenced_blocks(markdown: str) -> list[str]:
    return re.findall(
        r"^```[^\n]*\n(.*?)^```", markdown, flags=re.DOTALL | re.MULTILINE
    )


def _assignment_led(block: str) -> list[str]:
    """Lines that open with `NAME=value`: the shape a shell guard denies as a command start."""
    return [
        line
        for line in block.splitlines()
        if re.match(r"\s*[A-Za-z_][A-Za-z0-9_]*=", line)
    ]


def test_the_assignment_detector_sees_the_old_block_shape() -> None:
    assert _assignment_led('D="x"\nmkdir -p "$D"\ngit diff > "$D/a.patch"') == ['D="x"']
    assert (
        _assignment_led('python -B "${CLAUDE_SKILL_DIR}/scripts/x.py" <branch>') == []
    )


def test_the_skill_prints_one_command_that_starts_with_the_script() -> None:
    text = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    blocks = _fenced_blocks(text)
    naming = [block for block in blocks if "pre_switch_backup.py" in block]
    assert len(naming) == 1, f"{len(naming)} fenced blocks name the backup script"
    first = next(line for line in naming[0].splitlines() if line.strip())
    assert first.startswith(
        'python -B "${CLAUDE_SKILL_DIR}/scripts/pre_switch_backup.py" '
    )
    assert _SCRIPT.is_file(), "the printed command points at a script that is not there"
    offenders = [line for block in blocks for line in _assignment_led(block)]
    assert offenders == [], f"a printed block opens with an assignment: {offenders}"
    assert ".ai/pre-switch-backups" not in text, (
        "the backup folder is not under .ai/ any more"
    )
