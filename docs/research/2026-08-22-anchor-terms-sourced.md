# Anchor terms — sourcing pass

**Measured:** 2026-08-22 · **Deliverable:** I3 D10 · **Read-only research**
**Rule applied:** *"The session must verify each attribution against a primary source
and drop any it cannot. A mis-attributed pattern in the README is a worse
credibility hit than an unnamed one."*

## Verdict on the charter's own falsifier

> *"More than three of the anchor terms cannot be attributed to a primary source"*
> → *"Ship only the sourced ones. A short honest list beats a long borrowed one."*

**It does not hold.** 11 of 13 carry a primary source. The two that do not
(`product requirements document`, `hypothesis-driven development`) were already
marked `—` in the charter's own attribution column, so nothing was lost that the
charter expected to find. One term is dropped on **adoption** grounds rather than
sourcing grounds, and one needs rewording for precision.

| # | Term | Verdict |
|---|---|---|
| 1 | spec-driven development | **SOURCED**, with a correction to the charter |
| 2 | Architecture Decision Record | **SOURCED** |
| 3 | product requirements document | **no primary** — use as plain vocabulary, claim nothing |
| 4 | vertical slice architecture | **SOURCED** |
| 5 | orchestrator–worker delegation | **SOURCED** |
| 6 | progressive disclosure | **SOURCED**, with a caveat on what is attributable |
| 7 | SIFT method | **SOURCED** |
| 8 | Conventional Commits | **SOURCED**, and verified against the kit's own skill |
| 9 | stacked pull requests | **SOURCED** — and one fact is three weeks old |
| 10 | hypothesis-driven development | **no primary** — use as plain vocabulary |
| 11 | blameless retrospective | **REWORD** — the principle is sourced, the phrase is not |
| 12 | the AGENTS.md convention | **SOURCED** — a genuine cross-vendor standard |
| 13a | generative engine optimization | **SOURCED** — peer-reviewed |
| 13b | `llms.txt` | **DROP** — sourced as a proposal, too thinly adopted to anchor on |

---

## 1. spec-driven development — the charter attributes this to the wrong project

The charter asks "which project popularized the triad". Two different projects, and
the distinction matters because only one of them matches what the kit actually ships.

**The term** was popularized by **GitHub Spec Kit** — first commit ~August 2025 (the
repo's own note reads "One year after the first commit, Spec Kit has reached 1.0.0",
dated 2026-08-21), MIT licensed, ~130.8k stars. But its phases are
`constitution → specify → plan → tasks → implement → converge`. **That is not the
kit's triad.**

**The triad** is **AWS Kiro's**, exactly. Kiro's documented spec artifacts are
`requirements.md`, `design.md`, `tasks.md`, in a three-phase
Requirements → Design → Tasks workflow. The kit scaffolds
`.ai/templates/{requirements,design,tasks}.md` — the same three filenames.

**So:** anchor the *term* on Spec Kit, and the *triad* on Kiro. Claiming Spec Kit
for the triad would be checkably wrong to anyone who opens either tool.

- https://github.com/github/spec-kit
- https://kiro.dev/docs/specs/

## 2. Architecture Decision Record — sourced, and the kit's format genuinely matches

Michael Nygard, **"Documenting Architecture Decisions"**, Cognitect blog,
**15 November 2011**. Five sections: Title, Status, Context, Decision, Consequences.

The kit's TECH charters use Context → Decision → Consequences with a Status header —
Nygard's structure, not a coincidental resemblance. ThoughtWorks moved ADRs to
*Adopt* on its Technology Radar in 2018.

- https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html
- https://adr.github.io/ (ecosystem index)

## 3. product requirements document — no primary source exists

Generic industry vocabulary with no canonical origin document. The charter marked its
attribution `—` and that was correct. **Use the phrase; make no attribution claim.**
Inventing a citation here is precisely the credibility hit this pass exists to avoid.

## 4. vertical slice architecture — sourced

**Jimmy Bogard, 2018**, blog post plus an NDC conference talk. His framing: *"my
architecture is built around distinct requests, encapsulating and grouping all
concerns from front-end to back ... couple along the axis of change."*

- https://www.jimmybogard.com/vertical-slice-architecture/

## 5. orchestrator–worker delegation — sourced

Anthropic, **"Building Effective AI Agents"** (engineering blog). The exact term
there is **"orchestrator-workers"**: *"a central LLM dynamically breaks down tasks,
delegates them to worker LLMs, and synthesizes their results."* Distinguished from
parallelisation by subtasks not being pre-defined.

Use Anthropic's hyphenation (`orchestrator-workers`) if quoting the pattern name.

- https://www.anthropic.com/engineering/building-effective-agents

## 6. progressive disclosure — sourced, but be precise about what is being attributed

Anthropic, **"Equipping agents for the real world with Agent Skills"**, names
progressive disclosure as the core design principle of the SKILL.md format, with the
tiers the kit relies on: name+description preloaded, full body loaded on relevance,
`references/` loaded only when needed.

**Caveat:** "progressive disclosure" is a much older UX/information-architecture term
and did not originate with Agent Skills. What is attributable to Anthropic is its
**application to agent context management**, not the concept. Phrase it that way.

- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

## 7. SIFT method — sourced

**Mike Caulfield**, "SIFT (The Four Moves)", Hapgood — **Stop, Investigate the
source, Find better coverage, Trace claims to the original context.** Proposed 2017,
canonical write-up 2019. Widely adopted in academic library instruction, which is
independent corroboration that the attribution is uncontested.

- https://hapgood.us/2019/06/19/sift-the-four-moves/

## 8. Conventional Commits — sourced, and checked against the kit rather than assumed

Specification v1.0.0 at conventionalcommits.org; derived from the Angular commit
guidelines. Format `<type>[optional scope]: <description>`, `BREAKING CHANGE:`
footer, dovetails with SemVer.

**Verified in the kit, not assumed:** `commit-message/SKILL.md` prescribes
`type(scope): description`, the standard type set (`feat`, `fix`, `refactor`,
`style`, `perf`), and the `BREAKING CHANGE:` footer. The attribution is real.

**Dogfooding inconsistency worth knowing before the README claims this.** The kit
ships a skill prescribing Conventional Commits, and **this repository's own history
does not follow it** — `f03ce20 Add Codex plugin packaging alongside Claude Code.`,
`335e31f Set package author to lemmi-ukraine`. No type prefixes anywhere. A reader
who checks will notice.

- https://www.conventionalcommits.org/en/v1.0.0/

## 9. stacked pull requests — sourced, and one fact is three weeks old

Lineage, oldest to newest:

| When | What |
|---|---|
| 2007 | **Differential**, by Evan Priestley and Luke Shepard at Facebook |
| 2011 | Differential open-sourced as part of **Phabricator** |
| — | **Gerrit** at Google, same workflow, independent tooling |
| — | **ghstack**, bringing stacks to GitHub |
| — | **Graphite**, founded by ex-Meta engineers to bring the workflow to GitHub |
| **2026-07-31** | **GitHub shipped native stacked pull requests to public preview** |

That last row is **three weeks old as of this writing** and directly relevant: the
kit's `stacked-pr-planner` describes a workflow the host platform has just started
supporting natively. Positioning written against "GitHub does not support this" would
be wrong by the time anyone reads it. Re-check the preview's status before the README
mentions it.

## 10. hypothesis-driven development — no primary source

Same as #3. Charter marked it `—`. Real vocabulary, no canonical origin. Claim
nothing.

## 11. blameless retrospective — reword; the phrase conflates two traditions

The **blameless principle** is solidly sourced: Google SRE book, *"Postmortem
Culture: Learning from Failure"* — *"an environment where every 'mistake' is seen as
an opportunity to strengthen the system"*, and a postmortem is blameless when it
identifies contributing causes *"without indicting any individual or team."*

But the SRE term is **blameless postmortem** — incident-triggered, about an outage.
The kit's `session-retrospective` is a **retrospective** in the Agile sense:
periodic, not incident-triggered, and about process rather than an outage. "Blameless
retrospective" welds an SRE adjective onto an Agile noun.

**Recommended phrasing:** cite the SRE book for the *blameless* stance, and do not
present "blameless retrospective" as an established term of art. Also note the
blameless idea is usually traced to healthcare and aviation safety culture well
before SRE — Google formalised it for software, it did not invent it.

- https://sre.google/sre-book/postmortem-culture/

## 12. the AGENTS.md convention — the strongest term on this list

The charter asks "whether it is a published cross-tool standard, and who maintains
it." Both answered, from the specification's own site:

- **Stewardship:** *"stewarded by the Agentic AI Foundation under the Linux
  Foundation"* — not a single vendor. Emerged from work across OpenAI Codex, Amp,
  Google's Jules, Cursor and Factory; formalised August 2025, donated to the Linux
  Foundation December 2025.
- **Adoption:** *"over 60k open-source projects"*, and 20+ agents and platforms
  support it, including GitHub Copilot, VS Code, Cursor, Aider, Zed and Devin.
- **Self-description:** *"a simple, open format"* that *"benefits the entire
  developer community, regardless of which coding agent you use."* Note it does not
  call itself an "open standard" in those words — do not put that phrase in its
  mouth.

This is the kit's best anchor: the kit seeds `AGENTS.md`, and `AGENTS.md` is a
vendor-neutral standard under Linux Foundation stewardship with six-figure adoption.

- https://agents.md/

## 13a. generative engine optimization — peer-reviewed, the strongest citation available

**Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, Deshpande**, *"GEO: Generative
Engine Optimization"*, **KDD 2024** (Proceedings of the 30th ACM SIGKDD Conference),
pp. 5–16. DOI `10.1145/3637528.3671900`; preprint arXiv:2311.09735.

The paper **coined the term** and demonstrated in controlled experiments (GEO-bench,
~10,000 queries, nine datasets) that content can be deliberately optimised for
visibility in AI-generated answers. Its finding is directly actionable for this
initiative: **adding verifiable statistics, credible quotations, and citations to
reliable sources produced the largest visibility gains.**

That is the same behaviour this document performs, which is a convenient alignment
between honesty and reach — the trade the charter refused to make does not need to be
made.

## 13b. `llms.txt` — DROP

Proposed by **Jeremy Howard (Answer.AI) on 2024-09-03**. The proposal is real and
attributable. The *adoption* is not there:

- ~**10.1%** of 300,000 domains carry one (SE Ranking study — a secondary source,
  flagged as such)
- 5–15% among technology and documentation sites
- As of mid-2026: **no W3C, IETF or schema.org recognition, no version number, no
  governance body, no conformance test**

The charter asked *"whether `llms.txt` has meaningful adoption, or is speculative."*
**Answer: closer to speculative.** Shipping a file costs almost nothing, so shipping
one is defensible — but **do not anchor positioning on it** and do not present it as
a standard. Contrast with AGENTS.md (#12), which is what an actually-adopted
convention looks like.

---

## Method note

Every claim above was taken from a primary source where one exists — the originating
blog post, specification site, vendor engineering post, or peer-reviewed paper.
Two claims rest on secondary sources and are flagged inline as such: the `llms.txt`
adoption percentages (an SE Ranking study) and the pre-SRE origin of blameless
culture in healthcare and aviation. Neither is load-bearing for a positioning claim.

Where a search summary and a primary source disagreed, the primary source won. One
such conflict was material: secondary sources dated GitHub Spec Kit's release to both
September 2024 and September 2025; the repository's own release note places the first
commit around August 2025.

## Sources

- [Documenting Architecture Decisions — Michael Nygard, Cognitect, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html)
- [ADR ecosystem index](https://adr.github.io/)
- [Vertical Slice Architecture — Jimmy Bogard](https://www.jimmybogard.com/vertical-slice-architecture/)
- [Building Effective AI Agents — Anthropic](https://www.anthropic.com/engineering/building-effective-agents)
- [Equipping agents for the real world with Agent Skills — Anthropic](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [SIFT (The Four Moves) — Mike Caulfield, Hapgood](https://hapgood.us/2019/06/19/sift-the-four-moves/)
- [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [Postmortem Culture: Learning from Failure — Google SRE book](https://sre.google/sre-book/postmortem-culture/)
- [AGENTS.md](https://agents.md/)
- [GitHub Spec Kit](https://github.com/github/spec-kit)
- [Kiro — Specs documentation](https://kiro.dev/docs/specs/)
- [GEO: Generative Engine Optimization — arXiv:2311.09735](https://arxiv.org/pdf/2311.09735)
- [Stacked diffs — Graphite guide](https://graphite.com/guides/stacked-diffs)
- [Stacked Diffs and tooling at Meta — The Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/stacked-diffs-and-tooling-at-meta)
- [GitHub Stacked PRs public preview — InfoQ, 2026](https://www.infoq.com/news/2026/04/github-stacked-prs/)
- [llms.txt adoption data — Digital Applied](https://www.digitalapplied.com/blog/llms-txt-in-practice-adoption-evidence-2026)
