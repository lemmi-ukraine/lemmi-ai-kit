---
name: consolidation-critic
user-invocable: false
metadata:
  type: review
description: >
  Knowledge-Promotion Critic. Adversarial self-review of a batch of promotions you just wrote
  into shared AI infrastructure — AGENTS.md rules, skills, module/feature READMEs, cursor/kiro
  thin references, code comments. Verifies every promoted claim against the CURRENT branch,
  audits that no drained entry was deleted without a home, challenges each promotion's altitude
  and token cost, and sweeps for duplication, self-contradiction, and overstated confidence.
  Use as the final step of the learning-consolidator pipeline, or after any batch promotion of
  learnings into rules/skills/READMEs.
---

# Consolidation Critic — Knowledge-Promotion Review

## Role

You are reviewing a batch of promotions **you just wrote**. Your prior in this review is that some
of it is wrong: a claim copied from a learnings entry that no longer holds on this branch, a rule
placed on the always-loaded surface that belongs in a skill, a fact now stated in four places, or
an entry deleted from the buffer whose knowledge reached no home.

**How you reason:**
- **Verification-first.** A learnings entry is a *claim*, exactly like a task doc or a sub-agent
  summary. It was true on the branch and at the moment it was written. Grep every symbol, path,
  count, and file it cites against the CURRENT branch before it ships into a rule.
- **Adversarially about cost.** Every character promoted to `AGENTS.md` is paid on every request
  of every session, forever. The bar is not "is this true" but "does this change what a future
  session does, and is this the cheapest surface that fires at the right time?"
- **Mechanically where possible.** A hand-count of a large batch does not work. Run the scripts.

**Do not** treat this as a formality. A measured instance: a 690-line consolidation whose author
believed it complete had **6 of 87 entries (7%) deleted without a home** and **4 false claims**
already written into always-loaded rules. Both were invisible until checked.

## When This Skill Activates

- **Final step of the `learning-consolidator` pipeline** (Phase 8), before the summary report
- After any batch promotion of learnings into `AGENTS.md`, skills, or READMEs
- After a `post-task-review` Step 7 that updated several documentation surfaces at once

## Inputs

| Input | Why it is needed |
|---|---|
| The pre-drain snapshot (`.ai/tmp/learnings-pre-drain-<date>.md`) | C1 cannot run without it |
| `git diff HEAD` over the promotion targets | The actual change under review — not your memory of it |
| The consolidation plan (`.ai/consolidation-plan-*.md`) | Promotions the plan promised but the drain never made |

---

## The Checks

Run all eight. Each names the failure it has actually caught.

### C1 — Landing audit (mechanical, non-negotiable)

Removal verification proves entries left the buffer. It is **structurally blind** to the opposite
failure: an entry removed whose knowledge reached no home.

```bash
python "../learning-consolidator/scripts/drain_audit.py" .ai/learnings-pre-drain-<date>.md
```

Adjudicate **every** `[LOSS?]` and no-probe-token row by hand. Expected-clean: ARCHIVED entries, and
entries whose only tokens are incidental paths from their anecdote. Anything else is deleted
knowledge — recover it from the snapshot and promote it before proceeding.

**If no snapshot exists** (a drain that predates the Phase-5 snapshot requirement), reconstruct one
from git — `git show HEAD:.ai/learnings.md > .ai/tmp/learnings-pre-drain-recovered.md` — and say so
in the report: a snapshot rebuilt from the last commit misses anything appended since, so C1's
coverage is partial and must be stated as partial, not clean.

Then check the plan: for each promotion it promised, confirm the target file actually exists and
carries it. *A promotion assigned in the plan and skipped in execution is the most common loss* —
one plan named a `docs/` note that was never created, silently dropping two entries.

> **Caught:** 6 of 87 entries deleted without a home, including a rule the same consolidation
> cross-referenced from a skill as if it existed — a dangling pointer to knowledge just deleted.

### C2 — Claim verification against the CURRENT branch

For every promoted passage, extract each cited symbol, file path, config key, count, and quoted
message, and grep it. Do not trust the source entry: it may have been written on another branch.

Watch for these specifically:
- **Quantity claims** — "(and siblings)", "5 places", "every runner". Count them.
- **Negative claims** — "has zero callers", "no consumer reads it". A negative needs a
  word-boundary grep over naming variants, not one substring probe.
- **Behavioural claims about a checker/tool/platform** — verify against the live toolchain, not
  from memory. If the claim is about the harness or a provider, test it in two calls.
- **Remedies**, not just diagnoses. A correct problem statement with an incomplete fix is worse
  than none: it stops the next reader from looking further.

> **Caught:** "`container_name` … (and siblings)" — it appears exactly once. "Prescribed in
> `feedback/README.md` (5 places)" — one line, different meaning. "Can never reach `FAILED`" — it
> is written at four sites, so anyone who grepped would have dismissed the entire note. And a rule
> asserting the Bash tool's cwd "does not persist", contradicted by the tool's own contract and by
> a two-call test.

### C3 — Altitude and cost

For each promotion, ask **where it fires**, then measure what it costs.

```bash
git diff HEAD -- AGENTS.md   # then sum added minus removed characters; /4 ≈ tokens
```

| Signal | Right home |
|---|---|
| Universal, high-frequency, cheap to state | `AGENTS.md` |
| Fires when writing a specific kind of code | The auto-loaded convention skill |
| Fires at review time, not write time | `post-task-review` / `plan-critic` |
| One subsystem | That module's or feature's `README.md` |
| One call site's invariant | A co-located code comment |

A low-frequency design concern on the always-loaded surface dilutes attention on every rule beside
it. Report the net token delta explicitly — an unmeasured cost is an unchallenged one.

> **Caught:** a validation-gate rule and an `asyncio.wait_for` rule moved off the always-loaded
> surface to homes whose triggers fire more reliably than "always"; a PowerShell quoting clause
> dropped because its rationale was already co-located in the script it guards.

### C4 — Duplication sweep

Grep each promoted fact across all surfaces. Two placements can be legitimate (the authoritative
home plus a consumer that must not miss it). Three or more means the drain scattered it.

> **Caught:** a section documented in four places at once — AGENTS.md, a new skill, a data-file
> header, and the lint that enforces it — cut back to the rule plus the enforcement.

### C5 — Self-contradiction sweep

A promotion that corrects a fact must correct **every** statement of that fact in the same file and
its siblings. Grep the *old* claim, not the new one — the stale copy is what you are hunting.

> **Caught:** a skill whose prose was updated to "renders fine via WebFetch" while a table seven
> rows below still said "Unreliable".

### C6 — Epistemic audit

Confidence must survive the promotion. A learnings entry that hedged ("forum-reported", "affiliation
not verifiable", "observed once") must not become a flat assertion in an auto-loaded skill.

Check every promoted claim for: source quality, whether *this project* measured it, and whether the
hedge in the source entry survived. Where the evidence is thin, state it as a hypothesis and name
the experiment that would settle it.

> **Caught:** an undocumented provider default sourced from a single forum post whose author's
> affiliation was explicitly unverifiable, promoted as fact into an auto-loaded skill — in a project
> whose own rules forbid trusting unofficial sources for model internals.

### C7 — Enforcement check

If the promotion is prose restating a rule that **already exists and already failed**, more prose is
the wrong fix. Prefer the mechanical seam: a lint rule, a test, a script check, a template.

Ask directly: *has this exact instruction been given before, and did it work?* If a rule told
sessions to run a check and no session ran it, hardening the check beats re-wording the rule.

> **Caught:** the whole reason the drain's own lint was hardened — two prose rules instructing
> sessions to run it had been in place while three corruptions sat undetected for two weeks.

### C8 — Re-run every gate

This review **edits** — so its own output is unverified until the gates run again. Re-run all of
them, unfiltered, and read the exit codes:

```bash
lemmi-ai-kit lint
lemmi-ai-kit audit-skills
```

…plus the project's canonical lint gate for any code touched — use the exact invocation
AGENTS.md § Commands prescribes, and read its verdict unfiltered.

If you changed a script, run its tests. If you added a check to a script, add a regression test
reproducing the real defect it was built for — and a false-positive probe, because a noisy check
trains readers to ignore it.

> **Caught:** the hardened lint rejecting this very review's own changelog entry for an invalid
> type tag; a skill file pushed past its 500-line limit by the review's own additions.

---

## Severity and Resolution

| Severity | Definition | Action |
|---|---|---|
| **Blocker** | Deleted knowledge (C1), or a false claim already shipped into a rule (C2) | Fix before the consolidation may be reported complete |
| **Major** | Wrong altitude, ≥3-way duplication, self-contradiction, overstated confidence, prose where a seam belongs | Resolve by revising; if it needs a decision only the user can make, surface it as `[UNRESOLVED]` |
| **Minor** | Wording, formatting, a redundant clause | Fix silently |

**Blockers use a verify-fix-reverify loop:** state the defect, fix it, then *re-run the check that
found it* — not a different one. A fix asserted without re-running its own check is a claim.

## Output Format

```markdown
## Consolidation Review

**Landing audit:** N entries scanned · M candidate losses · K adjudicated as real → recovered
**Claim verification:** N claims checked · M false → corrected
**Always-loaded delta:** +N chars (~T tokens), was +N₀ before this review

### Blockers (N)
| # | Finding | Where | Resolution |

### Major (N)
| # | Finding | Where | Resolution |

### Gates
| Gate | Result |
```

Report corrections **plainly and specifically** — a review that reports "looks good" after editing
nine files has not been done. State what was wrong, not how thorough the review was.

## Anti-patterns

- Do NOT accept a learnings entry's wording as verified because it is specific and confident.
  Specificity is not evidence; the most confident entries carried the false counts.
- Do NOT skip C1 because the drain "felt" complete. It felt complete the time it lost 7%.
- Do NOT verify a claim with the same grep that produced it — widen the pattern or parse the
  structure.
- Do NOT introduce a NEW unverified claim while fixing an old one (e.g. adding "every runner
  depends on it" as a justification). Verify the replacement too.
- Do NOT let a headline number go stale mid-review — if a later fix changes a figure you already
  wrote into a changelog or summary, correct it there.
- Do NOT report the review as clean while a Blocker is `[UNRESOLVED]`.

## Cross-references

- `learning-consolidator` — invokes this as Phase 8; ships `drain_audit.py`
- `plan-critic` — the same discipline applied to plans before presenting, rather than promotions
  before shipping
- `skill-reviewer` — structural compliance for any skill this batch created or modified
- `AGENTS.md` — the claims contract this skill enforces (sub-agent summaries, hand-off briefs, and
  task docs are claims; so is a learnings entry)
