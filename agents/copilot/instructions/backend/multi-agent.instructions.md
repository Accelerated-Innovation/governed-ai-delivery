# Multi-Agent Instructions

These instructions apply when editing files in `**/agents/**, **/graphs/**, **/orchestrators/**`.

Contract: `docs/backend/architecture/AGENT_ARCHITECTURE.md` (Section 17)

---

- Graph definitions live in `services/graphs/` — not in adapters, API routes, or CLI commands
- Graph state must be a `TypedDict` defined in `services/graphs/<feature>_state.py` — no untyped dicts between nodes
- Node functions must have signature `(state: T) -> dict` — pure transformation, no side effects inside the node
- All LLM calls from graph node functions route through `LLMPort` — no direct provider SDK usage
- System prompts are loaded from the file path declared in `agent_topology.md` — never hardcoded as strings in graph code
- All routing between agents goes through LangGraph graph edges — no direct agent-to-agent calls
- `agent_topology.md` must exist and be complete before implementation begins

**Prohibited:** Importing provider SDKs (`openai`, `anthropic`, `cohere`) in graph or orchestrator files. Hardcoding system prompt strings inside node functions. Direct agent-to-agent calls bypassing the graph. Untyped `dict` as graph state. Graph definitions in `adapters/` or `api/` layers. Implicit or unconditional loops.
