# Recommendation and Action Contract

## Purpose

This contract governs the lifecycle from agent-generated recommendation to client-reviewed action item.

## Architectural Rule

Recommendations are suggestions. Action items are decisions. External tasks are execution records.

```text
Recommendation
  -> client review
  -> accepted action item
  -> plan routing
  -> optional external task
  -> optional governed artifact proposal
```

## Recommendation Lifecycle

Recommended statuses:

```text
generated
client_review
accepted
rejected
deferred
dismissed
superseded
expired
```

## Action Item Lifecycle

Recommended statuses:

```text
proposed
accepted
prioritized
assigned
in_progress
done
rejected
deferred
cancelled
```

## Required Recommendation Fields

Recommendations must include:

- Recommendation ID
- Client/workspace ID
- Engagement ID when applicable
- Source skill ID and version
- Title
- Summary
- Why it matters
- Supporting signals
- Suggested actions
- Suggested priority
- Suggested plan route
- Confidence
- Risk level
- Visibility policy
- Trigger metadata

## Required Action Item Fields

Action items must include:

- Action item ID
- Source recommendation ID when applicable
- Title
- Summary
- Client/workspace ID
- Engagement ID
- Plan type or route
- Priority
- Status
- Owner when assigned
- Due date when assigned
- Linked metrics
- Linked artifacts
- External task references
- Decision history

## Client Decision Ownership

The client owns the decision to accept, reject, reprioritize, or route action items unless a policy assigns the decision to an internal or engagement role.

Agent-suggested priority must remain distinguishable from human-selected priority.

## Plan Routing

Accepted action items should be routed to an appropriate plan.

Examples:

- Acceleration Plan
- Quarterly Change Plan
- Targeted Coaching Plan
- Communications Plan
- Insights Plan

Plan routing may be recommended by an agent but must be editable by authorized users.

## Deduping

The system must avoid repeated recommendations for the same issue.

Deduping should consider:

- Client
- Engagement
- Metric or signal
- Skill ID
- Recommendation type
- Open action items
- Recent dismissals

## Prohibited Patterns

The system must not:

- Create external tasks before the action is accepted unless policy explicitly allows it.
- Hide rejected recommendations from audit history.
- Treat a generated recommendation as accepted.
- Lose the link between metric signal, recommendation, action, and external task.

## Feature Preflight Requirements

Feature `architecture_preflight.md` must identify:

- Recommendation type
- Action item type
- Status transitions
- Plan routing rules
- Visibility policy
- Deduping behavior
- External task sync behavior

