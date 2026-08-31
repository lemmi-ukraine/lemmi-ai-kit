---
name: orchestrate
user-invocable: true
metadata:
  type: workflow
description: >
  Run the current task as an orchestrator (tech lead): plan and decompose the work, delegate
  scoped subtasks to cheaper/faster workers — native subagents (deep reasoning on Opus,
  mechanical work on Sonnet/Haiku) and external CLI agents (codex, cursor-agent, grok) — run
  independent pieces in parallel, verify every result before merging, and synthesize. Use when
  the user says "orchestrate", "orchestrator mode", "act as tech lead", "delegate this",
  "fan out to codex/cursor/grok", or hands over a large multi-part task and wants the main
  (expensive) model to spend its tokens on judgment, not file editing. Scope is ONE session's
  task — for work spanning several sessions, run initiative-planner first and orchestrate its
  sessions one at a time. Do NOT use for tasks where the judgment IS the work (one hard design
  call, one gnarly bug needing a single coherent thread) — keep those in one agent.
---

# Orchestrate — plan, delegate, verify, synthesize

You are the orchestrator. Your job is judgment: decompose the goal, route subtasks to the
cheapest worker that can do them well, review what comes back, and own the final result.
Most of an agent run is reading files, writing patches, and running checks — none of that
needs orchestrator-tier tokens. Spend yours on the plan, the briefs, and the merge decisions.

## Worker roster and routing

| Worker | How to run | Route here |
|---|---|---|
| **deep-reasoner** | `Agent` tool, `model: "opus"` | Reasoning-heavy phases: architecture, complex debugging, algorithm design. Ask for a concise, actionable conclusion — not a transcript. |
| **fast-worker** | `Agent` tool, `model: "sonnet"` (or `"haiku"` for trivial) | Mechanical work: boilerplate, tests, formatting, renames, simple scoped edits. |
| **explorer** | `Explore` agent type | Read-only fan-out search when you only need the conclusion. |
| **codex** | `/codex:rescue --background` when the Codex plugin is installed; else `codex exec` (see [references/external-agents.md](references/external-agents.md)) | A peer senior engineer from a different model family. Independent takes, second implementations, root-cause passes. **A peer, not a reviewer, and that is a trust level: have externally authored code reviewed adversarially before it merges.** Its diff is a claim like any worker's — read the actual files, do not merge the summary. |
| **cursor-agent** | `cursor-agent -p …` via Bash | Cheap, fast scoped implementation subtasks (Composer-class); parallel grunt work when native fast-workers are busy or you want a different toolchain. |
| **grok** | `grok -p …` via Bash | Another independent perspective; second opinions, research-flavored questions, `--best-of-n` for small self-contained problems. |
| **cross-session** | Dispatch brief out → handoff file back, carried by the user (see `agent-delegate`) | A peer Claude Code session the user drives. Route here for work that needs its own context window and its own approval loop — a whole spec slice, a long implementation. **You cannot spawn it and cannot block on it**, so this is the one worker whose result arrives asynchronously through the filesystem, not a tool return. |

If a custom subagent named `deep-reasoner` or `fast-worker` exists in `.claude/agents/`, prefer
it; otherwise use the model override on the generic `Agent` tool as shown above.

**Availability probe (once per session, before the plan):** `command -v codex cursor-agent grok`.
Route only to what exists; native subagents are always available. CLIs evolve — on first use in a
session, sanity-check flags against `<cli> --help` (the cheatsheet documents the verified shapes).

## When NOT to orchestrate

Stay a single agent when:
- the judgment is the work — a hard design call, a bug that needs one coherent thread of thought;
- the plan must stay coupled — every step's outcome changes the next step;
- **you cannot name the subtasks** — if the decomposition isn't crisp, orchestrating just adds
  hand-off overhead and drift.

Delegate the scoped pieces even then (a test run, a survey of call sites), but keep the thread.

## The brief contract

Every delegation gets a written brief. A good brief has exactly:

1. **One concern** — a single goal, not a bundle.
2. **Enough context that the worker doesn't re-explore the repo** — name the files, paste the
   relevant snippets/constraints, state the conventions that apply. Workers don't invent the plan.
3. **A definition of done the worker can check on its own** — a command that must pass, an
   observable behavior, a concrete artifact. **Run every zero-hit DoD grep against the brief's own
   required literals before dispatch.** A brief that mandates a verbatim footer naming
   "Pydantic/response-model ordering, GCS prompt ops, realtime-session lore" while its DoD demands
   0 hits for `pydantic|GCS|realtime` in the same file is jointly unsatisfiable; the worker resolved
   it by paraphrasing and flagging the conflict, but a weaker one would have silently failed a side.
   A conflict found by the worker costs a round-trip; found by the author it costs nothing.
   **Presence-checks need tokens the OLD text cannot produce.** A precondition grep for
   `must-have\|red.flag\|Persona-specific WARM\|motivation` predicted 0 hits on a pre-feature file
   and returned **7** — `motivation` is an ordinary domain word the old file already used 7 times,
   which reads as "someone already synced" and would have justified skipping the sync-and-backup
   jobs entirely. A marker can also fail the other way by naming the *spec's* vocabulary rather than
   the *artifact's*: `red.flag` matched 0 in BOTH copies because the shipped feature was called
   "Résumé risk scan". Pick discriminating tokens, verify by running the grep against the old copy
   and requiring 0, and report **per-pattern counts, never a combined total**, so one generic word
   cannot mask the others. A precondition that fails open ("nonzero ⇒ assume done ⇒ skip the
   backup") deserves the strictest pattern in the set; prefer a hash comparison where an exact
   artifact is expected.
4. **A report format** — what to bring back so you can decide quickly (see
   [references/brief-template.md](references/brief-template.md)).
5. **The completion gates ride in the DoD, run BEFORE the handoff, and operator questions are
   self-addressed.** An implementation brief's definition of done includes the AGENTS.md
   task-completion checklist (post-task-review for 3+ files, learnings extraction) — **and the brief
   must state that it runs before the worker writes its return handoff, not after.** The handoff is
   the only thing you will read; one written first carries whatever the review would have corrected,
   and you inherit it as fact (measured 2026-08-15: a pre-review handoff shipped a false gate claim
   and two stale counts). In ≥5 sessions of the 2026-08 window the
   operator had to type "perform task completion review, fix all necessary" because workers treated
   the brief as the whole contract. Any question a worker escalates to the operator must be
   self-contained in plain language and must name its addressee — a worker's question once left the
   operator asking whether it was "to me or to the orchestration ai agent". **This clause was added
   2026-08-07 and did not work: the operator answered "i do not undertand" in ≥5 sessions before it,
   and 9 more times across 7 sessions after it.** Every post-fix recurrence was in ordinary
   conversational output, not in a dispatch brief — so the test is not "is the brief
   self-contained" but **expand every board ID, metric name and acronym on first use in any turn
   addressed to the operator** (the recurrences cite `I7`, `E5/E7/E8`, `db redim`, "300 seconds").
   **The completion checklist is ALWAYS in scope, whatever the declared file set says.** A worker
   closed with *"learnings extraction — still deferred because `.ai/learnings.md` sits outside my
   declared file set"*, and 12 sessions in the window never ran the review at all. The disjoint-file
   partition exists to stop destructive write collisions; `.ai/learnings.md` and
   `.ai/ai-changelog.md` are append-only, do not collide destructively, and `python -m lemmi_ai_kit lint`
   catches the merge artifacts that do occur. State this exemption in the brief — a scope
   rule that does not name its own exceptions gets read as exempting the obligations too.

6. **The target branch, as an assertion the worker runs — not as prose.** The brief carries its
   layer's branch from `.specs/{initiative}/topology.md`, and the worker asserts
   `git rev-parse --abbrev-ref HEAD` equals it **immediately before every commit**, staging with
   `git commit --only <paths>` from the *first* commit. Planning is not the failure here: in the
   08-05..08-19 window a topology existed, was committed, and was edited 10× while the orchestrator
   made **zero** `git checkout`/`switch` calls — so **89 commits and 245 files** (including a
   database migration and both deploy configs) landed on one branch named `docs/…`, which became a
   single PR carrying 34% of the window's commits — unreviewable. A separate
   session recorded *"I committed into another session's staged work, and onto their branch"* — four
   commits that needed cherry-picking back. If a brief forbids branch switching ("switch no
   branches"), then **the orchestrator owns placement** and must say, in the brief, where the
   worker's output will be committed and by whom.
7. **Every list in the brief is a starting set written before the mechanism was known — say so in
   the brief.** Three of its lists fail the same way, and the worker cannot tell which sentences
   aged:
   - **The file set.** A brief's declared files are a scope boundary drawn before anyone knew where
     the fix lives; the required file was the one it omitted. The worker must derive its sweep from
     the *claim* (2–3 phrasings, grepped tree-wide) and report **"N named / M actually carried it /
     K found outside the list"** — over-inclusion is caught free by grepping before editing, but
     under-inclusion is invisible unless someone deliberately searches outside the list.
   - **The governing documents.** A brief is not a complete statement of what governs the task:
     search `.specs/` by the **symbol you are about to change**, not by the brief's doc list. One
     dispatch missed four `tasks.md` items and two use-cases that constrained the exact function
     being edited.
   - **The blockers.** A brief goes stale *inside its own wave* — a peer session clears a blocker
     while the brief still names it. So a return hand-off must re-check every inbound blocker **in
     the CLEARED direction** and name the command that settled it, not merely restate it as open.

   Give the brief a `Written-at:` SHA so the worker can date every claim in it, and state explicitly
   that inherited claims are to be verified rather than adopted — the one time that instruction was
   present, it is what caught a wrong figure before it propagated.

## Protocol

### 1. Plan first, then execute
Decompose the goal into briefs. Present the plan — subtasks, routing, parallel groups, what you
keep for yourself — before dispatching (run the plan-critic self-review first, per AGENTS.md).
Keep coupled, load-bearing pieces in your own thread; parallelize only independent, well-bounded
ones.

**First, is this an initiative rather than a task?** If the work has more than one deliverable, AND
will outlive this session, AND has an operator gate before it is done — **stop and run
`initiative-planner`.** It owns the charter (goal, hypothesis, falsifiers), the decomposition into
sessions, the *derived* concurrency cap, and the operator critical path, and it emits artifacts that
outlive this session. Then come back here to run one of the sessions it planned.

**For multi-deliverable work inside this session, run `stacked-pr-planner` — it is not optional, and
stating the rule here is not doing it.** A version of this paragraph existed, unchanged, through the
initiative that put a DB migration at position 17 of 20 in a single mixed PR; the step was skipped
and nothing detected the omission for two days, because **a rule with no procedure and no detector
does not fire**. That skill owns risk classes, review lanes, the layer table and its command-shaped
re-plan triggers — do not restate them here — and emits `.specs/{initiative}/topology.md`. Mechanics
and fallback: `.ai/git-stacked-pr-workflow.md`.

**Scout before you partition when copies may have diverged.** For any fork-sync or multi-copy
reconciliation, spend one read-only scout that computes `git hash-object` per file per copy plus a
few structural greps, and classify each file *identical* / *strictly-older* / *divergent* /
*no-superset*. Byte-identical copies collapse instantly, divergent files get evidence-backed
winners, and the genuinely three-way files surface as "no copy is a superset ⇒ real merge required"
rather than as a pick — so real merge work is budgeted only for that class. Content hashes beat
mtimes, which bulk copies stamp uniformly and which are the only provenance an untracked tree has.

### 1b. Context and usage budget — decide WHERE work runs, before it runs

The measured failure mode (2026-08-02→04) is inline-by-default: the orchestrator argued "do that
part in this session — no handoff needed", fanned out inline, had ≥20 workers killed mid-wave by
the 5-hour usage limit across 3 sessions, and moved to a fresh session only after "very long and
expensive per turn" — in 2 of 3 observed moves the USER had to initiate it ("already overloaded").
Three rules, enforced at this step because dispatch is where the choice exists:

- **Preflight the usage window before every wave.** Check the remaining usage window (whatever
  your client exposes — a statusline rate-limit feed, or the provider's console) before any
  fan-out of ≥3 workers. Past the warn threshold: do not start the
  wave — checkpoint first (continuation notes + workflow `resumeFromRunId` lines), then wait or hand
  off. A wave that dies at the wall costs re-dispatch AND duplicate-dispatch races: every resume
  message must state who else is on the item ("two workers ran this assignment" was found by the
  worker, not the orchestrator).
- **Epic implementation slices leave the session by default** — the plan-time rule, now owned by
  `initiative-planner` (step 3 assigns each slice a session; step 4 derives what may run at once).
  What still binds you at run time: the orchestrator thread keeps plan, briefs, verification and
  synthesis only, and **the orchestrator editing production files across waves is a dispatch
  trigger, not diligence.**
- **Hand the orchestrator itself off on a leading trigger.** Write the kickoff/continuation doc at
  the first wave boundary and keep it current; move to a fresh orchestration session when the next
  wave would not fit comfortably in the remaining context/window. "This one is very long and
  expensive per turn now" is the lagging signal; the user saying "overloaded" means the handoff is
  already late.
  **This rule was written down, cited twice in-session, and still did not fire — the operator
  initiated the handoff.** A trigger phrased as a judgement ("would not fit comfortably") has no
  moment at which it obviously fires, so make it a wave-boundary *checklist item*: at the end of
  every wave, state the handoff decision explicitly — "continuing, N waves left" or "handing off" —
  rather than waiting to notice. A rule that only fires when you remember to consult it is not a
  control (see `session-retrospective`: count "carried the rule and violated it anyway" separately).
  And **a capability invented mid-initiative dies at the handoff unless it is written into this
  skill**: O2 used headless peer dispatch 7×, O3 used it 0× — the technique existed only in the
  previous orchestrator's context. When you improvise a mechanism that works, land it in §2a before
  the handoff, not in the handoff doc.

### 2. Dispatch

**Two defaults, both measured, both violated in the 08-05..08-19 window. Apply them before
choosing a worker.**

> **These two defaults are prose, and prose has not moved these numbers — so read them off the
> plan, not off memory.** `.specs/{initiative}/execution-plan.md` §3 carries a REQUIRED `Dispatch`
> column (`auto` | `headless` | `pasted`) per session, and §1 records the cap as
> `derived N / dispatched M`. Before dispatching, read those two fields and dispatch what the plan
> says; if you are about to deviate, change the plan first so the deviation is recorded rather
> than re-derived. `grep -c 'pasted' .specs/<init>/execution-plan.md` is the whole check, and it
> is what turns "43% of sessions were hand-pasted" from a 129-session transcript sweep into one
> command.
>
> **Transition rule, because the column is new.** For a plan authored from 2026-08-20 onward, a
> missing `Dispatch` column means the plan is not yet executable — send it back to
> `initiative-planner`. For a plan that predates the column (measured 2026-08-20: exactly one,
> `.specs/<initiative>/execution-plan.md`), do **not** bounce it and do not
> block in-flight work on a documentation gap: state the mode and the `derived / dispatched` pair
> in your own dispatch note for each session you launch, and backfill the column the next time
> you touch the plan.

**Default 1 — auto-dispatch (§2a), not a brief for the operator to paste.** Emitting a brief the
human carries into a new terminal (§2b) is the *fallback*, for work that genuinely needs the
operator's own approval loop — not the normal path. Measured: **56 of 129 sessions (43%) opened
with a hand-pasted brief**, 26 on one day, with the operator acting as transport. One orchestrator
had already proved the alternative — 7 headless launches, four concurrent — and the **next
orchestrator on the same initiative used none**, because the practice lived in that session
instead of in this file. If you are about to write "paste this into a new session", first say why
§2a's launcher will not do.

**Default 2 — parallel, up to the cap; serialize only on a *named* contended file.** Dispatch
every unblocked session at once, bounded by the concurrency cap `initiative-planner` derived at
plan time (`.specs/{initiative}/execution-plan.md`). Serialization needs a specific file two
sessions would both write, stated in the brief — not a general feeling that ordering is safer.
Measured: one orchestrator planned *"Window 1 … Window 2 — start immediately after"*, the operator
had to ask **twice** ("Can we run them in parallel", "can i tun them simultaniously?"), and the
serialization rationale was then **proven false by the worker**. Re-derive the cap per wave; do not
inherit a previous wave's serialization.

- Native subagents: send independent `Agent` calls in a single message so they run concurrently.
- External CLIs: run via Bash with `run_in_background: true` so you can keep working; you are
  re-invoked when they exit. Cap parallel **writers** at what the workspace tolerates — parallel
  writers must be isolated by **declared disjoint file sets** (never new git worktrees — standing
  user rule 2026-08-07, see `parallel-session-safety` §11; overlap ⇒ sequential); opinion/analysis
  workers run read-only and can fan out freely.
- **Partition by inventory, not by batch.** Enumerate the FULL file inventory first and assert
  every file class has an owner — or an explicit not-in-scope entry. A fix fan-out partitioned by
  audit batch left `workflows/*.md` belonging to no batch, so two live dead references survived all
  9 fixers and every per-batch DoD, and only an independent tree-wide sweep caught them. Give any
  *tree-wide* decision one tree-wide verification grep at the end: a "global" decision executed
  through per-scope owners is exactly as global as the union of the scopes.
- Safety: prefer read-only/plan modes for opinion tasks (`codex exec` default sandbox,
  `cursor-agent --mode plan`, `grok --permission-mode plan`). Grant write access only for
  implementation briefs, only workspace-scoped, never bypass/danger modes. Ensure `git status`
  is clean (or checkpoint) before any worker may write.

### 2a. Launching a headless `claude -p` session — measured mechanics

Whether fan-out is *economic* is a plan-time question (`initiative-planner` step 5.1 and its
`../initiative-planner/references/dispatch-economics.md`). These are the
run-time facts, all verified on CLI **2.1.224**, 2026-08-15:

- **`-p` and `--bg` are mutually exclusive.** The CLI rejects the pair naming the conflict —
  *"--print never starts the interactive session that `claude agents` attaches to."* Launch under the
  Bash tool's `run_in_background` instead; same outcome, different mechanism.
- **Always append `< /dev/null`.** Without it every launch prints *"no stdin data received in 3s"*
  and stalls three seconds — thirty wasted seconds across a ten-session wave.
- **Pass repo-relative paths, never absolute POSIX ones.** Measured: a `/nonexistent-probe.md`
  argument reached the CLI rewritten to sit under the Git Bash install root. MSYS rewrites
  `/abs/path` that way, so `--append-system-prompt-file /abs/…` silently loads the wrong file.
- **`--append-system-prompt-file` exists but is absent from `--help`'s flag list.** Confirmed by
  differential probe: it returns `Error: Append system prompt file not found` where an invented flag
  returns `error: unknown option`. Use it to inject
  `.claude/preambles/spawned-session-host-rules.md` — spawned sessions do **not** inherit `AGENTS.md`.
- **`--effort` is a real flag** with a validated enum (`low·medium·high·xhigh·max`). The `Agent`
  tool has no effort parameter, so `/effort` inside a prompt string remains the fallback for native
  subagents only.
- **Validate a launch table before dispatching it, at zero API cost:** append a sentinel flag
  (`--zzz-sentinel`) to each row; `unknown option '--zzz-sentinel'` proves every real flag parsed.
  **This checks flag names and syntax only** — `--model` has no enum (`--help`: *"Provide an alias …
  or a model's full name"*), so a typo'd model passes the check and fails after the session starts.
  Verified by a control row carrying a bogus model, which the sentinel harness wrongly passed.
- **Background subagents inside a `-p` run are cut off at ten minutes** by default, which would
  **silently truncate** a long research session. Raise it with
  `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` (`0` removes the cap) — set it in settings `env`, not as an
  inline shell prefix, which defeats this host's prefix-anchored permission rules.

### 2b. Dispatching to a peer session (cross-session)
A peer session is not a tool call: you emit a brief, the user carries it, and the result comes back
as a file. Three rules make that survivable — the full contract is in `agent-delegate`
(dispatch-brief shape) and `parallel-session-safety` (handoff artifact schema):

- **Preconditions are commands, not prose.** Write every state claim as something the delegate
  runs (`git rev-parse --verify <ref>`, `git status --porcelain`), with its expected result. A
  prose precondition in a brief you author is the same defect as trusting one you receive — and it
  has already shipped false ("already merged/committed" when it was not).
- **Name the return path** in the brief: `.ai/handoffs/{YYYY-MM-DD}-{slug}.md`. Never ask the user
  to paste results back by hand; that is the ritual this replaces.
- **Parallel peers must be isolated.** Two sessions writing one tree is the measured failure mode
  (HEAD moving mid-task, torn-tree suite verdicts). Give each a declared disjoint file set; if the
  sets overlap, dispatch them sequentially. **Never create a new git worktree for isolation**
  (standing user rule, 2026-08-07 — the 2026-08 worktrees caused the collisions
  `parallel-session-safety` §11 documents).
- **Stack layers are pinned; surgery is boundary-only.** A brief dispatching a stacked-PR layer
  names the branch and its base and carries the base-verification preconditions from
  `parallel-session-safety` §10. Delegates never run stack surgery or outward actions
  (`gh stack sync`/`rebase`/`modify`/`merge`/`submit`, any push) — those are user-authorized at
  session boundaries, where layer PRs open as drafts.

### 3. Review before merging — results are claims
A worker's summary is a claim, not verification. For every returned result: read the actual
diff/files, run the brief's definition-of-done check yourself (or have fast-worker run it), and
reconcile against the plan. If something's off, **rewrite the brief and spin another worker** —
don't silently patch over it yourself unless the fix is trivial.

**The review loop has three skills and none is optional:**

- **`branch-diff-review`** when the work is **committed but has no PR yet** — a teammate's or an
  agent's branch, measured against `origin/dev`. It emits a durable `tasks/TECH-*-review.md` so the
  findings can be routed after this session ends; `pr-review-concise`'s comment budget and posting
  gate do not apply because there is nothing to post on.
- **`pr-review-concise`** for reviewing a layer or a stack. Depth follows the lane the planner
  assigned — deep on the migration and backend layers, none on journal prose. Its output budget is
  enforced: our AI review comments measured a **2,359-char median against a human reviewer's 176** on
  the same PRs, and every one of those comments was *correct*. Correctness is not the bar; a comment
  the author did not want is a false positive regardless.
- **`pr-comment-resolver`** for addressing what comes back. **Fixes go in the branch that OWNS the
  code, cascading bottom-to-top — never collected into a new top-of-stack PR.** That shortcut was
  taken twice and produced a silent merge-train dependency: merging the bottom PR alone shipped a
  security hook still unregistered. The cascade itself is a user-authorized boundary operation
  (`parallel-session-safety` §10) — the resolver stops there and hands back.

### 4. High-stakes decisions — independent parallel takes
For decisions that are expensive to get wrong (architecture choice, tricky root-cause, risky
migration strategy): task 2–3 workers from *different families* (e.g. deep-reasoner + codex, or
deep-reasoner + codex + grok) on the same brief **in parallel, without showing any of them
another's answer**. Synthesize the best of all takes yourself. Keep your own context lean —
request conclusions, not transcripts.

### 5. Synthesize and report
Own the merge. Report per brief: what was asked, who did it, what came back, how it was verified,
what you rejected and why. End with the state of the overall goal against its definition of done.

### 6. Close the initiative — run `initiative-cleanup`, and only after the findings are resolved
An orchestration does not end when the last PR merges. It ends when the board tells the truth and the
scaffolding is gone. **Order is Review → Resolve → Clean Up**: cleanup retires the specs that
document what still needs fixing, so running it while `pr-comment-resolver` still has open findings
deletes their context. Run `initiative-cleanup` (approval-gated, destructive): settle every board row
against `git grep -l <symbol> <ref>` — **not** `--is-ancestor`, which answers a different question
after a squash-merge and produced three consecutive "nothing is merged" verdicts when all twelve PRs
had merged — write the forward plan **before** deleting anything, partition every deletion target
per file into tracked vs untracked (untracked is recoverable by nothing), retire parked specs with
their revival triggers instead of deleting them, and run the comment pass over what the initiative
added.

Skipping this is why two board rows read `UNCOMMITTED` after their work was committed, and why an
entire measurement corpus was deleted with no copy anywhere.

## Long-horizon work → `initiative-planner`

Work that outlives this session is not an orchestration variant — it is a **planning** problem, and
`initiative-planner` owns it end to end: the charter and its falsifiers, the decomposition into
typed sessions, the derived concurrency cap, the operator critical path, and re-plan triggers that
are commands rather than prose. Run it **before the first brief**; then orchestrate one session at a
time against the artifacts it wrote.

What stays yours within a single long session: write the definition of done into a checkable
artifact first, then loop plan → dispatch wave → verify → update the artifact.
