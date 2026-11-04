"""The context meter prints three numbers for one transcript, and says so when it cannot measure.

`orchestrate/scripts/context_meter.py` reads ONE session transcript (a JSON-lines file) and prints the
context size of the session's own thread: the input, cache-creation and cache-read tokens of the last
main-thread assistant record whose usage is above zero, that size as a percent of a window the caller
states, and the number of distinct tool calls. It is a meter and not a usage guard: it never stops or
advises, writes nothing and starts no process. A transcript it cannot read (a missing file, an empty
one, a line that is not a JSON object, no usage record, a usage block with absent fields) prints
`NOT MEASURED: <reason>` and exits 2, because no reading is not a zero reading.

THE SURFACE, in numbers the tests assert: 1 script, run as a subprocess in the form the brief template
names (the command line is what a worker meets); 3 reported fields; 10 transcripts it cannot measure;
and 1 bullet of the brief template, directly under its Budget line. Every transcript is written by the
test into a temporary folder. The two checks that read text (the template bullet and the script's own
source) are each fired at a planted fixture that holds the old shape and at near-misses, so a pass
means the check could see.
"""

import ast
import json
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import NamedTuple

import pytest

from lemmi_ai_kit import checks

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATE = _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate"
_SCRIPT = _ORCHESTRATE / "scripts" / "context_meter.py"
_TEMPLATE = _ORCHESTRATE / "references" / "brief-template.md"

_REPORTED = ("context_tokens", "percent_of_window", "tool_calls")
_NOT_MEASURED = "NOT MEASURED:"
# Words that sit in every record's text block. The meter reads text and must never print any of it.
_MARKER = "transcript-words-the-meter-never-prints"


class _Run(NamedTuple):
    code: int
    out: str
    err: str


@pytest.fixture(autouse=True)
def _scratch_working_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every script run starts in the test's own folder, so a script that wrote to its working
    folder could never write into the repository."""
    monkeypatch.chdir(tmp_path)


def _run(*args: str) -> _Run:
    done = subprocess.run(
        [sys.executable, "-B", "-I", str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    return _Run(done.returncode, done.stdout, done.stderr)


def _usage(fresh: int, created: int, read: int, written: int = 7) -> dict[str, object]:
    return {
        "input_tokens": fresh,
        "cache_creation_input_tokens": created,
        "cache_read_input_tokens": read,
        "output_tokens": written,
    }


def _assistant(
    usage: dict[str, object] | None,
    *,
    tools: tuple[str, ...] = (),
    sidechain: bool | None = False,
) -> dict[str, object]:
    """One assistant record; `sidechain=None` leaves the flag out, as a record of another type does."""
    blocks: list[dict[str, object]] = [{"type": "text", "text": _MARKER}]
    blocks.extend(
        {"type": "tool_use", "id": ident, "name": "Read", "input": {}}
        for ident in tools
    )
    message: dict[str, object] = {"role": "assistant", "content": blocks}
    if usage is not None:
        message["usage"] = usage
    record: dict[str, object] = {"type": "assistant", "message": message}
    if sidechain is not None:
        record["isSidechain"] = sidechain
    return record


def _user(text: str = "hello") -> dict[str, object]:
    return {
        "type": "user",
        "isSidechain": False,
        "message": {"role": "user", "content": text},
    }


def _write(folder: Path, records: Iterable[dict[str, object] | str]) -> Path:
    """One line per entry: a dict as JSON, a str as it is, so a test can plant a bad line."""
    lines = [r if isinstance(r, str) else json.dumps(r) for r in records]
    path = folder / "session.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _fields(out: str) -> dict[str, str]:
    """The `name: value` lines of a run, by name."""
    pairs = [line.split(": ", 1) for line in out.splitlines() if ": " in line]
    return {pair[0]: pair[1] for pair in pairs}


def _measured(path: Path, *args: str) -> dict[str, str]:
    """The three reported fields of a run that must have measured."""
    run = _run(str(path), *args)
    assert run.code == 0, f"exit {run.code}; stdout {run.out!r}; stderr {run.err!r}"
    fields = _fields(run.out)
    absent = [name for name in _REPORTED if name not in fields]
    assert not absent, f"no {absent} line in {run.out!r}"
    return fields


# --- what it measures -------------------------------------------------------------------------


def test_the_last_main_thread_usage_is_the_context(tmp_path: Path) -> None:
    """Not the first, not the largest, not a sum, and the output tokens are not part of it."""
    path = _write(
        tmp_path,
        [
            _user(),
            _assistant(_usage(100, 200, 300)),
            _assistant(_usage(1_000, 2_000, 3_000)),
            _user("again"),
            _assistant(_usage(10, 20, 30, written=999)),
        ],
    )
    assert _measured(path)["context_tokens"] == "60"


def test_a_later_sidechain_record_is_not_the_session(tmp_path: Path) -> None:
    """A helper's later and larger prompt is not the session's context, and its calls are not
    the session's calls: red if the skip is removed."""
    path = _write(
        tmp_path,
        [
            _assistant(_usage(100, 0, 0), tools=("toolu_main",)),
            _assistant(
                _usage(9_000, 9_000, 9_000), tools=("toolu_helper",), sidechain=True
            ),
        ],
    )
    fields = _measured(path)
    assert fields["context_tokens"] == "100"
    assert fields["tool_calls"] == "1"


def test_a_record_without_the_flag_is_the_main_thread(tmp_path: Path) -> None:
    path = _write(
        tmp_path, [_assistant(_usage(7, 0, 0), tools=("toolu_a",), sidechain=None)]
    )
    fields = _measured(path)
    assert (fields["context_tokens"], fields["tool_calls"]) == ("7", "1")


def test_a_replayed_tool_use_id_counts_once(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _assistant(_usage(1, 0, 0), tools=("toolu_a", "toolu_b")),
            _user(),
            _assistant(_usage(2, 0, 0), tools=("toolu_a",)),
        ],
    )
    assert _measured(path)["tool_calls"] == "2"


def test_a_zero_usage_record_does_not_hide_the_last_real_one(tmp_path: Path) -> None:
    path = _write(
        tmp_path, [_assistant(_usage(40, 50, 60)), _assistant(_usage(0, 0, 0, 0))]
    )
    assert _measured(path)["context_tokens"] == "150"


def test_a_blank_line_is_not_a_malformed_line(tmp_path: Path) -> None:
    """Near-miss for the malformed-line rule: a blank line holds no record and is not one."""
    path = _write(tmp_path, ["", _assistant(_usage(1, 2, 3)), "   ", ""])
    assert _measured(path)["context_tokens"] == "6"


# --- the window ---------------------------------------------------------------------------------


def test_the_percent_needs_a_stated_window(tmp_path: Path) -> None:
    path = _write(tmp_path, [_assistant(_usage(100_000, 50_000, 100_000))])
    without = _measured(path)
    assert without["context_tokens"] == "250000"
    assert without["percent_of_window"] == "NOT GIVEN"
    stated = _measured(path, "--window", "1000000")
    assert stated["context_tokens"] == "250000"
    assert stated["percent_of_window"] == "25.0"


@pytest.mark.parametrize("window", ["0", "-5", "many"])
def test_a_window_that_is_not_a_positive_number_is_refused(
    tmp_path: Path, window: str
) -> None:
    path = _write(tmp_path, [_assistant(_usage(1, 2, 3))])
    assert _measured(path)["context_tokens"] == "6"
    run = _run(str(path), "--window", window)
    assert run.code == 2, f"exit {run.code}; stdout {run.out!r}"
    assert "--window" in run.err, run.err
    assert "context_tokens" not in run.out


# --- what it says about itself and prints --------------------------------------------------------


def test_the_first_line_says_it_is_a_meter_and_not_a_usage_guard(
    tmp_path: Path,
) -> None:
    run = _run(str(_write(tmp_path, [_assistant(_usage(1, 1, 1))])))
    lines = run.out.splitlines()
    assert run.code == 0 and lines, f"exit {run.code}; stdout {run.out!r}"
    assert "meter" in lines[0].lower()
    assert "not a usage guard" in lines[0].lower()


def test_a_measured_run_prints_no_transcript_text(tmp_path: Path) -> None:
    path = _write(tmp_path, [_assistant(_usage(3, 3, 3), tools=("toolu_a",))])
    fields = _measured(path)
    assert fields["context_tokens"] == "9"
    run = _run(str(path))
    assert _MARKER not in run.out
    assert _MARKER not in run.err


def _snapshot(folder: Path) -> dict[str, tuple[int, int]]:
    """Every path under `folder` with its size and modification time."""
    return {
        str(p.relative_to(folder)): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(folder.rglob("*"))
    }


def test_the_run_writes_nothing(tmp_path: Path) -> None:
    """It measured (so a stub that prints nothing fails here), and neither the transcript nor
    the folder it ran in changed; the same when it could not measure."""
    path = _write(tmp_path, [_assistant(_usage(3, 3, 3))])
    before, content = _snapshot(tmp_path), path.read_bytes()
    run = _run(str(path))
    assert run.code == 0 and "context_tokens" in run.out, run
    assert _snapshot(tmp_path) == before
    assert path.read_bytes() == content
    refused = _run(str(tmp_path / "no-such-file.jsonl"))
    assert refused.code == 2 and _NOT_MEASURED in refused.out, refused
    assert _snapshot(tmp_path) == before


def test_the_write_check_sees_a_planted_write(tmp_path: Path) -> None:
    """Known-positive for `_snapshot`: a stray file and an appended byte are each a difference."""
    path = _write(tmp_path, [_assistant(_usage(3, 3, 3))])
    before = _snapshot(tmp_path)
    (tmp_path / "stray.txt").write_text("x", encoding="utf-8")
    assert _snapshot(tmp_path) != before
    (tmp_path / "stray.txt").unlink()
    assert _snapshot(tmp_path) == before
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    assert _snapshot(tmp_path) != before


# --- what it cannot measure ---------------------------------------------------------------------


def _missing(folder: Path) -> Path:
    return folder / "no-such-transcript.jsonl"


def _empty(folder: Path) -> Path:
    path = folder / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    return path


def _only_a_bad_line(folder: Path) -> Path:
    return _write(folder, [f"{_MARKER} is not json"])


def _good_records_around_a_bad_line(folder: Path) -> Path:
    return _write(
        folder,
        [
            _user(),
            _assistant(_usage(1, 2, 3)),
            f"{_MARKER} is not json",
            _assistant(_usage(4, 5, 6)),
        ],
    )


def _no_assistant_record(folder: Path) -> Path:
    return _write(folder, [_user(), _user("more")])


def _only_sidechain_records(folder: Path) -> Path:
    return _write(folder, [_assistant(_usage(5, 5, 5), sidechain=True)])


def _empty_usage_block(folder: Path) -> Path:
    return _write(folder, [_assistant(_usage(1, 2, 3)), _assistant({})])


def _usage_with_absent_fields(folder: Path) -> Path:
    return _write(folder, [_assistant({"input_tokens": 5, "output_tokens": 1})])


def _usage_with_a_non_integer_field(folder: Path) -> Path:
    usage = _usage(0, 0, 0)
    usage["input_tokens"] = "5"
    return _write(folder, [_assistant(usage)])


def _only_zero_usage(folder: Path) -> Path:
    return _write(folder, [_assistant(_usage(0, 0, 0, 0))])


_UNMEASURABLE = (
    pytest.param(_missing, id="missing-file"),
    pytest.param(_empty, id="empty-file"),
    pytest.param(_only_a_bad_line, id="one-malformed-line"),
    pytest.param(
        _good_records_around_a_bad_line, id="good-records-around-a-malformed-line"
    ),
    pytest.param(_no_assistant_record, id="no-assistant-record"),
    pytest.param(_only_sidechain_records, id="only-sidechain-records"),
    pytest.param(_usage_with_absent_fields, id="usage-with-absent-fields"),
    pytest.param(_empty_usage_block, id="empty-usage-block"),
    pytest.param(_usage_with_a_non_integer_field, id="usage-with-a-non-integer-field"),
    pytest.param(_only_zero_usage, id="only-zero-usage"),
)


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_REPORTED) == 3
    assert len(_UNMEASURABLE) == 10
    assert _SCRIPT.is_file(), _SCRIPT
    assert _TEMPLATE.is_file(), _TEMPLATE
    assert len(checks.PATH_PATTERNS) >= 3, "the audit's own path shapes are not there"


@pytest.mark.parametrize("writer", _UNMEASURABLE)
def test_a_transcript_that_cannot_be_measured_says_so(
    tmp_path: Path, writer: Callable[[Path], Path]
) -> None:
    """Exit 2 and a NOT MEASURED line, and no reading beside it: never zero tokens, never a pass,
    and never a word of the transcript."""
    run = _run(str(writer(tmp_path)))
    assert run.code == 2, f"exit {run.code}; stdout {run.out!r}; stderr {run.err!r}"
    assert any(line.startswith(_NOT_MEASURED) for line in run.out.splitlines()), run.out
    printed = [name for name in _REPORTED if name in _fields(run.out)]
    assert not printed, f"a reading was printed beside NOT MEASURED: {printed}"
    assert _MARKER not in run.out
    assert _MARKER not in run.err


def test_a_malformed_line_is_named_by_number_and_never_echoed(tmp_path: Path) -> None:
    run = _run(str(_good_records_around_a_bad_line(tmp_path)))
    assert run.code == 2
    assert "line 3" in run.out, run.out
    assert _MARKER not in run.out


# --- the script's own source --------------------------------------------------------------------

_ALLOWED_IMPORTS = frozenset(
    {"argparse", "json", "sys", "collections", "pathlib", "typing"}
)


def _shell_true_lines(source: str) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "shell"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
    ]


def _import_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _path_shapes(source: str) -> list[int]:
    """The lines holding a machine-specific path shape, by the audit's own patterns."""
    return [
        number
        for number, line in enumerate(source.splitlines(), 1)
        if any(pattern.search(line) for pattern in checks.PATH_PATTERNS)
    ]


def test_the_source_checks_see_what_they_are_for() -> None:
    """Known-positive and near-miss for the three scans below."""
    assert _shell_true_lines(
        "import subprocess\nsubprocess.run('x', shell=True)\n"
    ) == [2]
    assert _shell_true_lines("run(['x'], shell=False)  # shell=True is banned\n") == []
    assert _import_roots("import os\nfrom subprocess import run\n") == {
        "os",
        "subprocess",
    }
    assert (
        not _import_roots("import json\nfrom pathlib import Path\n") - _ALLOWED_IMPORTS
    )
    drive = "C" + ":" + chr(92) + "work"
    home = "/" + "Users" + "/someone"
    assert _path_shapes(f"path = {drive!r}\n") == [1]
    assert _path_shapes(f"path = {home!r}\n") == [1]
    assert _path_shapes("path = args.transcript\nshare = used / window\n") == []


def test_the_script_starts_no_process_and_names_no_path() -> None:
    source = _SCRIPT.read_text(encoding="utf-8")
    assert all(name in source for name in _REPORTED), "this is not the meter's source"
    assert _shell_true_lines(source) == []
    stray = _import_roots(source) - _ALLOWED_IMPORTS
    assert not stray, f"imports beyond the standard text-reading set: {sorted(stray)}"
    assert _path_shapes(source) == []


def test_the_docstring_says_it_never_stops_or_advises() -> None:
    docstring = ast.get_docstring(ast.parse(_SCRIPT.read_text(encoding="utf-8"))) or ""
    words = " ".join(docstring.split()).lower()
    assert "not a usage guard" in words
    assert "never stops or advises" in words


# --- the brief template: one Stop line bullet, directly under the Budget line -------------------

_STOP_LINE = "- Stop line:"
_STOP_LINE_PHRASES = (
    "stop line:",
    "the command that measures it",
    "${claude_skill_dir}/scripts/context_meter.py",
    "only reads",
    "never stops or advises",
)
_UNDER_BUDGET = "the bullet directly under '- Budget:' is not '- Stop line:'"


def _template() -> str:
    return _TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n")


def _skeleton(text: str) -> list[str]:
    """The lines between the first pair of code fences, the brief an orchestrator copies.
    Empty when there is none, so a check on it fails loudly."""
    inside: list[str] = []
    opened = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if opened:
                return inside
            opened = True
        elif opened:
            inside.append(line)
    return []


def _bullet_at(lines: list[str], start: int) -> list[str]:
    """The bullet that opens at `start`: its first line and the wrapped lines under it, up to the
    next bullet, heading or blank line."""
    end = start + 1
    while (
        end < len(lines)
        and lines[end].strip()
        and not lines[end].startswith(("- ", "#"))
    ):
        end += 1
    return lines[start:end]


def _index_of(lines: list[str], label: str) -> int | None:
    return next((i for i, line in enumerate(lines) if line.startswith(label)), None)


def _stop_line_gaps(text: str) -> list[str]:
    """What the skeleton lacks, one entry per gap; empty when the Stop line bullet is there."""
    lines = _skeleton(text)
    budget = _index_of(lines, "- Budget:")
    if budget is None:
        return ["the skeleton has no '- Budget:' bullet"]
    below = budget + len(_bullet_at(lines, budget))
    if below >= len(lines) or not lines[below].startswith(_STOP_LINE):
        return [_UNDER_BUDGET]
    bullet = " ".join(" ".join(_bullet_at(lines, below)).split()).lower()
    return [
        f"the Stop line bullet lacks {phrase!r}"
        for phrase in _STOP_LINE_PHRASES
        if phrase not in bullet
    ]


def test_the_template_names_the_meter_directly_under_the_budget_line() -> None:
    assert _stop_line_gaps(_template()) == []


def test_the_template_has_one_stop_line_bullet() -> None:
    assert _template().count(_STOP_LINE) == 1


def test_the_stop_line_names_a_script_that_ships() -> None:
    lines = _skeleton(_template())
    start = _index_of(lines, _STOP_LINE)
    assert start is not None, "the skeleton has no Stop line bullet"
    bullet = " ".join(_bullet_at(lines, start))
    named = re.search(r"\$\{CLAUDE_SKILL_DIR\}/(scripts/[\w.-]+)", bullet)
    assert named, f"the bullet names no script under the skill directory: {bullet!r}"
    assert _ORCHESTRATE / named.group(1) == _SCRIPT
    assert _SCRIPT.is_file()


_PLACED = (
    "```markdown\n- Budget: x\n- Stop line: <the command that measures it>\n"
    "  ${CLAUDE_SKILL_DIR}/scripts/context_meter.py only reads and never stops or advises\n"
    "- Ledgers: y\n```\n"
)
_OLD_SHAPE = "```markdown\n## Context\n- Budget: x\n- Ledgers: y\n```\n"
_MISPLACED = (
    "```markdown\n- Budget: x\n- Ledgers: y\n- Stop line: <the command that measures it>\n"
    "  ${CLAUDE_SKILL_DIR}/scripts/context_meter.py only reads and never stops or advises\n"
    "```\n"
)


def test_the_template_check_sees_the_old_shape() -> None:
    """Fixtures only, so this holds before and after the change: the check passes a bullet that
    is where it belongs, and reports the old template (no bullet), a bullet below the next bullet,
    a template with no skeleton, and a bullet that lost a phrase."""
    assert _stop_line_gaps(_PLACED) == []
    assert _stop_line_gaps(_OLD_SHAPE) == [_UNDER_BUDGET]
    assert _stop_line_gaps(_MISPLACED) == [_UNDER_BUDGET]
    assert _stop_line_gaps("no fence at all\n") == [
        "the skeleton has no '- Budget:' bullet"
    ]
    assert _stop_line_gaps(_PLACED.replace("only reads and ", "")) == [
        "the Stop line bullet lacks 'only reads'"
    ]


def test_the_template_check_sees_near_misses_of_the_real_bullet() -> None:
    """Derived from the template itself: without the bullet (the old shape), with it below the
    next bullet, naming no script, and re-wrapped on one line, which is the same bullet."""
    real = _template()
    lines = real.split("\n")
    skeleton = _skeleton(real)
    start = _index_of(skeleton, _STOP_LINE)
    assert start is not None, "the template has no Stop line bullet to plant a fault in"
    bullet = _bullet_at(skeleton, start)
    first = lines.index(bullet[0])
    assert lines[first : first + len(bullet)] == bullet

    without = lines[:first] + lines[first + len(bullet) :]
    assert _stop_line_gaps("\n".join(without)) == [_UNDER_BUDGET]

    ledgers = next(i for i, line in enumerate(without) if line.startswith("- Ledgers:"))
    after_ledgers = ledgers + len(_bullet_at(without, ledgers))
    moved = without[:after_ledgers] + bullet + without[after_ledgers:]
    assert _stop_line_gaps("\n".join(moved)) == [_UNDER_BUDGET]

    nameless = real.replace("context_meter.py", "meter.py")
    assert nameless != real
    assert _stop_line_gaps(nameless) == [
        "the Stop line bullet lacks '${claude_skill_dir}/scripts/context_meter.py'"
    ]

    one_line = " ".join(part.strip() for part in bullet)
    rewrapped = lines[:first] + [one_line] + lines[first + len(bullet) :]
    assert "\n".join(rewrapped) != real
    assert _stop_line_gaps("\n".join(rewrapped)) == []
