"""Five descriptions of what a reference holds were left behind when it grew, and are pinned here.

A reference gained an example, a section or a dimension, and the line that points at it kept
describing the file as it was: a list of three kinds of example with a fourth written, a pointer
that names two things where the file holds three, a count of four cases beside four more, a step
named for five dimensions over a file of seven. A fifth was never a count. Three review texts
named one repository's lint command as the gate, so a reader in another project was told that a
command it does not have is canonical, and the rule on a bare timeout decorator read as if every
project had those decorators.

What each test asserts:

* `test_the_text_states_the_claim` reads the row's file (lower-cased, whitespace collapsed) and
  looks for the corrected phrases and for the old ones. Two claims remove nothing (a bullet and a
  sentence are added), so their rows hold phrases that must be there and none that must be gone.
  The last row reads the sync record: a refresh re-applies only what a skill's note names, so
  each edited skill's row says what was changed here.
* The four count tests derive the number from the reference the line describes (the example
  headings, the section that was added, the numbered cases and the bullets of the closing
  section, the dimension headings) and compare it with the pointer, so a reference that grows
  again turns a test red instead of leaving a second generation of the same leftover.
* The instrument tests fire the readers and the checks at planted text, so their silence on the
  real files means something.

The lint example's own sample lines stay: `test_planner_review_source_roots.py` holds them to the
label that says they are one repository's. The rows here pin only the claims around them.

THE SURFACE, in numbers the tests assert: 9 rows over 8 files, 19 phrases that must be there and
9 that must be gone, and 4 references read for a count.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CORE = "plugins/core/skills"
_ORCHESTRATION = "plugins/orchestration/skills"
_PYTHON = "plugins/python/skills"

_ANALYZE_LOGS = f"{_CORE}/analyze-logs/SKILL.md"
_ANALYSIS_EXAMPLES = f"{_CORE}/analyze-logs/references/analysis-examples.md"
_METRIC_VALIDITY = f"{_CORE}/metric-validity-check/SKILL.md"
_JOIN_DIAGNOSTICS = f"{_CORE}/metric-validity-check/references/join-diagnostics.md"
_POST_TASK_REVIEW = f"{_CORE}/post-task-review/SKILL.md"
_CLAIM_BOUNDARIES = f"{_CORE}/post-task-review/references/claim-boundaries.md"
_PLAN_CRITIC = f"{_CORE}/plan-critic/SKILL.md"
_REVIEW_DIMENSIONS = f"{_CORE}/plan-critic/references/review-dimensions.md"
_FINDINGS_FORMAT = (
    f"{_ORCHESTRATION}/branch-diff-review/references/findings-report-format.md"
)
_PR_REVIEW = f"{_ORCHESTRATION}/pr-review-concise/SKILL.md"
_PYTHON_CONVENTIONS = f"{_PYTHON}/python-conventions/SKILL.md"
_SYNC_RECORD = "docs/upstream-sync.toml"

# The text carries this character; it is built from its code point so that a retyped one in an
# old excerpt cannot make a check that sees nothing look as if it works.
_SECTION = chr(0xA7)
_PROJECT_LINT = f"the project's lint command (agents.md {_SECTION} commands)"
_WIDER_SCOPE = (
    "can exit 0 over its own scope while a wider scope exits 1 on pre-existing"
)

_NUMBER_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
)
_COUNT_BEFORE_DIMENSIONS = re.compile(
    rf"\b({'|'.join(_NUMBER_WORDS[1:])})\s+dimensions\b", re.IGNORECASE
)

# (claim, file, phrases that must be there, phrases that must be gone); every phrase lower-cased,
# whitespace collapsed. A claim that only adds a sentence has no phrase to be gone.
_ROWS: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "1: the findings report's scope bullet points at the project's lint command",
        _FINDINGS_FORMAT,
        (f"{_PROJECT_LINT} {_WIDER_SCOPE} violations",),
        ("`ruff check backend` exits 0 while",),
    ),
    (
        "1: the review table's lint row points at the project's lint command",
        _PR_REVIEW,
        (f"the gate, {_PROJECT_LINT}, exits 0. name the scope.",),
        ("`ruff check backend` is the canonical gate",),
    ),
    (
        "1: the Python conventions' linting scope names the project's lint command",
        _PYTHON_CONVENTIONS,
        (
            f"{_PROJECT_LINT} {_WIDER_SCOPE} violations",
            "confirm violations outside that scope predate your branch",
        ),
        (
            "`ruff check backend` (the canonical gate)",
            "35 pre-existing violations across 25 files",
        ),
    ),
    (
        "1: the bare-decorator rule holds where the project defines the decorators",
        _PR_REVIEW,
        ("always flag, where the project defines them.**",),
        ("always flag.**",),
    ),
    (
        "2: the log-analysis pointer lists the join example",
        _ANALYZE_LOGS,
        ("an absence found by a join, with its overall match count vs. a bare zero",),
        (),
    ),
    (
        "3: the metric-validity pointer names the section on counting commands",
        _METRIC_VALIDITY,
        ("linkage detail, the write-up format, and counting recorded commands",),
        ("linkage detail and the write-up format",),
    ),
    (
        "4: the post-task-review pointer names the shorter cases",
        _POST_TASK_REVIEW,
        (
            "it also holds four shorter cases, where a status word or a figure stood in "
            "for what it summarises",
        ),
        (),
    ),
    (
        "5: the plan-critic step counts the dimensions the reference holds",
        _PLAN_CRITIC,
        (
            "run the seven dimensions",
            "after the dimensions, answer these six questions regardless of scope",
            "coherence is what the dimensions check",
        ),
        (
            "run the five dimensions",
            "after the five dimensions",
            "what the five dimensions check",
        ),
    ),
    (
        "notes: each edited upstream-origin skill records what was changed here",
        _SYNC_RECORD,
        (
            "the pointer to references/analysis-examples.md lists example 4",
            "scope bullet points at the project's lint command",
            "names the section on counting recorded commands",
            "step 2's heading says seven dimensions",
            "pointer to references/claim-boundaries.md also names the file's four shorter cases",
            "step 7's lint-scope row points at the project's lint command",
            "the rule on a bare timeout decorator applies where the project defines them",
            "the linting scope section points at the project's lint command",
        ),
        (),
    ),
)


def _raw(relative: str) -> str:
    return (_ROOT / relative).read_text(encoding="utf-8")


def _words(relative: str) -> str:
    return " ".join(_raw(relative).split()).lower()


def _problems(
    text: str, present: tuple[str, ...], absent: tuple[str, ...]
) -> list[str]:
    missing = [f"missing: {phrase}" for phrase in present if phrase not in text]
    returned = [f"old wording present: {phrase}" for phrase in absent if phrase in text]
    return missing + returned


def _count(text: str, pattern: str, what: str) -> int:
    """How many lines of `text` match `pattern`. None is an error: a renamed heading must fail."""
    found = len(re.findall(pattern, text, re.MULTILINE))
    assert found > 0, f"no {what} found by {pattern!r}"
    return found


def _word(count: int) -> str:
    assert 0 < count < len(_NUMBER_WORDS), f"no number word for {count}"
    return _NUMBER_WORDS[count]


def _section_bullets(text: str, heading_containing: str) -> list[str]:
    """The top-level bullets under the first `##` heading that contains a phrase, up to the next."""
    inside = False
    bullets: list[str] = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if inside:
                break
            inside = heading_containing in line.lower()
        elif inside and line.startswith("- "):
            bullets.append(line)
    assert inside, f"no '##' heading that contains {heading_containing!r}"
    return bullets


def _pointer_bullets(text: str, link: str) -> list[str]:
    """The bullet lines that follow the one line that links `link`."""
    lines = text.split("\n")
    pointers = [i for i, line in enumerate(lines) if link in line]
    assert len(pointers) == 1, (
        f"{len(pointers)} lines link {link!r}, expected one pointer line"
    )
    bullets: list[str] = []
    for line in lines[pointers[0] + 1 :]:
        if not line.startswith("- "):
            break
        bullets.append(line)
    return bullets


def _list_item(text: str, link: str) -> str:
    """The one list item that opens with a link to `link`, with its wrapped lines, folded."""
    lines = text.split("\n")
    opens = [
        i for i, line in enumerate(lines) if line.startswith("- [") and link in line
    ]
    assert len(opens) == 1, f"{len(opens)} list items open with {link!r}, expected one"
    item = [lines[opens[0]]]
    for line in lines[opens[0] + 1 :]:
        if not line.startswith("  "):
            break
        item.append(line)
    return " ".join(" ".join(item).split()).lower()


_REFERENCES = (
    _ANALYSIS_EXAMPLES,
    _JOIN_DIAGNOSTICS,
    _CLAIM_BOUNDARIES,
    _REVIEW_DIMENSIONS,
)


def test_the_surface_is_stated_in_numbers() -> None:
    files = {path for _, path, _, _ in _ROWS}
    present = [phrase for _, _, kept, _ in _ROWS for phrase in kept]
    absent = [phrase for _, _, _, gone in _ROWS for phrase in gone]
    assert (len(_ROWS), len(files), len(present), len(absent)) == (9, 8, 19, 9)
    assert len(_REFERENCES) == 4
    references = _REFERENCES
    unreadable = [
        name for name in (*files, *references) if not (_ROOT / name).is_file()
    ]
    assert not unreadable, (
        f"{len(unreadable)} files are not where the test looks: {unreadable}"
    )


@pytest.mark.parametrize(
    ("claim", "path", "present", "absent"), _ROWS, ids=[row[0] for row in _ROWS]
)
def test_the_text_states_the_claim(
    claim: str, path: str, present: tuple[str, ...], absent: tuple[str, ...]
) -> None:
    problems = _problems(_words(path), present, absent)
    assert not problems, f"{path} does not hold {claim!r}: {problems}"


def test_the_log_analysis_pointer_lists_one_kind_per_example() -> None:
    examples = _count(
        _raw(_ANALYSIS_EXAMPLES), r"^### Example \d+:", "example headings"
    )
    kinds = _pointer_bullets(_raw(_ANALYZE_LOGS), "references/analysis-examples.md")
    assert len(kinds) == examples, (
        f"the reference holds {examples} examples and the pointer lists {len(kinds)} kinds: "
        f"{kinds}"
    )


def test_the_metric_validity_pointer_names_the_section_the_reference_added() -> None:
    heading = re.search(
        r"^## (Counting recorded commands)\b", _raw(_JOIN_DIAGNOSTICS), re.MULTILINE
    )
    assert heading is not None, (
        "join-diagnostics.md lost its section on counting commands"
    )
    pointer = _list_item(_raw(_METRIC_VALIDITY), "references/join-diagnostics.md")
    assert heading.group(1).lower() in pointer, (
        f"the pointer does not name {heading.group(1)!r}: {pointer!r}"
    )


def test_the_post_task_review_pointer_counts_both_groups_of_cases() -> None:
    reference = _raw(_CLAIM_BOUNDARIES)
    measured = _count(reference, r"^## \d+\. ", "numbered case headings")
    shorter = len(_section_bullets(reference, "shorter cases"))
    assert shorter > 0, "the closing section of shorter cases holds no bullet"
    pointer = _words(_POST_TASK_REVIEW)
    for count, kind in ((measured, "measured"), (shorter, "shorter")):
        phrase = f"{_word(count)} {kind} cases"
        assert phrase in pointer, (
            f"the reference holds {count} {kind} cases: no {phrase!r}"
        )


def test_every_count_of_the_dimensions_is_the_number_the_reference_holds() -> None:
    held = _count(_raw(_REVIEW_DIMENSIONS), r"^## Dimension \d+ ", "dimension headings")
    stated = [m.lower() for m in _COUNT_BEFORE_DIMENSIONS.findall(_raw(_PLAN_CRITIC))]
    heading = re.search(
        r"^### Step 2 \S+ Run the (\w+) Dimensions$", _raw(_PLAN_CRITIC), re.MULTILINE
    )
    assert heading is not None, "plan-critic lost its Step 2 heading"
    assert stated, "plan-critic states no count of dimensions"
    wrong = [word for word in stated if word != _word(held)]
    assert not wrong, (
        f"the reference holds {held} dimensions; plan-critic says {stated}"
    )
    assert heading.group(1).lower() == _word(held), (
        f"the Step 2 heading says {heading.group(1)}, the reference holds {held}"
    )


def test_every_phrase_is_reported_when_it_goes_or_returns() -> None:
    """Planted removal and return, on text built from the row so it holds whatever the files say:
    each phrase cut out in turn is the one gap reported, and each old phrase added is the one
    return. A phrase the check cannot see go would let a line lose its claim and stay green."""
    for claim, _, present, absent in _ROWS:
        text = "an opening sentence. " + " and ".join(present) + ". a closing one."
        assert not _problems(text, present, absent), f"{claim!r} does not hold"
        for phrase in present:
            assert _problems(text.replace(phrase, ""), present, absent) == [
                f"missing: {phrase}"
            ], (claim, phrase)
        for phrase in absent:
            assert _problems(f"{text} {phrase}", present, absent) == [
                f"old wording present: {phrase}"
            ], (claim, phrase)
        assert _problems("", present, ()) == [f"missing: {p}" for p in present], claim


def test_the_readers_fail_loudly_and_stop_where_they_claim() -> None:
    with pytest.raises(AssertionError, match="no example headings"):
        _count("nothing", r"^### Example \d+:", "example headings")
    with pytest.raises(AssertionError, match="no number word for 0"):
        _word(0)
    with pytest.raises(AssertionError, match="no number word for 13"):
        _word(13)
    with pytest.raises(AssertionError, match="expected one pointer line"):
        _pointer_bullets("no link here", "references/x.md")
    with pytest.raises(AssertionError, match="2 lines link"):
        _pointer_bullets(
            "[a](references/x.md)\n[b](references/x.md)", "references/x.md"
        )
    with pytest.raises(AssertionError, match="no '##' heading"):
        _section_bullets("## One\n- a\n", "shorter cases")
    planted = "## Four shorter cases: x\n- one\n  cont\n- two\n## Next\n- not counted\n"
    assert _section_bullets(planted, "shorter cases") == ["- one", "- two"]
    pointer = "See [x](references/x.md) for:\n- a\n- b\n\n- not part of it\n"
    assert _pointer_bullets(pointer, "references/x.md") == ["- a", "- b"]
    related = "- [a](references/x.md) - one\n  two\n- [b](references/y.md) - three\n"
    assert _list_item(related, "references/x.md") == "- [a](references/x.md) - one two"
    with pytest.raises(AssertionError, match="0 list items open with"):
        _list_item("[a](references/x.md) not a list item\n", "references/x.md")
    assert [
        m.lower() for m in _COUNT_BEFORE_DIMENSIONS.findall("Run the Five Dimensions")
    ] == ["five"]
