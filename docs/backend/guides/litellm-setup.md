# LiteLLM Setup Guide

Practical guide for configuring LiteLLM as the LLM gateway.

Contract: `docs/backend/architecture/LLM_GATEWAY_CONTRACT.md`

---

## Installation

```bash
pip install litellm
```

---

## Configuration

### Environment Variables

```bash
# LiteLLM proxy mode (recommended for production)
LITELLM_API_BASE=http://localhost:4000
LITELLM_API_KEY=sk-...

# Or direct mode (simpler for local dev)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Proxy Configuration (litellm_config.yaml)

```yaml
model_list:
  - model_name: "default"
    litellm_params:
      model: "gpt-4o"
      api_key: "os.environ/OPENAI_API_KEY"

  - model_name: "default"
    litellm_params:
      model: "claude-sonnet-4-20250514"
      api_key: "os.environ/ANTHROPIC_API_KEY"

  - model_name: "fast"
    litellm_params:
      model: "gpt-4o-mini"
      api_key: "os.environ/OPENAI_API_KEY"

litellm_settings:
  drop_params: true
  set_verbose: false
  max_retries: 3
  request_timeout: 30

general_settings:
  master_key: "os.environ/LITELLM_MASTER_KEY"
```

### Running the Proxy

```bash
litellm --config litellm_config.yaml --port 4000
```

---

## Adapter Pattern

```python
# ports/outbound/llm_port.py
from abc import ABC, abstractmethod

class LLMPort(ABC):
    @abstractmethod
    async def completion(self, model: str, messages: list[dict], **kwargs) -> str:
        ...

# adapters/llm/litellm_adapter.py
import litellm

class LiteLLMAdapter(LLMPort):
    async def completion(self, model: str, messages: list[dict], **kwargs) -> str:
        response = await litellm.acompletion(model=model, messages=messages, **kwargs)
        return response.choices[0].message.content
```

---

## Fallback Chains

LiteLLM handles fallback automatically when multiple models share the same `model_name`. If the first provider fails, LiteLLM routes to the next.

---

## Cost Tracking

LiteLLM tracks cost per request. Access via:

```python
response = await litellm.acompletion(model="default", messages=[...])
cost = response._hidden_params.get("response_cost", 0)
```

Cost data is also emitted via OpenLLMetry telemetry.

---

## Testing

For unit tests, mock the `LLMPort` — do not call LiteLLM:

```python
mock_llm = Mock(spec=LLMPort)
mock_llm.completion.return_value = "mocked response"
```

For integration tests, use LiteLLM's mock provider or a local model.
