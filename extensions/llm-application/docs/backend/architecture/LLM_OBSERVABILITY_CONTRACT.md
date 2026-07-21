# LLM Observability Contract

## 1. Decision and scope

Model operations MUST emit privacy-aware telemetry through the application's observability port. Telemetry MUST make behavior, performance, usage, policy decisions, and configuration provenance diagnosable without making raw prompts, responses, retrieved content, or secrets observable by default.

This contract is telemetry-backend and instrumentation-library neutral.

## 2. Boundary and correlation

Instrumentation libraries and telemetry exporters are outbound adapters. Domain and application services use the existing observability port and do not import telemetry vendor SDKs.

Every model invocation MUST correlate:

- request, trace, and invocation identities
- feature, tenant, and environment where policy permits
- logical model alias and resolved provider/model identity
- prompt, routing, guardrail, retrieval, tool-definition, and configuration versions
- parent task or agent-run identity when applicable
- evaluation subject identity when the invocation belongs to an evaluation run

Identifiers MUST be opaque and MUST NOT encode sensitive prompt or user content.

## 3. Required signals

The adapter MUST emit normalized signals for:

- start, completion, failure, cancellation, and incomplete stream
- latency, time to first token when available, and retry/fallback attempts
- normalized input, output, cached, and reasoning usage when available
- estimated or reported cost with currency and calculation provenance
- timeout, rate-limit, policy rejection, invalid-output, and provider-error categories
- guardrail decisions by policy and rule identity
- proposed tool-call names and validation outcomes, without unsafe argument disclosure
- cache use, retrieval references, and response finish state where applicable

Unavailable provider fields MUST be marked unavailable. They MUST NOT be reported as zero or inferred without labelling the inference.

## 4. Content capture and redaction

Raw prompt, response, retrieved document, image, audio, tool argument, credential, and personal data capture MUST be disabled by default.

If content capture is approved for a defined environment or diagnostic window, policy MUST specify:

- purpose and lawful or contractual basis
- allowed fields and data classes
- sampling rate and affected tenants
- access controls and approvers
- encryption, residency, retention, and deletion
- redaction or tokenization before export
- an automatic expiry and rollback path

Redaction MUST occur before data leaves the application trust boundary. A downstream dashboard filter is not a redaction control.

## 5. Prompt and configuration provenance

Prompts MAY be stored in source control, a configuration service, or a prompt-management system. Regardless of storage, telemetry MUST reference immutable prompt and configuration identities sufficient to reproduce the invocation without logging prompt content.

A mutable label such as `production` is insufficient by itself. Record a digest, version, release identity, or equivalent immutable reference for every behavior-moving configuration.

## 6. Cardinality, sampling, and reliability

- Metrics labels MUST use bounded-cardinality dimensions.
- User text, prompts, response text, document identifiers, and arbitrary model errors MUST NOT become metric labels.
- Sampling policy MUST preserve error, policy-rejection, budget-breach, and safety-relevant events required for evidence.
- Telemetry failure MUST NOT crash the primary request unless the feature explicitly requires audit evidence before proceeding.
- When evidence is required for a consequential operation, inability to persist that evidence MUST block or defer the operation according to policy.
- Export retries and queues MUST be bounded and backpressure-aware.

## 7. Service objectives and alerts

Operational objectives SHOULD cover the dimensions needed by the feature, including:

- invocation success and policy-rejection rates
- latency and time to first token
- invalid structured-output rate
- retry and fallback rate
- token or unit usage and cost
- guardrail and safety-event rate
- evaluation drift or production-quality signals

Alerts MUST distinguish provider availability, application defects, policy rejections, and budget enforcement. A policy rejection is not automatically a service error.

## 8. Evidence and access

Telemetry used as governance evidence MUST identify its schema, producer, time range, retention, and integrity controls. Dashboard screenshots alone are not durable evidence when machine-readable records are required.

Access to model telemetry MUST follow least privilege. Read access to operational metrics does not imply access to captured content. Administrative access, content access, export, and deletion SHOULD be separately auditable.

## 9. Verification

Tests MUST cover:

- correlation across gateway attempts, guardrails, tool proposals, and evaluation runs
- normalized fields for success, refusal, failure, cancellation, and incomplete streams
- missing provider usage fields
- redaction before export
- raw-content capture disabled by default
- bounded-cardinality metrics
- sampling exceptions for required evidence
- exporter failure, queue pressure, and evidence-required fail-closed behavior

## 10. ADR triggers

An ADR is required for:

- selecting or replacing a telemetry or prompt-management product
- enabling raw content capture or changing its retention
- changing immutable prompt or model provenance strategy
- sampling away an event class used for safety or release evidence
- making telemetry availability a synchronous execution dependency

## 11. Prohibited patterns

- telemetry SDK imports in domain or application services
- raw prompt or response logging by default
- secrets, credentials, personal data, or untrusted text in metric labels
- provider fields reported as zero when they are unavailable
- mutable aliases as the only model or prompt provenance
- unbounded exporter queues or retries
- treating a dashboard as the sole auditable evidence source
