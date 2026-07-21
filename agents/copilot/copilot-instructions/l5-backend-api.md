---
applyTo: "**"
---
# GitHub Copilot Instructions — Level 5 GenAI Operations

These instructions govern how GitHub Copilot plans, reasons, and generates code in this repository.

They are mandatory.

Copilot must treat this repository as a governed delivery system, not an open coding environment.

Repository artifacts are the source of truth. Chat memory is not.

---

## 1. Operating Mode

Copilot operates aligned to:

* Product specifications under `features/`
* Architecture contracts under `docs/backend/architecture/`
* Evaluation standards under `docs/backend/evaluation/`
* Governance rules under `governance/`

Before planning or generating code:

* Confirm `extensions/llm-application/manifest.yaml` exists. If missing, stop and request `govkit extension add llm-application --target .`
* Read all files under `docs/backend/architecture/`
* Read `docs/backend/evaluation/eval_criteria.md`
* Read the contract sets declared by `extensions/llm-application/manifest.yaml`
* If `eval_criteria.yaml` declares `multi_agent: true`, read `extensions/skill-oriented-agent-architecture/docs/backend/architecture/SKILL_ORIENTED_AGENT_ARCHITECTURE.md` and the applicable runtime, authority, resilience, and completion contracts
* Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## 2. Mandatory Feature Structure

Required artifacts:

* `acceptance.feature`
* `nfrs.md` (including LLM Latency, LLM Cost, LLM Fallback, LLM Safety)
* `eval_criteria.yaml` (with configured quality/adversarial/retrieval evaluators criteria for mode: llm)
* `plan.md` (with model gateway, Guardrails, and extended evaluation_prediction)
* `architecture_preflight.md` (sections 1-9 standard + sections 10-14 GenAI)

Implementation must not begin unless all artifacts exist and are complete.

---

## 3. Feature Lifecycle (Mandatory Order)

0. **Multi-agent features only:** run `/govkit-multi-agent-design` before architecture preflight to produce `agent_topology.md`
1. Architecture Preflight
2. GenAI Preflight (L5-specific validation)
3. ADR creation (if required)
4. Plan finalization
5. Evaluation Suite Planning (configured quality/adversarial/retrieval evaluators)
6. Evaluation Compliance Summary
7. Incremental implementation
8. Automated tests (unit + LLM evaluation)
9. Static analysis and evaluation gates

Steps may not be skipped.

---

## 4. GenAI Contracts (Level 5)

All LLM features must comply with:

* **model gateway:** the configured model gateway is the sole gateway — no direct provider SDK calls
* **Observability:** model telemetry uses the observability port and approved adapters — via ObservabilityPort
* **Guardrails:** declared input, context, output, and tool-call controls — via GuardrailPort
* **Evaluation:** versioned criteria use the configured evaluator adapters — in tests/eval/

---

## 5. Project Documentation

Your project's language- and framework-specific conventions are documented in `docs/backend/architecture/`. Before implementing, read the relevant documents:

| Aspect | Document | Content |
|---|---|---|
| API / inbound adapter | `API_CONVENTIONS.md` | Routing, request/response, authentication, error mapping |
| Services / domain | `ARCH_CONTRACT.md` | Architecture model, layering, approved libraries |
| LLM gateway | `LLM_GATEWAY_CONTRACT.md` | provider-neutral port, logical routing, resilience, and budgets |
| Guardrails / safety | `MODEL_GUARDRAILS_CONTRACT.md` | input, context, output, and tool-call policy with fail-closed behavior |
| Observability | `LLM_OBSERVABILITY_CONTRACT.md` | privacy-aware telemetry, immutable provenance, usage, and trace correlation |
| LLM evaluation | `LLM_EVALUATION_CONTRACT.md` | versioned datasets, oracles, slices, thresholds, gates, and evidence |
| Technology decisions | `TECH_STACK.md` | Approved frameworks, libraries, tools, and versions |

These documents define your stack's implementation. The architecture principles (hexagonal architecture, boundaries, evaluation) are universal; the specific tools and patterns are here.

---

## 6. Implementation Rules

* Implement one increment at a time
* Follow Hexagonal Architecture (ports and adapters)
* All LLM calls through the configured model gateway (no direct provider imports outside adapters/llm/)
* Guardrails match the declared policy in architecture_preflight.md
* Observability via the configured model instrumentation + the configured telemetry backend

---

## 6. Evaluation Discipline

* FIRST and 7 Virtues apply to all code
* declared quality criteria required for mode: llm
* the configured adversarial evaluator required for user-facing features
* the configured retrieval evaluator required for RAG features
* CI gates: deepeval-gate, promptfoo-gate, guardrails-check

---

## 7. Testing Requirements

Each increment must include:

* Unit tests (FIRST compliant)
* BDD integration tests from Gherkin scenarios
* declared model-quality tests for LLM output
* declared adversarial tests (if user-facing)
* declared retrieval tests (if RAG)

---

## 8. Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message: `feat(<feature>): increment N — <name>`

---

## 9. Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Copilot follows standards — it does not invent them.

Multi-agent ADR triggers: adding/removing/rerouting agent-topology nodes, material system prompt changes, runtime state schema changes.
