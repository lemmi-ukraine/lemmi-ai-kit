# Security Policy

## Reporting a vulnerability

Email **support@lemmi.io**. Do not open a public issue for a security report.

Include what you can: what an attacker can do, the file or skill involved, and
the steps to reproduce. A partial report is worth sending — a rough description
of a real problem beats a polished one that never arrives.

**What to expect.** This project is maintained by one team, so the honest
commitment is an acknowledgement within **5 business days** and a fix or a stated
decision not to fix within **30 days** of that acknowledgement. If you do not
hear back in 5 business days, assume the mail was lost and send it again rather
than assuming it was ignored. We will tell you when a fix ships, and credit you
unless you ask us not to.

Please give us a reasonable window before publishing. We will not pursue anyone
who reports in good faith.

## Supported versions

The kit is at `0.1.0` and pre-publication. Only the current `main` is supported;
there are no maintained release branches and no backports.

## Threat model — read this part

**This kit ships instructions that AI agents execute, and some of those
instructions run shell commands.** That makes the threat model different from a
normal library, and worth stating plainly rather than leaving implicit.

A skill is a markdown file an agent reads and follows. Some skills in this pack
ship scripts, and several instruct the agent to run commands — `git`, `ruff`,
`pytest`, a Python script over your session logs. An agent following a malicious
skill would run whatever that skill told it to, with whatever permissions the
agent has, in your repository, on your machine. There is no sandbox between a
skill and your working tree.

**In scope** — please report:

- A skill, script, or template in this repo that instructs an agent to exfiltrate
  data, run a destructive command, or reach a network endpoint it does not
  document.
- Anything in `kit-setup` or the support CLI that writes outside its declared
  target directory, or that overwrites a file it declared it would not touch.
- A path traversal or injection in `plugins/core/src/lemmi_ai_kit/` — particularly `scaffold`,
  which takes a caller-supplied target path.
- A skill that instructs an agent to weaken a security control (disable a check,
  commit a secret, bypass a review gate).
- A supply-chain problem in the plugin or marketplace manifests: a `source` or
  `path` that resolves somewhere unintended.
- A dependency in `pyproject.toml` with a known vulnerability that affects this
  package's actual use of it.

**Out of scope:**

- The general fact that AI agents execute code. That is the premise of the tool,
  not a vulnerability in it. Decide your own agent's permissions accordingly.
- A skill giving advice you disagree with, or advice that is simply wrong. That
  is a bug — open a public issue.
- Vulnerabilities in Claude Code, Codex, or any model provider. Report those to
  the vendor.
- Anything requiring an attacker who already has write access to your machine or
  to this repository.

## If you install this kit

Two things worth knowing, neither of them a vulnerability report:

1. **Review skills before trusting them**, particularly anything from a
   community pack rather than from this repo. `SKILL.md` is plain markdown and
   reading it is the whole audit.
2. **`kit-setup` writes to your project.** It writes `AGENTS.md`, `CLAUDE.md`,
   and `.ai/`, and it declares which files it owns versus which are yours. Run it
   in a clean working tree the first time, so `git diff` shows you exactly what
   it did.
