# Adoption guide — the first deliberate claim-by-claim audit

**Dated:** 2026-08-24. **Audited at:** `818e4e1`, clean tree, suite 299 passed / 6 skipped,
all four gates green. **Owned by this record:** `docs/adoption-guide.md` and this file. Nothing
else was written.

## Why it was audited at all

Three sessions had each found a defect in this document *by accident*, while doing something
else. The third find is the one that funded this pass: it was not stale, it was **wrong when it
was written** — the guide told adopters the pack template, `new-pack` and the authoring document
did not exist, on a day all three did. A claim written from a brief rather than from the tree is
false at birth, and a staleness sweep never catches it, because there is no "before" in which it
was true.

The other two accidental finds have the same shape: the two install paths were described
**backwards** (Claude Code called documentation-only, Codex called executed), and the `/` menu
was described as showing a minority of skills when the manifest says most core skills are
user-invocable.

So: nobody had ever read it top to bottom against the tree. This is that read.

## Method, and the rule that produced most of the finds

Every factual assertion an adopter could act on or plan around — a path, a command, a count, a
capability, a limitation, a "verified", a comparison between the two hosts — was pulled out and
classified **TRUE / FALSE / UNVERIFIABLE HERE**, each against a thing in the tree.

**No other document was accepted as evidence.** Not handoffs, not the records in this directory,
not the README. The manifest, the tests, the shipped templates and the CLI's actual behaviour
were the only authorities. That rule is what produced the two subtlest finds below (the `--force`
scope and the pack-authoring citation): both were *consistent with a document* and inconsistent
with the code.

Where a claim could not be executed here it says so rather than being inferred. `claude` and
`codex` are both absent from this machine's PATH — verified, not assumed:

```
$ command -v claude || echo "claude: ABSENT"
claude: ABSENT
$ command -v codex || echo "codex: ABSENT"
codex: ABSENT
```

## Tally

| | Count |
|---|---|
| Claims audited | 128 |
| TRUE | 98 |
| FALSE — fixed in this pass | 13 |
| UNVERIFIABLE HERE — text made honest about it | 17 |

Two of the TRUE ones (the two install dates) rest on an operator-supplied fact, not on anything
executable here; they are marked as such below rather than counted as proven.

## The thirteen false claims

Ordered as they appear in the document.

### 1. A quoted phrase that is not in the tree

Said core routes to language conventions by role, quoting *"the installed coding conventions
skill"*. The shipped `AGENTS.md` template says **`coding-conventions`**, hyphenated, and the
unhyphenated form appears nowhere. The claim was right; the quotation marks were lying.

### 2. Which marketplace spelling was actually typed at Codex

Said *"Codex was verified with `.`"* and *"Each form above is the one actually run against that
client."* The Claude Code half is supported. The Codex half is not: the run that exists used a
**local directory path** and no record pins the spelling to a bare `.`. The commands are
unchanged — they are the repo's settled forms — but the guide no longer claims the Codex line is
a transcript.

### 3. The Codex verification date

Said the Codex local-clone install was run **2026-08-23**. It was **2026-08-22**. The document
contradicted itself: its own "Not verified" table at the end already said 2026-08-22. Fixed to
2026-08-22.

### 4. A pointer to a thing an adopter cannot find

Said *"the `invocation` column in the catalog tells you which is which."* An `invocation` column
does exist — in the CLI's catalog listing — but the guide never says what "the catalog" is, never
prints the command, and the reader at that point has installed a plugin rather than cloned a
repo. The claim was unactionable where it stood. Replaced with the `CLAUDE.md` the scaffold
writes into their own repository, which sorts the same inventory under three headings and was
read verbatim out of a real scaffold run.

### 5. The spec templates were under-listed

Said `.ai/templates/` holds `design.md`, `requirements.md`, `tasks.md`. It holds **five**:
`test-cases.md` and `test-plan.md` ship too, and `spec-driven-dev` names all five. Both new files
are tracked. The row now lists all five and credits `test-planner` alongside `spec-driven-dev`.

### 6 and 7. "Nine files", twice

Said the scaffold writes **nine** files (once in section 4, once in section 6B). It writes
**eleven**. Derived, not counted by eye:

```
$ python -m lemmi_ai_kit scaffold <fresh dir>
written: 6  seeded: 5  overwritten: 0  unchanged: 0
$ find <fresh dir> -type f | wc -l
11
```

Fixed by **removing the number rather than correcting it.** A corrected nine becomes a wrong
eleven the next time a template lands — which is exactly how it broke: the two new templates
moved the total and nothing pointed at this sentence. The text now refers to the table above it.

### 8 and 9. The `### Project rules` stub does not exist

Said the seeded `AGENTS.md` ends with:

```markdown
### Project rules
> TODO(project): add project-specific do-nots here as they are discovered
> (the `task-learnings` → `/learning-consolidator` loop will promote them).
```

No such text is in the template. The real section is self-documenting prose — it explains what
belongs there, what does not, and why a rule needs its reason — and it ends on an italic
empty-state line. `kit-setup` is explicit about this: *"That section is no longer a stub: it
explains itself and states its own empty state."* The follow-on instruction, *"Replace that stub
with your own rules,"* was therefore also wrong: the skill says to append under the heading and
replace the italic line only once you have a real rule. Both fixed against the template's actual
bytes.

This is the same failure class as the third accidental find: the guide described a template
revision that had already been superseded, and quoted it as if transcribed.

### 10. The dry-run sample output

Printed `written: 4  seeded: 4`. The real output against a project that already has an
`AGENTS.md` is `written: 6  seeded: 4`. Same root cause as the file count. The rest of the sample
block — the `kept 1 project-owned seed file(s)` line and the `- AGENTS.md` beneath it — is
verbatim correct and was left alone.

### 11. What `--force` actually touches

Said *"`--force` is milder — it refreshes the kit-managed `.ai/templates/` only."* It refreshes
**every** managed file, and one of them is outside `.ai/templates/`. Derived from the planner
rather than read off a docstring — `scaffold.py`'s own module docstring says `.ai/templates/`
too, so the guide was consistent with the prose and wrong about the code:

```
MANAGED (what --force refreshes):
    .ai/git-stacked-pr-workflow.md
    .ai/templates/design.md
    .ai/templates/requirements.md
    .ai/templates/tasks.md
    .ai/templates/test-cases.md
    .ai/templates/test-plan.md
```

The `--reseed` half of the same note is correct and unchanged.

### 12. "It is two paragraphs"

Section 6B sends a non-Python reader to section C and promises it is two paragraphs. Section C is
four paragraphs and a subsection. A small thing, but it is a claim about the cost of a click, and
it is the kind that makes a reader trust the next number less. Made non-numeric.

### 13. A citation that did not say what it was cited for

Said pack authoring without a clone was *"measured, not assumed: an author with no access to the
clone completes none of it."* The record it draws on measures something different — the
with-a-clone case — and its headline finding is that several registration steps are blocked even
*with* one. Rather than import a figure from a record that can age, the claim is now the
executable fact, run here:

```
$ python -m lemmi_ai_kit new-pack rust --skill rust-conventions --dry-run   # outside a checkout
error: not inside a git checkout: <scratch dir>
exit 2
```

The same substitution was made in the "Not built" table row.

## One addition that is not a correction

Section C tells a Go or Rust team that core works unchanged and *"that is the entire path."* That
is true of the **skills** — `tests/test_pack_boundaries.py` enforces it, and it passes. It is not
the whole picture of what lands in their repository: the `AGENTS.md` template is language-neutral
in its skills and not in its text, so a Go team is seeded with a `### Python rules (Python
projects)` block. Confirmed in two independent scaffold runs, at the same line each time.

Nothing in the guide was false about this — it simply did not come up. One paragraph was added
saying the block is there, that no core skill depends on it, and that deleting it sticks because
it lives outside every marker. A surprise an adopter can pre-empt is cheaper than one they
discover.

## Seventeen claims that cannot be settled on this machine

All of them concern the two hosts, and they split into three groups.

**Commands against an absent binary** — every `claude plugin …` and `codex plugin …` line, on
both the shorthand and the local-clone paths, plus `codex plugin --help` and invoking `kit-setup`
from Codex. Neither binary is installed here. What *is* checkable is the identifiers those
commands carry, and those were checked against the manifests: marketplace `lemmi`, display name
`Lemmi`, plugin ids `lemmi-ai-kit-core` and `lemmi-ai-kit-python`, owner `lemmi-ukraine`. All
correct.

**Assertions about past runs** — the codex-cli version, the isolated home directory, the
materialized inventory, the core-only install carrying no Python skills, a client accepting a
plugin with no manifest, and the shape of `plugin details` output. These are historical; they
cannot be re-executed here at all. The guide already attributes each to a dated run, which is the
right treatment.

**Whether the clone URL resolves.** It matches the repository URL declared in both plugin
manifests and in `pyproject.toml`. Whether it is reachable is a property of the remote.

The `owner/repo` shorthand remains unexercised on both hosts. The guide says so in two places and
both are accurate.

## Found in files this pass does not own

Reported, not fixed.

| Where | What |
|---|---|
| `plugins/core/src/lemmi_ai_kit/scaffold.py` | The module docstring defines **managed** as "`.ai/templates/`". Six files are managed and one of them, `.ai/git-stacked-pr-workflow.md`, is not under that path. The code is right; the docstring is the thing that misled this document, and it will mislead the next reader of `--force`. |
| `README.md` | Correct, and worth noting as the contrast: its `.ai/templates/` row already lists all five templates. The guide drifted; the README did not, because a test holds its counts. |

No defect was found in `CONTRIBUTING.md`, `docs/authoring-a-pack.md`, `docs/faq.md`,
`docs/migrating-from-0.1.0.md` or the tests, on the claims this audit touched.

## Guards, re-run after the edits

Every instrument was given a positive control first, because a zero from a blind probe is the
failure mode this program keeps paying for.

| Guard | Control | Result on the guide |
|---|---|---|
| `_LOOSE_COUNT_SHAPE` from `tests/test_readme_counts.py` | matches a known count claim | **0 count-shaped claims** — the property held before this pass and still holds |
| `_FORBIDDEN` from `tests/test_publication_hygiene.py` | matches the source-project name | **0 hits** |
| `_PACKAGE_PATH` from `tests/test_repo_path_references.py` | matches a bare package path | **0 references**, so nothing to anchor |
| Anchor resolution | slugger reproduces a known GitHub anchor with its doubled hyphen | **24 internal links, 0 broken** |

The anchor probe lied on its first run: it collapsed runs of whitespace, so every heading
containing a spaced em-dash reported a broken link. Four false positives, all of them real
anchors. The control was added afterwards and the finding evaporated — worth recording as another
instance of the instrument being wrong before the tree is.

Four gates after the edits: `pytest` 299 passed / 6 skipped, `ruff check` clean,
`ruff format --check` clean, `basedpyright` 0 errors.

## What this audit did not cover

- **The prose that is advice rather than fact** — which situation a reader belongs in, whether a
  rule belongs in `### Project rules` or a pack. Judgment, not claims.
- **Whether the skills do what their summaries say.** This audited the guide against the tree,
  not the tree against itself.
- **Anything downstream of an install.** No install path was executed here; the scaffold half was
  executed in full.
- **The wheel.** The guide never offers it as an install route — it says there is nothing to `pip
  install`, which is exactly right — so its behaviour was out of scope, and no text was added
  that would imply otherwise.
