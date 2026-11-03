"""kit-setup says how its seeded ignore file meets a partial root rule and notes already tracked.

kit-setup seeds one self-ignoring `.gitignore` (a star, then an exception for itself) in each
local-only folder. Two things follow from the star that the Scaffold section did not say:

- A root rule that covers such a folder only partly, say `.ai/handoffs/*` with
  `!.ai/handoffs/README.md`, is overridden by the seeded star, because a folder's own file
  outranks the root file. A file is kept tracked with a negation in the folder's own file,
  placed below the star (within one file the last matching line decides), which a re-run of
  the script leaves alone and only `--force` resets (the folder file is a managed file, not a
  seed).
- A note committed before the seed stays tracked, because an ignore rule never untracks a
  file. `git rm --cached` is how the user stops tracking it, and the skill never runs it.

The two sentences are two bullets placed directly after the seeding paragraph. Each bullet is
cut by its lead (no bullet, or two, fails loudly) and held to its own phrases, so a phrase that
survives in the other bullet or in some other part of the file does not count. The first
bullet's way to act is ONE phrase (what to write, where in the file, in which file): the
folder's own file is named twice in that bullet, and a phrase pinned by its parts would pass
with the way to act deleted. The helpers are functions over a string, so
`test_the_cutters_see_planted_text_and_fail_loudly` and
`test_the_phrase_check_names_each_missing_phrase_and_ignores_a_rewrap` fire them at planted
text, the old passage and near misses among it, before their silence on the real file is trusted.

These tests hold the wording and run no git. `test_scaffold_local_only_folders.py` pins the seed
bytes, what git ignores under the seed and the managed-file rules the bullets rest on; the
behaviours the bullets add (a root negation overridden by the star, a negation below the star
re-including a file, a note tracked before the seed staying tracked until `git rm --cached`)
are not exercised by any test.
"""

import re
import textwrap
from pathlib import Path

import pytest

_SKILL_MD = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "kit-setup"
    / "SKILL.md"
)
_HEADING = re.compile(r"^(#{1,6})\s+\S")

# The last sentence of the seeding paragraph, which the two bullets follow directly, and the
# lead of each bullet. A bullet is cut by its lead, so a renamed or dropped bullet fails loudly
# and never matches an empty string.
_ANCHOR = "the project's root `.gitignore` stays exactly as it was."
_ROOT_RULE_LEAD = "- A root rule that covers such a folder only partly"
_COMMITTED_LEAD = "- Notes committed before the seed"

# What each bullet must say, matched after folding case and whitespace: the claim, why it holds,
# the way to act on it, and (for the first) what resets the folder's file. The way to act is one
# clause: what to write, where in the file (below the star, because within one file the last
# matching line decides), and in which file. The folder's own file is named again in the reason,
# so the clause is pinned whole and its parts are not.
_HOW_TO_CLAUSE = (
    "negation (`!README.md`) below the `*` in the folder's own `.gitignore`"
)
_ROOT_RULE_PHRASES = (
    "only partly",
    "overridden by the seeded `*`",
    "a folder's own `.gitignore` outranks the root one",
    _HOW_TO_CLAUSE,
    "`--force`",
)
_COMMITTED_PHRASES = (
    "stay tracked",
    "never untracks",
    "git rm --cached",
    "do not run it",
)


def _fold(text: str) -> str:
    """The text, lower-cased, with whitespace runs as one space, so a re-wrap changes no match."""
    return " ".join(text.split()).lower()


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced
    block is a comment of the code it holds, not a heading. A missing heading fails with the
    heading named, so a renamed section is a loud failure and never an empty match.
    """
    in_fence = False
    level = 0
    started = False
    found: list[str] = []
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        match = None if in_fence or fence else _HEADING.match(line)
        if not started:
            if match is not None and line.startswith(heading):
                started = True
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    if not started:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(found)


def _bullets(section: str) -> list[str]:
    """Every bullet of `section`: a line that starts with `- `, and the lines it runs on to.

    A bullet runs to the line before the next bullet, the next heading or the first blank
    line, so a bullet re-wrapped onto more lines is still one bullet.
    """
    found: list[list[str]] = []
    current: list[str] | None = None
    for line in section.split("\n"):
        if line.startswith("- "):
            current = [line]
            found.append(current)
        elif current is not None and line.strip() and not line.startswith("#"):
            current.append(line)
        else:
            current = None
    return ["\n".join(lines) for lines in found]


def _bullet(section: str, lead: str) -> str:
    """The one bullet of `section` that starts with `lead`, matched after folding whitespace.

    The lead is matched on the folded bullet and not on its first line, so a re-wrap that
    breaks the lead across two lines still finds it. No bullet, or two, fails with the lead
    named, so a renamed bullet is a loud failure and never an empty match.
    """
    wanted = _fold(lead)
    matches = [b for b in _bullets(section) if _fold(b).startswith(wanted)]
    if len(matches) != 1:
        raise AssertionError(
            f"the section has {len(matches)} bullets starting {lead!r}; expected exactly one"
        )
    return matches[0]


def _missing_from(passage: str, phrases: tuple[str, ...]) -> list[str]:
    """The phrases that `passage` does not carry; empty is a pass."""
    folded = _fold(passage)
    return [phrase for phrase in phrases if _fold(phrase) not in folded]


def _directly_after(section: str, anchor: str, lead: str) -> bool:
    """Does `lead` start the text that follows `anchor` in `section`, whitespace folded?

    An anchor the section does not hold fails loudly: the placement is judged against it.
    """
    _, found, tail = _fold(section).partition(_fold(anchor))
    if not found:
        raise AssertionError(f"the section does not hold the anchor {anchor!r}")
    return tail.lstrip().startswith(_fold(lead))


def _scaffold_section() -> str:
    text = _SKILL_MD.read_text(encoding="utf-8")
    return _section(text, "### Scaffold", "kit-setup SKILL.md")


def test_kit_setup_says_a_partial_root_rule_is_overridden_by_the_seeded_star() -> None:
    section = _scaffold_section()
    bullet = _bullet(section, _ROOT_RULE_LEAD)
    missing = _missing_from(bullet, _ROOT_RULE_PHRASES)
    assert not missing, (
        f"the partial-root-rule bullet does not carry {missing}: {_fold(bullet)!r}"
    )
    assert _directly_after(section, _ANCHOR, _ROOT_RULE_LEAD), (
        "the partial-root-rule bullet does not follow the local-only seeding paragraph"
    )


def test_kit_setup_says_notes_committed_before_the_seed_stay_tracked() -> None:
    section = _scaffold_section()
    bullet = _bullet(section, _COMMITTED_LEAD)
    missing = _missing_from(bullet, _COMMITTED_PHRASES)
    assert not missing, (
        f"the already-committed-notes bullet does not carry {missing}: {_fold(bullet)!r}"
    )
    first = _bullet(section, _ROOT_RULE_LEAD)
    assert _directly_after(section, first, _COMMITTED_LEAD), (
        "the already-committed-notes bullet does not follow the partial-root-rule bullet"
    )


# Planted text. The old paragraph is what the passage said before the two bullets: the seeding
# paragraph and nothing about a partial root rule or a note that is already tracked.
_OLD_PARAGRAPH = (
    "The `.ai/` scaffolding includes three local-only folders, `.ai/tmp/`,\n"
    "`.ai/handoffs/` and `.ai/retrospectives/`, each with one self-ignoring\n"
    "`.gitignore` (`*`, then `!.gitignore`): git ignores every note in them but\n"
    "not that file, unless the project's own ignore rules already cover the folder\n"
    "(harmless: the notes stay ignored). The script edits no other ignore file, so\n"
    "the project's root `.gitignore` stays exactly as it was."
)
_OTHER_PARAGRAPH = "Another paragraph, about something else."
# The first bullet as it read before it said where in the folder's file the negation goes. It
# holds every pinned phrase but the way to act, which is there without its position.
_OLD_ROOT_RULE_BULLET = (
    "- A root rule that covers such a folder only partly (say `.ai/handoffs/*` with\n"
    "  `!.ai/handoffs/README.md`) is overridden by the seeded `*`, because a folder's\n"
    "  own `.gitignore` outranks the root one: to keep a file there tracked, put its\n"
    "  negation (`!README.md`) in the folder's own `.gitignore`, which a re-run of\n"
    "  the script leaves alone and only `--force` resets to the two seeded lines."
)


def _planted(*blocks: str) -> str:
    return "\n".join(
        ["### Scaffold", "", *blocks, "", "### After the section", "after the section"]
    )


def test_the_cutters_see_planted_text_and_fail_loudly() -> None:
    wrapped_root = (
        f"{_ROOT_RULE_LEAD} (a rule\n  wrapped onto\n  several lines) is overridden."
    )
    committed = f"{_COMMITTED_LEAD} stay tracked."
    planted = _planted(
        _OLD_PARAGRAPH, "", wrapped_root, committed, "", _OTHER_PARAGRAPH
    )
    section = _section(planted, "### Scaffold", "planted")
    assert "after the section" not in section, "the section ran past its next heading"
    bullet = _bullet(section, _ROOT_RULE_LEAD)
    assert "several lines) is overridden." in bullet, (
        "a re-wrapped bullet was cut short"
    )
    assert "stay tracked" not in bullet, "the bullet swallowed the one after it"
    assert _OTHER_PARAGRAPH not in bullet, "the bullet ran on into the next paragraph"
    assert _bullet(section, _COMMITTED_LEAD) == committed
    # A re-wrap that breaks the lead itself across two lines still finds the bullet.
    split = _ROOT_RULE_LEAD.replace("such a", "such\n  a") + " (a rule) is overridden."
    assert split.count("\n") == 1
    assert (
        _bullet(_section(_planted(split), "### Scaffold", "planted"), _ROOT_RULE_LEAD)
        == split
    )
    # The old passage has no bullet to cut: loud, and the old text is in the section it was
    # looked for in, so the failure is the missing bullet and never a missing section.
    old_only = _section(
        _planted(_OLD_PARAGRAPH, "", _OTHER_PARAGRAPH), "### Scaffold", "planted"
    )
    assert _fold(_ANCHOR) in _fold(old_only)
    with pytest.raises(AssertionError, match="0 bullets"):
        _bullet(old_only, _ROOT_RULE_LEAD)
    with pytest.raises(AssertionError, match="0 bullets"):
        _bullet(old_only, _COMMITTED_LEAD)
    with pytest.raises(AssertionError, match="2 bullets"):
        _bullet(section + "\n" + wrapped_root, _ROOT_RULE_LEAD)
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### Nowhere", "planted")
    # A `#` line inside a fenced block is a comment of the code, not the next heading.
    fenced = _planted(_OLD_PARAGRAPH, "```bash", "# a comment", "```", wrapped_root)
    assert _bullet(_section(fenced, "### Scaffold", "planted"), _ROOT_RULE_LEAD)
    # Placement: the bullet must come straight after the seeding paragraph, not after some
    # other paragraph that happens to sit in the same section.
    assert _directly_after(section, _ANCHOR, _ROOT_RULE_LEAD)
    elsewhere = _section(
        _planted(_OLD_PARAGRAPH, "", _OTHER_PARAGRAPH, "", wrapped_root),
        "### Scaffold",
        "planted",
    )
    assert not _directly_after(elsewhere, _ANCHOR, _ROOT_RULE_LEAD)
    with pytest.raises(AssertionError, match="does not hold the anchor"):
        _directly_after(_OTHER_PARAGRAPH, _ANCHOR, _ROOT_RULE_LEAD)


def test_the_phrase_check_names_each_missing_phrase_and_ignores_a_rewrap() -> None:
    for lead, phrases in (
        (_ROOT_RULE_LEAD, _ROOT_RULE_PHRASES),
        (_COMMITTED_LEAD, _COMMITTED_PHRASES),
    ):
        complete = f"{lead} " + " ".join(phrases)
        assert _missing_from(complete, phrases) == []
        # Dropping any one phrase fails, and names exactly that phrase.
        for phrase in phrases:
            assert _missing_from(complete.replace(phrase, ""), phrases) == [phrase]
        # The old passage carries none of them, so it fails on every one.
        assert _missing_from(_OLD_PARAGRAPH, phrases) == list(phrases)
        # Re-wrapped at another width, with a run of spaces and a changed case: still a pass.
        rewrapped = textwrap.fill(
            complete.replace(" ", "   ", 1), width=23, break_on_hyphens=False
        ).upper()
        assert _missing_from(rewrapped, phrases) == []
    # The old first bullet is the known positive for the position: it names the folder's own file
    # but not where in it, and it fails on that one clause. So does a negation placed ABOVE the
    # star, where git ignores it. The near misses are built, not assumed.
    assert _missing_from(_OLD_ROOT_RULE_BULLET, _ROOT_RULE_PHRASES) == [_HOW_TO_CLAUSE]
    above = _OLD_ROOT_RULE_BULLET.replace(
        "(`!README.md`) in the folder's", "(`!README.md`) above the `*` in the folder's"
    )
    assert above != _OLD_ROOT_RULE_BULLET
    assert _missing_from(above, _ROOT_RULE_PHRASES) == [_HOW_TO_CLAUSE]
    # The shape that used to pass: the folder's own file is named in the reason as well, so
    # deleting it from the way to act left the other mention to hold the phrase up.
    complete_root = f"{_ROOT_RULE_LEAD} " + " ".join(_ROOT_RULE_PHRASES)
    no_location = complete_root.replace(
        _HOW_TO_CLAUSE, _HOW_TO_CLAUSE.replace(" in the folder's own `.gitignore`", "")
    )
    assert no_location != complete_root
    assert "folder's own `.gitignore`" in no_location
    assert _missing_from(no_location, _ROOT_RULE_PHRASES) == [_HOW_TO_CLAUSE]
    # A phrase that is only in the NEIGHBOURING bullet does not count for this one.
    root = f"{_ROOT_RULE_LEAD} " + " ".join(_ROOT_RULE_PHRASES)
    committed = f"{_COMMITTED_LEAD} " + " ".join(_COMMITTED_PHRASES)
    section = _section(_planted(root, committed), "### Scaffold", "planted")
    assert _missing_from(_bullet(section, _ROOT_RULE_LEAD), _COMMITTED_PHRASES) == list(
        _COMMITTED_PHRASES
    )
    assert _missing_from(_bullet(section, _COMMITTED_LEAD), _ROOT_RULE_PHRASES) == list(
        _ROOT_RULE_PHRASES
    )
