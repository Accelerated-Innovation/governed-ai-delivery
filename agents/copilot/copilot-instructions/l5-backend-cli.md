# GitHub Copilot Instructions — Level 5 GenAI Operations (CLI)

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
* L5 contracts: `LLM_GATEWAY_CONTRACT.md`, `OBSERVABILITY_LLM_CONTRACT.md`, `GUARDRAILS_CONTRACT.md`, `EVALUATION_LLM_CONTRACT.md`

---

## 2. Mandatory Feature Structure

Required artifacts: `acceptance.feature`, `nfrs.md`, `eval_criteria.yaml`, `plan.md`, `architecture_preflight.md`

CLI features may be deterministic (no LLM). If mode is `llm`, all L5 contracts apply.

---

## 3. Feature Lifecycle

1. Architecture Preflight
2. GenAI Preflight (if mode: llm)
3. ADR creation (if required)
4. Plan finalization
5. Evaluation Suite Planning (if mode: llm)
6. Incremental implementation
7. Automated tests
8. CI gates

---

## 4. Project Documentation

Your project's language- and framework-specific conventions are documented in `docs/backend/architecture/`. Before implementing, read the relevant documents:

| Aspect | Document | Content |
|---|---|---|
| CLI / inbound adapter | `CLI_CONVENTIONS.md` | Command structure, arguments, output format |
| Services / domain | `ARCH_CONTRACT.md` | Architecture model, layering, approved libraries |
| LLM gateway | `LLM_GATEWAY_CONTRACT.md` | LiteLLM usage, provider routing, model aliases |
| Guardrails / safety | `GUARDRAILS_CONTRACT.md` | NeMo Guardrails and Guardrails AI integration |
| Observability | `OBSERVABILITY_LLM_CONTRACT.md` | OpenLLMetry and Langfuse setup |
| LLM evaluation | `EVALUATION_LLM_CONTRACT.md` | DeepEval, Promptfoo, RAGAS integration |
| Technology decisions | `TECH_STACK.md` | Approved frameworks, libraries, tools, and versions |

These documents define your stack's implementation. The architecture principles (hexagonal architecture, boundaries, evaluation) are universal; the specific tools and patterns are here.

---

## 5. Implementation Rules

* Follow Hexagonal Architecture, CLI conventions
* All LLM calls through LiteLLM
* Guardrails match declared mode
* CLI commands are inbound adapters — delegate to ports

---

## 5. Evaluation

* FIRST and 7 Virtues apply to all code
* DeepEval/Promptfoo/RAGAS apply when mode: llm

---

## 6. Commit Discipline

- One increment per commit: `feat(<feature>): increment N — <name>`

---

## 7. Authority

Copilot follows standards. It does not invent them.
