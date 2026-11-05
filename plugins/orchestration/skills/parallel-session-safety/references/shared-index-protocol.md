# The shared index — failure modes and protocols

Split out of `SKILL.md` §12 on 2026-08-29 to keep that file inside its 500-line budget.
§12 in `SKILL.md` states the rule; this file carries the measured failure modes and the
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

**Record what you checked, then compare it with what lands.** At the precondition, record
`git hash-object -- <path>` for each added or modified path to commit, untracked ones included (for
a rebuilt entry, the id `git hash-object -w` printed). Compare it with the blob that lands:
`git ls-files -s -- <path>` before `git commit`, `git ls-tree HEAD -- <path>` after
`git commit --only`. On a mismatch, read the diff and ask. A blob stored with CRLF line endings can
mismatch although nothing changed (the safe direction): hash it with and without the repository's
filters (`--no-filters`), as the reading-gate-output reference of `post-task-review` describes. 12g
runs the same check over the whole dirty set.

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

A file a peer holds staged is a stop for staging, not for every edit: to edit on top of it, with the
holder's consent, see 12i.

Read it the other direction too: a peer's dispatch doc naming *your* session's state is a signal to
go and read what else they assumed about you.

### 12c. Work done AFTER staging silently invalidates the staged set

`git add` snapshots **content**, not a subscription to the file. So any workflow step that runs after
staging — the post-task review, doc-impact fixes, a lint pass, a reviewer's own corrections — reopens
a gap that **no staged-set check can see**.

Measured 2026-08-27: eleven paths were staged and handed over for review; the mandated post-task
review then edited `tasks/TECH-round-two-review.md`, already in the index. Both proof commands stayed
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

`git checkout` / `git rebase` refuse (they never silently discard a tracked change) only when a file
both **differs between the current and target tree** *and* **has a local modification**. That is the
tracked-and-modified set, and it is not the whole collision surface: `git merge`, `git checkout` and
`git switch` overwrite an **ignored** file at a path the target tracks, by default.
`--no-overwrite-ignore` refuses that for a fast-forward merge, `checkout` and `switch`, but a
non-fast-forward merge overwrote the file anyway when measured (git 2.55), so dry-run a merge first
(12h). Checkout never touches a path the target branch does not itself track at that spot.

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

### 12g. Prove "unchanged" by content: hash the dirty set, never count it

Status rows and `--stat` counts show which paths are dirty, not what they hold. Before launching
workers, a suite run or a review, record HEAD, `git diff --cached --raw` and a SHA-256 of each path
`git ls-files -m -o --exclude-standard` lists; re-run it at each boundary and at the return; report
new, gone and changed paths, inside or outside the declared set. Prove "unchanged" by equal hashes,
never by equal counts. A hash flags a neighbour's edit too, so classify each changed path by owner
(`SKILL.md` §2) before calling it a violation.

### 12h. A merge into a tree others are writing: dry-run it first

`git merge-tree --write-tree HEAD <target>` (git 2.38+) merges in the object database and touches
neither the index nor the working tree. Redirect its output to a file and read the command's own
exit code, never through a pipe: 0 is clean, 1 is conflicts, anything else is unmeasured. An
unresolvable `<target>` also exits 1, so resolve it first (`git rev-parse --verify --quiet <target>^{commit}`).
The first line of a clean result is the merged tree, and the write set is
`git diff --name-only --no-renames HEAD <tree>`.

If it is clean, nothing is staged (`git diff --cached --name-only` prints nothing; the git-merge
manual says the index must generally match HEAD) and
`git status --porcelain --untracked-files=all --ignored -- <set>` prints nothing, run
`git merge --no-edit --no-overwrite-ignore <target>` without a stash. That empty status is the
protection: when measured (git 2.55) the flag refused a fast-forward merge but not a
non-fast-forward one. Otherwise use 12e or coordinate, and never stash a peer's staged files (12b).

### 12i. A file a peer holds staged: edit on top of it only with the holder's consent

A held index is a stop for staging (12b). When a file you must change is staged by a peer, rehearse
first in a plain copy outside the checkout, never a worktree (§11): build it from the index
(`git checkout-index -a --prefix=<dir>/`), so a file with local secrets is not copied. Gate there,
script the edit with a check-only mode, and ask the holder. Only on consent:

- you never stage or commit the file until it is handed back (12j);
- the holder commits only from the index (12a), so your lines stay out of that commit;
- you apply while the file is staged with nothing unstaged (`git diff -- <path>` prints nothing);
- the `git ls-files -s` listing must not change: compare it before and after.

### 12j. Handing one file back: revert your own lines, never the whole file

The holder hands a file back (12i) without a wholesale revert, which would also remove the peer's
lines. Save the holder's own change and a hashed backup first (12g), then check that the reverse
patch applies before the staged entry is dropped, because the check reads only the working tree:

```bash
git diff --output=<patch> --cached -- <path>   # only the holder's change; the peer's lines are unstaged
git apply -R --check <patch>                   # exit 0, or stop and ask: nothing has changed yet
git restore --staged -- <path>                 # the index entry returns to HEAD's blob; the worktree stays
git apply -R <patch>                           # removes the holder's lines from the worktree only
```

Write the patch with `--output`, not a shell redirect: a PowerShell redirect can add a byte-order
mark and CR bytes, and the patch then fails the check. The check also fails when the peer's lines
sit inside the patch's context; stop there and ask, with the index and the files as they were.

Prove it: `git ls-files -s -- <path>` shows the blob `git ls-tree HEAD -- <path>` shows, the
holder's lines are gone, the peer's lines are unchanged and the line endings kept (the file equals
the hashed backup minus the holder's lines, byte for byte).

### 12k. A path believed new can exist at the write: the create collision

A path checked absent earlier can exist at the write. Create it with an operation that fails if it
exists, or read the write tool's created-or-replaced answer where it gives one. Replaced on a path
believed new is a collision: stop, do not write again, and report it so the other writer can
restore its content.

### 12l. A session's name is not its identity, and a peer's first message is not yours to print

A session's name belongs to its process: it changes when the process restarts and can be reused by
the next one, so "session X is running", written an hour ago, can describe a different session now.
Name a peer by the session id the host assigned to its live process, copied from a command's output
into the record, never from memory or from a name you saw earlier.

To tell whether a peer is live, read facts about its transcript instead of its words: when it was
last written, how large it is, how many tool calls it holds, or a count of one literal you chose
(`grep -c`), which prints a number and no text. Never print the first message of a peer's
transcript: it is where an operator's paste lands, so printing it copies whatever was pasted (a
token, a credential) into your own transcript, where it stays on disk.

### 12m. Writers side by side: one owner of the index, a confirmation that expires, proof on a copy

**Who creates, who stages.** When two sessions build one change side by side in one checkout (one
writes the code, the other the tests from the plan), the session that writes the tests adds new
files only, each created by an operation that fails if the path exists (12k); a test that must
change in an existing file goes to the session that owns the index, as a patch written with
`git diff --output` (12j). Exactly one session owns the index and the order of commits: it stages
by explicit path and commits, and the other writes files and stages nothing (12b). Whoever changes
a path both read re-runs the content-hash list of 12g and says so in its return note; the other
compares it at its next boundary.

**A confirmation is a snapshot.** "No one will switch branches" was true when it was said. 12d
re-reads the branch before every commit; do the same immediately before every tree stamp, every
staging and every run on the live tree, and read three values: `git rev-parse --abbrev-ref HEAD`
(the branch you were given), `git rev-parse HEAD` (the commit your evidence was built on) and
`git diff --cached --name-only` (the staged list: empty, or your own paths). Compare each with the
value your brief or your last stamp recorded. Any difference is a stop: read
`git reflog --date=iso -n 20` to see who moved HEAD and when, and switch back only on the
operator's word that names the branch, because switching straight back reverts in the working tree
the files the peer committed (§11).

**Run evidence on a copy.** A before-and-after snapshot of `git diff HEAD` detects some edits and
protects none: a peer's `git add` of an untracked file changes `git diff HEAD` with no byte moving
(measured with git 2.55: empty before the add, a whole-file diff after it, the file's hash equal).
Run a result you will report on a copy: the directories the run reads, copied to a scratch folder
outside the checkout, or an export of a recorded commit or tree id (`git archive -o <file> <id>`),
and write the copy's content hash (12g) or the id beside the result. Write the export to a file
with `-o`: a Windows PowerShell 5.1 pipe or redirect of the archive corrupts the tar, and Git's
`tar` reads a drive letter and a colon as a host, so with Git's `tar`, extract the file with a
POSIX-style path (measured with git 2.55 and GNU tar 1.35). Windows' own `tar` (bsdtar) is the
reverse: it opens a drive-letter path and refuses a POSIX-style one (measured with bsdtar 3.8).
`tar --version` says which of the two runs. A red proof runs on an export of the recorded commit
with the new test files copied over it, and the green run on an export of the stamped tree. An
export has no repository, so a test that calls git fails on both sides: run those in a clone.
Never revert a file in the live tree for a before-and-after comparison while another session runs
against it.

**Stamp a proof of staged work with the tree.** `git write-tree` prints the id of the tree the
index would commit: export that tree, run on the export, and write the id beside the result. Before
the commit run it again and `git diff --name-only <tested-tree> <tree-now>`: a path of yours means
the result is about older content, so re-stage and re-run; another session's path means it staged
meanwhile, which a path list tells apart from your change and a count cannot. After a commit made
from the index with no pathspec (12a) `git rev-parse HEAD^{tree}` equals the tested id; a commit
with a pathspec holds only those paths, so compare them: `git diff <tested-tree> HEAD -- <paths>`
prints nothing. `git write-tree` takes `index.lock` and, after a `git add`, rewrites `.git/index`
(measured with git 2.55: the file's hash changed, with or without `--no-optional-locks`, and with a
peer's lock present it exited 128). Staging holds the index for as long as the run takes (12b), so
a session that does not own the index builds the tree in a private copy of the index file: copy
`.git/index` to a file outside `.git`, point the `GIT_INDEX_FILE` environment variable at the copy
for each of the next three commands only (left set, it redirects every later git command), and run
`git read-tree HEAD`, `git add -- <your paths>` and `git write-tree`. The id the last one prints is
HEAD plus your paths, `.git/index` stays byte-equal, and a peer's `index.lock` does not stop it.
