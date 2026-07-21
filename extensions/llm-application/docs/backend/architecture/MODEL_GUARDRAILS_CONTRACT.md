# Model Guardrails Contract

## 1. Decision and scope

Every model-backed feature MUST declare a risk-based guardrail policy for input, trusted instructions, retrieved context, model output, proposed tool calls, and user-visible responses. Guardrails are deterministic trusted controls around a probabilistic component; they do not grant authority to the model.

This contract defines required control points and failure behavior without selecting a guardrail, moderation, policy, or schema-validation product.

## 2. Policy definition

Architecture preflight MUST record:

- users, use case, harm categories, and data classes
- trusted and untrusted instruction sources
- allowed and prohibited content or actions
- required input, context, output, and tool-call controls
- structured-output schemas and semantic invariants
- refusal, escalation, quarantine, and degraded behavior
- policy, rule-set, classifier, and threshold versions
- false-positive and false-negative review routes
- evidence and retention requirements

`none` is not a guardrail policy. If a control point is not applicable, the preflight MUST provide a risk-based reason.

## 3. Control pipeline

The governed sequence is:

```text
Request authentication and authorization
    -> input and instruction controls
    -> context and retrieval controls
    -> model gateway invocation
    -> structural and semantic output controls
    -> tool-call validation and fresh authorization
    -> user-visible or side-effect commit
```

The application MAY short-circuit or add controls, but it MUST NOT bypass a required stage. Guardrail adapters MUST remain behind typed application ports.

## 4. Input and instruction controls

- User, document, webpage, image-derived, tool-returned, and retrieved content MUST be treated as untrusted data unless explicitly promoted by a trusted controller.
- Trusted system instructions MUST remain distinguishable from untrusted content throughout prompt assembly.
- Input controls MUST enforce size, encoding, content, data-classification, and policy limits before provider transmission.
- Prompt-injection detection MUST NOT be the sole boundary protecting secrets, permissions, or authoritative state.
- Secrets and privileged instructions MUST not be inserted where untrusted content can cause their disclosure.
- A rejected input MUST produce an explicit policy outcome without echoing unsafe content unnecessarily.

## 5. Context and retrieval controls

- Retrieved items MUST carry source, trust, tenant, classification, and freshness metadata.
- Retrieval filters MUST enforce tenant and authorization boundaries before content enters model context.
- Untrusted retrieved instructions MUST not override application policy or trusted instructions.
- Context construction MUST minimize sensitive data and respect provider residency and retention constraints.
- Missing or conflicting trust metadata MUST block inclusion when the policy requires it.

## 6. Output controls

Output controls are layered:

- Structural validation verifies parseability, schema, types, required fields, ranges, and allowed values.
- Semantic validation verifies application invariants, references, policy, and consistency with authoritative data.
- Content controls apply the declared safety and disclosure policy.
- Grounding checks apply where claims must be supported by supplied sources.

Validation retries MUST be bounded and count against the invocation budget. A repaired or retried response MUST pass the same controls as the original. Invalid output MUST NOT be coerced into authoritative data without an explicit deterministic rule.

## 7. Tool calls and side effects

A model-generated tool call is untrusted proposed data. Before execution, trusted code MUST:

- resolve the tool from an allowlisted registry
- validate arguments against a versioned schema and semantic rules
- apply tenant, user, task, and resource authorization
- obtain fresh approval when policy requires it
- assign an idempotency or operation identity
- enforce budgets, timeouts, rate limits, and destination restrictions
- record the decision and result as evidence

Model confidence, guardrail acceptance, or a valid schema MUST NOT substitute for authorization. Consequential actions require a deterministic commit boundary.

## 8. Failure behavior

- Required guardrail unavailability, timeout, invalid configuration, or ambiguous result MUST fail closed for the protected operation.
- A policy MAY permit a declared degraded read-only response, safe refusal, or human escalation.
- Safety-critical controls MUST NOT silently default to allow.
- The response MUST distinguish policy refusal, invalid output, system failure, and insufficient evidence without exposing exploitable internals.
- Repeated guardrail failure MUST be bounded and observable.

## 9. Versioning and evidence

Every decision MUST be attributable to immutable identities for the policy, rules, classifiers or detectors, schemas, thresholds, prompt, model configuration, and code release. Evidence MUST record the control point, outcome, reason category, and correlation identity while applying the observability contract's content-minimization rules.

A policy or threshold change that can move behavior MUST pass applicable safety and regression evaluation before promotion.

## 10. Verification

Tests MUST cover:

- prompt injection and instruction-precedence attacks
- tenant and authorization filtering for retrieved context
- malformed and semantically invalid structured output
- disallowed content and sensitive-data disclosure
- unknown tools, invalid arguments, stale approval, and unauthorized destinations
- guardrail timeout, unavailability, and ambiguous results
- bounded repair or retry behavior
- false-positive escalation and safe refusal behavior
- policy version and evidence correlation

## 11. ADR triggers

An ADR is required for:

- selecting or replacing a guardrail, moderation, or validation product
- changing a harm category, threshold, refusal, escalation, or fail-open policy
- allowing raw untrusted content to cross a previously enforced boundary
- permitting a model output or tool call to influence authoritative state through a new path
- disabling a normally required control point

## 12. Prohibited patterns

- guardrail SDK imports in domain or application services
- treating prompt-injection detection as an authorization control
- executing model-proposed tools after schema validation alone
- fail-open behavior for a required safety control
- unbounded output-repair loops
- trusting retrieved instructions because they came from an internal index
- logging rejected sensitive content without explicit approved capture policy
