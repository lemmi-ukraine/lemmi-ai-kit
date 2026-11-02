"""initiative-cleanup's audit script reads every file type and the ref it is told to.

The reference sweep opened a fixed list of suffixes, so a C# comment that cites a spec folder
was never listed. The evidence gate counted a hit as code by suffix alone and always searched
HEAD, so a symbol that exists only in a language it does not know, or only on the branch under
review, read as documentation or as absent, and spec folders that are not tracked could never
make a symbol SHARED. These tests run the script the way an adopter does: copied out of this
repository, inside a temporary git repository, over files of the shapes that failed.

The evidence gate also handed the symbol to `git grep` as a pattern and ignored git's own
failures, so a dotted symbol matched a different word, while a bracketed one, or one that
begins with dashes, made git fail and read as ABSENT.

Each assertion fails on the script it replaced. The last tests fire the text scan at planted
text before its silence on the real skill files is trusted.
"""

import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from lemmi_ai_kit.manifest import shipped_skill_dirs

_SKILL = shipped_skill_dirs()["initiative-cleanup"]
_TIMEOUT_SECONDS = 60
_SYMBOL = "WidgetFactory"
_BRANCH = "feature"
_SUFFIX_FILTER = "--include='*.md'"


@dataclass(frozen=True)
class Consumer:
    """The skill's script as an installed copy, and the repository it should read."""

    script: Path
    repo: Path


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=_TIMEOUT_SECONDS,
    )
    return result.stdout


def _write(repo: Path, relative: str, text: str) -> None:
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode("utf-8"))


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "--", ".")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m", message)


@pytest.fixture
def consumer(tmp_path: Path) -> Consumer:
    """A copied-out skill beside a repository whose branch `feature` alone holds a symbol.

    The copy sits outside this repository because the script looks for a `.git` above itself
    and falls back to the working directory, which is the temporary repository here.
    """
    installed = (
        tmp_path / "plugin cache" / "orchestration" / "skills" / "initiative-cleanup"
    )
    shutil.copytree(_SKILL, installed, ignore=shutil.ignore_patterns("__pycache__"))
    enclosing = [p for p in installed.parents if (p / ".git").exists()]
    assert not enclosing, (
        f"the temporary directory sits inside a git checkout ({enclosing[0]}), so the "
        "script would measure that checkout; run pytest with --basetemp outside any repository"
    )
    repo = tmp_path / "consumer repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for key, value in (
        ("user.name", "Fixture"),
        ("user.email", "fixture@example.invalid"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
    ):
        _git(repo, "config", "--local", key, value)
    _write(repo, "README.md", "base\n")
    _commit(repo, "base")
    base = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    _git(repo, "checkout", "-q", "-b", _BRANCH)
    _write(repo, "src/Widget.cs", f"public class {_SYMBOL} {{ }}\n")
    _write(repo, "docs/widget.md", f"{_SYMBOL} builds widgets.\n")
    _commit(repo, "the symbol exists only on this branch")
    _git(repo, "checkout", "-q", base)
    return Consumer(installed / "scripts" / "audit_cleanup_targets.py", repo)


def _audit(consumer: Consumer, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(consumer.script), *args],
        cwd=consumer.repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )


def _both(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


_LISTED = re.compile(r"^ {4}(?P<path>[^:\n]+):\d+: ", re.MULTILINE)


def _listed(stdout: str) -> set[str]:
    """The files a `refs` run names, from its indented `path:line: text` rows."""
    return {match.group("path") for match in _LISTED.finditer(stdout)}


# --- refs: no suffix list ----------------------------------------------------------------


def test_refs_lists_a_c_sharp_line_that_cites_an_untracked_spec(
    consumer: Consumer,
) -> None:
    repo = consumer.repo
    _write(repo, "src/Billing.cs", "// Rationale: .specs/a/design.md\n")
    _commit(repo, "a source file cites the spec")
    _write(repo, ".specs/a/design.md", "the spec\n")
    _write(repo, ".specs/b/design.md", "another spec nobody cites\n")
    assert _git(repo, "ls-files", "--", ".specs").strip() == "", (
        "the specs must stay untracked"
    )

    cited = _audit(consumer, "refs", "--target", ".specs/a")
    assert cited.returncode == 1, _both(cited)
    assert "src/Billing.cs:1:" in cited.stdout, _both(cited)

    uncited = _audit(consumer, "refs", "--target", ".specs/b")
    assert uncited.returncode == 0, _both(uncited)
    assert _listed(uncited.stdout) == set(), _both(uncited)


def test_refs_reads_files_of_every_type_but_skips_binary_and_archived_ones(
    consumer: Consumer,
) -> None:
    repo = consumer.repo
    needle = ".specs/a"
    for relative in ("src/Billing.cs", "scripts/deploy.ps1", "Makefile"):
        _write(repo, relative, f"cites {needle}/design.md\n")
    _write(repo, ".gitignore", "hand/\n")
    _commit(repo, "tracked files of three kinds")
    _write(repo, "hand/handoff.log", f"an ignored hand-off cites {needle}\n")
    _write(repo, ".specs/a/design.md", f"the target names itself: {needle}/design.md\n")
    (repo / "data").mkdir()
    (repo / "data" / "blob.bin").write_bytes(b"\0" + needle.encode() + b"\0\n")
    _write(repo, ".ai/tmp/scratch.md", f"scratch cites {needle}\n")
    for skipped in ("data/blob.bin", ".ai/tmp/scratch.md", ".specs/a/design.md"):
        assert needle.encode() in (repo / skipped).read_bytes(), (
            f"{skipped} must hold the needle, or its absence from the listing proves nothing"
        )

    result = _audit(consumer, "refs", "--target", needle)

    assert result.returncode == 1, _both(result)
    assert _listed(result.stdout) == {
        "Makefile",
        "hand/handoff.log",
        "scripts/deploy.ps1",
        "src/Billing.cs",
    }, _both(result)


# --- evidence: the ref, the code suffixes, the verdict that names what it did not count --


@pytest.mark.parametrize(
    ("args", "returncode", "must_hold", "must_not_hold"),
    [
        pytest.param(
            ("--ref", _BRANCH, "--code-suffix", ".cs"),
            0,
            ("IMPLEMENTED", f"ref={_BRANCH}"),
            ("NO VERDICT", "ABSENT"),
            id="ref-and-suffix-together",
        ),
        pytest.param(
            ("--ref", _BRANCH),
            1,
            ("NO VERDICT: hits in uncounted file types (.cs); see --code-suffix",),
            ("DOC-ONLY", "IMPLEMENTED"),
            id="no-suffix-names-the-uncounted-type",
        ),
        pytest.param(
            ("--code-suffix", ".cs"),
            1,
            ("ABSENT",),
            ("IMPLEMENTED",),
            id="suffix-without-the-ref-searches-head",
        ),
        pytest.param(
            (),
            1,
            ("ABSENT",),
            ("IMPLEMENTED",),
            id="neither-option",
        ),
        pytest.param(
            ("--ref", _BRANCH, "--code-suffix", ".cs", "--code-suffix", ".csproj"),
            0,
            ("IMPLEMENTED",),
            ("NO VERDICT",),
            id="repeated-suffix-first-one-counts",
        ),
        pytest.param(
            ("--ref", _BRANCH, "--code-suffix", ".csproj", "--code-suffix", ".cs"),
            0,
            ("IMPLEMENTED",),
            ("NO VERDICT",),
            id="repeated-suffix-last-one-counts",
        ),
    ],
)
def test_evidence_for_a_symbol_that_exists_only_on_a_branch(
    consumer: Consumer,
    args: tuple[str, ...],
    returncode: int,
    must_hold: tuple[str, ...],
    must_not_hold: tuple[str, ...],
) -> None:
    result = _audit(consumer, "evidence", "--symbol", _SYMBOL, *args)
    out = _both(result)
    assert result.returncode == returncode, out
    for text in must_hold:
        assert text in out, f"missing {text!r}:\n{out}"
    for text in must_not_hold:
        assert text not in out, f"unexpected {text!r}:\n{out}"


def test_evidence_does_not_count_data_files_as_code_and_keeps_the_doc_verdict(
    consumer: Consumer,
) -> None:
    repo = consumer.repo
    _write(repo, "data/payload.json", '{"shape": "PayloadShape"}\n')
    _write(repo, "docs/only.md", "OnlyDocSymbol is described here\n")
    _commit(repo, "a data file and a document")

    data = _audit(consumer, "evidence", "--symbol", "PayloadShape")
    assert data.returncode == 1, _both(data)
    assert "NO VERDICT: hits in uncounted file types (.json)" in data.stdout, _both(
        data
    )
    assert "IMPLEMENTED" not in data.stdout, _both(data)

    doc = _audit(consumer, "evidence", "--symbol", "OnlyDocSymbol")
    assert doc.returncode == 1, _both(doc)
    assert "DOC-ONLY" in doc.stdout, _both(doc)


@pytest.mark.parametrize("ref", ["no-such-branch", "HEAD^{tree}"])
def test_an_unresolvable_ref_exits_two_instead_of_reading_as_absent(
    consumer: Consumer, ref: str
) -> None:
    result = _audit(consumer, "evidence", "--symbol", _SYMBOL, "--ref", ref)
    out = _both(result)
    assert result.returncode == 2, out
    assert "does not resolve" in out, out
    assert "ABSENT" not in out, out


def test_a_symbol_named_by_two_untracked_spec_folders_is_shared(
    consumer: Consumer,
) -> None:
    repo = consumer.repo
    args = ("evidence", "--symbol", _SYMBOL, "--ref", _BRANCH, "--code-suffix", ".cs")
    _write(repo, ".specs/a/spec.md", f"{_SYMBOL} is the deliverable\n")
    assert _git(repo, "ls-files", "--", ".specs").strip() == "", (
        "the specs must stay untracked"
    )

    alone = _audit(consumer, *args)
    assert alone.returncode == 0, _both(alone)
    assert "IMPLEMENTED" in alone.stdout and "SHARED" not in alone.stdout, _both(alone)

    _write(repo, ".specs/b/spec.md", f"{_SYMBOL} again, in a second spec\n")
    shared = _audit(consumer, *args)
    assert shared.returncode == 1, _both(shared)
    assert "SHARED" in shared.stdout, _both(shared)
    assert ".specs/a" in shared.stdout and ".specs/b" in shared.stdout, _both(shared)


def test_a_symbol_named_twice_inside_one_spec_folder_is_not_shared(
    consumer: Consumer,
) -> None:
    repo = consumer.repo
    _write(repo, ".specs/a/spec.md", f"{_SYMBOL} is the deliverable\n")
    _write(repo, ".specs/a/design.md", f"{_SYMBOL} is designed here\n")

    result = _audit(
        consumer,
        "evidence",
        "--symbol",
        _SYMBOL,
        "--ref",
        _BRANCH,
        "--code-suffix",
        ".cs",
    )

    assert result.returncode == 0, _both(result)
    assert "IMPLEMENTED" in result.stdout and "SHARED" not in result.stdout, _both(
        result
    )


@pytest.mark.parametrize(
    ("second_copy", "shared"),
    [
        pytest.param(
            ".specs/b/backups/spec.md", False, id="copy-under-a-backups-folder"
        ),
        pytest.param(".specs/b/.ai/tmp/spec.md", False, id="copy-under-scratch"),
        pytest.param(".specs/b/spec.md", True, id="same-text-in-a-live-folder"),
    ],
)
def test_a_copy_in_an_archive_folder_does_not_make_a_symbol_shared(
    consumer: Consumer, second_copy: str, shared: bool
) -> None:
    repo = consumer.repo
    _write(repo, ".specs/a/spec.md", f"{_SYMBOL} is the deliverable\n")
    _write(repo, second_copy, f"{_SYMBOL} again, in a second place\n")

    result = _audit(
        consumer,
        "evidence",
        "--symbol",
        _SYMBOL,
        "--ref",
        _BRANCH,
        "--code-suffix",
        ".cs",
    )

    out = _both(result)
    if shared:
        assert result.returncode == 1, out
        assert "SHARED" in result.stdout, out
    else:
        assert result.returncode == 0, out
        assert "IMPLEMENTED" in result.stdout and "SHARED" not in result.stdout, out


# --- evidence: the symbol is text, and a search that did not run is not a verdict -------------


@pytest.mark.parametrize(
    ("symbol", "different_word"),
    [
        pytest.param("Foo.Bar", "FooXBar", id="dot-is-not-any-character"),
        pytest.param("a*b", "aab", id="star-is-not-a-repeat"),
    ],
)
def test_a_symbol_with_a_pattern_character_does_not_match_a_different_word(
    consumer: Consumer, symbol: str, different_word: str
) -> None:
    repo = consumer.repo
    _write(repo, "src/decoy.py", f"value = {different_word!r}\n")
    _commit(repo, "a word the symbol would match if it were a pattern")

    decoyed = _audit(consumer, "evidence", f"--symbol={symbol}")
    out = _both(decoyed)
    assert decoyed.returncode == 1, out
    assert "ABSENT" in decoyed.stdout and "IMPLEMENTED" not in decoyed.stdout, out
    assert "src/decoy.py" not in decoyed.stdout, out

    _write(repo, "src/real.py", f"value = {symbol!r}\n")
    _commit(repo, "the symbol itself")
    found = _audit(consumer, "evidence", f"--symbol={symbol}")
    out = _both(found)
    assert found.returncode == 0, out
    assert "IMPLEMENTED" in found.stdout and "src/real.py" in found.stdout, out
    assert "src/decoy.py" not in found.stdout, out


@pytest.mark.parametrize(
    ("symbol", "line"),
    [
        pytest.param("byte[]", "payload: byte[] = []", id="empty-brackets"),
        pytest.param("List[int]", "rows: List[int] = []", id="brackets-around-a-word"),
        pytest.param(
            "--dry-run", 'parser.add_argument("--dry-run")', id="leading-dashes"
        ),
    ],
)
def test_a_symbol_made_of_pattern_or_option_syntax_is_found_as_text(
    consumer: Consumer, symbol: str, line: str
) -> None:
    repo = consumer.repo
    _write(repo, "src/code.py", f"{line}\n")
    _commit(repo, "code that holds the symbol")

    result = _audit(consumer, "evidence", f"--symbol={symbol}")

    out = _both(result)
    assert result.returncode == 0, out
    assert "IMPLEMENTED" in result.stdout and "src/code.py" in result.stdout, out
    assert "ABSENT" not in out, out


def test_a_git_grep_that_fails_exits_two_instead_of_reading_as_absent(
    consumer: Consumer,
) -> None:
    repo = consumer.repo
    tree = _git(repo, "rev-parse", "HEAD^{tree}").strip()
    loose = repo / ".git" / "objects" / tree[:2] / tree[2:]
    assert loose.is_file(), (
        "the tree must be a loose object, or deleting it proves nothing"
    )
    loose.chmod(stat.S_IREAD | stat.S_IWRITE)
    loose.unlink()
    # The fixture is what it claims: HEAD still names a commit, and git itself cannot search it.
    still_a_commit = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
        cwd=repo,
        capture_output=True,
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    search = subprocess.run(
        ["git", "grep", "-l", "-I", "-F", "-e", _SYMBOL, "HEAD", "--"],
        cwd=repo,
        capture_output=True,
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert still_a_commit.returncode == 0
    assert search.returncode > 1, "git grep must fail here, or the script is not tested"

    result = _audit(consumer, "evidence", "--symbol", _SYMBOL)

    out = _both(result)
    assert result.returncode == 2, out
    assert "git grep failed" in out, out
    assert "ABSENT" not in out and "IMPLEMENTED" not in out, out


# --- the skill's own text ----------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s+\S")
_CONTINUATION = re.compile(r"\\\r?\n[ \t]*")
_EVIDENCE_COMMAND = re.compile(r"\bevidence\b\s+--symbol\b[^\n]*")
_SWEEP = "grep -rIn --exclude-dir=.git '<basename>' ."
_UNTRACKED_SWEEP = (
    "git grep --untracked --no-exclude-standard -I -n '<basename>' -- ':!.ai/tmp'"
)
_GATE_EXIT_TWO = "exit 2 = a git failure (the ref or git grep), never ABSENT"
_HELP_SENTENCES = (
    "The symbol is searched as a fixed string, never as a pattern.",
    "Exit codes: 0 = gate passed, 1 = gate failed, 2 = usage error, or a search that could not "
    "run (a ref that does not resolve, a `git grep` that failed): never read a 2 as ABSENT or as "
    "a pass.",
)


def _skill_files() -> list[Path]:
    """Every file of the skill as it ships: build output is not skill text."""
    return sorted(
        path
        for path in _SKILL.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _tracked_skill_files() -> list[str]:
    """The same set according to git, as an independent second instrument."""
    result = subprocess.run(
        ["git", "-C", str(_SKILL), "ls-files", "-z", "--", "."],
        capture_output=True,
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        pytest.fail(
            "git ls-files failed, so the skill's file set cannot be checked: "
            + result.stderr.decode("utf-8", "replace")
        )
    return sorted(entry for entry in result.stdout.decode("utf-8").split("\0") if entry)


def _files_holding(needle: str, files: list[Path]) -> list[str]:
    return [
        path.name
        for path in files
        if needle in path.read_text(encoding="utf-8", errors="replace")
    ]


def _logical(text: str) -> str:
    """The text with every backslash line continuation joined, so a printed command that is
    re-wrapped over two lines reads as the one line it is."""
    return _CONTINUATION.sub(" ", text)


def _fold(text: str) -> str:
    """The text with continuations joined, blockquote markers dropped and every run of
    whitespace one space, so a re-wrap of prose or of a command changes no match."""
    return " ".join(re.sub(r"(?m)^\s*>+ ?", "", _logical(text)).split())


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
        fence = line.lstrip().startswith("```")
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


def _skill_section(heading: str) -> str:
    text = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    return _section(text, heading, "initiative-cleanup SKILL.md")


def _evidence_commands(section: str) -> list[str]:
    return _EVIDENCE_COMMAND.findall(_logical(section))


def test_the_scan_surface_is_every_tracked_file_of_the_skill() -> None:
    on_disk = sorted(path.relative_to(_SKILL).as_posix() for path in _skill_files())
    tracked = _tracked_skill_files()
    assert on_disk, f"{_SKILL} holds no file, so every scan below would read nothing"
    assert on_disk == tracked, (
        f"the scan reads {len(on_disk)} files and git tracks {len(tracked)}: "
        f"only on disk {sorted(set(on_disk) - set(tracked))}, "
        f"only tracked {sorted(set(tracked) - set(on_disk))}"
    )
    must_read = {
        "SKILL.md",
        "references/output-templates.md",
        "references/retirement-sweep.md",
        "scripts/audit_cleanup_targets.py",
    }
    assert must_read <= set(on_disk), (
        f"the scan of {len(on_disk)} files lost one it must read: {sorted(must_read - set(on_disk))}"
    )


def test_no_skill_file_holds_the_suffix_filtered_sweep() -> None:
    assert _files_holding(_SUFFIX_FILTER, _skill_files()) == []


def test_step_4b_runs_a_suffix_free_sweep_in_both_forms() -> None:
    four_b = _fold(_skill_section("### 4b."))
    assert _SWEEP in four_b
    assert _UNTRACKED_SWEEP in four_b, (
        "Step 4b lost the form that also sees ignored files"
    )
    assert "plain `--untracked` skips ignored files" in four_b


def test_the_completion_report_runs_the_sweep_step_4b_runs() -> None:
    templates = (_SKILL / "references" / "output-templates.md").read_text(
        encoding="utf-8"
    )
    step_7 = _fold(_section(templates, "## Step 7", "output-templates.md"))
    assert _SWEEP in step_7, "the completion report's sweep is not the one Step 4b runs"


@pytest.mark.parametrize(
    "heading",
    [
        pytest.param("## The gates are a script", id="gates-block"),
        pytest.param("### 4a.", id="step-4a"),
        pytest.param("### 5.5a", id="step-5-5a"),
    ],
)
def test_every_evidence_command_passes_the_verified_ref(heading: str) -> None:
    commands = _evidence_commands(_skill_section(heading))
    assert commands, f"the section {heading!r} runs no `evidence --symbol` command"
    unpinned = [command for command in commands if "--ref" not in command]
    assert not unpinned, f"an evidence command does not pass the ref: {unpinned}"


def test_step_4a_says_what_the_ref_and_the_code_suffix_do() -> None:
    four_a = _fold(_skill_section("### 4a."))
    for phrase in (
        "`--ref` is the ref Step 1 verified",
        "default `HEAD` answers about your checkout, not the branch",
        "is NO VERDICT until `--code-suffix .cs` names it",
    ):
        assert phrase in four_a, f"Step 4a does not say {phrase!r}"


def test_the_gates_comment_on_evidence_names_exit_two() -> None:
    """Step 5.5a's comment on the evidence gate said what an exit of 1 means and left out 2, the one
    code the script says must never be read as ABSENT or as a pass."""
    commands = _evidence_commands(_skill_section("### 5.5a"))
    assert len(commands) == 1, (
        f"Step 5.5a runs {len(commands)} evidence commands, not 1"
    )
    assert _GATE_EXIT_TWO in _fold(commands[0]), (
        f"Step 5.5a's evidence comment does not say {_GATE_EXIT_TWO!r}: {commands[0]}"
    )


def _help_text() -> str:
    """The script's --help output, whitespace folded: its module docstring, printed as written."""
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(_SKILL / "scripts" / "audit_cleanup_targets.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, _both(result)
    return " ".join(result.stdout.split())


def test_the_help_says_the_symbol_is_a_fixed_string_and_what_exit_two_means() -> None:
    """The help text is what an adopter reads before running the gates: it says the symbol is text,
    not a pattern, and that an exit of 2 is a search that could not run, never ABSENT or a pass."""
    help_text = _help_text()
    for sentence in _HELP_SENTENCES:
        assert sentence in help_text, f"--help does not say {sentence!r}"


def test_the_text_scan_sees_planted_text(tmp_path: Path) -> None:
    planted = tmp_path / "planted.md"
    planted.write_text(f"run grep -rn x {_SUFFIX_FILTER} .\n", encoding="utf-8")
    clean = tmp_path / "clean.md"
    clean.write_text("run grep -rIn x .\n", encoding="utf-8")
    assert _files_holding(_SUFFIX_FILTER, [planted, clean]) == ["planted.md"]
    assert _files_holding("--no-such-flag", [planted, clean]) == []


def test_the_text_helpers_see_planted_text_and_fail_loudly() -> None:
    planted = "\n".join(
        [
            "### 4b. Repoint",
            "> **A quoted rule,** wrapped",
            "> over two lines.",
            "```bash",
            "# a comment inside a fence is not a heading",
            "python s evidence --symbol A \\",
            "    --ref origin/dev",
            "python s evidence --symbol B",
            "```",
            "### 4c. Next",
            "after the section",
        ]
    )
    four_b = _section(planted, "### 4b.", "planted")
    assert "# a comment inside a fence" in four_b and "after the section" not in four_b
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "### 9z.", "planted")
    assert "**A quoted rule,** wrapped over two lines." in _fold(four_b)
    commands = _evidence_commands(four_b)
    assert len(commands) == 2
    assert "--ref" in commands[0] and "--ref" not in commands[1]
