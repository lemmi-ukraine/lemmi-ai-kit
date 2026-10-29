"""The session-retrospective skill cannot contradict itself about where its report lives.

Phase 6 told the reader to `git add` the report because `.ai/retrospectives/` is "NOT
gitignored", and the paragraph right after it said the folder IS gitignored, that the report
is local scratch, and that nobody should stage it. Both arrived in one commit, so no edit ever
chose between them and the reader got opposite instructions from adjacent paragraphs. Three
more lines still spoke of a committed report. The settled decision is local scratch, never
staged.

The scan reads every text file of the skill, not only `SKILL.md`: the stale claim also lived
in a reference and in an extractor comment, and a scan of one file would have passed.
`test_the_scan_covers_every_file_of_the_skill` states that surface in numbers, and
`test_the_stale_phrase_scan_flags_what_it_is_meant_to_flag` fires the scan at planted
positives before its silence on the real files is trusted.

THE SECOND HALF OF THIS FILE pins three later requests, each against the text it replaced:

* the session folder is derived from the WORKING DIRECTORY (the old text said the extractor
  walked up from its own location), and each printed extractor command is taken out of the
  skill text and run, from a fake project root under a fake home, with no folder given;
* the retrospective's seam: a project that keeps P1/P2 as proposals has them registered in the
  changelog entry instead of applied, and the gate that checks the entry takes
  `--proposals-only`;
* the hypothesis validator runs at the end of the consolidator's Phase 2 as well as in its
  Phase 6.5, which three sentences of two skills left out: they name Phase 6.5 alone.

Each scan of the second half is fired at a planted positive that is the old text.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from test_printed_commands import (
    _load,  # pyright: ignore[reportPrivateUsage]
    _markdown_surface,  # pyright: ignore[reportPrivateUsage]
    _printed_elements,  # pyright: ignore[reportPrivateUsage]
    _read,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "session-retrospective"

# Every suffix a text file of the skill has today. A file with any other suffix fails
# `test_the_scan_covers_every_file_of_the_skill`, so a new kind of file is a decision made
# here rather than a silent gap in what is read.
_TEXT_SUFFIXES: frozenset[str] = frozenset({".md", ".py"})

# The files that held the stale claim. The scan must contain them by name, or it is not
# measuring the thing it is named for.
_FILES_THAT_HELD_THE_CLAIM: tuple[str, ...] = (
    "SKILL.md",
    "references/extractor-output-schema.md",
    "scripts/extract_sessions.py",
)

# Matched against whitespace-collapsed text, so a phrase that wraps across a line is still seen.
_STALE_PHRASES: dict[str, re.Pattern[str]] = {
    "says the report folder is not gitignored": re.compile(
        r"\bnot gitignored\b", re.IGNORECASE
    ),
    "tells the reader to stage the report": re.compile(
        r"`git add` it\b", re.IGNORECASE
    ),
    "speaks of a committed report": re.compile(
        r"(?<![A-Za-z])committed report\b", re.IGNORECASE
    ),
}

# The one claim that must stay: the folder is gitignored. `\s+` spans the line the source wraps.
_GITIGNORED_CLAIM = re.compile(r"`\.ai/retrospectives/`\s+is\s+\*\*gitignored\*\*")


def _skill_files() -> list[Path]:
    return sorted(
        path
        for path in _SKILL_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _relative(path: Path) -> str:
    return path.relative_to(_SKILL_DIR).as_posix()


def _collapsed(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _stale_hits(text: str) -> list[str]:
    """The rule itself, over a string, so it can be exercised on input the skill lacks."""
    flat = _collapsed(text)
    return [name for name, pattern in _STALE_PHRASES.items() if pattern.search(flat)]


def test_the_scan_covers_every_file_of_the_skill() -> None:
    """The scan surface in numbers: every file the skill ships is read, none is skipped."""
    everything = _skill_files()
    unread = [
        _relative(path) for path in everything if path.suffix not in _TEXT_SUFFIXES
    ]
    assert not unread, (
        f"{len(unread)} of {len(everything)} files of the skill have a suffix this test "
        f"does not read: {unread}. Add the suffix to _TEXT_SUFFIXES if the file is text."
    )
    names = {_relative(path) for path in everything}
    missing = [name for name in _FILES_THAT_HELD_THE_CLAIM if name not in names]
    assert not missing, f"the scan of {len(names)} files does not contain {missing}"


def test_no_file_of_the_skill_says_the_report_is_committed_or_not_ignored() -> None:
    offenders = {
        _relative(path): hits
        for path in _skill_files()
        if (hits := _stale_hits(path.read_text(encoding="utf-8")))
    }
    assert not offenders, (
        "the skill contradicts its settled decision (the report folder is gitignored "
        "local scratch that nobody stages):\n"
        + "\n".join(f"  {name}: {', '.join(hits)}" for name, hits in offenders.items())
    )


def test_the_skill_still_says_the_report_folder_is_gitignored() -> None:
    """Positive control: the decision the stale lines contradicted is still stated."""
    text = _collapsed((_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"))
    assert _GITIGNORED_CLAIM.search(text), (
        "SKILL.md no longer says that `.ai/retrospectives/` is **gitignored**; the "
        "absence checks above would then pass for the wrong reason"
    )


def test_the_stale_phrase_scan_flags_what_it_is_meant_to_flag() -> None:
    """Fire the scan at planted positives (including one that wraps a line) and negatives."""
    planted_positives = [
        "`.ai/retrospectives/` is NOT gitignored but has never been committed",
        "The report must survive the session - `git add` it.",
        "the committed report contains only findings",
        "the folder is NOT\ngitignored",
    ]
    for text in planted_positives:
        assert _stale_hits(text), f"the scan missed a planted positive: {text!r}"

    clean = [
        "`.ai/retrospectives/` is **gitignored** and the report is local scratch",
        "do **not** `git add` the report",
        "three reports went uncommitted",
        "an uncommitted report is lost with the session",
    ]
    for text in clean:
        assert _stale_hits(text) == [], f"the scan flagged clean text: {text!r}"


# --- reading a section of a skill ------------------------------------------------------------

_TASK_LEARNINGS_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "task-learnings"
_RETRO = _SKILL_DIR / "SKILL.md"
_SCHEMA = _SKILL_DIR / "references" / "extractor-output-schema.md"
_GATE = _SKILL_DIR / "references" / "report-gate.md"
_EXTRACTOR = _SKILL_DIR / "scripts" / "extract_sessions.py"
_TASK_LEARNINGS = _TASK_LEARNINGS_DIR / "SKILL.md"
_HEADING = re.compile(r"^(#{1,6})\s")


def _section(text: str, heading: str) -> str:
    """The lines from the heading that starts with `heading` to the next heading of the same
    or a higher level. A `#` line inside a fenced block is not a heading."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in re.split(r"\r?\n", text):
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
    assert body, f"no heading starts with {heading!r}"
    return "\n".join(body)


def _prose(section: str) -> str:
    """The section with its fenced blocks removed."""
    kept: list[str] = []
    in_fence = False
    for line in re.split(r"\r?\n", section):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            kept.append(line)
    return "\n".join(kept)


# --- K29: the session folder comes from the working directory --------------------------------

# Each is a sentence the extractor's present behavior no longer supports. Four describe the
# retired derivation, where the extractor walked up from its own location to the repo root and
# the session folder came from there; it now reads the working directory. The fifth quotes the
# digest's old label for the record count ("user msgs"), which is a change of label and has
# nothing to do with the walk: the digest now says "User-channel records". Matched against
# whitespace-collapsed text, so a phrase that wraps a line is still seen.
_K29_STALE: dict[str, re.Pattern[str]] = {
    "says the extractor walks up from its own location": re.compile(
        r"walks\s+up\s+from\s+its\s+own\s+location", re.IGNORECASE
    ),
    "calls the folder the auto-derivation target": re.compile(
        r"auto-derivation\s+target", re.IGNORECASE
    ),
    "says the session dir is auto-derived from the repo root": re.compile(
        r"auto-derived\s+from\s+the\s+repo\s+root", re.IGNORECASE
    ),
    "says the extractor walks up to the dir holding .claude/": re.compile(
        r"walks\s+up\s+to\s+the\s+dir\s+containing", re.IGNORECASE
    ),
    "quotes the digest's old count label (user msgs)": re.compile(
        r"\buser\s+msgs\b", re.IGNORECASE
    ),
}


def _k29_stale_hits(text: str) -> list[str]:
    flat = _collapsed(text)
    return [name for name, pattern in _K29_STALE.items() if pattern.search(flat)]


def _k29_files() -> list[Path]:
    """Markdown of the two skills that talk about the extractor's session folder."""
    return sorted(
        path
        for root in (_SKILL_DIR, _TASK_LEARNINGS_DIR)
        for path in root.rglob("*.md")
    )


def test_the_k29_scan_covers_the_markdown_of_both_skills() -> None:
    files = _k29_files()
    names = {path.relative_to(_REPO_ROOT).as_posix() for path in files}
    assert len(files) >= 6, f"only {len(files)} markdown files in the K29 scan"
    for path in (_RETRO, _SCHEMA, _GATE, _TASK_LEARNINGS):
        assert path.relative_to(_REPO_ROOT).as_posix() in names, path.name


def test_no_file_states_the_retired_session_dir_derivation() -> None:
    offenders = {
        path.relative_to(_REPO_ROOT).as_posix(): hits
        for path in _k29_files()
        if (hits := _k29_stale_hits(path.read_text(encoding="utf-8")))
    }
    assert not offenders, (
        f"{sum(len(hits) for hits in offenders.values())} sentence(s) in {len(offenders)} "
        "file(s) describe a session-folder derivation the extractor no longer does (it reads "
        "the working directory):\n"
        + "\n".join(f"  {name}: {', '.join(hits)}" for name, hits in offenders.items())
    )


_EXIT_ONE = re.compile(r"\bexit(?:s|ed)?\s+(?:status\s+)?1\b", re.IGNORECASE)
_WORKING_DIRECTORY = re.compile(r"working directory", re.IGNORECASE)
_PROJECT_ROOT = re.compile(r"project root", re.IGNORECASE)
_FIRST_ARGUMENT = re.compile(r"first argument", re.IGNORECASE)
_EXIT_CODES_LIST_ONE = re.compile(
    r"\*\*Exit codes:\*\*.{0,400}`1`.{0,200}first argument", re.IGNORECASE
)

_K29_FACTS: tuple[tuple[str, Path, str, re.Pattern[str]], ...] = (
    (
        "Phase 1 says the working directory decides",
        _RETRO,
        "### Phase 1",
        _WORKING_DIRECTORY,
    ),
    (
        "Phase 1 says the run starts in the project root",
        _RETRO,
        "### Phase 1",
        _PROJECT_ROOT,
    ),
    ("Phase 1 says a refused run exits 1", _RETRO, "### Phase 1", _EXIT_ONE),
    (
        "Phase 1 says the session dir is then the first argument",
        _RETRO,
        "### Phase 1",
        _FIRST_ARGUMENT,
    ),
    (
        "the schema's Invocation says the working directory decides",
        _SCHEMA,
        "## Invocation",
        _WORKING_DIRECTORY,
    ),
    (
        "the schema's Invocation says a refused run exits 1",
        _SCHEMA,
        "## Invocation",
        _EXIT_ONE,
    ),
    (
        "the schema's Invocation says the session dir is then the first argument",
        _SCHEMA,
        "## Invocation",
        _FIRST_ARGUMENT,
    ),
    (
        "the schema's Porting says the extractor reads the working directory",
        _SCHEMA,
        "## Porting",
        _WORKING_DIRECTORY,
    ),
    (
        "Step 0 says the extractor runs from the project root",
        _TASK_LEARNINGS,
        "### Step 0",
        _PROJECT_ROOT,
    ),
    (
        "Step 0 lists exit 1 with the first argument as the way out",
        _TASK_LEARNINGS,
        "### Step 0",
        _EXIT_CODES_LIST_ONE,
    ),
)


def _k29_gaps() -> list[str]:
    return [
        name
        for name, path, heading, pattern in _K29_FACTS
        if not pattern.search(
            _collapsed(_section(path.read_text(encoding="utf-8"), heading))
        )
    ]


def test_the_working_directory_rule_and_its_exit_1_are_stated() -> None:
    gaps = _k29_gaps()
    assert not gaps, f"{len(gaps)} of {len(_K29_FACTS)} facts are not stated: {gaps}"


def test_the_schema_invocation_prints_the_command_in_the_skill_dir_form() -> None:
    """The block used to print `\\  # comment` after the script, which breaks the
    continuation in a shell, and a path relative to a directory no reader is in."""
    section = _section(_SCHEMA.read_text(encoding="utf-8"), "## Invocation")
    commands = [
        e
        for e in _printed_elements(section)
        if e.fenced and "extract_sessions.py" in e.text
    ]
    assert commands, "the Invocation section prints no extractor command"
    first = commands[0].text
    assert first.startswith(
        'python "${CLAUDE_SKILL_DIR}/scripts/extract_sessions.py"'
    ), first


def test_the_k29_scans_flag_the_text_they_replaced() -> None:
    """Planted positives: the old sentences, one of them wrapped across a line."""
    old = [
        "The extractor walks up from its own location to the repo root.",
        "confirm it points at THIS repo — that is the auto-derivation target",
        "# <session-dir> is auto-derived from the repo root + ~/.claude/projects/",
        "this extractor walks up to the dir containing `.claude/`",
        "the counts (10 user msgs, 1 error class, 3 sub-agents)",
        "The extractor walks up\n   from its own location.",
    ]
    for text in old:
        assert _k29_stale_hits(text), f"the scan missed a planted positive: {text!r}"
    new = [
        "`<session-dir>` is derived from the working directory",
        "the counts (10 user-channel records, 1 error class, 3 sub-agents)",
        "the schema key userMsgs counts user-channel records",
    ]
    for text in new:
        assert _k29_stale_hits(text) == [], f"the scan flagged new text: {text!r}"

    assert _EXIT_ONE.search("refused with exit 1: pass the session dir")
    assert _EXIT_ONE.search("the run exits 1")
    assert not _EXIT_ONE.search("exit 10"), "exit 10 is not exit 1"
    assert _EXIT_CODES_LIST_ONE.search(
        "4. **Exit codes:** `0` digest written · `1` the session dir could not be derived "
        "(pass it as the first argument) · `4` ambiguous"
    )
    assert not _EXIT_CODES_LIST_ONE.search(
        "4. **Exit codes:** `0` digest written · `4` ambiguous `current` · `2` usage error"
    )


# --- K29: each printed extractor command, taken out of the text, runs ------------------------


@pytest.fixture
def short_tmp() -> Iterator[Path]:
    """A short folder: the session store names a folder after the project's whole path, so
    a path in these tests is about twice as long as the folder it hangs from, and under a
    deep `tmp_path` it passes the Windows limit."""
    folder = Path(tempfile.mkdtemp(prefix="k")).resolve()
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


class _Fake(NamedTuple):
    home: Path
    project: Path
    folder: Path
    session_id: str
    plugin_root: Path
    skill_dir: Path


_SESSION_ROW = {
    "type": "user",
    "timestamp": "2026-08-14T00:00:00Z",
    "gitBranch": "main",
    "message": {"content": [{"type": "text", "text": "please fix the build"}]},
}


def _fake(root: Path) -> _Fake:
    """A fake home holding one session folder for a fake project root and an installed copy
    of the extractor. The folder is named by the extractor's own helper, not retyped."""
    extractor = _load(_EXTRACTOR, "extract_sessions_printed_commands")
    home = root / "home"
    project = root / "work" / "proj"
    project.mkdir(parents=True)
    folder = home / ".claude" / "projects" / str(extractor._encode_repo_path(project))  # pyright: ignore[reportPrivateUsage]
    folder.mkdir(parents=True)
    session_id = "s0000001-0000-0000-0000-000000000000"
    (folder / f"{session_id}.jsonl").write_text(
        json.dumps(_SESSION_ROW) + "\n", encoding="utf-8", newline="\n"
    )
    plugin_root = home / ".claude" / "plugins" / "cache" / "kit"
    skill_dir = plugin_root / "skills" / "session-retrospective"
    (skill_dir / "scripts").mkdir(parents=True)
    shutil.copyfile(_EXTRACTOR, skill_dir / "scripts" / "extract_sessions.py")
    return _Fake(home, project, folder, session_id, plugin_root, skill_dir)


def _instantiate(command: str, fake: _Fake) -> str:
    """The printed command with each placeholder filled; one this test cannot fill fails it."""
    values = {
        "CLAUDE_SKILL_DIR": fake.skill_dir.as_posix(),
        "CLAUDE_PLUGIN_ROOT": fake.plugin_root.as_posix(),
        "SESSION-ID": fake.session_id,
    }

    def fill(match: re.Match[str]) -> str:
        assert match[1] in values, f"no stand-in for the placeholder {match[0]}"
        return values[match[1]]

    command = re.sub(r"\[[^\[\]]*\]", " ", command)
    command = re.sub(r"\$\{([A-Za-z_]+)\}", fill, command)
    return re.sub(r"<([^<>]+)>", fill, command)


def _printed_extractor_command(path: Path, heading: str) -> str:
    elements = [
        e
        for e in _printed_elements(_section(path.read_text(encoding="utf-8"), heading))
        if e.fenced and "extract_sessions.py" in e.text
    ]
    assert len(elements) == 1, (
        f"expected one printed extractor command under {heading!r}, found {len(elements)}"
    )
    return elements[0].text


def _run_printed(
    command: str, fake: _Fake, cwd: Path, first_argument: Path | None = None
) -> subprocess.CompletedProcess[str]:
    words = shlex.split(_instantiate(command, fake))
    assert words[0] == "python" and words[1].endswith("extract_sessions.py"), words[:2]
    argv = [sys.executable, "-B", words[1]]
    if first_argument is not None:
        argv.append(str(first_argument))
    argv += words[2:]
    return subprocess.run(
        argv,
        cwd=cwd,
        env={**os.environ, "HOME": str(fake.home), "USERPROFILE": str(fake.home)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )


def _named_session_dir(stderr: str) -> Path:
    named = [
        line for line in stderr.splitlines() if line.startswith("Using session dir:")
    ]
    assert len(named) == 1, f"expected one `Using session dir:` line in:\n{stderr}"
    return Path(named[0].split(":", 1)[1].strip())


_PRINTED_EXTRACTOR_COMMANDS = {
    "retrospective-phase-1": (_RETRO, "### Phase 1"),
    "task-learnings-step-0": (_TASK_LEARNINGS, "### Step 0"),
}


@pytest.mark.parametrize("which", sorted(_PRINTED_EXTRACTOR_COMMANDS))
def test_the_printed_extractor_command_runs_from_the_project_root(
    which: str, short_tmp: Path
) -> None:
    """The command is read out of the skill text, filled and run with `sys.executable`.

    What this proves: the command as printed, with no session folder given, runs from the
    project root under a fake home and names that project's folder; from below the root it
    exits 1 and asks for the first argument; and the first argument is the way out. What it
    cannot prove: that a sentence around the command is true. The two printed commands
    already left the folder out before the text was corrected, so this test is green on the
    old wording too; the stale-sentence scans above carry that red, and the check that this
    test can fail is a printed command given an argument that no longer fits.
    """
    path, heading = _PRINTED_EXTRACTOR_COMMANDS[which]
    command = _printed_extractor_command(path, heading)
    fake = _fake(short_tmp)

    at_the_root = _run_printed(command, fake, fake.project)
    assert at_the_root.returncode == 0, at_the_root.stderr
    assert _named_session_dir(at_the_root.stderr).samefile(fake.folder)

    below = fake.project / "src"
    below.mkdir()
    refused = _run_printed(command, fake, below)
    assert refused.returncode == 1, (refused.returncode, refused.stderr)
    assert "first argument" in refused.stderr
    assert not (below / ".ai").exists(), "nothing is written when the run is refused"

    given = _run_printed(command, fake, below, first_argument=fake.folder)
    assert given.returncode == 0, given.stderr
    assert _named_session_dir(given.stderr).samefile(fake.folder)


# --- K33: the seam, and the gate that takes it ------------------------------------------------

_SEAM_PHRASE = re.compile(r"keep P1/P2 as proposals")
_SEAM_SOURCE = re.compile(r"AGENTS\.md`? or (?:its|the) override document")
_ITEM = re.compile(r"^(?=\d+\. )", re.MULTILINE)


def _items(section: str) -> dict[int, str]:
    """The numbered steps of a section, by number."""
    return {
        int(chunk.split(".", 1)[0]): chunk
        for chunk in _ITEM.split(_prose(section))
        if re.match(r"\d+\. ", chunk)
    }


def _seam_paragraph(section: str) -> str:
    """The paragraph outside the numbered steps that says when P1/P2 stay proposals."""
    for paragraph in re.split(r"\n\s*\n", _prose(section)):
        flat = _collapsed(paragraph)
        if not re.match(r"\d+\. ", flat) and _SEAM_PHRASE.search(flat):
            return flat
    return ""


def _registers_in_the_entry(one: str) -> bool:
    """Step 1 names the changelog entry as where a seam run registers the proposals: the first
    mention of the entry comes before `applying none`, so a later mention (the gates, the
    anecdote, the reachability check) cannot stand in for it."""
    entry = one.find("changelog entry")
    none = one.find("applying none")
    return 0 <= entry < none


def _phase_7_gaps(section: str) -> list[str]:
    """The facts of the seam that Phase 7 must state; each name is one the section lacks."""
    items = _items(section)
    seam = _seam_paragraph(section)
    one = _collapsed(items.get(1, ""))
    four = _collapsed(items.get(4, ""))
    stated = {
        "no paragraph outside the numbered steps names the seam": bool(seam),
        "the seam names AGENTS.md or the override document": bool(
            _SEAM_SOURCE.search(seam)
        ),
        "the seam paragraph says step 1 registers": "step 1 registers" in seam,
        "the seam paragraph says steps 2 and 3 run either way": "steps 2 and 3" in seam,
        "step 1 keeps the default of applying in-session": (
            "Apply the P1/P2 recommendations in-session now" in one
        ),
        "step 1 registers them instead under the seam": "register them instead" in one,
        "step 1 prints the durability check with --proposals-only in one span": bool(
            re.search(
                r"`[^`]*check_report\.py[^`]*--check durability[^`]*--proposals-only[^`]*`",
                one,
            )
        ),
        "step 1 says the changelog entry is still required": bool(
            re.search(r"\bentry\b.{0,20}\bstill\b", one)
        ),
        "step 1 says the proposals are registered in the changelog entry, applying none": (
            _registers_in_the_entry(one)
        ),
        "step 1 scopes the completion gates to the applied case": bool(
            re.search(
                r"\bApplied,? route them through the same completion gates\b", one
            )
        ),
        "step 1 says a registered run owes no hypothesis or regression test": (
            "no hypothesis or regression test is due" in one
        ),
        "step 4 offers the consolidation": "learning-consolidator" in four,
    }
    return [name for name, ok in stated.items() if not ok]


def _phase_7() -> str:
    return _section(_RETRO.read_text(encoding="utf-8"), "### Phase 7")


def test_phase_7_names_the_seam_and_applies_it_to_steps_1_and_4() -> None:
    gaps = _phase_7_gaps(_phase_7())
    assert not gaps, f"Phase 7 does not state {len(gaps)} fact(s) of the seam: {gaps}"


def test_the_gate_of_phase_5_names_the_proposals_only_flag() -> None:
    """Without it a proposals-only run fails the completeness gate it is told to pass."""
    gate = _collapsed(_section(_RETRO.read_text(encoding="utf-8"), "### Phase 5"))
    assert re.search(r"check_report\.py.{0,300}--proposals-only", gate), (
        "Phase 5 prints the completeness gate without saying a proposals-only run adds "
        "--proposals-only"
    )


_NEW_PHASE_7 = """### Phase 7 — Present Summary & Apply the Default

**The seam.** When the project's `AGENTS.md` or its override document says to keep P1/P2 as
proposals, step 1 registers them instead of applying them; steps 2 and 3 run either way.

1. **Apply the P1/P2 recommendations in-session now** — unless the seam applies: then register
   them instead, each named in the changelog entry, applying none. **Applied, route them
   through the same completion gates as feature work.** Assert reachability with
   `check_report.py --check
   durability --proposals-only` (then no hypothesis or regression test is due, since nothing
   was applied; the entry still is).

2. **Auto-append the P4 items.**
3. **Surface the sibling cadence.**
4. **If 4g settled a signal,** offer `hypothesis-validator`, or under the seam
   `learning-consolidator`, whose Phase 2 runs it.
"""

_OLD_PHASE_7 = """### Phase 7 — Present Summary & Apply the Default

Then COMMIT to the default — do not end on an open ask-menu:

1. **Apply the P1/P2 recommendations in-session now.** They are visible, reviewable edits.
   **Then route them through the same completion gates as feature work** — an `ai-changelog`
   entry, a companion improvement hypothesis, and a regression test for anything mechanical.
   **Writing the entry is not landing it** — assert reachability with `check_report.py --check
   durability`.

2. **Auto-append the P4 items.**
3. **Surface the sibling cadence.**
4. **If 4g settled a window-elapsed signal,** offer to run `hypothesis-validator` now.

On autonomous (model-initiated) runs, steps 1–4 ARE the behavior — no ask-menu.
"""


def test_the_seam_check_fails_on_the_phase_7_it_replaced() -> None:
    """Planted positives: the old Phase 7, then the new one with one fact removed at a time."""
    assert _phase_7_gaps(_NEW_PHASE_7) == []
    old = _phase_7_gaps(_OLD_PHASE_7)
    assert "step 1 registers them instead under the seam" in old
    assert "the seam paragraph says step 1 registers" in old
    assert "step 4 offers the consolidation" in old
    assert "step 1 prints the durability check with --proposals-only in one span" in old
    assert "step 1 scopes the completion gates to the applied case" in old, (
        "the old Phase 7 told the reader to route the proposals through the completion "
        "gates with no word about the case where nothing was applied"
    )
    assert "step 1 says a registered run owes no hypothesis or regression test" in old
    assert (
        "step 1 says the proposals are registered in the changelog entry, applying none"
        in old
    )

    removals = {
        "the seam paragraph says step 1 registers": (
            "step 1 registers",
            "step 1 applies",
        ),
        "step 1 registers them instead under the seam": (
            "register\n   them instead",
            "apply them",
        ),
        "the seam paragraph says steps 2 and 3 run either way": (
            "steps 2 and 3",
            "steps 2 to 3",
        ),
        "the seam names AGENTS.md or the override document": (
            "or its override document",
            "or nothing",
        ),
        "step 4 offers the consolidation": (
            "`learning-consolidator`, whose",
            "the validator, whose",
        ),
        "step 1 says the changelog entry is still required": (
            "the entry still is",
            "nothing is",
        ),
        "step 1 prints the durability check with --proposals-only in one span": (
            "--check\n   durability --proposals-only",
            "--check\n   durability",
        ),
        "step 1 keeps the default of applying in-session": (
            "Apply the P1/P2 recommendations in-session now",
            "Register the P1/P2 recommendations",
        ),
        "step 1 says the proposals are registered in the changelog entry, applying none": (
            "each named in the changelog entry, ",
            "",
        ),
        "step 1 scopes the completion gates to the applied case": (
            "**Applied, route them",
            "**Then route them",
        ),
        "step 1 says a registered run owes no hypothesis or regression test": (
            "no hypothesis or regression test is due",
            "no hypothesis is due",
        ),
    }
    for expected, (before, after) in removals.items():
        assert before in _NEW_PHASE_7, f"the planted text no longer holds {before!r}"
        assert _phase_7_gaps(_NEW_PHASE_7.replace(before, after)) == [expected], (
            expected
        )


# --- the hypothesis validator runs in the consolidator's Phase 2 AND its Phase 6.5 -----------

_VALIDATOR_FROM_PHASE_6_5 = re.compile(r"learning-consolidator\s+Phase\s+6\.5")
_PLACEMENT = re.compile(r"Phase 2\b.{0,120}Phase 6\.5")

# Where a sentence says who runs the validator: (file, the words that open the claim). Each
# is followed within a short window by both of the consolidator's phases that run it.
_PLACEMENT_CLAIMS: tuple[tuple[str, str], ...] = (
    (
        "plugins/core/skills/ai-improvement-tracker/SKILL.md",
        "Only the `hypothesis-validator` skill",
    ),
    (
        "plugins/core/skills/ai-improvement-tracker/SKILL.md",
        "reserved for the `hypothesis-validator` skill",
    ),
    (
        "plugins/core/skills/session-retrospective/SKILL.md",
        "belong to the `hypothesis-validator` skill",
    ),
)


def _placement_gap(text: str, opening: str) -> str | None:
    """Why the claim that opens with `opening` does not place the validator, or None."""
    flat = _collapsed(text)
    at = flat.find(opening)
    if at < 0:
        return f"no sentence opens with {opening!r}"
    if not _PLACEMENT.search(flat[at : at + 360]):
        return f"the sentence at {opening!r} does not name both Phase 2 and Phase 6.5"
    return None


def test_no_skill_says_the_validator_runs_from_phase_6_5_alone() -> None:
    surface = _markdown_surface()
    assert len(surface) > 120, f"only {len(surface)} shipped markdown files in the scan"
    offenders = [
        name
        for name in surface
        if _VALIDATOR_FROM_PHASE_6_5.search(_collapsed(_read(name)))
    ]
    assert not offenders, (
        "these files say the validator is invoked from learning-consolidator Phase 6.5; it "
        f"also runs at the end of Phase 2: {offenders}"
    )
    gaps = [
        gap
        for name, opening in _PLACEMENT_CLAIMS
        if (gap := _placement_gap(_read(name), opening))
    ]
    assert not gaps, gaps


def test_the_validator_scan_flags_the_text_it_replaced() -> None:
    for old in (
        "(invoked from learning-consolidator Phase 6.5, approval-gated; offered by",
        "(invoked via learning-consolidator\n  Phase 6.5)",
        "(normally invoked via learning-consolidator Phase 6.5)",
    ):
        assert _VALIDATOR_FROM_PHASE_6_5.search(_collapsed(old)), old
    new = (
        "Only the `hypothesis-validator` skill (run by learning-consolidator at the end of "
        "its Phase 2 and again in its Phase 6.5) changes it."
    )
    assert not _VALIDATOR_FROM_PHASE_6_5.search(_collapsed(new))
    assert _placement_gap(new, "Only the `hypothesis-validator` skill") is None
    old_claim = (
        "Only the `hypothesis-validator` skill (invoked from learning-consolidator "
        "Phase 6.5, approval-gated) changes it."
    )
    assert _placement_gap(old_claim, "Only the `hypothesis-validator` skill")
    assert _placement_gap(new, "an opening the text does not have")


# --- the gate reference says what the flag drops, and what it keeps ---------------------------

_GATE_ALWAYS_HAS_HYPOTHESIS = re.compile(
    r"and\s+that\s+a\s+companion\s+hypothesis\s+exists\s+for\s+the\s+same\s+date",
    re.IGNORECASE,
)

# What the paragraph of the `--check durability` section must say. The flag drops ONE
# requirement; a paragraph that said it drops two (or none) would send a reader to skip the
# changelog entry, which is the only durable record of the proposals.
_GATE_FACTS: dict[str, re.Pattern[str]] = {
    "names the flag": re.compile(r"--proposals-only"),
    "says the flag is for a run that keeps P1/P2 as proposals": re.compile(
        r"\bkeeps P1/P2 as proposals\b"
    ),
    "says the flag drops the hypothesis requirement and only that one": re.compile(
        r"\bdrops the hypothesis requirement and only that one\b"
    ),
    "says the entry is still required": re.compile(r"\bthe entry is still required\b"),
    "says the entry still has to be reachable": re.compile(
        r"\bstill has to be reachable\b"
    ),
}


def _durability_paragraph(text: str) -> str:
    """The first paragraph of the `--check durability` section, whitespace collapsed: the one
    that says what the check asserts and what the flag changes."""
    section = _section(text, "## `--check durability`")
    return _collapsed(re.split(r"\n\s*\n", section)[1])


def _gate_gaps(paragraph: str) -> list[str]:
    """Each fact of the paragraph that is missing, and the old claim if it is still there."""
    gaps = [
        name for name, pattern in _GATE_FACTS.items() if not pattern.search(paragraph)
    ]
    if _GATE_ALWAYS_HAS_HYPOTHESIS.search(paragraph):
        gaps.append("still says a companion hypothesis always exists")
    return gaps


def test_the_gate_reference_says_what_the_flag_drops_and_what_it_keeps() -> None:
    text = _GATE.read_text(encoding="utf-8")
    gaps = _gate_gaps(_durability_paragraph(text))
    assert not gaps, f"the durability paragraph of the gate reference: {gaps}"
    whole = _collapsed(_section(text, "## `--check durability`"))
    assert not _GATE_ALWAYS_HAS_HYPOTHESIS.search(whole), (
        "the durability section still says a companion hypothesis always exists"
    )


def test_the_gate_reference_check_fails_on_the_wording_it_guards() -> None:
    """Planted: the real paragraph with one claim reversed at a time, each producing exactly
    the gap it targets, and the old sentence appended."""
    paragraph = _durability_paragraph(_GATE.read_text(encoding="utf-8"))
    assert _gate_gaps(paragraph) == []
    plants = {
        "names the flag": ("--proposals-only", "--only"),
        "says the flag is for a run that keeps P1/P2 as proposals": (
            "keeps P1/P2 as proposals",
            "applies P1/P2",
        ),
        "says the flag drops the hypothesis requirement and only that one": (
            "and only that one",
            "and the changelog requirement",
        ),
        "says the entry is still required": (
            "the entry is still required",
            "the entry is not required",
        ),
        "says the entry still has to be reachable": (
            "still has to be reachable",
            "need not be reachable",
        ),
    }
    for expected, (before, after) in plants.items():
        assert before in paragraph, f"the paragraph no longer holds {before!r}"
        assert _gate_gaps(paragraph.replace(before, after)) == [expected], expected
    assert _gate_gaps(
        paragraph
        + " It asserts the entry is reachable from `HEAD` and that a companion\n"
        " hypothesis exists for the same date."
    ) == ["still says a companion hypothesis always exists"]
    assert _GATE_ALWAYS_HAS_HYPOTHESIS.search(
        "is reachable from `HEAD` — and that a companion\n hypothesis exists for the same date."
    )
    assert not _GATE_ALWAYS_HAS_HYPOTHESIS.search(
        "and, unless --proposals-only says nothing was applied, that a companion hypothesis exists"
    )
