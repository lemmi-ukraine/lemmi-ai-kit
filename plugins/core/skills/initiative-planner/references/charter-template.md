# Charter template — the level-1 document

The document that must exist **before** an initiative is decomposed. It states what is believed,
what it is worth, and what would prove it wrong.

**Two shapes, one per initiative — never both.** Pick by what a *rejection* would argue about:

| | **PDR** — product requirements | **ADR** — architecture decision |
|---|---|---|
| Rejection argues about | what users get, whether it is worth building | how the system is built, whether the trade is right |
| Lands in | `tasks/FEATURE-{slug}.md` | `tasks/TECH-{slug}.md` |
| Authored by | **`/product-brief`**, then add §A below | this template, §A + §C |

**Neither goes in `.specs/`.** That is level 2 (decomposition) and level 3 (slices). A charter that
lands inside a spec directory stops being findable as the initiative's own document.

**The bar for both shapes** is `/product-brief`'s Dimension 1 (Problem Strength): *falsifiable,
arguable, carrying at least one concrete number*. If a reasonable colleague could not disagree with
the Goal section, it is not yet a goal.

---

## §A — Shared charter block (BOTH shapes, none optional)

`/product-brief` does **not** emit three of these — its template is Problem · Behavior · UX Content ·
Out of Scope · Implementation Notes. On the PDR path, run that skill first, then append this block.

```markdown
## Goal

{What is true for a USER when this is done. Two sentences. Not what gets built.}

## Hypothesis

{The causal claim: because <mechanism>, changing <X> moves <metric> <direction> by <amount>.
State the metric's current value, its source, and the window it was measured over.}

## Expected value

{Who benefits · how many · how often. One number with its source and window.
If unknown, write UNKNOWN and name what would retrieve it — do not estimate.}

## Falsifiers

| Falsifier | How it gets measured | Verdict if it holds |
|---|---|---|
| {claim that would kill or redirect this} | {the deliverable that measures it} | {close · narrow to lane X · re-file against BACKLOG-Y} |

## Definition of done

1. {Checkable. Numeric targets may be deferred to a named gate — say which.}
2. {No-regression clause: what must NOT get worse, and the budget.}

## Minimal viable initiative

{The smallest subset that plausibly moves the metric, named as deliverables.
A legitimate stopping point, not a degraded one.}

## Non-goals

{What this deliberately excludes, and why. An empty section is a failure.}

## Open questions

{Each names its gate and its decider.}
```

## §B — PDR-only

Owned by `/product-brief` — Problem · Behavior · **UX Content** · Out of Scope · Implementation
Notes, plus its mandatory 2–3 assumption challenges. Do not re-author those sections here; run the
skill and append §A.

## §C — ADR-only

```markdown
**Type:** Architecture decision   **Status:** proposed | accepted at Gate {X} | superseded by {doc}

## Context — the forces

{What in the system makes a decision necessary NOW. Coupling, a failure class, a cost curve, a
constraint that blocks something else. Name the code: symbols, not line numbers.}

## Decision

{The architectural choice, stated in one paragraph, in the active voice.}

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| {the obvious one} | {the specific reason, not "worse"} |
| {do nothing} | {always list this one} |

## Consequences — split by reversibility

**Easier after this:** {…}
**Harder after this:** {…}
**Hard to undo (one-way doors):** {migrations, published contracts, deployed artifacts with no
review surface, anything with data loss on rollback}
```

> **The one-way-doors list is load-bearing, not decoration.** Irreversibility is the first
> discriminator in `SKILL.md` step 5's tier table, so an ADR that names its one-way doors has
> already routed its own riskiest sessions to `judgment` tier. An ADR with no rejected alternative
> was not a decision; an ADR with no one-way doors is either trivial or has not been thought through.

---

## Structure description — what each field is for

### Goal
User-observable outcome. **"Ship the typed contract" is not a goal; "candidates get feedback pitched
at their level" is.** If the sentence survives unchanged after the implementation approach changes
entirely, it is a goal. This holds for an ADR too — a technical initiative still ends at a user.

### Hypothesis
The **causal** claim, and the only field that can be wrong in an interesting way. Three parts, all
required: mechanism, the metric, the predicted direction and size. Without a current value there is
nothing to compare against later, and the initiative can never be evaluated — only declared done.

> **Weak:** "Improving criteria coverage will make feedback better."
> **Strong:** "Because seniority resolves to `middle` for 100% of candidates (measured in prod,
> 2026-08 window, n=54), seniors are graded on middle criteria; restoring the signal should move the
> seniority distribution off 100% `middle` and raise the substance rate on technical questions."

An ADR's hypothesis is usually about a **cost or a failure rate**, not a product metric: "because
every read path re-fetches the resume, p95 grows with question count; caching at the request scope
should flatten it." Same three parts.

### Expected value
Who, how many, how often — with a source. **UNKNOWN is a legitimate value** when paired with what
would retrieve it (the API, the query, the credential, the person). An estimate written where a
measurement belongs becomes load-bearing in later documents and nobody re-checks it.

Read the volume honestly in both directions. A lane covering 12.7% of rows but 37.6% of sessions is
neither the majority case nor a niche, and writing only the flattering number decides scope by
omission.

### Falsifiers
**The first deliverable should be able to kill the initiative.** Each falsifier names the deliverable
that measures it and the verdict it forces — including "re-file this against another backlog", which
is a success for the process even though it reads like a failure.

A falsifier nobody has scheduled a measurement for is a disclaimer, not a falsifier.

### Definition of done
Checkable statements. Numeric targets may be set later **at a named gate** from a baseline rather
than guessed now — say which gate. Always include the no-regression clause: an initiative that
improves its target metric while degrading a neighbouring one has not succeeded, and without a
recorded budget nobody will notice.

### Minimal viable initiative
Present it so the operator chooses **UP** from the smallest scope rather than **DOWN** from the
elaborate one. Name the elective deliverables explicitly so a gate approves them rather than
inheriting them.

### Non-goals
Every initiative has boundaries. The useful ones are the boundaries someone **will** try to cross
during implementation. If a non-goal conflicts with the chosen build order, say so here rather than
letting the conflict surface as a surprise at a gate — that is a decision for the operator, not for
whoever notices first.

### Alternatives considered (ADR)
"Do nothing" is always an alternative and always listed. A rejection reason must be specific enough
that someone could argue with it — "worse performance" is not a reason, "adds a second round-trip on
every question, and questions are the hot path at ~1,500/month" is.

### Consequences (ADR)
The **Harder after this** column is the one people skip, and it is where the honest cost lives. The
**one-way doors** list feeds step 5's tier routing and step 7's gate design — anything on it should
have an operator gate in front of it.

---

## Aging — charters are claims, not facts

A charter older than **~1 week** is re-verified before anything is planned on it:

- Re-anchor every claim **by symbol** (`grep -n` the symbol now) — never by a line number the
  document recorded. Anchors drift even when quotes are perfect.
- Re-measure every frequency claim against fresh data and **state the window**.
- Record which conclusions were **falsified**, so the next reader does not re-trust them.

Docs age in a specific direction: severity inflates (written at peak alarm, never re-measured) while
mechanism claims go stale under refactors. One audit of a doc in this state found **4 load-bearing
conclusions false**, including a prescribed fix that crashes on a unique constraint — and measuring
inverted the priority rather than confirming it.
