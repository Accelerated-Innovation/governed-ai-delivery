# OpenLLMetry Setup Guide

Practical guide for configuring OpenLLMetry for LLM telemetry emission.

Contract: `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`

---

## Installation

```bash
pip install traceloop-sdk
```

---

## Initialization

Add to your application bootstrap (in `adapters/observability/`):

```python
from traceloop.sdk import Traceloop

Traceloop.init(
    app_name="my-service",
    disable_batch=False,
)
```

This auto-instruments LiteLLM, LangChain, and LangGraph calls.

---

## What Gets Captured

OpenLLMetry automatically captures:

| Attribute | Description |
|-----------|-------------|
| `llm.request.model` | Model name used |
| `llm.usage.prompt_tokens` | Input token count |
| `llm.usage.completion_tokens` | Output token count |
| `llm.usage.total_tokens` | Total token count |
| `gen_ai.response.cost` | Cost per request |
| `llm.request.duration` | Latency in milliseconds |

---

## Export to Langfuse

Configure the OTel exporter to send to Langfuse:

```bash
TRACELOOP_BASE_URL=https://cloud.langfuse.com   # or self-hosted URL
TRACELOOP_HEADERS="Authorization=Bearer <langfuse-public-key>"
```

Or configure programmatically:

```python
Traceloop.init(
    app_name="my-service",
    api_endpoint="https://cloud.langfuse.com",
    headers={"Authorization": f"Bearer {settings.langfuse_public_key}"},
)
```

---

## Custom Span Attributes

Add feature-specific context to spans:

```python
from traceloop.sdk.decorators import workflow, task

@workflow(name="summarize-document")
async def summarize(document: str) -> str:
    ...

@task(name="retrieve-context")
async def retrieve(query: str) -> list[str]:
    ...
```

---

## Disabling in CI

```bash
TRACELOOP_ENABLED=false
```

---

## Testing

OpenLLMetry is an infrastructure concern. Unit tests should mock the `ObservabilityPort`, not OpenLLMetry directly.
