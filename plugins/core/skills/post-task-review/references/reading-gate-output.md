# Reading a gate's output — five ways a correct check produced a wrong verdict

AGENTS.md § Do not carries the rule: *a gate's verdict is its log, never its exit code and never a
filtered tail.* This file is the next layer down — cases where the log **was** read, in full, and the
verdict was still wrong, because the instrument or its framing was faulty.

All five are measured. Three of them cost real work: two nearly voided clean runs, one nearly
licensed a deletion.

---

## 1. `git diff HEAD --stat` is not a stable fingerprint — its BARS rescale

AGENTS.md requires snapshotting `git diff HEAD --stat` before and after any suite run you will
report, voiding the verdict if the set changed. That rule is right; `--stat` is the wrong instrument
for it.

`--stat` renders a **proportional histogram scaled to the largest change in the set**. Growing one
unrelated file rescales the bar on every other row:

```
connection_manager.py | 219 ++++++++++      # before
connection_manager.py | 219 +++++++++       # after — same 219, narrower bar
```

**Measured**: appending learnings entries during a 6-minute integration run took
`.ai/learnings.md` from 440 → 505 insertions, which rescaled every bar. A naive `diff` of the two
snapshots reported those rows as changed, and the rule as written **voids a green 441-pass run**. The
numeric columns were identical for every `backend/` and `tests/` path; the entire +65 delta was one
file the suite never opens.

> **Use `git diff HEAD --numstat`** — raw counts, no bars — or scope the compare to the paths the
> suite actually reads. When snapshots do differ, diff the **numeric columns** before voiding
> anything. A bar-width difference is not a torn tree.

**The second instrument in the same incident also failed:** an mtime check using `st_ctime` as "run
start" printed a window of `21:15:19 -> 17:39:15` — start *after* end. On Windows `st_ctime` is
**creation** time. For "was this file touched during the window", anchor on the **mtime of a file
written by the launching command**, never `st_ctime`.

## 2. "Every reviewed file still matches the SHA" does not validate a suite verdict

The standard torn-tree check — *did any file in my diff change?* — is necessary and **not
sufficient**, because a test's inputs are not limited to the change under review.

**Measured.** A per-file `git diff --quiet <sha> -- <path>` showed **18 of 19** reviewed files
still byte-matched, so `ruff` and `basedpyright` stayed valid. But the pytest batch included an
env-parity test that reads two build manifests **from disk** via module-level `Path` constants — and
one of those manifests was the single file that differed, because another session had checked out a
different branch mid-run.

That parity test **passed** — against a different branch's manifest — and would have been quoted as a
green gate. **A passing gate on the wrong input is the silent failure in the worst direction.**

> Before quoting a suite result in a contended checkout, ask **what each test READS**, not only which
> files the change touched. For any test reading a repo file from disk, re-derive the result from the
> committed blob (`git show <sha>:<path>`) rather than trusting the on-disk run.

## 3. A gate can run against a state that PREDATES the artifact it judges

**Measured.** A whole-tree hand-off lint (263 files, ~3 min) was reported as
*"exit 1, 89 findings, of which zero name this file"* — and that claim was repeated inside a tracked
review report. The scan had **started before the handoff was written**. It never saw the file.

**The tell was unavailable by construction:** a file with no findings emits **no output line at
all**, so "my filename is absent" is equally consistent with *clean* and with *never scanned*, and no
grep over the output can separate them. Re-running against the file as it actually existed produced
**3 ERRORs, all mine**.

> Never report a long-running gate that started before your last edit to the thing it judges — note
> the start time relative to the write, or re-run. **For any gate whose clean result is SILENT,
> prove reach with the DELTA across runs** (89 → 86, exactly the three findings fixed, contract count
> unchanged at 171/263), never with the absence of your own filename.

Sibling of the stale-Docker-image trap, with the difference that matters: there, grepping the log for
a test the change ADDED works, because a present test emits a line. Here the clean case is silent, so
the equivalent grep fails in both directions.

## 4. An `||`-chained redirect can skip its fallback and produce a false data-loss alarm

```bash
git diff > /tmp/x.patch 2>/dev/null || git diff > <fallback>/y.patch   # WRONG
```

**Measured**, verifying that ~1600 lines of another session's restored work were intact. The first
redirect trivially succeeded (writing to `/tmp`, which the project's conventions already avoid), so
the `||` fallback never ran — and the subsequent `diff` compared against a **stale**
`y.patch` from an earlier step, reporting **"DIFFERS"** on a real data-loss check. Caught only by
manually re-running a single unambiguous redirect.

> Never use an `||`-chained redirect inside a data-integrity or restoration check. One branch
> succeeding *for the wrong reason* silently invalidates the comparison. Use one plain redirect per
> check and diff against a known-good baseline directly.

## 5. Comparing a git blob to a working-tree file is a LINE-ENDING test, not a content test

`git show <ref>:<path>` returns the blob **as stored** (LF under this repo's `.gitattributes`); the
working-tree copy is **CRLF**. A `sha256sum` of the two therefore *always* differs for any text file,
whatever the content.

**Measured**: verifying 22 archived files were byte-identical to what git held reported
**0 identical / 22 problems**. The archive was perfect. The same false alarm fired **three times in
one session** — on an archive, on a PR body repair, and on a `git show`-based doc comparison.

The verdict reads as catastrophic — *every* file wrong — which is exactly the shape that prompts a
panicked re-do of correct work.

> Normalise before comparing (`tr -d '\r'`) whenever one side comes from git and the other from disk,
> and **treat an all-files-differ result as an instrument fault until proven otherwise.** The
> strongest content proof needs no hashing at all: `git apply --check --reverse <patch>` against the
> tree (passed for 23 uncommitted files across five rebases).

---

## 6. A zero with no denominator cannot be distinguished from a gate that never ran

This is the cheapest fix in this file and the most frequently needed. **Always print the
denominator beside the zero.**

```text
0 findings                      <- unreadable: clean? or nothing scanned?
0 findings across 344 files     <- a verdict
```

Measured instances, all of which read as a clean pass:

- A gate output file of **zero bytes** scored `PASS`, on the evidence `EXITCODE=0, FILEBYTES=0` —
  inside a *verification* agent whose own prompt required it to read the file it had redirected.
- A **marker-gated** linter returned `[]` for a file it never opened, because the file lacked the
  opt-in marker. The silence read exactly like a pass. Several sessions reported "lint-clean" for
  files the linter had not reached.
- A directory lint that scans **alphabetically** and exceeds its timeout reported clean for every
  file after the cutoff.
- A redirected command that died with `Argument list too long` was read as "zero hits" — and
  published.

The remedy generalises past linting: any instrument reporting an absence should report the size of
the set it searched. A zero over an unstated population is not a finding, it is an **unread**
result. Two corollaries:

- **A probe cannot see a *missing* input.** Pair every manifest or inventory check with a
  set-difference against the live tree — otherwise the check silently passes on the files nobody
  listed.
- **Exclude yourself from your own measurement, and say so.** An instrument whose output lands
  inside the corpus it measures will find itself. One recorded sweep recursed into its own growing
  output file, reached **34 GB**, and exhausted the disk.

---

## 7. Concrete command traps — each one ran, exited 0, and answered a different question

Measured instances. Every row below produced a confident wrong answer that drove a decision.

| Command shape | What you think it does | What it does |
|---|---|---|
| `grep -E 'a\|b'` | alternation | `\|` inside `-E` is a **literal pipe**; `-E` wants a bare `\|`. Four "0 files untracked" results in one sweep were silent zeros |
| `git grep 'def name\b'` | word-boundary match | plain `git grep` is BRE and does not know `\b` — reported **29 real tests ABSENT**. Use `-E` |
| `git grep <pat> HEAD` | searches your fix | searches the **commit**, so your just-applied worktree fix reads as still-broken |
| `git grep <pat>` (no rev) | searches the committed tree | searches the **worktree**, so a "has it landed?" gate passes on a peer's uncommitted edit |
| `grep -r -- "$p" DIR --include='*.md'` | restricts to the glob | the `--include` after the path is ignored; it searches **everything**. The giveaway is on **stderr** |
| `git diff --stat` (one number) | insertions | that number is **added + removed**. Use `--numstat` for any count you write down |
| `git diff --stat` (paths) | full paths | long paths are **abbreviated** with `...`, so grepping its output for a directory reports "only READMEs changed" for exactly the deep files you were looking for |
| `git log -- <path> --invert-grep --grep=X` | excludes X | flags after `--` are **pathspecs**, so it counts instead of excluding |
| `echo "$(cmd) rc=$?"` | the command's status | `$?` is the **command substitution's** status — seven failing gates read as `rc=0` |
| `cmd > out.log` (long run) | you will see the error | Python buffers stdout, so a hang and a crash look **identical** from outside. Use unbuffered output or check the process |
| `ls <path> 2>&1 \| grep <pat>` in a DoD | proves presence | the *error text* contains the path, so absence reports as success |
| `str.index("## Heading")` | finds the heading | matches the **prose that mentions** the heading first — silently duplicated a 166 KB document |
| a `\b` written into generated file **content** | a regex boundary | arrives at the next reader as the **BACKSPACE escape** (`0x08`), putting invisible bytes into a committed file |
| an italic-span regex over markdown | italics | swallows every **bold** span too, so a citation audit can report a whole document as uncited |
| a single-quoted heredoc holding `\\` | literal backslashes | the Bash tool still mangles them, so a Python script silently stops matching. Write the script to a **file** |
| `grep` on a wide table row | the whole line | the harness may print `[Omitted long matching line]`; read the span with one file read rather than one read per line |

The general rule underneath all of them: **run the command against a case whose answer you already
know before you trust it on a case whose answer you don't.** Every row here would have been caught
by a single known-positive/known-negative pair.

---

## The shape they share

In every case the command ran, exited as designed, and printed a true statement — about something
other than the question being asked. So the guard is not "read the log"; it is **state which question
the command answers, next to the number it produces**, and check that it is the question you have.

Case 6 is the same shape seen from the other side: when the number is a **zero**, the question it
answers is "how many did you find *in what*?" — and a zero that omits the second half has not
answered it.
