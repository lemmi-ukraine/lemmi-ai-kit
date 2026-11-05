"""`stacked-pr-planner` carries two references behind one pointer, and the commands they print run.

Step 6 of the planner lists its re-plan triggers as commands. Several lessons about a layer did not
fit there: a declared-file guard that fires on every compliant branch, class counters that read a
healthy layer as mixed, a task that is conditional on the base's contents, the target's delta since
a pin, the fork base of a new initiative, where the tests of unmerged layers ride, and how a layer
is committed. They sit in two references, `layer-triggers.md` and `layer-mechanics.md`, and Step 6
ends with one paragraph that points at both.

What each test asserts:

* `test_the_reference_states_the_claim` reads each reference for the phrases of each claim, in the
  folded and lower-cased text, so a re-wrap does not fail it. A missing file fails with its path.
* `test_a_planted_removal_of_each_phrase_is_reported` fires the phrase check at planted text: the
  text that holds every phrase is clean, and cutting any one phrase out is reported by itself.
* `test_skill_md_points_at_both_references_from_step_6` reads Step 6 for one paragraph that links
  both references, checks that both files exist and that SKILL.md stays under its line cap.
* `test_the_pointer_names_what_each_reference_holds` reads the H2 headings of each reference and
  asks that the pointer paragraph uses a word for each.
* `test_the_printed_commands_run_in_a_throwaway_repository` takes the command lines out of the
  references as they are printed, fills their placeholders and runs each through `sh -c` in a
  repository it builds, so a command that no longer runs, or no longer prints what the text says
  it prints, fails. A missing shell fails the test; it is never skipped.
* `test_the_sentence_about_the_sample_counters_is_still_true` keeps the reference's account of the
  Step 6 sample counters true: if the sample or the BACKEND row changes, the sentence is stale.
* `test_the_references_carry_no_request_id` keeps tracker ids (a letter family and a number) out of
  the references.
* The remaining tests fire the pointer, command-scan, heading and shell-lookup code at planted
  text and planted locations, so the silence of the checks on the real files means something.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _ROOT / "plugins" / "orchestration" / "skills" / "stacked-pr-planner"
_SKILL = _SKILL_DIR / "SKILL.md"
_WHERE = "stacked-pr-planner SKILL.md"
_LINE_CAP = 499

_TRIGGERS = "layer-triggers.md"
_MECHANICS = "layer-mechanics.md"
_POINTED_AT = (f"references/{_TRIGGERS}", f"references/{_MECHANICS}")

# (reference, claim, the phrases that must all be present; lower-cased, whitespace collapsed)
_CLAIMS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        _TRIGGERS,
        "the guard exempts the checklist's logs as a pattern line of its own",
        (
            "must exempt the tracked logs the project's completion checklist appends to",
            "as a pattern line of its own",
            "or it fires on every compliant branch",
            r"grep -ve '^\.ai/(learnings|ai-changelog)\.md$'",
        ),
    ),
    (
        _TRIGGERS,
        "a corrected guard is a topology revision that sweeps every sibling guard",
        (
            "a correction to one layer's guard is a topology revision",
            "grep every other layer's guard and the table's rows for the old pattern in the same edit",
        ),
    ),
    (
        _TRIGGERS,
        "the counters have an accepted mixed reading recorded in the row",
        (
            "step 6's sample counts `.ai/` as docs and `tests/` as tooling",
            "defines backend as production code and the tests that gate it",
            "record that reading in the layer's row and do not reopen the plan",
            "a count in a class the row does not accept still fires",
        ),
    ),
    (
        _TRIGGERS,
        "a task conditional on the base re-fires at every merge and is written as a command",
        (
            "is not settled when its condition first reads false",
            "a merge from the base, a rebase or a cascade can make it true",
            "write the condition as a command the cascade step runs",
            "git ls-tree -r --name-only <base-tip> -- <file>",
            "an empty result still exits 0: read the output",
        ),
    ),
    (
        _TRIGGERS,
        "the target's delta is read per layer at every dispatch round, with the rules file",
        (
            "shows that the target moved, not what moved",
            "at every dispatch round, list what the target changed in each layer's paths",
            "git diff --name-status <pin> origin/<target> -- $(git diff --name-only <base>...<layer>)",
            "git diff <pin> origin/<target> -- <rules file>",
            "a layer with no changed path gives an empty pathspec and prints the whole delta",
            "a rebase of the target does not inflate them the way it inflates a commit count",
        ),
    ),
    (
        _MECHANICS,
        "the fork base is put to the operator when head sits on an unmerged chain",
        (
            "git log --oneline origin/<trunk>..head",
            "ties the new initiative's merge path to that chain",
            "put the fork base to the operator as a decision",
            "stays the operator's to waive",
        ),
    ),
    (
        _MECHANICS,
        "the base question carries its measured side effect",
        (
            "git diff --name-status origin/<trunk> head",
            "a landing that takes head's tree reverts those the trunk changed since the chain forked",
            "removes those only the trunk has",
            "fetch first",
        ),
    ),
    (
        _MECHANICS,
        "where the tests of unmerged layers ride decides which heads pass a gate",
        (
            "which heads can pass a gate that runs the base's suite on each head",
            "when each pr is signed off and merged alone, every layer carries the tests its own change needs",
            "only when the stack merges as a unit, and say so in that pr's body",
        ),
    ),
    (
        _MECHANICS,
        "a test's layer follows from its imports",
        (
            "a test belongs to the layer whose code it imports, not to the layer of the task that wrote it",
        ),
    ),
    (
        _MECHANICS,
        "test edits are diffed against head and the old test is run on the new code",
        (
            "diff each test file against head",
            "run the old test against the new code",
            "the test belongs in this layer",
        ),
    ),
    (
        _MECHANICS,
        "two layers that edit one file are committed in order",
        (
            "two layers that edit one file need the first committed before the second starts",
        ),
    ),
]
_PHRASE_COUNT = 37

# One pair per H2 of each reference: a word of the heading, and the word the pointer must use.
_HOLDS: dict[str, tuple[tuple[str, str], ...]] = {
    _TRIGGERS: (
        ("declared-file guard", "declared-file guard"),
        ("class counters", "mixed reading"),
        ("conditional on the base", "conditional on the base"),
        ("target's delta", "target's delta"),
    ),
    _MECHANICS: (
        ("fork base", "fork base"),
        ("tests of unmerged layers", "tests ride"),
        ("committing a layer", "committing a layer"),
    ),
}
_H2_COUNTS = {_TRIGGERS: 4, _MECHANICS: 3}

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_LINK = re.compile(r"\]\((references/[^)#]+)")
_PLACEHOLDER = re.compile(r"<[^<>\n]+>")
_ASSIGNMENT_LED = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=")
_COMMAND_LINES = 6

# Tracker ids: a letter family, an optional hyphen and digits.
_REQUEST_ID = re.compile(r"\b(?:A|K|F|C|DEC|KIT)-?\d+\b")


# --- reading ------------------------------------------------------------------------------


def _reference(name: str) -> Path:
    return _SKILL_DIR / "references" / name


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(_ROOT).as_posix()} does not exist")
    return path.read_text(encoding="utf-8")


def _words(text: str) -> str:
    """The text lower-cased with every run of whitespace as one space."""
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: Sequence[str]) -> list[str]:
    """The phrases that the folded, lower-cased `text` does not hold."""
    words = _words(text)
    return [phrase for phrase in phrases if phrase not in words]


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the code it holds, not a heading. A missing heading fails with the
    heading named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _paragraphs(text: str) -> list[str]:
    return [chunk for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]


def _h2_headings(text: str) -> list[str]:
    """The H2 headings of `text`, outside fenced blocks."""
    in_fence = False
    found: list[str] = []
    for line in text.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            found.append(line[3:].strip())
    return found


def _fenced_blocks(section: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in section.split("\n"):
        if _is_fence(line):
            if in_fence:
                blocks.append(current)
                current = []
            in_fence = not in_fence
        elif in_fence:
            current.append(line)
    return blocks


# --- the claims ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reference", "claim", "phrases"), _CLAIMS, ids=[claim for _, claim, _ in _CLAIMS]
)
def test_the_reference_states_the_claim(
    reference: str, claim: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_read(_reference(reference)), phrases)
    assert not missing, f"{reference}, {claim}: missing {missing}"


def test_a_planted_removal_of_each_phrase_is_reported() -> None:
    phrases = [phrase for _, _, claim in _CLAIMS for phrase in claim]
    assert len(phrases) == _PHRASE_COUNT
    assert len(set(phrases)) == _PHRASE_COUNT, "a phrase is listed twice"
    planted = " ".join(
        f"Some words before. {phrase} Some words after." for phrase in phrases
    )
    assert _missing(planted, phrases) == [], "the control text is not clean"
    for phrase in phrases:
        cut = planted.replace(phrase, "", 1)
        assert cut != planted, f"the cut changed nothing: {phrase!r}"
        assert _missing(cut, phrases) == [phrase], (
            f"the cut of {phrase!r} was not reported alone"
        )
    # Near misses: a re-wrap and capital letters do not hide a phrase.
    assert _missing(planted.replace(" ", "\n  "), phrases) == []
    assert _missing(planted.upper(), phrases) == []


# --- the pointer --------------------------------------------------------------------------


def _pointer_problems(skill: str, exists: Callable[[str], bool]) -> list[str]:
    """What is wrong with the paragraph of Step 6 that links the references."""
    step = _section(skill, "## Step 6 ", _WHERE)
    holding = [chunk for chunk in _paragraphs(step) if _LINK.search(chunk)]
    problems: list[str] = []
    if len(holding) != 1:
        problems.append(
            f"{len(holding)} paragraphs of Step 6 link into references/, expected 1"
        )
    links = [link for chunk in holding for link in _LINK.findall(chunk)]
    problems.extend(
        f"Step 6 does not link {wanted}"
        for wanted in _POINTED_AT
        if wanted not in links
    )
    problems.extend(f"{link} does not exist" for link in links if not exists(link))
    return problems


def _cap_problems(skill_bytes: bytes) -> list[str]:
    lines = skill_bytes.count(b"\n")
    if lines > _LINE_CAP:
        return [f"SKILL.md has {lines} lines by wc -l, the cap is {_LINE_CAP}"]
    return []


def _pointer_text(skill: str) -> str:
    """The paragraphs of Step 6 that link into references/, joined."""
    step = _section(skill, "## Step 6 ", _WHERE)
    return "\n\n".join(chunk for chunk in _paragraphs(step) if _LINK.search(chunk))


def _hold_problems(reference: str, text: str, pointer: str) -> list[str]:
    """What the pointer fails to name of the H2 headings of one reference."""
    pairs = _HOLDS[reference]
    words = _words(pointer)
    problems: list[str] = []
    for heading in _h2_headings(text):
        named = [
            pointer_word
            for heading_word, pointer_word in pairs
            if heading_word in heading.lower()
        ]
        if len(named) != 1:
            problems.append(
                f"{reference}: the H2 {heading!r} matches {len(named)} table rows, expected 1"
            )
        elif named[0] not in words:
            problems.append(
                f"the pointer does not name {named[0]!r} for the H2 {heading!r} of {reference}"
            )
    return problems


def test_skill_md_points_at_both_references_from_step_6() -> None:
    skill = _SKILL.read_text(encoding="utf-8")
    problems = _pointer_problems(skill, lambda link: (_SKILL_DIR / link).is_file())
    problems.extend(_cap_problems(_SKILL.read_bytes()))
    assert not problems, f"{_WHERE}: " + "; ".join(problems)


def test_the_pointer_names_what_each_reference_holds() -> None:
    pointer = _pointer_text(_SKILL.read_text(encoding="utf-8"))
    problems: list[str] = []
    for reference, expected in _H2_COUNTS.items():
        text = _read(_reference(reference))
        found = len(_h2_headings(text))
        if found != expected:
            problems.append(f"{reference} has {found} H2 headings, expected {expected}")
        problems.extend(_hold_problems(reference, text, pointer))
    assert not problems, f"{_WHERE}, Step 6 pointer: " + "; ".join(problems)


_POINTER = (
    "More triggers and the mechanics of a layer, as commands: "
    "[layer triggers](references/layer-triggers.md)\n"
    "(the declared-file guard, the counters' accepted mixed reading, a task conditional on "
    "the base, the\n"
    "target's delta) and [layer mechanics](references/layer-mechanics.md) (the fork base, "
    "where tests\n"
    "ride, committing a layer)."
)


def _skill_with(step_six: str, after: str = "") -> str:
    return (
        "## Step 5 - before\n\nbody\n\n## Step 6 - triggers\n\nA closing paragraph.\n\n"
        f"{step_six}\n\n## Step 7 - next\n\n{after}\n"
    )


def _always(_link: str) -> bool:
    return True


def test_the_pointer_checks_see_planted_shapes() -> None:
    assert _pointer_problems(_skill_with(_POINTER), _always) == [], (
        "the control is not clean"
    )
    # A `#` comment line inside a fence does not end Step 6.
    fenced = "```bash\n# a comment\n```\n\n" + _POINTER
    assert _pointer_problems(_skill_with(fenced), _always) == []
    planted = {
        "the pointer sits under Step 7": _pointer_problems(
            _skill_with("", after=_POINTER), _always
        ),
        "the links sit in two paragraphs": _pointer_problems(
            _skill_with(
                _POINTER.replace(" and [layer mechanics]", "\n\n[layer mechanics]")
            ),
            _always,
        ),
        "one link is missing": _pointer_problems(
            _skill_with(
                _POINTER.replace("references/layer-mechanics.md", "elsewhere.md")
            ),
            _always,
        ),
        "a link is dead": _pointer_problems(_skill_with(_POINTER), lambda _link: False),
    }
    for shape, problems in planted.items():
        assert problems, f"the pointer check missed: {shape}"
    assert _cap_problems(b"x\n" * _LINE_CAP) == []
    assert _cap_problems(b"x\n" * (_LINE_CAP + 1)), "the cap check missed 500 lines"

    triggers = "\n".join(
        [
            "# Title",
            "## A declared-file guard exempts the logs",
            "```bash",
            "## a comment inside a fence is not a heading",
            "```",
            "## The class counters have an accepted mixed reading",
            "## A task conditional on the base's contents",
            "## The target's delta since the pin",
        ]
    )
    assert len(_h2_headings(triggers)) == _H2_COUNTS[_TRIGGERS]
    assert _hold_problems(_TRIGGERS, triggers, _POINTER) == [], (
        "the hold control is not clean"
    )
    silent = _POINTER.replace("mixed reading", "readings")
    assert _hold_problems(_TRIGGERS, triggers, silent), (
        "a word the pointer lost went unreported"
    )
    renamed = triggers + "\n## Something else entirely"
    assert _hold_problems(_TRIGGERS, renamed, _POINTER), (
        "an H2 with no table row went unreported"
    )


# --- the printed commands run -------------------------------------------------------------


def _fenced_lines(text: str) -> list[str]:
    """The non-blank lines inside fenced blocks, indentation dropped, in file order."""
    return [
        line.strip() for block in _fenced_blocks(text) for line in block if line.strip()
    ]


def _git_lines(text: str) -> list[str]:
    """Every line that starts with `git ` once its indentation is dropped."""
    return [
        line.strip() for line in text.split("\n") if line.lstrip().startswith("git ")
    ]


def _surface_problems(*texts: str) -> list[str]:
    """What the two instruments, a fence walk and a count of `git ` lines, make of the texts."""
    fenced = [line for text in texts for line in _fenced_lines(text)]
    started = [line for text in texts for line in _git_lines(text)]
    problems: list[str] = []
    if len(fenced) != _COMMAND_LINES:
        problems.append(
            f"{len(fenced)} fenced command lines, expected {_COMMAND_LINES}"
        )
    if len(started) != _COMMAND_LINES:
        problems.append(f"{len(started)} lines start `git `, expected {_COMMAND_LINES}")
    if fenced != started:
        problems.append(
            "the fence walk and the count of `git ` lines read different lines"
        )
    problems.extend(
        f"an assignment-led command line: {line!r}"
        for line in fenced
        if _ASSIGNMENT_LED.match(line)
    )
    return problems


def _the_line(lines: Sequence[str], start: str) -> str:
    hits = [line for line in lines if line.startswith(start)]
    if len(hits) != 1:
        raise AssertionError(f"{len(hits)} command lines start {start!r}, expected 1")
    return hits[0]


def _fill(command: str, values: dict[str, str]) -> str:
    """The command with each `<name>` replaced; a placeholder left over fails loudly."""
    filled = command
    for name, value in values.items():
        filled = filled.replace(f"<{name}>", value)
    left = _PLACEHOLDER.findall(filled)
    if left:
        raise AssertionError(f"placeholders {left} left unfilled in {command!r}")
    return filled


def _shell() -> str:
    """A POSIX shell: `sh` from PATH, else the one that ships with git. Never a skip."""
    found = shutil.which("sh")
    if found:
        return found
    git = shutil.which("git")
    if git:
        for parent in Path(git).resolve().parents:
            bundled = parent / "usr" / "bin" / "sh.exe"
            if bundled.is_file():
                return str(bundled)
    raise AssertionError(
        "no POSIX shell: `sh` is not on PATH and none ships beside git"
    )


def _run(repo: Path, command: str) -> tuple[int, str]:
    """The exit code and standard output of `command` through `sh -c`, run inside `repo`."""
    shell = _shell()
    path = os.pathsep.join([str(Path(shell).parent), os.environ.get("PATH", "")])
    done = subprocess.run(
        [shell, "-c", command],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PATH": path},
        timeout=60,
        check=False,
    )
    return done.returncode, done.stdout


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=True,
    )
    return done.stdout


def _repo(path: Path) -> Path:
    """An empty repository on branch `main`, with the identity a commit needs."""
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    for key, value in (
        ("user.name", "tester"),
        ("user.email", "tester@example.invalid"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
    ):
        _git(path, "config", key, value)
    return path


def _commit(repo: Path, message: str, files: dict[str, str | None]) -> str:
    """Write (or, for None, delete) each file, commit them all and return the commit."""
    for relative, body in files.items():
        target = repo / relative
        if body is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _guard_problems(tmp: Path, command: str) -> list[str]:
    head, tail = command.rsplit(" | ", 1)
    if "ai-changelog" not in tail or "ai-changelog" in head:
        return [f"the last stage of the guard is not the exemption: {tail!r}"]
    values = {"base": "main", "layer": "layer", "declared files regex": "^src/"}
    repo = _repo(tmp / "guard")
    _commit(repo, "base", {"src/code.py": "one\n", "docs/guide.md": "one\n"})
    _git(repo, "checkout", "-q", "-b", "layer")
    _commit(
        repo,
        "a compliant layer: its code and the two logs of the checklist",
        {
            "src/code.py": "two\n",
            ".ai/learnings.md": "x\n",
            ".ai/ai-changelog.md": "x\n",
        },
    )
    problems: list[str] = []
    _, compliant = _run(repo, _fill(command, values))
    if compliant.split():
        problems.append(f"the guard fires on a compliant layer: {compliant.split()}")
    _, without = _run(repo, _fill(head, values))
    if sorted(without.split()) != [".ai/ai-changelog.md", ".ai/learnings.md"]:
        problems.append(
            f"the guard without its exemption stage prints {without.split()}, "
            "expected the two logs"
        )
    _commit(repo, "a stray path", {"docs/other.md": "x\n"})
    _, stray = _run(repo, _fill(command, values))
    if stray.split() != ["docs/other.md"]:
        problems.append(f"a stray path prints {stray.split()}, expected docs/other.md")
    return problems


def _conditional_problems(tmp: Path, command: str) -> list[str]:
    repo = _repo(tmp / "conditional")
    _commit(repo, "base", {"src/present.py": "one\n"})
    problems: list[str] = []
    code, out = _run(
        repo, _fill(command, {"base-tip": "main", "file": "src/present.py"})
    )
    if code != 0 or out.split() != ["src/present.py"]:
        problems.append(f"a file the base holds prints {out.split()} (exit {code})")
    code, out = _run(
        repo, _fill(command, {"base-tip": "main", "file": "src/absent.py"})
    )
    if code != 0 or out != "":
        problems.append(
            f"a file the base lacks prints {out!r} (exit {code}), not nothing"
        )
    return problems


def _delta_problems(tmp: Path, rows_command: str, rules_command: str) -> list[str]:
    repo = _repo(tmp / "delta")
    pin = _commit(
        repo,
        "the trunk at the pin",
        {
            "src/a.py": "one\n",
            "src/b.py": "one\n",
            "src/c.py": "one\n",
            "AGENTS.md": "rule one\n",
            "other.txt": "one\n",
        },
    )
    _git(repo, "checkout", "-q", "-b", "layer")
    _commit(repo, "a layer", {"src/a.py": "layer\n", "src/b.py": "layer\n"})
    _git(repo, "branch", "layer-empty", "main")
    _git(repo, "checkout", "-q", "-b", "target-work", "main")
    moved = _commit(
        repo,
        "the target moves: one layer file changed, one deleted, the rules file changed",
        {
            "src/a.py": "target\n",
            "src/b.py": None,
            "AGENTS.md": "rule two\n",
            "other.txt": "t\n",
        },
    )
    _git(repo, "update-ref", "refs/remotes/origin/main", moved)
    values = {
        "pin": pin,
        "target": "main",
        "base": "main",
        "layer": "layer",
        "rules file": "AGENTS.md",
    }
    problems: list[str] = []
    _, rows = _run(repo, _fill(rows_command, values))
    if rows.splitlines() != ["M\tsrc/a.py", "D\tsrc/b.py"]:
        problems.append(
            f"the layer's rows are {rows.splitlines()}, expected its M and D rows only"
        )
    _, rules = _run(repo, _fill(rules_command, values))
    if "-rule one" not in rules or "+rule two" not in rules or "other.txt" in rules:
        problems.append(
            f"the rules-file diff is {rules!r}, expected that file's change alone"
        )
    _, whole = _run(repo, _fill(rows_command, {**values, "layer": "layer-empty"}))
    if len(whole.splitlines()) != 4 or "other.txt" not in whole:
        problems.append(
            f"a layer with no path prints {whole.splitlines()}, expected the whole delta"
        )
    return problems


def _fork_problems(tmp: Path, log_command: str, diff_command: str) -> list[str]:
    repo = _repo(tmp / "fork")
    _commit(repo, "the trunk", {"shared.txt": "one\n", "keep.txt": "one\n"})
    _git(repo, "checkout", "-q", "-b", "chain")
    # The two new files differ throughout, so rename detection cannot pair an A with a D.
    _commit(repo, "one unmerged commit", {"chain.txt": "chain one\nchain two\n"})
    _git(repo, "checkout", "-q", "main")
    moved = _commit(
        repo,
        "the trunk moves",
        {"shared.txt": "two\n", "trunk-only.txt": "trunk one\ntrunk two\n"},
    )
    _git(repo, "update-ref", "refs/remotes/origin/main", moved)
    values = {"trunk": "main"}
    problems: list[str] = []
    _git(repo, "checkout", "-q", "chain")
    _, unmerged = _run(repo, _fill(log_command, values))
    if len(unmerged.splitlines()) != 1:
        problems.append(
            f"HEAD on a chain prints {unmerged.splitlines()}, expected one line"
        )
    _, rows = _run(repo, _fill(diff_command, values))
    if sorted(rows.splitlines()) != [
        "A\tchain.txt",
        "D\ttrunk-only.txt",
        "M\tshared.txt",
    ]:
        problems.append(f"the side-effect rows are {sorted(rows.splitlines())}")
    _git(repo, "checkout", "-q", "main")
    _, none = _run(repo, _fill(log_command, values))
    if none != "":
        problems.append(f"HEAD on the trunk prints {none!r}, expected nothing")
    return problems


def test_the_printed_commands_run_in_a_throwaway_repository(tmp_path: Path) -> None:
    triggers = _read(_reference(_TRIGGERS))
    mechanics = _read(_reference(_MECHANICS))
    surface = _surface_problems(triggers, mechanics)
    assert not surface, "the scan surface is not what the test claims: " + "; ".join(
        surface
    )

    lines = [*_fenced_lines(triggers), *_fenced_lines(mechanics)]
    problems = [
        *_guard_problems(
            tmp_path, _the_line(lines, "git diff --name-only <base>...<layer> |")
        ),
        *_conditional_problems(tmp_path, _the_line(lines, "git ls-tree")),
        *_delta_problems(
            tmp_path,
            _the_line(lines, "git diff --name-status <pin>"),
            _the_line(lines, "git diff <pin>"),
        ),
        *_fork_problems(
            tmp_path,
            _the_line(lines, "git log --oneline origin/<trunk>"),
            _the_line(lines, "git diff --name-status origin/<trunk>"),
        ),
    ]
    assert not problems, "\n".join(problems)


def test_the_command_scan_sees_planted_lines() -> None:
    planted = "\n".join(
        [
            "Prose that mentions (`git status`) inline and is not a command line.",
            "```bash",
            "git log --oneline origin/<trunk>..HEAD",
            "",
            "  git diff --name-status origin/<trunk> HEAD",
            "```",
            "git stash list",
            "```bash",
            "TRUNK=main git fetch",
            "```",
        ]
    )
    assert _fenced_lines(planted) == [
        "git log --oneline origin/<trunk>..HEAD",
        "git diff --name-status origin/<trunk> HEAD",
        "TRUNK=main git fetch",
    ]
    assert _git_lines(planted) == [
        "git log --oneline origin/<trunk>..HEAD",
        "git diff --name-status origin/<trunk> HEAD",
        "git stash list",
    ]
    problems = _surface_problems(planted)
    assert any("assignment-led" in problem for problem in problems), problems
    assert any("read different lines" in problem for problem in problems), problems
    assert any("fenced command lines" in problem for problem in problems), problems

    clean = (
        "```bash\n"
        + "\n".join(f"git log -{n}" for n in range(_COMMAND_LINES))
        + "\n```\n"
    )
    assert _surface_problems(clean) == [], "the control is not clean"
    with pytest.raises(AssertionError, match="placeholders"):
        _fill("git log <trunk>..<other>", {"trunk": "main"})
    with pytest.raises(AssertionError, match="expected 1"):
        _the_line(["git log -1", "git log -2"], "git log")


def _which_only(found: dict[str, str]) -> Callable[[str], str | None]:
    """A stand-in for `shutil.which` that knows only the programs in `found`."""

    def which(name: str) -> str | None:
        return found.get(name)

    return which


def test_a_missing_shell_fails_and_the_one_beside_git_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    git_home = tmp_path / "Git"
    bundled = git_home / "usr" / "bin" / "sh.exe"
    fake_git = git_home / "cmd" / "git.exe"
    for stand_in in (bundled, fake_git):
        stand_in.parent.mkdir(parents=True)
        stand_in.write_text("", encoding="utf-8")

    monkeypatch.setattr(shutil, "which", _which_only({"sh": "/opt/bin/sh"}))
    assert _shell() == "/opt/bin/sh", "a shell on PATH must be the one used"
    monkeypatch.setattr(shutil, "which", _which_only({"git": str(fake_git)}))
    assert Path(_shell()) == bundled.resolve(), "the shell beside git was not found"
    monkeypatch.setattr(shutil, "which", _which_only({}))
    with pytest.raises(AssertionError, match="no POSIX shell"):
        _shell()


# --- the sample counters ------------------------------------------------------------------


def _classifier_block(section: str) -> list[str]:
    """The lines of the one fenced block of `section` that holds the class counters."""
    holding = [
        block
        for block in _fenced_blocks(section)
        if any("MIGRATION=$(" in line for line in block)
    ]
    if len(holding) != 1:
        raise AssertionError(
            f"{_WHERE}, Step 6: {len(holding)} fenced blocks hold the class counters, "
            "expected 1; the reference's account of the counters may be stale"
        )
    return holding[0]


def _backend_row(section: str) -> str:
    rows = [line for line in section.split("\n") if line.startswith("| `BACKEND` |")]
    if len(rows) != 1:
        raise AssertionError(f"{_WHERE}, Step 2: {len(rows)} BACKEND rows, expected 1")
    return rows[0]


def _sample_problems(block: list[str], backend_row: str) -> list[str]:
    """What no longer holds of the account of the counters that the reference gives."""
    problems: list[str] = []
    for name, word in (("DOCS", ".ai"), ("TOOLING", "tests")):
        lines = [line for line in block if line.startswith(f"{name}=$(")]
        if len(lines) != 1:
            problems.append(
                f"the sample has {len(lines)} {name} counter lines, expected 1"
            )
        elif word not in lines[0]:
            problems.append(f"the sample's {name} counter no longer counts {word!r}")
    if "tests that gate it" not in _words(backend_row):
        problems.append(
            "Step 2's BACKEND row no longer says it holds the tests that gate it"
        )
    return problems


def test_the_sentence_about_the_sample_counters_is_still_true() -> None:
    skill = _SKILL.read_text(encoding="utf-8")
    block = _classifier_block(_section(skill, "## Step 6 ", _WHERE))
    row = _backend_row(_section(skill, "## Step 2 ", _WHERE))
    problems = _sample_problems(block, row)
    assert not problems, "; ".join(problems)

    # Known positives: each way the sentence could go stale is reported, the control is not.
    docs = [
        line.replace("|\\.ai", "") if line.startswith("DOCS=$(") else line
        for line in block
    ]
    tooling = [
        line.replace("|tests", "") if line.startswith("TOOLING=$(") else line
        for line in block
    ]
    assert docs != block and tooling != block, "a planted block changed nothing"
    assert _sample_problems(docs, row), "a DOCS counter without .ai went unreported"
    assert _sample_problems(tooling, row), (
        "a TOOLING counter without tests went unreported"
    )
    assert _sample_problems(block, "| `BACKEND` | Production runtime code |")
    assert _sample_problems(
        [line for line in block if not line.startswith("DOCS=$(")], row
    )
    # Near misses: a re-wrapped, re-cased row and a re-ordered block stay clean.
    assert (
        _sample_problems(block, "| `BACKEND` | Code and\n the Tests That\n Gate It |")
        == []
    )
    assert _sample_problems(list(reversed(block)), row) == []
    with pytest.raises(AssertionError, match="0 fenced blocks hold the class counters"):
        _classifier_block("```text\nother\n```\n")
    with pytest.raises(AssertionError, match="0 BACKEND rows"):
        _backend_row("| `DOCS` | prose |")


# --- the request ids ----------------------------------------------------------------------


def test_the_references_carry_no_request_id() -> None:
    # Planted ids are built from fragments, so this file holds none.
    planted = (
        "A" + "38",
        "K-" + "9",
        "F" + "6",
        "C-" + "3",
        "DEC-" + "4",
        "KIT-" + "12",
        "KIT" + "12",
    )
    for token in planted:
        assert _REQUEST_ID.search(f"see {token}, the rest"), f"the scan missed {token}"
    for near in ("A1c", "PA38", "layer 38", "Kit 12", "a-38", "CA9"):
        assert not _REQUEST_ID.search(f"see {near}, the rest"), (
            f"the scan flagged {near}"
        )
    scanned = {
        name: _REQUEST_ID.findall(_read(_reference(name)))
        for name in (_TRIGGERS, _MECHANICS)
    }
    assert len(scanned) == 2
    assert not any(scanned.values()), scanned
