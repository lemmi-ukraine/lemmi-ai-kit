"""Support-scripting CLI for the lemmi-ai-kit Claude Code / Codex plugin.

The plugin is the only installation mechanism for the kit's skills. This CLI is
NOT a user-facing installer — it is the deterministic helper the plugin's
`kit-setup` skill shells out to (and a dev tool for this repo):

- `scaffold` — place the project-owned files (AGENTS.md, CLAUDE.md, .ai/) into a
  project, with the CLAUDE.md skill index rendered from the shipped catalog.
- `list` — print the skill catalog (name, profile, invocation, summary).
- `lint` — validate the project's `.ai/` pipeline data files.
- `audit-skills` — audit a project's `.claude/skills/` against the mechanical
  subset of the skill-review checklist.

The last two exist because a skill cannot address a *sibling* skill's script
portably; see `checks.py` for why that made them subcommands instead. Both are
read-only and write nothing, so they are safe to run from parallel sessions.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from lemmi_ai_kit import __version__, checks, scaffold
from lemmi_ai_kit.manifest import ManifestError, assets_root, load_manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lemmi_ai_kit",
        description=(
            "Support scripts for the lemmi-ai-kit Claude Code / Codex plugin. "
            "Install via Claude: /plugin marketplace add lemmi-ukraine/lemmi-ai-kit — "
            "or Codex: codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit"
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scaffold_p = sub.add_parser(
        "scaffold",
        help="place the project-owned AI config files (AGENTS.md, CLAUDE.md, .ai/) into a project",
    )
    scaffold_p.add_argument(
        "target",
        nargs="?",
        default=".",
        help="project root (default: current directory)",
    )
    scaffold_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite locally modified managed files (.ai/templates)",
    )
    scaffold_p.add_argument(
        "--reseed",
        action="store_true",
        help="also overwrite seed files (AGENTS.md, CLAUDE.md, .ai state logs) — destructive to project customizations",
    )
    scaffold_p.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing",
    )

    sub.add_parser("list", help="list the skills shipped by the plugin")

    lint_p = sub.add_parser(
        "lint",
        help="validate the project's .ai/ pipeline data files",
        description=(
            "Structural and format lint for the .ai/ data files. Structural checks "
            "(heading order, append damage) always run file-wide; --since gates only "
            "the per-entry format checks."
        ),
    )
    lint_p.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=("all", *checks.LINT_TARGETS),
        help="which data file to lint (default: all)",
    )
    lint_p.add_argument(
        "--project",
        metavar="DIR",
        help="project root (default: nearest ancestor of the working directory with .ai/ or .git/)",
    )
    lint_p.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        help="apply per-entry format checks only to entries dated on or after this (default: every entry)",
    )
    lint_p.add_argument(
        "--list-entries",
        action="store_true",
        help="print the entry inventory (line, title, per-section counts) instead of linting",
    )
    lint_p.add_argument(
        "--resolve-anchors",
        action="store_true",
        help="also check that hand-off 'Durable anchors' resolve in git (shells out per anchor; reported as notes)",
    )

    audit_p = sub.add_parser(
        "audit-skills",
        help="audit a project's .claude/skills/ against the review checklist",
        description=(
            "The mechanical subset of the skill-review checklist. Findings are review "
            "input, not process failures, so the default exit code is 0 -- use --fail-on "
            "to gate on a severity."
        ),
    )
    audit_p.add_argument(
        "--project",
        metavar="DIR",
        help="project root (default: nearest ancestor of the working directory with .ai/ or .git/)",
    )
    audit_p.add_argument(
        "--skills-dir",
        metavar="DIR",
        help=(
            "directory of skills to audit (default: <project>/.claude/skills, or the "
            "kit's own bundled skills tree when that is absent and the project is a "
            "checkout of this repo)"
        ),
    )
    audit_p.add_argument(
        "--fail-on",
        choices=("none", "blocker", "major", "minor"),
        default="none",
        help="exit 1 when a finding at this severity or worse is present (default: none)",
    )

    return parser


def _project_root(raw: str | None) -> Path:
    """The project these checks run against: an explicit --project, or discovery from cwd."""
    if raw is None:
        return checks.find_project_root()
    root = Path(raw).resolve()
    if not root.is_dir():
        raise _UsageError(f"--project is not a directory: {root}")
    return root


def _bundled_skills_dir(root: Path) -> Path | None:
    """The kit's own shipped skills tree, but only when `root` is a checkout of this repo.

    `None` when the bundled assets sit outside `root`. In an adopter's project the kit is
    installed under site-packages or a plugin cache, and auditing *our* fleet instead of
    theirs would answer a question they did not ask -- so that case keeps the "nothing to
    audit" note rather than silently changing target.
    """
    try:
        bundled = (assets_root() / "skills").resolve()
    except OSError:
        return None
    if not bundled.is_dir():
        return None
    return bundled if bundled.is_relative_to(root.resolve()) else None


def _parse_since(raw: str | None) -> date | None:
    if raw is None:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        raise _UsageError(f"--since must be YYYY-MM-DD, got {raw!r}") from None


class _UsageError(ValueError):
    """A bad flag combination or value: reported on stdout, exit 2."""


def _cmd_lint(args: argparse.Namespace) -> int:
    root = _project_root(args.project)
    since = _parse_since(args.since)
    target: str = args.target
    inventory_only: bool = args.list_entries

    if inventory_only and target == "handoffs":
        raise _UsageError("--list-entries needs a data file target, not 'handoffs'")

    targets = checks.LINT_TARGETS if target == "all" else (target,)
    total = 0
    for name in targets:
        if name == "handoffs":
            if inventory_only:
                continue
            findings, scanned = checks.lint_handoff_dir(
                root, resolve_anchors=args.resolve_anchors
            )
            total += _report_lint(name, findings, note=f"{scanned} file(s)")
            continue

        path = checks.target_path(name, root)
        where = checks.display_path(path, root)
        if not path.is_file():
            # An explicitly named missing file is a user error. Under `all` it is not:
            # a project may not have scaffolded every log yet, and nothing to lint is
            # not a lint failure.
            if target != "all":
                raise _UsageError(
                    f"no such file: {where} (run `scaffold` to create it)"
                )
            print(checks.ascii_safe(f"{where}: not found, skipped"))
            continue

        text = checks.read_text(path)
        if inventory_only:
            for line in checks.inventory(text, where):
                print(checks.ascii_safe(line))
            continue
        total += _report_lint(name, checks.lint_file(name, text, where, since))

    if inventory_only:
        return 0
    print(
        checks.ascii_safe(
            f"LINT {'PASSED' if total == 0 else 'FAILED'} ({total} finding(s))"
        )
    )
    return 0 if total == 0 else 1


def _report_lint(
    target: str, findings: list[checks.LintFinding], note: str | None = None
) -> int:
    """Print one target's findings; return how many of them actually fail the run."""
    for finding in findings:
        prefix = "" if finding.note else "ERROR "
        print(
            checks.ascii_safe(
                f"{finding.where}:{finding.line}: {prefix}{finding.message}"
            )
        )
    failing = sum(1 for finding in findings if not finding.note)
    suffix = f", {note}" if note else ""
    print(checks.ascii_safe(f"--- {target}: {failing} finding(s){suffix} ---"))
    return failing


def _cmd_audit_skills(args: argparse.Namespace) -> int:
    root = _project_root(args.project)
    if args.skills_dir is not None:
        skills_dir = Path(args.skills_dir).resolve()
    else:
        skills_dir = root / ".claude" / "skills"
        if not skills_dir.is_dir():
            # A gate that scans nothing reports green forever, and a green detector
            # nobody can fail is worse than no detector because it is trusted. When
            # this project IS the kit, audit the fleet it ships so `--fail-on` has
            # something to fail on.
            bundled = _bundled_skills_dir(root)
            if bundled is not None:
                skills_dir = bundled

    findings = checks.audit_skills(
        skills_dir,
        claude_md=root / "CLAUDE.md",
        shipped=checks.shipped_skill_names(),
    )

    print(
        checks.ascii_safe(f"skill fleet audit: {checks.display_path(skills_dir, root)}")
    )
    counted = 0
    for severity in checks.SEVERITIES:
        at_severity = [f for f in findings if f.severity == severity]
        if not at_severity:
            continue
        if severity not in ("NOTE", "INFO"):
            counted += len(at_severity)
        print(checks.ascii_safe(f"\n{severity} ({len(at_severity)})"))
        for finding in at_severity:
            print(checks.ascii_safe(f"  - {finding.skill}: {finding.message}"))

    threshold: str = args.fail_on
    failed = _fails_threshold(findings, threshold)
    verdict = (
        f"exit 1 (--fail-on {threshold})"
        if failed
        else "Findings are review input, not failures"
    )
    print(checks.ascii_safe(f"\n{counted} finding(s). {verdict}."))
    return 1 if failed else 0


def _fails_threshold(findings: list[checks.AuditFinding], threshold: str) -> bool:
    """Is the worst finding at or above the `--fail-on` severity?"""
    if threshold == "none":
        return False
    worst = checks.worst_severity(findings)
    if worst is None:
        return False
    return checks.SEVERITIES.index(worst) <= checks.SEVERITIES.index(threshold.upper())


def _cmd_scaffold(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"error: target is not a directory: {target}")
        return 2
    dry_run: bool = args.dry_run
    manifest = load_manifest()
    report = scaffold.scaffold(
        target,
        manifest,
        force=args.force,
        reseed=args.reseed,
        dry_run=dry_run,
    )

    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}lemmi-ai-kit {__version__} scaffold -> {target}")
    print(
        f"{prefix}written: {report.count('written')}  seeded: {report.count('seeded')}  "
        f"overwritten: {report.count('overwritten')}  unchanged: {report.count('unchanged')}"
    )
    skipped_managed = report.by_action("skipped-exists")
    if skipped_managed:
        print(
            f"\n{prefix}skipped {len(skipped_managed)} locally modified managed file(s) (use --force to overwrite):"
        )
        for rel in skipped_managed:
            print(f"  - {rel}")
    skipped_seeds = report.by_action("skipped-seed")
    if skipped_seeds:
        print(
            f"\n{prefix}kept {len(skipped_seeds)} project-owned seed file(s) (use --reseed to overwrite):"
        )
        for rel in skipped_seeds:
            print(f"  - {rel}")
    return 0


def _cmd_list() -> int:
    manifest = load_manifest()
    skills = manifest.skills
    width_name = max(len(s.name) for s in skills)
    width_profile = max(len(s.profile) for s in skills)
    for entry in skills:
        print(
            f"{entry.name:<{width_name}}  {entry.profile:<{width_profile}}  {entry.invocation:<8}  {entry.summary}"
        )
    print(f"\n{len(skills)} skill(s) shipped by the plugin")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "scaffold":
            return _cmd_scaffold(args)
        if args.command == "list":
            return _cmd_list()
        if args.command == "lint":
            return _cmd_lint(args)
        if args.command == "audit-skills":
            return _cmd_audit_skills(args)
    except (ManifestError, OSError, _UsageError) as exc:
        print(f"error: {exc}")
        return 2
    parser.error(f"unknown command: {args.command}")
