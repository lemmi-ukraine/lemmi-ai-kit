---
name: parallel-session-safety
description: >
  Coordination rules for running several Claude Code sessions, sub-agents, or spec
  workstreams against ONE working tree. Covers file-ownership partitioning and its real
  failure modes, shared repo-root artifacts a skill writes by default, "modified since
  read" as a collision alarm, verify-don't-reapply, globally exclusive Docker suites,
  and why a suite verdict or a hand-off's state list is untrustworthy in a contended
  checkout. Auto-loaded background knowledge when work is split across parallel
  sessions/agents, when a spec assigns files to workstreams, or when diagnosing a
  torn-tree symptom (unexplained suite failures, stale-read Edit failures, files that
  changed under you). Fires on the literal symptoms too: "HEAD switched under me",
  "committed under me", "two things just changed under me", a branch that switched
  mid-task, a suite reporting failures in files this session never touched, or tens of
  uncommitted files appearing from another session's work.
user-invocable: false
metadata:
  type: reference
---

# Parallel Session Safety — One Tree, Many Writers

## When This Skill Activates

- A spec, plan, or user request splits work across parallel sessions, workstreams, or sub-agents
- You are about to run a partitioned build where each session owns a set of files
- An `Edit` fails "modified since read" on a file you believed you owned
- A test suite reports failures that point at production wiring you did not touch
- You are writing or picking up a hand-off brief that enumerates tree state
- You are about to run the Docker test suites and another session may be active

This checkout is routinely multi-session. Every failure mode below is **silent** — none of
them produces an error that names the real cause.

---

## 1. Disjoint file ownership is necessary, not sufficient

The orientation claim "disjoint file ownership ⇒ parallel runs are safe in one working tree"
holds only under an unstated precondition: **each session id runs at most once**.

Ownership disjointness does not protect a session from *itself*. A duplicate run of the same
session id collides on its OWN files. Observed shape: a workstream read its 5 owned files,
drafted edits, and every `Edit` failed "modified since read" — the re-read showed all 5
already at the exact target end-state, written by a concurrent run of the same session.

**Qualify the guarantee whenever you state it**: disjoint ownership is safe *assuming each
session id runs once*. Launching a session twice is the realistic break.

## 2. A spec-recorded ownership split is not a runtime lock

A coordination decision written into a spec does not reach a session that already loaded its
plan. A concurrently-running session executes ITS plan, not the latest recorded agreement.

Observed shape: two same-day sibling specs had a written ownership split (plan A owns the
hypothesis loop; plan B reduces to a pointer) — yet plan B's session landed a full
implementation plus edits to two files plan A owned, because it had started before the split
was recorded.

**Protocol:**
1. Check collision signals at **every phase/wave boundary**, not just at start:
   `git status` of the other owner's directories, plus file mtimes (edits minutes old
   distinguish fresh-parallel from pre-existing).
2. Fresh-read every shared file immediately before editing.
3. On a real ownership collision, **STOP and surface options** — do not silently absorb or
   revert the other session's work. Refactor-preserving-semantics beats both.
4. Budget for a reconcile step (their-work → agreed-architecture) instead of assuming
   disjointness held.

## 3. "Modified since read" is a collision alarm, not an annoyance

Treat a stale-read failure on an **owned** file as possible pre-completion:

- **Re-read** the file.
- **Verify** current state against the spec / source-of-truth.
- If it already satisfies the target: **VERIFY-don't-reapply.** Re-applying the drafted edit
  overwrites concurrent work and can clobber a cleaner version.
- Still run the required gate and a fresh final-state grep — the files mutated under you.
- **Report provenance honestly**: "verified, not authored".

## 4. Shared repo-root artifacts are collision surfaces

A skill that writes a repo-root artifact by default (a tracking index, a progress file,
`MEMORY.md`, a learnings file) will have every parallel session write the SAME path — stomping
each other and the convergence session's canonical output. The file-ownership partition that
makes the run safe usually never assigned that file to anyone.

**Before a partitioned parallel build, inventory every skill-default output path each session
will touch.** If contended: redirect to a session-local location (or keep the verdict in the
session's report) and let the convergence session produce the canonical artifact.

> The standing example was a review skill that wrote a fixed `Prompts_Review.md` to the repo
> root by instruction, which put 14 records at root in a fortnight (12 later deleted). Writing
> to a per-run `{date}-{slug}` path under `.ai/` fixed that instance. The class is not fixed —
> check any new skill's default output path.

### 4a. The partition never exempts the completion checklist

The disjoint-file partition exists to stop **destructive** write collisions. It is routinely
misread as a scope boundary that also excuses the task-completion obligations, because
`.ai/learnings.md` is never in a worker's declared file set. Measured 2026-08-19: a session closed
with *"learnings extraction — still deferred because `.ai/learnings.md` sits outside my declared
file set"*, and 12 sessions in that window never ran the completion review at all.

`.ai/learnings.md` and `.ai/ai-changelog.md` are **append-only**: concurrent appends do not
destroy each other, and `python -m lemmi_ai_kit lint` detects the duplicate-header/spliced-entry artifacts a
merge can produce. So they are always in scope, for every session, regardless of the partition —
state this explicitly in each brief rather than relying on the worker to infer the exception. A
scope rule that does not name its own exceptions gets read as exempting the obligations too.

## 5. The Docker test suites are globally exclusive

`docker-compose.test.yaml` pins `container_name: test-postgres-db` on the `db` service. A pinned
name is global to the Docker daemon, so `-p <other-project>` does **not** isolate a second stack —
the second run fails to start its DB. `db` is the only pinned service and that is sufficient to
block everything: all six runner services declare `depends_on: db: condition: service_healthy`.

Consequences:
- Two sessions running suites concurrently silently fight over one database.
- A clean-worktree baseline comparison is impossible while any other stack is up, so
  "is this failure pre-existing?" cannot be answered the obvious way.

**Coordinate before running the suites when more than one session is active.** If
baseline-vs-change comparison becomes routine, note that dropping the `container_name` pin is
necessary but **not sufficient** — `db` also binds host port `5434:5432`, which collides
independently of the project name. Both have to go for `-p` isolation to actually work.

## 6. A suite verdict over a contended tree is void

A suite run while other sessions edit the checkout samples a **torn state that no commit ever
contained**, and the failure is unreproducible by the time you read it.

Observed shape: 30 failed / 36 errors, all `TypeError: ActionBuildContext.__init__() missing
1 required positional argument` raised from *production* wiring. Nothing was broken — one
file had gained a required field while its caller had not yet been saved. Minutes later both
were consistent.

**Protocol:**
- Snapshot `git diff HEAD --stat` **before and after** any suite run whose result you will
  report. If the set changed, the run is void.
- `git status --short` under-reports: uncommitted work in a subsystem you are not reviewing
  is invisible without `git diff HEAD --stat -- <dir>`.
- Prefer a `git worktree` (worktree + Docker mounts = zero risk to your tree) or an explicit
  "no one edits while this runs" hand-off for anything reported as a gate.
- **Never report a torn-tree failure as a regression in the branch under review.**
- To prove a failure is inherited rather than yours: `git worktree add ../verify dev` and run
  the same suite there. One run settles it.

## 7. Hand-off briefs are claims sheets

A brief's state assertions are exactly as reliable as the command whose output its author
happened to see — and the harness truncates rendered `git status` past ~2 kB, so rows silently
vanish. One brief enumerated six uncommitted files against an actual twelve; the missing six
were another feature's in-flight work and the direct cause of a confusing 36-error suite run.

- **Picking one up:** re-derive with `git status --porcelain --untracked-files=no`, plus
  `git diff HEAD --stat` (and `git diff --cached --stat` for the staged/unstaged split)
  before acting on a single state claim.
- **Writing one:** generate the file list from `--porcelain` output, never from a truncated
  status render, and re-verify every state claim against disk at write time.
- **Claiming nobody owns it:** grep `.ai/handoffs/` and `.specs/*/plan.md` BEFORE writing that work
  is unowned, unenforced, or untracked. Deliberately-deferred work is owned in exactly those two
  places, and `.ai/handoffs/` is **gitignored** — so no code grep, `git log`, or tracked-file search
  will surface it, and the absence reads as "nobody is on this". A 2026-08-13 review shipped
  "nothing enforces the merge-order constraint" for two env vars while
  `.ai/handoffs/2026-08-13-interview-parking-env-propagation.md` sat at `ready-for-review` owning
  precisely that, and stated the cloud was already behaving correctly. Same defect class as the
  negative-existence rule in `AGENTS.md`, but a search surface that rule does not name:
  `ls .ai/handoffs/ | grep -i <topic>` costs one call and inverts the finding.

## 8. Filesystem timestamps die at the first git op

git materializes files on stash apply/pop, checkout, and merge, recreating them with fresh
timestamps. After any tree-mutating git operation, **no** filesystem timestamp distinguishes
your edits from git's rewrite — and switching from `LastWriteTime` to `CreationTime` fails
identically, because recreation resets both.

Scope "recently changed files" by `git status` / `git diff --stat` against a known ref, or by
filename/content reasoning. If one timestamp field proves reset by a git op, do not try the
sibling field.

**`stash@{N}` rots the same way, and more quietly.** A stash index is a LIFO *position*, not an
identity: every `git stash push` by ANY session renumbers every existing reference. Unlike a
deleted file (loud 404), a shifted index fails silently by resolving to the wrong stash — six
initiative docs carried `git show 'stash@{4}^3:<path>'` recovery commands that still *ran* and
returned a different stash's contents after a week of normal multi-session work. In any doc meant
to outlive the session, resolve to the SHA once at write time (`git rev-parse 'stash@{N}'`) and
reference `<sha>^3:<path>`, noting the human-readable stash message beside it; the SHA survives
reordering and even a drop (until gc). When auditing docs after stash activity, grep for
`stash@{` as a rot signal.

## 8b. Extracting your own hunks does not exclude someone else's

Filtering hunks by whether their added lines carry your markers is marker-**based**, not
marker-**exclusive**. One kept hunk carried three appended entries *and* a parallel session's 40
entry deletions, because a `learning-consolidator` drain was editing the same region; the filtered
patch looked correct and applied cleanly, and the leak was invisible in the patch itself. Presence
of your content in a hunk says nothing about the absence of theirs.

After any hunk-level extraction, verify by **counting the entities the file is made of** (entries,
functions, rows) against the base — 41 headings at base vs 18 after applying is what exposed it.
Deletions are the leak signal: a file whose staged diff shows `-0` cannot have swallowed anything,
and any unexplained deletion count is a stop.

## 9. The hand-off artifact contract

§7 says a brief's claims are unreliable. This is the format that makes them checkable. It applies
to any hand-off written for another session to pick up — the `cross-session` worker in
`agent-delegate` dispatches against it, and `python -m lemmi_ai_kit lint handoffs` enforces it.

**Path:** `.ai/handoffs/{YYYY-MM-DD}-{slug}.md`. Named so the return leg is a known location
instead of a paste into chat.

**Required sections:**

| Section | Contains |
|---|---|
| `## Scope` | The one slice this hand-off covers, and what it explicitly does not |
| `## Durable anchors` | Branch names, commit SHAs, spec/task paths — every fact that must outlive the file |
| `## Preconditions` | Command + expected result pairs the receiver runs before starting |
| `## Verification` | Command + expected result pairs that prove the work is done |
| `## Status` | `in-progress` / `blocked` / `ready-for-review`, plus what is NOT done |

**Preconditions and verification are commands, never prose.** Write what the receiver *runs*:

```
- `git rev-parse --verify origin/feat/x` -> resolves (branch pushed)
- `git merge-base --is-ancestor <lower> <upper>` -> exit 0 (chain connects)
- `git status --porcelain` -> empty (tree clean before starting)
```

Not `"branch x is already merged"`. A prose state claim in a hand-off you author is the same
defect as trusting one you receive, and it has shipped false: a brief asserted "already
merged/committed" when it was not, and the delegate acted on it.

**Hand-offs are untracked — so they are pointer documents.** `.ai/handoffs/` is gitignored by
decision. Every durable fact must therefore exist in git and be *referenced* here, never exist only
here. Losing a hand-off must cost convenience, not work. `## Durable anchors` is what the lint
checks for this. Never paste credentials or tokens into one.

**Parallel peers must be isolated.** Before dispatching two sessions concurrently, give each a git
worktree or a declared disjoint file set (§1 — and note it is necessary, not sufficient). Sharing
writable paths reproduces §6 exactly: a suite verdict over a tree two sessions are editing is void.
If isolation is not possible, dispatch sequentially.

**Returned work is verified, never merged on a claim.** The picker-up runs the hand-off's own
`## Verification` commands. A delegate session is a model, and delegated completion claims have
been fabricated before.

## 10. A stack cascade rewrites branches other sessions sit on

GitHub-native stacked PRs (`gh stack`, public preview 2026-07-30) make a branch chain a **shared
artifact**: `sync` / `rebase` / `modify` replay every branch above the changed layer, and
`submit` / `merge` / any push change remote state. Owning layer N does NOT isolate you from a
cascade started below N — after one, your branch points at a commit no longer in the chain, and
everything in §6 (torn-tree verdicts) applies.

- **Cascades and outward actions run only at session boundaries, user-authorized.** A boundary
  exists only when the user confirms no session is mid-layer — only the user can see all active
  sessions. A delegate session never runs `gh stack sync` / `rebase` / `modify` / `merge` /
  `submit` or any push; it commits on its own layer branch, clean-tree only. Layer PRs open as
  drafts at the session-end boundary — which on the interactive path means passing `--auto` or
  setting the Draft toggle, because bare `gh stack submit` opens PRs ready for review.
- **"No session is mid-layer" is not sufficient — check the WORKTREES too.** A peer that is
  clean, idle, and finished still blocks a cascade if it merely has an affected branch checked
  out: git refuses to move a branch another worktree holds. Verified on this repo —
  `git branch -f <branch> HEAD` returns
  `fatal: cannot force update the branch '<branch>' used by worktree at '<path>'`, and a rebase
  fails the same way mid-cascade, which is the worst time to discover it. Preflight before any
  cascade and detach or switch anything affected:

```
- `git worktree list --porcelain` -> no worktree holds a branch in the stack
- (per blocker) `git -C <worktree> switch --detach` -> frees the branch
```
- **A layer pin in a brief is commands, not prose** (§9 format). Pickup preconditions for layer
  work:

```
- `git fetch --prune origin` -> exit 0 (MUST be first — nothing else updates origin/*)
- `git rev-parse --verify origin/<base>` -> resolves (base pushed)
- `git rev-parse origin/<base>` -> <expected-base-oid>   (exact match, recorded in the brief)
- `git rev-parse origin/<layer>` -> <expected-layer-oid>  (exact match, recorded in the brief)- `git merge-base --is-ancestor origin/<base> origin/<layer>` -> exit 0 (chain connects)
- `gh stack view --json` -> matches the layer order and branch names in `.specs/<epic>/`
```

**Both additions are load-bearing, and each closes a hole the other cannot.**

- **Ancestry proves connectivity, not identity.** A chain someone else rewrote is *internally
  consistent* — every adjacent pair still passes `--is-ancestor` — so the ancestry check reports a
  healthy stack sitting on a base that is no longer the one the brief was written against. Only an
  exact OID comparison detects it, which is why the brief must **record** the expected base and head
  OIDs rather than describing the layer in prose (§9).
- **Without the fetch, every line below it reads a stale local copy.** `origin/<branch>` is a
  remote-tracking ref updated only by a fetch; `git ls-remote` queries the remote but does **not**
  update it. After a cascade rewrite, the stale refs satisfy the OID comparison too — so the fetch
  is what makes the OID check mean anything, and the OID check is what makes the fetch worth doing.

- **Moved base or plan mismatch ⇒ stop and report.** Never rebase unilaterally, never build on a
  stale base. A failing precondition before the first edit is the cheap outcome; a layer built on
  a rewritten base is §6's unreproducible failure with extra steps.

Command mapping, retained verification rules, and the manual fallback:
`.ai/git-stacked-pr-workflow.md`.

## 11. Do NOT create new worktrees — and treat the existing ones as hazards

**Standing user rule (2026-08-07): never create a new linked git worktree in this checkout — not
for branch isolation, not for peer-session or delegation isolation, not to escape a blocked
checkout.** The 2026-08 window ran 4+ worktrees at once and the operator's verdict was that the
mechanism is too complex to coordinate. Isolate parallel work with what this skill already
mandates: **disjoint file ownership (§1), pinned stack layers (§9/§10), or SEQUENTIAL dispatch
when file sets overlap.** A checkout blocked by another session's dirty files is a
**stop-and-report to the user**, not a license to isolate yourself. (This supersedes the
2026-08-04 "worktree beats stash-checkout-pop" recommendation — the mechanics remain true; the
policy forbids the move.)

Why the rule exists — one window's worktree incidents, kept for anyone handling leftovers:

- A worktree was **removed under a live session** by a peer's `/branch-switch` ~4h after its
  creator wrote "Don't remove the worktree until the branch merges" (the condition lived only in
  the creating session's transcript); a third session's probe files vanished with it.
- Checkout-refusal juggling: a branch locked to a worktree cost a 4× status / 4× stash-list /
  3× pop recovery dance.
- Hunk surgery across a worktree boundary silently carried a peer's 40-entry deletion.
- `gh stack` fails on detached HEADs ("not on any branch") and an idle peer worktree can block a
  cascade; stale unregistered worktree dirs accumulated on disk.

Handling the ones that already exist: before ANY `git worktree remove`, run `git worktree list`,
check the target's dirty AND gitignored-but-local state (`.env`, venvs are silently wiped), and
confirm no live session owns it — or get explicit user approval naming that risk. Leftover
detached-HEAD/backup worktrees are swept at initiative close via `initiative-cleanup`, each under
the no-delete-until-merged check.

**Untracked deployment artifacts invert the usual staleness direction across checkouts.** Untracked
files do not travel with branches — every worktree (and every second clone) holds its own private
copy. So finishing and uploading an untracked artifact from a secondary tree makes **production
newer than the main tree**, and the standard "local is newest" instinct becomes exactly wrong: the
next main-tree edit-and-upload silently reverts the deployed feature. Git offers zero protection,
because nothing involved is tracked. `prompts/interview/persona/recruiter_hr.txt` was shipped this
way and the main tree's copy carried a fraction of the markers.

Two obligations follow, and they apply to ANY second checkout, not only to worktrees: syncing the
primary tree's mirror is part of the implementing session's definition of done (and any dispatch
brief for such work must say so), and **before editing any deployment artifact, grep it for the
newest shipped feature's markers** — a low count means you are about to edit, and possibly
re-upload, a pre-deploy version.

---

## 12. The index is shared — `git add` is the collision, not `git commit`

The staging area is **one process-wide file** (`.git/index`) for every session in this checkout.
That makes `git add` — not the commit — the moment another session's work joins yours, and a
pathspec does not protect you: a `git add -- <paths>` whose own `git status` had just come back
clean still produced a **38-file commit**, two of them another session's `.claude/skills/` edits
(counted with `git show --stat <OID>`; an earlier note claimed 5, which did not hold at the
revision actually measured — state the OID with any such count).
Anything another session staged before you is already in the index, and your pathspec adds to that
set rather than replacing it.

Four rules follow.

- **Verify and stage in SEPARATE tool calls, then verify again after staging.** Combining the check
  with the action it gates is what loses the race — three collisions in one session came from exactly
  that pattern. The only trustworthy check is `git diff --cached --stat` read *after* the `add` and
  immediately before the commit; a pre-`add` `git status` is a claim about a moment that has passed.
- **Never `git checkout -b` raw in a contended tree.** A bare `checkout -b` inherits whatever HEAD
  currently is, which another session may have just moved — four commits landed on another session's
  branch this way. Use `/branch-switch` (it writes the pre-switch backup) and assert
  `git rev-parse --abbrev-ref HEAD` equals the branch you intend **immediately before every commit**.
- **A branch switch can hide another session's committed files, and the blocker you then log is
  stale.** Files present a moment ago vanish because they live on the branch you left, not because
  they were lost: `git ls-tree -r --name-only <other-branch> -- <dir>` found **125** files a session
  had just reported missing. Read other branches in place (`git show <ref>:<path>`,
  `git ls-tree`, `git -C <path>`) instead of switching to look.
- **The cheap live detector: diff `git status` immediately before and immediately after any
  checkout.** Any path that appears or disappears without your having touched it is another session
  writing concurrently — it catches a live peer without polling, a watcher, or a lock file.

Corollary for claims: "verified unchanged" and "staged" are **perishable** here. Only a content hash
or a commit SHA survives long enough to be quoted in a hand-off; re-derive anything else at write
time (§7, §9).

---

## Cross-references

- `AGENTS.md` — the hard don'ts (shared-checkout bullet, append-only-file clause, sub-agent
  and hand-off claims contract). This skill holds the protocols; AGENTS.md holds the rules.
- `spec-driven-dev` — phase/wave boundaries are where §2's collision checks belong.
- `test-conventions` — suite mechanics.
- Shared `.ai/*.md` files corrupted by a merge are enforced mechanically, not here: run
  `python -m lemmi_ai_kit lint` (see AGENTS.md).
