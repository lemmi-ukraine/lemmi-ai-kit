"""Validate flow-map Markdown against the repository's canonical schema.

The validator is deliberately structural. It verifies the document's internal
contract and that cited Python symbols/files exist; it does not attempt to prove
runtime call edges or the truth of prose evidence.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from flow_support import probe_project

REPO_ROOT = Path.cwd().resolve()
DEFAULT_CODE_ROOT = REPO_ROOT
PROBE_CHECKER = (
    Path(__file__).resolve().parents[2] / "post-task-review/scripts/probe_checker.py"
)

CHECKS = (
    "sections",
    "provenance",
    "verdicts",
    "distribution",
    "symbols",
    "index",
    "diagram",
    "evidence",
    "tone",
    "legends",
    "crossflow",
)

REQUIRED_SECTIONS = (
    "Provenance",
    "Scenarios",
    "Cross-flow scenarios",
    "Runtime applicability",
    "Symbol index",
    "Invariants",
    "Call graph",
    "Coverage",
)

# Diagrams are PERMITTED but no longer REQUIRED (improvement-plan item 2): a document may
# omit the section entirely, and a retained Mermaid block no longer needs an adjacent legend
# table. They still may not appear twice or out of canonical position -- dropping them from
# the membership check instead of moving them here would make every "## Diagrams" in the
# corpus an unexpected-H2 finding, which is a regression, not a reduction.
OPTIONAL_SECTIONS = ("Diagrams",)
PERMITTED_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS

# `## Provenance` CONTENT was completely unvalidated before improvement-plan item 3: a copy
# of the conformant fixture with every bullet deleted validated at rc 0 / zero bytes,
# indistinguishable from an intact control. Each label below must appear with non-empty
# content. The label is matched only up to its colon, so a parenthetical qualifier such as
# `**Owned files (comment pass):**` -- the spelling all seven corpus documents use -- counts.
#
# KNOWN LIMIT: the bullet scan does not track code fences, so a fenced EXAMPLE inside
# `## Provenance` would satisfy the check. No corpus document fences that section, and fence
# tracking is more apparatus than the hole is worth -- recorded here so a reader does not
# over-read what a clean `provenance` result proves.
#
# B1-I: add "Evidence sources" here once the seven legacy documents declare theirs. The
# template already ships that fifth bullet, so every NEW document carries it; enforcing it
# now would fail all seven at once, and this pass is forbidden from editing them.
PROVENANCE_REQUIRED_BULLETS = (
    "Flow / session",
    "Mapped at",
    "Owned files",
    "Authority",
)

TABLE_HEADERS: dict[str, tuple[str, ...]] = {
    "Scenarios": ("#", "class", "trigger", "path", "verdict", "evidence"),
    "Cross-flow scenarios": (
        "scenario",
        "owning flow",
        "this document's contribution",
    ),
    "Runtime applicability": (
        "profile",
        "effective switches",
        "reachable scenarios",
        "unreachable scenarios",
        "evidence",
    ),
    "Symbol index": ("symbol", "file", "scenarios", "called by", "invariants"),
    "Invariants": ("#", "symbol", "constraint", "breaks if violated"),
    "Call graph": ("caller", "callee", "site", "scenarios"),
    "Coverage": ("file", "scenarios", "coverage note"),
}

CLASS_VALUES = {"main", "alternative", "edge"}
VERDICT_VALUES = {"PASS", "UNKNOWN", "FAIL"}
SCENARIO_ID_RE = re.compile(r"^[A-Z]{2,4}-\d{2,3}$")
SCENARIO_ID_SEARCH_RE = re.compile(r"\b[A-Z]{2,4}-\d{2,3}\b")
INVARIANT_ID_RE = re.compile(r"^INV-\d{2,3}$")
INVARIANT_ID_SEARCH_RE = re.compile(r"\bINV-\d{2,3}\b")
SYMBOL_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+(?:\(\))?$")
EXTERNAL_RE = re.compile(r"^external[:]\s*\S.+$", re.IGNORECASE)
EVIDENCE_RE = re.compile(
    r"^(code|test|log|provider-doc|event-capture):\s*(\S.*)$",
    re.IGNORECASE,
)
TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_SCENARIO_RE = re.compile(r"^###\s+([A-Z]{2,4}-\d{2,3})\b")
INLINE_CODE_RE = re.compile(r"`([^`]*)`")
FILE_REF_RE = re.compile(
    r"(?<![\w.-])("
    r"(?:[A-Za-z_.][A-Za-z0-9_.-]*/)+"
    r"[A-Za-z0-9_./-]+\.(?:py|md|yaml|yml|json|toml)"
    r"|(?:cloudbuild|docker-compose)[A-Za-z0-9_.-]*\.(?:yaml|yml)"
    r")(?![\w.-])"
)
BANNED_TONE_PATTERNS = (
    ("please", re.compile(r"\bplease\b", re.IGNORECASE)),
    ("note that", re.compile(r"\bnote\s+that\b", re.IGNORECASE)),
    (
        "it's worth noting",
        re.compile(r"\bit(?:'|’)s\s+worth\s+noting\b", re.IGNORECASE),
    ),
    ("as you can see", re.compile(r"\bas\s+you\s+can\s+see\b", re.IGNORECASE)),
    ("simply", re.compile(r"\bsimply\b", re.IGNORECASE)),
    ("just", re.compile(r"\bjust\b", re.IGNORECASE)),
    ("obviously", re.compile(r"\bobviously\b", re.IGNORECASE)),
    ("clearly", re.compile(r"\bclearly\b", re.IGNORECASE)),
    ("in order to", re.compile(r"\bin\s+order\s+to\b", re.IGNORECASE)),
    ("additionally", re.compile(r"\badditionally\b", re.IGNORECASE)),
    ("furthermore", re.compile(r"\bfurthermore\b", re.IGNORECASE)),
)
UNCERTAINTY_PATTERNS = (
    ("probably", re.compile(r"\bprobably\b", re.IGNORECASE)),
    ("maybe", re.compile(r"\bmaybe\b", re.IGNORECASE)),
    ("may", re.compile(r"\bmay\b", re.IGNORECASE)),
    ("might", re.compile(r"\bmight\b", re.IGNORECASE)),
    ("possibly", re.compile(r"\bpossibly\b", re.IGNORECASE)),
    ("apparently", re.compile(r"\bapparently\b", re.IGNORECASE)),
    ("seems", re.compile(r"\bseems\b", re.IGNORECASE)),
    ("looks like", re.compile(r"\blooks\s+like\b", re.IGNORECASE)),
    ("appears to", re.compile(r"\bappears\s+to\b", re.IGNORECASE)),
    ("likely", re.compile(r"\blikely\b", re.IGNORECASE)),
    ("presumably", re.compile(r"\bpresumably\b", re.IGNORECASE)),
    ("I think", re.compile(r"\bI\s+think\b", re.IGNORECASE)),
)
SHOULD_RE = re.compile(r"\bshould\b", re.IGNORECASE)

MERMAID_QUALIFIED_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b")
MERMAID_PASCAL_RE = re.compile(r"\b[A-Z][a-z0-9_]+(?:[A-Z][A-Za-z0-9_]*)+\b")
MERMAID_KEYWORDS = {
    "SequenceDiagram",
    "Flowchart",
    "StateDiagram",
}

LEGEND_HEADERS = ("participant / node", "symbol", "file", "scenarios")
EXPANSION_HEADERS = ("#", "symbol", "does", "on failure")


@dataclass(frozen=True)
class Finding:
    check: str
    line: int
    message: str


@dataclass(frozen=True)
class Section:
    name: str
    heading_line: int
    start: int
    end: int


@dataclass(frozen=True)
class TableRow:
    line: int
    cells: tuple[str, ...]

    def as_dict(self, headers: tuple[str, ...]) -> dict[str, str]:
        return dict(zip(headers, self.cells, strict=False))


@dataclass(frozen=True)
class MarkdownTable:
    header_line: int
    headers: tuple[str, ...]
    rows: tuple[TableRow, ...]
    malformed_rows: tuple[int, ...]


@dataclass(frozen=True)
class MermaidBlock:
    start: int
    end: int
    body: tuple[str, ...]


@dataclass(frozen=True)
class ProbeCase:
    label: str
    check: str | None
    positive: str
    expected: int


# Counts are an executable manifest, not historical stamps. --probe-stamps
# re-runs every pair through probe_checker.py and fails on any count drift.
PROBE_CASES: tuple[ProbeCase, ...] = (
    ProbeCase("sections", "sections", "nonconformant.md", 1),
    ProbeCase("verdicts", "verdicts", "nonconformant.md", 2),
    ProbeCase("distribution", "distribution", "nonconformant.md", 1),
    ProbeCase("symbols", "symbols", "nonconformant.md", 1),
    ProbeCase("index", "index", "nonconformant.md", 1),
    ProbeCase("diagram", "diagram", "nonconformant.md", 1),
    ProbeCase("evidence", "evidence", "nonconformant.md", 1),
    ProbeCase("tone", "tone", "probe-tone.md", 24),
    ProbeCase("provenance", "provenance", "probe-provenance-stripped.md", 4),
    ProbeCase(
        "runtime-references",
        "symbols",
        "probe-runtime-references.md",
        1,
    ),
    ProbeCase(
        "runtime-unknown-pair",
        "symbols",
        "probe-runtime-unknown-pair.md",
        1,
    ),
    ProbeCase(
        "unknown-expansion",
        "verdicts",
        "probe-unknown-expansion.md",
        1,
    ),
    ProbeCase(
        "coverage-citation",
        "symbols",
        "probe-coverage-citation.md",
        1,
    ),
    ProbeCase(
        "legend-scenario",
        "legends",
        "probe-legend-scenario.md",
        1,
    ),
    ProbeCase(
        "crossflow-missing-id",
        "crossflow",
        "probe-crossflow-missing-id.md",
        1,
    ),
    ProbeCase(
        "crossflow-wrong-id-no-backpointer",
        "crossflow",
        "probe-crossflow-wrong-id-no-backpointer.md",
        1,
    ),
    # KNOWN LIMIT, deliberately NOT a probe pair (tasks/TECH-flow-map-validator-cross-doc-
    # resolve.md): a wrong-but-existing id whose SIBLING carries a doc-level back-pointer (some
    # row into this document, just not the specific one named in this row's own prose) yields 0
    # findings -- existence passes (the id is real) and reciprocity reads doc-level, not none.
    # Resolution proves the id EXISTS and shows a reviewer the row it lands on; it cannot prove
    # that row is the RIGHT one. `probe-crossflow-wrong-id-doclevel.md` demonstrates this and is
    # exercised by neither this manifest nor `--probe-stamps` -- a pair asserting 0 on a planted
    # defect would certify the checker's own blindness, not its sight.
    ProbeCase("aggregate", None, "nonconformant.md", 9),
)


class CodeIndex:
    """AST-derived existence index for local Python symbols."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._symbols: dict[str, set[str]] = {}
        self._callables: set[str] = set()

    @classmethod
    def build(cls, root: Path) -> CodeIndex:
        index = cls(root)
        for path in sorted(root.rglob("*.py")):
            if any(
                p.startswith(".") or p in {"node_modules", "__pycache__"}
                for p in path.relative_to(root).parts
            ):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            index._add_tree(path, tree)
        return index

    def _display_path(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return resolved.relative_to(self.root).as_posix()

    def _add(self, symbol: str, path: str, *, callable_: bool = False) -> None:
        self._symbols.setdefault(symbol, set()).add(path)
        if callable_:
            self._callables.add(symbol)

    def _add_tree(self, path: Path, tree: ast.Module) -> None:
        file_name = self._display_path(path)
        module = path.stem
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add(node.name, file_name, callable_=True)
                self._add(f"{module}.{node.name}", file_name, callable_=True)
            elif isinstance(node, ast.ClassDef):
                self._add(node.name, file_name, callable_=True)
                self._add(f"{module}.{node.name}", file_name, callable_=True)
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for symbol in (
                            f"{node.name}.{child.name}",
                            f"{module}.{node.name}.{child.name}",
                        ):
                            self._add(symbol, file_name, callable_=True)
                    elif isinstance(child, (ast.Assign, ast.AnnAssign)):
                        for name in assigned_names(child):
                            self._add(f"{node.name}.{name}", file_name)
                            self._add(f"{module}.{node.name}.{name}", file_name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for name in assigned_names(node):
                    self._add(name, file_name)
                    self._add(f"{module}.{name}", file_name)

    def files_for(self, raw_symbol: str) -> set[str]:
        symbol = normalize_symbol(raw_symbol)
        direct = self._symbols.get(symbol)
        if direct:
            return set(direct)

        parts = symbol.split(".")
        candidates: set[str] = set()
        for key, files in self._symbols.items():
            if (
                key == symbol
                or key.endswith(f".{symbol}")
                or (len(parts) >= 2 and key.endswith(f".{parts[-2]}.{parts[-1]}"))
            ):
                candidates.update(files)
        return candidates

    def resolves(self, raw_symbol: str) -> bool:
        return bool(self.files_for(raw_symbol))

    def is_callable(self, raw_symbol: str) -> bool:
        symbol = normalize_symbol(raw_symbol)
        if symbol in self._callables:
            return True
        return any(
            key.endswith(f".{symbol}") or key.endswith(symbol)
            for key in self._callables
        )


def assigned_names(node: ast.Assign | ast.AnnAssign) -> Iterable[str]:
    targets = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
    for target in targets:
        if isinstance(target, ast.Name):
            yield target.id


def normalize_header(value: str) -> str:
    return INLINE_CODE_RE.sub(r"\1", value).strip().casefold()


def normalize_symbol(value: str) -> str:
    symbol = INLINE_CODE_RE.sub(r"\1", value).strip()
    if symbol.endswith("()"):
        symbol = symbol[:-2]
    return symbol


def split_cells(line: str) -> tuple[str, ...]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return tuple(cell.strip() for cell in stripped.split("|"))


def is_separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(TABLE_SEPARATOR_RE.fullmatch(cell) for cell in cells)


def parse_sections(
    lines: Sequence[str],
) -> tuple[list[Section], dict[str, list[Section]]]:
    headings: list[tuple[str, int]] = []
    in_fence = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = H2_RE.match(line)
        if match:
            headings.append((match.group(1).strip(), index))

    sections: list[Section] = []
    by_name: dict[str, list[Section]] = {}
    for position, (name, index) in enumerate(headings):
        end = headings[position + 1][1] if position + 1 < len(headings) else len(lines)
        section = Section(name=name, heading_line=index + 1, start=index + 1, end=end)
        sections.append(section)
        by_name.setdefault(name, []).append(section)
    return sections, by_name


def parse_table_at(lines: Sequence[str], index: int, end: int) -> MarkdownTable | None:
    if index + 1 >= end or not lines[index].strip().startswith("|"):
        return None
    headers_raw = split_cells(lines[index])
    separator = split_cells(lines[index + 1])
    if len(separator) != len(headers_raw) or not is_separator(separator):
        return None

    headers = tuple(normalize_header(cell) for cell in headers_raw)
    rows: list[TableRow] = []
    malformed: list[int] = []
    cursor = index + 2
    while cursor < end and lines[cursor].strip().startswith("|"):
        cells = split_cells(lines[cursor])
        if len(cells) != len(headers):
            malformed.append(cursor + 1)
        else:
            rows.append(TableRow(line=cursor + 1, cells=cells))
        cursor += 1
    return MarkdownTable(
        header_line=index + 1,
        headers=headers,
        rows=tuple(rows),
        malformed_rows=tuple(malformed),
    )


def first_table(lines: Sequence[str], section: Section) -> MarkdownTable | None:
    for index in range(section.start, section.end - 1):
        table = parse_table_at(lines, index, section.end)
        if table is not None:
            return table
    return None


def section_is_none(lines: Sequence[str], section: Section) -> bool:
    for line in lines[section.start : section.end]:
        stripped = line.strip()
        if stripped:
            return stripped.casefold() == "_none_"
    return False


def row_dicts(table: MarkdownTable | None) -> list[tuple[TableRow, dict[str, str]]]:
    if table is None:
        return []
    return [(row, row.as_dict(table.headers)) for row in table.rows]


def parse_scenario_ids(value: str) -> set[str]:
    return set(SCENARIO_ID_SEARCH_RE.findall(value))


def parse_invariant_ids(value: str) -> set[str]:
    return set(INVARIANT_ID_SEARCH_RE.findall(value))


def is_none_cell(value: str) -> bool:
    return normalize_symbol(value).casefold() in {"_none_", "—", "-"}


def parse_symbol_list(value: str) -> list[str]:
    if is_none_cell(value):
        return []
    plain = INLINE_CODE_RE.sub(r"\1", value).replace("·", ",")
    return [part.strip() for part in plain.split(",") if part.strip()]


def parse_path_symbols(value: str) -> list[str]:
    plain = INLINE_CODE_RE.sub(r"\1", value)
    return [part.strip() for part in plain.split("→") if part.strip()]


def normalize_repo_path(value: str) -> str | None:
    plain = INLINE_CODE_RE.sub(r"\1", value).strip().replace("\\", "/")
    if not plain or plain.startswith("/") or re.match(r"^[A-Za-z]:/", plain):
        return None
    candidate = (REPO_ROOT / plain).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return plain.removeprefix("./")


def repo_file_exists(value: str) -> bool:
    path = normalize_repo_path(value)
    return path is not None and (REPO_ROOT / path).is_file()


def extract_file_refs(value: str) -> set[str]:
    return {match.group(1).replace("\\", "/") for match in FILE_REF_RE.finditer(value)}


def symbol_related(left: str, right: str) -> bool:
    a = normalize_symbol(left)
    b = normalize_symbol(right)
    return a == b or a.startswith(f"{b}.") or b.startswith(f"{a}.")


def resolve_cross_flow_sibling(raw_cell: str, doc_path: Path) -> Path | None:
    """The 'owning flow' cell as a Path: repo-root-relative first, then relative to the
    citing document's own directory -- so a fixture under scripts/fixtures/flow_map/ can cite
    a sibling fixture there and stay self-contained, with no docs/flows/ path needed."""
    plain = INLINE_CODE_RE.sub(r"\1", raw_cell).strip().replace("\\", "/")
    if not plain:
        return None
    for candidate in (REPO_ROOT / plain, doc_path.resolve().parent / plain):
        if candidate.is_file():
            return candidate.resolve()
    return None


def load_cross_flow_sibling(sibling_path: Path) -> tuple[dict[str, str], set[str]]:
    """A sibling flow document's own scenario id -> trigger text, and every target id ITS OWN
    Cross-flow scenarios table cites (the 'back' set reciprocity is checked against). Reads
    only the two sections this check needs; the sibling need not otherwise be a valid document."""
    lines = sibling_path.read_text(encoding="utf-8").splitlines()
    _sections, by_name = parse_sections(lines)
    scenarios: dict[str, str] = {}
    scenario_section = by_name.get("Scenarios")
    if scenario_section:
        for _row, values in row_dicts(first_table(lines, scenario_section[0])):
            sid = normalize_symbol(values.get("#", ""))
            if SCENARIO_ID_RE.fullmatch(sid) and sid not in scenarios:
                scenarios[sid] = normalize_symbol(values.get("trigger", ""))
    back_targets: set[str] = set()
    cross_section = by_name.get("Cross-flow scenarios")
    if cross_section:
        for _row, values in row_dicts(first_table(lines, cross_section[0])):
            target = normalize_symbol(values.get("scenario", ""))
            if target:
                back_targets.add(target)
    return scenarios, back_targets


def tone_text(line: str) -> str:
    """Remove code identifiers/paths but retain backticked prose evidence."""

    def replace(match: re.Match[str]) -> str:
        inner = match.group(1)
        if re.search(r"\s", inner):
            return inner
        return ""

    return INLINE_CODE_RE.sub(replace, line)


def mermaid_blocks(lines: Sequence[str]) -> list[MermaidBlock]:
    blocks: list[MermaidBlock] = []
    start: int | None = None
    body: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip().casefold()
        if start is None and stripped == "```mermaid":
            start = index
            body = []
        elif start is not None and stripped == "```":
            blocks.append(MermaidBlock(start=start, end=index, body=tuple(body)))
            start = None
            body = []
        elif start is not None:
            body.append(line)
    return blocks


def diagram_code_tokens(body: Sequence[str], index: CodeIndex) -> set[str]:
    text = "\n".join(body)
    tokens = set(MERMAID_QUALIFIED_RE.findall(text))
    for token in MERMAID_PASCAL_RE.findall(text):
        if token in MERMAID_KEYWORDS:
            continue
        if index.resolves(token):
            tokens.add(token)
    return tokens


def first_nonblank(lines: Sequence[str], start: int, end: int) -> int | None:
    for index in range(start, end):
        if lines[index].strip():
            return index
    return None


def add(
    findings: list[Finding],
    check: str,
    line: int,
    message: str,
) -> None:
    findings.append(Finding(check=check, line=line, message=message))


def validate(
    path: Path, code_root: Path, *, report_crossflow: bool = False
) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    code = CodeIndex.build(code_root)
    findings: list[Finding] = []

    sections, sections_by_name = parse_sections(lines)
    section_names = [section.name for section in sections]
    expected_names = [name for name in PERMITTED_SECTIONS if sections_by_name.get(name)]

    for name in REQUIRED_SECTIONS:
        count = len(sections_by_name.get(name, []))
        if count != 1:
            add(
                findings,
                "sections",
                1,
                f"required section '## {name}' occurs {count} times; expected exactly once",
            )
    for name in OPTIONAL_SECTIONS:
        count = len(sections_by_name.get(name, []))
        if count > 1:
            add(
                findings,
                "sections",
                1,
                f"optional section '## {name}' occurs {count} times; expected at most once",
            )
    unexpected = [name for name in section_names if name not in PERMITTED_SECTIONS]
    for name in unexpected:
        section = sections_by_name[name][0]
        add(
            findings,
            "sections",
            section.heading_line,
            f"unexpected H2 section '## {name}'",
        )
    if (
        not unexpected
        and all(len(sections_by_name.get(name, [])) == 1 for name in REQUIRED_SECTIONS)
        and all(len(sections_by_name.get(name, [])) <= 1 for name in OPTIONAL_SECTIONS)
        and section_names != expected_names
    ):
        add(
            findings,
            "sections",
            1,
            "required sections are not in canonical order",
        )

    canonical_sections = {
        name: occurrences[0]
        for name, occurrences in sections_by_name.items()
        if name in PERMITTED_SECTIONS and occurrences
    }
    provenance_section = canonical_sections.get("Provenance")
    if provenance_section is not None:
        for label in PROVENANCE_REQUIRED_BULLETS:
            bullet = re.compile(r"^- \*\*" + re.escape(label) + r"[^*]*:\*\*(.*)$")
            matched = [
                found
                for found in (
                    bullet.match(lines[i])
                    for i in range(provenance_section.start, provenance_section.end)
                )
                if found is not None
            ]
            if not matched:
                add(
                    findings,
                    "provenance",
                    provenance_section.heading_line,
                    f"Provenance is missing its '**{label}:**' bullet",
                )
            elif not any(found.group(1).strip() for found in matched):
                add(
                    findings,
                    "provenance",
                    provenance_section.heading_line,
                    f"Provenance bullet '**{label}:**' has no content",
                )

    tables: dict[str, MarkdownTable | None] = {
        name: first_table(lines, canonical_sections[name])
        if name in canonical_sections
        else None
        for name in TABLE_HEADERS
    }

    for name, expected_headers in TABLE_HEADERS.items():
        section = canonical_sections.get(name)
        table = tables[name]
        if section is None:
            continue
        allow_none = name == "Cross-flow scenarios"
        if table is None:
            if not (allow_none and section_is_none(lines, section)):
                add(
                    findings,
                    "sections",
                    section.heading_line,
                    f"section '## {name}' needs its canonical table",
                )
            continue
        if len(set(table.headers)) != len(table.headers):
            add(
                findings,
                "sections",
                table.header_line,
                f"section '## {name}' has duplicate headers",
            )
        if set(table.headers) != set(expected_headers) or len(table.headers) != len(
            expected_headers
        ):
            add(
                findings,
                "sections",
                table.header_line,
                f"section '## {name}' headers must be exactly: {' | '.join(expected_headers)}",
            )
        for line_number in table.malformed_rows:
            add(
                findings,
                "sections",
                line_number,
                f"section '## {name}' row has the wrong number of cells",
            )
        if not table.rows:
            add(
                findings,
                "sections",
                table.header_line,
                f"section '## {name}' table is empty",
            )
        for row in table.rows:
            if any(not cell.strip() for cell in row.cells):
                add(
                    findings,
                    "sections",
                    row.line,
                    f"section '## {name}' row has an empty cell",
                )

    scenario_rows: dict[str, tuple[TableRow, dict[str, str]]] = {}
    scenario_symbols: dict[str, set[str]] = {}
    scenario_evidence_files: dict[str, set[str]] = {}
    scenario_table = tables.get("Scenarios")
    for row, values in row_dicts(scenario_table):
        sid = normalize_symbol(values.get("#", ""))
        if not SCENARIO_ID_RE.fullmatch(sid):
            add(findings, "sections", row.line, f"invalid scenario id '{sid}'")
            continue
        if sid in scenario_rows:
            add(findings, "sections", row.line, f"duplicate scenario id '{sid}'")
            continue
        scenario_rows[sid] = (row, values)

        class_name = normalize_symbol(values.get("class", "")).casefold()
        if class_name not in CLASS_VALUES:
            add(
                findings,
                "verdicts",
                row.line,
                f"{sid} has invalid class '{values.get('class', '')}'",
            )
        verdict = normalize_symbol(values.get("verdict", "")).upper()
        if verdict not in VERDICT_VALUES:
            add(
                findings,
                "verdicts",
                row.line,
                f"{sid} has invalid verdict '{values.get('verdict', '')}'",
            )

        symbols = set(parse_path_symbols(values.get("path", "")))
        scenario_symbols[sid] = symbols
        for symbol in sorted(symbols):
            if not SYMBOL_RE.fullmatch(symbol):
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"{sid} path token '{symbol}' is not a qualified symbol",
                )
            elif not code.resolves(symbol):
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"{sid} path symbol '{symbol}' does not resolve",
                )

        evidence = normalize_symbol(values.get("evidence", ""))
        match = EVIDENCE_RE.fullmatch(evidence)
        if not match:
            add(
                findings,
                "evidence",
                row.line,
                f"{sid} evidence needs token and non-empty detail",
            )
        scenario_evidence_files[sid] = extract_file_refs(evidence)

    expansion_headings: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        match = H3_SCENARIO_RE.match(line)
        if match:
            expansion_headings.append((match.group(1), index))
    expansion_ids = {sid for sid, _ in expansion_headings}
    for sid in sorted(expansion_ids):
        occurrences = sum(candidate == sid for candidate, _ in expansion_headings)
        if occurrences > 1:
            add(
                findings,
                "verdicts",
                1,
                f"scenario {sid} has {occurrences} expansions; expected at most one",
            )

    for position, (sid, heading_index) in enumerate(expansion_headings):
        next_expansion = (
            expansion_headings[position + 1][1]
            if position + 1 < len(expansion_headings)
            else len(lines)
        )
        next_h2 = next(
            (
                index
                for index in range(heading_index + 1, len(lines))
                if H2_RE.match(lines[index])
            ),
            len(lines),
        )
        end = min(next_expansion, next_h2)
        expansion = Section(
            name=sid,
            heading_line=heading_index + 1,
            start=heading_index + 1,
            end=end,
        )
        if sid not in scenario_rows:
            add(
                findings,
                "verdicts",
                heading_index + 1,
                f"expansion {sid} has no scenario row",
            )
        expansion_table = first_table(lines, expansion)
        if expansion_table is None:
            add(
                findings,
                "sections",
                heading_index + 1,
                f"expansion {sid} needs its canonical step table",
            )
            continue
        if set(expansion_table.headers) != set(EXPANSION_HEADERS) or len(
            expansion_table.headers
        ) != len(EXPANSION_HEADERS):
            add(
                findings,
                "sections",
                expansion_table.header_line,
                f"expansion headers must be exactly: {' | '.join(EXPANSION_HEADERS)}",
            )
            continue
        if not expansion_table.rows:
            add(
                findings,
                "sections",
                expansion_table.header_line,
                f"expansion {sid} table is empty",
            )
        for expansion_row, values in row_dicts(expansion_table):
            symbols = parse_symbol_list(values.get("symbol", ""))
            for symbol in symbols:
                if EXTERNAL_RE.fullmatch(symbol):
                    continue
                if not SYMBOL_RE.fullmatch(symbol) or not code.resolves(symbol):
                    add(
                        findings,
                        "symbols",
                        expansion_row.line,
                        f"expansion {sid} symbol '{symbol}' does not resolve",
                    )
                elif sid in scenario_symbols and not any(
                    symbol_related(symbol, path_symbol)
                    for path_symbol in scenario_symbols[sid]
                ):
                    add(
                        findings,
                        "symbols",
                        expansion_row.line,
                        f"expansion {sid} symbol '{symbol}' is absent from its scenario path",
                    )
        if sid in scenario_rows:
            verdict = normalize_symbol(scenario_rows[sid][1].get("verdict", "")).upper()
            expansion_text = "\n".join(lines[expansion.start : expansion.end])
            if verdict == "UNKNOWN" and not re.search(
                r"\*\*Unresolved:\*\*\s*\S",
                expansion_text,
            ):
                add(
                    findings,
                    "verdicts",
                    heading_index + 1,
                    f"UNKNOWN expansion {sid} needs a non-empty Unresolved field",
                )
    for sid, (row, values) in scenario_rows.items():
        verdict = normalize_symbol(values.get("verdict", "")).upper()
        if verdict == "UNKNOWN" and sid not in expansion_ids:
            add(
                findings,
                "verdicts",
                row.line,
                f"UNKNOWN scenario {sid} needs a '### {sid} — …' expansion",
            )

    verdict_counts = {verdict: 0 for verdict in VERDICT_VALUES}
    for _, values in scenario_rows.values():
        verdict = normalize_symbol(values.get("verdict", "")).upper()
        if verdict in verdict_counts:
            verdict_counts[verdict] += 1
    distribution_line = next(
        (
            index + 1
            for index, line in enumerate(lines)
            if "Verdict distribution:" in line
        ),
        1,
    )
    distribution_match = re.search(
        r"Verdict distribution[:]\s*PASS\s+(\d+)\s*·\s*UNKNOWN\s+(\d+)\s*·\s*FAIL\s+(\d+)",
        text.replace("**", ""),
        re.IGNORECASE,
    )
    if distribution_match is None:
        add(
            findings,
            "distribution",
            distribution_line,
            "missing canonical 'Verdict distribution: PASS N · UNKNOWN N · FAIL N' line",
        )
    else:
        reported = {
            "PASS": int(distribution_match.group(1)),
            "UNKNOWN": int(distribution_match.group(2)),
            "FAIL": int(distribution_match.group(3)),
        }
        if reported != verdict_counts:
            add(
                findings,
                "distribution",
                distribution_line,
                f"verdict distribution {reported} does not match scenario rows {verdict_counts}",
            )

    all_scenarios = set(scenario_rows)

    # Cross-document id resolution (tasks/TECH-flow-map-validator-cross-doc-resolve.md): a
    # cross-flow row's cell 1 is a scenario id the "owning flow" cell claims belongs to a
    # SIBLING document. Shape-checking (TABLE_HEADERS above) cannot see a wrong id; this opens
    # the sibling and resolves it. Two-pass so a row's "found in another cited sibling" search
    # covers siblings cited later in the same table, not only earlier ones.
    crossflow_rows = row_dicts(tables.get("Cross-flow scenarios"))
    sibling_of_row: dict[int, Path | None] = {}
    sibling_cache: dict[Path, tuple[dict[str, str], set[str]]] = {}
    for row, values in crossflow_rows:
        sibling_path = resolve_cross_flow_sibling(values.get("owning flow", ""), path)
        sibling_of_row[row.line] = sibling_path
        if sibling_path is not None and sibling_path not in sibling_cache:
            sibling_cache[sibling_path] = load_cross_flow_sibling(sibling_path)
    for row, values in crossflow_rows:
        target = normalize_symbol(values.get("scenario", ""))
        owning_raw = values.get("owning flow", "")
        owning_display = normalize_symbol(owning_raw) or owning_raw
        sibling_path = sibling_of_row[row.line]
        if sibling_path is None:
            add(
                findings,
                "crossflow",
                row.line,
                f"cross-flow row cites owning flow '{owning_display}' which does not resolve "
                "to a file (tried the repo root and this document's own directory)",
            )
            continue
        sibling_scenarios, sibling_back = sibling_cache[sibling_path]
        if target not in sibling_scenarios:
            elsewhere = next(
                (
                    other
                    for other, (other_scenarios, _back) in sibling_cache.items()
                    if other != sibling_path and target in other_scenarios
                ),
                None,
            )
            location = (
                f"; it exists instead in '{elsewhere.name}'"
                if elsewhere is not None
                else " (not found in any other flow map this document cites either)"
            )
            add(
                findings,
                "crossflow",
                row.line,
                f"cross-flow row cites '{target}' as owned by '{owning_display}', but that "
                f"document has no such scenario row{location}",
            )
            if report_crossflow:
                print(
                    f"[crossflow-report] {path.name}:{row.line}: {target} -> "
                    f"{owning_display} :: UNRESOLVED{location}"
                )
            continue

        contribution = values.get("this document's contribution", "")
        named_here = {
            match
            for match in SCENARIO_ID_SEARCH_RE.findall(contribution)
            if match in all_scenarios
        }
        if named_here & sibling_back:
            reciprocity = "strict"
        elif sibling_back & all_scenarios:
            reciprocity = "doc-level"
        else:
            reciprocity = "none"
            add(
                findings,
                "crossflow",
                row.line,
                f"cross-flow row to '{target}' ('{owning_display}') has no back-pointer: that "
                "document's own Cross-flow scenarios table names no scenario of this one",
            )
        if report_crossflow:
            print(
                f"[crossflow-report] {path.name}:{row.line}: {target} -> {owning_display} :: "
                f"trigger={sibling_scenarios[target]!r}  reciprocity={reciprocity}"
            )

    runtime_table = tables.get("Runtime applicability")
    runtime_rows = row_dicts(runtime_table)
    runtime_file_scenarios: dict[str, set[str]] = {}
    for row, values in runtime_rows:
        profile = normalize_symbol(values.get("profile", ""))
        reachable_raw = normalize_symbol(values.get("reachable scenarios", ""))
        unreachable_raw = normalize_symbol(values.get("unreachable scenarios", ""))
        evidence = normalize_symbol(values.get("evidence", ""))
        evidence_match = EVIDENCE_RE.fullmatch(evidence)
        if not evidence_match:
            add(
                findings,
                "evidence",
                row.line,
                f"runtime profile '{profile}' evidence needs token and non-empty detail",
            )

        reachable_unknown = reachable_raw.upper() == "UNKNOWN"
        unreachable_unknown = unreachable_raw.upper() == "UNKNOWN"
        if reachable_unknown or unreachable_unknown:
            if not (reachable_unknown and unreachable_unknown):
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"runtime profile '{profile}' must put UNKNOWN in both scenario cells",
                )
            profile_scenarios = all_scenarios
        else:
            reachable = parse_scenario_ids(reachable_raw)
            unreachable = parse_scenario_ids(unreachable_raw)
            overlap = reachable & unreachable
            omitted = all_scenarios - reachable - unreachable
            unknown_refs = (reachable | unreachable) - all_scenarios
            if overlap:
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"runtime profile '{profile}' puts scenarios in both sets: {', '.join(sorted(overlap))}",
                )
            if omitted:
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"runtime profile '{profile}' omits scenarios: {', '.join(sorted(omitted))}",
                )
            if unknown_refs:
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"runtime profile '{profile}' cites unknown scenarios: {', '.join(sorted(unknown_refs))}",
                )
            profile_scenarios = reachable | unreachable
        for file_name in extract_file_refs(evidence):
            runtime_file_scenarios.setdefault(file_name, set()).update(
                profile_scenarios
            )

    invariant_rows: dict[str, tuple[TableRow, dict[str, str]]] = {}
    invariant_order: list[int] = []
    invariant_table = tables.get("Invariants")
    for row, values in row_dicts(invariant_table):
        iid = normalize_symbol(values.get("#", ""))
        symbol = normalize_symbol(values.get("symbol", ""))
        if not INVARIANT_ID_RE.fullmatch(iid):
            add(findings, "index", row.line, f"invalid invariant id '{iid}'")
            continue
        if iid in invariant_rows:
            add(findings, "index", row.line, f"duplicate invariant id '{iid}'")
            continue
        invariant_rows[iid] = (row, values)
        # Invariant ids must ASCEND in reading order. The hazard is not aesthetic: an
        # editor adding the next invariant reads the LAST row to pick the next number,
        # so a row parked out of position makes the last id lower than the maximum and
        # the next append silently mints a duplicate -- in a table the Symbol index,
        # Call graph and Cross-flow sections all reference by id. Found in 3 of 19
        # documents on 2026-09-10 (INV-1 review, FINDING 3), each one append away
        # from a collision. The remedy for a violation is to MOVE the row, never to
        # renumber it, which is why the message says so.
        if invariant_order and int(iid.split("-")[1]) <= invariant_order[-1]:
            add(
                findings,
                "index",
                row.line,
                f"invariant id '{iid}' does not ascend "
                f"(previous row was INV-{invariant_order[-1]:02d}); "
                "reposition the row -- never renumber, ids are cross-referenced",
            )
        invariant_order.append(int(iid.split("-")[1]))
        if not SYMBOL_RE.fullmatch(symbol) or not code.resolves(symbol):
            add(
                findings,
                "symbols",
                row.line,
                f"invariant {iid} symbol '{symbol}' does not resolve",
            )

    call_rows: list[tuple[TableRow, dict[str, str]]] = row_dicts(
        tables.get("Call graph")
    )
    incoming: dict[str, set[str]] = {}
    call_file_scenarios: dict[str, set[str]] = {}
    seen_edges: set[tuple[str, str, str]] = set()
    for row, values in call_rows:
        caller = normalize_symbol(values.get("caller", ""))
        callee = normalize_symbol(values.get("callee", ""))
        site = normalize_repo_path(values.get("site", ""))
        refs_raw = values.get("scenarios", "")
        refs = parse_scenario_ids(refs_raw)

        caller_external = bool(EXTERNAL_RE.fullmatch(caller))
        if not caller_external and (
            not SYMBOL_RE.fullmatch(caller) or not code.resolves(caller)
        ):
            add(
                findings,
                "symbols",
                row.line,
                f"call-graph caller '{caller}' does not resolve",
            )
        if not SYMBOL_RE.fullmatch(callee) or not code.resolves(callee):
            add(
                findings,
                "symbols",
                row.line,
                f"call-graph callee '{callee}' does not resolve",
            )
        if site is None or not repo_file_exists(site):
            add(
                findings,
                "symbols",
                row.line,
                f"call-graph site '{values.get('site', '')}' is not an existing repository file",
            )
        elif not caller_external and site not in code.files_for(caller):
            add(
                findings,
                "symbols",
                row.line,
                f"call-graph site '{site}' does not contain caller '{caller}'",
            )

        if not refs and not is_none_cell(refs_raw):
            add(
                findings,
                "symbols",
                row.line,
                "call-graph scenarios must cite IDs or '_none_'",
            )
        unknown_refs = refs - all_scenarios
        if unknown_refs:
            add(
                findings,
                "symbols",
                row.line,
                f"call-graph edge cites unknown scenarios: {', '.join(sorted(unknown_refs))}",
            )
        for sid in refs & all_scenarios:
            path_symbols = scenario_symbols.get(sid, set())
            if not any(symbol_related(callee, symbol) for symbol in path_symbols):
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"call-graph callee '{callee}' is absent from {sid}'s path",
                )
            if not caller_external and not any(
                symbol_related(caller, symbol) for symbol in path_symbols
            ):
                add(
                    findings,
                    "symbols",
                    row.line,
                    f"call-graph caller '{caller}' is absent from {sid}'s path",
                )

        edge = (caller, callee, site or values.get("site", ""))
        if edge in seen_edges:
            add(
                findings,
                "index",
                row.line,
                f"duplicate direct call edge {caller} → {callee}",
            )
        seen_edges.add(edge)
        incoming.setdefault(callee, set()).add(caller)
        if site is not None:
            call_file_scenarios.setdefault(site, set()).update(refs)

    index_rows: dict[str, tuple[TableRow, dict[str, str]]] = {}
    index_file_by_symbol: dict[str, str] = {}
    for row, values in row_dicts(tables.get("Symbol index")):
        symbol = normalize_symbol(values.get("symbol", ""))
        file_name = normalize_repo_path(values.get("file", ""))
        if symbol in index_rows:
            add(findings, "index", row.line, f"duplicate symbol-index row '{symbol}'")
            continue
        index_rows[symbol] = (row, values)

        if not SYMBOL_RE.fullmatch(symbol) or not code.resolves(symbol):
            add(
                findings,
                "symbols",
                row.line,
                f"indexed symbol '{symbol}' does not resolve",
            )
        if file_name is None or not repo_file_exists(file_name):
            add(
                findings,
                "symbols",
                row.line,
                f"indexed file '{values.get('file', '')}' is not an existing repository file",
            )
        elif code.resolves(symbol) and file_name not in code.files_for(symbol):
            add(
                findings,
                "symbols",
                row.line,
                f"indexed file '{file_name}' does not contain '{symbol}'",
            )
        else:
            if file_name is not None:
                index_file_by_symbol[symbol] = file_name

        declared_scenarios = parse_scenario_ids(values.get("scenarios", ""))
        unknown_refs = declared_scenarios - all_scenarios
        if unknown_refs:
            add(
                findings,
                "symbols",
                row.line,
                f"symbol '{symbol}' cites unknown scenarios: {', '.join(sorted(unknown_refs))}",
            )
        expected_scenarios = {
            sid
            for sid, symbols in scenario_symbols.items()
            if any(symbol_related(symbol, candidate) for candidate in symbols)
        }
        if declared_scenarios != expected_scenarios:
            add(
                findings,
                "index",
                row.line,
                f"symbol '{symbol}' scenarios {sorted(declared_scenarios)} do not match paths {sorted(expected_scenarios)}",
            )

        invariant_refs = parse_invariant_ids(values.get("invariants", ""))
        unknown_invariants = invariant_refs - set(invariant_rows)
        if unknown_invariants:
            add(
                findings,
                "index",
                row.line,
                f"symbol '{symbol}' cites unknown invariants: {', '.join(sorted(unknown_invariants))}",
            )

        called_by_raw = values.get("called by", "")
        declared_callers = set(parse_symbol_list(called_by_raw))
        for caller in sorted(declared_callers):
            if not EXTERNAL_RE.fullmatch(caller) and (
                not SYMBOL_RE.fullmatch(caller) or not code.resolves(caller)
            ):
                add(
                    findings,
                    "index",
                    row.line,
                    f"called-by symbol '{caller}' does not resolve",
                )
        expected_callers = {
            caller
            for callee, callers in incoming.items()
            if symbol_related(symbol, callee)
            for caller in callers
        }
        if declared_callers != expected_callers:
            add(
                findings,
                "index",
                row.line,
                f"symbol '{symbol}' called-by {sorted(declared_callers)} does not match incoming edges {sorted(expected_callers)}",
            )
        if not declared_callers and code.is_callable(symbol):
            add(
                findings,
                "index",
                row.line,
                f"callable '{symbol}' needs an incoming call edge or explicit external caller",
            )

    for sid, symbols in scenario_symbols.items():
        for symbol in sorted(symbols):
            if not any(symbol_related(symbol, indexed) for indexed in index_rows):
                line = scenario_rows[sid][0].line
                add(
                    findings,
                    "index",
                    line,
                    f"{sid} path symbol '{symbol}' is missing from the symbol index",
                )

    for iid, (row, values) in invariant_rows.items():
        symbol = normalize_symbol(values.get("symbol", ""))
        matching = [
            indexed for indexed in index_rows if symbol_related(symbol, indexed)
        ]
        if not matching:
            add(
                findings,
                "index",
                row.line,
                f"invariant {iid} symbol '{symbol}' is missing from the symbol index",
            )
        elif not any(
            iid in parse_invariant_ids(index_rows[indexed][1].get("invariants", ""))
            for indexed in matching
        ):
            add(
                findings,
                "index",
                row.line,
                f"invariant {iid} is not linked back from the symbol index",
            )

    diagram_section = canonical_sections.get("Diagrams")
    blocks = mermaid_blocks(lines)
    diagram_blocks = [
        block
        for block in blocks
        if diagram_section is not None
        and diagram_section.start <= block.start < diagram_section.end
    ]
    for block in blocks:
        if block not in diagram_blocks:
            add(
                findings,
                "sections",
                block.start + 1,
                "Mermaid blocks belong only under '## Diagrams'",
            )
    if (
        diagram_section is not None
        and not diagram_blocks
        and not section_is_none(lines, diagram_section)
    ):
        add(
            findings,
            "sections",
            diagram_section.heading_line,
            "Diagrams must contain Mermaid or '_none_'",
        )

    authoritative_symbols = set(index_rows)
    for symbols in scenario_symbols.values():
        authoritative_symbols.update(symbols)
    for block in diagram_blocks:
        for token in sorted(diagram_code_tokens(block.body, code)):
            if not any(
                symbol_related(token, symbol) for symbol in authoritative_symbols
            ):
                add(
                    findings,
                    "diagram",
                    block.start + 1,
                    f"diagram code symbol '{token}' is absent from scenarios and symbol index",
                )

    legend_file_scenarios: dict[str, set[str]] = {}
    for block in diagram_blocks:
        legend_heading = first_nonblank(
            lines, block.end + 1, diagram_section.end if diagram_section else len(lines)
        )
        # A retained diagram no longer needs an adjacent legend (improvement-plan item 2):
        # with no legend heading there is nothing to validate, so skip silently. A legend
        # the author DOES write is still checked in full below.
        if legend_heading is None or not lines[legend_heading].startswith(
            "### Legend —"
        ):
            continue
        table_start = first_nonblank(
            lines,
            legend_heading + 1,
            diagram_section.end if diagram_section else len(lines),
        )
        legend_table = (
            parse_table_at(
                lines,
                table_start,
                diagram_section.end if diagram_section else len(lines),
            )
            if table_start is not None
            else None
        )
        if legend_table is None:
            continue
        if set(legend_table.headers) != set(LEGEND_HEADERS) or len(
            legend_table.headers
        ) != len(LEGEND_HEADERS):
            add(
                findings,
                "legends",
                legend_table.header_line,
                f"legend headers must be exactly: {' | '.join(LEGEND_HEADERS)}",
            )
            continue
        if not legend_table.rows:
            add(findings, "legends", legend_table.header_line, "legend table is empty")
            continue

        legend_symbols: set[str] = set()
        for legend_row, values in row_dicts(legend_table):
            symbols = parse_symbol_list(values.get("symbol", ""))
            refs = parse_scenario_ids(values.get("scenarios", ""))
            unknown_refs = refs - all_scenarios
            if unknown_refs:
                add(
                    findings,
                    "legends",
                    legend_row.line,
                    f"legend cites unknown scenarios: {', '.join(sorted(unknown_refs))}",
                )
            if not refs:
                add(
                    findings,
                    "legends",
                    legend_row.line,
                    "legend row must cite a local scenario",
                )
            file_raw = values.get("file", "")
            for symbol in symbols:
                legend_symbols.add(symbol)
                if EXTERNAL_RE.fullmatch(symbol):
                    if not is_none_cell(file_raw):
                        add(
                            findings,
                            "legends",
                            legend_row.line,
                            "external legend symbols use '—' for file",
                        )
                    continue
                if not SYMBOL_RE.fullmatch(symbol) or not code.resolves(symbol):
                    add(
                        findings,
                        "symbols",
                        legend_row.line,
                        f"legend symbol '{symbol}' does not resolve",
                    )
                    continue
                file_name = normalize_repo_path(file_raw)
                if file_name is None or not repo_file_exists(file_name):
                    add(
                        findings,
                        "symbols",
                        legend_row.line,
                        f"legend file '{file_raw}' is not an existing repository file",
                    )
                elif file_name not in code.files_for(symbol):
                    add(
                        findings,
                        "symbols",
                        legend_row.line,
                        f"legend file '{file_name}' does not contain '{symbol}'",
                    )
                else:
                    legend_file_scenarios.setdefault(file_name, set()).update(refs)
                if refs and not any(
                    any(
                        symbol_related(symbol, path_symbol)
                        for path_symbol in scenario_symbols.get(sid, set())
                    )
                    for sid in refs & all_scenarios
                ):
                    add(
                        findings,
                        "legends",
                        legend_row.line,
                        f"legend symbol '{symbol}' maps to no cited scenario path",
                    )

        for token in sorted(diagram_code_tokens(block.body, code)):
            if not any(symbol_related(token, symbol) for symbol in legend_symbols):
                add(
                    findings,
                    "legends",
                    block.start + 1,
                    f"diagram symbol '{token}' is missing from its legend",
                )

    expected_coverage: dict[str, set[str]] = {}

    def cite_file(file_name: str, refs: Iterable[str]) -> None:
        expected_coverage.setdefault(file_name, set()).update(refs)

    for symbol, file_name in index_file_by_symbol.items():
        refs = {
            sid
            for sid, symbols in scenario_symbols.items()
            if any(symbol_related(symbol, candidate) for candidate in symbols)
        }
        cite_file(file_name, refs)
    for file_name, refs in call_file_scenarios.items():
        cite_file(file_name, refs)
    for sid, file_names in scenario_evidence_files.items():
        for file_name in file_names:
            cite_file(file_name, {sid})
    for file_name, refs in runtime_file_scenarios.items():
        cite_file(file_name, refs)
    for file_name, refs in legend_file_scenarios.items():
        cite_file(file_name, refs)

    coverage_rows: dict[str, tuple[TableRow, dict[str, str]]] = {}
    for row, values in row_dicts(tables.get("Coverage")):
        file_name = normalize_repo_path(values.get("file", ""))
        if file_name is None:
            add(
                findings,
                "symbols",
                row.line,
                f"coverage file '{values.get('file', '')}' is not repository-relative",
            )
            continue
        if file_name in coverage_rows:
            add(findings, "index", row.line, f"duplicate coverage row '{file_name}'")
            continue
        coverage_rows[file_name] = (row, values)
        if not repo_file_exists(file_name):
            add(
                findings,
                "symbols",
                row.line,
                f"coverage file '{file_name}' does not exist",
            )
        declared = parse_scenario_ids(values.get("scenarios", ""))
        if not declared and not is_none_cell(values.get("scenarios", "")):
            add(
                findings,
                "symbols",
                row.line,
                "coverage scenarios must cite IDs or '_none_'",
            )
        unknown_refs = declared - all_scenarios
        if unknown_refs:
            add(
                findings,
                "symbols",
                row.line,
                f"coverage row cites unknown scenarios: {', '.join(sorted(unknown_refs))}",
            )
        expected = expected_coverage.get(file_name, set())
        if declared != expected:
            add(
                findings,
                "index",
                row.line,
                f"coverage for '{file_name}' {sorted(declared)} does not match cited use {sorted(expected)}",
            )

    for file_name, refs in sorted(expected_coverage.items()):
        if file_name not in coverage_rows:
            add(
                findings,
                "symbols",
                1,
                f"cited file '{file_name}' is missing from Coverage (scenarios: {', '.join(sorted(refs)) or '_none_'})",
            )

    unknown_scenarios = {
        sid
        for sid, (_, values) in scenario_rows.items()
        if normalize_symbol(values.get("verdict", "")).upper() == "UNKNOWN"
    }
    allowed_uncertainty_lines = {
        row.line for sid, (row, _) in scenario_rows.items() if sid in unknown_scenarios
    }
    for row, values in runtime_rows:
        if (
            normalize_symbol(values.get("reachable scenarios", "")).upper() == "UNKNOWN"
            and normalize_symbol(values.get("unreachable scenarios", "")).upper()
            == "UNKNOWN"
        ):
            allowed_uncertainty_lines.add(row.line)

    current_expansion: str | None = None
    in_fence = False
    invariant_lines = {row.line for row, _ in row_dicts(invariant_table)}
    for index, line in enumerate(lines):
        line_number = index + 1
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        h3_match = H3_SCENARIO_RE.match(line)
        if h3_match:
            current_expansion = h3_match.group(1)
        elif line.startswith("##") or (line.startswith("###") and h3_match is None):
            current_expansion = None
        allowed_uncertainty = (
            line_number in allowed_uncertainty_lines
            or current_expansion in unknown_scenarios
        )
        searchable = tone_text(line)
        for label, pattern in BANNED_TONE_PATTERNS:
            if pattern.search(searchable):
                add(
                    findings,
                    "tone",
                    line_number,
                    f"banned tone phrase '{label}'",
                )
        if not allowed_uncertainty:
            for label, pattern in UNCERTAINTY_PATTERNS:
                if pattern.search(searchable):
                    add(
                        findings,
                        "tone",
                        line_number,
                        f"uncertainty phrase '{label}' needs an UNKNOWN context",
                    )
        if SHOULD_RE.search(searchable) and line_number not in invariant_lines:
            add(
                findings,
                "tone",
                line_number,
                "'should' is allowed only in an invariant row with a consequence",
            )

    return sorted(
        findings,
        key=lambda finding: (
            finding.line,
            CHECKS.index(finding.check),
            finding.message,
        ),
    )


def render_findings(
    path: Path, findings: Sequence[Finding], selected: str | None
) -> int:
    visible = [
        finding for finding in findings if selected is None or finding.check == selected
    ]
    for finding in visible:
        try:
            display = path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            display = str(path)
        print(f"[{finding.check}] {display}:{finding.line}: {finding.message}")
    return len(visible)


def _run_probes(project: Path) -> int:
    fixtures = project / "scripts/fixtures/flow_map"
    conformant = fixtures / "conformant.md"
    failures = 0
    for case in PROBE_CASES:
        checker_parts = [
            f'"{sys.executable}"',
            f'"{Path(__file__).resolve()}"',
            '"{file}"',
        ]
        if case.check is not None:
            checker_parts.extend(("--check", case.check))
        checker_parts.extend(("--project-root", f'"{project}"', "--code-root", "src"))
        checker_cmd = " ".join(checker_parts)
        command = [
            sys.executable,
            str(PROBE_CHECKER),
            "--cmd",
            checker_cmd,
            "--positive",
            str(fixtures / case.positive),
            "--negative",
            str(conformant),
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
        print(f"flow-map probe manifest: {failures} probe(s) failed", file=sys.stderr)
        return 1
    print(f"flow-map probe manifest: PASS ({len(PROBE_CASES)} exact probe pairs)")
    return 0


def run_probes() -> int:
    with probe_project() as project:
        return _run_probes(project)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", nargs="?", type=Path)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--code-root", type=Path)
    parser.add_argument("--check", choices=CHECKS)
    parser.add_argument(
        "--probe-stamps",
        action="store_true",
        help="execute every exact positive/negative probe pair",
    )
    parser.add_argument(
        "--report-crossflow",
        action="store_true",
        help=(
            "print every cross-flow row's resolved trigger text and reciprocity class "
            "(strict/doc-level/none); findings are unchanged, this only adds diagnostic lines"
        ),
    )
    args = parser.parse_args(argv)
    if not args.probe_stamps and args.document is None:
        parser.error("document is required unless --probe-stamps is used")
    if args.probe_stamps and args.document is not None:
        parser.error("document cannot be combined with --probe-stamps")
    return args


def configure(project_root: Path, code_root: Path | None = None) -> None:
    """Select consumer paths without changing immutable plugin resources."""
    global REPO_ROOT, DEFAULT_CODE_ROOT
    REPO_ROOT = project_root.resolve()
    DEFAULT_CODE_ROOT = (code_root or REPO_ROOT).resolve()
    global FILE_REF_RE
    relative = DEFAULT_CODE_ROOT.relative_to(REPO_ROOT)
    # Limit references to the declared source tree and documentation surfaces.
    # An unrelated package-cache path in prose is not a project Coverage claim.
    prefixes = {"tests", "scripts", "docs", ".ai", ".specs"}
    if relative.parts:
        prefixes.add(relative.parts[0])
        prefix = "(?:" + "|".join(re.escape(p) for p in sorted(prefixes)) + ")/"
    else:
        prefix = r"(?:[A-Za-z_.][A-Za-z0-9_.-]*/)+"
    FILE_REF_RE = re.compile(
        r"(?<![\w.-])("
        + prefix
        + r"[A-Za-z0-9_./-]+\.(?:py|md|yaml|yml|json|toml)"
        + r"|(?:cloudbuild|docker-compose)[A-Za-z0-9_.-]*\.(?:yaml|yml)"
        + r")(?![\w.-])"
    )


def main(argv: Sequence[str] | None = None) -> int:
    # Findings carry non-ASCII (e.g. the '### Legend — …' heading). On a Windows console
    # whose code page lacks them, print() would raise and abort the run mid-way, so the
    # probe counter would see a traceback instead of findings. Force UTF-8 out.
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

    if args.probe_stamps:
        return run_probes()
    assert args.document is not None
    if not args.document.is_file():
        print(f"flow-map document not found: {args.document}", file=sys.stderr)
        return 2
    if not args.code_root.is_dir():
        print(f"code root not found: {args.code_root}", file=sys.stderr)
        return 2
    findings = validate(
        args.document, args.code_root, report_crossflow=args.report_crossflow
    )
    return 1 if render_findings(args.document, findings, args.check) else 0


if __name__ == "__main__":
    raise SystemExit(main())
