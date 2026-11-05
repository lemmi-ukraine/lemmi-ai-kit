# Layer mechanics — the fork base, where tests ride, committing a layer

## The fork base is a decision when HEAD sits on an unmerged chain

Before writing a new initiative's fork base, list what HEAD carries that the trunk does not (fetch
first: the range reads the cached remote-tracking ref):

```bash
git log --oneline origin/<trunk>..HEAD
```

When HEAD sits on another initiative's unmerged chain, "fork from the current branch" ties the new
initiative's merge path to that chain: put the fork base to the operator as a decision, with each
option's measured side effect:

```bash
git diff --name-status origin/<trunk> HEAD
```

Its `M` and `D` rows list the files that differ from the trunk: a landing that takes HEAD's tree
reverts those the trunk changed since the chain forked and removes those only the trunk has. A
standing "fork from the current branch" rule stays the operator's to waive; do not waive it for them.

## Where the tests of unmerged layers ride

Where the tests of unmerged layers ride decides which heads can pass a gate that runs the base's
suite on each head. When each PR is signed off and merged alone, every layer carries the tests its
own change needs; put them in one PR on top only when the stack merges as a unit, and say so in that
PR's body. A test belongs to the layer whose code it imports, not to the layer of the task that wrote
it.

## Before committing a layer

- Before committing a layer without its test edits, diff each test file against HEAD
  (`git diff HEAD -- <test file>`). When an assertion, a fixture or a setup line changed, run the old
  test against the new code; if it fails, the test belongs in this layer.
- Two layers that edit one file need the first committed before the second starts, or the second
  layer's commit takes the first layer's hunks with it.
