# Lemmi AI Kit Core

Development, planning, verification and the project learnings loop.

Install `lemmi-ai-kit-core@lemmi` with the host plugin manager. Skills are
canonical under this pack's `skills/`; do not copy them into a consuming project.

Project-specific rules and commands come from the consuming project's `AGENTS.md`.
Optional workflows in other packs are available only when those plugins are enabled.

## FFF file search

Core bundles [FFF v0.10.6](vendor/fff/README.md) and a shared [MCP declaration](.mcp.json)
for Claude and Codex. There is no separate FFF installation, PATH configuration or
FFF download on first use. The six bundled binaries cover macOS, Linux and Windows
on x64 and ARM64, adding about 78 MB to the plugin payload.

The launcher uses the kit's existing `uv` runtime, which must be available to the
agent client. `uv` selects Python 3.11 or newer and can fetch that Python runtime
if it is missing. The launcher selects the bundled FFF binary, verifies its SHA-256
checksum and starts it over stdio without changing the consuming working directory.
It fails explicitly for unsupported platforms or damaged/missing binaries.

Plugin updates own the FFF version; FFF's upstream startup update check is disabled.
FFF retains its normal user cache locations and Git-root discovery. Existing user-level
FFF registrations may take precedence over this plugin; removing such a registration
through the host's MCP manager opts into the bundled version.
