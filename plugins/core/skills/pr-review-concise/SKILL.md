---
name: pr-review-concise
description: >
  Adversarially review a pull request and produce inline comments under an enforced length budget —
  two sentences, defect then mechanism then fix, 300 characters target. Long-form reasoning goes to
  the operator report, never on the diff line. Posts only findings that would change a merge decision
  or a production outcome; "found nothing" is a valid result. Use when the user says "review this
  PR", "review the stack", "PR review", or asks for review comments to post on GitHub.
when_to_use: >
  "review this PR", "review the stack", "PR review", "leave review comments", "review PR #N",
  or reviewing a stacked chain before merge.
metadata:
  type: review
---

# PR Review (Concise) — findings that fit on a diff line

## When this skill activates

- Reviewing a pull request or a stacked chain whose comments will be **posted for another human**
- Re-reviewing a PR after a push (read the existing threads first — see step 7)

**This is not `post-task-review`.** That skill reviews your own working tree, in-session, writing to
the operator with no length budget. This one reviews a *diff on a remote PR* and writes to *a third
party's screen*, where attention is the scarce resource. Inheriting post-task-review's prose style is
exactly what caused the failure below. For your own uncommitted diff, use `post-task-review` or the
built-in `/code-review`.

**Versus the built-in `/review`.** That command reviews a GitHub PR too, and answers the same request
— but with no length budget, no lane-based depth allocation, and no false-positive list for this
codebase. Use this skill for any PR in this repo; `/review` is the fallback elsewhere.

**Not `context: fork`,** deliberately: posting is an outward action that needs an operator approval
loop in the main session (step 8). Finding-generation is read-only by instruction — do not edit files
while reviewing.

## Why this exists

Measured over 21 inline comments on one real stack:

| author | n | min | median | max |
|---|---|---|---|---|
| external human reviewer | 14 | 134 | **176** | 196 |
| our AI review session | 7 | 2,128 | **2,359** | 2,870 |

**13.4× the human's median.** The AI comments were *correct* — they found real defects, including one
that could destroy candidate data. They were essays in the wrong container.

**The cause was the prompt, and it is instructive:** it demanded "why it matters and what it can
break", and the session complied by writing three labelled paragraphs per comment. It was not being
verbose by accident; it was being obedient. So this skill specifies the **shape**, not a word budget
bolted onto the same template.

That prompt also over-read its source. Google's review guidance makes explaining *conditional* —
"You don't always need to include this information in your review comments" — and explicitly
disclaims fix-design: "In general it is the developer's responsibility to fix a CL, not the
reviewer's." So name the *direction* of a fix in one clause; do not design it.

**A length cap alone would not have worked** — it compresses the same three paragraphs rather than
restructuring them. *(Inferred, not measured. The nearest evidence is a vendor's report that
prompting for fewer nits also cost them critical comments — a volume/precision trade-off, not a
measurement of caps.)*

## Step 1 — Two posted surfaces, two budgets (read this before anything else)

A GitHub review has **two** places to write — plus the operator report, which is never posted.
Confusing them is what produced the failure:

| Surface | Budget | Carries |
|---|---|---|
| **Inline comment** (anchored to a diff line) | **≤300 chars target, ~500 hard max** | defect, mechanism, fix — nothing else |
| **Review summary body** (one per review) | **unbudgeted** | coverage + depth variance, evidence (`OBSERVED:` / `INFERRED:` / `UNKNOWN:`), falsification tests, severity table, non-blocking observations |
| Operator report (not posted) | unbudgeted | everything above plus rejected findings and reasoning |

**Every field this skill asks you to produce that is not defect/mechanism/fix belongs to the summary
body or the operator report.** GitHub already anchors an inline comment to its `file:line`, so
re-quoting the code there is pure budget spend. If you find yourself adding a label, a quote block or
an evidence tag to an inline comment, it goes in the summary instead.

## Step 2 — The output shape (this is the skill)

Every inline comment is one line of grammar, borrowed from Conventional Comments:

```
<label> (<decoration>): <defect>, so <mechanism>. <fix>.
```

- **Labels you may post:** `issue`, `todo`, `question`. Nothing else reaches the PR.
- **Labels that never reach the PR:** `praise`, `nitpick`, `thought`, `chore`, `note`, `suggestion` —
  these go in the operator report. The linter already owns formatting and style.
- **Decorations:** `(blocking)` or `(non-blocking)`.
- **Discussion field: always empty on a posted comment.** Conventional Comments makes discussion
  syntactically separate and optional; the measured failure is precisely a comment where discussion
  ate the body. There is no "important enough" exception — that judgment is what produced the
  2,359-char median. A finding that needs discussion puts it in the summary body.
- **`todo` survives the step-3 gate only when the trivial change is itself a merge blocker** (a stray
  debug print shipping to production). Otherwise it is report material.
- **`<fix>` names the DIRECTION in one clause — it does not design the fix.** "Resolve SHAs", "move
  the entry into this PR". Google is explicit that fixing the CL is the developer's job, not the
  reviewer's; a designed fix is also the fastest way back to 2,400 characters.

**Budget: ≤300 characters target, ~500 hard maximum, including the label.**

> Provenance, stated honestly: **no authoritative norm for review-comment length exists.** The
> 176-char baseline is n=14, one reviewer, one stack. This budget is *this project's chosen budget
> derived from one local measurement* — not an industry standard. Say so if challenged.

**Three beats, two sentences: defect → mechanism → fix.** Not three headed sections. The human
baseline, annotated:

> "This only validates string shape, so nonexistent `deadbee` / `does/not/exist` anchors pass.
> Resolve SHAs, refs …"

defect (*validates shape only*) → mechanism (*bad anchors pass*) → fix (*resolve SHAs*). One sentence
plus a fragment. **The full comment measured 176 characters — the excerpt above is elided**, so do
not calibrate against the visible string's length.

**Self-test before you write anything:** *would my wording here produce 176 characters, or 2,400?* If
what you are about to write has more than one heading, more than two sentences, or a newline, it
produces 2,400.

## Step 3 — The posting gate

**Post only if the finding would change a merge decision or a production outcome.** Everything else
is operator-report material.

The reframe that makes this concrete — Tricorder (Google, ICSE 2015) defines an **effective false
positive** as "any report from the tool where a user chooses not to take action to resolve the
report… to a developer, a false positive is any report that they did not want to see."

**All seven of our AI comments were correct. Under this definition all seven were false positives.**
Correctness does not exempt a comment from the gate.

Tricorder's admission criteria, applied per finding — post only if all four hold:

1. The problem is obvious and actionable once pointed out, and the fix is clear.
2. You would be right at least ~90 % of the time on findings of this kind.
3. It has potential for significant impact.
4. The defect **class** is not endemic. If the pattern is everywhere in the codebase it is a
   convention question for the report, not N inline comments — post **once**, with the count ("same
   pattern at 3 other call sites"). *(Tricorder's own criterion is about analyzer-level frequency
   across a corpus — "if a warning occurs too frequently, it's likely that it's not causing any real
   problems." Applied per finding it must never suppress a repeated real defect.)*

**Volume is not evidence of a good review.** Usefulness density *falls* as a change grows (Microsoft
Research, MSR 2015, peer-reviewed: "as number of files in the change increases, the proportion of
comments that are useful drops"). One vendor measured its own pre-fix output as "~19 % were good, 2 %
were flat-out incorrect, and 79 % were nits" *(vendor self-report, not independent measurement)*.

## Step 4 — Depth by lane, not uniform

The migration once sat at position 17 of 20 and was "reviewed with the same attention as a board-row
edit". Allocate attention by what `stacked-pr-planner` assigned:

| Lane / class | Depth |
|---|---|
| `MIGRATION` | Deepest. Reversibility, data loss, lock behaviour, the down-path. Read every line. |
| `BACKEND` (Lane R) | Deep. Every changed line. |
| Executable prose (Lane R): `AGENTS.md`, `.claude/**`, `.cursor/**`, hooks, CI, prompts | Deep — it changes what every future session does and no test catches it. Check hook registration and rule contradictions. |
| `TOOLING` | Normal. |
| Lane C (docs riding with code) | Verify it matches the diff it documents. |
| Lane J (journal prose) | **Not on the review surface at all** — review skipped, risk accepted (this repo has no CODEOWNERS and no veto channel, so it is not Apache-style commit-then-review). If asked to review one anyway, skim and say so. |

**Record the variance on the PR, not just to the operator.** Varying depth is legitimate only if
stated: Google's default is "look at *every* line of code that you have been assigned to review",
with partial review sanctioned only when reviewers "note in a comment which parts you reviewed." That
note must be where the author and other reviewers see it — **post the step-6 coverage block as the
review summary body.** An operator-only coverage statement tells the one person who already knows.

## Step 5 — Evidence discipline: OBSERVED vs INFERRED

An inference was once stated as fact — "`gh stack` requires the `read:org` scope" — from having only
seen `gh pr edit` fail that way. It was never tested, and the claim had already been used to argue
against a course of action before the operator falsified it.

**There is no established convention for this in automated review. This skill invents a small one and
says so.** (Nearest prior art: SARIF's `kind: review|open` for "a human must decide"; Conventional
Comments' `question` for "a potential concern but not quite sure".)

> **All of the fields below live in the summary body and the operator report — never in an inline
> comment.** They are the reason step 1 exists: an obedient session that reads "every finding carries
> an anchor plus the quoted code" and puts it on the diff line cannot fit in 300 characters, and will
> comply anyway. That is the exact mechanism that produced the 2,359-char median.

- Every finding carries an **anchor**: `file:line` plus the quoted code it rests on. Re-grep the
  symbol at write time — never cite a line number recalled from a Read.
- **A finding with no quotable anchor is not an `issue`.** Downgrade it to `question` or drop it.
- Write `OBSERVED:` for what you ran and saw, `INFERRED:` for what follows from it. An inference
  never carries a recommendation without a test that would falsify it — name the test.
- If a check is blocked by a missing tool or credential, report **UNKNOWN** and name what would
  retrieve the fact. Do not substitute a proxy's output.
- **Sweep by CLASS, not by instance.** Once you have one instance of a defect, search for its
  *category* across the diff — not for the string you already found. A redaction verified with the
  pattern of its one known instance missed two more of the same class. This is also what turns a
  single finding into "same pattern at N other call sites", which step 3 requires instead of N
  separate comments.

**Severity is the LAST field of each finding's report row, emitted in the same pass. Never run a
second-pass LLM judge over your own comments** — a vendor that tried it reported "the LLMs judgment of its own output
was nearly random." *(That the last-field placement helps is an inference from two sources, not a
tested claim in this repo. Falsification test: compare address rates over the next stack.)*

## Step 6 — The summary body (every review posts one)

**Every review posts a summary body — with findings or without.** It is the unbudgeted surface from
step 1, and it is where everything evicted from the diff line lands. Without it, step 5's evidence
has nowhere to go and the agent will improvise it back onto the comment.

```markdown
## Review: <PR> — <n> blocking, <n> non-blocking

**Coverage:** <files/layers read> at <depth per lane>; skimmed <what> because <lane J / generated / vendored>.
**Checked for:** <the specific defect classes you hunted — not "bugs">.
**Not checked:** <what you could not verify, and what would settle it — UNKNOWN, plus what retrieves the fact>.

### Findings
| # | file:line | anchor (quoted code) | OBSERVED / INFERRED | falsification test (inferred only) | severity |
|---|---|---|---|---|---|
| 1 | … | `…` | OBSERVED: ran X, saw Y | — | high |

**Non-blocking (deliberately not posted inline):** <n items, one line each>.
```

Severity is the **last column**, written in the same pass — never a second judging pass.

**"Found nothing" is a first-class result.** An adversarial reviewer that returns nothing looks like
it did not try, and that pressure is what manufactures findings. Post the same block with
`— 0 blocking, <n> non-blocking`, an empty Findings table, and the coverage lines filled in. **A
review that posts no inline comments and states its coverage is a complete review**, not a failed one.

## Step 7 — Known false positives in this codebase

Do not flag these. Each has cost a real round-trip.

| # | Pattern | Why it is not a defect |
|---|---|---|
| 1 | Gate output quoted from the PR body | A gate's verdict is its log, never its exit code — the Docker runner returned exit 0 around `1 failed, 2260 passed`. Never accept "gates green". |
| 2 | `ruff` violations under a broader scope | `ruff check backend tests` exits 1 on ~35 pre-existing violations; `ruff check backend` is the canonical gate and exits 0. Name the scope. |
| 3 | Type errors in `scripts/` | `pyproject.toml` scopes basedpyright to `include = ["backend", "tests"]` — `scripts/` was never in gate scope. |
| 4 | "This prompt file is missing from the repo" | `prompts/**` are deployment artifacts (untracked; runtime reads GCS). `git ls-files prompts` is empty by design. |
| 5 | Any `patch()` in a test | Only patching a **concrete external client class** violates the DI rule. `patch()` on a non-client internal at the import site is allowed. |
| 6 | Enum form (`StrEnum` vs `class X(str, Enum)`) | **The sources contradict each other.** AGENTS.md bans `StrEnum` under its `## Do not` heading, while another AGENTS.md bullet calls `str, Enum` "the deliberate convention" and the installed language-conventions skill may show a conflicting example. Measured in `backend/`: **79 `StrEnum` to 2 legacy**. Check the file; surface the contradiction to the operator rather than picking a side. |
| 7 | `.value` on an enum member | **Required** for the legacy `class X(str, Enum)` form (2 survive: `CandidateLiteralKey`, `TranscriptActionType`). It is banned only at AI-parse boundaries (use `str(field)` — AI may return raw strings that bypass Pydantic coercion) and in models with `use_enum_values=True`. **Read the enum's base class before flagging.** |

**True positives that look like these:**

- **Bare `@fast_test` / `@integration_test` / `@websocket_test` without parentheses — ALWAYS flag.**
  These are decorator *factories*, so the bare form rebinds the test to the inner `decorator(func)`.
  **The consequence depends on the shape, and the common shape is the silent one:**
  - On a **test method** (the dominant form here — tests inherit `BaseEndpointTest`/`BaseCRUDTest`):
    `self` binds to `func`, `decorator` returns `sync_wrapper`, and pytest **records a PASS with the
    assertions never executed.** The only signal is a `PytestReturnNotNoneWarning` buried under a
    green summary. One real 27-test class ran this way: exit 0, "27 passed", zero assertions.
  - On a **module-level test function**: pytest requests `func` as a fixture and the test **ERRORS**
    at setup — loud, and the suite catches it.

  *Both verified 2026-08-04 by running the two shapes against `tests/utils/timeout_decorator.py`:
  `1 passed, 1 warning, 1 error`. Never assume the loud case — grep the diff for bare
  `@fast_test$`/`@integration_test$`/`@websocket_test$` at end of line, and treat `N passed` on a new
  test class as unproven until the warning block is checked.*
- A repository query or partial unique index missing `deleted_at.is_(None)`.
- A cached/existing-data fast path that skips the ownership check the generation path enforces.

**Meta-rule, learned the hard way while building this list: a rules file is a claim.** Re-grep the
tree before flagging a convention violation.

**Before posting on a re-review, read the existing threads.** Duplicate comments across re-reviews
are an unsolved problem in shipped products — GitHub's own docs say Copilot "may repeat the same
comments again, even if they have been dismissed." Do not reproduce it.

## Step 8 — Posting is an outward action, separately authorized

Generate findings → **show the operator every comment body with its character count** → post only on
approval.

```markdown
| # | file:line | comment (verbatim) | chars | shape ok | severity |
|---|---|---|---|---|---|
| 1 | backend/…/x.py:42 | issue (blocking): … | 214 | yes | high |

median: 214 chars · max: 287 · human baseline: 176 · over 500: 0
```

`shape ok` is three mechanical checks: **no newline, no `**`, ≤500 characters.** A row failing any of
them is rewritten, not posted.

*Sentence count is deliberately NOT in the mechanical set.* Counting periods misfires on the very
comments this skill wants — its own showcase example contains three (`inert.`, `settings.json`,
`PR.`), only two of which end a sentence. Judge two-sentence shape by reading it; automate only what
cannot be wrong.

**The posting mechanism matters, because the obvious one destroys the anchoring.** Inline comments
must be posted as a *review* with a `comments[]` array — pasting approved comments as one general
comment throws away the `file:line` anchor the whole shape depends on:

```bash
gh api repos/{owner}/{repo}/pulls/{n}/reviews --input review.json
# review.json: { "event": "COMMENT",
#                "body": "<the step-6 coverage block — the summary body>",
#                "comments": [ {"path": "...", "line": 42, "body": "issue (blocking): ..."} ] }
```

One call posts the summary body and every inline comment atomically. `gh pr comment` is **not** a
substitute — it cannot anchor to a line.

**Authorization is scoped to the action it was granted for.** A one-time "go ahead" does not carry to
the next PR, the next push, or a second review pass — it once became ~15 commits and 12 pushes across
two days, none re-authorized. Re-ask when the scope changes.

**Route a comment to the PR that OWNS the code** (`.ai/git-stacked-pr-workflow.md`), not to whatever
PR is open. Fixing it is `pr-comment-resolver`'s job — never collect fixes into a new top PR.

**Do not claim a verdict you cannot hold.** Leave comments; approving or requesting changes on the
operator's behalf is theirs.

**Self-check, mandatory:** report your own median and max comment length next to the 176-char
baseline. A skill about comment length that does not measure its own output is self-refuting.

## Worked example — a real finding from this stack, rewritten

**The finding (real, and it survived to be verified):** `.claude/settings.json` is absent at the tip
of the lower PR and present in the one stacked above it, so merging the lower PR alone ships the
`cd`-guard hook still unregistered — the reviewer's original finding, unfixed.

**Before — the measured shape.** *(Reconstruction of the three-labelled-paragraph template at the
measured length; not a verbatim quote of the stored comment.)*

> **What this is:** The `deny-cd-prefix.py` hook has been added to `.claude/hooks/` in this PR, and
> it implements a `PreToolUse` deny for Bash commands whose leading token is `cd` into an absolute or
> home-anchored path…
>
> **Why it matters:** The 2026-08-01 retrospective counted 577 such prefixes across 12 sessions, and
> 298 of them in the single session that started after the prose rule was added. The rule was already
> stated in AGENTS.md and in `.cursor/rules/code-quality.md` and carried as a standing user
> preference, and none of it moved the number, which is the entire reason the enforcement was
> escalated from prose to a hook in the first place…
>
> **What it can break:** Because hook registration lives in `.claude/settings.local.json` rather than
> travelling with the hook file, a merge of this PR in isolation produces a tree where the hook
> script exists but nothing invokes it. Every reader of the diff will reasonably conclude the
> enforcement is live…
>
> *(the stored comment measured ~2,400 characters; elided here — three headings, each a paragraph.)*

**After — same finding, this skill's shape:**

> `issue (blocking): The hook file lands here but its registration is in the PR above, so merging
> this PR alone ships the cd-guard inert. Move the settings.json hook entry into this PR.`


**182 characters** (164 without the label) — within six characters of the human's 176 baseline, in
exactly two sentences. Defect (*registration is not in this PR*), so mechanism (*merging alone ships it inert*).
Fix (*move the entry here*).

Everything cut — the 577/298 counts, the retrospective history, the prose-vs-hook argument — is
*true* and belongs in the summary body or the operator report. Google's advice to CL authors applies
symmetrically to reviewers: "Writing a response in the code review tool doesn't help future code
readers, but clarifying your code or adding code comments does help them"
(eng-practices, `review/developer/handling-comments.md`). If it is durable knowledge it belongs in the
code, the spec, or the report; if it is not, it belongs nowhere.

## Anti-patterns

| Anti-pattern | Why it seems right | What actually happens |
|---|---|---|
| Three labelled paragraphs per comment | It is more informative, and the prompt asked for it | 2,359-char median against a 176 baseline |
| "Just be concise" bolted onto the same template | It is the obvious fix | Compresses; does not restructure (inferred — the nearest evidence is a vendor failing to prompt away nits without losing critical comments) |
| A second LLM pass to rate severity and filter | The obvious architecture | Documented dead end — self-judgment was "nearly random" |
| Post everything you found | Suppressing a finding feels like hiding a defect | Nits drown the signal; a correct-but-unwanted comment is a false positive |
| Return findings because returning none looks lazy | An adversarial reviewer should find things | Manufactured findings; an untested inference shipped into a recommendation |
| Uniform depth across the stack | Every PR deserves care | The migration gets board-row attention |
| Accept "gates green" from the PR body | The author ran them | Exit 0 around `1 failed, 2260 passed` |
| Re-post on re-review | The finding is still open | Duplicate threads; unsolved even in shipped tools |

## Cross-cutting rules

Secrets, durable-vs-ephemeral artifacts, authorization scope, branch hygiene, own-hunks staging, and
gate-verdict discipline are shared across the stacked-PR skills — see
[stacked-pr-planner](../stacked-pr-planner/SKILL.md) § Cross-cutting rules. Reviewing a shared
checkout: `parallel-session-safety` (a suite verdict over a tree other sessions are editing is void).

## Related

- `stacked-pr-planner` — assigns the lane that sets review depth
- `pr-comment-resolver` — fixes comments in the owning layer. **Replies do NOT use this budget** —
  they are receipts, not findings, and carry a tighter one (≤120 chars for a fix, no markdown):
  see its Step 6. Measured: 21 of 24 comments we posted on the 435→461 stack were replies, at a
  2,424-char median, because that surface had no spec of its own
- `post-task-review` — your own tree, in-session, no length budget
- `branch-diff-review` — committed branch vs a base, **no PR**, output is a durable
  `tasks/TECH-*-review.md`. It inherits steps 4–7 and declines steps 2–3 (a durable doc has no
  per-finding attention budget). **It also runs a second pass over its own findings, which step 5
  above appears to forbid** — the reconciliation is in its SKILL.md: this step's ban targets
  *re-rating* severity from judgment, which stays banned; its pass permits a severity change only as
  the mechanical consequence of a recorded command output, and freezes severity for judgment-only
  checks. Read that before concluding the approach is banned outright
- `plan-critic` — the Blocker/Major/Minor vocabulary for internal reviews
