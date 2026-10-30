"""`generate_flow_projections.py --certify` says what it did not check.

`--certify` compares the derived columns of the rows a document declares. A Symbol index row the
author never wrote, and an authored cell left blank, therefore read as `0 differing` and exit 0:
the same zero a correct document gets. A clean run that cannot see part of its subject has to say
so (cannot-measure is never a pass), so every run prints one `NOT CHECKED:` line naming the
authored columns and the row sets it did not look at. The exit code and the bare total on the last
line are unchanged, because `probe_checker` reads that line.

Each test runs the script as a process on a variant of the skill's own conformant fixture.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills" / "flow-mapping"
)
_FIXTURE = "scripts/fixtures/flow_projection"
_CONFORMANT = (
    _SKILL / "assets" / "probe-project" / _FIXTURE / "conformant.md"
).read_text(encoding="utf-8")

_ROW = "| `IdlePolicy._silent_for` | `src/policy.py` | FP-02 | `IdlePolicy.evaluate` | — |\n"
_INVARIANT_CELL = "`external: connection-manager sweep` | INV-01 |"
_DERIVED_ROW = "| `IdlePolicy._reset` | `src/policy.py` | FP-01, FP-03 | `IdlePolicy.evaluate` | — |"
_CITED_COVERAGE_ROW = "| `src/policy.py` | FP-01, FP-02, FP-03 | all indexed symbols, call sites, and evidence live in this fixture file |\n"
_UNCITED_COVERAGE_ROW = (
    "| `src/constants.py` | _none_ | read in full; no cited use in this fixture |\n"
)

# Per table: the columns --certify compares, and the columns that name a row. Everything else is
# authored, and the NOT CHECKED line has to name exactly that.
_DERIVED = {
    "Symbol index": {"scenarios", "called by"},
    "Call graph": {"scenarios"},
    "Coverage": {"scenarios"},
    "Runtime applicability": {"unreachable scenarios"},
}
_ROW_KEYS = {
    "Symbol index": {"symbol"},
    "Call graph": {"caller", "callee"},
    "Coverage": {"file"},
    "Runtime applicability": set[str](),
}


@pytest.fixture(scope="module")
def installation(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    work = tmp_path_factory.mktemp("c")
    skill = work / "flow-mapping"
    shutil.copytree(_SKILL, skill)
    project = work / "proj"
    shutil.copytree(skill / "assets" / "probe-project", project)
    return skill, project


def _certify(
    installation: tuple[Path, Path], text: str
) -> "subprocess.CompletedProcess[str]":
    skill, project = installation
    (project / _FIXTURE / "variant.md").write_text(text, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(skill / "scripts" / "generate_flow_projections.py"),
            "--project-root",
            str(project),
            "--code-root",
            "src",
            f"{_FIXTURE}/variant.md",
            "--certify",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def _edited(old: str, new: str) -> str:
    assert _CONFORMANT.count(old) == 1, f"the edit must match exactly once: {old!r}"
    return _CONFORMANT.replace(old, new)


def _not_checked(done: "subprocess.CompletedProcess[str]") -> str:
    lines = [
        line for line in done.stdout.splitlines() if line.startswith("NOT CHECKED:")
    ]
    assert len(lines) == 1, f"{len(lines)} NOT CHECKED lines in:\n{done.stdout}"
    return lines[0]


def _last_line(done: "subprocess.CompletedProcess[str]") -> str:
    return done.stdout.strip().splitlines()[-1]


def test_a_conformant_document_certifies_clean_and_still_says_what_it_did_not_check(
    installation: tuple[Path, Path],
) -> None:
    done = _certify(installation, _CONFORMANT)
    assert done.returncode == 0, done.stdout + done.stderr
    assert _last_line(done) == "0", (
        "the bare total stays the last line, for probe_checker"
    )
    assert "| Symbol index | 6 | 0 | 0 |" in done.stdout
    assert "row sets" in _not_checked(done)


def test_a_symbol_index_row_the_author_never_wrote_reads_clean_and_the_line_names_row_sets(
    installation: tuple[Path, Path],
) -> None:
    done = _certify(installation, _edited(_ROW, ""))
    assert done.returncode == 0, done.stdout + done.stderr
    assert _last_line(done) == "0"
    assert "| Symbol index | 5 | 0 | 0 |" in done.stdout, (
        "five rows read, none differing"
    )
    line = _not_checked(done)
    assert "row sets" in line and "only declared rows are compared" in line


def test_a_blanked_authored_cell_reads_clean_and_the_line_names_that_column(
    installation: tuple[Path, Path],
) -> None:
    done = _certify(
        installation, _edited(_INVARIANT_CELL, _INVARIANT_CELL.replace("INV-01", "—"))
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert _last_line(done) == "0"
    assert "invariants" in _not_checked(done)


def test_a_wrong_derived_cell_is_still_reported_and_the_line_is_still_printed(
    installation: tuple[Path, Path],
) -> None:
    """The control: the instrument can see a derived column, so the zeros above are not blindness."""
    wrong = _DERIVED_ROW.replace("FP-01, FP-03", "FP-01")
    done = _certify(installation, _edited(_DERIVED_ROW, wrong))
    assert done.returncode == 1, done.stdout + done.stderr
    assert _last_line(done) == "1"
    assert "| Symbol index | 6 | 1 | 0 |" in done.stdout
    _not_checked(done)


def test_a_cited_file_with_no_coverage_row_is_refused_not_certified(
    installation: tuple[Path, Path],
) -> None:
    """The one row-set check there is: a cited file needs a Coverage row, or --certify refuses."""
    done = _certify(installation, _edited(_CITED_COVERAGE_ROW, ""))
    assert done.returncode == 2, done.stdout + done.stderr
    assert "has no Coverage row" in done.stderr


def test_a_file_no_scenario_cites_can_lose_its_coverage_row_unseen_and_the_line_says_so(
    installation: tuple[Path, Path],
) -> None:
    done = _certify(installation, _edited(_UNCITED_COVERAGE_ROW, ""))
    assert done.returncode == 0, done.stdout + done.stderr
    assert _last_line(done) == "0"
    assert "a file no scenario cites" in _not_checked(done)


def _columns(markdown: str, section: str) -> list[str]:
    after = markdown.split(f"## {section}\n", 1)[1]
    header = next(line for line in after.splitlines() if line.startswith("|"))
    return [cell.strip() for cell in header.strip().strip("|").split("|")]


def test_the_line_names_exactly_the_authored_columns_of_the_four_tables(
    installation: tuple[Path, Path],
) -> None:
    line = _not_checked(_certify(installation, _CONFORMANT))
    examined = 0
    for section, derived in _DERIVED.items():
        columns = _columns(_CONFORMANT, section)
        examined += len(columns)
        authored = set(columns) - derived - _ROW_KEYS[section]
        clause = re.search(rf"{re.escape(section)}: ([^;)]*)", line)
        assert clause is not None, f"the line does not mention {section}: {line}"
        named = {name.strip() for name in clause.group(1).split(",")}
        assert named == authored, (
            f"{section}: the line names {named}, the table has {authored}"
        )
    assert examined == 17, (
        "the scan surface changed: re-derive the derived and row-key sets"
    )
