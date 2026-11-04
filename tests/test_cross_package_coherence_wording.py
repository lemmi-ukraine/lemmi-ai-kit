"""Pages of three packs said what another page of the kit contradicted; each pair now agrees.

Each of the five clauses below was a sentence that a neighbouring page of the kit contradicted,
both sides shipped, each side passing its own tests:

* the stacked-PR planner gave a reason for a silent grep miss that is false on GNU grep. An
  escaped pipe is an alternation in plain GNU grep and a literal only under `-E`, which the
  design guide of the spec-driven pipeline already says. What makes the unquoted naive form
  silent is the shell: it drops the backslash, and plain grep takes the bare pipe it is handed
  as a literal. The planner now says those three things, and still prescribes `grep -E` with a
  real pipe;
* the initiative planner called `--effort` a flag with a validated enum, while `orchestrate` says
  an unknown value only warns and the default effort runs. Both now say the second;
* the route list of the consolidator's operator steps, and the denial text of the learnings guard
  (a message an adopter's session reads), told the session to add an entry by "appending after
  the last entry", which is the file end, while the same reference and the intake skill say an
  entry goes under its own category header and never at the file end. Both now say that;
* the brief template said a paste-line mismatch writes nothing more and a placeholder stop writes
  nothing, while the stub a delegate writes first says a failed precondition sets its Status to
  `blocked`. The stop now sets the hand-off stub's Status and writes nothing more.

Three groups of pages are also held to agree with each other, because a clause read alone can be
right and still contradict its neighbour: the two effort statements, the route list and the
guard's denial, and the three pages that say what a stop leaves behind.

THE SURFACE, in numbers the tests assert: 5 clauses in 4 files, judged by 7 required phrases, 1
phrase compared with its capitals as written (`-E` is not `-e`), 1 kept phrase (the prescribed
command, which has to stay) and 5 retired ones, and 3 agreements (the effort statements of 2
skill pages; the route list of 1 reference page against the 3 routes that the shell denial of 1
hook script lists; the 3 pages that name the stub's Status after a stop). A check holds when its
words are in the place (lower-cased, quote marks and bold marks dropped, whitespace collapsed; the
one phrase whose capital is its meaning is compared as written). Each clause is fired at the
sentence it held before; the grep note and the stop clause of the paste line were reworded twice,
so each is also fired at the wording between the two. Each requirement is removed from the real
text in turn and must be the only thing reported, each retired wording is put back and must be the
only thing reported, and a copy re-wrapped at 60 columns must still pass. A clause or a heading
that goes missing fails with the clause's name, not with an empty pass, and so does a page that
cannot be found; a lead that opens two lines is a failure, not a guess. A paragraph is found by
the words that open it, so a wrap narrower than those words hides the paragraph and fails with
its name.

The classes of shape covered: the old sentence as it stood, the old sentence in other words that
keep the key words (the retired phrases are the short shapes `under basic regex`, `validated enum`,
`after the last entry`), a requirement removed, a retired wording returned, a re-wrapped copy, a
missing heading or paragraph, a flag letter in the wrong case, a lead that opens two lines, and an
agreement that breaks on either side.
"""

import importlib.util
import re
import textwrap
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple, cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_QUOTE_MARK = re.compile(r"^\s*>\s?")
_DASH = chr(0x2014)
_SECT = chr(0xA7)

_SKILLS = "plugins/orchestration/skills"
_PLANNER = f"{_SKILLS}/stacked-pr-planner/SKILL.md"
_INITIATIVE = f"{_SKILLS}/initiative-planner/SKILL.md"
_ORCHESTRATE = f"{_SKILLS}/orchestrate/SKILL.md"
_TEMPLATE = f"{_SKILLS}/orchestrate/references/brief-template.md"
_DELEGATE = f"{_SKILLS}/agent-delegate/SKILL.md"
_STUB = f"{_SKILLS}/agent-delegate/assets/handoff-stub.md"
_ACTIONS = (
    "plugins/core/skills/learning-consolidator/references/consolidation-actions.md"
)
_GUARD_PATH = "plugins/core/hooks/gate_learnings_drain.py"

_EFFORT_LEAD = "> **Set effort with the `--effort` flag.**"
_ORCHESTRATE_EFFORT_LEAD = "- **`--effort` is a real flag**"
_STUB_ITEM_LEAD = "   - **The hand-off stub, before any precondition**"
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

# Two sentences as they read between the old wording and the current one: the grep note gave the
# reading of an escaped pipe as the reason for the silent miss and did not name the shell, and the
# paste line named the stub's Status before it said which stub. Planted, so that the checks for
# the words that came after are fired at text that lacks them.
_INTERIM_GREP = (
    "> **Use `grep -E` with a real pipe, not `grep -i a\\|b`.** Under `-E` an escaped pipe is a literal\n"
    "> (plain GNU grep reads it as alternation), so the naive form silently matches nothing and reports\n"
    '> "no migration here" on a layer that has one. Reproduced on the very migration behind this skill.\n'
)

_INTERIM_PASTE_LINE = (
    f"{_PASTE_LINE}\n\n"
    "A line that disagrees with what the delegate finds, or that holds a placeholder, is a stop: the\n"
    "delegate sets the stub's Status to `blocked` and writes nothing more, and says so in one sentence.\n"
    "The delegate's first write is the hand-off stub, made only if the return note at the named return\n"
    "path does not exist: that write is the done check. The live-peer check follows it, as `SKILL.md`\n"
    f"{_SECT} 2b says: copy that check into the brief's preconditions, and a live peer sets the stub `blocked`.\n"
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
_IDS = [clause.slug for clause in _CLAUSES]


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


def _gaps(clause: _Clause, flat: str) -> list[str]:
    """What a clause lacks, given its folded text: one entry per gap."""
    gaps = [f"missing: {phrase}" for phrase in clause.required if phrase not in flat]
    gaps += [
        f"kept wording gone: {phrase}" for phrase in clause.kept if phrase not in flat
    ]
    gaps += [
        f"retired wording still there: {phrase}"
        for phrase in clause.retired
        if phrase in flat
    ]
    return gaps


def _exact_gaps(clause: _Clause, exact: str) -> list[str]:
    """What a clause lacks among the phrases whose capitals are the meaning, given its text
    folded with the capitals kept."""
    return [
        f"missing, capitals as written: {phrase}"
        for phrase in clause.exact
        if phrase not in exact
    ]


def _absent(clause: _Clause) -> str:
    where = clause.section or "any heading"
    return f"{clause.slug}: no paragraph opens with {clause.lead!r} under {where}"


def _problems(clause: _Clause, text: str) -> list[str]:
    region = _region(clause, text)
    if not region.strip():
        return [_absent(clause)]
    return _gaps(clause, _folded(region)) + _exact_gaps(
        clause, _folded(region, keep_case=True)
    )


def _rewrapped(clause: _Clause, text: str, columns: int) -> str:
    """`text` with the clause broken into rows of at most `columns` characters, so that its
    phrases run over several rows; the markers of a quote or a list item are kept."""
    region = _region(clause, text)
    first = region.split("\n", 1)[0]
    quoted = first.startswith(">")
    item = _ITEM.match(first) is not None
    opening = "> " if quoted else "- " if item else ""
    running = "> " if quoted else "  " if item else ""
    body = " ".join(_QUOTE_MARK.sub("", line) for line in region.split("\n"))
    body = re.sub(r"^\s*[-*+]\s", "", body) if item else body
    rows = textwrap.wrap(
        body,
        width=columns,
        initial_indent=opening,
        subsequent_indent=running,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return text.replace(region, "\n".join(rows), 1)


# --- the clauses ----------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_CLAUSES) == 5
    assert sum(len(clause.required) for clause in _CLAUSES) == 7
    assert sum(len(clause.exact) for clause in _CLAUSES) == 1
    assert sum(len(clause.kept) for clause in _CLAUSES) == 1
    assert sum(len(clause.retired) for clause in _CLAUSES) == 5
    paths = {clause.path for clause in _CLAUSES}
    assert len(paths) == 4, sorted(paths)
    assert len(set(_IDS)) == len(_IDS), "two clauses share a slug"
    for path in (*paths, _ORCHESTRATE, _DELEGATE, _STUB, _GUARD_PATH):
        assert _read(path).strip(), f"{path} is empty"
    for clause in _CLAUSES:
        judged = (*clause.required, *clause.kept)
        for phrase in (*judged, *clause.retired):
            assert phrase == " ".join(phrase.lower().split()), (
                f"{clause.slug}: {phrase!r} is not lower-cased and folded, so it can never match"
            )
        for phrase in clause.exact:
            assert phrase == " ".join(phrase.split()), (
                f"{clause.slug}: {phrase!r} is not folded, so it can never match"
            )
            assert phrase != phrase.lower(), (
                f"{clause.slug}: {phrase!r} carries no capital, so it belongs in required"
            )
        for phrase in judged:
            others = [p for p in judged if p != phrase and (p in phrase or phrase in p)]
            assert not others, f"{clause.slug}: {phrase!r} overlaps {others}"
    # The three agreements, by what each compares.
    assert len(_AGREEMENT_TESTS) == 3, [test.__name__ for test in _AGREEMENT_TESTS]
    assert len(_EFFORT_PAGES) == 2
    routes = _denial_routes()
    assert len(routes) == 3, routes
    assert sum(route.startswith(_ADD_ENTRY) for route in routes) == 1, routes
    pages = _stop_pages(_read(_TEMPLATE), _read(_DELEGATE), _read(_STUB))
    assert list(pages) == [
        "the Paste line section of the brief template",
        "the stub item of agent-delegate",
        "the stub file",
    ]


@pytest.mark.parametrize("clause", _CLAUSES, ids=_IDS)
def test_the_clause_says_what_it_must(clause: _Clause) -> None:
    """Red before the change: each clause held its old sentence and not the new one."""
    problems = _problems(clause, _read(clause.path))
    assert not problems, f"{clause.path}: {problems}"


@pytest.mark.parametrize("clause", _CLAUSES, ids=_IDS)
def test_the_old_sentence_is_reported(clause: _Clause) -> None:
    """Known positive: the clause as it stood. Every requirement is missing from it, every
    retired wording is in it, and the wording that had to stay is on it too, so the checks above
    can see the old text."""
    old = _folded(_region(clause, clause.old))
    assert old, _absent(clause)
    assert all(phrase in old for phrase in clause.kept), (
        "kept wording is not on the old text"
    )
    expected = [f"missing: {phrase}" for phrase in clause.required]
    expected += [f"retired wording still there: {phrase}" for phrase in clause.retired]
    expected += [f"missing, capitals as written: {phrase}" for phrase in clause.exact]
    assert _problems(clause, clause.old) == expected


@pytest.mark.parametrize("clause", _CLAUSES, ids=_IDS)
def test_every_requirement_is_load_bearing(clause: _Clause) -> None:
    """Removing one requirement, or one kept phrase, from the real clause reports that one and
    no other; so does removing the phrase that is compared with its capitals."""
    region = _region(clause, _read(clause.path))
    flat = _folded(region)
    assert flat, _absent(clause)
    for label, phrases in (
        ("missing", clause.required),
        ("kept wording gone", clause.kept),
    ):
        for phrase in phrases:
            assert phrase in flat, (
                f"{clause.slug}: {phrase!r} is not in the real clause"
            )
            assert _gaps(clause, flat.replace(phrase, "")) == [f"{label}: {phrase}"]
    exact = _folded(region, keep_case=True)
    for phrase in clause.exact:
        assert phrase in exact, f"{clause.slug}: {phrase!r} is not in the real clause"
        assert _exact_gaps(clause, exact.replace(phrase, "")) == [
            f"missing, capitals as written: {phrase}"
        ]


@pytest.mark.parametrize("clause", _CLAUSES, ids=_IDS)
def test_every_retired_wording_is_reported_when_it_returns(clause: _Clause) -> None:
    """Planted return: the real clause with one retired wording appended reports that wording
    and nothing else, so a check that stopped at the requirements would not see it come back."""
    flat = _folded(_region(clause, _read(clause.path)))
    assert flat, _absent(clause)
    for phrase in clause.retired:
        assert _gaps(clause, f"{flat} {phrase}") == [
            f"retired wording still there: {phrase}"
        ]


@pytest.mark.parametrize("clause", _CLAUSES, ids=_IDS)
def test_a_rewrapped_clause_still_passes(clause: _Clause) -> None:
    """Near miss: the clause re-wrapped at 60 columns, so that a phrase runs over several rows,
    is the same clause. The wrap changes the text and hides a phrase from a raw read, and the
    checks read it whole."""
    text = _read(clause.path)
    assert _problems(clause, text) == [], (
        "the real clause must pass before it is re-wrapped"
    )
    wrapped = _rewrapped(clause, text, 60)
    assert wrapped != text, "the planted wrap changed nothing"
    raw = _region(clause, wrapped).lower()
    assert any(phrase not in raw for phrase in clause.required), (
        "the planted wrap hides no phrase from a raw read"
    )
    assert _problems(clause, wrapped) == []


@pytest.mark.parametrize("clause", _CLAUSES, ids=_IDS)
def test_a_clause_that_goes_missing_fails_with_its_name(clause: _Clause) -> None:
    assert _problems(clause, "") == [_absent(clause)]
    if clause.section:
        text = _read(clause.path)
        renamed = text.replace(clause.section, "## Renamed", 1)
        assert renamed != text, "the planted rename changed nothing"
        assert _problems(clause, renamed) == [_absent(clause)]


def test_a_near_miss_is_not_the_retired_route() -> None:
    """`after the entry's own category header` is not `after the last entry`: the retired
    wording is a shape of its own, so a near miss reports only the requirement it lacks."""
    clause = next(c for c in _CLAUSES if c.slug == "route-list")
    near = clause.required[0].replace("under the entry's", "after the entry's")
    assert near != clause.required[0], "the planted near miss changed nothing"
    assert _gaps(clause, near) == [f"missing: {clause.required[0]}"]
    assert _gaps(clause, clause.required[0]) == []


_INTERIM: dict[str, tuple[str, list[str]]] = {
    "grep-escaped-pipe": (
        _INTERIM_GREP,
        [
            "missing: unquoted, a posix shell drops the backslash",
            "missing: plain gnu grep is handed `a|b` and takes the pipe as a literal",
        ],
    ),
    "paste-line-stop": (
        _INTERIM_PASTE_LINE,
        [
            "missing: is a stop: the delegate sets the hand-off stub's status to "
            "`blocked` and writes nothing more, and says so in one sentence."
        ],
    ),
}


@pytest.mark.parametrize("slug", list(_INTERIM))
def test_an_interim_wording_is_reported(slug: str) -> None:
    """Known positive for the two clauses that were reworded twice: the wording between the old
    sentence and the current one passes every check that does not read the newest words (no
    retired wording, the kept command, the capitalised flag) and lacks exactly those words."""
    text, expected = _INTERIM[slug]
    clause = next(c for c in _CLAUSES if c.slug == slug)
    assert _problems(clause, text) == expected


def test_a_flag_letter_in_the_wrong_case_is_reported() -> None:
    """`-E` is not `-e`: under `-e` the pipe stays a literal and the prescribed command matches
    nothing. The folded match ignores capitals, so the phrase that names the flag is compared as
    written: the real clause with `-e` in its place reports that phrase and no other, a capital
    changed anywhere else is no difference, and the flag of the prescribed command is held by the
    lead that finds the paragraph, which is matched as written too."""
    clause = next(c for c in _CLAUSES if c.slug == "grep-escaped-pipe")
    text = _read(clause.path)
    assert _problems(clause, text) == [], (
        "the real clause must pass before it is planted on"
    )
    unwrapped = _rewrapped(clause, text, 10_000)
    assert unwrapped != text, "the planted unwrap changed nothing"
    sentence = unwrapped.replace(
        "Under `-E` an escaped pipe", "Under `-e` an escaped pipe", 1
    )
    assert sentence != unwrapped, "the planted flag letter changed nothing"
    assert _problems(clause, sentence) == [
        f"missing, capitals as written: {clause.exact[0]}"
    ]
    shouted = unwrapped.replace("Unquoted, a POSIX shell", "UNQUOTED, a POSIX SHELL", 1)
    assert shouted != unwrapped, "the planted capitals changed nothing"
    assert _problems(clause, shouted) == []
    heading = unwrapped.replace("**Use `grep -E` with", "**Use `grep -e` with", 1)
    assert heading != unwrapped, "the planted flag letter changed nothing"
    assert _problems(clause, heading) == [_absent(clause)]


def test_a_lead_that_opens_two_lines_is_a_failure_not_a_guess() -> None:
    """The unit finder refuses to choose between two paragraphs that open the same way. The
    failure is reached from the finder itself and from a clause whose lead is planted twice."""
    lead = "> **Lead.**"
    one = f"intro\n\n{lead} first\n> and on\n\n> **Another.** apart\n"
    assert _unit(one, lead) == f"{lead} first\n> and on", (
        "control: one line opens the unit"
    )
    with pytest.raises(AssertionError, match="2 lines open with"):
        _unit(f"{one}\n{lead} second\n", lead)
    clause = next(c for c in _CLAUSES if c.slug == "grep-escaped-pipe")
    doubled = f"{_read(clause.path)}\n{clause.lead} again\n"
    with pytest.raises(AssertionError, match="2 lines open with"):
        _problems(clause, doubled)


# --- the agreements -------------------------------------------------------------------------------

_AGREEMENT_TESTS: list[Callable[[], None]] = []


def _agreement(test: Callable[[], None]) -> Callable[[], None]:
    """Marks a test as one of this file's agreements, so the surface test can count them."""
    _AGREEMENT_TESTS.append(test)
    return test


_EFFORT_AGREED = ("an unknown value only warns", "2.1.316")
# The two pages that state it, each with the line that opens its paragraph.
_EFFORT_PAGES = (
    ("initiative-planner", _EFFORT_LEAD),
    ("orchestrate", _ORCHESTRATE_EFFORT_LEAD),
)


def _effort_disagreements(initiative: str, orchestrate: str) -> list[str]:
    """What the two skills do not agree on about an unknown `--effort` value."""
    problems: list[str] = []
    texts = (initiative, orchestrate)
    for (name, lead), text in zip(_EFFORT_PAGES, texts, strict=True):
        unit = _folded(_unit(text, lead))
        if not unit:
            problems.append(f"{name}: no paragraph opens with {lead!r}")
            continue
        problems += [f"{name}: lacks {p!r}" for p in _EFFORT_AGREED if p not in unit]
        if "validated enum" in unit:
            problems.append(f"{name}: says 'validated enum'")
    return problems


@_agreement
def test_the_two_effort_statements_agree() -> None:
    initiative = _read(_INITIATIVE)
    orchestrate = _read(_ORCHESTRATE)
    assert _effort_disagreements(initiative, orchestrate) == []


def test_an_effort_statement_that_disagrees_is_reported_on_either_side() -> None:
    """Known positives: the old paragraph of the initiative planner, and the older bullet of
    `orchestrate` that also said validated enum, each against the real other side."""
    initiative = _read(_INITIATIVE)
    orchestrate = _read(_ORCHESTRATE)
    assert _effort_disagreements(_OLD_EFFORT, orchestrate) == [
        "initiative-planner: lacks 'an unknown value only warns'",
        "initiative-planner: lacks '2.1.316'",
        "initiative-planner: says 'validated enum'",
    ]
    older = (
        "- **`--effort` is a real flag** with a validated enum "
        "(`low`, `medium`, `high`, `xhigh`, `max`). The `Agent`\n"
        "  tool has no effort parameter, so `/effort` inside a prompt string remains the "
        "fallback for native\n"
        "  subagents only.\n"
    )
    assert _effort_disagreements(initiative, older) == [
        "orchestrate: lacks 'an unknown value only warns'",
        "orchestrate: lacks '2.1.316'",
        "orchestrate: says 'validated enum'",
    ]
    assert _effort_disagreements(initiative, "") == [
        f"orchestrate: no paragraph opens with {_ORCHESTRATE_EFFORT_LEAD!r}"
    ]


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


_BLOCKED = "status to `blocked`"


def _stop_pages(template: str, delegate: str, stub: str) -> dict[str, str]:
    return {
        "the Paste line section of the brief template": _section(template, _PASTE_LINE),
        "the stub item of agent-delegate": _unit(delegate, _STUB_ITEM_LEAD),
        "the stub file": stub,
    }


def _stop_state_gaps(pages: dict[str, str]) -> list[str]:
    """The pages that do not say a stop sets the stub's Status to `blocked`."""
    return [
        f"{name}: does not say a stop sets Status to `blocked`"
        for name, text in pages.items()
        if _BLOCKED not in _folded(text)
    ]


def _missing_pages(pages: dict[str, str]) -> list[str]:
    """The pages that were not found: an empty page would make an agreement say nothing."""
    return [
        f"{name}: page not found" for name, text in pages.items() if not text.strip()
    ]


@_agreement
def test_every_page_that_says_what_a_stop_leaves_behind_agrees() -> None:
    pages = _stop_pages(_read(_TEMPLATE), _read(_DELEGATE), _read(_STUB))
    assert _missing_pages(pages) == []
    assert _stop_state_gaps(pages) == []


def test_a_page_that_says_a_stop_leaves_no_stub_is_reported() -> None:
    """Known positives: the Paste line section as it stood, and each page emptied in turn."""
    real = _stop_pages(_read(_TEMPLATE), _read(_DELEGATE), _read(_STUB))
    old = {**real, "the Paste line section of the brief template": _OLD_PASTE_LINE}
    assert _stop_state_gaps(old) == [
        "the Paste line section of the brief template: "
        "does not say a stop sets Status to `blocked`"
    ]
    for name in real:
        emptied = {**real, name: "nothing about a stop"}
        assert _stop_state_gaps(emptied) == [
            f"{name}: does not say a stop sets Status to `blocked`"
        ]


def test_a_stop_page_that_cannot_be_found_or_is_found_twice_is_reported() -> None:
    """Both guard paths of the stop pages are fired: a page whose lead or heading was renamed is
    reported by its name, and a lead planted on two lines fails instead of choosing one."""
    template, delegate, stub = _read(_TEMPLATE), _read(_DELEGATE), _read(_STUB)
    assert _missing_pages(_stop_pages(template, delegate, stub)) == [], (
        "the real pages must all be found before they are planted on"
    )
    renamed_item = delegate.replace(_STUB_ITEM_LEAD, "   - **Renamed**", 1)
    assert renamed_item != delegate, "the planted rename changed nothing"
    assert _missing_pages(_stop_pages(template, renamed_item, stub)) == [
        "the stub item of agent-delegate: page not found"
    ]
    renamed_section = template.replace(_PASTE_LINE, "## Renamed", 1)
    assert renamed_section != template, "the planted rename changed nothing"
    assert _missing_pages(_stop_pages(renamed_section, delegate, stub)) == [
        "the Paste line section of the brief template: page not found"
    ]
    assert _missing_pages(_stop_pages(template, delegate, "")) == [
        "the stub file: page not found"
    ]
    twice = f"{delegate}\n{_STUB_ITEM_LEAD} again\n"
    with pytest.raises(AssertionError, match="2 lines open with"):
        _stop_pages(template, twice, stub)
