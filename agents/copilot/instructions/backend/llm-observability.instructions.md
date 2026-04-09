# LLM Observability Instructions

These instructions apply when editing files in `**/adapters/observability/**`.

Contract: `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md`

---

- OpenLLMetry emits telemetry — auto-instruments LiteLLM with LLM-specific spans
- Langfuse stores and visualizes traces — receives OTel spans, provides dashboards
- OpenLLMetry initialization lives in `adapters/observability/` at startup
- Langfuse SDK is imported only in `adapters/observability/`
- Domain services use `ObservabilityPort` — never OpenLLMetry or Langfuse directly
- Prompt versioning is managed in Langfuse, not in code files
- The existing structlog + OpenTelemetry setup is preserved

**Prohibited:** Importing `traceloop`, `langfuse`, or `openllmetry` outside `adapters/observability/`. Embedding prompts in code. Using LangSmith or Arize.
