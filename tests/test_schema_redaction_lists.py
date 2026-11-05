"""The schema reference names every class of secret the extractor redacts, in both lists that say so.

The extractor masks a GitHub token by its shape. The reference lists what the extractor redacts in
two places, a bullet under "Redaction & privacy" and a clause in the passage on porting the
extractor, and neither named that class. The reference under-promised, which is the safe way to be
wrong and still a wrong list for a reader who relies on it. Nothing failed, because nothing
compared a list with the table it lists.

A CLASS is a distinct replacement the extractor writes, which is how the extractor names its own
classes. Several rules can write one replacement, and a list names a class once. `_WORDS` holds
what each list must carry for each class. The bullet is the long list and names classes finely;
the clause is a one-line summary that names families, so its words are coarser ("keys" stands for
every vendor key and named secret) and only a class that summary never named gets a word of its
own.

What is checked:

* the extractor's table and this file's table agree, in classes and in rules, so a class added to
  the extractor fails here by name. A rule that reuses a marker adds no class, which is why the
  rules are counted as well: a count that moves is the prompt to look at both lists;
* each list is cut out of its own section of the reference and judged by its own text, whitespace
  folded so that a re-wrap never matters. A heading that is not found fails, and so does a list
  that sits under another heading;
* the GitHub class is checked one level finer in the long list, which names its prefixes: every
  prefix the extractor masks, found by asking the extractor, must be named there;
* every check is fired at planted text first: the lists as they stood before the class was named,
  a re-wrapped list that has it, and near misses that must still fail. A pass over the real
  reference means something only because of those.

Not checked: the reverse direction (a list that names a class the table does not hold), and the
leak-gate table, which no live document enumerates.
"""

import importlib.util
import re
import string
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import NamedTuple, cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR = _REPO_ROOT / "plugins" / "core" / "skills" / "session-retrospective"
_SCHEMA = _SKILL_DIR / "references" / "extractor-output-schema.md"
_EXTRACTOR = _SKILL_DIR / "scripts" / "extract_sessions.py"


def _load(script: Path, name: str) -> ModuleType:
    """Import a script by path, without leaving bytecode inside the pack payload."""
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


_Table = list[tuple[re.Pattern[str], str]]
_EXTRACT = _load(_EXTRACTOR, "extract_sessions_redaction_lists")
_REDACTIONS = cast(_Table, _EXTRACT.REDACTIONS)
_redact = cast(Callable[[str], str], _EXTRACT.redact)


class _Words(NamedTuple):
    """What the long list and the short list must each carry for one class, as a pattern."""

    long_list: str
    short_list: str


_LONG, _SHORT = 0, 1
_GITHUB = "[REDACTED_GITHUB_TOKEN]"

# The replacement a rule writes -> the words each list carries for it. The short list names
# families: "keys" stands for every vendor key and named secret in it, so only the classes it
# names one for one, and the GitHub class, which it did not name at all, have a word of their own.
_WORDS: dict[str, _Words] = {
    "[REDACTED_PEM]": _Words(r"\bPEM\b", r"\bPEM\b"),
    '"private_key":"[REDACTED]"': _Words(r"\bprivate_key\b", r"\bkeys\b"),
    '"type":"[REDACTED_SA]"': _Words(r"\bservice-account\b", r"\bkeys\b"),
    "[REDACTED_KEY]": _Words(r"\bsk-", r"\bkeys\b"),
    "[REDACTED_JWT]": _Words(r"\bJWTs?\b", r"\bJWTs?\b"),
    "Authorization: Bearer [REDACTED]": _Words(
        r"\bAuthorization: Bearer\b", r"\bbearer\b"
    ),
    "Bearer [REDACTED]": _Words(r"\bBearer\b", r"\bbearer\b"),
    "[REDACTED_GOOGLE_KEY]": _Words(r"\bGoogle\b", r"\bkeys\b"),
    "[REDACTED_AWS_KEY]": _Words(r"\bAWS\b", r"\bkeys\b"),
    _GITHUB: _Words(r"\bGitHub\b", r"\bGitHub\b"),
    r"\1=[REDACTED]": _Words(r"\bgeneric\b", r"\bkeys\b"),
    "[REDACTED_HEX]": _Words(r"\bhex\b", r"\bhex\b"),
    "~": _Words(r"\bhome-(?:dir )?paths\b", r"\bhome-(?:dir )?paths\b"),
}

# The surface in numbers: rules in the extractor's table, and the classes they write.
_RULES = 19
_CLASSES = 13


def _classes(table: _Table) -> list[str]:
    """The distinct replacements a table writes, in table order: one class each."""
    return list(dict.fromkeys(replacement for _pattern, replacement in table))


def _table_gaps(table: _Table) -> list[str]:
    """Where `table` and this file's `_WORDS` disagree."""
    written = _classes(table)
    gaps = [
        f"the extractor writes {replacement!r}, and this file has no words for it"
        for replacement in written
        if replacement not in _WORDS
    ]
    gaps += [
        f"this file has words for {replacement!r}, which the extractor no longer writes"
        for replacement in _WORDS
        if replacement not in written
    ]
    if len(table) != _RULES:
        gaps.append(
            f"the table holds {len(table)} rules; this file was written against {_RULES}"
        )
    return gaps


def _github_prefixes() -> list[str]:
    """The prefixes the extractor masks as a GitHub token, found by asking it."""
    body = "Qz7Wm4" * 8
    candidates = [f"gh{letter}_" for letter in string.ascii_lowercase] + ["github_pat_"]
    return [
        prefix
        for prefix in candidates
        if _redact(f"x {prefix}{body} y") == f"x {_GITHUB} y"
    ]


# --- cutting the two lists out of the reference -----------------------------------------------

_LONG_HEADING = "## Redaction & privacy"
_LONG_LEAD = "Every emitted **content** string is redacted:"
_SHORT_HEADING = "## Porting the extractor to another repo"
_SHORT_OPENING = "(b) The redaction is"
_SHORT_CLOSING = "(c) "
_HEADING = re.compile(r"^(#{1,6})\s")


def _fold(text: str) -> str:
    return " ".join(text.split())


def _section(text: str, heading: str) -> str:
    """The lines from the heading that starts with `heading` to the next heading of the same
    or a higher level. A `#` line inside a fenced block is not a heading."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _HEADING.match(line)
        if not body:
            if found is not None and line.startswith(heading):
                level = len(found[1])
                body.append(line)
            continue
        if found is not None and len(found[1]) <= level:
            break
        body.append(line)
    assert body, f"no heading starts with {heading!r}"
    return "\n".join(body)


def _item(section: str, lead: str) -> str:
    """The list item of `section` that opens with `lead`: its dash line and the lines indented
    under it, whitespace folded."""
    for chunk in re.split(r"(?m)^(?=- )", section):
        flat = _fold(chunk)
        if flat.startswith(f"- {lead}"):
            return flat
    raise AssertionError(f"no list item of the section opens with {lead!r}")


def _clause(section: str, opening: str, closing: str) -> str:
    """From `opening` up to the next `closing`, whitespace folded."""
    flat = _fold(section)
    start = flat.find(opening)
    assert start >= 0, f"the section does not contain {opening!r}"
    end = flat.find(closing, start + len(opening))
    assert end >= 0, f"nothing in the section closes {opening!r} with {closing!r}"
    return flat[start:end].strip()


def _passages(text: str) -> dict[str, str]:
    """The two lists, each from its own section: `long` is the bullet, `short` the clause."""
    return {
        "long": _item(_section(text, _LONG_HEADING), _LONG_LEAD),
        "short": _clause(
            _section(text, _SHORT_HEADING), _SHORT_OPENING, _SHORT_CLOSING
        ),
    }


def _gaps(passage: str, column: int) -> list[str]:
    """Each class `passage` does not name, as `marker: what is missing`. The long list names the
    GitHub prefixes as well, so it also owes one gap per prefix it leaves out."""
    gaps = [
        f"{marker}: no match for {words[column]!r}"
        for marker, words in _WORDS.items()
        if not re.search(words[column], passage, re.IGNORECASE)
    ]
    if column == _LONG:
        gaps += [
            f"{_GITHUB}: the prefix {prefix!r} is not named"
            for prefix in _github_prefixes()
            if not re.search(rf"(?<![A-Za-z0-9]){re.escape(prefix)}", passage)
        ]
    return gaps


def _text() -> str:
    return _SCHEMA.read_text(encoding="utf-8")


# --- the reference as it is --------------------------------------------------------------------


def test_the_list_under_redaction_and_privacy_names_every_class_the_extractor_redacts() -> (
    None
):
    gaps = _gaps(_passages(_text())["long"], _LONG)
    assert not gaps, f"the bullet lacks {len(gaps)} class(es): {gaps}"


def test_the_clause_on_porting_names_every_class_the_extractor_redacts() -> None:
    gaps = _gaps(_passages(_text())["short"], _SHORT)
    assert not gaps, f"the clause lacks {len(gaps)} class(es): {gaps}"


def test_the_table_the_extractor_writes_is_the_table_the_words_are_written_against() -> (
    None
):
    gaps = _table_gaps(_REDACTIONS)
    assert not gaps, f"the extractor's table moved: {gaps}"
    assert (len(_REDACTIONS), len(_classes(_REDACTIONS)), len(_WORDS)) == (
        _RULES,
        _CLASSES,
        _CLASSES,
    )


def test_the_two_lists_are_cut_from_disjoint_stretches_of_the_reference() -> None:
    """Two scan surfaces judged by two rules: a stretch in both would be judged by the wrong one."""
    text = _text()
    passages = _passages(text)
    assert len(passages) == 2
    flat = _fold(text)
    spans = sorted(
        (flat.index(passage), flat.index(passage) + len(passage))
        for passage in passages.values()
    )
    assert all(flat.count(passage) == 1 for passage in passages.values())
    assert spans[0][1] <= spans[1][0], f"the two lists overlap: {spans}"


def test_the_github_prefixes_are_found_by_asking_the_extractor() -> None:
    """The prefix list is derived by probing, so it is shown to find one and to refuse another."""
    prefixes = _github_prefixes()
    assert len(prefixes) == 6
    assert "github_pat_" in prefixes
    assert "ghx_" not in prefixes


# --- the checks, fired at planted text ---------------------------------------------------------

_ARROW = chr(0x2192)
_DASH = chr(0x2014)

# The two lists as they stood before the GitHub class was named, as literals.
_OLD_LONG = (
    "- Every emitted **content** string is redacted: `sk-`/`sk-ant-` keys, JWTs, `Authorization: Bearer`,\n"
    "  GCP `private_key`/service-account JSON, PEM blocks, Google/AWS key prefixes, generic\n"
    "  `*(KEY|TOKEN|SECRET|PASSWORD|PWD|CRED)* = value`, long hex/base64, and home-dir paths "
    + _ARROW
    + " `~`.\n"
)
_OLD_SHORT = (
    "(b) The redaction is **SECRET-shapes only** (keys/JWTs/bearer/PEM/hex/home-paths) "
    + _DASH
    + " there are **no\n"
    "  email or PII patterns**. For transcripts carrying customer or research content, re-evaluate that\n"
    '  scope and state it honestly rather than claiming "redacted" generically.'
)


def _with_github_long(prefixes: list[str] | None = None) -> str:
    """The old bullet with the class added: the word, and the prefixes the extractor masks."""
    named = _github_prefixes() if prefixes is None else prefixes
    item = "GitHub tokens (" + "/".join(f"`{prefix}`" for prefix in named) + ")"
    return _OLD_LONG.replace(
        "Google/AWS key prefixes, generic", f"Google/AWS key prefixes, {item}, generic"
    )


def _with_github_short() -> str:
    """The old clause with the class added to its list."""
    return _OLD_SHORT.replace("(keys/", "(keys/GitHub tokens/")


def _rewrap(text: str, width: int) -> str:
    """`text` filled at `width` and indented as a list item, breaking at spaces only."""
    return textwrap.fill(
        _fold(text),
        width=width,
        subsequent_indent="  ",
        break_on_hyphens=False,
        break_long_words=False,
    )


def _fake_doc(
    long_item: str, short_clause: str, *, after: str = "", tail: str = ""
) -> str:
    """A small reference with the two sections the lists sit in, around the given text. `after`
    is a further bullet under the first section; `tail` runs on after the clause."""
    return (
        "# Extractor Output Schema\n\n"
        "## Redaction & privacy\n\n"
        f"{long_item.rstrip()}\n"
        f"{after}"
        "- `transcriptPath` is the one intentionally **unredacted absolute path**.\n\n"
        "## Porting the extractor to another repo\n\n"
        f"- **Porting this script elsewhere** {_DASH} three facts:\n"
        f"  (a) it pins Python 3.11+. {short_clause.strip()} (c) Root detection differs.{tail}\n"
    )


def test_the_checks_flag_the_lists_as_they_stood() -> None:
    """Planted: the old text. Each check must fire, and only for the class that was missing:
    the other twelve are found in it, which is the check's control."""
    passages = _passages(_fake_doc(_OLD_LONG, _OLD_SHORT))
    long_gaps = _gaps(passages["long"], _LONG)
    short_gaps = _gaps(passages["short"], _SHORT)
    assert len(long_gaps) == 1 + len(_github_prefixes())
    assert len(short_gaps) == 1
    assert all(gap.startswith(_GITHUB) for gap in (*long_gaps, *short_gaps)), (
        long_gaps,
        short_gaps,
    )


@pytest.mark.parametrize("width", [30, 52, 77, 100])
def test_a_re_wrapped_list_that_names_the_class_passes(width: int) -> None:
    passages = _passages(
        _fake_doc(
            _rewrap(_with_github_long(), width), _rewrap(_with_github_short(), width)
        )
    )
    assert _gaps(passages["long"], _LONG) == []
    assert _gaps(passages["short"], _SHORT) == []


@pytest.mark.parametrize("named_in", ["long", "short"])
def test_each_list_is_judged_by_its_own_text(named_in: str) -> None:
    """The class named in one list never counts for the other."""
    in_long = named_in == "long"
    passages = _passages(
        _fake_doc(
            _with_github_long() if in_long else _OLD_LONG,
            _OLD_SHORT if in_long else _with_github_short(),
        )
    )
    long_gaps = _gaps(passages["long"], _LONG)
    short_gaps = _gaps(passages["short"], _SHORT)
    if in_long:
        assert (long_gaps, len(short_gaps)) == ([], 1)
    else:
        assert (len(long_gaps), short_gaps) == (1 + len(_github_prefixes()), [])


class _NearMiss(NamedTuple):
    long_item: str
    short_clause: str
    after: str
    tail: str
    long_gaps: int
    short_gaps: int


_NAMED_IN_A_BULLET = (
    "- GitHub tokens ("
    + "/".join(f"`{p}`" for p in ("ghp_", "github_pat_"))
    + ") too.\n"
)
_NEAR_MISSES: dict[str, _NearMiss] = {
    "another-hosts-name": _NearMiss(
        _with_github_long().replace("GitHub", "GitLab"),
        _with_github_short().replace("GitHub", "GitLab"),
        "",
        "",
        1,
        1,
    ),
    "named-in-the-next-bullet": _NearMiss(
        _OLD_LONG, _OLD_SHORT, _NAMED_IN_A_BULLET, "", 1 + 6, 1
    ),
    "named-after-the-clause": _NearMiss(
        _OLD_LONG, _OLD_SHORT, "", " GitHub tokens are out of scope here.", 1 + 6, 1
    ),
    "one-prefix-of-six": _NearMiss(
        _with_github_long(["ghp_"]), _with_github_short(), "", "", 5, 0
    ),
}


@pytest.mark.parametrize("name", sorted(_NEAR_MISSES))
def test_a_near_miss_does_not_name_the_class(name: str) -> None:
    case = _NEAR_MISSES[name]
    passages = _passages(
        _fake_doc(case.long_item, case.short_clause, after=case.after, tail=case.tail)
    )
    long_gaps = _gaps(passages["long"], _LONG)
    short_gaps = _gaps(passages["short"], _SHORT)
    assert (len(long_gaps), len(short_gaps)) == (case.long_gaps, case.short_gaps), (
        long_gaps,
        short_gaps,
    )


def test_a_class_or_a_rule_added_to_the_extractor_fails_the_table_check() -> None:
    """Planted: a new class, a rule that reuses a marker (no new class, so only the rule count
    sees it), and a class dropped."""
    unseen = re.compile("x")
    new_class = [*_REDACTIONS, (unseen, "[REDACTED_SLACK_TOKEN]")]
    reused = [*_REDACTIONS, (unseen, "[REDACTED_KEY]")]
    dropped = [rule for rule in _REDACTIONS if rule[1] != _GITHUB]
    assert _table_gaps(_REDACTIONS) == []
    assert len(_table_gaps(new_class)) == 2
    assert len(_table_gaps(reused)) == 1
    assert len(_table_gaps(dropped)) == 2
    assert _classes(reused) == _classes(_REDACTIONS)


@pytest.mark.parametrize(
    "doc",
    [
        "# Title\n\nno section of either name\n",
        _fake_doc("- Something else entirely.\n", _OLD_SHORT),
        _fake_doc(_OLD_LONG, "(a) no clause of the kind"),
    ],
    ids=["no-heading", "no-bullet", "no-clause"],
)
def test_a_list_that_cannot_be_found_fails_loudly(doc: str) -> None:
    with pytest.raises(AssertionError):
        _passages(doc)


def _retitled(doc: str, heading: str, replacement: str) -> str:
    """`doc` with its one `heading` line renamed, so the list under it sits under another heading."""
    assert doc.count(heading) == 1, (
        f"the planted document does not hold {heading!r} once"
    )
    return doc.replace(heading, replacement)


class _Misplaced(NamedTuple):
    doc: str
    refusal: str


_INTACT = _fake_doc(_with_github_long(), _with_github_short())
_NEXT_SECTION = "\n\n## Appendix\n\n"
_MISPLACED: dict[str, _Misplaced] = {
    "long-heading-renamed": _Misplaced(
        _retitled(_INTACT, _LONG_HEADING, "## Privacy notes"),
        f"no heading starts with {_LONG_HEADING!r}",
    ),
    "short-heading-renamed": _Misplaced(
        _retitled(_INTACT, _SHORT_HEADING, "## Moving the extractor"),
        f"no heading starts with {_SHORT_HEADING!r}",
    ),
    "bullet-under-the-heading-after": _Misplaced(
        _fake_doc(
            "- Something else entirely.\n",
            _with_github_short(),
            tail=_NEXT_SECTION + _with_github_long(),
        ),
        f"no list item of the section opens with {_LONG_LEAD!r}",
    ),
    "clause-under-the-heading-after": _Misplaced(
        _fake_doc(
            _with_github_long(),
            "(a) no clause of the kind",
            tail=_NEXT_SECTION + _with_github_short() + " (c) Root detection differs.",
        ),
        f"the section does not contain {_SHORT_OPENING!r}",
    ),
}


@pytest.mark.parametrize("name", sorted(_MISPLACED))
def test_a_list_under_another_heading_is_not_found(name: str) -> None:
    """Planted: each list, text intact, under a heading that is not its own. The control is the
    same text under its own headings, which is found. The refusal is matched by its message, so a
    fixture that failed for another reason does not pass: only the cut can have refused it."""
    assert set(_passages(_INTACT)) == {"long", "short"}
    case = _MISPLACED[name]
    with pytest.raises(AssertionError, match=re.escape(case.refusal)):
        _passages(case.doc)
