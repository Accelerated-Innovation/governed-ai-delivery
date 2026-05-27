# Background Agent Trigger Contract

## Purpose

This contract governs scheduled and event-triggered agent runs.

## Architectural Rule

Background agents may proactively analyze context and create recommendations, summaries, or proposals. They must not create surprises: external mutations, client notifications, and governed artifact changes require explicit policy and approval.

## Trigger Types

Supported trigger categories:

- Schedule trigger: runs at a configured cadence.
- Event trigger: runs when a domain event occurs.
- Threshold trigger: runs when a metric crosses a threshold.
- Trend trigger: runs when a pattern persists over time.
- Staleness trigger: runs when an action, approval, or data source is stale.

## Trigger Definition

Each trigger must define:

- Trigger ID
- Trigger type
- Skill ID
- Required context
- Schedule or event condition
- Deduping rule
- Throttling rule
- Output type
- Visibility policy
- Failure behavior

## Recommended Trigger Lifecycle

```text
detected
  -> eligibility_checked
  -> deduped_or_scheduled
  -> agent_run_created
  -> output_validated
  -> stored
  -> visible_to_authorized_users
```

## Deduping

Background agents must avoid repeated noise.

Examples:

- Do not create duplicate recommendations for the same metric within a configured period.
- If an accepted action is already open, update context rather than create a duplicate.
- Cluster related metric changes into one recommendation when appropriate.

## Throttling

Triggers must enforce throttling to prevent bursts from overwhelming users or systems.

Throttle policies may be configured by:

- Client
- Engagement
- Skill
- Metric category
- Recommendation type
- User-visible priority

## Client Visibility

Background output must pass visibility policy before becoming visible.

The system must capture whether an output is:

- Internal-only
- Client-visible
- Reviewer-visible
- Role-scoped
- Pending approval

## Prohibited Patterns

Background agents must not:

- Write to external systems without policy and approval.
- Notify clients directly unless explicitly allowed.
- Create unbounded recommendation volume.
- Bypass role-based visibility.
- Run using stale or unauthorized context.

## Feature Preflight Requirements

Feature `architecture_preflight.md` must identify:

- Trigger type
- Scheduling/event source
- Required context
- Deduping rule
- Throttling rule
- Output type
- Visibility policy
- Audit events

