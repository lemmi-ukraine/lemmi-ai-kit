"""Emit or certify derived flow-document columns without writing project files.

Scenario membership and coverage are derived; invariant associations and read status
remain authored. A narrowed call-graph scenario set is a legal subset.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

REPO_ROOT = Path.cwd().resolve()
VALIDATOR_PATH = Path(__file__).with_name("validate_flow_map.py")
DEFAULT_CODE_ROOT = REPO_ROOT

EXIT_OK = 0
EXIT_DIFFERING = 1
EXIT_REFUSED = 2
EXIT_UNPARSEABLE = 3

OWNED_TABLE_SECTIONS = (
    "Symbol index",
    "Call graph",
    "Coverage",
    "Runtime applicability",
)


class SectionName(StrEnum):
    SYMBOL_INDEX = "symbol-index"
    CALL_GRAPH = "call-graph"
    COVERAGE = "coverage"
    RUNTIME = "runtime"
    VERDICT_DISTRIBUTION = "verdict-distribution"
    ALL = "all"


EMIT_ORDER = (
    SectionName.SYMBOL_INDEX,
    SectionName.CALL_GRAPH,
    SectionName.COVERAGE,
    SectionName.RUNTIME,
    SectionName.VERDICT_DISTRIBUTION,
)


def load_validator() -> ModuleType:
    """sys.modules registration is load-bearing: without it @dataclass raises
    `AttributeError: 'NoneType' object has no attribute '__dict__'` (spec SS8)."""
    if not VALIDATOR_PATH.is_file():
        print(
            f"generate_flow_projections: validator not found: {VALIDATOR_PATH}",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_UNPARSEABLE)
    spec = importlib.util.spec_from_file_location("vfm", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        print(
            f"generate_flow_projections: cannot load validator spec: {VALIDATOR_PATH}",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_UNPARSEABLE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["vfm"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # P0-T3's write set; a mid-edit break is theirs to know, not ours to patch
        print(
            f"generate_flow_projections: validator import failed ({VALIDATOR_PATH}): {exc!r}",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_UNPARSEABLE) from exc
    module.configure(REPO_ROOT, DEFAULT_CODE_ROOT)
    return module


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------


@dataclass
class ScenarioRow:
    sid: str
    path: set[str]
    verdict: str
    evidence: str


@dataclass
class FlowDocument:
    path: Path
    lines: list[str]
    tables: dict[str, Any]  # section name -> vfm.MarkdownTable | None
    scenarios: dict[str, ScenarioRow]
    all_ids: set[str]


def parse_document(vfm: ModuleType, doc_path: Path) -> FlowDocument:
    if not doc_path.is_file():
        print(
            f"generate_flow_projections: document not found: {doc_path}",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_UNPARSEABLE)
    text = doc_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    _sections, by_name = vfm.parse_sections(lines)

    required = ("Scenarios", *OWNED_TABLE_SECTIONS)
    missing = [name for name in required if name not in by_name]
    if missing:
        print(
            f"generate_flow_projections: {doc_path}: missing required section(s): {', '.join(missing)}",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_UNPARSEABLE)

    tables: dict[str, Any] = {}
    for name in required:
        table = vfm.first_table(lines, by_name[name][0])
        if table is None:
            print(
                f"generate_flow_projections: {doc_path}: section '## {name}' has no table",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_UNPARSEABLE)
        expected = set(vfm.TABLE_HEADERS.get(name, ()))
        if expected and (
            set(table.headers) != expected or len(table.headers) != len(expected)
        ):
            # Mirrors the validator's own header check (validate_flow_map.py ~L662) so a
            # malformed table fails here with a named section, never as an uncaught
            # ValueError out of column_index() further down.
            print(
                f"generate_flow_projections: {doc_path}: section '## {name}' headers must be "
                f"exactly: {' | '.join(vfm.TABLE_HEADERS[name])} (found: {' | '.join(table.headers)})",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_UNPARSEABLE)
        tables[name] = table

    scenarios: dict[str, ScenarioRow] = {}
    for _row, values in vfm.row_dicts(tables["Scenarios"]):
        sid = vfm.normalize_symbol(values.get("#", ""))
        if not vfm.SCENARIO_ID_RE.fullmatch(sid) or sid in scenarios:
            continue
        path = set(vfm.parse_path_symbols(values.get("path", "")))
        verdict = vfm.normalize_symbol(values.get("verdict", "")).upper()
        evidence = vfm.normalize_symbol(values.get("evidence", ""))
        scenarios[sid] = ScenarioRow(
            sid=sid, path=path, verdict=verdict, evidence=evidence
        )

    return FlowDocument(
        path=doc_path,
        lines=lines,
        tables=tables,
        scenarios=scenarios,
        all_ids=set(scenarios),
    )


# ---------------------------------------------------------------------------
# Rendering helpers -- shared by --certify (compare) and emit (print)
# ---------------------------------------------------------------------------


def format_scenario_ids(ids: set[str]) -> str:
    """Scenario-id-list cells (P1, P3, P4): bare, comma-space, ascending;
    empty is `_none_` (measured: Symbol index `scenarios` and Coverage
    `scenarios` both use `_none_` for an empty cell -- confirmed by grepping
    the corpus, not assumed from the `called by` convention below)."""
    return ", ".join(sorted(ids)) if ids else "_none_"


def format_symbol_list(symbols: set[str]) -> str:
    """Symbol-list cells (P2 `called by`): backticked, comma-space, ascending;
    empty is U+2014 em dash (measured, SS2/SS7: 6 cells, all `—`)."""
    return ", ".join(f"`{s}`" for s in sorted(symbols)) if symbols else "—"


def render_row(cells: tuple[str, ...]) -> str:
    return "| " + " | ".join(cells) + " |"


def column_index(table: Any, name: str) -> int:
    """Column position is NOT assumed: TABLE_HEADERS is checked as a SET by the
    validator (validate_flow_map.py ~L662), and the schema's own conformant
    fixture (scripts/fixtures/flow_map/conformant.md) deliberately reorders the
    Symbol index columns as "a control for header-aware parsing". Any generator
    that hardcodes a positional index would silently write into the wrong cell
    against such a document."""
    return table.headers.index(name)


@dataclass
class CellDerivation:
    """One derived cell in one row: which column index, the declared set (as
    already parsed), the computed set, and how to render a replacement."""

    column: int
    declared: set[str]
    computed: set[str]
    render: Any  # Callable[[set[str]], str]

    @property
    def matches(self) -> bool:
        return self.declared == self.computed


def apply_derivations(
    raw_cells: tuple[str, ...], derivations: list[CellDerivation]
) -> tuple[str, ...]:
    """D-3's general form: a cell whose computed SET matches the declared SET
    is left byte-for-byte untouched (preserves authored order/format, e.g.
    barge-in.md's 4 causal-order `called by` cells); only a genuine set
    mismatch is replaced with the canonical rendering."""
    cells = list(raw_cells)
    for d in derivations:
        if not d.matches:
            cells[d.column] = d.render(d.computed)
    return tuple(cells)


# ---------------------------------------------------------------------------
# P1 / P2 -- Symbol index
# ---------------------------------------------------------------------------


def compute_scenarios_for_symbol(
    vfm: ModuleType, symbol: str, doc: FlowDocument
) -> set[str]:
    return {
        sid
        for sid, scenario in doc.scenarios.items()
        if any(vfm.symbol_related(symbol, t) for t in scenario.path)
    }


def compute_incoming(
    vfm: ModuleType, call_rows: list[tuple[Any, dict[str, str]]]
) -> dict[str, set[str]]:
    """Unconditional on every declared call-graph edge, matching the
    validator's own `expected_callers` computation (validate_flow_map.py
    ~L1160/L1243) -- NOT filtered by whether that edge's own `scenarios` cell
    is populated. Matching this exactly is what makes P2 agree with the gate
    by construction (rule 2)."""
    incoming: dict[str, set[str]] = {}
    for _row, values in call_rows:
        caller = vfm.normalize_symbol(values.get("caller", ""))
        callee = vfm.normalize_symbol(values.get("callee", ""))
        incoming.setdefault(callee, set()).add(caller)
    return incoming


def compute_called_by(
    vfm: ModuleType, symbol: str, incoming: dict[str, set[str]]
) -> set[str]:
    return {
        caller
        for callee, callers in incoming.items()
        if vfm.symbol_related(symbol, callee)
        for caller in callers
    }


@dataclass
class SectionReport:
    name: str
    rows: int = 0
    differing: int = 0
    notes: list[str] = field(default_factory=list)


def process_symbol_index(
    vfm: ModuleType, doc: FlowDocument, incoming: dict[str, set[str]]
) -> tuple[SectionReport, list[tuple[Any, tuple[str, ...]]]]:
    table = doc.tables["Symbol index"]
    report = SectionReport(name="Symbol index")
    rendered: list[tuple[Any, tuple[str, ...]]] = []
    for row, values in vfm.row_dicts(table):
        report.rows += 1
        symbol = vfm.normalize_symbol(values.get("symbol", ""))
        declared_scen = vfm.parse_scenario_ids(values.get("scenarios", ""))
        declared_callers = set(vfm.parse_symbol_list(values.get("called by", "")))
        computed_scen = compute_scenarios_for_symbol(vfm, symbol, doc)
        computed_callers = compute_called_by(vfm, symbol, incoming)

        derivations = [
            CellDerivation(
                column_index(table, "scenarios"),
                declared_scen,
                computed_scen,
                format_scenario_ids,
            ),
            CellDerivation(
                column_index(table, "called by"),
                declared_callers,
                computed_callers,
                format_symbol_list,
            ),
        ]
        new_cells = apply_derivations(row.cells, derivations)
        new_line = render_row(new_cells)
        if new_line != doc.lines[row.line - 1]:
            report.differing += 1
        rendered.append((row, new_cells))
    return report, rendered


# ---------------------------------------------------------------------------
# V1 -- Call graph `scenarios` (verify only, D-1)
# ---------------------------------------------------------------------------


def compute_edge_closure(
    vfm: ModuleType, caller: str, callee: str, doc: FlowDocument
) -> set[str]:
    external = bool(vfm.EXTERNAL_RE.fullmatch(caller))
    return {
        sid
        for sid, scenario in doc.scenarios.items()
        if any(vfm.symbol_related(callee, t) for t in scenario.path)
        and (external or any(vfm.symbol_related(caller, t) for t in scenario.path))
    }


def process_call_graph(
    vfm: ModuleType, doc: FlowDocument
) -> tuple[SectionReport, list[tuple[Any, tuple[str, ...]]]]:
    table = doc.tables["Call graph"]
    report = SectionReport(name="Call graph (V1 verify-only)")
    call_rows = vfm.row_dicts(table)
    for row, values in call_rows:
        report.rows += 1
        caller = vfm.normalize_symbol(values.get("caller", ""))
        callee = vfm.normalize_symbol(values.get("callee", ""))
        declared = vfm.parse_scenario_ids(values.get("scenarios", ""))
        closure = compute_edge_closure(vfm, caller, callee, doc)
        if declared == closure:
            continue
        if declared <= closure:
            report.notes.append(
                f"line {row.line}: `{caller}` -> `{callee}` declares "
                f"{format_scenario_ids(declared)}, closure is {format_scenario_ids(closure)} "
                "(authored narrowing, not a diff -- D-1)"
            )
        else:
            report.differing += 1
            report.notes.append(
                f"line {row.line}: `{caller}` -> `{callee}` declares an id outside the "
                f"closure: {format_scenario_ids(declared - closure)} not in {format_scenario_ids(closure)} "
                "(this is a genuine defect; the generator never rewrites call-graph scenarios -- D-1)"
            )
    # call-graph cells are NEVER rewritten (D-1); rendered rows are always the source rows.
    rendered = [(row, row.cells) for row, _values in call_rows]
    return report, rendered


# ---------------------------------------------------------------------------
# P3 -- Coverage (5-source union) and the SS6 refusal
# ---------------------------------------------------------------------------


@dataclass
class Citation:
    refs: set[str]
    provenance: list[str]


def compute_coverage_citations(
    vfm: ModuleType, doc: FlowDocument, incoming: dict[str, set[str]], code: Any
) -> dict[str, Citation]:
    """P3 = index-file use UNION call-graph site UNION scenario evidence UNION
    runtime evidence UNION diagram legend (spec SS4). All five sources read
    AUTHORED cells only -- never a recomputed/derived value from another
    projection (e.g. call-graph's contribution uses the row's own declared
    `scenarios` cell, not the V1 closure -- matching validate_flow_map.py's
    own `call_file_scenarios` computation exactly, since V1 is verify-only
    and the declared cell IS the source of truth here)."""
    citations: dict[str, Citation] = {}

    def cite(file_name: str, refs: set[str], source: str) -> None:
        if not file_name or not refs:
            return
        entry = citations.setdefault(file_name, Citation(refs=set(), provenance=[]))
        entry.refs.update(refs)
        entry.provenance.append(source)

    # 1. Symbol index: declared file cell (authored) x computed scenarios-for-symbol.
    #    Skip a row whose declared file disagrees with CodeIndex's own resolution --
    #    this mirrors validate_flow_map.py's `index_file_by_symbol` guard exactly
    #    (its `elif code.resolves(symbol) and file_name not in code.files_for(symbol)`
    #    branch excludes such a row too), so citation and gate agree by construction
    #    even in this corner, not only in the common case.
    for _row, values in vfm.row_dicts(doc.tables["Symbol index"]):
        symbol = vfm.normalize_symbol(values.get("symbol", ""))
        file_name = vfm.normalize_repo_path(values.get("file", ""))
        if file_name is None:
            continue
        if code.resolves(symbol) and file_name not in code.files_for(symbol):
            continue
        refs = compute_scenarios_for_symbol(vfm, symbol, doc)
        cite(file_name, refs, f"symbol index: {symbol}")

    # 2. Call graph: declared site (authored) x declared scenarios cell (authored,
    #    never the V1 closure -- D-1 keeps that cell unrewritten).
    for _row, values in vfm.row_dicts(doc.tables["Call graph"]):
        site = vfm.normalize_repo_path(values.get("site", ""))
        if site is None:
            continue
        refs = vfm.parse_scenario_ids(values.get("scenarios", ""))
        if refs:
            cite(site, refs, f"call site: {', '.join(sorted(refs))}")

    # 3. Scenario evidence: file refs embedded in each scenario's own evidence prose.
    for sid, scenario in doc.scenarios.items():
        for file_name in vfm.extract_file_refs(scenario.evidence):
            cite(file_name, {sid}, f"evidence: {sid}")

    # 4. Runtime evidence: file refs in each profile's evidence prose, citing every
    #    scenario -- reachable UNION unreachable is always all_ids by construction
    #    (unreachable is DEFINED as the complement), and the UNKNOWN case also
    #    resolves to all_ids, so this is unconditionally all_ids.
    for _row, values in vfm.row_dicts(doc.tables["Runtime applicability"]):
        evidence = vfm.normalize_symbol(values.get("evidence", ""))
        profile = vfm.normalize_symbol(values.get("profile", ""))
        for file_name in vfm.extract_file_refs(evidence):
            cite(file_name, set(doc.all_ids), f"runtime: {profile}")

    # 5. Diagram legend: an input SOURCE for coverage only (spec SS4's formal P3
    #    definition names it explicitly) -- never emitted, verified, or owned as
    #    a section in its own right (SS13.5 non-goal). `_none_` Diagrams sections
    #    contribute nothing.
    for file_name, refs, sym in _legend_citations(vfm, doc):
        cite(file_name, refs, f"legend: {sym}")

    return citations


def _legend_citations(
    vfm: ModuleType, doc: FlowDocument
) -> list[tuple[str, set[str], str]]:
    _sections, by_name = vfm.parse_sections(doc.lines)
    diagrams = by_name.get("Diagrams")
    if not diagrams:
        return []
    section = diagrams[0]
    if vfm.section_is_none(doc.lines, section):
        return []
    out: list[tuple[str, set[str], str]] = []
    for block in vfm.mermaid_blocks(doc.lines):
        if not (section.start <= block.start < section.end):
            continue
        heading = vfm.first_nonblank(doc.lines, block.end + 1, section.end)
        if heading is None or not doc.lines[heading].startswith("### Legend —"):
            continue
        table_start = vfm.first_nonblank(doc.lines, heading + 1, section.end)
        if table_start is None:
            continue
        legend_table = vfm.parse_table_at(doc.lines, table_start, section.end)
        if legend_table is None:
            continue
        for _row, values in vfm.row_dicts(legend_table):
            refs = vfm.parse_scenario_ids(values.get("scenarios", ""))
            file_name = vfm.normalize_repo_path(values.get("file", ""))
            if file_name is None or not refs:
                continue
            for symbol in vfm.parse_symbol_list(values.get("symbol", "")):
                if vfm.EXTERNAL_RE.fullmatch(symbol):
                    continue
                out.append((file_name, refs, symbol))
    return out


def check_coverage_refusal(
    vfm: ModuleType, doc: FlowDocument, citations: dict[str, Citation]
) -> list[str]:
    """SS6: refuse, per file, exhaustively (D-4) -- never infer a note."""
    declared_notes: dict[str, str] = {}
    for _row, values in vfm.row_dicts(doc.tables["Coverage"]):
        file_name = vfm.normalize_repo_path(values.get("file", ""))
        if file_name is not None:
            declared_notes[file_name] = values.get("coverage note", "")

    offenders: list[str] = []
    for file_name in sorted(citations):
        note = declared_notes.get(file_name)
        if note is None:
            reason = "has no Coverage row"
        elif not note.strip() or vfm.is_none_cell(note):
            reason = "has a Coverage row with no read-status note"
        else:
            continue
        entry = citations[file_name]
        offenders.append(
            f"refusing to emit Coverage: cited file '{file_name}' {reason}\n"
            f"  cited by: {format_scenario_ids(entry.refs)} ({'; '.join(entry.provenance)})\n"
            "  add a Coverage row whose note records what was read, then re-run"
        )
    return offenders


def process_coverage(
    vfm: ModuleType, doc: FlowDocument, citations: dict[str, Citation]
) -> tuple[SectionReport, list[tuple[Any, tuple[str, ...]]]]:
    table = doc.tables["Coverage"]
    report = SectionReport(name="Coverage")
    rendered: list[tuple[Any, tuple[str, ...]]] = []
    for row, values in vfm.row_dicts(table):
        report.rows += 1
        file_name = vfm.normalize_repo_path(values.get("file", "")) or ""
        declared = vfm.parse_scenario_ids(values.get("scenarios", ""))
        computed = citations.get(file_name, Citation(refs=set(), provenance=[])).refs
        derivations = [
            CellDerivation(
                column_index(table, "scenarios"),
                declared,
                computed,
                format_scenario_ids,
            )
        ]
        new_cells = apply_derivations(row.cells, derivations)
        new_line = render_row(new_cells)
        if new_line != doc.lines[row.line - 1]:
            report.differing += 1
        rendered.append((row, new_cells))
    return report, rendered


# ---------------------------------------------------------------------------
# P4 -- Runtime applicability `unreachable scenarios`
# ---------------------------------------------------------------------------


def process_runtime(
    vfm: ModuleType, doc: FlowDocument
) -> tuple[SectionReport, list[tuple[Any, tuple[str, ...]]]]:
    table = doc.tables["Runtime applicability"]
    report = SectionReport(name="Runtime applicability")
    rendered: list[tuple[Any, tuple[str, ...]]] = []
    for row, values in vfm.row_dicts(table):
        report.rows += 1
        reachable_raw = vfm.normalize_symbol(values.get("reachable scenarios", ""))
        declared_unreachable_raw = vfm.normalize_symbol(
            values.get("unreachable scenarios", "")
        )
        if reachable_raw.upper() == "UNKNOWN":
            new_cells = row.cells  # both cells stay UNKNOWN; authored, untouched
        else:
            reachable = vfm.parse_scenario_ids(reachable_raw)
            declared_unreachable = vfm.parse_scenario_ids(declared_unreachable_raw)
            computed_unreachable = doc.all_ids - reachable
            derivations = [
                CellDerivation(
                    column_index(table, "unreachable scenarios"),
                    declared_unreachable,
                    computed_unreachable,
                    format_scenario_ids,
                )
            ]
            new_cells = apply_derivations(row.cells, derivations)
        new_line = render_row(new_cells)
        if new_line != doc.lines[row.line - 1]:
            report.differing += 1
        rendered.append((row, new_cells))
    return report, rendered


# ---------------------------------------------------------------------------
# P5 -- Coverage `Verdict distribution` line
# ---------------------------------------------------------------------------

VERDICT_LINE_PREFIX = "Verdict distribution:"


def compute_verdict_distribution(doc: FlowDocument) -> dict[str, int]:
    counts = {"PASS": 0, "UNKNOWN": 0, "FAIL": 0}
    for scenario in doc.scenarios.values():
        if scenario.verdict in counts:
            counts[scenario.verdict] += 1
    return counts


def render_verdict_line(counts: dict[str, int]) -> str:
    return (
        f"- **Verdict distribution:** PASS {counts['PASS']} · "
        f"UNKNOWN {counts['UNKNOWN']} · FAIL {counts['FAIL']}."
    )


def find_verdict_line(doc: FlowDocument) -> int | None:
    for index, line in enumerate(doc.lines):
        if VERDICT_LINE_PREFIX in line:
            return index
    return None


def process_verdict_distribution(doc: FlowDocument) -> SectionReport:
    report = SectionReport(name="Verdict distribution")
    line_index = find_verdict_line(doc)
    counts = compute_verdict_distribution(doc)
    rendered = render_verdict_line(counts)
    report.rows = 1
    if line_index is None or doc.lines[line_index] != rendered:
        report.differing = 1
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def render_table_text(
    doc: FlowDocument, section_doc_name: str, rows: list[tuple[Any, tuple[str, ...]]]
) -> list[str]:
    table = doc.tables[section_doc_name]
    header_raw = doc.lines[table.header_line - 1]
    separator_raw = doc.lines[table.header_line]
    out = [header_raw, separator_raw]
    out.extend(render_row(cells) for _row, cells in rows)
    return out


def run_certify(
    vfm: ModuleType, doc: FlowDocument, code: Any, selected: set[SectionName]
) -> int:
    incoming = compute_incoming(vfm, vfm.row_dicts(doc.tables["Call graph"]))
    citations = compute_coverage_citations(vfm, doc, incoming, code)
    refusals = (
        check_coverage_refusal(vfm, doc, citations)
        if SectionName.COVERAGE in selected
        else []
    )

    reports: list[SectionReport] = []
    if SectionName.SYMBOL_INDEX in selected:
        report, _rows = process_symbol_index(vfm, doc, incoming)
        reports.append(report)
    if SectionName.CALL_GRAPH in selected:
        report, _rows = process_call_graph(vfm, doc)
        reports.append(report)
    if SectionName.COVERAGE in selected and not refusals:
        report, _rows = process_coverage(vfm, doc, citations)
        reports.append(report)
    if SectionName.RUNTIME in selected:
        report, _rows = process_runtime(vfm, doc)
        reports.append(report)
    if SectionName.VERDICT_DISTRIBUTION in selected:
        reports.append(process_verdict_distribution(doc))

    try:
        display = doc.path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        display = str(doc.path)

    print(f"certify: {display}")
    print("| section | rows | differing | notes |")
    print("|---|---|---|---|")
    for report in reports:
        note_count = len(report.notes or [])
        print(f"| {report.name} | {report.rows} | {report.differing} | {note_count} |")
    for report in reports:
        for note in report.notes or []:
            print(f"  [{report.name}] {note}")
    for offender in refusals:
        print(offender, file=sys.stderr)

    # A bare bottom line, deliberately separate from the human-readable table above:
    # this is the machine-parseable seam `probe_checker.py --count-mode grep-c` reads.
    # The report table's presence on BOTH a clean and a differing run means line-count
    # alone cannot tell them apart -- an unprobed zero is UNREAD, not clean (spec SS12).
    total_problems = sum(report.differing for report in reports) + len(refusals)
    print(total_problems)

    if refusals:
        return EXIT_REFUSED
    if any(report.differing for report in reports):
        return EXIT_DIFFERING
    return EXIT_OK


def run_emit(
    vfm: ModuleType, doc: FlowDocument, code: Any, selected: set[SectionName]
) -> int:
    incoming = compute_incoming(vfm, vfm.row_dicts(doc.tables["Call graph"]))
    citations = compute_coverage_citations(vfm, doc, incoming, code)

    if SectionName.COVERAGE in selected:
        refusals = check_coverage_refusal(vfm, doc, citations)
        if refusals:
            for offender in refusals:
                print(offender, file=sys.stderr)
            return EXIT_REFUSED

    chunks: list[str] = []
    if SectionName.SYMBOL_INDEX in selected:
        _report, rows = process_symbol_index(vfm, doc, incoming)
        chunks.append("## Symbol index")
        chunks.append("")
        chunks.extend(render_table_text(doc, "Symbol index", rows))
    if SectionName.CALL_GRAPH in selected:
        _report, rows = process_call_graph(vfm, doc)
        chunks.append("## Call graph")
        chunks.append("")
        chunks.extend(render_table_text(doc, "Call graph", rows))
    if SectionName.COVERAGE in selected:
        _report, rows = process_coverage(vfm, doc, citations)
        chunks.append("## Coverage")
        chunks.append("")
        chunks.extend(render_table_text(doc, "Coverage", rows))
    if SectionName.RUNTIME in selected:
        _report, rows = process_runtime(vfm, doc)
        chunks.append("## Runtime applicability")
        chunks.append("")
        chunks.extend(render_table_text(doc, "Runtime applicability", rows))
    if SectionName.VERDICT_DISTRIBUTION in selected:
        chunks.append(render_verdict_line(compute_verdict_distribution(doc)))

    print("\n".join(chunks))
    return EXIT_OK


def resolve_selected(section: SectionName) -> set[SectionName]:
    if section is SectionName.ALL:
        return set(EMIT_ORDER)
    return {section}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path, help="a docs/flows/*.md flow document")
    parser.add_argument(
        "--section",
        type=SectionName,
        choices=list(SectionName),
        default=SectionName.ALL,
    )
    parser.add_argument(
        "--certify", action="store_true", help="compare instead of emit"
    )
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--code-root", type=Path)
    return parser


def configure(project_root: Path, code_root: Path | None = None) -> None:
    """Select consumer paths without changing immutable plugin resources."""
    global REPO_ROOT, DEFAULT_CODE_ROOT
    REPO_ROOT = project_root.resolve()
    DEFAULT_CODE_ROOT = (code_root or REPO_ROOT).resolve()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure(
        args.project_root,
        (args.project_root / args.code_root)
        if args.code_root is not None
        else (
            DEFAULT_CODE_ROOT
            if args.project_root.resolve() == REPO_ROOT
            else args.project_root
        ),
    )
    args.code_root = DEFAULT_CODE_ROOT
    if getattr(args, "document", None) is not None:
        args.document = REPO_ROOT / args.document
    if not REPO_ROOT.is_dir():
        print(f"project root not found: {REPO_ROOT}", file=sys.stderr)
        return 2

    if not args.code_root.is_dir():
        print(
            f"generate_flow_projections: code root not found: {args.code_root}",
            file=sys.stderr,
        )
        return EXIT_UNPARSEABLE

    vfm = load_validator()
    doc = parse_document(vfm, args.document)
    # Built once per process, passed down (spec SS10 cost note); nothing below rebuilds it.
    code = vfm.CodeIndex.build(args.code_root)

    selected = resolve_selected(args.section)
    if args.certify:
        return run_certify(vfm, doc, code, selected)
    return run_emit(vfm, doc, code, selected)


if __name__ == "__main__":
    raise SystemExit(main())
