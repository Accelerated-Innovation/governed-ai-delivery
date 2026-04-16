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

- Read all files under `docs/backend/architecture/`
- Read `docs/backend/evaluation/eval_criteria.md`
- Read L5 contracts:
  - `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`
  - `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`
  - `docs/backend/architecture/GUARDRAILS_CONTRACT.md`
  - `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`
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

1. Architecture Preflight → invoke `$architecture-preflight`
2. GenAI Preflight → invoke `$genai-preflight` (if feature uses LLM)
3. ADR creation (if required by preflight)
4. Plan finalization → invoke `$spec-planning`
5. Evaluation Suite Planning → invoke `$eval-suite-planning` (if mode: llm)
6. Evaluation Compliance Summary (must be in `plan.md`)
7. Incremental implementation → guided by `$implementation-plan`
8. Automated tests
9. Static analysis and evaluation gates

---

## Implementation Rules

- Implement one increment at a time
- Respect all rules in `docs/backend/architecture/BOUNDARIES.md`
- Follow Hexagonal Architecture (ports and adapters)
- Follow CLI conventions from `docs/backend/architecture/CLI_CONVENTIONS.md`
- **All LLM calls must route through LiteLLM** — see `LLM_GATEWAY_CONTRACT.md`
- **Guardrails must match the declared mode** — see `GUARDRAILS_CONTRACT.md`

Layer-specific rules load automatically via nested `AGENTS.md` files at each scoped directory.

---

## Evaluation Discipline

- FIRST and 7 Virtue thresholds apply to all features
- DeepEval metrics required for `mode: llm` features
- Promptfoo required for user-facing features
- RAGAS required for RAG features
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
