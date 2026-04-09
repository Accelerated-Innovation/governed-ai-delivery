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

## 4. Implementation Rules

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
