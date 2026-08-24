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

**Two documents: `README.md` and `docs/faq.md`.** The FAQ is in scope because it is
adopter-facing in exactly the same way -- it names `kit-setup` and `commit-message` as
things you type, and links relative paths into this repository -- and because a reader
who arrives there instead of the README deserves the same guarantee.

The other documents are out of scope, and not by oversight. In every one of them a bare
hyphenated code span means something other than a skill, so the identifier rule would
raise findings that are all correct content:

| document | hyphenated identifiers that are not skills |
|---|---|
| `docs/migrating-from-0.1.0.md` | pre-split skill names, quoted *because* they no longer resolve |
| `docs/syncing-from-upstream.md` | upstream skill names this kit deliberately did not port |
| `CONTRIBUTING.md`, `docs/working-on-the-kit.md`, `docs/authoring-a-pack.md` | CLI subcommands (`publish-check`, `audit-skills`, `new-pack`) |
| `docs/adoption-guide.md` | generated-block markers (`project-rules`, `skills-index`) |

(No count is given for those findings on purpose. Nothing here would check it, and a
hand-written number is wrong the first time one of those documents is edited.)

The migration document is the sharp case: its subject is names that are gone. A guard
demanding they resolve would flag the record for being accurate, and the obvious way to
silence it would be to delete the migration path.
`test_the_exclusions_still_earn_themselves` asserts that this is still true of it, so
the exclusion keeps earning its place rather than persisting as an opinion someone once
held. The rule holds where the convention holds -- in the two documents where a bare
hyphenated identifier means a skill and nothing else.

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
first-segment rule excludes them for free rather than by exemption. Link *fragments*
are not resolved against the target's headings; that is a real gap, left open on
purpose, since anchor slugging is a per-renderer rule and getting it subtly wrong would
flag correct links.

**The two region scans must not overlap, and that assertion earned its place twice.**
The first draft of `_INLINE_CODE` allowed backticks inside a span, so it matched one
fence marker against the next and reported eight phantom spans in README.md alone --
found on the first run of the overlap check, before any of this was committed. The
second defect was in the check itself: it compared two lists of `re.Match` objects with
`==`, which is identity for matches, so it could never have passed. Both are the reason
`test_the_overlap_check_fires_when_the_regions_do_overlap` exists. An assertion that
cannot fail and an assertion that cannot pass are the same bug wearing different
clothes, and only running a deliberately bad input tells them apart.
"""

import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, cast

from lemmi_ai_kit.manifest import PACK_PLUGIN_NAMES, SkillEntry, load_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The two documents an adopter reads before installing anything. See the module
# docstring for why the rest of `docs/` is out of scope.
_GUARDED_DOCS: tuple[str, ...] = ("README.md", "docs/faq.md")

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

_EXTERNAL_LINK = ("http://", "https://", "mailto:", "#")

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
)


def _line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


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


def _code_chunks(text: str) -> list[tuple[int, str]]:
    """Every code-formatted region as `(offset, text)`: fence bodies and inline spans."""
    chunks = [(match.start(), match.group(0)) for match in _FENCE.finditer(text)]
    chunks += [
        (match.start("content"), match.group("content"))
        for match in _inline_outside_fences(text)
    ]
    return sorted(chunks)


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
    skill_problems: tuple[str, ...]
    install_problems: tuple[str, ...]
    path_problems: tuple[str, ...]

    @property
    def checked(self) -> tuple[str, ...]:
        return (
            *self.identifiers,
            *self.invocations,
            *self.install_targets,
            *self.repo_paths,
        )

    @property
    def problems(self) -> tuple[str, ...]:
        return (*self.skill_problems, *self.install_problems, *self.path_problems)


def _scan(relative: str, text: str) -> _Scan:
    """Apply every rule to one document.

    Pure over `(relative, text)` so the controls can run the real rules against a
    synthetic document rather than a re-implementation of them.
    """
    skills = _skills()
    exempt = _non_skill_identifiers()
    plugins = frozenset(PACK_PLUGIN_NAMES.values())
    base = (_REPO_ROOT / relative).parent

    identifiers: list[str] = []
    invocations: list[str] = []
    install_targets: list[str] = []
    repo_paths: list[str] = []
    skill_problems: list[str] = []
    install_problems: list[str] = []
    path_problems: list[str] = []

    def where(position: int) -> str:
        return f"{relative}:{_line_of(text, position)}"

    # -- skill names, shape-matched, in whole inline code spans -------------------
    for match in _inline_outside_fences(text):
        content = match.group("content")
        if not _IDENTIFIER.match(content):
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
        plugin, name = match.group("plugin"), match.group("skill")
        invocations.append(match.group(0))
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
    for offset, chunk in _code_chunks(text):
        for token in _CODE_TOKEN.finditer(chunk):
            target = _INSTALL_TARGET.match(token.group(0))
            if target is None:
                continue
            install_targets.append(token.group(0))
            plugin, marketplace = target.group("plugin"), target.group("marketplace")
            if plugin not in plugins:
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
            install_targets.append(add.group("target"))
            if add.group("target") != _repository_shorthand():
                install_problems.append(
                    f"{where(offset)}: `marketplace add {add.group('target')}` does not "
                    f"name this repository, which is {_repository_shorthand()!r} "
                    "according to pyproject.toml's Repository URL."
                )

    # -- paths: link destinations, then repository paths written as code ----------
    for match in _LINK_TARGET.finditer(text):
        target_path = match.group("target")
        if target_path.startswith(_EXTERNAL_LINK):
            continue
        path_part = target_path.partition("#")[0]
        if not path_part:
            continue
        repo_paths.append(target_path)
        resolved = (base / path_part).resolve()
        if not resolved.is_relative_to(_REPO_ROOT):
            path_problems.append(
                f"{where(match.start())}: the link to {target_path!r} escapes the "
                "repository."
            )
        elif not resolved.exists():
            path_problems.append(
                f"{where(match.start())}: the link to {target_path!r} resolves to "
                "nothing."
            )

    for match in _inline_outside_fences(text):
        content = match.group("content")
        if "/" not in content or content.split("/")[0] not in _tracked_top_level():
            continue
        if any(character in content for character in "<>*? "):
            continue
        repo_paths.append(content)
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
        skill_problems=tuple(skill_problems),
        install_problems=tuple(install_problems),
        path_problems=tuple(path_problems),
    )


def _scan_guarded_docs() -> dict[str, _Scan]:
    return {
        relative: _scan(relative, (_REPO_ROOT / relative).read_text(encoding="utf-8"))
        for relative in _GUARDED_DOCS
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


def test_the_scan_surface_is_what_it_claims() -> None:
    """State the coverage in numbers, and assert the two region scans are disjoint.

    Floors rather than exact totals: another session owns both documents, and a new
    paragraph is not a defect. What must not change silently is the *kind* of thing
    seen, so `_MUST_BE_CHECKED` names references that carried real risk and asserts
    each was examined.
    """
    scans = _scan_guarded_docs()
    assert len(_GUARDED_DOCS) == 2 and set(scans) == set(_GUARDED_DOCS), (
        "the guarded set is not the two documents this module claims to cover"
    )

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
    }
    report = "scan surface: " + ", ".join(
        f"{kind}={count}" for kind, count in sorted(totals.items())
    )
    assert totals["identifiers"] >= 10, report
    assert totals["invocations"] >= 4, report
    assert totals["targets"] >= 4, report
    assert totals["paths"] >= 20, report

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


_EXCLUDED_ON_THE_MERITS = "docs/migrating-from-0.1.0.md"


def test_the_exclusions_still_earn_themselves() -> None:
    """The scope decision must stay a finding about the documents, not a preference.

    The migration document is excluded because its subject is skill names that were
    deliberately retired, so the identifier rule would flag it for being accurate. That
    is a claim about its content, and content changes. Asserting it here means the
    scope note in the module docstring is checked rather than remembered -- and if this
    ever fails, the honest response is to widen `_GUARDED_DOCS`, not to delete the
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
