# Optional packs and native installation

Use the host plugin manager. Recommend only capability groups the user needs;
there is no kit selection file, preset engine, or separate installer.

| Plugin | Provides | Prerequisite |
|---|---|---|
| `lemmi-ai-kit-core` | Setup, development planning, verification and project learnings | None |
| `lemmi-ai-kit-research` | Source planning, ownership and parallel research | None |
| `lemmi-ai-kit-orchestration` | Delegation, initiatives, stacked-work coordination and reviews | Core 0.2.0 or newer |
| `lemmi-ai-kit-skill-authoring` | Research, create and review reusable skills | Core 0.2.0 or newer |
| `lemmi-ai-kit-python` | Python coding and testing conventions | None |

Language packs remain optional. A project with another language can use core,
research or orchestration without installing Python conventions. Do not invent
an unavailable language pack.

## Commands

Register the marketplace once. In a local checkout of the kit use `./` for Claude
and `.` for Codex. Git-based registration uses the kit repository URL. Then print
only the installation lines for the chosen groups; all groups means all five lines.

```sh
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
claude plugin install lemmi-ai-kit-research@lemmi
claude plugin install lemmi-ai-kit-orchestration@lemmi
claude plugin install lemmi-ai-kit-skill-authoring@lemmi
claude plugin install lemmi-ai-kit-python@lemmi
```

```sh
codex plugin marketplace add .
codex plugin add lemmi-ai-kit-core@lemmi
codex plugin add lemmi-ai-kit-research@lemmi
codex plugin add lemmi-ai-kit-orchestration@lemmi
codex plugin add lemmi-ai-kit-skill-authoring@lemmi
codex plugin add lemmi-ai-kit-python@lemmi
```

Claude declares core as a native versioned dependency for authoring and
orchestration. On Codex install or update core first; no custom resolver does it.
Research and Python do not require core. Use the host's native project/user scope
and enable/disable controls instead of copying skills into a project.

## Upgrade from the previously bundled core

Version 0.2.0 moves research, orchestration and skill-authoring out of core. A user
who wants all previously bundled capabilities installs those three plugins too.
Moved skill invocations now use their owning plugin namespace, for example
`/lemmi-ai-kit-research:parallel-deep-research`. Do not leave local duplicates as
aliases for the old core namespace.

## Verify

Read the native plugin inventory after installation. Claude's component inventory
is available with `claude plugin details lemmi-ai-kit-research`; Codex reports
installed and enabled plugins with `codex plugin list`. Verify expected skill files
in the path returned by the host. Installation/update does not refresh an already
running model's skill catalog; use a fresh session for the new groups.
