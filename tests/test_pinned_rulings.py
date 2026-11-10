"""Rulings that a merge or an upstream sync could silently undo, each held as one row.

A ruling is a decision about shipped text that was taken once and that a later change, reading
only the file in front of it, can reverse by accident. Most of the skills here descend from an
upstream skill, and a refresh from upstream brings the upstream wording back. So does merging
an outside pull request written before the rulings: the one merged on 2026-11-05 put four ruled
texts in conflict at once, and each had to be settled by hand. A row is a tripwire for ONE ruled
text: it forbids the text that was ruled out, or requires the one word that carries the ruling.
It does not pin the sentence around it; everything else about the wording of a skill is left to
review.

* R1 A language pack's test-type table is never called authoritative: the project's own testing
  conventions come first, in the five places the old text stood (four held a sentence, the
  plan-critic dimensions held its question form).
* R2 The two skills that load without being asked say Python in the clause that decides when.
* R3 The plan-critic skill names no fingerprint of the one project it once described.
* R4 The PR-review skill carries no bullet about one repository's test timeout decorators.

THE SURFACE, in numbers the tests assert: 4 rulings and 5 checks. R1 is one check over 5 files
(the two planner texts, the plan-critic dimensions and the two test-plan templates), R2 is two
checks of 1 file each, R3 is one check over every markdown file of a folder and R4 is one check
over 1 file. A folder is read by a glob, so a file added later is read without an edit here; the
floor of known files only stops a glob that matched nothing from passing silently.

Every check is fired at a planted violation, also with the line break a re-wrap leaves in the
middle of the banned sentence, and at a clean text, before its silence on the real files is
trusted. The names R3 and R4 ban are built from fragments, so this file carries none of them.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from lemmi_ai_kit.checks import parse_frontmatter

_REPO = Path(__file__).resolve().parents[1]


def _cat(*fragments: str) -> str:
    return "".join(fragments)


@dataclass(frozen=True)
class _Banned:
    """A text the ruling ruled out, and a planted sample that must match it."""

    pattern: re.Pattern[str]
    plant: str


@dataclass(frozen=True)
class _Check:
    """What the files matched by `globs` must not say."""

    globs: tuple[str, ...]
    banned: tuple[_Banned, ...]
    floor: int = 1


@dataclass(frozen=True)
class _UseWhen:
    """What a skill's description must say after its first "Use when", the clause that
    decides when the skill loads."""

    skill: str
    require: tuple[str, ...]


@dataclass(frozen=True)
class _Ruling:
    key: str
    decision: str
    checks: tuple[_Check | _UseWhen, ...]


def _word(text: str) -> _Banned:
    """A phrase, matched with a line break or a hyphen between its words."""
    parts = [re.escape(part) for part in re.split(r"[\s-]+", text) if part]
    return _Banned(re.compile(r"[\s-]+".join(parts), re.IGNORECASE), text)


def _token(*fragments: str) -> _Banned:
    """One identifier held as fragments, so this file does not spell it out."""
    token = _cat(*fragments)
    return _Banned(re.compile(re.escape(token), re.IGNORECASE), token)


_PLANNER = "plugins/core/skills/test-planner"
_R1_FILES = (
    f"{_PLANNER}/SKILL.md",
    f"{_PLANNER}/references/level-assignment.md",
    "plugins/core/skills/plan-critic/references/review-dimensions.md",
    "plugins/core/src/lemmi_ai_kit/assets/ai/templates/test-plan.md",
    ".ai/templates/test-plan.md",
)

_RULINGS: tuple[_Ruling, ...] = (
    _Ruling(
        "R1",
        "a pack's test-type table is never authoritative; the project's conventions come first",
        (
            _Check(
                _R1_FILES,
                banned=(
                    _word("that table is authoritative"),
                    _word("defer to it rather than inventing a competing taxonomy"),
                    _word("does the plan use that table's level names"),
                ),
                floor=5,
            ),
        ),
    ),
    _Ruling(
        "R2",
        "the skills that load without being asked say Python where they say when to load",
        (
            _UseWhen("plugins/python/skills/test-conventions/SKILL.md", ("Python",)),
            _UseWhen("plugins/core/skills/vertical-slice/SKILL.md", ("Python",)),
        ),
    ),
    _Ruling(
        "R3",
        "plan-critic reads the project's own conventions and names no one project's stack",
        (
            _Check(
                ("plugins/core/skills/plan-critic/**/*.md",),
                banned=(
                    _token("Base", "Internal", "Client"),
                    _token("core/con", "fig.py"),
                    _token("fast", "_test"),
                    _token("integration", "_test"),
                    _token("web", "socket", "_test"),
                ),
                floor=4,
            ),
        ),
    ),
    _Ruling(
        "R4",
        "the PR-review skill has no bullet about one repository's test timeout decorators",
        (
            _Check(
                ("plugins/orchestration/skills/pr-review-concise/SKILL.md",),
                banned=(
                    _token("@fast", "_test"),
                    _token("@integration", "_test"),
                    _token("@websocket", "_test"),
                ),
            ),
        ),
    ),
)
_CHECKS = tuple((r.key, c) for r in _RULINGS for c in r.checks)

# Near misses that must not be reported: the words the ruled texts sit beside.
_NEAR_MISSES = (
    "a table that applies only where it matches, and a source that is authoritative",
    "the vertical layout of an open API behind a socket",
    "a timeout in the test and a decorator in the code",
    "a base client class and a config module of the project",
)


def _plain(text: str) -> str:
    """The text lower-cased, emphasis and code marks dropped, every run of whitespace one
    space, so a re-wrap or a re-emphasis reads the same."""
    return " ".join(re.sub(r"[*`]", "", text).split()).lower()


def _text_problems(check: _Check, where: str, text: str) -> list[str]:
    plain = _plain(text)
    return [
        f"{where} says {ban.plant!r}"
        for ban in check.banned
        if ban.pattern.search(plain)
    ]


def _use_when_problems(use: _UseWhen, where: str, text: str) -> list[str]:
    fields, error = parse_frontmatter(text)
    if fields is None:
        return [f"{where}: the frontmatter does not parse: {error}"]
    value = fields.get("description")
    if not isinstance(value, str) or not value.strip():
        return [f"{where}: the frontmatter has no description"]
    description = " ".join(value.split())
    places = description.count("Use when")
    if places != 1:
        return [
            f"{where}: {places} places say 'Use when' in the description, expected 1"
        ]
    after = description.partition("Use when")[2]
    return [
        f"{where}: after 'Use when' the description does not say {phrase!r}"
        for phrase in use.require
        if re.search(rf"\b{re.escape(phrase)}\b", after) is None
    ]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _files(globs: tuple[str, ...]) -> list[Path]:
    return sorted(
        {path for glob in globs for path in _REPO.glob(glob) if path.is_file()}
    )


def _document(description: str) -> str:
    """A SKILL.md head that carries `description` as one folded block."""
    words = description.split()
    lines = ["  " + " ".join(words[at : at + 8]) for at in range(0, len(words), 8)]
    return (
        "---\nname: planted\ndescription: >\n" + "\n".join(lines) + "\n---\n\n# Body\n"
    )


# --- the rulings, on the real files -------------------------------------------------------


@pytest.mark.parametrize("ruling", _RULINGS, ids=[r.key for r in _RULINGS])
def test_every_ruling_holds_on_the_real_files(ruling: _Ruling) -> None:
    problems: list[str] = []
    for check in ruling.checks:
        if isinstance(check, _UseWhen):
            path = _REPO / check.skill
            problems += _use_when_problems(check, path.name, _read(path))
            continue
        paths = _files(check.globs)
        assert len(paths) >= check.floor, (
            f"{ruling.key}: {len(paths)} files matched {check.globs}, expected at least "
            f"{check.floor}"
        )
        for path in paths:
            problems += _text_problems(check, str(path.relative_to(_REPO)), _read(path))
    assert not problems, f"{ruling.key} ({ruling.decision}): " + "; ".join(problems)


# --- the instruments ----------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_RULINGS) == 4, f"{len(_RULINGS)} rulings, not the 4 stated"
    assert len(_CHECKS) == 5, f"{len(_CHECKS)} checks, not the 5 stated"
    assert len({r.key for r in _RULINGS}) == 4, "two rulings share a key"
    assert len(_files(_R1_FILES)) == 5, "R1 does not read the 5 files it states"
    use_when = [c for _, c in _CHECKS if isinstance(c, _UseWhen)]
    assert len(use_when) == 2 and all((_REPO / c.skill).is_file() for c in use_when)


@pytest.mark.parametrize(
    ("key", "check"),
    _CHECKS,
    ids=[f"{key}-{index}" for index, (key, _) in enumerate(_CHECKS)],
)
def test_every_check_reports_a_planted_violation_and_passes_a_clean_text(
    key: str, check: _Check | _UseWhen
) -> None:
    if isinstance(check, _UseWhen):
        clean = _document(
            "A skill. Use when working in " + " and ".join(check.require) + "."
        )
        broken = _document("A skill. Use when working in any repository.")
        assert _use_when_problems(check, key, clean) == []
        assert len(_use_when_problems(check, key, broken)) == len(check.require)
        return
    clean = "a text that rules nothing out"
    assert _text_problems(check, key, clean) == [], (
        f"{key}: the clean text is not silent"
    )
    for ban in check.banned:
        planted = f"{clean} {ban.plant}"
        assert any(ban.plant in p for p in _text_problems(check, key, planted)), (
            f"{key}: the planted {ban.plant!r} was not reported"
        )
        if " " in ban.plant:
            rewrapped = f"{clean} {ban.plant.replace(' ', chr(10) + '    ')}"
            assert _text_problems(check, key, rewrapped), (
                f"{key}: a re-wrapped {ban.plant!r} was not reported"
            )
        for text in _NEAR_MISSES:
            assert ban.pattern.search(_plain(text)) is None, (
                f"{key}: {ban.plant!r} matched the near miss {text!r}"
            )
