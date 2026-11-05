"""The kit-managed stacked-PR document carries generic recipes and no project detail.

`kit-setup` seeds this document into an adopter's `.ai/`, and several kit skills point at it
by path or by section name. Its copy had grown details of one project (a pull-request number
range, a trunk called `dev` in commands, "this repo", a dated CI line) and lacked the recipes
for delivering a branch from a shared checkout without switching it. These tests pin, by class:

- structure: every pre-existing heading is still there once, every added heading exists once,
  all in one expected order, and every section name a skill cites is a heading, also when
  the citing text wraps the name across a line break;
- neutrality: no class of project detail survives, shown against a planted fixture and a
  near-miss so that a zero means the scan can see; every regex alternative has a planted shape
  of its own, and a forbidden string wrapped across two lines is still seen;
- scan surface: the citation scan reads every markdown file under `plugins/` but the document,
  counted by a second instrument;
- wording: the intro is true of the whole document, a garbled sentence stays repaired, and each
  added section keeps the sentence that names the failure it prevents, in its own text; the
  intro says the kit manages the file, and two recipes keep the sentence that makes them work
  over a stack and from Windows PowerShell 5.1.

Every forbidden string is built from fragments, so this file is clean under its own scan.
"""

import os
import re
import textwrap
from pathlib import Path
from typing import NamedTuple

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PLUGINS = _ROOT / "plugins"
_DOC = (
    _PLUGINS
    / "core"
    / "src"
    / "lemmi_ai_kit"
    / "assets"
    / "ai"
    / "git-stacked-pr-workflow.md"
)

# --- the heading sequence ---------------------------------------------------------------
#
# (level, text) of every heading, outside code fences, in document order. The pre-existing
# ones are the headings of the document before the recipes were added; skills cite two of
# them by name, so none may be renamed, renumbered or dropped.
_EXPECTED_ORDER: tuple[tuple[int, str], ...] = (
    (1, "Stacked PR Workflow"),
    (2, "Native stacks first (`gh stack`, public preview 2026-07-30)"),
    (2, "Propagating a mid-stack fix"),
    (2, "Work the layers in ONE direction"),
    (2, "Verify the chain on the REMOTE, link by link"),
    (2, "Pushing a stack can start one CI build per branch"),
    (2, "Cascading a stack after fixes land at the bottom"),
    (3, "A branch whose own tip is a merge commit must be MERGED, not rebased"),
    (3, "Dropping exactly one isolated commit, without an interactive rebase"),
    (3, "Separate FIXING from CASCADING into different sessions"),
    (3, "Re-stacking without a checkout"),
    (2, "Collapsing a stack"),
    (2, "Deciding whether finished branches may stay independent PRs"),
    (2, "Prove the composition, not only the merge"),
    (2, "Base retargeting is a MANUAL step"),
    (2, "Plumbing from a shared checkout"),
    (3, "Building a stack by plumbing"),
    (3, "Edit a committed file by its blob bytes, not in an export"),
    (3, "Prove the delivery left the checkout alone"),
    (3, "Prove the tip"),
    (2, "Editing a file the operator holds uncommitted"),
    (2, "Hand-over checks in a shared checkout"),
    (2, "Is it merged? Is it safe to delete?"),
    (2, "Related"),
)
_PRE_EXISTING: tuple[tuple[int, str], ...] = (
    (1, "Stacked PR Workflow"),
    (2, "Native stacks first (`gh stack`, public preview 2026-07-30)"),
    (2, "Propagating a mid-stack fix"),
    (2, "Work the layers in ONE direction"),
    (2, "Verify the chain on the REMOTE, link by link"),
    (2, "Cascading a stack after fixes land at the bottom"),
    (3, "A branch whose own tip is a merge commit must be MERGED, not rebased"),
    (3, "Dropping exactly one isolated commit, without an interactive rebase"),
    (3, "Separate FIXING from CASCADING into different sessions"),
    (2, "Collapsing a stack"),
    (2, "Base retargeting is a MANUAL step"),
    (2, "Is it merged? Is it safe to delete?"),
    (2, "Related"),
)
_ADDED = tuple(h for h in _EXPECTED_ORDER if h not in _PRE_EXISTING)

_FLOOR = "Cascading a stack after fixes land at the bottom"
_PLUMBING = "Plumbing from a shared checkout"
_PLUMBING_PARTS = (
    "Building a stack by plumbing",
    "Edit a committed file by its blob bytes, not in an export",
    "Prove the delivery left the checkout alone",
    "Prove the tip",
)
_MERGED = "Is it merged? Is it safe to delete?"


class _Heading(NamedTuple):
    level: int
    text: str
    line: int


def _text() -> str:
    return _DOC.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """Whitespace folded and lower-cased, because lines wrap and case varies."""
    return " ".join(text.split()).lower()


def _headings(text: str) -> list[_Heading]:
    """Every markdown heading outside a code fence, with its line index."""
    found: list[_Heading] = []
    fenced = False
    for index, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        match = re.match(r"^(#{1,6}) (.+?)\s*$", line)
        if match and not fenced:
            found.append(_Heading(len(match.group(1)), match.group(2), index))
    return found


def _section(text: str, heading: str, level: int, *, own: bool = False) -> str:
    """The lines under `heading`, up to the next heading of the same or a shallower level.

    With `own`, up to the next heading of ANY level: the lead-in of a section, without its
    subsections. A heading that is absent, or present more than once, fails loudly: a guard
    that cannot find its subject must not pass.
    """
    lines = text.splitlines()
    heads = _headings(text)
    starts = [h.line for h in heads if h.level == level and h.text == heading]
    assert len(starts) == 1, (
        f"heading {'#' * level} {heading!r} found {len(starts)} times, want 1"
    )
    end = next(
        (h.line for h in heads if h.line > starts[0] and (own or h.level <= level)),
        None,
    )
    return "\n".join(lines[starts[0] + 1 : end])


# --- structure --------------------------------------------------------------------------


def test_every_pre_existing_heading_is_still_there_once() -> None:
    seen = [(h.level, h.text) for h in _headings(_text())]
    wrong = [h for h in _PRE_EXISTING if seen.count(h) != 1]
    assert not wrong, f"pre-existing headings renamed, dropped or duplicated: {wrong}"


def test_every_added_heading_exists_exactly_once() -> None:
    seen = [(h.level, h.text) for h in _headings(_text())]
    wrong = [f"{h} x{seen.count(h)}" for h in _ADDED if seen.count(h) != 1]
    assert not wrong, f"added headings not present exactly once: {wrong}"


def test_headings_appear_in_the_expected_order() -> None:
    known = set(_EXPECTED_ORDER)
    seen = [(h.level, h.text) for h in _headings(_text()) if (h.level, h.text) in known]
    assert seen == list(_EXPECTED_ORDER)


def test_restacking_is_the_last_subsection_of_the_cascading_section() -> None:
    section = _section(_text(), _FLOOR, 2)
    subsections = [h.text for h in _headings(section) if h.level == 3]
    assert subsections, "the cascading section has no subsection at all"
    assert subsections[-1] == "Re-stacking without a checkout"


def test_plumbing_section_has_its_four_subsections_in_order() -> None:
    section = _section(_text(), _PLUMBING, 2)
    subsections = [h.text for h in _headings(section) if h.level == 3]
    assert subsections == list(_PLUMBING_PARTS)


def test_heading_scan_skips_code_fences_and_the_section_finder_fails_loudly() -> None:
    fixture = (
        "# Top\n\n```bash\n# a comment, not a heading\n```\n\n## One\nbody\n## Two\nx\n"
    )
    assert [(h.level, h.text) for h in _headings(fixture)] == [
        (1, "Top"),
        (2, "One"),
        (2, "Two"),
    ]
    assert _section(fixture, "One", 2).strip() == "body"
    with pytest.raises(AssertionError):
        _section(fixture, "Absent", 2)
    with pytest.raises(AssertionError):
        _section(fixture + "## One\nagain\n", "One", 2)
    nested = "## One\nbody\n### Sub\ndeep\n## Two\nx\n"
    assert _section(nested, "One", 2).split() == ["body", "###", "Sub", "deep"]
    assert _section(nested, "One", 2, own=True).split() == ["body"]
    assert _section(nested, "Sub", 3, own=True).split() == ["deep"]


# --- the sections skills cite -----------------------------------------------------------

# A skill cites a section as `.ai/git-stacked-pr-workflow.md` followed by the section sign
# and the name between asterisks. The section sign is built, not typed.
_CITATION = re.compile(
    r"git-stacked-pr-workflow\.md`?\s*" + chr(0xA7) + r"\s*\*([^*]+)\*"
)


def _cited_sections(text: str) -> list[str]:
    return _CITATION.findall(" ".join(text.split()))


def _scanned_files() -> list[Path]:
    return sorted(p for p in _PLUGINS.rglob("*.md") if p != _DOC)


def _markdown_files_by_walk() -> set[Path]:
    """The same surface found by a second instrument: `os.walk`, not `Path.rglob`."""
    return {
        Path(folder) / name
        for folder, _dirs, names in os.walk(_PLUGINS)
        for name in names
        if name.endswith(".md")
    }


def test_every_section_a_skill_cites_is_a_heading_of_the_document() -> None:
    cited = {
        name
        for path in _scanned_files()
        for name in _cited_sections(path.read_text(encoding="utf-8"))
    }
    names = {h.text for h in _headings(_text())}
    assert not cited - names, f"cited but not a heading: {sorted(cited - names)}"


def test_the_citation_scan_reads_every_skill_and_sees_the_known_citations() -> None:
    scanned = _scanned_files()
    skills = sorted(_PLUGINS.glob("*/skills/*/SKILL.md"))
    assert skills, "no SKILL.md found: the glob is broken"
    assert set(skills) <= set(scanned), "the scan skips a SKILL.md"
    assert _DOC not in scanned, "the document is read for citations as well as judged"
    everywhere = _markdown_files_by_walk()
    assert _DOC in everywhere, "the second instrument cannot see the document"
    assert set(scanned) == everywhere - {_DOC}, (
        f"the scan reads {len(scanned)} files; a second walk finds "
        f"{len(everywhere) - 1} markdown files besides the document"
    )
    assert len(scanned) > len(skills), (
        f"{len(scanned)} files scanned, {len(skills)} of them SKILL.md: "
        "no reference or template file is read"
    )
    cited = {
        name
        for path in scanned
        for name in _cited_sections(path.read_text(encoding="utf-8"))
    }
    assert {
        "Work the layers in ONE direction",
        "Verify the chain on the REMOTE, link by link",
    } <= cited, f"the scan no longer sees the known citations, saw {sorted(cited)}"


def test_the_citation_scan_flags_a_planted_citation_and_spares_a_near_miss() -> None:
    sign = chr(0xA7)
    planted = f"read `.ai/git-stacked-pr-workflow.md` {sign}\n*Some Heading* first."
    near_miss = "the cascade forms live in `.ai/git-stacked-pr-workflow.md` as a whole."
    assert _cited_sections(planted) == ["Some Heading"]
    assert _cited_sections(near_miss) == []


def test_a_citation_name_wrapped_across_lines_resolves_to_its_heading() -> None:
    sign = chr(0xA7)
    heading = "Verify the chain on the REMOTE, link by link"
    planted = (
        f"see `.ai/git-stacked-pr-workflow.md` {sign} *Verify the chain on the\n"
        "  REMOTE, link by link* before you cascade."
    )
    # The break is inside the name, so only the whitespace fold can join the two halves; a
    # plant whose name the bare pattern can already read would leave the fold untested.
    assert _CITATION.findall(planted) != [heading], "the plant does not wrap its name"
    assert _cited_sections(planted) == [heading]
    assert heading in {h.text for h in _headings(_text())}, "the heading is gone"


# --- neutrality -------------------------------------------------------------------------

_PROJECT = "Acme" + "Backend"
_PRODUCT = "Acme" + "Portal"
_SERVICE = "acme" + "-service"
_CLOUD_PROJECT = "example" + "-project"
_CLOUD_CLI = "g" + "cloud"
_CLOUD_BUILD = "cloud" + "build"
_CLOUD_RUN = "Cloud" + " Run"
_REGION = "region" + "-example1"
_PR_RANGE = "#" + "123"
_BUILD_TOOL = "dot" + "net"
_SOLUTION = ".s" + "ln"
_AREA = "zz" + "area"


class _Class(NamedTuple):
    pattern: re.Pattern[str]
    alternatives: tuple[str, ...]  # the regex source of each shape the class forbids
    planted: tuple[
        str, ...
    ]  # planted[i] holds the shape of alternatives[i], and no other
    near_miss: str  # a sentence that talks about the same thing without the detail


def _class(
    alternatives: tuple[str, ...],
    planted: tuple[str, ...],
    near_miss: str,
    flags: int = re.IGNORECASE,
) -> _Class:
    pattern = re.compile("|".join(alternatives), flags)
    return _Class(pattern, alternatives, planted, near_miss)


# Classes of text the document must not hold: project detail, and a second spelling of the
# trunk placeholder. Each class lists its alternatives one by one with one planted shape per
# alternative, so that deleting any single alternative from a pattern turns a test red.
_CLASSES: dict[str, _Class] = {
    "project, product or area name": _class(
        (_PROJECT, _PRODUCT, _SERVICE, _CLOUD_PROJECT, rf"wip\({_AREA}\)"),
        (
            f"It also holds {_PROJECT}'s recipes.",
            f"the {_PRODUCT} trigger",
            f"deploys {_SERVICE} to a region",
            f"--project {_CLOUD_PROJECT}-123456",
            f"`wip({_AREA}): park` as a subject",
        ),
        "It also holds the project's recipes; a commit subject such as `wip(<scope>)`.",
    ),
    "cloud service or deploy command": _class(
        (_CLOUD_CLI, "cloud" + r"[ -]?build", "cloud" + r"[ -]run", _REGION),
        (
            f"`{_CLOUD_CLI} auth list` first",
            f"the {_CLOUD_BUILD}.yaml file",
            f"deployed to {_CLOUD_RUN}",
            f"--region {_REGION}",
        ),
        "list the newest deploy revisions with the project's own read-only command",
    ),
    "pull-request number": _class(
        (r"#\d+",),
        (f"(the deepest so far was 11 PRs, {_PR_RANGE})",),
        "(the deepest seen was 11 PRs)",
        flags=0,
    ),
    "build tool or solution file": _class(
        (_BUILD_TOOL, re.escape(_SOLUTION) + r"\b", "ms" + "build"),
        (
            f"Run `{_BUILD_TOOL} test` there.",
            f"open App{_SOLUTION} in the IDE",
            "invoke " + "MS" + "Build on it",
        ),
        "Run `<build command>` and `<test command>` in the export.",
    ),
    "trunk called dev": _class(
        (r"(?<![\w/])dev(?![\w/])", r"origin/dev(?![\w/])"),
        (
            "`behind-dev == 0` on the branch",
            "`git cherry -v origin/dev <ref>`",
        ),
        "`git cherry -v origin/<trunk> <ref>`; a developer, a development branch and "
        "`/dev/null` are not the trunk",
    ),
    "this repo": _class(
        ("this" + " repo",),
        ("a stacked-PR chain in this repo",),
        "a stacked-PR chain in the project, and the repository's trunk",
    ),
    "AGENTS.md rule citation": _class(
        (r"AGENTS\.md rule", r"AGENTS\.md gate-verdict rule", r"\(AGENTS\.md,"),
        (
            "(the AGENTS.md rule for it)",
            "(see the AGENTS.md gate-verdict rule for the trap)",
            "run it in the export (AGENTS.md, Testing)",
        ),
        "`AGENTS.md` for the branch and commit conventions; the project's own rule",
        flags=0,
    ),
    "dated CI line": _class(
        (r"CI repair", r"testing-conventions", r"\b20\d\d-\d\d\b(?!-\d)"),
        (
            "predates the CI repair of that month",
            "see the project's installed testing-conventions skill",
            "predates the 2026-05 notes",
        ),
        "public preview 2026-07-30; a green check is not evidence the tests pass",
    ),
    "second placeholder for the trunk": _class(
        (r"<integration-branch>",),
        ("`git log --grep=<short-sha> <integration-branch>`",),
        "the integration branch, which every recipe writes as `<trunk>`",
    ),
}


def _hits(pattern: re.Pattern[str], text: str) -> list[str]:
    return [m.group(0) for m in pattern.finditer(" ".join(text.split()))]


@pytest.mark.parametrize("name", list(_CLASSES))
def test_document_holds_no_project_detail(name: str) -> None:
    hits = _hits(_CLASSES[name].pattern, _text())
    assert not hits, f"{name}: {hits[:5]}"


@pytest.mark.parametrize("name", list(_CLASSES))
def test_the_scan_flags_the_old_shape_and_spares_the_near_miss(name: str) -> None:
    case = _CLASSES[name]
    assert len(case.planted) == len(case.alternatives), (
        f"{name}: {len(case.planted)} planted shapes "
        f"for {len(case.alternatives)} alternatives"
    )
    missed = [shape for shape in case.planted if not _hits(case.pattern, shape)]
    assert not missed, f"{name}: planted shapes not flagged: {missed}"
    assert not _hits(case.pattern, case.near_miss), f"{name}: near-miss was flagged"


@pytest.mark.parametrize("name", list(_CLASSES))
def test_each_planted_shape_is_hit_by_its_own_alternative_alone(name: str) -> None:
    case = _CLASSES[name]
    alternatives = [re.compile(a, case.pattern.flags) for a in case.alternatives]
    for index, shape in enumerate(case.planted):
        hit = [i for i, rx in enumerate(alternatives) if _hits(rx, shape)]
        assert hit == [index], f"{name}: shape {index} {shape!r} is hit by {hit}"


@pytest.mark.parametrize("name", list(_CLASSES))
def test_the_scan_sees_a_forbidden_string_wrapped_across_lines(name: str) -> None:
    case = _CLASSES[name]
    for shape in case.planted:
        wrapped = shape.replace(" ", "\n")
        assert _hits(case.pattern, wrapped), f"{name}: {wrapped!r} not flagged"


def test_the_wrap_check_has_shapes_that_need_the_fold() -> None:
    needing = [
        shape
        for case in _CLASSES.values()
        for shape in case.planted
        if not case.pattern.search(shape.replace(" ", "\n"))
        and _hits(case.pattern, shape.replace(" ", "\n"))
    ]
    assert needing, (
        "no planted shape needs the whitespace fold: the wrap check is empty"
    )


def test_the_scan_flags_every_class_in_one_planted_document() -> None:
    planted = "\n".join(shape for c in _CLASSES.values() for shape in c.planted)
    near_miss = "\n".join(c.near_miss for c in _CLASSES.values())
    flagged = {n for n, c in _CLASSES.items() if _hits(c.pattern, planted)}
    assert flagged == set(_CLASSES)
    assert not [n for n, c in _CLASSES.items() if _hits(c.pattern, near_miss)]


def test_a_git_version_number_appears_only_as_a_measured_on_tag() -> None:
    def untagged(text: str) -> list[str]:
        folded = _fold(text)
        return [
            m.group(0)
            for m in re.finditer(r"git \d+\.\d+", folded)
            if folded[max(0, m.start() - len("measured on ")) : m.start()]
            != "measured on "
        ]

    assert untagged("experimental in git 2.55: read the help") == ["git 2.55"]
    assert untagged("experimental, measured on git 2.55: read the help") == []
    assert not untagged(_text())


# --- wording ----------------------------------------------------------------------------


def test_intro_is_true_of_the_whole_document() -> None:
    text = _text()
    first = next(h.line for h in _headings(text) if h.level == 2)
    intro = "\n".join(text.splitlines()[:first])
    folded = _fold(intro)
    assert "both rules below" not in folded, "the intro still counts two rules"
    assert "each rule below cost real work to learn" in folded
    assert "silently drops a commit or closes a pr" in folded
    assert "recipes for delivering a branch from a shared checkout" in folded
    assert "`parallel-session-safety` owns the generic shared-index rules" in folded
    names = {(h.level, h.text) for h in _headings(text)}
    quoted = re.findall(r'"([^"]+)"', " ".join(intro.split()))
    assert quoted, "the intro cites no section by name"
    assert all((2, q) in names for q in quoted), f"unresolved citations: {quoted}"


def test_garbled_sentence_is_repaired() -> None:
    section = _fold(_section(_text(), _MERGED, 2))
    assert "but dev's one such commit" not in section
    assert (
        "reads as outstanding work, but the landed history may say otherwise. "
        'one such commit opens "splits <oid>" and adjudicates it piece by piece'
    ) in section


def test_related_holds_no_project_line() -> None:
    section = _section(_text(), "Related", 2)
    folded = _fold(section)
    assert "`agents.md` " in folded, "the AGENTS.md bullet is gone"
    assert "ci repair" not in folded
    assert "testing-conventions" not in folded
    assert not re.search(r"\b20\d\d-\d\d\b(?!-\d)", folded), "a dated line remains"


_WRAP = 100  # the width at which the document wraps its prose
_PUSHING = "Pushing a stack can start one CI build per branch"
_PUSHING_LINES = 5  # the section is a paragraph of at most this many wrapped lines


def _paragraph_lengths(section: str) -> list[int]:
    """The folded length of each paragraph, so that the measure ignores where lines wrap."""
    blocks = re.split(r"\n\s*\n", section)
    return [len(" ".join(block.split())) for block in blocks if block.strip()]


def test_pushing_section_is_a_short_generic_paragraph() -> None:
    section = _section(_text(), _PUSHING, 2)
    lengths = _paragraph_lengths(section)
    assert len(lengths) == 1, f"{len(lengths)} paragraphs, want 1"
    limit = _PUSHING_LINES * _WRAP
    assert lengths[0] <= limit, f"{lengths[0]} characters, want at most {limit}"
    assert "```" not in section, "a command block is back"


def _rewrapped(text: str, width: int) -> str:
    """The text filled to `width` columns the way an editor does: words are never split."""
    flat = " ".join(text.split())
    return textwrap.fill(flat, width, break_long_words=False, break_on_hyphens=False)


def test_the_paragraph_measure_ignores_wrapping_and_sees_a_long_paragraph() -> None:
    flat = " ".join(_section(_text(), _PUSHING, 2).split())
    wrapped = [_rewrapped(flat, width) for width in (40, 72, _WRAP)]
    newlines = [text.count("\n") for text in wrapped]
    assert newlines == sorted(newlines, reverse=True), "a narrower fill has fewer lines"
    assert newlines[0] > newlines[-1], "the control did not re-wrap"
    assert all(_paragraph_lengths(text) == [len(flat)] for text in wrapped)
    assert len(_paragraph_lengths("x " * 40 + "\n\n" + "y")) == 2
    assert _paragraph_lengths("word " * 120)[0] > _PUSHING_LINES * _WRAP


# (level, heading, phrases; matched in the section's own text, whitespace-folded and
# lower-cased: for a section with subsections that is its lead-in)
_TRAPS: list[tuple[int, str, tuple[str, ...]]] = [
    (
        2,
        _PUSHING,
        (
            "a push of any branch can start ci for it",
            "in the observed setup opening their prs started none",
            "name the expected builds in the hand-off",
            "never name a stack branch like the trunk",
            "a deploy condition may be keyed on that name",
            "prove that a push deployed nothing",
        ),
    ),
    (
        3,
        "Re-stacking without a checkout",
        (
            "`git rebase` is off the table",
            "without touching the working tree or the ref",
            "measured on git 2.55",
            "write the old tip down for rollback",
        ),
    ),
    (
        2,
        "Deciding whether finished branches may stay independent PRs",
        (
            "not two tips against `<trunk>`",
            "with that branch's own parent as the merge base",
            "one false conflict in 45 pairs (90 merges)",
            "give the operator the denominators",
            '"chaining is required" is not confused with "chaining is convenient"',
        ),
    ),
    (
        2,
        "Prove the composition, not only the merge",
        (
            "proves only that they do not conflict textually",
            "`<build command>` and `<test command>` in the export",
            "git archive <composed-commit> | tar -x -c <posix-dir>",
            "a posix-style path, not a backslash path",
            "read each exit code on its own line",
            "compose the exact combination the operator will release",
        ),
    ),
    (
        2,
        "Plumbing from a shared checkout",
        (
            "deliver a branch without ever checking it out",
            "create the ref last",
        ),
    ),
    (
        3,
        "Building a stack by plumbing",
        (
            "a failed predicate leaves nothing to undo",
            "an all-zero old value",
            "0000000000000000000000000000000000000000",
            "never pass an empty string for it",
            "windows powershell 5.1 drops an empty argument to a native program",
            "equal tree ids",
            "count the carriage-return bytes of a draft first",
        ),
    ),
    (
        3,
        "Edit a committed file by its blob bytes, not in an export",
        (
            "git cat-file blob <commit>:<path>",
            "git hash-object -w --no-filters",
            "a second run of the script must fail on its first assertion",
            "`git range-diff`",
        ),
    ),
    (
        3,
        "Prove the delivery left the checkout alone",
        (
            "`git status` before and after proves nothing either way",
            "one create-only ref and that ref's reflog entry, nothing else",
            "git write-tree",
            "`git --no-optional-locks`",
            "`git log -g --format='%gd %gn %gs'` adds who",
            "compare content hashes, never status rows or counts",
        ),
    ),
    (
        3,
        "Prove the tip",
        (
            "any correction to a plumbing-committed tip voids every proof",
            "none of the paths or ids the project keeps out of its history",
            "so that a zero is proven",
            "`<build command>`",
            "`<test command>`",
        ),
    ),
    (
        2,
        "Editing a file the operator holds uncommitted",
        (
            "at least ten unchanged lines away from every pending hunk",
            "git merge-file -p",
            "the exit code is the conflict count",
            "it must exit 1",
        ),
    ),
    (
        2,
        "Hand-over checks in a shared checkout",
        (
            "re-read in the same turn",
            "git ls-remote origin <trunk> <branch>",
            "run `git fetch origin <trunk>` and then `git rev-parse origin/<trunk>`",
            "git rev-parse origin/<trunk>",
            "a fetch that fails (an unreachable remote, say) leaves the same stale copy",
            "a commit on stale evidence stops (powershell): ```powershell "
            "git fetch origin <trunk>; if ($lastexitcode -ne 0 -or "
            "(git rev-parse origin/<trunk>) -ne '<verified base>') { throw } ```",
        ),
    ),
    (
        2,
        _MERGED,
        (
            "git log --grep=<short-sha> <trunk>",
            "lives only in its own reflog",
            "prove the bundle by restoring it",
            "git bundle create <file> ^<base> refs/heads/<branch>",
            "`git bundle verify` checks integrity and prerequisites, not that the "
            "bundle restores",
            "fetch <file> refs/heads/<branch>:refs/heads/<branch>",
            "fsck --connectivity-only",
        ),
    ),
]


@pytest.mark.parametrize(
    ("level", "heading", "phrases"), _TRAPS, ids=[heading for _l, heading, _p in _TRAPS]
)
def test_section_keeps_the_sentence_that_names_its_trap(
    level: int, heading: str, phrases: tuple[str, ...]
) -> None:
    section = _fold(_section(_text(), heading, level, own=True))
    missing = [p for p in phrases if p.lower() not in section]
    assert not missing, f"{heading!r} no longer says: {missing}"


# --- the kit-managed warning and the two recipes that under-delivered -------------------

_RESTACK = "Re-stacking without a checkout"
_COMPOSITION = "Prove the composition, not only the merge"

# What each added sentence must say, whitespace-folded and lower-cased like the traps above.
# The warning sits in the intro, above the first level-2 heading, where an adopter who edits
# the file sees it first; the other two sit in the section of the recipe they correct.
_BANNER = (
    "this file is kit-managed",
    "`--force`) overwrites an edited copy",
    "keep project-only lines in a separate file",
)
_REPLAY = (
    "when the range holds more than one branch",
    "add `--contained`",
    "only the tip's line is printed",
    "the lower branches keep their old commits",
    "replay one layer at a time",
)
_ARCHIVE = (
    "windows powershell 5.1 re-encodes the binary stream",
    "of that pipe (measured)",
    "`tar` cannot read it",
    "run the line in a posix shell (git bash)",
    "write the archive to a file first with `git archive -o <file>`",
)

# The passages as they read before the sentences were added, cut to the lead-in and the
# recipe line that each sentence follows. The intro is verbatim; the other two are abridged
# (shorter wording, fewer recipe lines): enough to plant the shape the checks must flag.
_OLD_INTRO = """\
# Stacked PR Workflow

Hard-won mechanics for maintaining a stacked-PR chain in the project (the deepest seen was 11 PRs).
Each rule below cost real work to learn and has a trap that silently drops a commit or closes a PR.

The later sections hold recipes for delivering a branch from a shared checkout without switching it
(see "Plumbing from a shared checkout" and "Hand-over checks in a shared checkout"); the kit's
`parallel-session-safety` owns the generic shared-index rules.
"""
_OLD_RESTACK = """\
In a dirty shared checkout that must not be switched, `git rebase` is off the table. `git replay`
(experimental, measured on git 2.55: read `git replay -h` first) computes the new commits and
prints the ref update without touching the working tree or the ref:

```bash
git replay --ref-action=print --onto <new-base> <old-base>..<branch>    # exit 0
```

Prove that only the base changed before moving anything: (1) each new commit's patch-id equals
the old commit's.
"""
_OLD_COMPOSITION = """\
A clean `git merge-tree` over a set of branches proves only that they do not conflict textually,
not that the combination builds or passes. Compose them as unreferenced commits, export, then
build and test what would ship:

```bash
git archive <composed-commit> | tar -x -C <posix-dir>          # a POSIX-style path
```

GNU tar (measured on 1.35) could not open a directory given with backslashes after `-C`, and it read
the `C:` of a drive-letter archive name (`-f`) as a host.
"""


def _intro(text: str) -> str:
    """The title and lead-in: everything above the first level-2 heading."""
    firsts = [h.line for h in _headings(text) if h.level == 2]
    assert firsts, "no level-2 heading: the intro cannot be cut"
    return "\n".join(text.splitlines()[: firsts[0]])


def _passages(text: str) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Each passage cut by its own heading, with the phrases it must hold."""
    return {
        "intro": (_intro(text), _BANNER),
        "restack": (_section(text, _RESTACK, 3), _REPLAY),
        "composition": (_section(text, _COMPOSITION, 2), _ARCHIVE),
    }


def _missing(passage: str, phrases: tuple[str, ...]) -> list[str]:
    folded = _fold(passage)
    return [p for p in phrases if p not in folded]


def _planted(
    intro: str, restack: str, composition: str, tail: str = "", first: str = "x"
) -> str:
    """A small document whose passages are cut by the same headings as the real one.

    `first` is the section right below the intro and `tail` the last one: text planted in
    either belongs to no passage, so a cut that runs into one of them is seen.
    """
    return (
        f"{intro}\n## First\n\n{first}\n\n"
        f"## Cascading\n\n### {_RESTACK}\n\n{restack}\n"
        f"## {_COMPOSITION}\n\n{composition}\n"
        f"## Tail\n\n{tail}\n"
    )


def test_the_document_warns_at_the_top_that_the_kit_manages_it() -> None:
    gaps = _missing(_intro(_text()), _BANNER)
    assert not gaps, f"the intro no longer says: {gaps}"


def test_restacking_names_contained_for_a_range_of_several_branches() -> None:
    gaps = _missing(_section(_text(), _RESTACK, 3), _REPLAY)
    assert not gaps, f"{_RESTACK!r} no longer says: {gaps}"


def test_the_archive_pipe_warns_about_windows_powershell() -> None:
    gaps = _missing(_section(_text(), _COMPOSITION, 2), _ARCHIVE)
    assert not gaps, f"{_COMPOSITION!r} no longer says: {gaps}"


def test_the_sentence_checks_flag_the_old_text_in_full() -> None:
    old = _planted(_OLD_INTRO, _OLD_RESTACK, _OLD_COMPOSITION)
    for name, (passage, phrases) in _passages(old).items():
        assert _missing(passage, phrases) == list(phrases), (
            f"{name}: not flagged in full"
        )


def test_the_sentence_checks_are_scoped_to_their_own_passage() -> None:
    real = _passages(_text())
    elsewhere = "\n\n".join(passage for passage, _phrases in real.values())
    for _passage, phrases in real.values():
        assert not _missing(elsewhere, phrases), "the control text lacks a phrase"
    old = _planted(
        _OLD_INTRO, _OLD_RESTACK, _OLD_COMPOSITION, first=elsewhere, tail=elsewhere
    )
    for name, (passage, phrases) in _passages(old).items():
        assert _missing(passage, phrases) == list(phrases), (
            f"{name}: counted from elsewhere"
        )
    with pytest.raises(AssertionError):
        _passages(old.replace(f"### {_RESTACK}", "### Renamed"))
    with pytest.raises(AssertionError):
        _intro("# Title\n\ntext, and no level-2 heading\n")


def test_the_sentence_checks_ignore_wrapping_and_each_phrase_counts_alone() -> None:
    for name, (passage, phrases) in _passages(_text()).items():
        narrow = _rewrapped(passage, 40)
        assert any(p not in narrow.lower() for p in phrases), (
            f"{name}: no phrase wrapped"
        )
        assert not _missing(narrow, phrases), f"{name}: a re-wrap hides a phrase"
        for phrase in phrases:
            without = _fold(passage).replace(phrase, "")
            assert _missing(without, phrases) == [phrase], f"{name}: {phrase!r} alone"
