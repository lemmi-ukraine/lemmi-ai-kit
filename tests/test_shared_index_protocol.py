"""The shared-index protocol covers three operations it lacked, and its pointer lists every subsection.

Three gaps, one part each, so that each part can be read and approved alone:

* a merge into a tree others are writing had no dry run, and 12e said checkout and rebase "never
  silently discard", which is wrong for an ignored file: merge, checkout and switch overwrite an
  ignored file at a path the target tracks, by default. Subsection 12h dry-runs the merge with
  `git merge-tree --write-tree`, reads its exit code directly (0 clean, 1 conflicts, else
  unmeasured), takes the write set from `git diff --name-only --no-renames HEAD <tree>`, and runs
  `git merge --no-edit --no-overwrite-ignore <target>` without a stash only when nothing is staged
  and `git status` over that set prints nothing. The empty status is the protection, because the
  flag did not stop a non-fast-forward merge when it was measured;
* a held index (12b) was a stop with no route for editing on top of a file a peer holds staged.
  Subsection 12i rehearses in a plain copy outside the checkout, asks the holder, and applies only
  on consent, never staging or committing the file, with the `git ls-files -s` listing unchanged;
* section 3b's "hand that file back" gave no way to revert only your own lines. Subsection 12j
  has the holder save its change with `git diff --output` and a hashed backup, check the reverse
  patch with `git apply -R --check` while the index entry is still staged, then
  `git restore --staged` and `git apply -R`, never a wholesale revert, and prove the result. The
  check runs first because it reads only the working tree: when the peer's lines sit inside the
  patch's context it fails, and a check that fails after the entry was dropped leaves the holder's
  staged work half undone. The patch is written with `--output` because a PowerShell redirect can
  add a byte-order mark and CR bytes, and a patch written that way fails the check.

The section 12 pointer in `SKILL.md` named 12a to 12e while the reference held 12f. The test reads
every `### 12x.` id from the reference and requires each in the pointer, so a subsection added
later cannot be left out of it again.

Every check is fired at the text its place carried before (`old`), and each requirement is removed
from the real text one at a time and must be the only thing reported. The pointer check is fired
at the old reference with the old pointer, where it reports 12f and only 12f. Subsection 12j as it
first stood (a redirect, and the entry dropped before the check) is fired at too. The two helpers
that find a section and fold its lines have a test of their own, since every check reads the text
through them.
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
_SUBSECTION = re.compile(r"^### (12[a-z])\.", re.MULTILINE)
_DASH = chr(0x2014)

_SKILL_DIR = "plugins/orchestration/skills/parallel-session-safety"
_SKILL = f"{_SKILL_DIR}/SKILL.md"
_REFERENCE = f"{_SKILL_DIR}/references/shared-index-protocol.md"
_REFERENCE_FLOOR = 11


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
    retired: tuple[_Check, ...] = ()
    # The id the place must name and link, or "" when the place is a subsection itself.
    links: str = ""


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


def _links_the_reference(region: str, path: str) -> bool:
    """Whether a prose link of `region` points at the reference file, resolved from `path`."""
    base = (_REPO_ROOT / path).parent
    wanted = (_REPO_ROOT / _REFERENCE).resolve()
    for link in _LINK.findall(_FENCED.sub("", region)):
        name = link.split("#", 1)[0]
        if name and "://" not in name and (base / name).resolve() == wanted:
            return True
    return False


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
    if place.links:
        if not re.search(rf"\b{place.links}\b", flat):
            problems.append(f"missing: the id {place.links}")
        if not _links_the_reference(region, place.path):
            problems.append("missing: a link to a reference file that exists")
    return problems


def _expected_on_old(place: _Place) -> list[str]:
    expected = [f"missing: {c.label}" for c in place.required]
    expected += [f"retired wording still there: {c.label}" for c in place.retired]
    if place.links:
        expected.append(f"missing: the id {place.links}")
        expected.append("missing: a link to a reference file that exists")
    return expected


def _reference_ids(reference: str) -> list[str]:
    return _SUBSECTION.findall(reference)


def _pointer(skill: str) -> str:
    """The blockquote lines of section 12 of `SKILL.md`: the pointer to the reference."""
    lines = _section(skill, "## 12.").split("\n")
    return "\n".join(line for line in lines if line.startswith(">"))


def _ids_missing_from_the_pointer(reference: str, skill: str) -> list[str]:
    pointer = _pointer(skill)
    return [i for i in _reference_ids(reference) if not re.search(rf"\b{i}\b", pointer)]


# The commands of the hand-back block in the order they run: the holder's change is saved, the
# reverse patch is checked against the working tree while the index entry is still staged, the
# entry is dropped, the patch is applied.
_HAND_BACK_COMMANDS = (
    "git diff --output=<patch> --cached -- <path>",
    "git apply -R --check <patch>",
    "git restore --staged -- <path>",
    "git apply -R <patch>",
)


def _hand_back_order_problems(region: str) -> list[str]:
    """The four commands of the hand-back block, each by name when it is not there and the order
    once when they stand in another."""
    spots = [region.find(command) for command in _HAND_BACK_COMMANDS]
    missing = [
        f"missing command: {command}"
        for command, spot in zip(_HAND_BACK_COMMANDS, spots, strict=True)
        if spot < 0
    ]
    if missing:
        return missing
    if spots != sorted(spots):
        return ["the commands are not in the order: save, check, drop the entry, apply"]
    return []


# --- the text each place carried before -----------------------------------------------------------

_OLD_12B = """### 12b. A held index is a LOCK, not a save point

So: treat "staged, awaiting review" as an **exposure window**, not a resting state. Keep it short.
When asked to stage without committing, say in the hand-off that the index is held and name the
paths. When a long gap is expected, prefer leaving the work unstaged and handing over the exact
`git add` command, or hand over a patch file. **Leave the index empty when the session ends.**

Read it the other direction too: a peer's dispatch doc naming *your* session's state is a signal to
go and read what else they assumed about you.

### 12c. Work done AFTER staging silently invalidates the staged set
"""

_OLD_12E = f"""### 12e. A multi-branch history operation: back up the TRACKED layer twice, never touch untracked

`git checkout` / `git rebase` refuse (they never silently discard) only when a file both **differs
between the current and target tree** *and* **has a local modification**. So the real collision
surface is exactly the **tracked-and-modified** set {_DASH} checkout never touches a path the target branch
does not itself track at that spot.

That makes the safe protocol for running a 14-branch sync inside a tree holding ~44 modified tracked
files and ~88 untracked paths of someone else's live work:

### 12f. Your BASE is a draft until it commits
"""

_OLD_3B = f"""## 3b. VERIFY-don't-reapply has a BRANCH-level twin, and a worktree grep is blind to it

- If a peer branch already covers a site, **hand that file back** {_DASH} revert your version rather than
  competing. Keep only the sites the other branch did not touch, and say which those are.
- The residue to check afterwards: a changelog entry describing work that lives on **another**
  branch is a dangling claim on yours.

## 4. Shared repo-root artifacts are collision surfaces
"""

_OLD_REFERENCE_IDS = """### 12a. Contention
### 12b. A held index
### 12c. Work done AFTER staging
### 12d. `git push` answering
### 12e. A multi-branch history operation
### 12f. Your BASE is a draft until it commits
"""

_OLD_POINTER = """## 12. The index is shared

> **Five measured failure modes, with the exact commands for each, are in
> [references/shared-index-protocol.md](references/shared-index-protocol.md):** contention is
> per-LINE and defeats both standard guards (12a); a held index is a lock that blocked four
> planned sessions (12b); work done AFTER staging silently invalidates the staged set (12c);
> `git push` answering "Everything up-to-date" means you are not on that branch (12d); and how
> to back up a tree for a multi-branch history operation (12e).

## Cross-references
"""

# Subsection 12j as it first stood: a shell redirect wrote the patch, and the staged entry was
# dropped before the patch was checked.
_FIRST_WRITTEN_12J = """### 12j. Handing one file back: revert your own lines, never the whole file

The holder hands a file back (12i) without a wholesale revert, which would also remove the peer's
lines. Save the holder's own change and a hashed backup first (12g), then:

```bash
git diff --cached -- <path> > <patch>   # only the holder's change; the peer's lines are unstaged
git restore --staged -- <path>          # the index entry returns to HEAD's blob; the worktree stays
git apply -R --check <patch>            # exit 0, or stop and ask
git apply -R <patch>                    # removes the holder's lines from the worktree only
```

Prove it: `git ls-files -s -- <path>` shows the blob `git ls-tree HEAD -- <path>` shows, the
holder's lines are gone, the peer's lines are unchanged and the line endings kept (the file equals
the hashed backup minus the holder's lines, byte for byte).
"""

# The new save command and the old order of the other three, to fire the order check at.
_RESTORE_BEFORE_CHECK = """```bash
git diff --output=<patch> --cached -- <path>
git restore --staged -- <path>
git apply -R --check <patch>
git apply -R <patch>
```
"""


# --- part 1: the merge dry run --------------------------------------------------------------------

_MERGE_DRY_RUN = _Place(
    name="merge-dry-run-subsection",
    path=_REFERENCE,
    where="subsection 12h of the reference",
    locate=_section_of("### 12h."),
    required=(
        _Check(
            "the dry run is git merge-tree --write-tree, git 2.38 or later",
            "`git merge-tree --write-tree HEAD <target>` (git 2.38+)",
        ),
        _Check(
            "it touches neither the index nor the working tree",
            "touches neither the index nor the working tree",
        ),
        _Check(
            "the exit code is read directly: 0 clean, 1 conflicts, else unmeasured",
            "read the command's own exit code, never through a pipe: 0 is clean, 1 is "
            "conflicts, anything else is unmeasured",
        ),
        _Check(
            "an unresolvable target also exits 1, so it is resolved first",
            "An unresolvable `<target>` also exits 1, so resolve it first",
        ),
        _Check(
            "the write set is git diff --name-only --no-renames HEAD <tree>",
            "`git diff --name-only --no-renames HEAD <tree>`",
        ),
        _Check(
            "nothing is staged, and the git-merge manual says why",
            "the git-merge manual says the index must generally match HEAD",
        ),
        _Check(
            "git status over the write set prints nothing",
            "`git status --porcelain --untracked-files=all --ignored -- <set>`",
        ),
        _Check(
            "the merge runs with --no-overwrite-ignore and without a stash",
            "`git merge --no-edit --no-overwrite-ignore <target>` without a stash",
        ),
        _Check(
            "the empty status is the protection: the flag did not stop a non-fast-forward merge",
            "when measured (git 2.55) the flag refused a fast-forward merge but not a "
            "non-fast-forward one",
        ),
        _Check(
            "otherwise 12e or coordination, and never a peer's staged files stashed (12b)",
            "use 12e or coordinate, and never stash a peer's staged files (12b)",
        ),
    ),
    old="",
)

_OVERWRITE_DEFAULT = _Place(
    name="overwrite-default-in-12e",
    path=_REFERENCE,
    where="subsection 12e of the reference",
    locate=_section_of("### 12e."),
    required=(
        _Check(
            "merge, checkout and switch overwrite an ignored file at a tracked path by default",
            "`git merge`, `git checkout` and `git switch` overwrite an ignored file at a "
            "path the target tracks, by default",
        ),
        _Check(
            "the tracked-and-modified set is not the whole collision surface",
            "it is not the whole collision surface",
        ),
        _Check("12e points at the dry run", "dry-run a merge first (12h)"),
    ),
    old=_OLD_12E,
    retired=(
        _Check(
            "the surface was said to be exactly the tracked-and-modified set",
            "the real collision surface is exactly the tracked-and-modified set",
        ),
    ),
)

_PART_1: tuple[_Place, ...] = (_MERGE_DRY_RUN, _OVERWRITE_DEFAULT)


# --- part 2: editing on top of a file a peer holds staged -----------------------------------------

_HELD_FILE = _Place(
    name="held-file-subsection",
    path=_REFERENCE,
    where="subsection 12i of the reference",
    locate=_section_of("### 12i."),
    required=(
        _Check(
            "a held index is a stop for staging (12b)",
            "A held index is a stop for staging (12b)",
        ),
        _Check(
            "rehearse in a plain copy outside the checkout",
            "rehearse first in a plain copy outside the checkout",
        ),
        _Check("never a worktree", "never a worktree"),
        _Check(
            "the copy is built from the index, so files with local secrets are not copied",
            "build it from the index (`git checkout-index -a --prefix=<dir>/`), so a file "
            "with local secrets is not copied",
        ),
        _Check("gate there", "Gate there"),
        _Check(
            "script the edit with a check-only mode",
            "script the edit with a check-only mode",
        ),
        _Check("ask the holder", "ask the holder"),
        _Check("only on the holder's consent", "Only on consent"),
        _Check(
            "the file is never staged or committed until it is handed back (12j)",
            "you never stage or commit the file until it is handed back (12j)",
        ),
        _Check(
            "the holder commits only from the index (12a)",
            "the holder commits only from the index (12a)",
        ),
        _Check(
            "the edit is applied while the file is staged with nothing unstaged",
            "you apply while the file is staged with nothing unstaged",
        ),
        _Check(
            "the git ls-files -s listing must not change",
            "the `git ls-files -s` listing must not change",
        ),
    ),
    old="",
)

_HELD_INDEX_LINK = _Place(
    name="held-file-in-12b",
    path=_REFERENCE,
    where="subsection 12b of the reference",
    locate=_section_of("### 12b."),
    required=(
        _Check(
            "a held file is a stop for staging, and 12i is the route for editing on top of it",
            "to edit on top of it, with the holder's consent, see 12i",
        ),
    ),
    old=_OLD_12B,
)

_PART_2: tuple[_Place, ...] = (_HELD_FILE, _HELD_INDEX_LINK)


# --- part 3: handing one file back ----------------------------------------------------------------

_HAND_BACK = _Place(
    name="hand-back-subsection",
    path=_REFERENCE,
    where="subsection 12j of the reference",
    locate=_section_of("### 12j."),
    required=(
        _Check("never a wholesale revert", "without a wholesale revert"),
        _Check(
            "the holder's own change is saved from the index with --output",
            "git diff --output=<patch> --cached -- <path>",
        ),
        _Check(
            "a shell redirect is not the way to write the patch",
            "with `--output`, not a shell redirect",
        ),
        _Check("a hashed backup is saved", "a hashed backup"),
        _Check("the reverse patch is checked", "git apply -R --check <patch>"),
        _Check(
            "a failed check leaves the index and the files as they were",
            "stop there and ask, with the index and the files as they were",
        ),
        _Check(
            "the index entry returns to HEAD's blob", "git restore --staged -- <path>"
        ),
        _Check("the reverse patch is applied", "git apply -R <patch>"),
        _Check(
            "HEAD's blob is proved staged",
            "`git ls-files -s -- <path>` shows the blob `git ls-tree HEAD -- <path>` shows",
        ),
        _Check(
            "its own lines gone, the peer's unchanged, the line endings kept",
            "the holder's lines are gone, the peer's lines are unchanged and the line "
            "endings kept",
        ),
    ),
    old="",
    retired=(
        _Check("the patch was written by a shell redirect", "-- <path> > <patch>"),
    ),
)

_HAND_THAT_FILE_BACK = _Place(
    name="hand-back-in-section-3b",
    path=_SKILL,
    where="section 3b of the safety skill",
    locate=_section_of("## 3b."),
    required=(
        _Check(
            "revert your own lines, not the file", "revert your own lines, not the file"
        ),
    ),
    old=_OLD_3B,
    retired=(
        _Check(
            "revert your version, with no way to keep the peer's lines",
            "revert your version rather than competing",
        ),
    ),
    links="12j",
)

_PART_3: tuple[_Place, ...] = (_HAND_BACK, _HAND_THAT_FILE_BACK)

_PLACES: tuple[_Place, ...] = (*_PART_1, *_PART_2, *_PART_3)


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Six places in two files, three parts of two places each, and a reference of at least the
    eleven subsections the pointer test was written for, with no gap in their letters."""
    assert len(_PLACES) == 6, f"{len(_PLACES)} places, not the 6 stated"
    assert [len(_PART_1), len(_PART_2), len(_PART_3)] == [2, 2, 2]
    paths = {place.path for place in _PLACES}
    assert paths == {_REFERENCE, _SKILL}, f"{len(paths)} files: {sorted(paths)}"
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    ids = _reference_ids(_read(_REFERENCE))
    assert len(ids) >= _REFERENCE_FLOOR, (
        f"{len(ids)} subsections, fewer than {_REFERENCE_FLOOR}"
    )
    assert ids == [f"12{chr(ord('a') + i)}" for i in range(len(ids))], (
        f"ids with a gap: {ids}"
    )


def test_every_subsection_id_is_listed_in_the_skill_pointer() -> None:
    """Red before the change: the reference held 12f and the pointer ended at 12e."""
    missing = _ids_missing_from_the_pointer(_read(_REFERENCE), _read(_SKILL))
    assert not missing, f"the section 12 pointer does not name {missing}"


def test_the_pointer_check_reports_the_one_id_the_old_pointer_left_out() -> None:
    """Fired at the old reference and the old pointer: 12f, and only 12f."""
    assert _reference_ids(_OLD_REFERENCE_IDS) == [f"12{c}" for c in "abcdef"]
    assert _ids_missing_from_the_pointer(_OLD_REFERENCE_IDS, _OLD_POINTER) == ["12f"]
    listed = _OLD_POINTER.replace("(12e).", "(12e), 12f.")
    assert listed != _OLD_POINTER, "the planted repair changed nothing"
    assert _ids_missing_from_the_pointer(_OLD_REFERENCE_IDS, listed) == []


def _assert_whole(places: tuple[_Place, ...]) -> None:
    for place in places:
        problems = _problems(place, _read(place.path))
        assert not problems, f"{place.path} ({place.name}): {problems}"


def test_the_merge_dry_run_text_is_whole() -> None:
    """Part 1. Red before the change: no 12h, and 12e said the surface was the tracked set."""
    _assert_whole(_PART_1)


def test_the_held_file_text_is_whole() -> None:
    """Part 2. Red before the change: a held index was a stop and nothing covered editing on top."""
    _assert_whole(_PART_2)


def test_the_hand_back_text_is_whole() -> None:
    """Part 3. Red before the change: 'hand that file back' said nothing about your own lines."""
    _assert_whole(_PART_3)


def test_the_reverse_patch_is_checked_before_the_staged_entry_is_dropped() -> None:
    """Part 3. The check reads only the working tree, so it runs while the entry is still staged:
    when the peer's lines sit inside the patch's context it fails, and then nothing has changed."""
    region = _section(_read(_REFERENCE), "### 12j.")
    assert _hand_back_order_problems(region) == []


def test_the_order_check_reports_a_block_that_dropped_the_entry_first() -> None:
    """The order check can fail: the old order is reported, a block with no commands names all
    four, and the subsection as first written names the save command it lacked."""
    assert _hand_back_order_problems(_RESTORE_BEFORE_CHECK) == [
        "the commands are not in the order: save, check, drop the entry, apply"
    ]
    assert _hand_back_order_problems("") == [
        f"missing command: {command}" for command in _HAND_BACK_COMMANDS
    ]
    assert _hand_back_order_problems(_section(_FIRST_WRITTEN_12J, "### 12j.")) == [
        "missing command: git diff --output=<patch> --cached -- <path>"
    ]


def test_the_hand_back_text_as_first_written_is_reported() -> None:
    """The subsection as first written wrote the patch with a shell redirect and said nothing of a
    failed check. Each new wording is reported missing, the redirect is seen, and nothing else is."""
    assert _problems(_HAND_BACK, _FIRST_WRITTEN_12J) == [
        "missing: the holder's own change is saved from the index with --output",
        "missing: a shell redirect is not the way to write the patch",
        "missing: a failed check leaves the index and the files as they were",
        "retired wording still there: the patch was written by a shell redirect",
    ]


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_fails_on_the_text_it_replaced(place: _Place) -> None:
    """Fired at the old text: every requirement reports it and every retired phrase is seen. A
    subsection that is new has no old text, so the place itself is what is reported missing."""
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
    """The link check can fail: a real link is found; a link to a missing file, a link to
    another file that exists and a link inside a fenced block are not."""
    linked = "Hand it back ([12j](references/shared-index-protocol.md))."
    assert _links_the_reference(linked, _SKILL)
    for text in (
        "Hand it back ([12j](references/no-such-file.md)).",
        "Hand it back ([12j](SKILL.md)).",
        "```\n[12j](references/shared-index-protocol.md)\n```",
    ):
        assert not _links_the_reference(text, _SKILL), text


def test_a_place_that_is_missing_says_so_by_name() -> None:
    assert _problems(_HAND_BACK, "### 12i. A held file\n\nText.\n") == [
        f"{_HAND_BACK.where} is missing from {_HAND_BACK.path}"
    ]
    assert _problems(_HAND_BACK, "") == [
        f"{_HAND_BACK.where} is missing from {_HAND_BACK.path}"
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
