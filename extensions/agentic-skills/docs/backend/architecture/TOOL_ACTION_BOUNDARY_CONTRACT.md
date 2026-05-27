# Tool Action Boundary Contract

## Purpose

This contract defines the boundary between agent reasoning, deterministic tools, application services, and external actions.

## Architectural Rule

Agents may propose or request actions. Application services decide whether actions are allowed. Integration adapters execute approved external operations.

```text
Agent
  -> proposes or requests action
  -> Policy / application service validates request
  -> Human approval when required
  -> Integration adapter executes
  -> Audit event records outcome
```

## Action Classes

Actions should be classified by risk:

- Read-only: retrieve data, summarize, inspect state.
- Drafting: create recommendations, proposals, or task drafts.
- Internal mutation: update portal-owned state.
- External mutation: create or update records in external systems.
- Governed artifact mutation: write to official documents, records, or published artifacts.

## Required Boundaries

Agents may:

- Read authorized context.
- Call approved read tools.
- Produce structured proposals.
- Request approved application actions.
- Explain rationale and source basis.

Agents must not:

- Directly write to SharePoint, ClickUp, Jira, Planner, Teams, or similar systems.
- Grant themselves permissions.
- Skip required approvals.
- Convert model output into durable state without schema validation.
- Execute external mutations through prompt-only instructions.

## Tool Contracts

Every tool callable by an agent must have a documented contract:

- Tool name
- Purpose
- Input schema
- Output schema
- Side effects
- Required permissions
- Idempotency behavior
- Error behavior
- Audit requirements

## Idempotency

External mutation tools must support idempotency or duplicate detection.

Examples:

- `external_correlation_id`
- `action_item_id`
- `proposal_id`
- `request_hash`

## Approval Boundary

Approval must happen before the side effect, not after it.

Approval-required actions include:

- Publishing to SharePoint
- Creating external tasks when auto-sync is disabled
- Modifying methodology-sensitive artifacts
- Sending client-visible notifications
- Changing integration settings

## Audit Boundary

Every action request and execution must create audit events that capture:

- Requesting agent or user
- Acting user or service
- Policy decision
- Approval status
- External system target
- Result
- Timestamp

## Feature Preflight Requirements

Feature `architecture_preflight.md` must list:

- Tools involved
- Action class
- Side effects
- Required approvals
- Idempotency strategy
- Audit events

