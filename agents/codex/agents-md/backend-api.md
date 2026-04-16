# Governed AI Delivery — Codex Agent Instructions

These instructions are mandatory. Codex operates as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Codex operates aligned to:

- Product specifications under `features/`
- Architecture contracts under `docs/backend/architecture/`
- Evaluation standards under `docs/backend/evaluation/`
- Governance rules under `governance/`

Before planning or generating code:

- Read all files under `docs/backend/architecture/`
- Read `docs/backend/evaluation/eval_criteria.md`
- Apply architecture, testing, technology, and evaluation contracts as binding constraints
- Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## Mandatory Feature Structure

Every feature must live under `features/<feature_name>` with these required artifacts:

- `acceptance.feature`
- `nfrs.md`
- `eval_criteria.yaml`
- `plan.md`
- `architecture_preflight.md`

Implementation must not begin unless all five artifacts exist.

Before proceeding to Architecture Preflight or planning:

- If `nfrs.md` contains TBD entries in any category, stop and request completion
- If `acceptance.feature` is empty or missing scenarios, stop and request completion
- If Gherkin tag coverage does not satisfy `docs/backend/architecture/GHERKIN_CONVENTIONS.md`, stop and request completion

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

1. Architecture Preflight → invoke `$architecture-preflight`
2. ADR creation (if required by preflight)
3. Plan finalization → invoke `$spec-planning`
4. Evaluation Compliance Summary (must be in `plan.md`)
5. Incremental implementation → guided by `$implementation-plan`
6. Automated tests
7. Static analysis and evaluation gates

---

## Planning Discipline

Generate and maintain `features/<feature_name>/plan.md` based on `governance/backend/templates/plan.md`.

The plan must:

- Define explicit increments with deliverables and tests
- Map Gherkin scenarios to BDD integration tests
- Include an Evaluation Compliance Summary predicting FIRST and 7 Virtue scores
- Reference ADRs and architecture contracts

The Evaluation Compliance Summary must use the structured YAML prediction block from `governance/backend/templates/plan.md`. All score and evidence fields must be populated with a numeric value (0–5) and a one-sentence rationale. Null values are not permitted at plan finalization. If any average is below 4.0, revise the plan before writing any code.

---

## ADR Rules

An ADR is required when:

- A standard is extended, overridden, or bypassed
- A new architectural pattern is introduced
- A security or auth approach changes
- A boundary rule or dependency direction changes
- A shared schema, API contract, event definition, or data model is introduced or modified that will be consumed by other features, services, or agents

ADRs live under `docs/backend/architecture/ADR/`, follow `docs/backend/architecture/ADR/TEMPLATE.md`, and must be Accepted before implementation proceeds.

---

## Implementation Rules

- Implement one increment at a time
- Respect all rules in `docs/backend/architecture/BOUNDARIES.md`
- Follow Hexagonal Architecture (ports and adapters)
- Use only approved frameworks from `docs/backend/architecture/TECH_STACK.md`
- Use approved auth patterns from `docs/backend/architecture/SECURITY_AUTH_PATTERNS.md`
- Follow API naming, versioning, and error rules from `docs/backend/architecture/API_CONVENTIONS.md`; update OpenAPI definitions when APIs change
- Follow design principles from `docs/backend/architecture/DESIGN_PRINCIPLES.md`; use findings from approved tools (Ruff, SonarQube, Snyk, import-linter) as defined in `docs/backend/architecture/TECH_STACK.md` — blocking findings must be resolved before proceeding

Layer-specific rules load automatically via nested `AGENTS.md` files when working in each layer:

- `api/AGENTS.md` — API routes and inbound HTTP adapters
- `services/AGENTS.md` — domain services
- `ports/AGENTS.md` — inbound/outbound port interfaces
- `adapters/AGENTS.md` — outbound adapter implementations
- `security/AGENTS.md` — auth, token validation, RBAC

---

## Evaluation Discipline

Before implementation, read `docs/backend/evaluation/eval_criteria.md` and `features/<feature_name>/eval_criteria.yaml`. Confirm FIRST and 7 Virtue enforcement thresholds.

Implementation must not proceed unless an Evaluation Compliance Summary exists in `plan.md` with predicted averages meeting required thresholds. CI evaluation gates are binding.

---

## Testing Requirements

Each increment must include:

- Unit tests compliant with FIRST principles
- BDD integration tests derived from Gherkin scenarios
- Contract tests when APIs, ports, or external integrations are affected

Gherkin scenarios must follow `docs/backend/architecture/GHERKIN_CONVENTIONS.md`:

- Every populated NFR category in `nfrs.md` must have at least one scenario tagged with the corresponding `@nfr-*` tag
- Features producing shared artifacts must include at least one `@contract` scenario
- Verify coverage during Architecture Preflight and plan finalization — stop if incomplete

Undocumented Gherkin gaps must be noted in `plan.md`.

---

## Automatic Refactor Conditions

Trigger refactor before proceeding if:

- Duplicate logic detected
- Structural complexity excessive
- FIRST or 7 Virtue score below threshold
- Test flakiness detected

---

## Architecture Preflight Triggers

Architecture Preflight must be re-run (or updated) when:

- Scope expands beyond what the current preflight covers
- New external dependencies are introduced
- Security or auth patterns change
- Evaluation mode changes
- An ADR trigger condition is met
- A shared contract or producer relationship is introduced or modified

If Preflight status is Blocked, implementation must not proceed.

---

## Output Expectations

Every plan and implementation output must include:

- Referenced standards (architecture contracts, eval criteria, ADRs)
- ADR status (Accepted / pending / not required — with justification)
- Architecture compliance confirmation
- Test coverage summary
- Evaluation impact summary

If alignment is unclear, stop and ask.

---

## Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit
- If an increment exceeds ~300 lines of production code, split it before committing

---

## Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Codex follows standards — it does not invent them.
