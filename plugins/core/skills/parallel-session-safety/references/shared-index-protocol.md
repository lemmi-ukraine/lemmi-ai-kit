# The shared index — failure modes and protocols

Split out of `SKILL.md` §12 on 2026-08-29 to keep that file inside its 500-line budget.
§12 in `SKILL.md` states the rule; this file carries the five measured failure modes and the
exact commands for each. Read it whenever you are about to stage or commit in a tree another
session is writing to.

---

### 12a. Contention is per-LINE, and both standard guards are blind to it

**This narrows the `--only` remedy above.** `git commit --only <my paths>` commits the
**working-tree state** of the named paths — so a peer's uncommitted lines *inside a file that is
legitimately yours* ship inside your commit. And the prescribed check cannot see it:
`git diff --cached --name-only` prints **file names**, which were correctly yours. The check passes
while the defect ships.

Measured: a layer adding its own settings keys to a compose file and both build manifests would
have committed four of a peer's unrelated settings lines along with them. Env manifests, build
configs and an environment reference doc are exactly the files several sessions touch at once, so in
a shared checkout that is the **common** case, not the edge.

Before committing any path that `git status` showed as already dirty *and that you did not dirty
yourself*:

```bash
git diff HEAD -- <path>     # confirm EVERY + line is yours
```

If it is not, rebuild that index entry from HEAD plus only your lines, leave the worktree alone, and
commit **from the index with no pathspec**:

```bash
git show HEAD:<path> > /tmp-ish/edit-me      # then apply ONLY your lines
git hash-object -w --no-filters /tmp-ish/edit-me
git update-index --cacheinfo 100644,<sha>,<path>
git diff --cached -- <path>    # only your lines
git diff -- <path>             # only theirs
git commit                     # NO pathspec
```

**Anything that re-adds the path — `git add`, `git commit --only`, `git commit -a` — silently undoes
this**, so say so explicitly in the hand-off: the next person's instinct is to `git add` first.

### 12b. A held index is a LOCK, not a save point

Staging is a mutually-exclusive resource in this checkout, and holding it has a measured cost beyond
your own session. One session staged 26 paths early (the operator asked for staging without a commit)
and held them through a review, a refactor and three suite runs. A concurrent QA orchestration
session had to detect that, work around it, and encode it in its own dispatch prompts:

> `git diff --cached --name-only | wc -l -> 0` required before you stage anything. At write time it
> was 26 (the adoption session's index). **"A non-zero value here is a STOP, not a nuisance."**

It **blocked four planned sessions**, and committing cleared it in one command. Peer sessions also
unstage your files: `git ls-files --error-unmatch` reported one of five staged paths untracked
minutes after staging, because another session had dropped it — caught only by checking the specific
paths, since `git status --porcelain` over a tree with dozens of dirty files does not make it obvious.

So: treat "staged, awaiting review" as an **exposure window**, not a resting state. Keep it short.
When asked to stage without committing, say in the hand-off that the index is held and name the
paths. When a long gap is expected, prefer leaving the work unstaged and handing over the exact
`git add` command, or hand over a patch file. **Leave the index empty when the session ends.**

Read it the other direction too: a peer's dispatch doc naming *your* session's state is a signal to
go and read what else they assumed about you.

### 12c. Work done AFTER staging silently invalidates the staged set

`git add` snapshots **content**, not a subscription to the file. So any workflow step that runs after
staging — the post-task review, doc-impact fixes, a lint pass, a reviewer's own corrections — reopens
a gap that **no staged-set check can see**.

Measured 2026-08-27: eleven paths were staged and handed over for review; the mandated post-task
review then edited `tasks/TECH-r2-tt-review.md`, already in the index. Both proof commands stayed
green — `git diff --cached --name-only` still listed exactly 11 paths and `--stat` still showed the
file — because **both describe the index, and the index was simply old**. Had the operator committed
on that evidence, the commit would have carried the *pre-review* version of the very document the
review had just corrected.

```bash
git diff --name-only -- <staged paths>   # worktree vs INDEX; the only command that sees it
```

Re-run that over the staged set and re-add whatever it touched **before** reporting the set as ready.
This is the mirror of the "check and the action it gates in one call" trap: here the check was
correct when run, and was invalidated by the work that followed it.

### 12d. `git push` answering "Everything up-to-date" means you are not on that branch

The failure has one reliable tell and it is **not** an error message. Commits landed on the wrong
branch **four separate times** in one orchestration session, from two silent causes: a peer ran
`git checkout -b` and the next commits followed HEAD onto their branch; and twice a `git checkout`
**aborted** on a file another session had modified — printing its reason and then **exiting 0 inside
a compound command**, so the `&&` chain proceeded as though the switch had happened.

Re-read `git rev-parse --abbrev-ref HEAD` *after* every switch and immediately before every commit.
Never infer the branch from the switch command having succeeded.

Recovery is cheap while the commits still exist — apply them onto the right branch **by path**, which
works even when `git cherry-pick` refuses because a peer holds a staged index:

```bash
git checkout <sha> -- <files>
git commit -F <msg> -- <files>
```

> §12's assertion already existed and had been written into three dispatch briefs *during* the
> session that then violated it three more times. That is the prose-vs-seam result again.

### 12e. A multi-branch history operation: back up the TRACKED layer twice, never touch untracked

`git checkout` / `git rebase` refuse (they never silently discard) only when a file both **differs
between the current and target tree** *and* **has a local modification**. So the real collision
surface is exactly the **tracked-and-modified** set — checkout never touches a path the target branch
does not itself track at that spot.

That makes the safe protocol for running a 14-branch sync inside a tree holding ~44 modified tracked
files and ~88 untracked paths of someone else's live work:

```bash
git diff > ../pre-sync-<date>.patch             # 1: OUTSIDE the repo and git's own mechanisms
git stash push                                  # 2: NOTE no -u — tracked layer only
```

Leave the untracked estate **entirely alone**. Verified lossless: after `stash pop`, `diff` against
the original patch was byte-identical. Reserve `-u` for when the untracked files are your own task's,
never when they are the repo's standing cross-initiative state.

---

### 12f. Your BASE is a draft until it commits — re-verify every finding against what landed

A concurrent session's working tree is a **draft, and drafts get cut**. Findings for a stacked layer
were analysed while the branch below it had 22 files staged — a new ownership-error class, a 404
middleware entry, a fail-closed owner resolver. When that session committed, the commit **excluded
two of those files entirely**: an operator review had cut the whole local-enforcement design as
overengineering. The error class the analysis was built on exists nowhere at the base.

The failure is silent in the dangerous direction. The files still parse, the greps still return, and
nothing announces that the design you reasoned about was abandoned — so a finding written against
removed code reads as competent and is simply about nothing.

- When your base commits, re-run every finding's evidence against the **commit**, not the tree you
  read: `git show --stat <base-sha>` for what actually landed, then re-grep each symbol the analysis
  depends on. Two commands, and here it changed the answer.
- **Cite the base by SHA** in any review doc, and treat analysis written against an uncommitted
  sibling as provisional until that sibling commits.
