"""The scaffold's local-only folders: one self-ignoring ignore file each, and no other.

Several skills call `.ai/tmp/`, `.ai/handoffs/` and `.ai/retrospectives/` gitignored,
and a scaffold that never ignored them left an adopter free to commit hand-offs,
retrospective reports and scratch files. Each folder now gets ONE `.gitignore` holding a
star and an exception for itself, so git ignores every note in the folder but not the
file that says so. No other ignore file is written: the project's root `.gitignore` is
never touched.

The git cases ask real `git check-ignore` in a repository built in `tmp_path`, with the
system config pointed at an empty file and the global one naming an empty excludes file
(an empty global config is not enough: git still reads its default excludes file under
the user's config home), so a developer's own ignore rules can neither ignore a note on
the scaffold's behalf nor hide one from it.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from lemmi_ai_kit import scaffold
from lemmi_ai_kit.manifest import Manifest, load_manifest

_SKILL_MD = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "kit-setup"
    / "SKILL.md"
)

# Written out by hand on purpose: the expectation must not be read back from the code
# under test, or a folder dropped from the code would drop out of the test with it.
_LOCAL_ONLY = (".ai/tmp", ".ai/handoffs", ".ai/retrospectives")
_SELF_IGNORING = b"*\n!.gitignore\n"


@pytest.fixture(scope="module")
def manifest() -> Manifest:
    return load_manifest()


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty git repository with ambient git config neutralised."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed, so git check-ignore cannot be asked")
    empty = tmp_path / "git-empty"
    empty.write_text("", encoding="utf-8")
    # Emptying GIT_CONFIG_GLOBAL is not enough: git still reads its default excludes
    # file under the user's config home, and a planted `*.md` there made this fixture
    # ignore AGENTS.md. An empty excludesFile closes that.
    global_config = tmp_path / "gitconfig-global"
    global_config.write_text(
        f'[core]\n\texcludesFile = "{empty.as_posix()}"\n', encoding="utf-8"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(empty))
    repo = tmp_path / "adopter"
    repo.mkdir()
    completed = subprocess.run(
        ("git", "-C", str(repo), "init", "-q"), capture_output=True, check=False
    )
    if completed.returncode != 0:  # pragma: no cover - fixture setup failure
        pytest.fail("git init failed: " + completed.stderr.decode("utf-8", "replace"))
    return repo


def _ignored(repo: Path, relative: str) -> bool:
    """Does git ignore `relative`? Exit 0 is yes, 1 is no; anything else is no answer."""
    completed = subprocess.run(
        ("git", "-C", str(repo), "check-ignore", "-q", relative),
        capture_output=True,
        check=False,
    )
    if completed.returncode not in (0, 1):
        pytest.fail(
            f"git check-ignore {relative} could not answer (exit {completed.returncode}): "
            + completed.stderr.decode("utf-8", "replace")
        )
    return completed.returncode == 0


def _ignore_files(relatives: list[str]) -> list[str]:
    return sorted(r for r in relatives if r.rsplit("/", 1)[-1] == ".gitignore")


def test_plan_puts_one_self_ignoring_file_in_each_local_only_folder(
    manifest: Manifest,
) -> None:
    planned = scaffold.plan(manifest)
    for folder in _LOCAL_ONLY:
        under = [p for p in planned if p.relative.startswith(f"{folder}/")]
        assert [p.relative for p in under] == [f"{folder}/.gitignore"], (
            f"{folder}/ should hold exactly one planned file, its own .gitignore; "
            f"the plan has {[p.relative for p in under]}"
        )
        assert under[0].content == _SELF_IGNORING, (
            f"{folder}/.gitignore must be exactly two LF lines, a star and an exception "
            f"for itself; the plan has {under[0].content!r}"
        )


def test_git_ignores_a_note_in_each_local_only_folder_but_not_its_ignore_file(
    git_repo: Path, manifest: Manifest
) -> None:
    scaffold.scaffold(git_repo, manifest)
    for folder in _LOCAL_ONLY:
        note = git_repo / folder / "note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("a local note\n", encoding="utf-8")
        assert _ignored(git_repo, f"{folder}/note.md"), (
            f"git does not ignore {folder}/note.md after the scaffold"
        )
        assert not _ignored(git_repo, f"{folder}/.gitignore"), (
            f"git ignores {folder}/.gitignore itself, so the rule could not be committed"
        )
    # The near miss: the star stays inside its folder. The files a project commits are
    # still visible to git.
    for committed in ("AGENTS.md", ".ai/ai-changelog.md", ".ai/templates/tasks.md"):
        assert not _ignored(git_repo, committed), (
            f"the scaffold made git ignore {committed}"
        )


def test_self_ignoring_files_follow_the_managed_file_rules(
    tmp_path: Path, manifest: Manifest
) -> None:
    files = [f"{folder}/.gitignore" for folder in _LOCAL_ONLY]

    first = scaffold.scaffold(tmp_path, manifest)
    assert set(files) <= set(first.by_action("written")), first.results

    second = scaffold.scaffold(tmp_path, manifest)
    assert set(files) <= set(second.by_action("unchanged")), second.results
    assert all((tmp_path / f).read_bytes() == _SELF_IGNORING for f in files)

    # An adopter's edit survives a plain run and a reseed: these are managed files, not
    # seeds. Only `force`, the explicit refresh of managed files, restores the kit's copy.
    edited = tmp_path / ".ai/handoffs/.gitignore"
    adopter_copy = b"*\n!.gitignore\n!README.md\n"
    edited.write_bytes(adopter_copy)

    third = scaffold.scaffold(tmp_path, manifest)
    assert third.by_action("skipped-exists") == [".ai/handoffs/.gitignore"]
    assert edited.read_bytes() == adopter_copy

    reseeded = scaffold.scaffold(tmp_path, manifest, reseed=True)
    assert reseeded.by_action("skipped-exists") == [".ai/handoffs/.gitignore"]
    assert edited.read_bytes() == adopter_copy

    forced = scaffold.scaffold(tmp_path, manifest, force=True)
    assert forced.by_action("overwritten") == [".ai/handoffs/.gitignore"]
    assert edited.read_bytes() == _SELF_IGNORING


def test_the_scaffold_writes_no_other_ignore_file(
    tmp_path: Path, manifest: Manifest
) -> None:
    root_ignore = tmp_path / ".gitignore"
    project_rules = b"node_modules/\r\n# the project's own rules, CRLF and all\r\n"
    root_ignore.write_bytes(project_rules)

    for _ in range(2):
        report = scaffold.scaffold(tmp_path, manifest)
        assert root_ignore.read_bytes() == project_rules
        assert _ignore_files([r.relative for r in report.results]) == sorted(
            f"{folder}/.gitignore" for folder in _LOCAL_ONLY
        )


def _scaffold_section() -> str:
    """kit-setup's `### Scaffold` section, whitespace folded, or a loud failure."""
    text = _SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n### Scaffold\n")
    assert start != -1, "kit-setup SKILL.md has no '### Scaffold' heading"
    end = text.find("\n## ", start + 1)
    assert end != -1, "the '### Scaffold' section of kit-setup SKILL.md has no end"
    return " ".join(text[start:end].split())


def test_kit_setup_names_the_local_only_folders_and_no_other_ignore_file() -> None:
    section = _scaffold_section()
    missing = [folder for folder in _LOCAL_ONLY if f"`{folder}/`" not in section]
    assert not missing, f"kit-setup's Scaffold section does not name {missing}"
    assert "self-ignoring `.gitignore`" in section
    assert "`*`" in section and "`!.gitignore`" in section
    # Qualified where the claim is made: where the project's own rules already ignore a
    # folder, git ignores the seeded file in it as well.
    qualified = (
        "but not that file, unless the project's own ignore rules already cover "
        "the folder"
    )
    assert qualified in section, "the Scaffold section says git never ignores the file"
    assert "edits no other ignore file" in section
    # That phrase alone can stand next to a sentence saying the root file is edited.
    assert "root `.gitignore` stays exactly as it was" in section, (
        "the Scaffold section no longer says the root .gitignore is left as it was"
    )
