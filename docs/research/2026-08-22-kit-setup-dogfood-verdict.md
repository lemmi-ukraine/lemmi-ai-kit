# `kit-setup` dogfood verdict

**Measured:** 2026-08-22 · **Deliverable:** I3 D11 · **Verdict, not a commit**
**Charter falsifier:** *"Dogfooding `kit-setup` on this repo fails or produces
something embarrassing"* → *"Fix it as an I2/I4 bug — finding it is worth more than
the proof asset."*

Run in a throwaway clone, per the topology: Part A produces the verdict, Part B
commits the output (charter DoD #11), because the `CLAUDE.md` it renders contains a
skill catalog that I4's renames invalidate.

## Verdict: the falsifier **partially holds**. Nothing is broken; one advertised mechanism does not exist.

## What works

`uv run python -m lemmi_ai_kit scaffold .` against a fresh clone of this repo:

```
written: 3  seeded: 5  overwritten: 0  unchanged: 0
```

- 8 files placed: `AGENTS.md`, `CLAUDE.md`, `.ai/{learnings,ai-changelog,improvement-hypotheses}.md`, `.ai/templates/{requirements,design,tasks}.md`
- **Zero unsubstituted placeholders** in either rendered file
- `.claude/` correctly **not** created — skills come from the plugin, never the scaffold
- Idempotent: a second run reports `seeded: 0`
- 4 honest `TODO(project)` stubs in `AGENTS.md` rather than invented facts

None of that is embarrassing. It is the behaviour the README describes.

## Finding 1 — the marker/refresh mechanism the README advertises does not ship

`README.md:56` states:

> Generated sections are wrapped in `<!-- lemmi-ai-kit:begin/end ... -->` markers.
> The files are yours to edit; the markers only exist so
> `/lemmi-ai-kit:kit-setup refresh` can later re-detect and update those blocks —
> per-block diff and approval, manual edits are never silently overwritten.

Measured:

| Claim | Reality |
|---|---|
| Markers in the scaffolded output | **0** |
| Markers in the shipped templates | **0** |
| Markers anywhere in the package | **1** — `skills/kit-setup/SKILL.md:86`, as an example inside the skill's own instructions |
| A `refresh` subcommand | **absent** — the CLI exposes `scaffold` and `list` only |

This is a **division of labour, not a bug**: inserting marked blocks is the
`kit-setup` *skill's* job — an agent workflow that detects a project's commands
from its CI config, manifests and lockfiles — and the CLI is only its mechanical
half. `/lemmi-ai-kit:kit-setup refresh` is a skill invocation, not a CLI one.

But it means two things are true at once, and only one of them is documented:

1. **The CLI-only path produces no markers**, so a project scaffolded by
   `scaffold` alone has nothing for a later `refresh` to find.
2. **The refresh path is unverified.** No test covers it, nothing in the shipped
   templates or CLI emits a marker, and confirming it requires running the agent
   workflow rather than the package. Its correctness is currently an untested
   claim in the README.

Not an I2/I4 bug as the falsifier anticipated. It is a **documentation-accuracy
and test-coverage gap**, and it belongs to whoever rewrites the README — the
sentence promises an outcome the mechanical path does not produce.

## Finding 2 — dogfooding specifically is a degenerate case

The template's example commands are `uv run ruff check .`, `uv run ruff format .`,
`uv run basedpyright`, `uv run pytest tests/`. Those are **this repo's actual
commands**, because the template was written from a project with the same stack.
So the scaffolded `AGENTS.md` puts

> `TODO(project): replace with this project's real commands`

directly above commands that are already correct.

Harmless, and it only happens when dogfooding on a matching stack. It matters for
one reason: **the dogfood output needs a human pass before it becomes a public
proof asset.** Committing it verbatim would ship a repo whose own AI config tells
its agents to replace commands that are already right — and one command,
`pytest tests/`, that differs from what CI and `CONTRIBUTING.md` actually run
(`uv run pytest`).

## Recommendation

Dogfooding is still the right move and still the best proof asset available. Two
conditions before committing it, both Part B:

1. Run the **skill**, not just the CLI, so the detected blocks and their markers
   are real.
2. Human-review the rendered `AGENTS.md` and resolve the four `TODO(project)`
   stubs. A public `AGENTS.md` full of TODOs is a weaker proof than none.

Neither is a blocker on Part A.
