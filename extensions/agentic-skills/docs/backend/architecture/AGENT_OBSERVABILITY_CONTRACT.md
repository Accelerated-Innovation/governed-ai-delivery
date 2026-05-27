# Agent Observability Contract

## Purpose

This contract governs observability for agent runs, tool calls, recommendations, approvals, and external actions.

## Architectural Rule

Agentic systems must be observable enough to debug behavior, audit decisions, evaluate quality, and improve prompts or skills without exposing unauthorized client data.

## Required Observability Events

The system should capture:

- Agent run requested
- Agent run authorized or denied
- Context loaded
- Model invoked
- Tool called
- Structured output validated
- Recommendation created
- Action accepted/rejected
- Approval requested
- Approval decision recorded
- External task created or updated
- SharePoint publish requested/completed
- Agent run failed

## Required Agent Run Metadata

Every agent run should record:

- Run ID
- Skill ID and version
- Runtime mode
- Model or routing profile
- Client/workspace ID
- Engagement ID when applicable
- User ID or trigger ID
- Authorization context summary
- Start/end timestamps
- Token usage when available
- Cost when available
- Latency
- Outcome

## Traceability

Agent outputs should be traceable to:

- Source skill
- Source context
- Source metrics or documents
- Trigger event
- Recommendation/action/proposal IDs
- Approvals
- External task IDs

## Prompt and Context Logging

Prompt and context logging must follow security and privacy rules.

The system should support:

- Redaction
- Tenant scoping
- Role-scoped trace access
- Configurable retention
- Prompt/template version tracking

## Metrics

Recommended operational metrics:

- Agent run count
- Success/failure rate
- Validation failure rate
- Tool failure rate
- Average latency
- Token/cost by skill
- Recommendations generated
- Recommendations accepted/rejected
- Action conversion rate
- Approval cycle time
- External sync failure rate

## Prohibited Patterns

The system must not:

- Log secrets or access tokens.
- Expose traces across tenants or engagements.
- Store full sensitive context when a redacted summary is sufficient.
- Lose correlation between agent runs and durable outputs.

## Feature Preflight Requirements

Feature `architecture_preflight.md` must identify:

- Observability events emitted
- Trace/correlation IDs used
- Sensitive data handling
- Metrics added
- Retention considerations

