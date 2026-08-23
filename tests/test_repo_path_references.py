"""No published file may point at the package by its pre-split path.

The pack split moved the support package to `plugins/core/src/lemmi_ai_kit/`, and
every reference to the old location became an instruction to a directory that does
not exist. Nothing caught the ones that were missed: `test_assets.py` scans from
`assets_root()`, and `test_publication_hygiene.py` -- which does cover the repo
surface -- carries a contamination contract (machine paths, source-project names),
not a layout one. So the restructure commit's path sweep skipped `.github/`, the PR
checklist went on telling contributors to register their skill in a manifest at a
dead path, and the suite stayed green for a day. That is the gap this file closes.

Why the prefix is matched rather than excluded: the pack segment is captured as an
optional group and then inspected, instead of using a negative lookbehind for
`plugins/core/`. Python requires fixed-width lookbehind, so that spelling would
have to hard-code one pack name's length and would quietly stop matching the day a
pack with a different name is added -- failing open, which is the failure mode this
file exists to remove.

Two exemptions, on different grounds, and neither is a blanket:

**Dated research records under `docs/research/`.** These describe the tree as it
stood on the date in their filename, and several quote the old path *as the
evidence for the finding* -- a before/after table of what the split moved. Rewriting
them would destroy the record rather than fix a defect. The exemption is keyed on
the dated filename convention, so an undated document dropped in that directory is
still scanned.

**`CONTRIBUTING.md` and `SECURITY.md`, which are genuinely wrong today.** They are
not exempt: they are a known, open defect, recorded below as a strict xfail rather
than an allowlist entry. An allowlist entry would assert it is *correct* for those
files to carry the old path, which is false -- `CONTRIBUTING.md` still tells a new
contributor to create their skill under a dead directory, and one of its links is
dead on arrival. A strict xfail states the opposite: this is broken, it is measured,
and the moment someone fixes it the XPASS turns red and this scaffolding must be
deleted. Neither file was in this session's ownership, which is why the defect is
recorded here rather than repaired here.
"""

import re
from pathlib import Path

import pytest
from test_publication_hygiene import (
    _tracked_text_files,  # pyright: ignore[reportPrivateUsage]
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The pack prefix is optional and captured, so its ABSENCE is what fails -- see the
# module docstring on why this is not a lookbehind. `\b` rather than a required
# trailing slash: `packages = ["src/lemmi_ai_kit"]` in a build config is the same
# defect, and breaks more loudly than a stale sentence in prose.
_PACKAGE_PATH = re.compile(
    r"(?:plugins/(?P<pack>[A-Za-z0-9_-]+)/)?(?P<path>src/lemmi_ai_kit)\b"
)

# Dated research records describe the tree on the date in their name.
_DATED_RESEARCH = re.compile(r"^docs/research/\d{4}-\d{2}-\d{2}-")

# Open defect, not an exemption. See the module docstring.
_KNOWN_STALE: tuple[str, ...] = ("CONTRIBUTING.md", "SECURITY.md")

# Defines the pattern, so its own source and prose necessarily contain the shape.
_THIS_FILE = "tests/test_repo_path_references.py"


def _prefixless_references(relative: str) -> list[str]:
    """Every `src/lemmi_ai_kit` in one file that is missing its `plugins/<pack>/`."""
    text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
    return [
        f"{relative}:{text.count(chr(10), 0, match.start()) + 1}: "
        f"{text[match.start() : match.end()]!r}"
        for match in _PACKAGE_PATH.finditer(text)
        if match.group("pack") is None
    ]


def _scanned_files() -> list[str]:
    """The published set, less the two documented exemptions and this file."""
    return [
        relative
        for relative in _tracked_text_files()
        if relative != _THIS_FILE
        and relative not in _KNOWN_STALE
        and not _DATED_RESEARCH.match(relative)
    ]


def test_no_published_file_points_at_a_prefixless_package_path() -> None:
    violations: list[str] = []
    for relative in _scanned_files():
        try:
            violations.extend(_prefixless_references(relative))
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "CONTRIBUTING.md and SECURITY.md still name the pre-split package path; "
        "both were outside the ownership of the session that added this guard. "
        "When they are corrected this turns XPASS and fails -- at which point "
        "delete this test and _KNOWN_STALE, and the files fall under the scan "
        "above."
    ),
)
def test_the_known_stale_documents_have_been_corrected() -> None:
    violations = [
        line for relative in _KNOWN_STALE for line in _prefixless_references(relative)
    ]
    assert not violations, "\n".join(violations)


def test_the_scan_is_not_vacuous() -> None:
    """Guard the guard: an empty file set or a dead pattern would pass silently."""
    scanned = _scanned_files()
    assert len(scanned) > 10, (
        f"only {len(scanned)} files left after exemptions -- the enumeration or the "
        "exemption rules are probably broken, which would make the scan vacuous"
    )
    assert any(relative.endswith(".toml") for relative in scanned), (
        "no build config in the scanned set; a stale `packages = [...]` entry is "
        "the highest-cost instance of this defect and must be in scope"
    )

    caught = _PACKAGE_PATH.search('packages = ["src/lemmi_ai_kit"]')
    assert caught is not None and caught.group("pack") is None
    passed = _PACKAGE_PATH.search("plugins/core/src/lemmi_ai_kit/manifest.py")
    assert passed is not None and passed.group("pack") == "core"
    other = _PACKAGE_PATH.search("plugins/python/src/lemmi_ai_kit/x.py")
    assert other is not None and other.group("pack") == "python", (
        "a second pack name must satisfy the prefix too -- this is the case a "
        "fixed-width lookbehind would have silently failed"
    )
