"""A review, a suite run and a commit prove "unchanged" by content, not by status rows or counts.

Status rows and `--stat` counts show which paths are dirty, not what they hold: an edit to a file
that was already modified leaves both as they were. The shared-index protocol told a session to
read `git diff --cached --stat` after the `add`, to snapshot `git diff HEAD --stat` before and
after a run and to compare status in a re-snapshot. No step recorded what was checked so that it
could be compared with the blob that lands, and the dispatch step's "checkpoint" was never defined.

What the text says now:

* 12a records `git hash-object -- <path>` at the precondition for every path to commit, untracked
  ones included, compares it with `git ls-files -s -- <path>` before the commit and with
  `git ls-tree HEAD -- <path>` after `git commit --only`, and on a mismatch reads the diff and
  asks; a blob stored with CRLF line endings is pointed at the review skill's reference by name;
* a new subsection 12g records HEAD, `git diff --cached --raw` and a SHA-256 of each path that
  `git ls-files -m -o --exclude-standard` lists, re-runs that at each boundary and at the return,
  reports new, gone and changed paths, and proves "unchanged" by equal hashes, never by equal
  counts;
* seven places link that subsection: sections 2, 6 and 12 of the safety skill, the first step of
  the protocol in section 2 of it, the dispatch step and the review step of `orchestrate`, and
  Step 1 of `branch-diff-review`. The review step says what is proved unchanged: every path
  outside the declared set. The first step of the section 2 protocol said to compare `git status`
  and file mtimes at every wave boundary while the paragraph below it says to re-snapshot by
  content hash, not by status rows; it now says that the status rows and the mtimes only find
  candidate paths and the content hash decides, so the section has one procedure, not two. That
  step lies inside the section 2 region, and the two places are judged by different wording.

Every check is fired at the text its place carried before (`old`): each requirement must report
it, so a pattern that could not fail cannot stand in for the sentence. Each requirement is also
removed from the real text, one at a time, and must be the only thing reported. A link counts only
if its target is a file that exists, and the test shows that a link to a missing file does not.
The review step as first written ("Prove "unchanged" by equal hashes", with no subject) is fired
at too. The two helpers that find a section and fold its lines have a test of their own, since
every check reads the text through them.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_FENCED = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_NUMBERED_STEP = re.compile(r"^\d+\. ")
_DASH = chr(0x2014)
_SECT = chr(0xA7)

_SKILLS = "plugins/orchestration/skills"
_SAFETY = f"{_SKILLS}/parallel-session-safety/SKILL.md"
_REFERENCE = f"{_SKILLS}/parallel-session-safety/references/shared-index-protocol.md"
_ORCHESTRATE = f"{_SKILLS}/orchestrate/SKILL.md"
_BRANCH_REVIEW = f"{_SKILLS}/branch-diff-review/SKILL.md"
_SUBSECTION_ID = "12g"


class _Check(NamedTuple):
    label: str
    needle: str


class _Place(NamedTuple):
    name: str
    path: str
    where: str
    locate: Callable[[str], str]
    required: tuple[_Check, ...]
    old: str
    # Wording that goes: it is on the old text, and must be gone from the new.
    retired: tuple[_Check, ...] = ()
    # The place must link the subsection: its id and a link to the reference file.
    linked: bool = False
    # The old text already carried a link to the reference file (the section 12 pointer).
    old_linked: bool = False


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


def _step_of(heading: str, number: int) -> Callable[[str], str]:
    """The numbered step of the list in the section that starts with `heading`: from the line
    that starts `<number>. ` to the line before the next numbered step or the next blank line.
    Empty when the section or the step is missing."""

    def locate(text: str) -> str:
        lines = _section(text, heading).split("\n")
        start = next(
            (i for i, line in enumerate(lines) if line.startswith(f"{number}. ")), None
        )
        if start is None:
            return ""
        end = start + 1
        while (
            end < len(lines)
            and lines[end].strip()
            and not _NUMBERED_STEP.match(lines[end])
        ):
            end += 1
        return "\n".join(lines[start:end])

    return locate


def _has(flat: str, needle: str) -> bool:
    return needle.lower() in flat.lower()


def _link_targets(region: str, path: str) -> list[Path]:
    """The files the prose links of `region` point at, resolved from the file `path`."""
    base = (_REPO_ROOT / path).parent
    prose = _FENCED.sub("", region)
    targets: list[Path] = []
    for link in _LINK.findall(prose):
        name = link.split("#", 1)[0]
        if name and "://" not in name:
            targets.append((base / name).resolve())
    return targets


def _links_the_reference(region: str, path: str) -> bool:
    wanted = (_REPO_ROOT / _REFERENCE).resolve()
    return any(target == wanted for target in _link_targets(region, path))


def _problems(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"{place.where} is missing from {place.path}"]
    flat = _folded(region)
    problems = [
        f"missing: {c.label}" for c in place.required if not _has(flat, c.needle)
    ]
    problems += [
        f"retired wording still there: {c.label}"
        for c in place.retired
        if _has(flat, c.needle)
    ]
    if place.linked:
        if not _has(flat, _SUBSECTION_ID):
            problems.append(f"missing: the subsection id {_SUBSECTION_ID}")
        if not _links_the_reference(region, place.path):
            problems.append("missing: a link to a reference file that exists")
    return problems


def _expected_on_old(place: _Place) -> list[str]:
    expected = [f"missing: {c.label}" for c in place.required]
    expected += [f"retired wording still there: {c.label}" for c in place.retired]
    if place.linked:
        expected.append(f"missing: the subsection id {_SUBSECTION_ID}")
        if not place.old_linked:
            expected.append("missing: a link to a reference file that exists")
    return expected


# --- the text each place carried before -----------------------------------------------------------

_OLD_SAFETY_2 = """## 2. A spec-recorded ownership split is not a runtime lock

So: **"you are the SINGLE WRITER" is a claim about the tree, not a property the check can establish.**
Re-snapshot at every wave boundary and diff against the *previous* snapshot rather than the session's
first, and classify each hit by owner (the initiative's ownership register) before calling anything a
violation. A check that cannot distinguish a violation from a neighbour is not a gate.

## 3. "Modified since read" is a collision alarm, not an annoyance
"""

# The first step of the section 2 protocol as it stood beside the re-snapshot paragraph: the status
# rows and the mtimes were the comparison, and nothing said that a content hash decides.
_OLD_SAFETY_2_STEP_1 = """## 2. A spec-recorded ownership split is not a runtime lock

**Protocol:**
1. Check collision signals at **every phase/wave boundary**, not just at start:
   `git status` of the other owner's directories, plus file mtimes (edits minutes old
   distinguish fresh-parallel from pre-existing).
2. Fresh-read every shared file immediately before editing.

## 3. "Modified since read" is a collision alarm, not an annoyance
"""

_OLD_SAFETY_6 = """## 6. A suite verdict over a contended tree is void

**Protocol:**
- Snapshot `git diff HEAD --stat` **before and after** any suite run whose result you will
  report. If the set changed, the run is void.
- `git status --short` under-reports: uncommitted work in a subsystem you are not reviewing
  is invisible without `git diff HEAD --stat -- <dir>`.

## 7. Hand-off briefs are claims sheets
"""

_OLD_SAFETY_12 = f"""## 12. The index is shared

- **Verify and stage in SEPARATE tool calls, then verify again after staging.** Combining the check
  with the action it gates is what loses the race {_DASH} three collisions in one session came from exactly
  that pattern. The only trustworthy check is `git diff --cached --stat` read *after* the `add` and
  immediately before the commit; a pre-`add` `git status` is a claim about a moment that has passed.

Corollary for claims: "verified unchanged" and "staged" are **perishable** here. Only a content hash
or a commit SHA survives long enough to be quoted in a hand-off; re-derive anything else at write
time ({_SECT}7, {_SECT}9).

> **Five measured failure modes, with the exact commands for each, are in
> [references/shared-index-protocol.md](references/shared-index-protocol.md):** contention is
> per-LINE and defeats both standard guards (12a); a held index is a lock that blocked four
> planned sessions (12b); work done AFTER staging silently invalidates the staged set (12c);
> `git push` answering "Everything up-to-date" means you are not on that branch (12d); and how
> to back up a tree for a multi-branch history operation (12e).

## Cross-references
"""

_OLD_ORCHESTRATE_2 = """### 2. Dispatch

- Safety: prefer read-only/plan modes for opinion tasks (`codex exec` default sandbox,
  `cursor-agent --mode plan`, `grok --permission-mode plan`). Grant write access only for
  implementation briefs, only workspace-scoped, never bypass/danger modes. Ensure `git status`
  is clean (or checkpoint) before any worker may write.

### 2a. Launching a headless `claude -p` session
"""

_OLD_ORCHESTRATE_3 = f"""### 3. Review before merging {_DASH} results are claims
A worker's summary is a claim, not verification. For every returned result: read the actual
diff/files, run the brief's definition-of-done check yourself (or have fast-worker run it), and
reconcile against the plan. If something's off, **rewrite the brief and spin another worker** {_DASH}
don't silently patch over it yourself unless the fix is trivial.

### 4. High-stakes decisions
"""

# The step as first written: it said "unchanged" by equal hashes and named nothing that is proved
# unchanged.
_FIRST_WRITTEN_ORCHESTRATE_3 = f"""### 3. Review before merging {_DASH} results are claims
A worker's summary is a claim, not verification. For every returned result: read the actual
diff/files, run the brief's definition-of-done check yourself (or have fast-worker run it), and
reconcile against the plan. If something's off, **rewrite the brief and spin another worker** {_DASH}
don't silently patch over it yourself unless the fix is trivial. Prove "unchanged" by equal hashes
([12g](../parallel-session-safety/references/shared-index-protocol.md)). **A verifier is an
instrument too.**

### 4. High-stakes decisions
"""

_OLD_BRANCH_REVIEW_1 = f"""## Step 1 {_DASH} Establish the input, and state what it excludes

```bash
git diff HEAD --stat                         # snapshot the dirty set BEFORE reviewing
```

**Re-snapshot `git diff HEAD --stat` after reviewing.** If the set changed, another session edited the
tree mid-review and the verdict is void {_DASH} restart, do not merge a stale verdict
(`parallel-session-safety` {_SECT} 6, which also notes `git status --short` under-reports).

## Step 2 {_DASH} Map ownership before reviewing anything
"""

_OLD_REFERENCE_12A = f"""### 12a. Contention is per-LINE, and both standard guards are blind to it

Before committing any path that `git status` showed as already dirty *and that you did not dirty
yourself*:

```bash
git diff HEAD -- <path>     # confirm EVERY + line is yours
```

**Anything that re-adds the path {_DASH} `git add`, `git commit --only`, `git commit -a` {_DASH} silently undoes
this**, so say so explicitly in the hand-off: the next person's instinct is to `git add` first.

### 12b. A held index is a LOCK, not a save point
"""


# --- the places -----------------------------------------------------------------------------------

_LINKED_PLACES: tuple[_Place, ...] = (
    _Place(
        name="safety-section-2",
        path=_SAFETY,
        where="section 2 of the safety skill",
        locate=_section_of("## 2."),
        required=(
            _Check("the re-snapshot is by content hash", "by content hash"),
            _Check("not by status rows", "not by status rows"),
        ),
        old=_OLD_SAFETY_2,
        linked=True,
    ),
    _Place(
        name="safety-section-2-protocol-step-1",
        path=_SAFETY,
        where="step 1 of the protocol in section 2 of the safety skill",
        locate=_step_of("## 2.", 1),
        required=(
            _Check(
                "the status rows and the mtimes find candidate paths",
                "find candidate paths",
            ),
            _Check("the content hash decides", "the content hash decides"),
        ),
        old=_OLD_SAFETY_2_STEP_1,
        retired=(
            _Check(
                "the status rows and the mtimes were the comparison itself",
                "directories, plus file mtimes",
            ),
        ),
        linked=True,
    ),
    _Place(
        name="safety-section-6",
        path=_SAFETY,
        where="section 6 of the safety skill",
        locate=_section_of("## 6."),
        required=(_Check("the dirty set is hashed as well", "hash the dirty set too"),),
        old=_OLD_SAFETY_6,
        linked=True,
    ),
    _Place(
        name="safety-section-12",
        path=_SAFETY,
        where="section 12 of the safety skill",
        locate=_section_of("## 12."),
        required=(
            _Check(
                "the hash recorded at the precondition",
                "record `git hash-object -- <path>`",
            ),
            _Check(
                "compared with the blob that lands",
                "compare it with the blob that lands",
            ),
            _Check(
                "the commit check is the staged paths and the recorded hashes",
                "The only trustworthy checks, read *after* the `add` and immediately before "
                "the commit, are `git diff --cached --stat` and the recorded hashes",
            ),
        ),
        old=_OLD_SAFETY_12,
        retired=(
            _Check(
                "the commit check was the staged paths alone",
                "The only trustworthy check is `git diff --cached --stat`",
            ),
        ),
        linked=True,
        old_linked=True,
    ),
    _Place(
        name="orchestrate-dispatch",
        path=_ORCHESTRATE,
        where="step 2 of the orchestrate protocol",
        locate=_section_of("### 2. Dispatch"),
        required=(
            _Check(
                "the checkpoint is a content checkpoint of the dirty set",
                "checkpoint the dirty set by content",
            ),
        ),
        old=_OLD_ORCHESTRATE_2,
        linked=True,
    ),
    _Place(
        name="orchestrate-review",
        path=_ORCHESTRATE,
        where="step 3 of the orchestrate protocol",
        locate=_section_of("### 3. Review before merging"),
        required=(
            _Check(
                "what is proved unchanged is every path outside the declared set",
                "Prove no path outside the declared set changed",
            ),
            _Check("the proof is equal hashes", "by equal hashes"),
        ),
        old=_OLD_ORCHESTRATE_3,
        linked=True,
    ),
    _Place(
        name="branch-diff-review-step-1",
        path=_BRANCH_REVIEW,
        where="Step 1 of branch-diff-review",
        locate=_section_of("## Step 1"),
        required=(
            _Check(
                "the re-snapshot compares content hashes",
                "compare content hashes of the dirty set",
            ),
            _Check(
                "equal counts do not prove an unchanged tree",
                "equal counts do not prove",
            ),
        ),
        old=_OLD_BRANCH_REVIEW_1,
        linked=True,
    ),
)

_REFERENCE_PLACES: tuple[_Place, ...] = (
    _Place(
        name="reference-12a",
        path=_REFERENCE,
        where="subsection 12a of the reference",
        locate=_section_of("### 12a."),
        required=(
            _Check(
                "the hash is recorded at the precondition, untracked paths included",
                "record `git hash-object -- <path>` for each added or modified path to commit, "
                "untracked ones included",
            ),
            _Check(
                "a rebuilt entry records the id hash-object -w printed",
                "the id `git hash-object -w` printed",
            ),
            _Check(
                "compared with the staged blob before the commit",
                "`git ls-files -s -- <path>` before `git commit`",
            ),
            _Check(
                "compared with the committed blob after the commit",
                "`git ls-tree HEAD -- <path>` after `git commit --only`",
            ),
            _Check(
                "a mismatch is read and asked about",
                "On a mismatch, read the diff and ask",
            ),
            _Check(
                "a blob stored with CRLF is pointed at the review skill's reference by name",
                "reading-gate-output reference of `post-task-review`",
            ),
        ),
        old=_OLD_REFERENCE_12A,
    ),
    _Place(
        name="reference-12g",
        path=_REFERENCE,
        where="subsection 12g of the reference",
        locate=_section_of("### 12g."),
        required=(
            _Check(
                "status rows and counts show which paths are dirty, not what they hold",
                "Status rows and `--stat` counts show which paths are dirty, not what they hold",
            ),
            _Check(
                "HEAD, the staged raw diff and a SHA-256 of each dirty path are recorded",
                "record HEAD, `git diff --cached --raw` and a SHA-256 of each path "
                "`git ls-files -m -o --exclude-standard` lists",
            ),
            _Check(
                "re-run at each boundary and at the return",
                "re-run it at each boundary and at the return",
            ),
            _Check(
                "new, gone and changed paths are reported, inside or outside the declared set",
                "report new, gone and changed paths, inside or outside the declared set",
            ),
            _Check(
                "unchanged is proved by equal hashes, never by equal counts",
                'Prove "unchanged" by equal hashes, never by equal counts',
            ),
            _Check(
                "a hash flags a neighbour's edit, so each path is classified by owner",
                "classify each changed path by owner",
            ),
        ),
        old="",
    ),
)

_PLACES: tuple[_Place, ...] = (*_LINKED_PLACES, *_REFERENCE_PLACES)


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Seven places that link the subsection, in three files, and two places in the reference."""
    assert len(_LINKED_PLACES) == 7, (
        f"{len(_LINKED_PLACES)} linking places, not the 7 stated"
    )
    linked_files = {place.path for place in _LINKED_PLACES}
    assert len(linked_files) == 3, (
        f"{len(linked_files)} files, not 3: {sorted(linked_files)}"
    )
    assert len(_REFERENCE_PLACES) == 2
    reference_files = {place.path for place in _REFERENCE_PLACES}
    assert reference_files == {_REFERENCE}, (
        f"reference places in {sorted(reference_files)}"
    )
    assert not linked_files & reference_files, (
        "a file is in both scans: the reference is not judged by the link rule"
    )
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    empty = [p for p in sorted({*linked_files, _REFERENCE}) if not _read(p).strip()]
    assert not empty, f"{len(empty)} files are empty: {empty}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_proves_unchanged_by_content(place: _Place) -> None:
    """Red before the change: no place named a hash of the dirty set or linked 12g."""
    problems = _problems(place, _read(place.path))
    assert not problems, f"{place.path} ({place.name}): {problems}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_fails_on_the_text_it_replaced(place: _Place) -> None:
    """Fired at the old text: every requirement reports it. 12g is new, so its old text is empty
    and the place itself is the one thing reported missing."""
    reported = _problems(place, place.old)
    if not place.old:
        assert reported == [f"{place.where} is missing from {place.path}"]
        return
    assert reported == _expected_on_old(place), (
        f"{place.name}: on the old text the checks reported {reported}"
    )


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_requirement_is_load_bearing(place: _Place) -> None:
    """Removing one requirement from the real text reports that one and no other."""
    region = place.locate(_read(place.path))
    assert region.strip(), f"{place.where} is missing from {place.path}"
    flat = _folded(region)
    for check in place.required:
        start = flat.lower().find(check.needle.lower())
        assert start >= 0, f"{place.name}: {check.label!r} is not in the real text"
        stripped = flat[:start] + flat[start + len(check.needle) :]
        gaps = [c.label for c in place.required if not _has(stripped, c.needle)]
        assert gaps == [check.label], (
            f"{place.name}: removing {check.label!r} reported {gaps}"
        )


def test_a_link_to_a_missing_file_is_not_a_link_to_the_reference() -> None:
    """The link check can fail. A link to the reference is found; a link whose target does not
    exist, a link to another file that does exist and a link inside a fenced block are not."""
    path = _SAFETY
    linked = "See [12g](references/shared-index-protocol.md) for the hash."
    assert _links_the_reference(linked, path), (
        "a real link to the reference is not found"
    )
    assert _links_the_reference(f"{linked}\n\nMore text.", path)
    missing = "See [12g](references/no-such-file.md) for the hash."
    other = "See [12g](SKILL.md) for the hash."
    fenced = "```\n[12g](references/shared-index-protocol.md)\n```"
    for text in (missing, other, fenced):
        assert not _links_the_reference(text, path), text


def test_a_place_that_is_missing_says_so_by_name() -> None:
    place = _LINKED_PLACES[0]
    assert _problems(place, "## 3. Another section\n\nText.\n") == [
        f"{place.where} is missing from {place.path}"
    ]
    assert _problems(place, "") == [f"{place.where} is missing from {place.path}"]


def test_a_proof_that_names_nothing_it_proves_unchanged_is_reported() -> None:
    """The review step as first written said 'Prove "unchanged" by equal hashes': a reader cannot
    tell what is proved unchanged. Only the missing subject is reported, since the hashes, the
    id and the link were there."""
    place = next(p for p in _LINKED_PLACES if p.name == "orchestrate-review")
    assert _problems(place, _FIRST_WRITTEN_ORCHESTRATE_3) == [
        "missing: what is proved unchanged is every path outside the declared set"
    ]


def test_the_fold_joins_a_rewrapped_sentence_and_drops_bold_marks() -> None:
    """Every check reads the text through the fold: lines join, a run of spaces is one space,
    bold marks go, the ends are trimmed."""
    assert _folded("  a **bold**  word\n     and a second\nline  \n") == (
        "a bold word and a second line"
    )


_SECTIONS = "\n".join(
    [
        "#### 12a. A look-alike that only contains the wanted prefix",
        "### 12a. First",
        "first body",
        "#### 12a.1 Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "```",
        "### 12b. Second",
        "second body",
        "## 13. Higher",
        "higher body",
        "",
    ]
)


def test_a_section_runs_to_the_next_heading_of_its_level_or_a_higher_one() -> None:
    """The section finder starts at the heading that begins with its text, keeps a deeper heading
    and a `#` line inside a fence, stops at a heading of its own level or a higher one, and
    finds nothing for a heading that is not there."""
    first = _section(_SECTIONS, "### 12a.")
    assert first.startswith("### 12a. First"), first
    for kept in ("first body", "deeper body", "a comment in a fence"):
        assert kept in first, first
    assert "second body" not in first, first
    second = _section(_SECTIONS, "### 12b.")
    assert "second body" in second and "higher body" not in second, second
    assert _section(_SECTIONS, "### 12z.") == ""


_STEPS = "\n".join(
    [
        "## 2. A section",
        "**Protocol:**",
        "1. first step, first line",
        "   first step, second line",
        "2. second step",
        "",
        "11. a look-alike that only starts with a 1",
        "",
        "## 3. Another section",
        "1. a step of another section",
        "",
    ]
)


def test_a_step_runs_to_the_next_step_or_the_next_blank_line() -> None:
    """The step finder takes the numbered line and its continuation lines, stops at the next
    numbered step or a blank line, does not take '11.' for step 1, stays inside its own section
    and finds nothing for a step or a section that is not there."""
    assert _step_of("## 2.", 1)(_STEPS) == (
        "1. first step, first line\n   first step, second line"
    )
    assert _step_of("## 2.", 2)(_STEPS) == "2. second step"
    assert _step_of("## 2.", 11)(_STEPS) == "11. a look-alike that only starts with a 1"
    assert _step_of("## 3.", 1)(_STEPS) == "1. a step of another section"
    assert _step_of("## 2.", 3)(_STEPS) == ""
    assert _step_of("## 9.", 1)(_STEPS) == ""


def test_a_missing_protocol_step_says_so_by_name() -> None:
    """A section 2 that lost its protocol is a failure with a name, not an empty pass."""
    place = next(
        p for p in _LINKED_PLACES if p.name == "safety-section-2-protocol-step-1"
    )
    only_the_paragraph = "## 2. A section\n\nSo: a paragraph and no list.\n"
    assert _problems(place, only_the_paragraph) == [
        f"{place.where} is missing from {place.path}"
    ]
    assert _problems(place, "") == [f"{place.where} is missing from {place.path}"]
