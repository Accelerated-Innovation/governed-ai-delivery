# Guardrails Rules

These rules apply when editing files in the guardrails adapter layer.

Contract: `docs/backend/architecture/GUARDRAILS_CONTRACT.md`

---

## Rules

- NeMo Guardrails handles conversational safety — dialog flow, topic boundaries, jailbreak prevention
- Guardrails AI handles structured output validation — JSON schema enforcement on LLM responses
- The guardrail mode declared in `architecture_preflight.md` section 12 must match the implementation
- Both tools are adapters behind `GuardrailPort` — domain services call the port, never the tools directly
- NeMo Colang definitions live in `adapters/guardrails/nemo/rails/`
- Guardrails AI guard definitions live in `adapters/guardrails/validators/`
- NeMo must reference the LiteLLM model alias, not a direct provider
- Guardrails AI validators from the hub must be pinned to specific versions

## Prohibited

- Importing `nemoguardrails` or `guardrails` outside `adapters/guardrails/`
- Using NeMo for output schema validation (Guardrails AI owns this)
- Using Guardrails AI for topic boundary enforcement (NeMo owns this)
- Setting guardrail mode to `none` for user-facing features without ADR justification
- Hardcoding guardrail config in domain code
