"""Project checks the shipped skills invoke: the `.ai/` data-file lint and the skill audit.

Two upstream scripts became CLI subcommands here, per the I2 Gate B decision: ship
skill-owned scripts inside their skill, and substitute a CLI subcommand only where no
portable idiom exists. A script a skill calls *for itself* needs no substitution --
`session-retrospective` already ships its extractor and calls it through
`${CLAUDE_SKILL_DIR}`. What has no portable idiom is the CROSS-skill call: that variable
resolves to the *calling* skill's directory, so it cannot address a sibling skill's
script, and a project-relative skills path is broken by construction under plugin
distribution (the hygiene contract bans it outright). Those calls come here:

- `lint`         <- the 6 sites that called `learning-consolidator`'s `ai_files_lint.py`
- `audit-skills` <- the 3 sites that called `skill-reviewer`'s `audit_skills.py`

Both are read-only, stdlib-only, and write nothing, so they are safe to run from parallel
sessions. Three portability rules hold throughout, because this code has to work on
Windows, macOS and Linux where the originals only ever ran on one:

1. **Every emitted line is ASCII.** A legacy code-page console raises on an em-dash, and
   a lint that crashes while reporting is worse than no lint.
2. **Every path printed is relative to the project root.** This output gets pasted into
   hand-offs and retrospectives, where an absolute path is portable to one machine.
3. **Nothing is anchored on `__file__`.** Installed as a plugin, this module sits in a
   package cache with no ancestor inside the adopter's project, so the working directory
   is the only sound anchor.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lemmi_ai_kit.manifest import ManifestError, load_manifest

# --- shared -------------------------------------------------------------------------------

# `.ai` before `.git`: it is what these checks read, and in a monorepo the checkout root
# can sit above the project that owns the `.ai/` pipeline.
_PROJECT_MARKERS: tuple[str, ...] = (".ai", ".git")


def find_project_root(start: Path | None = None) -> Path:
    """Nearest ancestor of `start` holding a project marker; `start` itself if none does."""
    base = (start or Path.cwd()).resolve()
    candidates = (base, *base.parents)
    for marker in _PROJECT_MARKERS:
        for candidate in candidates:
            if (candidate / marker).is_dir():
                return candidate
    return base


def read_text(path: Path) -> str:
    """Read a text file the way a lint must: never crash, never trip over a byte-order mark.

    `utf-8-sig` strips a BOM when one is present and is a no-op when it is not. A file
    written by a Windows editor can carry one, and a BOM left in place silently breaks the
    very first line's `## heading` or `---` match. `errors="replace"` keeps a mis-encoded
    file reportable rather than fatal.
    """
    return path.read_text(encoding="utf-8-sig", errors="replace")


def ascii_safe(text: str) -> str:
    """Replace non-ASCII so our own output cannot crash a legacy code-page console.

    Applied at the print boundary rather than by reconfiguring `sys.stdout`: mutating
    global stream state breaks the caller's own output capture, and the only non-ASCII we
    ever emit is quoted out of the files being checked.
    """
    return text.encode("ascii", "replace").decode("ascii")


def display_path(path: Path, root: Path) -> str:
    """POSIX-style path relative to `root`, falling back to the bare filename."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def shipped_skill_names() -> frozenset[str] | None:
    """Names in the bundled catalog, or `None` when it cannot be read.

    A malformed bundled manifest must not take the audit down with it: these checks are
    about the adopter's project, and the catalog only supplies context for one direction of
    the registration check. `None` and an empty set are deliberately different answers --
    "I do not know what the plugin ships" must not be read as "the plugin ships nothing",
    which would report every plugin skill in a CLAUDE.md index as a ghost listing.
    """
    try:
        return frozenset(entry.name for entry in load_manifest().skills)
    except (ManifestError, OSError):
        return None


@dataclass(frozen=True)
class LintFinding:
    """One `.ai` lint result. A `note` is reported but never fails the run."""

    where: str
    line: int
    message: str
    note: bool = False


# --- vocabularies -------------------------------------------------------------------------
#
# These mirror the taxonomies the shipped skills document, NOT the source project's. Three
# upstream rules were deliberately dropped rather than ported, because each encodes that
# project's policy rather than anything an adopter agreed to: a hardcoded 2026 policy
# cutoff (replaced by `--since`), a name-matched allowlist of that project's own
# historical entries, and a 12th changelog type added by one of its decision records.
# `tests/test_checks.py` pins each set below to the skill that teaches it, so a refresh
# that changes a taxonomy cannot leave this file behind.

CHANGELOG_TYPES: frozenset[str] = frozenset(
    {
        "SKILL-ADDED",
        "SKILL-MODIFIED",
        "SKILL-REMOVED",
        "CONV-ADDED",
        "CONV-MODIFIED",
        "RULE-ADDED",
        "RULE-MODIFIED",
        "WORKFLOW-MODIFIED",
        "INFRA-ADDED",
        "INFRA-MODIFIED",
        "CONSOLIDATION",
    }
)
CHANGELOG_REQUIRED_FIELDS: tuple[str, ...] = (
    "What",
    "Why",
    "Files",
    "Affected workflows",
)

HYPOTHESIS_CATEGORIES: frozenset[str] = frozenset(
    {
        "Consistency",
        "Speed",
        "Quality",
        "Cognitive Load",
        "Knowledge Retention",
        "Coverage",
        "Observability",
    }
)
# Shapes the hint in a message only -- never whether an entry passes. Naming the category
# the author probably meant is the difference between a fixed entry and an ignored lint.
CATEGORY_SYNONYMS: dict[str, str] = {
    "Reliability": "Quality",
    "Maintainability": "Quality",
    "Efficiency": "Speed",
    "Reusability": "Coverage",
}
HYPOTHESIS_STATUSES: tuple[str, ...] = (
    "PENDING",
    "CONFIRMED",
    "REFUTED",
    "INCONCLUSIVE",
    "SUPERSEDED",
)
# `Risk` is documented as "optional but encouraged", so it is not required here.
HYPOTHESIS_REQUIRED_FIELDS: tuple[str, ...] = (
    "Category",
    "Hypothesis",
    "Signal",
    "Status",
    "Changelog ref",
)

LEARNINGS_SECTIONS: dict[str, str] = {
    "Architecture Decisions": "architecture",
    "Common Pitfalls": "pitfall",
    "External Service Quirks": "external-api",
    "Performance Insights": "performance",
    "Pattern Discoveries": "pattern",
    "Convention Clarifications": "convention",
}
LEARNINGS_REQUIRED_FIELDS: tuple[str, ...] = (
    "Context",
    "Finding",
    "Impact",
    "Category",
)

HANDOFF_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Scope",
    "Durable anchors",
    "Preconditions",
    "Verification",
    "Status",
)
HANDOFF_COMMAND_SECTIONS: tuple[str, ...] = ("Preconditions", "Verification")
HANDOFF_STATUSES: tuple[str, ...] = ("in-progress", "blocked", "ready-for-review")

# --- parsing ------------------------------------------------------------------------------

DATE_HEADING_RE = re.compile(r"^## (\d{4})-(\d{2})-(\d{2})\s*$")
ANY_H2_RE = re.compile(r"^## (.+?)\s*$")
ENTRY_RE = re.compile(r"^### (.+?)\s*$")
LEARNING_TITLE_RE = re.compile(r"^\[(\d{4})-(\d{2})-(\d{2})\]\s+\S")
TYPE_TAG_RE = re.compile(r"^([A-Z][A-Z-]+):")
HYP_TAG_RE = re.compile(r"^\[([A-Z][A-Z-]+)\]")
# Both bullet shapes the skills use: `- **What:** x` and `- **Context**: x`.
FIELD_RE = re.compile(r"^- \*\*(.+?):?\*\*:?\s*(.*)$")
REF_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
# Entries legitimately quote headings inside code spans; strip those before looking for
# splice damage, or every entry that documents the format reports itself.
INLINE_CODE_RE = re.compile(r"`[^`]*`")
# Only ENTRY-shaped headings, never a bare `###`: a `###` in prose is a false positive, and
# a lint people learn to ignore is worse than the corruption it catches.
EMBEDDED_HEADING_RE = re.compile(
    r"###\s+(?:\[\d{4}-\d{2}-\d{2}\]|\[[A-Z][A-Z-]+\]|[A-Z][A-Z-]{2,}:)"
)


FENCE_RE = re.compile(r"^\s*(?:```|~~~)")


def _fence_mask(lines: Sequence[str]) -> list[bool]:
    """True for every line inside a fenced code block, the fence markers included.

    These files document their own format, so a fenced example is a date heading, an
    entry, or a field bullet -- exactly the shapes every check below looks for. Parsing
    them as real content produced three separate false-positive classes: a fenced `##`
    date split its entry (losing the fields below it), a fenced `### TYPE:` became a
    phantom entry, and fenced field bullets read as a duplicated field block. All three
    reported a *conforming* entry as broken, which is the failure mode that teaches people
    to ignore a lint.

    One definition, used by every reader of these files -- the audit's link check grew its
    own inline fence toggle first, and a second notion of "fenced" is how they drift.
    """
    mask: list[bool] = []
    inside = False
    for line in lines:
        if FENCE_RE.match(line) is not None:
            mask.append(True)
            inside = not inside
            continue
        mask.append(inside)
    return mask


def _parse_date(year: str, month: str, day: str) -> date | None:
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


@dataclass(frozen=True)
class Entry:
    """One `### ` entry: its title, its line, and the body lines beneath it."""

    title: str
    line: int
    body: tuple[str, ...]


@dataclass(frozen=True)
class Block:
    """One `## ` section and the entries filed under it."""

    heading: str
    line: int
    entries: tuple[Entry, ...]

    def heading_date(self) -> date | None:
        match = DATE_HEADING_RE.match(f"## {self.heading}")
        return _parse_date(*match.groups()) if match else None


def parse_blocks(text: str) -> list[Block]:
    """Split a data file into `## ` sections, each holding its `### ` entries."""
    blocks: list[Block] = []
    heading: str | None = None
    heading_line = 0
    entries: list[Entry] = []
    title: str | None = None
    title_line = 0
    body: list[str] = []

    def close_entry() -> None:
        nonlocal title
        if title is not None:
            entries.append(Entry(title, title_line, tuple(body)))
            title = None

    def close_block() -> None:
        nonlocal heading
        close_entry()
        if heading is not None:
            blocks.append(Block(heading, heading_line, tuple(entries)))
            heading = None

    lines = text.splitlines()
    fenced = _fence_mask(lines)
    for index, line in enumerate(lines):
        lineno = index + 1
        if fenced[index]:
            # Inside a fence this is example text, not structure -- but it is still part
            # of the entry it sits in, so it stays in the body.
            if title is not None:
                body.append(line)
            continue
        h2 = ANY_H2_RE.match(line)
        if h2:
            close_block()
            heading, heading_line, entries = h2.group(1), lineno, []
            continue
        entry = ENTRY_RE.match(line)
        if entry:
            close_entry()
            title, title_line, body = entry.group(1), lineno, []
            continue
        if title is not None:
            body.append(line)
    close_block()
    return blocks


def fields_of(body: tuple[str, ...]) -> dict[str, str]:
    """Map of `**Field:**` bullet name -> the first value seen for it."""
    out: dict[str, str] = {}
    for line in body:
        match = FIELD_RE.match(line.strip())
        if match is None:
            continue
        name = match.group(1).rstrip(":")
        if name not in out:
            out[name] = match.group(2)
    return out


# --- structural checks (always file-wide, never gated by --since) --------------------------
#
# Append and merge damage predates no cutoff: a grandfathered entry can be corrupted by a
# bad merge exactly as easily as a current one, so these run over every entry regardless of
# date. Only the per-entry FORMAT checks below honour `--since`.


def check_date_headings(blocks: list[Block], where: str) -> list[LintFinding]:
    """Every `## ` heading must be a real date, in strictly reverse-chronological order."""
    findings: list[LintFinding] = []
    previous: date | None = None
    for block in blocks:
        match = DATE_HEADING_RE.match(f"## {block.heading}")
        if match is None:
            findings.append(
                LintFinding(
                    where,
                    block.line,
                    f"heading '## {block.heading}' is not a YYYY-MM-DD date",
                )
            )
            continue
        current = _parse_date(*match.groups())
        if current is None:
            findings.append(
                LintFinding(
                    where,
                    block.line,
                    f"heading '## {block.heading}' is not a real calendar date",
                )
            )
            continue
        if previous is not None:
            if current > previous:
                findings.append(
                    LintFinding(
                        where,
                        block.line,
                        f"date heading {current} appears BELOW older heading {previous} "
                        "(reverse-chronological order violated)",
                    )
                )
            elif current == previous:
                findings.append(
                    LintFinding(where, block.line, f"duplicate date heading {current}")
                )
        previous = current
    return findings


def check_entry_body_integrity(
    blocks: list[Block], where: str, required_fields: tuple[str, ...]
) -> list[LintFinding]:
    """Catch the append damage the required-field checks structurally cannot see.

    Two shapes, both seen in the wild:

    1. A heading spliced INTO a field line. Two appends get unioned onto one line, so the
       second entry loses its `###` and becomes headless -- its fields are then collected
       as the *previous* entry's body, satisfying that entry's required-field check while
       the swallowed entry is invisible to every heading-based check and to the counter.
    2. A duplicated field block (double append). `fields_of` keeps only the first
       occurrence of each name, so the second block is silently ignored.
    """
    findings: list[LintFinding] = []
    for block in blocks:
        for entry in block.entries:
            counts: dict[str, int] = {}
            body_fenced = _fence_mask(entry.body)
            for offset, raw in enumerate(entry.body, start=1):
                if body_fenced[offset - 1]:
                    continue  # a fenced example of the format is not a second copy of it
                if EMBEDDED_HEADING_RE.search(INLINE_CODE_RE.sub("", raw)):
                    findings.append(
                        LintFinding(
                            where,
                            entry.line + offset,
                            f"entry '{entry.title[:50]}' has a heading spliced into a "
                            "field line -- the swallowed entry is headless (append damage)",
                        )
                    )
                match = FIELD_RE.match(raw.strip())
                if match is None:
                    continue
                name = match.group(1).rstrip(":")
                if name in required_fields:
                    counts[name] = counts.get(name, 0) + 1
            for name, seen in sorted(counts.items()):
                if seen > 1:
                    findings.append(
                        LintFinding(
                            where,
                            entry.line,
                            f"entry '{entry.title[:50]}' repeats required field "
                            f"'{name}' {seen}x (duplicate field block -- double append)",
                        )
                    )
    return findings


def check_orphan_entries(text: str, where: str) -> list[LintFinding]:
    """Entries sitting above the first `## ` heading, which no other check can see.

    `parse_blocks` files entries under headings, so an entry that precedes the first
    heading belongs to no block at all -- invisible to the required-field, taxonomy and
    date checks. The file lints clean while the entry is broken, which is the same silent
    under-reporting a byte-order mark causes, reached by a different route: a bad append,
    or a heading deleted out from over its entries.
    """
    lines = text.splitlines()
    fenced = _fence_mask(lines)
    findings: list[LintFinding] = []
    for index, line in enumerate(lines):
        if fenced[index]:
            continue
        if ANY_H2_RE.match(line) is not None:
            break
        entry = ENTRY_RE.match(line)
        if entry is not None:
            findings.append(
                LintFinding(
                    where,
                    index + 1,
                    f"entry '{entry.group(1)[:60]}' appears above the first '## ' "
                    "heading, so it is filed under no section and every heading-based "
                    "check skips it",
                )
            )
    return findings


def _in_policy(entry_date: date | None, since: date | None) -> bool:
    """Does this entry fall inside the per-entry format policy?

    With no `--since` -- the default, and the only correct one for a project that adopted
    the kit and started its files empty -- every entry is in policy. Given a cutoff, an
    entry with no parseable date is treated as OUT of policy: there is no way to tell which
    side of the line it falls on, and guessing would fail entries the adopter excluded.
    """
    if since is None:
        return True
    return entry_date is not None and entry_date >= since


# --- per-file lints -----------------------------------------------------------------------


def lint_changelog(
    text: str, where: str, since: date | None = None
) -> list[LintFinding]:
    blocks = parse_blocks(text)
    findings = check_orphan_entries(text, where)
    findings += check_date_headings(blocks, where)
    findings += check_entry_body_integrity(blocks, where, CHANGELOG_REQUIRED_FIELDS)
    for block in blocks:
        heading_date = block.heading_date()
        for entry in block.entries:
            if not _in_policy(heading_date, since):
                continue
            tag = TYPE_TAG_RE.match(entry.title)
            if tag is None:
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"entry '{entry.title[:60]}' has no 'TYPE:' prefix",
                    )
                )
            elif tag.group(1) not in CHANGELOG_TYPES:
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"type '{tag.group(1)}' is not one of the "
                        f"{len(CHANGELOG_TYPES)} in the locked taxonomy",
                    )
                )
            present = fields_of(entry.body)
            for field in CHANGELOG_REQUIRED_FIELDS:
                if field not in present:
                    findings.append(
                        LintFinding(
                            where, entry.line, f"entry missing required field '{field}'"
                        )
                    )
    return findings


def lint_hypotheses(
    text: str, where: str, since: date | None = None
) -> list[LintFinding]:
    blocks = parse_blocks(text)
    findings = check_orphan_entries(text, where)
    findings += check_date_headings(blocks, where)
    findings += check_entry_body_integrity(blocks, where, HYPOTHESIS_REQUIRED_FIELDS)
    for block in blocks:
        heading_date = block.heading_date()
        for entry in block.entries:
            present = fields_of(entry.body)
            # STRUCTURAL: an entry must not be filed under a heading older than its ref.
            ref_match = REF_DATE_RE.search(present.get("Changelog ref", ""))
            if ref_match is not None and heading_date is not None:
                ref_date = _parse_date(*ref_match.groups())
                if ref_date is not None and ref_date > heading_date:
                    findings.append(
                        LintFinding(
                            where,
                            entry.line,
                            f"entry ref-dated {ref_date} is misfiled under older heading "
                            f"{heading_date} (re-file under its own date heading)",
                        )
                    )
            if not _in_policy(heading_date, since):
                continue
            tag = HYP_TAG_RE.match(entry.title)
            if tag is None:
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"entry '{entry.title[:60]}' has no '[TYPE]' tag",
                    )
                )
            elif tag.group(1) not in CHANGELOG_TYPES:
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"type tag '[{tag.group(1)}]' is not one of the "
                        f"{len(CHANGELOG_TYPES)} in the locked taxonomy",
                    )
                )
            for field in HYPOTHESIS_REQUIRED_FIELDS:
                if field not in present:
                    findings.append(
                        LintFinding(
                            where, entry.line, f"entry missing required field '{field}'"
                        )
                    )
            category = present.get("Category", "").strip()
            if category:
                if "/" in category or "," in category:
                    findings.append(
                        LintFinding(
                            where,
                            entry.line,
                            f"compound category '{category}' -- exactly ONE primary "
                            "category; put the secondary angle in prose",
                        )
                    )
                elif category not in HYPOTHESIS_CATEGORIES:
                    hint = CATEGORY_SYNONYMS.get(category)
                    suffix = f" (use '{hint}')" if hint else ""
                    findings.append(
                        LintFinding(
                            where,
                            entry.line,
                            f"category '{category}' is not one of the closed "
                            f"{len(HYPOTHESIS_CATEGORIES)}{suffix}",
                        )
                    )
            status = present.get("Status", "").strip()
            if status and status not in HYPOTHESIS_STATUSES:
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"status '{status[:40]}' is not exactly one of "
                        f"{list(HYPOTHESIS_STATUSES)}; partial evidence belongs in a "
                        "'Validation notes:' sub-field with Status staying PENDING",
                    )
                )
    return findings


def lint_learnings(
    text: str, where: str, since: date | None = None
) -> list[LintFinding]:
    """Lint the intake buffer. Sections are topic names here, not dates."""
    blocks = parse_blocks(text)
    findings = check_orphan_entries(text, where)
    findings += check_entry_body_integrity(blocks, where, LEARNINGS_REQUIRED_FIELDS)
    for block in blocks:
        canonical = block.heading in LEARNINGS_SECTIONS
        if not canonical:
            findings.append(
                LintFinding(
                    where,
                    block.line,
                    f"non-canonical section '## {block.heading}' tolerated until drained",
                    note=True,
                )
            )
        for entry in block.entries:
            title_match = LEARNING_TITLE_RE.match(entry.title)
            entry_date = _parse_date(*title_match.groups()[:3]) if title_match else None
            present = fields_of(entry.body)
            slug = present.get("Category", "").strip().strip("`")
            # STRUCTURAL: inside a canonical section the slug must match that section.
            if (
                canonical
                and slug
                and slug in LEARNINGS_SECTIONS.values()
                and slug != LEARNINGS_SECTIONS[block.heading]
            ):
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"entry slug '{slug}' does not match its section "
                        f"'## {block.heading}' (expected "
                        f"'{LEARNINGS_SECTIONS[block.heading]}')",
                    )
                )
            if not _in_policy(entry_date, since):
                continue
            if title_match is None:
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"entry title '{entry.title[:60]}' is not '[YYYY-MM-DD] title'",
                    )
                )
            for field in LEARNINGS_REQUIRED_FIELDS:
                if field not in present:
                    findings.append(
                        LintFinding(
                            where, entry.line, f"entry missing required field '{field}'"
                        )
                    )
            if slug and slug not in LEARNINGS_SECTIONS.values():
                # The count is derived, never spelled out: a literal here is what breaks
                # the day a seventh category is added.
                findings.append(
                    LintFinding(
                        where,
                        entry.line,
                        f"category slug '{slug}' is not one of the canonical "
                        f"{len(LEARNINGS_SECTIONS)}",
                    )
                )
    return findings


# --- hand-offs ----------------------------------------------------------------------------
#
# Unlike the other three targets this is a DIRECTORY, and it is normally gitignored:
# hand-offs are deliberately local. That is exactly why the contract exists -- an untracked
# note must be a POINTER to git, never the only copy of a fact.

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
BACKTICK_RE = re.compile(r"`([^`]+)`")
# A git-resolvable anchor: a SHA-ish hex run, or anything path- or branch-shaped.
GIT_ANCHOR_RE = re.compile(r"^(?:[0-9a-f]{7,40}|[^\s`]*/[^\s`]*)$")
BRACE_EXPANSION_RE = re.compile(r"[{}]")
PATH_LINE_SUFFIX_RE = re.compile(r":\d+$")
SECTION_RE = re.compile(r"^## (.+)$")


def _handoff_sections(text: str) -> tuple[dict[str, list[tuple[int, str]]], list[str]]:
    """`({section: [(lineno, line)]}, duplicate section names)`.

    HTML comments are blanked -- they hold deliberately-bad teaching examples -- but their
    newlines are kept so reported line numbers stay true. Duplicates are returned rather
    than silently overwritten: a second `## Status` would otherwise hide the first from
    every check, the same defect `check_entry_body_integrity` catches elsewhere.
    """
    text = HTML_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    sections: dict[str, list[tuple[int, str]]] = {}
    duplicates: list[str] = []
    current: str | None = None
    lines = text.splitlines()
    fenced = _fence_mask(lines)
    for index, line in enumerate(lines):
        lineno = index + 1
        if fenced[index]:
            # A fenced `## Status` example must not become a phantom (or duplicate)
            # section, but it is still body text of the section it sits in.
            if current is not None and current in sections:
                sections[current].append((lineno, line))
            continue
        match = SECTION_RE.match(line)
        if match is not None:
            heading: str = match.group(1).strip()
            current = heading
            if heading in sections:
                duplicates.append(heading)
            else:
                sections[heading] = []
        elif current is not None and current in sections:
            sections[current].append((lineno, line))
    return sections, duplicates


def _anchor_probe_token(token: str) -> str:
    """Reduce an anchor to what git could actually resolve, or `''` when nothing can.

    Two real-world forms are not single git objects and must not be probed as one: a shell
    brace expansion (naming several files, none of them literal) and a `path:line` citation
    (the file exists, the suffix does not).
    """
    if BRACE_EXPANSION_RE.search(token):
        return ""
    return PATH_LINE_SUFFIX_RE.sub("", token)


def _git_anchor_resolves(token: str, root: Path) -> bool | None:
    """Does `token` name something git can find? `None` when undecidable.

    `None` covers "git is unavailable, or this is not a checkout" -- the lint has to stay
    runnable outside a clone. A token is accepted if it resolves as a revision (SHA,
    branch, tag) or names a path git knows at HEAD or that exists on disk; hand-offs anchor
    on all of those. `--` guards the path form so a token containing `:` cannot be reparsed
    as a revision, and `MSYS_NO_PATHCONV` stops a Git-for-Windows shell rewriting slashes.
    """
    if not token:
        return None
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}

    def ok(args: list[str]) -> bool | None:
        try:
            completed = subprocess.run(
                args, cwd=root, capture_output=True, env=env, timeout=10, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.returncode == 0

    if ok(["git", "rev-parse", "--git-dir"]) is not True:
        return None
    if ok(["git", "rev-parse", "--verify", "--quiet", f"{token}^{{commit}}"]):
        return True
    if (
        ok(["git", "ls-tree", "-r", "--name-only", "HEAD", "--", token])
        and (root / token).exists()
    ):
        return True
    # A path that exists but is untracked still anchors a hand-off usefully.
    return (root / token).exists()


def lint_handoff(text: str, where: str, root: Path | None = None) -> list[LintFinding]:
    """Lint ONE hand-off file. Pass `root` to resolve its anchors against git."""
    findings: list[LintFinding] = []
    sections, duplicates = _handoff_sections(text)

    for name in HANDOFF_REQUIRED_SECTIONS:
        if name not in sections:
            findings.append(
                LintFinding(where, 1, f"missing required section '## {name}'")
            )
    for name in duplicates:
        findings.append(
            LintFinding(
                where, 1, f"duplicate section '## {name}' (the second hides the first)"
            )
        )

    # Preconditions and verification must be runnable: a backticked command AND its
    # expected result after '->'. A prose state claim is the defect the contract exists to
    # stop -- it is exactly the unreliable brief that made hand-offs need a contract.
    for name in HANDOFF_COMMAND_SECTIONS:
        bullets = [
            (lineno, line)
            for lineno, line in sections.get(name, [])
            if line.lstrip().startswith("- ")
        ]
        if name in sections and not bullets:
            findings.append(LintFinding(where, 1, f"'## {name}' has no entries"))
        for lineno, line in bullets:
            if BACKTICK_RE.search(line) is None:
                findings.append(
                    LintFinding(
                        where,
                        lineno,
                        f"'## {name}' entry is prose, not a runnable command: "
                        f"{line.strip()[:60]!r}",
                    )
                )
            elif "->" not in line:
                findings.append(
                    LintFinding(
                        where,
                        lineno,
                        f"'## {name}' entry has no expected result (use '-> result'): "
                        f"{line.strip()[:60]!r}",
                    )
                )

    # Durable anchors must carry at least one git-resolvable reference. A hand-off whose
    # facts exist nowhere in git loses the work, not just the note.
    if "Durable anchors" in sections:
        anchors = [
            (lineno, token)
            for lineno, line in sections["Durable anchors"]
            for token in BACKTICK_RE.findall(line)
            if GIT_ANCHOR_RE.match(token.strip())
        ]
        if not anchors:
            findings.append(
                LintFinding(
                    where,
                    1,
                    "'## Durable anchors' has no git-resolvable reference "
                    "(branch, SHA, or path)",
                )
            )
        # Shape is not existence: `deadbee` and `does/not/exist` both match the shape, and
        # a pointer that does not resolve is the exact failure the contract prevents. But
        # this is a NOTE, deliberately -- any 7-40 char hex string is shape-identical to a
        # short SHA, so an identifier that merely looks like one would hard-fail forever,
        # and a validator whose own corpus fails trains authors to ignore it. Off by
        # default too: it shells out per anchor, so the caller opts in.
        for lineno, token in anchors if root is not None else []:
            if (
                _git_anchor_resolves(_anchor_probe_token(token), root or Path.cwd())
                is False
            ):
                findings.append(
                    LintFinding(
                        where,
                        lineno,
                        f"anchor {token!r} does not resolve in git -- a dead pointer, or "
                        "an identifier that only looks like a SHA; confirm it",
                        note=True,
                    )
                )

    if "Status" in sections:
        body = " ".join(line for _, line in sections["Status"])
        if not any(status in body for status in HANDOFF_STATUSES):
            findings.append(
                LintFinding(
                    where,
                    1,
                    f"'## Status' must state one of {'/'.join(HANDOFF_STATUSES)}",
                )
            )
    return findings


# --- targets ------------------------------------------------------------------------------

# The public target names. `plans` is deliberately absent: the execution-plan lint belongs
# to an initiative-planning convention the kit does not ship yet, and adding a target later
# is additive where removing one is a breaking change.
LINT_TARGETS: tuple[str, ...] = ("learnings", "changelog", "hypotheses", "handoffs")

_FILE_TARGETS: dict[str, str] = {
    "learnings": ".ai/learnings.md",
    "changelog": ".ai/ai-changelog.md",
    "hypotheses": ".ai/improvement-hypotheses.md",
}
_HANDOFF_DIR = ".ai/handoffs"


def target_path(target: str, root: Path) -> Path:
    """Filesystem path of a lint target inside `root`.

    Raises on an unknown name rather than defaulting. Argparse `choices` guards the CLI,
    but these are library functions: a target added to `LINT_TARGETS` without a path here
    would otherwise resolve silently to the wrong file.
    """
    if target == "handoffs":
        return root.joinpath(*_HANDOFF_DIR.split("/"))
    relative = _FILE_TARGETS.get(target)
    if relative is None:
        raise ValueError(f"unknown lint target: {target!r}")
    return root.joinpath(*relative.split("/"))


_FILE_LINTS = {
    "learnings": lint_learnings,
    "changelog": lint_changelog,
    "hypotheses": lint_hypotheses,
}


def lint_file(
    target: str, text: str, where: str, since: date | None
) -> list[LintFinding]:
    """Dispatch one of the three data files to its lint. Raises on any other target."""
    lint = _FILE_LINTS.get(target)
    if lint is None:
        raise ValueError(f"not a data-file lint target: {target!r}")
    return lint(text, where, since)


def lint_handoff_dir(
    root: Path, resolve_anchors: bool = False
) -> tuple[list[LintFinding], int]:
    """Lint every hand-off in `.ai/handoffs/`. Returns `(findings, files scanned)`.

    A missing directory is a NO-OP, never an error: a project with no hand-offs yet must
    not fail its lint. Every `*.md` is linted -- upstream gates on an opt-in marker because
    it has pre-contract files on disk, whereas an adopter starts clean and a lint that
    silently passes everything is worse than none. `README.md` is the one exception, since
    a directory note is not a hand-off.
    """
    directory = target_path("handoffs", root)
    if not directory.is_dir():
        return [], 0
    findings: list[LintFinding] = []
    scanned = 0
    for path in sorted(directory.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        scanned += 1
        findings += lint_handoff(
            read_text(path),
            display_path(path, root),
            root if resolve_anchors else None,
        )
    return findings, scanned


# --- entry inventory (`--list-entries`) ---------------------------------------------------

_LIST_ENTRY_RE = re.compile(r"^### (.*)$", re.MULTILINE)
_LIST_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def _numbered(pattern: re.Pattern[str], text: str) -> list[tuple[int, str]]:
    return [
        (text.count("\n", 0, m.start()) + 1, m.group(1)) for m in pattern.finditer(text)
    ]


def inventory(text: str, where: str) -> list[str]:
    """Per-section counts plus every `line<TAB>title`, for eyeballing a file's contents."""
    entries = _numbered(_LIST_ENTRY_RE, text)
    sections = _numbered(_LIST_SECTION_RE, text)
    lines = [
        f"FILE: {where}  lines={text.count(chr(10)) + 1}  "
        f"entries={len(entries)}  sections={len(sections)}"
    ]
    # An entry above the first section is counted in the total but belongs to no section,
    # so without this row the per-section counts silently fail to add up to it.
    orphans = sum(1 for line, _ in entries if not sections or line < sections[0][0])
    if orphans:
        lines.append(f"  (above the first section)  entries={orphans}")
    bounds = [line for line, _ in sections] + [10**9]
    for index, (line, name) in enumerate(sections):
        count = sum(
            1 for entry_line, _ in entries if line < entry_line < bounds[index + 1]
        )
        lines.append(f"  ## {name}  (line {line})  entries={count}")
    lines.append("--- ENTRIES ---")
    lines += [f"{line}\t{title}" for line, title in entries]
    return lines


# --- `audit-skills` -----------------------------------------------------------------------

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_TYPES: frozenset[str] = frozenset({"task", "reference", "review", "workflow"})
# Spec limits, not project policy: a description over the per-skill cap is rejected, and a
# description plus when_to_use over the listing cap is silently truncated in the menu.
SPEC_DESCRIPTION_MAX = 1024
LISTING_CAP = 1536
# The cap the skill-authoring skills teach: past this, detail belongs in `references/`.
MAX_SKILL_LINES = 500

# Machine-specific path shapes. The macOS and Linux home patterns are written as one
# alternation so this module's own source does not contain the literal string it bans.
PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]"),
    re.compile(r"/(?:Users|home)/\w"),
    re.compile(r"projects/[a-z]--"),
)
# Lines that document the rule, and redaction or path-encoding fixtures, are the allowed
# matches. A fixture sits NEXT TO its redact/encode call, so the marker is searched in a
# window around the match rather than only on the matching line.
PATH_ALLOW_MARKERS: tuple[str, ...] = (
    "redact",
    "encode",
    "session_dir",
    "drive-letter",
    "machine-specific",
    "hardcoded",
)
PATH_ALLOW_WINDOW = 3

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
AUDITED_SUFFIXES: frozenset[str] = frozenset({".md", ".py", ".sh", ".txt", ".json"})

SEVERITIES: tuple[str, ...] = ("BLOCKER", "MAJOR", "MINOR", "NOTE", "INFO")

FrontmatterValue = str | dict[str, str]
Frontmatter = dict[str, FrontmatterValue]

_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")
_NESTED_KEY_RE = re.compile(r"^\s+([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")
_FOLD_MARKERS: frozenset[str] = frozenset({">", ">-", "|", "|-"})


@dataclass(frozen=True)
class AuditFinding:
    """One skill-audit result, at one of `SEVERITIES`."""

    severity: str
    skill: str
    message: str


def parse_frontmatter(text: str) -> tuple[Frontmatter | None, str | None]:
    """Bounded YAML-subset parse: flat keys, folded scalars, one nested level.

    Returns `(fields, error)`. Mirrors the failure mode that actually matters -- an
    unparseable block means the body loads with EMPTY metadata, so `/name` still works
    while auto-matching dies silently.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "no opening --- frontmatter delimiter"
    fields: Frontmatter = {}
    nested: str | None = None
    index, total = 1, len(lines)
    while index < total:
        line = lines[index]
        if line.strip() == "---":
            return fields, None
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        top = _TOP_KEY_RE.match(line)
        if top is not None:
            key, value = top.group(1), top.group(2).strip()
            nested = None
            if value in _FOLD_MARKERS:
                folded: list[str] = []
                index += 1
                while index < total and (
                    not lines[index].strip() or lines[index].startswith((" ", "\t"))
                ):
                    if lines[index].strip() == "---":
                        break
                    folded.append(lines[index].strip())
                    index += 1
                fields[key] = " ".join(part for part in folded if part)
                continue
            if value == "":
                fields[key] = {}
                nested = key
            else:
                fields[key] = value.strip("\"'")
            index += 1
            continue
        child = _NESTED_KEY_RE.match(line)
        if child is not None and nested is not None:
            parent = fields.get(nested)
            if isinstance(parent, dict):
                parent[child.group(1)] = child.group(2).strip().strip("\"'")
        # Any other shape is tolerated: this is a bounded parser, and the model reviews
        # semantics. Only the delimiters are structural.
        index += 1
    return None, "no closing --- frontmatter delimiter"


def _text_field(fields: Frontmatter, key: str) -> str:
    value = fields.get(key)
    return value if isinstance(value, str) else ""


def has_skill_md(skill_dir: Path) -> bool:
    """Is there a `SKILL.md` with EXACTLY that name?

    `(skill_dir / "SKILL.md").exists()` is not this check: on Windows and on a default
    macOS volume it also answers True for `skill.md`, which the runtime will not load. The
    directory listing is the only case-exact test that behaves the same on all three.
    """
    try:
        return "SKILL.md" in {p.name for p in skill_dir.iterdir() if p.is_file()}
    except OSError:
        return False


def _path_findings(skill_dir: Path, name: str) -> list[AuditFinding]:
    """Machine-specific path shapes anywhere in a skill's shipped files."""
    findings: list[AuditFinding] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix not in AUDITED_SUFFIXES:
            continue
        relative = path.relative_to(skill_dir).as_posix()
        lines = read_text(path).splitlines()
        for lineno, raw in enumerate(lines, start=1):
            if not any(pattern.search(raw) for pattern in PATH_PATTERNS):
                continue
            window = " ".join(
                lines[
                    max(0, lineno - 1 - PATH_ALLOW_WINDOW) : lineno + PATH_ALLOW_WINDOW
                ]
            ).lower()
            if any(marker in window for marker in PATH_ALLOW_MARKERS):
                continue
            findings.append(
                AuditFinding(
                    "MAJOR",
                    name,
                    f"hardcoded absolute path shape at {relative}:{lineno} "
                    "(machine-specific; derive it at runtime)",
                )
            )
            break  # one finding per file is enough signal
    return findings


def _link_findings(skill_dir: Path, name: str, text: str) -> list[AuditFinding]:
    """Relative links in SKILL.md that point at nothing, ignoring fenced examples."""
    findings: list[AuditFinding] = []
    lines = text.splitlines()
    fenced = _fence_mask(lines)
    for index, line in enumerate(lines):
        if fenced[index]:
            continue
        for target in LINK_RE.findall(line):
            stripped = target.split("#")[0].strip()
            if not stripped or stripped.startswith(("http://", "https://", "mailto:")):
                continue
            if not (skill_dir / stripped).exists():
                findings.append(
                    AuditFinding(
                        "MAJOR", name, f"SKILL.md links to a missing file: {stripped}"
                    )
                )
    return findings


def claude_md_skill_names(path: Path) -> set[str] | None:
    """Names listed in CLAUDE.md's `## Skills` section, or `None` if there is no CLAUDE.md.

    Scoped structurally rather than by grepping the whole file: a content grep also matches
    files that merely *mention* a skill name. Both listed forms are accepted, because a
    scaffolded index writes user-invocable plugin skills as `/plugin:name` and the rest as
    a bare name.
    """
    if not path.is_file():
        return None
    names: set[str] = set()
    in_section = False
    for line in read_text(path).splitlines():
        if line.startswith("## "):
            in_section = line.strip().lower() == "## skills"
            continue
        if not in_section or not line.lstrip().startswith("- "):
            continue
        token = line.lstrip()[2:].strip().split(" ")[0].strip("`").lstrip("/")
        # `/plugin-name:skill-name` -- the skill is the part after the colon.
        token = token.rpartition(":")[2] or token
        if SKILL_NAME_RE.match(token):
            names.add(token)
    return names


def audit_skills(
    skills_dir: Path,
    claude_md: Path | None = None,
    shipped: frozenset[str] | None = None,
) -> list[AuditFinding]:
    """The mechanical subset of the skill-review checklist, over a whole skills directory.

    Findings are review input, not process failures -- the caller decides whether any
    severity should change an exit code.

    Two upstream checks are deliberately absent, because both encode the source project's
    policy rather than a portable rule:

    - a name allowlist for `disable-model-invocation: true`. The kit's own taxonomy
      *encourages* that flag on side-effect skills, so an allowlist would report the
      skills that follow the documented rule. What is genuinely broken -- both invocation
      flags set, so nobody can reach the skill -- stays a BLOCKER.
    - `metadata.type: reference` requiring `user-invocable: false`. The shipped taxonomy
      makes that conditional ("when invoked only by workflows"), and a reference skill a
      user may want to invoke directly is legitimate.
    """
    findings: list[AuditFinding] = []
    if not skills_dir.is_dir():
        # The directory is named in the caller's header line, not repeated here: this
        # function has no project root to make it relative to, and an absolute path in a
        # message that gets pasted into a hand-off is portable to one machine.
        return [
            AuditFinding(
                "NOTE",
                "(fleet)",
                "no skills directory, so there is nothing to audit (a project with only "
                "plugin skills is the normal case)",
            )
        ]

    on_disk: dict[str, Frontmatter] = {}
    budget = 0
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        name = skill_dir.name
        if not has_skill_md(skill_dir):
            findings.append(
                AuditFinding(
                    "BLOCKER",
                    name,
                    "SKILL.md missing (the name is case-sensitive at load time)",
                )
            )
            continue
        text = read_text(skill_dir / "SKILL.md")
        fields, error = parse_frontmatter(text)
        if fields is None:
            findings.append(
                AuditFinding(
                    "BLOCKER",
                    name,
                    f"frontmatter unparseable ({error}) -- the body loads with EMPTY "
                    "metadata, so /name works but auto-matching dies",
                )
            )
            continue
        on_disk[name] = fields

        declared = _text_field(fields, "name")
        if declared and declared != name:
            findings.append(
                AuditFinding(
                    "BLOCKER",
                    name,
                    f"frontmatter name '{declared}' does not match the directory name",
                )
            )
        if declared and (SKILL_NAME_RE.match(declared) is None or len(declared) > 64):
            findings.append(
                AuditFinding(
                    "BLOCKER",
                    name,
                    f"name '{declared}' violates the spec charset or length rules",
                )
            )

        description = _text_field(fields, "description")
        when_to_use = _text_field(fields, "when_to_use")
        if not description:
            findings.append(
                AuditFinding(
                    "MAJOR",
                    name,
                    "description missing (spec-required; auto-invocation needs it)",
                )
            )
        elif len(description) > SPEC_DESCRIPTION_MAX:
            findings.append(
                AuditFinding(
                    "MAJOR",
                    name,
                    f"description {len(description)} chars > {SPEC_DESCRIPTION_MAX} "
                    "(spec max)",
                )
            )
        if len(description) + len(when_to_use) > LISTING_CAP:
            findings.append(
                AuditFinding(
                    "MAJOR",
                    name,
                    f"description+when_to_use {len(description) + len(when_to_use)} "
                    f"chars > {LISTING_CAP} listing cap (it will be truncated)",
                )
            )
        budget += len(description) + len(when_to_use)

        model_blocked = (
            _text_field(fields, "disable-model-invocation").lower() == "true"
        )
        user_blocked = _text_field(fields, "user-invocable").lower() == "false"
        if model_blocked and user_blocked:
            findings.append(
                AuditFinding(
                    "BLOCKER",
                    name,
                    "both disable-model-invocation:true AND user-invocable:false -- "
                    "the skill is unreachable by anyone",
                )
            )

        metadata = fields.get("metadata")
        skill_type = metadata.get("type") if isinstance(metadata, dict) else None
        if not skill_type:
            findings.append(
                AuditFinding(
                    "MAJOR",
                    name,
                    "metadata.type missing (taxonomy: "
                    f"{'|'.join(sorted(SKILL_TYPES))})",
                )
            )
        elif skill_type not in SKILL_TYPES:
            findings.append(
                AuditFinding(
                    "MAJOR",
                    name,
                    f"metadata.type '{skill_type}' is off-vocabulary "
                    f"{sorted(SKILL_TYPES)}",
                )
            )

        line_count = text.count("\n") + 1
        if line_count > MAX_SKILL_LINES:
            findings.append(
                AuditFinding(
                    "MAJOR",
                    name,
                    f"SKILL.md {line_count} lines > {MAX_SKILL_LINES} -- move detail "
                    "into references/",
                )
            )

        if (skill_dir / "README.md").is_file():
            findings.append(
                AuditFinding(
                    "MINOR",
                    name,
                    "README.md in the skill directory (entrypoint confusion)",
                )
            )

        findings += _path_findings(skill_dir, name)
        findings += _link_findings(skill_dir, name, text)

    findings += _registration_findings(claude_md, frozenset(on_disk), shipped)
    findings.append(
        AuditFinding(
            "INFO",
            "(fleet)",
            f"{len(on_disk)} skills; description+when_to_use total = {budget} chars. "
            "The listing budget defaults to 1% of the context window and drops "
            "least-invoked skills first -- run /doctor to see shortened entries.",
        )
    )
    return findings


def _registration_findings(
    claude_md: Path | None, on_disk: frozenset[str], shipped: frozenset[str] | None
) -> list[AuditFinding]:
    """Drift between the skills index and what actually exists, in both directions.

    A listed name may resolve EITHER to a project-local skill directory OR to the plugin
    catalog: a scaffolded index lists both, so checking only the directory would report
    every plugin skill as a ghost. That is the substantive difference from upstream, whose
    skills all live in one directory.
    """
    if claude_md is None:
        return []
    listed = claude_md_skill_names(claude_md)
    if listed is None:
        return [
            AuditFinding(
                "NOTE",
                "(fleet)",
                f"no {claude_md.name} at the project root, so registration is unchecked",
            )
        ]
    findings: list[AuditFinding] = []
    for name in sorted(on_disk - listed):
        findings.append(
            AuditFinding(
                "MAJOR",
                name,
                f"on disk but NOT listed in {claude_md.name} '## Skills' "
                "(registration drift)",
            )
        )
    # Only this direction needs the catalog, and an unknown catalog must SKIP it rather
    # than assume an empty one: every plugin skill in the index would otherwise be
    # reported as a ghost, which is a wrong answer dressed as a finding.
    if shipped is None:
        findings.append(
            AuditFinding(
                "NOTE",
                "(fleet)",
                "the plugin catalog could not be read, so listed-but-absent skills are "
                "unchecked (a name shipped by the plugin is indistinguishable from a "
                "ghost without it)",
            )
        )
        return findings
    for name in sorted(listed - on_disk - shipped):
        findings.append(
            AuditFinding(
                "MAJOR",
                name,
                f"listed in {claude_md.name} but neither on disk nor shipped by the "
                "plugin (ghost listing)",
            )
        )
    return findings


def worst_severity(findings: list[AuditFinding]) -> str | None:
    """The most severe severity present, ordered by `SEVERITIES`."""
    present = {finding.severity for finding in findings}
    return next((s for s in SEVERITIES if s in present), None)
