"""The pre-publish guard: refuse to publish while the payload carries anything git does not.

`plugin install` copies the WORKING TREE, not the git tree. V-1 measured it: 117 files
shipped from `plugins/core` against 107 tracked, the extra eight being six gitignored
`.pyc` and two uncommitted template drafts that happened to be sitting there when the
install ran. Nothing tracked was *missing*, so the leak is one-directional and silent --
the install looks complete because it is complete, plus extra. The copy does not care
what the extra files are; several sessions write this one checkout, and it has been
dirty at every measurement taken.

Three probes, and four rules they follow:

**No escape hatch.** The whole-repo probe demands an EMPTY `git status --porcelain` --
not "only my files", empty. A flag to excuse a path would restore the judgement call
("that draft is fine") that the guard exists to remove, and that judgement gets made by
whoever is publishing, about their own mess, under time pressure.

**Cannot-measure is never clean.** No git, not a work tree, no marketplace manifest, or
a payload pathspec matching nothing tracked -- each raises rather than returning an
empty finding list. A gate that scans nothing reports green forever, and a green
detector nobody can fail is worse than no detector, because it gets trusted.

**The payload is read from the marketplace manifests, not written down here.** A pack
added to `.claude-plugin/marketplace.json` or `.agents/plugins/marketplace.json` comes
under the guard by that fact alone. Both are read and unioned: the two hosts disagree on
source syntax (a bare string vs `source.path`), and a pack listed to only one of them
still ships to that one.

**Every refusal names its remedy, and applies none of them.** A guard that says no
without saying what to run hands the publisher a dead end at the worst possible moment,
and that dead end is the pressure that produces an escape hatch later -- so refusing and
remediating are one control, not two. Naming the fix costs nothing and removes the
motive. *Running* it is refused just as firmly: `git clean -Xdf` and `git commit` are
decisions about what the world should contain, and a check that quietly makes them turns
"the tree is clean" from a fact the publisher established into a side effect of asking.

**Every path printed is repo-relative and ASCII**, per the portability rules in
`checks.py` -- this output gets pasted into hand-offs, and a guard that crashes a legacy
code-page console while reporting is worse than no guard.

One tension, stated rather than worked around. Importing this module writes
`__pycache__/publish.cpython-311.pyc` under `plugins/`, which this module would then
refuse to publish -- the ignored count under `plugins/` was measured going from six to
seven the first time it was imported. So the guard cannot be self-tested by running it
after importing it, and a green self-run is not evidence of anything.

The obvious fix is to exempt `__pycache__`. It is refused: six `.pyc` files under
`plugins/core/src/` ARE the original finding, and a guard blind to the exact bytes that
motivated it is a gate that reports green for a reason unrelated to what it measures.
The tension is real and stays. It is resolved by *when* the guard runs -- immediately
before publishing, on a tree cleaned for publishing -- not by narrowing what it sees;
`tests/test_publish.py` therefore asserts against throwaway checkouts, and asserts only
measurability, never cleanliness, against this one.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

_GIT_TIMEOUT_SECONDS = 30

# Read in this order; results are unioned. Claude spells a source as a bare relative
# string, Codex as an object with `path`. `_source_path` accepts both.
MARKETPLACE_MANIFESTS: tuple[str, ...] = (
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
)

_WORKTREE = "working tree"


class PublishCheckError(RuntimeError):
    """The guard could not measure. Reported as exit 2 -- never as a pass."""


@dataclass(frozen=True)
class Probe:
    """One question asked of git, what a non-empty answer means, and how to clear it."""

    label: str
    argv: tuple[str, ...]
    consequence: str
    remedy: tuple[str, ...]


@dataclass(frozen=True)
class ProbeResult:
    probe: Probe
    paths: tuple[str, ...]

    @property
    def blocks(self) -> bool:
        return bool(self.paths)


@dataclass(frozen=True)
class Report:
    """Everything the guard measured, so the caller renders it without re-running git."""

    root: Path
    payload: tuple[str, ...]
    tracked: int
    results: tuple[ProbeResult, ...]

    @property
    def blocked(self) -> bool:
        return any(result.blocks for result in self.results)

    @property
    def extra(self) -> int:
        """Payload files a `plugin install` would copy that git does not track.

        Probes 2 and 3 are disjoint by construction -- `--others` without `--ignored`
        excludes ignored files -- so this is a sum, not a union.
        """
        return sum(len(r.paths) for r in self.results if r.probe.label != _WORKTREE)


def _git(root: Path, argv: tuple[str, ...]) -> bytes:
    """Run git in `root`, or raise. Bytes, never `text=True`: that decodes by locale.

    `MSYS_NO_PATHCONV` stops a Git-for-Windows shell rewriting the pathspecs into
    absolute Windows paths, which would silently match nothing.
    """
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    try:
        completed = subprocess.run(
            ("git", *argv),
            cwd=root,
            capture_output=True,
            env=env,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PublishCheckError(
            f"git could not be run in {root}, so nothing was verified: {exc}"
        ) from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip().splitlines()
        detail = stderr[0] if stderr else f"exit {completed.returncode}"
        raise PublishCheckError(f"git {' '.join(argv)} failed: {detail}")
    return completed.stdout


def _records(raw: bytes) -> tuple[str, ...]:
    """Split NUL-separated git output.

    `errors="replace"` so a mis-encoded filename stays reportable instead of taking the
    guard down -- the count is what blocks, and a lossy name still identifies the file.

    One caveat, harmless here: `status --porcelain -z` emits a rename as two records,
    the second being the bare source path with no status prefix. It reads as an extra
    line naming a real file, and this probe only needs empty-or-not.
    """
    return tuple(
        chunk.decode("utf-8", "replace") for chunk in raw.split(b"\0") if chunk
    )


def checkout_root(start: Path | None = None) -> Path:
    """Nearest ancestor holding `.git`.

    Deliberately not `checks.find_project_root`, which prefers `.ai/` -- in a monorepo
    that resolves to a subproject, and every probe below is a question about a git
    checkout, not about a project.
    """
    base = (start or Path.cwd()).resolve()
    for candidate in (base, *base.parents):
        if (candidate / ".git").exists():
            return candidate
    raise PublishCheckError(f"not inside a git checkout: {base}")


def _source_path(raw: object) -> str | None:
    """The relative payload path from one marketplace entry's `source`, in either syntax."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        path = cast(dict[str, object], raw).get("path")
        return path if isinstance(path, str) else None
    return None


def payload_roots(root: Path) -> tuple[str, ...]:
    """Repo-relative pathspecs for everything a `plugin install` would copy.

    Raises when no manifest names a payload: `publish-check` outside this repo's layout
    has nothing to check, and "nothing to check" must not render as clean.
    """
    found: set[str] = set()
    read: list[str] = []
    for relative in MARKETPLACE_MANIFESTS:
        path = root / relative
        if not path.is_file():
            continue
        try:
            raw_text = path.read_text(encoding="utf-8-sig")
            data = cast(object, json.loads(raw_text))
        except (UnicodeDecodeError, OSError, json.JSONDecodeError) as exc:
            # Not skipped: an unreadable manifest is a payload we cannot enumerate, and
            # continuing would under-scope the guard to whatever the other file listed.
            raise PublishCheckError(f"{relative} could not be read: {exc}") from exc
        read.append(relative)
        if not isinstance(data, dict):
            raise PublishCheckError(f"{relative} is not a JSON object")
        plugins = cast(dict[str, object], data).get("plugins")
        if not isinstance(plugins, list):
            raise PublishCheckError(f"{relative} has no `plugins` list")
        for entry in cast(list[object], plugins):
            if not isinstance(entry, dict):
                continue
            source = _source_path(cast(dict[str, object], entry).get("source"))
            if source is None:
                continue
            spec = source.removeprefix("./").rstrip("/") or "."
            if spec.startswith("/") or ".." in Path(spec).parts:
                raise PublishCheckError(
                    f"{relative}: source escapes the repository: {source!r}"
                )
            found.add(spec)

    if not read:
        raise PublishCheckError(
            "no marketplace manifest found ("
            + ", ".join(MARKETPLACE_MANIFESTS)
            + f") under {root} -- this is not a checkout of the kit"
        )
    if not found:
        raise PublishCheckError(
            f"{', '.join(read)} list no plugin sources, so the payload is unknown"
        )
    # A `./` source means the whole repo ships; it subsumes every sibling pathspec, and
    # keeping both would double-count the files beneath them.
    return (".",) if "." in found else tuple(sorted(found))


def _probes(payload: tuple[str, ...]) -> tuple[Probe, ...]:
    spec = " ".join(payload)
    return (
        Probe(
            label=_WORKTREE,
            argv=("status", "--porcelain", "-z"),
            consequence="whoever publishes ships whatever is dirty at that instant",
            remedy=(
                "decide per file, then re-run:",
                "  keep it:    git add <path> && git commit",
                "  discard it: git restore <path>   (tracked)   git clean -i (untracked)",
                "a dirty TRACKED file ships MODIFIED -- leaving it uncommitted is not a",
                "third option, it publishes the edit without publishing the decision",
            ),
        ),
        Probe(
            label="untracked in the payload",
            argv=("ls-files", "--others", "--exclude-standard", "-z", "--", *payload),
            consequence="reaches every adopter, in no commit, reviewed by no one",
            remedy=(
                "should ship:     git add <path> && git commit",
                "should not ship: delete it, or move it outside " + spec,
                "adding it to .gitignore does NOT stop it shipping -- it only moves it",
                "into the next probe, which is the whole reason that probe exists",
            ),
        ),
        Probe(
            label="gitignored in the payload",
            argv=(
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "-z",
                "--",
                *payload,
            ),
            consequence="ignored by git is not excluded by the copy -- __pycache__ ships",
            remedy=(
                f"preview: git clean -Xdn -- {spec}",
                f"delete:  git clean -Xdf -- {spec}",
                "-X removes ONLY ignored files, so tracked and untracked work survives.",
                "Read the preview before the delete: this is the one remedy here that",
                "destroys something.",
            ),
        ),
    )


def check(root: Path) -> Report:
    """Measure the three probes against `root`, or raise `PublishCheckError`."""
    # `rev-parse` is the one probe with no `-z`: it answers in a newline, so it is
    # decoded and stripped here rather than run through the NUL splitter.
    inside = _git(root, ("rev-parse", "--is-inside-work-tree"))
    if inside.decode("utf-8", "replace").strip() != "true":
        raise PublishCheckError(f"not a git work tree: {root}")

    payload = payload_roots(root)
    tracked = _records(_git(root, ("ls-files", "-z", "--", *payload)))
    if not tracked:
        # Guard the guard. An empty payload makes probes 2 and 3 vacuously clean, which
        # is the exact shape of failure this module refuses to have.
        raise PublishCheckError(
            f"no tracked files under the payload ({', '.join(payload)}) -- the pathspec "
            "is wrong, so the untracked and ignored probes would pass vacuously"
        )

    results = tuple(
        ProbeResult(probe=probe, paths=_records(_git(root, probe.argv)))
        for probe in _probes(payload)
    )
    return Report(
        root=root, payload=payload, tracked=len(set(tracked)), results=results
    )
