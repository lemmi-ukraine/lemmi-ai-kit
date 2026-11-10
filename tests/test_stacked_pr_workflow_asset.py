"""The checks of the stacked pr workflow asset tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_every_section_a_skill_cites_is_a_heading_of_the_document`: every section a skill cites is a heading of the document
* `test_the_citation_scan_reads_every_skill_and_sees_the_known_citations`: the citation scan reads every skill and sees the known citations
* `test_the_citation_scan_flags_a_planted_citation_and_spares_a_near_miss`: the citation scan flags a planted citation and spares a near miss
* `test_a_citation_name_wrapped_across_lines_resolves_to_its_heading`: a citation name wrapped across lines resolves to its heading
* `test_document_holds_no_project_detail`: document holds no project detail
* `test_the_scan_flags_the_old_shape_and_spares_the_near_miss`: the scan flags the old shape and spares the near miss
* `test_each_planted_shape_is_hit_by_its_own_alternative_alone`: each planted shape is hit by its own alternative alone
* `test_the_scan_sees_a_forbidden_string_wrapped_across_lines`: the scan sees a forbidden string wrapped across lines
* `test_the_wrap_check_has_shapes_that_need_the_fold`: the wrap check has shapes that need the fold
* `test_the_scan_flags_every_class_in_one_planted_document`: the scan flags every class in one planted document
* `test_related_holds_no_project_line`: related holds no project line
"""

import os
import re
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


# --- wording ----------------------------------------------------------------------------


def test_related_holds_no_project_line() -> None:
    section = _section(_text(), "Related", 2)
    folded = _fold(section)
    assert "`agents.md` " in folded, "the AGENTS.md bullet is gone"
    assert "ci repair" not in folded
    assert "testing-conventions" not in folded
    assert not re.search(r"\b20\d\d-\d\d\b(?!-\d)", folded), "a dated line remains"


# --- the kit-managed warning and the two recipes that under-delivered -------------------
