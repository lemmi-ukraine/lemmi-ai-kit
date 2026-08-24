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
- `publish-check` — the pre-publish guard: refuse to publish while the plugin
  payload carries files git does not track. Maintainer-facing, not adopter-facing.
- `new-pack` — scaffold a new plugin pack from the repo's pack template.
  Maintainer-facing: it runs in a checkout, and it registers nothing.

`lint` and `audit-skills` exist because a skill cannot address a *sibling* skill's
script portably; see `checks.py` for why that made them subcommands instead. All
three are read-only and write nothing, so they are safe to run from parallel
sessions.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from datetime import date, datetime
from pathlib import Path
from typing import cast

from lemmi_ai_kit import __version__, checks, publish, scaffold
from lemmi_ai_kit.manifest import (
    PACKS,
    ManifestError,
    assets_root,
    load_manifest,
    repository_root,
    skills_root,
)


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

    publish_p = sub.add_parser(
        "publish-check",
        help="pre-publish guard: refuse to publish while the payload carries untracked or ignored files",
        description=(
            "`plugin install` copies the WORKING tree, not the git tree, so anything "
            "sitting under a pack directory ships to whoever installs. Exit 0 clean, "
            "1 blocked, 2 could not be measured. There is deliberately no flag to "
            "excuse a path: the tree must be EMPTY, not 'only my files'."
        ),
    )
    publish_p.add_argument(
        "--repo",
        metavar="DIR",
        help="checkout to inspect (default: nearest ancestor of the working directory with .git/)",
    )

    new_pack_p = sub.add_parser(
        "new-pack",
        help="scaffold a new plugin pack from plugins/_template",
        description=(
            "Copies the pack template into `plugins/<name>/`, substituting the "
            "placeholders and renaming the example skill. Maintainer-facing: it runs "
            "in a checkout of the kit. It deliberately REGISTERS NOTHING -- the "
            "marketplace manifests, the pack enum and the asset manifest are reviewed "
            "chokepoints, and it prints them as a checklist instead of editing them."
        ),
    )
    new_pack_p.add_argument(
        "name",
        help="pack directory name, e.g. `rust` (becomes plugins/<name>/)",
    )
    new_pack_p.add_argument(
        "--skill",
        metavar="NAME",
        help="name for the pack's first skill (default: <name>-conventions)",
    )
    new_pack_p.add_argument(
        "--plugin-name",
        metavar="NAME",
        help="plugin id in both marketplaces (default: lemmi-ai-kit-<name>)",
    )
    new_pack_p.add_argument(
        "--display-name",
        metavar="TEXT",
        help="human-readable name (default: derived from the plugin name)",
    )
    new_pack_p.add_argument(
        "--description",
        metavar="TEXT",
        help="one-line description for both plugin manifests",
    )
    new_pack_p.add_argument(
        "--author",
        metavar="NAME",
        help=(
            "author credited in both plugin manifests (default: the package author "
            "from pyproject.toml). REQUIRED, with --plugin-name, for a pack this "
            "repo's owner did not write: the author field is a provenance label"
        ),
    )
    new_pack_p.add_argument(
        "--author-url",
        metavar="URL",
        help="author URL (default: the repository URL with its last segment dropped)",
    )
    new_pack_p.add_argument(
        "--repo",
        metavar="DIR",
        help="checkout to write into (default: nearest ancestor of the working directory with .git/)",
    )
    new_pack_p.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be written without writing",
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


def _bundled_skills_dirs(root: Path) -> tuple[Path, ...]:
    """The kit's own shipped skill roots, but only when `root` is this repo.

    Empty when the bundled assets sit outside `root`. In an adopter's project the kit is
    installed under site-packages or a plugin cache, and auditing *our* fleet instead of
    theirs would answer a question they did not ask -- so that case keeps the "nothing to
    audit" note rather than silently changing target.
    """
    try:
        checkout = repository_root().resolve()
        resolved_root = root.resolve()
    except OSError:
        return ()
    if checkout != resolved_root:
        return ()
    return tuple(path for pack in PACKS if (path := skills_root(pack)).is_dir())


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
        skills_dirs = (Path(args.skills_dir).resolve(),)
    else:
        skills_dir = root / ".claude" / "skills"
        if not skills_dir.is_dir():
            # A gate that scans nothing reports green forever, and a green detector
            # nobody can fail is worse than no detector because it is trusted. When
            # this project IS the kit, audit the fleet it ships so `--fail-on` has
            # something to fail on.
            bundled = _bundled_skills_dirs(root)
            skills_dirs = bundled or (skills_dir,)
        else:
            skills_dirs = (skills_dir,)

    findings = [
        finding
        for skills_dir in skills_dirs
        for finding in checks.audit_skills(
            skills_dir,
            claude_md=root / "CLAUDE.md",
            shipped=checks.shipped_skill_names(),
        )
    ]

    print(
        checks.ascii_safe(
            "skill fleet audit: "
            + ", ".join(checks.display_path(path, root) for path in skills_dirs)
        )
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


# How many offending paths to name per probe. A tree with hundreds of dirty files is
# already answered by the first screenful, and the count above the list is the number
# that blocks -- so truncation costs nothing, but it is announced rather than silent.
_MAX_LISTED = 25


def _cmd_publish_check(args: argparse.Namespace) -> int:
    if args.repo is None:
        root = publish.checkout_root()
    else:
        root = Path(args.repo).resolve()
        if not root.is_dir():
            raise _UsageError(f"--repo is not a directory: {root}")

    report = publish.check(root)

    # The checkout's NAME, not its path: this output gets pasted into hand-offs, and an
    # absolute path is portable to exactly one machine (and trips the hygiene scan).
    print(
        checks.ascii_safe(
            f"lemmi-ai-kit {__version__} pre-publish check -> {root.name}"
        )
    )
    print(
        checks.ascii_safe(
            f"payload: {', '.join(report.payload)} ({report.tracked} tracked file(s))\n"
        )
    )

    previous_blocked = False
    for result in report.results:
        if previous_blocked:
            print()
        previous_blocked = result.blocks
        status = "BLOCKED" if result.blocks else "ok     "
        print(checks.ascii_safe(f"{status} {result.probe.label} ({len(result.paths)})"))
        if not result.blocks:
            continue
        print(checks.ascii_safe(f"         {result.probe.consequence}"))
        for path in result.paths[:_MAX_LISTED]:
            # A trailing slash means git stopped at a nested repository and cannot say
            # how many files are inside. Marked, because an unmarked directory entry
            # reads as one file.
            note = (
                " <- a whole directory git cannot look inside; all of it ships"
                if path.endswith("/")
                else ""
            )
            print(checks.ascii_safe(f"           - {path}{note}"))
        hidden = len(result.paths) - _MAX_LISTED
        if hidden > 0:
            print(checks.ascii_safe(f"           ... and {hidden} more"))
        # The remedy travels with the refusal. A publisher told only "no", at the moment
        # they are trying to ship, is a publisher who goes looking for a --force.
        print(checks.ascii_safe("         to clear it:"))
        for line in result.probe.remedy:
            print(checks.ascii_safe(f"           {line}"))

    if report.extra:
        # "at least" is not hedging. When a nested repo is in the set the true number is
        # unknowable to git, and a guard about what ships must not print a floor as a total.
        floor = "at least " if report.undercounts else ""
        print(
            checks.ascii_safe(
                f"\na plugin install would copy {floor}{report.tracked + report.extra} file(s) "
                f"out of the payload: {report.tracked} tracked + {floor}{report.extra} that git does not track"
            )
        )

    blocking = sum(1 for result in report.results if result.blocks)
    if blocking:
        print(
            checks.ascii_safe(
                f"\nPUBLISH BLOCKED ({blocking} of {len(report.results)} probe(s) non-empty). "
                "Commit it, delete it, or do not publish -- there is no third option here."
            )
        )
        return 1
    print(
        checks.ascii_safe(
            "\nPUBLISH CHECK PASSED (the payload is exactly the git tree)"
        )
    )
    return 0


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


# --- `new-pack` ---------------------------------------------------------------------------

# The skeleton `new-pack` copies. Deliberately NOT a pack: neither marketplace manifest
# lists it, and every pack enumeration in this package -- `shipped_skill_dirs()`,
# `available_packs()`, and the test modules that follow them -- iterates the `PACKS`
# literal instead of globbing `plugins/*`. That is what keeps a skill directory in here
# invisible to `load_manifest()`, which raises on an unlisted skill dir and would redden
# the whole suite on the day the template was added.
PACK_TEMPLATE = "plugins/_template"

# The template's own README documents the template, not the pack, so it is the one file
# that is not copied. Matched against the relative posix path, so only the top-level one
# is skipped and a `skills/<name>/README.md` would still be copied (and still be a bug).
_TEMPLATE_ONLY: frozenset[str] = frozenset({"README.md"})

# Renamed to the author's skill name on copy.
_TEMPLATE_SKILL_DIR = "example-skill"

# Substituted in these; anything else is copied byte for byte.
_TEMPLATE_TEXT_SUFFIXES: frozenset[str] = frozenset(
    {".md", ".json", ".toml", ".txt", ".yaml", ".yml"}
)

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

# The charset `tests/test_plugin.py` asserts every plugin name against. Refused here
# rather than at test time, because the failure it produces there names the generated
# manifest rather than the argument that caused it.
_PACK_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

# Words a title-caser gets wrong, listed rather than guessed from length -- `ai` is an
# initialism and `go` is a language name, and both are two letters. This only produces
# the DEFAULT display name; `--display-name` overrides it.
_INITIALISMS: frozenset[str] = frozenset(
    {"ai", "ml", "cli", "api", "sdk", "sql", "db", "ui", "ux", "os", "io", "js", "ts"}
)


def _project_metadata(repo: Path) -> dict[str, object]:
    """`[project]` from the checkout's `pyproject.toml`, or a usage error naming why not."""
    path = repo / "pyproject.toml"
    try:
        data = cast(
            "dict[str, object]", tomllib.loads(path.read_text(encoding="utf-8"))
        )
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise _UsageError(
            f"could not read pyproject.toml under {repo.name}: {exc}"
        ) from None
    project = data.get("project")
    if not isinstance(project, dict):
        raise _UsageError(
            "pyproject.toml has no [project] table, so a pack's version, repository "
            "and license cannot be derived -- and every one of those is asserted "
            "against it by the suite"
        )
    return cast("dict[str, object]", project)


def _required_string(table: dict[str, object], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise _UsageError(f"pyproject.toml [project] has no usable {where}")
    return value


def _owner_url(repository: str) -> str:
    """The owner page for a repository URL: the same URL with its last segment dropped."""
    head, _, tail = repository.rstrip("/").rpartition("/")
    return head if head and tail else repository


def _default_display_name(plugin_name: str) -> str:
    """`lemmi-ai-kit-rust` -> `Lemmi AI Kit Rust`. A default, not a rule."""
    return " ".join(
        word.upper() if word in _INITIALISMS else word.capitalize()
        for word in plugin_name.split("-")
        if word
    )


def _pack_substitutions(
    repo: Path,
    *,
    pack: str,
    skill: str,
    plugin_name: str,
    display_name: str,
    description: str,
    author: str | None,
    author_url: str | None,
) -> dict[str, str]:
    """Every `{{KEY}}` the template may use, with the derivable half derived.

    Version, repository and license come from `pyproject.toml` rather than from flags
    on purpose: `test_plugin.py` asserts a pack's version and repository against that
    file and `test_license.py` asserts its license against `LICENSE`, so a value typed
    in here would be a test failure waiting on the next release bump -- and the wrong
    value the first time somebody authors a pack in a fork.

    The AUTHOR defaults to the same file and is overridable, which the others are not.
    CONTRIBUTING.md makes the `author` field a provenance label rather than metadata:
    a pack this repo's owner did not write must carry its own author in both manifests,
    and a default that silently claimed otherwise would produce exactly the mislabelling
    the rule exists to prevent -- on the path of least resistance.
    """
    project = _project_metadata(repo)
    urls = project.get("urls")
    repository = _required_string(
        cast("dict[str, object]", urls) if isinstance(urls, dict) else {},
        "Repository",
        "urls.Repository",
    )
    author_name = author or ""
    if not author_name:
        authors = project.get("authors")
        if isinstance(authors, list) and authors:
            first = cast("list[object]", authors)[0]
            if isinstance(first, dict):
                raw = cast("dict[str, object]", first).get("name")
                author_name = raw if isinstance(raw, str) else ""
    if not author_name:
        raise _UsageError(
            "pyproject.toml [project] names no author and --author was not given, so "
            "the pack cannot credit one"
        )

    return {
        "PACK": pack,
        "SKILL_NAME": skill,
        "PLUGIN_NAME": plugin_name,
        "DISPLAY_NAME": display_name,
        "DESCRIPTION": description,
        "VERSION": _required_string(project, "version", "version"),
        "LICENSE": _required_string(project, "license", "license"),
        "REPOSITORY": repository,
        "AUTHOR_NAME": author_name,
        "AUTHOR_URL": author_url or _owner_url(repository),
    }


def _render_template(text: str, subs: dict[str, str], where: str) -> str:
    """Substitute, then refuse anything still holding a placeholder.

    Failing loudly is the point. Passing an unknown key through would write a literal
    `{{...}}` into a marketplace listing, and the only things that read that listing are
    a plugin host and whoever is deciding whether to install.
    """
    rendered = _PLACEHOLDER_RE.sub(lambda m: subs.get(m.group(1), m.group(0)), text)
    unresolved = sorted({m.group(1) for m in _PLACEHOLDER_RE.finditer(rendered)})
    if unresolved:
        raise _UsageError(
            f"{where}: template placeholder(s) with no value: "
            f"{', '.join(unresolved)} -- give them a value in _pack_substitutions, or "
            "drop them from the template"
        )
    return rendered


def _pack_layout(template: Path, skill: str) -> list[tuple[Path, Path]]:
    """(source, destination relative to the new pack) for every file that gets copied."""
    pairs: list[tuple[Path, Path]] = []
    for source in sorted(p for p in template.rglob("*") if p.is_file()):
        relative = source.relative_to(template)
        if relative.as_posix() in _TEMPLATE_ONLY:
            continue
        parts = list(relative.parts)
        if len(parts) > 2 and parts[0] == "skills" and parts[1] == _TEMPLATE_SKILL_DIR:
            parts[1] = skill
        pairs.append((source, Path(*parts)))

    # Guard the template, not the argument. A template missing one of these still copies
    # cleanly and produces a pack the suite rejects with an error naming the generated
    # manifest instead of the skeleton that omitted it.
    produced = {destination.as_posix() for _, destination in pairs}
    required = (
        ".claude-plugin/plugin.json",
        ".codex-plugin/plugin.json",
        f"skills/{skill}/SKILL.md",
    )
    missing = [name for name in required if name not in produced]
    if missing:
        raise _UsageError(
            f"{PACK_TEMPLATE} cannot produce a valid pack: no {', '.join(missing)} "
            f"(the example skill directory must be named `skills/{_TEMPLATE_SKILL_DIR}/`)"
        )
    return pairs


def _relative_to_repo(path: Path, repo: Path, fallback: str) -> str:
    """`path` as a repo-relative posix path, or `fallback` when it sits outside `repo`."""
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except (OSError, ValueError):
        return fallback


def _package_dir_relative(repo: Path) -> str:
    """Where this package sits inside `repo`, as a repo-relative posix path.

    Two cases, both derived. Normally the running package IS the target checkout's, so
    the answer falls straight out of `Path(__file__)`. When `--repo` names a DIFFERENT
    checkout -- which the round-trip test does deliberately -- the running package is
    somewhere else entirely, so it is located inside the target by its own directory
    name. Neither spelling puts a repo-layout path literal into this file, which ships
    inside a plugin payload where no `plugins/<pack>/` exists above it.
    """
    here = Path(__file__).resolve().parent
    inside = _relative_to_repo(here, repo, "")
    if inside:
        return inside
    for candidate in sorted((repo / "plugins").glob(f"*/src/{here.name}")):
        if candidate.is_dir():
            return candidate.relative_to(repo).as_posix()
    return here.name


def _registration_steps(
    repo: Path, pack: str, plugin_name: str
) -> list[tuple[str, str]]:
    """The chokepoints a new pack must be registered in, and what to add to each.

    Derived, not written down. The marketplace pair comes from the same constant the
    publish guard reads, so a manifest added there appears here too. The two package
    paths are computed because spelling either as a literal would put a repo-layout path
    into a file that ships inside a plugin payload, where there is no `plugins/<pack>/`
    above it.
    """
    package_dir = _package_dir_relative(repo)
    assets = _relative_to_repo(
        assets_root(), repo, f"{package_dir}/{assets_root().name}"
    )
    source = f"./plugins/{pack}"
    steps: list[tuple[str, str]] = [
        (
            relative,
            f'add "{plugin_name}" with source {source} -- copy the `source` syntax '
            "this file's existing entries use (the two hosts spell it differently)",
        )
        for relative in publish.MARKETPLACE_MANIFESTS
        if (repo / relative).is_file()
    ]
    steps += [
        (
            f"{package_dir}/manifest.py",
            f'add "{pack}" to Pack, PACKS and PACK_PLUGIN_NAMES, add its profile to '
            "PROFILES, and map that profile in pack_for_profile()",
        ),
        (f"{assets}/manifest.toml", "one [[skills]] entry per skill in the pack"),
        (
            "docs/upstream-sync.toml",
            "one row per skill, SORTED BY NAME, each with an explicit `upstream` "
            "(empty string when there is no counterpart)",
        ),
        (
            "README.md",
            "update the skill counts (tests/test_readme_counts.py derives them from "
            "the asset manifest)",
        ),
    ]
    return steps


def _cmd_new_pack(args: argparse.Namespace) -> int:
    if args.repo is None:
        repo = publish.checkout_root()
    else:
        repo = Path(args.repo).resolve()
        if not repo.is_dir():
            raise _UsageError(f"--repo is not a directory: {args.repo}")

    template = repo / PACK_TEMPLATE
    if not template.is_dir():
        raise _UsageError(
            f"no pack template at {PACK_TEMPLATE} under {repo.name} -- `new-pack` runs "
            "in a checkout of the kit, not in an adopter's project"
        )

    pack: str = args.name
    if _PACK_NAME_RE.fullmatch(pack) is None:
        raise _UsageError(
            f"pack name {pack!r} must match {_PACK_NAME_RE.pattern} -- it becomes both "
            "a directory name and a plugin name, and the suite asserts that charset"
        )
    destination = repo / "plugins" / pack
    if destination.exists():
        raise _UsageError(
            f"plugins/{pack} already exists -- `new-pack` never writes over a pack"
        )

    skill: str = args.skill or f"{pack}-conventions"
    if checks.SKILL_NAME_RE.match(skill) is None:
        raise _UsageError(
            f"skill name {skill!r} must match {checks.SKILL_NAME_RE.pattern} -- the "
            "audit rejects a skill whose directory name does not"
        )

    plugin_name: str = args.plugin_name or f"lemmi-ai-kit-{pack}"
    if _PACK_NAME_RE.fullmatch(plugin_name) is None:
        raise _UsageError(
            f"plugin name {plugin_name!r} must match {_PACK_NAME_RE.pattern}"
        )
    display_name: str = args.display_name or _default_display_name(plugin_name)
    # Shaped like the existing packs' descriptions rather than like a placeholder: this
    # string lands in two marketplace listings, and a default that reads as unfinished
    # is one somebody ships anyway.
    description: str = (
        args.description
        or f"{pack.capitalize()} conventions for projects using the "
        "Lemmi AI Kit core plugin."
    )

    subs = _pack_substitutions(
        repo,
        pack=pack,
        skill=skill,
        plugin_name=plugin_name,
        display_name=display_name,
        description=description,
        author=args.author,
        author_url=args.author_url,
    )
    layout = _pack_layout(template, skill)

    # Render everything before writing anything: a placeholder with no value must fail
    # with no pack on disk, not with a half-written one somebody has to clean up.
    rendered: list[tuple[Path, str | bytes]] = []
    for source, relative in layout:
        if source.suffix in _TEMPLATE_TEXT_SUFFIXES:
            where = f"{PACK_TEMPLATE}/{source.relative_to(template).as_posix()}"
            rendered.append(
                (
                    relative,
                    _render_template(source.read_text(encoding="utf-8"), subs, where),
                )
            )
        else:
            rendered.append((relative, source.read_bytes()))

    dry_run: bool = args.dry_run
    prefix = "[dry-run] " if dry_run else ""
    print(
        checks.ascii_safe(
            f"{prefix}lemmi-ai-kit {__version__} new-pack -> plugins/{pack}"
        )
    )
    for relative, _ in rendered:
        print(checks.ascii_safe(f"{prefix}  plugins/{pack}/{relative.as_posix()}"))

    if not dry_run:
        for relative, payload in rendered:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(payload, str):
                target.write_text(payload, encoding="utf-8", newline="\n")
            else:
                target.write_bytes(payload)

    print(
        checks.ascii_safe(
            f"\n{prefix}{len(rendered)} file(s), plugin `{plugin_name}`, skill `{skill}`"
        )
    )
    print(
        checks.ascii_safe(
            "\nnot done yet -- register the pack. `new-pack` edits none of these: each "
            "is a reviewed chokepoint, and adding a plugin to a published marketplace "
            "listing is a decision, not a side effect of scaffolding."
        )
    )
    for index, (where, what) in enumerate(
        _registration_steps(repo, pack, plugin_name), 1
    ):
        print(checks.ascii_safe(f"  {index}. {where}"))
        print(checks.ascii_safe(f"     {what}"))
    print(
        checks.ascii_safe(
            "\nthen `uv run pytest` -- the suite is what tells you the pack is real. "
            "The whole path is in docs/authoring-a-pack.md."
        )
    )
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
        if args.command == "publish-check":
            return _cmd_publish_check(args)
        if args.command == "new-pack":
            return _cmd_new_pack(args)
    except (ManifestError, OSError, _UsageError, publish.PublishCheckError) as exc:
        print(f"error: {exc}")
        return 2
    parser.error(f"unknown command: {args.command}")
