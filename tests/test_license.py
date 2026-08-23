"""The license claim cannot drift from the license file.

Before this test existed, both plugin manifests declared `"license": "MIT"` and no
LICENSE file was in the repo, while `pyproject.toml` declared no license at all —
three sources, two wrong, nothing catching it. A legal review looks for the file.
"""

import tomllib
from pathlib import Path
from typing import Any, cast

_REPO_ROOT = Path(__file__).resolve().parents[1]

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


def _pyproject() -> dict[str, Any]:
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return cast(dict[str, Any], tomllib.loads(text)["project"])


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
    """All three declarations must agree with LICENSE. Names the ones that don't."""
    import json

    expected = _declared_spdx()
    declarations: dict[str, str | None] = {}

    for relative in (
        "plugins/core/.claude-plugin/plugin.json",
        "plugins/core/.codex-plugin/plugin.json",
        "plugins/python/.claude-plugin/plugin.json",
        "plugins/python/.codex-plugin/plugin.json",
    ):
        data = cast(
            dict[str, Any],
            json.loads((_REPO_ROOT / relative).read_text(encoding="utf-8")),
        )
        declarations[relative] = cast("str | None", data.get("license"))

    declarations["pyproject.toml"] = cast("str | None", _pyproject().get("license"))

    mismatches = [
        f"{source}: declares {value!r}, LICENSE is {expected!r}"
        for source, value in declarations.items()
        if value != expected
    ]
    assert not mismatches, (
        "license declarations out of sync with LICENSE:\n" + "\n".join(mismatches)
    )


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
