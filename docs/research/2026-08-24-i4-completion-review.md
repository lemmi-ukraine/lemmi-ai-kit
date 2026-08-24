# I4 completion review — every deliverable settled by command, and what is left

**Session:** C-1 (Clean Up), the closing row of `.specs/i4-pack-split/execution-plan.md` §3.
**Baseline:** `HEAD 53c0a56`, `main`, 0 unpushed, suite `249 passed, 6 skipped`.
**Method:** every row below was settled against the tree, not against a handoff. Handoffs in this
directory have gone stale within a day more than once; they are treated here as claims with dates.

> **This session did not retire `.specs/i4-pack-split/`, and the register row saying it should be
> retired is overridden.** The reasoning and the partition that makes a later retirement a decision
> rather than an accident are in §5. Nothing under `.specs/` or `tasks/` was deleted, moved, or
> edited.

---

## 0. Two facts about the tree that outrank the brief

**This session was not the only writer, and the brief said it was.** `git status --porcelain`
returned empty at session start and again mid-session. Minutes later the same command returned
three modified paths:

```
 M plugins/core/skills/session-retrospective/SKILL.md
 M plugins/core/skills/task-learnings/SKILL.md
 M plugins/core/skills/task-learnings/references/learnings-format.md
```

with mtimes inside the same two-minute window and `HEAD` unchanged at `53c0a56`. By the time this
record was staged, minutes later again, the same command returned **five** modified tracked files —
`README.md` and `plugins/python/skills/test-conventions/SKILL.md` had joined them — plus three
untracked documents that are not this session's.

A concurrent writer is editing `plugins/`, `README.md` and `docs/` right now. Nothing in this
record touched those paths, and the commit carrying this file uses an explicit pathspec
(`git add -- <path>` then `git commit -m … -- <path>`, verified against
`git diff --cached --name-only` returning exactly one line) so that it cannot pick them up.
**Any later session reading "tree clean, you are the only writer" in a brief should re-probe rather
than believe it** — the clean reading had a shelf life of about two minutes here, and the brief for
this session asserted it as a settled precondition.

**Seven gitignored bytecode files are sitting in the publish payload, and `publish-check` blocks on
them.** `python -m lemmi_ai_kit publish-check` exits 1 with `gitignored in the payload (7)`, all
seven under `plugins/core/src/lemmi_ai_kit/__pycache__/`. They are **not** from this session's
invocations, and that is proven rather than assumed:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run python -c "import sys; print(sys.dont_write_bytecode)"   # True
uv run python -c "import sys; print(sys.dont_write_bytecode)"                             # False
```

`uv run` propagates the variable correctly, so no invocation carrying it could have written
bytecode. The rule in the working brief is sound; something ran without it. **This is left in
place, not cleaned** — see §7.

---

## 1. The deliverable table, settled

`landed` means the artifact exists and the claim it makes about the tree is true today.
Twenty-two rows; `topology.md` §1 numbers them D1–D22 with D12 split into a and b, so twenty-three
identifiers.

| # | Verdict | Evidence |
|---|---|---|
| **D1** pack-payload verdict | **ruled out — never delivered, question overtaken** | `git ls-files -- 'docs/research/*pack-payload*'` → 0. `tasks/R1-CODEX-PAYLOAD-PROBE.md` is a prompt for a host that is not installed (`command -v codex` → absent). The tree moved anyway under I-2; the layout question was answered by doing it |
| **D2** five audit findings cleared | **landed** | `python -m lemmi_ai_kit audit-skills --skills-dir plugins/core/skills --fail-on major` → `0 finding(s)`, exit 0. Same for `plugins/python/skills`. Was 3 MAJOR + 2 MINOR on 2026-08-23 |
| **D3** `analyze-logs` genericized, re-filed to core | **landed** | `git ls-files -- '**analyze-logs**'` → `plugins/core/skills/analyze-logs/`. `realtime-session-events.md` is now `session-event-streams.md`. `SKILL.md:113` states the frame explicitly: "worked examples of two platforms, not the supported set". The two GCP references and the Docker one survive **as** worked examples, which is what D3 asked for |
| **D4** `openai-realtime-quirks` dropped | **landed** | `ls plugins/*/skills \| grep realtime` → no match. `git grep -l` finds 12 files; 7 are historical records under `docs/research/`, and of the remaining 5 none is a live dependency: `docs/migrating-from-0.1.0.md:142` announces the removal, `docs/upstream-sync.toml:353` files it under `[[unported]]` with a reason, `tests/test_manifest.py:29` asserts it is absent, and two core skills carry it inside illustrative changelog entries |
| **D5** `vertical-slice` re-filed to core | **landed** | `git ls-files -- '**vertical-slice**'` → `plugins/core/skills/vertical-slice/SKILL.md`. The DoD-4 violation the re-file was predicted to create is gone — see D7 |
| **D6** `extras` out of `PROFILES` | **landed** | `plugins/core/src/lemmi_ai_kit/manifest.py:14-29`. `PROFILES` is `core, skill-authoring, research, orchestration, python`; the bias comment is rewritten to say pack boundaries are enforced by layout |
| **D7** cross-pack names replaced by role | **landed** | For each of the two python-pack skills, `git grep -l -- "<name>" -- 'plugins/core/skills'` → 0. **Probe proven:** the same pattern against `plugins/` returns `plugins/python/skills/python-conventions/SKILL.md` and the asset manifest, so the grep is not silently empty. The only core-tree hits are the manifest's own catalog rows (`assets/manifest.toml:210,222`), which are registration, not routing |
| **D8** DoD-4 guard test | **landed, and proven non-blind** | `tests/test_pack_boundaries.py`. It carries its own non-vacuity assertion (`assert python_skill_names`), and its search roots resolve through `skill_dir()` to the real post-restructure trees: reconstructed in-process, **38 roots, 97 files scanned**, sample root `plugins/core/skills/kit-setup`. The module docstring still says "pre-restructure skill catalog", which is stale prose over correct code |
| **D9** the restructure | **landed** | `dcb8c15`. `git ls-files -- '*plugin.json'` → 6 (4 for core+python, 2 for the later `_template`); `git ls-files -- '*marketplace*'` → 2. `.claude-plugin/marketplace.json` sources `./plugins/core` and `./plugins/python`; the Codex catalog uses `source: local` with per-pack paths |
| **D10** `test_plugin.py` across all packs | **landed** | `tests/test_plugin.py` iterates `PACKS` in every assertion (identity, path resolution, marketplace membership, per-pack skill dirs). The literal `source == "./"` assertion named in `topology.md` is gone |
| **D11** `_MANIFEST_FILES` widened | **landed, better than specified** | `tests/test_readme_counts.py:78-87`. It is **derived** from `PACKS` by comprehension, not widened by hand, with a comment naming the failure that motivated it. See §3 for the one tree it still does not reach |
| **D12a** sync map reconciled to the new skill **set** | **landed** | `tests/test_upstream_sync.py` asserts `mapped == shipped` and `mapped == listed`; suite green. The dropped skill moved to `[[unported]]` with a stated reason |
| **D12b** sync machinery repointed at the new **location** | **landed** | `tests/test_upstream_sync.py:42` imports `shipped_skill_dirs()` instead of reading `assets_root()/"skills"`, and carries a floor assertion so an empty enumeration cannot pass. `docs/syncing-from-upstream.md:310` now says `--skills-dir plugins/core/skills`. `git grep 'src/lemmi_ai_kit/assets/skills' -- . ':!docs/research'` → exit 1, **probe proven** by the same grep on `src/lemmi_ai_kit` returning hits in five tracked files |
| **D13** README repoint | **landed** | Install command, invocation prefix (`/lemmi-ai-kit-core:kit-setup`), and the structure claims all describe the two-pack layout. `tests/test_readme_counts.py` holds the count half. The README additionally carries the F8 caveat in prose at `README.md:90-99` |
| **D14** pack template | **landed** | `git ls-files -- 'plugins/_template/'` → 4 files: two host manifests, `README.md`, and `skills/example-skill/SKILL.md`. Commit `aa574ed` |
| **D15** `new-pack` subcommand + tests | **landed** | `plugins/core/src/lemmi_ai_kit/cli.py:169`. `--help` lists `{scaffold,list,lint,audit-skills,publish-check,new-pack}`. Ten `test_new_pack_*` tests in `tests/test_cli.py`, including the round-trip that must satisfy `test_plugin.py` |
| **D16** `kit-setup` pack-aware + `### Project rules` seam | **landed** | `plugins/core/skills/kit-setup/SKILL.md` §2 recommends packs without installing them and refuses to invent a pack name; `references/packs-and-hosts.md` is the per-host command table. The seam is real at `assets/templates/AGENTS.md:166`, and `SKILL.md:176` documents append-under-heading behaviour rather than the old bare TODO. Commit `df2b173` |
| **D17** `docs/authoring-a-pack.md` | **landed** | Tracked, 144 lines. Commit `d5cc088` |
| **D18** `docs/adoption-guide.md` | **landed, but carries three false claims** | Tracked, 643 lines, commit `7c1c237`. **See §2 — this is the finding of this review** |
| **D19** `CONTRIBUTING.md` pack section | **landed** | `CONTRIBUTING.md:181` "Contributing a pack", with the naming rule at `:217` and the harm-remedy at `:277`. Commit `845c0e7` |
| **D20** `docs/migrating-from-0.1.0.md` | **landed** | Tracked, 158 lines. Carries the unverified-shorthand caveat at `:65` |
| **D21** W3.4 authoring proof | **OPEN — the document failed its own falsifier** | `docs/research/2026-08-24-i4-pack-authoring-proof.md`. 0 of 10 cold, ~7 of 10 realistic with 3 rows blocked, and the record argues against its own charitable number: the environment auto-injects project memory, so the subagent could not be starved of context. Its own §"Verdict" asks for a re-run elsewhere. **Not settled** |
| **D22** completion review, forward plan, partition | **this document** | — |

**Rows in the brief's I4 summary that the tree confirms.** R-1's verdict is absent and the tree
moved without it (D1). I-2 is `dcb8c15`, direct to `main`. V-1 ran post-merge and found the split
correct at install level, filing both its findings *outside* the split — §2 of its record is a
packaging-governance control, §3 is the wheel. X-1 correctly did not fire: neither V-1 finding is a
restructure defect. I-4 was reopened three times after landing (`ddf0086`, `3c34e1f`, `579c949`)
and none of those commits touched what §2 below reports.

---

## 2. The finding: `docs/adoption-guide.md` tells adopters that shipped features do not exist

Three passages in a flip-bound, adopter-facing document are false against the tree:

| Line | Claim | Falsified by |
|---|---|---|
| `:91-92` | contributing a pack back "is not documented yet" | `CONTRIBUTING.md:181`, D19 |
| `:528-531` | "**Authoring is not documented yet.** There is no pack template, no scaffolding command, and no `docs/authoring-a-pack.md` in this repository today." | D14, D15, D17 — all three exist |
| `:627` | the *Not built* table row "**No pack template, no scaffolding command, no `docs/authoring-a-pack.md`**" | same three |

`docs/faq.md:248-251` inherits the error by pointing readers at that section.

**Two of the three went stale; one was wrong on arrival, and the difference matters.** Commit order
from `git log --oneline`:

```
845c0e7  CONTRIBUTING pack section (D19)          <- before the guide
7c1c237  Add the adoption guide (D18)             <- the guide
aa574ed  Give a pack a skeleton and a command     <- D14, D15, after
d5cc088  Document the pack path end to end        <- D17, after
```

`:528` and `:627` were true when written and were falsified by I-3 landing afterwards — ordinary
staleness, and the phase-2 concurrency the plan bought is exactly what produced it. `:91` was
already false when the guide was committed, because D19 was in `main` first. That one is not a
staleness problem; it is a session writing a limits section from its brief rather than from the
tree.

**The document contradicts itself in the same table.** `:629`'s neighbouring row on pre-merge
review *was* updated to say "The path itself is now documented — see CONTRIBUTING.md". So the file
has been reconciled once against D19 at one line and not at another.

**No record in `docs/research/` flags any of this** — `git grep -n -i 'adoption-guide' --` over the
I-3 and S-2 handoffs returns nothing. It was found here for the first time.

**Not fixed by this session.** C-1 owns one file. This needs an owner — §4.

---

## 3. The four open items, re-measured — one of them refuted

**F8 — the `owner/repo` install form, still never exercised. Confirmed open.**
`command -v` for `claude`, `codex`, `cursor-agent`, `grok` → all four absent; `gh` present. No host
CLI exists on this machine, so the public install path cannot be tried here at all. It remains the
only test that path will ever get, and the flip is 2026-08-29. Both the README (`:90-99`) and the
adoption guide (`:638`) already say so in prose, which is the right disclosure and not a substitute.

**V1-F2 — the wheel packages zero skills. Confirmed, and it is worse than "latent".**
Previously reasoned from `pyproject.toml`. Now measured: `uv build` into a scratch directory, then
inspection of the artifact.

```
wheel entries                     25
entries containing /skills/        0
entries under assets/             12
assets/manifest.toml present    True
```

Installed into a throwaway venv and run from a neutral directory:

```
available_packs()  -> ()
load_manifest()    -> ManifestError: no plugin skill roots found
lemmi-ai-kit list  -> error: no plugin skill roots found      (exit 2)
```

So the artifact is not merely skill-less; the manifest **ships without the tree it validates
against**, and every command that loads it dies. The severity upgrade is what happens next:

```
lemmi-ai-kit audit-skills  ->  "no skills directory, so there is nothing to
                                audit (a project with only plugin skills is the
                                normal case)"
                               0 finding(s).   exit 0
```

**The audit passes green having audited nothing.** `list` fails loudly, which is safe; `audit-skills`
succeeds silently, which is not. That is the same shape as the guards this repo spent 2026-08-24
correcting, one artifact over. The brief's "no adopter path reaches it" still holds — plugin
installs never run `pip` — so this stays deferred, but it should be deferred as a *silent* failure,
not a dormant one.

**F20 — REFUTED as stated. The ban is enforced over the shipped skill trees.**
The claim was that the `.claude/skills/<name>/scripts/` rule is unenforced across the shipped skill
files. It is enforced. `tests/test_assets.py:_asset_text_files()` scans `assets_root()` **plus**
`skills_root(pack) for pack in PACKS`. Reconstructed in-process:

```
files scanned by _asset_text_files()        108
  of which under plugins/*/skills/           94
F20 regex                    \.claude/skills/[A-Za-z0-9_-]+/scripts/
regex matches a known-positive string      True
live occurrences across scanned files         0
```

The zero is a real zero: the regex was fired against a synthetic positive in the same run before the
count was taken. `test_publication_hygiene.py`'s `_ALREADY_COVERED` exclusion of the two skill
trees is therefore correct rather than blind, which is the thing worth re-checking, because that
exclusion is exactly where a wrong belief would hide. The residual risk the finding named — an
upstream refresh re-importing what extraction rewrote nineteen times — is now carried by a test.

**The I2 extraction debt — confirmed open, unchanged.**
`docs/upstream-sync.toml:80` → `status = "unreviewed"`.
`docs/research/2026-08-24-extraction-window-remainder-measured.md:214` → 36 of 92 lines resolved, so
**56 remain**, with an adjudicated worklist at that record's §"The remaining worklist". Its own
caveat stands: 92 is a ceiling, not a total.

### One gap this review found while checking F20

**`plugins/_template/` is guarded by the contamination rules but not by the payload rules.** The
template is the seed `new-pack` copies into every future pack, and it falls between two scans:

| Scan | Covers `_template`? | Why |
|---|---|---|
| `test_assets.py` (`_FORBIDDEN` + `_ASSET_ONLY_FORBIDDEN`) | **no** | iterates `PACKS`, and `_template` is deliberately not a pack |
| `test_publication_hygiene.py` (`_FORBIDDEN` only) | yes, all 4 files | not in `_ALREADY_COVERED` |
| `test_readme_counts.py` (`_MANIFEST_FILES`) | **no** | derived from `PACKS` |

Measured in-process: `_tracked_text_files()` returns 92 paths including all four `_template` files;
`_asset_text_files()` returns 108 paths including **zero** of them.

So the four DoD-4 payload rules — the unshipped-linter names, the console-script invocation form,
the stacked-PR doc path — never apply to the template, and neither does the stale-count guard on its
two `plugin.json` files. Nothing is wrong in those four files today. The point is that the one file
designed to be copied is the one file the payload rules do not read. Latent, cheap to close by
adding `_template` to those two scans' roots, and **not closed here** because both files are
outside this session's ownership.

---

## 4. Forward plan — what remains, and who it belongs to

Ordered by whether the flip on **2026-08-29** makes it more expensive.

### Before the flip

| Item | Why now | Owner |
|---|---|---|
| **The three false claims in `docs/adoption-guide.md`** (§2) | It is the document a stranger follows on day one, and it currently routes them away from three shipped features. Fixing it after publication means correcting a page people have already read. Owner must also fix `:91`'s root cause — the limits section was written from a brief, so it needs re-deriving against the tree, not patching line by line | A doc session owning `docs/adoption-guide.md` alone. One file, disjoint from the concurrent writer in `plugins/core/skills/` |
| **`publish-check` is currently blocking** (§0) | `PUBLISH BLOCKED (2 of 3 probes non-empty)` — seven ignored bytecode files plus the concurrent writer's two uncommitted skill edits. Whoever publishes must clear both. The remedy the tool prints is `git clean -Xdn -- plugins/core plugins/python` to preview, then `-Xdf` | Operator / the flip runbook. **Not done here** — §7 |
| **F8, the `owner/repo` form** | It becomes testable the moment the repo is public and untestable before. Whatever runs at that instant is its first and only exercise | The flip runbook, `tasks/FLIP-RUNBOOK-2026-08-29.md`. Needs a host CLI on some machine; none is on this one |

### After the flip

| Item | Why deferred | Owner |
|---|---|---|
| **D21 re-run** | The proof needs an author with no memory of this project, and this environment auto-injects it. Not solvable by trying harder here — it needs a different machine or a different account | Unowned. This is the one I4 deliverable that is genuinely **not settled**, and the initiative should not be reported as complete without saying so |
| **V1-F2, the wheel** | No adopter path reaches it. But it emits a silently green audit (§3), so the fix should also make `audit-skills` refuse to report success when it found no tree to audit | Packaging. Two candidate fixes: `force-include` the skill trees, or make the wheel refuse to build without them |
| **`plugins/_template/` scan gap** (§3) | Latent; nothing wrong in the four files today | Whoever owns `tests/test_assets.py` and `tests/test_readme_counts.py` |
| **I2 extraction debt, 56 of 92 lines** | Has an adjudicated worklist already | Its own initiative. `status` stays `"unreviewed"` until the 92 are closed |
| **I5, guided onboarding** | Not started. Depends on the `### Project rules` seam D16 shipped | I5. **This is the reason `.specs/i4-pack-split/` cannot be retired** — see §5 |

### Two register rows that should be recorded as not-run, not as done

D1 (R-1's verdict) and D21 (R-2's proof) are the initiative's two Research rows and its two declared
falsifiers. One was never delivered and the tree moved without it; the other was delivered and
**failed**. A completion report that lists twenty of twenty-three identifiers as landed and stops
there would be describing an initiative that tested itself. It did not: it shipped the work and its
own two tests of that work are, respectively, absent and negative.

---

## 5. The deletion partition — what is tracked, what is not, and what that costs

Run at close, with the sanity probe alongside so a zero cannot be mistaken for a broken command:

| Path | `git ls-files` | Files on disk | Recoverable after deletion? |
|---|---|---|---|
| `.specs/` | **0** | 11 | **No.** No commit, no reflog, no history |
| `tasks/` | **0** | 12 | **No.** Same |
| `docs/research/` | **42** | 42 | Yes — every file is in history |
| *probe sanity:* `docs/` | 48 | — | the enumeration works; the two zeros above are real |

**The exclusion mechanism is itself unrecoverable, which sharpens the point.**

```
$ git check-ignore -v .specs/i4-pack-split/execution-plan.md
.git/info/exclude:11:.specs/     .specs/i4-pack-split/execution-plan.md
```

`.specs/` and `tasks/` are excluded through `.git/info/exclude`, not `.gitignore`. That file is
per-checkout and in no commit either. A fresh clone of this repository has neither the documents nor
the rule that keeps them out — so "it is in git somewhere" is false twice over.

**`.specs/i4-pack-split/` is cited by 13 files, 9 of them tracked and flip-bound.**
`grep -rln 'i4-pack-split' tasks/ docs/ .specs/` returns 4 files under `tasks/`, 5 tracked records
under `docs/research/`, and the spec triple itself. The live ones:

- `tasks/I5-FEATURE-guided-onboarding.md:19` cites `execution-plan.md:159` (the I-5 row) and `:318`
  cites `:157` (the I-3 row, which carries the `### Project rules` seam I5 builds on). Both target
  lines exist and are the rows named.
- `tasks/I5-FEATURE-guided-onboarding.md:377` states outright that if `execution-plan.md` is lost,
  the sequencing argument goes with it.

**`docs/research/` is not retirable in the same sense at all.** It is tracked, it is flip-bound
under ruling F9, and `docs/research/README.md` states the standing rule for the whole directory: a
superseded record is *corrected in place, not deleted*. Retiring a spec directory and retiring a
research record are different acts with different reversibility, and conflating them is how the
irreversible one gets done casually.

**What would make retirement safe later.** Not a date — a condition: `grep -rl 'i4-pack-split'`
returning only the spec triple itself. Today it returns thirteen. The first thing that changes that
number is I5 starting and either consuming or superseding the two cited rows.

---

## 6. What this review did NOT verify

- **No install was performed.** No host CLI is on this machine (§3, F8), so nothing here re-checks
  what materializes per pack. D9's correctness at install level rests entirely on V-1's record of
  2026-08-23, which is one execution on one host on one day.
- **The wheel test proves the artifact is broken, not that no adopter reaches it.** "No adopter path
  reaches `pip install`" is inherited from the brief and V-1; this session did not enumerate adopter
  paths independently.
- **The three modified files under `plugins/core/skills/` were not read or reviewed.** They belong
  to a live concurrent writer. Their content is unknown to this record and their effect on the
  suite's `249 passed` is unmeasured — the suite ran *before* they appeared.
- **`docs/adoption-guide.md` was audited for the pack-authoring claims specifically**, prompted by
  the `:627` hit. The sweep that found them covered seven flip-bound documents for
  not-yet/unverified phrasing, but it is a phrase sweep, not a full re-derivation of the guide's
  643 lines against the tree. **There may be more.** The `:91` case shows the failure is not only
  staleness, so a phrase sweep is the wrong instrument for the general problem.
- **D2's audit was re-run, not re-derived.** It reports zero findings at `--fail-on major` today;
  this record did not confirm that the five original findings are the same five the tool would have
  named, only that the gate the deliverable specified now passes.
- **Counts of the two Research rows were taken from their own records**, not re-executed. R-2's
  scoring in particular is a judgment this session accepted rather than reproduced.

---

## 7. What was judged unsafe to do, and left undone

**The seven bytecode files under `plugins/core/src/lemmi_ai_kit/__pycache__/` were not deleted.**
They block `publish-check`, and `git clean -Xdf -- plugins/core plugins/python` would clear them.
Two reasons not to:

1. A concurrent writer is active in this checkout (§0) and may be mid-import. Deleting bytecode out
   from under a running interpreter is a cheap way to hand someone else an unexplainable failure.
2. `-X` deletes ignored files, and this session cannot enumerate what the other writer's tooling
   considers disposable.

The remedy is the tool's own printed command, and it belongs to whoever is publishing — at which
point the tree must be clean anyway for the *other* blocked probe.

**Nothing under `.specs/` or `tasks/` was retired, per the orchestrator ruling that overrode the
register row.** §5 records what a later retirement needs. This session judges the ruling correct on
the evidence it gathered independently: the citation count is 13, not 0, and the mechanism keeping
those files out of git is itself uncommitted.

**`docs/adoption-guide.md` was not corrected**, though the fix is three edits and this session found
the defect. C-1 owns one file. Recording a defect you could have fixed is the weaker outcome, and it
is the correct one when the alternative is a Clean Up session writing into another session's
declared file set while that session's neighbours are actively writing the same tree.

### This session amended a concurrent writer's commit, and the recovery is why §0 exists

Recorded because this repository publishes what its workflow catches, and this one it caught
afterwards rather than before.

The first commit of this record landed as `603590f` with a **malformed subject line: a bare `@`.**
The message was passed with PowerShell here-string syntax (`-m @'…'@`) through the Bash tool, where
`@` is an ordinary character — so the shell delivered a message beginning and ending with a literal
`@`. The environment offers both shells and they take different syntax; this is the failure mode of
using one's quoting in the other, and it is silent.

The recovery attempt did the real damage. `git commit --amend -F <file>` was chained behind a
`git log -1` check with `&&`. **A verification chained to the action it is meant to gate does not
gate it** — the shell ran both, and the output arrived too late to stop anything. In the interval,
the concurrent writer of §0 had committed `8c2c55b` on top. The amend therefore rewrote *their*
commit, producing `269db27`: their tree, their parent, this session's message.

Restored with `git reset --soft 8c2c55b` after verifying the two commits were message-only
divergent:

```
tree 8c2c55b   794ea4cfc8c98dfaa5a637077b2be2ae7c72816d
tree 269db27   794ea4cfc8c98dfaa5a637077b2be2ae7c72816d
parent, both   603590f
```

`--soft` moves the ref without touching index or working tree, so the writer's uncommitted edits
were never at risk. Verified after: `git diff --cached` empty, their four in-progress paths still
present.

**`603590f`'s `@` subject is left in history deliberately.** Correcting it means rewriting a commit
that a concurrent writer has already built on, in a checkout three sessions share — which is the
exact manoeuvre that makes work disappear, traded against a cosmetic subject line. The commit's body
is intact and its content is this file.

Two rules this pays for, neither of which was in the working brief:

1. **Re-probe `HEAD` in its own call before any history rewrite**, and read the result, in a shared
   checkout. `--amend` is not a local edit when someone else may have committed since.
2. **Never chain a safety check to a destructive command with `&&`.** The check must be a separate
   call whose output is read first.

---

## 8. Where this record's verification stops

Every number above names the command that produced it, and each was run in this session against
`HEAD 53c0a56`. Three probes were checked for the failure this repo keeps paying for — a zero that
means the instrument is broken rather than the tree is clean:

- the D7 cross-pack grep, proven by the same pattern returning hits one directory over;
- the D12b stale-path grep, proven by its own prefix returning five tracked files;
- the F20 regex, fired against a synthetic positive in the same process before its count was taken.

The glob `plugins/*/skills` still returns 0 from `git ls-files` on this shell while the explicit
two-path form returns 96 (92 core + 4 python) — the known liar, re-confirmed rather than
rediscovered. Any count in a future record derived from that glob is wrong.

The suite figure `249 passed, 6 skipped` was measured before the concurrent writer's three edits
appeared and is not a claim about the tree as it stands now:

```sh
T=$(mktemp -d); PYTHONDONTWRITEBYTECODE=1 uv run pytest -q --basetemp "$T"; rm -rf "$T"
```
