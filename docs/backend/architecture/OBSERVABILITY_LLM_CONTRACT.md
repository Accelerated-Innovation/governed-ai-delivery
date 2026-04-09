# LLM Observability Contract

This document defines the observability standards for LLM operations in this repository.

**OpenLLMetry emits telemetry. Langfuse stores and visualizes it.** These roles are non-overlapping.

---

## 1. Tool Ownership

| Tool | Role | Scope |
|------|------|-------|
| **OpenLLMetry** | Telemetry emission | Auto-instruments LiteLLM calls, emits OpenTelemetry spans with LLM-specific attributes (model, tokens, cost, latency) |
| **Langfuse** | Trace storage and visibility | Receives OTel spans, provides trace UI, prompt versioning, evaluation dashboards, production monitoring |

No other tool may perform these functions. Langfuse replaces LangSmith and Arize from the previous evaluation stack.

---

## 2. Hexagonal Placement

LLM observability extends the existing `ObservabilityPort` pattern:

```
Domain (services/)
    ↓
ObservabilityPort (ports/outbound/)    ← contract: record_event(), start_span()
    ↓
LLMObservabilityAdapter (adapters/observability/)
    ├── structlog (structured logging — existing)
    ├── OpenTelemetry SDK (traces/metrics — existing)
    ├── OpenLLMetry (LLM-specific instrumentation — L5)
    └── Langfuse SDK (trace export — L5)
```

Rules:

- Domain services call `ObservabilityPort` — never OpenLLMetry or Langfuse directly
- OpenLLMetry auto-instrumentation is initialized in the adapter layer at application startup
- Langfuse SDK is imported only in `adapters/observability/`
- The existing structlog + OpenTelemetry setup is preserved — OpenLLMetry extends it, does not replace it

---

## 3. OpenLLMetry Integration

OpenLLMetry auto-instruments supported libraries (LiteLLM, LangChain, LangGraph) at startup:

```python
# In adapters/observability/ — application bootstrap
from traceloop.sdk import Traceloop
Traceloop.init(app_name="my-service")
```

This automatically captures:

- LLM call spans (model, provider, prompt tokens, completion tokens)
- Cost per call
- Latency per call
- Error rates

Rules:

- OpenLLMetry initialization lives in `adapters/observability/`, not in domain code
- Custom span attributes may be added via the ObservabilityPort
- OpenLLMetry must not be imported in domain or service layers

---

## 4. Langfuse Integration

Langfuse receives telemetry via OpenTelemetry export:

```
OpenLLMetry → OTel Collector → Langfuse
```

Langfuse provides:

- **Trace viewing:** end-to-end request traces including LLM calls
- **Prompt versioning:** prompts managed and versioned in Langfuse, not in code files
- **Evaluation visibility:** DeepEval and RAGAS results viewable in Langfuse dashboard
- **Production monitoring:** latency trends, cost trends, error rates

Rules:

- Langfuse SDK is imported only in `adapters/observability/`
- Prompt versioning in Langfuse is the L5 standard — prompts are fetched from Langfuse at runtime via the adapter
- Domain code references prompt names, not prompt content

---

## 5. Prompt Versioning

L5 replaces file-based prompt management with Langfuse prompt versioning:

```python
# Domain calls port with prompt name
response = llm_port.completion(prompt_name="summarize-v2", variables={...})

# Adapter resolves prompt from Langfuse
prompt = langfuse.get_prompt("summarize-v2")
```

Rules:

- Prompt names are constants defined in domain code
- Prompt content is managed in Langfuse (versioned, A/B testable)
- Fallback: if Langfuse is unavailable, adapter may use cached prompts
- Prompt changes do not require code deployments

---

## 6. Environment Matrix

| Environment | OpenLLMetry | Langfuse | Notes |
|-------------|------------|----------|-------|
| Local dev | enabled | optional | Developers may run local Langfuse or disable |
| CI | disabled | disabled | No external telemetry in CI — use mocks |
| Staging | enabled | enabled | Full observability for integration testing |
| Production | enabled | **required** | Production LLM features must have Langfuse tracing |

---

## 7. Configuration

```bash
# OpenLLMetry
TRACELOOP_BASE_URL=...          # OTel collector endpoint

# Langfuse
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=...               # Self-hosted or cloud URL
```

Secrets must use `BaseSettings` — never hardcoded.

See `docs/backend/guides/openllmetry-setup.md` and `docs/backend/guides/langfuse-integration.md` for details.

---

## 8. ADR Triggers

An ADR is required when:

- Replacing OpenLLMetry with a different LLM instrumentation library
- Replacing Langfuse with a different trace storage backend
- Disabling observability for production LLM features
- Changing the prompt versioning strategy (e.g., back to file-based)

---

## 9. Prohibited Patterns

- Importing `traceloop`, `langfuse`, or `openllmetry` outside `adapters/observability/`
- Embedding prompt content in source code (use Langfuse prompt management)
- Disabling telemetry in production without an ADR
- Using LangSmith or Arize (replaced by Langfuse in L5)
