# Definition of Ready (DoR) Pre-Flight Tables

Answer each verification question with evidence from the document — "Yes (evidence)", "No", or "Unknown". Any "No" or "Unknown" becomes a finding with the pre-assigned severity.

## Requirements DoR Table

Apply when reviewing `requirements.md` or `spec.md`:

| Verification question | If "No" or "Unknown" | Severity |
|-----------------------|---------------------|----------|
| Does the problem statement explain *why* with measurable impact or user pain? | Completeness — problem rationale missing | Major |
| Are all actors identified (who initiates, who is affected)? | Completeness — actors undefined | Major |
| Do all acceptance scenarios use a valid format — either Gherkin (User Stories with Given/When/Then) OR Use Cases (Main Success Scenario + at least one Exception Flow)? | No verifiable criteria — plan cannot be tested | Blocker |
| Does every acceptance scenario have adversarial coverage — Gherkin error Scenarios OR Use Case Exception Flows? | Missing adversarial coverage | Major |
| Are AI-specific behaviors specified where the feature involves AI model interaction? | Missing AI failure contract | Major |
| Can a test be written for each scenario or use case step independently? | Criteria are not independently verifiable | Major |
| Do NFRs have quantifiable targets (no adjectives: "fast", "properly", "good")? | Vague non-functional requirements | Minor |
| Are scope boundaries explicit — both in-scope deliverables and out-of-scope exclusions? | Scope ambiguity | Minor |
| Are dependencies and constraints identified? | Implicit assumptions | Minor |

## Design/Plan DoR Table

Apply when reviewing `design.md`, `spec.md` (combined), or a Cursor plan:

| Verification question | If "No" or "Unknown" | Severity |
|-----------------------|---------------------|----------|
| Does every Gherkin scenario or Use Case (main flow + alternatives + exceptions) map to at least one implementation task? | Orphan requirements — untraceable to work | Major |
| Does the risk assessment cover AI-specific risks where the feature involves AI? | Missing AI failure modes in risk model | Major |
| Is there a rollback strategy for schema changes or API contract changes? | Missing rollback path | Major (if DB/API touched) |
| Does the testing strategy cover scenario-level or use-case-step verification? | Untestable plan | Major |
| Are the files to create and files to modify explicitly listed? | Implicit scope | Minor |
| Are external AI service integration points documented with their failure modes? | Missing failure contract at AI boundary | Major |

## Verification DoR Table

Apply when reviewing `test-cases.md` or `test-plan.md`. Pair it with Dimension 6.

| Verification question | If "No" or "Unknown" | Severity |
|-----------------------|---------------------|----------|
| Does every expected result cite the `AC-`/`UC-`/`NFR-` id or design contract it derives from? | Ungrounded assertions — the document encodes invented expectations that read as specific | Blocker |
| Does every cited id actually exist in `requirements.md`? (verify by grep, not by reading) | Fabricated citation — traceability is decorative | Blocker |
| Does every case have exactly one owning level? | Duplicate coverage — same assertion maintained at several levels, no authoritative failure | Major |
| Does every condition name the design technique used to expand it? | Arbitrary case count — coverage that looks systematic and is not | Major |
| Does every NFR have a verification method (`automated`/`observability`/`manual`/`accepted-unverified`)? | Unverifiable non-functional requirement | Major |
| Is any test category the project's conventions ban assigned `automated`? | Plan produces work that must be deleted on sight | Major |
| Is every `TC-` owned by an implementing task or a named out-of-scope party? | Planned verification nobody will perform | Major |
| Does every task's `Test requirements` field cite `TC-` ids rather than prose? | Reconciliation incomplete — the two parallel documents never met | Major |
| Is deliberate non-coverage stated with risk bands and rationale? | Silent gaps indistinguishable from oversights | Major |
| Are risk bands taken from `design.md`'s existing Likelihood/Impact scores? | Two competing risk models in one spec | Major |
| Is any Given/When/Then text copied from `requirements.md` rather than cited? | Second source of truth; drifts on first edit | Major |
| Are upward level moves justified and excluded levels named? | Level drift toward slow, brittle high-level tests | Minor |
