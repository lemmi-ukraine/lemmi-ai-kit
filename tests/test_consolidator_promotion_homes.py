"""The consolidator sends a promotion to the project's own homes and names its bundled ones a sample.

`learning-consolidator` drains the learnings buffer of every project that installs the kit, and it
was written against one project's layout: README promotions went to two `backend/app/` paths, a
feature README was paired with `docs/onboarding/` by an "AGENTS.md rule" another project need not
have, both references read as THE map of homes, and the landing audit's text listed READMEs and
source trees its ten default globs never scan. The routing text now sends the promoter to the
project's own AGENTS.md for its homes and calls the bundled homes a sample, each table or rule that
names one is labelled, and the audit's text names the option that adds a home outside its globs and
the files that are never a landing site. The critic's own landing audit passes the same surfaces,
or a home the consolidator's audit saw reads as deleted knowledge in the critic's pass.

THE SURFACE, in numbers the tests assert: 11 places in 4 files. SKILL.md: the Step 3 routing
paragraph, PROMOTE_TO_README steps 1 and 4, Phase 5 step 6. consolidation-actions.md: the two
Target selection labels, the README pairing rule, the Drain Landing Audit's surface paragraph and
its closing note. cross-reference-targets.md: its head. consolidation-critic SKILL.md: the lead of
C1, its landing audit. Each place is cut by its heading (a heading or a lead that is missing fails
loudly), folded, and checked for the words it must carry and the old words it must not. Each check
is fired first at the text its place carried before (`old`, unedited excerpts) and must report it,
and at near-misses that carry half of a label.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_CONSOLIDATOR = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "learning-consolidator"
)
_SKILL = _CONSOLIDATOR / "SKILL.md"
_ACTIONS = _CONSOLIDATOR / "references" / "consolidation-actions.md"
_TARGETS = _CONSOLIDATOR / "references" / "cross-reference-targets.md"
_CRITIC = _CONSOLIDATOR.parent / "consolidation-critic" / "SKILL.md"

_EM = chr(0x2014)  # em dash
_IMPLIES = chr(0x21D2)  # rightwards double arrow
_SECTION_SIGN = chr(0xA7)
_HEADING = re.compile(r"^(#{1,6})\s")


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _flat(text: str) -> str:
    """Quote markers dropped and whitespace folded, so a re-wrapped quoted label is the same
    sentence."""
    return " ".join(re.sub(r"^\s*>+ ?", "", text, flags=re.MULTILINE).split())


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. A missing heading
    fails loudly, with the heading named."""
    found: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        match = None if in_fence or fence else _HEADING.match(line)
        if not found:
            if match is not None and line.startswith(heading):
                level = len(match.group(1))
                found.append(line)
        elif match is not None and len(match.group(1)) <= level:
            break
        else:
            found.append(line)
        if fence:
            in_fence = not in_fence
    assert found, f"no heading starts with {heading!r}"
    return "\n".join(found)


def _block(text: str, lead: str) -> str:
    """The blank-line-delimited block whose first line starts with `lead`; missing fails."""
    for block in re.split(r"\n\s*\n", text):
        if block.lstrip().startswith(lead):
            return block
    raise AssertionError(f"no block starts with {lead!r}")


def _item(text: str, lead: str) -> str:
    """A list item: its first line starts with `lead`, and it runs through the indented lines
    that follow it; a missing item fails loudly."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(lead):
            item = [line]
            for follow in lines[index + 1 :]:
                if not follow.startswith((" ", "\t")) or not follow.strip():
                    break
                item.append(follow)
            return "\n".join(item)
    raise AssertionError(f"no list item starts with {lead!r}")


def _head(text: str) -> str:
    """Everything before the first `## ` heading: the title, the purpose and any label."""
    head, separator, _ = text.partition("\n## ")
    assert separator, "the file has no `## ` heading to end its head"
    return head


def _cut(
    heading: str, part: Callable[[str, str], str], lead: str
) -> Callable[[str], str]:
    """The place a heading's section holds: its block or list item that starts with `lead`."""

    def place(text: str) -> str:
        return part(_section(text, heading), lead)

    return place


class _Place(NamedTuple):
    name: str
    path: Path
    cut: Callable[[str], str]
    needs: tuple[str, ...]
    gone: tuple[str, ...]
    old: str


def _gaps(place: _Place, text: str) -> list[str]:
    """What `text` (already cut to the place) lacks or still carries, folded."""
    flat = _flat(text)
    return [
        f"does not say {need!r}" for need in place.needs if _flat(need) not in flat
    ] + [f"still says {old!r}" for old in place.gone if _flat(old) in flat]


_SAMPLE_TARGETS = "a sample; the homes the project's own AGENTS.md names replace it"
_PAIRING = "Where the project's AGENTS.md pairs READMEs with docs"
_LANDING = "consolidation-actions.md Drain Landing Audit surface paragraph"
# The sentence that lists the files neither scan counts, whole and in order: the buffer, the file
# under audit, the byte copies and the two ledgers, then why. The audit script's docstring and
# `--help` say the same list.
_NEVER_COUNTED = (
    "Neither scan counts a file that holds or quotes the entries themselves, whatever the "
    "globs match: the buffer (any `learnings.md`), the snapshot under audit (the path the "
    "run is given, whatever its name), every byte copy (`learnings-pre-drain-*.md`; an "
    "older one still holds the KEEP entries of earlier drains) and the two ledgers that "
    "quote what a drain removed (any `ai-changelog.md`, any `improvement-hypotheses.md`), "
    "so a surface that reaches `.ai/` cannot land an entry in its own copy or in the "
    "record of its removal."
)
# The same sentence as the paragraph carried it: the byte copies were called snapshots and the
# ledgers were not named.
_NEVER_COUNTED_BEFORE = (
    "Neither scan counts a file that holds the entries themselves, whatever the globs "
    "match: the buffer (any `learnings.md`), the snapshot under audit (the path the run "
    "is given, whatever its name) and every other pre-drain snapshot "
    "(`learnings-pre-drain-*.md`, which still holds the KEEP entries of earlier drains), "
    "so a surface that reaches `.ai/` cannot land an entry in its own copy."
)
_BYTE_COPIES_AS_SNAPSHOTS = "every other pre-drain snapshot"
# Each plant is one change to the shipped sentence: what it says now, and what it is made to say.
# The classes are the lead's polarity, which files the list holds, and the closing consequence.
_PLANTS: tuple[tuple[str, str, str], ...] = (
    ("the lead flipped", "Neither scan counts", "Both scans count"),
    ("the lead negated twice", "Neither scan counts", "Neither scan does not count"),
    (
        "the ledgers moved out of the list",
        " and the two ledgers that quote what a drain removed",
        ", but both scans count the two ledgers that quote what a drain removed",
    ),
    ("a ledger dropped", ", any `improvement-hypotheses.md`", ""),
    (
        "the byte copies called snapshots again",
        "every byte copy (`learnings-pre-drain-*.md`",
        "every other pre-drain snapshot (`learnings-pre-drain-*.md`",
    ),
    (
        "the consequence inverted",
        "cannot land an entry in its own copy",
        "can land an entry in its own copy",
    ),
)

_PLACES: tuple[_Place, ...] = (
    _Place(
        "SKILL.md Step 3 routing paragraph",
        _SKILL,
        _cut("#### Step 3: Promotion Classification", _block, "For entries that are"),
        (
            "classify the promotion action and its home",
            "one the project's own AGENTS.md names",
            "this skill's homes are a sample",
        ),
        ("classify the promotion action. Use the decision criteria",),
        "For entries that are `CURRENT` and `NOT_COVERED` or `PARTIALLY_COVERED`, classify the\n"
        "promotion action. Use the decision criteria in\n"
        "[references/consolidation-actions.md](references/consolidation-actions.md):",
    ),
    _Place(
        "SKILL.md PROMOTE_TO_README step 1",
        _SKILL,
        _cut("#### PROMOTE_TO_README", _item, "1. "),
        ("README from the project's own AGENTS.md", "(a sample layout:"),
        ("Identify the owning subsystem: `backend/app",),
        "1. Identify the owning subsystem: `backend/app/core/<module>/README.md` or\n"
        "   `backend/app/features/<feature>/README.md`.",
    ),
    _Place(
        "SKILL.md PROMOTE_TO_README step 4",
        _SKILL,
        _cut("#### PROMOTE_TO_README", _item, "4. "),
        (_PAIRING, "the sample pairs feature READMEs with `docs/onboarding/`"),
        ("(AGENTS.md rule)",),
        "4. Feature READMEs must stay in sync with `docs/onboarding/` (AGENTS.md rule) "
        f"{_EM} check whether\n   the matching onboarding doc needs the same note.",
    ),
    _Place(
        "SKILL.md Phase 5 step 6",
        _SKILL,
        _cut("### Phase 5", _item, "6. **Verify LANDING"),
        (
            "Run (`--surface <glob>` adds a home) `drain_audit.py <snapshot> <base-ref>`",
        ),
        (),
        f"6. **Verify LANDING {_EM} mandatory, and NOT step 5's check.** Step 5 proves "
        "entries left the buffer; it\n   is blind to an entry removed whose knowledge "
        "reached no home. Run\n   `drain_audit.py <snapshot> <base-ref>` "
        f"{_EM} **the ref is not optional** (no ref exits 2), and which\n   one is correct "
        "depends on whether the promotions are committed; reconcile `entries scanned`\n"
        "   against `grep -c '^### ' <snapshot>`, then adjudicate every flagged row (exit 1 "
        f"means rows to\n   adjudicate): [{_SECTION_SIGN} Drain Landing Audit]"
        "(references/consolidation-actions.md#drain-landing-audit).",
    ),
    _Place(
        "consolidation-actions.md PROMOTE_TO_RULE Target selection",
        _ACTIONS,
        _cut("### PROMOTE_TO_RULE", _block, "**Target selection"),
        (_SAMPLE_TARGETS,),
        ("**Target selection:**",),
        "**Target selection:**",
    ),
    _Place(
        "consolidation-actions.md PROMOTE_TO_README Target selection",
        _ACTIONS,
        _cut("### PROMOTE_TO_README", _block, "**Target selection"),
        (_SAMPLE_TARGETS,),
        ("**Target selection:**",),
        "**Target selection:**",
    ),
    _Place(
        "consolidation-actions.md PROMOTE_TO_README pairing rule",
        _ACTIONS,
        _cut("### PROMOTE_TO_README", _block, "**Rules:**"),
        (_PAIRING, "keep each pair in sync"),
        ("feature docs (AGENTS.md rule)",),
        f"**Rules:**\n- Create the README if absent {_EM} short purpose header + the guidance "
        "(precedent:\n  `backend/app/core/jobs/README.md`, created by the redistribution)\n"
        "- Match the README's existing style; one concise bullet per lesson (constraint + why)\n"
        "- Feature READMEs must stay in sync with `docs/onboarding/` feature docs (AGENTS.md rule)",
    ),
    _Place(
        _LANDING,
        _ACTIONS,
        _cut("## Drain Landing Audit", _block, "For each entry the script extracts"),
        (
            "its ten default globs (AGENTS.md, CLAUDE.md, `docs/`",
            "plus each `--surface <glob>` the run adds",
            "Neither scan counts a file that holds or quotes the entries themselves",
            "the buffer (any `learnings.md`)",
            "the snapshot under audit (the path the run is given, whatever its name)",
            "every byte copy (`learnings-pre-drain-*.md`",
            "the two ledgers that quote what a drain removed (any `ai-changelog.md`, "
            "any `improvement-hypotheses.md`)",
            _NEVER_COUNTED,
        ),
        ("module and feature READMEs, backend source", _BYTE_COPIES_AS_SNAPSHOTS),
        "For each entry the script extracts its most distinctive backticked identifiers and "
        "greps every\npromotion surface (AGENTS.md, CLAUDE.md, `docs/`, skills, cursor rules, "
        "kiro steering, module and\nfeature READMEs, backend source, task docs). Zero hits "
        f"{_IMPLIES} `[LOSS?]`.",
    ),
    _Place(
        "consolidation-actions.md Drain Landing Audit closing note",
        _ACTIONS,
        # The section's one blockquote, cut by a lead the old note and the new one share.
        _cut("## Drain Landing Audit", _block, "> "),
        (
            "needs one `--surface <glob>` on every run",
            "adds a glob without replacing a default",
            "A surface the two scans are known to read differently exits 2",
        ),
        ("in sync with the promotion surfaces above",),
        "> Keep `TARGET_GLOBS` in the script in sync with the promotion surfaces above. A "
        "missing glob\n> produces false `[LOSS?]` rows, which trains readers to skim the "
        f"output {_EM} the same\n> noisy-check-gets-ignored failure the entry-integrity lint "
        "was tightened to avoid. Each glob\n> reaches git as a `:(glob)` pathspec, so `**/` "
        "matches zero or more directories and `*` never\n> crosses `/`: `docs/**/*.md` "
        "includes `docs/x.md`, and `tasks/*.md` is that folder's own files only.",
    ),
    _Place(
        "cross-reference-targets.md head",
        _TARGETS,
        _head,
        (
            "A sample.",
            "The project's own AGENTS.md names its homes and replaces this map",
        ),
        (),
        f"# Cross-Reference Targets {_EM} Files to Update After Promotions\n\nWhen the "
        "learning-consolidator promotes entries to rules, skills, or conventions, multiple\n"
        "files across the project may need corresponding updates. This reference maps each "
        "promotion\ntarget to its dependent files.\n\n> **Extension note:** `.cursor/rules/` "
        "may mix `.md` and `.mdc` files.\n> Check the actual on-disk extension before "
        f"creating/editing a cursor rule {_EM}\n> assuming `.md` can create a divergent "
        "duplicate.",
    ),
    _Place(
        "consolidation-critic SKILL.md C1 lead",
        _CRITIC,
        _cut("### C1", _block, "Removal verification proves"),
        (
            "with the same `--surface` values as the consolidator's Phase 5 audit",
            "(`--surface <glob>` adds a home)",
        ),
        (),
        "Removal verification proves entries left the buffer. It is **structurally blind** "
        "to the opposite\nfailure: an entry removed whose knowledge reached no home. Run the "
        "audit that fits the state of the\npromotions; the base ref is mandatory (no ref "
        "exits 2):",
    ),
)


def test_the_scan_surface_is_eleven_places_in_four_files() -> None:
    """Stated in numbers, so a place that is dropped from the table is a red, not a gap."""
    assert len(_PLACES) == 11, [place.name for place in _PLACES]
    assert len({place.name for place in _PLACES}) == len(_PLACES)
    assert {place.path for place in _PLACES} == {_SKILL, _ACTIONS, _TARGETS, _CRITIC}


@pytest.mark.parametrize("place", _PLACES, ids=[place.name for place in _PLACES])
def test_each_place_sends_the_promoter_to_the_project_s_own_homes(
    place: _Place,
) -> None:
    """Red on the text each place carried: no word of the project's own AGENTS.md, no
    sample label, no option for a home outside the audit's default globs, and no word of the
    files that are never a landing site."""
    gaps = _gaps(place, place.cut(_read(place.path)))
    assert not gaps, f"{place.name}: {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[place.name for place in _PLACES])
def test_each_check_reports_the_text_its_place_carried(place: _Place) -> None:
    """The known positive for every check above: the unedited excerpt must be reported."""
    assert _gaps(place, place.old), f"{place.name}: the check passes its old text"


def test_a_label_that_carries_half_of_the_rule_is_reported() -> None:
    """Near-misses: a sample label with no word of the project's AGENTS.md, a pointer at the
    AGENTS.md with no sample label, and the new label beside the old one, are each reported;
    the shipped label re-wrapped and re-emphasised is not."""
    place = _PLACES[4]
    assert _gaps(place, "**Target selection** (a sample):")
    assert _gaps(
        place, "**Target selection** (the project's own AGENTS.md names homes):"
    )
    assert _gaps(place, f"**Target selection:**\n({_SAMPLE_TARGETS})")
    assert not _gaps(
        place,
        "**Target selection** (a sample; the homes the project's\nown "
        "AGENTS.md names replace it):",
    )
    routing = _PLACES[0]
    assert _gaps(
        routing, "classify the promotion action and its home (homes are a sample)."
    )


def test_the_never_counted_sentence_keeps_its_files_and_its_polarity() -> None:
    """A pin on each name passes a sentence that has turned the byte copies or the ledgers from
    files the scans skip into files they count, so the sentence is pinned whole and in order and
    fired at plants. The shipped paragraph must pass; the sentence as it read before (byte copies
    called snapshots, no ledgers) and each plant, a change of the lead's polarity, of which files
    the list holds, or of the closing consequence, must each be reported; a plant that misses its
    target fails loudly instead of passing; the paragraph re-wrapped, or followed by another
    sentence, is not reported."""
    place = next(place for place in _PLACES if place.name == _LANDING)
    shipped = _flat(place.cut(_read(place.path)))
    assert not _gaps(place, shipped), "the shipped paragraph fails its own check"
    assert _NEVER_COUNTED in shipped
    before = shipped.replace(_NEVER_COUNTED, _NEVER_COUNTED_BEFORE)
    assert before != shipped
    assert _gaps(place, before), "the check passes the sentence as it read before"
    for label, target, change in _PLANTS:
        assert target in shipped, f"the plant {label!r} misses its target"
        assert _gaps(place, shipped.replace(target, change)), (
            f"the check passes the plant {label!r}"
        )
    words = shipped.split(" ")
    rewrapped = "\n".join(
        "> " + " ".join(words[start : start + 9]) for start in range(0, len(words), 9)
    )
    assert "\n" in rewrapped and not _gaps(place, rewrapped)
    assert not _gaps(place, shipped + " A sentence that follows changes nothing here.")
