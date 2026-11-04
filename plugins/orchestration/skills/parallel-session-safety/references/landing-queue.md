# Landing queue: one writer per tree, a lock line, and a gate before every commit

Read this when two or more sessions can write one working tree: it gives them one queue file, one
lock and one gate. How to stage and commit in a shared index is in
[shared-index-protocol.md](shared-index-protocol.md); this file does not repeat it.

## The queue file

- **Keep one queue file per initiative, append-only, newest line last.** Nobody edits or deletes an
  earlier line, so the order of the lines is the order of the events.
- **Keep it where an append does not change the tree's status**, outside the tree or in an ignored
  folder, because every gate run compares that status line by line.
- **Write one line per event.** A line starts with its event word and the machine-clock time (read
  with `date` as you write it), then names who, by the session id the host assigned
  ([12l](shared-index-protocol.md)), and what.
- **The newest lock line is the lock.** LOCK TAKEN and LOCK TRANSFERRED name the one session that
  may write the tree; LOCK FREE says that no session does.

The five events, as neutral examples:

```text
LOCK TAKEN 14:02 session-a: lands the docs lane; real HEAD <parent id>, status = the 2 allowed lines, 0 staged
LOCK TRANSFERRED 14:40 session-a to session-b: session-a confirmed at 14:38 that it is idle and writes nothing more here
READY 15:05 tests lane, session-c: parent <parent id>, tree <tree id>, 3 commits; land with <script or commands>; gate exit 0 at 15:03
LANDED 15:20 tests lane, landed by session-b: <first id> .. <last id>, every tree as gated; real HEAD now <new id>
LOCK FREE 15:31 session-b: nothing is being landed; real HEAD <new id>, status = the 2 allowed lines
```

## Rules

- **Take the lock before the first write, and end it with a LOCK FREE line.** A session that writes
  while the newest lock line names another session is a second writer, whatever its file set.
- **One writer per tree, through the lock.** Every other session builds in its own clone or export
  and delivers a chain with a READY line, so a file partition is never the only guard.
- **Sub-agents never write in the tree.** A sub-agent delivers a patch or an export; only the main
  session that holds the lock lands it.
- **Transfer the lock only after the old owner confirms that it is idle.** Waiting for that answer
  is the control, not asking for it: the LOCK TRANSFERRED line is written after the confirmation.
- **If the old owner was stopped and cannot answer, only the operator moves the lock.** A stopped
  session can be resumed later, and only the operator knows whether it will be, so the LOCK
  TRANSFERRED line quotes the operator's ruling and the time of the owner's latest checkpoint, or
  says that there is none.
- **A lane starts landing only when the real HEAD equals its chain's parent.** A chain built on
  another commit carries trees that nobody gated.
- **A lane that finds the parent moved rebuilds on the new tip and writes a new READY line.** The new
  line names the line it replaces, and nobody repairs a stopped landing by hand.
- **Read the status before every write, not only at the start.** A session found the checkout's
  status unchanged by a second writer only because it read the status before every write
  (observed, 2026-11-04).

## The gate before every commit

Run it in the real tree under the lock, before each commit of a chain: the first with the parent the
READY line recorded, each later one with the commit just landed (now the real HEAD) as `--parent`,
and each with that commit's own patch, tree and paths file, which the READY line's script or
commands give:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/landing_gate.py" check --repo <tree> --parent <parent id> \
  --patch <patch file> --tree <tree id> --allow '<status line>' --paths <paths file>
```

- **What it checks:** HEAD is the parent; the status is exactly the `--allow` lines, each written as
  `git status --porcelain --untracked-files=all` prints it; nothing is staged; the patch, replayed
  on the parent in a private index, writes the `--tree`; with `--paths`, the patch changes exactly
  those paths; the patch changes at least one path, and `git add --` would store exactly the patch
  from this working tree, because each changed path is still the parent's file there, is not
  ignored, and has an executable bit and line ends that this repository stores as the patch has
  them. Run it
  before you apply the patch, and allow only status lines for paths the patch leaves alone: a peer's
  edit to a changed path fails even when its line is allowed or hidden from the status, because
  `git add --` would store it in the landing commit. It writes nothing in the tree, the index or
  any ref.
- **Exit 0:** every check measured and passed, and it printed the landing commands with a pathspec on
  both `git add --` and `git commit --`; run each yourself, in its own call.
- **Exit 1:** a check failed and the output names what it saw; do not commit.
- **Exit 2:** it could not measure (a git error, a missing input, a patch that does not apply), and
  that is never a pass.
- **Write the LANDED line only after `git rev-parse HEAD^{tree}` prints the `--tree`.**

## From the first day of an initiative

- **One orchestrator per lane, plus one queue owner.** The queue file's first lines name the queue
  owner and the lanes; the queue owner keeps the landing order and the last version stamp.
- **The queue and the lock exist before the first landing**, so the first landing does not invent
  the protocol under time pressure.
- **Set a freeze point before the last version stamp.** From the freeze point (90 minutes before
  the stamp, a starting value, uncalibrated) lanes land nothing and write only a drafts file, so
  the stamp lands on the tree the final gates ran on.
- **Keep a lessons slot that survives the stamp:** a file beside the queue, outside the stamped
  tree, so a lesson found after the stamp has a home until the next release lands it.
