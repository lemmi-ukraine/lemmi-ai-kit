#!/usr/bin/env python
"""Mechanical gates for the initiative-cleanup workflow.

WHY THIS IS A SCRIPT AND NOT MORE PROSE
---------------------------------------
SKILL.md stated "partition per FILE, never per directory" four separate times, and a
2026-08-09 cleanup run violated it anyway on its first pass -- caught only by a later
self-review, not by the rule. That matches the recorded finding that prose
rules do not move the number (AGENTS.md: the cd-prefix rule was written in three places
and the first post-rule session out-violated the entire pre-rule window; what fixed it
was a hook). So the checks that decide whether a file gets deleted live here, where they
exit non-zero, instead of in a paragraph that reads as satisfied.

Every subcommand is READ-ONLY. Nothing here deletes, stages, or writes to the repo.

THE SECOND AXIS, ADDED 2026-08-19
---------------------------------
Until this revision every gate here answered ONE question: *is the work this file describes
implemented?* (SKILL.md step 4a). That question is right for a spec and structurally
unanswerable for session scaffolding -- a dispatch brief describes no code, so no symbol
exists to prove and it can never satisfy 4a. Measured on `.specs/feedback-relevance-and-
realism` (2026-08-19): 51 briefs + 85 capture files = 136 of 157 tracked
files were unreachable by the only gate the skill had, and the run still reported success.

Two blindnesses let that pass, both reproduced before being fixed:
  * `census` partitions on git status (tracked/untracked/ignored) -- a RECOVERABILITY axis,
    not a KIND axis. Every file was tracked => all "claimed" => PASS.
  * `census`'s row key was the first two path components, so a --root that is itself two
    deep collapsed the whole initiative into ONE row, and `coverage` counted DIRECTORIES, so
    a plan naming the initiative directory dispositioned all 157 files at once.

So `kinds` adds the orthogonal axis, per FILE, and refuses to pass on an unclassified file.
The rule it encodes: **a kind alone never authorises a move.** Disposition is the conjunction
of the kind and that kind's life-ending condition. Measured counter-example -- the 25
measurement scripts in that initiative are "measurement", whose naive disposition is "archive
off-repo, it never needed to be in git", and every one of them is load-bearing: some are
invoked by a brief whose header says "DO NOT RUN THIS YET", others are the declared replay
point for an upload that has not happened.

Subcommands
-----------
  census    Per-file tracked/untracked/ignored inventory of a root, plus an exhaustiveness
            assertion: every file on disk must be claimed by exactly one partition.
  kinds     Per-file ARTIFACT-KIND classification + completeness assertion. Exits non-zero
            on any file no kind claims. This is the gate the 135 files walked past.
  extraction  Is a scaffolding file SPENT? Only if its reasoning already lives in a decision
            record. A brief with no other home is not spent, whatever its session's status.
  fundep    Is a path read by an executable (shell array, python literal)? Then it is a
            FUNCTIONAL dependency, not a citation, and moving it breaks a program.
  evidence  Classify a symbol as CODE / DOC-ONLY / ABSENT, and flag it if it is shared
            across several spec directories (a shared symbol proves nothing about any one).
  refs      Inbound-reference sweep for a deletion target, using a working-tree walk --
            `git grep` reads the index and cannot see untracked files.
  coverage  Assert that every FILE under a root is dispositioned by the plan document, so a
            partial audit cannot present itself as a complete one.

Exit codes: 0 = gate passed, 1 = gate failed, 2 = usage error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path, PurePosixPath

# Extensions treated as CODE for implementation evidence. A hit anywhere else -- above all
# in a README -- is documentation OF the thing, not the thing. A 2026-08-09 run scored 34
# specs "implemented" and 14 of those hits were in README.md files.
CODE_SUFFIXES = frozenset(
    {".py", ".ts", ".tsx", ".js", ".sql", ".toml", ".yaml", ".yml"}
)
DOC_SUFFIXES = frozenset({".md", ".txt", ".rst"})

# Reference sweeps skip these: archives and scratch, where a stale pointer is expected and
# rewriting one would falsify a historical record.
ARCHIVE_MARKERS = (
    "/.ai/tmp/",
    "/backups/",
    "/.git/",
    "/node_modules/",
    "/__pycache__/",
)

# Files whose citation of a spec makes that spec an authority (a decision record), not a
# disposable implementation artifact. A 2026-08-09 run nearly deleted the F11 decision
# record that CLAUDE.md names as the authority for a shipped skill's core policy.
AUTHORITY_FILES = ("CLAUDE.md", "AGENTS.md")

# ---------------------------------------------------------------------------
# THE ARTIFACT-KIND AXIS
# ---------------------------------------------------------------------------
# Each kind pairs with the condition that ENDS ITS LIFE. The disposition is the conjunction:
# a kind alone never authorises a move. `LIFE_END` text is printed next to every row so a
# plan cannot quote a kind without quoting what would have to be true to act on it.
KIND_DECISION = "decision-record"
KIND_SLICE_SPEC = "slice-spec"
KIND_SCAFFOLDING = "scaffolding"
KIND_ROLLBACK = "rollback-anchor"
KIND_INSTRUMENT = "instrument"
KIND_RESULT = "result"

LIFE_END: dict[str, str] = {
    KIND_DECISION: "NOTHING ends it. It is the durable why -- keep, always. Status transition only",
    KIND_SLICE_SPEC: "step 4a: the deliverable exists in CODE (`evidence` = IMPLEMENTED)",
    KIND_SCAFFOLDING: "the session returned AND its reasoning is in a decision record (`extraction`)",
    KIND_ROLLBACK: "the change it reverts is DEPLOYED **and** VALIDATED -- operator-confirmed",
    KIND_INSTRUMENT: "every documented invocation is spent: none future-scheduled, none open",
    KIND_RESULT: "the claim it supports is closed",
}

# Ordered, first match wins. Deliberately conservative: anything these do not name is
# UNCLASSIFIED and fails the gate. Forcing an explicit declaration is the whole point --
# a default bucket is how 135 files got a disposition nobody chose.
DEFAULT_KIND_RULES: tuple[tuple[str, str], ...] = (
    # Every doc-shaped rule is pinned to a doc EXTENSION. Measured while building this gate:
    # an unpinned `*changelog*` claimed `pending-edits/apply_changelog_ub_row.py` as a
    # decision-record, hiding a script from the instrument checks. A name pattern must never
    # outrank what the file actually is.
    (KIND_DECISION, "topology.md"),
    (KIND_DECISION, "roadmap.md"),
    (KIND_DECISION, "execution-plan.md"),
    (KIND_DECISION, "forward-plan.md"),
    (KIND_DECISION, "*changelog*.md"),
    (KIND_DECISION, "*DECISION*.md"),
    (KIND_DECISION, "*-decision.md"),
    (KIND_DECISION, "*ADR*.md"),
    (KIND_DECISION, "*PDR*.md"),
    # Slice specs: the shape spec-driven-dev emits.
    (KIND_SLICE_SPEC, "requirements.md"),
    (KIND_SLICE_SPEC, "design.md"),
    (KIND_SLICE_SPEC, "tasks.md"),
    (KIND_SLICE_SPEC, "spec.md"),
    # Session scaffolding: describes no code, so step 4a can never reach it.
    (KIND_SCAFFOLDING, "briefs/*.md"),
    (KIND_SCAFFOLDING, "*dispatch*.md"),
    (KIND_SCAFFOLDING, "*edit-sheet*.md"),
    (KIND_SCAFFOLDING, "*orchestrator-handoff*.md"),
    (KIND_SCAFFOLDING, "*pending-edits/*.md"),
    # Rollback anchors: byte captures and the manifests that pin them.
    (KIND_ROLLBACK, "*.sha256"),
    (KIND_ROLLBACK, "*.txt"),
    # Instruments: anything executable.
    (KIND_INSTRUMENT, "*.py"),
    (KIND_INSTRUMENT, "*.sh"),
    # Results: machine-readable outputs.
    (KIND_RESULT, "*.json"),
    (KIND_RESULT, "*.sql"),
    (KIND_RESULT, "*.csv"),
)

# Markers inside a file that make it PENDING regardless of kind -- its own text says its
# work has not happened. Measured: one deferred-gate brief opens
# "DO NOT RUN THIS YET ... scheduled ~2 weeks after the prompt upload" and literally invokes
# two measurement scripts by repo-root-relative path. Archiving either would have broken a
# session that has not run.
PENDING_MARKERS = (
    "DO NOT RUN THIS YET",
    "DO NOT RUN YET",
    "not yet run",
    "scheduled for",
    "after the prompt upload",
    "after deploy",
    "must be sequenced",
)

# Markers on the CITING line. A decision record that mentions a brief as still-open is not
# evidence the brief is spent -- it is evidence of the opposite, and it reads as a citation
# either way. Measured: a roadmap cited a brief as "**OPEN.** Sent to settle ... Blocks the
# gate", and a citation-counting gate scored that brief SPENT.
OPEN_STATE_MARKERS = (
    "open",
    "pending",
    "blocks",
    "blocked",
    "awaiting",
    "unresolved",
    "not yet",
    "todo",
    "still to",
    "in progress",
)

MANIFEST_NAME = "cleanup-kinds.txt"


def repo_root() -> Path:
    """Walk up from this file to the checkout root, else the working directory.

    Never hardcode an absolute path: drive letter, username and clone location all
    differ per engineer. The fallback is what makes this work from a plugin install,
    where no ancestor of this script is inside the adopter's repository at all.
    """
    here = Path(__file__).resolve()
    return next((p for p in here.parents if (p / ".git").exists()), Path.cwd())


def git(root: Path, *args: str) -> list[str]:
    """Run a git command and return non-empty stdout lines. Never raises on a non-zero
    exit -- an empty result and a failed command are distinguished by the caller when it
    matters, and most callers here treat both as 'no rows'."""
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _partition(root: Path, target: str) -> tuple[set[str], set[str], set[str]]:
    tracked = set(git(root, "ls-files", "--", target))
    untracked = set(
        git(root, "ls-files", "--others", "--exclude-standard", "--", target)
    )
    ignored = set(
        git(
            root,
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--",
            target,
        )
    )
    return tracked, untracked, ignored


def cmd_census(root: Path, target: str) -> int:
    """Per-file inventory + exhaustiveness. Directory-level checks are the trap this
    replaces: `git ls-files --error-unmatch <dir>` exits 0 if ANY file under it is
    indexed, so a mixed directory passes while an untracked file inside it is
    recoverable by nothing."""
    tracked, untracked, ignored = _partition(root, target)
    claimed = tracked | untracked | ignored

    base = root / target
    if not base.exists():
        print(f"FAIL  target does not exist: {target}")
        return 1

    on_disk = {
        p.relative_to(root).as_posix()
        for p in base.rglob("*")
        if p.is_file()
        and not any(m in f"/{p.relative_to(root).as_posix()}" for m in ARCHIVE_MARKERS)
    }
    unclaimed = on_disk - claimed

    dirs: dict[str, dict[str, int]] = {}
    for path in sorted(on_disk):
        # Group ONE level below the target, never by absolute path depth. The previous key
        # was the first two path components, so a --root already two deep (an initiative
        # directory) collapsed every file under it into a single row: measured 2026-08-19,
        # `census --root .specs/<initiative>` printed ONE line for 156
        # files and called it a complete per-file inventory.
        rest = path[len(target) :].lstrip("/") if path.startswith(target) else path
        head = rest.split("/", 1)[0]
        key = f"{target}/{head}" if rest else path
        row = dirs.setdefault(key, {"tracked": 0, "untracked": 0, "ignored": 0})
        if path in tracked:
            row["tracked"] += 1
        elif path in untracked:
            row["untracked"] += 1
        elif path in ignored:
            row["ignored"] += 1

    print(f"CENSUS  {target}   ({len(dirs)} entries, {len(on_disk)} files on disk)")
    print()
    print(f"  {'entry':<52} {'trk':>4} {'untrk':>6} {'ign':>4}  flag")
    fully_untracked = 0
    mixed = 0
    for name, row in sorted(dirs.items()):
        flag = ""
        if row["tracked"] == 0 and row["untracked"] > 0:
            flag = "NO GIT HISTORY - deletion is permanent"
            fully_untracked += 1
        elif row["tracked"] > 0 and row["untracked"] > 0:
            flag = "MIXED - dir-level checks lie here"
            mixed += 1
        print(
            f"  {name:<52} {row['tracked']:>4} {row['untracked']:>6} {row['ignored']:>4}  {flag}"
        )

    print()
    print(f"  fully untracked entries : {fully_untracked}")
    print(f"  mixed entries           : {mixed}")

    if unclaimed:
        print()
        print(
            f"FAIL  {len(unclaimed)} file(s) claimed by NO partition -- resolve before removing anything:"
        )
        for path in sorted(unclaimed)[:20]:
            print(f"        {path}")
        return 1

    print()
    print("PASS  every file on disk is claimed by exactly one partition")
    return 0


def _load_manifest(
    root: Path, target: str, manifest: str | None
) -> list[tuple[str, str]]:
    """Read `kind: glob` lines from an initiative's own kind manifest.

    The manifest is a COMMITTED artifact, not a convenience: declaring which kind each
    artifact belongs to is a decision, and a decision that lives only in a session's head is
    the thing this gate exists to stop. Lines are `kind: glob`, `#` comments ignored.
    """
    path = root / manifest if manifest else root / target / MANIFEST_NAME
    if not path.exists():
        return []
    rules: list[tuple[str, str]] = []
    for lineno, raw in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            print(f"WARN  {path.name}:{lineno}: expected `kind: glob`, got {line!r}")
            continue
        kind, glob = (part.strip() for part in line.split(":", 1))
        if kind not in LIFE_END:
            print(f"WARN  {path.name}:{lineno}: unknown kind {kind!r} -- ignored")
            continue
        rules.append((kind, glob))
    return rules


def _classify(rel: str, rules: list[tuple[str, str]]) -> str | None:
    """First matching rule wins. Match on the path relative to the target root, and also on
    the bare filename, so a rule may name either `briefs/*` or `topology.md`."""
    name = rel.rsplit("/", 1)[-1]
    for kind, glob in rules:
        if PurePosixPath(rel).match(glob) or PurePosixPath(name).match(glob):
            return kind
        # A directory-prefix rule such as `briefs/*` must also claim files nested deeper.
        if glob.endswith("/*") and (
            rel.startswith(glob[:-1]) or f"/{glob[:-1]}" in rel
        ):
            return kind
    return None


def cmd_kinds(
    root: Path, target: str, manifest: str | None, listing: bool = False
) -> int:
    """Per-FILE artifact-kind classification, with a completeness assertion.

    This is the gate whose absence let 135 of 156 files walk past a cleanup run that then
    reported success. `census` already claimed every one of them -- on the git-status axis,
    which says only whether a delete is recoverable, never whether it is warranted.
    """
    base = root / target
    if not base.exists():
        print(f"FAIL  target does not exist: {target}")
        return 2

    rules = _load_manifest(root, target, manifest) + list(DEFAULT_KIND_RULES)
    files = sorted(
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file()
        and not any(m in f"/{p.relative_to(root).as_posix()}" for m in ARCHIVE_MARKERS)
    )

    buckets: dict[str, list[str]] = {}
    unclassified: list[str] = []
    for rel in files:
        kind = _classify(rel, rules)
        if kind is None:
            unclassified.append(rel)
        else:
            buckets.setdefault(kind, []).append(rel)

    print(f"KINDS  {target}   ({len(files)} files)")
    print(
        f"  manifest: {target}/{MANIFEST_NAME}"
        f"{'' if (root / target / MANIFEST_NAME).exists() else '  (ABSENT -- defaults only)'}"
    )
    print()
    for kind in (
        KIND_DECISION,
        KIND_SLICE_SPEC,
        KIND_SCAFFOLDING,
        KIND_ROLLBACK,
        KIND_INSTRUMENT,
        KIND_RESULT,
    ):
        rows = buckets.get(kind, [])
        print(f"  {kind:<16} {len(rows):>4}   ends when: {LIFE_END[kind]}")
        if listing:
            for rel in rows:
                print(f"        {rel}")
    print()
    print(f"  classified   : {len(files) - len(unclassified)}")
    print(f"  UNCLASSIFIED : {len(unclassified)}")

    if unclassified:
        print()
        print(f"FAIL  {len(unclassified)} file(s) claimed by NO kind. A cleanup cannot")
        print(
            f"      disposition what it has not classified -- declare each in {MANIFEST_NAME}:"
        )
        for rel in unclassified[:25]:
            print(f"        {target}/{rel}")
        if len(unclassified) > 25:
            print(f"        ... +{len(unclassified) - 25} more")
        return 1

    print()
    print("PASS  every file is claimed by exactly one kind")
    print("      REMINDER: a kind is not a disposition. Each row above still needs its")
    print("      life-ending condition proven before anything moves.")
    return 0


def _cites_this_file(line: str, target: str, name: str) -> bool:
    """Does this line cite THIS file, or merely a different file with the same basename?

    Measured 2026-08-19: `.ai/ai-changelog.md` cites
    `.ai/handoffs/2026-08-16-B5B1-baseline-and-validation.md` -- the session's HAND-OFF. A brief
    of the same basename lives in `briefs/`, and a bare-basename match scored the brief "spent"
    against a citation of a different file. Worse, the file actually cited is in `.ai/handoffs/`,
    which is gitignored, so the "other home" was not durable either.
    """
    if target in line:
        return True
    if name not in line:
        return False
    # The basename appears somewhere. Recover the full path FRAGMENT around each occurrence and
    # accept only if that fragment is a genuine SUFFIX of the target path. That distinguishes
    # `briefs/<name>.md` (a suffix -> a real citation) from
    # `.ai/handoffs/<date>-<name>.md` (not a suffix -> a different
    # file that merely CONTAINS the basename), while still matching a fragment written relative
    # to another root, e.g. `<capture-dir>/json_output_format.txt` inside a shell
    # FILES=() array -- which a strict prefix comparison misses and a bare-substring match
    # over-accepts.
    pathish = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./"
    )
    for idx in (m for m in range(len(line)) if line.startswith(name, m)):
        start = idx
        while start > 0 and line[start - 1] in pathish:
            start -= 1
        fragment = line[start : idx + len(name)]
        if fragment == name or target == fragment or target.endswith(f"/{fragment}"):
            return True
    return False


def cmd_extraction(root: Path, target: str, records: list[str]) -> int:
    """Is this scaffolding file SPENT? Only if its reasoning already lives elsewhere.

    Two independent ways to fail, and either one keeps the file:
      1. The file's own text says its work has not happened yet (PENDING_MARKERS).
      2. No decision record cites it, so archiving it is the only copy leaving the repo.

    Measured 2026-08-19: several briefs in `feedback-relevance-and-realism` carry traps
    recorded nowhere else, and one (`DG1-run-the-deferred-gates.md`) is a brief for a session
    scheduled ~2 weeks out. "The session returned" is not the test; "the reasoning has
    another home" is.
    """
    path = root / target
    if not path.exists():
        print(f"FAIL  target does not exist: {target}")
        return 2

    text = path.read_text(encoding="utf-8", errors="replace")
    name = path.name
    pending = [m for m in PENDING_MARKERS if m.lower() in text.lower()]

    record_globs = records or [
        "topology.md",
        "roadmap.md",
        "execution-plan.md",
        "forward-plan.md",
        "*changelog*.md",
        "*DECISION*.md",
    ]
    homes: list[tuple[str, int, str]] = []
    open_cites: list[tuple[str, int, str]] = []
    for candidate in root.rglob("*.md"):
        rel = candidate.relative_to(root).as_posix()
        if any(m in f"/{rel}" for m in ARCHIVE_MARKERS) or rel == target:
            continue
        if not any(PurePosixPath(candidate.name).match(g) for g in record_globs):
            continue
        body = candidate.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(body.splitlines(), 1):
            if not _cites_this_file(line, target, name):
                continue
            row = (rel, lineno, line.strip()[:88])
            if any(m in line.lower() for m in OPEN_STATE_MARKERS):
                open_cites.append(row)
            else:
                homes.append(row)

    print(f"EXTRACTION  {target}")
    print(f"  decision records citing it as SETTLED : {len(homes)}")
    print(f"  decision records citing it as OPEN    : {len(open_cites)}")
    for rel, lineno, line in homes[:12]:
        print(f"    settled  {rel}:{lineno}: {line}")
    if len(homes) > 12:
        print(f"    ... +{len(homes) - 12} more")
    for rel, lineno, line in open_cites[:8]:
        print(f"    OPEN     {rel}:{lineno}: {line}")

    if open_cites:
        print()
        print(
            "  STOP  a decision record still describes this work as OPEN. A citation is not"
        )
        print(
            "        evidence of extraction when the citing line says the work is unfinished."
        )
        return 1

    if pending:
        print()
        print("  STOP  this file's OWN TEXT says its work has not happened:")
        for marker in pending:
            print(f"          {marker!r}")
        print(
            "        Scaffolding for a session that has not run is NOT spent. It stays."
        )
        return 1

    if not homes:
        print()
        print("  NOT SPENT  no decision record carries this file's reasoning.")
        print(
            "        Archiving it now removes the only copy from the repo. Either extract"
        )
        print("        the reasoning into a decision record FIRST, or keep the file.")
        return 1

    print()
    print(
        "  SPENT  the reasoning has another home. Archiving removes a duplicate, not a record."
    )
    return 0


def cmd_fundep(root: Path, target: str) -> int:
    """Is this path READ BY A PROGRAM rather than merely cited by a document?

    A citation goes stale silently and is fixed by an edit. A functional dependency BREAKS,
    and no amount of re-annotation repairs it. `regenerate-prompt-packet.sh` in
    `feedback-relevance-and-realism` holds 9 capture paths in a `FILES=()` array; each is an
    argument to a running program, not a reference in prose. Crossing that line without
    noticing is how a documentation sweep silently becomes a code change.
    """
    needle = target.rstrip("/")
    base = needle.rsplit("/", 1)[-1]
    hits: list[tuple[str, int, str]] = []

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {
            ".sh",
            ".py",
            ".bash",
            ".ps1",
            ".yaml",
            ".yml",
        }:
            continue
        rel = path.relative_to(root).as_posix()
        if any(m in f"/{rel}" for m in ARCHIVE_MARKERS) or rel.startswith(needle):
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(body.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("#", "//", '"""', "'''")):
                continue  # a comment mentioning the path is a citation, not a dependency
            # Two filters, both from measured false positives on 2026-08-19:
            #   * `_cites_this_file` rejects a same-named file in another directory --
            #     `.specs/persona-mains-consistency-pass/apply_fixes.py` referencing ITSELF
            #     was scored a dependency on this initiative's `apply_fixes.py`.
            #   * a program addresses a file by PATH, so require a separator. Without it this
            #     gate flagged its own SKILL.md prose ("regenerate-prompt-packet.sh holds 9
            #     capture paths") as a functional dependency.
            if "/" not in line or not _cites_this_file(line, needle, base):
                continue
            hits.append((rel, lineno, stripped[:88]))

    print(f"FUNDEP  target={needle}")
    print(f"  executable references : {len(hits)}")
    for rel, lineno, line in hits[:20]:
        print(f"    {rel}:{lineno}: {line}")
    if len(hits) > 20:
        print(f"    ... +{len(hits) - 20} more")

    if hits:
        print()
        print(
            "  STOP  this path is LOAD-BEARING, not derived. Moving it edits a program's"
        )
        print(
            "        behaviour. Repoint the executable in the same commit, or do not move"
        )
        print("        the file. Do not treat these as citations to re-annotate.")
        return 1

    print()
    print("PASS  no executable reads this path -- any inbound reference is a citation")
    return 0


def cmd_evidence(root: Path, symbol: str, spec_root: str) -> int:
    """Classify implementation evidence for a symbol.

    Two failure modes this exists to stop, both measured on 2026-08-09:
      1. An unscoped `git grep <symbol>` matches README.md and scores documentation as
         implementation (14 of 34 verdicts in one run).
      2. A symbol owned by a DIFFERENT spec matches and scores the wrong spec as shipped
         (`transcript_gradeability` belongs to the eligibility work, not to the STT spec
         whose own header says "no code written").
    """
    hits = git(root, "grep", "-l", "-I", symbol, "HEAD")
    paths = [h.split(":", 1)[1] for h in hits if ":" in h]

    code = [p for p in paths if Path(p).suffix in CODE_SUFFIXES]
    docs = [p for p in paths if Path(p).suffix in DOC_SUFFIXES]
    other = [p for p in paths if p not in code and p not in docs]

    print(f"EVIDENCE  symbol={symbol!r}")
    if code:
        verdict = "IMPLEMENTED"
    elif docs or other:
        verdict = "DOC-ONLY  (documentation of the thing, NOT the thing)"
    else:
        verdict = "ABSENT -- NO VERDICT (this is NOT 'not implemented')"
    print(f"  verdict : {verdict}")

    for label, group in (("code", code), ("other", other), ("docs", docs)):
        for path in group[:5]:
            print(f"  {label:<6}: {path}")
        if len(group) > 5:
            print(f"  {label:<6}: ... +{len(group) - 5} more")

    if not paths:
        # Measured 2026-08-09: `ai-driven-interview-end` was recorded "not implemented" from an
        # ABSENT result. The spec had shipped; the probe used EndProposalBehavior when the real
        # symbols were ai_end_settings / ai_end_debug_propose_action / end_proposed. ABSENT is
        # far more often a bad guess than a missing feature, so the tool refuses to let a single
        # miss read as a negative verdict.
        print()
        print(
            "  ABSENT means the SYMBOL was not found. It does NOT mean the work is missing."
        )
        print("  Before recording any verdict:")
        print("    1. Try >=3 more symbols from the spec's OWN acceptance criteria")
        print(
            "       (class, route, settings field, migration id, event name, config module)"
        )
        print(
            "    2. Grep the spec for identifiers:  grep -oE '[a-z_]{6,}\\.py|[A-Z][A-Za-z]{6,}'"
        )
        print(
            "    3. Ask whether the deliverable ships OUTSIDE this checkout (a kit, a fork,"
        )
        print("       another repo) -- this tool can only see this working tree")
        print("  If no symbol resolves, the verdict is NO VERDICT and the spec STAYS.")

    owning = sorted(
        {
            p.split("/")[1]
            for p in paths
            if p.startswith(f"{spec_root}/") and "/" in p[len(spec_root) + 1 :]
        }
    )
    if len(owning) > 1:
        print()
        print(
            f"  WARN  symbol appears under {len(owning)} spec dirs -- it is SHARED, so it"
        )
        print(
            "        proves nothing about any single one. Pick a symbol unique to the spec."
        )
        for name in owning[:8]:
            print(f"          {spec_root}/{name}")
        return 1

    return 0 if code else 1


def cmd_refs(root: Path, target: str) -> int:
    """Inbound-reference sweep over the WORKING TREE.

    `git grep` reads the index and cannot see untracked files. Measured 2026-08-04: after a
    real retirement `git grep` returned 0 inbound references while a working-tree walk
    returned 10+, all in a live hand-off whose preconditions then silently failed.
    """
    needle = target.rstrip("/")
    live: list[tuple[str, int, str]] = []
    archived = 0

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in (
            DOC_SUFFIXES | CODE_SUFFIXES | {".json"}
        ):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(needle):
            continue  # self-references die with the target
        if any(m in f"/{rel}" for m in ARCHIVE_MARKERS):
            archived += 1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if needle in line:
                live.append((rel, lineno, line.strip()[:90]))

    print(f"REFS  target={needle}")
    print(f"  live inbound references : {len(live)}  (archives/scratch skipped)")
    authority = [
        r
        for r in live
        if Path(r[0]).name in AUTHORITY_FILES or r[0].startswith(".claude/skills/")
    ]
    for rel, lineno, line in live[:25]:
        print(f"    {rel}:{lineno}: {line}")
    if len(live) > 25:
        print(f"    ... +{len(live) - 25} more")

    if authority:
        print()
        print(
            f"  STOP  {len(authority)} reference(s) come from CLAUDE.md/AGENTS.md or a skill."
        )
        print(
            "        A spec cited as an authority is a DECISION RECORD -- it transitions"
        )
        print("        status, it is never deleted. Confirm before proposing removal.")
        return 1

    return 1 if live else 0


def cmd_coverage(root: Path, target: str, plan: str, per_file: bool = False) -> int:
    """Assert the plan dispositions the WHOLE population.

    A 2026-08-09 run dispositioned 19 of 55 spec directories and read as a complete
    cleanup. The population came from that session's own sweep, so the directories it
    missed were exactly the ones that could have contradicted it.

    `--per-file` closes the granularity hole measured 2026-08-19: the directory mode below
    counts DIRECTORIES, so a plan containing the single string
    one initiative's spec directory dispositioned all 156 files inside it at once.
    Use --per-file whenever the target IS one initiative rather than the whole `.specs` tree.
    """
    plan_path = root / plan
    if not plan_path.exists():
        print(f"FAIL  plan not found: {plan}")
        return 2
    text = plan_path.read_text(encoding="utf-8", errors="replace")

    base = root / target
    if per_file:
        entries = sorted(
            p.relative_to(base).as_posix()
            for p in base.rglob("*")
            if p.is_file()
            and not any(
                m in f"/{p.relative_to(root).as_posix()}" for m in ARCHIVE_MARKERS
            )
        )
        # A file counts as dispositioned if the plan names it by relative path or by its
        # own basename -- never by its parent directory, which is the trap this mode closes.
        missing = [
            rel
            for rel in entries
            if rel not in text and rel.rsplit("/", 1)[-1] not in text
        ]
        unit = "file"
    else:
        entries = sorted(p.name for p in base.iterdir() if p.is_dir())
        missing = [name for name in entries if name not in text]
        unit = "directory"

    print(f"COVERAGE  plan={plan}  population={target}  granularity={unit}")
    print(f"  entries in population : {len(entries)}")
    print(f"  named in plan         : {len(entries) - len(missing)}")
    if missing:
        print()
        print(
            f"FAIL  {len(missing)} entr(ies) have NO disposition -- the plan would read as"
        )
        print("      complete while silently covering a subset:")
        for name in missing[:25]:
            print(f"        {target}/{name}")
        if len(missing) > 25:
            print(f"        ... +{len(missing) - 25} more")
        return 1

    print()
    print("PASS  every entry in the population is dispositioned")
    if not per_file:
        print(
            "      NOTE: directory granularity. A plan naming only this directory would"
        )
        print(
            "      pass while covering none of its files -- re-run with --per-file for an"
        )
        print("      initiative-scoped plan.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_census = sub.add_parser(
        "census", help="per-file partition + exhaustiveness assertion"
    )
    p_census.add_argument("--root", default=".specs")

    p_ev = sub.add_parser(
        "evidence", help="classify a symbol as CODE / DOC-ONLY / ABSENT"
    )
    p_ev.add_argument("--symbol", required=True)
    p_ev.add_argument("--spec-root", default=".specs")

    p_refs = sub.add_parser("refs", help="working-tree inbound-reference sweep")
    p_refs.add_argument("--target", required=True)

    p_cov = sub.add_parser(
        "coverage", help="assert the plan dispositions the whole population"
    )
    p_cov.add_argument("--root", default=".specs")
    p_cov.add_argument("--plan", required=True)
    p_cov.add_argument(
        "--per-file",
        action="store_true",
        help="require every FILE to be named, not merely its directory (the 156-in-1-row trap)",
    )

    p_kinds = sub.add_parser(
        "kinds", help="per-file artifact-KIND classification + completeness assertion"
    )
    p_kinds.add_argument("--root", required=True)
    p_kinds.add_argument("--manifest", default=None)
    p_kinds.add_argument(
        "--list",
        dest="listing",
        action="store_true",
        help="print every file under its kind, so a plan can quote membership not just counts",
    )

    p_extr = sub.add_parser(
        "extraction",
        help="is a scaffolding file SPENT (its reasoning has another home)?",
    )
    p_extr.add_argument("--target", required=True)
    p_extr.add_argument(
        "--records",
        nargs="*",
        default=None,
        help="decision-record filename globs (default: topology/roadmap/execution-plan/...)",
    )

    p_fd = sub.add_parser(
        "fundep",
        help="is this path read by an executable (load-bearing, not a citation)?",
    )
    p_fd.add_argument("--target", required=True)

    args = parser.parse_args()
    root = repo_root()

    if args.cmd == "census":
        return cmd_census(root, args.root)
    if args.cmd == "kinds":
        return cmd_kinds(root, args.root, args.manifest, args.listing)
    if args.cmd == "extraction":
        return cmd_extraction(root, args.target, args.records or [])
    if args.cmd == "fundep":
        return cmd_fundep(root, args.target)
    if args.cmd == "evidence":
        return cmd_evidence(root, args.symbol, args.spec_root)
    if args.cmd == "refs":
        return cmd_refs(root, args.target)
    if args.cmd == "coverage":
        return cmd_coverage(root, args.root, args.plan, args.per_file)
    return 2


if __name__ == "__main__":
    sys.exit(main())
