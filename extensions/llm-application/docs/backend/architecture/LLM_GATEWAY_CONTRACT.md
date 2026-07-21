# LLM Gateway Contract

## 1. Decision and scope

Every model invocation MUST cross an application-owned outbound port and a governed gateway adapter. The gateway contract applies to text generation, chat, embeddings, reranking, tool-call proposals, structured generation, and streaming responses.

This contract defines behavior, boundaries, and evidence. It does not select a provider, model family, SDK, proxy, or framework.

## 2. Ownership boundary

The application owns a provider-neutral `ModelGatewayPort`. Domain and application services depend only on that port. Provider clients, hosted-gateway clients, and framework-specific model wrappers remain inside outbound adapters.

```text
Application service
    -> ModelGatewayPort
        -> Gateway adapter
            -> Provider or hosted gateway
```

Rules:

- Domain code MUST NOT import a provider or gateway SDK.
- Provider request, response, exception, stream, and tool-call types MUST NOT escape the adapter.
- The port MUST expose application concepts and typed envelopes, not a lowest-common-denominator copy of one vendor API.
- Provider-specific capability gaps MUST be normalized by the adapter or rejected explicitly.
- Direct provider access outside approved adapters is prohibited.

## 3. Invocation envelope

Each request MUST identify:

- a logical capability or model alias rather than a provider model identifier
- the prompt or instruction version and variable inputs
- output mode and schema when structured output is expected
- timeout, cancellation, and maximum output bounds
- tenant, feature, data-classification, and request correlation context
- tool definitions and allowed tool names when tool calling is enabled
- an idempotency or operation identity when a retry could repeat a consequential downstream action

Each response MUST normalize:

- output content or typed structured result
- finish reason and refusal state
- logical model alias and resolved provider/model identity
- prompt, input, output, cached, and reasoning usage when available
- latency, retry, fallback, and cache metadata
- proposed tool calls without executing them
- a stable error category when the invocation fails

Unknown provider fields MUST be preserved only inside adapter-owned diagnostic metadata and MUST NOT become domain dependencies.

## 4. Routing and configuration

Routing policy belongs to deployable configuration or an infrastructure policy store. Application code MAY request a logical capability, latency class, quality class, or data-residency class; it MUST NOT choose a provider through conditional domain logic.

Routing policy MUST define:

- allowed providers and model versions per environment and data class
- capability constraints such as context window, structured output, tools, or modality
- primary and fallback order
- per-attempt and end-to-end timeouts
- retryable error categories, maximum attempts, and backoff
- rate, concurrency, token, and financial budgets
- residency, retention, and provider training-use restrictions

Resolved model and policy versions MUST be observable for every invocation. A routing change that can alter behavior MUST pass evaluation gates before production promotion.

## 5. Failure, retry, fallback, and streaming

- Retries MUST be bounded and limited to classified transient failures.
- The gateway MUST respect cancellation and an end-to-end deadline across retries and fallbacks.
- A fallback MUST satisfy the request's capability, safety, residency, and policy constraints; availability alone is insufficient.
- Partial streaming output MUST be treated as uncommitted until required validation completes.
- A stream interruption MUST produce an explicit incomplete result; callers MUST NOT treat partial text as success.
- Failures MUST map to stable application categories such as timeout, rate limited, policy rejected, invalid output, unavailable, or provider error.
- Degraded behavior MUST be explicit and testable. Silent model substitution or unbounded retry is prohibited.

## 6. Tools and consequential actions

Model tool calls are proposals. The gateway MAY normalize a proposed call, but it MUST NOT grant authority or execute an external action.

Before execution, trusted application code MUST independently validate the tool identity, arguments, schema, authorization, approval requirements, idempotency, and current policy. A model response MUST NOT directly mutate authoritative state.

## 7. Security and data governance

- Credentials MUST come from an approved secret provider and MUST NOT appear in prompts, source, logs, traces, or evaluation fixtures.
- Input classification MUST be evaluated before data crosses a provider boundary.
- Sensitive data MUST be minimized, redacted, tokenized, or blocked according to policy.
- Provider retention, training use, geographic processing, and subprocessors MUST satisfy the applicable data policy.
- Untrusted retrieved content and user content MUST remain distinguishable from trusted instructions.
- Prompt and tool definitions MUST be protected from untrusted override according to `MODEL_GUARDRAILS_CONTRACT.md`.

## 8. Usage and budgets

The gateway MUST emit normalized usage and budget evidence for each attempt and the overall invocation. When a provider does not return a field, the adapter MUST mark it unavailable rather than fabricate a value.

Budget controls MUST support the scopes required by the project, such as request, task, feature, tenant, and time window. A budget breach MUST stop or degrade execution according to declared policy. It MUST NOT silently continue at unlimited cost.

## 9. Verification

Tests MUST cover:

- provider types do not cross the port
- logical aliases resolve only to approved configurations
- timeout, cancellation, bounded retry, and fallback behavior
- capability and data-policy rejection
- streaming interruption and incomplete output
- normalized usage and error categories
- tool calls remain proposals until independently authorized
- sensitive data is not emitted to prohibited providers or telemetry

Contract tests SHOULD run against adapter fakes and at least one approved integration environment. Tests MUST NOT depend on nondeterministic live model quality unless explicitly classified as evaluation tests.

## 10. ADR triggers

An ADR is required for:

- selecting or replacing a gateway product or provider
- adding a new provider or model class
- changing routing, fallback, residency, retention, or budget policy
- allowing a direct provider path
- changing the port envelope in a way that exposes provider semantics

An ADR cannot waive security, privacy, authorization, or evidence obligations without the corresponding governance approval.

## 11. Prohibited patterns

- provider SDK imports in domain or application services
- hard-coded provider model identifiers outside adapter configuration
- provider-specific response objects returned by an application port
- retries without a shared deadline and maximum attempt count
- fallback that weakens data, safety, or capability policy
- model-proposed tool calls executed without deterministic validation and authorization
- treating partial streams or unavailable usage evidence as complete success
