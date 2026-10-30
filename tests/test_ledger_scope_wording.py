"""A delegated flow names who writes the changelog entry and the hypothesis.

The brief contract of `orchestrate` exempts the completion checklist from the file-set
partition because the learnings buffer and the changelog are append-only. It named two ledgers.
`post-task-review` Step 8 may also write an improvement hypothesis after each changelog entry,
and no Orchestration file named that ledger. When a project or a plan barred workers from the
ledgers anyway, nothing named a writer, so a flow ran Step 8 "as drafts" and the drafts stayed
in an untracked hand-off.

What the text says now, in the five places of the Orchestration and Core packs:

* the hypotheses ledger is named beside the other two, for appends only (a worker appends a new
  hypothesis entry; a Status or marker edit stays with the validator's run, outside the
  always-in-scope rule, so the exemption's append-only reason stays true);
* if the project or the plan bars workers from these files, the brief names one writer for
  each entry (the worker in its own branch, the session that receives the return, or the next
  consolidation) and adds the files to that writer's set; any other worker returns its drafts
  and lists each as not done, with the writer's name, under `## Status` in a hand-off;
* Step 8 tells a worker whose brief names another writer to draft both entries in its return
  and name that writer, in the same item that tells it to append, and its checklist lists both
  entries, the hypothesis as appended if warranted, and that rule.

The sixth place, the session register of the initiative planner's template, belongs to the
planner's own tests; this file asserts only the places in the files it lists.

Every check is fired at the text its place carried before (`old`), and every check of every
place must report it, since the old text carried none of the new wording. The writer sentence is
asserted whole, and as the last thing its item says: the three writers in its parenthesis are
the whole list only while nothing after the parenthesis adds a fourth.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEADING = re.compile(r"^(#{1,6})\s")
_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")


class _Check(NamedTuple):
    label: str
    needle: str


class _Place(NamedTuple):
    name: str
    path: str
    locate: Callable[[str], str]
    required: tuple[_Check, ...]
    old: str


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


def _first_fenced_block(text: str) -> str:
    """The lines between the first pair of code fences; the brief template is that block."""
    inside: list[str] = []
    opened = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if opened:
                return "\n".join(inside)
            opened = True
        elif opened:
            inside.append(line)
    return ""


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"the place is missing from {place.path}"]
    flat = _folded(region)
    return [f"missing: {c.label}" for c in place.required if c.needle not in flat]


def _section_of(heading: str) -> Callable[[str], str]:
    return lambda text: _section(text, heading)


def _item_of(lead: str) -> Callable[[str], str]:
    return lambda text: _list_item(text, lead)


def _then(*steps: Callable[[str], str]) -> Callable[[str], str]:
    def run(text: str) -> str:
        for step in steps:
            text = step(text)
        return text

    return run


def _writer_sentence_gaps(flat: str, sentence: str) -> list[str]:
    """The writer rule has to be there whole and has to be the last thing its item says: text
    after it would name a writer that its parenthesis does not list."""
    if sentence not in flat:
        return ["the writer sentence is missing or reworded"]
    after = flat[flat.index(sentence) + len(sentence) :]
    if after:
        return [f"text follows the writer sentence: {after!r}"]
    return []


# --- the wording ----------------------------------------------------------------------------------

_LEDGER = ".ai/improvement-hypotheses.md"
_APPENDS_ONLY = "for appends only, `.ai/improvement-hypotheses.md`"
_NOT_A_WORKERS_EDIT = "a Status or marker edit stays with the validator's run"
_ONE_WRITER = "names one writer for each entry"
_THREE_WRITERS = (
    "(the worker in its own branch, the session that receives the return, "
    "or the next consolidation)"
)
_WRITER_SET = "adds the files to that writer's set"
_DRAFTS_NOT_DONE = "any other worker returns its drafts and lists each as not done, with the writer's name"
_UNDER_STATUS = "under `## Status` in a hand-off"

_LEDGER_SENTENCE = (
    "`.ai/learnings.md`, `.ai/ai-changelog.md` and, for appends only, "
    "`.ai/improvement-hypotheses.md` are append-only, do not collide destructively, and "
    "the kit's data-file lint catches the merge artifacts that do occur."
)
_APPENDS_SENTENCE = (
    "A worker appends a new hypothesis entry; a Status or marker edit stays with the "
    "validator's run, outside this rule, so the exemption's append-only reason stays true."
)
_WRITER_SENTENCE_ITEM_5 = (
    "If the project or the plan bars workers from these files, the brief names one writer "
    f"for each entry {_THREE_WRITERS} and adds the files to that writer's set; any other "
    "worker returns its drafts and lists each as not done, with the writer's name "
    "(under `## Status` in a hand-off)."
)
_EXEMPTION = (
    "- Ledgers: `.ai/learnings.md`, `.ai/ai-changelog.md` and, for appends only, "
    "`.ai/improvement-hypotheses.md` stay open to your appends whatever the file set says "
    "(a Status or marker edit stays with the validator's run, not with you)."
)
_WRITER_SENTENCE_TEMPLATE = (
    "<Where the project or the plan bars workers from these files, replace that sentence "
    "with the writer rule: the brief names one writer for each entry "
    f"{_THREE_WRITERS} and adds the files to that writer's set; any other worker returns "
    "its drafts and lists each as not done, with the writer's name, under `## Status` in "
    "a hand-off.>"
)
_SAFETY_LEDGERS = (
    "`.ai/learnings.md`, `.ai/ai-changelog.md` and, for appends only, "
    "`.ai/improvement-hypotheses.md` are append-only: concurrent appends do not destroy "
    "each other (a Status or marker edit stays with the validator's run), and the support "
    "CLI's `lint` subcommand detects the duplicate-header/spliced-entry artifacts a merge "
    "can produce."
)
_WRITER_SENTENCE_4A = (
    "If the project or the plan bars workers from them, the brief names one writer for "
    "each entry, and any other worker returns its drafts as not done, naming that writer "
    "(`orchestrate`, item 5)."
)
_STEP_8_OTHER_WRITER = (
    "If the brief names another writer, draft the changelog entry and the hypothesis in "
    "your return and name that writer; append neither."
)
_STEP_8_APPEND = "append the appropriate changelog entry to `.ai/ai-changelog.md`"

_ORCHESTRATE = "plugins/orchestration/skills/orchestrate/SKILL.md"
_ITEM_5_LEAD = "5. **The completion gates ride in the DoD"
_BRIEF_TEMPLATE = (
    "plugins/orchestration/skills/orchestrate/references/brief-template.md"
)
_SAFETY = "plugins/orchestration/skills/parallel-session-safety/SKILL.md"
_REVIEW = "plugins/core/skills/post-task-review/SKILL.md"
_STEP_8_ITEM_6_LEAD = "6. **If any AI infrastructure files"
_CHECKLIST = "plugins/core/skills/post-task-review/references/review-checklist.md"

# What item 5 and the brief template both say, in the words of the request.
_COMMON_RULE: tuple[_Check, ...] = (
    _Check("the hypotheses ledger is named", _LEDGER),
    _Check("it is open to appends only", _APPENDS_ONLY),
    _Check("a Status or marker edit is not a worker's", _NOT_A_WORKERS_EDIT),
    _Check("the brief names one writer for each entry", _ONE_WRITER),
    _Check("the three writers, and no fourth", _THREE_WRITERS),
    _Check("the files join that writer's set", _WRITER_SET),
    _Check("any other worker returns its drafts as not done", _DRAFTS_NOT_DONE),
    _Check("the not-done line goes under Status in a hand-off", _UNDER_STATUS),
)
_ITEM_5_RULE: tuple[_Check, ...] = (
    *_COMMON_RULE,
    _Check("the ledgers are append-only, so the exemption holds", _LEDGER_SENTENCE),
    _Check(
        "a worker appends; a Status or marker edit stays with the validator",
        _APPENDS_SENTENCE,
    ),
    _Check("the writer sentence, whole", _WRITER_SENTENCE_ITEM_5),
)
_TEMPLATE_RULE: tuple[_Check, ...] = (
    *_COMMON_RULE,
    _Check(
        "the exemption: the ledgers stay open to appends whatever the file set says",
        _EXEMPTION,
    ),
    _Check("the writer sentence, whole", _WRITER_SENTENCE_TEMPLATE),
)


# --- the text each place carried before -------------------------------------------------------------

_OLD_ITEM_5 = """5. **The completion gates ride in the DoD, run BEFORE the handoff, and operator questions are
   self-addressed.** An implementation brief's definition of done includes the AGENTS.md
   task-completion checklist (post-task-review for 3+ files, learnings extraction) — **and the brief
   must state that it runs before the worker writes its return handoff, not after.** The handoff is
   the only thing you will read; one written first carries whatever the review would have corrected,

   **The completion checklist is ALWAYS in scope, whatever the declared file set says.** A worker
   closed with *"learnings extraction — still deferred because `.ai/learnings.md` sits outside my
   declared file set"*, and 12 sessions in the window never ran the review at all. The disjoint-file
   partition exists to stop destructive write collisions; `.ai/learnings.md` and
   `.ai/ai-changelog.md` are append-only, do not collide destructively, and the kit's data-file lint
   catches the merge artifacts that do occur. State this exemption in the brief — a scope
   rule that does not name its own exceptions gets read as exempting the obligations too.

6. **The target branch, as an assertion the worker runs — not as prose.**
"""

_OLD_BRIEF_TEMPLATE = """# Delegation brief template

Use this shape for every worker dispatch.

```markdown
## Standing rules (read this FILE — it is not restated below)
Read `<absolute path to the installed agent-delegate skill's assets/worker-preamble.md>` in full before your first
shell call: evidence discipline, working-tree discipline, and how to return a result.

## Goal (one concern)
<single outcome this worker owns>

## Context (so you don't re-explore the repo)
- Files: <paths the work touches, with one-line roles> — a STARTING SET, not a boundary
- Constraints/conventions: <the TASK-SPECIFIC rules — inline them, don't cite them>
- Known facts: <what the orchestrator already verified; state these as COMMANDS that regenerate
  the figure, not as figures — a brief's measured premise is the most common thing to go stale>
- Out of scope: <adjacent things this brief must NOT touch>

## Definition of done (self-checkable)
- <command that must pass / observable behavior / artifact that must exist>

## Report back (keep it short)
1. What you did (≤5 bullets)

## Close (run in this order, do not wait to be asked)
1. Self-challenge: is it detailed enough? Have you missed something? Say what it changed,
   including "nothing".
```

Rules of thumb:
"""

_OLD_SAFETY_4A = """### 4a. The partition never exempts the completion checklist

`.ai/learnings.md` and `.ai/ai-changelog.md` are **append-only**: concurrent appends do not
destroy each other, and the support CLI's `lint` subcommand detects the duplicate-header/spliced-entry
artifacts a merge can produce. So they are always in scope, for every session, regardless of the partition —
state this explicitly in each brief rather than relying on the worker to infer the exception. A
scope rule that does not name its own exceptions gets read as exempting the obligations too.

## 5. The Docker test suites are globally exclusive
"""

_OLD_REVIEW_STEP_8 = """### Step 8: Learnings Extraction & Changelog

After the full review is complete, extract and record learnings.

Invoke the `task-learnings` skill to:

1. Review the entire task for discoveries, surprises, and corrections
6. **If any AI infrastructure files were modified** during steps 1–7 (convention updates,
   skill modifications, rule additions), read the `ai-changelog` skill and
   append the appropriate changelog entry to `.ai/ai-changelog.md`
7. **After writing a changelog entry**, read the `ai-improvement-tracker` skill
   and evaluate whether the change warrants a testable improvement hypothesis

### Step 9: Close Self-Challenge (MANDATORY — it is not step 4, and it runs LAST)
"""

_OLD_CHECKLIST_STEP_8 = """## Step 8: Learnings Extraction

- [ ] Task reviewed for discoveries and surprises
- [ ] Review findings (steps 1–7) also considered as learnings
- [ ] Findings classified (project-level vs task-specific)
- [ ] Project-level findings appended to `.ai/learnings.md`
- [ ] Rules updated if convention gaps found
- [ ] Results reported (count + summary)

## Step 9: Close Self-Challenge (MANDATORY — runs LAST)
"""


# --- the places -----------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="orchestrate-item-5",
        path=_ORCHESTRATE,
        locate=_item_of(_ITEM_5_LEAD),
        required=_ITEM_5_RULE,
        old=_OLD_ITEM_5,
    ),
    _Place(
        name="brief-template",
        path=_BRIEF_TEMPLATE,
        locate=_first_fenced_block,
        required=_TEMPLATE_RULE,
        old=_OLD_BRIEF_TEMPLATE,
    ),
    _Place(
        name="safety-section-4a",
        path=_SAFETY,
        locate=_section_of("### 4a."),
        required=(
            _Check("the hypotheses ledger is named", _LEDGER),
            _Check("it is open to appends only", _APPENDS_ONLY),
            _Check("a Status or marker edit is not a worker's", _NOT_A_WORKERS_EDIT),
            _Check("the brief names one writer for each entry", _ONE_WRITER),
            _Check(
                "the ledgers are append-only and a Status or marker edit is the validator's",
                _SAFETY_LEDGERS,
            ),
            _Check("the writer sentence, whole", _WRITER_SENTENCE_4A),
        ),
        old=_OLD_SAFETY_4A,
    ),
    _Place(
        name="review-step-8",
        path=_REVIEW,
        locate=_then(_section_of("### Step 8:"), _item_of(_STEP_8_ITEM_6_LEAD)),
        required=(
            _Check(
                "item 6 drafts both entries in the return and names the writer",
                _STEP_8_OTHER_WRITER,
            ),
        ),
        old=_OLD_REVIEW_STEP_8,
    ),
    _Place(
        name="checklist-step-8",
        path=_CHECKLIST,
        locate=_section_of("## Step 8"),
        required=(
            _Check(
                "the changelog entry is listed",
                "- [ ] AI-infrastructure files modified: changelog entry appended to "
                "`.ai/ai-changelog.md`",
            ),
            _Check(
                "the hypothesis is appended if warranted, appends only",
                "- [ ] Changelog entry written: hypothesis evaluated, and appended to "
                "`.ai/improvement-hypotheses.md` if warranted (appends only; "
                f"{_NOT_A_WORKERS_EDIT})",
            ),
            _Check(
                "a brief that names another writer: both drafted, writer named, each not done",
                "- [ ] Brief names another writer for these two entries: both drafted in "
                "the return, that writer named, each listed as not done",
            ),
        ),
        old=_OLD_CHECKLIST_STEP_8,
    ),
)

_PLANNER_OWNED = "initiative-planner"


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Five places in five files, none of them the planner's, each file present and non-empty."""
    assert len(_PLACES) == 5, f"{len(_PLACES)} places, not the 5 stated"
    paths = [place.path for place in _PLACES]
    assert len(set(paths)) == 5, f"{len(set(paths))} distinct files, not 5: {paths}"
    assert not [p for p in paths if _PLANNER_OWNED in p], (
        "a place of the planner's own tests is asserted here too"
    )
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    empty = [path for path in paths if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_names_the_ledger_and_the_writer(place: _Place) -> None:
    """Red before the change: no place named the hypotheses ledger or a writer."""
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_fails_on_the_text_it_replaced(place: _Place) -> None:
    """The old text carried none of the new wording, so each of the place's checks must say so."""
    reported = _gaps(place, place.old)
    assert len(reported) == len(place.required), (
        f"{place.name}: {len(reported)} of {len(place.required)} checks saw the old text; "
        f"the ones that did not are blind: "
        f"{[c.label for c in place.required if f'missing: {c.label}' not in reported]}"
    )


def test_item_5_and_the_template_name_exactly_three_writers() -> None:
    """No fourth writer option: the writer sentence is whole in item 5, in the template's
    ledger bullet and in section 4a, and nothing follows it in its item, its bullet or its
    section, so a way out cannot be appended after the parenthesis of the three."""
    cases = (
        (
            "orchestrate-item-5",
            _ORCHESTRATE,
            _item_of(_ITEM_5_LEAD),
            _WRITER_SENTENCE_ITEM_5,
        ),
        (
            "brief-template",
            _BRIEF_TEMPLATE,
            _then(_first_fenced_block, _item_of("- Ledgers:")),
            _WRITER_SENTENCE_TEMPLATE,
        ),
        ("safety-section-4a", _SAFETY, _section_of("### 4a."), _WRITER_SENTENCE_4A),
    )
    assert len(cases) == 3, f"{len(cases)} places carry the writer sentence, not 3"
    for name, path, locate, sentence in cases:
        flat = _folded(locate(_read(path)))
        assert _writer_sentence_gaps(flat, sentence) == [], name


def test_the_writer_sentence_check_sees_a_fourth_way_out() -> None:
    """The check is fired at planted wording: a way out added inside the sentence, a way out
    added after it, and a fourth writer added in the parenthesis."""
    for sentence in (
        _WRITER_SENTENCE_ITEM_5,
        _WRITER_SENTENCE_TEMPLATE,
        _WRITER_SENTENCE_4A,
    ):
        assert _writer_sentence_gaps(f"Text. {sentence}", sentence) == []
        planted = {
            "inside the sentence": sentence[:-1]
            + ", or ask the operator to write them.",
            "after the sentence": f"{sentence} Or ask the operator to write them.",
        }
        if "consolidation" in sentence:
            planted["a fourth writer"] = sentence.replace(
                "or the next consolidation", "the planner, or the next consolidation"
            )
        for where, text in planted.items():
            assert _writer_sentence_gaps(text, sentence), (where, text)


def test_the_other_writer_rule_sits_in_the_item_that_appends() -> None:
    """Step 8 tells the worker to append in item 6 and says in the same item when it must not,
    so a reader who has done what item 6 says has not already appended before the override."""
    item = _folded(
        _list_item(_section(_read(_REVIEW), "### Step 8:"), _STEP_8_ITEM_6_LEAD)
    )
    assert _STEP_8_APPEND in item, (
        "item 6 no longer tells the worker to append the entry"
    )
    assert _STEP_8_OTHER_WRITER in item, "item 6 does not carry the other-writer rule"
    assert item.index(_STEP_8_APPEND) < item.index(_STEP_8_OTHER_WRITER)


def test_a_check_that_cannot_find_its_place_says_so() -> None:
    place = next(p for p in _PLACES if p.name == "review-step-8")
    assert _gaps(place, "### Step 7: Documentation\n\nText.\n") == [
        f"the place is missing from {place.path}"
    ]
    assert _gaps(place, "### Step 8: Learnings\n\n1. Review the task\n") == [
        f"the place is missing from {place.path}"
    ]
    assert _gaps(place, "") == [f"the place is missing from {place.path}"]
