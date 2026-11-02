"""`plan-critic` reads the project's own conventions and names no one project's stack.

Its last section held rules written for one Python service -- a feature layout, a file rule,
a migration tool, an auth client class, a config module, a prompt step, test timeout
decorators and a socket event enum -- beside two AI-failure checks that hold everywhere, and
it applied all of them to every plan in every consumer, so a review in another stack called a
different layout a violation. It now tells the reviewer to read the project's own
architecture, conventions and Do-not sections, and keeps only the two AI-failure checks. The
same visit made the persona generic, widened the design-and-plan checklist to any
implementation plan, capped a document at two runs, and, of the two review lines that name a
convention only some projects hold, made one conditional on the project's conventions and
deleted the other.

What each test asserts:

* `test_no_file_of_the_skill_names_one_projects_stack` scans every file of the skill folder.
  The names are built from fragments, so this file does not itself carry a project's names.
* `test_each_change_is_stated_where_it_belongs` is one row per change. A row names one file
  and one section (the run cap also one paragraph of it), and keys on wording the old files
  did not hold.
* `test_the_generic_rules_the_removed_bullets_shared_stay` sits beside those rows and is NOT
  red on the old files: they held the same two lines, which are now the only home of two
  rules, so it guards a later edit and shows no change. It reads those two lines only, with
  no name scan, so it is green on the old text.
* `test_the_project_section_has_exactly_the_two_ai_checks` reads every block of the section,
  whatever its list style, and holds each block to its exact words.
* The instrument tests fire the scan, the readers, the guard and the re-wrap checks at known
  text, so their silence on the real files means something. Most of them pass on the old skill
  files too. The ones that take real new text as their control need it, and on the old files
  that control itself is not clean: the section guard and its re-wrap check take the real
  project section, which there still holds the removed rules, and the run-cap row's re-wrap
  check and its scope check take the real per-artifact paragraph, which there states no cap.
"""

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_ROOT = shipped_skill_dirs()["plan-critic"]

_SKILL = "SKILL.md"
_DIMENSIONS = "references/review-dimensions.md"
_DOR = "references/dor-tables.md"
_FINDING_FORMAT = "references/finding-format.md"

# What the scan must at least see. The scan itself walks the folder, so a file added later is
# scanned without an edit here; this set only stops a walk that quit descending into
# `references/` from passing silently.
_EXPECTED_FILES = frozenset({_SKILL, _DIMENSIONS, _DOR, _FINDING_FORMAT})

_HEADING = re.compile(r"^(#{1,6})\s+\S")
# A list item of any style: `-`, `*`, `+` or a number, then a space.
_LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
# A line that holds nothing but the marker, as it would after a break straight behind it.
_MARKER_ALONE = re.compile(r"\s*(?:[-*+]|\d+[.)])")
# A hyphen inside a word followed by a space: the shape a line break after the hyphen leaves.
_HYPHEN_GAP = re.compile(r"(?<=\w)- (?=\w)")

# The paragraph that holds the run cap is found by how it starts.
_RUN_CAP_LEAD_IN = "**Self-challenge is per-ARTIFACT"


def _cat(*fragments: str) -> str:
    return "".join(fragments)


# The dash the skill text uses, spelled as a code point so this file stays ASCII.
_EM_DASH = chr(0x2014)


@dataclass(frozen=True)
class _Name:
    label: str
    pattern: re.Pattern[str]
    samples: tuple[str, ...]


def _token(label: str, *fragments: str, whole_word: bool = False) -> _Name:
    """One identifier, held as fragments so this file does not spell it out.

    With `whole_word` a letter on either side of the token means it is part of another word,
    so a name that is also the start or end of ordinary words is not flagged inside them.
    """
    token = _cat(*fragments)
    pattern = re.escape(token)
    if whole_word:
        pattern = rf"(?<![A-Za-z]){pattern}(?![A-Za-z])"
    return _Name(label, re.compile(pattern, re.IGNORECASE), (token, token.lower()))


def _phrase(label: str, *words: str) -> _Name:
    """Words that a re-wrap or a hyphen may separate."""
    return _Name(
        label,
        re.compile(r"[\s-]+".join(map(re.escape, words)), re.IGNORECASE),
        ("\n    ".join(words), "-".join(words), " ".join(words).title()),
    )


# The names that tie the skill to one project. The first five groups are the ones the change
# was asked to remove; the rest are the other names the removed rules, the dimension lines
# and the design-and-plan checklist carried.
_NAMES: tuple[_Name, ...] = (
    _token("the migration tool", "Alem", "bic"),
    _token("the service-client class", "Base", "Internal", "Client"),
    _token("the config-module path", "core/con", "fig.py"),
    _token("the socket transport", "Web", "Socket"),
    _phrase("the feature layout", "vertical", "slice"),
    _phrase("the file rule", "one", "class", "per", "file"),
    _token("the env-var reader", "get", "env"),
    _token("the token format", "J", "WT"),
    _token("the AI provider", "Open", "AI"),
    _token("a test decorator (fast)", "fast", "_test"),
    _token("a test decorator (integration)", "integration", "_test"),
    _token("a code editor's plan mode", "Cur", "sor", whole_word=True),
)


@dataclass(frozen=True)
class _Claim:
    """One change: a file, one section of it (and, when `lead_in` is set, the one paragraph
    of that section that starts with it), the wording that must be there, and the words that
    must not be."""

    key: str
    file: str
    heading: str
    carries: tuple[str, ...]
    absent: tuple[str, ...] = ()
    lead_in: str | None = None


_CLAIMS: tuple[_Claim, ...] = (
    _Claim(
        "persona-names-no-medium",
        _SKILL,
        "## Role",
        carries=(
            "real-time streaming, prompt safety, async job processing",
            "AI services fail in ways traditional services don't",
        ),
        absent=("voice", "audio"),
    ),
    _Claim(
        "project-section-defers-to-the-projects-own-rules",
        _SKILL,
        "## Project-Specific Context",
        carries=(
            "project's own architecture, conventions and Do-not sections",
            "its AGENTS.md",
            "a convention the project does not state is not a finding",
        ),
        absent=("keep in mind", "unreliable for this project"),
    ),
    _Claim(
        "step-one-dependency-list-is-neutral",
        _SKILL,
        "### Step 1",
        carries=("streaming channels, auth providers",),
    ),
    _Claim(
        "rollback-question-is-neutral",
        _SKILL,
        "### Step 3",
        carries=("API contracts, or message and event formats",),
    ),
    # The cap sits INSIDE the per-artifact paragraph, so each clause is read there and not in
    # the whole section: that section holds other sentences with some of the same words, and
    # a cap moved into a paragraph of its own would still pass a section-wide read. The last
    # clause is the paragraph's own closing words, so a paragraph split anywhere fails loudly.
    _Claim(
        "run-cap-sits-in-the-per-artifact-paragraph",
        _SKILL,
        "## When This Skill Activates",
        lead_in=_RUN_CAP_LEAD_IN,
        carries=(
            "at most two",
            "at most two runs per document",
            "re-run this skill once on the revised document",
            "because a fix pass introduces defects at roughly the rate it resolves them",
            "the second and last run, because further runs mostly add churn",
            "a later run edits only for",
            "factual error",
            "contradiction",
            "missing item",
            "unsafe statement",
            "not for wording, order or taste",
            "full re-read of the document belongs to that same run, not to an extra one",
            "a fresh-reader re-review counts as the second run, within the limits the "
            "post-task-review skill sets for a fresh reader",
        ),
        # The reason to re-run comes first and the reason for the cap after it. The pointer
        # names a skill and no path or link, so it still reads where only one pack is installed.
        absent=(
            "re-run this skill on the revised document",
            "the second and last run, because a fix pass",
            "](",
            "references/",
            "fix-rounds",
            "post-task-review/",
        ),
    ),
    # Step 4 points at the run cap for the classes and does not list them a second time, so the
    # four classes live in one paragraph and cannot drift apart.
    _Claim(
        "later-run-applies-only-the-cap-classes",
        _SKILL,
        "### Step 4",
        carries=(
            "in a later run",
            "the run cap in When This Skill Activates",
            "resolve only the classes the run cap names",
            "drop every other finding",
            "a Minor included",
            "without fixing or surfacing it",
        ),
        absent=(
            "a factual error, a contradiction, a missing item or an unsafe statement",
        ),
    ),
    # The severity table says each finding's required action; a later run narrows it.
    _Claim(
        "severity-table-defers-to-the-later-run-rule",
        _FINDING_FORMAT,
        "## Severity Definitions",
        carries=(
            "in a later run only the classes named by the run cap (Step 4) are acted on",
            "every other finding is dropped",
        ),
    ),
    _Claim(
        "minor-findings-follow-the-later-run-rule",
        _SKILL,
        "### Step 5",
        carries=(
            "never surfaced to the user",
            "fixed silently, or dropped in a later run (Step 4)",
        ),
        absent=("always fixed silently",),
    ),
    _Claim(
        "plan-checklist-applies-to-any-implementation-plan",
        _DOR,
        "## Design/Plan DoR Table",
        carries=("or any implementation plan",),
    ),
    _Claim(
        "security-auth-and-secrets-are-neutral",
        _DIMENSIONS,
        "## Dimension 1",
        carries=("authentication between services", "configuration mechanism"),
    ),
    _Claim(
        "stability-race-example-is-neutral",
        _DIMENSIONS,
        "## Dimension 3",
        carries=("concurrent events or messages",),
    ),
    _Claim(
        "impact-contract-wire-format-and-migration-are-neutral",
        _DIMENSIONS,
        "## Dimension 4",
        carries=(
            "message or event type",
            "any message or event its consumers parse",
            "Is there a migration?",
            "e.g., message handlers, real-time streams",
        ),
    ),
    _Claim(
        "completeness-test-timeout-is-neutral",
        _DIMENSIONS,
        "## Dimension 5",
        carries=("timeout guard the project's testing conventions require",),
    ),
    # Two review lines that only some projects' conventions hold. The repository line says so,
    # and the line that asked for dependency-override mocking is gone: the line above it already
    # asks for the project's own testing conventions, and a project may ban that mocking style.
    _Claim(
        "repository-line-holds-only-where-the-project-requires-it",
        _DIMENSIONS,
        "## Dimension 4",
        carries=(
            "If the project's conventions require it, are queries going through "
            "repositories",
        ),
    ),
    _Claim(
        "dependency-override-mocking-line-is-gone",
        _DIMENSIONS,
        "## Dimension 5",
        carries=("timeout guard the project's testing conventions require",),
        absent=(
            "mocked via DI overrides",
            "not patched directly",
            "dependency override",
        ),
    ),
)

# These rows are TRUE ON THE OLD TEXT TOO: before the project rules were removed, the same two
# lines stood in the same dimension, beside two of the removed bullets that stated the same
# rules. They are now the only home of a stale-client rule and a table-locking rule, so these
# rows guard a later wording edit from dropping them. They show no change and are not red:
# they read the two lines only (no name scan, which the old text would fail). Each pins the
# whole clause with its directive, so "must be defined" turned into "may be ignored" is a
# finding, not just a missing noun.
_KEPT: tuple[_Claim, ...] = (
    _Claim(
        "stale-client-behavior-stays-in-dimension-four",
        _DIMENSIONS,
        "## Dimension 4",
        carries=("Stale-client behavior must be defined.",),
    ),
    _Claim(
        "table-locking-question-stays-in-dimension-four",
        _DIMENSIONS,
        "## Dimension 4",
        carries=("Will it lock tables under production load",),
    ),
)


@dataclass(frozen=True)
class _Shape:
    """One block the project section must hold, word for word: its kind, a label and its text
    (folded, and for an item without its marker)."""

    kind: str
    label: str
    text: str


_PARAGRAPH = "paragraph"
_ITEM = "item"

# Everything the section holds, word for word: one instruction and the two AI checks, nothing
# else. A ninth rule, in any list style or as prose, is a block the section does not list, and
# a word changed or added inside a listed block is a block that differs from its pinned text,
# so either takes a conscious edit here.
_RULE_CLAUSE = "must address rate limits, timeouts, and unexpected response formats"

_PROJECT_SECTION_SHAPE: tuple[_Shape, ...] = (
    _Shape(
        _PARAGRAPH,
        "the instruction",
        "Read the project's own architecture, conventions and Do-not sections (its "
        "AGENTS.md) and review the plan against what they state; a convention the "
        "project does not state is not a finding. Two AI checks hold in every project:",
    ),
    _Shape(
        _ITEM,
        "the AI failure check",
        "**AI failure modes**: any plan involving AI provider API calls "
        + _RULE_CLAUSE
        + ". Missing failure contracts are a Major finding.",
    ),
    _Shape(
        _ITEM,
        "the AI model facts check",
        "**AI model facts must be doc-verified**: any plan that states a model ID, event "
        "name, session parameter, audio format, or capability limit must have that fact "
        "verified against the official docs via `WebFetch` (see the `ai-docs-lookup` "
        f"skill). Unverified AI provider facts are a Major finding {_EM_DASH} in-memory "
        "knowledge is unreliable for these facts.",
    ),
)


@dataclass(frozen=True)
class _Block:
    kind: str
    text: str


def _read(relative: str) -> str:
    return (_ROOT / relative).read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text with every run of whitespace, line breaks included, as one space, and no
    space left after a hyphen inside a word.

    A sentence re-wrapped across lines then reads the same: a break at a space gives a space,
    and a break after the hyphen of "re-read" gives "re-read", never "re- read", so a re-wrap
    neither hides a name nor invents one. A clause is folded the same way before it is
    searched for, so a clause and the text it sits in agree about a hyphen.
    """
    return _HYPHEN_GAP.sub("-", " ".join(text.split()))


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


def _paragraph(section: str, lead_in: str, where: str) -> str:
    """The one paragraph of `section` that starts with `lead_in`.

    A paragraph is a run of non-blank lines. The lead-in is matched after both sides are
    folded, so a break, a tab or a doubled space inside it neither hides the paragraph nor
    invents a second one. No paragraph, or more than one, starting with the lead-in fails with
    the lead-in and the count named, so a reworded lead-in is a loud failure and never an
    empty match. A paragraph that was split in two keeps its lead-in on the first half only,
    and the clauses that moved to the second half are then missing from the half this returns.
    """
    paragraphs = [block for block in re.split(r"\n\s*\n", section) if block.strip()]
    start = _fold(lead_in)
    found = [block for block in paragraphs if _fold(block).startswith(start)]
    if len(found) != 1:
        raise AssertionError(
            f"{where}: {len(found)} paragraphs start with {lead_in!r}, expected 1"
        )
    return found[0]


def _where(claim: _Claim) -> str:
    place = f"plan-critic {claim.file}, section {claim.heading!r}"
    if claim.lead_in is None:
        return place
    return f"{place}, paragraph {claim.lead_in!r}"


def _claim(key: str) -> _Claim:
    return next(claim for claim in _CLAIMS if claim.key == key)


def _slice(text: str, claim: _Claim, where: str) -> str:
    """The part of `text` a claim is about: its section, or one paragraph of it."""
    section = _section(text, claim.heading, where)
    if claim.lead_in is None:
        return section
    return _paragraph(section, claim.lead_in, where)


def _names_in(text: str) -> list[str]:
    """Every name `_NAMES` holds that `text` carries, after line breaks are folded."""
    folded = _fold(text)
    return [
        f"{name.label}: {match.group(0)!r}"
        for name in _NAMES
        for match in name.pattern.finditer(folded)
    ]


def _problems(section: str, claim: _Claim, *, names: bool = True) -> list[str]:
    """What is wrong with `section` against `claim`; an empty list means nothing.

    With `names` off only the wording is read: the name scan is left to the other checks.
    """
    folded = _fold(section)
    lowered = folded.lower()
    problems = [
        f"does not carry {clause!r}"
        for clause in claim.carries
        if _fold(clause).lower() not in lowered
    ]
    problems += [
        f"still carries {word!r}"
        for word in claim.absent
        if _fold(word).lower() in lowered
    ]
    if names:
        problems += [f"names {hit}" for hit in _names_in(folded)]
    return problems


def _blocks(section: str) -> list[_Block]:
    """The blocks under the heading line of `section`, every non-blank line in one of them.

    Each list item, whatever its marker, is one block together with the lines that continue
    it; every other run of non-blank lines is one paragraph. A blank line ends a block. The
    text of a block is folded and, for an item, has its marker removed, so a bullet and a
    numbered item with the same words read the same.
    """
    kinds: list[str] = []
    lines: list[list[str]] = []
    open_block = False
    for line in section.split("\n")[1:]:
        if not line.strip():
            open_block = False
        elif _LIST_MARKER.match(line):
            kinds.append(_ITEM)
            lines.append([_LIST_MARKER.sub("", line, count=1)])
            open_block = True
        elif open_block:
            lines[-1].append(line)
        else:
            kinds.append(_PARAGRAPH)
            lines.append([line])
            open_block = True
    return [
        _Block(kind, _fold("\n".join(parts)))
        for kind, parts in zip(kinds, lines, strict=True)
    ]


def _project_section_problems(section: str) -> list[str]:
    """What is wrong with the project section: a block it does not list, a listed block
    that is missing or whose first or last words or rule clause changed."""
    blocks = _blocks(section)
    expected_items = sum(shape.kind == _ITEM for shape in _PROJECT_SECTION_SHAPE)
    expected_paragraphs = len(_PROJECT_SECTION_SHAPE) - expected_items
    items = sum(block.kind == _ITEM for block in blocks)
    paragraphs = len(blocks) - items
    problems: list[str] = []
    if (items, paragraphs) != (expected_items, expected_paragraphs):
        shown = "; ".join(f"{block.kind} {block.text[:50]!r}" for block in blocks)
        problems.append(
            f"the section has {items} list items and {paragraphs} paragraphs, expected "
            f"{expected_items} and {expected_paragraphs}: {shown}"
        )
    for shape in _PROJECT_SECTION_SHAPE:
        pinned = _fold(shape.text)
        start = " ".join(pinned.split()[:3]).lower()
        block = next(
            (
                candidate
                for candidate in blocks
                if candidate.kind == shape.kind
                and candidate.text.lower().startswith(start)
            ),
            None,
        )
        if block is None:
            problems.append(f"no {shape.kind} starts with {start!r}")
        elif block.text != pinned:
            problems.append(
                f"{shape.label} is not its pinned text: "
                + _around_difference(block.text, pinned)
            )
    return problems


def _project_section() -> str:
    return _section(
        _read(_SKILL), "## Project-Specific Context", f"plan-critic {_SKILL}"
    )


def _rewraps(text: str) -> Iterator[str]:
    """`text` once for each place a re-wrap could put a line break.

    A break replaces a single space between two words, with or without an indent on the next
    line, or follows a hyphen inside a word, where a formatter that breaks on hyphens breaks
    too. A space before something that would read as a list marker is left alone, and so is
    the space straight after a marker: no formatter starts a continuation line with a marker
    or leaves one alone at the end of a line.
    """
    for match in re.finditer(r"(?<=\S) (?=\S)(?!(?:[-*+]|\d+[.)])\s)", text):
        at = match.start()
        if _MARKER_ALONE.fullmatch(text[text.rfind("\n", 0, at) + 1 : at]):
            continue
        yield text[:at] + "\n" + text[at + 1 :]
        yield text[:at] + "\n    " + text[at + 1 :]
    for match in re.finditer(r"(?<=\w)-(?=\w)", text):
        yield text[: match.end()] + "\n" + text[match.end() :]


def _around_difference(left: str, right: str) -> str:
    at = next(
        (i for i, (a, b) in enumerate(zip(left, right, strict=False)) if a != b),
        min(len(left), len(right)),
    )
    window = slice(max(at - 25, 0), at + 25)
    return f"{left[window]!r} against {right[window]!r}"


def _surface() -> list[Path]:
    return sorted(path for path in _ROOT.rglob("*") if path.is_file())


def _scan_folder() -> tuple[int, list[str]]:
    """How many files were read, and every name hit as `file: name`."""
    files = _surface()
    hits = [
        f"{path.relative_to(_ROOT).as_posix()}: {hit}"
        for path in files
        for hit in _names_in(path.read_text(encoding="utf-8"))
    ]
    return len(files), hits


def _assert_claim(claim: _Claim, *, names: bool = True) -> None:
    where = _where(claim)
    problems = _problems(_slice(_read(claim.file), claim, where), claim, names=names)
    assert not problems, f"{where}: " + "; ".join(problems)


# --- the change ---------------------------------------------------------------------------


def test_no_file_of_the_skill_names_one_projects_stack() -> None:
    scanned, hits = _scan_folder()
    assert not hits, (
        f"plan-critic names one project's stack ({len(hits)} hits in {scanned} files "
        "scanned):\n" + "\n".join(hits)
    )


@pytest.mark.parametrize("claim", _CLAIMS, ids=[claim.key for claim in _CLAIMS])
def test_each_change_is_stated_where_it_belongs(claim: _Claim) -> None:
    _assert_claim(claim)


@pytest.mark.parametrize("claim", _KEPT, ids=[claim.key for claim in _KEPT])
def test_the_generic_rules_the_removed_bullets_shared_stay(claim: _Claim) -> None:
    # Names are not scanned here: the old Dimension 4 named a stack in the same section, so
    # a scan would make these rows red on the old text, and they are meant to be green there.
    _assert_claim(claim, names=False)


def test_the_project_section_has_exactly_the_two_ai_checks() -> None:
    problems = _project_section_problems(_project_section())
    assert not problems, (
        "one project's rules do not belong in a skill that every project runs: "
        + "; ".join(problems)
    )


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_the_whole_skill_folder() -> None:
    relative = [path.relative_to(_ROOT).as_posix() for path in _surface()]
    missing = sorted(_EXPECTED_FILES - set(relative))
    assert not missing, f"the scan walks {relative} and misses {missing}"
    assert len(relative) == len(set(relative))
    empty = [name for name in relative if not _read(name).strip()]
    assert not empty, f"files with no text, so the scan saw nothing in them: {empty}"
    scanned, _ = _scan_folder()
    assert scanned == len(relative), (
        f"{len(relative)} files in the folder, {scanned} scanned"
    )


@pytest.mark.parametrize("name", _NAMES, ids=[name.label for name in _NAMES])
def test_the_name_scan_sees_a_planted_name(name: _Name) -> None:
    for sample in name.samples:
        planted = (
            f"An opening sentence.\nThen {sample} turns up\nin the middle of a line."
        )
        found = _names_in(planted)
        assert any(hit.startswith(name.label) for hit in found), (
            f"the scan missed {sample!r} planted in a sentence; it found {found}"
        )


def test_the_name_scan_is_silent_on_neutral_text() -> None:
    neutral = (
        "Is authentication between services stated? Does each slice of work have one "
        "owner, each file one class, and every change a migration, a wire format and a "
        "timeout the project's own rules name?"
    )
    assert _names_in(neutral) == []


def test_a_re_wrap_neither_hides_a_name_nor_invents_one() -> None:
    assert _fold("a\n   b\t\tc\n\n d") == "a b c d"
    layout = _phrase("planted", "vertical", "slice")
    assert layout.pattern.search(_fold("a vertical\n    slice of work"))
    assert not layout.pattern.search(_fold("a vertical line and a slice of cake"))


def test_the_fold_joins_a_hyphen_break_and_keeps_a_spaced_dash() -> None:
    assert _fold("a fresh-\n    reader reads") == "a fresh-reader reads"
    assert _fold("a fresh-reader reads") == "a fresh-reader reads"
    assert _fold("one - two") == "one - two"
    assert _fold("one -\ntwo") == "one - two"
    # A clause is folded the same way, so a clause and the text it sits in agree.
    assert _fold("a fresh- reader") == _fold("a fresh-\nreader")


def test_the_re_wrap_generator_makes_the_breaks_it_claims() -> None:
    assert sorted(_rewraps("a b-c d")) == sorted(
        [
            "a\nb-c d",
            "a\n    b-c d",
            "a b-c\nd",
            "a b-c\n    d",
            "a b-\nc d",
        ]
    )
    # No break before a marker: a continuation line never starts one.
    varied = list(_rewraps("a - b 1. c + d * e"))
    assert varied, "the generator made no break at all"
    for variant in varied:
        later = variant.split("\n")[1:]
        assert not any(_LIST_MARKER.match(line) for line in later), variant
    # No break straight after a marker either: it would leave the marker alone on its line.
    assert list(_rewraps("- a")) == []
    assert set(_rewraps("1. a b")) == {"1. a\nb", "1. a\n    b"}


def test_a_re_wrap_changes_no_folded_text() -> None:
    checked = 0
    for claim in (*_CLAIMS, *_KEPT):
        where = _where(claim)
        text = _slice(_read(claim.file), claim, where)
        expected = _fold(text)
        for variant in _rewraps(text):
            checked += 1
            assert _fold(variant) == expected, (
                f"{where}: a re-wrap changes the folded text: "
                + _around_difference(_fold(variant), expected)
            )
    assert checked > 1000, f"only {checked} re-wraps were tried"


def test_a_re_wrap_changes_no_verdict_of_the_section_guard() -> None:
    heading, _, body = _project_section().partition("\n")
    checked = 0
    for variant in _rewraps(body):
        checked += 1
        problems = _project_section_problems(heading + "\n" + variant)
        assert not problems, (
            "a re-wrap changes the verdict: "
            + "; ".join(problems)
            + f" (variant {variant[:80]!r})"
        )
    assert checked > 100, f"only {checked} re-wraps were tried"


def _without_the_rule_clause(section: str) -> str:
    loose = r"\s+".join(map(re.escape, _RULE_CLAUSE.split()))
    return re.sub(loose, "", section)


def _swap(old: str, new: str) -> Callable[[str], str]:
    """A planted edit that finds `old` whatever line breaks sit between its words, so the
    planted forms need no particular wrapping of the section they are planted in."""
    pattern = r"\s+".join(map(re.escape, old.split()))
    # A formatter that breaks after a hyphen leaves its line break inside the word.
    pattern = pattern.replace(r"\-", r"\-\s*")
    if old[:1].isspace():
        pattern = r"\s+" + pattern
    if old[-1:].isspace():
        pattern += r"\s+"
    loose = re.compile(pattern)
    return lambda section: loose.sub(new, section, count=1)


def _without_the_last_item(section: str) -> str:
    lines = section.split("\n")
    last = max(at for at, line in enumerate(lines) if _LIST_MARKER.match(line))
    return "\n".join(lines[:last])


_NINTH_RULE = "A ninth rule that names a convention no project has stated."

# Each form is one way a rule could come back into the section. The first two are written
# the way the removed rules were; the rest are the shapes a reader of bold leads alone misses.
_PLANTED_SECTIONS: dict[str, Callable[[str], str]] = {
    "bold-led-bullet": lambda s: f"{s.rstrip()}\n- **Ninth rule**: {_NINTH_RULE}",
    "last-bullet-removed": _without_the_last_item,
    "plain-bullet": lambda s: f"{s.rstrip()}\n- {_NINTH_RULE}",
    "star-bullet": lambda s: f"{s.rstrip()}\n* {_NINTH_RULE}",
    "plus-bullet": lambda s: f"{s.rstrip()}\n+ {_NINTH_RULE}",
    "numbered-item": lambda s: f"{s.rstrip()}\n1. {_NINTH_RULE}",
    "prose-paragraph": lambda s: f"{s.rstrip()}\n\n{_NINTH_RULE}",
    "line-appended-to-the-last-bullet": lambda s: f"{s.rstrip()}\n  {_NINTH_RULE}",
    "rule-clause-removed-from-a-bullet": _without_the_rule_clause,
    # Edits inside a block, between its first words and its last: a guard that pins how a block
    # starts and ends, or one clause of it, reads every one of these as unchanged.
    "words-inserted-in-the-middle-of-a-bullet": _swap(
        "unexpected response formats.",
        "unexpected response formats, and a ninth thing the project never stated.",
    ),
    "word-changed-in-the-instruction": _swap("what they state", "what they omit"),
    "pointer-removed-from-the-facts-bullet": _swap(
        " (see the `ai-docs-lookup` skill)", ""
    ),
    "tool-swapped-in-the-facts-bullet": _swap("via `WebFetch`", "from memory"),
}


@pytest.mark.parametrize("form", list(_PLANTED_SECTIONS))
def test_the_section_guard_sees_a_planted_change(form: str) -> None:
    section = _project_section()
    assert _project_section_problems(section) == [], "the control is not clean"
    planted = _PLANTED_SECTIONS[form](section)
    assert planted != section, f"{form}: the planted change changed nothing"
    assert _project_section_problems(planted), f"the guard missed a planted {form}"


def test_the_section_reader_sees_planted_text_and_fails_loudly() -> None:
    planted = "\n".join(
        [
            "## Alpha",
            "first body",
            "```bash",
            "# a comment inside a fence is not a heading",
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
    assert "second body" not in alpha
    child = _section(planted, "### Alpha child", "planted")
    assert "child body" in child and "second body" not in child
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "## Gamma", "planted")


def test_the_paragraph_reader_sees_planted_text_and_fails_loudly() -> None:
    planted = "\n".join(
        [
            "## Alpha",
            "",
            "**Lead** first paragraph",
            "that wraps onto a second line and ends here.",
            "",
            "A neighbour that mentions **Lead** later but does not start with it.",
            "",
            "- a list item",
        ]
    )
    found = _paragraph(planted, "**Lead**", "planted")
    assert "ends here." in found
    assert "neighbour" not in found and "list item" not in found
    with pytest.raises(AssertionError, match="0 paragraphs start with"):
        _paragraph(planted, "**Missing**", "planted")
    with pytest.raises(AssertionError, match="2 paragraphs start with"):
        _paragraph(
            planted + "\n\n**Lead** a second paragraph with the lead-in",
            "**Lead**",
            "planted",
        )
    # A paragraph split in two keeps the lead-in on its first half, so the clause that moved to
    # the second half is missing from the half the reader returns.
    split = planted.replace("first paragraph\n", "first paragraph\n\n")
    claim = _Claim(
        "planted", "none", "## Alpha", carries=("ends here.",), lead_in="**Lead**"
    )
    assert _problems(_paragraph(split, "**Lead**", "planted"), claim) == [
        "does not carry 'ends here.'"
    ]
    assert _problems(_paragraph(planted, "**Lead**", "planted"), claim) == []


def test_the_row_check_fails_on_planted_text() -> None:
    claim = _Claim(
        "planted",
        "none",
        "## Planted",
        carries=("a clause", "another clause"),
        absent=("forbidden",),
    )
    assert _problems("A clause and another\n  clause, nothing else.", claim) == []
    short = _problems("A clause only, and a forbidden word.", claim)
    assert any("another clause" in problem for problem in short), short
    assert any("forbidden" in problem for problem in short), short
    named = _problems(f"A clause, another clause, {_NAMES[0].samples[0]}.", claim)
    assert any(problem.startswith("names") for problem in named), named
    # With the name scan off, a name is not flagged and a missing clause still is.
    planted = f"A clause, another clause, {_NAMES[0].samples[0]}."
    assert _problems(planted, claim, names=False) == []
    assert _problems("A clause only.", claim, names=False) == [
        "does not carry 'another clause'"
    ]


# --- the instruments, second round ---------------------------------------------------------

_CAP_ROW = "run-cap-sits-in-the-per-artifact-paragraph"

# The names the change was asked to remove, by label. The scan's own surface is stated in
# numbers here, so a name dropped from the list is a failure and no longer a silent shrink.
_ASKED_NAMES = (
    "the migration tool",
    "the service-client class",
    "the config-module path",
    "the socket transport",
    "the feature layout",
)
_NAME_COUNT = 12
# The planted section forms and the two tables of rows are stated in numbers too. Each feeds a
# parametrized test, so a form or a row dropped from its table is only one test fewer, which
# nothing counts, and an emptied table is a skip, not a failure.
_PLANTED_FORM_COUNT = 13
_CLAIM_COUNT = 15
_KEPT_COUNT = 2


def test_the_name_list_keeps_what_the_change_was_asked_to_remove() -> None:
    labels = [name.label for name in _NAMES]
    assert len(labels) == len(set(labels)), f"two names share a label: {labels}"
    missing = [label for label in _ASKED_NAMES if label not in labels]
    assert not missing, f"the scan no longer looks for {missing}"
    assert len(_NAMES) == _NAME_COUNT, (
        f"the scan looks for {len(_NAMES)} names, expected {_NAME_COUNT}: {labels}"
    )


def test_the_planted_forms_and_the_rows_keep_their_stated_number() -> None:
    sizes = {
        "planted section forms": (len(_PLANTED_SECTIONS), _PLANTED_FORM_COUNT),
        "change rows": (len(_CLAIMS), _CLAIM_COUNT),
        "kept rows": (len(_KEPT), _KEPT_COUNT),
    }
    wrong = [
        f"{table}: {found}, expected {expected}"
        for table, (found, expected) in sizes.items()
        if found != expected
    ]
    assert not wrong, "a table of the guard changed size: " + "; ".join(wrong)


def test_the_name_scan_is_silent_on_words_that_contain_a_name() -> None:
    assert _names_in("a cursory read of a precursor of the plan") == []
    seen = _names_in("the Cursor plan, and a (cursor) beside it")
    assert len(seen) == 2, f"the real name must still be seen, twice: {seen}"


def test_the_paragraph_reader_finds_a_lead_in_that_a_re_wrap_broke() -> None:
    lead_in = "**Self-challenge is per-ARTIFACT, not per-task.**"
    variants = (
        lead_in,
        "**Self-challenge is\nper-ARTIFACT, not per-task.**",
        "**Self-challenge is\n    per-ARTIFACT, not per-task.**",
        "**Self-challenge  is per-ARTIFACT,\tnot per-task.**",
        "**Self-\nchallenge is per-ARTIFACT, not per-task.**",
        "**Self-challenge is per-\nARTIFACT, not per-task.**",
    )
    for variant in variants:
        planted = f"## Alpha\n\n{variant} Its text\nruns on here.\n\nA neighbour.\n"
        found = _paragraph(planted, lead_in, "planted")
        assert "runs on here." in found and "neighbour" not in found, variant


def test_a_re_wrap_changes_no_verdict_of_the_run_cap_row() -> None:
    claim = _claim(_CAP_ROW)
    assert claim.lead_in is not None
    where = _where(claim)
    section = _section(_read(claim.file), claim.heading, where)
    checked = 0
    for variant in _rewraps(section):
        checked += 1
        problems = _problems(_paragraph(variant, claim.lead_in, where), claim)
        assert not problems, (
            f"{where}: a re-wrap changes the verdict: "
            + "; ".join(problems)
            + f" (variant {variant[:80]!r})"
        )
    assert checked > 100, f"only {checked} re-wraps were tried"


def test_the_run_cap_row_is_scoped_to_its_paragraph() -> None:
    claim = _claim(_CAP_ROW)
    where = _where(claim)
    assert claim.lead_in == _RUN_CAP_LEAD_IN, (
        "the cap row lost its lead-in, so it reads the whole section and cannot see a cap "
        "that moved out of the per-artifact paragraph"
    )
    section = _section(_read(claim.file), claim.heading, where)
    paragraph = _paragraph(section, _RUN_CAP_LEAD_IN, where)
    cap = re.search(r"\*\*at\s+most\s+two\s+runs\s+per\s+document\*\*", paragraph)
    assert cap is not None, f"{where}: the paragraph no longer states the cap in bold"
    moved = section.replace(
        paragraph, paragraph[: cap.start()].rstrip() + "\n\n" + paragraph[cap.start() :]
    )
    assert moved != section, "the planted move changed nothing"
    assert _problems(_paragraph(moved, _RUN_CAP_LEAD_IN, where), claim), (
        "the scoped row missed a cap that moved into a paragraph of its own"
    )
    assert _problems(moved, replace(claim, lead_in=None)) == [], (
        "a row without its lead-in was expected to read the moved cap as present"
    )


# The run cap lets a fresh reader's re-review count as the second run, within the limits another
# skill sets for such a reader. A pointer is only as good as its target, so the limits it leans
# on are read where they live.
_FRESH_READER_HOME = ("post-task-review", "references/fix-rounds.md")
_FRESH_READER_LIMITS = (
    "a fresh reader",
    "planted false claim",
    "at most four real claims",
    "only if it rejected the planted claim",
)
_FRESH_READER_LIMIT_COUNT = 4


def _fresh_reader_limits_missing(text: str) -> list[str]:
    """The limits that `text` does not state. The whole file is read, not one numbered
    section of it, so renumbering its sections cannot fail this check."""
    folded = _fold(text).lower()
    return [clause for clause in _FRESH_READER_LIMITS if clause not in folded]


def test_the_fresh_reader_pointer_has_a_target() -> None:
    skill, relative = _FRESH_READER_HOME
    folder = shipped_skill_dirs().get(skill)
    assert folder is not None, (
        f"plan-critic points at the {skill} skill; it is not shipped"
    )
    text = (folder / relative).read_text(encoding="utf-8")
    missing = _fresh_reader_limits_missing(text)
    assert not missing, f"{skill} {relative} no longer states the limits: {missing}"


def test_the_fresh_reader_check_fails_on_planted_text() -> None:
    assert len(_FRESH_READER_LIMITS) == _FRESH_READER_LIMIT_COUNT, (
        "the check reads fewer limits than it was written for, so it would pass on any text"
    )
    bare = "# Reviewing\n\n## 1. Order\n\nfirst\n\n## 2. A reader\n\nnothing about limits.\n"
    assert _fresh_reader_limits_missing(bare) == list(_FRESH_READER_LIMITS)
    stated = (
        "A fresh reader, given a planted false claim.\n"
        "Its brief carries at most four real claims.\n"
        "Trust it only if it rejected the planted\nclaim."
    )
    assert _fresh_reader_limits_missing(stated) == []


def test_a_planted_edit_finds_its_words_across_breaks() -> None:
    edit = _swap(" (see the `ai-docs-lookup` skill)", "")
    texts = (
        "facts via `WebFetch` (see the `ai-docs-lookup` skill). Next",
        "facts via `WebFetch` (see the\n  `ai-docs-lookup` skill). Next",
        "facts via `WebFetch`\n(see the `ai-docs-lookup` skill). Next",
        # A formatter that breaks after a hyphen leaves the break inside the word.
        "facts via `WebFetch` (see the `ai-\n  docs-lookup` skill). Next",
        "facts via `WebFetch` (see the `ai-docs-\nlookup` skill). Next",
    )
    for text in texts:
        assert edit(text) == "facts via `WebFetch`. Next", text
