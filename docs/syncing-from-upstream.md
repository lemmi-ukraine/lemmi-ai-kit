# Syncing the skill pack from upstream

The skill pack was extracted from a private source project once (2026-07-02..07-09) and
refreshed once (2026-08-23). Between those two dates upstream made 43 commits to its
skills tree and the pack fell to roughly a third of upstream's content on its worst
skills — in about six weeks, not gradually. A one-shot re-port would be stale again
within two months, so the sync channel is a shipped deliverable rather than a chore.

This document is the procedure. It has three parts: what is recorded, how to measure
drift, and how to carry a change across without breaking portability.

---

## 1. The three artifacts

| File | Role |
|---|---|
| [upstream-sync.toml](upstream-sync.toml) | The pin and the correspondence map. The only place a SHA or a skill's provenance is recorded |
| [../tests/upstream_sync.py](../tests/upstream_sync.py) | The drift check. Reads the record, measures against an upstream checkout, prints a report. **Always exits 0** |
| [../tests/test_upstream_sync.py](../tests/test_upstream_sync.py) | The gates. Everything checkable without upstream: record validity, map/pack correspondence, and the measurement arithmetic against a synthetic repository |

The split matters. Upstream is private and absent from CI, so a check that needed it
would be unrunnable exactly where it is wired. Instead the parts that can rot without
upstream are hard gates on every run, and the measurement itself is a report a
maintainer runs locally before a sync.

## 2. Measuring drift

```sh
LEMMI_UPSTREAM_REPO=/path/to/upstream uv run python tests/upstream_sync.py
```

`--repo PATH` overrides the environment variable; `--upstream-ref REF` measures against
something other than the checkout's `HEAD`. The upstream path is never committed — the
source project is private, and the hygiene contract bans naming it in a tracked file.

The report has six possible findings:

| Finding | Meaning | Action |
|---|---|---|
| `BEHIND` | Upstream commits have touched a skill's directory since that skill's base | Port them (§4) |
| `UNDECLARED` | An upstream skill in neither the map nor the unported list | Decide it: port, or add an `[[unported]]` row with a reason |
| `VANISHED` | A declared upstream skill no longer exists upstream | Upstream deleted or renamed it; update the map |
| `MAP ERROR` | A row points at a directory absent at that row's own base ref | The row is wrong — a bad upstream name or a bad base |
| `EXTRACTION WINDOW` | Skills an earlier sync based on a commit from inside the extraction window | Per-skill read (§3c) |
| `NOT MEASURED` | No upstream checkout was reachable | Normal in CI. Not a pass |

`MAP ERROR` exists because `git rev-list --count` over a path that does not exist
returns 0. Without that check a row with a typo in its upstream name would report "in
sync" forever while measuring nothing — the failure mode that turns a check into a
rubber stamp.

**Drift is counted in commits, not content, and that is deliberate.** The refresh dropped
82 upstream lines on purpose — banned patterns, unshipped infrastructure, unreachable
pointers, machine-specific rules. A content diff or a per-skill hash would report all 82
as drift on every run, forever, and would be silenced within a month. A commit count is
zero the moment a sync lands and stays zero until upstream actually moves.

## 3. The three rules that make this non-obvious

### 3a. Compare three-way, never two-way

The two repositories share no git history. In a two-way kit-versus-upstream diff, an
upstream advance and a deliberate portability edit are **the same shape** — both appear
as lines upstream has and this repo does not. So a two-way gap is not a work estimate,
and following one mechanically reverts the extraction edits the hygiene contract exists
to protect.

Measured, when this was checked against the real merge base rather than assumed:

| Assumed from a two-way gap | Measured three-way |
|---|---|
| 26 skills need refreshing | 7 needed nothing — byte-identical upstream since extraction. Refreshing them would have reverted the extraction edits |
| `skill-reviewer` is 2,275 words behind | Only **+195** was upstream advance. The other 91% is this repo's own generalization work |
| `test-conventions` is +4,089 behind | The real upstream advance in SKILL.md was **+1,308**. The rest was content this repo deleted as non-portable |

Those three rows are still the right lesson, but read them with §3c in hand: they were
themselves measured against a base four days too new, so "needed nothing" means "nothing
after 2026-07-06". Three of the four skills upstream never touched between that base and
the pin are on the window list — they had moved, just earlier than the base could see.

Get the base content with `git show <base>:<skills-path>/<name>/SKILL.md` in the upstream
checkout, where `<base>` is that skill's `base` from the record. Then diff base→upstream
(the real advance) and base→shipped (this repo's own edits) separately, and merge. Listing
section headings across the three sides is usually enough to classify:

| base | shipped | upstream | Verdict |
|---|---|---|---|
| present | absent | present | A deliberate kit deletion. **Keep it deleted** |
| absent | absent | present | Genuine new upstream content. Assess portability, then port |
| present | present | changed | A real upstream edit to carry |

### 3b. Direction is not always downstream

Two skills **originate in this repo**. `orchestrate` (as `fable-orchestrate`) and
`agent-delegate` entered here 2026-07-03 and upstream 2026-07-13, byte-identical at 6,775
and 3,153 bytes. Upstream is downstream: its later edits to those files are contributions
to review, not a backlog to absorb, and their merge base is the commit where upstream
received the copy — not the extraction point, where neither existed.

Two documents assumed the opposite before it was measured. That is why the record carries
a `direction` column with three values (`upstream-origin`, `kit-origin`,
`divergent-both`) rather than name pairs, and why the report phrases those rows
differently. A `kit-origin` row must cite the upstream commit that received the copy —
the loader rejects the claim otherwise, so it stays falsifiable.

Correspondence is not name equality either: three skills dropped a `lemmi-` prefix on
extraction, one had a typo corrected (`analyge-logs` → `analyze-logs`), and two have no
upstream counterpart at all. Read the map; never derive it.

### 3c. The extraction window is not a point — and the last sync got this wrong

This is the second-order version of §3a, and it cost more than the first-order version
would have. Comparing three-way is not enough if the base is the wrong commit.

This repo's first commit is 2026-07-02T23:26. The last upstream commit touching the
skills tree before that is 2026-06-25 — that is the true base, and it is what
`sync.extraction_base` now records. But the 2026-08-23 refresh used a commit dated
**2026-07-06** as the base for every skill: four days *inside* the extraction window.

Three upstream commits fall in that gap. They add **2,668 insertions across 16 skill
directories** (15 shipped skills plus one declined). 1,024 of those belong to the two
linters and their tests, which this kit deliberately does not ship — leaving exactly
**1,644 insertions of skill content** that the refresh's base could not distinguish from
this repo's own deletions.

Why that is worse than a mis-measurement, and not merely an inaccuracy in a table: the
classification rule in §3a reads *present at base, absent in ours, present in theirs* as
a deliberate kit deletion — **keep it deleted**. Every line upstream added inside the
window is present at the too-new base, so all of it was eligible to be read that way and
dropped without anyone noticing. The refresh's own carry audit measured against the same
base, so it could not have caught this either.

Measured rather than inferred: **all 19 window-added lines of `skill-researcher/SKILL.md`
are absent from the shipped file, and that skill reports zero drift against the pin.**
Some of those lines are correctly absent — they carry source-project rules — which is
exactly why this needs a per-skill read and not a bulk re-merge.

The report shows this as its own `EXTRACTION WINDOW` block, deliberately **not** folded
into the per-skill drift counts. Drift answers "has upstream moved since we synced"; this
answers "did an earlier sync read upstream's additions as our deletions". Merged, 16
skills would sit permanently "behind" and the ongoing signal would be drowned — which is
how a check gets silenced. The affected list is recorded so the debt is visible without
an upstream checkout, and re-derived from git whenever one is available; a name the record
missed is reported as `RECORD INCOMPLETE`.

**Clearing it:** for each affected skill, diff `extraction_base` → the too-new base for
that directory, and decide each added hunk on portability — port it, or record why it
stays out. Then set `extraction_window.status` and say what was carried. Do not delete
the table silently; a test requires it to be present or deliberately closed.

**`extraction_base` is a default, not the base.** At least three skills need a per-skill
override, and the way to find them is mechanical rather than a judgment call: for each file,
diff the shipped copy against **every** upstream revision of it and take the
minimum-distance commit. No interpretation required, and it is decisive in practice — for
the retrospective extractor the true base scored 9 diff-lines against 271 for the
next-closest revision. Do this before merging any skill whose base you have not verified,
and record the result as that row's `base`.

**The transferable rule:** an extraction window is a range of commits, not an instant. Pick
the base by the *timestamp of the first commit of the extraction*, verify no upstream commit
touching the tree falls between that base and the extraction, then confirm per file by
minimum distance. Otherwise the base carries content the extraction never saw, and a
three-way merge will attribute it to you.

## 4. The procedure

1. **Run the report** (§2). If it is clean, there is nothing to sync.
2. **Handle `UNDECLARED` and `VANISHED` first.** They change the *set* of skills, which
   changes the manifest, the README counts and the plugin indexes. Deciding them before
   any content work keeps those edits in one commit instead of three.
3. **For each `BEHIND` skill, merge three-way against its own `base`** (§3a). Not against
   the pin — the record overrides `base` exactly where the pin is untrue.
4. **Clean the carried content against the hygiene contract.** `tests/test_assets.py` is
   the enforcement, and it will reject naive copies by construction: upstream content
   carries machine paths, dated citations, project references, and references to
   infrastructure this kit does not ship. Do not add allowlist entries to make a refresh
   green — an allowlist entry is a claim that the file *teaches* the banned rule.
5. **Replay the rename map onto new content** rather than hand-editing it. Upstream still
   uses the `lemmi-` prefixes and the pre-rename skill names.
6. **Check the command forms an adopter can actually reach.** A skill that names
   `lemmi-ai-kit <sub>` names a console script from `[project.scripts]`, which exists
   only after a pip or uv install of the distribution. A plugin install places skills and
   never installs the package. The reachable form is
   `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit <sub>`. This defect
   reached 16 call sites across 10 skills once, and it resolved in testing only because
   the development environment had the package installed. **When a skill names a command,
   check it against the install path the adopter uses, not the one the developer has.**
7. **Run the four checks:** `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run basedpyright`, `uv run pytest`. If a vocabulary test in `test_checks.py` goes
   red because upstream added a changelog type or a learnings category, that is the alarm
   working — extend the constant in `src/lemmi_ai_kit/checks.py`. Do not loosen the test
   to keep a refresh green.
8. **Update the record last.** Move `sync.upstream_commit` to the revision you merged
   from, refresh `synced_on`, and drop the `base` override from every skill you actually
   carried. A skill you did not carry keeps its override — that is how the next sync
   knows its base is older than the pin.
9. **Re-run the report.** It should now be clean for everything you touched.

**Commit shape.** Skill-content refreshes are journal-class and travel with the content.
The hygiene-contract extensions, the CLI, and this check are reviewed code and belong in
their own commits. A manifest rename goes alone. Every commit boundary must leave
`assets/manifest.toml` consistent with the shipped skill directories — `uv run pytest` is
that check, and a half-updated manifest blocks every other session working on the tree.

## 5. What is deliberately not ported

Seven upstream skills are declined, each with its reason recorded in the
`[[unported]]` rows of [upstream-sync.toml](upstream-sync.toml). In summary:

- **`feedback-audit`, `interview-transcript-analysis`** — the source project's interview
  product. Same coupling class this pack removed four prompt-engineering skills for.
- **`prompt-domain-reviewer`, `prompt-eng-reviewer`, `prompt-engineering-conventions`,
  `review-prompts`** — removed as product-coupled. This repo was measurably *ahead* of
  upstream on two of them, which is evidence of extraction-time generalization rather
  than neglect.
- **`usage-guard`** — deferred, not rejected. Generically valuable, but 12,509 words of
  which 9,049 are PowerShell, tied to a scheduled task and a statusline feed. It needs a
  cross-platform pass, as its own task, never inside a sync.

Beyond skills, four deliberate divergences will show up as diffs on every future sync.
They are **correct** diffs:

- **Upstream's file linter and skills auditor are not shipped.** The kit's CLI replaces
  both (`lint`, `audit-skills`). Shipping upstream's scripts alongside the CLI would mean
  two implementations disagreeing about what is valid, since the CLI deliberately drops
  four upstream rules. This departs from the original infrastructure ruling on purpose,
  and the departure is ratified.
- **Skill-owned scripts are shipped with a working-directory fallback.** A fixed
  `parents[N]` depth breaks from a plugin install, so each walks up for a marker and
  falls back to the current directory.
- **Upstream's `.cursor/` and `.kiro/` thin references** are out of scope for a Claude
  Code plus Codex plugin.
- **No hooks.** Upstream enforces some rules with a `PreToolUse` hook; this kit ships
  none, so a rule whose enforcement is a hook arrives as a suggestion. Port the rule
  knowing that, or leave it.

## 6. Known outstanding debt

**`session-retrospective` is 8 upstream commits behind and is the one row whose `base` is
still the extraction point.** The report says so on every run, and it is the reason this
check could be observed to be accurate before being trusted: on its first run against a
real upstream checkout it reported exactly one skill behind — the one independently known
to have been deferred — with the other 35 tracked skills at zero, and zero map errors,
undeclared additions or vanished rows.

It is deferred because a mechanical merge was attempted and reverted. The merge reported
13 conflicts that all resolved to "take upstream", which looks clean; it produced an
extractor of 1,400 lines against upstream's 1,547, with 8 of 35 tests failing — new
function bodies without the constants they read. A partial version is worse than either
side alone, and it failed loudly only because that file is well tested.

Root cause, and it is the §3c defect in miniature: the merge was based on the too-new
2026-07-06 commit. Upstream added the extractor's schema v4 on 2026-07-05 — **three days
after this repo extracted** — so diffing from that base rendered the entire v4 feature set
as a deliberate kit removal of roughly 1,100 words. Against the true base the edit set is
four small hunks totalling about 13 words. The blocking premise was a measurement
artifact, and the row's `base` in the record has been corrected accordingly.

Based correctly, that merge produces **3 conflicts rather than 13**, with zero in the
extractor, its tests, and the output-schema reference.

**State at the time of writing:** a reconciliation of this skill was complete in the working
tree but not yet committed, so this record still describes it as unmerged — the row keeps
its `base` override and its `divergent-both` direction. That choice is deliberate. If the
record claimed the skill were reconciled and the work did not land, the check would report
"in sync" for a skill ten commits behind: a silent false negative. Claiming it is behind
when it is not produces a loud false positive instead, which a maintainer investigates and
fixes. **Whoever commits that reconciliation should update the row in the same commit** —
drop the `base` override and the `divergent-both` direction, then re-run the report.

One constraint survives regardless: the schema version is stated in the script and in both
reference documents, so the skill moves whole or not at all, and upstream's newer
`sweep_user_corrections.py` needs its own portability read.

## 7. Promotion criteria — when a report becomes a gate

Both of the kit's upstream-facing checks ship as reports and are promoted only on
evidence. Recording the criteria here is what stops "promote it later" from meaning
"never".

**The drift check → a CI gate.** Promote when all three hold:

1. Two consecutive syncs have run where the report's `BEHIND` set matched the set of
   skills the maintainer independently intended to carry — no false positives from the
   kit's own divergences, no misses.
2. `session-retrospective` is reconciled, so a clean run is actually reachable. Until
   then a gate would fail every build for a known, accepted debt.
3. The extraction-window debt (§3c) is cleared or explicitly accepted. A gate that fires
   on 16 skills of known, unreviewed debt teaches people to ignore it.
4. CI has a way to reach an upstream checkout. Without it, promoting the gate would
   promote `NOT MEASURED` to a pass — the worst outcome available, because it looks
   green.

Criterion 1 is one sync in. Criteria 2, 3 and 4 are open.

**`audit-skills --fail-on major` → a CI gate.** Promote once the five open audit findings
are cleared. Measured on the shipped pack at the time of writing, all five are still open
and all five are inside the skill directories:

| Severity | Finding |
|---|---|
| MAJOR | `ai-docs-lookup`: `metadata.type` missing — set `type: task` |
| MAJOR | `kit-setup`: `metadata.type` missing — set `type: workflow` |
| MAJOR | `initiative-cleanup`: SKILL.md 556 lines > 500 — move detail into `references/` |
| MINOR | `ai-docs-lookup/README.md` — delete; the modern mechanism is `description` |
| MINOR | `test-conventions/README.md` — delete; a bare duplicate frontmatter block |

Gate at `major`, not `minor`: minor findings are review input, and gating on them makes
the suite brittle. Re-measure with
`uv run python -m lemmi_ai_kit audit-skills --skills-dir src/lemmi_ai_kit/assets/skills`
rather than trusting this table — it is a snapshot.

## 8. What this check does not see

Stated plainly, because a check's blind spots are the part that gets forgotten:

- **It counts commits, not content.** It cannot tell a one-word typo fix from a 5,000-word
  rewrite. It answers "has upstream moved", not "how much work is this".
- **It says nothing about quality or portability.** A `BEHIND` skill might be entirely
  unportable content. Only reading it tells you.
- **Prose generalization is unmeasured.** The 82 deliberately-dropped lines are a floor on
  this repo's intentional divergence, not a total.
- **It measures the checkout it is pointed at.** A maintainer on a stale or feature-branch
  upstream checkout gets a confident answer about the wrong tree. `--upstream-ref` exists
  for that; the report prints the resolved SHA so the answer is auditable.
- **The window block counts commits, not missing lines.** It says which skills were based
  on the wrong commit, not how much of that content is actually absent from the pack.
  Only the per-skill read in §3c answers that; the one skill spot-checked was missing all
  of it.
- **`NOT MEASURED` is not a pass.** It is the absence of a measurement, printed so the
  absence is visible instead of silent.
