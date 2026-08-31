"""The hygiene contract, applied to commit messages -- the surface no scan reached.

`test_assets.py` scans `assets_root()`. `test_publication_hygiene.py` widened that to
everything `git ls-files` reports. Both stop at the file boundary, and a repository
publishes more than its files: every commit message in every branch becomes readable
the moment the repository goes public, and no test in this suite had ever looked at
one.

**This was not hypothetical.** Commit `0b2ea4f` named the private source project in
its message and sized it -- an AGENTS.md line count against a Python line count and a
file count. The commit immediately after it, `b999aaf` ("Strip the private arm's
identity and metrics from a record that goes public"), removed exactly that from the
tracked file and explained why in its own message: *"Sizing a private repository is
still describing it."* The file was fixed. The parent's message was not, and the
fixing commit's subject line is a signpost pointing a reader straight at it.

Nothing failed, because `git ls-files` does not enumerate commit messages. That is
this repository's own recurring defect -- a guard's scan surface deciding its
coverage -- caught here on the one surface that a public flip makes irreversible:
messages can be rewritten while a repository is private, and cannot once clones,
forks and archives exist.

**Why this scans a subset of `_FORBIDDEN`, and why the subset is asserted rather
than assumed.** The forbidden patterns are not one kind of rule. Some are
*confidentiality* rules -- they name a private project, and naming it is a leak
wherever the text appears. Others are *portability* rules -- an absolute path or a
machine-specific workaround is a defect because the text ships as instructions an
agent follows on someone else's machine. A commit message is never executed by an
agent and never installed by an adopter, so a portability pattern in a message costs
nothing; and in practice every commit here that carries one is a commit that *built
or fixed the pattern guards*, and had to quote the shape it was banning.

Narrowing a scan is exactly how a guard comes to pass while blind, so the narrowing
is not left to a comment. `test_every_forbidden_reason_is_classified` asserts the two
buckets are exhaustive and disjoint over `_FORBIDDEN`, which means a pattern added to
`test_assets.py` cannot land silently in the unscanned half -- it fails this file
until somebody decides which kind of rule it is.
"""

import subprocess
from pathlib import Path

import pytest
from test_assets import (
    _FORBIDDEN as _ASSET_FORBIDDEN,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Reasons whose harm is disclosure: the text identifies a repository outsiders cannot
# read. These are scanned in commit messages.
_CONFIDENTIALITY: frozenset[str] = frozenset(
    {
        "source-project reference",
        "source-project backup reference",
    }
)

# Reasons whose harm is that shipped instructions stop working on another machine.
# Not scanned in commit messages -- see the module docstring.
_PORTABILITY: frozenset[str] = frozenset(
    {
        "absolute macOS home path",
        "absolute Linux home path",
        "Windows drive-letter path",
        "machine-specific host rule",
        "machine-specific console workaround",
        "dated learnings citation",
        "dated retrospective citation",
        "hard-coded skill-script path (use ${CLAUDE_SKILL_DIR})",
    }
)

# A commit message that is itself about the ban has to name what it bans. Keyed by
# subject rather than by SHA on purpose: a message rewrite changes every SHA below it,
# which would invalidate a SHA-keyed allowlist wholesale at exactly the moment the
# rewrite needs verifying. Subjects survive a body rewrite.
#
# Empty, deliberately. Every commit that carried a confidentiality pattern carried a
# real one; none was discussing the rule. An entry here needs a comment saying why the
# message cannot be written without the name.
_ALLOWED_SUBJECTS: dict[str, tuple[str, ...]] = {}


def _commit_messages(repo: Path) -> list[tuple[str, str, str]]:
    """(sha, subject, full message) for every commit reachable from any ref."""
    result = subprocess.run(
        ["git", "log", "--all", "--format=%H%x00%s%x00%B%x01"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"git log failed in {repo}, so the commit surface cannot be checked: "
            f"{result.stderr.decode('utf-8', 'replace')}"
        )

    records: list[tuple[str, str, str]] = []
    for raw in result.stdout.decode("utf-8", "replace").split("\x01"):
        if not raw.strip():
            continue
        sha, _, rest = raw.strip().partition("\x00")
        subject, _, body = rest.partition("\x00")
        records.append((sha, subject, body))
    return records


def _leaks(repo: Path) -> list[str]:
    """Confidentiality-pattern hits across every commit message in `repo`."""
    scanned = {reason for reason in _CONFIDENTIALITY}
    violations: list[str] = []
    for sha, subject, body in _commit_messages(repo):
        allowed = _ALLOWED_SUBJECTS.get(subject, ())
        for pattern, why in _ASSET_FORBIDDEN:
            if why not in scanned or why in allowed:
                continue
            for match in pattern.finditer(body):
                violations.append(f"{sha[:8]} {subject!r}: {why} ({match.group(0)!r})")
    return violations


def test_the_commit_surface_is_not_empty() -> None:
    """Guard the guard: a broken enumeration would make the scan below vacuous.

    Stated as a comparison against `rev-list --count` rather than as a hand-written
    floor, because a floor is a number that goes stale and this repository has paid
    for that ten times. The two instruments must agree.
    """
    scanned = len(_commit_messages(_REPO_ROOT))
    counted = int(
        subprocess.run(
            ["git", "rev-list", "--all", "--count"],
            cwd=_REPO_ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode()
    )
    assert scanned == counted, (
        f"parsed {scanned} commit messages but git counts {counted} commits — the "
        "record separator has probably collided with message content, which would "
        "silently shrink the scan surface"
    )
    assert scanned > 0, "no commits found, so every check below would pass vacuously"


def test_every_forbidden_reason_is_classified() -> None:
    """Exhaustive and disjoint over `_FORBIDDEN`.

    Without this, a pattern added to `test_assets.py` lands in neither bucket and is
    silently unscanned here -- the scan-surface failure this file exists to close,
    reintroduced through the back door. A reason in both buckets is the mirror defect:
    two classifications read as better covered, not worse.
    """
    reasons = {why for _, why in _ASSET_FORBIDDEN}
    classified = _CONFIDENTIALITY | _PORTABILITY

    assert not (overlap := _CONFIDENTIALITY & _PORTABILITY), (
        f"reasons classified as both confidentiality and portability: {sorted(overlap)}"
    )
    assert not (unclassified := reasons - classified), (
        f"forbidden reasons in neither bucket: {sorted(unclassified)} — decide whether "
        "each one leaks a private project (add to _CONFIDENTIALITY, it will be scanned "
        "in commit messages) or breaks a shipped instruction (add to _PORTABILITY)"
    )
    assert not (unknown := classified - reasons), (
        f"classified reasons that no longer exist in _FORBIDDEN: {sorted(unknown)} — "
        "a stale entry means the bucket no longer describes the pattern set"
    )


def test_the_scan_catches_a_planted_leak(tmp_path: Path) -> None:
    """A guard never shown to fail has not been shown to work.

    Built against a synthetic repository rather than by asserting on real history, so
    the proof survives the rewrite that is about to clean real history -- after which
    the true positives are gone and there is nothing left to demonstrate on.
    """
    repo = tmp_path / "planted"
    repo.mkdir()

    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)

    run("init", "-q", "-b", "main")
    run("config", "user.email", "fixture@example.invalid")
    run("config", "user.name", "fixture")
    (repo / "f.txt").write_text("x", encoding="utf-8")
    run("add", "f.txt")

    run("commit", "-qm", "Clean subject\n\nA body with nothing forbidden in it.")
    assert not _leaks(repo), "a clean history must produce no findings"

    (repo / "f.txt").write_text("y", encoding="utf-8")
    run("add", "f.txt")
    run(
        "commit",
        "-qm",
        "Innocent subject\n\nPrimary arm: lemmi-ai-api, sized at 999,999 files.",
    )

    found = _leaks(repo)
    assert len(found) == 1, f"expected exactly one finding, got {found}"
    assert "source-project reference" in found[0]
    assert "lemmi-ai-api" in found[0]


def test_no_commit_message_leaks_the_source_project() -> None:
    violations = _leaks(_REPO_ROOT)
    assert not violations, (
        "commit messages naming a private project:\n"
        + "\n".join(violations)
        + "\n\nA commit message is published with the repository and cannot be "
        "rewritten once clones and forks exist. Rewrite the message while the "
        "repository is still private (git filter-repo --message-callback), or, if the "
        "message genuinely cannot be written without the name, add its subject to "
        "_ALLOWED_SUBJECTS with a comment saying why."
    )


def test_the_allowlist_has_no_stale_entries() -> None:
    """A dead allowlist entry silently exempts the next real leak."""
    subjects = {subject for _, subject, _ in _commit_messages(_REPO_ROOT)}
    by_reason = {why for _, why in _ASSET_FORBIDDEN}
    stale: list[str] = []
    for subject, reasons in sorted(_ALLOWED_SUBJECTS.items()):
        if subject not in subjects:
            stale.append(f"{subject!r}: allowlisted but no commit has that subject")
        for reason in reasons:
            if reason not in by_reason:
                stale.append(f"{subject!r}: allowlists unknown reason {reason!r}")
            elif reason not in _CONFIDENTIALITY:
                stale.append(
                    f"{subject!r}: allowlists {reason!r}, which this scan does not "
                    "check — the exemption does nothing and hides that fact"
                )
    assert not stale, "stale _ALLOWED_SUBJECTS entries:\n" + "\n".join(stale)
