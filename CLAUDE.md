# CLAUDE.md
@AGENTS.md

## Skills

### User-Invocable (use with `/skill-name`)
- `/lemmi-ai-kit-core:kit-setup` — Seed or refresh project-owned AGENTS.md/CLAUDE.md/.ai files from plugin templates, placeholders filled from the detected project
- `/lemmi-ai-kit-core:commit-message` — Generate conventional commit messages from the working diff
- `/lemmi-ai-kit-core:branch-switch` — Safely stash, switch branch, and re-apply with conflict detection
- `/lemmi-ai-kit-core:spec-driven-dev` — Spec-driven development pipeline with task-size detection and requirements/design/tasks/verification gates
- `/lemmi-ai-kit-core:test-planner` — Derive a verification plan from an approved spec: conditions by id, one owning test level per case, a verification method per NFR
- `/lemmi-ai-kit-core:post-task-review` — 8-step post-task review: code review, documentation impact, learnings extraction
- `/lemmi-ai-kit-core:learning-consolidator` — Periodically drain .ai/learnings.md intake into rules, skills, READMEs, and comments
- `/lemmi-ai-kit-core:session-retrospective` — Analyze Claude Code session history for behavioral patterns and workflow friction
- `/lemmi-ai-kit-core:product-brief` — Shape a product idea into a team-readable task brief with assumption challenges and UX content
- `/lemmi-ai-kit-core:skill-creator` — Interactive guide for building new Claude Code skills
- `/lemmi-ai-kit-core:skill-creation-workflow` — Research-backed skill creation pipeline (research, build, structural and content review)
- `/lemmi-ai-kit-core:skill-reviewer` — Audit skills against the Agent Skills spec and determine workflow placement
- `/lemmi-ai-kit-core:research-source-planner` — Build a deduplicated, single-owner source manifest before parallel research
- `/lemmi-ai-kit-core:research-source-claim` — Consumer protocol for fan-out agents: work only your assigned manifest sources
- `/lemmi-ai-kit-core:parallel-deep-research` — One-command parallel deep research with disjoint source ownership and a cited report
- `/lemmi-ai-kit-core:orchestrate` — Orchestrator mode: decompose, delegate to native/external workers (codex, cursor-agent, grok), verify, synthesize
- `/lemmi-ai-kit-core:agent-delegate` — Delegate one scoped, verified task to a named worker (codex, cursor, grok, deep-reasoner, fast-worker)
- `/lemmi-ai-kit-core:scout-review` — DoorDash-style three-stage review: cheap lead scout, strong deep reviewers, adversarial disprove-it pass (fable or opus combo)
- `/lemmi-ai-kit-core:initiative-cleanup` — Retire a finished initiative's artifacts safely: per-file partition and exhaustiveness census, artifact-kind classification, evidence and reference gates before any delete, and a self-review gate
- `/lemmi-ai-kit-core:branch-diff-review` — Review a branch's committed diff against its base and emit a findings report: gates with exit codes and scope, explicit not-reviewed section, and per-finding verification that bans re-rating from judgment
- `/lemmi-ai-kit-core:pr-comment-resolver` — Resolve reviewer comments in the layer that owns the code: per-thread verdict, owning-layer lookup by introducing commit, backup tags and preflight before any authorized cascade
- `/lemmi-ai-kit-core:pr-review-concise` — Adversarially review a pull request under an enforced comment-length budget: severity-labelled inline findings routed to the PR that owns the code, posted in one atomic call
- `/lemmi-ai-kit-core:initiative-planner` — Plan a multi-session initiative before work starts: level-1 charter (PDR or ADR), typed session decomposition, derived concurrency, capability-tier routing, and the operator-only blockers
- `/lemmi-ai-kit-core:stacked-pr-planner` — Plan branch/PR topology before the first commit: classify each deliverable by risk class and review lane, assign it to exactly one layer, emit a checkable layer table with re-plan triggers
- `/lemmi-ai-kit-core:analyze-logs` — Root-cause analysis from structured or plain application logs — platform examples are GCP and Docker, the method is not — with task file creation

### Auto-Loaded by Claude (background knowledge)
- ai-docs-lookup — Fetch official AI provider docs before answering questions about model internals
- parallel-session-safety — One-tree/many-writers coordination: file-ownership partitioning, shared-artifact collisions, verify-don't-reapply, and why a suite verdict is untrustworthy in a contended checkout
- python-conventions — Python coding conventions (one class per file, typed models, DI at boundaries)
- vertical-slice — Vertical slice architecture patterns for feature-oriented codebases
- test-conventions — Testing conventions: integration-first, DI-based mocking, timeout decorators

### Internal Pipeline Skills (invoked by workflows or directly by the model; hidden from the `/` menu)
- plan-critic — Self-review specs and plans for gaps before presenting them
- task-learnings — Extract and record project learnings after task completion
- ai-changelog — Append structured entries to the AI infrastructure changelog
- consolidation-critic — Adversarial gate on a consolidation plan before it executes: challenges every promotion, archive and new-skill proposal, and audits that no drained entry lost its knowledge
- hypothesis-validator — Close the improvement-hypothesis loop: window guardrail, evidence for and against, CONFIRMED/REFUTED/INCONCLUSIVE/SUPERSEDED verdicts, archive rotation and meta-synthesis
- ai-improvement-tracker — Record testable improvement hypotheses for AI infrastructure changes
- skill-researcher — Deep domain research producing a brief for skill creation
- skill-content-reviewer — Verify skill content quality against its research brief
