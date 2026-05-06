# Agent Topology: <feature_name>

> This file is required when `multi_agent: true` is declared in `eval_criteria.yaml`.
> Run `/multi-agent-design <feature_name>` to generate this from guided prompts.
> See `docs/backend/architecture/AGENT_ARCHITECTURE.md` Section 17 for rules.

---

## Orchestrator

- **Role:** TBD — describe what the orchestrator decides and how it routes
- **System Prompt:** `src/agents/orchestrator/system_prompt.md`
- **Model:** TBD — use alias from `docs/backend/architecture/TECH_STACK.md`
- **Routing Strategy:** TBD — describe the conditions that determine which specialist receives the task

---

## Specialist Agents

### <specialist-1-name>

- **Role:** TBD — one sentence describing this agent's bounded responsibility
- **Input State:**
  - `field_name: type` — description
- **Output State:**
  - `field_name: type` — description
- **System Prompt:** `src/agents/<specialist-1-name>/system_prompt.md`
- **Model:** TBD — use alias from `docs/backend/architecture/TECH_STACK.md`
- **Ports Invoked:** TBD — list outbound ports called (e.g., `LLMPort`, `VectorSearchPort`)

### <specialist-2-name>

- **Role:** TBD — one sentence describing this agent's bounded responsibility
- **Input State:**
  - `field_name: type` — description
- **Output State:**
  - `field_name: type` — description
- **System Prompt:** `src/agents/<specialist-2-name>/system_prompt.md`
- **Model:** TBD — use alias from `docs/backend/architecture/TECH_STACK.md`
- **Ports Invoked:** TBD

---

## Routing Logic

Describe the LangGraph edge conditions. Every path to END must be explicit.

```
START → orchestrator
orchestrator → <specialist-1-name>  (condition: TBD)
orchestrator → <specialist-2-name>  (condition: TBD)
<specialist-1-name> → END           (condition: TBD)
<specialist-2-name> → END           (condition: TBD)
```

No implicit recursion or unconditional loops permitted (see Section 13 of `AGENT_ARCHITECTURE.md`).

---

## Failure Modes

- **Per-node timeout:** TBD seconds
- **Graph timeout:** TBD seconds
- **Node failure handling:** TBD — describe what happens when a node raises an exception or times out (e.g., return partial state with `error` field, route to END)
- **Fallback model:** TBD — declare in LiteLLM config, not in graph code

---

## State Schema Reference

State TypedDict defined in: `services/graphs/<feature_name>_state.py`

```python
class <FeatureName>State(TypedDict):
    # inputs
    # intermediate fields
    # outputs
    error: str | None  # populated on node failure
```
