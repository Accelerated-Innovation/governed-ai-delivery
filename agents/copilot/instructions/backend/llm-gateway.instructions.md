# LLM Gateway Instructions

These instructions apply when editing files in `**/adapters/llm/**`.

Contract: `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

---

- All LLM completion and chat requests must route through LiteLLM
- `LLMPort` (in `ports/outbound/`) defines the contract — domain services call the port, never LiteLLM directly
- `LiteLLMAdapter` (in `adapters/llm/`) is the only implementation of `LLMPort`
- Provider SDK packages (`openai`, `anthropic`, `cohere`) must not be imported outside `adapters/llm/`
- Model names must use LiteLLM aliases — do not hardcode provider-specific model IDs
- Fallback and retry logic is LiteLLM's responsibility — do not implement in application code
- When using LangGraph or LangChain, LLM calls must route through `LLMPort`

**Prohibited:** Importing provider SDKs outside this directory. Calling LLM APIs without going through `LLMPort`. Hardcoding model names in domain code.
