# I-4 · D18 adoption guide — handoff

**Dated:** 2026-08-23. **Row:** I-4 (`.specs/i4-pack-split/execution-plan.md`). **Deliverable:** D18.
**Written to the hand-off contract** in `plugins/core/src/lemmi_ai_kit/checks.py`
(`HANDOFF_REQUIRED_SECTIONS`), so it lints rather than merely reads well.

## Scope

Wrote `docs/adoption-guide.md` (605 lines) — the four-adopter-case guide, D18, the last
document in I4's minimal viable initiative.

Did **not** write: `CONTRIBUTING.md` (I-5, and it needs the OP-I4-1 cross-initiative
ruling), `docs/authoring-a-pack.md` (I-3/D17), the pack template, or `new-pack` (D14/D15).
Did not touch the restructure. One path added, nothing else in the tree modified.

**Two operator rulings were obtained this session and they are not recorded in any planning
document — they are the most perishable thing in this hand-off.**

| Question | Ruling (operator, 2026-08-23) |
|---|---|
| **OQ-4** | **"Four Go teams" is a TYPO.** It means *teams using Go instead of Python* — a language with no pack. There is no four-team isolation requirement. The charter, `roadmap.md` (OQ-4 and §1.4), `topology.md`, and `00-KICKOFF-PROMPTS.md` all still carry the wrong framing and were **not** corrected in place |
| **OQ-3** | **Private-overlay-first.** The guide leads with "attach your conventions in your own repo"; contributing a pack back is an optional later step. Shipped as §2, *"You probably do not need to author a pack"* |

The OQ-4 correction dissolved the blocker: repo topology was recorded as a discriminator
"only the operator has", because four teams sharing one repo would share one
`### Project rules` block. With the framing dropped, Case 2 is two paragraphs.

**A third item was raised and deliberately not built.** The operator asked for a guided
onboarding interview — user describes their project and existing conventions, the agent
reads the code and derives a project map and conventions — and immediately scoped it out:
*"this one may be an additional big step for the roadmap instead of this session scope."*
`kit-setup` does the detection half only. Recorded in the guide's "Not built" table; it has
**no charter, no initiative row, and no deliverable id.**

## Durable anchors

- `docs/adoption-guide.md` — the deliverable, untracked
- `plugins/core/skills/kit-setup/SKILL.md` — the seam's real mechanism (agent prose, not code)
- `plugins/core/src/lemmi_ai_kit/scaffold.py` — `_decide()`, the seed semantics Case A rests on
- `docs/research/2026-08-23-i4-pack-split-implementation-handoff-to-orchestration.md` — the install verification the guide's §3 cites
- `3938ddf` — HEAD when this was written; the restructure is **not** in it

## Preconditions

- `git log --oneline -1` -> `3938ddf`; if HEAD moved the restructure may have landed, re-read §3 of the guide before trusting it
- `git status --porcelain | wc -l` -> `141` while the split is uncommitted (140 were Codex's, 1 is the guide)
- `git status --porcelain -- docs/adoption-guide.md` -> `?? docs/adoption-guide.md` — untracked, so `git clean -xdf` destroys it
- `ls plugins/core/skills | wc -l` -> `35`, and `ls plugins/python/skills | wc -l` -> `2`; the guide hardcodes both

## Verification

- `wc -l < docs/adoption-guide.md` -> `605`
- `grep -c '^\`\`\`' docs/adoption-guide.md` -> `48`, an even count, so no unbalanced fence
- `grep -c '^### [ABCD]\.' docs/adoption-guide.md` -> `4`, the four cases, case A first
- `grep -c 'codex plugin update' docs/adoption-guide.md` -> `0`; that command was drafted, found to exist nowhere in the repo, and removed as fabricated
- `grep -c 'invocation = "user"' plugins/core/src/lemmi_ai_kit/assets/manifest.toml` -> `24`, the count the guide tells adopters to expect in their `/` menu
- `git status --porcelain -- CONTRIBUTING.md` -> empty; I-5's file was not touched

## Status

**ready-for-review.** The deliverable is written, its factual claims are re-verified against
the tree, and its acceptance check is the operator's — `roadmap.md` §1.5 row 5 defines it as
*"operator reads it cold"*, which no session can perform for itself.

**It cannot land yet, and that is not a defect in it.** Every install command in the guide
describes a layout that exists only in the working tree. If the restructure is reverted
rather than committed, the guide is wrong in its entirety. It must land **in or after** the
split commit, never before. Per `topology.md`, B3 is a branch off `main` post-L1-merge; L1
has not merged, so it could not be branched cleanly without entangling Codex's 139 paths.

### For the next session

1. **Do not re-derive OQ-4 from the planning documents.** Four of them are wrong. Read the
   Scope table above first.
2. **Do not re-verify the pack split.** It was install-verified 2026-08-23 (codex-cli
   0.149.0, isolated `CODEX_HOME`, 37 skills materialized). See the anchored handoff.
3. **Three claims in the guide are marked unverified and should stay marked** until someone
   can run them: the Claude Code install path (doc-verified only, `claude` absent from
   PATH), the `owner/repo` marketplace transport (F8, untestable while the repo is
   private), and nested `AGENTS.md` pickup in a monorepo (host behaviour, not kit
   behaviour). Do not quietly upgrade these to asserted.
4. **The guide will need one edit at the flip** if F8's 30-second transport check fails —
   §3's "If the `owner/repo` shorthand does not resolve" already carries the fallback, so
   the edit is to the verification note, not to the instructions.
