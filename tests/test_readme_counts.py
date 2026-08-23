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
"""

import json
import re
from pathlib import Path
from typing import Any, cast

from lemmi_ai_kit.manifest import load_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# "29 skills", "all 29 skills", and the rot-prone "30+ skills" form.
_COUNT_CLAIM = re.compile(r"(\d+)(\+?)\s+skills\b")

# Manifests whose prose is indexed by a marketplace, so it must carry no count.
_MANIFEST_FILES: tuple[str, ...] = (
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    "plugins/core/.claude-plugin/plugin.json",
    "plugins/core/.codex-plugin/plugin.json",
    "plugins/python/.claude-plugin/plugin.json",
    "plugins/python/.codex-plugin/plugin.json",
)


def _shipped_skill_count() -> int:
    return len(load_manifest().skills)


def test_every_readme_skill_count_matches_the_manifest() -> None:
    text = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
    expected = _shipped_skill_count()

    problems: list[str] = []
    found = 0
    for match in _COUNT_CLAIM.finditer(text):
        found += 1
        line = text.count("\n", 0, match.start()) + 1
        claimed, approx = int(match.group(1)), match.group(2)
        if approx:
            problems.append(
                f"README.md:{line}: {match.group(0)!r} is an approximate count — "
                "state the exact number so this test can hold it, or drop it entirely"
            )
        elif claimed != expected:
            problems.append(
                f"README.md:{line}: claims {claimed} skills, manifest ships {expected}"
            )

    assert not problems, "\n".join(problems)
    assert found > 0, (
        "no skill count found in README.md. If the count was deliberately removed "
        "that is fine — delete this assertion. It exists so the check cannot pass "
        "vacuously after a rewrite silently drops the number."
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
