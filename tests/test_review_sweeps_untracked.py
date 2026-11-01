"""Step 0 of `post-task-review` counts untracked files, and every sweep says which form it ran.

Step 0 ran `git diff --name-only HEAD` and `git grep -n "<symbol>" -- <source-roots>` and called
them "the two commands above". Neither sees a file the task created and has not added: a new test
file that uses a type throughout, or a new spec document, stayed invisible to the sweep, and the
dependents list read as complete when it was a floor. `git grep --untracked` finds such a file and
still skips the ignored ones. Git refuses the flag together with a revision, so a ref-based "did it
land?" grep keeps its form, and only Step 0's block is checked for a plain `git grep`.

The sentences of the rule live once, in a row of section 7 of the gate-output reference: the
`--untracked` form and its ignored-file limit, the new files `git ls-files --others` lists, that
every sweep counts untracked files and says which form ran, and the one deliberate exception (the
Untracked-dependency check reads the tracked tree). Step 0's limits list is one line that says plain
`git grep` and `git diff HEAD` see tracked files only and points at that section, so SKILL.md stays
short; the row is asserted to carry the sentences, and Step 0 is asserted not to repeat them.

THE SURFACE, in numbers the tests assert: 3 places in 3 files (Step 0 of SKILL.md, section 7 of the
gate-output reference, Step 0 of the review checklist), and in Step 0 one fenced block of 3
commands, exactly 1 of them a `git grep`. The orchestration places of the same rule are asserted by
that pack's own tests, not here.

Every check is fired at the text its place carried before (`_OLD_*`, each an unedited excerpt of the
file as it stood), and each must report it. The block scan is fired at a planted plain `git grep`
first, so a green result on the real block means the scan can see one. The pointer check and the
no-repeat check are also fired at Step 0's limits list as the first round wrote it (the rule's four
sentences in four lines, no link), and the two row checks that carry the moved sentences at the row
as it stood before they moved into it.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
)
_SKILL_MD = _SKILL / "SKILL.md"
_GATE_OUTPUT = _SKILL / "references" / "reading-gate-output.md"
_CHECKLIST = _SKILL / "references" / "review-checklist.md"

_HEADING = re.compile(r"^(#{1,6})\s")
_FORM_RAN = "which form ran next to"


# --- the instruments ------------------------------------------------------------------------------


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and every run of whitespace folded to one space, so a
    re-wrapped line or a re-emphasised word is not a different sentence."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _section(text: str, heading: str, where: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or a
    higher level. A `#` line inside a fenced block is not a heading. A missing heading fails with
    the heading named, so a renamed section is a loud failure and never an empty match."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        found = None if in_fence or fence else _HEADING.match(line)
        if fence:
            in_fence = not in_fence
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


def _fenced_blocks(section: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] | None = None
    for line in section.split("\n"):
        if line.lstrip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append("\n".join(current))
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def _outside_fences(section: str) -> str:
    kept: list[str] = []
    in_fence = False
    for line in section.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            kept.append(line)
    return "\n".join(kept)


def _commands(block: str) -> list[str]:
    """The command part of every non-empty line of a block, its trailing comment dropped, so a
    comment that mentions a flag does not count as the flag."""
    found: list[str] = []
    for line in block.split("\n"):
        command = line.split("#", 1)[0].strip()
        if command:
            found.append(command)
    return found


def _greps(block: str) -> list[str]:
    return [c for c in _commands(block) if c.startswith("git grep")]


def _step_0_block(section: str) -> str:
    blocks = _fenced_blocks(section)
    assert len(blocks) == 1, (
        f"Step 0 holds {len(blocks)} fenced blocks, not the 1 scanned"
    )
    return blocks[0]


def _table_rows(section: str, needle: str) -> list[str]:
    """The table rows (a line that starts and ends with a pipe) that mention `needle`."""
    return [
        line
        for line in section.split("\n")
        if line.startswith("|") and line.rstrip().endswith("|") and needle in line
    ]


def _checklist_rows(section: str) -> list[str]:
    """Every checklist row of the section as one string: its `- [ ]` line and the lines that
    continue it, up to a blank line or the start of another block, so a row wrapped over two
    lines is the same row."""
    rows: list[str] = []
    open_row = False
    for line in section.split("\n"):
        if line.startswith("- [ ]"):
            rows.append(line)
            open_row = True
        elif not line.strip() or line.startswith(("- ", "* ", "#", "|", ">", "```")):
            open_row = False
        elif open_row:
            rows[-1] += " " + line.strip()
    return rows


def _list_lines(section: str, needle: str) -> list[str]:
    return [row for row in _checklist_rows(section) if needle in row]


# --- the checks of each place ---------------------------------------------------------------------


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


def _prose_says(*needles: str) -> Callable[[str], bool]:
    return lambda section: all(n in _plain(_outside_fences(section)) for n in needles)


def _prose_lacks(needle: str) -> Callable[[str], bool]:
    return lambda section: needle not in _plain(_outside_fences(section))


def _every_grep_counts_untracked(section: str) -> bool:
    greps = _greps(_step_0_block(section))
    return bool(greps) and all("--untracked" in g for g in greps)


def _block_lists_new_files(section: str) -> bool:
    return any(
        c.startswith("git ls-files --others --exclude-standard")
        for c in _commands(_step_0_block(section))
    )


def _block_has_the_reader_line(section: str) -> bool:
    return 'git grep -n --untracked "<symbol>" -- <source-roots>' in _commands(
        _step_0_block(section)
    )


def _row_says(*needles: str) -> Callable[[str], bool]:
    """One table row of the section carries every needle, so the rule is a row and not loose prose."""
    return lambda section: any(
        all(n in _plain(row) for n in needles)
        for row in _table_rows(section, "--untracked")
    )


def _line_says(*needles: str) -> Callable[[str], bool]:
    return lambda section: any(
        all(n in _plain(line) for n in needles)
        for line in _list_lines(section, "--untracked")
    )


_SECTION_7_LINK = "(references/reading-gate-output.md)"
_TRACKED_ONLY = "Plain git grep and git diff HEAD see tracked files only"
_POINTER_LABEL = "the limits list points at section 7 of the gate-output reference"
_ROW_SCOPE_LABEL = "that row says every sweep for readers counts untracked files"
_ROW_EXCEPTION_LABEL = (
    "that row keeps the Untracked-dependency check on the tracked tree on purpose"
)
# The sentences of the rule that the row of section 7 carries once, in the words the limits list
# used before it became a pointer.
_ROW_SENTENCES = (
    "git grep --untracked adds it and still skips ignored files",
    "Every sweep for readers of a symbol, a claim or an old name counts untracked files",
    "the Untracked-dependency check reads the tracked tree on purpose",
)


def _bullets(section: str) -> list[str]:
    """Every list item of the section outside its fenced blocks: its `- ` line and the indented
    lines that continue it, folded to one line, so a re-wrapped item is the same item."""
    items: list[str] = []
    open_item = False
    for line in _outside_fences(section).split("\n"):
        if line.startswith("- "):
            items.append(line)
            open_item = True
        elif open_item and line.startswith("  ") and line.strip():
            items[-1] += " " + line.strip()
        else:
            open_item = False
    return [_plain(item) for item in items]


def _points_at_section_7(section: str) -> bool:
    """One list item says plain git grep and git diff HEAD see tracked files only and links the
    gate-output reference at its section 7, where the sweep forms and their limits are."""
    return any(
        _TRACKED_ONLY in item and _SECTION_7_LINK in item and "§ 7" in item
        for item in _bullets(section)
    )


def _repeated_row_sentences(section: str) -> list[str]:
    """The sentences of the row that the prose of the section still carries: the row says them
    once, and a second copy is a second place to keep true."""
    prose = _plain(_outside_fences(section))
    return [sentence for sentence in _ROW_SENTENCES if sentence in prose]


_STEP_0_CHECKS: tuple[_Check, ...] = (
    _Check(
        "every git grep of the block carries --untracked", _every_grep_counts_untracked
    ),
    _Check(
        "the block lists git ls-files --others for new files", _block_lists_new_files
    ),
    _Check(
        "the block's reader line is the --untracked form", _block_has_the_reader_line
    ),
    _Check(
        _POINTER_LABEL,
        _points_at_section_7,
    ),
    _Check(
        "the minimum is the three commands", _prose_says("the three commands above")
    ),
    _Check("Step 0 no longer says two commands", _prose_lacks("two commands")),
)
_GATE_OUTPUT_CHECKS: tuple[_Check, ...] = (
    _Check(
        "a table row says plain git grep and git diff see tracked files only",
        _row_says("tracked files only", "git diff --name-only HEAD"),
    ),
    _Check(
        "that row gives the --untracked form and its ignored-file limit",
        _row_says("git grep -n --untracked adds them and still skips ignored files"),
    ),
    _Check(
        "that row lists new files with git ls-files --others --exclude-standard",
        _row_says("git ls-files --others --exclude-standard lists them"),
    ),
    _Check(
        "that row says git refuses --untracked with a revision",
        _row_says("Git refuses --untracked with a revision"),
    ),
    _Check(
        "that row says which form ran next to the count",
        _row_says("Say which form ran next to the count"),
    ),
    _Check(
        _ROW_SCOPE_LABEL,
        _row_says(
            "Every sweep for readers of a symbol, a claim or an old name counts untracked files"
        ),
    ),
    _Check(
        _ROW_EXCEPTION_LABEL,
        _row_says("(the Untracked-dependency check reads the tracked tree on purpose)"),
    ),
)
_CHECKLIST_CHECKS: tuple[_Check, ...] = (
    _Check(
        "a checklist line names git grep -n --untracked",
        _line_says("git grep -n --untracked"),
    ),
    _Check(
        "that line lists new files with git ls-files --others --exclude-standard",
        _line_says("git ls-files --others --exclude-standard"),
    ),
    _Check(
        "that line says which form ran next to its count",
        _line_says(f"{_FORM_RAN} its count"),
    ),
)


class _Place(NamedTuple):
    name: str
    path: Path
    heading: str
    checks: tuple[_Check, ...]
    old: str


# --- the text each place carried before -----------------------------------------------------------

_OLD_STEP_0 = r"""### Step 0: Dependency & Blast Radius (produces a LIST, not an opinion)

**Run this before steps 1–6 — and ideally before the change itself.** Step 7 is *documentation*
impact: which docs to update afterwards. This step is the other question entirely: **what does this
change break?** Nothing else in this pipeline asks it.

For every symbol the diff adds, removes, renames or changes the signature of, enumerate its
dependents and **write the list down**:

```bash
git diff --name-only HEAD          # the changed files
git grep -n "<symbol>" -- <source-roots>   # every reader, per changed symbol
```

Then, for each dependent, record one of: *checked and unaffected* · *checked and updated* ·
**UNKNOWN**. An entry you did not open is `UNKNOWN`, never "assumed fine".

**Why this is a step and not advice.** In one measured window a session changed a flag and reported:
*"Four sites set `<flag>`; I checked two, assumed a third, never opened the fourth."* The outcome
was a live production regression. In the same window a diff-driven impact tool was built for exactly
this, honestly backtested from 0/10 to 7/10 answerability, probe-stamped — and **gated nothing**:
the corpus's maintain interface ran **738×** against **5** impact queries, a 33:1 ratio of
maintaining the asset to consulting it. *Measured and wired in are independent properties, and only
the second changes outcomes.* A dependency check that produces no artifact is not wired in.

**State the instrument's limits next to its answer**, or the list will be read as complete when it
is a floor:

- A caller list derived by grep or by a generated index is typically a **subset** — dynamic
  dispatch, reflection, string-keyed lookup and config-driven wiring are invisible to it.
- Any authored (hand-maintained) dependency record is a claim about the tree, and can be stale in
  both directions at once.
- So an impact answer is a **floor, not a complete set**. That is fine — but only if it is said at
  the point of use, not in a caveat elsewhere.

If the project ships a diff-driven impact tool, run it here and paste its output. If it does not,
the two commands above are the minimum.
"""

_OLD_GATE_OUTPUT_7 = r"""## 7. Concrete command traps — each one ran, exited 0, and answered a different question

Measured instances. Every row below produced a confident wrong answer that drove a decision.

| Command shape | What you think it does | What it does |
|---|---|---|
| `grep -E 'a\|b'` | alternation | `\|` inside `-E` is a **literal pipe**; `-E` wants a bare `\|`. Four "0 files untracked" results in one sweep were silent zeros |
| `git grep 'def name\b'` | word-boundary match | plain `git grep` is BRE and does not know `\b` — reported **29 real tests ABSENT**. Use `-E` |
| `git grep <pat> HEAD` | searches your fix | searches the **commit**, so your just-applied worktree fix reads as still-broken |
| `git grep <pat>` (no rev) | searches the committed tree | searches the **worktree**, so a "has it landed?" gate passes on a peer's uncommitted edit |
| `grep -r -- "$p" DIR --include='*.md'` | restricts to the glob | the `--include` after the path is ignored; it searches **everything**. The giveaway is on **stderr** |
| `git diff --stat` (one number) | insertions | that number is **added + removed**. Use `--numstat` for any count you write down |
| `git diff --stat` (paths) | full paths | long paths are **abbreviated** with `...`, so grepping its output for a directory reports "only READMEs changed" for exactly the deep files you were looking for |
| `git log -- <path> --invert-grep --grep=X` | excludes X | flags after `--` are **pathspecs**, so it counts instead of excluding |
| `echo "$(cmd) rc=$?"` | the command's status | `$?` is the **command substitution's** status — seven failing gates read as `rc=0` |
| `cmd > out.log` (long run) | you will see the error | Python buffers stdout, so a hang and a crash look **identical** from outside. Use unbuffered output or check the process |
| `ls <path> 2>&1 \| grep <pat>` in a DoD | proves presence | the *error text* contains the path, so absence reports as success |
| `str.index("## Heading")` | finds the heading | matches the **prose that mentions** the heading first — silently duplicated a 166 KB document |
| a `\b` written into generated file **content** | a regex boundary | arrives at the next reader as the **BACKSPACE escape** (`0x08`), putting invisible bytes into a committed file |
| an italic-span regex over markdown | italics | swallows every **bold** span too, so a citation audit can report a whole document as uncited |
| a single-quoted heredoc holding `\\` | literal backslashes | the Bash tool still mangles them, so a Python script silently stops matching. Write the script to a **file** |
| `grep` on a wide table row | the whole line | the harness may print `[Omitted long matching line]`; read the span with one file read rather than one read per line |

The general rule underneath all of them: **run the command against a case whose answer you already
know before you trust it on a case whose answer you don't.** Every row here would have been caught
by a single known-positive/known-negative pair.
"""

_OLD_CHECKLIST_0 = r"""## Step 0: Dependency & Blast Radius

- [ ] Ran BEFORE steps 1–6 (ideally before the change itself)
- [ ] Produced a LIST of affected callers/callees/tests — not an opinion
- [ ] Every item in that list either reviewed or explicitly excluded with a reason
"""

# The limits list of Step 0 as the first round wrote it: the sentences of the rule in four lines of
# the list, no link. An unedited excerpt of SKILL.md at that commit.
_FIRST_ROUND_LIMITS = r"""- Plain `git grep` and `git diff HEAD` see tracked files only: a file the task created and has not
  added is invisible to them. `git grep --untracked` adds it and still skips ignored files. Every
  sweep for readers of a symbol, a claim or an old name counts untracked files, and says which form
  ran next to the count (the Untracked-dependency check reads the tracked tree on purpose).
"""

# The row of section 7 as it stood before the scope sentence and the exception moved into it: an
# unedited excerpt of the reference at the same commit.
_FIRST_ROUND_ROW = r"""| `git grep -n "<symbol>"` or `git diff --name-only HEAD` as the sweep of a task's files | every reader, every changed file | **tracked** files only: a file the task created and has not added is invisible to both, so the sweep is silent about the files you wrote. `git grep -n --untracked` adds them and still skips ignored files; `git ls-files --others --exclude-standard` lists them. Git refuses `--untracked` with a revision, so a ref-based "did it land?" grep stays as it is. Say which form ran next to the count |"""

_PLACES: tuple[_Place, ...] = (
    _Place("skill-step-0", _SKILL_MD, "### Step 0:", _STEP_0_CHECKS, _OLD_STEP_0),
    _Place(
        "gate-output-section-7",
        _GATE_OUTPUT,
        "## 7.",
        _GATE_OUTPUT_CHECKS,
        _OLD_GATE_OUTPUT_7,
    ),
    _Place(
        "checklist-step-0",
        _CHECKLIST,
        "## Step 0:",
        _CHECKLIST_CHECKS,
        _OLD_CHECKLIST_0,
    ),
)


def _gaps(place: _Place, text: str) -> list[str]:
    section = _section(text, place.heading, place.path.name)
    return [c.label for c in place.checks if not c.holds(section)]


# --- the tests ------------------------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    """3 places in 3 distinct files, each present, and one block of 3 commands with 1 git grep."""
    assert len(_PLACES) == 3, f"{len(_PLACES)} places, not the 3 stated"
    paths = {place.path for place in _PLACES}
    assert len(paths) == 3, f"{len(paths)} distinct files, not 3"
    empty = [str(p) for p in paths if not _read(p).strip()]
    assert not empty, f"{len(empty)} of {len(paths)} files are empty: {empty}"
    block = _step_0_block(_section(_read(_SKILL_MD), "### Step 0:", "SKILL.md"))
    assert len(_commands(block)) == 3, f"Step 0's block holds {_commands(block)}"
    assert len(_greps(block)) == 1, (
        f"Step 0's block holds {len(_greps(block))} git grep"
    )


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_counts_untracked_files(place: _Place) -> None:
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path.name} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The old text carried none of the new wording, so each check must say so: a check that
    passes on it tests nothing."""
    reported = _gaps(place, place.old)
    assert len(reported) == len(place.checks), (
        f"{place.name}: {len(reported)} of {len(place.checks)} checks saw the old text; "
        f"blind: {[c.label for c in place.checks if c.label not in reported]}"
    )


def test_the_block_scan_sees_a_planted_plain_git_grep() -> None:
    """The scan is fired at planted blocks first: a plain git grep, one whose trailing comment
    only mentions the flag, and a block that has no git grep at all."""
    plain = (
        "### Step 0: planted\n\n```bash\n"
        "git diff --name-only HEAD\n"
        'git grep -n "<symbol>" -- <source-roots>   # add --untracked here\n'
        "```\n"
    )
    assert _greps(_step_0_block(plain)) == ['git grep -n "<symbol>" -- <source-roots>']
    assert not _every_grep_counts_untracked(plain)
    assert not _block_has_the_reader_line(plain)

    fixed = plain.replace(
        'git grep -n "<symbol>"', 'git grep -n --untracked "<symbol>"'
    )
    assert _every_grep_counts_untracked(fixed)
    assert _block_has_the_reader_line(fixed)

    no_grep = "### Step 0: planted\n\n```bash\ngit diff --name-only HEAD\n```\n"
    assert not _every_grep_counts_untracked(no_grep), "an empty scan must not pass"
    assert not _block_lists_new_files(no_grep)


def test_step_0_points_at_the_row_and_does_not_repeat_it() -> None:
    """The limits list says in one line that plain git grep and git diff HEAD see tracked files
    only and points at section 7 of the gate-output reference, where the forms and their limits are
    stated once. Step 0 does not carry a second copy of the row's sentences."""
    section = _section(_read(_SKILL_MD), "### Step 0:", "SKILL.md")
    assert _points_at_section_7(section), (
        "Step 0's limits list has no pointer to section 7"
    )
    assert _repeated_row_sentences(section) == [], (
        "Step 0 repeats sentences that section 7 carries"
    )
    assert _GATE_OUTPUT.is_file(), "the pointer's target does not exist"


def test_the_pointer_and_no_repeat_checks_see_the_limits_list_as_it_stood_and_planted() -> (
    None
):
    """Fired at the limits list as the first round wrote it (no link; all three row sentences in
    Step 0), then at planted lists: a pointer, the same pointer wrapped over two lines, one that
    links another file, names no section, states no limit or sits in a fenced block, and a pointer
    with one of the row's sentences copied beside it."""
    head = "### Step 0: planted\n\n"
    as_it_stood = head + _FIRST_ROUND_LIMITS
    assert not _points_at_section_7(as_it_stood)
    assert _repeated_row_sentences(as_it_stood) == list(_ROW_SENTENCES)

    pointer = (
        "- Plain `git grep` and `git diff HEAD` see tracked files only: "
        "[the untracked forms](references/reading-gate-output.md), § 7.\n"
    )
    assert _points_at_section_7(head + pointer)
    assert _repeated_row_sentences(head + pointer) == []
    wrapped = (
        "- Plain `git grep` and `git diff HEAD` see tracked files only:\n"
        "  [the untracked forms](references/reading-gate-output.md), § 7.\n"
    )
    assert _points_at_section_7(head + wrapped)
    for name, text in {
        "another file": pointer.replace("reading-gate-output", "review-checklist"),
        "no section": pointer.replace(", § 7", ""),
        "no limit": pointer.replace("see tracked files only", "see little"),
        "a fenced block": f"```text\n{pointer}```\n",
    }.items():
        assert not _points_at_section_7(head + text), name
    copied = pointer + f"- {_ROW_SENTENCES[1]}.\n"
    assert _repeated_row_sentences(head + copied) == [_ROW_SENTENCES[1]]


def test_the_row_checks_that_carry_the_moved_sentences_report_the_row_as_it_stood() -> (
    None
):
    """Fired at the row before the scope sentence and the exception moved into it: the five checks
    it already satisfied hold, and the two that carry the moved sentences report it."""
    place = next(p for p in _PLACES if p.name == "gate-output-section-7")
    text = "## 7. planted\n\n| a | b | c |\n|---|---|---|\n" + _FIRST_ROUND_ROW + "\n"
    assert _gaps(place, text) == [_ROW_SCOPE_LABEL, _ROW_EXCEPTION_LABEL]


def test_the_checks_that_join_needles_or_greps_need_every_one() -> None:
    """Fired at planted text that holds one of two needles, and at a block of two greps of which
    one is plain: a join that settled for any would pass them. The plain block above holds one
    grep, where any and all read the same."""
    prose = "### Step 0: planted\n\nalpha and beta, not gamma.\n"
    assert _prose_says("alpha", "beta")(prose)
    assert not _prose_says("alpha", "delta")(prose)

    mixed = (
        "### Step 0: planted\n\n```bash\n"
        'git grep -n --untracked "<symbol>" -- <source-roots>\n'
        'git grep -n "<other>" -- <source-roots>\n'
        "```\n"
    )
    assert len(_greps(_step_0_block(mixed))) == 2
    assert not _every_grep_counts_untracked(mixed), "a plain grep among two must fail"

    table = "| `--untracked` alpha | beta |\n"
    assert _row_says("alpha", "beta")(table)
    assert not _row_says("alpha", "delta")(table)

    rows = "- [ ] a row with --untracked and alpha\n"
    assert _line_says("alpha", "--untracked")(rows)
    assert not _line_says("alpha", "delta")(rows)


def test_the_slicers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "### Step 0: planted",
            "Some **prose** with `git grep --untracked`.",
            "```bash",
            "# a comment line inside a fence is not a heading",
            "git ls-files --others --exclude-standard -- src",
            "```",
            "| `a` | b | c |",
            "- [ ] a line with --untracked",
            "### Next",
            "after the section",
        ]
    )
    section = _section(planted, "### Step 0:", "planted")
    assert "after the section" not in section and "a comment line" in section
    assert _plain(_outside_fences(section)).startswith("### Step 0: planted Some prose")
    assert "git ls-files" not in _outside_fences(section)
    assert _commands(_fenced_blocks(section)[0]) == [
        "git ls-files --others --exclude-standard -- src"
    ]
    assert _table_rows(section, "a") == ["| `a` | b | c |"]
    assert _list_lines(section, "--untracked") == ["- [ ] a line with --untracked"]
    wrapped = "- [ ] a row that\n  continues here with --untracked\n\nnot part of it\n- [ ] next"
    assert _checklist_rows(wrapped) == [
        "- [ ] a row that continues here with --untracked",
        "- [ ] next",
    ]
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### Step 9", "planted")
    with pytest.raises(AssertionError, match="fenced blocks"):
        _step_0_block("### Step 0: planted\n\nno block here\n")
