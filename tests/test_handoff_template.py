"""The hand-off template the kit seeds, and the places that say it exists.

A project that gets the kit has the lint and, in the Orchestration pack's safety skill, the contract
text, but until now no file to copy: a delegated session wrote its note from memory. The Core pack
ships one template, `.ai/templates/handoff.md`, whose line 1 is the version label and whose seven
sections are the contract: the five the lint always required and the two a v2 note adds. Core owns
it because Core alone has the lint, so the template is what shows a Core-only project the contract.

What each test holds: the file is planned by the scaffold as a kit-managed file and the kit's own
copy is its byte twin; line 1 is the label of the newest contract version; the unfilled template
passes the lint and has exactly the required sections in order; each defect planted in it is found,
so the clean result means something; the comments do not nest (the label closes a comment, so a
comment that quoted it would end early); and the skill section, the three docs pages and the FAQ
answer that list what the kit manages name this one. Every section list is derived from `checks`,
never typed.

Known limit, stated here and not fixed: the lint asks for a non-empty section, so the unfilled
template's placeholder text satisfies it, and a note copied and left unfilled passes.
"""

import re
from pathlib import Path

import pytest

from lemmi_ai_kit import checks, scaffold
from lemmi_ai_kit.manifest import assets_root, load_manifest, shipped_skill_dirs

_REPO = Path(__file__).resolve().parents[1]
_SEEDED = assets_root() / "ai" / "templates" / "handoff.md"
_OWN = _REPO / ".ai" / "templates" / "handoff.md"
_PLANNED = ".ai/templates/handoff.md"
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _template() -> str:
    if not _SEEDED.is_file():
        pytest.fail("the seeded hand-off template does not exist")
    return _SEEDED.read_text(encoding="utf-8")


def _newest() -> int:
    return max(checks.HANDOFF_SECTIONS_BY_VERSION)


def _required() -> tuple[str, ...]:
    return (
        *checks.HANDOFF_REQUIRED_SECTIONS,
        *checks.HANDOFF_SECTIONS_BY_VERSION[_newest()],
    )


def _headings(text: str) -> list[str]:
    outside = _COMMENT.sub("", text)
    return re.findall(r"^## (.+?)\s*$", outside, re.MULTILINE)


def _replaced_body(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"^(## {re.escape(name)}\n).*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
    )
    out, hits = pattern.subn(lambda m: m.group(1) + body + "\n", text, count=1)
    assert hits == 1, f"the template has no '## {name}' section"
    return out


def _messages(text: str) -> list[str]:
    return [finding.message for finding in checks.lint_handoff(text, "handoff.md")]


def _cut(text: str, start: str, end: str) -> str:
    """The part of `text` from the heading `start` up to the heading `end`, whitespace folded."""
    first = text.find(start)
    assert first != -1, f"no heading {start!r}"
    last = text.find(end, first)
    assert last != -1, f"no heading {end!r} after {start!r}"
    return " ".join(text[first:last].split())


# --- the file and where it lands --------------------------------------------------------------


def test_the_template_is_planned_by_the_scaffold_as_a_kit_managed_file() -> None:
    planned = {item.relative: item for item in scaffold.plan(load_manifest())}
    item = planned.get(_PLANNED)

    assert item is not None, f"the scaffold plans no {_PLANNED}"
    assert item.kind == "managed"
    assert item.content == _SEEDED.read_bytes()


def test_the_kits_own_copy_is_the_byte_twin_of_the_seeded_one() -> None:
    assert _OWN.is_file(), f"the kit's own {_PLANNED} does not exist"
    assert _OWN.read_bytes() == _SEEDED.read_bytes()


# --- what the template says -------------------------------------------------------------------


def test_line_one_is_the_label_of_the_newest_contract_version() -> None:
    first = _template().splitlines()[0].rstrip()
    match = checks.HANDOFF_LABEL_RE.match(first)

    assert match is not None, f"line 1 is not a version label: {first!r}"
    assert int(match.group(1)) == _newest()


def test_the_unfilled_template_passes_the_lint() -> None:
    assert checks.lint_handoff(_template(), "handoff.md") == []


def test_the_template_has_the_required_sections_in_order_and_no_others() -> None:
    assert tuple(_headings(_template())) == _required()


def test_the_comments_of_the_template_do_not_nest() -> None:
    text = _template()

    assert text.count("<!--") == text.count("-->")
    for comment in _COMMENT.findall(text):
        assert "<!--" not in comment[len("<!--") :], "a comment contains another"


def test_the_template_tells_its_author_to_run_the_hand_off_lint_on_the_file() -> None:
    comments = " ".join(" ".join(_COMMENT.findall(_template())).split())

    assert "lint handoffs" in comments
    assert "LINT PASSED" in comments


# --- each defect planted in the template is found -----------------------------------------------


def test_the_lint_finds_a_section_removed_from_the_template() -> None:
    text = _template()
    for name in checks.HANDOFF_SECTIONS_BY_VERSION[_newest()]:
        removed = re.sub(
            rf"^## {re.escape(name)}\n.*?(?=^## |\Z)",
            "",
            text,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )
        assert removed != text
        assert any(
            m.startswith(f"missing required section '## {name}'")
            for m in _messages(removed)
        ), f"removing '## {name}' was not found"


def test_the_lint_finds_a_status_word_outside_the_three() -> None:
    planted = _replaced_body(_template(), "Status", "**Status:** done")

    assert any("must state one of" in m for m in _messages(planted))


def test_the_lint_finds_a_verification_line_turned_into_prose() -> None:
    planted = _replaced_body(_template(), "Verification", "- the build is green")

    assert any("prose, not a runnable command" in m for m in _messages(planted))


# --- the places that say it exists ------------------------------------------------------------


def test_the_safety_skill_states_the_v2_sections_and_the_label() -> None:
    skill = shipped_skill_dirs()["parallel-session-safety"] / "SKILL.md"
    section = _cut(
        skill.read_text(encoding="utf-8"),
        "## 9. The hand-off artifact contract",
        "\n## 10. ",
    )

    for name in checks.HANDOFF_SECTIONS_BY_VERSION[_newest()]:
        assert f"`## {name}`" in section, f"section 9 does not name '## {name}'"
    assert f"`<!-- handoff-contract: v{_newest()} -->`" in section
    assert "no label, or `v1`" in section, "section 9 does not say what no label means"


_ROWS: tuple[tuple[str, str], ...] = (
    ("README.md", "| `.ai/templates/` |"),
    ("docs/adoption-guide.md", "| `.ai/templates/design.md`"),
    ("docs/working-on-the-kit.md", "| `plugins/core/src/lemmi_ai_kit/assets/ai/` |"),
    ("docs/working-on-the-kit.md", "| `--force` |"),
)


def _row(relative: str, anchor: str) -> str:
    text = (_REPO / relative).read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith(anchor)]
    assert len(rows) == 1, f"{relative}: {len(rows)} rows start with {anchor!r}"
    return rows[0]


@pytest.mark.parametrize(("relative", "anchor"), _ROWS)
def test_each_row_that_lists_the_seeded_templates_names_the_hand_off_template(
    relative: str, anchor: str
) -> None:
    assert "hand-off template" in _row(relative, anchor)


def test_the_faq_names_the_hand_off_template_among_what_the_kit_manages() -> None:
    text = (_REPO / "docs" / "faq.md").read_text(encoding="utf-8")
    answer = _cut(text, "## What does it actually put in my repository?", "\n## ")

    assert "the spec templates" in answer, (
        "the answer that lists what the kit manages moved"
    )
    assert "hand-off template" in answer


def test_the_adoption_guide_row_names_every_seeded_template_file() -> None:
    row = _row("docs/adoption-guide.md", "| `.ai/templates/design.md`")
    named = {
        name.removeprefix(".ai/templates/")
        for name in re.findall(r"`([^`]+\.md)`", row.split("|")[1])
    }
    on_disk = {path.name for path in _SEEDED.parent.glob("*.md")}

    assert named == on_disk
