# Project Learnings

This file is a **lean intake buffer**, not a knowledge store. New lessons are appended here by the
`task-learnings` skill, then **periodically drained** to the agent-facing home where each lesson is
actually useful — so this file normally holds only a handful of not-yet-promoted entries.

**Where the knowledge lives (consult these, not one big flat file):**
- **Universal conventions & anti-patterns** → `AGENTS.md` (always loaded).
- **Cross-cutting patterns** → the relevant skill (project-local `.claude/skills/`; kit skills are plugin-managed).
- **Subsystem conventions & gotchas** → the code-adjacent **module / feature `README.md`**.
  **When you work in a subsystem, consult that subsystem's README** — that is where its
  promoted lessons live.
- **Invariant-guarding gotchas** → a co-located code comment at the exact site it guards.

**How entries are added:** `task-learnings` appends each finding as a `### [YYYY-MM-DD] title` block
under the matching `## Category` header (create the header if absent; use a canonical category —
Architecture Decisions, Common Pitfalls, External Service Quirks, Performance Insights, Pattern
Discoveries, Convention Clarifications). Place each entry under its **topic** category, never at the
file end (a chronological catch-all misleads the consolidator's clustering).

**How it drains:** periodically (`/learning-consolidator`, ~weekly) each accumulated entry is routed
to its home above and removed here.

---

## Common Pitfalls

### [2026-09-14] A portable code root also controls which file references are project claims
- **Context**: Moving flow validators into an installed Core skill.
- **Finding**: Generalizing the file-reference regex to every slash path introduced new findings for package-cache paths and relative prose references. Deriving its source prefix from the declared code root preserved the consumer contract while supporting independent src/ and lib/ projects.
- **Impact**: Port parser configuration together with root resolution, and compare a real consumer's outputs before and after changing either. Keep bundled probe fixtures independent of that consumer.
- **Category**: pitfall
- **Home**: comment:plugins/core/skills/flow-mapping/scripts/validate_flow_map.py:configure
- **Enforce-via**: test
- **Verify-at**: tests/test_flow_mapping.py
- **Scope**: durable
