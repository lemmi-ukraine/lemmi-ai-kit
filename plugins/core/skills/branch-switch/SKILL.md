---
name: branch-switch
description: >
  Safely stash current changes, switch to a target branch, and optionally apply
  the stash. Handles conflict detection, dirty worktree warnings, and stash
  management. Use when the user says "switch branch", "checkout to", "stash and
  switch", "apply stash", or provides branch-switching git commands. Also invocable by the model
  when a task requires working in a branch it does not currently have checked out — see
  "Model-initiated switches" for the mandatory pre-switch backup.
argument-hint: "<target-branch> [--apply-stash] [--no-stash]"
metadata:
  type: task
---

# Branch Switch — Safe Branch Switching with Stash Management

## When This Skill Activates

- User says "switch to branch X", "checkout to X", "stash and switch"
- User provides a sequence like "stash, checkout X, apply stash"
- User wants to move work-in-progress to a different branch

## Safety First

Branch switching with uncommitted changes is a **high-risk operation** that can
cause data loss. Always:

1. Check for uncommitted changes BEFORE any git operation
2. Show the user what will be stashed
3. Confirm before applying stash if there are potential conflicts
4. Never force-checkout or discard changes without explicit user approval

## Model-initiated switches — the extra gate

The model may invoke this skill (opened up 2026-08-08, to unblock layer-by-layer PR fix work). The
guardrail that previously existed was `disable-model-invocation`; **what replaces it is this gate,
not trust.** The data-loss incident above happened once and the tree has only gotten more
contended since — a real measurement from 2026-08-08: **617 untracked files, 46 stashes, three
worktrees, and a parallel session that moved `HEAD` mid-task.** A stash-and-switch across that is
where work disappears.

**Before any model-initiated switch, take a durable backup. This step is not skippable, and it is
cheap — it costs one command and it is the only thing standing between a bad switch and lost work.**

```bash
D=".ai/pre-switch-backups/$(date +%Y-%m-%d)-<target-branch>"
mkdir -p "$D"
git diff                                  > "$D/unstaged-tracked.patch"
git diff --cached                         > "$D/staged-tracked.patch"
git ls-files --others --exclude-standard  > "$D/untracked-inventory.txt"
git stash list                            > "$D/stash-list.txt"
git rev-parse HEAD                        > "$D/head-at-backup.txt"
```

Then **report the backup path to the user before switching.** A backup nobody knows about is not a
backup.

Three refusals that are absolute for a model-initiated switch — stop and hand back to the user:

| Condition | Why | Check |
|---|---|---|
| Another worktree holds the target branch | git refuses the checkout, and it fails *after* the stash — the worst moment | `git worktree list` |
| Files staged by another session | Switching carries or conflicts with an index you did not build; never stash someone else's staged work | `git diff --cached --name-only` non-empty and not yours |
| The switch is part of a cascade, rebase, or force-push | Boundary operation — `parallel-session-safety` §10 | any of those in the plan |

**Prefer not switching at all.** Most work that seems to need a checkout does not: `git show
<ref>:<path>` and `git ls-tree` read any branch's content in place, and an existing worktree can be
addressed with `git -C <path>`. Reach for a switch only when you must *write* to a branch, and never
create a new worktree to avoid one (standing user rule, 2026-08-07).

## Pipeline

### Step 1 — Assess Current State

Run these commands to understand the current situation:

```bash
git status --short
git stash list
git branch --show-current
```

Report to the user:
- Current branch name
- Number of modified/untracked files (if any)
- Existing stashes (if any)

If there are NO uncommitted changes, skip to Step 3.

### Step 2 — Stash Changes

Unless `--no-stash` was specified:

1. **Show what will be stashed** — list modified and untracked files
2. **Create the stash** with a descriptive message:
   ```bash
   git stash push -m "WIP on {current-branch}: {brief description of changes}" --include-untracked
   ```
3. **Verify the stash was created**:
   ```bash
   git stash list | head -1
   ```
4. **Confirm clean worktree**:
   ```bash
   git status --short
   ```

If `git stash push` fails (e.g., merge conflicts in progress), inform the user and
suggest alternatives:
- `git stash push --keep-index` to stash only unstaged changes
- `git merge --abort` if a merge is in progress
- Manual commit of work-in-progress

### Step 3 — Switch Branch

```bash
git checkout {target-branch}
```

If the branch doesn't exist locally:
1. Check if it exists on remote: `git branch -r | grep {target-branch}`
2. If remote exists: `git checkout -b {target-branch} origin/{target-branch}`
3. If not found anywhere: ask user if they want to create a new branch

If checkout fails due to remaining uncommitted changes, report the error and suggest
either committing or force-stashing.

### Step 4 — Apply Stash (if requested)

Only apply stash if the user requested it (explicit `--apply-stash` or the user said
"apply stash" in their message).

1. **Check for potential conflicts** before applying:
   ```bash
   git stash show --stat
   ```
   Compare the stashed files against the target branch — if the same files were modified
   on both branches, warn the user about potential conflicts.

2. **Apply the stash** (keep it in the stash list as safety net):
   ```bash
   git stash apply
   ```

3. **Check the result**:
   ```bash
   git status --short
   ```

4. **If conflicts occurred**: inform the user and list conflicted files. Do NOT
   auto-resolve — let the user decide.

5. **If clean apply**: report success and ask if user wants to drop the stash:
   ```bash
   git stash drop stash@{0}
   ```

### Step 5 — Confirm Final State

Always end by reporting:
```
Branch: {new branch name}
Status: {clean / N modified files}
Stash: {stash entry if still exists, or "dropped"}
```

## Decision Tree

```
User wants to switch branches
  │
  ├─ Has uncommitted changes?
  │   ├─ YES → Stash changes (Step 2) → Switch (Step 3)
  │   └─ NO → Switch directly (Step 3)
  │
  ├─ User said "apply stash"?
  │   ├─ YES → Apply stash (Step 4)
  │   └─ NO → Done
  │
  └─ Stash apply had conflicts?
      ├─ YES → Report conflicts, let user decide
      └─ NO → Offer to drop stash
```

## Append-Log Conflicts (`.ai/*.md`)

When a stash-pop, FF-pull, or merge conflicts on append-only logs (`.ai/learnings.md`,
`.ai/ai-changelog.md`) — both sides added entries at the same section top/end:

1. **Back up** the affected files before resolving (a botched log merge is silent — entries vanish or
   malform with nothing failing).
2. **Union-resolve** (keep both sides' entries), but dedup-check each local entry by title first:
   `grep -c "<title>"` == 1 → local-unique, keep; == 2 → already upstream, drop the duplicate.
3. **After stripping conflict markers**, verify the entry straddling each `=======` / `>>>>>>>` seam
   still has its full field set — a 3-way merge can pull an entry's trailing field (`- **Category**`)
   out as common context and silently attach it to the next entry.

## A big merge's real hazard is DOC-TRUTH, not code

Measured: a long-lived integration branch (185 ahead) merged into a branch 7 ahead whose 5-of-7
commit subjects had **patch-id-identical twins** already upstream via other PRs. The handoff
predicted 2 conflicting files; the merge produced **1** — the feature README, where both sides
appended *different* bullets at the same EOF anchor. The predicted *code* file auto-merged as a true
composition of both sides.

Patch-id-identical duplicates make textual divergence collapse at merge time, so surviving conflicts
concentrate in **append-heavy prose** — and the resolution risk there is that the kept prose asserts
**live-state claims**. One side's bullets claimed a particular enum value was unreachable and that a
kill switch was in no env file; either could have been falsified by the other side of the very merge
being resolved.

- **Resolve doc conflicts against the POST-merge tree** — `git grep` each kept claim's symbols —
  never against either parent alone.
- **Sweep open sibling PRs for content that will invalidate the kept text**, and write the expiry
  next to it. One of those two claims retires the moment an open PR merges; that was recorded inline
  where the text was kept.
- **For files that auto-merged, diff the result against BOTH parents** (`git diff HEAD -- <f>` and
  `git diff <other> -- <f>`) to see what actually composed, then let the type and lint checks
  arbitrate the composition.

## What NOT to Do

- Do NOT use `git checkout .` or `git restore .` to discard changes — this destroys work
- Do NOT use `git checkout --force` unless the user explicitly requests it
- Do NOT auto-drop stashes — always confirm with the user
- Do NOT apply a stash from a different branch without warning the user
- Do NOT use `cd` in any git commands — use absolute paths
