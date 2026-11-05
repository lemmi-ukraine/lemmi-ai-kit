# Seam-detector probe registers, side B (fixture, not a register of anything real)

> **SCHEMA FIXTURE — not runtime documentation, and not a valid register.** The sibling of
> `BUG-register-flow-probe-seam-a.md`, which carries the `EXPECTED` table. The bullet below is
> wrapped on purpose: the symbol and the second document sit on the continuation line, so a
> matcher that reads only the first line of a bullet cannot dispose of its candidate.

### R-probe-seam-b-01 · disposed by an ownership marker
- **Verdict ownership:** `probe-seam-b.md` owns the verdict for
  `ProbeVerdictSplit.fail_here_unknown_there` against `probe-seam-a.md`, which records FAIL
  where this document records UNKNOWN.

### R-probe-seam-b-02 · disposed by an ownership marker on a linked pair
- **Verdict ownership:** `probe-seam-a.md` owns the verdict for `ProbeLinkedSplit.linked_fail_unknown`; `probe-seam-b.md` records UNKNOWN where the first records FAIL.
