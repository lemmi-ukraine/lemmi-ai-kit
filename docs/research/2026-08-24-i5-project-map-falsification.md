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
| **Primary** | *(unfilled)* | A real project the operator knows cold. The premise is that a derived map tells the code's own author something new; anything less familiar tests a weaker claim |
| **Control** | *(unfilled)* | A real project **nobody in this loop wrote**. Exists to separate *"the method has no signal"* from *"this operator knows this one repo unusually well"* |

The control arm can be a public repository. It does not need to be Lemmi's.

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

## Step 4 — the run · **NOT YET RUN**

A hand-driven interview plus code read, one session per arm. **Not the shipped `kit-setup`** — this
is a probe, not a prototype. No new files under `plugins/`.

## Step 5 — labelling · **NOT YET RUN**

## Step 6 — verdict · **NOT YET RUN**

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
