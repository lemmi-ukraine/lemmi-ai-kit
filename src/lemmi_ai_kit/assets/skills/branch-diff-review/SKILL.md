---
name: branch-diff-review
description: >
  Produce a DURABLE tracked findings document for committed work on a branch measured against a base
  ref — no PR required, and local uncommitted work deliberately excluded. Owns the report format, a
  per-finding verification pass in which severity may change only on a recorded check output, the
  torn-tree/re-verification protocol, and cross-branch ownership routing when sibling branches carry
  duplicate commits. Delegates finding generation to /code-review and evidence discipline to
  pr-review-concise rather than restating either.
when_to_use: >
  "review this branch against dev", "compare dev and the current branch and review it", "review what
  codex/the teammate implemented", "deep review before this becomes a PR", or any review whose
  findings must outlive the session as a file rather than as comments.
argument-hint: "[base ref, e.g. origin/dev]"
metadata:
  type: review
---

# Branch Diff Review — a findings document that outlives the session

ultrathink

**Not `context: fork`, deliberately.** Two steps need the main session: the report's tracking status
and the routing-handoff decision are operator-facing (step 7), and a forked review cannot hold that
loop. Finding-generation is read-only by instruction — do not edit reviewed files while reviewing.
The only file this skill writes is the report.

## When this skill activates

- Committed work on a branch needs review against a base (`origin/dev`), and **there is no PR yet**.
- The findings must survive as a file — to route fixes across branches, to hand to an orchestration
  session, or because the reviewer is not the author.

**Pick the right skill first.** All four overlap and only one fits each request:

| Situation | Use |
|---|---|
| A PR exists and comments will be posted for a human | `pr-review-concise` |
| Your own uncommitted work, and you will fix it now | `post-task-review` |
| Fast findings on a diff/branch, no durable artifact needed | built-in `/code-review` |
| Committed branch vs a base, findings must persist as a file | **this skill** |

This skill is **not** a second review engine. It is a *procedure and a format* wrapped around one
(see step 3).

## The one thing to read before running this

`pr-review-concise` step 5 states: *"Never run a second-pass LLM judge over your own comments"*, and
its anti-pattern table calls a second pass a **"documented dead end"**. Step 4 of this skill is a
second pass over your own findings. Read this reconciliation or you will either skip step 4 or run
the banned version of it.

**Both rules are correct, because they describe different operations.**

- **Banned (and still banned): re-rating.** Re-reading your findings and re-scoring severity or
  confidence from judgment. Evidence against it is strong: self-correction "based solely on
  [the model's] inherent capabilities, without the crutch of external feedback" degrades performance
  (Huang et al., ICLR 2024), and LLM evaluators favour their own generations (Panickssery et al.,
  NeurIPS 2024) — so a re-scoring pass is biased toward *keeping* findings.
- **Required here: verification.** Each finding gets a **named check, executed, with its output
  recorded**. Self-correction *does* work "in tasks that can use reliable external feedback",
  specifically decomposable tasks and tasks with external tools (Kamoi et al., 2024) — which is
  exactly a per-finding check against a tree.

**Quote the survey's negative alongside its positive, or the citation is selective.** The same paper
says: *"no prior work demonstrates successful self-correction with feedback from prompted LLMs, except
for studies in tasks that are exceptionally suited for self-correction."* This pass claims to be one of
the exceptions **only** to the extent its checks are real commands.

**And the analogy is partial, so do not oversell it.** Kamoi's qualifying example is code generation,
where the tool is an oracle *on the answer*. A `grep` is an oracle on the **evidence** — you still
adjudicate whether the evidence means "defect". That gap is exactly why the checklist is split into
tool-grounded and judgment-only halves.

The operational difference is one rule, and it is the core of this skill:

> **Severity may change only as the mechanical consequence of a recorded output from a
> tool-grounded (Part A) check.** No output — and every judgment-only (Part B) item — leaves severity
> unchanged and caps confidence at `PLAUSIBLE`.

That split is not decoration. An earlier draft of `references/finding-verification.md` claimed *all* its
items were operations with outputs; three were not, and one of those three is the item that produced
the source run's top-severity finding. A judgment item running under the verification banner **is** the
banned operation.

## Step 1 — Establish the input, and state what it excludes

```bash
git fetch origin <base>                      # never review against an unfetched ref
git rev-parse --verify origin/<base>         # resolve it explicitly; a || fallback cannot
git diff --stat origin/<base>...HEAD         # THREE dots
git diff HEAD --stat                         # snapshot the dirty set BEFORE reviewing
```

**Three dots, not two.** `A...B` is `git diff $(git merge-base A B) B`; `A..B` is plain `git diff A B`.
If the base advanced after the branch forked, two-dot renders the base's own new commits as phantom
deletions in your diff.

**Check whether it matters on THIS pair before arguing about it:**

```bash
git merge-base --is-ancestor origin/<base> HEAD   # exit 0 → base IS the merge-base
```

Exit 0 means the base has not advanced since the fork, so the two forms are **identical** and the
distinction is moot for this run — measured on a real pair where both produced 36 files / 3812
insertions. Exit 1 means the base moved and three-dot is load-bearing; say which case you were in,
because a reader who sees identical output and no explanation will conclude two-dot is fine in general.

Read the snapshot's **last line** — on this host `git diff --stat` also emits CRLF warnings to stderr,
and the dirty-set count is deliberately unrelated to the reviewed diff.

**Committed only.** Local uncommitted work is out of scope. Say so in the report — a tree with
modified tracked files can produce a clean verdict on code that is about to change.

**Re-snapshot `git diff HEAD --stat` after reviewing.** If the set changed, another session edited the
tree mid-review and the verdict is void — restart, do not merge a stale verdict
(`parallel-session-safety` § 6, which also notes `git status --short` under-reports).

## Step 2 — Map ownership before reviewing anything

A finding is only actionable if exactly one branch owns its code.

```bash
git log --oneline origin/<base>..HEAD
git log --oneline --all --grep="<a commit subject from above>"   # same work on a sibling branch?
git merge-base <branchA> <branchB>
```

Duplicate commits across sibling branches (same subject, different SHAs) mean **no finding has a
single owning branch** — record ownership as unresolved and route nothing until the operator settles
the topology. Code below the merge-base is owned by neither branch exclusively; a fix there reaches
only the branch you apply it to.

This is the step `/code-review` cannot do for you, and it belongs *before* review because it decides
whether findings are routable at all.

## Step 3 — Generate findings (delegate; do not reinvent)

Run the built-in **`/code-review`** with the branch target and an explicit effort level — e.g.
`/code-review origin/dev...HEAD high`. Its dial is real: low/medium yield fewer high-confidence
findings, high/max broaden coverage and admit uncertain ones. Pick from blast radius, not habit.

**Confirm the diff basis before trusting the findings.** What basis `/code-review` uses for a branch
target is **UNKNOWN** from inside this repo — its definition is not a readable file here. So compare its
reported file set against step 1's `git diff --stat <base>...HEAD` and state which basis produced the
findings. If they disagree, step 1's three-dot argument is the one to keep, and re-run scoped to the
file list. Do not skip this: without it, the most-emphasised rule in step 1 may be decorative.

**All eight `pr-review-concise` steps, classified** — an unclassified step is one a reader will apply
or drop at random:

| Step | Decision |
|---|---|
| 1 — two posted surfaces, two budgets | **Not applicable** — no PR, no posted surface |
| 2 — the ≤300-char output shape | **Do NOT inherit** (see below) |
| 3 — the posting gate | **Do NOT inherit** (see below) |
| 4 — depth by lane, not uniform | **Inherit.** A migration, a security hook and a docs change in one branch do not get equal attention; `/code-review`'s dial is uniform across the diff, so allocate depth yourself and record it |
| 5 — evidence discipline | **Inherit**, and re-home its fields (below) |
| 6 — the summary body | **Inherit as the report's Coverage section** — this is where step 5's fields exist in template form (`Coverage` / `Checked for` / `Not checked`, falsification-test column) |
| 7 — known false positives here | **Inherit** verbatim; read before raising anything |
| 8 — posting is separately authorized | **Not applicable**, but its spirit carries: writing the report is fine, committing it is not (step 7) |

**Why not steps 2 and 3.** Both exist because inline comments compete for a human's attention on a diff
line. A durable document has no per-finding attention budget, and its failure mode is the opposite:
under-reporting, then being cited for months without re-verification. Suppressing a real Minor to
satisfy a comment-economy gate deletes exactly the material that makes the artifact worth keeping.

**Re-homing step 5's fields.** They are scoped to "the summary body and the operator report" — surfaces
that do not exist without a PR. `references/findings-report-format.md` § 6 carries them instead:
`OBSERVED:`/`INFERRED:` per statement, the named falsification test for any inference, and the anchor as
`file:symbol` **plus the quoted code**. If you find yourself writing an inference with a recommendation
and no falsification test, that field is missing, not optional.

## Step 4 — The verification pass (mandatory)

Work `references/finding-verification.md` against **every** finding. For each one, write the check
name, the command or read you performed, and its output. Then:

The reference splits its items into **Part A (tool-grounded)** and **Part B (judgment-only)**, and the
split governs what you may conclude:

| Check class and outcome | What happens |
|---|---|
| Part A confirms the mechanism | severity stands, confidence `CONFIRMED` |
| Part A contradicts it | downgrade or retract, **citing the output** |
| Part A could not be constructed or run | **severity unchanged**, confidence `PLAUSIBLE`, say why |
| Part B (any outcome) | **severity frozen**, confidence capped at `PLAUSIBLE` |

A Part B item may still be the most valuable thing you write — the source run's top finding came from
one. It may raise a concern, argue it, and anchor it. It may not settle it. Converting a Part B concern
into a Part A constructible trigger is the highest-value move available.

**Severity vocabulary — reuse, do not invent.** `Blocker` / `Major` / `Minor` / `Question`, as
`plan-critic/references/finding-format.md` defines them (Blocker = data loss, security, system failure;
Major = significant instability or design flaw; Minor = suboptimal, not dangerous; Question = missing
clarity that blocks progress). **Vocabulary only** — that file's required actions target a plan
document, not a code review; the actions are defined here.

File an uncertainty as `Question`, never as a weak defect. Mapping from the older
Critical/High/Medium/Low/Note scale used by the five predecessor reports, and the fact that
`Medium → Major` *tightens* the gate: `references/findings-report-format.md` § 5.

Confidence is a *separate* axis: `CONFIRMED` / `PLAUSIBLE`, matching the `ReportFindings` tool's
`verdict` field. Keeping "is it real" apart from "how bad" is what stops severity inflation from
absorbing uncertainty.

Blocker and Major must be resolved before any "complete" claim; only the operator may accept one.

## Step 5 — Re-verify every anchor at write time

Immediately before writing, re-resolve each finding's anchor **by symbol** (`grep -n "<symbol>"`),
never by a line number recalled from an earlier read. Then re-run step 1's snapshot.

This is not ceremony. In the run this skill generalises from, five commits landed mid-review: one
finding escalated to the top severity because a peer commit removed the mitigation it relied on, and
another was partly closed because its dead code had been deleted. Both changes came from
re-resolution, not reconsideration — which is exactly the allowed kind of severity change.

## Step 6 — Write the report

To `tasks/TECH-<slug>-review.md`, following `references/findings-report-format.md`. Required whether or
not you found anything: base and HEAD SHAs, the input used, gates run **with exit codes and scope**,
an explicit "not run" line for gates that did not run, a "not reviewed" section, and a corrections log.

**"Found nothing" is a complete result** — an empty findings table with populated coverage and
not-reviewed sections is a finished review, not a failed one.

## Step 7 — Close out

1. **Report the doc's tracking status.** `git ls-files --error-unmatch <path>` — two of the five
   predecessor review docs in `tasks/` have zero commits, so an untracked report is the normal
   failure. Name the commit as the operator's action; do not commit unasked.
2. **Redaction.** `tasks/` is tracked and pushed, so the report enters git history permanently. Cite
   `file:symbol` and describe shapes — never paste credentials, tokens, account identifiers, emails,
   or raw log payloads. Assume pushed branches may already expose such identifiers in their history.
3. **Routing handoff, only if an orchestration context exists** — the operator says so, a
   `.specs/*/plan.md` names the initiative, or a recent orchestration file sits in `.ai/handoffs/`.
   Otherwise **state that it was skipped**. Count what is already there before adding to it
   (`ls .ai/handoffs/*.md | wc -l`); one more unread brief is the failure mode, not the safe
   default. If written, check it with `lemmi-ai-kit lint handoffs`, attributing findings **by
   filename** — the target lints every handoff, not only yours.

## Example — the verification line, wrong and right

**Wrong** (a re-rating; unfalsifiable, and the banned operation):

```
F8 — downgraded to Minor (on reflection, less likely than I first thought).
```

**Right** (a check, its output, and the consequence):

```
F8 — Minor. CHECK: construct the trigger. Requires _record_failure to raise;
grep -n "_record_failure" <file> shows only a logger.warning and a counter
increment, neither of which raises. Reachability UNKNOWN, not demonstrated.
confidence=PLAUSIBLE.
```

The second is reproducible by the next reader. The first asks them to trust a mood.

## Additional resources

- `references/finding-verification.md` — the per-finding checklist, its provenance, and its blind spot
- `references/findings-report-format.md` — required report sections, with a worked header
- `pr-review-concise` steps 5 and 7 · `parallel-session-safety` §§ 6–7 ·
  `plan-critic/references/finding-format.md`
