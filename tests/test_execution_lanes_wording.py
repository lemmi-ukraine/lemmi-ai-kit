"""The optional page on execution lanes, the line that points at it, the template line and the join
gate it describes are pinned here.

A plan can split a build into two execution lanes: a development lane (D) that writes the code and a
tests lane (T) that writes tests from the requirements, design and test plan only, in new files. The
skill said nothing of it and no seeded template had a field to say which lane a task is in. One
reference of `spec-driven-dev` now says it, labelled optional and untried, because no feature has
been built through it end to end yet. SKILL.md gains one pointer line under "During Implementation",
and both copies of the tasks template gain one optional Lane line in each of their two example
tasks. The page belongs to Core: nothing in it links out of the pack.

What each test asserts:

* The page states each claim: its label, the two lanes, the Lane field, disjoint file sets, the
  contracts, the join gate (red on an export of the pre-feature commit, green on the D lane's tree,
  a failure settled against the requirements), and what the split does not do. Each phrase is fired
  at a planted removal.
* SKILL.md points at the page once, inside its section, calls it optional, the link resolves, and
  the file stays inside the 499-line cap. The pointer check is fired at planted shapes.
* Both template copies carry the Lane line in each task block and nowhere else, and the two copies
  are byte-equal. The check is fired at planted shapes.
* The join gate is run, not only quoted. A throwaway repository is built in a temporary folder with
  one pre-feature commit and one commit for both lanes. The page's own `git archive` line is run as
  written, its two placeholders filled, and the archive is unpacked; the T lane's tests are copied
  into the export (they are new files, so the export cannot hold them) and run there, then on the
  tree. Exit 1 before, exit 0 after. A test that already passes on the export is flagged as vacuous,
  and so are one that fails on the tree and one that fails on the export for a reason the plan did
  not state. A machine without git fails these tests: they do not skip.

THE SURFACE, in numbers the tests assert: 9 claims and 21 phrases in one page, 1 pointer line in 1
SKILL.md, 2 template copies with 2 task blocks each, and 1 toy repository with 4 test scripts of the
T lane: 1 that is red then green, and 3 planted known positives (one already green on the export,
one red on the tree, one red on the export for another reason).
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
_SKILL_MD = _SKILL_DIR / "SKILL.md"
_PAGE = _SKILL_DIR / "references" / "execution-lanes.md"
_LINK_TARGET = "references/execution-lanes.md"
_SKILL_SECTION = "## During Implementation"
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
_SKILL_CAP = 499
_HEADING = re.compile(r"^(#{1,6})\s")

# (claim, the phrases that must all be in the page; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1: the page is labelled optional and untried",
        (
            "optional, and untried",
            "reasoned, not run end to end on a real feature",
        ),
    ),
    (
        "2: a task may run in two execution lanes, and an execution lane is not a review lane",
        (
            "a task may run in two execution lanes",
            "an execution lane is not a review lane",
        ),
    ),
    (
        "3: every task carries a Lane field: D writes the code, T writes tests from the spec only",
        (
            "every task in `tasks.md` carries a lane field",
            "d (development: writes the implementation)",
            "t (tests: written from the requirements, design and test plan only, in new files",
        ),
    ),
    (
        "4: the lanes use disjoint file sets, and a shared file belongs to exactly one lane",
        ("disjoint file sets", "belongs to exactly one lane"),
    ),
    (
        "5: the T lane opens by asking about each shared contract, a practice and not a rule",
        (
            "each contract the two lanes share",
            "before its first code edit",
            "a practice, not a rule",
        ),
    ),
    (
        "6: the join gate runs the T lane's tests on an export of the pre-feature commit, red",
        (
            "join gate",
            "an export of the pre-feature commit",
            "every one must fail, for the reason the test plan gives",
            "proves nothing about the feature",
        ),
    ),
    (
        "7: the same tests run on the D lane's tree, green",
        ("run the same tests on the d lane's tree. every one must pass",),
    ),
    (
        "8: a failure is settled against the requirements and recorded, never edited away",
        (
            "settled against the requirements, never by editing the test to fit the code",
            "record it in the deviations log",
        ),
    ),
    (
        "9: the split does not change whose properties the tests come from, or replace a mutation pass",
        (
            "changes who writes the tests, not whose list of properties they come from",
            "does not replace an independent mutation pass or the review",
        ),
    ),
)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _words(text: str) -> str:
    """Quote markers and emphasis marks dropped, whitespace folded, lower-cased: a line re-wrapped
    inside a quote or a re-emphasised word is the same sentence."""
    plain = re.sub(r"^\s*>+ ?|\*", "", text, flags=re.MULTILINE)
    return " ".join(plain.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


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


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (9, 21)
    assert _PAGE.is_file(), _PAGE
    assert _SKILL_MD.is_file(), _SKILL_MD
    assert len(_TEMPLATES) == 2
    unreadable = [name for name, path in _TEMPLATES.items() if not path.is_file()]
    assert not unreadable, f"templates not where the test looks: {unreadable}"
    assert len(_T_LANE) == 4


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[row[0] for row in _ROWS])
def test_the_page_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_words(_read(_PAGE)), phrases)
    assert not missing, f"the page does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real page in turn is the one gap reported, and
    an empty page lacks every phrase of a row. A phrase the check cannot see go would let the page
    lose its claim and stay green."""
    text = _words(_read(_PAGE))
    for claim, phrases in _ROWS:
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_label_comes_before_the_first_section() -> None:
    """A reader who stops at the first heading has still been told the page is optional."""
    text = _words(_read(_PAGE))
    assert "## " in text, "the page has no section"
    assert text.index("optional, and untried") < text.index("## "), text[:120]


# --- the pointer in SKILL.md -----------------------------------------------------------------------


def _pointer_problems(text: str, skill_dir: Path) -> list[str]:
    """What is wrong with the pointer lines of a SKILL.md: not one line, outside its section, not
    called optional, a link that does not resolve, or more lines than the cap."""
    section_lines = _section(text, _SKILL_SECTION).split("\n")
    lines = [line for line in text.split("\n") if f"]({_LINK_TARGET})" in line]
    if len(lines) != 1:
        return [f"{len(lines)} lines link {_LINK_TARGET}, expected one"]
    problems: list[str] = []
    if lines[0] not in section_lines:
        problems.append(f"the pointer is not under {_SKILL_SECTION!r}")
    if "optional" not in lines[0].lower():
        problems.append("the pointer does not call the page optional")
    if not (skill_dir / _LINK_TARGET).is_file():
        problems.append(f"the link target {_LINK_TARGET} does not resolve")
    if text.count("\n") > _SKILL_CAP:
        problems.append(f"{text.count(chr(10))} lines, over the cap of {_SKILL_CAP}")
    return problems


def test_the_skill_points_at_the_page_once_inside_its_section() -> None:
    assert _pointer_problems(_read(_SKILL_MD), _SKILL_DIR) == []


def test_the_pointer_check_sees_each_planted_shape(tmp_path: Path) -> None:
    """Known positives and one near miss: a pointer that is missing, doubled, outside its section,
    not called optional, dead, or one line over the cap. The clean text passes with the page
    present, so a silence means something."""
    link = f"[{_LINK_TARGET}]({_LINK_TARGET})"
    good_line = f"- Optional: two execution lanes, see {link}"
    page = tmp_path / _LINK_TARGET
    page.parent.mkdir(parents=True)
    page.write_text("# page\n", encoding="utf-8")

    def skill(*, pointer: str = good_line, other: str = "Other text.") -> str:
        return (
            f"# S\n\n{_SKILL_SECTION}\n\n- a\n{pointer}\n\n## Next section\n\n{other}\n"
        )

    assert _pointer_problems(skill(), tmp_path) == []
    assert _pointer_problems(skill(pointer="- nothing"), tmp_path) == [
        f"0 lines link {_LINK_TARGET}, expected one"
    ]
    doubled = _pointer_problems(skill(pointer=good_line, other=good_line), tmp_path)
    assert doubled == [f"2 lines link {_LINK_TARGET}, expected one"]
    outside = _pointer_problems(skill(pointer="- a", other=good_line), tmp_path)
    assert outside == [f"the pointer is not under {_SKILL_SECTION!r}"]
    plain = _pointer_problems(skill(pointer=f"- Two lanes, see {link}"), tmp_path)
    assert plain == ["the pointer does not call the page optional"]
    page.unlink()
    assert _pointer_problems(skill(), tmp_path) == [
        f"the link target {_LINK_TARGET} does not resolve"
    ]
    page.write_text("# page\n", encoding="utf-8")
    long_text = skill(other="\n" * (_SKILL_CAP + 1))
    assert len(_pointer_problems(long_text, tmp_path)) == 1
    with pytest.raises(AssertionError, match="no heading"):
        _pointer_problems(f"# S\n\n{good_line}\n", tmp_path)


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


def test_the_lane_check_sees_each_planted_shape() -> None:
    """Known positives: a line missing from one block, doubled in one, outside every block, and
    reworded. The seeded copy, which holds the line twice, reports nothing."""
    text = _read(_TEMPLATES["seeded"])
    assert text.count(_LANE_LINE) == 2, "the planted shapes need the line twice"
    assert _lane_gaps(text) == []
    once = text.replace(f"{_LANE_LINE}\n", "", 1)
    assert [gap.split(":")[0] for gap in _lane_gaps(once)] == ["### Task 1"]
    doubled = text.replace(_LANE_LINE, f"{_LANE_LINE}\n{_LANE_LINE}", 1)
    assert [gap.split(":")[0] for gap in _lane_gaps(doubled)] == ["### Task 1"]
    outside = text.replace(f"{_LANE_LINE}\n", "", 1).replace(
        "## Task List", f"{_LANE_LINE}\n\n## Task List", 1
    )
    assert len(_lane_gaps(outside)) == 2, _lane_gaps(outside)
    reworded = text.replace("D (development) / T (tests)", "D / T", 1)
    assert [gap.split(":")[0] for gap in _lane_gaps(reworded)] == ["### Task 1"]
    assert _lane_gaps("no task blocks at all") == ["0 task blocks, not 2"]


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
