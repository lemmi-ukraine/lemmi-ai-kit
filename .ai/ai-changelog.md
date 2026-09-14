# AI Infrastructure Changelog

> Reverse-chronological log of all changes to the project's AI infrastructure:
> skills, conventions, rules, and workflow modifications.
>
> **How entries are added:** Automatically by AI workflows (skill-creator, learning-consolidator,
> post-task-review) or manually via the `ai-changelog` skill.
>
> **Format:** Each entry follows the structured format defined by the `ai-changelog` skill (lemmi-ai-kit plugin).

---

## 2026-09-14

### SKILL-ADDED: Share portable flow mapping through Core
- **What:** Registered flow-mapping in Core with its schema, five reusable tools and synthetic self-certification project. Tool paths stay inside the plugin; consumer roots and code directories are explicit. Nested probes propagate the no-bytecode flag into every subprocess. Preserved authored projection columns and made missing corpus inputs fail visibly. Comment checking distinguishes docstrings from executable string expressions.
- **Why:** The formerly deferred workflow must work outside its source checkout without copied skills or validators. Independent consumer tests exercise installation paths, invalid inputs and the shared-tool contract.
- **Files:** `plugins/core/skills/flow-mapping/`, Core native manifests and README, the bundled `manifest.toml`, `docs/upstream-sync.toml`, `README.md`, `tests/test_flow_mapping.py`, `tests/test_upstream_sync.py`, `.ai/ai-changelog.md`, `.ai/learnings.md`, `.ai/improvement-hypotheses.md`, `CHANGELOG.md`.
- **Affected workflows:** Flow mapping, native Core installation, flow validation, projection generation, seam reconciliation and optional comment cleanup. This completes the deferred port described in the earlier entry.

### INFRA-MODIFIED: Resolve the changelog merge and explain research workflows
- **What:** Kept main's dated, structured changelog and retained this PR's plugin split, bundled FFF and onboarding entries in that format. Added README descriptions of parallel research, planner/claim ownership, the skill-researcher authoring stage and the currently deferred flow-mapping port.
- **Why:** Reviewers and users need visible workflow roles, outputs and availability, while the PR must preserve the newer upstream changelog structure.
- **Files:** `README.md`, `CHANGELOG.md`, `.ai/ai-changelog.md`.
- **Affected workflows:** Research and skill authoring documentation. No workflow implementation or installation behavior changed; no new improvement hypothesis is warranted.

### INFRA-MODIFIED: Add agent-led onboarding and measure real installation sessions
- **What:** Added a paste-ready installation prompt and separate new/existing-project guidance to README. Ran four native agent sessions in temporary repositories and recorded external wall-clock timing, independent file/plugin checks and manual content findings.
- **Why:** Users should be able to ask their agent to install and configure the kit, with explicit preservation boundaries and evidence of how that workflow behaves.
- **Files:** `README.md`, `docs/research/2026-09-14-agent-installation.md`, `docs/research/2026-09-14-agent-installation-results.json`.
- **Affected workflows:** Installation and kit-setup entry point; the installer and skills are unchanged. All four trials met the installation checks; one generated-prose error remains recorded. No comparative speed/quality hypothesis: these are single-run smoke measurements, not a controlled improvement study.

### INFRA-MODIFIED: Bundle FFF binaries so users need no separate FFF installation
- **What:** Vendored the six official FFF v0.10.6 platform binaries with their MIT license and SHA-256 checksums. Added a stdlib launcher through the existing uv runtime, preserving cwd/stdio and rejecting unsupported or corrupt payloads. Disabled upstream startup update checks; plugin updates own the version.
- **Why:** Installing Core should provide FFF directly instead of requiring each user to install and configure an executable separately.
- **Files:** `plugins/core/vendor/fff/`, `plugins/core/src/lemmi_ai_kit/fff.py`, `plugins/core/.mcp.json`, both Core native manifests, `.gitattributes`, `plugins/core/README.md`, `README.md`, `CHANGELOG.md`, `tests/test_fff.py`, `tests/test_pack_isolation.py`.
- **Affected workflows:** Native file-search MCP startup and plugin distribution. This supersedes the PATH prerequisite in the preceding entry. No quality/performance hypothesis: the upstream tool's behavior is unchanged, and the setup requirement is removed structurally.

### INFRA-MODIFIED: Bundle the FFF MCP declaration with Core
- **What:** Added a shared `.mcp.json` to Core and referenced it from both native manifests. It launches the installed `fff-mcp` binary through the client PATH; no machine-specific path, installer or binary is vendored.
- **Why:** Projects using Core receive the same file-search integration through either host's existing plugin system.
- **Files:** `plugins/core/.mcp.json`, both Core native manifests, `plugins/core/README.md`, `README.md`, `CHANGELOG.md`, `tests/test_plugin.py`, `tests/test_pack_isolation.py`.
- **Affected workflows:** Native MCP discovery and file search. No new hypothesis: this packages an existing tool; no search-quality or performance improvement is claimed.

### INFRA-MODIFIED: Split workflow families into native optional plugins
- **What:** Moved Research, Orchestration and Skill Authoring out of Core into their own native plugins; Python remains separate. Each skill has one owner. Claude declares Core dependencies for Orchestration and Authoring; Codex uses explicit prerequisite installs. Core-only instructions guard optional routes, and native skill audits use plugin registration rather than a consumer's incomplete CLAUDE index.
- **Why:** Users choose capability groups with existing plugin managers and keep project customization in their own rules. No selection schema, bundle generator or dependency resolver was added.
- **Files:** `plugins/core/skills/`, `plugins/research/`, `plugins/orchestration/`, `plugins/skill-authoring/`, `plugins/python/`, both native marketplace catalogs, `plugins/core/src/lemmi_ai_kit/{manifest,scaffold,cli}.py`, its template assets, `pyproject.toml`, `uv.lock`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, adoption/authoring/migration/developer guides under `docs/`, and manifest/plugin/isolation/CLI/publication/document-reference tests.
- **Affected workflows:** Native install, update and skill discovery, project scaffolding, optional workflow handoffs and skill audit. Local installs are development snapshots; source changes are uncommitted and unpublished. No new improvement hypothesis: this is distribution and registration work preserving the existing workflow methods; no user-outcome improvement has been measured.
