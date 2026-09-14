"""Bundled FFF selection, integrity and launch without a system FFF install."""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lemmi_ai_kit.fff import binary_name, verified_binary

_PLUGIN = Path(__file__).resolve().parents[1] / "plugins" / "core"
_VENDOR = _PLUGIN / "vendor" / "fff"
_PLATFORMS = (
    ("Darwin", "arm64", "aarch64-apple-darwin"),
    ("Darwin", "x86_64", "x86_64-apple-darwin"),
    ("Linux", "aarch64", "aarch64-unknown-linux-musl"),
    ("Linux", "x86_64", "x86_64-unknown-linux-musl"),
    ("Windows", "ARM64", "aarch64-pc-windows-msvc.exe"),
    ("Windows", "AMD64", "x86_64-pc-windows-msvc.exe"),
)


@pytest.mark.parametrize(("system", "machine", "target"), _PLATFORMS)
def test_every_supported_platform_resolves_to_a_verified_release_binary(
    system: str, machine: str, target: str
) -> None:
    binary = verified_binary(_VENDOR, system, machine)
    assert binary.name == f"fff-mcp-{target}"
    if not target.endswith(".exe") and os.name != "nt":
        assert os.access(binary, os.X_OK)


def test_checksum_inventory_covers_every_bundled_binary() -> None:
    listed = {
        line.split()[1] for line in (_VENDOR / "SHA256SUMS").read_text().splitlines()
    }
    actual = {path.name for path in _VENDOR.glob("fff-mcp-*")}
    assert listed == actual == {f"fff-mcp-{target}" for _, _, target in _PLATFORMS}


def test_unsupported_platform_does_not_fall_back_to_a_system_binary() -> None:
    for system, machine in (("FreeBSD", "x86_64"), ("Linux", "riscv64")):
        with pytest.raises(ValueError, match="unsupported FFF platform"):
            binary_name(system, machine)


def test_missing_and_corrupt_payloads_fail_before_execution(tmp_path: Path) -> None:
    name = binary_name("Darwin", "arm64")
    content = b"verified fixture"
    (tmp_path / "SHA256SUMS").write_text(
        f"{hashlib.sha256(content).hexdigest()}  {name}\n"
    )
    with pytest.raises(FileNotFoundError):
        verified_binary(tmp_path, "Darwin", "arm64")
    binary = tmp_path / name
    binary.write_bytes(content)
    assert verified_binary(tmp_path, "Darwin", "arm64") == binary
    binary.write_bytes(b"corrupted fixture")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verified_binary(tmp_path, "Darwin", "arm64")


def test_copied_launcher_runs_without_fff_on_path(tmp_path: Path) -> None:
    try:
        name = binary_name(platform.system(), platform.machine())
    except ValueError:
        pytest.skip("the executing host is outside FFF's supported platforms")
    copied = tmp_path / "plugin cache with spaces"
    launcher = copied / "src" / "lemmi_ai_kit" / "fff.py"
    launcher.parent.mkdir(parents=True)
    shutil.copy2(_PLUGIN / "src" / "lemmi_ai_kit" / "fff.py", launcher)
    vendor = copied / "vendor" / "fff"
    vendor.mkdir(parents=True)
    shutil.copy2(_VENDOR / name, vendor / name)
    shutil.copy2(_VENDOR / "SHA256SUMS", vendor / "SHA256SUMS")
    environment = os.environ.copy()
    environment["PATH"] = ""
    uv = shutil.which("uv")
    assert uv is not None
    result = subprocess.run(
        [
            uv,
            "run",
            "--offline",
            "--no-project",
            "--python",
            sys.executable,
            "python",
            "-B",
            str(launcher),
            "--version",
        ],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.stdout.startswith("fff-mcp 0.10.6"), result.stdout
