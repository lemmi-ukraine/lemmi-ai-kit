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


## Why this needs a rule rather than judgement

Both populations have been lost this way. A scratch directory deleted mid-initiative took the raw
inputs **and** every artifact derived from them — nothing in a gitignored tree is in the recycle
bin, and the inputs were no longer regenerable because the upstream window had rolled. Separately, a
blanket sweep was proposed against a tree that tracked files were actively citing, which would have
broken those citations at the same time.

The shape to remember: **the population that must never be swept grows over time, and the hazard
does not shrink.** Sweeping per file is the safe default until the two populations live at different
paths.

## Structural fix — operator decision, not a default

Give the input class its own gitignored home that cleanup never touches, and leave the scratch tree
as true scratch. That makes disposition a property of the path again instead of a judgement call per
file.

It is not free: every skill that writes these paths, and their reference docs, need repointing, so
it belongs in its own change rather than inside a cleanup run. **Until that lands, sweep per file,
never wholesale.**
