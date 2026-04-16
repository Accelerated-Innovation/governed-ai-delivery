# LLM Gateway Rules

These rules apply when editing files in the LLM adapter layer.

Contract: `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

---

## Rules

- All LLM completion and chat requests must route through LiteLLM
- `LLMPort` (in `ports/outbound/`) defines the contract — domain services call the port, never LiteLLM directly
- `LiteLLMAdapter` (in `adapters/llm/`) is the only implementation of `LLMPort`
- Provider SDK packages (`openai`, `anthropic`, `cohere`) must not be imported outside `adapters/llm/`
- Model names must use LiteLLM aliases — do not hardcode provider-specific model IDs in domain code
- Fallback and retry logic is LiteLLM's responsibility — do not implement in application code
- Cost tracking is emitted via OpenLLMetry telemetry — do not build custom cost tracking
- When using LangGraph or LangChain, LLM calls within graph nodes must route through `LLMPort`

## Prohibited

- Importing `openai`, `anthropic`, or other provider SDKs outside this directory
- Calling LLM APIs from domain services without going through `LLMPort`
- Hardcoding model names or provider endpoints in domain or service code
- Implementing retry/fallback logic outside LiteLLM configuration
