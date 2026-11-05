"""CI's gates are named in the contributor documents, and no document counts them.

`.github/workflows/ci.yaml` is the authority on what CI runs. Five documents said "the
four checks" while CI ran more, because a count written in prose is checked by nothing:
the day a gate was added, every sentence that counted them became false and stayed that
way. Two properties prevent a repeat, and neither lists the gates by hand -- both are
derived from the workflow:

1. `AGENTS.md` and `CONTRIBUTING.md` each contain every gate command CI runs, as a
   substring, so a document keeps its own local form (`pytest -q --basetemp ...`) and
   still names the command CI runs.
2. None of the five documents states a count of the gates, so adding a gate cannot
   make a sentence false.

**What counts as a gate.** A step that runs a command and can fail the job, other than
environment setup. Two kinds of step run commands and are not gates, and each is
recognised by what it IS rather than by its name or position, so the rule survives a
rename or a reorder: a step marked `continue-on-error: true` cannot fail the job
whatever it prints, so it is a report; and `uv sync` prepares the environment the gates
run in and has no opinion about the change. A step that only `uses:` an action runs no
command, so it is neither. If a new setup command appears, this module fails by naming
it as a gate, which is the loud direction: extend `_is_dependency_sync`, or document it.

**Why a hand-written reader.** PyYAML is not a dev dependency and a test is no reason to
add one. `_read_steps` understands the one shape the workflow uses, single-line `run:`
values, and RAISES on anything else: a reader that cannot see a step must say so rather
than return a shorter list, because cannot-measure is never a pass.

**Scan surfaces.** Property 1 covers two documents and property 2 covers five, the two
included. That overlap is deliberate: they are two questions about the same file, and
neither judges a file by a rule that does not apply to it.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yaml"

# Must NAME every gate command.
_GATE_DOCUMENTS = ("AGENTS.md", "CONTRIBUTING.md")

# Must NOT count the gates.
_COUNT_DOCUMENTS = (
    *_GATE_DOCUMENTS,
    "docs/faq.md",
    "docs/working-on-the-kit.md",
    "docs/syncing-from-upstream.md",
)

# A floor on what the reader must see in the live workflow. A reader that finds fewer
# is blind, and a blind reader makes every check below pass over an empty list.
_GATE_FLOOR = 6

# The phrases the documents used to count the gates with. Matched case-insensitively, and
# across a line break, because prose wraps.
_COUNT_PHRASES = (
    "four CI gates",
    "the four checks",
    "These four are the gates",
    "all four",
    "Run all four",
)

_NUMBER_BEFORE_GATES = "a number before 'gates' or 'checks'"
_COUNT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    *(
        (
            phrase,
            re.compile(
                r"\b" + r"\s+".join(map(re.escape, phrase.split())) + r"\b",
                re.IGNORECASE,
            ),
        )
        for phrase in _COUNT_PHRASES
    ),
    # The listed phrases all say "four". Without this, replacing the word with the current
    # number would pass, and the sentence would be wrong again at the next gate.
    (
        _NUMBER_BEFORE_GATES,
        re.compile(
            r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)"
            r"\s+(?:CI\s+)?(?:gates|checks)\b",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class _Step:
    commands: tuple[str, ...]  # empty for a step that only `uses:` an action
    tolerates_failure: bool  # `continue-on-error: true`


_STEPS_KEY = re.compile(r"^(?P<indent> *)steps:[ \t]*(?:#.*)?$")
_KEY_VALUE = re.compile(r"^(?P<key>[A-Za-z_][\w-]*):(?:[ \t]+(?P<value>.*))?$")
_QUOTED = re.compile(r"""^(?P<quote>["'])(?P<body>.*?)(?P=quote)[ \t]*(?:#.*)?$""")
_TRAILING_COMMENT = re.compile(r"[ \t]+#.*$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_content(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _scalar(raw: str) -> str:
    """A YAML plain or quoted scalar, without its quotes or a trailing comment."""
    value = raw.strip()
    quoted = _QUOTED.match(value)
    if quoted is not None:
        return quoted["body"]
    return _TRAILING_COMMENT.sub("", value).strip()


def _parse_step(lines: list[str], dash_indent: int) -> _Step:
    key_indent = dash_indent + 2
    texts = [lines[0].lstrip()[2:]]
    texts += [line[key_indent:] for line in lines[1:] if _indent(line) == key_indent]
    pairs: dict[str, str] = {}
    for text in texts:
        pair = _KEY_VALUE.match(text)
        if pair is None:
            raise ValueError(f"cannot read the workflow step line {text!r}")
        raw = pair["value"] or ""
        if pair["key"] == "run" and (not raw.strip() or raw.strip()[0] in "|>"):
            raise ValueError(
                "a multi-line or empty `run:`; extend _read_steps() or keep the "
                "command on one line"
            )
        pairs[pair["key"]] = _scalar(raw)
    tolerant = pairs.get("continue-on-error", "false").lower()
    if tolerant not in ("true", "false"):
        raise ValueError(
            f"`continue-on-error: {tolerant}` is not a literal true or false, so this "
            "reader cannot tell whether the step can fail the job"
        )
    run = pairs.get("run")
    return _Step(commands=(run,) if run else (), tolerates_failure=tolerant == "true")


def _parse_block(block: list[str]) -> list[_Step]:
    if not block:
        return []
    dash_indent = _indent(block[0])
    items: list[list[str]] = []
    for line in block:
        if _indent(line) == dash_indent and line.lstrip().startswith("- "):
            items.append([line])
        elif items and _indent(line) > dash_indent:
            items[-1].append(line)
        else:
            raise ValueError(f"cannot read the workflow line {line!r}")
    return [_parse_step(item, dash_indent) for item in items]


def _read_steps(workflow: str) -> list[_Step]:
    """Every step of every `steps:` block, in file order."""
    lines = workflow.splitlines()
    steps: list[_Step] = []
    at = 0
    while at < len(lines):
        header = _STEPS_KEY.match(lines[at])
        at += 1
        if header is None:
            continue
        base = len(header["indent"])
        block: list[str] = []
        while at < len(lines):
            line = lines[at]
            if _is_content(line):
                indent = _indent(line)
                if indent < base or (
                    indent == base and not line.lstrip().startswith("- ")
                ):
                    break
                block.append(line)
            at += 1
        steps += _parse_block(block)
    return steps


def _is_dependency_sync(command: str) -> bool:
    # Environment setup is recognised by the command itself, never by a step's name or
    # position; see "What counts as a gate" in the module docstring.
    return command.split()[:2] == ["uv", "sync"]


def _gate_commands(steps: Sequence[_Step]) -> list[str]:
    """What CI runs that can fail the job and judges the change; see the docstring above."""
    return [
        command
        for step in steps
        if not step.tolerates_failure
        for command in step.commands
        if not _is_dependency_sync(command)
    ]


def _missing_gate_commands(document: str, gates: Sequence[str]) -> list[str]:
    return [gate for gate in gates if gate not in document]


def _count_statements(text: str) -> list[tuple[int, str]]:
    """Every place `text` counts the gates, as (line number, what matched)."""
    return sorted(
        (text.count("\n", 0, match.start()) + 1, label)
        for label, pattern in _COUNT_PATTERNS
        for match in pattern.finditer(text)
    )


def _live_gates() -> list[str]:
    return _gate_commands(_read_steps(_WORKFLOW.read_text(encoding="utf-8")))


# The text this module replaced, one excerpt per phrase, copied from the documents as they
# stood before it: the known-positives that show each phrase can fire at all.
_TODAYS_TEXT: tuple[tuple[str, str], ...] = (
    (
        "four CI gates",
        "Run from the repository root. The four CI gates are `ruff check`, `ruff format\n"
        "--check`, `basedpyright` and `pytest`; all four must be green.",
    ),
    ("the four checks", "#### The four checks"),
    (
        "These four are the gates",
        "These four are the gates: CI runs exactly them, in this order, on every pull request,",
    ),
    (
        "all four",
        "the session.** All four import the package, and each import writes `__pycache__/*.pyc`",
    ),
    (
        "Run all four",
        "**Run all four, not just `pytest`.** They are separate CI steps, so a green suite says",
    ),
)

_PLANTED_WORKFLOW = """\
name: Planted
on:
  pull_request:
jobs:
  first:
    steps:
      # steps: a comment that mentions the key must not open a block
      - uses: actions/checkout@abc # pinned

      - name: Sync
        run: uv sync --dev
      - name: Alpha
        run: uv run alpha check .   # a trailing comment is not part of the command
      - name: Beta
        run: "uv run beta"
      - name: Report
        continue-on-error: true
        run: uv run gamma report
  second:
    steps:
    - name: Delta
      run: uv run delta --flag
"""

_PLANTED_GATES = ["uv run alpha check .", "uv run beta", "uv run delta --flag"]


def test_the_reader_keeps_the_gates_and_drops_setup_and_reports() -> None:
    """Fire the reader at a known-positive: it must drop what is not a gate, and no more."""
    steps = _read_steps(_PLANTED_WORKFLOW)
    assert _gate_commands(steps) == _PLANTED_GATES
    assert [step.tolerates_failure for step in steps].count(True) == 1
    assert [step.commands for step in steps].count(()) == 1


@pytest.mark.parametrize(
    ("workflow", "reason"),
    [
        (
            "jobs:\n  j:\n    steps:\n      - run: |\n          one\n          two\n",
            "multi-line",
        ),
        (
            "jobs:\n  j:\n    steps:\n      - run: x\n        continue-on-error: ${{ y }}\n",
            "literal true or false",
        ),
        ("jobs:\n  j:\n    steps:\n      - {run: x}\n", "cannot read"),
    ],
    ids=["block-scalar", "expression-flag", "flow-mapping"],
)
def test_a_shape_the_reader_cannot_read_fails_loudly(
    workflow: str, reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        _read_steps(workflow)


def test_the_reader_sees_the_floor_of_gates_in_the_live_workflow() -> None:
    steps = _read_steps(_WORKFLOW.read_text(encoding="utf-8"))
    gates = _gate_commands(steps)
    assert len(gates) >= _GATE_FLOOR, (
        f"read {len(steps)} steps and {len(gates)} gate(s) from {_WORKFLOW}, expected "
        f"at least {_GATE_FLOOR}: {gates}"
    )


@pytest.mark.parametrize("document", _GATE_DOCUMENTS)
def test_the_document_names_every_gate_command(document: str) -> None:
    text = (_REPO_ROOT / document).read_text(encoding="utf-8")
    missing = _missing_gate_commands(text, _live_gates())
    assert not missing, (
        f"{document} does not contain the command CI runs for: {missing}. Add each "
        f"one to the document's list of gates; {_WORKFLOW.name} is the authority"
    )


def test_a_document_missing_one_gate_command_is_caught() -> None:
    complete = "\n".join(_PLANTED_GATES)
    assert _missing_gate_commands(complete, _PLANTED_GATES) == []
    for gate in _PLANTED_GATES:
        assert _missing_gate_commands(complete.replace(gate, ""), _PLANTED_GATES) == [
            gate
        ]


def test_the_scan_surface_is_the_five_named_documents() -> None:
    assert len(_COUNT_DOCUMENTS) == len(set(_COUNT_DOCUMENTS)) == 5
    assert set(_GATE_DOCUMENTS) <= set(_COUNT_DOCUMENTS)


@pytest.mark.parametrize("document", _COUNT_DOCUMENTS)
def test_no_document_states_a_count_of_the_gates(document: str) -> None:
    text = (_REPO_ROOT / document).read_text(encoding="utf-8")
    assert text.strip(), f"{document} is empty, so scanning it proves nothing"
    statements = _count_statements(text)
    assert not statements, (
        f"{document} counts the CI gates at (line, match): {statements}. Name the "
        "gates and the command CI runs for each; a count goes false the day one is added"
    )


def test_the_detector_fires_on_the_text_this_module_replaced() -> None:
    for phrase, excerpt in _TODAYS_TEXT:
        labels = {label for _, label in _count_statements(excerpt)}
        assert phrase in labels, f"{phrase!r} did not fire on {excerpt!r}"
    assert {phrase for phrase, _ in _TODAYS_TEXT} == set(_COUNT_PHRASES), (
        "every phrase the detector bans needs a known-positive; one has none"
    )


def test_the_detector_ignores_case_and_line_breaks_and_catches_new_counts() -> None:
    assert _count_statements("RUN ALL\nFOUR, then stop") != []
    for rewritten in ("CI runs six gates", "Run the 5 checks", "the Seven CI Checks"):
        labels = {label for _, label in _count_statements(rewritten)}
        assert _NUMBER_BEFORE_GATES in labels, rewritten


def test_the_detector_leaves_a_clean_paragraph_alone() -> None:
    clean = (
        "CI runs these gates, in this order, on every pull request. Run every gate, not "
        "just `pytest`: they are separate CI steps. A third check lives elsewhere, and "
        "all fourteen skills pass it."
    )
    assert _count_statements(clean) == []
