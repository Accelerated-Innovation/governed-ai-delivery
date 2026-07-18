---
name: govkit-genai-preflight
description: Validate Level 5 GenAI architecture decisions (LLM gateway, observability, guardrails, evaluation) before planning. Use after /govkit-architecture-preflight for features with mode:llm or when invoking /govkit-genai-preflight.
---

# GenAI Preflight

Run after `/govkit-architecture-preflight` to validate GenAI-specific architecture decisions for a feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Inputs to read

Feature specs:
- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/eval_criteria.yaml`
- `features/<feature_name>/architecture_preflight.md` (sections 1-9 should already be complete)

L5 Contracts:
- `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`
- `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`
- `docs/backend/architecture/GUARDRAILS_CONTRACT.md`
- `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

## Validation Checklist

For each item, validate and document the finding:

### 1. LLM Gateway (Section 10)
- Confirm LiteLLM is configured as the sole gateway
- Identify model alias(es) to be used
- Confirm fallback chain is defined (or justify single-provider)
- Confirm cost budget is documented in nfrs.md under "LLM Cost"
- Check for prohibited direct provider SDK imports

### 2. Observability (Section 11)
- Confirm OpenLLMetry instrumentation is planned
- Confirm Langfuse trace export is configured
- Determine if prompt versioning in Langfuse applies
- Confirm environment matrix alignment

### 3. Guardrails (Section 12)
- Determine guardrail mode: `nemo`, `guardrails-ai`, `both`, or `none`
- If `none`, confirm justification exists (non-user-facing feature)
- If `nemo` or `both`, confirm rail definition path
- If `guardrails-ai` or `both`, confirm validators listed

### 4. Evaluation Strategy (Section 13)
- Confirm DeepEval metrics are defined in eval_criteria.yaml
- Determine if Promptfoo is required (user-facing or untrusted input?)
- Determine if RAGAS is required (does the feature use retrieval?)
- Confirm evaluation dataset path exists

### 5. LLM NFR Validation (Section 14)
- Confirm LLM Latency is populated in nfrs.md (not TBD)
- Confirm LLM Cost is populated (not TBD)
- Confirm LLM Fallback is populated (not TBD)
- Confirm LLM Safety is populated (not TBD)

### 6. Multi-Agent Validation (Section 16 — only when `multi_agent: true`)

Check if `features/<feature_name>/eval_criteria.yaml` declares `multi_agent: true`.

If **not declared**: write "Section 16: Not applicable" and skip.

If **declared**:
- Confirm `features/<feature_name>/agent_topology.md` exists and all four sections are complete
- Confirm each agent's system prompt file exists at the declared path in the repository
- Confirm graph state schema `TypedDict` is declared (path in agent_topology.md)
- Confirm `eval_criteria.yaml` includes `multi_agent_evaluation` block with `topology_validated` and `system_prompt_governed` fields
- Confirm LangGraph is listed as approved in `docs/backend/architecture/TECH_STACK.md`

Block if any item fails.

## Output

Update `features/<feature_name>/architecture_preflight.md` sections 10-14 with findings.

Set section 15 (Final Status) based on validation results:
- If all checks pass: "Approved for planning"
- If any check fails: "Blocked pending resolution" with specific items to address

Do not proceed to planning if any L5 check is blocked.
