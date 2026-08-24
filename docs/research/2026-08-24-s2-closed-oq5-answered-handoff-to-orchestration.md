# Session handoff — S-2 closed by events, OQ-5 answered and unclaimed. Read this first.

**Session:** `lemmi-ai-kit-90` · **Date:** 2026-08-24 · **Paths held:** this file only.
**Repo writes:** none, except this file. The session was placed under an operator stand-down after
its first report and never lifted.

**One-line state:** S-2 is closed — Arm A landed while the decision was still being read, and the
`AGENTS.md` freeze resolved on its own terms. **One deliverable produced here has not been consumed
by anything: OQ-5 now has an answer, and nobody has ruled on it.**

**What orchestration needs from this document, in priority order:**

1. Take OQ-5's answer to the operator (§3). It is a one-line ruling and it unblocks I-3's D16.
2. Fix the OQ-5 identifier collision before anyone answers the wrong question (§4).
3. Correct the Arm A atomicity text in the kickoff — it is wrong and still deployed (§5).

---

## 1. Task completion review — what this session was asked, and what it did

**Asked:** the operator pasted S-2's ARM A / ARM B block with no instruction.

**Did not execute either arm.** Two reasons, both load-bearing:

- S-2 states plainly *"Do not dispatch this to a fresh session — the owner is frozen, not
  finished."* This session was fresh.
- The tree was being rewritten mid-measurement. Between the first and second probe of one session,
  the staged skill moved out of `.specs/` into `plugins/core/skills/`, and the manifest gained its
  row. Arm B would have run `git restore` across a live peer's uncommitted work.

**Did instead:** measured the decision read-only, produced findings, put the two genuinely
operator-owned questions to the operator, carried the resulting ruling to orchestration, and then
ran the one investigation the board had been waiting on.

### Findings and their disposition

| # | Finding | Disposition |
|---|---------|-------------|
| F1 | Arm A's atomic unit is **four** derived files, not the two the kickoff names | **Confirmed** — `eefaa23` carries all four. Kickoff text still wrong (§5) |
| F2 | No arm honoured the `AGENTS.md` freeze; leaving it dirty is not neutral either | **Resolved** — freeze lifted by orchestration, landed as `d317027` (§6) |
| F3 | Arm B would not clear the flip hazard it names — the two templates sit under `plugins/`, not under `.specs/` | Moot — Arm A landed |
| F4 | The staged PR-template edit risked cross-contaminating two initiatives in one commit | Moot — `3aeee07` took `.github/` alone, one minute earlier |
| F5 | `AGENTS.md`'s dirty hunks and I-3's declared seam are **disjoint**, so the file never needed I-3 | **Acted on** — `d317027` commits exactly those hunks (§6) |
| F6 | **OQ-5 answers itself: detect and recommend, do not install** | **OPEN — the unconsumed deliverable** (§3) |
| F7 | Four different documents each define an "OQ-5" | **OPEN** (§4) |
| F8 | A guard that refuses without naming a remedy breeds the escape hatch it forbids | **Landed** — `publish.py` carries it as a stated rule |

### Verified end state

Measured on a clean tree, not reported second-hand:

```
git status --porcelain                                      -> empty
uv run pytest -q --basetemp <tmp>                           -> 218 passed, 6 skipped, 1 xfailed
git ls-files --others --exclude-standard plugins/           -> 0
git ls-files --others --ignored --exclude-standard plugins/ -> 7   (see section 7)
```

Baseline at session start was 190 passed / 6 skipped. Commits since `7c1c237`, oldest first:

| SHA | Files | Subject |
|-----|-------|---------|
| `3aeee07` | 1 | Point the PR checklist at the post-split manifest paths |
| `eefaa23` | 14 | Add the verification stage the spec pipeline never had |
| `972122a` | 1 | File V-1's review of the restructure |
| `ddf0086` | 1 | Stop the adoption guide promising a skill count |
| `6d40edf` | 2 | Guard the pre-split package path, and stop counting patterns by hand |
| `c88d152` | 3 | Refuse to publish while the payload carries files git does not track |
| `d317027` | 1 | Point the seeded AGENTS.md at the verification stage |

57 commits unpushed. Nothing on this list was written by this session.

---

## 2. What is genuinely closed, so nobody re-opens it

- **S-2.** Arm A landed. The skill is registered, the templates ship, the suite is green.
- **The `AGENTS.md` freeze.** Lifted by orchestration, committed as a declared input to I-3, with
  the non-owner write recorded in the commit message rather than left to be discovered.
- **The two-initiatives-one-commit hazard.** Did not occur.

**Explicitly NOT closed by any of the above: OP-I4-1's open half** — whether one initiative may
write another's file as a standing rule. `d317027` settles the instance and says so in its own
message. Do not read it as precedent.

---

## 3. OQ-5 — answered. This is the payload of this handoff.

**The question (I-4's):** does `kit-setup` install packs, or only detect and recommend them?

**Its dispatch line reads `Session, reported to operator`** — it was never waiting on a ruling. It
was waiting on a session to run it, and no session had. That is why it sat open long enough to be
mistaken for a decision bottleneck.

**Answer: detect and recommend. Do not install.** Four independent grounds, every one from the
repo's own verified measurements rather than from preference:

**a. The bootstrap paradox.** `kit-setup` is a skill inside `lemmi-ai-kit-core`. To invoke it the
user has already added a marketplace and installed a plugin. An install capability could therefore
only ever reach the *second* pack — the exact case the user has already proven they can do unaided.
The feature would be spent on the population that does not need it.

**b. The two hosts diverge on two axes, and one form is a hard error.** From the adoption guide's
verified section:

| Host | Marketplace source | Install verb |
|------|--------------------|--------------|
| Codex | `.` | `codex plugin add` |
| Claude Code | `./` | `claude plugin install` |

Claude Code rejects `.` outright with `Invalid marketplace source format`. Different verb, different
path spelling, and the wrong spelling fails loudly. A skill driving both encodes two brittle CLIs
pinned to the only two host versions ever exercised.

**c. The path the docs actually recommend has never been proven to work.** The adoption guide is
explicit that the `owner/repo` shorthand is *not yet exercised* against this repository on either
host — and that shorthand is precisely what the README tells every adopter to run. Automating an
unverified path ships a skill that fails on first contact with a new adopter.

**d. It self-modifies for no gain.** Installing mutates the running client's plugin configuration
from inside a skill loaded out of that same plugin cache, and the newly installed skills are not
live in the current session regardless. The user restarts either way; the automation saves one
pasted line and costs a restart.

### Two things D16 should know before it builds the recommend arm

**`kit-setup` has zero pack awareness today.** 126 lines; every occurrence of "pack" in it is
incidental — invocation namespacing in the rendered skill catalog, and the word "package" in
project detection. OQ-5's phrasing presupposes a detect-and-recommend capability that does not
exist. **Both arms are unbuilt** — the real question is what D16 builds, and the answer above is
the cheaper arm.

**The host discriminator already exists in the skill, and it has a trap.** Step 0 reads the plugin
root from the environment, so the recommend arm can print the correct command form instead of
guessing. The trap: Codex sets *both* variables for compatibility, so testing the Claude variable
first misidentifies Codex as Claude. The correct test is **`PLUGIN_ROOT` set means Codex, otherwise
Claude.**

---

## 4. Four documents define an "OQ-5". Fix this before answering anything.

| Where | Its OQ-5 | State |
|-------|----------|-------|
| I-4's charter | does `kit-setup` install packs, or detect and recommend | **the live one** — answered in §3 |
| I-2's charter | does the kit need a hooks story | resolved: zero skills require a hook |
| I-3's charter | README-only, or README plus a docs site | open, unrelated |
| Program kickoff table | quotes I-4's wording | duplicate of the live one |

**The failure mode is concrete.** I-3's blocker in the execution plan reads `GATE 3, OQ-5`. A reader
who opens I-3's own charter to find that blocker reads the docs-site question and answers the wrong
thing. Recommend namespacing them — `OQ-I4-5`, `OQ-I3-5` — or at minimum spelling out the owning
charter at every cross-initiative citation.

**A second collision sits underneath it.** The "I-3" that owns `assets/templates/AGENTS.md` is
**I-4's implementation slice 3** (`.specs/i4-pack-split/execution-plan.md:157`), not the program's
I-3 OSS-discoverability initiative. Same label, different work, different owners. Worth noting that
the authoritative ownership record for a contested path currently lives in an **uncommitted** file,
which is its own quiet hazard.

---

## 5. The kickoff's Arm A atomicity text is wrong, and still deployed

S-2 Arm A states the coupled unit as two files — manifest and README — and argues the coupling
convincingly enough to be trusted. Registering a skill actually touches **four**:

1. the manifest — the skill row
2. `README.md` — the count, derived from the manifest
3. `docs/upstream-sync.toml` — a correspondence row, bound by **two** tests
4. `tests/test_upstream_sync.py` — **only for a kit-origin skill.** The kit-origin set is a
   hand-pinned constant, deliberately not derived from the record it checks, so a new kit-origin
   skill has to argue with a test. That is the design; do not route around it.

Measured, not inferred: a tree carrying the skill directory and the manifest row but no sync row
gives **2 failed, 188 passed, 6 skipped**, both failures in `test_upstream_sync.py`. The executing
session reached the same four independently and `eefaa23` is correct. **The kickoff text was never
corrected and will mislead the next session that registers a skill.**

Row shape for a never-extracted skill: empty upstream, direction `kit-origin`, plus a note. No
adopted-evidence SHA is required — that loop is scoped to the two skills that also exist upstream
and that a naive check reports backwards.

---

## 6. How `AGENTS.md` actually resolved, and the argument that unlocked it

The operator's ruling was *postpone the commit and delegate to the I-3 orchestration session.* That
ruling was carried to orchestration and is recorded. It was then overtaken by a better outcome, and
the reasoning is worth keeping because it generalises.

**The freeze looked like it needed I-3 to run. It did not.** The dirty hunks sat at lines 95,
99-102 and 116-118 — inside `### Spec-driven development` and `### Plan self-review`, both under
`## AI Development Workflows`. I-3's declared seam in that file is `### Project rules`, at line 163,
under `## Do not`. **Disjoint: different top-level sections, 45+ lines apart, no overlap.**

The freeze's stated purpose was that I-3 should not open its own `Owns` set and find an unexplained
modification. That purpose is served by **the record**, not by the file staying dirty — and by then
the record existed in three places. Meanwhile "dirty" had stopped being free: `plugin install`
copies the working tree, so a **modified tracked** file ships modified exactly as an untracked one
does, and the new guard demands an empty status with no escape hatch.

**Generalisable rule:** a freeze on a path is only as narrow as the overlap it actually protects.
Before treating one as blocking, diff the frozen hunks against the owner's declared seam. If they
are disjoint, the freeze costs more than it buys.

---

## 7. The flip's remaining mechanical condition

`others` under `plugins/` is 0. `ignored` is **7** — bytecode caches, one of which the guard module
creates by the act of being imported. The guard will refuse on these, deliberately: its docstring
refuses to exempt bytecode on the grounds that six such files under the package tree **were** the
original finding, and a guard blind to the bytes that motivated it reports green for an unrelated
reason.

**So this is operating procedure, not a defect: the tree must be cleaned of ignored files
immediately before publishing, and the guard must run after that cleaning, not before.** The
docstring is explicit that a green self-run after importing the module is not evidence of anything.
Whoever runs the flip drill should treat "clean, then measure, then publish" as one ordered step.

A related note for anyone measuring this tree: run the suite with bytecode writing suppressed, or
the act of measuring adds to the count the guard refuses on.

---

## 8. Limits of this handoff — what was not done, and what may already be stale

- **Nothing here was executed.** No arm, no commit, no correction. Every §4 and §5 fix is
  unassigned work.
- **Every measurement is a snapshot of a shared, actively-written checkout.** During this session
  the tree changed under a single probe more than once. Re-measure before acting on any number.
- **OQ-5's answer is a finding, not a ruling.** Its dispatch says the session reports and the
  operator rules. The operator has not yet ruled.
- **`kit-setup` was read, not exercised.** The bootstrap and discriminator claims come from reading
  the skill and the adoption guide's verified section, not from running an install.
- **Session enumeration sees Claude sessions only.** Attribution of any tree change to a named
  session would be a guess, so none is made.
