# Session handoff — three guards that passed while blind, and what fixed them

Written 2026-08-24 by the session that ran S-1, S-4 and F19. Seven commits across three work
packages; this record exists because the *findings* were not in any of them. They lived in commit
messages and an inter-session channel, and neither is somewhere git keeps a lesson where the next
person will look.

The subject is a single failure mode with three instances, all found in one evening, all in this
repository's own test suite. It is the one the directory README describes as "the times it caught
us" — except that here the thing being caught was the catching machinery.

## 1. The failure mode

Every measurement failure this program had recorded before tonight **fails closed**: the instrument
returns empty, and a zero at least looks like an answer worth a second look. An `ast.Assign` scan
over an annotated assignment printing nothing; a grep whose pattern collapsed in a shell.

The three below **fail open**. They return SUCCESS — the outcome everybody wants — which makes a
green guard the least interrogated result in the repository. That asymmetry is the whole finding.
A zero invites suspicion. A pass does not.

| # | Guard | Claimed | Actually did |
|---|---|---|---|
| 1 | `test_readme_counts.py` | every skill count matches the manifest | enforced **1 of 3** claims; the invisible one was false |
| 2 | `test_repo_path_references.py` | no **published** file names the pre-split path | scanned **43 of 144** files; skipped everything that ships |
| 3 | the same file, internally | two scan surfaces | 11 files were in **both**, judged by the wrong rule |

Instance 1 sat over a false claim on the README landing page while this program's own documentation
asserted "README's count is enforced against the manifest." It was — against a third of the file.

## 2. Three standing rules

These are the durable payload. Each came from one of the instances above and generalises past it.

**A guard that has never been shown to fail has not been shown to work.**
Prove the matcher can fire before trusting that it did not. Run negative controls against perturbed
copies *in memory* — monkeypatch the reader, never edit the real file — and keep a positive control
in the suite so the proof survives.

**A guard states its scan surface in numbers it asserts.**
Its name is not evidence of its coverage. `len(scanned)` against `git ls-files | wc -l` is one probe
and it is what found instance 2. Assert the surface inside the test, and name the specific files
that must stay in scope, so the name cannot drift from the coverage later.

**When a guard has more than one scan surface, assert they are disjoint.**
`assert not (a & b)` found instance 3 on its first run, after reading had not. The direction matters
and is counter-intuitive: a file present in two surfaces makes coverage look **better**, not worse,
while being judged by a rule that does not apply to it.

## 3. The negative controls, and which one mattered

Four were run against the count guard, on perturbed copies with `README.md` untouched on disk. All
four fired:

| control | result |
|---|---|
| the original defect, core count off by one | `claims 35 skills, the core pack ships 36` |
| a wrong total | `claims 37 skills, the manifest ships 38` |
| **an unregistered qualifier** | **rejected by name, not skipped** |
| a phrasing outside the enforcing net | caught by the loose-net guard |

**The third is the one that converts a fix into a guard.** The original pattern required `skills` to
follow the digits immediately, so a qualifier — `35 language-agnostic skills` — was invisible.
Widening the regex would have made all three of today's claims enforced and left the *class* intact
for the next phrasing nobody anticipated. Instead the qualifier is captured and **resolved**: absent
means the manifest total, registered means that pack's size, and unregistered is a **failure rather
than a skip**. Writing `36 orchestration skills` now demands that the author register what the
phrase scopes to or drop the number. That is what closes the class.

The same shape appears in the fourth control: a second, deliberately sloppier regex runs over the
same file and fails if it sees a claim the enforcing one cannot. It never checks a number. Its only
job is to prove the enforcing pattern is not blind.

## 4. A wider net is sometimes a bug, not an extension

Instance 2 looked like "the scan is too narrow, widen it." It was not, and widening it would have
shipped a defect.

Correctness here depends on *which tree* a path lives in. On the repo surface a package path must
carry `plugins/<pack>/`. Inside an installed plugin that prefix names nothing — the plugin root
contains `src/` directly — so the payload's anchor is `${CLAUDE_PLUGIN_ROOT}/`. The one shipped file
that matched carried both cases two lines apart:

```
kit-setup/SKILL.md:45   ${PLUGIN_ROOT}/src/lemmi_ai_kit/assets/    CORRECT
kit-setup/SKILL.md:47   src/lemmi_ai_kit/assets/manifest.toml      the defect
```

Line 47 was not missing a prefix. It was missing its **anchor**, reading as payload-relative by
context while saying nothing. Had the guard been extended by exemption — "skip the payload, or allow
line 45" — the shape of the fix would have invited someone to add `plugins/core/` to line 47 and
produce a path that resolves nowhere on an adopter's machine. The guard now treats the repo prefix
as a *violation* inside the payload, so it pushes back on that edit.

The generalisable question: before widening a scan across a boundary, check whether the rule
**inverts** across it.

## 5. The finding this record exists for

While deleting hand-written counts, I wrote one.

The guard's own module docstring said **"Two exemptions"** after I had retired one of them, in the
same commit whose stated purpose was removing hand-written counts, written by the session that had
spent the evening on exactly this defect. I caught it re-reading before committing. Nothing else
would have.

Every prior instance in this program could be read as someone not knowing the rule. This one cannot:
maximum awareness, immediate context, same hour, same file. **The reflex is not self-corrected by
awareness, only by a check.** That is the argument for deriving or asserting a count rather than
resolving to be careful with it — including, and especially, when you are the person who just
wrote the rule.

Related tally correction: the stale "nine patterns" count (the tuple has ten) lived in **two** files
— `tests/test_publication_hygiene.py` and `CONTRIBUTING.md` — and only one of them was ever briefed.
The second was found by sweeping rather than by the brief, which puts the program's count of paid-for
hand-written counts at **seven, not six**.

## 6. Two things that need no further probe

**`${PLUGIN_ROOT}` vs `${CLAUDE_PLUGIN_ROOT}` in shipped skills is not a defect.** Three uses of the
bare form against eleven of the prefixed one looks like a host-compatibility bug. It is not:
`kit-setup/SKILL.md:37` reads `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT}}"` with a comment
naming both hosts, and it is the only shipped file using the bare form. Correct as written.

**`CONTRIBUTING.md` said the hygiene scan covers "every *tracked* file."** It never did — the
enumeration has always passed `--others --exclude-standard`, so unignored untracked files are in
scope. That is the right behaviour (such a file is one `git add .` from being published) and the
prose was corrected to match the code rather than the reverse. The same false claim was in the
scanning module's own docstring.

## 7. Open, and explicitly not mine

**F20 — the same shape, one level over.** `_FORBIDDEN` bans `.claude/skills/<name>/scripts/`, which
is the repo-shaped spelling of a payload-relative path — structurally the same defect as §4. That
rule is enforced only inside the asset tree by `test_assets.py`. Measured by orchestration after I
raised it: unenforced across **95 shipped skill files, 0 occurrences today**. Latent rather than
live, and the risk is an upstream refresh re-importing what the extraction once rewrote nineteen
times with nothing watching.

I hold no paths and did not run this myself. It is a lead with a measurement attached, not a finding.

## 8. Where verification stops

Everything above was verified by running it. The suite went 190 → 224 passed across the evening,
with the growth in the middle belonging to other sessions; each of the four commits carrying a guard
was checked out into a throwaway clone and run in isolation, because "green in a shared working tree"
and "green as committed" are different claims. Invocation throughout:

```sh
T=$(mktemp -d); uv run pytest -q --basetemp "$T"; rm -rf "$T"
```

What is **not** verified: whether the three rules in §2 generalise beyond this repository. They were
derived from three instances in one evening in one test suite. They are stated as rules because they
each caught something the previous habit did not, not because they have been tested against a
counter-example.
