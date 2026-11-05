"""Section 5 of the gate-output reference compares a blob with a file by blob id, in two forms.

The section said a git blob is stored with LF and the working-tree copy is CRLF, so "a `sha256sum`
of the two therefore *always* differs for any text file", and its remedy normalised line endings
before comparing. Nothing in it turned a disk file into a blob id, and the claim was too wide:
what is stored follows `.gitattributes` or `core.autocrlf` and can differ per file, a `git archive`
export is written in the checkout form like the working tree, and a byte hash differs only for the
files whose line endings were converted.

The section now compares ids, two hashes per file, each against the blob: `git hash-object
--path=<path>` (the input filter the repository applies to that path) and `git hash-object
--no-filters` (the raw bytes). A blob stored with LF matches the first, and one stored with CRLF can
match only the second, so the file equals the blob when either id matches. The two forms were run
by hand against a scratch repository (an LF-stored and a CRLF-stored file, an archive export under
`core.autocrlf=true`, an edited copy, an LF copy of the CRLF-stored file) before this wording was
written; no test here runs git.

THE SURFACE, in numbers the tests assert: 1 place (section 5 of 1 file) and 13 checks. 9 are for
wording that was added and 3 for the claim that was corrected; each is fired at the unedited text of
the section as it stood (`_OLD_SECTION_5`) and must report it. The 13th guards a rule the rewrite
had to keep, so it must still hold on the old text and on the new.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
    / "references"
    / "reading-gate-output.md"
)
_HEADING = re.compile(r"^(#{1,6})\s")
_HEADING_5 = "## 5."


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis, code-span and quote marks dropped and whitespace folded to one space."""
    return re.sub(r"\s+", " ", re.sub(r"^\s*>+ ?|[*`]", "", text, flags=re.M)).strip()


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same or a
    higher level; a `#` line inside a fenced block is not a heading. A missing heading fails
    loudly, with the heading named."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
        fence = line.lstrip().startswith("```")
        found = None if in_fence or fence else _HEADING.match(line)
        if fence:
            in_fence = not in_fence
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    if not body:
        raise AssertionError(f"reading-gate-output.md: no heading starting {heading!r}")
    return "\n".join(body)


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


def _says(*needles: str) -> Callable[[str], bool]:
    return lambda section: all(n in _plain(section) for n in needles)


def _lacks(needle: str) -> Callable[[str], bool]:
    return lambda section: needle not in _plain(section)


# The wording that was added.
_ADDED: tuple[_Check, ...] = (
    _Check(
        "the path form is named, with what it applies",
        _says(
            "git hash-object --path=<path> <file> (the input filter the repository applies to that path)"
        ),
    ),
    _Check(
        "the raw-bytes form is named",
        _says("git hash-object --no-filters <file> (the raw bytes)"),
    ),
    _Check(
        "each hash is compared with the blob id",
        _says("each against git rev-parse <tree-ish>:<path>"),
    ),
    _Check(
        "the file equals the blob when either id matches",
        _says("The file equals the blob when either id matches"),
    ),
    _Check(
        "an LF blob matches the first form, a CRLF blob only the second",
        _says(
            "A blob stored with LF matches the first; one stored with CRLF can match only the second"
        ),
    ),
    _Check(
        "the mechanism: hash-object converts what git leaves alone in a CRLF-stored file",
        _says(
            "because hash-object converts line endings that git leaves alone in a file already stored with CRLF",
            "git ls-files --eol",
        ),
    ),
    _Check("the denominator is printed", _says("Print the denominator")),
    _Check(
        "the stored form follows the attributes or autocrlf and differs per file",
        _says(".gitattributes or core.autocrlf and can differ per file"),
    ),
    _Check(
        "an archive export is a disk side like the working tree",
        _says("git archive", "an export is a disk side like the working tree"),
    ),
)
# The claim that was corrected: what went, and what replaced it.
_CORRECTED: tuple[_Check, ...] = (
    _Check("no longer says a byte hash always differs", _lacks("always differs")),
    _Check("no longer says it differs for any text file", _lacks("for any text file")),
    _Check(
        "a byte hash differs only for the files whose endings were converted",
        _says("differs for the files whose line endings were converted"),
    ),
)
# What the rewrite had to keep, and so what the old text still says.
_KEPT = _Check(
    "an all-files-differ result is still an instrument fault until proven otherwise",
    _says(
        "treat an all-files-differ result as an instrument fault until proven otherwise"
    ),
)

_OLD_SECTION_5 = r"""## 5. Comparing a git blob to a working-tree file is a LINE-ENDING test, not a content test

`git show <ref>:<path>` returns the blob **as stored** (LF under this repo's `.gitattributes`); the
working-tree copy is **CRLF**. A `sha256sum` of the two therefore *always* differs for any text file,
whatever the content.

**Measured**: verifying 22 archived files were byte-identical to what git held reported
**0 identical / 22 problems**. The archive was perfect. The same false alarm fired **three times in
one session** — on an archive, on a PR body repair, and on a `git show`-based doc comparison.

The verdict reads as catastrophic — *every* file wrong — which is exactly the shape that prompts a
panicked re-do of correct work.

> Normalise before comparing (`tr -d '\r'`) whenever one side comes from git and the other from disk,
> and **treat an all-files-differ result as an instrument fault until proven otherwise.** The
> strongest content proof needs no hashing at all: `git apply --check --reverse <patch>` against the
> tree (passed for 23 uncommitted files across five rebases).
"""


def _gaps(text: str, checks: tuple[_Check, ...]) -> list[str]:
    section = _section(text, _HEADING_5)
    return [c.label for c in checks if not c.holds(section)]


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_ADDED) + len(_CORRECTED) == 12, "the 12 checks the docstring states"
    assert (len(_ADDED), len(_CORRECTED)) == (9, 3)
    labels = [c.label for c in (*_ADDED, *_CORRECTED, _KEPT)]
    assert len(set(labels)) == len(labels), "two checks share a label"
    assert _read(_REFERENCE).strip(), "the reference is empty"
    assert _HEADING_5 in _read(_REFERENCE)


def test_section_5_compares_blob_ids_in_two_forms() -> None:
    gaps = _gaps(_read(_REFERENCE), (*_ADDED, *_CORRECTED, _KEPT))
    assert not gaps, f"section 5 of reading-gate-output.md: {gaps}"


def test_every_check_reports_the_text_it_replaced() -> None:
    """The old section carried none of the new wording and all of the old: each check must say so
    (the kept rule is the exception, and must still hold on it)."""
    reported = _gaps(_OLD_SECTION_5, (*_ADDED, *_CORRECTED))
    assert len(reported) == len(_ADDED) + len(_CORRECTED), (
        f"{len(reported)} of {len(_ADDED) + len(_CORRECTED)} checks saw the old text; blind: "
        f"{[c.label for c in (*_ADDED, *_CORRECTED) if c.label not in reported]}"
    )
    assert _gaps(_OLD_SECTION_5, (_KEPT,)) == [], "the kept rule is not in the old text"


def test_the_checks_see_planted_wording_and_a_missing_heading_fails_loudly() -> None:
    planted = "\n".join(
        [
            "## 5. Planted",
            "A sha256sum of the two therefore *always* differs for any text file.",
            "> **Compare blob ids**, wrapped",
            "> over two lines.",
            "## 6. After",
        ]
    )
    assert _gaps(planted, _CORRECTED[:2]) == [c.label for c in _CORRECTED[:2]]
    assert _plain(_section(planted, _HEADING_5)).endswith(
        "Compare blob ids, wrapped over two lines."
    )
    assert (
        _gaps(
            planted.replace("*always* differs for any text file", "differs"),
            _CORRECTED[:2],
        )
        == []
    )
    with pytest.raises(AssertionError, match="no heading"):
        _section(planted, "## 9.")


def test_the_needle_helper_needs_every_needle_it_is_given() -> None:
    """`_says` holds only when every needle is there. Fired at a section that holds one of two, so
    a helper that settled for any needle would pass the two-needle checks on one of them."""
    section = "## 5. Planted\nalpha and beta, not gamma\n"
    assert _says("alpha", "beta")(section)
    assert not _says("alpha", "delta")(section)
