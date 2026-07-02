"""Command-line interface: lemmi-ai-kit install | list | diff."""

from __future__ import annotations

import argparse
from pathlib import Path

from lemmi_ai_kit import __version__, installer
from lemmi_ai_kit.manifest import (
    DEFAULT_PROFILES,
    PROFILES,
    Manifest,
    ManifestError,
    load_manifest,
    normalize_profiles,
)


def _add_profile_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "profile(s) to include (repeatable or comma-separated); "
            f"known: {', '.join(PROFILES)}; default: {', '.join(DEFAULT_PROFILES)}"
        ),
    )
    parser.add_argument(
        "--all", action="store_true", help="include every profile, including extras"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lemmi-ai-kit",
        description="Deploy Lemmi's shared AI configuration (Claude Code skills, AGENTS.md/CLAUDE.md, .ai scaffolding) into a project.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    install_p = sub.add_parser(
        "install", help="install the AI configuration into a project"
    )
    install_p.add_argument(
        "target",
        nargs="?",
        default=".",
        help="project root (default: current directory)",
    )
    _add_profile_args(install_p)
    install_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite locally modified managed files (skills, .ai/templates)",
    )
    install_p.add_argument(
        "--reseed",
        action="store_true",
        help="also overwrite seed files (AGENTS.md, CLAUDE.md, .ai state logs) — destructive to project customizations",
    )
    install_p.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing",
    )

    list_p = sub.add_parser("list", help="list the skills shipped by the kit")
    _add_profile_args(list_p)

    diff_p = sub.add_parser(
        "diff",
        help="show drift between a project and the kit (exit 1 when drift exists)",
    )
    diff_p.add_argument(
        "target",
        nargs="?",
        default=".",
        help="project root (default: current directory)",
    )
    _add_profile_args(diff_p)

    return parser


def _cmd_install(
    args: argparse.Namespace, manifest: Manifest, profiles: tuple[str, ...]
) -> int:
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"error: target is not a directory: {target}")
        return 2
    dry_run: bool = args.dry_run
    report = installer.install(
        target,
        manifest,
        profiles,
        force=args.force,
        reseed=args.reseed,
        dry_run=dry_run,
    )

    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}lemmi-ai-kit {__version__} -> {target}")
    print(f"{prefix}profiles: {', '.join(profiles)}")
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


def _cmd_list(manifest: Manifest, profiles: tuple[str, ...]) -> int:
    selected = manifest.for_profiles(profiles)
    width_name = max(len(s.name) for s in selected)
    width_profile = max(len(s.profile) for s in selected)
    for entry in selected:
        print(
            f"{entry.name:<{width_name}}  {entry.profile:<{width_profile}}  {entry.invocation:<8}  {entry.summary}"
        )
    print(f"\n{len(selected)} skill(s) in profiles: {', '.join(profiles)}")
    return 0


def _cmd_diff(
    args: argparse.Namespace, manifest: Manifest, profiles: tuple[str, ...]
) -> int:
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"error: target is not a directory: {target}")
        return 2
    entries = installer.diff(target, manifest, profiles)
    drift = [e for e in entries if e.state != "unchanged"]
    if not drift:
        print(
            f"{target}: in sync with lemmi-ai-kit {__version__} ({len(entries)} files)"
        )
        return 0
    print(f"{target}: {len(drift)} file(s) differ from lemmi-ai-kit {__version__}")
    for entry in drift:
        print(f"  {entry.state:<9} {entry.kind:<8} {entry.relative}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        profiles = normalize_profiles(args.profile, include_all=args.all)
        manifest = load_manifest()
    except (ManifestError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    if args.command == "install":
        return _cmd_install(args, manifest, profiles)
    if args.command == "list":
        return _cmd_list(manifest, profiles)
    if args.command == "diff":
        return _cmd_diff(args, manifest, profiles)
    parser.error(f"unknown command: {args.command}")
