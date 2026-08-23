# Session handoff — I2 Gate B option (c): `lint` and `audit-skills` are in the CLI

**Dated:** 2026-08-23, at session close. **Executed:** the (c)-substitute half of Gate B
decision D2 — the two CLI subcommands that replace the cross-skill script calls.
**Nothing is committed and nothing is pushed.** Three files changed, listed below.

**Read §3 first if you are Session D.** It is the table of call sites you can now rewrite,
and it is the only part of this document that unblocks other work.

Companion documents:
- [2026-08-22-i2-portability-triage.md](2026-08-22-i2-portability-triage.md) §5–§6, §11 D2 — the decision this implements
- [../../tasks/I2-TECH-port-upstream-skills.md](../../tasks/I2-TECH-port-upstream-skills.md) — the charter, whose OP-2 D2 revises

---

## 1. What landed

| File | State | Lines |
|---|---|---|
| `src/lemmi_ai_kit/checks.py` | **new** | 1,440 |
| `tests/test_checks.py` | **new** | 1,333 (104 test functions, 109 cases with parametrisation) |
| `src/lemmi_ai_kit/cli.py` | modified | +216 / −2 |

**No asset was touched.** `assets/skills/**` and `assets/manifest.toml` were read but never
written — Session D held them throughout, and the tree moved four times under me (33 → 36
skills, `branch-diff-review`, `initiative-cleanup`, `initiative-planner`,
`pr-comment-resolver`, `pr-review-concise`, `stacked-pr-planner` all arrived mid-session).

## 2. The public API, named once and deliberately

Both subcommands become a published contract the moment a skill or a CI job scripts against
them, so the surface is small on purpose. Every name below is a decision, not a default.

```
lemmi-ai-kit lint [TARGET] [--project DIR] [--since YYYY-MM-DD]
                           [--list-entries] [--resolve-anchors]

  TARGET   all (default) | learnings | changelog | hypotheses | handoffs
  exit     0 clean · 1 findings · 2 misuse (bad flag, explicitly-named missing file)
  prints   <relative-path>:<line>: [ERROR ]<message>
           --- <target>: N finding(s) ---
           LINT PASSED (0 finding(s)) | LINT FAILED (N finding(s))

lemmi-ai-kit audit-skills [--project DIR] [--skills-dir DIR]
                          [--fail-on {none,blocker,major,minor}]

  exit     0 always, unless --fail-on names a severity that is present
  prints   skill fleet audit: <relative-dir>
           BLOCKER|MAJOR|MINOR|NOTE|INFO (N)
             - <skill>: <message>
           N finding(s). <verdict>.
```

Four naming calls worth recording, because each replaced something upstream had:

- **`--since YYYY-MM-DD` replaces a hardcoded policy cutoff and `--all-entries`.** Upstream
  pins a 2026-07-01 constant because it has pre-policy history; an adopter's files ship
  empty, so the kit's default is *check everything* and the cutoff is the adopter's to set.
  One flag instead of a constant plus its escape hatch. The structural checks ignore it
  entirely (§4).
- **`--list-entries` rather than a second verb.** Upstream's inventory mode is
  `ai_files_lint.py list learnings`, but `lint` is a subcommand and `list` is already taken
  by the skill catalogue. It is a reporting mode of `lint`, so it is a flag on `lint`.
- **`--fail-on` rather than upstream's always-0.** Findings-are-review-input is the right
  default and the three calling skills rely on it, but an always-0 command cannot gate
  anything — the self-review gate that cites "`audit_skills.py` exit 0" is vacuous today.
  `--fail-on major` makes it real without changing the default.
- **`--project DIR` on both.** `scaffold` takes its target positionally; `lint`'s positional
  is the *lint target*, so the directory has to be a flag, and `audit-skills` matches `lint`
  rather than `scaffold` so the two new commands agree with each other.

**Discovery, not `__file__`.** With no `--project`, the root is the nearest ancestor of the
working directory holding `.ai/` (preferred) or `.git/`, falling back to the working
directory. Installed as a plugin this module lives in a package cache with no ancestor
inside the adopter's project, so anchoring on `__file__` — which is what upstream's
`audit_skills.py` does via `parents[4]`, the defect §6 of the triage flagged — cannot work.

## Correction (2026-08-23, added by the session that consumed this)

**Every `lemmi-ai-kit <sub>` form in this document is not reachable for an adopter, §3's
rewrite table included.** `lemmi-ai-kit` is a `[project.scripts]` console script, so it
exists only after a pip/uv install of the distribution. The kit installs as a Claude Code
plugin (`/plugin install`), which places skills and never installs the Python package.

The reachable form is the one `kit-setup` already documents:

```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit <sub>
```

All 16 shipped call sites were rewritten to the module form, `cli.py`'s argparse `prog`
was corrected so `--help` stops teaching the console script, and
`tests/test_assets.py::_ASSET_ONLY_FORBIDDEN` now rejects the console-script form in
assets (mutation-tested, and the bare plugin name plus `/lemmi-ai-kit:<skill>` stay
legal). Read §3's right-hand column as naming the *subcommand*, not the invocation.

## 3. Cross-skill site coverage — what Session D can rewrite now

Re-measured against upstream at session close. The triage counted 6 + 3 = 9 sites; the
executable count is **10**, because `session-retrospective` has two, not one.

### `lint` covers 7 sites across 6 skills (was `learning-consolidator`'s `ai_files_lint.py`)

| Caller | Upstream invocation | Rewrite to |
|---|---|---|
| `ai-changelog` | `ai_files_lint.py lint changelog` | `lemmi-ai-kit lint changelog` |
| `ai-improvement-tracker` | `ai_files_lint.py lint hypotheses` | `lemmi-ai-kit lint hypotheses` |
| `consolidation-critic` | `ai_files_lint.py lint all` | `lemmi-ai-kit lint` |
| `hypothesis-validator` | `ai_files_lint.py lint hypotheses` | `lemmi-ai-kit lint hypotheses` |
| `session-retrospective` (2 sites) | `ai_files_lint.py list learnings` | `lemmi-ai-kit lint learnings --list-entries` |
| `task-learnings` | `ai_files_lint.py lint learnings` | `lemmi-ai-kit lint learnings` |

### `audit-skills` covers 3 sites across 3 skills (was `skill-reviewer`'s `audit_skills.py`)

| Caller | Upstream invocation | Rewrite to |
|---|---|---|
| `consolidation-critic` | `audit_skills.py` | `lemmi-ai-kit audit-skills` |
| `hypothesis-validator` | `audit_skills.py` (guarded "if that script exists") | `lemmi-ai-kit audit-skills` |
| `skill-creator` | `audit_skills.py` | `lemmi-ai-kit audit-skills` |

### Already in the shipped tree and dangling right now

`parallel-session-safety` landed this session carrying **three** references to
`ai_files_lint.py` that no shipped file backs. They are bare mentions, so they do not trip
the hard-coded-skill-script pattern the hygiene contract added — but they do violate DoD
item 4, and two of them are executable forms:

| Site | Now rewritable to |
|---|---|
| `parallel-session-safety/SKILL.md:209` — `ai_files_lint.py lint handoffs` | `lemmi-ai-kit lint handoffs` |
| `parallel-session-safety/SKILL.md:394` — `ai_files_lint.py lint all` | `lemmi-ai-kit lint` |
| `parallel-session-safety/SKILL.md:106` — prose, "detects the duplicate-header/spliced-entry artifacts" | prose fix; the behaviour is real (`check_entry_body_integrity`) |

**`handoffs` is a supported target specifically so those two can be rewritten rather than
stripped.** That is a change of scope from the triage, which did not count
`parallel-session-safety` among the callers because its references are not hard-coded paths.

## 4. Deliberate divergences from upstream, and why

Recorded here because each one is a place where a future sync will show a diff that is
**correct** and must not be "fixed" back.

**Three upstream rules dropped as project policy, not portable rules.**

| Dropped | Why |
|---|---|
| `POLICY_CUTOFF = 2026-07-01` and its `ALLOWLIST` of named historical entries | Both encode one project's history. The allowlist names specific upstream entry titles; shipping it would exempt strings no adopter has. Replaced by `--since`. |
| A 12th changelog type (`EXPERIMENT-REGISTERED`) | Added by an upstream decision record. The kit's `ai-changelog` skill documents an 11-type locked set; the lint enforces what the shipped skill teaches. |
| `disable-model-invocation: true` outside a two-name allowlist → MAJOR | The kit's own taxonomy *encourages* that flag on side-effect skills, so the allowlist would report the skills that follow the documented rule. The genuinely broken case — both invocation flags set, nobody can reach the skill — stays a BLOCKER. |
| `metadata.type: reference` without `user-invocable: false` → MAJOR | The shipped taxonomy makes it conditional ("when invoked only by workflows"). `openai-realtime-quirks` is a legitimate counter-example already in the pack. |

**Structural vs per-entry is now an explicit split.** Heading order, date validity, spliced
headings, duplicated field blocks, and misfiled hypothesis refs run **file-wide regardless
of `--since`**; only the format checks (title shape, required fields, vocabulary) are gated.
Merge damage predates no policy — a grandfathered entry corrupts as easily as a new one.

**Six correctness and portability fixes upstream never needed.**

0. **Fenced code blocks are documentation, not structure.** These files document their own
   format, so a fenced example is a date heading, an entry, or a field bullet — exactly the
   shapes every check looks for. Parsing them as real content reported *conforming* entries
   as broken, in three separate ways. Found at review, not during the work; see the
   completion review §2.
1. **BOM-tolerant reads** (`utf-8-sig`). A BOM on a `## ` heading line makes that heading
   unparseable, and every entry beneath an unparsed heading is collected into no block at
   all — so the lint reports **zero** findings on a file full of broken entries. Silent
   under-reporting, from an invisible three bytes a Windows editor adds.
2. **Case-exact `SKILL.md` detection.** `(dir / "SKILL.md").exists()` returns True for
   `skill.md` on Windows and on a default macOS volume, and the runtime will not load it.
   The directory listing is the only case-exact test that behaves the same on all three.
3. **ASCII-only output**, applied at the print boundary rather than by reconfiguring
   `sys.stdout` (which would break the caller's capture). Upstream's `ai_files_lint`
   reconfigures the stream; `audit_skills` ASCII-replaces. This does the latter, everywhere.
4. **Every printed path is relative to the project root.** This output gets pasted into
   hand-offs and retrospectives — an absolute path there is portable to one machine, and
   would seed exactly the contamination `tests/test_assets.py` exists to reject.
5. **Anchor resolution is opt-in** (`--resolve-anchors`) and note-only. It shells out to git
   per anchor; the default path is hermetic and identical on every platform.

**Two behavioural calls that differ from upstream and are debatable — flagging, not hiding.**

- **Hand-offs: no opt-in marker.** Upstream lints only files containing `handoff-contract:`,
  because it has pre-contract files on disk. The kit's `parallel-session-safety` documents
  the contract without documenting any marker, so requiring one would ship a lint nothing
  can satisfy — it would pass everything, silently. Every `*.md` in `.ai/handoffs/` is
  linted, `README.md` excepted. **If Session D ports the marker language into the skill, add
  the gate back** — it is additive.
- **A missing file under `lint` (no target) is a skipped note; naming it explicitly is exit
  2.** A project that has not scaffolded every log yet has nothing to lint, which is not a
  failure. Asking for a specific file that is not there is a user error.

## 5. What these two do NOT cover

Scope boundaries, so nobody assumes coverage that is not there:

- **`check <patterns.txt>`** (the mass-removal dry-run) — a *same-skill* call:
  `learning-consolidator` owns the script and calls it for itself, so D2 option (a) applies
  and it ships with the skill. Not a CLI subcommand.
- **`lint plans`** (`.specs/*/execution-plan.md`, the Dispatch-column vocabulary) — the
  convention belongs to initiative planning the kit does not ship a lint contract for yet.
  Adding a target later is additive; removing one is breaking, so it is omitted.
- **`drain_audit.py`, `test_ai_files_lint.py`** (1 cross-skill site each, both from
  `consolidation-critic`) and **`validate_realtime_export.py`** (1 site, both ends are
  charter non-goals). Unaddressed by design — the triage's own count was 9 of 14 in scope.
- **`extract_sessions.py`** (2 cross-skill sites) — already ships inside
  `session-retrospective`. Nothing to substitute; the sites need rewriting to the
  skill-directory variable, which is the (a) half of D2.
- **The hypotheses archive lint and the buffer/synthesis pressure notes.** They depend on
  rotation and cadence conventions no shipped skill defines. Not ported.

## 6. What the audit found in the kit's own pack, on day one

`lemmi-ai-kit audit-skills --skills-dir src/lemmi_ai_kit/assets/skills` — all true
positives, all verified by hand, none of them mine to fix (they are in Session D's tree):

```
MAJOR (3)
  ai-docs-lookup       metadata.type missing
  kit-setup            metadata.type missing
  initiative-cleanup   SKILL.md 556 lines > 500 -- move detail into references/
MINOR (2)
  ai-docs-lookup       README.md in the skill directory (entrypoint confusion)
  test-conventions     README.md in the skill directory (entrypoint confusion)
INFO
  36 skills; description+when_to_use total = 18,676 chars
```

Two skills carry no `metadata.type` while 34 do, and `initiative-cleanup` arrived this
session already over the 500-line cap the skill-authoring skills teach. **Decision needed:**
either fix the five, or rule that `metadata.type` is not a kit requirement — in which case
that check should come out rather than sit as permanent noise. `--fail-on` defaults to
`none`, so nothing is gated on this today.

*(This list shrank by one while the session ran: `test-conventions` gained a `metadata.type`
under Session D. The numbers move — re-run the command rather than quoting this block.)*

## 7. Verification

**The four checks are green**, run at session close on the shared tree:

```
uv run ruff check .          -> All checks passed!
uv run ruff format --check . -> 15 files already formatted
uv run basedpyright          -> 0 errors, 0 warnings, 0 notes
uv run pytest -q             -> 137 passed
```

Two things worth knowing about that pytest number. **It was red when I started** — 8 failed,
7 errors, every one from `manifest.toml out of sync with assets/skills` while Session D
staged skills ahead of their manifest entries. It went green mid-session when they synced.
None of those failures were mine, and none of my tests depend on the manifest: the audit
treats an unreadable catalogue as *unknown*, not empty (§8, first row).

**The 98 new cases passed on the first run, so I mutation-tested the load-bearing ones**
rather than trusting that. Five mutations, each reverting a deliberate design choice back to
the obvious implementation; all five were caught by assertion, not by crash:

| Mutation | Caught by |
|---|---|
| case-exact `SKILL.md` → `.exists()` | `test_a_lowercase_skill_md_is_a_blocker_on_a_case_insensitive_filesystem` |
| `utf-8-sig` → `utf-8` | `test_read_text_strips_a_byte_order_mark`, `test_a_bom_does_not_silently_swallow_the_whole_file` |
| unknown catalogue coerced to empty | `test_an_unreadable_catalog_suppresses_the_ghost_check_instead_of_guessing` |
| a changelog type removed from the constant | `test_changelog_types_match_the_shipped_skill` |

The BOM mutation is the reason this section exists: the **first** version of that test put
the BOM on a prose title line and **passed under the mutant**. It now puts the BOM where it
does damage, and asserts the three findings that go missing without the fix.

**Manual end-to-end, on Windows:** `scaffold` into a fresh directory → `lint` PASSED (0
findings) → `audit-skills` degrades to a NOTE with no local skills directory. The shipped
`.ai/` seed files lint clean, which is pinned as a test — a validator whose own corpus fails
trains people to ignore it.

**Not verified:** macOS and Linux. This platform was the only one available, same limitation
the W2.1 triage recorded. The portability work is *designed* for all three and the
case-sensitivity and BOM tests are meaningful on this one, but "runs green on Linux" is
unmeasured. CI covers it on the next PR.

## 8. Notes for whoever is next

**The vocabulary pinning tests couple this module to four shipped files.** Five tests assert
that `CHANGELOG_TYPES`, `LEARNINGS_SECTIONS` (keys *and* slugs), `HYPOTHESIS_CATEGORIES`,
`HYPOTHESIS_STATUSES` and the hand-off contract sections match what `ai-changelog`,
`task-learnings`, `ai-improvement-tracker`, the `improvement-hypotheses.md` seed and
`parallel-session-safety` document — **in both directions**. A one-sided check is not enough:
a value the skill documents but the lint rejects turns every conforming entry into a false
positive.

**This is a deliberate tripwire, and W2.2 will trip it.** Those four skills are all in the
refresh set, and upstream has already added a 12th changelog type and a seventh learnings
category (`Interaction & Workflow Friction`). When a refresh lands, the test fails naming
the constant and the file — update `checks.py` to match the skill. That is the drift alarm
the initiative exists to build, firing as intended, not a broken test.

**Three loose ends I did not take, all outside my ownership:**

1. `README.md:114` lists `src/lemmi_ai_kit/{cli,scaffold,manifest}.py` as "the support
   scripting code" and is now missing `checks.py`. No test covers that line. README was
   modified by another session throughout, so I left it — a one-word edit for whoever owns
   it next.
2. `CONTRIBUTING.md:66` says "Nine patterns are rejected" — the hygiene contract carries ten
   since W2.1b added the skill-script pattern. Also not mine, also untested.
3. **A manifest-vs-frontmatter cross-check is the obvious next audit**, and I did not add
   it: the kit declares each skill's `invocation` in `manifest.toml` while the SKILL.md
   declares `user-invocable` / `disable-model-invocation`, and nothing verifies they agree.
   It belongs in `tests/test_assets.py` (it is about the *shipped* pack, not an adopter's
   project), which is Session D's file right now.

**Nothing here is committed.** `checks.py` and `test_checks.py` are untracked; `cli.py` is
modified in place. Sequencing per the charter: this is reviewed code, not journal-class
content, so it belongs in its own layer — not folded into a skill-content commit.
