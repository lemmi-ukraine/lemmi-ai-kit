# Limit recovery and wave sizing

Read this before you start or resume a wave of sub-agents, and when a usage limit stops one.

It adds to the usage preflight of [`SKILL.md` § 1b](../SKILL.md) and to "Resuming a worker" in the
[`agent-delegate` skill](../../agent-delegate/SKILL.md), and repeats neither. Each number below is a
starting value, uncalibrated, unless its sentence says it was observed: replace it with your own
measurement. None is a cap the kit sets; a project that states its own cap (§ 1b) uses that one.

## Size the wave in tokens

- **Size a wave in tokens, not agents, and state its cost shape before any wave.** The cost shape
  is the start cost times the number of agents, plus the work each one does, set against what is
  left of the window. A fresh sub-agent costs about 54K tokens of fixed context before it does
  anything (observed, 2026-11-04), and three fresh read-only sub-agents cost 363K to 479K tokens
  each over 30 to 37 minutes (observed, 2026-11-04). A spawned session's start cost is measured in
  [dispatch-economics § 4](../../initiative-planner/references/dispatch-economics.md).
- **Until you have measured your own, spend no more than about 4 M sub-agent tokens per 5-hour
  window per account (starting value, uncalibrated).** Every session on the account draws on the
  same window.
- **Reserve the verification budget first, then run builders no wider than the cap you derived
  ([`initiative-planner` step 4](../../initiative-planner/SKILL.md)) and verifiers in sub-waves.**
  Builders that start first spend the window the verifiers needed, and work that nobody verified
  cannot ship.
- **Pass an explicit `model` on every sub-agent call.** A sub-agent inherits its parent's model when
  the call names none, so a wave started from a session on a large model runs every mechanical row
  on that model and drains its bucket.

## Probe before you start or resume

- **Probe each model bucket with a one-word agent before you start or resume a wave.** Limits are
  per model, so one model can be stopped while another answers, and a probe costs one agent's start
  cost.
- **Trust the probe, not a printed reset time.** A limit printed a reset time that the bucket had
  already passed, and the one-word probe answered within minutes (observed once).

## When a limit stops the wave

- **Write the checkpoint's next wake condition before you wait.** A session stopped during the wait
  leaves its successor the one fact it needs, what it was waiting for
  ([worker preamble](../../agent-delegate/assets/worker-preamble.md), section 3).
- **On a printed reset time, a session arms a background waiter that exits at that time, and probes
  again when it wakes.** Its completion notice is what restarts the work: a session that ends its
  turn with nothing armed waits until someone types. A sub-agent is not restarted by a notice, so it
  stays in its turn instead ([runtime hazards](../../agent-delegate/references/runtime-hazards.md)).
- **A waiter that watches for a line anchors its pattern to the start of a line, and you run the
  pattern once on the present state and once on a planted positive before you rely on it.** On the
  present state it must say no and on the planted positive yes: a pattern that cannot match waits
  forever, and one that matches a quoted mention of the signal fires at once.
- **Read `date` at every wake-up and before every estimate, and give times to others from that
  reading.** After a stall the last plan can be hours stale: a session that waited out a limit found
  on waking that the clock had moved about 2.5 hours (observed, 2026-11-04), and with it its own
  estimates and the times it had given its peers.
- **Stopping a task can leave its child processes running, so list the ones you started and stop
  them before you go on.** An orphaned run keeps loading the machine, and a gate run beside it can
  fail for that reason alone. Never stop a process a peer started.
