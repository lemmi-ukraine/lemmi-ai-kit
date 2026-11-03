"""The worker preamble and the brief contract stop teaching two things a harness refuses.

A leading `NAME=value` assignment before a command can be denied by a shell hook, and a
harness may refuse a sub-agent's write of a report file. The preamble and the brief contract
said "write your report file EARLY and INCREMENTALLY" with no word about either, so a worker
that obeyed met a denial on its first command or on its last write, with no way out.

What the text says now, in the seven places of the three files it lists:

* the preamble's host rules, outside the block an adopter replaces, give the shell-hook limit
  and its substitutes: put the value inline, write multi-step logic to a script file, or use the
  interpreter's UTF-8 mode flag instead of an environment variable; the paragraph says it is a
  kit default to keep when the block above it is replaced;
* the preamble's section on the report file says the advice holds only if the worker is allowed
  to write, and its section on returning a result says that a refused write makes the final
  message the report;
* the brief contract (items 8 and 9) and the brief template carry the same two harness limits
  as lines the orchestrator pastes, and the template carries one budget line: how many sessions
  the work needs and the split, written before phase 1;
* the template's rule of thumb that standing rules are pointed at, not pasted, names the two
  harness limits as its one exception.

Every check is fired at the text its place carried before (`old`): the checks that carry the
change must all report it, the retired wording must be seen, and what has to stay must still be
there, so a pattern that could not fail cannot stand in for the sentence. A place asserts each
sentence it gained whole, so a clause cannot be dropped while the rest of the sentence matches.
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
    retired: tuple[_Check, ...] = ()
    kept: tuple[_Check, ...] = ()


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


def _without_blockquotes(text: str) -> str:
    """The text without its blockquote lines: the block an adopter replaces is one."""
    return "\n".join(line for line in text.split("\n") if not line.startswith(">"))


def _section_of(heading: str) -> Callable[[str], str]:
    return lambda text: _section(text, heading)


def _item_of(lead: str) -> Callable[[str], str]:
    return lambda text: _list_item(text, lead)


def _without_quote_marks(locate: Callable[[str], str]) -> Callable[[str], str]:
    """The located text with its blockquote markers removed, so that a step the block wraps onto
    a second quoted line is read as the one sentence it is."""
    return lambda text: re.sub(r"(?m)^[ \t]*>[ \t]?", "", locate(text))


def _outside_the_adopters_block(heading: str) -> Callable[[str], str]:
    return lambda text: _without_blockquotes(_section(text, heading))


def _has(flat: str, needle: str) -> bool:
    """Whether the folded text says `needle`, capitals ignored: the same sentence opens a
    sentence in one place and follows a colon in another."""
    return needle.lower() in flat.lower()


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    if not region.strip():
        return [f"the place is missing from {place.path}"]
    flat = _folded(region)
    gaps = [f"missing: {c.label}" for c in place.required if not _has(flat, c.needle)]
    gaps += [
        f"missing (kept): {c.label}" for c in place.kept if not _has(flat, c.needle)
    ]
    gaps += [
        f"retired wording still there: {c.label}"
        for c in place.retired
        if _has(flat, c.needle)
    ]
    return gaps


# --- the wording ----------------------------------------------------------------------------------

_SHELL_HOOK = (
    "A leading `NAME=value` assignment before a command can be denied by a shell hook"
)
_INLINE = "put the value inline"
_SCRIPT_FILE = "write multi-step logic to a script file"
_UTF8_FLAG = "use the interpreter's UTF-8 mode flag"
_NOT_AN_ENV_VAR = "instead of an environment variable"
_REFUSAL = "A harness may refuse a sub-agent's write of a report file"
_REFUSED_WRITE_REPORTED = "say the write was refused"

_KIT_DEFAULT = "Shell hooks (a kit default: keep it when you replace the block above)."
_PREAMBLE_SHELL_PARAGRAPH = (
    f"{_KIT_DEFAULT} {_SHELL_HOOK}. Put the value inline in the command, write multi-step "
    "logic to a script file, or use the interpreter's UTF-8 mode flag (`python -X utf8` for "
    "Python) instead of an environment variable."
)
_PREAMBLE_REPORT_PARAGRAPH = (
    "Write the deliverable as you go, not at the end — but only if you are allowed to "
    f"write. {_REFUSAL}. If yours does, do not retry or route around the refusal: return "
    "your findings as text in your final message (section 4) and say the write was refused."
)
_PREAMBLE_RETURN_BULLET = (
    "If the harness refused your report file, your final message is the report: return "
    "the findings as text, in the report format your brief gave, and say the write was "
    "refused (section 3). Without that, the refusal reads as a worker that found nothing."
)
_ITEM_8_LEAD = (
    "*Write the report file EARLY and INCREMENTALLY — if the worker may write.* State "
    "this in the brief."
)
_ITEM_8_REFUSAL = (
    f"{_REFUSAL}: such a sub-agent returns its findings as text, so "
    '"write your report early" applies only to workers allowed to write.'
)
_ITEM_8_EXCEPTION = (
    'Two harness limits are the exception to "point, don\'t paste" — the template '
    "restates both, because a worker meets them on its first command and its last write."
)
_ITEM_8_SHELL_SENTENCE = (
    f"{_SHELL_HOOK}: put the value inline, write multi-step logic to a script file, or use "
    "the interpreter's UTF-8 mode flag instead of an environment variable."
)
_ITEM_8_OTHER_LIMIT = "The other limit is the refused report file, in the clause above."
_ITEM_9_SENTENCE = (
    "Step 4 writes a file: a sub-agent whose harness refuses the write returns the "
    "handoff content as text (item 8)."
)
_TEMPLATE_HEADING = (
    "## Standing rules (read this FILE — only two harness limits are restated below)"
)
_TEMPLATE_SHELL_LINE = (
    "- Shell hook: a leading `NAME=value` assignment before a command can be denied. "
    "Put the value inline, write multi-step logic to a script file, or use the "
    "interpreter's UTF-8 mode flag instead of an environment variable."
)
_TEMPLATE_REPORT_LINE = (
    "- Report file: a harness may refuse a sub-agent's write of a report file. If yours "
    'does, return your findings as text; "write your report early" applies only if you '
    "are allowed to write."
)
_TEMPLATE_BUDGET_LINE = (
    "- Budget: <how many sessions this work needs and how it splits, written before "
    "phase 1>"
)
_TEMPLATE_REPORT_PARAGRAPH = (
    "If you may write files, write this report file EARLY and INCREMENTALLY, not at the "
    "end: workers are killed mid-run by usage limits often enough that a report written "
    "only at the end is often never written at all."
)
_TEMPLATE_EXCEPTION = (
    "The one exception is the two harness limits restated at the top of the template "
    "(a denied leading `NAME=value` assignment, a refused report file): a worker meets "
    "them on its first command and its last write."
)

_PREAMBLE = "plugins/orchestration/skills/agent-delegate/assets/worker-preamble.md"
_ORCHESTRATE = "plugins/orchestration/skills/orchestrate/SKILL.md"
_TEMPLATE = "plugins/orchestration/skills/orchestrate/references/brief-template.md"


# --- the text each place carried before -----------------------------------------------------------

_OLD_PREAMBLE = """# Worker preamble — point every delegated worker at this FILE

---

## 0 · Host rules (project-specific — fill this in)

> **Adopters: replace this block** with your environment's hard constraints — shell and path
> rules, forbidden directories, interpreter names, redirection requirements. Keep it to
> constraints a worker can *violate*, not general advice.
>
> Leave the heading in place even if the block is empty: a worker that finds the section missing
> cannot tell "no host rules" from "the preamble was truncated".

---

## 1 · Evidence discipline — how you are allowed to make a claim

Each rule below is a measured failure mode, not a style preference.

---

## 3 · Write your report file EARLY and INCREMENTALLY

Write the deliverable as you go, not at the end.

Workers are killed mid-run by usage limits often enough to matter — **22% of one measured
sub-agent corpus returned nothing at all**. A worker that dies returns exactly what a worker that
found nothing returns, so the orchestrator cannot tell a missing gate from a passing one.

---

## 4 · Returning your result

- **Your final message *is* the return value** — data for the orchestrator, not a status report.
- **Results are claims.** State what you ran and what it output. If you could not verify something,
  say UNKNOWN and name what would settle it.
- **Run your completion checklist BEFORE writing your return, never after.** A return written first
  carries whatever the review would have corrected, and the orchestrator inherits it as fact.
"""

_OLD_ITEM_8 = """8. **Point the worker at the preamble FILE — do not restate the rules inline, and require the
   report to be written incrementally.** Two clauses, both measured:

   - *Point, don't paste.* Give the worker the path to
     [`../agent-delegate/assets/worker-preamble.md`](../agent-delegate/assets/worker-preamble.md)
     (evidence discipline, working-tree discipline, how to return a result). Across 59 sub-agent
     transcripts, prompts that restated the rules verbatim were violated at **32/32 (100%)** versus
     **25/27 (93%)** for prompts that did not — restating inline has **no measurable effect**. The
     only transcripts with zero violations were pointed at a rules *file*. One condition in a small
     corpus, so: current best practice with a named test (re-measure the violation rate), not a law.
     It costs one line either way.
   - *Write the report file EARLY and INCREMENTALLY.* State this in the brief. **22% of one measured
     sub-agent corpus was killed mid-run by the usage window and returned nothing at all** — and a
     worker that dies returns exactly what a worker that found nothing returns, so you cannot tell a
     missing gate from a passing one. In the one recorded controlled contrast, the worker given this
     clause survived the window that killed its sibling. Also treat it as a hypothesis with a test:
     re-measure the no-return rate.

   Both clauses exist because **a prose rule does not bind, and a seam binds only the exact shape it
   matches.** When you add a guard, match the resulting *state*, not a leading token: guards that
   match a token are routinely reached by a rephrasing, and the violation counter then reads zero
   for a worker that violated throughout.

9. **The close block — paste it verbatim into every brief.** The single largest behavioural finding
"""

_OLD_ITEM_9 = """9. **The close block — paste it verbatim into every brief.** The single largest behavioural finding
   in the measured corpus: an operator hand-pasted an adversarial self-challenge in **114 of 303
   sessions**, and it found a real defect nearly every time. In one session it found four defects
   *after* the completion review had already passed. That is a quality gate being run by hand
   because the pipeline does not run it.

   Item 5 already mandates the completion review; this is a **different** control. The review asks
   *is my reasoning correct?*, which confirms. The challenge asks *what did I not look at?*, which
   searches. Paste this into the brief rather than referencing it — a literal reachable only through
   a template gets re-discovered rather than followed:

   > **Close — run in this order, do not wait to be asked.**
   > 1. Self-challenge: is it detailed enough? Have you missed something? Say what it changed,
   >    including "nothing".
   > 2. Then the task-completion review, if you have not already run it. Both run BEFORE the
   >    handoff.
   > 3. Save everything into the handoff.
   > 4. Then write a short summary for whoever reads it next: bullets, ≤10 lines, plain language,
   >    no internal ids.

   Plus three operator-interface rules, which apply to **every turn addressed to a human**, not just
   to briefs:

10. **Any rule a close-time lint enforces by EXACT MATCH goes in the brief's close section
"""

_OLD_TEMPLATE = """# Delegation brief template

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
2. Definition-of-done result (command output / evidence)

Write this report file EARLY and INCREMENTALLY, not at the end: workers are killed mid-run by
usage limits often enough that a report written only at the end is often never written at all.

## Close (run in this order, do not wait to be asked)
1. Self-challenge: is it detailed enough? Have you missed something? Say what it changed,
   including "nothing".
```

Rules of thumb:
"""

_OLD_TEMPLATE_RULES = """Rules of thumb:

- **Workers don't invent the plan.** If the worker would need to make an architectural choice,
  the brief is under-specified — decide it yourself first (or make that decision the brief, routed
  to a reasoning worker).
- **Inline the TASK-SPECIFIC source of truth; POINT at the standing rules.** These pull in opposite
  directions and the split is deliberate. Paste the convention or spec text that governs *this*
  change — it is small, task-scoped, and a stale reference is the real risk. But give the **standing**
  rules (evidence discipline, tree discipline, how to return) as a path to
  `../../agent-delegate/assets/worker-preamble.md`: that content is identical across every dispatch,
  and restating it inline was measured to change nothing (violated at 32/32 when restated vs 25/27
  when not, with the only clean transcripts being the ones pointed at a file). Inlining it also
  crowds out the task-specific text that inlining is *for*.
- **Definition of done must be checkable by the worker alone** — and re-checkable by you at merge
  time. "Looks good" is not a definition of done.
"""


# --- the places -----------------------------------------------------------------------------------

_PLACES: tuple[_Place, ...] = (
    _Place(
        name="preamble-section-0",
        path=_PREAMBLE,
        locate=_outside_the_adopters_block("## 0 ·"),
        required=(
            _Check("a leading NAME=value can be denied by a shell hook", _SHELL_HOOK),
            _Check("substitute: put the value inline", _INLINE),
            _Check("substitute: a script file for multi-step logic", _SCRIPT_FILE),
            _Check("substitute: the UTF-8 mode flag", _UTF8_FLAG),
            _Check("not an environment variable", _NOT_AN_ENV_VAR),
            _Check(
                "a kit default that is kept when the block above is replaced",
                _KIT_DEFAULT,
            ),
            _Check("the shell-hook paragraph, whole", _PREAMBLE_SHELL_PARAGRAPH),
        ),
        old=_OLD_PREAMBLE,
    ),
    _Place(
        name="preamble-section-3",
        path=_PREAMBLE,
        locate=_section_of("## 3 ·"),
        required=(
            _Check(
                "the advice holds only for a worker allowed to write",
                "only if you are allowed to write",
            ),
            _Check("a harness may refuse a report-file write", _REFUSAL),
            _Check(
                "no retry and no workaround", "do not retry or route around the refusal"
            ),
            _Check(
                "the findings come back as text",
                "return your findings as text in your final message",
            ),
            _Check("the refusal is said", _REFUSED_WRITE_REPORTED),
            _Check("the report paragraph, whole", _PREAMBLE_REPORT_PARAGRAPH),
        ),
        old=_OLD_PREAMBLE,
        kept=(
            _Check(
                "the advice itself", "Write the deliverable as you go, not at the end"
            ),
        ),
    ),
    _Place(
        name="preamble-section-4",
        path=_PREAMBLE,
        locate=_section_of("## 4 ·"),
        required=(
            _Check(
                "a refused write makes the final message the report",
                "If the harness refused your report file, your final message is the report",
            ),
            _Check(
                "the findings come back as text in the brief's report format",
                "return the findings as text, in the report format your brief gave",
            ),
            _Check("the refusal is said", _REFUSED_WRITE_REPORTED),
            _Check("the bullet, whole", _PREAMBLE_RETURN_BULLET),
        ),
        old=_OLD_PREAMBLE,
        kept=(
            _Check(
                "the final message is the return value",
                "Your final message *is* the return value",
            ),
        ),
    ),
    _Place(
        name="orchestrate-item-8",
        path=_ORCHESTRATE,
        locate=_item_of("8. **Point the worker at the preamble FILE"),
        required=(
            _Check("a leading NAME=value can be denied by a shell hook", _SHELL_HOOK),
            _Check("substitute: put the value inline", _INLINE),
            _Check("substitute: a script file for multi-step logic", _SCRIPT_FILE),
            _Check(
                "substitute: the UTF-8 mode flag instead of an environment variable",
                f"{_UTF8_FLAG} {_NOT_AN_ENV_VAR}",
            ),
            _Check("a harness may refuse a report-file write", _REFUSAL),
            _Check(
                "such a sub-agent returns its findings as text",
                "such a sub-agent returns its findings as text",
            ),
            _Check(
                "write-early applies only to workers allowed to write",
                "applies only to workers allowed to write",
            ),
            _Check(
                "the template restates both harness lines", "the template restates both"
            ),
            _Check("the write-early lead is conditional", _ITEM_8_LEAD),
            _Check("the refusal sentence, whole", _ITEM_8_REFUSAL),
            _Check(
                "the exception to point, don't paste, and why the template restates both",
                _ITEM_8_EXCEPTION,
            ),
            _Check("the shell-hook sentence, whole", _ITEM_8_SHELL_SENTENCE),
            _Check("the other limit is the refused report file", _ITEM_8_OTHER_LIMIT),
        ),
        retired=(
            _Check(
                "the write-early lead with no condition",
                "*Write the report file EARLY and INCREMENTALLY.* State this in the brief.",
            ),
        ),
        old=_OLD_ITEM_8,
        kept=(_Check("point, don't paste", "*Point, don't paste.*"),),
    ),
    _Place(
        name="orchestrate-item-9",
        path=_ORCHESTRATE,
        locate=_without_quote_marks(_item_of("9. **The close block")),
        required=(
            _Check(
                "a sub-agent barred from writing returns the handoff content as text",
                "a sub-agent whose harness refuses the write returns the handoff content as text",
            ),
            _Check("the sentence, whole, pointing at item 8", _ITEM_9_SENTENCE),
            _Check(
                "the step the sentence names is the one that saves into the handoff",
                "4. Save everything into the handoff (the report file or return note your "
                "brief names).",
            ),
        ),
        old=_OLD_ITEM_9,
    ),
    _Place(
        name="brief-template",
        path=_TEMPLATE,
        locate=_first_fenced_block,
        required=(
            _Check(
                "the heading says two harness limits are restated",
                "only two harness limits are restated below",
            ),
            _Check(
                "the shell-hook line",
                "Shell hook: a leading `NAME=value` assignment before a command can be denied.",
            ),
            _Check("substitute: put the value inline", "Put the value inline"),
            _Check("substitute: a script file for multi-step logic", _SCRIPT_FILE),
            _Check(
                "substitute: the UTF-8 mode flag instead of an environment variable",
                f"{_UTF8_FLAG} {_NOT_AN_ENV_VAR}",
            ),
            _Check(
                "the report-file line",
                "Report file: a harness may refuse a sub-agent's write of a report file.",
            ),
            _Check(
                "a refused worker returns its findings as text",
                "return your findings as text",
            ),
            _Check(
                "write-early applies only if the worker may write",
                "applies only if you are allowed to write",
            ),
            _Check(
                "the report paragraph is conditional on being allowed to write",
                "If you may write files, write this report file EARLY and INCREMENTALLY",
            ),
            _Check(
                "the budget line: sessions needed and the split, before phase 1",
                "Budget: <how many sessions this work needs and how it splits, written before phase 1>",
            ),
            _Check("the heading, whole", _TEMPLATE_HEADING),
            _Check("the shell-hook line, whole", _TEMPLATE_SHELL_LINE),
            _Check("the report-file line, whole", _TEMPLATE_REPORT_LINE),
            _Check("the budget line, whole", _TEMPLATE_BUDGET_LINE),
            _Check("the report paragraph, whole", _TEMPLATE_REPORT_PARAGRAPH),
        ),
        retired=(
            _Check(
                "the heading that said nothing is restated", "it is not restated below"
            ),
        ),
        old=_OLD_TEMPLATE,
    ),
    _Place(
        name="brief-template-rules-of-thumb",
        path=_TEMPLATE,
        locate=_item_of("- **Inline the TASK-SPECIFIC source of truth"),
        required=(
            _Check(
                "the two harness limits are the one exception to restating no rule inline",
                _TEMPLATE_EXCEPTION,
            ),
        ),
        old=_OLD_TEMPLATE_RULES,
        kept=(_Check("the rule of thumb itself", "POINT at the standing rules"),),
    ),
)


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """Seven places in three files, each file present and non-empty."""
    assert len(_PLACES) == 7, f"{len(_PLACES)} places, not the 7 stated"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 3, f"{len(paths)} distinct files, not 3: {sorted(paths)}"
    names = [place.name for place in _PLACES]
    assert len(set(names)) == len(names), "two places share a name"
    empty = [path for path in sorted(paths) if not _read(path).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_states_the_two_harness_limits(place: _Place) -> None:
    """Red before the change: no place said a leading assignment can be denied or that a
    report-file write can be refused, and the template's rule of thumb named no exception."""
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_fails_on_the_text_it_replaced(place: _Place) -> None:
    """Fired at the old text: every required check reports it, every retired phrase is seen, and
    what has to stay is still there (it is the one kind of check that passes on the old text)."""
    reported = _gaps(place, place.old)
    expected = [f"missing: {c.label}" for c in place.required]
    expected += [f"retired wording still there: {c.label}" for c in place.retired]
    assert reported == expected, (
        f"{place.name}: on the old text the checks reported {reported}, not {expected}"
    )


def test_the_shell_hook_line_is_outside_the_block_an_adopter_replaces() -> None:
    """An adopter replaces the blockquote of section 0. A limit written inside it goes with it,
    so the line must be found in the section with its blockquote lines removed, and the
    blockquote must still be there to replace."""
    section = _section(_read(_PREAMBLE), "## 0 ·")
    quoted = [line for line in section.split("\n") if line.startswith(">")]
    assert quoted, "section 0 has no block to replace any more"
    assert "NAME=value" not in "\n".join(quoted), (
        "the shell-hook limit sits inside the block"
    )
    assert "NAME=value" in section


def test_the_blockquote_filter_sees_a_limit_written_inside_the_block() -> None:
    inside = "## 0 · Host rules\n\n> **Adopters: replace this block.** A leading `NAME=value`\n> assignment can be denied.\n"
    assert "NAME=value" in _section(inside, "## 0 ·")
    assert "NAME=value" not in _without_blockquotes(_section(inside, "## 0 ·"))


def test_the_close_block_is_not_reworded() -> None:
    """The close block is pasted verbatim into every brief, so the fallback for a refused write
    goes beside it and not in it: the five steps read as they do now, in the same words in the
    contract and in the template. (The block was reworded once on purpose, when the review skill,
    the lessons step and the handoff's name were added; this pins the wording after that.)"""
    steps = (
        "1. Self-challenge: is it detailed enough? Have you missed something? Say what it changed, "
        'including "nothing".',
        "2. Then the completion review: run `lemmi-ai-kit-core:post-task-review` through the "
        "Skill tool, whatever the size of the task (a hand-written review does not replace it), "
        "if you have not already run it. Both run BEFORE the handoff.",
        "3. Lessons: run `lemmi-ai-kit-core:task-learnings`. If your brief bars the learnings "
        "buffer, put the lesson drafts in your handoff and say so in your closing message.",
        "4. Save everything into the handoff (the report file or return note your brief "
        "names).",
        "5. Then write a short summary for whoever reads it next: bullets, at most 10 lines, "
        "plain language, no internal ids, with the review's step list and the lessons result in "
        "it, and say in plain words that the session may be closed.",
    )
    quoted = _list_item(_read(_ORCHESTRATE), "9. **The close block")
    contract = _folded(re.sub(r"(?m)^\s*>\s?", "", quoted))
    template = _folded(_first_fenced_block(_read(_TEMPLATE)))
    for step in steps:
        assert step in contract, f"the contract lost: {step}"
        assert step in template, f"the template lost: {step}"


def _planted_item_9(step_four: str) -> str:
    """Item 9 cut down to what its place reads: a blockquote holding the Close block, whose fourth
    step is `step_four`, and the sentence after the block. It is planted, so that the test below
    does not depend on how the real file wraps its lines."""
    return (
        "9. **The close block** paste it verbatim into every brief.\n\n"
        "   > **Close, run in this order.**\n"
        "   > 1. Self-challenge: one.\n"
        f"   {step_four}\n"
        "   > 5. Then write a short summary: five.\n\n"
        f"   {_ITEM_9_SENTENCE}\n"
        "10. **Another item.**\n"
    )


def test_a_re_wrapped_close_block_is_read_whole() -> None:
    """The Close block is a blockquote, and a step can wrap onto a second quoted line at any
    word. The step that saves into the handoff is still found when the quoted line breaks inside
    it, and is still reported when its number or its words change."""
    place = next(p for p in _PLACES if p.name == "orchestrate-item-9")
    saves = (
        "> 4. Save everything into the handoff (the report file or return note your "
        "brief names)."
    )
    assert _gaps(place, _planted_item_9(saves)) == []
    wraps = (
        "> 4. Save everything into the handoff\n"
        "   > (the report file or return note your brief names).",
        "> 4. Save everything into\n   >    the handoff (the report file or return\n"
        "   >    note your brief names).",
        "> 4.\n   >    Save everything into the handoff (the report file or return note "
        "your brief names).",
    )
    for wrapped in wraps:
        assert wrapped != saves and "\n" in wrapped, "the planted wrap changed nothing"
        assert _gaps(place, _planted_item_9(wrapped)) == [], wrapped
    changed = (
        saves.replace("4.", "3."),
        saves.replace("everything", "it"),
        saves.replace(" (the report file or return note your brief names)", ""),
    )
    for other in changed:
        gaps = _gaps(place, _planted_item_9(other))
        assert len(gaps) == 1 and "saves into the handoff" in gaps[0], (other, gaps)


def test_a_re_wrapped_item_is_read_whole() -> None:
    """Item 8 is re-wrapped so that its continuation lines sit in column 0, and every place that
    reads it still finds its sentences: the reader stops at the next item, not at the first line
    that is not indented."""
    text = _read(_ORCHESTRATE)
    lines = _list_item(text, "8. **Point the worker at the preamble FILE").split("\n")
    wrapped = [lines[0]]
    for previous, line in zip(lines, lines[1:], strict=False):
        continues = (
            bool(previous.strip() and line.strip()) and _MARKER.match(line) is None
        )
        wrapped.append(line.strip() if continues else line)
    assert wrapped != lines, "the planted wrap changed nothing"
    place = next(p for p in _PLACES if p.name == "orchestrate-item-8")
    assert _gaps(place, "\n".join([*wrapped, "9. **The close block", ""])) == []
    assert not _has(_folded(lines[0]), _ITEM_8_REFUSAL), (
        "the planted wrap hides nothing"
    )
