"""Every command a shipped file prints is the one form that runs where it is read.

A skill prints a command for a model to run, and an installed plugin is not a checkout. At
c02f235, the commit before this test, the printed lines had drifted into four shapes that
nothing parsed: a `NAME=value` in front of the command, the bare `python -m lemmi_ai_kit` that
only a source checkout can import, a `lint` or `audit-skills` with no `--project` (under `uv
--directory` the working directory is the plugin, so discovery starts there: a single-file lint
target exits 2 for a file that is not there, and `lint all` prints a pass having measured the
plugin's own directory), and `list learnings`, a mode the parser does not have. A fifth shape,
the console script a plugin install never places, was printed in no shipped file at that
commit; the scan reads it as a guard, beside the hygiene scan that forbids it in skills.

THE ONE FORM, for a command that reaches the support CLI from a skill:

    uv run --no-project --directory "${ROOT}/src" python -B -m lemmi_ai_kit <sub> <args> ...

with nothing before it. `ROOT` is `CLAUDE_PLUGIN_ROOT` in a core file and `KIT_CORE_PLUGIN_ROOT`
in any other pack, which locates core through its kit-setup skill. `KIT_PLUGIN_ROOT` is allowed
only in a file that assigns it, which is kit-setup. The one other form is the checkout form of
`new-pack`, printed in the pack template, which never installs.

THE SCAN. The surface is two lists that must not overlap: every shipped markdown file outside
the assets tree, and every text file of the assets tree. A printed command is a fenced line or an
inline code span that holds `-m lemmi_ai_kit` or the console script; a span that opens with a
subcommand and has arguments is parsed too, which is how `list learnings` is caught though it
names no module. Each is parsed with the kit's own parser, `_build_parser()`, and each printed
`drain_audit.py` line with that script's own `build_parser()`. FILE is also checked before the
options on the tokens, because Python 3.12 reads `lint handoffs --project DIR FILE` and 3.11
refuses it, so a parse alone would pass on one and fail on the other.

WHAT KEEPS IT HONEST. The surface is stated in numbers the test asserts and was cross-checked by
two instruments (git's list against a walk of the tree). The printed commands are cross-checked
the same way: a raw count of every mention of the module per file against the count the
extractor found, so a mention outside any code span fails by name instead of being unseen. Each
rule is fired at a planted positive before its silence on the real files is believed.

NOT SCANNED, and a decision for the operator: `docs/` and `AGENTS.md` print commands that run
from a clone of this repository (some behind an environment prefix), not from an installed
plugin, so the one-form rule was not extended to them.
"""

import argparse
import contextlib
import functools
import importlib.util
import io
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import NamedTuple, cast

import pytest

from lemmi_ai_kit.cli import _build_parser  # pyright: ignore[reportPrivateUsage]
from lemmi_ai_kit.manifest import PACKS, assets_root

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = "plugins/core/src/lemmi_ai_kit/assets/"
_TEMPLATE = "plugins/_template/"
_ASSET_SUFFIXES = frozenset({".md", ".toml", ".txt", ".json", ".yaml", ".yml"})
_DRAIN_AUDIT = (
    _REPO_ROOT
    / "plugins"
    / "core"
    / "skills"
    / "learning-consolidator"
    / "scripts"
    / "drain_audit.py"
)


# --- the scan surface ---------------------------------------------------------------------


@functools.cache
def _published() -> tuple[str, ...]:
    """Everything under `plugins/` that a publish would carry, as git sees it.

    Tracked files plus untracked ones that are not ignored, because an unignored file under
    `plugins/` reaches an adopter whether or not it was ever committed.
    """
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "plugins",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:  # pragma: no cover - not a work tree
        pytest.fail("not a git work tree, so the shipped set cannot be listed")
    return tuple(
        sorted(
            raw
            for raw in result.stdout.decode("utf-8").split("\0")
            if raw and (_REPO_ROOT / raw).is_file()
        )
    )


def _markdown_surface() -> list[str]:
    return [p for p in _published() if p.endswith(".md") and not p.startswith(_ASSETS)]


def _asset_surface() -> list[str]:
    return [
        p
        for p in _published()
        if p.startswith(_ASSETS) and Path(p).suffix in _ASSET_SUFFIXES
    ]


def _walked(root: Path, suffixes: frozenset[str]) -> set[str]:
    """The second instrument for the surface: a walk of the tree, with no git in it."""
    return {
        path.relative_to(_REPO_ROOT).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in suffixes
        and "__pycache__" not in path.parts
    }


# --- reading the printed commands out of markdown -------------------------------------------


class _Element(NamedTuple):
    """One fenced command line (continuations joined) or one inline code span."""

    line: int
    text: str
    fenced: bool


_FENCE = re.compile(r"^\s*(?P<ticks>`{3,}|~{3,})(?P<rest>.*)$")
_SPAN = re.compile(
    r"(?<!`)(?P<ticks>`+)(?!`)(?P<body>.+?)(?<!`)(?P=ticks)(?!`)", re.DOTALL
)
_QUOTE = re.compile(r"^\s{0,3}(?:>\s?)+")
_NEWLINE = re.compile(r"\r?\n")


def _split_lines(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """(command lines of fenced blocks, prose lines), each with its 1-based line number.

    A fence labelled markdown holds a template that has inline spans of its own, so its
    lines are prose. A fence marker ends the paragraph it interrupts.
    """
    code: list[tuple[int, str]] = []
    prose: list[tuple[int, str]] = []
    opened: str | None = None
    template = False
    for number, raw in enumerate(_NEWLINE.split(text), 1):
        fence = _FENCE.match(raw)
        if fence is not None:
            ticks, rest = fence["ticks"], fence["rest"].strip()
            if opened is None:
                opened = ticks
                template = rest.split(" ")[0].lower() in {"markdown", "md"}
                prose.append((number, ""))
                continue
            if ticks[0] == opened[0] and len(ticks) >= len(opened) and not rest:
                opened = None
                template = False
                prose.append((number, ""))
                continue
        if opened is not None and not template:
            code.append((number, raw))
        else:
            prose.append((number, _QUOTE.sub("", raw)))
    return code, prose


def _printed_elements(text: str) -> list[_Element]:
    """Every fenced command line and every inline code span of `text`."""
    code, prose = _split_lines(text)
    found: list[_Element] = []
    index = 0
    while index < len(code):
        number, raw = code[index]
        parts = [raw.rstrip()]
        while parts[-1].endswith("\\") and index + 1 < len(code):
            parts[-1] = parts[-1][:-1]
            index += 1
            parts.append(code[index][1].strip())
        joined = " ".join(" ".join(parts).split())
        if joined and not joined.startswith("#"):
            found.append(_Element(number, joined, True))
        index += 1

    paragraph: list[tuple[int, str]] = []

    def flush() -> None:
        if not paragraph:
            return
        body = "\n".join(line for _, line in paragraph)
        for span in _SPAN.finditer(body):
            line = paragraph[0][0] + body.count("\n", 0, span.start())
            found.append(_Element(line, " ".join(span["body"].split()), False))
        paragraph.clear()

    for number, line in prose:
        if line.strip():
            paragraph.append((number, line))
        else:
            flush()
    flush()
    return sorted(found)


def _broken_continuations(text: str) -> list[int]:
    """Lines of fenced blocks that end a backslash continuation with a comment.

    The shell reads `\\` followed by spaces as an escaped space, then reads the `#` as a
    comment, so the next line runs as a command of its own.
    """
    return [
        number for number, raw in _split_lines(text)[0] if re.search(r"\\\s+#", raw)
    ]


# --- the parser the commands must satisfy ---------------------------------------------------


def _cli_subcommands() -> tuple[str, ...]:
    """Every subcommand the CLI declares, from the parser that declares them."""
    for action in _build_parser()._actions:  # pyright: ignore[reportPrivateUsage]
        choices = cast("dict[str, object] | None", getattr(action, "choices", None))
        if choices:
            return tuple(sorted(choices))
    raise AssertionError(
        "the CLI parser declares no subcommands -- the probe is broken"
    )


_SUBS = "|".join(re.escape(name) for name in _cli_subcommands())
_MODULE = re.compile(r"-m\s+lemmi_ai_kit\b")
_CONSOLE = re.compile(rf"\blemmi-ai-kit\s+(?:{_SUBS})\b")
_SUBCOMMAND_LED = re.compile(rf"^(?:{_SUBS})\s+\S")
_ENV_PREFIX = re.compile(r"""^(?:[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|'[^']*'|\S*)\s+)+""")
_CANONICAL = re.compile(
    r'^uv run --no-project --directory "\$\{(?P<root>[A-Z_]+)\}/src" '
    r"python -B -m lemmi_ai_kit(?: |$)"
)
_CHECKOUT = re.compile(r"^uv run python -B -m lemmi_ai_kit(?: |$)")
_SHELL_CONTROL = re.compile(r"^(?:\||\|\||&&|;|&|\d?>.*)$")


def _dummy(name: str) -> str:
    lowered = name.lower()
    for marker, value in (
        ("file", "HANDOFF.md"),
        ("project", "PROJECT"),
        ("skills", "SKILLS"),
    ):
        if marker in lowered:
            return value
    return "ROOT"


def _fill(text: str) -> str:
    """Stand-ins for the placeholders a printed command carries: optional `[...]` tokens
    are dropped, `${VAR}` and `<name>` become a dummy word."""
    text = re.sub(r"\[[^\[\]]*\]", " ", text)
    text = re.sub(r"\$\{([A-Za-z_]+)\}", lambda match: _dummy(match[1]), text)
    return re.sub(r"<([^<>]+)>", lambda match: _dummy(match[1]), text)


def _tokens(text: str) -> tuple[list[str], str]:
    """The shell words of a filled command, cut at the first pipe or redirect."""
    try:
        words = shlex.split(_fill(text))
    except ValueError as error:
        return [], f"cannot be split into shell words: {error}"
    for index, word in enumerate(words):
        if _SHELL_CONTROL.match(word):
            return words[:index], ""
    return words, ""


def _parse(
    parser: argparse.ArgumentParser, argv: list[str]
) -> tuple[argparse.Namespace | None, str]:
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            return parser.parse_args(argv), ""
    except SystemExit:
        message = " ".join(stderr.getvalue().split())
        return None, message.rsplit("error: ", 1)[-1]


def _cli_namespace(command: str) -> tuple[list[str], argparse.Namespace | None, str]:
    """The kit parser's reading of what follows `-m lemmi_ai_kit` in `command`."""
    module = _MODULE.search(command)
    assert module is not None, f"not a module command: {command!r}"
    words, problem = _tokens(command[module.end() :])
    if problem:
        return words, None, problem
    namespace, error = _parse(_build_parser(), words)
    return words, namespace, error


def _load(script: Path, name: str) -> ModuleType:
    """Import a script by path, without leaving bytecode inside the pack payload."""
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@functools.cache
def _drain_audit_parser() -> argparse.ArgumentParser:
    module = _load(_DRAIN_AUDIT, "drain_audit_printed_commands")
    return cast(argparse.ArgumentParser, module.build_parser())


# --- the rules ------------------------------------------------------------------------------


class _Finding(NamedTuple):
    line: int
    rule: str
    message: str
    command: str


# `--project` names the consuming project. Under `uv --directory` the working directory is the
# plugin's `src/`, so a relative root resolves inside the plugin, and `lint all` then measures
# nothing and still prints a pass. A printed placeholder therefore says the root is absolute:
# `<absolute project root>`, or the variable the other packs are told to keep absolute.
_ABSOLUTE_ROOT = re.compile(r"^(?:<absolute [^<>]*root>|\$\{KIT_PROJECT_ROOT\})$")
_PLAIN_ROOT = "<project root>"

# A printed `--project "<project root>"` that a file ships without the word absolute may be
# accepted where it stands, by file and by number. The list is empty: the three skills that
# the first wave shipped with the plain placeholder print the absolute one now, so nothing is
# accepted. An entry here is a file and how many plain placeholders it may print;
# `test_the_plain_project_placeholders_are_exactly_the_pending_ones` fails when a file prints
# more or fewer, so a listed file that is fixed must leave the list, and a file that goes back
# to the plain placeholder fails until it is fixed or listed.
_PENDING_PLAIN_ROOT: dict[str, int] = {}


def _raw_project(command: str) -> str | None:
    """The `--project` value as printed, before any placeholder is filled in."""
    module = _MODULE.search(command)
    if module is None:
        return None
    try:
        words = shlex.split(command[module.end() :])
    except ValueError:
        return None
    for index, word in enumerate(words):
        if word == "--project":
            return words[index + 1] if index + 1 < len(words) else None
        if word.startswith("--project="):
            return word.split("=", 1)[1]
    return None


def _expected_root(relative: str) -> str:
    """The plugin-root variable a printed command may use in this file."""
    pack = relative.split("/")[1]
    return "CLAUDE_PLUGIN_ROOT" if pack == "core" else "KIT_CORE_PLUGIN_ROOT"


def _module_problems(
    text: str, relative: str, assigned: frozenset[str]
) -> list[tuple[str, str]]:
    problems: list[tuple[str, str]] = []
    command = text
    prefix = _ENV_PREFIX.match(command)
    if prefix is not None:
        name = prefix.group(0).split("=", 1)[0]
        problems.append(
            (
                "env-prefix",
                f"sets {name} before the command; a printed command sets nothing first",
            )
        )
        command = command[prefix.end() :]

    canonical = _CANONICAL.match(command)
    checkout = _CHECKOUT.match(command)
    if canonical is None and checkout is None:
        problems.append(
            (
                "bare-module",
                "does not open with `uv run --no-project --directory "
                '"${ROOT}/src" python -B -m lemmi_ai_kit`, the one form that runs from '
                "an installed plugin",
            )
        )
    if canonical is not None:
        root = canonical["root"]
        if root == "KIT_PLUGIN_ROOT":
            if root not in assigned:
                problems.append(
                    (
                        "unassigned-variable",
                        "uses ${KIT_PLUGIN_ROOT}, which only a file that assigns it may "
                        "print (kit-setup does)",
                    )
                )
        elif root != _expected_root(relative):
            problems.append(
                (
                    "root-variable",
                    f"uses ${{{root}}}, but a file of this pack prints "
                    f"${{{_expected_root(relative)}}}",
                )
            )

    words, namespace, error = _cli_namespace(command)
    # From the tokens, before the parse: Python 3.11 fails the parse itself on this shape.
    problems += _positional_position_problems(words)
    if namespace is None:
        problems.append(("parse", f"the kit's parser refuses it: {error}"))
        return problems

    subcommand = cast(str, namespace.command)
    if checkout is not None and (
        not relative.startswith(_TEMPLATE) or subcommand != "new-pack"
    ):
        problems.append(
            (
                "checkout-form",
                "is the checkout form, which only the pack template prints for `new-pack`: "
                "it never installs",
            )
        )
    if canonical is not None:
        project_flag = {
            "lint": "project",
            "audit-skills": "project",
            "publish-check": "repo",
            "new-pack": "repo",
        }.get(subcommand)
        if project_flag and getattr(namespace, project_flag) is None:
            problems.append(
                (
                    "no-project",
                    f"has no --{project_flag}: under `uv --directory` the working directory "
                    "is the plugin, so the check measures that directory, not the project",
                )
            )
        if subcommand == "scaffold" and cast(str, namespace.target) == ".":
            problems.append(
                (
                    "no-project",
                    "scaffolds `.`, which is the plugin under `uv --directory`; name the "
                    "project as the target",
                )
            )
        printed_root = _raw_project(command)
        if (
            printed_root is not None
            and not _ABSOLUTE_ROOT.match(printed_root)
            and not (printed_root == _PLAIN_ROOT and relative in _PENDING_PLAIN_ROOT)
        ):
            problems.append(
                (
                    "relative-project",
                    f"passes {printed_root!r} as the project root without saying it is "
                    "absolute: a relative root resolves inside the plugin under `uv "
                    "--directory`, so the check measures nothing and still passes. Print "
                    "`<absolute project root>`",
                )
            )
    return problems


@functools.cache
def _valued_options() -> frozenset[str]:
    """The options of `lint` that take a value, read off the parser that declares them."""
    for action in _build_parser()._actions:  # pyright: ignore[reportPrivateUsage]
        choices = cast(
            "dict[str, argparse.ArgumentParser] | None",
            getattr(action, "choices", None),
        )
        if choices and "lint" in choices:
            return frozenset(
                option
                for declared in choices["lint"]._actions  # pyright: ignore[reportPrivateUsage]
                if declared.nargs != 0
                for option in declared.option_strings
            )
    raise AssertionError(
        "the CLI parser declares no `lint` subcommand -- the probe is broken"
    )


def _positional_position_problems(words: list[str]) -> list[tuple[str, str]]:
    """The target and FILE of `lint` go before every option.

    Python 3.11 stops reading positionals at the first option, so `lint handoffs --project
    DIR FILE` is refused there and read from 3.12 on. A parse alone would pass on one
    interpreter and fail on the other, so the order is checked on the tokens.
    """
    if not words or words[0] != "lint":
        return []
    after_option = False
    skip = False
    for word in words[1:]:
        if skip:
            skip = False
        elif word.startswith("-"):
            after_option = True
            skip = word in _valued_options()
        elif after_option:
            return [
                (
                    "file-after-option",
                    f"writes {word!r} after an option; Python 3.11 refuses that and 3.12 "
                    "reads it, so write the target and FILE directly after `lint`",
                )
            ]
    return []


def _drain_audit_argv(text: str) -> tuple[list[str] | None, str]:
    """What follows `drain_audit.py` in a printed line, or None when the line only names it.

    The second element is a reason the line could not be read at all, or empty."""
    if "drain_audit.py" not in text:
        return None, ""
    words, problem = _tokens(text)
    if problem:
        return None, problem
    script = next(
        (i for i, word in enumerate(words) if word.endswith("drain_audit.py")), -1
    )
    if script < 0 or script + 1 >= len(words):
        return None, ""  # names the script and prints no command
    return words[script + 1 :], ""


def _drain_audit_problems(text: str) -> list[tuple[str, str]]:
    argv, problem = _drain_audit_argv(text)
    if problem:
        return [("drain-audit", problem)]
    if argv is None:
        return []
    _, error = _parse(_drain_audit_parser(), argv)
    if error:
        return [("drain-audit", f"drain_audit's own parser refuses it: {error}")]
    return []


def _element_problems(
    element: _Element, relative: str, assigned: frozenset[str]
) -> list[tuple[str, str]]:
    text = element.text
    problems: list[tuple[str, str]] = []
    if _CONSOLE.search(text):
        problems.append(
            (
                "console-script",
                "names the `lemmi-ai-kit` console script, which a plugin install never places",
            )
        )
    if _MODULE.search(text):
        problems += _module_problems(text, relative, assigned)
    elif (
        not element.fenced and _SUBCOMMAND_LED.match(text) and not _CONSOLE.search(text)
    ):
        words, problem = _tokens(text)
        error = problem or _parse(_build_parser(), words)[1]
        if error:
            problems.append(("parse", f"the kit's parser refuses it: {error}"))
    if "drain_audit.py" in text:
        problems += _drain_audit_problems(text)
    return problems


def _findings(relative: str, text: str) -> list[_Finding]:
    """Every problem of every printed command in one markdown text."""
    assigned = frozenset(re.findall(r"^\s*(KIT_[A-Z_]+)=", text, re.MULTILINE))
    found = [
        _Finding(element.line, rule, message, element.text)
        for element in _printed_elements(text)
        for rule, message in _element_problems(element, relative, assigned)
    ]
    found += [
        _Finding(
            number,
            "broken-continuation",
            "ends a backslash continuation with a comment; the next line runs on its own",
            "",
        )
        for number in _broken_continuations(text)
    ]
    return sorted(found)


def _render(relative: str, finding: _Finding) -> str:
    shown = f" -- {finding.command[:100]!r}" if finding.command else ""
    return f"{relative}:{finding.line}: [{finding.rule}] {finding.message}{shown}"


def _is_module_command(element: _Element) -> bool:
    return bool(_MODULE.search(element.text) or _CONSOLE.search(element.text))


def _is_printed_command(element: _Element) -> bool:
    """Everything the rules read: a module or console-script command, a span that opens with a
    subcommand and has arguments, and a `drain_audit.py` line that prints arguments."""
    return (
        _is_module_command(element)
        or (not element.fenced and bool(_SUBCOMMAND_LED.match(element.text)))
        or _drain_audit_argv(element.text)[0] is not None
    )


def _mentions(text: str) -> int:
    return len(_MODULE.findall(text)) + len(_CONSOLE.findall(text))


def _mention_gap(text: str) -> tuple[int, int]:
    """(mentions of the module in the raw text, mentions inside the extracted elements)."""
    seen = sum(_mentions(element.text) for element in _printed_elements(text))
    return _mentions(text), seen


def _read(relative: str) -> str:
    return (_REPO_ROOT / relative).read_text(encoding="utf-8")


# Files that print a support-CLI command in a code span or a fence today. The scan must keep
# reading a command out of each, or it has gone blind on the file it is named for.
_PRINT_A_COMMAND: tuple[str, ...] = (
    "plugins/core/skills/ai-changelog/SKILL.md",
    "plugins/core/skills/ai-improvement-tracker/SKILL.md",
    "plugins/core/skills/kit-setup/SKILL.md",
    "plugins/core/skills/session-retrospective/SKILL.md",
    "plugins/core/skills/task-learnings/SKILL.md",
    "plugins/orchestration/README.md",
    "plugins/skill-authoring/README.md",
    "plugins/orchestration/skills/parallel-session-safety/SKILL.md",
    "plugins/_template/README.md",
)

# Files the scan must contain whether or not they print a command.
_MUST_BE_SCANNED: tuple[str, ...] = (
    "plugins/core/skills/task-learnings/references/learnings-format.md",
    "plugins/core/skills/session-retrospective/references/report-template.md",
    "plugins/skill-authoring/skills/skill-reviewer/references/review-checklist.md",
    "plugins/orchestration/skills/agent-delegate/SKILL.md",
    "plugins/orchestration/skills/branch-diff-review/SKILL.md",
)
_MUST_BE_SCANNED_ASSETS: tuple[str, ...] = (
    "plugins/core/src/lemmi_ai_kit/assets/templates/AGENTS.md",
    "plugins/core/src/lemmi_ai_kit/assets/templates/CLAUDE.md",
)


# --- the tests ------------------------------------------------------------------------------


def test_the_scan_surface_is_what_it_claims() -> None:
    """A guard states its scan surface in numbers it asserts, cross-checked two ways."""
    markdown = _markdown_surface()
    assets = _asset_surface()
    assert len(markdown) > 120, (
        f"only {len(markdown)} shipped markdown files in the scan"
    )
    assert len(assets) > 8, f"only {len(assets)} asset text files in the scan"
    assert not set(markdown) & set(assets), "the two surfaces must not overlap"

    plugins = _REPO_ROOT / "plugins"
    walked_markdown = {
        p for p in _walked(plugins, frozenset({".md"})) if not p.startswith(_ASSETS)
    }
    assert assets_root().resolve() == (_REPO_ROOT / _ASSETS).resolve(), (
        "the imported package is not this checkout's, so a walk of its assets would read "
        "another tree than the one git lists"
    )
    walked_assets = _walked(assets_root(), _ASSET_SUFFIXES)
    assert set(markdown) == walked_markdown, (
        f"git lists {len(markdown)} markdown files and a walk finds {len(walked_markdown)}; "
        f"only one sees {sorted(set(markdown) ^ walked_markdown)} -- an ignored or deleted "
        "file in the payload"
    )
    assert set(assets) == walked_assets, (
        f"git lists {len(assets)} asset text files and a walk finds {len(walked_assets)}; "
        f"only one sees {sorted(set(assets) ^ walked_assets)}"
    )

    for name in (*_PRINT_A_COMMAND, *_MUST_BE_SCANNED):
        assert name in markdown, f"{name} is no longer in the markdown scan"
    for name in _MUST_BE_SCANNED_ASSETS:
        assert name in assets, f"{name} is no longer in the asset scan"

    elements = [
        element
        for relative in (*markdown, *assets)
        for element in _printed_elements(_read(relative))
    ]
    commands = [element for element in elements if _is_module_command(element)]
    assert len(commands) > 20, f"only {len(commands)} printed commands were found"
    drain = [e for e in elements if _drain_audit_argv(e.text)[0] is not None]
    assert len(drain) > 3, (
        f"only {len(drain)} printed `drain_audit.py` lines were found, so the parse of "
        "that script's own parser would be close to vacuous"
    )
    for name in _PRINT_A_COMMAND:
        mine = [e for e in _printed_elements(_read(name)) if _is_module_command(e)]
        assert mine, f"the scan reads no printed command out of {name}"


def test_the_extractor_and_a_raw_count_agree_on_every_file() -> None:
    """Two instruments: the mentions of the module per file against the commands extracted.

    A mention outside any code span is a command the extractor never sees, so the raw count
    runs ahead and the file is named.
    """
    disagree = {
        relative: gap
        for relative in (*_markdown_surface(), *_asset_surface())
        if (gap := _mention_gap(_read(relative)))[0] != gap[1]
    }
    assert not disagree, (
        "files whose mentions of the module are not all inside a code span or a fence "
        "(raw count, extracted count): "
        + ", ".join(f"{k} {v}" for k, v in disagree.items())
    )


def test_every_printed_command_has_the_one_form_and_parses() -> None:
    problems: list[str] = []
    commands = 0
    breaking = 0
    stray = 0
    for relative in (*_markdown_surface(), *_asset_surface()):
        text = _read(relative)
        commands += sum(1 for e in _printed_elements(text) if _is_printed_command(e))
        found = _findings(relative, text)
        breaking += len({finding.line for finding in found if finding.command})
        stray += sum(1 for finding in found if not finding.command)
        problems += [_render(relative, finding) for finding in found]
    assert not problems, (
        f"{breaking} of {commands} printed commands break the one form, and {stray} fenced "
        f"line(s) end a continuation with a comment ({len(problems)} problems in all):\n"
        + "\n".join(problems)
    )


_CORE = "plugins/core/skills/demo/SKILL.md"
_OTHER = "plugins/orchestration/skills/demo/SKILL.md"
_UV = 'uv run --no-project --directory "${CLAUDE_PLUGIN_ROOT}/src" python -B -m lemmi_ai_kit'
_UV_OTHER = 'uv run --no-project --directory "${KIT_CORE_PLUGIN_ROOT}/src" python -B -m lemmi_ai_kit'


def _fence(*lines: str) -> str:
    return "```bash\n" + "\n".join(lines) + "\n```\n"


_PLANTED: tuple[tuple[str, str, str], ...] = (
    (
        "env-prefix",
        _CORE,
        _fence(f'PYTHONDONTWRITEBYTECODE=1 {_UV} lint all --project "<project root>"'),
    ),
    (
        "env-prefix",
        _CORE,
        'Run (`PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint\n'
        "   learnings --list-entries`) now.\n",
    ),
    ("bare-module", _CORE, "Run `python -m lemmi_ai_kit lint learnings` now.\n"),
    (
        "bare-module",
        _CORE,
        'Run `uv run python -m lemmi_ai_kit audit-skills --project "<project root>"`.\n',
    ),
    ("console-script", _CORE, _fence("lemmi-ai-kit lint all")),
    ("parse", _CORE, "The count is printed by `list learnings`.\n"),
    ("parse", _CORE, f'Run `{_UV} lint nowhere --project "<project root>"`.\n'),
    ("no-project", _CORE, _fence(f"{_UV} lint learnings")),
    ("no-project", _CORE, _fence(f"{_UV} audit-skills --fail-on major")),
    ("no-project", _CORE, _fence(f"{_UV} scaffold")),
    ("no-project", _CORE, _fence(f"{_UV} publish-check")),
    (
        "relative-project",
        _CORE,
        _fence(f'{_UV} lint all --project "<project root>"'),
    ),
    ("relative-project", _CORE, _fence(f"{_UV} audit-skills --project .")),
    (
        "relative-project",
        "plugins/core/skills/hypothesis-validator/SKILL.md",
        _fence(f"{_UV} lint hypotheses --project ."),
    ),
    (
        "file-after-option",
        _OTHER,
        _fence(f'{_UV_OTHER} lint handoffs --project "${{KIT_PROJECT_ROOT}}" <file>'),
    ),
    (
        "root-variable",
        _OTHER,
        _fence(f'{_UV} lint all --project "${{KIT_PROJECT_ROOT}}"'),
    ),
    (
        "root-variable",
        _CORE,
        _fence(f'{_UV_OTHER} lint all --project "<project root>"'),
    ),
    (
        "unassigned-variable",
        _CORE,
        _fence(
            'uv run --no-project --directory "${KIT_PLUGIN_ROOT}/src" python -B -m '
            'lemmi_ai_kit scaffold "<project root>"'
        ),
    ),
    (
        "checkout-form",
        _CORE,
        _fence("uv run python -B -m lemmi_ai_kit new-pack rust --skill x"),
    ),
    (
        "drain-audit",
        _CORE,
        _fence('python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <snapshot>.md'),
    ),
    (
        "broken-continuation",
        _CORE,
        _fence("python scripts/extract_sessions.py \\  # path of the script", "  out/"),
    ),
)

_CLEAN: tuple[tuple[str, str], ...] = (
    (
        _CORE,
        _fence(
            f'{_UV} lint learnings --list-entries --project "<absolute project root>"'
        ),
    ),
    (_CORE, f'Run `{_UV} lint all --project "<absolute project root>"` now.\n'),
    (
        _CORE,
        'Run (`uv run --no-project --directory "${CLAUDE_PLUGIN_ROOT}/src" python -B -m\n'
        '   lemmi_ai_kit audit-skills --project "<absolute project root>"`) now.\n',
    ),
    (
        "plugins/core/skills/hypothesis-validator/SKILL.md",
        _fence(f'{_UV} lint hypotheses --project "<absolute project root>"'),
    ),
    (
        _OTHER,
        _fence(
            f'{_UV_OTHER} lint handoffs <file> --resolve-anchors --project "${{KIT_PROJECT_ROOT}}"',
            f'{_UV_OTHER} lint handoffs <file> --list-commands --project "${{KIT_PROJECT_ROOT}}"',
        ),
    ),
    (
        _OTHER,
        _fence(
            f'{_UV_OTHER} audit-skills --project "${{KIT_PROJECT_ROOT}}" \\',
            '  --skills-dir "${KIT_SKILLS_DIR}" --fail-on major',
        ),
    ),
    (
        _CORE,
        'KIT_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"\n'
        + _fence(
            'uv run --no-project --directory "${KIT_PLUGIN_ROOT}/src" python -B -m '
            'lemmi_ai_kit scaffold "<project root>"'
        ),
    ),
    (
        "plugins/_template/README.md",
        _fence("uv run python -B -m lemmi_ai_kit new-pack <pack> --skill <skill-name>"),
    ),
    (_CORE, _fence(f'{_UV} lint all --project "<absolute project root>" | tail -3')),
    (
        _CORE,
        'Run `python "${CLAUDE_SKILL_DIR}/scripts/drain_audit.py" <snapshot>.md HEAD`.\n',
    ),
    (
        _CORE,
        "The `lint learnings` target and the `audit-skills` subcommand are read-only.\n",
    ),
    (
        _CORE,
        _fence(
            f"{_UV} lint all \\",
            '  --project "<absolute project root>"',
            "# a comment line between commands is not a continuation",
            "python scripts/x.py",
        ),
    ),
    (
        _CORE,
        _fence(
            f'{_UV} lint all --project "<absolute project root>" --since 2026-01-01'
        ),
    ),
)


def test_every_rule_fires_on_its_planted_positive() -> None:
    """A rule never shown to fire has not been shown to work: at least one planted text per
    rule, and a rule with none fails the set comparison below."""
    for rule, relative, text in _PLANTED:
        fired = [finding.rule for finding in _findings(relative, text)]
        assert rule in fired, (
            f"the {rule!r} rule did not fire on its planted positive {text!r}; "
            f"the rules that did: {fired}"
        )
    assert {rule for rule, _, _ in _PLANTED} == {
        "env-prefix",
        "bare-module",
        "console-script",
        "parse",
        "no-project",
        "relative-project",
        "file-after-option",
        "root-variable",
        "unassigned-variable",
        "checkout-form",
        "drain-audit",
        "broken-continuation",
    }, "a rule of the scan has no planted positive, or a planted positive names no rule"


def test_clean_text_raises_no_finding() -> None:
    """The negative half: each form the skills may print passes, so no rule is over-broad."""
    for relative, text in _CLEAN:
        found = [_render(relative, finding) for finding in _findings(relative, text)]
        assert not found, f"clean text was flagged: {text!r}\n" + "\n".join(found)


def test_a_mention_outside_any_code_span_breaks_the_instrument_agreement() -> None:
    """Planted: a command in plain prose is invisible to the extractor and visible to the count."""
    bare = "To audit, run python -m lemmi_ai_kit audit-skills and read the result.\n"
    raw, seen = _mention_gap(bare)
    assert (raw, seen) == (1, 0)
    inside = (
        "To audit, run `python -m lemmi_ai_kit audit-skills` and read the result.\n"
    )
    assert _mention_gap(inside) == (1, 1)
    fenced = "```bash\npython -m lemmi_ai_kit lint all\n```\n"
    assert _mention_gap(fenced) == (1, 1)
    comment = "```bash\n# python -m lemmi_ai_kit lint all\n```\n"
    assert _mention_gap(comment) == (1, 0), "a mention inside a comment is a gap too"
    both = (
        "A `python -m lemmi_ai_kit lint` span, then python -m lemmi_ai_kit lint bare.\n"
    )
    assert _mention_gap(both) == (2, 1)


def test_the_extractor_reads_spans_that_wrap_and_fences_that_continue() -> None:
    """The reading rules themselves, on shapes the shipped text has."""
    wrapped = (
        "(`PYTHONPATH=x python -m lemmi_ai_kit lint\n   learnings --list-entries`)\n"
    )
    assert [e.text for e in _printed_elements(wrapped)] == [
        "PYTHONPATH=x python -m lemmi_ai_kit lint learnings --list-entries"
    ]
    quoted = "> `python -m lemmi_ai_kit audit-skills` (read-only) and\n> more.\n"
    assert [e.text for e in _printed_elements(quoted)] == [
        "python -m lemmi_ai_kit audit-skills"
    ]
    template = "```markdown\nRun `python -m lemmi_ai_kit lint` here\n```\n"
    assert [(e.text, e.fenced) for e in _printed_elements(template)] == [
        ("python -m lemmi_ai_kit lint", False)
    ]
    continued = "```sh\nuv run x \\\n  python -m lemmi_ai_kit lint all\n```\n"
    assert [(e.line, e.text) for e in _printed_elements(continued)] == [
        (2, "uv run x python -m lemmi_ai_kit lint all")
    ]
    double = "A ``code `with` ticks`` and `lint learnings` span.\n"
    assert [e.text for e in _printed_elements(double)] == [
        "code `with` ticks",
        "lint learnings",
    ]
    fenced_tilde = "~~~\nlemmi-ai-kit lint\n~~~\nprose with `list` only\n"
    assert [(e.fenced, e.text) for e in _printed_elements(fenced_tilde)] == [
        (True, "lemmi-ai-kit lint"),
        (False, "list"),
    ]


def test_the_checkout_form_is_allowed_only_where_nothing_installs() -> None:
    """The template is the one file that prints the checkout form, so it must never ship."""
    assert "_template" not in PACKS
    for marketplace in (
        ".claude-plugin/marketplace.json",
        ".agents/plugins/marketplace.json",
    ):
        assert "_template" not in _read(marketplace), (
            f"{marketplace} lists the pack template, which prints the checkout form"
        )
    template = _read("plugins/_template/README.md")
    assert [
        finding.rule for finding in _findings("plugins/_template/README.md", template)
    ] == []
    printed = [e for e in _printed_elements(template) if _is_module_command(e)]
    assert printed, "the template prints no command, so its carve-out covers nothing"
    for element in printed:
        _, namespace, _ = _cli_namespace(element.text)
        assert namespace is not None and namespace.command == "new-pack", element.text


def _handoff_commands(relative: str) -> list[argparse.Namespace]:
    """The kit parser's reading of every `lint handoffs` command a file prints."""
    found: list[argparse.Namespace] = []
    for element in _printed_elements(_read(relative)):
        if _MODULE.search(element.text):
            _, namespace, _ = _cli_namespace(element.text)
            if namespace is not None and (namespace.command, namespace.target) == (
                "lint",
                "handoffs",
            ):
                found.append(namespace)
    return found


def test_agent_delegate_checks_the_anchors_of_the_one_hand_off_it_received() -> None:
    """Anchors resolve only under `--resolve-anchors`, and the command takes ONE file.

    The text told the reader to check that the anchors resolve in git and printed no way
    to do it. The check exists now: it names the hand-off, and the flag is what makes it
    look at the anchors at all.
    """
    namespaces = _handoff_commands(
        "plugins/orchestration/skills/agent-delegate/SKILL.md"
    )
    assert namespaces, "agent-delegate prints no `lint handoffs` command"
    assert any(n.file is not None and n.resolve_anchors for n in namespaces), (
        "no printed command lints the one hand-off the delegate returned with "
        "--resolve-anchors"
    )


# The stale claim is that checking your own hand-off lints everyone's. Saying that the target
# lints every hand-off when no file is named is true, and stays.
_LINTS_EVERY_HANDOFF = re.compile(
    r"lints\s+every\s+hand-?off,?\s+not\s+only\s+yours", re.IGNORECASE
)


def test_branch_diff_review_lints_the_hand_off_it_wrote() -> None:
    """The review writes one hand-off, so it names that file; it no longer says the target
    lints every hand-off, which was true before the command took a file."""
    relative = "plugins/orchestration/skills/branch-diff-review/SKILL.md"
    namespaces = _handoff_commands(relative)
    assert any(n.file is not None for n in namespaces), (
        "branch-diff-review prints no `lint handoffs` command that names the one file"
    )
    flat = " ".join(_read(relative).split())
    assert not _LINTS_EVERY_HANDOFF.search(flat), (
        "branch-diff-review still says the target lints every hand-off"
    )
    assert _LINTS_EVERY_HANDOFF.search("the target lints every handoff, not only yours")
    assert not _LINTS_EVERY_HANDOFF.search("lints the one hand-off you wrote")
    assert not _LINTS_EVERY_HANDOFF.search(
        "Leave `<file>` out and the target lints every hand-off in the directory"
    )


def _plain_root_counts(texts: dict[str, str]) -> dict[str, int]:
    """File -> how many of its printed commands pass `--project "<project root>"`, for the
    files that print any."""
    counts = {
        relative: sum(
            1
            for element in _printed_elements(text)
            if _raw_project(element.text) == _PLAIN_ROOT
        )
        for relative, text in texts.items()
    }
    return {relative: count for relative, count in counts.items() if count}


def _pending_drift(plain: dict[str, int], pending: dict[str, int]) -> str:
    """Why the accepted list is not the set of files that print the plain placeholder, or
    an empty string when it is."""
    if plain == pending:
        return ""
    return (
        f"files that print --project {_PLAIN_ROOT!r} (file: how many) are {plain}, and the "
        f"accepted list is {pending}. A printed project root says `<absolute project root>`; "
        "a listed file that has been fixed leaves the list"
    )


def test_the_plain_project_placeholders_are_exactly_the_pending_ones() -> None:
    """The exemption of `_PENDING_PLAIN_ROOT` is a list of files and a number each, both
    ways. The list is empty, so this says that no printed command passes the plain one."""
    surface = (*_markdown_surface(), *_asset_surface())
    plain = _plain_root_counts({relative: _read(relative) for relative in surface})
    drift = _pending_drift(plain, _PENDING_PLAIN_ROOT)
    assert not drift, drift


def test_the_count_of_plain_placeholders_sees_each_shape_a_file_prints() -> None:
    """Planted: an empty list passes only if the counter can see, so fire it at the shapes
    the three skills printed: two commands in one fence, one alone, and inline spans (one
    wrapped across lines) in running prose. The absolute placeholder is not counted."""
    fenced = _fence(
        f'{_UV} lint --project "<project root>"',
        f'{_UV} audit-skills --project "<project root>"',
    )
    alone = _fence(f'{_UV} lint hypotheses --project "<project root>"')
    spans = (
        "count intake entries (run\n"
        f'   `{_UV} lint learnings --list-entries --project "<project root>"`)\n'
        "and, further down, run\n"
        f'   `{_UV} lint learnings --project "<project root>"`.\n'
    )
    absolute = _fence(f'{_UV} lint all --project "<absolute project root>"')
    assert _plain_root_counts(
        {"fenced": fenced, "alone": alone, "spans": spans, "absolute": absolute}
    ) == {"fenced": 2, "alone": 1, "spans": 2}


def test_the_pending_list_is_compared_in_both_directions_and_by_number() -> None:
    """Planted: a file that went back to the plain placeholder, an entry that no file earns,
    and a wrong count each differ from the list; the exact match does not."""
    listed = {"plugins/core/skills/demo/SKILL.md": 2}
    assert _pending_drift({}, {}) == ""
    assert _pending_drift(listed, listed) == ""
    assert _pending_drift(listed, {}), "a file prints it and the list is empty"
    assert _pending_drift({}, listed), "an entry that no file earns is stale"
    more = {"plugins/core/skills/demo/SKILL.md": 3}
    assert _pending_drift(more, listed), "a file prints more than its entry allows"
    fewer = {"plugins/core/skills/demo/SKILL.md": 1}
    assert _pending_drift(fewer, listed), "a file prints fewer than its entry says"


# --- `lint learnings`: the verdict and the entry count are two different commands --------------

# With no flag `lint learnings` lints and prints a verdict; `--list-entries` prints the entry
# inventory INSTEAD of linting. So a sentence that asks for the count needs the flag, and one
# that asks for the verdict must not carry it. The verdict uses are the exceptions, each named
# by the words of the sentence that asks for it; every other printed `lint learnings` is a count.
_VERDICT_USES: dict[str, re.Pattern[str]] = {
    "plugins/core/skills/task-learnings/SKILL.md": re.compile(r"read\s+the\s+verdict"),
    "plugins/core/skills/learning-consolidator/SKILL.md": re.compile(
        r"\(zero\s+findings\s+required\),\s+then\s+re-read"
    ),
}
# Lines between the words that ask for a verdict and the command that answers them.
_VERDICT_NEAR = 4


class _LearningsUse(NamedTuple):
    line: int
    verdict: bool
    flagged: bool


def _learnings_uses(relative: str, text: str) -> list[_LearningsUse]:
    """Each printed `lint learnings`: its line, whether the words of a verdict sentence stand
    within `_VERDICT_NEAR` lines of it, and whether it carries `--list-entries`."""
    pattern = _VERDICT_USES.get(relative)
    asked = (
        [text.count("\n", 0, match.start()) + 1 for match in pattern.finditer(text)]
        if pattern is not None
        else []
    )
    uses: list[_LearningsUse] = []
    for element in _printed_elements(text):
        if not _MODULE.search(element.text):
            continue
        _, namespace, _ = _cli_namespace(element.text)
        # `target` belongs to `lint` alone: `new-pack` and `scaffold` have none to read.
        if (
            namespace is None
            or namespace.command != "lint"
            or namespace.target != "learnings"
        ):
            continue
        uses.append(
            _LearningsUse(
                element.line,
                any(abs(element.line - line) <= _VERDICT_NEAR for line in asked),
                bool(namespace.list_entries),
            )
        )
    return uses


def _learnings_problems(relative: str, text: str) -> list[str]:
    uses = _learnings_uses(relative, text)
    problems = [
        f"{relative}:{use.line}: asks for the lint verdict but passes --list-entries, which "
        "prints the inventory INSTEAD of linting"
        for use in uses
        if use.verdict and use.flagged
    ]
    problems += [
        f"{relative}:{use.line}: prints `lint learnings` with no --list-entries, so it gives "
        "a verdict and not the entry count, and no sentence beside it asks for the verdict"
        for use in uses
        if not use.verdict and not use.flagged
    ]
    pattern = _VERDICT_USES.get(relative)
    if pattern is not None:
        asked = len(pattern.findall(text))
        beside = sum(1 for use in uses if use.verdict)
        if asked != beside:
            problems.append(
                f"{relative}: {asked} sentence(s) ask for the verdict and {beside} printed "
                "`lint learnings` stand beside them"
            )
    return problems


def test_lint_learnings_carries_the_flag_where_a_count_is_wanted() -> None:
    problems: list[str] = []
    counts = 0
    verdicts = 0
    for relative in (*_markdown_surface(), *_asset_surface()):
        text = _read(relative)
        uses = _learnings_uses(relative, text)
        counts += sum(1 for use in uses if not use.verdict)
        verdicts += sum(1 for use in uses if use.verdict)
        problems += _learnings_problems(relative, text)
    assert not problems, "\n".join(problems)
    assert verdicts == len(_VERDICT_USES), (
        f"{verdicts} printed verdict uses were found and the table names {len(_VERDICT_USES)}"
    )
    assert counts > 3, (
        f"only {counts} printed entry-count commands were found, so the flag check would "
        "be close to vacuous"
    )


_VERDICT_FILE = "plugins/core/skills/task-learnings/SKILL.md"
_LEARNINGS = f'{_UV} lint learnings --project "<absolute project root>"'
_LEARNINGS_COUNT = (
    f'{_UV} lint learnings --list-entries --project "<absolute project root>"'
)


def test_the_lint_learnings_check_fails_on_each_use_it_guards() -> None:
    """Planted: a count without the flag, a verdict with it, and verdict words with no command."""
    count_without = (
        f"The same lint with `--list-entries` (`{_LEARNINGS}`) prints the count.\n"
    )
    assert len(_learnings_problems(_CORE, count_without)) == 1
    count_with = f"The same lint with `--list-entries` (`{_LEARNINGS_COUNT}`) prints the count.\n"
    assert _learnings_problems(_CORE, count_with) == []

    ask = "Then run, and read the verdict.\n\n"
    verdict_with = ask + _fence(_LEARNINGS_COUNT)
    assert len(_learnings_problems(_VERDICT_FILE, verdict_with)) == 1
    verdict_without = ask + _fence(_LEARNINGS)
    assert _learnings_problems(_VERDICT_FILE, verdict_without) == []

    far = ask + "\n" * 8 + count_with
    assert len(_learnings_problems(_VERDICT_FILE, far)) == 1, (
        "verdict words with no command beside them must be reported"
    )
    both = ask + _fence(_LEARNINGS) + "\n" + "\n" * 8 + count_with
    assert _learnings_problems(_VERDICT_FILE, both) == []
