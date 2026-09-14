# Settle-and-preserve — six measured lessons for Steps 1–3

Companion to `SKILL.md` Steps 1–3. Each section is one failure a retirement pass actually produced;
the numbers are measurements from the corpus they came from, not thresholds.

## Step 1 — a document's own Status line is the least-maintained claim in it

**And its staleness is DIRECTIONAL: it over-reports openness, every time.** Fixing a defect and
updating its ticket are separate acts, performed by different sessions at different times, and only
the first is forced by a gate. Measured in one retirement pass: **4 of 4** Status lines checked were
stale toward "still open".

The consequence is asymmetric and easy to miss — a retirement pass that reads Status lines
systematically **keeps documents it should retire**, and a triage that reads them systematically
**re-opens finished work**. Neither failure announces itself, because in both cases the document
agrees with the reader. Settle every row against `git grep` for the fix, never against the Status
line, and never against ancestry (squash-merge breaks `--is-ancestor`).

## Step 1 — an orphan sweep shaped like an identifier cannot find an id-less finding

An id, a filename or a `Home:` field **is routing metadata** — a finding that carries one has already
been through somebody's routing step. So an identifier-shaped sweep enumerates the findings that are
*already half-routed* and is structurally blind to the genuinely orphaned ones.

Measured: the highest-severity orphan in one corpus had no id at all. It was a prose section heading —
*"the measured blast radius is FAR smaller than its ticket assumed"* — carrying a production
measurement, and every identifier sweep passed clean over it. Sweep for **claims** (headings, bolded
assertions, numbers with units), not only for ids.

## Step 1 — a handed list of orphaned findings is a claims sheet

Of three sub-findings handed to one routing session, **one was real, one was misframed, and one was
already in the ticket under different wording** — "12 of 31 citations resolve to the wrong line" was
that ticket's own *title*. The previous session's `grep -c` had been true of the **string** and false
of the **finding set**, because a finding is reworded on its way into its home while the token
someone grepped does not travel with it.

The routing task's real failure mode is therefore **writing a non-finding into a durable file**.
Verify each item against its putative home by *concept* before creating a row for it.

## Step 2 — there is a THIRD state, and both durability checks call it durable: tracked-but-uncommitted

`git ls-files --error-unmatch <path>` answers "tracked"; `git check-ignore -q <path>` answers "could be
committed". A file can pass both while almost all of its *content* has never been committed. Measured
at one commit: `git show HEAD:.ai/learnings.md | grep -c '^### '` → **14** against
`grep -c '^### ' .ai/learnings.md` → **183** in the worktree — **92% of the file had no history at
all**, and the initiative's own designated durable home was sitting in that state. It survives
`git clean -fdx` (unlike untracked), which is exactly why it feels safe. Neither existing check can see
it, so add the content-level one whenever you are about to delete something on the strength of "git
has it":

```
git show HEAD:<path> | wc -l      # what history actually holds
wc -l <path>                      # what you are about to rely on
```

Re-measured before a later drain: **12** entries at `HEAD` against **303** in the worktree. If the two
disagree materially, git history is *not* the backup — snapshot and commit before deleting.

Two related traps in the checks themselves: pass a FILE, never a directory and never a trailing slash
(`check-ignore` can flip its verdict on one character), and read the `-v` output rather than reasoning
from a remembered result — an ignore status changes under you as `.gitignore` grows.

## Step 3 — the inverse loss: a committed file whose evidence pointer is a channel path

The guarded direction is "a finding that lives only in a channel file". The unguarded direction is
larger. Measured tree-wide:

```
git grep -l '\.ai/handoffs/' HEAD -- tasks/ .specs/ docs/ | wc -l
```

**67 committed files carrying 179 such citations** (re-measured two days after the entry that produced
this rule said 56/88, which is how fast this number moves). After cleanup the *conclusion* survives and
its *derivation* becomes unresolvable — the reader cannot check the claim, and cannot tell that they
cannot. Before removing any channel file, grep the committed corpus for citations of it and inline the
evidence into the citing file.

## Step 3 — staleness is a per-citation verdict and does not aggregate to a file

"The citations into this file are already stale" was a **7-of-29 sample** generalised to the whole
file, and it licensed a cut that moved 11 correct citations. The sample was biased in a way that was
invisible from inside it: the document sampled was a reconciliation ledger written weeks earlier — the
artifact most likely to be stale — while the correct citations sat in specs written days before.

A sample can justify *looking further*. It cannot license a file-level edit. Resolve every citation you
are about to invalidate, or state the count you did not check.
