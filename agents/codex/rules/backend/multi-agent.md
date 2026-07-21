# Multi-Agent Rules

These rules apply when editing agent runtimes, task controllers, delegation, orchestration, or shared agent state.

Contracts:

- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/SKILL_ORIENTED_AGENT_ARCHITECTURE.md`
- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/RUNTIME_STATE_AND_EXECUTION_CONTRACT.md`
- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/AUTHORITY_AND_APPROVAL_CONTRACT.md`

---

## Rules

- One accountable principal accepts the task and exactly one trusted runtime owner controls authoritative task state
- Classify each component as agent run, skill, tool, resource, workflow, policy, evaluator, memory, or trusted controller
- Model output, skill output, delegation, routing, and completion claims are proposals until trusted code validates and commits them
- Runtime state is explicit, typed, versioned, and updated only by declared authoritative writers
- Handoffs preserve task identity, authority, budgets, context provenance, and evidence; they do not create implicit authority
- Every external operation uses a typed port, fresh authorization, idempotency, bounded execution, and reconciliation or compensation
- Loops, retries, delegation depth, time, tokens, cost, and tool use have explicit limits
- Completion requires an independent verification gate and a trusted task-controller transition
- If the system invokes language models, also apply the `llm-application` gateway, guardrail, observability, and evaluation contracts
- Record the chosen orchestration framework in `TECH_STACK.md` or an ADR; the SOAA contracts do not require one

## Prohibited

- Multiple authoritative runtime owners for one task
- Direct model or skill writes to authoritative state
- Authority inferred from a prompt, tool schema, skill package, handoff, or model confidence
- Hidden agent-to-agent calls, implicit recursion, unconditional loops, or unbounded delegation
- Declaring completion from model confidence, agent confidence, or skill success alone
