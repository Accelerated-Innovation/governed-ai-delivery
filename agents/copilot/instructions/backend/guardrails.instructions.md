# Guardrails Instructions

These instructions apply when editing files in `**/adapters/guardrails/**` and `**/rails/**`.

Contract: `docs/backend/architecture/GUARDRAILS_CONTRACT.md`

---

- NeMo Guardrails handles conversational safety (dialog flow, topic boundaries, jailbreak prevention)
- Guardrails AI handles structured output validation (JSON schema enforcement on LLM responses)
- Both are adapters behind `GuardrailPort` — domain services call the port, never the tools directly
- NeMo Colang definitions live in `adapters/guardrails/nemo/rails/`
- Guardrails AI guard definitions live in `adapters/guardrails/validators/`
- Guardrail mode must match `architecture_preflight.md` section 12

**Prohibited:** Importing `nemoguardrails` or `guardrails` outside `adapters/guardrails/`. Using NeMo for schema validation. Using Guardrails AI for topic boundaries.
