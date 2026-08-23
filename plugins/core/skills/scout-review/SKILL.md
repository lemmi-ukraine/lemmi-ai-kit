---
name: scout-review
user-invocable: true
metadata:
  type: workflow
description: >
  High-precision multi-agent code review modeled on DoorDash's production AI reviewer:
  a cheap lead scout flags suspicious areas without verifying, two strong deep reviewers
  investigate the top leads beyond the diff (callers, siblings, tests, deletions), and
  every candidate finding must survive an adversarial disprove-it pass before it is
  reported. Use when the user asks for a "scout review", a "doordash review", a thorough
  high-signal review of a branch/PR/working diff, or wants to A/B reviewer model combos.
  Do NOT use for a quick single-file glance or style pass — a plain inline review is
  cheaper and faster there.
---

# Scout Review — notice cheaply, verify expensively, report rarely

Three-stage review pipeline. The design borrows the core lessons from DoorDash's
production code reviewer (careersatdoordash.com engineering blog, 2026):

1. **Separate noticing from verifying.** A cheap scout reads the whole change and
   flags suspicious areas as unverified *leads*. Strong reviewers then dig only into
   the strongest leads — the way a senior engineer reviews: hunch first, then dig
   selectively, never exhaustively line-by-line.
2. **Most bugs worth catching don't live in the diff.** They live in how the diff
   interacts with its dependencies and dependents. Deep reviewers must read beyond
   the hunks: callers, sibling implementations, tests, and what deleted code used
   to guarantee.
3. **Precision over recall.** Before anything is reported, the system attempts to
   falsify its own finding. A reviewer that spams gets muted, and a muted reviewer
   catches nothing. Silence is a valid, successful outcome.

## Usage

```
/scout-review                 # default combo: sonnet scout + fable deep reviewers
/scout-review opus            # combo B: sonnet scout + opus deep reviewers
/scout-review fable base=main # review current branch against main
/scout-review opus <PR-url>   # review a PR (fetch the diff via `gh pr diff`)
/scout-review scout=haiku reviewer=opus   # explicit override for experiments
```

## Model combos

| Combo | Scout | Deep reviewers + verifiers | When |
|---|---|---|---|
| `fable` (default) | `model: "sonnet"` | `model: "fable"` | Strongest verification tier |
| `opus` | `model: "sonnet"` | `model: "opus"` | Baseline / cost comparison |

Dispatch every worker through the `Agent` tool with the combo's model override. If a
model name is rejected by the harness (e.g. `fable` unavailable), say so and fall back
to `opus` for that role — never silently downgrade. When the user is comparing combos,
keep everything else identical (same diff, same leads cap, same budgets) and report
per-combo findings, wall-clock, and rough token spend side by side.

## Pipeline

All worker briefs are in [references/briefs.md](references/briefs.md). Fill the
placeholders; do not improvise leaner prompts — the guardrails in them are the product.

### 0. Scope + review profile (you, inline)

- Resolve the diff: working tree vs `HEAD`, branch vs `base=<ref>`, or `gh pr diff`.
  If the diff is empty, say so and stop.
- Build a **review profile** — the domain-specific bar for this repo. Mine
  `CLAUDE.md`, `AGENTS.md`, `.ai/learnings.md`, and nearby docs for invariants.
  Keep a candidate rule only if ALL hold (DoorDash's profile filter):
  - CI / typecheck / linters would NOT already catch violations of it;
  - it is NOT generic knowledge any strong model already applies;
  - you can point at concrete file-and-line evidence of it in this codebase.
- Cap the profile at ~10 rules. Zero rules is fine; the pipeline still runs.

### 1. Lead scout (cheap model, read-only)

One `Agent` call, scout model, with the scout brief + full diff + profile. The scout
flags up to **12 ranked leads** — hunches with locations and a why — and explicitly
does NOT verify anything. High recall is its only job.

### 2. Deep reviewers (strong model, parallel)

Split the top leads between **two** `Agent` calls in a single message (reviewer
model). Each investigates only its assigned leads, reading beyond the diff, and
returns candidate findings with severity, exact `file:line`, a concrete failure
scenario, and evidence snippets — or discards the lead with a stated reason.

### 3. Disprove-it pass (strong model, parallel, fresh context)

For every candidate finding, one fresh `Agent` call (reviewer model) whose sole job
is to **refute** it: find the guard clause, the covering test, the caller that never
passes that value. Uncertain → refuted. Only findings that survive are reportable.

### 4. Report (you, inline)

- Lead with the outcome: N findings survived out of M candidates from K leads.
- **Critical/High** findings first, each with `file:line`, the failure scenario, the
  evidence, and a suggested fix. Direct language — no "consider possibly maybe".
- Medium/Low collapsed into a short appendix list; never more than **10 findings
  total** — drop the weakest, say you dropped them.
- If nothing survived: say exactly that, plus what was checked. Do not pad.
- Close the loop: when the user accepts or rejects findings, append what the
  pipeline got right/wrong to `.ai/learnings.md` — rejected findings are future
  profile filters, missed bugs (found later) are future scout hints.

## What the scout must sniff hardest (from DoorDash's miss analysis)

- **Deletions** — removed struct fields, config defaults, flags, interface methods:
  compiles clean, silently changes runtime behavior. Humans skim deleted code.
- **Cross-boundary drift** — one side of a boundary updated (an enum handler, an
  adapter, a producer/consumer pair) while sibling implementations were not.
- **Silent behavior changes** — same signature, different semantics: error handling
  that swallows more cases, cache misses handled differently, changed defaults.
- Whatever the review profile says has caused incidents here before.
