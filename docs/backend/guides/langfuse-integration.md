# Langfuse Integration Guide

Practical guide for configuring Langfuse for trace storage, prompt versioning, and production monitoring.

Contract: `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`

---

## Installation

```bash
pip install langfuse
```

---

## Configuration

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com   # or self-hosted URL
```

---

## Trace Viewing

Langfuse receives traces from OpenLLMetry automatically. Navigate to the Langfuse dashboard to:

- View end-to-end request traces
- Inspect individual LLM calls (model, tokens, latency, cost)
- Filter by user, session, or feature
- Identify slow or expensive calls

---

## Prompt Management

L5 uses Langfuse for prompt versioning instead of file-based prompts.

### Creating Prompts in Langfuse

1. Navigate to Prompts in the Langfuse dashboard
2. Create a prompt with a name (e.g., `summarize-v1`)
3. Define the prompt template with variables: `Summarize the following: {{document}}`
4. Publish the prompt version

### Fetching Prompts in Code

```python
# In adapters/llm/ or adapters/observability/
from langfuse import Langfuse

langfuse = Langfuse()
prompt = langfuse.get_prompt("summarize-v1")
compiled = prompt.compile(document="...")
```

### Versioning

- Langfuse tracks prompt versions automatically
- Use the dashboard to compare versions and roll back
- Prompt changes do not require code deployments

---

## Evaluation Dashboards

DeepEval and RAGAS results can be sent to Langfuse for visualization:

```python
from langfuse import Langfuse

langfuse = Langfuse()
langfuse.score(
    trace_id=trace_id,
    name="faithfulness",
    value=0.92,
)
```

---

## Production Monitoring

Langfuse provides production dashboards for:

- Latency trends (p50, p95, p99)
- Cost trends (daily, weekly, per-model)
- Error rates and failure patterns
- Token usage distribution

---

## Environment Matrix

| Environment | Langfuse Active | Notes |
|-------------|----------------|-------|
| Local dev | Optional | Useful for debugging traces |
| CI | Disabled | No external telemetry in CI |
| Staging | Enabled | Integration testing visibility |
| Production | **Required** | Mandatory for LLM features |
