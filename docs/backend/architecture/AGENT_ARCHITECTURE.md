# Agent Architecture

This document defines the architecture and implementation rules for AI agents in this repository.

Agents must follow the same governance model as the rest of the system:

- Hexagonal architecture
- Evaluation-driven development
- Security and architecture contracts
- Deterministic testing where possible

Agent logic must remain **observable, testable, and replaceable**.

---

# 1. Agent Design Principles

Agents must follow these principles:

- Orchestration must be deterministic
- Agent state must be explicit
- Prompt templates must be versioned
- External tools must be isolated behind adapters
- Domain logic must remain independent of LLM frameworks

Agent behavior must be measurable using evaluation criteria.

---

# 2. Agent Architecture Model

Agents are implemented using **LangGraph** as the primary orchestration framework.

Architecture structure:
```
Agent
│
├── Graph definition
├── Node functions
├── Tool adapters
├── Prompt templates
└── Evaluation hooks
```

Agents must be composed of **explicit graph nodes**, not hidden chains.

---

# 3. LangGraph Usage

LangGraph is the **approved orchestration framework**.

LangGraph is used for:

- multi-step reasoning
- stateful workflows
- tool calling
- deterministic execution paths

Rules:

- Graphs must be defined explicitly
- Graph state must use typed schemas
- Nodes must perform one responsibility
- Execution paths must remain observable

Agent graphs must avoid implicit recursion or uncontrolled loops.

---

# 4. LangChain Usage

LangChain is allowed for:

- model wrappers
- prompt templating
- simple utilities

LangChain must **not** be used as the primary orchestration layer.

Prefer LangGraph when building agent workflows.

---

# 5. Prompt Management

Prompts must be stored in version-controlled files.

Recommended structure:
```
prompts/
agent_prompts/
system_prompts/
task_prompts/
```

Rules:

- Prompts must be named and versioned
- Prompts must not be embedded directly in code
- Prompt changes should be reviewed like code changes

---

# 6. Agent State

Agent state must be explicit and typed.

Recommended pattern:

```python
class AgentState(TypedDict):
    user_input: str
    intermediate_steps: list
    context: dict
```
Rules:

- Avoid hidden state inside closures
- Avoid implicit global state
- State must be observable in logs

# 7. Tool Integration

External tools must be implemented as **adapters**.

Examples:
- database access
- vector search
- external APIs
- document retrieval
- code execution
- LLM calls (via LiteLLM — see `LLM_GATEWAY_CONTRACT.md`)

Tools must live under:
```
adapters/
```
Rules:
- Agents must call tools through adapters
- Domain logic must not call tools directly
- Tool failures must be handled gracefully
- **LLM calls must route through LiteLLM** (Level 5) — no direct provider SDK usage in agent nodes

---

## 7.1 Development Tool Access

AI coding agents may use approved development tools during planning and implementation.

Approved tools include:

- Ruff — Python linting and formatting
- SonarQube — code quality analysis
- Snyk — dependency and security scanning
- import-linter — architecture boundary validation

Agents may use these tools to:

- detect structural complexity
- identify duplication
- resolve lint issues
- identify security vulnerabilities
- validate architectural boundaries

Tool results must be treated as **blocking signals** if they violate project policies.

---

# 8. Ports and Adapters

Agents must follow Hexagonal Architecture.

Agents interact with:
```
src/ports/inbound/
src/ports/outbound/
```
Inbound ports:
- define how the system invokes agent capabilities

Outbound ports:
- define external capabilities required by the agent

Adapters implement the ports.

# 9. Observability

Agent execution must be observable.

Logs must include:
- request_id
- user_id (if applicable)
- agent name
- node execution events
- tool invocation events

Tracing should capture:
- graph execution paths
- node timing
- tool latency

### LLM-Specific Observability (Level 5)

OpenLLMetry auto-instruments LiteLLM calls to capture LLM-specific telemetry:
- model name, provider, token counts, cost, latency
- Traces exported to Langfuse for storage and visualization

See `docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md` for full details.

---

# 10. Evaluation Integration

Agents must support evaluation-driven development.

Evaluation rules are defined in:
```
docs/backend/evaluation/eval_criteria.md
```
Feature-level evaluation configuration lives in:
```
features/<feature>/eval_criteria.yaml
```
Evaluation may include:
- groundedness checks
- hallucination detection
- safety validation
- response structure validation

Evaluation must run in CI.

### LLM Evaluation Tools (Level 5)

| Tool | Responsibility |
|------|---------------|
| DeepEval | Quality metrics (faithfulness, relevancy, hallucination) — dev + CI |
| Promptfoo | Adversarial testing (jailbreak, injection, regression) — CI |
| RAGAS | Retrieval quality (context recall, precision) — CI, RAG only |

See `docs/backend/architecture/EVALUATION_LLM_CONTRACT.md` for full details.

---

# 11. Testing Agents

Agent components must be testable.

Testing categories:

**Unit tests**

Test individual nodes and tool adapters.

**BDD integration tests**

Validate agent behavior through Gherkin scenarios.

**Evaluation tests**

Validate LLM outputs using evaluation criteria.

Testing rules are defined in:
```
docs/backend/architecture/TESTING.md
```

---

# 12. Security

Agents must follow the security patterns defined in:
```
docs/backend/architecture/SECURITY_AUTH_PATTERNS.md
```
Rules:
- Agents must not access raw tokens
- Sensitive data must not be included in prompts
- External tools must validate inputs

---

# 13. Performance Constraints

Agents must avoid:
- infinite loops
- uncontrolled tool recursion
- repeated prompt calls without state changes

Token usage must be monitored.

Graph execution must remain bounded.

---

# 14. ADR Requirements

An ADR is required when:
- introducing a new agent orchestration framework
- changing LangGraph usage patterns
- introducing a new LLM provider
- introducing a new tool capability
- modifying evaluation strategies

ADR template:
```
docs/backend/architecture/ADR/TEMPLATE.md
```

---

# 15. Definition of Done for Agent Features

An agent feature is complete when:
- Gherkin scenarios pass
- evaluation thresholds are satisfied
- architecture boundaries are respected
- tests pass
- CI evaluation gates succeed

---

# 16. Guardrails Integration (Level 5)

Agent features that interact with users must implement runtime guardrails.

| Tool | When to Use |
|------|------------|
| NeMo Guardrails | Conversational features — topic boundaries, jailbreak prevention, dialog flow control |
| Guardrails AI | Features requiring structured LLM output — JSON schema enforcement, field validation |

Both tools are adapters behind `GuardrailPort`. NeMo wraps the LLM call chain (pre/post filtering). Guardrails AI validates output structure after the LLM responds.

Guardrail mode (`nemo`, `guardrails-ai`, `both`, `none`) must be declared in the architecture preflight.

See `docs/backend/architecture/GUARDRAILS_CONTRACT.md` for full details.