---
applyTo: "**"
---
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
* The contract sets declared by `extensions/llm-application/manifest.yaml`; if the manifest is missing for `mode: llm`, stop and request `govkit extension add llm-application --target .`
* If `eval_criteria.yaml` declares `multi_agent: true`, read `extensions/skill-oriented-agent-architecture/docs/backend/architecture/SKILL_ORIENTED_AGENT_ARCHITECTURE.md` and the applicable runtime, authority, resilience, and completion contracts

---

## 2. Mandatory Feature Structure

Required artifacts: `acceptance.feature`, `nfrs.md`, `eval_criteria.yaml`, `plan.md`, `architecture_preflight.md`

CLI features may be deterministic (no LLM). If mode is `llm`, all L5 contracts apply.

---

## 3. Feature Lifecycle

0. **Multi-agent features only:** run `/govkit-multi-agent-design` before architecture preflight to produce `agent_topology.md`
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
| LLM gateway | `LLM_GATEWAY_CONTRACT.md` | provider-neutral port, logical routing, resilience, and budgets |
| Guardrails / safety | `MODEL_GUARDRAILS_CONTRACT.md` | input, context, output, and tool-call policy with fail-closed behavior |
| Observability | `LLM_OBSERVABILITY_CONTRACT.md` | privacy-aware telemetry, immutable provenance, usage, and trace correlation |
| LLM evaluation | `LLM_EVALUATION_CONTRACT.md` | versioned datasets, oracles, slices, thresholds, gates, and evidence |
| Technology decisions | `TECH_STACK.md` | Approved frameworks, libraries, tools, and versions |

These documents define your stack's implementation. The architecture principles (hexagonal architecture, boundaries, evaluation) are universal; the specific tools and patterns are here.

---

## 5. Implementation Rules

* Follow Hexagonal Architecture, CLI conventions
* All LLM calls through the configured model gateway
* Guardrails match the declared policy
* CLI commands are inbound adapters — delegate to ports

---

## 5. Evaluation

* FIRST and 7 Virtues apply to all code
* configured quality/adversarial/retrieval evaluators apply when mode: llm

---

## 6. Commit Discipline

- One increment per commit: `feat(<feature>): increment N — <name>`

---

## 7. Authority

Copilot follows standards. It does not invent them.

Multi-agent ADR triggers: adding/removing/rerouting agent-topology nodes, material system prompt changes, runtime state schema changes.
