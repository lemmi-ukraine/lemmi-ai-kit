# The pre-publish guard — self-challenge and completion review

**Dated:** 2026-08-24, after `c88d152` landed and before the fixes below were committed.
**Reviews:** S-3 step 2 — `plugins/core/src/lemmi_ai_kit/publish.py`, its `publish-check`
subcommand in `plugins/core/src/lemmi_ai_kit/cli.py`, and `tests/test_publish.py`.

**Sizes, anchored to commits rather than to this file, because an unanchored one rots on the
next commit — which is what happened here.** An earlier draft of this line said "353 lines,
27 tests, 515 lines" with no anchor; those were true at `34360e2` and were already stale by
`68139d5`, in the header of the document whose §2 is about counts that read low.

| at | `publish.py` | `test_publish.py` |
|---|---|---|
| `c88d152` as reviewed | 316 lines | 25 tests, 458 lines |
| `34360e2` after §2's fixes | 353 lines | 27 tests, 515 lines |
| `68139d5` after §7's fix | 421 lines | 30 tests, 586 lines |
**Method:** adversarial, against real git behaviour rather than against my own report. Five
probes run in throwaway checkouts, asking what git *actually does* rather than what the tests
assume. **Two defects in shipped behaviour were found this way, both after a green 25-test
suite. Both are fixed, each has a test, and every figure in the handoff is recomputed.**

---

## 1. The structural failure: 25 green tests, written entirely from my own fixtures

The suite passed. Every probe I had thought to write, I had also written the fixture for — so
the suite proved that the guard accepted my idea of a clean tree and rejected my idea of a
dirty one. It never asked **what git actually reports**, which is the only question the guard
is made of. Every one of its three probes is a `git` invocation; the entire product is the
behaviour of three command lines I had not independently characterised.

This is [the I2 CLI-substitution review's](2026-08-23-i2-cli-substitution-completion-review.md)
finding arriving a second time, in a different costume. There it was "fixtures written by the
author are the weakest possible corpus" for a *file-format* parser. Here the corpus is not a
file format but a *tool's output contract*, and I made the identical mistake: I tested my
intentions against my own idea of git's behaviour.

**The fix that found the bugs was ten minutes of `mktemp -d` and five scratch repos.** Not
more tests — a different question. Both defects below fell out of the first two probes.

## 2. The findings

| # | Finding | Class | Consequence |
|---|---|---|---|
| **1** | `git status --porcelain` collapses an untracked subtree to one entry at its **topmost untracked ancestor** | **undercount in shipped behaviour** | One entry for a subtree of *any* size — six files reported as `working tree (1)` in the fixture, but the ratio is unbounded. A guard whose entire subject is "how many files actually ship" undercounting in the direction of looking safer |
| **2** | A **nested git repository** is one entry in *every* probe, even with `-uall` | **undercount that cannot be fixed** | Git will not look inside another repo. A vendored clone under `plugins/` is `nested/`, one entry, however many files — and `extra` printed that floor as an exact total |
| **3** | My first probe of my own checker was itself blind | **method** | `probe_checker` reported `positive=0 … verdict=UNUSABLE`. The guard was fine; my probe's `$(dirname …)` never ran, because `shell=True` is `cmd.exe` on Windows |
| 4 | The guard has **two** independent detections, not three | overstatement | Probe 2 is a strict subset of probe 1 — every untracked non-ignored payload file also appears in `status`. Its value is scoping, not detection |
| 5 | The premise itself is **inherited, not re-measured** | unverified | See §5 |
| **6** | **The guard blocked on files it created itself** — added after this review closed | **gate unpassable by construction** | Importing the package writes seven `.pyc` into the payload *before* the probe runs. From a genuinely clean tree, a plain run reported `gitignored in the payload (7)` and exited 1, having made all seven. `git clean` then a plain re-run is a loop. Found by `lemmi-ai-kit-c2`; see §7 |

Findings 1 and 2 are the same defect at two depths, and finding 3 is why I trust 1 and 2:
the instrument that certified the guard first certified *itself* as broken, loudly, before
I could quote a number off it.

### Finding 1 — the guard undercounted what ships

```
$ git status --porcelain              →  ?? plugins/core/newdir/          (1 entry)
$ git status --porcelain -uall        →  6 files, listed individually
$ git ls-files --others               →  the same 6
```

`-uall` is now passed, and `test_an_untracked_directory_is_counted_file_by_file` pins it.
This one deserves its rank: reporting six files as one is *the same class of error* as the
leak the guard exists to catch — a count that is silently low, in the direction of looking
clean. Had it shipped, the guard's most quotable output line would have been wrong exactly
when a large accidental drop made it matter most.

**Corrected in place, 2026-08-24 — the ratio above understates it.** `lemmi-ai-kit-c2`
challenged the 6:1 framing, and re-measuring settles it in their favour: git collapses to
the **topmost entirely-untracked ancestor directory**, at any depth, not to the directory
holding the files.

```
tracked:   plugins/core/skills/demo/SKILL.md
untracked: plugins/core/a/b/c/f1.md … f6.md
$ git status --porcelain     →  ?? plugins/core/a/     ← one entry, three levels up
```

So **the undercount is unbounded, not six-to-one**: a single entry stands for an untracked
subtree of any size. Six-to-one was the instance I happened to build. The fix is unchanged —
`-uall` enumerates all of it either way — but the severity is not, and a bound quoted from
one fixture is exactly the kind of number this document exists to distrust.

One qualification the peer's own fixture surfaces: their shape had *no* tracked file under
`plugins/`, which in the guard's real path does not produce a wrong count at all — it trips
the vacuous-payload check and exits 2. The unbounded undercount needs the shape above, where
the pack has tracked content *and* an untracked subtree. That is the realistic one.

### Finding 2 — the limit that gets disclosed instead of hidden

`-uall` does not expand a nested repository, and nothing will: git declines to look inside
another repo, so the file count is unknowable from outside. Verified — three files in a
nested repo, one entry in all three probes.

It still **blocks**, which is the part that matters. What it cannot do is say how many files
it stands for. Two changes rather than one:

- the entry is marked in the listing — an unmarked `vendored/` reads as a single file;
- the arithmetic prints **"at least"** whenever such an entry is present.

Refusing to print a floor as a total is the same rule as refusing to call a vacuous scan
clean, applied to a number instead of a verdict.

### Finding 4 — three probes, two detections. Stated because it is flattering otherwise

With `-uall` in place, probe 2 (`ls-files --others`) reports a strict subset of probe 1
(`status --porcelain -uall`). It can never fire when probe 1 is silent, so as a *gate* it
adds nothing. It earns its place for two other reasons — it scopes the finding to the payload
rather than the repo, and it supplies the `extra` arithmetic — but "three probes" should not
be read as three independent chances to catch a leak.

**The one that is genuinely independent is probe 3.** `git status` is blind to ignored files
by construction, which is why six `.pyc` reached V-1's measured payload while the tree looked
clean. That is now proven rather than argued — see §3.

## 3. Certification: the checker was probed before its verdicts were quoted

Per the post-task-review skill's step 4(j). `probe_checker.py` takes file fixtures and the
guard takes a repository, so a bridge does the path arithmetic in Python — **not** in the
`--cmd` string, which is where the first attempt died.

```
probe_checker PASS - publish-check fires on an untracked payload file, silent on a clean tree
  probe_checker: positive=2 negative=0 verdict=CAN-SEE

probe_checker PASS - the ignored-file probe sees a .pyc that git status reports as a clean tree
  probe_checker: positive=1 negative=0 verdict=CAN-SEE
```

The second stamp is the load-bearing one. Its positive fixture is a repository whose
`git status --porcelain` is **empty** while a `.pyc` sits under the payload — the exact
shape of V-1's leak, reproduced from scratch, caught by the guard, invisible to `status`.
That claim was the reason to build the thing, and it is now a measurement rather than an
argument.

### The probe that reported the guard blind, and was itself the blind thing

The first invocation returned `positive=0 negative=0 verdict=UNUSABLE`. Read carelessly,
that says the guard cannot see. It said the opposite: `probe_checker` runs `--cmd` under
`shell=True`, which is `cmd.exe` on Windows, so the `$(dirname …)` I had written silently
never executed and the command produced nothing on either fixture.

**A zero from an unprobed instrument is unproven in both directions** — and the instrument
whose entire purpose is to say so caught me on its own first use. The negative fixture is
what makes this legible: an over-matching probe and a blind probe both look like "0 findings"
until something distinguishes them.

## 4. Probes run, and what each settled

| Probe | Question | Answer |
|---|---|---|
| A | Does a nested git repo escape the guard entirely? | **No** — it blocks, as one entry (finding 2) |
| B | Does `status --porcelain` enumerate an untracked directory? | **No** — one entry for six files (finding 1) |
| C | Is probe 2 redundant with probe 1? | **Yes, for blocking** (finding 4) |
| D | Are probes 2 and 3 disjoint, as `extra`'s sum assumes? | **Yes** — verified, an untracked tree and an ignored `.pyc` under one pack appear in exactly one probe each |
| E | Does the remedy I tell people to run actually work? | **Yes** — `git clean -Xdf -- plugins/core` removed the ignored `__pycache__` and left six untracked files untouched |

Probe E was worth running for its own sake: the guard prints a **destructive** command, and
"`-X` removes only ignored files" was a claim about git I had made in prose, in a file, that
a reader would act on. It holds.

## 5. What is still unverified, stated as unverified

**The guard's premise is inherited.** Every probe above measures *git state*. The claim that
git state corresponds to what a `plugin install` actually copies comes from V-1's
measurement, not from anything this session ran: there is no `claude` or `codex` binary on
this machine's `PATH`, so the payload could not be re-materialised and diffed. If V-1's
finding were wrong, this guard would be precise about the wrong thing. It is the best-attested
finding in the program and I do not doubt it — but the distinction between *attested* and
*re-measured* is the distinction this document exists to keep.

Not probed, and each a plausible route to a wrong answer:

- **symlinks** under a pack — git tracks the link, the copy may follow it;
- **case-only collisions**, which Windows and git disagree about;
- **the `./` payload form** end to end — unit-tested in `payload_roots`, never run against a
  marketplace that actually declares it;
- **performance** on a large tree — three `git` invocations, never timed on anything big.

## 6. Carry forward

**For a checker, "the tests pass" and "the tool behaves as I assumed" are different claims,
and only the second one is load-bearing.** Where the previous instance of this lesson said to
run a parser against the repository's real files, this one generalises it: when the product
*is* a wrapper around another tool, characterise that tool's output contract directly, in a
scratch fixture, before writing a single assertion about it. Ten minutes of `mktemp -d` found
two defects that twenty-five tests did not.

**A count that can be low must never print as though it were exact.** "At least" is not
hedging; it is the numeric form of the rule this guard already applies to verdicts, where
cannot-measure exits 2 rather than 0. A guard that undercounts what ships has adopted the
failure mode of the leak it was built to stop.

## 7. Added 2026-08-24, after this review closed — the guard blocked on its own output

`lemmi-ai-kit-c2` ran the guard from a genuinely empty starting state, which nothing in this
review had done. Reproduced here on a fresh `git clone`, so the measurement is independent:

```
git clean -Xdf -- plugins/core plugins/python     →  0 .pyc

python    -m lemmi_ai_kit publish-check  →  BLOCKED gitignored (7)   exit 1   7 .pyc after
python -B -m lemmi_ai_kit publish-check  →  PUBLISH CHECK PASSED     exit 0   0 .pyc after
```

Importing the package writes its bytecode into the payload **before** the git probe runs, so the
guard manufactured all seven of its own findings. `git clean` followed by a plain re-run is a
loop, and **the gate was unpassable by construction** — from a tree that was genuinely clean.

That is this document's §2 warning arriving from the direction it did not check. §4 of the
handoff argues that a permanently red gate drives whoever is publishing toward a `__pycache__`
exemption, and that the exemption is the one edit that would truly blind the detector. A gate
that cannot pass *even when the tree is clean* is the strongest possible version of that
pressure — and I built it while writing the warning about it.

**The obvious fix does not work, and was measured rather than assumed.** Setting
`sys.dont_write_bytecode = True` at the top of `__init__.py` takes seven to **one**, never zero:
CPython writes a module's cache entry before the module body executes, so `__init__.pyc` lands
before that assignment can run. There is no in-process fix; the flag must be on the interpreter.

**What shipped:** `writes_bytecode_into_payload` detects the condition — bytecode caching on,
*and* this package resolving inside the declared payload — and the ignored-file remedy then
carries the invocation that actually works, after the `git clean` it would otherwise leave the
operator repeating. Disclosure, not exemption.

### Why neither the suite nor this review could have caught it

Every test but two builds a throwaway repo that does not contain this package, and the one test
touching the real checkout **deliberately asserts only measurability, never the verdict** — a
choice made because several sessions write this tree, and defended in §1 of the handoff. It was
the right call and it is exactly what made this invisible: the single test positioned to see the
bug was designed not to look at the answer.

**Carry forward, and it generalises past this guard: a check that runs inside its own subject
must be measured from the subject's clean state, by something that is not the check.** Every
probe in §4 asked *what does git do?*. None asked *what does running this command do to the tree
it measures?* — and that question needed a starting state this session never created, because
the session's own tooling had dirtied the tree before the first probe.
