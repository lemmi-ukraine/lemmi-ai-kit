"""Launch the verified FFF binary bundled with this native plugin."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

_TARGETS = {
    ("Darwin", "arm64"): "aarch64-apple-darwin",
    ("Darwin", "x86_64"): "x86_64-apple-darwin",
    ("Linux", "arm64"): "aarch64-unknown-linux-musl",
    ("Linux", "x86_64"): "x86_64-unknown-linux-musl",
    ("Windows", "arm64"): "aarch64-pc-windows-msvc.exe",
    ("Windows", "x86_64"): "x86_64-pc-windows-msvc.exe",
}
_ARCH_ALIASES = {"aarch64": "arm64", "amd64": "x86_64"}


def binary_name(system: str, machine: str) -> str:
    architecture = machine.lower()
    architecture = _ARCH_ALIASES.get(architecture, architecture)
    target = _TARGETS.get((system, architecture))
    if target is None:
        raise ValueError(f"unsupported FFF platform: {system}/{machine}")
    return f"fff-mcp-{target}"


def verified_binary(vendor: Path, system: str, machine: str) -> Path:
    name = binary_name(system, machine)
    checksums: dict[str, str] = {}
    for line in (vendor / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, filename = line.split()
        checksums[filename] = digest
    expected = checksums[name]
    binary = vendor / name
    with binary.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"checksum mismatch for bundled {name}")
    return binary


def main() -> int:
    vendor = Path(__file__).resolve().parents[2] / "vendor" / "fff"
    try:
        binary = verified_binary(vendor, platform.system(), platform.machine())
        command = [str(binary), "--no-update-check", *sys.argv[1:]]
        # Keep the parent alive for FFF's parent-process watchdog on every host.
        return subprocess.run(command, check=False).returncode
    except (OSError, ValueError, KeyError) as error:
        print(f"Cannot start bundled FFF: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
