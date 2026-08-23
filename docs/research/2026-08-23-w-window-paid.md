# W-window paid — carriage 11% to 84% across the funded six, and the pin that could not see it

**Dated:** 2026-08-23.
**Pays:** the debt measured in
[2026-08-23-extraction-window-debt-measured.md](2026-08-23-extraction-window-debt-measured.md)
and its [completion review](2026-08-23-extraction-window-debt-completion-review.md), scoped by
program doc §5f items **W-1** (fund six skills), **W-2** (close the vocabulary-pin blind spot)
and **W-3** (restore `EXPERIMENT-REGISTERED`).
**Method:** three-way re-merge against each skill's own extraction base, per file, not
hand-restore. Bases taken from
[2026-08-23-per-skill-extraction-base.md](2026-08-23-per-skill-extraction-base.md) and
re-verified here.

---

## 1. The answer

Carriage of window content across the six funded skills plus `ai-changelog`:

| Skill | Window lines | Carried before | Carried after | Absent now |
|---|---:|---:|---:|---:|
| `skill-creator` | 125 | 1 | **117** | 8 |
| `learning-consolidator` | 170 | 40 | **146** | 24 |
| `skill-reviewer` | 110 | 3 | **98** | 12 |
| `python-conventions` | 58 | 6 | **38** | 20 |
| `skill-creation-workflow` | 50 | 0 | **44** | 6 |
| `ai-improvement-tracker` | 53 | 11 | **42** | 11 |
| `ai-changelog` (W-3) | 23 | 2 | **8** | 15 |
| **Total** | **589** | **63 (11%)** | **493 (84%)** | **96** |

**The denominators reconcile with the measuring session.** Its per-skill window counts were
170, 110, 58, 53 and 23 for five of these; this run returns 170, 110, 58, 53, 23 — exact. Two
differ by one line (`skill-creator` 125 vs 124, `skill-creation-workflow` 50 vs 49), which is a
tie-break difference in opcode attribution, not a disagreement. That agreement on the
denominator is what makes the numerator worth reading.

**Restated on substantive lines only, which is the figure that survived review:** dropping every
line of 25 characters or fewer and every pure table/fence line from **both** sides gives
**45/540 (8%) — 444/540 (82%)**. The measuring session's review warned that a *carried* count
built from positive matches on short strings is the weak half of such a pair, so the same test
was turned on this run's own headline. It moves the result by two points. Filtering only the
numerator gives a misleading 75%; the honest comparison filters the denominator too.

**The 96 still absent are accounted for, all 96 classified** — see §5. That is the first
actual measurement of the portable / correctly-stripped split the measuring session left open,
and it found **zero accidental losses** in these seven skills.

## 2. W-3: the premise was right, and the recorded reason for the drop was circular

`checks.py` carried this claim, written 2026-08-23 09:29 in the CLI-substitution commit:

> Three upstream rules were deliberately dropped rather than ported, because each encodes that
> project's policy [...] and a 12th changelog type added by one of its decision records.

That reads as a ruling, and it would have made W-3 a reversal of a ratified decision. It is not.
The timeline refutes it:

| When | What |
|---|---|
| 2026-07-02 23:26 | kit extracted (`002dadd`). Shipped table: **11** rows, "the 11 change types above are a closed set" |
| 2026-07-03 15:55 | upstream ADDS `EXPERIMENT-REGISTERED` — **17 hours after** extraction |
| 2026-07-06 | `c05bf72d`, the base the refresh later used. The type is present here |
| 2026-08-23 | refresh merges against `c05bf72d`: present at base, absent in ours, present in theirs → "deliberate kit deletion" → kept deleted |
| 2026-08-23 09:29 | the comment above is written, reasoning that the lint should enforce what the shipped skill teaches |

The shipped skill taught 11 **because the type arrived after extraction and no refresh had yet
carried it**. So the comment explains an artifact with a rationale, and the rationale then
protects the artifact. Against the true base `3dd2496d` the same member reads as what it is: an
upstream addition to carry.

The two other dropped rules — a hardcoded 2026 policy cutoff and a name-matched allowlist of the
source project's own historical entries — are genuine policy. A taxonomy member whose rule is
"a registered measurement experiment must pair with a dated, falsifiable hypothesis carrying a
re-eval date" is not, and this kit ships the hypotheses machinery that rule pairs with. Restored;
only its dated source-project template citation was stripped. The comment is corrected in place,
including how it went wrong, because the failure mode is more reusable than the fix.

## 3. W-2: the pins measured consistency, and now something measures fidelity

All five vocabulary pins assert *shipped document == kit constant*. Both operands come from this
tree, so a refresh that drops a member from the document **and** from `checks.py` leaves every one
of them green. Five new tests add the third operand, reading upstream at the pin.

**All four mutation-tested, because a detector's only interesting property is that it can fail.**
Each had a member removed from its kit-side constant; **4/4 went red and each named the missing
member.** Three of the four had never failed before that, which is the same defect class this
section exists to close — an untested detector is a claim, not a check. For changelog
types the mutation reproduces the original defect exactly, so the two pins can be compared
directly:

| Test | Result under the mutation |
|---|---|
| `test_changelog_types_match_the_shipped_skill` (existing pin) | **PASSED** — the blind spot, reproduced |
| `test_upstream_changelog_types_are_all_carried` (new) | **FAILED** — names the member |

Design decisions worth stating, because each is a way this could have been useless:

- **It skips without an upstream checkout.** Upstream is private and its location is deliberately
  not recorded in this repo, so a contributor's clone and CI both skip these cleanly —
  verified: `6 skipped`, counting the pre-existing upstream test. A fidelity check that is honestly skipped beats one that is red for
  everyone who cannot run it.
- **The assertion is one-sided.** The kit is allowed to be ahead of upstream and is. What it may
  not be is silently *behind*: an upstream member must either ship here or be named in
  `_DECLARED_VOCABULARY_DIVERGENCES` with a reason. That table is empty on purpose — at this sync
  every member upstream defines is carried — and its comment says that an entry is a claim, and
  points at `EXPERIMENT-REGISTERED` as the reason such a claim needs scrutiny.
- **The hand-off parse had to be rewritten.** The first version derived upstream's candidate
  sections by filtering `checks.HANDOFF_REQUIRED_SECTIONS`, which makes the assertion pass by
  construction — upstream could add a sixth required section and it could never see it. That is
  the same defect one level down, written while fixing it. It now parses `` `## X` `` out of
  upstream's own text, so the parse can return something the kit lacks.
- **It reads bytes, not `text=True`.** `_git` in `tests/upstream_sync.py` decodes through the
  locale codec. For commit counts that is fine; for prose tables on a Windows console it is the
  defect that once turned 14 rewritten lines into 176 phantom dropped ones. The new
  `read_upstream_file` decodes UTF-8 explicitly and says why in its docstring.

At the pin all five vocabularies are now at parity: changelog types 12=12, hypothesis categories
7=7, learnings sections 7=7, hand-off sections and statuses all present. Before W-3 the first row
read 12 vs 11.

## 4. Bases: verified per file, and the probe's method has a flaw worth recording

The funded six needed no re-probe under the brief's rule — none of them is among the five rows
marked untrusted at 1.0–1.2x separation. They were verified anyway, per file, because the base is
the one operand that makes or breaks a re-merge.

**All 15 files: distance at the recorded base == global minimum over every upstream revision that
touched the file.** No contradictions. `ai-improvement-tracker`'s non-default base `03a10499`
(2026-03-29) confirms at 2 against a global minimum of 2.

**But the minimum-distance method has a tie ambiguity the base document does not name.**
`git log -- <path>` lists only commits that *touched* the path, so a file unchanged across a range
scores distance 0 at every revision in that range and the "winner" is whichever SHA the sort
happens to return. Probing `skill-creator/references/skill-patterns.md` this way returns
`f8ffbab6` (2026-03-15) at distance 0 with the runner-up 64 lines away — which looks like a
far stronger result than the `3dd2496d` the document records for that skill, and is not a
disagreement at all: the file simply did not change between the two. What a three-way merge
consumes is the base **content**, not the SHA, and `git show <rev>:<path>` resolves for any
revision whether or not it touched the file. Measuring content at the candidate removes the
ambiguity entirely. Five rows in that table are marked untrusted on separation; this is a
different failure, and it can make a *trusted* row look wrong.

## 5. What is still absent, and why — the split the measurement left open

96 lines, **all 96 classified** rather than sampled: **52 carried in reworded or re-wrapped
form** (best fuzzy match against the shipped skill at 0.60 or better), **30 deliberate strips**
matched to a named banned pattern or source-project marker, and **14 continuation lines of
blocks in that second group** — a marker landed on a block's first line and not its tail.
Reviewing those 14 by hand leaves **zero accidental losses**. One of them is worth naming
because it inverts: upstream's *"handles cleanup by changing statuses and optionally archiving
resolved entries"* is absent because the kit says it better — it names the archive file and
the rotation step
(`ai-improvement-tracker/SKILL.md` § File Size Management). Superseded, not lost.

**Deliberate strips (the large majority).** Named source-project test files
(`tests/integration/features/feedback/...`), module paths (`core/subscription/...`,
`features/realtime_interview/...`, `backend/app/core/{module}/README.md`), decision-record
provenance (`Project policy (2026-06-21)`, `Project position (D2, 2026-07-02)`, `project D1
policy`), dated project incidents (the 06-11/06-12 heading disorder, the 2026-07-16 drain's
`ShutdownRunContext`), an unverifiable org claim ("feedback from 10+ engineers"), machine rules
(one naming this host's interpreter policy, quoted verbatim in the measured-debt record),
the two unshipped linters, and one whole section
(`Decorator-Extracted Route Dependencies`) built entirely from source-project internals whose
transferable rule the surrounding bullets already carry.

**Re-wrapped, not lost.** Several lines report absent because an exact-line match is
whitespace-sensitive. Spot-checked three that looked like real losses; all three are carried:
`learning-consolidator/SKILL.md:382` holds the hypothesis-window rule upstream wraps differently,
`:120` and `:129` hold the `.ai/retrospectives/` cross-link.

**One line where the kit is right and upstream's window content was stale.** Upstream at
`c05bf72d` says the canonical learnings category set is "exactly six". There are **seven**, and
upstream itself fixed this later — the pin has 7. The kit drops the count rather than the
sentence. Restoring that line would have shipped a wrong number.

**One thing upstream has that the kit now has a caller for and still does not ship.**
`skill-creation-workflow/references/subagent-preamble.md`, 25 lines. The measuring session put it
out of scope (it is in the 901 lines "in files the kit ships no version of at all"), so the two
`{paste references/subagent-preamble.md VERBATIM}` instructions the merge would have carried were
dropped rather than pointed at a missing file — an instruction to paste a file that does not exist
fails silently, which is worse than the absence. It is a genuine mixed file: roughly half is
machine-specific (a console-encoding environment variable, `/tmp`, a "Host" preamble, a dated
retrospective citation),
and the rest is portable and good — never `git stash` in a shared tree, WebFetch summaries
fabricate figures, your final message is a claim and not verification. **Owed, sized: ~12 portable
lines, and it is the only window content with a live caller in the shipped pack.**

## 6. Findings outside the task

**The pack-boundary guard cannot see a line-wrapped name.** `tests/test_pack_boundaries.py`
scans for contiguous `python-conventions` / `test-conventions`. In `skill-reviewer/SKILL.md` the
working tree carried `python-` on one line and `conventions` on the next, inside an ASCII box
diagram — `"python-conventions" in text` returns **False** while the reference is fully present to
a reader. Measured directly at lines 309–310 before this merge. It is gone now, because upstream
retires that diagram in favour of a pointer to AGENTS.md and taking upstream's side removed it;
the guard's blind spot did not cause the fix and is not closed by it.

**A shell-quoting defect that produces a confident, plausible number.** Same file, same instant:

```bash
grep -c $'\r$' "$F"                                     -> 0    (exit 1)  CORRECT
printf "%s" "$(grep -c $'\r$' "$F" 2>/dev/null||echo 0)" -> 176            WRONG
```

Nested inside a double-quoted `printf` argument the pattern degrades to match-every-line, so the
count equals the file's line count. It is not that `$'\r$'` is broken — bare, it is correct. The
tell is structural and worth more than the instance: **a count that exactly equals the line count
is a match-everything pattern, not a measurement.** On an all-CRLF file the broken form and the
right answer agree, which is what sold it.

**CRLF/LF asymmetry defeats a three-way merge silently.** The working tree is CRLF
(`core.autocrlf=true`, no `.gitattributes`); `git show` yields LF. Merging those directly makes
every line differ by a trailing `\r`, and `git merge-file` returns one whole-file conflict per
file — which reads as "these files are 100% divergent" rather than as an encoding artifact. All
seven files did this on the first run. Normalising all three operands to LF took
`skill-creator/SKILL.md` from one whole-file conflict to two real, localised ones. Route every
operand through the same writer.

## 7. Scope discipline — what was declined

- **`docs/upstream-sync.toml` was not touched.** Its `[extraction_window] status` should move off
  `"unreviewed"` and that is owed work, but the file is inside another concurrent session's
  declared path set and was already modified there. Handed over with the exact value rather than
  edited into a conflict.
- **No `docs/research/README.md` row.** That file is deliberately prose with no per-file index, so
  the measuring session's owed item #2 has nothing to add a row to. Naming that rather than
  inventing a table.
- **`task-learnings` was not touched.** It is the row that contradicts the mechanism (66% carriage
  where its exposed peers were near zero, with the measuring session's pinning-test explanation
  tested and refuted). It is outside the funded six and remains unexplained.
- **The seven remaining exposed skills were not touched** — 91 lines between them, ~13 each, ruled
  not worth a session.
- **`learning-consolidator/scripts/drain_audit.py` was checked, not merged.** Absent at the base
  and present at the pin, so the harness skipped it; diffing kit against upstream shows the kit
  strictly ahead — `${CLAUDE_SKILL_DIR}` for the script path, generic `src/**` globs with an
  adjustment note, a plugin-safe `repo_root()`, and no Windows-host rule. Verified rather than
  assumed.

## 8. One thing this run changed that was not a merge

`learning-consolidator/SKILL.md` came out of the merge at 524 lines against the pack's 500-line
cap, a MAJOR audit finding and an `--fail-on major` gate failure. Rather than lose the recovered
content, three blocks moved into `references/consolidation-actions.md` behind pointers — the
section-placement audit, the parked-pattern verification rule, and the `PROMOTE_TO_SKILL`
execution procedure, which joins the criteria for that same action already in that file. Final:
SKILL.md 481, reference 484, audit `0 finding(s)`, exit 0. The dated `ShutdownRunContext` incident
was genericised on the way rather than carried into the reference.

## 9. Limits

- **Line-level, not semantic.** §5's "re-wrapped, not lost" rests on three spot-checks, not on all
  of the re-wrapped lines.
- **The 84% is carriage, not correctness.** It says upstream's window lines are present; it does
  not say the merged documents read well. `skill-creator/SKILL.md` grew 66 lines and no human has
  read it end to end since.
- **`ai-changelog`'s 35% is the lowest row and is expected.** Its window content is
  disproportionately the unshipped linter's invocation and dated project history; the taxonomy
  member that motivated W-3 is carried.
- **The tree was moving under this work.** Four concurrent sessions plus a Codex session writing
  in the same checkout, which ran `git restore` on two of these six skills once. Every measurement
  here is timestamped in the session log; the four-check gate below was run at 19:23:58.
- **No test guards the carriage numbers.** §1 lives in this document. W-2's four tests guard the
  vocabularies against upstream, which is a different and smaller claim.
- **`ruff format --check .` exits 2 on this tree** for an unrelated reason: a concurrent session
  holds `.pytest-tmp/` and ruff cannot read it. With `--exclude .pytest-tmp` it is exit 0. Anyone
  reporting this gate must say which they ran.

## 10. Gate

Run at **19:23:58**, with `LEMMI_UPSTREAM_REPO` set so the new fidelity tests execute rather than
skip:

| Check | Result |
|---|---|
| `ruff check` | All checks passed |
| `ruff format --check` | 18 files already formatted |
| `basedpyright` | 0 errors, 0 warnings, 0 notes |
| `pytest` | **190 passed** at that time; **196** at close |
| `audit-skills --fail-on major` | 0 findings, exit 0 |

The 190 attributes exactly: the recorded baseline is 185 passed / 1 skipped; setting
`LEMMI_UPSTREAM_REPO` converts the pre-existing skipped upstream test to a pass (186), and these
four fidelity tests bring it to 190. A 19:28:28 run returned 193 — the extra three are another
session's, landed in the interval.

### 10a. The restructure landed at 19:29, and the suite is transiently red for reasons outside this work

Between the 19:28:28 run (193 passed) and 19:29:32, the I4 restructure moved the skills tree out of
`src/lemmi_ai_kit/assets/skills/` into `plugins/core/skills/` and `plugins/python/skills/`. The
suite is now `11 failed, 175 passed, 7 errors` — `load_manifest()` and `assets_root()` still
resolve the old path, which is the restructure's own remaining work in another session's declared
files (`manifest.py`, `manifest.toml`, `test_manifest.py`, `test_scaffold.py`). **None of it is
this work, and none of it is fixable from inside this scope.**

What was verified rather than assumed, at 19:30:28:

- **All 13 merged skill files survived the move with content intact**, checked by content marker
  in the new location — not by trusting that a move is a move. `skill-creator`,
  `skill-creation-workflow`, `ai-improvement-tracker`, `ai-changelog`, `skill-reviewer`,
  `learning-consolidator` under `plugins/core/skills/`; `python-conventions` under
  `plugins/python/skills/`.
- **Zero banned-pattern hits** across all seven skills re-scanned at the new paths.
- **The new fidelity tests still pass** post-move, because their kit-side operand is a
  constant in `checks.py` rather than a file path.
- **The three existing pins that read `assets_root() / "skills"` fail** for exactly that reason.

That contrast is worth keeping: the pins this document adds are indifferent to where the skills
tree lives, and the pins it did not touch are not. It also settles W-1's stated reason for
sequencing W-window before the restructure — *"content edits survive a path move cleanly"* — as
measured rather than predicted. The content did survive; it was the path-dependent tests that
broke.

**Verified byte-for-byte, not by inspection.** SHA-256 of all 13 merged files, pre-move backup
against the post-move tree: **13 identical, 0 changed.** A move and a move-plus-rewrite are
indistinguishable by eye in this tree, so they were hashed.

### 10b. The three pins were repointed, because the hardcoded path was in this document's own file

`checks.py` resolves nothing — every audit entry point takes `skills_dir` as a parameter. The one
hardcoded tree path was `_SKILLS = assets_root() / "skills"` in `tests/test_checks.py`, which is
this work's file, so leaving it red would have meant leaving a red test in a file already dirty
under this session and inviting a collision on it.

The pins now resolve each skill through `manifest.shipped_skill_dirs()`, by **name** rather than by
tree path. That is the better shape independent of the restructure: a pin on the changelog taxonomy
should not go red because `ai-changelog` changed pack, and it should survive the next move without
an edit. `tests/test_checks.py`: **113 passed**, from 3 failed.

This was outside W-1/W-2/W-3 and is named rather than folded in. What was **not** done: the other
seven failures, all in files belonging to other sessions —
`.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` are tracked but no longer on disk (so
the license and publication-hygiene tests fail on a missing file, not on a hygiene defect),
`test_assets`, `test_cli`, `test_scaffold` and `test_upstream_sync` resolve the old tree.

### 10c. RESOLVED: the restructure briefly moved the shipped skill scripts into the lint surface

A consequence that has not been noticed by the sessions doing the move: `pyproject.toml` excludes
`src/lemmi_ai_kit/assets` from `basedpyright`, and the skill scripts were inside it. Under
`plugins/` they are not excluded from **ruff**, and `ruff format --check .` now wants to reformat
four shipped skill scripts — `drain_audit.py`, `audit_cleanup_targets.py`,
`sweep_user_corrections.py`, `test_extract_sessions.py`. `basedpyright` still passed only because
its `include` was `["src", "tests"]`. The repo's own formatter would have rewritten pack content
meant to ship as authored.

**Fixed by the restructure session after this was raised, and re-verified here at 19:56:**
`pyproject.toml` now carries `extend-exclude` and a matching `basedpyright` `exclude` for
`plugins/core/skills`, `plugins/python/skills` and the assets tree. `ruff check --show-files`
returns 19 files, **none of them under a skills tree**. Recorded as resolved rather than deleted,
because the failure mode generalises: **a lint or type-check exclusion is written against a path,
so every tree move silently changes what is checked** — in either direction.
