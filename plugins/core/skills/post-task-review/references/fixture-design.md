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

## 7. Fixtures must be FILES, so a multi-root check can only probe one root

`probe_checker.py` asserts that `--positive` and `--negative` are **files** before it runs anything,
and it substitutes a single `{file}` into `--cmd`. A check whose real invocation takes *two* roots —
`--join <TREE_A> <TREE_B>`, a corpus-vs-corpus comparison — therefore cannot be probed with two
directory fixtures. It fails before the checker is ever called.

The fix is a design constraint on the *check*, adopted early rather than discovered late:

- Keep exactly **one** argument as the probed `{file}` — a single small fixture file — and bake the
  other roots into the `--cmd` string as fixed paths.
- Make the check accept **either a directory or a single file** for that argument, so the probe can
  point it at one small file while the real invocation still passes a whole tree.

Verified shape: making the second root of a `--join` accept a bare file as well as a directory let
two single-file fixtures (one routed, one unrouted) serve as the probe pair against a fixed shared
first root.

The general point: **a check that cannot be probed is a check you will end up trusting unprobed.**
Probe-ability is a design property, so decide it when you write the signature, not when the gate
refuses your fixtures.

## 8. The probe's counting unit is OUTPUT LINES, and a mismatch accuses the innocent party

`probe_checker.py` counts your checker's **output lines**. Two very common checker shapes therefore
probe as `UNUSABLE / OVER-MATCHING` while being perfectly correct:

- **`grep -c PATTERN {file}`** prints one count line always, so positive and negative both yield 1.
  Measured three times independently (`positive=1 negative=1`, `positive=3 negative=2`).
- **A checker that prints an unconditional summary** (`TOTAL: n`, a per-file header) adds a line to
  every run, including the clean one.

The fix is one flag — **`--count-mode grep-c`** parses a bare integer on stdout instead of counting
lines — or make the checker print nothing when it finds nothing.

**The trap is that the FAIL is a true statement about the wrong quantity, and it points at the
innocent party**: it accuses the *pattern* of over-matching when the defect is the *counting unit*.
Read literally, it sends you to rewrite a correct pattern. Before believing an OVER-MATCHING verdict,
run the checker by hand on the negative fixture and look at what it actually printed.

## 9. A fixture must model the real confounder, not a stub of it

Five separate instances, all of which produced a confidently wrong number:

- **When you write the format AND the checker, the negative fixture must come from the format's own
  mandated forms.** A "diagram-only fact" check flagged `WarnSent` and `EndPending` — ordinary
  two-word `stateDiagram-v2` state names, the exact form *the template mandates for lifecycles*. A
  stub negative would never have contained them.
- **A fixture the shell could not actually write reads as "the checker is blind".**
  `printf 'foo \\n --flag\n'` emits the literal characters `\` and `n`, not a backslash-newline, so
  the fixture had no continued line and the checker correctly reported nothing. Verify the fixture
  contains what you think (`cat -A`) before believing the probe.
- **A self-probe that tests an instrument's REACH passes while the instrument is wrong.** A parser
  reported six overlaps across five session pairs — every one an artifact — and would have refuted a
  purpose-built audit that found none. Reach and correctness are different questions.
- **A category table whose counts sum EXACTLY to the population size is evidence of first-match-wins
  accounting, not of coverage.** One report read 279 / 29 / 9 / **0** / **0**, recommended deleting
  the two zero tokens as dead vocabulary, and defended the zeros as "read, not blind" because its
  probe returned all five at 1 each. Overlapping categories cannot sum to the population.
- **The probe substitutes the fixture path as a native path string.** A checker receiving `{file}`
  through `awk -v` gets its escape sequences processed — on a backslash-separated path every component
  starting with `t`, `v`, `r`, `n`, `b`, `f` is mangled silently. If a checker's hand run and probe
  run disagree, suspect the path before the pattern.

## 10. A shell tool that cannot parse its pattern exits 2, and `rc != 0` reads as "no match"

A `grep` that receives a mangled pattern (measured: a POSIX-emulation `grep` invoked from a native
Python stripped the backslashes, so a backslash-escaped ERE arrived unbalanced) exits **2** on every
call with `Unmatched ( or \(`. Guards written as

```python
if res.returncode == 0 and res.stdout.strip():   # WRONG: rc 2 is silently "no match"
```

make a broken command and an honest zero indistinguishable — and the failure direction is always
"reports clean". Treat `rc >= 2` as an ERROR, never as a negative result, and assert `res.stderr` is
empty. Prefer Python's own `re` over shelling out when the pattern needs escapes at all.

## 11. A scripted replacement spliced into a CRLF file silently makes it mixed-ending

§5 covers matching. This is the write path: a Python `"""..."""` literal carries `\n`, so splicing
it into a pure-CRLF file lands an LF island inside it — a 44-line island landed this way with no gate
failing. What catches it is an assertion, not care: measure the OUTPUT endings against the MEASURED
input in the same script, immediately before the write.

```python
raw = open(P, "rb").read()
crlf_in = raw.count(b"\r\n"); lf_in = raw.count(b"\n") - crlf_in
...                                  # build `out`
crlf_out = out.count(b"\r\n"); lf_out = out.count(b"\n") - crlf_out
assert (crlf_out > 0) == (crlf_in > 0) and (lf_out > 0) == (lf_in > 0), "ending mix changed"
```

**The obvious repair is itself a trap.** `.replace("\r\n", "\n").replace("\n", "\r\n")` normalises
the *whole file*, so a script written to change two strings rewrites every line — the whole-file
rewrite hazard wearing the clothes of a fix. Normalise only the replacement text, never the document.
And measure in BYTES: a `grep -c $'\r$'` census can degrade to a bare end-of-line anchor under some
shells and report every file as 100% CRLF unconditionally.

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
