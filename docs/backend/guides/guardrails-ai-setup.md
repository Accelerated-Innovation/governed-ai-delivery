# Guardrails AI Setup Guide

Practical guide for configuring Guardrails AI for structured output validation.

Contract: `docs/backend/architecture/GUARDRAILS_CONTRACT.md`

---

## Installation

```bash
pip install guardrails-ai
guardrails hub install hub://guardrails/valid_length
guardrails hub install hub://guardrails/valid_choices
```

---

## Configuration Structure

Guard definitions live in the adapter layer:

```
adapters/
└── guardrails/
    └── validators/
        ├── summary_guard.py      # Guard for summary output
        └── classification_guard.py  # Guard for classification output
```

---

## Defining Guards

```python
# adapters/guardrails/validators/summary_guard.py
from guardrails import Guard
from guardrails.hub import ValidLength, ReadingTime
from pydantic import BaseModel

class SummaryOutput(BaseModel):
    summary: str
    key_points: list[str]

summary_guard = Guard.for_pydantic(
    output_class=SummaryOutput,
).use_many(
    ValidLength(min=50, max=500, on="summary"),
    ReadingTime(reading_time=30, on="summary"),
)
```

---

## Using Guards with LiteLLM

```python
# In the adapter layer
import litellm

response = summary_guard(
    litellm.completion,
    model="default",
    messages=[{"role": "user", "content": "Summarize this document..."}],
)

# response.validated_output is a SummaryOutput instance
# response.validation_passed is True/False
# On failure, Guardrails AI can auto-retry
```

---

## Available Validators

Common validators from the Guardrails Hub:

| Validator | Purpose |
|-----------|---------|
| `ValidLength` | Enforce min/max character length |
| `ValidChoices` | Constrain to allowed values |
| `ReadingTime` | Enforce readability constraints |
| `ToxicLanguage` | Detect toxic content |
| `DetectPII` | Flag personally identifiable information |
| `ValidJSON` | Ensure valid JSON structure |

Pin validators to specific versions in `requirements.txt`.

---

## Retry on Failure

Guardrails AI can retry LLM calls when validation fails:

```python
guard = Guard.for_pydantic(SummaryOutput).use(
    ValidLength(min=50, max=500, on="summary"),
)

response = guard(
    litellm.completion,
    model="default",
    messages=[...],
    num_reasks=2,  # Retry up to 2 times on validation failure
)
```

---

## Testing

```gherkin
@guardrails
Scenario: LLM output matches expected schema
  Given a summarization request
  When the LLM responds
  Then the output contains a summary field under 500 characters
  And the output contains a key_points list
```

---

## When to Use

Guardrails AI is required when:

- The LLM must produce structured output (JSON, specific fields)
- Field-level constraints must be enforced (length, format, allowed values)
- Output must conform to a Pydantic model

Guardrails AI is NOT for:

- Conversational safety or topic boundaries (use NeMo Guardrails)
- Quality evaluation (use DeepEval)
