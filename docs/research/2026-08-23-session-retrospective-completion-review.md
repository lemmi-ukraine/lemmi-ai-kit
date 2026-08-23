# `session-retrospective` reconciliation — self-challenge and completion review

**Dated:** 2026-08-23, at the end of the session that merged the skill to schema v4.
**Reviews:** [2026-08-23-session-retrospective-reconciliation.md](2026-08-23-session-retrospective-reconciliation.md).

---

## 1. The structural failure: I verified a command the developer's way, which is the defect I was removing

The merge pulled in upstream call sites naming `ai_files_lint.py` and `audit_skills.py`, which this
kit does not ship. I rewrote five of them to
`PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit <sub>`, then verified by running the
commands. They worked. Exit 0, real output.

**The test was worthless.** The shell resolved bare `python` to
`.venv/Scripts/python` — the development venv, where `lemmi_ai_kit` is installed *and*
`lemmi-ai-kit` is on `PATH`. That environment satisfies **every** form of the invocation, including
the console-script form the handoff's §6 had just deleted from 16 call sites for being unreachable.
Had I written the broken form, the test would have passed identically.

This is §6's own transferable rule — *check a named command against the install path the adopter
actually uses, not the one the developer has* — violated in the act of checking a named command. The
defect class survives being documented; it is a property of the default `PATH`, not of anyone's
attention.

**Re-run with controls,** on `Python313\python.exe` outside the venv:

| Probe | Result |
|---|---|
| `import lemmi_ai_kit` (no `PYTHONPATH`) | `ModuleNotFoundError` — the interpreter is genuinely clean |
| `lemmi-ai-kit lint learnings` (console script, §6's deleted form) | `No such file or directory` — the control has discriminating power |
| `PYTHONPATH=<kit>/src python -m lemmi_ai_kit lint learnings --list-entries` | **exit 0**, entry inventory printed |
| `PYTHONPATH=<kit>/src python -m lemmi_ai_kit audit-skills` | **exit 0**, fleet audit printed |

Both forms I wrote are reachable. The claim now rests on a test that could have failed.

**Generalisable:** a reachability test with no failing control is not a test. Before believing one,
run the form you believe is broken and confirm it breaks.

## 2. Two measuring tools that returned confident nonsense

Both were caught by the shape of the number, not by inspecting the tool.

| # | Tool | Reported | Actual | Tell |
|---|---|---|---|---|
| 1 | `grep -c $'\r' <file>` | every file CRLF | only the working tree is, via `core.autocrlf=true` | the count **equalled each file's line count** — the pattern had collapsed to empty and matched every line |
| 2 | `subprocess.run(diff, text=True)` | **176** upstream lines dropped | **14** | nearly every "dropped" line contained an em-dash — Windows decoded UTF-8 with the locale codec |

Tool 2 mattered. 176 dropped lines out of 1,336 would have read as a merge that discarded 13% of
upstream's advance, and the fix for a phantom would have been to re-merge. Re-run with `difflib` and
explicit `encoding="utf-8"`: 1,322 verbatim, 14 rewritten, **0 dropped**, and all 14 are my own
portability substitutions.

Same failure family as the base error this session existed to fix: **the instrument was wrong, and
its output was plausible.**

## 3. A finding I nearly filed against correct code

`--check-file` — the v4 report-privacy gate — returned `PASSED` on a file containing
`OPENAI_API_KEY=supersecretvalue123456`. Written up, that is "the leak gate misses API keys."

It is wrong. Importing the module rather than reasoning about it shows two deliberately different
sets: `LEAK_PATTERNS` (**6** high-confidence shapes — `sk-`, JWT, `AIza`, `AKIA`, PEM,
`"private_key"`) is the *gate*; `REDACTIONS` (**16**) is the *scrubber*. The key shape is redacted
but deliberately out of gate, because a generic `KEY=value` matcher would false-alarm on ordinary
prose. The extractor says so in a comment, and the schema doc I had just merged says so too.

Confirmed working in both directions: in-gate shape → `CHECK-FILE FAILED`, **exit 3**, pattern named.

Cost of the reflex: one import. Cost of skipping it: a false security finding against a correct gate,
in a document whose whole authority rests on the last one being right.

## 4. What held under challenge

| Claim | How it was re-checked |
|---|---|
| True base is `3dd2496d`, not `c05bf72d` | Three independent routes agree: minimum-distance across **all five** files (9 diff-lines vs 271 next-closest for the extractor); upstream's v4 commit dated 2026-07-05; the kit's first commit dated 2026-07-02 |
| "~1,100 words" is not a removal | The kit-side edit set against the true base is **4 hunks / ~13 words**, every one a documented extraction category |
| §5's baseline of 15 tests | Re-ran the shipped v3 pair in isolation: **15 passed** — quoted figure independently confirmed |
| Merge kept both sides | 29 kit-side edits across four files: **27 survived verbatim**; 1 is a line-join from my own conflict resolution (the phrase survives), 1 is the deliberate `report-template` choice in §5 below |
| Nothing structural dropped | Upstream's and the final file's `SKILL.md` heading sets are **identical** |
| v4 actually works, not just compiles | End-to-end on **15 real transcripts**: `schemaVersion 4`, `deepDiveCandidates` 8 selected / 4 over cap, `slashCommands` captured, `models` populated (`claude-opus-5`, `claude-sonnet-5`), `compactions` counted, `stats.skillInvocationModes` = `{'model': {'user': 2, 'model': 0}}` — the capture that was invisible before v4 — and `SELF-CHECK PASSED` |
| New references resolve | `.ai/improvement-hypotheses.md` and `.ai/ai-changelog.md` are scaffold-seeded; `tasks/TECH-deferred-consolidation-*` is established vocabulary in `consolidation-critic` and `learning-consolidator`, not something I introduced dangling |
| Guard scan honest | Ran the **imported** `_FORBIDDEN`/`_ASSET_ONLY_FORBIDDEN` with the real `_ALLOWLIST`; the 5 residual hits are the pre-existing allowlisted fixtures, and all 6 merge-introduced hits are fixed |

## 5. Judgment calls, stated as judgment rather than measurement

- **`report-template.md` effect-join row.** Upstream's example reads `Rule since 2026-06-25`; the
  kit's read `Partial — learnings {date}`. I took upstream's richer column (it teaches the
  covered-since + post-date-occurrences + escalation verdict) with the kit's `{date}` placeholder.
  **No guard forced this** — no pattern matches a bare date in a table cell. It is an editorial
  choice for consistency with the template's other placeholders, and it is the one kit-side line
  deliberately not carried verbatim.
- **`sweep_user_corrections.py` ported rather than dropped.** §7 assigned only the portability
  *read*. Dropping it was available and would have left `SKILL.md`'s §4e naming an unshipped
  script — the §6 defect. I ported it, generalising one dated source-project incident in the kit's
  established idiom. It ships in the wheel and runs with no `.git`/`.ai` ancestor. **It has no
  tests** — upstream ships none either, so this is inherited, not introduced.
- **`interview-transcript-analysis` → "any downstream analysis skill."** The kit does not ship that
  skill. Generalising keeps upstream's compatibility claim true instead of pointing at nothing.

## 6. Did the task meet its Definition of Done?

| # | Criterion (from the kickoff and §5) | Verdict |
|---|---|---|
| 1 | Read §5 before writing anything | **pass** — and it inverted the task: the premise was measurement error |
| 2 | Characterise the ~1,100-word removal *before* any merge | **pass** — done first; result is that it does not exist, written up in §1 of the reconciliation |
| 3 | Three-way merge against the extraction-point base, not overwrite-then-clean | **pass** — `git merge-file` against `3dd2496d`; the extractor merged with **0 conflicts** |
| 4 | Neither side's changes discardable | **pass** — 99.0% of upstream carried verbatim, 0 dropped; 27 of 29 kit edits verbatim, both exceptions accounted |
| 5 | Own `session-retrospective/**` and nothing else | **pass** — `git status` shows my writes confined to that directory plus two new `docs/research/` files |
| 6 | Do not loosen the vocabulary-pinning tests | **pass, vacuously — and worth knowing why.** Those tests pin `ai-changelog` and `task-learnings` vocabularies, **not** this skill's error taxonomy. The kickoff expected them to be the drift alarm here; they are not wired to this skill, so green is not evidence the taxonomies are unchanged. Verified separately: `ERROR_CATEGORIES` is untouched |
| 7 | Whole skill moves together (script + both reference docs) | **pass** — `SCHEMA_VERSION = 4`, `schemaVersion: **4**`, and `schema v4` throughout `SKILL.md` |

## 7. Limits that remain

- **`SKILL.md` was not human-read end to end** (493 lines). Confidence is mechanical: 2 conflicts,
  identical heading sets, the carry audit, the guard scan. A prose regression that is
  syntactically clean and portable would not have been caught.
- **The Python 3.11+ floor is asserted, not tested.** The doc derives it from
  `from datetime import UTC`; I ran only on 3.11 (venv) and 3.13 (clean). No 3.10 run proves the
  failure mode.
- **`sweep_user_corrections.py` is untested** — smoke-run only (one synthetic transcript, correct
  hit, correct skip).
- **Item 6 above is the honest gap in the DoD**: the change is *believed* taxonomy-neutral on the
  strength of a diff, not enforced by any test. If this skill's `ERROR_CATEGORIES` deserve a pin
  like the other three vocabularies have, that pin does not exist and this session did not add one.
- **The reconciliation doc's §6 asserts the W2.4 pin is wrong** for this skill. That is my
  measurement applied to another session's in-progress file, which moved twice while I worked
  (`docs/syncing-from-upstream.md` and a CI change appeared mid-review). It should be re-read at
  its committed state before being acted on.
