# Join diagnostics — proving the labelled set is not a biased sample

Loaded on demand from `metric-validity-check` Phase B. Read this when there is no foreign key
between the outcome label and the artifact, or when the match rate is below ~90%. (That 90% and the
~50% floor near the end are **chosen, not derived** — no source sets them. Treat them as prompts to
think, not thresholds to pass.)

## Why this is not paperwork

Joining a label to an artifact by anything other than a key is **record linkage**. Its defining
hazard is that linkage error is *not random*: the records that fail to link differ systematically
from the ones that succeed, so the joined set is a biased sample and every downstream comparison
inherits the bias.

Measured magnitudes from the linkage literature (Harron et al. 2014, *BMC Med Res Methodol* 14:36 —
<https://pmc.ncbi.nlm.nih.gov/articles/PMC4015706/>):

> estimates of difference in rates were biased by up to 38% for a match rate of 70%, rising to 53%
> for a match rate of 10%

and ~112% when the error was non-randomly distributed with respect to the outcome. Harron et al.
2017 (*IJE* 46(5):1699–1710) name the three mechanisms — **attenuation**, **reduced power**, and
**selection bias** — and state the reason plainly:

> linkage errors do not always occur randomly, meaning that particular subgroups of individuals are
> often over- or under-represented amongst records affected by linkage error

The audit this skill comes from lost a headline finding to exactly this and nothing else.

## The nearest-match join, written out

Within each user (never across users), for each label event, choose the artifact with the smallest
positive gap `label_time − artifact_time`, subject to a stated maximum window.

Three decisions must be *written down*, because each silently changes the result:

1. **The window.** Derive it from the product's timing — where does the app fire the survey? — not
   from what makes the numbers work.
2. **The tie rule.** What happens when two artifacts are equidistant, or when two labels claim the
   same artifact. State it even if it never fires; a rule that fired zero times is a fact, a rule
   that was never defined is a gap.
3. **Direction.** Labels almost always follow artifacts. If you allow negative gaps you are matching
   a rating to a session that had not happened yet.

## The seven diagnostics, with the write-up format

> **Emit the diagnostics from the join itself, or three of them become unrecoverable.**
> Measured while validating this skill: a join artifact that stores only the *chosen* match and its
> gap cannot afterwards answer #1 (labels that matched nothing), #3 (how many candidates were in the
> window, and which tie rule fired) or the label half of #4 — the losing candidates and the orphan
> labels are simply not in the file, and re-deriving them means re-running the join.
>
> So the join script must write, per label event: the chosen artifact, the gap, **the candidate
> count**, **the tie rule applied**, and a separate list of **unmatched labels**. Two minutes at
> write time; otherwise the numbers are gone.

Report all seven. Copy this block into the report and fill it.

```text
JOIN: {nearest-match within user | FK | fuzzy on <fields>}
window: {W}    direction: {label after artifact}    ties: {rule}

1. match rate          labels {a}/{b} = {p}%      artifacts {c}/{d} = {q}%
2. gap distribution    median {m}  p90 {n}  max {x}    (n={N})
                       tail read: {what the longest few look like on inspection}
3. multi-candidate     {k} label events had >1 artifact in window; resolved by {rule}
4. unmatched           labels {b-a} — spot-read cause: {...}
                       artifacts {d-c} — spot-read cause: {...}
5. linked vs unlinked  compared on {covariates}: {difference or "none detectable"}
6. window sensitivity  {W/2}: {result}   {W}: {result}   {2W}: {result}
7. coverage per arm    worst arm {x}%   best arm {y}%   overall {z}%
```

### 1 — Match rate, both directions

An asymmetric rate is informative. Labels-matched far below artifacts-matched means labels are being
dropped (window too tight, or a population mismatch). The reverse means most artifacts never get
rated, which is normal but means the labelled set is self-selected — say so.

### 2 — The full gap distribution

**Never report a mean alone.** The mean hides the tail, and the tail is where the false matches are.
Report median, p90 and max. Then actually look at the longest few matches and say what they are.

Worked numbers from the source audit (162 label rows): median **15.2 min**, mean 16.8, min 6.0, max
**74.3**. The tight distribution is what licensed the join — a survey that fires minutes after the
session leaves little room for a wrong nearest neighbour. A distribution with a fat tail would not
have.

### 3 — Multi-candidate events

Count them. If a meaningful share of label events had more than one candidate artifact in the
window, "nearest" is doing real work and you need the sensitivity analysis in #6 to be convincing.

### 4 — Unmatched on both sides

Do not just count. Read a handful. Systematic unmatching is usually a **finding about the product**
(a flow that never fires the survey, a cohort excluded from the artifact table), and it tells you
who is missing from your labelled set.

### 5 — Linked vs unlinked comparison

Take any covariate you have for both linked and unlinked records — tenure, plan, platform, duration,
locale — and compare. If they differ, **the labelled set is not the population**, and that sentence
belongs in every downstream claim, not just here.

If you have no shared covariate, say that. "Could not compare" is a real limitation; "no difference"
is a claim you did not earn.

**This is the diagnostic most often skipped and the one that most often bites.** Measured while
validating this skill, on the corpus the source audit used — a comparison that audit never ran:

| measure | linked (rated) | unlinked (unrated) |
| --- | --- | --- |
| n | 161 | 217 |
| median duration | 876 s | **219 s** † |
| median turns | 19.0 | **7.0** |
| completed | 99% | **38%** |

† 2 of the 217 unlinked rows carry no duration and are excluded from that median; counting them
as zero gives 215 s. Say which you did — an unstated exclusion is an unnamed denominator wearing a
different hat.

Only 43% of artifacts carried a label, and the ones that did were four times longer and almost
always finished. Users who abandoned early essentially never rated. That does not invalidate the
audit's findings — but it bounds them: **every conclusion drawn from those labels describes long,
completed sessions**, and the worst experiences in the product are systematically absent from the
labelled set. One `git`-free command produced this; not running it left the bound unstated in a
five-day audit.

### 6 — Window sensitivity across ≥3 widths

Re-run the whole analysis at half, nominal, and double the window. Report the headline number at
each.

**Read the result correctly.** If the answer is stable, the join is not driving it. If the answer
moves, the honest conclusion is usually *not* "pick the best window" — when the matching variable
correlates with the outcome, window width is an **effect modifier**: different widths select
genuinely different populations. Report the instability as a limit rather than tuning it away.

### 7 — Coverage per arm, never overall

This is the one that inverted a headline. A derived covariate available on 40% of records overall
sounds like a coverage caveat. Available on **5 of 22 records in the arm the finding is about**, it
is a selection artifact — and the direction of the bias is unknowable without a higher-coverage
substitute.

**Rule: any covariate whose availability differs by arm is itself an outcome.** Report its coverage
per arm before you report any comparison that uses it. If the imbalance is large, either find a
higher-coverage estimator and validate it against labels you did not produce, or drop the claim.

## When the join is not worth it

Skip the nearest-match join and say so if any of these hold:

- Labels arrive hours-to-days after the artifact and users have several artifacts per day — the
  nearest neighbour is a coin flip.
- The match rate would be under ~50% and you have no way to characterise who is missing.
- There is a queryable key one team away. Ask for it. One request beats three passes of inference —
  and an inferred join that is later falsified propagates into every document built on it.

In those cases the fallback is an aggregate before/after comparison, which is far weaker but honest.
Say which you used and why.
