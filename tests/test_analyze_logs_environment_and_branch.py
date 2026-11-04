"""`analyze-logs` asks which branch an incident took, and names the environment in every query.

Two process rules, with nothing to measure beyond the text. A fix was named for an incident without
asking which branch of the mechanism the incident ran through, so a change to a branch that never
ran could be proposed as the fix and the observed failure would stay as it was. And the query
method did not say that two deployments can share a service name and a region: a filter or a
command that names the service alone reads whichever environment the tool points at, and the
query templates named the project filter once, as an option for comparing environments, with 11 of
their service blocks carrying no project at all. The flag spelling the reference now uses was read
from the platform tool's own help output; no query was run.

What the text says now: Step 3f opens with the branch check and Step 4b's fix-correctness item asks
it again; the querying method has a fifth step that names the environment in every query and runs it
once per environment, platform-neutral; and the query reference puts the project in every service
block, passes the project flag on each platform command, and keeps one copy of a block it had twice.

THE SURFACE, in numbers the tests assert: 2 files are read (the skill and the query reference), 5
places are read in them (four stretches of text and the set of service blocks), 19 phrases are
asserted in all, 11 service blocks are counted, and 3 stretches of the skill are checked to name no
platform. Each cutter and each check is fired at the pre-edit text, at a near miss (the phrases in a
neighbouring item, a project line in prose and not in a block) and at planted text with the new
shape, so a silence on the real files is a silence about the files. The section reader is also
fired at a `#` line inside a fenced block, which is a comment and never a heading.
"""

import re
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO / "plugins" / "core" / "skills" / "analyze-logs"
_SKILL = _SKILL_DIR / "SKILL.md"
_QUERIES = _SKILL_DIR / "references" / "gcp-query-templates.md"

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_ITEM = re.compile(r"^(\d+)\. ")

_PROPOSE = "#### 3f."
_CHALLENGE = "### Step 4b"
_METHOD = "## Querying the Log Platform Directly"
_BASE = "## Base Filters"

_SERVICE_LINE = 'resource.labels.service_name="{SERVICE_NAME}"'
_PROJECT_LINE = 'resource.labels.project_id="{PROJECT_ID}"'

_EM = chr(0x2014)

Cut = Callable[[str], str]


def _whole(section: str) -> str:
    return section


def _first_bullet(section: str) -> str:
    """The first top-level bullet of a section, with its indented continuation lines."""
    found: list[str] = []
    for line in section.split("\n"):
        if not found:
            if line.startswith("- "):
                found.append(line)
        elif line.startswith("  "):
            found.append(line)
        else:
            break
    if not found:
        raise AssertionError("no bullet in the section")
    return "\n".join(found)


def _item(section: str, number: int) -> str:
    """Numbered item `number` of a section, with its indented continuation lines."""
    found: list[str] = []
    for line in section.split("\n"):
        match = _ITEM.match(line)
        if not found:
            if match is not None and int(match.group(1)) == number:
                found.append(line)
        elif line.startswith("   "):
            found.append(line)
        else:
            break
    if not found:
        raise AssertionError(f"no numbered item {number} in the section")
    return "\n".join(found)


# What each place says: the label the test id carries, the file, the heading whose section holds
# the words, the cut of that section the words must sit in, and the phrases that must all be there
# once whitespace is folded.
_PLACES: tuple[tuple[str, Path, str, Cut, tuple[str, ...]], ...] = (
    (
        "propose",
        _SKILL,
        _PROPOSE,
        _first_bullet,
        (
            "Before calling a change the fix for this incident, trace which branch of the"
            " mechanism the incident took",
            "which outcome of each decision, which terminal state, which threshold was crossed",
            "confirm that the fix acts on that branch",
            "A fix for a branch that did not run leaves the observed failure as it was",
            "record a class-level fix as a separate item",
        ),
    ),
    (
        "challenge",
        _SKILL,
        _CHALLENGE,
        partial(_item, number=2),
        ("Does it act on the branch the incident took (Step 3f)?",),
    ),
    (
        "method",
        _SKILL,
        _METHOD,
        partial(_item, number=5),
        (
            "Name the environment in every query, and run it once per environment",
            "Two deployments can share a service name and a region",
            "a filter or command that names the service alone reads whichever environment the"
            " tool points at",
            "Put the project, account or cluster in the filter and in every command that takes"
            " one",
            "label each result with the environment it came from",
            "read the identifiers from the deploy manifests, not from memory",
        ),
    ),
    (
        "base-filters",
        _QUERIES,
        _BASE,
        _whole,
        (
            "All queries should start with the service and project filters:",
            "Put `resource.labels.project_id` in every filter, not only when comparing"
            " environments",
            "`--project {PROJECT_ID}` on every `gcloud logging read` and every"
            " `gcloud run services describe`",
            "Run each query once per project",
            "label each result with the environment it came from",
            "take the project ids from the deploy manifests, not from memory",
            "**Measured: `location` does not distinguish environments**",
        ),
    ),
)

# Words the new SKILL.md text must not carry: it is platform-neutral, and the platform's own words
# live in the reference.
_PLATFORM_WORDS = (
    "gcloud",
    "GCP",
    "Cloud Run",
    "resource.labels",
    "project_id",
    "job_id",
)

# The text of the four stretches before the change, as `git show` printed it at the start commit.
_OLD_PROPOSE = """\
#### 3f. Propose Solution
- Describe the fix conceptually (what needs to change, not the code diff).
- Reference the specific file(s) and function(s) that need modification.
- If multiple approaches exist, list pros/cons briefly.
- Flag if the fix requires a migration, config change, or external service update.

### Step 4: Compile Findings Report
"""

_OLD_CHALLENGE = """\
### Step 4b: Challenge Review (Mandatory)

For each reported issue, challenge:

1. **Evidence grounding**: Is the root cause verified against current code, or assumed from stack traces alone?
   Files may have changed since the log was produced.
2. **Fix correctness**: Does the proposed fix contradict any convention in AGENTS.md or `.ai/learnings.md`?
   Cross-check fix patterns against both sources <EM> they can conflict.
3. **Issue grouping**: Are any "separate" issues actually symptoms of the same root cause? Would fixing
   one resolve another?

### Step 5: Create Task Files
""".replace("<EM>", _EM)

_OLD_METHOD = """\
## Querying the Log Platform Directly

When the user needs to search the platform rather than a downloaded file, the method is the same on
every backend:

1. **Start with the narrowest service/resource filter** the platform offers
2. **Add explicit time bounds** <EM> an unbounded scan is slow, and on a hosted platform it is billable
3. **Search the field that matches the target**: the structured payload for application fields, the
   raw-text field for startup output and uncaught exceptions
4. **Validate the query against a downloaded sample first** when one exists, so that a zero-result
   query can be told apart from a wrong-field query

[references/gcp-query-templates.md](references/gcp-query-templates.md) works this through in GCP
Cloud Logging's query dialect <EM> a worked example to translate, not the required backend.
""".replace("<EM>", _EM)

_OLD_BASE = """\
## Base Filters

All queries should start with the service filter:

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
```

To scope to a specific environment, use `resource.labels.project_id`, not
`resource.labels.location`. **Measured: `location` does not distinguish environments** when
deployments share a region <EM> every entry across 11 log exports spanning two environments carried
the same `location`. One project id per environment is the reliable discriminator:

```
resource.labels.configuration_name="{SERVICE_NAME}"
resource.labels.project_id="{PROJECT_ID}"
```

```
resource.labels.configuration_name="{SERVICE_NAME}"
resource.labels.project_id="{PROJECT_ID}"
```

## Common Queries

### Errors Only (Last N Hours)

```
resource.type="cloud_run_revision"
resource.labels.service_name="{SERVICE_NAME}"
severity>=ERROR
timestamp>="{N_HOURS_AGO}"
```
""".replace("<EM>", _EM)

_OLD = {
    "propose": _OLD_PROPOSE,
    "challenge": _OLD_CHALLENGE,
    "method": _OLD_METHOD,
    "base-filters": _OLD_BASE,
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fold(text: str) -> str:
    """The text with every run of whitespace, line breaks included, as one space."""
    return " ".join(text.split())


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _section(text: str, heading: str, where: str) -> str:
    """The text under the first heading line that starts with `heading`.

    It runs to the next heading of the same or a higher level. A `#` line inside a fenced block is
    a comment of the code it holds, not a heading. A missing heading fails with the heading named,
    so a renamed section is a loud failure and never an empty match.
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


def _fenced_blocks(text: str) -> list[list[str]]:
    """The lines inside each fenced block, without its fence lines."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if _is_fence(line):
            if current is not None:
                blocks.append(current)
            current = [] if current is None else None
        elif current is not None:
            current.append(line)
    return blocks


def _cut(text: str, heading: str, cut: Cut, where: str) -> str:
    """The stretch of text under `heading` that `cut` picks out, whitespace folded.

    A heading or a stretch that is not found raises, and the caller names the phrases the whole
    file lacks as well, so a renamed heading and a text that is gone read differently.
    """
    return _fold(cut(_section(text, heading, where)))


def _missing(
    text: str, heading: str, cut: Cut, phrases: tuple[str, ...], where: str
) -> list[str]:
    try:
        stretch = _cut(text, heading, cut, where)
    except AssertionError as error:
        gone = [phrase for phrase in phrases if phrase not in _fold(text)]
        raise AssertionError(
            f"{where}, under {heading!r}: {error}; phrases found nowhere in the file: {gone}"
        ) from error
    return [phrase for phrase in phrases if phrase not in stretch]


def _lines(block: list[str]) -> list[str]:
    return [line.strip() for line in block]


def _service_blocks(text: str) -> list[list[str]]:
    """The fenced blocks that name the service by its label."""
    return [block for block in _fenced_blocks(text) if _SERVICE_LINE in _lines(block)]


def _names_project(block: list[str]) -> bool:
    return _PROJECT_LINE in _lines(block)


# --- the change ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "heading", "cut", "phrases"),
    [row[1:] for row in _PLACES],
    ids=[row[0] for row in _PLACES],
)
def test_the_place_states_its_claim(
    path: Path, heading: str, cut: Cut, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_read(path), heading, cut, phrases, path.name)
    assert not missing, f"{path.name}, {heading!r} does not carry {missing}"


def test_every_service_block_of_the_reference_names_the_project() -> None:
    blocks = _service_blocks(_read(_QUERIES))
    assert len(blocks) == 11, (
        f"{len(blocks)} blocks name the service, not the 11 stated"
    )
    without = [block for block in blocks if not _names_project(block)]
    assert not without, (
        f"{len(blocks) - len(without)} of {len(blocks)} blocks that name the service"
        " also name the project"
    )


def test_the_reference_holds_no_duplicated_block() -> None:
    blocks = ["\n".join(block) for block in _fenced_blocks(_read(_QUERIES))]
    copies = len(blocks) - len(set(blocks))
    assert copies == 0, (
        f"{copies} fenced block(s) of the reference repeat another block"
    )


@pytest.mark.parametrize(
    ("heading", "cut", "phrases"),
    [row[2:] for row in _PLACES if row[1] == _SKILL],
    ids=[row[0] for row in _PLACES if row[1] == _SKILL],
)
def test_the_new_skill_text_names_no_platform(
    heading: str, cut: Cut, phrases: tuple[str, ...]
) -> None:
    stretch = _cut(_read(_SKILL), heading, cut, _SKILL.name)
    assert phrases[0] in stretch, f"{heading!r} has no new text to check"
    named = [word for word in _PLATFORM_WORDS if word in stretch]
    assert not named, f"{heading!r} names the platform: {named}"


# --- the instruments ----------------------------------------------------------------------

_PLANTED = "\n".join(
    [
        "## Before",
        "",
        "text before",
        "",
        "#### 3f. Planted",
        "- the first bullet",
        "  runs over a line break",
        "- the second bullet",
        "",
        "```bash",
        "# a comment line inside a fenced block is not a heading",
        "```",
        "",
        "1. **One** the first item",
        "   continues here",
        "2. **Two** the second item",
        "",
        "### After",
        "",
        "after",
    ]
)


def test_the_cutters_see_planted_text_and_fail_loudly() -> None:
    section = _section(_PLANTED, "#### 3f.", "planted")
    assert "the second bullet" in section and "text before" not in section
    assert "after" not in section
    assert "# a comment line inside" in section
    assert _fold(_first_bullet(section)) == "- the first bullet runs over a line break"
    assert _fold(_item(section, 1)) == "1. **One** the first item continues here"
    assert _fold(_item(section, 2)) == "2. **Two** the second item"
    with pytest.raises(AssertionError, match="no numbered item 3"):
        _item(section, 3)
    with pytest.raises(AssertionError, match="no bullet"):
        _first_bullet("1. **One** a numbered item\n")
    with pytest.raises(AssertionError, match="no heading"):
        _section(_PLANTED, "# a comment line", "planted")
    with pytest.raises(AssertionError, match="no heading"):
        _section(_PLANTED, "### Nothing like this", "planted")


def test_the_phrase_check_flags_the_pre_edit_text() -> None:
    for label, _path, heading, cut, phrases in _PLACES:
        old = _OLD[label]
        if label == "method":
            with pytest.raises(
                AssertionError, match="no numbered item 5.*found nowhere"
            ):
                _missing(old, heading, cut, phrases, label)
        else:
            lacking = _missing(old, heading, cut, phrases, label)
            assert set(lacking) <= set(phrases)
            assert lacking, f"{label}: the pre-edit text already carries every phrase"
    kept = "**Measured: `location` does not distinguish environments**"
    assert _missing(_OLD_BASE, _BASE, _whole, (kept,), "old") == []
    assert _missing(
        _OLD_CHALLENGE, _CHALLENGE, partial(_item, number=2), (kept,), "old"
    ) == [kept]


def test_phrases_in_the_wrong_place_do_not_satisfy_the_check() -> None:
    for label, _path, heading, cut, phrases in _PLACES:
        said = " ".join(phrases)
        if label == "propose":
            near_miss = f"{heading} Planted\n- a first bullet\n- {said}\n"
        elif label == "challenge":
            near_miss = f"{heading}\n\n1. **One** x\n2. **Two** y\n3. **Three** {said}\n\n### Next\n"
        elif label == "method":
            near_miss = f"{heading}\n\n4. **Four** {said}\n5. **Five** nothing here\n"
        else:
            near_miss = f"{heading}\n\ntext\n\n## Elsewhere\n\n{said}\n"
        assert _missing(near_miss, heading, cut, phrases, label) == list(phrases), label
        with pytest.raises(AssertionError, match="no heading"):
            _missing(f"## Elsewhere\n\n{said}\n", heading, cut, phrases, label)


def test_the_phrase_check_passes_planted_text_with_the_new_shape() -> None:
    for label, _path, heading, cut, phrases in _PLACES:
        wrapped = "\n".join(f"   {word}" for word in " ".join(phrases).split(" "))
        if label == "propose":
            planted = f"{heading} Planted\n- {wrapped.strip()}\n- another bullet\n"
        elif label == "challenge":
            planted = (
                f"{heading}\n\n1. **One** x\n2. **Two** y\n{wrapped}\n3. **Three** z\n"
            )
        elif label == "method":
            planted = (
                f"{heading}\n\n4. **Four** x\n5. **Five** {wrapped.strip()}\n\nlink\n"
            )
        else:
            planted = f"{heading}\n\n{wrapped}\n\n## Next\n"
        assert _missing(planted, heading, cut, phrases, label) == [], label


_PLANTED_BLOCKS = "\n".join(
    [
        "```",
        'resource.type="cloud_run_revision"',
        _SERVICE_LINE,
        "```",
        "",
        _PROJECT_LINE,
        "",
        "```",
        _SERVICE_LINE,
        _PROJECT_LINE,
        "```",
        "",
        "```",
        'resource.labels.configuration_name="{SERVICE_NAME}"',
        "```",
        "",
        "```",
        _SERVICE_LINE,
        'resource.labels.project_idx="{PROJECT_ID}"',
        "```",
    ]
)


def test_the_block_guard_flags_planted_blocks_without_the_project_line() -> None:
    blocks = _service_blocks(_PLANTED_BLOCKS)
    assert len(blocks) == 3, (
        "the configuration-name block must not count as a service block"
    )
    assert [_names_project(block) for block in blocks] == [False, True, False]
    old = _service_blocks(_OLD_BASE)
    assert len(old) == 2 and not any(_names_project(block) for block in old)
    pre_edit = ["\n".join(block) for block in _fenced_blocks(_OLD_BASE)]
    assert len(pre_edit) - len(set(pre_edit)) == 1, (
        "the pre-edit duplicate pair is not seen"
    )
    clean = ["\n".join(block) for block in _fenced_blocks(_PLANTED_BLOCKS)]
    assert len(clean) - len(set(clean)) == 0


def test_the_platform_check_flags_planted_platform_words() -> None:
    clean = _fold(
        _item("5. **Name it** Put the project, account or cluster in the filter.", 5)
    )
    assert [word for word in _PLATFORM_WORDS if word in clean] == []
    dirty = "5. **Name it** Put resource.labels.project_id on every gcloud call, as GCP wants."
    flagged = [word for word in _PLATFORM_WORDS if word in _fold(_item(dirty, 5))]
    assert flagged == ["gcloud", "GCP", "resource.labels", "project_id"]


def test_the_scan_surface_is_stated_in_numbers() -> None:
    assert len({path for _, path, _, _, _ in _PLACES}) == 2, "not the 2 files stated"
    assert len(_PLACES) + 1 == 5, (
        f"{len(_PLACES)} text places and 1 block place, not the 5 stated"
    )
    assert sum(len(row[4]) for row in _PLACES) == 19, "not the 19 phrases stated"
    assert len([row for row in _PLACES if row[1] == _SKILL]) == 3, (
        "not the 3 platform checks"
    )
    assert set(_OLD) == {row[0] for row in _PLACES}, "an excerpt has no place"
    for path in (_SKILL, _QUERIES):
        assert path.is_file(), f"{path} is not a file"
    assert len(_read(_SKILL).split("\n")) > 300, (
        "SKILL.md is shorter than any real version"
    )
    assert len(_read(_QUERIES).split("\n")) > 150, (
        "the reference is shorter than any real one"
    )
    assert len(_service_blocks(_read(_QUERIES))) == 11, (
        "not the 11 service blocks stated"
    )
