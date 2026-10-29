"""A citation counts as tracked when git finds it, wherever the project root sits in its repository.

`validate_register.is_tracked_at_head` asked git with the project root as the working directory,
so git resolved the pathspec relative to it. A scratch export of a repository, made inside that
repository, therefore found nothing for any path: every `tasks/` citation was reported as "not
tracked at HEAD" although it is tracked at the checkout's HEAD.

Asking from the repository top instead would break the opposite case, a project root that is a
subdirectory of a larger repository and cites paths relative to itself. So a citation is tracked if
git finds it either way, and the second test pins the case that a single repository-top lookup
would lose. The third pins that a path tracked nowhere is still reported from every root.

The functions are loaded from the script file with a fresh module per test, because the module
keeps its project root and a lookup cache in globals.
"""

import importlib.util
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

_SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "flow-mapping"
    / "scripts"
)
_GIT = (
    "git",
    "-c",
    "user.name=test",
    "-c",
    "user.email=test@example.invalid",
    "-c",
    "commit.gpgsign=false",
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run([*_GIT, *args], cwd=repo, check=True, capture_output=True, text=True)


def _repository_tracking(tmp_path: Path, name: str, tracked: str) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / tracked).parent.mkdir(parents=True, exist_ok=True)
    (repo / tracked).write_text("x\n", encoding="utf-8")
    _git(repo, "add", "--", tracked)
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def _is_tracked_from(
    root: Path, rel_path: str, monkeypatch: pytest.MonkeyPatch
) -> bool:
    monkeypatch.setattr(sys, "path", [str(_SCRIPTS), *sys.path])
    spec = importlib.util.spec_from_file_location(
        "validate_register_under_test", _SCRIPTS / "validate_register.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO_ROOT", root)
    return cast(Callable[[str], bool], module.is_tracked_at_head)(rel_path)


def test_a_scratch_export_inside_the_repository_finds_a_tracked_citation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository_tracking(tmp_path, "repo", "tasks/a.md")
    export = repo / "scratch" / "export"
    export.mkdir(parents=True)
    assert _is_tracked_from(export, "tasks/a.md", monkeypatch) is True


def test_a_project_root_below_the_repository_top_still_reads_paths_relative_to_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository_tracking(tmp_path, "mono", "svc/tasks/b.md")
    assert _is_tracked_from(repo / "svc", "tasks/b.md", monkeypatch) is True


def test_a_path_tracked_nowhere_is_reported_from_every_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository_tracking(tmp_path, "repo", "tasks/a.md")
    export = repo / "scratch" / "export"
    export.mkdir(parents=True)
    assert _is_tracked_from(repo, "tasks/never.md", monkeypatch) is False
    assert _is_tracked_from(export, "tasks/never.md", monkeypatch) is False
