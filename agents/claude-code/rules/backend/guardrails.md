# Model Guardrail Rules

These rules apply when editing model input, context, output, or tool-call controls.

Contract: `extensions/llm-application/docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md`

---

## Rules

- Architecture preflight declares the risks, trusted and untrusted sources, required control points, policies, versions, and failure behavior
- User, retrieved, document-derived, image-derived, and tool-returned content remains untrusted unless a trusted controller promotes it
- Input and context controls run before provider transmission; output controls include structural, semantic, content, and grounding checks as applicable
- Guardrail libraries remain in adapters behind typed application ports
- Validation and repair retries are bounded and count against the invocation budget
- A model-proposed tool call is untrusted data and requires schema checks, semantic checks, fresh authorization, and any required approval before execution
- A required guardrail timeout, outage, invalid configuration, or ambiguous result fails closed for the protected operation
- Every decision records immutable policy, rule, threshold, schema, prompt, model, and correlation identities
- Record selected guardrail products and profiles in `TECH_STACK.md` or an ADR

## Prohibited

- Treating prompt-injection detection, content filtering, or schema validity as authorization
- Executing model-proposed tools after validation alone
- Fail-open defaults for required controls
- Unbounded repair loops or silent coercion of invalid output into authoritative data
- Trusting retrieved instructions merely because they came from an internal source
