# R-2 — can an outsider author a pack from the document alone? Measured: no.

**Dated:** 2026-08-24. **Deliverable:** D21. **Question:** *Can someone who did not write it author
a valid, testable pack from `docs/authoring-a-pack.md` alone?*

This is the initiative's own falsifier — the row that exists to test the funnel premise rather than
confirm it. Its output is **a number and a stall point**, not a review. Filed by orchestration
because the session was forbidden to write inside the repository, which is part of how the test stays
valid.

## The number: 0 of 10

The document supplies its own denominator: three scaffolded files, plus *"a pack is not real until
all seven are done"* — ten items. A cold author completes **three empty paths, zero bytes of
specified content, and none of the seven registration edits.**

**The stop is at step 1 and it is structural, not effort:**

```
$ uv run python -B -m lemmi_ai_kit new-pack rust --skill rust-conventions --dry-run
error: not inside a git checkout: <scratch dir>
```

The only construction path the document offers writes into a clone of this repository, and **no file's
contents are stated anywhere in the document**, so when the tool is unavailable the prose cannot
recover you.

## The more useful number: ~7 of 10, with 3 blocked

For a realistic contributor — has the clone, may read it and copy patterns, but no prior knowledge —
seven rows are reachable and **three are blocked: registration steps 2, 5 and 7.** Those three are
**decisions, not lookups**, which is why copying the neighbouring pack does not resolve them.

## The stalls that mattered

| Wanted | Document said | Needed |
|---|---|---|
| Write either `plugin.json` | "derived from `pyproject.toml`" / only a path | the keys. The schema is one hop out, in `plugins/_template/README.md`; the Codex manifest is not described at all, not even as sharing the Claude schema |
| Write `SKILL.md` | "a skeleton with `TODO` markers" | the frontmatter contract. §3 says `audit-skills` checks "frontmatter" and never says what it checks |
| Registration row 5 / row 7 | `upstream` required, `""` when no counterpart; row 7 "only for a `kit-origin` skill" | **`kit-origin` appears three times and is never defined.** Whether `upstream == ""` *is* kit-origin is never joined — a coin flip costing either a red suite or a silently unpinned direction |
| Registration row 3 | names five symbols and flags the trap — the strongest row | what a **profile** is, and whether pack:profile is 1:1 |
| A multi-skill pack | `--skill` shown once | the repeat syntax; and `--author`'s value format |

**Everything it had to infer:** run from the repo root · `--author` takes a bare string · one pack =
one profile · a brand-new skill takes `upstream = ""` · both manifests share a schema · the hosts are
exactly Claude and Codex. **An inference that happens to be right is still a gap**, because the next
author may infer differently.

## A live trap the document did not cover, found by walking into it

A bare `python -c "import lemmi_ai_kit"` run **from outside the repository** still wrote
`plugins/core/src/lemmi_ai_kit/__pycache__/__init__.cpython-311.pyc` **into the repository** — the
exact untracked bytecode `publish-check` refuses on. An author following steps 1–2 without `-B`
therefore poisons the check before reaching step 3, and the failure names files they never wrote.
The session removed the artifact and restored the tree.

The `-B` advice existed, attached to one command, when the hazard belongs to all of them.

## What the document does well, and it is worth saying

**The verification section is its strongest part by a wide margin** — three commands, the expected
end state, and two by-construction failures with `file:line` and the fix for each. That is better than
most repositories manage. Three caveats stand: verification is all-or-nothing and repo-global, with no
way to check *just* your pack; and the pinned suite figure was a hardcoded number that rots silently.

## Fixed in response, same day

- **`kit-origin` is now defined at first use** and tied to `upstream = ""`, with the consequence
  stated: a pack you author is kit-origin by definition, so step 7 applies to every skill in it.
- **The `-B` hazard is broadened to every command**, carrying R-2's measurement and the
  `PYTHONDONTWRITEBYTECODE=1` alternative.
- **The hardcoded suite figure is gone.** The document now tells the author to establish their own
  baseline on a clean checkout instead of comparing against a printed number.
- **The two by-construction failures no longer exist** — `386a507` derived them, along with the
  quieter third the session flagged. The document's instruction to fix them yourself was stale within
  a day and is replaced by a record of the shape, so the next one is recognisable.

## The limit on this test, reported by the session against its own result

**A subagent in this environment cannot be fully starved of context.** `MEMORY.md` is auto-injected
before any file is read, and it carried fourteen prior findings about this repository — at least three
bearing directly on this test, including one that *is* the step-3/step-4 trap the document warns
about, and others that pre-loaded the existence of an upstream project and of `kit-origin` as a
concept.

**This biases the charitable 7-of-10 upward; a genuinely cold author would land lower.** The session
volunteered this unprompted, knowing it discounted its own headline number. It also noted the one way
the contamination cut usefully: it could see the `kit-origin` gap *because* it noticed itself
importing the meaning from memory rather than from the page.

**R-2 should be re-run from a machine with no memory of this project before D21 is called settled.**

## Verdict

> *"A good checklist for someone who already has the map. It is not a specification. Its answer to
> 'what is in these files' is, in every case, a pointer somewhere else."*

**DoD 6 is not met by the document alone**, and that is the finding the row was funded to produce.
The registration table, the three named traps and the verification section are real assets; the gap
is that nothing states file contents, so the document assumes the clone it is trying to help someone
work without.
