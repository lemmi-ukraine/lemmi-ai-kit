# Learnings Entry Format Reference

## Entry Structure

Every entry in `.ai/learnings.md` must follow this exact format (the four routing fields are
optional — see § Routing Fields):

```markdown
### [YYYY-MM-DD] Short descriptive title
- **Context**: What task or situation triggered this
- **Finding**: The specific insight discovered
- **Impact**: What to do differently going forward
- **Category**: architecture | pitfall | external-api | performance | pattern | convention | interaction
- **Home**: agents-rule | skill:<name> | readme:<path> | comment:<file>:<symbol> | tasks:<tasks/FILE.md> | roadmap | memory
- **Enforce-via**: lint | test | template | script | prose
- **Verify-at**: <live file path or symbol that anchors the claim>
- **Scope**: durable | branch:<name> | until:<event>
```

### Field Rules

| Field | Required | Constraints |
|-------|----------|-------------|
| Date | Yes | ISO format `YYYY-MM-DD` |
| Title | Yes | No length cap — state the finding, not a topic label (see note below); no generic titles |
| Context | Yes | Reference the task or situation specifically |
| Finding | Yes | One concrete insight per entry |
| Impact | Yes | Must be actionable — "do X" or "avoid Y" |
| Category | Yes | Must be one of the canonical slugs (see below) |
| Home | No | Routing HINT for the consolidator (see § Routing Fields) — one of the listed forms |
| Enforce-via | No | How the promoted guidance should bind; `lint`/`test`/`template`/`script` outrank `prose` |
| Verify-at | No | A live anchor (`<module path>` / `ClassName.method`) for cheap actuality re-checks |
| Scope | No | Validity boundary; default `durable`. `branch:`/`until:` entries expire when the boundary passes |

> **Titles state the finding, and carry no length cap** (the "max 80 characters" rule was removed
> 2026-08-20). A title that says *what is true* — "`grep -c $'\r$'` under Git Bash always answers
> 100% CRLF" — lets the consolidator's Phase 1 cluster-detection route most entries without opening
> their bodies; that is the step the field exists to serve, and it was measured on the 2026-08-20
> drain (~80 of 111 entries routed from titles alone). A topic label ("line endings") forces 111 full
> reads instead.
>
> **Why it was deleted rather than enforced**, since 108 of 111 titles violated it and that fact
> alone is not the reason: **a constraint whose violation has never produced a failure is decoration;
> a constraint whose violation produces failures earns a mechanical seam, not deletion.** No incident,
> retro finding, or changelog entry has ever traced a problem to a long title, whereas the `cd`-prefix
> rule — violated 577 times — earned a hook and went to 0 successes. Reading a high violation rate as
> licence to delete would have deleted that one too. Apply the discriminator, not the percentage.

## Routing Fields (the improvement contract)

The Category encodes the *shape* of the insight; the routing fields encode **what should change,
how it binds, and how long it stays true**. Fill them at CAPTURE time — the session that hit the
problem knows the destination cheapest — but they are HINTS: the consolidation plan's approval
gate remains the authoritative routing decision, and the consolidator must verify every hint
(a wrong `Home:` is possible; a `Verify-at:` symbol may have been renamed on this branch).

- **Home** — where the knowledge belongs when drained. `tasks:<file>` is the **work lane**: if the
  finding is a *defect to fix* or a *code/pipeline change* (work, not knowledge), it must name an
  existing or newly created `tasks/` doc (prefixes per AGENTS.md § Task documents) — create the
  task file in the same step. Learnings hold knowledge; task files hold work; an entry that is
  really work with no task file is homeless by construction.
- **Enforce-via** — retrospectives show mechanical seams (spawn templates, lints, tests, script
  gates) reliably change behavior while always-loaded prose only raises probability (e.g.
  edit-stale-read recurred 43× despite its rule; the spawn-preamble fix took sub-agent env-traps
  50/263 → 0/300). Declaring `lint`/`test`/`template`/`script` biases the promotion toward
  tooling; `prose` is the honest default when no mechanical seam exists.
- **Verify-at** — anchors the entry's central claim to a live path/symbol so the consolidator's
  actuality check is one grep instead of an investigation. **It must name a TRACKED path.** Four
  tracked entries once cited a *gitignored* report as their anchor, which makes the claim
  unverifiable for every future reader — the file exists only on the machine that wrote it, and the
  next drain has nothing to re-check. Caught only by the post-task-review untracked-dependency step.
  Confirm with `git ls-files --error-unmatch <path>` (exit 0), and where the evidence genuinely lives
  in an untracked or gitignored artifact, **state the claim inline in the entry** instead of pointing
  at the file. Anchor by **symbol**, not line number: in this tree HEAD moves mid-session and anchors
  drift ~14 lines, so a line number rots into an apparent fabrication.
- **Scope** — entries written during a freeze, on a divergent branch, or about an in-flight
  refactor rot silently; `branch:`/`until:` makes the expiry visible so the consolidator can
  archive expired entries without re-litigating them.

## Canonical Categories

Exactly **seven** categories exist. Each entry lives under the matching `## <section header>` in
`.ai/learnings.md` — find the section (create the header if absent), never append at the file
end (a chronological catch-all misleads the consolidator's clustering).

> **This sentence is the only place the category COUNT is written down.** Consumers say "the
> canonical set" and link here rather than restating a number: a count duplicated across five files
> breaks silently in all five when an eighth category is added, and prose has no test to catch it.
> `python -m lemmi_ai_kit lint` and its test derive the count from one constant for the same reason —
> a hardcoded "six" in both is exactly what broke when the seventh was added.

| Section header (`##`) | `Category:` slug | What belongs here |
|-----------------------|------------------|-------------------|
| Architecture Decisions | `architecture` | Structural choices, pattern selections, rationale for design |
| Common Pitfalls | `pitfall` | Bugs that could recur, tricky edge cases, easy mistakes |
| External Service Quirks | `external-api` | OpenAI, GCS, PostgreSQL behaviors that aren't obvious |
| Performance Insights | `performance` | Latency findings, optimization discoveries, scaling concerns |
| Pattern Discoveries | `pattern` | What worked well, reusable approaches, effective abstractions |
| Convention Clarifications | `convention` | Ambiguous rules resolved, edge cases in conventions |
| Interaction & Workflow Friction | `interaction` | How the human and the agent INTERACT — repeated work, agent error classes, human re-asks, a skill that should have fired and didn't |

### `interaction` vs `pitfall` — the distinction that makes the category work

The first six describe the **codebase**; `interaction` describes the **collaboration**. Ask: *if a
different agent worked on a different feature in this project tomorrow, would it hit this?* If the
answer turns on the code, it is a codebase category. If it turns on how the work was conducted —
what got re-read, re-run, re-asked, or re-done — it is `interaction`.

This split is load-bearing, not cosmetic. The consolidator promotes a **3+-entry cluster** into a
skill or workflow change. Behavioral findings filed under `pitfall` sit among codebase bugs and
never present as a cluster, so they are never promoted. Keeping them together is what lets three of
them become one skill improvement.

Prefer `interaction` when both seem to fit — a finding that is *really* about agent behavior filed
as a `pitfall` is invisible to promotion, whereas the reverse is merely untidy.

**Legacy sections:** older section names (e.g. "Prompt Engineering for AI Skills",
"Specification Engineering", "Feedback AI Pipeline", or transitional carried-over intake
sections) may still appear in `.ai/learnings.md` until the consolidator drains them. Tolerate
them when reading; never add NEW entries under a non-canonical section.

## Good Entry Examples

### Example 1: Convention Clarification (with routing fields)

```markdown
### [2026-02-15] Feature exception conversion must happen in routes, not services
- **Context**: New feature implementation — service was raising HTTPException directly
- **Finding**: Feature-specific exceptions (e.g., `SessionNotFoundError`) must be caught in API routes and converted to shared exceptions (`NotFoundError`). Services should raise feature-specific exceptions only.
- **Impact**: When writing service code, always raise feature-specific exceptions. In routes, wrap service calls with try/except that converts to shared exceptions.
- **Category**: convention
- **Home**: the installed language-conventions skill
- **Enforce-via**: prose
- **Verify-at**: backend/app/features/coach/api/routes.py
- **Scope**: durable
```

### Example 2: External API Quirk

```markdown
### [2026-02-20] OpenAI Realtime API silently drops audio chunks over 15MB
- **Context**: Realtime voice session audio streaming — users reported truncated responses
- **Finding**: The OpenAI Realtime API does not return an error when audio input exceeds ~15MB per chunk. It silently truncates. The session appears to continue normally but the AI response quality degrades.
- **Impact**: Always chunk audio input to stay under 10MB per segment. Add a size check before sending to the API.
- **Category**: external-api
```

### Example 3: Architecture Decision

```markdown
### [2026-03-01] Use SSE instead of polling for async job status
- **Context**: Async report generation migration from polling to SSE
- **Finding**: Server-Sent Events provide real-time progress updates without the overhead of polling intervals. The existing job infrastructure supports SSE via the `StreamingResponse` pattern already used in other features.
- **Impact**: For new async operations that need progress updates, prefer SSE over polling. Use the existing `StreamingResponse` + job status pattern.
- **Category**: architecture
```

### Example 4: Common Pitfall

```markdown
### [2026-03-02] Missing await on async repository calls causes silent data loss
- **Context**: Session scoring feature — scores were intermittently not persisted
- **Finding**: Calling an async repository method without `await` returns a coroutine object that is silently discarded. No error is raised, but the database operation never executes.
- **Impact**: Always verify async/await usage in service methods, especially when calling repository save/update operations. The ruff linter does not catch missing awaits on coroutines.
- **Category**: pitfall
```

## Bad Entry Examples

### Bad: Too vague

```markdown
### [2026-03-01] Testing lesson
- **Context**: Working on tests
- **Finding**: Tests are important
- **Impact**: Write more tests
- **Category**: pattern
```

**Why it's bad:** No specific context, finding is not an insight, impact is not actionable.

### Bad: Duplicates existing rules

```markdown
### [2026-03-01] Use one class per file
- **Context**: Code review
- **Finding**: Each class should be in its own file
- **Impact**: Create separate files for each class
- **Category**: convention
```

**Why it's bad:** This is already documented in AGENTS.md and multiple skills. A learnings entry should add new insight, not restate known rules.

### Bad: Too granular

```markdown
### [2026-03-01] Fixed typo in user_service.py line 42
- **Context**: Bug fix
- **Finding**: Variable name was misspelled
- **Impact**: Check spelling
- **Category**: pitfall
```

**Why it's bad:** This is a task-specific fix with no broader lesson. Does not help future tasks.

## Consolidation Guidance

- **Universal convention or anti-pattern** → `AGENTS.md`
- **Cross-cutting pattern** → the relevant `.claude/skills/*` skill
- **Subsystem gotcha** → the module/feature `README.md`
  (`backend/app/core/<module>/README.md`, `backend/app/features/<feature>/README.md`)
- **Invariant guard a future edit could break** → a co-located code comment at the exact site
- **Defect to fix / code or pipeline change** → a `tasks/` doc (the entry's `Home: tasks:<file>`
  names it; the learning may then be archived once the task file carries the work)
- **Same insight recorded twice** → merge the entries before promoting

An entry's routing fields (`Home:`/`Enforce-via:`/`Verify-at:`/`Scope:`) seed the consolidator's
classification — verified, never followed blindly. Entries whose `Scope:` boundary has passed are
archive candidates without further analysis.

**No tombstones:** promoted entries are deleted cleanly — never leave "Promoted to {file} on
{date}" notes behind. The rule/skill/README/comment is the authoritative source now; git
history preserves the original entry.
