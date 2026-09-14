# Migrating to 0.2.0

Version 0.2.0 splits the former Core pack into optional native plugin families.
Core still provides project setup, specs, review and learnings, while Research,
Orchestration and Skill Authoring now ship their own skills. Python remains a
separate optional conventions pack. The manifest in Core is the source of truth
for each skill's current owner.

If you installed only Core in 0.1.x, install **all three new family packs** to
keep the capabilities that Core previously bundled. If you installed Python,
keep it installed for its auto-loaded conventions. If you still have the original
single `lemmi-ai-kit` plugin, read [Migrating from 0.1.0](migrating-from-0.1.0.md)
first; that note covers its earlier plugin-id and skill-name changes.

## Choose your packs

| Pack | What moved or remains | Dependency |
|---|---|---|
| `lemmi-ai-kit-core` | Project setup, specs, review, learnings, commit and branch workflows | None |
| `lemmi-ai-kit-research` | Source planning and parallel research | None |
| `lemmi-ai-kit-orchestration` | Delegation, initiative coordination and stacked-work review | Core |
| `lemmi-ai-kit-skill-authoring` | Skill creation, research and review | Core |
| `lemmi-ai-kit-python` | Python coding and test conventions | None |

You may now install just one pack, a combination, or all five. Before installing
Orchestration or Skill Authoring on either host, install or upgrade Core to
0.2.0 or newer. Their Claude plugin manifests declare that minimum version;
fresh Claude installation of either dependent pack also installs Core. For an
existing 0.1.0 Core, run the native update command first; install alone may report
that it is already installed. Codex requires the explicit Core-first commands.
Research and Python can be used alone.

## Install from a local clone

Clone the kit and run the commands from its repository root. Use your host's
native plugin manager to add the marketplace, then run the install lines for
the packs you selected. These examples show all five choices. A former Core
user needs Core plus Research, Orchestration and Skill Authoring to retain the
capabilities Core previously bundled; Python remains optional.

For an existing Claude install, first run `claude plugin update lemmi-ai-kit-core@lemmi`
and `claude plugin update lemmi-ai-kit-python@lemmi` if Python is installed. Use the
same scope as the original installation (for example `--scope project`).

Claude Code:

```sh
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
claude plugin install lemmi-ai-kit-research@lemmi
claude plugin install lemmi-ai-kit-orchestration@lemmi
claude plugin install lemmi-ai-kit-skill-authoring@lemmi
claude plugin install lemmi-ai-kit-python@lemmi
```

Codex:

```sh
codex plugin marketplace add .
codex plugin add lemmi-ai-kit-core@lemmi
codex plugin add lemmi-ai-kit-research@lemmi
codex plugin add lemmi-ai-kit-orchestration@lemmi
codex plugin add lemmi-ai-kit-skill-authoring@lemmi
codex plugin add lemmi-ai-kit-python@lemmi
```

Local 0.2.0 installation was verified on both hosts on 2026-09-14. Research and
Python installed alone in fresh Claude configurations; Authoring and Orchestration
automatically installed Core. Codex's native configuration selected Research alone
and restored the normal enabled set after the override. Installed payload bytes
were compared with the source. The Git-based 0.2.0 release still requires publishing
the source changes; the `owner/repo` shorthand was not part of this check.

## Update references you own

Moved user-invocable skills now use their owning plugin namespace. For example,
`orchestrate` moved from Core to Orchestration, so type
`/lemmi-ai-kit-orchestration:orchestrate`. `skill-creator` moved to Skill
Authoring; type `/lemmi-ai-kit-skill-authoring:skill-creator`. Research skills use
`/lemmi-ai-kit-research:<skill-name>`. Core skills such as
`/lemmi-ai-kit-core:kit-setup` keep their namespace.

Check saved prompts, project rules, team documentation and any hand-maintained
skill index for old prefixes. Project-owned `AGENTS.md`, `CLAUDE.md` and `.ai/`
data remain yours; installing or updating plugins does not rewrite them. Do not
use scaffold `--reseed` as an upgrade shortcut because it resets project-owned
seed files. Review and edit only the references that moved. Auto-loaded Python
conventions need no slash-command change.

Use your host's plugin manager to enable, disable and update the packs you
choose. Disabling a pack removes its skills from that host's available inventory;
it does not delete your project rules or learnings. After updating, inspect the
installed pack list and each pack's skill inventory by name. In Claude Code,
`claude plugin list` and `claude plugin details <plugin-name>` provide those
views. In Codex, start with `codex plugin list` and its plugin directory.
