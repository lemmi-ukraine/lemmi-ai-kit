"""lemmi-ai-kit — Lemmi's shared AI configuration (Claude Code / Codex plugin) support code."""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, cast


def pyproject_fallback() -> dict[str, Any]:
    """[project] table when running uninstalled from a source tree / plugin cache."""
    path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    project = data.get("project")
    return cast(dict[str, Any], project) if isinstance(project, dict) else {}


try:
    __version__ = version("lemmi-ai-kit")
except PackageNotFoundError:  # running from a source tree without installation
    _fallback = pyproject_fallback().get("version")
    __version__ = _fallback if isinstance(_fallback, str) else "0.0.0+unknown"
