"""The test-planning texts name a test form per case, the branch a manual check reaches, the
comparison a boundary row's command runs, and five shapes of vacuous pass where they named three.

Four changes, each stated where the reader who needs it will look:

* A level with more than one test form (plain test functions beside scenario or feature files,
  or hand-written tests beside generated ones) gets a `Style` column, a placement rule the plan
  states in one sentence and a census line. The planner's level-assignment reference holds the
  rule, the plan critic's Dimension 6 asks the question, and both copies of the two seeded
  templates carry the column and the census line, each marked as left out in a one-form project.
* A manual check says which branch the operator's action normally reaches and how often, with
  one step per branch (planner Step 5, critic Dimension 6).
* A command assigned to boundary rows exercises the comparison, not only the threshold table it
  reads, and runs once on the pre-change tree (planner design-techniques reference, critic).
* The vacuous-pass list has five shapes where it had three, in BOTH the planner's Step 4 and the
  critic's Dimension 6. The plan names the tree where a new checker must fail, and the
  reconciliation step counts ids in the task bodies alone.

THE SURFACE, in numbers the tests assert: 8 files (4 skill files, and the 2 seeded templates in
2 copies each), 20 section-scoped claims holding 73 phrases that must be there and 2 that must be
gone, and 2 kept claims. A text is read with emphasis and code marks dropped, whitespace folded
and the case lowered, so a re-wrap or a re-emphasis is the same sentence. The skill files and the
template files are two surfaces and are asserted disjoint: the template copies are also held
byte-equal, a rule that does not apply to a skill file.

What each test asserts:

* `test_each_change_is_stated_where_it_belongs` is one row per claim. A row names one file and
  one section (a label block inside it where the section holds several lists) and the wording
  the old files did not hold; a section or label that is not found fails loudly.
* `test_the_first_three_shapes_stay` is NOT red on the old files: it guards the three shapes the
  lists already named, so a rewrite that adds two cannot drop one.
* The structure tests count what a phrase check cannot: five bullets in the planner's list,
  five numbered shapes in the critic's, a Style column in each of the two case tables, the two
  template pairs equal byte for byte, and the planner's SKILL.md inside its line cap.
* The instrument tests fire every helper at planted text, so their silence on the real files
  means something: a planted removal of each phrase is flagged, a re-wrap or an emphasis mark
  hides nothing, a look-alike does not stand in for a phrase, the old three-shape text is
  flagged by the structure checks and a near-miss is not.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PLANNER = _REPO / "plugins" / "core" / "skills" / "test-planner"
_CRITIC = _REPO / "plugins" / "core" / "skills" / "plan-critic"
_REVIEW = _REPO / "plugins" / "core" / "skills" / "post-task-review"
_SEEDED = (
    _REPO / "plugins" / "core" / "src" / "lemmi_ai_kit" / "assets" / "ai" / "templates"
)
_OWN = _REPO / ".ai" / "templates"

_PLANNER_SKILL = _PLANNER / "SKILL.md"
_LEVELS = _PLANNER / "references" / "level-assignment.md"
_TECHNIQUES = _PLANNER / "references" / "design-techniques.md"
_DIMENSIONS = _CRITIC / "references" / "review-dimensions.md"
_CASES = "test-cases.md"
_PLAN = "test-plan.md"
_COPIES: tuple[tuple[str, Path], ...] = (("seeded", _SEEDED), ("kit-own", _OWN))

_LINE_CAP = 499
_HEADING = re.compile(r"^(#{1,6})\s+\S")
# A line that is nothing but a bold label, as Dimension 6 heads its lists.
_LABEL = re.compile(r"^\*\*[^*]+\*\*\s*$")
_HYPHEN_GAP = re.compile(r"(?<=\w)- (?=\w)")
_QUOTE_MARKER = re.compile(r"^[ \t]*>[ \t]?", re.MULTILINE)
_SEPARATOR = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_NUMBERED = re.compile(r"\((\d)\)")
# The "section" of a template that is the note above its first level-2 heading.
_PREAMBLE = "(note above the first heading)"

_STEP_4_LEAD_IN = "Five shapes to check for:"
_STEP_4_ITEMS = 5
_DIMENSION_6_SHAPES = [1, 2, 3, 4, 5]


@dataclass(frozen=True)
class _Claim:
    """One change: a file, one section of it (and, when `label` is set, the one bold-labelled
    block of that section), the wording that must be there and the words that must not be."""

    key: str
    path: Path
    heading: str
    carries: tuple[str, ...]
    absent: tuple[str, ...] = ()
    label: str | None = None


def _template_claims() -> tuple[_Claim, ...]:
    claims: list[_Claim] = []
    for copy, folder in _COPIES:
        claims += [
            _Claim(
                f"cases-template-{copy}-says-when-to-leave-the-style-column-out",
                folder / _CASES,
                _PREAMBLE,
                carries=(
                    "omit unless a level has more than one test form",
                    "the placement rule and the census are in test-plan.md, under test levels",
                    "one form per level: leave the column out",
                ),
            ),
            _Claim(
                f"plan-template-{copy}-guide-says-when-to-leave-style-and-census-out",
                folder / _PLAN,
                _PREAMBLE,
                carries=(
                    "style column and census line",
                    "omit unless a level has more than one test form",
                    "one form per level: leave both out",
                ),
            ),
            _Claim(
                f"plan-template-{copy}-test-levels-holds-the-census-and-the-rule",
                folder / _PLAN,
                "## Test Levels",
                carries=(
                    "only where a level has more than one test form",
                    "a listing command run now, not from memory",
                    "census: {feature}: {n} {form}",
                    "placement rule: {one sentence",
                    "the form the repository already uses for that kind of flow, read from "
                    "the census, unless the case says why not",
                ),
            ),
        ]
    return tuple(claims)


_CLAIMS: tuple[_Claim, ...] = (
    _Claim(
        "planner-step-3-points-at-the-style-column",
        _PLANNER_SKILL,
        "## Step 3",
        carries=("the exclusion phrasing and the style column",),
    ),
    _Claim(
        "planner-step-4-counts-five-shapes",
        _PLANNER_SKILL,
        "## Step 4",
        carries=("five shapes to check for",),
        absent=("three shapes",),
    ),
    _Claim(
        "planner-step-4-names-the-absence-shape",
        _PLANNER_SKILL,
        "## Step 4",
        carries=(
            "an absence check with no positive precondition",
            "the handler's own evidence that it ran",
        ),
    ),
    _Claim(
        "planner-step-4-names-the-id-coverage-shape",
        _PLANNER_SKILL,
        "## Step 4",
        carries=(
            "an id-coverage check that reads a region restating the ids",
            "a closing paragraph or an index",
            "put that shape in the checker's own fixtures",
        ),
    ),
    _Claim(
        "planner-step-4-has-each-checker-fail-once",
        _PLANNER_SKILL,
        "## Step 4",
        carries=(
            "run every new checker once where the right answer is fail before "
            "trusting its zero",
            "name that tree beside each checker command in the plan",
            "the post-task-review skill covers how to fire a checker at a known positive",
        ),
    ),
    _Claim(
        "planner-step-5-manual-check-names-its-branch",
        _PLANNER_SKILL,
        "## Step 5",
        carries=(
            "a manual check names the branch it reaches",
            "states which branch the operator's action normally reaches and how often "
            "(a measured rate, or unknown)",
            "one step per branch with how to force the rare one",
            "only a test or review proves it",
            "never list as a falsifier a value that the common, correct branch produces",
        ),
    ),
    _Claim(
        "planner-step-7-counts-ids-in-task-bodies-alone",
        _PLANNER_SKILL,
        "## Step 7",
        carries=(
            "count ids in the task bodies alone",
            "never in a closing index that lists them all",
            "the fifth shape in step 4",
        ),
    ),
    _Claim(
        "planner-output-contract-item-5-covers-all-five-shapes",
        _PLANNER_SKILL,
        "## Output Contract",
        carries=(
            "absence checks carry a positive precondition",
            "id-coverage checks read the task bodies alone",
            "each new checker command names the tree where it must fail",
        ),
    ),
    _Claim(
        "levels-style-within-a-level",
        _LEVELS,
        "## Style within a level",
        carries=(
            "style is optional and empty by default",
            "only where a level has more than one test form",
            "plain test functions beside scenario or feature files, or hand-written "
            "tests beside generated or snapshot ones",
            "leaves the column and the census line out",
            "states its placement rule in one sentence",
            "a case goes in the form the repository already uses for that kind of flow, "
            "read from the census, unless the case says why not",
            "one line for the feature and two sibling areas, each counting its tests by form",
            "a listing command run now, not from memory",
            "observed once",
        ),
    ),
    _Claim(
        "techniques-boundary-command-runs-the-comparison",
        _TECHNIQUES,
        "## Equivalence Partitioning + Boundary Value Analysis",
        carries=(
            "a command as the owner",
            "exercise the comparison that decides accept or reject",
            "not only the threshold table it reads",
            "run it once on the pre-change tree",
            "identical output before and after means it cannot see the change",
            "name the edges that stay review-only",
        ),
    ),
    _Claim(
        "critic-dimension-6-counts-five-vacuous-shapes",
        _DIMENSIONS,
        "## Dimension 6",
        label="**Vacuous passes**",
        carries=(
            "five shapes",
            "(1) it iterates a population",
            "(2) its expected result is a falsy value",
            "(3) its precondition cannot hold in the target environment",
            "(4) it is an absence check with no positive precondition",
            "(5) it is an id-coverage check that reads a region restating the ids",
            "was each new checker command run once where the right answer is fail, "
            "and does the plan name that tree?",
        ),
        absent=("three shapes",),
    ),
    _Claim(
        "critic-dimension-6-asks-for-the-owner-in-the-repositorys-form",
        _DIMENSIONS,
        "## Dimension 6",
        label="**Level assignment**",
        carries=(
            "when a level has more than one test form: does every acceptance scenario "
            "that ci can verify have an owner in the form the repository uses for that "
            "kind of flow, per the census? major.",
        ),
    ),
    _Claim(
        "critic-dimension-6-asks-which-branch-a-manual-check-reaches",
        _DIMENSIONS,
        "## Dimension 6",
        label="**Verification method**",
        carries=(
            "does every manual row state which branch the operator's action normally "
            "reaches and how often (a measured rate, or unknown)",
            "one step per branch with how to force the rare one",
            "only a test or review proves it",
            "listed as a falsifier",
        ),
    ),
    _Claim(
        "critic-dimension-6-asks-what-a-boundary-command-exercises",
        _DIMENSIONS,
        "## Dimension 6",
        label="**Technique discipline**",
        carries=(
            "does a command assigned to boundary rows exercise the comparison that "
            "decides accept or reject, not only the threshold table it reads",
            "run once on the pre-change tree (identical output before and after means "
            "it cannot see the change)",
            "the edges that stay review-only named",
        ),
    ),
    *_template_claims(),
)

# Rows that are TRUE ON THE OLD TEXT TOO: the three shapes the lists already named. They guard
# the rewrite that adds two shapes from dropping one, and show no change, so they are not red.
_KEPT: tuple[_Claim, ...] = (
    _Claim(
        "planner-step-4-keeps-the-first-three-shapes",
        _PLANNER_SKILL,
        "## Step 4",
        carries=(
            "empty population.",
            "a falsy expected result with more than one cause.",
            "a precondition that cannot hold in the target environment.",
        ),
    ),
    _Claim(
        "critic-dimension-6-keeps-the-first-three-shapes",
        _DIMENSIONS,
        "## Dimension 6",
        label="**Vacuous passes**",
        carries=(
            "it iterates a population that may be empty and is not guarded",
            "its expected result is a falsy value",
            "that more than one code path produces",
            "its precondition cannot hold in the target environment",
            "so it is skipped rather than run",
        ),
    ),
)

_SKILL_FILES = frozenset({_PLANNER_SKILL, _LEVELS, _TECHNIQUES, _DIMENSIONS})
_TEMPLATE_FILES = frozenset(
    folder / name for _, folder in _COPIES for name in (_CASES, _PLAN)
)
_CLAIM_COUNT = 20
_PHRASE_COUNT = 73
_ABSENT_COUNT = 2
_KEPT_COUNT = 2
_FILE_COUNT = 8


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """The text lower-cased, emphasis and code marks and the quote marker at the start of a
    line dropped, every run of whitespace one space and a break after the hyphen of a word
    joined, so a re-wrap reads the same, inside a quoted note too."""
    marks_dropped = re.sub(r"[*`]", "", _QUOTE_MARKER.sub("", text))
    return _HYPHEN_GAP.sub("-", " ".join(marks_dropped.split())).lower()


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


def _preamble(text: str, where: str) -> str:
    """Everything above the first level-2 heading that is not inside a fence."""
    in_fence = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = _is_fence(line)
        if not in_fence and not fence and line.startswith("## "):
            return "\n".join(found)
        found.append(line)
        if fence:
            in_fence = not in_fence
    raise AssertionError(f"{where}: no level-2 heading, so no note above one to cut")


def _block(section: str, label: str, where: str) -> str:
    """The lines of `section` from the line that is exactly the bold `label` to the next
    bold label, quote line or rule. A label that is not found fails with it named."""
    lines = section.split("\n")
    wanted = _plain(label)
    start = next(
        (
            at
            for at, line in enumerate(lines)
            if _LABEL.match(line) and _plain(line) == wanted
        ),
        None,
    )
    if start is None:
        raise AssertionError(f"{where}: no bold label line {label!r}")
    end = len(lines)
    for at in range(start + 1, len(lines)):
        line = lines[at]
        if _LABEL.match(line) or line.startswith(">") or line.strip() == "---":
            end = at
            break
    return "\n".join(lines[start:end])


def _where(claim: _Claim) -> str:
    place = f"{claim.path.relative_to(_REPO).as_posix()}, section {claim.heading!r}"
    return place if claim.label is None else f"{place}, block {claim.label!r}"


def _slice(text: str, claim: _Claim) -> str:
    """The part of `text` a claim is about: a section or a note, or one block of a section."""
    where = _where(claim)
    if claim.heading == _PREAMBLE:
        part = _preamble(text, where)
    else:
        part = _section(text, claim.heading, where)
    return part if claim.label is None else _block(part, claim.label, where)


def _problems(text: str, claim: _Claim) -> list[str]:
    """What `text` lacks or still says against `claim`; an empty list means nothing."""
    plain = _plain(text)
    problems = [
        f"does not carry {phrase!r}"
        for phrase in claim.carries
        if _plain(phrase) not in plain
    ]
    problems += [
        f"still carries {word!r}" for word in claim.absent if _plain(word) in plain
    ]
    return problems


def _list_items_after(section: str, lead_in: str, where: str) -> list[str]:
    """The top-level `- ` items of the list in the paragraph that follows the one starting
    with `lead_in`. A line that starts with white space continues the item above it, so a
    nested or wrapped line is never a count of its own."""
    paragraphs = [block for block in re.split(r"\n\s*\n", section) if block.strip()]
    wanted = _plain(lead_in)
    starts = [
        at for at, block in enumerate(paragraphs) if _plain(block).startswith(wanted)
    ]
    if len(starts) != 1:
        raise AssertionError(
            f"{where}: {len(starts)} paragraphs start with {lead_in!r}, expected 1"
        )
    items: list[str] = []
    for block in paragraphs[starts[0] + 1 :]:
        if not block.startswith("- "):
            break
        for line in block.split("\n"):
            if line.startswith("- "):
                items.append(line[2:])
            elif items:
                items[-1] += " " + line.strip()
    return [_plain(item) for item in items]


def _numbered_shapes(block: str) -> list[int]:
    """The single-digit labels `(1)`, `(2)`, ... in `block`, in order of appearance."""
    return [int(digit) for digit in _NUMBERED.findall(_plain(block))]


def _table_headers(text: str) -> list[list[str]]:
    """The header cells of every markdown table in `text`, folded and lower-cased."""
    lines = text.split("\n")
    headers: list[list[str]] = []
    for here, below in zip(lines, lines[1:], strict=False):
        if here.lstrip().startswith("|") and _SEPARATOR.match(below):
            cells = here.strip().strip("|").split("|")
            headers.append([_plain(cell) for cell in cells])
    return headers


def _style_columns(text: str) -> tuple[int, int, int]:
    """How many case tables `text` holds, how many of them end in a Style column, and how
    many other tables carry a Style cell in their header."""
    headers = _table_headers(text)
    cases = [header for header in headers if header[:2] == ["id", "preconditions"]]
    ending = sum(header[-1:] == ["style"] for header in cases)
    others = sum("style" in header for header in headers if header not in cases)
    return len(cases), ending, others


def _twin_problem(seeded: bytes, own: bytes) -> str | None:
    """Why two copies of a template differ, or None when they are the same text."""
    left, right = seeded.replace(b"\r\n", b"\n"), own.replace(b"\r\n", b"\n")
    if left == right:
        return None
    at = next(
        (i for i, (a, b) in enumerate(zip(left, right, strict=False)) if a != b),
        min(len(left), len(right)),
    )
    return f"the copies differ at byte {at} ({len(left)} against {len(right)} bytes)"


def _synthetic(claim: _Claim) -> str:
    """A small document that holds every phrase of `claim` once, each in a sentence of its
    own, and none of its absent words."""
    return "\n\n".join(
        f"A sentence that says {phrase} here." for phrase in claim.carries
    )


def _by_key(key: str) -> _Claim:
    return next(claim for claim in _CLAIMS if claim.key == key)


def _variants(phrase: str) -> Iterator[str]:
    """`phrase` once for each place a re-wrap could break it: at a space, with or without an
    indent on the next line, or after the hyphen of a word."""
    for match in re.finditer(" ", phrase):
        for pad in ("\n", "\n    "):
            yield phrase[: match.start()] + pad + phrase[match.end() :]
    for match in re.finditer(r"(?<=\w)-(?=\w)", phrase):
        yield phrase[: match.end()] + "\n" + phrase[match.end() :]


# --- the change ---------------------------------------------------------------------------


@pytest.mark.parametrize("claim", _CLAIMS, ids=[claim.key for claim in _CLAIMS])
def test_each_change_is_stated_where_it_belongs(claim: _Claim) -> None:
    problems = _problems(_slice(_read(claim.path), claim), claim)
    assert not problems, f"{_where(claim)}: " + "; ".join(problems)


@pytest.mark.parametrize("claim", _KEPT, ids=[claim.key for claim in _KEPT])
def test_the_first_three_shapes_stay(claim: _Claim) -> None:
    problems = _problems(_slice(_read(claim.path), claim), claim)
    assert not problems, f"{_where(claim)}: " + "; ".join(problems)


def test_the_planners_list_has_five_shapes() -> None:
    claim = _by_key("planner-step-4-counts-five-shapes")
    section = _slice(_read(claim.path), claim)
    items = _list_items_after(section, _STEP_4_LEAD_IN, _where(claim))
    assert len(items) == _STEP_4_ITEMS, (
        f"{_where(claim)}: {len(items)} items in the list after {_STEP_4_LEAD_IN!r}, "
        f"expected {_STEP_4_ITEMS}: {[item[:40] for item in items]}"
    )


def test_the_critics_list_has_five_numbered_shapes() -> None:
    claim = _by_key("critic-dimension-6-counts-five-vacuous-shapes")
    block = _slice(_read(claim.path), claim)
    assert _numbered_shapes(block) == _DIMENSION_6_SHAPES, (
        f"{_where(claim)}: the numbered shapes are {_numbered_shapes(block)}"
    )


@pytest.mark.parametrize(("copy", "folder"), _COPIES, ids=[copy for copy, _ in _COPIES])
def test_the_cases_template_has_a_style_column_in_each_case_table(
    copy: str, folder: Path
) -> None:
    cases, ending, others = _style_columns(_read(folder / _CASES))
    assert (cases, ending, others) == (2, 2, 0), (
        f"{copy} {_CASES}: {cases} case tables, {ending} end in a Style column, "
        f"{others} other tables carry a Style cell; expected 2, 2 and 0"
    )


@pytest.mark.parametrize("name", (_CASES, _PLAN))
def test_both_copies_of_a_template_are_the_same_text(name: str) -> None:
    problem = _twin_problem((_SEEDED / name).read_bytes(), (_OWN / name).read_bytes())
    assert problem is None, f"{name}: {problem}"


def test_the_planner_skill_stays_inside_the_line_cap() -> None:
    lines = _read(_PLANNER_SKILL).count("\n")
    assert lines <= _LINE_CAP, (
        f"test-planner SKILL.md has {lines} lines, cap {_LINE_CAP}"
    )


def test_the_pointer_to_the_review_skill_has_a_target() -> None:
    target = _REVIEW / "references" / "reading-gate-output.md"
    assert target.is_file(), "the planner points at a skill whose reference is gone"
    assert "known-positive" in _plain(_read(target)), (
        "the skill the planner points at no longer teaches firing a checker at a known positive"
    )


# --- the instruments ----------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    every_file = _SKILL_FILES | _TEMPLATE_FILES
    assert len(every_file) == _FILE_COUNT, f"{len(every_file)} files, not the 8 stated"
    assert len(_SKILL_FILES) == 4 and len(_TEMPLATE_FILES) == 4
    assert _SKILL_FILES.isdisjoint(_TEMPLATE_FILES), "a file is on both surfaces"
    # Every claim reads a file of the surface, and every file of the surface has a claim.
    claimed = {claim.path for claim in (*_CLAIMS, *_KEPT)}
    assert claimed == every_file, f"claims and surface differ: {claimed ^ every_file}"
    for path in sorted(every_file):
        assert _plain(_read(path)), f"{path.name}: the file is empty"
    assert len(_CLAIMS) == _CLAIM_COUNT, f"{len(_CLAIMS)} claims, not the 20 stated"
    assert len({claim.key for claim in _CLAIMS}) == _CLAIM_COUNT, (
        "two claims share a key"
    )
    phrases = sum(len(claim.carries) for claim in _CLAIMS)
    assert phrases == _PHRASE_COUNT, f"{phrases} phrases, not the 73 stated"
    absent = sum(len(claim.absent) for claim in _CLAIMS)
    assert absent == _ABSENT_COUNT, f"{absent} absent words, not the 2 stated"
    assert len(_KEPT) == _KEPT_COUNT, f"{len(_KEPT)} kept claims, not the 2 stated"


@pytest.mark.parametrize("claim", _CLAIMS, ids=[claim.key for claim in _CLAIMS])
def test_a_planted_removal_of_each_phrase_is_flagged(claim: _Claim) -> None:
    text = _synthetic(claim)
    assert _problems(text, claim) == [], (
        "the control holds every phrase and is not silent"
    )
    for phrase in claim.carries:
        removed = text.replace(phrase, "something else")
        assert removed != text, f"the planted removal of {phrase!r} changed nothing"
        assert f"does not carry {phrase!r}" in _problems(removed, claim)
    for word in claim.absent:
        planted = f"{text}\n\nThe old text said {word} here."
        assert f"still carries {word!r}" in _problems(planted, claim)


@pytest.mark.parametrize("claim", _CLAIMS, ids=[claim.key for claim in _CLAIMS])
def test_a_line_break_or_an_emphasis_mark_does_not_hide_a_phrase(claim: _Claim) -> None:
    text = _synthetic(claim)
    assert _problems(text, claim) == [], "the control is not silent"
    tried = 0
    for phrase in claim.carries:
        for variant in _variants(phrase):
            wrapped = text.replace(phrase, variant)
            assert wrapped != text, f"the break in {phrase!r} changed nothing"
            assert _problems(wrapped, claim) == [], (
                f"a break hid {phrase!r}: {variant!r}"
            )
            tried += 1
        first, _, rest = phrase.partition(" ")
        marked = text.replace(phrase, f"**{first}** `{rest}`")
        assert marked != text, f"the emphasis mark on {phrase!r} changed nothing"
        assert _problems(marked, claim) == [], f"an emphasis mark hid {phrase!r}"
    assert tried > 0, f"{claim.key}: no break was tried"


_LOOKALIKES: tuple[tuple[str, str, str], ...] = (
    # (the key of the claim, the phrase swapped out, the look-alike swapped in)
    (
        "planner-step-4-counts-five-shapes",
        "five shapes to check for",
        "four shapes to check for",
    ),
    (
        "planner-step-4-names-the-absence-shape",
        "the handler's own evidence that it ran",
        "the handler's own evidence that it exists",
    ),
    (
        "planner-step-5-manual-check-names-its-branch",
        "which branch the operator's action normally reaches",
        "which branch the operator's action rarely reaches",
    ),
    (
        "techniques-boundary-command-runs-the-comparison",
        "exercise the comparison that decides accept or reject",
        "exercise the threshold that decides accept or reject",
    ),
    (
        "levels-style-within-a-level",
        "a case goes in the form the repository already uses for that kind of flow",
        "a case goes in the form its author prefers",
    ),
)


@pytest.mark.parametrize(
    ("key", "phrase", "lookalike"), _LOOKALIKES, ids=[key for key, _, _ in _LOOKALIKES]
)
def test_a_look_alike_does_not_stand_in_for_a_phrase(
    key: str, phrase: str, lookalike: str
) -> None:
    claim = next(c for c in _CLAIMS if c.key == key)
    text = _synthetic(claim)
    assert _problems(text, claim) == [], "the control is not silent"
    swapped = text.replace(phrase, lookalike)
    assert swapped != text, f"{key}: the planted look-alike replaced nothing"
    missing = [p for p in _problems(swapped, claim) if p.startswith("does not carry")]
    assert any(phrase in problem for problem in missing), (
        f"{key}: {lookalike!r} stood in for {phrase!r}: {_problems(swapped, claim)}"
    )


_OLD_STEP_4 = (
    "### Can this case pass without proving anything?\n\n"
    "Ask it of every case before the gate closes.\n\n"
    "Three shapes to check for:\n\n"
    "- **Empty population.** The case iterates over a set that can legitimately be empty.\n"
    "  Add an assertion that the set is non-empty, and say what it is guarding.\n"
    "- **A falsy expected result with more than one cause.** `None`, `False`, `[]` or\n"
    '  "rejected" that two different code paths produce.\n'
    "- **A precondition that cannot hold in the target environment.** The case is skipped\n"
    "  rather than run. A skip is not a pass; plan to count them.\n\n"
    "Note the guard on the case itself.\n"
)
_OLD_DIMENSION_6 = (
    "**Vacuous passes**\n"
    "- Can any case pass without proving anything? Three shapes: it iterates a population that\n"
    "  may be empty and is not guarded; its expected result is a falsy value (`None`, `False`,\n"
    '  `[]`, "rejected") that more than one code path produces; or its precondition cannot hold\n'
    "  in the target environment, so it is skipped rather than run. Major.\n"
)


def test_the_old_three_shape_text_is_flagged_by_every_structure_check() -> None:
    step_4 = _by_key("planner-step-4-counts-five-shapes")
    vacuous = _by_key("critic-dimension-6-counts-five-vacuous-shapes")
    assert "three shapes" in step_4.absent and "three shapes" in vacuous.absent
    assert f"still carries {'three shapes'!r}" in _problems(_OLD_STEP_4, step_4)
    assert f"still carries {'three shapes'!r}" in _problems(_OLD_DIMENSION_6, vacuous)
    # The old list read under the new lead-in is three items, not five.
    relead = _OLD_STEP_4.replace("Three shapes", "Five shapes")
    assert len(_list_items_after(relead, _STEP_4_LEAD_IN, "planted")) == 3
    # Read under its own lead-in the old paragraph is not found under the new one at all.
    with pytest.raises(AssertionError, match="0 paragraphs start with"):
        _list_items_after(_OLD_STEP_4, _STEP_4_LEAD_IN, "planted")
    assert _numbered_shapes(_OLD_DIMENSION_6) == []


def test_a_near_miss_is_not_flagged_as_the_old_text() -> None:
    claim = _by_key("planner-step-4-counts-five-shapes")
    near_miss = "Five shapes to check for, not three; the first three are listed below."
    assert "three shapes" not in _plain(near_miss)
    assert _problems(near_miss, claim) == []
    # Two-digit and prose numbers are not shape labels.
    assert _numbered_shapes("Five shapes (2021) and (see 5) and (12) and (a)") == []
    assert _numbered_shapes("(1) one; (2) two; (3) three; (4) four; (5) five") == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _numbered_shapes("(1) one; (2) two; (3) three; (4) four") != [1, 2, 3, 4, 5]
    assert _numbered_shapes("(1) a; (2) b; (3) c; (4) d; (5) e; (6) f") != [
        1,
        2,
        3,
        4,
        5,
    ]


def test_the_list_counter_counts_top_level_items_only() -> None:
    five = "Five shapes to check for:\n\n" + "\n".join(f"- item {n}" for n in range(5))
    assert len(_list_items_after(five, "Five shapes", "planted")) == 5
    four = "Five shapes to check for:\n\n" + "\n".join(f"- item {n}" for n in range(4))
    assert len(_list_items_after(four, "Five shapes", "planted")) == 4
    six = "Five shapes to check for:\n\n" + "\n".join(f"- item {n}" for n in range(6))
    assert len(_list_items_after(six, "Five shapes", "planted")) == 6
    # A wrapped line and a nested item are part of the item above them, not items.
    wrapped = "Five shapes to check for:\n\n- a\n  continues here\n  - nested\n- b\n- c\n- d\n- e\n"
    assert len(_list_items_after(wrapped, "Five shapes", "planted")) == 5
    # Items after a paragraph that is not a list are not part of the list.
    split = "Five shapes to check for:\n\n- a\n- b\n\nA paragraph.\n\n- c\n- d\n- e\n"
    assert len(_list_items_after(split, "Five shapes", "planted")) == 2
    twice = "Five shapes to check for:\n\n- a\n\nFive shapes to check for:\n\n- b\n"
    with pytest.raises(AssertionError, match="2 paragraphs start with"):
        _list_items_after(twice, "Five shapes", "planted")


def test_the_table_check_sees_a_planted_style_column() -> None:
    head = "| ID | Preconditions | Input / action | Expected result | Source |"
    rule = "|----|---------------|----------------|-----------------|--------|"
    row = "| TC-01 | a | b | c | `AC-01` |"
    without = f"{head}\n{rule}\n{row}\n\n{head}\n{rule}\n{row}\n"
    assert _style_columns(without) == (2, 0, 0)
    one = without.replace(
        f"{head}\n{rule}\n{row}", f"{head} Style |\n{rule}-------|\n{row}", 1
    )
    assert one != without, "the planted column changed nothing"
    assert _style_columns(one) == (2, 1, 0)
    both = one.replace(f"{head}\n{rule}", f"{head} Style |\n{rule}-------|")
    assert _style_columns(both) == (2, 2, 0)
    # A header cell that only mentions style, or a Style cell in another table, is not a column
    # of a case table: the first is not a Style cell, the second is counted apart.
    guide = "| Document | Style guide |\n|---|---|\n| a | b |\n"
    assert _style_columns(guide) == (0, 0, 0)
    other = "| Level | Style |\n|---|---|\n| a | b |\n"
    assert _style_columns(other) == (0, 0, 1)
    first = f"| Style | ID | Preconditions |\n|---|---|---|\n| a | b | c |\n{without}"
    assert _style_columns(first) == (2, 0, 1)


def test_a_quoted_note_is_read_as_the_text_it_quotes() -> None:
    quoted = (
        "> a phrase that wraps\n> across two quoted lines\n>\n>   and an indented one"
    )
    assert (
        _plain(quoted)
        == "a phrase that wraps across two quoted lines and an indented one"
    )
    # A marker counts only at the start of a line.
    assert _plain("a > b\nc") == "a > b c"
    wrapped = _Claim("planted", Path("x"), _PREAMBLE, carries=("two quoted lines",))
    assert _problems(quoted, wrapped) == []


def test_the_twin_check_sees_a_planted_difference() -> None:
    same = b"line one\nline two\n"
    assert _twin_problem(same, same) is None
    assert _twin_problem(same, b"line one\r\nline two\r\n") is None
    drift = _twin_problem(same, b"line one\nline twp\n")
    assert drift is not None and "byte 16" in drift
    assert _twin_problem(same, same + b"x") is not None
    assert _twin_problem(same, same[:-1]) is not None


def test_the_readers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "# Title",
            "a note above the first heading",
            "## Alpha",
            "**First**",
            "- one",
            "**Second**",
            "- two",
            "> a quote ends the block",
            "- three",
            "```bash",
            "## a heading-looking line inside a fence",
            "```",
            "after the fence",
            "### Alpha child",
            "child body",
            "## Beta",
            "second body",
        ]
    )
    alpha = _section(planted, "## Alpha", "planted")
    assert "after the fence" in alpha and "child body" in alpha
    assert "second body" not in alpha and "inside a fence" in alpha
    first = _block(alpha, "**First**", "planted")
    assert "- one" in first and "- two" not in first
    second = _block(alpha, "**Second**", "planted")
    assert "- two" in second and "- three" not in second
    assert "a note above the first heading" in _preamble(planted, "planted")
    assert "Alpha" not in _preamble(planted, "planted")
    with pytest.raises(AssertionError, match="no heading starting"):
        _section(planted, "## Gamma", "planted")
    with pytest.raises(AssertionError, match="no bold label line"):
        _block(alpha, "**Third**", "planted")
    with pytest.raises(AssertionError, match="no level-2 heading"):
        _preamble("# Only a title\n\ntext\n", "planted")
    # A bold lead-in that is not the whole line is not a label.
    with pytest.raises(AssertionError, match="no bold label line"):
        _block("**First** and more words\n- one\n", "**First**", "planted")
