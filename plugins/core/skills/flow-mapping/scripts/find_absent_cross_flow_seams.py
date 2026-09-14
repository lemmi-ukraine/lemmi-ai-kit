"""Find missing cross-flow links and verdict disagreements.

Certifies its detector on bundled fixtures before inspecting the target corpus.
Structural candidates require source review; the sweep does not prove a bug.
"""

import argparse
import importlib.util
import io
import pathlib
import sys
from collections import defaultdict
from dataclasses import dataclass, field

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path.cwd().resolve()
DEFAULT_CORPUS = REPO / "docs" / "flows"
PROBE_CORPUS = (
    pathlib.Path(__file__).resolve().parent.parent
    / "assets/probe-project/scripts/fixtures/flow_map/seam_probe"
)

spec = importlib.util.spec_from_file_location(
    "vfm", pathlib.Path(__file__).with_name("validate_flow_map.py")
)
vfm = importlib.util.module_from_spec(spec)
sys.modules["vfm"] = vfm
spec.loader.exec_module(vfm)


def configure(project_root, code_root=None):
    global REPO, DEFAULT_CORPUS
    REPO = pathlib.Path(project_root).resolve()
    DEFAULT_CORPUS = REPO / "docs/flows"
    vfm.configure(REPO, code_root)


class CorpusUnreadable(Exception):
    """The population is not readable as a flow-map corpus: refuse to print a count over it."""


@dataclass
class Corpus:
    """One parsed flow-map population. Every analysis function takes one of these explicitly, so
    the fixture corpus the probes certify against and the live corpus the sweep measures are
    different objects and cannot be confused for one another."""

    root: pathlib.Path
    docs: dict = field(default_factory=dict)
    excluded: list = field(
        default_factory=list
    )  # (name, reason) -- out of population, deliberately
    pair_text: dict = field(default_factory=lambda: defaultdict(str))
    pair_n: dict = field(default_factory=lambda: defaultdict(int))
    # [pair][host slug] -> target ids the host's own rows assert (ids owned by the OTHER side)
    pair_targets: dict = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(set))
    )
    dangling: list = field(default_factory=list)
    xrow_total: int = 0

    @property
    def slugs(self):
        return sorted(self.docs)


def resolve_corpus(raw: str | None) -> pathlib.Path:
    """--root relative to the cwd, else relative to the repo root, else fail loudly."""
    if raw is None:
        return DEFAULT_CORPUS
    candidates = [pathlib.Path(raw), REPO / raw]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    tried = " | ".join(str(c) for c in candidates)
    raise CorpusUnreadable(f"--root is not a directory. Tried: {tried}")


def load(p):
    lines = p.read_text(encoding="utf-8").splitlines()
    sections, _ = vfm.parse_sections(lines)
    return lines, {s.name: s for s in sections}


def rows(lines, by, title):
    sec = by.get(title)
    return vfm.row_dicts(vfm.first_table(lines, sec)) if sec else []


def build_corpus(root: pathlib.Path | str | None = None, echo: bool = False) -> Corpus:
    """Classify and parse every `*.md` under `root` into a Corpus.

    Raises CorpusUnreadable for a MALFORMED flow map (a `## Scenarios` section that yields no
    parseable ids, or a flow map with no `## Symbol index`), for a scenario-prefix collision, and
    for a population with fewer than two flow maps -- all cases where a printed count would be
    computed over a silently shrunken population. A document with no `## Scenarios` section at all
    is EXCLUDED rather than malformed (v3 note 2) and is named in `corpus.excluded`.
    """
    root = root if isinstance(root, pathlib.Path) else resolve_corpus(root)
    corpus = Corpus(root=root)
    candidates = sorted(root.glob("*.md"))
    if echo:
        print("=" * 74)
        print(f"CORPUS  {root}")
        print(f"  .md files found: {len(candidates)}")

    malformed = []  # (name, reason) -- a flow map that will not parse: instrument failure
    for p in candidates:
        lines, by = load(p)
        if "Scenarios" not in by:
            corpus.excluded.append(
                (p.name, "no '## Scenarios' section -- not a flow map (index/README)")
            )
            continue
        verdict = {}
        local = []
        for _r, d in rows(lines, by, "Scenarios"):
            sid = (d.get("#") or "").strip()
            if vfm.SCENARIO_ID_RE.match(sid):
                local.append(sid)
                verdict[sid] = (d.get("verdict") or "").strip()
        if not local:
            malformed.append(
                (p.name, "'## Scenarios' present but zero rows match SCENARIO_ID_RE")
            )
            continue
        if "Symbol index" not in by:
            malformed.append(
                (
                    p.name,
                    "flow map with no '## Symbol index' section -- cannot share symbols",
                )
            )
            continue
        sym2scen = {}
        for _r, d in rows(lines, by, "Symbol index"):
            s = vfm.normalize_symbol((d.get("symbol") or "").strip())
            if s:
                sym2scen[s] = vfm.parse_scenario_ids(d.get("scenarios") or "")
        corpus.docs[p.name] = {
            "prefix": local[0].split("-")[0],
            "verdict": verdict,
            "sym2scen": sym2scen,
            "xrows": rows(lines, by, "Cross-flow scenarios"),
        }

    if echo:
        print(f"  flow maps in population: {len(corpus.docs)}  {corpus.slugs}")
        if corpus.excluded:
            print(
                f"  EXCLUDED, not a flow map ({len(corpus.excluded)}) -- named so the skip is auditable:"
            )
            for name, why in corpus.excluded:
                print(f"     {name:28s} {why}")
    if malformed:
        detail = "; ".join(f"{name}: {why}" for name, why in malformed)
        raise CorpusUnreadable(
            f"MALFORMED flow maps ({len(malformed)}) -- CORPUS UNREADABLE. Refusing to print a "
            f"count over a silently shrunken population. {detail}"
        )
    if len(corpus.docs) < 2:
        raise CorpusUnreadable(
            f"Fewer than two flow maps in {root}: no pair to sweep (found {len(corpus.docs)})."
        )

    pref2slug = {}
    for slug, d in sorted(corpus.docs.items()):
        other = pref2slug.get(d["prefix"])
        if other:
            raise CorpusUnreadable(
                f"PREFIX COLLISION: {d['prefix']} claimed by both {other} and {slug}"
            )
        pref2slug[d["prefix"]] = slug

    for slug, d in corpus.docs.items():
        for r, rd in d["xrows"]:
            corpus.xrow_total += 1
            tgt = (rd.get("scenario") or "").strip()
            tslug = pref2slug.get(tgt.split("-")[0])
            if not tslug:
                corpus.dangling.append(
                    (slug, r.line, tgt, (rd.get("owning flow") or "").strip())
                )
                continue
            k = frozenset((slug, tslug))
            corpus.pair_text[k] += (
                " " + (rd.get("this document's contribution") or "") + " " + tgt
            )
            corpus.pair_n[k] += 1
            corpus.pair_targets[k][slug].add(tgt)
    return corpus


def link_strength(corpus, sym, k):
    """None | 'row-level' | 'strong' (full dotted symbol in the cell) | 'weak' (bare suffix only).

    Row-level (RC1-01 2a): a cross-flow row hosted by one side of the pair, whose target id is
    one of `sym`'s OWN scenarios on the OTHER side (via sym2scen), links `sym` structurally --
    checked first because it is evidence independent of prose, so it can suppress a symbol no
    cell names by text. See the module docstring's v4 note 2 for a case where this is correct
    by the rule but not obviously correct by prose (attempt_recovery / SD-43).
    """
    a, b = tuple(k)
    ids_a = corpus.pair_targets.get(k, {}).get(a, set())
    ids_b = corpus.pair_targets.get(k, {}).get(b, set())
    if ids_a & corpus.docs[b]["sym2scen"].get(sym, set()) or ids_b & corpus.docs[a][
        "sym2scen"
    ].get(sym, set()):
        return "row-level"
    txt = corpus.pair_text.get(k, "")
    if sym in txt:
        return "strong"
    if sym.split(".")[-1] in txt:
        return "weak"
    return None


def residue(corpus, a, b):
    k = frozenset((a, b))
    shared = set(corpus.docs[a]["sym2scen"]) & set(corpus.docs[b]["sym2scen"])
    return (
        {s for s in shared if link_strength(corpus, s, k) is None},
        shared,
        corpus.pair_n.get(k, 0),
    )


def verdict_set(corpus, slug, sym):
    return {
        corpus.docs[slug]["verdict"].get(x, "")
        for x in corpus.docs[slug]["sym2scen"].get(sym, set())
    }


def verdict_disagreement(corpus, a, b, sym):
    """RC1-01 2b, narrowed from the ticket's literal 'FAIL...UNKNOWN or PASS' to FAIL-vs-
    UNKNOWN only: `sym2scen` unions EVERY scenario a symbol's path touches in one document,
    and most touch more than one, so a bare "PASS present somewhere in the side's set" fires
    on nearly every shared symbol in this corpus by coincidence, not disagreement -- all 9 of
    RC1-01's non-removed HIGH VALUE entries carry a stray PASS on at least one side (verified
    by enumeration), which would make this block fire on everything and silently broke the
    ticket's own named known-negative (`ResponseGateBehavior._reject`: the ticket claims
    barge-in.md is 'SE-11/SE-24 FAIL, FAIL' but SE-11's verdict is actually PASS -- so the
    literal predicate flags it as a disagreement, the opposite of 'must not appear'). UNKNOWN
    has no such problem: a document never asserts it incidentally, so its presence stays a
    real signal even at this coarser granularity. A side's own set may still be mixed (e.g.
    `add_record` on turn-lifecycle.md is {'FAIL', 'UNKNOWN', 'PASS'}) and the check still
    fires on FAIL/UNKNOWN presence, not exclusivity; both directions are checked.

    What this CANNOT see is `verdict_blind_spot` below -- FAIL against a PASS-only set. That is
    the larger slice of the rule and it has no instrument; see the docstring's header block.
    """
    va, vb = verdict_set(corpus, a, sym), verdict_set(corpus, b, sym)
    return ("FAIL" in va and "UNKNOWN" in vb) or ("FAIL" in vb and "UNKNOWN" in va)


def verdict_blind_spot(corpus, a, b, sym):
    """The complement `verdict_disagreement` deliberately does not report: FAIL on one side and a
    PASS-only set (no FAIL, no UNKNOWN) on the other.

    This is a straight contradiction under the template's verdict-agreement rule and the LARGER
    share of that rule's surface, but it is not flagged, because widening the predicate to the
    ticket's literal "FAIL ... UNKNOWN or PASS" fires on nearly every shared symbol and breaks the
    ticket's own named known-negative (see `verdict_disagreement`). It is measured and printed so
    that a zero from the disagreement block is never read as "no disagreements", and it is
    DISJOINT from that predicate by construction: a side with UNKNOWN is excluded here.
    """
    va, vb = verdict_set(corpus, a, sym), verdict_set(corpus, b, sym)
    fwd = "FAIL" in va and "PASS" in vb and not ({"FAIL", "UNKNOWN"} & vb)
    rev = "FAIL" in vb and "PASS" in va and not ({"FAIL", "UNKNOWN"} & va)
    return fwd or rev


# ---------------------------------------------------------------- PROBE
# Every probe runs against PROBE_CORPUS -- two fixture documents under
# scripts/fixtures/flow_map/seam_probe/ -- and NOT against the live corpus. v4 pinned each of
# these to a live symbol, which made the known-POSITIVE a pin on a live corpus DEFECT: fixing the
# corpus de-certified the detector (see the docstring's v5 note 1). The fixture pair carries the
# EXPECTED table and the two invariants an edit must preserve; read probe-seam-a.md before
# touching either document.
# The column-0 token every enumerated candidate line carries. Selecting on it is what lets a
# caller read the list without also matching the probe banner or the block prose above it,
# which name the same fixture symbols and would otherwise satisfy a naive grep.
RESIDUE_PREFIX = "RESIDUE  "
POS_SYM, POS_A, POS_B = (
    "ProbeAbsentSeam.sweep_only",
    "probe-seam-a.md",
    "probe-seam-b.md",
)
NEG_SYM, NEG_A, NEG_B = (
    "ProbeNamedInProse.cell_names_me",
    "probe-seam-a.md",
    "probe-seam-b.md",
)
RL_SYM, RL_A, RL_B = (
    "ProbeRowLevelOnly.target_id_links_me",
    "probe-seam-a.md",
    "probe-seam-b.md",
)
VD_SYM, VD_A, VD_B = (
    "ProbeVerdictSplit.fail_here_unknown_there",
    "probe-seam-a.md",
    "probe-seam-b.md",
)
VD_NEG_SYM, VD_NEG_A, VD_NEG_B = (
    "ProbeVerdictAgree.fail_here_pass_there",
    "probe-seam-a.md",
    "probe-seam-b.md",
)


def residue_lines(corpus: Corpus) -> list[str]:
    """Every absent-seam candidate as one RESIDUE-prefixed line, newest caller first.

    Extracted from `sweep` so the PROBE can certify what is RENDERED, not only what
    `residue()` computes. The five original probes assert on the set; a defect in the
    rendering -- an empty loop, a wrong column, a pair filter that drops the candidate --
    would print a short clean list and leave every one of them saying CERTIFIED. The
    prefix sits at column 0 so a caller can select these lines without also matching the
    probe banner or the block's own prose, both of which name the same fixture symbols.
    """
    docs = corpus.docs
    slugs = corpus.slugs
    pairs = []
    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            a, b = slugs[i], slugs[j]
            r, _sh, _n = residue(corpus, a, b)
            if r:
                pairs.append((a, b, r))
    out: list[str] = []
    for a, b, r in sorted(pairs, key=lambda x: (-len(x[2]), x[0], x[1])):
        for sym in sorted(r):
            va = sorted(verdict_set(corpus, a, sym))
            vb = sorted(verdict_set(corpus, b, sym))
            both = (set(va) & {"FAIL", "UNKNOWN"}) and (set(vb) & {"FAIL", "UNKNOWN"})
            out.append(
                f"RESIDUE  {a}  {b}  {sym}" + ("  <- HIGH VALUE" if both else "")
            )
            out.append(f"         {a:26s} {sorted(docs[a]['sym2scen'][sym])} {va}")
            out.append(f"         {b:26s} {sorted(docs[b]['sym2scen'][sym])} {vb}")
    return out


def run_probes(echo: bool = True) -> bool:
    """Certify the detector against the fixture corpus. False = do not read any count."""
    if echo:
        print("\n" + "=" * 74)
        print("PROBE (a zero from an unprobed detector is UNREAD, not clean)")
        print(f"  fixture corpus: {PROBE_CORPUS}")
    try:
        fx = build_corpus(PROBE_CORPUS, echo=False)
    except CorpusUnreadable as exc:
        if echo:
            print(f"  PROBE INCONCLUSIVE -- the fixture corpus does not load: {exc}")
            print(
                "  A probe that cannot run is not a probe that passed. Counts below are unread."
            )
        return False

    fixture_docs = (
        POS_A,
        POS_B,
        NEG_A,
        NEG_B,
        RL_A,
        RL_B,
        VD_A,
        VD_B,
        VD_NEG_A,
        VD_NEG_B,
    )
    missing = [n for n in fixture_docs if n not in fx.docs]
    if missing:
        if echo:
            print(
                f"  PROBE INCONCLUSIVE -- fixture documents absent: {sorted(set(missing))}"
            )
            print(
                "  A probe that cannot run is not a probe that passed. Counts below are unread."
            )
        return False

    res_p, sh_p, _ = residue(fx, POS_A, POS_B)
    res_n, sh_n, _ = residue(fx, NEG_A, NEG_B)
    p_ok = POS_SYM in res_p
    n_ok = NEG_SYM in sh_n and NEG_SYM not in res_n

    res_rl, sh_rl, _ = residue(fx, RL_A, RL_B)
    rl_kind = link_strength(fx, RL_SYM, frozenset((RL_A, RL_B)))
    rl_ok = RL_SYM in sh_rl and RL_SYM not in res_rl and rl_kind == "row-level"

    vd_pos = verdict_disagreement(fx, VD_A, VD_B, VD_SYM)
    vd_neg = verdict_disagreement(fx, VD_NEG_A, VD_NEG_B, VD_NEG_SYM)
    bs_pos = verdict_blind_spot(fx, VD_NEG_A, VD_NEG_B, VD_NEG_SYM)
    vd_pos_ok, vd_neg_ok, bs_ok = vd_pos is True, vd_neg is False, bs_pos is True

    # RENDERING probe (v6): the five above certify the SET; these two certify the LIST the
    # --list-residue flag actually prints. Positive: the absent-seam symbol must be NAMED on
    # a RESIDUE line. Negative: the prose-linked symbol must NOT be, which is the half that
    # catches a renderer that dumps every shared symbol rather than the residue.
    rendered = [ln for ln in residue_lines(fx) if ln.startswith(RESIDUE_PREFIX)]
    render_pos_ok = any(POS_SYM in ln for ln in rendered)
    render_neg_ok = not any(NEG_SYM in ln for ln in rendered)

    if echo:
        neg_kind = link_strength(fx, NEG_SYM, frozenset((NEG_A, NEG_B)))
        print(f"  known-POSITIVE {POS_SYM}")
        print(
            f"     in both symbol indexes: {POS_SYM in sh_p}   flagged as absent seam: {p_ok}   -> {'PASS' if p_ok else 'FAIL (detector blind)'}"
        )
        print(
            f"  known-NEGATIVE {NEG_SYM}  (named in full inside a {NEG_B} contribution cell)"
        )
        print(
            f"     in both symbol indexes: {NEG_SYM in sh_n}   NOT flagged: {NEG_SYM not in res_n}   link kind: {neg_kind}  -> {'PASS' if n_ok else 'FAIL (over-matching)'}"
        )
        print(
            f"  known-POSITIVE (row-level) {RL_SYM}  (only link is a target id, not prose)"
        )
        print(
            f"     in both symbol indexes: {RL_SYM in sh_rl}   link kind: {rl_kind}   -> {'PASS' if rl_ok else 'FAIL (row-level rule blind)'}"
        )
        print(
            f"  known-POSITIVE (verdict disagreement) {VD_SYM}  ({VD_A} {sorted(verdict_set(fx, VD_A, VD_SYM))} vs {VD_B} {sorted(verdict_set(fx, VD_B, VD_SYM))})"
        )
        print(
            f"     flagged as disagreement: {vd_pos}   -> {'PASS' if vd_pos_ok else 'FAIL (verdict-disagreement rule blind)'}"
        )
        print(
            f"  known-NEGATIVE (verdict disagreement) {VD_NEG_SYM}  ({VD_NEG_A} {sorted(verdict_set(fx, VD_NEG_A, VD_NEG_SYM))} vs {VD_NEG_B} {sorted(verdict_set(fx, VD_NEG_B, VD_NEG_SYM))}, no UNKNOWN on either side)"
        )
        print(
            f"     NOT flagged: {not vd_neg}   -> {'PASS' if vd_neg_ok else 'FAIL (over-matching, a stray PASS treated as disagreement)'}"
        )
        print(
            f"  known-POSITIVE (blind spot) {VD_NEG_SYM}  -- the SAME pair the predicate above must ignore"
        )
        print(
            f"     counted as FAIL-vs-PASS-only: {bs_pos}   -> {'PASS' if bs_ok else 'FAIL (blind-spot measurement blind)'}"
        )
        print(f"  known-POSITIVE (rendering) {POS_SYM} must be NAMED by --list-residue")
        print(
            f"     RESIDUE lines rendered: {len(rendered)}   names it: {render_pos_ok}   -> {'PASS' if render_pos_ok else 'FAIL (enumeration blind)'}"
        )
        print(
            f"  known-NEGATIVE (rendering) {NEG_SYM} must NOT be named by --list-residue"
        )
        print(
            f"     absent from the rendered list: {render_neg_ok}   -> {'PASS' if render_neg_ok else 'FAIL (enumeration over-matching)'}"
        )

    ok = (
        p_ok
        and n_ok
        and rl_ok
        and vd_pos_ok
        and vd_neg_ok
        and bs_ok
        and render_pos_ok
        and render_neg_ok
    )
    if echo:
        if ok:
            print(
                "  DETECTOR CERTIFIED on every probe (5 known positives, 3 known negatives), against"
            )
            print(
                "  fixtures -- so fixing the live corpus can no longer de-certify this instrument."
            )
        else:
            print("  DETECTOR NOT CERTIFIED -- counts below are unread.")
    return ok


# ---------------------------------------------------------------- SWEEP
def sweep(corpus: Corpus, *, list_residue: bool = False) -> None:
    slugs = corpus.slugs
    docs = corpus.docs
    print("\n" + "=" * 74)
    print("SWEEP RESULT")
    tot_shared = tot_res = 0
    per_pair = []
    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            a, b = slugs[i], slugs[j]
            r, sh, n = residue(corpus, a, b)
            tot_shared += len(sh)
            tot_res += len(r)
            per_pair.append((a, b, n, len(sh), r))
    print(f"  flow maps swept                                 : {len(slugs)}")
    print(f"  document pairs                                  : {len(per_pair)}")
    print(f"  cross-flow rows read                            : {corpus.xrow_total}")
    print(f"  shared symbols across all pairs                 : {tot_shared}")
    print(
        f"  shared symbols with NO linking cross-flow row   : {tot_res}   <- ABSENT SEAM CANDIDATES"
    )
    print(
        f"  pairs carrying at least one                     : {sum(1 for x in per_pair if x[4])} of {len(per_pair)}"
    )

    print(
        "\n  -- FINDING: dangling cross-flow rows (target scenario exists in no flow map)"
    )
    print(f"     count: {len(corpus.dangling)}")
    for slug, line, tgt, owner in corpus.dangling:
        print(f"     {slug}:{line}  scenario={tgt!r}  owning flow={owner!r}")

    weak = []
    for a, b, _n, _nsh, _r in per_pair:
        k = frozenset((a, b))
        for s in sorted(set(docs[a]["sym2scen"]) & set(docs[b]["sym2scen"])):
            if link_strength(corpus, s, k) == "weak":
                weak.append((a, b, s))
    print(
        "\n  -- SENSITIVITY: links resting only on a bare method-name match, not the full symbol"
    )
    print(
        f"     count: {len(weak)}  (each is a POSSIBLE false suppression -- an absent seam hidden by prose)"
    )
    print(
        f"     upper bound on absent seams if every weak link is spurious: {tot_res + len(weak)}"
    )
    for a, b, s in weak:
        print(f"     {a:26s} {b:26s} {s}")

    link_audit = []
    for a, b, _n, _nsh, _r in per_pair:
        k = frozenset((a, b))
        for s in sorted(set(docs[a]["sym2scen"]) & set(docs[b]["sym2scen"])):
            kind = link_strength(corpus, s, k)
            if kind is not None:
                link_audit.append((a, b, s, kind))
    print(
        "\n  -- LINK AUDIT: every shared, non-residue symbol with the kind that suppressed it"
    )
    print(
        f"     count: {len(link_audit)}  (row-level is structural -- a shared target id, not prose; audit before trusting a suppression)"
    )
    for a, b, s, kind in link_audit:
        print(f"     {a:26s} {b:26s} {s:55s} {kind}")

    print("\n  -- HIGH VALUE: residue symbols carrying FAIL/UNKNOWN on BOTH sides")
    hi = []
    for a, b, _n, _nsh, r in per_pair:
        for s in sorted(r):
            va = {docs[a]["verdict"].get(x, "") for x in docs[a]["sym2scen"][s]}
            vb = {docs[b]["verdict"].get(x, "") for x in docs[b]["sym2scen"][s]}
            bad_a = va & {"FAIL", "UNKNOWN"}
            bad_b = vb & {"FAIL", "UNKNOWN"}
            if bad_a and bad_b:
                hi.append(
                    (
                        a,
                        b,
                        s,
                        sorted(docs[a]["sym2scen"][s]),
                        sorted(docs[b]["sym2scen"][s]),
                        bad_a,
                        bad_b,
                    )
                )
    print(f"     count: {len(hi)}")
    for a, b, s, sa, sb, va, vb in hi:
        print(f"     {s}")
        print(f"        {a:26s} {sa} {sorted(va)}")
        print(f"        {b:26s} {sb} {sorted(vb)}")

    print("\n  -- VERDICT DISAGREEMENT: one mechanism, two verdicts")
    print(
        "     predicate: FAIL in one side's verdict SET and UNKNOWN in the other side's, symmetric,"
    )
    print(
        "     evaluated per shared symbol regardless of link status; a side's own set may itself"
    )
    print(
        "     be mixed (e.g. {'FAIL', 'UNKNOWN', 'PASS'}) and still trigger on FAIL/UNKNOWN presence."
    )
    print(
        "     A bare PASS is deliberately NOT a trigger (module docstring v4 note 3: it is noise at"
    )
    print(
        "     this granularity, not disagreement, and the ticket's own named negative had a stray"
    )
    print("     PASS its data claim missed)")
    disagreements = []
    for a, b, _n, _nsh, _r in per_pair:
        for s in sorted(set(docs[a]["sym2scen"]) & set(docs[b]["sym2scen"])):
            if verdict_disagreement(corpus, a, b, s):
                disagreements.append(
                    (
                        a,
                        b,
                        s,
                        sorted(docs[a]["sym2scen"][s]),
                        sorted(verdict_set(corpus, a, s)),
                        sorted(docs[b]["sym2scen"][s]),
                        sorted(verdict_set(corpus, b, s)),
                    )
                )
    print(f"     count: {len(disagreements)}")
    for a, b, s, sa, va, sb, vb in disagreements:
        print(f"     {s}")
        print(f"        {a:26s} {sa} {va}")
        print(f"        {b:26s} {sb} {vb}")

    blind = []
    for a, b, _n, _nsh, _r in per_pair:
        for s in sorted(set(docs[a]["sym2scen"]) & set(docs[b]["sym2scen"])):
            if verdict_blind_spot(corpus, a, b, s):
                blind.append(
                    (
                        a,
                        b,
                        s,
                        sorted(verdict_set(corpus, a, s)),
                        sorted(verdict_set(corpus, b, s)),
                    )
                )
    print(
        "\n  -- VERDICT AGREEMENT: RULE SURFACE (what the block above does NOT report)"
    )
    print(
        "     The rule is 'their verdicts must agree, or one artifact says which document owns the"
    )
    print(
        "     verdict' (template, Cross-document verdict agreement). This detector reports one slice."
    )
    print(
        f"     reported above, FAIL vs UNKNOWN                 : {len(disagreements)}"
    )
    print(
        f"     NOT reported, FAIL vs a PASS-only set          : {len(blind)}   <- straight contradiction, NO INSTRUMENT"
    )
    print(
        f"     rule-relevant candidates on shared symbols     : {len(disagreements) + len(blind)}"
    )
    print(
        "     A zero above means 'no FAIL-vs-UNKNOWN pair on a shared symbol', never 'no"
    )
    print(
        "     disagreements'. This slice is a READING obligation; widening the predicate to cover"
    )
    print(
        "     it breaks the ticket's own known-negative (see verdict_disagreement's docstring)."
    )
    print(
        "     Also invisible to both counts: one mechanism mapped under two different symbols."
    )
    for a, b, s, va, vb in blind:
        print(f"     {a:26s} {b:26s} {s:55s} {va} vs {vb}")

    print("\n  -- per-pair residue counts")
    for a, b, n, nsh, r in sorted(per_pair, key=lambda x: -len(x[4])):
        print(f"     {a:26s} {b:26s} rows={n:2d} shared={nsh:3d} absent={len(r):3d}")

    if not list_residue:
        (
            print(
                "\n  -- RESIDUE ENUMERATED: not requested. Re-run with --list-residue to NAME"
            ),
        )
        (
            print(
                f"     the {tot_res} absent-seam candidates counted above. Until then this report"
            ),
        )
        (
            print(
                "     gives a count for every pair and names only the HIGH VALUE and weak-link"
            ),
        )
        (
            print(
                "     subsets -- so a triage worked from it alone is complete for those and"
            ),
        )
        (
            print(
                "     SILENT for the remainder, which reads identically to having none."
            ),
        )
        return

    # Every residue symbol BY NAME. The count above is a number; a triage needs the list,
    # and a candidate nobody can name is a candidate nobody works. Session B3-A1 hit exactly
    # that: it wrote a set-difference reimplementation to recover the 20 names this report
    # only counted, the reimplementation FAILED its own certification (it reproduced the
    # per-pair counts for 3 of 9 pairs and totalled 20 against 22), and it correctly quoted
    # nothing from it. The names have to come from the instrument that computed them.
    # Lines carry the prefix RESIDUE at column 0 so a caller can select them without also
    # matching the probe banner or this prose, both of which name the same fixture symbols.
    print(
        "\n  -- RESIDUE ENUMERATED: every absent-seam candidate by name (--list-residue)"
    )
    print(
        "     The same set the count above reports: shared symbols with NO linking cross-flow"
    )
    print(
        "     row, in either direction. Each is a candidate needing a `Residue verdict:` marker"
    )
    print(
        "     in the register of the document owning the FAIL. Leaving one out of a triage is a"
    )
    print("     claim like any other -- flow-mapping rule 5.")
    print(
        f"     count: {tot_res}   (pairs carrying at least one: "
        f"{sum(1 for x in per_pair if x[4])} of {len(per_pair)})"
    )
    for line in residue_lines(corpus):
        print(line)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=None,
        help="directory holding the flow-map documents (default: <repo>/docs/flows)",
    )
    parser.add_argument(
        "--list-residue",
        action="store_true",
        help=(
            "NAME every absent-seam candidate instead of only counting it. Emits one "
            "RESIDUE-prefixed line per candidate with both sides' scenario ids and verdict "
            "sets, so a residue triage can be worked and audited rather than estimated."
        ),
    )
    parser.add_argument("--project-root", type=pathlib.Path, default=REPO)
    args = parser.parse_args(argv)
    configure(args.project_root)
    if not REPO.is_dir():
        parser.error(f"project root not found: {REPO}")

    if not run_probes(echo=True):
        return 2
    try:
        corpus = build_corpus(resolve_corpus(args.root), echo=True)
    except CorpusUnreadable as exc:
        print(f"\n{exc}")
        return 3
    sweep(corpus, list_residue=args.list_residue)
    return 0


if __name__ == "__main__":
    sys.exit(main())
