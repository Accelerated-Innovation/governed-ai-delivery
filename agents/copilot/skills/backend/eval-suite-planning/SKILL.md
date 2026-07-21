---
name: govkit-eval-suite-planning
description: Plan a provider-neutral evaluation suite for an LLM feature. Use when the user asks to plan model evaluations or invokes /govkit-eval-suite-planning.
---

# LLM Evaluation Suite Planning

Plan the model evaluation suite for a feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Inputs to read

- `extensions/llm-application/manifest.yaml`
- `extensions/llm-application/docs/backend/architecture/LLM_EVALUATION_CONTRACT.md`
- `extensions/llm-application/docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md`
- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/eval_criteria.yaml`
- `features/<feature_name>/architecture_preflight.md`
- `docs/backend/architecture/TECH_STACK.md`
- applicable ADRs and implementation-profile guides

If the LLM application extension is missing, stop and request its installation. Do not choose an evaluation product from model memory; use the configured adapter or propose a product decision through an ADR.

## Instructions

1. Define the evaluation subject by immutable model-routing, prompt, retrieval, guardrail, tool-definition, and configuration identities.
2. Select every applicable family:
   - deterministic structure and policy assertions
   - task correctness, relevance, completeness, and faithfulness
   - safety, prompt-injection, jailbreak, leakage, and policy-bypass cases
   - retrieval precision, recall, grounding, attribution, and source coverage
   - tool selection, argument validity, abstention, authorization, and recovery
   - latency, usage, cost, timeout, retry, and fallback behavior
   - declared fairness, language, and accessibility slices
3. For each criterion, specify the oracle, evaluator adapter, dataset slice, threshold scope, fail policy, and evidence.
4. Prefer deterministic or executable oracles. For a model judge, version its rubric, prompt, model, parsing logic, calibration set, independence decision, and inconclusive behavior.
5. Version datasets and declare provenance, development/acceptance separation, sensitive-data controls, synthetic-data labels, and required negative and boundary cases.
6. Set thresholds before the gated run. Safety-critical or required-slice failures block regardless of aggregate score.
7. Plan missing, stale, malformed, ambiguous, and insufficient-evidence tests.
8. Map the configured evaluator to a supported `eval_class`; use `custom` plus `tool: custom` when the selected adapter has no built-in profile.
9. Treat the bundled product-specific guides and CI gates as optional implementation profiles, not architecture requirements.

## Output

Update `features/<feature_name>/eval_criteria.yaml` with versioned criteria, dataset paths, tools, thresholds, slices or tags, and regression policy. Recommend a test/evidence structure appropriate to the configured adapters, for example:

```text
tests/eval/<feature_name>/
├── deterministic/
├── quality/
├── adversarial/
├── retrieval/
├── tool_use/
├── datasets/
└── evidence/
```

No implementation code in this step.
