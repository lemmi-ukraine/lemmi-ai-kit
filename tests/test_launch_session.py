"""`orchestrate` starts a headless session with one script, and a plan row may say `pasted` with no reason.

Section 2a held measured launch facts and no launcher, so each orchestrator rebuilt the command by
hand, and the plan template told a planner that `headless` "requires the launcher" and that `pasted`
is the fallback to justify. The script prints the exact command, runs it only when told to, and
checks the flags against the installed CLI at zero cost. The tests run it the way an adopter does,
copied out of this repository into a folder whose name holds a space, against a stand-in for the
CLI that records the arguments and the standard input it was started with.

The check is a sentinel: an unknown flag appended last, which the CLI rejects while parsing, so
every real flag before it was read. It passes only when the CLI names the sentinel in an `unknown
option` error. A CLI that accepts the sentinel, a missing CLI and an answer nobody recognises read
CANNOT MEASURE and exit 2, never a pass. The check sends no prompt and cuts standard input, so
even a CLI that accepted the sentinel would have nothing to run.

THE SURFACE, in numbers the tests assert: 1 script, copied out and run; 3 modes (print, run,
check); 12 refusals (9 of a path that is missing or not relative, or of a missing argument, and
3 of the absolute spelling of a file that exists); 11 planted CLI answers for the check;
2 files read for wording (`orchestrate/SKILL.md` and the plan template), judged in 6 scopes by 9
claims and 11 phrases (a claim holds when every phrase is in its scope, lower-cased, whitespace
collapsed). Each phrase is fired at a planted removal. The text that came before is embedded and
must be reported for exactly the phrases the change added; the wordings it retired are fired at
that old text and at the real text. The behaviour checks are fired at launchers with one fault
each (one that leaves standard input open, one that puts the sentinel first, one that accepts any
path), and the answer classifier at a naive one that passes whenever the sentinel is mentioned.
"""

import ast
import json
import os
import re
import runpy
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _REPO_ROOT / "plugins" / "orchestration" / "skills"
_ORCHESTRATE = _SKILLS / "orchestrate"
_SCRIPT = _ORCHESTRATE / "scripts" / "launch_session.py"
_SKILL = _ORCHESTRATE / "SKILL.md"
_TEMPLATE = _SKILLS / "initiative-planner" / "references" / "execution-plan-template.md"

_TIMEOUT_SECONDS = 60
_LEAK = "TEXT-THE-LAUNCHER-MUST-NOT-PASS-ON"
_BRIEF = ".specs/work/briefs/B1.md"
_AWKWARD_BRIEF = "it's here/B 2.md"
_RULES = "AGENTS.md"
_SENTINEL = "--zzz-sentinel"
_SEC = chr(0xA7)
_EM = chr(0x2014)
_DOT = chr(0xB7)

# What the stand-in does, by STAND_IN_MODE, once the sentinel is among its arguments. Commander,
# which the CLI parses with, says `error: ...` in lower case; the CLI's own messages say `Error: ...`.
_STAND_IN = """\
import json
import os
import sys

sentinel = "--zzz-sentinel"
stdin_text = sys.stdin.read()
with open(os.environ["STAND_IN_RECORD"], "w", encoding="utf-8") as handle:
    json.dump({"argv": sys.argv[1:], "stdin": stdin_text}, handle)
if sentinel not in sys.argv:
    sys.stdout.write("the session ran\\n")
    sys.exit(int(os.environ["STAND_IN_EXIT"]))
mode = os.environ["STAND_IN_MODE"]
if mode == "reject":
    sys.stderr.write("error: unknown option '" + sentinel + "'\\n")
elif mode == "blame":
    sys.stderr.write("error: unknown option '--effrot'\\n(Did you mean --effort?)\\n")
elif mode == "warn":
    sys.stderr.write("Warning: Unknown --effort value 'x' - ignoring it and using the default.\\n")
    sys.stderr.write("error: unknown option '" + sentinel + "'\\n")
elif mode == "bad-choice":
    sys.stderr.write("error: option '--permission-mode <mode>' argument 'x' is invalid.\\n")
else:
    sys.stderr.write("Error: Input must be provided either through stdin or as a prompt argument.\\n")
sys.exit(1)
"""


class Seen(NamedTuple):
    """What the stand-in recorded when it was started."""

    argv: list[str]
    stdin: str


class Outcome(NamedTuple):
    code: int
    out: str
    err: str
    seen: Seen | None  # None: the stand-in was never started


@dataclass(frozen=True)
class Kit:
    launcher: Path  # the script, copied out beside a folder whose name holds a space
    repo: Path  # the working directory, holding a brief and a host-rules file
    cli: str  # the `--cli` value that runs the stand-in
    record: Path  # where the stand-in writes what it saw


def _install(source: Path, root: Path) -> Path:
    target = root / "plugin cache" / "orchestrate" / "scripts" / "launch_session.py"
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    return target


def _make_kit(tmp_path: Path, script: Path) -> Kit:
    repo = tmp_path / "repo"
    for relative in (_BRIEF, _AWKWARD_BRIEF, _RULES):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("text\n", encoding="utf-8")
    stand_in = tmp_path / "stand_in.py"
    stand_in.write_text(_STAND_IN, encoding="utf-8")
    return Kit(
        launcher=_install(script, tmp_path),
        repo=repo,
        cli=shlex.join([sys.executable, str(stand_in)]),
        record=tmp_path / "record.json",
    )


@pytest.fixture
def kit(tmp_path: Path) -> Kit:
    return _make_kit(tmp_path, _SCRIPT)


def _seen(record: Path) -> Seen | None:
    if not record.is_file():
        return None
    data = cast("dict[str, Any]", json.loads(record.read_text(encoding="utf-8")))
    return Seen(
        [str(item) for item in cast("list[Any]", data["argv"])], str(data["stdin"])
    )


def _launch(
    kit: Kit,
    *args: str,
    mode: str = "reject",
    exit_code: int = 0,
    stdin: str = _LEAK,
    cli: str | None = None,
    with_cli: bool = True,
) -> Outcome:
    """Run the copied-out script in the repository folder. The parent offers `stdin` on a pipe it
    closes, so a launcher that leaves standard input open hands the text on instead of hanging."""
    extra = ["--cli", kit.cli if cli is None else cli] if with_cli else []
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "STAND_IN_RECORD": str(kit.record),
        "STAND_IN_MODE": mode,
        "STAND_IN_EXIT": str(exit_code),
    }
    done = subprocess.run(
        [sys.executable, "-B", "-I", str(kit.launcher), *args, *extra],
        cwd=kit.repo,
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_TIMEOUT_SECONDS,
        check=False,
    )
    return Outcome(done.returncode, done.stdout, done.stderr, _seen(kit.record))


def _cli_tokens(kit: Kit) -> list[str]:
    return shlex.split(kit.cli)


_ALL_OPTIONS = [
    "--model",
    "sonnet",
    "--effort",
    "high",
    "--permission-mode",
    "acceptEdits",
    "--rules-file",
    _RULES,
]
_ALL_FLAGS = [
    "--model",
    "sonnet",
    "--effort",
    "high",
    "--permission-mode",
    "acceptEdits",
    "--append-system-prompt-file",
    _RULES,
]


def _printed_arguments(kit: Kit, outcome: Outcome) -> list[str]:
    """The printed line as the shell reads it, less the CLI and the redirect of standard input."""
    lines = outcome.out.splitlines()
    assert len(lines) == 1, f"print wrote {len(lines)} lines: {outcome.out!r}"
    tokens = shlex.split(lines[0])
    cli = _cli_tokens(kit)
    assert tokens[: len(cli)] == cli, tokens
    assert tokens[-2:] == ["<", "/dev/null"], f"no redirect of standard input: {tokens}"
    return tokens[len(cli) : -2]


def test_the_behaviour_surface_is_stated_in_numbers(kit: Kit) -> None:
    assert (
        kit.launcher.is_file()
        and kit.launcher.parent.parent.parent.name == "plugin cache"
    )
    assert " " in str(kit.launcher), (
        "the copied-out script must sit in a folder whose name holds a space"
    )
    assert kit.launcher.read_bytes() == _SCRIPT.read_bytes(), (
        "the copy is not the shipped script"
    )
    assert (len(_REFUSED), len(_ABSOLUTE), len(_ANSWERS)) == (9, 3, 11)
    help_text = subprocess.run(
        [sys.executable, "-B", "-I", str(kit.launcher), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_TIMEOUT_SECONDS,
        check=False,
    ).stdout
    assert all(mode in help_text for mode in ("print", "run", "check")), help_text


# --- print: one exact command, nothing started -------------------------------------------------


@pytest.mark.parametrize(
    ("options", "flags"),
    [
        pytest.param([], [], id="brief-only"),
        pytest.param(_ALL_OPTIONS, _ALL_FLAGS, id="every-option"),
    ],
)
def test_print_writes_one_exact_command_and_starts_nothing(
    kit: Kit, options: list[str], flags: list[str]
) -> None:
    outcome = _launch(kit, "print", _BRIEF, *options)
    assert outcome.code == 0, outcome.err
    assert outcome.seen is None, "print started the CLI"
    arguments = _printed_arguments(kit, outcome)
    assert arguments[: 1 + len(flags)] == ["-p", *flags]
    assert len(arguments) == 2 + len(flags), arguments
    prompt = arguments[-1]
    assert prompt.startswith("Read ") and _BRIEF in prompt, prompt


def test_print_names_the_default_cli_without_a_path(kit: Kit) -> None:
    """Without `--cli` the command opens with the bare name, so it holds no per-machine path."""
    outcome = _launch(kit, "print", _BRIEF, with_cli=False)
    assert outcome.code == 0, outcome.err
    assert shlex.split(outcome.out)[:2] == ["claude", "-p"], outcome.out


def test_a_path_with_a_space_and_a_quote_is_one_shell_word(kit: Kit) -> None:
    outcome = _launch(kit, "print", _AWKWARD_BRIEF)
    assert outcome.code == 0, outcome.err
    arguments = _printed_arguments(kit, outcome)
    assert len(arguments) == 2, arguments
    assert _AWKWARD_BRIEF in arguments[1], arguments


# --- run: the printed arguments, standard input closed -----------------------------------------


def _assert_stdin_closed(outcome: Outcome) -> None:
    assert outcome.seen is not None, outcome.err
    assert outcome.seen.stdin == "", (
        f"the CLI was handed standard input: {outcome.seen.stdin!r}"
    )


def test_run_starts_the_cli_once_with_the_printed_arguments(kit: Kit) -> None:
    printed = _launch(kit, "print", _BRIEF, *_ALL_OPTIONS)
    ran = _launch(kit, "run", _BRIEF, *_ALL_OPTIONS)
    assert ran.code == 0, ran.err
    assert ran.seen is not None
    assert ran.seen.argv == _printed_arguments(kit, printed)
    assert "the session ran" in ran.out


def test_run_cuts_standard_input_off_the_cli(kit: Kit) -> None:
    _assert_stdin_closed(_launch(kit, "run", _BRIEF))


def test_run_reports_a_cli_that_failed_as_exit_1(kit: Kit) -> None:
    outcome = _launch(kit, "run", _BRIEF, exit_code=3)
    assert outcome.code == 1, (outcome.code, outcome.err)
    assert "3" in outcome.err, outcome.err


def test_run_says_so_when_the_cli_is_not_found(kit: Kit) -> None:
    outcome = _launch(kit, "run", _BRIEF, cli="no-such-cli-for-the-control")
    assert outcome.code == 2, (outcome.code, outcome.err)
    assert "not found" in outcome.err, outcome.err


# --- refusals: nothing is printed, nothing starts ----------------------------------------------

_REFUSED = [
    pytest.param("print", ["/abs/brief.md"], id="print-posix-absolute-brief"),
    pytest.param("run", ["/abs/brief.md"], id="run-posix-absolute-brief"),
    pytest.param("print", ["C:/work/brief.md"], id="print-drive-letter-brief"),
    pytest.param("print", ["c:brief.md"], id="print-drive-relative-brief"),
    pytest.param("print", ["\\\\server\\share\\brief.md"], id="print-unc-brief"),
    pytest.param("print", [".specs/work/briefs/missing.md"], id="print-missing-brief"),
    pytest.param(
        "run", [_BRIEF, "--rules-file", "/abs/AGENTS.md"], id="run-absolute-rules"
    ),
    pytest.param(
        "check", ["--rules-file", "missing-rules.md"], id="check-missing-rules"
    ),
    pytest.param("print", [], id="print-without-a-brief"),
]


def _assert_refused(outcome: Outcome) -> None:
    assert outcome.code == 2, (outcome.code, outcome.out, outcome.err)
    assert outcome.seen is None, "the CLI was started on a refused input"
    assert outcome.out == "", f"a refused input still printed: {outcome.out!r}"
    assert outcome.err.strip(), "a refusal that says nothing"


@pytest.mark.parametrize(("mode", "args"), _REFUSED)
def test_a_path_that_is_not_repo_relative_or_not_there_is_refused(
    kit: Kit, mode: str, args: list[str]
) -> None:
    _assert_refused(_launch(kit, mode, *args))


_ABSOLUTE = [
    pytest.param("print", False, id="print-brief"),
    pytest.param("run", False, id="run-brief"),
    pytest.param("check", True, id="check-rules-file"),
]


def _absolute_launch(kit: Kit, mode: str, as_rules_file: bool) -> Outcome:
    """The launcher given the ABSOLUTE spelling of a file that exists, so that only the shape of the
    path can refuse it: a path that is also missing would be refused for that, whatever its shape."""
    assert (kit.repo / _BRIEF).is_file() and (kit.repo / _RULES).is_file()
    target = (kit.repo / (_RULES if as_rules_file else _BRIEF)).as_posix()
    return _launch(
        kit, mode, *(["--rules-file", target] if as_rules_file else [target])
    )


@pytest.mark.parametrize(("mode", "as_rules_file"), _ABSOLUTE)
def test_an_absolute_path_to_a_file_that_exists_is_still_refused(
    kit: Kit, mode: str, as_rules_file: bool
) -> None:
    _assert_refused(_absolute_launch(kit, mode, as_rules_file))


def _refusal() -> Callable[[str], str | None]:
    return cast("Callable[[str], str | None]", runpy.run_path(str(_SCRIPT))["refusal"])


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/abs/brief.md", id="posix-absolute"),
        pytest.param("//server/share/brief.md", id="double-slash"),
        pytest.param("C:/work/brief.md", id="drive-letter"),
        pytest.param("c:brief.md", id="drive-relative"),
        pytest.param("\\rooted\\brief.md", id="backslash-rooted"),
        pytest.param("", id="empty"),
    ],
)
def test_the_refusal_names_a_reason_for_each_shape(path: str) -> None:
    assert _refusal()(path), f"{path!r} was not refused"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(".specs/work/briefs/B1.md", id="repo-relative"),
        pytest.param("brief.md", id="bare-name"),
        pytest.param("../up/brief.md", id="parent-relative"),
        pytest.param("dir with space/it's.md", id="space-and-quote"),
        pytest.param("docs/a:b.md", id="colon-inside-a-name"),
    ],
)
def test_the_refusal_leaves_a_repo_relative_path_alone(path: str) -> None:
    assert _refusal()(path) is None


# --- check: the sentinel, and what it can and cannot read --------------------------------------


def _assert_sentinel_last_and_no_prompt(outcome: Outcome) -> None:
    assert outcome.seen is not None, outcome.err
    argv = outcome.seen.argv
    assert argv == ["-p", *_ALL_FLAGS, _SENTINEL], argv


@pytest.mark.parametrize(
    ("mode", "code", "word"),
    [
        pytest.param("reject", 0, "PASS", id="sentinel-rejected"),
        pytest.param("blame", 1, "FAIL", id="another-flag-rejected"),
        pytest.param("warn", 1, "FAIL", id="a-value-the-cli-will-ignore"),
        pytest.param("bad-choice", 1, "FAIL", id="a-value-the-cli-refuses"),
        pytest.param("accept", 2, "CANNOT MEASURE", id="sentinel-accepted"),
    ],
)
def test_check_reads_the_answer_the_cli_gave(
    kit: Kit, mode: str, code: int, word: str
) -> None:
    outcome = _launch(kit, "check", *_ALL_OPTIONS, mode=mode)
    assert outcome.code == code, (outcome.code, outcome.out, outcome.err)
    assert word in outcome.out, outcome.out
    _assert_sentinel_last_and_no_prompt(outcome)
    _assert_stdin_closed(outcome)


def test_check_names_what_the_cli_rejected_or_warned_about(kit: Kit) -> None:
    blamed = _launch(kit, "check", *_ALL_OPTIONS, mode="blame")
    assert "--effrot" in blamed.out, blamed.out
    warned = _launch(kit, "check", *_ALL_OPTIONS, mode="warn")
    assert "Unknown --effort value" in warned.out, warned.out


def test_check_reads_cannot_measure_when_the_cli_is_not_found(kit: Kit) -> None:
    outcome = _launch(kit, "check", cli="no-such-cli-for-the-control")
    assert outcome.code == 2, (outcome.code, outcome.out, outcome.err)
    assert "CANNOT MEASURE" in outcome.out, outcome.out


def _classify() -> Callable[[str], tuple[int, str, str]]:
    return cast(
        "Callable[[str], tuple[int, str, str]]",
        runpy.run_path(str(_SCRIPT))["classify"],
    )


_ACCEPTED = (
    "Error: Input must be provided either through stdin or as a prompt argument.\n"
)
_REJECTED = f"error: unknown option '{_SENTINEL}'\n"

# (name, the CLI's answer, the exit code the check gives, the label it reads)
_ANSWERS: list[tuple[str, str, int, str]] = [
    ("the sentinel rejected", _REJECTED, 0, "PASS"),
    (
        "the sentinel rejected, CRLF line ends",
        _REJECTED.replace("\n", "\r\n"),
        0,
        "PASS",
    ),
    (
        "another flag rejected, with a suggestion",
        "error: unknown option '--effrot'\n(Did you mean --effort?)\n",
        1,
        "FAIL",
    ),
    (
        "another flag first, the sentinel second",
        "error: unknown option '--effrot'\n" + _REJECTED,
        1,
        "FAIL",
    ),
    (
        "a warning before the sentinel error",
        "Warning: Unknown --effort value 'x' - ignoring it.\n" + _REJECTED,
        1,
        "FAIL",
    ),
    (
        "an option argument the CLI refuses",
        "error: option '--permission-mode <mode>' argument 'x' is invalid.\n",
        1,
        "FAIL",
    ),
    ("the sentinel accepted", _ACCEPTED, 2, "CANNOT MEASURE"),
    ("no answer at all", "", 2, "CANNOT MEASURE"),
    (
        "the sentinel named in a warning that says it was ignored",
        "Warning: unknown option '--zzz-sentinel' ignored\n",
        2,
        "CANNOT MEASURE",
    ),
    (
        "a longer flag that merely starts with the sentinel",
        "error: unknown option '--zzz-sentinel-2'\n",
        1,
        "FAIL",
    ),
    (
        "an answer in the CLI's own words",
        "Error: something else broke\n",
        2,
        "CANNOT MEASURE",
    ),
]


@pytest.mark.parametrize(
    ("name", "answer", "code", "label"),
    [pytest.param(*row, id=row[0]) for row in _ANSWERS],
)
def test_the_check_classifies_each_planted_answer(
    name: str, answer: str, code: int, label: str
) -> None:
    got_code, got_label, detail = _classify()(answer)
    assert (got_code, got_label) == (code, label), (name, detail)
    assert detail.strip(), f"{name}: a verdict with no detail"


def _naive(answer: str) -> int:
    """The classifier the real one must not be: a pass whenever the sentinel is mentioned."""
    return 0 if _SENTINEL in answer else 1


def test_the_planted_answers_tell_a_naive_classifier_from_the_real_one() -> None:
    """Fired at a known-positive: the naive shape passes four answers the real one does not."""
    disagree = [
        name
        for name, answer, code, _ in _ANSWERS
        if _naive(answer) != code and _naive(answer) == 0
    ]
    assert disagree == [
        "another flag first, the sentinel second",
        "a warning before the sentinel error",
        "the sentinel named in a warning that says it was ignored",
        "a longer flag that merely starts with the sentinel",
    ]


# --- faults: the behaviour checks must see a launcher that has one --------------------------------


def _faulty_kit(tmp_path: Path, anchor: str, replacement: str) -> Kit:
    source = _SCRIPT.read_text(encoding="utf-8")
    assert source.count(anchor) >= 1, f"the script no longer holds {anchor!r}"
    copy = tmp_path / "faulty" / "launch_session.py"
    copy.parent.mkdir()
    copy.write_text(source.replace(anchor, replacement), encoding="utf-8")
    return _make_kit(tmp_path, copy)


def test_the_stdin_check_fails_on_a_launcher_that_leaves_stdin_open(
    tmp_path: Path,
) -> None:
    faulty = _faulty_kit(tmp_path, "stdin=subprocess.DEVNULL", "stdin=None")
    with pytest.raises(AssertionError, match="was handed standard input"):
        _assert_stdin_closed(_launch(faulty, "run", _BRIEF))
    with pytest.raises(AssertionError, match="was handed standard input"):
        _assert_stdin_closed(_launch(faulty, "check", *_ALL_OPTIONS))


def test_the_refusal_check_fails_on_a_launcher_that_accepts_any_path(
    tmp_path: Path,
) -> None:
    faulty = _faulty_kit(
        tmp_path,
        "    if not path.strip():",
        "    return None\n    if not path.strip():",
    )
    accepted = _absolute_launch(faulty, "print", False)
    assert accepted.code == 0, (
        "the fault was not injected: the absolute path was refused"
    )
    with pytest.raises(AssertionError):
        _assert_refused(accepted)


def test_the_sentinel_check_fails_on_a_launcher_that_puts_it_first(
    tmp_path: Path,
) -> None:
    faulty = _faulty_kit(
        tmp_path, "return [*flags, SENTINEL]", "return [SENTINEL, *flags]"
    )
    outcome = _launch(faulty, "check", *_ALL_OPTIONS)
    with pytest.raises(AssertionError):
        _assert_sentinel_last_and_no_prompt(outcome)


# --- the script is stdlib only and never starts a shell -------------------------------------------

# Standard-library modules that reach off the machine; anything outside the library is found by name.
_NETWORK = frozenset(
    {"socket", "urllib", "http", "ftplib", "smtplib", "xmlrpc", "webbrowser"}
)
_DYNAMIC = frozenset({"eval", "exec", "compile", "__import__"})


def _scan(source: str) -> list[str]:
    """What a script must not do: import beyond the standard library, start a shell, run data as code."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots = [node.module.split(".")[0]]
        else:
            roots = []
        found.extend(
            f"imports {root}" for root in roots if root not in sys.stdlib_module_names
        )
        found.extend(f"imports {root}" for root in roots if root in _NETWORK)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _DYNAMIC:
                found.append(f"calls {func.id}")
            if isinstance(func, ast.Attribute) and ast.unparse(func) in {
                "os.system",
                "os.popen",
            }:
                found.append(f"calls {ast.unparse(func)}")
            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    found.append("shell=True")
    return sorted(set(found))


def test_the_script_imports_only_the_standard_library_and_starts_no_shell() -> None:
    source = _SCRIPT.read_text(encoding="utf-8")
    assert ast.parse(source).body, (
        "the script parsed to nothing, so the scan saw nothing"
    )
    assert _scan(source) == []


def test_the_source_scan_sees_planted_shapes_and_not_near_misses() -> None:
    planted = (
        "import requests\nimport socket\nimport subprocess\n"
        "subprocess.run(x, shell=True)\nos.system('x')\neval('1')\nexec('1')\n"
    )
    assert _scan(planted) == [
        "calls eval",
        "calls exec",
        "calls os.system",
        "imports requests",
        "imports socket",
        "shell=True",
    ]
    near_miss = (
        "import os\nimport shlex\nimport subprocess\n# import socket\n"
        "text = 'shell=True and eval(1)'\nsubprocess.run(x, shell=False)\n"
        "os_system = os.path.join(a, b)\nevaluate(1)\n"
    )
    assert _scan(near_miss) == []


def test_the_help_says_what_each_mode_does_and_what_exit_two_means() -> None:
    done = subprocess.run(
        [sys.executable, "-B", "-I", str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_TIMEOUT_SECONDS,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    folded = " ".join(done.stdout.split())
    for sentence in (
        "print shows the exact command and starts nothing",
        "run starts the session only when this mode is named",
        "check sends no prompt and costs nothing",
        "CANNOT MEASURE is exit 2, never a pass",
    ):
        assert sentence in folded, f"--help does not say {sentence!r}"


# --- the wording: section 2a, Default 1 and the plan template ------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s")
_SKILL_SCOPE = "orchestrate section 2a"
_STDIN_SCOPE = "2a stdin bullet"
_EFFORT_SCOPE = "2a effort bullet"
_DEFAULT_SCOPE = "orchestrate Default 1"
_PASTED_SCOPE = "template pasted bullet"
_HEADLESS_SCOPE = "template headless bullet"

# (scope, claim, the phrases that must all be in the scope; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        _SKILL_SCOPE,
        "section 2a names the script and where its modes are listed",
        ("are applied by `${claude_skill_dir}/scripts/launch_session.py` (`--help`)",),
    ),
    (
        _STDIN_SCOPE,
        "the stdin bullet keeps both facts it had",
        ("always append `< /dev/null`", "stalls 3 s", "no stdin data received in 3s"),
    ),
    (
        _EFFORT_SCOPE,
        "the effort bullet says an unknown value only warns",
        ("an unknown value only warns and the default effort runs",),
    ),
    (
        _DEFAULT_SCOPE,
        "a pasted row in the plan is the operator's request made at plan time",
        (
            "a `pasted` row in the plan's `dispatch` column is that request made at plan "
            "time: write it, no reason needed.",
        ),
    ),
    (
        _PASTED_SCOPE,
        "pasted is an equal choice made at plan time",
        ("`pasted` is an equal choice, made here at plan time",),
    ),
    (
        _PASTED_SCOPE,
        "a row may say pasted with no reason when the operator drives the session",
        (
            "a row may say `pasted` with no reason when the operator will drive that session",
        ),
    ),
    (
        _PASTED_SCOPE,
        "any other pasted row still gives its reason",
        ("any other `pasted` row gives its reason in the row's `blocked by` cell",),
    ),
    (
        _HEADLESS_SCOPE,
        "headless rows are launched with the orchestrate script",
        (
            "`headless` is launched with `orchestrate`'s `scripts/launch_session.py` "
            f"({_SEC}2a)",
        ),
    ),
    (
        _HEADLESS_SCOPE,
        "a mechanism invented mid-initiative is still written into the skill first",
        (
            "if you invent a dispatch mechanism mid-initiative, write it into that skill "
            "**before** the orchestrator handoff or it dies there",
        ),
    ),
)
# The phrases the old text already carried: they must survive, and the old text must show it.
_KEPT = frozenset(
    {
        "always append `< /dev/null`",
        "no stdin data received in 3s",
        "if you invent a dispatch mechanism mid-initiative, write it into that skill "
        "**before** the orchestrator handoff or it dies there",
    }
)

# The wordings the change retired: absent from the real text, present in the old text.
_RETIRED: tuple[tuple[str, str], ...] = (
    (_EFFORT_SCOPE, "with a validated enum"),
    (_PASTED_SCOPE, "`pasted` is the **fallback**, not the default"),
    (_HEADLESS_SCOPE, "`headless` requires the launcher in `orchestrate`"),
)

_OLD: dict[str, str] = {
    _SKILL_SCOPE: (
        "Whether fan-out is *economic* is a plan-time question (`initiative-planner` step 5.1 and its\n"
        "`../initiative-planner/references/dispatch-economics.md`). These are the\n"
        "run-time facts, all verified on CLI **2.1.224**, 2026-08-15:\n"
    ),
    _STDIN_SCOPE: (
        "- **Always append `< /dev/null`.** Without it every launch prints "
        '*"no stdin data received in 3s"*\n'
        f"  and stalls three seconds {_EM} thirty wasted seconds across a ten-session wave.\n"
    ),
    _EFFORT_SCOPE: (
        "- **`--effort` is a real flag** with a validated enum "
        f"(`low{_DOT}medium{_DOT}high{_DOT}xhigh{_DOT}max`). The `Agent`\n"
        "  tool has no effort parameter, so `/effort` inside a prompt string remains the fallback for native\n"
        "  subagents only.\n"
    ),
    _DEFAULT_SCOPE: (
        "instead of in this file. A pasteable prompt the operator asks for by name is written, not argued:\n"
        "a request by name measures what the launch costs, it is not a lapse to correct. Unasked, if you\n"
        f'are about to write "paste this into a new session", first say why a {_SEC}2a launch will not do.\n'
    ),
    _PASTED_SCOPE: (
        f"- `pasted` is the **fallback**, not the default {_EM} justify each one in the row's `Blocked by`\n"
        '  cell ("needs the operator\'s own approval loop"), because an unjustified `pasted` row is the\n'
        "  43% reproducing itself.\n"
    ),
    _HEADLESS_SCOPE: (
        f"- `headless` requires the launcher in `orchestrate` {_SEC}2a; if you invent a dispatch mechanism\n"
        "  mid-initiative, write it into that skill **before** the orchestrator handoff or it dies there.\n"
    ),
}
_LINE_CAP = 499


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _words(text: str) -> str:
    """Whitespace folded and lower-cased: lines wrap, and the claims are about words."""
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _section(text: str, heading: str) -> str:
    """The one heading line that starts with `heading` and the lines under it, up to the next
    heading of the same or a higher level. Fails loudly when none, or more than one, starts with it."""
    lines = text.split("\n")
    starts = [
        i
        for i, line in enumerate(lines)
        if _HEADING.match(line) and line.startswith(heading)
    ]
    assert len(starts) == 1, f"{heading!r} starts {len(starts)} headings, not 1"
    opening = _HEADING.match(lines[starts[0]])
    assert opening is not None
    body = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        found = _HEADING.match(line)
        if found is not None and len(found[1]) <= len(opening[1]):
            break
        body.append(line)
    return "\n".join(body)


def _paragraph(section: str, lead: str) -> str:
    """The one paragraph of `section` that starts with `lead`. Fails loudly otherwise."""
    found = [part for part in section.split("\n\n") if part.startswith(lead)]
    assert len(found) == 1, f"{lead!r} starts {len(found)} paragraphs, not 1"
    return found[0]


def _bullet(text: str, lead: str) -> str:
    """The one bullet of `text` that starts a line with `lead`, up to the next bullet or blank line."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith(lead)]
    assert len(starts) == 1, f"{lead!r} starts {len(starts)} lines, not 1"
    body = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if not line.strip() or line.startswith("- "):
            break
        body.append(line)
    return "\n".join(body)


def _scopes(skill: str, template: str) -> dict[str, str]:
    """The folded text of each scope a claim is judged in."""
    section_2a = _section(skill, "### 2a.")
    dispatch = _section(skill, "### 2. Dispatch")
    return {
        _SKILL_SCOPE: _words(section_2a),
        _STDIN_SCOPE: _words(_bullet(section_2a, "- **Always append")),
        _EFFORT_SCOPE: _words(_bullet(section_2a, "- **`--effort` is a real flag**")),
        _DEFAULT_SCOPE: _words(_paragraph(dispatch, "**Default 1")),
        _PASTED_SCOPE: _words(_bullet(template, "- `pasted` is")),
        _HEADLESS_SCOPE: _words(_bullet(template, "- `headless` ")),
    }


def _real_scopes() -> dict[str, str]:
    return _scopes(_read(_SKILL), _read(_TEMPLATE))


def test_the_wording_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (9, 11)
    assert len({scope for scope, _, _ in _ROWS}) == 6
    assert set(_real_scopes()) == {scope for scope, _, _ in _ROWS} == set(_OLD)
    assert all(_real_scopes().values())
    assert all(path.is_file() for path in (_SKILL, _TEMPLATE))
    assert len(_KEPT) == 3 and len(_RETIRED) == 3


@pytest.mark.parametrize(
    ("scope", "claim", "phrases"), _ROWS, ids=[row[1] for row in _ROWS]
)
def test_the_scope_states_the_claim(
    scope: str, claim: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_real_scopes()[scope], phrases)
    assert not missing, f"the {scope} does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real text in turn is the one gap reported, and an
    empty text lacks every phrase of a row. A phrase the check cannot see go would let the scope lose
    its claim and stay green."""
    scopes = _real_scopes()
    for scope, claim, phrases in _ROWS:
        text = scopes[scope]
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_text_that_came_before_is_reported_for_exactly_the_added_phrases() -> None:
    """The old wording is the known positive: each embedded old scope lacks every phrase the change
    added and holds every phrase it kept."""
    old = {scope: _words(text) for scope, text in _OLD.items()}
    for scope, claim, phrases in _ROWS:
        reported = _missing(old[scope], phrases)
        assert reported == [p for p in phrases if p not in _KEPT], (claim, reported)
    for kept in _KEPT:
        assert any(kept in text for text in old.values()), (
            f"the old text lacks {kept!r}"
        )


def test_the_retired_wordings_are_gone_and_the_scan_sees_them_in_the_old_text() -> None:
    real = _real_scopes()
    old = {scope: _words(text) for scope, text in _OLD.items()}
    for scope, wording in _RETIRED:
        assert wording.lower() in old[scope], f"the old {scope} never held {wording!r}"
        assert wording.lower() not in real[scope], f"the {scope} still says {wording!r}"


def test_the_pointer_names_a_script_that_ships_and_the_script_is_not_empty() -> None:
    section = _words(_section(_read(_SKILL), "### 2a."))
    assert "scripts/launch_session.py" in section
    assert _SCRIPT.is_file(), (
        f"section 2a points at a file that does not ship: {_SCRIPT}"
    )
    assert _SCRIPT.read_text(encoding="utf-8").strip()


def _lines_over_the_cap(text: str) -> int:
    """How many lines `wc -l` counts above the cap; zero when the file is within it."""
    return max(0, text.count("\n") - _LINE_CAP)


def test_skill_md_stays_within_its_line_cap() -> None:
    """`wc -l` of a SKILL.md is at most 499. Fired at planted texts of 499 and 500 lines."""
    assert _lines_over_the_cap(_read(_SKILL)) == 0, "SKILL.md is over the cap"
    assert _lines_over_the_cap("x\n" * _LINE_CAP) == 0
    assert _lines_over_the_cap("x\n" * (_LINE_CAP + 1)) == 1


def test_a_missing_section_paragraph_or_bullet_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="starts 0 headings"):
        _section("## Another\ntext\n", "### 2a.")
    with pytest.raises(AssertionError, match="starts 2 headings"):
        _section("### 2a. one\na\n### 2a. two\nb\n", "### 2a.")
    with pytest.raises(AssertionError, match="starts 0 paragraphs"):
        _paragraph("a paragraph\n\nanother\n", "**Default 1")
    with pytest.raises(AssertionError, match="starts 2 paragraphs"):
        _paragraph("**Default 1 one\n\n**Default 1 two\n", "**Default 1")
    with pytest.raises(AssertionError, match="starts 0 lines"):
        _bullet("- Another bullet\n", "- `pasted` is")
    with pytest.raises(AssertionError, match="starts 2 lines"):
        _bullet("- `pasted` is one\n- `pasted` is two\n", "- `pasted` is")


def test_a_section_paragraph_and_bullet_are_cut_where_they_end() -> None:
    text = "\n".join(
        [
            "### 2a. Launch",
            "",
            "**Default 1 one**",
            "continued",
            "",
            "- first bullet",
            "  wrapped",
            "- `pasted` is two",
            "  wrapped too",
            "- last bullet",
            "#### Deeper",
            "kept",
            "### 2b. Peer",
            "left out",
            "",
        ]
    )
    section = _section(text, "### 2a.")
    assert "kept" in section and "left out" not in section
    assert _paragraph(section, "**Default 1") == "**Default 1 one**\ncontinued"
    assert _bullet(section, "- `pasted` is") == "- `pasted` is two\n  wrapped too"
