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
* Step 8 tells a worker whose brief names another writer for the learnings entry, the changelog
  entry or the hypothesis to draft each in its return, name that writer, list each as not done and
  append none, whether or not infrastructure files changed. The clause leads with its own
  condition and sits in item 4, the item that appends the learnings entry and has no condition of
  its own. It is not in item 6, which opens on "If any AI infrastructure files were modified" and
  would make the rule depend on that, and no part of it is anywhere from item 6 to the end of the
  list, which is told only when such a file changed; item 6, which appends the changelog entry,
  points back to item 4. Its checklist lists the entries, the hypothesis as appended if warranted,
  and that rule.

The sixth place, the session register of the initiative planner's template, belongs to the
planner's own tests; this file asserts only the places in the files it lists.

Every check is fired at the text its place carried before (`old`), and every check of every
place must report it, since the old text carried none of the new wording. The writer sentence is
asserted whole, and as the last thing its item says: the three writers in its parenthesis are
the whole list only while nothing after the parenthesis adds a fourth. The Step 8 checks are also
fired at Step 8 as the first round wrote it (`_FIRST_ROUND_STEP_8`), as the two-entry clause left
it and as it stood before any clause, and at planted placements, among them a rule reworded so
that the clause's own words are absent from the item that opens on the infrastructure condition.
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
    "If the brief names another writer for the learnings entry, the changelog entry or the "
    "hypothesis, draft each in your return, name that writer, list each as not done, and "
    "append none, whether or not infrastructure files changed."
)
_STEP_8_APPEND = "append the appropriate changelog entry to `.ai/ai-changelog.md`"
_STEP_8_ITEM_4_LEAD = "4. Append project-level findings"
_STEP_8_ITEM_4_APPEND = "4. Append project-level findings to `.ai/learnings.md`."
_STEP_8_ITEM_6_POINTS_BACK = "(unless item 4's other-writer rule applies)"
_STEP_8_GATE = "If any AI infrastructure files were modified"
_GATE_OPENING = re.compile(rf"\d+\. {re.escape(_STEP_8_GATE)}")
# The parts of the other-writer rule, in the words of the clause and of the two-entry clause it
# replaced ("append neither"). A part of the rule in an item that is told only when infrastructure
# files changed is not told to a worker whose task changed none.
_RULE_PARTS = (
    "another writer",
    "name that writer",
    "not done",
    "append none",
    "append neither",
)
# What a Step 8 can lack so that a worker whose brief names another writer is not told what to do.
_GATED = "the clause sits in an item that opens on the infrastructure-change condition"
_NO_OWN_LEAD = (
    "no item carries the clause whole: its own condition naming the learnings entry, the "
    "changelog entry and the hypothesis, and that it holds whether or not infrastructure "
    "files changed"
)
_NO_ANTECEDENT = "an item says 'for these entries' before it has named the entries"

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
2. Include findings from the review itself (steps 1–7) — if the review caught issues, those are learnings too
3. Classify findings as project-level or task-specific
4. Append project-level findings to `.ai/learnings.md`
5. Update project rules if any convention gaps were found
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
        locate=_then(_section_of("### Step 8:"), _item_of(_STEP_8_ITEM_4_LEAD)),
        required=(
            _Check(
                "item 4 drafts the learnings entry, the changelog entry and the hypothesis in "
                "the return, names the writer, lists each as not done and appends none, "
                "whether or not infrastructure files changed",
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
                "a brief that names another writer: the three entries drafted, writer named, "
                "each not done, none appended",
                "- [ ] Brief names another writer for these entries: the learnings entry, the "
                "changelog entry and the hypothesis drafted in the return, that writer named, "
                "each listed as not done, none appended",
            ),
        ),
        old=_OLD_CHECKLIST_STEP_8,
    ),
)

_PLANNER_OWNED = "initiative-planner"

# What Step 8 and its checklist carried when the two-entry clause landed: it named the changelog
# entry and the hypothesis only, listed nothing as not done, and item 4 appended the learnings
# entry whatever the brief said. Unedited excerpts of the two files at that commit.
_TWO_ENTRY_STEP_8 = r"""### Step 8: Learnings Extraction & Changelog

After the full review is complete, extract and record learnings.

Invoke the `task-learnings` skill to:

1. Review the entire task for discoveries, surprises, and corrections
2. Include findings from the review itself (steps 1–7) — if the review caught issues, those are learnings too
3. Classify findings as project-level or task-specific
4. Append project-level findings to `.ai/learnings.md`
5. Update project rules if any convention gaps were found
6. **If any AI infrastructure files were modified** during steps 1–7 (convention updates,
   skill modifications, rule additions), read the `ai-changelog` skill and
   append the appropriate changelog entry to `.ai/ai-changelog.md`. If the brief names another
   writer, draft the changelog entry and the hypothesis in your return and name that writer;
   append neither.
7. **After writing a changelog entry**, read the `ai-improvement-tracker` skill
   and evaluate whether the change warrants a testable improvement hypothesis
"""

# What Step 8 carried after the first round: the clause was widened to the three entries but stayed
# in item 6 behind its infrastructure condition, item 4 pointed at it, and "these entries" came
# before the entries were named. An unedited excerpt of the file at that commit.
_FIRST_ROUND_STEP_8 = r"""### Step 8: Learnings Extraction & Changelog

After the full review is complete, extract and record learnings.

Invoke the `task-learnings` skill to:

1. Review the entire task for discoveries, surprises, and corrections
2. Include findings from the review itself (steps 1–7) — if the review caught issues, those are learnings too
3. Classify findings as project-level or task-specific
4. Append project-level findings to `.ai/learnings.md`, unless the brief names another writer for it (item 6)
5. Update project rules if any convention gaps were found
6. **If any AI infrastructure files were modified** during steps 1–7 (convention updates,
   skill modifications, rule additions), read the `ai-changelog` skill and append the
   appropriate changelog entry to `.ai/ai-changelog.md`. If the brief names another writer for
   these entries, draft the learnings entry, the changelog entry and the hypothesis in your
   return, name that writer, list each as not done, and append none.
7. **After writing a changelog entry**, read the `ai-improvement-tracker` skill
   and evaluate whether the change warrants a testable improvement hypothesis
"""

_TWO_ENTRY_CHECKLIST_STEP_8 = r"""## Step 8: Learnings Extraction

- [ ] Task reviewed for discoveries and surprises
- [ ] Review findings (steps 1–7) also considered as learnings
- [ ] Findings classified (project-level vs task-specific)
- [ ] Project-level findings appended to `.ai/learnings.md`
- [ ] Rules updated if convention gaps found
- [ ] AI-infrastructure files modified: changelog entry appended to `.ai/ai-changelog.md`
- [ ] Changelog entry written: hypothesis evaluated, and appended to `.ai/improvement-hypotheses.md` if warranted (appends only; a Status or marker edit stays with the validator's run)
- [ ] Brief names another writer for these two entries: both drafted in the return, that writer named, each listed as not done
- [ ] Results reported (count + summary)
"""


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
        _STEP_8_OTHER_WRITER,
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


def _step_8_item(lead: str, text: str) -> str:
    return _folded(_list_item(_section(text, "### Step 8:"), lead))


def _step_8_items(step_8: str) -> list[str]:
    """The numbered items of a Step 8 section, each folded to one line."""
    chunks = re.split(r"(?m)^(?=\d+\. )", step_8)
    return [_folded(chunk) for chunk in chunks if re.match(r"\d+\. ", chunk)]


def _gated_items(step_8: str) -> list[str]:
    """The items of a Step 8 section from the one that opens on the infrastructure condition to the
    end of the list: item 6 and item 7, which follows the changelog entry item 6 appends. They are
    told only when an infrastructure file changed. Empty when no item opens on the condition, so
    a renamed condition is a loud failure at the caller and never a scope with nothing in it."""
    items = _step_8_items(step_8)
    for index, item in enumerate(items):
        if _GATE_OPENING.match(item):
            return items[index:]
    return []


def _gated_rule_parts(step_8: str) -> list[str]:
    """The parts of the other-writer rule that sit in an item told only when infrastructure files
    changed, whatever the wording around them. Empty when none do."""
    return [
        part for item in _gated_items(step_8) for part in _RULE_PARTS if part in item
    ]


def _clause_gaps(step_8: str) -> list[str]:
    """What a Step 8 section lacks if a worker whose brief names another writer is to be told what
    to do whether or not the task changed infrastructure files: the clause in an item that does
    not open on that condition, the clause whole (its own condition, the three entries, the
    'whether or not'), and no 'these entries' before the entries are named."""
    items = _step_8_items(step_8)
    gaps: list[str] = []
    if any(_STEP_8_GATE in item and "names another writer" in item for item in items):
        gaps.append(_GATED)
    if not any(_STEP_8_OTHER_WRITER in item for item in items):
        gaps.append(_NO_OWN_LEAD)
    if any("for these entries" in item for item in items):
        gaps.append(_NO_ANTECEDENT)
    return gaps


def test_the_other_writer_rule_sits_in_the_item_that_appends() -> None:
    """Step 8 tells the worker to append the learnings entry in item 4 and says in the same item
    when it must not, so a reader who has done what item 4 says has not already appended before
    the override, and the item has no condition of its own that the override would hide behind."""
    item = _step_8_item(_STEP_8_ITEM_4_LEAD, _read(_REVIEW))
    assert _STEP_8_ITEM_4_APPEND in item, (
        "item 4 no longer tells the worker to append the entry"
    )
    assert _STEP_8_OTHER_WRITER in item, "item 4 does not carry the other-writer rule"
    assert item.index(_STEP_8_ITEM_4_APPEND) < item.index(_STEP_8_OTHER_WRITER)


def test_item_6_points_back_to_the_other_writer_rule_instead_of_repeating_it() -> None:
    """Item 6 appends the changelog entry, so it says where the exception is stated: a worker
    whose brief names another writer has read item 4's rule and is told again at the append it
    overrides. The rule is stated once."""
    item = _step_8_item(_STEP_8_ITEM_6_LEAD, _read(_REVIEW))
    assert _STEP_8_APPEND in item, (
        "item 6 no longer tells the worker to append the entry"
    )
    assert _STEP_8_ITEM_6_POINTS_BACK in item, f"item 6 reads {item!r}"
    assert item.index(_STEP_8_APPEND) < item.index(_STEP_8_ITEM_6_POINTS_BACK)
    assert "names another writer" not in item, "the rule is stated in item 6 as well"


def test_the_writer_clause_covers_the_learnings_entry_and_ends_its_item() -> None:
    """'learnings' is inside the clause, and the clause is the last thing item 4 says, so no way
    out can follow it."""
    item = _step_8_item(_STEP_8_ITEM_4_LEAD, _read(_REVIEW))
    assert "If the brief names another writer" in item, "item 4 lost the clause"
    clause = item[item.index("If the brief names another writer") :]
    assert "learnings" in clause
    assert _writer_sentence_gaps(clause, _STEP_8_OTHER_WRITER) == []


def test_the_writer_clause_is_not_gated_on_an_infrastructure_change() -> None:
    """The clause leads with its own condition and lives in an item with none, so a brief that
    names another writer for the learnings entry is answered when no infrastructure file changed."""
    gaps = _clause_gaps(_section(_read(_REVIEW), "### Step 8:"))
    assert not gaps, f"Step 8 of {_REVIEW}: {gaps}"


def test_the_other_writer_rule_is_not_inside_item_6s_condition() -> None:
    """Item 6 opens on "If any AI infrastructure files were modified", so from it to the end of the
    list Step 8 is told only when such a file changed. A worker whose brief names another writer
    and whose task changed none must still be told to draft the three entries, name the writer,
    list each as not done and append none, so no part of that rule may sit there: it sits in item
    4, which has no condition. A Step 8 with no item that opens on the condition fails too, since
    there would be no scope to check."""
    step_8 = _section(_read(_REVIEW), "### Step 8:")
    gated = _gated_items(step_8)
    assert gated, "no item of Step 8 opens on the infrastructure condition"
    assert gated[0].startswith("6. "), f"the gated items start at {gated[0][:40]!r}"
    held = _gated_rule_parts(step_8)
    assert not held, f"item 6 or 7 holds part of the other-writer rule: {held}"


def test_the_condition_scope_check_reports_step_8_as_it_stood_and_as_planted() -> None:
    """Fired at Step 8 as the first round wrote it (the whole rule in item 6, behind the
    condition), as the two-entry clause left it (item 6 again, "append neither") and as it stood
    before any clause; then at planted placements: the rule reworded so that "names another
    writer" is absent (the clause check does not see it, this one does), the rule in item 7, which
    follows item 6, a rule in item 4 with a pointer in item 6, and a Step 8 with no item that
    opens on the condition."""
    step_8 = "### Step 8:"
    assert _gated_rule_parts(_section(_FIRST_ROUND_STEP_8, step_8)) == [
        "another writer",
        "name that writer",
        "not done",
        "append none",
    ]
    assert _gated_rule_parts(_section(_TWO_ENTRY_STEP_8, step_8)) == [
        "another writer",
        "name that writer",
        "append neither",
    ]
    assert _gated_rule_parts(_section(_OLD_REVIEW_STEP_8, step_8)) == []

    reworded = (
        "### Step 8: Planted\n\n"
        "4. Append project-level findings to `.ai/learnings.md`.\n"
        f"6. **{_STEP_8_GATE}**, append the entry. Where someone else owns the ledgers, "
        "list each as not done and append none.\n"
        "7. After writing a changelog entry, read the tracker skill\n"
    )
    assert _gated_rule_parts(reworded) == ["not done", "append none"]
    assert _GATED not in _clause_gaps(reworded), (
        "the clause check sees the reworded rule"
    )
    in_item_7 = (
        "### Step 8: Planted\n\n"
        "4. Append project-level findings to `.ai/learnings.md`.\n"
        f"6. **{_STEP_8_GATE}**, append the entry.\n"
        "7. After writing a changelog entry, read the tracker skill. If another writer owns "
        "it, append none.\n"
    )
    assert _gated_rule_parts(in_item_7) == ["another writer", "append none"]
    ungated = (
        "### Step 8: Planted\n\n"
        f"4. Append project-level findings to `.ai/learnings.md`. {_STEP_8_OTHER_WRITER}\n"
        f"6. **{_STEP_8_GATE}**, append the entry {_STEP_8_ITEM_6_POINTS_BACK}.\n"
    )
    assert _gated_rule_parts(ungated) == []
    no_scope = (
        "### Step 8: Planted\n\n"
        "4. Append project-level findings. If another writer owns it, append none.\n"
    )
    assert _gated_items(no_scope) == []
    assert _gated_rule_parts(no_scope) == []


def test_the_clause_checks_report_step_8_as_it_stood_and_as_planted() -> None:
    """Fired at Step 8 as the first round wrote it (the clause in item 6, behind the infrastructure
    condition, with 'these entries' before the entries), as the two-entry clause left it (item 6
    again, two entries) and as it stood before any clause; then at planted placements, each of
    which trips one check and no other."""
    step_8 = "### Step 8:"
    assert _clause_gaps(_section(_FIRST_ROUND_STEP_8, step_8)) == [
        _GATED,
        _NO_OWN_LEAD,
        _NO_ANTECEDENT,
    ]
    assert _clause_gaps(_section(_TWO_ENTRY_STEP_8, step_8)) == [_GATED, _NO_OWN_LEAD]
    assert _clause_gaps(_section(_OLD_REVIEW_STEP_8, step_8)) == [_NO_OWN_LEAD]
    planted = (
        "### Step 8: Planted\n\n"
        "4. Append project-level findings to `.ai/learnings.md`.\n"
        f"6. **{_STEP_8_GATE}**, append the entry. {_STEP_8_OTHER_WRITER}\n"
        "7. After writing a changelog entry, read the tracker skill\n"
    )
    assert _clause_gaps(planted) == [_GATED]
    ungated = (
        "### Step 8: Planted\n\n"
        f"4. Append project-level findings to `.ai/learnings.md`. {_STEP_8_OTHER_WRITER}\n"
        "5. Update project rules if any convention gaps were found\n"
    )
    assert _clause_gaps(ungated) == []
    assert _clause_gaps(f"{ungated}6. Update the rules for these entries\n") == [
        _NO_ANTECEDENT
    ]


def test_the_widened_checks_fail_on_the_two_entry_text() -> None:
    """Fired at Step 8 and its checklist as they stood when the two-entry clause landed. Item 6
    named two entries and no 'not done', item 4 appended the learnings entry unconditionally, and
    the checklist row said 'these two entries'; each new check must report that text."""
    item_6 = _step_8_item(_STEP_8_ITEM_6_LEAD, _TWO_ENTRY_STEP_8)
    assert item_6, "the old item 6 was not found"
    assert _STEP_8_OTHER_WRITER not in item_6
    for needle in ("the learnings entry", "list each as not done", "append none"):
        assert needle not in item_6, needle
    item_4 = _step_8_item(_STEP_8_ITEM_4_LEAD, _TWO_ENTRY_STEP_8)
    assert item_4, "the old item 4 was not found"
    assert _STEP_8_OTHER_WRITER not in item_4
    assert "another writer" not in item_4

    by_name = {place.name: place for place in _PLACES}
    review = by_name["review-step-8"]
    assert _gaps(review, _TWO_ENTRY_STEP_8) == [f"missing: {review.required[0].label}"]
    checklist = by_name["checklist-step-8"]
    assert _gaps(checklist, _TWO_ENTRY_CHECKLIST_STEP_8) == [
        f"missing: {checklist.required[2].label}"
    ]


def test_a_check_that_cannot_find_its_place_says_so() -> None:
    place = next(p for p in _PLACES if p.name == "review-step-8")
    assert _gaps(place, "### Step 7: Documentation\n\nText.\n") == [
        f"the place is missing from {place.path}"
    ]
    assert _gaps(place, "### Step 8: Learnings\n\n1. Review the task\n") == [
        f"the place is missing from {place.path}"
    ]
    assert _gaps(place, "") == [f"the place is missing from {place.path}"]
