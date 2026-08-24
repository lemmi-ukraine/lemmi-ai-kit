"""Gates on the sync record, and on the drift check's own arithmetic.

The drift *report* is non-blocking by charter (DoD 5) and cannot run in CI at all -- the
upstream repository is private and absent there. So this file exists to make everything
that does NOT need upstream a real gate, which is most of what can actually rot:

1. **The record is well-formed and internally consistent** -- SHAs are full-length, every
   `direction` is from the enum, a `kit-origin` claim cites its evidence, a
   `divergent-both` claim says why a mechanical merge is unsafe.
2. **The map and the pack stay in correspondence** -- one row per shipped skill, no
   orphans either way. This is the check that stops the table becoming decoration: a
   session that adds or removes a skill without touching the map goes red.
3. **The measurement arithmetic is right** -- exercised against a synthetic git
   repository built in a temp directory, so the logic is covered on every run even
   though the real upstream is unreachable. Without this the check would be untested
   precisely where CI runs it.

The record's validation rules are mutation-tested: each test perturbs one field of an
otherwise valid record and asserts the loader rejects it. A validator nobody has seen
reject anything is an assumption, not a check.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from upstream_sync import (
    DIRECTIONS,
    ENV_VAR,
    RECORD_PATH,
    SyncRecordError,
    UpstreamUnavailable,
    format_report,
    load_sync_record,
    main,
    measure_drift,
    resolve_upstream,
)

from lemmi_ai_kit.manifest import load_manifest, shipped_skill_dirs

# --------------------------------------------------------------------------------------
# The real record
# --------------------------------------------------------------------------------------


def test_the_shipped_record_loads() -> None:
    """Every rule in the loader, applied to the file that actually ships."""
    record = load_sync_record()
    assert record.skills, "the correspondence map is empty"
    assert record.unported, "no declined upstream skills recorded"


def test_every_shipped_skill_has_exactly_one_row() -> None:
    """The map and the pack must stay in correspondence, in both directions.

    This is the test that keeps the record honest. A skill added, removed or renamed
    without a matching map edit fails here -- which is the intended coupling, not an
    inconvenience: a correspondence map that has stopped corresponding is worse than
    none, because the drift report would keep printing a confident number for a pack it
    no longer describes.
    """
    shipped = set(shipped_skill_dirs())
    assert len(shipped) > 10, (
        f"only {len(shipped)} skill directories found -- the enumeration is probably "
        "broken, which would make this check pass vacuously"
    )
    mapped = {row.name for row in load_sync_record().skills}
    assert mapped == shipped, (
        "correspondence map out of sync with the shipped pack: "
        f"unmapped dirs {sorted(shipped - mapped) or '-'}, "
        f"stale rows {sorted(mapped - shipped) or '-'}"
    )


def test_rows_agree_with_the_manifest() -> None:
    """The manifest is the pack's other index; the two must not disagree."""
    mapped = {row.name for row in load_sync_record().skills}
    listed = {entry.name for entry in load_manifest().skills}
    assert mapped == listed, (
        f"map/manifest mismatch: map-only {sorted(mapped - listed) or '-'}, "
        f"manifest-only {sorted(listed - mapped) or '-'}"
    )


def test_the_kit_origin_set_is_the_measured_one() -> None:
    """Pinned as a constant on purpose, not derived from the record it checks.

    `orchestrate` and `agent-delegate` entered this repo 2026-07-03 and upstream
    2026-07-13, byte-identical: upstream is downstream. Two earlier documents assumed
    the opposite and would have had the drift check report them backwards. Deriving
    this list from the record would test nothing -- pinning it means a future edit that
    quietly flips a direction has to argue with a test, and a genuinely new kit-origin
    skill costs one deliberate line here. Same reasoning as the vocabulary pinning in
    `test_checks.py`: the alarm is the point.
    """
    record = load_sync_record()
    kit_origin = {r.name for r in record.skills if r.direction == "kit-origin"}
    assert kit_origin == {
        "agent-delegate",
        "kit-setup",
        "orchestrate",
        "scout-review",
        "test-planner",
    }
    # The two with an upstream counterpart are the ones a naive check reports backwards,
    # so those are the two that must carry re-checkable evidence.
    for name in ("agent-delegate", "orchestrate"):
        row = next(r for r in record.skills if r.name == name)
        assert row.upstream_adopted, f"{name}: kit-origin claim cites no evidence"
        assert row.origin.startswith("kit:"), f"{name}: origin must name a kit commit"


def test_the_direction_enum_is_the_ruled_one() -> None:
    """Pins the enum the operator ruled, NOT which values currently have members.

    An earlier version of this test asserted all three values were in use. That was
    wrong in a way worth recording: `divergent-both` is legitimately allowed to be
    empty -- it means "a mechanical merge is unsafe here", and the correct steady state
    is that no skill is in it. Requiring a member would have turned reconciling the last
    such skill into a test failure, i.e. punished the fix. Pin the vocabulary; let the
    population move.
    """
    assert DIRECTIONS == ("upstream-origin", "kit-origin", "divergent-both")
    # The two structural values must always have members: every pack has skills it
    # received and skills it authored. If either empties, the map is broken, not tidy.
    used = {r.direction for r in load_sync_record().skills}
    for required in ("upstream-origin", "kit-origin"):
        assert required in used, f"no skill is {required} -- the map cannot be right"


def test_base_overrides_are_the_unsynced_skills() -> None:
    """A row overriding the pin is exactly a skill the last sync did not carry."""
    record = load_sync_record()
    overrides = {r.name for r in record.skills if not r.base_is_default}
    # Empty since 2026-08-23: `session-retrospective` was the only override and its
    # reconciliation landed, so its `base` was dropped in that same commit. Empty is the
    # healthy state -- every skill sits on the pin. This stays a tripwire: it fires the
    # next time any row needs an override, which forces the reason to be written down.
    assert overrides == set(), (
        "the set of skills not synced to the pin changed. If a sync deliberately "
        "skipped a skill, add it here with its reason; if one was reconciled, drop its "
        f"`base` override from the record. Currently: {sorted(overrides)}"
    )


def test_every_base_override_is_explained() -> None:
    """Keeps `sync.extraction_base` load-bearing without naming a specific skill.

    Structural on purpose. An earlier version asserted that
    `session-retrospective` specifically sat at the extraction base, which made
    reconciling that skill fail a test -- punishing the fix. This states the durable
    rule instead: an override is either the recorded extraction point (a skill never
    carried) or an intermediate revision, and an intermediate revision has to say why.
    Zero overrides passes vacuously here; `test_base_overrides_are_the_unsynced_skills`
    is the non-vacuity guard.
    """
    record = load_sync_record()
    for row in record.skills:
        if row.base_is_default:
            continue
        if row.base == record.extraction_base:
            continue
        assert row.note, (
            f"{row.name}: base {row.base[:12]} is neither the pin nor the recorded "
            "extraction point, so the note must say which revision it is and why"
        )


# --------------------------------------------------------------------------------------
# Mutation tests on the loader
# --------------------------------------------------------------------------------------

_SHA_A = "a" * 40
_SHA_B = "b" * 40

_UNPORTED = """
[[unported]]
upstream = "declined-thing"
reason = "not portable"
"""


def _write(
    tmp_path: Path,
    skills: str,
    unported: str = _UNPORTED,
    extra: str = "",
    extraction_base: str = _SHA_B,
    upstream_commit: str = _SHA_A,
) -> Path:
    path = tmp_path / "record.toml"
    _ = path.write_text(
        f"""
[sync]
upstream_commit = "{upstream_commit}"
upstream_skills_commit = "{upstream_commit}"
extraction_base = "{extraction_base}"
skills_path = ".claude/skills"
synced_on = "2026-01-01"
{skills}
{unported}
{extra}
""",
        encoding="utf-8",
    )
    return path


_VALID_ROWS = """
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "upstream-origin"

[[skills]]
name = "beta"
upstream = "beta"
direction = "upstream-origin"
"""


def test_a_minimal_valid_record_loads(tmp_path: Path) -> None:
    """Guard the mutation tests: they prove nothing if the baseline never loaded."""
    record = load_sync_record(_write(tmp_path, _VALID_ROWS))
    assert [r.name for r in record.skills] == ["alpha", "beta"]
    assert all(r.base == _SHA_A for r in record.skills), (
        "rows without an explicit base must inherit the sync pin"
    )
    assert all(r.base_is_default for r in record.skills)


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        pytest.param(
            """
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "sideways"
""",
            "unknown direction",
            id="direction outside the enum",
        ),
        pytest.param(
            """
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "kit-origin"
""",
            "upstream_adopted",
            id="kit-origin claim with no evidence",
        ),
        pytest.param(
            """
[[skills]]
name = "alpha"
upstream = ""
direction = "upstream-origin"
""",
            "must be `kit-origin`",
            id="no counterpart but claims upstream origin",
        ),
        pytest.param(
            """
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "divergent-both"
base = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
""",
            "must carry a `note`",
            id="divergent-both with no stated reason",
        ),
        pytest.param(
            """
[[skills]]
name = "alpha"
direction = "upstream-origin"
""",
            "`upstream` is required",
            id="omitted rather than explicitly empty",
        ),
        pytest.param(
            """
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "upstream-origin"
base = "c05bf72d"
""",
            "full 40-character",
            id="abbreviated SHA",
        ),
        pytest.param(
            """
[[skills]]
name = "alpha"
upstream = "shared"
direction = "upstream-origin"

[[skills]]
name = "beta"
upstream = "shared"
direction = "upstream-origin"
""",
            "same upstream directory",
            id="two skills claiming one upstream directory",
        ),
        pytest.param(
            """
[[skills]]
name = "zeta"
upstream = "zeta"
direction = "upstream-origin"

[[skills]]
name = "alpha"
upstream = "alpha"
direction = "upstream-origin"
""",
            "must be sorted",
            id="unsorted rows",
        ),
        pytest.param(
            """
[[skills]]
name = "declined-thing"
upstream = "declined-thing"
direction = "upstream-origin"
""",
            "both shipped and unported",
            id="shipped and declined at once",
        ),
    ],
)
def test_the_loader_rejects(tmp_path: Path, rows: str, expected: str) -> None:
    with pytest.raises(SyncRecordError, match=expected):
        _ = load_sync_record(_write(tmp_path, rows))


def test_a_record_without_an_unported_list_is_rejected(tmp_path: Path) -> None:
    """Without it, a new upstream skill is indistinguishable from a declined one."""
    with pytest.raises(SyncRecordError, match="unported"):
        _ = load_sync_record(_write(tmp_path, _VALID_ROWS, unported=""))


def test_a_malformed_record_names_its_file(tmp_path: Path) -> None:
    path = tmp_path / "record.toml"
    _ = path.write_text("this is not toml = = =", encoding="utf-8")
    with pytest.raises(SyncRecordError, match="not valid TOML"):
        _ = load_sync_record(path)


# --------------------------------------------------------------------------------------
# The measurement, against a synthetic upstream
# --------------------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    # Identity and signing are forced off so the fixture is hermetic: a maintainer with
    # commit signing configured globally would otherwise fail this test for reasons that
    # have nothing to do with the code under test.
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git {args}: {result.stderr}"


def _commit(repo: Path, path: str, text: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    out = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout.strip()


@pytest.fixture
def synthetic_upstream(tmp_path: Path) -> tuple[Path, str, str]:
    """An upstream-shaped repo: a base commit, two advances, and a later addition."""
    repo = tmp_path / "upstream"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    base = _commit(repo, ".claude/skills/alpha/SKILL.md", "v1\n", "add alpha")
    _ = _commit(repo, ".claude/skills/steady/SKILL.md", "v1\n", "add steady")
    base_after_steady = _commit(
        repo, ".claude/skills/declined-thing/SKILL.md", "v1\n", "add declined"
    )
    _ = _commit(repo, ".claude/skills/alpha/SKILL.md", "v2\n", "advance alpha")
    _ = _commit(repo, ".claude/skills/alpha/references/more.md", "x\n", "extend alpha")
    _ = _commit(repo, ".claude/skills/newcomer/SKILL.md", "v1\n", "add newcomer")
    return repo, base, base_after_steady


def test_drift_counts_only_commits_touching_the_skill(
    synthetic_upstream: tuple[Path, str, str], tmp_path: Path
) -> None:
    repo, base, base_after_steady = synthetic_upstream
    record = load_sync_record(
        _write(
            tmp_path,
            f"""
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "upstream-origin"
base = "{base}"

[[skills]]
name = "steady"
upstream = "steady"
direction = "upstream-origin"
base = "{base_after_steady}"
""",
        )
    )
    drift = measure_drift(repo, record)
    counts = {d.name: d.commits for d in drift.measured}
    # Two commits touched alpha after `base` -- one changing SKILL.md, one adding a
    # references/ file. A SKILL.md-only check would have reported 1 and understated it.
    assert counts == {"alpha": 2, "steady": 0}
    assert [d.name for d in drift.behind] == ["alpha"]
    assert drift.total_commits == 2
    assert not drift.clean


def test_an_upstream_skill_in_neither_table_is_reported_undeclared(
    synthetic_upstream: tuple[Path, str, str], tmp_path: Path
) -> None:
    """The addition signal: this is how a new upstream skill gets noticed at all."""
    repo, base, _ = synthetic_upstream
    record = load_sync_record(
        _write(
            tmp_path,
            f"""
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "upstream-origin"
base = "{base}"
""",
        )
    )
    drift = measure_drift(repo, record)
    # `declined-thing` is in the unported list, so it must NOT be reported; `newcomer`
    # and `steady` are in neither table, so they must be.
    assert drift.undeclared == ("newcomer", "steady")


def test_a_row_pointing_nowhere_is_reported_not_silently_zero(
    synthetic_upstream: tuple[Path, str, str], tmp_path: Path
) -> None:
    """The failure mode that would make the whole check a rubber stamp.

    `rev-list --count` over a path that does not exist returns 0, so a row with a wrong
    upstream name or a base predating the directory reports "in sync" while measuring
    nothing at all. Both cases must surface instead.
    """
    repo, base, _ = synthetic_upstream
    record = load_sync_record(
        _write(
            tmp_path,
            f"""
[[skills]]
name = "misnamed"
upstream = "alpha-typo"
direction = "upstream-origin"
base = "{base}"

[[skills]]
name = "newcomer"
upstream = "newcomer"
direction = "upstream-origin"
base = "{base}"
""",
        )
    )
    drift = measure_drift(repo, record)
    # Wrong name: the directory is not upstream at all.
    assert drift.vanished == ("alpha-typo",)
    # Right name, but the base predates the directory -- so the base is wrong, and a
    # count against it would be meaningless rather than zero.
    assert len(drift.unresolved) == 1
    assert "newcomer" in drift.unresolved[0]
    assert not drift.measured


def test_an_unresolvable_base_is_named_as_such(
    synthetic_upstream: tuple[Path, str, str], tmp_path: Path
) -> None:
    """The two ways a row can fail to measure need different fixes, so they read apart.

    An unresolvable base is a bad SHA or a shallow clone; a resolvable base with no such
    directory means the `upstream` name is wrong. One message for both would send the
    reader to the wrong field of the record.
    """
    repo, base, _ = synthetic_upstream
    record = load_sync_record(
        _write(
            tmp_path,
            f"""
[[skills]]
name = "bad-base"
upstream = "alpha"
direction = "upstream-origin"
base = "{_SHA_B}"

[[skills]]
name = "bad-name"
upstream = "alpha-typo"
direction = "upstream-origin"
base = "{base}"
""",
            upstream_commit=base,
        )
    )
    drift = measure_drift(repo, record)
    assert len(drift.unresolved) == 1, (
        f"expected only the bad-base row in unresolved, got {drift.unresolved}"
    )
    assert (
        "base ref" in drift.unresolved[0] and "does not resolve" in drift.unresolved[0]
    )
    # The wrong-name row is a different fault and belongs in `vanished`.
    assert drift.vanished == ("alpha-typo",)
    assert not drift.measured


def test_the_report_phrases_kit_origin_drift_differently(
    synthetic_upstream: tuple[Path, str, str], tmp_path: Path
) -> None:
    """The direction field has to change the output, or it is inert data.

    "N commits behind" is false for a skill this repo authored: upstream's later edits
    there are contributions to review, not a backlog to absorb.
    """
    repo, base, _ = synthetic_upstream
    record = load_sync_record(
        _write(
            tmp_path,
            f"""
[[skills]]
name = "alpha"
upstream = "alpha"
direction = "kit-origin"
origin = "kit:{_SHA_B}"
upstream_adopted = "{base}"
base = "{base}"
""",
        )
    )
    text = format_report(record, measure_drift(repo, record))
    assert "THIS repo authored" in text
    assert "commits behind" not in text


def test_an_unmeasurable_upstream_says_so_rather_than_guessing(tmp_path: Path) -> None:
    record = load_sync_record(_write(tmp_path, _VALID_ROWS))
    text = format_report(record, None, why="nowhere to look")
    assert "NOT MEASURED" in text
    assert "nowhere to look" in text


def test_the_report_is_ascii_only(tmp_path: Path) -> None:
    """Some consoles default to a code page that cannot encode an em dash, and the
    hygiene contract bans the environment-variable workaround for that as a
    machine-specific rule. A report that raises UnicodeEncodeError on the maintainer's
    terminal is not a report, so the shipped record's own summary is checked here, not
    just a fixture."""
    text = format_report(load_sync_record(), None)
    assert text.isascii(), "non-ASCII in report output: " + repr(
        [c for c in text if not c.isascii()]
    )


# --------------------------------------------------------------------------------------
# The non-blocking contract
# --------------------------------------------------------------------------------------


def test_main_never_fails_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Charter DoD 5: report first, gate later. Every path returns 0.

    Including the invalid-record path -- the gate on record validity is the rest of this
    file, which needs no upstream repository. Making the CI report fail as well would
    break the non-blocking contract for a defect already caught earlier and louder.
    """
    monkeypatch.delenv("LEMMI_UPSTREAM_REPO", raising=False)
    assert main([]) == 0
    assert "NOT MEASURED" in capsys.readouterr().out

    assert main(["--repo", str(tmp_path / "does-not-exist")]) == 0
    assert "NOT MEASURED" in capsys.readouterr().out

    broken = tmp_path / "broken.toml"
    _ = broken.write_text("[sync]\n", encoding="utf-8")
    assert main(["--record", str(broken)]) == 0
    assert "RECORD INVALID" in capsys.readouterr().out


def test_the_record_lives_where_the_procedure_says_it_does() -> None:
    """A broken pointer between the two deliverables would strand both."""
    assert RECORD_PATH.is_file()
    procedure = RECORD_PATH.parent / "syncing-from-upstream.md"
    assert procedure.is_file(), "the sync procedure document is missing"
    text = procedure.read_text(encoding="utf-8")
    assert RECORD_PATH.name in text, "the procedure never names the pin file"
    assert "tests/upstream_sync.py" in text, "the procedure never names the check"


# --------------------------------------------------------------------------------------
# The extraction window
# --------------------------------------------------------------------------------------


def test_the_recorded_window_is_the_measured_one() -> None:
    """Pinned like the kit-origin set, and for the same reason.

    The 2026-08-23 refresh based every skill on a commit four days INSIDE this repo's
    extraction window, so upstream's own additions from that gap were eligible to be
    classified as deliberate kit deletions and kept deleted. The proof was
    `skill-researcher`: all 19 of its window-added lines absent from the shipped file
    while it reported ZERO drift against the pin, because drift counts upstream commits
    since a base that is four days wrong.

    Reviewed and paid on 2026-08-24 -- the record's comment block says what was carried.
    This test now pins the REVIEWED state for the same reason it pinned the open one:
    deriving the affected list from the record would test nothing, and a later edit that
    quietly reopens or deletes the table should have to argue with a test.
    """
    window = load_sync_record().window
    assert window is not None, "the extraction-window debt is no longer recorded"
    assert window.status == "reviewed-2026-08-24", (
        "the window was reviewed on 2026-08-24 and the record carries the note saying "
        "what was carried. If it is reviewed again, move this pin and update that note "
        "-- do not delete the table, and do not silently return it to `unreviewed`"
    )
    assert window.kit_first_commit.startswith("kit:")
    assert len(window.affected) == 16, (
        f"expected 16 window-affected upstream directories, got {len(window.affected)}"
    )
    assert "skill-researcher" in window.affected, (
        "the spot-checked skill is missing from the affected list"
    )


def test_a_record_without_a_window_table_is_valid(tmp_path: Path) -> None:
    """The table goes away once the debt is closed; its absence must not be an error."""
    record = load_sync_record(_write(tmp_path, _VALID_ROWS))
    assert record.window is None


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        pytest.param(
            f"""
[extraction_window]
kit_first_commit = "{_SHA_A}"
base_used_by_refresh = "{_SHA_A}"
status = "unreviewed"
affected = ["alpha"]
""",
            "must carry the `kit:` prefix",
            id="kit commit without its repo prefix",
        ),
        pytest.param(
            f"""
[extraction_window]
kit_first_commit = "kit:{_SHA_A}"
base_used_by_refresh = "{_SHA_A}"
status = "unreviewed"
affected = ["alpha", "who-is-this"]
""",
            "does not otherwise mention",
            id="affected names an unknown upstream directory",
        ),
        pytest.param(
            f"""
[extraction_window]
kit_first_commit = "kit:{_SHA_A}"
base_used_by_refresh = "{_SHA_A}"
status = "unreviewed"
affected = ["beta", "alpha"]
""",
            "must be sorted",
            id="unsorted affected list",
        ),
        pytest.param(
            f"""
[extraction_window]
kit_first_commit = "kit:{_SHA_A}"
base_used_by_refresh = "{_SHA_A}"
status = "unreviewed"
affected = []
""",
            "non-empty list",
            id="empty affected list",
        ),
    ],
)
def test_the_loader_rejects_a_bad_window(
    tmp_path: Path, extra: str, expected: str
) -> None:
    with pytest.raises(SyncRecordError, match=expected):
        _ = load_sync_record(_write(tmp_path, _VALID_ROWS, extra=extra))


_WINDOW_ROW = """
[[skills]]
name = "steady"
upstream = "steady"
direction = "upstream-origin"
"""


def test_window_debt_is_measured_apart_from_drift(
    synthetic_upstream: tuple[Path, str, str], tmp_path: Path
) -> None:
    """The design claim: window debt must not inflate the drift numbers.

    `steady` moved upstream inside the window but not since the pin. It must show zero
    drift and still appear in the window block -- if the two were merged, a maintainer
    could not tell a one-time base error from upstream moving today, and 16 skills would
    sit permanently "behind" until someone silenced the check.
    """
    repo, base, base_after_steady = synthetic_upstream
    record = load_sync_record(
        _write(
            tmp_path,
            _WINDOW_ROW,
            extraction_base=base,
            upstream_commit=base_after_steady,
            extra=f"""
[extraction_window]
kit_first_commit = "kit:{_SHA_A}"
base_used_by_refresh = "{base_after_steady}"
status = "unreviewed"
affected = ["steady"]
""",
        )
    )
    drift = measure_drift(repo, record)
    # Zero ongoing drift: nothing touched `steady` after the pin.
    assert [d.commits for d in drift.measured] == [0]
    assert not drift.behind
    assert drift.total_commits == 0
    # But one commit of window debt, reported separately.
    assert [(d.name, d.commits) for d in drift.window] == [("steady", 1)]

    text = format_report(record, drift)
    assert "EXTRACTION WINDOW (unreviewed)" in text
    assert "IN SYNC" in text, "ongoing drift and window debt must be reported apart"


def test_a_window_list_missing_a_skill_is_reported(
    synthetic_upstream: tuple[Path, str, str], tmp_path: Path
) -> None:
    """A recorded list nothing re-derives is a claim, not a measurement."""
    repo, base, base_after_steady = synthetic_upstream
    record = load_sync_record(
        _write(
            tmp_path,
            _WINDOW_ROW,
            extraction_base=base,
            upstream_commit=base_after_steady,
            extra=f"""
[extraction_window]
kit_first_commit = "kit:{_SHA_A}"
base_used_by_refresh = "{base_after_steady}"
status = "unreviewed"
affected = ["steady"]
""",
        )
    )
    drift = measure_drift(repo, record)
    # `declined-thing` was also added inside the window and is not in `affected`.
    assert drift.window_unlisted == ("declined-thing",)
    assert "RECORD INCOMPLETE" in format_report(record, drift)


def test_the_shipped_record_holds_up_against_real_upstream() -> None:
    """Skipped without an upstream checkout; the point is that it is runnable at all.

    This is the check that made the window finding trustworthy rather than plausible:
    the recorded list of 16 was re-derived from upstream history and matched exactly.
    """
    record = load_sync_record()
    repo = resolve_upstream(None)
    if repo is None:
        pytest.skip(f"set ${ENV_VAR} to a real upstream checkout to run this")
    try:
        drift = measure_drift(repo, record)
    except UpstreamUnavailable as exc:
        pytest.skip(f"upstream checkout unusable: {exc}")
    assert not drift.window_unlisted, (
        "upstream touched these inside the window but the record omits them: "
        f"{drift.window_unlisted}"
    )
    assert not drift.unresolved, f"correspondence map errors: {drift.unresolved}"
    assert not drift.undeclared, f"undeclared upstream skills: {drift.undeclared}"
    assert not drift.vanished, f"vanished upstream skills: {drift.vanished}"
