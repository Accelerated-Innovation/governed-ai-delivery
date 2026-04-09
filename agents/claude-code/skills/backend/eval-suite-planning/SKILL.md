---
description: "Plan DeepEval, Promptfoo, and RAGAS evaluation suites for an LLM feature"
argument-hint: "<feature_name>"
---

# Evaluation Suite Planning

Plan the LLM evaluation test suite for: **$ARGUMENTS**

## Inputs to read

Feature specs:
- `features/$ARGUMENTS/nfrs.md`
- `features/$ARGUMENTS/acceptance.feature`
- `features/$ARGUMENTS/eval_criteria.yaml`
- `features/$ARGUMENTS/architecture_preflight.md` (sections 10-14)

Contracts and guides:
- `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`
- `docs/backend/guides/deepeval-usage.md`
- `docs/backend/guides/promptfoo-usage.md`
- `docs/backend/guides/ragas-evaluation.md`

## Instructions

1. Read all inputs listed above.
2. Determine which evaluation tools are required based on the architecture preflight:
   - DeepEval: always required for `mode: llm`
   - Promptfoo: required if feature is user-facing or processes untrusted input
   - RAGAS: required if feature uses retrieval (RAG pipeline)

3. For **DeepEval**, select metrics based on feature type:
   - All LLM features: `FaithfulnessMetric`, `AnswerRelevancyMetric`
   - Features with context: add `HallucinationMetric`, `ContextualRelevancyMetric`
   - Features needing custom criteria: add `GEval` with specific rubric
   - Set thresholds (recommend 0.8 minimum, 0.85+ for production features)

4. For **Promptfoo**, plan adversarial scenarios:
   - Jailbreak attempts (bypass system instructions)
   - Prompt injection (embed malicious instructions in user input)
   - Topic boundary testing (off-topic requests)
   - Regression baselines (expected output stability)

5. For **RAGAS** (if applicable), select retrieval metrics:
   - `context_recall` — does the retriever find all relevant docs?
   - `context_precision` — are retrieved docs relevant (low noise)?
   - `faithfulness` — is the answer faithful to retrieved context?
   - `answer_relevancy` — does the answer address the question?

6. Plan the evaluation dataset:
   - Minimum 20 test cases for DeepEval
   - Minimum 10 adversarial scenarios for Promptfoo
   - Minimum 15 query-context-answer triples for RAGAS

## Output

Update `features/$ARGUMENTS/eval_criteria.yaml` with:
- DeepEval criteria using `deepeval_*` eval_class values
- Promptfoo criteria using `promptfoo_*` eval_class values (if required)
- RAGAS criteria using `ragas_*` eval_class values (if required)
- Dataset path reference
- Appropriate thresholds per metric

Provide recommended test file structure:
```
tests/eval/$ARGUMENTS/
├── test_quality.py           # DeepEval test cases
├── promptfoo.yaml            # Promptfoo config (if required)
└── eval_sets/
    ├── dataset.json          # DeepEval dataset
    └── rag_dataset.json      # RAGAS dataset (if required)
```

No implementation code in this step.
