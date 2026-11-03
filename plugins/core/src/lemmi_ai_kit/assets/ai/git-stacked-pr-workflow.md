# Stacked PR Workflow

This file is kit-managed: refreshing it (a scaffold run with `--force`) overwrites an edited copy,
so keep project-only lines in a separate file.

Hard-won mechanics for maintaining a stacked-PR chain in the project (the deepest seen was 11 PRs).
Each rule below cost real work to learn and has a trap that silently drops a commit or closes a PR.

The later sections hold recipes for delivering a branch from a shared checkout without switching it
(see "Plumbing from a shared checkout" and "Hand-over checks in a shared checkout"); the kit's
`parallel-session-safety` owns the generic shared-index rules.

## Native stacks first (`gh stack`, public preview 2026-07-30)

GitHub now ships stacked PRs natively: the `gh stack` CLI extension, a REST/webhook surface,
automatic cascade + retarget when a bottom PR merges, and whole-stack merges. **Prefer the native
path; the manual sections below are the fallback** — and the verification rules stay mandatory
either way.

**Prerequisites (probe once per session):** `gh --version` succeeds and `gh extension list`
shows `gh-stack`. Missing → use the manual workflow below and say which path you used. Install
(interactive, user-run): `winget install GitHub.cli`, `gh auth login`,
`gh extension install github/gh-stack`.

| Intent | Command |
|---|---|
| Start a stack (`<trunk>` is the project's integration branch) | `gh stack init --base <trunk> [branches...]` |
| New layer on top | `gh stack add [-m <msg>]` (run from the top branch) |
| Open/update the PRs | `gh stack submit` — **draft is NOT the default on the interactive path.** Verified against the CLI: in the editor "new PRs default to ready for review; switch any to draft with the CREATE AS toggle". Only `--auto` creates drafts ("with `--auto`, new PRs are created as drafts unless you pass `--open`"). To honour the project's early-draft rule, either toggle each PR in the editor or use `gh stack submit --auto` |
| Absorb a mid-stack fix | commit on the owning branch; cascade at a boundary via `gh stack sync` |
| Cascade + push + PR sync | `gh stack sync` (fetch, trunk FF, cascading rebase, per-branch `--force-with-lease`, PR sync) |
| Conflict recovery | **start** `gh stack rebase`, then `--continue` / `--abort` — a `sync` that hit a conflict has already rolled every branch back, so there is nothing to continue (see below). **The often-quoted "exit code 3 = conflict" mapping is UNVERIFIED**: `gh stack rebase --help` documents no exit codes. Branch on the command's output, not a remembered code. |
| Inspect state (agent-friendly) | `gh stack view --json` |
| Restructure layers | `gh stack modify` (clean tree required) |
| Adopt branches made by other tooling | `gh stack link` |

**Drafts are not the default on the interactive path.** `gh stack submit --help`: *"In the
editor, new PRs default to ready for review; switch any to draft with the CREATE AS toggle.
With `--auto`, new PRs are created as drafts unless you pass `--open`."* So the two paths
disagree, and the one a human types is the one that publishes. Since `parallel-session-safety`
§10 requires layer PRs to open as drafts at a session boundary, use `--auto` (which is also
what a non-interactive terminal falls back to) or set the Draft toggle explicitly before
Ctrl+S. Do not rely on "submit defaults to draft" — it does not.

**After `gh stack sync` reports a conflict there is no rebase in progress.** Its help is
explicit: *"If a rebase conflict is detected, all branches are restored to their original state
and you are advised to run `gh stack rebase` to resolve conflicts interactively."* The rollback
is the point — `sync` is atomic. So `gh stack rebase --continue` at that moment fails with
nothing to continue; the sequence is **`gh stack rebase` first** (which re-runs the cascade and
stops at the conflict, leaving a live rebase), resolve, then `gh stack rebase --continue`, and
`--abort` to unwind. Re-run `gh stack sync` afterwards to push and re-sync PR state.

**Superseded on the native path:** the hand-rolled `--update-refs --onto` cascade below
(`gh stack sync` runs it, with `--continue`/`--abort` recovery), and *manual* base retargeting —
merging the bottom PR auto-rebases the remaining branches and retargets the next PR to trunk. The
base-lock 422 documented below still stands, but on the native path you never need to retarget by
hand, so it stops being a workflow step and becomes a guardrail.

**Still mandatory with the native path:**

- Verify the remote chain link by link after every sync/push (section below) — `gh stack`'s
  success output is a claim, exactly like a push report.
- Zero-conflict-marker assertion after any conflicted cascade; `own-commits >= 1` per moved
  branch; backup tags until merge.
- **Session discipline:** cascades and outward actions (`sync` / `rebase` / `modify` / `merge` /
  `submit` / any push) are user-authorized boundary operations — never from a session mid-layer.
  Sessions may run `gh stack` commands only on a clean tree within their pinned layer. Layer PRs
  open as drafts at the session-end boundary. See `parallel-session-safety` §10; topology
  planning (stacked spine vs sibling leaves, risk class, review lane) is the **`stacked-pr-planner`**
  skill, invoked by `orchestrate`'s plan step for a single session's work and by
  **`initiative-planner`** step 2 for anything spanning several sessions. Review and comment
  resolution on the resulting
  PRs: `pr-review-concise` and `pr-comment-resolver` — the latter owns the rule that a fix goes in
  the branch that owns the code, never in a new top-of-stack PR.

**Preview caveats:** same-repo branches only (no cross-fork); public-preview semantics may
change; keep `gh-stack` extension versions roughly aligned across the team.

## Propagating a mid-stack fix

A review comment belongs on the PR that **owns** the code, and every descendant then has to absorb
it. Work bottom-up, one fix at a time:

```bash
git checkout <owning-branch>
OLD=$(git rev-parse HEAD)      # capture the tip BEFORE committing — this is the rebase base
# ...edit + commit...
git rebase --update-refs --onto <owning-branch> "$OLD" <top-branch>
```

`--update-refs` replays every descendant onto the new owning tip **and moves all intermediate
branch refs in one pass**. Never hand-rebase each descendant. Force-push the moved branches with
`--force-with-lease`.

> **Trap — a silently dropped commit.** Do NOT use the descendant's OWN tip as the rebase base when
> `local == origin`: the replay range is empty and the branch collapses onto its parent, losing its
> commit with no error. This is why `OLD` is captured explicitly *before* the commit rather than
> derived afterwards.

**Guard before any force-push** — a per-branch integrity check: `own-commits >= 1` and
`behind-<trunk> == 0`. Run it for every branch the rebase moved, not just the one you edited.

## Work the layers in ONE direction

`git rebase --update-refs <base> <tip>` replays only `merge-base(<base>, <tip>)..<tip>` — a commit
reachable only from a branch ref OUTSIDE that range is not protected by `--update-refs`.
Committing at layer N and then cascading from a layer BELOW N puts N's fresh commit outside the
replayed range: the rebase rebuilds N's layer from the tip's history and moves N's ref past the
commit. This bit twice in one session, in both possible shapes — a LOST commit (not an ancestor
of anything; found only because the test suite failed) and a STRANDED ref (N left pointing at a
dangling commit, so N+1 no longer descended from it — a broken PR chain caught seconds before
push). Neither produces any git warning; `rebase --continue` and `push --dry-run` both report
success.

So: after committing at layer N, cascade upward from N **before** touching any layer below it.

**That rule covers ONE fix. A review sweep produces fixes at MANY layers, and the obvious generalization is wrong.** Committing at every layer and then running a single `rebase --update-refs` from the bottom does NOT carry them: each fix commit sits on its own branch ref *outside* the replayed range, so the rebase replays the OLD chain onto the new base and silently drops every fix. Measured: one such pass exited **0**, reported success, and moved 4 refs — none of the 11 intended. The correct form is N sequential rebases, bottom-to-top, one per layer:

```bash
# for each (base, layer) pair, in bottom-to-top order:
git rebase --onto <base> origin/<base> <layer>     # replays only that layer's own commits
```

**Then assert the fixes actually arrived** — the rebase's exit code will not tell you:

```bash
git log --oneline origin/<trunk>..<top> | grep -c '<your fix marker>'   # must equal the number of layers you fixed
```

> **`--update-refs` also moves branches you never named.** It updates *every* ref pointing into the replayed range, not just your stack layers — one cascade here moved three unrelated branches (two of them old review-fix branches) under a success banner. Snapshot before, diff after, restore anything unintended:
>
> ```bash
> git branch --format='%(objectname) %(refname:short)' | sort > .ai/tmp/refs-before
> # ...cascade...
> git branch --format='%(objectname) %(refname:short)' | sort | diff .ai/tmp/refs-before -
> ```
Run the fast suite after the FIRST layer of a stacked change, not after the last — one session
landed 13 commits before its first suite run, which then found 14 failures + 4 errors the static
gates had missed. After any conflicted cascade, assert conflict markers are ZERO at **every**
layer before continuing: a marker committed at layer N is replayed into every layer above it.
`git rebase --continue` does not check content, and `git diff --check` inspects only *uncommitted*
changes — it does flag leftover markers if you run it before staging, but once the marker is
committed both are silent (see the project's gate-verdict rule for the `grep -c`
count-read-as-clean trap). Keep pre-work backup tags until merge — a lost commit is recoverable
only while the object survives.

**Do not begin a cascade you cannot finish and verify in one sitting.** A completed cascade and an
untouched stack are both safe states; a half-replayed chain is neither — branches sit at intermediate
SHAs, a conflicted rebase holds the tree, and the next session inherits a shape no document describes.
Before starting, confirm you can reach the end: every affected branch free of other worktrees, backup
tags taken, and enough remaining budget for the conflicts plus the remote link-by-link verification.
If any of that is missing, stop while the stack is still untouched — that is the cheap outcome. If you
are already mid-cascade and must stop, `git rebase --abort` and restore every branch from its backup
tag rather than leaving partial progress.

## Verify the chain on the REMOTE, link by link

"Each branch exists" and a correct-looking local chain prove nothing about remote topology. A
rejected `--force-with-lease` leaves the old SHA on the remote and does not announce itself to a
later session — one audited push table recorded a branch as force-pushed while the remote still
held a commit stacked on a branch deliberately rebased OUT of the line; merging that chain would
have landed another developer's parked WIP on `<trunk>`. Exactly one link was broken, so spot-checks
passed.

Before any push of — or PR action on — a stacked chain:

```bash
git fetch --prune origin                          # REQUIRED: this is what updates origin/*
git merge-base --is-ancestor origin/<lower> origin/<upper>   # for EVERY adjacent pair
```

**`git ls-remote` is not a substitute for the fetch, and pairing the two is the trap.**
`ls-remote` queries the remote and PRINTS SHAs; it does not write `refs/remotes/origin/*`. So
the old form here — `ls-remote` followed by ancestry checks "using `origin/` refs" — read fresh
truth to the screen and then tested *stale local copies*, which is precisely the mistake this
section exists to catch. The stale chain passes, too: before someone else's cascade rewrote it,
the old chain was internally consistent, so every adjacent pair still answers "ancestor". Fetch
first, or compare against the OIDs `ls-remote` actually printed — never mix the two.

Re-verify after every force-push rather than trusting the push's own report. A `push --dry-run`
confirms the push would be *accepted*, not that the chain is *connected*.

**Ancestry is necessary and not sufficient — also assert remote SHA == local SHA, per branch.**
A rejected push leaves the old ref in place, and the *old* chain is internally consistent, so every
adjacent pair still answers "ancestor" while three branches sit on the pre-sync base. Measured: a
stack sync reported success having stranded three branches, and the tell only surfaced when a PR
opened from one of them showed **19 commits / 100 files** for a change that was really
**1 commit / 9 files**, because head and base had diverged.

```bash
git rev-parse <branch> origin/<branch>     # the two SHAs must be identical, per branch
```

Stop at the first failing pair. Pushing a higher layer onto a broken link buries the break.

## Pushing a stack can start one CI build per branch

A push of any branch can start CI for it: pushing 14 branches started 14 parallel builds, and in the
observed setup opening their PRs started none. Read the CI trigger filters before pushing a deep
stack, name the expected builds in the hand-off, and never name a stack branch like the trunk (a
deploy condition may be keyed on that name). To prove that a push deployed nothing, list the newest
deploy revisions with the project's own read-only command and look for one created at the push time.

## Cascading a stack after fixes land at the bottom

**Switch to `--onto` at the first branch whose base needed a conflict resolution.** A plain
`git rebase <base>` relies on patch-id matching to skip commits already present upstream, which
holds only while the lower branch was rewritten *mechanically*. Resolving a conflict **changes the
patch**, so its patch-id no longer matches the copy the upper branch carries; git then replays the
lower branch's old commit on top of the new one and conflicts against your own resolution. Measured
on a 13-branch cascade: the first five rebased cleanly and the sixth blew up.

```bash
git rebase --onto <newbase> <old-base-tip> <branch>
```

**Derive `<old-base-tip>` from `git merge-base`, not from a pre-cascade tag, whenever a link was
already broken.** If an upper branch had forked from an older tip, the tag is not the true fork
point — using it replayed 16 commits where 4 were expected. `git merge-base <lower-tip> <upper-tip>`
(both pre-cascade) is the honest answer.

**Cheap proof that nothing duplicated:** `git rev-list --count <base>..<branch>` against its
pre-cascade count. An unchanged count is the check; a grown one is the alarm.

### A branch whose own tip is a merge commit must be MERGED, not rebased

`git rebase` does not preserve merge structure — it replays both sides of an existing merge commit
as one flat sequence, so content the merge already brought in gets replayed a second time out of
context. The symptom is a **false conflict** in which a later commit's entire diff appears to already
exist in "ours".

```bash
git log --format='%H %P' -1 <tip>    # two parents = the tip is a merge; do not plain-rebase
```

Use `git merge <new-upstream>` instead: a real 3-way merge against the true historical merge-base. It
resolves cleanly in this shape, and because the result's first parent is the branch's own unchanged
tip, it often pushes as a **fast-forward** rather than a force-push.

### Dropping exactly one isolated commit, without an interactive rebase

Pass the unwanted commit **itself** (not its parent) as the `<upstream>` argument — the replay
covers only commits strictly after it:

```bash
git rebase --onto <newbase> <the-unwanted-commit> <branch>
```

Confirm two things first, or this silently drops work: (a) nothing later depends on what the commit
introduced (`git grep` for its content across the full range), and (b) the very next commit still
applies with its original content (`git show --stat` after). Used to excise a redundant migration
merge-revision from a 14-branch scripted sync where `git rebase -i` was not an option.

### Separate FIXING from CASCADING into different sessions

Having each branch fix *and* cascade across a 14-deep stack costs ~48 force-pushes, and every cascade
rewrites the branches the next session was briefed against — so each brief goes stale before it is
used. Fix-only sessions that commit but **never push**, followed by a single cascade session, cost
~13. Tell the fix sessions *why* they must not push, or they will helpfully push.

### Re-stacking without a checkout

In a dirty shared checkout that must not be switched, `git rebase` is off the table. `git replay`
(experimental, measured on git 2.55: read `git replay -h` first) computes the new commits and
prints the ref update without touching the working tree or the ref:

```bash
git replay --ref-action=print --onto <new-base> <old-base>..<branch>    # exit 0; prints "update <ref> <new-tip> <old-tip>"
```

When the range holds more than one branch, add `--contained` (without it only the tip's line is
printed and the lower branches keep their old commits) or replay one layer at a time.

Prove that only the base changed before moving anything: (1) each new commit's
`git patch-id --stable` equals the old commit's; (2) author, date and message are identical and the
first new commit's parent is `<new-base>`; (3) `git diff <old-tip> <new-tip>` has the same patch-id
as `git diff <old-base> <new-base>`, while a control pair of different commits does not. Then write
the old tip down for rollback, apply with it as the guard, and build an export of the new tip:

```bash
git update-ref <ref> <new-tip> <old-tip>
```

## Collapsing a stack

Advancing a root PR's head branch past a child's head makes **GitHub automatically mark that direct
child as merged**. Deeper descendants stay open, because their own direct base branches have not
moved.

So after advancing the root:

1. Refresh **every** child's state immediately — do not assume the stack is unchanged.
2. Treat an auto-merged direct child as complete.
3. Close only the descendants that remain open; preserve their branches and discussions.
4. Guard the root update with an exact `--force-with-lease`.

## Deciding whether finished branches may stay independent PRs

Compare each branch's own change, not two tips against `<trunk>`. Per-branch `git diff --name-only`
finds the shared files; then apply each branch's own change onto the other's tree, in both
directions, with that branch's own parent as the merge base:

```bash
git merge-tree --write-tree --merge-base=<parent of b> <a> <b>     # exit 0 = clean, 1 = conflict
```

Tip-versus-`<trunk>` pairs gave one false conflict in 45 pairs (90 merges): that branch's parent was
two commits behind `<trunk>`, so its tree carried stale copies of two files another branch changes.
Re-parent a branch that is behind `<trunk>` before judging it, and give the operator the denominators
(pairs, directions) with the verdict, so that "chaining is required" is not confused with "chaining
is convenient".

## Prove the composition, not only the merge

A clean `git merge-tree` over a set of branches proves only that they do not conflict textually, not
that the combination builds or passes. Compose them as unreferenced commits (no ref, index or
checkout changes), export, then build and test what would ship:

```bash
git merge-tree --write-tree <cur> <branch>                     # prints the tree id; exit 0 = clean
git commit-tree <tree> -p <cur> -p <branch> -m compose         # one pair per branch; the new commit becomes <cur>
git archive <composed-commit> | tar -x -C <posix-dir>          # a POSIX-style path, not a backslash path
```

GNU tar (measured on 1.35) could not open a directory given with backslashes after `-C`, and it read
the `C:` of a drive-letter archive name (`-f`) as a host.
Windows PowerShell 5.1 re-encodes the binary stream of that pipe (measured) and `tar` cannot read
it: run the line in a POSIX shell (Git Bash), or write the archive to a file first with
`git archive -o <file>`.

Run `<build command>` and `<test command>` in the export (the project's testing rule); tests that are
not committed must be copied into it to run. Read each exit code on its own line, and compare the
distinct warnings of the base and composed builds with their positions stripped. Eight branches that
merged clean also built with no added warning and passed every test; the pairwise results had said
nothing about either. Compose the exact combination the operator will release.

## Base retargeting is a MANUAL step

GitHub's stacked-PR feature LOCKS base branches: `PATCH /pulls/{n}` returns 422 (`"Cannot change
the base branch because the pull request is part of a stack."`) and the GraphQL
`updatePullRequest` mutation silently no-ops (returns null, base unchanged). Closing the PR below
does NOT release the lock — only the web UI can change the base. When planning stack surgery,
write base retargeting into the hand-off as an explicit manual step. Symptom if skipped: the PR
shows a huge wrong diff (44 files instead of 1 in the observed case), because GitHub diffs
against a base that is no longer an ancestor — the branch content is fine, only the PR pointer is
stale. Related: a platform refusal message names a precondition, not a permanent verdict (the
project's rule) — e.g. a "branch was force-pushed or recreated" reopen-refusal clears once the
branch is force-pushed back to the exact commit the PR was closed at.

## Plumbing from a shared checkout

When the checkout is dirty, another session works in it or the operator edits through the IDE,
deliver a branch without ever checking it out: build trees and commits with a private index file and
create the ref last. The kit's `parallel-session-safety` owns the generic shared-index rules; this
is the recipe that applies here.

### Building a stack by plumbing

1. Create every tree and commit first (a private index file, `git write-tree`, then
   `git commit-tree -p <parent>`). Nothing is referenced yet, so a failed predicate leaves nothing to
   undo.
2. Check every predicate on the commit ids: the parent chain, the changed paths (none that the
   project keeps out of its history), the tree ids.
3. Create each ref with an all-zero old value, which makes the call fail if the ref exists:

```bash
git update-ref refs/heads/<name> <new-commit> 0000000000000000000000000000000000000000
```

Never pass an empty string for it: Windows PowerShell 5.1 drops an empty argument to a native
program and the guard disappears.

A deterministic rebuild gives equal tree ids for the layers it did not change, which proves that
nothing leaked downward. `git commit-tree -F` stores the message file's bytes as they are: count the
carriage-return bytes of a draft first (Git Bash's `grep -c $'\r'` is not a CR counter).

### Edit a committed file by its blob bytes, not in an export

Read the bytes with `git cat-file blob <commit>:<path>`, assert that every old text occurs once and
every new text is absent, replace, and store the result with `git hash-object -w --no-filters`:
editing an export and hashing with `--path` runs into the line-ending and byte-order-mark traps of an
autocrlf checkout. A second run of the script must fail on its first assertion. Replay the later
commits with `git merge-tree --write-tree --merge-base=<old parent> <new parent> <old commit>`,
check them with `git range-diff` (`=` for each), build and test an export of the exact candidate
commit, and create the ref last.

### Prove the delivery left the checkout alone

`git status` before and after proves nothing either way: it changed in one observed case although no
command used could have changed it (the operator committed the staged files through the IDE), and it
stays equal when an already-modified file is edited again. Prove instead: (1) the write set, which
is a private index file, new objects, one create-only ref and that ref's reflog entry, nothing else;
(2) an unchanged shared index tree (copy `.git/index`, point `GIT_INDEX_FILE` at the copy and run
`git write-tree`: the tree stays equal even when someone commits the staged files); (3) reflog
attribution of any HEAD move (`git reflog --date=iso` says when and which command ran;
`git log -g --format='%gd %gn %gs'` adds who). Take the read-only snapshots with
`git --no-optional-locks` so they cannot touch the shared index, and the last one right before the
ref is created. To show that content, not just paths, did not change, compare content hashes, never
status rows or counts (see the kit's `parallel-session-safety`).

### Prove the tip

Any correction to a plumbing-committed tip voids every proof, so re-run the whole set and print each
command's own exit code and denominator:

1. Export check: export the tip (`git archive`), compare the file count with
   `git ls-tree -r --name-only <tip>`, and each file's `git hash-object --path <p> <p>` with
   `git rev-parse <tip>:<p>`.
2. Id check: the commit's diff holds none of the paths or ids the project keeps out of its history.
3. Checker probe: run that check on a planted positive and a placeholder negative, so that a zero is
   proven.
4. Build: `<build command>` in the export.
5. Tests: `<test command>` there (the tracked tests; copy the change's local, uncommitted tests in to
   run them too).
6. Mutation pass, only when the change claims its tests catch a regression: one planted mutant per
   claim, each run once.

List these commands in the hand-off so that a re-run after a correction is explicit. Script them
only if the operator asks.

## Editing a file the operator holds uncommitted

The operator edits through the IDE, so a file you must change may carry uncommitted hunks of theirs.
Read their diff first (`git --no-optional-locks diff -- <path>`), add the new text at least ten
unchanged lines away from every pending hunk instead of rewriting paragraphs they own, and prove the
merge on LF-normalised copies before committing:

```bash
git merge-file -p <operator's file> <base> <your file>; echo $?     # the exit code is the conflict count: expect 0
```

Add a control that rewrites one of their sentences in a copy of your file: it must exit 1. Reading
two diffs side by side does not show whether edits to nearby lines of one file merge cleanly.

## Hand-over checks in a shared checkout

The operator acts through the IDE in a shared checkout, and none of it shows in an agent's own
commands: within minutes of a "ready for a PR" hand-over the checkout was switched to a new branch,
the two staged files were committed and merged, and `<trunk>` had moved.

- **Before any "ready to PR" or "next step" message**, re-read in the same turn
  `git rev-parse --abbrev-ref HEAD`, `git diff --cached --name-only` and
  `git ls-remote origin <trunk> <branch>`, and compare blob ids (`git rev-parse <ref>:<path>`) before
  calling a pushed branch still needed.
- **Re-read the base after any pause and before the commit.** Write the base commit down at the
  start and run `git fetch origin <trunk>` and then `git rev-parse origin/<trunk>` again after any
  pause (an approval, a long gate) and before `commit-tree`: when `origin/<trunk>` moved twice during
  one wait, the first export and baseline no longer described the tip. Without the fetch,
  `git rev-parse` re-reads only the local copy of the ref and passes after the remote has moved; a
  fetch that fails (an unreachable remote, say) leaves the same stale copy, so the line also reads
  the fetch's exit code. Make the check a line of the commit script, so that a commit on stale
  evidence stops (PowerShell):

  ```powershell
  git fetch origin <trunk>; if ($LASTEXITCODE -ne 0 -or (git rev-parse origin/<trunk>) -ne '<verified base>') { throw }
  ```

  If the base moved, compare the blobs of the touched files, and of what they depend on, across the
  tips and run `git merge-tree --write-tree origin/<trunk> <branch>` (exit 0) before deciding
  whether the export, the baseline and the gate must be rebuilt, and record the base commit in the
  hand-off.

## Is it merged? Is it safe to delete?

After a stack is **rebased or squash-merged**, no single git check answers this — triangulate.
Deciding whether 21 branches and 26 backup tags from a replayed stack were safe to delete, all
three standard checks disagreed and each was wrong on its own:

- `git merge-base --is-ancestor` said **none** of the 21 were merged — the rebase changed every
  SHA. Trusting it alone means never deleting anything.
- `git cherry` (patch-id) got the bulk right but produced **5 false positives** where a different
  rebase base shifted hunk offsets and blob hashes.
- `git branch -d` refused 3 provably-safe branches, and its refusal carries its own exoneration
  one line **above** the error: `warning: not deleting branch '…' that is not yet merged to
  'refs/remotes/origin/…', even though it is merged to HEAD`. That fires for every branch whose PR
  merged while its remote-tracking ref went stale, so reading only the `error:` line misclassifies
  it.

To prove a rebased branch is safe to delete: (1) `git cherry -v origin/<trunk> <ref>` for the bulk
verdict; (2) for each `+` commit, find the same-subject commit on `<trunk>` and diff the two
patch bodies — base drift shows up ONLY as blob hashes and `@@` offsets, real divergence shows as
content; (3) run `git branch -d` and read the whole message, not the error line; (4) for anything
the branch uniquely added, check file-level survival on the integration branch. Finish with
`git branch --list '<glob>'` — globbing after a hand-written delete list is a discovery step, and
it surfaced 5 sibling branches the list had missed.

**A branch built by plumbing and never checked out lives only in its own reflog.** Its tip is in no
other ref, so deleting the branch leaves the objects reachable by nothing until garbage collection
(two weeks by default). Bundle it first and prove the bundle by restoring it: `git bundle verify`
checks integrity and prerequisites, not that the bundle restores.

```bash
git bundle create <file> ^<base> refs/heads/<branch>
git init --bare <scratch>.git      # then point <scratch>.git/objects/info/alternates at the main repository's objects folder
git -C <scratch>.git fetch <file> refs/heads/<branch>:refs/heads/<branch>
git -C <scratch>.git fsck --connectivity-only     # exit 0; list the files the bundle carries
```

Check that the main repository's refs did not move, and keep the bundle in a gitignored folder until
the operator lets it go.

**"Did this work land?" is a different question from "is this commit an ancestor?"** Under
squash-merge the same `--is-ancestor` false-negative misleads about *shipping*: three successive
passes read `git merge-base --is-ancestor <sha> origin/<trunk>` → false and wrote "nothing is merged"
onto two boards, when all twelve stack PRs had merged hours earlier and the code was in `<trunk>`. For
landing, the authoritative check is **content, not ancestry**: `git grep -l <symbol> origin/<trunk>`.
Any history rewrite — rebase or squash — makes ancestry a different question from the one asked.

**A commit's own subject states its status at authoring time; its disposition lives in the commit
that landed it.** `wip(<scope>): park … with handoff` reads as outstanding work, but the landed
history may say otherwise. One such commit opens "Splits <OID>" and adjudicates it piece by piece
— two parts LANDED, one deliberately NOT (review found it unsafe, so it was divided rather than
taken or dropped whole); 9 of the WIP's 10 files were already on `<trunk>`. Nothing in the WIP
commit could have said this: its subject was written before the review existed. To decide whether
commit X is outstanding, search the LANDED history for a commit referencing it
(`git log --grep=<short-sha> <trunk>`) and read its body — never X's own subject.
`wip`/`park`/`temp`/`hotfix` are self-reported status, and self-reported status ages in exactly the
direction that makes safe cleanup look risky.

## Related

- `AGENTS.md` — branch and commit conventions.
