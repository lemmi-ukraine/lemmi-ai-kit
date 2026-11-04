"""Six small corrections to sentences that were stale, or wider than what was measured.

Each is a few words, and no test read any of them:

* a test docstring called the hand-off stub rule "not built yet" after it was built; it now says
  where that rule is pinned;
* the docstring of the shell-prefix hook and two comments of the registration test named a count
  of hooks ("both", "the two") while `hooks.json` registers three; they name no count now;
* Default 1 of `orchestrate` called a brief the operator pastes "the fallback" and said a `pasted`
  row of the plan needs no reason. The plan template makes `pasted` an equal choice that needs no
  reason only for a row the operator will drive; the paragraph now says what the template says;
* `context_meter.py` evaluated its `X | None` annotations when it was imported, which fails on a
  Python older than 3.10; it defers them, as `launch_session.py` does;
* the section on a deadline on an event said the cancel is lost when the event is set "around" it;
  what reproduces is an event set just before the cancel;
* subsection 12m of the shared-index reference said to export with a command that writes a tar to
  standard output. A Windows PowerShell 5.1 pipe or redirect corrupts that stream, and Git's `tar`
  reads a drive letter and a colon as a host; it now says to write the archive to a file and, with
  Git's `tar`, to extract the file with a POSIX-style path. Windows' own `tar` (bsdtar) takes the
  other form, so the paragraph also says how to tell which one runs. The printed command itself
  is pinned in `test_shared_tree_recipes.py` and `test_shared_tree_rules_wording.py`.

THE SURFACE, in numbers the tests assert: 6 files of text, judged by 14 phrases that must stand
exactly once and 2 retired wordings that must not, each in its own scope (the whole file, one
section, or one paragraph; lower-cased, whitespace collapsed); 5 files scanned for a count of
hooks or scripts that `hooks.json` contradicts; 2 scripts judged for deferred annotations. The
text sites and the count-scan files overlap on purpose in 2 files, `gate_shell_prefix.py` and
`test_hook_registration.py`: the site pins the one sentence corrected there, the scan reads every
count of hooks in the file, and both rules apply to both files.
Every phrase is fired at the text its place carried before: the new words put back as the old
ones (or taken out, for a sentence the change added) must be reported for that phrase alone, and
a retired wording planted back must be reported. A re-wrapped scope must not be reported. The
count scan and the annotation check are fired at planted sources and near-misses. A heading or a
paragraph that is not found, or is found twice, fails loudly.
"""

import __future__

import ast
import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")

_SKILLS = "plugins/orchestration/skills"
_SKILL = f"{_SKILLS}/orchestrate/SKILL.md"
_TEMPLATE = f"{_SKILLS}/initiative-planner/references/execution-plan-template.md"
_SHARED_INDEX = f"{_SKILLS}/parallel-session-safety/references/shared-index-protocol.md"
_METER = f"{_SKILLS}/orchestrate/scripts/context_meter.py"
_LAUNCHER = f"{_SKILLS}/orchestrate/scripts/launch_session.py"
# The scripts judged for deferred annotations: the one that was repaired, then the one it follows.
_ANNOTATED = (_METER, _LAUNCHER)
_CODING_PATTERNS = (
    "plugins/python/skills/python-conventions/references/coding-patterns.md"
)
_HOOKS_JSON = "plugins/core/hooks/hooks.json"
_STUB_TEST = "tests/test_handoff_stub_wording.py"


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Whitespace folded and lower-cased: lines wrap, and the claims are about words."""
    return " ".join(text.split()).lower()


def _section(text: str, heading: str) -> str:
    """The one heading line that starts with `heading` and the lines under it, up to the next
    heading of the same or a higher level. A `#` line inside a fence is not a heading. Fails
    loudly when no line, or more than one, starts with `heading`."""
    lines = text.split("\n")
    inside = False
    fenced: list[bool] = []
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            fenced.append(True)
        else:
            fenced.append(inside)
    starts = [
        index
        for index, line in enumerate(lines)
        if not fenced[index] and _HEADING.match(line) and line.startswith(heading)
    ]
    assert len(starts) == 1, f"{heading!r} starts {len(starts)} headings, not 1"
    opening = _HEADING.match(lines[starts[0]])
    assert opening is not None
    body = [lines[starts[0]]]
    for index in range(starts[0] + 1, len(lines)):
        found = None if fenced[index] else _HEADING.match(lines[index])
        if found is not None and len(found[1]) <= len(opening[1]):
            break
        body.append(lines[index])
    return "\n".join(body)


def _paragraph(section: str, lead: str) -> str:
    """The one paragraph (a run of lines up to a blank line) of `section` that starts with
    `lead`. Fails loudly when no paragraph, or more than one, starts with it."""
    found = [part for part in section.split("\n\n") if part.startswith(lead)]
    assert len(found) == 1, f"{lead!r} starts {len(found)} paragraphs, not 1"
    return found[0]


def _whole(text: str) -> str:
    return text


def _cut(heading: str) -> Callable[[str], str]:
    """A scope that is the section under `heading`."""

    def scope(text: str) -> str:
        return _section(text, heading)

    return scope


def _default_one(text: str) -> str:
    """Default 1 of `orchestrate`: the one paragraph of the Dispatch section that opens it."""
    return _paragraph(_section(text, "### 2. Dispatch"), "**Default 1")


class _Edit(NamedTuple):
    """The words a place carried before and the words it carries now, both lower-cased.
    `before` is empty for a sentence that the change added."""

    before: str
    now: str


class _Site(NamedTuple):
    name: str
    path: str
    scope: Callable[[str], str]
    edits: tuple[_Edit, ...]
    # Wording the change took out and put nothing in its place.
    retired: tuple[str, ...] = ()


# The one sentence of Default 1 that set the rule for a `pasted` row, as it stood and as it reads.
_PASTED_ROW_BEFORE = (
    "a `pasted` row in the plan's `dispatch` column is that request made at plan time: "
    "write it, no reason needed."
)
_PASTED_ROW_NOW = (
    "a `pasted` plan row the operator will drive is that request made at plan time: "
    "write it, no reason needed; any other `pasted` row says why in `blocked by`."
)

_DEFAULT_ONE = _Site(
    "orchestrate Default 1",
    _SKILL,
    _default_one,
    (
        _Edit("is the *fallback*,", "is the unasked fallback,"),
        _Edit(_PASTED_ROW_BEFORE, _PASTED_ROW_NOW),
    ),
    # Retiring "not the normal path" was a choice made to pay the line budget (the file sits at
    # its cap), so putting it back means paying that line elsewhere and dropping it from here.
    retired=("not the normal path",),
)

_SITES: tuple[_Site, ...] = (
    _Site(
        "the create-collision test docstring",
        "tests/test_create_collision_wording.py",
        _whole,
        (
            _Edit(
                "separate rule that is not built yet",
                f"separate rule, pinned in {_STUB_TEST},",
            ),
        ),
    ),
    _Site(
        "the shell-prefix hook docstring",
        "plugins/core/hooks/gate_shell_prefix.py",
        _whole,
        (
            _Edit(
                "a test pins that for both hook scripts",
                "a test pins that for each hook script",
            ),
        ),
    ),
    _Site(
        "the registration test",
        "tests/test_hook_registration.py",
        _whole,
        (
            _Edit(
                "the two scripts are each exercised",
                "the scripts are each exercised",
            ),
            _Edit(
                "not a thing these two hooks do",
                "not a thing these hooks do",
            ),
        ),
    ),
    _DEFAULT_ONE,
    _Site(
        "the deadline-on-an-event section",
        _CODING_PATTERNS,
        _cut("### A deadline on an event or future"),
        (
            _Edit(
                "set in the loop iterations around the cancel",
                "set in the loop iterations just before the cancel",
            ),
        ),
    ),
    _Site(
        "subsection 12m",
        _SHARED_INDEX,
        _cut("### 12m."),
        (
            _Edit("", "write the export to a file with `-o`"),
            _Edit(
                "",
                "a windows powershell 5.1 pipe or redirect of the archive corrupts "
                "the tar",
            ),
            _Edit("", "reads a drive letter and a colon as a host"),
            _Edit(
                "so extract the file with a posix-style path",
                "so with git's `tar`, extract the file with a posix-style path",
            ),
            _Edit("", "(measured with git 2.55 and gnu tar 1.35)"),
            _Edit(
                "",
                "windows' own `tar` (bsdtar) is the reverse: it opens a drive-letter "
                "path and refuses a posix-style one (measured with bsdtar 3.8)",
            ),
            _Edit("", "`tar --version` says which of the two runs"),
        ),
        retired=("(`git archive <id>`)",),
    ),
)


def _problems(site: _Site, folded: str) -> list[str]:
    """What is wrong with a folded scope: each new phrase that is not there exactly once, each
    old phrase that is still there, and each retired wording that is."""
    found: list[str] = []
    for edit in site.edits:
        count = folded.count(edit.now)
        if count != 1:
            found.append(f"{edit.now!r} is there {count} times, not once")
        if edit.before and edit.before in folded:
            found.append(f"{edit.before!r} is still there")
    found.extend(
        f"{phrase!r} is still there" for phrase in site.retired if phrase in folded
    )
    return found


def _ids() -> list[str]:
    return [site.name for site in _SITES]


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_SITES) == 6
    assert sum(len(site.edits) for site in _SITES) == 14
    assert sum(len(site.retired) for site in _SITES) == 2
    for site in _SITES:
        assert (_REPO_ROOT / site.path).is_file(), f"{site.path} is not a file"
        assert site.scope(_read(site.path)).strip(), f"{site.name} has an empty scope"
    # The text sites and the count-scan files overlap on purpose, in exactly these 2 files.
    assert {site.path for site in _SITES} & set(_HOOK_FILES) == {
        "plugins/core/hooks/gate_shell_prefix.py",
        "tests/test_hook_registration.py",
    }
    assert len(_ANNOTATED) == 2
    for script in _ANNOTATED:
        assert (_REPO_ROOT / script).is_file(), f"{script} is not a file"


@pytest.mark.parametrize("site", _SITES, ids=_ids())
def test_the_place_says_what_it_now_says(site: _Site) -> None:
    folded = _folded(site.scope(_read(site.path)))
    assert _problems(site, folded) == []


@pytest.mark.parametrize("site", _SITES, ids=_ids())
def test_every_edit_is_reported_when_it_is_undone(site: _Site) -> None:
    """The text the place carried before is the known positive: each new phrase put back as the
    old one (or taken out, for a sentence the change added) is reported for that phrase alone,
    and a retired wording planted back is reported."""
    folded = _folded(site.scope(_read(site.path)))
    assert _problems(site, folded) == [], f"{site.name} does not hold at the start"
    for edit in site.edits:
        undone = folded.replace(edit.now, edit.before)
        expected = [f"{edit.now!r} is there 0 times, not once"]
        if edit.before:
            expected.append(f"{edit.before!r} is still there")
        assert _problems(site, undone) == expected, edit
    for phrase in site.retired:
        assert _problems(site, f"{folded} {phrase}") == [f"{phrase!r} is still there"]


@pytest.mark.parametrize("site", _SITES, ids=_ids())
def test_a_rewrapped_place_is_not_a_different_sentence(site: _Site) -> None:
    scope = site.scope(_read(site.path))
    for width in (40, 72, 100):
        wrapped = textwrap.fill(
            scope, width, break_on_hyphens=False, break_long_words=False
        )
        assert _problems(site, _folded(wrapped)) == [], (site.name, width)


def test_a_heading_or_a_paragraph_that_is_not_found_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="starts 0 headings"):
        _section("## Another\ntext\n", "### 12m.")
    with pytest.raises(AssertionError, match="starts 2 headings"):
        _section("### 12m. a\nx\n### 12m. b\ny\n", "### 12m.")
    with pytest.raises(AssertionError, match="starts 0 paragraphs"):
        _paragraph("a paragraph\n\nanother\n", "**Default 1")
    with pytest.raises(AssertionError, match="starts 2 paragraphs"):
        _paragraph("**Default 1 one\n\n**Default 1 two\n", "**Default 1")
    fenced = "### 12m. x\n```\n### 12m. in a fence\n```\n### Next\nleft out\n"
    assert "left out" not in _section(fenced, "### 12m.")


# ------------------------------------------------------------------ the file the docstring names


def test_the_file_the_docstring_points_at_reads_the_hand_off_stub_rule() -> None:
    """The docstring now sends the reader to a file: it must exist and must be about the stub."""
    assert (_REPO_ROOT / _STUB_TEST).is_file(), f"{_STUB_TEST} is not a file"
    opening = _folded(_read(_STUB_TEST))[:400]
    assert "hand-off path with a stub" in opening, opening


# ----------------------------------------------------------- a count of hooks that hooks.json denies

_COUNT_WORDS = {"both": 2, "two": 2, "three": 3, "four": 4}
_COUNTED = re.compile(r"\b(both|two|three|four)\s+(?:hook\s+)?(?:scripts?|hooks?)\b")
_HOOK_FILES = (
    "plugins/core/hooks/gate_learnings_drain.py",
    "plugins/core/hooks/gate_shell_prefix.py",
    "plugins/core/hooks/nudge_learnings_drain.py",
    "plugins/core/README.md",
    "tests/test_hook_registration.py",
)


def _registered() -> list[str]:
    """The distinct hook scripts that hooks.json registers, by file name."""
    found = re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/hooks/(\w+\.py)", _read(_HOOKS_JSON))
    return sorted(set(found))


def _miscounts(text: str, registered: int) -> list[str]:
    """Every count word that stands before `hook(s)` or `script(s)` and is not `registered`."""
    return [
        found[0]
        for found in _COUNTED.finditer(_folded(text))
        if _COUNT_WORDS[found[1]] != registered
    ]


def test_hooks_json_registers_more_than_two_scripts() -> None:
    registered = _registered()
    assert len(registered) >= 3, registered
    for name in registered:
        assert (_REPO_ROOT / "plugins/core/hooks" / name).is_file(), name


def test_no_hook_file_names_a_count_that_hooks_json_contradicts() -> None:
    registered = len(_registered())
    assert len(_HOOK_FILES) == 5
    for path in _HOOK_FILES:
        assert _miscounts(_read(path), registered) == [], path


def test_the_count_scan_flags_the_old_sentences_and_spares_near_misses() -> None:
    """Planted: the three sentences as they stood are reported against three registered hooks.
    Near-misses: the words that replaced them, a right count, and counts of other things."""
    for old, found in (
        ("A test pins that for\n    both hook scripts.", "both hook scripts"),
        ("# the two scripts are each exercised", "two scripts"),
        ("Not a thing these two hooks do", "two hooks"),
        ("the two hook scripts", "two hook scripts"),
    ):
        assert _miscounts(old, 3) == [found], old
    for fine in (
        "A test pins that for each hook script.",
        "# the scripts are each exercised",
        "Not a thing these hooks do",
        "All three hooks may be offered",
        "both options and two projects",
    ):
        assert _miscounts(fine, 3) == [], fine
    # The same words are right when two scripts are registered: the scan reads the count.
    assert _miscounts("both hook scripts", 2) == []


# ------------------------------------------------------------- one agreed rule for a pasted row

_CONDITIONS = ("the operator will drive", "any other `pasted` row", "`blocked by`")


def _pasted_bullet(template: str) -> str:
    """The one bullet of the plan template that opens with `pasted`, folded. Fails loudly when
    there is none or more than one."""
    lines = template.split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith("- `pasted` is")]
    assert len(starts) == 1, f"{len(starts)} bullets start with `pasted`"
    body = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if not line.strip() or line.startswith("- "):
            break
        body.append(line)
    return _folded("\n".join(body))


def _missing(folded: str) -> list[str]:
    return [condition for condition in _CONDITIONS if condition not in folded]


def test_default_one_and_the_plan_template_set_the_same_conditions_on_a_pasted_row() -> (
    None
):
    """The template says a `pasted` row needs no reason when the operator will drive that
    session, and that any other `pasted` row gives its reason in `Blocked by`. Default 1 names
    the same two conditions, so neither file can move without the other being read."""
    bullet = _pasted_bullet(_read(_TEMPLATE))
    default = _folded(_default_one(_read(_SKILL)))
    assert _missing(bullet) == [], "the plan template no longer sets the conditions"
    assert _missing(default) == [], "Default 1 does not set the template's conditions"


def test_the_conditions_are_missing_from_default_one_as_it_stood() -> None:
    """The known positive: the sentence before the change, and a template that lost a clause."""
    real = _folded(_default_one(_read(_SKILL)))
    assert _PASTED_ROW_NOW in real, "Default 1 does not carry the sentence under test"
    stood = real.replace(_PASTED_ROW_NOW, _PASTED_ROW_BEFORE)
    assert _missing(stood) == list(_CONDITIONS)
    bullet = _pasted_bullet(_read(_TEMPLATE))
    assert _missing(bullet.replace("`blocked by`", "the notes")) == ["`blocked by`"]


# --------------------------------------------------------------------- deferred annotations


def _defers_annotations(source: str) -> bool:
    """Whether the module, compiled by itself, carries `from __future__ import annotations`:
    the compiler sets a flag on the code object, so a comment or a string cannot fake it."""
    code = compile(source, "<source>", "exec", dont_inherit=True)
    return bool(code.co_flags & __future__.annotations.compiler_flag)


def _signature_unions(source: str) -> list[str]:
    """The functions whose signature holds an `X | Y` annotation, which Python before 3.10
    cannot evaluate when the function is defined."""
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        arguments = [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            *([node.args.vararg] if node.args.vararg else []),
            *([node.args.kwarg] if node.args.kwarg else []),
        ]
        notes = [a.annotation for a in arguments if a.annotation is not None]
        if node.returns is not None:
            notes.append(node.returns)
        if any(
            isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr)
            for note in notes
            for sub in ast.walk(note)
        ):
            names.append(node.name)
    return names


def _breaks_before_3_10(source: str) -> bool:
    return bool(_signature_unions(source)) and not _defers_annotations(source)


def test_the_context_meter_defers_its_annotations() -> None:
    assert _defers_annotations(_read(_METER)), (
        "context_meter.py has no `from __future__ import annotations`, so its `X | None` "
        "annotations are evaluated at import and fail on Python 3.9 or older"
    )
    assert not _breaks_before_3_10(_read(_METER))


def test_the_launcher_the_meter_follows_defers_its_annotations_too() -> None:
    """The control: the check sees the import in a real file that has it."""
    assert _defers_annotations(_read(_LAUNCHER))


_UNION = "def f(a: int | None) -> int | None:\n    return a\n"


def test_the_annotation_check_flags_planted_sources_and_spares_near_misses() -> None:
    flagged = {
        "a union and no import": _UNION,
        "another future import": f"from __future__ import division\n{_UNION}",
        "the import in a comment": f"# from __future__ import annotations\n{_UNION}",
        "the import in a string": f'"""from __future__ import annotations"""\n{_UNION}',
    }
    for label, source in flagged.items():
        assert _breaks_before_3_10(source), label
    spared = {
        "a union and the import": f"from __future__ import annotations\n{_UNION}",
        "no union and no import": "def f(a: int) -> int:\n    return a\n",
        "a quoted union": 'def f(a: "int | None") -> int:\n    return 1\n',
        "a union only in the body": "def f(a: int) -> int:\n    b: int | None = a\n    return 1\n",
    }
    for label, source in spared.items():
        assert not _breaks_before_3_10(source), label
    assert _signature_unions(_UNION) == ["f"]
