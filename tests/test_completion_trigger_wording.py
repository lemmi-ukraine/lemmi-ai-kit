"""The review and the lessons run at every completion event, not after a large task only.

`post-task-review` told the model to fire "after completing any major task (3+ files modified
...)". The AGENTS.md checklist item and bullet that `kit-setup` seeds said the same, the brief
contract of `orchestrate` handed that bound to every worker it briefed, and further places
bounded the review in their own words: the gate levels of a phased spec, the close of a spec,
and the close of a flow mapping. `task-learnings` had the same shape ("at the end of every
qualifying task"), so a plan, an audit, or a stop at a gate never qualified for a lessons run.

What the text says now: the review runs at every completion event (a finished task of any
size, a precondition stop, a gate report, a hand-off); a close with no changed files still runs
every step; a workflow skill is never the caller, so the review is its own top-level step after
the workflow ends, and at a phase gate only Step 9 is run inline, as a step of the gate; a stage
report may still defer a gate, but only by naming it. The lessons run at the close of every
task and at each of those events.

Each place is one `_Place`: where it is, what it must say, which retired wording must be gone,
and the text it replaced. A place asserts each sentence it gained WHOLE, so a clause cannot be
dropped from a sentence while the rest of it still matches. A bullet or an item is read whole,
whatever its continuation lines look like, so a re-wrap cannot cut it short.
`test_every_place_check_fails_on_the_text_it_replaced` fires every check at the old text and
expects each one to report it, except the few a place lists as kept or preventive, so a pattern
that could never fail cannot stand in for the sentence. `test_the_scan_surface_is_stated_in_numbers`
asserts the size of the scan, and the sweep scans the same files the places live in, so neither
can shrink without a failure.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

Needle = str | re.Pattern[str]


class _Check(NamedTuple):
    label: str
    needle: Needle


class _Place(NamedTuple):
    """One spot of shipped text that states the rule, and the text it replaced.

    `kept` lists the labels of required checks that the old text satisfies as well (the wording
    the place had already), and `preventive` the labels of retired checks the old text never
    carried (they guard against a wording that has not been written yet). Every other check
    must report the old text.
    """

    name: str
    path: str
    locate: Callable[[str], str]
    required: tuple[_Check, ...]
    old: str
    retired: tuple[_Check, ...] = ()
    kept: tuple[str, ...] = ()
    preventive: tuple[str, ...] = ()


# --- reading a place out of a file ------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s")
_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_REPO_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _folded(text: str) -> str:
    """Bold marks dropped and every run of whitespace folded to one space, so a re-wrapped line
    or a re-emphasised word is not a different sentence."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _found(folded: str, needle: Needle) -> bool:
    if isinstance(needle, str):
        return needle in folded
    return needle.search(folded) is not None


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or
    a higher level. A `#` line inside a fenced block is not a heading. Empty when none matches."""
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


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _list_item(text: str, lead: str) -> str:
    """The first line that starts with `lead` and the lines that belong to it: every line after
    it up to the next heading, up to the next list marker at the same or a shallower indent, and,
    after a blank line, up to the next line that is not indented. A continuation line stays in
    whether it is indented or sits in column 0, so a re-wrapped item is read whole. Empty when no
    line starts with `lead`."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if not line.startswith(lead):
            continue
        item = [line]
        after_blank = False
        for follow in lines[index + 1 :]:
            if not follow.strip():
                item.append(follow)
                after_blank = True
                continue
            shallow = _indent(follow) <= _indent(line)
            if _HEADING.match(follow) or (
                shallow and (_MARKER.match(follow) is not None or after_blank)
            ):
                break
            item.append(follow)
            after_blank = False
        return "\n".join(item)
    return ""


def _paragraph(text: str, needle: str) -> str:
    return next((b for b in re.split(r"\n\s*\n", text) if needle in b), "")


def _description(text: str) -> str:
    """The `description:` value of the frontmatter, or an empty string."""
    block = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if block is None:
        return ""
    lines = block.group(1).split("\n")
    start = next(
        (i for i, row in enumerate(lines) if row.startswith("description:")), -1
    )
    if start < 0:
        return ""
    value = [lines[start].split(":", 1)[1].strip().lstrip(">")]
    for follow in lines[start + 1 :]:
        if follow and not follow.startswith((" ", "\t")):
            break
        value.append(follow)
    return "\n".join(value)


def _before_first_subheading(text: str) -> str:
    kept: list[str] = []
    for line in text.split("\n")[1:]:
        if line.startswith("### "):
            break
        kept.append(line)
    return "\n".join(kept)


def _section_of(heading: str) -> Callable[[str], str]:
    return lambda text: _section(text, heading)


def _item_of(lead: str) -> Callable[[str], str]:
    return lambda text: _list_item(text, lead)


def _paragraph_of(needle: str) -> Callable[[str], str]:
    return lambda text: _paragraph(text, needle)


def _then(*steps: Callable[[str], str]) -> Callable[[str], str]:
    def run(text: str) -> str:
        for step in steps:
            text = step(text)
        return text

    return run


def _gaps(place: _Place, text: str) -> list[str]:
    """What the place lacks or still carries, in `text`; an empty list is a pass."""
    region = place.locate(text)
    if not region.strip():
        return [f"the place is missing from {place.path}"]
    flat = _folded(region)
    gaps = [f"missing: {c.label}" for c in place.required if not _found(flat, c.needle)]
    gaps += [
        f"retired wording still there: {c.label}"
        for c in place.retired
        if _found(flat, c.needle)
    ]
    return gaps


# --- the wording --------------------------------------------------------------------------------

_TRIGGER = (
    "every completion event: a finished task of any size, a precondition stop, "
    "a gate report, a hand-off"
)
_NO_DIFF = (
    "A close with no changed files still runs every step, reading the report's claims "
    "where there is no diff, and always Step 9."
)
_TOP_LEVEL = "own top-level step after that workflow ends"
_NEVER_NESTED = "a workflow skill is never invoked from inside another"
_INSIDE_A_WORKFLOW = (
    "Inside a workflow skill, run it as its own top-level step after that workflow ends "
    f"({_NEVER_NESTED})."
)
_REVIEW_BULLET = f"- Run the full post-task review at {_TRIGGER}."
_STEP_LIST = (
    "Step 0 through Step 9: blast radius (0), code review (1–6), documentation impact (7), "
    "learnings extraction (8), close self-challenge (9)."
)

_ACTIVATION_LEAD = (
    "Run this review at every completion event, whatever the task's size or kind:"
)
_ACTIVATION_FINISHED = (
    "- A task of any size or kind is finished "
    "(code, a plan, an audit, a report, a migration)"
)
_ACTIVATION_STOP = "- A task stops at a precondition it could not meet"
_ACTIVATION_GATE = (
    "- A gate report or a hand-off is about to be written; inside a workflow skill, the "
    f"review runs as its own top-level step after that workflow ends, since {_NEVER_NESTED}"
)
_STAGED_POINTER = (
    "A stage report may defer a gate only as the staged-delivery note under Important "
    "Notes allows."
)
_STAGED_DELIVERY = (
    "Treat each approved stage as a completion for gate purposes, or say in the stage "
    "report which gates are deferred and to when."
)

# What the three places that speak of a phase gate must all say: the first fragment is how
# Step 9 runs at the gate, the second is where the full review runs. Compared in lower case,
# since one place carries them inside a sentence and another opens a sentence with them.
_PHASE_GATE_INLINE = "runs inline, as a step of the gate"
_FULL_REVIEW_AFTER = (
    "the full review runs as its own top-level step after the workflow ends"
)
_PHASE_GATE_SENTENCE = (
    f"At a phase gate inside a workflow, Step 9 {_PHASE_GATE_INLINE}; "
    f"{_FULL_REVIEW_AFTER}."
)
_SPEC_GATE_PARAGRAPH = (
    "Every gate report is a completion event: whatever the level, Step 9 of "
    "`post-task-review` runs inline, as a step of the gate, before the report is written, "
    "and a step the level leaves out is named in the report with the gate that will run it; "
    f"{_FULL_REVIEW_AFTER}."
)
_PHASED_GATE_PARAGRAPH = (
    "Every gate report is a completion event: whatever the level, Step 9 of the "
    "`post-task-review` skill (the close self-challenge) runs inline, as a step of the gate, "
    "before the report is written, and a step the level leaves out is named in the report "
    "with the gate that will run it, the final phase's Full gate; "
    f"{_FULL_REVIEW_AFTER}."
)
_PHASE_GATE_PLACES = (
    "review-activation-list",
    "spec-gate-levels",
    "phased-gate-report-rule",
)

_SPEC_CLOSING_PAREN = (
    "(mandatory at every completion event, a Small task closed by direct implementation "
    "included; a spec gets the full pass)"
)
_FULL_GATE_STEP_0 = "- Step 0: dependency and blast radius, before the steps below"
_FULL_GATE_STEP_9 = "- Step 9: close self-challenge, run last"

_SIZE_LIMIT = "3+ files"
_MAJOR_TASK = re.compile(r"major tasks?", re.IGNORECASE)
_DEFERRAL_BAN = _Check(
    "a ban on deferral that the staged-delivery note contradicts",
    re.compile(r"never defer|no exceptions?|without exception", re.IGNORECASE),
)

_POST_TASK_REVIEW = "plugins/core/skills/post-task-review/SKILL.md"
_SPEC_DRIVEN_DEV = "plugins/core/skills/spec-driven-dev/SKILL.md"
_PHASED = "plugins/core/skills/spec-driven-dev/references/phased-execution.md"
_FLOW_MAPPING = "plugins/core/skills/flow-mapping/SKILL.md"
_TEMPLATE = "plugins/core/src/lemmi_ai_kit/assets/templates/AGENTS.md"
_KIT_AGENTS = "AGENTS.md"
_ORCHESTRATE = "plugins/orchestration/skills/orchestrate/SKILL.md"
_TASK_LEARNINGS = "plugins/core/skills/task-learnings/SKILL.md"


# --- the text each place carried before ---------------------------------------------------------

_OLD_REVIEW_DESCRIPTION = """---
name: post-task-review
metadata:
  type: workflow
description: >
  Comprehensive post-task review including code review, convention compliance, documentation
  impact analysis, and learnings extraction. Extends the existing task-completion-review
  process with two new mandatory steps. Use after completing any major task (3+ files
  modified, new feature, significant refactoring, or spec task completion).
---
"""

_OLD_REVIEW_ACTIVATION = """## When This Skill Activates

Run this review when any of these conditions are met:

- A new feature or significant functionality was implemented
- Refactoring touched 3 or more files
- A spec-driven development task was completed
- A bug fix revealed a systemic issue
- The human explicitly requests a review
- Any task that created or modified database migrations

## Review Pipeline
"""

_OLD_SPEC_CLOSING = """## Closing a Spec — self-review, then retire

A spec is not finished when its last task is ticked. Two steps close it, in order:

1. **Self-review — `post-task-review`** (mandatory for Medium and Large; the full pass). Its
   step 4 self-challenge, step 7 documentation-impact sweep and step 9 CLOSE self-challenge (a
   separate, later pass than step 4) are what catch the defects the
   implementation pass cannot see, because they check the work against the *approved scenarios* and
   against every doc that cites the changed files. Phased specs run the gate levels in
   § Quality Gate Levels; the final phase always gets the Full pass.

2. **Retire — `initiative-cleanup`** (approval-gated, destructive).
"""

_OLD_SPEC_GATE_LEVELS = """### Quality Gate Levels

| Level | When to Use | Steps |
|-------|-------------|-------|
| **Light** | Simple phases (2–3 tasks, single layer) | Lint + quick self-review |
| **Standard** | Default for most phases | Steps 1–6 of post-task-review |
| **Full** | Final phase, or phases with cross-feature impact | Full post-task-review, every step |

### Context Handoff Rules
"""

_OLD_PHASED_GATES = """## Quality Gate Levels

### Light Gate

Use for simple, low-risk phases (single layer, 2–3 tasks, no cross-feature impact).

Steps:
1. Run `uv run ruff check` on all modified files
2. Check lint/type diagnostics on all modified files
3. Quick self-review: any obvious issues, missing error handling, broken imports?
4. Fix any issues found

### Standard Gate

Use as the default for most phases.

Steps: Follow steps 1–6 of the `post-task-review` skill:
1. High-level conceptual review
6. Run linting and diagnostics

### Full Gate

Use for the final phase, or for phases with cross-feature impact or architectural decisions.

Steps: Follow the complete process from the `post-task-review` skill, Step 0 through Step 9:
- Steps 1–6: code review and convention compliance
- Step 7: documentation impact analysis
- Step 8: learnings extraction
"""

_OLD_FLOW_CLOSE = """## F. Validate and close

Return output paths, pinned revision, evidence limits, actual gate results and
outstanding register IDs. Run Core's post-task-review for major mapping work.
Do not claim a structural pass proves runtime truth, commit/push without user
authorization, or leave actionable findings only in temporary session notes.
"""

_OLD_TEMPLATE_AGENTS = """### Task completion checklist (mandatory)
When a task is complete, ALWAYS perform these steps before considering it done:
1. **Post-task review** (major tasks: 3+ files, new feature, spec completion) — Run the full review, Step 0 through Step 9: blast radius (0), code review (1–6), documentation impact (7), learnings extraction (8), close self-challenge (9). The `post-task-review` skill is the authority on its own step list; do not restate a step COUNT here, it goes stale.
2. **Learnings extraction** (all tasks) — Extract project-level findings and append to `.ai/learnings.md`. See the `task-learnings` skill.

### Post-task review
Uses: post-task-review (workflow), task-learnings (task), commit-message (task)
- Run the full post-task review for all major tasks (3+ files modified, new features, spec completions).
- Steps 1–6: code review and convention compliance (see the `post-task-review` skill).
"""

_OLD_KIT_AGENTS = """### Task completion checklist (mandatory)
When a task is complete, ALWAYS perform these steps before considering it done:
1. **Post-task review** (major tasks: 3+ files, new feature, spec completion) — Run the full 8-step review: code review (1–6), documentation impact (7), learnings extraction (8). See the `post-task-review` skill.
2. **Learnings extraction** (all tasks) — Extract project-level findings and append to `.ai/learnings.md`. See the `task-learnings` skill.

### Post-task review
Uses: post-task-review (workflow), task-learnings (task), commit-message (task)
- Run the 8-step review for all major tasks (3+ files modified, new features, spec completions).
- Steps 1–6: code review and convention compliance (see the `post-task-review` skill).
"""

_OLD_ORCHESTRATE_BRIEF_LINE = """5. **The completion gates ride in the DoD, run BEFORE the handoff, and operator questions are
   self-addressed.** An implementation brief's definition of done includes the AGENTS.md
   task-completion checklist (post-task-review for 3+ files, learnings extraction) — **and the brief
   must state that it runs before the worker writes its return handoff, not after.** The handoff is
   the only thing you will read; one written first carries whatever the review would have corrected,
"""

_OLD_LEARNINGS_DESCRIPTION = """---
name: task-learnings
user-invocable: false
metadata:
  type: task
description: >
  Extract and record project learnings after task completion. Captures architecture
  decisions, pitfalls, patterns, and convention gaps discovered during implementation.
  Automatically updates .ai/learnings.md and relevant project rules. Use after completing
  any coding task, bug fix, refactoring, or when the AI discovers something non-obvious
  about the project.
---
"""

_OLD_LEARNINGS_ACTIVATION = """## When This Skill Activates

Run the learnings extraction process when any of these occur:

- A coding task, bug fix, or refactoring is completed
- A surprising or non-obvious behavior is discovered in the codebase
- The human corrects the AI's approach or assumption

## Learnings Extraction Process

Follow these steps in order at the end of every qualifying task:

### Step 0: Measure This Session (gated)
"""


# --- the places ---------------------------------------------------------------------------------

_REVIEW_PLACES: tuple[_Place, ...] = (
    _Place(
        name="review-description",
        path=_POST_TASK_REVIEW,
        locate=_description,
        required=(_Check("the trigger sentence", f"Use at {_TRIGGER}."),),
        retired=(
            _Check("the two new mandatory steps", "two new mandatory steps"),
            _Check("the 3+ files limit", _SIZE_LIMIT),
            _Check("any major task", _MAJOR_TASK),
            _Check("significant refactoring", "significant refactoring"),
        ),
        old=_OLD_REVIEW_DESCRIPTION,
    ),
    _Place(
        name="review-activation-list",
        path=_POST_TASK_REVIEW,
        locate=_section_of("## When This Skill Activates"),
        required=(
            _Check("the lead-in names every completion event", _ACTIVATION_LEAD),
            _Check("a finished task of any size or kind", _ACTIVATION_FINISHED),
            _Check("a stop at a precondition", _ACTIVATION_STOP),
            _Check(
                "a gate report or a hand-off, and the review as its own top-level step",
                _ACTIVATION_GATE,
            ),
            _Check(
                "a close with no changed files runs every step and Step 9", _NO_DIFF
            ),
            _Check("the pointer to the staged-delivery note", _STAGED_POINTER),
            _Check(
                "at a phase gate Step 9 runs inline and the full review runs after the workflow",
                _PHASE_GATE_SENTENCE,
            ),
        ),
        retired=(
            _Check("the 3-or-more-files condition", "3 or more files"),
            _Check("the old lead-in", "when any of these conditions are met"),
            _DEFERRAL_BAN,
        ),
        old=_OLD_REVIEW_ACTIVATION,
        preventive=(_DEFERRAL_BAN.label,),
    ),
    _Place(
        name="spec-closing-item",
        path=_SPEC_DRIVEN_DEV,
        locate=_then(_section_of("## Closing a Spec"), _item_of("1. **Self-review")),
        required=(
            _Check(
                "mandatory at every completion event, a Small task included",
                _SPEC_CLOSING_PAREN,
            ),
        ),
        retired=(
            _Check("mandatory for Medium and Large", "mandatory for Medium and Large"),
        ),
        old=_OLD_SPEC_CLOSING,
    ),
    _Place(
        name="spec-gate-levels",
        path=_SPEC_DRIVEN_DEV,
        locate=_section_of("### Quality Gate Levels"),
        required=(
            _Check(
                "a gate report is a completion event, Step 9 runs inline, the full "
                "review runs after the workflow",
                _SPEC_GATE_PARAGRAPH,
            ),
        ),
        old=_OLD_SPEC_GATE_LEVELS,
    ),
    _Place(
        name="phased-full-gate-steps",
        path=_PHASED,
        locate=_section_of("### Full Gate"),
        required=(
            _Check("Step 0 is listed with its body", _FULL_GATE_STEP_0),
            _Check("Step 9 is listed with its body", _FULL_GATE_STEP_9),
        ),
        old=_OLD_PHASED_GATES,
    ),
    _Place(
        name="phased-gate-report-rule",
        path=_PHASED,
        locate=_section_of("## Quality Gate Levels"),
        required=(
            _Check(
                "a gate report is a completion event, Step 9 runs inline, the full "
                "review runs after the workflow",
                _PHASED_GATE_PARAGRAPH,
            ),
        ),
        old=_OLD_PHASED_GATES,
    ),
    _Place(
        name="flow-mapping-close",
        path=_FLOW_MAPPING,
        locate=_then(
            _section_of("## F. Validate and close"), _paragraph_of("post-task-review")
        ),
        required=(
            _Check(
                "the trigger sentence",
                "Run Core's post-task-review at every completion event of mapping "
                "work, whatever its size.",
            ),
        ),
        retired=(_Check("major mapping work", "major mapping work"),),
        old=_OLD_FLOW_CLOSE,
    ),
    _Place(
        name="template-checklist-item",
        path=_TEMPLATE,
        locate=_item_of("1. **Post-task review**"),
        required=(
            _Check("the trigger", f"({_TRIGGER})"),
            _Check("Step 0 through Step 9 is kept", "Step 0 through Step 9"),
        ),
        retired=(
            _Check("major tasks", _MAJOR_TASK),
            _Check("the 3+ files limit", _SIZE_LIMIT),
        ),
        old=_OLD_TEMPLATE_AGENTS,
        kept=("Step 0 through Step 9 is kept",),
    ),
    _Place(
        name="template-review-bullet",
        path=_TEMPLATE,
        locate=_then(_section_of("### Post-task review"), _item_of("- Run the ")),
        required=(
            _Check("the trigger sentence", _REVIEW_BULLET),
            _Check(
                "a close with no changed files runs every step and Step 9", _NO_DIFF
            ),
            _Check(
                "inside a workflow skill, the review is its own top-level step",
                _INSIDE_A_WORKFLOW,
            ),
        ),
        retired=(
            _Check("major tasks", _MAJOR_TASK),
            _Check("the 3+ files limit", _SIZE_LIMIT),
        ),
        old=_OLD_TEMPLATE_AGENTS,
    ),
    _Place(
        name="kit-checklist-item",
        path=_KIT_AGENTS,
        locate=_item_of("1. **Post-task review**"),
        required=(
            _Check("the trigger", f"({_TRIGGER})"),
            _Check("the skill's Step 0 through Step 9, each step named", _STEP_LIST),
        ),
        retired=(
            _Check("major tasks", _MAJOR_TASK),
            _Check("the 3+ files limit", _SIZE_LIMIT),
            _Check("the 8-step count", "8-step"),
        ),
        old=_OLD_KIT_AGENTS,
    ),
    _Place(
        name="kit-review-bullet",
        path=_KIT_AGENTS,
        locate=_then(_section_of("### Post-task review"), _item_of("- Run the ")),
        required=(
            _Check("the trigger sentence", _REVIEW_BULLET),
            _Check(
                "a close with no changed files runs every step and Step 9", _NO_DIFF
            ),
            _Check(
                "inside a workflow skill, the review is its own top-level step",
                _INSIDE_A_WORKFLOW,
            ),
        ),
        retired=(
            _Check("major tasks", _MAJOR_TASK),
            _Check("the 3+ files limit", _SIZE_LIMIT),
            _Check("the 8-step count", "8-step"),
        ),
        old=_OLD_KIT_AGENTS,
    ),
    _Place(
        name="orchestrate-brief-line",
        path=_ORCHESTRATE,
        locate=_item_of("5. **The completion gates ride in the DoD"),
        required=(
            _Check(
                "post-task-review at every completion event, then learnings extraction",
                f"(post-task-review at {_TRIGGER}; and learnings extraction)",
            ),
        ),
        retired=(
            _Check("post-task-review for 3+ files", "post-task-review for 3+ files"),
        ),
        old=_OLD_ORCHESTRATE_BRIEF_LINE,
    ),
)

_LESSONS_PLACES: tuple[_Place, ...] = (
    _Place(
        name="task-learnings-description",
        path=_TASK_LEARNINGS,
        locate=_description,
        required=(
            _Check(
                "the close of every task, whatever its kind or size",
                "Use at the close of every task, whatever its kind or size (code, "
                "documentation, a plan, an audit, a report), at a stop or hand-off before "
                "it, and when the AI discovers something non-obvious about the project.",
            ),
            _Check("the description says every task", "every task"),
        ),
        retired=(
            _Check(
                "any coding task, bug fix, refactoring",
                "any coding task, bug fix, refactoring",
            ),
        ),
        old=_OLD_LEARNINGS_DESCRIPTION,
    ),
    _Place(
        name="task-learnings-first-trigger",
        path=_TASK_LEARNINGS,
        locate=_then(_section_of("## When This Skill Activates"), _item_of("- ")),
        required=(
            _Check(
                "a task of any kind or size, or a stop at a gate or hand-off",
                "- A task of any kind or size is completed, or stops at a gate or a hand-off",
            ),
        ),
        retired=(
            _Check(
                "a coding task, bug fix, or refactoring is completed",
                "A coding task, bug fix, or refactoring is completed",
            ),
        ),
        old=_OLD_LEARNINGS_ACTIVATION,
    ),
    _Place(
        name="task-learnings-opening",
        path=_TASK_LEARNINGS,
        locate=_then(
            _section_of("## Learnings Extraction Process"), _before_first_subheading
        ),
        required=(
            _Check(
                "the close of every task and each event above",
                "Follow these steps in order at the close of every task and at each "
                "event above:",
            ),
            _Check(
                "a run that finds nothing is a valid result",
                "A run that finds nothing new is a valid result, not a skipped step: say "
                "so in one line.",
            ),
            _Check(
                "Step 8 of the review is this run",
                "When `post-task-review` runs, its Step 8 is this run.",
            ),
            _Check(
                "only a candidate that waits on an answer may wait",
                "At a stop, a candidate that waits on an answer is not yet a finding and "
                "may wait if the report names it",
            ),
            _Check(
                "a settled finding is appended now",
                "a finding already settled is appended now",
            ),
            _Check(
                "Step 5's append rule stands",
                "Step 5's rule that the append itself is never deferred stands",
            ),
        ),
        retired=(_Check("every qualifying task", "every qualifying task"),),
        old=_OLD_LEARNINGS_ACTIVATION,
    ),
)

_PLACES = (*_REVIEW_PLACES, *_LESSONS_PLACES)

# The files this change touches. The sweep below reads every one of them whole; the places
# above are located inside them. A place in a ninth file is a decision made here.
_SURFACE: tuple[str, ...] = (
    _POST_TASK_REVIEW,
    _SPEC_DRIVEN_DEV,
    _PHASED,
    _FLOW_MAPPING,
    _TEMPLATE,
    _KIT_AGENTS,
    _ORCHESTRATE,
    _TASK_LEARNINGS,
)

_RETIRED_EVERYWHERE: tuple[_Check, ...] = (
    _Check("a 3+ files limit", re.compile(r"3\+ files", re.IGNORECASE)),
    _Check("a 3-or-more-files limit", re.compile(r"3 or more files", re.IGNORECASE)),
    _Check("a major-task limit", _MAJOR_TASK),
    _Check("an 8-step count", re.compile(r"\b8-step\b", re.IGNORECASE)),
    _Check("the two new mandatory steps", re.compile(r"two new mandatory steps", re.I)),
    _Check(
        "the end of every qualifying task", re.compile(r"every qualifying task", re.I)
    ),
    _Check(
        "any coding task, bug fix, refactoring",
        re.compile(r"any coding task, bug fix, refactoring", re.IGNORECASE),
    ),
    _Check("major mapping work", re.compile(r"major mapping work", re.IGNORECASE)),
    _Check(
        "mandatory for Medium and Large",
        re.compile(r"mandatory for Medium and Large", re.IGNORECASE),
    ),
)


def _swept(text: str) -> list[str]:
    flat = _folded(text)
    return [c.label for c in _RETIRED_EVERYWHERE if _found(flat, c.needle)]


# --- the tests ----------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """The sweep reads exactly the files the places live in, and every one is there to read."""
    assert len(_SURFACE) == 8, f"the scan reads {len(_SURFACE)} files, not the 8 stated"
    assert len(set(_SURFACE)) == len(_SURFACE), "a file is listed twice in the scan"
    unread = [path for path in _SURFACE if not _read(path).strip()]
    assert not unread, f"{len(unread)} of {len(_SURFACE)} files are empty: {unread}"
    assert len(_PLACES) == 15, f"{len(_PLACES)} places, not the 15 stated"
    placed = {place.path for place in _PLACES}
    assert placed == set(_SURFACE), (
        f"the places live in {len(placed)} files and the sweep reads {len(_SURFACE)}; "
        f"only one side has {sorted(placed ^ set(_SURFACE))}"
    )
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), (
        "two places share a name, so ids would collide"
    )
    for place in _PLACES:
        labels = {c.label for c in place.required}
        assert set(place.kept) <= labels, f"{place.name}: kept names an unknown check"
        retired = {c.label for c in place.retired}
        assert set(place.preventive) <= retired, (
            f"{place.name}: preventive names an unknown check"
        )


@pytest.mark.parametrize("place", _REVIEW_PLACES, ids=[p.name for p in _REVIEW_PLACES])
def test_each_place_says_the_review_runs_at_every_completion_event(
    place: _Place,
) -> None:
    """Red before the change: each place bounded the review by the size of the task."""
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


def test_the_phase_gate_rule_reads_the_same_in_its_three_places() -> None:
    """At a phase gate Step 9 runs inline and the full review runs after the workflow. The skill
    that owns the review, the skill that runs the gates and the reference that lists them say
    so in the same words, so a reader of one is not told the opposite by another."""
    by_name = {place.name: place for place in _PLACES}
    assert len(_PHASE_GATE_PLACES) == 3
    for name in _PHASE_GATE_PLACES:
        place = by_name[name]
        flat = _folded(place.locate(_read(place.path))).lower()
        for fragment in (_PHASE_GATE_INLINE, _FULL_REVIEW_AFTER):
            assert fragment in flat, f"{name} ({place.path}) does not say: {fragment}"


def test_no_file_of_the_surface_still_bounds_the_review_by_size() -> None:
    """Red before the change: the limit sat in these files in several wordings (3+ files, major
    tasks, an 8-step count, "qualifying" tasks), so the sweep reads them all at once."""
    offenders = {path: hits for path in _SURFACE if (hits := _swept(_read(path)))}
    assert not offenders, (
        f"{sum(len(h) for h in offenders.values())} retired phrasing(s) in "
        f"{len(offenders)} of {len(_SURFACE)} files: {offenders}"
    )


def test_the_staged_delivery_sentence_is_kept_and_not_contradicted() -> None:
    """The sentence that lets a stage report defer a gate by naming it stays word for word, and
    the activation list points at it instead of banning deferral outright."""
    text = _read(_POST_TASK_REVIEW)
    kept = _folded(_list_item(text, "- **A staged delivery never fires"))
    assert _STAGED_DELIVERY in kept, (
        "the staged-delivery sentence of post-task-review's Important Notes is gone or reworded"
    )
    activation = next(p for p in _REVIEW_PLACES if p.name == "review-activation-list")
    gaps = _gaps(activation, text)
    assert not any("deferral" in gap or "staged-delivery" in gap for gap in gaps), gaps


def test_the_deferral_ban_check_sees_a_ban() -> None:
    """The one retired check the old text never carried is fired at a planted ban, since the
    old text cannot show that it works."""
    activation = next(p for p in _REVIEW_PLACES if p.name == "review-activation-list")
    banned = "## When This Skill Activates\n\nNever defer a gate to a later stage.\n"
    assert f"retired wording still there: {_DEFERRAL_BAN.label}" in _gaps(
        activation, banned
    )


@pytest.mark.parametrize(
    "place", _LESSONS_PLACES, ids=[p.name for p in _LESSONS_PLACES]
)
def test_task_learnings_runs_at_the_close_of_every_task(place: _Place) -> None:
    """Red before the change: the skill ran "at the end of every qualifying task"."""
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


def test_task_learnings_step_5_still_never_defers_the_append() -> None:
    """The deferral the opening paragraph allows is for a candidate that waits on an answer.
    It points at this rule, so the rule it points at must still be there."""
    step_5 = _folded(_section(_read(_TASK_LEARNINGS), "### Step 5"))
    assert "Never refuse or defer the append itself" in step_5, (
        "Step 5 no longer says the append itself is never deferred"
    )


def test_the_template_and_the_kit_keep_learnings_extraction_for_all_tasks() -> None:
    """The lessons item is already "(all tasks)" in both files and has to stay so: the
    review's wider trigger is no reason to narrow it."""
    for path in (_TEMPLATE, _KIT_AGENTS):
        item = _folded(_list_item(_read(path), "2. **Learnings extraction**"))
        assert item.startswith("2. Learnings extraction (all tasks)"), (path, item)


def test_every_place_check_fails_on_the_text_it_replaced() -> None:
    """A guard never shown to fail has not been shown to work: each place's checks are fired at
    the text the place carried before. Every required check must report it, but the ones the
    place lists as kept, and every retired check must see its wording, but the preventive one."""
    blind: dict[str, object] = {}
    for place in _PLACES:
        reported = _gaps(place, place.old)
        expected = [
            f"missing: {c.label}" for c in place.required if c.label not in place.kept
        ]
        expected += [
            f"retired wording still there: {c.label}"
            for c in place.retired
            if c.label not in place.preventive
        ]
        if reported != expected:
            blind[place.name] = {"reported": reported, "expected": expected}
    assert not blind, f"checks that cannot see the text they replaced: {blind}"


def test_the_sweep_flags_each_retired_phrase() -> None:
    planted = {
        "a 3+ files limit": "Use after any major spec (3+ files modified)",
        "a 3-or-more-files limit": "Refactoring touched 3 or more files",
        "a major-task limit": "for all major tasks",
        "an 8-step count": "Run the full 8-step review",
        "the two new mandatory steps": "process with two new\n  mandatory steps",
        "the end of every qualifying task": "at the end of every\nqualifying task",
        "any coding task, bug fix, refactoring": "after any coding task, bug fix, refactoring",
        "major mapping work": "post-task-review for major\nmapping work",
        "mandatory for Medium and Large": "(mandatory for Medium and\nLarge; the full pass)",
    }
    missing = {c.label for c in _RETIRED_EVERYWHERE} - set(planted)
    assert not missing, f"no planted positive for {sorted(missing)}"
    for label, text in planted.items():
        assert label in _swept(text), f"the sweep missed {label!r} in {text!r}"
    clean = (
        "Run the full review at every completion event, a finished task of any size",
        "a task of any kind or size is completed",
        "Step 0 through Step 9",
        "the 8 steps of the old review were renamed",
    )
    for text in clean:
        assert _swept(text) == [], f"the sweep flagged clean text: {text!r}"


def test_the_keep_guards_fail_on_text_without_what_they_keep() -> None:
    without_sentence = (
        "- **A staged delivery never fires** the event.\n  Nothing else.\n"
    )
    kept = _folded(_list_item(without_sentence, "- **A staged delivery never fires"))
    assert _STAGED_DELIVERY not in kept
    narrowed = (
        "2. **Learnings extraction** (major tasks) — Extract project-level findings."
    )
    assert not _folded(_list_item(narrowed, "2. **Learnings extraction**")).startswith(
        "2. Learnings extraction (all tasks)"
    )
    no_rule = "### Step 5: Write Entries\n\nAppend under the matching header.\n"
    assert "Never refuse or defer the append itself" not in _folded(
        _section(no_rule, "### Step 5")
    )


def test_a_list_item_is_read_whole_however_it_is_re_wrapped() -> None:
    """A re-wrap puts a continuation in column 0, at the item's indent or under its text. The
    reader keeps all three and stops at the next item, the next block and a heading, where the
    reader the five bullets used before (their first line only) lost the tail of the sentence."""
    tail = "the tail of the item"
    wrapped = {
        "column 0": f"- Run the review at every event, and then\n{tail}.\n- Next bullet.\n",
        "indented": f"- Run the review at every event, and then\n  {tail}.\n- Next bullet.\n",
        "numbered": f"1. Run the review at every event, and then\n   {tail}.\n2. Next item.\n",
        "numbered in column 0": f"1. Run the review at every event, and then\n{tail}.\n2. Next item.\n",
        "after a blank line": f"1. Run the review at every event,\n\n   {tail}.\n\n2. Next item.\n",
    }
    for name, text in wrapped.items():
        lead = f"{text.split(' ', 1)[0]} Run the review"
        item = _list_item(text, lead)
        assert tail in item, f"{name}: the tail of the item was cut off: {item!r}"
        assert "Next" not in item, f"{name}: the next item was read in: {item!r}"
        first_line_only = next(row for row in text.split("\n") if row.startswith(lead))
        assert tail not in first_line_only, f"{name}: the planted wrap hides nothing"
    for text, gone in (
        ("- Run the review.\n\nA new paragraph in column 0.\n", "new paragraph"),
        ("- Run the review\n## A heading\n", "heading"),
    ):
        assert gone not in _list_item(text, "- Run"), text
    assert _list_item("no such lead\n", "- Run") == ""
