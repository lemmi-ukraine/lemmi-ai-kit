"""The upstream drift check: how far the shipped pack has fallen behind its source.

Reads `docs/upstream-sync.toml` -- the recorded sync point and correspondence map --
and measures, per skill, how many upstream commits have touched that skill's directory
since the revision this repo's copy was taken from.

Three design decisions worth the words, because each replaces something that looks
more obvious and is wrong.

**Drift is counted in commits, not content.** A content diff or a per-skill hash cannot
tell an upstream advance from one of this repo's own portability edits -- the two are
the same shape in a two-way diff, and the refresh dropped 82 upstream lines on purpose.
A hash check would report those 82 lines as drift forever, so it would be silenced
within a month. A commit count is zero the moment a sync lands and stays zero until
upstream actually moves, which is the only definition that can hold a maintainer's
attention.

**The map is read, never inferred.** Correspondence is not name equality: three skills
were renamed on extraction (`lemmi-` prefixes dropped), one had a typo corrected
(`analyge-logs`), two have no upstream counterpart at all, and two ORIGINATE HERE and
travel the other way. Every one of those is a row in the record, and
`test_upstream_sync.py` fails if a shipped skill has no row.

**It never fails the build.** Charter DoD 5: this ships as a non-blocking report and is
promoted to a gate only once it has been observed to be accurate. `main()` returns 0 on
every path, including a malformed record -- the gate on the record's validity lives in
the test suite, where it does not depend on an external repository being present. See
syncing-from-upstream.md for the promotion criteria.

The upstream repository is private and is NOT present in CI, so the report's normal CI
output is "not measured". That is deliberate rather than a defect to paper over: the
line makes the absence visible instead of silent, and the parts that do not need
upstream -- record validity, map/pack correspondence, and the measurement logic itself
against a synthetic repository -- are gated on every run.

Usage:

    uv run python tests/upstream_sync.py [--repo PATH] [--upstream-ref REF]

`--repo` defaults to `$LEMMI_UPSTREAM_REPO`. The path is never committed: the source
project is private and the hygiene contract bans naming it in a tracked file.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

_REPO_ROOT = Path(__file__).resolve().parents[1]

RECORD_PATH = _REPO_ROOT / "docs" / "upstream-sync.toml"
ENV_VAR = "LEMMI_UPSTREAM_REPO"

DIRECTIONS: tuple[str, ...] = ("upstream-origin", "kit-origin", "divergent-both")

_SHA_LEN = 40
_KIT_PREFIX = "kit:"


class SyncRecordError(ValueError):
    """Raised when the sync record is malformed or internally inconsistent."""


@dataclass(frozen=True)
class SkillRow:
    """One shipped skill's correspondence to its upstream counterpart."""

    name: str
    upstream: str
    """Directory name under `skills_path`. Empty means no upstream counterpart."""
    direction: str
    base: str
    """Resolved base ref for the next three-way merge of this skill."""
    base_is_default: bool
    """False when the row overrides the sync pin -- i.e. this skill is behind."""
    origin: str
    upstream_adopted: str
    note: str

    @property
    def tracked(self) -> bool:
        """Does this skill have an upstream counterpart to measure at all?"""
        return bool(self.upstream)


@dataclass(frozen=True)
class UnportedRow:
    """An upstream skill deliberately not shipped."""

    upstream: str
    reason: str


@dataclass(frozen=True)
class ExtractionWindow:
    """Upstream commits that fall between the true extraction base and a later base
    an earlier refresh used by mistake.

    This is a separate finding from drift, and deliberately not folded into the
    per-skill commit counts. Those counts answer "has upstream moved since we synced";
    this answers "did an earlier sync silently classify upstream content as our own
    deletion". Merging them would bury a one-time debt inside an ongoing signal and
    leave 16 skills permanently reported as behind, which is how a check gets ignored.
    """

    kit_first_commit: str
    base_used_by_refresh: str
    status: str
    affected: tuple[str, ...]
    """Upstream directory names, resolved through the correspondence map by the check."""


@dataclass(frozen=True)
class SyncRecord:
    """The recorded sync point plus the full correspondence map."""

    upstream_commit: str
    upstream_skills_commit: str
    extraction_base: str
    skills_path: str
    synced_on: str
    carried_note: str | None
    skills: tuple[SkillRow, ...]
    unported: tuple[UnportedRow, ...]
    window: ExtractionWindow | None


# --------------------------------------------------------------------------------------
# Loading and validation
# --------------------------------------------------------------------------------------


def _require_str(table: dict[str, object], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise SyncRecordError(f"{where}: `{key}` must be a non-empty string")
    return value


def _optional_str(table: dict[str, object], key: str, where: str) -> str:
    if key not in table:
        return ""
    value = table[key]
    if not isinstance(value, str):
        raise SyncRecordError(f"{where}: `{key}` must be a string")
    return value


def _require_sha(table: dict[str, object], key: str, where: str) -> str:
    value = _require_str(table, key, where)
    _check_sha(value, f"{where}.{key}")
    return value


def _check_sha(value: str, where: str) -> None:
    """Full 40-hex only.

    An abbreviated SHA is ambiguous by construction -- it can stop resolving as a
    repository grows, and a provenance record that silently stops resolving is worse
    than no record. `kit:` marks a SHA in THIS repository rather than upstream; without
    the prefix a reader would look for it in the wrong history.
    """
    body = value[len(_KIT_PREFIX) :] if value.startswith(_KIT_PREFIX) else value
    if len(body) != _SHA_LEN or any(c not in "0123456789abcdef" for c in body):
        raise SyncRecordError(
            f"{where}: expected a full {_SHA_LEN}-character lowercase hex SHA"
            f" (optionally `{_KIT_PREFIX}`-prefixed), got {value!r}"
        )


def _load_skill_rows(
    raw_rows: list[dict[str, object]], default_base: str
) -> tuple[SkillRow, ...]:
    rows: list[SkillRow] = []
    for raw in raw_rows:
        name = _require_str(raw, "name", "[[skills]]")
        where = f"skill {name}"

        upstream = raw.get("upstream")
        if not isinstance(upstream, str):
            raise SyncRecordError(
                f"{where}: `upstream` is required -- use an empty string to say"
                " explicitly that no upstream counterpart exists"
            )

        direction = _require_str(raw, "direction", where)
        if direction not in DIRECTIONS:
            raise SyncRecordError(
                f"{where}: unknown direction {direction!r} (known: {', '.join(DIRECTIONS)})"
            )

        base = _optional_str(raw, "base", where) or default_base
        _check_sha(base, f"{where}.base")

        origin = _optional_str(raw, "origin", where)
        if origin:
            _check_sha(origin, f"{where}.origin")
        adopted = _optional_str(raw, "upstream_adopted", where)
        if adopted:
            _check_sha(adopted, f"{where}.upstream_adopted")
        note = _optional_str(raw, "note", where)

        # The direction field has to cost something to claim, or it decays into a
        # column of guesses. `kit-origin` on a skill upstream also carries is the
        # claim that reverses the sync direction, so it must name the upstream commit
        # that received the copy -- the evidence a future maintainer can re-check.
        if direction == "kit-origin" and upstream and not adopted:
            raise SyncRecordError(
                f"{where}: `kit-origin` with an upstream counterpart must cite"
                " `upstream_adopted` (the upstream commit that received the copy)"
            )
        if not upstream and direction != "kit-origin":
            raise SyncRecordError(
                f"{where}: no upstream counterpart, so direction must be `kit-origin`,"
                f" not {direction!r}"
            )
        # `divergent-both` says a mechanical merge is unsafe. That is only actionable
        # with a base to merge from and a written reason it is unsafe.
        if direction == "divergent-both" and not note:
            raise SyncRecordError(
                f"{where}: `divergent-both` must carry a `note` saying what makes a"
                " mechanical merge unsafe"
            )

        rows.append(
            SkillRow(
                name=name,
                upstream=upstream,
                direction=direction,
                base=base,
                base_is_default=base == default_base,
                origin=origin,
                upstream_adopted=adopted,
                note=note,
            )
        )

    names = [r.name for r in rows]
    if len(names) != len(set(names)):
        raise SyncRecordError("duplicate skill names in the correspondence map")
    if names != sorted(names):
        raise SyncRecordError(
            "correspondence map rows must be sorted by `name` -- an unsorted 38-row"
            " table makes every future diff unreviewable"
        )
    paths = [r.upstream for r in rows if r.tracked]
    if len(paths) != len(set(paths)):
        duplicated = sorted({p for p in paths if paths.count(p) > 1})
        raise SyncRecordError(
            f"two skills claim the same upstream directory: {', '.join(duplicated)}"
        )
    return tuple(rows)


def load_sync_record(path: Path | None = None) -> SyncRecord:
    """Parse and validate the sync record.

    Every rule enforced here is checkable without the upstream repository, which is why
    the test suite can gate all of it while the drift measurement stays a report.
    """
    record_path = path or RECORD_PATH
    try:
        with record_path.open("rb") as fh:
            data = cast(dict[str, object], tomllib.load(fh))
    except OSError as exc:
        raise SyncRecordError(f"cannot read {record_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise SyncRecordError(f"{record_path} is not valid TOML: {exc}") from exc

    sync = data.get("sync")
    if not isinstance(sync, dict):
        raise SyncRecordError("missing the [sync] table")
    sync_table = cast(dict[str, object], sync)

    upstream_commit = _require_sha(sync_table, "upstream_commit", "[sync]")
    upstream_skills_commit = _require_sha(
        sync_table, "upstream_skills_commit", "[sync]"
    )
    extraction_base = _require_sha(sync_table, "extraction_base", "[sync]")
    skills_path = _require_str(sync_table, "skills_path", "[sync]")
    synced_on = _require_str(sync_table, "synced_on", "[sync]")

    # Optional. Present only while content has been carried WITHOUT moving the pin --
    # which happens when the source ref is an open PR head that a rebase or squash-merge
    # would rewrite, making a pin that names it unresolvable. Holding the pin makes the
    # report list carried skills as BEHIND, and that false positive is only useful if the
    # reader can see WHY from the report itself: a note buried in a TOML comment is
    # invisible to this loader and to anyone running the check.
    raw_note = sync_table.get("carried_note")
    if raw_note is not None and not isinstance(raw_note, str):
        raise SyncRecordError("[sync] carried_note must be a string")
    carried_note = (
        raw_note.strip() if isinstance(raw_note, str) and raw_note.strip() else None
    )

    raw_skills = data.get("skills")
    if not isinstance(raw_skills, list) or not raw_skills:
        raise SyncRecordError("the record must contain a non-empty [[skills]] list")
    rows = _load_skill_rows(cast(list[dict[str, object]], raw_skills), upstream_commit)

    raw_unported = data.get("unported")
    if not isinstance(raw_unported, list):
        raise SyncRecordError(
            "the record must contain an [[unported]] list -- without it the report"
            " cannot tell a new upstream skill from one that was declined"
        )
    unported: list[UnportedRow] = []
    for raw in cast(list[dict[str, object]], raw_unported):
        name = _require_str(raw, "upstream", "[[unported]]")
        reason = _require_str(raw, "reason", f"unported {name}")
        unported.append(UnportedRow(upstream=name, reason=reason))

    declined = [u.upstream for u in unported]
    if len(declined) != len(set(declined)):
        raise SyncRecordError("duplicate entries in the unported list")
    if names := sorted(set(declined) & set(rows_upstream(rows))):
        raise SyncRecordError(
            f"listed as both shipped and unported: {', '.join(names)}"
        )
    if declined != sorted(declined):
        raise SyncRecordError("unported entries must be sorted by `upstream`")

    window = _load_window(data, declared=set(rows_upstream(rows)) | set(declined))

    return SyncRecord(
        upstream_commit=upstream_commit,
        upstream_skills_commit=upstream_skills_commit,
        extraction_base=extraction_base,
        skills_path=skills_path,
        synced_on=synced_on,
        carried_note=carried_note,
        skills=rows,
        unported=tuple(unported),
        window=window,
    )


def _load_window(
    data: dict[str, object], *, declared: set[str]
) -> ExtractionWindow | None:
    """Optional: the table is absent once the window has been reviewed and closed."""
    raw = data.get("extraction_window")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise SyncRecordError("[extraction_window] must be a table")
    table = cast(dict[str, object], raw)
    where = "[extraction_window]"

    kit_first = _require_sha(table, "kit_first_commit", where)
    if not kit_first.startswith(_KIT_PREFIX):
        raise SyncRecordError(
            f"{where}: `kit_first_commit` is a commit in THIS repository, so it must"
            f" carry the `{_KIT_PREFIX}` prefix"
        )
    base_used = _require_sha(table, "base_used_by_refresh", where)
    status = _require_str(table, "status", where)

    affected = table.get("affected")
    if not isinstance(affected, list) or not affected:
        raise SyncRecordError(f"{where}: `affected` must be a non-empty list")
    names: list[str] = []
    for item in cast(list[object], affected):
        if not isinstance(item, str) or not item:
            raise SyncRecordError(f"{where}: `affected` entries must be strings")
        names.append(item)
    if names != sorted(names):
        raise SyncRecordError(f"{where}: `affected` must be sorted")
    if len(names) != len(set(names)):
        raise SyncRecordError(f"{where}: duplicate entries in `affected`")
    # Every affected name must be an upstream directory the record already knows about,
    # shipped or declined. An unknown name means the list was hand-edited against a
    # different vocabulary -- exactly the drift this file exists to prevent.
    if unknown := sorted(set(names) - declared):
        raise SyncRecordError(
            f"{where}: `affected` names upstream directories the record does not"
            f" otherwise mention: {', '.join(unknown)}"
        )
    return ExtractionWindow(
        kit_first_commit=kit_first,
        base_used_by_refresh=base_used,
        status=status,
        affected=tuple(names),
    )


def rows_upstream(rows: tuple[SkillRow, ...]) -> list[str]:
    return [r.upstream for r in rows if r.tracked]


# --------------------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillDrift:
    """One skill's measured distance from upstream."""

    name: str
    upstream: str
    direction: str
    base: str
    commits: int


@dataclass(frozen=True)
class DriftReport:
    """What a measurement against a real upstream checkout found."""

    upstream_ref: str
    resolved_head: str
    measured: tuple[SkillDrift, ...]
    undeclared: tuple[str, ...]
    """Upstream skill directories in neither the map nor the unported list."""
    vanished: tuple[str, ...]
    """Declared upstream directories that no longer exist upstream."""
    unresolved: tuple[str, ...]
    """Rows whose upstream directory does not exist at that row's own base ref."""
    window: tuple[SkillDrift, ...]
    """The extraction-window debt, measured separately. See `ExtractionWindow`."""
    window_unlisted: tuple[str, ...]
    """Skills upstream touched inside the window that the record does not list."""

    @property
    def behind(self) -> tuple[SkillDrift, ...]:
        return tuple(d for d in self.measured if d.commits > 0)

    @property
    def total_commits(self) -> int:
        return sum(d.commits for d in self.measured)

    @property
    def clean(self) -> bool:
        return not (self.behind or self.undeclared or self.vanished or self.unresolved)


class UpstreamUnavailable(RuntimeError):
    """The upstream checkout is absent, not a git repository, or lacks a needed ref."""


def _git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - git absent from PATH
        raise UpstreamUnavailable(f"cannot run git: {exc}") from exc
    if result.returncode != 0:
        raise UpstreamUnavailable(
            f"git {' '.join(args)} failed: {result.stderr.strip() or 'no stderr'}"
        )
    return result.stdout


def read_upstream_file(repo: Path, ref: str, path: str) -> str:
    """One file's content from upstream at `ref`, decoded as UTF-8 explicitly.

    Deliberately NOT `_git`. That helper passes `text=True`, which decodes through the
    locale codec -- fine for the commit counts and ASCII paths it was written for, and
    wrong for content. On a Windows console code page every em dash comes back mangled,
    so a comparison of two prose tables reports differences that are not there; the same
    defect once turned 14 rewritten lines into 176 phantom dropped ones. Vocabularies are
    prose, so they get bytes and an explicit decode.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{path}"],
            capture_output=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - git absent from PATH
        raise UpstreamUnavailable(f"cannot run git: {exc}") from exc
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise UpstreamUnavailable(
            f"cannot read {path} at {ref[:8]}: {stderr or 'no stderr'}"
        )
    return result.stdout.decode("utf-8")


def _exists(repo: Path, spec: str) -> bool:
    """Does `spec` (a ref, or `ref:path`) resolve? A miss is an answer, not an error."""
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", spec],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _tree_exists(repo: Path, ref: str, path: str) -> bool:
    return _exists(repo, f"{ref}:{path}")


def measure_drift(
    repo: Path, record: SyncRecord, upstream_ref: str = "HEAD"
) -> DriftReport:
    """Count upstream commits touching each skill since that skill's own base ref.

    Raises `UpstreamUnavailable` if the checkout cannot answer the question. A report
    that guessed at a missing repository would be worse than no report.
    """
    if not repo.is_dir():
        raise UpstreamUnavailable(f"{repo} is not a directory")
    resolved = _git(repo, "rev-parse", "--verify", f"{upstream_ref}^{{commit}}").strip()

    listing = _git(
        repo, "ls-tree", "-d", "--name-only", f"{resolved}:{record.skills_path}"
    )
    present = {line.strip() for line in listing.splitlines() if line.strip()}

    measured: list[SkillDrift] = []
    vanished: list[str] = []
    unresolved: list[str] = []
    for row in record.skills:
        if not row.tracked:
            continue
        path = f"{record.skills_path}/{row.upstream}"
        if row.upstream not in present:
            vanished.append(row.upstream)
            continue
        # A row pointing at a directory that did not exist at its own base ref is a
        # wrong row, not zero drift -- `rev-list` would report 0 either way, so this
        # is the difference between a check and a rubber stamp.
        #
        # The two faults are reported apart because they need different fixes: an
        # unresolvable base is a bad SHA (or a shallow clone), while a resolvable base
        # with no such directory means the `upstream` name is wrong. Collapsing them
        # into one message sends the reader to the wrong field.
        if not _exists(repo, f"{row.base}^{{commit}}"):
            unresolved.append(
                f"{row.name}: base ref {row.base[:12]} does not resolve in this checkout"
            )
            continue
        if not _tree_exists(repo, row.base, path):
            unresolved.append(
                f"{row.name} -> {row.upstream}: no such directory at base {row.base[:12]}"
            )
            continue
        count = _git(
            repo, "rev-list", "--count", f"{row.base}..{resolved}", "--", path
        ).strip()
        measured.append(
            SkillDrift(
                name=row.name,
                upstream=row.upstream,
                direction=row.direction,
                base=row.base,
                commits=int(count or "0"),
            )
        )

    declared = set(rows_upstream(record.skills)) | {u.upstream for u in record.unported}
    for name in sorted(u.upstream for u in record.unported):
        if name not in present:
            vanished.append(name)

    window, window_unlisted = _measure_window(repo, record)

    return DriftReport(
        upstream_ref=upstream_ref,
        resolved_head=resolved,
        measured=tuple(measured),
        undeclared=tuple(sorted(present - declared)),
        vanished=tuple(sorted(vanished)),
        unresolved=tuple(sorted(unresolved)),
        window=window,
        window_unlisted=tuple(window_unlisted),
    )


def _measure_window(
    repo: Path, record: SyncRecord
) -> tuple[tuple[SkillDrift, ...], list[str]]:
    """Measure the recorded extraction-window debt, and re-derive it independently.

    The record lists the affected skills so the debt is visible without an upstream
    checkout. When one IS available the list is re-derived from git and any name the
    record missed is reported -- a recorded list nothing re-checks is just a claim.
    """
    win = record.window
    if win is None:
        return (), []

    by_upstream = {r.upstream: r for r in record.skills if r.tracked}
    rows: list[SkillDrift] = []
    for upstream_dir in win.affected:
        path = f"{record.skills_path}/{upstream_dir}"
        count = _git(
            repo,
            "rev-list",
            "--count",
            f"{record.extraction_base}..{win.base_used_by_refresh}",
            "--",
            path,
        ).strip()
        row = by_upstream.get(upstream_dir)
        rows.append(
            SkillDrift(
                # Declined skills have no shipped name; show the upstream one so the
                # row is still identifiable rather than blank.
                name=row.name if row else f"({upstream_dir}, not shipped)",
                upstream=upstream_dir,
                direction=row.direction if row else "upstream-origin",
                base=record.extraction_base,
                commits=int(count or "0"),
            )
        )

    # `-z` rather than line splitting: git quotes paths containing non-ASCII bytes by
    # default, and a quoted path would parse into a directory name that does not exist,
    # fabricating a RECORD INCOMPLETE entry. Skill directories are kebab-case ASCII
    # today, which is exactly the kind of assumption that stops holding quietly.
    touched = _git(
        repo,
        "log",
        "--format=",
        "--name-only",
        "-z",
        f"{record.extraction_base}..{win.base_used_by_refresh}",
        "--",
        record.skills_path,
    )
    prefix = f"{record.skills_path}/"
    derived = {
        entry[len(prefix) :].split("/", 1)[0]
        for entry in touched.split("\0")
        if entry.startswith(prefix) and "/" in entry[len(prefix) :]
    }
    return tuple(rows), sorted(derived - set(win.affected))


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------

# Output is deliberately ASCII-only: this runs on consoles whose default code page
# cannot encode an em dash, and the hygiene contract bans the environment-variable
# workaround for that as a machine-specific rule. A report that crashes on the
# maintainer's terminal is not a report.

_HEADER = "upstream drift report"


def _summary_lines(record: SyncRecord) -> list[str]:
    tracked = sum(1 for r in record.skills if r.tracked)
    overrides = [r for r in record.skills if not r.base_is_default]
    lines = [
        f"  pin           {record.upstream_commit[:12]} (skills last moved at"
        f" {record.upstream_skills_commit[:12]}), synced {record.synced_on}",
        f"  map           {len(record.skills)} shipped skills:"
        f" {tracked} tracked upstream,"
        f" {len(record.skills) - tracked} kit-only;"
        f" {len(record.unported)} upstream skills declined",
    ]
    by_direction = {d: 0 for d in DIRECTIONS}
    for row in record.skills:
        by_direction[row.direction] += 1
    lines.append(
        "  direction     " + ", ".join(f"{d} {by_direction[d]}" for d in DIRECTIONS)
    )
    if overrides:
        lines.append(
            "  base override "
            + ", ".join(f"{r.name} @ {r.base[:12]}" for r in overrides)
            + "  (not synced to the pin)"
        )
    return lines


def format_report(record: SyncRecord, drift: DriftReport | None, why: str = "") -> str:
    """Render the report. `drift` is None when upstream could not be measured."""
    lines = [_HEADER, "=" * len(_HEADER), *_summary_lines(record), ""]

    if drift is None:
        lines += [
            "  NOT MEASURED  " + (why or "no upstream checkout given"),
            "",
            "  The source project is private and absent from CI, so this is the normal",
            f"  CI result. To measure locally, point {ENV_VAR} at an upstream checkout",
            "  or pass --repo. Record validity and map/pack correspondence ARE gated",
            "  on every run, in tests/test_upstream_sync.py.",
        ]
        return "\n".join(lines)

    lines.append(
        f"  measured against {drift.resolved_head[:12]} ({drift.upstream_ref})"
    )
    lines.append("")

    if drift.unresolved:
        lines.append(
            "  MAP ERROR - a row points at a directory absent at its own base:"
        )
        lines += [f"    - {item}" for item in drift.unresolved]
        lines.append("")
    if drift.undeclared:
        lines.append(
            "  UNDECLARED - upstream skills in neither the map nor the unported list:"
        )
        lines += [f"    - {name}" for name in drift.undeclared]
        lines.append(
            "    Decide each one: port it, or add it to [[unported]] with a reason."
        )
        lines.append("")
    if drift.vanished:
        lines.append(
            "  VANISHED - declared upstream skills that no longer exist there:"
        )
        lines += [f"    - {name}" for name in drift.vanished]
        lines.append("")

    if drift.behind and record.carried_note:
        lines.append(
            "  CARRIED WITHOUT MOVING THE PIN - read this before porting anything:"
        )
        lines += [f"    {line}" for line in record.carried_note.splitlines()]
        lines.append("")

    if drift.behind:
        lines.append(
            f"  BEHIND - {len(drift.behind)} of {len(drift.measured)} tracked skills,"
            f" {drift.total_commits} upstream commits total:"
        )
        for item in sorted(drift.behind, key=lambda d: (-d.commits, d.name)):
            # kit-origin skills are phrased differently on purpose. "N commits behind"
            # is false for a skill this repo authored: upstream's later edits there are
            # contributions to review, not a backlog to absorb. Two skills read
            # backwards under the obvious wording, which is why direction is in the map.
            verb = (
                "upstream advanced a skill THIS repo authored"
                if item.direction == "kit-origin"
                else "commits behind"
            )
            lines.append(
                f"    - {item.name:<24} {item.commits:>3}  {verb}"
                f"  (base {item.base[:12]})"
            )
        lines.append("")
    else:
        lines.append(
            f"  IN SYNC - all {len(drift.measured)} tracked skills at zero drift."
        )
        lines.append("")

    lines += _window_lines(record, drift)

    lines.append("  Non-blocking by design (charter DoD 5). Promotion criteria and the")
    lines.append("  three-way merge procedure: docs/syncing-from-upstream.md")
    return "\n".join(lines)


def _window_lines(record: SyncRecord, drift: DriftReport) -> list[str]:
    """The extraction-window debt, reported apart from drift.

    Kept separate because it is a different question. Drift asks whether upstream has
    moved since the pin; this asks whether an earlier sync used a base from INSIDE the
    extraction window and so read upstream's own additions as this repo's deletions.
    Folded into the drift numbers it would show 16 skills permanently behind and drown
    the ongoing signal.
    """
    win = record.window
    if win is None or not drift.window:
        return []
    total = sum(d.commits for d in drift.window)
    lines = [
        f"  EXTRACTION WINDOW ({win.status}) - {len(drift.window)} skills,"
        f" {total} upstream commits between the true base and",
        f"  the base an earlier refresh used ({win.base_used_by_refresh[:12]}). Content"
        " upstream added in that",
        "  gap was eligible to be read as a deliberate kit deletion and dropped. Needs"
        " a per-skill",
        "  read, not a bulk re-merge:",
    ]
    for item in sorted(drift.window, key=lambda d: d.name):
        lines.append(f"    - {item.name:<32} {item.commits:>2} commit(s) in the window")
    if drift.window_unlisted:
        lines.append(
            "    RECORD INCOMPLETE - upstream also touched these in the window: "
            + ", ".join(drift.window_unlisted)
        )
    lines.append("")
    return lines


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


def resolve_upstream(explicit: str | None) -> Path | None:
    raw = explicit or os.environ.get(ENV_VAR, "")
    return Path(raw).expanduser() if raw.strip() else None


def main(argv: list[str] | None = None) -> int:
    """Print the report. Always returns 0 -- see the module docstring."""
    parser = argparse.ArgumentParser(
        prog="upstream_sync",
        description="Report how far the shipped skill pack has drifted from upstream.",
    )
    _ = parser.add_argument(
        "--repo",
        default=None,
        help=f"path to an upstream checkout (default: ${ENV_VAR})",
    )
    _ = parser.add_argument(
        "--upstream-ref",
        default="HEAD",
        help="upstream revision to measure against (default: HEAD)",
    )
    _ = parser.add_argument(
        "--record",
        default=None,
        help=f"path to the sync record (default: {RECORD_PATH.name})",
    )
    args = parser.parse_args(argv)
    repo_arg = cast("str | None", args.repo)
    ref = cast(str, args.upstream_ref)
    record_arg = cast("str | None", args.record)

    try:
        record = load_sync_record(Path(record_arg) if record_arg else None)
    except SyncRecordError as exc:
        # Still 0. The gate on record validity is test_upstream_sync.py, which needs no
        # upstream repository; making this step fail too would break the non-blocking
        # contract for a defect that is already caught earlier and louder.
        print(f"{_HEADER}\n{'=' * len(_HEADER)}\n  RECORD INVALID  {exc}")
        return 0

    repo = resolve_upstream(repo_arg)
    if repo is None:
        print(format_report(record, None))
        return 0
    try:
        drift = measure_drift(repo, record, ref)
    except UpstreamUnavailable as exc:
        print(format_report(record, None, why=str(exc)))
        return 0
    print(format_report(record, drift))
    return 0


if __name__ == "__main__":
    sys.exit(main())
