"""The checks of the shared index protocol tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_every_subsection_id_is_listed_in_the_skill_pointer`: Red before the change: the reference held 12f and the pointer ended at 12e.
* `test_the_pointer_check_reports_the_one_id_the_old_pointer_left_out`: Fired at the old reference and the old pointer: 12f, and only 12f.
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_SUBSECTION = re.compile(r"^### (12[a-z])\.", re.MULTILINE)

_SKILL_DIR = "plugins/orchestration/skills/parallel-session-safety"
_SKILL = f"{_SKILL_DIR}/SKILL.md"
_REFERENCE = f"{_SKILL_DIR}/references/shared-index-protocol.md"


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


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


def _reference_ids(reference: str) -> list[str]:
    return _SUBSECTION.findall(reference)


def _pointer(skill: str) -> str:
    """The blockquote lines of section 12 of `SKILL.md`: the pointer to the reference."""
    lines = _section(skill, "## 12.").split("\n")
    return "\n".join(line for line in lines if line.startswith(">"))


def _ids_missing_from_the_pointer(reference: str, skill: str) -> list[str]:
    pointer = _pointer(skill)
    return [i for i in _reference_ids(reference) if not re.search(rf"\b{i}\b", pointer)]


# --- the text each place carried before -----------------------------------------------------------


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


# --- part 1: the merge dry run --------------------------------------------------------------------


# --- part 2: editing on top of a file a peer holds staged -----------------------------------------


# --- part 3: handing one file back ----------------------------------------------------------------


# --- the tests ------------------------------------------------------------------------------------


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
