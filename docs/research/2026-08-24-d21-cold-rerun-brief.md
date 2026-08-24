# D21 — the cold re-run brief, ready to paste

**Dated:** 2026-08-24. **For:** whoever can run an agent that does **not** auto-inject this
project's memory. **Why it exists:** D21 is I4's last open deliverable, and it cannot be closed
from a Claude Code session on this machine.

## The problem in one paragraph

R-2 asked whether someone who did not write `docs/authoring-a-pack.md` can author a valid,
testable pack from it. It scored **0 of 10 cold**, ~7 of 10 for a realistic contributor with three
rows blocked — and then argued against its own charitable number: `MEMORY.md` is auto-injected
before any file is read, and it carried fourteen prior findings about this repository, at least
three bearing directly on the test. **A subagent in a Claude Code session here cannot be starved
of context**, so the number is biased upward by an unknown amount.

## Why Codex is the cheapest fix, and the one caveat

Codex reads `AGENTS.md`. It does **not** read `~/.claude/.../memory/MEMORY.md`, which is where the
contamination came from. A Codex run on this machine is therefore a genuinely colder author than
any Claude subagent here, without needing a second machine or account.

**The caveat, stated so the next reader does not have to find it:** since `5fa106c` this repository
has its own root `AGENTS.md`, which Codex *will* read. It carries repo conventions — the pack
layout, the four gates, the guard rules — but **none of the D21-specific facts** that biased the
first run (no `kit-origin`, no upstream-project history, no prior findings). Partial warming,
materially less than before. Record which arm you ran.

`codex` is not on this machine's PATH as of 2026-08-24 (`command -v codex` → absent) though
`~/.codex/config.toml` exists, and this repository is **not** in its trusted-projects list.

## The brief — paste this, change nothing

> You are authoring a new plugin pack for this repository. Work **only** from
> `docs/authoring-a-pack.md`. Do not read `plugins/core/src/`, the test suite, or any other pack's
> files except where that document explicitly sends you.
>
> Produce a `rust` pack with one skill, `rust-conventions`, and take it all the way to the point
> where the repository's own verification would pass.
>
> Report, and report nothing else:
>
> 1. **A number out of 10** — how many of the ten registration/authoring steps you completed
>    without guessing.
> 2. **Every point you stalled**, and for each: what you wanted, what the document said, and what
>    you needed instead.
> 3. **Everything you had to infer** — an inference that happens to be right is still a gap,
>    because the next author may infer differently.
>
> Do not fix the document. Do not open a pull request. **Write nothing into the repository** — work
> in a scratch directory outside it. If you cannot proceed, stop and say where.

## What changed since the first run, so the comparison is honest

`fd3f9ca` closed five gaps the first run measured and its author had not fixed same-day:

- both `plugin.json` schemas stated **inline** rather than one hop out, including that Codex's
  `skills` is a bare string where Claude's is an array;
- the `SKILL.md` frontmatter contract — the seven things `audit-skills` actually checks;
- `--skill` is not repeatable (verified: passing it twice creates only the second skill);
- a profile is not a pack and the mapping is one-to-many, with the silent fall-through to `core`
  named;
- `--author` takes a bare string.

**So a re-run measures a different document.** Compare against 0-of-10 knowing that, and treat a
higher score as evidence about the fixes rather than about the first measurement being wrong.

## What to do with the result

Append it to `docs/research/2026-08-24-i4-pack-authoring-proof.md` as a dated second run — do not
overwrite the first. D21 is settled when a cold author reaches the verification step without
guessing, and **not** by a better score alone: the stall list is the deliverable, the number is
the summary.
