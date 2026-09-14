---
name: metric-validity-check
description: >
  Test whether a metric, score, harness or judge actually tracks a user-visible outcome, before
  anyone uses its number to make a decision. Joins the outcome label to the artifact that produced
  it (including when there is no foreign key), reports the linkage diagnostics that decide whether
  the joined set is representative, then runs a known-groups test of every metric against the
  label's extremes. Returns one of four verdicts — SEPARATES, DOES NOT SEPARATE, UNDERPOWERED,
  SUSPECT — and states what each one licenses you to claim.
when_to_use: >
  "does this metric actually measure anything", "our dashboard looks fine but users complain", "is
  the harness predictive", "validate this metric", "does the score track satisfaction", "join the
  ratings to the sessions", "we have no foreign key between the survey and the run". NOT for scoring
  a corpus against a rubric (a judge-based audit is a different instrument), and NOT for checking
  that a checker can see at all (`probe_checker.py` in `post-task-review`).
argument-hint: "<metric or harness> <outcome label source>"
allowed-tools: Read, Grep, Glob, Bash, Write
metadata:
  type: task
  author: extracted from one five-day metric-validity audit of a single product. Every number
    below is a measurement from that audit; re-measure against your own corpus rather than
    inheriting it.
---

# Metric Validity Check — does this number track anything a user felt?

ultrathink

> *"Until the evidence is in, he has no justification for employing the test as a basis for
> terminal decisions."* — Cronbach & Meehl, *Construct Validity in Psychological Tests*, 1955

A metric that has never been tested against a user-visible outcome is not a weak signal. It is an
**unknown** signal, and steering by it is indistinguishable from steering by noise until you check.

Skipping the check has cost one product team months. A behavioural harness with 119 self-tests was
the declared validation instrument for every fix in a program; when it was finally tested against
user ratings it separated the arms on **1 of the 9 metrics in its comparison output** (n=24 rated 1-2
star vs n=97 rated 4-5 star), and that one measured how much the *user* talked, not what the system
did. Two metrics pointed the wrong way.

> Note the denominator, because this skill's Phase B3 exists because of it: that harness **emits 12
> metric keys**, its methodology reference **names 8**, and its **comparison summary carries 9**.
> Nine is right *for the surface that was compared*. Say which surface you counted, every time.

**Evidence base: n=1.** This method comes from one five-day audit of one product. In that case the
check took about an afternoon; whether that generalises is unknown. Steps marked **[n=1]** are that
audit's choices, not requirements — and a skill that asserted its own effectiveness without evidence
would fail its own test.

This skill is the check. It is deliberately small and standalone so it gets run.

## What this is not

| Not this | Because |
| --- | --- |
| `probe_checker.py` (post-task-review) | That certifies **sight** — can the checker see a positive, does it over-match a negative. Two fixtures. It cannot tell you whether what the checker sees *matters*. Run both: sight first, validity second. |
| A rubric-judge corpus audit | Measures a corpus against a rubric with parallel judges. Its golden-set re-judge compares the judge to **its own frozen verdicts** — that is stability, not validity. |
| A/B test analysis | You are not testing a change. You are testing the **ruler**. |
| Model eval accuracy | Accuracy against labels *you* wrote measures well-formedness. This measures whether the construct tracks a real user reaction. |

## When this check is the wrong shape

Skip it, and say you skipped it, when:

- **The metric never claimed to predict this outcome, and nobody uses it as though it did.** A
  latency SLO is not a satisfaction proxy and was never sold as one. The check earns its cost only
  where a number is *actually steering decisions* about user experience. Ask: has anyone cited this
  metric in a prioritisation argument? If no, leave it alone.
- **No user-visible outcome exists yet.** Then the deliverable is instrumenting one, not this.
- **You have an experiment history instead.** With ~20+ shipped changes whose user impact you already
  know, a *validation corpus* is stronger than a known-groups check — see Phase C.

It is *not* excused by "the metric is obviously reasonable". Face validity is the thing this check
exists to distrust.

## Phase A — Name the outcome label, and build the label-blind list

An outcome label is something **a user did or said** that you did not derive from the system's own
behaviour: a survey rating, a thumbs-up, a churn event, a refund, a completed purchase, a support
ticket, a re-run.

Write down, before touching data:

1. **The label** and its exact question wording or event definition.
2. **Who is in it** — self-selected responders? all users? one plan tier? A survey answered by 20%
   of users is a label about *those* users.
3. **What the label structurally cannot perceive — the `label-blind list`.** This is the important
   one; Phase D gates on it. A user who cannot evaluate the thing being measured will rate it fine.
   Write the list now, before you see any result, so it cannot be written to fit one.

> **[n=1] A label-blind defect, found the hard way.** A defect class ran at ~11% of units and the rate
> was **flat across every rating band** (10% in the worst, 12% in the best). The reason: a
> knowledgeable user handles the defective unit fine and rates the session top marks, so the survey
> cannot see it. Flatness was the *finding*, not a refutation — and the fix needed a non-rating
> instrument to measure it.

## Phase B — Join the label to the artifact

### B1. Is there a foreign key?

If yes, join on it, report the match rate, and skip to B3. Most of the time there is not: the
analytics event and the application record live in different systems.

### B2. No foreign key — the nearest-match join

The strategy that works when the label fires shortly after the artifact: within each user, match
each label event to the artifact with the smallest positive time gap.

This is **record linkage**, it has a century of literature and a known failure mode: linkage error
is rarely random, so the successfully-joined set can be a biased sample of the population. That is
not hypothetical — in the source audit a headline collapsed from 1.6 to 0.41 because the field it
rested on was missing more often in one arm, and the finding had to be retracted.

**Report all seven diagnostics. Every one. A join without them is not evidence.**

| # | Diagnostic | Why it decides something |
| --- | --- | --- |
| 1 | Match rate, **both directions** — labels matched / labels total, and artifacts matched / artifacts total | An asymmetric rate means one side has duplicates or a window problem |
| 2 | **Full gap distribution** — median, max, and the shape of the tail. Never a mean alone | The tail is where the false matches live |
| 3 | **Multi-candidate count** and the tie rule you applied, stated | "Nearest" is undefined when two artifacts tie |
| 4 | **Unmatched counts on both sides**, with a spot-read of why | Systematic unmatching is a finding about the product |
| 5 | **Linked vs unlinked comparison** on any covariate you have | If they differ, your labelled set is not the population and you must say so in every downstream claim |
| 6 | **Sensitivity across ≥3 window widths** | If the answer changes with the window, the window is doing the work |
| 7 | **Coverage per arm**, never overall | A covariate available 40% of the time overall but 23% of the time in the bad arm will invert your conclusion |

**The trap that costs the most:** when the matching variable correlates with the outcome, window
width is an **effect modifier, not a tuning knob**. Widening the window until the numbers look right
is p-hacking with extra steps. Pick the window from the product's timing, state it, then report the
sensitivity.

Detail and the full diagnostic write-up format:
[references/join-diagnostics.md](references/join-diagnostics.md).

### B3. Name the denominator, permanently

Populations drift during an audit — one gets de-duplicated, one gets filtered, one is the pre-join
count. Three different numbers all called "rated sessions" is the normal outcome, and it produced a
correction twice inside one session of the source audit.

**Rule: every number you write carries its denominator inline.** `5 of 23`, never `22%`. `11% of
questions (n=100 sampled)`, never `11%`.

## Phase C — The known-groups test

The cheapest form of criterion validity, and the one that needs no experiment history: if the metric
measures what you think, it must separate groups you already know differ.

> **The simplest possible instance**, and the one the technique is named for: Thurstone and Chave
> validated an attitude-toward-the-church scale by showing it scored church members differently from
> nonchurchgoers. Two groups you already know differ; one metric; does it tell them apart. That is
> the whole move — everything below is bookkeeping so the answer survives scrutiny.

1. **Take the label's extremes**, not its middle. Worst-rated vs best-rated. The middle band dilutes.
2. **Run every metric in the suite, not the one you expect to win.** The suite is what is being
   tested. Reporting only the metric that separated is the whole failure mode, restaged.
3. **Report direction, not only significance.** A metric that separates *backwards* is a stronger
   finding than one that does not separate at all — it means the number has been read upside-down in
   every review it appeared in.
4. **Report n per arm with every line.**
5. **Attribute a null honestly.** Deng & Shi's decomposition: a metric can fail to move because it is
   insensitive, or because *nothing in your data moved it*. More data fixes the first, never the
   second.

### The four verdicts

| Verdict | Condition | What it licenses |
| --- | --- | --- |
| **SEPARATES** | Moves with the label, in the right direction, at a stated n | You may use it as a decision metric **for this outcome**, and must say which outcome |
| **DOES NOT SEPARATE** | Flat or inconsistent across the extremes | You may **not** report movement in it as user impact. Go to Phase D before concluding anything about the system |
| **UNDERPOWERED** | Too few in an arm to tell | State the n you would need, and escalate rather than wait (below). An underpowered null is not a null |
| **SUSPECT** | Separates almost perfectly | Check for leakage before celebrating. Cronbach & Meehl: *"an item that correlates .95 with age in an elementary school sample would surely be suspect"* — near-perfect correspondence usually means the metric is reading the label, not the construct |

### When known-groups cannot settle it

Two stronger designs exist; both cost more, and both are named so you can ask for them:

| escalation | what it needs | what it buys |
| --- | --- | --- |
| **Validation corpus** | ~20+ past changes whose user impact you already know | tests the metric against many known-good/known-bad shipments instead of one contrast — the standard practice in online-experiment metric development |
| **Degradation experiment** | permission to deliberately harm a slice (add latency, downgrade a service) | tests *direction and sensitivity* directly. It harms real users, so it is a human call, never an analyst's |

The formal bar either one is reaching for is the **Prentice surrogacy criterion**: a surrogate is
only a valid stand-in if the treatment's effect on the true outcome is fully captured by its effect
on the surrogate. Almost nothing meets it. Naming it keeps "this metric correlates" from being
mistaken for "this metric can replace the outcome" — a correlate is not a surrogate.

## Phase D — The fork a null result creates, and the gate on it

**A metric that does not separate has two readings, and your data cannot distinguish them:**

1. The metric measures something that does not matter to users.
2. The metric measures something real that the **label cannot perceive**.

These lead to opposite actions — retire the metric, or keep it and stop using ratings to evaluate it.
The only thing that separates them is the **label-blind list** you wrote in **Phase A, before you saw
the result**.

> **Gate.** If a null lands on something on the Phase-A label-blind list, the verdict is
> `DOES NOT SEPARATE — label-blind`, and the metric survives with a stated non-rating instrument.
> If it does not, the verdict is `DOES NOT SEPARATE — no user signal`.
>
> Writing the label-blind list *after* seeing results is how this method becomes a defect-deletion
> machine. If you did not write it first, say so in the report and mark every null as UNRESOLVED
> rather than back-filling a justification.

## Phase E — Report

Keep it short; the table is the deliverable.

```markdown
# Metric validity — {metric suite} against {outcome label}

**Verdict: {n} of {N} metrics separate the extremes.**

## The label
{wording/definition} · {who is in it} · response rate {x of y}
Blind spots written before analysis: {list}

## The join
{FK | nearest-match, window W}. Match rate {a/b} labels, {c/d} artifacts.
Gap: median {m}, max {x}. Multi-candidate {k}, tie rule: {rule}.
Linked vs unlinked differ on: {covariates, or "no difference detectable on {list}"}
Window sensitivity: {W1: r1 · W2: r2 · W3: r3}
Coverage per arm: {low arm x% · high arm y%}

## Known-groups results
| metric | worst arm (n=) | best arm (n=) | direction | test | p | verdict |

## What this licenses
- Metrics usable as decision metrics for {outcome}: {list}
- Metrics that must NOT be reported as user impact: {list}
- Nulls attributable to label blindness (Phase A list): {list}
- Nulls with no user signal: {list}
```

## Non-negotiables

- **Never report a metric movement as user impact** unless that metric has a `SEPARATES` verdict
  against the outcome you are claiming impact on.
- **A null is a claim about the metric, not about the system.** Say "the harness cannot see this",
  not "this does not matter".
- **If every metric in a suite is the same instrument class** (all lexical, all latency-derived, all
  click-derived) and the suite fails as a whole, the finding is about the **class**, not the metrics.
  A property the class cannot represent is invisible to it in principle and no amount of new metrics
  in that class will help. Say so — it redirects the next month of work.
- **Do not carry an odds ratio out of a zero cell.** A zero makes it degenerate — 0 or infinite,
  depending on which cell is empty. Report the two counts instead.
- **A metric computed over the rows that EXIST cannot report a row that is ABSENT, so improving it
  is not evidence of improved coverage.** A reciprocity score grades existing links, so a seam with
  no row in *either* direction is not scored low — it is not scored at all, and every such seam is
  invisible to the number that supposedly measures linkage. Measured: **four independent structural
  checks scored one seam clean**, each for its own reason — the validator cannot resolve a foreign
  id, so a missing row is as invisible to it as a wrong one. Whenever a metric ranges over existing
  records, state its **complement** as a separate number (candidate seams with zero rows, derived by
  set difference against the full pair space), or the score measures the wrong population and rises
  as coverage falls.
- Failure to validate is a normal, publishable result. Record it where the next person will hit it —
  in the instrument's own file, not in a report they will not read.

## Related

- `${CLAUDE_PLUGIN_ROOT}/skills/post-task-review/scripts/probe_checker.py` — the **sight** gate.
  Different question, run first.
- [references/join-diagnostics.md](references/join-diagnostics.md) — linkage detail and the
  write-up format.
- The audit this method comes from is not shipped with the kit; every claim above that cites it is a
  measurement of that one corpus, and Phase A's label-blind list is what keeps it from being
  generalised past its evidence.
