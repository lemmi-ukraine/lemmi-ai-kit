"""The two AGENTS.md files give the skill's score bands for the three task sizes, not file counts.

`spec-driven-dev` classifies a task by a score over six dimensions (the number of files is one of
them) and maps the total to a size: 0 to 2 Small, 3 to 6 Medium, 7 or more Large. The seeded
AGENTS.md section and the kit's own section classified by file count alone ("1-3 files", "4-10 files",
"10+ files"), so a task of three files and a new integration was Small in one file and Large in the
other, and the agent's first read of the size rule contradicted the skill it points at.

What the text says now: each size bullet names its score band, in the same words in both files. The
bands are not hand-copied into the test: they are read from the skill's classification lines, so a
change to the skill's bands fails here until the two files follow. Only projects seeded after this
change get the bands: the bullets sit outside the blocks `kit-setup refresh` rewrites, so a project
seeded before keeps its old bullets until someone edits them by hand.

The Medium bullet also said a Medium task creates one document (`spec.md`), where the skill creates
three (spec, tasks, test plan) and adds a design document only when the Technical Approach runs past
about 60 lines. It now repeats the skill's words for both, read from the skill's Medium block the way
the bands are, and the one-document sentence is gone from both files. The plan-critic bullet of the
Plan self-review section still sent a Medium task's review to `spec.md` alone, where the skill
reviews the three documents together; it now names them in the skill's words too, the same in both
files.

A bullet is read whole, however it is wrapped: the lines after its first, indented or in column 0,
belong to it, and it is found by its folded start, so a line end anywhere in it, inside its lead
included, reads the same (`test_a_size_bullet_is_read_whole_however_it_is_re_wrapped` breaks each
bullet at every space to show it). The skill's three classification lines and its Medium sentence
are read the same way (`test_the_skill_bands_are_read_however_its_lines_are_wrapped`,
`test_the_skills_documents_are_read_however_its_sentence_is_wrapped`).

THE SURFACE, in numbers the tests assert: 2 files, 3 size bullets and 1 plan-critic bullet in each,
3 bands and 2 document phrases in the skill, and 11 checks per file (3 bands named, 3 old file counts
gone, 2 document phrases named, 1 old one-document sentence gone, and on the plan-critic bullet the
three documents named and the one-document review gone).
"""

import re
from pathlib import Path
from typing import NamedTuple

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_KIT = "AGENTS.md"
_TEMPLATE = "plugins/core/src/lemmi_ai_kit/assets/templates/AGENTS.md"
_FILES = (_KIT, _TEMPLATE)
_SKILL = "plugins/core/skills/spec-driven-dev/SKILL.md"
_SECTION = "### Spec-driven development"
_HEADING = re.compile(r"^(#{1,6})\s")
_LIST_MARKER = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")

# The old bullets held these characters; they are built from their code points, so an assertion
# written with an ASCII hyphen could never fail on text that has the en dash.
_EN = chr(0x2013)
_ARROW = chr(0x2192)
_SIZES = ("Small", "Medium", "Large")


class _Band(NamedTuple):
    size: str
    low: int
    high: int | None

    def words(self) -> str:
        """The band as the AGENTS.md bullets spell it."""
        return (
            f"{self.low} to {self.high}"
            if self.high is not None
            else f"{self.low} or more"
        )


# What the old bullets said, and what no bullet may say again.
_OLD_COUNTS = (f"1{_EN}3 files", f"4{_EN}10 files", "10+ files")
_OLD_BULLETS = (
    f"- Small tasks (1{_EN}3 files, single concern): implement directly.\n"
    f"- Medium tasks (4{_EN}10 files, new components): create a lightweight spec in "
    "`.specs/{task-name}/spec.md`.\n"
    "- Large tasks (10+ files, multi-feature, architectural): create full spec "
    "(requirements.md, design.md, tasks.md, test-cases.md + test-plan.md) in "
    "`.specs/{task-name}/`.\n"
)
# The Medium bullet said a Medium task creates one document; the skill creates three. This is the
# sentence no bullet may carry again. The control that fires at `_OLD_BULLETS` shows the excerpt
# holds it, so a retyped copy here cannot make the check blind.
_OLD_ONE_DOCUMENT = ("create a lightweight spec in `.specs/{task-name}/spec.md`",)

# The plan-critic bullet of the Plan self-review section, and the review scope it gave a Medium task:
# the one document no plan-critic bullet may send that review to again.
_PLAN_SECTION = "### Plan self-review"
_PLAN_LEAD = "- Invoke the `plan-critic` skill after writing:"
_OLD_PLAN_BULLET = (
    "- Invoke the `plan-critic` skill after writing: `spec.md` (medium tasks), `design.md` "
    "(large tasks), `tasks.md` (large tasks, completeness-only), `test-cases.md` / "
    "`test-plan.md` (Dimension 6 plus the citation check), or any bug-fix/task plan.\n"
)
_OLD_MEDIUM_REVIEW = ("`spec.md` (medium tasks)",)


def _read(relative: str) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return (_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def _section(text: str, heading: str) -> str:
    """From the first line that starts with `heading` to the next heading of the same or a higher
    level. A missing heading fails loudly, with the heading named."""
    body: list[str] = []
    level = 0
    for line in text.split("\n"):
        found = _HEADING.match(line)
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


def _bullets(section: str) -> list[str]:
    """Each list item of the section, read whole: the lines after it, indented or in column 0,
    belong to it until the next list marker, a heading or a blank line. Each is returned folded,
    so a line end put anywhere in a bullet does not make it a different bullet."""
    items: list[list[str]] = []
    open_item = False
    for line in section.split("\n"):
        if _LIST_MARKER.match(line):
            items.append([line])
            open_item = True
        elif not line.strip() or _HEADING.match(line):
            open_item = False
        elif open_item:
            items[-1].append(line)
    return [_plain(" ".join(parts)) for parts in items]


def _size_bullets(text: str) -> dict[str, str]:
    """The `- <Size> tasks (...)` bullets of the section, by size, each read whole."""
    items = _bullets(text)
    bullets: dict[str, str] = {}
    for size in _SIZES:
        lead = f"- {size} tasks ("
        found = [item for item in items if item.startswith(lead)]
        if len(found) != 1:
            raise AssertionError(
                f"expected one bullet starting {lead!r}, found {len(found)}"
            )
        bullets[size] = found[0]
    return bullets


def _skill_bands(skill_text: str) -> list[_Band]:
    """The bands from the skill's `Total score ... -> **Size**` lines, read from the folded text so
    a line end at any space of a line is the same line. Fewer than three fail loudly, so a reworded
    classification cannot leave the comparison with nothing to compare."""
    pattern = re.compile(
        rf"Total score (\d+)(?:[{_EN}-](\d+)|\+) {_ARROW} \*\*(Small|Medium|Large)\*\*"
    )
    bands = [
        _Band(m[3], int(m[1]), int(m[2]) if m[2] else None)
        for m in pattern.finditer(re.sub(r"\s+", " ", skill_text))
    ]
    if [b.size for b in bands] != list(_SIZES):
        raise AssertionError(
            f"the skill's classification lines read {bands}, not three bands"
        )
    return bands


def _skill_documents(skill_text: str) -> tuple[str, str]:
    """The two phrases of the skill's Medium block that the Medium bullet repeats in the skill's
    words: its documents ("three documents (spec, tasks, test plan)") and the one condition that
    adds a design document. Read from the folded text, so a line end at any space of the sentence
    is the same sentence, and a change to the skill fails here until the two files follow. A block
    that no longer says it fails loudly, so a reworded block cannot leave nothing to compare."""
    found = re.search(
        r"Create (three documents \([^)]+\)); (a design document is added only when [^:.;]+)",
        re.sub(r"\s+", " ", skill_text),
    )
    if found is None:
        raise AssertionError(
            "the skill's Medium block no longer reads 'Create three documents (...); a design "
            "document is added only when ...'"
        )
    return found[1], found[2]


def _document_gaps(agents_text: str, documents: tuple[str, str]) -> list[str]:
    """What the Medium bullet lacks or still carries about its documents, in `agents_text`; an empty
    list is a pass. The bullet is read whole, and each phrase is looked for whatever its case."""
    section = _section(agents_text, _SECTION)
    medium = _size_bullets(section)["Medium"]
    gaps = [
        f"Medium: the documents '{phrase}' are not named in '{medium}'"
        for phrase in documents
        if phrase.lower() not in medium.lower()
    ]
    flat = _plain(section)
    gaps += [
        f"retired one-document wording still there: {old}"
        for old in _OLD_ONE_DOCUMENT
        if old in flat
    ]
    return gaps


def _band_gaps(agents_text: str, bands: list[_Band]) -> list[str]:
    """What the section lacks or still carries about the bands, in `agents_text`; an empty list is
    a pass."""
    section = _section(agents_text, _SECTION)
    bullets = _size_bullets(section)
    gaps = [
        f"{b.size}: the band '{b.words()}' is not in '{bullets[b.size]}'"
        for b in bands
        if f"{b.size} tasks (score {b.words()}," not in bullets[b.size]
    ]
    flat = _plain(section)
    gaps += [
        f"retired file count still there: {old}" for old in _OLD_COUNTS if old in flat
    ]
    return gaps


def _gaps(
    agents_text: str, bands: list[_Band], documents: tuple[str, str]
) -> list[str]:
    """Every gap the section has, the bands and the Medium documents together."""
    return _band_gaps(agents_text, bands) + _document_gaps(agents_text, documents)


def _plan_bullet(agents_text: str) -> str:
    """The plan-critic bullet of the Plan self-review section, read whole and folded. None or two
    fail loudly, with the count named."""
    items = _bullets(_section(agents_text, _PLAN_SECTION))
    found = [item for item in items if item.startswith(_PLAN_LEAD)]
    if len(found) != 1:
        raise AssertionError(
            f"expected one bullet starting {_PLAN_LEAD!r}, found {len(found)}"
        )
    return found[0]


def _plan_gaps(agents_text: str, documents: tuple[str, str]) -> list[str]:
    """What the plan-critic bullet lacks or still carries about a Medium task's review; an empty
    list is a pass. The documents are the skill's own words, looked for whatever their case."""
    bullet = _plan_bullet(agents_text)
    gaps = (
        []
        if documents[0].lower() in bullet.lower()
        else [
            f"plan-critic: the documents '{documents[0]}' are not named in '{bullet}'"
        ]
    )
    gaps += [
        f"retired one-document review still there: {old}"
        for old in _OLD_MEDIUM_REVIEW
        if old in bullet
    ]
    return gaps


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_FILES) == 2 and len(set(_FILES)) == 2
    assert len(_OLD_COUNTS) == 3
    assert len(_OLD_ONE_DOCUMENT) == 1
    assert len(_OLD_MEDIUM_REVIEW) == 1
    documents = _skill_documents(_read(_SKILL))
    size_checks = (
        len(_SIZES) + len(_OLD_COUNTS) + len(documents) + len(_OLD_ONE_DOCUMENT)
    )
    plan_checks = 1 + len(_OLD_MEDIUM_REVIEW)
    assert size_checks + plan_checks == 11, (
        "a file is checked 11 ways: 3 bands, 3 old counts, 2 document phrases, 1 old sentence, "
        "and on the plan-critic bullet the documents named and the old review gone"
    )
    for path in _FILES:
        assert len(_size_bullets(_section(_read(path), _SECTION))) == 3, path
        assert _plan_bullet(_read(path)).startswith(_PLAN_LEAD), path
    assert len(_skill_bands(_read(_SKILL))) == 3


@pytest.mark.parametrize("path", _FILES)
def test_each_size_bullet_names_the_skills_score_band_and_no_file_count(
    path: str,
) -> None:
    gaps = _band_gaps(_read(path), _skill_bands(_read(_SKILL)))
    assert not gaps, f"{path}: {gaps}"


@pytest.mark.parametrize("path", _FILES)
def test_the_medium_bullet_names_the_skills_three_documents_and_not_one(
    path: str,
) -> None:
    gaps = _document_gaps(_read(path), _skill_documents(_read(_SKILL)))
    assert not gaps, f"{path}: {gaps}"


@pytest.mark.parametrize("path", _FILES)
def test_the_plan_critic_bullet_reviews_the_three_medium_documents_and_not_one(
    path: str,
) -> None:
    gaps = _plan_gaps(_read(path), _skill_documents(_read(_SKILL)))
    assert not gaps, f"{path}: {gaps}"


def test_the_two_files_say_the_same_plan_critic_bullet() -> None:
    kit = _plan_bullet(_read(_KIT))
    template = _plan_bullet(_read(_TEMPLATE))
    assert kit == template, f"the files disagree: {kit!r} versus {template!r}"


def test_every_plan_critic_check_fails_on_the_bullet_it_replaced() -> None:
    """Fired at the old plan-critic bullet, the three documents are reported missing and the
    one-document review is reported present: two gaps, one per check. The excerpt is shown to carry
    the old review, so a retyped one in `_OLD_MEDIUM_REVIEW` cannot make that check blind."""
    old = f"{_PLAN_SECTION} (plan-critic)\n{_OLD_PLAN_BULLET}"
    gaps = _plan_gaps(old, _skill_documents(_read(_SKILL)))
    absent = [g for g in gaps if "are not named in" in g]
    retired = [g for g in gaps if g.startswith("retired one-document review")]
    assert len(absent) == 1 and len(retired) == 1 and len(gaps) == 2, gaps
    for old_review in _OLD_MEDIUM_REVIEW:
        assert old_review in _plain(old), f"the excerpt lacks {old_review!r}"
    with pytest.raises(AssertionError, match="found 0"):
        _plan_bullet(f"{_PLAN_SECTION} (plan-critic)\n- Resolve all findings.\n")


@pytest.mark.parametrize("path", _FILES)
def test_the_plan_critic_bullet_is_read_whole_however_it_is_re_wrapped(
    path: str,
) -> None:
    """The bullet is taken from what the file says and broken at every space, in column 0 and
    indented: the section reads the same bullet each time, and it still passes."""
    documents = _skill_documents(_read(_SKILL))
    whole = _plan_bullet(_read(path))
    text = f"{_PLAN_SECTION} (plan-critic)\n{whole}\n"
    variants = _rewrapped(text, whole)
    assert len(variants) >= 4, f"{path}: the bullet gave {len(variants)} re-wraps"
    for variant in variants:
        assert _plan_bullet(variant) == whole, (
            f"{path}: a re-wrap of {whole!r} reads as a different bullet"
        )
        assert _plan_gaps(variant, documents) == [], (
            f"{path}: a re-wrap of {whole!r} breaks it"
        )


def test_the_bands_are_the_ones_the_skill_states() -> None:
    """Derived from the skill, so the numbers asserted above are not a second copy of them."""
    bands = _skill_bands(_read(_SKILL))
    assert [b.words() for b in bands] == ["0 to 2", "3 to 6", "7 or more"]


def test_the_documents_are_the_ones_the_skill_states() -> None:
    """Derived from the skill, so the phrases asserted in the bullets are not a second copy."""
    assert _skill_documents(_read(_SKILL)) == (
        "three documents (spec, tasks, test plan)",
        "a design document is added only when the Technical Approach runs past about 60 lines",
    )


def test_the_two_files_say_the_same_thing_for_the_same_bullets() -> None:
    kit = _size_bullets(_section(_read(_KIT), _SECTION))
    template = _size_bullets(_section(_read(_TEMPLATE), _SECTION))
    assert kit == template, f"the files disagree: {kit} versus {template}"


def test_every_check_fails_on_the_bullets_it_replaced() -> None:
    """A guard never shown to fail has not been shown to work: fired at the old bullets, the three
    bands are reported missing and the three file counts reported present. The old bullets carry an
    en dash, so a retyped hyphen in `_OLD_COUNTS` would show up here as a count that is not seen."""
    old = f"{_SECTION}\n{_OLD_BULLETS}"
    gaps = _band_gaps(old, _skill_bands(_read(_SKILL)))
    missing = [g for g in gaps if "is not in" in g]
    retired = [g for g in gaps if g.startswith("retired file count")]
    assert len(missing) == 3, f"{len(missing)} of 3 bands reported missing: {gaps}"
    assert len(retired) == 3, f"{len(retired)} of 3 old file counts reported: {gaps}"
    for old_count in _OLD_COUNTS:
        assert old_count in _plain(old), f"the excerpt does not carry {old_count!r}"


def test_every_document_check_fails_on_the_bullet_it_replaced() -> None:
    """Fired at the old Medium bullet, both document phrases are reported missing and the
    one-document sentence is reported present: three gaps, one per check. The excerpt is shown to
    carry the sentence, so a retyped sentence in `_OLD_ONE_DOCUMENT` cannot make that check blind."""
    old = f"{_SECTION}\n{_OLD_BULLETS}"
    gaps = _document_gaps(old, _skill_documents(_read(_SKILL)))
    absent = [g for g in gaps if "are not named in" in g]
    retired = [g for g in gaps if g.startswith("retired one-document wording")]
    assert len(absent) == 2, f"{len(absent)} of 2 document phrases reported: {gaps}"
    assert len(retired) == 1, f"{len(retired)} of 1 old sentence reported: {gaps}"
    for old_sentence in _OLD_ONE_DOCUMENT:
        assert old_sentence in _plain(old), f"the excerpt lacks {old_sentence!r}"


def test_a_medium_bullet_that_words_its_documents_differently_is_reported() -> None:
    """Planted: a bullet in the skill's words, one with the documents but not the design condition,
    one that words the same three documents another way, and one that still creates `spec.md`
    alone. Only the first is clean, and each of the others is reported once, for its own defect."""
    documents = _skill_documents(_read(_SKILL))

    def medium(sentence: str) -> str:
        return (
            f"{_SECTION}\n- Small tasks (score 0 to 2, x): a.\n"
            f"- Medium tasks (score 3 to 6, new components): {sentence}\n"
            "- Large tasks (score 7 or more, y): c.\n"
        )

    in_the_words = f"create {documents[0]} in `.specs/{{task-name}}/`; {documents[1]}."
    assert _document_gaps(medium(in_the_words), documents) == []
    no_design = f"create {documents[0]} in `.specs/{{task-name}}/`."
    assert len(_document_gaps(medium(no_design), documents)) == 1
    other_words = (
        "create three documents (spec, tasks and test plan) in `.specs/{task-name}/`; "
        f"{documents[1]}."
    )
    assert len(_document_gaps(medium(other_words), documents)) == 1
    assert len(_document_gaps(medium(_OLD_ONE_DOCUMENT[0] + "."), documents)) == 3
    with pytest.raises(AssertionError, match="no longer reads"):
        _skill_documents(
            "Create two documents (spec, tasks); a design document is added"
        )


def test_a_hyphen_is_not_the_old_text() -> None:
    """The en dash is the character the old bullets held: they carry no ASCII-hyphen form of a file
    count, so a check written with a hyphen would pass on the text it must reject."""
    flat = _plain(_OLD_BULLETS)
    assert "1-3 files" not in flat and "4-10 files" not in flat
    assert all(old in flat for old in _OLD_COUNTS)


def test_a_band_that_differs_from_the_skills_is_reported() -> None:
    """Planted: bullets whose Medium band is the skill's old file range, and a skill whose Small
    band moved. Both must be reported, and the matching text must not be."""
    skill = (
        f"- Total score 0{_EN}3 {_ARROW} **Small** {_ARROW} x\n"
        f"- Total score 4{_EN}6 {_ARROW} **Medium** {_ARROW} x\n"
        f"- Total score 7+ {_ARROW} **Large** {_ARROW} x\n"
    )
    bands = _skill_bands(skill)
    assert [b.words() for b in bands] == ["0 to 3", "4 to 6", "7 or more"]
    matching = (
        f"{_SECTION}\n- Small tasks (score 0 to 3, single concern): a.\n"
        "- Medium tasks (score 4 to 6, new components): b.\n"
        "- Large tasks (score 7 or more, multi-feature): c.\n"
    )
    assert _band_gaps(matching, bands) == []
    assert len(_band_gaps(matching, _skill_bands(_read(_SKILL)))) == 2


def test_the_readers_fail_loudly_on_a_missing_heading_bullet_or_band() -> None:
    with pytest.raises(AssertionError, match="no heading"):
        _section("### Other\n- Small tasks (score 0 to 2): a.\n", _SECTION)
    with pytest.raises(AssertionError, match="found 0"):
        _size_bullets("- Small tasks (score 0 to 2): a.\n")
    with pytest.raises(AssertionError, match="found 2"):
        _size_bullets("- Small tasks (a)\n- Small tasks (b)\n- Medium tasks (c)\n")
    with pytest.raises(AssertionError, match="not three bands"):
        _skill_bands("Total score 0 to 2 is Small")
    section = _section("### A\n- x\n### B\n- y\n", "### A")
    assert "- x" in section and "- y" not in section


def _rewrapped(text: str, line: str) -> list[str]:
    """`text` once per space of `line`, that space turned into a line end, the rest of the line
    carried on as a continuation in column 0 and again indented. Two kinds of break are left out
    because they are not a re-wrap: one inside the list marker in front of the words (no letter
    before it), and one that would put a list marker, a heading mark or a table bar first on the
    continuation, which makes another block."""
    variants: list[str] = []
    for at, char in enumerate(line):
        head, tail = line[:at], line[at + 1 :]
        if char != " " or not re.search(r"[A-Za-z]", head) or not tail.strip():
            continue
        if _LIST_MARKER.match(tail) or tail.lstrip().startswith(("#", "|", "```")):
            continue
        for pad in ("", "  "):
            variants.append(text.replace(line, f"{head}\n{pad}{tail}", 1))
    return variants


@pytest.mark.parametrize("path", _FILES)
def test_a_size_bullet_is_read_whole_however_it_is_re_wrapped(path: str) -> None:
    """A re-wrap puts the rest of a bullet on a continuation line, in column 0 or indented. Fired at
    the file's three size bullets, each on one line and broken at every space, the section reads
    the same and passes: the reader that kept only the first physical line of a bullet reported a
    band that had been wrapped away. The bullets are taken from what the file says, not located by
    their first physical line, so the guard holds however the file's own lines are wrapped."""
    bands = _skill_bands(_read(_SKILL))
    documents = _skill_documents(_read(_SKILL))
    whole = _size_bullets(_section(_read(path), _SECTION))
    text = f"{_SECTION}\n" + "\n".join(whole.values()) + "\n"
    for size in _SIZES:
        line = whole[size]
        variants = _rewrapped(text, line)
        assert len(variants) >= 4, f"{path}: {size} gave {len(variants)} re-wraps"
        for variant in variants:
            assert _gaps(variant, bands, documents) == [], (
                f"{path}: a re-wrap of {line!r} breaks it"
            )
            assert _size_bullets(_section(variant, _SECTION)) == whole, (
                f"{path}: a re-wrap of {line!r} reads as a different bullet"
            )


def test_the_skill_bands_are_read_however_its_lines_are_wrapped() -> None:
    """The bands come from the skill's three `Total score` lines, and a re-wrap may split any of
    them at any space. Each line is rebuilt from the band read from the skill and broken at every
    space, and the same three bands are read each time: the reader that matched the raw text read
    none of them once a line end fell inside `Total score N -> **Size**`, and every band test
    failed on a harmless re-wrap. The lines are rebuilt, not located in the file, so the guard
    holds however the skill's own lines are wrapped."""
    whole = _skill_bands(_read(_SKILL))
    lines: list[str] = []
    for band in whole:
        span = f"{_EN}{band.high}" if band.high is not None else "+"
        lines.append(
            f"- Total score {band.low}{span} {_ARROW} **{band.size}** then some words"
        )
    text = "\n".join(lines) + "\n"
    for line in lines:
        variants = _rewrapped(text, line)
        assert len(variants) >= 4, f"{line!r} gave {len(variants)} re-wraps"
        for variant in variants:
            assert _skill_bands(variant) == whole, (
                f"a re-wrap of {line!r} changes the bands read"
            )


def test_the_skills_documents_are_read_however_its_sentence_is_wrapped() -> None:
    """The documents come from one sentence of the skill's Medium block, and a re-wrap may split it
    at any space. The sentence is rebuilt from the two phrases read from the skill and broken at
    every space, and the same two phrases are read each time. It is rebuilt, not located in the
    file, so the guard holds however the skill's own lines are wrapped."""
    whole = _skill_documents(_read(_SKILL))
    line = f"Create {whole[0]}; {whole[1]}: then some words follow."
    text = f"### Medium Tasks\n\n{line}\n\n1. Create the spec\n"
    variants = _rewrapped(text, line)
    assert len(variants) >= 4, f"{line!r} gave {len(variants)} re-wraps"
    for variant in variants:
        assert _skill_documents(variant) == whole, (
            f"a re-wrap of {line!r} changes the documents read"
        )
