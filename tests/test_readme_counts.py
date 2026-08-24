"""Every skill count in the README must equal the manifest's, and the plugin
manifests must carry no count at all.

Before this test, **no test read README.md**. The count there was maintained by
hand, and it went wrong the moment the catalog changed: the repo shipped
"33 skills" in the README while the manifest carried 29, and both plugin manifests
advertised "30+ skills" — vague against 33 and false against 29. CI stayed green
throughout, because nothing looked.

That makes a one-time correction worthless on its own: I2 and I4 both change this
number again. So the README is allowed to state a count *because* this test
enforces it, and the plugin manifests are not allowed to state one at all — a
marketplace listing is the worst place for a number nobody can see rot.

**The pattern was then blind to qualifiers, which is how it stayed green over a
false claim.** It required `skills` to follow the digits immediately, so
`"38 skills"` was enforced while `"35 language-agnostic skills"` and
`"2 Python-specific skills"` were invisible to it. Measured 2026-08-24: one claim
of three enforced, and one of the two it could not see was wrong — the core pack
had grown to 36. The durable fix for hand-written counts was applied to the
headline number and never to the rest of the file, so this repo's own
documentation could assert that the README count "is enforced against the
manifest" while a third of it was.

That failure is worth naming precisely, because it is the opposite of the usual
one. A scan that finds nothing at least returns a zero, and a zero invites a
second look. This one returned SUCCESS — the outcome everybody wants — which
makes it the least interrogated result in the repository.

Two things follow, and both are load-bearing:

**A qualifier scopes the claim to a pack, and an unregistered qualifier fails.**
`_PACK_QUALIFIERS` maps the prose a human would actually write onto a pack whose
size the manifest knows. A qualifier that is *not* registered is a failure, not a
pass — that is the whole difference between this guard and the one it replaces.
Writing "36 orchestration skills" is not silently ignored; it demands that the
author either register what the phrase scopes to or drop the number.

**The enforcing pattern is checked against a deliberately looser net.** A guard
that has never been shown to fail has not been shown to work, so
`test_the_enforcing_pattern_sees_every_count_shaped_claim` runs a sloppier regex
over the same file and fails if it finds a claim the enforcing one missed. Fixing
today's three claims would otherwise leave the *class* of defect intact, waiting
for the next phrasing nobody anticipated.
"""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

from lemmi_ai_kit.manifest import PACKS, load_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# "38 skills", "30+ skills", and the qualified forms the previous pattern could not
# see: "35 language-agnostic skills", "2 Python-specific skills". The qualifier is
# captured so it can be RESOLVED rather than skipped, and is bounded to three words
# so an unrelated sentence that merely contains a number and the word "skills" is
# not swept in.
_COUNT_CLAIM = re.compile(r"(\d+)(\+?)\s+((?:[A-Za-z][\w-]*\s+){0,3}?)skills\b")

# A deliberately sloppier net. It exists only to prove the enforcing pattern is not
# blind, and is never used to check a number. If it sees a count-shaped phrase that
# `_COUNT_CLAIM` does not, the enforcing pattern has a hole — which is exactly how a
# wrong count sat on the README landing page and stayed green.
_LOOSE_COUNT_SHAPE = re.compile(r"\d+\+?(?:\s+\S+){0,4}?\s+skills\b")

# Prose that scopes a count to one pack. An unregistered qualifier is an error; see
# the module docstring.
_PACK_QUALIFIERS: dict[str, str] = {
    "language-agnostic": "core",
    "Python-specific": "python",
}

# Manifests whose prose is indexed by a marketplace, so it must carry no count.
_MANIFEST_FILES: tuple[str, ...] = (
    # The two marketplace catalogs are per-repo, not per-pack.
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    # Pack manifests are DERIVED. Enumerating them by hand meant a pack added later was
    # silently never scanned -- the guard would not fail, it would just stop looking,
    # which is the failure mode this module exists to prevent.
    *(f"plugins/{pack}/.claude-plugin/plugin.json" for pack in sorted(PACKS)),
    *(f"plugins/{pack}/.codex-plugin/plugin.json" for pack in sorted(PACKS)),
)



def _shipped_skill_count() -> int:
    return len(load_manifest().skills)


def _skills_per_pack() -> Counter[str]:
    return Counter(skill.pack for skill in load_manifest().skills)


def _readme() -> str:
    return (_REPO_ROOT / "README.md").read_text(encoding="utf-8")


def test_every_readme_skill_count_matches_the_manifest() -> None:
    text = _readme()
    total = _shipped_skill_count()
    per_pack = _skills_per_pack()

    problems: list[str] = []
    found = 0
    for match in _COUNT_CLAIM.finditer(text):
        found += 1
        line = text.count("\n", 0, match.start()) + 1
        claimed, approx = int(match.group(1)), match.group(2)
        qualifier = match.group(3).strip()

        if approx:
            problems.append(
                f"README.md:{line}: {match.group(0)!r} is an approximate count — "
                "state the exact number so this test can hold it, or drop it entirely"
            )
            continue

        if not qualifier:
            expected, what = total, "the manifest"
        elif qualifier in _PACK_QUALIFIERS:
            pack = _PACK_QUALIFIERS[qualifier]
            expected, what = per_pack[pack], f"the {pack} pack"
        else:
            problems.append(
                f"README.md:{line}: {match.group(0)!r} scopes a count with "
                f"{qualifier!r}, which is not in _PACK_QUALIFIERS, so nothing can "
                "check it. Register the phrase against a pack, or drop the number. "
                "An unrecognised qualifier is not a free pass — that is how "
                "'35 language-agnostic skills' stayed wrong and green."
            )
            continue

        if claimed != expected:
            problems.append(
                f"README.md:{line}: claims {claimed} skills, {what} ships {expected}"
            )

    assert not problems, "\n".join(problems)
    assert found > 0, (
        "no skill count found in README.md. If the count was deliberately removed "
        "that is fine — delete this assertion. It exists so the check cannot pass "
        "vacuously after a rewrite silently drops the number."
    )


def test_the_enforcing_pattern_sees_every_count_shaped_claim() -> None:
    """Guard the guard: prove `_COUNT_CLAIM` is not blind to some phrasing.

    Both patterns end on the word `skills`, so a shared end offset identifies the
    same claim under either net.
    """
    text = _readme()
    enforced = {match.end() for match in _COUNT_CLAIM.finditer(text)}
    missed = [
        f"README.md:{text.count(chr(10), 0, match.start()) + 1}: {match.group(0)!r}"
        for match in _LOOSE_COUNT_SHAPE.finditer(text)
        if match.end() not in enforced
    ]
    assert not missed, (
        "count-shaped claims in README.md that the enforcing pattern cannot see:\n"
        + "\n".join(missed)
        + "\n\nWiden _COUNT_CLAIM to cover the phrasing, or reword the README. A "
        "claim this test cannot see is a claim that nothing checks."
    )


def test_the_qualifier_resolution_is_exercised() -> None:
    """A positive control: the pattern must demonstrably catch what it claims to.

    Without this, `_PACK_QUALIFIERS` could be emptied or the qualifier group
    broken and every test above would still pass, on a README that happened to
    carry only an unqualified count.
    """
    per_pack = _skills_per_pack()
    for qualifier, pack in _PACK_QUALIFIERS.items():
        match = _COUNT_CLAIM.search(f"plus {per_pack[pack]} {qualifier} skills under")
        assert match is not None, f"{qualifier!r} is no longer matched at all"
        assert match.group(3).strip() == qualifier, (
            f"{qualifier!r} did not survive as the captured qualifier; got "
            f"{match.group(3)!r}"
        )

    bare = _COUNT_CLAIM.search("— 38 skills (spec-driven dev)")
    assert bare is not None and bare.group(3).strip() == ""

    unknown = _COUNT_CLAIM.search("12 wildly-invented skills")
    assert unknown is not None and unknown.group(3).strip() == "wildly-invented", (
        "an unregistered qualifier must still MATCH, so the check above can reject "
        "it by name; a pattern that failed to match it would fail open instead"
    )


def _strings(node: Any) -> list[str]:
    """Every string value anywhere in a parsed JSON document."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in cast(dict[str, Any], node).values() for s in _strings(v)]
    if isinstance(node, list):
        return [s for v in cast(list[Any], node) for s in _strings(v)]
    return []


def test_no_plugin_manifest_advertises_a_skill_count() -> None:
    """A marketplace listing is the worst place for a number nobody watches.

    Checks every string in each manifest rather than named fields, so a count added
    to a field that does not exist yet is still caught.
    """
    problems: list[str] = []
    for relative in _MANIFEST_FILES:
        path = _REPO_ROOT / relative
        if not path.is_file():
            continue
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        for value in _strings(data):
            match = _COUNT_CLAIM.search(value)
            if match is not None:
                problems.append(
                    f"{relative}: advertises {match.group(0)!r}. Describe what the "
                    "skills do instead — this text is indexed by a marketplace and "
                    "nothing can catch it going stale."
                )

    assert not problems, "\n".join(problems)
