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

* Read all files under `docs/backend/architecture/`
* Read `docs/backend/evaluation/eval_criteria.md`
* Read L5 contracts: `LLM_GATEWAY_CONTRACT.md`, `OBSERVABILITY_LLM_CONTRACT.md`, `GUARDRAILS_CONTRACT.md`, `EVALUATION_LLM_CONTRACT.md`
* Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## 2. Mandatory Feature Structure

Required artifacts:

* `acceptance.feature`
* `nfrs.md` (including LLM Latency, LLM Cost, LLM Fallback, LLM Safety)
* `eval_criteria.yaml` (with DeepEval/Promptfoo/RAGAS criteria for mode: llm)
* `plan.md` (with LLM Gateway, Guardrails, and extended evaluation_prediction)
* `architecture_preflight.md` (sections 1-9 standard + sections 10-14 GenAI)

Implementation must not begin unless all artifacts exist and are complete.

---

## 3. Feature Lifecycle (Mandatory Order)

1. Architecture Preflight
2. GenAI Preflight (L5-specific validation)
3. ADR creation (if required)
4. Plan finalization
5. Evaluation Suite Planning (DeepEval/Promptfoo/RAGAS)
6. Evaluation Compliance Summary
7. Incremental implementation
8. Automated tests (unit + LLM evaluation)
9. Static analysis and evaluation gates

Steps may not be skipped.

---

## 4. GenAI Contracts (Level 5)

All LLM features must comply with:

* **LLM Gateway:** LiteLLM is the sole gateway — no direct provider SDK calls
* **Observability:** OpenLLMetry emits, Langfuse stores — via ObservabilityPort
* **Guardrails:** NeMo for conversation safety, Guardrails AI for output validation — via GuardrailPort
* **Evaluation:** DeepEval for quality, Promptfoo for adversarial, RAGAS for retrieval — in tests/eval/

---

## 5. Project Documentation

Your project's language- and framework-specific conventions are documented in `docs/backend/architecture/`. Before implementing, read the relevant documents:

| Aspect | Document | Content |
|---|---|---|
| API / inbound adapter | `API_CONVENTIONS.md` | Routing, request/response, authentication, error mapping |
| Services / domain | `ARCH_CONTRACT.md` | Architecture model, layering, approved libraries |
| LLM gateway | `LLM_GATEWAY_CONTRACT.md` | LiteLLM usage, provider routing, model aliases |
| Guardrails / safety | `GUARDRAILS_CONTRACT.md` | NeMo Guardrails and Guardrails AI integration |
| Observability | `OBSERVABILITY_LLM_CONTRACT.md` | OpenLLMetry and Langfuse setup |
| LLM evaluation | `EVALUATION_LLM_CONTRACT.md` | DeepEval, Promptfoo, RAGAS integration |
| Technology decisions | `TECH_STACK.md` | Approved frameworks, libraries, tools, and versions |

These documents define your stack's implementation. The architecture principles (hexagonal architecture, boundaries, evaluation) are universal; the specific tools and patterns are here.

---

## 6. Implementation Rules

* Implement one increment at a time
* Follow Hexagonal Architecture (ports and adapters)
* All LLM calls through LiteLLM (no direct provider imports outside adapters/llm/)
* Guardrails match declared mode in architecture_preflight.md
* Observability via OpenLLMetry + Langfuse

---

## 6. Evaluation Discipline

* FIRST and 7 Virtues apply to all code
* DeepEval metrics required for mode: llm
* Promptfoo required for user-facing features
* RAGAS required for RAG features
* CI gates: deepeval-gate, promptfoo-gate, guardrails-check

---

## 7. Testing Requirements

Each increment must include:

* Unit tests (FIRST compliant)
* BDD integration tests from Gherkin scenarios
* DeepEval quality tests for LLM output
* Promptfoo adversarial tests (if user-facing)
* RAGAS retrieval tests (if RAG)

---

## 8. Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message: `feat(<feature>): increment N — <name>`

---

## 9. Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Copilot follows standards — it does not invent them.
