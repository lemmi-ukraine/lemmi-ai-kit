# F7 skill rename — self-challenge and completion review

**Dated:** 2026-08-22, at the end of the session that executed the pre-flip rename
(F7 / I4 W3.1).
**Method:** adversarial. Every claim re-measured, and the findings are stated against
my own output. The point is to find what is wrong with the work, not to certify it.
**Verdict:** the rename is complete and the merged gate is green. Four findings below
are against my process, one is a scope judgement the operator may reverse.

---

## 1. A sweep I ran returned a false CLEAN, and only luck caught it

Checking whether the brand survived in prose, I ran this and it printed nothing:

```
grep -rniE "lemmi" src/lemmi_ai_kit/assets/ | grep -viE "lemmi-ai-kit|lemmi_ai_kit|lemmi-ukraine"
```

It printed nothing because **`grep -r` prefixes every output line with the file path,
and every path under that tree contains `lemmi_ai_kit`** — so the `-v` filter deleted
every line, including the real hits. The filter was not filtering content. It was
filtering the paths its own `-r` had prepended.

I caught it only because I had run a narrower sweep seconds earlier and had four real
hits on screen. Run in the other order, I would have believed the CLEAN and reported
a de-branded pack that was not de-branded.

**The load-bearing sweep was not affected, and I re-verified rather than assumed it.**
The DoD sweep used `-o` (match only, no path prefix) with no `-v` filter at all:

```
git grep -ohE "(lemmi|fable)-[a-z0-9_-]*" -- . | sort | uniq -c
      5 <source-project name redacted: this file is published, and the
          hygiene contract bans the literal> <- rule-teaching refs, exempt under F5
     72 lemmi-ai-kit      <- package / plugin namespace
     34 lemmi-ukraine     <- org owner
```

Zero old skill names. That result stands.

**Carry forward:** never `-v`-filter the output of `grep -r`. Use `-o`, or let case do
the discriminating (`Lemmi` in prose vs `lemmi-` in identifiers), which is what
actually produced the finding in §2.

## 2. The rename removed the brand from every NAME. It survives in five content sites

My DoD line — *zero `lemmi-` or `fable-` skill names anywhere* — is **true exactly as
written, and narrower than it sounds.** Measured with a case-sensitive sweep, since the
package and org names are lowercase and the prose brand is capitalised:

| Site | Text |
|---|---|
| `python-conventions/SKILL.md:7` | frontmatter `description`: "for the Lemmi backend" |
| `python-conventions/SKILL.md:15` | H1: "Python Convention Examples — Lemmi Backend" |
| `python-conventions/references/coding-patterns.md:1` | H1: "Coding Patterns Reference — Lemmi Backend" |
| `vertical-slice/SKILL.md:14` | H1: "Vertical Slice Architecture - Lemmi Backend" |
| `templates/AGENTS.md:19` | "The shared Lemmi conventions live in the …" |

The first and the last are the ones that matter. The frontmatter `description` is the
text a model reads when deciding whether to load the skill, and `templates/AGENTS.md`
is **seeded into every adopter project** — so an adopter who installs the pack gets
another company's name written into their own repo, which is the exact sentence D4
gives as its reason for existing.

**This is a judgement, not an oversight, and it is inconsistent with a call I made two
commits earlier.** I rewrote `# Fable Orchestrate` to `# Orchestrate` on the reasoning
that an H1 is body text the model reads, then left four comparable sites alone. The
distinction I drew: `Fable Orchestrate` was the skill's *own name*, title-cased, and
renaming the skill without it would have left the rename half-done. `— Lemmi Backend`
is a *scope qualifier* — a factual claim about what these conventions are for — and
replacing it needs a decision about what the public pack's conventions are scoped to
instead. That decision is OQ-2's pack axis, and it is a one-way door.

So the defensible line is the one I took, but it is thin, and `AGENTS.md:19` is a
one-word deletion that does not depend on OQ-2 at all. **Operator call. If the answer
is "strip it now", it is five edits and none of them touch a name.**

## 3. I reported "pytest green" against a four-check gate

The DoD asked for `uv run pytest`, I ran `uv run pytest`, and I reported it. CI runs
**four** checks (`.github/workflows/ci.yaml`): `ruff check`, `ruff format --check`,
`basedpyright`, then `pytest`. My completion claim was narrower than the gate that
will actually judge the branch, and I did not say so at the time.

Run at review time, on `pre-flip`:

```
ruff check .              All checks passed!
ruff format --check .     12 files already formatted
basedpyright              0 errors, 0 warnings, 0 notes
pytest -q                 37 passed
```

No harm done. But "green" should have meant the gate, not the one command I was handed.

## 4. The merged gate was a carry-forward I inherited and did not apply

The previous session's completion review closes its first finding with:

> **Carry forward:** for any multi-branch delivery, "done" includes the merged gate.

I did better than nothing and worse than that. I ran `git merge-tree` and inspected
blobs out of the resulting tree — enough to show the merge is conflict-free and that
`test_manifest.py` ends up carrying F3's count of 29 *and* my renamed python set. I did
not run the gate on the merged state, which is what the carry-forward asks for.

Done properly at review time, and **without touching the shared working tree** — the
whole flip state assembled in the object database, then extracted to a scratch
directory outside the repo:

```
T1 = merge-tree(pre-flip, f3-stale-counts)                    clean
C1 = commit-tree T1
T2 = merge-tree(C1, readme-drop-unbacked-refresh-claim)       clean
     git archive <T2> | tar -x -C <scratch outside the repo>

skill dirs 29 · manifest entries 29 · README "29 skills" ×2 · zero old skill names
ruff check          All checks passed!
ruff format         13 files already formatted
basedpyright        0 errors, 0 warnings, 0 notes
pytest              37 passed, 2 failed
```

**The two failures are an artifact of my harness, not a defect, and I verified that
rather than assuming it.** Both are in `test_publication_hygiene.py`, which resolves
the tracked set by running `git ls-files` — and an extracted tree has no git metadata,
so it takes its `returncode != 0` branch and calls `pytest.fail("not a git work tree,
so the tracked set cannot be checked")`. That is the test working: its own docstring
says the failure mode it exists to catch is "it passed because the scan never looked",
so refusing to pass when it cannot look is correct behaviour.

Since that left the hygiene contract genuinely unverified on the merged state, I
checked it a second way — reproducing the scan against the merged tree's blobs with the
nine patterns **imported from the test rather than retyped**, because a regex retyped
through a shell loses its escaping silently:

```
patterns imported: 9
scanning 36 tracked text files outside assets/
CLEAN - no forbidden pattern outside the allowlist
```

Test-count note, so the numbers reconcile: `pre-flip` collects 37, the merged state
collects 39. The two extra are `test_readme_counts.py`, which arrives with
`f3-stale-counts`.

## 5. A branch decision I made alone, and the operator may reasonably disagree

The brief said *"you are on branch `pre-flip`"*. **There was no such branch** — the
checkout was on `i3a-contribution-surface`. I created `pre-flip` at that tip, which
moves no files, and did the work there.

What I refused to do, and why: basing on `f3-stale-counts` would have been the better
*content* base (it carries F3's corrected counts), but reaching it means checking out a
divergent sibling — deleting four skill directories and nineteen commits' worth of
files out of a working tree that **three other sessions are live in**, one of them with
uncommitted work. I judged the merge cost strictly cheaper than the disruption, then
measured the merge instead of trusting that judgement (§4: clean, and semantically
correct).

The consequence the operator has to own: **`pre-flip` does not contain F3.** Its
`manifest.toml` and `test_manifest.py` still say 33. That is correct for the branch and
wrong for the flip, and it resolves on merge, not here.

## 6. Scope discipline — measured, not asserted

- **19 paths touched**: 16 with content edits, 3 pure moves. The brief predicted 16, and
  16 is the number of files that needed an edit — the other three are files that moved
  inside a renamed directory without their content changing.
- **Nothing outside my ownership.** No `.codex-plugin/`, no `.agents/`, no
  `tests/test_plugin.py`. Every commit staged by explicit path with
  `git diff --cached --name-only` checked first; `git add -A` never run.
- **Foreign dirty files never staged.** Four when I started, six by the end, as other
  sessions worked around me. All still uncommitted and untouched.
- **No worktree, and the tree never switched** out from under the other sessions.
- **The mis-filing was flagged, not fixed**, as instructed: `vertical-slice` remains
  under profile `python` though vertical slice architecture is language-independent.

## 7. What is actually complete

| DoD item | Evidence |
|---|---|
| Zero `lemmi-` / `fable-` skill names | prefix-and-tokenize sweep, §1 |
| All 16 files consistent | 19 paths; 33/33 skills now have frontmatter `name:` matching their directory |
| `uv run pytest` green | 37 passed — and the other three CI checks too, §3 |
| Scaffold renders new names | scaffolded to a temp dir: all four names in `CLAUDE.md`, zero old names anywhere in the adopter project |
| Merges into the flip state | full gate on the merged tree, §4 |

`CLAUDE.md` needed no edit in any commit: `render_claude_md()` builds it from the
manifest, so the manifest rename propagates. That is worth stating because it is the
opposite of the F3 problem — one place where the count/name is generated rather than
hand-written, and it cost zero maintenance here.

## 8. Open, and none of it mine to close

1. **The five brand-in-prose sites** (§2) — operator, then I2's refresh.
2. **`vertical-slice` mis-filed under `python`** — OQ-2, one-way door.
3. **`manifest.toml:2`'s profile comment has never listed `orchestration`.** Left
   deliberately: `f3-stale-counts` edits that exact line to drop `prompts`, so fixing a
   comment typo here would have manufactured a conflict.
4. **`test-conventions/README.md` is a frontmatter-only duplicate** of its `SKILL.md`
   with a *different* description. Renamed, not resolved — content call for I2.
5. **Nothing enforces frontmatter `name:` == directory name.** I verified all 33 by
   hand; a five-line test makes every future rename self-checking. Same shape as F3's
   "stop hand-writing the number", and it belongs with that work.
6. **The nine hygiene patterns are duplicated in spirit across two files** — already
   flagged in `test_publication_hygiene.py`'s own comments for whoever owns
   `test_assets.py` next. Not mine, noted because I imported them and saw it.
