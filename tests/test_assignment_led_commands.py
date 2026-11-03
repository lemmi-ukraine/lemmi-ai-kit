"""Shipped text never shows a command that opens with an assignment.

The kit ships a hook (`plugins/core/hooks/gate_shell_prefix.py`) that a project can switch on to
refuse a Bash or PowerShell call whose first word is a `NAME=value` assignment, or a disguise of
one (`export`, `env`, `$env:` and so on). A prefix in front of the command defeats the permission
rules that match on the bare command, so the call prompts again, and under the hook it is refused.
A skill, reference or template that tells the model to run a block opening with an assignment
teaches exactly the call that hook refuses: an adopter who switches it on meets it in the kit's
own text.

The rule, over every `.md` and `.txt` file under `plugins/`:

- a fenced block in a shell language (sh, bash, shell, zsh, console, ps1, powershell, pwsh, cmd,
  bat) or with no language must not OPEN with an assignment-led line. A comment line counts as the
  opening line, so a block that starts with a comment is not flagged, and a leading `$ ` prompt is
  dropped first;
- an inline code span must not be assignment-led with a command after it. A span may wrap across
  lines but never across a blank line. The assignment is an optional `export`, `env` or similar
  word, then `NAME=value` words or a PowerShell `$env:NAME = value`; a command is a later word
  that is neither part of that nor bare punctuation.

"Assignment-led" is not re-implemented here. It is the hook's own `judge`, asked for the family
`ASSIGN`, so the rule and the guard cannot drift: the day the hook reads more or less, this test
follows it. Not flagged by design, each pinned by a planted negative: a later assignment
(`ls && FOO=bar cmd`, or any line after the first), `export NAME` with no value, a fenced block in
another language, a bare inline `NAME=value` (notation), an inline span whose words are all
`NAME=value` pairs (an output line), an inline span that only names the form (`env NAME=value`,
`$env:NAME = value`), keyword arguments (`logger=logger, ...`: a first word that ends with a
comma is call syntax), a continuation line, and `1A=b ls` (not an assignment in a POSIX shell). A
`$env:` form is judged as PowerShell, so it is flagged in a PowerShell block and in a block with
no language, and not in a block tagged for another shell.

THE ALLOWLIST. The lines that open with an assignment today are named in `_ALLOWED`, so this test
starts green and fails on the next one. It is a list of debts, not of permissions: fixing a line
deletes its entry in the same change, and `test_every_allowlisted_line_is_still_in_the_text` fails
on an entry whose line is gone, so the list can only shrink or be argued for.

THE SURFACE IS ASSERTED, NOT ASSUMED. `test_the_scan_surface_is_what_it_claims` states the scan in
numbers it asserts: the files of both surfaces, that the two are disjoint, that a tree walk and
`git ls-files` agree on them, and how many blocks and spans were actually judged. A zero from a
scan that never looked reads the same as a clean tree.

What this scan does not see: an indented (not fenced) code block, an assignment-led line outside
any fence or span, a fenced block tagged for a language that is not listed above, and text outside
`plugins/`. The kit's own AGENTS.md tells its readers to start a command with an assignment on
purpose; that file is not shipped, so it is not read.
"""

import importlib.util
import re
import subprocess
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / "plugins" / "core" / "hooks" / "gate_shell_prefix.py"

_SHIPPED = "plugins"
# What the scaffold copies into an adopter's project: a surface of its own, scanned by the same
# rule, so the two are listed and counted apart and must never share a file.
_ASSETS_TREE = "plugins/core/src/lemmi_ai_kit/assets/"
_TEXT_SUFFIXES = (".md", ".txt")

_POWERSHELL_TAGS = frozenset({"ps1", "powershell", "pwsh"})
_SHELL_TAGS = frozenset({"sh", "bash", "shell", "zsh", "console", "cmd", "bat"}) | (
    _POWERSHELL_TAGS
)

_FENCE = re.compile(r"^[ \t]*(?P<mark>`{3,}|~{3,})(?P<info>.*)$")
# A run of backticks closed by a run of exactly the same length (CommonMark's code span).
_SPAN = re.compile(
    r"(?<!`)(?P<ticks>`+)(?!`)(?P<code>.+?)(?<!`)(?P=ticks)(?!`)", re.DOTALL
)
_PROMPT = re.compile(r"^\$[ \t]+")
# A NAME=value word, and its PowerShell spelling `$env:NAME=value` with no space around the `=`.
_PAIR = re.compile(r"^(?:\$env:)?[A-Za-z_][A-Za-z0-9_]*\+?=\S*$", re.IGNORECASE)
# The words that introduce the assignments rather than being the command that follows them.
_WRAPPERS = frozenset({"export", "readonly", "declare", "typeset", "env"})
# `$env:NAME = value` with spaces: three words that together are the assignment.
_POWERSHELL_TARGET = re.compile(r"^\$(?:env:)?[A-Za-z_][A-Za-z0-9_]*$", re.IGNORECASE)
_POWERSHELL_OPERATOR = re.compile(r"^[-+*/%]?=$")

# The decision, as the scan asks for it: (command, tool name) -> the hook's denial family, or None.
Judge = Callable[[str, str], str | None]

# The lines that open with an assignment today: (file, the opening line or span with its
# whitespace folded) -> how many times. Each is a debt, not a permission; see the docstring.
_ALLOWED: dict[tuple[str, str], int] = {
    ("plugins/core/skills/kit-setup/SKILL.md", 'KIT_PROJECT_ROOT="$(pwd)"'): 1,
    ("plugins/core/skills/vertical-slice/SKILL.md", "FEATURE=my_feature"): 1,
    (
        "plugins/orchestration/skills/initiative-cleanup/SKILL.md",
        'S="${CLAUDE_SKILL_DIR}/scripts/audit_cleanup_targets.py"',
    ): 2,
    (
        "plugins/orchestration/skills/pr-comment-resolver/SKILL.md",
        "OLD=$(git rev-parse HEAD)",
    ): 1,
    # an inline span that wraps across two lines, so a scan that reads one line at a time misses it
    (
        "plugins/orchestration/skills/pr-comment-resolver/SKILL.md",
        "GH_TOKEN=" + chr(0x2026) + " gh api",
    ): 1,
}


# ------------------------------------------------------------------------------- the hook


@cache
def _hook() -> ModuleType:
    """The hook, loaded once from its file (it is a script, not a package)."""
    assert _HOOK.is_file(), f"the hook script does not exist: {_HOOK}"
    spec = importlib.util.spec_from_file_location("gate_shell_prefix_text_scan", _HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assign_family() -> str:
    return cast(str, _hook().ASSIGN)


def _hook_judge(command: str, tool: str) -> str | None:
    """The denial family the hook names for `command`, or None when it lets it through."""
    hook = _hook()
    verdict = cast(
        "tuple[str, str] | None", hook.judge(command, tool, hook.Config(), ".")
    )
    return None if verdict is None else verdict[0]


# ----------------------------------------------------------------------------- the parsing


@dataclass(frozen=True)
class _Block:
    tag: str  # lower-cased first word of the info string, "" when the fence has none
    line: int  # 1-based line of the block's first non-blank line
    opening: str  # that line, stripped


@dataclass(frozen=True)
class _Candidate:
    kind: str  # "fence" or "inline"
    line: int
    command: str  # the opening line or the span, prompt dropped, whitespace folded
    tools: tuple[str, ...]  # the tool names the hook is asked about


@dataclass(frozen=True)
class _Hit:
    path: str
    line: int
    kind: str
    command: str

    def where(self) -> str:
        return f"{self.path}:{self.line}"


def _fold(text: str) -> str:
    return " ".join(text.split())


def _command_of(text: str) -> str:
    return _fold(_PROMPT.sub("", text.strip(), count=1))


def _split(text: str) -> tuple[list[_Block], list[str]]:
    """The fenced blocks of a markdown text, and its prose with every fenced line blanked (so the
    line numbers of the prose stay true). A block left open at the end runs to the end."""
    blocks: list[_Block] = []
    prose: list[str] = []
    opener: str | None = None
    tag = ""
    opening: tuple[int, str] | None = None
    for number, line in enumerate(text.split("\n"), start=1):
        fence = _FENCE.match(line)
        if opener is None:
            # a run of backticks with more backticks after it on the line is a code span
            if fence is not None and not (
                fence["mark"][0] == "`" and "`" in fence["info"]
            ):
                opener = fence["mark"]
                tag = (fence["info"].split() or [""])[0].lower()
                opening = None
                prose.append("")
            else:
                prose.append(line)
            continue
        prose.append("")
        closes = (
            fence is not None
            and fence["mark"][0] == opener[0]
            and len(fence["mark"]) >= len(opener)
            and not fence["info"].strip()
        )
        if closes:
            if opening is not None:
                blocks.append(_Block(tag, *opening))
            opener = None
        elif opening is None and line.strip():
            opening = (number, line.strip())
    if opener is not None and opening is not None:
        blocks.append(_Block(tag, *opening))
    return blocks, prose


def _spans(prose: Sequence[str]) -> list[tuple[int, str]]:
    """The inline code spans of the prose as (line, whitespace-folded text)."""
    found: list[tuple[int, str]] = []
    start = 0
    paragraph: list[str] = []
    for number, line in enumerate([*prose, ""], start=1):
        if line.strip():
            if not paragraph:
                start = number
            paragraph.append(line)
            continue
        if paragraph:
            joined = "\n".join(paragraph)
            for match in _SPAN.finditer(joined):
                at = start + joined.count("\n", 0, match.start())
                found.append((at, _fold(match["code"])))
            paragraph = []
    return found


def _command_follows(span: str) -> bool:
    """Is there a command after the assignment: a word that is no part of it? `FEATURE=my_feature`,
    `a=1 b=2`, `env NAME=value` and `$env:NAME = value` are notation, and a first word that ends
    with a comma is call syntax or prose (`logger=logger, ...`), so none of them is a command."""
    words = span.split()
    if not words or words[0].endswith(","):
        return False
    index = 0
    if words[0] in _WRAPPERS:
        index = 1
        while index < len(words) and words[index].startswith("-"):
            index += 1
    while index < len(words):
        word = words[index]
        if _PAIR.match(word) or not any(char.isalnum() for char in word):
            index += 1
        elif (
            _POWERSHELL_TARGET.match(word)
            and index + 1 < len(words)
            and _POWERSHELL_OPERATOR.match(words[index + 1])
        ):
            index += 3
        else:
            return True
    return False


def _tools_for(tag: str) -> tuple[str, ...]:
    """A block tagged for PowerShell is PowerShell, any other shell is Bash, and a block with no
    language could be either, so the hook is asked about both."""
    if tag in _POWERSHELL_TAGS:
        return ("PowerShell",)
    return ("Bash", "PowerShell") if tag == "" else ("Bash",)


def _candidates(text: str) -> list[_Candidate]:
    """Every line the rule applies to: the opening line of each shell block and each span with a
    command after its assignments. Whether it is assignment-led is the hook's call, not this
    function's."""
    blocks, prose = _split(text)
    found = [
        _Candidate(
            "fence", block.line, _command_of(block.opening), _tools_for(block.tag)
        )
        for block in blocks
        if block.tag == "" or block.tag in _SHELL_TAGS
    ]
    for line, span in _spans(prose):
        command = _command_of(span)
        if _command_follows(command):
            found.append(_Candidate("inline", line, command, ("Bash", "PowerShell")))
    return found


def _hits_in(path: str, text: str, judge: Judge) -> list[_Hit]:
    family = _assign_family()
    return [
        _Hit(path, candidate.line, candidate.kind, candidate.command)
        for candidate in _candidates(text)
        if any(judge(candidate.command, tool) == family for tool in candidate.tools)
    ]


# ------------------------------------------------------------------- the surface and the rule


def _is_text(name: str) -> bool:
    return name.lower().endswith(_TEXT_SUFFIXES)


def _walk(root: Path) -> list[str]:
    """The text files under `plugins/` by a tree walk, which asks git nothing."""
    return sorted(
        path.relative_to(root).as_posix()
        for path in (root / _SHIPPED).rglob("*")
        if path.is_file() and _is_text(path.name)
    )


def _surfaces(root: Path) -> tuple[list[str], list[str]]:
    """(text outside the assets tree, text of the assets tree)."""
    files = _walk(root)
    inside = [name for name in files if name.startswith(_ASSETS_TREE)]
    outside = [name for name in files if not name.startswith(_ASSETS_TREE)]
    return outside, inside


def _git_files(root: Path, *flags: str) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", *flags, "--", _SHIPPED],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - git absent
        pytest.fail(f"git is not available, so the surface cannot be checked: {exc}")
    if result.returncode != 0:  # pragma: no cover - not a work tree
        pytest.fail("not a git work tree, so the surface cannot be checked")
    return {
        raw
        for raw in result.stdout.decode("utf-8").split("\0")
        if raw and _is_text(raw) and (root / raw).is_file()
    }


def _read(root: Path, files: Sequence[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for relative in files:
        try:
            texts[relative] = (root / relative).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            # Never skip silently: an unreadable file is a scan that did not look.
            pytest.fail(f"{relative} could not be scanned ({type(exc).__name__})")
    return texts


def _unallowed(
    hits: Sequence[_Hit], allowed: Mapping[tuple[str, str], int]
) -> list[_Hit]:
    """Every hit of a (file, line) pair that occurs more often than the allowlist says."""
    counts = Counter((hit.path, hit.command) for hit in hits)
    return [
        hit
        for hit in hits
        if counts[(hit.path, hit.command)] > allowed.get((hit.path, hit.command), 0)
    ]


def _violations(
    texts: Mapping[str, str], allowed: Mapping[tuple[str, str], int], judge: Judge
) -> list[str]:
    hits = [hit for path, text in texts.items() for hit in _hits_in(path, text, judge)]
    return [
        f"{hit.where()}: a {hit.kind} opens with an assignment: {hit.command!r}"
        for hit in _unallowed(hits, allowed)
    ]


# ------------------------------------------------------------------------- the tree itself


def test_the_scan_surface_is_what_it_claims() -> None:
    """A guard states its scan surface in numbers it asserts."""
    outside, inside = _surfaces(_REPO_ROOT)
    assert len(outside) >= 100, (
        f"only {len(outside)} text files outside the assets tree: the walk is broken"
    )
    assert len(inside) >= 5, (
        f"only {len(inside)} text files in the assets tree: the walk is broken"
    )
    assert not set(outside) & set(inside), "the two surfaces must not share a file"
    assert len(outside) + len(inside) == len(_walk(_REPO_ROOT))

    # Two independent enumerations must agree: the walk finds every file git lists, and a file
    # it finds that git does not list is one that git ignores.
    walked = set(outside) | set(inside)
    listed = _git_files(_REPO_ROOT, "--cached", "--others", "--exclude-standard")
    ignored = _git_files(_REPO_ROOT, "--others", "--ignored", "--exclude-standard")
    assert listed <= walked, (
        f"git lists files the walk missed: {sorted(listed - walked)[:5]}"
    )
    assert walked - listed <= ignored, (
        f"files on disk that git neither lists nor ignores: {sorted(walked - listed - ignored)[:5]}"
    )

    # And the parser must have judged something: a scan that finds no block and no span reads
    # the same as a clean tree.
    candidates = [
        candidate
        for text in _read(_REPO_ROOT, outside + inside).values()
        for candidate in _candidates(text)
    ]
    blocks = sum(1 for candidate in candidates if candidate.kind == "fence")
    spans = sum(1 for candidate in candidates if candidate.kind == "inline")
    assert blocks >= 100, (
        f"only {blocks} shell blocks were judged: the fence parser is blind"
    )
    assert spans >= 1000, (
        f"only {spans} inline spans were judged: the span parser is blind"
    )


def test_the_real_tree_flags_nothing_outside_the_allowlist() -> None:
    outside, inside = _surfaces(_REPO_ROOT)
    texts = _read(_REPO_ROOT, outside + inside)
    violations = _violations(texts, _ALLOWED, _hook_judge)
    assert not violations, (
        "shipped text that opens a command with an assignment:\n"
        + "\n".join(violations)
        + "\n\nThe hook this kit ships refuses that first word. Inline the value where it is "
        "used, or put the steps in a script file and run that. A line that is a deliberate "
        "exception goes into _ALLOWED with its reason; it is not an exemption to make quietly."
    )


def test_every_allowlisted_line_is_still_in_the_text() -> None:
    outside, inside = _surfaces(_REPO_ROOT)
    hits = [
        hit
        for path, text in _read(_REPO_ROOT, outside + inside).items()
        for hit in _hits_in(path, text, _hook_judge)
    ]
    counts = Counter((hit.path, hit.command) for hit in hits)
    stale = [
        f"{path}: {command!r} is allowed {allowed} time(s) but found {counts[(path, command)]}"
        for (path, command), allowed in _ALLOWED.items()
        if counts[(path, command)] < allowed
    ]
    assert not stale, (
        "allowlist entries whose line is gone or fixed (delete them in the same change):\n"
        + "\n".join(stale)
    )


# ------------------------------------------------------------------ the planted known cases

# (name, markdown text, the line the offence is reported at). Every one must be found, exactly
# once; each pins one class of shape.
_POSITIVES: list[tuple[str, str, int]] = [
    ("a fenced sh block", "```sh\nFOO=bar make test\n```\n", 2),
    ("a fenced bash block with two assignments", "```bash\nA=1 B=2 make\n```\n", 2),
    (
        "an untagged block with export and a value",
        "```\nexport X=1 && uv run pytest\n```\n",
        2,
    ),
    ("a prompt line in a console block", "```console\n$ FOO=bar make test\n```\n", 2),
    ("a prompt line in a bash block", "```bash\n$ FOO=bar make test\n```\n", 2),
    ("an env wrapper", "```sh\nenv FOO=bar make test\n```\n", 2),
    ("a PowerShell env assignment", "```powershell\n$env:FOO = 'x'; make\n```\n", 2),
    (
        "a PowerShell env assignment with no language",
        "```\n$env:FOO = 'x'; make\n```\n",
        2,
    ),
    ("a tilde fence", "~~~sh\nFOO=bar make\n~~~\n", 2),
    ("a fence inside a list item", "- step\n\n  ```sh\n  FOO=bar make\n  ```\n", 4),
    ("a fence of four backticks", "````sh\nFOO=bar make\n```\ntext\n````\n", 2),
    ("blank lines before the first line", "```sh\n\n\nFOO=bar make\n```\n", 4),
    ("a block that is never closed", "```sh\nFOO=bar make\n", 2),
    (
        "a block after an ordinary one",
        "```sh\nmake\n```\n\n```sh\nFOO=bar make\n```\n",
        6,
    ),
    (
        "an inline span with a command after the assignment",
        'Run `T=$(mktemp -d); uv run pytest -q --basetemp "$T"` first.\n',
        1,
    ),
    ("an inline span with export", "Run `export X=1 && make` first.\n", 1),
    (
        "an inline span with env and a command",
        "Run `env FOO=bar make test` first.\n",
        1,
    ),
    (
        "an inline span with a PowerShell env assignment",
        "Run `$env:FOO = 'x'; make` first.\n",
        1,
    ),
    ("an inline span that wraps across lines", "Run `FOO=bar\nmake test` first.\n", 1),
    (
        "an inline span on the second line of a paragraph",
        "Intro line\nthen `FOO=bar make` here.\n",
        2,
    ),
]

# (name, markdown text). None may be flagged; each pins one shape the rule leaves alone. The
# first group are the shapes an earlier, wider scan wrongly counted.
_NEGATIVES: list[tuple[str, str]] = [
    (
        "a bare inline pair that ends a sentence",
        "The grade is `confidence=PLAUSIBLE.` here.\n",
    ),
    (
        "an inline output line of pairs",
        "It probed `positive=3 negative=0 verdict=CAN-SEE` once.\n",
    ),
    (
        "inline keyword arguments with an ellipsis",
        "Pass `logger=logger, ...` as keywords.\n",
    ),
    ("inline call syntax", "Pass `request=cast(Any, None)` there.\n"),
    (
        "keyword arguments on the later lines of an untagged block",
        '```\nTool(\n  url="https://example.test/x",\n  prompt="say it",\n)\n```\n',
    ),
    ("an inline span that names the env form", "The form is `env NAME=value` here.\n"),
    (
        "an inline span that names the PowerShell form",
        "The form is `$env:NAME = value` here.\n",
    ),
    ("a bare inline pair", "Set `FEATURE=my_feature` first.\n"),
    ("a later assignment on the same line", "```sh\nls && FOO=bar cmd\n```\n"),
    ("an assignment on a later line", "```sh\nuv run tool\nFOO=bar cmd\n```\n"),
    ("export with no value", "```sh\nexport FOO\n```\n"),
    (
        "a fenced block in another language",
        "```python\nsvc = Service(\n    logger=logger, timeout=timeout)\n```\n",
    ),
    ("a yaml block", "```yaml\nkey=value\n```\n"),
    ("a block with a language that is not a shell", "```text\nFOO=bar\n```\n"),
    ("a continuation line", "```sh\nuv run tool \\\n  KEY=value\n```\n"),
    ("a name that is not an assignment in a POSIX shell", "```sh\n1A=b ls\n```\n"),
    ("a block that opens with a comment", "```sh\n# set it first\nFOO=bar cmd\n```\n"),
    (
        "a PowerShell form in a block tagged for another shell",
        "```sh\n$env:FOO = 'x'\n```\n",
    ),
    (
        "a span that does not start with an assignment",
        "Run `uv run tool KEY=value` now.\n",
    ),
    (
        "an example fence inside a longer fence",
        "````markdown\n```sh\nFOO=bar make\n```\n````\n",
    ),
    (
        "a shorter run of backticks does not end a longer fence",
        "````sh\nmake\n```\n```sh\nFOO=bar make\n```\n````\n",
    ),
]


def _positive_ids() -> list[str]:
    return [name for name, _, _ in _POSITIVES]


def _negative_ids() -> list[str]:
    return [name for name, _ in _NEGATIVES]


@pytest.mark.parametrize(("name", "text", "line"), _POSITIVES, ids=_positive_ids())
def test_the_scan_finds_the_planted_positive(name: str, text: str, line: int) -> None:
    hits = _hits_in("planted.md", text, _hook_judge)
    assert [hit.line for hit in hits] == [line], (
        f"{name}: expected one hit at line {line}, got {[hit.where() for hit in hits]}"
    )


@pytest.mark.parametrize(("name", "text"), _NEGATIVES, ids=_negative_ids())
def test_the_scan_leaves_the_planted_negative_alone(name: str, text: str) -> None:
    hits = _hits_in("planted.md", text, _hook_judge)
    assert not hits, f"{name}: flagged {[hit.command for hit in hits]}"


def test_a_new_line_in_a_copy_of_a_real_skill_is_reported_with_its_file_and_line() -> (
    None
):
    relative = "plugins/core/skills/kit-setup/SKILL.md"
    real = (_REPO_ROOT / relative).read_text(encoding="utf-8").rstrip("\n").split("\n")
    quiet = _violations({relative: "\n".join(real)}, _ALLOWED, _hook_judge)
    assert not quiet, f"the unplanted copy must be quiet, got {quiet}"

    planted = "\n".join([*real, "", "```sh", "FOO=planted make x", "```"])
    reported = _violations({relative: planted}, _ALLOWED, _hook_judge)
    assert len(reported) == 1, reported
    assert reported[0].startswith(f"{relative}:{len(real) + 3}: "), reported
    assert "FOO=planted make x" in reported[0], reported


def test_a_synthetic_tree_is_scanned_on_both_surfaces(tmp_path: Path) -> None:
    offence = "```sh\nFOO=bar make\n```\n"
    tree = {
        "plugins/one/skills/demo/SKILL.md": "text\n\n" + offence,
        "plugins/core/src/lemmi_ai_kit/assets/templates/NOTE.md": (
            "Run `T=$(mktemp -d); make` first.\n"
        ),
        "plugins/one/notes.txt": "```\n$ export X=1 && make\n```\n",
        "plugins/one/skills/demo/data.json": offence,
        "docs/outside.md": offence,
    }
    for relative, text in tree.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    outside, inside = _surfaces(tmp_path)
    assert outside == ["plugins/one/notes.txt", "plugins/one/skills/demo/SKILL.md"]
    assert inside == ["plugins/core/src/lemmi_ai_kit/assets/templates/NOTE.md"]

    reported = _violations(_read(tmp_path, outside + inside), {}, _hook_judge)
    assert sorted(line.split(": ")[0] for line in reported) == [
        "plugins/core/src/lemmi_ai_kit/assets/templates/NOTE.md:1",
        "plugins/one/notes.txt:2",
        "plugins/one/skills/demo/SKILL.md:4",
    ]


def _blind(_command: str, _tool: str) -> str | None:
    return None


def _flags_everything(_command: str, _tool: str) -> str | None:
    return _assign_family()


def _names_another_family(_command: str, _tool: str) -> str | None:
    return "move"


def test_a_hook_that_detects_nothing_leaves_every_planted_positive_unseen() -> None:
    """The positives are found by the hook's judgement and by nothing else in this file."""
    seen = [
        name for name, text, _ in _POSITIVES if _hits_in("planted.md", text, _blind)
    ]
    assert not seen, f"found without the hook's help: {seen}"


def test_the_decision_is_the_hooks_and_only_the_assign_family_counts() -> None:
    plain = "```sh\nls -la\n```\n"
    assert _hits_in("planted.md", plain, _flags_everything), (
        "a hook that flags everything must flag a plain opening line too"
    )
    offence = "```sh\nFOO=bar make\n```\n"
    assert not _hits_in("planted.md", offence, _names_another_family), (
        "a denial of another family is not an assignment"
    )


def test_the_hook_still_offers_what_the_scan_relies_on() -> None:
    assert _hook_judge("FOO=bar make", "Bash") == _assign_family()
    assert _hook_judge("$env:FOO = 'x'", "PowerShell") == _assign_family()
    assert _hook_judge("make test", "Bash") is None
