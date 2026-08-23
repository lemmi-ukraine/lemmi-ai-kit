# I2 W2.4 — self-challenge and completion review

**Dated:** 2026-08-23, at the end of the session that executed I2 W2.4 (pin, drift check,
sync procedure).
**Reviews:** [upstream-sync.toml](../upstream-sync.toml) ·
[syncing-from-upstream.md](../syncing-from-upstream.md) · `tests/upstream_sync.py` ·
`tests/test_upstream_sync.py`
**Method:** adversarial. Every figure re-derived from the two trees at review time, not
re-read from the artifacts that published it. The one claim that did not survive is
corrected below.

---

## 1. The finding that changes other people's work: the base I was told to use is wrong

The kickoff was explicit — *"Compare three-way against the extraction-point merge base
(upstream at 2026-07-06)"* — and building to it exposed it.

This repo's first commit is **2026-07-02T23:26**. The base named for the whole initiative
is dated **2026-07-06**: four days *inside* the extraction window. Three upstream commits
land in the gap.

| Measured | Value |
|---|---|
| Insertions in the gap, across the skills tree | **2,668** over 16 skill directories (15 shipped, 1 declined) |
| Of those, the two linters + tests this kit deliberately does not ship | 1,024 |
| **Skill content the wrong base could not distinguish from this repo's own deletions** | **1,644** |
| True base — last upstream skills commit before this repo's first | `3dd2496d`, 2026-06-25T21:39 |

**Why this is worse than a mis-measurement.** The refresh's own classification rule reads
*present at base, absent in ours, present in theirs* as a deliberate kit deletion — keep it
deleted. Every line upstream added inside the window is present at the too-new base, so all
1,644 were eligible to be read that way and dropped with nothing objecting. The carry audit
that certified the refresh used the same base, so it could not have caught this either. A
wrong base does not merely mis-order the work; it launders upstream content into "our
deliberate divergence".

**Spot-checked rather than asserted:** all **19** window-added lines of
`skill-researcher/SKILL.md` are absent from the shipped file — and that skill reports
**zero** drift against the pin. Some of those lines are correctly absent (they carry
source-project rules), which is exactly why clearing this needs a per-skill read and not a
bulk re-merge.

**Independent corroboration.** The concurrent `session-retrospective` session reached the
same conclusion by a different route — minimum-distance base selection across every
upstream revision of each file (9 diff-lines at the true base against 271 at the
next-closest) — and found the charter's "~1,100-word uncharacterized removal" was this same
artifact: upstream added the extractor's schema v4 on 2026-07-05, three days after
extraction. Two sessions, two methods, one answer.

**Carry forward:** an extraction window is a range of commits, not an instant. Pick the base
by the timestamp of the extraction's *first* commit, verify no upstream commit touching the
tree falls between base and extraction, then confirm per file by minimum distance.

## 2. The claim that did not survive review

One published sentence was wrong, and it was wrong in the direction of sounding stronger.

I wrote that "three of the four skills that **report zero drift against the pin** are on the
window list." After I corrected `extraction_base`, every row's base became the pin, so
**35 of 36** skills report zero drift — the sentence had become nearly vacuous while reading
as a tight coincidence. The substance is intact but needed the precise frame: three of the
four skills upstream never touched **between the too-new base and the pin** are on the
window list. Re-derived at review time: `commit-message`, `skill-content-reviewer`,
`skill-creation-workflow`, `skill-researcher` are the four; the last three are on the list.

**Carry forward:** when a denominator changes because of a correction made later in the same
session, re-derive every ratio that used it. This one broke silently — the number stayed
true, the population moved underneath it.

## 3. Two diagnosis defects I found by challenging the check rather than testing it

Both were in code that passed, and neither would have produced an error — only a confident
wrong answer.

**A row whose base SHA does not resolve was reported as "directory absent at base".** Two
different faults with two different fixes — a bad SHA or a shallow clone versus a wrong
`upstream` name — collapsed into one message that sends the reader to the wrong field of the
record. Now reported apart, and the new branch has its own test; adding a diagnosis branch
nothing has seen fire is the failure this suite's own docstring criticises.

**The window re-derivation parsed newline-separated `--name-only` output.** Git quotes paths
containing non-ASCII bytes by default, so a quoted path would parse into a directory name
that does not exist and fabricate a `RECORD INCOMPLETE` entry. Now `-z`. Skill directories
are kebab-case ASCII today — which is the kind of assumption that stops holding quietly.

## 4. What I checked at review time and found sound

| Claim | How re-checked | Result |
|---|---|---|
| Pin SHAs resolve and are correctly ordered | `git log -1` each; `merge-base --is-ancestor` | `c05bf72d` 2026-07-06, `aa31c338` 2026-07-13, `2e9737bd` 2026-08-20, `a78ee5af` 2026-08-22; ancestry holds |
| Zero upstream skills commits between `2e9737bd` and the pin | `rev-list` | 0 — the two are interchangeable for drift |
| `orchestrate`/`agent-delegate` originate here | byte compare kit `a836bd5` vs upstream `aa31c338` | **identical**, 6,775 and 3,153 bytes. Upstream's commit message even carries this repo's `fable-orchestrate` name |
| `scout-review` is not an upstream ancestor | `log --all` on that path upstream | 0 commits — kit original, verified not assumed |
| Correspondence map resolves against real upstream | live run | 36 tracked rows, **0** map errors, **0** undeclared, **0** vanished |
| The recorded window list is complete | re-derived from git independently of the record | exact match, 16/16 |
| Window arithmetic | `diff --numstat`, insertions only | 2,668 total, 1,024 unshipped, **1,644** exactly — not "roughly", as first published |
| The correspondence gate actually fires | removed one row, ran the suite | 2 tests red with the row named; restored |
| Hygiene contract on my own files | imported the compiled patterns, applied them to all five | 2 violations found in my own comments, fixed by rewriting rather than allowlisting |
| CI wiring is valid | parsed the workflow; ran the exact step command | 8 steps, `continue-on-error: true`, exit 0 |
| Scaffold no-regression (charter DoD 7) | scaffold into a fresh temp directory | `AGENTS.md`/`CLAUDE.md`/`.ai/` produced, 24 skills indexed |

Four checks green throughout: `ruff check` · `ruff format --check` · `basedpyright` ·
`pytest`. **148 → 185** tests (184 plus one that skips without an upstream checkout).

## 5. The design decision most likely to be second-guessed, and why it holds

**Drift is counted in commits, not content.** The obvious implementation is a per-skill
content hash, and it is wrong here: the refresh dropped 82 upstream lines deliberately, so a
hash would report them as drift on every run forever and be silenced within a month. A
commit count is zero the moment a sync lands and stays zero until upstream moves.

The cost of that choice is a real blind spot, and §1 is an instance of it: a commit count
cannot see a gap that predates the base. That is why the window is reported as its own
finding rather than folded into the drift numbers — folded in, 16 skills would sit
permanently "behind", which is the other way a check gets ignored. Both failure modes are
"the maintainer stops reading it"; the split is what avoids each.

**A second-guess I accept in advance:** `MAP ERROR` exists only because `rev-list --count`
over a non-existent path returns 0. Without it a single typo in an `upstream` name would
report "in sync" forever while measuring nothing. That check is the difference between a
gate and a rubber stamp, and it is the one I would restore first if any of this were cut.

## 6. Scope discipline — what I declined to do

- **Did not clear the extraction-window debt.** 15 shipped skills needing per-skill
  portability reads, all inside `assets/skills/` — another session's tree, and a content
  refresh rather than a sync mechanism.
- **Did not promote either gate.** The drift check's criteria are written down with three of
  four still open; `audit-skills --fail-on major` needs the five audit findings cleared and I
  re-measured that all five are still open, all inside `assets/skills/`.
- **Did not touch `assets/skills/`.** The `session-retrospective` modifications in the tree
  are the concurrent session's.
- **Did not put the drift check in the CLI.** Adopters have no upstream, and the charter
  names shipped CLI subcommands a one-way door. It is maintainer tooling and lives in
  `tests/`, where all four checks cover it.
- **Did not add a README or CONTRIBUTING pointer** to the new document. Not my files; named
  as an owed follow-up instead.

## 7. Limits that remain, and are not resolvable from this session

- **The check cannot run in CI.** Upstream is private and absent, so the step's normal
  output is `NOT MEASURED`. Everything not needing upstream is gated instead. Promoting the
  gate before CI can reach a checkout would promote `NOT MEASURED` to a pass — green, and
  meaningless.
- **The 82 deliberately-dropped lines are classified but not enumerated anywhere
  machine-readable.** A future maintainer wanting to revisit one has prose, not a list.
- **The record describes `HEAD`, not the working tree.** With the reconciliation uncommitted,
  `session-retrospective` is recorded as unmerged on purpose: claiming it reconciled and
  being wrong is a silent false negative; claiming it behind and being wrong is a loud false
  positive somebody investigates.
- **Window exposure is measured in commits, spot-checked in one file.** How much of the 1,644
  lines is actually absent from the pack is unknown; in the one skill checked it was all of
  it.
- **`sweep_user_corrections.py`** has still had no portability read, and it now exists
  untracked in the tree.

## 8. Did W2.4 meet its Definition of Done?

| DoD | Verdict |
|---|---|
| **5** — recorded upstream revision, plus a drift check wired into CI as a non-blocking report | **Met.** Pin is the upstream SHA at the sync point; correspondence map carries the `direction` column; report is `continue-on-error` and returns 0 on every path, including an invalid record |
| **6** — `docs/syncing-from-upstream.md`, including what is deliberately not ported and why | **Met.** Nine sections: the three artifacts, how to measure, the three rules, the procedure, the seven declined skills plus four standing divergences, outstanding debt, promotion criteria, and the check's blind spots |
| **7** — scaffold no-regression | **Met**, re-verified at review time |
| **1–4** | Not this wave's, and untouched — I edited no asset and added no allowlist entry |

**Net:** the deliverables are built and the check earns its keep on first contact — its
opening run reported exactly one skill behind, the one independently known to be deferred,
with zero map errors across the other 35. The larger result is not the mechanism though: it
is that building the mechanism honestly refuted the base the whole initiative measured
against, and put a number on what that cost.
