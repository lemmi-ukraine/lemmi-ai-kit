"""Validate a flow risk register and its scenario/citation links.

Required finding fields and vocabularies are defined by the bundled schema.
Symbol notes remain informational because AST indexing cannot resolve dynamic references.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from flow_support import probe_project

REPO_ROOT = Path.cwd().resolve()
DEFAULT_CODE_ROOT = REPO_ROOT
DEFAULT_FLOWS_ROOT = REPO_ROOT / "docs" / "flows"
PROBE_CHECKER = (
    Path(__file__).resolve().parents[2] / "post-task-review/scripts/probe_checker.py"
)
VFM_PATH = Path(__file__).with_name("validate_flow_map.py")
FIXTURES_ROOT = (
    Path(__file__).resolve().parent.parent
    / "assets/probe-project/scripts/fixtures/register"
)

CHECKS = (
    "heading",
    "bullets",
    "severity",
    "class",
    "observed",
    "citation",
    "line-cite",
)
NON_BLOCKING_CHECKS = frozenset({"symbols"})
ALL_CHECKS = CHECKS + ("symbols",)

REQUIRED_LABELS: tuple[str, ...] = (
    "Class",
    "Severity",
    "Symbol",
    "Observed",
    "Verdict",
    "Reconciled against",
    "Provenance",
)

FILENAME_RE = re.compile(r"^BUG-register-flow-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")
HEADING_RE = re.compile(r"^### (R-\S+)")
BULLET_LINE_RE = re.compile(r"^- ")
LABEL_RE = re.compile(r"^- \*\*([A-Za-z][A-Za-z ]*?):\*\*\s?(.*)$")
NO_FIX_RE = re.compile(r"^- \*\*No fix proposed\b")

SEVERITY_LINE_RE = re.compile(r"^- \*\*Severity:\*\* (.*)$")
SEVERITY_VALUE_RE = re.compile(r"^(Critical|High|Medium|Low)(?: \([^()]+\)| — .+)?$")

CLASS_LINE_RE = re.compile(r"^- \*\*Class:\*\* (.*)$")
CLASS_VALUES = {"bug", "risk", "STALE-comment", "doc-contradiction", "UNKNOWN"}

SCENARIO_ID_SEARCH_RE = re.compile(r"\b[A-Z]{2,4}-\d{2,3}\b")
NO_COVERING_ROW = "**no covering row**"

INLINE_CODE_RE = re.compile(r"`([^`]*)`")
# A sibling REGISTER ENTRY id (`R-SA-05`, `R-connection-transport-05`) is not a scenario
# citation, but its trailing `-NN` makes the legacy uppercase form look exactly like the
# scenario id `SA-05` to SCENARIO_ID_SEARCH_RE. Stripped before the scenario search so the
# `observed` rule cannot resolve against an id the entry never cited (roadmap item 35).
ENTRY_ID_RE = re.compile(r"\bR-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-\d{2,3}\b")
# "... cited in <file> as `Class.method`" introduces a symbol the entry asserts is WRONG. It is
# the entry's evidence, not its subject, so it is stripped before symbol resolution (P0-R1 F7).
QUOTED_AS_WRONG_RE = re.compile(r"\bcited\b.{0,200}?\bas\s+`[^`]+`")
SYMBOL_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+(?:\(\))?$")

TASKS_PATH_RE = re.compile(r"`(tasks/[A-Za-z0-9_./-]+\.md)`")
LINE_CITE_A_RE = re.compile(r"\.(?:py|md|yaml):\d+")
LINE_CITE_B_RE = re.compile(r"`[^`]*`.{0,60}?\blines?\s+\d+\b")


def _load_vfm():
    spec = importlib.util.spec_from_file_location("vfm", VFM_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["vfm"] = module  # load-bearing: @dataclass resolves via sys.modules
    spec.loader.exec_module(module)
    return module


vfm = _load_vfm()


@dataclass(frozen=True)
class Finding:
    check: str
    line: int
    message: str


@dataclass(frozen=True)
class ProbeCase:
    label: str
    check: str | None
    positive: str
    expected: int
    mode: str = "document"  # "document" | "join"


# Counts are an executable manifest, not historical stamps: --probe-stamps re-runs every pair
# through probe_checker.py and fails on any count drift.
PROBE_CASES: tuple[ProbeCase, ...] = (
    ProbeCase("heading", "heading", "BUG-register-flow-example-bad.md", 1),
    ProbeCase("bullets", "bullets", "BUG-register-flow-example-bad.md", 2),
    ProbeCase("severity", "severity", "BUG-register-flow-example-bad.md", 1),
    ProbeCase("class", "class", "BUG-register-flow-example-bad.md", 1),
    ProbeCase("observed", "observed", "BUG-register-flow-example-bad.md", 1),
    ProbeCase("citation", "citation", "BUG-register-flow-example-bad.md", 1),
    ProbeCase("line-cite", "line-cite", "BUG-register-flow-example-bad.md", 2),
    ProbeCase("symbols", "symbols", "BUG-register-flow-example-bad.md", 1),
    # roadmap item 35: an Observed bullet whose ONLY id is a sibling entry id. The fixture's own
    # flows document carries QC-05, so before the fix the extracted `QC-05` RESOLVED and the rule
    # stayed silent -- the fixture has to make the coincidence real or it proves nothing.
    ProbeCase(
        "observed-sibling-entry-id", "observed", "BUG-register-flow-siblingcite.md", 1
    ),
    ProbeCase("aggregate", None, "BUG-register-flow-example-bad.md", 10),
    ProbeCase("join-unrouted", None, "join/registers-unrouted.md", 1, mode="join"),
)


def slug_from_path(path: Path) -> str | None:
    match = FILENAME_RE.match(path.stem)
    return match.group("slug") if match else None


def entry_blocks(lines: Sequence[str]) -> list[tuple[str, int, int]]:
    """(entry_id, heading_line_index, end_index) for each '### R-...' heading, 0-indexed."""
    headings = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            headings.append((match.group(1), index))
    blocks: list[tuple[str, int, int]] = []
    for position, (entry_id, index) in enumerate(headings):
        end = headings[position + 1][1] if position + 1 < len(headings) else len(lines)
        blocks.append((entry_id, index, end))
    return blocks


def bullet_spans(lines: Sequence[str], start: int, end: int) -> list[tuple[int, int]]:
    """(span_start, span_end) index ranges for each top-level '- ' bullet within [start, end)."""
    starts = [i for i in range(start, end) if BULLET_LINE_RE.match(lines[i])]
    spans: list[tuple[int, int]] = []
    for position, span_start in enumerate(starts):
        span_end = starts[position + 1] if position + 1 < len(starts) else end
        spans.append((span_start, span_end))
    return spans


def label_of(line: str) -> str | None:
    match = LABEL_RE.match(line)
    return match.group(1) if match else None


def resolve_flow_scenarios(flows_root: Path, slug: str) -> set[str]:
    """Scenario ids in flows_root/{slug}.md's '## Scenarios' table. Empty if absent/empty."""
    doc = flows_root / f"{slug}.md"
    if not doc.is_file():
        return set()
    lines = doc.read_text(encoding="utf-8").splitlines()
    _sections, by_name = vfm.parse_sections(lines)
    sections = by_name.get("Scenarios")
    if not sections:
        return set()
    table = vfm.first_table(lines, sections[0])
    ids: set[str] = set()
    for _row, values in vfm.row_dicts(table):
        sid = vfm.normalize_symbol(values.get("#", ""))
        if vfm.SCENARIO_ID_RE.fullmatch(sid):
            ids.add(sid)
    return ids


_TRACKED_CACHE: dict[str, bool] = {}


def is_tracked_at_head(rel_path: str) -> bool:
    if rel_path not in _TRACKED_CACHE:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", rel_path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        _TRACKED_CACHE[rel_path] = bool(result.stdout.strip())
    return _TRACKED_CACHE[rel_path]


def check_citations(lines: Sequence[str], findings: list[Finding]) -> None:
    for index, line in enumerate(lines):
        for match in TASKS_PATH_RE.finditer(line):
            path = match.group(1)
            if not is_tracked_at_head(path):
                findings.append(
                    Finding(
                        "citation",
                        index + 1,
                        f"cited path '{path}' is not tracked at HEAD (git ls-tree -r --name-only HEAD)",
                    )
                )


def check_line_cite(lines: Sequence[str], findings: list[Finding]) -> None:
    for index, line in enumerate(lines):
        if LINE_CITE_A_RE.search(line) or LINE_CITE_B_RE.search(line):
            findings.append(
                Finding(
                    "line-cite",
                    index + 1,
                    "cites a file by 'path:NN' / 'line NN' instead of a register/scenario id (RC1-05)",
                )
            )


def validate(path: Path, flows_root: Path, code_root: Path) -> list[Finding]:
    lines = path.read_text(encoding="utf-8").splitlines()
    findings: list[Finding] = []

    slug = slug_from_path(path)
    if slug is None:
        findings.append(
            Finding(
                "heading",
                1,
                f"filename '{path.name}' does not match 'BUG-register-flow-{{slug}}.md'",
            )
        )

    flow_scenarios = (
        resolve_flow_scenarios(flows_root, slug) if slug is not None else set()
    )
    code = vfm.CodeIndex.build(code_root)

    seen_ids: set[str] = set()
    for entry_id, start, end in entry_blocks(lines):
        heading_line = start + 1
        if entry_id in seen_ids:
            findings.append(
                Finding("heading", heading_line, f"duplicate entry id '{entry_id}'")
            )
        else:
            seen_ids.add(entry_id)
        if slug is not None:
            expected = re.compile(rf"^R-{re.escape(slug)}-\d+$")
            if not expected.fullmatch(entry_id):
                findings.append(
                    Finding(
                        "heading",
                        heading_line,
                        f"entry id '{entry_id}' does not match 'R-{slug}-NN' for this file's slug",
                    )
                )

        by_label: dict[str, list[tuple[int, int]]] = {}
        for span_start, span_end in bullet_spans(lines, start + 1, end):
            label = label_of(lines[span_start])
            if label is not None:
                by_label.setdefault(label, []).append((span_start, span_end))
        has_no_fix = any(NO_FIX_RE.match(lines[i]) for i in range(start, end))

        for label in REQUIRED_LABELS:
            count = len(by_label.get(label, []))
            if count == 0:
                findings.append(
                    Finding(
                        "bullets",
                        heading_line,
                        f"{entry_id} is missing required bullet '**{label}:**'",
                    )
                )
            elif count > 1:
                findings.append(
                    Finding(
                        "bullets",
                        heading_line,
                        f"{entry_id} has {count} '**{label}:**' bullets; expected exactly one",
                    )
                )
        if not has_no_fix:
            findings.append(
                Finding(
                    "bullets",
                    heading_line,
                    f"{entry_id} is missing the 'No fix proposed' line",
                )
            )

        severity_spans = by_label.get("Severity", [])
        if len(severity_spans) == 1:
            span_start, _span_end = severity_spans[0]
            match = SEVERITY_LINE_RE.match(lines[span_start])
            value = match.group(1).strip() if match else ""
            if not SEVERITY_VALUE_RE.fullmatch(value):
                findings.append(
                    Finding(
                        "severity",
                        span_start + 1,
                        f"{entry_id} Severity '{value}' is not Critical/High/Medium/Low with "
                        "an optional ' (rationale)' or ' — rationale'",
                    )
                )

        class_spans = by_label.get("Class", [])
        if len(class_spans) == 1:
            span_start, _span_end = class_spans[0]
            match = CLASS_LINE_RE.match(lines[span_start])
            value = match.group(1).strip() if match else ""
            if value not in CLASS_VALUES:
                findings.append(
                    Finding(
                        "class",
                        span_start + 1,
                        f"{entry_id} Class '{value}' is not one of {sorted(CLASS_VALUES)}",
                    )
                )

        observed_spans = by_label.get("Observed", [])
        if len(observed_spans) == 1:
            span_start, span_end = observed_spans[0]
            block_text = " ".join(lines[span_start:span_end])
            mentioned = SCENARIO_ID_SEARCH_RE.findall(ENTRY_ID_RE.sub(" ", block_text))
            resolves = any(sid in flow_scenarios for sid in mentioned)
            if not resolves and NO_COVERING_ROW not in block_text:
                findings.append(
                    Finding(
                        "observed",
                        span_start + 1,
                        f"{entry_id} Observed names no scenario id resolving in "
                        f"docs/flows/{slug}.md and lacks the literal '**no covering row**'",
                    )
                )

        symbol_spans = by_label.get("Symbol", [])
        if len(symbol_spans) == 1:
            span_start, span_end = symbol_spans[0]
            block_text = " ".join(lines[span_start:span_end])
            subject_text = QUOTED_AS_WRONG_RE.sub(" ", block_text)
            reported: set[str] = set()
            for token_match in INLINE_CODE_RE.finditer(subject_text):
                token = token_match.group(1)
                candidate = token[:-2] if token.endswith("()") else token
                if candidate in reported:
                    continue  # same symbol named twice in one bullet (e.g. "accept() ... again")
                if SYMBOL_RE.fullmatch(candidate) and not code.resolves(candidate):
                    reported.add(candidate)
                    findings.append(
                        Finding(
                            "symbols",
                            span_start + 1,
                            f"{entry_id} Symbol '{candidate}' does not resolve (may be an "
                            "instance attribute or closure the index cannot see; not a failure)",
                        )
                    )

    check_citations(lines, findings)
    check_line_cite(lines, findings)

    findings.sort(
        key=lambda finding: (
            finding.line,
            ALL_CHECKS.index(finding.check),
            finding.message,
        )
    )
    return findings


def _iter_markdown(path: Path, pattern: str) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob(pattern))
    if path.is_file():
        return [path]
    return []


def collect_flow_verdicts(
    flows_root: Path,
) -> tuple[dict[str, tuple[str, Path, int]], list[str]]:
    """scenario id -> (verdict, owning doc, row line), for verdict in {FAIL, UNKNOWN}.

    A file with no '## Scenarios' section is an index/README, not a flow map, and is
    excluded by name (returned separately) rather than silently skipped.
    """
    result: dict[str, tuple[str, Path, int]] = {}
    excluded: list[str] = []
    for doc in _iter_markdown(flows_root, "*.md"):
        lines = doc.read_text(encoding="utf-8").splitlines()
        _sections, by_name = vfm.parse_sections(lines)
        sections = by_name.get("Scenarios")
        if not sections:
            excluded.append(doc.name)
            continue
        table = vfm.first_table(lines, sections[0])
        for row, values in vfm.row_dicts(table):
            sid = vfm.normalize_symbol(values.get("#", ""))
            if not vfm.SCENARIO_ID_RE.fullmatch(sid):
                continue
            verdict = vfm.normalize_symbol(values.get("verdict", "")).upper()
            if verdict in ("FAIL", "UNKNOWN"):
                result[sid] = (verdict, doc, row.line)
    return result, excluded


def collect_register_mentions(registers_root: Path) -> set[str]:
    mentioned: set[str] = set()
    for doc in _iter_markdown(registers_root, "BUG-register-flow-*.md"):
        lines = doc.read_text(encoding="utf-8").splitlines()
        for _entry_id, start, end in entry_blocks(lines):
            block_text = "\n".join(lines[start:end])
            mentioned.update(SCENARIO_ID_SEARCH_RE.findall(block_text))
    return mentioned


def run_join(flows_root: Path, registers_root: Path) -> int:
    flow_files = _iter_markdown(flows_root, "*.md")
    if not flow_files or not registers_root.exists():
        print("flow/register corpus missing or empty", file=sys.stderr)
        return 2
    fail_or_unknown, _excluded = collect_flow_verdicts(flows_root)
    if len(_excluded) == len(flow_files):
        print("no flow scenarios found in corpus", file=sys.stderr)
        return 2
    mentioned = collect_register_mentions(registers_root)
    unrouted = sorted(
        (sid, verdict, doc, line)
        for sid, (verdict, doc, line) in fail_or_unknown.items()
        if sid not in mentioned
    )
    for sid, verdict, doc, line in unrouted:
        try:
            display = doc.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            display = str(doc)
        print(
            f"[join] {display}:{line}: scenario {sid} ({verdict}) is not named by any register entry"
        )
    return 1 if unrouted else 0


def render_findings(path: Path, findings: Sequence[Finding]) -> None:
    for finding in findings:
        try:
            display = path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            display = str(path)
        print(f"[{finding.check}] {display}:{finding.line}: {finding.message}")


def _run_probes(project: Path) -> int:
    fixtures = project / "scripts/fixtures/register"
    conformant = fixtures / "BUG-register-flow-example.md"
    join_negative = fixtures / "join" / "registers-routed.md"
    flows_fixture = fixtures / "flows"
    script = Path(__file__).resolve()
    failures = 0
    for case in PROBE_CASES:
        if case.mode == "join":
            checker_cmd = (
                f'"{sys.executable}" -B "{script}" --join "{flows_fixture}" "{{file}}"'
            )
            negative = join_negative
        else:
            parts = [
                f'"{sys.executable}"',
                "-B",
                f'"{script}"',
                "--flows-root",
                f'"{flows_fixture}"',
                '"{file}"',
            ]
            if case.check is not None:
                parts.extend(("--check", case.check))
            checker_cmd = " ".join(parts)
            negative = conformant
        checker_cmd += f' --project-root "{project}" --code-root src'
        command = [
            sys.executable,
            "-B",
            str(PROBE_CHECKER),
            "--cmd",
            checker_cmd,
            "--positive",
            str(fixtures / case.positive),
            "--negative",
            str(negative),
            "--expect-positive-exact",
            str(case.expected),
            "--label",
            case.label,
        ]
        completed = subprocess.run(
            command,
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        if completed.returncode != 0:
            failures += 1
    if failures:
        print(f"register probe manifest: {failures} probe(s) failed", file=sys.stderr)
        return 1
    print(f"register probe manifest: PASS ({len(PROBE_CASES)} exact probe pairs)")
    return 0


def run_probes() -> int:
    with probe_project() as project:
        return _run_probes(project)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", nargs="?", type=Path)
    parser.add_argument("--flows-root", type=Path, default=Path("docs/flows"))
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--code-root", type=Path)
    parser.add_argument("--check", choices=ALL_CHECKS)
    parser.add_argument(
        "--probe-stamps",
        action="store_true",
        help="execute every exact positive/negative probe pair",
    )
    parser.add_argument(
        "--join",
        nargs=2,
        type=Path,
        metavar=("FLOWS_ROOT", "REGISTERS_ROOT"),
        help="corpus-level join: every FAIL/UNKNOWN scenario in FLOWS_ROOT must be named "
        "by some entry in REGISTERS_ROOT",
    )
    args = parser.parse_args(argv)

    modes = sum((args.probe_stamps, args.join is not None, args.document is not None))
    if modes == 0:
        parser.error(
            "one of: document, --probe-stamps, or --join FLOWS_ROOT REGISTERS_ROOT is required"
        )
    if modes > 1:
        parser.error("document, --probe-stamps and --join are mutually exclusive")
    return args


def configure(project_root: Path, code_root: Path | None = None) -> None:
    """Select consumer paths without changing immutable plugin resources."""
    global REPO_ROOT, DEFAULT_CODE_ROOT
    REPO_ROOT = project_root.resolve()
    DEFAULT_CODE_ROOT = (code_root or REPO_ROOT).resolve()
    global DEFAULT_FLOWS_ROOT
    DEFAULT_FLOWS_ROOT = REPO_ROOT / "docs/flows"
    _TRACKED_CACHE.clear()
    vfm.configure(REPO_ROOT, DEFAULT_CODE_ROOT)


def main(argv: Sequence[str] | None = None) -> int:
    # Findings/notes can carry non-ASCII (em dash, bold markers). Force UTF-8 out so a
    # narrow Windows console code page cannot abort the run mid-print.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
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
    args.flows_root = REPO_ROOT / args.flows_root
    if args.join is not None:
        args.join = [REPO_ROOT / p for p in args.join]

    if args.probe_stamps:
        return run_probes()
    if args.join is not None:
        flows_root, registers_root = args.join
        return run_join(flows_root, registers_root)
    assert args.document is not None
    if not args.document.is_file():
        print(f"register document not found: {args.document}", file=sys.stderr)
        return 2
    if not args.code_root.is_dir():
        print(f"code root not found: {args.code_root}", file=sys.stderr)
        return 2
    findings = validate(args.document, args.flows_root, args.code_root)
    visible = [f for f in findings if args.check is None or f.check == args.check]
    render_findings(args.document, visible)
    blocking = [f for f in visible if f.check not in NON_BLOCKING_CHECKS]
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
