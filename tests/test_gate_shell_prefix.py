"""The shell-prefix hook denies the shapes it names and lets everything else through.

`plugins/core/hooks/gate_shell_prefix.py` is switched on per project by a JSON file, and when
it is on it refuses the shell calls that move the persistent working directory, start with a
variable assignment, or shadow `cd`. Its table of shapes is the fixture list a consumer's own
hook grew over several review rounds: the original 50-shape probe, then the shapes each review
found. Every row states the decision it REQUIRES, and the ALLOW rows matter as much as the DENY
rows: a hook that blocks unrelated work is worse than no hook.

Row = (name, tool, command, configuration, decision). The configuration names the project file
the row runs under (`_CONFIGS`); the decision is `allow`, a denial family (`move`, `shadow`,
`assign`), `warn` (the file is unusable, so the call is allowed with a message), or one of two
annotated forms:

- `allowed:<id>` is an ALLOW the hook states on purpose, or a shape it does not cover. The
  hook's header says why in an `ALLOWED <id>:` paragraph, and `test_the_header_and_the_table_name_the_same_limits`
  keeps the two lists equal in both directions, so a limit nobody wrote down and a limit nobody
  tests cannot both exist.
- `refused:<id>` is a DENY the hook makes although the shape is harmless; the header carries a
  `REFUSED <id>:` paragraph for it.

The three controls come first and are asserted on their own: a deny, an allow, and the default
(no file) allowing a shape the switched-on hook denies. A table that only ever passes proves
nothing, so `test_the_table_can_fail_both_ways` runs it against a hook that allows everything and
a hook that denies everything and demands failures on the right side of each.

The hook is a script. Most rows call its `decide` function in this process (the table is large and
a process per row costs most of a second on Windows); the tests that pin the contract run it as a
subprocess, the way the harness does, so a stray line on stdout, a crash or a reply that is not
JSON cannot hide.

Commands that need a drive, home or user-folder path are built from fragments: written whole they
are the machine-specific paths the repository's hygiene scans exist to keep out.
"""

import ast
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping
from functools import cache
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / "plugins" / "core" / "hooks" / "gate_shell_prefix.py"
_README = _REPO_ROOT / "plugins" / "core" / "README.md"
_CONFIG_RELATIVE = Path(".ai") / "shell-prefix-hook.json"

# Built from fragments: written whole these read as machine paths, or as the name of the console
# encoding variable, to the repository's hygiene scans.
_DRIVE = "C" + ":"
_USERS = "Us" + "ers"
_ENCODING_VARIABLE = "PYTHON" + "IOENCODING"

Row = tuple[str, str, str, str, str]
Decide = Callable[[bytes, Mapping[str, str]], str]

# What the model reads after a denial, one opening per rule family, so the families can be told apart.
_OPENINGS: tuple[tuple[str, str], ...] = (
    ("Do not move the shell's working directory", "move"),
    ("Do not redefine", "shadow"),
    ("Drop the leading variable assignment", "assign"),
)

_NONE = "none"
_OFF = "off"
_LAX = "lax"
_RELATIVE_CD = "relative-cd"
_SET_LOCATION = "set-location"
_PS_ASSIGN = "ps-assign"
_STRICT = "strict"
_POWERSHELL_FORM = "powershell-form"
_TWO_FORMS = "two-forms"

_STRICT_FORMS: list[dict[str, Any]] = [
    {"tool": "Bash", "folder": "app-dir", "then": ["build-tool"]}
]

# Configuration name -> the text of `.ai/shell-prefix-hook.json` (None: no such file).
_CONFIGS: dict[str, str | None] = {
    _NONE: None,
    _OFF: json.dumps({"enabled": False}),
    _LAX: json.dumps({"enabled": True}),
    _RELATIVE_CD: json.dumps({"enabled": True, "deny_relative_cd": True}),
    _SET_LOCATION: json.dumps({"enabled": True, "deny_set_location": True}),
    _PS_ASSIGN: json.dumps({"enabled": True, "deny_powershell_assignment": True}),
    _STRICT: json.dumps(
        {
            "enabled": True,
            "deny_relative_cd": True,
            "deny_set_location": True,
            "deny_powershell_assignment": True,
            "allowed_forms": _STRICT_FORMS,
        }
    ),
    _POWERSHELL_FORM: json.dumps(
        {
            "enabled": True,
            "deny_relative_cd": True,
            "allowed_forms": [
                {"tool": "PowerShell", "folder": "app-dir", "then": ["build-tool"]}
            ],
        }
    ),
    _TWO_FORMS: json.dumps(
        {
            "enabled": True,
            "deny_relative_cd": True,
            "allowed_forms": [
                {"tool": "Bash", "folder": "app-dir", "then": ["build-tool"]},
                {
                    "tool": "Bash",
                    "folder": "lib-dir",
                    "then": ["lint-tool", "build-tool"],
                },
            ],
        }
    ),
    "unusable: not JSON": "{ this is not json",
    "unusable: unknown key": json.dumps({"enabled": True, "deny_relative_cds": True}),
    "unusable: wrong type": json.dumps({"enabled": "yes"}),
    "unusable: form without then": json.dumps(
        {
            "enabled": True,
            "allowed_forms": [{"tool": "Bash", "folder": "app-dir"}],
        }
    ),
}

# ------------------------------------------------------------------------------ the controls

_CONTROLS: list[Row] = [
    ("CONTROL deny: an absolute cd", "Bash", "cd /x && ls", _LAX, "move"),
    ("CONTROL allow: a plain command", "Bash", "ls -la", _LAX, "allow"),
    (
        "CONTROL default: no file allows what the switched-on hook denies",
        "Bash",
        "cd /x && ls",
        _NONE,
        "allow",
    ),
]

# ----------------------------------------------------------------- the 50-shape probe table

_PROBE: list[Row] = [
    ("cd abs posix", "Bash", "cd /c/" + _USERS + "/x && ls", _LAX, "move"),
    ("plain ls", "Bash", "ls -la", _LAX, "allow"),
    ("cd abs drive fwd", "Bash", f"cd {_DRIVE}/x && ls", _LAX, "move"),
    ("cd abs drive back", "Bash", f"cd {_DRIVE}\\x && ls", _LAX, "move"),
    ("cd home tilde", "Bash", "cd ~ && ls", _LAX, "move"),
    ("cd $HOME", "Bash", "cd $HOME/x && ls", _LAX, "move"),
    ("cd quoted abs", "Bash", 'cd "/c/x" && ls', _LAX, "move"),
    ("cd relative", "Bash", "cd backend && ls", _LAX, "allowed:relative-cd"),
    ("cd dot", "Bash", "cd . && ls", _LAX, "allowed:cd-dot"),
    ("cd dotdot", "Bash", "cd .. && ls", _LAX, "allowed:relative-cd"),
    ("cd alone", "Bash", "cd", _LAX, "move"),
    ("cd dash", "Bash", "cd - && ls", _LAX, "move"),
    ("cd $VAR path", "Bash", 'cd "$R" && ls', _LAX, "move"),
    ("leading spaces then cd abs", "Bash", "   cd /x && ls", _LAX, "move"),
    ("cd abs on the second line", "Bash", "echo hi\ncd /x\nls", _LAX, "move"),
    ("subshell cd abs", "Bash", "(cd /x && ls)", _LAX, "allowed:subshell-cd"),
    ("brace group cd abs", "Bash", "{ cd /x; ls; }", _LAX, "move"),
    ("pushd abs", "Bash", "pushd /x && ls", _LAX, "move"),
    ("builtin cd abs", "Bash", "builtin cd /x && ls", _LAX, "move"),
    ("command cd abs", "Bash", "command cd /x && ls", _LAX, "move"),
    ("time cd abs", "Bash", "time cd /x", _LAX, "move"),
    ("cd shadow function", "Bash", "cd() { :; }; cd /x", _LAX, "shadow"),
    ("alias cd", "Bash", "alias cd=true; cd /x", _LAX, "shadow"),
    ("FOO=bar cmd", "Bash", "FOO=bar ls", _LAX, "assign"),
    (
        "console encoding variable then python",
        "Bash",
        _ENCODING_VARIABLE + "=utf-8 python x.py",
        _LAX,
        "assign",
    ),
    ("dummy cd_unused=1;", "Bash", "cd_unused=1; ls", _LAX, "assign"),
    ("two assignments", "Bash", "A=1 B=2 ls", _LAX, "assign"),
    ("assignment alone", "Bash", "VAR=1", _LAX, "assign"),
    ("assignment then newline", "Bash", "VAR=1\nls", _LAX, "assign"),
    ("assignment with empty value", "Bash", "FOO= ls", _LAX, "assign"),
    ("assignment from substitution", "Bash", "x=$(date) && echo $x", _LAX, "assign"),
    ("assignment with quoted space", "Bash", 'FOO="a b" cmd', _LAX, "assign"),
    ("lowercase name", "Bash", "foo=bar ls", _LAX, "assign"),
    (
        "name starting with a digit",
        "Bash",
        "1A=b ls",
        _LAX,
        "allowed:not-an-assignment",
    ),
    ("dotted name", "Bash", "a.b=c ls", _LAX, "allowed:not-an-assignment"),
    ("export then assignment", "Bash", "export FOO=bar && ls", _LAX, "assign"),
    ("env then assignment", "Bash", "env FOO=bar ls", _LAX, "assign"),
    ("set -e", "Bash", "set -e; ls", _LAX, "allowed:set-builtin"),
    (
        "assignment after &&",
        "Bash",
        "ls && FOO=bar cmd",
        _LAX,
        "allowed:later-assignment",
    ),
    ("heredoc body names cd abs", "Bash", "cat <<'EOF'\ncd /x\nEOF", _LAX, "allow"),
    ("git -C abs", "Bash", "git -C /abs status", _LAX, "allow"),
    (
        "uv run python -X utf8",
        "Bash",
        "uv run --no-project python -X utf8 x.py",
        _LAX,
        "allow",
    ),
    ("echo a=b", "Bash", "echo a=b", _LAX, "allow"),
    ("git commit message with =", "Bash", 'git commit -m "a=b c"', _LAX, "allow"),
    ("empty command", "Bash", "", _LAX, "allow"),
    (
        "PowerShell $env:FOO='1'; ls",
        "PowerShell",
        "$env:FOO='1'; ls",
        _LAX,
        "assign",
    ),
    (
        "PowerShell $x = 1; ls",
        "PowerShell",
        "$x = 1; ls",
        _LAX,
        "allowed:ps-local-variable",
    ),
    (
        "PowerShell Set-Location abs",
        "PowerShell",
        f"Set-Location {_DRIVE}\\x; ls",
        _LAX,
        "move",
    ),
    ("PowerShell cd abs", "PowerShell", f"cd {_DRIVE}\\x; ls", _LAX, "move"),
    (
        "PowerShell leading NAME=value (bash shape)",
        "PowerShell",
        "FOO=bar ls",
        _LAX,
        "assign",
    ),
]

# ---------------------------------------- the shapes the reviews of that table found, and more

_FOUND: list[Row] = [
    # a move in any statement, not only the first
    ("cd abs after &&", "Bash", "ls && cd /x && ls", _LAX, "move"),
    ("cd abs after a semicolon", "Bash", "ls; cd /x", _LAX, "move"),
    ("cd abs after ||", "Bash", "false || cd /x", _LAX, "move"),
    (
        "cd var inside a for loop",
        "Bash",
        'for d in a b; do cd "$d"; done',
        _LAX,
        "move",
    ),
    ("cd abs inside an if", "Bash", "if true; then cd /x; fi", _LAX, "move"),
    ("cd abs as the condition of an if", "Bash", "if cd /x; then ls; fi", _LAX, "move"),
    ("cd abs after a negation", "Bash", "! cd /x", _LAX, "move"),
    (
        "cd abs after a heredoc ends",
        "Bash",
        "cat <<'EOF' > f\ncd /x\nEOF\ncd /y",
        _LAX,
        "move",
    ),
    (
        "cd abs after a heredoc with a dash tag",
        "Bash",
        "cat <<-EOF\n\tcd /x\n\tEOF\ncd /y",
        _LAX,
        "move",
    ),
    ("cd -P abs", "Bash", "cd -P /x && ls", _LAX, "move"),
    ("cd -- abs", "Bash", "cd -- /x && ls", _LAX, "move"),
    ("pushd bare", "Bash", "pushd", _LAX, "move"),
    ("command cd in a later statement", "Bash", "ls && command cd /x", _LAX, "move"),
    (
        "cd with a command substitution",
        "Bash",
        "cd $(git rev-parse --show-toplevel)",
        _LAX,
        "move",
    ),
    ("cd then a redirect", "Bash", "cd /x > /dev/null", _LAX, "move"),
    ("command -p cd abs", "Bash", "command -p cd /x", _LAX, "move"),
    ("command -- cd abs", "Bash", "command -- cd /x", _LAX, "move"),
    ("time -p cd abs", "Bash", "time -p cd /x", _LAX, "move"),
    ("builtin -- cd abs", "Bash", "builtin -- cd /x", _LAX, "move"),
    ("a brace group after &&", "Bash", "ls && { cd /x; }", _LAX, "move"),
    ("a brace group after time", "Bash", "time { cd /x; }", _LAX, "move"),
    ("a cd after a background statement", "Bash", "ls & cd /x", _LAX, "move"),
    ("a cd after a pipeline", "Bash", "ls | cat; cd /x", _LAX, "move"),
    ("a cd on the line after a pipeline", "Bash", "ls | cat\ncd /x", _LAX, "move"),
    ("a cd split by a line continuation", "Bash", "c\\\nd /x", _LAX, "move"),
    ("a cd split by a CRLF continuation", "Bash", "c\\\r\nd /x", _LAX, "move"),
    ("a continued line then && cd", "Bash", "ls \\\n&& cd /x", _LAX, "move"),
    ("a CRLF line ending after a cd", "Bash", "cd /x\r\nls", _LAX, "move"),
    # a backslash before a letter only quotes it: the shell still runs cd
    (
        "a backslash before the command word still runs cd",
        "Bash",
        "\\cd /x",
        _LAX,
        "move",
    ),
    (
        "a backslash inside the command word still runs cd",
        "Bash",
        "c\\d /x",
        _LAX,
        "move",
    ),
    # a heredoc tag is any word, so the body is data and the line after it is code again
    (
        "heredoc tag with hyphens then cd",
        "Bash",
        "cat <<END-OF-FILE\nbody\nEND-OF-FILE\ncd /x",
        _LAX,
        "move",
    ),
    (
        "heredoc tag with a dot then cd",
        "Bash",
        "cat <<EOF.TXT\nbody\nEOF.TXT\ncd /x",
        _LAX,
        "move",
    ),
    (
        "heredoc with a backslash-quoted tag then cd",
        "Bash",
        "cat <<\\EOF\nbody\nEOF\ncd /x",
        _LAX,
        "move",
    ),
    (
        "heredoc with a quoted hyphenated tag then cd",
        "Bash",
        "cat <<'END-OF-FILE'\nbody\nEND-OF-FILE\ncd /x",
        _LAX,
        "move",
    ),
    (
        "hyphenated tag: the body naming cd is data",
        "Bash",
        "cat <<END-OF-FILE\ncd /x\nEND-OF-FILE",
        _LAX,
        "allow",
    ),
    (
        "quoted tag: the body naming cd is data",
        "Bash",
        "cat <<'END-OF-FILE'\ncd /x\nEND-OF-FILE",
        _LAX,
        "allow",
    ),
    (
        "a tag after a space: the body naming cd is data",
        "Bash",
        "cat << EOF\ncd /x\nEOF",
        _LAX,
        "allow",
    ),
    ("a here-string is not a heredoc", "Bash", 'cat <<< "cd /x"', _LAX, "allow"),
    (
        "apostrophe in a heredoc body then a relative cd",
        "Bash",
        "cat <<'EOF'\ndon't cd /x\nEOF\ncd backend",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "ANSI-C quote holding an escaped quote then cd",
        "Bash",
        "echo $'\\''; cd /x; echo ''",
        _LAX,
        "move",
    ),
    ("ANSI-C quote naming cd is data", "Bash", "echo $'cd /x'", _LAX, "allow"),
    (
        "ANSI-C quote with an escaped quote around cd is data",
        "Bash",
        "echo $'it\\'s; cd /x'",
        _LAX,
        "allow",
    ),
    # subshells, substitutions and backgrounded moves leave the persistent directory alone
    ("a cd in $( )", "Bash", "echo $(cd /x && pwd)", _LAX, "allowed:subshell-cd"),
    (
        "a subshell after a statement",
        "Bash",
        "ls && (cd /x && ls)",
        _LAX,
        "allowed:subshell-cd",
    ),
    ("a cd in backticks", "Bash", "echo `cd /x && pwd`", _LAX, "allowed:subshell-cd"),
    (
        "a separator inside backticks keeps the cd after it in the substitution",
        "Bash",
        "echo `ls; cd /x`",
        _LAX,
        "allowed:subshell-cd",
    ),
    ("a lone (cd /x)", "Bash", "(cd /x)", _LAX, "allowed:subshell-cd"),
    (
        "a cd in a background statement",
        "Bash",
        "cd /x &",
        _LAX,
        "allowed:background-cd",
    ),
    (
        "a background cd then wait",
        "Bash",
        "cd /x & wait",
        _LAX,
        "allowed:background-cd",
    ),
    (
        "a cd as a pipeline segment",
        "Bash",
        "cd /x | cat",
        _LAX,
        "allowed:pipeline-segment",
    ),
    (
        "a cd as the last pipeline segment",
        "Bash",
        "echo hi | cd /x",
        _LAX,
        "allowed:pipeline-segment",
    ),
    (
        "a lone closing brace is an argument",
        "Bash",
        "echo } cd /x",
        _LAX,
        "allowed:brace-argument",
    ),
    (
        "a lone opening brace is an argument",
        "Bash",
        "echo { cd /x",
        _LAX,
        "allowed:brace-argument",
    ),
    # relative targets
    (
        "cd relative after &&",
        "Bash",
        "ls && cd backend && ls",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "cd relative on the second line",
        "Bash",
        "echo hi\ncd backend\nls",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "cd with a colon in a relative name",
        "Bash",
        "cd dir:name",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "cd with an at sign in a relative name",
        "Bash",
        "cd @x",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "a continued line then a relative cd",
        "Bash",
        "ls \\\n  -la && cd backend",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "a spaced shift in an arithmetic expansion then cd",
        "Bash",
        "echo $((1 << n))\ncd /x",
        _LAX,
        "move",
    ),
    (
        "a shift after a name in an arithmetic expansion then cd",
        "Bash",
        "echo $((a<<n))\ncd /x",
        _LAX,
        "move",
    ),
    (
        "a shift in an arithmetic command then cd",
        "Bash",
        "(( x << n ))\ncd /x",
        _LAX,
        "move",
    ),
    (
        "a heredoc after an arithmetic expansion is still a heredoc",
        "Bash",
        "echo $((1 << 2)); cat <<EOF\ncd /x\nEOF",
        _LAX,
        "allow",
    ),
    (
        "arithmetic shift then a relative cd",
        "Bash",
        "echo $((1 << n))\ncd backend",
        _LAX,
        "allowed:relative-cd",
    ),
    # data that merely names a mover
    (
        "quoted multi-line string with a cd line",
        "Bash",
        'git commit -m "fix\ncd /x\nmore"',
        _LAX,
        "allow",
    ),
    (
        "single-quoted multi-line string with a cd line",
        "Bash",
        "echo 'a\ncd /x\nb'",
        _LAX,
        "allow",
    ),
    ("a comment line naming cd", "Bash", "# cd /x\nls", _LAX, "allow"),
    ("a trailing comment hides a cd", "Bash", "ls # note; cd /x", _LAX, "allow"),
    ("a comment hides an && and a cd", "Bash", "ls # a && cd /x", _LAX, "allow"),
    # spellings of an absolute target, and a hash that is not a comment (each was an unguarded gap)
    ("a hash inside a word is not a comment", "Bash", "echo a#b; cd /x", _LAX, "move"),
    (
        "a hash right after a closing quote is not a comment",
        "Bash",
        "echo 'x'#b; cd /x",
        _LAX,
        "move",
    ),
    ("cd to a single-quoted absolute target", "Bash", "cd '/x' && ls", _LAX, "move"),
    (
        "cd to a UNC path in double quotes",
        "Bash",
        'cd "\\\\\\\\server\\\\share" && ls',
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location to a single-quoted absolute target",
        "PowerShell",
        "Set-Location '/x'; ls",
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location to a UNC path",
        "PowerShell",
        "Set-Location \\\\server\\share; ls",
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location to a root-relative backslash path",
        "PowerShell",
        "Set-Location \\x; ls",
        _LAX,
        "move",
    ),
    # constructs the lexer reads, each pinned by the shape that tells it from its absence
    (
        "PowerShell backtick continuation joins a Set-Location and its target",
        "PowerShell",
        "Set-Location `\n/x",
        _LAX,
        "move",
    ),
    (
        "PowerShell here-string body naming a mover is data",
        "PowerShell",
        "@'\nx\nSet-Location /x\n'@ | Out-Null",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a here-string given to Set-Location is an unreadable target",
        "PowerShell",
        "Set-Location @'\n/x\n'@",
        _LAX,
        "move",
    ),
    (
        "PowerShell backtick-escaped colon in a quoted drive path",
        "PowerShell",
        'Set-Location "C`:\\x"',
        _LAX,
        "move",
    ),
    (
        "PowerShell a backtick escape in double quotes is resolved before the target is judged",
        "PowerShell",
        'Set-Location "`a/x"',
        _LAX,
        "allow",
    ),
    (
        "PowerShell a backtick before an ordinary letter of the command word still runs the mover",
        "PowerShell",
        f"Set-Locat`ion {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell an escaped quote keeps a mover inside the string, where it is data",
        "PowerShell",
        f'Write-Host "a`"; Set-Location {_DRIVE}\\x"',
        _LAX,
        "allow",
    ),
    (
        "PowerShell a mover after a string that holds an escaped quote is judged",
        "PowerShell",
        f'Write-Host "a`"b"; Set-Location {_DRIVE}\\x; Write-Host "c"',
        _LAX,
        "move",
    ),
    (
        "PowerShell a hash right after a quote is not a comment",
        "PowerShell",
        "Write-Output 'x'#y; Set-Location /x",
        _LAX,
        "move",
    ),
    (
        "cd then a both-streams redirect is not a background job",
        "Bash",
        "cd /x &>/dev/null",
        _LAX,
        "move",
    ),
    (
        "a function body that is never called is still judged",
        "Bash",
        "function f { cd /x; }",
        _LAX,
        "refused:unexecuted-code",
    ),
    (
        "a function definition body is judged like any statement",
        "Bash",
        "f() { cd /x; }",
        _LAX,
        "refused:unexecuted-code",
    ),
    (
        "a branch that is never taken is still judged",
        "Bash",
        "if false; then cd /x; fi",
        _LAX,
        "refused:unexecuted-code",
    ),
    ("cd inside double quotes", "Bash", 'echo "cd /x"', _LAX, "allow"),
    ("cd inside single quotes", "Bash", "grep -rn 'cd /x' dir", _LAX, "allow"),
    ("python -c with cd text", "Bash", "python -c \"print('cd /x')\"", _LAX, "allow"),
    (
        "docker exec sh -c cd",
        "Bash",
        "docker exec c sh -c 'cd /app && ls'",
        _LAX,
        "allow",
    ),
    ("ssh remote cd", "Bash", 'ssh host "cd /x; ls"', _LAX, "allow"),
    ("bash -c runs a child process", "Bash", "bash -c 'cd /x && ls'", _LAX, "allow"),
    ("command -v cd only looks the name up", "Bash", "command -v cd", _LAX, "allow"),
    ("command -V cd only looks the name up", "Bash", "command -V cd", _LAX, "allow"),
    ("command -pv cd only looks the name up", "Bash", "command -pv cd", _LAX, "allow"),
    ("command -p ls runs no mover", "Bash", "command -p ls", _LAX, "allow"),
    ("time -p ls runs no mover", "Bash", "time -p ls", _LAX, "allow"),
    ("type cd", "Bash", "type cd", _LAX, "allow"),
    ("git log -- cd", "Bash", "git log -- cd", _LAX, "allow"),
    ("echo cd", "Bash", "echo cd /tmp", _LAX, "allow"),
    ("a cd-named file as an argument", "Bash", "cat cd", _LAX, "allow"),
    # leading assignments and their disguises
    ("export alone sets nothing", "Bash", "export FOO", _LAX, "allow"),
    ("export -p lists variables", "Bash", "export -p", _LAX, "allow"),
    ("export -n then an assignment", "Bash", "export -n FOO=bar; ls", _LAX, "assign"),
    ("readonly then an assignment", "Bash", "readonly X=1; ls", _LAX, "assign"),
    ("readonly alone", "Bash", "readonly FOO", _LAX, "allow"),
    ("readonly -p lists variables", "Bash", "readonly -p", _LAX, "allow"),
    ("declare -x then an assignment", "Bash", "declare -x X=1; ls", _LAX, "assign"),
    ("typeset -x then an assignment", "Bash", "typeset -x X=1; ls", _LAX, "assign"),
    ("declare -rx then an assignment", "Bash", "declare -rx X=1; ls", _LAX, "assign"),
    ("declare -p lists variables", "Bash", "declare -p", _LAX, "allow"),
    ("declare -x without a value", "Bash", "declare -x FOO", _LAX, "allow"),
    (
        "declare -a with an array assignment stays allowed",
        "Bash",
        "declare -a arr=(1 2 3); echo ${arr[1]}",
        _LAX,
        "allow",
    ),
    ("env -u NAME then an assignment", "Bash", "env -u A X=1 ls", _LAX, "assign"),
    ("env with two unset options", "Bash", "env -u A -u B X=1 ls", _LAX, "assign"),
    ("env -C DIR then an assignment", "Bash", "env -C /x X=1 ls", _LAX, "assign"),
    (
        "env --unset=NAME then an assignment",
        "Bash",
        "env --unset=A X=1 ls",
        _LAX,
        "assign",
    ),
    (
        "env --unset NAME then an assignment",
        "Bash",
        "env --unset A X=1 ls",
        _LAX,
        "assign",
    ),
    ("env -u without an assignment", "Bash", "env -u A ls", _LAX, "allow"),
    ("env piped", "Bash", "env | sort", _LAX, "allow"),
    ("env -i without an assignment", "Bash", "env -i bash -c true", _LAX, "allow"),
    ("an appended assignment", "Bash", "FOO+=x ls", _LAX, "assign"),
    ("an array assignment", "Bash", "arr=(1 2) ls", _LAX, "assign"),
    (
        "a subshell with an assignment prefix",
        "Bash",
        "( X=1 ls )",
        _LAX,
        "allowed:subshell-assignment",
    ),
    (
        "a brace group with an assignment prefix",
        "Bash",
        "{ X=1 ls; }",
        _LAX,
        "allowed:group-assignment",
    ),
    (
        "an assignment on the second line",
        "Bash",
        "ls\nFOO=bar cmd",
        _LAX,
        "allowed:later-assignment",
    ),
    # the shadows
    ("cd () with a space", "Bash", "cd () { :; }; ls", _LAX, "shadow"),
    ("function cd", "Bash", "function cd { :; }; ls", _LAX, "shadow"),
    ("function cd with parentheses", "Bash", "function cd() { :; }", _LAX, "shadow"),
    ("a shadow after a statement", "Bash", "ls; cd() { :; }", _LAX, "shadow"),
    (
        "a function that is not cd",
        "Bash",
        'mkd() { mkdir -p "$1"; }; mkd x',
        _LAX,
        "allow",
    ),
    ("alias of another name", "Bash", "alias ll='ls -l'; ll", _LAX, "allow"),
    (
        "an alias whose name only starts with cd is not a shadow",
        "Bash",
        "alias cdx=ls",
        _LAX,
        "allow",
    ),
    ("an alias named cd is a shadow", "Bash", "alias cd=ls", _LAX, "shadow"),
    ("PowerShell function cd", "PowerShell", "function cd { }; ls", _LAX, "shadow"),
    # PowerShell
    (
        "PowerShell $x += 1",
        "PowerShell",
        "$x += 1; $x",
        _LAX,
        "allowed:ps-local-variable",
    ),
    (
        "PowerShell a lone local assignment",
        "PowerShell",
        "$ErrorActionPreference = 'Stop'",
        _LAX,
        "allowed:ps-local-variable",
    ),
    ("PowerShell env var with spaces", "PowerShell", "$env:FOO = 'a'", _LAX, "assign"),
    ("PowerShell env var append", "PowerShell", "$env:PATH += ';x'", _LAX, "assign"),
    (
        "PowerShell encoding variable then python",
        "PowerShell",
        "$env:" + _ENCODING_VARIABLE + "='utf-8'; python x.py",
        _LAX,
        "assign",
    ),
    (
        "PowerShell $Env: with a capital E",
        "PowerShell",
        "$Env:X='1'; ls",
        _LAX,
        "assign",
    ),
    ("PowerShell $ENV: in upper case", "PowerShell", "$ENV:X = 1; ls", _LAX, "assign"),
    ("PowerShell braced ${env:X}", "PowerShell", "${env:X}='1'; ls", _LAX, "assign"),
    (
        "PowerShell braced upper-case with an operator",
        "PowerShell",
        "${ENV:Path} += ';x'",
        _LAX,
        "assign",
    ),
    (
        "PowerShell braced name with a parenthesis",
        "PowerShell",
        "${env:ProgramFiles(x86)} = 'x'",
        _LAX,
        "assign",
    ),
    (
        "PowerShell $Env: read",
        "PowerShell",
        "Write-Output $Env:USERPROFILE",
        _LAX,
        "allow",
    ),
    (
        "PowerShell braced read",
        "PowerShell",
        "Write-Output ${env:USERPROFILE}",
        _LAX,
        "allow",
    ),
    ("PowerShell braced comparison", "PowerShell", "${env:X} -eq 1", _LAX, "allow"),
    (
        "PowerShell $Env: comparison in an if",
        "PowerShell",
        "if ($Env:X -eq 1) { ls }",
        _LAX,
        "allow",
    ),
    (
        "PowerShell comparison is not an assignment",
        "PowerShell",
        "$a -eq 1",
        _LAX,
        "allow",
    ),
    (
        "PowerShell member access is not an assignment",
        "PowerShell",
        "$x.Length",
        _LAX,
        "allow",
    ),
    (
        "PowerShell call by variable path",
        "PowerShell",
        "$env:USERPROFILE\\tools\\run.ps1",
        _LAX,
        "allow",
    ),
    (
        "PowerShell assignment after a statement",
        "PowerShell",
        "ls; $env:X = 1",
        _LAX,
        "allowed:later-assignment",
    ),
    (
        "PowerShell Set-Location -Path abs",
        "PowerShell",
        f"Set-Location -Path {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location -LiteralPath abs",
        "PowerShell",
        f"Set-Location -LiteralPath {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    ("PowerShell sl abs", "PowerShell", f"sl {_DRIVE}\\x", _LAX, "move"),
    ("PowerShell chdir abs", "PowerShell", f"chdir {_DRIVE}\\x", _LAX, "move"),
    (
        "PowerShell Set-Location variable",
        "PowerShell",
        "Set-Location $PSScriptRoot",
        _LAX,
        "move",
    ),
    ("PowerShell Set-Location home", "PowerShell", "Set-Location ~", _LAX, "move"),
    (
        "PowerShell Set-Location after a statement",
        "PowerShell",
        f"Get-ChildItem; Set-Location {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location in a script block",
        "PowerShell",
        f"if ($true) {{ Set-Location {_DRIVE}\\x }}",
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location on the next line",
        "PowerShell",
        f"Get-ChildItem\nSet-Location {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell Push-Location abs",
        "PowerShell",
        f"Push-Location {_DRIVE}\\x; ls",
        _LAX,
        "move",
    ),
    ("PowerShell pushd abs", "PowerShell", f"pushd {_DRIVE}\\x; ls", _LAX, "move"),
    (
        "PowerShell Set-Location piped to Out-Null",
        "PowerShell",
        f"Set-Location {_DRIVE}\\x | Out-Null",
        _LAX,
        "move",
    ),
    (
        "PowerShell a block of another command",
        "PowerShell",
        f"ForEach-Object {{ Set-Location {_DRIVE}\\x }}",
        _LAX,
        "move",
    ),
    (
        "PowerShell a call operator before the mover",
        "PowerShell",
        f"& Set-Location {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell a mover in parentheses",
        "PowerShell",
        f"(Set-Location {_DRIVE}\\x)",
        _LAX,
        "move",
    ),
    (
        "PowerShell a mover in a subexpression",
        "PowerShell",
        f"$(Set-Location {_DRIVE}\\x)",
        _LAX,
        "move",
    ),
    (
        "PowerShell a mover in two pairs of parentheses",
        "PowerShell",
        f"((Set-Location {_DRIVE}\\x))",
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location with a parenthesised target",
        "PowerShell",
        "Set-Location (Join-Path $PWD 'x')",
        _LAX,
        "move",
    ),
    (
        "PowerShell cd with a parenthesised target",
        "PowerShell",
        f"cd (Resolve-Path {_DRIVE}\\x)",
        _LAX,
        "move",
    ),
    (
        "PowerShell Set-Location with a subexpression target",
        "PowerShell",
        "Set-Location $(Get-Location).Path",
        _LAX,
        "move",
    ),
    (
        "PowerShell -Path with a parenthesised value",
        "PowerShell",
        "Set-Location -Path (Join-Path $a $b)",
        _LAX,
        "move",
    ),
    (
        "PowerShell -Path:value",
        "PowerShell",
        f"Set-Location -Path:{_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell -LiteralPath:value",
        "PowerShell",
        f"Set-Location -LiteralPath:{_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell -Path:$variable",
        "PowerShell",
        "Set-Location -Path:$target",
        _LAX,
        "move",
    ),
    (
        "PowerShell -Path: with a space before the value",
        "PowerShell",
        f"Set-Location -Path: {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell -Path:.. is relative",
        "PowerShell",
        "Set-Location -Path:..",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "PowerShell -LiteralPath:.\\sub is relative",
        "PowerShell",
        "Set-Location -LiteralPath:.\\sub",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "PowerShell Set-Location relative",
        "PowerShell",
        "Set-Location ..",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "PowerShell Set-Location relative name",
        "PowerShell",
        "Set-Location backend; ls",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "PowerShell Set-Location a dotted name",
        "PowerShell",
        "Set-Location .ai",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "PowerShell Set-Location an at sign inside a name",
        "PowerShell",
        "Set-Location a@b",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "PowerShell Set-Location with no path",
        "PowerShell",
        "Set-Location",
        _LAX,
        "allowed:ps-bare-set-location",
    ),
    (
        "PowerShell bare Set-Location then a statement",
        "PowerShell",
        "Set-Location; Get-ChildItem",
        _LAX,
        "allowed:ps-bare-set-location",
    ),
    (
        "PowerShell Set-Location -PassThru has no target",
        "PowerShell",
        "Set-Location -PassThru",
        _LAX,
        "allowed:ps-bare-set-location",
    ),
    (
        "PowerShell a registry provider path",
        "PowerShell",
        "Set-Location HKLM:/Software",
        _LAX,
        "move",
    ),
    ("PowerShell the Env provider", "PowerShell", "Set-Location Env:", _LAX, "move"),
    ("PowerShell a quoted provider", "PowerShell", "Set-Location 'Env:'", _LAX, "move"),
    (
        "PowerShell -Path with a provider path",
        "PowerShell",
        "Set-Location -Path HKLM:/Software",
        _LAX,
        "move",
    ),
    (
        "PowerShell a provider-qualified path",
        "PowerShell",
        f"Set-Location FileSystem::{_DRIVE}\\Windows",
        _LAX,
        "move",
    ),
    (
        "PowerShell an array expression",
        "PowerShell",
        "Set-Location @('x')",
        _LAX,
        "move",
    ),
    ("PowerShell splatted arguments", "PowerShell", "Set-Location @args", _LAX, "move"),
    (
        "PowerShell a provider path given to a command that is not a mover",
        "PowerShell",
        "Get-ChildItem HKLM:/Software",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a parenthesis after a command that is not a mover",
        "PowerShell",
        "Get-ChildItem (Join-Path $a 'b')",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a subexpression after a command that is not a mover",
        "PowerShell",
        "Write-Output $(Get-Location).Path",
        _LAX,
        "allow",
    ),
    (
        "PowerShell here-string naming cd",
        "PowerShell",
        f"Write-Output @'\ncd {_DRIVE}\\x\n'@",
        _LAX,
        "allow",
    ),
    (
        "PowerShell here-string, then a real mover",
        "PowerShell",
        f"Write-Output @'\ncd x\n'@\nSet-Location {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell string naming Set-Location",
        "PowerShell",
        f'Write-Output "Set-Location {_DRIVE}\\x"',
        _LAX,
        "allow",
    ),
    (
        "PowerShell single-quoted string naming a mover",
        "PowerShell",
        f"Write-Output 'Set-Location {_DRIVE}\\x'",
        _LAX,
        "allow",
    ),
    (
        "PowerShell block comment naming cd",
        "PowerShell",
        f"<# Set-Location {_DRIVE}\\x #>\nGet-ChildItem",
        _LAX,
        "allow",
    ),
    (
        "PowerShell line comment naming cd",
        "PowerShell",
        f"Get-ChildItem # Set-Location {_DRIVE}\\x",
        _LAX,
        "allow",
    ),
    (
        "PowerShell backtick continuation then a mover",
        "PowerShell",
        f"Get-ChildItem `\n; Set-Location {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell a statement after a block comment",
        "PowerShell",
        f"<# note #> Set-Location {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    # keywords that only introduce the command that follows them
    (
        "cd abs as the else branch of an if",
        "Bash",
        "if true; then ls; else cd /x; fi",
        _LAX,
        "move",
    ),
    (
        "cd abs as the condition of an elif",
        "Bash",
        "if false; then ls; elif cd /x; then ls; fi",
        _LAX,
        "move",
    ),
    (
        "cd abs as the condition of a while loop",
        "Bash",
        "while cd /x; do :; done",
        _LAX,
        "move",
    ),
    (
        "cd abs as the condition of an until loop",
        "Bash",
        "until cd /x; do :; done",
        _LAX,
        "move",
    ),
    ("cd abs in a case branch", "Bash", "case x in a) cd /x;; esac", _LAX, "move"),
    # a redirect that names a descriptor is not a background job
    ("cd then a descriptor redirect", "Bash", "cd /x 2>&1; ls", _LAX, "move"),
    (
        "cd then a descriptor sent to a file",
        "Bash",
        "cd /x 2>/dev/null; ls",
        _LAX,
        "move",
    ),
    # env options that take an argument, and env with nothing to assign
    (
        "env --chdir DIR then an assignment",
        "Bash",
        "env --chdir /x F=1 ls",
        _LAX,
        "assign",
    ),
    ("env -a NAME then an assignment", "Bash", "env -a name F=1 ls", _LAX, "assign"),
    (
        "env --argv0 NAME then an assignment",
        "Bash",
        "env --argv0 n F=1 ls",
        _LAX,
        "assign",
    ),
    ("env -S STRING then an assignment", "Bash", "env -S x F=1 ls", _LAX, "assign"),
    (
        "env --split-string STRING then an assignment",
        "Bash",
        "env --split-string x F=1 ls",
        _LAX,
        "assign",
    ),
    ("a bare env prints the environment", "Bash", "env", _LAX, "allow"),
    (
        "env with a command first: the assignment is its argument",
        "Bash",
        "env ls F=1",
        _LAX,
        "allow",
    ),
    # the shapes of an assignment name
    ("an assignment name with a digit", "Bash", "F1=1 ls", _LAX, "assign"),
    (
        "an assignment name with a leading underscore",
        "Bash",
        "_F=1 ls",
        _LAX,
        "assign",
    ),
    (
        "an assignment name with an underscore inside",
        "Bash",
        "F_1=1 ls",
        _LAX,
        "assign",
    ),
    # PowerShell parameters, parentheses, pipes, here-strings, comments and strings
    (
        "PowerShell -PSPath:value",
        "PowerShell",
        f"Set-Location -PSPath:{_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell -PSPath value",
        "PowerShell",
        f"Set-Location -PSPath {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell an abbreviated parameter with a space before its value",
        "PowerShell",
        f"Set-Location -Pat {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell a mover in an array expression",
        "PowerShell",
        f"@(Set-Location {_DRIVE}\\x)",
        _LAX,
        "move",
    ),
    (
        "PowerShell a mover in parentheses with spaces",
        "PowerShell",
        f"( Set-Location {_DRIVE}\\x )",
        _LAX,
        "move",
    ),
    (
        "PowerShell a mover on the right of a pipe",
        "PowerShell",
        f"Write-Output hi | Set-Location {_DRIVE}\\x",
        _LAX,
        "move",
    ),
    (
        "PowerShell a double-quoted here-string body naming a mover is data",
        "PowerShell",
        f'Write-Output @"\nSet-Location {_DRIVE}\\x\n"@',
        _LAX,
        "allow",
    ),
    (
        "PowerShell a double-quoted here-string, then a real mover",
        "PowerShell",
        f'Write-Output @"\nx\n"@\nSet-Location {_DRIVE}\\x',
        _LAX,
        "move",
    ),
    (
        "PowerShell a single-quoted here-string body holding a quote and a separator",
        "PowerShell",
        f"Write-Output @'\nit's; Set-Location {_DRIVE}\\x\n'@",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a double-quoted here-string body holding a quote and a separator",
        "PowerShell",
        f'Write-Output @"\nit"s; Set-Location {_DRIVE}\\x\n"@',
        _LAX,
        "allow",
    ),
    (
        "PowerShell a CRLF continuation joins the next line to the command",
        "PowerShell",
        f"Write-Output a `\r\n  cd {_DRIVE}\\x",
        _LAX,
        "allow",
    ),
    (
        "a CRLF continuation joins the next line to the command",
        "Bash",
        "echo a \\\r\n  cd /x",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a comment holding a separator and a mover",
        "PowerShell",
        f"Get-ChildItem # a; Set-Location {_DRIVE}\\x",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a double-quoted string holding a separator and a mover",
        "PowerShell",
        f'Write-Output "a; Set-Location {_DRIVE}\\x"',
        _LAX,
        "allow",
    ),
    (
        "PowerShell a single-quoted string holding a separator and a mover",
        "PowerShell",
        f"Write-Output 'a; Set-Location {_DRIVE}\\x'",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a CRLF continuation inside an ordinary command",
        "PowerShell",
        "Get-ChildItem `\r\n  -Force\r\nGet-Location",
        _LAX,
        "allow",
    ),
    # heredocs and continuations with CRLF line endings
    (
        "a heredoc with CRLF line endings, then a cd",
        "Bash",
        "cat <<EOF\r\ncd /x\r\nEOF\r\ncd /y",
        _LAX,
        "move",
    ),
    (
        "a heredoc with CRLF line endings: the body naming cd is data",
        "Bash",
        "cat <<EOF\r\ncd /x\r\nEOF\r\n",
        _LAX,
        "allow",
    ),
    (
        "a CRLF continuation inside an ordinary command",
        "Bash",
        "ls \\\r\n  -la\r\ngit status",
        _LAX,
        "allow",
    ),
    # what the shell itself does with two shapes that look like holes: both are right to allow
    (
        "an unquoted shift in let is a heredoc to the shell too",
        "Bash",
        "let x=1<<2\ncd /x",
        _LAX,
        "allow",
    ),
    (
        "command takes FOO=1 for a command name, not an assignment",
        "Bash",
        "command FOO=1 ls",
        _LAX,
        "allow",
    ),
    # a backtick target, and shadows in their other spellings
    ("cd with a backtick target", "Bash", "cd `pwd`", _LAX, "move"),
    (
        "alias with -- before the name",
        "Bash",
        "alias -- cd=true; ls",
        _LAX,
        "shadow",
    ),
    (
        "PowerShell Function with a capital F",
        "PowerShell",
        "Function cd { }; ls",
        _LAX,
        "shadow",
    ),
    (
        "PowerShell a function named CD",
        "PowerShell",
        "function CD { }; ls",
        _LAX,
        "shadow",
    ),
    (
        "a Bash function named CD is not cd",
        "Bash",
        "function CD { :; }; ls",
        _LAX,
        "allow",
    ),
    # `--` ends the options: what follows is the folder, even when it starts with a dash
    (
        "cd -- with a dash-led relative folder",
        "Bash",
        "cd -- -x",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "cd -- with a lone dash is the previous directory",
        "Bash",
        "cd -- -",
        _LAX,
        "move",
    ),
    ("cd -- with no folder goes home", "Bash", "cd --", _LAX, "move"),
    # a hash is a comment only at the start of a word: after `)` of a substitution it is not one
    (
        "a hash glued after a command substitution is not a comment",
        "Bash",
        "echo $(true)#x; cd /x",
        _LAX,
        "move",
    ),
    (
        "a hash glued after an arithmetic expansion is not a comment",
        "Bash",
        "echo $((1))#x; cd /x",
        _LAX,
        "move",
    ),
    (
        "a hash glued after a process substitution is not a comment",
        "Bash",
        "echo <(true)#x; cd /x",
        _LAX,
        "move",
    ),
    (
        "a hash after a closed substitution and a space is a comment",
        "Bash",
        "echo $(true) #x; cd /x",
        _LAX,
        "allow",
    ),
]

# ------------------------------------------------- ordinary work the hook must never fire on

_ORDINARY: list[Row] = [
    ("git status", "Bash", "git --no-optional-locks status --porcelain", _LAX, "allow"),
    ("git diff", "Bash", "git --no-optional-locks diff HEAD --stat", _LAX, "allow"),
    (
        "uv run pytest",
        "Bash",
        'uv run --no-project --python ">=3.11" --with pytest python -B -m pytest x -q',
        _LAX,
        "allow",
    ),
    ("grep -c -F", "Bash", 'grep -c -F "x" file', _LAX, "allow"),
    ("tr with octal", "Bash", "tr -cd '\\010' < file | wc -c", _LAX, "allow"),
    ("bash a script", "Bash", "bash scripts/run.sh", _LAX, "allow"),
    ("venv ruff", "Bash", ".venv/Scripts/ruff.exe check f.py", _LAX, "allow"),
    ("diff to a file", "Bash", "diff -U0 a b > out", _LAX, "allow"),
    ("printf", "Bash", "printf '%s\\n' x", _LAX, "allow"),
    ("a for loop without cd", "Bash", "for f in a b; do echo $f; done", _LAX, "allow"),
    ("a while read loop", "Bash", "while read l; do echo $l; done < f", _LAX, "allow"),
    ("a redirect with a descriptor", "Bash", "ls nope 2>&1 | head", _LAX, "allow"),
    (
        "a case statement without cd",
        "Bash",
        "case $x in a) echo a;; esac",
        _LAX,
        "allow",
    ),
    ("find with -exec", "Bash", "find . -name '*.py' -exec wc -l {} +", _LAX, "allow"),
    ("a here-string", "Bash", 'grep x <<< "$v"', _LAX, "allow"),
    ("a heredoc to a file", "Bash", "cat > f <<'EOF'\nline\nEOF\nls", _LAX, "allow"),
    (
        "a quoted path with spaces as an argument",
        "Bash",
        'ls "/some dir/x"',
        _LAX,
        "allow",
    ),
    (
        "PowerShell guard status",
        "PowerShell",
        '& "$env:USERPROFILE\\tools\\status.ps1"',
        _LAX,
        "allow",
    ),
    (
        "PowerShell Get-FileHash",
        "PowerShell",
        "Get-FileHash -Algorithm SHA256 -LiteralPath x",
        _LAX,
        "allow",
    ),
    ("PowerShell Get-ChildItem", "PowerShell", "Get-ChildItem", _LAX, "allow"),
    (
        "PowerShell a pipeline",
        "PowerShell",
        "Get-ChildItem | Where-Object { $_.Length -gt 1 }",
        _LAX,
        "allow",
    ),
    (
        "PowerShell a foreach over a list",
        "PowerShell",
        "foreach ($f in Get-ChildItem) { $f.Name }",
        _LAX,
        "allow",
    ),
]

# ----------------------------------------------------- shapes the hook does not cover, pinned

_LIMITS: list[Row] = [
    ("eval of a move", "Bash", 'eval "cd /x"', _LAX, "allowed:eval-string"),
    ("eval of a later move", "Bash", 'eval "ls; cd /x"', _LAX, "allowed:eval-string"),
    (
        "Invoke-Expression of a move",
        "PowerShell",
        f"Invoke-Expression 'Set-Location {_DRIVE}\\x'",
        _LAX,
        "allowed:eval-string",
    ),
    (
        "iex of a move",
        "PowerShell",
        f'iex "Set-Location {_DRIVE}\\x"',
        _LAX,
        "allowed:eval-string",
    ),
    ("a sourced script", "Bash", "source ./moves.sh", _LAX, "allowed:sourced-script"),
    ("a dot-sourced script", "Bash", ". ./moves.sh", _LAX, "allowed:sourced-script"),
    (
        "a mover fed by a PowerShell pipeline",
        "PowerShell",
        "Get-Item .ai | Set-Location",
        _LAX,
        "allowed:ps-pipeline-mover",
    ),
    (
        "a mover command held in a variable",
        "Bash",
        'ls; "$c" /x',
        _LAX,
        "allowed:variable-held-command",
    ),
    ("popd", "Bash", "popd", _LAX, "allowed:other-mover-spelling"),
    (
        "Pop-Location",
        "PowerShell",
        "Pop-Location",
        _LAX,
        "allowed:other-mover-spelling",
    ),
    (
        "a PowerShell alias of Set-Location",
        "PowerShell",
        f"Set-Alias go Set-Location; go {_DRIVE}\\x",
        _LAX,
        "allowed:other-mover-spelling",
    ),
    (
        "Start-Job runs another process but is judged as a block",
        "PowerShell",
        f"Start-Job {{ cd {_DRIVE}\\x }}",
        _LAX,
        "refused:ps-job-block",
    ),
    # spellings of a mover or of its parameter that the hook does not read
    (
        "PowerShell cd glued to a backslash",
        "PowerShell",
        "cd\\",
        _LAX,
        "allowed:other-mover-spelling",
    ),
    (
        "PowerShell cd glued to two dots",
        "PowerShell",
        "cd..",
        _LAX,
        "allowed:other-mover-spelling",
    ),
    (
        "PowerShell a backtick before an escape letter breaks the name, and the call is refused",
        "PowerShell",
        f"Set-Loc`ation {_DRIVE}\\x",
        _LAX,
        "refused:ps-escape-letter-in-name",
    ),
    (
        "PowerShell an abbreviated parameter bound to its value by a colon",
        "PowerShell",
        f"Set-Location -Pat:{_DRIVE}\\x",
        _LAX,
        "allowed:other-mover-spelling",
    ),
    (
        "PowerShell a function named with a scope prefix",
        "PowerShell",
        "function global:cd { }; ls",
        _LAX,
        "allowed:other-mover-spelling",
    ),
    (
        "PowerShell a function that redefines Set-Location",
        "PowerShell",
        "function Set-Location { }; ls",
        _LAX,
        "allowed:other-mover-spelling",
    ),
    # a target quoted in the ANSI-C style, written with an escape sequence
    (
        "an ANSI-C target that writes its slash as a hex escape",
        "Bash",
        "cd $'\\x2fx'",
        _LAX,
        "allowed:ansi-c-target",
    ),
    (
        "an ANSI-C target that writes its slash as an octal escape",
        "Bash",
        "cd $'\\057x'",
        _LAX,
        "allowed:ansi-c-target",
    ),
    # a shift in the legacy arithmetic expansion reads as the start of a heredoc
    (
        "a legacy arithmetic expansion with a shift hides the next line",
        "Bash",
        "echo $[1<<2]\ncd /x",
        _LAX,
        "allowed:non-heredoc-shift",
    ),
    # an assignment that is the real first word of the command but not the first word of the text
    (
        "an assignment after a comment line",
        "Bash",
        "# note\nFOO=1 cmd",
        _LAX,
        "allowed:unread-leading-assignment",
    ),
    (
        "an assignment after time",
        "Bash",
        "time FOO=1 ls",
        _LAX,
        "allowed:unread-leading-assignment",
    ),
    (
        "an assignment after sudo",
        "Bash",
        "sudo FOO=1 ls",
        _LAX,
        "allowed:unread-leading-assignment",
    ),
    (
        "env -S with an assignment inside its string",
        "Bash",
        "env -S 'F=1 cmd'",
        _LAX,
        "allowed:unread-leading-assignment",
    ),
    (
        "PowerShell an assignment in parentheses",
        "PowerShell",
        "($env:X = 1); ls",
        _LAX,
        "allowed:unread-leading-assignment",
    ),
    (
        "PowerShell Set-Item on the Env provider",
        "PowerShell",
        "Set-Item Env:X 1",
        _LAX,
        "allowed:unread-leading-assignment",
    ),
    # a disguise reached through a path, command, builtin or a backslash is not read as one
    (
        "env called by its path then an assignment",
        "Bash",
        "/usr/bin/env X=1 cmd",
        _LAX,
        "allowed:wrapped-disguise",
    ),
    (
        "command env then an assignment",
        "Bash",
        "command env X=1 cmd",
        _LAX,
        "allowed:wrapped-disguise",
    ),
    (
        "command export then an assignment",
        "Bash",
        "command export A=1; make",
        _LAX,
        "allowed:wrapped-disguise",
    ),
    (
        "builtin export then an assignment",
        "Bash",
        "builtin export A=1; make",
        _LAX,
        "allowed:wrapped-disguise",
    ),
    (
        "a backslash before export then an assignment",
        "Bash",
        "\\export A=1; make",
        _LAX,
        "allowed:wrapped-disguise",
    ),
    (
        "command declare -x then an assignment",
        "Bash",
        "command declare -x A=1; make",
        _LAX,
        "allowed:wrapped-disguise",
    ),
    # a PowerShell mover that is not the first word of its statement
    (
        "PowerShell a mover after an assignment to $null",
        "PowerShell",
        f"$null = Set-Location {_DRIVE}\\x",
        _LAX,
        "allowed:ps-mover-not-first-word",
    ),
    (
        "PowerShell a mover inside a cast to void",
        "PowerShell",
        f"[void](Set-Location {_DRIVE}\\x)",
        _LAX,
        "allowed:ps-mover-not-first-word",
    ),
    (
        "PowerShell a mover as the parenthesised argument of another command",
        "PowerShell",
        f"Write-Output (Set-Location {_DRIVE}\\x)",
        _LAX,
        "allowed:ps-mover-not-first-word",
    ),
    (
        "PowerShell a mover as the condition of an if",
        "PowerShell",
        f"if (Set-Location {_DRIVE}\\x) {{ ls }}",
        _LAX,
        "allowed:ps-mover-not-first-word",
    ),
    # a backslash or a backtick before a newline is removed before the text is read
    (
        "a comment that ends in a backslash",
        "Bash",
        "# note \\\ncd /x",
        _LAX,
        "allowed:continuation-context",
    ),
    (
        "an escaped backslash before a newline",
        "Bash",
        "echo a \\\\\ncd /x",
        _LAX,
        "allowed:continuation-context",
    ),
    (
        "PowerShell a comment that ends in a backtick",
        "PowerShell",
        f"# note `\nSet-Location {_DRIVE}\\x",
        _LAX,
        "allowed:continuation-context",
    ),
    (
        "PowerShell a doubled backtick before a newline",
        "PowerShell",
        f"Write-Output a ``\nSet-Location {_DRIVE}\\x",
        _LAX,
        "allowed:continuation-context",
    ),
    # a hash glued after the `)` that closes a subshell is a comment to the shell
    (
        "a hash glued after the closing parenthesis of a subshell",
        "Bash",
        "(true)#x; cd /x",
        _LAX,
        "refused:glued-hash-after-paren",
    ),
    (
        "a hash glued after a stray closing parenthesis",
        "Bash",
        "echo a)#x; cd /x",
        _LAX,
        "refused:glued-hash-after-paren",
    ),
]

# --------------------------------------------------------------------- the options, on and off

_OPTION_ROWS: list[Row] = [
    (
        "no options: a relative cd is allowed",
        "Bash",
        "cd backend && ls",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "deny_relative_cd denies a relative cd",
        "Bash",
        "cd backend && ls",
        _RELATIVE_CD,
        "move",
    ),
    ("deny_relative_cd denies cd ..", "Bash", "cd .. && ls", _RELATIVE_CD, "move"),
    (
        "deny_relative_cd denies a later relative cd",
        "Bash",
        "ls && cd backend",
        _RELATIVE_CD,
        "move",
    ),
    (
        "deny_relative_cd denies pushd with a relative target",
        "Bash",
        "pushd backend",
        _RELATIVE_CD,
        "move",
    ),
    (
        "deny_relative_cd denies a PowerShell cd",
        "PowerShell",
        "cd backend; ls",
        _RELATIVE_CD,
        "move",
    ),
    (
        "deny_relative_cd leaves cd . alone",
        "Bash",
        "cd . && ls",
        _RELATIVE_CD,
        "allowed:cd-dot",
    ),
    (
        "deny_relative_cd still allows a subshell",
        "Bash",
        "(cd backend && ls)",
        _RELATIVE_CD,
        "allowed:subshell-cd",
    ),
    (
        "deny_relative_cd does not cover the Set-Location spelling",
        "PowerShell",
        "Set-Location backend",
        _RELATIVE_CD,
        "allowed:relative-cd",
    ),
    (
        "no options: a relative Set-Location is allowed",
        "PowerShell",
        "Set-Location backend",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "deny_set_location denies a relative Set-Location",
        "PowerShell",
        "Set-Location backend",
        _SET_LOCATION,
        "move",
    ),
    ("deny_set_location denies sl ..", "PowerShell", "sl ..", _SET_LOCATION, "move"),
    (
        "deny_set_location denies Push-Location",
        "PowerShell",
        "Push-Location backend",
        _SET_LOCATION,
        "move",
    ),
    (
        "deny_set_location denies -Path with a relative value",
        "PowerShell",
        "Set-Location -Path backend",
        _SET_LOCATION,
        "move",
    ),
    (
        "deny_set_location leaves a bare Set-Location alone",
        "PowerShell",
        "Set-Location",
        _SET_LOCATION,
        "allowed:ps-bare-set-location",
    ),
    (
        "deny_set_location does not cover the cd spelling",
        "PowerShell",
        "cd backend",
        _SET_LOCATION,
        "allowed:relative-cd",
    ),
    (
        "deny_set_location does not touch a Bash cd",
        "Bash",
        "cd backend && ls",
        _SET_LOCATION,
        "allowed:relative-cd",
    ),
    (
        "no options: a PowerShell local variable is allowed",
        "PowerShell",
        "$x = 1; ls",
        _LAX,
        "allowed:ps-local-variable",
    ),
    (
        "deny_powershell_assignment denies $x = 1",
        "PowerShell",
        "$x = 1; ls",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies $x=1",
        "PowerShell",
        "$x=1",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies a preference variable",
        "PowerShell",
        "$ErrorActionPreference = 'Stop'",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies $x += 1",
        "PowerShell",
        "$x += 1; $x",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies a scoped variable",
        "PowerShell",
        "$script:x = 1",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies a typed variable",
        "PowerShell",
        "[int]$x = 1",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment leaves a comparison alone",
        "PowerShell",
        "$a -eq 1",
        _PS_ASSIGN,
        "allow",
    ),
    (
        "deny_powershell_assignment leaves member access alone",
        "PowerShell",
        "$x.Length",
        _PS_ASSIGN,
        "allow",
    ),
    (
        "deny_powershell_assignment leaves a later assignment alone",
        "PowerShell",
        "ls; $x = 1",
        _PS_ASSIGN,
        "allowed:later-assignment",
    ),
    (
        "deny_powershell_assignment does not touch Bash",
        "Bash",
        "ls",
        _PS_ASSIGN,
        "allow",
    ),
    (
        "deny_powershell_assignment denies a Script-scoped variable in capitals",
        "PowerShell",
        "$Script:x = 1",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies a Global-scoped variable in capitals",
        "PowerShell",
        "$GLOBAL:y = 2",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies a Local-scoped variable",
        "PowerShell",
        "$local:z = 3",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies a Private-scoped variable",
        "PowerShell",
        "$private:w = 4",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment denies a Using-scoped variable",
        "PowerShell",
        "$using:u = 5",
        _PS_ASSIGN,
        "assign",
    ),
    (
        "deny_powershell_assignment does not read a multiple assignment",
        "PowerShell",
        "$a, $b = 1, 2",
        _PS_ASSIGN,
        "allowed:ps-local-variable",
    ),
    (
        "deny_powershell_assignment does not read Set-Variable",
        "PowerShell",
        "Set-Variable x 1",
        _PS_ASSIGN,
        "allowed:ps-local-variable",
    ),
    (
        "deny_powershell_assignment does not read New-Variable",
        "PowerShell",
        "New-Variable x 1",
        _PS_ASSIGN,
        "allowed:ps-local-variable",
    ),
    (
        "deny_relative_cd leaves cd ./ alone",
        "Bash",
        "cd ./ && ls",
        _RELATIVE_CD,
        "allowed:cd-dot",
    ),
    (
        "deny_relative_cd denies a dash-led relative folder after --",
        "Bash",
        "cd -- -x",
        _RELATIVE_CD,
        "move",
    ),
    (
        "enabled false: nothing is judged",
        "Bash",
        "cd /x && FOO=bar ls",
        _OFF,
        "allow",
    ),
]

# --------------------------------------------------- the strict project and the allowed forms

_STRICT_ROWS: list[Row] = [
    (
        "strict: the relative spelling of the one form",
        "Bash",
        "cd app-dir && build-tool test",
        _STRICT,
        "allow",
    ),
    (
        "strict: a trailing slash",
        "Bash",
        "cd app-dir/ && build-tool test",
        _STRICT,
        "allow",
    ),
    (
        "strict: a quoted folder",
        "Bash",
        'cd "app-dir" && build-tool test',
        _STRICT,
        "allow",
    ),
    (
        "strict: the absolute spelling",
        "Bash",
        "cd {root}/app-dir && build-tool test",
        _STRICT,
        "allow",
    ),
    (
        "strict: the absolute spelling with a trailing slash",
        "Bash",
        "cd {root}/app-dir/ && build-tool test",
        _STRICT,
        "allow",
    ),
    (
        "strict: the absolute spelling, quoted, with backslashes",
        "Bash",
        'cd "{root_backslash}\\app-dir" && build-tool test',
        _STRICT,
        "allow",
    ),
    (
        "strict: the absolute spelling with the drive letter in the other case",
        "Bash",
        "cd {root_drive_flipped}/app-dir && build-tool test",
        _STRICT,
        "allow",
    ),
    (
        "strict: the word followed by a pipe",
        "Bash",
        "cd app-dir && build-tool test | tail -5",
        _STRICT,
        "allow",
    ),
    (
        "strict: a later plain statement is judged on its own",
        "Bash",
        "cd app-dir && build-tool test\nls",
        _STRICT,
        "allow",
    ),
    (
        "strict: a later plain statement after &&",
        "Bash",
        "cd app-dir && build-tool test && echo done",
        _STRICT,
        "allow",
    ),
    (
        "strict: a third spelling, ./",
        "Bash",
        "cd ./app-dir && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a .. spelling of the folder",
        "Bash",
        "cd app-dir/../app-dir && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a .. spelling of the absolute folder",
        "Bash",
        "cd {root}/app-dir/../app-dir && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a .. spelling that reaches the folder from a sibling",
        "Bash",
        "cd {root}/other/../app-dir && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a different command word",
        "Bash",
        "cd app-dir && other-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a different folder",
        "Bash",
        "cd other-dir && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a folder that only starts with the name",
        "Bash",
        "cd {root}/app-dir-two && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a subfolder of the folder",
        "Bash",
        "cd app-dir/sub && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: the folder name in another case",
        "Bash",
        "cd APP-DIR && build-tool test",
        _STRICT,
        "move",
    ),
    ("strict: the form without its command", "Bash", "cd app-dir", _STRICT, "move"),
    (
        "strict: an extra word after the folder",
        "Bash",
        "cd app-dir extra && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a semicolon instead of &&",
        "Bash",
        "cd app-dir; build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: || instead of &&",
        "Bash",
        "cd app-dir || build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a trailing cd after a semicolon",
        "Bash",
        "cd app-dir && build-tool test; cd /x",
        _STRICT,
        "move",
    ),
    (
        "strict: a trailing cd after &&",
        "Bash",
        "cd app-dir && build-tool test && cd /x",
        _STRICT,
        "move",
    ),
    (
        "strict: a trailing relative cd on the next line",
        "Bash",
        "cd app-dir && build-tool test\ncd other-dir",
        _STRICT,
        "move",
    ),
    (
        "strict: the form after another statement",
        "Bash",
        "ls && cd app-dir && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: the form inside a brace group",
        "Bash",
        "{ cd app-dir && build-tool test; }",
        _STRICT,
        "move",
    ),
    (
        "strict: the form in the PowerShell tool",
        "PowerShell",
        "cd app-dir; build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: Set-Location in the PowerShell tool",
        "PowerShell",
        "Set-Location app-dir",
        _STRICT,
        "move",
    ),
    ("strict: sl in the PowerShell tool", "PowerShell", "sl app-dir", _STRICT, "move"),
    (
        "strict: an absolute cd with the allowed command",
        "Bash",
        "cd /x && build-tool test",
        _STRICT,
        "move",
    ),
    (
        "strict: a leading assignment",
        "Bash",
        "FOO=bar build-tool test",
        _STRICT,
        "assign",
    ),
    (
        "strict: a PowerShell variable assignment",
        "PowerShell",
        "$x = 1; ls",
        _STRICT,
        "assign",
    ),
    (
        "strict: a PowerShell env assignment",
        "PowerShell",
        "$env:X = 1; ls",
        _STRICT,
        "assign",
    ),
    ("strict: a shadow", "Bash", "cd() { :; }; build-tool test", _STRICT, "shadow"),
    ("strict: an ordinary command", "Bash", "build-tool test", _STRICT, "allow"),
    (
        "strict: git -C with the folder",
        "Bash",
        "git -C app-dir status",
        _STRICT,
        "allow",
    ),
    (
        "a PowerShell form: allowed in the PowerShell tool",
        "PowerShell",
        "cd app-dir && build-tool test",
        _POWERSHELL_FORM,
        "allow",
    ),
    (
        "a PowerShell form: not in the Bash tool",
        "Bash",
        "cd app-dir && build-tool test",
        _POWERSHELL_FORM,
        "move",
    ),
    (
        "two forms: the first folder and its word",
        "Bash",
        "cd app-dir && build-tool test",
        _TWO_FORMS,
        "allow",
    ),
    (
        "two forms: the second folder and its first word",
        "Bash",
        "cd lib-dir && lint-tool x",
        _TWO_FORMS,
        "allow",
    ),
    (
        "two forms: the second folder and its second word",
        "Bash",
        "cd lib-dir && build-tool x",
        _TWO_FORMS,
        "allow",
    ),
    (
        "two forms: the first folder with the second folder's word",
        "Bash",
        "cd app-dir && lint-tool x",
        _TWO_FORMS,
        "move",
    ),
    (
        "strict: a command word that only starts with the listed one",
        "Bash",
        "cd app-dir && build-tool-other test",
        _STRICT,
        "move",
    ),
    (
        "a PowerShell form: CD in capitals is the same command",
        "PowerShell",
        "CD app-dir && build-tool test",
        _POWERSHELL_FORM,
        "allow",
    ),
    (
        "lax: the relative spelling is allowed without any form",
        "Bash",
        "cd app-dir && build-tool test",
        _LAX,
        "allowed:relative-cd",
    ),
    (
        "lax: the absolute spelling is denied",
        "Bash",
        "cd {root}/app-dir && build-tool test",
        _LAX,
        "move",
    ),
]

# ----------------------------------------------------- a file the hook cannot use: allow and warn

_UNUSABLE_ROWS: list[Row] = [
    ("unusable file: not JSON", "Bash", "cd /x && ls", "unusable: not JSON", "warn"),
    (
        "unusable file: an unknown key",
        "Bash",
        "cd /x && ls",
        "unusable: unknown key",
        "warn",
    ),
    (
        "unusable file: a wrong type",
        "Bash",
        "cd /x && ls",
        "unusable: wrong type",
        "warn",
    ),
    (
        "unusable file: a form without then",
        "Bash",
        "cd /x && ls",
        "unusable: form without then",
        "warn",
    ),
    (
        "unusable file: an assignment is allowed too",
        "Bash",
        "FOO=bar ls",
        "unusable: not JSON",
        "warn",
    ),
    (
        "unusable file: a plain command still warns",
        "Bash",
        "ls",
        "unusable: not JSON",
        "warn",
    ),
]

_ALL_ROWS: list[Row] = (
    _CONTROLS
    + _PROBE
    + _FOUND
    + _ORDINARY
    + _LIMITS
    + _OPTION_ROWS
    + _STRICT_ROWS
    + _UNUSABLE_ROWS
)


# ------------------------------------------------------------------------------- the machinery


@cache
def _hook() -> ModuleType:
    """The hook, loaded once from its file (it is a script, not a package)."""
    assert _HOOK.is_file(), f"the hook script does not exist: {_HOOK}"
    spec = importlib.util.spec_from_file_location("gate_shell_prefix", _HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _real_decide(raw: bytes, environ: Mapping[str, str]) -> str:
    return cast(str, _hook().decide(raw, environ))


def _payload(
    tool: str, command: str, cwd: Path | None = None, *, escaped: bool = False
) -> bytes:
    """The PreToolUse payload as UTF-8 bytes; `escaped` writes non-ASCII as \\u escapes instead."""
    body: dict[str, Any] = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"command": command},
    }
    if cwd is not None:
        body["cwd"] = str(cwd)
    return json.dumps(body, ensure_ascii=escaped).encode("utf-8")


def _write_config(project: Path, text: str | bytes | None) -> Path:
    target = project / _CONFIG_RELATIVE
    if text is None:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8") if isinstance(text, str) else text
    target.write_bytes(data)
    return target


def _family(out: str) -> str:
    """Name what the hook said: allow (nothing), warn (a message only) or a denial family."""
    if not out:
        return "allow"
    reply = cast(dict[str, Any], json.loads(out))
    if "hookSpecificOutput" not in reply:
        assert set(reply) == {"systemMessage"}, f"an unexpected reply: {reply}"
        return "warn"
    inner = cast(dict[str, Any], reply["hookSpecificOutput"])
    assert inner["permissionDecision"] == "deny", inner
    reason = str(inner["permissionDecisionReason"])
    for opening, family in _OPENINGS:
        if reason.startswith(opening):
            return family
    raise AssertionError(f"a denial with an unknown opening: {reason[:80]!r}")


def _reason(out: str) -> str:
    reply = cast(dict[str, Any], json.loads(out))
    return str(reply["hookSpecificOutput"]["permissionDecisionReason"])


def _flip_drive_case(path: str) -> str:
    if len(path) > 1 and path[1] == ":":
        return path[0].swapcase() + path[1:]
    return path


def _fill(command: str, project: Path) -> str:
    """The row's command with the project root written in the spellings the strict rows use."""
    root = str(project)
    return (
        command.replace("{root_backslash}", root.replace("/", "\\"))
        .replace("{root_drive_flipped}", _flip_drive_case(project.as_posix()))
        .replace("{root}", project.as_posix())
    )


def _expected(decision: str) -> str:
    """The verdict a row's decision requires: an `allowed:` row allows, a `refused:` row is a move."""
    kind = decision.partition(":")[0]
    if kind == "allowed":
        return "allow"
    if kind == "refused":
        return "move"
    return kind


class _Projects:
    """One project folder per configuration name, each holding that configuration's file."""

    def __init__(self, base: Path) -> None:
        self.paths: dict[str, Path] = {}
        for index, (name, text) in enumerate(_CONFIGS.items()):
            project = base / f"p{index}"
            project.mkdir()
            _write_config(project, text)
            self.paths[name] = project


@pytest.fixture(scope="module")
def projects(tmp_path_factory: pytest.TempPathFactory) -> _Projects:
    return _Projects(tmp_path_factory.mktemp("proj"))


def _verdict(decide: Decide, row: Row, projects: _Projects) -> str:
    _name, tool, command, config, _decision = row
    project = projects.paths[config]
    out = decide(
        _payload(tool, _fill(command, project), project),
        {"CLAUDE_PROJECT_DIR": str(project)},
    )
    return _family(out)


def _failures(decide: Decide, projects: _Projects) -> list[str]:
    """The names of the rows `decide` gets wrong."""
    return [
        row[0]
        for row in _ALL_ROWS
        if _verdict(decide, row, projects) != _expected(row[4])
    ]


# ------------------------------------------------------------------------------- the table


@pytest.mark.parametrize("row", _ALL_ROWS, ids=[row[0] for row in _ALL_ROWS])
def test_the_hook_decides_each_shape(row: Row, projects: _Projects) -> None:
    got = _verdict(_real_decide, row, projects)
    want = _expected(row[4])
    assert got == want, f"{row[0]}: required {want}, got {got}\n{row[2]!r}"


def test_the_three_controls_come_first_and_discriminate(projects: _Projects) -> None:
    assert [row[0] for row in _ALL_ROWS[:3]] == [row[0] for row in _CONTROLS]
    deny, allow, default = _CONTROLS
    assert _verdict(_real_decide, deny, projects) == "move"
    assert _verdict(_real_decide, allow, projects) == "allow"
    assert _verdict(_real_decide, default, projects) == "allow"
    assert deny[2] == default[2], (
        "the default control must be the deny control's own command"
    )
    assert deny[3] != default[3]


def test_the_table_can_fail_both_ways(projects: _Projects) -> None:
    """A table that cannot fail has not been shown to work: run it against two wrong hooks."""

    def allow_everything(_raw: bytes, _environ: Mapping[str, str]) -> str:
        return ""

    def deny_everything(_raw: bytes, _environ: Mapping[str, str]) -> str:
        reply = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": _OPENINGS[0][0] + " (a stub)",
            }
        }
        return json.dumps(reply)

    by_name = {row[0]: row for row in _ALL_ROWS}
    missed = _failures(allow_everything, projects)
    assert missed, "a hook that allows everything passed the whole table"
    assert {by_name[name][4].partition(":")[0] for name in missed} >= {
        "move",
        "shadow",
        "assign",
        "warn",
    }
    assert not {
        name for name in missed if by_name[name][4].startswith(("allow", "allowed"))
    }
    overreached = _failures(deny_everything, projects)
    assert overreached, "a hook that denies everything passed the whole table"
    assert any(
        by_name[name][4] in ("allow", "warn") or by_name[name][4].startswith("allowed")
        for name in overreached
    )
    assert len(overreached) > len(_ALL_ROWS) // 4


def test_the_probe_table_holds_the_fifty_probed_shapes() -> None:
    names = [row[0] for row in _PROBE]
    assert len(_PROBE) == 50 and len(set(names)) == 50
    tally: dict[str, int] = {}
    for row in _PROBE:
        family = _expected(row[4])
        tally[family] = tally.get(family, 0) + 1
    # The original probe allowed 30 of the 50. The hook's decision moves 14 of those to a denial
    # (assignments and moves the first guard did not see), so 18 shapes are moves, 14 are
    # assignments, 2 are shadows and 16 stay allowed.
    assert tally == {"move": 18, "shadow": 2, "assign": 14, "allow": 16}


def test_every_row_name_is_unique() -> None:
    names = [row[0] for row in _ALL_ROWS]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert not duplicates, f"rows share a name: {duplicates}"


def test_every_configuration_a_row_names_exists() -> None:
    unknown = sorted({row[3] for row in _ALL_ROWS} - set(_CONFIGS))
    assert not unknown, f"rows name configurations that do not exist: {unknown}"
    unused = sorted(set(_CONFIGS) - {row[3] for row in _ALL_ROWS})
    assert not unused, f"configurations no row uses: {unused}"


def test_the_table_states_its_own_surface() -> None:
    """Both polarities in both tools, and every denial family, or the table is one-sided."""
    for tool in ("Bash", "PowerShell"):
        decisions = {_expected(row[4]) for row in _ALL_ROWS if row[1] == tool}
        assert {"allow", "move", "assign"} <= decisions, f"{tool}: {sorted(decisions)}"
    assert {"shadow", "warn"} <= {_expected(row[4]) for row in _ALL_ROWS}
    # the strict rows reach the absolute spelling, so the placeholder must be in use
    assert any("{root}" in row[2] for row in _STRICT_ROWS)


def test_the_table_states_its_size_in_numbers() -> None:
    """A table that can lose rows unseen has not said what it covers: every table's size, the total
    and the split by tool are asserted, so a deleted row is a visible change to this test."""
    sizes = {
        "controls": len(_CONTROLS),
        "probe": len(_PROBE),
        "found": len(_FOUND),
        "ordinary": len(_ORDINARY),
        "limits": len(_LIMITS),
        "options": len(_OPTION_ROWS),
        "strict": len(_STRICT_ROWS),
        "unusable": len(_UNUSABLE_ROWS),
    }
    assert sizes == {
        "controls": 3,
        "probe": 50,
        "found": 257,
        "ordinary": 22,
        "limits": 43,
        "options": 39,
        "strict": 48,
        "unusable": 6,
    }
    assert len(_ALL_ROWS) == sum(sizes.values()) == 468
    assert dict(Counter(row[1] for row in _ALL_ROWS)) == {
        "Bash": 304,
        "PowerShell": 164,
    }


# ----------------------------------------------------------- the limits and the hook's header


def _header() -> str:
    tree = ast.parse(_HOOK.read_text(encoding="utf-8"))
    header = ast.get_docstring(tree)
    assert header is not None, "the hook has no header"
    return header


def _header_ids(kind: str) -> set[str]:
    return set(re.findall(rf"^\s*{kind} ([a-z0-9-]+):", _header(), flags=re.MULTILINE))


def test_the_header_and_the_table_name_the_same_limits() -> None:
    """A limit with no written reason looks like a forgotten gap; one with no row looks like a promise."""
    counts: dict[str, int] = {}
    for kind, prefix in (("ALLOWED", "allowed:"), ("REFUSED", "refused:")):
        in_table = {
            row[4][len(prefix) :] for row in _ALL_ROWS if row[4].startswith(prefix)
        }
        in_header = _header_ids(kind)
        assert in_table, f"the table has no {kind} rows"
        assert in_table == in_header, (
            f"{kind}: table-only {sorted(in_table - in_header)}, header-only {sorted(in_header - in_table)}"
        )
        counts[kind] = len(in_header)
    # In numbers too: a limit dropped from the header and from the table together is still a change here.
    assert counts == {"ALLOWED": 24, "REFUSED": 4}, counts


def test_the_header_names_the_switch_file_and_every_key() -> None:
    header = _header()
    assert ".ai/shell-prefix-hook.json" in header
    for key in cast(tuple[str, ...], _hook().CONFIG_KEYS):
        assert key in header, f"the header does not name the key {key!r}"
    assert cast(tuple[str, ...], _hook().CONFIG_KEYS) == (
        "enabled",
        "deny_relative_cd",
        "deny_set_location",
        "deny_powershell_assignment",
        "allowed_forms",
    )


# The sentence about turning the switch on or off while other windows are open. What was recorded
# is one case in another consumer, with the delay not timed; for a plugin registration nothing is
# measured. So it must say that, and it must not state a delay as if it had been measured.
_SWITCH_SENTENCE_PHRASES = (
    "reached windows that were already open",
    "in one recorded case",
    "the delay was not timed",
    "unmeasured",
    "flip the switch when no peer session is mid-task",
)
_SWITCH_SENTENCE_FORBIDDEN = (
    "within about a minute",
    "binds windows that are already open",
)


def _switch_sentence_problems(text: str) -> list[str]:
    flat = " ".join(text.split())
    missing = [f"missing {p!r}" for p in _SWITCH_SENTENCE_PHRASES if p not in flat]
    claimed = [f"must not say {p!r}" for p in _SWITCH_SENTENCE_FORBIDDEN if p in flat]
    return missing + claimed


def test_the_switch_sentence_check_rejects_the_unqualified_claim() -> None:
    """The check is shown to fail: the sentence as first drafted breaks all six of its terms."""
    unqualified = (
        "A hook wired into a settings file binds windows that are already open, within "
        "about a minute, so flip the switch when no peer session is mid-task."
    )
    assert len(_switch_sentence_problems(unqualified)) == 6
    qualified = (
        "A hook wired into a settings file reached windows that were already open, on their "
        "next call, in one recorded case in another consumer: the delay was not timed, and "
        "for a plugin registration it is unmeasured. So flip the switch when no peer "
        "session is mid-task."
    )
    assert _switch_sentence_problems(qualified) == []


def test_the_header_states_what_it_follows_and_the_switch_sentence() -> None:
    header = _header()
    for phrase in (
        "CLAUDE_PLUGIN_ROOT",  # registered through a runtime path variable
        "fail-open",  # the registration, and the hook itself
        "JSON reply",  # decides by the reply, never by an exit code
        "bytes",  # reads stdin as bytes
        "script file",  # a remedy the denial texts name
        "read on every call",
    ):
        assert phrase in header, f"the header does not say {phrase!r}"
    assert not _switch_sentence_problems(header), _switch_sentence_problems(header)
    flat = " ".join(header.split())
    assert "python -P" in flat, (
        "the header must say that the launcher keeps the working directory off the import path"
    )
    for phrase in (
        "imports only the standard library",  # the launcher keeps a script's own folder off the path
        "/reload-plugins",  # what the plugin documentation says about an open window
        "not a boolean",  # `enabled` with any other value is an unusable file, not an off switch
    ):
        assert phrase in flat, f"the header does not say {phrase!r}"
    assert "needs a restart first" not in flat, (
        "the plugin documentation names a second way a registration reaches a window"
    )


def _readme_hooks_section() -> str:
    text = _README.read_text(encoding="utf-8")
    match = re.search(
        r"^## Hooks\s*$(.*?)(?=^## |\Z)", text, flags=re.MULTILINE | re.DOTALL
    )
    assert match is not None, "plugins/core/README.md has no 'Hooks' section"
    return match.group(1)


def test_the_readme_has_a_hooks_section_that_says_what_it_must() -> None:
    section = _readme_hooks_section()
    for phrase in (
        ".ai/shell-prefix-hook.json",
        "restart",
        "Codex",
    ):
        assert phrase in section, f"the Hooks section does not say {phrase!r}"
    assert not _switch_sentence_problems(section), _switch_sentence_problems(section)
    assert "python -P" in " ".join(section.split()), (
        "the Hooks section must say that the launcher keeps the working directory off the import path"
    )
    for key in cast(tuple[str, ...], _hook().CONFIG_KEYS):
        assert key in section, f"the Hooks section does not name the key {key!r}"
    for hook_name in ("gate_learnings_drain", "gate_shell_prefix"):
        assert hook_name in section, f"the Hooks section does not name {hook_name}"
    assert "off by default" in section


# What the Registration part of the README states about hosts, each checked against the document
# it comes from, so a sentence that the document contradicts cannot pass in silence again: the
# plugin documentation for an open window, the Codex plugin documentation for Codex, and the hooks
# reference for what a failing hook does.
_README_HOST_PHRASES = (
    "/reload-plugins",  # loads a change in a session that is already open
    "keeps the versions it already loaded",  # the running session
    "discovers `hooks/hooks.json` by default",  # Codex finds the registration without the manifest
    "reviews and trusts",  # and skips plugin hooks until the user does
    "have not been run in Codex",  # so nothing is claimed about how they behave there
    "standard library",  # a hook script is one file
    "Not protected",
    "127",  # uv missing from the PATH, in a POSIX shell
    "exits 2",  # uv starts but cannot do its job
    "only exit code 0 or 2",  # Windows without Git Bash: any other code blocks
    "onFailure",
    "other value makes the file unusable",  # `enabled` that is not a boolean
)
_README_HOST_FORBIDDEN = (
    "neither hook is registered",  # the Codex plugin documentation says otherwise
    "declares no hooks, so",
    "within about a minute",
)


def _host_sentence_problems(section: str) -> list[str]:
    flat = " ".join(section.split())
    missing = [f"missing {p!r}" for p in _README_HOST_PHRASES if p not in flat]
    claimed = [f"must not say {p!r}" for p in _README_HOST_FORBIDDEN if p in flat]
    return missing + claimed


def test_the_host_sentence_check_rejects_the_claim_the_codex_documentation_contradicts() -> (
    None
):
    """The check is shown to fail: the README's first account of Codex breaks its terms."""
    contradicted = (
        "The Codex manifest declares no hooks, so neither hook is registered for Codex; "
        "whether and how Codex registers plugin hooks is not established here."
    )
    problems = _host_sentence_problems(contradicted)
    assert "must not say 'neither hook is registered'" in problems
    assert "must not say 'declares no hooks, so'" in problems
    assert len(problems) == len(_README_HOST_PHRASES) + 2, problems
    # the other way: a text that holds every required phrase and none of the forbidden ones passes
    assert _host_sentence_problems(" ".join(_README_HOST_PHRASES)) == []


def test_the_readme_states_what_the_host_documents_say() -> None:
    problems = _host_sentence_problems(_readme_hooks_section())
    assert not problems, problems


# --------------------------------------------------------------- the switch and its problems


def _decide_in(
    project: Path, tool: str, command: str, environ: Mapping[str, str] | None = None
) -> str:
    return _real_decide(
        _payload(tool, command, project),
        {"CLAUDE_PROJECT_DIR": str(project)} if environ is None else environ,
    )


def test_no_file_means_the_hook_does_nothing(tmp_path: Path) -> None:
    assert _decide_in(tmp_path, "Bash", "cd /x && FOO=bar ls") == ""


@pytest.mark.parametrize(
    "text",
    [
        pytest.param({"enabled": False}, id="enabled false"),
        pytest.param({}, id="an empty object"),
        pytest.param({"deny_relative_cd": True}, id="options but no enabled"),
        pytest.param(
            {"enabled": False, "deny_relative_cd": True, "deny_set_location": True},
            id="options under enabled false",
        ),
    ],
)
def test_a_project_that_is_not_enabled_is_never_judged(
    tmp_path: Path, text: dict[str, Any]
) -> None:
    _write_config(tmp_path, json.dumps(text))
    assert _decide_in(tmp_path, "Bash", "cd /x && FOO=bar ls") == ""
    assert _decide_in(tmp_path, "PowerShell", "$env:X = 1") == ""


def test_the_file_is_read_on_every_call(tmp_path: Path) -> None:
    """Turning the switch on or off reaches the next call: nothing is cached between calls."""
    command = "cd /x && ls"
    assert _decide_in(tmp_path, "Bash", command) == ""
    _write_config(tmp_path, json.dumps({"enabled": True}))
    assert _family(_decide_in(tmp_path, "Bash", command)) == "move"
    _write_config(tmp_path, json.dumps({"enabled": False}))
    assert _decide_in(tmp_path, "Bash", command) == ""
    _write_config(tmp_path, json.dumps({"enabled": True, "deny_relative_cd": True}))
    assert _family(_decide_in(tmp_path, "Bash", "cd backend")) == "move"
    _write_config(tmp_path, json.dumps({"enabled": True}))
    assert _decide_in(tmp_path, "Bash", "cd backend") == ""
    (tmp_path / _CONFIG_RELATIVE).unlink()
    assert _decide_in(tmp_path, "Bash", command) == ""


def _form_file(folder: str = "app-dir", then: list[str] | None = None) -> str:
    """A switch file that is valid except for the one allowed form it carries."""
    form = {
        "tool": "Bash",
        "folder": folder,
        "then": ["build-tool"] if then is None else then,
    }
    return json.dumps({"enabled": True, "allowed_forms": [form]})


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty file"),
        pytest.param("   \n", id="whitespace only"),
        pytest.param("{", id="truncated"),
        pytest.param("not json", id="not JSON"),
        pytest.param("[]", id="a list at the top level"),
        pytest.param('"enabled"', id="a string at the top level"),
        pytest.param("null", id="null at the top level"),
        pytest.param(json.dumps({"enabled": "true"}), id="enabled as a string"),
        pytest.param(json.dumps({"enabled": 1}), id="enabled as a number"),
        pytest.param(json.dumps({"enabled": None}), id="enabled as null"),
        pytest.param(
            json.dumps({"enabled": True, "deny_relative_cd": "yes"}),
            id="an option as a string",
        ),
        pytest.param(
            json.dumps({"enabled": True, "deny_set_location": 1}),
            id="an option as a number",
        ),
        pytest.param(
            json.dumps({"enabled": True, "deny_powershell_assignment": []}),
            id="an option as a list",
        ),
        pytest.param(json.dumps({"enabled": True, "extra": 1}), id="an unknown key"),
        pytest.param(
            json.dumps({"enabled": False, "extra": 1}),
            id="an unknown key under enabled false",
        ),
        pytest.param(
            json.dumps({"enabled": True, "Enabled": True}), id="a key in the wrong case"
        ),
        pytest.param(
            json.dumps({"enabled": True, "allowed_forms": {}}),
            id="allowed_forms as an object",
        ),
        pytest.param(
            json.dumps({"enabled": True, "allowed_forms": "x"}),
            id="allowed_forms as a string",
        ),
        pytest.param(
            json.dumps({"enabled": True, "allowed_forms": ["x"]}),
            id="a form as a string",
        ),
        pytest.param(
            json.dumps({"enabled": True, "allowed_forms": [{}]}), id="an empty form"
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [
                        {"tool": "Bash", "folder": "a", "then": ["b"], "x": 1}
                    ],
                }
            ),
            id="a form with an unknown key",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [{"tool": "Zsh", "folder": "a", "then": ["b"]}],
                }
            ),
            id="a form for an unknown tool",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [{"tool": "Bash", "folder": "", "then": ["b"]}],
                }
            ),
            id="an empty folder",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [
                        {"tool": "Bash", "folder": "/abs/dir", "then": ["b"]}
                    ],
                }
            ),
            id="an absolute folder",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [
                        {"tool": "Bash", "folder": "a/../b", "then": ["b"]}
                    ],
                }
            ),
            id="a folder with ..",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [{"tool": "Bash", "folder": "a", "then": []}],
                }
            ),
            id="an empty then list",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [{"tool": "Bash", "folder": "a", "then": "b"}],
                }
            ),
            id="then as a string",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [{"tool": "Bash", "folder": "a", "then": ["b c"]}],
                }
            ),
            id="a command word with a space",
        ),
        pytest.param(
            json.dumps(
                {
                    "enabled": True,
                    "allowed_forms": [{"tool": "Bash", "folder": "a", "then": [1]}],
                }
            ),
            id="a command word that is a number",
        ),
        pytest.param(
            _form_file(folder=_DRIVE + "/app"), id="a folder that starts with a drive"
        ),
        pytest.param(_form_file(folder="~/app"), id="a folder under the home folder"),
        pytest.param(
            _form_file(folder="\\app"), id="a folder with a leading backslash"
        ),
        pytest.param(_form_file(folder="app$x"), id="a folder with a variable"),
        pytest.param(_form_file(folder="app`x"), id="a folder with a backtick"),
        pytest.param(_form_file(folder="."), id="a folder that is a dot"),
        pytest.param(_form_file(folder="./"), id="a folder that is a dot and a slash"),
        pytest.param(_form_file(folder="   "), id="a folder that is blank"),
        pytest.param(
            _form_file(folder="..\\x"),
            id="a folder that starts with .. and a backslash",
        ),
        pytest.param(
            _form_file(folder="a\\..\\b"),
            id="a folder with a .. segment and backslashes",
        ),
        pytest.param(_form_file(then=[""]), id="an empty command word"),
        pytest.param(_form_file(then=[" "]), id="a blank command word"),
        pytest.param(_form_file(then=["a", "b\tc"]), id="a tab inside a command word"),
    ],
)
def test_an_unusable_file_allows_the_call_and_says_so_once(
    tmp_path: Path, text: str
) -> None:
    """A broken switch must not block work, and must not pass in silence."""
    _write_config(tmp_path, text)
    for tool, command in (
        ("Bash", "cd /x && FOO=bar ls"),
        ("PowerShell", "Set-Location /x"),
        ("Bash", "ls"),
    ):
        out = _decide_in(tmp_path, tool, command)
        reply = cast(dict[str, Any], json.loads(out))
        assert set(reply) == {"systemMessage"}, f"{tool} {command!r}: {out}"
        message = str(reply["systemMessage"])
        assert ".ai/shell-prefix-hook.json" in message
        assert message.count("\n") == 0, "one message, on one line"
        assert 20 < len(message) < 2000
        assert out.count("systemMessage") == 1, (
            "the warning is one object with one message"
        )


def test_a_missing_ai_folder_or_an_unreadable_path_is_not_a_warning(
    tmp_path: Path,
) -> None:
    """Absent means off. A folder where the file should be is a problem the message names."""
    assert _decide_in(tmp_path, "Bash", "cd /x") == ""
    (tmp_path / ".ai").write_text("not a folder", encoding="utf-8")
    assert _decide_in(tmp_path, "Bash", "cd /x") == ""
    other = tmp_path / "other"
    (other / _CONFIG_RELATIVE).mkdir(parents=True)
    reply = cast(dict[str, Any], json.loads(_decide_in(other, "Bash", "cd /x")))
    assert set(reply) == {"systemMessage"}


def test_a_byte_order_mark_is_accepted(tmp_path: Path) -> None:
    """Editors on Windows write one, and a switch that silently stops working there is the worst kind."""
    _write_config(
        tmp_path, b"\xef\xbb\xbf" + json.dumps({"enabled": True}).encode("utf-8")
    )
    assert _family(_decide_in(tmp_path, "Bash", "cd /x")) == "move"


def test_a_file_that_is_not_utf8_is_unusable_not_a_crash(tmp_path: Path) -> None:
    _write_config(tmp_path, json.dumps({"enabled": True}).encode("utf-16"))
    reply = cast(dict[str, Any], json.loads(_decide_in(tmp_path, "Bash", "cd /x")))
    assert set(reply) == {"systemMessage"}


def test_a_file_nested_too_deeply_is_unusable_and_says_so(tmp_path: Path) -> None:
    """The JSON reader raises RecursionError, which is not a ValueError. Left uncaught it would end
    the call in the outer guard, which allows it in silence: a broken switch with no warning."""
    _write_config(tmp_path, '{"a":' * 100_000 + "1" + "}" * 100_000)
    reply = cast(dict[str, Any], json.loads(_decide_in(tmp_path, "Bash", "cd /x")))
    assert set(reply) == {"systemMessage"}
    assert "nested too deeply" in str(reply["systemMessage"])


def test_a_folder_written_with_a_trailing_slash_in_the_file_still_matches(
    tmp_path: Path,
) -> None:
    """The file is normalised like the command: `app-dir/` in the file is `app-dir`."""
    config = {
        "enabled": True,
        "deny_relative_cd": True,
        "allowed_forms": [
            {"tool": "Bash", "folder": "app-dir/", "then": ["build-tool"]}
        ],
    }
    _write_config(tmp_path, json.dumps(config))
    for command in ("cd app-dir && build-tool test", "cd app-dir/ && build-tool test"):
        assert _decide_in(tmp_path, "Bash", command) == "", command
    other = _decide_in(tmp_path, "Bash", "cd other-dir && build-tool test")
    assert _family(other) == "move", "the form must not match every folder"


def test_a_valid_file_prints_no_message(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        json.dumps(
            {"enabled": True, "deny_relative_cd": True, "allowed_forms": _STRICT_FORMS}
        ),
    )
    assert _decide_in(tmp_path, "Bash", "ls") == ""


def test_the_project_folder_comes_from_the_environment_then_from_the_payload(
    tmp_path: Path,
) -> None:
    enabled = tmp_path / "enabled"
    disabled = tmp_path / "disabled"
    _write_config(enabled, json.dumps({"enabled": True}))
    disabled.mkdir()
    command = "cd /x && ls"
    # the environment variable wins, even when the payload's folder says otherwise
    out = _real_decide(
        _payload("Bash", command, disabled), {"CLAUDE_PROJECT_DIR": str(enabled)}
    )
    assert _family(out) == "move"
    out = _real_decide(
        _payload("Bash", command, enabled), {"CLAUDE_PROJECT_DIR": str(disabled)}
    )
    assert out == ""
    # without the variable, the payload's folder is the project
    assert _family(_real_decide(_payload("Bash", command, enabled), {})) == "move"
    assert _real_decide(_payload("Bash", command, disabled), {}) == ""
    assert (
        _real_decide(_payload("Bash", command, enabled), {"CLAUDE_PROJECT_DIR": ""})
        != ""
    )
    # with neither, there is no project: nothing to judge
    assert _real_decide(_payload("Bash", command), {}) == ""
    # a shell that has moved into a sub-folder still finds the project through the variable
    sub = enabled / "sub"
    sub.mkdir()
    assert (
        _family(
            _real_decide(
                _payload("Bash", command, sub), {"CLAUDE_PROJECT_DIR": str(enabled)}
            )
        )
        == "move"
    )


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"not json", id="not JSON"),
        pytest.param(b"[]", id="a list"),
        pytest.param(b"{}", id="an empty object"),
        pytest.param(b'{"tool_name": "Bash"}', id="no tool_input"),
        pytest.param(
            b'{"tool_name": "Bash", "tool_input": null}', id="a null tool_input"
        ),
        pytest.param(
            b'{"tool_name": "Bash", "tool_input": []}', id="a list tool_input"
        ),
        pytest.param(b'{"tool_name": "Bash", "tool_input": {}}', id="no command"),
        pytest.param(
            b'{"tool_name": "Bash", "tool_input": {"command": 5}}',
            id="a numeric command",
        ),
        pytest.param(
            b'{"tool_name": "Bash", "tool_input": {"command": null}}',
            id="a null command",
        ),
        pytest.param(
            b'{"tool_name": 5, "tool_input": {"command": "cd /x"}}',
            id="a numeric tool name",
        ),
        pytest.param(
            b'{"tool_name": "Edit", "tool_input": {"command": "cd /x"}}',
            id="a tool the hook does not watch",
        ),
        pytest.param(
            b'{"tool_name": "bash", "tool_input": {"command": "cd /x"}}',
            id="a tool name in the wrong case",
        ),
        pytest.param(b"\xff\xfe\x00", id="bytes that are not text"),
        pytest.param(
            b'{"tool_name": "Bash", "tool_input": {"command": "cd /x"}',
            id="truncated JSON",
        ),
    ],
)
def test_a_payload_the_hook_cannot_use_is_allowed(tmp_path: Path, raw: bytes) -> None:
    _write_config(tmp_path, json.dumps({"enabled": True}))
    assert _real_decide(raw, {"CLAUDE_PROJECT_DIR": str(tmp_path)}) == ""


def test_a_non_ascii_command_is_judged(tmp_path: Path) -> None:
    """The payload may carry non-ASCII as raw UTF-8 or as \\u escapes: both are judged alike."""
    _write_config(tmp_path, json.dumps({"enabled": True}))
    cyrillic = "привіт"
    emoji = "☃"
    environ = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
    for escaped in (False, True):
        for tool, command, want in (
            ("Bash", f"echo {cyrillic} {emoji}; cd /x", "move"),
            ("Bash", f"echo {cyrillic} {emoji} && ls", "allow"),
            ("PowerShell", f"Write-Output '{cyrillic}'; Set-Location /x", "move"),
            ("Bash", f"{cyrillic}=1 ls", "allow"),
            ("Bash", f"FOO={cyrillic} ls", "assign"),
        ):
            raw = _payload(tool, command, tmp_path, escaped=escaped)
            assert (raw.isascii()) == escaped
            assert _family(_real_decide(raw, environ)) == want, (escaped, tool, command)


# ---------------------------------------------------------------------- what the model reads


def _denial(
    tmp_path: Path, tool: str, command: str, config: dict[str, Any] | None = None
) -> str:
    _write_config(
        tmp_path, json.dumps(config if config is not None else {"enabled": True})
    )
    return _reason(_decide_in(tmp_path, tool, command))


def test_the_three_openings_tell_the_families_apart(tmp_path: Path) -> None:
    """One text per rule family, and its first words say which family it is."""
    texts = {
        "move": _denial(tmp_path, "Bash", "cd /x"),
        "shadow": _denial(tmp_path, "Bash", "cd() { :; }"),
        "assign": _denial(tmp_path, "Bash", "FOO=bar ls"),
    }
    for opening, family in _OPENINGS:
        assert texts[family].startswith(opening), (family, texts[family][:60])
    assert len({text[:20] for text in texts.values()}) == len(texts)
    assert len(set(texts.values())) == len(texts)


def test_a_denial_names_remedies_that_work_and_none_that_do_not(tmp_path: Path) -> None:
    move = _denial(tmp_path, "Bash", "cd /x")
    assign = _denial(tmp_path, "Bash", "FOO=bar ls")
    shadow = _denial(tmp_path, "Bash", "cd() { :; }")
    for text in (move, shadow):
        assert "git -C" in text and "absolute" in text
    assert "script file" in move
    # The same text says that a prefix in front of the command defeats the permission rules, so it
    # must not offer one as the way out: `(cd <dir> && ls)` is a prefix.
    for text in (move, shadow):
        assert "subshell" not in text and "(cd " not in text
    for needle in ("inline", "script file", "-X utf8"):
        assert needle in assign, (
            f"the assignment text does not name the remedy {needle!r}"
        )
    assert "gone in the next" in assign, (
        "the text must say a variable does not survive to the next call"
    )
    for text in (move, assign, shadow):
        lowered = text.lower()
        for wrong in (
            "export in a previous call",
            "export in a prior call",
            "export in an earlier call",
            "in a previous call",
        ):
            assert wrong not in lowered, (
                f"the text recommends a remedy that cannot work: {wrong!r}"
            )
        assert text.isascii() and "\n" not in text and len(text) < 1400


def test_a_denial_does_not_quote_a_copyable_throwaway(tmp_path: Path) -> None:
    """An example in a denial text is an instruction: the text must not show a dummy assignment."""
    assign = _denial(tmp_path, "Bash", "FOO=bar ls")
    assert "cd_" not in assign and "any name" in assign


def test_the_strict_text_lists_the_allowed_forms_for_the_tool_that_was_denied(
    tmp_path: Path,
) -> None:
    config = json.loads(cast(str, _CONFIGS[_STRICT]))
    text = _denial(tmp_path, "Bash", "cd /x", config)
    assert "cd app-dir && build-tool" in text
    assert (tmp_path / "app-dir").as_posix() in text.replace("\\", "/")
    plain = _denial(tmp_path, "Bash", "cd /x")
    assert "This project allows only" not in plain
    powershell = _denial(tmp_path, "PowerShell", "Set-Location /x", config)
    assert "build-tool" not in powershell, (
        "a Bash form must not be offered to the PowerShell tool"
    )


def test_a_target_with_dotdot_never_matches_even_when_the_project_path_has_one(
    tmp_path: Path,
) -> None:
    """Nothing is resolved. A target spelled with `..` never matches an allowed folder, even when the
    project folder was itself given with a `..` and the two strings are therefore equal."""
    config = cast(str, _CONFIGS[_STRICT])
    clean = tmp_path / "clean"
    _write_config(clean, config)
    allowed = f"cd {clean.as_posix()}/app-dir && build-tool test"
    assert _decide_in(clean, "Bash", allowed) == "", (
        "the control: the plain spelling is allowed"
    )
    (tmp_path / "a").mkdir()
    dotted = tmp_path / "a" / ".." / "p"
    _write_config(dotted, config)
    command = f"cd {dotted.as_posix()}/app-dir && build-tool test"
    assert ".." in command
    assert _family(_decide_in(dotted, "Bash", command)) == "move"


# ------------------------------------------------------------- the contract, as a process


def _script(
    stdin: bytes,
    project: Path | None,
    env: Mapping[str, str] | None = None,
) -> "subprocess.CompletedProcess[bytes]":
    """Run the hook the way the harness does: a process that reads stdin and prints JSON or nothing."""
    base = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    if project is not None:
        base["CLAUDE_PROJECT_DIR"] = str(project)
    base.update(env or {})
    return subprocess.run(
        [sys.executable, "-B", str(_HOOK)],
        input=stdin,
        capture_output=True,
        env=base,
        cwd=project,
        timeout=60,
        check=False,
    )


def test_a_denial_is_one_json_object_and_nothing_else(tmp_path: Path) -> None:
    _write_config(tmp_path, json.dumps({"enabled": True}))
    proc = _script(_payload("Bash", "cd /x && ls", tmp_path), tmp_path)
    assert (proc.returncode, proc.stderr) == (0, b""), (
        "the decision is the reply, never the exit code"
    )
    text = proc.stdout.decode("ascii")
    reply = cast(dict[str, Any], json.loads(text))
    assert set(reply) == {"hookSpecificOutput"}
    inner = cast(dict[str, Any], reply["hookSpecificOutput"])
    assert set(inner) == {
        "hookEventName",
        "permissionDecision",
        "permissionDecisionReason",
    }
    assert (
        inner["hookEventName"] == "PreToolUse" and inner["permissionDecision"] == "deny"
    )
    assert text.strip() == text, "nothing around the object but the object"


def test_an_allowed_call_prints_nothing_and_exits_zero(tmp_path: Path) -> None:
    _write_config(tmp_path, json.dumps({"enabled": True}))
    proc = _script(_payload("Bash", "ls -la", tmp_path), tmp_path)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, b"", b"")


def test_a_project_with_no_file_prints_nothing(tmp_path: Path) -> None:
    proc = _script(_payload("Bash", "cd /x && FOO=bar ls", tmp_path), tmp_path)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, b"", b"")


def test_an_unusable_file_prints_one_message_object_and_exits_zero(
    tmp_path: Path,
) -> None:
    _write_config(tmp_path, "{ nope")
    proc = _script(_payload("Bash", "cd /x", tmp_path), tmp_path)
    assert (proc.returncode, proc.stderr) == (0, b"")
    reply = cast(dict[str, Any], json.loads(proc.stdout.decode("ascii")))
    assert set(reply) == {"systemMessage"}


@pytest.mark.parametrize(
    "stdin",
    [
        pytest.param(b"", id="empty stdin"),
        pytest.param(b"not json at all", id="not JSON"),
        pytest.param(b"\xff\xfe\xfd\x00garbage", id="bytes that are not UTF-8"),
        pytest.param(
            b'{"tool_name":"Bash","tool_input":{"command":5}}',
            id="a command that is not text",
        ),
    ],
)
def test_a_crash_or_unusable_stdin_is_an_allow(tmp_path: Path, stdin: bytes) -> None:
    _write_config(tmp_path, json.dumps({"enabled": True}))
    proc = _script(stdin, tmp_path)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, b"", b"")


def test_a_non_ascii_payload_is_judged_under_a_legacy_console_encoding(
    tmp_path: Path,
) -> None:
    """Stdin is read as bytes: a host whose default console encoding is not UTF-8 changes nothing."""
    _write_config(tmp_path, json.dumps({"enabled": True}))
    cyrillic = "привіт ☃"
    legacy = {_ENCODING_VARIABLE: "cp1252:surrogateescape", "PYTHONUTF8": "0"}
    denied = _script(_payload("Bash", f"echo {cyrillic}; cd /x"), tmp_path, legacy)
    assert (denied.returncode, denied.stderr) == (0, b"")
    assert _family(denied.stdout.decode("ascii")) == "move"
    allowed = _script(_payload("Bash", f"echo {cyrillic} && ls"), tmp_path, legacy)
    assert (allowed.returncode, allowed.stdout, allowed.stderr) == (0, b"", b"")


def test_bytes_that_are_not_utf8_inside_a_command_do_not_hide_it(
    tmp_path: Path,
) -> None:
    _write_config(tmp_path, json.dumps({"enabled": True}))
    raw = b'{"tool_name":"Bash","tool_input":{"command":"echo \xff\xfe; cd /x"}}'
    proc = _script(raw, tmp_path)
    assert (proc.returncode, proc.stderr) == (0, b"")
    assert _family(proc.stdout.decode("ascii")) == "move"


def test_a_non_ascii_folder_in_an_allowed_form_is_read_as_utf8_bytes(
    tmp_path: Path,
) -> None:
    """The verdict here depends on the decoded characters. Read as text under a legacy console
    encoding, a Cyrillic folder name would turn into other characters and the form would not match;
    read as UTF-8 bytes it matches. A different Cyrillic folder is the control: it is refused."""
    folder = "папка"
    config = {
        "enabled": True,
        "deny_relative_cd": True,
        "allowed_forms": [{"tool": "Bash", "folder": folder, "then": ["build-tool"]}],
    }
    _write_config(tmp_path, json.dumps(config))
    legacy = {_ENCODING_VARIABLE: "cp1252:surrogateescape", "PYTHONUTF8": "0"}
    allowed = _script(
        _payload("Bash", f"cd {folder} && build-tool test"), tmp_path, legacy
    )
    assert (allowed.returncode, allowed.stdout, allowed.stderr) == (0, b"", b"")
    other = _script(_payload("Bash", "cd другая && build-tool test"), tmp_path, legacy)
    assert (other.returncode, other.stderr) == (0, b"")
    assert _family(other.stdout.decode("ascii")) == "move"


def test_a_bug_in_the_scanner_is_an_allow_and_not_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The header's contract: a payload it cannot use, or a bug in the scanner, is an allow, because a
    guard that crashes must not block unrelated work. The control: the same call, with the scanner
    intact, is a denial."""
    _write_config(tmp_path, json.dumps({"enabled": True}))
    module = _hook()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    def give_stdin() -> None:
        stdin = SimpleNamespace(
            buffer=io.BytesIO(_payload("Bash", "cd /x && ls", tmp_path))
        )
        monkeypatch.setattr(sys, "stdin", stdin)

    give_stdin()
    module.main()
    assert _family(capsys.readouterr().out) == "move"

    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("a bug in the scanner")

    monkeypatch.setattr(module, "judge", broken)
    give_stdin()
    module.main()
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


# ------------------------------------------------------------ very long and hostile commands

# The hook's registered timeout is 10 seconds. These bounds are a quarter of that, in a process,
# and a few times the measured worst case in this one, so a slow runner does not make them flake.
_SCRIPT_BOUND = 5.0
_IN_PROCESS_BOUND = 2.0

_PAD_60K = "x" * 60000

_HOSTILE: list[tuple[str, str, str]] = [
    ("a run of spaces", "Bash", " " * 30000 + "ls"),
    ("a run of semicolons", "Bash", ";" * 30000),
    ("a run of ampersands", "Bash", "&" * 30000),
    ("alternating ampersands and pipes", "Bash", "&|" * 30000),
    ("a run of newlines", "Bash", "\n" * 30000 + "ls"),
    ("pairs of single quotes", "Bash", "''" * 30000),
    ("pairs of double quotes", "Bash", '""' * 30000),
    ("one open single quote and a long tail", "Bash", "'" + "a" * 30000),
    ("one open double quote and a long tail", "Bash", '"' + "a " * 30000),
    ("an odd run of single quotes", "Bash", "'" * 30001),
    ("an odd run of double quotes", "Bash", '"' * 30001),
    ("an odd run of backticks", "Bash", "`" * 30001),
    ("a run of escaped quotes", "Bash", '"' + '\\"' * 30000),
    ("a run of backslashes", "Bash", "\\" * 30001),
    ("a run of ANSI-C openers", "Bash", "$'" * 30000),
    ("a run of substitution openers", "Bash", "$(" * 30000),
    ("a run of parentheses", "Bash", "(" * 30000 + ")" * 30000),
    ("a run of braces", "Bash", "{ " * 30000),
    ("a run of heredoc markers", "Bash", "cat <<A " * 8000),
    ("heredoc markers on separate lines, none closed", "Bash", "cat <<A\n" * 8000),
    ("a run of here-string markers", "Bash", "cat <<< x " * 6000),
    ("a run of comment starts", "Bash", "# " * 30000 + "\nls"),
    ("many short statements", "Bash", "a;" * 30000),
    ("many pipeline segments", "Bash", "a|" * 30000),
    ("many assignment-looking words", "Bash", "a=b " * 15000),
    ("a long word of digits then a redirect", "Bash", "1" * 30000 + ">x"),
    ("a long digit run with no redirect", "Bash", "1" * 30000 + "x"),
    ("a long line with a late cd", "Bash", "echo " + _PAD_60K + "; cd /x"),
    ("PowerShell: a run of here-string openers", "PowerShell", "@'\n" * 15000),
    ("PowerShell: a run of block comment openers", "PowerShell", "<#" * 30000),
    ("PowerShell: a run of double quotes", "PowerShell", '"' * 30001),
    ("PowerShell: a run of single quotes", "PowerShell", "'" * 30001),
    ("PowerShell: a run of backticks", "PowerShell", "`" * 30001),
    ("PowerShell: a run of braces", "PowerShell", "{}" * 30000),
    ("PowerShell: many short statements", "PowerShell", "a;" * 30000),
    (
        "PowerShell: a long line with a late mover",
        "PowerShell",
        "Write-Output " + _PAD_60K + "; Set-Location /x",
    ),
]


@pytest.mark.parametrize(
    ("name", "tool", "command"), _HOSTILE, ids=[row[0] for row in _HOSTILE]
)
def test_a_hostile_command_is_judged_in_bounded_time(
    name: str, tool: str, command: str, tmp_path: Path
) -> None:
    _write_config(
        tmp_path,
        json.dumps(
            {"enabled": True, "deny_relative_cd": True, "deny_set_location": True}
        ),
    )
    started = time.perf_counter()
    out = _decide_in(tmp_path, tool, command)
    elapsed = time.perf_counter() - started
    assert elapsed < _IN_PROCESS_BOUND, (
        f"{name}: {elapsed:.2f}s for {len(command)} characters"
    )
    if out:
        _family(out)  # a reply, if any, is a well-formed one


# A run of the words that only introduce a command (`!`, `if`, the options of `time` and `command`,
# PowerShell's `&` and bare parentheses) is read word by word. The cost must grow with the length
# of the run and not with its square: at 200 KB a quadratic reading takes several seconds to tens of
# seconds (the hook's own timeout is 10), a linear one a fraction of a second, so the in-process
# bound tells the two apart. One row per place that walks such a run: the Bash keyword loop, the
# options of `time`, `command` and `builtin`, and the PowerShell loop (its `&` and its parentheses
# are different tests inside it).
_PREFIX_RUNS: list[tuple[str, str, str]] = [
    ("negations", "Bash", "! " * 100_000 + "cd /x"),
    ("command options", "Bash", "command " + "-p " * 66_000 + "cd /x"),
    ("PowerShell call operators", "PowerShell", "& " * 100_000 + f"cd {_DRIVE}\\x"),
    ("PowerShell bare parentheses", "PowerShell", "( " * 100_000 + f"cd {_DRIVE}\\x"),
]


@pytest.mark.parametrize(
    ("name", "tool", "command"), _PREFIX_RUNS, ids=[row[0] for row in _PREFIX_RUNS]
)
def test_a_long_run_of_introducing_words_is_judged_in_linear_time(
    name: str, tool: str, command: str, tmp_path: Path
) -> None:
    assert len(command) >= 190_000, (
        "the run must be long enough to tell the two costs apart"
    )
    _write_config(tmp_path, json.dumps({"enabled": True}))
    started = time.perf_counter()
    out = _decide_in(tmp_path, tool, command)
    elapsed = time.perf_counter() - started
    assert _family(out) == "move", f"{name}: the mover after the run was not found"
    assert elapsed < _IN_PROCESS_BOUND, (
        f"{name}: {elapsed:.2f}s for {len(command)} characters"
    )


def test_a_line_of_sixty_kilobytes_is_judged_in_full_and_not_guessed_at(
    tmp_path: Path,
) -> None:
    """No length limit: the scan is linear, so a cd after 60 KB of text is still found, and a
    long line with nothing to find is allowed. Decided here so it is not left to a default."""
    _write_config(tmp_path, json.dumps({"enabled": True}))
    started = time.perf_counter()
    late = _decide_in(tmp_path, "Bash", "echo " + _PAD_60K + "; cd /x")
    quiet = _decide_in(tmp_path, "Bash", "echo " + _PAD_60K)
    early = _decide_in(tmp_path, "Bash", "cd /x && echo " + _PAD_60K)
    elapsed = time.perf_counter() - started
    assert _family(late) == "move" and quiet == "" and _family(early) == "move"
    assert elapsed < _IN_PROCESS_BOUND, f"{elapsed:.2f}s for three 60 KB commands"


def test_a_line_of_sixty_kilobytes_runs_inside_the_bound_as_a_process(
    tmp_path: Path,
) -> None:
    _write_config(tmp_path, json.dumps({"enabled": True}))
    started = time.perf_counter()
    long_line = _script(_payload("Bash", "echo " + _PAD_60K + "; cd /x"), tmp_path)
    hostile = _script(
        _payload("Bash", "'" * 60001 + ";" * 60000 + " " * 60000), tmp_path
    )
    elapsed = time.perf_counter() - started
    assert (long_line.returncode, long_line.stderr) == (0, b"")
    assert _family(long_line.stdout.decode("ascii")) == "move"
    assert (hostile.returncode, hostile.stderr) == (0, b"")
    assert elapsed < _SCRIPT_BOUND, (
        f"{elapsed:.2f}s for two long commands, as processes"
    )


def test_a_disabled_project_does_almost_nothing_even_for_a_huge_command(
    tmp_path: Path,
) -> None:
    """Off means: read stdin, look for one file, exit. The command is never scanned."""
    _write_config(tmp_path, json.dumps({"enabled": False}))
    started = time.perf_counter()
    out = _decide_in(tmp_path, "Bash", "echo " + "x" * 3_000_000)
    elapsed = time.perf_counter() - started
    assert out == "" and elapsed < 1.0, f"{elapsed:.2f}s"


# ------------------------------------------------------------------ rule-level pins

_RULE_PINS: list[tuple[str, str, str, str, str]] = [
    # (tool, command, configuration text, family, rule)
    ("Bash", "cd /x", '{"enabled": true}', "move", "absolute-cd"),
    ("Bash", "cd", '{"enabled": true}', "move", "bare-cd"),
    (
        "Bash",
        "cd backend",
        '{"enabled": true, "deny_relative_cd": true}',
        "move",
        "relative-cd",
    ),
    (
        "PowerShell",
        "Set-Location backend",
        '{"enabled": true, "deny_set_location": true}',
        "move",
        "relative-set-location",
    ),
    ("Bash", "cd() { :; }", '{"enabled": true}', "shadow", "shadow"),
    ("Bash", "function cd { :; }", '{"enabled": true}', "shadow", "shadow"),
    ("Bash", "alias cd=true", '{"enabled": true}', "shadow", "shadow"),
    ("Bash", "FOO=bar ls", '{"enabled": true}', "assign", "assignment"),
    ("Bash", "export FOO=bar", '{"enabled": true}', "assign", "export"),
    ("Bash", "readonly FOO=bar", '{"enabled": true}', "assign", "export"),
    ("Bash", "declare -x FOO=bar", '{"enabled": true}', "assign", "declare"),
    ("Bash", "typeset -x FOO=bar", '{"enabled": true}', "assign", "declare"),
    ("Bash", "env FOO=bar ls", '{"enabled": true}', "assign", "env"),
    ("PowerShell", "$env:FOO = 1", '{"enabled": true}', "assign", "powershell-env"),
    (
        "PowerShell",
        "$x = 1",
        '{"enabled": true, "deny_powershell_assignment": true}',
        "assign",
        "powershell-variable",
    ),
]


@pytest.mark.parametrize(
    ("tool", "command", "config_text", "family", "rule"),
    _RULE_PINS,
    ids=[f"{pin[0]}: {pin[1]} -> {pin[4]}" for pin in _RULE_PINS],
)
def test_each_rule_fires_by_its_own_name(
    tool: str, command: str, config_text: str, family: str, rule: str, tmp_path: Path
) -> None:
    """The family says what the model reads; the rule says which check fired, so a check that
    another one happens to cover cannot be deleted without a test noticing."""
    _write_config(tmp_path, config_text)
    config, problems = _hook().load_config(str(tmp_path))
    assert config is not None and not problems, problems
    found = _hook().judge(command, tool, config, str(tmp_path))
    assert found == (family, rule), found


def test_the_judge_never_raises_on_any_row(projects: _Projects) -> None:
    """decide() fails open, so a crash in the judge looks exactly like an allow: call it directly."""
    judge = _hook().judge
    for row in _ALL_ROWS:
        _name, tool, command, config_name, _decision = row
        if config_name.startswith("unusable"):
            continue
        project = projects.paths[config_name]
        config, problems = _hook().load_config(str(project))
        if config is None:
            assert not problems, (row[0], problems)
            continue
        if not config.enabled:
            continue  # the switch is decide()'s to read; the judge does not look at it
        found = judge(_fill(command, project), tool, config, str(project))
        denied = found is not None
        want = _expected(row[4]) not in ("allow", "warn")
        assert denied == want, (
            f"{row[0]}: expected denial={want}, the judge said {found!r}"
        )
