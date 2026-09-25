---
name: govkit-multi-agent-design
description: Design a governed agent topology and produce agent_topology.md. Use for multi-agent features, delegation, adaptive orchestration, or when invoking /govkit-multi-agent-design.
---

# Governed Agent Topology Design

Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Required extension

Confirm `extensions/skill-oriented-agent-architecture/manifest.yaml` exists. If it is missing, stop and report:

```bash
govkit extension add skill-oriented-agent-architecture --target .
```

## Inputs to read

- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/eval_criteria.yaml`
- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/SKILL_ORIENTED_AGENT_ARCHITECTURE.md`
- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/RUNTIME_STATE_AND_EXECUTION_CONTRACT.md`
- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/AUTHORITY_AND_APPROVAL_CONTRACT.md`
- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/RESILIENCE_AND_RECOVERY_CONTRACT.md`
- `extensions/skill-oriented-agent-architecture/docs/backend/architecture/EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md`
- `docs/backend/architecture/TECH_STACK.md` and applicable ADRs

If the design invokes language models, also load the applicable `llm-application` contracts.

## 1. Justify the topology

State why multiple agent runs, delegation, or specialization is necessary. Prefer the smallest topology that satisfies the feature. Stop and recommend a simpler workflow when separate agent ownership does not provide a clear benefit.

## 2. Define task control

Record:

- accountable principal and accepted task boundary
- exactly one trusted runtime owner and task controller
- authoritative state and its declared writers
- completion authority and independent verification gate
- time, token, cost, tool, retry, and delegation budgets

## 3. Classify components and responsibilities

Classify every component as agent run, skill, tool, resource, workflow, policy, evaluator, memory, or trusted controller. For each agent run, define its bounded responsibility, accepted inputs, proposed outputs, context, permitted ports, authority ceiling, and evidence obligations. Collapse overlapping responsibilities.

## 4. Define execution and state

Specify typed, versioned runtime state; legal transitions; deterministic admission and routing controls; proposal/validation/commit boundaries; and the persistence or checkpoint boundary. Model or skill output cannot be an authoritative state write.

## 5. Define handoffs and external operations

For each handoff, preserve task identity, authority, context provenance, budgets, and evidence. For every external operation, define typed arguments, fresh authorization, approval, idempotency, timeout, retry, reconciliation, compensation, and evidence.

## 6. Define failure and recovery

Specify failure categories, bounded retries, cancellation, deadline behavior, checkpoint/replay rules, reconciliation, compensation, degraded behavior, escalation, and terminal states. No implicit recursion or unbounded delegation is permitted.

## 7. Define completion

List the independent evidence required to enter verification and the trusted controller transition required for completion. Agent confidence, model confidence, and skill success are not completion evidence by themselves.

## Output

Write `features/<feature_name>/agent_topology.md` using the bundled template. Include the framework or runtime chosen in `TECH_STACK.md` or an ADR, but do not make product-specific types part of application contracts.

Before proceeding, confirm:

- [ ] one accountable principal and exactly one runtime owner
- [ ] all components and authoritative writers are classified
- [ ] state, transitions, handoffs, and ports are typed
- [ ] authority and approvals are explicit and fresh at execution time
- [ ] retries, loops, delegation, time, tokens, cost, and tools are bounded
- [ ] every side effect has idempotency and recovery behavior
- [ ] completion requires independent evidence and a trusted transition

Then proceed to `/govkit-architecture-preflight <feature_name>`.
