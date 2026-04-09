# Guardrails Contract

This document defines the runtime safety and output validation standards for LLM features in this repository.

**NeMo Guardrails handles conversation flow safety. Guardrails AI handles structured output validation.** These roles are non-overlapping.

---

## 1. Tool Ownership

| Tool | Role | Scope |
|------|------|-------|
| **NeMo Guardrails** | Conversational safety | Dialog flow control, topic boundaries, jailbreak prevention, input/output content filtering |
| **Guardrails AI** | Structured output validation | JSON schema enforcement on LLM responses, field-level validators, type coercion, retry on validation failure |

Rules:

- NeMo Guardrails is for **behavioral safety** — what the LLM is allowed to discuss and how
- Guardrails AI is for **structural correctness** — whether the LLM output matches the expected schema
- Do not use NeMo for output schema validation
- Do not use Guardrails AI for topic boundary enforcement

---

## 2. Guardrail Mode Selection

Every L5 feature must declare a guardrail mode in the architecture preflight:

| Mode | When to Use |
|------|------------|
| `nemo` | Conversational features with user-facing chat, topic boundaries, or safety requirements |
| `guardrails-ai` | Features requiring structured LLM output (JSON, enum fields, validated schemas) |
| `both` | Conversational features that also produce structured output |
| `none` | Features where LLM output is purely internal and does not face users (requires justification) |

The selected mode must be documented in `architecture_preflight.md` section 12 and enforced in implementation.

---

## 3. Hexagonal Placement

Both guardrail tools are **adapters** in the hexagonal architecture:

```
Domain (services/)
    ↓
GuardrailPort (ports/outbound/)          ← contract: validate_input(), validate_output()
    ↓
├── NeMoGuardrailAdapter (adapters/guardrails/nemo/)
│   └── Colang dialog definitions, rail configs
└── GuardrailsAIAdapter (adapters/guardrails/validators/)
    └── Guard definitions, validator configs
```

Rules:

- Domain services call `GuardrailPort` — never NeMo or Guardrails AI directly
- Guardrail adapters live in `adapters/guardrails/`
- NeMo Colang files live in `adapters/guardrails/nemo/rails/`
- Guardrails AI guard definitions live in `adapters/guardrails/validators/`
- Neither NeMo nor Guardrails AI may be imported in domain or service layers

---

## 4. NeMo Guardrails

NeMo Guardrails uses Colang to define conversational rails:

```colang
define user ask about competitors
  "What about [competitor]?"
  "How does [competitor] compare?"

define bot refuse competitor discussion
  "I can only discuss our products. How can I help you with those?"

define flow
  user ask about competitors
  bot refuse competitor discussion
```

Rules:

- Rail definitions are versioned in `adapters/guardrails/nemo/rails/`
- NeMo wraps the LLM call chain — it sits between the request and LiteLLM
- NeMo config must reference the LiteLLM model alias, not a direct provider
- Jailbreak detection rails should be enabled by default for user-facing features

See `docs/backend/guides/nemo-guardrails-setup.md` for configuration details.

---

## 5. Guardrails AI

Guardrails AI validates LLM output structure:

```python
from guardrails import Guard
from guardrails.hub import ValidLength, ValidChoices

guard = Guard().use_many(
    ValidLength(min=1, max=500, on="summary"),
    ValidChoices(choices=["positive", "negative", "neutral"], on="sentiment"),
)
```

Rules:

- Guard definitions live in `adapters/guardrails/validators/`
- Guards validate the LLM response after it returns from LiteLLM
- On validation failure, the adapter may retry the LLM call (with retry limits from LiteLLM config)
- Guardrails AI validators from the hub must be approved and pinned to versions

See `docs/backend/guides/guardrails-ai-setup.md` for configuration details.

---

## 6. Integration with LiteLLM

Both guardrail tools integrate with LiteLLM through the adapter layer:

```
User Request
    ↓
NeMo Guardrails (input filtering)     ← if mode is nemo or both
    ↓
LiteLLM (model routing)               ← via LLMPort / LiteLLMAdapter
    ↓
Guardrails AI (output validation)      ← if mode is guardrails-ai or both
    ↓
NeMo Guardrails (output filtering)     ← if mode is nemo or both
    ↓
Response
```

---

## 7. Testing Guardrails

Guardrail behavior must be tested:

- **NeMo:** test that prohibited topics are blocked, jailbreak attempts are caught
- **Guardrails AI:** test that malformed LLM output triggers retry or rejection
- **Both:** integration tests for the full pipeline (input → guardrails → LLM → validation → output)

Use `@guardrails` Gherkin tag for guardrail-related scenarios.

---

## 8. ADR Triggers

An ADR is required when:

- Changing the guardrail mode for a production feature
- Disabling guardrails for a user-facing LLM feature
- Adding a new Guardrails AI validator from the hub
- Modifying NeMo rail definitions that affect safety boundaries
- Introducing a custom guardrail mechanism not listed here

---

## 9. Prohibited Patterns

- Importing `nemoguardrails` or `guardrails` outside `adapters/guardrails/`
- Using NeMo for output schema validation (Guardrails AI owns this)
- Using Guardrails AI for topic boundary enforcement (NeMo owns this)
- Setting guardrail mode to `none` for user-facing features without ADR justification
- Hardcoding guardrail configurations in domain code
