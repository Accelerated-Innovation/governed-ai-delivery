# LLM Gateway Contract

This document defines the rules for LLM provider access in this repository.

**LiteLLM is the sole LLM gateway.** All LLM completion and chat requests must route through LiteLLM. No direct provider SDK calls are permitted for inference.

---

## 1. Gateway Ownership

LiteLLM owns:

- Model routing and selection
- Provider abstraction (OpenAI, Anthropic, Azure OpenAI, local models)
- Fallback chains and retry logic
- Cost tracking and budget enforcement
- Rate limiting and load balancing

No other tool or library may perform these functions.

---

## 2. Hexagonal Placement

LiteLLM is an **outbound adapter** in the hexagonal architecture.

```
Domain (services/)
    ↓
LLMPort (ports/outbound/)         ← contract: completion(), chat(), embed()
    ↓
LiteLLMAdapter (adapters/llm/)    ← implementation: routes through LiteLLM proxy
```

Rules:

- Domain services call `LLMPort` — never LiteLLM directly
- `LiteLLMAdapter` is the only implementation of `LLMPort`
- Provider SDK packages (`openai`, `anthropic`, `cohere`) may be installed as dependencies but must not be imported outside `adapters/llm/`
- `adapters/llm/` is the only directory that may import `litellm`

---

## 3. Provider Abstraction

All LLM calls use LiteLLM model aliases:

```python
# Correct — uses LiteLLM model alias
response = llm_port.completion(model="gpt-4o", messages=[...])

# Prohibited — direct provider SDK call
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(...)
```

Model aliases are configured in LiteLLM proxy config, not in application code.

---

## 4. Fallback and Retry

Fallback chains are defined in LiteLLM configuration:

```yaml
model_list:
  - model_name: "primary"
    litellm_params:
      model: "gpt-4o"
  - model_name: "primary"
    litellm_params:
      model: "claude-sonnet-4-20250514"
```

Rules:

- Fallback order is an infrastructure concern — lives in LiteLLM config, not in domain code
- Retry policies (max retries, backoff) are configured in LiteLLM, not in application code
- Application code must handle `LLMPort` failures gracefully (circuit breaker, degraded mode)

---

## 5. Cost Tracking

LiteLLM provides per-request cost tracking.

Rules:

- Cost data must be emitted as telemetry (via OpenLLMetry — see `OBSERVABILITY_LLM_CONTRACT.md`)
- Cost budgets are configured in LiteLLM proxy, not in application code
- Per-feature cost limits should be documented in `nfrs.md` under "LLM Cost"

---

## 6. LangGraph and LangChain Integration

When using LangGraph or LangChain:

- LLM calls within graph nodes must route through the `LLMPort`
- Do not use `ChatOpenAI()` or `ChatAnthropic()` directly — use a LiteLLM-backed wrapper
- The LiteLLM adapter may expose a LangChain-compatible interface for convenience

---

## 7. Configuration

LiteLLM configuration lives in infrastructure, not in application code:

- **Local dev:** environment variables (`LITELLM_API_BASE`, `LITELLM_API_KEY`) or local proxy
- **CI:** mock or minimal proxy config
- **Staging/Production:** LiteLLM proxy server with full model routing

Secrets must use `BaseSettings` — never hardcoded.

See `docs/backend/guides/litellm-setup.md` for configuration details.

---

## 8. ADR Triggers

An ADR is required when:

- Adding a new LLM provider to the routing table
- Changing the fallback chain order
- Bypassing LiteLLM for any LLM call (requires justification)
- Changing cost budget thresholds
- Introducing a self-hosted LLM that requires custom routing

---

## 9. Prohibited Patterns

- Importing `openai`, `anthropic`, or other provider SDKs outside `adapters/llm/`
- Hardcoding model names in domain or service code
- Implementing retry/fallback logic in application code (LiteLLM owns this)
- Calling LLM APIs from domain services without going through `LLMPort`

---

## 10. Enforcement

- **CI:** import-linter rules verify no provider SDK imports outside `adapters/llm/`
- **Agent rules:** path-scoped rules enforce gateway contract at code generation time
- **Architecture preflight:** L5 preflight validates LiteLLM is the configured gateway
