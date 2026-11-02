"""The skill-authoring pack advises in the kit's own voice and cites no one repository's decision.

`skill-creator` and `skill-reviewer` backed several rules with a citation that only one
repository's decision record could resolve: an opaque label (a capital D and a number, in
parentheses), and "project policy" or "project convention" followed by a calendar date. A reader
of the shipped skill can look up neither. Each place now says it is the kit's recommendation or
the kit's convention, and keeps the advice it backed.

What each test asserts:

* `test_no_file_of_the_pack_cites_a_decision_by_label_or_date` scans every markdown file under
  the pack and says how many it read. Two classes of citation count: the label, and a project
  policy or convention followed straight by a date, bracketed or not.
* `test_each_citation_is_reworded_where_it_stood` is one row per place: a file and the words the
  place holds now, so a citation deleted outright, advice and all, fails too.
* `test_the_comment_row_survives_a_re_flow_of_the_template_comment` lays the frontmatter
  template comment that holds one of those places out again at every width from 20 to 140
  columns. A formatter may move its line breaks, and the `#` that starts each comment line must
  not hide the words of the row.
* The instrument tests fire the scan at planted text, so its silence on the real files means
  something. Each old shape is flagged, also across line breaks and a comment marker; each near
  miss is not; a planted folder is read, and only its markdown; the scan surface is stated in
  numbers, and the count of files read is a count of reads, not the length of a list.
"""

import os
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PACK = _REPO / "plugins" / "skill-authoring"

_CREATOR = "skills/skill-creator/SKILL.md"
_REVIEWER = "skills/skill-reviewer/SKILL.md"
_TAXONOMY = "skills/skill-reviewer/references/skill-taxonomy.md"

# The dash the skill text uses, spelled as a code point so this file stays ASCII.
_EM_DASH = chr(0x2014)


def _cat(*fragments: str) -> str:
    return "".join(fragments)


# Two classes of citation. A label: a capital D and a number in parentheses. A dated rule:
# "project policy" or "project convention", then a calendar date, bracketed or not.
_LABEL = re.compile(r"\(D\d+\)")
_DATED_RULE = re.compile(
    r"\b[Pp]roject\s+(?:policy|convention)\s*\(?\s*\d{4}-\d{2}-\d{2}"
)


def _plain(text: str) -> str:
    """The text with backticks removed and every run of whitespace, line breaks included, as
    one space, so a re-wrapped sentence reads the same as the one on a single line. A lone `#`
    is dropped too: it starts each line of the frontmatter template's comments, and a comment
    laid out again puts it between any two words."""
    return " ".join(word for word in text.replace("`", "").split() if word != "#")


def _citations(text: str) -> list[str]:
    """Every citation of either class that `text` holds."""
    plain = _plain(text)
    return [
        match.group(0)
        for pattern in (_LABEL, _DATED_RULE)
        for match in pattern.finditer(plain)
    ]


def _surface(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def _walked(root: Path) -> list[Path]:
    """The same surface by a second route, so a walk that quit descending cannot pass alone."""
    return sorted(
        Path(folder) / name
        for folder, _subfolders, names in os.walk(root)
        for name in names
        if name.endswith(".md")
    )


def _scan(root: Path) -> tuple[int, list[str]]:
    """How many files were read, and every citation found as `file: text`.

    The count goes up after a file is read, so it measures the scan and not the list the
    scan was given: a scan that stops early reports the files it reached.
    """
    read = 0
    hits: list[str] = []
    for path in _surface(root):
        text = path.read_text(encoding="utf-8")
        read += 1
        hits += [
            f"{path.relative_to(root).as_posix()}: {hit!r}" for hit in _citations(text)
        ]
    return read, hits


@dataclass(frozen=True)
class _Place:
    """One place that held a citation: its file under the pack, and the words it holds now."""

    key: str
    file: str
    carries: str


_PLACES: tuple[_Place, ...] = (
    _Place(
        "creator-when-to-use-comment",
        _CREATOR,
        "Kit recommendation: NEW skills put trigger phrases here",
    ),
    _Place(
        "reviewer-when-to-use-row",
        _REVIEWER,
        "Kit recommendation: new skills put trigger phrases here "
        "(1,536-char combined listing cap)",
    ),
    _Place(
        "creator-decision-tree",
        _CREATOR,
        f"decision tree (kit recommendation {_EM_DASH} AGENTS.md governs "
        "auto-invocation behavior):",
    ),
    _Place(
        "reviewer-decision-tree",
        _REVIEWER,
        f"Decision tree (kit recommendation {_EM_DASH} validate against the FLEET, "
        "not only theory):",
    ),
    _Place(
        "taxonomy-workflow-line",
        _TAXONOMY,
        f"Model-invocable by kit recommendation {_EM_DASH} do NOT set "
        "disable-model-invocation: true on workflows",
    ),
    _Place(
        "reviewer-name-neutrality-source",
        _REVIEWER,
        "immediate re-registration) | Kit convention |",
    ),
)

# The old shapes, one per kind of phrase the pack held. The label and the dates are spelled
# from fragments, so this file does not itself carry a decision label or a dated rule.
_OLD_SHAPES: dict[str, str] = {
    "label": f"{_cat('Project policy (D', '1)')}: new skills put trigger phrases here",
    "policy-bare-date": "Decision tree (project policy "
    f"{_cat('2026', '-06-21')} {_EM_DASH} validate against the FLEET)",
    "policy-bracketed-date": "Model-invocable by project policy "
    f"({_cat('2026', '-06-21')}) {_EM_DASH} do NOT set the flag",
    "convention-bracketed-date": "renamed | Project convention "
    f"({_cat('2026', '-08-02')}) | Rate: GOOD",
    "policy-date-after-a-comment-marker": "# (trigger lists degrade gracefully). Project policy\n"
    f"# {_cat('2026', '-06-21')}: NEW skills put trigger phrases here",
}

# Text that sits close to a citation and is not one. The label's letter and number are
# spelled from fragments here too.
_NEAR_MISSES: dict[str, str] = {
    "the-new-wording": "Kit recommendation: new skills put trigger phrases here",
    "a-rule-with-no-label-and-no-date": "Project policy: new skills put trigger phrases here",
    "an-undated-convention": "| Includes 2+ specific phrases | Project convention |",
    "a-date-that-cites-no-rule": f"(facts verified {_cat('2026', '-07-02')} against the docs)",
    "a-d-and-a-number-outside-brackets": f"the {_cat('D', '1')} cache and a (D) marker",
    "a-year-with-no-month": "project policy of the 2026 release",
}

# The size of each table above, and of the scan surface, stated so a dropped row or file is a
# failure and not a silent shrink. The surface is the pack's markdown: its README, five
# SKILL.md files and three references.
_PLACE_COUNT = 6
_OLD_SHAPE_COUNT = 5
_NEAR_MISS_COUNT = 6
_SURFACE_COUNT = 9

# The template comment of one place, and the widths it is laid out again at.
_COMMENT_KEY = "when_to_use: {trigger context}"
_WIDTHS = range(20, 141)


def _read(relative: str) -> str:
    return (_PACK / relative).read_text(encoding="utf-8")


def _carries(place: _Place, text: str) -> bool:
    return _plain(place.carries) in _plain(text)


def _reflowed(text: str, key: str, width: int) -> str:
    """`text` with the run of `#` comment lines that starts on the line holding `key` laid out
    again at `width` columns, the way a formatter would: the same words, new line breaks, the
    marker on every line."""
    lines = text.split("\n")
    start = next((index for index, line in enumerate(lines) if key in line), None)
    assert start is not None, f"no line of the text holds {key!r}"
    column = lines[start].index("#")
    end = start + 1
    while end < len(lines) and lines[end].lstrip().startswith("#"):
        end += 1
    words = " ".join(line.split("#", 1)[1] for line in lines[start:end]).split()
    pieces = textwrap.wrap(" ".join(words), width=width)
    laid = [lines[start][:column] + "# " + pieces[0]]
    laid += [" " * column + "# " + piece for piece in pieces[1:]]
    return "\n".join(lines[:start] + laid + lines[end:])


# --- the change ---------------------------------------------------------------------------


def test_no_file_of_the_pack_cites_a_decision_by_label_or_date() -> None:
    scanned, hits = _scan(_PACK)
    assert not hits, (
        f"{len(hits)} citations no reader can look up, in {scanned} files scanned:\n"
        + "\n".join(hits)
    )


@pytest.mark.parametrize("place", _PLACES, ids=[place.key for place in _PLACES])
def test_each_citation_is_reworded_where_it_stood(place: _Place) -> None:
    assert _carries(place, _read(place.file)), (
        f"{place.file} does not carry {place.carries!r}"
    )


def test_the_comment_row_survives_a_re_flow_of_the_template_comment() -> None:
    place = _PLACES[0]
    assert place.key == "creator-when-to-use-comment"
    text = _read(place.file)
    # A known positive first: with the words only folded, the comment's own spelling of this
    # phrase, marker and all, is lost at most widths, so the sweep can see what it is for.
    spelled = "Kit recommendation: # NEW skills put trigger phrases here"
    lost = [
        width
        for width in _WIDTHS
        if spelled not in " ".join(_reflowed(text, _COMMENT_KEY, width).split())
    ]
    assert lost, (
        "no width moves a line break onto the phrase, so the sweep shows nothing"
    )
    unread = [
        width
        for width in _WIDTHS
        if not _carries(place, _reflowed(text, _COMMENT_KEY, width))
    ]
    assert not unread, (
        f"{len(unread)} of {len(_WIDTHS)} widths lose the words of the row: {unread}"
    )


# --- the instruments ----------------------------------------------------------------------


@pytest.mark.parametrize("shape", list(_OLD_SHAPES))
def test_the_scan_sees_each_old_shape(shape: str) -> None:
    sample = _OLD_SHAPES[shape]
    assert _citations(sample), f"the scan missed {shape}: {sample!r}"
    # A formatter may break any line between two words; the scan must still see it.
    broken = re.sub(r" +", "\n    ", sample)
    assert broken != sample
    assert _citations(broken), f"a line break hid {shape}: {broken!r}"


@pytest.mark.parametrize("miss", list(_NEAR_MISSES))
def test_the_scan_is_silent_on_near_misses(miss: str) -> None:
    sample = _NEAR_MISSES[miss]
    assert _citations(sample) == [], f"the scan flagged {miss}: {sample!r}"


def test_a_row_sees_missing_words_and_a_re_wrap() -> None:
    place = _PLACES[2]
    held = f"**Invocation model decision tree (kit recommendation {_EM_DASH} AGENTS.md"
    held += "\n   governs auto-invocation behavior):**"
    assert _carries(place, held)
    old = f"**Invocation model decision tree (project policy 2026{'-06-21'} {_EM_DASH} AGENTS.md"
    assert not _carries(place, old + " governs auto-invocation behavior):**")
    assert not _carries(place, "")


def test_the_scan_reads_a_planted_folder_and_only_its_markdown(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()
    old = f"A rule. {_OLD_SHAPES['label']}\n"
    # The clean file sorts first and the old one last, so a scan that stops after one file
    # misses it, and so does one that reads only the first.
    (tmp_path / "skills" / "clean.md").write_text(
        f"A rule. {_NEAR_MISSES['the-new-wording']}\n", encoding="utf-8"
    )
    (tmp_path / "skills" / "old.md").write_text(old, encoding="utf-8")
    (tmp_path / "notes.txt").write_text(old, encoding="utf-8")
    scanned, hits = _scan(tmp_path)
    assert scanned == 2, f"expected the two markdown files, the scan read {scanned}"
    assert len(hits) == 1 and hits[0].startswith("skills/old.md: "), hits


def test_the_scan_surface_is_every_markdown_file_of_the_pack() -> None:
    files = _surface(_PACK)
    walked = _walked(_PACK)
    assert files == walked, f"two walks of the pack disagree: {files} against {walked}"
    assert len(files) == _SURFACE_COUNT, (
        f"the pack holds {len(files)} markdown files, not the {_SURFACE_COUNT} stated"
    )
    relative = {path.relative_to(_PACK).as_posix() for path in files}
    named = {place.file for place in _PLACES}
    assert named <= relative, (
        f"rows name files the scan misses: {sorted(named - relative)}"
    )
    empty = [name for name in sorted(relative) if not _read(name).strip()]
    assert not empty, f"files with no text, so the scan saw nothing in them: {empty}"
    scanned, _ = _scan(_PACK)
    assert scanned == _SURFACE_COUNT, (
        f"the scan read {scanned} of the {_SURFACE_COUNT} files of the pack"
    )


def test_the_tables_keep_their_stated_size() -> None:
    sizes = {
        "places": (len(_PLACES), _PLACE_COUNT),
        "old shapes": (len(_OLD_SHAPES), _OLD_SHAPE_COUNT),
        "near misses": (len(_NEAR_MISSES), _NEAR_MISS_COUNT),
    }
    wrong = [
        f"{table}: {found}, expected {expected}"
        for table, (found, expected) in sizes.items()
        if found != expected
    ]
    assert not wrong, "a table of the guard changed size: " + "; ".join(wrong)
