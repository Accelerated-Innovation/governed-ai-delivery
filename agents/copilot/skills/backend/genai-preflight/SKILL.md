---
name: genai-preflight
description: Validate Level 5 GenAI architecture decisions before planning
argument-hint: "<feature_name>"
user-invocable: true
---

# GenAI Preflight

Run after architecture preflight to validate GenAI-specific decisions for: **$ARGUMENTS**

## Inputs to read

- `features/$ARGUMENTS/nfrs.md`
- `features/$ARGUMENTS/acceptance.feature`
- `features/$ARGUMENTS/eval_criteria.yaml`
- `features/$ARGUMENTS/architecture_preflight.md`
- `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`
- `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`
- `docs/backend/architecture/GUARDRAILS_CONTRACT.md`
- `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

## Validate

1. **LLM Gateway:** LiteLLM is sole gateway, model alias defined, fallback chain exists, cost budget in nfrs.md
2. **Observability:** OpenLLMetry planned, Langfuse export configured, prompt versioning decision made
3. **Guardrails:** Mode declared (nemo/guardrails-ai/both/none), configs referenced, justification if none
4. **Evaluation:** DeepEval metrics in eval_criteria.yaml, Promptfoo stated, RAGAS if retrieval
5. **LLM NFRs:** Latency, Cost, Fallback, Safety all populated in nfrs.md

6. **Multi-Agent** (only when `multi_agent: true`): `agent_topology.md` complete, all system prompt files exist, state schema declared, `multi_agent_evaluation` block in `eval_criteria.yaml`, LangGraph approved in TECH_STACK.md

## Output

Update `features/$ARGUMENTS/architecture_preflight.md` sections 10-14 and set final status.

Do not proceed to planning if any L5 check is blocked.
