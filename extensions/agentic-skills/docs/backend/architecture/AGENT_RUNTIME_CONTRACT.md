# Agent Runtime Contract

## Purpose

This contract governs how agentic capabilities are executed, observed, retried, and controlled. It applies to both interactive agents and background agents.

## Architectural Rule

Agents are reasoning components. They may interpret context, call approved tools, draft outputs, and request actions. They must not own durable business state, bypass authorization, or directly mutate external systems outside approved service boundaries.

## Runtime Modes

Agentic systems may support two runtime modes:

- Interactive agents: user-triggered, conversational, and context-aware.
- Background agents: scheduled or event-triggered, analytical, and recommendation-oriented.

Both modes must run through the same authorization, policy, observability, and evaluation boundaries.

## Required Runtime Responsibilities

The runtime must:

- Load the active Agent Skill package and version.
- Resolve tenant, client, engagement, user, role, and permission context.
- Retrieve only the context needed for the run.
- Enforce allowed tools and actions for the active skill.
- Validate structured outputs against schemas.
- Record trace metadata, tool calls, model usage, and run outcome.
- Return safe failure states when required context, policy, or validation is missing.

## Agent Run Lifecycle

Every agent run should move through a clear lifecycle:

```text
requested
  -> authorized
  -> context_loaded
  -> model_invoked
  -> tools_called
  -> output_validated
  -> stored_or_returned
  -> completed | failed | blocked
```

## State Boundary

Agents must not be the system of record.

Durable state belongs in application services and persistence layers, including:

- Recommendations
- Action items
- Approvals
- Change proposals
- External task references
- Audit events
- Skill versions

## Failure Handling

Agent failures must be explicit and recoverable.

The runtime must distinguish:

- Authorization failure
- Missing context
- Tool failure
- Schema validation failure
- Model refusal or safety block
- Timeout
- External integration failure
- Policy violation

Retries must be bounded and idempotent. Retrying an agent run must not duplicate durable actions unless the action service explicitly permits it.

## Prohibited Patterns

The runtime must not:

- Let agents write directly to external systems.
- Let agents bypass application services.
- Persist unvalidated structured output.
- Expose hidden context or unauthorized data.
- Treat model output as approved user intent.
- Retry external writes without idempotency protection.

## Required Evidence

Feature `architecture_preflight.md` files must identify:

- Runtime mode: interactive, background, or both.
- Active Agent Skill package.
- Required context sources.
- Allowed tools.
- Durable state touched.
- Applicable approval gates.
- Evaluation requirements.

