# I5-D1 — the project-map falsification run

**Status: PRE-REGISTERED, NOT YET RUN.** Steps 1–3 of the charter's protocol are below. Steps 4–6
are blank by design and get appended after the run.

**The point of committing this first.** The charter says *"a scoring rule chosen after seeing the
output is not a test."* Git history is the proof: this file's commit predates any result appended to
it, so the rule cannot be adjusted to fit what came out. If you are reading a filled-in version,
check that the verdict table below is byte-identical to the one in this commit.

**Gate:** I4 slice I-3 merged — **satisfied 2026-08-24** (`aa574ed`, `df2b173`, `d5cc088`), which is
what made this runnable.

---

## Step 1 — the two arms · **NEEDS THE OPERATOR**

Both must be named here **before** the run.

| Arm | Project | Why this one |
|---|---|---|
| **Primary** | **The private source project this kit was extracted from** — fixed by the operator 2026-08-24, before the run. Not named here; it is named in the operator's own records, which is where identifying detail about a private repository belongs | The operator knows it cold, which is what the premise requires |
| **Control** | **not run** — recorded as a gap, not skipped silently | See the limitation below |

> **Why this record carries no detail about the arm.** The subject is a **private** repository, and
> this file is tracked in a repo that goes public. Naming it, or describing its internals, is the
> "source-project reference" this project's own publication-hygiene contract bans — and the contract
> caught exactly that in an earlier revision of this file. The derived claims and the raw
> measurements live outside this repository. **Only counts and the verdict come back here**, which is
> all the falsification test needs: the arm has to be *fixed* before the run, not *published*.

The control arm can be a public repository. It does not need to be Lemmi's.

### The confound the operator raised, recorded BEFORE the run

**The operator's objection, verbatim in substance:** the arm already has a hand-written `AGENTS.md`,
a map, and AI-oriented comments in its code, so a derived map may find nothing simply because
everything worth saying is already written.

**It is a real confound and it is recorded here rather than discovered afterwards.** Measured
2026-08-24; the figures themselves stay in the operator's records, since sizing a private
repository is still describing it. The one ratio the argument turns on:

> **Roughly 270 lines of application code per line of hand-written `AGENTS.md`.**

**Why the run proceeds anyway.** At that ratio the prior documentation is a strong *baseline*, not a
ceiling. The premise is being tested against a real hand-written map rather than against a vacuum,
which makes a **positive** result stronger than it would be on an undocumented repo.

**What this costs, stated so the verdict cannot be over-read.** A `did-not-know = 0` outcome here
must be reported as *"refuted on an unusually well-documented repository"* — the hardest available
case — and **not** as "refuted for the population I5 targets," which is an adopter installing the
kit into a project with no `AGENTS.md` at all. If the verdict table's second or third row fires,
that qualification travels with it into every document that cites this result.

**Two protocol adjustments, both made before deriving anything:**

1. **The derivation is blind.** Claims are produced from the code only. `AGENTS.md`, `CLAUDE.md`,
   `.ai/` and the AI comment markers are not read while deriving, so no claim can be laundered out
   of the existing documentation and then counted as derived from code.
2. **`already-written-down` is labelled mechanically, by the session, not by the operator.** Each
   claim is checked against those documents *after* derivation. That label is a fact about the repo,
   not about the operator's memory, so it does not need their judgement — and removing it from their
   burden leaves them the three labels that genuinely require it.

## Step 2 — the claim definition and scoring rule · **FROZEN**

**A claim is** one sentence an adopter would plausibly paste into `AGENTS.md`, **or** one node of the
project map. Count claims; **do not grade prose quality.**

**Every claim gets exactly one label. No abstentions, no second labels, no "partly".**

| Label | Means |
|---|---|
| `already-written-down` | It is already stated somewhere in the project — a README, a docstring, a rule file |
| `knew-but-unwritten` | True, the operator knew it, but it was not written anywhere |
| `did-not-know` | True, and the operator did not know it or had not articulated it |
| `wrong` | False, or true-but-misleading in a way that would mislead a new contributor |

`did-not-know` is the load-bearing label. It is the only one that supports the premise.

## Step 3 — the verdict table · **FROZEN**

Read the outcome off this table. Do not argue with it afterwards.

| Outcome of the primary arm | Verdict |
|---|---|
| **≥3 `did-not-know`** claims that change a rule the operator would actually write | **Premise holds.** Build `I5-D2`–`I5-D7`. At n=1 this licenses the **minimal** shape only, not the full set |
| **`did-not-know` = 0** and **`knew-but-unwritten` ≥ 5** | **The value is transcription, not derivation.** Do not build a deriving skill. `kit-setup` gains a *question list* — cheap, no code read — and the guide gains the section. The initiative shrinks by roughly its whole cost |
| **`did-not-know` = 0** and **`knew-but-unwritten` < 5** | **Premise refuted. I5 closes.** Ship `I5-D6` as a section in `docs/adoption-guide.md` telling the adopter what to write by hand. **A legitimate outcome, not a failure** — the cheapest result available, and it retires a roadmap item |
| **Any `wrong` claim** that would have reached `AGENTS.md` unchallenged | **Independent gate, regardless of the counts above.** `I5-D5` (provenance per claim) becomes a precondition on everything, not a deliverable among others |

**And the third outcome the control arm can produce:** if the control arm yields `did-not-know`
claims and the primary does not, the finding is **not** that the interview is ceremony — it is that
**it serves someone joining an existing codebase, not its author.** Different product, different
pitch, different audience. The charter gets rewritten rather than closed.

## Step 4 — the run · **RUN 2026-08-24**

A hand-driven code read by `lemmi-ai-kit-b1`, then labelling by the operator in conversation.
**Not the shipped `kit-setup`** — a probe, not a prototype. No new files under `plugins/`, and no
file was written into the arm.

**12 claims** were derived. The derivation was **blind** as pre-registered: the arm's `AGENTS.md`,
`CLAUDE.md`, `.ai/` and AI-oriented code comments were not read while deriving, so no claim could be
laundered out of existing documentation. Scope was the layout, the persistence/observability seam,
the AI-provider composition, the test topology and the dependency surface. **12 is what one pass
produced, not a ceiling** — several subsystems were not read at all, and their absence is not
evidence that they are well documented.

`already-written-down` was assigned mechanically by the session, per the pre-registration, by
grepping each claim's key term across the arm's documentation set. The probe was controlled: a term
known to be present hit 3 of 3 top-level documents, 44 files in `docs/` and 146 in `.ai/`, so a zero
means absent rather than a broken search.

**No claim, quotation, path or measurement from the arm is recorded here.** The working list stayed
outside this repository and was destroyed after labelling. Counts and verdict only — which is all
the test needs, and all a public repository may carry about a private one.

## Step 5 — labelling · **COMPLETE 2026-08-24**

| Label | Count |
|---|---|
| **`did-not-know`** | **6** |
| `knew-but-unwritten` | 4 |
| `already-written-down` | 2 |
| **`wrong`** | **0** |
| **Total** | **12** |

**The qualifier the first verdict row demands was asked separately**, so it could not be inferred
from the count: of the six `did-not-know` claims, the operator identified **four** as ones that
would change a rule they would actually write into `AGENTS.md`. They cover three distinct areas —
a configuration flag with an undocumented second effect, two parallel structures kept in sync by
hand, and the construction path for a core abstraction.

## Step 6 — verdict · **PREMISE HOLDS**

Read off row 1 of the frozen table: **≥3 `did-not-know` claims that change a rule the operator would
actually write** — measured 4, against a threshold of 3.

> **Build `I5-D2`–`I5-D7`. At n=1 this licenses the MINIMAL shape only, not the full set** — per the
> charter's own Minimal viable initiative section, and per the warning there against funding the
> build half in the same breath as the test half.

**The `wrong` gate did not fire.** Zero wrong claims, so `I5-D5` (provenance per claim) stays a
deliverable ranked among others rather than becoming an unconditional precondition. It is still in
the licensed set.

### What this result is not

- **n = 1, and there was no control arm.** The control existed to distinguish *"the method has no
  signal"* from *"this operator knows this one repository unusually well"* — a distinction that
  matters when the result is null. **This result is not null**, so the missing control weakens the
  generalisation but not the finding: something was found, and a control cannot unfind it.
- **The confound the operator raised cuts in favour here.** The premise was tested against a real
  hand-written `AGENTS.md` at roughly 270 lines of code per line of map — a strong baseline, not a
  vacuum. Six `did-not-know` claims survived that. On a project with no `AGENTS.md`, the population
  I5 actually targets, the yield should be higher, not lower.
- **It licenses the minimal shape and nothing else.** One arm, one operator, one pass over part of
  one codebase. It does not license the full deliverable set, and it says nothing about whether an
  adopter who is *new* to a codebase gets the same value — the charter's own third outcome.
- **The derivation was an agent reading code, not the shipped tooling.** Whether `kit-setup` can
  produce claims of this quality is a separate question that `I5-D2` has to answer.

---

## The objection this record must answer when it is filled in

*"Of course the operator already knows their own project — the test is rigged."*

**No: that is the population.** Everyone who runs `kit-setup` runs it on a repository they own. The
premise is precisely that a derived map tells the code's own authors something they did not know. If
it only works for strangers to the code, the feature has a different audience than the one it was
requested for — and the control arm is what detects that.

## Honesty about n, recorded before the result exists

**n=1 per arm refutes cheaply but confirms weakly.** A passing primary arm licenses the *minimal*
build, not the full deliverable set. The second and third data points come from real adopters, who do
not exist while the repository is private — so a confirming result here should be treated as
permission to build the smallest thing, and re-tested when adopters exist.

## What already argues against the premise, recorded so a passing run has to beat it

The charter's provenance table has eight rows. Seven are measured. **The one carrying the whole
initiative — *"a derived project map tells the adopter something they did not already know"* — is
inherited from the operator and unverified at n=0.** And the eighth row contradicts it: the kit's own
shipped `AGENTS.md` template routes project rules to the `task-learnings` → `learning-consolidator`
loop *"as they are discovered"*, which is the opposite of front-loading them from a code read.

**The kit's shipped design and this initiative's premise disagree.** That is the strongest reason to
spend one session measuring before spending five building, and a passing run should be read against
it rather than instead of it.
