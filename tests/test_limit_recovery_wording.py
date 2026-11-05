"""The kit says how to size a wave, wait out a usage limit and keep work where a stop cannot reach it.

A usage limit stops every agent on an account at once, and the kit said only to preflight the usage
window and checkpoint before a wave. It said nothing on what a wave costs, on limits being per
model, on what restarts a session that waits for a reset, on which model a sub-agent runs when its
call names none, or on where work survives a lost clone or a full disk.

What the text says now, in five places of five files:

* a new reference, `orchestrate/references/limit-recovery.md`, opens with one line that says when to
  read it, says which skill text it adds to, and marks every number as a starting value,
  uncalibrated, unless its sentence says it was observed. Its three sections say: size a wave in
  tokens and state its cost shape before any wave (with the observed start cost of a sub-agent),
  the window per account, the verification budget reserved first with builders no wider than the
  cap the initiative planner derives and verifiers in sub-waves, and an explicit `model` on every
  sub-agent call; probe each model before a wave and trust the probe over a printed reset time;
  write the next wake condition before waiting, read the clock at every wake, a session arms a
  waiter at a printed reset time while a sub-agent stays in its turn, anchor and test a waiter's
  pattern twice, and stop the child processes a stopped task leaves behind;
* section 2 of the worker preamble holds a "Durable state" group: a lead paragraph and five bullets
  (a patch after each verified commit into a git-excluded folder, no overnight work in an OS-temp
  clone, `git fsck` and a pack backup at clone time, the test run's temporary folder made and
  deleted in one command, a free-disk floor before a wave), each with its reason;
* the "Context" section of the brief template's skeleton has the dispatcher name the patch folder
  and the free-disk floor;
* the "Orchestration and delegation" section of the kit's own AGENTS.md and of the seeded template
  hold one bullet of at most three lines, in the same words, on the explicit `model` and on sizing a
  wave in tokens, pointing at the reference.

Two fixes follow a cold read of the new reference. It gave a start threshold of about 8 agents and
a builder width of 8 at a time, each as a starting value, where the initiative planner's step 4
forbids a concurrency number with no derivation and the orchestrate skill's section 1b says the kit
sets no number and no default cap; the reference now says "before any wave" and "no wider than the
cap you derived", and carries no agent count (the figure check below holds it to the four tagged
figures that remain). And its waiter bullet said a completion notice restarts a stopped session,
while the runtime-hazards reference of `agent-delegate` says a sub-agent that ended its turn was not
woken, and the two were told apart only by "worker" and "session": the waiter is now a session's,
and a sub-agent stays in its turn, with a pointer to that reference.

A last guard holds every place this change wrote outside `tests/` to the kit's publication rule:
no request id, no absolute local path and no commit id. It reads the three whole files and the
"Orchestration and delegation" section of each AGENTS.md; the rest of those two files is not this
change's, and already carries a home-path example in a rule and, in the kit's own file, a commit id.

THE SURFACE, in numbers the tests assert: 5 places in 5 files; 13 claims and 30 sentences in the
reference, 4 tagged figures and 6 links in it; 6 claims and 13 sentences in section 2 of the
preamble; 1 claim and 1 sentence in the skeleton's "Context" section; 1 claim and 2 sentences in the
"Orchestration and delegation" section of each AGENTS.md. The id scan reads 5 regions, 3 whole files
and 2 sections, with 5 patterns. A claim holds when the block it names (a paragraph or a list item,
read whole) holds every one of its sentences whole (lower-cased, bold marks dropped, whitespace
collapsed). Each sentence occurs once in its place and is fired at a planted removal, and each
sentence of more than three words also at a planted cut of its last clause.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATION_SKILLS = _ROOT / "plugins" / "orchestration" / "skills"
_REFERENCE = _ORCHESTRATION_SKILLS / "orchestrate" / "references" / "limit-recovery.md"
_PREAMBLE = _ORCHESTRATION_SKILLS / "agent-delegate" / "assets" / "worker-preamble.md"
_TEMPLATE = _ORCHESTRATION_SKILLS / "orchestrate" / "references" / "brief-template.md"
_KIT_AGENTS = _ROOT / "AGENTS.md"
_SEEDED_AGENTS = (
    _ROOT
    / "plugins"
    / "core"
    / "src"
    / "lemmi_ai_kit"
    / "assets"
    / "templates"
    / "AGENTS.md"
)
_AGENTS_FILES = (_KIT_AGENTS, _SEEDED_AGENTS)

_DOT = chr(0xB7)  # the middle dot in the preamble's numbered headings
_SECT = chr(0xA7)  # the section sign the reference uses for a skill's sections
_SECTION_2 = f"## 2 {_DOT}"
_SECTION_3 = f"## 3 {_DOT}"
_CONTEXT = "## Context"
_ORCHESTRATION = "### Orchestration and delegation"
_HEADING = re.compile(r"^(#{1,6})\s")
_RULE = re.compile(r"^-{3,}\s*$")  # the `---` line that ends each numbered section
_REFERENCE_MAX_LINES = 70
_AGENTS_MAX_LINES = 3

Claim = tuple[str, tuple[str, ...]]

# The reference's claims by the region that holds them: the text above its first `##` heading, and
# each `##` section. (claim id, the sentences of its block, whole, in order; lower-cased, bold marks
# dropped, whitespace collapsed.) The first sentence is the lead that opens the block.
_REFERENCE_REGIONS: tuple[tuple[str, tuple[Claim, ...]], ...] = (
    (
        "",
        (
            (
                "when to read",
                (
                    "read this before you start or resume a wave of sub-agents, and when a usage "
                    "limit stops one.",
                ),
            ),
            (
                "scope",
                (
                    f"it adds to the usage preflight of [`skill.md` {_SECT} 1b](../skill.md) and to "
                    '"resuming a worker" in the [`agent-delegate` skill](../../agent-delegate/'
                    "skill.md), and repeats neither.",
                    "each number below is a starting value, uncalibrated, unless its sentence says "
                    "it was observed: replace it with your own measurement.",
                    f"none is a cap the kit sets; a project that states its own cap ({_SECT} 1b) "
                    "uses that one.",
                ),
            ),
        ),
    ),
    (
        "## Size the wave in tokens",
        (
            (
                "cost shape",
                (
                    "size a wave in tokens, not agents, and state its cost shape before any wave.",
                    "the cost shape is the start cost times the number of agents, plus the work "
                    "each one does, set against what is left of the window.",
                    "a fresh sub-agent costs about 54k tokens of fixed context before it does "
                    "anything (observed, 2026-11-04), and three fresh read-only sub-agents cost "
                    "363k to 479k tokens each over 30 to 37 minutes (observed, 2026-11-04).",
                    f"a spawned session's start cost is measured in [dispatch-economics {_SECT} 4]"
                    "(../../initiative-planner/references/dispatch-economics.md).",
                ),
            ),
            (
                "window",
                (
                    "until you have measured your own, spend no more than about 4 m sub-agent "
                    "tokens per 5-hour window per account (starting value, uncalibrated).",
                    "every session on the account draws on the same window.",
                ),
            ),
            (
                "verification first",
                (
                    "reserve the verification budget first, then run builders no wider than the cap "
                    "you derived ([`initiative-planner` step 4](../../initiative-planner/"
                    "skill.md)) and verifiers in sub-waves.",
                    "builders that start first spend the window the verifiers needed, and work "
                    "that nobody verified cannot ship.",
                ),
            ),
            (
                "explicit model",
                (
                    "pass an explicit `model` on every sub-agent call.",
                    "a sub-agent inherits its parent's model when the call names none, so a wave "
                    "started from a session on a large model runs every mechanical row on that "
                    "model and drains its bucket.",
                ),
            ),
        ),
    ),
    (
        "## Probe before you start or resume",
        (
            (
                "probe",
                (
                    "probe each model bucket with a one-word agent before you start or resume a "
                    "wave.",
                    "limits are per model, so one model can be stopped while another answers, and "
                    "a probe costs one agent's start cost.",
                ),
            ),
            (
                "reset time",
                (
                    "trust the probe, not a printed reset time.",
                    "a limit printed a reset time that the bucket had already passed, and the "
                    "one-word probe answered within minutes (observed once).",
                ),
            ),
        ),
    ),
    (
        "## When a limit stops the wave",
        (
            (
                "wake first",
                (
                    "write the checkpoint's next wake condition before you wait.",
                    "a session stopped during the wait leaves its successor the one fact it "
                    "needs, what it was waiting for ([worker preamble](../../agent-delegate/"
                    "assets/worker-preamble.md), section 3).",
                ),
            ),
            (
                "waiter",
                (
                    "on a printed reset time, a session arms a background waiter that exits at that "
                    "time, and probes again when it wakes.",
                    "its completion notice is what restarts the work: a session that ends its turn "
                    "with nothing armed waits until someone types.",
                    "a sub-agent is not restarted by a notice, so it stays in its turn instead "
                    "([runtime hazards](../../agent-delegate/references/runtime-hazards.md)).",
                ),
            ),
            (
                "pattern",
                (
                    "a waiter that watches for a line anchors its pattern to the start of a line, "
                    "and you run the pattern once on the present state and once on a planted "
                    "positive before you rely on it.",
                    "on the present state it must say no and on the planted positive yes: a "
                    "pattern that cannot match waits forever, and one that matches a quoted "
                    "mention of the signal fires at once.",
                ),
            ),
            (
                "clock",
                (
                    "read `date` at every wake-up and before every estimate, and give times to "
                    "others from that reading.",
                    "after a stall the last plan can be hours stale: a session that waited out a "
                    "limit found on waking that the clock had moved about 2.5 hours (observed, "
                    "2026-11-04), and with it its own estimates and the times it had given its "
                    "peers.",
                ),
            ),
            (
                "children",
                (
                    "stopping a task can leave its child processes running, so list the ones you "
                    "started and stop them before you go on.",
                    "an orphaned run keeps loading the machine, and a gate run beside it can fail "
                    "for that reason alone.",
                    "never stop a process a peer started.",
                ),
            ),
        ),
    ),
)
_REFERENCE_CLAIMS = tuple(c for _, claims in _REFERENCE_REGIONS for c in claims)
_REFERENCE_SENTENCES = tuple(s for _, sentences in _REFERENCE_CLAIMS for s in sentences)

# Every figure of the reference, whole, with the tag that says what it rests on. A digit outside
# these and outside a reference to a section is a number nobody labelled.
_FIGURES: tuple[str, ...] = (
    "about 54k tokens of fixed context before it does anything (observed, 2026-11-04)",
    "363k to 479k tokens each over 30 to 37 minutes (observed, 2026-11-04)",
    "about 4 m sub-agent tokens per 5-hour window per account (starting value, uncalibrated)",
    "about 2.5 hours (observed, 2026-11-04)",
)
# "step 4" is the initiative planner's step that derives the cap: a pointer, not a number.
_SECTION_REFERENCE = re.compile(rf"(?:{_SECT}|section|step) \d+[a-z]?\b")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_LINKS = (
    "../SKILL.md",
    "../../agent-delegate/SKILL.md",
    "../../initiative-planner/references/dispatch-economics.md",
    "../../initiative-planner/SKILL.md",
    "../../agent-delegate/assets/worker-preamble.md",
    "../../agent-delegate/references/runtime-hazards.md",
)

_DURABLE_CLAIMS: tuple[Claim, ...] = (
    (
        "lead",
        (
            "durable state.",
            "work held only in a scratch clone or in your context is lost when you are stopped.",
            "keep it where a stop or a cleanup cannot reach it:",
        ),
    ),
    (
        "patch",
        (
            "cut a patch into a git-excluded folder after each verified commit.",
            "a clone can be lost or damaged, and the patch is what the work is rebuilt from.",
        ),
    ),
    (
        "overnight",
        (
            "do no overnight work in a clone under the os temp folder.",
            "the system can empty that folder on a schedule or at a restart, and the clone goes "
            "with it.",
        ),
    ),
    (
        "fsck",
        (
            "run `git fsck` and back up the pack when you make a clone.",
            "objects can go missing from a clone later: the check shows it started whole, and the "
            "backup is what you restore from.",
        ),
    ),
    (
        "basetemp",
        (
            "create and delete a test run's temporary folder (pytest's `--basetemp`) inside one "
            "command.",
            "a delete left for a later step is the one a stopped worker skips, and the folders "
            "left behind fill the disk.",
        ),
    ),
    (
        "disk floor",
        (
            "check free disk space against the floor your brief names before you start a wave.",
            "a full disk stops every agent at once, in the middle of a write.",
        ),
    ),
)
_DURABLE_SENTENCES = tuple(s for _, sentences in _DURABLE_CLAIMS for s in sentences)
_DURABLE_LEADS = tuple(sentences[0] for _, sentences in _DURABLE_CLAIMS)

_CONTEXT_CLAIM: Claim = (
    "context",
    (
        "durable state: <the git-excluded folder that each verified commit's patch is cut into, "
        "and the free-disk floor to check before a wave; section 2 of the worker preamble gives "
        "the other lines>",
    ),
)

_AGENTS_CLAIM: Claim = (
    "agents",
    (
        "pass an explicit `model` on every sub-agent call, because a call that names none "
        "inherits its parent's model, and size a wave in tokens rather than agents before you "
        "start it;",
        "see `references/limit-recovery.md` in the `orchestrate` skill.",
    ),
)

# The id scan. Request-id shapes, absolute home and drive-letter paths, and commit-id-like tokens;
# the path literals are built from parts so that this file does not carry what it bans.
_ID_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a request id", re.compile(r"\b(?:A|C|K|L|O|P|KIT|OQ)-?\d+\b")),
    ("a drive-letter path", re.compile(r"\b[A-Za-z]:[\\/]")),
    ("a macOS home path", re.compile("/" + "Users" + "/")),
    ("a Linux home path", re.compile("/" + "home" + r"/\w")),
    (
        "a commit id",
        re.compile(r"\b(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b"),
    ),
)
# One planted positive per pattern, built at run time for the same reason.
_PLANTS: tuple[tuple[str, str], ...] = (
    ("a request id", "-".join(("KIT", "0"))),
    ("a drive-letter path", "D:" + chr(92) + "work" + chr(92) + "x"),
    ("a macOS home path", "/".join(("", "Users", "someone", ""))),
    ("a Linux home path", "/".join(("", "home", "someone", ""))),
    ("a commit id", "0" * 3 + "abc" + "1" * 2),
)
# Near-misses that must not be reported: the words the reference and the preamble use.
_NEAR_MISSES = (
    "UTF-8",
    "Step 9",
    f"{_SECT} 1b",
    "section 3",
    "a 5-hour window",
    "54K tokens",
    "4 M tokens",
    "a defaced wall",
    "abc123",
    "2026-11-04",
    "https://example.com/x",
)


def _read(path: Path) -> str:
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


def _intro(text: str) -> str:
    """The lines above the first `##` heading."""
    lines = text.split("\n")
    end = next(
        (at for at, line in enumerate(lines) if line.startswith("## ")), len(lines)
    )
    return "\n".join(lines[:end])


def _region(text: str, heading: str) -> str:
    """A region of the reference: its intro for an empty heading, else that section."""
    return _intro(text) if not heading else _section(text, heading)


def _skeleton(text: str) -> str:
    """The lines inside the first ```markdown fence, without the fence lines: the brief skeleton
    the template asks a dispatcher to fill. Empty when there is no such fence."""
    body: list[str] = []
    inside = False
    for line in text.split("\n"):
        if not inside:
            inside = line.startswith("```markdown")
            continue
        if line.strip() == "```":
            return "\n".join(body)
        body.append(line)
    return ""


def _blocks(text: str) -> list[list[str]]:
    """The blocks of `text` outside fenced code: a heading line; a list item, from a line that
    begins with "- " to a blank line or the next item, its other lines indented or in column 0;
    or a paragraph, up to a blank line or the next item. A fenced line and a `---` rule belong to
    no block."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            current = None
            continue
        if in_fence or not line.strip() or _RULE.match(line):
            current = None
            continue
        if _HEADING.match(line):
            blocks.append([line])
            current = None
            continue
        if current is None or line.startswith("- "):
            current = [line]
            blocks.append(current)
        else:
            current.append(line)
    return blocks


def _joined(lines: list[str]) -> str:
    """A block's lines as one text, a list item's "- " dropped."""
    text = "\n".join(lines)
    return text[2:] if text.startswith("- ") else text


def _block_lines(text: str, lead: str) -> list[str]:
    """The lines of the first block whose flat text opens with `lead`; empty when none does."""
    for lines in _blocks(text):
        if _flat(_joined(lines)).startswith(lead):
            return lines
    return []


def _block(text: str, lead: str) -> str:
    """The flat text of the first block that opens with `lead`; empty when none does."""
    lines = _block_lines(text, lead)
    return _flat(_joined(lines)) if lines else ""


def _gaps(flat: str, sentences: tuple[str, ...]) -> list[str]:
    return [sentence for sentence in sentences if sentence not in flat]


def _tail(sentence: str) -> str:
    """The last clause of a sentence: the words after its last comma, colon or semicolon, or its
    last three words when it has none."""
    parts = re.split(r"[,:;] ", sentence)
    return parts[-1] if len(parts) > 1 else " ".join(sentence.split()[-3:])


def _figure_gaps(flat: str) -> list[str]:
    """Each figure that is missing or has lost its tag, and each digit left once the figures and
    the references to a section are taken out: a number nobody labelled."""
    gaps = [
        f"figure missing or untagged: {f!r}" for f in _FIGURES if flat.count(f) != 1
    ]
    rest = flat
    for figure in _FIGURES:
        rest = rest.replace(figure, " ")
    rest = _SECTION_REFERENCE.sub(" ", rest)
    gaps += [f"unlabelled number: {word!r}" for word in re.findall(r"\S*\d\S*", rest)]
    return gaps


def _link_gaps(text: str, base: Path) -> list[str]:
    """Each link target that is not one of the expected ones (`_LINKS`) or does not resolve from
    `base`, and each expected target that is not linked."""
    found = _LINK.findall(text)
    gaps = [
        f"link does not resolve: {t}"
        for t in found
        if not (base / t).resolve().is_file()
    ]
    gaps += [f"unexpected link: {t}" for t in found if t not in _LINKS]
    gaps += [f"not linked: {t}" for t in _LINKS if t not in found]
    return gaps


def _id_hits(text: str) -> list[str]:
    return [f"{name}: {hit!r}" for name, rx in _ID_PATTERNS for hit in rx.findall(text)]


def _reference() -> str:
    assert _REFERENCE.is_file(), f"{_REFERENCE} is not a file"
    text = _read(_REFERENCE)
    assert text.strip(), "limit-recovery.md is empty"
    return text


def _section_2() -> str:
    section = _section(_read(_PREAMBLE), _SECTION_2)
    assert section.strip(), "section 2 is missing from worker-preamble.md"
    return section


def _context() -> str:
    skeleton = _skeleton(_read(_TEMPLATE))
    assert skeleton.strip(), "brief-template.md has no fenced skeleton"
    section = _section(skeleton, _CONTEXT)
    assert section.strip(), "the skeleton has no Context section"
    return section


def _orchestration(path: Path) -> str:
    section = _section(_read(path), _ORCHESTRATION)
    assert section.strip(), f"{path.name} has no {_ORCHESTRATION!r} section"
    return section


def _places() -> list[tuple[str, str, tuple[Claim, ...]]]:
    """Each place, a reference region counted as its own, as (name, its text, its claims)."""
    text = _reference()
    return [
        *(
            (f"reference {heading or 'intro'}", _region(text, heading), claims)
            for heading, claims in _REFERENCE_REGIONS
        ),
        ("preamble section 2", _section_2(), _DURABLE_CLAIMS),
        ("skeleton context", _context(), (_CONTEXT_CLAIM,)),
        *(
            (
                f"{path.name} at {path.parent.name}",
                _orchestration(path),
                (_AGENTS_CLAIM,),
            )
            for path in _AGENTS_FILES
        ),
    ]


def _id_surface() -> list[tuple[str, str]]:
    """The regions the id scan reads, as (name, text): three whole files and two sections."""
    whole = [(path.name, _read(path)) for path in (_REFERENCE, _PREAMBLE, _TEMPLATE)]
    sections = [
        (f"{path.name} at {path.parent.name}", _orchestration(path))
        for path in _AGENTS_FILES
    ]
    return [*whole, *sections]


# --- the surface -------------------------------------------------------------------------------


def test_the_surface_is_stated_in_numbers() -> None:
    assert (len(_REFERENCE_CLAIMS), len(_REFERENCE_SENTENCES)) == (13, 30)
    assert (len(_FIGURES), len(_LINKS)) == (4, 6)
    assert (len(_DURABLE_CLAIMS), len(_DURABLE_SENTENCES)) == (6, 13)
    assert len(_CONTEXT_CLAIM[1]) == 1 and len(_AGENTS_CLAIM[1]) == 2
    every = [
        *_REFERENCE_SENTENCES,
        *_DURABLE_SENTENCES,
        *_CONTEXT_CLAIM[1],
        *_AGENTS_CLAIM[1],
    ]
    assert len(set(every)) == len(every), "a sentence is listed twice"
    for sentence in every:
        others = [other for other in every if other != sentence]
        assert not any(sentence in other for other in others), (
            f"{sentence!r} is part of another sentence"
        )
    files = {_REFERENCE, _PREAMBLE, _TEMPLATE, *_AGENTS_FILES}
    assert len(files) == 5
    assert len(_places()) == 4 + 1 + 1 + 2
    assert (len(_ID_PATTERNS), len(_PLANTS)) == (5, 5)
    assert [name for name, _ in _PLANTS] == [name for name, _ in _ID_PATTERNS]


# --- the reference ------------------------------------------------------------------------------


def test_the_reference_opens_with_when_to_read_it_and_stays_short() -> None:
    """A reference is read whole, so it says first when to read it, under its title, and it holds
    at most 70 lines."""
    text = _reference()
    blocks = _blocks(text)
    assert blocks and blocks[0][0].startswith("# "), "the reference has no title first"
    when = _REFERENCE_REGIONS[0][1][0][1][0]
    assert _flat(_joined(blocks[1])) == when, f"the first paragraph is {blocks[1]!r}"
    lines = text.rstrip("\n").split("\n")
    assert len(lines) <= _REFERENCE_MAX_LINES, (
        f"{len(lines)} lines, over {_REFERENCE_MAX_LINES}"
    )


@pytest.mark.parametrize(
    ("claim", "sentences"), _REFERENCE_CLAIMS, ids=[c[0] for c in _REFERENCE_CLAIMS]
)
def test_the_reference_states_the_claim_in_its_region(
    claim: str, sentences: tuple[str, ...]
) -> None:
    """Red before the change: the reference did not exist."""
    heading = next(
        h for h, claims in _REFERENCE_REGIONS if (claim, sentences) in claims
    )
    region = _region(_reference(), heading)
    assert region.strip(), f"the region {heading or 'intro'!r} is missing"
    block = _block(region, sentences[0])
    assert block, f"no block of {heading or 'the intro'!r} opens with {sentences[0]!r}"
    missing = _gaps(block, sentences)
    assert not missing, f"the {claim!r} block does not state: {missing}"


def test_every_figure_carries_its_tag_and_no_number_goes_unlabelled() -> None:
    """Each figure stands once, whole with its tag; once they and the references to a section are
    taken out, no digit is left."""
    assert _figure_gaps(_flat(_reference())) == []


def test_an_unlabelled_or_untagged_number_is_reported() -> None:
    """Planted: a new number, and a figure whose tag was dropped. Each is reported, and so is a
    figure that went missing, so the check is not blind to either."""
    flat = _flat(_reference())
    assert _figure_gaps(flat) == [], "the reference has a gap at the start"
    planted = _figure_gaps(f"{flat} start about 12 agents at once.")
    assert planted == ["unlabelled number: '12'"], planted
    for figure in _FIGURES:
        bare = figure.split(" (")[0]
        gaps = _figure_gaps(flat.replace(figure, bare))
        assert f"figure missing or untagged: {figure!r}" in gaps, figure
        assert any(g.startswith("unlabelled number") for g in gaps), figure


def test_every_link_resolves_and_names_the_text_it_adds_to() -> None:
    assert _link_gaps(_reference(), _REFERENCE.parent) == []


def test_a_broken_or_missing_link_is_reported() -> None:
    text = _reference()
    assert _link_gaps(text, _REFERENCE.parent) == []
    broken = text.replace(_LINKS[0], "../MISSING.md", 1)
    gaps = _link_gaps(broken, _REFERENCE.parent)
    assert "link does not resolve: ../MISSING.md" in gaps, gaps
    assert f"not linked: {_LINKS[0]}" in gaps, gaps


# --- the preamble, the skeleton and the two AGENTS.md files -------------------------------------


@pytest.mark.parametrize(
    ("claim", "sentences"), _DURABLE_CLAIMS, ids=[c[0] for c in _DURABLE_CLAIMS]
)
def test_section_2_states_the_claim(claim: str, sentences: tuple[str, ...]) -> None:
    """Red before the change: section 2 said nothing on where work survives a stop."""
    block = _block(_section_2(), sentences[0])
    assert block, f"no block of section 2 opens with {sentences[0]!r}"
    missing = _gaps(block, sentences)
    assert not missing, f"the {claim!r} block does not state: {missing}"


def test_the_durable_group_closes_section_2_in_order() -> None:
    """The lead paragraph and the five bullets are one run of blocks in this order, after the
    bullets section 2 had, and each lead opens one block of the whole preamble."""
    flats = [_flat(_joined(lines)) for lines in _blocks(_section_2())]
    order = [
        next((at for at, flat in enumerate(flats) if flat.startswith(lead)), -1)
        for lead in _DURABLE_LEADS
    ]
    assert -1 not in order, f"a block of the group is missing: {order}"
    assert order == list(range(len(flats) - len(order), len(flats))), (
        f"the group is not the last run of blocks of section 2, in order: {order}"
    )
    text = _read(_PREAMBLE)
    for lead in _DURABLE_LEADS:
        openers = [b for b in _blocks(text) if _flat(_joined(b)).startswith(lead)]
        assert len(openers) == 1, f"{len(openers)} blocks open with {lead!r}"


def test_the_skeleton_names_the_durable_state_in_context() -> None:
    """Red before the change: the Context section named no patch folder and no disk floor."""
    sentences = _CONTEXT_CLAIM[1]
    block = _block(_context(), sentences[0])
    assert block, f"no block of the Context section opens with {sentences[0]!r}"
    assert not _gaps(block, sentences)
    assert _flat(_read(_TEMPLATE)).count(sentences[0]) == 1, (
        "the line occurs more than once"
    )


@pytest.mark.parametrize("path", _AGENTS_FILES, ids=["kit", "seeded"])
def test_each_agents_file_states_the_bullet(path: Path) -> None:
    """Red before the change: neither section named a model rule or a wave size."""
    section = _orchestration(path)
    sentences = _AGENTS_CLAIM[1]
    lines = _block_lines(section, sentences[0])
    assert lines, f"{path.name}: no bullet opens with {sentences[0]!r}"
    assert lines[0].startswith("- "), f"{path.name}: the block is not a list item"
    assert len(lines) <= _AGENTS_MAX_LINES, (
        f"{path.name}: the bullet has {len(lines)} lines, more than {_AGENTS_MAX_LINES}"
    )
    assert not _gaps(_block(section, sentences[0]), sentences)


def test_the_two_agents_files_say_the_same_bullet() -> None:
    lead = _AGENTS_CLAIM[1][0]
    kit = _block(_orchestration(_KIT_AGENTS), lead)
    seeded = _block(_orchestration(_SEEDED_AGENTS), lead)
    assert kit, "the kit's AGENTS.md has no model bullet"
    assert kit == seeded, f"the files disagree: {kit!r} versus {seeded!r}"


# --- the checks can fail ------------------------------------------------------------------------


def test_every_sentence_occurs_once_and_is_reported_when_it_goes() -> None:
    """Planted removal: each sentence cut out of its real place is the one gap reported, and an
    empty place lacks every sentence."""
    for name, text, claims in _places():
        sentences = tuple(s for _, group in claims for s in group)
        flat = _flat(text)
        assert _gaps(flat, sentences) == [], (
            f"{name}: a sentence is missing at the start"
        )
        for sentence in sentences:
            assert flat.count(sentence) == 1, (
                f"{name}: {sentence!r} occurs {flat.count(sentence)} times"
            )
            assert _gaps(flat.replace(sentence, ""), sentences) == [sentence], sentence
        assert _gaps("", sentences) == list(sentences)


def test_a_clause_cut_from_its_sentence_is_reported() -> None:
    """Planted clause removal: the last clause of each sentence (after its last comma, colon or
    semicolon, or its last three words) is cut out of the real block, and the claim then reports
    exactly that sentence. A lead of three words or fewer has no clause to cut; the planted
    removal above fires at it, and the count says how many there are."""
    cut = short = 0
    for name, text, claims in _places():
        for claim, sentences in claims:
            block = _block(text, sentences[0])
            assert block, f"{name}: no block opens with {sentences[0]!r}"
            assert not _gaps(block, sentences), f"{name}: {claim}"
            for sentence in sentences:
                tail = _tail(sentence)
                if tail == sentence:
                    assert len(sentence.split()) <= 3, (
                        f"no clause to cut from {sentence!r}"
                    )
                    short += 1
                    continue
                assert block.count(tail) == 1, (
                    f"{tail!r} is not a clause of one sentence"
                )
                assert _gaps(block.replace(tail, ""), sentences) == [sentence], (
                    name,
                    sentence,
                )
                cut += 1
    every = (
        len(_REFERENCE_SENTENCES)
        + len(_DURABLE_SENTENCES)
        + len(_CONTEXT_CLAIM[1])
        + 2 * len(_AGENTS_CLAIM[1])
    )
    assert (cut, short) == (every - 1, 1), (
        f"{cut} cut and {short} short of {every} sentences"
    )


def test_the_durable_claims_are_judged_inside_section_2_only() -> None:
    """Planted move: the group cut out of section 2 and put into section 3 is a section 2 that
    lacks every claim and exactly them, while a search of the whole text still finds them all."""
    blocks = _blocks(_section_2())
    moved = [
        lines for lines in blocks if _flat(_joined(lines)).startswith(_DURABLE_LEADS)
    ]
    kept = [lines for lines in blocks if lines not in moved]
    assert len(moved) == len(_DURABLE_LEADS), "the group to move is not in section 2"
    text = "\n\n".join(
        "\n".join(lines) for lines in [*kept, [f"{_SECTION_3} Elsewhere"], *moved]
    )
    after = _section(text, _SECTION_2)
    assert after.strip(), "the planted text has no section 2"
    for lead in _DURABLE_LEADS:
        assert _block(after, lead) == "", lead
    assert _gaps(_flat(after), _DURABLE_SENTENCES) == list(_DURABLE_SENTENCES)
    assert _gaps(_flat(text), _DURABLE_SENTENCES) == [], (
        "a whole-file search would have passed"
    )


def test_a_reference_claim_is_judged_inside_its_own_section() -> None:
    """Planted move: the explicit-model bullet moved from its section into the next one is a
    section that lacks that claim, while the file as a whole still holds it."""
    text = _reference()
    claim = next(c for c in _REFERENCE_CLAIMS if c[0] == "explicit model")
    heading = "## Size the wave in tokens"
    lines = _block_lines(_section(text, heading), claim[1][0])
    assert lines, "the explicit-model bullet is not in its section"
    moved = text.replace("\n".join(lines) + "\n", "", 1)
    moved = moved.replace(
        "## Probe before you start or resume\n",
        "## Probe before you start or resume\n\n" + "\n".join(lines) + "\n",
        1,
    )
    assert moved != text, "the planted move changed nothing"
    assert _block(_section(moved, heading), claim[1][0]) == ""
    assert _gaps(_flat(moved), claim[1]) == [], "a whole-file search would have passed"


# --- the id scan --------------------------------------------------------------------------------


def test_the_id_scan_reads_its_surface_and_finds_nothing() -> None:
    """THE SURFACE: 3 whole files and 2 sections, disjoint by path, none empty; then no hit. A file
    that is missing fails here and is never read as a clean scan."""
    for path in (_REFERENCE, _PREAMBLE, _TEMPLATE, *_AGENTS_FILES):
        assert path.is_file(), f"cannot scan {path}: not a file"
    whole = {_REFERENCE, _PREAMBLE, _TEMPLATE}
    assert len(whole) == 3 and len(set(_AGENTS_FILES)) == 2
    assert whole.isdisjoint(_AGENTS_FILES), "a file is read whole and by section"
    surface = _id_surface()
    assert len(surface) == 5
    for name, text in surface:
        assert text.strip(), f"{name}: nothing to scan"
    for name, text in surface[3:]:
        assert text.startswith(_ORCHESTRATION), (
            f"{name}: not the section the scan names"
        )
    hits = [f"{name}: {hit}" for name, text in surface for hit in _id_hits(text)]
    assert not hits, hits


def test_every_id_pattern_fires_at_a_plant_in_every_region() -> None:
    """Planted positive: each plant put into each region of the surface is reported, by the
    pattern it was made for and by no other, so a blind pattern cannot pass as a clean region."""
    surface = _id_surface()
    for name, text in surface:
        assert _id_hits(text) == [], f"{name} has a hit before any plant"
        for kind, plant in _PLANTS:
            hits = _id_hits(f"{text}\nPlanted: {plant} here.\n")
            assert len(hits) == 1 and hits[0].startswith(f"{kind}:"), (name, kind, hits)


def test_a_near_miss_is_not_an_id() -> None:
    """The words the texts use for sections, units, dates and links are not reported."""
    for word in _NEAR_MISSES:
        assert _id_hits(f"A line with {word} in it.") == [], word


# --- the finders --------------------------------------------------------------------------------


_DOCUMENT = "\n".join(
    [
        "# Title",
        "",
        "First paragraph.",
        "",
        "## Size",
        "- **A lead.** A body",
        "in column 0.",
        "",
        "```text",
        "## Not a heading",
        "- **A fenced lead.** Not an item.",
        "```",
        "",
        "## Probe",
        "",
        "**A paragraph lead.** Its body.",
        "",
    ]
)


def test_the_finders_keep_their_edges() -> None:
    """The intro stops at the first `##` heading; a section stops at the next one of its level and
    ignores a fenced heading; a block is a paragraph or a list item read whole, fenced lines are no
    block, and an absent lead or heading finds nothing."""
    assert _intro(_DOCUMENT) == "# Title\n\nFirst paragraph.\n"
    size = _section(_DOCUMENT, "## Size")
    assert "a fenced lead" not in _flat("\n".join(_joined(b) for b in _blocks(size)))
    assert "## Probe" not in size and "## Not a heading" in size
    assert _block(size, "a lead.") == "a lead. a body in column 0."
    assert _block(size, "a fenced lead.") == ""
    assert _block(_section(_DOCUMENT, "## Probe"), "a paragraph lead.") == (
        "a paragraph lead. its body."
    )
    assert _region(_DOCUMENT, "") == _intro(_DOCUMENT)
    assert _section(_DOCUMENT, "## Absent") == ""
    assert _block(_DOCUMENT, "an absent lead.") == ""
    assert (
        _skeleton("```markdown\n## Context\n- Budget: x\n```\n")
        == "## Context\n- Budget: x"
    )
    assert _skeleton("no fence") == ""
