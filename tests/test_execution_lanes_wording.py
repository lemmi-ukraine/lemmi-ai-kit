"""The checks of the execution lanes wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_each_template_copy_carries_the_lane_line_in_each_task_block`: each template copy carries the lane line in each task block
* `test_the_two_template_copies_are_byte_equal`: The seeded copy and the kit's own are two files that must not drift. Two different texts are shown to be told apart, so an agreement of the real pair is not an agreement of two things the comparison cannot tell apart.
* `test_git_is_installed`: The join gate is a git export. A machine without git fails here instead of skipping.
* `test_the_join_gate_names_the_export_command_the_toy_repository_runs`: the join gate names the export command the toy repository runs
* `test_the_export_holds_the_pre_feature_commit_and_none_of_the_new_files`: the export holds the pre feature commit and none of the new files
* `test_the_join_gate_is_red_on_the_export_and_green_on_the_tree`: the join gate is red on the export and green on the tree
* `test_the_join_gate_flags_a_test_that_already_passes_on_the_export`: The planted known positive: a T lane test of something that exists before the feature exits 0 on the export, so the gate reports that it proves nothing about the feature.
* `test_the_join_gate_flags_a_test_that_fails_on_the_tree`: the join gate flags a test that fails on the tree
* `test_the_join_gate_flags_a_test_that_fails_on_the_export_for_another_reason`: the join gate flags a test that fails on the export for another reason
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO / "plugins" / "core" / "skills" / "spec-driven-dev"
_PAGE = _SKILL_DIR / "references" / "execution-lanes.md"
_JOIN_GATE = "## Join gate"
_TEMPLATE_DIR = (
    _REPO / "plugins" / "core" / "src" / "lemmi_ai_kit" / "assets" / "ai" / "templates"
)
_TEMPLATES: dict[str, Path] = {
    "seeded": _TEMPLATE_DIR / "tasks.md",
    "kit": _REPO / ".ai" / "templates" / "tasks.md",
}
_LANE_LINE = (
    "- **Lane** (optional, only when the plan uses execution lanes): "
    "D (development) / T (tests)"
)
_HEADING = re.compile(r"^(#{1,6})\s")


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _section(text: str, heading: str) -> str:
    """From the line that is `heading` to the next heading of the same or a higher level; a `#`
    line inside a fenced block is not a heading. A text without the heading fails loudly."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        found = None if in_fence or fence else _HEADING.match(line)
        if fence:
            in_fence = not in_fence
        if not body:
            if found is not None and line == heading:
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"no heading {heading!r}")
    return "\n".join(body)


def _fenced_lines(text: str) -> list[str]:
    """Every line inside a fenced block, in order; a block left open fails loudly."""
    lines: list[str] = []
    inside = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
        elif inside:
            lines.append(line)
    assert not inside, "a fenced block is never closed"
    return lines


# --- the page ------------------------------------------------------------------------------------


# --- the pointer in SKILL.md -----------------------------------------------------------------------


# --- the tasks template ----------------------------------------------------------------------------


def _task_blocks(text: str) -> list[tuple[str, list[str]]]:
    """(heading, lines) of every `### Task` block: from its heading to the next heading."""
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if line.startswith("### Task "):
            current = []
            blocks.append((line, current))
        elif _HEADING.match(line):
            current = None
        elif current is not None:
            current.append(line)
    return blocks


def _lane_gaps(text: str) -> list[str]:
    """What a copy of the tasks template lacks: one Lane line, the expected one, in each of its two
    example task blocks, and no Lane line outside a task block."""
    blocks = _task_blocks(text)
    gaps = [] if len(blocks) == 2 else [f"{len(blocks)} task blocks, not 2"]
    for title, body in blocks:
        found = [line for line in body if "**Lane**" in line]
        if found != [_LANE_LINE]:
            gaps.append(f"{title}: Lane lines are {found}")
    every = [line for line in text.split("\n") if "**Lane**" in line]
    inside = [line for _, body in blocks for line in body if "**Lane**" in line]
    if len(every) != len(inside):
        gaps.append(f"{len(every) - len(inside)} Lane lines outside a task block")
    return gaps


@pytest.mark.parametrize("name", list(_TEMPLATES))
def test_each_template_copy_carries_the_lane_line_in_each_task_block(name: str) -> None:
    gaps = _lane_gaps(_read(_TEMPLATES[name]))
    assert not gaps, f"{name} copy of the tasks template: {gaps}"


def test_the_two_template_copies_are_byte_equal() -> None:
    """The seeded copy and the kit's own are two files that must not drift. Two different texts
    are shown to be told apart, so an agreement of the real pair is not an agreement of two things
    the comparison cannot tell apart."""
    seeded = _TEMPLATES["seeded"].read_bytes()
    kit = _TEMPLATES["kit"].read_bytes()
    assert seeded == kit, "the two copies of the tasks template differ"
    assert seeded + b" " != kit and seeded[:-1] != kit


# --- the join gate, run -------------------------------------------------------------------------------

# The toy: a pre-feature file, the D lane's edit of it, and the T lane's new files. The lanes use
# disjoint file sets: the D lane owns `shop.py`, the T lane owns the `check_*.py` scripts.
_SHOP_BEFORE = "def subtotal(prices):\n    return sum(prices)\n"
_SHOP_AFTER = (
    f"{_SHOP_BEFORE}\n\ndef total(prices, tax_percent):\n"
    "    return subtotal(prices) * (100 + tax_percent) // 100\n"
)
_GOOD = "check_total.py"
_ALREADY_GREEN = "check_subtotal.py"
_RED_ON_TREE = "check_wrong.py"
_OTHER_REASON = "check_other.py"
_T_LANE: dict[str, str] = {
    _GOOD: "import shop\n\nassert shop.total([100, 100], 10) == 220, 'tax is added'\n",
    _ALREADY_GREEN: "import shop\n\nassert shop.subtotal([1, 2]) == 3, 'sums'\n",
    _RED_ON_TREE: "import shop\n\nassert shop.total([100, 100], 10) == 999, 'wrong'\n",
    _OTHER_REASON: "import shop\n\nassert shop.subtotal([1]) == 2, 'unrelated'\n",
}
# The reason the plan states for a test failing on the pre-feature tree: the feature is absent.
_STATED_REASON = "has no attribute 'total'"


class _Toy(NamedTuple):
    repo: Path
    start: str


class _Run(NamedTuple):
    code: int
    output: str


class _Verdict(NamedTuple):
    script: str
    on_export: _Run
    on_tree: _Run


def _git(repo: Path, *args: str) -> str:
    """One git command in `repo`, with no identity, signing or line-end setting read from the
    machine. A machine without git raises here: the test fails, it does not skip."""
    done = subprocess.run(
        [
            "git",
            "-c",
            "user.name=lane-test",
            "-c",
            "user.email=lane-test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.autocrlf=false",
            "-C",
            str(repo),
            *args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert done.returncode == 0, f"git {' '.join(args)}: {done.stderr}"
    return done.stdout.strip()


def _build_toy(root: Path) -> _Toy:
    repo = root / "toy"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    (repo / "shop.py").write_text(_SHOP_BEFORE, encoding="utf-8", newline="\n")
    _git(repo, "add", "--", "shop.py")
    _git(repo, "commit", "--quiet", "-m", "the pre-feature commit")
    start = _git(repo, "rev-parse", "HEAD")
    assert {"shop.py"}.isdisjoint(_T_LANE), "the two lanes share a file"
    (repo / "shop.py").write_text(_SHOP_AFTER, encoding="utf-8", newline="\n")
    for name, body in _T_LANE.items():
        (repo / name).write_text(body, encoding="utf-8", newline="\n")
    _git(repo, "add", "--", "shop.py", *_T_LANE)
    _git(repo, "commit", "--quiet", "-m", "both lanes")
    return _Toy(repo, start)


@pytest.fixture(scope="module")
def toy(tmp_path_factory: pytest.TempPathFactory) -> _Toy:
    return _build_toy(tmp_path_factory.mktemp("lanes"))


def _export_line() -> str:
    """The one `git archive` line of the page's join gate, as written there."""
    lines = _fenced_lines(_section(_read(_PAGE), _JOIN_GATE))
    found = [line for line in lines if line.startswith("git archive ")]
    assert len(found) == 1, f"{len(found)} git archive lines in the join gate: {lines}"
    return found[0]


def _option(argv: list[str], name: str) -> str:
    values = [arg[len(name) :] for arg in argv if arg.startswith(name)]
    assert len(values) == 1, f"{len(values)} {name} options in {argv}"
    return values[0]


def _export(toy: _Toy, scratch: Path) -> Path:
    """The pre-feature commit unpacked as the page says: its `git archive` line run as written with
    the two placeholders filled, then the archive unpacked. The page prints no unpack command, so
    this does it with the standard library: GNU `tar` reads `C:` in a file name as a host."""
    scratch.mkdir(parents=True, exist_ok=True)
    line = _export_line().replace("<start commit>", toy.start)
    argv = shlex.split(line.replace("<scratch>", shlex.quote(scratch.as_posix())))
    done = subprocess.run(
        argv,
        cwd=toy.repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert done.returncode == 0, f"{argv}: {done.stderr}"
    with tarfile.open(_option(argv, "--output=")) as bundle:
        bundle.extractall(scratch, filter="data")
    return scratch / _option(argv, "--prefix=").strip("/")


def _run(folder: Path, script: str) -> _Run:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    done = subprocess.run(
        [sys.executable, "-B", script],
        cwd=folder,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return _Run(done.returncode, done.stdout + done.stderr)


def _join(toy: _Toy, scratch: Path, scripts: tuple[str, ...]) -> list[_Verdict]:
    """The join gate: the T lane's scripts copied into the export of the pre-feature commit and run
    there, then run on the tree both lanes wrote."""
    exported = _export(toy, scratch)
    for script in scripts:
        shutil.copyfile(toy.repo / script, exported / script)
    return [
        _Verdict(script, _run(exported, script), _run(toy.repo, script))
        for script in scripts
    ]


def _problems(verdicts: list[_Verdict]) -> list[str]:
    """Every way a test fails the gate: green on the export, red there for a reason the plan did
    not state, or red on the tree."""
    found: list[str] = []
    for verdict in verdicts:
        if verdict.on_export.code == 0:
            found.append(
                f"{verdict.script}: passes on the export, so it proves nothing"
            )
        elif _STATED_REASON not in verdict.on_export.output:
            found.append(f"{verdict.script}: fails on the export for another reason")
        if verdict.on_tree.code != 0:
            found.append(f"{verdict.script}: fails on the tree")
    return found


def test_git_is_installed() -> None:
    """The join gate is a git export. A machine without git fails here instead of skipping."""
    assert shutil.which("git") is not None, (
        "git is not on PATH: these tests do not skip"
    )


def test_the_join_gate_names_the_export_command_the_toy_repository_runs() -> None:
    line = _export_line()
    for part in ("--format=tar", "--prefix=", "--output=<scratch>/", "<start commit>"):
        assert part in line, f"the git archive line lacks {part!r}: {line!r}"
    block = _fenced_lines(_section(_read(_PAGE), _JOIN_GATE))
    assert block == [line], f"the join gate prints a command that is not run: {block}"


def test_the_export_holds_the_pre_feature_commit_and_none_of_the_new_files(
    toy: _Toy, tmp_path: Path
) -> None:
    exported = _export(toy, tmp_path / "scratch")
    assert (exported / "shop.py").read_text(encoding="utf-8") == _SHOP_BEFORE
    held = sorted(p.name for p in exported.iterdir())
    assert held == ["shop.py"], f"the export holds {held}: the T lane's files are new"


def test_the_join_gate_is_red_on_the_export_and_green_on_the_tree(
    toy: _Toy, tmp_path: Path
) -> None:
    (verdict,) = _join(toy, tmp_path / "scratch", (_GOOD,))
    assert (verdict.on_export.code, verdict.on_tree.code) == (1, 0), verdict
    assert _STATED_REASON in verdict.on_export.output, verdict.on_export.output
    assert _problems([verdict]) == []


def test_the_join_gate_flags_a_test_that_already_passes_on_the_export(
    toy: _Toy, tmp_path: Path
) -> None:
    """The planted known positive: a T lane test of something that exists before the feature
    exits 0 on the export, so the gate reports that it proves nothing about the feature."""
    verdicts = _join(toy, tmp_path / "scratch", (_GOOD, _ALREADY_GREEN))
    by_script = {v.script: v for v in verdicts}
    assert by_script[_ALREADY_GREEN].on_export.code == 0, by_script[_ALREADY_GREEN]
    assert _problems(verdicts) == [
        f"{_ALREADY_GREEN}: passes on the export, so it proves nothing"
    ]


def test_the_join_gate_flags_a_test_that_fails_on_the_tree(
    toy: _Toy, tmp_path: Path
) -> None:
    verdicts = _join(toy, tmp_path / "scratch", (_GOOD, _RED_ON_TREE))
    assert _problems(verdicts) == [f"{_RED_ON_TREE}: fails on the tree"]


def test_the_join_gate_flags_a_test_that_fails_on_the_export_for_another_reason(
    toy: _Toy, tmp_path: Path
) -> None:
    verdicts = _join(toy, tmp_path / "scratch", (_OTHER_REASON,))
    assert _problems(verdicts) == [
        f"{_OTHER_REASON}: fails on the export for another reason",
        f"{_OTHER_REASON}: fails on the tree",
    ]
