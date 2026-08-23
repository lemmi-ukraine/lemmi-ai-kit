# D3 — `analyze-logs` genericized, and the orphan closed (2026-08-23)

Closes the last open deliverable on row I-1. Scope was `plugins/core/skills/analyze-logs/**` and
nothing else; the scope held, and the three files this work says should change are named in §5 for
their owners rather than edited here.

Everything below was measured at write time by two independent instruments. Where a number is a
count, the scan surface is printed beside it.

## 1. What shipped

| | before | after |
|---|---|---|
| Scan surface | 7 files / 988 lines | 7 files / 1116 lines |
| Platform mentions (GCP · Cloud Run · Cloud Logging · docker · OpenAI · Realtime API) | **68** | **42** |
| Provider/product vocabulary (OpenAI · Realtime API · VAD · interview · Deepgram · internal field names) | **38** | **0** |
| Platform-named reference files | 4 of 6 | 3 of 6 |
| Relative links resolving | 9 of 9 | 9 of 9 |

The change is 33 anchored string replacements, producing **35 diff hunks across 6 files**, plus one
file deleted and one added. Both figures are derived from the backup→live diff, not from the edit
scripts' own list lengths — see §4.

**42 is the intended floor, not a miss.** The OQ-2 ruling made GCP and Docker *worked examples*,
so the remaining mentions were never meant to reach zero. All 42 were enumerated by `file:line` and
each sits in one of three places: a worked-example file's own title banner, an explicitly paired
"…in a GCP export, …in container output" clause, or content already labelled illustrative. Nothing
normative in the skill's prose now assumes a platform.

## 2. Part 1 — genericization

The load-bearing addition is **`SKILL.md` Step 1a, "Map Platform Fields to Roles"**: a seven-role
table (timestamp, severity, message, service identity, correlation id, latency, event name) with the
GCP and container columns filled in and a blank **Yours** column, plus the instruction to state which
roles are *absent* rather than assume a default. Everything downstream now refers to the role. That
is what makes an adopter on CloudWatch, Loki, ELK, Datadog or journald able to follow the skill —
a banner saying "this is only an example" does not, by itself, tell anyone what to substitute.

Each reference file gained a header saying what it is an example *of* and what to swap. `## GCP Query
Assistance` became `## Querying the Log Platform Directly` — a backend-neutral four-step method with
the GCP file as the worked translation. No platform detail was deleted.

A partial pass had already landed at 18:55 (frontmatter, activation list, format table, Steps 1b/1c/2),
three minutes before the 18:58 measurement that recorded D3 as unstarted. The row was partly started,
not unstarted; this work continued it rather than redoing it.

## 3. Part 2 — the orphan: KEPT, genericized, renamed

`references/realtime-session-events.md` → `references/session-event-streams.md`.

The file was two separable things. The **method** — lifecycle reconstruction, adjacent-pair gap
analysis, "a sub-10 ms gap between causally-ordered events means concurrency, not sequence" — is
generic, and two steps of the skill (1c and 3d) are nothing but pointers into it. Deleting it would
have removed a generic capability in order to remove specific vocabulary. The **residue** was real
and worse than platform coupling: a SQL query against a private table, an internal persistence
helper, a third-party transcription vendor, and internal field names. Those fail the exact test that
killed the skill they came from — *knowledge only its author can use* — so they were removed rather
than relabelled.

The file now opens with a Provenance section stating the drop, what was kept, what was removed, and
where the line is, so the next person extending it does not re-import the residue.

**On the rename, which differs from how the other three were treated.** `gcp-*` and `docker-*` keep
their names because those files genuinely *are* about that platform — the name is the correct label,
and a reader needs it before opening. "Realtime" would have misdescribed a file that is now generic,
and it kept advertising the dropped skill at three call sites. Different treatment because they are
different cases.

## 4. What the completion review caught, after the work was reported done

Three findings, all in work already reported as finished. Recorded because the pattern is the point:
the review is not a formality after a clean gate.

**(a) A count that went stale between being computed and being written.** "31 anchored edits" was
the sum of two edit scripts' list lengths, quoted after two further edits had been applied by hand.
Neither 31 nor any single script's length describes the change. The tree says 33 replacements / 35
hunks. The rule that catches this — recompute every derived figure from the diff at write time, and
say which quantity the number describes — is in the review skill because it has happened before.

**(b) The doc-retirement gate found a real omission.** Retiring a document requires enumerating its
*executable* artifacts separately from its knowledge. The retired file held two: a SQL query and a
fenced event-sequence chain. Dropping the query was correct — no adopter has that table, and the
knowledge it served survives in the triangulation paragraph. But the **turn chain**, the thing an
observed timeline is diffed *against*, had been compressed to the word "alternating" in the phase
map. It is now restored verbatim as a fenced block, with the normal-flow and interruption readings
beside it. A prose rewrite captures claims and obligations and systematically misses sequences;
that is exactly what happened.

**(c) One internal field name survived a narrower net.** The first "provider vocabulary = 0" claim
was true for the six terms measured. A wider net found a seventh. This was **not** a regression
introduced by the fixes — it was a narrow probe reporting a clean zero — but it contradicted the
file's own claim that internal names were removed, so it was generalized. The corrected figure now
carries a **positive control**: the same probe returns 38 on the pre-edit tree and 0 on the current
one, which is what makes the zero mean something.

## 5. Owed to other writers — three files this work says should change, none edited

Each is held by another session. Reported with the exact change rather than half-applied.

| File | Why | What to change |
|---|---|---|
| `docs/upstream-sync.toml:154` | `analyze-logs` is `direction = "upstream-origin"`, and the kit's copy is now substantially divergent by design. A future refresh will show large diffs on a row that gives a reader no reason for them. | Extend the existing `note` with: "Genericized 2026-08-23 per the OQ-2 ruling — platform-neutral prose, `references/realtime-session-events.md` renamed to `session-event-streams.md`. Refresh diffs against upstream are expected and correct." |
| `plugins/core/src/lemmi_ai_kit/assets/manifest.toml:225` | Summary is accurate but predates the event-stream branch becoming a first-class format. | Optional: "…from structured, plain, container and event-stream logs with task file creation". |
| `.specs/i4-pack-split/topology.md:63` | The D3 row is now factually wrong in two figures. | "4 of 6 references are platform-named" → **3 of 6**; the mention count is now **42** across 7 files / 1116 lines. |

`docs/research/2026-08-23-i4-i1-stand-down-and-audit-gate-fix.md:109` also names the old filename and
was **deliberately left alone**: it is a dated audit artifact, it was true at its date, and rewriting
it would falsify the record.

## 6. Instrument faults — one of them in the instrument that exists to prevent them

**`plugins/core/skills/post-task-review/scripts/probe_checker.py` is unusable on this platform for
realistic checkers, and it fails by reporting a confident wrong verdict rather than an error.**

The script runs checkers via `subprocess.run(..., shell=True)`. On Windows that dispatches to
`cmd.exe`, where POSIX single quotes are not quote characters — so any pattern containing alternation
is parsed as a command pipeline and the checker never runs. Isolated three ways, same fixtures:

| Checker | Through `probe_checker` | Same command in the POSIX shell |
|---|---|---|
| `grep -c GCP {file}` (bare literal — the shape its own self-test uses) | positive=5, **CAN-SEE** | 5 |
| `grep -cE 'GCP\|Cloud Run' {file}` (alternation — the shape a real checker has) | exit 255, **invocation error** | 6 |
| `grep -oiE '<6-term union>' {file}` (default count mode) | positive=0, **"BLIND / UNUSABLE"** | 7 |

The third row is the dangerous one. In `--count-mode grep-c` the code checks the exit status and
raises loudly. In the **default line-count mode it does not** — a checker that never ran returns
zero matches, which the tool then reports as a confident verdict about the *checker* instead of an
admission that nothing executed. Same underlying failure, loud in one mode and silently wrong in the
other. Its own self-test passes because its fixture command is a bare literal with no alternation and
no quoting, so the self-test does not exercise the shape that breaks.

This is a shipped, public-surface artifact and it goes public with the flip. Two candidate fixes,
both outside this session's scope: pass the command as an argument list rather than a shell string,
or apply the `grep-c` branch's exit-code guard to the default branch as well so the failure is at
least loud. **Suggested minimum: the exit-code guard**, since a loud failure is recoverable and a
false "BLIND" verdict trains people to ignore the tool.

Because the mandated certification could not run, both measuring instruments used in this document
were certified manually against the same fixtures and the same contract: positive fixture
`gcp-log-fields.md` = 6, negative fixture `task-file-template.md` = 0, both instruments, verdict
CAN-SEE. Recorded as *blocked with the error*, which is its own state — neither a pass nor an open
finding.

**Two smaller ones, both of which produced a plausible zero.**

`grep … | sed …` inside an `X || echo "0 hits"` guard reports the exit status of **`sed`**, not
`grep`, so the fallback never fires and a broken pipeline is indistinguishable from a genuine zero.
Caught only because the expected fallback text did not appear. Every zero in this document is now
backed by a positive control on the pre-edit tree.

`git diff HEAD` reported roughly 2× line-count deltas on all seven files — the "too round to be
true" tell this program has already paid for once. Cause: the tree is CRLF under `core.autocrlf=true`,
so every line differs. With `--strip-trailing-cr` the real figure was 40 lines in one file, and the
other six were byte-identical. Anything written back was written back as CRLF to match its siblings.

## 7. A guard that has never caught anything

`tests/test_assets.py`'s `_FORBIDDEN` entry for a *dated learnings citation* requires whitespace
directly between the filename and the date. The house style backticks the path, and a closing
backtick is not whitespace — so the guard cannot match the form this repo actually writes. Verified
by importing the compiled pattern and probing it: the bare form matches, the backticked form does not.

`docs/research/2026-08-23-session-retrospective-reconciliation.md` rows 1, 3 and 4 record three such
citations removed **by hand**. All three were backticked. The guard has never caught one.

Same shape as the W-2 finding in program §5f, in a different guard. Not fixed here: the pattern tuple
is imported by `tests/test_publication_hygiene.py`, so one edit changes two contracts, and the file is
held elsewhere. Minimal fix is an optional backtick in the pattern. `analyze-logs` carried exactly
such a citation until today; it was rewritten to state the fact inline, since an adopter cannot open
the cited entry in any case.

## 8. Step inventory

| Mandated step | Ran? | Evidence / why not |
|---|---|---|
| Conceptual review (1) | yes | Checked against the OQ-2 ruling and all nine requirements in the brief; each ticked against the diff, not against prose |
| File-by-file review (2) | yes | Backup→live diff, all 6 edited files plus the delete/add pair |
| Convention compliance (3) | yes | CRLF preserved on all 7 files; repo's own 15 hygiene patterns imported and run over the tree — 0 hits |
| Self-challenge (4) | yes | Findings (a), (b) and (c) in §4 all came from this step |
| Fixes applied (5) | yes | Turn chain restored; field name generalized; review re-run over the fix diff, which is how (c) surfaced |
| Lint + diagnostics (6) | yes | `ruff check` 0 · `ruff format --check` 0 · `basedpyright` 0 errors, all on explicit targets |
| Documentation impact (7) | yes | Matrix consulted; 3 affected files identified and reported in §5 rather than edited; 1 dated artifact deliberately left |
| Learnings extraction (8) | **partial** | This repo ships no root `.ai/learnings.md` — the documented dogfooding gap in program §7. Findings recorded here and in session memory instead; no changelog entry, as no kit infrastructure file was modified |
| Checker certification (trap j) | **blocked** | `probe_checker.py` cannot run a multi-pattern checker on this platform — §6. Equivalent certification performed manually, same fixtures, recorded above |
| Four-check gate | yes | `1 failed, 189 passed, 6 skipped` — identical to the pre-work baseline, same test, same file, another writer's |
| Untracked-dependency check | yes | `git ls-files --error-unmatch` on every doc naming these files: one tracked (left, dated artifact), four untracked |
| Scope audit | yes | `find -newermt` over the whole tree: the only files this session wrote are the 7 in `analyze-logs/` |

## 9. State at hand-off

Nothing is committed — the standing choice, unchanged. The whole skill tree is **untracked**, so
`git diff` cannot snapshot it; a pre-edit tarball was kept for the duration and the backup→live diff
in §1 is derived from it. The pre-existing `test_publication_hygiene` failure belongs to
`docs/research/2026-08-23-i4-pack-split-implementation-handoff-to-orchestration.md` and is untouched
here.

D3 is closed. Row I-1 has no remaining deliverables.
