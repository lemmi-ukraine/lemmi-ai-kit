"""The doc-retirement gate of `post-task-review` searches for the ids that moved with the content.

A retirement sweep greps the retired file's path and its base name. The ids that were written
inside it (an acceptance-criterion id, a use-case id) moved with the relocated content, and no sweep
searched for them, so an id could stand in the destination with nothing left that said what it
meant once the source was deleted. The gate now says to derive the id prefixes from the retired
file, grep the destination for them, and write what each id means where the content now stands.

This file asserts the review skill's place only. The cleanup skill's own retirement step is a
second place of the same rule, and it is asserted by the test of the package that owns it.

THE SURFACE, in numbers the tests assert: 1 place (the doc-retirement gate bullet of 1 file) and 3
checks, each fired at the gate as it stood (`_OLD_GATE`, an unedited excerpt) and each reporting it.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILL_MD = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
    / "SKILL.md"
)
_GATE_LEAD = "- **Doc-retirement gate**"
_GATE_END = "See [references/review-checklist.md]"


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _gate(text: str) -> str:
    """The gate bullet, from its lead to the pointer line that follows the Important Notes list.
    Either marker missing fails loudly."""
    begin = text.find(_GATE_LEAD)
    if begin < 0:
        raise AssertionError(f"SKILL.md: no bullet starting {_GATE_LEAD!r}")
    stop = text.find(_GATE_END, begin)
    if stop < 0:
        raise AssertionError(f"SKILL.md: no {_GATE_END!r} after the gate bullet")
    return text[begin:stop]


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


def _says(needle: str) -> Callable[[str], bool]:
    return lambda gate: needle in _plain(gate)


_CHECKS: tuple[_Check, ...] = (
    _Check(
        "the gate derives the id prefixes from the retired file",
        _says("Derive the id prefixes from the retired file"),
    ),
    _Check(
        "the gate greps the destination for them",
        _says("grep the destination for them"),
    ),
    _Check(
        "the gate writes what each id means where the content now stands",
        _says("write what each id means there"),
    ),
)

_OLD_GATE = r"""- **Doc-retirement gate** (step 7): before deleting any doc, enumerate its EXECUTABLE artifacts
  separately from its knowledge — grep it for fenced code blocks and "Reproduce" / "How to find" /
  query sections, and relocate each VERBATIM next to the step that needs it, not into a summary.
  A relocation pass naturally captures claims and obligations and systematically misses
  queries/repro steps; "the checklist survived" and "the means of executing it survived" are two
  separate gates. Pair with the AGENTS.md deletion-sweep rule (partition targets by `git ls-files`
  first — the untracked half is unrecoverable).

See [references/review-checklist.md](references/review-checklist.md) for a quick-reference checklist.
"""


def _gaps(text: str) -> list[str]:
    gate = _gate(text)
    return [c.label for c in _CHECKS if not c.holds(gate)]


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_CHECKS) == 3, f"{len(_CHECKS)} checks, not the 3 stated"
    assert len({c.label for c in _CHECKS}) == 3, "two checks share a label"
    gate = _gate(_read(_SKILL_MD))
    assert _plain(gate).startswith("- Doc-retirement gate (step 7)"), (
        "the slice starts elsewhere"
    )
    assert "Important Notes" not in gate and "### " not in gate, (
        "the slice runs past the bullet"
    )


def test_the_gate_searches_the_destination_for_the_moved_ids() -> None:
    gaps = _gaps(_read(_SKILL_MD))
    assert not gaps, f"the doc-retirement gate of SKILL.md: {gaps}"


def test_every_check_reports_the_text_it_replaced() -> None:
    """The old gate stopped at the partition by `git ls-files`; each check must say so."""
    reported = _gaps(_OLD_GATE)
    assert reported == [c.label for c in _CHECKS], (
        f"{len(reported)} of {len(_CHECKS)} checks saw the old gate; blind: "
        f"{[c.label for c in _CHECKS if c.label not in reported]}"
    )


def test_the_checks_see_a_planted_gate_and_a_missing_bullet_fails_loudly() -> None:
    planted = (
        f"{_GATE_LEAD} (step 7): relocate it. Derive the id prefixes from the retired\n"
        "  file; grep the destination for them and write what each id means there.\n\n"
        f"{_GATE_END} for a checklist."
    )
    assert _gaps(planted) == [], "a wrapped sentence must still be read whole"
    assert _gaps(planted.replace("grep the destination", "search the tree")) == [
        _CHECKS[1].label
    ]
    assert _gaps(planted.replace("what each id means", "what it is")) == [
        _CHECKS[2].label
    ]
    with pytest.raises(AssertionError, match="no bullet"):
        _gate("no gate here")
    with pytest.raises(AssertionError, match="after the gate bullet"):
        _gate(f"{_GATE_LEAD} and nothing after it")
