"""Subsection 12m of the shared-index reference tells writers side by side what to do, and its
pointer in the safety skill names it.

The reference told a session how to stage, how to commit, how to hand a file back and how to name
a peer. It said nothing to two sessions that build one change side by side in one checkout: who
may create a file and who may stage, what a spoken confirmation is worth a minute later, where a
result that will be reported must be run, and how to show that the staged work is the work that
was tested. Subsection 12m says it in four paragraphs, one claim each:

* the session that writes the tests adds new files only, each created by an operation that fails
  if the path exists; exactly one session owns the index and the order of commits; a changed
  shared path is announced by re-running the content-hash list of 12g;
* a confirmation is a snapshot: before every tree stamp, staging and run on the live tree the
  branch, the commit and the staged list are read again and compared with what was recorded; a
  difference is a stop, read from the reflog, and switching back waits for the operator's word;
* a result that will be reported runs on a copy or on an export of a recorded commit or tree id,
  never on a snapshot of the live tree; a red proof is an export plus the new test files;
* staged work is stamped with `git write-tree` and compared by path before the commit; a stamp is
  a write to the shared index, so a session that does not own the index builds the tree in a
  private copy of the index file.

THE SURFACE, in numbers the tests assert: 4 claims and 37 phrases over 1 subsection of 1
reference, plus 4 pointer phrases in the one pointer of `SKILL.md`. A claim holds when every one
of its phrases is in subsection 12m (bold marks dropped, whitespace collapsed, lower-cased); a
phrase that sits in another subsection does not count, because the subsection is cut out first
and a heading that is not found fails by name. Each phrase is fired at a planted removal, three
commands are fired at a planted wrong form, and the checks of the pointer, the line cap, the
machine paths and the assignment-led command each have a planted positive and a near-miss.

What these tests do not do: they read text. That the printed commands do what the subsection says
is run, once each, in `test_shared_tree_recipes.py`, which also ties the commands it runs to the
ones printed here.
"""

import re
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SAFETY = (
    _REPO_ROOT / "plugins" / "orchestration" / "skills" / "parallel-session-safety"
)
_REFERENCE = _SAFETY / "references" / "shared-index-protocol.md"
_SKILL = _SAFETY / "SKILL.md"

_HEADING = "### 12m."
_POINTER_HEADING = "## 12."
_SKILL_LINE_CAP = 499
_REFERENCE_FLOOR = 13

_SECT = chr(0xA7)
_MD_HEADING = re.compile(r"^(#{1,6})\s")
_SUBSECTION = re.compile(r"^### (12[a-z])\.", re.MULTILINE)
_QUOTE_MARK = re.compile(r"^>\s?")
_FENCED_BLOCK = re.compile(r"^```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)
_FENCED_WHOLE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_SPAN = re.compile(r"`([^`\n]+)`")
_ASSIGNMENT_LED = re.compile(r"^(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*=\S*\s+\S")


class _Claim(NamedTuple):
    name: str
    phrases: tuple[str, ...]


_CLAIMS: tuple[_Claim, ...] = (
    _Claim(
        "a: the test writer adds new files only, and one session owns the index and the commits",
        (
            "the session that writes the tests adds new files only",
            "each created by an operation that fails if the path exists (12k)",
            "goes to the session that owns the index, as a patch written with "
            "`git diff --output` (12j)",
            "exactly one session owns the index and the order of commits",
            "the other writes files and stages nothing (12b)",
            "re-runs the content-hash list of 12g and says so in its return note",
        ),
    ),
    _Claim(
        "c: a confirmation is a snapshot; a difference is a stop; switching back waits",
        (
            "a confirmation is a snapshot",
            "12d re-reads the branch before every commit",
            "immediately before every tree stamp, every staging and every run on the live tree",
            "`git rev-parse --abbrev-ref HEAD` (the branch you were given)",
            "`git rev-parse HEAD` (the commit your evidence was built on)",
            "`git diff --cached --name-only` (the staged list: empty, or your own paths)",
            "the value your brief or your last stamp recorded",
            "any difference is a stop",
            "`git reflog --date=iso -n 20` to see who moved HEAD and when",
            "switch back only on the operator's word that names the branch",
            f"reverts in the working tree the files the peer committed ({_SECT}11)",
        ),
    ),
    _Claim(
        "b: a result to be reported runs on a copy or an export, and a red proof is export plus overlay",
        (
            "run evidence on a copy",
            "a peer's `git add` of an untracked file changes `git diff HEAD` with no byte moving",
            "an export of a recorded commit or tree id (`git archive <id>`)",
            "write the copy's content hash (12g) or the id beside the result",
            "a red proof runs on an export of the recorded commit with the new test files "
            "copied over it",
            "the green run on an export of the stamped tree",
            "an export has no repository, so a test that calls git fails on both sides: "
            "run those in a clone",
            "never revert a file in the live tree for a before-and-after comparison while "
            "another session runs against it",
        ),
    ),
    _Claim(
        "d: staged work is stamped with the tree, compared by path, and built privately by a non-owner",
        (
            "stamp a proof of staged work with the tree",
            "`git write-tree` prints the id of the tree the index would commit",
            "`git diff --name-only <tested-tree> <tree-now>`",
            "a path list tells apart from your change and a count cannot",
            "`git rev-parse HEAD^{tree}` equals the tested id",
            "`git diff <tested-tree> HEAD -- <paths>` prints nothing",
            "`git write-tree` takes `index.lock` and, after a `git add`, rewrites `.git/index`",
            "a private copy of the index file",
            "for each of the next three commands only (left set, it redirects every later "
            "git command)",
            "`git read-tree HEAD`, `git add -- <your paths>` and `git write-tree`",
            "the id the last one prints is HEAD plus your paths",
            "`.git/index` stays byte-equal",
        ),
    ),
)

# What the section 12 pointer must say about the new subsection and keep from the old ones.
_POINTER_PHRASES = (
    "writers side by side (12m)",
    "(12k)",
    "(12l)",
    "references/shared-index-protocol.md",
)

# A command as printed, the wrong form of it, and nothing else changed: the claim that holds it
# must report exactly the phrases that held the command.
_WRONG_COMMANDS: tuple[tuple[str, str], ...] = (
    (
        "`git diff --name-only <tested-tree> <tree-now>`",
        "`git diff --name-status <tested-tree> <tree-now>`",
    ),
    ("`git rev-parse HEAD^{tree}` equals", "`git rev-parse HEAD` equals"),
    ("`git reflog --date=iso -n 20`", "`git reflog --date=iso`"),
)

# The pointer of section 12 as it stood before 12m: 12l was the last id it named.
_OLD_POINTER = """## 12. The index is shared

> **Exact commands are in [references/shared-index-protocol.md](references/shared-index-protocol.md):**
> per-line contention (12a), a held index (12b), work after staging (12c), "Everything up-to-date" (12d),
> a multi-branch operation (12e), a draft base (12f), content proof (12g), a merge dry run (12h),
> editing a held file (12i), handing a file back (12j), the create collision (12k), naming a peer (12l).

## Cross-references
"""


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _MD_HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _flat(text: str) -> str:
    """Bold marks dropped, whitespace collapsed to one space and lower-cased, so a re-wrapped
    line or a re-emphasised word is not a different sentence."""
    return " ".join(text.replace("**", "").split()).lower()


def _missing(flat: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase.lower() not in flat]


def _subsection() -> str:
    return _section(_read(_REFERENCE), _HEADING)


def _pointer(skill: str) -> str:
    """The quoted lines of section 12, quote marks dropped: the pointer to the reference."""
    lines = _section(skill, _POINTER_HEADING).split("\n")
    return "\n".join(
        _QUOTE_MARK.sub("", line) for line in lines if line.startswith(">")
    )


def _pointer_problems(skill: str) -> list[str]:
    return _missing(_flat(_pointer(skill)), _POINTER_PHRASES)


def _lines(text: str) -> int:
    """What `wc -l` counts: the newline characters."""
    return text.count("\n")


# --- the machine paths and the assignment-led command, as shapes a scan can see -------------------

# Built from fragments, so that this file carries none of what it looks for.
_MACHINE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile("/" + "Users/"), "a macOS home path"),
    (re.compile("/" + r"home/\w"), "a Linux home path"),
    (re.compile(r"[A-Za-z]:[\\/][A-Za-z]\w+"), "a drive-letter path"),
    (re.compile("Windows" + " host"), "a machine-specific host rule"),
    (re.compile(r"\.ai/" + "backups/"), "a backup path"),
)

_PLANTED_PATHS: tuple[tuple[str, str], ...] = (
    ("see " + "/" + "Users/someone/work", "a macOS home path"),
    ("see " + "/" + "home/someone/work", "a Linux home path"),
    ("see " + "C" + ":" + "\\" + "work", "a drive-letter path"),
    ("see " + "D" + ":" + "/" + "work", "a drive-letter path"),
    ("the " + "Windows" + " host", "a machine-specific host rule"),
    ("under " + ".ai/" + "backups/old", "a backup path"),
)

_NEAR_MISS_PATHS = (
    "the staged list: empty, or your own paths",
    "`git rev-parse HEAD^{tree}` equals the tested id",
    "`git diff --name-only <tree-a> <tree-b>`",
    "version 1.2: see section 11, a:b and 12m: x",
    "the C: drive is not a path without a separator after the colon",
)


def _machine_paths(text: str) -> list[str]:
    return [why for pattern, why in _MACHINE_PATTERNS if pattern.search(text)]


def _assignment_led(section: str) -> list[str]:
    """Every line of a fenced block and every inline code span that opens with `NAME=value`
    (an optional `export` first) and has a command after it."""
    fenced = [
        line.strip()
        for block in _FENCED_BLOCK.findall(section)
        for line in block.split("\n")
    ]
    spans = [span.strip() for span in _SPAN.findall(_FENCED_WHOLE.sub("", section))]
    return [item for item in (*fenced, *spans) if _ASSIGNMENT_LED.match(item)]


_PLANTED_ASSIGNMENTS: tuple[tuple[str, str], ...] = (
    ("a fenced first line", "```sh\nGIT_INDEX_FILE=/x git read-tree HEAD\n```\n"),
    ("a fenced later line", "```bash\ngit add -- a\nFOO=bar git commit\n```\n"),
    ("an untagged fence", "```\nexport X=1 && git write-tree\n```\n"),
    ("an inline span", "Run `GIT_INDEX_FILE=/x git add -- a` first.\n"),
    ("an inline span with export", "Run `export X=1 && git write-tree` first.\n"),
)

_NEAR_MISS_ASSIGNMENTS: tuple[tuple[str, str], ...] = (
    (
        "the variable named in prose",
        "Point the `GIT_INDEX_FILE` environment variable at the copy.\n",
    ),
    ("an option form inside a command", "Run `git diff --output=<patch> -- <path>`.\n"),
    ("a fenced command", "```bash\ngit read-tree HEAD\n```\n"),
    ("a comment line", "```sh\n# FOO=bar git x\ngit write-tree\n```\n"),
    ("a bare pair that is notation", "Set `FEATURE=my_feature` first.\n"),
)


# --- the tests ------------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for claim in _CLAIMS for phrase in claim.phrases]
    assert (len(_CLAIMS), len(phrases)) == (4, 37)
    assert len(set(phrases)) == len(phrases), "a phrase is pinned twice"
    assert len(_POINTER_PHRASES) == 4
    for path in (_REFERENCE, _SKILL):
        assert path.is_file(), f"{path.name} is not a file"
    ids = _SUBSECTION.findall(_read(_REFERENCE))
    assert len(ids) >= _REFERENCE_FLOOR, f"{len(ids)} subsections, fewer than the floor"
    assert ids.count("12m") == 1, f"subsection 12m is heading {ids.count('12m')} times"


def test_the_reference_has_the_subsection() -> None:
    """Red before the change: the reference ended at 12l, so there was no section to cut."""
    section = _subsection()
    assert section.strip(), f"{_HEADING} is not in {_REFERENCE.name}"
    assert _lines(section) >= 20, "subsection 12m is too short to carry four paragraphs"


@pytest.mark.parametrize("claim", _CLAIMS, ids=[claim.name for claim in _CLAIMS])
def test_the_subsection_states_the_claim(claim: _Claim) -> None:
    missing = _missing(_flat(_subsection()), claim.phrases)
    assert not missing, (
        f"subsection 12m does not state {claim.name!r}: missing {missing}"
    )


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real subsection in turn is the one gap
    reported, and an empty text lacks every phrase of a claim. A phrase the check could not
    see go would let the subsection lose its claim and stay green."""
    flat = _flat(_subsection())
    for claim in _CLAIMS:
        assert not _missing(flat, claim.phrases), f"{claim.name!r} does not hold"
        for phrase in claim.phrases:
            gone = flat.replace(phrase.lower(), "")
            assert _missing(gone, claim.phrases) == [phrase], (claim.name, phrase)
        assert _missing("", claim.phrases) == list(claim.phrases), claim.name


@pytest.mark.parametrize(("printed", "wrong"), _WRONG_COMMANDS)
def test_a_command_printed_in_a_wrong_form_is_reported(
    printed: str, wrong: str
) -> None:
    """A planted wrong command: the phrases that held the printed form are the ones newly
    reported, whatever else the subsection may already be missing."""
    flat = _flat(_subsection())
    assert printed.lower() in flat, f"{printed!r} is not printed in subsection 12m"
    phrases = tuple(phrase for claim in _CLAIMS for phrase in claim.phrases)
    held = [phrase for phrase in phrases if printed.lower() in phrase.lower()]
    assert held, f"no phrase pins {printed!r}"
    planted = flat.replace(printed.lower(), wrong.lower())
    already = _missing(flat, phrases)
    assert [p for p in _missing(planted, phrases) if p not in already] == held


def test_the_section_12_pointer_names_the_subsection() -> None:
    """The pointer lists every lettered subsection; 12m is one, so it is named there, and the
    ids it named before are still there."""
    skill = _read(_SKILL)
    assert _pointer(skill).strip(), "section 12 of the safety skill has no pointer"
    assert not _pointer_problems(skill), _pointer_problems(skill)
    assert re.search(r"\(12m\)", _pointer(skill)), _pointer(skill)


def test_the_pointer_check_reports_the_old_pointer() -> None:
    """Fired at the pointer as it stood: only the new subsection is missing from it, and a
    pointer that also dropped 12k is reported for both."""
    assert _pointer_problems(_OLD_POINTER) == ["writers side by side (12m)"]
    dropped = _OLD_POINTER.replace("the create collision (12k), ", "")
    assert dropped != _OLD_POINTER, "the planted removal changed nothing"
    assert _pointer_problems(dropped) == ["writers side by side (12m)", "(12k)"]
    repaired = _OLD_POINTER.replace(
        "naming a peer (12l).", "naming a peer (12l), writers side by side (12m)."
    )
    assert repaired != _OLD_POINTER, "the planted repair changed nothing"
    assert _pointer_problems(repaired) == []


def test_the_safety_skill_stays_inside_its_line_cap() -> None:
    """`SKILL.md` has at most 499 lines by `wc -l`: the pointer was re-wrapped in the lines it
    already had, and the detail lives in the reference."""
    lines = _lines(_read(_SKILL))
    assert lines <= _SKILL_LINE_CAP, f"{lines} lines, over the cap of {_SKILL_LINE_CAP}"


def test_the_line_cap_check_reports_a_file_one_line_over() -> None:
    assert _lines("x\n" * _SKILL_LINE_CAP) <= _SKILL_LINE_CAP
    assert _lines("x\n" * (_SKILL_LINE_CAP + 1)) > _SKILL_LINE_CAP
    assert _lines("no newline at the end") == 0


def test_the_subsection_names_no_machine_path() -> None:
    section = _subsection()
    assert section.strip(), f"{_HEADING} is not in {_REFERENCE.name}"
    assert _machine_paths(section) == [], _machine_paths(section)


@pytest.mark.parametrize(("planted", "why"), _PLANTED_PATHS)
def test_the_path_check_sees_each_planted_shape(planted: str, why: str) -> None:
    assert _machine_paths(planted) == [why], planted


@pytest.mark.parametrize("near_miss", _NEAR_MISS_PATHS)
def test_the_path_check_leaves_a_near_miss_alone(near_miss: str) -> None:
    assert _machine_paths(near_miss) == [], near_miss


def test_the_subsection_prints_no_command_led_by_an_assignment() -> None:
    """The variable that redirects the index is named in prose, never written in front of a
    command: a project that switches on the kit's shell-prefix hook refuses that first word."""
    section = _subsection()
    assert section.strip(), f"{_HEADING} is not in {_REFERENCE.name}"
    assert _assignment_led(section) == [], _assignment_led(section)


@pytest.mark.parametrize(
    ("name", "text"), _PLANTED_ASSIGNMENTS, ids=[n for n, _ in _PLANTED_ASSIGNMENTS]
)
def test_the_assignment_check_sees_each_planted_shape(name: str, text: str) -> None:
    assert len(_assignment_led(text)) == 1, f"{name}: {_assignment_led(text)}"


@pytest.mark.parametrize(
    ("name", "text"),
    _NEAR_MISS_ASSIGNMENTS,
    ids=[n for n, _ in _NEAR_MISS_ASSIGNMENTS],
)
def test_the_assignment_check_leaves_a_near_miss_alone(name: str, text: str) -> None:
    assert _assignment_led(text) == [], f"{name}: {_assignment_led(text)}"


_SECTIONS = "\n".join(
    [
        "#### 12m. A look-alike that only contains the wanted prefix",
        "### 12m. First",
        "first body",
        "#### 12m.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "```",
        "### 12n. Second",
        "second body",
        "## 13. Higher",
        "higher body",
        "",
    ]
)


def test_a_section_runs_to_the_next_heading_of_its_level_or_a_higher_one() -> None:
    """The section finder starts at the heading that begins with its text, keeps a deeper heading
    and a `#` line inside a fence, stops at a heading of its own level or a higher one, and
    finds nothing for a heading that is not there."""
    first = _section(_SECTIONS, "### 12m.")
    assert first.startswith("### 12m. First"), first
    for kept in ("first body", "deeper body", "a comment in a fence"):
        assert kept in first, first
    assert "second body" not in first, first
    second = _section(_SECTIONS, "### 12n.")
    assert "second body" in second and "higher body" not in second, second
    assert _section(_SECTIONS, "### 12z.") == ""


def test_the_fold_joins_a_rewrapped_sentence_and_drops_bold_marks() -> None:
    """Every phrase is read through the fold: lines join, a run of spaces is one space, bold marks
    go, the ends are trimmed and the case is dropped."""
    assert _flat("  A **bold**  Word\n     and a second\nline  \n") == (
        "a bold word and a second line"
    )
