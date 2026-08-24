"""The license claim cannot drift from the license file.

Before this test existed, both plugin manifests declared `"license": "MIT"` and no
LICENSE file was in the repo, while `pyproject.toml` declared no license at all —
three sources, two wrong, nothing catching it. A legal review looks for the file.

**The set it checks is now derived, and that is the second defect this file has
had.** Until 2026-08-24 the four pack manifests were written out by hand here. That
was correct for exactly as long as there were four, and `new-pack` (I4 D15) makes a
fifth a single command away — a pack whose license claim nothing would have read,
in a file whose whole subject is a claim nothing reads. The list now comes from
`publish.payload_roots()`, the same marketplace-derived payload the pre-publish
guard uses, so a pack reaches this check by being listed rather than by being
remembered.

Deriving it moves the failure mode rather than removing it, so both halves are
controlled: `test_a_pack_added_after_this_was_written_cannot_escape` builds a
synthetic checkout carrying a pack this file has never heard of, with a
deliberately wrong license, and asserts it is caught AND named. A guard that has
only ever been shown to pass has not been shown to work.

`tests/test_readme_counts.py:78` still hand-enumerates the same six manifest paths
for its own check, and has the same escape. It is not this file's to change.
"""

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest

from lemmi_ai_kit import publish

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Both hosts' manifest directories inside one payload root. A pack may legitimately
# carry only one -- the two marketplaces are read and unioned, so a pack listed to a
# single host still ships to that host -- but carrying NEITHER is unmeasurable, and
# `_declarations` fails rather than skipping it.
_PLUGIN_MANIFEST_DIRS: tuple[str, ...] = (".claude-plugin", ".codex-plugin")

# The SPDX identifier every declaration must agree on, derived from LICENSE itself
# rather than hardcoded — change the file and this test tells you what else to update.
_SPDX_BY_TITLE: dict[str, str] = {
    "MIT License": "MIT",
    "Apache License": "Apache-2.0",
    "BSD 3-Clause License": "BSD-3-Clause",
    "BSD 2-Clause License": "BSD-2-Clause",
    "GNU General Public License": "GPL-3.0-only",
    "Mozilla Public License": "MPL-2.0",
}


def _license_path() -> Path:
    return _REPO_ROOT / "LICENSE"


def _license_text() -> str:
    return _license_path().read_text(encoding="utf-8")


def _declared_spdx() -> str:
    """The SPDX id implied by the LICENSE file's own title line."""
    title = _license_text().strip().splitlines()[0].strip()
    for prefix, spdx in _SPDX_BY_TITLE.items():
        if title.startswith(prefix):
            return spdx
    raise AssertionError(
        f"LICENSE opens with {title!r}, which maps to no known SPDX id. "
        f"Add it to _SPDX_BY_TITLE if the license changed deliberately."
    )


def _pyproject(root: Path = _REPO_ROOT) -> dict[str, Any]:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    return cast(dict[str, Any], tomllib.loads(text)["project"])


def _declarations(root: Path) -> dict[str, str | None]:
    """Every license declaration in `root`, keyed by the file that makes it.

    The payload roots come from the marketplace manifests rather than from a list
    here, which is what stops a pack added later from being silently unchecked.
    """
    declarations: dict[str, str | None] = {}
    for payload in publish.payload_roots(root):
        found = False
        for host in _PLUGIN_MANIFEST_DIRS:
            relative = f"{payload}/{host}/plugin.json"
            path = root / relative
            if not path.is_file():
                continue
            found = True
            data = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
            declarations[relative] = cast("str | None", data.get("license"))
        # Cannot-measure is never clean: a payload the marketplace advertises but
        # whose manifest cannot be found is the shape of failure this file exists
        # to have caught the first time.
        assert found, (
            f"{payload} is listed as a plugin payload but carries no plugin.json "
            f"under {' or '.join(_PLUGIN_MANIFEST_DIRS)}, so its license claim "
            "cannot be read at all"
        )

    declarations["pyproject.toml"] = cast("str | None", _pyproject(root).get("license"))
    return declarations


def _mismatches(declarations: Mapping[str, str | None], expected: str) -> list[str]:
    """The rule itself, over a mapping, so it can be exercised on input this repo lacks.

    `Mapping`, not `dict`: a control that has to build a `dict[str, str | None]` to be
    accepted cannot pass the plain `dict[str, str]` a caller would naturally write, and
    the friction lands on the tests that exist to feed it bad input.
    """
    return [
        f"{source}: declares {value!r}, LICENSE is {expected!r}"
        for source, value in declarations.items()
        if value != expected
    ]


def test_license_file_exists_and_is_substantive() -> None:
    path = _license_path()
    assert path.is_file(), "LICENSE is missing — every manifest below claims one"
    text = _license_text()
    assert len(text.split()) > 100, "LICENSE looks like a stub, not a license"
    # Guard against a title-only file that would satisfy the drift check below.
    assert "Copyright (c)" in text, "LICENSE has no copyright line"
    assert "WITHOUT WARRANTY" in text.upper(), "LICENSE has no warranty disclaimer"


def test_license_names_a_copyright_holder_matching_the_package_author() -> None:
    copyright_line = next(
        line for line in _license_text().splitlines() if "Copyright (c)" in line
    )
    authors = cast(list[dict[str, str]], _pyproject()["authors"])
    holder = authors[0]["name"]
    assert holder in copyright_line, (
        f"LICENSE copyright line {copyright_line.strip()!r} does not name "
        f"the package author {holder!r} from pyproject.toml"
    )


def test_every_license_declaration_matches_the_license_file() -> None:
    """Every declaration must agree with LICENSE. Names the ones that don't."""
    mismatches = _mismatches(_declarations(_REPO_ROOT), _declared_spdx())
    assert not mismatches, (
        "license declarations out of sync with LICENSE:\n" + "\n".join(mismatches)
    )


def test_the_derived_set_covers_every_pack_this_repo_actually_ships() -> None:
    """Guard the guard: derivation that returned nothing would pass vacuously."""
    declarations = _declarations(_REPO_ROOT)
    manifests = [source for source in declarations if source != "pyproject.toml"]

    payloads = publish.payload_roots(_REPO_ROOT)
    assert len(payloads) >= 2, f"only {len(payloads)} payload root(s) derived"
    assert len(manifests) >= 2 * len(payloads), (
        "fewer manifests than payload roots x hosts, so a pack is being skipped:\n"
        + "\n".join(sorted(manifests))
    )
    for payload in payloads:
        assert any(source.startswith(f"{payload}/") for source in manifests), payload


def test_the_drift_check_catches_a_wrong_declaration() -> None:
    """Positive control on the comparison, independent of what is on disk."""
    good = {"plugins/core/.claude-plugin/plugin.json": "MIT"}
    bad = {"plugins/other/.codex-plugin/plugin.json": "Apache-2.0"}

    assert _mismatches(good, "MIT") == []
    caught = _mismatches({**good, **bad}, "MIT")
    assert len(caught) == 1
    assert "plugins/other/.codex-plugin/plugin.json" in caught[0]
    # A missing `license` key is a mismatch, not a pass. It was the original defect.
    assert _mismatches({"pyproject.toml": None}, "MIT")


def test_a_pack_added_after_this_was_written_cannot_escape(tmp_path: Path) -> None:
    """Positive control on the DERIVATION: the failure the hand-written list had.

    `new-pack` makes a fifth pack one command away. Against the four paths this file
    used to name, the pack below declares the wrong license and the suite stays
    green — which is the whole reason the list is derived now. So the control is a
    checkout containing a pack this file has never heard of, and the assertion is
    that it is both seen and named.
    """
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.0.1"\nlicense = "MIT"\n',
        encoding="utf-8",
    )
    claude: dict[str, Any] = {
        "plugins": [
            {"name": "fixture-core", "source": "./plugins/core"},
            {"name": "fixture-new", "source": "./plugins/newpack"},
        ]
    }
    codex: dict[str, Any] = {
        "plugins": [
            {
                "name": "fixture-new",
                "source": {"source": "local", "path": "./plugins/newpack"},
            }
        ]
    }
    for relative, data in (
        (".claude-plugin/marketplace.json", claude),
        (".agents/plugins/marketplace.json", codex),
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    for payload, spdx in (("core", "MIT"), ("newpack", "Apache-2.0")):
        for host in _PLUGIN_MANIFEST_DIRS:
            path = tmp_path / "plugins" / payload / host / "plugin.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"license": spdx}), encoding="utf-8")

    declarations = _declarations(tmp_path)
    assert "plugins/newpack/.claude-plugin/plugin.json" in declarations, (
        "the derivation did not see the new pack at all -- this is the exact miss "
        "the hand-written list had"
    )

    caught = _mismatches(declarations, "MIT")
    assert len(caught) == 2, caught
    assert all("newpack" in problem for problem in caught)


def test_a_payload_with_no_manifest_fails_rather_than_being_skipped(
    tmp_path: Path,
) -> None:
    """Positive control on the cannot-measure rule: an advertised pack with nothing
    to read must fail, because skipping it renders as a pass."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.0.1"\nlicense = "MIT"\n',
        encoding="utf-8",
    )
    path = tmp_path / ".claude-plugin" / "marketplace.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"plugins": [{"name": "ghost", "source": "./plugins/ghost"}]}),
        encoding="utf-8",
    )
    (tmp_path / "plugins" / "ghost").mkdir(parents=True)

    with pytest.raises(AssertionError, match="carries no plugin.json"):
        _declarations(tmp_path)


def test_pyproject_ships_the_license_file_in_the_distribution() -> None:
    """Without this, the built wheel and sdist carry no license at all."""
    license_files = cast("list[str] | None", _pyproject().get("license-files"))
    assert license_files, (
        "pyproject.toml declares no license-files, so the built wheel ships "
        "without the LICENSE file even though the metadata names a license"
    )
    for pattern in license_files:
        assert (_REPO_ROOT / pattern).is_file(), (
            f"license-files lists {pattern!r}, which does not exist"
        )
