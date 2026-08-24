"""CLI surface: exit codes and human-readable output."""

import json
import re
import shutil
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest

from lemmi_ai_kit import checks, cli, publish
from lemmi_ai_kit.cli import main
from lemmi_ai_kit.manifest import load_manifest


def test_list_prints_full_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "commit-message" in out
    assert "analyze-logs" in out
    assert "kit-setup" in out
    # Derived, not literal: the CLI's own count must agree with the manifest it renders.
    expected = len(load_manifest().skills)
    assert f"{expected} skill(s)" in out


def test_scaffold_and_rerun_roundtrip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scaffold", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "seeded: " in out
    assert (tmp_path / "AGENTS.md").is_file()
    assert not (tmp_path / ".claude").exists()

    # a second run is a no-op, not an error
    assert main(["scaffold", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "seeded: 0" in out


def test_scaffold_rejects_missing_target(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["scaffold", "/nonexistent/definitely-not-here"]) == 2
    assert "not a directory" in capsys.readouterr().out


# --- audit-skills: the gate must never pass by scanning nothing --------------------
#
# This repo has no `.claude/skills/`, so `audit-skills --fail-on major` used to print
# "nothing to audit" and exit 0 -- a gate that cannot fail, which is worse than no gate
# because it gets trusted. The three tests below pin both directions of the fallback.

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NOTHING_TO_AUDIT = "nothing to audit"


def test_audit_skills_falls_back_to_the_bundled_fleet(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no .claude/skills/, auditing this repo must still scan the shipped fleet."""
    exit_code = main(["audit-skills", "--project", str(_REPO_ROOT)])
    out = capsys.readouterr().out

    assert _NOTHING_TO_AUDIT not in out, (
        "the audit scanned nothing, so --fail-on cannot fail:\n" + out
    )
    # Derived, not literal: adding or dropping a skill must not need an edit here.
    manifest = load_manifest()
    for pack in ("core", "python"):
        expected = sum(1 for entry in manifest.skills if entry.pack == pack)
        assert f"{expected} skills;" in out
    assert exit_code == 0


def test_audit_skills_does_not_hijack_an_adopter_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An adopter with only plugin skills keeps the note -- we must not audit OUR fleet."""
    exit_code = main(["audit-skills", "--project", str(tmp_path)])
    out = capsys.readouterr().out

    assert _NOTHING_TO_AUDIT in out
    # The fleet's own INFO line would appear if we had silently changed target.
    assert "skills; description+when_to_use" not in out
    assert exit_code == 0


def test_audit_skills_without_the_fallback_would_scan_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The regression this guards: disable the fallback and the gate goes vacuous again."""

    def no_bundled_tree(_root: Path) -> tuple[Path, ...]:
        return ()

    monkeypatch.setattr(cli, "_bundled_skills_dirs", no_bundled_tree)

    exit_code = main(
        ["audit-skills", "--project", str(_REPO_ROOT), "--fail-on", "major"]
    )
    out = capsys.readouterr().out

    assert _NOTHING_TO_AUDIT in out
    assert exit_code == 0, "a vacuous scan exits 0 -- which is exactly the defect"


# --- `new-pack` -----------------------------------------------------------------------
#
# The acceptance test for D15 is a ROUND TRIP: generate a pack, then hold it to the same
# contract `tests/test_plugin.py` applies to `core` and `python`. Those assertions are
# restated here rather than imported, because that module reads a module-level
# `_REPO_ROOT` and cannot be pointed at a generated tree -- so each block below cites the
# test it mirrors, and the citation is what keeps the two from drifting apart silently.
#
# Every fixture copies the REAL `plugins/_template`, never a hand-written stand-in. A
# fixture template would let the shipped one rot while these stayed green, which is the
# failure this file exists to prevent, not to have.

_TEMPLATE = _REPO_ROOT / cli.PACK_TEMPLATE
_PLUGIN_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def _fixture_checkout(root: Path) -> Path:
    """A throwaway checkout holding exactly what `new-pack` reads."""
    shutil.copytree(_TEMPLATE, root / cli.PACK_TEMPLATE)
    shutil.copy2(_REPO_ROOT / "pyproject.toml", root / "pyproject.toml")
    for relative in publish.MARKETPLACE_MANIFESTS:
        source = _REPO_ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return root


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _project(repo: Path) -> dict[str, Any]:
    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    return cast(dict[str, Any], tomllib.loads(text)["project"])


def test_new_pack_round_trip_produces_a_pack_the_plugin_contract_accepts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The discriminator for this command: does what it writes pass the pack contract?"""
    repo = _fixture_checkout(tmp_path)
    assert (
        main(["new-pack", "demo", "--skill", "demo-conventions", "--repo", str(repo)])
        == 0
    )
    capsys.readouterr()

    pack_root = repo / "plugins" / "demo"
    claude = _json(pack_root / ".claude-plugin" / "plugin.json")
    codex = _json(pack_root / ".codex-plugin" / "plugin.json")
    project = _project(repo)

    # test_plugin.py::_assert_plugin_identity, plus the license claim that
    # test_license.py::test_every_license_declaration_matches_the_license_file makes.
    for host, data in (("claude", claude), ("codex", codex)):
        assert data["name"] == "lemmi-ai-kit-demo", host
        assert _PLUGIN_NAME_RE.fullmatch(cast(str, data["name"])), host
        assert data["version"] == project["version"], host
        assert data["repository"] == project["urls"]["Repository"], host
        assert data["license"] == project["license"], host

    # test_plugin.py::test_claude_and_codex_pack_manifests_share_identity_and_skills
    assert claude["name"] == codex["name"]
    assert claude["version"] == codex["version"]
    assert claude["repository"] == codex["repository"]
    assert cast(list[str], claude["skills"]) == [codex["skills"]]

    # test_plugin.py::_assert_skills_path_resolves
    for rel in cast(list[str], claude["skills"]):
        assert rel.startswith("./")
        assert ".." not in rel
        skills = pack_root / rel
        assert skills.is_dir(), f"plugin skills path missing: {rel}"
        assert (skills / "demo-conventions").is_dir()

    # test_plugin.py::test_pack_plugin_json_paths_resolve, the Codex half
    interface = cast(dict[str, Any], codex["interface"])
    assert interface["displayName"]
    assert interface["category"]

    # test_assets.py::test_every_skill_has_valid_frontmatter
    text = (pack_root / "skills" / "demo-conventions" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    block = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert block, "generated SKILL.md has no frontmatter"
    assert re.search(r"^name:\s*demo-conventions\s*$", block.group(1), re.MULTILINE)
    assert re.search(r"^description:", block.group(1), re.MULTILINE)

    # Nothing unsubstituted anywhere in the tree. A literal `{{KEY}}` in a plugin.json
    # is what a marketplace would render, and no other assertion here would see it.
    for path in sorted(p for p in pack_root.rglob("*") if p.is_file()):
        assert "{{" not in path.read_text(encoding="utf-8"), (
            f"{path.relative_to(pack_root).as_posix()} still holds a placeholder"
        )


def test_the_generated_pack_passes_the_audit_that_gates_this_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`audit-skills --fail-on major` runs over every pack, so a template that seeds a
    finding would break the gate for whoever authors from it -- one commit later, in
    somebody else's diff."""
    repo = _fixture_checkout(tmp_path)
    assert main(["new-pack", "demo", "--repo", str(repo)]) == 0
    capsys.readouterr()

    findings = checks.audit_skills(repo / "plugins" / "demo" / "skills")
    blocking = [f for f in findings if f.severity in ("BLOCKER", "MAJOR")]
    assert not blocking, "generated pack fails the fleet audit:\n" + "\n".join(
        f"  {f.severity} {f.skill}: {f.message}" for f in blocking
    )


def test_new_pack_names_every_registration_chokepoint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The command registers nothing, so the checklist IS the deliverable.

    Both marketplace paths are asserted from `publish.MARKETPLACE_MANIFESTS` rather than
    written out: a manifest added there must appear in this output without anyone
    remembering to edit the checklist.
    """
    repo = _fixture_checkout(tmp_path)
    assert main(["new-pack", "demo", "--repo", str(repo)]) == 0
    out = capsys.readouterr().out

    for relative in publish.MARKETPLACE_MANIFESTS:
        assert relative in out
    assert "manifest.py" in out
    assert "manifest.toml" in out
    assert "docs/upstream-sync.toml" in out
    assert "README.md" in out
    assert "docs/authoring-a-pack.md" in out

    # ...and it must not have edited any of them.
    for relative in publish.MARKETPLACE_MANIFESTS:
        assert (repo / relative).read_bytes() == (_REPO_ROOT / relative).read_bytes()


def test_new_pack_dry_run_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _fixture_checkout(tmp_path)
    assert main(["new-pack", "demo", "--repo", str(repo), "--dry-run"]) == 0
    out = capsys.readouterr().out

    assert "[dry-run]" in out
    assert "plugins/demo/.claude-plugin/plugin.json" in out
    assert not (repo / "plugins" / "demo").exists()


def test_new_pack_refuses_to_write_over_an_existing_pack(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _fixture_checkout(tmp_path)
    (repo / "plugins" / "demo" / "skills").mkdir(parents=True)
    marker = repo / "plugins" / "demo" / "skills" / "keep-me.md"
    marker.write_text("mine\n", encoding="utf-8")

    assert main(["new-pack", "demo", "--repo", str(repo)]) == 2
    assert "already exists" in capsys.readouterr().out
    assert marker.read_text(encoding="utf-8") == "mine\n"


# The tail is parametrized rather than the whole argv, because `--repo` has to come
# BEFORE the `--` that lets a leading-hyphen name reach the validator at all. Passed the
# other way round argparse claims it as an option and the case never reaches the code
# under test -- which is how it first passed for the wrong reason.
@pytest.mark.parametrize(
    "tail",
    [
        ["Demo"],
        ["demo_pack"],
        ["demo.pack"],
        ["--", "-demo"],
        ["demo", "--skill", "Demo_Skill"],
        ["demo", "--plugin-name", "Lemmi_Demo"],
    ],
    ids=["uppercase", "underscore", "dot", "leading-hyphen", "skill", "plugin-name"],
)
def test_new_pack_rejects_names_the_suite_would_reject_later(
    tail: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Refused at the argument, not at test time: the later failure names the generated
    manifest, which is two steps from the typo that caused it."""
    repo = _fixture_checkout(tmp_path)
    assert main(["new-pack", "--repo", str(repo), *tail]) == 2
    assert "must match" in capsys.readouterr().out
    # The template is the only thing that was ever under `plugins/` here, so anything
    # else means the refusal came after a write rather than before one.
    assert [p.name for p in (repo / "plugins").iterdir()] == ["_template"]


def test_new_pack_needs_a_checkout_with_the_template(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An adopter's project is not a place this command can work, and must say so."""
    assert main(["new-pack", "demo", "--repo", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert cli.PACK_TEMPLATE in out
    assert "checkout of the kit" in out


def test_the_placeholder_guard_refuses_an_unfilled_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Positive control: a guard nobody has watched refuse is an assumption.

    Also pins render-before-write. The refusal must leave NO pack on disk -- a
    half-written one is worse than none, because the retry then trips the
    already-exists refusal and the author is stuck between two errors.
    """
    repo = _fixture_checkout(tmp_path)
    skill_md = (
        repo
        / cli.PACK_TEMPLATE
        / "skills"
        / cli._TEMPLATE_SKILL_DIR  # pyright: ignore[reportPrivateUsage]
        / "SKILL.md"
    )
    skill_md.write_text(
        skill_md.read_text(encoding="utf-8") + "\n{{NOT_A_REAL_KEY}}\n",
        encoding="utf-8",
    )

    assert main(["new-pack", "demo", "--repo", str(repo)]) == 2
    out = capsys.readouterr().out
    assert "NOT_A_REAL_KEY" in out
    assert not (repo / "plugins" / "demo").exists(), (
        "the refusal left a partial pack behind"
    )


def test_a_template_that_cannot_produce_a_valid_pack_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Positive control for the template guard: break the skeleton, not the argument.

    Without this the same breakage surfaces as a `test_plugin.py` failure naming the
    generated manifest -- which is the wrong file, in the wrong pack, one commit later.
    """
    repo = _fixture_checkout(tmp_path)
    (repo / cli.PACK_TEMPLATE / ".codex-plugin" / "plugin.json").unlink()

    assert main(["new-pack", "demo", "--repo", str(repo)]) == 2
    out = capsys.readouterr().out
    assert ".codex-plugin/plugin.json" in out
    assert not (repo / "plugins" / "demo").exists()


def test_the_shipped_template_is_the_one_the_round_trip_exercises() -> None:
    """Guard the guard: every fixture above copies `_TEMPLATE`, so if that path stopped
    resolving the copies would be empty and each round trip would pass vacuously."""
    assert _TEMPLATE.is_dir(), f"{cli.PACK_TEMPLATE} is missing"
    files = sorted(
        p.relative_to(_TEMPLATE).as_posix() for p in _TEMPLATE.rglob("*") if p.is_file()
    )
    assert ".claude-plugin/plugin.json" in files
    assert ".codex-plugin/plugin.json" in files
    assert f"skills/{cli._TEMPLATE_SKILL_DIR}/SKILL.md" in files  # pyright: ignore[reportPrivateUsage]


def test_the_template_is_invisible_to_every_pack_enumeration() -> None:
    """The trap this layout was chosen to avoid: `load_manifest()` raises on a skill
    directory under a pack with no manifest entry, and the template ships one. It is
    safe only because every enumeration iterates the `PACKS` literal rather than globbing
    `plugins/*` -- an invariant with no other test, and one a single `glob` would end."""
    from lemmi_ai_kit.manifest import PACKS, available_packs, shipped_skill_dirs

    assert "_template" not in PACKS
    assert "_template" not in available_packs()
    shipped = shipped_skill_dirs()
    assert cli._TEMPLATE_SKILL_DIR not in shipped  # pyright: ignore[reportPrivateUsage]
    assert not any("_template" in path.parts for path in shipped.values())
    # And the manifest still loads, which is the assertion that would have gone red.
    assert load_manifest().skills
