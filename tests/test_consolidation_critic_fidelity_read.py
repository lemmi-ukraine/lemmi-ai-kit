"""The consolidation critic reads each promoted paragraph beside the entry it came from.

`consolidation-critic` checked where a drained entry landed (C1), what a promoted passage cites
(C2) and whether the hedge of its source entry survived (C6). No check read the rewritten
paragraph beside that entry, so a paraphrase that changed the claim passed every check. C6 now
carries a fidelity read: each promoted paragraph is read beside its source entry and every place
it changes the claim is listed (a narrative inverted, two techniques fused, a sentence addressed
to the promoter left in committed text, a dropped qualifier such as "not run" or "only"); a
promotion passes only when the read lists none; a fresh reader carries the read, not the author
of the promotions, who spawns and briefs it as `post-task-review` describes one for a fix round;
the read replaces none of C1 to C8. The Output Format block gains a "Fidelity read" summary line.

The read sits inside C6, so "Run all eight" stays true and the eight check headings stand as they
were: both are asserted. "source entry" stood in the file before the change, so no check rests on
it alone. The pointer to the fix-round text is plain text, not a markdown link, and the section
number it names must resolve to the fresh-reader section of `post-task-review`'s fix-rounds
reference. C6 names the fresh reader before it describes the read and orders no one to read or
list, because a literal reader given the read in the imperative does it itself; that order rule
rests on two of the phrases below, so it is a test of its own and not one of the checks.

THE SURFACE, in numbers the tests assert: 2 places in 1 file (the C6 section and the Output Format
section of the critic's SKILL.md) and 7 checks: 6 over 13 phrases in C6 and 1 over the summary
lines of the Output Format template. Every check is fired at the text its place carried before
(`_OLD_C6` and `_OLD_OUTPUT_FORMAT`, unedited excerpts), each C6 phrase is removed from the real
text one at a time and must be the only thing reported, and the summary-line check is fired at
near-misses (the line above or below the template fence, a table row, the line twice, an old line
dropped). A heading that is not found fails loudly, with the heading named.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"
_CRITIC_MD = _SKILLS / "consolidation-critic" / "SKILL.md"
_FIX_ROUNDS = _SKILLS / "post-task-review" / "references" / "fix-rounds.md"

_HEADING = re.compile(r"^(#{1,6})\s")
_SUMMARY_LINE = re.compile(r"^\*\*([^*]+):\*\*")
_POINTER = re.compile(r"section (\d+) of its fix-rounds reference")
# A sentence or paragraph that opens on the read's own verbs orders the skill's reader, who wrote
# the promotions, to do the read itself.
_ORDER_TO_READ = re.compile(r"(?:^|[.!?:;] )(?:Read|List) (?:each|every)\b")

_DASH = chr(0x2014)
_DOT = chr(0x00B7)
_ARROW = chr(0x2192)
_SUBSCRIPT_ZERO = chr(0x2080)

_THE_READ = "read each promoted paragraph beside its source entry"
_READER_FIRST = "A fresh reader carries the read"


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same.
    A missing file is its own loud failure, never an empty match."""
    if not path.is_file():
        raise AssertionError(f"{path.name} does not exist")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return " ".join(re.sub(r"[*`]", "", text).split())


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or a
    higher level. A `#` line inside a fenced block is not a heading (C1 prints shell comments, and
    the Output Format template holds headings of its own). A missing heading fails loudly."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = _is_fence(line)
        found = None if in_fence or fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
        elif found is not None and len(found[1]) <= level:
            break
        else:
            body.append(line)
        if fence:
            in_fence = not in_fence
    if not body:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


def _level_3_headings(text: str) -> list[str]:
    """The `### ` heading lines of the text, fenced blocks left out."""
    headings: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _is_fence(line):
            in_fence = not in_fence
        elif not in_fence and line.startswith("### "):
            headings.append(line)
    return headings


def _summary_labels(region: str) -> list[str]:
    """The labels of the bold summary lines inside the region's `markdown` template fence."""
    labels: list[str] = []
    inside = False
    for line in region.split("\n"):
        if _is_fence(line):
            if inside:
                break
            inside = line.lstrip()[3:].strip().lower() == "markdown"
            continue
        if inside and (found := _SUMMARY_LINE.match(line)) is not None:
            labels.append(found[1])
    return labels


def _orders_its_reader_to_read(region: str) -> bool:
    """Whether a sentence or a paragraph of the region opens on the read's own verbs. Paragraphs
    are folded one at a time, so a paragraph that opens on the order after a heading is seen."""
    return any(
        _ORDER_TO_READ.search(_plain(paragraph)) is not None
        for paragraph in region.split("\n\n")
    )


def _names_the_reader_first(region: str) -> bool:
    """The fresh reader is named before the read is described, and no sentence orders the skill's
    reader to read or list."""
    folded = _plain(region).lower()
    reader = folded.find(_READER_FIRST.lower())
    read = folded.find(_THE_READ)
    return 0 <= reader < read and not _orders_its_reader_to_read(region)


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


class _Place(NamedTuple):
    name: str
    path: Path
    checks: tuple[_Check, ...]
    locate: Callable[[str, str], str]
    old: str


def _says(*phrases: str) -> Callable[[str], bool]:
    return lambda region: all(p in _plain(region) for p in phrases)


# Each C6 check, with the phrases it needs. Every phrase had 0 hits in the file before the read.
_C6_PHRASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "C6 names a fidelity read of each promoted paragraph beside its source entry",
        (
            "Fidelity read",
            _THE_READ,
            "list every place it changes the claim",
        ),
    ),
    (
        "C6 lists the four ways a paraphrase changes a claim",
        (
            "a narrative inverted",
            "two techniques fused",
            "a sentence addressed to the promoter",
            'a dropped qualifier such as "not run" or "only"',
        ),
    ),
    (
        "C6 passes a promotion only when the read lists none",
        ("A promotion passes only when the read lists none",),
    ),
    (
        "C6 gives the read to a fresh reader the promoter spawns",
        (_READER_FIRST, "You spawn it"),
    ),
    (
        "C6 names the fix-round text by skill and section",
        (
            "as post-task-review describes one for a fix round",
            "section 2 of its fix-rounds reference",
        ),
    ),
    (
        "C6 keeps C1 to C8 whole",
        ("The read does not replace C1 to C8",),
    ),
)
_C6_CHECKS: tuple[_Check, ...] = tuple(
    _Check(label, _says(*phrases)) for label, phrases in _C6_PHRASES
)

_OLD_LABELS = ("Landing audit", "Claim verification", "Always-loaded delta")
_FIDELITY_LABEL = "Fidelity read"


def _has_the_fidelity_line(region: str) -> bool:
    labels = _summary_labels(region)
    return all(labels.count(label) == 1 for label in (*_OLD_LABELS, _FIDELITY_LABEL))


_OUTPUT_CHECK = _Check(
    "the Output Format template has a Fidelity read summary line beside the three it had",
    _has_the_fidelity_line,
)

_CHECK_HEADINGS = (
    f"### C1 {_DASH} Landing audit (mechanical, non-negotiable)",
    f"### C2 {_DASH} Claim verification against the CURRENT branch",
    f"### C3 {_DASH} Altitude and cost",
    f"### C4 {_DASH} Duplication sweep",
    f"### C5 {_DASH} Self-contradiction sweep",
    f"### C6 {_DASH} Epistemic audit",
    f"### C7 {_DASH} Enforcement check",
    f"### C8 {_DASH} Re-run every gate",
)

_OLD_C6 = f"""### C6 {_DASH} Epistemic audit

Confidence must survive the promotion. A learnings entry that hedged ("forum-reported", "affiliation
not verifiable", "observed once") must not become a flat assertion in an auto-loaded skill.

Check every promoted claim for: source quality, whether *this project* measured it, and whether the
hedge in the source entry survived. Where the evidence is thin, state it as a hypothesis and name
the experiment that would settle it.

> **Caught:** an undocumented provider default sourced from a single forum post whose author's
> affiliation was explicitly unverifiable, promoted as fact into an auto-loaded skill {_DASH} in a project
> whose own rules forbid trusting unofficial sources for model internals.
"""

_OLD_OUTPUT_FORMAT = f"""## Output Format

```markdown
## Consolidation Review

**Landing audit:** N entries scanned {_DOT} M candidate losses {_DOT} K adjudicated as real {_ARROW} recovered
**Claim verification:** N claims checked {_DOT} M false {_ARROW} corrected
**Always-loaded delta:** +N chars (~T tokens), was +N{_SUBSCRIPT_ZERO} before this review

### Blockers (N)
| # | Finding | Where | Resolution |

### Major (N)
| # | Finding | Where | Resolution |

### Gates
| Gate | Result |
```

Report corrections **plainly and specifically** {_DASH} a review that reports "looks good" after editing
nine files has not been done. State what was wrong, not how thorough the review was.
"""


def _c6(text: str, where: str) -> str:
    return _section(text, "### C6", where)


def _output_format(text: str, where: str) -> str:
    return _section(text, "## Output Format", where)


_PLACES: tuple[_Place, ...] = (
    _Place("critic-c6", _CRITIC_MD, _C6_CHECKS, _c6, _OLD_C6),
    _Place(
        "critic-output-format",
        _CRITIC_MD,
        (_OUTPUT_CHECK,),
        _output_format,
        _OLD_OUTPUT_FORMAT,
    ),
)


def _gaps(checks: tuple[_Check, ...], region: str) -> list[str]:
    return [c.label for c in checks if not c.holds(region)]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


_PHRASE_CASES = [
    (label, phrase) for label, phrases in _C6_PHRASES for phrase in phrases
]


def test_the_surface_is_stated_in_numbers() -> None:
    """2 places in 1 file, and 7 checks: 6 over 13 phrases in C6, 1 in the Output Format."""
    assert len(_PLACES) == 2, f"{len(_PLACES)} places, not the 2 stated"
    assert {p.path for p in _PLACES} == {_CRITIC_MD}, (
        "the places are not all in SKILL.md"
    )
    checks = [c for p in _PLACES for c in p.checks]
    assert len(checks) == 7, f"{len(checks)} checks, not the 7 stated"
    assert len(_PHRASE_CASES) == 13, (
        f"{len(_PHRASE_CASES)} C6 phrases, not the 13 stated"
    )
    assert len({c.label for c in checks}) == len(checks), "two checks share a label"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_carries_its_rule(place: _Place) -> None:
    region = place.locate(_read(place.path), place.path.name)
    gaps = _gaps(place.checks, region)
    assert not gaps, f"{place.path.name} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The old C6 has no fidelity read and the old template three summary lines, so every check
    must say so."""
    reported = _gaps(place.checks, place.locate(place.old, f"{place.name} excerpt"))
    assert reported == [c.label for c in place.checks], (
        f"{place.name}: blind to the old text: "
        f"{[c.label for c in place.checks if c.label not in reported]}"
    )


@pytest.mark.parametrize(
    ("label", "phrase"), _PHRASE_CASES, ids=[_slug(p) for _, p in _PHRASE_CASES]
)
def test_each_c6_phrase_removed_alone_is_the_only_gap(label: str, phrase: str) -> None:
    """A near-miss of the real text: one phrase gone, the rest of the read intact. Only the check
    that needs the phrase may report it, so no check leans on another's words."""
    real = _plain(_c6(_read(_CRITIC_MD), "SKILL.md"))
    assert phrase in real, f"C6 does not say {phrase!r}"
    assert _gaps(_C6_CHECKS, real.replace(phrase, " ")) == [label]


def test_a_read_left_to_the_promoter_alone_is_reported() -> None:
    """Planted: the read is done by the promoter alone, everything else as written."""
    real = _plain(_c6(_read(_CRITIC_MD), "SKILL.md"))
    planted = real.replace(_READER_FIRST, "The promoter alone does the read")
    assert planted != real, "C6 has no fresh-reader sentence to replace"
    assert _gaps(_C6_CHECKS, planted) == [
        "C6 gives the read to a fresh reader the promoter spawns"
    ]


def test_c6_names_the_fresh_reader_before_the_read_it_carries() -> None:
    """Who carries the read is said before the read is described, and C6 orders no one to read or
    list: a literal reader given the read in the imperative does it itself and treats the fresh
    reader as optional. Fired at the read described with no fresh reader named, the read described
    first, an order to read and an order to list after the reader, an order after each of the five
    stops the order rule names (`.`, `!`, `?`, `:` and `;`), a paragraph that opens on the order
    with no stop before it, and the old C6; the reader named first and briefed with the read
    holds."""
    c6 = _c6(_read(_CRITIC_MD), "SKILL.md")
    assert _names_the_reader_first(c6), (
        "C6 describes the read before it names the fresh reader, or orders its reader to do it"
    )
    assert _names_the_reader_first(
        f"{_READER_FIRST}, not you. You spawn it and brief it to {_THE_READ}."
    )
    order = _THE_READ.capitalize()
    planted = (
        # No fresh reader is named. A reader that is not found sits at -1, before the read, so the
        # position test alone lets this through: only the test that it was found rejects it.
        f"Brief a reader to {_THE_READ}.",
        f"Brief a reader to {_THE_READ}. {_READER_FIRST}.",
        f"{_READER_FIRST}. {order}.",
        f"{_READER_FIRST}; brief it to {_THE_READ}. List every place it changes the claim.",
        f"{_READER_FIRST}, briefed to {_THE_READ}\n\n{order} first.",
        # The reader named first, then an order after each stop of the order rule, one stop a text.
        *(
            f"{_READER_FIRST}, briefed to {_THE_READ}{stop} List every place it changes the claim."
            for stop in ".!?:;"
        ),
        _OLD_C6,
    )
    for text in planted:
        assert not _names_the_reader_first(text), text


def test_c6_points_at_the_fresh_reader_section_in_plain_text() -> None:
    """C6 names the fix-round text without a markdown link, and the section it names is the
    fresh-reader section of `post-task-review`'s fix-rounds reference: a renumbered reference turns
    this red instead of leaving the critic pointing at another rule."""
    c6 = _c6(_read(_CRITIC_MD), "SKILL.md")
    assert "](" not in c6, "C6 links to the fix-round text instead of naming it"
    named = _POINTER.search(_plain(c6))
    assert named is not None, (
        "C6 names no section of post-task-review's fix-rounds reference"
    )
    target = _section(_read(_FIX_ROUNDS), f"## {named[1]}.", "fix-rounds.md")
    heading = target.split("\n", 1)[0]
    assert "fresh reader" in heading.lower(), (
        f"section {named[1]} of fix-rounds.md is {heading!r}, not the fresh reader"
    )
    assert "planted false claim" in _plain(target)


def test_the_read_sits_inside_c6_and_the_checks_stay_eight() -> None:
    """True before the read was added and after: it is part of C6, not a ninth check, so the count
    the section states and the eight check headings stand as they were."""
    checks = _section(_read(_CRITIC_MD), "## The Checks", "SKILL.md")
    assert "Run all eight." in _plain(checks)
    assert tuple(_level_3_headings(checks)) == _CHECK_HEADINGS


def test_the_heading_list_sees_a_ninth_check_and_skips_fenced_lines() -> None:
    eight = "\n\n".join(_CHECK_HEADINGS)
    assert tuple(_level_3_headings(eight)) == _CHECK_HEADINGS
    ninth = f"{eight}\n\n### C9 {_DASH} Fidelity read\n"
    assert len(_level_3_headings(ninth)) == 9
    fenced = f"{eight}\n\n```markdown\n### Blockers (N)\n```\n"
    assert tuple(_level_3_headings(fenced)) == _CHECK_HEADINGS


def test_the_fidelity_line_check_needs_a_summary_line_in_the_template() -> None:
    """Fired at near-misses of the old template: the line above the fence and below it, the words
    as a table row, the line twice, and the new line with an old one dropped. Only the line in the
    template, once, beside the three it had, holds."""
    line = f"**Fidelity read:** N paragraphs {_DOT} M changed claims {_ARROW} corrected"
    anchor = "before this review\n"
    added = _OLD_OUTPUT_FORMAT.replace(anchor, f"{anchor}{line}\n", 1)
    assert added != _OLD_OUTPUT_FORMAT
    assert _has_the_fidelity_line(added)
    fence = "```markdown\n"
    above = _OLD_OUTPUT_FORMAT.replace(fence, f"{line}\n\n{fence}", 1)
    assert above.index(line) < above.index(fence)
    below = f"{_OLD_OUTPUT_FORMAT}\n{line}\n"
    as_row = _OLD_OUTPUT_FORMAT.replace(
        "| Gate | Result |", "| Gate | Result |\n| Fidelity read | yes |", 1
    )
    twice = added.replace(f"{line}\n", f"{line}\n{line}\n", 1)
    assert twice.count(line) == 2
    dropped = "\n".join(
        row
        for row in added.split("\n")
        if not row.startswith("**Claim verification:**")
    )
    for planted in (above, below, as_row, twice, dropped):
        assert planted != _OLD_OUTPUT_FORMAT
        assert not _has_the_fidelity_line(planted), planted


def test_a_missing_heading_fails_loudly_and_a_fenced_hash_line_is_no_heading() -> None:
    with pytest.raises(AssertionError, match="no heading"):
        _section("## Other\ntext\n", "### C6", "planted")
    planted = "## A\nfirst\n```bash\n# a shell comment\n```\nafter the fence\n### A.1\ndeeper\n## B\nnext\n"
    section = _section(planted, "## A", "planted")
    assert "after the fence" in section
    assert "deeper" in section
    assert "next" not in section
    with pytest.raises(AssertionError, match="does not exist"):
        _read(Path(__file__).with_name("no-such-skill.md"))
