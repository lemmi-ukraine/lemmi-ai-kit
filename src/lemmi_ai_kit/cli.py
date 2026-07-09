"""Support-scripting CLI for the lemmi-ai-kit Claude Code / Codex plugin.

The plugin is the only installation mechanism for the kit's skills. This CLI is
NOT a user-facing installer — it is the deterministic helper the plugin's
`kit-setup` skill shells out to (and a dev tool for this repo):

- `scaffold` — place the project-owned files (AGENTS.md, CLAUDE.md, .ai/) into a
  project, with the CLAUDE.md skill index rendered from the shipped catalog.
- `list` — print the skill catalog (name, profile, invocation, summary).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lemmi_ai_kit import __version__, scaffold
from lemmi_ai_kit.manifest import ManifestError, load_manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lemmi-ai-kit",
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

    return parser


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
    except (ManifestError, OSError) as exc:
        print(f"error: {exc}")
        return 2
    parser.error(f"unknown command: {args.command}")
