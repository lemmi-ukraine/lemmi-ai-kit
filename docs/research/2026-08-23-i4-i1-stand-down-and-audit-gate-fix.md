# I4 row I-1 — stood down, and the audit gate it was supposed to promote

**Date:** 2026-08-23 · **Session:** `lemmi-ai-kit-94` · **Row:** I4 execution-plan **I-1** (B1,
`hygiene/pack-boundaries`) · **Status:** complete for its ruled scope; the row itself was
reassigned mid-session by operator ruling.

> **Operator note before the flip:** §5 records a multi-session coordination incident. The
> engineering content is the useful part; the session-identity detail is not, and is held in the
> private planning artifacts. Trim §5 to its first paragraph if that detail should not go public.

---

## 1. What shipped

One commit: **`599be56` — "Stop audit-skills from passing a gate it never ran."** Two files, staged
by explicit path, `git diff --cached --name-only` verified before commit. No contended path staged.

Row I-1's exit criterion reads *"then `audit-skills --fail-on major` becomes promotable."* It was not
promotable. The bare command defaulted `--skills-dir` to `<project>/.claude/skills`, which does not
exist in this repo, printed *"no skills directory, so there is nothing to audit"*, and **exited 0**.

Promoting that installs exactly the pathology program doc §5f W-2 names: a detector that is trusted
*because* it reports green, having consulted nothing. The same section was written about the
vocabulary pins; this is a second instance of the same class, in the gate meant to certify the first.

**The fix** (`cli.py`, `_bundled_skills_dirs`): when `<project>/.claude/skills` is absent, audit the
skill roots the kit ships — **but only when the bundled assets resolve inside the project root.**

That containment test is the substance, not a guard clause. A blanket fallback would, in an
adopter's project, silently audit *our* fleet instead of theirs and report on a tree they cannot
fix — trading one false signal for another. In an adopter's project the kit lives in site-packages
or a plugin cache, so the fallback does not fire and they keep the existing note.

Measured, both directions:

| Invocation | Before | After |
|---|---|---|
| `audit-skills --fail-on major` (this repo) | "nothing to audit", exit 0 | `plugins/core/skills, plugins/python/skills`, 35 + 2 scanned, exit 0 |
| same, temp project with no `.claude/skills/` | note, exit 0 | note, exit 0 — **unchanged** |

Three tests in `tests/test_cli.py`, including one that disables the fallback and asserts the gate
goes vacuous again — the regression this guards. Skill counts derived from the manifest, never
written down.

## 2. Two findings against my own commit, from the review

Both found by `post-task-review` step 4, both real, **neither fixed** — the file moved to
`plugins/core/src/lemmi_ai_kit/cli.py` and is held by another writer. Editing it would recreate the
collision this session stood down from. Per the skill's own trap (l), a scoped edit that cannot be
completed inside its scope is escalated, not shipped partial.

### F1 — the fallback is conditioned on absence, not on having scanned anything

An **empty** `.claude/skills/` directory still gates green. Measured on a temp project containing
one:

```
skill fleet audit: .claude/skills
  - (fleet): 0 skills; description+when_to_use total = 0 chars
0 finding(s). Findings are review input, not failures.     exit=0
```

So the hole is narrowed, not closed. Concretely: if anyone creates `.claude/skills/` in this
checkout — a developer experimenting, or a `kit-setup` run that seeds it — the fallback stops firing
and the promoted CI gate silently reverts to vacuous green. `docs/syncing-from-upstream.md:305`
promotes this command to a CI gate and describes the absence condition accurately, so the doc is
correct about a fix that is still defeatable.

**The complete fix gates on the scan set being empty, not on a path existing:** under
`--fail-on {blocker,major,minor}`, exit 1 when zero skills were scanned. I raised that option at
decision time and it was deliberately not chosen, because it changes exit codes for adopters who
gate on a project with no local skills. That trade-off is still live and is the operator's, not a
session's. Recording it because the narrower fix leaves the defect half-open and the doc now
advertises the gate as sound.

### F2 — three statements of the default, one updated

`cli.py` states the `.claude/skills` default in three places. My edit updated one.

| Site | State |
|---|---|
| `--skills-dir` help (`:132`) | **updated** — names the fallback |
| module docstring (`:11`) | stale — "audit a project's `.claude/skills/`" |
| subcommand `help=` (`:116`) | stale — same |

Textbook trap (f): a behavioural claim documented in one place is echoed in siblings. Two-line fix
for whoever holds the file.

## 3. Row I-1's deliverable state — measured, not assumed

Measured 18:58:31 unless noted. **Not my work** — recorded because it is what the row's next owner
needs, and because this session verified it rather than trusting it.

| # | Deliverable | State |
|---|---|---|
| D2 | five audit findings | **done** — both `metadata.type` added, both stray READMEs deleted, `initiative-cleanup` 555 → 499 lines (cap 500), audit reports 0 findings |
| D3 | `analyze-logs` genericized | **NOT DONE** — 68 platform mentions; all four platform-named reference files intact. Only the manifest summary line changed |
| D4 | `openai-realtime-quirks` dropped | **done** — dir gone, manifest row gone, sync-map row moved to `[[unported]]` |
| D5 | `vertical-slice` → core | **done**, and its own `SKILL.md:196` cite stripped |
| D6 | `extras` out of `PROFILES` | **done**. Note `python` was also dropped from `DEFAULT_PROFILES` — a live behaviour change to `scaffold`/`list` defaults that the brief did not ask for |
| D7 | cross-pack names by role | **done** — 0 sites remaining, three independent instruments agreeing |
| D8 | DoD-4 guard test | **done** and green; verified green *legitimately*, not vacuously |
| D12a | sync map set | **done** — `test_upstream_sync` green |

**Counted, not trusted:** 37 skill dirs = 37 manifest entries = core 35 + python 2. Re-derived at
write time.

**D3 carries a hole no deliverable tracks** (caught by the orchestration session, not by me):
`analyze-logs/references/realtime-session-events.md` is content from `openai-realtime-quirks` — the
skill D4 reports as *dropped*. The directory is gone, the manifest row is gone, and its knowledge
still ships inside another skill, un-genericized. Whoever finishes D3 owns that.

## 4. Instrument faults — three, all returning a plausible zero

Every measurement in this document was taken twice with independent tools, for these reasons.

1. **`grep -i` + `-F` + `-e` together silently matches nothing.** One directory, one instant:
   `grep -rni gcp` → 21 · `grep -rnF "GCP"` → 20 · `grep -rniF -e gcp` → **0**. Any two flags are
   fine; the trio is not. It nearly produced "D3 is already done" about a skill whose own filenames
   are `gcp-log-fields.md` and `docker-log-format.md`.
2. **The Bash tool's working directory persists between calls.** A relative-path probe after an
   earlier `cd` scanned nothing and reported `0 hits`. Caught only because the probe printed
   `files scanned: 0` beside the hit count.
3. **`git diff HEAD > backup.patch` does not back up this tree.** Patches contain no untracked
   files, and the entire post-restructure skill tree is untracked (92 files). Any snapshot taken on
   that advice contains **zero skills**. A worktree tarball is the only form that covers it. This
   correction is mine; I gave the patch advice before establishing the tree was untracked.

**Faults 1–3 have no tell.** The earlier faults recorded in this program produced numbers *too round
to be true* (a CR count equal to the line count). `0` is a plausible and welcome answer to "how much
work is left", so it reads as good news. **Make probes print their scan surface, not only their
findings** — files scanned, per-subtree counts, undecodable paths — and require two independent
instruments to agree before a count decides that work is done.

## 5. Why this row produced one commit instead of eight deliverables

Two sessions were dispatched execution-plan row **I-1** with the same `Owns` set, and a third writer
executed it concurrently. The row was reassigned by operator ruling; this session stood down having
written zero bytes into any contended path.

**The transferable finding is structural, and no existing rule catches it.** Path partition defends
*disjoint* sets from each other. It has no defence against one set being assigned **twice**, because
both assignees are correctly inside their own boundary — so nothing fires: not the brief, not the
plan's re-plan triggers, not `parallel-session-safety`. It surfaced only because this session ran
`git status --porcelain` **before its first write** and watched 0 entries become 22.

**Make that baseline a standing opener for any writing session in this tree.** "The tree was dirty
when I arrived" is unrecoverable information ten minutes later.

Two corollaries, both measured:

- **A peer's "I have written zero bytes" is true for one instant.** One session's denial was accurate
  when sent and false three minutes later, discovered from a file mtime rather than a re-announcement.
  Denial-by-poll cannot establish who is writing a moving tree. Transcript forensics can; the writer
  re-announcing on state change is cheaper.
- **In a contended tree, every measurement is stale on arrival.** Stamp them. Two sessions reported
  contradictory `pytest` verdicts 90 seconds apart, both correct for their instant. Two
  "false findings" in this session — a guard test passing with sites still open, a clean audit with a
  skill over the cap — both dissolved on re-measurement, because the writer had closed the gap
  between probes.

## 6. Gate results

| Check | Result |
|---|---|
| `ruff check` (my two files) | pass |
| `ruff format --check` (my two files) | pass |
| `basedpyright` (my two files) | 0 errors, 0 warnings, 0 notes |
| `pytest tests/test_cli.py` | 6 passed |
| Full suite at commit time | 188 passed, 5 skipped |

**A full-suite verdict on this tree is not trustworthy right now** and should not be quoted as one:
the restructure is in flight, and the failures present are path-move artifacts rather than defects.
`parallel-session-safety` says exactly this about a contended checkout; it is the shipped skill's own
rule, applied to its own repo.

## 7. Left undone, deliberately

- **Row I-1 D2–D8, D12a** — reassigned by ruling. Zero bytes written to any contended path.
- **F1 and F2 above** — the file is held by another writer; escalated rather than half-fixed.
- **Promoting `audit-skills --fail-on major` to a gate** — that is D2's call, and D2 is not mine.
  The command is now *capable* of being a real gate in this repo; F1 bounds how much that is worth.
