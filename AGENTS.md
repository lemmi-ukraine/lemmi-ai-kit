# AGENTS.md

## Commands

Run from the repository root. The four CI gates are `ruff check`, `ruff format
--check`, `basedpyright` and `pytest`; all four must be green.

```bash
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run basedpyright

# ALWAYS pass --basetemp. A bare `pytest` and a bare `ruff format --check .` both
# trip on an unreadable .pytest-tmp/ — ruff exits 2 while printing "already
# formatted", which reads as a pass. Say which invocation you ran.
T=$(mktemp -d); uv run pytest -q --basetemp "$T"; rm -rf "$T"

# Before publishing or installing anything an adopter will consume.
# -B is not optional: this package lives inside the plugin payload, so without it
# the import writes .pyc into the tree being measured and the check blocks on
# files it created itself. Exit 0 clean, 1 blocked, 2 could-not-measure — gate on
# `!= 0`, because 2 means the answer is unknown, not good.
uv run python -B -m lemmi_ai_kit publish-check
```

There is nothing to run or serve: the kit is a plugin plus a support CLI.

## Conventions

Shared conventions live in the installed coding, architecture, and testing
convention skills. What follows is specific to THIS repository.

### Layout
- `plugins/core/` and `plugins/python/` are the two shipped packs; each is a plugin
  entry in both marketplaces. `plugins/_template/` is the seed `new-pack` copies and
  is deliberately **not** a pack — it is absent from `PACKS`.
- The support CLI is `plugins/core/src/lemmi_ai_kit/`, and it lives *inside* the core
  payload. That is how it reaches an adopter, and it is why `publish-check` needs `-B`.
- `docs/research/` holds dated engineering records. They are evidence, not
  documentation: each states where its verification stops, and a record that a later
  one supersedes is corrected in place rather than deleted.
- `tasks/` and `.specs/` are in `.git/info/exclude` by operator ruling — permanently
  untracked, local to this checkout, never pushed. Do not plan to commit them.

### Rules with a cost behind them
- **A guard never shown to fail has not been shown to work.** Fire a new check at a
  known-positive before trusting its verdict. Every guard in this repo that reported
  green while blind was caught this way, and several were caught in their author's own
  work on the first run.
- **Cannot-measure is never a pass.** A check that cannot see its subject must say so
  and exit non-zero, not return an empty finding list.
- **Recompute every number at the moment you write it**, and anchor it to a commit.
  Counts written from working memory have gone stale inside the same session more than
  once, including inside documents about stale counts.
- **This checkout is shared by several sessions at once.** Deconflict by path, check
  `git status` before writing, and commit with an explicit pathspec on *both*
  `git add --` and `git commit --` — the index is shared, so a bare commit sweeps in
  a peer's staged work.

### Task documents (`tasks/`)
- One task per markdown file; keep focused on a single problem.
- Prefixes: `TECH-` (design), `STRUCT-` (refactor), `PROD-` (runtime), `BUG-` (fix), `FEATURE-` (new work).

### AI provider knowledge

**Rule: Always fetch official docs before answering questions about AI model internals.**

Never rely on in-memory training knowledge for AI provider specifics. Model IDs, API
parameters, event schemas, audio formats, rate limits, and capabilities change between
releases. Stale answers cause bugs that are hard to trace.

Prefer authoritative, auth-free sources (fetch with `WebFetch` before answering) — e.g.
provider docs pages and, when docs pages are unreliable, raw SDK type source files
(for OpenAI: `https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/...`).

See the `ai-docs-lookup` skill for the full lookup process.

## AI Development Workflows

### Pipeline Overview

```
PRE-PLANNING                PLANNING                    IMPLEMENTATION              COMPLETION
────────────                ─────────                   ──────────────              ──────────
/product-brief              /spec-driven-dev            [auto-loaded]               /post-task-review
(task)                      (workflow)                  convention skills           (workflow)
   │                           │                            │                          │
   └─→ tasks/FEATURE-*         ├─→ test-planner             │                          ├─→ task-learnings
                               │   (task)                   │                          │   (task)
                               │                            │                          │
                               ├─→ plan-critic                                        └─→ /commit-message
                               │   (review)                                               (task)
                               │
                               └─→ .specs/{name}/
                                   (state files)

SKILL CREATION                          PERIODIC (weekly/biweekly)
──────────────                          ──────────────────────────
/skill-creation-workflow                /learning-consolidator
(workflow)                              (workflow)
   │                                       │
   ├─→ skill-researcher                    ├─→ Analyze .ai/learnings.md entries
   │   (task)                              ├─→ Promote to AGENTS.md / skills
   │                                       └─→ Clean up processed entries
   ├─→ /skill-creator
   │   (task)                           /session-retrospective
   │                                    (task)
   └─→ skill-content-reviewer              │
       (review)                            ├─→ Extract session data (Python)
                                           ├─→ Analyze patterns & feedback
                                           ├─→ .ai/retrospectives/ report
                                           └─→ feeds /learning-consolidator
```

### Task completion checklist (mandatory)
When a task is complete, ALWAYS perform these steps before considering it done:
1. **Post-task review** (major tasks: 3+ files, new feature, spec completion) — Run the full 8-step review: code review (1–6), documentation impact (7), learnings extraction (8). See the `post-task-review` skill.
2. **Learnings extraction** (all tasks) — Extract project-level findings and append to `.ai/learnings.md`. See the `task-learnings` skill.
3. **Documentation updates** — If any modified files affect docs (per `references/doc-impact-matrix.md` in the `post-task-review` skill), update the affected documentation.
4. **Rebuild/restart** — not needed. This repository runs no long-lived services; it ships a plugin and a support CLI, both of which take effect on the next invocation.

### Learnings system
- `.ai/learnings.md` is a **lean intake buffer**, not the knowledge store. Before a task, draw on: the always-loaded `AGENTS.md` rules; the relevant skills (plugin or project-local); and — **when working in a subsystem, that subsystem's code-adjacent module/feature `README.md`**, where its specific conventions and gotchas live. Skim `.ai/learnings.md` itself only for not-yet-promoted intake entries.
- After completing a task, extract and record new learnings using the `task-learnings` skill — it appends to the `.ai/learnings.md` intake buffer under the matching category.
- If a finding reveals a convention gap, write it straight to its home: a universal rule → `AGENTS.md`; a cross-cutting pattern → the relevant skill; a subsystem gotcha → the module/feature README; an invariant guard a future edit could break → a co-located code comment.
- Periodically (~weekly) run `/learning-consolidator` to drain accumulated intake entries into rules, skills, READMEs, and comments, then remove the promoted source entries.
- See the `task-learnings` skill for the full extraction process.

### Product brief (pre-planning)
Uses: product-brief (task)
- For new product ideas that need shaping before implementation, run `/product-brief` first.
- The skill researches the codebase, challenges assumptions (2-3 mandatory), then writes a team-readable task description to `tasks/FEATURE-*.md` with production-ready UX content.
- Hand off to `/spec-driven-dev` when the brief is approved and the team is ready to implement.

### Spec-driven development
Uses: spec-driven-dev (workflow), test-planner (task), plan-critic (review)
- Auto-detect task size before implementation using scope analysis.
- Small tasks (1–3 files, single concern): implement directly.
- Medium tasks (4–10 files, new components): create a lightweight spec in `.specs/{task-name}/spec.md`.
- Large tasks (10+ files, multi-feature, architectural): create full spec (requirements.md, design.md, tasks.md, test-cases.md + test-plan.md) in `.specs/{task-name}/`.
- Large tasks: present requirements → approval → design → approval → then tasks and the verification plan **in parallel**, each with its own approval → implement.
- Verification planning (`test-planner`) runs for Medium and Large tasks whose design touches executable code; skip it otherwise and say so. It harvests conditions by id from requirements rather than restating scenarios, gives every case exactly one owning test level, and assigns each NFR a verification method (automated / observability / manual / accepted-unverified).
- Because tasks and the verification plan are written in parallel, reconcile them before implementing: every `TC-` needs an implementing task, and every task's `Test requirements` field cites `TC-` ids rather than prose.
- At each spec gate, iterate if the user requests changes. Challenge changes that are technically unsound or contradict prior approvals — once, with reasoning — then defer to the user.
- All spec documents must be written to `.specs/{task-name}/` as actual files. IDE-specific plan tools do not substitute for file creation.
- Large tasks with natural phase boundaries: use phased execution with intermediate quality gates to reduce context load and catch drift early.
- Templates live in `.ai/templates/`. See the `spec-driven-dev` skill for the full pipeline.

### Post-task review
Uses: post-task-review (workflow), task-learnings (task), commit-message (task)
- Run the 8-step review for all major tasks (3+ files modified, new features, spec completions).
- Steps 1–6: code review and convention compliance (see the `post-task-review` skill).
- Step 7: documentation impact analysis — check and update affected docs.
- Step 8: learnings extraction — capture and record project knowledge.

### Plan self-review (plan-critic)
Uses: plan-critic (review) — **universal, not limited to spec-driven-dev**
- **Before presenting ANY plan, spec, or design document to the user**, run the plan-critic self-review. This applies to bug-fix plans, feature specs, refactoring plans, and any other structured plan.
- Invoke the `plan-critic` skill after writing: `spec.md` (medium tasks), `design.md` (large tasks), `tasks.md` (large tasks, completeness-only), `test-cases.md` / `test-plan.md` (Dimension 6 plus the citation check), or any bug-fix/task plan.
- Resolve all Blocker and Major findings silently before presenting. Minor findings are fixed without mention.
- If any Blockers or Questions cannot be resolved without user input, surface them prominently at the top of the presented document — do not suppress them.

### Orchestration and delegation
Uses: orchestrate (workflow), agent-delegate (task)
- For large decomposable tasks, run `/orchestrate`: the main model plans and judges;
  scoped subtasks go to cheaper native subagents (Opus for reasoning, Sonnet for mechanical
  work) and external CLI peers (codex, cursor-agent, grok) in parallel.
- Every delegation uses the brief contract (one concern, inlined context, self-checkable
  definition of done, short report) — see `references/brief-template.md` in the `orchestrate` skill.
- A worker's summary is a claim: verify the actual output against the definition of done before
  merging. For high-stakes decisions, task independent workers in parallel without showing them
  each other's answers, then synthesize.
- Keep single-agent when judgment is the work or the subtasks can't be crisply named.

### Parallel research source planning
Uses: research-source-planner (task), research-source-claim (task), parallel-deep-research (workflow)
- **One-command path:** `/parallel-deep-research <question>` runs the whole flow automatically — scope → plan sources (planner) → fan out one sub-agent per owner (claim protocol) → synthesize a cited report.
- **Manual path / pre-step:** before any hand-rolled parallel/multi-session fan-out, run `/research-source-planner <question>` first. It builds a deduplicated `source-manifest.md` that assigns each source to exactly one owner.
- Each fan-out worker then follows `research-source-claim`: workers touch ONLY their assigned rows.
- Skip for single-agent lookups (1 owner → no overlap to prevent).

## Do not

### AI workflow rules (universal)
- Invoke a Workflow Skill from within another Workflow Skill (max 1 level of skill nesting).
- Auto-invoke side-effect skills that take outward or destructive action (commit, deploy, review, branch-switch) without an explicit user request. **Standing exception:** the model MAY proactively run `session-retrospective` and `learning-consolidator` — the retrospective only writes a report, and the consolidator presents its plan and waits for approval before editing any rule, skill, or learning, so the destructive step stays gated.
- Hardcode an absolute local path — a drive-letter path, `/Users/…`, `/home/…`, or a per-machine session directory — in a shared skill, script, or doc. These are machine-specific, so a hardcoded path works for exactly ONE person. Derive at runtime instead: relative to the referring file, repo-root-relative, `${CLAUDE_SKILL_DIR}`, or `Path(__file__)` / `Path.home()`. Enforced by the skill-reviewer portability check.
- Build scope the task didn't ask for. Volunteering speculative features, fallbacks, or examples "just in case" is over-engineering — surface optional scope as a decision in the plan and implement it only on approval.
- Merge a sub-agent's (Agent/Task) returned summary as if it were verified — its change-log is a **claim**, not verification. For delegated multi-file work: keep coupled/load-bearing pieces in the main thread, inline the source-of-truth into each brief so the sub-agent can't drift, and ALWAYS read each sub-agent's actual output files and reconcile them against the source-of-truth before integrating.
- Edit a file you read earlier in the session without re-reading it first when it may have changed since — a file open in the IDE, touched by a linter/formatter, edited as part of a sibling change, or an append-only log (`.ai/*.md`). For append-heavy markdown, copy an Edit's `old_string` verbatim from a fresh Read of the target region — never reconstruct it from memory.
- `Read` a conventional or assumed path before confirming it exists — `Glob`/verify first.
- Verify a structured-config value (YAML frontmatter key, JSON field, enum membership) with a whole-file substring grep — parse the structure or scope the match to the structural region instead. A content grep also matches files that merely *document* the key.
- Start implementing bug fixes without presenting a brief plan first — even for "quick" fixes. If the fix touches more than 1 file or involves data flow changes, write a plan and get approval before coding.
- Treat task docs as runtime configuration, or let tasks drift from current implementation without updating status.

### Python rules (Python projects)
- Use `str()` on `str, Enum` subclasses to extract values — use `.value` instead (Python 3.11 breaking change).
- Use `.value` on enum-typed fields in models with `use_enum_values=True` — these fields are already strings at runtime.
- Use `cast(Any, ...)` to pass objects between layers with different models — perform explicit type conversion instead.
- Use `if TYPE_CHECKING:` import guards to break an import cycle or type a back-reference — resolve the cycle structurally instead (narrow `Protocol`, neutral module, inverted dependency). See the installed coding-conventions skill for language-specific examples.
- Use blocking I/O inside async flows.
- Make real external API calls in tests, or patch concrete clients instead of using protocol-based DI overrides.

### Project rules

Everything above this heading is shipped by the kit and is refreshed when the kit
updates. **Nothing below it is ever generated, overwritten, or reordered** —
`kit-setup refresh` rewrites only its own marked blocks — which is what makes this
the one place in the file a convention can safely live.

A rule belongs here when it is a do-not, specific to THIS repository, that a
newcomer would otherwise learn by breaking something. Three near-misses go
elsewhere instead: a universal rule belongs in the sections above or in a skill; a
single subsystem's gotcha belongs in that subsystem's README, next to the code it
constrains; and one still being argued about stays in `.ai/learnings.md` until it
settles.

State the rule and its reason in the same breath. A rule with no reason attached
is dropped the first time it is inconvenient, and nobody can tell later whether
dropping it was fine.

Rules arrive two ways: by promotion, when `/learning-consolidator` drains an entry
`task-learnings` put in `.ai/learnings.md`, or by hand the moment one is known —
from an existing `CONTRIBUTING.md`, a house style, or a decision made in review.

*None recorded yet. That is a legitimate state: it means none have been
established, which is not the same as nobody having looked.*

---

*Generated by [lemmi-ai-kit](https://github.com/lemmi-ukraine/lemmi-ai-kit).*
