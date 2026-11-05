"""The safety skill's backup rule names the commit as the backup and a byte copy as a convenience.

The rule for a shared `.ai/` data file that is about to be drained, rewritten or bulk-edited said:
snapshot it to a durable path, verify the copy with `cmp`, and confirm the snapshot's location is
not itself ignored, because a gitignored backup directory cannot be committed without `git add -f`
and an uncommitted backup is not a backup. A drain now commits the buffer at a restore point and
keeps its byte copy local: never committed, and listed in the project's ignore file. So the rule
asked a drain operator to confirm the opposite of what the drain asks for.

What the rule says now: commit the file as it stands first, in its own commit; that commit, the
restore point, is the backup; an uncommitted backup is still not a backup, so work that exists only
uncommitted has none, whatever copies sit beside it; a local byte copy of the committed file,
checked with `cmp`, is a convenience. Its three measured losses, its width (any shared `.ai/` data
file, not only the learnings buffer) and its closing re-read stay as they were.

THE SURFACE, in numbers the tests assert: one file and one list item in it, cut by its lead. The
item is found exactly once, runs at least `_MIN_ITEM_CHARS` characters once its whitespace is folded
(a number no re-flow can change) and is followed by its sibling list item, so a cut that stopped at
the lead line, or swallowed the next rule, cannot pass. Every check is a function over the text of
that item. `test_every_check_sees_its_planted_positive` fires them at the old item (verbatim, apart
from the dash built from `chr()`) and at near-misses before their silence on the real file is
trusted. `test_a_rewrap_of_the_shipped_rule_passes_every_check` shows that a re-flowed line is the
same text at each of `_WIDTHS`, and `test_the_rewrap_widths_are_different_shapes` shows those widths
to be different layouts. A width the rule is already filled to may change nothing, so a reflow of
the shipped rule to any width leaves every test green.
"""

import re
import textwrap
from itertools import pairwise
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SAFETY = (
    _REPO_ROOT
    / "plugins"
    / "orchestration"
    / "skills"
    / "parallel-session-safety"
    / "SKILL.md"
)

# The first words of the list item, short enough to stay on one line when it is re-wrapped.
_LEAD = "- **A shared append-only data file"
# Counted over the folded text, so it does not move when the item is re-flowed to another width.
_MIN_ITEM_CHARS = 800
# The widths a re-wrap is tried at, narrow to wide.
_WIDTHS = (48, 72, 130)
_DASH = chr(0x2014)


# --- slicers over a string -----------------------------------------------------------------


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _view(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space: what every pattern
    below is matched against, so a re-wrapped line is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _item(text: str, lead: str) -> str:
    """The list item whose first line starts with `lead`, and the indented lines after it.

    It ends at the first blank line or the first line that is not indented, which is the next
    list item. A lead that is not found, or is found twice, fails loudly with the lead named, so
    a renamed rule is a loud failure and never an empty match.
    """
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith(lead)]
    assert len(starts) == 1, f"{len(starts)} lines start {lead!r}, not exactly 1"
    body = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if not line.strip() or not line.startswith("  "):
            break
        body.append(line)
    return "\n".join(body)


def _rule() -> str:
    return _item(_read(_SAFETY), _LEAD)


def _missing(view: str, facts: dict[str, str]) -> list[str]:
    """The names of the facts whose pattern is not found in `view`."""
    return [
        name
        for name, pattern in facts.items()
        if not re.search(pattern, view, re.IGNORECASE)
    ]


# --- what the rule must say now, and what must stay ----------------------------------------

_NOW: dict[str, str] = {
    "the file is committed as it stands, first, in its own commit": (
        r"\bcommit it as it stands first, in its own commit\b"
    ),
    "that commit, the restore point, is the backup": (
        r"\bthat commit, the restore point, is the backup\b"
    ),
    "work that exists only uncommitted has no backup, whatever copies sit beside it": (
        r"\bwork that exists only uncommitted has none, whatever copies sit beside it\b"
    ),
    "a local byte copy of the committed file is a convenience": (
        r"\blocal byte copy of the committed file\b.{0,40}\bis a convenience\b"
    ),
}

# In the old text too, and still required: the rule must not be weakened for what it was written
# for, which is work that exists only uncommitted.
_KEPT: dict[str, str] = {
    "the width: any shared data file under .ai/ that is drained, rewritten or bulk-edited": (
        r"\bany shared `\.ai/` data file you are about to drain, rewrite, or bulk-edit\b"
    ),
    "evidence: a merge took a shared buffer from 236 entries to 15": (
        r"\b236 entries to 15\b"
    ),
    "evidence: a truncating write destroyed 20 lines of another session's edit": (
        r"\bdestroyed 20 lines of \*?another\*? session's uncommitted edit\b"
    ),
    "evidence: a deliverable vanished while its backup was three edits stale": (
        r"\bits backup was three edits stale\b"
    ),
    "the reason: an uncommitted backup is not a backup": (
        r"\ban uncommitted backup is not a backup\b"
    ),
    "the closing step: re-read the file immediately before each edit": (
        r"\bre-read the file immediately before each edit\b"
    ),
}

# --- what the old text said, as the classes of shape it came in ----------------------------

# slug -> (pattern, what the old text did).
_OLD_SHAPES: dict[str, tuple[str, str]] = {
    "the-copy-is-the-backup": (
        r"\b(?:snapshot|copy)\b.{0,20}\bto a durable path\b",
        "made a copy at a durable path the backup",
    ),
    "the-copy-must-not-be-ignored": (
        r"\b(?:not|never)\s+(?:be\s+|itself\s+)?(?:git)?ignored\b",
        "asked for the copy's location to be confirmed NOT ignored",
    ),
    "force-add-the-copy": (
        r"\bgit add (?:-f|--force)\b",
        "told the reader to force-stage an ignored copy",
    ),
    "commit-the-copy-with-the-change": (
        r"\bcommitted alongside the change\b",
        "said the copy is committed with the change",
    ),
}

# The old list item, verbatim apart from the dash built from chr().
_OLD_RULE = f"""\
- **A shared append-only data file can be DESTROYED by a peer's merge, and no gate will say so.**
  This is a different loss mode from a mis-scoped commit: the file is not over-staged, it is
  emptied. A peer running `git merge` took a shared intake buffer from **236 entries to 15** in one
  operation; the content survived only because that peer happened to stash first. Related measured
  losses in the same window: a truncating in-place write on a full disk permanently destroyed 20
  lines of *another* session's uncommitted edit, and a deliverable vanished when a merge moved HEAD
  while its backup was three edits stale. So for any shared `.ai/` data file you are about to drain,
  rewrite, or bulk-edit: **snapshot it to a durable path first, verify the copy with `cmp`, and
  confirm the snapshot location is not itself ignored** (`git check-ignore -v <path>` {_DASH} a backup
  directory that is gitignored cannot be committed alongside the change without `git add -f`, and an
  uncommitted backup is not a backup). Then re-read the file immediately before each edit.
- **Never `git checkout -b` raw in a contended tree.** A bare `checkout -b` inherits whatever HEAD
"""


def _old_shapes(text: str) -> list[str]:
    """The slugs of the old shapes found in `text`."""
    view = _view(text)
    return [
        slug
        for slug, (pattern, _why) in _OLD_SHAPES.items()
        if re.search(pattern, view, re.IGNORECASE)
    ]


def _problems(item: str) -> list[str]:
    """Every check over the text of one list item, as a flat list."""
    view = _view(item)
    return [
        *(f"missing: {name}" for name in _missing(view, _NOW)),
        *(f"missing (kept): {name}" for name in _missing(view, _KEPT)),
        *(f"still says: {slug}" for slug in _old_shapes(item)),
    ]


# --- the tests -----------------------------------------------------------------------------


def test_the_scan_surface_is_one_file_and_one_list_item() -> None:
    assert _SAFETY.is_file(), f"{_SAFETY.name} is not a file"
    text = _read(_SAFETY)
    assert text.strip(), f"{_SAFETY.name} is empty"
    lines = _item(text, _LEAD).split("\n")
    size = len(_view("\n".join(lines)))
    assert size >= _MIN_ITEM_CHARS, (
        f"the rule is {size} characters once folded, under {_MIN_ITEM_CHARS}; "
        "the cut stopped early"
    )
    assert all(line.startswith("  ") for line in lines[1:])
    following = text.split("\n")[text.split("\n").index(lines[0]) + len(lines)]
    assert following.startswith("- "), (
        f"the rule is followed by {following!r}, not by its sibling list item"
    )


def test_the_rule_names_the_commit_as_the_backup() -> None:
    gaps = _missing(_view(_rule()), _NOW)
    assert not gaps, f"the backup rule does not say: {gaps}"


def test_the_rule_keeps_its_evidence_reason_and_width() -> None:
    gaps = _missing(_view(_rule()), _KEPT)
    assert not gaps, f"the backup rule lost what it was written for: {gaps}"


@pytest.mark.parametrize("slug", list(_OLD_SHAPES))
def test_the_old_instruction_is_gone(slug: str) -> None:
    pattern, why = _OLD_SHAPES[slug]
    assert not re.search(pattern, _view(_rule()), re.IGNORECASE), (
        f"the backup rule still carries the old shape that {why}"
    )


# --- the instruments -----------------------------------------------------------------------


def _mutated(text: str, old: str, new: str) -> str:
    """`text` with `old` replaced by `new`; an `old` that is not there fails loudly."""
    assert old in text, f"the mutation target is not in the text: {old!r}"
    return text.replace(old, new, 1)


def _rewrap(item: str, width: int) -> str:
    """The list item re-flowed to `width`: its lead and two-space continuation indent kept."""
    folded = " ".join(item.split())
    assert folded.startswith("- "), "a list item starts with its marker"
    return "\n".join(
        textwrap.wrap(
            folded[2:],
            width=width,
            initial_indent="- ",
            subsequent_indent="  ",
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def test_every_check_sees_its_planted_positive() -> None:
    """A guard never shown to fail has not been shown to work."""
    # The old item is found by its lead and runs to its sibling, so the slicer sees real text.
    old_item = _item(_OLD_RULE, _LEAD)
    assert len(old_item.split("\n")) == 11, (
        "the planted item is the eleven lines it was"
    )
    assert "Never `git checkout -b`" not in old_item, (
        "the planted item swallowed its sibling"
    )

    # The old item holds every old shape and lacks every new fact, so each pattern can see its
    # target, and it still holds every kept fact, so those patterns can see theirs.
    assert _old_shapes(old_item) == list(_OLD_SHAPES)
    assert _missing(_view(old_item), _NOW) == list(_NOW)
    assert _missing(_view(old_item), _KEPT) == []
    assert _problems(old_item), "the old rule must not pass"

    # A lead that is gone, or is found twice, is a loud failure and never an empty match.
    with pytest.raises(AssertionError, match="0 lines start"):
        _item("some text\n- **Another rule.**\n", _LEAD)
    with pytest.raises(AssertionError, match="2 lines start"):
        _item(f"{_LEAD} one.\n{_LEAD} two.\n", _LEAD)

    # Near-misses that carry the new rule's words, or the old words in another sense, are not
    # old shapes.
    for near in (
        "A byte copy that the ignore file lists is ignored, so a broad `git add` cannot stage it.",
        "`git add -- <paths>` stages exactly the files named.",
        "Snapshot `git diff HEAD --stat` before and after a suite run.",
        "A copy at a durable location is not the backup.",
        "The restore point is its own commit, and the byte copy is never committed with the change.",
        "Do not rely on a copy that is not committed.",
    ):
        assert _old_shapes(near) == [], f"flagged a near-miss: {near!r}"


def test_each_regression_of_the_shipped_rule_is_caught() -> None:
    """One mutation round over the real rule: each regression adds the problem it should."""
    view = _view(_rule())
    assert _problems(view) == [], (
        "the shipped rule must pass before a mutation can mean anything"
    )
    cases = (
        (
            "commit it as it stands first, in its own commit",
            "snapshot it to a durable path first",
            (
                "missing: the file is committed as it stands, first, in its own commit",
                "still says: the-copy-is-the-backup",
            ),
        ),
        (
            "so work that exists only uncommitted has none, whatever copies sit beside it",
            "so keep a copy",
            (
                "missing: work that exists only uncommitted has no backup, whatever copies "
                "sit beside it",
            ),
        ),
        (
            "An uncommitted backup is not a backup",
            "A backup is a copy",
            ("missing (kept): the reason: an uncommitted backup is not a backup",),
        ),
        (
            "236 entries to 15",
            "many entries",
            (
                "missing (kept): evidence: a merge took a shared buffer from 236 entries "
                "to 15",
            ),
        ),
        (
            "is a convenience",
            "is the backup",
            ("missing: a local byte copy of the committed file is a convenience",),
        ),
        (
            "Then re-read the file immediately",
            "Confirm the snapshot location is not itself ignored. Then re-read the file immediately",
            ("still says: the-copy-must-not-be-ignored",),
        ),
    )
    for old, new, expected in cases:
        found = _problems(_mutated(view, old, new))
        for problem in expected:
            assert problem in found, (old, problem, found)


def test_the_shipped_rule_has_no_problem_in_any_check() -> None:
    problems = _problems(_rule())
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("width", _WIDTHS)
def test_a_rewrap_of_the_shipped_rule_passes_every_check(width: int) -> None:
    text = _read(_SAFETY)
    rule = _item(text, _LEAD)
    assert _problems(rule) == [], (
        "the shipped rule must pass before a re-wrap can mean anything"
    )
    rewrapped = _rewrap(rule, width)
    # A width narrower than the rule's widest line cannot be met by an unchanged rule, so this also
    # shows the re-wrap moved words. A width the rule is already filled to may change nothing.
    assert all(len(line) <= width for line in rewrapped.split("\n")), (
        f"a line of the re-wrap is wider than the {width} columns asked for"
    )
    # The re-flowed item is cut out of the re-flowed file by its lead, as a reader would find it.
    relocated = _item(text.replace(rule, rewrapped), _LEAD)
    assert relocated == rewrapped
    assert _problems(relocated) == []


def test_the_rewrap_widths_are_different_shapes() -> None:
    """The same words fall on fewer lines as the width grows, so the widths are not one layout.

    `_rewrap` folds the item first, so these counts depend on the words alone and not on how the
    shipped file happens to be wrapped."""
    rule = _rule()
    counts = [len(_rewrap(rule, width).split("\n")) for width in _WIDTHS]
    assert all(wider < narrower for narrower, wider in pairwise(counts)), (
        f"the line counts at widths {_WIDTHS} are {counts}, not strictly falling"
    )
