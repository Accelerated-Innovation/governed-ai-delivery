# Governed AI Delivery — Claude Code Instructions

These instructions are mandatory. Claude operates as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Claude operates aligned to:

- Product specifications under `features/`
- Architecture contracts under `docs/architecture/`
- Evaluation standards under `docs/evaluation/`
- Governance rules under `governance/`

Before planning or generating code:

- Read all files under `docs/architecture/`
- Read `docs/evaluation/eval_criteria.md`
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

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

1. Architecture Preflight → run `/project:architecture-preflight`
2. ADR creation (if required by preflight)
3. Plan finalization → run `/project:spec-planning`
4. Evaluation Compliance Summary (must be in `plan.md`)
5. Incremental implementation → guided by `/project:implementation-plan`
6. Automated tests
7. Static analysis and evaluation gates

---

## Planning Discipline

Generate and maintain `features/<feature_name>/plan.md` based on `governance/templates/plan.md`.

The plan must:

- Define explicit increments with deliverables and tests
- Map Gherkin scenarios to BDD integration tests
- Include an Evaluation Compliance Summary predicting FIRST and 7 Virtue scores
- Reference ADRs and architecture contracts

If predicted evaluation thresholds are not met, revise the plan before writing any code.

---

## ADR Rules

An ADR is required when:

- A standard is extended, overridden, or bypassed
- A new architectural pattern is introduced
- A security or auth approach changes
- A boundary rule or dependency direction changes

ADRs live under `docs/architecture/ADR/`, follow `docs/architecture/ADR/TEMPLATE.md`, and must be Accepted before implementation proceeds.

---

## Implementation Rules

- Implement one increment at a time
- Respect all rules in `docs/architecture/BOUNDARIES.md`
- Follow Hexagonal Architecture (ports and adapters)
- Use only approved frameworks from `docs/architecture/TECH_STACK.md`
- Use approved auth patterns from `docs/architecture/SECURITY_AUTH_PATTERNS.md`

Layer-specific rules load automatically from `.claude/rules/` when editing files in each layer:

- `api.md` — `**/api/**`
- `services.md` — `**/services/**`
- `ports.md` — `**/ports/**`
- `adapters.md` — `**/adapters/**`
- `security.md` — `**/security/**` and `**/auth/**`

---

## Evaluation Discipline

Before implementation, read `docs/evaluation/eval_criteria.md` and `features/<feature_name>/eval_criteria.yaml`. Confirm FIRST and 7 Virtue enforcement thresholds.

Implementation must not proceed unless an Evaluation Compliance Summary exists in `plan.md` with predicted averages meeting required thresholds. CI evaluation gates are binding.

---

## Testing Requirements

Each increment must include:

- Unit tests compliant with FIRST principles
- BDD integration tests derived from Gherkin scenarios
- Contract tests when APIs, ports, or external integrations are affected

Undocumented Gherkin gaps must be noted in `plan.md`.

---

## Automatic Refactor Conditions

Trigger refactor before proceeding if:

- Duplicate logic detected
- Structural complexity excessive
- FIRST or 7 Virtue score below threshold
- Test flakiness detected

---

## Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Claude follows standards — it does not invent them.
