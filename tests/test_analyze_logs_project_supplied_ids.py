"""`analyze-logs` takes its task prefixes and its correlation fields from the project.

The step that creates task files listed four prefixes, one of them for missing functionality,
and the task-file template carried the same row. Some projects reserve that prefix for product
work, and a log finding is not a product request, so the skill filed a task under a prefix the
project had not offered it. The rule against quoting a raw `grep -c` as a frequency ran a grep
that named two fields, an id for a background job and an id for a session; a project whose ids
are spelled another way, or that runs no jobs, got a command that matches nothing and a count
of zero. The skill already holds a field map (Step 1a) with a Correlation id role that the
analyst fills from the real file, and the grep did not use it.

What the text says now: the prefixes are the ones the project's own task conventions define and
its AGENTS.md names; a task for missing functionality has no default prefix; the grep names its
field by a placeholder, and the rule sends the analyst to the Correlation id row of the Step 1a
field map for it. The query-template reference keeps its labelled job id example, so the ban on
that name is scoped to SKILL.md and no ban is run over the references.

Four clauses keep that text in agreement with the text around it. The container column of the
Correlation id row holds an id inside the message text, not a quoted key, so the rule says to drop
the double quotes from the pattern for it. The bullet for missing functionality is an exception to
the step's own rule that every issue of MEDIUM or above gets a task file, and to the task files
Step 4b asks for (its completeness check and its action list), so it says so, and it names the
prefix some projects reserve for product work where a bare pronoun once stood for it; the
template row says the same.

THE SURFACE, in numbers the tests assert: 2 files are scanned (the skill and its task-file
template) for 3 bans in all (the new-work prefix in both, the job id in the skill only), 1 fenced
block of the skill is read for its grep, 3 places say where a name comes from, and 4 clauses make
the new text agree with the text around it. The one reference the bans are not run over is
asserted to lie outside the scan. Each helper is fired at planted text that holds the old shape,
and at a near miss it must not flag, before its silence on the real files is trusted. The section
reader is also fired at a `#` line inside a fenced block, which is a comment and never a heading.
"""

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO / "plugins" / "core" / "skills" / "analyze-logs"
_SKILL = _SKILL_DIR / "SKILL.md"
_TEMPLATE = _SKILL_DIR / "references" / "task-file-template.md"
# The reference that keeps its labelled job id example. No ban is run over it.
_QUERY_TEMPLATES = _SKILL_DIR / "references" / "gcp-query-templates.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
# The correlation grep as the new text writes it: its -E pattern holds placeholders only.
_PLACEHOLDER_GREP = re.compile(r"""grep -E '"\(<[^<>]+>(?:\|<[^<>]+>)*\)"'""")

_EM = chr(0x2014)
_NEW_WORK_PREFIX = "FEATURE-"
_JOB_ID = "job_id"
_SESSION_ID = "session_id"

# What each file may no longer name. The job id is banned in the skill alone: the query
# templates keep it as a labelled example.
_BANS: dict[Path, tuple[str, ...]] = {
    _SKILL: (_NEW_WORK_PREFIX, _JOB_ID),
    _TEMPLATE: (_NEW_WORK_PREFIX,),
}

# Where the new text says a name comes from: the file, the section that holds the words, the words.
_SOURCES: tuple[tuple[Path, str, str], ...] = (
    (
        _SKILL,
        "### Step 5",
        "the project's own task conventions define them; its AGENTS.md names them",
    ),
    (_SKILL, "## Ground Rules", "the Correlation id row of the Step 1a field map"),
    (
        _TEMPLATE,
        "## Prefix Selection",
        "the prefixes the project's own task conventions define",
    ),
)

# What the new text says so that it agrees with the text around it: the file, the section that
# holds the words, the words, and the label the test id carries.
_CLAUSES: tuple[tuple[Path, str, str, str], ...] = (
    (_SKILL, "## Ground Rules", "drop the double quotes from the pattern", "quotes"),
    (_SKILL, "### Step 5", "Exception, here and in Step 4b", "exception"),
    (
        _SKILL,
        "### Step 5",
        "reserve the new-work prefix for product work",
        "reason",
    ),
    (
        _TEMPLATE,
        "## Prefix Selection",
        "reserve the new-work prefix for product work",
        "template-reason",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def _fenced_blocks(text: str) -> list[str]:
    """The text inside each fenced block, without its fence lines."""
    blocks: list[str] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if _is_fence(line):
            if current is not None:
                blocks.append("\n".join(current))
            current = [] if current is None else None
        elif current is not None:
            current.append(line)
    return blocks


def _correlation_block(text: str, where: str) -> str:
    """The one fenced block that holds the correlation grep: the one that ends in `sort -u`.

    None or several fail loudly with the count named, so a moved or duplicated command is a
    loud failure and never an empty match.
    """
    found = [block for block in _fenced_blocks(text) if "sort -u" in block]
    if len(found) != 1:
        raise AssertionError(
            f"{where}: expected one fenced block with 'sort -u', found {len(found)}"
        )
    return found[0]


def _carried(text: str, names: tuple[str, ...]) -> list[str]:
    """The names `text` still carries, a line break anywhere in it folded away."""
    folded = _fold(text)
    return [name for name in names if name in folded]


# --- the change ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", list(_BANS), ids=[path.name for path in _BANS])
def test_no_name_one_project_supplies_is_left_in_the_file(path: Path) -> None:
    found = _carried(_read(path), _BANS[path])
    assert not found, f"{path.name} still names {found}"


def test_the_correlation_grep_names_its_field_by_placeholder() -> None:
    block = _correlation_block(_read(_SKILL), "analyze-logs SKILL.md")
    named = _carried(block, (_JOB_ID, _SESSION_ID))
    assert not named, f"the correlation grep still names {named}"
    assert _PLACEHOLDER_GREP.search(_fold(block)), (
        "the correlation grep does not name its field by a <placeholder>: "
        + _fold(block)
    )


@pytest.mark.parametrize(
    ("path", "heading", "words"),
    _SOURCES,
    ids=[f"{path.name}:{heading}" for path, heading, _ in _SOURCES],
)
def test_the_new_text_says_where_each_name_comes_from(
    path: Path, heading: str, words: str
) -> None:
    section = _fold(_section(_read(path), heading, path.name))
    assert words in section, f"{path.name}, {heading!r} does not carry {words!r}"


@pytest.mark.parametrize(
    ("path", "heading", "words"),
    [row[:3] for row in _CLAUSES],
    ids=[row[3] for row in _CLAUSES],
)
def test_the_new_text_agrees_with_the_text_around_it(
    path: Path, heading: str, words: str
) -> None:
    section = _fold(_section(_read(path), heading, path.name))
    assert words in section, f"{path.name}, {heading!r} does not carry {words!r}"


# --- the instruments ----------------------------------------------------------------------


def test_the_scan_surface_is_stated_in_numbers() -> None:
    assert len(_BANS) == 2, f"{len(_BANS)} files are scanned, not the 2 stated"
    assert sum(len(names) for names in _BANS.values()) == 3, "not the 3 bans stated"
    assert len(_SOURCES) == 3, f"{len(_SOURCES)} source places, not the 3 stated"
    assert len(_CLAUSES) == 4, f"{len(_CLAUSES)} clauses, not the 4 stated"
    assert _QUERY_TEMPLATES.is_file(), "the reference the bans skip is gone"
    assert _QUERY_TEMPLATES not in _BANS, "the reference is inside the scan"
    assert {path for path, _, _ in _SOURCES} <= set(_BANS), (
        "a source is outside the scan"
    )
    assert {path for path, _, _, _ in _CLAUSES} <= set(_BANS), (
        "a clause is outside the scan"
    )
    for path in _BANS:
        assert path.is_file(), f"{path} is not a file"
    assert len(_read(_SKILL).split("\n")) > 300, (
        "SKILL.md is shorter than any real version"
    )
    assert len(_read(_TEMPLATE).split("\n")) > 40, (
        "the template is shorter than any real one"
    )


def test_the_bans_flag_the_old_shapes_and_pass_the_near_misses() -> None:
    ban = (_NEW_WORK_PREFIX, _JOB_ID)
    old_bullet = f"- `FEATURE-` {_EM} missing functionality that caused the error"
    old_row = "| `FEATURE-` | Missing functionality that caused the error | No retry |"
    old_grep = """grep -E '"(job_id|session_id)"' | sort -u"""
    assert _carried(old_bullet, ban) == [_NEW_WORK_PREFIX]
    assert _carried(old_row, ban) == [_NEW_WORK_PREFIX]
    assert _carried(old_grep, ban) == [_JOB_ID]
    assert _carried("tasks/FEATURE-*.md, and `FEATURE-`\n  again", ban) == [
        _NEW_WORK_PREFIX
    ]
    for near_miss in (
        "grouping on `trace` ID or `session_id` / feature-scoped ID fields",
        "the job-execution wrapper plus the feature-level handler",
        "a FEATURE request, and one job failure",
        "File it only where the project says to.",
    ):
        assert _carried(near_miss, ban) == [], near_miss


def test_the_grep_reader_flags_the_old_command_and_passes_the_new_one() -> None:
    old_doc = "\n".join(
        [
            "6. **Never quote a raw `grep -c`.**",
            "",
            "   ```bash",
            """   grep -B4 -A12 "<error string>" <file> | grep -E '"(job_id|session_id)"' | sort -u""",
            "   ```",
            "",
            "   Then `session_id` is named in the prose, outside the block.",
        ]
    )
    old = _correlation_block(old_doc, "planted old")
    assert _carried(old, (_JOB_ID, _SESSION_ID)) == [_JOB_ID, _SESSION_ID]
    assert _PLACEHOLDER_GREP.search(_fold(old)) is None
    new = _correlation_block(
        old_doc.replace("(job_id|session_id)", "(<id field>)"), "planted new"
    )
    assert _carried(new, (_JOB_ID, _SESSION_ID)) == []
    assert _PLACEHOLDER_GREP.search(_fold(new)) is not None
    mixed = old_doc.replace("(job_id|session_id)", "(<id field>|session_id)")
    assert (
        _PLACEHOLDER_GREP.search(_fold(_correlation_block(mixed, "planted mixed")))
        is None
    )
    assert _carried(_correlation_block(mixed, "planted mixed"), (_SESSION_ID,)) == [
        _SESSION_ID
    ]
    with pytest.raises(AssertionError, match="found 0"):
        _correlation_block("```bash\nls\n```\n", "planted none")
    with pytest.raises(AssertionError, match="found 2"):
        _correlation_block(f"{old_doc}\n\n{old_doc}", "planted two")


def test_the_section_reader_sees_planted_text_and_fails_loudly() -> None:
    old = "\n".join(
        [
            "### Step 5: Create Task Files",
            "",
            "**Prefix rules** (from project conventions):",
            f"- `FEATURE-` {_EM} missing functionality that caused the error",
            "",
            "```bash",
            "# a comment line inside a fenced block is not a heading",
            "grep -c x file",
            "```",
            "",
            "- text after the fenced block, still inside Step 5",
            "",
            "### Step 6: Ask About Unknowns",
            "- the project's own task conventions define them; its AGENTS.md names them",
        ]
    )
    step = _section(old, "### Step 5", "planted")
    assert "FEATURE-" in step and "Step 6" not in step
    # A `#` line inside a fenced block is the comment of the code it holds: the section runs past
    # it to the text after the fence, and a heading wanted by that comment's words is not found.
    assert "text after the fenced block" in step
    with pytest.raises(AssertionError, match="no heading"):
        _section(old, "# a comment line", "planted")
    assert (
        "the project's own task conventions define them; its AGENTS.md names them"
        not in _fold(step)
    )
    with pytest.raises(AssertionError, match="no heading"):
        _section(old, "### Step 9", "planted")
    new = old.replace(
        "(from project conventions):",
        "(the project's own task conventions\n   define them; its AGENTS.md\n   names them):",
    )
    assert (
        "the project's own task conventions define them; its AGENTS.md names them"
        in _fold(_section(new, "### Step 5", "planted"))
    )
