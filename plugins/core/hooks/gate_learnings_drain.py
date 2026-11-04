"""PreToolUse guard: a learnings DRAIN may not run without its approved plan.

Why this exists (measured, not theoretical): `learning-consolidator` Phase 3 ends with
"**STOP and wait for user approval before proceeding.**" — prose. The 2026-09-13 drain
removed **263** entries from `.ai/learnings.md` without ever presenting that plan. Prose
already said to; prose is what failed, so the rule is enforced here instead.

WHAT IT BLOCKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
Only **removal** of entries from `.ai/learnings.md` is gated. Appends are the intake path —
`task-learnings` writes to this file constantly and must stay frictionless — so a call that
adds entries, or leaves the entry count unchanged, is never blocked. The gate fires on the
one irreversible act: deleting entries that a promotion is supposed to have re-homed.

THE GATE RECORD
---------------
`.ai/consolidation-gates/<YYYY-MM-DD>-plan-approved.md`, containing the Phase 3 plan the
operator approved. Absent or empty -> the drain is denied with the path it needs.

HONEST LIMITS — read these before trusting the guard
----------------------------------------------------
1. **The record is forgeable.** Nothing here proves a human approved anything; a model can
   Write that file itself. What the guard changes is the SHAPE of the failure: skipping the
   gate stops being an omission (invisible, deniable, what happened on 2026-09-13) and
   becomes a conspicuous written claim in a dated file, which `consolidation-critic` and the
   changelog can be audited against afterwards. That is a real improvement and it is not
   enforcement. Closing it properly needs the stamp to come from a `UserPromptSubmit` hook —
   which sees the operator's own message and the model never gets to author — carrying a
   nonce this guard verifies. Sketched, deliberately not built: it is a bigger change than
   the defect warrants today.
2. **The shell arm is best-effort.** It cannot count entries, so it reads the command the way
   a shell does (quotes, comments, heredoc bodies, `;` `&&` `||` `|` and a lone `&`) and
   denies a command that names the file when the command word and its arguments are a shape
   that can rewrite or delete it: `sed -i`, a `>` redirect whose target is the file, `rm`,
   `mv` whose destination is the file, `tee` without `-a`, `xargs rm` or `find -exec rm` on
   it, an inline python script (`-c`, a lone `-`, a heredoc, or no script argument) whose code
   writes, and, for the PowerShell tool, `Set-Content`, `Clear-Content`, `Remove-Item`,
   `Out-File` without `-Append` (aliases included) and `Get-Item | Remove-Item`. A name held in
   a variable assigned on the same command is followed. Appends (`>>`, `tee -a`,
   `Add-Content`, `Out-File -Append`) and reads are never matched. A line over `_MAX_LINE`
   characters is denied rather than guessed at (cannot-measure is never a pass).
   It is still text matching, so a rephrasing reaches it. Known gaps, not decisions to allow
   them: `truncate`, `perl -i`, `awk -i inplace`, `cp` over the file, `git checkout`, `git
   restore` or `git stash` of the file, `mv` or `Move-Item` of the file away, `.NET` file
   calls, `ed` and `vim -es`, `pwsh -c` and `ipython -c`, a script file that holds the path (`bash x.sh`, `python x.py`),
   a path built in pieces, `bash -c "..."` and `eval`, and every command that removes the file
   without naming it (`rm -rf .ai`, `git reset --hard`). Known false positive: a python
   script that reads the file and writes some OTHER file is denied, because the write is not
   tied to the file. The Edit/Write arms are exact because they see the content; the shell
   arm is a speed bump.
3. **Hook config snapshots at session start**, so registering this engages next session; the
   plugin documentation says `/reload-plugins` loads a change into a session that is already open,
   which was not tried here.
4. It fails **open** on any malformed payload. A guard that crashes must not block unrelated
   work.

Contract: reads the PreToolUse payload on stdin, prints a deny decision as JSON when the call
would remove entries without an approved plan, prints nothing otherwise. Never raises.
"""

import datetime
import json
import os
import re
import shlex
import sys

LEARNINGS_SUFFIX = os.path.join(".ai", "learnings.md")
ENTRY_RE = re.compile(r"^### ", re.MULTILINE)

# A line this long is not judged: the call is denied with that reason. A guard that cannot
# measure must not report a pass. The longest line of a real command that named the file, over
# a month of transcripts, was 3.5 KB.
_MAX_LINE = 10000

# The file as a command names it: the whole name, in any case (the file system may not care).
# A longer name that ends in it (`seed-learnings.md`), starts with it (`learnings.md.bak`) or is
# an editor backup of it (`learnings.md~`) is another file.
_FILE_RE = re.compile(r"(?<![\w.\-])learnings\.md(?![\w.\-~])", re.IGNORECASE)

# A backslash before a newline continues a command; so does a backtick in PowerShell.
_CONTINUATION = re.compile(r"\\\r?\n")
_CONTINUATION_POWERSHELL = re.compile(r"(?:\\|`)\r?\n")

# `< file` feeds the file to a command; it never writes it.
_INPUT_REDIRECT = re.compile(r"<\s*[^\s|;&<>]+")
# A redirect whose TARGET is the file: `>`, `N>` or `>|`. Not `>>` (an append), not `>&` (a
# descriptor copy such as `2>&1`), and not a `>` inside quoted code (`NR>=3`): the target must
# start right after the operator and be one word that ends in the file name.
_REDIRECT_ONTO_FILE = re.compile(
    r"(?<![>\\])>(?:&(?![\d\s-]))?\|?\s*[\"']?[^\s\"'|;&<>]{0,500}(?<![\w.\-])learnings\.md(?![\w.\-~])",
    re.IGNORECASE,
)
# A redirect inside a command's own arguments: the operator alone (the target is the next
# word) or with its target attached.
_REDIRECT_ALONE = re.compile(r"^(?:\d*>>?|&>>?|\d*<)$")
_REDIRECT_ATTACHED = re.compile(r"^(?:\d*>>?|&>>?|\d*<{1,3}|\d*>&|\d*<&)\S")
_HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*([\"']?)([A-Za-z_]\w*)\1")

# `NAME=path-to-the-file` on the command line: later `$NAME` and `${NAME}` are the file.
_BASH_ASSIGNMENT = re.compile(
    r"(?<![\w$])([A-Za-z_]\w*)=([\"']?)([^\s\"';|&]*learnings\.md)\2", re.IGNORECASE
)
_POWERSHELL_ASSIGNMENT = re.compile(
    r"\$([A-Za-z_]\w*)\s*=\s*([\"'])([^\"']*learnings\.md)\2", re.IGNORECASE
)

# Words that run another command: `sudo rm file` is `rm file`.
_WRAPPERS = frozenset(
    {"sudo", "command", "builtin", "exec", "time", "nohup", "env", "nice"}
    | {"timeout", "ionice"}
    | {"then", "do", "else", "if", "while", "until", "!", "{"}
)
_LAUNCHERS = frozenset({"uv", "uvx", "poetry", "pipenv", "pyenv", "conda", "winpty"})
_POWERSHELL_SET = frozenset({"set-content", "sc"})
_POWERSHELL_CLEAR = frozenset({"clear-content", "clc"})
_POWERSHELL_REMOVE = frozenset({"remove-item", "ri", "del", "erase", "rmdir", "rd"})
_POWERSHELL_LISTERS = frozenset({"get-item", "gi", "get-childitem", "gci", "ls", "dir"})

# `tee -a` appends; the short flags tee takes are a, i and p, alone or combined, and a long
# option may be shortened to any unambiguous prefix. PowerShell takes -Append, shortened.
_TEE_APPEND = re.compile(
    r"^(?:-[aip]{0,3}a[aip]{0,3}|--a(?:p(?:p(?:e(?:n(?:d)?)?)?)?)?)$"
)
_POWERSHELL_APPEND = re.compile(
    r"^-a(?:p(?:p(?:e(?:n(?:d)?)?)?)?)?(?::\$true)?$", re.IGNORECASE
)
# `-i` takes an attached suffix (`-i.bak`); `--in-place` may be shortened to `--in`.
_SED_IN_PLACE = re.compile(r"^(?:-(?!-)[A-Za-z]*i|--in(?:-[A-Za-z-]*)?(?:=.*)?$)")
_PYTHON_WORD = re.compile(r"^(?:python[0-9.]*|py)$")
_PYTHON_DASH_C = re.compile(r"^-[A-Za-z]*c(?:[\"'].*)?$")

# What inline python does that writes. The mode is a short string, so it is matched in a short
# window (a longer one is quadratic); a backslash before the quote is a quote escaped inside a
# double-quoted `python -c "..."`.
_PYTHON_WRITES = re.compile(
    r"""\b(?:os\.)?open\s*\((?:[^()\n]|\([^()\n]*\)){0,300}?,\s*(?:mode\s*=\s*)?\\?["'](?!a)[^"']{0,8}?[wx+]"""
    r"""|\.open\s*\(\s*(?:mode\s*=\s*)?\\?["'](?!a)[^"']{0,8}?[wx+]"""
    r"|\.write_text\s*\(|\.write_bytes\s*\(|\.truncate\s*\(|\.unlink\s*\("
    r"""|\.(?:replace|rename)\s*\(\s*\\?["'][^"']*learnings\.md\\?["']\s*\)"""
    r"|\bos\.(?:replace|rename|remove|unlink|truncate)\s*\("
    r"|\bos\.open\s*\([^)]{0,200}O_(?:TRUNC|WRONLY|RDWR)"
    r"|\bfileinput\b[^\n]{0,300}inplace"
    r"""|\\?["']--?in(?:-place)?\\?["']"""
    r"|\bshutil\.(?:copy\w*|move|rmtree)\s*\(",
    re.IGNORECASE,
)


def _targets_learnings(path):
    return isinstance(path, str) and path.replace("/", os.sep).endswith(
        LEARNINGS_SUFFIX
    )


def _count(text):
    return len(ENTRY_RE.findall(text or ""))


def _expand_variables(text, tool):
    """Replace `$NAME` by the file when the command assigns the file name to NAME."""
    pattern = _POWERSHELL_ASSIGNMENT if tool == "PowerShell" else _BASH_ASSIGNMENT
    for match in list(pattern.finditer(text))[:8]:
        name, value = match.group(1), match.group(3)
        text = re.sub(
            r"\$\{?" + re.escape(name) + r"\}?(?!\w)",
            lambda _, value=value: value,
            text,
            flags=re.IGNORECASE if tool == "PowerShell" else 0,
        )
    return text


def _pipelines(text, tool):
    """Split a command into pipelines of segments the way a shell reads it.

    Quotes, comments and heredoc bodies are honoured: `;` `&&` `||` and a newline end a
    pipeline, `|` ends a segment inside one, a lone `&` ends both in a shell (it is the call
    operator in PowerShell), and none of them counts inside quotes. Heredoc body lines are
    text, not commands, so they are dropped here (the python check reads the raw text).
    """
    escape = "`" if tool == "PowerShell" else "\\"
    pipelines, segments, buf = [], [], []
    quote, pending = None, []
    i, n = 0, len(text)

    def end_segment():
        segment = "".join(buf).strip()
        buf.clear()
        if segment:
            segments.append(segment)

    def end_pipeline():
        end_segment()
        if segments:
            pipelines.append(segments[:])
        segments.clear()

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if quote:
            buf.append(c)
            if c == escape and quote == '"' and nxt:
                buf.append(nxt)
                i += 1
            elif c == quote:
                quote = None
        elif c in "'\"":
            quote = c
            buf.append(c)
        elif c == escape and nxt:
            buf.append(c + nxt)
            i += 1
        elif c == "<" and nxt == "<" and tool != "PowerShell":
            marker = _HEREDOC.match(text, i)
            if marker:
                pending.append(marker.group(2))
            buf.append(c)
        elif c == "#" and (not buf or buf[-1].isspace()):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif c == "\n":
            end_pipeline()
            while pending and i + 1 < n:
                terminator = pending.pop(0)
                i += 1
                while i < n:
                    end = text.find("\n", i)
                    line = text[i : end if end != -1 else n]
                    i = end if end != -1 else n
                    if line.strip() == terminator:
                        break
                    i += 1
            pending.clear()
        elif c == ";":
            end_pipeline()
        elif c == "&" and nxt == "&":
            end_pipeline()
            i += 1
        elif c == "&" and (
            nxt == ">" or (buf and buf[-1] in "<>") or tool == "PowerShell"
        ):
            buf.append(c)
        elif c == "&":
            end_pipeline()
        elif c == "|" and nxt == "|":
            end_pipeline()
            i += 1
        elif c == "|" and buf and buf[-1] == ">":
            buf.append(c)
        elif c == "|":
            end_segment()
        else:
            buf.append(c)
        i += 1
    end_pipeline()
    return pipelines


def _words(segment):
    try:
        return shlex.split(segment, posix=False)
    except ValueError:
        return segment.split()


def _command(words):
    """The command word (lower case, no path, no .exe) and the words after it."""
    skipping = False
    for i, raw in enumerate(words):
        word = raw.lstrip("({")
        if skipping and (word.startswith("-") or re.fullmatch(r"\d+[smhd]?", word)):
            continue
        skipping = False
        if not word or re.fullmatch(r"[A-Za-z_]\w*=.*", word):
            continue
        if word.lower() in _WRAPPERS:
            skipping = word.lower() in {"timeout", "nice", "ionice"}
            continue
        name = re.split(r"[/\\]", word.strip("'\""))[-1].lower()
        return (name[:-4] if name.endswith(".exe") else name), words[i + 1 :]
    return "", []


def _strip_redirects(args):
    kept, skip = [], False
    for word in args:
        if skip:
            skip = False
        elif _REDIRECT_ALONE.match(word):
            skip = True
        elif not _REDIRECT_ATTACHED.match(word):
            kept.append(word)
    return kept


def _names_file(word):
    return _FILE_RE.search(word) is not None


def _outside_parentheses(args):
    """The arguments that are not inside a parenthesised sub-expression (those are being read)."""
    depth, kept = 0, []
    for word in args:
        if depth <= 0:
            kept.append(word)
        depth += word.count("(") - word.count(")")
    return kept


def _python_arguments(cmd, args):
    if cmd in _LAUNCHERS:
        for j, word in enumerate(args):
            if _PYTHON_WORD.match(word.lower()):
                return args[j + 1 :]
        return None
    return args if _PYTHON_WORD.match(cmd) else None


def _is_inline_python(segment):
    """True when this segment runs python on a script it was given inline or on stdin."""
    cmd, args = _command(_words(segment))
    py_args = _python_arguments(cmd, args)
    if py_args is None:
        return False
    positional = [a for a in py_args if not a.startswith("-")]
    return (
        any(_PYTHON_DASH_C.match(a) for a in py_args)
        or "-" in py_args
        or "<<" in segment
        or not positional
    )


def _segment_shape(segment, tool):
    """The first rewrite-or-delete shape of one command segment that names the file, or None."""
    if _REDIRECT_ONTO_FILE.search(_INPUT_REDIRECT.sub(" ", segment)):
        return "a redirect that overwrites the file (>)"
    cmd, args = _command(_words(segment))
    args = _strip_redirects(args)
    named = [a for a in args if _names_file(a)]
    if cmd in ("rm", "unlink") and named:
        return "rm on the file"
    if cmd == "mv":
        operands = [a for a in args if not a.startswith("-")]
        if len(operands) >= 2 and _names_file(operands[-1]):
            return "mv onto the file"
    if cmd == "sed" and named and any(_SED_IN_PLACE.match(a) for a in args):
        return "an in-place sed (sed -i)"
    append = _POWERSHELL_APPEND if tool == "PowerShell" else _TEE_APPEND
    if (
        cmd in ("tee", "tee-object")
        and named
        and not any(append.match(a) for a in args if a.startswith("-"))
    ):
        return "tee without -a on the file"
    if cmd == "find" and named:
        executed = [
            args[k + 1].lower() for k, a in enumerate(args[:-1]) if a == "-exec"
        ]
        if "-delete" in args or any(w in ("rm", "unlink", "mv") for w in executed):
            return "find deleting the file"
    if cmd == "git" and named and "rm" in args and "--cached" not in args:
        return "git rm on the file"
    if tool == "PowerShell":
        outside = [a for a in _outside_parentheses(args) if _names_file(a)]
        if outside and cmd in _POWERSHELL_SET:
            return "Set-Content on the file"
        if outside and cmd in _POWERSHELL_CLEAR:
            return "Clear-Content on the file"
        if outside and cmd in _POWERSHELL_REMOVE:
            return "Remove-Item on the file"
        if (
            outside
            and cmd == "out-file"
            and not any(_POWERSHELL_APPEND.match(a) for a in args if a.startswith("-"))
        ):
            return "Out-File without -Append on the file"
    return None


def _pipeline_shape(pipeline, tool):
    names_file = [_names_file(s) for s in pipeline]
    for index, segment in enumerate(pipeline):
        shape = _segment_shape(segment, tool)
        if shape:
            return shape
        cmd, args = _command(_words(segment))
        if cmd == "xargs" and any(names_file):
            nested = [a.lower() for a in args if not a.startswith("-")]
            if any(a in ("rm", "unlink") for a in nested):
                return "rm fed the file by xargs"
        if (
            tool == "PowerShell"
            and index > 0
            and cmd in _POWERSHELL_REMOVE | _POWERSHELL_CLEAR
            and any(names_file[:index])
            and _command(_words(pipeline[0]))[0] in _POWERSHELL_LISTERS
        ):
            return "Remove-Item or Clear-Content fed the file by a pipeline"
    return None


def _shell_shape(cmd, tool):
    """Name the first shape in a shell command that can rewrite or delete the file, or None."""
    continuation = _CONTINUATION_POWERSHELL if tool == "PowerShell" else _CONTINUATION
    flat = continuation.sub(" ", cmd)
    if any(len(line) > _MAX_LINE for line in flat.splitlines()):
        return f"a line over {_MAX_LINE} characters, which the guard cannot judge"
    flat = _expand_variables(flat, tool)
    if not _FILE_RE.search(flat):
        return None
    pipelines = _pipelines(flat, tool)
    if _PYTHON_WRITES.search(flat) and any(
        _is_inline_python(segment) for pipeline in pipelines for segment in pipeline
    ):
        return "an inline python script that writes the file (python -c or a script on stdin)"
    for pipeline in pipelines:
        shape = _pipeline_shape(pipeline, tool)
        if shape:
            return shape
    return None


def _gate_record_exists(project_dir):
    """A non-trivial gate record dated today. Empty or missing -> no gate."""
    today = datetime.date.today().isoformat()
    path = os.path.join(
        project_dir, ".ai", "consolidation-gates", f"{today}-plan-approved.md"
    )
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return len(fh.read().strip()) >= 200, path
    except OSError:
        return False, path


def _reason(path, removed):
    return (
        f"BLOCKED: this call would remove {removed} entr"
        + ("y" if removed == 1 else "ies")
        + " from .ai/learnings.md, and no approved consolidation plan exists for today.\n\n"
        "A drain removes the only copy of knowledge that promotions are supposed to have "
        "re-homed. learning-consolidator Phase 3 requires the plan to be presented and "
        "APPROVED first; the 2026-09-13 drain removed 263 entries without one.\n\n"
        "To proceed:\n"
        "  1. Present the Phase 3 consolidation plan to the operator and WAIT.\n"
        f"  2. On approval, record it at: {path}\n"
        "  3. Re-run this edit.\n\n"
        "Appending to learnings.md is never blocked - only removal is."
    )


def _shell_reason(path, shape):
    """The text for the shell arm, which sees a command and not the entries it would touch."""
    return (
        "BLOCKED: this shell call may rewrite or delete "
        f".ai/learnings.md ({shape}), and no approved consolidation plan exists for today.\n\n"
        "The guard reads the command text and cannot tell what the call does to the file: "
        "nothing is known to be removed.\n\n"
        "These routes are never blocked:\n"
        "  - count entries: Grep in count mode, pattern ^### \\[\n"
        "  - read entries: Read with offset and limit\n"
        "  - add an entry: Edit appending under the entry's own category header\n\n"
        "Retrying the same change through another route (another shell, an interpreter, a "
        "copy of the file, another spelling of its name) is the breach this gate exists to "
        "stop, not a way round it.\n\n"
        "If this really is a drain, learning-consolidator Phase 3 requires the plan to be "
        "presented and APPROVED first:\n"
        "  1. Present the Phase 3 consolidation plan to the operator and WAIT.\n"
        f"  2. On approval, record it at: {path}\n"
        "  3. Re-run the call.\n\n"
        "Appending to learnings.md is never blocked when it is written as an append: only a "
        "call shaped like a rewrite or a removal is."
    )


def main():
    try:
        payload = json.load(sys.stdin)
        tool = payload.get("tool_name", "")
        ti = payload.get("tool_input", {}) or {}
    except Exception:
        return  # fail open

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    removed = 0
    shape = None

    try:
        if tool in ("Edit", "MultiEdit"):
            if not _targets_learnings(ti.get("file_path")):
                return
            edits = ti.get("edits") or [ti]
            for e in edits:
                removed += max(
                    0, _count(e.get("old_string")) - _count(e.get("new_string"))
                )

        elif tool == "Write":
            if not _targets_learnings(ti.get("file_path")):
                return
            try:
                with open(ti["file_path"], encoding="utf-8", errors="replace") as fh:
                    current = _count(fh.read())
            except OSError:
                return  # new file: cannot be a removal
            removed = max(0, current - _count(ti.get("content")))

        elif tool in ("Bash", "PowerShell"):
            cmd = ti.get("command", "")
            if not isinstance(cmd, str) or "learnings.md" not in cmd.lower():
                return
            shape = _shell_shape(cmd, tool)
            if shape is None:
                return

        else:
            return
    except Exception:
        return  # fail open

    if shape is None and removed == 0:
        return

    ok, path = _gate_record_exists(project_dir)
    if ok:
        return

    reason = _shell_reason(path, shape) if shape else _reason(path, removed)
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
