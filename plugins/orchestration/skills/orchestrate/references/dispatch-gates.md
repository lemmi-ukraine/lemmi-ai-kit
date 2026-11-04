# Dispatch gates — failure shapes from the moment a brief goes out to the report back

Companion to `SKILL.md` § "The brief contract" (items 7–10) and § 2 "Dispatch". Unless a section
states a lower evidence level, every shape below was measured in a multi-session initiative; the
numbers are corpus measurements, not targets.

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
deliverable-path STOP precondition in every brief and repeat the check at the write, because a path
absent at the precondition can exist by the time the worker writes it
([12k](../../parallel-session-safety/references/shared-index-protocol.md)); and check the escalation
file and the deliverable path before auto-dispatching.

## 6. Designing the gates that guard a dispatch — three measured failure shapes

- **A deliverable-path gate detects DONE and is structurally blind to IN-FLIGHT.** Every gate tests
  either an input being ready or an output being absent, and that pair is exactly the signature of a
  session already mid-flight — an open session has produced no deliverable yet, so it is
  indistinguishable from "never dispatched". The two states are causally linked: **clearing a blocker
  is what resumes the sessions parked on it**, so the chance of a live peer *peaks* at the moment a
  gate reads clear. A complete gate set is not a sufficient one; add a liveness check (claim file,
  recent mtime, the peer's own register row) before dispatching into a cleared blocker. The stub a
  cross-session delegate writes first is the claim file (see
  [cross-session mode](../../agent-delegate/SKILL.md)).
- **A gate written as a literal count decays into a false STOP the moment its directory legitimately
  grows** — three instances in one initiative. `wc -l == 7` meant "the corpus is present"; write
  `>= 7`, or an existence loop over the seven names. Encode the predicate you mean, never an
  incidental measurement of it.
- **"Read at dispatch" is not "current."** In a many-writer tree a worker's source documents can be
  rewritten hours later — by the very orchestrator that dispatched it — and the worker will keep
  arguing from the stale copy. Staleness has no minimum elapsed time; tell workers to re-read
  governing documents at close, not only at start.

## 7. A changed decision reaches only the prompts someone sweeps

A prompt quotes the decision, spec or plan it was written under and keeps that wording after the
source moves. `stacked-pr-planner` Step 6 sweeps pending briefs when the branch topology is
revised; a decision, a returned spec or a revised plan has no such trigger. Evidence level:
observed in one cluster of hand-off notes, not yet repeated; defaults to adopt and re-measure, not
calibrated rules. Each check is a command or a comparison:

- **Sweep on the change.** In the same edit session, grep every dispatched and pending prompt for
  the old wording and for the name of each row or file the change touches (a search for the old
  wording misses a prompt that names the row by id only). The step that receives a returned spec
  runs this as a "conflicts with the spec" pass over the dispatch prompts.
- **Date the plan a session follows.** Record the modification time of each plan file when a
  session starts and again before it hands back, and have the session say which plan version its
  work follows; a plan that changed in between is reconciled before the hand-back is accepted.
- **Check every row a prompt names against the register text.** Read the row as the plan's register
  states it, not as the prompt paraphrases it. When two prompts share a fix, check the row in both:
  an "or" between alternatives is read as a split, and the row then closes in neither.
- **Compare a foreign prompt's edit list with its rows' homes before pasting it.** A prompt written
  in another repository or session lists the files its author saw. Compare that list with the files
  each named row's register text puts at home, and add what the rows require before the prompt goes
  out.
- **Look for a live session before rewriting a dispatch file.** Another session may be using it:
  check the hand-off folder by file time, the session's scratch folder times, `git reflog -3` and
  the host's live-session list. A change meant for a running session goes into an addendum keyed to
  its state, and the next prompts are gated on a board line that session itself checks.

## 8. A report to the operator opens with the answer, or with the action only the operator can take

Evidence level: observed in one project's notes, not yet repeated; defaults to adopt and
re-measure, not calibrated rules.

- **A long deliverable carries the short answer.** Put the two- or three-line answer to the question
  the operator literally asked before the evidence, so nobody has to ask for the restatement; for an
  initiative plan that is the goal, the session count by type and the pull-request stack.
- **A stop at an action only the operator can take opens with that action and its owner.** When the
  work is blocked on something only the operator can do (a credential, a push, a release, a
  decision), the report's first lines say what the action is, who does it and what stays blocked
  until then, before any state.
- **A bare "proceed" after such a stop is unresolved.** It does not name the action: re-check the
  gate with the command that reads it, and while it is closed ask ONE question with explicit
  options; never read the word as consent to bypass the gate. A "proceed" that answers a presented
  spec at its approval stop is the approval that stop asked for; this rule is about a stop at an
  action the operator has to take.
- **An answer that picks no option is a deferral.** The one question a bare "proceed" draws is
  asked once: a reply that picks none of its options (a remark, a rule, another bare "proceed")
  leaves it open. Record the deferral, with the path each option would take, and do not ask the
  same question again unless the operator gives a clear yes.
- **When a default was offered and no answer arrives, take exactly the default and say so.** A
  tighter option you would have preferred goes into the report as a suggestion, not into the work.
