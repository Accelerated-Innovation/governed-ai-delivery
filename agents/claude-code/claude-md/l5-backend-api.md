# Governed AI Delivery — Claude Code Instructions (Level 5: GenAI Operations)

These instructions are mandatory. Claude operates as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Claude operates aligned to:

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

1. Architecture Preflight → run `/architecture-preflight`
2. GenAI Preflight → run `/genai-preflight` (validates L5-specific decisions)
3. ADR creation (if required by preflight)
4. Plan finalization → run `/spec-planning`
5. Evaluation Suite Planning → run `/eval-suite-planning` (plans DeepEval/Promptfoo/RAGAS suites)
6. Evaluation Compliance Summary (must be in `plan.md`)
7. Incremental implementation → guided by `/implementation-plan`
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

## Project Documentation

Your project's language- and framework-specific conventions are documented in `docs/backend/architecture/`. Before implementing, read the relevant documents:

| Aspect | Document | Content |
|---|---|---|
| API / inbound adapter | `API_CONVENTIONS.md` | Routing, request/response, authentication, error mapping |
| Services / domain | `ARCH_CONTRACT.md` | Architecture model, layering, approved libraries |
| LLM gateway | `LLM_GATEWAY_CONTRACT.md` | LiteLLM usage, provider routing, model aliases, cost tracking |
| Guardrails / safety | `GUARDRAILS_CONTRACT.md` | NeMo Guardrails and Guardrails AI integration |
| Observability / telemetry | `OBSERVABILITY_LLM_CONTRACT.md` | OpenLLMetry and Langfuse setup |
| LLM evaluation | `EVALUATION_LLM_CONTRACT.md` | DeepEval, Promptfoo, RAGAS integration |
| Technology decisions | `TECH_STACK.md` | Approved frameworks, libraries, tools, and versions |

These documents define your stack's implementation. The architecture principles (hexagonal architecture, boundaries, evaluation) are universal; the specific tools and patterns are here.

---

## Implementation Rules

- Implement one increment at a time
- Respect all rules in `docs/backend/architecture/BOUNDARIES.md`
- Follow Hexagonal Architecture (ports and adapters)
- Use only approved frameworks from `docs/backend/architecture/TECH_STACK.md`
- **All LLM calls must route through the LLM gateway** — see `LLM_GATEWAY_CONTRACT.md`
- **Guardrails must match the declared mode** — see `GUARDRAILS_CONTRACT.md`
- **Observability via LLM telemetry** — see `OBSERVABILITY_LLM_CONTRACT.md`

Layer-specific rules load automatically from `.claude/rules/` when editing files in each layer:

- `api.md` — `**/api/**`
- `services.md` — `**/services/**`
- `ports.md` — `**/ports/**`
- `adapters.md` — `**/adapters/**`
- `security.md` — `**/security/**` and `**/auth/**`
- `llm-gateway.md` — `**/adapters/llm/**`
- `guardrails.md` — `**/adapters/guardrails/**` and `**/rails/**`
- `llm-evaluation.md` — `**/tests/eval/**` and `**/eval_sets/**`
- `llm-observability.md` — `**/adapters/observability/**`

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

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Claude follows standards — it does not invent them.
