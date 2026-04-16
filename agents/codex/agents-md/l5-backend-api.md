# Governed AI Delivery — Codex Agent Instructions (Level 5: GenAI Operations)

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
- Read L5 contracts:
  - `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`
  - `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`
  - `docs/backend/architecture/GUARDRAILS_CONTRACT.md`
  - `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`
- Apply architecture, testing, technology, evaluation, and GenAI contracts as binding constraints
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

- If `nfrs.md` contains TBD entries in any category (including LLM Latency, LLM Cost, LLM Fallback, LLM Safety), stop and request completion
- If `acceptance.feature` is empty or missing scenarios, stop and request completion
- If Gherkin tag coverage does not satisfy `docs/backend/architecture/GHERKIN_CONVENTIONS.md`, stop and request completion

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

1. Architecture Preflight → invoke `$architecture-preflight`
2. GenAI Preflight → invoke `$genai-preflight` (validates L5-specific decisions)
3. ADR creation (if required by preflight)
4. Plan finalization → invoke `$spec-planning`
5. Evaluation Suite Planning → invoke `$eval-suite-planning` (plans DeepEval/Promptfoo/RAGAS suites)
6. Evaluation Compliance Summary (must be in `plan.md`)
7. Incremental implementation → guided by `$implementation-plan`
8. Automated tests (unit + LLM evaluation)
9. Static analysis and evaluation gates

---

## Planning Discipline

Generate and maintain `features/<feature_name>/plan.md` based on `governance/backend/templates/l5-plan.md`.

The plan must:

- Define explicit increments with deliverables and tests
- Map Gherkin scenarios to BDD integration tests
- Include an Evaluation Compliance Summary predicting FIRST, 7 Virtue, and LLM evaluation scores
- Include LLM Gateway Configuration and Guardrails Configuration sections
- Reference ADRs and architecture contracts

---

## ADR Rules

An ADR is required when:

- A standard is extended, overridden, or bypassed
- A new architectural pattern is introduced
- A security or auth approach changes
- A boundary rule or dependency direction changes
- A shared schema, API contract, event definition, or data model is introduced or modified
- A new LLM provider is added to the routing table
- The guardrail mode is changed for a production feature
- LiteLLM is bypassed for any LLM call

---

## Implementation Rules

- Implement one increment at a time
- Respect all rules in `docs/backend/architecture/BOUNDARIES.md`
- Follow Hexagonal Architecture (ports and adapters)
- Use only approved frameworks from `docs/backend/architecture/TECH_STACK.md`
- **All LLM calls must route through LiteLLM** — see `LLM_GATEWAY_CONTRACT.md`
- **Guardrails must match the declared mode** — see `GUARDRAILS_CONTRACT.md`
- **Observability via OpenLLMetry + Langfuse** — see `OBSERVABILITY_LLM_CONTRACT.md`

Layer-specific rules load automatically via nested `AGENTS.md` files when working in each layer:

- `api/AGENTS.md` — API routes and inbound HTTP adapters
- `services/AGENTS.md` — domain services
- `ports/AGENTS.md` — inbound/outbound port interfaces
- `adapters/AGENTS.md` — outbound adapter implementations
- `security/AGENTS.md` — auth, token validation, RBAC
- `adapters/llm/AGENTS.md` — LLM gateway (LiteLLM)
- `adapters/guardrails/AGENTS.md` — NeMo Guardrails and Guardrails AI
- `tests/eval/AGENTS.md` — DeepEval/Promptfoo/RAGAS test suites
- `adapters/observability/AGENTS.md` — OpenLLMetry and Langfuse

---

## Evaluation Discipline

Before implementation:

- Read `docs/backend/evaluation/eval_criteria.md`
- Read `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`
- Read `features/<feature_name>/eval_criteria.yaml`
- Confirm FIRST, 7 Virtue, and LLM evaluation thresholds

Implementation must not proceed unless:

- An Evaluation Compliance Summary exists in `plan.md` with predicted averages meeting thresholds
- DeepEval metrics are defined for `mode: llm` features
- Promptfoo is addressed (required or justified as not required)
- RAGAS is addressed if the feature uses retrieval

CI evaluation gates are binding.

---

## Testing Requirements

Each increment must include:

- Unit tests compliant with FIRST principles
- BDD integration tests derived from Gherkin scenarios
- Contract tests when APIs, ports, or external integrations are affected
- **DeepEval quality tests** for LLM output (faithfulness, relevancy, hallucination)
- **Promptfoo adversarial tests** if the feature is user-facing
- **RAGAS retrieval tests** if the feature uses RAG

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
