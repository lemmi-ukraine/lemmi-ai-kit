"""Six short lessons are written down in references their skills already link, and pinned here.

Each lesson cost a page something: a suite credited with a branch it never ran, a commit message
carrying figures from an earlier run, a surviving mutant that was equivalent, a lint that printed
PASSED over zero files, a command counter that counted the investigation's own probes, and a join
whose zero said nothing about the rows it was meant to exonerate. They are references only: no
SKILL.md gains a line, and each reference is reached through a link its SKILL.md already has.

THE SURFACE, in numbers the tests assert: 11 claims and 25 phrases over three references. A claim
holds when every one of its phrases is in its reference (lower-cased, whitespace collapsed). Each
phrase is fired at a planted removal, so a phrase the check could not see go is not in the table.
One claim is about the kit's own behaviour (the lint passes over zero files), so it is measured by
running the lint as well as quoted, with a control that shows the summary line counts files.
"""

import re
from pathlib import Path

import pytest

from lemmi_ai_kit.cli import main

_SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "core" / "skills"

_CLAIM_BOUNDARIES = "post-task-review/references/claim-boundaries.md"
_JOIN_DIAGNOSTICS = "metric-validity-check/references/join-diagnostics.md"
_ANALYSIS_EXAMPLES = "analyze-logs/references/analysis-examples.md"

# (claim, reference under plugins/core/skills, the phrases that must all be present;
# lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "a: a suite stands in for a file only after the switches its tests pass are grepped",
        _CLAIM_BOUNDARIES,
        (
            "grepped which switches its tests pass",
            "the branch behind the other values was never run",
        ),
    ),
    (
        "b: a drafted commit message is compared with the final log before the commit",
        _CLAIM_BOUNDARIES,
        (
            "copies figures from the run that existed when it was written",
            "compare every figure in the draft with the final log",
        ),
    ),
    (
        "c: a surviving mutant may be equivalent, so it is traced before a test is added",
        _CLAIM_BOUNDARIES,
        (
            "a mutant that survives may be equivalent",
            "trace why it survived before adding a test",
        ),
    ),
    (
        "c: a mutation runner has an unmutated control, an old-wording control, and a needle count",
        _CLAIM_BOUNDARIES,
        (
            "an unmutated control",
            "an old-wording control",
            "proves only that the needle occurs once",
        ),
    ),
    (
        "j: a lint's pass is its summary line, not the word PASSED",
        _CLAIM_BOUNDARIES,
        (
            "a lint's pass is its summary line, not the word passed",
            "n finding(s), m file(s)",
        ),
    ),
    (
        "j: the lint prints PASSED over zero files, so a pass is 0 findings and the file count meant",
        _CLAIM_BOUNDARIES,
        (
            "it prints passed over zero files",
            "0 findings and m equal to the number of files you meant to lint",
        ),
    ),
    (
        "e: a counter over recorded commands counts the investigator's own probes",
        _JOIN_DIAGNOSTICS,
        (
            "the counter counts the investigator's own probes",
            "before the investigating session's own probes",
        ),
    ),
    (
        "e: a zero is probed with a fixture pair built from real output and one planted row",
        _JOIN_DIAGNOSTICS,
        (
            "a zero is not a finding until the probe has seen something",
            "a fixture pair built from real output",
            "a single planted matching row",
        ),
    ),
    (
        "e: a fixed-string grep with both quote kinds can return a silent 0",
        _JOIN_DIAGNOSTICS,
        ("can return a silent 0", "a script file"),
    ),
    (
        "e: a bare pipe character in a command a probe runs through a shell is a pipe",
        _JOIN_DIAGNOSTICS,
        ("a bare `|` is a pipe",),
    ),
    (
        "f: a join-based absence needs the overall match count beside the zero",
        _ANALYSIS_EXAMPLES,
        (
            "### example 4: an absence found by a join",
            "a zero with no denominator",
            "the overall match count beside the zero",
            "says nothing about the application",
        ),
    ),
)

_SUMMARY = re.compile(r"^--- handoffs: (\d+) finding\(s\), (\d+) file\(s\) ---$")


def _words(reference: str) -> str:
    return " ".join((_SKILLS / reference).read_text(encoding="utf-8").split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _summary(lines: list[str]) -> tuple[str, ...]:
    """The two numbers of the one summary line, wherever it falls among the finding lines."""
    found = [match for line in lines if (match := _SUMMARY.match(line))]
    assert len(found) == 1, lines
    return found[0].groups()


def test_the_surface_is_stated_in_numbers() -> None:
    references = {reference for _, reference, _ in _ROWS}
    phrases = [phrase for _, _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(references), len(phrases)) == (11, 3, 25)
    unreadable = [name for name in sorted(references) if not (_SKILLS / name).is_file()]
    assert not unreadable, (
        f"{len(unreadable)} of {len(references)} references: {unreadable}"
    )


@pytest.mark.parametrize(
    ("claim", "reference", "phrases"), _ROWS, ids=[row[0] for row in _ROWS]
)
def test_the_reference_states_the_claim(
    claim: str, reference: str, phrases: tuple[str, ...]
) -> None:
    missing = _missing(_words(reference), phrases)
    assert not missing, f"{reference} does not state {claim!r}: missing {missing}"


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real text in turn is the one gap reported,
    and an empty text lacks every phrase of a row. A phrase the check cannot see go would let
    a reference lose its claim and stay green."""
    for claim, reference, phrases in _ROWS:
        text = _words(reference)
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


@pytest.mark.parametrize("reference", sorted({row[1] for row in _ROWS}))
def test_the_skill_already_links_the_reference(reference: str) -> None:
    """A reference no SKILL.md links is not read; the links exist, so no SKILL.md grows."""
    skill, _, relative = reference.partition("/")
    linked = (_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    assert relative in linked, f"{skill}/SKILL.md does not link {relative}"


def _lint_handoffs(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, list[str]]:
    code = main(["lint", "handoffs", "--project", str(project)])
    return code, capsys.readouterr().out.splitlines()


def test_the_lint_passes_over_zero_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The reference says the hand-off lint prints PASSED over zero files; this is that, measured."""
    code, lines = _lint_handoffs(tmp_path, capsys)
    assert code == 0, lines
    assert _summary(lines) == ("0", "0"), lines
    assert lines[-1].startswith("LINT PASSED"), lines


def test_the_summary_line_counts_the_files_it_linted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Control for the test above: with one note in the folder M is 1 whatever the findings
    are, so M is the number the reference tells the reader to compare with the files meant."""
    folder = tmp_path / ".ai" / "handoffs"
    folder.mkdir(parents=True)
    (folder / "2026-01-01-example-return.md").write_text(
        "# a note that holds no contract line\n", encoding="utf-8"
    )
    _, lines = _lint_handoffs(tmp_path, capsys)
    assert _summary(lines)[1] == "1", lines
