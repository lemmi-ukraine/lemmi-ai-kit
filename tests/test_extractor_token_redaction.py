"""A GitHub token is redacted wherever it sits, and the leak gate sees one that was not.

The extractor's KEY/TOKEN assignment pattern masks a token only where such a name sits right
before "=" or ":". A GitHub token after a command-line flag, or in an "Authorization: token"
header, reached the output as it was, and the leak gate that --self-check and --check-file share
(check_file) could not see it, because no pattern in either list was keyed to the token's shape.
The shapes and the pages they come from are in the comment above GITHUB_PREFIXED_TOKEN_RE in
extract_sessions.py.

Four kinds of fixture: one per POSITION a token was seen to survive in, one per documented
SHAPE, CONTROLS that worked before the shapes were added (green on the old code too, which
proves the loader before any red is trusted), and NEGATIVES shaped like real text that a pattern
too wide would rewrite. Every fake token is joined from fragments at run time: no file in the
repository holds a contiguous one, only the code that makes one. A failing assertion prints each
long run of letters and digits as its length, so it never prints a token either.
"""

import base64
import importlib.util
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXTRACTOR = (
    _REPO_ROOT
    / "plugins"
    / "core"
    / "skills"
    / "session-retrospective"
    / "scripts"
    / "extract_sessions.py"
)


def _load(script: Path, name: str) -> ModuleType:
    """Import a script by path, without leaving bytecode inside the pack payload."""
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


_EXTRACT = _load(_EXTRACTOR, "extract_sessions_token_redaction")
_redact = cast(Callable[[str], str], _EXTRACT.redact)
_check_file = cast(Callable[[Path], list[str]], _EXTRACT.check_file)

_MARK = "[REDACTED_GITHUB_TOKEN]"
_FILL = "Qz7Wm4"  # letters and digits, none of them hex, so the hex rule never reads a run of it
_LONG_RUN = re.compile(r"[A-Za-z0-9]{12,}")


def _run(length: int) -> str:
    """A run of `length` base62 characters."""
    return (_FILL * (length // len(_FILL) + 1))[:length]


def _shown(text: str) -> str:
    """`text` with each long run of letters and digits replaced by its length."""
    return _LONG_RUN.sub(lambda match: f"<{len(match.group(0))} chars>", text)


def _base64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


# The prefixes GitHub documents under "GitHub's token formats" (docs.github.com).
_PREFIXES = {
    "classic": "ghp_",
    "oauth": "gho_",
    "app-user": "ghu_",
    "app-installation": "ghs_",
    "app-refresh": "ghr_",
}
_FINE_GRAINED = "github_pat_"
_SHAPES = (*_PREFIXES, "fine-grained", "fine-grained-unbroken")


def _token(shape: str, length: int = 36) -> str:
    """A fake token of `shape`, joined at run time."""
    if shape == "fine-grained":
        # GitHub documents this prefix and nothing more. The body holds an underscore because
        # GitHub's token alphabet allows one; the 22/59 split is the commonly cited one, which no
        # GitHub page confirms, and the pattern does not depend on it.
        return _FINE_GRAINED + _run(22) + "_" + _run(59)
    if shape == "fine-grained-unbroken":
        return _FINE_GRAINED + _run(length)
    return _PREFIXES[shape] + _run(length)


# A stateless installation token is a ghs_-prefixed JWT (GitHub changelog, 2026-05-15); the docs
# also show it as ghs_APPID_JWT. The JWT pattern masks both forms, so they are controls here.
_JWT = ".".join(
    (
        _base64url('{"alg":"RS256","typ":"JWT"}'),
        _base64url('{"iss":"12345"}'),
        _run(342),
    )
)

# position -> (shape, text around the token, whether the new marker replaces exactly the token)
_POSITIONS: dict[str, tuple[str, str, bool]] = {
    "classic-after-a-flag": (
        "classic",
        "docker login ghcr.io -u octocat -p {token}",
        True,
    ),
    "classic-in-an-authorization-token-header": (
        "classic",
        'curl -H "Authorization: token {token}" https://api.github.com/user',
        True,
    ),
    "fine-grained-after-a-flag": (
        "fine-grained",
        "git push --token {token} origin main",
        True,
    ),
    # The bearer pattern runs first and owns this replacement; what was missing here is the leak
    # gate, which could not see the token in the text before redaction.
    "classic-in-an-authorization-bearer-header": (
        "classic",
        'curl -H "Authorization: Bearer {token}" https://api.github.com/user',
        False,
    ),
}

# control -> (the secret, the raw text, whether the leak gate must see the raw text)
_CONTROLS: dict[str, tuple[str, str, bool]] = {
    "bare-key-with-the-sk-prefix": ("sk-" + _run(24), "key {secret} end", True),
    "assignment-to-a-token-name": (
        _token("classic"),
        "export GITHUB_TOKEN={secret}",
        False,
    ),
    "url-userinfo-after-x-access-token": (
        _token("classic"),
        "git clone https://x-access-token:{secret}@github.com/owner/repo.git",
        False,
    ),
    "stateless-installation-token": (_JWT, "use ghs_{secret} now", True),
    "stateless-installation-token-with-an-app-id": (
        _JWT,
        "use ghs_12345_{secret} now",
        True,
    ),
}

_HYPHENATED = "Qz7-" * 9  # 36 characters, with a hyphen that no GitHub token body holds
_NEGATIVES: dict[str, str] = {
    "branch-name-with-the-classic-prefix": "git checkout -b fix/ghp_rotation-and-expiry",
    "branch-name-with-the-fine-grained-prefix": (
        "git push origin feature/github_pat_expiry-warning"
    ),
    "prose-that-names-the-prefixes": (
        "Classic tokens start with ghp_ and fine-grained ones with github_pat_."
    ),
    # longer than the minimum after the prefix, with no uppercase letter: only the lookahead
    # refuses it, and it is joined at run time so the source holds no long prefixed name
    "snake-case-name-with-the-fine-grained-prefix": "def test_"
    + _FINE_GRAINED
    + "_".join(("expiration", "notification", "settings", "page"))
    + "():",
    "file-name-with-the-installation-prefix": (
        "edited src/ghs_installation_token_refresh_handler.py"
    ),
    "uuid-after-the-installation-prefix": "ghs_0f8e2a4c-6b1d-4e3f-9a7b-5c2d1e0f3a4b",
    "letter-before-the-classic-prefix": "x" + _token("classic"),
    "digit-before-the-classic-prefix": "7" + _token("classic"),
    "letters-before-the-fine-grained-prefix": "my" + _token("fine-grained"),
    **{
        f"one-character-short-{shape}": f"login -p {_token(shape, 35)} done"
        for shape in (*_PREFIXES, "fine-grained-unbroken")
    },
    **{
        f"wrong-alphabet-{shape}": f"login -p {prefix}{_HYPHENATED} done"
        for shape, prefix in (*_PREFIXES.items(), ("fine-grained", _FINE_GRAINED))
    },
}


def _every_fixture() -> dict[str, str]:
    fixtures = {
        f"position-{name}": template.format(token=_token(shape))
        for name, (shape, template, _) in _POSITIONS.items()
    }
    fixtures |= {
        f"shape-{shape}": f"login -p {_token(shape)} done" for shape in _SHAPES
    }
    fixtures |= {
        f"control-{name}": raw.format(secret=secret)
        for name, (secret, raw, _) in _CONTROLS.items()
    }
    fixtures |= {f"negative-{name}": text for name, text in _NEGATIVES.items()}
    return fixtures


_EVERY_FIXTURE = _every_fixture()


def _leaks(tmp_path: Path, text: str) -> int:
    """How many findings the leak gate reports for a digest holding `text`."""
    digest = tmp_path / "digest.md"
    digest.write_text(f"USER: {text}\n", encoding="utf-8", newline="\n")
    return len(_check_file(digest))


def test_the_fixture_tables_are_the_ones_the_tests_state() -> None:
    """The surface in numbers: a fixture that drops out of a table cannot pass unseen."""
    assert sorted(_PREFIXES.values()) == ["gho_", "ghp_", "ghr_", "ghs_", "ghu_"]
    assert len(_SHAPES) == 7
    assert len(_POSITIONS) == 4
    assert len(_CONTROLS) == 5
    assert len(_NEGATIVES) == 21
    assert len(_EVERY_FIXTURE) == 4 + 7 + 5 + 21


@pytest.mark.parametrize("position", sorted(_POSITIONS))
def test_a_github_token_is_redacted_at_each_position(position: str) -> None:
    shape, template, exact = _POSITIONS[position]
    token = _token(shape)
    out = _redact(template.format(token=token))
    survived = token in out
    assert not survived, f"the token survived redaction: {_shown(out)!r}"
    if exact:
        assert out == template.format(token=_MARK)
    else:
        assert "[REDACTED]" in out


@pytest.mark.parametrize("position", sorted(_POSITIONS))
def test_the_leak_gate_sees_a_github_token_at_each_position(
    position: str, tmp_path: Path
) -> None:
    shape, template, _ = _POSITIONS[position]
    raw = template.format(token=_token(shape))
    seen = _leaks(tmp_path, raw)
    assert seen > 0, "the leak gate did not see the token in the text before redaction"
    left = _leaks(tmp_path, _redact(raw))
    assert left == 0, f"the leak gate flagged the redacted text {left} time(s)"


@pytest.mark.parametrize("shape", _SHAPES)
def test_every_documented_shape_is_redacted_and_seen_by_the_leak_gate(
    shape: str, tmp_path: Path
) -> None:
    token = _token(shape)
    out = _redact(f"login -p {token} done")
    survived = token in out
    assert not survived, f"the token survived redaction: {_shown(out)!r}"
    assert out == f"login -p {_MARK} done"
    seen = _leaks(tmp_path, f"login -p {token} done")
    assert seen > 0, "the leak gate did not see the token in the text before redaction"


@pytest.mark.parametrize("control", sorted(_CONTROLS))
def test_a_control_that_worked_before_the_shapes_still_does(
    control: str, tmp_path: Path
) -> None:
    secret, raw, gate_sees_raw = _CONTROLS[control]
    raw = raw.format(secret=secret)
    out = _redact(raw)
    survived = secret in out
    assert not survived, f"the secret survived redaction: {_shown(out)!r}"
    if gate_sees_raw:
        seen = _leaks(tmp_path, raw)
        assert seen > 0, (
            "the leak gate did not see the secret in the text before redaction"
        )
    left = _leaks(tmp_path, out)
    assert left == 0, f"the leak gate flagged the redacted text {left} time(s)"


@pytest.mark.parametrize("negative", sorted(_NEGATIVES))
def test_text_that_only_resembles_a_github_token_is_left_alone(
    negative: str, tmp_path: Path
) -> None:
    text = _NEGATIVES[negative]
    out = _redact(text)
    unchanged = out == text
    assert unchanged, f"rewritten: {_shown(text)!r} -> {_shown(out)!r}"
    flagged = _leaks(tmp_path, text)
    assert flagged == 0, f"the leak gate flagged it {flagged} time(s)"


@pytest.mark.parametrize("fixture", sorted(_EVERY_FIXTURE))
def test_redacting_twice_changes_nothing(fixture: str) -> None:
    once = _redact(_EVERY_FIXTURE[fixture])
    stable = _redact(once) == once
    assert stable, f"a second pass changed {_shown(once)!r}"
