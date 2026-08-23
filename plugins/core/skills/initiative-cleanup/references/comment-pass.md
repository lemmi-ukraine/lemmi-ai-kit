# Comment-reduction pass — the detail behind SKILL.md Step 5

Read this when the operator has asked for a comment trim over the code an initiative added.
It applies only then; a cleanup run that was not asked for a trim skips Step 5 entirely.

## Scoping the file set

Scope it to code **this initiative added**, including files not yet committed — a committed-range
diff lists no untracked file, and new code is routinely still untracked at cleanup time:

```bash
{ git diff --name-only --diff-filter=d <initiative-base>..HEAD -- '<src>/**/*.py' 'tests/**/*.py'
  git ls-files --others --exclude-standard -- '<src>/**/*.py' 'tests/**/*.py'; } | sort -u
```

**Scope the pathspec, or the pass edits what Step 3 just preserved.** Unscoped, the untracked arm
returns everything: measured 2026-08-04, **30 untracked `.py` files of which 26 were under `.ai/`** —
22 of them backup copies of retired work made minutes earlier by Step 3. A comment pass that rewrites
its own preservation copies is worse than no pass. Exclude `.ai/**` and name the source trees.

`--diff-filter=d` drops deleted paths, which the plain form happily returns. Re-check each surviving
file exists (Step 0).

## Judging each comment

**There is no evidence-based comment-density target, and this skill does not invent one.** No
authoritative source states a target ratio. Judge per comment, then *report the delta* — never work
toward a percentage.

| Verdict | Test |
|---|---|
| **KEEP** | Explains a non-obvious *why* or a design rationale · pins an invariant a future edit could silently break · **carries the only copy of a measurement** (e.g. a census that justifies a constant) — *this clause is local, not from the cited sources, and it is the one that saves evidence* · docstring on a public-API, nontrivial, or non-obvious function |
| **CUT** | Restates what the line does · narrates history git already holds ("changed from X in the I13 pass") · a section banner that adds no information · docstring on a trivial private helper whose name says it |
| **SHORTEN** | Right content, three lines where one does |
| **RELOCATE** | It is really a spec — move it into the spec and leave a link |

The criteria come from Ousterhout ("Comments should describe things that are not obvious from the
code"; "Mistake #1: comments duplicate code") and Google's Python style guide (a docstring is required
when a function is public API, nontrivial, or non-obvious — and "never describe the code").

**Docstrings are usually the majority of the surface.** In the one measurement available, 249 of 386
comment-ish lines were docstrings (137 `#` + 249 docstring) — a pass that only touches `#` lines
addresses about a third of the problem.

**The cut criterion is duplication, not length.** A long comment carrying a measurement that exists
nowhere else is a KEEP; a one-line comment restating the code is a CUT.
