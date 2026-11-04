# Reading returns: what a note says about itself, and what a workflow's failures mean

A return can claim more than it has earned. Two cases are worth a check before you act on them.

## A status line, an "updated" time and a "nothing done yet" are claims

The session that wrote a note may have kept working after it did. Before you act on a status line,
a "last updated" time or a "nothing done yet", compare the note's file time with the newest file or
commit in the paths it owns and with the host's live-session list. A note older than the work it
describes is stale: say so, and correct it in place with a dated line, never by rewriting it.

## Read a workflow's failures before its findings

Read a workflow's failures before its findings. A run whose verifier stage did not finish returns
findings without verdicts: treat every finding as unverified, and verify the load-bearing ones
before you act on them.

Evidence level: preventive. Each case behind these two rules was caught by the reader before it
cost anything; neither was measured for frequency.
