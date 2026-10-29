"""The `lint` and `audit-skills` subcommands: behaviour, exit codes, and portability.

Both subcommands are a **published API** the moment a skill or a CI job scripts against
them, so this file pins three things deliberately, not incidentally:

**The flag and exit-code surface.** Removing or renaming any of it later is a breaking
change with no telemetry to size the impact, so the tests name the contract explicitly:
`lint` exits 0 clean / 1 on findings / 2 on misuse, `audit-skills` exits 0 unless
`--fail-on` says otherwise.

**Cross-platform behaviour.** The originals only ever ran on one platform. A BOM, CRLF
line endings, a case-insensitive filesystem and a legacy code-page console are all
first-class cases here, because they are what an adopter on a different machine actually
hits.

**The vocabularies, against the skills that teach them.** A taxonomy documented in a
SKILL.md and re-typed into Python is two copies of one fact. The pinning tests below fail
in both directions, which is the whole point: a refresh that adds a category the lint
rejects would otherwise turn every conforming entry into a false positive.
"""

import re
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import NoReturn

import pytest
from upstream_sync import (
    ENV_VAR,
    SyncRecordError,
    UpstreamUnavailable,
    load_sync_record,
    read_upstream_file,
    resolve_upstream,
)

from lemmi_ai_kit import checks
from lemmi_ai_kit.cli import (
    _build_parser,  # pyright: ignore[reportPrivateUsage]
    main,
)
from lemmi_ai_kit.manifest import assets_root, shipped_skill_dirs

# --- fixtures -----------------------------------------------------------------------------

# A machine-specific path, assembled at runtime so this file never contains the literal it
# needs as a fixture. The publication hygiene contract bans the shape in every tracked file,
# and a test fixture is not an exception worth carving out.
_SEP = "\\"
_DRIVE_PATH = "C:" + _SEP + "Users" + _SEP + "someone" + _SEP + "scratch.md"
_POSIX_HOME = "/" + "Users" + "/someone/scratch.md"

_GOOD_CHANGELOG = """# AI Infrastructure Changelog

---

## 2026-08-22

### SKILL-ADDED: a real entry
- **What:** added a thing
- **Why:** it was needed
- **Files:** `a.md`
- **Affected workflows:** none
"""

_GOOD_LEARNINGS = """# Project Learnings

---

## Common Pitfalls

### [2026-08-22] A thing that bites
- **Context**: doing the task
- **Finding**: it bites
- **Impact**: do not do that
- **Category**: pitfall
"""

_GOOD_HYPOTHESES = """# AI Infrastructure Improvement Hypotheses

---

## 2026-08-22

### [SKILL-ADDED] a real entry
- **Category:** Quality
- **Hypothesis:** By doing X, we expect Y because Z.
- **Signal:** fewer findings next month
- **Status:** PENDING
- **Changelog ref:** 2026-08-22 - SKILL-ADDED: a real entry
"""

_GOOD_HANDOFF = """# Hand-off

## Scope
The one slice. Not the rest.

## Durable anchors
- branch `feature/thing`
- charter `tasks/TECH-thing.md`

## Preconditions
- `git status --short` -> clean tree

## Verification
- `pytest -q` -> 0 failed

## Status
in-progress. The second half is not done.
"""

# Placeholders in both command sections, a bullet that wraps (its arrow is on the second
# line), and one bullet with no command at all -- the listing has to cope with each.
_COMMANDS_HANDOFF = """# Hand-off

## Scope
The one slice. Not the rest.

## Durable anchors
- branch `feature/thing`

## Preconditions
- `git status --short` -> clean tree
- `git ls-tree <TREE>` against the tree the build
  printed -> lists d/

## Verification
- `pytest -q` -> 0 failed
- `git diff <LOWER>..<UPPER>` -> empty
- the diff reads well

## Status
in-progress. The second half is not done.
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _project(tmp_path: Path, **files: str) -> Path:
    """A project root whose `.ai/` holds the named data files (`changelog=...`)."""
    names = {
        "learnings": "learnings.md",
        "changelog": "ai-changelog.md",
        "hypotheses": "improvement-hypotheses.md",
    }
    for key, text in files.items():
        _write(tmp_path / ".ai" / names[key], text)
    (tmp_path / ".ai").mkdir(exist_ok=True)
    return tmp_path


_EM = "—"
_TERMINAL_CYCLE = ("CONFIRMED", "REFUTED", "INCONCLUSIVE", "SUPERSEDED")


def _ledger(
    terminal: int = 0,
    pending: int = 0,
    marker: str | None = None,
    header_extra: str = "",
) -> str:
    """A conforming hypotheses ledger: `terminal` resolved entries, `pending` open ones.

    The resolved entries cycle through all four terminal statuses, so one fixture also
    shows that every terminal status counts.
    """
    head = "# AI Infrastructure Improvement Hypotheses\n\n"
    if marker is not None:
        head += marker + "\n\n"
    head += header_extra
    head += "---\n\n## 2026-08-22\n\n"
    statuses = [_TERMINAL_CYCLE[i % len(_TERMINAL_CYCLE)] for i in range(terminal)]
    statuses += ["PENDING"] * pending
    entries = [
        f"### [SKILL-ADDED] entry {index}\n"
        "- **Category:** Quality\n"
        "- **Hypothesis:** By doing X, we expect Y because Z.\n"
        "- **Signal:** fewer findings next month\n"
        f"- **Status:** {status}\n"
        f"- **Changelog ref:** 2026-08-22 - SKILL-ADDED: entry {index}\n"
        for index, status in enumerate(statuses)
    ]
    return head + "\n".join(entries)


def _git(repo: Path, *args: str) -> str:
    """Run git in a fixture repository and return its stdout; fail loudly if it fails."""
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, f"git {args}: {done.stderr}"
    return done.stdout.strip()


def _git_repo(path: Path) -> Path:
    """`path` as an initialised repository with a local identity, so commits are hermetic."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "fixture")
    _git(path, "config", "user.email", "fixture@example.invalid")
    return path


def _skill(
    skills_dir: Path,
    name: str,
    *,
    frontmatter: str | None = None,
    body: str = "# Body\n",
    filename: str = "SKILL.md",
) -> Path:
    """One skill directory. `frontmatter=None` writes a valid minimal block."""
    block = (
        frontmatter
        if frontmatter is not None
        else f"---\nname: {name}\ndescription: Does a thing.\nmetadata:\n  type: task\n---\n"
    )
    _write(skills_dir / name / filename, block + "\n" + body)
    return skills_dir / name


def _severities(findings: list[checks.AuditFinding]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for finding in findings:
        out.setdefault(finding.severity, []).append(
            f"{finding.skill}: {finding.message}"
        )
    return out


# --- shared helpers: portability ----------------------------------------------------------


def test_project_root_prefers_the_ai_directory_over_the_checkout(
    tmp_path: Path,
) -> None:
    """In a monorepo the checkout root can sit above the project owning the pipeline."""
    (tmp_path / ".git").mkdir()
    inner = tmp_path / "packages" / "thing"
    (inner / ".ai").mkdir(parents=True)
    deep = inner / "src" / "nested"
    deep.mkdir(parents=True)

    assert checks.find_project_root(deep) == inner.resolve()


def test_project_root_falls_back_to_the_starting_directory(tmp_path: Path) -> None:
    """No marker anywhere is not an error: a plugin install has no ancestor in the project."""
    bare = tmp_path / "nowhere"
    bare.mkdir()
    assert checks.find_project_root(bare) == bare.resolve()


def test_read_text_strips_a_byte_order_mark(tmp_path: Path) -> None:
    """A BOM left in place breaks the very first line's heading match."""
    path = tmp_path / "bom.md"
    path.write_bytes(b"\xef\xbb\xbf## 2026-08-22\n")
    text = checks.read_text(path)

    assert text.startswith("## ")
    assert checks.DATE_HEADING_RE.match(text.splitlines()[0]) is not None


def test_a_bom_does_not_silently_swallow_the_whole_file(tmp_path: Path) -> None:
    """The dangerous shape, not just the visible one.

    A BOM on a line the parser must match makes that `## ` heading unrecognisable, and
    every entry beneath an unrecognised heading is collected into no block at all -- so the
    lint reports ZERO findings on a file full of broken entries. Silent under-reporting is
    the failure worth a test; a BOM on a prose title line would pass either way.
    """
    broken_entry = (
        "## 2026-08-22\n\n### SKILL-ADDED: missing everything\n- **What:** x\n"
    )
    path = tmp_path / "ai-changelog.md"
    path.write_bytes(b"\xef\xbb\xbf" + broken_entry.encode("utf-8"))

    messages = [
        f.message for f in checks.lint_changelog(checks.read_text(path), "x.md")
    ]
    assert sorted(messages) == [
        "entry missing required field 'Affected workflows'",
        "entry missing required field 'Files'",
        "entry missing required field 'Why'",
    ]


def test_crlf_endings_produce_identical_findings_and_line_numbers() -> None:
    """A file authored on Windows must report the same lines as one authored on Linux."""
    broken = _GOOD_CHANGELOG.replace("- **Files:** `a.md`\n", "")
    lf = checks.lint_changelog(broken, "x.md")
    crlf = checks.lint_changelog(broken.replace("\n", "\r\n"), "x.md")

    assert lf == crlf
    assert [f.message for f in lf] == ["entry missing required field 'Files'"]


def test_ascii_safe_survives_content_a_legacy_console_cannot_encode() -> None:
    text = "an em-dash — an arrow → and 日本語"
    safe = checks.ascii_safe(text)

    safe.encode("cp1252")  # the crash this exists to prevent
    assert safe.isascii()


def test_every_emitted_line_is_ascii_even_when_the_file_is_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Findings quote entry titles, so non-ASCII input must not reach the console raw."""
    contaminated = _GOOD_CHANGELOG.replace(
        "a real entry", "an em-dash — entry"
    ).replace("- **Files:** `a.md`\n", "")
    root = _project(tmp_path, changelog=contaminated)

    assert main(["lint", "changelog", "--project", str(root)]) == 1
    out = capsys.readouterr().out
    assert out.isascii(), f"non-ASCII reached stdout: {out!r}"
    assert "entry" in out


def test_no_absolute_path_is_ever_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """This output gets pasted into hand-offs; an absolute path there is machine-specific."""
    root = _project(
        tmp_path, changelog=_GOOD_CHANGELOG.replace("- **Files:** `a.md`\n", "")
    )
    _write(root / ".ai" / "handoffs" / "2026-08-22-x.md", _GOOD_HANDOFF)

    assert main(["lint", "--project", str(root)]) == 1
    out = capsys.readouterr().out
    assert str(root) not in out
    assert str(tmp_path) not in out
    assert ".ai/ai-changelog.md:" in out


# --- vocabulary pinning -------------------------------------------------------------------
#
# Each of these reads the shipped skill and compares both directions. A one-sided check is
# not enough: a taxonomy value the skill documents but the lint rejects turns every
# conforming entry into a false positive, and a value the lint accepts but the skill does
# not document is a rule nobody was told about.


def _shipped_skill(name: str, *parts: str) -> Path:
    """One shipped skill's file, resolved by NAME rather than by a hardcoded tree path.

    The pack split moved the skills tree from `assets/skills/` to `plugins/<pack>/skills/`,
    and these pins broke on the path even though no taxonomy had drifted -- a red test that
    means nothing about the thing it guards. `shipped_skill_dirs()` answers "where does this
    skill live" across every pack, so the pins survive the next move too, and a skill that
    changes pack does not read as a vocabulary change.
    """
    return shipped_skill_dirs()[name].joinpath(*parts)


_TABLE_CODE_RE = re.compile(r"^\|\s*`([A-Z][A-Z-]+)`\s*\|", re.MULTILINE)
_TABLE_BOLD_RE = re.compile(r"^\|\s*\*\*([A-Z][^*|]+?)\*\*\s*\|", re.MULTILINE)
_LEARNINGS_ROW_RE = re.compile(
    r"^\|\s*([A-Z][^|]*?)\s*\|\s*`([a-z-]+)`\s*\|", re.MULTILINE
)

# Upstream states the hand-off contract in prose and in one table row, so these parse it on
# its own terms. Both must be able to yield a member `checks.py` lacks -- see the fidelity
# section at the bottom of this file for why that property is the whole point.
_UPSTREAM_HANDOFF_SECTION_RE = re.compile(r"`## ([A-Z][^`]*)`")
_LIFECYCLE_RE = re.compile(r"Status lifecycle:\*\*(.+)$", re.MULTILINE)
_STATUS_TOKEN_RE = re.compile(r"\b([A-Z]{4,})\b")
_UPSTREAM_HANDOFF_STATUS_ROW_RE = re.compile(
    r"^\|\s*`## Status`\s*\|(.+)$", re.MULTILINE
)
_BACKTICKED_SLUG_RE = re.compile(r"`([a-z][a-z-]+)`")


def _pin_message(kind: str, source: str) -> str:
    return (
        f"the {kind} in checks.py no longer matches {source}. A refresh changed the "
        "taxonomy: update the constant (and any entry-format assumption it carries) so "
        "the lint accepts exactly what the skill documents."
    )


def test_changelog_types_match_the_shipped_skill() -> None:
    text = _shipped_skill("ai-changelog", "SKILL.md").read_text(encoding="utf-8")
    documented = set(_TABLE_CODE_RE.findall(text))

    assert documented, "no change-type table found in ai-changelog/SKILL.md"
    assert documented == set(checks.CHANGELOG_TYPES), _pin_message(
        "changelog taxonomy", "ai-changelog/SKILL.md"
    )


def test_learnings_sections_and_slugs_match_the_shipped_skill() -> None:
    # The canonical set lives in the reference doc, not SKILL.md: it is shared with
    # `learning-consolidator`, and a table duplicated in both drifts silently.
    ref = "task-learnings/references/learnings-format.md"
    text = (
        _shipped_skill("task-learnings", "references", "learnings-format.md")
    ).read_text(encoding="utf-8")
    # Two groups per row, so this pins the header-to-slug PAIRING, not just the
    # header set -- a mismatched slug is the failure that actually breaks the lint.
    documented_pairs = set(_LEARNINGS_ROW_RE.findall(text))

    assert documented_pairs, f"no category table found in {ref}"
    assert documented_pairs == set(checks.LEARNINGS_SECTIONS.items()), _pin_message(
        "learnings sections", ref
    )

    # The slug list is the one the entry format tells an author to write.
    slug_line = re.search(r"^- \*\*Category\*\*: (.+\|.+)$", text, re.MULTILINE)
    assert slug_line is not None, f"no Category slug line found in {ref}"
    documented_slugs = {part.strip() for part in slug_line.group(1).split("|")}
    assert documented_slugs == set(checks.LEARNINGS_SECTIONS.values()), _pin_message(
        "learnings category slugs", ref
    )


def test_hypothesis_categories_match_the_shipped_skill() -> None:
    text = _shipped_skill("ai-improvement-tracker", "SKILL.md").read_text(
        encoding="utf-8"
    )
    documented = set(_TABLE_BOLD_RE.findall(text))

    assert documented, "no category table found in ai-improvement-tracker/SKILL.md"
    assert documented == set(checks.HYPOTHESIS_CATEGORIES), _pin_message(
        "hypothesis categories", "ai-improvement-tracker/SKILL.md"
    )


def test_hypothesis_statuses_match_the_shipped_seed_file() -> None:
    """The seed file states the lifecycle, so it is the stable source for the status set."""
    text = (assets_root() / "ai" / "improvement-hypotheses.md").read_text(
        encoding="utf-8"
    )
    lifecycle = _LIFECYCLE_RE.search(text)

    assert lifecycle is not None, (
        "no status lifecycle line in improvement-hypotheses.md"
    )
    documented = set(_STATUS_TOKEN_RE.findall(lifecycle.group(1)))
    assert documented == set(checks.HYPOTHESIS_STATUSES), _pin_message(
        "hypothesis statuses", "the improvement-hypotheses.md seed"
    )


# The tracker states the threshold as "(>=10 unsynthesized terminal verdicts" and wraps the
# line inside it, so the gap is any whitespace.
_THRESHOLD_RE = re.compile(r"(?:≥|>=)\s*(\d+)\s+unsynthesized\s+terminal\s+verdicts")


def _documented_threshold(text: str) -> int | None:
    match = _THRESHOLD_RE.search(text)
    return int(match.group(1)) if match else None


def test_the_meta_synthesis_threshold_matches_the_tracker_skill() -> None:
    """The number the lint fires at and the number the skill tells people it fires at are
    one fact stated twice; this is what stops them drifting apart."""
    # The reader can see a number other than the code's, and can see none at all -- so a
    # green result below means it read the skill, not that it read nothing.
    assert (
        _documented_threshold("the NOTE (≥12\nunsynthesized terminal verdicts)") == 12
    )
    assert _documented_threshold("no threshold is stated in this text") is None

    text = _shipped_skill("ai-improvement-tracker", "SKILL.md").read_text(
        encoding="utf-8"
    )
    documented = _documented_threshold(text)

    assert documented is not None, (
        "ai-improvement-tracker/SKILL.md no longer states the threshold in the form "
        "'>=N unsynthesized terminal verdicts', so the pin cannot read it"
    )
    assert documented == checks.META_SYNTHESIS_DUE_AT, (
        f"the tracker skill says the due NOTE fires at {documented}, checks.py at "
        f"{checks.META_SYNTHESIS_DUE_AT}: change one so they agree"
    )


def test_handoff_contract_sections_match_the_shipped_skill() -> None:
    """`parallel-session-safety` defines the contract this lint enforces."""
    skill = _shipped_skill("parallel-session-safety", "SKILL.md")
    if not skill.is_file():  # pragma: no cover - the skill is being ported concurrently
        pytest.skip("parallel-session-safety is not shipped yet")
    text = skill.read_text(encoding="utf-8")

    for section in checks.HANDOFF_REQUIRED_SECTIONS:
        assert f"`## {section}`" in text, _pin_message(
            f"hand-off section '{section}'", "parallel-session-safety/SKILL.md"
        )
    for status in checks.HANDOFF_STATUSES:
        assert status in text, _pin_message(
            f"hand-off status '{status}'", "parallel-session-safety/SKILL.md"
        )


# The one printed form of a support-CLI command in a skill of a pack OTHER than core, which
# finds core through its kit-setup skill. Nothing precedes the command and `--project` is
# last: without it, `uv --directory` moves the working directory into the plugin and the
# project cannot be discovered, so the command exits 2.
_CANONICAL_PREFIX = (
    'uv run --no-project --directory "${KIT_CORE_PLUGIN_ROOT}/src" '
    "python -B -m lemmi_ai_kit "
)
_CANONICAL_SUFFIX = ' --project "${KIT_PROJECT_ROOT}"'


def _printed_cli_lines(text: str) -> list[str]:
    """Every line of `text` that names the support package's module."""
    return [line.strip() for line in text.splitlines() if "lemmi_ai_kit" in line]


def _is_canonical_cli_line(line: str) -> bool:
    return line.startswith(_CANONICAL_PREFIX) and line.endswith(_CANONICAL_SUFFIX)


def _section_nine(skill_text: str) -> str:
    match = re.search(
        r"^## [^\n]*The hand-off artifact contract\n(.*?)(?=^## )",
        skill_text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, "parallel-session-safety has no hand-off contract section"
    return match.group(1)


def test_parallel_session_safety_prints_the_cli_in_the_canonical_form() -> None:
    text = _shipped_skill("parallel-session-safety", "SKILL.md").read_text(
        encoding="utf-8"
    )
    printed = _printed_cli_lines(text)

    assert len(printed) >= 2, f"the scan saw {len(printed)} line(s) naming the module"
    assert [line for line in printed if not _is_canonical_cli_line(line)] == []

    # The check can fail: each form the skill used to print is exactly what it refuses.
    assert not _is_canonical_cli_line("python -m lemmi_ai_kit lint handoffs")
    assert not _is_canonical_cli_line(
        'PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint'
    )
    assert not _is_canonical_cli_line(
        'uv run --no-project --directory "${KIT_CORE_PLUGIN_ROOT}/src" '
        "python -B -m lemmi_ai_kit lint handoffs x.md"
    )


def test_section_nine_names_list_commands_and_its_printed_lines_parse() -> None:
    text = _shipped_skill("parallel-session-safety", "SKILL.md").read_text(
        encoding="utf-8"
    )
    section = _section_nine(text)
    printed = _printed_cli_lines(section)

    assert "`--list-commands`" in section
    assert any("--list-commands" in line for line in printed)
    assert any(
        "lint handoffs <file>" in line and "--list-commands" not in line
        for line in printed
    )

    parser = _build_parser()
    for line in printed:
        words = shlex.split(line)
        argv = [
            re.sub(r"<[^>]+>", "x.md", word)
            for word in words[words.index("lemmi_ai_kit") + 1 :]
        ]
        args = parser.parse_args(argv)
        assert (args.command, args.target) == ("lint", "handoffs"), line
        assert args.list_commands is ("--list-commands" in line), line

    # The parse can fail: a flag the parser does not know is refused, not ignored.
    with pytest.raises(SystemExit):
        parser.parse_args(["lint", "handoffs", "x.md", "--no-such-flag"])


def test_section_nine_states_every_clause_of_its_listing_rule() -> None:
    """`--list-commands` is one clause of section 9's rule; the others are what make the
    listing worth running. Each clause is asserted on its own, so a deleted one names
    itself, and line breaks are folded first, so re-wrapping the paragraph is no change."""
    text = _shipped_skill("parallel-session-safety", "SKILL.md").read_text(
        encoding="utf-8"
    )
    flat = " ".join(_section_nine(text).split())

    for clause in (
        "give each `<placeholder>` a stand-in (`--stand-in NAME=VALUE`)",
        "run each that neither writes nor bills in the shell the receiver will use",
        "name in `## Status` any not run and why",
    ):
        assert clause in flat, f"section 9 lost the clause: {clause}"

    # The flag the section names is a flag the parser takes.
    args = _build_parser().parse_args(
        ["lint", "handoffs", "x.md", "--list-commands", "--stand-in", "NAME=VALUE"]
    )
    assert args.stand_in == ["NAME=VALUE"]


def test_the_shipped_seed_files_lint_clean() -> None:
    """The kit's own corpus must pass: a validator whose fixtures fail trains people to
    ignore it, and these three files are what every adopter starts from."""
    root = assets_root() / "ai"
    assert checks.lint_learnings(checks.read_text(root / "learnings.md"), "x") == []
    assert checks.lint_changelog(checks.read_text(root / "ai-changelog.md"), "x") == []
    assert (
        checks.lint_hypotheses(
            checks.read_text(root / "improvement-hypotheses.md"), "x"
        )
        == []
    )


# --- changelog lint -----------------------------------------------------------------------


def test_changelog_accepts_a_conforming_entry() -> None:
    assert checks.lint_changelog(_GOOD_CHANGELOG, "x.md") == []


def test_changelog_rejects_an_off_taxonomy_type() -> None:
    text = _GOOD_CHANGELOG.replace("SKILL-ADDED:", "BOGUS-TYPE:")
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert any("BOGUS-TYPE" in m and "locked taxonomy" in m for m in messages)


def test_changelog_rejects_an_entry_with_no_type_prefix() -> None:
    text = _GOOD_CHANGELOG.replace("### SKILL-ADDED: a real entry", "### a real entry")
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert any("no 'TYPE:' prefix" in m for m in messages)


def test_changelog_reports_every_missing_required_field() -> None:
    text = "# c\n\n## 2026-08-22\n\n### SKILL-ADDED: bare\n- **What:** only this\n"
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert sorted(messages) == [
        "entry missing required field 'Affected workflows'",
        "entry missing required field 'Files'",
        "entry missing required field 'Why'",
    ]


def test_date_headings_must_be_reverse_chronological_and_unique() -> None:
    text = "# c\n\n## 2026-08-20\n\n## 2026-08-22\n\n## 2026-08-22\n"
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert any("reverse-chronological order violated" in m for m in messages)
    assert any("duplicate date heading" in m for m in messages)


def test_a_heading_that_is_not_a_date_is_reported() -> None:
    text = "# c\n\n## Not A Date\n"
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert any("is not a YYYY-MM-DD date" in m for m in messages)


def test_an_impossible_calendar_date_is_reported() -> None:
    text = "# c\n\n## 2026-02-30\n"
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert any("not a real calendar date" in m for m in messages)


# --- structural checks: append and merge damage -------------------------------------------


def test_a_heading_spliced_into_a_field_line_is_caught() -> None:
    """The swallowed entry is invisible to every heading-based check, so this is the only
    thing that sees it."""
    text = (
        "# c\n\n## 2026-08-22\n\n### SKILL-ADDED: first\n"
        "- **What:** a thing### SKILL-ADDED: second swallowed\n"
        "- **Why:** y\n- **Files:** f\n- **Affected workflows:** none\n"
    )
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert any("spliced into a field line" in m for m in messages)


def test_a_heading_quoted_inside_a_code_span_is_not_a_splice() -> None:
    """Entries legitimately quote the format they follow; a lint people learn to ignore is
    worse than the corruption it catches."""
    text = (
        "# c\n\n## 2026-08-22\n\n### SKILL-ADDED: first\n"
        "- **What:** the format is `### SKILL-ADDED: title`\n"
        "- **Why:** y\n- **Files:** f\n- **Affected workflows:** none\n"
    )
    assert checks.lint_changelog(text, "x.md") == []


def test_a_duplicated_field_block_is_caught() -> None:
    """`fields_of` keeps the first value, so a double append is otherwise silent."""
    text = (
        "# c\n\n## 2026-08-22\n\n### SKILL-ADDED: first\n"
        "- **What:** a\n- **Why:** b\n- **Files:** f\n- **Affected workflows:** none\n"
        "- **What:** a\n- **Why:** b\n- **Files:** f\n- **Affected workflows:** none\n"
    )
    messages = [f.message for f in checks.lint_changelog(text, "x.md")]

    assert len([m for m in messages if "duplicate field block" in m]) == 4


def test_structural_checks_ignore_the_since_cutoff() -> None:
    """Merge damage predates no policy: a grandfathered entry corrupts as easily as a new
    one, so only the per-entry FORMAT checks are gated."""
    text = "# c\n\n## 2026-01-05\n\n## 2026-08-22\n\n### BOGUS: x\n"
    messages = [
        f.message for f in checks.lint_changelog(text, "x.md", since=date(2027, 1, 1))
    ]

    assert any("reverse-chronological order violated" in m for m in messages)
    assert not any("BOGUS" in m for m in messages)


def test_since_admits_entries_on_the_boundary_date() -> None:
    """The cutoff is inclusive, so an entry dated exactly on it is still checked."""
    text = "# c\n\n## 2026-08-22\n\n### BOGUS: x\n"
    messages = [
        f.message for f in checks.lint_changelog(text, "x.md", since=date(2026, 8, 22))
    ]

    assert any("BOGUS" in m for m in messages)


# --- hypotheses lint ----------------------------------------------------------------------


def test_hypotheses_accepts_a_conforming_entry() -> None:
    assert checks.lint_hypotheses(_GOOD_HYPOTHESES, "x.md") == []


def test_a_compound_category_is_rejected() -> None:
    text = _GOOD_HYPOTHESES.replace(
        "Category:** Quality", "Category:** Quality / Speed"
    )
    messages = [f.message for f in checks.lint_hypotheses(text, "x.md")]

    assert any("compound category" in m for m in messages)


def test_an_off_vocabulary_category_names_its_synonym() -> None:
    """The hint is what turns a rejected entry into a fixed one."""
    text = _GOOD_HYPOTHESES.replace("Category:** Quality", "Category:** Reliability")
    messages = [f.message for f in checks.lint_hypotheses(text, "x.md")]

    assert any("Reliability" in m and "use 'Quality'" in m for m in messages)


def test_an_unknown_category_without_a_synonym_is_still_rejected() -> None:
    text = _GOOD_HYPOTHESES.replace("Category:** Quality", "Category:** Vibes")
    messages = [f.message for f in checks.lint_hypotheses(text, "x.md")]

    assert any("Vibes" in m and "closed 7" in m for m in messages)


def test_a_narrative_status_is_rejected() -> None:
    text = _GOOD_HYPOTHESES.replace("Status:** PENDING", "Status:** mostly confirmed")
    messages = [f.message for f in checks.lint_hypotheses(text, "x.md")]

    assert any("Validation notes:" in m for m in messages)


def test_a_hypothesis_filed_under_an_older_heading_than_its_ref_is_caught() -> None:
    text = _GOOD_HYPOTHESES.replace("## 2026-08-22", "## 2026-08-01")
    messages = [f.message for f in checks.lint_hypotheses(text, "x.md")]

    assert any("misfiled under older heading" in m for m in messages)


def test_an_untagged_hypothesis_entry_is_reported() -> None:
    text = _GOOD_HYPOTHESES.replace("### [SKILL-ADDED] ", "### ")
    messages = [f.message for f in checks.lint_hypotheses(text, "x.md")]

    assert any("no '[TYPE]' tag" in m for m in messages)


# --- hypotheses lint: the ledger-growth NOTE ----------------------------------------------
#
# The validator and the tracker both tell an author that the lint prints a `meta-synthesis
# due` NOTE once enough terminal verdicts have piled up unsynthesized. For a long time the
# lint printed nothing of the kind, so a ledger could grow while nothing closed and no check
# said so. A NOTE never fails a run -- it schedules work -- so every shape below that is not
# "due" must also produce no FAILING finding.


def test_the_due_note_fires_at_ten_unmarked_verdicts_and_not_at_nine() -> None:
    findings = checks.lint_hypotheses(_ledger(terminal=10), "x.md")

    assert [f for f in findings if not f.note] == []
    notes = [f for f in findings if f.note]
    assert len(notes) == 1
    message = notes[0].message
    assert message.startswith("NOTE: meta-synthesis due")
    assert message.isascii()
    assert "10 terminal verdicts" in message and "0 covered" in message

    # One fewer is below the threshold, and entries still open never count towards it.
    # A MISSING marker alone must stay silent: the kit's own seed ledgers have none.
    assert checks.lint_hypotheses(_ledger(terminal=9), "x.md") == []
    assert checks.lint_hypotheses(_ledger(terminal=9, pending=5), "x.md") == []
    assert checks.lint_hypotheses(_ledger(pending=12), "x.md") == []


def test_the_due_count_is_file_wide_and_ignores_since() -> None:
    """The cutoff gates per-entry FORMAT checks; the ledger's growth is not a format."""
    findings = checks.lint_hypotheses(
        _ledger(terminal=10), "x.md", since=date(2030, 1, 1)
    )

    assert [f.message[:24] for f in findings] == ["NOTE: meta-synthesis due"]


def test_a_marker_discounts_the_verdicts_it_covers() -> None:
    """Fourteen resolved entries are due or not depending only on what the marker covers."""
    covered = "**Last meta-synthesis:** 2026-08-02 - {n} terminal verdicts covered"

    five = checks.lint_hypotheses(
        _ledger(terminal=14, marker=covered.format(n=5)), "x.md"
    )
    four = checks.lint_hypotheses(
        _ledger(terminal=14, marker=covered.format(n=4)), "x.md"
    )

    assert five == [], "14 - 5 = 9 unsynthesized is below the threshold"
    assert len(four) == 1 and four[0].note
    assert "14 terminal verdicts, 4 covered" in four[0].message


@pytest.mark.parametrize(
    ("marker", "covered"),
    [
        pytest.param(
            f"> **Last meta-synthesis:** none {_EM} 0 terminal verdicts covered",
            0,
            id="seed-shape",
        ),
        pytest.param(
            "**Last meta-synthesis:** 2026-08-02 - 4 terminal verdicts covered",
            4,
            id="date-hyphen-no-blockquote",
        ),
        pytest.param(
            f"> **Last meta-synthesis:** 2026-08-02 {_EM} 4 terminal verdicts covered "
            "(13 CONFIRMED / 3 REFUTED / 6 INCONCLUSIVE)",
            4,
            id="blockquote-em-dash-trailing-text",
        ),
        pytest.param(
            "**Last meta-synthesis**: 4 terminal verdicts covered",
            4,
            id="colon-outside-the-bold",
        ),
    ],
)
def test_the_marker_shapes_the_reader_accepts(marker: str, covered: int) -> None:
    findings = checks.lint_hypotheses(_ledger(terminal=14, marker=marker), "x.md")

    assert [f.note for f in findings] == [True]
    assert f"14 terminal verdicts, {covered} covered" in findings[0].message


def test_a_marker_above_the_count_is_a_note_and_never_a_failure() -> None:
    """A marker that covers MORE verdicts than the ledger holds is stale or mistyped; the
    operator's ruling is that it is reported, not failed."""
    marker = (
        f"> **Last meta-synthesis:** 2026-08-02 {_EM} 22 terminal verdicts covered "
        "(13 CONFIRMED / 3 REFUTED / 6 INCONCLUSIVE)"
    )
    findings = checks.lint_hypotheses(_ledger(terminal=1, marker=marker), "x.md")

    assert [f.note for f in findings] == [True]
    message = findings[0].message
    assert "22" in message and "holds 1" in message
    assert "meta-synthesis due" not in message, (
        "it is not due, it is ahead of the ledger"
    )
    assert message.isascii()


def test_an_unreadable_marker_is_a_note_and_never_a_failure() -> None:
    marker = "**Last meta-synthesis:** sometime last week"
    findings = checks.lint_hypotheses(_ledger(terminal=3, marker=marker), "x.md")

    assert [f.note for f in findings] == [True]
    assert "unreadable" in findings[0].message
    assert findings[0].message.isascii()


def test_a_fenced_marker_is_example_text_not_the_marker() -> None:
    """These files document their own format, so a fenced example is not the marker."""
    example = (
        "```markdown\n"
        "**Last meta-synthesis:** 2026-08-02 - 9 terminal verdicts covered\n"
        "```\n\n"
    )
    findings = checks.lint_hypotheses(
        _ledger(terminal=10, header_extra=example), "x.md"
    )

    assert [f.note for f in findings] == [True]
    assert "10 terminal verdicts, 0 covered" in findings[0].message


def test_the_seed_ships_the_marker_and_still_lints_clean() -> None:
    """The scaffold skips an existing seed, so only a NEW project gets this line; the
    validator text carries it to everyone else. It must not look like an entry or hold a
    date, because the seed is pinned as an empty ledger."""
    text = (assets_root() / "ai" / "improvement-hypotheses.md").read_text(
        encoding="utf-8"
    )
    expected = f"> **Last meta-synthesis:** none {_EM} 0 terminal verdicts covered"

    assert [ln for ln in text.splitlines() if "Last meta-synthesis" in ln] == [expected]
    marker = checks.read_meta_synthesis_marker(text)
    assert marker is not None and marker.covered == 0
    assert checks.lint_hypotheses(text, "x") == []


def test_lint_hypotheses_on_a_due_ledger_exits_zero_and_prints_the_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, hypotheses=_ledger(terminal=10))

    assert main(["lint", "hypotheses", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    assert "NOTE: meta-synthesis due" in out
    assert "--- hypotheses: 0 finding(s) ---" in out
    assert "LINT PASSED (0 finding(s))" in out
    assert out.isascii()


# --- learnings lint -----------------------------------------------------------------------


def test_learnings_accepts_a_conforming_entry() -> None:
    assert checks.lint_learnings(_GOOD_LEARNINGS, "x.md") == []


def test_a_slug_that_contradicts_its_section_is_caught() -> None:
    text = _GOOD_LEARNINGS.replace("- **Category**: pitfall", "- **Category**: pattern")
    messages = [f.message for f in checks.lint_learnings(text, "x.md")]

    assert any(
        "does not match its section" in m and "expected 'pitfall'" in m
        for m in messages
    )


def test_an_off_vocabulary_slug_reports_a_derived_count() -> None:
    """The count is derived from the section map -- a literal is what breaks on the day a
    seventh category is added."""
    text = _GOOD_LEARNINGS.replace(
        "- **Category**: pitfall", "- **Category**: nonsense"
    )
    messages = [f.message for f in checks.lint_learnings(text, "x.md")]

    expected = f"canonical {len(checks.LEARNINGS_SECTIONS)}"
    assert any(expected in m for m in messages)


def test_a_malformed_learnings_title_is_reported() -> None:
    text = _GOOD_LEARNINGS.replace("### [2026-08-22] A thing", "### A thing")
    messages = [f.message for f in checks.lint_learnings(text, "x.md")]

    assert any("not '[YYYY-MM-DD] title'" in m for m in messages)


def test_a_non_canonical_section_is_a_note_not_a_failure() -> None:
    """Sections drain over time; an intake buffer mid-drain must not fail its own lint."""
    text = _GOOD_LEARNINGS.replace("## Common Pitfalls", "## Some Other Bucket")
    findings = checks.lint_learnings(text, "x.md")

    notes = [f for f in findings if f.note]
    assert len(notes) == 1
    assert "tolerated until drained" in notes[0].message
    assert not [f for f in findings if not f.note]


# --- hand-offs ----------------------------------------------------------------------------


def test_a_conforming_handoff_passes() -> None:
    assert checks.lint_handoff(_GOOD_HANDOFF, "h.md") == []


def test_a_wrapped_bullet_keeps_the_expected_result_on_its_second_line() -> None:
    """A long command wraps, so its `-> result` sits on the CONTINUATION line.

    Reading only the first line of each bullet reports "no expected result" against an
    entry that has one. That punishes wrapping, which trains authors either to write
    unreadably long lines or to stop reading the linter.
    """
    text = _GOOD_HANDOFF.replace(
        "- `git status --short` -> clean tree",
        "- `git status --short --untracked-files=no` against a tree no peer"
        + chr(10)
        + "  session is writing -> clean tree",
    )

    assert checks.lint_handoff(text, "h.md") == []


def test_joining_a_wrapped_bullet_does_not_blind_the_missing_result_check() -> None:
    """The negative control for the join: a bullet with NO arrow anywhere still fails.

    A fix that only silences findings is worse than the defect it replaced.
    """
    text = _GOOD_HANDOFF.replace(
        "- `git status --short` -> clean tree",
        "- `git status --short --untracked-files=no` against a tree no peer"
        + chr(10)
        + "  session is writing, with no expected result stated at all",
    )

    messages = [f.message for f in checks.lint_handoff(text, "h.md")]
    assert any("no expected result" in m for m in messages)


def test_a_blank_line_closes_a_bullet_so_a_later_paragraph_is_not_absorbed() -> None:
    """Absorption must stop at the blank line, or an unrelated paragraph can supply
    the arrow a bullet is missing and the check passes on someone else's text."""
    text = _GOOD_HANDOFF.replace(
        "- `git status --short` -> clean tree",
        "- `git status --short`"
        + chr(10) * 2
        + "  an unrelated paragraph that happens to contain -> an arrow",
    )

    messages = [f.message for f in checks.lint_handoff(text, "h.md")]
    assert any("no expected result" in m for m in messages)


def test_a_handoff_missing_a_required_section_is_reported() -> None:
    text = _GOOD_HANDOFF.replace(
        "## Status\nin-progress. The second half is not done.\n", ""
    )
    messages = [f.message for f in checks.lint_handoff(text, "h.md")]

    assert "missing required section '## Status'" in messages


def test_a_duplicated_handoff_section_is_reported() -> None:
    """The second `## Status` would otherwise hide the first from every check."""
    messages = [
        f.message
        for f in checks.lint_handoff(_GOOD_HANDOFF + "\n## Status\nblocked\n", "h.md")
    ]

    assert any("duplicate section '## Status'" in m for m in messages)


def test_a_prose_precondition_is_rejected() -> None:
    """Prose state claims are the unreliable brief this contract exists to stop."""
    text = _GOOD_HANDOFF.replace(
        "- `git status --short` -> clean tree", "- make sure the tree is clean"
    )
    messages = [f.message for f in checks.lint_handoff(text, "h.md")]

    assert any("prose, not a runnable command" in m for m in messages)


def test_a_command_without_an_expected_result_is_rejected() -> None:
    text = _GOOD_HANDOFF.replace("- `pytest -q` -> 0 failed", "- `pytest -q`")
    messages = [f.message for f in checks.lint_handoff(text, "h.md")]

    assert any("no expected result" in m for m in messages)


def test_a_handoff_with_no_git_resolvable_anchor_is_rejected() -> None:
    """A hand-off is normally gitignored, so facts held only there lose the work."""
    text = _GOOD_HANDOFF.replace(
        "- branch `feature/thing`\n- charter `tasks/TECH-thing.md`",
        "It is all in my head.",
    )
    messages = [f.message for f in checks.lint_handoff(text, "h.md")]

    assert any("no git-resolvable reference" in m for m in messages)


def test_a_status_outside_the_vocabulary_is_rejected() -> None:
    text = _GOOD_HANDOFF.replace(
        "in-progress. The second half is not done.", "mostly fine"
    )
    messages = [f.message for f in checks.lint_handoff(text, "h.md")]

    assert any("must state one of" in m for m in messages)


def test_handoff_examples_inside_html_comments_are_ignored() -> None:
    """Comments hold deliberately-bad teaching examples, but line numbers must stay true."""
    text = _GOOD_HANDOFF.replace(
        "## Scope", "<!--\n## Status\nnot a real section\n-->\n\n## Scope"
    )
    assert checks.lint_handoff(text, "h.md") == []


def test_a_missing_handoff_directory_is_a_no_op(tmp_path: Path) -> None:
    """A project with no hand-offs yet must not fail its lint."""
    findings, scanned = checks.lint_handoff_dir(_project(tmp_path))

    assert findings == []
    assert scanned == 0


def test_a_readme_in_the_handoff_directory_is_not_linted(tmp_path: Path) -> None:
    """A directory note is not a hand-off."""
    root = _project(tmp_path)
    _write(root / ".ai" / "handoffs" / "README.md", "# What lives here\n")
    _write(root / ".ai" / "handoffs" / "2026-08-22-x.md", _GOOD_HANDOFF)

    findings, scanned = checks.lint_handoff_dir(root)
    assert findings == []
    assert scanned == 1


def test_anchor_resolution_is_off_unless_requested(tmp_path: Path) -> None:
    """It shells out per anchor, so the caller opts in; and it only ever adds notes."""
    root = _project(tmp_path)
    text = _GOOD_HANDOFF.replace("`feature/thing`", "`deadbee`")
    _write(root / ".ai" / "handoffs" / "2026-08-22-x.md", text)

    assert checks.lint_handoff_dir(root)[0] == []

    findings, _ = checks.lint_handoff_dir(root, resolve_anchors=True)
    assert all(f.note for f in findings), "anchor resolution must never fail a run"


def test_anchor_resolution_accepts_any_object_git_has_and_tests_head_for_real(
    tmp_path: Path,
) -> None:
    """A tree id, a blob id and `<rev>:<path>` are objects git has, and a committed file
    that was deleted from disk is still in HEAD -- all four used to draw a "does not
    resolve" note because only the disk and the commit test were consulted. `deadbee` and
    a path that exists nowhere are the negative controls: they prove the probe still runs
    and still says no."""
    repo = _git_repo(tmp_path / "repo")
    _write(repo / "d" / "a.md", "a\n")
    _write(repo / "d" / "b.md", "b\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture")
    tree = _git(repo, "rev-parse", "HEAD:d")
    blob = _git(repo, "rev-parse", "HEAD:d/a.md")
    (repo / "d" / "b.md").unlink()

    resolving = [tree, blob, "HEAD:d/a.md", "d/b.md"]
    dead = ["deadbee", "d/absent.md"]
    anchors = "\n".join(f"- `{token}`" for token in [*resolving, *dead])
    text = _GOOD_HANDOFF.replace(
        "- branch `feature/thing`\n- charter `tasks/TECH-thing.md`", anchors
    )

    findings = checks.lint_handoff(text, "h.md", repo)

    assert [f for f in findings if not f.note] == []
    notes = [f.message for f in findings if f.note]
    for token in resolving:
        assert not any(f"anchor {token!r} " in m for m in notes), (token, notes)
    for token in dead:
        assert any(f"anchor {token!r} " in m for m in notes), (token, notes)


def test_anchor_resolution_costs_at_most_four_git_calls_and_only_when_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe shells out per anchor, so its cost is part of the contract: one more call
    than before at most, none unless the caller opted in -- and the token goes after `--`,
    so an anchor that starts with a dash is an object name and never a git option. No real
    token tells those two forms apart, which is why the recorded argv is what is checked."""
    calls: list[list[str]] = []

    def fake_run(
        args: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        is_repo_check = args[1:3] == ["rev-parse", "--git-dir"]
        return subprocess.CompletedProcess(args, 0 if is_repo_check else 1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    text = _GOOD_HANDOFF.replace(
        "- branch `feature/thing`\n- charter `tasks/TECH-thing.md`", "- `-x/y`"
    )

    assert checks.lint_handoff(text, "h.md") == [], "no root, so nothing is resolved"
    assert calls == []

    findings = checks.lint_handoff(text, "h.md", tmp_path)

    assert [f.note for f in findings] == [True], "nothing resolved, so one note"
    assert len(calls) == 4, [" ".join(call[1:]) for call in calls]
    probes = [call for call in calls if call[1] == "cat-file"]
    assert [call[-2:] for call in probes] == [["--", "-x/y"], ["--", "HEAD:-x/y"]]


# --- lint CLI surface ---------------------------------------------------------------------


def test_lint_exits_zero_and_says_passed_on_a_clean_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Skills key on the PASSED/FAILED line, so it is part of the contract."""
    root = _project(
        tmp_path,
        learnings=_GOOD_LEARNINGS,
        changelog=_GOOD_CHANGELOG,
        hypotheses=_GOOD_HYPOTHESES,
    )
    assert main(["lint", "--project", str(root)]) == 0
    assert "LINT PASSED (0 finding(s))" in capsys.readouterr().out


def test_lint_exits_one_and_says_failed_on_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(
        tmp_path, changelog=_GOOD_CHANGELOG.replace("SKILL-ADDED:", "NOPE:")
    )

    assert main(["lint", "changelog", "--project", str(root)]) == 1
    assert "LINT FAILED (1 finding(s))" in capsys.readouterr().out


def test_lint_all_skips_a_missing_file_without_failing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A project that has not scaffolded every log yet has nothing to lint, not a failure."""
    root = _project(tmp_path, changelog=_GOOD_CHANGELOG)

    assert main(["lint", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    assert ".ai/learnings.md: not found, skipped" in out
    assert "LINT PASSED" in out


def test_naming_a_missing_file_explicitly_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, changelog=_GOOD_CHANGELOG)

    assert main(["lint", "learnings", "--project", str(root)]) == 2
    assert "no such file" in capsys.readouterr().out


def test_lint_rejects_a_malformed_since(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, changelog=_GOOD_CHANGELOG)

    assert (
        main(["lint", "changelog", "--project", str(root), "--since", "08/22/26"]) == 2
    )
    assert "--since must be YYYY-MM-DD" in capsys.readouterr().out


def test_lint_rejects_a_project_that_is_not_a_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["lint", "--project", str(tmp_path / "nope")]) == 2
    assert "not a directory" in capsys.readouterr().out


def test_list_entries_prints_the_inventory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, learnings=_GOOD_LEARNINGS)

    assert main(["lint", "learnings", "--project", str(root), "--list-entries"]) == 0
    out = capsys.readouterr().out
    assert "entries=1  sections=1" in out
    assert "## Common Pitfalls" in out
    assert "--- ENTRIES ---" in out
    assert "[2026-08-22] A thing that bites" in out
    assert "LINT" not in out, "inventory mode reports, it does not lint"


def test_list_entries_is_rejected_for_the_handoff_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)

    assert main(["lint", "handoffs", "--project", str(root), "--list-entries"]) == 2
    assert "needs a data file target" in capsys.readouterr().out


# --- lint handoffs: one file, and the command listing --------------------------------------


def _line_of(text: str, needle: str) -> int:
    """1-based number of the first line of `text` that contains `needle`."""
    return next(i for i, line in enumerate(text.splitlines(), 1) if needle in line)


def _handoff_project(tmp_path: Path) -> Path:
    """A git-backed project holding a README, a conforming hand-off and a broken one.

    Git-backed so `--resolve-anchors` has a repository to ask: outside one, anchors are
    undecidable and the lint reports no note at all, which would leave the notes half of
    these comparisons empty.
    """
    root = _project(_git_repo(tmp_path / "project"))
    handoffs = root / ".ai" / "handoffs"
    _write(handoffs / "README.md", "# What lives here\n")
    _write(handoffs / "2026-08-22-good.md", _GOOD_HANDOFF)
    _write(
        handoffs / "2026-08-22-bad.md",
        _GOOD_HANDOFF.replace("- `pytest -q` -> 0 failed", "- `pytest -q`"),
    )
    return root


def test_one_file_mode_reports_what_the_directory_run_reports_for_that_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The whole-directory run takes minutes on a large directory, so one file must be
    checkable alone -- and it has to be the SAME check, or the shortcut reports a
    different truth than the full run does."""
    root = _handoff_project(tmp_path)
    where = ".ai/handoffs/2026-08-22-bad.md"

    dir_findings, scanned = checks.lint_handoff_dir(root, resolve_anchors=True)
    expected = [f for f in dir_findings if f.where == where]
    assert scanned == 2, "the directory run skips the README"
    assert any(f.note for f in expected) and any(not f.note for f in expected), (
        "the comparison must cover a failing finding AND a note"
    )
    assert (
        checks.lint_handoff_file(root / where, root, resolve_anchors=True) == expected
    )

    assert main(["lint", "handoffs", "--resolve-anchors", "--project", str(root)]) == 1
    dir_lines = [
        ln for ln in capsys.readouterr().out.splitlines() if ln.startswith(where + ":")
    ]
    argv = ["lint", "handoffs", where, "--project", str(root), "--resolve-anchors"]
    assert main(argv) == 1
    one_run = capsys.readouterr().out
    one_lines = [ln for ln in one_run.splitlines() if ln.startswith(where + ":")]

    assert one_lines == dir_lines
    assert len(one_lines) == len(expected)
    assert "2026-08-22-good.md" not in one_run
    assert "--- handoffs: 1 finding(s), 1 file(s) ---" in one_run
    assert "LINT FAILED (1 finding(s))" in one_run


def test_a_relative_file_resolves_against_the_project_root_not_the_working_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The printed command runs with the working directory inside the plugin, so a
    relative FILE anchored on the working directory would never find the hand-off."""
    root = _handoff_project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    _write(elsewhere / "only-here.md", _GOOD_HANDOFF)
    monkeypatch.chdir(elsewhere)
    relative = ".ai/handoffs/2026-08-22-good.md"
    assert not (elsewhere / relative).exists()

    assert main(["lint", "handoffs", relative, "--project", str(root)]) == 0
    assert "--- handoffs: 0 finding(s), 1 file(s) ---" in capsys.readouterr().out

    absolute = str(root / relative)
    assert main(["lint", "handoffs", absolute, "--project", str(root)]) == 0
    capsys.readouterr()

    assert main(["lint", "handoffs", "only-here.md", "--project", str(root)]) == 2
    assert "only-here.md" in capsys.readouterr().out


def test_a_named_readme_is_linted_though_the_directory_run_skips_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _handoff_project(tmp_path)
    readme = ".ai/handoffs/README.md"

    assert main(["lint", "handoffs", "--project", str(root)]) == 1
    assert "README.md" not in capsys.readouterr().out

    assert main(["lint", "--project", str(root), "handoffs", readme]) == 1
    out = capsys.readouterr().out
    assert f"{readme}:1: ERROR missing required section '## Scope'" in out


def test_a_file_with_any_target_but_handoffs_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(
        tmp_path,
        learnings=_GOOD_LEARNINGS,
        changelog=_GOOD_CHANGELOG,
        hypotheses=_GOOD_HYPOTHESES,
    )
    for target in ("learnings", "changelog", "hypotheses", "all"):
        assert main(["lint", target, "x.md", "--project", str(root)]) == 2, target
        out = capsys.readouterr().out
        assert f"FILE is only valid with the 'handoffs' target, not '{target}'" in out


def test_a_named_hand_off_that_does_not_exist_is_a_usage_error_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _handoff_project(tmp_path)
    argv = ["lint", "handoffs", ".ai/handoffs/nope.md", "--project", str(root)]

    assert main(argv) == 2
    out = capsys.readouterr().out
    assert "no such hand-off file: .ai/handoffs/nope.md" in out
    assert str(tmp_path) not in out, "paths are printed relative to the project root"


def test_list_commands_prints_every_precondition_and_verification_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)
    where = ".ai/handoffs/2026-08-22-x.md"
    _write(root / where, _COMMANDS_HANDOFF)
    text = _COMMANDS_HANDOFF

    assert main(["lint", "handoffs", "--list-commands", "--project", str(root)]) == 0
    out = capsys.readouterr().out

    status = _line_of(text, "git status --short")
    tree = _line_of(text, "git ls-tree")
    pytest_at = _line_of(text, "pytest -q")
    diff = _line_of(text, "git diff")
    assert f"{where}:{status}: Preconditions: `git status --short` -> clean tree" in out
    # The wrapped bullet is reported at the line it starts on, with the arrow's text.
    assert (
        f"{where}:{tree}: Preconditions: UNRESOLVED <TREE> `git ls-tree <TREE>` "
        "-> lists d/"
    ) in out
    assert f"{where}:{pytest_at}: Verification: `pytest -q` -> 0 failed" in out
    assert (
        f"{where}:{diff}: Verification: UNRESOLVED <LOWER> <UPPER> "
        "`git diff <LOWER>..<UPPER>` -> empty"
    ) in out
    assert "the diff reads well" not in out, "a bullet with no command is not a command"
    assert "--- commands: 4 listed, 2 unresolved, 1 file(s) ---" in out
    assert "LINT" not in out, "a listing reports, it does not lint"


def test_a_stand_in_fills_its_placeholder_and_an_unfilled_one_is_marked_unresolved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)
    where = ".ai/handoffs/2026-08-22-x.md"
    _write(root / where, _COMMANDS_HANDOFF)
    tree = _line_of(_COMMANDS_HANDOFF, "git ls-tree")
    base = ["lint", "handoffs", where, "--list-commands", "--project", str(root)]

    assert main([*base, "--stand-in", "TREE=abc1234"]) == 0
    out = capsys.readouterr().out
    assert f"{where}:{tree}: Preconditions: `git ls-tree abc1234` -> lists d/" in out
    assert "UNRESOLVED <TREE>" not in out
    assert "UNRESOLVED <LOWER> <UPPER>" in out, "no stand-in was given for these"

    both = [*base, "--stand-in", "LOWER=v1", "--stand-in", "UPPER=v2"]
    assert main([*both, "--stand-in", "TREE=abc1234"]) == 0
    out = capsys.readouterr().out
    assert "`git diff v1..v2` -> empty" in out
    assert "UNRESOLVED" not in out
    assert "--- commands: 4 listed, 0 unresolved, 1 file(s) ---" in out


def test_list_commands_starts_no_subprocess(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running another session's text needs a shell, and the content-safety suite pins
    `shell=True` to one site that is not this one. So the listing builds no process at all
    -- shown by making every process start fail the test."""
    root = _project(tmp_path)
    _write(root / ".ai" / "handoffs" / "2026-08-22-x.md", _COMMANDS_HANDOFF)

    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("the listing must not start a process")

    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)

    # The instrument can see: a git probe made under the same patch trips it.
    probe = _GOOD_HANDOFF.replace("`feature/thing`", "`deadbee`")
    with pytest.raises(AssertionError, match="must not start a process"):
        checks.lint_handoff(probe, "h.md", root)

    argv = ["lint", "handoffs", "--list-commands", "--resolve-anchors"]
    assert main([*argv, "--project", str(root)]) == 0
    assert "`git status --short` -> clean tree" in capsys.readouterr().out


def test_list_commands_and_stand_in_misuse_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _handoff_project(tmp_path)
    where = ".ai/handoffs/2026-08-22-good.md"
    needs_target = "--list-commands needs the 'handoffs' target"
    shape = "--stand-in must be NAME=VALUE"
    cases = [
        (["lint", "all", "--list-commands"], needs_target),
        (["lint", "learnings", "--list-commands"], needs_target),
        (
            ["lint", "handoffs", where, "--stand-in", "TREE=abc"],
            "needs --list-commands",
        ),
        (["lint", "handoffs", where, "--list-commands", "--stand-in", "TREE"], shape),
        (["lint", "handoffs", where, "--list-commands", "--stand-in", "=abc"], shape),
        (
            ["lint", "handoffs", where, "--list-commands", "--stand-in", "<TREE>=a"],
            shape,
        ),
        (["lint", "handoffs", where, "--list-commands", "--stand-in", "TREE="], shape),
    ]
    for argv, fragment in cases:
        assert main([*argv, "--project", str(root)]) == 2, argv
        assert fragment in capsys.readouterr().out, argv


def test_list_commands_with_a_file_lists_that_file_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Section 9 prints `lint handoffs <file> --list-commands`, so naming a file has to
    narrow the listing to it -- shown against a second hand-off that the whole-directory
    listing does print."""
    root = _project(tmp_path)
    named = ".ai/handoffs/2026-08-22-named.md"
    other = ".ai/handoffs/2026-08-22-other.md"
    _write(root / named, _COMMANDS_HANDOFF)
    _write(root / other, _GOOD_HANDOFF.replace("`pytest -q`", "`make other`"))

    assert main(["lint", "handoffs", "--list-commands", "--project", str(root)]) == 0
    everything = capsys.readouterr().out
    assert "`make other` -> 0 failed" in everything
    assert "--- commands: 6 listed, 2 unresolved, 2 file(s) ---" in everything

    argv = ["lint", "handoffs", named, "--list-commands", "--project", str(root)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert f"FILE: {named}  commands=4  unresolved=2" in out
    assert other not in out
    assert "make other" not in out
    assert "--- commands: 4 listed, 2 unresolved, 1 file(s) ---" in out


def test_a_bullet_with_no_command_before_its_arrow_is_prose_to_the_lint_and_the_listing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Section 9: preconditions and verification are commands, never prose. A bullet that
    states a claim and backticks only its result names nothing to run, so the lint reports
    it as it reports any prose entry and the listing finds nothing in it to list -- where
    it used to print the RESULT as the command."""
    claim = "- check the log -> `ERROR` absent"
    text = _GOOD_HANDOFF.replace("- `pytest -q` -> 0 failed", claim)

    findings = checks.lint_handoff(text, "h.md")
    assert [(f.line, f.note) for f in findings] == [(_line_of(text, claim), False)]
    assert "'## Verification' entry is prose, not a runnable command" in (
        findings[0].message
    )

    root = _project(tmp_path)
    _write(root / ".ai" / "handoffs" / "2026-08-22-x.md", text)
    assert main(["lint", "handoffs", "--list-commands", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    assert "ERROR" not in out, "the expected result was listed as a command"
    assert "--- commands: 1 listed, 0 unresolved, 1 file(s) ---" in out

    # The same claim with its command before the arrow is a command again.
    command_first = text.replace(
        claim, "- `grep -c ERROR app.log` -> 0: `ERROR` absent"
    )
    assert checks.lint_handoff(command_first, "h.md") == []


def test_an_arrow_inside_a_command_belongs_to_the_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only an arrow outside the backticks ends a command: a jq path or a format string
    may hold `->` itself, and splitting there lists half a command and a wrong result."""
    command = "jq '.a -> .b' f.json"
    text = _GOOD_HANDOFF.replace(
        "- `pytest -q` -> 0 failed", f"- `{command}` -> prints x"
    )
    assert checks.lint_handoff(text, "h.md") == []

    root = _project(tmp_path)
    where = ".ai/handoffs/2026-08-22-x.md"
    _write(root / where, text)
    assert main(["lint", "handoffs", "--list-commands", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    line = _line_of(text, command)
    assert f"{where}:{line}: Verification: `{command}` -> prints x" in out
    assert "--- commands: 2 listed, 0 unresolved, 1 file(s) ---" in out


def test_a_placeholder_with_a_space_is_marked_and_a_stand_in_fills_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Section 9: give each `<placeholder>` a stand-in; an unfilled one is marked. The kit
    spells its own placeholder `<project root>`, with a space, which a name grammar with
    no spaces neither marked nor let a stand-in fill. The name must sit right inside the
    brackets, so a redirect with spaces around its file is still a plain command."""
    root = _project(tmp_path)
    where = ".ai/handoffs/2026-08-22-x.md"
    text = _GOOD_HANDOFF.replace(
        "- `pytest -q` -> 0 failed",
        "- `cat <project root>/x` -> ok\n- `sort < in.txt > out.txt` -> sorted",
    )
    _write(root / where, text)
    cat = _line_of(text, "cat <project root>")
    sort = _line_of(text, "sort < in.txt")
    base = ["lint", "handoffs", where, "--list-commands", "--project", str(root)]

    assert main(base) == 0
    out = capsys.readouterr().out
    assert (
        f"{where}:{cat}: Verification: UNRESOLVED <project root> "
        "`cat <project root>/x` -> ok"
    ) in out
    assert f"{where}:{sort}: Verification: `sort < in.txt > out.txt` -> sorted" in out
    assert "--- commands: 3 listed, 1 unresolved, 1 file(s) ---" in out

    assert main([*base, "--stand-in", "project root=/srv/app"]) == 0
    out = capsys.readouterr().out
    assert f"{where}:{cat}: Verification: `cat /srv/app/x` -> ok" in out
    assert "UNRESOLVED" not in out


def test_a_stand_in_fills_the_expected_result_as_well(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A result may name a placeholder too (`-> prints <SHA>`); left unfilled, the reader
    would compare real output with the literal `<SHA>`."""
    root = _project(tmp_path)
    where = ".ai/handoffs/2026-08-22-x.md"
    text = _GOOD_HANDOFF.replace(
        "- `pytest -q` -> 0 failed", "- `git rev-parse HEAD` -> prints <SHA>"
    )
    _write(root / where, text)
    argv = ["lint", "handoffs", where, "--list-commands", "--project", str(root)]

    assert main([*argv, "--stand-in", "SHA=abc1234"]) == 0
    out = capsys.readouterr().out
    assert "`git rev-parse HEAD` -> prints abc1234" in out
    assert "<SHA>" not in out


def test_a_refused_file_position_names_where_file_goes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FILE is read directly after the target. Python 3.11 stops reading positionals at
    the first option, so `lint handoffs --project DIR FILE` is refused there and read from
    3.12 on. How arguments are read is unchanged; what this pins is that refusing a stray
    `lint` argument says where FILE goes."""
    root = _handoff_project(tmp_path)
    where = ".ai/handoffs/2026-08-22-good.md"
    hint = "write FILE directly after the target"

    # Refused on every Python version: there is one FILE.
    with pytest.raises(SystemExit) as two_files:
        main(["lint", "handoffs", where, where, "--project", str(root)])
    assert two_files.value.code == 2
    assert hint in capsys.readouterr().err

    # The order the hint exists for.
    argv = ["lint", "handoffs", "--project", str(root), where]
    reads_file_after_an_option = sys.version_info >= (3, 12)
    if reads_file_after_an_option:
        assert main(argv) == 0
    else:
        with pytest.raises(SystemExit) as option_first:
            main(argv)
        assert option_first.value.code == 2
        assert hint in capsys.readouterr().err

    # Only a stray positional under `lint` gets the hint, not every refusal.
    for other in (["list", "extra"], ["lint", "handoffs", "--no-such-flag"]):
        with pytest.raises(SystemExit):
            main(other)
        err = capsys.readouterr().err
        assert "unrecognized arguments" in err, other
        assert hint not in err, other


def test_every_lint_target_is_reachable_from_the_cli(tmp_path: Path) -> None:
    """Guard the surface itself: a target in LINT_TARGETS the parser rejects is dead API."""
    root = _project(
        tmp_path,
        learnings=_GOOD_LEARNINGS,
        changelog=_GOOD_CHANGELOG,
        hypotheses=_GOOD_HYPOTHESES,
    )
    for target in checks.LINT_TARGETS:
        assert main(["lint", target, "--project", str(root)]) == 0, target


# --- audit-skills -------------------------------------------------------------------------


def test_a_conforming_skill_produces_nothing_above_info(tmp_path: Path) -> None:
    _skill(tmp_path, "good-skill")
    findings = checks.audit_skills(tmp_path)

    assert _severities(findings).keys() == {"INFO"}


def test_a_missing_skill_md_is_a_blocker(tmp_path: Path) -> None:
    (tmp_path / "empty-skill").mkdir()
    findings = checks.audit_skills(tmp_path)

    assert any(
        "SKILL.md missing" in f.message for f in findings if f.severity == "BLOCKER"
    )


def test_a_lowercase_skill_md_is_a_blocker_on_a_case_insensitive_filesystem(
    tmp_path: Path,
) -> None:
    """`(dir / "SKILL.md").exists()` answers True for `skill.md` on Windows and on a
    default macOS volume, and the runtime will not load it. The directory listing is the
    only case-exact test that behaves the same on all three platforms."""
    _skill(tmp_path, "wrong-case", filename="skill.md")
    findings = checks.audit_skills(tmp_path)

    assert any(
        "SKILL.md missing" in f.message for f in findings if f.severity == "BLOCKER"
    )


def test_unparseable_frontmatter_is_a_blocker(tmp_path: Path) -> None:
    _skill(tmp_path, "no-close", frontmatter="---\nname: no-close\ndescription: x\n")
    findings = checks.audit_skills(tmp_path)

    assert any("frontmatter unparseable" in f.message for f in findings)


def test_a_frontmatter_name_that_disagrees_with_the_directory_is_a_blocker(
    tmp_path: Path,
) -> None:
    _skill(
        tmp_path,
        "dir-name",
        frontmatter="---\nname: other-name\ndescription: x\nmetadata:\n  type: task\n---\n",
    )
    findings = checks.audit_skills(tmp_path)

    assert any("does not match the directory name" in f.message for f in findings)


def test_both_invocation_flags_set_is_a_blocker(tmp_path: Path) -> None:
    """The one genuinely broken combination: nobody can reach the skill."""
    _skill(
        tmp_path,
        "unreachable",
        frontmatter=(
            "---\nname: unreachable\ndescription: x\ndisable-model-invocation: true\n"
            "user-invocable: false\nmetadata:\n  type: task\n---\n"
        ),
    )
    findings = checks.audit_skills(tmp_path)

    assert any(
        "unreachable by anyone" in f.message
        for f in findings
        if f.severity == "BLOCKER"
    )


def test_a_missing_description_is_a_major(tmp_path: Path) -> None:
    _skill(
        tmp_path,
        "no-desc",
        frontmatter="---\nname: no-desc\nmetadata:\n  type: task\n---\n",
    )
    findings = checks.audit_skills(tmp_path)

    assert any("description missing" in f.message for f in findings)


def test_an_oversized_description_reports_the_spec_cap(tmp_path: Path) -> None:
    _skill(
        tmp_path,
        "long-desc",
        frontmatter=(
            f"---\nname: long-desc\ndescription: {'x' * (checks.SPEC_DESCRIPTION_MAX + 1)}\n"
            "metadata:\n  type: task\n---\n"
        ),
    )
    findings = checks.audit_skills(tmp_path)

    assert any(f"> {checks.SPEC_DESCRIPTION_MAX}" in f.message for f in findings)


def test_description_plus_when_to_use_over_the_listing_cap_is_reported(
    tmp_path: Path,
) -> None:
    half = "y" * (checks.LISTING_CAP // 2 + 10)
    _skill(
        tmp_path,
        "long-pair",
        frontmatter=(
            f"---\nname: long-pair\ndescription: {half}\nwhen_to_use: {half}\n"
            "metadata:\n  type: task\n---\n"
        ),
    )
    findings = checks.audit_skills(tmp_path)

    assert any("listing cap" in f.message for f in findings)


def test_a_missing_or_off_vocabulary_type_is_a_major(tmp_path: Path) -> None:
    _skill(tmp_path, "no-type", frontmatter="---\nname: no-type\ndescription: x\n---\n")
    _skill(
        tmp_path,
        "odd-type",
        frontmatter="---\nname: odd-type\ndescription: x\nmetadata:\n  type: vibes\n---\n",
    )
    messages = [f.message for f in checks.audit_skills(tmp_path)]

    assert any("metadata.type missing" in m for m in messages)
    assert any("off-vocabulary" in m for m in messages)


def test_an_oversized_skill_md_is_a_major(tmp_path: Path) -> None:
    _skill(tmp_path, "verbose", body="filler\n" * (checks.MAX_SKILL_LINES + 5))
    findings = checks.audit_skills(tmp_path)

    assert any(f"> {checks.MAX_SKILL_LINES}" in f.message for f in findings)


def test_a_readme_in_a_skill_directory_is_a_minor(tmp_path: Path) -> None:
    _skill(tmp_path, "with-readme")
    _write(tmp_path / "with-readme" / "README.md", "# nope\n")
    findings = checks.audit_skills(tmp_path)

    assert any(
        "entrypoint confusion" in f.message for f in findings if f.severity == "MINOR"
    )


@pytest.mark.parametrize("machine_path", [_DRIVE_PATH, _POSIX_HOME, "projects/c--x-y"])
def test_a_machine_specific_path_is_a_major(tmp_path: Path, machine_path: str) -> None:
    """All three shapes, so a fix to one pattern cannot silently drop the others."""
    _skill(tmp_path, "leaky", body=f"Read the notes at {machine_path} first.\n")
    findings = checks.audit_skills(tmp_path)

    assert any("hardcoded absolute path shape" in f.message for f in findings), (
        machine_path
    )


def test_a_path_shape_near_a_rule_marker_is_allowed(tmp_path: Path) -> None:
    """A line documenting the rule, and a redaction fixture next to its call, are the
    allowed matches -- the marker is searched in a window, not only on the matching line."""
    _skill(
        tmp_path,
        "documents-the-rule",
        body=f"Never hardcode a machine-specific path.\n\nLike {_DRIVE_PATH}.\n",
    )
    findings = checks.audit_skills(tmp_path)

    assert not any("hardcoded absolute path" in f.message for f in findings)


def test_a_broken_relative_link_is_a_major(tmp_path: Path) -> None:
    _skill(tmp_path, "bad-link", body="See [the detail](references/gone.md).\n")
    findings = checks.audit_skills(tmp_path)

    assert any("links to a missing file" in f.message for f in findings)


def test_a_link_inside_a_fenced_block_is_an_example_not_a_reference(
    tmp_path: Path,
) -> None:
    _skill(
        tmp_path,
        "teaches-links",
        body="Write it like this:\n\n```markdown\n[detail](references/example.md)\n```\n",
    )
    findings = checks.audit_skills(tmp_path)

    assert not any("links to a missing file" in f.message for f in findings)


def test_an_external_link_is_not_checked(tmp_path: Path) -> None:
    _skill(tmp_path, "links-out", body="See [the spec](https://example.com/spec).\n")
    findings = checks.audit_skills(tmp_path)

    assert not any("links to a missing file" in f.message for f in findings)


def test_a_missing_skills_directory_is_a_note_not_a_crash(tmp_path: Path) -> None:
    findings = checks.audit_skills(tmp_path / "nothing-here")

    assert _severities(findings).keys() == {"NOTE"}


# --- audit-skills: the two deliberately dropped upstream rules ----------------------------


def test_disable_model_invocation_alone_is_not_a_finding(tmp_path: Path) -> None:
    """Upstream reports this outside a name allowlist, which is that project's policy. The
    kit's own taxonomy *encourages* the flag on side-effect skills, so an allowlist here
    would report the skills that follow the documented rule."""
    _skill(
        tmp_path,
        "side-effect",
        frontmatter=(
            "---\nname: side-effect\ndescription: x\ndisable-model-invocation: true\n"
            "metadata:\n  type: task\n---\n"
        ),
    )
    findings = checks.audit_skills(tmp_path)

    assert _severities(findings).keys() == {"INFO"}


def test_a_user_invocable_reference_skill_is_not_a_finding(tmp_path: Path) -> None:
    """The shipped taxonomy makes `user-invocable: false` conditional on being
    workflow-only, so a reference skill a user may invoke directly is legitimate."""
    _skill(
        tmp_path,
        "quirks",
        frontmatter="---\nname: quirks\ndescription: x\nmetadata:\n  type: reference\n---\n",
    )
    findings = checks.audit_skills(tmp_path)

    assert _severities(findings).keys() == {"INFO"}


# --- audit-skills: registration drift -----------------------------------------------------


def _claude_md(root: Path, *lines: str) -> Path:
    body = "# Project\n\n## Skills\n\n" + "".join(f"- {line}\n" for line in lines)
    return _write(root / "CLAUDE.md", body)


def test_a_skill_on_disk_but_not_in_the_index_is_reported(tmp_path: Path) -> None:
    skills = tmp_path / ".claude" / "skills"
    _skill(skills, "unlisted")
    findings = checks.audit_skills(
        skills, claude_md=_claude_md(tmp_path), shipped=frozenset()
    )

    assert any("registration drift" in f.message for f in findings)


def test_a_plugin_namespaced_listing_resolves_against_the_catalog(
    tmp_path: Path,
) -> None:
    """A scaffolded index lists plugin skills as `/plugin:name`; checking only the
    directory would report every one of them as a ghost."""
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    claude_md = _claude_md(
        tmp_path, "`/lemmi-ai-kit-core:commit-message` - write a commit message"
    )
    findings = checks.audit_skills(
        skills, claude_md=claude_md, shipped=frozenset({"commit-message"})
    )

    assert not any("ghost listing" in f.message for f in findings)


def test_a_bare_listing_of_a_plugin_skill_also_resolves(tmp_path: Path) -> None:
    """Auto and internal plugin skills are indexed by bare name, not `/plugin:name`."""
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    claude_md = _claude_md(tmp_path, "ai-changelog - record an infra change")
    findings = checks.audit_skills(
        skills, claude_md=claude_md, shipped=frozenset({"ai-changelog"})
    )

    assert not any("ghost listing" in f.message for f in findings)


def test_a_name_in_the_index_that_exists_nowhere_is_a_ghost(tmp_path: Path) -> None:
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    claude_md = _claude_md(tmp_path, "long-gone - deleted last month")
    findings = checks.audit_skills(
        skills, claude_md=claude_md, shipped=frozenset({"commit-message"})
    )

    assert any("ghost listing" in f.message for f in findings)


def test_an_unreadable_catalog_suppresses_the_ghost_check_instead_of_guessing(
    tmp_path: Path,
) -> None:
    """The regression this exists for: treating an unknown catalog as an empty one reports
    every plugin skill in the index as a ghost -- a wrong answer dressed as a finding."""
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    claude_md = _claude_md(
        tmp_path, "`/lemmi-ai-kit-core:commit-message` - write a commit message"
    )
    findings = checks.audit_skills(skills, claude_md=claude_md, shipped=None)

    assert not any("ghost listing" in f.message for f in findings)
    assert any(
        "plugin catalog could not be read" in f.message
        for f in findings
        if f.severity == "NOTE"
    )


def test_a_name_only_mentioned_outside_the_skills_section_is_not_a_listing(
    tmp_path: Path,
) -> None:
    """Structural scope, not a whole-file grep: prose that mentions a skill is not an index
    entry, and treating it as one hides real drift."""
    skills = tmp_path / ".claude" / "skills"
    _skill(skills, "on-disk")
    _write(
        tmp_path / "CLAUDE.md",
        "# Project\n\n## Notes\n\n- on-disk is great\n\n## Skills\n\n- (none)\n",
    )
    findings = checks.audit_skills(
        skills, claude_md=tmp_path / "CLAUDE.md", shipped=frozenset()
    )

    assert any("registration drift" in f.message for f in findings)


def test_no_claude_md_is_a_note_not_a_major(tmp_path: Path) -> None:
    """The kit's own repository has no CLAUDE.md, and an adopter may not have scaffolded
    yet -- neither is a defect in their skills."""
    skills = tmp_path / ".claude" / "skills"
    _skill(skills, "fine")
    findings = checks.audit_skills(skills, claude_md=tmp_path / "CLAUDE.md")

    assert not [f for f in findings if f.severity == "MAJOR"]
    assert any("registration is unchecked" in f.message for f in findings)


# --- audit-skills CLI surface -------------------------------------------------------------


def test_audit_exits_zero_by_default_even_with_blockers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Findings are review input, not process failures -- that is the default contract the
    three calling skills rely on."""
    skills = tmp_path / ".claude" / "skills"
    (skills / "broken").mkdir(parents=True)

    assert main(["audit-skills", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "BLOCKER (1)" in out
    assert "review input, not failures" in out


@pytest.mark.parametrize(
    ("threshold", "expected"),
    [("none", 0), ("blocker", 1), ("major", 1), ("minor", 1)],
)
def test_fail_on_gates_at_the_named_severity(
    tmp_path: Path, threshold: str, expected: int
) -> None:
    skills = tmp_path / ".claude" / "skills"
    (skills / "broken").mkdir(parents=True)  # a BLOCKER: no SKILL.md

    assert (
        main(["audit-skills", "--project", str(tmp_path), "--fail-on", threshold])
        == expected
    )


def test_fail_on_ignores_severities_below_the_threshold(tmp_path: Path) -> None:
    """A MINOR-only fleet must not fail a blocker gate."""
    skills = tmp_path / ".claude" / "skills"
    _skill(skills, "with-readme")
    _write(skills / "with-readme" / "README.md", "# nope\n")

    assert (
        main(["audit-skills", "--project", str(tmp_path), "--fail-on", "blocker"]) == 0
    )
    assert main(["audit-skills", "--project", str(tmp_path), "--fail-on", "minor"]) == 1


def test_skills_dir_override_audits_an_arbitrary_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """How this repository audits its own shipped pack, which lives outside `.claude/`."""
    elsewhere = tmp_path / "packaged" / "skills"
    _skill(elsewhere, "fine")

    assert (
        main(
            ["audit-skills", "--project", str(tmp_path), "--skills-dir", str(elsewhere)]
        )
        == 0
    )
    assert "packaged/skills" in capsys.readouterr().out


def test_the_audit_output_is_ascii_even_for_a_non_ascii_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills = tmp_path / ".claude" / "skills"
    _skill(
        skills,
        "unicode-name",
        frontmatter="---\nname: unicode-name\ndescription: an em-dash — here\n---\n",
    )

    assert main(["audit-skills", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.isascii(), f"non-ASCII reached stdout: {out!r}"


def test_worst_severity_orders_by_the_published_scale() -> None:
    findings = [
        checks.AuditFinding("MINOR", "a", "m"),
        checks.AuditFinding("BLOCKER", "b", "m"),
        checks.AuditFinding("MAJOR", "c", "m"),
    ]
    assert checks.worst_severity(findings) == "BLOCKER"
    assert checks.worst_severity([]) is None


# --- frontmatter parser -------------------------------------------------------------------


def test_folded_scalars_and_one_nested_level_parse() -> None:
    """The two shapes every shipped skill uses: a folded description and `metadata.type`."""
    fields, error = checks.parse_frontmatter(
        "---\nname: x\ndescription: >\n  first line\n  second line\n"
        "metadata:\n  type: task\n---\n"
    )

    assert error is None
    assert fields is not None
    assert fields["description"] == "first line second line"
    assert fields["metadata"] == {"type": "task"}


def test_a_missing_opening_delimiter_is_reported() -> None:
    fields, error = checks.parse_frontmatter("# No frontmatter\n")

    assert fields is None
    assert error is not None
    assert "opening" in error


# --- fenced content is documentation, not structure ---------------------------------------
#
# Added after review. These files document their own format, so every fenced example is a
# heading, an entry, or a field bullet. Parsing them as real content reported CONFORMING
# entries as broken -- three separate false-positive classes from one missing fence check,
# and a false positive is the failure mode that teaches people to ignore a lint.


def test_a_fenced_date_heading_does_not_split_the_entry_around_it() -> None:
    """It became a real heading, so every field below the fence left the entry with it."""
    text = (
        "# c\n\n## 2026-08-22\n\n### SKILL-ADDED: teaches the format\n"
        "- **What:** write it like\n\n```markdown\n## 2026-01-01\n```\n\n"
        "- **Why:** y\n- **Files:** f\n- **Affected workflows:** none\n"
    )
    assert checks.lint_changelog(text, "x.md") == []


def test_a_fenced_entry_heading_is_not_a_phantom_entry() -> None:
    text = (
        "# c\n\n## 2026-08-22\n\n### INFRA-MODIFIED: documents the format\n"
        "- **What:** entries look like:\n\n```markdown\n### SKILL-ADDED: title\n```\n\n"
        "- **Why:** y\n- **Files:** f\n- **Affected workflows:** none\n"
    )
    assert checks.lint_changelog(text, "x.md") == []


def test_fenced_field_bullets_are_not_a_duplicate_field_block() -> None:
    """A skill that shows the entry format in a fence is not double-appending it."""
    text = (
        "# c\n\n## 2026-08-22\n\n### INFRA-MODIFIED: documents the format\n"
        "- **What:** a\n- **Why:** b\n- **Files:** f\n- **Affected workflows:** none\n\n"
        "```markdown\n- **What:** a\n- **Why:** b\n- **Files:** f\n"
        "- **Affected workflows:** none\n```\n"
    )
    assert checks.lint_changelog(text, "x.md") == []


def test_a_tilde_fence_counts_as_a_fence_too() -> None:
    text = (
        "# c\n\n## 2026-08-22\n\n### SKILL-ADDED: teaches the format\n"
        "- **What:** like so\n\n~~~markdown\n## 2026-01-01\n~~~\n\n"
        "- **Why:** y\n- **Files:** f\n- **Affected workflows:** none\n"
    )
    assert checks.lint_changelog(text, "x.md") == []


def test_a_fenced_status_example_is_not_a_duplicate_handoff_section() -> None:
    text = _GOOD_HANDOFF + "\nExample:\n```markdown\n## Status\nnot real\n```\n"
    assert checks.lint_handoff(text, "h.md") == []


# --- entries above the first heading ------------------------------------------------------


def test_an_entry_above_the_first_heading_is_reported() -> None:
    """Added after review. Entries are filed under headings, so one that precedes the first
    heading belongs to no block -- invisible to the required-field, taxonomy and date
    checks. The file linted CLEAN while the entry was broken."""
    findings = checks.lint_changelog(
        "# Title\n\n### SKILL-ADDED: orphan\n- **What:** x\n", "x.md"
    )

    assert len(findings) == 1
    assert "above the first '## ' heading" in findings[0].message
    assert findings[0].line == 3


def test_an_orphan_entry_is_reported_in_every_data_file(tmp_path: Path) -> None:
    orphan = "# t\n\n### [2026-08-22] a thing\n- **Context**: x\n"
    for lint in (checks.lint_learnings, checks.lint_changelog, checks.lint_hypotheses):
        findings = [f for f in lint(orphan, "x.md") if "above the first" in f.message]
        assert len(findings) == 1, lint.__name__


def test_a_fenced_entry_before_any_heading_is_not_an_orphan() -> None:
    """A file whose header block shows the entry format has not lost an entry."""
    text = "# t\n\nEntries look like:\n\n```markdown\n### SKILL-ADDED: title\n```\n"
    assert checks.lint_changelog(text, "x.md") == []


def test_the_inventory_attributes_entries_above_the_first_section() -> None:
    """Without the row, the per-section counts silently fail to add up to the total."""
    lines = checks.inventory("# t\n\n### orphan\n\n## A\n\n### one\n", "x.md")

    assert "  (above the first section)  entries=1" in lines
    assert "entries=2  sections=1" in lines[0]


# --- explicit dispatch --------------------------------------------------------------------


def test_an_unknown_lint_target_raises_instead_of_resolving_silently() -> None:
    """Argparse guards the CLI, but these are library functions: the old code mapped any
    unknown name to the hand-off directory and to the hypotheses lint."""
    with pytest.raises(ValueError, match="unknown lint target"):
        checks.target_path("nonsense", Path("root"))
    with pytest.raises(ValueError, match="not a data-file lint target"):
        checks.lint_file("nonsense", "", "x.md", None)


def test_every_file_target_resolves_to_a_distinct_path(tmp_path: Path) -> None:
    """Guard the table itself: two targets sharing a path would lint the same file twice."""
    paths = {t: checks.target_path(t, tmp_path) for t in checks.LINT_TARGETS}
    assert len(set(paths.values())) == len(checks.LINT_TARGETS), paths


# --- upstream fidelity (W-2) --------------------------------------------------------------
#
# The five pins above compare a shipped document to a kit constant. Both operands come from
# this tree, so they measure CONSISTENCY, never fidelity: a refresh that drops a taxonomy
# member from the document AND from `checks.py` leaves every one of them green. That is not
# hypothetical. `EXPERIMENT-REGISTERED` was absent from the shipped table, from
# `CHANGELOG_TYPES`, and from `ai-improvement-tracker` -- zero occurrences in the whole
# package -- while `test_changelog_types_match_the_shipped_skill` passed, because both of its
# operands had lost the member together.
#
# So these add the third operand. They are skipped without an upstream checkout, which is the
# normal case for a contributor and for CI: the upstream repository is private and its
# location is deliberately not recorded in this repo. A skipped fidelity check is honest; a
# check that cannot fail is not.
#
# The assertion is deliberately ONE-SIDED. The kit is allowed to be ahead of upstream, and is
# (`orchestrate` and `agent-delegate` originated here). What it may not be is silently BEHIND:
# a member upstream defines must either ship here or be named below with a reason.

_DECLARED_VOCABULARY_DIVERGENCES: dict[str, dict[str, str]] = {
    # vocabulary -> {member: why the kit deliberately does not carry it}
    #
    # Empty on purpose, and it is the point of the mechanism rather than an oversight: at the
    # 2026-08-23 sync every member upstream defines is carried. Adding an entry here is a
    # CLAIM -- that the member encodes the source project's policy rather than something an
    # adopter agreed to -- and it belongs in review. Two rules were dropped on exactly that
    # ground (see the `checks.py` vocabularies comment); a third, `EXPERIMENT-REGISTERED`, was
    # recorded as a deliberate drop and turned out to be an accident of a bad merge base. So a
    # reason written here needs to survive the question "was this decided, or explained after
    # the fact?"
}


def _upstream_or_skip() -> tuple[Path, str]:
    """The upstream checkout and the pinned revision, or a skip."""
    repo = resolve_upstream(None)
    if repo is None:
        pytest.skip(f"set ${ENV_VAR} to a real upstream checkout to run this")
    try:
        return repo, load_sync_record().upstream_commit
    except (
        SyncRecordError,
        OSError,
    ) as exc:  # pragma: no cover - record is gated elsewhere
        pytest.skip(f"sync record unusable: {exc}")


def _assert_carried(vocabulary: str, upstream_members: set[str], kit: set[str]) -> None:
    assert upstream_members, (
        f"parsed zero {vocabulary} out of upstream -- the document moved or the regex no "
        "longer matches it. A fidelity check that parses nothing passes vacuously, which is "
        "the failure this whole section exists to prevent."
    )
    declared = _DECLARED_VOCABULARY_DIVERGENCES.get(vocabulary, {})
    missing = {m for m in upstream_members - kit if m not in declared}
    assert not missing, (
        f"upstream defines {vocabulary} this pack does not carry: {sorted(missing)}. Either "
        "carry them (re-merge the skill against its own extraction base, not the pin) or add "
        f"each to _DECLARED_VOCABULARY_DIVERGENCES['{vocabulary}'] with the reason it encodes "
        "the source project's policy rather than an adopter's. Dropping a member from the doc "
        "and the constant together is exactly what the pins above cannot see."
    )


def test_upstream_changelog_types_are_all_carried() -> None:
    repo, pin = _upstream_or_skip()
    try:
        text = read_upstream_file(repo, pin, ".claude/skills/ai-changelog/SKILL.md")
    except UpstreamUnavailable as exc:
        pytest.skip(f"upstream checkout unusable: {exc}")
    _assert_carried(
        "changelog types",
        set(_TABLE_CODE_RE.findall(text)),
        set(checks.CHANGELOG_TYPES),
    )


def test_upstream_hypothesis_categories_are_all_carried() -> None:
    repo, pin = _upstream_or_skip()
    try:
        text = read_upstream_file(
            repo, pin, ".claude/skills/ai-improvement-tracker/SKILL.md"
        )
    except UpstreamUnavailable as exc:
        pytest.skip(f"upstream checkout unusable: {exc}")
    _assert_carried(
        "hypothesis categories",
        set(_TABLE_BOLD_RE.findall(text)),
        set(checks.HYPOTHESIS_CATEGORIES),
    )


def test_upstream_learnings_sections_are_all_carried() -> None:
    """Pairs, not headers: a header carried under a changed slug still breaks the lint."""
    repo, pin = _upstream_or_skip()
    try:
        text = read_upstream_file(
            repo, pin, ".claude/skills/task-learnings/references/learnings-format.md"
        )
    except UpstreamUnavailable as exc:
        pytest.skip(f"upstream checkout unusable: {exc}")
    upstream_pairs = {f"{h} -> {s}" for h, s in _LEARNINGS_ROW_RE.findall(text)}
    kit_pairs = {f"{h} -> {s}" for h, s in checks.LEARNINGS_SECTIONS.items()}
    _assert_carried("learnings sections", upstream_pairs, kit_pairs)


def test_upstream_handoff_contract_is_all_carried() -> None:
    """Sections and statuses are parsed OUT of upstream, not filtered against our own set.

    Filtering a candidate list taken from `checks.py` would make this pass by construction
    -- upstream could add a sixth required section and the assertion could never see it.
    That is the defect class this section exists to close, so the parse has to be able to
    return something the kit does not have.
    """
    repo, pin = _upstream_or_skip()
    try:
        text = read_upstream_file(
            repo, pin, ".claude/skills/parallel-session-safety/SKILL.md"
        )
    except UpstreamUnavailable as exc:
        pytest.skip(f"upstream checkout unusable: {exc}")

    _assert_carried(
        "handoff sections",
        set(_UPSTREAM_HANDOFF_SECTION_RE.findall(text)),
        set(checks.HANDOFF_REQUIRED_SECTIONS),
    )

    status_row = _UPSTREAM_HANDOFF_STATUS_ROW_RE.search(text)
    assert status_row is not None, (
        "no `## Status` contract row found in upstream parallel-session-safety/SKILL.md -- "
        "the document moved and this parse needs updating rather than deleting."
    )
    _assert_carried(
        "handoff statuses",
        set(_BACKTICKED_SLUG_RE.findall(status_row.group(1))),
        set(checks.HANDOFF_STATUSES),
    )


def test_upstream_hypothesis_statuses_are_all_carried() -> None:
    """The fifth of the family, and it completes it.

    An earlier draft of the hand-off filed this as owed on the stated grounds that upstream's
    counterpart is a live data file with no clean parse. That was asserted, not checked, and it
    is false: upstream's `.ai/improvement-hypotheses.md` carries the same `Status lifecycle:`
    line the shipped seed does, so the same two patterns read both sides.
    """
    repo, pin = _upstream_or_skip()
    try:
        text = read_upstream_file(repo, pin, ".ai/improvement-hypotheses.md")
    except UpstreamUnavailable as exc:
        pytest.skip(f"upstream checkout unusable: {exc}")

    lifecycle = _LIFECYCLE_RE.search(text)
    assert lifecycle is not None, (
        "no `Status lifecycle:` line in upstream's improvement-hypotheses.md -- the document "
        "moved and this parse needs updating rather than deleting."
    )
    _assert_carried(
        "hypothesis statuses",
        set(_STATUS_TOKEN_RE.findall(lifecycle.group(1))),
        set(checks.HYPOTHESIS_STATUSES),
    )
