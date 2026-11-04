"""The landing-queue reference says how several sessions share one tree: a queue, a lock, a gate.

`parallel-session-safety/references/landing-queue.md` is new. It says when to read it (two or
more sessions can write one tree) and links the shared-index protocol instead of restating it.
The queue file is one per initiative, append-only, newest line last, kept where an append does
not change the tree's status, one line per event that starts with the event word and the
machine-clock time and names who and what; the newest lock line is the lock. It shows a neutral
example of each of five events (LOCK TAKEN, LOCK TRANSFERRED after the old owner confirmed it is
idle, READY with parent, tree, how to land and the gate's result, LANDED with the real HEAD now,
LOCK FREE). Its rules: the lock before the first write and a FREE line at the end; one writer
per tree; sub-agents never write in the tree; a transfer only after the confirmation, or on the
operator's ruling when the old owner was stopped and cannot answer; a lane starts landing only on
its chain's parent and rebuilds when the parent moved; the status is read before every write (one
observed fact). The gate is run before every commit, with its path, its flags and the meaning of
each exit code, and each commit of a chain takes its own parent (the commit just landed, after the
first), patch, tree and paths file. From the first day: one orchestrator per lane plus one queue
owner, the queue and the lock before the first landing, a freeze point before the last version
stamp (a starting value, uncalibrated) and a lessons slot that survives the stamp.

THE SURFACE, in numbers the tests assert: 1 file; 2 opening sentences; 4 sections, 21 claims and
36 sentences, every claim one bullet in its own section and every sentence held whole
(lower-cased, bold marks dropped, whitespace collapsed), occurring once in its section and fired
at a planted removal, and each of the 27 sentences that has a clause also fired at a cut one; 1
sentence that opens the gate's section; 5 example lines, one per event word, in order; 1 command
whose 6 flags are exactly the flags the script's `check` takes; 2 links, both resolving to the
shared-index protocol, one of them to a section that exists there.

The same file holds the hygiene test for the 6 files this change adds (the 3 kit files and the 3
test files): no request-id shape, commit-id shape, absolute local path, host session id, host
session name or e-mail address outside the reserved `example.invalid` domain, 6 patterns, each
fired at a planted positive and a near-miss. A project's or a company's own name has no generic
shape, so that part stays a reading check and is not claimed here.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "plugins" / "orchestration" / "skills" / "parallel-session-safety"
_FILE = _SKILL / "references" / "landing-queue.md"
_SCRIPT = _SKILL / "scripts" / "landing_gate.py"
_HEADING = re.compile(r"^(#{1,6})\s")
_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_CLAUSE = re.compile(r"[,:;] ")
_FLAG = re.compile(r"(?<![\w-])--[a-z][a-z-]*")

_OPENING = (
    "read this when two or more sessions can write one working tree: it gives them one queue "
    "file, one lock and one gate.",
    "how to stage and commit in a shared index is in "
    "[shared-index-protocol.md](shared-index-protocol.md); this file does not repeat it.",
)
_GATE_SECTION = "## The gate before every commit"
_GATE_OPENS = (
    "run it in the real tree under the lock, before each commit of a chain: the first with the "
    "parent the ready line recorded, each later one with the commit just landed (now the real "
    "head) as `--parent`, and each with that commit's own patch, tree and paths file, which "
    "the ready line's script or commands give:"
)

# (section heading, ((claim id, the sentences of its bullet, whole, in order), ...)). The first
# sentence of a claim is the bold lead that opens its bullet; lower-cased, bold marks dropped.
_SECTIONS: tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    (
        "## The queue file",
        (
            (
                "one file",
                (
                    "keep one queue file per initiative, append-only, newest line last.",
                    "nobody edits or deletes an earlier line, so the order of the lines is the "
                    "order of the events.",
                ),
            ),
            (
                "where it lives",
                (
                    "keep it where an append does not change the tree's status, outside the "
                    "tree or in an ignored folder, because every gate run compares that status "
                    "line by line.",
                ),
            ),
            (
                "one line per event",
                (
                    "write one line per event.",
                    "a line starts with its event word and the machine-clock time (read with "
                    "`date` as you write it), then names who, by the session id the host "
                    "assigned ([12l](shared-index-protocol.md)), and what.",
                ),
            ),
            (
                "the lock line",
                (
                    "the newest lock line is the lock.",
                    "lock taken and lock transferred name the one session that may write the "
                    "tree; lock free says that no session does.",
                ),
            ),
        ),
    ),
    (
        "## Rules",
        (
            (
                "lock first",
                (
                    "take the lock before the first write, and end it with a lock free line.",
                    "a session that writes while the newest lock line names another session is "
                    "a second writer, whatever its file set.",
                ),
            ),
            (
                "one writer",
                (
                    "one writer per tree, through the lock.",
                    "every other session builds in its own clone or export and delivers a chain "
                    "with a ready line, so a file partition is never the only guard.",
                ),
            ),
            (
                "sub-agents",
                (
                    "sub-agents never write in the tree.",
                    "a sub-agent delivers a patch or an export; only the main session that "
                    "holds the lock lands it.",
                ),
            ),
            (
                "transfer",
                (
                    "transfer the lock only after the old owner confirms that it is idle.",
                    "waiting for that answer is the control, not asking for it: the lock "
                    "transferred line is written after the confirmation.",
                ),
            ),
            (
                "stopped owner",
                (
                    "if the old owner was stopped and cannot answer, only the operator moves "
                    "the lock.",
                    "a stopped session can be resumed later, and only the operator knows "
                    "whether it will be, so the lock transferred line quotes the operator's "
                    "ruling and the time of the owner's latest checkpoint, or says that there "
                    "is none.",
                ),
            ),
            (
                "parent",
                (
                    "a lane starts landing only when the real head equals its chain's parent.",
                    "a chain built on another commit carries trees that nobody gated.",
                ),
            ),
            (
                "rebuild",
                (
                    "a lane that finds the parent moved rebuilds on the new tip and writes a "
                    "new ready line.",
                    "the new line names the line it replaces, and nobody repairs a stopped "
                    "landing by hand.",
                ),
            ),
            (
                "status",
                (
                    "read the status before every write, not only at the start.",
                    "a session found the checkout's status unchanged by a second writer only "
                    "because it read the status before every write (observed, 2026-11-04).",
                ),
            ),
        ),
    ),
    (
        _GATE_SECTION,
        (
            (
                "what it checks",
                (
                    "what it checks: head is the parent; the status is exactly the `--allow` "
                    "lines, each written as `git status --porcelain --untracked-files=all` "
                    "prints it; nothing is staged; the patch, replayed on the parent in a "
                    "private index, writes the `--tree`; with `--paths`, the patch changes "
                    "exactly those paths; the patch changes at least one path, and `git add --` "
                    "would store exactly the patch from this working tree, because each changed "
                    "path is still the parent's file there, is not ignored, and has an executable "
                    "bit and line ends that this repository stores as the patch has them.",
                    "run it before you apply the patch, and allow only status lines for paths "
                    "the patch leaves alone: a peer's edit to a changed path fails even when its "
                    "line is allowed or hidden from the status, because `git add --` would store "
                    "it in the landing commit.",
                    "it writes nothing in the tree, the index or any ref.",
                ),
            ),
            (
                "exit 0",
                (
                    "exit 0: every check measured and passed, and it printed the landing "
                    "commands with a pathspec on both `git add --` and `git commit --`; run "
                    "each yourself, in its own call.",
                ),
            ),
            (
                "exit 1",
                (
                    "exit 1: a check failed and the output names what it saw; do not commit.",
                ),
            ),
            (
                "exit 2",
                (
                    "exit 2: it could not measure (a git error, a missing input, a patch that "
                    "does not apply), and that is never a pass.",
                ),
            ),
            (
                "landed line",
                (
                    "write the landed line only after `git rev-parse head^{tree}` prints the "
                    "`--tree`.",
                ),
            ),
        ),
    ),
    (
        "## From the first day of an initiative",
        (
            (
                "owners",
                (
                    "one orchestrator per lane, plus one queue owner.",
                    "the queue file's first lines name the queue owner and the lanes; the queue "
                    "owner keeps the landing order and the last version stamp.",
                ),
            ),
            (
                "queue first",
                (
                    "the queue and the lock exist before the first landing, so the first "
                    "landing does not invent the protocol under time pressure.",
                ),
            ),
            (
                "freeze point",
                (
                    "set a freeze point before the last version stamp.",
                    "from the freeze point (90 minutes before the stamp, a starting value, "
                    "uncalibrated) lanes land nothing and write only a drafts file, so the "
                    "stamp lands on the tree the final gates ran on.",
                ),
            ),
            (
                "lessons slot",
                (
                    "keep a lessons slot that survives the stamp: a file beside the queue, "
                    "outside the stamped tree, so a lesson found after the stamp has a home "
                    "until the next release lands it.",
                ),
            ),
        ),
    ),
)
_CLAIMS = tuple(
    (heading, claim, sentences)
    for heading, claims in _SECTIONS
    for claim, sentences in claims
)
_SENTENCES = tuple(sentence for _, _, sentences in _CLAIMS for sentence in sentences)
_LEADS = tuple(sentences[0] for _, _, sentences in _CLAIMS)
_WITH_CLAUSE = tuple(sentence for sentence in _SENTENCES if _CLAUSE.search(sentence))

_EVENTS = ("LOCK TAKEN", "LOCK TRANSFERRED", "READY", "LANDED", "LOCK FREE")
_EVENT_LINE = re.compile(
    r"^(LOCK TAKEN|LOCK TRANSFERRED|READY|LANDED|LOCK FREE) (\d{2}):(\d{2}) "
)
# What the example line of each event must name, beyond its word and its time.
_EVENT_NAMES: dict[str, tuple[str, ...]] = {
    "READY": ("parent <parent id>", "tree <tree id>", "land with", "gate exit 0"),
    "LANDED": ("<first id> .. <last id>", "real HEAD now"),
    "LOCK TRANSFERRED": ("confirmed at", "idle"),
}


def _read(path: Path = _FILE) -> str:
    """The file as text with LF line ends, so a checkout that stores CRLF reads the same."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _flat(text: str) -> str:
    """Bold marks dropped, every run of whitespace one space, lower-cased: a re-wrapped line or
    a re-emphasised word is not a different sentence."""
    return " ".join(text.replace("**", "").split()).lower()


def _section(text: str, heading: str) -> str:
    """From the first heading line that starts with `heading` to the next heading of the same
    or a higher level; a `#` line inside a fenced block is not a heading. Empty when none."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.split("\n"):
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
    return "\n".join(body)


def _item_lines(text: str) -> tuple[list[str], list[list[str]]]:
    """The lines before the first list item, and the lines of every item. An item starts at a
    line that begins with "- " outside a fenced block and runs to the next such line, so a line
    that continues it is part of it whether it is indented or sits in column 0."""
    head: list[str] = []
    items: list[list[str]] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("- "):
            items.append([line])
        elif items:
            items[-1].append(line)
        else:
            head.append(line)
    return head, items


def _bullet(text: str, lead: str) -> str:
    """The flat text of the first list item that opens with `lead`; empty when none does. An
    item that merely contains the lead further on is not that item."""
    for lines in _item_lines(text)[1]:
        flat = _flat("\n".join(lines)[2:])
        if flat.startswith(lead):
            return flat
    return ""


def _gaps(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _rewrap(text: str, width: int) -> str:
    """The list items of `text` re-wrapped at `width` columns, a continuation line indented by two
    spaces, whatever the file's own wrap was: a bold lead can break over two lines. Any other
    line is kept as it is."""
    head, items = _item_lines(text)
    out = list(head)
    for lines in items:
        words = " ".join(lines)[2:].split()
        row = "-"
        for word in words:
            if len(row) + 1 + len(word) > width and row.strip("- "):
                out.append(row)
                row = " "
            row = f"{row} {word}"
        out.append(row)
    return "\n".join(out) + "\n"


def _fence(text: str, language: str) -> list[str]:
    """The lines of the first fenced block opened with ```language; empty when there is none."""
    lines = text.split("\n")
    opener = f"```{language}"
    for start, line in enumerate(lines):
        if line.strip() == opener:
            body: list[str] = []
            for inner in lines[start + 1 :]:
                if inner.strip().startswith("```"):
                    return body
                body.append(inner)
    return []


def _real_section(heading: str) -> str:
    section = _section(_read(), heading)
    assert section.strip(), f"{heading!r} is missing from landing-queue.md"
    return section


def _event_problems(lines: list[str]) -> list[str]:
    """What is wrong with the example lines: a missing or extra event, the wrong order, a name an
    event line must carry, or a transfer written before the confirmation it reports."""
    found = [
        (match[1], int(match[2]) * 60 + int(match[3]))
        for match in map(_EVENT_LINE.match, lines)
        if match
    ]
    problems: list[str] = []
    words = [word for word, _ in found]
    if words != list(_EVENTS):
        problems.append(f"events {words}, expected {list(_EVENTS)}")
    if len(found) != len([line for line in lines if line.strip()]):
        problems.append("a line does not start with an event word and a time")
    for word, names in _EVENT_NAMES.items():
        line = next((entry for entry in lines if entry.startswith(f"{word} ")), "")
        problems += [
            f"{word} does not name {name!r}" for name in names if name not in line
        ]
    transfer = next(
        (entry for entry in lines if entry.startswith("LOCK TRANSFERRED ")), ""
    )
    confirmed = re.search(r"confirmed at (\d{2}):(\d{2})", transfer)
    at = next((minute for word, minute in found if word == "LOCK TRANSFERRED"), None)
    if (
        confirmed is not None
        and at is not None
        and int(confirmed[1]) * 60 + int(confirmed[2]) >= at
    ):
        problems.append("the transfer is not written after the confirmation")
    return problems


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    counts = (len(_SECTIONS), len(_CLAIMS), len(_SENTENCES), len(_WITH_CLAUSE))
    assert counts == (4, 21, 36, 27), counts
    every = (*_OPENING, _GATE_OPENS, *_SENTENCES)
    assert len(set(every)) == len(every), "a sentence is listed twice"
    for sentence in every:
        others = [other for other in every if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    assert _FILE.is_file(), f"{_FILE} is not a file"
    headings = [line for line in _read().split("\n") if line.startswith("## ")]
    assert headings == [heading for heading, _ in _SECTIONS], headings


def test_the_file_opens_by_saying_when_to_read_it_and_where_the_index_rules_are() -> (
    None
):
    text = _read()
    assert text.startswith("# "), "the file does not open with its title"
    opening = _flat(text.split("\n## ", 1)[0])
    assert _gaps(opening, _OPENING) == [], "the opening lost a sentence"


@pytest.mark.parametrize(
    ("heading", "claim", "sentences"), _CLAIMS, ids=[c[1] for c in _CLAIMS]
)
def test_each_section_states_its_claim(
    heading: str, claim: str, sentences: tuple[str, ...]
) -> None:
    bullet = _bullet(_real_section(heading), sentences[0])
    assert bullet, f"no bullet of {heading!r} opens with {sentences[0]!r}"
    missing = _gaps(bullet, sentences)
    assert not missing, f"the {claim!r} bullet does not state: {missing}"


def test_every_claim_is_one_bullet_with_one_home() -> None:
    """Exactly one list item of the whole file opens with each lead, and each lead occurs once
    in the file, so no rule has a second copy to drift from the first."""
    text = _read()
    for lead in _LEADS:
        openers = [
            lines
            for lines in _item_lines(text)[1]
            if _flat("\n".join(lines)[2:]).startswith(lead)
        ]
        assert len(openers) == 1, f"{len(openers)} list items open with {lead!r}"
        assert _flat(text).count(lead) == 1, f"{lead!r} occurs more than once"


def test_the_examples_show_each_event_once_in_order() -> None:
    """Five example lines, one per event word in the order a landing goes through them, each
    opening with its word and a time; READY names the parent, the tree, how to land and the
    gate's result; LANDED names what landed and the real HEAD now; and the transfer is written
    after the confirmation it reports. Planted: the READY line removed, and the first two lines
    swapped, are each reported."""
    lines = _fence(_real_section("## The queue file"), "text")
    assert len(lines) == len(_EVENTS), lines
    assert _event_problems(lines) == []
    without_ready = [line for line in lines if not line.startswith("READY ")]
    assert any("READY does not name" in p for p in _event_problems(without_ready))
    swapped = [lines[1], lines[0], *lines[2:]]
    assert any(p.startswith("events ") for p in _event_problems(swapped))
    early = [line.replace("confirmed at 14:38", "confirmed at 14:41") for line in lines]
    assert early != lines
    assert "the transfer is not written after the confirmation" in _event_problems(
        early
    )


def test_the_gate_section_opens_with_when_to_run_it() -> None:
    head = _item_lines(_real_section(_GATE_SECTION))[0]
    assert _GATE_OPENS in _flat("\n".join(head)), "the gate section lost its opening"


def test_the_command_names_the_script_and_exactly_its_flags() -> None:
    """The command runs the script that ships beside this file, with every flag its `check`
    takes and no other, so the reference and the script cannot drift apart unseen. A planted
    flag the script lacks is reported."""
    command = "\n".join(_fence(_real_section(_GATE_SECTION), "bash"))
    assert '"${CLAUDE_SKILL_DIR}/scripts/landing_gate.py" check ' in command, command
    assert _SCRIPT.is_file(), f"{_SCRIPT} is not a file"
    done = subprocess.run(
        [sys.executable, "-B", "-I", str(_SCRIPT), "check", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    offered = set(_FLAG.findall(done.stdout)) - {"--help"}
    used = set(_FLAG.findall(command))
    assert len(offered) == 6 and used == offered, (sorted(used), sorted(offered))
    planted = command.replace("--paths", "--paths <paths file> --message", 1)
    assert set(_FLAG.findall(planted)) - offered == {"--message"}


def test_the_script_states_the_same_three_exit_codes() -> None:
    """The script's own docstring says what the reference's three exit bullets say."""
    text = " ".join(_read(_SCRIPT).split())
    for said in (
        "Exit 0 only when every check measured and passed",
        "Exit 1 when a check failed",
        "Exit 2 when any check could not measure",
        "cannot-measure is never a pass",
    ):
        assert said in text, said


def test_the_links_resolve_and_the_section_they_name_exists() -> None:
    text = _read()
    targets = [target.split("#")[0] for target in _LINK.findall(text)]
    assert targets == ["shared-index-protocol.md", "shared-index-protocol.md"], targets
    protocol = _FILE.parent / "shared-index-protocol.md"
    assert protocol.is_file()
    assert any(line.startswith("### 12l.") for line in _read(protocol).split("\n"))


# --- the checks can fail -----------------------------------------------------------------------


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of its real section is the one gap reported, and
    an empty section lacks every sentence. A sentence that occurs twice would let a clause go
    and stay green."""
    for heading, claims in _SECTIONS:
        flat = _flat(_real_section(heading))
        sentences = tuple(s for _, group in claims for s in group)
        assert _gaps(flat, sentences) == [], f"{heading}: a sentence is missing"
        for sentence in sentences:
            assert flat.count(sentence) == 1, (
                f"{sentence!r} occurs {flat.count(sentence)} times"
            )
            assert _gaps(flat.replace(sentence, ""), sentences) == [sentence], sentence
        assert _gaps("", sentences) == list(sentences)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the words after the last comma, colon or semicolon of every
    sentence that has one, leads included, are cut out of the real bullet, and the claim then
    reports exactly that sentence. A check on a fragment of the sentence would stay green."""
    fired = 0
    for heading, claim, sentences in _CLAIMS:
        bullet = _bullet(_real_section(heading), sentences[0])
        assert bullet, f"no bullet of {heading!r} opens with {sentences[0]!r}"
        for sentence in sentences:
            tail = _CLAUSE.split(sentence)[-1]
            if tail == sentence:
                continue
            assert bullet.count(tail) == 1, f"{tail!r} is not a clause of one sentence"
            assert _gaps(bullet.replace(tail, ""), sentences) == [sentence], (
                claim,
                sentence,
            )
            fired += 1
    assert fired == len(_WITH_CLAUSE)


@pytest.mark.parametrize("width", [40, 72, 100])
def test_a_rewrapped_and_reemphasised_file_still_holds_every_claim(width: int) -> None:
    """Near-miss that must NOT be reported: each real section with its list items re-wrapped at
    `width` columns, so that a bold lead breaks over two lines, and bold marks around one more
    word, put after the first list item starts so that it lands in a bullet, is the same text."""
    for heading, claim, sentences in _CLAIMS:
        real = _real_section(heading)
        wrapped = _rewrap(real, width)
        cut = wrapped.index("\n- ")
        reshaped = wrapped[:cut] + wrapped[cut:].replace(" the ", " **the** ", 1)
        assert "**the**" in reshaped, f"{heading}: the planted emphasis changed nothing"
        bullet = _bullet(reshaped, sentences[0])
        assert bullet, f"{claim}: the re-wrapped bullet was not found"
        assert _gaps(bullet, sentences) == [], claim


def test_the_claims_are_judged_inside_their_section_only() -> None:
    """Planted move: the bullets of "Rules" put under "The queue file" leave a "Rules" section
    that lacks its claims and exactly them. A search of the whole file would still find every
    sentence and pass, which is why each claim is read from its own section."""
    text = _read()
    moving = _real_section("## Rules")
    head, items = _item_lines(moving)
    moved = "\n".join(line for lines in items for line in lines)
    planted = text.replace(moving, "\n".join(head)).replace(
        "## The queue file\n", f"## The queue file\n\n{moved}\n", 1
    )
    assert planted != text and moved in planted
    after = _section(planted, "## Rules")
    assert after.strip(), "the planted text has no Rules section"
    sentences = tuple(s for h, _, group in _CLAIMS if h == "## Rules" for s in group)
    assert _gaps(_flat(after), sentences) == list(sentences)
    assert _gaps(_flat(planted), sentences) == [], (
        "a whole-file search would have passed"
    )


# --- the finders -------------------------------------------------------------------------------


_FIXTURE_SECTIONS = "\n".join(
    [
        "#### Rules, a look-alike that only contains the wanted prefix",
        "## Rules",
        "first body",
        "### Deeper",
        "deeper body",
        "```bash",
        "# a comment in a fence is not a heading",
        "## nor is this one",
        "```",
        "## The gate before every commit",
        "second body",
        "",
    ]
)


def test_the_section_finder_keeps_its_edges() -> None:
    """The finder starts at the heading that begins with its text, keeps a deeper heading and a
    `#` line inside a fence, stops at the next heading of its level, finds nothing for a heading
    that is not there, and finds every section of the real file."""
    first = _section(_FIXTURE_SECTIONS, "## Rules")
    assert first.startswith("## Rules"), first
    for kept in (
        "first body",
        "deeper body",
        "a comment in a fence",
        "nor is this one",
    ):
        assert kept in first, first
    assert "second body" not in first, first
    assert "second body" in _section(_FIXTURE_SECTIONS, _GATE_SECTION)
    assert _section(_FIXTURE_SECTIONS, "## Absent") == ""
    for heading, _ in _SECTIONS:
        assert _section(_read(), heading).strip(), heading


_ITEMS = "\n".join(
    [
        "Evidence line before the list.",
        "",
        "- **The first lead is",
        "  broken over two lines.** Its body says the second lead is not here.",
        "- **The second lead.** A body that quotes the first lead is",
        "the first lead is broken over two lines. again, in column 0.",
        "```text",
        "- **A fenced lead.** It is not an item.",
        "```",
        "- **The third lead.** Last body.",
        "",
    ]
)


def test_the_bullet_and_fence_finders_keep_their_edges() -> None:
    """The bullet finder reads an item whole whether its lead is bold or broken over two lines
    and whether its continuation lines are indented or in column 0, stops at the next item, takes
    neither a fenced line nor an item that only contains the lead, and finds every real lead. The
    fence finder returns the body of the first fence of its language and nothing for another."""
    first = _bullet(_ITEMS, "the first lead is broken over two lines.")
    assert first.startswith("the first lead is broken over two lines. its body"), first
    second = _bullet(_ITEMS, "the second lead.")
    assert "in column 0" in second and "fenced lead" in second, second
    assert "last body" not in second, second
    assert _bullet(_ITEMS, "a fenced lead.") == ""
    assert _bullet(_ITEMS, "its body says") == ""
    assert _bullet(_ITEMS, "an absent lead.") == ""
    assert len(_item_lines(_ITEMS)[1]) == 3
    assert _fence(_ITEMS, "text") == ["- **A fenced lead.** It is not an item."]
    assert _fence(_ITEMS, "bash") == []
    assert all(_bullet(_read(), lead) for lead in _LEADS)


# --- hygiene of the six added files ------------------------------------------------------------


_ADDED = (
    "plugins/orchestration/skills/parallel-session-safety/references/landing-queue.md",
    "plugins/orchestration/skills/parallel-session-safety/scripts/landing_gate.py",
    "plugins/orchestration/skills/orchestrate/references/operator-questions.md",
    "tests/test_landing_gate.py",
    "tests/test_landing_queue_wording.py",
    "tests/test_operator_questions_wording.py",
)
# Generic shapes only: none names a project, a person or a session.
_FORBIDDEN: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("request id", re.compile(r"\b[A-Z]{1,4}-?\d+[a-z]?\b")),
    ("commit id", re.compile(r"\b[0-9a-f]{7,64}\b")),
    (
        "absolute local path",
        re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]|/(?:Users|home)/\w"),
    ),
    (
        "session id",
        re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
    ),
    ("session name", re.compile(r"\b[a-z]+(?:-[a-z]+)+-[0-9a-f]{2}\b")),
    (
        "e-mail address",
        re.compile(r"[\w.+-]+@(?!example\.invalid\b)[\w-]+(?:\.[\w-]+)+"),
    ),
)
# (pattern name, a planted positive, a near-miss), each assembled here so that this file's own
# text holds no match.
_CONTROLS: tuple[tuple[str, str, str], ...] = (
    (
        "request id",
        "rows " + "K" + "-" + "8a" + " and " + "PY" + "3",
        "utf-8 and HEAD~1",
    ),
    ("commit id", "at " + "1a2b" + "3c4d", "abc12 and decade"),
    (
        "absolute local path",
        "C" + ":" + "/x and " + "/" + "Us" + "ers/x",
        "https://host",
    ),
    (
        "session id",
        "-".join(["0a" * 4, "0b" * 2, "0c" * 2, "0d" * 2, "0e" * 6]),
        "0a-0b",
    ),
    ("session name", "-".join(["alpha", "beta", "c0"]), "re-read the worker-preamble"),
    (
        "e-mail address",
        "person" + "@" + "company.com",
        "gate" + "@" + "example.invalid",
    ),
)


def _hits(text: str) -> list[str]:
    return [
        f"{name}: {match.group(0)!r}"
        for name, pattern in _FORBIDDEN
        for match in pattern.finditer(text)
    ]


def test_the_added_files_carry_no_id_session_or_local_path() -> None:
    """First the instrument: each pattern sees its planted positive and passes its near-miss.
    Then all 6 added files exist and are scanned whole, with the scan surface printed beside the
    hits. Red when a file is missing, so a scan of fewer files never passes as clean."""
    assert [name for name, _ in _FORBIDDEN] == [name for name, _, _ in _CONTROLS]
    for name, positive, near_miss in _CONTROLS:
        pattern = dict(_FORBIDDEN)[name]
        assert pattern.search(positive), f"{name}: the planted {positive!r} is not seen"
        assert not pattern.search(near_miss), (
            f"{name}: the near-miss {near_miss!r} is hit"
        )
    scanned = 0
    found: list[str] = []
    for relative in _ADDED:
        path = _ROOT / relative
        assert path.is_file(), f"{relative} is not a file"
        text = path.read_text(encoding="utf-8")
        assert text.strip(), f"{relative} is empty"
        scanned += len(text.splitlines())
        found += [f"{relative}: {hit}" for hit in _hits(text)]
    assert found == [], (
        f"{len(found)} hits in {len(_ADDED)} files, {scanned} lines: {found}"
    )
    assert scanned > 0
