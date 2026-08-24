"""A reference to the support package must be anchored, on both surfaces.

The pack split moved the package to `plugins/core/src/lemmi_ai_kit/`, and every
reference to the old location became an instruction to a directory that does not
exist. Nothing caught the ones that were missed: `test_assets.py` scans from
`assets_root()`, and `test_publication_hygiene.py` -- which does cover the repo
surface -- carries a contamination contract (machine paths, source-project names),
not a layout one. So the restructure commit's path sweep skipped `.github/`, the PR
checklist went on telling contributors to register their skill in a manifest at a
dead path, and the suite stayed green for a day.

TWO SURFACES, TWO ANCHORS, ONE RULE.

The first version of this file guarded the repo surface only, and required the
`plugins/<pack>/` prefix. Applying that rule to the shipped tree would have been a
bug, not an extension: **inside the payload there is no `plugins/` above the
package.** An adopter's installed plugin root contains `src/` directly, so
`plugins/core/src/lemmi_ai_kit/` names nothing on their machine. A guard that
demanded it there would have flagged correct code, and the natural way to silence
it would have been to edit working paths into broken ones.

What the two surfaces share is *anchoring*. A bare `src/lemmi_ai_kit` is the defect
in both trees, for opposite reasons, and each tree has its own correct anchor:

| surface | correct anchor | why the other is wrong |
|---|---|---|
| repo (`docs/`, `.github/`, config) | `plugins/<pack>/` | — |
| shipped (`plugins/**`) | `${...PLUGIN_ROOT}/` | the payload has no `plugins/` above it |

Measured before this was written: on the shipped tree, one `${PLUGIN_ROOT}`-anchored
reference and zero `plugins/`-anchored ones; on the repo surface, thirty-nine
`plugins/`-anchored and zero `${PLUGIN_ROOT}`-anchored. Neither form appears on the
wrong surface, so each rule is enforced with no exemption and no false positive.

WHY THE SURFACE IS ASSERTED, NOT ASSUMED. This file previously reused
`_tracked_text_files()`, whose documented contract is "outside the asset/skill
trees" -- correct for its own module, and it silently excluded all 100 shipped
markdown files. The test was named for every *published* file while scanning 43 of
144, and the name was believed because nothing printed the surface. That is the
same failure as a green count guard enforcing one claim of three: the coverage, not
the pattern, decided what was seen. So `test_the_scan_surface_is_what_it_claims`
asserts both surfaces in numbers, and names the specific documents that must stay
in scope. A rename or a moved directory now fails loudly instead of shrinking the
scan in silence.

One exemption, and it is not a blanket: **dated research records under
`docs/research/`.** These describe the tree as it stood on the date in their
filename, and several quote the old path *as the evidence for the finding*.
Rewriting them would destroy the record rather than fix a defect. The exemption is
keyed on the dated filename convention, so an undated document dropped in that
directory is still scanned.

`CONTRIBUTING.md` and `SECURITY.md` were once a second exemption, recorded as a
strict xfail while they sat outside their finder's ownership -- an allowlist would
have asserted they were *right* to carry the dead path, which was false. They were
fixed and the xfail retired in the same commit, the only sequencing that never
leaves the tree red for an unrelated reason. The episode is kept because the next
person who finds a defect they cannot fix needs the pattern: record it as a failing
expectation with an owner, never as a permission.
"""

import re
import subprocess
from pathlib import Path

import pytest
from test_publication_hygiene import (
    _TEXT_SUFFIXES,  # pyright: ignore[reportPrivateUsage]
    _tracked_text_files,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Both anchors are optional and captured, so the ABSENCE of one is what fails, and
# the presence of the *wrong* one can be reported differently per surface. This is
# not a lookbehind: Python requires those to be fixed-width, so that spelling would
# hard-code one pack name's length and stop matching the day a differently-named
# pack is added -- failing open, which is the mode this file exists to remove.
#
# `\b` rather than a required trailing slash: `packages = ["src/lemmi_ai_kit"]` in a
# build config is the same defect and breaks more loudly than a sentence in prose.
_PACKAGE_PATH = re.compile(
    r"(?:\$\{(?P<var>[A-Z_]*PLUGIN_ROOT)\}/|plugins/(?P<pack>[A-Za-z0-9_-]+)/)?"
    r"src/lemmi_ai_kit\b"
)

# Everything under here is installed onto an adopter's machine.
_SHIPPED_PREFIX = "plugins/"

# Dated research records describe the tree on the date in their name.
_DATED_RESEARCH = re.compile(r"^docs/research/\d{4}-\d{2}-\d{2}-")

# Defines the pattern, so its own source and prose necessarily contain the shape.
_THIS_FILE = "tests/test_repo_path_references.py"

# Named so the scan cannot quietly stop covering the documents that carried the
# original defect, or the payload file that carried the shipped one.
_MUST_BE_SCANNED: tuple[tuple[str, str], ...] = (
    ("CONTRIBUTING.md", "repo"),
    ("SECURITY.md", "repo"),
    (".github/PULL_REQUEST_TEMPLATE.md", "repo"),
    ("plugins/core/skills/kit-setup/SKILL.md", "shipped"),
)


def _shipped_text_files() -> list[str]:
    """Published text files INSIDE the payload -- the complement of the other scan.

    Deliberately not `_tracked_text_files()`: that helper's contract is "outside the
    asset/skill trees", which is precisely the set this needs. Same git flags on
    purpose, so both scans agree on what "published" means -- tracked files plus
    untracked ones that are not ignored, since an unignored file under `plugins/`
    reaches adopters whether or not it was ever committed.
    """
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--"],
        cwd=_REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:  # pragma: no cover - not a work tree
        pytest.fail("not a git work tree, so the shipped set cannot be checked")

    return sorted(
        raw
        for raw in result.stdout.decode("utf-8").split("\0")
        if raw
        and raw.startswith(_SHIPPED_PREFIX)
        and (_REPO_ROOT / raw).is_file()
        and Path(raw).suffix.lower() in _TEXT_SUFFIXES
    )


def _surface_text_files() -> list[str]:
    """Published text files OUTSIDE the payload, less the dated records and this.

    `_tracked_text_files()` excludes the asset tree and both skills trees, but not
    the rest of `plugins/` -- `cli.py`, `manifest.py` and the plugin manifests all
    survive it. Those ship, so they must be judged by the payload rule, not this
    one. Partitioning on `_SHIPPED_PREFIX` here is what keeps the two scans
    disjoint; `test_the_scan_surface_is_what_it_claims` asserts that they are.
    """
    return [
        relative
        for relative in _tracked_text_files()
        if relative != _THIS_FILE
        and not relative.startswith(_SHIPPED_PREFIX)
        and not _DATED_RESEARCH.match(relative)
    ]


def _violations(relative: str, *, shipped: bool) -> list[str]:
    """Package references in one file that carry the wrong anchor, or none."""
    text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
    return _violations_in(text, shipped=shipped, relative=relative)


def _violations_in(text: str, *, shipped: bool, relative: str = "<text>") -> list[str]:
    """The rule itself, over a string, so it can be exercised without a file."""
    problems: list[str] = []
    for match in _PACKAGE_PATH.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        if shipped:
            if match.group("var"):
                continue
            why = (
                "anchored to the repo layout, which does not exist inside an "
                "installed plugin"
                if match.group("pack")
                else "not anchored"
            )
            problems.append(
                f"{relative}:{line}: {match.group(0)!r} is {why} — use "
                "${CLAUDE_PLUGIN_ROOT}/src/lemmi_ai_kit/..."
            )
        elif match.group("pack") is None and match.group("var") is None:
            problems.append(
                f"{relative}:{line}: {match.group(0)!r} is not anchored — use "
                "plugins/<pack>/src/lemmi_ai_kit/..."
            )
    return problems


def test_no_shipped_file_points_outside_its_own_payload() -> None:
    """The tree installed onto an adopter's machine, where only `${...}` resolves."""
    violations: list[str] = []
    for relative in _shipped_text_files():
        try:
            violations.extend(_violations(relative, shipped=True))
        except (UnicodeDecodeError, OSError) as exc:
            violations.append(f"{relative}: could not be scanned ({exc!r})")

    assert not violations, (
        "shipped files naming the package by a path that does not resolve where "
        "they land:\n" + "\n".join(violations) + "\n\nAn installed plugin's root "
        "contains `src/` directly — there is no `plugins/<pack>/` above it. Do not "
        "'fix' these by adding that prefix; anchor them to the plugin root."
    )


def test_no_published_file_points_at_a_prefixless_package_path() -> None:
    """The repo surface: docs, config, community files, CI templates."""
    violations: list[str] = []
    for relative in _surface_text_files():
        try:
            violations.extend(_violations(relative, shipped=False))
        except (UnicodeDecodeError, OSError) as exc:
            # Never skip silently: an unreadable file is the "passed because the
            # scan never looked" failure this suite exists to catch.
            violations.append(f"{relative}: could not be scanned ({exc!r})")

    assert not violations, (
        "published files naming the package at its pre-split path:\n"
        + "\n".join(violations)
        + "\n\nThe package lives at `plugins/core/src/lemmi_ai_kit/`. Add the "
        "`plugins/<pack>/` prefix. If the file is a dated record of the old "
        "layout, it belongs under `docs/research/` with a dated filename."
    )


def test_the_scan_surface_is_what_it_claims() -> None:
    """A guard states its scan surface in numbers it asserts.

    The first version of this file was named for every published file while
    covering 43 of 144, because it inherited an exclusion built for a different
    contract and nobody printed the surface. Asserting it here means the name
    cannot drift from the coverage again without failing.
    """
    surface = set(_surface_text_files())
    shipped = set(_shipped_text_files())

    assert len(shipped) > 90, (
        f"only {len(shipped)} shipped text files found — the payload holds ~118, so "
        "the enumeration is probably broken and this scan is close to vacuous"
    )
    assert len(surface) > 30, (
        f"only {len(surface)} repo-surface files after exemptions — the enumeration "
        "or the exemption rules are probably broken"
    )
    assert not (surface & shipped), "the two surfaces must not overlap"

    for relative, where in _MUST_BE_SCANNED:
        covered = shipped if where == "shipped" else surface
        assert relative in covered, (
            f"{relative} is no longer in the {where} scan. It carried an instance "
            "of this defect; it must not drop out of scope silently."
        )

    assert any(relative.endswith(".toml") for relative in surface), (
        "no build config in the scanned set; a stale `packages = [...]` entry is "
        "the highest-cost instance of this defect and must be in scope"
    )


def test_the_matcher_distinguishes_the_two_anchors() -> None:
    """Positive control: a guard that has never been shown to fail is not shown to work.

    The `${PLUGIN_ROOT}` case is the one that matters most. Flagging a correct
    payload-relative path would be worse than the gap this closes, because the
    obvious way to silence it is to edit working code into a path that resolves
    nowhere.
    """
    payload = _PACKAGE_PATH.search(
        "copy from `${PLUGIN_ROOT}/src/lemmi_ai_kit/assets/`"
    )
    assert payload is not None and payload.group("var") == "PLUGIN_ROOT"
    claude = _PACKAGE_PATH.search("${CLAUDE_PLUGIN_ROOT}/src/lemmi_ai_kit/cli.py")
    assert claude is not None and claude.group("var") == "CLAUDE_PLUGIN_ROOT"

    repo = _PACKAGE_PATH.search("plugins/core/src/lemmi_ai_kit/manifest.py")
    assert repo is not None and repo.group("pack") == "core"
    other = _PACKAGE_PATH.search("plugins/python/src/lemmi_ai_kit/x.py")
    assert other is not None and other.group("pack") == "python", (
        "a second pack name must satisfy the prefix too — this is the case a "
        "fixed-width lookbehind would have silently failed"
    )

    bare = _PACKAGE_PATH.search('packages = ["src/lemmi_ai_kit"]')
    assert bare is not None
    assert bare.group("pack") is None and bare.group("var") is None

    # The two rules must disagree about the repo anchor, which is the whole reason
    # the shipped tree could not simply inherit the surface scan.
    repo_anchored = "see plugins/core/src/lemmi_ai_kit/manifest.py"
    assert _violations_in(repo_anchored, shipped=False) == []
    assert _violations_in(repo_anchored, shipped=True) != [], (
        "the repo prefix must be a VIOLATION inside the payload — an installed "
        "plugin has no `plugins/<pack>/` above its `src/`"
    )
