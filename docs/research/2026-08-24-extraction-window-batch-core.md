# Extraction-window recovery, core batch — 39 lines adjudicated across three skills

**Dated:** 2026-08-24. **Scope:** `task-learnings`, `hypothesis-validator`, `session-retrospective`
— three of the seven skills the measurement record left `unreviewed`.

This executes the worklist in
[2026-08-24-extraction-window-remainder-measured.md](2026-08-24-extraction-window-remainder-measured.md).
Every window-added line absent from the shipped tree now carries an explicit verdict with a rule
cited. **Nothing here is left "expected to be fine".**

## The defect, restated in one line

The 2026-08-23 refresh used `c05bf72d` as the three-way base for every skill — four days *inside*
the extraction window, whose true base is `3dd2496d`. The refresh read *"present at base, absent in
ours, present in theirs"* as a deliberate kit deletion, so anything the window added was eligible to
be dropped silently. Drift reports zero because drift counts upstream commits since the base, and
the base is wrong.

## Carriage

Reproduced independently before touching anything: window-added lines under each upstream skill
directory, checked for presence anywhere in the shipped directory, bytes decoded explicitly as
UTF-8. The three absent counts matched the measurement record exactly (19 / 11 / 9), which is the
only reason the adjudication below can be trusted to be reading the same set.

| Skill | Window lines | Carried before | Carried after | Absent now | Carriage |
|---|---:|---:|---:|---:|---:|
| `core/task-learnings` | 56 | 37 | 43 | 13 | **66% → 77%** |
| `core/hypothesis-validator` | 115 | 104 | 104 | 11 | 90% → 90% |
| `core/session-retrospective` | 598 | 589 | 589 | 9 | 98% → 98% |
| **Batch** | **769** | **730** | **736** | **33** | **95% → 96%** |

**The percentage understates the work, and the metric says so itself.** Presence is exact substring
match, so a line recovered in *generalised* form still reads as absent. Of the 12 lines recovered or
partially recovered below, the probe credits 6; the other 6 were rewritten to strip a source path, a
dated internal citation, or a machine-specific clause, and a rewritten line cannot match. The verdict
table, not the percentage, is the deliverable.

## Verdicts, grouped by rule

39 absent lines. Every one classified; the counts below sum to 39.

| Rule applied | `task-learnings` | `hypothesis-validator` | `session-retrospective` | Total |
|---|---:|---:|---:|---:|
| **RECOVER** — portable content the refresh dropped; carried verbatim or generalised | 11 | 0 | 1 | **12** |
| **ALREADY REPOINTED** — an unshipped-linter call site the refresh had *already* pointed at the kit CLI; verified, not assumed | 1 | 2 | 3 | **6** |
| **SUPERSEDED / re-wrap** — the kit's text says the same or more; the exact match fails because the kit inserted, renumbered, or re-wrapped around the line | 6 | 7 | 3 | **16** |
| **CORRECTLY ABSENT** — the line is coupling the kit must not ship | 1 | 2 | 2 | **5** |
| | **19** | **11** | **9** | **39** |

The CORRECTLY-ABSENT bucket is small because most coupling was **inside a line whose rule was
portable**. Those lines are counted as RECOVER and were rewritten to strip the coupling — a source
directory layout, a dated internal citation, an onboarding-sync clause. Counting them as
correctly-absent would have made the drop look like a decision when it was a rewrite.

### `task-learnings` — 19 lines, spans `SKILL.md` and `references/learnings-format.md`

**RECOVER (11 lines).** Delivered as four edits:

- **`SKILL.md` Step 5.3** — the verify-placement instruction now reads *"Verify placement
  structurally — not by eyeballing — and run the lint"*. The structural rule and the lint call were
  already shipped (and the kit had already strengthened the lint from *optional* to REQUIRED); the
  **contrast** was what the window added and the refresh dropped.
- **`SKILL.md` Step 6 table, two new rows.** *"Invariant a future edit could silently break →
  co-located code comment at the exact site"* is fully generic and is carried verbatim. The
  subsystem row is carried as its **idea** — a gotcha scoped to one module belongs in that module's
  own README rather than the global rules — with the source project's directory layout and its
  onboarding-sync clause left out.
- **`references/learnings-format.md` preamble** — the file is declared the **single source of truth**
  for the entry format *and* the canonical category set, shared with `learning-consolidator`, with
  SKILL.md linking rather than restating. This is the rule the kit already follows; the window added
  the sentence that says so, and without it the arrangement was convention rather than contract.
- **`references/learnings-format.md` lifecycle** — `## Consolidation Guidance` becomes
  `## Lifecycle: Intake Buffer → Homes`, prefaced with the model: the intake file is a lean buffer,
  not a knowledge store; entries accumulate and the consolidator drains each to its home, run
  whenever entries have accumulated rather than waiting for the file to grow large. The
  drains-to-homes bullets were already shipped — **the model that explains why they are a lifecycle
  was not**, and a list of destinations without it reads as filing advice. No inbound link targeted
  the old heading (checked repo-wide before renaming).

**ALREADY REPOINTED (1 line).** The placement self-check invoked the unshipped linter by a
hard-coded skill-script path. The kit substitutes its own CLI and the refresh had already made that
substitution, in the module form the packaging requires — the console-script form is banned because
a plugin install places no console script. Verified rather than re-done.

**SUPERSEDED / re-wrap (6 lines).**

- **Four lines carry the count "six"** — in Step 4, in the entry-format stub, in the field-rules
  table, and in the categories heading. The kit ships **seven** categories, and its
  `learnings-format.md` states the count in exactly one place on purpose, with the reason written
  next to it. Re-importing "six" would reintroduce the duplicated-constant defect that file
  documents. **The upstream line here is the wrong one** — this is the `skill-content-reviewer`
  shape in miniature, except the kit is ahead rather than behind.
- **One line makes the lint optional** (*"Optional self-check —"*). The kit made it REQUIRED after
  three malformed entries reached the buffer. Carrying it back would revert a fix.
- **One line describes what the lint validates.** The kit says the same thing; the exact match fails
  only because the machine-specific parenthetical was stripped from the tail of it.

**CORRECTLY ABSENT (1 line).** A machine-specific runner rule naming a developer OS and forbidding a
particular runner on it. Banned by the hygiene contract, and the instruction it qualifies is shipped
without it.

**Coupling stripped from inside RECOVERED lines, and therefore not counted separately:** the source
project's `backend/app/...` directory layout and its onboarding-sync clause (both in the subsystem
row), and one dated internal citation attributing the intake-buffer model to a source-project event.
The rules survive; the coupling does not.

### `hypothesis-validator` — 11 lines, **zero recoveries, and that is the finding**

The whole file was added inside the window, so its 90% carriage means the refresh imported the skill
and stripped exactly what it should have. Every absent line was read; none is a loss.

- **ALREADY REPOINTED (2).** Both unshipped-linter call sites — the fleet audit in Step 3 and the
  data-file lint in the verify step — already invoke the kit CLI in module form.
- **CORRECTLY ABSENT (2).** The machine-specific runner parenthetical on the lint call, same rule as
  above.
- **SUPERSEDED / re-wrap (7).** Four description lines and two Step-1 lines fail an exact match only
  because the kit **inserted new sentences into the middle of them** — the ledger-lifecycle summary
  in the description, and the hot-file / DORMANT-skip qualifications in Step 1. The seventh is
  `### Step 7: Verify`, which the kit renumbered to Step 8 when it added archive rotation as the new
  Step 7. Every one of these is a line the kit is *ahead* on.

**This is the result the measurement predicted, now measured.** Worth stating plainly: a 90% that
resolves entirely to substitutions, insertions and a renumber is a different fact from a 90% nobody
opened.

### `session-retrospective` — 9 lines, one recovery

- **ALREADY REPOINTED (3).** Three separate call sites of the unshipped linter's intake-count mode —
  the pipeline-health data sources, the sibling-cadence step, and the report template — all already
  point at the kit CLI's list mode.
- **RECOVER (1).** The pipeline-health rule lost half a sentence in the repoint: the kit kept *"one
  markdown table, not a dashboard"* and dropped *"not a new JSON artifact"*. Both halves are generic
  anti-scope-creep, both are restored. Small, but it is the exact shape this program keeps finding —
  a clause lost inside an otherwise-correct edit, invisible to a per-file diff.
- **CORRECTLY ABSENT (2).** Two backwards-compatibility notes name a skill ruled out of the port
  (OP-5). The kit **generalised rather than deleted** them — both now read "any downstream analysis
  skill", so the compatibility promise survives without the coupling. This is the right pattern and
  it was already applied.
- **SUPERSEDED / re-wrap (3).** Two lines the kit inserted into (the sub-agent deep-dive gained the
  `emittedBytes`-not-`bytes` guidance mid-paragraph; the cadence step gained the repointed call), and
  one schema example the kit **extended** with an additional key.

## Unsettled

- **The source project's directory layout is shipped across 8 skills in 12 files** — counted, not
  estimated: `analyze-logs`, `learning-consolidator`, `post-task-review`, `python-conventions`,
  `spec-driven-dev`, `stacked-pr-planner`, `vertical-slice`, and `task-learnings` itself. The
  subsystem row was recovered path-free here, per the adjudication; but `learnings-format.md`'s own
  drains-to-homes bullet still names that layout, two lines below the path-free row this batch just
  added. **No test bans the shape**, so this is a fleet-wide convention, not a defect in one file,
  and unilaterally diverging a single skill from it would trade one inconsistency for another. Left
  as recorded, not fixed: it needs a fleet decision, and the fleet is the right unit for it.
- **The measurement's first-pass call for `task-learnings` was close but not line-exact.** It listed
  "the named legacy section headers" as correctly absent; those headers are in fact **shipped**
  verbatim and were never absent. It also counted two dated internal citations where the diff
  contains one. Neither changes a verdict — both were pre-adjudication notes the record explicitly
  labelled "a first pass, not a verdict" — but it is the reason every line was re-read rather than
  executed from the summary.
- **`status` stays `"unreviewed"`** in the sync manifest. This batch does not own that flip, and one
  skill of the seven — `test-conventions`, in the python pack — is still outstanding. With the two
  0% skills already paid and these three, 75 of the 92 measured lines are adjudicated.

## Gates

Full suite 249 passed / 6 skipped; `audit-skills --fail-on major` reports 0 findings over a fleet of
38. Both run after the edits, before the commit — the guard scans this record too, and a session
already pushed red this week by quoting a banned pattern as an example. Nothing here is quoted
verbatim that the contract bans; where a banned shape had to be discussed it is described instead.
