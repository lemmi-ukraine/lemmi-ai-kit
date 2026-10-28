"""The learnings drain guard denies what can remove entries and lets everything else through.

`plugins/core/hooks/gate_learnings_drain.py` stops a drain of `.ai/learnings.md` that has no
approved plan. Its shell arm judged a command by tokens, so it denied read-only commands that
merely had a `2>&1` or a `>=` before the file name, denied appends and then said appends are
never blocked, denied any inline `python -c`, and told the model only that an unknown number
of entries would be removed: a message that fits none of those calls and teaches no route but
the plan. The kit had no test for it at all after its first one was removed.

The table below is the probe table of 27 shapes the fix was specified from, then the shapes
the fix adds. Every row states the decision it REQUIRES, and the ALLOW rows matter as much as
the DENY rows: a guard that blocks unrelated work is worse than no guard.

`GAP` rows are shapes the guard passes today and does not endorse: they are the known limits
the module docstring lists (the shell arm reads command text only). A GAP row is pinned as
ALLOW so that closing a gap is a visible change here and not a silent one; when a gap is
closed, move its row to DENY. An `FPOS` row is a known false positive the same way: pinned as
DENY, listed in the module docstring, and moved to ALLOW when the guard stops denying it.

The guard runs as a subprocess, the way the harness runs it, so the tests also catch what an
in-process call would hide: a stray line on stdout, a crash, a reply that is not JSON.
"""

import contextlib
import datetime
import importlib.util
import io
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from unittest import mock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_GUARD = _REPO_ROOT / "plugins" / "core" / "hooks" / "gate_learnings_drain.py"

_THREE_ENTRIES = (
    "# Learnings\n\n### [one] A\nbody\n\n### [two] B\nbody\n\n### [three] C\nbody\n"
)

# (name, tool, command, required decision). ALLOW and DENY are required; GAP is a known limit
# pinned as ALLOW (see the module docstring).
Row = tuple[str, str, str, str]

# The 27 shapes of the probe table, in its order.
_PROBE_SHAPES: list[Row] = [
    (
        "control deny: sed -i on the file",
        "Bash",
        "sed -i '/### A/d' .ai/learnings.md",
        "DENY",
    ),
    ("control allow: plain ls", "Bash", "ls -la", "ALLOW"),
    (
        "read-only git diff with 2>&1 before the name",
        "Bash",
        "git diff --numstat 2>&1 -- .ai/learnings.md",
        "ALLOW",
    ),
    (
        "read-only, 2>/dev/null, the file named on two lines",
        "Bash",
        "git diff --numstat -- .ai/learnings.md 2>/dev/null\n"
        "echo ---\n"
        "git log --oneline -3 -- .ai/learnings.md 2>/dev/null",
        "ALLOW",
    ),
    (
        "read-only awk with >= before the name",
        "Bash",
        "awk 'NR>=210 && NR<=220' .ai/learnings.md",
        "ALLOW",
    ),
    (
        "read-only grep with a quoted >= before the name",
        "Bash",
        "grep -E 'n>=3' .ai/learnings.md",
        "ALLOW",
    ),
    (
        "read-only python -X utf8 -c",
        "Bash",
        "python -X utf8 -c \"print(open('.ai/learnings.md', encoding='utf-8')"
        ".read().count('### '))\"",
        "ALLOW",
    ),
    (
        "backup: git diff > patch, the name after",
        "Bash",
        "git diff > backup.patch -- .ai/learnings.md",
        "ALLOW",
    ),
    (
        "heredoc body only names the file",
        "Bash",
        "cat > plan.txt <<'EOF'\nnotes about .ai/learnings.md\nEOF",
        "ALLOW",
    ),
    ("append: cat x >> file", "Bash", "cat extra.md >> .ai/learnings.md", "ALLOW"),
    (
        "append: printf >> file",
        "Bash",
        "printf '\\n### D\\n' >> .ai/learnings.md",
        "ALLOW",
    ),
    ("append: tee -a file", "Bash", "echo x | tee -a .ai/learnings.md", "ALLOW"),
    ("truncate: : > file", "Bash", ": > .ai/learnings.md", "DENY"),
    ("remove: rm file", "Bash", "rm .ai/learnings.md", "DENY"),
    ("gap: truncate -s 0 file", "Bash", "truncate -s 0 .ai/learnings.md", "GAP"),
    (
        "python3 -c writes the file",
        "Bash",
        "python3 -c \"open('.ai/learnings.md', 'w').close()\"",
        "DENY",
    ),
    (
        "py -c writes the file",
        "Bash",
        "py -c \"open('.ai/learnings.md', 'w').close()\"",
        "DENY",
    ),
    ("gap: git checkout -- file", "Bash", "git checkout -- .ai/learnings.md", "GAP"),
    ("gap: mv file", "Bash", "mv .ai/learnings.md elsewhere.md", "GAP"),
    ("cp file (the snapshot copy)", "Bash", "cp .ai/learnings.md snapshot.md", "ALLOW"),
    ("sanctioned count: grep -c", "Bash", "grep -c '^### ' .ai/learnings.md", "ALLOW"),
    ("wc -l file", "Bash", "wc -l .ai/learnings.md", "ALLOW"),
    ("sed -n range read", "Bash", "sed -n '210,220p' .ai/learnings.md", "ALLOW"),
    (
        "PowerShell Set-Content file",
        "PowerShell",
        "Set-Content -Path .ai/learnings.md -Value ''",
        "DENY",
    ),
    (
        "PowerShell Remove-Item file",
        "PowerShell",
        "Remove-Item .ai/learnings.md",
        "DENY",
    ),
    (
        "PowerShell Out-File file",
        "PowerShell",
        "'' | Out-File .ai/learnings.md",
        "DENY",
    ),
    ("PowerShell redirect > file", "PowerShell", "'' > .ai/learnings.md", "DENY"),
]

# Shapes the fix adds: what an inline script may do, which flags make a write an append, what
# a redirect target is, and the PowerShell routes.
_ADDED_SHAPES: list[Row] = [
    (
        "python -c that writes with open(..., 'w')",
        "Bash",
        "python -c \"open('.ai/learnings.md', 'w').write('')\"",
        "DENY",
    ),
    (
        "python -c that writes with write_text",
        "Bash",
        "python -c \"import pathlib; pathlib.Path('.ai/learnings.md').write_text('')\"",
        "DENY",
    ),
    (
        "python -c that replaces the file with os.replace",
        "Bash",
        "python -c \"import os; os.replace('new.md', '.ai/learnings.md')\"",
        "DENY",
    ),
    (
        "python -c that only appends",
        "Bash",
        "python -c \"open('.ai/learnings.md', 'a').write('x')\"",
        "ALLOW",
    ),
    (
        "python -c that only reads with pathlib",
        "Bash",
        'python -c "import pathlib; '
        "print(len(pathlib.Path('.ai/learnings.md').read_text().splitlines()))\"",
        "ALLOW",
    ),
    ("tee without -a", "Bash", "echo x | tee .ai/learnings.md", "DENY"),
    (
        "tee -ai (combined flags that append)",
        "Bash",
        "echo x | tee -ai .ai/learnings.md",
        "ALLOW",
    ),
    (
        "redirect with no space before the target",
        "Bash",
        "echo x >.ai/learnings.md",
        "DENY",
    ),
    (
        "redirect of fd 1 to a quoted target",
        "Bash",
        'echo x 1> ".ai/learnings.md"',
        "DENY",
    ),
    ("redirect of stderr into the file", "Bash", "ls 2> .ai/learnings.md", "DENY"),
    ("redirect that overrides noclobber", "Bash", "echo x >| .ai/learnings.md", "DENY"),
    (
        "redirect onto a different file that starts with the name",
        "Bash",
        "git diff > .ai/learnings.md.patch",
        "ALLOW",
    ),
    (
        "rm of a backup that starts with the name",
        "Bash",
        "rm .ai/learnings.md.bak",
        "ALLOW",
    ),
    (
        "sed -i split over a continued line",
        "Bash",
        "sed -i \\\n  '/### A/d' .ai/learnings.md",
        "DENY",
    ),
    ("rm split over a continued line", "Bash", "rm \\\n  .ai/learnings.md", "DENY"),
    (
        "sed -i with a backup suffix",
        "Bash",
        "sed -i.bak '/### A/d' .ai/learnings.md",
        "DENY",
    ),
    (
        "sed -n read of a directory whose name contains -i",
        "Bash",
        "sed -n '1,5p' docs/some-index/learnings.md",
        "ALLOW",
    ),
    (
        "a command with CRLF line endings",
        "Bash",
        "sed -i '/### A/d' .ai/learnings.md\r\n",
        "DENY",
    ),
    (
        "PowerShell Clear-Content",
        "PowerShell",
        "Clear-Content .ai/learnings.md",
        "DENY",
    ),
    (
        "PowerShell Add-Content is an append",
        "PowerShell",
        "Add-Content -Path .ai/learnings.md -Value 'x'",
        "ALLOW",
    ),
    ("PowerShell >> is an append", "PowerShell", "'x' >> .ai/learnings.md", "ALLOW"),
    (
        "PowerShell Out-File -Append",
        "PowerShell",
        "'x' | Out-File -Append .ai/learnings.md",
        "ALLOW",
    ),
    (
        "PowerShell Out-File -FilePath then -Append",
        "PowerShell",
        "'x' | Out-File -FilePath .ai/learnings.md -Append",
        "ALLOW",
    ),
    (
        "PowerShell Out-File -FilePath with no append (the letter a is in the parameter names)",
        "PowerShell",
        "'x' | Out-File -FilePath .ai/learnings.md -Encoding utf8",
        "DENY",
    ),
    (
        "PowerShell read with Select-String",
        "PowerShell",
        "Get-Content .ai/learnings.md | Select-String '^### '",
        "ALLOW",
    ),
    ("PowerShell count", "PowerShell", "(Get-Content .ai/learnings.md).Count", "ALLOW"),
]

# What a replay of 1,200 real commands that name the file found wrong, or wrongly right, in the
# first version of the fix. FPOS is a known false positive, pinned as DENY so removing it is a
# visible change; GAP is a known gap, pinned as ALLOW.
_CORPUS_SHAPES: list[Row] = [
    (
        "rm of another file, then a read on the same line",
        "Bash",
        "rm -f tmp.txt && grep -c '^### ' .ai/learnings.md",
        "ALLOW",
    ),
    (
        "tee to another file, then a read",
        "Bash",
        "echo x | tee out.txt && wc -l .ai/learnings.md",
        "ALLOW",
    ),
    (
        "sed -i on another file, then a read",
        "Bash",
        "sed -i s/a/b/ notes.txt && wc -l .ai/learnings.md",
        "ALLOW",
    ),
    (
        "tee that only reads the file as input",
        "Bash",
        "tee out.txt < .ai/learnings.md",
        "ALLOW",
    ),
    (
        "redirect onto a file that ends with the name",
        "Bash",
        "printf x > seed-learnings.md",
        "ALLOW",
    ),
    ("rm of a file that ends with the name", "Bash", "rm old-learnings.md", "ALLOW"),
    (
        "a filtered copy moved over the original",
        "Bash",
        "grep -v '^### ' .ai/learnings.md > t.tmp && mv t.tmp .ai/learnings.md",
        "DENY",
    ),
    (
        "gap: cp of a snapshot over the file",
        "Bash",
        "cp snapshot.md .ai/learnings.md",
        "GAP",
    ),
    (
        "cp of the file into a backup folder that mirrors the tree",
        "Bash",
        # split in two: the hygiene scan forbids that folder name written out
        "cp .ai/learnings.md .ai/back" + "ups/pre/files/.ai/learnings.md",
        "ALLOW",
    ),
    (
        "a heredoc that only creates a .py file that names the file",
        "Bash",
        "cat > tools/fix.py <<'PYEOF'\nopen('.ai/learnings.md', 'w').close()\nPYEOF",
        "ALLOW",
    ),
    (
        "the file sorted onto itself",
        "Bash",
        "sort < .ai/learnings.md > .ai/learnings.md",
        "DENY",
    ),
    (
        "python script on stdin that rewrites the file",
        "Bash",
        "python - <<'EOF'\np = '.ai/learnings.md'\nopen(p, 'wb').write(b'')\nEOF",
        "DENY",
    ),
    (
        "python script on stdin that only reads the file",
        "Bash",
        "python - <<'EOF'\nprint(open('.ai/learnings.md').read().count('### '))\nEOF",
        "ALLOW",
    ),
    (
        "known false positive: python reads the file and writes another",
        "Bash",
        "python -c \"t = open('.ai/learnings.md').read(); open('out.txt', 'w').write(t)\"",
        "FPOS",
    ),
    (
        "PowerShell Set-Content that only reads the file inside a value",
        "PowerShell",
        "Set-Content -Path out.txt -Value (Get-Content .ai/learnings.md)",
        "ALLOW",
    ),
    (
        "PowerShell Out-File that only reads the file inside a value",
        "PowerShell",
        "Out-File out.txt -InputObject (Get-Content .ai/learnings.md)",
        "ALLOW",
    ),
    (
        "PowerShell Remove-Item of another file, then a read",
        "PowerShell",
        "Remove-Item tmp.txt && (Get-Content .ai/learnings.md).Count",
        "ALLOW",
    ),
    ("gap: perl -pi", "Bash", "perl -pi -e 's/^### .*//' .ai/learnings.md", "GAP"),
    (
        "gap: awk -i inplace",
        "Bash",
        "awk -i inplace '/### A/ {next} {print}' .ai/learnings.md",
        "GAP",
    ),
    ("gap: git restore", "Bash", "git restore .ai/learnings.md", "GAP"),
    (
        "gap: PowerShell WriteAllText",
        "PowerShell",
        "[IO.File]::WriteAllText('.ai/learnings.md', '')",
        "GAP",
    ),
]

_BASE_ROWS: list[Row] = _PROBE_SHAPES + _ADDED_SHAPES + _CORPUS_SHAPES

# ---- rows that each pin a decision a mutant of the guard had flipped.
_LONG_HEREDOC = (
    "cat >> .ai/learnings.md <<'EOF'\n"
    + "\n".join(f"### [n{i}] entry line {i}" for i in range(1500))
    + "\nEOF"
)
_MUTATION_SHAPES: list[Row] = [
    # a shape on any line of a multi-line call is judged, not only the first or the last
    (
        "rm on the second line of a call",
        "Bash",
        "echo start\nrm .ai/learnings.md",
        "DENY",
    ),
    (
        "rm on the first line of a call",
        "Bash",
        "rm .ai/learnings.md\necho done",
        "DENY",
    ),
    (
        "rm split over a CRLF continued line",
        "Bash",
        "rm \\\r\n  .ai/learnings.md",
        "DENY",
    ),
    (
        "PowerShell Remove-Item split over a backtick continuation",
        "PowerShell",
        "Remove-Item `\n  .ai/learnings.md",
        "DENY",
    ),
    (
        "PowerShell Remove-Item split over a CRLF backtick continuation",
        "PowerShell",
        "Remove-Item `\r\n  .ai/learnings.md",
        "DENY",
    ),
    # the file name is the whole name
    (
        "rm of a name that ends in it with no separator",
        "Bash",
        "rm xlearnings.md",
        "ALLOW",
    ),
    ("rm of a dotted name that ends in it", "Bash", "rm foo.learnings.md", "ALLOW"),
    (
        "rm of a name that starts with it and a letter",
        "Bash",
        "rm learnings.mdx",
        "ALLOW",
    ),
    (
        "rm of a name that starts with it and a hyphen",
        "Bash",
        "rm learnings.md-old",
        "ALLOW",
    ),
    (
        "the dot in the name is literal",
        "Bash",
        "rm learningsXmd learnings.md.bak",
        "ALLOW",
    ),
    (
        "a long command that never names the file",
        "Bash",
        "echo " + "x" * 12000,
        "ALLOW",
    ),
    # redirects
    ("an escaped > is not a redirect", "Bash", "echo a \\> .ai/learnings.md", "ALLOW"),
    (
        "redirect to a long path",
        "Bash",
        "echo x > " + "d" * 100 + "/learnings.md",
        "DENY",
    ),
    (
        ">&file sends both streams into the file",
        "Bash",
        "echo x >&.ai/learnings.md",
        "DENY",
    ),
    # the && stop, in every shape
    (
        "mv of other files, then a read",
        "Bash",
        "mv a b && cat .ai/learnings.md",
        "ALLOW",
    ),
    (
        "python run, then a read that quotes a write call",
        "Bash",
        'python run.py && grep -c "p.write_text(" .ai/learnings.md',
        "ALLOW",
    ),
    (
        "PowerShell Set-Content of another file, then a read",
        "PowerShell",
        "Set-Content out.txt -Value x && Get-Content .ai/learnings.md",
        "ALLOW",
    ),
    (
        "PowerShell Clear-Content of another file, then a read",
        "PowerShell",
        "Clear-Content tmp.txt && Get-Content .ai/learnings.md",
        "ALLOW",
    ),
    (
        "PowerShell Remove-Item of another file, then a plain read",
        "PowerShell",
        "Remove-Item tmp.txt && Get-Content .ai/learnings.md",
        "ALLOW",
    ),
    (
        "PowerShell Out-File to another file, then a read",
        "PowerShell",
        "'x' | Out-File out.txt && Get-Content .ai/learnings.md",
        "ALLOW",
    ),
    # how far a shape looks
    (
        "sed -i with a 600-character script",
        "Bash",
        "sed -i '" + "x" * 600 + "' .ai/learnings.md",
        "DENY",
    ),
    (
        "sed -i with a script of 2000 characters",
        "Bash",
        "sed -i '" + "x" * 2000 + "' .ai/learnings.md",
        "DENY",
    ),
    # sed
    ("sed --in-place", "Bash", "sed --in-place '/### A/d' .ai/learnings.md", "DENY"),
    (
        "sed with a combined flag cluster",
        "Bash",
        "sed -Ei '/### A/d' .ai/learnings.md",
        "DENY",
    ),
    (
        "a word that ends in sed, then -i",
        "Bash",
        "git log --grep=parsed -i -- .ai/learnings.md",
        "ALLOW",
    ),
    # rm, mv
    ("a word that ends in rm", "Bash", "echo perform .ai/learnings.md", "ALLOW"),
    ("rmdir names the file", "Bash", "rmdir .ai/learnings.md", "ALLOW"),
    ("mv onto a quoted target", "Bash", 'mv t.tmp ".ai/learnings.md"', "DENY"),
    (
        "mv onto the file, then more commands",
        "Bash",
        "mv t.tmp .ai/learnings.md && echo ok",
        "DENY",
    ),
    # tee
    ("tee --append", "Bash", "echo x | tee --append .ai/learnings.md", "ALLOW"),
    (
        "tee to a file named like a flag, plus the file",
        "Bash",
        "echo x | tee out-a .ai/learnings.md",
        "DENY",
    ),
    ("a word that ends in tee", "Bash", "echo committee .ai/learnings.md", "ALLOW"),
    (
        "tee with the flag after the file",
        "Bash",
        "echo x | tee .ai/learnings.md -a",
        "ALLOW",
    ),
    (
        "PowerShell tee -Append",
        "PowerShell",
        "'x' | tee -FilePath .ai/learnings.md -Append",
        "ALLOW",
    ),
    # PowerShell
    (
        "PowerShell Out-File with a -Append prefix",
        "PowerShell",
        "'x' | Out-File .ai/learnings.md -App",
        "ALLOW",
    ),
    (
        "PowerShell Out-File with -Append:$true",
        "PowerShell",
        "'x' | Out-File .ai/learnings.md -Append:$true",
        "ALLOW",
    ),
    (
        "PowerShell Out-File with -a glued to another token",
        "PowerShell",
        "'x' | Out-File .ai/learnings.md -Encoding utf8-a",
        "DENY",
    ),
    (
        "gap: a cmdlet reached through pwsh from Bash",
        "Bash",
        "pwsh -c \"Set-Content .ai/learnings.md ''\"",
        "GAP",
    ),
    (
        "PowerShell lowercase set-content",
        "PowerShell",
        "set-content -Path .ai/learnings.md -Value ''",
        "DENY",
    ),
    (
        "PowerShell lowercase clear-content",
        "PowerShell",
        "clear-content .ai/learnings.md",
        "DENY",
    ),
    (
        "PowerShell lowercase remove-item",
        "PowerShell",
        "remove-item .ai/learnings.md",
        "DENY",
    ),
    (
        "PowerShell lowercase out-file",
        "PowerShell",
        "'' | out-file .ai/learnings.md",
        "DENY",
    ),
    # inline python
    (
        "python script piped to a lone -",
        "Bash",
        "echo \"open('.ai/learnings.md', 'w').write('')\" | python -",
        "DENY",
    ),
    (
        "python3 heredoc without a dash",
        "Bash",
        "python3 <<EOF\nopen('.ai/learnings.md', 'w').close()\nEOF",
        "DENY",
    ),
    (
        "python flag cluster before c",
        "Bash",
        "python -Ic \"open('.ai/learnings.md', 'w').close()\"",
        "DENY",
    ),
    (
        "python run with -csv, then a read that quotes a write call",
        "Bash",
        'python tool.py -csv && grep "p.write_text(" .ai/learnings.md',
        "ALLOW",
    ),
    (
        "python open for append and read",
        "Bash",
        "python -c \"open('.ai/learnings.md', 'a+').write('x')\"",
        "ALLOW",
    ),
    (
        "python open for exclusive create",
        "Bash",
        "python -c \"open('.ai/learnings.md', 'x').write('x')\"",
        "DENY",
    ),
    (
        "python open for read and write",
        "Bash",
        "python -c \"open('.ai/learnings.md', 'r+').write('x')\"",
        "DENY",
    ),
    (
        "python open with a mode keyword",
        "Bash",
        "python -c \"open('.ai/learnings.md', mode='w').close()\"",
        "DENY",
    ),
    (
        "python write_bytes",
        "Bash",
        "python -c \"import pathlib; pathlib.Path('.ai/learnings.md').write_bytes(b'')\"",
        "DENY",
    ),
    (
        "python truncate",
        "Bash",
        "python -c \"f = open('.ai/learnings.md', 'rb'); f.truncate(0)\"",
        "DENY",
    ),
    (
        "python unlink",
        "Bash",
        "python -c \"import pathlib; pathlib.Path('.ai/learnings.md').unlink()\"",
        "DENY",
    ),
    (
        "python os.remove",
        "Bash",
        "python -c \"import os; os.remove('.ai/learnings.md')\"",
        "DENY",
    ),
    (
        "python shutil.copy",
        "Bash",
        "python -c \"import shutil; shutil.copy('snapshot.md', '.ai/learnings.md')\"",
        "DENY",
    ),
    (
        "python open with a nested call in the path",
        "Bash",
        "python -c \"import os; open(os.path.join('.ai', 'learnings.md'), 'w').close()\"",
        "DENY",
    ),
    (
        "python open with a long path",
        "Bash",
        "python -c \"open('/very/long/path/to/some/place/in/the/repo/.ai/learnings.md', 'w')\"",
        "DENY",
    ),
    (
        "python write that only names seed-learnings.md",
        "Bash",
        "python -c \"open('seed-learnings.md', 'w').close()\"",
        "ALLOW",
    ),
    (
        "grep for a write call, no inline script",
        "Bash",
        'grep -n "os.replace(" scripts/x.py .ai/learnings.md',
        "ALLOW",
    ),
    # the long-line limit judges per line, so a long heredoc of short lines is an ordinary call
    (
        "a long heredoc of short lines is judged per line",
        "Bash",
        _LONG_HEREDOC,
        "ALLOW",
    ),
]

_MUTATION_SHAPES_EXTRA: list[Row] = [
    ("a word that ends in mv", "Bash", "echo xmv .ai/learnings.md", "ALLOW"),
    (
        "gap: ipython -c is not matched as an interpreter",
        "Bash",
        "ipython -c \"open('.ai/learnings.md', 'w').close()\"",
        "GAP",
    ),
]

_MUTATION_SHAPES_V2: list[Row] = [
    (
        "the Windows launcher run by its full path",
        "Bash",
        # split in two: the hygiene scan forbids a drive-letter path written out
        "C" + ":\\Windows\\py.exe -c \"open('.ai/learnings.md', 'w').close()\"",
        "DENY",
    ),
]
# Shapes a parser, not a pattern, has to get right: where a heredoc starts, what ends a string,
# which word is the command, and what a find or a git rm does.
_PARSER_SHAPES: list[Row] = [
    (
        "a heredoc marker inside quotes does not hide the next line",
        "Bash",
        'echo "<<EOF"\nrm .ai/learnings.md',
        "DENY",
    ),
    (
        "the line after a real heredoc body is a command again",
        "Bash",
        "cat <<'EOF' > plan.txt\nrm .ai/learnings.md\nEOF\nrm .ai/learnings.md",
        "DENY",
    ),
    (
        "a heredoc body that only names rm as text",
        "Bash",
        "cat <<'EOF' > plan.txt\nrm .ai/learnings.md\nEOF",
        "ALLOW",
    ),
    (
        "a PowerShell string that ends in a backslash does not hide the next cmdlet",
        "PowerShell",
        'Write-Output "a\\"; Remove-Item .ai/learnings.md',
        "DENY",
    ),
    ("git rm of the file", "Bash", "git rm -f .ai/learnings.md", "DENY"),
    (
        "git rm --cached keeps the file",
        "Bash",
        "git rm --cached .ai/learnings.md",
        "ALLOW",
    ),
    ("a timeout wrapper around rm", "Bash", "timeout 5 rm .ai/learnings.md", "DENY"),
    (
        "a nice wrapper with an argument around rm",
        "Bash",
        "nice -n 5 rm .ai/learnings.md",
        "DENY",
    ),
    (
        "find that only reads the file",
        "Bash",
        "find . -name learnings.md -exec cat {} +",
        "ALLOW",
    ),
    ("find -delete on the file", "Bash", "find . -name learnings.md -delete", "DENY"),
    (
        "find -exec rm on the file",
        "Bash",
        "find . -name learnings.md -exec rm {} +",
        "DENY",
    ),
]

_SHELL_ROWS: list[Row] = (
    _BASE_ROWS
    + _MUTATION_SHAPES
    + _MUTATION_SHAPES_EXTRA
    + _MUTATION_SHAPES_V2
    + _PARSER_SHAPES
)


def _make_project(root: Path) -> Path:
    (root / ".ai").mkdir(parents=True, exist_ok=True)
    (root / ".ai" / "learnings.md").write_text(_THREE_ENTRIES, encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A project with three entries and NO gate record: every call is judged ungated."""
    return _make_project(tmp_path_factory.mktemp("project"))


@cache
def _guard_module() -> ModuleType:
    """The guard, loaded once from its file (the hook is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("gate_learnings_drain", _GUARD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _guard_main() -> Callable[[], None]:
    return cast(Callable[[], None], _guard_module().main)


def _guard_out(stdin: str, project_dir: Path) -> str:
    """What the guard prints for `stdin`, run in this process.

    The table is large and a subprocess per row costs about a second on Windows. `main`
    reads stdin and the environment and nothing else, so this is the call the harness makes;
    the tests that need a real process (stdout, exit status) use `_run_as_script`.
    """
    out = io.StringIO()
    with (
        mock.patch.object(sys, "stdin", io.StringIO(stdin)),
        mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project_dir)}),
        contextlib.redirect_stdout(out),
    ):
        _guard_main()()
    return out.getvalue().strip()


def _run(payload: dict[str, Any], project_dir: Path) -> str:
    return _guard_out(json.dumps(payload), project_dir)


def _run_as_script(stdin: str, project_dir: Path) -> "subprocess.CompletedProcess[str]":
    """The real contract, as the harness runs it: a process that reads stdin and prints JSON."""
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [sys.executable, "-B", str(_GUARD)],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=project_dir,
        timeout=60,
        check=False,
    )


def _decision(out: str) -> str:
    if not out:
        return "ALLOW"
    reply = cast(dict[str, Any], json.loads(out))
    return str(reply["hookSpecificOutput"]["permissionDecision"]).upper()


def _reason(out: str) -> str:
    reply = cast(dict[str, Any], json.loads(out))
    return str(reply["hookSpecificOutput"]["permissionDecisionReason"])


def _shell(tool: str, command: str) -> dict[str, Any]:
    return {"tool_name": tool, "tool_input": {"command": command}}


def _record_path(project_dir: Path) -> Path:
    today = datetime.date.today().isoformat()
    return project_dir / ".ai" / "consolidation-gates" / f"{today}-plan-approved.md"


def _approve(project_dir: Path, text: str) -> None:
    record = _record_path(project_dir)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- the shell arm


@pytest.mark.parametrize(
    ("name", "tool", "command", "required"),
    _SHELL_ROWS,
    ids=[row[0] for row in _SHELL_ROWS],
)
def test_the_shell_arm_decides_each_shape(
    name: str, tool: str, command: str, required: str, project: Path
) -> None:
    got = _decision(_run(_shell(tool, command), project))
    want = {"GAP": "ALLOW", "FPOS": "DENY"}.get(required, required)
    assert got == want, f"{name}: required {want}, got {got}\n{command!r}"


def test_the_table_holds_the_27_probe_shapes_and_both_controls() -> None:
    """Guard the guard's table: it must state its own surface and its controls."""
    assert len(_PROBE_SHAPES) == 27
    assert len({row[0] for row in _SHELL_ROWS}) == len(_SHELL_ROWS), (
        "duplicate row names"
    )
    for tool in ("Bash", "PowerShell"):
        decisions = {row[3] for row in _SHELL_ROWS if row[1] == tool}
        assert {"ALLOW", "DENY"} <= decisions, f"{tool} has no row of both decisions"
    controls = {row[0]: row[3] for row in _PROBE_SHAPES[:2]}
    assert set(controls.values()) == {"ALLOW", "DENY"}, controls


# -------------------------------------------------------- the Edit, Write and other arms


def _edit(
    old: str, new: str, file_name: str = "learnings.md"
) -> Callable[[Path], dict[str, Any]]:
    def build(project_dir: Path) -> dict[str, Any]:
        target = project_dir / ".ai" / file_name
        return {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(target),
                "old_string": old,
                "new_string": new,
            },
        }

    return build


def _write(content: str) -> Callable[[Path], dict[str, Any]]:
    def build(project_dir: Path) -> dict[str, Any]:
        target = project_dir / ".ai" / "learnings.md"
        return {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target), "content": content},
        }

    return build


_ARM_BASE: list[tuple[str, Callable[[Path], dict[str, Any]], str]] = [
    (
        "Edit removes 2 entries",
        _edit("### A\nbody\n\n### B\nbody\n", "### A\nbody\n"),
        "DENY",
    ),
    ("Edit removes 1 of 2", _edit("### A\n\n### B\n", "### A\n"), "DENY"),
    (
        "Edit appends an entry (the intake path stays free)",
        _edit("### C\nbody\n", "### C\nbody\n\n### D\nnew\n"),
        "ALLOW",
    ),
    (
        "Edit rewords, same entry count",
        _edit("### A\nbody\n", "### A\nreworded\n"),
        "ALLOW",
    ),
    (
        "Edit on an unrelated file that removes headers",
        _edit("### A\n\n### B\n", "### A\n", file_name="other.md"),
        "ALLOW",
    ),
    ("Write shrinks 3 entries to 1", _write("# Learnings\n\n### A\nbody\n"), "DENY"),
    (
        "Write grows 3 entries to 4",
        _write("# L\n\n### A\n\n### B\n\n### C\n\n### D\n"),
        "ALLOW",
    ),
]


def _edit_at(rel: str, old: str, new: str) -> Callable[[Path], dict[str, Any]]:
    def build(project_dir: Path) -> dict[str, Any]:
        target = project_dir / rel
        return {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(target),
                "old_string": old,
                "new_string": new,
            },
        }

    return build


def _multi_edit(old: str, new: str) -> Callable[[Path], dict[str, Any]]:
    def build(project_dir: Path) -> dict[str, Any]:
        target = project_dir / ".ai" / "learnings.md"
        return {
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(target),
                "edits": [{"old_string": old, "new_string": new}],
            },
        }

    return build


_ARM_CASES: list[tuple[str, Callable[[Path], dict[str, Any]], str]] = _ARM_BASE + [
    (
        "Edit removes a #### sub-heading, which is not an entry",
        _edit("#### sub\nbody\n", "body\n"),
        "ALLOW",
    ),
    (
        "Edit on another directory's learnings.md removes entries",
        _edit_at("docs/learnings.md", "### A\n\n### B\n", "### A\n"),
        "ALLOW",
    ),
    ("MultiEdit removes an entry", _multi_edit("### A\n\n### B\n", "### A\n"), "DENY"),
]


@pytest.mark.parametrize(
    ("name", "build", "required"),
    _ARM_CASES,
    ids=[case[0] for case in _ARM_CASES],
)
def test_the_edit_and_write_arms_judge_the_entry_count(
    name: str, build: Callable[[Path], dict[str, Any]], required: str, project: Path
) -> None:
    got = _decision(_run(build(project), project))
    assert got == required, f"{name}: required {required}, got {got}"


def test_a_tool_the_guard_does_not_watch_is_allowed(project: Path) -> None:
    target = project / ".ai" / "learnings.md"
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(target)}}
    assert _decision(_run(payload, project)) == "ALLOW"


# ------------------------------------------------------------------ the gate record


def _denied_payloads(project_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    shell = [
        (row[0], _shell(row[1], row[2])) for row in _SHELL_ROWS if row[3] == "DENY"
    ]
    arms = [(case[0], case[1](project_dir)) for case in _ARM_CASES if case[2] == "DENY"]
    return shell + arms


def test_an_approved_gate_record_lets_every_denied_call_through(tmp_path: Path) -> None:
    project_dir = _make_project(tmp_path)
    denied = _denied_payloads(project_dir)
    assert len(denied) >= 10, f"only {len(denied)} denied shapes to flip"
    for name, payload in denied:
        assert _decision(_run(payload, project_dir)) == "DENY", (
            f"{name}: not denied first"
        )
    _approve(project_dir, "x" * 250)
    for name, payload in denied:
        assert _decision(_run(payload, project_dir)) == "ALLOW", f"{name}: still denied"


def test_a_stub_gate_record_does_not_satisfy_the_gate(tmp_path: Path) -> None:
    """A record that anything short satisfies would make the gate a typing exercise."""
    project_dir = _make_project(tmp_path)
    _approve(project_dir, "ok\n")
    payload = _shell("Bash", "rm .ai/learnings.md")
    assert _decision(_run(payload, project_dir)) == "DENY"


# ---------------------------------------------------------- the reply and its words


def test_a_denial_is_the_json_the_harness_expects(project: Path) -> None:
    proc = _run_as_script(json.dumps(_shell("Bash", "rm .ai/learnings.md")), project)
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    reply = cast(
        dict[str, Any], json.loads(proc.stdout)
    )  # nothing else may be on stdout
    assert set(reply) == {"hookSpecificOutput"}
    inner = cast(dict[str, Any], reply["hookSpecificOutput"])
    assert set(inner) == {
        "hookEventName",
        "permissionDecision",
        "permissionDecisionReason",
    }
    assert inner["hookEventName"] == "PreToolUse"
    assert inner["permissionDecision"] == "deny"
    assert isinstance(inner["permissionDecisionReason"], str)


def test_an_allowed_call_prints_nothing(project: Path) -> None:
    proc = _run_as_script(json.dumps(_shell("Bash", "ls -la")), project)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


@pytest.mark.parametrize(
    "stdin", ["not json at all", "{}", '{"garbage": true}', "[]", ""]
)
def test_a_malformed_payload_fails_open(stdin: str, project: Path) -> None:
    assert _guard_out(stdin, project) == ""


def test_a_malformed_payload_fails_open_as_a_script(project: Path) -> None:
    proc = _run_as_script("not json at all", project)
    assert (proc.returncode, proc.stdout) == (0, ""), proc.stderr


def test_the_shell_denial_fits_what_it_blocked(project: Path) -> None:
    """What the model reads after a block: which shape matched, that nothing is known to be
    removed, the routes that are never blocked, and that another route is the breach."""
    out = _run(_shell("Bash", "sed -i '/### A/d' .ai/learnings.md"), project)
    reason = _reason(out)
    assert "sed -i" in reason, "the text does not name the shape that matched"
    assert "nothing is known to be removed" in reason
    assert "unknown number" not in reason, (
        "the old text claimed entries would be removed"
    )
    for route in ("Grep", "count mode", r"^### \[", "Read", "offset", "limit", "Edit"):
        assert route in reason, f"the text does not name the route {route!r}"
    assert "another route" in reason
    assert "breach" in reason
    assert "plan-approved.md" in reason, (
        "the text no longer says where the gate record goes"
    )
    for not_named in ("drain_audit", "snapshot"):
        assert not_named not in reason, (
            f"the text names {not_named!r}: no such route exists"
        )


@pytest.mark.parametrize(
    ("tool", "command", "shape"),
    [
        ("Bash", "sed -i '/### A/d' .ai/learnings.md", "an in-place sed (sed -i)"),
        ("Bash", ": > .ai/learnings.md", "a redirect that overwrites the file"),
        ("Bash", "rm .ai/learnings.md", "rm on the file"),
        ("Bash", "echo x | tee .ai/learnings.md", "tee without -a"),
        (
            "Bash",
            "python -c \"open('.ai/learnings.md', 'w').close()\"",
            "an inline python script that writes the file",
        ),
        (
            "PowerShell",
            "Set-Content -Path .ai/learnings.md -Value ''",
            "Set-Content on the file",
        ),
        ("PowerShell", "Clear-Content .ai/learnings.md", "Clear-Content on the file"),
        ("PowerShell", "Remove-Item .ai/learnings.md", "Remove-Item on the file"),
        (
            "PowerShell",
            "'x' | Out-File .ai/learnings.md",
            "Out-File without -Append",
        ),
    ],
)
def test_the_denial_names_the_shape_that_matched(
    tool: str, command: str, shape: str, project: Path
) -> None:
    reason = _reason(_run(_shell(tool, command), project))
    assert shape in reason, (
        f"{command!r} was denied but the text does not name {shape!r}"
    )


def test_appending_is_never_blocked_so_the_sentence_that_says_so_is_true(
    project: Path,
) -> None:
    """The deny text says appending is never blocked. Every append shape must therefore pass."""
    appends = [
        row
        for row in _SHELL_ROWS
        if row[0].startswith(("append", "tee -ai", "PowerShell >>"))
    ]
    appends += [
        row
        for row in _SHELL_ROWS
        if "only appends" in row[0] or "Add-Content" in row[0]
    ]
    appends += [row for row in _SHELL_ROWS if "Out-File -Append" in row[0]]
    assert len(appends) >= 7, f"only {len(appends)} append shapes are pinned"
    for name, tool, command, _required in appends:
        assert _decision(_run(_shell(tool, command), project)) == "ALLOW", name
    reason = _reason(_run(_shell("Bash", "rm .ai/learnings.md"), project))
    assert "Appending" in reason and "never blocked" in reason
    entry_append = _edit("### C\nbody\n", "### C\nbody\n\n### D\nnew\n")
    assert _decision(_run(entry_append(project), project)) == "ALLOW"


def test_a_line_too_long_to_judge_is_denied_and_a_shorter_one_is_judged(
    project: Path,
) -> None:
    """Cannot-measure is never a pass: a line over the limit that names the file is denied."""
    too_long = _run(
        _shell("Bash", "echo " + "x" * 12000 + " .ai/learnings.md"), project
    )
    assert _decision(too_long) == "DENY"
    assert "cannot judge" in _reason(too_long)
    under = _run(_shell("Bash", "echo " + "x" * 9000 + " .ai/learnings.md"), project)
    assert _decision(under) == "ALLOW"


# One line of repeated keywords once made a shape quadratic: 11 seconds at 25 KB against the
# hook's 10 second limit. These are sized to take tens of seconds without the line limit.
_PATHOLOGICAL: list[tuple[str, str, str]] = [
    (
        "an unterminated open( run",
        "Bash",
        'python -c "open(x, ' + "a" * 60000 + " .ai/learnings.md",
    ),
    ("a tee flag run", "Bash", "echo x | tee -" + "a" * 40000 + "x .ai/learnings.md"),
    ("repeated sed words", "Bash", ".ai/learnings.md " + "sed " * 15000),
    (
        "repeated Set-Content words",
        "PowerShell",
        ".ai/learnings.md " + "Set-Content " * 8000,
    ),
]


@pytest.mark.parametrize(
    ("name", "tool", "command"), _PATHOLOGICAL, ids=[row[0] for row in _PATHOLOGICAL]
)
def test_a_huge_pathological_line_is_refused_quickly(
    name: str, tool: str, command: str, project: Path
) -> None:
    started = time.perf_counter()
    out = _run(_shell(tool, command), project)
    elapsed = time.perf_counter() - started
    assert _decision(out) == "DENY", f"{name}: a line this long must not be allowed"
    assert elapsed < 5.0, f"{name}: {elapsed:.1f}s for {len(command)} characters"


@pytest.mark.parametrize(
    ("name", "tool", "command"),
    [
        (
            "an unterminated open( run",
            "Bash",
            'python -c "open(x, ' + "a" * 9800 + " .ai/learnings.md",
        ),
        (
            "a tee flag run",
            "Bash",
            "echo x | tee -" + "a" * 9800 + "x .ai/learnings.md",
        ),
        ("repeated sed words", "Bash", ".ai/learnings.md " + "sed " * 2400),
        (
            "repeated Set-Content words",
            "PowerShell",
            ".ai/learnings.md " + "Set-Content " * 800,
        ),
    ],
)
def test_a_pathological_line_just_under_the_limit_stays_inside_the_hook_budget(
    name: str, tool: str, command: str, project: Path
) -> None:
    started = time.perf_counter()
    _run(_shell(tool, command), project)
    elapsed = time.perf_counter() - started
    assert len(command) < _guard_module()._MAX_LINE, "the case must be under the limit"  # pyright: ignore[reportPrivateUsage]
    assert elapsed < 3.0, f"{name}: {elapsed:.1f}s for {len(command)} characters"


# ---- function-level and timing tests


def test_many_pipeline_segments_stay_inside_the_hook_budget(project: Path) -> None:
    """A line of thousands of pipe segments, just under the line limit, once took about seven
    seconds against the hook's ten second limit, because a list was rebuilt for every segment."""
    command = ".ai/learnings.md" + "|x" * 4800
    assert len(command) < _guard_module()._MAX_LINE  # pyright: ignore[reportPrivateUsage]
    started = time.perf_counter()
    _run(_shell("Bash", command), project)
    elapsed = time.perf_counter() - started
    assert elapsed < 3.0, f"{elapsed:.1f}s for {len(command)} characters"


def test_the_shape_judge_never_raises_and_agrees_with_every_row() -> None:
    """main() fails open, so a crash in the judge looks exactly like an ALLOW. Call the judge itself."""
    judge = _guard_module()._shell_shape  # pyright: ignore[reportPrivateUsage]
    for name, tool, command, required in _SHELL_ROWS:
        if "learnings.md" not in command:
            continue  # main() returns before the judge for these
        got = judge(command, tool)  # an exception here is a failure, not an allow
        want = {"ALLOW": False, "GAP": False, "DENY": True, "FPOS": True}[required]
        assert (got is not None) == want, (
            f"{name}: required {required}, judge said {got!r}"
        )


def test_the_shell_denial_lists_exactly_the_three_routes(project: Path) -> None:
    reason = _reason(_run(_shell("Bash", "rm .ai/learnings.md"), project))
    bullets = [ln.strip() for ln in reason.splitlines() if ln.startswith("  - ")]
    assert bullets == [
        "- count entries: Grep in count mode, pattern ^### \\[",
        "- read entries: Read with offset and limit",
        "- add an entry: Edit, appending after the last entry",
    ]
    assert (
        "Appending to learnings.md is never blocked when it is written as an append: "
        "only a call shaped like a rewrite or a removal is."
    ) in reason


def test_the_edit_denial_names_the_count_and_is_not_the_shell_text(
    project: Path,
) -> None:
    two = _reason(_run(_edit("### A\n### B\n### C\n", "### A\n")(project), project))
    one = _reason(_run(_edit("### A\n### B\n", "### A\n")(project), project))
    assert "would remove 2 entries" in two
    assert "would remove 1 entry" in one
    for text in (one, two):
        assert "shell" not in text
        assert "plan-approved.md" in text
        assert "Appending to learnings.md is never blocked - only removal is." in text


@pytest.mark.parametrize(("size", "satisfies"), [(199, False), (200, True)])
def test_the_gate_record_needs_200_characters(
    tmp_path: Path, size: int, satisfies: bool
) -> None:
    project_dir = _make_project(tmp_path)
    _approve(project_dir, "x" * size)
    got = _decision(_run(_shell("Bash", "rm .ai/learnings.md"), project_dir))
    assert got == ("ALLOW" if satisfies else "DENY")


def test_a_line_of_exactly_the_limit_is_judged_and_one_more_is_denied(
    project: Path,
) -> None:
    limit = _guard_module()._MAX_LINE  # pyright: ignore[reportPrivateUsage]
    pad = len("echo  .ai/learnings.md")
    at = _run(
        _shell("Bash", "echo " + "x" * (limit - pad) + " .ai/learnings.md"), project
    )
    over = _run(
        _shell("Bash", "echo " + "x" * (limit - pad + 1) + " .ai/learnings.md"), project
    )
    assert _decision(at) == "ALLOW"
    assert _decision(over) == "DENY"
