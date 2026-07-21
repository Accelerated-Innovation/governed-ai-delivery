# Governed AI Delivery — Codex Agent Instructions (Level 5: GenAI Operations — CLI)

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

- Confirm `extensions/llm-application/manifest.yaml` exists. If missing, stop and request `govkit extension add llm-application --target .`
- Read all files under `docs/backend/architecture/`
- Read `docs/backend/evaluation/eval_criteria.md`
- Read L5 contracts:
  - `extensions/llm-application/docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`
  - `extensions/llm-application/docs/backend/architecture/LLM_OBSERVABILITY_CONTRACT.md`
  - `extensions/llm-application/docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md`
  - `extensions/llm-application/docs/backend/architecture/LLM_EVALUATION_CONTRACT.md`
- If `eval_criteria.yaml` declares `multi_agent: true`, read `extensions/skill-oriented-agent-architecture/docs/backend/architecture/SKILL_ORIENTED_AGENT_ARCHITECTURE.md` and the applicable runtime, authority, resilience, and completion contracts
- Apply all contracts as binding constraints
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

0. **Multi-agent features only:** invoke `$govkit-multi-agent-design` before architecture preflight to produce `agent_topology.md`
1. Architecture Preflight → invoke `$govkit-architecture-preflight`
2. GenAI Preflight → invoke `$govkit-genai-preflight` (if feature uses LLM)
3. ADR creation (if required by preflight)
4. Plan finalization → invoke `$govkit-spec-planning`
5. Evaluation Suite Planning → invoke `$govkit-eval-suite-planning` (if mode: llm)
6. Evaluation Compliance Summary (must be in `plan.md`)
7. Incremental implementation → guided by `$govkit-implementation-plan`
8. Automated tests
9. Static analysis and evaluation gates

---

## Project Documentation

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

## Implementation Rules

- Implement one increment at a time
- Respect all rules in `docs/backend/architecture/BOUNDARIES.md`
- Follow Hexagonal Architecture (ports and adapters)
- Follow CLI conventions from `docs/backend/architecture/CLI_CONVENTIONS.md`
- **All LLM calls must route through the configured model gateway** — see `LLM_GATEWAY_CONTRACT.md`
- **Guardrails must match the declared policy** — see `MODEL_GUARDRAILS_CONTRACT.md`

Layer-specific rules load automatically via nested `AGENTS.md` files at each scoped directory.

---

## Evaluation Discipline

- FIRST and 7 Virtue thresholds apply to all features
- declared quality criteria required for `mode: llm` features
- the configured adversarial evaluator required for user-facing features
- the configured retrieval evaluator required for RAG features
- CI evaluation gates are binding

---

## Commit Discipline

- Complete one increment, then commit before starting the next
- Each commit must be independently buildable and testable
- Commit message references the increment: `feat(<feature>): increment N — <name>`
- Do not combine multiple increments into a single commit

---

## Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and explicit approval. Codex follows standards — it does not invent them.

Multi-agent ADR triggers: adding/removing/rerouting agent-topology nodes, material system prompt changes, runtime state schema changes.
