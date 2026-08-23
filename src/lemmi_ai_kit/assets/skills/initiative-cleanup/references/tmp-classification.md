# `.ai/tmp/` classification — the detail behind SKILL.md Step 4c

`.ai/tmp/` is gitignored, so **nothing in it has history and nothing in it is
recoverable.** A sweep there is final. It holds two populations that look identical from the path.

| Population | Examples | Disposition |
|---|---|---|
| **Scratch** — this session produced it and could produce it again | gate captures, one-off scripts, intermediate JSON, diff dumps | Sweep |
| **INPUT / corpus** — production data pulled at a point in time | raw export dumps under a skill's own `raw/` tree, `logs/` (cloud downloads), transcript exports, any file a report's numbers were computed from | **NEVER sweep.** Upstream retention rolls, so it is **not regenerable** — re-running the query later returns a different (or empty) window |

## Two checks before removing anything from `.ai/tmp/`

```bash
# 1. Is it cited by a TRACKED file? If yes it is not scratch — a skill or report depends on it.
git grep -l '<the path or its parent dir>'
# 2. Could you regenerate it? If it came from a production query, a log export, or an API call
#    against data with retention, the answer is NO regardless of how temporary the path looks.
```

## Measured, twice

**(a)** `.ai/tmp/` was deleted mid-initiative and took **both the raw exports and every derived
artifact** — not in the Recycle Bin, unrecoverable, the measurement corpus had no copy anywhere.

**(b)** One measured inventory found `.ai/tmp/` holding **124 MB of `logs/`, a 4.4 MB corpus tree
of raw export data, and 36 data files over 200 KB — while 43 TRACKED files cited `.ai/tmp`
paths**, including the SKILL.md of a skill that *writes there by design*. A blanket sweep would
have destroyed the corpora and broken 43 live citations at once.

Re-measured days later: `.ai/tmp/` was **168 MB**, of which 124 MB `logs/` and the 4.4 MB corpus
tree are INPUT class, and **54 tracked files** cited paths inside it. The population grows; the
hazard does not shrink.

## Recommended structural fix — operator decision, not a default

Give the input class its own gitignored home that cleanup never touches — e.g. `.ai/corpora/` — and
leave `.ai/tmp/` as true scratch. That makes the disposition a property of the path again instead of
a judgment call per file.

It is not free: every skill that writes these paths (`analyze-logs` among them) and their
reference docs would need repointing, so it belongs in
its own change, not in a cleanup run. **Until that lands, `.ai/tmp/` is swept per file, never
wholesale.**
