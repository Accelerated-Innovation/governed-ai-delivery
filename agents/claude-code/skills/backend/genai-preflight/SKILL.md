---
name: govkit-genai-preflight
description: Validate Level 5 provider-neutral LLM architecture decisions before planning. Use after /govkit-architecture-preflight for features with mode:llm or when invoking /govkit-genai-preflight.
---

# LLM Application Preflight

Run after `/govkit-architecture-preflight` for a model-backed feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Required extension

Confirm `extensions/llm-application/manifest.yaml` exists. If it is missing, stop and report:

```bash
govkit extension add llm-application --target .
```

Do not reconstruct the contracts from agent knowledge.

## Inputs to read

Feature specs:

- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/eval_criteria.yaml`
- `features/<feature_name>/architecture_preflight.md`

Extension contracts:

- `extensions/llm-application/docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`
- `extensions/llm-application/docs/backend/architecture/LLM_OBSERVABILITY_CONTRACT.md`
- `extensions/llm-application/docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md`
- `extensions/llm-application/docs/backend/architecture/LLM_EVALUATION_CONTRACT.md`

Also read `docs/backend/architecture/TECH_STACK.md` and applicable ADRs for selected implementation products. Product configuration never overrides an extension contract.

## Validation checklist

### 1. Gateway boundary (Section 10)

- Identify the typed outbound model gateway port and adapter boundary
- Identify logical model capabilities or aliases; reject provider identifiers in domain code
- Record routing, capability, fallback, retry, timeout, cancellation, streaming, and degraded-mode policy
- Record data classification, residency, retention, provider-use restrictions, credentials, rate limits, and budgets
- Confirm model-proposed tool calls remain proposals until deterministic validation and authorization
- Check for direct provider or gateway SDK imports outside approved adapters

### 2. Observability (Section 11)

- Record required model events, usage, latency, failures, guardrail outcomes, and trace correlations
- Record immutable model, prompt, routing, guardrail, retrieval, and configuration identities
- Confirm raw prompt, response, retrieved content, and tool arguments are not captured by default
- Record redaction-before-export, sampling, cardinality, retention, access, exporter failure, and evidence-required behavior

### 3. Model guardrails (Section 12)

- Classify trusted and untrusted instruction and context sources
- Record required input, context, structural, semantic, content, grounding, and tool-call controls
- Record policy, rule, schema, threshold, and detector identities
- Define refusal, escalation, quarantine, repair, degraded, and fail-closed behavior
- Confirm guardrail acceptance or schema validity never substitutes for authorization

### 4. Evaluation (Section 13)

- Select applicable deterministic, task-quality, safety/adversarial, retrieval, tool-use, operational, and fairness/accessibility families
- Record versioned datasets, slices, provenance, separation rules, and sensitive-data controls
- Name each oracle and evaluator adapter; calibrate any model judge
- Declare per-case, per-slice, and aggregate thresholds before execution
- Confirm missing, stale, invalid, ambiguous, or insufficient evidence cannot pass a release gate

### 5. LLM NFRs (Section 14)

- Confirm latency, cost or usage, fallback/degraded behavior, and safety NFRs are complete
- Add feature-specific privacy, residency, availability, quality, or human-review NFRs when applicable
- Block when a required NFR remains TBD

### 6. Agent architecture (Section 15, when applicable)

If the feature uses agents, skills, delegation, adaptive orchestration, or multi-agent execution, confirm `extensions/skill-oriented-agent-architecture/manifest.yaml` exists and load its applicable contract sets. Do not infer agent controls from the LLM contracts.

Block if a required extension, contract, decision, or control is missing.

## Output

Update `features/<feature_name>/architecture_preflight.md` sections 10–15 with evidence-backed findings. Set the final status to `Approved for planning`, `Requires ADR`, or `Blocked pending resolution`. Do not proceed to planning while any required control is blocked.
