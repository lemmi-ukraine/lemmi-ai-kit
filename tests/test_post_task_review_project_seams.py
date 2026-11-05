"""`post-task-review` names the project's own lint command and doc map, not one stack's.

Every completion review runs this skill, in every project that installs the kit. It told all of them
to run `ruff check --fix` (a Python linter), to resolve a default from a `Field(default=...)`
declaration (one framework's), to pair its deletion gate with "the AGENTS.md deletion-sweep rule" (a
rule a project may not have), and it shipped a documentation matrix of `backend/app/` paths as if it
were the project's. The project's AGENTS.md already names its lint command, so the skill points
there, and the matrix stays as a labelled sample that the project's own matrix replaces. Step 7b
sent every project to that sample with no word of the project's own matrix, so it now says to check
the project's own code-to-docs matrix, else the sample.

THE SURFACE, in numbers the tests assert: 7 places in 3 files (SKILL.md Step 6; SKILL.md as a whole,
for the stack's lint command, the framework's default and the output template; the SKILL.md deletion
gate; SKILL.md Step 7b; the checklist's Step 6; the checklist as a whole, for the stack's lint
command; the matrix's head) and 13 checks. The checklist is scanned whole, as SKILL.md is: a lint
command named in any other row is as much one stack's as one named in Step 6. The scan for `ruff
check` is fired at a planted line first, and again at a checklist whose Step 6 is clean and whose
other row names it; each check is fired at the text its place carried (`_OLD_*`, unedited excerpts)
and must report it.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
)
_SKILL_MD = _SKILL / "SKILL.md"
_CHECKLIST = _SKILL / "references" / "review-checklist.md"
_MATRIX = _SKILL / "references" / "doc-impact-matrix.md"
_HEADING = re.compile(r"^(#{1,6})\s")


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis, code-span and quote marks dropped and whitespace folded to one space, so a
    re-wrapped quoted label is the same sentence."""
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


def _between(text: str, start: str, end: str, where: str) -> str:
    begin = text.find(start)
    if begin < 0:
        raise AssertionError(f"{where}: no marker {start!r}")
    stop = text.find(end, begin)
    if stop < 0:
        raise AssertionError(f"{where}: no marker {end!r} after {start!r}")
    return text[begin:stop]


def _head(text: str, where: str) -> str:
    """Everything above the first `## ` heading: the title and whatever labels the file."""
    cut = re.search(r"^## ", text, flags=re.M)
    if cut is None:
        raise AssertionError(f"{where}: no `## ` heading, so there is no head to read")
    return text[: cut.start()]


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
    """Every needle is in the region, whatever its capitalisation: a checklist row opens with a
    capital where the skill's sentence does not."""
    return lambda region: all(n.lower() in _plain(region).lower() for n in needles)


def _lacks(*needles: str) -> Callable[[str], bool]:
    return lambda region: all(n.lower() not in _plain(region).lower() for n in needles)


# The em dash of the old sentence, built from its code point so a retyped dash cannot slip in.
_EM_DASH = chr(0x2014)
# A lint command of one stack, as the skill and its checklist spelled it.
_RUFF = "ruff check"
# A config-default declaration of one framework, with both the ASCII dots and the ellipsis.
_FIELD_DEFAULT = "Field(default"

_OLD_STEP_6 = r"""6. **Run Linting and Diagnostics** — `ruff check --fix` on all modified files, `read_lints` on all modified files.
   **Before quoting any gate result, check you are reading the question you actually asked** —
"""

_OLD_CONFIG_DEFAULT = r"""Resolve the default from the `Field(default=…)` AND every
   compose/cloudbuild pin, which disagree here: `STT__PIPELINE_MODE` defaults to `mono` in both
   `config.py` and `docker-compose.yaml` while only the cloudbuilds set stereo."""

_OLD_GATE = r"""- **Doc-retirement gate** (step 7): before deleting any doc, enumerate its EXECUTABLE artifacts
  separately from its knowledge — grep it for fenced code blocks and "Reproduce" / "How to find" /
  query sections, and relocate each VERBATIM next to the step that needs it, not into a summary.
  A relocation pass naturally captures claims and obligations and systematically misses
  queries/repro steps; "the checklist survived" and "the means of executing it survived" are two
  separate gates. Pair with the AGENTS.md deletion-sweep rule (partition targets by `git ls-files`
  first — the untracked half is unrecoverable).

See [references/review-checklist.md](references/review-checklist.md) for a quick-reference checklist.
"""

_OLD_LINT_OUTPUT = r"""### 6. Linting Results
{Summary of ruff and diagnostic results}
"""

_OLD_CHECKLIST_STEP_6 = r"""### Step 6: Linting
- [ ] `read_lints` run on ALL modified files
- [ ] `ruff check --fix` run on all changed Python files
- [ ] All remaining issues resolved
"""

_OLD_MATRIX_HEAD = r"""# Documentation Impact Matrix

## Code Path to Documentation Mapping

Use this matrix to determine which documentation files to check when code in a given path changes.
"""

_OLD_STEP_7B = r"""#### 7b. Consult the Documentation Impact Matrix

For each modified file, check [references/doc-impact-matrix.md](references/doc-impact-matrix.md) to
determine which documentation files might be affected.

#### 7c. Read and Evaluate Affected Docs
"""


def _step_7b(text: str, where: str) -> str:
    return _section(text, "#### 7b.", where)


def _step_6(text: str, where: str) -> str:
    return _between(
        text, "6. **Run Linting and Diagnostics**", "**Before quoting any gate", where
    )


def _whole_file(text: str, where: str) -> str:
    if not text.strip():
        raise AssertionError(f"{where}: the file is empty")
    return text


def _deletion_gate(text: str, where: str) -> str:
    return _between(
        text, "- **Doc-retirement gate**", "See [references/review-checklist.md]", where
    )


def _checklist_step_6(text: str, where: str) -> str:
    return _section(text, "### Step 6:", where)


_PLACES: tuple[_Place, ...] = (
    _Place(
        "skill-step-6",
        _SKILL_MD,
        _step_6,
        (
            _Check(
                "Step 6 names the project's lint command",
                _says("the project's lint command"),
            ),
            _Check("Step 6 no longer names ruff check", _lacks(_RUFF)),
        ),
        _OLD_STEP_6,
    ),
    _Place(
        "skill-config-default-and-gate-and-output",
        _SKILL_MD,
        _whole_file,
        (
            _Check("SKILL.md names no ruff check anywhere", _lacks(_RUFF)),
            _Check(
                "the config-default sentence no longer names Field(default",
                _lacks(_FIELD_DEFAULT),
            ),
            _Check(
                "the output template summarises lint results, not ruff's",
                _says("Summary of lint and diagnostic results"),
            ),
        ),
        _OLD_STEP_6 + "\n" + _OLD_CONFIG_DEFAULT + "\n" + _OLD_LINT_OUTPUT,
    ),
    _Place(
        "skill-deletion-gate",
        _SKILL_MD,
        _deletion_gate,
        (
            _Check(
                "the gate no longer leans on the AGENTS.md deletion-sweep rule",
                _lacks("AGENTS.md deletion-sweep rule"),
            ),
            _Check(
                "the gate says on its own that the untracked half is unrecoverable",
                _says(
                    f"Partition targets by git ls-files first {_EM_DASH} the untracked half is unrecoverable."
                ),
            ),
        ),
        _OLD_GATE,
    ),
    _Place(
        "skill-step-7b",
        _SKILL_MD,
        _step_7b,
        (
            _Check(
                "Step 7b sends the reader to the project's own code-to-docs matrix, else the sample",
                _says("the project's own code-to-docs matrix, else the sample"),
            ),
        ),
        _OLD_STEP_7B,
    ),
    _Place(
        "checklist-step-6",
        _CHECKLIST,
        _checklist_step_6,
        (
            _Check(
                "the checklist names the project's lint command",
                _says("the project's lint command"),
            ),
            _Check("the checklist no longer names ruff check", _lacks(_RUFF)),
        ),
        _OLD_CHECKLIST_STEP_6,
    ),
    _Place(
        "checklist-whole-file",
        _CHECKLIST,
        _whole_file,
        (_Check("the checklist names no ruff check anywhere", _lacks(_RUFF)),),
        _OLD_CHECKLIST_STEP_6,
    ),
    _Place(
        "matrix-head",
        _MATRIX,
        _head,
        (
            _Check("the matrix head says it is a sample", _says("sample")),
            _Check(
                "the matrix head says the project's own matrix replaces it",
                _says("the project's own"),
            ),
        ),
        _OLD_MATRIX_HEAD,
    ),
)


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text, place.path.name)
    return [c.label for c in place.checks if not c.holds(region)]


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_PLACES) == 7, f"{len(_PLACES)} places, not the 7 stated"
    assert len({p.path for p in _PLACES}) == 3, "the places are not in 3 distinct files"
    checks = [c for p in _PLACES for c in p.checks]
    assert len(checks) == 13, f"{len(checks)} checks, not the 13 stated"
    names = [p.name for p in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    empty = [p.path.name for p in _PLACES if not _read(p.path).strip()]
    assert not empty, f"empty files: {empty}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_names_the_projects_own_commands_and_map(place: _Place) -> None:
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path.name} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The old text carried the stack-specific wording and none of the new, so each check of the
    place must say so, or it tests nothing."""
    reported = _gaps(place, place.old)
    assert len(reported) == len(place.checks), (
        f"{place.name}: {len(reported)} of {len(place.checks)} checks saw the old text; "
        f"blind: {[c.label for c in place.checks if c.label not in reported]}"
    )


def test_step_7b_still_links_the_sample_matrix() -> None:
    """What the rewording had to keep: Step 7b links the sample, and the sample exists, so the
    fallback it names can be opened."""
    section = _step_7b(_read(_SKILL_MD), "SKILL.md")
    assert "(references/doc-impact-matrix.md)" in section
    assert _MATRIX.is_file()


def test_the_config_default_sentence_keeps_the_pins_it_compares() -> None:
    """What the edit had to keep: the default is resolved from the pins as well, and the
    sentence that follows still reads."""
    text = _plain(_read(_SKILL_MD))
    assert "AND every compose/cloudbuild pin" in text
    assert "which disagree here" in text


def test_the_scans_see_planted_text() -> None:
    """Fired at planted wording: a ruff line in each spelling, a checklist whose Step 6 is clean
    and whose Step 0 row names ruff (the Step 6 scan misses it, the whole-file scan reports it), a
    Field default with the ASCII dots and with the ellipsis, a head that lacks the label, a Step 7b
    that drops the word of the project's own matrix or names the sample first, a missing heading,
    and a region that holds one of two needles (a join that settled for any needle would pass the
    two-needle checks on it)."""
    ruff = "6. Run Linting - `ruff check --fix` on all modified files"
    assert not _lacks(_RUFF)(ruff)
    assert _lacks(_RUFF)("run the project's lint command")
    checklist = (
        "### Step 0: Impact\n- [ ] dependents listed (ruff check)\n\n"
        "### Step 6: Linting\n- [ ] the project's lint command run\n"
    )
    assert _lacks(_RUFF)(_checklist_step_6(checklist, "planted"))
    assert not _lacks(_RUFF)(_whole_file(checklist, "planted"))
    own_first = _says("the project's own code-to-docs matrix, else the sample")
    assert own_first(
        "check the project's own code-to-docs matrix, else the sample in it"
    )
    assert not own_first("check the project's own matrix, else the sample")
    assert not own_first("check the sample, else the project's own code-to-docs matrix")
    both = "Alpha and beta, not gamma"
    assert _says("alpha", "beta")(both)
    assert not _says("alpha", "delta")(both)
    assert _lacks("delta", "epsilon")(both)
    assert not _lacks("delta", "alpha")(both)
    for spelling in ("`Field(default=...)`", "`Field(default=…)`"):
        assert not _lacks(_FIELD_DEFAULT)(
            f"Resolve the default from the {spelling} AND the pins"
        )
    assert (
        _head("# Matrix\n\nUse this.\n\n## Paths\n| a | b |\n", "planted")
        == "# Matrix\n\nUse this.\n\n"
    )
    assert not _says("sample")(_head("# Matrix\n\nUse this.\n\n## Paths\n", "planted"))
    assert _says("sample", "the project's own")(
        _head(
            "# Matrix\n\n> A **sample**; the project's own\n> replaces it.\n\n## Paths\n",
            "planted",
        )
    )
    with pytest.raises(AssertionError, match="no heading"):
        _section("### Step 5: Fixes\n- [ ] one\n", "### Step 6:", "planted")
    with pytest.raises(AssertionError, match="no `## ` heading"):
        _head("# Only a title\n", "planted")
