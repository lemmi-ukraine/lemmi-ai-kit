"""The skill-authoring pack and `pr-comment-resolver` say truthfully which kit skills a model may not invoke.

Six places in five files of the pack named `commit-message` and `branch-switch` as the kit's
two skills that carry `disable-model-invocation: true`. Only `commit-message` does:
`branch-switch` is model-invocable behind a pre-switch backup. `pr-comment-resolver` repeated
the claim and told a session it may not invoke `branch-switch`. Each place now names
`commit-message` as the kit's example, and `pr-comment-resolver` says a session may use
`branch-switch` after its backup, and on a shared checkout only with the operator's word. The
two lists of what the flag is for no longer call every branch mutation flag-worthy: they name
it only without a backup gate, which `branch-switch` has.

What each test asserts:

* `test_no_file_of_the_pack_names_the_two_skills_side_by_side` scans every markdown file under
  the pack and says how many it read. Two names with only a comma, a plus sign or "and" between
  them, in either order, are the claim; backticks and line breaks do not hide it.
* `test_each_place_states_the_kit_example` is one row per place: a file and the words the place
  holds now, so a claim deleted outright, advice and all, fails too.
* `test_the_flag_list_names_branch_mutation_only_without_a_backup_gate` is one row per list of
  what the flag is for.
* `test_pr_comment_resolver_says_a_session_may_use_branch_switch` reads that one file: neither
  old statement about `branch-switch` is in it (each is matched together with the skill's name,
  so a true sentence about another skill is not taken for it), and the paragraph that held them
  states the new rule.
* `test_the_shared_checkout_rule_beside_the_claim_stays` is NOT red on the old text: the two
  clauses it reads were there already. It guards a later edit from weakening them.
* The instrument tests fire the scan, the paragraph reader and the row check at planted text,
  so their silence on the real files means something: every planted shape is flagged, each near
  miss and each true sentence about another skill is not, a planted folder is read, the count of
  files read is a count of reads, and the two scan surfaces are stated in numbers and are
  disjoint.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PACK = _REPO / "plugins" / "skill-authoring"
_RESOLVER = (
    _REPO / "plugins" / "orchestration" / "skills" / "pr-comment-resolver" / "SKILL.md"
)

# The dash the skill text uses, spelled as a code point so this file stays ASCII.
_EM_DASH = chr(0x2014)

_COMMIT = "commit-message"
_SWITCH = "branch-switch"
# Only a comma, a plus sign or the word "and" between the two names, in either order.
_JOIN = r"\s*(?:,|\+|\band\b)\s*"
_SIDE_BY_SIDE = re.compile(rf"{_COMMIT}{_JOIN}{_SWITCH}|{_SWITCH}{_JOIN}{_COMMIT}")


def _plain(text: str) -> str:
    """The text with backticks removed and every run of whitespace, line breaks included, as
    one space, so a re-wrapped sentence reads the same as the one on a single line."""
    return " ".join(text.replace("`", "").split())


def _pairs(text: str) -> list[str]:
    """Every place `text` puts the two names side by side."""
    return [match.group(0) for match in _SIDE_BY_SIDE.finditer(_plain(text))]


def _surface(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def _walked(root: Path) -> list[Path]:
    """The same surface by a second route, so a walk that quit descending cannot pass alone."""
    return sorted(
        Path(folder) / name
        for folder, _subfolders, names in os.walk(root)
        for name in names
        if name.endswith(".md")
    )


def _scan(root: Path) -> tuple[int, list[str]]:
    """How many files were read, and every side-by-side pair found as `file: text`.

    The count goes up after a file is read, so it measures the scan and not the list the
    scan was given: a scan that stops early reports the files it reached.
    """
    read = 0
    hits: list[str] = []
    for path in _surface(root):
        text = path.read_text(encoding="utf-8")
        read += 1
        hits += [
            f"{path.relative_to(root).as_posix()}: {hit!r}" for hit in _pairs(text)
        ]
    return read, hits


@dataclass(frozen=True)
class _Place:
    """One place that held the claim: its file under the pack, and the words it holds now."""

    key: str
    file: str
    carries: str


_PLACES: tuple[_Place, ...] = (
    _Place(
        "creator-decision-tree",
        "skills/skill-creator/SKILL.md",
        "(kit example: commit-message. Side effect: the description leaves context",
    ),
    _Place(
        "creator-patterns-table",
        "skills/skill-creator/references/skill-patterns.md",
        "timing-critical action | true | true (default) | commit-message, deploy |",
    ),
    _Place(
        "creator-patterns-policy",
        "skills/skill-creator/references/skill-patterns.md",
        f"are user-only {_EM_DASH} in the kit, for example commit-message. "
        "Repo-file-writing skills and workflows stay model-invocable",
    ),
    _Place(
        "reviewer-decision-tree",
        "skills/skill-reviewer/SKILL.md",
        "(kit example: commit-message. The flag also removes the description from context",
    ),
    _Place(
        "reviewer-checklist",
        "skills/skill-reviewer/references/review-checklist.md",
        "(kit example: commit-message); repo-internal writers and workflows stay "
        "model-invocable",
    ),
    _Place(
        "reviewer-taxonomy",
        "skills/skill-reviewer/references/skill-taxonomy.md",
        "(kit example: commit-message); repo-internal writers stay model-invocable",
    ),
)

# The two lists of what the flag is for. `branch-switch` mutates branches and is
# model-invocable behind a backup gate, so a list that called every branch mutation
# flag-worthy would send a reviewer to recommend the flag for it.
_BRANCH_MUTATION_OLD = "(commit, push, deploy, branch mutation, external sends)"
_FLAG_LISTS: tuple[_Place, ...] = (
    _Place(
        "creator-flag-list",
        "skills/skill-creator/SKILL.md",
        "(commit, push, deploy, branch mutation without a backup gate, external sends)",
    ),
    _Place(
        "reviewer-flag-list",
        "skills/skill-reviewer/SKILL.md",
        "(commit, push, deploy, branch mutation without a backup gate, external sends)",
    ),
)

# The paragraph of `pr-comment-resolver` that held the claim is found by how it starts: the
# words its lead sentence had before the rewording and has after it.
_RESOLVER_LEAD_IN = "**Switching to the owning branch"
# The old claim, as the two statements it made about `branch-switch`. Each pattern holds the
# skill's name, so a true sentence about ANOTHER skill that uses the same words is not the
# claim, and no sentence boundary has to be found: a bullet with no full stop cannot join one
# statement to the next. The old text said "carries"; "has" is the same statement.
_CARRIES_THE_FLAG = "branch-switch carries the flag"
_MAY_NOT_INVOKE = "a session may not invoke branch-switch"
_OLD_CLAIMS: dict[str, re.Pattern[str]] = {
    _CARRIES_THE_FLAG: re.compile(
        r"branch-switch (?:carries|has) disable-model-invocation: true"
    ),
    _MAY_NOT_INVOKE: re.compile(
        r"may not invoke \S*branch-switch|branch-switch may not be invoked"
    ),
}
# What the paragraph states now.
_NEW_CLAUSES = (
    "Switching to the owning branch on a shared checkout is an operator action.",
    "A session may use /lemmi-ai-kit-core:branch-switch after its pre-switch backup",
    "and on a shared checkout only with the operator's word.",
)
# What the paragraph already stated and must keep stating.
_KEPT_CLAUSES = (
    "Ask the operator to run /lemmi-ai-kit-core:branch-switch <owning-branch> and wait.",
    "this checkout is shared.",
)

_OLD_PARAGRAPH = (
    "**Switching to the owning branch is an operator action.** "
    "`/lemmi-ai-kit-core:branch-switch` carries\n"
    f"`disable-model-invocation: true` {_EM_DASH} a session may not invoke it. Ask the "
    "operator to run\n"
    "`/lemmi-ai-kit-core:branch-switch <owning-branch>` and wait. The workflow doc's bare "
    "`git checkout` form assumes a\n"
    "clean single-writer tree; this checkout is shared.\n"
)
_NEW_PARAGRAPH = (
    "**Switching to the owning branch on a shared checkout is an operator action.** "
    "A session may use\n"
    "`/lemmi-ai-kit-core:branch-switch` after its pre-switch backup, and on a shared "
    "checkout only with the operator's\n"
    "word. Ask the operator to run `/lemmi-ai-kit-core:branch-switch <owning-branch>` "
    "and wait. The workflow doc's bare\n"
    "`git checkout` form assumes a clean single-writer tree; this checkout is shared.\n"
)

# Every shape of the claim the check is asked to see: a comma, a plus sign and "and", each in
# both orders, the way the six places wrote them.
_PLANTED: dict[str, str] = {
    "comma-commit-first": "(project fleet: commit-message, branch-switch); repo-internal",
    "comma-switch-first": "(project fleet: branch-switch, commit-message); repo-internal",
    "plus-commit-first": "(fleet: only commit-message + branch-switch. Side effect:",
    "plus-switch-first": "(fleet: only branch-switch + commit-message. Side effect:",
    "and-commit-first": "in this pack, `commit-message` and `branch-switch`. Repo-file",
    "and-switch-first": "in this pack, `branch-switch` and `commit-message`. Repo-file",
}

# Text that sits close to the claim and is not it.
_NEAR_MISSES: dict[str, str] = {
    "two-sentences": "`commit-message` makes a commit. `branch-switch` moves between branches.",
    "a-period-between": "the user-only skill is commit-message. branch-switch is not one.",
    "the-first-name-in-a-list": "commit-message, task-learnings and post-task-review",
    "the-second-name-in-a-list": "branch-switch, a backup script and a refusal table",
    "the-new-wording": "(kit example: commit-message); repo-internal writers stay model-invocable",
}

# True text that holds the words of an old statement and is not the claim: sentences about
# ANOTHER skill, the claim denied of `branch-switch`, and a sentence that follows a bullet
# naming `branch-switch` that has no full stop (the last lines of the real file are bullets).
_TRUE_SENTENCES: dict[str, str] = {
    "another-skill-may-not-be-invoked": "A session may not invoke commit-message.",
    "another-skill-carries-the-flag": (
        "Only commit-message carries disable-model-invocation: true."
    ),
    "the-claim-denied": "`branch-switch` does not carry `disable-model-invocation: true`.",
    "after-a-bullet-with-no-full-stop": (
        f"- `/lemmi-ai-kit-core:branch-switch` {_EM_DASH} the only sanctioned way to move\n"
        "between branches\n"
        "Only commit-message carries disable-model-invocation: true."
    ),
}

# The size of each table above, and of the scan surface, stated so a dropped row or file is a
# failure and not a silent shrink. The surface is the pack's markdown: its README, five
# SKILL.md files and three references.
_PLACE_COUNT = 6
_FLAG_LIST_COUNT = 2
_PLANTED_COUNT = 6
_NEAR_MISS_COUNT = 5
_TRUE_SENTENCE_COUNT = 4
_SURFACE_COUNT = 9


def _read(relative: str) -> str:
    return (_PACK / relative).read_text(encoding="utf-8")


def _carries(place: _Place, text: str) -> bool:
    return _plain(place.carries) in _plain(text)


def _paragraph(text: str, lead_in: str) -> str:
    """The one paragraph (a run of non-blank lines) of `text` that starts with `lead_in`.

    No paragraph, or more than one, fails with the lead-in and the count named, so a
    reworded lead-in is a loud failure and never an empty match.
    """
    start = _plain(lead_in)
    found = [
        block for block in re.split(r"\n\s*\n", text) if _plain(block).startswith(start)
    ]
    if len(found) != 1:
        raise AssertionError(
            f"{len(found)} paragraphs start with {lead_in!r}, expected 1"
        )
    return found[0]


def _resolver_problems(text: str) -> list[str]:
    """What is wrong with the `pr-comment-resolver` text: an old statement about `branch-switch`
    anywhere in it, and each clause of the new rule that its paragraph lacks."""
    plain = _plain(text)
    paragraph = _plain(_paragraph(text, _RESOLVER_LEAD_IN))
    problems = [
        f"still says {claim!r}"
        for claim, pattern in _OLD_CLAIMS.items()
        if pattern.search(plain)
    ]
    problems += [
        f"the paragraph does not say {clause!r}"
        for clause in _NEW_CLAUSES
        if _plain(clause) not in paragraph
    ]
    return problems


# --- the change ---------------------------------------------------------------------------


def test_no_file_of_the_pack_names_the_two_skills_side_by_side() -> None:
    scanned, hits = _scan(_PACK)
    assert not hits, (
        f"{len(hits)} places say the two skills are alike, in {scanned} files scanned:\n"
        + "\n".join(hits)
    )


@pytest.mark.parametrize("place", _PLACES, ids=[place.key for place in _PLACES])
def test_each_place_states_the_kit_example(place: _Place) -> None:
    assert _carries(place, _read(place.file)), (
        f"{place.file} does not carry {place.carries!r}"
    )


@pytest.mark.parametrize("place", _FLAG_LISTS, ids=[place.key for place in _FLAG_LISTS])
def test_the_flag_list_names_branch_mutation_only_without_a_backup_gate(
    place: _Place,
) -> None:
    text = _read(place.file)
    assert _carries(place, text), f"{place.file} does not carry {place.carries!r}"
    assert _plain(_BRANCH_MUTATION_OLD) not in _plain(text), (
        f"{place.file} still calls every branch mutation flag-worthy"
    )


def test_pr_comment_resolver_says_a_session_may_use_branch_switch() -> None:
    problems = _resolver_problems(_RESOLVER.read_text(encoding="utf-8"))
    assert not problems, "pr-comment-resolver: " + "; ".join(problems)


# This row is TRUE ON THE OLD TEXT TOO: the paragraph already told a session to ask the
# operator and wait, on a checkout it called shared. It shows no change and is not red; it
# guards the new sentence from being written over them.
def test_the_shared_checkout_rule_beside_the_claim_stays() -> None:
    paragraph = _plain(
        _paragraph(_RESOLVER.read_text(encoding="utf-8"), _RESOLVER_LEAD_IN)
    )
    missing = [clause for clause in _KEPT_CLAUSES if _plain(clause) not in paragraph]
    assert not missing, f"the paragraph no longer says {missing}"


# --- the instruments ----------------------------------------------------------------------


@pytest.mark.parametrize("shape", list(_PLANTED))
def test_the_scan_sees_each_planted_shape(shape: str) -> None:
    sample = _PLANTED[shape]
    assert _pairs(sample), f"the scan missed {shape}: {sample!r}"
    # Backticks around the names and a line break at every space must not hide it.
    marked = sample.replace(_COMMIT, f"`{_COMMIT}`").replace(_SWITCH, f"`{_SWITCH}`")
    assert _pairs(marked), f"backticks hid {shape}: {marked!r}"
    broken = re.sub(r" +", "\n    ", sample)
    assert broken != sample
    assert _pairs(broken), f"a line break hid {shape}: {broken!r}"


@pytest.mark.parametrize("miss", list(_NEAR_MISSES))
def test_the_scan_is_silent_on_near_misses(miss: str) -> None:
    sample = _NEAR_MISSES[miss]
    assert _pairs(sample) == [], f"the scan flagged {miss}: {sample!r}"


def test_the_scan_reads_a_planted_folder_and_only_its_markdown(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()
    claim = f"A rule. {_PLANTED['plus-commit-first']}\n"
    # The clean file sorts first and the claim last, so a scan that stops after one file
    # misses it, and so does one that reads only the first.
    (tmp_path / "skills" / "clean.md").write_text(
        f"A rule. {_NEAR_MISSES['two-sentences']}\n", encoding="utf-8"
    )
    (tmp_path / "skills" / "the-claim.md").write_text(claim, encoding="utf-8")
    (tmp_path / "notes.txt").write_text(claim, encoding="utf-8")
    scanned, hits = _scan(tmp_path)
    assert scanned == 2, f"expected the two markdown files, the scan read {scanned}"
    assert len(hits) == 1 and hits[0].startswith("skills/the-claim.md: "), hits


def test_the_resolver_check_fails_on_the_old_paragraph_and_passes_the_new_one() -> None:
    old = _resolver_problems(f"Intro.\n\n{_OLD_PARAGRAPH}\nOutro.\n")
    # The old paragraph made the first statement outright and the second as "it", so the check
    # reads the first; every clause of the new rule is missing from it.
    missing = [f"the paragraph does not say {clause!r}" for clause in _NEW_CLAUSES]
    assert old == [f"still says {_CARRIES_THE_FLAG!r}", *missing], old
    assert _resolver_problems(f"Intro.\n\n{_NEW_PARAGRAPH}\nOutro.\n") == []
    # Either statement in another place of the file is still the claim, whichever comes first,
    # the skill's name or the words of the statement.
    carries = f"Elsewhere, `{_SWITCH}` carries `disable-model-invocation: true`."
    assert _resolver_problems(f"{carries}\n\n{_NEW_PARAGRAPH}") == [
        f"still says {_CARRIES_THE_FLAG!r}"
    ]
    for sentence in (
        f"A session may not invoke `{_SWITCH}`.",
        f"A session may not invoke `/lemmi-ai-kit-core:{_SWITCH}`.",
        f"`{_SWITCH}` may not be invoked by a session.",
    ):
        assert _resolver_problems(f"{sentence}\n\n{_NEW_PARAGRAPH}") == [
            f"still says {_MAY_NOT_INVOKE!r}"
        ], sentence


@pytest.mark.parametrize("sentence", list(_TRUE_SENTENCES))
def test_the_resolver_check_is_silent_on_a_true_sentence(sentence: str) -> None:
    text = f"Intro.\n\n{_NEW_PARAGRAPH}\n{_TRUE_SENTENCES[sentence]}\n"
    assert _resolver_problems(text) == [], (
        f"the check flagged {sentence}: {_TRUE_SENTENCES[sentence]!r}"
    )


def test_the_paragraph_reader_fails_loudly() -> None:
    text = f"Intro.\n\n{_NEW_PARAGRAPH}\nOutro.\n"
    assert "operator's" in _paragraph(text, _RESOLVER_LEAD_IN)
    assert "Outro." not in _paragraph(text, _RESOLVER_LEAD_IN)
    with pytest.raises(AssertionError, match="0 paragraphs start with"):
        _paragraph("Intro.\n\nOutro.\n", _RESOLVER_LEAD_IN)
    with pytest.raises(AssertionError, match="2 paragraphs start with"):
        _paragraph(f"{_NEW_PARAGRAPH}\n{_OLD_PARAGRAPH}", _RESOLVER_LEAD_IN)
    # A re-wrapped lead-in is still found.
    wrapped = _NEW_PARAGRAPH.replace("owning branch", "owning\nbranch")
    assert wrapped != _NEW_PARAGRAPH
    assert _paragraph(wrapped, _RESOLVER_LEAD_IN)


def test_a_row_sees_missing_words_and_a_re_wrap() -> None:
    place = _PLACES[0]
    held = "        (kit example: commit-message. Side effect: the description\n"
    held += "        leaves context"
    assert _carries(place, held)
    old = "(fleet: only commit-message + branch-switch. Side effect: the description leaves"
    assert not _carries(place, old)
    assert not _carries(place, "")


def test_the_scan_surfaces_are_stated_in_numbers_and_do_not_overlap() -> None:
    files = _surface(_PACK)
    walked = _walked(_PACK)
    assert files == walked, f"two walks of the pack disagree: {files} against {walked}"
    assert len(files) == _SURFACE_COUNT, (
        f"the pack holds {len(files)} markdown files, not the {_SURFACE_COUNT} stated"
    )
    relative = {path.relative_to(_PACK).as_posix() for path in files}
    named = {place.file for place in (*_PLACES, *_FLAG_LISTS)}
    assert named <= relative, (
        f"rows name files the scan misses: {sorted(named - relative)}"
    )
    empty = [name for name in sorted(relative) if not _read(name).strip()]
    assert not empty, f"files with no text, so the scan saw nothing in them: {empty}"
    scanned, _ = _scan(_PACK)
    assert scanned == _SURFACE_COUNT, (
        f"the scan read {scanned} of the {_SURFACE_COUNT} files of the pack"
    )
    # The second surface is the one file of the resolver; it is read by its own check only,
    # so it must not also sit inside the first.
    assert _RESOLVER.is_file()
    assert _RESOLVER not in files
    assert not _RESOLVER.is_relative_to(_PACK)


def test_the_tables_keep_their_stated_size() -> None:
    sizes = {
        "places": (len(_PLACES), _PLACE_COUNT),
        "flag lists": (len(_FLAG_LISTS), _FLAG_LIST_COUNT),
        "planted shapes": (len(_PLANTED), _PLANTED_COUNT),
        "near misses": (len(_NEAR_MISSES), _NEAR_MISS_COUNT),
        "true sentences": (len(_TRUE_SENTENCES), _TRUE_SENTENCE_COUNT),
    }
    wrong = [
        f"{table}: {found}, expected {expected}"
        for table, (found, expected) in sizes.items()
        if found != expected
    ]
    assert not wrong, "a table of the guard changed size: " + "; ".join(wrong)
