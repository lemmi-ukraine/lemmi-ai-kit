# Agent installation trials — 2026-09-14

Four real agent sessions installed and configured the kit in temporary projects.
All four met the nine mechanical installation checks. Manual review found one minor
error in generated project prose, so this is evidence of working installation and
preservation, **not a claim that generated documentation is error-free**.

## Observed time and result

| Client / project | Native installs returned by | Full agent session | Installation checks | Manual content review |
|---|---:|---:|---|---|
| Codex / empty repository | 76.5 s | 6m 00s | Pass | No finding in the reviewed generated blocks |
| Codex / existing Python project | 125.3 s | 7m 12s | Pass | No finding in the reviewed generated blocks |
| Claude / empty repository | 35.8 s | 2m 50s | Pass | No finding in the reviewed generated blocks |
| Claude / existing Python project | 42.6 s | 5m 25s | Pass | One minor lockfile explanation error |

Both time columns start at process launch. The first ends when the last required native
plugin-install command returns successfully; it does not imply project setup is complete.
The second includes detection, tool calls, generated-file edits, verification and the final
agent response. It excludes fixture preparation and the independent post-run assessment.
No manual rescue prompt was sent. Exact seconds and per-check results are in the
[measurement record](2026-09-14-agent-installation-results.json).

## What was exercised

- **Empty repository:** Core only; complete project AI scaffolding; unknown language,
  framework and application commands left explicit; no application scaffold created.
- **Existing Python project:** Core and Python; detect three commands from its README
  and tool dependencies from its manifest. Preserve the existing instruction blocks,
  both clients' settings, source/test files, three history files and a customized
  requirements template. Add missing kit files and clearly marked instruction sections.

Original-content preservation was exercised in the two existing-project fixtures;
the empty repositories had no project content to lose.

The evaluator checked nine conditions independently of the agents' completion claims:
required files, no copied skill trees, preserved original project content, correct project
enablement, no commit, complete native installation, installed/source byte equality,
unchanged source checkout, and no unrequested trial plugins. New-project outputs were
also inspected for invented application structure; generated detection blocks were read
against fixture evidence. The verifier accepted a good control fixture and rejected
missing files, lost rules, copied skills, wrong plugin selection and removed settings.

### The content finding

Claude's existing-project output said that an uncommitted lockfile means dependency
sync resolves fresh every time. Git tracking does not determine whether uv reuses a
local lockfile: an existing compatible lockfile retains its locked versions. This was
an inaccurate explanation, despite the successful installation and preserved files.
The generated test output was left unchanged so the finding remains auditable.
[uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/#upgrading-locked-package-versions).

## Conditions and limits

- **One run per client/scenario**, on macOS ARM64. Do not treat the table as a model
  ranking, average installation time or guarantee for another machine.
- Codex CLI 0.154.0 used the configured `gpt-6-astra` model at `xhigh`. Claude Code
  2.1.266 reported `claude-opus-5[1m]` as its CLI default. The model settings differ.
- Codex ignored user configuration for session startup but retained the configured model
  explicitly, with write access to its native configuration directory for trial registration.
  Claude loaded project/local settings and pre-approved the install helper commands.
  Neither run used a permission-bypass flag.
- The host was already authenticated, with Git, uv and Python available. Each case
  used a local source snapshot and a new temporary marketplace name. Remote cloning,
  client installation, first sign-in and clean-machine dependency downloads were not timed.
- Codex reported model-transport retries in both runs. Their delay remains in the
  wall-clock measurement; it was not attributed to the kit or subtracted.
- Tests used the exact README prompt, followed only by source/marketplace/project
  isolation instructions. The payload was from commit `c6e5185`; the README prompt was
  the proposed addition. Its SHA-256 is recorded alongside the results.
- No all-packs agent trial, legacy-copy migration, missing-runtime/authentication flow,
  Windows session or actual next-session MCP invocation was measured here. Earlier native
  packaging tests cover different questions and are not included in these timings.
- Preservation checks cover fixture project content. Host cleanup removed the trial
  registrations and restored the Codex configuration; original Claude plugin IDs were
  retained. A full before/after baseline of Claude user settings was not captured.

## Repeating the test

1. Freeze the README prompt and record its hash. Prepare one empty Git repository and
   one small existing project with protected instruction, configuration and history content.
2. Give each trial a source snapshot with a unique native marketplace name. Keep that
   checkout outside the project and preserve existing personal registrations.
3. Run a fresh non-interactive agent process. These trials used `codex exec --json`
   with workspace write/automatic approval and `claude --print --output-format stream-json`
   with edit permissions and approved installation commands. Retain normal authentication;
   do not copy credentials or replace HOME/CODEX_HOME to isolate a test.
4. Capture timestamped events and elapsed time outside the agent. Check native registries,
   payload hashes and project files after completion, then review detected facts manually.
   Keep failures and timeouts in the result set.
5. Save the resulting project, then remove trial plugins and marketplaces through the
   native clients. Remove only the fixture-specific trust entries and verify the original
   configuration is restored. Preserve evidence rather than active throwaway registrations.

The actual runner, verifier, baselines, transcripts and verified project snapshots were
kept in the session's temporary benchmark directory. They are local test artifacts, not
a new kit installer or a permanent benchmark service.
