# Session handoff — I1 and I3a executed. Read this first.

**Dated:** 2026-08-22, at session close. **Executed:** I1 (complete), I3 Part A (complete).
**Not started:** I3 Part B, I2, I4.
**Nothing is pushed.** All four branches are local. Publishing them is the operator's call.

This is the execution-side handoff. A planning-side one exists at
`.specs/i3-oss-discoverability/handoff-to-orchestrator.md` (private, never committed — see §6). Where
they disagree on what shipped, this one was written from `git`.

---

## 1. Merge order — there is no ordering requirement. Three branches, not four.

```
main
 └── i1-decouple-prompt-skills ....... I1 complete
      └── f3-stale-counts ............ CONTAINS i1 — merging this lands both
main
 └── i3a-contribution-surface ........ I3a complete, independent
main
 └── readme-drop-unbacked-refresh-claim  independent
```

**Merge `f3-stale-counts`, `i3a-contribution-surface`, and
`readme-drop-unbacked-refresh-claim`, in any order. Do not merge `i1` separately** — it is
subsumed.

> **Corrected 2026-08-22, after this document first claimed the opposite.** An earlier
> version said *"`f3-stale-counts` descends from `i1`, so it cannot merge first"*. That
> inverts the consequence of its own premise. Descending from `i1` is precisely why `f3`
> **can** go first: it is a fast-forward that carries `i1` with it. Measured:
>
> ```
> git merge-base --is-ancestor main f3-stale-counts                → 0  (fast-forward)
> git merge-base --is-ancestor i1-decouple-prompt-skills f3-…      → 0  (f3 contains i1)
> git rev-list --count f3-stale-counts..i1-decouple-prompt-skills  → 0  (i1 has nothing f3 lacks)
> ```
>
> Confirmed by doing it: merging `f3` alone into `main` yields 29 skill dirs, README at
> "29 skills", the four deleted skills absent, 31 tests passing — and a subsequent
> `git merge i1-decouple-prompt-skills` reports **"Already up to date."**
>
> The correct weaker statement: `f3`'s README-at-29 is only true when the 29-skill tree is
> present, and **containment guarantees that** — no merge ordering is required to achieve
> it. Read as an ordering rule, the original invented a separate merge of `i1` that is
> redundant at best. Flagged as an error in the worst possible place: the section labelled
> as the one constraint that could not be reordered.

**Verified, not assumed:** all branches merge clean and the merged result passes the full
gate — `ruff`, `ruff format`, `basedpyright` strict, **39 tests**, 29 skill dirs, 29
manifest entries, README at 29, zero unbacked refresh claims. Independently reproduced by a
second session, twice, from a fresh clone. Re-run before merging:

```bash
git checkout -b MERGE-VERIFY main
for b in f3-stale-counts i3a-contribution-surface \
         readme-drop-unbacked-refresh-claim; do
  git merge --no-edit "$b" || echo "CONFLICT: $b"
done
uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run pytest
```

**Verified, not assumed:** all four merge clean, and the merged result passes the full
gate — `ruff`, `ruff format`, `basedpyright` strict, **39 tests**, 29 skill dirs, 29
manifest entries, README at 29, zero unbacked refresh claims. Re-run before merging:

```bash
git checkout -b MERGE-VERIFY main
for b in i1-decouple-prompt-skills f3-stale-counts \
         i3a-contribution-surface readme-drop-unbacked-refresh-claim; do
  git merge --no-edit "$b" || echo "CONFLICT: $b"
done
uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run pytest
```

## 2. What each branch delivers

| Branch | Delivers |
|---|---|
| `i1-decouple-prompt-skills` | Four prompt-review skills removed (33 → 29), `prompts` profile dropped from both tuples, 5 content references repointed, the seeded prompt-review mandate removed from `templates/AGENTS.md`. **8,734 words** of capability leave, recorded in the removal commit. |
| `i3a-contribution-surface` | `LICENSE` (MIT) + the five other community files + 4 issue forms; a license-drift test across **three** sources; `pyproject.toml` license and `license-files`; a tracked-tree hygiene guard; five research documents. |
| `f3-stale-counts` | The four stale public counts corrected, **plus the test that keeps them correct** (README ↔ manifest, and no counts in any plugin manifest). |
| `readme-drop-unbacked-refresh-claim` | Removes a README paragraph advertising a `kit-setup refresh` mechanism that does not ship. |

Every test that guards something was verified by deliberate breakage and then restored —
the license-drift test three ways, the hygiene guard three ways, the count guard three ways.

## 3. Decisions already taken — do not re-litigate these

| Decision | Value | Decided by |
|---|---|---|
| OP-1 / OQ-1 license | **MIT** | program §5b, shipped |
| OQ-2 CLA/DCO/neither | **Neither** — MIT inbound=outbound | operator, 2026-08-22 |
| OQ-3 contacts | **`support@lemmi.io`** for maintainer, security, conduct | operator, 2026-08-22 |
| I1 OQ-1 | **Delete** `post-task-review`'s prompt-template check | operator |
| I1 OQ-2 | **Drop** both `openai-realtime-quirks` citations | operator |
| I1 OQ-3, OQ-4 | Illustrative example; rule stays coherent | session, from reading the code |
| Flip date | **2026-08-29 as planned**, OP-3 to be re-decided | operator, 2026-08-22 |
| README exceptions | **Two, both surgical**: the four counts, and the refresh claim. The rewrite stays behind I4's Gate D | operator |
| `tasks/` + `.specs/` | **Do not commit** — see §6 | session, as hygiene-contract owner |

**A divergence worth knowing about:** OQ-2 and OQ-3 were answered *differently* in two
parallel sessions on the same day (`.specs/…/roadmap.md:357` records the superseded pair).
The operator was shown both accounts and confirmed the values above. If a document still
says DCO or "GitHub-native contact", it is stale.

## 4. Recommended next actions, in priority order

**P0 — has a hard deadline and no owner.** Capture the traffic baseline **on 2026-08-29**:
`gh api repos/lemmi-ukraine/lemmi-ai-kit` for stars/forks/watchers at t=0, then
`/traffic/views` and `/traffic/popular/paths`. The API retains **14 days**. Miss it and
"did discoverability work?" is permanently unanswerable — which is the defect I3 exists to
fix. `gh` is currently unauthenticated in this environment.

**P0 — flip-critical, no owner.** The README advertises a Codex install path nobody in this
environment can verify (`command -v codex` is absent). Worse, `tests/test_plugin.py:89`
asserts `source["path"] == "./"` — the shape the program doc says Codex rejects — so a
manifest-only fix goes **red** and reads as if the fix were wrong. Either qualify the
Codex block before the flip or fix manifest *and* test together.

**P1 — expires on the flip date.** OP-3. Its rationale (program line 193: *"breakage is
near-zero now and compounds weekly"*) was a property of being private. After 2026-08-29
I4's rename breaks real installs. Option space is narrower than "re-decide" implies — see
the Part B handoff §4 for the three shim shapes, which is feasible, and the two
implementation traps.

**P2 — operator, cheap, any time.** Re-split `i3a` so `LICENSE` sits alone in its own PR,
per the charter's explicit instruction. Cleanly separable at `1d61cae`, no history rewrite.
Recorded as a deviation, not a pass.

**P2 — operator.** Send one test message to `support@lemmi.io`. The domain accepts mail
(full Google Workspace MX set plus matching SPF, measured) but the alias is unconfirmed,
and it is now the security *and* conduct channel in three published documents.

**P3 — I2/I4.** `learning-consolidator` hardcodes 29 IDE-specific paths while
`skill-reviewer:153` forbids them "unless justified". Nothing mechanical catches it. The
cheap fix is to write the justification, not strip 29 references.

## 5. Two DoD rows that cannot be signed yet — and are not defects

- **I3a DoD #4** (community-standards checklist): every required file is present, but the
  checklist itself lives in GitHub's Insights UI and is unreadable on a private repo.
  **Unverified, not passed.** Signable at the flip.
- **I3a DoD #5** (clone → four checks using only `CONTRIBUTING.md`): content verified in a
  fresh clone, all four checks clean. But CONTRIBUTING's literal first command
  (`git clone https://github.com/…`) fails for an outsider. **Partial.** Resolves at the
  flip with no code change.

Both were previously reported as passes. Corrected — see the completion review.

## 6. `tasks/` and `.specs/` — untracked, and should stay that way

Both trees are untracked and **were never committed on any branch** (verified: 0 files).
Do not commit them.

The reason is not the hygiene contract, though they would now fail it — the tracked-tree
guard added on `i3a` catches the source-project name in any tracked file, so committing
them can no longer happen silently. The real reason is that **stripping that name would not
make them safe.** `tasks/I2-TECH-port-upstream-skills.md` (private planning artifact — not committed to this repository) publishes a named inventory of a
private repository's skills — 13 entries with word counts and dependency counts — plus
internal script names, a product-line attribution, and one line of internal usage
telemetry. **Four** occurrences of the name; **13** inventory rows that survive removing all
four. Redaction makes that unattributed, not safe.

If the planning record should be public, that is a **rewrite**, not a redaction, and a
decision separate from I3. A verified byte-for-byte backup already exists outside the
working tree, so the loss risk that argued for committing them is already handled.

## 7. Read these, in this order

1. [`2026-08-22-i3a-completion-review.md`](2026-08-22-i3a-completion-review.md) — the
   adversarial review of this session's own output, including what was overstated
2. [`2026-08-22-i3-part-b-handoff.md`](2026-08-22-i3-part-b-handoff.md) — Part B scope, the
   pre-flip gate, OP-3's option table
3. [`2026-08-22-publication-reachability.md`](2026-08-22-publication-reachability.md) — the
   repo is private; the three independent install blockers
4. [`2026-08-22-anchor-terms-sourced.md`](2026-08-22-anchor-terms-sourced.md) — 13 terms,
   11 sourced, 1 dropped, 1 reworded
5. [`2026-08-22-kit-setup-dogfood-verdict.md`](2026-08-22-kit-setup-dogfood-verdict.md) —
   what works, and the one advertised mechanism that does not

## 8. One correction to the program document

`00-PROGRAM-oss-launch.md`'s header says the repo is *"(already public)"*. **It is not.**
Measured three ways and reproduced by a second session: the REST API returns 404, the org
has zero public repos, and an anonymous `ls-remote` with credential helpers disabled demands
a username. The same command *succeeds* with helpers enabled — which is the most likely way
the original claim was made, and the trap to avoid re-making.
