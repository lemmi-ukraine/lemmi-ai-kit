"""The pre-publish guard: what blocks, and what must never be mistaken for clean.

Every test but the last builds its own throwaway checkout. This repo's own working tree
is written by several sessions at once and has been dirty at every measurement taken, so
a test that asserted anything about *its* cleanliness would be red or green by accident.
The one test that does touch the real checkout asserts only that the guard can measure
it -- never that the answer is clean.

`_isolated_git` points git's global and system config at an empty file for the duration
of each test, so a developer's `core.excludesFile` cannot quietly ignore a fixture file
and turn a blocking probe green.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from lemmi_ai_kit import publish
from lemmi_ai_kit.cli import main
from lemmi_ai_kit.manifest import PACKS

_REPO_ROOT = Path(__file__).resolve().parents[1]

# core is listed only to Claude, python only to Codex, and in the two different source
# syntaxes. A pack listed to one host still ships to that host, so the guard must union
# the manifests rather than read whichever it finds first.
_CLAUDE_MARKETPLACE: dict[str, Any] = {
    "name": "fixture",
    "plugins": [{"name": "fixture-core", "source": "./plugins/core"}],
}
_CODEX_MARKETPLACE: dict[str, Any] = {
    "name": "fixture",
    "plugins": [
        {
            "name": "fixture-python",
            "source": {"source": "local", "path": "./plugins/python"},
        }
    ],
}


# pyright cannot see that pytest collects an autouse fixture, so it reads as dead code.
@pytest.fixture(autouse=True)
def _isolated_git(  # pyright: ignore[reportUnusedFunction]
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neutralise ambient git config and supply a committer identity.

    Applied to `os.environ`, not just to the fixture-building calls, because
    `publish._git` reads the real environment -- which is the point: the isolation has
    to cover the code under test, not only the scaffolding around it.
    """
    empty = tmp_path / "gitconfig-empty"
    empty.write_text("", encoding="utf-8")
    for name, value in (
        ("GIT_CONFIG_GLOBAL", str(empty)),
        ("GIT_CONFIG_SYSTEM", str(empty)),
        ("GIT_AUTHOR_NAME", "fixture"),
        ("GIT_AUTHOR_EMAIL", "fixture@example.invalid"),
        ("GIT_COMMITTER_NAME", "fixture"),
        ("GIT_COMMITTER_EMAIL", "fixture@example.invalid"),
    ):
        monkeypatch.setenv(name, value)


def _git(repo: Path, *argv: str) -> None:
    completed = subprocess.run(
        ("git", *argv), cwd=repo, capture_output=True, check=False
    )
    if completed.returncode != 0:  # pragma: no cover - fixture setup failure
        pytest.fail(
            f"fixture git {' '.join(argv)} failed: "
            + completed.stderr.decode("utf-8", "replace")
        )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture_repo(
    tmp_path: Path,
    *,
    claude: dict[str, Any] | None = None,
    codex: dict[str, Any] | None = None,
) -> Path:
    """A committed checkout shaped like this one: two packs, two marketplaces, clean."""
    repo = tmp_path / "checkout"
    repo.mkdir()
    if claude is not None:
        _write(
            repo / ".claude-plugin" / "marketplace.json", json.dumps(claude, indent=2)
        )
    if codex is not None:
        _write(repo / ".agents" / "plugins" / "marketplace.json", json.dumps(codex))
    _write(repo / "plugins" / "core" / "skills" / "demo" / "SKILL.md", "# demo\n")
    _write(repo / "plugins" / "python" / "skills" / "demo-py" / "SKILL.md", "# py\n")
    # A tracked file OUTSIDE the payload, so "dirty anywhere blocks" is testable.
    _write(repo / "README.md", "fixture\n")
    _write(repo / ".gitignore", "__pycache__/\n")

    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture")
    return repo


def _both(tmp_path: Path) -> Path:
    return _fixture_repo(tmp_path, claude=_CLAUDE_MARKETPLACE, codex=_CODEX_MARKETPLACE)


# --- the three probes ---------------------------------------------------------------


def test_a_clean_checkout_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _both(tmp_path)
    assert main(["publish-check", "--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "PUBLISH CHECK PASSED" in out
    # The payload is unioned across both manifests and both source syntaxes.
    assert "payload: plugins/core, plugins/python" in out


def test_an_untracked_payload_file_blocks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _both(tmp_path)
    _write(repo / "plugins" / "core" / "skills" / "demo" / "DRAFT.md", "wip\n")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "PUBLISH BLOCKED" in out
    assert "untracked in the payload (1)" in out
    assert "plugins/core/skills/demo/DRAFT.md" in out


def test_a_gitignored_payload_file_blocks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The surprising one. Ignored by git is not excluded by the copy.

    Six `.pyc` files reached V-1's measured payload this way, and `git status` says
    nothing about them -- so a guard built on `status` alone would have called that
    tree clean.
    """
    repo = _both(tmp_path)
    _write(repo / "plugins" / "core" / "__pycache__" / "demo.cpython-311.pyc", "x")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "gitignored in the payload (1)" in out
    assert "demo.cpython-311.pyc" in out
    # It is invisible to the working-tree probe, which is why the third probe exists.
    assert "working tree (0)" in out


def test_a_dirty_file_outside_the_payload_still_blocks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """'Empty' means empty, not 'only my files'. README ships in no pack and still blocks."""
    repo = _both(tmp_path)
    _write(repo / "README.md", "edited\n")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "working tree (1)" in out
    assert "README.md" in out
    assert "untracked in the payload (0)" in out


def test_the_shipped_file_count_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """V-1's arithmetic, restated for whoever is about to publish: tracked + extra."""
    repo = _both(tmp_path)
    _write(repo / "plugins" / "core" / "skills" / "demo" / "DRAFT.md", "wip\n")
    _write(repo / "plugins" / "python" / "__pycache__" / "x.cpython-311.pyc", "x")

    report = publish.check(repo)
    assert report.tracked == 2, "one SKILL.md per pack"
    assert report.extra == 2, "one untracked plus one ignored"

    assert main(["publish-check", "--repo", str(repo)]) == 1
    assert "would copy 4 file(s) out of the payload" in capsys.readouterr().out


# --- counting: a guard about what ships cannot undercount what ships -------------------


def test_an_untracked_directory_is_counted_file_by_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The `-uall` regression. Without it git collapses the drop to a single entry.

    Measured before the fix: six files under a pack reported as `working tree (1)`.
    A guard whose subject is "what actually ships" reporting six as one is the same
    class of defect as the leak it exists to catch.
    """
    repo = _both(tmp_path)
    for index in range(6):
        _write(repo / "plugins" / "core" / "drop" / f"f{index}.md", "x\n")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "working tree (6)" in out
    assert "untracked in the payload (6)" in out
    assert "at least" not in out, "every file here is countable; do not hedge"

    report = publish.check(repo)
    assert report.extra == 6
    assert not report.undercounts


def test_a_nested_repository_blocks_and_its_count_is_marked_a_floor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The limit `-uall` cannot fix, so it is disclosed instead of being wrong quietly.

    Git will not look inside another repository: a vendored clone or someone's scratch
    checkout under a pack is ONE entry however many files it holds. It still blocks --
    that is the part that matters -- but the arithmetic derived from it is a floor, and
    an unmarked directory entry in that list reads as a single file.
    """
    repo = _both(tmp_path)
    nested = repo / "plugins" / "core" / "skills" / "vendored"
    nested.mkdir(parents=True)
    for index in range(3):
        _write(nested / f"s{index}.md", "s\n")
    _git(nested, "init", "-q")
    _git(nested, "add", "-A")
    _git(nested, "commit", "-q", "-m", "inner")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "plugins/core/skills/vendored/" in out
    assert "a whole directory git cannot look inside" in out
    assert "at least" in out, "the total is unknowable, so it must not print as exact"

    report = publish.check(repo)
    assert report.undercounts
    assert report.extra == 1, "one entry standing for three files -- hence the floor"


# --- the refusal carries its remedy ---------------------------------------------------
#
# Half a control otherwise. A publisher told only "no", at the moment they are trying to
# ship, is the publisher who goes looking for a --force -- so the remedy is part of the
# refusal, and these pin it rather than leaving it to drift out of the output.


def test_every_refusal_names_a_remedy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _both(tmp_path)
    _write(repo / "README.md", "edited\n")
    _write(repo / "plugins" / "core" / "skills" / "demo" / "DRAFT.md", "wip\n")
    _write(repo / "plugins" / "core" / "__pycache__" / "x.cpython-311.pyc", "x")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out

    assert out.count("to clear it:") == 3, "every blocking probe, not just the first"
    assert "git add <path> && git commit" in out
    # The destructive one is named exactly, scoped to the payload, preview before delete.
    assert "git clean -Xdn -- plugins/core plugins/python" in out
    assert "git clean -Xdf -- plugins/core plugins/python" in out


def test_a_passing_run_prints_no_remedy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing to clear, so nothing to say. Advice on a green run is noise that gets skimmed."""
    repo = _both(tmp_path)
    assert main(["publish-check", "--repo", str(repo)]) == 0
    assert "to clear it:" not in capsys.readouterr().out


def test_the_gitignore_trap_is_stated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The remedy a reader would otherwise invent, and it does not work.

    Ignoring an untracked payload file moves it from probe 2 to probe 3; it does not
    stop the copy. Left unsaid, the obvious response to probe 2 is the wrong one.
    """
    repo = _both(tmp_path)
    _write(repo / "plugins" / "core" / "skills" / "demo" / "DRAFT.md", "wip\n")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert ".gitignore does NOT stop it shipping" in out


def test_the_guard_changes_nothing(tmp_path: Path) -> None:
    """It names fixes and applies none. A check with side effects is not a measurement."""
    repo = _both(tmp_path)
    draft = repo / "plugins" / "core" / "skills" / "demo" / "DRAFT.md"
    _write(draft, "wip\n")
    pyc = repo / "plugins" / "core" / "__pycache__" / "x.cpython-311.pyc"
    _write(pyc, "x")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    assert draft.is_file(), "the guard deleted an untracked file"
    assert pyc.is_file(), "the guard ran its own clean command"
    # And it did not stage anything on the publisher's behalf either.
    staged = subprocess.run(
        ("git", "diff", "--cached", "--name-only"),
        cwd=repo,
        capture_output=True,
        check=False,
    )
    assert staged.stdout == b""


# --- the guard must not dirty its own subject -----------------------------------------
#
# Found by `lemmi-ai-kit-c2` against a genuinely empty tree, and confirmed here on a
# clean clone: from zero .pyc, a plain `python -m lemmi_ai_kit publish-check` reports
# `gitignored in the payload (7)` and exits 1, having written all seven itself. Under
# `-B` the same invocation exits 0. The gate was unpassable by construction.
#
# Nothing above could have caught it. Every other test builds a throwaway repo that does
# not contain this package, and the one test that touches the real checkout deliberately
# asserts only measurability, never the verdict.


def test_the_guard_knows_when_it_writes_bytecode_into_its_own_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = tuple(sorted(f"plugins/{pack}" for pack in PACKS))

    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    assert publish.writes_bytecode_into_payload(_REPO_ROOT, payload), (
        "this package lives inside the payload, so importing it dirties what it measures"
    )

    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    assert not publish.writes_bytecode_into_payload(_REPO_ROOT, payload), (
        "-B / PYTHONDONTWRITEBYTECODE is the invocation that makes the gate passable"
    )


def test_a_checkout_that_does_not_contain_this_package_is_not_self_dirtying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The condition is about geography, not about bytecode being on."""
    repo = _both(tmp_path)
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    assert not publish.writes_bytecode_into_payload(repo, ("plugins/core",))


def test_the_bytecode_remedy_appears_only_when_the_guard_caused_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`git clean` alone is not sufficient here, and the printed remedy must say so."""
    ignored = next(
        probe
        for probe in publish._probes(("plugins/core",), self_written=True)  # pyright: ignore[reportPrivateUsage]
        if probe.label == "gitignored in the payload"
    )
    text = "\n".join(ignored.remedy)
    assert "python -B -m lemmi_ai_kit publish-check" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "NOT SUFFICIENT ON ITS OWN HERE" in text
    # Order matters: the destructive command first, then why it is not enough. The
    # reverse invites a clean-and-publish that silently re-dirties the tree.
    assert text.index("git clean -Xdf") < text.index("NOT SUFFICIENT")

    clean = next(
        probe
        for probe in publish._probes(("plugins/core",), self_written=False)  # pyright: ignore[reportPrivateUsage]
        if probe.label == "gitignored in the payload"
    )
    assert not any("-B" in line for line in clean.remedy), (
        "a checkout the guard did not dirty must not be told to work around that"
    )

    # And end to end: a fixture repo does not contain this package, so no -B advice.
    repo = _both(tmp_path)
    _write(repo / "plugins" / "core" / "__pycache__" / "x.cpython-311.pyc", "x")
    assert main(["publish-check", "--repo", str(repo)]) == 1
    assert "PYTHONDONTWRITEBYTECODE" not in capsys.readouterr().out


# --- cannot-measure is never clean ---------------------------------------------------


def test_a_payload_matching_nothing_tracked_cannot_pass(tmp_path: Path) -> None:
    """A gate that scans nothing reports green forever. This one refuses to scan nothing."""
    market: dict[str, Any] = {
        "name": "fixture",
        "plugins": [{"name": "ghost", "source": "./plugins/ghost"}],
    }
    repo = _fixture_repo(tmp_path, claude=market)
    (repo / "plugins" / "ghost").mkdir(parents=True)

    with pytest.raises(publish.PublishCheckError, match="pass vacuously"):
        publish.check(repo)


def test_a_checkout_with_no_marketplace_manifest_cannot_pass(tmp_path: Path) -> None:
    repo = _fixture_repo(tmp_path)
    with pytest.raises(publish.PublishCheckError, match="not a checkout of the kit"):
        publish.check(repo)


def test_a_directory_that_is_not_a_work_tree_cannot_pass(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(publish.PublishCheckError):
        publish.check(plain)


def test_git_being_unavailable_cannot_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The failure mode that would matter most: no measurement must never read as clean."""
    repo = _both(tmp_path)

    def no_git(*_args: object, **_kwargs: object) -> object:
        raise OSError("git not found")

    # Patched on the shared `subprocess` module object, which `publish` imported too --
    # reaching through `publish.subprocess` would be a private re-export.
    monkeypatch.setattr(subprocess, "run", no_git)
    with pytest.raises(publish.PublishCheckError, match="nothing was verified"):
        publish.check(repo)


def test_an_unreadable_marketplace_is_not_silently_skipped(tmp_path: Path) -> None:
    """Under-scoping the payload to whatever the other manifest listed is the same defect."""
    repo = _both(tmp_path)
    (repo / ".agents" / "plugins" / "marketplace.json").write_text(
        "{not json", encoding="utf-8"
    )
    with pytest.raises(publish.PublishCheckError, match="could not be read"):
        publish.payload_roots(repo)


def test_cannot_measure_exits_two_not_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 2 is the whole point: a publish script gating on `!= 0` must not proceed."""
    repo = _fixture_repo(tmp_path)
    assert main(["publish-check", "--repo", str(repo)]) == 2
    assert "error:" in capsys.readouterr().out


def test_a_missing_repo_directory_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["publish-check", "--repo", "/nonexistent/not-here"]) == 2
    assert "not a directory" in capsys.readouterr().out


# --- payload derivation ---------------------------------------------------------------


def test_a_root_source_subsumes_the_pack_paths(tmp_path: Path) -> None:
    """`./` means the whole repo ships; keeping the pack paths too would double-count."""
    market: dict[str, Any] = {
        "name": "fixture",
        "plugins": [
            {"name": "whole", "source": "./"},
            {"name": "part", "source": "./plugins/core"},
        ],
    }
    repo = _fixture_repo(tmp_path, claude=market)
    assert publish.payload_roots(repo) == (".",)


def test_a_source_escaping_the_repository_is_refused(tmp_path: Path) -> None:
    market: dict[str, Any] = {
        "name": "fixture",
        "plugins": [{"name": "escapee", "source": "../elsewhere"}],
    }
    repo = _fixture_repo(tmp_path, claude=market)
    with pytest.raises(publish.PublishCheckError, match="escapes the repository"):
        publish.payload_roots(repo)


def test_a_manifest_listing_no_sources_cannot_pass(tmp_path: Path) -> None:
    market: dict[str, Any] = {"name": "fixture", "plugins": []}
    repo = _fixture_repo(tmp_path, claude=market)
    with pytest.raises(publish.PublishCheckError, match="payload is unknown"):
        publish.payload_roots(repo)


def test_checkout_root_walks_up_to_the_git_directory(tmp_path: Path) -> None:
    repo = _both(tmp_path)
    nested = repo / "plugins" / "core" / "skills"
    assert publish.checkout_root(nested) == repo.resolve()


def test_checkout_root_outside_a_checkout_raises(tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    with pytest.raises(publish.PublishCheckError, match="not inside a git checkout"):
        publish.checkout_root(outside)


# --- this repository -------------------------------------------------------------------


def test_this_checkout_is_measurable() -> None:
    """Pins the guard against the REAL layout -- but asserts nothing about cleanliness.

    Several sessions write this tree, and CI's own pytest run leaves `__pycache__` under
    `plugins/core/src/`, so both the working-tree and the ignored probe are legitimately
    non-empty here. What must hold is that the payload resolves from the manifests that
    actually ship and that the probes have something real to look at.
    """
    report = publish.check(_REPO_ROOT)

    assert report.payload == ("plugins/core", "plugins/python")
    assert report.tracked > 50, (
        f"only {report.tracked} tracked file(s) under the payload -- the pathspec is "
        "probably wrong, which would make the untracked and ignored probes vacuous"
    )
    assert len(report.results) == 3
    assert {r.probe.label for r in report.results} == {
        "working tree",
        "untracked in the payload",
        "gitignored in the payload",
    }


def test_the_payload_matches_what_the_marketplaces_declare() -> None:
    """Derived, not written down: adding a pack must not need an edit here.

    `test_plugin.py` pins both manifests to `./plugins/<pack>` for every pack in `PACKS`;
    this asserts the guard reads that same set, so a pack added there comes under the
    guard by that fact alone.
    """
    assert publish.payload_roots(_REPO_ROOT) == tuple(
        sorted(f"plugins/{pack}" for pack in PACKS)
    )


# --- decoding -------------------------------------------------------------------------
#
# The separators and the replacement character are built with `bytes([...])` and `chr()`
# rather than written as escapes. Not style: an earlier draft of this file was authored
# through a shell, which ate one level of backslash and put a real NUL into the source.
# These forms have no escape to lose.

_NUL = bytes([0])
_REPLACEMENT = chr(0xFFFD)


def test_a_mis_encoded_path_is_reported_not_fatal() -> None:
    """Decoding is `errors="replace"`, so an undecodable filename still blocks.

    The count is what blocks, and a lossy name still identifies the file. A guard that
    raised here would be a guard that fails open at exactly the wrong moment.
    """
    raw = b"a.md" + _NUL + bytes([0xFF, 0xFE]) + b".md" + _NUL
    assert publish._records(raw) == (  # pyright: ignore[reportPrivateUsage]
        "a.md",
        _REPLACEMENT * 2 + ".md",
    )
    assert publish._records(b"") == ()  # pyright: ignore[reportPrivateUsage]
    # Trailing and repeated separators must not become empty findings: one blank entry
    # would block a publish with a path nobody can act on.
    assert publish._records(_NUL * 3) == ()  # pyright: ignore[reportPrivateUsage]


def test_a_non_ascii_payload_filename_blocks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end, on the console this program has already been burned by twice."""
    repo = _both(tmp_path)
    _write(repo / "plugins" / "core" / "skills" / "demo" / "über.md", "wip\n")

    assert main(["publish-check", "--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "untracked in the payload (1)" in out
    # Printed through `ascii_safe`, so the name degrades rather than the run being lost.
    assert out.isascii()
