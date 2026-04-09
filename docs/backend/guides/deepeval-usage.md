# DeepEval Usage Guide

Practical guide for writing and running LLM evaluation tests with DeepEval.

Contract: `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md`

---

## Installation

```bash
pip install deepeval
```

---

## Test Structure

DeepEval tests live alongside feature tests:

```
tests/
└── eval/
    └── <feature_name>/
        ├── test_quality.py       # DeepEval test cases
        └── eval_sets/
            └── dataset.json      # Input/expected pairs
```

---

## Writing Test Cases

```python
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    HallucinationMetric,
)

def test_summarization_faithfulness():
    test_case = LLMTestCase(
        input="Summarize the Q3 earnings report",
        actual_output="Revenue grew 15% to $2.1B...",
        retrieval_context=["Q3 2025 earnings: Revenue $2.1B, up 15% YoY..."],
    )
    metric = FaithfulnessMetric(threshold=0.8)
    assert_test(test_case, [metric])

def test_answer_relevancy():
    test_case = LLMTestCase(
        input="What was the revenue growth?",
        actual_output="Revenue grew 15% year over year.",
    )
    metric = AnswerRelevancyMetric(threshold=0.85)
    assert_test(test_case, [metric])
```

---

## Available Metrics

| Metric | eval_class | What It Measures |
|--------|-----------|------------------|
| `FaithfulnessMetric` | `deepeval_faithfulness` | Output grounded in provided context |
| `AnswerRelevancyMetric` | `deepeval_answer_relevancy` | Response relevant to question |
| `HallucinationMetric` | `deepeval_hallucination` | No fabricated facts |
| `ContextualRelevancyMetric` | `deepeval_contextual_relevancy` | Retrieved context is relevant |
| `GEval` | `deepeval_geval` | Custom LLM-as-judge criteria |

---

## GEval (Custom Criteria)

```python
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

metric = GEval(
    name="Conciseness",
    criteria="The response should be concise and under 100 words",
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.7,
)
```

---

## Datasets

Store evaluation datasets in `tests/eval/<feature>/eval_sets/`:

```json
[
    {
        "input": "What is the return policy?",
        "expected_output": "You can return items within 30 days.",
        "context": ["Return policy: 30-day window for all purchases."]
    }
]
```

---

## Running in CI

```bash
deepeval test run tests/eval/<feature>/test_quality.py
```

The `deepeval-gate.yml` CI template automates this for all features with `deepeval_*` eval_class values.

---

## Mapping to eval_criteria.yaml

Each DeepEval test should correspond to a criterion in `eval_criteria.yaml`:

```yaml
llm_evaluation:
  criteria:
    - name: faithfulness
      eval_class: deepeval_faithfulness
      threshold: 0.8
      fail_on: below_threshold
      tool: deepeval
  dataset: tests/eval/my_feature/eval_sets/dataset.json
  fail_on_regression: true
```
