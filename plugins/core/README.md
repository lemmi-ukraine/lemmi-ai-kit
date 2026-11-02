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

## Flow mapping

Invoke `lemmi-ai-kit-core:flow-mapping` to document scenarios, callers, invariants
and cross-flow dependencies. The [skill](skills/flow-mapping/SKILL.md) includes
its schema, Python validation tools and synthetic self-check fixtures. Pass the
consumer project root and code directory; project documents and overrides stay
in the project. Existing installations need a Core update and a new agent session.

## Hooks

Core registers two `PreToolUse` command hooks in [hooks/hooks.json](hooks/hooks.json). Both start
their script through `uv`, which must be available to the agent client, as for the rest of Core.

| Hook | What it blocks | Default |
|---|---|---|
| `gate_learnings_drain` | Removing entries from `.ai/learnings.md` (an Edit, MultiEdit or Write that drops entries, or a shell call shaped like a rewrite or a removal of the file) while no approved consolidation plan is recorded for the day. Appending is never blocked. | Registered whenever Core is enabled; there is no switch. |
| `gate_shell_prefix` | Shell calls (the Bash and PowerShell tools) that move the persistent working directory, start with a variable assignment, or shadow `cd`. | Off by default: it does nothing until a project switches it on. |

### The shell-prefix hook

A prefix in front of a command defeats the permission rules that match on the bare command, and the
shell tools keep one working directory across calls, so one `cd` re-bases every later call. When a
project switches the hook on, it refuses three families of call, each with its own message:

- a move: `cd`, `pushd`, `Set-Location` or `Push-Location` to an absolute, home, variable or
  unreadable target, in any statement of the command (not only the first), and `cd` with no target;
- a shadow: a function, `function` keyword or alias that redefines `cd`;
- a leading assignment: `NAME=value` and its disguises `export`, `readonly`, `declare -x`,
  `env NAME=value` and, in PowerShell, `$env:NAME = value`.

It is off by default because a default that suits one project breaks another: a project whose own
instructions tell sessions to start a command with an assignment or a `cd` would have them refused.
Read your project's instructions before switching it on.

The switch is a file in the project, `.ai/shell-prefix-hook.json`, read on every call. Every key is
optional:

| Key | Meaning | Default |
|---|---|---|
| `enabled` | `true` switches the hook on; `false`, or no file, and it does nothing. Any other value makes the file unusable: the call is allowed and one warning per call says so. | `false` |
| `deny_relative_cd` | Also refuse a relative target for `cd`, `pushd` and `chdir`. `cd .` stays allowed. | `false` |
| `deny_set_location` | Also refuse a relative target for `Set-Location`, `sl` and `Push-Location`. | `false` |
| `deny_powershell_assignment` | Also refuse a leading `$name = value` in the PowerShell tool. | `false` |
| `allowed_forms` | A list of `{tool, folder, then}`: the one shape a strict project lets through although it starts with `cd`. | none |

Each option names the spelling it governs, so a project that wants no relative moves sets both
`deny_relative_cd` and `deny_set_location`. A lax project is `{"enabled": true}`: a relative `cd`
stays allowed. A strict project allows a `cd` into one named folder, followed by `&&` and a build
command word, and refuses every other call that starts with `cd`, `Set-Location`, `NAME=value` or a
variable assignment (`app-dir` and `build-tool` are placeholders):

```json
{
  "enabled": true,
  "deny_relative_cd": true,
  "deny_set_location": true,
  "deny_powershell_assignment": true,
  "allowed_forms": [
    { "tool": "Bash", "folder": "app-dir", "then": ["build-tool"] }
  ]
}
```

The folder is spelled relative to the project root or by its absolute path; separators, a trailing
slash and the case of a drive letter are normalised, `..` is never resolved, and the form must open
the command (later statements are judged on their own). A file the hook cannot use never blocks a
call and never passes in silence: the call is allowed and one warning message per call says what is
wrong with the file. The module docstring of `hooks/gate_shell_prefix.py` lists every shape the hook
deliberately does not cover.

A hook wired into a settings file reached windows that were already open, on their next call, in one
recorded case in another consumer: the delay was not timed, and for a plugin registration it is
unmeasured. So flip the switch when no peer session is mid-task. The hooks reference says: "Direct
edits to hooks in settings files are normally picked up automatically by the file watcher." It gives
no delay and says nothing about a plugin's own hooks file. This design differs in the part that
matters: the switch file is read on every call, so turning it on or off reaches every window that
already has the hook registered on its next shell call.

### Registration

A plugin update's new registration is not assumed to reach a window that is already open: restart
it. The plugin documentation says the running session keeps the versions it already loaded, that the
next session loads the update, and that `/reload-plugins` loads a change into a session that is
already open. The hooks reference says nothing about when a plugin's hooks file takes effect in an
open window, and loading these registrations with `/reload-plugins` was not tried here, so a new
session is the safe assumption.

The Codex manifest declares no hooks, which is not the same as no hooks for Codex. Codex's plugin
documentation says Codex "discovers `hooks/hooks.json` by default" when the plugin's manifest does
not define hooks, that it skips a plugin's hooks "until the user reviews and trusts the current hook
definition", and that it "also sets `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` for compatibility
with existing plugin hooks". Both hooks may therefore be offered to a Codex user. They have not been
run in Codex here, so whether they work there, with Codex's own tool names and payloads, is not
established.

Both registrations fail open. Without care, a missing script (a moved plugin folder, an update that
renamed a file) makes Python exit 2, and the hooks reference says "Exit with code 2 to block the
action", so every call the matcher covers would be blocked. Each command is therefore a short launcher:
it checks that the script file exists, runs it with `runpy` when it does, and ends with
`exit $LASTEXITCODE`, which passes the script's own exit code on in POSIX shells (where the variable
is empty and `exit` reports the last command's status) and in PowerShell (whose `-Command` otherwise
reports 1 where the script exited 2). With the script missing the command exits 0 and prints nothing
in sh, Git Bash and PowerShell; with it present, its own output and exit code reach the harness
unchanged. The launcher runs under `python -P`, which keeps the working directory off the import
path: with `-c` alone, a file named `json.py` in the project would be run in place of the module. The
same flag keeps the script's own folder off the import path, so a hook script is one file that
imports only the standard library: a sibling module would not be found, the script would exit 1
(a non-blocking failure, except on Windows without Git Bash, see below) and the hook would go quiet.
A test pins that for both scripts.

Not protected: `uv` itself. A `uv` that is not on the `PATH` is a shell error: 127 in a POSIX shell,
which the hooks reference counts as a non-blocking failure, and 0 in PowerShell, because the tail
passes on a `$LASTEXITCODE` that `uv` never set. A `uv` that starts but cannot do its job exits 2,
which blocks every call the matcher covers: no Python 3.11 or newer, a cache folder it cannot use
and a configuration file it cannot read each gave exit 2 when tried. On Windows without Git Bash the
hooks reference says "only exit code 0 or 2 counts as this hook's verdict", so there a crash, a
script that does not compile or a timeout blocks the call as well. The `onFailure` field (`"continue"`
or `"block"`, Claude Code v2.1.295 or later) says whether the action goes ahead when a hook fails;
Core sets neither value, and choosing one is left to whoever deploys it.
