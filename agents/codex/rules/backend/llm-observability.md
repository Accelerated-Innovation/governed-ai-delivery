# LLM Observability Rules

These rules apply when editing files in the observability adapter layer.

Contract: `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`

---

## Rules

- OpenLLMetry handles telemetry emission — auto-instruments LiteLLM calls with LLM-specific spans
- Langfuse handles trace storage and visualization — receives OTel spans, provides dashboards
- OpenLLMetry initialization lives in `adapters/observability/` at application startup
- Langfuse SDK is imported only in `adapters/observability/`
- Domain services use `ObservabilityPort` — never OpenLLMetry or Langfuse directly
- Prompt versioning is managed in Langfuse — domain code references prompt names, not content
- The existing structlog + OpenTelemetry setup is preserved — OpenLLMetry extends it

## Prohibited

- Importing `traceloop`, `langfuse`, or `openllmetry` outside `adapters/observability/`
- Embedding prompt content in source code (use Langfuse prompt management)
- Using LangSmith or Arize (replaced by Langfuse in L5)
- Disabling telemetry in production without an ADR
