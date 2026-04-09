# LLM Evaluation Contract

This document defines the evaluation standards for LLM features in this repository.

**DeepEval measures quality. Promptfoo tests adversarial resilience. RAGAS evaluates retrieval.** These roles are non-overlapping.

---

## 1. Tool Ownership

| Tool | Role | When Required |
|------|------|---------------|
| **DeepEval** | Feature-level LLM quality evaluation | Always required for features with `mode: llm` |
| **Promptfoo** | Adversarial and regression attack suites | Required when feature is user-facing or processes untrusted input |
| **RAGAS** | Retrieval-specific evaluation | Required only for RAG (retrieval-augmented generation) features |

Rules:

- DeepEval measures **quality** — faithfulness, answer relevancy, hallucination, contextual relevancy
- Promptfoo measures **safety** — jailbreak resistance, prompt injection, toxic output prevention
- RAGAS measures **retrieval** — context recall, context precision, answer correctness for RAG
- Do not use DeepEval for adversarial testing (Promptfoo owns this)
- Do not use Promptfoo for quality metrics (DeepEval owns this)
- Do not use RAGAS for non-retrieval features

---

## 2. Integration with eval_criteria.yaml

Each tool maps to specific `eval_class` values in `eval_criteria.yaml`:

### DeepEval eval_class values

| eval_class | DeepEval Metric | What It Measures |
|-----------|----------------|------------------|
| `deepeval_faithfulness` | `FaithfulnessMetric` | LLM output is grounded in provided context |
| `deepeval_answer_relevancy` | `AnswerRelevancyMetric` | Response is relevant to the question asked |
| `deepeval_hallucination` | `HallucinationMetric` | LLM does not fabricate facts |
| `deepeval_contextual_relevancy` | `ContextualRelevancyMetric` | Retrieved context is relevant to the query |
| `deepeval_geval` | `GEval` | Custom LLM-as-judge evaluation with user-defined criteria |

### Promptfoo eval_class values

| eval_class | Promptfoo Test Type | What It Measures |
|-----------|-------------------|------------------|
| `promptfoo_adversarial` | Red-team suite | Resistance to jailbreak, injection, and manipulation |
| `promptfoo_regression` | Baseline comparison | Output stability across prompt or model changes |

### RAGAS eval_class values

| eval_class | RAGAS Metric | What It Measures |
|-----------|-------------|------------------|
| `ragas_context_recall` | `context_recall` | Retriever finds all relevant documents |
| `ragas_faithfulness` | `faithfulness` | Generated answer is faithful to retrieved context |
| `ragas_answer_relevancy` | `answer_relevancy` | Generated answer addresses the question |
| `ragas_context_precision` | `context_precision` | Retrieved documents are relevant (low noise) |

---

## 3. Evaluation Pipeline

```
Feature Development
    ↓
DeepEval (quality metrics)     ← dev + CI
    ↓
Promptfoo (adversarial suite)  ← CI (if required by preflight)
    ↓
RAGAS (retrieval metrics)      ← CI (if feature uses retrieval)
    ↓
CI Gates
    ├── deepeval-gate.yml      ← fails if quality below threshold
    ├── promptfoo-gate.yml     ← fails if adversarial tests fail
    └── (RAGAS runs as part of DeepEval suite)
```

---

## 4. DeepEval Usage

DeepEval tests live alongside feature tests:

```
tests/
└── eval/
    └── <feature_name>/
        ├── test_quality.py       ← DeepEval test cases
        └── eval_sets/
            └── dataset.json      ← input/expected pairs
```

Rules:

- One test file per feature for DeepEval metrics
- Datasets stored in `eval_sets/` and versioned in git
- Each criterion in `eval_criteria.yaml` with a `deepeval_*` eval_class must have a corresponding test
- DeepEval tests run in CI via `deepeval-gate.yml`
- Thresholds defined in `eval_criteria.yaml` are enforced — failures block merge

See `docs/backend/guides/deepeval-usage.md` for test writing patterns.

---

## 5. Promptfoo Usage

Promptfoo configurations live alongside feature specs:

```
tests/
└── eval/
    └── <feature_name>/
        ├── promptfoo.yaml        ← adversarial test configuration
        └── adversarial/
            └── attacks.yaml      ← attack scenarios
```

Rules:

- Promptfoo config uses YAML format
- Red-team scenarios must cover: jailbreak attempts, prompt injection, toxic output elicitation
- Regression baselines are stored and compared across runs
- Promptfoo tests run in CI via `promptfoo-gate.yml`
- Architecture preflight must explicitly state whether Promptfoo is required

See `docs/backend/guides/promptfoo-usage.md` for configuration patterns.

---

## 6. RAGAS Usage

RAGAS evaluates retrieval quality for RAG features:

```
tests/
└── eval/
    └── <feature_name>/
        ├── test_retrieval.py     ← RAGAS evaluation
        └── eval_sets/
            └── rag_dataset.json  ← queries + ground truth contexts
```

Rules:

- RAGAS is required only when the feature uses retrieval (vector search, document retrieval)
- RAGAS metrics run as part of the DeepEval test suite (DeepEval can execute RAGAS metrics)
- Architecture preflight must state whether RAGAS is required
- Retrieval quality thresholds defined in `eval_criteria.yaml`

See `docs/backend/guides/ragas-evaluation.md` for dataset preparation.

---

## 7. Evaluation Prediction in plan.md

L5 extends the `evaluation_prediction` block in `plan.md`:

```yaml
evaluation_prediction:
  first: { ... }        # Existing L4 FIRST scores
  virtues: { ... }      # Existing L4 Virtue scores
  llm_evaluation:
    deepeval_metrics:
      - { metric: "faithfulness", predicted_score: 0.85, threshold: 0.8 }
      - { metric: "answer_relevancy", predicted_score: 0.9, threshold: 0.85 }
    promptfoo_required: true
    guardrail_mode: "both"
    ragas_required: false
  thresholds_met: true
```

---

## 8. Relationship to Existing Evaluation

L5 LLM evaluation **complements** existing FIRST and 7 Virtues:

| Framework | What It Evaluates | When |
|-----------|------------------|------|
| FIRST | Test quality (speed, isolation, determinism) | All levels |
| 7 Virtues | Code quality (simplicity, clarity, uniqueness) | L4+ |
| DeepEval | LLM output quality (faithfulness, relevancy) | L5 |
| Promptfoo | LLM safety (adversarial resilience) | L5 |
| RAGAS | Retrieval quality (recall, precision) | L5 (RAG only) |

The home-grown CI framework (FIRST/Virtues) remains required. DeepEval/Promptfoo/RAGAS are **additional** gates, not replacements.

---

## 9. ADR Triggers

An ADR is required when:

- Replacing DeepEval, Promptfoo, or RAGAS with a different tool
- Disabling LLM evaluation for a production feature with `mode: llm`
- Changing evaluation thresholds below the minimums
- Introducing a custom evaluation metric not covered by standard eval_class values

---

## 10. Prohibited Patterns

- Using DeepEval for adversarial testing (Promptfoo owns this)
- Using Promptfoo for quality metrics (DeepEval owns this)
- Using RAGAS on non-retrieval features
- Skipping DeepEval for `mode: llm` features
- Importing `deepeval`, `promptfoo`, or `ragas` outside `tests/eval/`
- Storing evaluation datasets outside version control
