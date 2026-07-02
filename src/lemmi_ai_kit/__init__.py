"""lemmi-ai-kit — deploy Lemmi's shared AI configuration into any project."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lemmi-ai-kit")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0+unknown"
