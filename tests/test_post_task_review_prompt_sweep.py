"""The prompt cross-reference sweep of post-task-review also checks a strengthened rule and a pointer.

Step 7c-extra of SKILL.md had three items, all about a feature removed or added. It said nothing
about a rule that is added or strengthened, where sharpening it can turn an exception the prompt
tolerated into a contradiction and an example that speaks the old phrasing outweighs the
instruction; and nothing about a pointer from one prompt part to another, which has to contain the
rule it names and not only resolve to a heading.

SKILL.md sits at its line cap, so it gains ONE item (4), on ONE physical line, that carries its own
lead-in, names both checks by their key words and links the full text. The file has room for one
line and a second would cross the audit's cap, so the item is read for its line count as well as for
its words. The full text is in the review checklist reference, in a subsection named for 7c-extra,
as its checks 4 and 5.

THE SURFACE, in numbers the tests assert: 2 files (SKILL.md, section 7c-extra, 1 new numbered item
of 1 physical line after the 3 it had; the checklist, subsection 7c-extra, 2 numbered items), 3 key
phrases in the SKILL.md item and 3 in the checklist items plus the 2 items whole, 1 link, and 1 line
cap of 499 lines by `wc -l` (the audit counts one more and fails above 500). The checklist phrase `exceptions`
also stands in other items of that file, so every checklist check reads the subsection's own items
and never the file (a planted decoy item outside the subsection must not satisfy it). Each check is
fired at the section as it stood (`_OLD_SKILL_SECTION`; the checklist had no such subsection) and at
planted fixtures.
"""

import re
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
)
_SKILL_MD = _SKILL / "SKILL.md"
_CHECKLIST = _SKILL / "references" / "review-checklist.md"
_CHECKLIST_LINK = "references/review-checklist.md"
_SKILL_HEADING = "#### 7c-extra."
_CHECKLIST_HEADING = "### 7c-extra"
_LINE_CAP = 499
_LINK_TEXT = "checks 4 and 5"
_HEADING = re.compile(r"^(#{1,6})\s")
_LIST_ITEM = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_NUMBER = re.compile(r"(\d+)[.)]\s")

_EM = chr(0x2014)

# The two checks as they were filed. The checklist carries them whole; SKILL.md carries them by key words.
_ITEM_4 = (
    "When a rule is added or strengthened, re-read its own exceptions and every example that speaks "
    "its phrasing: sharpening a rule can turn a tolerated exception into a contradiction, and "
    "examples outweigh instructions."
)
_ITEM_5 = (
    "A pointer from one prompt part to another must contain the rule it names, not only resolve "
    "to a heading."
)
# What SKILL.md item 4 says: its own lead-in (the lead-in above the items speaks of a feature removed
# or added), the first check, the second check.
_SKILL_PHRASES: tuple[str, ...] = (
    "Also when a rule is added or strengthened",
    "re-read its exceptions and examples",
    "a pointer between prompt parts must contain the rule it names",
)
# The key words of the two checks inside the checklist's own items.
_CHECKLIST_PHRASES: tuple[str, ...] = (
    "exceptions",
    "examples outweigh instructions",
    "must contain the rule it names",
)

_OLD_ITEMS = f"""1. Grep the entire prompt file (and all injected partials/persona files) for every phrase
   that implies or enables the removed/added feature.
2. A single stale reference in a downstream partial is enough for the model to revert to
   old behavior {_EM} treat every mention as load-bearing.
3. Check newly written sample phrases against the prompt's Prohibited Language and Variety
   sections to avoid introducing contradictions."""
# The item on ONE physical line: SKILL.md has room for one line, and a second crosses the audit's cap.
_ITEM_4_LINES = 1
_SKILL_ITEM_4 = (
    "4. Also when a rule is added or strengthened: re-read its exceptions and examples; a pointer "
    "between prompt parts must contain the rule it names "
    "([checks 4 and 5](references/review-checklist.md#7c-extra-checks-4-and-5))"
)
# The shape the line check must reject: the same words wrapped over two lines, as the item was first
# filed.
_TWO_LINE_ITEM_4 = _SKILL_ITEM_4.replace("a pointer between", "a pointer\n   between")
_OLD_SKILL_SECTION = f"""#### 7c-extra. Prompt Cross-Reference Sweep (when prompt files were modified)

When a behavioral feature is removed from or added to a prompt template:

{_OLD_ITEMS}
"""
_NEW_SKILL_SECTION = f"{_OLD_SKILL_SECTION.rstrip()}\n{_SKILL_ITEM_4}\n"
_CHECKLIST_SECTION = f"""### 7c-extra: checks 4 and 5

Checks 4 and 5 of the prompt cross-reference sweep in SKILL.md (step 7c-extra, when prompt files
were modified). Its checks 1 to 3 cover a feature removed or added.

4. {_ITEM_4}
5. {_ITEM_5}
"""


def _checklist(subsection: str) -> str:
    """A checklist with `subsection` where the real one has it: between Step 7 and Step 8."""
    return (
        "## Step 7: Documentation Impact\n\n- [ ] Results reported\n\n"
        f"{subsection}\n## Step 8: Learnings Extraction\n\n- [ ] x\n"
    )


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return " ".join(re.sub(r"[*`]", "", text).split())


def _section(text: str, heading: str) -> str:
    """From the first line that starts with `heading` to the next heading of the same or a higher
    level; a `#` line inside a fenced block is not a heading. A missing heading fails loudly, with
    the heading named."""
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
        raise AssertionError(f"no heading starting {heading!r}")
    return "\n".join(body)


def _raw_items(section: str) -> list[list[str]]:
    """Each list item of the section, bulleted or numbered, as its physical lines: the lines after
    it, indented or in column 0, belong to it until the next list item, a heading or a blank line."""
    items: list[list[str]] = []
    open_item = False
    for line in section.split("\n"):
        if _LIST_ITEM.match(line):
            items.append([line])
            open_item = True
        elif not line.strip() or _HEADING.match(line):
            open_item = False
        elif open_item:
            items[-1].append(line)
    return items


def _items(section: str) -> list[str]:
    """Each list item of the section read whole and folded. A line end put anywhere in an item does
    not change what it says."""
    return [_plain(" ".join(parts)) for parts in _raw_items(section)]


def _numbers(section: str) -> list[int]:
    """The numbers of the numbered list items of the section, in order."""
    found = (_NUMBER.match(item) for item in _items(section))
    return [int(match[1]) for match in found if match is not None]


def _numbered_lines(section: str, number: int) -> list[str]:
    """The physical lines of the one list item numbered `number`. None or several fail loudly,
    with the count named."""
    found = [
        parts
        for parts in _raw_items(section)
        if _plain(" ".join(parts)).startswith(f"{number}. ")
    ]
    if len(found) != 1:
        raise AssertionError(
            f"expected one list item numbered {number}, found {len(found)}"
        )
    return found[0]


def _numbered(section: str, number: int) -> str:
    """The one list item numbered `number`, read whole and folded. None or several fail loudly,
    with the count named."""
    return _plain(" ".join(_numbered_lines(section, number)))


def _headings(text: str) -> list[str]:
    """The heading lines of a file, outside fenced blocks."""
    found: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and _HEADING.match(line):
            found.append(line)
    return found


def _slug(heading: str) -> str:
    """The anchor a renderer gives a heading line: lower case, punctuation other than hyphens
    dropped, each space a hyphen."""
    text = re.sub(r"^#{1,6}\s+", "", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def _line_count(text: str) -> int:
    """What `wc -l` prints: the number of line ends."""
    return text.count("\n")


def _skill_item_gaps(skill_text: str) -> list[str]:
    """What item 4 of the 7c-extra section lacks: its lead-in and the key words of both checks."""
    item = _numbered(_section(skill_text, _SKILL_HEADING), 4)
    return [
        f"item 4 lacks {phrase!r}" for phrase in _SKILL_PHRASES if phrase not in item
    ]


def _item_4_line_gaps(skill_text: str) -> list[str]:
    """What is wrong with the physical lines of item 4: it is `_ITEM_4_LINES` line, because SKILL.md
    has room for one. `_skill_item_gaps` reads the words and accepts every re-wrap; this reads the
    lines themselves."""
    count = len(_numbered_lines(_section(skill_text, _SKILL_HEADING), 4))
    if count == _ITEM_4_LINES:
        return []
    return [f"item 4 spans {count} lines, not {_ITEM_4_LINES}"]


def _link_gaps(skill_text: str, files: dict[str, str]) -> list[str]:
    """What is wrong with the link item 4 carries: it must name the checks, point at the checklist
    and reach a heading of that file that is the 7c-extra subsection. `files` maps a path
    relative to the skill folder to the file's text."""
    item = _numbered(_section(skill_text, _SKILL_HEADING), 4)
    links = [target for text, target in _LINK.findall(item) if text == _LINK_TEXT]
    if len(links) != 1:
        return [f"item 4 holds {len(links)} links named {_LINK_TEXT!r}, not 1"]
    path, _, anchor = links[0].partition("#")
    if path not in files:
        return [f"the link points at {path!r}, which is not there"]
    slugs = [_slug(heading) for heading in _headings(files[path])]
    gaps: list[str] = []
    if anchor not in slugs:
        gaps.append(f"no heading of {path} has the anchor {anchor!r}")
    if not anchor.startswith("7c-extra"):
        gaps.append(f"the anchor {anchor!r} is not the 7c-extra subsection")
    return gaps


def _checklist_gaps(checklist_text: str) -> list[str]:
    """What the checklist's 7c-extra subsection lacks: items numbered 4 and 5, each holding its
    check whole, and the key words."""
    section = _section(checklist_text, _CHECKLIST_HEADING)
    gaps: list[str] = []
    if _numbers(section) != [4, 5]:
        gaps.append(f"the items are numbered {_numbers(section)}, not [4, 5]")
        return gaps
    item_4, item_5 = _numbered(section, 4), _numbered(section, 5)
    if _plain(_ITEM_4) not in item_4:
        gaps.append("item 4 does not hold the first check whole")
    if _plain(_ITEM_5) not in item_5:
        gaps.append("item 5 does not hold the second check whole")
    both = f"{item_4} {item_5}"
    gaps += [
        f"the items lack {phrase!r}"
        for phrase in _CHECKLIST_PHRASES
        if phrase not in both
    ]
    return gaps


def test_the_surface_is_stated_in_numbers() -> None:
    skill = _read(_SKILL_MD)
    section = _section(skill, _SKILL_HEADING)
    assert _numbers(section)[:3] == [1, 2, 3], "the section lost an item it had"
    assert len(_SKILL_PHRASES) == 3 and len(set(_SKILL_PHRASES)) == 3
    assert len(_CHECKLIST_PHRASES) == 3 and len(set(_CHECKLIST_PHRASES)) == 3
    assert _LINE_CAP == 499
    assert _ITEM_4_LINES == 1
    checklist = _read(_CHECKLIST)
    assert _section(checklist, "## Step 7") and _section(checklist, "## Step 8")


def test_skill_item_4_names_both_checks_by_their_key_words() -> None:
    gaps = _skill_item_gaps(_read(_SKILL_MD))
    assert not gaps, f"section 7c-extra of post-task-review SKILL.md: {gaps}"


def test_skill_item_4_is_one_line_because_the_file_has_room_for_one() -> None:
    gaps = _item_4_line_gaps(_read(_SKILL_MD))
    assert not gaps, (
        f"section 7c-extra of post-task-review SKILL.md: {gaps}; the file stands at the audit's "
        "line cap, so the full text of a check belongs in references/review-checklist.md"
    )


def test_skill_item_4_links_the_full_text_to_a_heading_that_exists() -> None:
    files = {_CHECKLIST_LINK: _read(_CHECKLIST)}
    assert (_SKILL / _CHECKLIST_LINK).is_file(), "the file the link names is not there"
    gaps = _link_gaps(_read(_SKILL_MD), files)
    assert not gaps, f"the link of item 4 in SKILL.md: {gaps}"


def test_the_checklist_holds_both_checks_in_full() -> None:
    gaps = _checklist_gaps(_read(_CHECKLIST))
    assert not gaps, f"subsection 7c-extra of review-checklist.md: {gaps}"


def test_skill_md_stays_within_the_audits_line_cap() -> None:
    lines = _line_count(_read(_SKILL_MD))
    assert lines <= _LINE_CAP, (
        f"SKILL.md has {lines} lines by wc -l, more than {_LINE_CAP}: the audit counts one more and "
        "fails above 500, so move detail into references/"
    )
    assert _line_count("x\n" * (_LINE_CAP + 1)) > _LINE_CAP, (
        "the line count cannot see a long file"
    )
    assert _line_count("x\n" * _LINE_CAP) <= _LINE_CAP


def test_the_checks_report_the_text_they_replaced() -> None:
    """The section as it stood had three items and no item 4; the checklist had no subsection.
    Every check must fail loudly on them, and say what it found."""
    assert _numbers(_section(_OLD_SKILL_SECTION, _SKILL_HEADING)) == [1, 2, 3]
    with pytest.raises(AssertionError, match="numbered 4, found 0"):
        _skill_item_gaps(_OLD_SKILL_SECTION)
    with pytest.raises(AssertionError, match="numbered 4, found 0"):
        _link_gaps(_OLD_SKILL_SECTION, {})
    with pytest.raises(AssertionError, match="no heading"):
        _checklist_gaps(_checklist(""))


def test_the_checks_accept_the_new_text_and_every_rewrap_of_it() -> None:
    files = {_CHECKLIST_LINK: _checklist(_CHECKLIST_SECTION)}
    assert _numbers(_section(_NEW_SKILL_SECTION, _SKILL_HEADING)) == [1, 2, 3, 4]
    assert _skill_item_gaps(_NEW_SKILL_SECTION) == []
    assert _link_gaps(_NEW_SKILL_SECTION, files) == []
    assert _checklist_gaps(files[_CHECKLIST_LINK]) == []
    skill_words = _SKILL_ITEM_4.split(" ")
    for at in range(2, len(skill_words)):
        wrapped = " ".join(skill_words[:at]) + "\n   " + " ".join(skill_words[at:])
        section = _NEW_SKILL_SECTION.replace(_SKILL_ITEM_4, wrapped)
        assert _skill_item_gaps(section) == [], wrapped
        assert _link_gaps(section, files) == [], wrapped
    for item in (_ITEM_4, _ITEM_5):
        words = item.split(" ")
        for at in range(2, len(words)):
            wrapped = " ".join(words[:at]) + "\n   " + " ".join(words[at:])
            changed = _CHECKLIST_SECTION.replace(item, wrapped)
            assert _checklist_gaps(_checklist(changed)) == [], wrapped


def test_the_checks_reject_what_lacks_a_key_word_a_link_or_a_number() -> None:
    files = {_CHECKLIST_LINK: _checklist(_CHECKLIST_SECTION)}
    for phrase in _SKILL_PHRASES:
        assert phrase in _SKILL_ITEM_4, f"{phrase!r} is not in the planted item"
        mutated = _NEW_SKILL_SECTION.replace(
            _SKILL_ITEM_4, _SKILL_ITEM_4.replace(phrase, "x" * 4)
        )
        assert _skill_item_gaps(mutated) == [f"item 4 lacks {phrase!r}"], phrase
    gone = _NEW_SKILL_SECTION.replace(
        "(references/review-checklist.md#7c-extra-checks-4-and-5)", ""
    )
    assert _link_gaps(gone, files) == [
        "item 4 holds 0 links named 'checks 4 and 5', not 1"
    ]
    elsewhere = _NEW_SKILL_SECTION.replace("review-checklist.md#", "other.md#")
    assert "which is not there" in _link_gaps(elsewhere, files)[0]
    moved = _NEW_SKILL_SECTION.replace(
        "#7c-extra-checks-4-and-5", "#7c-extra-checks-4-and-6"
    )
    assert _link_gaps(moved, files) == [
        "no heading of references/review-checklist.md has the anchor '7c-extra-checks-4-and-6'"
    ]
    stray = _NEW_SKILL_SECTION.replace(
        "#7c-extra-checks-4-and-5", "#step-8-learnings-extraction"
    )
    assert _link_gaps(stray, files) == [
        "the anchor 'step-8-learnings-extraction' is not the 7c-extra subsection"
    ]
    twice = f"{_NEW_SKILL_SECTION}{_SKILL_ITEM_4}\n"
    with pytest.raises(AssertionError, match="numbered 4, found 2"):
        _skill_item_gaps(twice)
    renumbered = _CHECKLIST_SECTION.replace("4. When", "1. When").replace(
        "5. A pointer", "2. A pointer"
    )
    assert _checklist_gaps(_checklist(renumbered)) == [
        "the items are numbered [1, 2], not [4, 5]"
    ]
    for phrase in _CHECKLIST_PHRASES:
        cut = _CHECKLIST_SECTION.replace(phrase, "x" * 4)
        assert cut != _CHECKLIST_SECTION, f"{phrase!r} is not in the planted subsection"
        assert _checklist_gaps(_checklist(cut)), phrase
    one_item = _CHECKLIST_SECTION.replace(f"5. {_ITEM_5}\n", "")
    assert _checklist_gaps(_checklist(one_item)) == [
        "the items are numbered [4], not [4, 5]"
    ]
    decoy = _checklist(
        _CHECKLIST_SECTION.replace(_CHECKLIST_PHRASES[1], "x" * 4)
    ).replace("- [ ] Results reported", f"- [ ] {', '.join(_CHECKLIST_PHRASES)}")
    assert _CHECKLIST_PHRASES[1] in decoy, "the decoy item does not hold the phrase"
    assert _checklist_gaps(decoy), "a phrase outside the subsection satisfied the check"


def test_the_line_check_rejects_every_wrap_of_the_item_and_accepts_the_one_line_item() -> (
    None
):
    """Known-positives for the line check: the item as it was first filed (two lines), the same words
    wrapped at every other space, and a three-line wrap are all reported; the one-line item and the
    section as it stood (no item 4) are not accepted silently."""
    assert _TWO_LINE_ITEM_4 != _SKILL_ITEM_4, (
        "the planted two-line item is the one-line item"
    )
    assert _plain(_TWO_LINE_ITEM_4) == _plain(_SKILL_ITEM_4), (
        "the planted item says other words"
    )
    assert _item_4_line_gaps(_NEW_SKILL_SECTION) == []
    two_lines = f"{_OLD_SKILL_SECTION.rstrip()}\n{_TWO_LINE_ITEM_4}\n"
    assert _item_4_line_gaps(two_lines) == ["item 4 spans 2 lines, not 1"]
    words = _SKILL_ITEM_4.split(" ")
    for at in range(2, len(words)):
        wrapped = " ".join(words[:at]) + "\n   " + " ".join(words[at:])
        section = _NEW_SKILL_SECTION.replace(_SKILL_ITEM_4, wrapped)
        assert _item_4_line_gaps(section) == ["item 4 spans 2 lines, not 1"], wrapped
    three_lines = _SKILL_ITEM_4.replace(
        "a pointer between", "a pointer\n   between"
    ).replace("re-read its", "re-read\n   its")
    assert three_lines.count("\n") == 2
    section = _NEW_SKILL_SECTION.replace(_SKILL_ITEM_4, three_lines)
    assert _item_4_line_gaps(section) == ["item 4 spans 3 lines, not 1"]
    with pytest.raises(AssertionError, match="numbered 4, found 0"):
        _item_4_line_gaps(_OLD_SKILL_SECTION)


def test_the_slug_gives_the_anchors_of_the_checklists_own_headings() -> None:
    """Known-positives for the anchor helper, so a link that resolves is a link that resolves."""
    assert _slug("### 7c-extra: checks 4 and 5") == "7c-extra-checks-4-and-5"
    assert _slug("## Step 7: Documentation Impact") == "step-7-documentation-impact"
    assert (
        _slug("## Step 9: Close Self-Challenge (MANDATORY) ")
        == "step-9-close-self-challenge-mandatory"
    )
    headings = _headings("# A\n```\n# not a heading\n```\n## B b\n")
    assert headings == ["# A", "## B b"], "a heading inside a fenced block was counted"
