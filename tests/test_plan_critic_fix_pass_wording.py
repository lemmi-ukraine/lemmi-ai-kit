"""`plan-critic` asks for a fix as exact replacement text and closes its fix passes with a diff.

The skill already caps a document at two runs and says what a later run may edit. Two things
were missing from it. A finding recorded its fix as a description of what changed, so a fix pass
could "tighten the wording" and nobody could tell which lines it had touched. And nothing checked,
after the last fix pass, that the document held only the fixes the critic meant to make.

The finding format now asks for the fix as the line or paragraph as it must read once the fix is
applied, in the `Resolution:` field of its template, and the good example there shows one: it had
described a change, the shape the clause rules out. Step 4 now holds a paragraph of its own after
the later-run paragraph: diff the document against its version before the first fix pass, and
revert every changed line that is not a fix made on purpose. Neither clause restates the run cap,
which keeps one home in "When This Skill Activates".

That paragraph named a version to diff against and never said where it comes from. For a tracked
document git holds it; for an untracked one, which is any spec a project keeps out of version
control, nothing does, and the rule could not run as written. The paragraph now ends with one
sentence that closes the gap: copy the document before the first fix pass and diff against the
copy, a tracked document using git instead when git holds that version.

What each test asserts:

* `test_the_fix_field_asks_for_exact_replacement_text` reads the finding format's "Finding
  Format" section: its first fenced block, the template, and in it the `Resolution:` field only,
  so the same words in a sentence below the template or in an example do not count.
  `test_the_good_finding_shows_its_fix_as_quoted_replacement_text` reads the block after the
  "Good finding" marker.
* `test_step_four_holds_the_diff_check_after_the_later_run_paragraph` cuts Step 4 by its
  heading and reads its paragraphs: the diff check is one paragraph of its own, after the one
  that starts "In a later run".
* `test_the_diff_check_says_where_the_earlier_version_comes_from` reads the one paragraph of
  Step 4 that starts "After the last fix pass" and nothing else: the copy is made before the
  first fix pass, the diff is against the copy, and a tracked document may use git instead when
  git holds that version. The same words in a neighbouring paragraph, in Step 5 or as a
  paragraph of their own do not count.
* `test_the_run_cap_is_unchanged_and_stated_once` is NOT red on the old text: it holds each of
  the cap's two phrases to one place, so it guards the edits above and shows no change.
* The instrument tests fire every check at planted text. Each reads a small literal document, so
  none depends on the shipped wording and all pass on the old files too: the old shape of each
  clause must be flagged, each part dropped on its own must be flagged and no other part with it,
  and a re-wrapped or a reworded near-miss must pass.

A guard that reads text never runs out of shapes. This one covers classes: a clause dropped, a
clause hollowed (its name kept, its contrast or its measure gone), a clause moved out of its
field, a paragraph moved out of its place, merged into a neighbour or repeated, the run cap
restated (in any of its words, in capitals too) or changed, the later-run paragraph missing or
repeated, a field that runs past a blank line, and a re-wrap or a rewording that changes no
rule; a planted re-wrap is asserted to differ from its source, so it is never the shipped shape
under another name. The helpers the tables go through are fired too: the verdict helper must
enforce each of its three rules, the disjointness check must see a planted overlap, and the
heading, field and later-run matches must pass over a decoy that holds the heading, the label
or the lead only after other words. The sentence about the earlier version has a table of its
own: it dropped, hollowed one part at a time (the timing, the diff against the copy, the git
stand-in, its condition), moved into the later-run paragraph, into Step 5 or into a paragraph
of its own, the paragraph it belongs to missing, repeated or run on to the later-run paragraph
(where its lead stands after other words, and must not be found there), and a re-wrap, a
rewording and a split into three sentences, which change no rule and pass.
"""

import re
import textwrap
from pathlib import Path
from typing import NamedTuple

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_ROOT = shipped_skill_dirs()["plan-critic"]
_SKILL = _ROOT / "SKILL.md"
_FORMAT = _ROOT / "references" / "finding-format.md"
_SURFACE: tuple[Path, ...] = (_SKILL, _FORMAT)

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_FIELD_LABELS = ("Problem:", "Reasoning:", "Resolution:", "Alternative:")
_EM_DASH = chr(0x2014)

# The parts of each new clause. A clause is held by its name and by its contrast and its
# measure, not by its lead alone, so one that kept its name and lost the rest is flagged.
_FIX_PARTS = (
    "exact replacement text",
    "the line or paragraph as it must read once the fix is applied",
    "not a description of a change",
)
_DIFF_PARTS = (
    "diff the document against its version before the first fix pass",
    "every changed line must be a fix you made on purpose",
    "any other change is reverted",
)
# The diff check also says where the earlier version comes from: without it the rule cannot
# run on a document git does not track. Held lower-cased, because the first part opens its
# sentence.
_SOURCE_PARTS = (
    "copy the document before the first fix pass",
    "diff against the copy",
    "a tracked document may use git instead",
    "when git holds that version",
)
# The run cap has one home, in "When This Skill Activates". These are its two phrases, and the
# words by which a new clause would be restating it.
_CAP_PHRASES = (
    "at most two runs per document",
    "a factual error, a contradiction, a missing item or an unsafe statement",
)
_CAP_WORDS = (
    "at most two",
    "twice",
    "two runs",
    "factual error",
    "missing item",
    "unsafe statement",
)
_LATER_RUN_LEAD = "In a later run"
_DIFF_LEAD = "After the last fix pass"
# A quoted line shorter than this is a word, not the line as it must read.
_MIN_QUOTED_LINE = 20


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _fold(text: str) -> str:
    """The text with every run of whitespace, line breaks included, as one space."""
    return " ".join(text.split())


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


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
        fence = _is_fence(line)
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


def _paragraphs(section: str) -> list[str]:
    """The blank-line-separated blocks of the section, the heading line among them."""
    return [block for block in re.split(r"\n\s*\n", section) if block.strip()]


def _fenced_block_after(section: str, lead: str, where: str) -> str:
    """The content of the first fenced block after the first line that starts with `lead`;
    with an empty `lead`, the first fenced block of the section.

    A block that is never opened or never closed fails with the lead named.
    """
    armed = lead == ""
    content: list[str] | None = None
    for line in section.split("\n"):
        if content is None:
            if not armed:
                armed = line.startswith(lead)
            elif _is_fence(line):
                content = []
        elif _is_fence(line):
            return "\n".join(content)
        else:
            content.append(line)
    raise AssertionError(f"{where}: no fenced block after a line starting {lead!r}")


def _field(block: str, label: str, where: str) -> str:
    """The first field of a finding block that starts with `label`: its line and the lines
    after it, indented or not, up to the next field label or a blank line."""
    lines = block.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(label):
            field = [line]
            for follow in lines[index + 1 :]:
                if not follow.strip() or follow.startswith(_FIELD_LABELS):
                    break
                field.append(follow)
            return "\n".join(field)
    raise AssertionError(f"{where}: no field starting {label!r}")


def _restated_cap(folded: str) -> list[str]:
    lowered = folded.lower()
    return [
        f"restates the run cap ({word!r})" for word in _CAP_WORDS if word in lowered
    ]


def _missing_parts(subject: str, folded: str, parts: tuple[str, ...]) -> list[str]:
    return [
        f"{subject} does not carry {part!r}" for part in parts if part not in folded
    ]


def _fix_field_problems(finding_format: str, where: str) -> list[str]:
    """What is wrong with the template's fix field: a part of the clause it lacks, or a
    restatement of the run cap. Only the `Resolution:` field of the first fenced block of the
    "Finding Format" section is read, so a clause that sits anywhere else is not counted."""
    section = _section(finding_format, "## Finding Format", where)
    template = _fenced_block_after(section, "", where)
    folded = _fold(_field(template, "Resolution:", where))
    return _missing_parts("the fix field", folded, _FIX_PARTS) + [
        f"the fix field {issue}" for issue in _restated_cap(folded)
    ]


def _good_example_problems(finding_format: str, where: str) -> list[str]:
    """The good example is a calibration anchor, so its fix must show the line as it must
    read, in quotes, and not describe a change.

    Quotes pair from left to right, so the words between two quoted strings are never read
    as a quoted string of their own.
    """
    section = _section(finding_format, "## Finding Format", where)
    block = _fenced_block_after(section, "**Good finding**", where)
    folded = _fold(_field(block, "Resolution:", where))
    quoted = re.findall(r'"([^"]*)"', folded)
    if not any(len(line) >= _MIN_QUOTED_LINE for line in quoted):
        return ["the good finding's fix holds no quoted replacement text"]
    return []


def _diff_check_problems(skill: str, where: str) -> list[str]:
    """What is wrong with the diff check in Step 4: not one paragraph of its own, before the
    later-run paragraph, a part of its rule missing, or a restatement of the run cap."""
    folded = [_fold(p) for p in _paragraphs(_section(skill, "### Step 4", where))]
    later = [at for at, text in enumerate(folded) if text.startswith(_LATER_RUN_LEAD)]
    own = [at for at, text in enumerate(folded) if text.startswith(_DIFF_LEAD)]
    problems: list[str] = []
    if len(later) != 1:
        problems.append(
            f"{len(later)} paragraphs of Step 4 start {_LATER_RUN_LEAD!r}, expected 1"
        )
    if len(own) != 1:
        problems.append(
            f"{len(own)} paragraphs of Step 4 start {_DIFF_LEAD!r}, expected 1"
        )
        return problems
    if len(later) == 1 and own[0] < later[0]:
        problems.append("the diff check comes before the later-run paragraph")
    paragraph = folded[own[0]]
    problems += _missing_parts("the diff check", paragraph, _DIFF_PARTS)
    return problems + [f"the diff check {issue}" for issue in _restated_cap(paragraph)]


def _source_problems(skill: str, where: str) -> list[str]:
    """What is wrong with the sentence that says where the diff check's earlier version comes
    from: the paragraph of Step 4 that starts with the diff check's lead is not found exactly
    once, or a part of the sentence is missing from it.

    Only that paragraph is read, so the same words in a neighbouring paragraph, in another
    section or as a paragraph of their own are not counted. The parts are held lower-cased, so
    the case of the sentence's first word decides nothing.
    """
    folded = [_fold(p) for p in _paragraphs(_section(skill, "### Step 4", where))]
    own = [text for text in folded if text.startswith(_DIFF_LEAD)]
    if len(own) != 1:
        return [f"{len(own)} paragraphs of Step 4 start {_DIFF_LEAD!r}, expected 1"]
    return _missing_parts("the diff check", own[0].lower(), _SOURCE_PARTS)


def _run_cap_problems(skill: str, where: str) -> list[str]:
    """Each of the cap's two phrases must stand once in the file, and in its own section."""
    whole = _fold(skill)
    home = _fold(_section(skill, "## When This Skill Activates", where))
    return [
        f"{phrase!r} stands {whole.count(phrase)} times in the file and "
        f"{home.count(phrase)} in its section, expected 1 and 1"
        for phrase in _CAP_PHRASES
        if (whole.count(phrase), home.count(phrase)) != (1, 1)
    ]


def _overlap_problems(skill: str, where: str) -> list[str]:
    """The lines that sit in both scanned sections of SKILL.md, the one that holds the run cap and
    Step 4. A line in both is judged by two rules, so each one is a problem."""
    cap_home = _section(skill, "## When This Skill Activates", where)
    step_four = _section(skill, "### Step 4", where)
    shared = {line for line in cap_home.split("\n") if line.strip()} & {
        line for line in step_four.split("\n") if line.strip()
    }
    return [f"one line is judged by two rules: {line!r}" for line in sorted(shared)]


# --- the change ---------------------------------------------------------------------------


def test_the_fix_field_asks_for_exact_replacement_text() -> None:
    where = "plan-critic references/finding-format.md"
    problems = _fix_field_problems(_text(_FORMAT), where)
    assert not problems, f"{where}, template fix field: " + "; ".join(problems)


def test_the_good_finding_shows_its_fix_as_quoted_replacement_text() -> None:
    where = "plan-critic references/finding-format.md"
    problems = _good_example_problems(_text(_FORMAT), where)
    assert not problems, f"{where}, good finding: " + "; ".join(problems)


def test_step_four_holds_the_diff_check_after_the_later_run_paragraph() -> None:
    where = "plan-critic SKILL.md"
    problems = _diff_check_problems(_text(_SKILL), where)
    assert not problems, f"{where}, Step 4: " + "; ".join(problems)


def test_the_diff_check_says_where_the_earlier_version_comes_from() -> None:
    where = "plan-critic SKILL.md"
    problems = _source_problems(_text(_SKILL), where)
    assert not problems, f"{where}, Step 4: " + "; ".join(problems)


def test_the_run_cap_is_unchanged_and_stated_once() -> None:
    where = "plan-critic SKILL.md"
    problems = _run_cap_problems(_text(_SKILL), where)
    assert not problems, f"{where}, run cap: " + "; ".join(problems)


# --- planted text: the instruments --------------------------------------------------------

_LABEL = "Resolution: "
_UNRESOLVED = f'OR "UNRESOLVED {_EM_DASH} requires user input"'
# The old fix field, and the old good example, as they stood before the clause.
_FIX_OLD = "{what was changed in the document to fix this, " + _UNRESOLVED + "}"
_GOOD_OLD = (
    "Added retry_with_backoff(max=3, backoff_base=2) to the service layer section of the "
    "design. Updated the corresponding task's acceptance criteria."
)
_FIX_NEW = (
    "{the fix as exact replacement text: the line or paragraph as it must read once the fix "
    "is applied, not a description of a change, " + _UNRESOLVED + "}"
)
_GOOD_NEW = (
    'Design, service layer section: "The generation call goes through '
    'retry_with_backoff(max=3, backoff_base=2)."'
)
_CLAUSE_SENTENCE = (
    "Write the fix as exact replacement text: the line or paragraph as it must read once "
    "the fix is applied, not a description of a change."
)

_CAP_PARAGRAPH = (
    "**Self-challenge is per-ARTIFACT, not per-task.** The same applies to a revision, with a\n"
    "cap: **at most two runs per document**. That re-run is the second and last run: a later\n"
    "run edits only for a factual error, a contradiction, a\n"
    "missing item or an unsafe statement, not for wording, order or taste."
)
_LATER_RUN = (
    "In a later run (the run cap in When This Skill Activates), resolve only the classes the\n"
    "run cap names; drop every other finding, a Minor included, without fixing or surfacing it."
)
# The diff check as it stood before it said where the earlier version comes from, then the
# sentence that does, then the paragraph as it ships: the sentence joins the paragraph on a
# line of its own, with no blank line between.
_DIFF_OLD = (
    "After the last fix pass, diff the document against its version before the first fix pass:\n"
    "every changed line must be a fix you made on purpose, and any other change is reverted."
)
_SOURCE = (
    "Copy the document before the first fix pass and diff against the copy; a tracked document may use\n"
    "git instead when git holds that version."
)
_DIFF = _DIFF_OLD + "\n" + _SOURCE


class _Plant(NamedTuple):
    """A planted document and what a check must say about it: nothing for a near-miss, and
    for a planted defect one fragment per problem the check must name, no more."""

    label: str
    text: str
    flagged: tuple[str, ...] = ()


def _swap(text: str, old: str, new: str) -> str:
    """A planted edit that must find its anchor exactly once, so it cannot change nothing."""
    assert text.count(old) == 1, f"planted edit: {old!r} stands {text.count(old)} times"
    return text.replace(old, new)


def _wrapped(text: str, width: int, indent: str = "") -> str:
    """The text re-wrapped at `width`, a break falling wherever it falls."""
    return "\n".join(
        textwrap.wrap(
            text,
            width,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def _re_wrapped(text: str, width: int, indent: str = "") -> str:
    """A planted re-wrap: the text wrapped at `width`, which must differ from the text, so a plant
    that was meant to be re-wrapped can never be the shipped shape under another name."""
    wrapped = _wrapped(text, width, indent)
    assert wrapped != text, (
        f"planted re-wrap at {width} columns changed nothing: {text!r}"
    )
    return wrapped


def _format_fixture(resolution: str, good: str, below: str = "") -> str:
    """A small finding-format document: a template whose fix field is `resolution`, an
    optional sentence below it, a good example whose fix field is `good` and a bad one. Both
    are whole field texts, label included."""
    return "\n".join(
        [
            "# Finding Format & Severity Definitions",
            "",
            "## Severity Definitions",
            "",
            "A table sits here.",
            "",
            "## Finding Format",
            "",
            "For each issue found, record it internally during review:",
            "",
            "```",
            f"[SEVERITY] Category {_EM_DASH} Title",
            "Problem: {specific issue and realistic failure or cost}",
            "Reasoning: {grounded in concrete logic, not preference}",
            resolution,
            "Alternative: {if rejecting an approach, what is proposed instead}",
            "```",
            "",
            below,
            "",
            "**Good finding** (grounded, actionable):",
            "",
            "```",
            f"[Major] Stability {_EM_DASH} No retry on a provider rate limit",
            "Problem: The generation flow calls the provider without retry logic.",
            good,
            "```",
            "",
            "**Bad finding** (vague):",
            "",
            "```",
            f"[Major] Overengineering {_EM_DASH} Too complex",
            "Resolution: Simplify it.",
            "```",
            "",
            "## Output Format",
            "",
            "Present the document normally.",
            "",
        ]
    )


def _skill_fixture(
    *,
    cap: str = _CAP_PARAGRAPH,
    later_run: str = _LATER_RUN,
    before_later_run: str = "",
    after_later_run: str = "",
    step_five: str = "",
) -> str:
    """A small SKILL.md: the section that holds the run cap, Step 4 with its list, the
    later-run paragraph and room before and after it, and Step 5."""
    return "\n".join(
        [
            "# Plan Critic",
            "",
            "## When This Skill Activates",
            "",
            cap,
            "",
            "---",
            "",
            "## Review Process",
            "",
            f"### Step 4 {_EM_DASH} Resolve What You Can",
            "",
            "For each finding:",
            "- **Minor**: fix silently in the document.",
            "- **Blocker**: apply the Self-Refine loop:",
            "  1. Propose a specific fix to the document",
            "  2. Apply the fix",
            "",
            before_later_run,
            "",
            later_run,
            "",
            after_later_run,
            "",
            f"### Step 5 {_EM_DASH} Determine Output",
            "",
            "- If any Blocker remains, the document is NOT APPROVED.",
            "",
            step_five,
            "",
        ]
    )


def _fix_plant(
    label: str, fix: str, flagged: tuple[str, ...] = (), *, below: str = ""
) -> _Plant:
    return _Plant(
        label, _format_fixture(_LABEL + fix, _LABEL + _GOOD_NEW, below), flagged
    )


_P_NAME, _P_MEASURE, _P_CONTRAST = _FIX_PARTS

_FIX_PLANTS: tuple[_Plant, ...] = (
    _fix_plant("shipped-shape", _FIX_NEW),
    _Plant(
        "re-wrapped-from-column-zero",
        _format_fixture(_re_wrapped(_LABEL + _FIX_NEW, 40), _LABEL + _GOOD_NEW),
    ),
    _Plant(
        "re-wrapped-and-indented",
        _format_fixture(_re_wrapped(_LABEL + _FIX_NEW, 25, "  "), _LABEL + _GOOD_NEW),
    ),
    _fix_plant(
        "reworded-and-present",
        "{the exact replacement text of the fix: the line or paragraph as it must read "
        "once the fix is applied, not a description of a change}",
    ),
    _fix_plant("old-shape", _FIX_OLD, (_P_NAME, _P_MEASURE, _P_CONTRAST)),
    _fix_plant(
        "name-only",
        "{the fix as exact replacement text, " + _UNRESOLVED + "}",
        (_P_MEASURE, _P_CONTRAST),
    ),
    _fix_plant(
        "contrast-dropped",
        _swap(_FIX_NEW, ", not a description of a change", ""),
        (_P_CONTRAST,),
    ),
    _fix_plant(
        "measure-dropped",
        _swap(
            _FIX_NEW,
            ": the line or paragraph as it must read once the fix is applied",
            "",
        ),
        (_P_MEASURE,),
    ),
    _fix_plant(
        "clause-below-the-template-only",
        _FIX_OLD,
        (_P_NAME, _P_MEASURE, _P_CONTRAST),
        below=_CLAUSE_SENTENCE,
    ),
    _Plant(
        "clause-in-the-example-only",
        _format_fixture(_LABEL + _FIX_OLD, _LABEL + _FIX_NEW),
        (_P_NAME, _P_MEASURE, _P_CONTRAST),
    ),
    _fix_plant(
        "run-cap-restated",
        _swap(
            _FIX_NEW,
            "of a change, ",
            "of a change; a later run edits only for a factual error, ",
        ),
        ("restates the run cap",),
    ),
)

_D_NAME, _D_RULE, _D_REMEDY = _DIFF_PARTS

_DIFF_PLANTS: tuple[_Plant, ...] = (
    _Plant("shipped-shape", _skill_fixture(after_later_run=_DIFF)),
    _Plant("re-wrapped-narrow", _skill_fixture(after_later_run=_re_wrapped(_DIFF, 30))),
    _Plant("re-wrapped-to-one-line", _skill_fixture(after_later_run=_fold(_DIFF))),
    _Plant(
        "reworded-and-present",
        _skill_fixture(after_later_run=_swap(_DIFF, "reverted.", "reverted at once.")),
    ),
    _Plant(
        "decoy-holds-the-later-run-lead-mid-paragraph",
        _skill_fixture(
            before_later_run="Compare: In a later run the same rule applies.",
            after_later_run=_DIFF,
        ),
    ),
    _Plant(
        "old-shape-absent",
        _skill_fixture(),
        (f"0 paragraphs of Step 4 start {_DIFF_LEAD!r}",),
    ),
    _Plant(
        "before-the-later-run-paragraph",
        _skill_fixture(before_later_run=_DIFF),
        ("comes before the later-run paragraph",),
    ),
    _Plant(
        "merged-into-the-later-run-paragraph",
        _skill_fixture(later_run=_LATER_RUN + "\n" + _DIFF),
        (f"0 paragraphs of Step 4 start {_DIFF_LEAD!r}",),
    ),
    _Plant(
        "moved-into-step-five",
        _skill_fixture(step_five=_DIFF),
        (f"0 paragraphs of Step 4 start {_DIFF_LEAD!r}",),
    ),
    _Plant(
        "duplicated",
        _skill_fixture(after_later_run=_DIFF + "\n\n" + _DIFF),
        (f"2 paragraphs of Step 4 start {_DIFF_LEAD!r}",),
    ),
    _Plant(
        "no-later-run-paragraph",
        _skill_fixture(later_run="", after_later_run=_DIFF),
        (f"0 paragraphs of Step 4 start {_LATER_RUN_LEAD!r}",),
    ),
    _Plant(
        "two-later-run-paragraphs",
        _skill_fixture(
            later_run=_LATER_RUN + "\n\n" + _LATER_RUN, after_later_run=_DIFF
        ),
        (f"2 paragraphs of Step 4 start {_LATER_RUN_LEAD!r}",),
    ),
    _Plant(
        "remedy-dropped",
        _skill_fixture(
            after_later_run=_swap(_DIFF, ", and any other change is reverted", "")
        ),
        (_D_REMEDY,),
    ),
    _Plant(
        "purpose-dropped",
        _skill_fixture(after_later_run=_swap(_DIFF, " you made on purpose", "")),
        (_D_RULE,),
    ),
    _Plant(
        "baseline-dropped",
        _skill_fixture(
            after_later_run=_swap(
                _DIFF, " against its version before the first fix pass", ""
            )
        ),
        (_D_NAME,),
    ),
    _Plant(
        "run-cap-restated",
        _skill_fixture(
            after_later_run=_DIFF + " A later run edits only for a factual error."
        ),
        ("restates the run cap",),
    ),
)

_S_COPY, _S_DIFF, _S_GIT, _S_WHEN = _SOURCE_PARTS
# The shipped paragraph on one line, so a planted edit's anchor can never straddle a line break.
_SOURCE_LINE = _fold(_DIFF)

_SOURCE_PLANTS: tuple[_Plant, ...] = (
    _Plant("shipped-shape", _skill_fixture(after_later_run=_DIFF)),
    _Plant("re-wrapped-narrow", _skill_fixture(after_later_run=_re_wrapped(_DIFF, 30))),
    _Plant("re-wrapped-to-one-line", _skill_fixture(after_later_run=_SOURCE_LINE)),
    _Plant(
        "reworded-and-present",
        _skill_fixture(
            after_later_run=_swap(
                _SOURCE_LINE,
                "and diff against the copy",
                "and then diff against the copy",
            )
        ),
    ),
    _Plant(
        "split-into-three-sentences",
        _skill_fixture(
            after_later_run=_swap(
                _SOURCE_LINE,
                " and diff against the copy; a tracked document",
                ". Diff against the copy. A tracked document",
            )
        ),
    ),
    _Plant("old-paragraph", _skill_fixture(after_later_run=_DIFF_OLD), _SOURCE_PARTS),
    _Plant(
        "timing-dropped",
        _skill_fixture(
            after_later_run=_swap(
                _SOURCE_LINE, " before the first fix pass and diff", " and diff"
            )
        ),
        (_S_COPY,),
    ),
    _Plant(
        "copy-made-after-the-first-fix-pass",
        _skill_fixture(
            after_later_run=_swap(
                _SOURCE_LINE,
                "Copy the document before the first fix pass",
                "Copy the document after the first fix pass",
            )
        ),
        (_S_COPY,),
    ),
    _Plant(
        "diff-against-the-copy-dropped",
        _skill_fixture(
            after_later_run=_swap(_SOURCE_LINE, " and diff against the copy;", ";")
        ),
        (_S_DIFF,),
    ),
    _Plant(
        "git-alternative-dropped",
        _skill_fixture(
            after_later_run=_swap(
                _SOURCE_LINE,
                "; a tracked document may use git instead when git holds that version",
                "",
            )
        ),
        (_S_GIT, _S_WHEN),
    ),
    _Plant(
        "git-condition-dropped",
        _skill_fixture(
            after_later_run=_swap(_SOURCE_LINE, " when git holds that version", "")
        ),
        (_S_WHEN,),
    ),
    _Plant(
        "in-the-later-run-paragraph",
        _skill_fixture(
            later_run=_LATER_RUN + "\n" + _SOURCE, after_later_run=_DIFF_OLD
        ),
        _SOURCE_PARTS,
    ),
    _Plant(
        "as-a-paragraph-of-its-own",
        _skill_fixture(after_later_run=_DIFF_OLD + "\n\n" + _SOURCE),
        _SOURCE_PARTS,
    ),
    _Plant(
        "in-step-five",
        _skill_fixture(after_later_run=_DIFF_OLD, step_five=_SOURCE),
        _SOURCE_PARTS,
    ),
    _Plant(
        "diff-paragraph-absent",
        _skill_fixture(after_later_run=_SOURCE),
        (f"0 paragraphs of Step 4 start {_DIFF_LEAD!r}",),
    ),
    _Plant(
        "diff-paragraph-repeated",
        _skill_fixture(after_later_run=_DIFF + "\n\n" + _DIFF),
        (f"2 paragraphs of Step 4 start {_DIFF_LEAD!r}",),
    ),
    # The whole paragraph, sentence included, run on to the later-run paragraph: its lead stands
    # after other words there, so only a match that reads from the start of a paragraph flags it.
    _Plant(
        "merged-into-the-later-run-paragraph",
        _skill_fixture(later_run=_LATER_RUN + "\n" + _DIFF),
        (f"0 paragraphs of Step 4 start {_DIFF_LEAD!r}",),
    ),
)

_CAP_RUNS = _CAP_PHRASES[0]
_CAP_CLASSES = _CAP_PHRASES[1]
_CAP_CLASSES_IN_TEXT = (
    "a factual error, a contradiction, a\nmissing item or an unsafe statement"
)

_CAP_PLANTS: tuple[_Plant, ...] = (
    _Plant("shipped-shape", _skill_fixture(after_later_run=_DIFF)),
    _Plant("re-wrapped", _skill_fixture(cap=_re_wrapped(_CAP_PARAGRAPH, 28))),
    _Plant(
        "cap-dropped",
        _skill_fixture(cap=_swap(_CAP_PARAGRAPH, f"**{_CAP_RUNS}**", "**a cap**")),
        (_CAP_RUNS,),
    ),
    _Plant(
        "classes-dropped",
        _skill_fixture(cap=_swap(_CAP_PARAGRAPH, _CAP_CLASSES_IN_TEXT, "some errors")),
        (_CAP_CLASSES,),
    ),
    _Plant(
        "classes-repeated-in-step-four",
        _skill_fixture(after_later_run=f"Only for {_CAP_CLASSES}."),
        (_CAP_CLASSES,),
    ),
    _Plant(
        "cap-moved-out-of-its-section",
        _skill_fixture(
            cap=_swap(_CAP_PARAGRAPH, f"**{_CAP_RUNS}**", "**a cap**"),
            step_five=f"The cap: {_CAP_RUNS}.",
        ),
        (_CAP_RUNS,),
    ),
)

# One planted restatement per cap word, each holding that word and no other, one in capitals and a
# near-miss: a word dropped from `_CAP_WORDS`, or a check that reads case, must be seen to fail.
_CAP_WORD_PLANTS: tuple[_Plant, ...] = (
    _Plant("at-most-two", "Run it at most two more times.", ("'at most two'",)),
    _Plant("twice", "Run it twice.", ("'twice'",)),
    _Plant("two-runs", "Allow two runs per document.", ("'two runs'",)),
    _Plant("factual-error", "Edit only for a factual error.", ("'factual error'",)),
    _Plant("missing-item", "Edit only for a missing item.", ("'missing item'",)),
    _Plant(
        "unsafe-statement",
        "Edit only for an unsafe statement.",
        ("'unsafe statement'",),
    ),
    _Plant("in-capitals", "Twice is the limit.", ("'twice'",)),
    _Plant("near-miss", "Edit only for a factual claim or a missing page."),
)

# The two scanned sections of SKILL.md, disjoint, and with one line in both.
_OVERLAP_PLANTS: tuple[_Plant, ...] = (
    _Plant("disjoint-sections", _skill_fixture()),
    _Plant(
        "one-shared-line",
        _skill_fixture(after_later_run="---"),
        ("judged by two rules: '---'",),
    ),
)

_EXAMPLE_FIX = _LABEL + _GOOD_NEW

_EXAMPLE_PLANTS: tuple[_Plant, ...] = (
    _Plant("quoted-replacement-text", _format_fixture(_LABEL + _FIX_NEW, _EXAMPLE_FIX)),
    _Plant(
        "quote-re-wrapped",
        _format_fixture(_LABEL + _FIX_NEW, _re_wrapped(_EXAMPLE_FIX, 30, "  ")),
    ),
    _Plant(
        "old-example",
        _format_fixture(_LABEL + _FIX_NEW, _LABEL + _GOOD_OLD),
        ("holds no quoted replacement text",),
    ),
    _Plant(
        "quote-too-short",
        _format_fixture(_LABEL + _FIX_NEW, _LABEL + 'Design: "retry".'),
        ("holds no quoted replacement text",),
    ),
    _Plant(
        "two-short-quotes-with-words-between",
        _format_fixture(
            _LABEL + _FIX_NEW,
            _LABEL
            + 'Design: "retry it." Task acceptance criteria, new line: "retry 429s."',
        ),
        ("holds no quoted replacement text",),
    ),
)

# Each table is stated in numbers: a plant dropped from a table is only one test fewer, which
# nothing else counts.
_PLANT_COUNTS = {
    "fix field": 11,
    "diff check": 16,
    "version source": 17,
    "run cap": 6,
    "good example": 5,
    "cap words": 8,
    "overlap": 2,
}
_FORMAT_FENCE_LINES = 6


def _assert_verdict(plant: _Plant, problems: list[str]) -> None:
    if not plant.flagged:
        assert not problems, f"{plant.label}: a near-miss was flagged: {problems}"
        return
    unnamed = [
        fragment
        for fragment in plant.flagged
        if not any(fragment in problem for problem in problems)
    ]
    assert not unnamed, f"{plant.label}: not flagged for {unnamed}; it said {problems}"
    assert len(problems) == len(plant.flagged), (
        f"{plant.label}: flagged for more than the planted defect: {problems}"
    )


@pytest.mark.parametrize("plant", _FIX_PLANTS, ids=[p.label for p in _FIX_PLANTS])
def test_the_fix_field_check_tells_the_old_shape_from_a_near_miss(
    plant: _Plant,
) -> None:
    _assert_verdict(plant, _fix_field_problems(plant.text, "planted"))


@pytest.mark.parametrize("plant", _DIFF_PLANTS, ids=[p.label for p in _DIFF_PLANTS])
def test_the_diff_check_check_tells_the_old_shape_from_a_near_miss(
    plant: _Plant,
) -> None:
    _assert_verdict(plant, _diff_check_problems(plant.text, "planted"))


@pytest.mark.parametrize("plant", _SOURCE_PLANTS, ids=[p.label for p in _SOURCE_PLANTS])
def test_the_source_check_tells_a_stated_source_from_a_missing_one(
    plant: _Plant,
) -> None:
    _assert_verdict(plant, _source_problems(plant.text, "planted"))


def test_the_source_check_fails_loudly_when_step_four_is_missing() -> None:
    with pytest.raises(AssertionError, match="no heading"):
        _source_problems("# Plan Critic\n\n## Review Process\n", "planted")


@pytest.mark.parametrize("plant", _CAP_PLANTS, ids=[p.label for p in _CAP_PLANTS])
def test_the_run_cap_check_tells_a_kept_cap_from_a_changed_one(plant: _Plant) -> None:
    _assert_verdict(plant, _run_cap_problems(plant.text, "planted"))


@pytest.mark.parametrize(
    "plant", _EXAMPLE_PLANTS, ids=[p.label for p in _EXAMPLE_PLANTS]
)
def test_the_example_check_tells_replacement_text_from_a_description(
    plant: _Plant,
) -> None:
    _assert_verdict(plant, _good_example_problems(plant.text, "planted"))


@pytest.mark.parametrize(
    "plant", _CAP_WORD_PLANTS, ids=[p.label for p in _CAP_WORD_PLANTS]
)
def test_the_restated_cap_check_names_each_cap_word(plant: _Plant) -> None:
    _assert_verdict(plant, _restated_cap(_fold(plant.text)))


def test_every_cap_word_has_a_planted_restatement_and_one_is_in_capitals() -> None:
    planted = {fragment for plant in _CAP_WORD_PLANTS for fragment in plant.flagged}
    unplanted = [word for word in _CAP_WORDS if f"{word!r}" not in planted]
    assert not unplanted, f"cap words with no planted restatement: {unplanted}"
    in_capitals = [
        plant.label
        for plant in _CAP_WORD_PLANTS
        if plant.flagged and not any(word in plant.text for word in _CAP_WORDS)
    ]
    assert in_capitals, "no plant holds a cap word only in capitals"


def test_the_verdict_helper_enforces_each_of_its_three_rules() -> None:
    """The helper every planted table goes through: a near-miss must be clean, a planted defect
    must be named, and nothing may be flagged beyond it."""
    _assert_verdict(_Plant("near-miss", ""), [])
    _assert_verdict(_Plant("defect", "", ("alpha",)), ["a problem with alpha"])
    with pytest.raises(AssertionError, match="a near-miss was flagged"):
        _assert_verdict(_Plant("near-miss", ""), ["a problem"])
    with pytest.raises(AssertionError, match="not flagged for"):
        _assert_verdict(_Plant("defect", "", ("alpha",)), ["a problem with beta"])
    with pytest.raises(AssertionError, match="more than the planted defect"):
        _assert_verdict(
            _Plant("defect", "", ("alpha",)),
            ["a problem with alpha", "an extra problem"],
        )


def test_the_scan_surface_is_stated_in_numbers() -> None:
    assert len(_SURFACE) == 2
    assert len({path.resolve() for path in _SURFACE}) == 2
    for path in _SURFACE:
        assert path.is_file(), f"{path} is not a file"
        assert _text(path).strip(), f"{path} is empty"
    section = _section(_text(_FORMAT), "## Finding Format", "finding-format.md")
    fences = sum(_is_fence(line) for line in section.split("\n"))
    assert fences == _FORMAT_FENCE_LINES, (
        f"the Finding Format section holds {fences} fence lines, expected "
        f"{_FORMAT_FENCE_LINES}: the template, the good example and the bad one"
    )


def test_the_planted_tables_keep_their_stated_size() -> None:
    sizes = {
        "fix field": len(_FIX_PLANTS),
        "diff check": len(_DIFF_PLANTS),
        "version source": len(_SOURCE_PLANTS),
        "run cap": len(_CAP_PLANTS),
        "good example": len(_EXAMPLE_PLANTS),
        "cap words": len(_CAP_WORD_PLANTS),
        "overlap": len(_OVERLAP_PLANTS),
    }
    assert sizes == _PLANT_COUNTS, f"a planted table changed size: {sizes}"
    tables = (
        ("fix field", _FIX_PLANTS),
        ("diff check", _DIFF_PLANTS),
        ("version source", _SOURCE_PLANTS),
        ("run cap", _CAP_PLANTS),
        ("good example", _EXAMPLE_PLANTS),
        ("cap words", _CAP_WORD_PLANTS),
        ("overlap", _OVERLAP_PLANTS),
    )
    for name, table in tables:
        labels = [plant.label for plant in table]
        assert len(labels) == len(set(labels)), f"{name}: a label repeats: {labels}"


def test_the_two_sections_of_skill_md_that_are_scanned_do_not_overlap() -> None:
    problems = _overlap_problems(_text(_SKILL), "SKILL.md")
    assert not problems, "; ".join(problems)


@pytest.mark.parametrize(
    "plant", _OVERLAP_PLANTS, ids=[p.label for p in _OVERLAP_PLANTS]
)
def test_the_overlap_check_tells_a_shared_line_from_disjoint_sections(
    plant: _Plant,
) -> None:
    _assert_verdict(plant, _overlap_problems(plant.text, "planted"))


def test_the_slicers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "### An aside on ## Alpha",
            "decoy body",
            "## Alpha",
            "first body",
            "```",
            "# a comment inside a fence is not a heading",
            "Resolution: inside the fence",
            "```",
            "after the fence",
            "### Alpha child",
            "child body",
            "## Beta",
            "second body",
        ]
    )
    alpha = _section(planted, "## Alpha", "planted")
    assert alpha.startswith("## Alpha\nfirst body"), alpha
    assert "after the fence" in alpha and "child body" in alpha
    assert "second body" not in alpha
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "## Gamma", "planted")

    assert [_fold(p) for p in _paragraphs("a\nb\n\n\n c\n")] == ["a b", "c"]

    fenced = "intro\n```\nfirst block\n```\ntext\nMARKER here\n```\nsecond block\n```\n"
    assert _fenced_block_after(fenced, "", "planted") == "first block"
    assert _fenced_block_after(fenced, "MARKER", "planted") == "second block"
    with pytest.raises(AssertionError, match="no fenced block"):
        _fenced_block_after(fenced, "ABSENT", "planted")
    with pytest.raises(AssertionError, match="no fenced block"):
        _fenced_block_after("MARKER\n```\nnever closed\n", "MARKER", "planted")

    block = (
        "Problem: a, and the Resolution: field below says how\n"
        "Resolution: first line\n  a continuation\ncolumn zero too\n"
        "Alternative: b\n\nResolution: a later one"
    )
    assert _field(block, "Resolution:", "planted") == (
        "Resolution: first line\n  a continuation\ncolumn zero too"
    )
    stray = (
        "Resolution: first line\n\nA stray paragraph, not part of the field.\n"
        "Alternative: b"
    )
    assert _field(stray, "Resolution:", "planted") == "Resolution: first line"
    with pytest.raises(AssertionError, match="no field"):
        _field(block, "Reasoning:", "planted")
    assert _fold("a\n  b\t\tc\n\n d") == "a b c d"
