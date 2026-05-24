# Background Trigger Policy

## Purpose

Define when a background agent runs, what it can produce, and how noise is controlled.

## Trigger Identity

- Trigger ID:
- Source skill:
- Trigger type: schedule | event | threshold | trend | staleness
- Runtime environment:

## Trigger Condition

Describe the schedule or event condition that starts the run.

Examples:

- Weekly scorecard review
- Metric moved off track
- Risk cluster detected
- Accepted action overdue
- New assessment submitted

## Required Context

| Context | Source | Scope | Required? |
|---|---|---|---:|
| | | | |

## Output Policy

| Output Type | Client Visible | Approval Required | Notes |
|---|---:|---:|---|
| | | | |

## Deduping Rule

Describe how duplicate outputs are prevented.

## Throttling Rule

Describe frequency limits by client, engagement, skill, metric, or output type.

## Failure Handling

Describe retry behavior, dead-letter behavior, and user-visible failure handling.

## Audit Events

List required audit events.

## Evaluation

Describe tests and evals for this trigger.

