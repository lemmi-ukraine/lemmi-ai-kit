"""The checks of the spec driven dev project neutral tests that run code or compare two copies of one fact.

Only the tests that assert something provable remain: they run a command, parse data, resolve a path or compare two shipped copies. The tests that pinned that a sentence says something, and the tests of those pins, are gone; the rule each one pinned stays in the skill or reference it read.

What each remaining test asserts:

* `test_the_two_design_templates_say_the_same_on_the_line_that_names_the_conventions`: The seeded copy and the kit's own are two files that must not drift on the one line the skill points a Technical Approach at. Compared as the placeholder item, whitespace folded; a pair that differs is shown to be told apart, with the old placeholder against a changed one, so an agreement of the two real copies is not an agreement of two things the check cannot tell apart.
"""

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
# The second surface: the design template a Technical Approach starts from, in the copy every
# project is seeded with and in the kit's own. Outside the skill's folder, so no file is in both.
_TEMPLATES: dict[str, Path] = {
    "design-template-seeded": _REPO
    / "plugins"
    / "core"
    / "src"
    / "lemmi_ai_kit"
    / "assets"
    / "ai"
    / "templates"
    / "design.md",
    "design-template-kit": _REPO / ".ai" / "templates" / "design.md",
}
_TEMPLATE_ANCHOR = "Describe the overall approach"


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


_LIST_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")


def _squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _opens_item(line: str) -> bool:
    """A heading, a table row, a fence or a list marker starts a new piece of text. Any other
    non-blank line carries on the piece above it, however far it is indented."""
    return line.lstrip().startswith(("#", "|", "```")) or bool(_LIST_MARKER.match(line))


def _items(text: str) -> list[str]:
    """The text cut into the pieces a re-wrap cannot split: a fenced block, a heading, a table row,
    and a list item or a paragraph together with every continuation line after it, indented or in
    column 0. A blank line ends the piece; a heading or a table row never takes a continuation."""
    pieces: list[list[str]] = []
    current: list[str] | None = None
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if in_fence and current is not None:
                current.append(line)
                current = None
            else:
                current = [line]
                pieces.append(current)
            in_fence = not in_fence
        elif in_fence and current is not None:
            current.append(line)
        elif not line.strip():
            current = None
        elif current is None or _opens_item(line):
            current = [line]
            pieces.append(current)
            if line.lstrip().startswith(("#", "|")):
                current = None
        else:
            current.append(line)
    return ["\n".join(piece) for piece in pieces]


def _item_with(text: str, needle: str, where: str) -> str:
    """The one list item, paragraph, table row, heading or fenced block that contains `needle`,
    whatever its capitalisation and wherever a re-wrap has put a line end. None or several fail
    loudly, with the count named."""
    wanted = _squeeze(needle).lower()
    found = [item for item in _items(text) if wanted in _squeeze(item).lower()]
    if len(found) != 1:
        raise AssertionError(
            f"{where}: expected one item containing {needle!r}, found {len(found)}"
        )
    return found[0]


# --- the text each place carried before ---------------------------------------------------------


_OLD_TEMPLATE_APPROACH = (
    "{Describe the overall approach. Reference the vertical slice architecture and existing "
    "patterns where applicable.}"
)

# --- the places ---------------------------------------------------------------------------------


# --- the tests ----------------------------------------------------------------------------------


def test_the_two_design_templates_say_the_same_on_the_line_that_names_the_conventions() -> (
    None
):
    """The seeded copy and the kit's own are two files that must not drift on the one line the
    skill points a Technical Approach at. Compared as the placeholder item, whitespace folded; a
    pair that differs is shown to be told apart, with the old placeholder against a changed one,
    so an agreement of the two real copies is not an agreement of two things the check cannot
    tell apart."""

    def line_of(text: str, where: str) -> str:
        return _squeeze(_item_with(text, _TEMPLATE_ANCHOR, where))

    lines = {name: line_of(_read(path), name) for name, path in _TEMPLATES.items()}
    assert len(set(lines.values())) == 1, f"the copies disagree: {lines}"
    changed = _OLD_TEMPLATE_APPROACH.replace("vertical slice architecture", "layout")
    assert changed != _OLD_TEMPLATE_APPROACH, (
        "the planted change found nothing to change"
    )
    assert line_of(changed, "planted") != line_of(_OLD_TEMPLATE_APPROACH, "planted"), (
        "two different placeholders read as the same line"
    )
