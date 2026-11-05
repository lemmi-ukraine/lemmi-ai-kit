# Layer triggers — guards, counters and the target's delta

Each trigger is a command with an expected result, run at every dispatch round; one that fires
re-opens the topology that day.

## A declared-file guard exempts the checklist's logs

A trigger that fires when a layer changes a path outside the files its row declares must exempt the
tracked logs the project's completion checklist appends to (the learnings buffer, the AI changelog),
as a pattern line of its own, or it fires on every compliant branch:

```bash
git diff --name-only <base>...<layer> | grep -vE '<declared files regex>' | grep -vE '^\.ai/(learnings|ai-changelog)\.md$'
```

Fires when the output is non-empty. A correction to one layer's guard is a topology revision: grep
every other layer's guard and the table's rows for the old pattern in the same edit.

## The class counters have an accepted mixed reading

Step 6's sample counts `.ai/` as DOCS and `tests/` as TOOLING, while Step 2 defines BACKEND as
production code and the tests that gate it, so a healthy BACKEND layer that carries its tests or
follows the checklist reads mixed. Record that reading in the layer's row and do not reopen the
plan; a count in a class the row does not accept still fires.

## A task conditional on the base's contents re-fires at every merge from the base

A task written "once the base has X, do Y" is not settled when its condition first reads false: a
merge from the base, a rebase or a cascade can make it true with the layer's own diff untouched, and
the layer then fails the base's tests. Write the condition as a command the cascade step runs:

```bash
git ls-tree -r --name-only <base-tip> -- <file>
```

Non-empty output means the condition now holds. An empty result still exits 0: read the output.

## The target's delta since the pin

A kickoff that pins the target by hash shows that the target moved, not what moved. At every
dispatch round, list what the target changed in each layer's paths, and read its change to the file
that holds the project's branch and testing rules (a replaced rule can invalidate a layer the delta
never touches):

```bash
git diff --name-status <pin> origin/<target> -- $(git diff --name-only <base>...<layer>)
git diff <pin> origin/<target> -- <rules file>
```

Output of the first command re-opens that layer (a `D` row first); a layer with no changed path gives
an empty pathspec and prints the whole delta, so skip it. Both compare endpoints, so a rebase of the
target does not inflate them the way it inflates a commit count.
