# Flow — Seam-detector probe corpus, side A (QA)

> **SCHEMA FIXTURE — not runtime documentation, and not a flow map of anything real.** This is one
> half of the two-document corpus that certifies `scripts/find_absent_cross_flow_seams.py`. Its
> sibling is `probe-seam-b.md`. Together they plant one instance of each behaviour the detector's
> five probes assert, so the probes decay only when a fixture is edited — never when the live
> `docs/flows` corpus is *fixed*. Read `EXPECTED` below before changing a cell.
>
> **EXPECTED, per symbol, for the (A, B) pair:**
>
> | symbol | what the detector must say | which probe |
> |---|---|---|
> | `ProbeAbsentSeam.sweep_only` | residue — no cell names it, no row targets its scenarios | known-POSITIVE |
> | `ProbeNamedInProse.cell_names_me` | NOT residue, link kind `strong` — B's cell names it in full | known-NEGATIVE |
> | `ProbeRowLevelOnly.target_id_links_me` | NOT residue, link kind `row-level` — only a target id links it | known-POSITIVE (row-level) |
> | `ProbeVerdictSplit.fail_here_unknown_there` | verdict disagreement — FAIL here, UNKNOWN in B | known-POSITIVE (disagreement) |
> | `ProbeVerdictAgree.fail_here_pass_there` | NOT a disagreement — FAIL here, PASS in B, no UNKNOWN | known-NEGATIVE (disagreement) |
>
> **Two invariants a future edit must preserve**, because breaking either silently weakens a probe
> rather than failing it:
>
> 1. Neither the string `ProbeAbsentSeam.sweep_only` nor its bare suffix `sweep_only` may appear in
>    ANY *Cross-flow scenarios* contribution cell in either document — the bare-suffix match is what
>    the detector calls a `weak` link, and it would suppress the known-positive.
> 2. No cross-flow row hosted here may target a scenario that `probe-seam-b.md` maps to
>    `ProbeAbsentSeam.sweep_only`, and vice versa — that is the `row-level` rule, and it would
>    suppress the known-positive structurally, with no prose to notice.

## Scenarios

| # | class | trigger | path | verdict | evidence |
|---|---|---|---|---|---|
| QA-01 | main | the fixture's absent-seam symbol runs on this side | `ProbeAbsentSeam.sweep_only` | PASS | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-b.md maps the same symbol with no row between the two` |
| QA-02 | main | the fixture's prose-linked symbol runs on this side | `ProbeNamedInProse.cell_names_me` | PASS | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-b.md names this symbol in full inside a contribution cell` |
| QA-03 | main | the fixture's row-level-linked symbol runs on this side | `ProbeRowLevelOnly.target_id_links_me` | PASS | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-a.md hosts a row whose target id is this symbol's scenario on the sibling side` |
| QA-04 | edge | the disagreeing symbol fails on this side | `ProbeVerdictSplit.fail_here_unknown_there` | FAIL | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-b.md records UNKNOWN for the same symbol` |
| QA-05 | edge | the agreeing symbol fails on this side | `ProbeVerdictAgree.fail_here_pass_there` | FAIL | `code: scripts/fixtures/flow_map/seam_probe/probe-seam-b.md records PASS for the same symbol, and no UNKNOWN exists on either side` |

## Symbol index

| symbol | file | scenarios | called by | invariants |
|---|---|---|---|---|
| `ProbeAbsentSeam.sweep_only` | `scripts/fixtures/flow_map/seam_probe/probe-seam-a.md` | QA-01 | _none_ | _none_ |
| `ProbeNamedInProse.cell_names_me` | `scripts/fixtures/flow_map/seam_probe/probe-seam-a.md` | QA-02 | _none_ | _none_ |
| `ProbeRowLevelOnly.target_id_links_me` | `scripts/fixtures/flow_map/seam_probe/probe-seam-a.md` | QA-03 | _none_ | _none_ |
| `ProbeVerdictSplit.fail_here_unknown_there` | `scripts/fixtures/flow_map/seam_probe/probe-seam-a.md` | QA-04 | _none_ | _none_ |
| `ProbeVerdictAgree.fail_here_pass_there` | `scripts/fixtures/flow_map/seam_probe/probe-seam-a.md` | QA-05 | _none_ | _none_ |

## Cross-flow scenarios

| scenario | owning flow | this document's contribution |
|---|---|---|
| QB-03 | `scripts/fixtures/flow_map/seam_probe/probe-seam-b.md` | this row exists to link its target STRUCTURALLY and nothing else: it names no symbol at all, so the only thing tying it to a symbol is that QB-03 is one of that symbol's scenarios on the sibling side. That is the `row-level` rule under test. Do not add a symbol name to this cell. |
