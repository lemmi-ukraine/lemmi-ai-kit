"""PreToolUse guard for the Bash and PowerShell tools: refuse the calls that move the persistent
working directory, start with a variable assignment, or shadow `cd` - in the projects that switch it on.

It is OFF until a project turns it on, and when it is on it refuses three families of call:

  MOVE        `cd`, `pushd`, `Set-Location` or `Push-Location` to an absolute, home, variable or
              otherwise unreadable target, wherever it sits in the command (after `&&`, `;` or a
              newline, in a loop, an `if` or a brace group), and `cd` with no target (home) or `-`.
  SHADOW      a function, `function` keyword or alias that redefines `cd`.
  ASSIGNMENT  a leading `NAME=value`, and its disguises `export`, `readonly`, `declare -x`,
              `typeset -x`, `env NAME=value` and, in PowerShell, `$env:NAME = value`.

Why these. A prefix in front of the command defeats the permission rules that match on the bare
command, so every allow-listed command prompts again. And the Bash and PowerShell tools keep ONE
working directory across calls, so one move silently re-bases every later call in the session. A
refused shape is retried in a new disguise, which is why the shadows and the assignment disguises
are rules of their own and why every statement of the command is judged, not only the first.

THE SWITCH. `.ai/shell-prefix-hook.json` in the project folder: `CLAUDE_PROJECT_DIR`, or the `cwd` of
the payload when the variable is absent. The file is read on every call, so nothing is cached, a
change needs no restart and no change to the plugin, and the state of the switch can be read from
the file without running anything. It is a JSON object, and every key is optional:

  enabled                      true switches the hook on. Absent or false: the hook does nothing at
                               all. Any value that is not a boolean makes the file unusable, as
                               below: one warning per call, and the call is allowed. (default false)
  deny_relative_cd             also refuse a relative target for `cd`, `pushd` and `chdir`.
                               `cd .` moves nowhere and stays allowed. (default false)
  deny_set_location            also refuse a relative target for `Set-Location`, `sl` and
                               `Push-Location`. (default false)
  deny_powershell_assignment   also refuse a leading `$name = value` in the PowerShell tool;
                               `$env:` assignments are always refused. (default false)
  allowed_forms                a list of {tool, folder, then}: the one call shape a strict project
                               lets through although it starts with `cd`. (default: none)

Each option names the spelling it governs: PowerShell reads `cd` as an alias of `Set-Location`, so a
project that wants no relative moves at all sets both `deny_relative_cd` and `deny_set_location`.
Absolute, home, variable and unreadable targets are refused under every spelling, options or not.

An allowed form is `cd <folder> && <word> ...` where `tool` is Bash or PowerShell, `folder` is ONE
folder under the project root (relative, no `..`) and `then` lists the command words that may follow
the `&&`. The folder may be spelled as given or by its absolute path. Spellings are compared after
separators are normalised to `/`, a trailing slash is dropped and the case of a drive letter is
ignored; `..` is never resolved, so a target that contains it never matches, and nothing else is
resolved either (no symlinks, no `./`). A form matches only when the whole command starts with it;
every later statement is judged on its own, so `cd app-dir && build-tool test; cd /x` is refused.

Two projects, by configuration alone:

  lax     {"enabled": true}
  strict  {"enabled": true, "deny_relative_cd": true, "deny_set_location": true,
           "deny_powershell_assignment": true,
           "allowed_forms": [{"tool": "Bash", "folder": "app-dir", "then": ["build-tool"]}]}

A file the hook cannot use (not UTF-8 JSON, not an object, an unknown key, a value of the wrong type,
a form that is not well formed) never blocks a call and never passes in silence: the call is
allowed, nothing is judged, and one `systemMessage` per call says what is wrong with the file.

TURNING IT ON OR OFF. A hook wired into a settings file reached windows that were already open, on
their next call, in one recorded case in another consumer: the delay was not timed, and for a plugin
registration it is unmeasured. So flip the switch when no peer session is mid-task. The hooks
reference says: "Direct edits to hooks in settings files are normally picked up automatically by the
file watcher." It gives no delay, and it says nothing about when a plugin's own hooks file reaches a
window that is already open. This design differs in the part that matters: the switch file is read
on every call, so turning it on or off reaches every window that already has the hook registered on
its next shell call. A window that does not have the hook registered yet loads the registration in
a new session. The plugin documentation says that a running session keeps the versions it already
loaded and that `/reload-plugins` loads a change into a session that is already open; loading these
registrations that way was not tried here.

WHAT THE REGISTRATION AND THE SCRIPT FOLLOW

  1. Registered through the runtime path variable `${CLAUDE_PLUGIN_ROOT}`, in double quotes, never
     through a machine path.
  2. A fail-open registration: the registered command is a short launcher that checks that the
     script file exists, runs it with `runpy` and passes its exit code on. A missing script is then
     an allow (exit 0, no output) in sh, Git Bash and PowerShell, where Python's own exit 2 for a
     file it cannot open is read by the harness as a block. The launcher runs under `python -P`,
     which keeps the working directory off the import path: with `-c` alone, a project file named
     like a standard module (`json.py`) would be run in its place. The flag also keeps the
     script's own folder off the import path, so a hook script is one file that imports only the
     standard library: a sibling module would not be found, the script would exit 1 (a non-blocking
     failure, except on Windows without Git Bash) and the hook would go quiet. A test pins that for
     each hook script.
  3. The decision is a JSON reply on stdout with exit 0, never an exit code.
  4. Stdin is read as bytes and decoded as UTF-8 with errors replaced, so a console code page
     changes nothing.
  5. A denial names remedies that work (inline the value; write multi-step logic to a script file
     and run that; use the interpreter's own UTF-8 switch instead of an environment variable; pass
     a directory as an argument, `git -C <dir>` or an absolute path, instead of `cd`) and never
     recommends setting a variable in an earlier call, which does not survive to the next one.
     There is one text per rule family, and their openings tell them apart.

WHAT IT DELIBERATELY DOES NOT BLOCK. Each limit below is pinned by a row of the shape table in the
test file, so closing one is a visible change. They are accepted limits, not oversights.

ALLOWED relative-cd: `cd backend`, `cd ..` and `Set-Location ..` move the persistent directory too.
  What was measured as a habit was the absolute and home-anchored move, and a relative move is how
  most real work starts, so the default leaves it alone. The two options refuse it.
ALLOWED cd-dot: `cd .` changes nothing.
ALLOWED subshell-cd: `(cd /x && ls)`, `$(cd /x && pwd)` and backticks run in a subshell, so the
  persistent directory is unchanged.
ALLOWED background-cd: `cd /x &` runs in a background subshell.
ALLOWED pipeline-segment: every segment of a Bash pipeline runs in a subshell, so `cd /x | cat` and
  `echo hi | cd /x` leave the directory alone. (`shopt -s lastpipe` keeps the last segment in the
  current shell and is not read. PowerShell pipelines share one runspace, and there a mover IS judged.)
ALLOWED brace-argument: a brace is a group delimiter only in command position, so in
  `echo } cd /x` the `cd` is an argument of echo.
ALLOWED not-an-assignment: `1A=b ls` and `a.b=c ls` are not assignments in a POSIX shell (a name
  cannot start with a digit or hold a dot), so the assignment text would describe something that
  did not happen.
ALLOWED set-builtin: `set -e; ls` sets a shell option, not a variable, and options do not persist
  between calls.
ALLOWED later-assignment: `ls && FOO=bar cmd` and a PowerShell `ls; $env:X = 1`. Only a LEADING word
  defeats a permission rule that matches on the bare command; an assignment after the first command
  leaves that command's own prefix intact.
ALLOWED subshell-assignment: `( X=1 ls )`. A prefix assignment is scoped to its one command, and
  inside parentheses it never reaches the persistent shell; the first word of the string is `(`.
ALLOWED group-assignment: `{ X=1 ls; }`, the same for a brace group.
ALLOWED ps-local-variable: `$x = 1; ls` and `$ErrorActionPreference = 'Stop'` are how an ordinary
  PowerShell script begins and no harm was measured for them, so they stay allowed until a project
  turns on `deny_powershell_assignment`. With it on, only a leading `$name = value` is read: a
  multiple assignment (`$a, $b = 1, 2`), `Set-Variable` and `New-Variable` still pass.
ALLOWED ps-bare-set-location: `Set-Location` with no target, or with only switches, stays where it is.
ALLOWED eval-string: a mover inside the string given to `eval`, `Invoke-Expression` or `iex` is not
  read. (`bash -c "cd /x"` runs a child process and is harmless; a string given to `eval` runs in
  the persistent shell and is not looked into.)
ALLOWED sourced-script: `source x.sh` and `. x.sh` run a file this hook does not open.
ALLOWED ps-pipeline-mover: `Get-Item .ai | Set-Location` moves to a target that arrives through the
  pipeline. A mover with no explicit target is judged as having none, which PowerShell leaves in place.
ALLOWED variable-held-command: a mover whose command word is a variable, as in `"$c" /x`, is not read.
ALLOWED other-mover-spelling: `popd`, `Pop-Location`, a PowerShell alias made with `Set-Alias`, and
  every other spelling that reaches a mover are not read. Among them: in PowerShell, `cd` glued to
  a backslash or to two dots (a move to the drive root or up one level), and a parameter that is
  abbreviated and bound to its value by a colon (`Set-Location -Pat:<path>`; with a space before
  the value the path is read). A shadow made with `Set-Alias` is likewise not read, nor is one
  made with a scope prefix (`function global:cd`) or by redefining `Set-Location` itself, and
  `declare -f cd` and `unalias cd` print or remove a definition, so they are not shadows.
ALLOWED ansi-c-target: a `cd` target quoted in the ANSI-C style that writes its slash as an escape
  sequence is read with the backslashes dropped, so it looks relative.
ALLOWED non-heredoc-shift: `echo $[1<<2]` is a shift inside the legacy arithmetic expansion, but
  outside `(( ))` and `$(( ))` the scanner reads `<<2` as the start of a heredoc, and the body of a
  heredoc is data until its marker line, so a `cd` on a later line is not seen. (An unquoted
  `let x=1<<2` IS a heredoc to the shell as well, and hides the later lines from the shell too.)
ALLOWED unread-leading-assignment: the assignment rule reads the first word of the text. An
  assignment that is the real first word of the command but not the first word of the text passes:
  one after a comment line (`# note`, then `FOO=1 cmd` on the next line), one after `time` or
  `sudo`, one inside `env -S '...'`, and, in PowerShell, one inside parentheses (`($env:X = 1); ls`)
  or made with `Set-Item Env:X 1`. (`command FOO=1 ls` is not an assignment: `command` looks
  `FOO=1` up as a command name.)
ALLOWED wrapped-disguise: the assignment rule reads the first word of the text as it is written, so
  any disguise reached through a path, `command`, `builtin` or a backslash passes:
  `/usr/bin/env X=1 cmd`, `command env X=1 cmd`, `command export A=1; make`,
  `builtin export A=1; make`, `\\export A=1; make` and `command declare -x A=1; make` each do what
  the refused spelling without the wrapper does. A backslash before `cd` is read through, because
  the move rule reads words with their quoting removed (`\\cd /x` is refused), while a backslash
  before `export` is not. Like the `time` and `sudo` shapes above, each is one rephrase away from a
  refused call.
ALLOWED ps-mover-not-first-word: a PowerShell mover is read only as the first word of a statement
  (after `&` and opening parentheses), so one that is not passes: after an assignment
  (`$null = Set-Location <dir>`, which `deny_powershell_assignment` refuses as an assignment),
  inside a cast (`[void](Set-Location <dir>)`), as the parenthesised argument of another command
  (`Write-Output (Set-Location <dir>)`) and in the condition of an `if`. Each of them does move
  the location; finding a mover anywhere inside an expression would take a parser, which this
  small core is not.
ALLOWED continuation-context: a backslash before a newline is removed from the text before it is
  read, wherever it sits, so two shapes that a shell reads differently pass: a comment that ends
  in a backslash (the shell ends the comment at the newline and runs the next line) and an escaped
  backslash before a newline (the shell does not continue the line). In PowerShell the same two
  with a backtick: a comment that ends in one, and a doubled one before a newline.

REFUSED ps-job-block: `Start-Job { Set-Location /x }` runs its block in another process, so the
  persistent location is unchanged, but a script block is judged like any other statement list.
REFUSED ps-escape-letter-in-name: in a command word PowerShell reads a backtick before one of its
  escape letters as a control character (in Windows PowerShell 5.1: `0`, `a`, `b`, `f`, `n`, `r`,
  `t` and `v`), so a backtick before the `a` of `Set-Location` leaves a name that is no command,
  and nothing moves. The hook drops every backtick alike, reads `Set-Location` and refuses a call
  that would not have run. A backtick before any other letter is only dropped, by both.
REFUSED unexecuted-code: `function f { cd /x; }`, `f() { cd /x; }` and `if false; then cd /x; fi`
  only define a function or name a branch that never runs, so nothing moves, but their bodies are
  judged like any other statement: the hook cannot tell a body that is never run from one that is.
REFUSED glued-hash-after-paren: `(true)#x; cd /x` and `echo a)#x; cd /x`. After the `)` that closes
  a subshell a shell reads `#` as the start of a comment (and a lone `)` after a word is a syntax
  error), so the `cd` never runs. The hook reads `#` as a comment only at the start of a word, and
  the word goes on after the `)` of `$( )`, `$(( ))` and `<( )`, where a glued `#` is NOT a comment
  and the `cd` after it does run. The scanner does not tell the two kinds of `)` apart, so it
  judges the `cd` and refuses.

Other limits, without a row of their own: the lexer reads quotes, comments, heredocs, here-strings,
parentheses, braces and line continuation, and it is not a parser, so a construct it does not model
(a double quote nested inside `$( )` inside double quotes, a `${...}` that holds a separator) can
hide a later statement. An allowed folder spelled with a Git Bash drive prefix (`/c/...`) is refused,
and the denial text names the spellings that are accepted. The hook cannot tell a `cd` that was never
run (a function body that is never called, a branch that is not taken) from one that was.
A line of any length is judged in full: the scan is linear in its length, so there is no length limit
to guess at. Runs of the words that only introduce a command (`!`, `if`, `time -p`, PowerShell's `&`
and bare parentheses) were once read by slicing a list per word, which made them quadratic; a test
pins them.

Contract: reads the PreToolUse payload on stdin and prints either one JSON object (a deny decision, or
a warning when the switch file is unusable) or nothing. It exits 0 in every case, and a payload it
cannot use, or a bug in the scanner, is an allow: a guard that crashes must not block unrelated work.
"""

import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

CONFIG_PARTS = (".ai", "shell-prefix-hook.json")
CONFIG_KEYS = (
    "enabled",
    "deny_relative_cd",
    "deny_set_location",
    "deny_powershell_assignment",
    "allowed_forms",
)
_FLAG_KEYS = CONFIG_KEYS[:4]
_FORM_KEYS = frozenset({"tool", "folder", "then"})
_TOOLS = ("Bash", "PowerShell")

MOVE = "move"
SHADOW = "shadow"
ASSIGN = "assign"

_TEXTS = {
    MOVE: (
        "Do not move the shell's working directory (cd, pushd, Set-Location, Push-Location: "
        "wherever they sit in the command). The Bash and PowerShell tools keep ONE working "
        "directory across calls, so one move silently re-bases every later call in the session, "
        "and a prefix in front of the command defeats the permission rules that match on the bare "
        "command. Name the directory where it is used instead: git -C <dir>, an absolute path "
        "argument, or the command's own directory option; read other trees with the Read, Glob and "
        "Grep tools and absolute paths. For several steps, write them to a script file and run "
        "that."
    ),
    SHADOW: (
        "Do not redefine, alias or replace cd to get past this hook. A shadowed cd leaves the "
        "path in the command and hides the move this hook exists to stop. Name the directory "
        "where it is used instead: git -C <dir>, an absolute path argument, or the Read, Glob and "
        "Grep tools with absolute paths."
    ),
    ASSIGN: (
        "Drop the leading variable assignment (NAME=value, export NAME=value, env NAME=value, "
        "$env:NAME = value, a throwaway assignment of any name, and in the PowerShell tool a "
        "$name = value where this project denies those). A prefix in front of the command defeats "
        "the permission rules that match on the bare command, so every allow-listed command "
        "prompts again. Instead: inline the value where it is used; put multi-step logic in a "
        "script file and run that; for UTF-8 output use the interpreter's own switch (Python: "
        "-X utf8) and not an environment variable. A variable set in one call is gone in the next, "
        "so do not plan to set it once and reuse it."
    ),
}


# ----------------------------------------------------------------------------------- the switch


@dataclass(frozen=True)
class AllowedForm:
    tool: str
    folder: str
    then: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    enabled: bool = False
    deny_relative_cd: bool = False
    deny_set_location: bool = False
    deny_powershell_assignment: bool = False
    allowed_forms: tuple[AllowedForm, ...] = ()


_DRIVE = re.compile(r"[A-Za-z]:")


def _normalize(path: str) -> str:
    """Separators as `/`, no trailing slash, a lower-case drive letter. Nothing else is resolved."""
    text = path.replace("\\", "/")
    if len(text) > 1:
        text = text.rstrip("/") or "/"
    if _DRIVE.match(text):
        text = text[0].lower() + text[1:]
    return text


def _plain_folder(value: object) -> bool:
    """A relative folder under the project root: no drive, no leading separator or `~`, no `..`."""
    if not isinstance(value, str) or not value.strip():
        return False
    if value[0] in "/\\~" or _DRIVE.match(value) or "$" in value or "`" in value:
        return False
    segments = value.replace("\\", "/").split("/")
    return ".." not in segments and _normalize(value) not in (".", "")


def _plain_word(value: object) -> bool:
    return (
        isinstance(value, str) and bool(value) and not any(c.isspace() for c in value)
    )


def _validate_forms(raw: object, problems: list[str]) -> tuple[AllowedForm, ...]:
    if not isinstance(raw, list):
        problems.append("allowed_forms must be a list")
        return ()
    forms: list[AllowedForm] = []
    for index, item in enumerate(raw):
        label = f"allowed_forms[{index}]"
        if not isinstance(item, dict) or set(item) != _FORM_KEYS:
            problems.append(
                f"{label} must be an object with exactly the keys tool, folder and then"
            )
            continue
        tool, folder, then = item["tool"], item["folder"], item["then"]
        complete = True
        if tool not in _TOOLS:
            problems.append(f"{label}.tool must be Bash or PowerShell")
            complete = False
        if not _plain_folder(folder):
            problems.append(
                f"{label}.folder must be a relative folder under the project root, without .."
            )
            complete = False
        if not (
            isinstance(then, list) and then and all(_plain_word(word) for word in then)
        ):
            problems.append(f"{label}.then must be a non-empty list of command words")
            complete = False
        if complete:
            forms.append(AllowedForm(tool, _normalize(folder), tuple(then)))
    return tuple(forms)


def _validate(data: object) -> tuple[Config | None, list[str]]:
    if not isinstance(data, dict):
        return None, ["the top level must be a JSON object"]
    fields = {str(key): value for key, value in data.items()}
    problems: list[str] = []
    unknown = sorted(key for key in fields if key not in CONFIG_KEYS)
    if unknown:
        problems.append("unknown key(s): " + ", ".join(unknown[:5]))
    flags: dict[str, bool] = {}
    for key in _FLAG_KEYS:
        value = fields.get(key, False)
        if not isinstance(value, bool):
            problems.append(f"{key} must be true or false")
        flags[key] = value is True
    forms = _validate_forms(fields.get("allowed_forms", []), problems)
    if problems:
        return None, problems
    return Config(allowed_forms=forms, **flags), []


def load_config(project_dir: str) -> tuple[Config | None, list[str]]:
    """The project's switch file as a Config, (None, []) when there is none, (None, problems) when it
    cannot be used. Read on every call."""
    path = os.path.join(project_dir, *CONFIG_PARTS)
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except (FileNotFoundError, NotADirectoryError):
        return None, []
    except OSError as error:
        return None, [f"it cannot be read ({type(error).__name__})"]
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        return None, ["it is not UTF-8 text"]
    except RecursionError:
        return None, ["it is nested too deeply"]
    except ValueError as error:
        return None, [f"it is not valid JSON ({str(error)[:80]})"]
    return _validate(data)


# --------------------------------------------------------------------------------------- the lexer

# A backslash before a newline continues a command; so does a backtick in PowerShell.
_CONTINUATION = re.compile(r"\\\r?\n")
_CONTINUATION_POWERSHELL = re.compile(r"`\r?\n")

# Bash. One pass, every alternative linear: a token is matched at a position and consumed, and the
# alternatives that scan ahead (quotes) fail at most once per kind, because a failed quote means no
# closing quote exists after it. A `#` starts a comment only at the start of a word: after
# whitespace, a separator or `(`. After `)` it does not, because the word goes on after the `)` of
# `$( )`, `$(( ))` and `<( )`.
_BASH_TOKEN = re.compile(
    r"""
      (?P<ansic>\$'(?:\\.|[^'\\])*')
    | (?P<sq>'[^']*')
    | (?P<dq>"(?:\\.|[^"\\])*")
    | (?P<bt>`[^`]*`)
    | (?P<heredoc><<-?[ \t]*(?:(?P<quote>['"])(?P<qtag>[^'"\n]*)(?P=quote)|\\?(?P<tag>[^\s;&|()<>'"\\]+)))
    | (?P<comment>(?<![^\s;&|(])\#[^\n]*)
    | (?P<redirect>[0-9]*[<>]+&?[0-9-]*|&>>?)
    | (?P<fndef>\(\s*\))
    | (?P<open>\$?\(+)
    | (?P<close>\)+)
    | (?P<sep>&&|\|\||[;&|\n])
    | (?P<space>[ \t\r\f\v]+)
    | (?P<word>(?:\\.|\$(?!')|[^\s;&|()'"`<>\\$])+)
    | (?P<rest>.)
    """,
    re.VERBOSE | re.DOTALL,
)

# PowerShell: braces always delimit script blocks, `&` is the call operator (a word), the escape
# character is the backtick and a quote is doubled to escape it. A here-string or a block comment
# is only OPENED here; its end is found with `str.find` in the loop, so an unterminated one costs
# one pass over the rest of the text and not one pass per opener.
_POWERSHELL_TOKEN = re.compile(
    r"""
      (?P<herestart>@['"][ \t]*\r?\n)
    | (?P<blockcomment><\#)
    | (?P<comment>(?<![^\s;|(){}])\#[^\n]*)
    | (?P<sq>'(?:[^']|'')*')
    | (?P<dq>"(?:`.|""|[^"`])*")
    | (?P<sep>&&|\|\||[;|{}\n])
    | (?P<space>[ \t\r\f\v]+)
    | (?P<word>(?:`.|[^\s;|{}'"`])+)
    | (?P<rest>.)
    """,
    re.VERBOSE | re.DOTALL,
)

_PIECES = frozenset({"sq", "dq", "bt", "word", "rest", "ansic"})
_BASH_ESCAPE = re.compile(r"\\(.)", re.DOTALL)
_BASH_DQ_ESCAPE = re.compile(r'\\([\\"$`\n])')
_POWERSHELL_ESCAPE = re.compile(r"`(.)", re.DOTALL)

# Words that only introduce the command that follows them.
_BASH_PREFIXES = frozenset(
    {
        "time",
        "command",
        "builtin",
        "!",
        "if",
        "then",
        "else",
        "elif",
        "do",
        "while",
        "until",
    }
)
_WITH_OPTIONS = frozenset({"time", "command", "builtin"})
# `command -v cd` and `command -pV cd` say what a name is and run nothing.
_LOOKUP_OPTION = re.compile(r"-\w*[vV]")


def _unquote(kind: str, text: str, powershell: bool) -> str:
    """The value of one piece of a word, so `cd "$R"` reads as the target `$R`."""
    if kind == "sq":
        return text[1:-1].replace("''", "'") if powershell else text[1:-1]
    if kind == "dq":
        inner = text[1:-1]
        if powershell:
            return _POWERSHELL_ESCAPE.sub(r"\1", inner).replace('""', '"')
        return _BASH_DQ_ESCAPE.sub(r"\1", inner)
    if kind == "bt":
        return text
    if kind == "ansic":
        return _BASH_ESCAPE.sub(r"\1", text[2:-1])
    return (_POWERSHELL_ESCAPE if powershell else _BASH_ESCAPE).sub(r"\1", text)


@dataclass
class _Statement:
    """One simple command: its words, whether it runs in the persistent shell, and the token that
    ended it (`&&`, `;`, a newline, `()` for the head of a function definition, and so on)."""

    words: list[str]
    persistent: bool
    end: str


class _Scanner:
    """Collects the statements of one command string, one token at a time."""

    def __init__(self, powershell: bool) -> None:
        self.powershell = powershell
        self.found: list[_Statement] = []
        self.words: list[str] = []
        self.pieces: list[str] = []
        self.depth = 0  # parentheses open: above 0 is a subshell or a substitution
        self.started_at_depth = 0
        self.arith_depth = (
            0  # inside `$(( ))` or `(( ))`: the depth it opened at, else 0
        )
        self.piped = False  # the next statement is a segment of a Bash pipeline
        self.in_subshell = False

    def end_word(self) -> None:
        if not self.pieces:
            return
        word, self.pieces = "".join(self.pieces), []
        # In command position a Bash brace is a group delimiter that stays in this shell.
        if word in ("{", "}") and not self.powershell and self._group_position():
            self.end_statement(word)
            return
        if not self.words:
            self.started_at_depth = self.depth
            self.in_subshell = self.piped
            self.piped = False
        self.words.append(word)

    def _group_position(self) -> bool:
        return all(word in _BASH_PREFIXES for word in self.words) or (
            len(self.words) == 2 and self.words[0] == "function"
        )

    def end_statement(self, end: str, subshell: bool = False) -> None:
        self.end_word()
        if self.words:
            persistent = self.started_at_depth == 0 and not (
                self.in_subshell or subshell
            )
            self.found.append(_Statement(self.words, persistent, end))
            self.words = []

    def open_paren(self, token: str) -> None:
        self.end_statement("(")
        self.depth += token.count("(")
        if token.count("(") >= 2:
            self.arith_depth = self.depth

    def close_paren(self, token: str) -> None:
        self.end_statement(")")
        self.depth = max(0, self.depth - len(token))
        if self.depth < self.arith_depth:
            self.arith_depth = 0

    def separator(self, token: str) -> None:
        # `cmd &` and every segment of `a | b` run in a subshell in Bash; PowerShell pipelines
        # and background jobs are not modelled.
        self.end_statement(token, subshell=not self.powershell and token in ("&", "|"))
        if not self.powershell and token == "|":
            self.piped = True


def _skip_heredoc_bodies(text: str, pos: int, pending: list[tuple[str, bool]]) -> int:
    """Move past the bodies of the heredocs opened on the line that just ended: their text is data."""
    for tag, strip_tabs in pending:
        while pos < len(text):
            eol = text.find("\n", pos)
            line_end = len(text) if eol == -1 else eol
            line = text[pos:line_end].rstrip(" \t\r")
            pos = len(text) if eol == -1 else eol + 1
            if (line.lstrip("\t") if strip_tabs else line) == tag:
                break
    return pos


def _statements(text: str, powershell: bool) -> list[_Statement]:
    token = _POWERSHELL_TOKEN if powershell else _BASH_TOKEN
    scan = _Scanner(powershell)
    pending: list[tuple[str, bool]] = []
    pos, size = 0, len(text)
    while pos < size:
        match = token.match(text, pos)
        if (
            match is None
        ):  # cannot happen: the last alternative takes any single character
            pos += 1
            continue
        kind, piece, pos = match.lastgroup, match.group(), match.end()
        if kind in _PIECES:
            scan.pieces.append(_unquote(kind, piece, powershell))
            continue
        scan.end_word()
        if kind == "herestart":
            # the text up to the closing marker is data; an unterminated one runs to the end
            closing = "\n" + piece[1] + "@"
            found = text.find(closing, pos)
            pos = size if found == -1 else found + len(closing)
            scan.pieces.append(
                "@"
            )  # a here-string given to a mover is an unreadable target
        elif kind == "blockcomment":
            found = text.find("#>", pos)
            pos = size if found == -1 else found + 2
        elif kind == "heredoc":
            if (
                scan.arith_depth
            ):  # `$(( a << n ))` is a shift, not a heredoc: lex what follows `<<`
                pos = match.start() + 2
                continue
            tag = match.group("tag")
            pending.append(
                (
                    tag if tag is not None else match.group("qtag"),
                    piece.startswith("<<-"),
                )
            )
        elif kind == "open":
            scan.open_paren(piece)
        elif kind == "close":
            scan.close_paren(piece)
        elif kind == "fndef":
            scan.end_statement("()")
        elif kind == "sep":
            scan.separator(piece)
            if piece == "\n" and pending:
                pos, pending = _skip_heredoc_bodies(text, pos, pending), []
    scan.end_statement("")
    return scan.found


# ------------------------------------------------------------------------------------- the rules

_BASH_MOVERS = frozenset({"cd", "pushd"})
_POWERSHELL_MOVERS = frozenset(
    {"set-location", "sl", "push-location", "cd", "chdir", "pushd"}
)
# The spellings `deny_set_location` governs; every other mover is governed by `deny_relative_cd`.
_SET_LOCATION_WORDS = frozenset({"set-location", "sl", "push-location"})
_POWERSHELL_PATH_PARAMETERS = frozenset({"-path", "-literalpath", "-pspath"})
# A target that is not relative: a drive, `~`, a slash of either kind, a variable or a substitution.
_NOT_RELATIVE = re.compile(r"[A-Za-z]:|[~/\\$`]")
# PowerShell only: a target that is no plain path. A name and a colon is a provider path (`HKLM:`,
# `Env:`); a leading `@` is an array expression or a splat; a leading `(` is an expression.
_POWERSHELL_UNREADABLE = re.compile(r"[@(]|[^:]*:")
# `(cd x)`, `$(cd x)` and `@(cd x)`: the opening that is not part of the command word itself.
_POWERSHELL_OPEN = re.compile(r"(?:[$@]?\()+")


def _strip_open(word: str) -> str:
    opening = _POWERSHELL_OPEN.match(word)
    return word[opening.end() :] if opening else word


def _skip_options(prefix: str, words: list[str], index: int) -> int | None:
    """The index of the first word after `time`, `command` or `builtin` and its options, counting from
    `index`; None when it runs nothing. Walks by index: slicing the list once per word would make a
    long run of options cost the square of its length."""
    while index < len(words) and words[index].startswith("-") and words[index] != "-":
        option = words[index]
        index += 1
        if prefix == "command" and _LOOKUP_OPTION.match(option):
            return None
        if option == "--":
            break
    return index


def _skip_prefixes(words: list[str], powershell: bool) -> list[str]:
    """The command's own words, after the keywords and wrappers that only introduce it. The words are
    walked by index and cut once at the end, so the cost grows with their number and not its square."""
    index = 0
    if powershell:
        while index < len(words) and (
            words[index] == "&" or not _strip_open(words[index])
        ):
            index += 1
        if index == len(words):
            return []
        return [_strip_open(words[index]), *words[index + 1 :]]
    while index < len(words) and words[index] in _BASH_PREFIXES:
        prefix = words[index]
        index += 1
        if prefix in _WITH_OPTIONS:
            skipped = _skip_options(prefix, words, index)
            if skipped is None:
                return []
            index = skipped
    return words[index:]


def _target_of(args: list[str], powershell: bool) -> str | None:
    """The path a mover is given, skipping options (`cd -P /x`, `Set-Location -Path /x`). `--` ends
    the options: the word after it is the target even when it starts with a dash."""
    remaining = iter(args)
    for arg in remaining:
        if powershell:
            name, colon, value = arg.partition(
                ":"
            )  # `-Path:/x` binds the value in one word
            if name.lower() in _POWERSHELL_PATH_PARAMETERS:
                return value if colon and value else next(remaining, None)
        if arg == "-":
            return arg
        if arg == "--":
            return next(remaining, None)
        if arg.startswith("-") and len(arg) > 1:
            continue
        return arg
    return None


def _move_rule(words: list[str], config: Config, powershell: bool) -> str | None:
    """The name of the rule that refuses this simple command, or None."""
    command = words[0].lower() if powershell else words[0]
    if command not in (_POWERSHELL_MOVERS if powershell else _BASH_MOVERS):
        return None
    target = _target_of(words[1:], powershell)
    if target is None:
        return (
            None if powershell else "bare-cd"
        )  # a bare `cd` goes home; a bare Set-Location stays
    if target == "-" or _NOT_RELATIVE.match(target):
        return "absolute-cd"
    if powershell and _POWERSHELL_UNREADABLE.match(target):
        return "absolute-cd"
    if target in (".", "./"):
        return None
    if command in _SET_LOCATION_WORDS:
        return "relative-set-location" if config.deny_set_location else None
    return "relative-cd" if config.deny_relative_cd else None


def _is_shadow(words: list[str], end: str, powershell: bool) -> bool:
    first = words[0].lower() if powershell else words[0]
    if first == "function" and len(words) > 1:
        return (words[1].lower() if powershell else words[1]) == "cd"
    if end == "()" and words == ["cd"]:
        return True  # `cd() { :; }` and `cd () { :; }`
    return first == "alias" and any(word.startswith("cd=") for word in words[1:])


# Leading assignments are read from the start of the text, so the shapes that look like one inside
# a subshell or a group (`( X=1 ls )`, `{ X=1 ls; }`) are not leading ones.
_ASSIGNMENT_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
_NON_SPACE = re.compile(r"\S+")
_POWERSHELL_ENV = re.compile(
    r"\s*(?:\$env:[A-Za-z_][A-Za-z0-9_]*|\$\{env:[^}]+\})\s*(?:[-+*/%]|\?\?)?=",
    re.IGNORECASE,
)
_POWERSHELL_VARIABLE = re.compile(
    r"\s*(?:\[[^\]\n]*\]\s*)?\$(?:(?:script|global|local|private|using):)?[A-Za-z_][A-Za-z0-9_]*"
    r"\s*(?:[-+*/%]|\?\?)?=(?!=)",
    re.IGNORECASE,
)
_ENV_OPTIONS_WITH_ARGUMENT = frozenset(
    {"-u", "-C", "-S", "-a", "--unset", "--chdir", "--split-string", "--argv0"}
)


def _first_operand_is_assignment(tokens: list[str]) -> bool:
    return bool(tokens) and _ASSIGNMENT_WORD.match(tokens[0]) is not None


_DISGUISES = frozenset({"export", "readonly", "declare", "typeset", "env"})


def _leading_assignment(text: str, powershell: bool, config: Config) -> str | None:
    """The name of the rule when the command STARTS with an assignment or a disguise of one."""
    first = _NON_SPACE.search(text)
    if first is None:
        return None
    head = first.group()
    if _ASSIGNMENT_WORD.match(head):
        return "assignment"
    # the words after the head are read only for the few heads that can carry an assignment
    rest = (
        [match.group() for match in _NON_SPACE.finditer(text, first.end())]
        if head in _DISGUISES
        else []
    )
    if head in ("export", "readonly"):
        operands = [token for token in rest if not token.startswith("-")]
        return "export" if _first_operand_is_assignment(operands) else None
    if head in ("declare", "typeset"):
        options = [token for token in rest if token.startswith("-")]
        exporting = any(
            "x" in option[1:] and option[1:].isalpha() for option in options
        )
        operands = [token for token in rest if not token.startswith("-")]
        return (
            "declare" if exporting and _first_operand_is_assignment(operands) else None
        )
    if head == "env":
        skip = False
        for index, token in enumerate(rest):
            if skip:
                skip = False
            elif token in _ENV_OPTIONS_WITH_ARGUMENT:
                skip = True
            elif not token.startswith("-"):
                return "env" if _first_operand_is_assignment(rest[index:]) else None
        return None
    if powershell:
        if _POWERSHELL_ENV.match(text):
            return "powershell-env"
        if config.deny_powershell_assignment and _POWERSHELL_VARIABLE.match(text):
            return "powershell-variable"
    return None


def _same_folder(target: str, folder: str, project_dir: str) -> bool:
    """The target spelled as the folder, or as the project folder's absolute path to it."""
    spelled = _normalize(target)
    if ".." in spelled.split("/"):
        return False
    return spelled in (folder, _normalize(project_dir) + "/" + folder)


_LEADING_CD = re.compile(r"\s*cd\s", re.IGNORECASE)


def _form_exempts_first(
    text: str, statements: list[_Statement], tool: str, config: Config, project_dir: str
) -> bool:
    """Is the first statement the `cd <folder>` of an allowed form, followed by `&& <listed word>`?"""
    powershell = tool == "PowerShell"
    if not config.allowed_forms or len(statements) < 2:
        return False
    if _LEADING_CD.match(text) is None:
        return False
    first, second = statements[0], statements[1]
    if not first.persistent or first.end != "&&" or len(first.words) != 2:
        return False
    if (first.words[0].lower() if powershell else first.words[0]) != "cd":
        return False
    return any(
        form.tool == tool
        and second.words[0] in form.then
        and _same_folder(first.words[1], form.folder, project_dir)
        for form in config.allowed_forms
    )


def judge(
    command: str, tool: str, config: Config, project_dir: str
) -> tuple[str, str] | None:
    """What the hook says about `command`: (family, rule) to deny, None to allow. The switch is not
    read here; `decide` reads it."""
    powershell = tool == "PowerShell"
    text = (_CONTINUATION_POWERSHELL if powershell else _CONTINUATION).sub("", command)
    rule = _leading_assignment(text, powershell, config)
    if rule:
        return ASSIGN, rule
    statements = _statements(text, powershell)
    exempt = _form_exempts_first(text, statements, tool, config, project_dir)
    for index, statement in enumerate(statements):
        if not statement.persistent:
            continue
        words = _skip_prefixes(statement.words, powershell)
        if not words:
            continue
        if _is_shadow(words, statement.end, powershell):
            return SHADOW, "shadow"
        if index == 0 and exempt:
            continue
        rule = _move_rule(words, config, powershell)
        if rule:
            return MOVE, rule
    return None


# ----------------------------------------------------------------------------------- the reply


def _forms_sentence(config: Config, tool: str, project_dir: str) -> str:
    forms = [form for form in config.allowed_forms if form.tool == tool]
    if not forms:
        return ""
    root = project_dir.rstrip("/\\")
    allowed = "; ".join(
        f"cd {form.folder} && {' or '.join(form.then)} ... (the folder spelled {form.folder} or {root}/{form.folder})"
        for form in forms
    )
    return f" This project allows only: {allowed}."


def _warning(problems: list[str]) -> str:
    text = "; ".join(problems)[:600]
    return (
        f"shell-prefix hook: {'/'.join(CONFIG_PARTS)} is not usable ({text}); this call was not judged. "
        "Fix the file, or delete it to switch the hook off."
    )


def decide(raw: bytes, environ: Mapping[str, str]) -> str:
    """The text to print on stdout for one payload: a deny reply, a warning, or nothing at all."""
    try:
        payload: Any = json.loads(raw.decode("utf-8-sig", errors="replace"))
        tool = payload["tool_name"]
        command = payload["tool_input"]["command"]
    except Exception:  # fail open: a payload that cannot be read is an allow
        return ""
    if tool not in _TOOLS or not isinstance(command, str):
        return ""
    project = environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
    if not isinstance(project, str) or not project:
        return ""
    config, problems = load_config(project)
    if problems:
        return json.dumps({"systemMessage": _warning(problems)})
    if config is None or not config.enabled:
        return ""
    found = judge(command, tool, config, project)
    if found is None:
        return ""
    family = found[0]
    reason = _TEXTS[family] + (
        _forms_sentence(config, tool, project) if family == MOVE else ""
    )
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def main() -> None:
    try:
        raw = sys.stdin.buffer.read()
        out = decide(raw, os.environ)
    except Exception:  # fail open: a bug here must never block unrelated work
        return
    if out:
        sys.stdout.write(out)  # ASCII only: json.dumps escapes everything else
        sys.stdout.flush()


if __name__ == "__main__":
    main()
