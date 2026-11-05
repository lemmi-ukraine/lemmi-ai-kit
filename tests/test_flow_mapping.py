"""Exercise installed flow tools against independent consumer projects."""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import load_manifest, skill_dir


@pytest.fixture
def installation(tmp_path: Path) -> tuple[Path, Path]:
    entry = next(s for s in load_manifest().skills if s.name == "flow-mapping")
    source = skill_dir(entry)
    installed = tmp_path / "plugin cache/core/skills/flow-mapping"
    shutil.copytree(source, installed)
    checker = source.parent / "post-task-review/scripts/probe_checker.py"
    destination = installed.parent / "post-task-review/scripts/probe_checker.py"
    destination.parent.mkdir(parents=True)
    shutil.copy2(checker, destination)
    project = tmp_path / "separate consumer"
    shutil.copytree(installed / "assets/probe-project", project)
    return installed, project


# Both limits guard against a hang, not against a slow machine. `--probe-stamps` is the one
# call whose duration scales with the tool's probe manifest: it runs every probe pair in a
# single call, on a positive and a negative file each, so it gets a limit in minutes while
# every other call keeps 45 s. At 4244f3c on a loaded Windows machine the two calls took
# between 45 s and 158 s from one run to the next, and a flat 45 s killed both in one run.
_CALL_TIMEOUT_SECONDS = 45
_PROBE_STAMPS_TIMEOUT_SECONDS = 10 * 60


def run(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    timeout = (
        _PROBE_STAMPS_TIMEOUT_SECONDS
        if "--probe-stamps" in args
        else _CALL_TIMEOUT_SECONDS
    )
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=cwd,
        env={
            key: value
            for key, value in os.environ.items()
            if key != "PYTHONDONTWRITEBYTECODE"
        },
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def hashes(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("tool", ["validate_flow_map", "validate_register"])
def test_installed_probe_pairs_need_no_source_repository(
    installation: tuple[Path, Path], tool: str
) -> None:
    installed, project = installation
    before = hashes(installed.parent)
    result = run(installed / f"scripts/{tool}.py", project, "--probe-stamps")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "exact probe pairs)" in result.stdout
    assert "verdict=CAN-SEE" in result.stdout
    if tool == "validate_flow_map":
        assert "probe_checker PASS - quantifiers" in result.stdout
    assert hashes(installed.parent) == before


@pytest.mark.parametrize("source_root", ["src", "lib"])
def test_consumer_resolution_corrupt_and_missing_inputs(
    installation: tuple[Path, Path],
    source_root: str,
) -> None:
    installed, project = installation
    tool = installed / "scripts/validate_flow_map.py"
    if source_root != "src":
        (project / "src").rename(project / source_root)
        for path in (project / "scripts/fixtures").rglob("*.md"):
            path.write_text(path.read_text().replace("src/", f"{source_root}/"))
    nested = project / "nested"
    nested.mkdir()
    fixture = "scripts/fixtures/flow_map/conformant.md"
    args = ("--project-root", str(project), "--code-root", source_root, fixture)
    valid = run(tool, nested, *args)
    assert (valid.returncode, valid.stdout) == (0, ""), valid.stderr
    doc = project / fixture
    text = doc.read_text()
    assert "IdlePolicy.evaluate" in text
    doc.write_text(text.replace("IdlePolicy.evaluate", "IdlePolicy.nonexistent"))
    invalid = run(tool, nested, *args)
    assert invalid.returncode == 1 and "does not resolve" in invalid.stdout
    doc.unlink()
    missing = run(tool, nested, *args)
    assert missing.returncode == 2 and "not found" in missing.stderr
    absent = run(tool, nested, "--project-root", str(project / "missing"), fixture)
    assert absent.returncode == 2 and "project root not found" in absent.stderr


def test_projection_certification_and_authorship_refusal(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/generate_flow_projections.py"
    prefix = ("--project-root", str(project), "--code-root", "src")
    good = run(
        tool,
        project,
        *prefix,
        "scripts/fixtures/flow_projection/conformant.md",
        "--certify",
    )
    assert good.returncode == 0, good.stdout + good.stderr
    bad = run(
        tool,
        project,
        *prefix,
        "scripts/fixtures/flow_projection/wrong-row.md",
        "--certify",
    )
    assert bad.returncode == 1, bad.stdout + bad.stderr
    unread = run(
        tool, project, *prefix, "scripts/fixtures/flow_projection/unread-file.md"
    )
    assert unread.returncode == 2, unread.stdout + unread.stderr


def test_seam_candidates_and_unreadable_corpus(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/find_absent_cross_flow_seams.py"
    result = run(
        tool,
        project,
        "--project-root",
        str(project),
        "--root",
        "scripts/fixtures/flow_map/seam_probe",
        "--list-residue",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = [line for line in result.stdout.splitlines() if line.startswith("RESIDUE  ")]
    assert any("ProbeAbsentSeam.sweep_only" in line for line in rows)
    assert not any("ProbeNamedInProse.cell_names_me" in line for line in rows)
    bad = run(tool, project, "--root", str(project / "missing"))
    assert bad.returncode != 0


def test_comment_checker_detects_executable_change_and_missing_file(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/verify_no_code_change.py"
    module = project / "mod.py"
    original = '"""Module docs."""\n\ndef f():\n    """Function docs."""\n    "original".upper()\n    return 1\n'
    module.write_text(original)
    for args in (
        ["init", "-q"],
        ["add", "--", "mod.py"],
        [
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Fixture",
        ],
    ):
        subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
    module.write_text(original.replace("Function docs.", "New documentation."))
    assert run(tool, project, "HEAD", "mod.py").returncode == 0
    module.write_text(original.replace("return 1", "return 2"))
    changed = run(tool, project, "HEAD", "mod.py")
    assert changed.returncode == 1 and "CODE-CHANGED" in changed.stdout
    module.write_text(original.replace('"original"', '"different"'))
    expression = run(tool, project, "HEAD", "mod.py")
    assert expression.returncode == 1 and "CODE-CHANGED" in expression.stdout
    missing = run(tool, project, "HEAD", "absent.py")
    assert missing.returncode == 1 and "MISSING-AT-REF" in missing.stdout


def test_register_join_refuses_missing_population(
    installation: tuple[Path, Path],
) -> None:
    installed, project = installation
    tool = installed / "scripts/validate_register.py"
    result = run(
        tool, project, "--project-root", str(project), "--join", "absent", "tasks"
    )
    assert result.returncode == 2 and "missing or empty" in result.stderr


# --- seam candidates need a disposition in a register --------------------------------------

_SEAM_ROOT = "scripts/fixtures/flow_map/seam_probe"
_SEAM_REGISTERS = "scripts/fixtures/flow_map/seam_probe_registers"
_DOC_A = "probe-seam-a.md"
_DOC_B = "probe-seam-b.md"
_SWEEP = "ProbeAbsentSeam.sweep_only"
_SPLIT = "ProbeVerdictSplit.fail_here_unknown_there"
_AGREE = "ProbeVerdictAgree.fail_here_pass_there"
_LINKED = "ProbeLinkedSplit.linked_fail_unknown"
_UNDISPOSED_PREFIX = "UNDISPOSED  "


def seam_run(
    installation: tuple[Path, Path], *args: str
) -> subprocess.CompletedProcess[str]:
    installed, project = installation
    return run(
        installed / "scripts/find_absent_cross_flow_seams.py",
        project,
        "--project-root",
        str(project),
        "--root",
        _SEAM_ROOT,
        *args,
    )


def undisposed_rows(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.startswith(_UNDISPOSED_PREFIX)]


def test_seam_registers_flag_lists_only_the_undisposed_candidate(
    installation: tuple[Path, Path],
) -> None:
    result = seam_run(installation, "--registers", _SEAM_REGISTERS)
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "4 candidates, 1 without a disposition" in result.stdout, out
    rows = undisposed_rows(result.stdout)
    assert len(rows) == 1 and _AGREE in rows[0], out
    assert _DOC_A in rows[0] and _DOC_B in rows[0], out


_BASE_BULLETS = (
    f"- **Residue verdict:** shared-entry-no-seam — `{_SWEEP}` in `{_DOC_A}` and `{_DOC_B}`\n"
    f"- **Verdict ownership:** `{_DOC_B}` owns `{_SPLIT}` against `{_DOC_A}`\n"
    f"- **Verdict ownership:** `{_DOC_A}` owns `{_LINKED}` against `{_DOC_B}`\n"
)

# (case, the one bullet written for the third candidate, whether it disposes of it)
_BULLET_CASES: list[tuple[str, str, bool]] = [
    (
        "residue marker with the full symbol and both documents",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        True,
    ),
    (
        "ownership marker with the full symbol and both documents",
        f"- **Verdict ownership:** `{_DOC_A}` owns `{_AGREE}`; `{_DOC_B}` agrees",
        True,
    ),
    (
        "documents named by path",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `docs/flows/{_DOC_A}` and `docs/flows/{_DOC_B}`",
        True,
    ),
    (
        "bullet wrapped over two lines",
        f"- **Residue verdict:** seamed-at-row-level — `{_DOC_A}` and\n  `{_DOC_B}` share `{_AGREE}`",
        True,
    ),
    (
        "one document only",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}`",
        False,
    ),
    (
        "no disposition marker",
        f"- **Reconciled against:** `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "bare suffix instead of the full symbol",
        f"- **Residue verdict:** seamed-at-row-level — fail_here_pass_there in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "a longer symbol that starts with the candidate",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}_extra` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "a document whose name only ends the same",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `old-{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "marker in a paragraph that is not a bullet",
        f"**Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    # The edges the matcher documents, one near miss each: how a symbol and a document name
    # may be bounded, where a bullet ends, and the exact spelling of the marker.
    (
        "a symbol qualified by an outer name",
        f"- **Residue verdict:** seamed-at-row-level — `Outer.{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "a symbol that ends a longer name",
        f"- **Residue verdict:** seamed-at-row-level — `Old{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "a longer dotted symbol that starts with the candidate",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}.nested` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "a document name followed by a hyphen",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}-old` and `{_DOC_B}`",
        False,
    ),
    (
        "a document name followed by a word character",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}x` and `{_DOC_B}`",
        False,
    ),
    (
        "a document name glued to a word before it",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `x{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "a document name after a dotted prefix",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `v2.{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "the second document named after a blank line",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}`\n\n  and `{_DOC_B}` in a following paragraph",
        False,
    ),
    (
        "the second document named in a heading right after the bullet",
        f"- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}`\n### {_DOC_B}",
        False,
    ),
    (
        "marker with the colon outside the bold",
        f"- **Residue verdict**: seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "marker with no colon",
        f"- **Residue verdict** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "marker not in bold",
        f"- Residue verdict: seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "marker in italics",
        f"- *Residue verdict:* seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "marker on a numbered item",
        f"1. **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
    (
        "marker in lower case",
        f"- **residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`",
        False,
    ),
]


@pytest.mark.parametrize(
    ("bullet", "disposed"),
    [pytest.param(b, d, id=case) for case, b, d in _BULLET_CASES],
)
def test_a_register_bullet_disposes_a_candidate_only_when_it_names_everything(
    installation: tuple[Path, Path], bullet: str, disposed: bool
) -> None:
    _installed, project = installation
    registers = project / "case-registers"
    registers.mkdir()
    (registers / "BUG-register-flow-case.md").write_text(
        f"### R-case-01 · the other two candidates\n{_BASE_BULLETS}\n"
        f"### R-case-02 · the third candidate\n{bullet}\n",
        encoding="utf-8",
    )
    result = seam_run(installation, "--registers", "case-registers")
    out = result.stdout + result.stderr
    if disposed:
        assert result.returncode == 0, out
        assert "4 candidates, 0 without a disposition" in result.stdout, out
        assert undisposed_rows(result.stdout) == [], out
    else:
        assert result.returncode == 1, out
        assert "4 candidates, 1 without a disposition" in result.stdout, out
        rows = undisposed_rows(result.stdout)
        assert len(rows) == 1 and _AGREE in rows[0], out


def test_seam_registers_flag_refuses_a_missing_or_empty_directory(
    installation: tuple[Path, Path],
) -> None:
    _installed, project = installation
    missing = seam_run(installation, "--registers", "no-such-registers")
    assert missing.returncode == 3, missing.stdout + missing.stderr
    assert "--registers" in missing.stdout, missing.stdout
    (project / "empty-registers").mkdir()
    empty = seam_run(installation, "--registers", "empty-registers")
    assert empty.returncode == 3, empty.stdout + empty.stderr
    assert "--registers" in empty.stdout, empty.stdout
    assert undisposed_rows(empty.stdout) == [], "an unreadable directory lists nothing"


def test_seam_registers_flag_refuses_a_register_that_cannot_be_decoded(
    installation: tuple[Path, Path],
) -> None:
    _installed, project = installation
    registers = project / "case-registers"
    shutil.copytree(project / _SEAM_REGISTERS, registers)
    (registers / "BUG-register-flow-bad-bytes.md").write_bytes(
        b"### R-bad-01 \xff\xfe not text\n"
    )
    result = seam_run(installation, "--registers", "case-registers")
    out = result.stdout + result.stderr
    assert result.returncode == 3, out
    assert "BUG-register-flow-bad-bytes.md cannot be read" in result.stdout, out
    assert undisposed_rows(result.stdout) == [], "an unreadable register lists nothing"


def test_registers_are_read_from_the_project_root_before_the_working_directory(
    installation: tuple[Path, Path], tmp_path: Path
) -> None:
    installed, project = installation
    own = sorted((project / _SEAM_REGISTERS).glob("*.md"))
    assert len(own) == 2, "the project's own registers are the two seam registers"
    for register in own:
        shutil.copy2(register, project / "tasks" / register.name)
    own_files = len(list((project / "tasks").glob("*.md")))
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "tasks").mkdir(parents=True)
    (elsewhere / "tasks" / "BUG-register-flow-decoy.md").write_text(
        "### R-decoy-01 · a register of another project\n- **Class:** risk\n",
        encoding="utf-8",
    )
    shutil.copytree(project / _SEAM_REGISTERS, elsewhere / "registers-kept-here")

    def read_from(raw: str) -> subprocess.CompletedProcess[str]:
        return run(
            installed / "scripts/find_absent_cross_flow_seams.py",
            elsewhere,
            "--project-root",
            str(project),
            "--root",
            _SEAM_ROOT,
            "--registers",
            raw,
        )

    shadowed = read_from("tasks")
    out = shadowed.stdout + shadowed.stderr
    assert f"registers read: {own_files} file(s)" in shadowed.stdout, out
    assert "4 candidates, 1 without a disposition" in shadowed.stdout, out
    assert shadowed.returncode == 1, out

    fallback = read_from("registers-kept-here")
    assert "registers read: 2 file(s)" in fallback.stdout, fallback.stdout
    assert "4 candidates, 1 without a disposition" in fallback.stdout, fallback.stdout


def test_a_linked_verdict_split_is_a_candidate_for_that_reason_alone(
    installation: tuple[Path, Path],
) -> None:
    _installed, project = installation
    registers = project / "case-registers"
    registers.mkdir()
    (registers / "BUG-register-flow-case.md").write_text(
        "### R-case-01 · every candidate but the linked split\n"
        + "\n".join(_BASE_BULLETS.splitlines()[:2])
        + f"\n- **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` and `{_DOC_B}`\n",
        encoding="utf-8",
    )
    result = seam_run(installation, "--registers", "case-registers", "--list-residue")
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "4 candidates, 1 without a disposition" in result.stdout, out
    rows = undisposed_rows(result.stdout)
    assert len(rows) == 1 and _LINKED in rows[0], out
    assert rows[0].endswith("(verdict-disagreement)"), rows[0]
    residue = [
        line for line in result.stdout.splitlines() if line.startswith("RESIDUE  ")
    ]
    assert residue and not any(_LINKED in line for line in residue), (
        "a pair linked by a cross-flow row has no absent seam to list"
    )


_PROBE_FIXTURES = "assets/probe-project/scripts/fixtures/flow_map"
_ARM_HEADERS = {
    "residue": "known-POSITIVE (disposition, residue marker)",
    "ownership": "known-POSITIVE (disposition, ownership marker)",
    "negative": "known-NEGATIVE (disposition)",
    "kind": "known-POSITIVE (candidate kind, disagreement only)",
}
_PASS = "PASS"
_BLIND = "FAIL (disposition matcher blind)"
_OVER_MATCHING = "FAIL (disposition matcher over-matching)"
_KIND_BLIND = "FAIL (candidate list blind to a linked verdict disagreement)"
_ALL_PASS = dict.fromkeys(_ARM_HEADERS, _PASS)


def probe_arms(stdout: str) -> dict[str, str]:
    """What each disposition arm of the probe block says: {arm: the words after its arrow}."""
    lines = stdout.splitlines()
    arms: dict[str, str] = {}
    for arm, header in _ARM_HEADERS.items():
        starts = [i for i, line in enumerate(lines) if line.strip().startswith(header)]
        assert len(starts) == 1, f"{header!r} is printed {len(starts)} times:\n{stdout}"
        verdict_line = lines[starts[0] + 1]
        assert "->" in verdict_line, f"no verdict after {header!r}: {verdict_line!r}"
        arms[arm] = verdict_line.rsplit("->", 1)[1].strip()
    return arms


def test_seam_detector_certifies_the_disposition_matcher(
    installation: tuple[Path, Path],
) -> None:
    certified = seam_run(installation)
    assert certified.returncode == 0, certified.stdout + certified.stderr
    assert probe_arms(certified.stdout) == _ALL_PASS, certified.stdout
    assert "DETECTOR CERTIFIED" in certified.stdout


# (a file under the probe fixtures, the one text in it to replace, its replacement, and what
# each arm must then say). Every defect leaves the other arms green, so each arm is shown to
# fail on its own.
_PLANTED_DEFECTS = [
    pytest.param(
        "seam_probe_registers/BUG-register-flow-probe-seam-a.md",
        "- **Residue verdict:** shared-entry-no-seam",
        "- **Notes:** shared-entry-no-seam",
        {**_ALL_PASS, "residue": _BLIND},
        id="residue-bullet-loses-its-marker",
    ),
    pytest.param(
        "seam_probe_registers/BUG-register-flow-probe-seam-b.md",
        f"- **Verdict ownership:** `{_DOC_B}` owns the verdict for",
        f"- **Notes:** `{_DOC_B}` owns the verdict for",
        {**_ALL_PASS, "ownership": _BLIND},
        id="ownership-bullet-loses-its-marker",
    ),
    pytest.param(
        "seam_probe_registers/BUG-register-flow-probe-seam-a.md",
        "with no second document named.",
        f"and `{_DOC_B}`.",
        {**_ALL_PASS, "negative": _OVER_MATCHING},
        id="near-miss-gains-the-second-document",
    ),
    pytest.param(
        "seam_probe/probe-seam-b.md",
        f"| `{_LINKED}` | UNKNOWN |",
        f"| `{_LINKED}` | FAIL |",
        {**_ALL_PASS, "kind": _KIND_BLIND},
        id="linked-split-stops-being-a-disagreement",
    ),
]


@pytest.mark.parametrize(("fixture", "old", "new", "arms"), _PLANTED_DEFECTS)
def test_seam_detector_refuses_when_one_probe_arm_goes_blind(
    installation: tuple[Path, Path],
    fixture: str,
    old: str,
    new: str,
    arms: dict[str, str],
) -> None:
    installed, _project = installation
    target = installed / _PROBE_FIXTURES / fixture
    text = target.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"the planted defect needs one {old!r} in {fixture}"
    target.write_text(text.replace(old, new), encoding="utf-8")
    result = seam_run(installation)
    out = result.stdout + result.stderr
    assert result.returncode == 2, out
    assert "DETECTOR NOT CERTIFIED" in result.stdout, out
    assert probe_arms(result.stdout) == arms, out


def test_seam_detector_refuses_when_the_probe_registers_are_missing(
    installation: tuple[Path, Path],
) -> None:
    installed, _project = installation
    shutil.rmtree(installed / _PROBE_FIXTURES / "seam_probe_registers")
    absent = seam_run(installation)
    assert absent.returncode == 2, absent.stdout + absent.stderr
    assert "PROBE INCONCLUSIVE" in absent.stdout, absent.stdout


# --- universal words in a claim need an enumeration or a narrower word ----------------------

_QUANTIFIER_FIXTURE = "scripts/fixtures/flow_map/probe-quantifiers.md"
_FLAGGED_ROWS: tuple[tuple[str, str], ...] = (
    ("a scenario row", "| CF-03 | alternative"),
    ("an expansion row", "| 1 | `IdlePolicy.evaluate` |"),
    ("an invariant row", "| INV-01 |"),
)
_SKIPPED_ROWS: tuple[tuple[str, str], ...] = (
    ("a row with a hyphenated name", "| CF-01 | main"),
    ("a row with a backticked value", "| CF-02 | edge"),
)
_FINDING = re.compile(r"^\[(?P<check>\w+)\] \S+:(?P<line>\d+): (?P<message>.*)$")


def validate_run(
    installation: tuple[Path, Path], document: str, *args: str
) -> subprocess.CompletedProcess[str]:
    installed, project = installation
    return run(
        installed / "scripts/validate_flow_map.py",
        project,
        "--project-root",
        str(project),
        "--code-root",
        "src",
        document,
        *args,
    )


def line_of(document: Path, prefix: str) -> int:
    """The 1-based line of the first line that starts with `prefix`, or a loud failure."""
    for number, line in enumerate(
        document.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line.startswith(prefix):
            return number
    raise AssertionError(f"{document.name} has no line starting {prefix!r}")


def findings(stdout: str) -> dict[int, tuple[str, str]]:
    """Every finding line as {line number: (check, message)}."""
    found: dict[int, tuple[str, str]] = {}
    for line in stdout.splitlines():
        match = _FINDING.match(line)
        assert match is not None, f"not a finding line: {line!r}"
        found[int(match.group("line"))] = (match.group("check"), match.group("message"))
    return found


def test_quantifiers_check_flags_universal_words_beside_a_partly_read_file(
    installation: tuple[Path, Path],
) -> None:
    _installed, project = installation
    document = project / _QUANTIFIER_FIXTURE
    result = validate_run(installation, _QUANTIFIER_FIXTURE, "--check", "quantifiers")
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    found = findings(result.stdout)
    flagged = {line_of(document, prefix): label for label, prefix in _FLAGGED_ROWS}
    assert set(found) == set(flagged), out
    assert {check for check, _ in found.values()} == {"quantifiers"}
    words = ("'only'", "'never'", "'every'")
    for number, word in zip(sorted(flagged), words, strict=True):
        assert word in found[number][1], out
    for label, prefix in _SKIPPED_ROWS:
        assert line_of(document, prefix) not in found, f"{label} was flagged:\n{out}"


def test_quantifiers_findings_are_printed_by_the_default_run_without_failing_it(
    installation: tuple[Path, Path],
) -> None:
    result = validate_run(installation, _QUANTIFIER_FIXTURE)
    out = result.stdout + result.stderr
    assert result.returncode == 0, out
    found = findings(result.stdout)
    assert {check for check, _ in found.values()} == {"quantifiers"}
    assert len(found) == 3, out


def test_a_blocking_finding_still_fails_the_default_run_beside_quantifier_findings(
    installation: tuple[Path, Path],
) -> None:
    _installed, project = installation
    source = project / _QUANTIFIER_FIXTURE
    edited = source.with_name("probe-quantifiers-blocking.md")
    edited.write_text(
        source.read_text(encoding="utf-8")
        + "\n## Notes\n\nA section the schema does not list.\n",
        encoding="utf-8",
    )
    result = validate_run(installation, f"{_QUANTIFIER_FIXTURE[:-3]}-blocking.md")
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    checks = sorted(check for check, _ in findings(result.stdout).values())
    assert checks == ["quantifiers"] * 3 + ["sections"], out


@pytest.mark.parametrize(
    ("case", "edits"),
    [
        pytest.param(
            "the cited file's note starts with read in full",
            (
                (
                    "| all indexed symbols, call sites, and evidence live in this fixture file |",
                    "| read in full; all indexed symbols, call sites, and evidence live in this fixture file |",
                ),
            ),
            id="note-starts-with-read-in-full",
        ),
        pytest.param(
            "each universal word is narrowed",
            (
                ("holds the only path", "holds the reset path"),
                ("delivery never reaches", "delivery fails to reach"),
                ("every concurrent mutation", "a concurrent mutation"),
            ),
            id="words-narrowed",
        ),
    ],
)
def test_quantifiers_check_passes_once_the_note_or_the_words_change(
    installation: tuple[Path, Path],
    case: str,
    edits: tuple[tuple[str, str], ...],
) -> None:
    _installed, project = installation
    source = project / _QUANTIFIER_FIXTURE
    text = source.read_text(encoding="utf-8")
    for old, new in edits:
        assert old in text, f"{case}: the edit needs {old!r} in the fixture"
        text = text.replace(old, new)
    edited = source.with_name("probe-quantifiers-edited.md")
    edited.write_text(text, encoding="utf-8")
    result = validate_run(
        installation, f"{_QUANTIFIER_FIXTURE[:-3]}-edited.md", "--check", "quantifiers"
    )
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


def test_quantifiers_check_leaves_the_conformant_fixture_clean(
    installation: tuple[Path, Path],
) -> None:
    result = validate_run(
        installation,
        "scripts/fixtures/flow_map/conformant.md",
        "--check",
        "quantifiers",
    )
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


_NOTE = "| all indexed symbols, call sites, and evidence live in this fixture file |"
_CF01_EVIDENCE = "`code: src/policy.py resets state when eligibility fails`"
_BASELINE_FLAGGED = (
    "| CF-03 | alternative",
    "| 1 | `IdlePolicy.evaluate` |",
    "| INV-01 |",
)


@pytest.mark.parametrize(
    ("edits", "flagged"),
    [
        pytest.param(
            ((_NOTE, "| partly read; not read in full: the fixture file only |"),),
            _BASELINE_FLAGGED,
            id="a-note-that-says-read-in-full-later-is-still-partly-read",
        ),
        pytest.param(
            (
                (_NOTE, f"| read in full; {_NOTE[2:]}"),
                (
                    "\n\n**Verdict distribution:**",
                    "\n| `src/constants.py` | CF-01 | partly read: the thresholds only |"
                    "\n\n**Verdict distribution:**",
                ),
                (
                    _CF01_EVIDENCE,
                    "`code: src/constants.py defines every threshold the policy reads`",
                ),
            ),
            ("| CF-01 | main",),
            id="a-file-cited-in-an-evidence-cell-and-in-no-symbol-row",
        ),
        pytest.param(
            (
                (
                    _CF01_EVIDENCE,
                    "`code: src/only/policy.py resets state when eligibility fails`",
                ),
            ),
            _BASELINE_FLAGGED,
            id="a-universal-word-inside-a-file-path-is-a-name",
        ),
        pytest.param(
            (
                (
                    _CF01_EVIDENCE,
                    "`code: src/policy.py resets state and only then returns`",
                ),
            ),
            (*_BASELINE_FLAGGED, "| CF-01 | main"),
            id="the-same-word-beside-a-file-path-is-a-claim",
        ),
    ],
)
def test_quantifiers_check_edge_cases(
    installation: tuple[Path, Path],
    edits: tuple[tuple[str, str], ...],
    flagged: tuple[str, ...],
) -> None:
    _installed, project = installation
    source = project / _QUANTIFIER_FIXTURE
    text = source.read_text(encoding="utf-8")
    for old, new in edits:
        assert text.count(old) == 1, (
            f"the edit needs exactly one {old!r} in the fixture"
        )
        text = text.replace(old, new)
    edited = source.with_name("probe-quantifiers-edge.md")
    edited.write_text(text, encoding="utf-8")
    result = validate_run(
        installation, f"{_QUANTIFIER_FIXTURE[:-3]}-edge.md", "--check", "quantifiers"
    )
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert set(findings(result.stdout)) == {line_of(edited, p) for p in flagged}, out


# --- the skill text carries the markers, the flag and the rule -------------------------------

_UNIVERSAL_WORD_RULE = (
    "A universal word (every, only, always, never, no) in a scenario, invariant or register "
    "claim covers a whole set: write its enumeration beside it or narrow the word, and "
    "search your text for these words before review."
)


def folded(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def h2_section(path: Path, title: str) -> str:
    """The text under the `## ` heading that starts with `title`, or a loud failure."""
    for part in re.split(r"(?m)^## ", path.read_text(encoding="utf-8"))[1:]:
        if part.startswith(title):
            return " ".join(part.split())
    raise AssertionError(f"{path.name} has no section '## {title}'")


def test_the_universal_word_rule_is_stated_in_section_b_and_the_self_challenge(
    installation: tuple[Path, Path],
) -> None:
    installed, _project = installation
    section_b = h2_section(installed / "SKILL.md", "B. Author judgments")
    assert _UNIVERSAL_WORD_RULE in section_b
    challenge = h2_section(
        installed / "references/evidence-and-close.md", "Final self-challenge"
    )
    assert _UNIVERSAL_WORD_RULE in challenge


def joined_continuations(path: Path) -> str:
    """The file's text with every backslash line continuation joined, so a printed command
    that is re-wrapped over two lines is still the one line it is."""
    return re.sub(r"\\\r?\n[ \t]*", " ", path.read_text(encoding="utf-8"))


# How a label must be written for the detector to count it: a label in another form is not counted.
_LABEL_FORM = "exactly as written (bold, the colon inside the bold, capitalised)"


def test_the_skill_passes_the_registers_flag_and_names_both_markers(
    installation: tuple[Path, Path],
) -> None:
    installed, _project = installation
    skill = installed / "SKILL.md"
    commands = [
        line
        for line in joined_continuations(skill).splitlines()
        if "find_absent_cross_flow_seams.py" in line
    ]
    assert len(commands) == 1 and "--registers" in commands[0], commands
    section_d = h2_section(skill, "D. Reconcile neighbors and register findings")
    assert "- **Residue verdict:**" in section_d
    assert "- **Verdict ownership:**" in section_d
    template = folded(installed / "assets/flow-map-template.md")
    register_note = template.rsplit("````", 1)[-1]
    assert "- **Residue verdict:**" in register_note, (
        "the template's register note does not show the form the detector counts"
    )
    assert "- **Verdict ownership:**" in register_note
    assert _LABEL_FORM in register_note, (
        f"the template's register note does not say the label is counted {_LABEL_FORM!r}"
    )


# Every way a list item can open. The detector reads some of them, the template's register
# note says which, and the test below holds the two together by running the detector.
_ITEM_OPENERS = ("-", "*", "+", "1.", "1)")
_ITEM_PROMISE = re.compile(
    r"counts only an? (?P<forms>`[^`\s]+`(?:(?:, | or )`[^`\s]+`)*) bullet\b"
)


def promised_item_forms(note: str) -> set[str]:
    """The item openers a register note says the detector counts, read from its sentence
    "counts only a `-` or `*` bullet"; a note that does not say it in that shape fails loudly
    instead of promising nothing."""
    match = _ITEM_PROMISE.search(note)
    if match is None:
        raise AssertionError(
            "the register note does not say which item forms the detector counts "
            f"(expected: counts only a `-` or `*` bullet): {note}"
        )
    return set(re.findall(r"`([^`]+)`", match.group("forms")))


@pytest.mark.parametrize(
    "opener",
    [
        pytest.param(opener, id=name)
        for opener, name in zip(
            _ITEM_OPENERS,
            ("hyphen", "asterisk", "plus", "number-dot", "number-paren"),
            strict=True,
        )
    ],
)
def test_the_register_note_promises_exactly_the_item_forms_the_detector_counts(
    installation: tuple[Path, Path], opener: str
) -> None:
    installed, project = installation
    registers = project / "form-registers"
    registers.mkdir()
    (registers / "BUG-register-flow-form.md").write_text(
        f"### R-form-01 · the other candidates\n{_BASE_BULLETS}\n"
        "### R-form-02 · the candidate under test\n"
        f"{opener} **Residue verdict:** seamed-at-row-level — `{_AGREE}` in `{_DOC_A}` "
        f"and `{_DOC_B}`\n",
        encoding="utf-8",
    )
    result = seam_run(installation, "--registers", "form-registers")
    out = result.stdout + result.stderr
    counted = "4 candidates, 0 without a disposition" in result.stdout
    assert counted or "4 candidates, 1 without a disposition" in result.stdout, out
    assert result.returncode == (0 if counted else 1), out

    note = folded(installed / "assets/flow-map-template.md").rsplit("````", 1)[-1]
    assert "list item" not in note, (
        "the note says any list item counts; the detector does not"
    )
    promised = opener in promised_item_forms(note)
    assert promised == counted, (
        f"the detector {'counts' if counted else 'does not count'} an item opened with "
        f"{opener!r}, and the register note "
        f"{'promises' if promised else 'does not promise'} it: {note}"
    )


def test_the_item_form_parser_sees_planted_sentences_and_fails_loudly() -> None:
    two = "The run counts only a `-` or `*` bullet that opens with a label."
    assert promised_item_forms(two) == {"-", "*"}
    assert promised_item_forms("It counts only a `-`, `*` or `+` bullet.") == {
        "-",
        "*",
        "+",
    }
    assert promised_item_forms("It counts only a `-` bullet here.") == {"-"}
    with pytest.raises(AssertionError, match="does not say which item forms"):
        promised_item_forms("The run counts only a list item that opens with a label.")
    with pytest.raises(AssertionError, match="does not say which item forms"):
        promised_item_forms("The run counts a `-` or `*` bullet and more.")


_REGISTERS_PARAGRAPH = (
    "With `--registers` the detector counts an absent-link candidate, verdict "
    "disagreement or blind spot as disposed only when one register bullet with either "
    "marker names its full symbol and both documents by file name, and exits 1 listing "
    "the rest. Ownership stated only in a row is not counted: write the bullet too. "
    "Suppressed-link candidates stay a reading obligation."
)
_QUANTIFIERS_SENTENCE = (
    "The validator's `quantifiers` check reports such a word in a row that cites a file "
    "whose Coverage note does not start `read in full`. The default run prints it "
    "without failing; `--check quantifiers` makes it block."
)
_QUANTIFIERS_VALIDATION_SENTENCE = (
    "Flow validation succeeds with exit 0 and no blocking findings; a `[quantifiers]` "
    "line is printed without changing the exit code, so read it, or run "
    "`--check quantifiers` to make it block."
)


def test_the_skill_says_what_the_registers_flag_counts_and_how_the_quantifiers_check_reports(
    installation: tuple[Path, Path],
) -> None:
    installed, _project = installation
    skill = installed / "SKILL.md"
    section_d = h2_section(skill, "D. Reconcile neighbors and register findings")
    assert _REGISTERS_PARAGRAPH in section_d
    section_b = h2_section(skill, "B. Author judgments")
    assert _QUANTIFIERS_SENTENCE in section_b
    section_f = h2_section(skill, "F. Validate and close")
    assert _QUANTIFIERS_VALIDATION_SENTENCE in section_f
