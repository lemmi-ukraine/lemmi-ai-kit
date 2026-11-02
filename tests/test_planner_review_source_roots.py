"""The planning and review skills name their source roots and sample gates as one repository's.

Three places carried one repository's directory or gates as though every project had them.
`initiative-planner`'s chokepoint search listed a literal source directory after `--`, where the
command is an instruction and the directory is the project's own. The findings-report example in
`branch-diff-review` showed a lint run on one directory and a test run that was not made, and
`pr-review-concise`'s table of known false positives named a lint scope, a type-check scope and a
source tree, none of which was said to be that repository's. The planner's token becomes a
placeholder, and each of the two examples gains one line that says what it is. The examples
themselves stay as they were: a reader still sees what a real gate line looks like.

What each test asserts:

* `test_the_chokepoint_search_names_a_placeholder_for_the_source_roots` reads the one fenced
  block in Step 4 of the planner that holds the planned-work search, and its pathspec.
* `test_the_findings_example_labels_its_gates_as_one_repositorys` and
  `test_the_false_positive_table_labels_its_gates_as_one_repositorys` read the text that
  introduces the example (before its fence) and the text that introduces the table (before its
  first row), and look for a label that says its gate commands are one repository's examples.
* `test_the_findings_example_keeps_its_sample_gates` and
  `test_the_false_positive_table_keeps_its_gate_rows` are NOT red on the old files: the examples
  are meant to stay. They hold the change to a label, so a label cannot become a rewrite.
* The instrument tests fire the readers and the checks at planted text, so their silence on the
  real files means something. A label is planted after the thing it labels, and as two phrases
  in different sentences, and neither is accepted.

The planner's line count is held by the skill audit's cap, not by a number here: a number would
fail a later, legitimate edit of a file that has no room to spare.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "orchestration" / "skills"
_PLANNER = _ROOT / "initiative-planner" / "SKILL.md"
_FINDINGS = _ROOT / "branch-diff-review" / "references" / "findings-report-format.md"
_REVIEW = _ROOT / "pr-review-concise" / "SKILL.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
# What follows a bare `--` up to the end of the command: a pipe, a semicolon or `&&` ends it.
_BARE_PATHSPEC = re.compile(r"(?:^|\s)--\s+(.+?)\s*$")
_END_OF_COMMAND = re.compile(r"\s*(?:\||;|&&)")
_PLACEHOLDER = re.compile(r"^<[a-z][a-z-]*>$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

_SOURCE_ROOTS = "<source-roots>"
# The words every label carries; each file's label also has to sit where its example starts.
_LABEL_PHRASES: tuple[str, ...] = ("gate commands", "one repository's examples")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text with every run of whitespace, line breaks included, as one space."""
    return " ".join(text.split())


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


def _search_block(section: str, where: str) -> list[str]:
    """The lines of the one fenced block of `section` that holds the planned-work search."""
    holding = [
        block
        for block in _fenced_blocks(section)
        if any(line.startswith("git grep") for line in block)
    ]
    if len(holding) != 1:
        raise AssertionError(
            f"{where}: {len(holding)} fenced blocks hold a git grep, expected 1"
        )
    return holding[0]


def _pathspec_problems(block: list[str]) -> list[str]:
    """Every `git grep` line whose pathspec after a bare `--` is not a placeholder.

    A flag that starts with two hyphens is not a bare `--`, so the log line beside the search
    is not read. A search with no `--` at all has no pathspec to be wrong and is not flagged.
    """
    problems: list[str] = []
    for line in block:
        if not line.startswith("git grep"):
            continue
        match = _BARE_PATHSPEC.search(line)
        if match is None:
            continue
        pathspecs = _END_OF_COMMAND.split(match.group(1))[0].split()
        problems += [
            f"a literal pathspec after '--': {pathspec!r}"
            for pathspec in pathspecs
            if _PLACEHOLDER.match(pathspec) is None
        ]
    return problems


def _before_first_fence(section: str) -> str:
    """The text of `section` after its heading line and before its first fence line."""
    kept: list[str] = []
    for line in section.split("\n")[1:]:
        if _is_fence(line):
            break
        kept.append(line)
    return "\n".join(kept)


def _before_first_row(section: str) -> str:
    """The text of `section` after its heading line and before its first table row."""
    kept: list[str] = []
    for line in section.split("\n")[1:]:
        if line.startswith("|"):
            break
        kept.append(line)
    return "\n".join(kept)


def _label_problems(introduction: str) -> list[str]:
    """What is missing from the text that introduces an example: one sentence, both phrases."""
    for sentence in _SENTENCE_END.split(_fold(introduction)):
        lowered = sentence.lower()
        if all(phrase in lowered for phrase in _LABEL_PHRASES):
            return []
    return [
        f"no one sentence says {list(_LABEL_PHRASES)}; the text is {_fold(introduction)!r}"
    ]


def _findings_gates() -> str:
    return _section(_text(_FINDINGS), "### 2. Gates", "findings-report-format.md")


def _false_positives() -> str:
    return _section(_text(_REVIEW), "## Step 7 ", "pr-review-concise SKILL.md")


# --- the change ---------------------------------------------------------------------------


def test_the_chokepoint_search_names_a_placeholder_for_the_source_roots() -> None:
    section = _section(_text(_PLANNER), "## Step 4 ", "initiative-planner SKILL.md")
    block = _search_block(section, "initiative-planner SKILL.md, Step 4")
    problems = _pathspec_problems(block)
    assert not problems, "initiative-planner SKILL.md, Step 4: " + "; ".join(problems)
    searches = [line for line in block if line.startswith("git grep")]
    assert len(searches) == 1 and searches[0].endswith(f" -- {_SOURCE_ROOTS}"), (
        f"the planned-work search does not end on ' -- {_SOURCE_ROOTS}': {searches}"
    )


def test_the_findings_example_labels_its_gates_as_one_repositorys() -> None:
    problems = _label_problems(_before_first_fence(_findings_gates()))
    assert not problems, "findings-report-format.md, section 2: " + "; ".join(problems)


def test_the_false_positive_table_labels_its_gates_as_one_repositorys() -> None:
    problems = _label_problems(_before_first_row(_false_positives()))
    assert not problems, "pr-review-concise SKILL.md, Step 7: " + "; ".join(problems)


def test_the_findings_example_keeps_its_sample_gates() -> None:
    block = " ".join(_fenced_blocks(_findings_gates())[0])
    for kept in ("ruff", "check backend", "basedpyright <paths>", "pytest was NOT run"):
        assert kept in _fold(block), f"the sample gate block lost {kept!r}"


def test_the_false_positive_table_keeps_its_gate_rows() -> None:
    rows = _fold(
        " ".join(
            line for line in _false_positives().split("\n") if line.startswith("|")
        )
    )
    for kept in ("ruff check backend tests", 'include = ["backend", "tests"]'):
        assert kept in rows, f"the false-positive table lost {kept!r}"


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_what_it_claims() -> None:
    for path in (_PLANNER, _FINDINGS, _REVIEW):
        assert path.is_file(), f"{path.name} is not where the test looks"
        assert _text(path).count("\n") > 150, f"{path.name} is nearly empty"
    section = _section(_text(_PLANNER), "## Step 4 ", "initiative-planner SKILL.md")
    assert len(_fenced_blocks(section)) >= 1, "Step 4 lost its fenced block"
    assert len(_fenced_blocks(_findings_gates())) == 1, (
        "section 2 lost its one sample block"
    )
    table_rows = [
        line for line in _false_positives().split("\n") if line.startswith("|")
    ]
    assert len(table_rows) > 5, "Step 7's table is nearly empty"


_SEARCH = (
    "# Existing history: which file do most commits touch?",
    "git log --format= --name-only <base>..<tip> | sort | uniq -c | sort -rn | head",
    "",
    "# Planned work: does one file host the symbols two workstreams both need?",
    'git grep -n "<symbolA>\\|<symbolB>" -- ' + _SOURCE_ROOTS,
)


def _with_pathspec(pathspec: str) -> list[str]:
    return [*_SEARCH[:-1], 'git grep -n "<symbolA>\\|<symbolB>" -- ' + pathspec]


@pytest.mark.parametrize(
    "pathspec", ["back" + "end/", "src/", "app", "src lib", "'*.cs'", "back" + "end"]
)
def test_the_pathspec_check_sees_a_planted_literal_directory(pathspec: str) -> None:
    assert _pathspec_problems(list(_SEARCH)) == [], "the control is not clean"
    assert _pathspec_problems(_with_pathspec(pathspec)), f"missed {pathspec!r}"


@pytest.mark.parametrize("pathspec", ["<source-roots>", "<roots>", "<source-root>"])
def test_the_pathspec_check_accepts_a_placeholder(pathspec: str) -> None:
    assert _pathspec_problems(_with_pathspec(pathspec)) == []


def test_the_pathspec_check_is_silent_on_flags_and_on_a_search_with_no_pathspec() -> (
    None
):
    block = [
        "git log --format= --name-only <base>..<tip> | sort | uniq -c | sort -rn | head",
        'git grep -n "<symbolA>"',
        "git grep --name-only <symbolA> | head",
    ]
    assert _pathspec_problems(block) == []


def test_the_search_reader_fails_loudly() -> None:
    planted = "## Step 4\n\n```bash\ngit log --oneline\n```\n"
    with pytest.raises(AssertionError, match="0 fenced blocks hold a git grep"):
        _search_block(planted, "planted")
    twice = (
        planted
        + "\n```bash\ngit grep -n a -- x\n```\n\n```bash\ngit grep -n b -- y\n```\n"
    )
    with pytest.raises(AssertionError, match="2 fenced blocks hold a git grep"):
        _search_block(twice, "planted")
    one = "## Step 4\n\n```bash\n" + "\n".join(_SEARCH) + "\n```\n"
    assert _search_block(one, "planted") == list(_SEARCH)


_FINDINGS_LEAD_IN = "The most valuable line in the source report was an admission"
_FINDINGS_LABEL = "the gate commands below are one repository's examples; use the ones your project runs"
_FENCE = "```markdown\n**Gates run:** `ruff check backend` -> exit 0\n```"


def _gates_section(introduction: str, after_fence: str = "") -> str:
    return f"### 2. Gates\n\n{introduction}\n\n{_FENCE}\n{after_fence}\n"


def test_the_findings_label_check_sees_the_old_text_and_accepts_the_new() -> None:
    labelled = _gates_section(f"{_FINDINGS_LEAD_IN} ({_FINDINGS_LABEL}):")
    old = _gates_section(f"{_FINDINGS_LEAD_IN}:")
    assert _label_problems(_before_first_fence(labelled)) == [], (
        "the control is not clean"
    )
    assert _label_problems(_before_first_fence(old)), "the check missed the old text"
    wrapped = _gates_section(
        f"{_FINDINGS_LEAD_IN} (the gate commands below\nare one\nrepository's examples):"
    )
    assert _label_problems(_before_first_fence(wrapped)) == [], (
        "a re-wrap changed the verdict"
    )


def test_a_label_after_the_example_or_split_over_sentences_is_not_accepted() -> None:
    after = _gates_section(
        f"{_FINDINGS_LEAD_IN}:", after_fence=f"Note: {_FINDINGS_LABEL}."
    )
    assert _label_problems(_before_first_fence(after)), (
        "a label after the fence was accepted"
    )
    split = _gates_section(
        f"{_FINDINGS_LEAD_IN}. The gate commands vary. This is one repository's examples."
    )
    assert _label_problems(_before_first_fence(split)), (
        "two sentences were read as one label"
    )
    other = _gates_section(
        f"{_FINDINGS_LEAD_IN}: one repository's examples of a report."
    )
    assert _label_problems(_before_first_fence(other)), (
        "a label that names no gates was accepted"
    )


_TABLE = (
    "| # | Pattern | Why |\n|---|---|---|\n| 1 | `ruff check backend tests` | scope |\n"
)


def _step_seven(introduction: str) -> str:
    return f"## Step 7 - Known false positives\n\n{introduction}\n\n{_TABLE}\nAfter the table.\n"


def test_the_review_label_check_sees_the_old_text_and_accepts_the_new() -> None:
    old = _step_seven("Do not flag these. Each has cost a real round-trip.")
    new = _step_seven(
        "Do not flag these. Each has cost a real round-trip.\n"
        "The gate commands and paths in this table are one repository's examples."
    )
    assert _label_problems(_before_first_row(new)) == [], "the control is not clean"
    assert _label_problems(_before_first_row(old)), "the check missed the old text"
    after_table = old + "The gate commands in it are one repository's examples.\n"
    assert _label_problems(_before_first_row(after_table)), (
        "a label after the table counted"
    )


def test_the_section_and_slice_readers_fail_loudly_and_stop_where_they_claim() -> None:
    planted = "\n".join(
        [
            "### 2. Gates - alpha",
            "intro text",
            "```markdown",
            "# a comment inside a fence is not a heading",
            "```",
            "after the fence",
            "### 3. Coverage",
            "coverage body",
        ]
    )
    section = _section(planted, "### 2. Gates", "planted")
    assert "after the fence" in section and "coverage body" not in section
    assert _before_first_fence(section) == "intro text"
    assert _before_first_row("## H\nbefore\n| a |\nafter") == "before"
    with pytest.raises(AssertionError, match="no heading starting"):
        _section(planted, "### 9.", "planted")
