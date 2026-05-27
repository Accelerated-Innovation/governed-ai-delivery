# Human Approval Contract

## Purpose

This contract governs when and how human review is required before agent-generated recommendations, actions, or artifact changes become durable or external.

## Architectural Rule

Agents can propose. Humans approve when risk, policy, client visibility, or external mutation requires it.

## Approval Levels

Approval requirements should be based on risk:

- Low risk: simple, reversible, or internal-only changes.
- Medium risk: client-visible recommendations, plan routing, priority changes, or external task creation.
- High risk: official artifacts, methodology-sensitive changes, security settings, integration configuration, or broad client-visible actions.

## Approval Subjects

Approval may apply to:

- Recommendations
- Action items
- Plan routing decisions
- External task creation
- Change proposals
- SharePoint publishing
- Client notifications
- Skill version activation
- Automation policy changes

## Required Approval Metadata

Every approval request must include:

- Subject type
- Subject ID
- Proposed change
- Rationale
- Source basis
- Risk level
- Required approver roles
- Expiration or stale date when applicable
- Current status

## Approval Statuses

Recommended statuses:

```text
draft
pending_review
approved
rejected
changes_requested
expired
published
cancelled
```

## Reviewer Scope

Approval rights must be role and scope aware.

Examples:

- Program Lead can approve scoped client actions.
- Plan Owner can approve scoped plan actions.
- Engagement Admin can approve engagement setup and publishing operations.
- Accelerated Innovation Coach can review methodology-sensitive changes.
- Platform Admin does not automatically gain client engagement approval rights.

## Human Edits

Reviewers may edit agent-generated proposals before approval. Edited approvals must record:

- Original proposal
- Human-edited version
- Editor
- Edit timestamp
- Approval decision

## Prohibited Patterns

Systems must not:

- Treat recommendation visibility as approval.
- Treat user chat acknowledgment as approval unless explicitly captured.
- Publish official artifacts based only on model output.
- Allow approval by unauthorized roles.
- Hide high-risk changes inside low-risk batches.

## Audit Requirements

Approval events must be immutable or append-only.

Required audit fields:

- Approver user ID
- Role or group used for approval
- Decision
- Timestamp
- Subject ID
- Prior state
- Approved state
- Rationale or comment when provided

