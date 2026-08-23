# `session-retrospective` reconciliation — the ~1,100-word removal does not exist

**Dated:** 2026-08-23. **Task:** the D-retro item from
[2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md](2026-08-23-i2-port-and-refresh-handoff-to-orchestration.md) §5.
**Outcome:** the skill is merged to schema v4 and shipped. The blocking premise was measurement error.

---

## 1. The finding, first

§5 required, before any merge: *"diff the extraction-point extractor against the shipped one and
write down what those ~1,100 words were and why they went."*

Done. **The answer is that they were never removed.** The kit's shipped extractor is upstream's v3
file with **four edits totalling ~13 words**. The ~1,100-word gap is an artifact of comparing
against a base four days newer than the file the kit actually extracted.

| Fact | Measured |
|---|---|
| Kit's first commit (extraction) | `002dadd`, **2026-07-02** |
| Upstream file state at that moment | `3dd2496d` (2026-06-25), `SCHEMA_VERSION = 3` |
| Upstream added schema v4 | `0ff80065`, **2026-07-05** — *three days after the kit extracted* |
| Base the refresh used for every skill | `c05bf72d` (2026-07-06) — **already contains v4** |

Diffing `c05bf72d` → shipped therefore renders the entire v4 feature set as a kit *deletion*:
1,211 → 970 lines, 4,584 → 3,453 words. That is the "~1,100 words". It is upstream content the
kit never had, not content the kit dropped.

**The kit's actual edit set against its true base** (`3dd2496d` → shipped: 4 hunks, 5 lines removed,
4 added) is entirely the documented extraction categories:

| # | Edit | Category |
|---|---|---|
| 1 | `/tmp` note: "Git Bash and Python … on Windows (see `.ai/learnings.md` 2026-03-28)" → "shells and platforms resolve `/tmp` inconsistently" | platform note generalised + dated citation |
| 2 | "a 137-agent fan-out" → "a large fan-out" | source-project measurement de-specified |
| 3 | redaction comment: dropped "(See `.ai/learnings.md` 2026-06-22.)" | dated citation |
| 4 | `_encode_repo_path` comment: dropped "See `.ai/learnings.md` 2026-06-22." | dated citation |

Nothing else. There is no uncharacterized removal to account for.

## 2. Why the first attempt failed — and why that was not the file's fault

§5 reported the reverted merge as evidence that this file is non-mechanical: 13 conflicts all
resolving to "take upstream", 1,400 lines against upstream's 1,547, 8 of 35 tests failing, with
`DEEP_DIVE_*` / `PRESCAN_*` constants absent while their function bodies landed.

That symptom is the precise signature of the wrong base, not of a difficult file:

- The v4 constants exist in `c05bf72d` and are missing from the kit, so the merge reads them as
  **"ours deleted these"** and honours the deletion.
- Later upstream commits *modified* the function bodies that read those constants, so those hunks
  conflict, resolve to "take upstream", and **land**.
- Result: new bodies without their constants — exactly what was observed.

The merge was never insufficient. It was correct arithmetic on a wrong operand.

**This is the same failure §4 of the handoff names** — a two-way diff cannot distinguish an upstream
advance from a deliberate kit removal — reappearing one level down: the *base itself* was picked
by a repo-wide rule, and for this skill the rule is wrong. §4 predicted "two entries need a
per-skill base override"; this is a third, and it was misread as a content problem instead.

## 3. What the corrected merge produced

Base `3dd2496d`, ours kit `HEAD`, theirs upstream `a78ee5af`. Empirically confirmed as the true base:
for **all five** files it is the minimum-distance upstream revision by a wide margin
(extractor: 9 diff-lines vs 271 for the next-closest).

| File | Conflicts |
|---|---|
| `scripts/extract_sessions.py` | **0** |
| `scripts/test_extract_sessions.py` | **0** |
| `references/extractor-output-schema.md` | **0** |
| `SKILL.md` | 2 |
| `references/report-template.md` | 1 |

Three prose conflicts, hand-resolved to keep both sides. Against §5's 13.

**Tests:** 35 passed (v3 baseline 15; the reverted attempt 8 failed / 27 passed). Every item §5
listed as absent — `check_file`, slash-command capture, `compact_boundary` counting, the
`DEEP_DIVE_*` and `PRESCAN_*` constants — is present with both its definition and its uses.

**Carry audit** over the 1,336 lines upstream added since the true base: **1,322 carried verbatim
(99.0%), 14 carried rewritten, 0 dropped.** All 14 rewrites are the portability substitutions in §4
below.

**Schema coherence:** `SCHEMA_VERSION = 4` in the script, `schemaVersion: **4**` in the schema
reference, `schema v4` throughout `SKILL.md`. §5's "the skill moves whole or not at all" is satisfied.

## 4. Portability work the merge required

Upstream's advance introduced **8 references the kit cannot satisfy** — none present in either the
base or the shipped file, so all merge-introduced. Six tripped the DoD-4 asset guards; all are the
§6 defect class (naming something the adopter's install path does not provide):

| Site | Was | Now |
|---|---|---|
| `SKILL.md` ×3, `report-template.md`, `extractor-output-schema.md` | `ai_files_lint.py` | `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit lint learnings --list-entries` |
| `SKILL.md` | `audit_skills.py` | `… python -m lemmi_ai_kit audit-skills` |
| `SKILL.md`, `extractor-output-schema.md` | `.claude/skills/<name>/scripts/…` | `"${CLAUDE_SKILL_DIR}/scripts/…"` |
| `extractor-output-schema.md`, `extract_sessions.py` | names `interview-transcript-analysis` as a live consumer | "any downstream analysis skill" (the kit does not ship that skill) |

Consistent with the standing decision that the kit ships neither upstream linter and same-skill
sites use the CLI too.

**`sweep_user_corrections.py` — ported.** §7 left its portability unread and assigned it here. It is
pure stdlib, Python 3.9+, no hardcoded paths, no brand leakage: portable as written. Ported with one
edit in the kit's established idiom — a dated source-project incident ("on 2026-08-07 … the 39
unscanned sessions") generalised, the teaching kept. It ships in the wheel and runs from a path with
no `.git`/`.ai` ancestor. Without it, `SKILL.md`'s §4e full-corpus sweep would have named a script
the kit does not ship — the §6 defect again.

## 5. State

`session-retrospective` is **9,025 → 18,120 words**, 5 → 6 files, schema v3 → v4. Pack total 38
skills (unchanged), ~158,900 words. Four checks green on the full tree: `ruff`, `ruff format`,
`basedpyright`, `pytest` **183 passed, 1 skipped** (148 at the time of the merge; the W2.4 session
added 35 more during the review), plus the skill's own **35 passed**.

**Not committed.** Nothing pushed.

## 6. Consequence for W2.4 — its pin, since corrected

**Resolved during this session.** When first measured, `docs/upstream-sync.toml` (in progress,
another session) recorded `base = "c05bf72d…"` for this skill together with the ~1,100-word removal
as its stated root cause. Both were refuted by §1.

That session has since adopted the finding: the row now reads
`base = "3dd2496d874552d6acaac3de6095abc4ec68c2b0"` with a note explaining the artifact. Their file
was not edited from here.

**One coupling remains.** Their row says the `base` override and the `divergent-both` direction
should be dropped when this reconciliation lands — which is now true, since the skill sits at
upstream `a78ee5af` modulo the kit's portability edits. The merge and that row must be committed
together, or the pin describes a state that no longer exists.

**The generalisable point for W2.4:** a per-skill `base` is not optional metadata. `extraction_base`
is a *default*, and it is too new for any skill extracted before 2026-07-06. The cheap way to find
those is the measurement used here — for each skill, diff the shipped file against **every** upstream
revision of it and take the minimum-distance commit. That is mechanical, needs no judgment, and
would have caught this one before it became a blocked task.

## 7. Where this stops

- **`SKILL.md` prose was not human-read end to end.** 493 lines; confidence rests on the merge
  being 3 conflicts, the carry audit, the guard scan, and the heading-set check (upstream's and the
  final file's heading sets are identical).
- **The 4-hunk edit set is the whole kit-side divergence for the extractor only.** `SKILL.md`
  carried 28 diff-lines against its base — more editorial work, not re-verified line by line here.
- **The taxonomies were not touched**, so the vocabulary-pinning tests were never at risk. Those
  tests pin `ai-changelog` and `task-learnings` vocabularies, not this skill's error taxonomy —
  worth knowing, since the kickoff expected them to be the alarm.
- **Two audit tools lied before they were fixed**, both from Windows text decoding: `grep -c $'\r'`
  collapsed to an empty pattern and "found" CRLF in every file, and a `subprocess(text=True)` diff
  decoded em-dashes with the locale codec, reporting 176 dropped lines where 14 were real. Both were
  caught by results that were too round to be true (a CR count equal to the line count; a drop list
  where nearly every entry contained an em-dash). **Check the tool before believing the measurement**
  — the same reflex that produced §1.
