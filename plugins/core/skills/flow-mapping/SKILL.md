---
name: flow-mapping
description: >
  Map a subsystem's runtime behavior into scenario-based flow documentation,
  with callers, invariants, cross-flow links, evidence and a risk register.
  Use for "map this flow", "document this subsystem for agents", revising
  docs/flows, or diagnosing flow-validator findings. Bundles Python symbol
  validation, projection generation and cross-flow checks. Not for PR review
  or incident log analysis.
metadata:
  type: task
---

# Flow mapping

Produce a flow document an agent can query by file or symbol before changing code.
The output is a project-owned `docs/flows/<slug>.md` and, when findings exist, a
companion `tasks/BUG-register-flow-<slug>.md`. One scenario follows one trigger
through one linear path, including its caller-visible outcome.

## Host and project contract

Read the target project's AGENTS.md, relevant module documentation and any local
flow schema first. Existing project policy takes precedence. The bundled
[schema and skeletons](assets/flow-map-template.md) are the default; an existing
project template can add requirements. Report incompatible schemas rather than
silently dropping fields or weakening a validator.

Resolve `scripts/`, `references/` and `assets/` from this installed skill directory.
On Claude use `${CLAUDE_SKILL_DIR}`; on Codex substitute the actual directory
supplied by the host. All project paths belong to the consuming project, never
the plugin cache. Quote paths. Use `uv run --no-project python -B` for these
stdlib tools. Take task arguments from the request on hosts without `$ARGUMENTS`.

Set `FLOW_SKILL` below to that resolved skill directory and `PROJECT` to the
absolute target root. Select `CODE` as the project-relative directory containing
Python source (for example `src`, `backend`, or `.`). These are command examples,
not an instruction to use POSIX assignment syntax in PowerShell.

```sh
uv run --no-project python -B "$FLOW_SKILL/scripts/validate_flow_map.py" --project-root "$PROJECT" --code-root "$CODE" docs/flows/<slug>.md
uv run --no-project python -B "$FLOW_SKILL/scripts/validate_register.py" --project-root "$PROJECT" --code-root "$CODE" tasks/BUG-register-flow-<slug>.md
uv run --no-project python -B "$FLOW_SKILL/scripts/generate_flow_projections.py" --project-root "$PROJECT" --code-root "$CODE" docs/flows/<slug>.md --section all
uv run --no-project python -B "$FLOW_SKILL/scripts/generate_flow_projections.py" --project-root "$PROJECT" --code-root "$CODE" docs/flows/<slug>.md --certify
uv run --no-project python -B "$FLOW_SKILL/scripts/find_absent_cross_flow_seams.py" --project-root "$PROJECT" --list-residue
```

The default project root is the current directory; pass it explicitly when running
from a nested directory. Code paths default to the project root, and flow paths
to `docs/flows`. `--code-root`, `--flows-root` and `--root` customize these without
copying a skill. A missing input is an unmet prerequisite, never a clean check.

**Scope of automation:** symbol indexing and comment token checks support Python.
The documentation method applies elsewhere, but do not claim automated symbol
coverage for another language. The AST index cannot establish dynamic dispatch,
instance attributes, runtime configuration or whether a cited test proves a claim.

## A. Establish the boundary

1. Pin the current commit and record dirty files separately. Inspect prior flow
   documents and risk registers by symbol before assuming a subsystem is unmapped.
2. Declare owned output paths and source-read scope. Identify entry events,
   callers, persistence boundaries and neighboring flows. Record available code,
   tests, logs, configuration and event-capture evidence; name unavailable sources.
3. Trace scenarios from triggers through callers and branches. A directory inventory
   alone cannot reveal recovery, cancellation, stale data, retries or cached paths.
   Classify the trigger as main, alternative or edge, not the handler it reaches.
4. If the user requests parallel work, load
   `lemmi-ai-kit-orchestration:parallel-session-safety`, assign disjoint write sets
   and include host rules, read-only review rules and evidence requirements in every
   delegation brief. Otherwise work within the current session.

## B. Author judgments

Use local scenario IDs, stable dotted symbols and repository-relative file paths.
For each row, capture trigger, path, outcome and evidence. Mark PASS only for the
specific claim supported by available evidence. FAIL needs a concrete consequence;
UNKNOWN names the missing evidence and how to obtain it. Expand each UNKNOWN path
with precondition, per-step behavior, outcome and unresolved question.

Read both ends of every call edge and every cited test assertion. Record real
read status per file. Never generate "read in full" from a list of filenames.
Map runtime profiles from their actual configuration sources, not assumptions
about what a setting's default implies after deployment.

Read [evidence and closing rules](references/evidence-and-close.md) for citation
durability, cross-flow ownership, completeness sweeps and safe document retirement.

## C. Generate projections

Author scenarios, call edges, row order, evidence, read-status and invariants first.
Run `generate_flow_projections.py --section all` and apply its stdout selectively
to the corresponding tables. It has no write mode. Then run `--certify`.

| Column | Contract |
|---|---|
| Symbol index `scenarios`, `called by` | Derived set equality |
| Coverage `scenarios`, verdict distribution | Derived set equality |
| Runtime `unreachable scenarios` | Complement of authored `reachable scenarios` |
| Call graph `scenarios` | Authored subset of the applicable scenario closure; narrower subsets are legal |
| Symbol index `invariants`, legend `scenarios` | Authored; never overwrite with a guessed derivation |

Preserve authored invariant associations even when they exceed the invariant's
single anchor symbol. Keep same-named symbols in different files distinct. A
generator refusal requires fixing missing inputs, never fabricating read status.

## D. Reconcile neighbors and register findings

Resolve each cross-flow ID against the actual target row and read its trigger.
Check the return link; a document-level backpointer is weaker than an exact row
reference. Reconcile verdicts for the same mechanism across both documents: make
them agree, or explicitly assign verdict ownership in a row or register entry.
State the full symbol, both documents and the reason for that ownership.

Use the bundled register skeleton. Capture evidence and severity, then reconcile
by symbol against existing findings. Mapping does not authorize implementing fixes.
Run the register validator and, for a corpus, `--join docs/flows tasks` to check
that FAIL/UNKNOWN scenarios have a register destination.

Run the seam detector. It certifies itself against immutable synthetic fixtures
before scanning the project. Review every absent-link candidate, verdict
disagreement and suppressed-link candidate; a count is not a disposition. Put each
result in the owning register with this marker:

```markdown
- **Residue verdict:** seamed-at-row-level | real-gap-row-written | shared-entry-no-seam — <pair, full symbol and reason>
```

The detector's disagreement predicate is deliberately narrow (FAIL versus UNKNOWN);
it separately reports FAIL-versus-PASS blind spots. Its candidates do not establish
runtime reachability or require inventing a cross-flow link.

## E. Optional comment pass and onboarding trim

Perform these only when included in the user's scope. Comment cleanup uses
`lemmi-ai-kit-orchestration:initiative-cleanup` and its comment-pass reference;
report that prerequisite if absent. Retain ownership, invariant, consequence and
non-obvious intent comments. Remove narration only with a source-backed reason.

Run the token check from the project root (paths are root-relative):

```sh
uv run --no-project python -B "$FLOW_SKILL/scripts/verify_no_code_change.py" HEAD src/example.py
```

Missing-at-ref, parse errors and executable-token differences fail the check.
It is a token comparison, not proof of complete runtime equivalence; docstrings
can be runtime metadata. Run project checks appropriate to any edited source.

Before trimming old documentation, map every claim, identifier and number to a
surviving destination or an evidenced retirement. Resolve missing string matches
by concept before treating them as missing knowledge. Preserve untracked work
with a durable backup before removing it. Update inbound links too.

## F. Validate and close

Run these self-checks from any directory; they create disposable fixture projects
and never require the original repository:

```sh
uv run --no-project python -B "$FLOW_SKILL/scripts/validate_flow_map.py" --probe-stamps
uv run --no-project python -B "$FLOW_SKILL/scripts/validate_register.py" --probe-stamps
```

Then validate the real document, register and projections. Flow validation succeeds
with exit 0 and no findings; register exit 0 can include informational `[symbols]`
notes, which require manual resolution. Certify exit 0 permits legal subset notes.
Nonzero exits are unmet checks; capture the whole output and preserve the code.

Complete the evidence/coverage self-challenge in the reference. Re-read every
published claim against the final tree. Snapshot the relevant input set before and
after a check and rerun if it changed. A fresh shared-corpus edit can invalidate an
otherwise correct reconciliation within the same session.

Return output paths, pinned revision, evidence limits, actual gate results and
outstanding register IDs. Run Core's post-task-review for major mapping work.
Do not claim a structural pass proves runtime truth, commit/push without user
authorization, or leave actionable findings only in temporary session notes.
