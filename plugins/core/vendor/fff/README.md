# Bundled FFF MCP server

These are unmodified binaries from [FFF v0.10.6](https://github.com/dmtrKovalenko/fff/releases/tag/v0.10.6).
The [upstream source](https://github.com/dmtrKovalenko/fff/tree/v0.10.6) is licensed
under the included MIT [LICENSE](LICENSE). `SHA256SUMS` contains the release asset
digests, also pinned in the upstream installation scripts.

The six targets cover macOS, Linux and Windows on x64 and ARM64. Linux uses the
static musl builds. The Core launcher selects and checks the appropriate file;
it never downloads or installs FFF. Native plugin updates distribute version changes.

To update, replace all six binaries from one official release, compare their hashes
with that release's published digests, refresh `SHA256SUMS` and this version record,
and preserve the release's license. Keep POSIX binaries executable and the binary Git
attributes intact. Run the launcher/payload tests and a native-host MCP smoke check
before updating the plugin version. A checksum proves byte identity, not execution
compatibility on a platform that was not tested.
