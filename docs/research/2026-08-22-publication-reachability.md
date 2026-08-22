# Publication reachability and the traffic baseline

**Measured:** 2026-08-22 · **Deliverable:** I3 D9 · **Status:** settled, not estimated
**Charter:** `tasks/I3-FEATURE-oss-discoverability.md` (private planning artifact — not committed to this repository)

This is the baseline the charter said must exist before any discoverability claim
is made. It came back as a finding rather than a number.

## 1. The repository is private

The program document's header says
`https://github.com/lemmi-ukraine/lemmi-ai-kit (already public)`. **That is false.**
Three independent measurements, two of them reproduced by a second session:

| Probe | Result | Reads as |
|---|---|---|
| `curl https://api.github.com/repos/lemmi-ukraine/lemmi-ai-kit` | `404 Not Found` | absent **or** private — unauthenticated GitHub returns 404 for both |
| `curl https://api.github.com/orgs/lemmi-ukraine/repos` | `200`, empty array | the org has **zero** public repos |
| `GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote <url>` | `fatal: could not read Username` | **decisive** — a public repo never asks for credentials |
| `curl https://api.github.com/users/lemmi-ukraine` | `200`, org id `92667741` | the owner exists and is public; only the repo is not |
| `curl https://api.github.com/rate_limit` | `51/60` remaining | the 404 is not a rate-limit artifact |

The same `ls-remote` **succeeds** with credential helpers enabled, because Git
Credential Manager supplies the operator's stored credentials. Any check that does
not disable the helper will wrongly conclude the repo is public. That is most
likely how the original claim was made.

**Operator decision, 2026-08-22:** the repository goes public in approximately one
week (≈2026-08-29).

## 2. Consequences

**The baseline is structurally zero, not UNKNOWN.** A private repo has no public
traffic, no search presence, and no marketplace reach. The charter's metric is not
unmeasured; it is definitionally nil until the flip. `gh api …/traffic/views`
would return the operator's own clones, and `gh` is not authenticated in this
environment in any case.

**One of the charter's own falsifiers therefore fires:**

> *"Baseline traffic is effectively zero **and** GitHub search does not surface the
> repo for any candidate term"* → *"The binding constraint is distribution, not
> on-page content."*

It holds today, definitionally. It **stops holding at the flip**, which is why the
anchor-term sourcing pass (D10) was kept in scope rather than deferred: the
constraint is about to be removed on a known date.

**Neither plugin marketplace can install today.** `plugin marketplace add
lemmi-ukraine/lemmi-ai-kit` requires read access to the repo. This is a *third*
independent blocker on the install path, and it is worth separating from the other
two because fixing any one leaves the others standing:

| # | Blocker | Clears at the flip? |
|---|---|---|
| 1 | **Schema** — can one repo serve N plugins? | N/A — verified against both vendors' docs and three production marketplaces. Stands. |
| 2 | **Reachability** — a private repo is unreadable to `marketplace add` | **Yes**, automatically |
| 3 | **Codex `source.path`** — `.agents/plugins/marketplace.json` uses `"path": "./"`, the marketplace root, where Codex requires a concrete plugin subdirectory | **No** |

So I4's Gate C is **untested, not passed**: it was verified against vendor
documentation, never against this repository. Blocker 3 has never been
*observable*, because blocker 2 sits in front of it. It is reproducible today
against a **local** path source, which exercises the schema with no network and no
auth — that is the check to run, not `marketplace add` against the remote.

## 3. A time-boxed action that will otherwise be missed silently

**The GitHub traffic API retains 14 days.** The baseline this charter requires must
be captured **on the flip date**, not after:

```bash
gh api repos/lemmi-ukraine/lemmi-ai-kit                        # stars, forks, watchers at t=0
gh api repos/lemmi-ukraine/lemmi-ai-kit/traffic/views          # requires push access
gh api repos/lemmi-ukraine/lemmi-ai-kit/traffic/popular/paths
```

Miss the window and "did discoverability work?" becomes permanently unanswerable —
which is the original defect this initiative exists to fix. **Nobody currently owns
this.** It needs an owner on 2026-08-29.

## 4. What the marketplace surface looks like today

Relevant to the charter's marketplace-vs-README falsifier, which **cannot be
tested** while the repo is private — no referrer data exists. What is inspectable
statically:

- `.claude-plugin/marketplace.json` carries a `description`; the Codex marketplace
  entry in `.agents/plugins/marketplace.json` carries **none**.
- No marketplace surface links back to a README or docs entry point.
- Both plugin descriptions advertise **"30+ skills"**, which is false at 29 after
  I1 — not merely imprecise.

The falsifier stays open. Re-test after the flip, when referrer paths exist.
