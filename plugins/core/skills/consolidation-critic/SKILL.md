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
| The pre-drain snapshot: a scratch file written from the buffer at the restore-point commit | C1 cannot run without it |
| `git diff HEAD` over the promotion targets | The actual change under review — not your memory of it |
| The consolidation plan (`.ai/consolidation-plan-*.md`) | Promotions the plan promised but the drain never made |
| The gate record (`.ai/consolidation-gates/<date>-plan-approved.md`) | The plan as recorded approved before any removal: a written claim C1 checks against the plan the operator saw |

---

## The Checks

Run all eight. Each names the failure it has actually caught.

### C1 — Landing audit (mechanical, non-negotiable)

Removal verification proves entries left the buffer. It is **structurally blind** to the opposite
failure: an entry removed whose knowledge reached no home. Run the audit that fits the state of the
promotions, with the same `--surface` values as the consolidator's Phase 5 audit (`--surface <glob>`
adds a home). It takes the pre-drain snapshot, a scratch file written from the buffer at the
restore-point commit, and a base ref, which is mandatory (no ref exits 2):

```bash
# Promotions still UNCOMMITTED: HEAD is the pre-promotion state.
python "${CLAUDE_PLUGIN_ROOT}/skills/learning-consolidator/scripts/drain_audit.py" \
  <pre-drain-snapshot>.md HEAD

# Promotions ALREADY COMMITTED: the commit before the promotion commit, never HEAD.
python "${CLAUDE_PLUGIN_ROOT}/skills/learning-consolidator/scripts/drain_audit.py" \
  <pre-drain-snapshot>.md <promo-commit>~1
```

Exit 1 means rows to adjudicate, not a failed run. Adjudicate **every** `[LOSS?]` and no-probe-token
row by hand. Expected-clean: ARCHIVED entries, and entries whose only tokens are incidental paths
from their anecdote. Anything else is deleted knowledge — recover it from the snapshot and promote
it before proceeding.

**If no snapshot exists** (a drain that predates the Phase-5 restore point), reconstruct one from
git into scratch: the operator writes the buffer's last committed contents to a scratch path in
their own terminal (a session never names the buffer on a shell line), deliberately NOT the byte
copy's path (the operator's local, never-committed copy of the buffer from Phase 5), so it cannot
pass for that copy, and say in the report that it is a reconstruction: it is not evidence, and a
snapshot rebuilt from the last commit misses anything appended since, so C1's coverage is partial
and must be stated as partial, not clean.

Then check the plan: for each promotion it promised, confirm the target file actually exists and
carries it. *A promotion assigned in the plan and skipped in execution is the most common loss* —
one plan named a `docs/` note that was never created, silently dropping two entries. Read the gate
record too: it is a written claim, not proof, that the operator approved this plan before the
removals, so confirm it holds the plan approved at the Phase 3 gate and report any difference.

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

**Characters are the binding number; bullets and lines are not.** Measured on a drain that promoted 9 entries into `AGENTS.md` as *extensions of existing bullets*: **55 bullets before and after, +7 lines (2.2%)** — clean against the declared metric — while the same change was **+6.8 KB (~1,700 tokens), +13.1%**. Because each bullet is one very long line, extending bullets grows cost without moving either declared metric, which is exactly the "gameable by cramming" evasion that hypothesis's own risk clause named, reached without anyone intending to game it. **A metric chosen because it is easy to count will be satisfied in the way that is easy to count.**

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

The sweep reaches the files the batch did not edit: grep the old claim in every skill, reference and
README that cites a promoted rule, because a contradiction sits where the diff does not look. The
fresh reader of C6 carries the same sweep and checks that each pointer in the batch names a section
number or a stable heading name, never only a line number or a commit id. Its return ends with what
it did not check (`post-task-review`, fix-rounds reference, section 2a).

> **Caught:** a skill whose prose was updated to "renders fine via WebFetch" while a table seven
> rows below still said "Unreliable".

### C6 — Epistemic audit

Confidence must survive the promotion. A learnings entry that hedged ("forum-reported", "affiliation
not verifiable", "observed once") must not become a flat assertion in an auto-loaded skill.

Check every promoted claim for: source quality, whether *this project* measured it, and whether the
hedge in the source entry survived. Where the evidence is thin, state it as a hypothesis and name
the experiment that would settle it.

**Fidelity read.** The checks above test where an entry landed, what its passage cites and whether
its hedge survived; none reads the rewritten paragraph beside the entry it came from, so a
paraphrase that changes the claim passes them all. A fresh reader carries the read, not you: the
author of a paraphrase reads it as faithful. You spawn it, as `post-task-review` describes one for
a fix round (section 2 of its fix-rounds reference, the planted false claim included), and brief it
to read each promoted paragraph beside its source entry in the pre-drain snapshot and list every
place it changes the claim: a narrative inverted, two techniques fused into one, a sentence
addressed to the promoter left in committed text, a dropped qualifier such as "not run" or "only".
A reader's brief carries at most four real claims, plus the planted one, so spawn one fresh reader
per four promoted paragraphs. A promotion passes only when the read lists none. The read does not
replace C1 to C8.

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
them, unfiltered, and read the exit codes (`--project` takes the absolute project root: a relative path such as `.` resolves inside the plugin, so the lint and the audit would measure nothing and still pass):

```bash
uv run --no-project --directory "${CLAUDE_PLUGIN_ROOT}/src" python -B -m lemmi_ai_kit lint --project "<absolute project root>"
uv run --no-project --directory "${CLAUDE_PLUGIN_ROOT}/src" python -B -m lemmi_ai_kit audit-skills --project "<absolute project root>"
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
| **Major** | Wrong altitude, ≥3-way duplication, self-contradiction, overstated confidence, a fidelity defect (a promoted paragraph that says more or less than its source entry), prose where a seam belongs | Resolve by revising; if it needs a decision only the user can make, surface it as `[UNRESOLVED]` |
| **Minor** | Wording, formatting, a redundant clause | Fix silently |

**Blockers use a verify-fix-reverify loop:** state the defect, fix it, then *re-run the check that
found it* — not a different one. A fix asserted without re-running its own check is a claim.

## Output Format

```markdown
## Consolidation Review

**Landing audit:** N entries scanned · M candidate losses · K adjudicated as real → recovered
**Claim verification:** N claims checked · M false → corrected
**Always-loaded delta:** +N chars (~T tokens), was +N₀ before this review
**Fidelity read:** N paragraphs · M changed claims → corrected · planted claim rejected: yes/no

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
