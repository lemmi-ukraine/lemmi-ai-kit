"""Every skill name, install target and repository path in the two adopter-facing
documents must resolve to something this repository actually ships.

The pack split's no-regression clause reads: "every install command, path, and skill
name in the README resolves after I4. Budget: zero broken commands." Nothing enforced
it. `test_readme_counts.py` does read README.md, but it checks *how many* skills there
are and is blind to *which*: renaming `spec-driven-dev` leaves the total unchanged,
keeps that test green, and leaves the landing page telling adopters to type a command
that resolves to nothing. The count and the catalog are different claims, and only one
of them was guarded.

WHAT IS GUARDED, AND WHAT IS DELIBERATELY NOT.

**Eight documents, under two rule sets.** `README.md` and `docs/faq.md` get every rule.
The FAQ is in scope because it is adopter-facing in exactly the same way -- it names
`kit-setup` and `commit-message` as things you type, and links relative paths into this
repository -- and because a reader who arrives there instead of the README deserves the
same guarantee.

Six more documents -- `CONTRIBUTING.md`, `docs/adoption-guide.md`,
`docs/working-on-the-kit.md`, `docs/authoring-a-pack.md`, `docs/migrating-from-0.1.0.md`
and `docs/syncing-from-upstream.md` -- get every rule EXCEPT the bare-identifier one.
Invocations, install targets, paths and link fragments are matched by *context*, so they
mean the same thing in a contributor document as in the README. In every one of the six a
bare hyphenated code span means something else, so the identifier rule would raise
findings that are all correct content:

| document | hyphenated identifiers that are not skills |
|---|---|
| `docs/migrating-from-0.1.0.md` | pre-split skill names, quoted *because* they no longer resolve |
| `docs/syncing-from-upstream.md` | upstream skill names this kit deliberately did not port |
| `CONTRIBUTING.md`, `docs/working-on-the-kit.md`, `docs/authoring-a-pack.md` | CLI subcommands (`publish-check`, `audit-skills`, `new-pack`) |
| `docs/adoption-guide.md` | generated-block markers (`project-rules`, `skills-index`) |
| `docs/syncing-from-upstream.md` | also a typo quoted as the finding: "one had a typo corrected (`analyge-logs` -> `analyze-logs`)" |

(No count is given for those findings on purpose. Nothing here would check it, and a
hand-written number is wrong the first time one of those documents is edited.)

The migration document is the sharp case: its subject is names that are gone. A guard
demanding they resolve would flag the record for being accurate, and the obvious way to
silence it would be to delete the migration path.
`test_the_exclusions_still_earn_themselves` asserts that this is still true of it, so
the exclusion keeps earning its place rather than persisting as an opinion someone once
held. The rule holds where the convention holds -- in the two documents where a bare
hyphenated identifier means a skill and nothing else.

**"Only the shape-based rule cannot travel" was measured, and it was false.** Widening
the context-anchored rules to the six raised eight findings, and every one of them was
correct content. Two separate rules were wrong, not two documents:

1. *`marketplace add` does not only take an `owner/repo` shorthand.* Five of the eight
   were `marketplace add .` and `marketplace add ./`, the local-clone form -- which
   `docs/adoption-guide.md` documents as **the only path actually executed end to end**,
   adding that Claude Code rejects a bare `.` and that "the trailing slash is not
   optional -- on one of these clients it is the difference between an install and an
   error". A guard telling a contributor that `./` "does not name this repository" is
   how a working install command gets edited into a broken one. The shorthand rule now
   fires only on a shorthand-shaped argument; a local source is counted and skipped.
2. *The retired plugin id is the migration document's subject, in every rule and not
   just the shape one.* Its Before/After table names `lemmi-ai-kit@lemmi` and
   `/lemmi-ai-kit:<name>` in the *Before* column. The FAQ escaped this by accident --
   it writes `/lemmi-ai-kit:...`, and `...` is not identifier-shaped -- which the note
   below calls the pattern declining to match rather than an exemption. That was luck,
   not design, and it did not survive contact with a document that spells the
   placeholder `<name>`. So the retired id, derived from `pyproject.toml` exactly as it
   already was for the identifier rule, is allowed in the one document whose subject is
   its retirement. `test_the_retired_plugin_id_is_allowed_only_where_it_is_the_subject`
   holds both halves: that the document still names it, and that README.md and
   docs/faq.md are still failed by the same reference.

Neither correction weakens the guard elsewhere: `someone-else/some-other-repo` and
`/lemmi-ai-kit-legacy:kit-setup` are still caught, and both controls still run.

**One illustrative path, and the exemption is derived from the document.**
`docs/authoring-a-pack.md` names `plugins/rust/` and `plugins/rust`, which do not exist
-- it is the worked example, the output of the `new-pack rust --skill rust-conventions`
command in its own step 1, generated "in a throwaway clone" per its own step 3. So the
illustrative pack name is read back out of that document's `new-pack` invocation rather
than written down here: change the example to `swift` and the exemption follows it,
delete the example and the exemption evaporates. It covers `plugins/<that name>/` and
nothing else, so a genuinely dead `plugins/core/...` path in the same file still fails,
which `test_the_illustrative_pack_exemption_is_narrow` asserts directly.

**Inline code spans, not fenced blocks, for the bare-identifier rule.** A whole inline
span that is nothing but a lowercase hyphenated identifier is an unambiguous "this is a
name". A token inside a fence is a shell word, where `some-package` is an argument
rather than a claim, so applying the same rule there would invent findings. The fence is
not unguarded: invocations, install targets and marketplace arguments are matched by
*context* rather than by shape, so they are checked wherever they appear -- fenced,
inline, or in bare prose. That split is the answer to "a guard that only matches inside
code fences will miss a skill named in prose": the strongest form, the one an adopter
actually types, is checked on every surface; the weakest form is checked only where it
can be read unambiguously.

**Three holes, each measured rather than assumed.** `test_the_stated_limits_are_real`
asserts all three, so this prose cannot quietly become false:

1. *An unbackticked prose mention of a skill is invisible.* Nothing distinguishes a
   stale `spec-driven-devv` from ordinary hyphenated English (`language-agnostic`,
   `orchestrator-workers`, `user-invocable`) without a dictionary. Cost today: zero --
   both documents already backtick every skill they name.
2. *A single-token skill name in a bare code span is invisible.* `orchestrate` is
   shape-identical to `git`, `ruff`, `pytest` and `main`, all of which appear as code
   spans in these documents and none of which is a skill. Cost today: exactly one
   skill, and the test asserts *which* one, so a second single-token skill fails here
   and forces this note to be re-read. In invocation form (`/plugin:orchestrate`) it is
   fully checked -- context beats shape.
3. *An invocation that names no skill is not checked.* The FAQ quotes the pre-split
   prefix as `/lemmi-ai-kit:...` while explaining that it stopped working; that is
   correct content, and the pattern declines to match it rather than being exempted.

**Nothing is hand-listed.** The skills come from `load_manifest()`. The identifiers
that are legitimately *not* skills -- the plugin names, and the pre-split plugin id,
which is also the repository and distribution name -- are read from `PACK_PLUGIN_NAMES`
and `pyproject.toml`; the marketplace ids come from the two catalogs. Add or rename a
pack and the exemption follows it. `_non_skill_identifiers()` carries the provenance of
each one into the failure message, so a reader is told *why* a name is allowed rather
than only that it is -- an exemption nobody can audit is how a renamed skill gets
waved through.

**Paths are in scope, for two shapes and no others.** A relative markdown link target
must exist relative to its own document, and must stay inside the repository. A code
span containing a slash whose first segment is a tracked top-level entry of this
repository must exist too -- which is what puts `tests/test_pack_boundaries.py` in the
FAQ under guard. `AGENTS.md`, `CLAUDE.md` and `.ai/learnings.md` are *not* checked and
must never be: they name files in the adopter's repository, not this one, and the
first-segment rule excludes them for free rather than by exemption.

**Link fragments are resolved, by reproducing GitHub's slug algorithm rather than
approximating it.** This was the largest remaining hole: a heading rename in
`docs/adoption-guide.md` silently broke every `#anchor` aimed at it. It was left open
on the grounds that anchor slugging is per-renderer and a subtly wrong implementation
would flag *correct* links -- the right instinct, and the wrong conclusion, because the
algorithm is not a matter of taste. `github-slugger` lowercases, deletes a fixed set of
punctuation, and only then turns each remaining space into a hyphen. That order is the
whole trap: a spaced em dash leaves **two** adjacent spaces behind, which become **two**
hyphens. `## 5. The seam -- where your conventions attach` is `#5-the-seam--where-your-
conventions-attach`, double hyphen intact. Approximating that one case wrong produced
four false positives in one session and two in another, so it is the first assertion in
`test_the_slug_algorithm_reproduces_the_cases_that_produced_false_positives`, alongside
every other heading in the tree that punctuation touches.

`_github_slug` is written as the complement of that deletion set: keep letters, numbers,
marks, `-`, `_` and the space; drop everything else. The real implementation is a
deletion list, so the two agree on every character either has an opinion about and
differ only on exotic codepoints no heading here contains. Repeats are numbered the way
GitHub numbers them -- the second `## Verify` is `#verify-1` -- which is why the fence
rule below is load-bearing rather than tidy.

*Headings are read outside fenced blocks, and that is not a detail.*
`docs/adoption-guide.md` contains five shell comments (`# from a clone of
lemmi-ai-kit`, `# 1. See exactly what would be touched...`) and a `### Project rules`
inside a ```markdown example. Read naively, those mint six extra anchors -- including
three colliding `from-a-clone-of-lemmi-ai-kit`, `-1`, `-2` -- so a link to a heading
that does not exist would resolve against a comment in a code sample and pass.
`test_a_heading_inside_a_fence_is_not_an_anchor` asserts all six stay out and that a
link to one is caught.

*Documented limits, each measured by `test_the_stated_limits_are_real` rather than
asserted in prose.* Setext headings (`===` underlines) are not matched, and no document
uses one. `_heading_plain_text` does not strip `_emphasis_`, and no heading contains an
underscore. A fragment on a non-markdown target (`file.py#L20` is a GitHub line anchor,
not a heading) is counted and skipped, and there are none today. Each of those costs
zero right now, which is only knowable because the test measures it; the day one appears
the limit fails loudly instead of quietly mis-slugging.

*Nothing is trimmed, and that was a finding against this module's own first draft.* It
also registered each slug's stripped spelling, hedging against a `github-slugger`
version that might trim leading hyphens. `### `### Project rules`` slugs to
`-project-rules`, whose trimmed spelling is `project-rules` -- precisely the phantom
anchor the fence filter had just removed. The hedge defended against a link nobody has
written by re-admitting one the filter existed to suppress, and the fence control caught
it on its first run. Reproduce the algorithm; do not hedge it.

**The scan surfaces must not overlap, and that assertion earned its place three times.**
The first draft of `_INLINE_CODE` allowed backticks inside a span, so it matched one
fence marker against the next and reported eight phantom spans in README.md alone --
found on the first run of the overlap check, before any of this was committed. The
second defect was in the check itself: it compared two lists of `re.Match` objects with
`==`, which is identity for matches, so it could never have passed. Both are the reason
`test_the_overlap_check_fires_when_the_regions_do_overlap` exists. An assertion that
cannot fail and an assertion that cannot pass are the same bug wearing different
clothes, and only running a deliberately bad input tells them apart.

The third was found widening the scope, and it is why there are now two forms of the
check. *Zero inline spans inside a fence* is a property of README.md and docs/faq.md,
not of the patterns: `docs/adoption-guide.md` legitimately shows markdown inside a
```markdown fence, backticks and all, so the strict form cannot travel and is asserted
only where it holds. What travels is the real invariant -- **no byte is read by two
rules** -- asserted as `_code_chunks` producing pairwise disjoint spans, on all eight
documents. On adoption-guide.md that check has teeth precisely because there IS
something to filter: turn the filter off and the fence chunk overlaps the two spans
inside it, which is what its control does.
"""

import json
import re
import subprocess
import tomllib
import unicodedata
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

from lemmi_ai_kit.manifest import PACK_PLUGIN_NAMES, SkillEntry, load_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The two documents an adopter reads before installing anything. Every rule applies.
_GUARDED_DOCS: tuple[str, ...] = ("README.md", "docs/faq.md")

# Contributor-facing documents. Every rule EXCEPT the shape-based identifier one, which
# cannot travel: see the table in the module docstring for what a bare hyphenated code
# span means in each of them.
_CONTEXT_GUARDED_DOCS: tuple[str, ...] = (
    "CONTRIBUTING.md",
    "docs/adoption-guide.md",
    "docs/working-on-the-kit.md",
    "docs/authoring-a-pack.md",
    "docs/migrating-from-0.1.0.md",
    "docs/syncing-from-upstream.md",
)

_ALL_SCANNED_DOCS: tuple[str, ...] = _GUARDED_DOCS + _CONTEXT_GUARDED_DOCS

# The rules, named so a document's coverage is a set rather than a pile of booleans.
_IDENTIFIERS = "identifiers"
_INVOCATIONS = "invocations"
_INSTALLS = "installs"
_PATHS = "paths"
_FRAGMENTS = "fragments"

# The tree the kit scaffolds into an ADOPTER's repository. A span under it in an
# adopter-facing document describes their checkout, not this one, so whether it exists
# here is not evidence either way -- and CONTRIBUTING.md's table of banned patterns
# names one such path precisely BECAUSE it must not exist. Kept as a constant so the
# rule is stated once and the reason travels with it.
_ADOPTER_TREE = ".ai"

# Everything except `_IDENTIFIERS` is matched by CONTEXT rather than by shape, which is
# what lets it mean the same thing in a contributor document as on the landing page.
_TRAVELLING_RULES = frozenset({_INVOCATIONS, _INSTALLS, _PATHS, _FRAGMENTS})
_ALL_RULES = _TRAVELLING_RULES | {_IDENTIFIERS}

# The one document whose subject is the retired plugin id. See the module docstring:
# the id itself is derived from pyproject.toml, only the document is named, and
# `test_the_retired_plugin_id_is_allowed_only_where_it_is_the_subject` holds both ends.
_DOCUMENTS_ABOUT_THE_RETIRED_PLUGIN: tuple[str, ...] = ("docs/migrating-from-0.1.0.md",)

# A fenced block, with the closing run required to match the opening one so a nested
# example cannot end the block early.
_FENCE = re.compile(
    r"^(?P<ticks>```+)[^\n]*\n.*?^(?P=ticks)[ \t]*$", re.DOTALL | re.MULTILINE
)

# One inline code span. The content class EXCLUDES backticks on purpose: allowing them
# lets this pattern span from one fence marker to the next. See the docstring.
_INLINE_CODE = re.compile(r"`(?P<content>[^`\n]+)`")

# A whole span that is nothing but a lowercase hyphenated identifier -- the shape of
# every shipped skill directory except `orchestrate`.
_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")

# `/lemmi-ai-kit-core:kit-setup`, anywhere in the document. The lookbehind keeps the
# `/x:y` shape from being found inside a URL; it is one character wide, so it is a
# legal fixed-width lookbehind and stays legal when a pack of a different name is
# added. A `<placeholder>` skill part is matched and then skipped, so a *missing*
# placeholder form does not silently drop out of the scan.
_INVOCATION = re.compile(
    r"(?<![\w./-])/(?P<plugin>[a-z0-9][a-z0-9-]*):"
    r"(?P<skill>[a-z0-9][a-z0-9-]*|<[a-z][a-z-]*>)"
)

# `lemmi-ai-kit-core@lemmi` -- anchored to the whole token, so `support@lemmi.io` and
# `@AGENTS.md` cannot match.
_INSTALL_TARGET = re.compile(
    r"^(?P<plugin>[a-z0-9][a-z0-9-]*)@(?P<marketplace>[a-z0-9][a-z0-9-]*)$"
)

# The argument to `marketplace add`, matched by context. Anchoring on the command is
# what keeps the literal placeholder `owner/repo` -- which the README uses in prose to
# describe this exact argument -- from being read as a real repository.
_MARKETPLACE_ADD = re.compile(r"marketplace\s+add\s+(?P<target>\S+)")

# A markdown link destination.
_LINK_TARGET = re.compile(r"\]\((?P<target>[^)\s]+)\)")

# Shell-ish word splitting, for fence bodies.
_CODE_TOKEN = re.compile(r"[^\s`'\"()\[\],;]+")

# `#` is NOT here: a same-document `](#anchor)` is a relative link whose target file is
# the document itself, and the fragment rule resolves it like any other.
_EXTERNAL_LINK = ("http://", "https://", "mailto:")

# An ATX heading. The optional trailing run of `#` is the closing sequence, which is
# decoration and not part of the text. Setext headings (`===` underlines) are not
# matched; `test_the_stated_limits_are_real` asserts the tree contains none.
_ATX_HEADING = re.compile(
    r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.*?)(?:[ \t]+#+)?[ \t]*$", re.MULTILINE
)

# Markdown inline constructs that render to their text content. Applied before slugging
# so a heading's LINK TEXT and CODE CONTENT are what gets slugged, which is what
# `### If the `owner/repo` shorthand does not resolve` needs to reach
# `#if-the-ownerrepo-shorthand-does-not-resolve` -- backticks gone, then the slash.
_HEADING_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\([^)]*\)")
_HEADING_LINK = re.compile(r"\[(?P<text>[^\]]*)\]\([^)]*\)")

# The argument to `marketplace add` when it is a LOCAL clone rather than a shorthand:
# `.`, `./`, `../somewhere`, an absolute path. Verified working and documented as the
# only end-to-end-executed install path, so the shorthand rule must not govern it.
_LOCAL_MARKETPLACE_SOURCE = re.compile(r"^(?:\.{1,2}$|[.~/]|[A-Za-z]:[\\/])")

# `new-pack <name>`, read back out of a document to learn which pack it invents for the
# sake of the example. Derived, so the exemption follows the example if it is renamed.
_NEW_PACK = re.compile(r"new-pack\s+(?P<name>[a-z][a-z0-9-]*)")

# Characters `github-slugger` keeps that are not letters, numbers or marks. Note the
# SPACE: it survives deletion and is only turned into a hyphen afterwards, which is the
# entire reason a spaced em dash leaves two hyphens behind.
_SLUG_KEPT_PUNCTUATION = frozenset("-_ ")

# References that carried real risk and must not drop out of the scan in silence.
#
# These are used twice, and the second use is the one that matters.
# `test_the_scan_surface_is_what_it_claims` asserts each was EXAMINED -- a rule that
# stopped matching returns an empty problem list, which is indistinguishable from a
# clean document. `test_every_reference_that_must_be_checked_is_actually_held` then
# perturbs each one *in the real document* and requires a finding, which is the only
# evidence that the README itself is held rather than a synthetic string that resembles
# it. One entry per rule, so no rule can rot unobserved.
_MUST_BE_CHECKED: tuple[tuple[str, str], ...] = (
    # The charter's own example: a skill name inside a fenced install command.
    ("README.md", "/lemmi-ai-kit-core:kit-setup"),
    # A skill named in a prose table, which a fence-only guard would miss entirely.
    ("README.md", "spec-driven-dev"),
    ("README.md", "lemmi-ai-kit-core@lemmi"),
    ("README.md", "docs/adoption-guide.md"),
    ("docs/faq.md", "commit-message"),
    # A path into this repository, named from a document one directory down.
    ("docs/faq.md", "tests/test_pack_boundaries.py"),
    ("docs/faq.md", "../SECURITY.md"),
    # The fragment that produced four false positives in one session and two in
    # another: a spaced em dash leaves TWO hyphens behind. Held in the real README.
    ("README.md", "docs/adoption-guide.md#5-the-seam--where-your-conventions-attach"),
    ("docs/faq.md", "adoption-guide.md#what-is-not-built-yet-and-what-is-not-verified"),
    # A fragment into a document that is not itself scanned -- the target's headings
    # are read wherever it lives, which is what makes SECURITY.md's anchors held.
    ("CONTRIBUTING.md", "SECURITY.md#threat-model--read-this-part"),
    # A same-document fragment, resolved against the document's own headings.
    ("docs/adoption-guide.md", "#4-set-up-a-project"),
    # The two travelling rules, in newly guarded documents. Without these the widening
    # could silently buy nothing and every problem list would still be empty.
    ("docs/adoption-guide.md", "/lemmi-ai-kit-core:kit-setup"),
    ("docs/adoption-guide.md", "lemmi-ai-kit-python@lemmi"),
    ("docs/migrating-from-0.1.0.md", "lemmi-ai-kit-core@lemmi"),
    # A relative path from a contributor document, one directory down.
    ("docs/authoring-a-pack.md", "../CONTRIBUTING.md#contributing-a-pack"),
)


def _line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _heading_plain_text(inline: str) -> str:
    """The rendered text of a heading -- what GitHub actually slugs.

    Images become their alt text, links become their link text, and inline code becomes
    its content. Emphasis markers need no handling: `*` is deleted by the slug rule
    whether it is markup or not, and `_` is the one that would differ -- which is why
    `test_the_stated_limits_are_real` asserts no heading in the tree contains one.
    """
    out = _HEADING_IMAGE.sub(lambda match: match.group("alt"), inline)
    out = _HEADING_LINK.sub(lambda match: match.group("text"), out)
    return out.replace("`", "")


def _github_slug(text: str) -> str:
    """Reproduce `github-slugger`: lowercase, delete punctuation, THEN space -> hyphen.

    Written as the complement of the real deletion list -- keep letters, numbers, marks
    and `-_ `, drop the rest. The two agree on every character either has an opinion
    about. Doing the deletion BEFORE the space substitution is not a stylistic choice:
    it is what leaves a spaced em dash as two adjacent spaces and therefore two hyphens.
    """
    lowered = text.lower()
    kept = "".join(
        character
        for character in lowered
        if character in _SLUG_KEPT_PUNCTUATION
        or unicodedata.category(character)[0] in "LNM"
    )
    return kept.replace(" ", "-")


def _headings(text: str) -> list[re.Match[str]]:
    """Every ATX heading OUTSIDE a fenced block.

    The fence filter is the load-bearing half. A shell comment in a `sh` fence and a
    heading in a `markdown` example are both `^#+ ` and neither is an anchor; counting
    them mints anchors that GitHub never generates, and a dead link then resolves
    against one. See `test_a_heading_inside_a_fence_is_not_an_anchor`.
    """
    fences = _fence_regions(text)
    return [
        match
        for match in _ATX_HEADING.finditer(text)
        if not any(start <= match.start() < end for start, end in fences)
    ]


def _anchors_in(text: str) -> dict[str, str]:
    """Slug -> heading text, for one document, numbered the way GitHub numbers repeats.

    A repeated slug gets `-1`, `-2` appended, so the SECOND `## Verify` is `#verify-1`.

    Nothing is trimmed. An earlier draft also registered each slug's stripped spelling,
    as a hedge against `github-slugger` trimming leading hyphens in some version this
    cannot check offline -- and `test_a_heading_inside_a_fence_is_not_an_anchor` caught
    it immediately: `### `### Project rules`` slugs to `-project-rules`, whose trimmed
    spelling is `project-rules`, which is exactly the phantom anchor the fence filter
    exists to suppress. The hedge defended against a link nobody has written and
    re-admitted one the filter had just removed, so it is gone. Reproduce the
    algorithm; do not hedge it.
    """
    occurrences: dict[str, int] = {}
    anchors: dict[str, str] = {}
    for match in _headings(text):
        heading = match.group("text")
        base = _github_slug(_heading_plain_text(heading))
        seen = occurrences.get(base, 0)
        occurrences[base] = seen + 1
        anchors.setdefault(base if seen == 0 else f"{base}-{seen}", heading)
    return anchors


@cache
def _anchors_of_file(path: Path) -> tuple[str, ...]:
    return tuple(_anchors_in(path.read_text(encoding="utf-8")))


@cache
def _skills() -> dict[str, SkillEntry]:
    return {skill.name: skill for skill in load_manifest().skills}


@cache
def _project_metadata() -> dict[str, Any]:
    raw = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return cast(dict[str, Any], tomllib.loads(raw)["project"])


@cache
def _marketplace_ids() -> frozenset[str]:
    """The marketplace id each catalog publishes -- the `@lemmi` half of a target."""
    catalogs = (
        ".claude-plugin/marketplace.json",
        ".agents/plugins/marketplace.json",
    )
    ids: set[str] = set()
    for relative in catalogs:
        path = _REPO_ROOT / relative
        if path.is_file():
            data: Any = json.loads(path.read_text(encoding="utf-8"))
            ids.add(cast(str, data["name"]))
    return frozenset(ids)


@cache
def _repository_shorthand() -> str:
    """`owner/repo`, from the Repository URL the package already declares."""
    url = cast(str, _project_metadata()["urls"]["Repository"])
    return "/".join(url.rstrip("/").split("/")[-2:])


@cache
def _non_skill_identifiers() -> dict[str, str]:
    """Hyphenated identifiers that are legitimately not skills, and where each is from.

    All of them are derived. The pre-split plugin id is the distribution name, which is
    also the repository name and the second half of the `owner/repo` shorthand -- one
    string with three jobs, which is precisely why the README says it so often.
    """
    reasons: dict[str, str] = {}
    for name in PACK_PLUGIN_NAMES.values():
        reasons[name] = "a plugin name (lemmi_ai_kit.manifest.PACK_PLUGIN_NAMES)"
    for marketplace in _marketplace_ids():
        reasons.setdefault(marketplace, "a marketplace id (marketplace.json)")
    reasons.setdefault(
        cast(str, _project_metadata()["name"]),
        "the repository and distribution name, and the pre-split plugin id "
        "(pyproject.toml [project].name)",
    )
    return reasons


@cache
def _tracked_top_level() -> frozenset[str]:
    """Top-level entries git tracks -- the first segment of any path into this repo."""
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=_REPO_ROOT, capture_output=True, check=True
    )
    entries = frozenset(
        raw.split("/")[0] for raw in result.stdout.decode("utf-8").split("\0") if raw
    )
    assert len(entries) > 5, (
        f"git listed only {len(entries)} top-level entries, so the path rule is close "
        "to vacuous -- the enumeration is broken, not the repository"
    )
    return entries


def _illustrative_pack_paths(text: str) -> frozenset[str]:
    """`plugins/<pack>` for each pack a document tells you to GENERATE, not to ship.

    `docs/authoring-a-pack.md` step 1 is `new-pack rust --skill rust-conventions`, and
    its step 3 records the measurement as made "by generating `plugins/rust` and
    registering it in a throwaway clone". So `plugins/rust` is the worked example's
    output and is *correctly* absent from this tree; the whole subtree is fictional, and
    nothing under it could be verified even in principle.

    Read back out of the document's own command rather than written down: rename the
    example to `swift` and the exemption follows, delete the example and the exemption
    evaporates. Packs that really ship are excluded from it, so a document containing
    `new-pack core` could never launder a genuinely dead `plugins/core/...` path.
    """
    real = frozenset(PACK_PLUGIN_NAMES)
    return frozenset(
        f"plugins/{match.group('name')}"
        for match in _NEW_PACK.finditer(text)
        if match.group("name") not in real
    )


def _fence_regions(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in _FENCE.finditer(text)]


def _inline_code(text: str) -> list[re.Match[str]]:
    """Every inline-span match, unfiltered -- the input to the disjointness check."""
    return list(_INLINE_CODE.finditer(text))


def _inline_outside_fences(text: str) -> list[re.Match[str]]:
    inside = {match.span() for match in _inline_code_inside_fences(text)}
    return [match for match in _inline_code(text) if match.span() not in inside]


def _inline_code_inside_fences(text: str) -> list[re.Match[str]]:
    """Inline spans that land inside a fenced block -- which must always be none.

    The two region scans partition the document, so a match here means the same bytes
    are being read under two different rules. Returned rather than asserted so the
    surface test can report the offenders and the control can prove the check fires.
    Compared by span, not by identity: two `finditer` passes over the same text yield
    equal-looking `re.Match` objects that are never `==`, which is a comparison that
    fails open in one direction and shut in the other.
    """
    fences = _fence_regions(text)
    return [
        match
        for match in _inline_code(text)
        if any(start <= match.start() < end for start, end in fences)
    ]


def _code_chunks(
    text: str, *, drop_fenced_inline: bool = True
) -> list[tuple[int, str]]:
    """Every code-formatted region as `(offset, text)`: fence bodies and inline spans.

    `drop_fenced_inline=False` is the deliberately broken input for
    `test_the_chunk_scans_are_disjoint_and_the_check_can_fail`: it restores the state
    where an inline span inside a fence is ALSO read as its own chunk, so the same
    bytes go through two rules. Nothing in production passes it.
    """
    inline = (
        _inline_code(text) if not drop_fenced_inline else _inline_outside_fences(text)
    )
    chunks = [(match.start(), match.group(0)) for match in _FENCE.finditer(text)]
    chunks += [(match.start("content"), match.group("content")) for match in inline]
    return sorted(chunks)


def _overlapping_chunks(chunks: list[tuple[int, str]]) -> list[tuple[str, str]]:
    """Pairs of code chunks whose byte ranges intersect -- which must always be none.

    This is the invariant the strict inline-inside-a-fence check was reaching for, in
    the form that survives a document legitimately showing markdown inside a
    ```markdown fence. `_code_chunks` is sorted by offset, so comparing each chunk to
    the previous one is enough to find any intersection.
    """
    spans = [(start, start + len(body), body) for start, body in chunks]
    return [
        (previous_body, body)
        for (_, previous_end, previous_body), (start, _, body) in zip(
            spans, spans[1:], strict=False
        )
        if start < previous_end
    ]


@dataclass(frozen=True)
class _Scan:
    """What one document was examined for, and what came back wrong.

    `checked` is the scan surface and is asserted directly, because a rule that
    silently stops matching produces an empty problem list -- the same result as a
    clean document. Printing what was looked at is the only thing that tells the two
    apart.
    """

    identifiers: tuple[str, ...]
    invocations: tuple[str, ...]
    install_targets: tuple[str, ...]
    repo_paths: tuple[str, ...]
    fragments: tuple[str, ...]
    skill_problems: tuple[str, ...]
    install_problems: tuple[str, ...]
    path_problems: tuple[str, ...]
    fragment_problems: tuple[str, ...]

    @property
    def checked(self) -> tuple[str, ...]:
        return (
            *self.identifiers,
            *self.invocations,
            *self.install_targets,
            *self.repo_paths,
            *self.fragments,
        )

    @property
    def problems(self) -> tuple[str, ...]:
        return (
            *self.skill_problems,
            *self.install_problems,
            *self.path_problems,
            *self.fragment_problems,
        )


def _rules_for(relative: str) -> frozenset[str]:
    """Which rules govern one document. Anything unlisted gets all of them.

    The default matters: every synthetic control names a document that is not in
    `_CONTEXT_GUARDED_DOCS`, so it exercises the full rule set without saying so.
    """
    if relative in _CONTEXT_GUARDED_DOCS:
        return _TRAVELLING_RULES
    return _ALL_RULES


def _scan(relative: str, text: str, *, rules: frozenset[str] | None = None) -> _Scan:
    """Apply the rules governing `relative` to one document.

    Pure over `(relative, text)` so the controls can run the real rules against a
    synthetic document rather than a re-implementation of them. `rules` overrides the
    per-document set, which is how a control exercises one rule in isolation.
    """
    active = _rules_for(relative) if rules is None else rules
    skills = _skills()
    exempt = _non_skill_identifiers()
    plugins = frozenset(PACK_PLUGIN_NAMES.values())
    base = (_REPO_ROOT / relative).parent
    retired = cast(str, _project_metadata()["name"])
    retirement_is_the_subject = relative in _DOCUMENTS_ABOUT_THE_RETIRED_PLUGIN
    illustrative = _illustrative_pack_paths(text)

    identifiers: list[str] = []
    invocations: list[str] = []
    install_targets: list[str] = []
    repo_paths: list[str] = []
    fragments: list[str] = []
    skill_problems: list[str] = []
    install_problems: list[str] = []
    path_problems: list[str] = []
    fragment_problems: list[str] = []

    def where(position: int) -> str:
        return f"{relative}:{_line_of(text, position)}"

    # -- skill names, shape-matched, in whole inline code spans -------------------
    for match in _inline_outside_fences(text):
        content = match.group("content")
        if _IDENTIFIERS not in active or not _IDENTIFIER.match(content):
            continue
        identifiers.append(content)
        if content in skills or content in exempt:
            continue
        recognised = "; ".join(
            f"{name} ({reason})" for name, reason in sorted(exempt.items())
        )
        skill_problems.append(
            f"{where(match.start())}: `{content}` is written the way this document "
            "writes a skill name, but no skill by that name ships. Rename it to a "
            "skill in the manifest, or -- if it is not a skill at all -- note that the "
            f"only non-skill identifiers recognised here are {recognised}, every one "
            "of them derived rather than listed. Do not add an exemption for a skill "
            "that was renamed; fix the reference."
        )

    # -- skill names, context-matched, on every surface ---------------------------
    for match in _INVOCATION.finditer(text):
        if _INVOCATIONS not in active:
            continue
        plugin, name = match.group("plugin"), match.group("skill")
        invocations.append(match.group(0))
        if plugin == retired and retirement_is_the_subject:
            # The Before column of a migration table. The id is derived from
            # pyproject.toml; only the document is named. Elsewhere this still fails.
            continue
        if plugin not in plugins:
            install_problems.append(
                f"{where(match.start())}: {match.group(0)!r} is typed at a plugin this "
                f"repository does not publish. The packs are "
                f"{', '.join(sorted(plugins))}."
            )
            continue
        if name.startswith("<"):
            continue
        entry = skills.get(name)
        if entry is None:
            skill_problems.append(
                f"{where(match.start())}: {match.group(0)!r} names no skill in the "
                "manifest, so an adopter typing it gets nothing."
            )
        elif entry.plugin_name != plugin:
            skill_problems.append(
                f"{where(match.start())}: {match.group(0)!r} is wrong about the pack -- "
                f"{name!r} ships in {entry.plugin_name}, so the command resolves only "
                "for someone who installed that pack, under that prefix."
            )
        elif entry.invocation != "user":
            skill_problems.append(
                f"{where(match.start())}: {match.group(0)!r} names a skill whose "
                f"invocation is {entry.invocation!r}. It never appears in the `/` menu, "
                "so this is a command nobody can type."
            )

    # -- install targets and the marketplace argument -----------------------------
    scanned_chunks: list[tuple[int, str]] = (
        _code_chunks(text) if _INSTALLS in active else []
    )
    for offset, chunk in scanned_chunks:
        for token in _CODE_TOKEN.finditer(chunk):
            target = _INSTALL_TARGET.match(token.group(0))
            if target is None:
                continue
            install_targets.append(token.group(0))
            plugin, marketplace = target.group("plugin"), target.group("marketplace")
            # "Before: `lemmi-ai-kit@lemmi`" -- the thing you are migrating OFF. Only
            # the PLUGIN half is excused. An earlier draft skipped the whole token and
            # a mutation sweep caught it at once: `lemmi-ai-kit@not-a-marketplace` sailed
            # through, because a `continue` here also skips the marketplace check below.
            retired_here = plugin == retired and retirement_is_the_subject
            if plugin not in plugins and not retired_here:
                install_problems.append(
                    f"{where(offset)}: `{token.group(0)}` installs {plugin!r}, which is "
                    f"not a plugin this repository publishes "
                    f"({', '.join(sorted(plugins))})."
                )
            if marketplace not in _marketplace_ids():
                install_problems.append(
                    f"{where(offset)}: `{token.group(0)}` installs from marketplace "
                    f"{marketplace!r}; the catalogs publish "
                    f"{', '.join(sorted(_marketplace_ids()))}."
                )
        for add in _MARKETPLACE_ADD.finditer(chunk):
            argument = add.group("target")
            install_targets.append(argument)
            if _LOCAL_MARKETPLACE_SOURCE.match(argument):
                # A local clone, not a shorthand. `./` is the form the only end-to-end
                # verified install actually used, and this client rejects a bare `.`;
                # demanding `owner/repo` here would call a working command broken.
                continue
            if argument != _repository_shorthand():
                install_problems.append(
                    f"{where(offset)}: `marketplace add {argument}` does not "
                    f"name this repository, which is {_repository_shorthand()!r} "
                    "according to pyproject.toml's Repository URL."
                )

    # -- paths and fragments: link destinations, then repository paths as code ----
    for match in _LINK_TARGET.finditer(text):
        target_path = match.group("target")
        if target_path.startswith(_EXTERNAL_LINK):
            continue
        path_part, _, fragment = target_path.partition("#")
        if not path_part and not fragment:
            continue

        resolved = (base / path_part).resolve() if path_part else _REPO_ROOT / relative
        if path_part and _PATHS in active:
            repo_paths.append(target_path)
            if not resolved.is_relative_to(_REPO_ROOT):
                path_problems.append(
                    f"{where(match.start())}: the link to {target_path!r} escapes the "
                    "repository."
                )
                continue
            if not resolved.exists():
                path_problems.append(
                    f"{where(match.start())}: the link to {target_path!r} resolves to "
                    "nothing."
                )
                continue

        if not fragment or _FRAGMENTS not in active:
            continue
        if not resolved.is_file() or not resolved.is_relative_to(_REPO_ROOT):
            continue
        fragments.append(target_path)
        if resolved.suffix != ".md":
            # `file.py#L20` is a GitHub line anchor, not a heading. Counted above so
            # this skip stays visible; the limits test asserts there are none today.
            continue
        # The document under scan may be a MUTATED copy, so a same-file fragment must
        # resolve against `text` rather than against what is still on disk -- or the
        # control that breaks a link in memory would silently check the clean file.
        known = (
            _anchors_in(text)
            if resolved == (_REPO_ROOT / relative).resolve()
            else _anchors_of_file(resolved)
        )
        if fragment not in known:
            near = ", ".join(sorted(known)[:4]) or "none -- the target has no headings"
            fragment_problems.append(
                f"{where(match.start())}: the link to {target_path!r} points at "
                f"`#{fragment}`, which is not a heading in "
                f"{resolved.relative_to(_REPO_ROOT).as_posix()}. A heading was renamed "
                "and the anchor was not, so this link lands at the top of the page "
                f"instead of the section it names. Anchors there begin: {near}. "
                "Fix the link -- the slug is GitHub's, not a choice."
            )

    for match in _inline_outside_fences(text):
        content = match.group("content")
        if _PATHS not in active:
            continue
        if "/" not in content or content.split("/")[0] not in _tracked_top_level():
            continue
        if any(character in content for character in "<>*? "):
            continue
        repo_paths.append(content)
        bare = content.rstrip("/")
        if any(bare == pack or bare.startswith(f"{pack}/") for pack in illustrative):
            # The worked example this very document tells you to generate. Derived
            # from its own `new-pack` line, so a real dead path here still fails.
            continue
        if bare == _ADOPTER_TREE or bare.startswith(f"{_ADOPTER_TREE}/"):
            # A span under the adopter tree names a path in the ADOPTER's repository,
            # so whether it exists *here* says nothing. This test's own failure message
            # has always asserted that; until 2026-08-24 nothing implemented it, and it
            # held only because that directory did not exist in this checkout -- the
            # guard was gated on an accident. Running the kit's scaffold on the kit
            # (I3 DoD 11) tracked it, `_tracked_top_level()` began admitting it, and
            # CONTRIBUTING.md's row from its table of BANNED patterns -- a path that
            # must never exist -- started reading as a dead path claim.
            continue
        if not (_REPO_ROOT / content.rstrip("/")).exists():
            path_problems.append(
                f"{where(match.start())}: `{content}` names a path in this repository "
                "that does not exist."
            )

    return _Scan(
        identifiers=tuple(identifiers),
        invocations=tuple(invocations),
        install_targets=tuple(install_targets),
        repo_paths=tuple(repo_paths),
        fragments=tuple(fragments),
        skill_problems=tuple(skill_problems),
        install_problems=tuple(install_problems),
        path_problems=tuple(path_problems),
        fragment_problems=tuple(fragment_problems),
    )


def _scan_guarded_docs() -> dict[str, _Scan]:
    """Every scanned document, each under the rule set that governs it."""
    return {
        relative: _scan(relative, (_REPO_ROOT / relative).read_text(encoding="utf-8"))
        for relative in _ALL_SCANNED_DOCS
    }


def test_every_skill_name_in_the_guarded_docs_resolves_to_the_manifest() -> None:
    """The charter's clause: no document may name a skill that does not ship."""
    problems = [
        problem
        for scan in _scan_guarded_docs().values()
        for problem in scan.skill_problems
    ]
    assert not problems, (
        "skill names in adopter-facing documents that resolve to nothing:\n"
        + "\n".join(problems)
        + "\n\nThe manifest is the authority. Fix the document -- do not add the name "
        "to an exemption, which would restore exactly the silence this test exists to "
        "end."
    )


def test_every_install_target_in_the_guarded_docs_is_published() -> None:
    """The install commands themselves: plugin, marketplace and repository shorthand."""
    problems = [
        problem
        for scan in _scan_guarded_docs().values()
        for problem in scan.install_problems
    ]
    assert not problems, (
        "install commands that do not resolve to anything this repository publishes:\n"
        + "\n".join(problems)
    )


def test_every_repository_path_in_the_guarded_docs_exists() -> None:
    """Link destinations and repository-relative code spans, resolved on disk."""
    problems = [
        problem
        for scan in _scan_guarded_docs().values()
        for problem in scan.path_problems
    ]
    assert not problems, (
        "paths named in adopter-facing documents that do not exist:\n"
        + "\n".join(problems)
        + "\n\nPaths in the ADOPTER's repository (AGENTS.md, .ai/learnings.md) are out "
        "of scope by construction, and must never be made to pass by creating a file "
        "here."
    )


def test_every_link_fragment_in_the_guarded_docs_resolves_to_a_heading() -> None:
    """`docs/adoption-guide.md#5-the-seam--...` must land on a heading, not the top."""
    problems = [
        problem
        for scan in _scan_guarded_docs().values()
        for problem in scan.fragment_problems
    ]
    assert not problems, (
        "links whose #anchor names no heading in the document they point at:\n"
        + "\n".join(problems)
        + "\n\nA browser does not error on these -- it drops the reader at the top of "
        "the page -- so the only way this is ever noticed is here. The anchor follows "
        "the heading: fix the link, or rename the heading back."
    )


def test_the_scan_surface_is_what_it_claims() -> None:
    """State the coverage in numbers, and assert the scan surfaces stay disjoint.

    Floors rather than exact totals: other sessions own these documents, and a new
    paragraph is not a defect. What must not change silently is the *kind* of thing
    seen, so `_MUST_BE_CHECKED` names references that carried real risk and asserts
    each was examined.
    """
    scans = _scan_guarded_docs()
    assert len(_GUARDED_DOCS) == 2 and len(_CONTEXT_GUARDED_DOCS) == 6, (
        "the scanned set is no longer the two adopter-facing documents plus the six "
        "contributor-facing ones this module claims to cover"
    )
    assert set(scans) == set(_ALL_SCANNED_DOCS) and len(scans) == 8, (
        f"eight documents are claimed and {len(scans)} were scanned"
    )
    assert not set(_GUARDED_DOCS) & set(_CONTEXT_GUARDED_DOCS), (
        "a document is in both rule sets, so its coverage depends on dict ordering"
    )
    for relative in _ALL_SCANNED_DOCS:
        assert (_REPO_ROOT / relative).is_file(), (
            f"{relative} is scanned but does not exist, so its rules are vacuous"
        )

    # The real invariant, on all eight: no byte is read by two rules. This form
    # survives `docs/adoption-guide.md` legitimately showing markdown inside a
    # ```markdown fence, which the stricter form below does not.
    for relative in _ALL_SCANNED_DOCS:
        text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
        collisions = _overlapping_chunks(_code_chunks(text))
        assert not collisions, (
            f"{relative}: two code chunks overlap, so the same bytes go through the "
            f"install rule twice: {collisions}\n\nThe usual cause is the inline-span "
            "filter no longer dropping spans that sit inside a fenced block."
        )
        headings_in_fences = [
            f"{relative}:{_line_of(text, match.start())}: {match.group(0)!r}"
            for match in _ATX_HEADING.finditer(text)
            if any(start <= match.start() < end for start, end in _fence_regions(text))
        ]
        assert set(headings_in_fences).isdisjoint(
            f"{relative}:{_line_of(text, match.start())}: {match.group(0)!r}"
            for match in _headings(text)
        ), f"{relative}: a heading inside a fence is being minted as an anchor"

    # The stricter form, only where it holds. See the module docstring: this is a
    # property of these two documents, not of the patterns, and it does not travel.
    for relative in _GUARDED_DOCS:
        text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
        overlapping = [
            f"{relative}:{_line_of(text, match.start())}: {match.group(0)!r}"
            for match in _inline_code_inside_fences(text)
        ]
        assert not overlapping, (
            f"{relative}: an inline code span was matched INSIDE a fenced block, so "
            "the two region scans overlap and the same bytes are read under two "
            "different rules:\n" + "\n".join(overlapping) + "\n\nThe usual cause is an "
            "inline pattern that permits a backtick in its content and therefore spans "
            "from one fence marker to the next."
        )

    totals = {
        "identifiers": sum(len(scan.identifiers) for scan in scans.values()),
        "invocations": sum(len(scan.invocations) for scan in scans.values()),
        "targets": sum(len(scan.install_targets) for scan in scans.values()),
        "paths": sum(len(scan.repo_paths) for scan in scans.values()),
        "fragments": sum(len(scan.fragments) for scan in scans.values()),
        "anchors": sum(
            len(_anchors_of_file((_REPO_ROOT / relative).resolve()))
            for relative in _ALL_SCANNED_DOCS
        ),
    }
    report = "scan surface: " + ", ".join(
        f"{kind}={count}" for kind, count in sorted(totals.items())
    )
    # Floors at roughly four fifths of what is there today (17, 16, 30, 122, 47, 116),
    # so an edit has room and a rule that stops matching does not.
    assert totals["identifiers"] >= 14, report
    assert totals["invocations"] >= 12, report
    assert totals["targets"] >= 24, report
    assert totals["paths"] >= 95, report
    assert totals["fragments"] >= 38, report
    assert totals["anchors"] >= 95, report

    # The identifier rule must NOT have travelled. Measured, not asserted in prose:
    # the six raise 40-odd shape findings, every one of them correct content.
    assert all(not scans[relative].identifiers for relative in _CONTEXT_GUARDED_DOCS), (
        "the bare-identifier rule reached a contributor document. In every one of them "
        "a lowercase hyphenated code span is a CLI subcommand, a marker name, a retired "
        "name or a quoted typo -- see the table in the module docstring."
    )
    for relative in _CONTEXT_GUARDED_DOCS:
        assert scans[relative].checked, (
            f"{relative} is in the scanned set but nothing in it was examined, so "
            "adding it bought no coverage at all"
        )

    shipped = set(_skills())
    covered = {
        identifier
        for scan in scans.values()
        for identifier in scan.identifiers
        if identifier in shipped
    }
    assert len(covered) >= 8, (
        f"only {len(covered)} of {len(shipped)} shipped skills are named in the "
        f"guarded documents at all ({report}) -- if these documents stopped naming "
        "skills, this guard is close to vacuous and the drift it exists to catch has "
        "nowhere to land"
    )

    for relative, reference in _MUST_BE_CHECKED:
        assert reference in scans[relative].checked, (
            f"{relative} no longer has {reference!r} in the examined set. It is listed "
            "because it carried real risk; a rule that stopped matching it returns an "
            "empty problem list, which is indistinguishable from a clean document."
        )


def test_every_reference_that_must_be_checked_is_actually_held() -> None:
    """Positive control against the real documents, not a synthetic stand-in.

    A control built only from invented text proves the rules work on invented text. It
    would still pass if `_GUARDED_DOCS` pointed at the wrong file, if the README were
    read with the wrong encoding, or if a reference sat in a region the extraction
    silently drops. So each entry in `_MUST_BE_CHECKED` is perturbed inside the
    document that actually ships, and must produce a finding that names the damage.

    Appending one character is enough: it breaks resolution while leaving the shape
    intact, which isolates the resolve check from the matcher. The unmutated document
    is asserted clean first, so a pre-existing failure cannot be mistaken for the
    mutation being caught.
    """
    for relative, reference in _MUST_BE_CHECKED:
        text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
        assert reference in text, (
            f"{relative} no longer contains {reference!r}, so this control is testing "
            "nothing. Point it at whatever replaced the reference, or drop the entry "
            "-- do not leave it here looking like coverage."
        )
        assert not _scan(relative, text).problems, (
            f"{relative} already fails before any mutation, so this control cannot "
            "attribute a finding to the mutation"
        )

        damaged = reference + "x"
        found = _scan(relative, text.replace(reference, damaged)).problems
        assert any(damaged in problem for problem in found), (
            f"{relative}: breaking {reference!r} into {damaged!r} produced no finding "
            f"that names it (findings: {list(found)}). The reference is in the "
            "document and in the examined set, but nothing is checking that it "
            "resolves -- which is precisely the state this module exists to end."
        )


def test_the_overlap_check_fires_when_the_regions_do_overlap() -> None:
    """Positive control for the disjointness check above.

    A fence body containing a lone backtick is the case that makes an inline pattern
    run away into it. Both documents happen to be clean today, so without this the
    overlap assertion would be an untested claim that the region scans partition the
    text -- and it has already been wrong twice.
    """
    runaway = "\n".join(("```sh", "echo `date`", "```", "", "and `kit-setup` after."))
    inside = _inline_code_inside_fences(runaway)
    assert [match.group(0) for match in inside] == ["`date`"], (
        "the overlap check no longer sees an inline span inside a fenced block, so "
        "the assertion in the surface test can no longer fail and has stopped being "
        "evidence of anything"
    )
    assert [match.group("content") for match in _inline_outside_fences(runaway)] == [
        "kit-setup"
    ], "the span outside the fence must survive; the filter must not eat everything"


def test_the_guard_catches_a_broken_reference_of_every_kind() -> None:
    """Positive control. A guard never shown to fail has not been shown to work.

    Every case runs the real `_scan`, not a re-implementation, over a synthetic
    document resolved from the repository root -- so `docs/faq.md` genuinely exists and
    `docs/no-such-page.md` genuinely does not.
    """
    bad = _scan(
        "README.md",
        "\n".join(
            (
                "A renamed skill: `spec-driven-devv` should not survive.",
                "A dead command: `/lemmi-ai-kit-core:no-such-skill` either.",
                "Wrong pack: `/lemmi-ai-kit-core:python-conventions`.",
                "Not typeable: `/lemmi-ai-kit-core:plan-critic`.",
                "A dead prefix: `/lemmi-ai-kit-legacy:kit-setup`.",
                "```",
                "/plugin marketplace add someone-else/some-other-repo",
                "/plugin install lemmi-ai-kit-core@not-a-marketplace",
                "/plugin install not-a-plugin@lemmi",
                "```",
                "A dead link: [gone](docs/no-such-page.md).",
                "A dead path: `tests/test_no_such_module.py`.",
            )
        ),
    )

    def caught(fragment: str) -> bool:
        return any(fragment in problem for problem in bad.problems)

    assert caught("spec-driven-devv"), "a renamed skill in a code span went unseen"
    assert caught("no-such-skill"), "an invocation of a missing skill went unseen"
    assert caught("python-conventions"), (
        "a core-prefixed invocation of a PYTHON-pack skill went unseen; the skill "
        "exists, so only the pack check can catch it"
    )
    assert caught("plan-critic"), (
        "an invocation of an internal skill went unseen -- it resolves in the manifest "
        "but never appears in the `/` menu, so nobody can type it"
    )
    assert caught("lemmi-ai-kit-legacy"), "the pre-split prefix shape went unseen"
    assert caught("some-other-repo"), "a `marketplace add` at another repo went unseen"
    assert caught("not-a-marketplace"), "an unpublished marketplace id went unseen"
    assert caught("not-a-plugin"), "an unpublished plugin name went unseen"
    assert caught("no-such-page.md"), "a dead relative link went unseen"
    assert caught("test_no_such_module.py"), "a dead repository path went unseen"

    assert len(bad.problems) == 10, (
        f"expected exactly ten findings, got {len(bad.problems)}:\n"
        + "\n".join(bad.problems)
        + "\n\nAn extra finding means a rule fired twice or on the wrong text; a "
        "missing one means the count above and the assertions have drifted apart."
    )


def test_the_guard_does_not_flag_the_names_that_are_not_skills() -> None:
    """Negative control: the plugin names, the marketplace id and the placeholders.

    Each of these is correct content that a shape-only rule would flag, and the obvious
    way to silence such a failure is to edit a working install command into a broken
    one. That makes a false positive here more expensive than a miss.
    """
    fine = _scan(
        "README.md",
        "\n".join(
            (
                "The packs are `lemmi-ai-kit-core` and `lemmi-ai-kit-python`.",
                "The pre-split plugin was `lemmi-ai-kit`.",
                "Skills are typed as `/lemmi-ai-kit-core:<name>`, for example",
                "`/lemmi-ai-kit-core:commit-message`.",
                "The old prefix `/lemmi-ai-kit:...` no longer resolves.",
                "Your own `AGENTS.md`, `CLAUDE.md` and `.ai/learnings.md` are yours.",
                "Run `git`, `ruff`, `pytest`; the branch is `main`.",
                "The `owner/repo` shorthand is what `marketplace add` takes.",
                "```sh",
                "codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit",
                "codex plugin add lemmi-ai-kit-python@lemmi",
                "```",
            )
        ),
    )
    assert not fine.problems, (
        "correct content was flagged:\n"
        + "\n".join(fine.problems)
        + "\n\nThese are plugin names, a marketplace id, a placeholder, and files in "
        "the adopter's own repository -- none of them is a skill name."
    )
    assert "lemmi-ai-kit-core" in fine.identifiers, (
        "the plugin name must be EXAMINED and then allowed, not invisible to the rule "
        "-- an exemption that works by never matching cannot be reviewed"
    )
    assert "/lemmi-ai-kit-core:<name>" in fine.invocations, (
        "the placeholder form must be matched and then skipped, so that losing it "
        "fails here rather than shrinking the scan in silence"
    )
    assert "lemmi-ukraine/lemmi-ai-kit" in fine.install_targets


# Every heading in the tree that punctuation touches, with the slug GitHub generates.
# The first is the one that has produced six false positives across two sessions.
_SLUG_CASES: tuple[tuple[str, str], ...] = (
    (
        "5. The seam — where your conventions attach",
        "5-the-seam--where-your-conventions-attach",
    ),
    (
        "One monorepo — works, with a caveat you should know about",
        "one-monorepo--works-with-a-caveat-you-should-know-about",
    ),
    ("Separate repositories — solved", "separate-repositories--solved"),
    # Inline code renders to its content, and only THEN loses the slash.
    (
        "If the `owner/repo` shorthand does not resolve",
        "if-the-ownerrepo-shorthand-does-not-resolve",
    ),
    (
        "A. You already have `AGENTS.md` and written conventions",
        "a-you-already-have-agentsmd-and-written-conventions",
    ),
    (
        "What is not built yet, and what is not verified",
        "what-is-not-built-yet-and-what-is-not-verified",
    ),
    (
        "2. You probably do not need to author a pack",
        "2-you-probably-do-not-need-to-author-a-pack",
    ),
    # A link in a heading renders to its text.
    ("See [the guide](docs/adoption-guide.md)", "see-the-guide"),
    # Underscores survive; they are not in the deletion set.
    ("A snake_case name", "a-snake_case-name"),
)


def test_the_slug_algorithm_reproduces_the_cases_that_produced_false_positives() -> (
    None
):
    """Positive control on the slugger, on the trap first.

    The double hyphen is the whole test. `github-slugger` deletes punctuation and only
    afterwards turns spaces into hyphens, so a spaced em dash leaves two spaces and
    therefore two hyphens. An implementation that collapses runs -- the obvious way to
    write this -- produces `#5-the-seam-where-...`, flags a link that works, and the
    cheapest way to silence it is to edit the working link. That happened four times in
    one session and twice in another, which is why it is asserted before anything else.
    """
    for heading, expected in _SLUG_CASES:
        actual = _github_slug(_heading_plain_text(heading))
        assert actual == expected, (
            f"slugging {heading!r} gave {actual!r}, not {expected!r}. This is GitHub's "
            "algorithm, not a choice: lowercase, delete punctuation, THEN replace each "
            "remaining space with a hyphen. Collapsing hyphen runs is the classic error."
        )

    # ...and the negative half: a collapsed double hyphen is NOT the same anchor.
    assert _github_slug("5. The seam — where it attaches") != _github_slug(
        "5. The seam - where it attaches"
    ), "a spaced em dash and a spaced hyphen must not slug to the same anchor"


def test_a_heading_inside_a_fence_is_not_an_anchor() -> None:
    """Positive control for the heading/fence disjointness, on the real document.

    `docs/adoption-guide.md` carries five `#` shell comments inside `sh` fences and a
    `### Project rules` inside a ```markdown example. Counted as headings they mint six
    anchors GitHub never generates -- including three that collide and get numbered
    `-1` and `-2` -- and a link to a heading that does not exist then resolves against
    a comment in a code sample and passes. That is a guard reporting success because it
    invented the thing it was looking for.
    """
    text = (_REPO_ROOT / "docs/adoption-guide.md").read_text(encoding="utf-8")
    honoured = set(_anchors_in(text))

    all_atx = list(_ATX_HEADING.finditer(text))
    fenced = [
        match
        for match in all_atx
        if any(start <= match.start() < end for start, end in _fence_regions(text))
    ]
    assert len(fenced) >= 5, (
        f"only {len(fenced)} of {len(all_atx)} `#` lines in adoption-guide.md sit "
        "inside a fence, so this control is no longer testing the filter it exists to "
        "test -- the document changed and the numbers here must be re-measured"
    )

    leaked = {_github_slug(_heading_plain_text(m.group("text"))) for m in fenced}
    assert "from-a-clone-of-lemmi-ai-kit" in leaked, (
        "the shell comment that produced the collision is gone from the document; "
        "re-measure this control rather than deleting it"
    )
    assert not leaked & honoured, (
        f"a `#` line inside a fenced block is being minted as an anchor: "
        f"{sorted(leaked & honoured)}"
    )

    # And the duplicate-numbering path is genuinely exercised: the repeated comment
    # collides three ways, so an unfiltered read would mint `-1` and `-2` as well.
    naive: dict[str, int] = {}
    for match in all_atx:
        slug = _github_slug(_heading_plain_text(match.group("text")))
        naive[slug] = naive.get(slug, 0) + 1
    assert naive.get("from-a-clone-of-lemmi-ai-kit", 0) >= 3, (
        "the repeated fenced comment no longer repeats, so the duplicate-numbering "
        "path this control exercises is untested"
    )

    # Finally: a link to one of the phantom anchors must FAIL.
    broken = _scan(
        "README.md",
        "See [the clone step](docs/adoption-guide.md#from-a-clone-of-lemmi-ai-kit).",
    )
    assert any("from-a-clone-of-lemmi-ai-kit" in p for p in broken.fragment_problems), (
        "a link pointing at a shell comment inside a code fence was accepted as a "
        f"heading (problems: {list(broken.problems)})"
    )


def test_the_chunk_scans_are_disjoint_and_the_check_can_fail() -> None:
    """Positive control for `_overlapping_chunks`, on the document that has teeth.

    `docs/adoption-guide.md` shows markdown inside a ```markdown fence, so two inline
    spans genuinely sit inside a fenced block and the filter has real work to do. Turn
    the filter off and the fence chunk overlaps both of them, which is exactly the
    state a runaway inline pattern produces. Without this the disjointness assertion in
    the surface test would be a claim nobody had ever seen fail.
    """
    text = (_REPO_ROOT / "docs/adoption-guide.md").read_text(encoding="utf-8")
    inside = _inline_code_inside_fences(text)
    assert len(inside) >= 2, (
        f"only {len(inside)} inline spans sit inside a fence in adoption-guide.md, so "
        "the filter has nothing to do and this control proves nothing. Re-measure."
    )

    assert not _overlapping_chunks(_code_chunks(text)), (
        "the real chunk list overlaps -- the filter is not filtering"
    )
    unfiltered = _overlapping_chunks(_code_chunks(text, drop_fenced_inline=False))
    assert unfiltered, (
        "turning the inline-inside-a-fence filter OFF produced no overlap, so the "
        "disjointness check cannot fail and is not evidence of anything"
    )

    # ...and the comparison itself works on a hand-made pair, which is the bug the
    # first version of the old check had: an assertion that could never have passed.
    assert _overlapping_chunks([(0, "abcdef"), (3, "def")]) == [("abcdef", "def")]
    assert not _overlapping_chunks([(0, "abc"), (3, "def")])


def test_the_fragment_rule_catches_a_broken_anchor() -> None:
    """Positive control. Every shape of anchor failure, against the real documents."""
    cases = {
        # The trap, inverted: the COLLAPSED spelling must be caught.
        "docs/adoption-guide.md#5-the-seam-where-your-conventions-attach": "collapsed",
        "docs/adoption-guide.md#3-installation": "renamed",
        "docs/faq.md#no-such-question": "cross-document",
        "CONTRIBUTING.md#no-such-section": "into an unscanned target",
    }
    for target, label in cases.items():
        found = _scan("README.md", f"See [it]({target}).").fragment_problems
        assert any(target in problem for problem in found), (
            f"a {label} anchor ({target}) produced no finding: {list(found)}"
        )

    # A same-document anchor is checked too, against the text actually scanned.
    same_doc = _scan("docs/adoption-guide.md", "# Real\n\nSee [x](#not-a-heading).")
    assert any("#not-a-heading" in p for p in same_doc.fragment_problems), (
        "a same-document anchor naming no heading in its own text went unseen"
    )


def test_the_fragment_rule_does_not_flag_the_anchors_that_are_correct() -> None:
    """Negative control, and here it is the expensive direction.

    Flagging a working link is worse than missing a broken one: the cheapest way to
    silence a false positive is to rewrite the anchor into the shape the guard wants,
    which breaks the link for every reader. Each of these is a live link in the tree.
    """
    fine = _scan(
        "README.md",
        "\n".join(
            (
                "The seam is [here]"
                "(docs/adoption-guide.md#5-the-seam--where-your-conventions-attach).",
                "Install is [here](docs/adoption-guide.md#3-install).",
                "The shorthand note is [here]"
                "(docs/adoption-guide.md#if-the-ownerrepo-shorthand-does-not-resolve).",
                "The FAQ is [here](docs/faq.md).",
                "An external anchor: [spec](https://example.com/page#section).",
                "A bare hash: [top](#).",
            )
        ),
    )
    assert not fine.problems, (
        "correct links were flagged:\n"
        + "\n".join(fine.problems)
        + "\n\nEvery one of these resolves today. Do not 'fix' the document to match "
        "the guard -- fix the guard."
    )
    assert (
        "docs/adoption-guide.md#5-the-seam--where-your-conventions-attach"
        in fine.fragments
    ), (
        "the double-hyphen anchor must be EXAMINED and then allowed, not invisible -- "
        "a rule that passes by never matching cannot be reviewed"
    )
    assert not any("example.com" in reference for reference in fine.fragments), (
        "an external URL fragment was resolved against local headings"
    )


def test_the_illustrative_pack_exemption_is_narrow() -> None:
    """`plugins/rust` is the worked example; `plugins/core/nope.py` is still a defect.

    The exemption is derived from the document's own `new-pack` line, so both halves
    matter: that it covers the invented pack, and that it covers nothing else in the
    same file. An exemption keyed on the filename would have silenced the whole
    document.
    """
    illustrative = _illustrative_pack_paths(
        (_REPO_ROOT / "docs/authoring-a-pack.md").read_text(encoding="utf-8")
    )
    assert illustrative == frozenset({"plugins/rust"}), (
        f"the worked example's pack is now {sorted(illustrative)}. It is read out of "
        "the document's `new-pack` command; if the example changed, this control's "
        "expectation changes with it -- but if it EMPTIED, the exemption is now "
        "silencing nothing and should be deleted rather than kept as decoration."
    )
    assert not (_REPO_ROOT / "plugins/rust").exists(), (
        "plugins/rust now exists, so it is no longer illustrative and the exemption "
        "has stopped being needed"
    )

    # Negative: the invented pack, and a file under it, pass.
    allowed = _scan(
        "docs/authoring-a-pack.md",
        "Run `new-pack rust`; it writes `plugins/rust/` and "
        "`plugins/rust/skills/rust-conventions/SKILL.md`.",
    )
    assert not allowed.path_problems, (
        f"the worked example was flagged: {list(allowed.path_problems)}"
    )
    assert "plugins/rust/" in allowed.repo_paths, (
        "the illustrative path must be EXAMINED and then allowed, not invisible"
    )

    # Positive: a genuinely dead path in the same document still fails.
    dead = _scan(
        "docs/authoring-a-pack.md",
        "Run `new-pack rust`; then edit `plugins/core/src/lemmi_ai_kit/no_such.py` "
        "and `plugins/python/skills/no-such-skill/SKILL.md`.",
    )
    assert len(dead.path_problems) == 2, (
        "the exemption is too wide -- a dead path in a REAL pack survived it:\n"
        + "\n".join(dead.path_problems)
    )


def test_the_marketplace_rule_accepts_a_local_clone_and_still_rejects_another_repo() -> (
    None
):
    """Negative then positive control for the corrected `marketplace add` rule.

    `./` is not a defective `owner/repo`; it is the local-clone install, and
    `docs/adoption-guide.md` documents it as the only path executed end to end, adding
    that this client rejects a bare `.` and that the trailing slash is "the difference
    between an install and an error". A guard calling it broken invites exactly the
    edit that breaks it.
    """
    local = _scan(
        "README.md",
        "\n".join(
            (
                "```sh",
                "claude plugin marketplace add ./",
                "codex plugin marketplace add .",
                "claude plugin marketplace add ../lemmi-ai-kit",
                "```",
            )
        ),
    )
    assert not local.problems, (
        "a local-clone marketplace source was flagged:\n" + "\n".join(local.problems)
    )
    assert local.install_targets.count("./") == 1 and "." in local.install_targets, (
        "the local sources must be EXAMINED and then skipped, so that losing the "
        f"match fails here rather than shrinking the scan (saw {local.install_targets})"
    )

    elsewhere = _scan(
        "README.md",
        "```sh\nclaude plugin marketplace add someone-else/some-other-repo\n```",
    )
    assert any("some-other-repo" in p for p in elsewhere.install_problems), (
        "widening the rule for local paths also let another repository through"
    )


def test_the_retired_plugin_id_is_allowed_only_where_it_is_the_subject() -> None:
    """Both ends of the one document-scoped exemption in this module.

    The id is derived from `pyproject.toml`; only the document is named. So the
    exemption has to prove two things: that the document still names the retired id
    (or it has stopped earning its place) and that the SAME reference still fails in
    README.md and docs/faq.md (or it is a hole rather than an exemption).
    """
    retired = cast(str, _project_metadata()["name"])
    relative = _DOCUMENTS_ABOUT_THE_RETIRED_PLUGIN[0]
    text = (_REPO_ROOT / relative).read_text(encoding="utf-8")

    assert f"{retired}@" in text and f"/{retired}:" in text, (
        f"{relative} no longer names the retired plugin id {retired!r} in both forms, "
        "so the exemption has stopped earning its place and should be deleted"
    )
    assert not _scan(relative, text).problems, (
        f"{relative} fails under the travelling rules:\n"
        + "\n".join(_scan(relative, text).problems)
    )

    # ...and the same content, in a document whose subject it is NOT, still fails.
    elsewhere = _scan(
        "README.md",
        f"Install `{retired}@lemmi`, then type `/{retired}:kit-setup`.",
    )
    assert len(elsewhere.install_problems) >= 2, (
        f"the retired id passed in README.md too, so this is not an exemption scoped "
        f"to the migration document -- it is a hole ({list(elsewhere.problems)})"
    )


_EXCLUDED_ON_THE_MERITS = "docs/migrating-from-0.1.0.md"


def test_the_exclusions_still_earn_themselves() -> None:
    """The scope decision must stay a finding about the documents, not a preference.

    The migration document is now scanned under the travelling rules, but stays outside
    the bare-identifier one because its subject is skill names that were deliberately
    retired, so that rule would flag it for being accurate. That is a claim about its
    content, and content changes. Asserting it here means the scope note in the module
    docstring is checked rather than remembered -- and if this ever fails, the honest
    response is to promote the document into `_GUARDED_DOCS`, not to delete the
    assertion.
    """
    text = (_REPO_ROOT / _EXCLUDED_ON_THE_MERITS).read_text(encoding="utf-8")
    retired = sorted(
        {
            match.group("content")
            for match in _inline_outside_fences(text)
            if _IDENTIFIER.match(match.group("content"))
            and match.group("content") not in _skills()
            and match.group("content") not in _non_skill_identifiers()
        }
    )
    assert retired, (
        f"{_EXCLUDED_ON_THE_MERITS} no longer names any identifier that fails to "
        "resolve, so the reason it sits outside _GUARDED_DOCS has gone. Either it now "
        "belongs in scope, or the exclusion needs a different justification than the "
        "one the module docstring gives."
    )


def test_the_stated_limits_are_real() -> None:
    """The docstring names three holes. Assert their size, so the prose cannot rot.

    A limit that is written down but never measured drifts the same way a hand-written
    count does -- and this one would drift towards claiming more coverage than the
    rules deliver.
    """
    single_token = sorted(name for name in _skills() if "-" not in name)
    assert single_token == ["orchestrate"], (
        f"the single-token skills are now {single_token}. Limit 2 in the module "
        "docstring says exactly one skill is invisible to the bare-identifier rule; "
        "that just changed. Either name new skills with a hyphen, or "
        "widen the rule and rewrite the note -- do not leave the prose claiming the "
        "old size."
    )

    prose_only = _scan("README.md", "A skill named spec-driven-devv in bare prose.")
    assert not prose_only.problems, (
        "limit 1 claims unbackticked prose is not scanned, but something matched it"
    )

    unmarked = _scan("README.md", "Run orchestrate to split the work up.")
    assert not unmarked.problems and not unmarked.identifiers

    # ...and the same name in invocation form IS checked, which is what makes the
    # single-token hole a shape problem rather than a coverage problem.
    invoked = _scan("README.md", "Type `/lemmi-ai-kit-core:orchestrate` to split work.")
    assert invoked.invocations == ("/lemmi-ai-kit-core:orchestrate",)
    assert not invoked.problems

    # -- the fragment rule's own two limits, both measured ------------------------
    #
    # 1. Setext headings (`===` / `---` underlines) are not matched. Cost today: zero,
    #    and this is what says so. If one appears, its anchor becomes invisible and a
    #    link to it would be reported as broken -- a false positive, the expensive kind.
    setext = re.compile(r"(?m)^(?!#)(\S[^\n]*)\n(=+|-{3,})[ \t]*$")
    with_setext = {
        relative
        for relative in _ALL_SCANNED_DOCS
        if setext.search((_REPO_ROOT / relative).read_text(encoding="utf-8"))
    }
    assert not with_setext, (
        f"{sorted(with_setext)} now use setext headings, which `_ATX_HEADING` does not "
        "match. Their anchors are invisible to the fragment rule, so a correct link to "
        "one would be reported broken. Extend the pattern -- do not rewrite the link."
    )

    # 2. `_heading_plain_text` handles code, links and images, but not `_emphasis_`.
    #    `*` is deleted by the slug rule whether it is markup or not, so only `_`
    #    could differ -- it SURVIVES slugging, so `_x_` would slug to `_x_` and not
    #    `x`. Cost today: zero, asserted rather than assumed.
    underscored = [
        (relative, match.group("text"))
        for relative in _ALL_SCANNED_DOCS
        for match in _headings((_REPO_ROOT / relative).read_text(encoding="utf-8"))
        if "_" in match.group("text")
    ]
    assert not underscored, (
        f"a heading now contains an underscore: {underscored}. If it is emphasis, the "
        "slug drops it and `_heading_plain_text` does not, so the anchor computed here "
        "is wrong. If it is a literal underscore in a name, it is safe -- but say so "
        "here rather than leaving the limit unmeasured."
    )

    # 3. A fragment on a non-markdown target (`file.py#L20`) is counted and skipped.
    #    Vacuous today, and the assertion is what makes that visible: the day one
    #    appears, this fails and the skip has to be justified rather than inherited.
    non_markdown = [
        reference
        for scan in _scan_guarded_docs().values()
        for reference in scan.fragments
        if not reference.partition("#")[0].endswith(".md")
        and reference.partition("#")[0]
    ]
    assert not non_markdown, (
        f"a fragment now points at a non-markdown file: {non_markdown}. These are "
        "skipped as GitHub line anchors; confirm that is still what they are."
    )
