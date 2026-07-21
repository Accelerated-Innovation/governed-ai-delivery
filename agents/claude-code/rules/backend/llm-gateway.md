# LLM Gateway Rules

These rules apply when editing model gateway ports and adapters.

Contract: `extensions/llm-application/docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

---

## Rules

- Every model invocation routes through an application-owned, typed outbound gateway port
- Provider and gateway SDKs remain inside outbound adapters; their types never escape into domain or application services
- Callers use logical capabilities or model aliases, not provider-specific model identifiers
- Routing, fallback, retry, timeout, residency, retention, rate, and budget policy live in governed configuration
- Retries and fallbacks are bounded by one end-to-end deadline and must preserve capability, data, and safety policy
- Streaming output remains incomplete until all required validation succeeds
- Model-proposed tool calls are data; trusted code validates and authorizes them before execution
- The adapter emits normalized usage, resolved model identity, failure category, and correlation evidence
- Record the selected gateway or provider product in `TECH_STACK.md` or an ADR; product choice does not change these boundaries

## Prohibited

- Importing provider or gateway SDKs outside approved adapters
- Direct model calls from domain or application services
- Hard-coding provider model identifiers, endpoints, credentials, routing, or fallback logic in domain code
- Returning provider-specific response, exception, stream, or tool-call types through the application port
- Unbounded retries, silent fallback, or tool execution based only on model output
