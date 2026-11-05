"""A verification pass is an instrument, so it is given controls, and a fresh reader is given limits.

The kit's known-answer controls were for instruments: a worker runs its own checker against a
known-positive and a known-negative fixture. `orchestrate` said a worker's summary is a claim and
gave a verifier no control, and `finding-verification.md` could not say whether the self-review
over-corrected or the independent verifier rubber-stamped: which is better calibrated was
**UNKNOWN**. A pass that is never shown a false claim cannot be told from a pass that confirms
everything.

What the text says now, in the two places of the Orchestration pack this file owns:

* a verifier is an instrument too: it gets one to three controls, which are real claims with one
  fact changed, planted unmarked by the dispatcher or invented by the pass; its confirmations are
  trusted only if it rejected every control, and a return without control results is unverified;
  the key stays out of the artifact;
* a fresh reader's brief is limited: at most four claims per pass, a tool-call budget stated in
  the brief, the counting traps its AGENTS.md lists, if any, and the author re-runs every
  finding it cites. The traps are conditional because a project whose AGENTS.md lists none has
  none to give: the template the kit seeds has no such list, so "its AGENTS.md lists them" was a
  premise that is false there.

The two places are section 3 of `orchestrate` and the "Provenance and blind spot" section of
`branch-diff-review`'s finding-verification reference. The review skill's own step for the re-review
after a fix round is the other pack's to assert, in its own test; this file reads neither it nor
any other file.

Section 3 of `orchestrate` also says what a fresh reader is, in the sentence that names it: a new
agent that re-derives each claim from the pinned source. The reference glosses the term in a
parenthesis of its own, and a dispatcher meets the term first in section 3.

Every check is fired at the text its place carried before (`old`), and each requirement is removed
from the real text one at a time and must be the only thing reported. A heading that goes missing
fails with a message that names it, not with an empty pass. The two helpers that find a section
and fold its lines have a test of their own, since every check reads the text through them.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_DASH = chr(0x2014)

_SKILLS = "plugins/orchestration/skills"
_ORCHESTRATE = f"{_SKILLS}/orchestrate/SKILL.md"
_FINDING_VERIFICATION = (
    f"{_SKILLS}/branch-diff-review/references/finding-verification.md"
)


class _Check(NamedTuple):
    label: str
    needle: str


class _Place(NamedTuple):
    name: str
    path: str
    where: str
    locate: Callable[[str], str]
    old: str


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space, so a re-wrapped
    line or a re-emphasised word is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


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


def _section_of(heading: str) -> Callable[[str], str]:
    return lambda text: _section(text, heading)


def _has(flat: str, needle: str) -> bool:
    return needle.lower() in flat.lower()


# The controls: the clauses do not overlap, so that removing one reports that one and no other.
_CONTROLS: tuple[_Check, ...] = (
    _Check("a verifier is an instrument too", "A verifier is an instrument too"),
    _Check(
        "one to three controls, real claims with one fact changed",
        "Give it one to three controls: real claims with one fact changed",
    ),
    _Check(
        "planted unmarked by the dispatcher or invented by the pass",
        "planted unmarked by the dispatcher or invented by the pass",
    ),
    _Check(
        "its confirmations are trusted only if it rejected every control",
        "Trust its confirmations only if it rejected every control",
    ),
    _Check(
        "a return without control results is unverified",
        "a return without control results is unverified",
    ),
    _Check("the key stays out of the artifact", "Keep the key out of the artifact"),
)

# The four phrases of the fresh reader's brief, the same in both places.
_FRESH_READER: tuple[_Check, ...] = (
    _Check("a fresh reader is named", "A fresh reader"),
    _Check("at most four claims per pass", "at most four claims per pass"),
    _Check(
        "a tool-call budget stated in the brief",
        "a tool-call budget stated in the brief",
    ),
    _Check(
        "the counting traps its AGENTS.md lists, if it lists any",
        "the counting traps its AGENTS.md lists, if any",
    ),
    _Check(
        "the author re-runs every finding it cites",
        "the author re-runs every finding it cites",
    ),
)

_REQUIRED: tuple[_Check, ...] = (*_CONTROLS, *_FRESH_READER)

# Wording that goes: the brief said the repository's known counting traps are listed in its
# AGENTS.md. A project whose AGENTS.md has no such list (every project the kit seeds) has none to
# give, so the premise was false there. The words "counting traps" stay.
_RETIRED: tuple[_Check, ...] = (
    _Check(
        "every repository is assumed to have an AGENTS.md that lists its counting traps",
        "AGENTS.md lists them",
    ),
)

# What a fresh reader is. It must stand in the sentence that names the reader, not beside it.
_GLOSS = "a new agent that re-derives each claim from the pinned source"
_FRESH_READER_SENTENCE = "A fresh reader"


def _glossed(region: str) -> bool:
    """Whether the sentence of the region that begins with a fresh reader carries the gloss.
    False when no sentence begins with it."""
    for sentence in re.split(r"(?<=\.)\s+", _folded(region)):
        if sentence.startswith(_FRESH_READER_SENTENCE):
            return _GLOSS in sentence
    return False


# --- the text each place carried before -----------------------------------------------------------

_OLD_ORCHESTRATE_3 = f"""### 3. Review before merging {_DASH} results are claims
A worker's summary is a claim, not verification. For every returned result: read the actual
diff/files, run the brief's definition-of-done check yourself (or have fast-worker run it), and
reconcile against the plan. If something's off, **rewrite the brief and spin another worker** {_DASH}
don't silently patch over it yourself unless the fix is trivial.

**The review loop has three skills and none is optional:**

### 4. High-stakes decisions
"""

_OLD_FINDING_VERIFICATION = f"""## Provenance and blind spot

Two readings, and n=1 each cannot distinguish them: either the checklist overcame self-preference
bias, **or** the self-review over-corrected while the independent verifier rubber-stamped. Which is
better calibrated is **UNKNOWN**. What justifies this pass is the *mechanism* {_DASH} Part A checks with
outputs {_DASH} not the ratio.

---

## Part A {_DASH} tool-grounded (may move severity)
"""

# The fresh reader's sentence as first written, with the premise that goes, and as it stands now.
# Each is put into a place as the first lines of its section, so the place judges it by its own
# heading.
_PREMISE_AS_FIRST_WRITTEN = (
    "A fresh reader (a new agent that re-derives each claim from the pinned source) gets a\n"
    "brief with at most four claims per pass, a tool-call budget stated in the brief and the\n"
    "repository's known counting traps (its AGENTS.md lists them); the author re-runs every\n"
    "finding it cites.\n"
)
_PREMISE_AS_CONDITIONAL = (
    "A fresh reader (a new agent that re-derives each claim from the pinned source) gets a\n"
    "brief with at most four claims per pass, a tool-call budget stated in the brief and, from\n"
    "the repository, the counting traps its AGENTS.md lists, if any; the author re-runs every\n"
    "finding it cites.\n"
)


# --- the places -----------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="orchestrate-section-3",
        path=_ORCHESTRATE,
        where="section 3 of orchestrate",
        locate=_section_of("### 3. Review before merging"),
        old=_OLD_ORCHESTRATE_3,
    ),
    _Place(
        name="finding-verification-provenance",
        path=_FINDING_VERIFICATION,
        where="the Provenance and blind spot section of finding-verification",
        locate=_section_of("## Provenance and blind spot"),
        old=_OLD_FINDING_VERIFICATION,
    ),
)


def _gaps(
    place: _Place, text: str, checks: tuple[_Check, ...] = _REQUIRED
) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    flat = _folded(region)
    return [f"missing: {c.label}" for c in checks if not _has(flat, c.needle)]


def _retired(place: _Place, text: str) -> list[str]:
    """The wording of `_RETIRED` that the place still carries, one line per check, or the
    place itself when it is missing."""
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    flat = _folded(region)
    return [
        f"retired wording still there: {c.label}"
        for c in _RETIRED
        if _has(flat, c.needle)
    ]


def _with_sentence(place: _Place, sentence: str) -> str:
    """The text the place carried before, with `sentence` as the first lines of its section."""
    heading, _, rest = place.old.partition("\n")
    return f"{heading}\n{sentence}{rest}"


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Two places in two files of one pack, each present and non-empty, and eleven requirements
    that share no clause."""
    assert len(_PLACES) == 2, f"{len(_PLACES)} places, not the 2 stated"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 2, f"{len(paths)} files, not 2: {sorted(paths)}"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"
    assert (len(_CONTROLS), len(_FRESH_READER)) == (6, 5)
    labels = [check.label for check in _REQUIRED]
    assert len(set(labels)) == len(labels), "two requirements share a label"
    assert len(_RETIRED) == 1, f"{len(_RETIRED)} retired phrases, not the 1 stated"
    required = {check.needle.lower() for check in _REQUIRED}
    assert not any(c.needle.lower() in n for c in _RETIRED for n in required), (
        "a retired phrase is part of a required one"
    )


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_verifier_is_given_controls(place: _Place) -> None:
    """Red before the change: no section named a control or said what a verifier's confirmation
    is worth."""
    gaps = _gaps(place, _read(place.path), _CONTROLS)
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_a_fresh_readers_brief_is_limited(place: _Place) -> None:
    """The four phrases of the fresh reader's brief are in both files. Red before the change:
    'fresh reader' had no hit in the pack."""
    gaps = _gaps(place, _read(place.path), _FRESH_READER)
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_the_brief_does_not_assume_the_repository_lists_its_counting_traps(
    place: _Place,
) -> None:
    """Red before the change: both places said the traps are listed in the repository's
    AGENTS.md, which is false for a project whose AGENTS.md has no such list."""
    problems = _retired(place, _read(place.path))
    assert not problems, f"{place.path} ({place.name}): {problems}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_the_premise_as_first_written_is_reported_and_the_conditional_is_not(
    place: _Place,
) -> None:
    """The retired-wording check can fail. The sentence as first written is reported as retired,
    and the requirement that replaces it is missing from it. The conditional sentence is not
    reported as retired, and it carries the requirement."""
    first = _with_sentence(place, _PREMISE_AS_FIRST_WRITTEN)
    assert _retired(place, first) == [
        f"retired wording still there: {_RETIRED[0].label}"
    ]
    assert _gaps(place, first, _FRESH_READER) == [
        "missing: the counting traps its AGENTS.md lists, if it lists any"
    ]
    now = _with_sentence(place, _PREMISE_AS_CONDITIONAL)
    assert _retired(place, now) == []
    assert _gaps(place, now, _FRESH_READER) == []


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_fails_on_the_text_a_place_carried_before(place: _Place) -> None:
    """Fired at the old text: every requirement reports it, since the old text carried none of
    the new wording."""
    assert _gaps(place, place.old) == [f"missing: {c.label}" for c in _REQUIRED]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_requirement_is_load_bearing(place: _Place) -> None:
    """Removing one requirement from the real text reports that one and no other."""
    region = place.locate(_read(place.path))
    assert region.strip(), f"{place.where} is missing from {place.path}"
    flat = _folded(region)
    for check in _REQUIRED:
        start = flat.lower().find(check.needle.lower())
        assert start >= 0, f"{place.name}: {check.label!r} is not in the real text"
        stripped = flat[:start] + flat[start + len(check.needle) :]
        gaps = [c.label for c in _REQUIRED if not _has(stripped, c.needle)]
        assert gaps == [check.label], (
            f"{place.name}: removing {check.label!r} reported {gaps}"
        )


def test_a_missing_heading_is_a_failure_with_a_name() -> None:
    """A section that goes missing must not read as a pass."""
    for place in _PLACES:
        text = "## Another section\n\nA verifier is an instrument too.\n"
        assert _gaps(place, text) == [f"{place.where} is missing from {place.path}"]
        assert _gaps(place, "") == [f"{place.where} is missing from {place.path}"]


def test_the_claims_cap_is_not_a_larger_number() -> None:
    """The brief says four. A copy that says a larger number, or no number, reports the cap."""
    place = _PLACES[0]
    planted = (
        f"### 3. Review before merging {_DASH} results are claims\n"
        "A fresh reader's brief carries at most twenty claims per pass.\n"
    )
    assert "missing: at most four claims per pass" in _gaps(place, planted)


def test_orchestrate_says_what_a_fresh_reader_is_in_the_sentence_that_names_it() -> (
    None
):
    """Red before the change: section 3 used the term and defined it nowhere."""
    place = _PLACES[0]
    assert place.name == "orchestrate-section-3"
    assert _glossed(place.locate(_read(place.path)))


def test_a_fresh_reader_with_no_gloss_in_its_own_sentence_is_reported() -> None:
    """The gloss check can fail. The sentence with no gloss, a gloss that stands in the sentence
    before the reader's, and a section with no such sentence are reported; a glossed sentence
    passes."""
    without_gloss = (
        "Keep the key out of the artifact. A fresh reader's brief carries at most four claims\n"
        "per pass, a tool-call budget stated in the brief and the counting traps its AGENTS.md\n"
        "lists, if any; the author re-runs every finding it cites.\n"
    )
    beside = (
        f"Keep the key out of the artifact ({_GLOSS}). A fresh reader's brief carries at\n"
        "most four claims per pass.\n"
    )
    assert not _glossed(without_gloss)
    assert not _glossed(beside)
    assert not _glossed("Nothing about readers here.\n")
    assert _glossed(
        f"Keep the key out.\nA fresh reader ({_GLOSS}) gets a brief. More.\n"
    )


def test_the_fold_joins_a_rewrapped_sentence_and_drops_bold_marks() -> None:
    """Every check reads the text through the fold: lines join, a run of spaces is one space,
    bold marks go, the ends are trimmed."""
    assert _folded("  a **bold**  word\n     and a second\nline  \n") == (
        "a bold word and a second line"
    )


_SECTIONS = "\n".join(
    [
        "#### 3. A look-alike that only contains the wanted prefix",
        "### 3. First",
        "first body",
        "#### 3.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "```",
        "### 4. Second",
        "second body",
        "## 5. Higher",
        "higher body",
        "",
    ]
)


def test_a_section_runs_to_the_next_heading_of_its_level_or_a_higher_one() -> None:
    """The section finder starts at the heading that begins with its text, keeps a deeper heading
    and a `#` line inside a fence, stops at a heading of its own level or a higher one, and
    finds nothing for a heading that is not there."""
    first = _section(_SECTIONS, "### 3.")
    assert first.startswith("### 3. First"), first
    for kept in ("first body", "deeper body", "a comment in a fence"):
        assert kept in first, first
    assert "second body" not in first, first
    second = _section(_SECTIONS, "### 4.")
    assert "second body" in second and "higher body" not in second, second
    assert _section(_SECTIONS, "### 9.") == ""
