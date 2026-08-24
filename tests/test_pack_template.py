"""The pack skeleton, held to the pack contracts without being made a pack.

`plugins/_template/` is the seed `new-pack` copies, so a defect there does not stay
there: it is reproduced into every pack anyone authors afterwards, and the contracts
that would catch it only run after the copy, in a module whose failure names the
generated pack rather than the skeleton that caused it.

Two contracts did not reach the template, for the same reason. `test_assets.py`'s
`_ASSET_ONLY_FORBIDDEN` scan and `test_readme_counts.py`'s no-count-in-a-manifest scan
both derive their scope from `PACKS`, and `_template` is deliberately not in `PACKS`.
(`_FORBIDDEN` does reach it, via `test_publication_hygiene.py`, which scans everything
git would publish. These two do not.)

**That exclusion is load-bearing and this module does not touch it.** `load_manifest()`
raises on a skill directory under a pack with no manifest entry, and the template ships
one, so a guard that reached the template by adding it to `PACKS` would redden the whole
suite. `test_cli.py::test_the_template_is_invisible_to_every_pack_enumeration` pins that
invisibility. So the contracts are imported and applied to a second, separately derived
scope -- the same shape `test_publication_hygiene.py` uses for `_FORBIDDEN`. One
definition, two scopes, and `test_the_two_scopes_are_disjoint` proves the second scope is
not silently a subset of the first, which would make every check here a duplicate.

## The trap this module had to avoid

The template is full of `{{VERSION}}`-style placeholders that `new-pack` substitutes. A
guard that treated it as a finished pack would fail on placeholders that are *correct*.
So the scope below is exactly the set of files `new-pack` copies, taken from
`cli._pack_layout()` -- the function that does the copying -- rather than from a second
`rglob` that could drift from it. `test_the_placeholders_are_present_and_all_resolve`
then pins the other half: the placeholders are really there (so the check is not passing
on an empty set), every one of them is a key `new-pack` can fill, and text containing all
of them trips neither contract.

The template's `README.md` is outside this scope on purpose: `new-pack` does not copy it
(`cli._TEMPLATE_ONLY`), it documents the template rather than any pack, and
`test_publication_hygiene.py` already scans it.

## Nothing was wrong in the template when this was written

This is a coverage fix, not a defect fix. That is precisely why the positive controls
below matter: with the template clean, every check here would also pass if it were
scanning nothing at all.
"""

import json
import re
from pathlib import Path
from typing import Any

from test_assets import (
    _ASSET_ONLY_FORBIDDEN,  # pyright: ignore[reportPrivateUsage]
    _asset_text_files,  # pyright: ignore[reportPrivateUsage]
)
from test_readme_counts import (
    _COUNT_CLAIM,  # pyright: ignore[reportPrivateUsage]
    _MANIFEST_FILES,  # pyright: ignore[reportPrivateUsage]
    _strings,  # pyright: ignore[reportPrivateUsage]
)

from lemmi_ai_kit import cli

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE_DIR = _REPO_ROOT / cli.PACK_TEMPLATE

# `_pack_layout` renames the example skill directory to whatever it is given. This module
# only ever reads the SOURCE side of each pair, so the name is arbitrary; it is a
# constant rather than a literal at the call sites so that is obvious.
_PROBE_SKILL = "probe-conventions"


def _copied_sources() -> dict[str, Path]:
    """{repo-relative path: file} for everything `new-pack` copies out of the template.

    Derived from the copying function itself. A second `rglob` here would be a second
    opinion about what propagates, and the two would drift the first time the template
    grew a file the copier skips.
    """
    return {
        source.relative_to(_REPO_ROOT).as_posix(): source
        for source, _ in cli._pack_layout(_TEMPLATE_DIR, _PROBE_SKILL)  # pyright: ignore[reportPrivateUsage]
    }


def _hits(text: str) -> list[tuple[str, re.Match[str]]]:
    """(reason, match) for every asset-only pattern `text` trips."""
    return [
        (why, match)
        for pattern, why in _ASSET_ONLY_FORBIDDEN
        for match in pattern.finditer(text)
    ]


def _contamination(relative: str, text: str) -> list[str]:
    return [
        f"{relative}:{text.count(chr(10), 0, match.start()) + 1}: {why} "
        f"({match.group(0)!r})"
        for why, match in _hits(text)
    ]


def _count_claims(relative: str, data: Any) -> list[str]:
    """Every string anywhere in `data` that advertises a skill count."""
    return [
        f"{relative}: advertises {match.group(0)!r}"
        for value in _strings(data)
        if (match := _COUNT_CLAIM.search(value)) is not None
    ]


def _pack_manifest_shapes() -> frozenset[str]:
    """`.claude-plugin/plugin.json` and friends, derived from the guard being widened.

    Taken from `_MANIFEST_FILES` by stripping the `plugins/<pack>/` prefix, so a third
    plugin host added there brings the template into scope for it automatically. A
    hand-written pair here would be the same "enumerated by hand, so the next one is
    never scanned" failure that module's own docstring describes.
    """
    return frozenset(
        entry.split("/", 2)[2]
        for entry in _MANIFEST_FILES
        if entry.startswith("plugins/") and entry.count("/") >= 2
    )


def _template_manifests() -> dict[str, Path]:
    return {
        f"{cli.PACK_TEMPLATE}/{shape}": _TEMPLATE_DIR / shape
        for shape in sorted(_pack_manifest_shapes())
    }


# --- the scan surface -----------------------------------------------------------------


def test_the_scan_surface_is_everything_new_pack_copies() -> None:
    """State the surface in numbers the test recomputes, so the name cannot drift.

    Two independent facts have to agree: what is on disk under the template, and what
    the copier reports it will copy. The only permitted difference is `_TEMPLATE_ONLY`.
    """
    on_disk = {
        path.relative_to(_TEMPLATE_DIR).as_posix()
        for path in _TEMPLATE_DIR.rglob("*")
        if path.is_file()
    }
    copied = {
        path.relative_to(_TEMPLATE_DIR).as_posix()
        for path in _copied_sources().values()
    }
    template_only = cli._TEMPLATE_ONLY  # pyright: ignore[reportPrivateUsage]

    assert on_disk, (
        f"{cli.PACK_TEMPLATE} holds no files, so every check here is vacuous"
    )
    assert copied, "`new-pack` copies nothing, so every check here is vacuous"
    assert template_only <= on_disk, (
        f"_TEMPLATE_ONLY names {sorted(template_only - on_disk)}, which is not in the "
        "template. A dead exclusion silently widens the scope it was meant to narrow."
    )
    assert copied == on_disk - template_only, (
        f"the copied set {sorted(copied)} is not the template minus "
        f"{sorted(template_only)}; the scope this module scans no longer matches what "
        "`new-pack` propagates"
    )


def test_the_two_scopes_are_disjoint() -> None:
    """A contract with two scan surfaces must not have one silently inside the other.

    If the template were reachable from the `PACKS`-derived scope, every check in this
    module would be a second run of `test_assets.py` -- green, and covering nothing new.
    """
    asset_scope = {path.resolve() for path in _asset_text_files()}
    template_scope = {path.resolve() for path in _copied_sources().values()}
    assert asset_scope, "the PACKS-derived asset scope is empty; the probe is broken"
    assert template_scope, "the template scope is empty; the probe is broken"
    assert not asset_scope & template_scope, (
        "these files are in both scopes: "
        f"{sorted(str(p) for p in asset_scope & template_scope)}"
    )

    packs_manifests = {(_REPO_ROOT / entry).resolve() for entry in _MANIFEST_FILES}
    template_manifests = {path.resolve() for path in _template_manifests().values()}
    assert packs_manifests and template_manifests
    assert not packs_manifests & template_manifests, (
        "these manifests are in both scopes: "
        f"{sorted(str(p) for p in packs_manifests & template_manifests)}"
    )


def test_the_template_manifest_set_is_derived_and_real() -> None:
    """The two derivations of "which files are a pack's manifests" must agree.

    One comes from the guard being widened (`_MANIFEST_FILES`), the other from the
    copier (`_pack_layout`). A host added to one and not the other means either a pack
    manifest nobody scans, or a scan pointed at a file the template does not ship.
    """
    shapes = _pack_manifest_shapes()
    assert shapes, (
        "_MANIFEST_FILES lists no per-pack manifest, so nothing here is scoped to the "
        "template and this module's manifest half is vacuous"
    )
    from_copier = {
        destination.as_posix()
        for _, destination in cli._pack_layout(_TEMPLATE_DIR, _PROBE_SKILL)  # pyright: ignore[reportPrivateUsage]
        if destination.suffix == ".json"
    }
    assert set(shapes) == from_copier, (
        f"_MANIFEST_FILES implies {sorted(shapes)} but `new-pack` copies "
        f"{sorted(from_copier)}"
    )
    for relative, path in sorted(_template_manifests().items()):
        assert path.is_file(), f"{relative} is missing, so it is scanned as nothing"


# --- the widened contracts ------------------------------------------------------------


def test_the_template_carries_no_unshipped_reference() -> None:
    """`_ASSET_ONLY_FORBIDDEN`, applied to the skeleton every pack is copied from.

    Every copied file is read, including suffixes `new-pack` treats as binary: a file
    that cannot be decoded is REPORTED rather than skipped, because a silent skip is
    the failure this module exists to close.
    """
    problems: list[str] = []
    scanned = 0
    sources = _copied_sources()
    for relative, path in sorted(sources.items()):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            problems.append(
                f"{relative}: could not be scanned ({type(exc).__name__}). It still "
                "ships into every pack, so decide deliberately what to do with it."
            )
            continue
        scanned += 1
        problems += _contamination(relative, text)

    assert not problems, (
        "the pack template points at things the kit does not ship:\n"
        + "\n".join(problems)
        + "\n\nFix the template, not the pack it produced -- every pack authored after "
        "this carries the same text."
    )
    assert scanned == len(sources), (
        f"{scanned} of {len(sources)} copied files were scanned; the rest were skipped"
    )


def test_the_template_manifests_advertise_no_skill_count() -> None:
    """The count rule, applied to the manifests every pack's manifests are copied from.

    A marketplace listing is the worst place for a number nobody watches, and a number
    seeded here would be reproduced into every pack -- each one then advertising a count
    that was wrong before it was written, since a new pack ships one skill.
    """
    problems: list[str] = []
    for relative, path in sorted(_template_manifests().items()):
        problems += _count_claims(
            relative, json.loads(path.read_text(encoding="utf-8"))
        )
    assert not problems, (
        "the pack template advertises a skill count:\n"
        + "\n".join(problems)
        + "\n\nDescribe what the skills do instead."
    )


# --- positive controls ----------------------------------------------------------------
#
# Nothing is wrong in the template today, so every check above would also pass on an
# empty scan. These prove the checks can fail.

# One probe per pattern is NOT asserted by counting probes -- the assertion below is that
# the probes between them trip every reason in `_ASSET_ONLY_FORBIDDEN`. A pattern added
# upstream with no probe here fails that assertion by name, and no reason string is
# restated in this file, so the two cannot drift into disagreeing about wording.
_KNOWN_BAD: tuple[str, ...] = (
    "run `python scripts/ai_files_lint.py` before committing",
    "then `python scripts/audit_skills.py --strict`",
    "install the package, then run `lemmi-ai-kit audit-skills`",
    "branch layout is in `docs/git-stacked-pr-workflow.md`",
    "keep `.ai/interview-prompt-changelog.md` current",
)


def test_the_contamination_scan_catches_a_known_bad_template() -> None:
    """Every asset-only pattern must be shown to fire, on text shaped like a template."""
    triggered: set[str] = set()
    for probe in _KNOWN_BAD:
        hits = _hits(probe)
        assert hits, (
            f"probe {probe!r} tripped nothing. It is meant to be caught -- either the "
            "pattern it targets changed, or the probe no longer resembles it."
        )
        triggered |= {why for why, _ in hits}

    expected = {why for _, why in _ASSET_ONLY_FORBIDDEN}
    assert triggered == expected, (
        f"patterns no probe exercises: {sorted(expected - triggered)}. An unexercised "
        "pattern is one this module has never shown itself able to catch in the "
        "template, which is the only claim it makes."
    )
    # And the scan is not simply always-positive.
    assert _hits("a pack of conventions for a language, with no forbidden text") == []


def test_the_count_scan_catches_a_seeded_count() -> None:
    """Seed a count into a real template manifest and prove it comes back flagged."""
    relative, path = sorted(_template_manifests().items())[0]
    shipped: Any = json.loads(path.read_text(encoding="utf-8"))
    assert _count_claims(relative, shipped) == [], (
        "the shipped manifest is not clean, so this control cannot tell a seeded count "
        "from the file's own text"
    )
    for seeded in ("30+ skills", "36 skills", "12 language-agnostic skills"):
        polluted: dict[str, Any] = dict(shipped)
        polluted["description"] = f"A pack of {seeded} for something"
        assert _count_claims(relative, polluted), f"{seeded!r} was not caught"
        # Nested too: the codex manifest keeps prose under `interface`, and a scan that
        # only read top-level fields would miss every one of them.
        nested: dict[str, Any] = {"interface": {"defaultPrompt": [f"Review {seeded}"]}}
        assert _count_claims(relative, nested), f"{seeded!r} was not caught when nested"


def test_the_placeholders_are_present_and_all_resolve() -> None:
    """The trap, pinned: `{{VERSION}}` is CORRECT in the template and must not be flagged.

    Three claims, and the first is what makes the other two mean anything:

    1. The template really does carry placeholders -- otherwise "the guards do not trip
       on placeholders" is a statement about an empty set.
    2. Every placeholder present is a key `new-pack` can fill. `_render_template` already
       refuses an unfillable one at scaffold time; this catches it before anyone runs the
       command, and names the template rather than the half-written pack.
    3. Text carrying all of them trips neither widened contract.
    """
    subs = cli._pack_substitutions(  # pyright: ignore[reportPrivateUsage]
        _REPO_ROOT,
        pack="probe",
        skill=_PROBE_SKILL,
        plugin_name="lemmi-ai-kit-probe",
        display_name="Probe",
        description="A probe pack.",
        author=None,
        author_url=None,
    )

    found: set[str] = set()
    for path in _copied_sources().values():
        found |= {
            match.group(1)
            for match in cli._PLACEHOLDER_RE.finditer(  # pyright: ignore[reportPrivateUsage]
                path.read_text(encoding="utf-8")
            )
        }
    assert found, (
        "no placeholder found anywhere in the copied template. Either the template "
        "stopped using them or the probe stopped seeing them -- and this control is "
        "worthless until it is fixed."
    )

    unknown = sorted(found - set(subs))
    assert not unknown, (
        f"{cli.PACK_TEMPLATE} uses placeholder(s) `new-pack` cannot fill: {unknown}. "
        "Give them a value in _pack_substitutions, or drop them from the template."
    )

    sample = " ".join("{{" + name + "}}" for name in sorted(found))
    assert _hits(sample) == [], (
        f"a correct placeholder is being read as contamination: {_hits(sample)}"
    )
    assert _COUNT_CLAIM.search(sample) is None, (
        "a correct placeholder is being read as a skill count"
    )
