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
  multi-subtask coordination across several workers, use /lemmi-ai-kit-orchestration:orchestrate instead.
---

# Agent Delegate — one brief, one worker, verified — [pack prerequisites](../../README.md)

Single-shot version of the orchestration flow: build a proper brief, dispatch it to the named
worker, verify what comes back, report. You stay accountable for the result.

## Usage

```
/lemmi-ai-kit-orchestration:agent-delegate <worker>: <task>
/lemmi-ai-kit-orchestration:agent-delegate codex: find the root cause of the flaky websocket test
/lemmi-ai-kit-orchestration:agent-delegate grok --second-opinion: is this migration plan safe? <context>
/lemmi-ai-kit-orchestration:agent-delegate fast-worker: add missing type hints in src/utils/
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
   `../orchestrate/SKILL.md` § "The brief contract" (**every** item applies here); the preamble
   every worker is pointed at is [`assets/worker-preamble.md`](assets/worker-preamble.md);
   template: `../orchestrate/references/brief-template.md`. If the task needs decisions
   the brief can't pin down, surface that to the user instead of delegating mush.
   **Boilerplate host rules are copied; the MEASUREMENTS inside them are not transferable.** One
   brief carried the correct rule (*measure line endings in bytes, never `grep -c $'\r$'`*) attached
   to a wrong measurement of the specific target file, then promoted that measurement into a
   pass/fail criterion — so obeying the DoD literally would have normalised all 144 line endings of
   a file the session was only meant to append a section to, which is the whole-file-rewrite hazard
   the rule exists to prevent. Re-measure every file-specific fact **at brief-writing time**, and
   never let a boilerplate paragraph supply a number about *this* file.
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
   anything off-brief the worker flagged. Save each hand-back report verbatim and stamp last:
   [hand-back and stamps](references/hand-back-and-stamps.md).

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
   - **The hand-off stub, before any precondition**: the brief has the delegate create the hand-off
     path it names as a stub the hand-off lint accepts, with an operation that fails if the path
     exists (or read the write tool's created-or-replaced answer). An existing path or a reported
     replace is a stop: write nothing more and report it. A failed precondition sets the stub's
     Status to `blocked`. The stub is [`assets/handoff-stub.md`](assets/handoff-stub.md). (Observed
     in a small sample, not calibrated.)
   - **Preconditions as command + expected-result pairs**, never prose. `git rev-parse --verify
     <ref>` → resolves. `git status --porcelain` → empty. A prose precondition you author is the
     same defect as trusting one you receive, and it has already shipped false.
   - **The return path**: `.ai/handoffs/{YYYY-MM-DD}-{slug}.md`, or `{YYYY-MM-DD}-{slug}--{part}.md`
     for a second note of the task that day, and the instruction to write the hand-off there per the
     contract in `parallel-session-safety` §9. Never ask for a paste-back.
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
   `## Verification` block and check that `## Durable anchors` resolve in git. The support CLI
   does that for the one hand-off you were handed, and only `--resolve-anchors` makes it look at
   the anchors; a dead one prints as a note line, not an error, and the exit code stays 0, so read
   the output (set `KIT_CORE_PLUGIN_ROOT` and `KIT_PROJECT_ROOT` as the pack README says):
   `uv run --no-project --directory "${KIT_CORE_PLUGIN_ROOT}/src" python -B -m lemmi_ai_kit lint handoffs <file> --resolve-anchors --project "${KIT_PROJECT_ROOT}"`
   A delegate session is a model; delegated completion claims have been fabricated before. Never
   merge on a claim.

Because hand-offs are untracked, treat the file as a pointer: everything durable must already be in
git. If it is missing, the work is missing — not just the note.

## Second-opinion mode

With `--second-opinion` (or when the user asks to "compare" or "get another take"): run the
worker read-only on the question, do NOT share your own or any other worker's answer with it,
then present both takes and your synthesis — agreements, conflicts, and your recommendation.

## Resuming a worker

A scripted run (a workflow) has hazards of its own that a stopped worker does not: read
[runtime hazards](references/runtime-hazards.md) before you message, resume or trust one.

- **After a usage limit.** A sub-agent that a usage limit stopped can be resumed with `SendMessage`
  once requests are accepted again. Say what you measured and what is left, and re-read the state by
  command first: its last words can predate its last write. Small sub-agents resumed more than an
  hour after the stop finished normally (observed once), and a sub-agent that had already finished
  re-sent its old report when messaged (observed once). A worker that wrote checkpoints is resumed from its latest one ([worker preamble](assets/worker-preamble.md), section 3).
- **Near the context window.** Do not resume a session that ended near its window: the resume
  compacts almost at once, and past the prompt-cache lifetime it first re-reads the whole context
  uncached (reasoned, not tried). Resume only a session well under its window and within that
  lifetime; otherwise start a fresh session whose brief points at the return note of the first.
- **After a refusal by the platform.** A sub-agent can be refused mid-run by an organization-policy
  error (an HTTP 403 whose text says the organization has disabled the access it used) while its
  parent session keeps working. Read it as a permission decision, not a tool failure, and do not
  route around it. Quote the refusal verbatim in the report, and keep the dead worker's partial
  report under a new name, so that the brief's rule that an existing return note stops a second run
  does not stop the rerun. Retry the route at most once, at a later gate (one small read-only agent
  first costs less than relaunching), and when it is refused again hand the operator the brief as a
  pasteable session prompt (the `cross-session` worker). Say in the report which independent read is
  missing, because the approval decision then passes to the operator. (Observed more than once; the
  same route answered again later.)
