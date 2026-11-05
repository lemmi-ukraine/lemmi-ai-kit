"""The second operator-interface rule of the brief contract also covers a term of art and a decision question.

Item 9 of the brief contract in `orchestrate/SKILL.md` ends with a few rules that apply to every turn
addressed to a human. The second one said to expand every internal id, board code, metric name and
acronym on first use. A question that put an undefined term of art in front of the operator, or
listed the options before saying which one the orchestrator recommends, was not covered by it. The
bullet now also asks for one defining clause per term of art and for the recommendation first, then
the options, and it labels that addition `both from one recorded case`, because one recorded case is
all it rests on. The prose above the bullets says how many rules there are, so a fourth bullet would
make that prose false: the count of bullets is compared with the number word.

THE SURFACE, in numbers the tests assert: 1 file (`SKILL.md`), 1 item (item 9), 3 operator-interface
bullets under the prose count, 1 of them (the one that expands ids on first use) judged by 5 claims
and 6 phrases. A claim holds when every one of its phrases is in the bullet (lower-cased, whitespace
collapsed). Each phrase is fired at a planted removal, so a phrase the check could not see go is not
in the table. The bullet count is fired at a planted fourth bullet and at a planted prose word that
disagrees with the bullets, and at near-misses that are not bullets (a wrapped line, a quoted list
item). Every helper that cuts the item, the region or the bullet out of the file fails loudly when
what it looks for is absent or doubled, and the checks are fired at the bullet as it stood before
this change, which must be reported for exactly the four phrases the change added or reworded.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL = (
    _REPO_ROOT / "plugins" / "orchestration" / "skills" / "orchestrate" / "SKILL.md"
)

_ITEM_LEAD = "9. **The close block"
_BULLET_LEAD = "- **Expand every internal id"
_PROSE_COUNT = re.compile(r"\bPlus (\w+) operator-interface rules\b")
_NEXT_ITEM = re.compile(r"^\d+\. ")
_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}

# (claim, the phrases that must all be in the bullet; lower-cased, whitespace collapsed)
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "the lead still covers ids, board codes, metric names and acronyms on first use",
        ("expand every internal id, board code, metric name and acronym on first use",),
    ),
    (
        "a term of art needs one defining clause",
        ("a term of art needs one defining clause",),
    ),
    (
        "a decision question states the recommendation first, then the options",
        ("a decision question states your recommendation first, then the options",),
    ),
    (
        "the addition is labelled with its evidence level",
        ("(both from one recorded case)",),
    ),
    (
        "the recurrence is stated at its measured level and the test is any turn to a human",
        (
            "recurred across four consecutive measured windows",
            "whether *any* turn to a human is readable",
        ),
    ),
)

# The bullet as it stood before the change, less the quotation it carried: it holds the lead and
# the recurrence, and none of the three additions.
_PLANTED_OLD_BULLET = (
    "   - **Expand every internal id, board code, metric name and acronym on first use.** Sessions\n"
    "     repeatedly produced questions the operator could not parse. This clause has recurred\n"
    "     across four consecutive measured windows, the test is not whether the brief is\n"
    "     self-contained but whether *any* turn addressed to a human is readable.\n"
)
# What the change added or reworded, as the labels of the phrases the old bullet lacks.
_ADDED_PHRASES = (
    "a term of art needs one defining clause",
    "a decision question states your recommendation first, then the options",
    "(both from one recorded case)",
    "whether *any* turn to a human is readable",
)


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _words(text: str) -> str:
    return " ".join(text.split()).lower()


def _missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _item_9(text: str) -> str:
    """The line that starts item 9 and every line after it up to the next top-level item. Fails
    loudly when no line, or more than one, starts it."""
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith(_ITEM_LEAD)]
    assert len(starts) == 1, f"{_ITEM_LEAD!r} starts {len(starts)} lines, not 1"
    item = [lines[starts[0]]]
    for line in lines[starts[0] + 1 :]:
        if _NEXT_ITEM.match(line):
            break
        item.append(line)
    return "\n".join(item)


def _operator_region(item: str) -> str:
    """The prose line that says how many operator-interface rules there are, and everything
    after it in the item. Fails loudly when no line, or more than one, says it."""
    lines = item.split("\n")
    starts = [index for index, line in enumerate(lines) if _PROSE_COUNT.search(line)]
    assert len(starts) == 1, (
        f"{len(starts)} lines say how many operator-interface rules there are, not 1"
    )
    return "\n".join(lines[starts[0] :])


def _bullets(region: str) -> list[str]:
    """The bullets of a region, each as one line of folded whitespace. A bullet starts at three
    spaces and a dash and runs over the more deeply indented lines under it; a quoted list item
    (`>` first) and a wrapped line are not bullets."""
    bullets: list[str] = []
    for line in region.split("\n"):
        if line.startswith("   - "):
            bullets.append(line.strip())
        elif bullets and line.startswith("     ") and line.strip():
            bullets[-1] = f"{bullets[-1]} {line.strip()}"
    return [" ".join(bullet.split()) for bullet in bullets]


def _lead_bullet(bullets: list[str]) -> str:
    """The one bullet that starts with the lead of the rule about expanding ids. Fails loudly
    when no bullet, or more than one, starts with it."""
    found = [bullet for bullet in bullets if bullet.startswith(_BULLET_LEAD)]
    assert len(found) == 1, f"{_BULLET_LEAD!r} starts {len(found)} bullets, not 1"
    return found[0]


def _count_problem(region: str) -> str | None:
    """Why the number word in the prose disagrees with the bullets under it; None when they
    agree. Fails loudly when the word is not one the table knows."""
    found = _PROSE_COUNT.search(region)
    assert found is not None, "the region carries no prose count"
    word = found[1].lower()
    assert word in _NUMBER_WORDS, f"the prose count {word!r} is not in the number table"
    held = len(_bullets(region))
    if _NUMBER_WORDS[word] == held:
        return None
    return f"the prose says {word} rules and the region holds {held} bullets"


def _real_region() -> str:
    return _operator_region(_item_9(_read(_SKILL)))


def _real_bullet() -> str:
    return _lead_bullet(_bullets(_real_region()))


def test_the_surface_is_stated_in_numbers() -> None:
    phrases = [phrase for _, claim_phrases in _ROWS for phrase in claim_phrases]
    assert (len(_ROWS), len(phrases)) == (5, 6)
    assert len(_ADDED_PHRASES) == 4
    assert all(phrase in phrases for phrase in _ADDED_PHRASES)
    assert _SKILL.is_file(), _SKILL
    assert len(_bullets(_real_region())) == 3


@pytest.mark.parametrize(("claim", "phrases"), _ROWS, ids=[claim for claim, _ in _ROWS])
def test_the_bullet_states_the_claim(claim: str, phrases: tuple[str, ...]) -> None:
    missing = _missing(_words(_real_bullet()), phrases)
    assert not missing, f"the bullet does not state {claim!r}: missing {missing}"


def test_the_prose_count_equals_the_number_of_bullets() -> None:
    assert _count_problem(_real_region()) is None


def test_every_phrase_is_reported_when_it_goes() -> None:
    """Planted removal: each phrase cut out of the real bullet in turn is the one gap reported,
    and an empty bullet lacks every phrase of a row. A phrase the check cannot see go would let
    the bullet lose its rule and stay green."""
    text = _words(_real_bullet())
    for claim, phrases in _ROWS:
        assert not _missing(text, phrases), f"{claim!r} does not hold at the start"
        for phrase in phrases:
            assert _missing(text.replace(phrase, ""), phrases) == [phrase], (
                claim,
                phrase,
            )
        assert _missing("", phrases) == list(phrases), claim


def test_the_checks_report_the_bullet_as_it_stood_before_the_change() -> None:
    """The old shape is the known positive: only the four added or reworded phrases are
    reported, so the lead and the recurrence that were kept are not what turns it red."""
    old = _words(_lead_bullet(_bullets(f"{_PLANTED_OLD_BULLET}")))
    reported = [phrase for _, phrases in _ROWS for phrase in _missing(old, phrases)]
    assert reported == list(_ADDED_PHRASES), reported


def test_a_planted_fourth_bullet_or_a_wrong_number_word_is_reported() -> None:
    region = _real_region()
    assert _count_problem(region) is None
    fourth = f"{region}\n   - **A fourth rule.** Which the prose does not count.\n"
    assert _count_problem(fourth) == (
        "the prose says three rules and the region holds 4 bullets"
    )
    assert _count_problem(region.replace("Plus three", "Plus four")) == (
        "the prose says four rules and the region holds 3 bullets"
    )
    with pytest.raises(AssertionError, match="number table"):
        _count_problem(region.replace("Plus three", "Plus several"))


def test_a_wrapped_line_and_a_quoted_list_item_are_not_bullets() -> None:
    """Near-misses of the bullet count: a continuation line under a bullet and an item of a
    quoted list (`>` first) at the same indent are not a bullet each."""
    region = (
        "   Plus three operator-interface rules, which apply to every turn:\n\n"
        "   - **One.** text that wraps\n"
        "     onto a second line\n"
        "   - **Two.** text\n"
        "   > - a quoted list item\n"
        "   - **Three.** text\n"
    )
    assert len(_bullets(region)) == 3
    assert _count_problem(region) is None


def test_a_missing_item_region_or_bullet_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="starts 0 lines"):
        _item_9("no item here\n")
    with pytest.raises(AssertionError, match="starts 2 lines"):
        _item_9(f"{_ITEM_LEAD}** one\n{_ITEM_LEAD}** two\n")
    with pytest.raises(AssertionError, match="0 lines say"):
        _operator_region("9. an item with no prose count\n")
    with pytest.raises(AssertionError, match="starts 0 bullets"):
        _lead_bullet(["- **Another rule.** text"])
    with pytest.raises(AssertionError, match="starts 2 bullets"):
        _lead_bullet([f"{_BULLET_LEAD} one", f"{_BULLET_LEAD} two"])


def test_the_item_ends_at_the_next_top_level_item() -> None:
    """The item holds the quoted block and the paragraphs that trail it, and stops where the
    next numbered item starts, so the bullets of a later item are never counted."""
    text = (
        "8. **Eight.** before\n"
        f"{_ITEM_LEAD}** lead\n"
        "   > 1. quoted step\n"
        "   Plus three operator-interface rules:\n"
        "   - **One.** a\n"
        "10. **Ten.** belongs to the next item\n"
        "   - **Stray.** b\n"
    )
    item = _item_9(text)
    assert "quoted step" in item
    assert "Stray" not in item and "10. **Ten.**" not in item
    assert len(_bullets(_operator_region(item))) == 1
