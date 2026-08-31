# Fixture design — the half `probe_checker.py` cannot do for you

`probe_checker.py` answers one question: *given these two fixtures, can the checker see?* It cannot
tell you whether the fixtures model anything real. Every failure below produced a **green probe** on
a **wrong instrument**, and all of them were measured in this repo.

Read this at the moment you write a checker, not at the gate that has already been driven by its
output.

---

## 1. A negative fixture must RESEMBLE the target and still pass

"Something unrelated" proves nothing. The negative's whole job is to sit one step away from the
positive, so that a pattern which over-reaches gets caught.

**Measured.** `session-retrospective`'s extractor aborted with exit 3:

```
possible secret leak: matched /sk-[A-Za-z0-9_\-]{16,}/ -> sk-content-reduction-spec
```

That is the tail of a real branch name ending in `...-spec`, matched at
`...subta|sk-content-reduction-spec` because the pattern had **no left word boundary**. It was the
only `sk-` match in a 191-session corpus — a 100% false-positive rate.

The same pattern sat in two places and failed in **opposite directions at once**:

| Where | Mode | Damage |
|---|---|---|
| `LEAK_PATTERNS` | fail-closed | halted the pipeline, exit 3 |
| `REDACTIONS` | **fail-silent** | rewrote **119** real `.specs/` paths to `subta[REDACTED_KEY]` |

The redaction half is the dangerous one: no error, no signal, and an analyst reading those
transcripts sees mangled paths it cannot cite. A sibling pattern `\b[A-Fa-f0-9]{32,}\b` did the same
to **170** git SHAs and sha256 digests — this repo's primary citation anchors.

The existing tests could not catch it because their clean fixture was the literal string
`"all findings redacted"` — a trivial non-match exercising no boundary. **There was a positive
control and no resembling negative one.**

> Applies to every redactor, linter and detector — including the ones inside our own measurement
> instruments. This one had been corrupting the retrospective's evidence base for an unknown number
> of runs while reporting success.

## 2. The probe certifies the half you pointed it at — usually the wrong half

The split that makes code probeable is the same split that decides what gets probed. The **pure**
half is easy to fixture, so it gets the fixture; the **network-adjacent** half carrying the external
system's actual semantics gets none.

**Measured.** A PR-state gate script was split into `evaluate()` (verdict logic) and
`fetch()` (three GitHub REST calls plus a digest step). `evaluate()` probed
`positive=3 negative=0 verdict=CAN-SEE`. The digest inside `fetch()` was never reached by any
fixture — and it was wrong: it applied `in_reply_to_id` inline-reply detection uniformly to all three
endpoints, but only `pulls/{n}/comments` carries that field. Every review summary body and every
PR-level comment came back `answered=False`, **including a bare APPROVE with an empty body**. A live
run over the r2 stack would have been a wall of false UNANSWERED findings on 2 of 3 surfaces.

The probe's PASS was true and irrelevant.

**So:** ask *which function would be wrong if I misunderstood the external system*, and put the seam
**there** — e.g. a pure `digest_surface(name, raw_items)` fed **RAW recorded payloads**, never
records you hand-digested. A fixture whose field values you typed yourself can only confirm what you
already believed. **State in the probe stamp which functions the fixtures actually reach.**

## 3. Two ways a fixture silently comes to agree with its author

Both happened to the same checker within one hour.

**DECAY — the fixture stops modelling anything, and SUCCESS is the trigger.** The positive fixture
for a "cited-as-durable but untracked" check cited `tasks/TECH-r2-layer5-review.md`, chosen precisely
*because* it was untracked. The commit that **fixed** the defect tracked that report, so the probe
went `CAN-SEE` → `UNUSABLE` **inside the commit that fixed the thing it detects**.

> **Pin a positive fixture to something the fix cannot change.** Here: a permanently gitignored path,
> which reports UNTRACKED where the directory exists and DOES NOT EXIST in a fresh clone — a finding
> either way. And **re-run every probe after the commit that fixes what it detects.**

**SHARED PROVENANCE — it never tested anything.** The checker's durability-phrase list
(`Durable report`, `Full analysis`, …) was written from the same head as the fixture, so they matched
by construction. Grepping the corpus for citation-shaped lines the pattern could **not** see returned
`Topology:` (×4), `Gate record:` (×2), `Source analysis:` (×2) and the whole decision/side/own-record
family. Adding the measured phrases took the live finding count **16 → 51**, with zero false
positives across all 21 distinct cited paths.

> **Derive any word or phrase list by grepping the corpus for what the pattern MISSES — invert the
> match — before trusting a clean reading. Never write the list and the fixture in one pass.**

A green probe means the fixture and the code agree. It says nothing about whether either agrees with
the world.

## 4. A marker-gated checker returns a silent zero for the files it never opened

A marker-gated file linter carries two traps that compose, and they fail in **opposite**
directions. Both were measured on the linter this kit's `lint` subcommand replaced:

1. It printed `LINT FAILED (102 finding(s))` and **exited 0**. That is the inverse of the usual
   shape (`All checks passed!` alongside exit 1), so a reader primed for that direction is not
   protected. **The text is the verdict; the exit code is not.**
2. Its hand-off check returned an empty list before any rule ran, for any file lacking the literal
   `handoff-contract:` marker. A newly-written hand-off scored **zero findings because it was never
   opened.**

The only evidence distinguishing "clean" from "never read" is the summary's own
`[N/252 file(s) under contract]` counter: adding the marker moved it **163 → 164**, and only then
did the zero mean anything.

> When linting a file you just wrote: **grep the output for your own filename AND check the
> under-contract counter rose by one.** Treat "my file is absent from the findings" as UNREAD until
> the counter proves otherwise. Generalises to any opt-in-gated checker — the files it skips are
> precisely the set a new artifact belongs to.

## 5. A tool that MATCHES source text must normalise line endings first

Not only tools that write. **Measured:** a fail-before harness (revert one fix, run the
one test meant to catch it, assert it FAILS) used LF triple-quoted anchors against a repo whose
`.py` files are CRLF on disk. First run scored **3 of 7**, four cases reporting
`SKIPPED - anchor not found`.

Nothing was wrong with the fixes or the tests. Normalising both sides took it to **9/9**.

This is the CRLF trap arriving through a **verification** tool rather than an editing one, and that
is what makes it dangerous: the output was a plausible verdict *about your own work* ("four fixes
unproven") rather than an obvious tool error. The three passing cases proved the harness *could*
work, which is exactly the evidence that made the four skips look real.

> **Assert that every anchor resolves BEFORE running any case.** That is the shape to build in from
> the start, and it would have caught this immediately.

## 6. A compound pattern encodes two guesses at once, and fails silently while returning results

**Measured.** The operator said *"extend our test assistant mode"*. The search pattern was
`test.assistant|assistant.mode|test_mode`. Measured after the fact: **0 hits** in the feature
directory actually named `testing_assistant`, **5+** in an unrelated one named `<other>_test`.

The real feature is `testing_assistant` — "test**ing_**assistant" — so a `.` between "test" and
"assistant" could never match it, while `test_mode` happened to hit the other directory. The pattern
did not merely miss; it **actively redirected to a plausible neighbour**, and a full round of
analysis plus a "this is the wrong vehicle, here is what to do instead" recommendation was built on
it.

```bash
grep -rli 'assistant' <source root> --include=*.py    # 6 files, all the right feature
```

> **When the human names a thing, search for their literal distinctive token first** — no compound,
> no separator guess. The tell that should have stopped it: every hit was in a feature whose name
> does not contain the operator's word "assistant" at all.
> **If none of your matches contain the user's actual word, you have found something else.**
> Cheap guard: before reasoning from a located feature, confirm its directory name contains the term
> the human used.

---

## Why this file is prose and not a check

The seam for this whole class is `probe_checker.py`, and it carried this defect itself until it was
repaired: it runs `--cmd` through the platform shell, and on Windows that is cmd.exe, so a
forward-slash executable path returned a **false BLIND** — the exact mirror of the false-clean it
exists to catch. What remains here is **fixture design**, which the
seam cannot encode: no script can decide whether your negative fixture resembles the target closely
enough, or whether you aimed it at the half that holds the domain semantics.

Two pieces of it *are* mechanizable and are not yet built — worth doing if this class recurs:

- have the probe stamp record **which functions the fixtures actually reach** (§2);
- flag a probe whose positive fixture is a **tracked path that a fix could change** (§3 decay).
