"""Callers of `plan-critic` point at its run cap and restate none of its rules.

`plan-critic` owns how often one document is reviewed, what a later run may still edit, and what
each run resolves or drops. A caller that restates those rules goes stale each time they change. Six
callers did: the five review steps of `spec-driven-dev` told the reader to "resolve all findings
before continuing", and the first item of `initiative-planner`'s "Before presenting" told it to
resolve Blockers and Majors silently. Neither named the cap, so the review read as a loop that ends
only when nothing is left, and a second run was told to fix what the cap says to drop. Each of the
six now says the review runs "within its own run cap" and holds no rule of the critic's.

What each test asserts:

* `test_each_caller_points_at_the_run_cap_and_restates_no_rule` has one row per place. The review
  step is cut by its heading, its numbered step and its lead; it must carry the pointer, keep the
  words that say what the review covers, and match no class of restated rule.
* `test_no_skill_file_restates_a_rule_plan_critic_owns` sweeps every Markdown file of every shipped
  skill except `plan-critic`'s own: a passage that names the critic, itself or in its heading, must
  match no class of restated rule.
* The instrument tests fire the cuts, the place check and the sweep's classes at planted text. The
  old shape of each place must be flagged, a re-wrap of the new shape must not be, a neighbour's old
  shape must not be read into a place, each part of the new shape dropped on its own must be flagged
  and nothing with it, and each class has a planted passage and a near-miss beside it.
* `test_the_planner_gives_a_true_reason_for_its_own_inheritance_check` cuts the same
  `initiative-planner` item again. The critic asks that check in its Step 3, so the item may not
  say the critic does not, and it must give the reason Step 3 states and point at that step.
  `test_the_critic_still_asks_the_question_the_planner_points_at` reads the critic and fails when
  the question or the sentence the pointer lands on is gone.

A guard that reads text never runs out of shapes. This one covers seven classes: "resolve all
findings", "resolve Blockers or Majors", "until nothing is left", "run it again", a number of runs of
a caller's own, a count of dimensions that is not the number the reference holds, and a finding's
fix described rather than quoted. The inheritance check reads one more shape at one place: the
critic's name followed directly by "does not", "cannot" or "never"; a claim about the critic that
leaves its name out is outside it.

THE SURFACE, in numbers the tests assert: 6 places in 2 files, and one sweep of the Markdown files
of every shipped skill but the critic's own, whose count is derived twice (a recursive glob and a
directory walk) and must agree. The two surfaces are disjoint: the critic's own files state its
rules, and the sweep never reads them. The seeded AGENTS.md template and the kit's own AGENTS.md hold
a plan-critic section too; they are another owner's surface and are not scanned here.

The inheritance check is not a sweep: it reads 1 of the 6 places, and it reads Step 3 of the
critic's own SKILL.md only to see that the pointer still lands, never to judge it by the sweep's
classes. Its planted table is counted too, 6 flagged and 3 near-misses.
"""

import os
import re
import textwrap
from pathlib import Path
from typing import NamedTuple

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_SKILLS = shipped_skill_dirs()
_CRITIC = _SKILLS["plan-critic"]
_DEV = _SKILLS["spec-driven-dev"] / "SKILL.md"
_PLANNER = _SKILLS["initiative-planner"] / "SKILL.md"
_DIMENSIONS = _CRITIC / "references" / "review-dimensions.md"

_POINTER = "within its own run cap"
_EN = chr(0x2013)
_EM = chr(0x2014)

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_NUMBERED_STEP = re.compile(r"^\d+\.\s")
_NAMES_CRITIC = re.compile(r"plan[- ]critic", re.IGNORECASE)

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
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


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


def _step(block: str, lead: str, where: str) -> str:
    """A numbered step: the line that starts with `lead`, and every line after it up to the
    next numbered step that starts in column 0."""
    lines = block.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(lead):
            found = [line]
            for follow in lines[index + 1 :]:
                if _NUMBERED_STEP.match(follow):
                    break
                found.append(follow)
            return "\n".join(found)
    raise AssertionError(f"{where}: no step starting {lead!r}")


def _extent(lines: list[str], index: int) -> list[str]:
    """The list item that starts at `lines[index]`: its first line and the lines after it, however
    they are indented, up to a blank line, a heading, or a list item at its own indent or less."""
    indent = len(lines[index]) - len(lines[index].lstrip())
    found = [lines[index]]
    for follow in lines[index + 1 :]:
        rest = follow.lstrip()
        if not rest or _HEADING.match(follow):
            break
        if _LIST_ITEM.match(follow) and len(follow) - len(rest) <= indent:
            break
        found.append(follow)
    return found


def _item(block: str, lead: str, where: str) -> str:
    """The first list item whose whitespace-folded text starts with `lead`, so a line break
    anywhere in the lead, inside it included, is not a different item."""
    wanted = _fold(lead)
    lines = block.split("\n")
    for index, line in enumerate(lines):
        if _LIST_ITEM.match(line):
            found = "\n".join(_extent(lines, index))
            if _fold(found).startswith(wanted):
                return found
    raise AssertionError(f"{where}: no list item starting {lead!r}")


class _Unit(NamedTuple):
    line: int
    text: str
    heading: str


def _units(text: str) -> list[_Unit]:
    """Every unit of the text, whitespace folded: a list item with its continuation lines, a
    paragraph, a table row, a heading or a fenced block. Each carries the nearest heading line
    above it, so a bullet that sits under a heading that names the critic is read as a passage
    about it. Blockquote markers are dropped."""
    units: list[_Unit] = []
    current: list[str] = []
    start = 0
    heading = ""
    in_fence = False

    def flush() -> None:
        if current:
            units.append(_Unit(start, _fold("\n".join(current)), heading))
            current.clear()

    for number, raw in enumerate(text.split("\n"), 1):
        line = re.sub(r"^\s*>+ ?", "", raw)
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_fence:
                current.append(line)
                flush()
                in_fence = False
            else:
                flush()
                start = number
                current.append(line)
                in_fence = True
            continue
        if in_fence:
            current.append(line)
            continue
        if not stripped:
            flush()
        elif stripped.startswith("#"):
            flush()
            start = number
            heading = stripped
            current.append(line)
            flush()
        elif stripped.startswith("|"):
            flush()
            start = number
            current.append(line)
            flush()
        elif _LIST_ITEM.match(line):
            flush()
            start = number
            current.append(line)
        else:
            if not current:
                start = number
            current.append(line)
    flush()
    return units


def _dimensions_held() -> int:
    held = len(re.findall(r"(?m)^## Dimension \d+ ", _text(_DIMENSIONS)))
    assert 0 < held < len(_NUMBER_WORDS), (
        f"{_DIMENSIONS.name} holds {held} dimension headings; the check reads 1 to 10"
    )
    return held


_HELD = _dimensions_held()


def _rules() -> tuple[tuple[str, re.Pattern[str]], ...]:
    """One pattern per class of restated rule, read against a folded passage."""
    others = "|".join(w for index, w in enumerate(_NUMBER_WORDS) if index != _HELD)
    flags = re.IGNORECASE
    return (
        (
            "resolve-all-findings",
            re.compile(
                r"\bresolve\s+(?:all|every|each)\b[^.;]{0,60}\bfindings?\b", flags
            ),
        ),
        (
            "resolve-blockers-or-majors",
            re.compile(r"\bresolve\s+(?:all\s+)?(?:blockers?|majors?)\b", flags),
        ),
        (
            "until-nothing-is-left",
            re.compile(
                r"\buntil\b[^.;]{0,60}\b(?:finds?\s+nothing"
                r"|no\s+(?:more\s+)?(?:findings?|issues?|blockers?)|clean|zero)\b",
                flags,
            ),
        ),
        (
            "run-it-again",
            re.compile(r"\b(?:run|re-?run|repeat)\b[^.;]{0,40}\bagain\b", flags),
        ),
        (
            "a-count-of-runs",
            re.compile(
                r"\b(?:twice|(?:two|three|four|five|[2-5])\s+(?:more\s+)?"
                r"(?:runs|times|passes|rounds|iterations|cycles))\b",
                flags,
            ),
        ),
        (
            "a-count-of-dimensions",
            re.compile(rf"\b(?:{others}|(?!{_HELD}\b)\d+)\s+dimensions\b", flags),
        ),
        (
            "a-fix-described",
            re.compile(
                r"\bResolution\b.{0,80}\b(?:what was changed|a description|describe)\b",
                flags,
            ),
        ),
    )


_RULES = _rules()


def _restated(folded: str) -> list[str]:
    """The restated rules a folded passage holds, as `class (matched text)`."""
    return [
        f"{name} ({match.group(0)!r})"
        for name, pattern in _RULES
        for match in pattern.finditer(folded)
    ]


def _is_caller(unit: _Unit) -> bool:
    return bool(_NAMES_CRITIC.search(unit.text) or _NAMES_CRITIC.search(unit.heading))


def _caller_matches(text: str) -> list[tuple[int, str, str]]:
    """(line, class, matched text) for every match in every unit that names the critic."""
    return [
        (unit.line, name, match.group(0))
        for unit in _units(text)
        if _is_caller(unit)
        for name, pattern in _RULES
        for match in pattern.finditer(unit.text)
    ]


def _place_problems(folded: str, scope: tuple[str, ...]) -> list[str]:
    """What is wrong with one review step: it must name the critic, point at its run cap, hold
    no restated rule and still say what the review covers."""
    problems: list[str] = []
    if not _NAMES_CRITIC.search(folded):
        problems.append("does not name plan-critic")
    if _POINTER not in folded:
        problems.append(f"does not point at the run cap ({_POINTER!r})")
    problems += [f"restates a rule of plan-critic: {hit}" for hit in _restated(folded)]
    problems += [
        f"has lost what the review covers ({words!r})"
        for words in scope
        if words not in folded
    ]
    return problems


class _Place(NamedTuple):
    key: str
    path: Path
    heading: str
    step: str  # the lead of the numbered step the item sits in; empty when it sits in none
    lead: str
    scope: tuple[str, ...]


_REVIEW_LEAD = "- **Run the plan-critic self-review**"
_PLACES: tuple[_Place, ...] = (
    _Place(
        "medium-step-7",
        _DEV,
        "### Medium Tasks",
        "",
        "7. **Run the plan-critic self-review**",
        (
            "full review over spec.md + tasks.md + test-plan.md (+ design.md if split out)",
        ),
    ),
    _Place(
        "large-step-1-requirements",
        _DEV,
        "### Large Tasks",
        "1. **Requirements**",
        _REVIEW_LEAD,
        ("full review",),
    ),
    _Place(
        "large-step-2-design",
        _DEV,
        "### Large Tasks",
        "2. **Design**",
        _REVIEW_LEAD,
        ("full review",),
    ),
    _Place(
        "large-step-3-tasks",
        _DEV,
        "### Large Tasks",
        "3. **Tasks**",
        _REVIEW_LEAD,
        (f"completeness-only pass (Dimensions 4{_EN}5 only)",),
    ),
    _Place(
        "large-step-4-verification",
        _DEV,
        "### Large Tasks",
        "4. **Verification plan**",
        _REVIEW_LEAD,
        ("verification pass",),
    ),
    _Place(
        "planner-before-presenting",
        _PLANNER,
        "## Before presenting",
        "",
        "1. Run **`plan-critic`**",
        (),
    ),
)


def _place_text(place: _Place, text: str, where: str) -> str:
    block = _section(text, place.heading, where)
    if place.step:
        block = _step(block, place.step, where)
    return _fold(_item(block, place.lead, where))


def _surface() -> list[Path]:
    """Every Markdown file of every shipped skill but the critic's own, by a recursive glob."""
    return sorted(
        path
        for root in _SKILLS.values()
        if root != _CRITIC
        for path in root.rglob("*.md")
    )


def _surface_by_walk() -> list[Path]:
    """The same files by a directory walk: a second instrument for the count."""
    found: list[Path] = []
    for name, root in _SKILLS.items():
        if name == "plan-critic":
            continue
        for folder, _, files in os.walk(root):
            found.extend(Path(folder) / file for file in files if file.endswith(".md"))
    return sorted(found)


class _Sweep(NamedTuple):
    files: int
    units: int
    callers: int
    hits: list[str]


def _sweep(surface: list[Path]) -> _Sweep:
    units = 0
    callers = 0
    hits: list[str] = []
    for path in surface:
        text = _text(path)
        cut = _units(text)
        units += len(cut)
        callers += sum(_is_caller(unit) for unit in cut)
        hits += [
            f"{path.parent.name}/{path.name}:{line}: {name} ({matched!r})"
            for line, name, matched in _caller_matches(text)
        ]
    return _Sweep(len(surface), units, callers, hits)


# --- the change ---------------------------------------------------------------------------


@pytest.mark.parametrize("place", _PLACES, ids=[place.key for place in _PLACES])
def test_each_caller_points_at_the_run_cap_and_restates_no_rule(place: _Place) -> None:
    where = f"{place.path.parent.name} SKILL.md, {place.key}"
    folded = _place_text(place, _text(place.path), where)
    problems = _place_problems(folded, place.scope)
    assert not problems, f"{where}: " + "; ".join(problems)


def test_no_skill_file_restates_a_rule_plan_critic_owns() -> None:
    sweep = _sweep(_surface())
    assert not sweep.hits, (
        f"a caller restates a rule plan-critic owns ({len(sweep.hits)} hits in "
        f"{sweep.files} files, {sweep.callers} caller passages of {sweep.units} units):\n"
        + "\n".join(sweep.hits)
    )


# --- planted text: the instruments --------------------------------------------------------

_REVIEW = "**Run the plan-critic self-review** (the `plan-critic` skill)"
_OLD: dict[str, str] = {
    "medium-step-7": (
        f"7. {_REVIEW} {_EM} full review over spec.md + tasks.md + test-plan.md (+ design.md if "
        "split out). Resolve all findings before continuing. If any Blockers or Questions "
        "remain, surface them in the presentation."
    ),
    "large-step-1-requirements": (
        f"   - {_REVIEW} {_EM} full review. Resolve all findings before continuing. If any "
        "Blockers or Questions remain unresolved, surface them in the presentation."
    ),
    "large-step-2-design": (
        f"   - {_REVIEW} {_EM} full review. Resolve all findings before continuing. If any "
        "Blockers or Questions remain unresolved, surface them in the presentation."
    ),
    "large-step-3-tasks": (
        f"   - {_REVIEW} {_EM} completeness-only pass (Dimensions 4{_EN}5 only). Resolve all "
        "findings before continuing. If any Blockers or Questions remain unresolved, surface "
        "them in the presentation."
    ),
    "large-step-4-verification": (
        f"   - {_REVIEW} {_EM} verification pass. Resolve all\n     findings before continuing"
    ),
    "planner-before-presenting": (
        "1. Run **`plan-critic`** over the artifacts, its Step 2.7 sequencing check included "
        "(AGENTS.md\n   requires it before *any* plan is presented). Resolve Blockers and Majors "
        "silently; surface anything\n   needing operator input at the top."
    ),
}
_NEW: dict[str, str] = {
    "medium-step-7": (
        f"7. {_REVIEW} {_EM} full review over spec.md + tasks.md + test-plan.md (+ design.md if "
        "split out), within its own run cap. If any Blockers or Questions remain, surface them "
        "in the presentation."
    ),
    "large-step-1-requirements": (
        f"   - {_REVIEW} {_EM} full review, within its own run cap. If any Blockers or "
        "Questions remain unresolved, surface them in the presentation."
    ),
    "large-step-2-design": (
        f"   - {_REVIEW} {_EM} full review, within its own run cap. If any Blockers or "
        "Questions remain unresolved, surface them in the presentation."
    ),
    "large-step-3-tasks": (
        f"   - {_REVIEW} {_EM} completeness-only pass (Dimensions 4{_EN}5 only), within its "
        "own run cap. If any Blockers or Questions remain unresolved, surface them in the "
        "presentation."
    ),
    "large-step-4-verification": (
        f"   - {_REVIEW} {_EM} verification pass, within its\n     own run cap"
    ),
    "planner-before-presenting": (
        "1. Run **`plan-critic`** over the artifacts, its Step 2.7 sequencing check included "
        "(AGENTS.md\n   requires it before *any* plan is presented), within its own run cap; "
        "surface anything\n   needing operator input at the top."
    ),
}
_PLACE_BY_KEY = {place.key: place for place in _PLACES}


def _swap(text: str, old: str, new: str) -> str:
    """A planted edit that must find its anchor exactly once, so it cannot change nothing."""
    assert text.count(old) == 1, f"planted edit: {old!r} stands {text.count(old)} times"
    return text.replace(old, new)


def _re_wrapped(item: str, width: int) -> str:
    """The item re-wrapped at `width`, its continuation lines three columns deeper than its first;
    it must differ from the item, so a planted re-wrap is never the shipped shape again."""
    folded = _fold(item)
    indent = " " * (len(item) - len(item.lstrip()))
    wrapped = "\n".join(
        textwrap.wrap(
            folded,
            width,
            initial_indent=indent,
            subsequent_indent=indent + "   ",
            break_long_words=False,
            break_on_hyphens=False,
        )
    )
    assert wrapped != item, (
        f"planted re-wrap at {width} columns changed nothing: {item!r}"
    )
    return wrapped


def _fixture(place: _Place, item: str) -> str:
    """A small document around one review step: the place's section, its numbered step when it
    has one, the item, a sibling after it and then, where the next section or step starts, the
    OLD shape of another review step, which no cut of this place may read."""
    indent = " " * (len(item) - len(item.lstrip()))
    level = len(place.heading) - len(place.heading.lstrip("#"))
    lines = [place.heading, ""]
    if place.step:
        lines += [
            place.step,
            "   - Use the template.",
            item,
            f"{indent}- **STOP.** Present.",
        ]
        lines += ["", "9. **Another step**", _OLD["large-step-1-requirements"]]
    else:
        lines += [
            item,
            f"{indent}- **STOP.** Present.",
            "",
            f"{'#' * level} Next section",
        ]
        lines += [_OLD["large-step-1-requirements"]]
    return "\n".join(lines) + "\n"


_KEYS = [place.key for place in _PLACES]


@pytest.mark.parametrize("key", _KEYS)
def test_the_old_shape_of_each_place_is_flagged(key: str) -> None:
    place = _PLACE_BY_KEY[key]
    where = f"planted old {key}"
    folded = _place_text(place, _fixture(place, _OLD[key]), where)
    problems = _place_problems(folded, place.scope)
    assert any("does not point at the run cap" in p for p in problems), problems
    assert any("restates a rule of plan-critic" in p for p in problems), problems
    assert not any("has lost" in p for p in problems), problems


@pytest.mark.parametrize("key", _KEYS)
def test_the_new_shape_of_each_place_passes_however_it_is_re_wrapped(key: str) -> None:
    place = _PLACE_BY_KEY[key]
    indent = " " * (len(_NEW[key]) - len(_NEW[key].lstrip()))
    shapes = [_NEW[key]] + [_re_wrapped(_NEW[key], width) for width in (30, 52, 79)]
    shapes.append(indent + _fold(_NEW[key]))
    for item in shapes:
        folded = _place_text(place, _fixture(place, item), f"planted new {key}")
        assert not _place_problems(folded, place.scope), (key, item)
        assert not _caller_matches(item), (key, item)


@pytest.mark.parametrize("key", _KEYS)
def test_a_neighbours_old_shape_is_not_read_into_the_place(key: str) -> None:
    place = _PLACE_BY_KEY[key]
    document = _fixture(place, _NEW[key])
    assert document.count("Resolve all findings before continuing") == 1, document
    folded = _place_text(place, document, f"planted neighbour {key}")
    assert "Resolve all" not in folded, folded
    assert not _place_problems(folded, place.scope)


def test_the_place_check_names_each_part_it_enforces() -> None:
    new = _NEW["medium-step-7"]
    parts: tuple[tuple[str, str, str], ...] = (
        ("the pointer", _swap(new, ", within its own run cap", ""), "does not point"),
        (
            "an old sentence back",
            _swap(new, " If any", " Resolve all findings before continuing. If any"),
            "resolve-all-findings",
        ),
        (
            "a count of runs of its own",
            _swap(new, "run cap.", "run cap, twice."),
            "a-count-of-runs",
        ),
        ("the scope", _swap(new, "full review over", "review over"), "has lost"),
        ("the critic's name", new.replace("plan-critic", "reviewer"), "does not name"),
    )
    scope = _PLACE_BY_KEY["medium-step-7"].scope
    assert not _place_problems(_fold(new), scope)
    for label, mutated, fragment in parts:
        problems = _place_problems(_fold(mutated), scope)
        assert len(problems) == 1 and fragment in problems[0], (label, problems)


class _Plant(NamedTuple):
    label: str
    text: str
    flagged: tuple[str, ...] = ()


_RIGHT_WORD = _NUMBER_WORDS[_HELD]
_WRONG_WORD = next(word for word in ("five", "six") if word != _RIGHT_WORD)
_ALL = "resolve-all-findings"
_SEV = "resolve-blockers-or-majors"
_UNTIL = "until-nothing-is-left"

_CLASS_PLANTS: tuple[_Plant, ...] = (
    _Plant("resolve-all-findings", _OLD["large-step-1-requirements"], (_ALL,)),
    _Plant(
        "resolve-all-findings-re-wrapped", _OLD["large-step-4-verification"], (_ALL,)
    ),
    _Plant("resolve-blockers-and-majors", _OLD["planner-before-presenting"], (_SEV,)),
    _Plant(
        "resolve-all-blocker-and-major-findings",
        "- Resolve all Blocker and Major findings silently before presenting (plan-critic).",
        (_ALL, _SEV),
    ),
    _Plant(
        "until-it-finds-nothing",
        "Run plan-critic again until it finds nothing.",
        (_UNTIL, "run-it-again"),
    ),
    _Plant(
        "until-no-more-findings",
        "Run `plan-critic`; re-run it until no more findings remain.",
        (_UNTIL,),
    ),
    _Plant("twice", "Run the plan-critic review twice.", ("a-count-of-runs",)),
    _Plant("three-rounds", "Run plan-critic for three rounds.", ("a-count-of-runs",)),
    _Plant(
        "a-count-of-dimensions-that-differs",
        f"The plan-critic skill runs its {_WRONG_WORD} dimensions.",
        ("a-count-of-dimensions",),
    ),
    _Plant(
        "a-fix-described",
        "A plan-critic finding: Resolution: what was changed in the document.",
        ("a-fix-described",),
    ),
    _Plant(
        "restated-under-a-heading-that-names-the-critic",
        "### Plan self-review (plan-critic)\n- Run it before presenting.\n"
        "- Resolve all Blocker and Major findings silently before presenting.",
        (_ALL, _SEV),
    ),
    _Plant(
        "near-miss-the-pointer",
        "Run the plan-critic skill within its own run cap; surface what it leaves unresolved.",
    ),
    _Plant("near-miss-no-critic-named", "- Resolve all findings before continuing."),
    _Plant(
        "near-miss-the-right-count-of-dimensions",
        f"Run plan-critic; its {_RIGHT_WORD} dimensions are in the references.",
    ),
    _Plant(
        "near-miss-resolve-the-question",
        "The plan-critic skill reviews the document. Resolve the open question first.",
    ),
    _Plant(
        "near-miss-a-range-of-dimensions",
        f"Run the plan-critic skill {_EM} completeness-only pass (Dimensions 4{_EN}5 only).",
    ),
    _Plant(
        "near-miss-a-separate-unit",
        "Run the plan-critic skill within its own run cap.\n\n"
        "Resolve all findings before continuing.",
    ),
    _Plant(
        "near-miss-the-same-bullet-under-another-heading",
        "### Spec review\n- Run it before presenting.\n"
        "- Resolve all Blocker and Major findings silently before presenting.",
    ),
    _Plant(
        "near-miss-the-heading-scope-ends-at-the-next-heading",
        "### Plan self-review (plan-critic)\n- Run it before presenting.\n\n"
        "### Something else\n- Resolve all findings before continuing.",
    ),
)

_PLANT_COUNTS = {"class plants": 19, "places": 6, "old shapes": 6, "new shapes": 6}


@pytest.mark.parametrize(
    "plant", _CLASS_PLANTS, ids=[plant.label for plant in _CLASS_PLANTS]
)
def test_the_sweep_flags_each_class_and_passes_each_near_miss(plant: _Plant) -> None:
    found = sorted({name for _, name, _ in _caller_matches(plant.text)})
    assert found == sorted(plant.flagged), f"{plant.label}: flagged {found}"


def test_every_class_has_a_planted_passage() -> None:
    planted = {name for plant in _CLASS_PLANTS for name in plant.flagged}
    assert planted == {name for name, _ in _RULES}, sorted(
        {name for name, _ in _RULES} ^ planted
    )


def test_the_planted_tables_keep_their_stated_size() -> None:
    sizes = {
        "class plants": len(_CLASS_PLANTS),
        "places": len(_PLACES),
        "old shapes": len(_OLD),
        "new shapes": len(_NEW),
    }
    assert sizes == _PLANT_COUNTS, f"a planted table changed size: {sizes}"
    assert set(_OLD) == set(_NEW) == set(_KEYS)
    assert len({place.path for place in _PLACES}) == 2
    labels = [plant.label for plant in _CLASS_PLANTS]
    assert len(labels) == len(set(labels)), f"a label repeats: {labels}"


def test_the_sweep_surface_is_stated_in_numbers() -> None:
    surface = _surface()
    walked = _surface_by_walk()
    assert surface == walked, (
        f"a recursive glob finds {len(surface)} files, a walk {len(walked)}"
    )
    assert len(set(surface)) == len(surface)
    assert not [path for path in surface if path.is_relative_to(_CRITIC)], (
        "the sweep reads the critic's own files, which state its rules"
    )
    assert _DEV in surface and _PLANNER in surface
    review_steps = [
        unit
        for unit in _units(_text(_DEV))
        if re.match(
            r"(?:[-*+]|\d+[.)])\s+\*\*Run the plan-critic self-review\*\*", unit.text
        )
    ]
    rows = [place for place in _PLACES if place.path == _DEV]
    assert len(review_steps) == len(rows), (
        f"spec-driven-dev has {len(review_steps)} review steps and the table {len(rows)} rows"
    )
    empty = [path.name for path in surface if not _text(path).strip()]
    assert not empty, f"files with no text, so the sweep saw nothing in them: {empty}"
    sweep = _sweep(surface)
    assert sweep.files == len(surface)
    assert sweep.units >= sweep.callers >= len(_PLACES), sweep[:3]
    for place in _PLACES:
        where = f"{place.path.parent.name} SKILL.md, {place.key}"
        cut = _place_text(place, _text(place.path), where)
        same = [unit for unit in _units(_text(place.path)) if unit.text == cut]
        assert same, f"{where}: the section cut and the unit cut disagree"
        assert all(_is_caller(unit) for unit in same), f"{where}: the sweep skips it"


def test_the_cuts_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "### An aside on ## Alpha",
            "decoy body",
            "## Alpha",
            "1. **First**",
            "   - lead item, first line",
            "     a lazy continuation",
            "   - sibling",
            "```",
            "# a comment inside a fence is not a heading",
            "```",
            "2. **Second**",
            "   - lead item, in the second step",
            "## Beta",
            "after the section",
        ]
    )
    alpha = _section(planted, "## Alpha", "planted")
    assert (
        alpha.startswith("## Alpha\n1. **First**") and "after the section" not in alpha
    )
    assert "a comment inside a fence" in alpha
    first = _step(alpha, "1. **First**", "planted")
    assert "second step" not in first and "sibling" in first
    item = _item(first, "- lead item", "planted")
    assert item == "   - lead item, first line\n     a lazy continuation", item
    assert "second step" in _item(
        _step(alpha, "2. **Second**", "planted"), "- lead", "p"
    )
    for call in (
        lambda: _section(planted, "## Gamma", "planted"),
        lambda: _step(alpha, "3. **Third**", "planted"),
        lambda: _item(first, "- absent", "planted"),
    ):
        with pytest.raises(AssertionError, match="no (heading|step|list item)"):
            call()
    midline = "see the - lead item below\n- another"
    with pytest.raises(AssertionError, match="no list item"):
        _item(midline, "- lead item", "planted")
    broken = "   - lead\n     item, first line\n   - sibling"
    assert _item(broken, "- lead item", "planted") == "   - lead\n     item, first line"


# --- the inheritance check: the reason a caller gives for it must be true ------------------

_INHERITANCE_PLACE = _PLACE_BY_KEY["planner-before-presenting"]
_ASKED_AT = "`plan-critic` Step 3"
_REASON = "a review pass cannot audit its own framing"
_QUESTION = "**Inherited framing**"
_APOS = f"['{chr(0x2019)}]"
_LACKS_A_CHECK = re.compile(
    rf"\bplan[- ]critic\b[`*_]*\s+(?:does\s+not|doesn{_APOS}t|cannot|can{_APOS}t|never)\b",
    re.IGNORECASE,
)


def _inheritance_problems(folded: str) -> list[str]:
    """What is wrong with the reason an item gives for running the inheritance check itself.

    The critic asks that check in its Step 3, so the item may not say the critic does not. It
    must give the reason the critic states there and point at the step that asks it.
    """
    problems = [
        f"says the critic lacks a check it has ({match.group(0)!r})"
        for match in _LACKS_A_CHECK.finditer(folded)
    ]
    if _REASON not in folded:
        problems.append(f"does not give the reason ({_REASON!r})")
    if _ASKED_AT not in folded:
        problems.append(f"does not point at the step that asks it ({_ASKED_AT!r})")
    return problems


def _target_problems(critic_text: str) -> list[str]:
    """What the pointer no longer lands on: Step 3 of the critic must still ask the question and
    still say the reason the caller gives. A critic with no Step 3 fails loudly."""
    step = _fold(_section(critic_text, "### Step 3", "plan-critic SKILL.md"))
    problems: list[str] = []
    if _QUESTION not in step:
        problems.append(f"Step 3 of plan-critic no longer asks {_QUESTION}")
    if _REASON not in step.lower():
        problems.append(f"Step 3 of plan-critic no longer says {_REASON!r}")
    return problems


def test_the_planner_gives_a_true_reason_for_its_own_inheritance_check() -> None:
    place = _INHERITANCE_PLACE
    where = f"{place.path.parent.name} SKILL.md, inheritance check"
    problems = _inheritance_problems(_place_text(place, _text(place.path), where))
    assert not problems, f"{where}: " + "; ".join(problems)


def test_the_critic_still_asks_the_question_the_planner_points_at() -> None:
    problems = _target_problems(_text(_CRITIC / "SKILL.md"))
    assert not problems, "; ".join(problems)


_INHERITANCE_OLD = (
    "1. Run **`plan-critic`** over the artifacts, within its own run cap; surface anything\n"
    "   needing operator input at the top. **Then run the inheritance check yourself, because\n"
    "   `plan-critic` does not.** It once missed three scope gaps, each an unexamined\n"
    "   inheritance rather than an inconsistency."
)
_INHERITANCE_NEW = (
    "1. Run **`plan-critic`** over the artifacts, within its own run cap; surface anything\n"
    "   needing operator input at the top. **Then run the inheritance check yourself: a review\n"
    "   pass cannot audit its own framing** (`plan-critic` Step 3). It once missed three scope\n"
    "   gaps, each an unexamined inheritance rather than an inconsistency."
)


def test_old_inheritance_clause_is_flagged_new_one_passes_however_wrapped() -> None:
    place = _INHERITANCE_PLACE
    old = _place_text(
        place, _fixture(place, _INHERITANCE_OLD), "planted old inheritance"
    )
    assert "`plan-critic` does not" in old, old
    assert [problem.split(" (")[0] for problem in _inheritance_problems(old)] == [
        "says the critic lacks a check it has",
        "does not give the reason",
        "does not point at the step that asks it",
    ]
    shapes = [_INHERITANCE_NEW, _fold(_INHERITANCE_NEW)]
    shapes += [_re_wrapped(_INHERITANCE_NEW, width) for width in (30, 52, 79)]
    for shape in shapes:
        folded = _place_text(place, _fixture(place, shape), "planted new inheritance")
        assert not _inheritance_problems(folded), shape
    document = _fixture(place, _INHERITANCE_NEW) + _INHERITANCE_OLD + "\n"
    neighbour = _place_text(place, document, "planted neighbour inheritance")
    assert "does not" not in neighbour and not _inheritance_problems(neighbour), (
        neighbour
    )


def test_the_inheritance_check_names_each_part_it_enforces() -> None:
    new = _fold(_INHERITANCE_NEW)
    parts: tuple[tuple[str, str, str], ...] = (
        (
            "the reason",
            _swap(new, _REASON, "a review pass reads the plan"),
            "does not give",
        ),
        ("the pointer", _swap(new, f" ({_ASKED_AT})", ""), "does not point"),
        (
            "a claim that the critic lacks it",
            _swap(new, "Step 3).", "Step 3), because `plan-critic` does not."),
            "lacks a check",
        ),
    )
    assert not _inheritance_problems(new)
    for label, mutated, fragment in parts:
        problems = _inheritance_problems(mutated)
        assert len(problems) == 1 and fragment in problems[0], (label, problems)


_LACKS_PLANTS: tuple[tuple[str, str, int], ...] = (
    ("does-not", "because `plan-critic` does not.", 1),
    ("does-not-after-a-line-break", "because `plan-critic`\n   does not.", 1),
    ("doesnt", "because plan-critic doesn't ask it.", 1),
    (
        "doesnt-with-a-curly-apostrophe",
        f"because plan-critic doesn{chr(0x2019)}t ask it.",
        1,
    ),
    ("cannot-under-bold", "because **plan-critic** cannot see it.", 1),
    ("never", "because plan-critic never asks.", 1),
    ("near-miss-another-subject", "because the compiler does not.", 0),
    ("near-miss-the-critic-asks", "plan-critic asks it; your plan does not say so.", 0),
    (
        "near-miss-the-name-without-a-negation",
        "because `plan-critic` Step 3 asks it.",
        0,
    ),
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [(text, expected) for _, text, expected in _LACKS_PLANTS],
    ids=[label for label, _, _ in _LACKS_PLANTS],
)
def test_the_lacks_a_check_shape_flags_each_plant_and_passes_each_near_miss(
    text: str, expected: int
) -> None:
    assert len(_LACKS_A_CHECK.findall(_fold(text))) == expected, text


_CRITIC_STEPS = (
    "### Step 2 - Run the Dimensions\n"
    "A dimension is not a question.\n"
    "### Step 3 - Apply the Universal Challenge Questions\n"
    "5. **Inherited framing**: which claims did this plan inherit rather than measure?\n"
    "   - **A review pass cannot audit its own framing.** It reads the plan against itself.\n"
    "### Step 4 - Resolve What You Can\n"
    "Resolve what you can.\n"
)


def test_the_target_check_flags_a_critic_that_lost_the_question_or_sentence() -> None:
    assert not _target_problems(_CRITIC_STEPS)
    step_three = "### Step 3 - Apply the Universal Challenge Questions\n"
    mutants: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        (
            "the question renamed",
            _swap(_CRITIC_STEPS, _QUESTION, "**Provenance**"),
            ("no longer asks",),
        ),
        (
            "the sentence reworded",
            _swap(_CRITIC_STEPS, "audit its own framing", "see its own framing"),
            ("no longer says",),
        ),
        (
            "both moved out of Step 3",
            _swap(
                _CRITIC_STEPS,
                step_three,
                step_three + "### Step 4 - Resolve What You Can\n",
            ),
            ("no longer asks", "no longer says"),
        ),
    )
    for label, mutated, fragments in mutants:
        problems = _target_problems(mutated)
        assert len(problems) == len(fragments), (label, problems)
        assert all(
            fragment in problem
            for fragment, problem in zip(fragments, problems, strict=True)
        ), (label, problems)
    with pytest.raises(AssertionError, match="no heading starting"):
        _target_problems("### Step 4 - Resolve What You Can\nnothing else\n")


def test_the_inheritance_plants_keep_their_stated_size() -> None:
    flagged = [label for label, _, expected in _LACKS_PLANTS if expected]
    near_misses = [label for label, _, expected in _LACKS_PLANTS if not expected]
    assert (len(flagged), len(near_misses)) == (6, 3), (flagged, near_misses)
    labels = flagged + near_misses
    assert len(labels) == len(set(labels)), f"a label repeats: {labels}"
