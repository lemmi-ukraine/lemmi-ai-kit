"""The fixture-design text agrees with the probe, and a positive must resemble the target too.

Three places carried a rule that the probe or the experience of using it had moved past:

* Step 4 item (j) of `post-task-review` showed `--cmd '<check with {file}>'` and said nothing of the
  shell it runs in. `--cmd` goes to the platform shell, cmd.exe on Windows, where a single quote is
  an ordinary character and `|`, `&`, `<`, `>`, `^` and parentheses are syntax (the probe's own
  docstring and error list all six, and so does the item); the probe gained `--script`, which
  runs a Python checker with no shell and replaces `--cmd`, and the item now says so: write the
  check as a Python script that takes the file path, and `--script <checker.py>` replaces `--cmd`
  (the script is `<checker.py>` because `<file>` reads as the fixture). It also says that a
  positive must resemble the target too.
* Section 1 of the fixture-design reference is titled for the negative fixture only. A positive
  planted on a line unlike the real ones lets a filter that drops typical lines pass, and no negative
  catches that, so the section gained the positive's rule.
* Section 8 said `grep -c PATTERN {file}` prints one count line always, so positive and negative
  both read 1. The probe has since read a lone bare integer as its count, so that checker probes
  correctly with no flag. What stays true is the shapes whose output is more than one number; the
  section names them and says which flag fixes which, as the probe does (checked by running the
  probe on each shape).

THE SURFACE, in numbers the tests assert: 3 places in 2 files (item (j) of SKILL.md; sections 1 and
8 of the reference) and 19 checks. 16 must fail on the unedited text its place carried (`_OLD_*`),
and 3 guard what section 8 still says, so they must hold on the old text and on the new. The checks
on the script clause are also fired at the clause as the first round wrote it
(`_FIRST_ROUND_SCRIPT_CLAUSE`) and as the second left it (`_SECOND_ROUND_SHELL_CLAUSE`, which names
three of the six shell characters), and the two helpers that join needles are fired at a region
that holds only one of two. The probe script is not read or run here: its own tests pin its
behaviour.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

_SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "core"
    / "skills"
    / "post-task-review"
)
_SKILL_MD = _SKILL / "SKILL.md"
_REFERENCE = _SKILL / "references" / "fixture-design.md"
_HEADING = re.compile(r"^(#{1,6})\s")

_ITEM_J_START = "(j) **Before acting on a checker"
_ITEM_J_END = "(k) **Reading your own side"
_RESEMBLE = "A positive must resemble the target too: plant the defect on a line shaped like its real lines"


def _read(path: Path) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _plain(text: str) -> str:
    """Emphasis and code-span marks dropped and whitespace folded to one space."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", text)).strip()


def _section(text: str, heading: str, where: str) -> str:
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
        raise AssertionError(f"{where}: no heading starting {heading!r}")
    return "\n".join(body)


def _between(text: str, start: str, end: str, where: str) -> str:
    """The text from `start` up to the next `end`. Item (j) starts in the middle of a line, so it
    is cut by its two markers; either missing, or the end before the start, fails loudly."""
    begin = text.find(start)
    if begin < 0:
        raise AssertionError(f"{where}: no marker {start!r}")
    stop = text.find(end, begin)
    if stop < 0:
        raise AssertionError(f"{where}: no marker {end!r} after {start!r}")
    return text[begin:stop]


class _Check(NamedTuple):
    label: str
    holds: Callable[[str], bool]


def _says(*needles: str) -> Callable[[str], bool]:
    return lambda region: all(n in _plain(region) for n in needles)


def _lacks(*needles: str) -> Callable[[str], bool]:
    return lambda region: all(n not in _plain(region) for n in needles)


class _Place(NamedTuple):
    name: str
    path: Path
    locate: Callable[[str], str]
    checks: tuple[_Check, ...]
    old: str


# --- the old text of each place (unedited excerpts) -----------------------------------------------

_OLD_ITEM_J = r"""(j) **Before acting on a checker you wrote during this task, certify it with the seam** —
   `python "${CLAUDE_SKILL_DIR}/scripts/probe_checker.py" --cmd '<check with {file}>'
   --positive <must-match> --negative <must-not-match>` (exit 1 = blind or over-matching; paste its
   stamp beside the number). An in-session verifier gets less scrutiny than the artifacts it judges,
   yet its verdicts drive the edits. Five of one session's "blocker" findings were its own parsing
   bugs (quote-stripping, a leading `-` parsed as a grep option, an unanchored whole-file substring
   check); the failure is symmetric, since a silently-broken checker's clean pass would bless a
   defect. A zero or a wall of findings from an unprobed checker is unproven either way. **This
   step ran at task END for a month while the blind instrument had already driven the edits** —
   which is why the script exists and belongs at the moment the checker is written. Two shapes the
   probe cannot see for you: a manifest check cannot flag a file that was never in the manifest
   (pair it with a set-difference against the live tree), and a self-check whose fixtures share
   provenance with the code under test measures well-formedness, not validity.
   **The probe answers "can this checker see?" and nothing about whether your FIXTURES model
   anything real — six measured ways a green probe certifies a wrong instrument are in
   [references/fixture-design.md](references/fixture-design.md):** a negative fixture that does not
   *resemble* the target (one unbounded `sk-` pattern halted a pipeline on a branch name AND
   silently rewrote 119 real paths); a probe aimed at the pure half while the network-adjacent half
   held the API semantics (an empty-body APPROVE read as unanswered); fixture **decay**, where the
   commit that fixes the defect is what breaks the fixture; **shared provenance**, where inverting
   the match took a live count 16 → 51; a marker-gated linter's silent zero for files it never
   opened; and a text-matching tool that must normalise CRLF before comparing.
   (k) **Reading your own side of a contract cannot establish what the other side populates.**
"""

_OLD_SECTION_1 = r"""## 1. A negative fixture must RESEMBLE the target and still pass

"Something unrelated" proves nothing. The negative's whole job is to sit one step away from the
positive, so that a pattern which over-reaches gets caught.

**Measured.** `session-retrospective`'s extractor aborted with exit 3:

```
possible secret leak: matched /sk-[A-Za-z0-9_\-]{16,}/ -> sk-content-reduction-spec
```

That is the tail of a real branch name ending in `...-spec`, matched at
`...subta|sk-content-reduction-spec` because the pattern had **no left word boundary**. It was the
only `sk-` match in a 191-session corpus — a 100% false-positive rate.

The same pattern sat in two places and failed in **opposite directions at once**:

| Where | Mode | Damage |
|---|---|---|
| `LEAK_PATTERNS` | fail-closed | halted the pipeline, exit 3 |
| `REDACTIONS` | **fail-silent** | rewrote **119** real `.specs/` paths to `subta[REDACTED_KEY]` |

The redaction half is the dangerous one: no error, no signal, and an analyst reading those
transcripts sees mangled paths it cannot cite. A sibling pattern `\b[A-Fa-f0-9]{32,}\b` did the same
to **170** git SHAs and sha256 digests — this repo's primary citation anchors.

The existing tests could not catch it because their clean fixture was the literal string
`"all findings redacted"` — a trivial non-match exercising no boundary. **There was a positive
control and no resembling negative one.**

> Applies to every redactor, linter and detector — including the ones inside our own measurement
> instruments. This one had been corrupting the retrospective's evidence base for an unknown number
> of runs while reporting success.
"""

_OLD_SECTION_8 = r"""## 8. The probe's counting unit is OUTPUT LINES, and a mismatch accuses the innocent party

`probe_checker.py` counts your checker's **output lines**. Two very common checker shapes therefore
probe as `UNUSABLE / OVER-MATCHING` while being perfectly correct:

- **`grep -c PATTERN {file}`** prints one count line always, so positive and negative both yield 1.
  Measured three times independently (`positive=1 negative=1`, `positive=3 negative=2`).
- **A checker that prints an unconditional summary** (`TOTAL: n`, a per-file header) adds a line to
  every run, including the clean one.

The fix is one flag — **`--count-mode grep-c`** parses a bare integer on stdout instead of counting
lines — or make the checker print nothing when it finds nothing.

**The trap is that the FAIL is a true statement about the wrong quantity, and it points at the
innocent party**: it accuses the *pattern* of over-matching when the defect is the *counting unit*.
Read literally, it sends you to rewrite a correct pattern. Before believing an OVER-MATCHING verdict,
run the checker by hand on the negative fixture and look at what it actually printed.
"""

# The script clause of item (j) as the first round wrote it: the script was named `<file>`, which is
# also what `{file}` reads as in the same item, "that takes the file path" was dropped, and nothing
# said that the script replaces --cmd. An unedited excerpt of SKILL.md at that commit.
_FIRST_ROUND_SCRIPT_CLAUSE = r"""   stamp beside the number). `--cmd` runs in cmd.exe on Windows, where single quotes are ordinary
   characters and `|`, `^` and parentheses are shell syntax: write the check as a Python script and
   pass `--script <file>`. An in-session verifier gets less scrutiny than the artifacts it judges,
"""

# The same clause as the second round left it: the script is `<checker.py>` and replaces --cmd, and
# the shell characters are three of the six the probe lists (`&`, `<` and `>` are missing). An
# unedited excerpt of SKILL.md at that commit.
_SECOND_ROUND_SHELL_CLAUSE = r"""   --negative <must-not-match>` (exit 1 = blind or over-matching; paste its stamp beside the number). `--cmd`
   runs in cmd.exe on Windows, where single quotes are ordinary characters and `|`, `^` and parentheses
   are shell syntax: write the check as a Python script that takes the file path; `--script <checker.py>`
   replaces `--cmd`. An in-session verifier gets less scrutiny than the artifacts it judges,
"""

# --- the checks -----------------------------------------------------------------------------------

_SHELL_CHARACTERS_LABEL = "item (j) names all six shell characters (| & < > ^ and parentheses) as shell syntax"
_SCRIPT_TAKES_THE_FILE_PATH = (
    "item (j) says to write the check as a Python script that takes the file path"
)
_SCRIPT_REPLACES_CMD = "item (j) says --script <checker.py> replaces --cmd"
_RESEMBLE_LABEL = "item (j) says a positive must resemble the target too"

_ITEM_J_CHECKS: tuple[_Check, ...] = (
    _Check(
        "item (j) says --cmd runs in cmd.exe on Windows",
        _says("--cmd runs in cmd.exe on Windows"),
    ),
    _Check(
        "item (j) says single quotes are ordinary characters there",
        _says("single quotes are ordinary characters"),
    ),
    _Check(
        _SHELL_CHARACTERS_LABEL,
        _says("|, &, <, >, ^ and parentheses are shell syntax"),
    ),
    _Check(
        _SCRIPT_TAKES_THE_FILE_PATH,
        _says("write the check as a Python script that takes the file path"),
    ),
    _Check(_SCRIPT_REPLACES_CMD, _says("--script <checker.py> replaces --cmd")),
    _Check(_RESEMBLE_LABEL, _says(_RESEMBLE)),
)
_SECTION_1_CHECKS: tuple[_Check, ...] = (
    _Check(
        "section 1 carries the positive's rule, ids included",
        _says(f"{_RESEMBLE}, ids included"),
    ),
    _Check(
        "section 1 says why no negative catches a dropped-line filter",
        _says(
            "a filter that drops typical lines only lowers counts, so no negative catches it"
        ),
    ),
    _Check(
        "section 1 gives a filter that hides nearly every line of the target",
        _says("hides nearly every line"),
    ),
)
_SECTION_8_CHECKS: tuple[_Check, ...] = (
    _Check(
        "section 8 says a lone bare integer is read as its count",
        _says("when the whole output is ONE bare integer"),
    ),
    _Check(
        "section 8 says a grep -c checker probes correctly with no flag",
        _says("probes correctly with no flag"),
    ),
    _Check(
        "section 8 no longer says grep -c prints one count line always",
        _lacks("prints one count line always"),
    ),
    _Check(
        "section 8 no longer says positive and negative both yield 1",
        _lacks("positive and negative both yield 1"),
    ),
    _Check(
        "section 8 names the count printed beside other lines",
        _says("A checker that prints its count beside other lines"),
    ),
    _Check(
        "section 8 says --count-mode grep-c sums the bare integers",
        _says("--count-mode grep-c, which sums the bare integers"),
    ),
    _Check(
        "section 8 says grep-c does not fix the summary shape and reads BLIND",
        _says("the positive reads 0 and the verdict flips to BLIND"),
    ),
)
# What the rewrite had to keep, and so what the old section still says as well.
_SECTION_8_KEPT: tuple[_Check, ...] = (
    _Check(
        "section 8 still names the unconditional summary that adds a line to every run",
        _says(
            "A checker that prints an unconditional summary", "adds a line to every run"
        ),
    ),
    _Check(
        "section 8 still says to make the checker print nothing when it finds nothing",
        _says("make the checker print nothing when it finds nothing"),
    ),
    _Check(
        "section 8 still says the FAIL is true of the wrong quantity",
        _says("the FAIL is a true statement about the wrong quantity"),
    ),
)


def _item_j(text: str) -> str:
    return _between(text, _ITEM_J_START, _ITEM_J_END, "SKILL.md")


def _section_1(text: str) -> str:
    return _section(text, "## 1.", "fixture-design.md")


def _section_8(text: str) -> str:
    return _section(text, "## 8.", "fixture-design.md")


_PLACES: tuple[_Place, ...] = (
    _Place("skill-item-j", _SKILL_MD, _item_j, _ITEM_J_CHECKS, _OLD_ITEM_J),
    _Place(
        "reference-section-1", _REFERENCE, _section_1, _SECTION_1_CHECKS, _OLD_SECTION_1
    ),
    _Place(
        "reference-section-8", _REFERENCE, _section_8, _SECTION_8_CHECKS, _OLD_SECTION_8
    ),
)


def _gaps(place: _Place, text: str) -> list[str]:
    region = place.locate(text)
    return [c.label for c in place.checks if not c.holds(region)]


# --- the tests ------------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert len(_PLACES) == 3, f"{len(_PLACES)} places, not the 3 stated"
    assert len({p.path for p in _PLACES}) == 2, (
        "the 3 places are not in 2 distinct files"
    )
    checks = [c for p in _PLACES for c in p.checks]
    assert len(checks) == 16, (
        f"{len(checks)} checks that must fail on the old text, not 16"
    )
    assert len(_SECTION_8_KEPT) == 3, f"{len(_SECTION_8_KEPT)} kept checks, not 3"
    labels = [c.label for c in (*checks, *_SECTION_8_KEPT)]
    assert len(set(labels)) == len(labels), "two checks share a label"
    empty = [p.path.name for p in _PLACES if not _read(p.path).strip()]
    assert not empty, f"empty files: {empty}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_each_place_carries_its_rule(place: _Place) -> None:
    gaps = _gaps(place, _read(place.path))
    assert not gaps, f"{place.path.name} ({place.name}): {gaps}"


@pytest.mark.parametrize("place", _PLACES, ids=[p.name for p in _PLACES])
def test_every_check_of_a_place_reports_the_text_it_replaced(place: _Place) -> None:
    """The old text carried none of the new wording and all of the old: each check must say so,
    or it tests nothing."""
    reported = _gaps(place, place.old)
    assert len(reported) == len(place.checks), (
        f"{place.name}: {len(reported)} of {len(place.checks)} checks saw the old text; "
        f"blind: {[c.label for c in place.checks if c.label not in reported]}"
    )


def test_section_8_keeps_what_was_still_true_in_the_old_text_and_the_new() -> None:
    section = _section(_read(_REFERENCE), "## 8.", "fixture-design.md")
    old = _section(_OLD_SECTION_8, "## 8.", "old section 8")
    for text, name in ((section, "the new section 8"), (old, "the old section 8")):
        gaps = [c.label for c in _SECTION_8_KEPT if not c.holds(text)]
        assert not gaps, f"{name}: {gaps}"


def test_item_j_still_points_at_the_fixture_reference_and_the_probe() -> None:
    """What the edit had to keep: the pointer to the reference and the probe invocation."""
    item = _plain(_between(_read(_SKILL_MD), _ITEM_J_START, _ITEM_J_END, "SKILL.md"))
    assert "references/fixture-design.md" in item
    assert "scripts/probe_checker.py" in item
    assert "--cmd '<check with {file}>'" in item, "the --cmd invocation was dropped"


def test_a_missing_marker_or_heading_fails_loudly_and_the_cutters_see_planted_text() -> (
    None
):
    planted = f"before {_ITEM_J_START} body text {_ITEM_J_END} after"
    assert _between(planted, _ITEM_J_START, _ITEM_J_END, "planted") == (
        f"{_ITEM_J_START} body text "
    )
    with pytest.raises(AssertionError, match="no marker"):
        _between("no markers here", _ITEM_J_START, _ITEM_J_END, "planted")
    with pytest.raises(AssertionError, match="no marker"):
        _between(f"{_ITEM_J_START} but no end", _ITEM_J_START, _ITEM_J_END, "planted")
    with pytest.raises(AssertionError, match="no heading"):
        _section("## 1. Only\ntext\n", "## 8.", "planted")
    wrapped = "## 8. Planted\nprobes correctly\nwith no flag\n## 9. After\n"
    assert _says("probes correctly with no flag")(_section(wrapped, "## 8.", "planted"))
    assert not _says("probes correctly with no flag")(
        _section(wrapped, "## 9.", "planted")
    )


def test_the_script_checks_report_the_clause_as_the_first_round_wrote_it() -> None:
    """Fired at the clause as it stood. Of item (j)'s six checks the two on the shell's quotes and
    on cmd.exe hold. The one that wants all six shell characters reports it (it named three), and
    so do the two on the script: it named the script `<file>`, dropped "that takes the file path"
    and never said the script replaces --cmd. The sixth reports it too, only because this excerpt
    stops before the sentence that says a positive must resemble the target."""
    reported = [
        c.label for c in _ITEM_J_CHECKS if not c.holds(_FIRST_ROUND_SCRIPT_CLAUSE)
    ]
    assert reported == [
        _SHELL_CHARACTERS_LABEL,
        _SCRIPT_TAKES_THE_FILE_PATH,
        _SCRIPT_REPLACES_CMD,
        _RESEMBLE_LABEL,
    ]


def test_the_shell_check_reports_the_clause_that_names_three_of_the_six_characters() -> (
    None
):
    """Fired at the clause as the second round left it: the script is named right, and the only
    gap but the missing positive sentence is the three shell characters the probe's own text lists
    beside them, `&`, `<` and `>`."""
    reported = [
        c.label for c in _ITEM_J_CHECKS if not c.holds(_SECOND_ROUND_SHELL_CLAUSE)
    ]
    assert reported == [_SHELL_CHARACTERS_LABEL, _RESEMBLE_LABEL]


def test_the_shell_check_needs_every_one_of_the_six_characters() -> None:
    """Fired at the sentence whole and at the sentence with each character taken out in turn, so
    a check that settled for most of the list would pass one of them."""
    check = next(c for c in _ITEM_J_CHECKS if c.label == _SHELL_CHARACTERS_LABEL)
    whole = "`|`, `&`, `<`, `>`, `^` and parentheses are shell syntax"
    assert check.holds(whole)
    for dropped in ("`|`, ", "`&`, ", "`<`, ", "`>`, ", "`^` and "):
        assert whole.count(dropped) == 1, dropped
        assert not check.holds(whole.replace(dropped, "")), dropped
    assert not check.holds(whole.replace(" and parentheses", ""))


def test_the_needle_helpers_need_every_needle_they_are_given() -> None:
    """`_says` holds only when every needle is there and `_lacks` only when every needle is
    absent. Fired at a region that holds one of two needles, so a helper that settled for any
    needle would pass the two-needle checks on one of them."""
    region = "alpha and beta, not gamma"
    assert _says("alpha", "beta")(region)
    assert not _says("alpha", "delta")(region)
    assert _lacks("delta", "epsilon")(region)
    assert not _lacks("delta", "alpha")(region)
