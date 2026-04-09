---
description: "Plan DeepEval, Promptfoo, and RAGAS evaluation suites for an LLM feature"
agent: "ask"
---

# Evaluation Suite Planning Prompt

Plan the LLM evaluation test suite for: **{{FEATURE_NAME}}**

## Inputs to read

- `features/{{FEATURE_NAME}}/nfrs.md`
- `features/{{FEATURE_NAME}}/acceptance.feature`
- `features/{{FEATURE_NAME}}/eval_criteria.yaml`
- `features/{{FEATURE_NAME}}/architecture_preflight.md`
- `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`
- `docs/backend/guides/deepeval-usage.md`
- `docs/backend/guides/promptfoo-usage.md`
- `docs/backend/guides/ragas-evaluation.md`

## Instructions

1. Determine which tools are required: DeepEval (always for mode:llm), Promptfoo (if user-facing), RAGAS (if RAG)
2. Select DeepEval metrics: FaithfulnessMetric, AnswerRelevancyMetric, HallucinationMetric, GEval
3. Plan Promptfoo adversarial scenarios: jailbreak, injection, topic boundaries, regression
4. Select RAGAS metrics if applicable: context_recall, context_precision, faithfulness, answer_relevancy
5. Plan evaluation dataset (min 20 DeepEval cases, 10 Promptfoo scenarios, 15 RAGAS triples)

## Output

Update `features/{{FEATURE_NAME}}/eval_criteria.yaml` with criteria using `deepeval_*`, `promptfoo_*`, and `ragas_*` eval_class values. Set thresholds and dataset paths.

No implementation code in this step.
