"""`spec-driven-dev` says one thing about each size's documents, and names the project's own
conventions and lint command where it used to name one stack's.

The skill called a Medium spec "a single combined document" in its size table, said "(single doc)"
in the size reference's table and "create single combined document" in its override list, told the
reader to "Create two documents" and then listed a spec, a task breakdown and a test plan, and
announced "lightweight spec + tasks" as the plan. Its override list sent "a full spec" to "all three
documents" while its Large block creates four, and its Large lines left the verification plan out.
Its design guide named one Python layout, the skill that serves only that layout, Pydantic and
Alembic, and headed its risk list "in This Project"; its Challenge Protocol and its checklist named
the vertical slice rules as the project's own; its requirements guide called its actor table the
project's own; its Light gate ran `uv run ruff check`, one stack's linter. The design template that
every Technical Approach starts from, in the copy every project is seeded with and in the kit's own,
told its author to reference the vertical slice architecture.

What the text says now: a Medium task gets three documents (spec, tasks, test plan), and a design
document only past about 60 lines of Technical Approach; a Large task gets four (requirements,
design, tasks, verification plan); each in every place that names them. The design guide, the
Challenge Protocol and the checklist ask for the project's architecture conventions, and the Python
layout, the stack items, the risk list and the actor table are labelled as examples; the Light gate
runs the project's lint command. Both design templates ask for the project's architecture
conventions (AGENTS.md), in the same words.

A place is read as one ITEM: a list item, a paragraph, a table row, a heading or a fenced block,
together with every continuation line a re-wrap may have put after its first line. A needle is
searched in the item with whitespace folded, so a line end anywhere in a sentence, inside the needle
included, is not a different sentence; `test_an_item_place_holds_however_its_line_is_re_wrapped`
breaks each line at every space to show it, and
`test_the_python_layout_check_holds_however_its_label_is_re_wrapped` does the same for the design
guide's layout label, which the layout check reads as a section.

THE SURFACE, in numbers the tests assert: 5 files (the skill and its four references), 19 places in
them, 34 checks, 13 places whose line is re-wrapped, and one sweep of all 5 files for 9 retired
phrases. A second surface, asserted disjoint from the first: the 2 design templates (the seeded copy
and the kit's own), with 1 place in each, 2 checks per place, both places re-wrapped, the same
sweep, and the two copies equal on the line that names the conventions. Each check is fired at the
text its place carried before (`_OLD_*`, excerpts of the file as it stood), and must report it; the
sweep is fired at planted phrases, four of them wrapped over two lines, before its silence is
trusted.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO / "plugins" / "core" / "skills" / "spec-driven-dev"
_SKILL_MD = _SKILL_DIR / "SKILL.md"
_SIZE = _SKILL_DIR / "references" / "size-detection.md"
_DESIGN = _SKILL_DIR / "references" / "design-guide.md"
_REQUIREMENTS = _SKILL_DIR / "references" / "requirements-guide.md"
_PHASED = _SKILL_DIR / "references" / "phased-execution.md"
_FILES = (_SKILL_MD, _SIZE, _DESIGN, _REQUIREMENTS, _PHASED)
# The second surface: the design template a Technical Approach starts from, in the copy every
# project is seeded with and in the kit's own. Outside the skill's folder, so no file is in both.
_TEMPLATES: dict[str, Path] = {
    "design-template-seeded": _REPO
    / "plugins"
    / "core"
    / "src"
    / "lemmi_ai_kit"
    / "assets"
    / "ai"
    / "templates"
    / "design.md",
    "design-template-kit": _REPO / ".ai" / "templates" / "design.md",
}
_TEMPLATE_ANCHOR = "Describe the overall approach"
_HEADING = re.compile(r"^(#{1,6})\s")

# The old text carried these characters; they are built from their code points so that a retyped
# hyphen or arrow in an old excerpt cannot make a check that sees nothing look as if it works.
_EN = chr(0x2013)
_EM = chr(0x2014)
_ARROW = chr(0x2192)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks and quote markers dropped, whitespace folded to one space, so a
    re-wrapped line or a re-emphasised word is the same sentence."""
    return re.sub(r"\s+", " ", re.sub(r"^\s*>+ ?|[*`]", "", text, flags=re.M)).strip()


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or a
    higher level; a `#` line inside a fenced block is not a heading. A missing heading fails
    loudly, with the heading named."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        found = None if in_fence or fence else _HEADING.match(line)
        if fence:
            in_fence = not in_fence
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


_LIST_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")


def _squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _opens_item(line: str) -> bool:
    """A heading, a table row, a fence or a list marker starts a new piece of text. Any other
    non-blank line carries on the piece above it, however far it is indented."""
    return line.lstrip().startswith(("#", "|", "```")) or bool(_LIST_MARKER.match(line))


def _items(text: str) -> list[str]:
    """The text cut into the pieces a re-wrap cannot split: a fenced block, a heading, a table row,
    and a list item or a paragraph together with every continuation line after it, indented or in
    column 0. A blank line ends the piece; a heading or a table row never takes a continuation."""
    pieces: list[list[str]] = []
    current: list[str] | None = None
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if in_fence and current is not None:
                current.append(line)
                current = None
            else:
                current = [line]
                pieces.append(current)
            in_fence = not in_fence
        elif in_fence and current is not None:
            current.append(line)
        elif not line.strip():
            current = None
        elif current is None or _opens_item(line):
            current = [line]
            pieces.append(current)
            if line.lstrip().startswith(("#", "|")):
                current = None
        else:
            current.append(line)
    return ["\n".join(piece) for piece in pieces]


def _item_with(text: str, needle: str, where: str) -> str:
    """The one list item, paragraph, table row, heading or fenced block that contains `needle`,
    whatever its capitalisation and wherever a re-wrap has put a line end. None or several fail
    loudly, with the count named."""
    wanted = _squeeze(needle).lower()
    found = [item for item in _items(text) if wanted in _squeeze(item).lower()]
    if len(found) != 1:
        raise AssertionError(
            f"{where}: expected one item containing {needle!r}, found {len(found)}"
        )
    return found[0]


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


class _Place(NamedTuple):
    name: str
    path: Path
    locate: Callable[[str, str], str]
    checks: tuple[_Check, ...]
    old: str


def _says(*needles: str) -> Callable[[str], bool]:
    """Every needle is in the region, whatever its capitalisation."""
    wanted = [_plain(n).lower() for n in needles]
    return lambda region: all(n in _plain(region).lower() for n in wanted)


def _lacks(*needles: str) -> Callable[[str], bool]:
    wanted = [_plain(n).lower() for n in needles]
    return lambda region: all(n not in _plain(region).lower() for n in wanted)


def _in_section(heading: str) -> Callable[[str, str], str]:
    return lambda text, where: _section(text, heading, where)


def _on_item_with(needle: str) -> Callable[[str, str], str]:
    return lambda text, where: _item_with(text, needle, where)


# --- the text each place carried before ---------------------------------------------------------

_OLD_MEDIUM_BLOCK = """### Medium Tasks — Lightweight Spec

Create two documents:

1. Create `.specs/{task-name}/spec.md`
"""

_OLD_CLASSIFICATION = (
    f"- Total score 3{_EN}6 {_ARROW} **Medium** {_EM} lightweight spec "
    "(single combined document)"
)

_OLD_ANNOUNCEMENT = (
    "Proceeding with: {direct implementation | lightweight spec + tasks | full spec}"
)

_OLD_SIZE_ROW = f"| 3{_EN}6 | Medium | Lightweight spec (single doc) |"

_OLD_SIZE_OVERRIDE = (
    f'- "Just do a lightweight spec" {_ARROW} create single combined document'
)

_OLD_DESIGN_HEAD = f"""## Designing Within the Vertical Slice Architecture

All new components must follow the project's vertical slice architecture. Reference the
`vertical-slice` skill for the
canonical feature directory template.

Key constraints:
- Feature code lives in `backend/app/features/{{feature_name}}/`
- Layer flow: API {_ARROW} Service {_ARROW} Storage (never reverse)
- No cross-feature imports {_EM} use internal APIs or shared core modules
- One class per file, file name matches class name in snake_case
"""

_OLD_ENUMS = "- [ ] Enums placed correctly: `storage/enums/` for persisted, `services/enums/` for business-only"

_OLD_SCHEMAS = "- [ ] Request/response schemas defined as separate Pydantic models (one class per file)"

_OLD_ROUTE = "- [ ] Route registered in the feature's `routes.py`, included via `backend/app/api/api.py`"

_OLD_MIGRATION_RISK = (
    "- Alembic migration conflicts when multiple branches modify schema"
)

_OLD_LIGHT_GATE = f"""### Light Gate

Use for simple, low-risk phases (single layer, 2{_EN}3 tasks, no cross-feature impact).

Steps:
1. Run `uv run ruff check` on all modified files
2. Check lint/type diagnostics on all modified files
"""

_OLD_ACTORS_LABEL = "**Common actors in this project:**"

_OLD_LARGE_CLASS = f"- Total score 7+ {_ARROW} **Large** {_EM} full spec (requirements + design + tasks)"

_OLD_SIZE_LARGE_ROW = "| 7+ | Large | Full spec (requirements + design + tasks) |"

_OLD_FULL_SPEC_OVERRIDE = (
    f'- "Make this a full spec" {_ARROW} create all three documents regardless of score'
)

_OLD_RISKS_HEAD = """### Common Risks in This Project

- AI provider API latency spikes or rate limits
"""

_OLD_CONFLICT_EXAMPLE = (
    "1. **State the conflict clearly**: name the specific constraint it violates "
    "(e.g., the vertical slice rule, the earlier approved decision, the risk entry in the spec)."
)

_OLD_CHALLENGE_LIST = (
    "- Changes that contradict the project's vertical slice architecture rules"
)

_OLD_CHECKLIST_LINE = "- [ ] Design follows existing vertical slice architecture"

_OLD_TEMPLATE_APPROACH = (
    "{Describe the overall approach. Reference the vertical slice architecture and existing "
    "patterns where applicable.}"
)

# --- the places ---------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        "skill-medium-block",
        _SKILL_MD,
        _in_section("### Medium Tasks"),
        (
            _Check(
                "the block says three documents, and when a design is added",
                _says(
                    "Create three documents (spec, tasks, test plan); a design document "
                    "is added only when the Technical Approach runs past about 60 lines:"
                ),
            ),
            _Check("the block no longer says two", _lacks("Create two documents")),
        ),
        _OLD_MEDIUM_BLOCK,
    ),
    _Place(
        "skill-classification",
        _SKILL_MD,
        _on_item_with("**Medium**"),
        (
            _Check(
                "the Medium class names its three documents",
                _says("lightweight spec (spec + tasks + test plan)"),
            ),
            _Check(
                "the Medium class is no longer one combined document",
                _lacks("single combined document"),
            ),
        ),
        _OLD_CLASSIFICATION,
    ),
    _Place(
        "skill-announcement",
        _SKILL_MD,
        _on_item_with("Proceeding with:"),
        (
            _Check(
                "the announced plan names the test plan too",
                _says(
                    "{direct implementation | lightweight spec + tasks + test plan "
                    "| full spec}"
                ),
            ),
        ),
        _OLD_ANNOUNCEMENT,
    ),
    _Place(
        "size-table-row",
        _SIZE,
        _on_item_with("| Medium |"),
        (
            _Check(
                "the table row names the three documents",
                _says(
                    f"| 3{_EN}6 | Medium | Lightweight spec (spec + tasks + test plan) |"
                ),
            ),
            _Check("the table row no longer says single doc", _lacks("(single doc)")),
        ),
        _OLD_SIZE_ROW,
    ),
    _Place(
        "size-override",
        _SIZE,
        _on_item_with('"Just do a lightweight spec"'),
        (
            _Check(
                "the override creates the three Medium documents",
                _says("create the three Medium documents (spec, tasks, test plan)"),
            ),
            _Check(
                "the override no longer creates one combined document",
                _lacks("single combined document"),
            ),
        ),
        _OLD_SIZE_OVERRIDE,
    ),
    _Place(
        "design-guide-head",
        _DESIGN,
        _in_section("## Designing Within"),
        (
            _Check(
                "the heading names the project's architecture conventions",
                _says("## Designing Within the Project's Architecture Conventions"),
            ),
            _Check(
                "the intro points at the project's own rules",
                _says(
                    "must follow the project's architecture conventions: the layout, "
                    "layering and import rules that its AGENTS.md and installed "
                    "convention skills state"
                ),
            ),
            _Check(
                "the intro says what to write where the project states no conventions",
                _says(
                    "Where the project states none, name the structure the design follows."
                ),
            ),
            _Check(
                "the Python layout is a labelled example",
                _says(
                    "Example, for a Python backend laid out as vertical slices "
                    "(the project's own conventions replace it):"
                ),
            ),
            _Check(
                "no skill that serves one layout is named",
                _lacks("vertical-slice", "Vertical Slice Architecture"),
            ),
        ),
        _OLD_DESIGN_HEAD,
    ),
    _Place(
        "design-guide-enums-line",
        _DESIGN,
        _on_item_with("Enums placed"),
        (
            _Check(
                "the line defers to the project's conventions and shows its layout as one example",
                _says(
                    "Enums placed where the project's architecture conventions put them "
                    "(example: storage/enums/ for persisted, services/enums/ for "
                    "business-only)"
                ),
            ),
        ),
        _OLD_ENUMS,
    ),
    _Place(
        "design-guide-schemas-line",
        _DESIGN,
        _on_item_with("Request/response schemas"),
        (
            _Check(
                "the line defers to the project's conventions and shows Pydantic as one example",
                _says(
                    "Request/response schemas defined as separate typed models, as the "
                    "project's conventions require (example: Pydantic models, one class "
                    "per file)"
                ),
            ),
        ),
        _OLD_SCHEMAS,
    ),
    _Place(
        "design-guide-route-line",
        _DESIGN,
        _on_item_with("Route registered"),
        (
            _Check(
                "the line defers to the project's conventions and shows its routes file as one example",
                _says(
                    "Route registered where the project's architecture conventions put "
                    "routes (example: the feature's routes.py, included via "
                    "backend/app/api/api.py)"
                ),
            ),
        ),
        _OLD_ROUTE,
    ),
    _Place(
        "design-guide-migration-risk",
        _DESIGN,
        _on_item_with("migration conflicts"),
        (
            _Check(
                "the risk names migration conflicts, with Alembic as one example",
                _says(
                    "Migration conflicts when multiple branches modify the schema "
                    "(example: Alembic revision heads)"
                ),
            ),
        ),
        _OLD_MIGRATION_RISK,
    ),
    _Place(
        "light-gate",
        _PHASED,
        _in_section("### Light Gate"),
        (
            _Check(
                "the gate runs the project's lint command",
                _says(
                    "Run the project's lint command (AGENTS.md § Commands) on all "
                    "modified files"
                ),
            ),
            _Check("the gate no longer runs ruff", _lacks("uv run ruff")),
        ),
        _OLD_LIGHT_GATE,
    ),
    _Place(
        "actors-label",
        _REQUIREMENTS,
        _on_item_with("Common actors"),
        (
            _Check(
                "the actor table is labelled as examples",
                _says(
                    "Common actors (examples from a realtime AI backend; the project's "
                    "own actor list replaces them):"
                ),
            ),
            _Check(
                "the actor table is no longer called the project's own",
                _lacks("Common actors in this project"),
            ),
        ),
        _OLD_ACTORS_LABEL,
    ),
    _Place(
        "skill-large-class",
        _SKILL_MD,
        _on_item_with("**Large**"),
        (
            _Check(
                "the Large class names its verification plan beside the other documents",
                _says("full spec (requirements + design + tasks + verification plan)"),
            ),
        ),
        _OLD_LARGE_CLASS,
    ),
    _Place(
        "size-large-row",
        _SIZE,
        _on_item_with("| Large |"),
        (
            _Check(
                "the table row names the four Large documents",
                _says(
                    "| 7+ | Large | Full spec (requirements + design + tasks + "
                    "verification plan) |"
                ),
            ),
        ),
        _OLD_SIZE_LARGE_ROW,
    ),
    _Place(
        "size-full-spec-override",
        _SIZE,
        _on_item_with('"Make this a full spec"'),
        (
            _Check(
                "the override creates the four Large documents",
                _says(
                    "create the four Large documents (requirements, design, tasks, "
                    "verification plan) regardless of score"
                ),
            ),
            _Check(
                "the override no longer counts three documents",
                _lacks("create all three documents"),
            ),
        ),
        _OLD_FULL_SPEC_OVERRIDE,
    ),
    _Place(
        "design-guide-risks",
        _DESIGN,
        _on_item_with("Common Risks"),
        (
            _Check(
                "the risk list is labelled as examples",
                _says(
                    "### Common Risks (examples from a realtime AI backend; the "
                    "project's own risk list replaces them)"
                ),
            ),
            _Check(
                "the risk list is no longer called the project's own",
                _lacks("Common Risks in This Project"),
            ),
        ),
        _OLD_RISKS_HEAD,
    ),
    _Place(
        "skill-conflict-example",
        _SKILL_MD,
        _on_item_with("name the specific constraint it violates"),
        (
            _Check(
                "the example constraint is the project's architecture conventions",
                _says(
                    "(e.g., one of the project's architecture conventions, the earlier"
                ),
            ),
            _Check("the example names no slice rule", _lacks("vertical slice")),
        ),
        _OLD_CONFLICT_EXAMPLE,
    ),
    _Place(
        "skill-challenge-list",
        _SKILL_MD,
        _on_item_with("Changes that contradict"),
        (
            _Check(
                "the challenge covers the project's architecture conventions",
                _says("Changes that contradict the project's architecture conventions"),
            ),
            _Check("the challenge names no slice rule", _lacks("vertical slice")),
        ),
        _OLD_CHALLENGE_LIST,
    ),
    _Place(
        "skill-checklist-line",
        _SKILL_MD,
        _on_item_with("Design follows"),
        (
            _Check(
                "the checklist asks for the project's architecture conventions",
                _says("Design follows the project's architecture conventions"),
            ),
            _Check("the checklist names no slice rule", _lacks("vertical slice")),
        ),
        _OLD_CHECKLIST_LINE,
    ),
)

# The same place in each design template: the placeholder under Technical Approach.
_TEMPLATE_PLACES: tuple[_Place, ...] = tuple(
    _Place(
        name,
        path,
        _on_item_with(_TEMPLATE_ANCHOR),
        (
            _Check(
                "the placeholder asks for the project's architecture conventions",
                _says(
                    "Reference the project's architecture conventions (AGENTS.md) and "
                    "existing patterns where applicable."
                ),
            ),
            _Check("the placeholder names no slice rule", _lacks("vertical slice")),
        ),
        _OLD_TEMPLATE_APPROACH,
    )
    for name, path in _TEMPLATES.items()
)
_EVERY_PLACE = _PLACES + _TEMPLATE_PLACES

# What no file of the skill may say again, with the file each came from.
_RETIRED: tuple[tuple[str, str], ...] = (
    ("two documents for a Medium task", "create two documents"),
    ("a Medium spec as one doc", "(single doc)"),
    ("a Medium spec as one combined document", "single combined document"),
    ("a full spec as three documents", "create all three documents"),
    ("one stack's linter in a gate", "uv run ruff"),
    ("the skill that serves one layout", "vertical-slice"),
    ("one layout as the project's architecture", "vertical slice architecture"),
    ("a slice rule as the project's rule", "vertical slice rule"),
    ("the risk list as the project's own", "common risks in this project"),
)
# The retired phrases found in the old excerpts, by file, so the sweep is shown to see them.
_OLD_BY_FILE: dict[Path, tuple[str, set[str]]] = {
    _SKILL_MD: (
        "\n".join(
            (
                _OLD_MEDIUM_BLOCK,
                _OLD_CLASSIFICATION,
                _OLD_CONFLICT_EXAMPLE,
                _OLD_CHALLENGE_LIST,
                _OLD_CHECKLIST_LINE,
            )
        ),
        {
            "two documents for a Medium task",
            "a Medium spec as one combined document",
            "a slice rule as the project's rule",
            "one layout as the project's architecture",
        },
    ),
    _SIZE: (
        "\n".join((_OLD_SIZE_ROW, _OLD_SIZE_OVERRIDE, _OLD_FULL_SPEC_OVERRIDE)),
        {
            "a Medium spec as one doc",
            "a Medium spec as one combined document",
            "a full spec as three documents",
        },
    ),
    _DESIGN: (
        "\n".join((_OLD_DESIGN_HEAD, _OLD_RISKS_HEAD)),
        {
            "the skill that serves one layout",
            "one layout as the project's architecture",
            "the risk list as the project's own",
        },
    ),
    _PHASED: (_OLD_LIGHT_GATE, {"one stack's linter in a gate"}),
}
# The same for the design templates: the old placeholder carried one of the retired phrases.
_OLD_IN_TEMPLATE = (
    _OLD_TEMPLATE_APPROACH,
    {"one layout as the project's architecture"},
)


def _swept(text: str) -> set[str]:
    flat = _plain(text).lower()
    return {label for label, phrase in _RETIRED if phrase in flat}


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text, place.path.name)
    return [c.label for c in place.checks if not c.holds(region)]


# --- the tests ----------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_FILES) == 5, f"{len(_FILES)} files, not the 5 stated"
    on_disk = sorted(_SKILL_DIR.rglob("*.md"))
    assert on_disk == sorted(_FILES), (
        f"the skill holds {len(on_disk)} markdown files and the scan reads {len(_FILES)}; "
        f"only one side has {sorted(set(on_disk) ^ set(_FILES))}"
    )
    empty = [p.name for p in _FILES if not _read(p).strip()]
    assert not empty, f"empty files: {empty}"
    assert len(_PLACES) == 19, f"{len(_PLACES)} places, not the 19 stated"
    assert {p.path for p in _PLACES} == set(_FILES), (
        "a file has no place, or a place is outside"
    )
    names = [p.name for p in _EVERY_PLACE]
    assert len(set(names)) == len(names), "two places share a name"
    checks = [c for p in _PLACES for c in p.checks]
    assert len(checks) == 34, f"{len(checks)} checks, not the 34 stated"
    assert len(_RETIRED) == 9, f"{len(_RETIRED)} retired phrases, not the 9 stated"
    assert set(_OLD_BY_FILE) <= set(_FILES), (
        "an old excerpt belongs to a file outside the scan"
    )
    assert len(_WRAPPED_PLACES) == 15, (
        f"{len(_WRAPPED_PLACES)} re-wrapped places, not the 15 stated"
    )
    assert set(_WRAPPED_PLACES) <= set(names), "a re-wrapped place is not a place"
    # The second surface: two design templates, outside the first, one place each, two checks each.
    templates = list(_TEMPLATES.values())
    assert len(templates) == 2, f"{len(templates)} templates, not the 2 stated"
    assert set(templates).isdisjoint(_FILES), "a template is also in the skill's scan"
    empty = [name for name, path in _TEMPLATES.items() if not _read(path).strip()]
    assert not empty, f"empty templates: {empty}"
    assert len(_TEMPLATE_PLACES) == 2, f"{len(_TEMPLATE_PLACES)} template places, not 2"
    assert {p.path for p in _TEMPLATE_PLACES} == set(templates), (
        "a template has no place, or a place is outside"
    )
    template_checks = [c for p in _TEMPLATE_PLACES for c in p.checks]
    assert len(template_checks) == 4, f"{len(template_checks)} template checks, not 4"


@pytest.mark.parametrize("place", _EVERY_PLACE, ids=[p.name for p in _EVERY_PLACE])
def test_each_place_names_the_same_documents_and_the_projects_own_conventions(
    place: _Place,
) -> None:
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path.name} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _EVERY_PLACE, ids=[p.name for p in _EVERY_PLACE])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The old text said two documents, a single document, one stack's names and none of the new
    wording, so each check of the place must say so, or it tests nothing."""
    reported = _gaps(place, place.old)
    assert len(reported) == len(place.checks), (
        f"{place.name}: {len(reported)} of {len(place.checks)} checks saw the old text; "
        f"blind: {[c.label for c in place.checks if c.label not in reported]}"
    )


_LAYOUT = (
    "Feature code lives in backend/app/features/{feature_name}/",
    f"Layer flow: API {_ARROW} Service {_ARROW} Storage (never reverse)",
    f"No cross-feature imports {_EM} use internal APIs or shared core modules",
    "One class per file, file name matches class name in snake_case",
)
_LAYOUT_LABEL = "Example, for a Python backend laid out as vertical slices"


def _labelled_layout_gaps(region: str) -> list[str]:
    """What the design guide's layout block lacks: each bullet of the Python layout, and the label
    that says it is an example, which must come before the first bullet."""
    flat = _plain(region)
    gaps = [
        f"the layout lost: {bullet}" for bullet in _LAYOUT if _plain(bullet) not in flat
    ]
    label_at = flat.find(_plain(_LAYOUT_LABEL))
    first_at = flat.find(_plain(_LAYOUT[0]))
    if label_at < 0 or not 0 <= label_at < first_at:
        gaps.append("the layout is not introduced by its example label")
    return gaps


def _assert_layout_kept_and_labelled(guide: str) -> None:
    """The design guide's layout block is intact and labelled, and a copy of it with a bullet cut
    or the label moved below the bullets is reported. The copies are cut from the folded text, so a
    line end inside the label or a bullet of the real file cannot stop them from being built."""
    region = _section(guide, "## Designing Within", _DESIGN.name)
    assert _labelled_layout_gaps(region) == []
    flat = _plain(region)
    cut = flat.replace("One class per file", "Classes")
    assert cut != flat, "the planted cut found nothing to cut"
    assert _labelled_layout_gaps(cut) == [f"the layout lost: {_LAYOUT[3]}"]
    below = f"{flat.replace(_plain(_LAYOUT_LABEL), '')} {_LAYOUT_LABEL}"
    assert below != flat, "the planted move found no label to move"
    assert _labelled_layout_gaps(below) == [
        "the layout is not introduced by its example label"
    ]


def test_the_python_layout_is_kept_as_a_labelled_example() -> None:
    """Kept, not removed: the four rules of the layout stay, under the label that says they are
    one project's example. Fired at the old text, the label is missing; fired at a copy of the
    new text with a bullet cut or the label moved below the bullets, each is reported."""
    _assert_layout_kept_and_labelled(_read(_DESIGN))
    assert _labelled_layout_gaps(_OLD_DESIGN_HEAD) == [
        "the layout is not introduced by its example label"
    ]


@pytest.mark.parametrize("path", _FILES, ids=[p.name for p in _FILES])
def test_no_file_of_the_skill_still_says_what_was_retired(path: Path) -> None:
    found = _swept(_read(path))
    assert not found, f"{path.name} still carries: {sorted(found)}"


def test_the_sweep_sees_the_old_text_of_every_file_it_covers() -> None:
    """Fired at the excerpts the files carried: every phrase the file carried is reported."""
    for path, (old, expected) in _OLD_BY_FILE.items():
        assert _swept(old) == expected, (
            f"{path.name}: the sweep reported {sorted(_swept(old))}, expected {sorted(expected)}"
        )


@pytest.mark.parametrize("name", list(_TEMPLATES))
def test_no_design_template_still_says_what_was_retired(name: str) -> None:
    found = _swept(_read(_TEMPLATES[name]))
    assert not found, f"{name} still carries: {sorted(found)}"


def test_the_sweep_sees_the_old_text_of_the_design_templates() -> None:
    """Fired at the placeholder the templates carried: the retired phrase it held is reported, and
    only that one, so the sweep over the second surface is shown able to see before it is trusted."""
    old, expected = _OLD_IN_TEMPLATE
    assert _swept(old) == expected, f"the sweep reported {sorted(_swept(old))}"


def test_the_two_design_templates_say_the_same_on_the_line_that_names_the_conventions() -> (
    None
):
    """The seeded copy and the kit's own are two files that must not drift on the one line the
    skill points a Technical Approach at. Compared as the placeholder item, whitespace folded; a
    pair that differs is shown to be told apart, with the old placeholder against a changed one,
    so an agreement of the two real copies is not an agreement of two things the check cannot
    tell apart."""

    def line_of(text: str, where: str) -> str:
        return _squeeze(_item_with(text, _TEMPLATE_ANCHOR, where))

    lines = {name: line_of(_read(path), name) for name, path in _TEMPLATES.items()}
    assert len(set(lines.values())) == 1, f"the copies disagree: {lines}"
    changed = _OLD_TEMPLATE_APPROACH.replace("vertical slice architecture", "layout")
    assert changed != _OLD_TEMPLATE_APPROACH, (
        "the planted change found nothing to change"
    )
    assert line_of(changed, "planted") != line_of(_OLD_TEMPLATE_APPROACH, "planted"), (
        "two different placeholders read as the same line"
    )


def test_the_sweep_sees_each_retired_phrase_planted_and_a_wrapped_one() -> None:
    planted = {
        "two documents for a Medium task": "Create two\ndocuments:",
        "a Medium spec as one doc": "| Medium | Lightweight spec (single doc) |",
        "a Medium spec as one combined document": "create single\ncombined document",
        "a full spec as three documents": '"Make this a full spec" create all three\ndocuments',
        "one stack's linter in a gate": "1. Run `uv run ruff check` on all files",
        "the skill that serves one layout": "Reference the `vertical-slice` skill",
        "one layout as the project's architecture": (
            "- [ ] Design follows existing vertical slice\n  architecture"
        ),
        "a slice rule as the project's rule": "(e.g., the vertical slice rule, the earlier one)",
        "the risk list as the project's own": "### Common Risks in This Project",
    }
    missing = {label for label, _ in _RETIRED} - set(planted)
    assert not missing, f"no planted positive for {sorted(missing)}"
    for label, text in planted.items():
        assert label in _swept(text), f"the sweep missed {label!r} in {text!r}"
    for clean in (
        "Create three documents (spec, tasks, test plan)",
        "produces a single document carrying the case table inline",
        "create the four Large documents (requirements, design, tasks, verification plan)",
        "- **Feature slices**: feature A vertical slice -> feature B vertical slice",
        "Example, for a Python backend laid out as vertical slices (the project's own",
        "Run the project's lint command on all modified files",
    ):
        assert _swept(clean) == set(), f"the sweep flagged clean text: {clean!r}"


def test_the_locators_see_planted_text_and_a_missing_one_fails_loudly() -> None:
    text = "# T\n\n## A\none line\n\n```\n# not a heading\n```\n\n## B\nother\n"
    section = _section(text, "## A", "planted")
    assert (
        "one line" in section and "other" not in section and "not a heading" in section
    )
    with pytest.raises(AssertionError, match="no heading"):
        _section(text, "## C", "planted")
    assert (
        _item_with("a\n\n| Medium | x |\nb\n", "| Medium |", "planted")
        == "| Medium | x |"
    )
    with pytest.raises(AssertionError, match="found 0"):
        _item_with("a\nb\n", "| Medium |", "planted")
    with pytest.raises(AssertionError, match="found 2"):
        _item_with("| Medium | 1\n| Medium | 2\n", "| Medium |", "planted")
    wrapped = "- Total **Medium** is\n  a list item that\nwraps twice.\n- Next item.\n"
    assert _squeeze(_item_with(wrapped, "**Medium** is a", "planted")) == (
        "- Total **Medium** is a list item that wraps twice."
    )
    split_needle = (
        "A paragraph that says Proceeding\nwith: the plan,\nover two lines.\n"
    )
    assert "over two lines" in _item_with(split_needle, "Proceeding with:", "planted")
    fenced = "```\nTask size: x\nProceeding with: {a |\nb}\n```\n\nAfter the fence.\n"
    block = _item_with(fenced, "Proceeding with:", "planted")
    assert "b}" in block and "After the fence" not in block
    assert _items("# H\nnext line\n- a\n  b\n| r |\ntext\n") == [
        "# H",
        "next line",
        "- a\n  b",
        "| r |",
        "text",
    ]
    assert _says("alpha `beta`")("An Alpha **Beta** here")
    assert not _says("alpha beta")("alpha gamma")
    assert _lacks("uv run ruff")("run the project's lint command")
    assert not _lacks("uv run ruff")("1. Run `uv run\nruff` check")


# The places that are one list item, one paragraph or one fenced block: a line of them can be
# re-wrapped. The other places are a heading's section (folded whole) or a table row (one line).
_WRAPPED_PLACES = (
    "skill-classification",
    "skill-announcement",
    "size-override",
    "design-guide-enums-line",
    "design-guide-schemas-line",
    "design-guide-route-line",
    "design-guide-migration-risk",
    "actors-label",
    "skill-large-class",
    "size-full-spec-override",
    "skill-conflict-example",
    "skill-challenge-list",
    "skill-checklist-line",
    "design-template-seeded",
    "design-template-kit",
)


def _rewrapped(text: str, line: str) -> list[str]:
    """`text` once per space of `line`, that space turned into a line end, the rest of the line
    carried on as a continuation in column 0 and again indented. Two kinds of break are left out
    because they are not a re-wrap: one inside the list marker or the checkbox in front of the
    words (no letter before it), and one that would put a list marker, a heading mark or a table
    bar first on the continuation, which makes another block."""
    variants: list[str] = []
    for at, char in enumerate(line):
        head, tail = line[:at], line[at + 1 :]
        if char != " " or not re.search(r"[A-Za-z]", head) or not tail.strip():
            continue
        if _opens_item(tail):
            continue
        for pad in ("", "  "):
            variants.append(text.replace(line, f"{head}\n{pad}{tail}", 1))
    return variants


@pytest.mark.parametrize("name", _WRAPPED_PLACES)
def test_an_item_place_holds_however_its_line_is_re_wrapped(name: str) -> None:
    place = next(p for p in _EVERY_PLACE if p.name == name)
    text = _read(place.path)
    line = max(place.locate(text, place.path.name).split("\n"), key=len)
    variants = _rewrapped(text, line)
    assert len(variants) >= 2, (
        f"{name}: the line {line!r} gave {len(variants)} re-wraps"
    )
    broken = sum(1 for variant in variants if _gaps(place, variant))
    assert broken == 0, (
        f"{name}: {broken} of {len(variants)} re-wraps of {line!r} break the place"
    )


def test_the_python_layout_check_holds_however_its_label_is_re_wrapped() -> None:
    """The layout check reads a section, not an item, so it is not one of the item places above.
    It once cut its planted copies from the raw lines and lost the label's line when a re-wrap
    split it. Fired at the label broken at every space, the whole check still holds. The label is
    first put on one line, wherever the file wraps it, so the guard holds either way."""
    text = _read(_DESIGN)
    item = _item_with(text, _LAYOUT_LABEL, _DESIGN.name)
    line = _squeeze(item)
    text = text.replace(item, line, 1)
    variants = _rewrapped(text, line)
    assert len(variants) >= 4, f"the label gave {len(variants)} re-wraps"
    for variant in variants:
        _assert_layout_kept_and_labelled(variant)
