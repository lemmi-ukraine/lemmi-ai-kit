---
name: pr-comment-resolver
description: >
  Resolve PR review comments by fixing in the branch that OWNS the commented code and cascading
  bottom-to-top — never by collecting fixes into a new top-of-stack PR, which creates a silent
  merge-train dependency. Gives every comment a verdict with evidence before any edit, and stops at
  the cascade because force-pushes are user-authorized. Use when the user says "address the review
  comments", "fix the PR feedback", "resolve review threads", or hands over a stack review.
when_to_use: >
  "address the review comments", "fix the PR feedback", "resolve the review threads", "apply the
  review findings", "the reviewer left comments on the stack".
metadata:
  type: task
---

# PR Comment Resolver — fix in the owning layer, cascade upward

## When this skill activates

- Review comments exist on one or more PRs and need to be addressed
- A stacked chain has comments spread across layers
- You are tempted to "just put all the fixes in a new branch on top" — **that is the failure this
  skill exists to prevent**

**This skill decides where a fix goes and verifies the result. It does not own the mechanics** —
every command, cascade form and verification rule lives in `.ai/git-stacked-pr-workflow.md`.
Cascade safety and session boundaries live in `parallel-session-safety` §10. Do not restate them.

## Why this exists

Fixes were parked in a separate top-layer PR **twice** (`T1`, `T2` — stack-layer labels used
throughout this skill; `L1` is the base layer). Each time it was the *locally*
rational choice — fixing in a lower layer requires a cascade through up to 10 branches and 8
force-pushes. It produced:

- **A silent merge-train dependency.** Verified, not assumed: `.claude/settings.json` is absent at
  L1's tip and present at T2's, so **merging L1 alone ships the `cd`-guard hook still
  unregistered** — the reviewer's original finding, unfixed. Any piecemeal merge silently drops fixes.
- **Comment/fix separation:** the reviewer must be told "your comment is on PR A, the fix is in PR K",
  14 times.
- **A second review surface** nobody asked for.
- **Compounding cascade cost — the argument that actually bites.** A collect-all PR does not just defer
  the cascade; it makes every LATER cascade harder, permanently. Those two collect-all branches touch the same files at many layers, so they collide with any per-layer fix that follows.
  Measured on the L1→top sweep: **every conflict in the cascade came from those two commits and no
  others** — five hunks across four files, each one a judgment call about whether a documented deferral
  or a new fix wins. Two of the fixes turned out to duplicate work those commits had already landed, and
  the duplication was invisible until the replay surfaced it. The one-time saving was repaid with
  interest at the next sweep, and will be again at the one after that.

**The operator's instruction is explicit: fixes are applied directly into the branch that owns the
code, cascading bottom-to-top — not collected into a new PR.**

## Step 1 — Inventory the comments, then challenge every one

**Before any edit, every comment gets a verdict with evidence.** A reviewer is right most of the time
and is still a claim.

| Verdict | Meaning | Required output |
|---|---|---|
| `VALID` | Real defect, in scope | The anchor: `file:line` + the quoted code it rests on |
| `INVALID` | Not a defect | A **reasoned reply on the thread** — never a silent no-op |
| `OUT-OF-SCOPE` | Real, but not this PR's job | Where it goes instead (task doc, follow-up layer) |
| `OPERATOR-DECISION` | A trade-off or policy call, not a technical one | The options and their costs; then stop and ask |
| `STALE-ANCHOR` | The commented code moved or was rewritten since the comment | Re-locate by symbol and re-verdict. If a force-push orphaned the thread, say so and link the new one — the motivating repair orphaned 7 threads this way |

> **Every cell in the `Required output` column lands in the Step 7 operator report — never on the
> thread.** This table is how you decide; Step 6 governs what the reviewer sees. Posting the evidence
> that justifies a verdict is precisely how our replies reached a 2,404-char median against the
> reviewer's 176.

**Read the existing threads before starting.** A comment already answered, or a duplicate posted on
re-review, is not new work — duplicate-on-re-review is unsolved even in shipped tools.

**Read the CODE before starting too, not just the threads — four of 36 findings needed no change.** A
finding may already be fixed in its own layer (grep the fix, then `git branch --contains`), already fixed
*above* it (then the fix must move DOWN, not be rewritten), or **deliberately deferred with the reasoning
recorded in-code**. One migration's own docstring pre-empted the reviewer with a documented deploy
decision; two other fixes duplicated work an earlier commit had already landed, and that duplication only
surfaced later as a cascade conflict. Verdict `ALREADY-FIXED` or `OPERATOR-DECISION` and reply — do not
re-fix, and never silently override a decision whose rationale is written next to the code.

Rules:
- **Cite by symbol, not by a remembered line number.** Re-grep at write time — comment anchors drift
  ±1 even when the quote is perfect, and a line number recalled from an earlier Read is a fabrication
  risk.
- **A comment you cannot reproduce is `OPERATOR-DECISION`, not `INVALID`.** Report UNKNOWN and name
  what would settle it.
- **Fix by CLASS, not by instance.** A reviewer names the instance they happened to see; the defect
  usually has siblings. Before closing a `VALID`, grep the *category* across the tracked tree and
  fix every hit — or say explicitly which ones you left and why. A redaction verified against its
  one known instance missed two more of the same class, and a fix landed in one implementation of a
  strategy seam leaves the configured DEFAULT unfixed.
- **Never fix silently what you believe is invalid** — that removes the reviewer's ability to
  disagree and looks like agreement.
- Known false positives for this codebase are listed in `pr-review-concise` § "Known false positives
  in this codebase". A reviewer flagging one of those gets an `INVALID` with the anchor, not a change.

**Getting the comments, and posting replies.** `gh` must be authenticated first — probe
`gh auth status`; if it fails, **report UNKNOWN and ask the operator for `gh auth login`** rather than
inferring PR state from local refs.

```bash
gh api repos/{owner}/{repo}/pulls/{n}/comments   # inline review comments (the diff-line threads)
gh api repos/{owner}/{repo}/pulls/{n}/reviews    # review summary bodies — a SEPARATE endpoint
gh api repos/{owner}/{repo}/issues/{n}/comments  # PR-level conversation — a THIRD endpoint
```

**All three, or the inventory silently drops comments.** A review built from two of them misses the
summary bodies entirely.

**The GraphQL shortcut is the trap, and it caught a session building this very inventory.** Only
GraphQL `reviewThreads` carries `isResolved` — REST does not — so the convenient move is to run one
GraphQL query and call the inventory done. It covers **inline threads only**. On the L1→top stack
that produced a confident "34 unresolved threads" work list which silently dropped a summary-body
finding on L1 (*"the renamed skill still declares its old name … those edits only land in
L2, so move them into this layer"*) — a wrong-layer finding, i.e. exactly this skill's subject
matter, invisible to the query. **Use GraphQL for resolution state, then the two REST endpoints for
the surfaces it cannot see.** Report the count per surface, never one total.

Also inventory **existing dispositions before working anything**: a thread already answered `INVALID`
is not new work, and an unresolved thread may already carry a reply (resolution is a human click, so
"unresolved" never means "unanswered"). Split the work list into *unanswered* / *answered-but-open*
and say which is which.

**Auth note:** `gh auth login --with-token` rejects a token lacking `read:org`, but `GH_TOKEN=…
gh api` works for both REST and GraphQL. A failed `gh auth login` is therefore **not** evidence that
PR state is unreachable — try the API before reporting UNKNOWN.

**Remote PR state is part of the definition of done, not context the operator supplies.** Measured: **5 of 14** operator messages carried state the session had credentials to fetch itself — a corrected PR count, two PRs' failing checks, one merge conflict, two PRs' review contents. It had an authenticated `gh` throughout and used it for *posting*, never polling; it reported "ready to merge" **three times** before CI state or mergeability had been checked once. Before claiming any PR ready, check `mergeable`, the check-run conclusion **against the current head SHA**, and unanswered threads. A completion claim scoped to local commits is not a completion claim about a PR.

## Step 2 — Locate the layer that OWNS each commented line

For every `VALID` comment, find the commit that **introduced** the line:

```bash
git log --reverse --format='%h %s' -S '<the exact code from the comment>' <base>..<top> | head -1
```

**`--reverse … | head -1`, never `-1` alone.** `git log` is newest-first, so `-1` returns the most
*recent* commit touching that string — typically a top-of-stack review-fix commit. Reproduced on this
repo: the naive form named the top-layer fix commit, which would send the fix straight back to the
top of the stack. That is the failure this skill exists to prevent, produced by its own instrument.

**`-S` matches changes in occurrence count**, so a commit that merely *moves* a line does not match.
Fall back to `git log -L` or `git blame <base>..<top>` on the anchor.

Then map the commit to the owning layer:

```bash
git branch --contains <that-sha>
```

**This returns the owner AND every layer above it** — on this repo one such probe returned 12
branches, and the intuitive pick (the checked-out one) is the top. **Walk the topology table from L1
upward; the first layer whose branch contains the sha is the owner.** The list is not the answer.

**Siblings break the "walk upward" rule, so check them first.** `stacked-pr-planner` emits sibling
branches off trunk alongside the stacked spine (`B`/`S` rows), and a sibling is in nobody's chain. If
the sha is contained in a sibling, **that sibling is the owner** — there is no layer order to walk.
Only fall back to the L-row walk when the sha is in the spine.

**The owning layer is where the fix goes.** Not the top of the stack, not the branch you have checked
out, not a new branch.

**And it must be the CURRENT owning layer.** A local branch can sit far behind its remote while every
other check still passes — `merge-base --is-ancestor` succeeds, the file opens, the code looks plausible.
Measured here: `infra/interview-metrics-toolchain` was **21 commits behind origin**, and the file at that
checkout did not contain the defect verified against `origin/` minutes earlier. Fixing it there would have
produced a correct-looking commit on a stale tree. Before the first edit of any layer:

```bash
git fetch --prune origin
git rev-list --left-right --count origin/<layer>...<layer>   # must be 0	0
```

Nonzero *behind* means stop and fast-forward first; nonzero *ahead* on a branch you have not yet
touched means someone else is mid-work on it — that is a hand-back, not a merge.

**Before the first edit, verify the layer pin.** Run `parallel-session-safety` §10's six-line
precondition block against the owning layer and its base — the expected base and head OIDs, not just
ancestry, because a chain someone else rewrote is still internally consistent and passes every other
check. **A moved base means stop and report, never rebase unilaterally.**

**Switching to the owning branch is an operator action.** `/branch-switch` carries
`disable-model-invocation: true` — a session may not invoke it. Ask the operator to run
`/branch-switch <owning-branch>` and wait. The workflow doc's bare `git checkout` form assumes a
clean single-writer tree; this checkout is shared.

A fix that touches code owned by *two* layers is a signal the topology is wrong — that is a re-plan
trigger, not a reason to jump to the top. Hand back to `stacked-pr-planner`.

**If the comment is on a merged or closed PR**, the owning branch may be gone. Then the fix goes to
the lowest still-open layer that contains the code, and the report says so explicitly. **If no open
layer contains it** — the normal case once a stack merges — the code is in `dev`: open a fix branch
off `dev` and name it in the reply. Do **not** graft it onto an unrelated open layer.

### Gate 2A — emit the ownership table BEFORE the first edit, then assert it after

The "never collect fixes into a new branch" rule is stated five times in this skill, in prose. **Prose
of exactly this kind has already failed in this repo at scale** — the `cd`-prefix rule was carried in
`AGENTS.md`, in `.cursor/rules/`, and as a standing user preference, and the retrospective still
counted 577 violations, 298 of them in the single session that started *after* the rule was written.
A rule holds when something checks it. So:

**Before touching a file**, emit this table — one row per `VALID` comment, no edits until it exists:

| # | PR | anchor | introducing sha | owning layer | branch |
|---|---|---|---|---|---|

**Snapshot the branch list in the same breath:**

```bash
git branch --format='%(refname:short)' | sort > .ai/tmp/branches-before.txt
```

**After the last fix, assert both invariants — with commands, not with intent:**

```bash
# 1. NO NEW BRANCH. Any output here is the failure this skill exists to prevent.
git branch --format='%(refname:short)' | sort | diff .ai/tmp/branches-before.txt - 

# 2. FIX SET == OWNERSHIP SET. For each fix sha, the lowest layer containing it
#    must equal the "owning layer" cell written before the edit.
git branch --contains <fix-sha>
```

**A non-empty diff on (1) is not a shortcut to justify in the report — it is the defect.** If `k`
distinct layers own comments, then `k` branches carry fix commits. **One branch carrying all of them
means every fix went to the wrong place**, no matter how clean the diff looks.

The pull toward one branch is real and it is *locally* rational — it is why this happened twice
(T1, T2, both before this skill existed). The gate exists because the reasoning that produces the
mistake is sound reasoning about cost, and cannot be argued away in the moment.

## Step 3 — Group by layer and work bottom-to-top, one layer at a time

Order the `VALID` fixes by layer depth, lowest first. **After committing at layer N, cascade upward
from N before touching any layer below it.**

The mechanism and both failure shapes (a silently *lost* commit, a *stranded* ref — neither produces
a git warning) are in `.ai/git-stacked-pr-workflow.md` § *Work the layers in ONE direction*. Read it
there; do not re-derive it.

Run the fast suite after the **first** layer of a stacked change, not after the last — the same doc
records why.

## Step 4 — Before any cascade: back up, then stop

**Backup tags before any cascade, kept until merge.** A lost commit is recoverable only while the
object survives.

```bash
# every branch the cascade will move — take the list from the topology table, not from memory
# NOT ONLY the topology table: `--update-refs` moves every ref pointing into the replayed
# range, which includes branches the table never mentions (one cascade moved three unrelated
# ones). A backup scoped to your INTENT cannot cover a tool whose blast radius exceeds it.
# Back up every local branch that is an ancestor of the top, or simply snapshot all refs.
for b in <layers from .specs/{initiative}/topology.md>; do
  git tag "backup/${b//\//-}-$(date +%Y%m%d)" "$b"
done
```

(Flat, hyphenated names match the tags already in this repo — a `backup/<layer>/<date>` form with a
slashed branch name produces a four-segment ref.)

**Then stop.** A cascade rewrites branches other sessions may be sitting on. Per
`parallel-session-safety` §10, `sync` / `rebase` / `modify` / `merge` / `submit` and **any push** are
**user-authorized boundary operations** — a boundary exists only when the operator confirms no
session is mid-layer, because only the operator can see all active sessions.

Preflight and hand back:

```bash
git worktree list --porcelain        # no worktree may hold a branch in the stack
git status --porcelain               # tree clean
git stash list                       # nothing of yours parked
```

A worktree that is clean, idle and finished **still blocks the cascade** if it merely has an affected
branch checked out — git refuses to move a branch another worktree holds, and it fails mid-cascade,
which is the worst time to find out.

**The remedy is to detach, not to remove.** `git -C <worktree> checkout --detach` frees the ref while
leaving the worktree and its contents intact, so the cascade can move the branch and the other session
loses nothing. Removing the worktree is never necessary for this, and creating a new one is barred by
standing rule. Re-attach afterwards if that session wants the branch back.

**Hand back with commands, not prose** (`parallel-session-safety` §9): every precondition the operator
or the next session runs, with its expected result, plus the expected base and head OIDs — a brief
without OIDs cannot be verified at pickup, because ancestry alone passes on a chain someone else
rewrote.

## Step 5 — After the cascade: verify the chain link by link

The cascade itself is `gh stack sync` on the native path or the `rebase --update-refs --onto` form in
`.ai/git-stacked-pr-workflow.md` — read it there; the dropped-commit trap is subtle and documented.

**Run `.ai/git-stacked-pr-workflow.md` § *Verify the chain on the REMOTE, link by link* in full.** It
is mandatory on the native path too, and it is not optional after a successful-looking push — a
rejected `--force-with-lease` leaves the old SHA on the remote silently, and a `push --dry-run` proves
acceptance, not connectivity. The doc also has the `ls-remote`-does-not-fetch trap.

Three things that doc requires, listed here only so you cannot claim the step is done without them:

- `git fetch --prune origin` **first** — nothing else updates `origin/*`.
- `git merge-base --is-ancestor origin/<lower> origin/<upper>` for **every** adjacent pair.
- Per branch the cascade moved (not just the one you edited): **`own-commits >= 1` and
  `behind-dev == 0`** — `git rev-list --count <parent>..<layer>` and
  `git rev-list --count <layer>..origin/dev`.

**After any conflicted replay, assert conflict markers are ZERO at every layer** — print the matching
lines, never a count. A `grep -c` returning nonzero has been read as "clean" and shipped markers into
commits, which then replayed up the cascade.

## Step 6 — Reply on the threads: a receipt, not an argument

**The reply is the surface this skill gets wrong, and it is the surface we use most.** Measured on
the L1→top stack, every comment on both sides:

| author | n | median chars | max | median newlines |
|---|---|---|---|---|
| the human reviewer | 48 | **176** | 216 | — |
| us (inline) | 24 | **2,404** | 3,237 | 18 |

**22 of the 25 things we posted were replies** — 21 inline (median 2,424) plus one 4,032-char reply
to a review summary on the PR conversation, our single longest artifact. So the reply is ~88 % of
everything we post, and it was the least specified thing in this skill: one inherited sentence
pointing at another skill's budget. Structure across the inline 21: **21/21 used `**` bold, 11/21
embedded code fences, 8/21 bullet lists.** Multi-paragraph documents opening `**VALID — confirmed…**`.

*(Our four review **summary bodies**, 2,278–3,172 chars, are excluded — `pr-review-concise` makes
that surface deliberately unbudgeted. Length there is correct; length in a reply is not.)*

**The cause is the same obedience failure `pr-review-concise` diagnosed one skill over.** Step 1 of
this skill demands a verdict "with evidence — the anchor: `file:line` + the quoted code". It never
said *where* the evidence goes, so the session posted it on the thread. **Step 1's verdict table is
operator-report material. It is not a reply.**

**Two surfaces, two budgets:**

| Surface | Budget | Carries |
|---|---|---|
| **Any reply to the reviewer** — inline thread **or** a PR-conversation reply to their review summary | **≤120 chars for a fix, ≤250 otherwise. One sentence. No markdown.** | that it is done, or the one fact that settles it |
| Operator report (Step 7, not posted) | unbudgeted | verdict, anchor, quoted code, evidence, reasoning, the class sweep |

**Do not prove the verdict to the reviewer.** They wrote the finding; they already believe it. A
reply that re-derives *why they were right* spends 2,400 characters telling someone what they
told you. Confirmation is `Fixed.` — the diff carries the argument.

### The templates — use them literally

| Verdict | Reply | Chars |
|---|---|---|
| `VALID`, fixed | `Fixed in <sha>.` | ~22 |
| `VALID`, fixed, non-obvious *what* | `Fixed in <sha> — <one clause>.` | ≤120 |
| `INVALID` | the single disqualifying fact, one sentence, no preamble | ≤250 |
| `OUT-OF-SCOPE` | `Out of scope here — tracked in <task file / PR #N>.` | ≤120 |
| `OPERATOR-DECISION` | `With the operator — <the call in ≤8 words>.` | ≤120 |
| `STALE-ANCHOR` | `Anchor moved to <symbol>; re-verdicted there: <one clause>.` | ≤160 |

A worked `INVALID`, at 118 chars — one fact, no verdict label, no build-up:

> `scripts/ is outside basedpyright's include (pyproject.toml: ["backend","tests"]), so this is not a gate failure.`

**Banned in a reply, all six measured in the failure:** a newline · `**` · a `#` heading · a bullet
list · a code fence · an opening verdict label (`**VALID —**`, `**Confirmed:**`). Each one is a
document-shaped tell; the reply is a sentence.

**Also banned:** restating the defect, quoting the code back, citing the retro/learning history,
naming what else you checked, and thanking the reviewer.

**Never write "your comment is on PR A, the fix is in PR K."** If you are about to, the fix is in the
wrong branch — go back to step 2.

### Before posting: measure your own replies

Posting replies is an **outward action** — show the operator this table and post on approval.
Authorization is scoped to the action it was granted for; a one-time "go ahead" does not carry to
the next layer or the next round.

```markdown
| # | PR | thread anchor | reply (verbatim) | chars | shape ok |
|---|---|---|---|---|---|
| 1 | L1 | hooks/deny-cd-prefix.py:34 | Fixed in a1b2c3d. | 17 | yes |

median: <n> chars · max: <n> · reviewer baseline: 176 · over budget: <n>
```

`shape ok` is mechanical: **no newline, no `**`, no fence, within the row's cap.** A row failing any
of them is rewritten, not posted. **If your median exceeds the reviewer's 176, you have reproduced
the failure** — rewrite before showing the operator, not after.

### Then resolve the threads you answered — replying is only half the loop

A reply does not close a thread. Resolution is a separate GraphQL mutation, and skipping it is why a
stack reads as "35 unresolved" when most were in fact answered — the reviewer cannot tell handled
from ignored, and the next session re-works them. **Measured on this stack: 16 threads sat resolved
after a reply while 1 stayed open with a complete answer on it, and a 34-item "work list" was built
from a count that could not distinguish the two.**

`resolveReviewThread` takes a thread **node id**, which REST never returns — the ids come from the
same query that gives you `isResolved`:

```bash
gh api graphql -f query='query { repository(owner:"<owner>", name:"<repo>") {
  pullRequest(number:<n>) { reviewThreads(first:100) { nodes { id isResolved
    comments(first:1){ nodes { path line } } } } } } }'

gh api graphql -f query='mutation($t:ID!){ resolveReviewThread(input:{threadId:$t}) {
  thread { id isResolved } } }' -f t='<thread-node-id>'
```

**Resolve only what you actually settled**, and only after the reply is posted:

| Verdict | Resolve? |
|---|---|
| `VALID`, fixed and replied | Yes |
| `INVALID`, replied with the evidence | **No** — resolving your own disagreement removes the reviewer's ability to push back. Leave it for them |
| `OUT-OF-SCOPE`, tracked elsewhere and replied | Yes |
| `OPERATOR-DECISION` | No — it is not settled |
| `STALE-ANCHOR` | No — re-verdict first |

Resolving is an **outward action** under the same authorization as posting: it changes what the
reviewer sees. Include the resolve list in the step-8 approval table, and never resolve a thread you
did not reply to.

## Step 7 — Report

```markdown
## Comment resolution — <stack/PR>

| # | comment | verdict | owning layer | fix sha | reply posted |
|---|---|---|---|---|---|

**Cascade:** <ran / handed back and why> · backup tags: <list>
**Chain verified:** <adjacent pairs checked, after `git fetch --prune`>
**Not done:** <OPERATOR-DECISION items, OUT-OF-SCOPE destinations>
```

## Worked example — the fix that went to the wrong layer

**What happened:** the reviewer's finding on L1 was that the `cd`-guard hook was unregistered. The
fix — the `.claude/settings.json` entry — was committed to T2 at the top of the stack. Both PRs
looked correct in isolation. Merging L1 alone ships the hook **inert**, with the reviewer's finding
recorded as addressed.

**What this skill does instead:**

1. Verdict: `VALID`, anchored at the hook file added in L1's diff.
2. Owning layer: `git log --reverse --format='%h %s' -S 'deny-cd-prefix' <base>..<top> | head -1` →
   the *introducing* commit, which is in **L1's** branch. (The `-1`-only form returns the
   top-of-stack review-fix commit instead — verified on this repo, and it is how the fix ends up back
   at the top.) Then walk the topology table upward for the first layer containing that sha.
3. Fix committed **on L1's branch**, capturing `OLD=$(git rev-parse HEAD)` *before* the commit.
4. Backup tags for every branch above it; preflight; **stop and hand back** — the cascade is the
   operator's call.
5. After the authorized cascade: `git fetch --prune`, then `--is-ancestor` for each adjacent pair;
   `own-commits >= 1` per moved branch.
6. Reply: `Fixed in <sha> on <branch> — the settings.json hook entry now lands with the hook file.`

Merging L1 alone now ships a registered hook. No merge-train dependency, no "the fix is in PR K",
no second review surface.

## Anti-patterns

| Anti-pattern | Why it seems right | What actually happens |
|---|---|---|
| Collect fixes into a new top PR | A cascade is 10 branches and 8 force-pushes | Silent merge-train dependency; a piecemeal merge drops the fix |
| Prove the verdict on the thread | Evidence is what makes a reply credible | 2,404-char median vs the reviewer's 176 — they wrote the finding; they already believe it |
| Open with `**VALID — confirmed…**` | It signals the finding was taken seriously | 21/21 of our replies did this; it is a document-shaped tell, not a courtesy |
| Paste the Step 1 verdict row as the reply | The skill asked for a verdict with evidence | The evidence column is report material; Step 6 is the only reply spec |
| Fix silently what you think is wrong | Faster than arguing | The reviewer cannot disagree, and reads it as agreement |
| Cascade from below after committing above | The rebase looks like it worked | Commit lost or ref stranded; no git warning either way |
| Trust the push report | It said everything was pushed | A rejected `--force-with-lease` leaves the old SHA silently |
| `ls-remote` then check `origin/` refs | It read the remote | It tested stale local copies; the stale chain passes too |
| Count conflict markers | Nonzero means "some" | A count read as clean shipped markers up three layers |
| Run the cascade yourself mid-task | It unblocks the work | Rewrites branches other sessions sit on; boundary operation |
| Re-anchor a fix by remembered line number | The Read was recent | Anchors drift; cite by symbol, re-grep at write time |

## Cross-cutting rules

Secrets, durable-vs-ephemeral artifacts, authorization scope, branch hygiene (never `git symbolic-ref`
to switch branches), own-hunks staging in a shared checkout, and gate-verdict discipline are shared —
see [stacked-pr-planner](../stacked-pr-planner/SKILL.md) § Cross-cutting rules.

Two that bind hardest here: **`git status` + `git stash list` before trusting any file** (three
sessions share this checkout, and a parallel session once deleted the initiative's branch mid-work,
silently unstaging the staged set), and **stage only your own hunks** — with 7 files carrying mixed
edits, build the index line-by-line (`git hash-object -w` + `git update-index --cacheinfo`) so the
working tree stays byte-identical, verified by checksum before and after.

## Related

- `.ai/git-stacked-pr-workflow.md` — the cascade forms, the dropped-commit trap, remote verification
- `parallel-session-safety` §9 (hand-off contract), §10 (cascade = boundary operation)
- `stacked-pr-planner` — a fix spanning two layers is a re-plan trigger, not a reason to go to the top
- `pr-review-concise` — the length budget these replies inherit; its false-positive list drives `INVALID`
- `/branch-switch` — the only sanctioned way to move between branches
