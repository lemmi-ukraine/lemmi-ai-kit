"""The hooks the Core pack registers fail open, and pass a script's own verdict through.

`plugins/core/hooks/hooks.json` registers each hook as a shell command. Running a hook's script
directly (as `test_gate_learnings_drain.py` and `test_gate_shell_prefix.py` do) proves the script
works and says nothing about what the harness sees when the script is not there: a plugin folder
that was moved, an update that renamed a file, a copy of the plugin with a file missing. The
registered command used to be `uv run ... python -B "<script>"`, and Python exits 2 when it cannot
open its script. Exit 2 is the code the hooks reference gives to a blocking error, so a missing file
turned a guard into a block on every call its matcher covers. That was found by running the string,
not by reading it, and it was not the same everywhere: Git Bash passed Python's 2 through, while
Windows PowerShell's `-Command` reported 1.

So these tests run the REGISTERED STRING, with `${CLAUDE_PLUGIN_ROOT}` replaced as the harness
replaces it, through every shell the harness may use that exists on this machine:

- the script is missing: the command exits 0 and prints nothing, in every shell;
- the script exists: its own stdout, its own exit code (a deny reply with 0, and an exit 2 with a
  message on stderr) and the bytes it read from stdin reach the harness unchanged, in every shell;
- PowerShell also gets the form the hooks reference says the harness writes into a PowerShell
  command, `${env:CLAUDE_PLUGIN_ROOT}`, which PowerShell resolves from the exported environment:
  the script is found and run, and a missing one is silent;
- input a hook cannot use (empty, not JSON, not UTF-8, cut short) ends in exit 0 and no output, for
  both hooks, in every shell;
- both hook scripts import only the standard library, because the launcher keeps the script's own
  folder off the import path and a sibling module would not be found;
- the old, unwrapped command exits non-zero on a missing script, which is the control that shows
  this probe can see the failure at all.

A shell that is not on this machine is a visible skip with its reason, never a pass. What the
registration still cannot protect (a `uv` that is missing or cannot find an interpreter) is pinned
as measured behaviour at the end, so the README's account of it stays true.

Every launch is a `uv` start plus a shell start, which costs a second on some machines, so all the
launches run once, concurrently, from one module fixture, and the tests read their results.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, NamedTuple, cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOKS_DIR = _REPO_ROOT / "plugins" / "core" / "hooks"
_HOOKS_JSON = _HOOKS_DIR / "hooks.json"
_PLACEHOLDER = "${CLAUDE_PLUGIN_ROOT}"
_SCRIPT_REFERENCE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/hooks/([A-Za-z0-9_.-]+\.py)")

_DRAIN = "gate_learnings_drain.py"
_PREFIX = "gate_shell_prefix.py"

_SHELLS = ("bash", "sh", "powershell", "pwsh")
_POWERSHELLS = ("powershell", "pwsh")

# The hook timeout in hooks.json: a hook that stalls must not stall the call, so it is short.
_TIMEOUT_CEILING = 10

# What a denying hook prints: one JSON object, exit 0. The fixture prints exactly this text, so the
# test can demand the same bytes back from the launcher.
_DENY_REPLY = json.dumps(
    {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "denied by fixture",
        }
    }
)

# Files a project could hold at its root. Each is run, and exits 7, if Python imports it instead of the
# standard module of the same name: `runpy` is imported by the launcher itself, the others by the hook.
_SHADOWED_MODULES = ("runpy", "json", "dataclasses", "typing", "re")
_SHADOW_SOURCE = "import sys\nsys.exit(7)\n"

# Input a hook cannot use. Each must end in exit 0 and no output, through the registered string.
_MALFORMED_STDIN = {
    "empty stdin": b"",
    "not JSON": b"not json at all",
    "bytes that are not UTF-8": b"\xff\xfe\xfd\x00garbage",
    "truncated JSON": b'{"tool_name": "Bash", "tool_input": {"command": "cd /x"',
}

# A stand-in for either registered script: it does what its stdin says, so one fixture file can
# print a deny reply, exit 2 with a message or echo the non-ASCII text it was given.
_FIXTURE = f"""\
import json
import sys

data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
mode = data["mode"]
if mode == "exit2":
    sys.stderr.write("blocked by fixture")
    sys.exit(2)
elif mode == "deny":
    sys.stdout.write({_DENY_REPLY!r})
else:
    sys.stdout.write(json.dumps({{"seen": data["text"], "argv": sys.argv[1:], "name": __name__}}))
"""


class _Registered(NamedTuple):
    matcher: str
    command: str
    script: str
    timeout: int | None
    kind: str


def _registered() -> list[_Registered]:
    data = cast(dict[str, Any], json.loads(_HOOKS_JSON.read_text(encoding="utf-8")))
    found: list[_Registered] = []
    for group in cast(list[dict[str, Any]], data["hooks"]["PreToolUse"]):
        for hook in cast(list[dict[str, Any]], group["hooks"]):
            command = str(hook["command"])
            match = _SCRIPT_REFERENCE.search(command)
            assert match is not None, (
                f"a registered command names no plugin script: {command}"
            )
            found.append(
                _Registered(
                    str(group["matcher"]),
                    command,
                    match.group(1),
                    cast("int | None", hook.get("timeout")),
                    str(hook.get("type")),
                )
            )
    return found


def _entry(script: str) -> _Registered:
    matching = [item for item in _registered() if item.script == script]
    assert len(matching) == 1, (
        f"expected exactly one registration of {script}: {matching}"
    )
    return matching[0]


# ---------------------------------------------------------------------------------- the shells

_POWERSHELL_FLAGS = ["-NoProfile", "-NonInteractive", "-Command"]


def _git_bash() -> str | None:
    """Git Bash on Windows (the harness's default shell there), else the system bash."""
    override = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if override and Path(override).is_file():
        return override
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    if git is None:
        return None
    for parent in Path(git).resolve().parents:
        for relative in (("bin", "bash.exe"), ("usr", "bin", "bash.exe")):
            candidate = parent.joinpath(*relative)
            if candidate.is_file():
                return str(candidate)
    return None  # a bash.exe on PATH may be the WSL launcher, which is not the harness's shell


def _shell_argv(name: str) -> tuple[list[str] | None, str]:
    """The argument list that runs a command string in the shell, or None and why it is absent."""
    if name == "bash":
        found = _git_bash()
        return (
            [found, "-c"] if found else None
        ), "no bash (Git Bash on Windows) was found"
    if name == "sh":
        found = shutil.which("sh") if os.name != "nt" else None
        return (
            [found, "-c"] if found else None
        ), "sh is a separate harness shell on macOS and Linux only"
    if name == "powershell":
        found = shutil.which("powershell") if os.name == "nt" else None
        return (
            [found, *_POWERSHELL_FLAGS] if found else None
        ), "Windows PowerShell 5.1 (powershell.exe) exists on Windows only"
    found = shutil.which("pwsh")
    return (
        [found, *_POWERSHELL_FLAGS] if found else None
    ), "pwsh (PowerShell 7) is not installed"


def _need(name: str) -> list[str]:
    """The shell's argument list, or a skip that says what is missing."""
    if shutil.which("uv") is None:
        pytest.skip("uv is not on PATH, and the registered commands start with it")
    argv, why = _shell_argv(name)
    if argv is None:
        pytest.skip(f"{name} is not available on this machine: {why}")
    return argv


# ------------------------------------------------------------------------------ the launches


class _Job(NamedTuple):
    """One launch of a registered string: the string, the plugin root it is run with, the payload on
    stdin, and what to add to the environment. `documented_rewrite` runs the string the way the hooks
    reference says the harness writes it for PowerShell (the placeholder becomes `${env:NAME}` and is
    resolved from the exported environment), so it is launched in PowerShell only."""

    command: str
    root: Path
    stdin: bytes
    env: dict[str, str]
    documented_rewrite: bool = False
    cwd: Path | None = None


def _mode(mode: str, text: str = "") -> bytes:
    return json.dumps({"mode": mode, "text": text}, ensure_ascii=False).encode("utf-8")


def _fixture_root(base: Path, name: str, *scripts: str) -> Path:
    """A plugin folder holding the fixture under each script name given; with none, an empty folder."""
    root = base / name
    root.mkdir()
    if scripts:
        (root / "hooks").mkdir()
        for script in scripts:
            (root / "hooks" / script).write_text(
                _FIXTURE, encoding="utf-8", newline="\n"
            )
    return root


def _find(script: str) -> str | None:
    matching = [item.command for item in _registered() if item.script == script]
    return matching[0] if len(matching) == 1 else None


def _jobs(base: Path) -> dict[str, _Job]:
    """Every launch to make. An entry that is not registered gets no launch, so the tests for it
    fail by name instead of the whole fixture failing before any test can say why."""
    drain, prefix = _find(_DRAIN), _find(_PREFIX)
    old = f'uv run --no-project --python ">=3.11" python -B "{_PLACEHOLDER}/hooks/{_DRAIN}"'
    empty = _fixture_root(base, "empty")
    both = _fixture_root(base, "both", _DRAIN, _PREFIX)
    no_path = _fixture_root(base, "nopath")
    real = _REPO_ROOT / "plugins" / "core"
    project = base / "project"
    (project / ".ai").mkdir(parents=True)
    (project / ".ai" / "shell-prefix-hook.json").write_text(
        '{"enabled": true}', encoding="utf-8"
    )
    project_env = {"CLAUDE_PROJECT_DIR": str(project)}
    # A project whose root holds files named like standard modules, which the hook is run from.
    shadow = base / "shadow"
    (shadow / ".ai").mkdir(parents=True)
    (shadow / ".ai" / "shell-prefix-hook.json").write_text(
        '{"enabled": true}', encoding="utf-8"
    )
    for module in _SHADOWED_MODULES:
        (shadow / f"{module}.py").write_text(
            _SHADOW_SOURCE, encoding="utf-8", newline="\n"
        )
    shadow_call = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "cd /x && ls"},
            "cwd": str(shadow),
        }
    ).encode("utf-8")
    shell_call = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "cd /x && ls"},
            "cwd": str(project),
        }
    ).encode("utf-8")
    drain_call = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "rm .ai/learnings.md"},
            "cwd": str(project),
        }
    ).encode("utf-8")
    text = "привіт ☃ plain"
    jobs: dict[str, _Job] = {
        "old command, script missing": _Job(old, empty, _mode("echo"), {})
    }
    # Each real hook, with its switch on, is handed input it cannot use: it must allow the call.
    for label, payload in _MALFORMED_STDIN.items():
        if prefix is not None:
            jobs[f"malformed stdin ({label}), shell-prefix hook"] = _Job(
                prefix, real, payload, project_env
            )
        if drain is not None:
            jobs[f"malformed stdin ({label}), learnings guard"] = _Job(
                drain, real, payload, project_env
            )
    # Each scenario runs on one entry; the entries share one launcher (asserted separately), and
    # the two scripts are each exercised by the scenarios that matter to them.
    if drain is not None:
        jobs["script missing, learnings guard"] = _Job(drain, empty, _mode("echo"), {})
        jobs["script exits 2"] = _Job(drain, both, _mode("exit2"), {})
        jobs["script prints a deny reply"] = _Job(drain, both, _mode("deny"), {})
        jobs["script echoes stdin"] = _Job(drain, both, _mode("echo", text), {})
        jobs["real learnings guard"] = _Job(drain, real, drain_call, project_env)
        jobs["uv not on PATH"] = _Job(
            drain, both, _mode("echo"), {"PATH": str(no_path)}
        )
    if prefix is not None:
        jobs["script missing, shell-prefix hook"] = _Job(
            prefix, empty, _mode("echo"), {}
        )
        jobs["real shell-prefix hook"] = _Job(prefix, real, shell_call, project_env)
        jobs["real hook, shadowing files in the working directory"] = _Job(
            prefix,
            real,
            shadow_call,
            {"CLAUDE_PROJECT_DIR": str(shadow)},
            False,
            shadow,
        )
        jobs["documented rewrite, script missing"] = _Job(
            prefix, empty, _mode("echo"), {}, True
        )
        jobs["documented rewrite, script present"] = _Job(
            prefix, both, _mode("echo", text), {}, True
        )
    return jobs


def _execute(shell: str, job: _Job) -> "subprocess.CompletedProcess[bytes]":
    """Run a registered string the way the harness does: the root substituted into the string and
    exported, the payload on stdin, one shell reading the whole string."""
    argv, _why = _shell_argv(shell)
    assert argv is not None
    root_text = (
        str(job.root) if shell in ("powershell", "pwsh") else job.root.as_posix()
    )
    if job.documented_rewrite:
        command = job.command.replace(_PLACEHOLDER, "${env:CLAUDE_PLUGIN_ROOT}")
    else:
        command = job.command.replace(_PLACEHOLDER, root_text)
    env = {
        **os.environ,
        "CLAUDE_PLUGIN_ROOT": root_text,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.update(job.env)
    return subprocess.run(
        [*argv, command],
        input=job.stdin,
        capture_output=True,
        env=env,
        cwd=job.cwd,
        timeout=120,
        check=False,
    )


class _Results:
    """Every launch for every shell on this machine, done once and concurrently."""

    def __init__(self, base: Path) -> None:
        self.done: dict[tuple[str, str], subprocess.CompletedProcess[bytes]] = {}
        if shutil.which("uv") is None:
            return
        jobs = _jobs(base)
        shells = [name for name in _SHELLS if _shell_argv(name)[0] is not None]
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                (shell, name): pool.submit(_execute, shell, job)
                for shell in shells
                for name, job in jobs.items()
                if not job.documented_rewrite or shell in _POWERSHELLS
            }
        self.done = {key: future.result() for key, future in futures.items()}

    def get(self, shell: str, name: str) -> "subprocess.CompletedProcess[bytes]":
        _need(shell)
        found = self.done.get((shell, name))
        assert found is not None, (
            f"no launch was made for {name!r}: is its hook registered in hooks.json?"
        )
        return found


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> _Results:
    return _Results(tmp_path_factory.mktemp("reg"))


# ------------------------------------------------------------------------ what is registered


def test_every_registered_script_exists_and_every_hook_script_is_registered() -> None:
    registered = {item.script for item in _registered()}
    on_disk = {path.name for path in _HOOKS_DIR.glob("*.py")}
    assert registered == {_DRAIN, _PREFIX}, registered
    assert registered == on_disk, (
        f"registered but absent: {sorted(registered - on_disk)}; present but not registered: {sorted(on_disk - registered)}"
    )


def test_each_command_names_its_script_through_the_plugin_root_variable_in_quotes() -> (
    None
):
    for item in _registered():
        assert item.command.count(_PLACEHOLDER) == 1, item.command
        assert f'"{_PLACEHOLDER}/hooks/{item.script}"' in item.command, (
            "the hooks reference says to wrap the placeholder in double quotes in shell form"
        )
        assert not re.search(r"[A-Za-z]:[\\/]", item.command), (
            "a registered path must be the variable, not a machine path"
        )


def test_both_entries_use_one_fail_open_launcher_and_the_exit_code_tail() -> None:
    """The launcher is the same text in both, so a fix to it cannot reach only one hook."""
    # `type` is required, and the hooks reference gives it five values; only a "command" entry runs
    # the shell string the launcher is. Asserted per script, so both entries are named.
    assert {item.script: item.kind for item in _registered()} == {
        _DRAIN: "command",
        _PREFIX: "command",
    }, "both registered entries must be command hooks"
    shapes = {item.command.replace(item.script, "<script>") for item in _registered()}
    assert len(shapes) == 1, f"the entries do not share a launcher: {sorted(shapes)}"
    (shape,) = shapes
    assert "os.path.isfile" in shape and "runpy.run_path" in shape, (
        "no check-then-run launcher"
    )
    assert shape.rstrip().endswith("exit $LASTEXITCODE"), (
        "the tail that carries a script's own exit code through PowerShell is missing"
    )
    assert "||" not in shape, "`||` is not valid in Windows PowerShell 5.1"
    assert "python -B -P -c" in shape, (
        "-P keeps the working directory off the import path: the behaviour is pinned by "
        "test_a_project_file_named_like_a_standard_module_is_not_run_by_the_hook"
    )
    # Both flags before `python` are load-bearing. `--no-project` keeps uv from reading or building
    # the consumer project's own environment, which is not the hook's to touch. `--python ">=3.11"`
    # is the floor that makes `-P` exist: an older interpreter rejects the flag and every call
    # would then run a launcher that failed to start.
    assert shape.startswith('uv run --no-project --python ">=3.11" python -B -P -c '), (
        "the launcher must run outside the consumer's project, on Python 3.11 or newer"
    )


def _imported_modules(source: str) -> set[str]:
    """The top-level modules a source imports; a relative import is reported with its leading dots."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                found.add("." * node.level + (node.module or ""))
            elif node.module:
                found.add(node.module.partition(".")[0])
    return found


def _not_standard(modules: set[str]) -> list[str]:
    return sorted(
        name
        for name in modules
        if name.startswith(".") or name not in sys.stdlib_module_names
    )


def test_the_import_scan_sees_a_module_that_is_not_in_the_standard_library() -> None:
    """The scan is shown to find what it looks for: a sibling module, a relative import and a
    third-party name are flagged, and the standard library is not."""
    assert (
        _not_standard(_imported_modules("import json, os.path\nfrom re import sub\n"))
        == []
    )
    planted = (
        "import json\nimport sibling_hook\nfrom helpers.core import x\n"
        "from . import neighbour\nfrom .pkg import y\n"
    )
    assert _not_standard(_imported_modules(planted)) == [
        ".",
        ".pkg",
        "helpers",
        "sibling_hook",
    ]


@pytest.mark.parametrize("script", [_DRAIN, _PREFIX])
def test_a_registered_hook_script_imports_only_the_standard_library(
    script: str,
) -> None:
    """The launcher runs the script by path under `python -P`, which keeps the working directory
    AND the script's own folder off the import path (`python script.py` put the folder first). A
    hook that imports a sibling module would fail to start with exit 1, which does not block, and
    would go quiet. A hook script is one file that imports only the standard library."""
    source = (_HOOKS_DIR / script).read_text(encoding="utf-8")
    assert not _not_standard(_imported_modules(source)), (
        f"{script} imports something the launcher cannot find: "
        f"{_not_standard(_imported_modules(source))}"
    )


def test_the_matchers_cover_the_tools_each_hook_judges() -> None:
    assert set(_entry(_DRAIN).matcher.split("|")) == {
        "Edit",
        "MultiEdit",
        "Write",
        "Bash",
        "PowerShell",
    }
    assert set(_entry(_PREFIX).matcher.split("|")) == {"Bash", "PowerShell"}


def test_each_hook_has_a_short_timeout() -> None:
    for item in _registered():
        assert item.timeout is not None and 0 < item.timeout <= _TIMEOUT_CEILING, item


# --------------------------------------------------------------------- the control and the fix


@pytest.mark.parametrize("shell", _SHELLS)
def test_the_old_unwrapped_command_fails_on_a_missing_script(
    shell: str, results: _Results
) -> None:
    """The control: the command as it was registered before the launcher exits non-zero when its
    script is missing (2 from Python under sh and bash, 1 from PowerShell's -Command). A probe that
    could not see this would pass the fix for the wrong reason."""
    done = results.get(shell, "old command, script missing")
    assert done.returncode != 0, (
        "the unwrapped command no longer fails on a missing script?"
    )
    if shell in ("bash", "sh"):
        assert done.returncode == 2, (
            "Python's exit code for a script it cannot open is 2, which blocks"
        )
    assert done.stdout == b""


@pytest.mark.parametrize("shell", _SHELLS)
@pytest.mark.parametrize(
    "name", ["script missing, learnings guard", "script missing, shell-prefix hook"]
)
def test_a_missing_script_exits_zero_and_prints_nothing(
    shell: str, name: str, results: _Results
) -> None:
    done = results.get(shell, name)
    assert (done.returncode, done.stdout) == (0, b""), done.stderr[-300:]


@pytest.mark.parametrize("shell", _SHELLS)
def test_a_script_that_exits_two_keeps_its_exit_code_and_its_message(
    shell: str, results: _Results
) -> None:
    """Not a thing these two hooks do (they decide by their reply), but the registration must not
    be the reason a script's own verdict is lost: PowerShell's -Command alone reports 1 here."""
    done = results.get(shell, "script exits 2")
    assert done.returncode == 2, (done.returncode, done.stderr[-300:])
    assert b"blocked by fixture" in done.stderr
    assert done.stdout == b""


@pytest.mark.parametrize("shell", _SHELLS)
def test_stdin_arrives_as_bytes_and_the_script_runs_as_main(
    shell: str, results: _Results
) -> None:
    done = results.get(shell, "script echoes stdin")
    assert done.returncode == 0, done.stderr[-300:]
    seen = cast(dict[str, Any], json.loads(done.stdout.decode("ascii")))
    assert seen["seen"] == "привіт ☃ plain"
    assert seen["name"] == "__main__", (
        "the script must run as __main__, as `python script.py` does"
    )
    assert seen["argv"] == [], (
        "the script must see the argument list it would see when run directly"
    )


@pytest.mark.parametrize("shell", _SHELLS)
def test_a_deny_reply_with_exit_zero_passes_through_unchanged(
    shell: str, results: _Results
) -> None:
    """The hooks decide by a JSON reply and exit 0: the launcher must hand those very bytes on."""
    done = results.get(shell, "script prints a deny reply")
    assert (done.returncode, done.stdout) == (0, _DENY_REPLY.encode("ascii")), (
        done.stderr[-300:]
    )


@pytest.mark.parametrize("shell", _SHELLS)
def test_input_a_hook_cannot_use_exits_zero_and_prints_nothing(
    shell: str, results: _Results
) -> None:
    """A guard that cannot read its input must not block unrelated work, whichever shell reads the
    registered string: empty input, text that is not JSON, bytes that are not UTF-8 and a payload
    cut short, for both hooks."""
    failures: list[str] = []
    for label in _MALFORMED_STDIN:
        for hook in ("shell-prefix hook", "learnings guard"):
            name = f"malformed stdin ({label}), {hook}"
            done = results.get(shell, name)
            if (done.returncode, done.stdout) != (0, b""):
                failures.append(f"{name}: exit {done.returncode}, {done.stdout[:80]!r}")
    assert not failures, failures


@pytest.mark.parametrize("shell", _POWERSHELLS)
def test_powershell_resolves_the_documented_environment_form_of_the_placeholder(
    shell: str, results: _Results
) -> None:
    """The hooks reference: Claude Code rewrites the plugin-root placeholder in a PowerShell
    shell-form command to PowerShell's `${env:NAME}` form, and PowerShell resolves it from the
    exported environment, which works inside double quotes. Run that form. A missing script is
    silent, and a present one really runs, so the path was resolved and not merely absent."""
    missing = results.get(shell, "documented rewrite, script missing")
    assert (missing.returncode, missing.stdout) == (0, b""), missing.stderr[-300:]
    present = results.get(shell, "documented rewrite, script present")
    assert present.returncode == 0, present.stderr[-300:]
    seen = cast(dict[str, Any], json.loads(present.stdout.decode("ascii")))
    assert seen["seen"] == "привіт ☃ plain" and seen["name"] == "__main__"


@pytest.mark.parametrize("shell", _SHELLS)
def test_a_project_file_named_like_a_standard_module_is_not_run_by_the_hook(
    shell: str, results: _Results
) -> None:
    """`python -c` puts the working directory first on the import path, so a file named `runpy.py`
    or `json.py` at the project root would be run in place of the module: the hook would not decide
    at all, and a file from the project would run inside a plugin hook. The command the hook ran
    from `python script.py` did not have this problem, because the script's own folder came first.
    The launcher keeps the working directory off the import path."""
    done = results.get(shell, "real hook, shadowing files in the working directory")
    assert done.returncode == 0, (done.returncode, done.stderr[-300:])
    reply = cast(dict[str, Any], json.loads(done.stdout.decode("ascii")))
    assert reply["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------- the real scripts, through the string


@pytest.mark.parametrize("shell", _SHELLS)
def test_the_real_learnings_guard_denies_through_the_registered_string(
    shell: str, results: _Results
) -> None:
    done = results.get(shell, "real learnings guard")
    assert done.returncode == 0, done.stderr[-300:]
    reply = cast(dict[str, Any], json.loads(done.stdout.decode("ascii")))
    assert reply["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("shell", _SHELLS)
def test_the_real_shell_prefix_hook_denies_through_the_registered_string(
    shell: str, results: _Results
) -> None:
    done = results.get(shell, "real shell-prefix hook")
    assert done.returncode == 0, done.stderr[-300:]
    reply = cast(dict[str, Any], json.loads(done.stdout.decode("ascii")))
    assert reply["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert reply["hookSpecificOutput"]["permissionDecisionReason"].startswith(
        "Do not move"
    )


# ------------------------------------------------------------ what the registration cannot protect


@pytest.mark.parametrize("shell", _SHELLS)
def test_a_uv_that_is_not_on_the_path_is_not_made_safe_by_the_launcher(
    shell: str, results: _Results
) -> None:
    """Measured, so the README's statement stays true. The launcher runs inside Python, so it cannot
    help when `uv` itself does not start: a POSIX shell reports 127 (not a blocking code), and
    PowerShell reports 0 because the tail passes on `$LASTEXITCODE`, which `uv` never set."""
    done = results.get(shell, "uv not on PATH")
    assert done.stdout == b""
    if shell in ("bash", "sh"):
        assert done.returncode == 127
    else:
        assert done.returncode == 0
