"""The hand-off lint reads a version label on line 1 and asks a v2 note for two more sections.

The label is `<!-- handoff-contract: vN -->`. A note with no label, or with `v1`, is held to the
five sections the lint has always required, and a folder run never skips a file. `v2` also
requires a non-empty `## Continue` and `## Orchestrator summary`. Three label defects are
findings of their own: a version the lint does not know, a line 1 that is shaped like the label
but does not parse, and an exact label below line 1 (which would otherwise be ignored in
silence). The last two are findings only when the label names v2 or a later version: a marker of
the older kind, naming v1 or no version, stays quiet wherever it sits and however it is spelled,
so a note that passed before the label existed still passes.

WHAT KEEPS IT HONEST. Each rule has a planted positive and a near miss that must stay quiet: a
fenced quote of the label below line 1, a title that merely mentions the contract, a note with no
label, and one synthetic note for each of the five classes of marker (v2 misplaced, v2 mistyped,
v1 misplaced, v1 mistyped, a label-shaped line that names no version). Three tests are green on
the lint as it stood before the label existed (a note with no label, a v1 note and a full v2 note
all pass): they are guards, and they are what "an older note still passes" means. The fixtures
are literal text, and `test_the_contract_versions_are_one_table_in_checks` ties their section
names to the table in checks.py, so a fixture cannot drift from the constants it stands for.

Classes of label shape covered: spacing inside the comment, the case of the `v`, text after the
comment, a missing colon, other separators between the words (hyphens, an underscore), the case of
the words, an indent, a leading zero, a version of two digits (10 is later than 2), a version of
thousands of digits, a `v` that is part of another word, and an exact label on a later line, with
trailing blanks or a blank line after it, inside and outside a fence. Any further shape is a line
in the change record, not another case here.
"""

import codecs
import re
from pathlib import Path

import pytest

from lemmi_ai_kit import checks
from lemmi_ai_kit.cli import main

_FIVE = """# Hand-off

## Scope
The one slice. Not the rest.

## Durable anchors
- branch `feature/thing`

## Preconditions
- `git status --short` -> clean tree

## Verification
- `pytest -q` -> 0 failed

## Status
in-progress. The second half is not done.
"""

_V2_TAIL = """
## Continue
Paste into a new session: `Read the note and follow it.`
Next step: one sentence.

## Orchestrator summary
Done: one thing. Open: one thing.
"""

_EXTRAS = ("Continue", "Orchestrator summary")


def _label(version: object) -> str:
    return f"<!-- handoff-contract: v{version} -->"


# More digits than the 4300 that `int()` converts from text by default.
_LONG = "9" * 5000
_UNMARKED = _FIVE
_V1 = _label(1) + "\n" + _FIVE
_V2 = _label(2) + "\n" + _FIVE + _V2_TAIL


def _on_line_three(marker: str) -> str:
    """A five-section note whose title is followed by `marker` on line 3, below line 1."""
    return "# Hand-off\n\n" + marker + "\n" + _FIVE.split("\n", 1)[1]


def _without(text: str, name: str) -> str:
    """The text with one `## name` section removed, heading and body."""
    pattern = re.compile(
        rf"^## {re.escape(name)}\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
    )
    out, hits = pattern.subn("", text)
    assert hits == 1, f"the fixture has no single '## {name}' section"
    return out


def _emptied(text: str, name: str, body: str = "") -> str:
    """The text with one section's heading kept and its body replaced."""
    pattern = re.compile(
        rf"^(## {re.escape(name)}\n).*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
    )
    out, hits = pattern.subn(lambda m: m.group(1) + body + "\n", text)
    assert hits == 1, f"the fixture has no single '## {name}' section"
    return out


def _findings(text: str) -> list[checks.LintFinding]:
    return checks.lint_handoff(text, "h.md")


def _messages(text: str) -> list[str]:
    return [finding.message for finding in _findings(text)]


def _write(path: Path, text: str, *, bom: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((codecs.BOM_UTF8 if bom else b"") + text.encode("utf-8"))
    return path


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".ai").mkdir(exist_ok=True)
    return tmp_path


# --- the table the fixtures stand for -------------------------------------------------------


def test_the_contract_versions_are_one_table_in_checks() -> None:
    table = getattr(checks, "HANDOFF_SECTIONS_BY_VERSION", None)
    assert table is not None, "checks.py has no table of hand-off contract versions"

    assert table.get(1) == (), "version 1 is the five sections and nothing more"
    assert table.get(2) == _EXTRAS, "the fixtures' two sections are the table's"
    for version, extras in table.items():
        assert not set(extras) & set(checks.HANDOFF_REQUIRED_SECTIONS), (
            f"v{version} repeats one of the five sections"
        )


# --- a note with no label, or v1, still passes (green before the label existed; guards) ---------


def test_a_note_with_no_label_is_held_to_the_five_sections_and_passes() -> None:
    assert _findings(_UNMARKED) == []


def test_a_v1_label_is_the_five_sections_and_passes() -> None:
    assert _findings(_V1) == []


def test_a_full_v2_note_passes() -> None:
    assert _findings(_V2) == []


# --- what v2 asks for -------------------------------------------------------------------------


@pytest.mark.parametrize("name", _EXTRAS)
def test_a_v2_note_without_a_section_is_reported_by_that_section(name: str) -> None:
    messages = _messages(_without(_V2, name))

    assert [
        m for m in messages if m.startswith(f"missing required section '## {name}'")
    ]
    assert len(messages) == 1, f"only the missing section is wrong with it: {messages}"


@pytest.mark.parametrize("name", _EXTRAS)
def test_a_v2_section_with_a_heading_and_no_body_is_reported(name: str) -> None:
    assert _messages(_emptied(_V2, name)) == [f"'## {name}' has no content"]


@pytest.mark.parametrize("name", _EXTRAS)
def test_a_v2_section_holding_only_a_comment_has_no_content(name: str) -> None:
    text = _emptied(_V2, name, body="<!-- fill this in later -->")

    assert _messages(text) == [f"'## {name}' has no content"]


# --- the label itself ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["4", "0", "10"])
def test_an_unknown_version_is_a_finding_and_the_note_is_checked_as_v1(
    version: str,
) -> None:
    messages = _messages(_label(version) + "\n" + _FIVE)

    assert len(messages) == 1, f"checked as v1 the five sections are enough: {messages}"
    assert f"unknown hand-off contract version 'v{version}'" in messages[0]


def test_a_version_of_thousands_of_digits_is_unknown_and_not_printed_in_full() -> None:
    messages = _messages(_label(_LONG) + "\n" + _FIVE)

    assert len(messages) == 1, f"checked as v1 the five sections are enough: {messages}"
    assert "unknown hand-off contract version" in messages[0]
    assert "9" * 100 not in messages[0], "the whole version was printed"
    assert len(messages[0]) < 200


def test_a_version_of_thousands_of_digits_is_a_finding_at_the_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)
    where = ".ai/handoffs/2026-01-01-long-version.md"
    _write(root / where, _label(_LONG) + "\n" + _FIVE)

    assert main(["lint", "handoffs", where, "--project", str(root)]) == 1
    printed = capsys.readouterr().out
    assert "unknown hand-off contract version" in printed
    assert "9" * 100 not in printed


# --- a marker is judged by the version it names ------------------------------------------------
#
# A marker that is misplaced or mistyped is a finding only when it names v2 or a later version.
# One that names v1 (or lower), or no version at all, is the older kind some projects wrote of
# their own before the label existed: it asks for nothing the five sections do not, so it stays
# quiet wherever it sits and however it is spelled. First, one synthetic note per class.

_CLASSES = (
    pytest.param(_on_line_three(_label(2)), "below line 1", id="v2-misplaced"),
    pytest.param(
        "<!-- handoff-contract: V2 -->\n" + _FIVE, "does not parse", id="v2-mistyped"
    ),
    pytest.param(_on_line_three(_label(1)), None, id="v1-misplaced"),
    pytest.param("<!-- handoff-contract: V1 -->\n" + _FIVE, None, id="v1-mistyped"),
    pytest.param(
        "<!-- hand-off contract notes -->\n" + _FIVE, None, id="names-no-version"
    ),
)


@pytest.mark.parametrize(("text", "finding"), _CLASSES)
def test_a_marker_is_a_finding_only_when_it_names_v2_or_a_later_version(
    text: str, finding: str | None
) -> None:
    messages = _messages(text)

    if finding is None:
        assert messages == []
    else:
        assert len(messages) == 1, f"checked as v1 the five are enough: {messages}"
        assert finding in messages[0]


_MISTYPED_V2_OR_LATER = (
    "<!--handoff-contract: v 2-->",
    "<!-- handoff-contract: V2 -->",
    "<!-- handoff-contract: v2 --> note",
    "<!-- handoff-contract v2 -->",
    "<!-- hand-off-contract: v2 -->",
    " <!-- handoff-contract: v2 -->",
    "<!-- handoff-contract: v02 -->",
    "<!-- HANDOFF-CONTRACT: v2 -->",
    "<!-- hand_off_contract: v2 -->",
    "<!-- handoff-contract: V10 -->",
)


@pytest.mark.parametrize("line_one", _MISTYPED_V2_OR_LATER)
def test_a_mistyped_line_one_label_that_names_v2_or_later_is_a_finding(
    line_one: str,
) -> None:
    messages = _messages(line_one + "\n" + _FIVE)

    assert len(messages) == 1, f"checked as v1 the five sections are enough: {messages}"
    assert "does not parse" in messages[0]


_QUIET_LABELS = (
    "<!-- handoff-contract: v1 --> generated",
    "<!-- handoff-contract: V1 -->",
    "<!--handoff-contract:v1-->",
    "<!-- hand-off-contract: v1 -->",
    "<!-- HAND_OFF_CONTRACT: v1 -->",
    "<!-- handoff-contract: v01 -->",
    "<!-- handoff-contract v0 -->",
    "<!-- handoff-contract -->",
    "<!-- handoff-contract: see the safety skill -->",
    "<!-- handoff-contract: rev2 -->",
)


@pytest.mark.parametrize("line_one", _QUIET_LABELS)
def test_a_mistyped_line_one_label_that_names_v1_or_no_version_is_not_a_finding(
    line_one: str,
) -> None:
    assert _findings(line_one + "\n" + _FIVE) == []


@pytest.mark.parametrize("version", ["2", "3", "10", "99"])
def test_an_exact_label_below_line_one_that_names_v2_or_later_is_a_finding_at_its_line(
    version: str,
) -> None:
    text = _on_line_three(_label(version))
    at = text.splitlines().index(_label(version)) + 1

    found = _findings(text)

    assert [(f.line, "below line 1" in f.message) for f in found] == [(at, True)]
    assert at > 1


@pytest.mark.parametrize("version", ["1", "0"])
def test_an_exact_label_below_line_one_that_names_v1_or_lower_is_not_a_finding(
    version: str,
) -> None:
    assert _findings(_on_line_three(_label(version))) == []


@pytest.mark.parametrize(
    "after", ["  ", "\t", "\n"], ids=["spaces", "tab", "blank-line"]
)
def test_a_label_below_line_one_followed_by_a_blank_is_still_found(after: str) -> None:
    found = _findings(_on_line_three(_label(2) + after))

    assert [(f.line, "below line 1" in f.message) for f in found] == [(3, True)]


@pytest.mark.parametrize(
    ("text", "finding"),
    [
        pytest.param(_on_line_three(_label(_LONG)), "below line 1", id="misplaced"),
        pytest.param(
            _label(_LONG) + " note\n" + _FIVE, "does not parse", id="mistyped"
        ),
    ],
)
def test_a_label_of_thousands_of_digits_is_found_by_its_place_without_a_crash(
    text: str, finding: str
) -> None:
    messages = _messages(text)

    assert len(messages) == 1, f"checked as v1 the five sections are enough: {messages}"
    assert finding in messages[0]
    assert "9" * 100 not in messages[0]


def test_a_fenced_quote_of_the_label_below_line_one_is_not_a_finding() -> None:
    quoted = _FIVE.replace(
        "The one slice. Not the rest.",
        "The one slice. Not the rest.\n\n```\n" + _label(2) + "\n```",
    )
    assert quoted != _FIVE

    assert _findings(quoted) == []


def test_a_title_that_only_mentions_the_contract_is_not_shaped_like_the_label() -> None:
    titled = _FIVE.replace("# Hand-off", "# Hand-off contract notes", 1)
    commented = (
        "<!-- the hand-off follows the contract in the safety skill -->\n" + _FIVE
    )

    assert _findings(titled) == []
    assert _findings(commented) == []


def test_trailing_blanks_and_crlf_line_endings_do_not_hide_the_label() -> None:
    padded = _V2.replace("-->\n", "-->  \n", 1)
    assert padded != _V2

    for variant in (padded, _V2.replace("\n", "\r\n")):
        assert _findings(variant) == []
    # Read as v2, not skipped: each still asks for the section it lacks.
    for lacking in (
        _without(padded, "Continue"),
        _without(_V2, "Continue").replace("\n", "\r\n"),
    ):
        assert _messages(lacking), (
            "the label was not read, so the note was checked as v1"
        )


# --- reading files ----------------------------------------------------------------------------


def test_a_byte_order_mark_does_not_hide_the_label(tmp_path: Path) -> None:
    root = _project(tmp_path)
    folder = root / ".ai" / "handoffs"
    bad = _write(folder / "bad.md", _without(_V2, "Continue"), bom=True)
    good = _write(folder / "good.md", _V2, bom=True)
    assert bad.read_bytes().startswith(codecs.BOM_UTF8)

    messages = [f.message for f in checks.lint_handoff_file(bad, root)]

    assert [
        m for m in messages if m.startswith("missing required section '## Continue'")
    ]
    assert checks.lint_handoff_file(good, root) == []
    # A caller that hands the lint raw text with the mark still in place is read the same way.
    raw = chr(0xFEFF) + _without(_V2, "Continue")
    assert [
        m
        for m in _messages(raw)
        if m.startswith("missing required section '## Continue'")
    ]


def test_a_folder_run_reads_each_note_at_its_own_version(tmp_path: Path) -> None:
    root = _project(tmp_path)
    notes = {
        "unmarked": _UNMARKED,
        "v1": _V1,
        "v2": _V2,
        "v2-lacking-continue": _without(_V2, "Continue"),
    }
    for name, text in notes.items():
        _write(root / ".ai" / "handoffs" / f"2026-01-01-{name}.md", text)

    findings, scanned = checks.lint_handoff_dir(root)

    assert scanned == len(notes), "a note with no label was skipped"
    assert {f.where for f in findings} == {
        ".ai/handoffs/2026-01-01-v2-lacking-continue.md"
    }
    assert len(findings) == 1


def test_the_named_file_run_prints_the_lines_the_folder_run_prints_for_a_v2_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)
    where = ".ai/handoffs/2026-01-01-lacking-summary.md"
    _write(root / where, _without(_V2, "Orchestrator summary"))
    _write(root / ".ai" / "handoffs" / "2026-01-01-fine.md", _V2)

    assert main(["lint", "handoffs", "--project", str(root)]) == 1
    folder = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(where + ":")
    ]
    assert main(["lint", "handoffs", where, "--project", str(root)]) == 1
    named = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(where + ":")
    ]

    assert folder, "the folder run printed nothing for the v2 note"
    assert named == folder
