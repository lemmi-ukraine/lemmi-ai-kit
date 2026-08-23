# Output templates — Step 6 approval gate and Step 7 completion report

## Step 6 — the approval gate

Present this, then wait. Nothing is removed before it returns.

```markdown
## Cleanup plan — <initiative>

**Gates:** census exit <n> · coverage exit <n> · refs exit <n> per target · evidence exit <n> per symbol
**plan-critic:** reference files read — dor-tables.md, review-dimensions.md, finding-format.md
**Self-review (S-1..S-5):** <one line each, per references/self-review-gate.md>

**Board:** <n> rows settled, each with its verification command · <n> already terminal
**Forward plan:** .specs/<initiative>/forward-plan.md — <n> open decisions, <n> dated verifications

**Deletion set, partitioned PER FILE:**
| file | tracked? | 4a evidence (CODE symbol + path) | inbound refs (4b) | regenerable? (4c) | action | recovery |
|---|---|---|---|---|---|---|

**Nothing appears in this table as a deletion until 4a, 4b and 4c all pass.** A blank 4c cell on a
`.ai/tmp/` row is a stop, not a default. A DOC-ONLY or SHARED 4a verdict is not a deletion.
**Single-copy artifacts:** <untracked targets whose removal is permanent — name each>

**Retained deliberately:** <parked specs + revival triggers, decision records, corpora>
**Sequencing:** <before / after / with the open PRs — as answered by the operator in Step 0>
**Comment pass:** <n> files in scope · KEEP <n> · CUT <n> · SHORTEN <n> · RELOCATE <n>
**Not touched (other sessions' uncommitted work):** <list>

Proceed?
```

## Step 7 — the completion report

```markdown
## Cleanup complete — <initiative>

**Board:** <n> rows settled → <terminal states>, each citing its command
**Removed:** <n> tracked (git rm) · <n> untracked (copied to <backup-root>/<date>-<initiative>/ first)
**Implementation verified (4a):** <per file — the symbol, the CODE path it was found on, after `git fetch`>
**References repointed (4b):** <n> citations across <n> files → code-adjacent home / recovery command
**Inputs preserved (4c):** <what was classified INPUT and therefore NOT swept>
**Post-delete sweep:** `grep -rn '<basename>' --include='*.md' .` -> 0 hits outside recovery commands
  (working-tree grep, same scope as the pre-delete sweep — `git grep` cannot see untracked files)
**Single-copy warnings:** <artifacts now existing in exactly one untracked place, named>
**Left untouched:** <another session's uncommitted work, listed not swept>
**Retired with pointers:** <spec → changelog entry / parked spec → revival trigger>
**Comments:** −<n> lines cut, <n> shortened, <n> relocated to <spec>; <n> kept and why
**Preserved:** <corpora, decision records, and where they now live>
**Next initiative inherits:** .specs/<initiative>/forward-plan.md
```

Report **what was preserved and where**, not just what was removed. A cleanup report that lists only
deletions is unauditable.
