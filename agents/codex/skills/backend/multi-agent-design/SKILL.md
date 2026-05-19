---
name: multi-agent-design
description: Design the agent topology for a multi-agent feature and produce agent_topology.md. Use when eval_criteria.yaml declares multi_agent:true or when invoking /multi-agent-design.
---

# Multi-Agent Design

You are designing the agent topology for a feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

Run this skill before `/architecture-preflight` whenever `eval_criteria.yaml` declares `multi_agent: true`.

## Inputs to read

- `features/<feature_name>/nfrs.md` — understand scope and constraints
- `features/<feature_name>/acceptance.feature` — understand required outcomes
- `features/<feature_name>/eval_criteria.yaml` — confirm `multi_agent: true`
- `docs/backend/architecture/AGENT_ARCHITECTURE.md` Section 17 — architecture rules
- `docs/backend/architecture/TECH_STACK.md` — approved model aliases

## Step 1: Justify multi-agent

Answer these questions before proceeding. If the answers do not justify multiple agents, recommend a single-agent design and stop.

- What workflow step genuinely benefits from specialization?
- Would a single agent with tool calls achieve the same outcome? If yes, prefer that.
- Is the expected output quality meaningfully better with specialized agents?

## Step 2: Define the Orchestrator

- What decision does the orchestrator make?
- What is its routing strategy (e.g., classify first, then route)?
- System prompt file path: `src/agents/orchestrator/system_prompt.md`
- Which LLM model alias does it use?

## Step 3: Define each Specialist Agent

For each specialist, specify:
- Role: one sentence
- Input state fields: name and type for each field received from the graph state
- Output state fields: name and type for each field written back to graph state
- System prompt file path: `src/agents/<name>/system_prompt.md`
- LLM model alias
- Outbound ports invoked (e.g., `LLMPort`, `VectorSearchPort`, `DatabasePort`)

Stop if any specialist's role overlaps significantly with another — collapse it.

## Step 4: Define Routing Logic

Map every graph edge with its condition. Every node must have a path to END. No unconditional loops.

Format:
```
START → <node>
<node> → <node>  (condition: <what triggers this edge>)
<node> → END     (condition: <what triggers termination>)
```

## Step 5: Define Failure Modes

- Per-node timeout (seconds)
- Graph-level timeout (seconds)
- What happens when a node fails: return partial state with `error` field, route to END
- Fallback model: declare in LiteLLM config, not in graph code

## Step 6: Define State Schema

Name the `TypedDict` and list all fields with types:
- Input fields (set by the caller)
- Intermediate fields (written and read between nodes)
- Output fields (consumed by the caller)
- `error: str | None` (required — populated on node failure)

## Output

Write `features/<feature_name>/agent_topology.md` following the template in `features/starter_backend_l5/agent_topology.md`.

After writing, confirm:
- [ ] All system prompt paths are declared
- [ ] All state fields are typed
- [ ] Every node has a path to END
- [ ] No direct agent-to-agent calls are implied
- [ ] `agent_topology.md` has all four required sections: Orchestrator, Specialist Agents, Routing Logic, Failure Modes

Then proceed to `/architecture-preflight <feature_name>`.
