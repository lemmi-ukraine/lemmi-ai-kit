# Findings Report Format

Destination: `tasks/TECH-<slug>-review.md`. Five predecessors already use that name; this file gives
them the format they never shared.

**Why the format matters more than the findings.** Those five are cited by **30+ other files** —
feature READMEs, specs, task docs, handoff briefs. (Measured three times on one task at 22, 32, and 84
depending on whether local backup copies and the initiative's own artifacts were excluded, which is
the lesson: **write the measurement command beside any count**, per verification item A5.) So the
failure mode is not that a report goes unread — it is **citation outliving verification**: a claim
written at peak alarm gets quoted for months after the code moved. Every required section below exists
to make a stale claim detectable.

---

## Required sections (eight)

### 1. Header — what was reviewed, against what

```markdown
# TECH — <subject> review

**Reviewed:** committed diff of `<branch>` against `<base>`
**Base (merge-base):** `<sha>` · **`<base>` at review time:** `<sha>` · **branch HEAD:** `<sha>`
**Base drift during review:** `git log --oneline HEAD..origin/<base> | wc -l` → N commits
**Date:** YYYY-MM-DD · **Input:** `git diff <base>...HEAD` (committed only; local uncommitted work excluded)
```

Three SHAs, not one — a reader six weeks later needs to know whether the anchors still mean anything,
and branch HEAD alone cannot tell them. Base drift is recorded *and assessed*: in the source run the
base advanced from one OID to another mid-review, which is what makes three-dot mandatory.

### 2. Gates — with exit codes AND scope

The most valuable line in the source report was an admission:

```markdown
**Gates run:** `.venv/Scripts/ruff.exe check backend` → exit 0, "All checks passed!" ·
`basedpyright <paths>` → exit 0, 0 errors.
**pytest was NOT run** — no test verdict in this document is an executed result.
```

- **Scope is part of the result.** `ruff check backend` exits 0 while `ruff check backend tests` exits
  1 on pre-existing violations. A gate name without its scope is not a result.
- **Name the gates that did NOT run.** Silence reads as "passed" to every later reader.
- A gate whose output you did not read is `UNREAD`, never `passed` — including one exiting 1 for
  reasons in files you did not touch. Attribute by filename and say so.

### 3. Coverage — what was reviewed

Referenced by `SKILL.md` § Step 6 and required even on an empty report. Adapted from
`pr-review-concise` step 6, which is where these fields exist in template form:

```markdown
**Coverage:** N files / M commits · axes: conventions · correctness · concurrency · retention ·
observability · deploy-reachability · tests
**Checked for:** <named classes you actively swept, with the pattern and its scope>
**Not checked:** <see § 4>
```

### 4. What was NOT reviewed

Mandatory and falsifiable: specs skimmed not audited, tests checked for structure but not assertion
soundness, subsystems out of scope. This is the main defence against a reviewer under-reporting to
close a task faster — **an empty "not reviewed" section on a large diff is itself a finding.**

### 5. Findings table

```markdown
| ID | Severity | Confidence | Disposition | Finding | Owning branch |
|---|---|---|---|---|---|
| F1 | Blocker | CONFIRMED | open | one-line claim | branch-a |
```

- **Severity:** `Blocker` / `Major` / `Minor` / `Question` — the vocabulary
  `plan-critic/references/finding-format.md` defines. **Vocabulary only; the required actions are
  defined here, not there** (plan-critic's actions target a plan document, not a code review).
  `Question` = missing clarity that blocks progress; file uncertainty there, not as a weak defect.
- **Mapping from the older scale.** Predecessor docs and the source run use
  Critical/High/Medium/Low/Note. `Critical`→`Blocker`; `High`→`Major`; **`Medium`→`Major`** (which
  *tightens* the gate — Medium findings now block completion, a deliberate change from spec D1, so say
  so if you carry one); `Low`/`Note`→`Minor`. Nothing maps below `Minor`: a genuine Note still gets a
  row, because under-reporting is this format's declared failure mode.
- **Confidence:** `CONFIRMED` / `PLAUSIBLE`, matching the `ReportFindings` tool's `verdict`. Separate
  axis on purpose — "is it real" must not be absorbed into "how bad". Part B verification items cap
  confidence at `PLAUSIBLE` and may not move severity at all.
- **Disposition:** `open` / `fixed` / `task-doc'd <path>` / `accepted: <reason>` / `retracted: <why>`,
  matching `ReportFindings.outcome`. Without this column a reader cannot tell whether F1 was fixed,
  accepted, or is still live — the exact "citation outliving verification" failure above. Only the
  operator may set `accepted` on a Blocker or Major.
- **Owning branch** is required whenever sibling branches exist; `unresolved` is legitimate and means
  no fix may be routed yet.

### 6. Per-finding detail

Defect → mechanism → fix → trade-off, plus the verification rows from `finding-verification.md`.
Each finding carries:

- **Anchor:** `file:symbol` **plus the quoted code it rests on**, re-grepped at write time. A finding
  with no quotable anchor is a `Question`, not a defect (`pr-review-concise` step 5).
- **`OBSERVED:` / `INFERRED:`** on every load-bearing statement. An `INFERRED` line never carries a
  recommendation without **naming the test that would falsify it**. These fields live here because
  `pr-review-concise` scopes them to "the summary body and the operator report" — surfaces that do not
  exist when there is no PR.
- **Depth by lane, not uniform** (`pr-review-concise` step 4): a migration, a security hook, and a
  docs change in one branch do not get equal attention. State the depth allocated per lane, or a
  migration silently receives board-row scrutiny.

State the trade-off even when the fix looks obvious. The source run's top finding had one worth naming:
skipping finalization on eviction risks stranding a session at `IN_PROGRESS`, which is the better
failure than writing a terminal status over a live one — a reader who cannot see that comparison will
"fix" it back.

### 7. Corrections log

Every finding downgraded, retracted, escalated, or reframed, **with the Part A output that moved it**.

```markdown
- F8 — Major → Minor. A1: trigger not constructible; `grep -n "_record_failure"` shows only a logger
  call and a counter increment, neither of which raises. confidence=PLAUSIBLE.
- F1 — Major → Blocker. Re-verified at <sha>: a peer commit removed the mitigation this finding
  relied on. Escalation driven by re-resolution (Part A), not reconsideration.
```

A severity change with no recorded output is the banned re-rating and must not appear here.

**An operator's live answer is a THIRD mechanism, and it needs its own dated section.** This log is
built for Part A/B tool-grounded reconsideration — *"the Part A output that moved it"*. A direct
operator answer is neither a tool output nor self-reconsideration; it is a distinct, always-
authoritative source that the severity rules already name (*only the operator may set `accepted` on a
Blocker or Major*) without ever giving it a place to be recorded.

Editing the findings table and detail sections in place to match such an answer, with nothing marking
**where** the resolution came from, looks identical to a finding that was Minor/accepted from the
first draft — which is precisely the "citation outliving verification" failure this whole format
exists to prevent, moved one layer up.

So when an open finding is resolved by a live, timestamped operator answer *after* the report already
exists:

1. Add a dedicated dated **`## Operator decisions`** section naming the question asked, the answer
   given, and which findings it changed.
2. Update the findings table and detail headers to match.
3. Add a Corrections-log line whose mechanism is explicitly **`operator input`**, distinguishing it
   from Part A/B.

Measured: a report shipped with two open findings (an unverified "no new breakage" claim, and a
Question awaiting another team's reply). Asked directly, the operator accepted the first's evidence
and supplied a fact that settled the second outright — moving it from Question to Minor. Both
changes would otherwise have been indistinguishable from original drafting.

**Never let a post-hoc operator answer overwrite a finding's history silently.**

### 8. What was good (do not delete this section)

Code review "is less about defects than expected" — its larger value is change understanding and
knowledge transfer (Bacchelli & Bird, ICSE 2013, verified verbatim at the paper). A pure defect list
deletes the part that tells the next reader which properties are load-bearing and must not be undone by
a later fix.

---

## Re-reviewing the same branch

The destination path is deterministic, so a second run **overwrites** — destroying the corrections log,
the most trustworthy part of the report. On a re-review, keep the file and tag every finding with a
baseline state, borrowed from SARIF: `new` · `unchanged` · `updated` · `absent` · `reintroduced`.
`absent` and `reintroduced` are the two a fresh run cannot express and the two that matter most after
fixes land.

## Optional but recommended

- **§ 0 blocker** — anything that must be settled *before* any fix (unresolved branch topology, a
  pending decision) goes above the findings. Routing that ignores it duplicates or loses work.
- **Commit sequence** — `git log --oneline <base>..HEAD`. A three-dot diff hides a migration added then
  reverted inside the branch; the sequence is a surface a squashed PR view does not have.
- **Tracking status** — whether the report itself is committed. Two of five predecessors have zero
  commits.

## Redaction

`tasks/` is tracked and pushed; the report enters git history permanently. Cite `file:symbol` and
describe shapes. Never paste credentials, tokens, account identifiers, emails, or raw log payloads —
account identifiers are already exposed in the history of pushed branches in this repo.

## The empty report

A review that found nothing still writes all eight sections: header, gates with exit codes, coverage,
not-reviewed, an empty findings table, no per-finding detail, no corrections, and what was good. That is
a complete result recording real coverage. **A missing report is not the same thing as a clean one.**

## Note on the worked example

`tasks/TECH-interview-stabilization-review.md` is the run this format generalises from and is worth
reading for its header and its corrections discipline — but it **predates this format** and does not
conform: it uses the older Critical/High severity scale, has no Confidence or Disposition columns, and
folds corrections inline rather than into § 7. Read it for shape, not as a template.
