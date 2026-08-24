"""Asset hygiene: valid frontmatter and no project/machine contamination.

These tests are the permanent enforcement of the porting cleanup contract:
assets must work in a brand-new project on any machine.
"""

import re
from pathlib import Path

from lemmi_ai_kit.manifest import (
    PACKS,
    assets_root,
    load_manifest,
    skill_dir,
    skills_root,
)

# (pattern, human explanation)
_FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"/Users/"), "absolute macOS home path"),
    (re.compile(r"/home/\w"), "absolute Linux home path"),
    (re.compile(r"[A-Za-z]:\\\\?[A-Za-z]"), "Windows drive-letter path"),
    (re.compile(r"Windows host"), "machine-specific host rule"),
    (re.compile(r"PYTHONIOENCODING"), "machine-specific console workaround"),
    (re.compile(r"lemmi-ai-api"), "source-project reference"),
    (re.compile(r"learnings\.md\s+20\d{2}-\d{2}"), "dated learnings citation"),
    (re.compile(r"retrospectives/20\d{2}"), "dated retrospective citation"),
    (re.compile(r"\.ai/backups/"), "source-project backup reference"),
    # Extraction rewrote 19 of these across 8 skills; nothing tested for it, so every
    # upstream refresh re-imported them on human diligence alone. Kit scripts ship
    # inside the plugin, so a project-relative skills path is broken by construction --
    # use ${CLAUDE_SKILL_DIR}/scripts/... instead. Bare `.claude/skills/` stays legal:
    # 20+ assets legitimately discuss the project-local skills directory.
    (
        re.compile(r"\.claude/skills/[A-Za-z0-9_-]+/scripts/"),
        "hard-coded skill-script path (use ${CLAUDE_SKILL_DIR})",
    ),
)


# Charter DoD 4: zero references to infrastructure the kit does not ship.
#
# These are ASSET-ONLY on purpose, and are deliberately not part of `_FORBIDDEN`.
# `_FORBIDDEN` is about contamination -- a machine path or a private project name is
# wrong in any tracked file, which is why test_publication_hygiene.py imports it and
# applies it repo-wide. This tuple is a different claim: it is about what the *shipped
# pack* may point at. A research doc that analyses the port necessarily names the
# upstream scripts, and `cli.py` necessarily contains `audit_skills` as its own
# subcommand identifier -- neither is a portability defect, and allowlisting each one
# would grow an exemption list with every future document.
#
# The two upstream scripts are replaced by the kit's own CLI. Shipping them alongside
# it would mean two implementations that disagree about what is valid, so the names
# must not reappear on the next sync. The scripts the kit DOES ship -- drain_audit,
# audit_cleanup_targets, probe_checker, extract_sessions -- are absent from this list
# on purpose.
def _cli_subcommands() -> tuple[str, ...]:
    """Every subcommand the CLI actually declares, from the parser that declares them.

    Hand-listing these went stale the moment `new-pack` and `publish-check` shipped: the
    pattern below covered four of six, so `lemmi-ai-kit new-pack <x>` in a shipped asset
    passed the guard that exists to catch exactly that. Deriving it means a seventh
    subcommand is covered by existing, not by someone remembering.
    """
    from lemmi_ai_kit.cli import _build_parser  # pyright: ignore[reportPrivateUsage]

    for action in _build_parser()._actions:  # pyright: ignore[reportPrivateUsage]
        choices = getattr(action, "choices", None)
        if choices:
            return tuple(sorted(str(name) for name in choices))
    raise AssertionError("the CLI parser declares no subcommands -- probe is broken")


_SUBCOMMAND_ALTERNATION = "|".join(re.escape(sub) for sub in _cli_subcommands())


_ASSET_ONLY_FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"ai_files_lint"),
        "unshipped linter (use `python -m lemmi_ai_kit lint`)",
    ),
    (
        re.compile(r"audit_skills"),
        "unshipped audit (use `python -m lemmi_ai_kit audit-skills`)",
    ),
    # The `lemmi-ai-kit` console script comes from `[project.scripts]`, so it exists
    # only after a pip/uv install of the package. The kit installs as a Claude Code
    # plugin -- `/plugin install` places skills and never installs the distribution --
    # so a skill telling an adopter to run `lemmi-ai-kit <sub>` names a command they do
    # not have. Use the module form, which `kit-setup` already documents:
    # PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python -m lemmi_ai_kit <sub>
    # The bare plugin name stays legal -- it is the marketplace id and the
    # `/lemmi-ai-kit-core:<skill>` invocation prefix.
    (
        re.compile(rf"lemmi-ai-kit\s+(?:{_SUBCOMMAND_ALTERNATION})\b"),
        "console-script invocation (plugin installs place no console script)",
    ),
    # The stacked-PR document scaffolds to `.ai/`, never `docs/`.
    (
        re.compile(r"docs/git-stacked-pr-workflow"),
        "stacked-PR doc path (scaffolds to .ai/, not docs/)",
    ),
    # Source-project product document, a declared non-goal of the port.
    (re.compile(r"interview-prompt-changelog"), "source-project product document"),
)

# Files allowed to mention a pattern because they *teach or implement* the rule
# that bans it. Keep this list minimal and specific.
_ALLOWLIST: dict[str, tuple[str, ...]] = {
    # The portability rule itself names the forbidden path shapes.
    "templates/AGENTS.md": ("absolute macOS home path",),
    # The portability review check documents the patterns to grep for.
    "skills/skill-reviewer/SKILL.md": (
        "absolute macOS home path",
        "Windows drive-letter path",
    ),
    # Secret-redaction regexes (`authorization:\s`) and a comment about runtime
    # Windows path normalization trip the drive-letter pattern.
    "skills/session-retrospective/scripts/extract_sessions.py": (
        "Windows drive-letter path",
    ),
    # Path-encoding test fixtures (the rule's explicit "redaction-test fixtures" exception).
    "skills/session-retrospective/scripts/test_extract_sessions.py": (
        "absolute macOS home path",
        "absolute Linux home path",
        "Windows drive-letter path",
    ),
}


def _asset_text_files() -> list[Path]:
    return sorted(
        p
        for root in (assets_root(), *(skills_root(pack) for pack in PACKS))
        if root.is_dir()
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix in {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml"}
    )


def _asset_relative(path: Path) -> str:
    root = assets_root()
    if path.is_relative_to(root):
        return path.relative_to(root).as_posix()
    for pack in PACKS:
        pack_root = skills_root(pack)
        if path.is_relative_to(pack_root):
            return f"skills/{path.relative_to(pack_root).as_posix()}"
    return path.as_posix()


def test_assets_have_no_contamination() -> None:
    violations: list[str] = []
    for path in _asset_text_files():
        rel = _asset_relative(path)
        text = path.read_text(encoding="utf-8")
        allowed = _ALLOWLIST.get(rel, ())
        for pattern, why in (*_FORBIDDEN, *_ASSET_ONLY_FORBIDDEN):
            if why in allowed:
                continue
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                violations.append(f"{rel}:{line}: {why} ({match.group(0)!r})")
    assert not violations, "contaminated assets:\n" + "\n".join(violations)


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def test_every_skill_has_valid_frontmatter() -> None:
    problems: list[str] = []
    for entry in load_manifest().skills:
        skill_md = skill_dir(entry) / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f"{entry.name}: SKILL.md missing")
            continue
        text = skill_md.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if match is None:
            problems.append(f"{entry.name}: no YAML frontmatter block")
            continue
        block = match.group(1)
        name_match = re.search(r"^name:\s*(\S+)\s*$", block, re.MULTILINE)
        if name_match is None or name_match.group(1) != entry.name:
            problems.append(
                f"{entry.name}: frontmatter name mismatch ({name_match and name_match.group(1)})"
            )
        if re.search(r"^description:", block, re.MULTILINE) is None:
            problems.append(f"{entry.name}: frontmatter missing description")
    assert not problems, "\n".join(problems)


def test_skill_relative_references_resolve() -> None:
    """Any references/..., assets/..., scripts/... path mentioned in a SKILL.md must ship.

    Fenced code blocks are excluded: skills that teach skill authoring show
    illustrative example links there.
    """
    link_re = re.compile(r"\((?:\./)?((?:references|assets|scripts)/[\w./-]+)\)")
    fence_re = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
    problems: list[str] = []
    for entry in load_manifest().skills:
        entry_dir = skill_dir(entry)
        skill_md = entry_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        prose = fence_re.sub("", skill_md.read_text(encoding="utf-8"))
        for match in link_re.finditer(prose):
            target = entry_dir / match.group(1)
            if not target.is_file():
                problems.append(f"{entry.name}: broken reference {match.group(1)}")
    assert not problems, "\n".join(problems)


def test_ai_state_files_ship_empty() -> None:
    """Stateful .ai logs must ship as headers only — a new project starts with zero entries."""
    root = assets_root()
    for name in ("learnings.md", "ai-changelog.md", "improvement-hypotheses.md"):
        text = (root / "ai" / name).read_text(encoding="utf-8")
        assert not re.search(r"^### \[?20\d{2}-", text, re.MULTILINE), (
            f"{name} ships with dated entries"
        )


def test_the_console_script_pattern_covers_every_subcommand() -> None:
    """Positive control for a guard that silently covered four of six.

    A pattern listing subcommands by hand cannot fail when a new one ships -- it just
    stops covering it. This asserts the opposite direction: for every subcommand the
    parser declares, the guard matches a realistic invocation of it. The negative case
    is asserted too, so a pattern degenerating to "match anything" fails here rather
    than passing everywhere.
    """
    pattern = next(pat for pat, why in _ASSET_ONLY_FORBIDDEN if "console-script" in why)
    subs = _cli_subcommands()
    assert len(subs) >= 6, f"expected at least 6 subcommands, probe saw {subs}"

    uncovered = [
        sub for sub in subs if not pattern.search(f"run lemmi-ai-kit {sub} now")
    ]
    assert not uncovered, (
        f"the console-script guard does not cover: {uncovered}. Add nothing by hand -- "
        "the alternation is derived, so an uncovered subcommand means the derivation broke"
    )

    # It must NOT match the bare plugin name, which is legal: it is the marketplace id
    # and the `/lemmi-ai-kit-core:<skill>` invocation prefix.
    for legal in (
        "install lemmi-ai-kit from the marketplace",
        "/lemmi-ai-kit-core:commit-message",
        "the lemmi-ai-kit repository",
    ):
        assert not pattern.search(legal), f"guard is over-broad: it matched {legal!r}"
