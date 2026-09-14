"""Compare Python executable tokens against a git revision.

Run from the consumer root with a revision and root-relative file paths. Comments
and actual docstrings are omitted; missing files, parse failures and token changes
return nonzero. This does not establish runtime equivalence of docstring metadata.
"""

from __future__ import annotations

import ast
import io
import subprocess
import sys
import tokenize
from pathlib import Path

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")


def code_tokens(src: str) -> list[tuple[str, str]]:
    """Executable tokens only: comments, docstrings and their statement NEWLINE removed.

    Docstrings are dropped WITH their terminating NEWLINE so that deleting one
    outright still compares identical -- otherwise every removed docstring reads
    as a code change and the check is useless for the job it exists to do.
    """
    out: list[tuple[str, str]] = []
    docstrings = []
    for node in ast.walk(ast.parse(src)):
        if (
            isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            )
            and node.body
            and isinstance(node.body[0], ast.Expr)
        ):
            value = node.body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                docstrings.append(
                    (
                        (value.lineno, value.col_offset),
                        (value.end_lineno, value.end_col_offset),
                    )
                )
    drop_newline = False
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type in (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING):
            continue
        if drop_newline and t.type == tokenize.NEWLINE:
            drop_newline = False
            continue
        if t.type == tokenize.STRING and any(
            start <= t.start and t.end <= end for start, end in docstrings
        ):
            drop_newline = True
            continue
        drop_newline = False
        out.append((tokenize.tok_name[t.type], t.string))
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: verify_no_code_change.py <ref> <file>...", file=sys.stderr)
        return 2
    ref, files = argv[0], argv[1:]
    bad = ok = missing = 0
    for f in files:
        r = subprocess.run(
            ["git", "show", f"{ref}:{f}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if r.returncode != 0:
            print(f"MISSING-AT-REF {f}")
            missing += 1
            continue
        try:
            a = code_tokens(r.stdout)
            b = code_tokens(Path(f).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, tokenize.TokenError, UnicodeDecodeError) as e:
            print(f"PARSE-ERROR    {f}: {e}")
            bad += 1
            continue
        if a == b:
            ok += 1
            continue
        bad += 1
        print(f"CODE-CHANGED   {f}")
        for i, (x, y) in enumerate(zip(a, b, strict=False)):
            if x != y:
                print(f"    first divergence at token {i}: {ref}={x!r}  worktree={y!r}")
                break
        else:
            print(f"    length differs: {ref}={len(a)} worktree={len(b)}")

    print(f"\nidentical={ok}  changed={bad}  missing={missing}")
    return 1 if bad or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
