# RAGAS Evaluation Guide

Practical guide for evaluating retrieval quality in RAG pipelines with RAGAS.

Contract: `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

---

## Installation

```bash
pip install ragas
```

---

## When to Use

RAGAS is required only for features that use retrieval-augmented generation (RAG):

- Vector search → context retrieval → LLM generation
- Document retrieval → augmented prompt → LLM response

Do NOT use RAGAS for non-retrieval features.

---

## Available Metrics

| Metric | eval_class | What It Measures |
|--------|-----------|------------------|
| `context_recall` | `ragas_context_recall` | Retriever finds all relevant documents |
| `context_precision` | `ragas_context_precision` | Retrieved documents are relevant (low noise) |
| `faithfulness` | `ragas_faithfulness` | Generated answer is faithful to retrieved context |
| `answer_relevancy` | `ragas_answer_relevancy` | Generated answer addresses the question |

---

## Dataset Preparation

RAGAS requires evaluation datasets with ground truth:

```json
[
    {
        "question": "What is the refund policy?",
        "answer": "Refunds are available within 30 days of purchase.",
        "contexts": [
            "Our refund policy allows returns within 30 days.",
            "Refunds are processed within 5 business days."
        ],
        "ground_truth": "Customers can get refunds within 30 days of purchase."
    }
]
```

Store datasets in `tests/eval/<feature>/eval_sets/rag_dataset.json`.

---

## Running RAGAS with DeepEval

RAGAS metrics can run within the DeepEval test framework:

```python
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    FaithfulnessMetric,
    AnswerRelevancyMetric,
)
from deepeval import assert_test

def test_rag_quality():
    test_case = LLMTestCase(
        input="What is the refund policy?",
        actual_output="Refunds are available within 30 days.",
        retrieval_context=[
            "Our refund policy allows returns within 30 days.",
            "Refunds are processed within 5 business days.",
        ],
        expected_output="Customers can get refunds within 30 days of purchase.",
    )

    metrics = [
        ContextualRecallMetric(threshold=0.8),
        ContextualPrecisionMetric(threshold=0.7),
        FaithfulnessMetric(threshold=0.8),
        AnswerRelevancyMetric(threshold=0.85),
    ]

    assert_test(test_case, metrics)
```

---

## Standalone RAGAS Evaluation

```python
from ragas import evaluate
from ragas.metrics import context_recall, faithfulness, answer_relevancy
from datasets import Dataset

dataset = Dataset.from_dict({
    "question": ["What is the refund policy?"],
    "answer": ["Refunds are available within 30 days."],
    "contexts": [["Our refund policy allows returns within 30 days."]],
    "ground_truth": ["Customers can get refunds within 30 days of purchase."],
})

results = evaluate(dataset, metrics=[context_recall, faithfulness, answer_relevancy])
```

---

## Mapping to eval_criteria.yaml

```yaml
llm_evaluation:
  criteria:
    - name: context_recall
      eval_class: ragas_context_recall
      threshold: 0.8
      fail_on: below_threshold
      tool: ragas
    - name: retrieval_faithfulness
      eval_class: ragas_faithfulness
      threshold: 0.8
      fail_on: below_threshold
      tool: ragas
  dataset: tests/eval/my_feature/eval_sets/rag_dataset.json
```

---

## CI Integration

RAGAS metrics run as part of the DeepEval test suite in `deepeval-gate.yml`. No separate CI gate is needed for RAGAS.
