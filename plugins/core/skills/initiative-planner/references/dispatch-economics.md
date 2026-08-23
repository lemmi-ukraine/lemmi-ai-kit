# Dispatch economics — execution mode, tool grants, nesting, launch cost

Detail for `SKILL.md` step 5. The step keeps the decisions; this file keeps the evidence.

Run-time launch mechanics (flags, stdin, path handling, validation) belong to `orchestrate` §2a —
not here.

---

## 1. Execution mode — the axis that is NOT "does it need review"

Every session is **unattended** or **operator-driven**. The dividing line is **write access to the
shared tree**, not judgement density and not whether the output gets reviewed:

- A one-line edit to a shared file needs no review and is still **unsafe unattended** — it collides.
- A judgement-heavy read-only analysis is **safe unattended** and still gets fully checked afterwards.

Getting this backwards routes by the wrong property. In the 2026-08-15 plan the split was **10
unattended / 13 operator-driven of 28**, in a tree carrying **341 untracked + 17 modified** files
from other sessions — that contention, not the difficulty of the work, is what decided it.

Operator-driven is also the default for anything that must **stop at a gate**: a session that needs
an approval mid-flight cannot run unattended, because there is nobody to approve.

## 2. Enforce constraints by tool grant, not by instruction

A withheld tool cannot be used; an instruction can be forgotten. The measured base rate in this repo
is **5 of 6 audited sub-agents violating a stated rule** in one window. So encode the constraint in
`--allowedTools`:

- **Withhold `Agent`** from every session that should not fan out.
- **Withhold `Bash(git commit *)`, `Bash(git push *)`, `Bash(git checkout *)`, `Bash(git stash *)`**
  from every unattended session. They produce artifacts; branch state stays with the operator.
- Grant the narrowest form that works — `Bash(python *)`, not `Bash`.

> **`--allowedTools` is not validated for you.** A malformed rule silently matches nothing rather
> than erroring. Validate a launch table before dispatch with the sentinel-flag trick in
> `orchestrate` §2a — and note its limit: it proves flag names and syntax, not `--model` values.

## 3. Nesting is allowed only where fan-out earns it

Documented limits: **3 layers** deep by default (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), **20**
concurrent (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`).

The limit that matters is not the platform's, it is **verification distance**: a summary of a summary
cannot be checked against its sources. In the 2026-08-15 plan exactly **1 of 10** unattended sessions
was granted `Agent`, and only because it worked a multi-source manifest. The other nine each worked
one corpus, one branch diff, or one file to write.

## 4. Per-launch context cost

A spawned session pays for its whole startup context **before it does any work**, billed as cache
*creation* — so it is paid again by every session and shared by none.

**Measured 2026-08-15, this repo, CLI 2.1.224, 43 skills.** Metric is `cache_creation + cache_read`,
because `cache_creation` alone is cache-state dependent and varied **2.2× between two identical
runs** (a cold run reported 62,653 / 0; the warm repeat reported 28,773 / 33,878 — same total).

| Launch | total context | vs full | cost |
|---|---|---|---|
| full context, `--model sonnet` | 82,966 | baseline | $0.50 |
| full context, `--model opus` | 71,588 | −13.7% | **$0.72** |
| `--exclude-dynamic-system-prompt-sections` | 82,888 | −0.1% | $0.51 |
| cwd with no `CLAUDE.md` | 61,192 | −26.2% | $0.18 |
| ↑ plus `--append-system-prompt-file` preamble | 62,651 | −24.5% | $0.18 |
| ↑ plus `--add-dir` back to the repo | 62,684 | −24.4% | **$0.19** |

Component costs isolated: the preamble adds **+1,459 tokens** (matching its file size), `--add-dir`
adds **+33** — so a spawned session can reach the whole repo without paying for its context.

**Four things this decides, none of them obvious:**

1. **Startup differs by model, and context and cost move in opposite directions.** Opus loads 13.7%
   *less* context and costs 43% *more*. A fan-out costed at one model's rate is wrong: the 2026-08-15
   plan's ten sessions (7 opus + 3 sonnet) cost **$6.51**, not the **$5.01** an all-sonnet estimate
   predicted.
2. **Cost falls faster than context** (−24% context, −62% cost) because cache *creation* is billed
   far above cache *read*. The lever is moving tokens from creation to read, not just deleting them.
3. **`--exclude-dynamic-system-prompt-sections` is not a cost lever.** Measured −0.1%, and cost went
   *up*. Its own help text says it *relocates* per-machine sections into the first user message to
   improve cross-user cache reuse — a benefit a single-session test cannot observe. Treat its
   cross-run effect as UNMEASURED rather than absent.
4. **`--bare` is unavailable on subscription auth.** `--help`: *"Anthropic auth is strictly
   `ANTHROPIC_API_KEY` or `apiKeyHelper`"*. Any plan whose economics depend on `--bare` is assuming
   API billing — say so explicitly rather than costing it as free.

**Re-measure rather than cite this table.** It grows with every skill and rule added, which is why
the number lives beside its command:

```bash
claude -p "Reply with exactly: CONTRACT-OK" --model sonnet --permission-mode dontAsk \
  --allowedTools "Read" --output-format json < /dev/null
```

The decision rule survives the number: **if startup context exceeds the useful work by more than
about an order of magnitude, route that session to a reduced-context launch** (a working directory
without `CLAUDE.md`, plus `--add-dir` for repo access and the host-rule preamble for the rules that
directory no longer supplies). Budget the fan-out before approving it.
