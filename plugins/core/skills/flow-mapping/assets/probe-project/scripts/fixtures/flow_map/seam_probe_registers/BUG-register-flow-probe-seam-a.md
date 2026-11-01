# Seam-detector probe registers, side A (fixture, not a register of anything real)

> **SCHEMA FIXTURE — not runtime documentation, and not a valid register.** Read by
> `scripts/find_absent_cross_flow_seams.py --registers` against the corpus in `seam_probe/`, to
> certify which register bullets count as a disposition. Its sibling is
> `BUG-register-flow-probe-seam-b.md`; read the `EXPECTED` table below before changing a bullet.
>
> **EXPECTED, per candidate of the (probe-seam-a.md, probe-seam-b.md) pair:**
>
> | symbol | disposed? | why |
> |---|---|---|
> | `ProbeAbsentSeam.sweep_only` | yes | the first entry carries a `Residue verdict:` bullet that names the full symbol and both documents |
> | `ProbeVerdictSplit.fail_here_unknown_there` | yes | the sibling file carries a `Verdict ownership:` bullet, wrapped over two lines, that names the full symbol and both documents |
> | `ProbeLinkedSplit.linked_fail_unknown` | yes | the sibling file's second entry carries a `Verdict ownership:` bullet that names the full symbol and both documents |
> | `ProbeVerdictAgree.fail_here_pass_there` | **no** | the second entry holds three near misses: one names a single document, one has no marker, one names only the bare suffix |
>
> **One invariant a future edit must preserve:** no bullet below may name the undisposed symbol in
> full, with a marker, and with both documents. Adding one disposes it and the probe stops
> having a known-negative.

### R-probe-seam-a-01 · disposed by a residue marker
- **Residue verdict:** shared-entry-no-seam — `ProbeAbsentSeam.sweep_only` is one shared entry point reached from `probe-seam-a.md` and `probe-seam-b.md`, so no cross-flow row is owed.

### R-probe-seam-a-02 · three near misses for the one candidate that stays undisposed
- **Residue verdict:** real-gap-row-written — `ProbeVerdictAgree.fail_here_pass_there` in `probe-seam-a.md`, with no second document named.
- **Reconciled against:** `ProbeVerdictAgree.fail_here_pass_there` in `probe-seam-a.md` and `probe-seam-b.md`, under no disposition marker.
- **Verdict ownership:** `probe-seam-a.md` owns the verdict for `fail_here_pass_there`, which `probe-seam-b.md` records as PASS.
