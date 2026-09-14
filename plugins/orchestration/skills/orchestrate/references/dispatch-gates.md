# Dispatch gates — six measured failure shapes at the moment a brief goes out

Companion to `SKILL.md` § "The brief contract" (items 7–10) and § 2 "Dispatch". Every shape below was
measured in a multi-session initiative; the numbers are corpus measurements, not targets.

## 1. A brief's RULES need the same suspicion as its LISTS — item 7 covers only the lists

A brief can carry a *correct and measured* rule ("exclude both feature READMEs from the code layer,
because each cites flow documents that are untracked") scoped to the files it happened to name, and a
worker will obey it there and never apply it to the artifact it is actually building. That is how one
commit shipped the exact dead pointer the rule existed to prevent. Restate every brief rule as a
**predicate over your whole output**, not over the brief's file list, and re-run it against what you
are about to commit.

## 2. A takeover is a dispatch, and it needs its own inbound step

A handover checklist verifies the initiative's *inputs* — tree clean, staging union, no double-claim,
corpus present — and typically none of its *outputs*. Nothing in that path routes through
`.ai/learnings.md`, the initiative's escalation file, or any deliverable's mtime, so a countermeasure
recorded by a previous session has no delivery mechanism at takeover and the same collision recurs.
When taking over an initiative, read the escalation surface and the learnings buffer before the first
dispatch, not the tree alone.

## 3. The forward plan is a wave-boundary DELIVERABLE, not a response to being asked

Measured: in one 215-tool-call session the operator asked for it three separate times — *what to do
next*, then *next steps plus prompts*, then *analyse and prepare the next steps*. None was a re-ask
(each followed genuinely new work), which is exactly why it is easy to miss: every request was
satisfied, and the pattern appears only when the messages are read together. The session produced
verification depth unprompted and the forward plan only on request. At the end of every verification
round, emit unasked: what is unblocked, what is blocked with the command that unblocks it, and the
paste block for each. **A rule that fires only when someone asks is not a control.**

## 4. Intersect the fix's file set against every peer's pending STAGING list, not just `git status`

A dirty file tells you *that* a peer holds it, never *why*, and one class is destroyed by any code
edit: a **comment-only** branch whose entire claim is a no-code-change gate reporting `changed=0`. A
code change landing there first breaks that branch's own gate, the owning session cannot see it
coming, and ` M` from a comment pass is indistinguishable from ` M` from anything else. Ask what each
peer intends to assert about its files.

## 5. One kickoff block, one dispatch CHANNEL — name it, because nothing else records ownership

A handover that both tells the next orchestrator to "dispatch what is unblocked" *and* hands the
operator ready-to-paste kickoff blocks creates two channels with no shared register: the execution
plan's derived/dispatched pair is read by nobody who is pasting a block. Measured: the same brief ran
twice in the same minutes — once auto-dispatched as a subagent, once by the operator — and the
subscription's usage window went 12% → 76% in 30 minutes with three sessions live, the subagent dying
at HTTP 429. **The collision was survived only because the brief carried a deliverable-path existence
check as a STOP precondition**, so the second run wrote to scratch instead of overwriting. So: state
per block *"the orchestrator dispatches this"* or *"the operator pastes this"*, never both; keep the
deliverable-path STOP precondition in every brief; and check the escalation file and the deliverable
path before auto-dispatching.

## 6. Designing the gates that guard a dispatch — three measured failure shapes

- **A deliverable-path gate detects DONE and is structurally blind to IN-FLIGHT.** Every gate tests
  either an input being ready or an output being absent, and that pair is exactly the signature of a
  session already mid-flight — an open session has produced no deliverable yet, so it is
  indistinguishable from "never dispatched". The two states are causally linked: **clearing a blocker
  is what resumes the sessions parked on it**, so the chance of a live peer *peaks* at the moment a
  gate reads clear. A complete gate set is not a sufficient one; add a liveness check (claim file,
  recent mtime, the peer's own register row) before dispatching into a cleared blocker.
- **A gate written as a literal count decays into a false STOP the moment its directory legitimately
  grows** — three instances in one initiative. `wc -l == 7` meant "the corpus is present"; write
  `>= 7`, or an existence loop over the seven names. Encode the predicate you mean, never an
  incidental measurement of it.
- **"Read at dispatch" is not "current."** In a many-writer tree a worker's source documents can be
  rewritten hours later — by the very orchestrator that dispatched it — and the worker will keep
  arguing from the stale copy. Staleness has no minimum elapsed time; tell workers to re-read
  governing documents at close, not only at start.
