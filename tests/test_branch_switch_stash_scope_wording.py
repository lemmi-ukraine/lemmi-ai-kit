"""branch-switch counts the untracked files first, and past a handful stashes tracked changes only.

Step 2 used to run `git stash push ... --include-untracked` every time. On a tree with hundreds of
untracked files that takes files out of the tree that may not be this session's, and git documents
`--include-untracked` as stashing them and then cleaning them up. Step 2 now counts the untracked
files before it picks the command (files, not `git status --short` lines: a new directory is one
line there), keeps `--include-untracked` for a handful of them or fewer, and past a handful stashes
the tracked changes only and says the untracked files stay. The handful is 5, a chosen default and
not a measured one, and the text says so.

The rule has to hold wherever the skill says what that stash takes: the backup paragraph under the
model-initiated switches, the note the backup script prints on every run (and the docstring that
describes it), and the final status report, which needs a word for a tree whose tracked changes are
stashed and whose untracked files stay. The count is taken over the whole repository, so it reads the
same from a subdirectory; two behaviour tests run the count command, the shipped one and the old one
as the planted positive that shows the probe can see an undercount. No test here runs `git stash`.

THE SURFACE, in numbers the tests assert: 2 files (the skill and its backup script); 3 skill
sections (Step 2, the model-initiated switches section and Step 5, each cut by its heading, a
missing or doubled heading fails loudly); 2 script sites (the docstring paragraph and the printed
note, both read from the syntax tree, where adjacent string literals are one sentence); 9 claims
over 12 phrases in Step 2 and 4 sites over 7 phrases elsewhere. A claim holds when every one of its
phrases is at its site (lower-cased, whitespace collapsed, bold marks dropped). Each phrase is fired
at a planted removal. The old Step 2 and the old notes (kept below as fixtures) are the planted
positives: they must be flagged, the real text must not be, and the same sentences placed at some
other site must not rescue them.
"""

import ast
import shlex
import subprocess
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "branch-switch"
    / "SKILL.md"
)
_SCRIPT = _SKILL.parent / "scripts" / "pre_switch_backup.py"
_STEP_2 = "### Step 2"
_STEP_5 = "### Step 5"
_MODEL_INITIATED = "## Model-initiated switches"
_FENCE = "```"
_DASH = chr(0x2014)
_STASH_COMMAND = "git stash push -m"
_OLD_COUNT_COMMAND = "git ls-files --others --exclude-standard"
_COUNT_COMMAND = f"{_OLD_COUNT_COMMAND} -- :/"
_FLAG = "--include-untracked"
_NOT_SAVED = "NOT saved"
_TAKES = "for a handful of files or fewer"
_STAYS = "past that they stay in the tree"

# (claim, the phrases that must all be present in Step 2)
_CLAIMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "the untracked files are counted, by command, before the stash command is chosen",
        ("count the untracked ones", f"{_COUNT_COMMAND} | wc -l"),
    ),
    (
        "the count covers the whole repository, whatever directory the command runs in",
        ("the whole repository, not only the current directory",),
    ),
    (
        "the count is of files, not of status lines",
        ("a new directory is one line there",),
    ),
    (
        "the handful is a chosen default, not a measured one",
        ("a chosen default, not a measured one",),
    ),
    (
        "past a handful only the tracked changes are stashed",
        (
            "past a handful, stash the tracked changes only",
            f"the same command without `{_FLAG}`",
        ),
    ),
    (
        "the user is told the untracked files stay in the tree",
        ("tell the user the untracked files stay in the tree",),
    ),
    (
        "leaving them in place loses nothing, because a checkout refuses to overwrite one",
        ("refuses rather than overwrite one", "leaving them in place loses nothing"),
    ),
    (
        "with no tracked change there is nothing to stash",
        ("with no tracked change there is nothing to stash",),
    ),
    (
        "after a tracked-only stash the untracked files still show in the status",
        ("the untracked files still show as `??`",),
    ),
)

# (site, the phrases that must all be present there): the other places that say what Step 2's
# stash takes, or what is left once it has run
_ELSEWHERE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("backup paragraph", (_TAKES, _STAYS)),
    ("final status", ("untracked files left in place",)),
    ("script docstring", (_TAKES, _STAYS)),
    ("script note", (_TAKES, _STAYS)),
)
_EVERY_ELSEWHERE_PHRASE = " ".join(
    phrase for _, phrases in _ELSEWHERE for phrase in phrases
)


def _old_step_2(count: bool) -> str:
    """Step 2 as it stood before the count (`count` False), or counting and still stashing
    everything (`count` True)."""
    show = (
        ["1. **Show what will be stashed** and **count the untracked ones**:"]
        + ["   ```bash", f"   {_COUNT_COMMAND} | wc -l", "   ```"]
        if count
        else [
            f"1. **Show what will be stashed** {_DASH} list modified and untracked files"
        ]
    )
    return "\n".join(
        [
            f"### Step 2 {_DASH} Stash Changes",
            "",
            "Unless `--no-stash` was specified:",
            "",
            *show,
            "2. **Create the stash** with a descriptive message:",
            "   ```bash",
            f'   {_STASH_COMMAND} "WIP on {{current-branch}}: {{brief description}}" {_FLAG}',
            "   ```",
            "3. **Verify the stash was created**:",
            "   ```bash",
            "   git stash list | head -1",
            "   ```",
            "",
        ]
    )


# Step 2 as it stood before the count: the planted positive of the old-shape check.
_OLD_STEP_2 = _old_step_2(count=False)
# A Step 2 that counts and then stashes everything anyway: the count is there, the rule that uses
# it is not.
_COUNTS_BUT_NEVER_BRANCHES = _old_step_2(count=True)


def _old_skill(extra: str = "") -> str:
    """The skill's backup paragraph and final status as they stood. `extra` goes above both, under
    no heading the checks read."""
    return "\n".join(
        [
            extra,
            "",
            f"## Model-initiated switches {_DASH} the extra gate",
            "",
            "It saves the tracked and staged diffs, the untracked file names, the stash list and HEAD,",
            "and says what it does not: untracked file contents (Step 2's stash takes those, with",
            f"`{_FLAG}`) and ignored files.",
            "",
            "## Pipeline",
            "",
            f"### Step 5 {_DASH} Confirm Final State",
            "",
            _FENCE,
            "Branch: {new branch name}",
            "Status: {clean / N modified files}",
            _FENCE,
            "",
            "## Decision Tree",
            "",
        ]
    )


def _old_script(extra: str = "") -> str:
    """The backup script's two notes as they stood. `extra` goes into a first docstring paragraph and
    into a print call of its own: not at the sites the checks read."""
    return "\n".join(
        [
            f'"""Backs the tree up. {extra}',
            "",
            "NOT saved, and the script says so on every run: the CONTENTS of untracked files (the",
            f"inventory holds names only; the stash a switch takes with `git stash push {_FLAG}` is",
            "what keeps them) and ignored files.",
            '"""',
            f'print("{extra}")',
            "print(",
            '    "NOT saved: the CONTENTS of untracked files (the stash taken with "',
            f'    "`git stash push {_FLAG}` keeps them) and ignored files."',
            ")",
            "",
        ]
    )


def _outside_fences(lines: list[str]) -> list[tuple[int, str]]:
    """(index, line) for every line that is neither a fence line nor inside a fenced block."""
    kept: list[tuple[int, str]] = []
    fenced = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith(_FENCE):
            fenced = not fenced
        elif not fenced:
            kept.append((index, line))
    return kept


def _level(line: str) -> int:
    hashes = len(line) - len(line.lstrip("#"))
    return hashes if hashes and line[hashes : hashes + 1] == " " else 0


def _section(text: str, prefix: str) -> str:
    """The lines from the one heading that starts with `prefix` to the next heading of its level
    or a higher one. A `#` line inside a fence is not a heading."""
    lines = text.splitlines()
    starts = [i for i, line in _outside_fences(lines) if line.startswith(prefix)]
    assert len(starts) == 1, f"{len(starts)} headings start with {prefix!r}, expected 1"
    start = starts[0]
    level = _level(lines[start])
    end = next(
        (
            i
            for i, line in _outside_fences(lines)
            if i > start and 0 < _level(line) <= level
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def _fold(text: str) -> str:
    return " ".join(text.replace("**", "").split()).lower()


def _missing(folded: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in folded]


def _old_shape(folded_section: str) -> bool:
    """The flag is run unconditionally: it is there, and no handful rule is."""
    return _FLAG in folded_section and "handful" not in folded_section


def _skill_text() -> str:
    return _SKILL.read_text(encoding="utf-8")


def _script_text() -> str:
    return _SCRIPT.read_text(encoding="utf-8")


def _step_2() -> str:
    return _fold(_section(_skill_text(), _STEP_2))


def _docstring_note(source: str) -> str:
    """The module docstring's one paragraph that says what the backup does not save."""
    paragraphs = (ast.get_docstring(ast.parse(source)) or "").split("\n\n")
    notes = [text for text in paragraphs if text.startswith(_NOT_SAVED)]
    assert len(notes) == 1, (
        f"{len(notes)} docstring paragraphs start with {_NOT_SAVED!r}, expected 1"
    )
    return _fold(notes[0])


def _printed_strings(source: str) -> list[str]:
    """The text of every `print(...)` call whose first argument is a string literal. Adjacent
    literals are one constant, so the wrapped source lines read as one sentence."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
            and node.args
        ):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.append(first.value)
    return found


def _printed_note(source: str) -> str:
    notes = [text for text in _printed_strings(source) if text.startswith(_NOT_SAVED)]
    assert len(notes) == 1, (
        f"{len(notes)} printed lines start with {_NOT_SAVED!r}, expected 1"
    )
    return _fold(notes[0])


def _site_text(site: str, skill: str, script: str) -> str:
    if site == "backup paragraph":
        return _fold(_section(skill, _MODEL_INITIATED))
    if site == "final status":
        return _fold(_section(skill, _STEP_5))
    if site == "script docstring":
        return _docstring_note(script)
    if site == "script note":
        return _printed_note(script)
    raise AssertionError(f"unknown site {site!r}")


def _git(where: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(where), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=True,
    )


def _tree_with_untracked(tmp_path: Path) -> tuple[Path, Path]:
    """A repository with six untracked files: two at the root, two in a subdirectory, two in a new
    directory two levels down (one line in `git status --short`). Returns the root and the
    subdirectory."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for name in (
        "a.txt",
        "b.txt",
        "sub/c.txt",
        "sub/d.txt",
        "other/deep/e.txt",
        "other/deep/f.txt",
    ):
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    return repo, repo / "sub"


def _count_arguments() -> list[str]:
    """The words of the count command in Step 2: the first line inside its first fenced block,
    without the pipe to `wc -l`."""
    fenced = False
    for line in _section(_skill_text(), _STEP_2).splitlines():
        if line.lstrip().startswith(_FENCE):
            if fenced:
                break
            fenced = True
        elif fenced and line.strip():
            return shlex.split(line.strip().split(" | ")[0])
    raise AssertionError("Step 2 has no fenced command")


def _files_counted(where: Path, arguments: list[str]) -> int:
    """How many names the count command prints when it runs in `where`: what `| wc -l` counts."""
    done = _git(where, *arguments[1:])
    return len([line for line in done.stdout.splitlines() if line.strip()])


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _CLAIMS for phrase in claim_phrases]
    assert (len(_CLAIMS), len(phrases)) == (9, 12)
    elsewhere = [phrase for _, site_phrases in _ELSEWHERE for phrase in site_phrases]
    assert (len(_ELSEWHERE), len(elsewhere)) == (4, 7)
    assert _SKILL.is_file(), "the skill is not where the test looks"
    assert _SCRIPT.is_file(), "the backup script is not where the test looks"
    assert len(_step_2()) > 0, "Step 2 is empty"
    for site, _ in _ELSEWHERE:
        text = _site_text(site, _skill_text(), _script_text())
        assert len(text) > 0, f"{site} is empty"


@pytest.mark.parametrize(
    ("claim", "phrases"), _CLAIMS, ids=[claim for claim, _ in _CLAIMS]
)
def test_step_2_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_step_2(), phrases)
    assert not missing, f"{claim}: not stated in Step 2, missing {missing}"


@pytest.mark.parametrize(
    ("site", "phrases"), _ELSEWHERE, ids=[site for site, _ in _ELSEWHERE]
)
def test_the_other_sites_state_the_claim(site: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_site_text(site, _skill_text(), _script_text()), phrases)
    assert not missing, f"{site}: not stated there, missing {missing}"


def test_the_count_comes_before_the_stash_command() -> None:
    step = _step_2()
    assert _COUNT_COMMAND in step and _STASH_COMMAND in step
    assert step.index(_COUNT_COMMAND) < step.index(_STASH_COMMAND), (
        "Step 2 picks the stash command before it counts the untracked files"
    )


def test_the_first_stash_command_keeps_the_flag_for_the_small_case() -> None:
    lines = _section(_skill_text(), _STEP_2).splitlines()
    printed = [line for line in lines if line.strip().startswith(_STASH_COMMAND)]
    outside = [line for _, line in _outside_fences(lines) if _STASH_COMMAND in line]
    assert outside == [], "a stash command is printed outside a fenced block"
    assert printed, "Step 2 prints no stash command"
    assert _FLAG in printed[0], "the first stash command lost the flag a handful needs"


def test_the_count_reads_the_same_from_a_subdirectory(tmp_path: Path) -> None:
    """The command Step 2 prints, run as printed, counts every untracked file of the repository
    from the root and from a subdirectory."""
    repo, sub = _tree_with_untracked(tmp_path)
    arguments = _count_arguments()
    assert arguments[:2] == ["git", "ls-files"], arguments
    assert _files_counted(repo, arguments) == 6
    assert _files_counted(sub, arguments) == 6, (
        "the count depends on the directory it runs in"
    )


def test_the_old_count_command_misses_the_rest_of_the_tree_from_a_subdirectory(
    tmp_path: Path,
) -> None:
    """Planted positive: the command Step 2 printed before the pathspec counts only the directory
    it runs in, so the equal pair in the test above is a measurement and not a blind probe."""
    repo, sub = _tree_with_untracked(tmp_path)
    old = shlex.split(_OLD_COUNT_COMMAND)
    assert _files_counted(repo, old) == 6
    assert _files_counted(sub, old) == 2


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real section is the one gap reported, and an
    empty section lacks every phrase of a claim."""
    step = _step_2()
    for claim, phrases in _CLAIMS:
        assert not _missing(step, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(step.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_every_phrase_at_the_other_sites_is_reported_when_it_goes() -> None:
    """Planted removal at the other sites: each phrase cut out is the one gap reported there."""
    skill, script = _skill_text(), _script_text()
    for site, phrases in _ELSEWHERE:
        text = _site_text(site, skill, script)
        assert not _missing(text, phrases), f"{site} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                site,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), site


def test_the_old_step_2_is_flagged_and_the_real_one_is_not() -> None:
    old = _fold(_section(_OLD_STEP_2, _STEP_2))
    assert _old_shape(old), "the planted old Step 2 is not seen: the check is blind"
    assert not _old_shape(_step_2()), "Step 2 still runs the flag unconditionally"
    for claim, phrases in _CLAIMS:
        assert _missing(old, phrases) == list(phrases), (
            f"the old Step 2 already states {claim!r}"
        )


def test_a_step_2_that_counts_and_still_stashes_everything_is_flagged() -> None:
    """Planted positive: a count nothing uses is not the new shape. The flag still runs for every
    tree, so the helper flags it although the count command is there."""
    section = _fold(_section(_COUNTS_BUT_NEVER_BRANCHES, _STEP_2))
    assert _COUNT_COMMAND in section, "the fixture lost its count"
    assert _old_shape(section), "a count that is never used passes as the new shape"
    assert "past a handful" not in section, (
        "the fixture holds the rule it is meant to lack"
    )


def test_the_old_text_is_flagged_at_every_other_site() -> None:
    """Planted positive: the sentences as they stood lack every phrase, the real ones hold them."""
    skill, script = _skill_text(), _script_text()
    for site, phrases in _ELSEWHERE:
        assert _missing(_site_text(site, skill, script), phrases) == [], (
            f"{site} does not hold"
        )
        old = _site_text(site, _old_skill(), _old_script())
        assert _missing(old, phrases) == list(phrases), (
            f"the old {site} already states the claim"
        )


def test_sentences_under_the_next_step_do_not_count() -> None:
    """Near-miss: the old Step 2 followed by the real sentences under Step 3 is still the old
    shape, because the claims are read from Step 2 alone."""
    real = _section(_skill_text(), _STEP_2)
    body = real.split("\n", 1)[1]  # the real Step 2 without its heading
    moved = f"{_OLD_STEP_2}\n### Step 3 {_DASH} Switch Branch\n\n{body}\n"
    section = _fold(_section(moved, _STEP_2))
    assert _old_shape(section)
    for claim, phrases in _CLAIMS:
        assert _missing(section, phrases) == list(phrases), claim


def test_a_qualifier_placed_at_another_site_does_not_rescue_a_site() -> None:
    """Near-miss: every phrase of every site, placed above the skill's headings, in a first docstring
    paragraph and in a print call of its own, leaves each site as the old text had it."""
    skill = _old_skill(extra=_EVERY_ELSEWHERE_PHRASE)
    script = _old_script(extra=_EVERY_ELSEWHERE_PHRASE)
    for site, phrases in _ELSEWHERE:
        assert _missing(_site_text(site, skill, script), phrases) == list(phrases), site
