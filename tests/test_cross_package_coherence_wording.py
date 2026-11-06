"""The checks of the cross package coherence wording tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_route_list_and_the_denial_name_the_same_way_to_add_an_entry`: the route list and the denial name the same way to add an entry
* `test_a_route_that_differs_or_is_the_file_end_is_reported_on_either_side`: Known positives: the denial's old bullet against the real route list, and the old route list against the real denial.
"""

import importlib.util
import re
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple, cast

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_QUOTE_MARK = re.compile(r"^\s*>\s?")
_DASH = chr(0x2014)
_SECT = chr(0xA7)

_SKILLS = "plugins/orchestration/skills"
_PLANNER = f"{_SKILLS}/stacked-pr-planner/SKILL.md"
_INITIATIVE = f"{_SKILLS}/initiative-planner/SKILL.md"
_TEMPLATE = f"{_SKILLS}/orchestrate/references/brief-template.md"
_ACTIONS = (
    "plugins/core/skills/learning-consolidator/references/consolidation-actions.md"
)
_GUARD_PATH = "plugins/core/hooks/gate_learnings_drain.py"

_EFFORT_LEAD = "> **Set effort with the `--effort` flag.**"
_PASTE_LINE = "## Paste line"
_RULES = "## Rules a dispatch brief carries"
_OPERATOR_STEPS = "## Operator Steps"


class _Clause(NamedTuple):
    slug: str
    path: str
    # The heading whose section holds the clause, or "" for the whole file.
    section: str
    # What the first line of the paragraph or list item starts with.
    lead: str
    # Phrases that must all be in the clause, wording that had to stay (it is on the old text
    # too) and wording it retired; lower-cased, folded.
    required: tuple[str, ...]
    # Phrases that must be in the clause with their capitals as written, because the capital is
    # the meaning (`-E` is not `-e`); folded, and each carries a capital.
    exact: tuple[str, ...]
    kept: tuple[str, ...]
    retired: tuple[str, ...]
    # The clause as it stood before, with its heading when it has a section: planted.
    old: str


_OLD_GREP = (
    "> **Use `grep -E` with a real pipe, not `grep -i a\\|b`.** Under basic regex `\\|` is a literal, so the\n"
    '> naive form silently matches nothing and reports "no migration here" on a layer that has one. That\n'
    "> failure was reproduced against the very migration this skill was written about.\n"
)


_OLD_EFFORT = (
    "> **Set effort with the `--effort` flag.** It is a first-class CLI flag with a validated enum. A\n"
    "> plan that routes effort through a `/effort` slash command inside the prompt string is working\n"
    f"> around a limitation that does not exist on this version {_DASH} the slash-command route survives only\n"
    "> because the **`Agent` tool** has no effort parameter, so it remains the fallback for *native\n"
    "> subagents*, not for spawned CLI sessions.\n"
)

_OLD_ROUTES = (
    f"{_OPERATOR_STEPS}\n\n"
    "The routes a session may use on the buffer are the three the guard names when it denies a line:\n"
    "**Grep in count mode** (pattern `^### \\[`) to count entries, **Read with offset and limit** to read\n"
    "them, and **Edit appending after the last entry** to add one.\n"
)

_OLD_PASTE_LINE = (
    f"{_PASTE_LINE}\n\n"
    "A line that disagrees with what the delegate finds, or that holds a placeholder, is a stop: the\n"
    "delegate writes nothing more and says so in one sentence. The delegate's first write is the hand-off\n"
    "stub, made only if the return note at the named return path does not exist: that write is the done\n"
    f"check. The live-peer check follows it, as `SKILL.md` {_SECT} 2b says: copy that check into the brief's\n"
    "preconditions, and a live peer sets the stub `blocked`.\n"
)

_OLD_PLACEHOLDER = (
    f"{_RULES}\n\n"
    "- **Stop on ANY `<...>` placeholder.** A delegate told to stop on two named spellings walks past the\n"
    '  third. A `<...>` in a command template means "fill it from the command that names it", and one the\n'
    "  delegate cannot fill is a stop: nothing is written, and its one-sentence report names the\n"
    "  placeholder.\n"
    "- **The return note is the first write.** The note and the session's scratch folder come before any\n"
)

_CLAUSES: tuple[_Clause, ...] = (
    _Clause(
        slug="grep-escaped-pipe",
        path=_PLANNER,
        section="",
        lead="> **Use `grep -E` with a real pipe",
        required=(
            "unquoted, a posix shell drops the backslash",
            "plain gnu grep is handed `a|b` and takes the pipe as a literal",
            "(plain gnu grep reads it as alternation)",
        ),
        exact=("Under `-E` an escaped pipe is a literal",),
        kept=("use `grep -e` with a real pipe, not `grep -i a\\|b`",),
        retired=("under basic regex",),
        old=_OLD_GREP,
    ),
    _Clause(
        slug="effort-flag",
        path=_INITIATIVE,
        section="",
        lead=_EFFORT_LEAD,
        required=("a first-class cli flag; an unknown value only warns (cli 2.1.316)",),
        exact=(),
        kept=(),
        retired=("validated enum",),
        old=_OLD_EFFORT,
    ),
    _Clause(
        slug="route-list",
        path=_ACTIONS,
        section=_OPERATOR_STEPS,
        lead="The routes a session may use on the buffer",
        required=(
            "and edit appending under the entry's own category header to add one",
        ),
        exact=(),
        kept=(),
        retired=("after the last entry",),
        old=_OLD_ROUTES,
    ),
    _Clause(
        slug="paste-line-stop",
        path=_TEMPLATE,
        section=_PASTE_LINE,
        lead="A line that disagrees with what the delegate finds",
        required=(
            "is a stop: the delegate sets the hand-off stub's status to `blocked` and "
            "writes nothing more, and says so in one sentence.",
        ),
        exact=(),
        kept=(),
        retired=("the delegate writes nothing more and says so",),
        old=_OLD_PASTE_LINE,
    ),
    _Clause(
        slug="placeholder-stop",
        path=_TEMPLATE,
        section=_RULES,
        lead="- **Stop on ANY `<...>` placeholder.**",
        required=(
            "is a stop: nothing more is written, and its one-sentence report names "
            "the placeholder.",
        ),
        exact=(),
        kept=(),
        retired=("nothing is written",),
        old=_OLD_PLACEHOLDER,
    ),
)


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str, *, keep_case: bool = False) -> str:
    """Quote marks and bold marks dropped, whitespace folded, capitals ignored unless `keep_case`:
    a re-wrapped, re-quoted or re-emphasised sentence is the same sentence."""
    lines = [_QUOTE_MARK.sub("", line) for line in text.split("\n")]
    flat = " ".join(" ".join(lines).replace("**", "").split())
    return flat if keep_case else flat.lower()


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _unit(text: str, lead: str) -> str:
    """The paragraph or list item that opens with `lead`: its first line and the lines that run
    on under it, up to a blank line, a heading, the next list item or the end of a quote. Empty
    when no line opens with `lead`; a lead that opens two lines is a failure, not a guess."""
    lines = text.split("\n")
    starts = [n for n, line in enumerate(lines) if line.startswith(lead)]
    if not starts:
        return ""
    assert len(starts) == 1, f"{len(starts)} lines open with {lead!r}, not one"
    start = starts[0]
    quoted = lines[start].startswith(">")
    unit = [lines[start]]
    for follow in lines[start + 1 :]:
        if (
            not follow.strip()
            or follow.strip() == ">"
            or _HEADING.match(follow)
            or _ITEM.match(follow)
            or (quoted and not follow.startswith(">"))
        ):
            break
        unit.append(follow)
    return "\n".join(unit)


def _region(clause: _Clause, text: str) -> str:
    scope = _section(text, clause.section) if clause.section else text
    return _unit(scope, clause.lead)


# --- the clauses ----------------------------------------------------------------------------------


# --- the agreements -------------------------------------------------------------------------------

_AGREEMENT_TESTS: list[Callable[[], None]] = []


def _agreement(test: Callable[[], None]) -> Callable[[], None]:
    """Marks a test as one of this file's agreements, so the surface test can count them."""
    _AGREEMENT_TESTS.append(test)
    return test


_ADD_ENTRY = "- add an entry: "


@cache
def _guard() -> dict[str, Any]:
    """The guard, loaded from its file (the hook is a script, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "gate_learnings_drain_wording", _REPO_ROOT / _GUARD_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(vars(module))


def _denial_routes() -> list[str]:
    """The routes the guard's shell denial lists, as the session that is denied reads them."""
    shell_reason = cast(Callable[[str, str], str], _guard()["_shell_reason"])
    reason = shell_reason("plan-approved.md", "a rewrite")
    return [line.strip() for line in reason.splitlines() if line.startswith("  - ")]


def _route_disagreements(route_list: str, routes: list[str]) -> list[str]:
    """What the reference's route list and the guard's denial do not share about adding an
    entry: the same words, and neither of them the file end."""
    added = [route for route in routes if route.startswith(_ADD_ENTRY)]
    if len(added) != 1:
        return [f"the denial lists {len(added)} routes that add an entry, not one"]
    words = added[0].removeprefix(_ADD_ENTRY).lower()
    flat = _folded(route_list)
    problems: list[str] = []
    if words not in flat:
        problems.append(f"the route list does not say {words!r}")
    for name, text in (("the route list", flat), ("the denial", words)):
        if "after the last entry" in text:
            problems.append(f"{name} says after the last entry")
    return problems


def _route_list() -> str:
    clause = next(c for c in _CLAUSES if c.slug == "route-list")
    return _region(clause, _read(clause.path))


@_agreement
def test_the_route_list_and_the_denial_name_the_same_way_to_add_an_entry() -> None:
    routes = _denial_routes()
    assert len(routes) == 3, routes
    assert _route_disagreements(_route_list(), routes) == []


def test_a_route_that_differs_or_is_the_file_end_is_reported_on_either_side() -> None:
    """Known positives: the denial's old bullet against the real route list, and the old route
    list against the real denial."""
    routes = _denial_routes()
    old_bullet = _ADD_ENTRY + "Edit, appending after the last entry"
    old_routes = [*routes[:2], old_bullet]
    assert _route_disagreements(_route_list(), old_routes) == [
        "the route list does not say 'edit, appending after the last entry'",
        "the denial says after the last entry",
    ]
    old_list = _section(_OLD_ROUTES, _OPERATOR_STEPS)
    assert _route_disagreements(old_list, routes) == [
        'the route list does not say "edit appending under the entry\'s own category header"',
        "the route list says after the last entry",
    ]
    assert _route_disagreements(_route_list(), routes[:2]) == [
        "the denial lists 0 routes that add an entry, not one"
    ]
