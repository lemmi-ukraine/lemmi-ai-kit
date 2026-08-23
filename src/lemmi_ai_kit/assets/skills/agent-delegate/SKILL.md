---
name: agent-delegate
user-invocable: true
metadata:
  type: task
description: >
  Delegate ONE scoped task to a named worker agent — codex, cursor-agent, grok, deep-reasoner
  (Opus subagent), fast-worker (Sonnet subagent), or cross-session (a peer Claude Code session the
  user drives) — using the standard brief contract, then verify and report the result. Use when the
  user says "delegate this to codex", "ask grok", "have cursor do it", "get a second opinion from
  codex/grok", "hand this to another session", or names a specific worker for a specific task. For
  multi-subtask coordination across several workers, use /orchestrate instead.
---

# Agent Delegate — one brief, one worker, verified

Single-shot version of the orchestration flow: build a proper brief, dispatch it to the named
worker, verify what comes back, report. You stay accountable for the result.

## Usage

```
/agent-delegate <worker>: <task>
/agent-delegate codex: find the root cause of the flaky websocket test
/agent-delegate grok --second-opinion: is this migration plan safe? <context>
/agent-delegate fast-worker: add missing type hints in src/utils/
```

Workers: `codex` | `cursor` (cursor-agent) | `grok` | `deep-reasoner` (Agent tool, model opus)
| `fast-worker` (Agent tool, model sonnet) | `cross-session` (a peer Claude Code session). If no
worker is named, pick per the routing table in `../orchestrate/SKILL.md` and say which
you chose.

## Process

1. **Probe.** External worker: check the CLI exists (`command -v <cli>`); if missing or
   unauthenticated, say so and offer the nearest native fallback (codex/grok → deep-reasoner,
   cursor → fast-worker). Don't fail silently into doing the work yourself.
2. **Brief.** Write the brief per the contract — one concern, inlined context, self-checkable
   definition of done, short report format. The contract itself is
   `../orchestrate/SKILL.md` § "The brief contract" (all **7** items apply here,
   including the DoD's zero-hit-grep self-check, the discriminating-token rule for presence checks,
   item 5's "the completion checklist is ALWAYS in scope regardless of the declared file set",
   item 6's target-branch assertion before every commit, and item 7's "every list in the brief is a
   starting set" — file set, governing documents, and blockers all age);
   template: `../orchestrate/references/brief-template.md`. If the task needs decisions
   the brief can't pin down, surface that to the user instead of delegating mush.
3. **Mode.** Opinion/analysis (`--second-opinion`, reviews, diagnosis) → read-only mode.
   Implementation → write-capable, clean `git status` first. Exact CLI invocations:
   `../orchestrate/references/external-agents.md`. Codex plugin installed →
   prefer `/codex:rescue` (add `--background` for long runs).
4. **Dispatch.** External CLIs via Bash (`run_in_background: true` for anything non-trivial,
   stdout to a file); native workers via the Agent tool. Do not do the worker's job in parallel
   yourself.
5. **Verify.** The worker's summary is a claim: read the actual diff/output, run the
   definition-of-done check. If the result is off, either re-dispatch with a corrected brief
   (default) or fix trivially yourself — say which you did.
6. **Report.** What was delegated, to whom, in which mode; the verified outcome with evidence;
   anything off-brief the worker flagged.

## Cross-session mode

`cross-session` is the one worker you **cannot spawn and cannot block on**. It is a peer Claude
Code session a human drives, with its own context window and its own approval loop. Route a whole
spec slice or a long implementation here; route anything you could await to a subagent instead.

The Process above changes in three places:

1. **Probe → not applicable.** There is no CLI to check. Instead confirm the slice is genuinely
   separable: name the files it owns, and confirm no other in-flight session owns them
   (`parallel-session-safety` §1).
2. **Dispatch → emit, don't call.** Write a dispatch brief the user carries to the other session.
   On top of the normal brief contract it must carry:
   - **Preconditions as command + expected-result pairs**, never prose. `git rev-parse --verify
     <ref>` → resolves. `git status --porcelain` → empty. A prose precondition you author is the
     same defect as trusting one you receive, and it has already shipped false.
   - **The return path**: `.ai/handoffs/{YYYY-MM-DD}-{slug}.md`, and the instruction to write the
     hand-off there per the contract in `parallel-session-safety` §9. Never ask for a paste-back.
   - **The verification commands** you will run on return, stated up front so the delegate can
     satisfy them.
   - **Isolation**, if this runs concurrently with another peer: a git worktree, or a declared
     disjoint file set. Never dispatch parallel peers that share writable paths.
   - **A layer pin, when the slice is a stacked-PR layer**: the branch, its base, the
     `parallel-session-safety` §10 base-verification preconditions, and the forbidden operations —
     stack surgery and outward actions (`gh stack sync`/`rebase`/`modify`/`merge`/`submit`, any
     push) stay user-authorized at session boundaries. **Paste the layer's whole row from
     `.specs/{initiative}/topology.md`** (branch, base, deliverable, risk class, lane, review
     audience) — a delegate that has to infer where its work belongs picks the checked-out branch,
     which is how 28 commits of 7 commit types landed in one PR. If no topology exists yet, the
     dispatch is premature: run `stacked-pr-planner` first.
3. **Verify → run the hand-off's own commands.** When the hand-off appears, execute its
   `## Verification` block and check `## Durable anchors` resolve in git. A delegate session is a
   model; delegated completion claims have been fabricated before. Never merge on a claim.

Because hand-offs are untracked, treat the file as a pointer: everything durable must already be in
git. If it is missing, the work is missing — not just the note.

## Second-opinion mode

With `--second-opinion` (or when the user asks to "compare" or "get another take"): run the
worker read-only on the question, do NOT share your own or any other worker's answer with it,
then present both takes and your synthesis — agreements, conflicts, and your recommendation.
