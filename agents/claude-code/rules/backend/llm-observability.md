# LLM Observability Rules

These rules apply when editing model telemetry and observability adapters.

Contract: `extensions/llm-application/docs/backend/architecture/LLM_OBSERVABILITY_CONTRACT.md`

---

## Rules

- Model telemetry is emitted through the application observability port; telemetry SDKs remain in adapters
- Correlate each invocation with request, trace, feature, logical model, resolved model, prompt, policy, and configuration identities
- Record completion, refusal, failure, cancellation, incomplete streams, latency, retries, fallback, and normalized usage
- Mark unavailable provider fields as unavailable; do not report them as zero
- Raw prompts, responses, retrieved content, tool arguments, secrets, and personal data are not captured by default
- Any approved content capture is scoped, redacted before export, access-controlled, retained for a declared period, and automatically expires
- Metric labels use bounded-cardinality values and never contain user or model text
- Export queues, sampling, and retries are bounded; required safety or audit evidence is never silently sampled away
- Record the selected instrumentation and telemetry products in `TECH_STACK.md` or an ADR

## Prohibited

- Importing telemetry vendor SDKs in domain or application services
- Raw prompt or response logging by default
- Secrets, personal data, arbitrary text, or document identifiers in metric labels
- Mutable aliases as the only prompt or model provenance
- Treating missing usage, export failure, or a dashboard screenshot as complete governance evidence
