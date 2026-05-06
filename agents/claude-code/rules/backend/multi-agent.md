# Multi-Agent Rules

These rules apply when editing files in agent, graph, and orchestrator layers.

Contract: `docs/backend/architecture/AGENT_ARCHITECTURE.md` (Section 17)

---

## Rules

- Graph definitions live in `services/graphs/` — not in adapters, API routes, or CLI commands
- Graph state must be a `TypedDict` defined in `services/graphs/<feature>_state.py` — no untyped dicts between nodes
- Node functions must have signature `(state: T) -> dict` — pure transformation, no side effects inside the node
- All LLM calls from graph node functions route through `LLMPort` — no direct provider SDK usage
- System prompts are loaded from the file path declared in `agent_topology.md` — never hardcoded as strings in graph code
- All routing between agents goes through LangGraph graph edges — no direct agent-to-agent calls
- `agent_topology.md` must exist and be complete before implementation begins

## Prohibited

- Importing `openai`, `anthropic`, `cohere`, or other provider SDKs in graph or orchestrator files
- Hardcoding system prompt strings inside graph node functions
- Calling one agent's logic directly from another agent's node function
- Defining graph state as untyped `dict`
- Placing graph definitions in `adapters/` or `api/` layers
- Implicit or unconditional loops in the graph definition
